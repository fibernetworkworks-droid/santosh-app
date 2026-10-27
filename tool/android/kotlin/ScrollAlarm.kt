package com.newtika.santosh

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import java.util.Calendar

/** v0.58 Scroll alerts in the background: a gentle notification when today's reel time reaches 80 % / 100 % of the
 *  owner's daily limit (and every 30 min past it), and one bedtime nudge after 15 min of scrolling past 11 pm.
 *  Checks are spaced by how soon the next alert could possibly be due (minutes only grow while scrolling), with a
 *  normal (inexact, non-wakeup) alarm: no exact-alarm permission, no battery cost while the phone sleeps. */
object ScrollAlarm {
    private const val PREFS = "hoola_scroll"
    private const val REQ = 7_310
    private const val NOTE_ID = 7_311

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun settings(ctx: Context): Map<String, Any> =
        mapOf("budget" to prefs(ctx).getInt("budget", 0), "bedtime" to prefs(ctx).getBoolean("bedtime", false),
              "yt_pct" to prefs(ctx).getInt("yt_pct", -1))

    fun configure(ctx: Context, budget: Int?, bedtime: Boolean?, ytShortsPct: Int? = null) {
        val e = prefs(ctx).edit()
        if (ytShortsPct != null) e.putInt("yt_pct", ytShortsPct.coerceIn(-1, 100))
        if (budget != null) e.putInt("budget", budget.coerceIn(0, 600))
        if (bedtime != null) e.putBoolean("bedtime", bedtime)
        e.apply()
        restore(ctx)
    }

    /** After boot / app start / a settings change. */
    fun restore(ctx: Context) {
        val p = prefs(ctx)
        if (p.getInt("budget", 0) > 0 || p.getBoolean("bedtime", false)) schedule(ctx, 60_000L) else cancel(ctx)
    }

    private fun pi(ctx: Context): PendingIntent {
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0)
        return PendingIntent.getBroadcast(ctx, REQ, Intent(ctx, ScrollAlarmReceiver::class.java), flags)
    }

    private fun schedule(ctx: Context, delayMs: Long) {
        val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        am.set(AlarmManager.RTC, System.currentTimeMillis() + delayMs, pi(ctx))
    }

    private fun cancel(ctx: Context) {
        (ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager).cancel(pi(ctx))
    }

    private fun hm(m: Int) = if (m < 60) "$m min" else if (m % 60 == 0) "${m / 60} ghante" else "${m / 60}h ${m % 60}m"

    private fun alert(ctx: Context, title: String, text: String) {
        val open = Intent(ctx, MainActivity::class.java).setData(android.net.Uri.parse("santosh://scroll"))
        Notify.tapToOpen(ctx, NOTE_ID, title, text, open)
    }

    /** One check: alert if due, then plan the next check. */
    fun check(ctx: Context) {
        val p = prefs(ctx)
        val budget = p.getInt("budget", 0)
        val bedtime = p.getBoolean("bedtime", false)
        if (budget <= 0 && !bedtime) { cancel(ctx); return }
        if (!ScrollStats.allowed(ctx)) { schedule(ctx, 6 * 3600_000L); return }   // Usage access was turned off
        val now = Calendar.getInstance()
        val today = "%04d-%02d-%02d".format(now.get(Calendar.YEAR), now.get(Calendar.MONTH) + 1, now.get(Calendar.DAY_OF_MONTH))
        val days = ScrollStats.collect(ctx, 2)
        val d = days.firstOrNull { it["date"] == today }
        @Suppress("UNCHECKED_CAST")
        val apps = (d?.get("apps") as? Map<String, Map<String, Any>>) ?: emptyMap()
        // YouTube counts only its Shorts part when the owner's history told us the share (-1 = unknown: all of it)
        val yt = p.getInt("yt_pct", -1)
        val used = apps.entries.sumOf { (k, v) ->
            ((v["min"] as? Number)?.toDouble() ?: 0.0) * (if (k == "YouTube" && yt in 0..100) yt / 100.0 else 1.0)
        }.toInt()
        val top = apps.maxByOrNull { (it.value["min"] as? Number)?.toDouble() ?: 0.0 }?.key ?: "reels"
        var nextMin = 30.0
        if (budget > 0) {
            val sent = p.getInt("sent_$today", 0)                 // highest threshold already alerted (minutes)
            val levels = mutableListOf((budget * 0.8).toInt(), budget)
            var x = budget + 30
            while (x <= used + 30) { levels.add(x); x += 30 }
            val due = levels.filter { it in (sent + 1)..used }.maxOrNull()
            if (due != null) {
                p.edit().putInt("sent_$today", due).apply()
                when {
                    due < budget -> alert(ctx, "Aaj ${hm(used)} reels ho gayi",
                        "Aapki roz ki limit ${hm(budget)} hai: bas ${hm(budget - used)} bachi. ($top sabse zyada)")
                    due == budget -> alert(ctx, "Aaj ki reel limit poori 🙂",
                        "${hm(used)} ho gaye ($top sabse zyada). Thoda break lijiye: paani, stretch, ya kisi se baat?")
                    else -> alert(ctx, "Limit se ${hm(used - budget)} zyada",
                        "Aaj ${hm(used)} reels. Phone rakh kar 5 minute aankhon ko aaram dijiye.")
                }
            }
            val nextLevel = levels.filter { it > maxOf(used, p.getInt("sent_$today", 0)) }.minOrNull() ?: (used + 30)
            nextMin = (nextLevel - used).toDouble()
        }
        if (bedtime) {
            val h = now.get(Calendar.HOUR_OF_DAY)
            @Suppress("UNCHECKED_CAST")
            val hours = (d?.get("hours") as? List<Number>)?.map { it.toDouble() } ?: emptyList()
            // tonight after 11 pm (today's 23:00 hour, or after midnight: yesterday 23:00 + today 0..4)
            val night = if (h >= 23) hours.getOrElse(23) { 0.0 } else if (h < 5) {
                @Suppress("UNCHECKED_CAST")
                val y = (days.firstOrNull { it["date"] != today }?.get("hours") as? List<Number>)?.map { it.toDouble() } ?: emptyList()
                y.getOrElse(23) { 0.0 } + (0 until 5).sumOf { hours.getOrElse(it) { 0.0 } }
            } else 0.0
            val start = (now.clone() as Calendar).apply { if (h < 5) add(Calendar.DAY_OF_YEAR, -1) }
            val nightKey = "%04d-%02d-%02d".format(start.get(Calendar.YEAR), start.get(Calendar.MONTH) + 1, start.get(Calendar.DAY_OF_MONTH))
            if (night >= 15 && !p.getBoolean("bed_$nightKey", false)) {
                p.edit().putBoolean("bed_$nightKey", true).apply()
                alert(ctx, "Raat ho gayi 😴", "11 baje ke baad ${hm(night.toInt())} scroll ho gaya. Kal ke liye neend bachaiye: phone side mein rakh dijiye.")
            }
            nextMin = minOf(nextMin, if (h in 22..23 || h < 5) 15.0 else 60.0)
        }
        // old per-day keys: keep the file small
        p.all.keys.filter { (it.startsWith("sent_") || it.startsWith("bed_")) && !it.endsWith(today) }.let { old ->
            if (old.size > 6) {
                val e = p.edit()
                old.forEach { e.remove(it) }
                e.apply()
            }
        }
        schedule(ctx, (nextMin.coerceIn(5.0, 60.0) * 60_000).toLong())
    }
}

class ScrollAlarmReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        val done = goAsync()
        Thread {
            try { ScrollAlarm.check(ctx.applicationContext) } catch (_: Exception) {} finally { done.finish() }
        }.start()
    }
}
