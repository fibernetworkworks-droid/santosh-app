package com.newtika.santosh

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log

/** Foreground service that keeps "Hoola Remote" (Bluetooth TV remote) registered while the app is in the background.
 *  Started only from the Ghar screen after the user allowed "Nearby devices". */
class RemoteService : Service() {
    companion object {
        private const val NOTIFICATION_ID = 1101
        @Volatile var running = false

        fun start(ctx: Context): String {
            if (Build.VERSION.SDK_INT < 28) return "TV remote needs Android 9 or newer."
            if (!HomeDevices.hasBluetoothPermission(ctx)) return "permission"
            val i = Intent(ctx, RemoteService::class.java)
            if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i) else ctx.startService(i)
            running = true
            return "ok"
        }

        fun stop(ctx: Context) {
            running = false
            ctx.stopService(Intent(ctx, RemoteService::class.java))
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val n = Notify.service(this, "Hoola TV remote on", "Hoola aapka TV remote hai")
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(NOTIFICATION_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE)
            } else {
                startForeground(NOTIFICATION_ID, n)
            }
        } catch (e: Exception) {   // permission revoked meanwhile (Android 14 checks it here)
            Log.w(HomeDevices.TAG, "remote service could not start", e)
            running = false
            stopSelf()
            return START_NOT_STICKY
        }
        if (Build.VERSION.SDK_INT >= 28) {
            try {
                HidRemote.get(this).start()
            } catch (e: Exception) {
                Log.w(HomeDevices.TAG, "HID start failed", e)
                running = false
                stopSelf()
                return START_NOT_STICKY
            }
        }
        running = true
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
        if (Build.VERSION.SDK_INT >= 28) HidRemote.get(this).stop()
        super.onDestroy()
    }
}
