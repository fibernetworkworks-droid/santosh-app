package com.newtika.santosh

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** v0.70 "Call band karein" in the call notification. A broadcast, not a service start: tapping it from the lock
 *  screen can never trip Android's foreground-service rules. */
class CallHangupReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        try { CallService.onHangup?.invoke() } catch (_: Throwable) {}
        try { VoiceAudio.stop(ctx.applicationContext) } catch (_: Throwable) {}
        try { CallService.stop(ctx.applicationContext) } catch (_: Throwable) {}
        CrashGuard.markCall(ctx.applicationContext, false)
    }
}
