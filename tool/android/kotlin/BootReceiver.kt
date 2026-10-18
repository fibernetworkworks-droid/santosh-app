package com.newtika.santosh

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** After a restart or an app update: re-arm Santosh's alarms and bring the background service back. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        val now = System.currentTimeMillis()
        for (spec in Store.alarms(ctx)) {
            val days = spec.optJSONArray("days")
            val repeating = days != null && days.length() > 0
            when {
                spec.optLong("at") > now -> Actions.schedule(ctx, spec)
                repeating -> { spec.put("at", Actions.nextTime(spec.optInt("hour"), spec.optInt("minute"), days!!, now)); Actions.schedule(ctx, spec) }
                else -> Store.removeAlarm(ctx, spec.optInt("id"))
            }
        }
        if (Store.enabled(ctx) && Store.server(ctx).isNotEmpty()) {
            try { SantoshService.start(ctx) } catch (_: Exception) {}
        }
    }
}
