package com.newtika.santosh

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.media.audiofx.AcousticEchoCanceler
import android.media.audiofx.AutomaticGainControl
import android.media.audiofx.NoiseSuppressor
import android.os.Build
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

/**
 * Full-duplex call audio for the Baat tab: the mic keeps listening while Santosh talks.
 * Uses the phone's call path (VOICE_COMMUNICATION) so hardware echo cancellation removes
 * Santosh's own voice from the mic, which is what lets you interrupt him naturally.
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

    /** Receives mic chunks; set by the activity's EventChannel. */
    @Volatile var sink: ((ByteArray) -> Unit)? = null

    fun hasPermission(ctx: Context) = Build.VERSION.SDK_INT < 23 ||
        ctx.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    /** Returns null when started, or a short reason. */
    @Synchronized
    fun start(ctx: Context): String? {
        if (running) return null
        if (!hasPermission(ctx)) return "permission"
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        am.mode = AudioManager.MODE_IN_COMMUNICATION
        route(am)

        val minIn = AudioRecord.getMinBufferSize(IN_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val r = try {
            AudioRecord(MediaRecorder.AudioSource.VOICE_COMMUNICATION, IN_RATE, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT, maxOf(minIn, CHUNK * 4))
        } catch (e: SecurityException) {
            return "permission"
        }
        if (r.state != AudioRecord.STATE_INITIALIZED) {
            r.release()
            am.mode = AudioManager.MODE_NORMAL
            return "Microphone shuru nahi ho paya"
        }
        val sid = r.audioSessionId
        if (AcousticEchoCanceler.isAvailable()) aec = AcousticEchoCanceler.create(sid)?.apply { enabled = true }
        if (NoiseSuppressor.isAvailable()) ns = NoiseSuppressor.create(sid)?.apply { enabled = true }
        if (AutomaticGainControl.isAvailable()) agc = AutomaticGainControl.create(sid)?.apply { enabled = true }

        val minOut = AudioTrack.getMinBufferSize(OUT_RATE, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val t = AudioTrack.Builder()
            .setAudioAttributes(AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            .setAudioFormat(AudioFormat.Builder().setSampleRate(OUT_RATE)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
            .setBufferSizeInBytes(maxOf(minOut * 2, 9600))
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build()
        record = r
        track = t
        queue.clear()
        running = true
        t.play()
        r.startRecording()

        micThread = Thread({
            val buf = ByteArray(CHUNK)
            while (running) {
                val n = r.read(buf, 0, buf.size)
                if (n > 0) sink?.invoke(buf.copyOf(n))
            }
        }, "santosh-mic").also { it.priority = Thread.MAX_PRIORITY; it.start() }

        playThread = Thread({
            while (running) {
                val chunk = try { queue.poll(200, TimeUnit.MILLISECONDS) } catch (_: InterruptedException) { null } ?: continue
                val gen = generation
                var off = 0
                while (running && off < chunk.size && gen == generation) {
                    val w = t.write(chunk, off, minOf(chunk.size - off, 4800))
                    if (w <= 0) break
                    off += w
                }
            }
        }, "santosh-speaker").also { it.priority = Thread.MAX_PRIORITY; it.start() }
        return null
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
        if (running) queue.offer(data)
    }

    /** Stop his current sentence at once (you interrupted). */
    fun flush() {
        generation++
        queue.clear()
        track?.let {
            try { it.pause(); it.flush(); it.play() } catch (_: Exception) {}
        }
    }

    @Synchronized
    fun stop(ctx: Context) {
        if (!running && record == null) return
        running = false
        generation++
        queue.clear()
        try { micThread?.join(300) } catch (_: InterruptedException) {}
        try { playThread?.join(300) } catch (_: InterruptedException) {}
        try { record?.stop() } catch (_: Exception) {}
        record?.release()
        try { track?.stop() } catch (_: Exception) {}
        track?.release()
        aec?.release(); ns?.release(); agc?.release()
        record = null; track = null; aec = null; ns = null; agc = null
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        if (Build.VERSION.SDK_INT >= 31) {
            am.clearCommunicationDevice()
        } else {
            @Suppress("DEPRECATION")
            am.isSpeakerphoneOn = false
        }
        am.mode = AudioManager.MODE_NORMAL
    }
}
