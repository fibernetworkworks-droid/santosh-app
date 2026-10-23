package com.newtika.santosh

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaRecorder
import android.os.Build

/**
 * v0.142 Is she on ANOTHER call right now (a normal phone call, or a WhatsApp / Meet / any VoIP call)?
 *
 * Before: only a normal phone call (MODE_IN_CALL) paused Hoola, and 3 s later Hoola took the audio back. A WhatsApp call
 * keeps the phone in MODE_IN_COMMUNICATION - the same mode Hoola uses - so Hoola grabbed the audio back and answered
 * what she said to her friend. Now we look at what Android lets every app see, with no extra permission (no
 * READ_PHONE_STATE, no call log):
 *  - the audio mode: in a call / ringing / call screening = "phone";
 *  - a ringtone playing (an incoming WhatsApp / phone call rings) = "ringing";
 *  - Hoola's own microphone silenced by Android (Android 10+: another call app took the mic) = "voip";
 *  - another app recording with the call-voice source (VoIP) = "voip";
 *  - not in a Hoola call and the phone is in communication mode = "voip" (someone else's VoIP call).
 * Every check is wrapped: a phone that refuses one of them just answers null for it.
 */
object CallWatch {

    /** null when she is free, else "phone" | "ringing" | "voip". `ourSession` = Hoola's own mic session (in a call). */
    fun busy(ctx: Context, ourCall: Boolean = false, ourSession: Int = 0): String? {
        val am = try { ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager } catch (_: Throwable) { return null }
        val mode = try { am.mode } catch (_: Throwable) { AudioManager.MODE_NORMAL }
        if (mode == AudioManager.MODE_IN_CALL) return "phone"
        if (mode == AudioManager.MODE_RINGTONE) return "ringing"
        if (Build.VERSION.SDK_INT >= 30 && mode == AudioManager.MODE_CALL_SCREENING) return "phone"
        if (!ourCall && mode == AudioManager.MODE_IN_COMMUNICATION) return "voip"
        if (Build.VERSION.SDK_INT >= 26) {
            try {
                for (p in am.activePlaybackConfigurations) {
                    if (p.audioAttributes.usage == AudioAttributes.USAGE_NOTIFICATION_RINGTONE) return "ringing"
                }
            } catch (_: Throwable) {}
        }
        if (Build.VERSION.SDK_INT >= 24) {
            try {
                var voiceRecorders = 0
                for (r in am.activeRecordingConfigurations) {
                    val mine = ourCall && ourSession != 0 && r.clientAudioSessionId == ourSession
                    if (mine) {
                        // Android 10+: our mic is silenced when another (call) app has taken it
                        if (Build.VERSION.SDK_INT >= 29 && r.isClientSilenced) return "voip"
                        continue
                    }
                    if (r.clientAudioSource == MediaRecorder.AudioSource.VOICE_COMMUNICATION) voiceRecorders++
                }
                if (voiceRecorders > 0) return "voip"
            } catch (_: Throwable) {}
        }
        return null
    }
}
