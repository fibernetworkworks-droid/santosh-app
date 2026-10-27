package com.newtika.santosh

import android.content.Context
import android.content.Intent
import android.os.Build

/** v0.70 The one safe way Hoola starts its services.
 *  Android's startForegroundService() is a promise: the service MUST reach startForeground() within seconds, or Android
 *  kills the whole app ("did not then call startForeground"), and Android 14 refuses startForeground for a microphone
 *  service whenever Hoola is not on screen. So: while Hoola is on screen, a plain start (no promise; the service still
 *  goes foreground itself, and a refusal costs only the notification, never the app). From the background only
 *  services Android allows there get the foreground start; a microphone service on Android 14+ waits for the app. */
object FgStart {
    fun launch(ctx: Context, i: Intent, microphone: Boolean = false): Boolean {
        if (Build.VERSION.SDK_INT < 26) {
            return try { ctx.startService(i); true } catch (_: Exception) { false }
        }
        if (MainActivity.visible) {
            try { ctx.startService(i); return true } catch (_: Exception) {}
        }
        if (microphone && Build.VERSION.SDK_INT >= 34) return false
        return try { ctx.startForegroundService(i); true } catch (_: Exception) { false }
    }
}
