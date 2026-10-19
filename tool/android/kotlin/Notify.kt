package com.newtika.santosh

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build

/** All notifications the native side shows. */
object Notify {
    const val SERVICE_ID = 1717
    const val CALL_ID = 1718
    private const val MSG_BASE = 3000
    private const val MSG_SLOTS = 40
    private const val CH_SERVICE = "santosh_service"
    private const val CH_MESSAGES = "santosh_messages"
    private const val CH_ALARM = "santosh_alarm"
    private const val CH_CALL = "santosh_call_v2"

    private fun nm(ctx: Context) = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

    fun piFlags() = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0)

    fun channels(ctx: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        val m = nm(ctx)
        m.createNotificationChannel(NotificationChannel(CH_SERVICE, "Hoola background", NotificationManager.IMPORTANCE_LOW).apply {
            description = "Shows that Hoola is working while the app is closed"
            setShowBadge(false)
        })
        m.createNotificationChannel(NotificationChannel(CH_MESSAGES, "Hoola messages", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "Replies, reminders and reports from Hoola"
            enableVibration(true)
        })
        m.deleteNotificationChannel("santosh_call")
        m.createNotificationChannel(NotificationChannel(CH_CALL, "Hoola call", NotificationManager.IMPORTANCE_DEFAULT).apply {
            description = "Shows while you are on a voice call with Hoola (also on the lock screen)"
            setShowBadge(false)
            setSound(null, null)
            enableVibration(false)
            lockscreenVisibility = Notification.VISIBILITY_PUBLIC
        })
        m.createNotificationChannel(NotificationChannel(CH_ALARM, "Hoola alarms", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "Alarms and timers set by Hoola"
            setSound(
                RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM),
                AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build()
            )
            enableVibration(true)
            vibrationPattern = longArrayOf(0, 800, 400, 800)
        })
    }

    @Suppress("DEPRECATION")
    private fun builder(ctx: Context, channel: String): Notification.Builder =
        if (Build.VERSION.SDK_INT >= 26) Notification.Builder(ctx, channel) else Notification.Builder(ctx)

    fun openApp(ctx: Context, req: Int): PendingIntent {
        val i = Intent(ctx, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        return PendingIntent.getActivity(ctx, req, i, piFlags())
    }

    fun service(ctx: Context, title: String, text: String): Notification {
        channels(ctx)
        return builder(ctx, CH_SERVICE)
            .setSmallIcon(R.drawable.ic_stat_santosh)
            .setContentTitle(title)
            .setContentText(text)
            .setOngoing(true)
            .setShowWhen(false)
            .setContentIntent(openApp(ctx, 1))
            .build()
    }

    /** Ongoing notification while a voice call runs (also when the screen is locked). */
    fun call(ctx: Context): Notification {
        channels(ctx)
        val hang = Intent(ctx, CallService::class.java).setAction(CallService.ACTION_HANGUP)
        val hangPi = if (Build.VERSION.SDK_INT >= 26) PendingIntent.getForegroundService(ctx, 7, hang, piFlags())
                     else PendingIntent.getService(ctx, 7, hang, piFlags())
        val b = builder(ctx, CH_CALL)
            .setSmallIcon(R.drawable.ic_stat_santosh)
            .setContentTitle("Hoola se baat chal rahi hai")
            .setContentText("Phone lock ho tab bhi sun raha hoon")
            .setOngoing(true)
            .setUsesChronometer(true)
            .setWhen(System.currentTimeMillis())
            .setCategory(Notification.CATEGORY_CALL)
            .setVisibility(Notification.VISIBILITY_PUBLIC)
            .setContentIntent(openApp(ctx, 8))
        @Suppress("DEPRECATION")
        b.addAction(Notification.Action.Builder(0, "Call band karein", hangPi).build())
        if (Build.VERSION.SDK_INT >= 31) b.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE)
        return b.build()
    }

    @Suppress("DEPRECATION")
    fun message(ctx: Context, text: String, eventId: Long) {
        if (text.isBlank()) return
        channels(ctx)
        val clean = text.replace(Regex("[*_#`]"), "")
        val b = builder(ctx, CH_MESSAGES)
            .setSmallIcon(R.drawable.ic_stat_santosh)
            .setContentTitle("Hoola")
            .setContentText(clean)
            .setStyle(Notification.BigTextStyle().bigText(clean))
            .setAutoCancel(true)
            .setContentIntent(openApp(ctx, 2))
            .setCategory(Notification.CATEGORY_MESSAGE)
        if (Build.VERSION.SDK_INT < 26) b.setPriority(Notification.PRIORITY_HIGH).setDefaults(Notification.DEFAULT_ALL)
        nm(ctx).notify(MSG_BASE + (eventId % MSG_SLOTS).toInt(), b.build())
    }

    fun clearMessages(ctx: Context) {
        val m = nm(ctx)
        for (i in 0 until MSG_SLOTS) m.cancel(MSG_BASE + i)
    }

    @Suppress("DEPRECATION")
    fun alarm(ctx: Context, id: Int, label: String, timeText: String) {
        channels(ctx)
        val full = Intent(ctx, AlarmActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_USER_ACTION)
            .putExtra("id", id).putExtra("label", label).putExtra("time", timeText)
        val fullPi = PendingIntent.getActivity(ctx, id, full, piFlags())
        val stop = Intent(ctx, AlarmReceiver::class.java).setAction(AlarmReceiver.DISMISS).putExtra("id", id)
        val stopPi = PendingIntent.getBroadcast(ctx, id + 1, stop, piFlags())
        val b = builder(ctx, CH_ALARM)
            .setSmallIcon(R.drawable.ic_stat_santosh)
            .setContentTitle("⏰ $label")
            .setContentText("Hoola: $timeText")
            .setCategory(Notification.CATEGORY_ALARM)
            .setFullScreenIntent(fullPi, true)
            .setContentIntent(fullPi)
            .setOngoing(true)
            .addAction(Notification.Action.Builder(null, "Band karo", stopPi).build())
        if (Build.VERSION.SDK_INT >= 26) b.setTimeoutAfter(10 * 60 * 1000L)
        if (Build.VERSION.SDK_INT < 26) {
            b.setPriority(Notification.PRIORITY_MAX)
                .setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM), android.media.AudioManager.STREAM_ALARM)
                .setVibrate(longArrayOf(0, 800, 400, 800))
        }
        val n = b.build()
        n.flags = n.flags or Notification.FLAG_INSISTENT   // keeps ringing until dismissed
        nm(ctx).notify(id, n)
    }

    fun cancel(ctx: Context, id: Int) = nm(ctx).cancel(id)

    @Suppress("DEPRECATION")
    fun tapToOpen(ctx: Context, id: Int, title: String, text: String, intent: Intent) {
        channels(ctx)
        val pi = PendingIntent.getActivity(ctx, id, intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK), piFlags())
        val b = builder(ctx, CH_MESSAGES)
            .setSmallIcon(R.drawable.ic_stat_santosh)
            .setContentTitle(title)
            .setContentText(text)
            .setAutoCancel(true)
            .setContentIntent(pi)
        if (Build.VERSION.SDK_INT < 26) b.setPriority(Notification.PRIORITY_HIGH)
        nm(ctx).notify(id, b.build())
    }
}
