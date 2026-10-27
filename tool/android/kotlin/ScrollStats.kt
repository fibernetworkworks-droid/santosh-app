package com.newtika.santosh

import android.app.AppOpsManager
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Process
import android.provider.Settings
import java.util.Calendar

/** v0.55 Reel scroll analysis: how long the owner spends in reel apps, from Android's own Usage Access (the owner turns
 *  it on in Settings). Only times are read: never what is on the screen, never other apps' content. */
object ScrollStats {
    val APPS = linkedMapOf(
        "com.instagram.android" to "Instagram",
        "com.instagram.lite" to "Instagram",
        "com.google.android.youtube" to "YouTube",
        "com.facebook.katana" to "Facebook",
        "com.facebook.lite" to "Facebook",
        "com.snapchat.android" to "Snapchat",
        "in.mohalla.video" to "Moj",
        "com.eterno.shortvideos" to "Josh",
        "in.mohalla.sharechat" to "ShareChat",
        "com.zhiliaoapp.musically" to "TikTok",
    )
    private const val RESUMED = 1        // ACTIVITY_RESUMED / MOVE_TO_FOREGROUND
    private const val PAUSED = 2         // ACTIVITY_PAUSED / MOVE_TO_BACKGROUND
    private const val STOPPED = 23       // ACTIVITY_STOPPED (Android 10+)
    private const val SCREEN_OFF = 16    // SCREEN_NON_INTERACTIVE
    private const val KEYGUARD = 17      // KEYGUARD_SHOWN
    private const val MERGE_MS = 30_000L // a gap under 30 s is the same sitting

    fun allowed(ctx: Context): Boolean {
        val ops = ctx.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = if (Build.VERSION.SDK_INT >= 29)
            ops.unsafeCheckOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), ctx.packageName)
        else @Suppress("DEPRECATION") ops.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), ctx.packageName)
        return mode == AppOpsManager.MODE_ALLOWED
    }

    fun openSettings(ctx: Context) {
        val i = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        try {
            ctx.startActivity(Intent(i).setData(Uri.parse("package:${ctx.packageName}")))
        } catch (_: Exception) {
            ctx.startActivity(i)
        }
    }

    private class Span(val app: String, var start: Long, var end: Long)

    /** Per local day: minutes / sittings / longest sitting per app, minutes per hour (24), late-night minutes. */
    fun collect(ctx: Context, days: Int): List<Map<String, Any>> {
        if (!allowed(ctx)) return emptyList()
        val usm = ctx.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val cal = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
            add(Calendar.DAY_OF_YEAR, -(days.coerceIn(1, 14) - 1))
        }
        val from = cal.timeInMillis
        val to = System.currentTimeMillis()
        val events = usm.queryEvents(from, to)
        val ev = android.app.usage.UsageEvents.Event()
        val open = HashMap<String, Long>()          // package -> foreground since
        val raw = ArrayList<Span>()
        while (events.hasNextEvent()) {
            events.getNextEvent(ev)
            val t = ev.timeStamp
            when (ev.eventType) {
                SCREEN_OFF, KEYGUARD -> {
                    for ((p, s) in open) raw.add(Span(APPS[p]!!, s, t))
                    open.clear()
                }
                RESUMED -> if (APPS.containsKey(ev.packageName) && !open.containsKey(ev.packageName)) open[ev.packageName] = t
                PAUSED, STOPPED -> open.remove(ev.packageName)?.let { s -> raw.add(Span(APPS[ev.packageName]!!, s, t)) }
            }
        }
        for ((p, s) in open) raw.add(Span(APPS[p]!!, s, to))
        // join the pieces of one sitting (activity switches, a quick notification) per app
        raw.sortWith(compareBy({ it.app }, { it.start }))
        val spans = ArrayList<Span>()
        for (s in raw) {
            if (s.end <= s.start) continue
            val last = spans.lastOrNull()
            if (last != null && last.app == s.app && s.start - last.end <= MERGE_MS) last.end = maxOf(last.end, s.end)
            else spans.add(Span(s.app, s.start, s.end))
        }
        val out = LinkedHashMap<String, MutableMap<String, Any>>()
        val day = Calendar.getInstance()
        fun key(ms: Long): String {
            day.timeInMillis = ms
            return "%04d-%02d-%02d".format(day.get(Calendar.YEAR), day.get(Calendar.MONTH) + 1, day.get(Calendar.DAY_OF_MONTH))
        }
        @Suppress("UNCHECKED_CAST")
        fun dayMap(k: String) = out.getOrPut(k) {
            mutableMapOf("date" to k, "apps" to LinkedHashMap<String, MutableMap<String, Double>>(), "hours" to DoubleArray(24))
        }
        for (s in spans) {
            // the sitting counts on the day it started; minutes are split over the hours they fall in
            @Suppress("UNCHECKED_CAST")
            val apps = dayMap(key(s.start))["apps"] as LinkedHashMap<String, MutableMap<String, Double>>
            val a = apps.getOrPut(s.app) { mutableMapOf("min" to 0.0, "sessions" to 0.0, "longest" to 0.0) }
            val mins = (s.end - s.start) / 60000.0
            a["min"] = a["min"]!! + mins
            a["sessions"] = a["sessions"]!! + 1
            a["longest"] = maxOf(a["longest"]!!, mins)
            var t = s.start
            while (t < s.end) {
                day.timeInMillis = t
                val h = day.get(Calendar.HOUR_OF_DAY)
                day.set(Calendar.MINUTE, 0); day.set(Calendar.SECOND, 0); day.set(Calendar.MILLISECOND, 0)
                day.add(Calendar.HOUR_OF_DAY, 1)
                val next = minOf(day.timeInMillis, s.end)
                @Suppress("UNCHECKED_CAST")
                val hours = dayMap(key(t))["hours"] as DoubleArray
                hours[h] += (next - t) / 60000.0
                t = next
            }
        }
        return out.values.map { d ->
            @Suppress("UNCHECKED_CAST")
            val apps = (d["apps"] as Map<String, Map<String, Double>>).mapValues { (_, v) ->
                mapOf("min" to Math.round(v["min"]!! * 10) / 10.0, "sessions" to v["sessions"]!!.toInt(),
                      "longest" to Math.round(v["longest"]!! * 10) / 10.0)
            }
            mapOf("date" to d["date"]!!, "apps" to apps,
                  "hours" to (d["hours"] as DoubleArray).map { Math.round(it * 10) / 10.0 })
        }
    }
}
