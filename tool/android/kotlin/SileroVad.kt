package com.newtika.santosh

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import java.nio.FloatBuffer
import java.nio.LongBuffer

/** v0.51 Silero VAD v5 (MIT, github.com/snakers4/silero-vad) on the phone: speech probability for each 40 ms mic
 *  chunk of a call, so the barge-in gate opens for a human voice, not for clatter, music, fans or traffic.
 *  16 kHz, 512-sample windows with 64 samples of context and the model's own recurrent state. ~1 ms per window. */
object SileroVad {
    private const val WIN = 512
    private const val CTX = 64
    private var env: OrtEnvironment? = null
    private var session: OrtSession? = null
    private val state = FloatArray(2 * 1 * 128)
    private val context = FloatArray(CTX)
    private val pending = FloatArray(WIN * 4)
    private var fill = 0
    @Volatile var failed = false
        private set

    @Synchronized
    fun init(ctx: Context) {
        if (session != null || failed) return
        try {
            val e = OrtEnvironment.getEnvironment()
            val bytes = ctx.assets.open("vad/silero_vad.onnx").use { it.readBytes() }
            session = e.createSession(bytes, OrtSession.SessionOptions().apply { setIntraOpNumThreads(1) })
            env = e
        } catch (_: Throwable) {
            failed = true
        }
    }

    @Synchronized
    fun reset() {
        state.fill(0f)
        context.fill(0f)
        fill = 0
    }

    /** Feed one chunk of 16-bit little-endian PCM; returns the highest speech probability in it, or null. */
    @Synchronized
    fun feed(pcm: ByteArray): Float? {
        if (failed) return null
        val s = session ?: return null
        val e = env ?: return null
        val n = pcm.size / 2
        var best = -1f
        for (i in 0 until n) {
            val v = ((pcm[2 * i].toInt() and 0xff) or (pcm[2 * i + 1].toInt() shl 8)).toShort() / 32768f
            pending[fill++] = v
            if (fill == WIN) {
                best = maxOf(best, run(s, e))
                fill = 0
            }
        }
        return if (best < 0f) null else best
    }

    private fun run(s: OrtSession, e: OrtEnvironment): Float {
        val x = FloatArray(CTX + WIN)
        System.arraycopy(context, 0, x, 0, CTX)
        System.arraycopy(pending, 0, x, CTX, WIN)
        System.arraycopy(pending, WIN - CTX, context, 0, CTX)
        return try {
            OnnxTensor.createTensor(e, FloatBuffer.wrap(x), longArrayOf(1, (CTX + WIN).toLong())).use { input ->
                OnnxTensor.createTensor(e, FloatBuffer.wrap(state.copyOf()), longArrayOf(2, 1, 128)).use { st ->
                    OnnxTensor.createTensor(e, LongBuffer.wrap(longArrayOf(16000)), longArrayOf()).use { sr ->
                        s.run(mapOf("input" to input, "state" to st, "sr" to sr)).use { out ->
                            @Suppress("UNCHECKED_CAST")
                            val prob = (out.get(0).value as Array<FloatArray>)[0][0]
                            @Suppress("UNCHECKED_CAST")
                            val ns = out.get(1).value as Array<Array<FloatArray>>
                            var k = 0
                            for (a in ns) for (b in a) for (c in b) { if (k < state.size) state[k++] = c }
                            prob
                        }
                    }
                }
            }
        } catch (_: Throwable) {
            failed = true
            session = null
            -1f
        }
    }
}
