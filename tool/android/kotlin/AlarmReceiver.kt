package com.newtika.santosh

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Rings Santosh's own alarms and timers; re-arms repeating ones. */
class AlarmReceiver : BroadcastReceiver() {
    companion object {
        const val FIRE = "com.newtika.santosh.ALARM_FIRE"
        const val DISMISS = "com.newtika.santosh.ALARM_DISMISS"
    }

    override fun onReceive(ctx: Context, intent: Intent) {
        val id = intent.getIntExtra("id", 0)
        when (intent.action) {
            DISMISS -> Notify.cancel(ctx, id)
            FIRE -> {
                val spec = Store.alarms(ctx).firstOrNull { it.optInt("id") == id } ?: return
                val h = spec.optInt("hour")
                val m = spec.optInt("minute")
                Notify.alarm(ctx, id, spec.optString("label", "Santosh alarm"), String.format("%02d:%02d", h, m))
                val days = spec.optJSONArray("days")
                if (days != null && days.length() > 0) {
                    spec.put("at", Actions.nextTime(h, m, days, System.currentTimeMillis() + 60_000L))
                    Actions.schedule(ctx, spec)
                } else {
                    Store.removeAlarm(ctx, id)
                }
            }
        }
    }
}
