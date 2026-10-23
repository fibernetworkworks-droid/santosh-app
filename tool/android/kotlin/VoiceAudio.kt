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

    /** v0.136.2 true while a music / video app has the audio during the call: the call goes on, Hoola does not fight it. */
    @Volatile var musicPlaying = false

    // v0.142 she is on ANOTHER call (phone / WhatsApp / any VoIP): Hoola steps back, sends no mic, plays nothing, never
    // takes the audio back, and comes back by itself a moment after that call ends (CallWatch, checked every second).
    @Volatile var callHeld: String? = null
        private set
    private var appCtx: Context? = null
    private var callCheckAt = 0L
    private var busyChecks = 0
    private var clearChecks = 0

    private fun otherCall(): String? {
        val c = appCtx ?: return null
        return try { CallWatch.busy(c, true, record?.audioSessionId ?: 0) } catch (_: Throwable) { null }
    }

    private fun holdForCall(kind: String) {
        if (callHeld != null || !running) return
        callHeld = kind
        musicPlaying = false
        busyChecks = 0
        clearChecks = 0
        paused = true
        flush()
        onState?.invoke("call_hold", kind)
    }

    private fun resumeAfterCall() {
        val am = manager ?: return
        if (!running || callHeld == null) return
        callHeld = null
        clearChecks = 0
        try { am.mode = AudioManager.MODE_IN_COMMUNICATION } catch (_: Exception) {}
        try { route(am) } catch (_: Exception) {}
        takeFocus(am)
        paused = false
        onState?.invoke("call_resume", "")
    }

    /** From the mic thread, once a second: start / end the hold for her other call. */
    private fun watchOtherCall() {
        val now = SystemClock.uptimeMillis()
        if (now < callCheckAt) return
        callCheckAt = now + 1000
        val other = otherCall()
        if (callHeld == null) {
            if (other == null) { busyChecks = 0; return }
            busyChecks++
            // a ringing / normal phone call is certain at once; a VoIP signal must hold for 2 checks (no false holds)
            if (other == "phone" || other == "ringing" || busyChecks >= 2) ui.post { holdForCall(other) }
        } else {
            if (other != null) { clearChecks = 0; return }
            clearChecks++
            if (clearChecks >= 2) ui.post { resumeAfterCall() }
        }
    }

    /** A real phone call (or its ringing) is the only thing that should pause Hoola's call. */
    private fun phoneCall(am: AudioManager): Boolean {
        val m = try { am.mode } catch (_: Exception) { AudioManager.MODE_NORMAL }
        return m == AudioManager.MODE_IN_CALL || m == AudioManager.MODE_RINGTONE
    }

    private fun musicNow(am: AudioManager): Boolean = try { am.isMusicActive } catch (_: Exception) { false }

    private fun pauseForOther() {
        if (!paused) {
            paused = true
            flush()
            onState?.invoke("paused", "focus")
        }
    }

    /**
     * v0.136.2 Another app took the audio. Before: the call always paused (mic + Hoola's voice stopped), so playing a
     * Spotify / YouTube song she asked for silenced the call. Now we look for ~2 s: a real phone call -> pause as before;
     * music / video playing -> the call keeps going alongside it (no pause, and we never take the audio back, which
     * would stop her song); neither -> pause as before.
     */
    private fun decideLoss(tries: Int, permanent: Boolean) {
        val am = manager ?: return
        if (!running) return
        val other = if (phoneCall(am)) "phone" else otherCall()
        if (other != null) {
            // v0.142 her phone / WhatsApp call: hold (the mic watch brings Hoola back when that call is over;
            // taking the audio back after 3 s, as before, made Hoola answer what she said to her friend)
            holdForCall(other)
            return
        }
        if (callHeld != null) return
        if (musicNow(am)) {
            if (!musicPlaying) musicFloor = 0.0
            musicPlaying = true
            if (paused) {
                paused = false
                onState?.invoke("resumed", "")
            }
            onState?.invoke("music", "")
            return
        }
        if (tries > 0) {
            ui.postDelayed({ decideLoss(tries - 1, permanent) }, 500)
            return
        }
        pauseForOther()
        if (permanent) ui.postDelayed({
            val a = manager
            if (running && paused && a != null && callHeld == null) {
                if (otherCall() != null || phoneCall(a)) decideLoss(0, true)
                else if (musicNow(a)) decideLoss(0, true) else takeFocus(a)
            }
        }, 3000)
    }

    private val focusListener = AudioManager.OnAudioFocusChangeListener { change ->
        when (change) {
            AudioManager.AUDIOFOCUS_LOSS -> ui.postDelayed({ decideLoss(4, true) }, 300)
            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> ui.postDelayed({ decideLoss(4, false) }, 300)
            AudioManager.AUDIOFOCUS_GAIN -> {
                musicPlaying = false
                if (paused && callHeld == null) {
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
        appCtx = ctx.applicationContext
        paused = false
        callHeld = null
        busyChecks = 0
        clearChecks = 0
        callCheckAt = SystemClock.uptimeMillis() + 1500   // our own mic needs a moment to show up in Android's list
        musicPlaying = false
        musicFloor = 0.0
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

    /** v0.69 nothing that goes wrong on the mic / speaker threads may close the app: it ends the audio instead. */
    private fun micLoop(first: AudioRecord) {
        try { micLoopInner(first) } catch (t: Throwable) {
            if (running) try { onState?.invoke("audio_error", "mic ${t.javaClass.simpleName}") } catch (_: Throwable) {}
        }
    }

    private fun playLoop(first: AudioTrack) {
        try { playLoopInner(first) } catch (t: Throwable) {
            if (running) try { onState?.invoke("audio_error", "speaker ${t.javaClass.simpleName}") } catch (_: Throwable) {}
        }
    }

    // v0.136.2 while her song plays the mic hears it all the time, so Hoola never heard the end of her sentence.
    // Only her own voice, clearly louder than the music's usual level, goes through; the rest goes as silence.
    @Volatile private var musicFloor = 0.0
    private var musicOpenUntil = 0L
    private var musicCheckAt = 0L

    private fun rms(b: ByteArray): Double {
        var sum = 0.0
        var i = 0
        var count = 0
        while (i + 1 < b.size) {
            val v = ((b[i + 1].toInt() shl 8) or (b[i].toInt() and 0xff)).toShort().toDouble() / 32768.0
            sum += v * v
            count++
            i += 2
        }
        return if (count == 0) 0.0 else Math.sqrt(sum / count)
    }

    private fun musicGate(chunk: ByteArray): ByteArray {
        val now = SystemClock.uptimeMillis()
        if (now >= musicCheckAt) {
            musicCheckAt = now + 1000
            val am = manager
            if (am != null && !musicNow(am)) {
                musicPlaying = false
                musicFloor = 0.0
                return chunk
            }
        }
        val level = rms(chunk)
        val floor = if (musicFloor <= 0.0) level else musicFloor
        val loud = level > Math.max(0.03, floor * 2.5)
        if (loud) musicOpenUntil = now + 600
        else musicFloor = floor * 0.95 + level * 0.05       // learn the music's level only from non-voice chunks
        return if (now < musicOpenUntil) chunk else ByteArray(chunk.size)
    }

    private fun micLoopInner(first: AudioRecord) {
        val buf = ByteArray(CHUNK)
        var cur = first
        var failures = 0
        while (running) {
            val n = try { cur.read(buf, 0, buf.size) } catch (e: Exception) { -1 }
            if (n > 0) {
                failures = 0
                try { watchOtherCall() } catch (_: Throwable) {}
                if (!paused) {
                    var chunk = buf.copyOf(n)
                    if (musicPlaying) chunk = musicGate(chunk)
                    vadSink?.let { vs -> try { SileroVad.feed(chunk)?.let { p -> vs(p) } } catch (_: Throwable) {} }
                    sink?.invoke(chunk)
                }
            } else if (n < 0 && running) {
                // v0.142 her other call took the mic: wait for it to end instead of giving up on the microphone
                try { watchOtherCall() } catch (_: Throwable) {}
                if (callHeld != null) {
                    try { Thread.sleep(500) } catch (_: InterruptedException) { return }
                    continue
                }
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

    private fun playLoopInner(first: AudioTrack) {
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
        callHeld = null
        musicPlaying = false
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
