package com.newtika.santosh

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.SystemClock
import java.nio.FloatBuffer

/**
 * Santosh Wake: our own on-device "Hey Santosh" detector (replaces Picovoice; no keys, no fees).
 *
 * 16 kHz mic -> every 80 ms (1280 samples):
 *   melspectrogram.onnx on the last 1760 samples -> new mel frames (x/10 + 2)
 *   embedding_model.onnx on the last 76 mel frames -> one 96-number embedding
 *   hey_santosh.onnx on the last 16 embeddings (1.28 s) -> score 0..1
 * The feature models are the open-source openWakeWord ones (Apache-2.0); the classifier is trained by wakeword/train.py
 * with exactly the same maths, so phone and training agree. Nothing leaves the phone.
 */
class WakeEngine(
    ctx: Context,
    classifier: ByteArray,
    private val threshold: Float,
    private val onWake: (Float) -> Unit,
) {
    companion object {
        const val SR = 16000
        const val CHUNK = 1280
        private const val MEL_CONTEXT = CHUNK + 480
        private const val MEL_WINDOW = 76
        private const val N_EMB = 16
        private const val DEBOUNCE_MS = 2500L

        fun asset(ctx: Context, name: String): ByteArray = ctx.assets.open("wake/$name").use { it.readBytes() }
    }

    private val env = OrtEnvironment.getEnvironment()
    private val opts = OrtSession.SessionOptions().apply { setIntraOpNumThreads(1) }
    private val mel = env.createSession(asset(ctx, "melspectrogram.onnx"), opts)
    private val emb = env.createSession(asset(ctx, "embedding_model.onnx"), opts)
    private val clf = env.createSession(classifier, opts)
    private val melIn = mel.inputNames.first()
    private val embIn = emb.inputNames.first()
    private val clfIn = clf.inputNames.first()

    private val raw = FloatArray(MEL_CONTEXT)
    private var rawFill = 0
    private val melFrames = ArrayDeque<FloatArray>()
    private val embeddings = ArrayDeque<FloatArray>()
    private var lastWake = 0L
    private var hits = 0

    @Volatile private var running = false
    private var thread: Thread? = null
    var lastError: String = ""
        private set

    init {
        reset()
    }

    fun reset() {
        rawFill = 0
        melFrames.clear()
        repeat(MEL_WINDOW) { melFrames.addLast(FloatArray(32) { 1f }) }
        embeddings.clear()
        hits = 0
    }

    /** Feed exactly CHUNK samples. Returns the score (or -1 while warming up). */
    fun process(chunk: ShortArray): Float {
        // keep the last 1760 samples (this chunk + 30 ms of context), as openWakeWord does
        System.arraycopy(raw, CHUNK, raw, 0, MEL_CONTEXT - CHUNK)
        for (i in 0 until CHUNK) raw[MEL_CONTEXT - CHUNK + i] = chunk[i].toFloat()
        rawFill = minOf(MEL_CONTEXT, rawFill + CHUNK)
        val n = rawFill
        val input = FloatBuffer.wrap(raw, MEL_CONTEXT - n, n).slice()
        OnnxTensor.createTensor(env, input, longArrayOf(1, n.toLong())).use { t ->
            mel.run(mapOf(melIn to t)).use { r ->
                val out = (r[0] as OnnxTensor).floatBuffer
                val frames = out.remaining() / 32
                for (f in 0 until frames) {
                    val row = FloatArray(32) { out.get() / 10f + 2f }
                    melFrames.addLast(row)
                }
            }
        }
        while (melFrames.size > MEL_WINDOW) melFrames.removeFirst()

        val window = FloatArray(MEL_WINDOW * 32)
        var k = 0
        for (row in melFrames) for (v in row) window[k++] = v
        OnnxTensor.createTensor(env, FloatBuffer.wrap(window), longArrayOf(1, MEL_WINDOW.toLong(), 32, 1)).use { t ->
            emb.run(mapOf(embIn to t)).use { r ->
                val out = (r[0] as OnnxTensor).floatBuffer
                embeddings.addLast(FloatArray(96) { out.get() })
            }
        }
        while (embeddings.size > N_EMB) embeddings.removeFirst()
        if (embeddings.size < N_EMB) return -1f

        val feats = FloatArray(N_EMB * 96)
        k = 0
        for (e in embeddings) for (v in e) feats[k++] = v
        val score = OnnxTensor.createTensor(env, FloatBuffer.wrap(feats), longArrayOf(1, N_EMB.toLong(), 96)).use { t ->
            clf.run(mapOf(clfIn to t)).use { r -> (r[0] as OnnxTensor).floatBuffer.get() }
        }
        hits = if (score >= threshold) hits + 1 else 0
        val now = SystemClock.elapsedRealtime()
        if (hits >= 1 && now - lastWake > DEBOUNCE_MS) {
            lastWake = now
            hits = 0
            onWake(score)
        }
        return score
    }

    /** Start listening on the microphone in a background thread. */
    @SuppressLint("MissingPermission")
    fun start(): Boolean {
        if (running) return true
        val min = AudioRecord.getMinBufferSize(SR, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val rec = try {
            AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, SR, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT, maxOf(min, CHUNK * 4))
        } catch (e: Exception) {
            lastError = "Mic nahi mila: ${e.message}"
            return false
        }
        if (rec.state != AudioRecord.STATE_INITIALIZED) {
            rec.release()
            lastError = "Mic abhi kisi aur app ke paas hai"
            return false
        }
        running = true
        reset()
        thread = Thread({
            val buf = ShortArray(CHUNK)
            try {
                rec.startRecording()
                while (running) {
                    var got = 0
                    while (got < CHUNK && running) {
                        val n = rec.read(buf, got, CHUNK - got)
                        if (n <= 0) break
                        got += n
                    }
                    if (got == CHUNK) {
                        try {
                            process(buf)
                        } catch (e: Exception) {
                            lastError = "Wake engine: ${e.message}"
                        }
                    } else if (running) {
                        Thread.sleep(20)
                    }
                }
            } finally {
                try { rec.stop() } catch (_: Exception) {}
                rec.release()
            }
        }, "santosh-wake").apply { priority = Thread.NORM_PRIORITY - 1; start() }
        return true
    }

    fun stop() {
        running = false
        thread?.join(1500)
        thread = null
    }

    fun close() {
        stop()
        try { clf.close() } catch (_: Exception) {}
        try { emb.close() } catch (_: Exception) {}
        try { mel.close() } catch (_: Exception) {}
    }
}
