package com.newtika.santosh

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * "Hey Santosh": listens for the wake word on the phone itself (Santosh Wake, our own on-device model — no audio
 * leaves the phone until you start talking to Santosh, and no licence keys). Works with the screen off and locked.
 * Android requires a visible "mic in use" notification for this; the user can switch it off any time.
 */
class WakeService : Service() {
    companion object {
        const val CH_WAKE = "santosh_wake"
        const val CH_HEARD = "santosh_heard"
        const val NOTE_ID = 7101
        const val HEARD_ID = 7102
        const val ACTION_RESUME = "santosh.WAKE_RESUME"
        const val ACTION_PAUSE = "santosh.WAKE_PAUSE"
        const val ACTION_WAKE = "santosh.WAKE"
        @Volatile var running = false
        @Volatile var status = ""

        fun start(ctx: Context) {
            ctx.getSharedPreferences("santosh_native", Context.MODE_PRIVATE).edit().putBoolean("wake_on", true).apply()
            val i = Intent(ctx, WakeService::class.java)
            if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i) else ctx.startService(i)
        }

        fun stop(ctx: Context) {
            ctx.getSharedPreferences("santosh_native", Context.MODE_PRIVATE).edit().putBoolean("wake_on", false).apply()
            ctx.stopService(Intent(ctx, WakeService::class.java))
        }

        fun resume(ctx: Context) {
            if (!running) return
            ctx.startService(Intent(ctx, WakeService::class.java).setAction(ACTION_RESUME))
        }

        /** A voice call is starting: give the microphone to the call. */
        fun pauseFor(ctx: Context) {
            if (!running) return
            ctx.startService(Intent(ctx, WakeService::class.java).setAction(ACTION_PAUSE))
        }

        fun wanted(ctx: Context) = ctx.getSharedPreferences("santosh_native", Context.MODE_PRIVATE).getBoolean("wake_on", false)
    }

    private var engine: WakeEngine? = null
    private val main = Handler(Looper.getMainLooper())
    private val fallbackResume = Runnable { listen() }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        channels()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val n = note("“Hey Santosh” sun raha hai", "Mic sirf wake word ke liye, phone par hi. Band karne ke liye Hoola app kholiye.")
        try {
            if (Build.VERSION.SDK_INT >= 30) startForeground(NOTE_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
            else startForeground(NOTE_ID, n)
        } catch (e: Exception) {
            // Android 14+: a microphone service can only start while the app is on screen
            status = "Hoola app ek baar kholiye, phir 'Hey Santosh' chalu hoga"
            running = false
            stopSelf()
            return START_NOT_STICKY
        }
        running = true
        if (intent?.action == ACTION_PAUSE) {
            pause()
            main.removeCallbacks(fallbackResume)
            main.postDelayed(fallbackResume, 30 * 60_000L)   // safety: a forgotten call never mutes it for good
            status = "Call chal rahi hai"
        } else if (intent?.action == ACTION_RESUME) {
            main.removeCallbacks(fallbackResume)
            listen()
        } else if (engine == null) {
            Thread({ prepareAndListen() }, "santosh-wake-setup").start()
        }
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
        main.removeCallbacks(fallbackResume)
        release()
        super.onDestroy()
    }

    /** Load the "Hey Santosh" model: the server may send a newer one; otherwise the one built into the app. */
    private fun prepareAndListen() {
        var threshold = 0.5f
        var model: ByteArray? = null
        try {
            val server = Store.server(this).trimEnd('/')
            val key = Store.key(this)
            if (server.isNotEmpty()) {
                val cfg = JSONObject(get("$server/api/wake", key).toString(Charsets.UTF_8))
                threshold = cfg.optDouble("threshold", 0.5).toFloat()
                if (cfg.optBoolean("custom_model")) {
                    val ver = cfg.optString("version", "1")
                    val f = File(filesDir, "hey_santosh_$ver.onnx")
                    if (!f.exists()) {
                        filesDir.listFiles()?.filter { it.name.startsWith("hey_santosh_") }?.forEach { it.delete() }
                        f.writeBytes(get("$server/api/wake/keyword", key))
                    }
                    model = f.readBytes()
                }
            }
        } catch (_: Exception) {
            // offline or old server: the built-in model still works
        }
        try {
            val bytes = model ?: WakeEngine.asset(this, "hey_santosh.onnx")
            val t = threshold.coerceIn(0.2f, 0.95f)
            main.post { build(bytes, t) }
        } catch (e: Exception) {
            status = "Wake model nahi mila: ${e.message ?: e.javaClass.simpleName}"
            main.post { stopSelf() }
        }
    }

    private fun get(url: String, key: String): ByteArray {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = 15000
        c.readTimeout = 30000
        if (key.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $key")
        try {
            if (c.responseCode >= 400) throw RuntimeException("server ${c.responseCode}")
            return c.inputStream.use { it.readBytes() }
        } finally {
            c.disconnect()
        }
    }

    private fun build(model: ByteArray, threshold: Float) {
        try {
            engine = WakeEngine(applicationContext, model, threshold) { _ -> main.post { onWake() } }
            listen()
        } catch (e: Exception) {
            status = "Wake word chalu nahi hua: ${e.message}"
            stopSelf()
        }
    }

    private fun listen() {
        val e = engine ?: return
        status = if (e.start()) "Sun raha hai: “Hey Santosh”" else e.lastError
    }

    private fun pause() {
        engine?.stop()
    }

    private fun release() {
        engine?.close()
        engine = null
    }

    /** Heard "Hey Santosh": free the mic for the call, buzz, and bring Santosh up (over the lock screen too). */
    private fun onWake() {
        pause()
        try {
            val v = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            if (Build.VERSION.SDK_INT >= 26) v.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 60, 80, 60), -1))
        } catch (_: Exception) {}
        val open = Intent(this, MainActivity::class.java)
            .setAction(ACTION_WAKE)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
        val pi = PendingIntent.getActivity(this, 7103, open, Notify.piFlags())
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val b = builder(CH_HEARD)
            .setSmallIcon(R.drawable.ic_stat_santosh)
            .setContentTitle("Haan ji, boliye…")
            .setContentText("Hoola sun raha hai")
            .setCategory(Notification.CATEGORY_CALL)
            .setFullScreenIntent(pi, true)
            .setContentIntent(pi)
            .setAutoCancel(true)
        if (Build.VERSION.SDK_INT >= 26) b.setTimeoutAfter(20000)
        nm.notify(HEARD_ID, b.build())
        if (MainActivity.visible) {
            try { startActivity(open) } catch (_: Exception) {}
        }
        // if the call never starts (dismissed), go back to listening after a while
        main.removeCallbacks(fallbackResume)
        main.postDelayed(fallbackResume, 90_000)
    }

    @Suppress("DEPRECATION")
    private fun builder(ch: String): Notification.Builder =
        if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, ch) else Notification.Builder(this)

    private fun note(title: String, text: String): Notification =
        builder(CH_WAKE)
            .setSmallIcon(R.drawable.ic_stat_santosh)
            .setContentTitle(title)
            .setContentText(text)
            .setOngoing(true)
            .setContentIntent(Notify.openApp(this, 7104))
            .build()

    private fun channels() {
        if (Build.VERSION.SDK_INT < 26) return
        val m = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        m.createNotificationChannel(NotificationChannel(CH_WAKE, "Hey Santosh (wake word)", NotificationManager.IMPORTANCE_MIN).apply {
            description = "Shows that Hoola is listening for “Hey Santosh” on this phone"
            setShowBadge(false)
        })
        m.createNotificationChannel(NotificationChannel(CH_HEARD, "Hoola ne suna", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "Opens Hoola when you say “Hey Santosh”"
            setSound(null, null)
        })
    }
}
