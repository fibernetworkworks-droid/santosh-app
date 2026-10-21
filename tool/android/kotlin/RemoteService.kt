package com.newtika.santosh

import android.app.Service
import android.bluetooth.BluetoothAdapter
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log

/**
 * Foreground service that keeps "Hoola Remote" (Bluetooth TV remote) registered while the app is in the background,
 * so the TV can re-join the phone by itself and every command finds the remote ready.
 * On by the owner's choice (Ghar > "TV remote background mein chalu rakhein", or pairing a TV); the choice is
 * remembered and restored after the app restarts or the phone reboots. Bluetooth turned off and on again
 * re-registers the remote automatically.
 */
class RemoteService : Service() {
    companion object {
        private const val NOTIFICATION_ID = 1101
        @Volatile var running = false

        private fun prefs(ctx: Context) = ctx.getSharedPreferences("hoola_bt", Context.MODE_PRIVATE)
        fun wanted(ctx: Context) = prefs(ctx).getBoolean("remote_on", false)

        fun start(ctx: Context): String {
            if (Build.VERSION.SDK_INT < 28) return "TV remote needs Android 9 or newer."
            if (!HomeDevices.hasBluetoothPermission(ctx)) return "permission"
            prefs(ctx).edit().putBoolean("remote_on", true).apply()
            if (running) return "ok"
            return try {
                val i = Intent(ctx, RemoteService::class.java)
                if (!FgStart.launch(ctx, i)) return "ok"   // not allowed right now: the remote works while the app runs
                running = true
                "ok"
            } catch (e: Exception) {   // background start not allowed right now: the remote still works while the app runs
                Log.w(HomeDevices.TAG, "remote service start", e)
                "ok"
            }
        }

        /** After an app start or a reboot: bring the remote back if the owner had it on. */
        fun restore(ctx: Context) {
            if (wanted(ctx) && !running) try { start(ctx) } catch (_: Exception) {}
        }

        fun stop(ctx: Context) {
            running = false
            prefs(ctx).edit().putBoolean("remote_on", false).apply()
            ctx.stopService(Intent(ctx, RemoteService::class.java))
        }
    }

    private val btState = object : BroadcastReceiver() {
        override fun onReceive(c: Context, i: Intent) {
            if (Build.VERSION.SDK_INT < 28) return
            when (i.getIntExtra(BluetoothAdapter.EXTRA_STATE, -1)) {
                BluetoothAdapter.STATE_ON -> try { HidRemote.get(c).start() } catch (e: Exception) { Log.w(HomeDevices.TAG, "re-register", e) }
                BluetoothAdapter.STATE_TURNING_OFF, BluetoothAdapter.STATE_OFF -> HidRemote.get(c).stop()
            }
        }
    }
    private var receiverOn = false

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
        if (!receiverOn) {
            val f = IntentFilter(BluetoothAdapter.ACTION_STATE_CHANGED)
            if (Build.VERSION.SDK_INT >= 33) registerReceiver(btState, f, Context.RECEIVER_EXPORTED) else registerReceiver(btState, f)
            receiverOn = true
        }
        if (Build.VERSION.SDK_INT >= 28) {
            // Bluetooth off right now is fine: the receiver registers the remote when it comes back on
            try { HidRemote.get(this).start() } catch (e: Exception) { Log.i(HomeDevices.TAG, "HID start later: ${e.message}") }
        }
        running = true
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
        if (receiverOn) try { unregisterReceiver(btState) } catch (_: Exception) {}
        receiverOn = false
        if (Build.VERSION.SDK_INT >= 28) HidRemote.get(this).stop()
        super.onDestroy()
    }
}
