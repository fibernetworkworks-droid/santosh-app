package com.newtika.santosh

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioFocusRequest
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.media.audiofx.AcousticEchoCanceler
import android.media.audiofx.AutomaticGainControl
import android.media.audiofx.NoiseSuppressor
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import java.io.ByteArrayOutputStream
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

/**
 * Full-duplex call audio for the Baat tab: the mic keeps listening while Santosh talks.
 * Uses the phone's call path (VOICE_COMMUNICATION) so hardware echo cancellation removes
 * Santosh's own voice from the mic, which is what lets you interrupt him naturally.
 *
 * Built to survive a real phone: if the microphone or the speaker path dies in the middle of a call (Bluetooth
 * connected, another app grabbed the mic, the audio server restarted) it is opened again; a real phone call or
 * another app taking the audio pauses the call and it carries on when the audio is back; plugging in or
 * removing a headset or Bluetooth earbuds moves the sound by itself.
 */
object VoiceAudio {
    private const val IN_RATE = 16000
    private const val OUT_RATE = 24000
    private const val CHUNK = 1280            // 40 ms of 16 kHz PCM16

    private var record: AudioRecord? = null
    private var track: AudioTrack? = null
    private var aec: AcousticEchoCanceler? = null
    private var ns: NoiseSuppressor? = null
    private var agc: AutomaticGainControl? = null
    private var micThread: Thread? = null
    private var playThread: Thread? = null
    private val queue = LinkedBlockingQueue<ByteArray>()
    @Volatile private var running = false
    @Volatile private var generation = 0      // bumps on flush so a write in progress is dropped
    @Volatile private var paused = false      // another app (a real phone call...) has the audio for a moment
    // Smooth start: a reply after a silence waits for a small cushion of audio first, so bursty mobile data
    // does not make his first words stutter. The cushion grows by itself if a reply still runs dry mid-sentence.
    @Volatile private var playingUntil = 0L   // when the audio written so far finishes playing (uptime ms)
    @Volatile private var cushionMs = 80
    private const val CUSHION_MAX_MS = 240

    private var manager: AudioManager? = null
    private var focusRequest: AudioFocusRequest? = null
    private var deviceCallback: AudioDeviceCallback? = null
    private val ui = Handler(Looper.getMainLooper())

    /** Receives mic chunks; set by the activity's EventChannel. */
    @Volatile var sink: ((ByteArray) -> Unit)? = null
    /** v0.51 speech probability (Silero VAD) of each mic chunk, sent just before the chunk itself. */
    @Volatile var vadSink: ((Float) -> Unit)? = null

    /** Audio trouble for the app to show: "paused" / "resumed" (another app has the audio), "audio_error" (mic or speaker lost for good). */
    @Volatile var onState: ((String, String) -> Unit)? = null

    fun hasPermission(ctx: Context) = Build.VERSION.SDK_INT < 23 ||
        ctx.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    private val focusListener = AudioManager.OnAudioFocusChangeListener { change ->
        when (change) {
            AudioManager.AUDIOFOCUS_LOSS -> {
                // another app took the audio for good: wait, then ask for it back (the user is in a call)
                if (!paused) {
                    paused = true
                    flush()
                    onState?.invoke("paused", "focus")
                }
                ui.postDelayed({
                    val am = manager
                    if (running && paused && am != null) takeFocus(am)
                }, 3000)
            }
            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> {
                if (!paused) {
                    paused = true
                    flush()
                    onState?.invoke("paused", "focus")
                }
            }
            AudioManager.AUDIOFOCUS_GAIN -> {
                if (paused) {
                    paused = false
                    onState?.invoke("resumed", "")
                }
            }
            else -> {}
        }
    }

    private fun takeFocus(am: AudioManager) {
        try {
            if (Build.VERSION.SDK_INT >= 26) {
                val req = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
                    .setAudioAttributes(AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
                    .setAcceptsDelayedFocusGain(true)
                    .setOnAudioFocusChangeListener(focusListener)
                    .build()
                focusRequest = req
                am.requestAudioFocus(req)
            } else {
                @Suppress("DEPRECATION")
                am.requestAudioFocus(focusListener, AudioManager.STREAM_VOICE_CALL, AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            }
        } catch (_: Exception) {}
    }

    private fun dropFocus(am: AudioManager) {
        try {
            if (Build.VERSION.SDK_INT >= 26) {
                focusRequest?.let { am.abandonAudioFocusRequest(it) }
                focusRequest = null
            } else {
                @Suppress("DEPRECATION")
                am.abandonAudioFocus(focusListener)
            }
        } catch (_: Exception) {}
    }

    /** A headset or Bluetooth device connected or disconnected during the call: move the sound. */
    private fun watchDevices(am: AudioManager) {
        if (Build.VERSION.SDK_INT < 23) return
        val cb = object : AudioDeviceCallback() {
            override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>?) = reroute()
            override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>?) = reroute()
        }
        deviceCallback = cb
        try { am.registerAudioDeviceCallback(cb, ui) } catch (_: Exception) {}
    }

    private fun reroute() {
        val am = manager ?: return
        if (running) {
            try { route(am) } catch (_: Exception) {}
        }
    }

    private fun releaseEffects() {
        try { aec?.release() } catch (_: Exception) {}
        try { ns?.release() } catch (_: Exception) {}
        try { agc?.release() } catch (_: Exception) {}
        aec = null; ns = null; agc = null
    }

    /** A new microphone with the phone's echo canceller, noise filter and gain control. Null when it will not open. */
    private fun openRecord(): AudioRecord? {
        val minIn = AudioRecord.getMinBufferSize(IN_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val r = try {
            AudioRecord(MediaRecorder.AudioSource.VOICE_COMMUNICATION, IN_RATE, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT, maxOf(minIn, CHUNK * 4))
        } catch (e: SecurityException) {
            throw e
        } catch (e: Exception) {
            return null
        }
        if (r.state != AudioRecord.STATE_INITIALIZED) {
            r.release()
            return null
        }
        releaseEffects()
        val sid = r.audioSessionId
        try {
            if (AcousticEchoCanceler.isAvailable()) aec = AcousticEchoCanceler.create(sid)?.apply { enabled = true }
            if (NoiseSuppressor.isAvailable()) ns = NoiseSuppressor.create(sid)?.apply { enabled = true }
            if (AutomaticGainControl.isAvailable()) agc = AutomaticGainControl.create(sid)?.apply { enabled = true }
        } catch (_: Exception) {}
        return r
    }

    private fun openTrack(): AudioTrack {
        val minOut = AudioTrack.getMinBufferSize(OUT_RATE, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT)
        return AudioTrack.Builder()
            .setAudioAttributes(AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            .setAudioFormat(AudioFormat.Builder().setSampleRate(OUT_RATE)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
            .setBufferSizeInBytes(maxOf(minOut * 2, 9600))
            .setTransferMode(AudioTrack.MODE_STREAM)
            .apply { if (Build.VERSION.SDK_INT >= 26) setPerformanceMode(AudioTrack.PERFORMANCE_MODE_LOW_LATENCY) }
            .build()
    }

    /** Undo what start() changed on the phone before it gave up. */
    private fun undoSetup(am: AudioManager) {
        deviceCallback?.let {
            try { am.unregisterAudioDeviceCallback(it) } catch (_: Exception) {}
        }
        deviceCallback = null
        dropFocus(am)
        if (Build.VERSION.SDK_INT >= 31) {
            am.clearCommunicationDevice()
        } else {
            @Suppress("DEPRECATION")
            am.isSpeakerphoneOn = false
        }
        am.mode = AudioManager.MODE_NORMAL
        manager = null
    }

    /** Returns null when started, or a short reason. */
    @Synchronized
    fun start(ctx: Context): String? {
        if (running) return null
        if (!hasPermission(ctx)) return "permission"
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        manager = am
        paused = false
        cushionMs = 80
        playingUntil = 0L
        am.mode = AudioManager.MODE_IN_COMMUNICATION
        route(am)
        takeFocus(am)
        watchDevices(am)

        val r = try {
            openRecord()
        } catch (e: SecurityException) {
            undoSetup(am)
            return "permission"
        }
        if (r == null) {
            undoSetup(am)
            return "Microphone shuru nahi ho paya"
        }
        val t = try {
            openTrack()
        } catch (e: Exception) {
            r.release()
            releaseEffects()
            undoSetup(am)
            return "Speaker shuru nahi ho paya"
        }
        record = r
        track = t
        queue.clear()
        running = true
        t.play()
        r.startRecording()

        micThread = Thread({ micLoop(r) }, "santosh-mic").also { it.priority = Thread.MAX_PRIORITY; it.start() }
        playThread = Thread({ playLoop(t) }, "santosh-speaker").also { it.priority = Thread.MAX_PRIORITY; it.start() }
        return null
    }

    private fun micLoop(first: AudioRecord) {
        val buf = ByteArray(CHUNK)
        var cur = first
        var failures = 0
        while (running) {
            val n = try { cur.read(buf, 0, buf.size) } catch (e: Exception) { -1 }
            if (n > 0) {
                failures = 0
                if (!paused) {
                    val chunk = buf.copyOf(n)
                    vadSink?.let { vs -> SileroVad.feed(chunk)?.let { p -> vs(p) } }
                    sink?.invoke(chunk)
                }
            } else if (n < 0 && running) {
                // the microphone died (Bluetooth connected, another app took it...): open it again
                failures++
                try { cur.stop() } catch (_: Exception) {}
                try { cur.release() } catch (_: Exception) {}
                if (failures > 3) {
                    onState?.invoke("audio_error", "mic read=$n")
                    return
                }
                try { Thread.sleep(150L * failures) } catch (_: InterruptedException) { return }
                if (!running) return
                val fresh = try { openRecord() } catch (e: Exception) { null }
                if (fresh == null) {
                    if (running) onState?.invoke("audio_error", "mic reopen")
                    return
                }
                try {
                    fresh.startRecording()
                } catch (e: Exception) {
                    fresh.release()
                    if (running) onState?.invoke("audio_error", "mic start")
                    return
                }
                cur = fresh
                record = fresh
            }
        }
    }

    private fun playLoop(first: AudioTrack) {
        var t = first
        while (running) {
            val chunk = try { queue.poll(200, TimeUnit.MILLISECONDS) } catch (_: InterruptedException) { null } ?: continue
            val gen = generation
            val now = SystemClock.uptimeMillis()
            var data = chunk
            if (now > playingUntil + 150) {
                // a new reply after a silence: gather a small cushion first, then fade in so it never clicks
                data = gather(chunk, gen, now)
                fadeIn(data)
            } else if (now > playingUntil + 20) {
                // ran dry in the middle of a sentence: keep a bigger cushion for the rest of the call
                cushionMs = minOf(cushionMs + 40, CUSHION_MAX_MS)
            }
            var off = 0
            while (running && off < data.size && gen == generation && !paused) {
                val w = try { t.write(data, off, minOf(data.size - off, 4800)) } catch (e: Exception) { AudioTrack.ERROR_DEAD_OBJECT }
                if (w < 0) {
                    // the speaker path died (headset unplugged, audio server restarted): build a new one
                    val fresh = try { openTrack().also { it.play() } } catch (e: Exception) { null }
                    try { t.release() } catch (_: Exception) {}
                    if (fresh == null) {
                        if (running) onState?.invoke("audio_error", "speaker")
                        return
                    }
                    t = fresh
                    track = fresh
                    break
                }
                if (w == 0) break
                off += w
            }
            if (gen == generation) {
                val ms = off * 1000L / (OUT_RATE * 2)
                playingUntil = maxOf(SystemClock.uptimeMillis(), playingUntil) + ms
            }
        }
    }

    /** Collect up to cushionMs of audio (or wait a little longer at most) before the first write of a reply. */
    private fun gather(first: ByteArray, gen: Int, start: Long): ByteArray {
        val want = cushionMs * OUT_RATE * 2 / 1000
        if (first.size >= want) return first
        val buf = ByteArrayOutputStream(want * 2)
        buf.write(first)
        val deadline = start + cushionMs + 60
        while (buf.size() < want && running && gen == generation) {
            val left = deadline - SystemClock.uptimeMillis()
            if (left <= 0) break
            val more = try { queue.poll(left, TimeUnit.MILLISECONDS) } catch (_: InterruptedException) { null } ?: break
            buf.write(more)
        }
        return buf.toByteArray()
    }

    /** 5 ms fade-in on 24 kHz PCM16 (little endian). */
    private fun fadeIn(d: ByteArray) {
        val n = minOf(120, d.size / 2)
        for (i in 0 until n) {
            val s = ((d[2 * i].toInt() and 0xff) or (d[2 * i + 1].toInt() shl 8)).toShort().toInt()
            val v = s * i / n
            d[2 * i] = (v and 0xff).toByte()
            d[2 * i + 1] = ((v shr 8) and 0xff).toByte()
        }
    }

    /** Headset or Bluetooth if connected, otherwise the loudspeaker. */
    private fun route(am: AudioManager) {
        if (Build.VERSION.SDK_INT >= 31) {
            val devices = am.availableCommunicationDevices
            val pref = listOf(AudioDeviceInfo.TYPE_WIRED_HEADSET, AudioDeviceInfo.TYPE_WIRED_HEADPHONES,
                AudioDeviceInfo.TYPE_USB_HEADSET, AudioDeviceInfo.TYPE_BLE_HEADSET, AudioDeviceInfo.TYPE_BLUETOOTH_SCO,
                AudioDeviceInfo.TYPE_BUILTIN_SPEAKER)
            for (type in pref) {
                val d = devices.firstOrNull { it.type == type } ?: continue
                if (am.setCommunicationDevice(d)) return
            }
        } else {
            @Suppress("DEPRECATION")
            am.isSpeakerphoneOn = !am.isWiredHeadsetOn
        }
    }

    /** Queue Santosh's voice (24 kHz PCM16). */
    fun play(data: ByteArray) {
        if (running && !paused) queue.offer(data)
    }

    /** Stop his current sentence at once (you interrupted). */
    fun flush() {
        generation++
        queue.clear()
        playingUntil = 0L
        track?.let {
            try { it.pause(); it.flush(); it.play() } catch (_: Exception) {}
        }
    }

    @Synchronized
    fun stop(ctx: Context) {
        if (!running && record == null) return
        running = false
        paused = false
        generation++
        queue.clear()
        try { micThread?.join(300) } catch (_: InterruptedException) {}
        try { playThread?.join(300) } catch (_: InterruptedException) {}
        try { record?.stop() } catch (_: Exception) {}
        try { record?.release() } catch (_: Exception) {}
        try { track?.stop() } catch (_: Exception) {}
        try { track?.release() } catch (_: Exception) {}
        releaseEffects()
        record = null; track = null
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        undoSetup(am)
    }
}
