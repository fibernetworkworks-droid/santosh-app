package com.newtika.santosh

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager

/**
 * Keeps a live voice call with Santosh going when the screen locks or another app is opened.
 *
 * Android only lets an app use the microphone in the background while it runs a foreground service of type
 * "microphone" that the user started and can see. The call starts this service (always while the app is open,
 * as Android 14+ requires) and stops it when the call ends. The ongoing notification shows the call and has a
 * "Call band karein" button. A partial wake lock + Wi-Fi lock keep the audio stream smooth with the screen off.
 */
class CallService : Service() {
    companion object {
        const val ACTION_HANGUP = "com.newtika.santosh.CALL_HANGUP"
        @Volatile var running = false
        /** Why the lock-screen keep-alive isn't on ("" = fine); shown in the app. */
        @Volatile var problem = ""
        /** Set by MainActivity: ends the call in Flutter when the notification button is pressed. */
        @Volatile var onHangup: (() -> Unit)? = null

        fun start(ctx: Context) {
            if (running) return
            val i = Intent(ctx, CallService::class.java)
            try {
                if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i) else ctx.startService(i)
                running = true
                problem = ""
            } catch (e: Exception) {
                // e.g. not allowed right now; the call still works while the app stays open
                problem = "start: ${e.javaClass.simpleName}: ${e.message ?: ""}".take(200)
            }
        }

        fun stop(ctx: Context) {
            if (!running) return
            running = false
            try { ctx.stopService(Intent(ctx, CallService::class.java)) } catch (_: Exception) {}
        }
    }

    private var wake: PowerManager.WakeLock? = null
    private var wifi: WifiManager.WifiLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val n = Notify.call(this)
        try {
            if (Build.VERSION.SDK_INT >= 30) {
                startForeground(Notify.CALL_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
            } else {
                startForeground(Notify.CALL_ID, n)
            }
        } catch (e: Exception) {
            problem = "foreground: ${e.javaClass.simpleName}: ${e.message ?: ""}".take(200)
            running = false
            stopSelf()
            return START_NOT_STICKY
        }
        if (intent?.action == ACTION_HANGUP) {
            onHangup?.invoke()
            VoiceAudio.stop(this)
            running = false
            stopSelf()
            return START_NOT_STICKY
        }
        running = true
        holdLocks()
        return START_NOT_STICKY   // a call never restarts by itself
    }

    @Suppress("DEPRECATION")
    private fun holdLocks() {
        if (wake == null) {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            wake = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "santosh:call").apply {
                setReferenceCounted(false)
                acquire(2 * 60 * 60 * 1000L)   // safety cap: 2 hours
            }
        }
        if (wifi == null) {
            val wm = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            val mode = if (Build.VERSION.SDK_INT >= 29) WifiManager.WIFI_MODE_FULL_LOW_LATENCY else WifiManager.WIFI_MODE_FULL_HIGH_PERF
            wifi = wm.createWifiLock(mode, "santosh:call").apply { setReferenceCounted(false); acquire() }
        }
    }

    override fun onDestroy() {
        running = false
        try { wake?.let { if (it.isHeld) it.release() } } catch (_: Exception) {}
        try { wifi?.let { if (it.isHeld) it.release() } } catch (_: Exception) {}
        wake = null
        wifi = null
        super.onDestroy()
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // app swiped away from recents: end the call cleanly
        onHangup?.invoke()
        VoiceAudio.stop(this)
        stopSelf()
        super.onTaskRemoved(rootIntent)
    }
}
