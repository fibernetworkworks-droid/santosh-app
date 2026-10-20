package com.newtika.santosh

import android.Manifest
import android.app.AlarmManager
import android.app.PendingIntent
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.provider.CalendarContract
import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar
import java.util.TimeZone

/** Phone actions done without opening any screen (used while the app is closed). */
object Actions {
    private val DAYS = mapOf("sun" to Calendar.SUNDAY, "mon" to Calendar.MONDAY, "tue" to Calendar.TUESDAY,
        "wed" to Calendar.WEDNESDAY, "thu" to Calendar.THURSDAY, "fri" to Calendar.FRIDAY, "sat" to Calendar.SATURDAY)

    /** Events older than [minutes] are stale (phone actions expire on the server after 15). */
    fun tooOld(at: String, minutes: Int = 15): Boolean {
        if (Build.VERSION.SDK_INT < 26 || at.isEmpty()) return false
        return try {
            val t = java.time.OffsetDateTime.parse(at).toInstant().toEpochMilli()
            System.currentTimeMillis() - t > minutes * 60 * 1000L
        } catch (_: Exception) {
            try {
                val t = java.time.LocalDateTime.parse(at).atZone(java.time.ZoneOffset.UTC).toInstant().toEpochMilli()
                System.currentTimeMillis() - t > minutes * 60 * 1000L
            } catch (_: Exception) { false }
        }
    }

    /** Returns (ok, detail for the server). */
    fun run(ctx: Context, a: JSONObject): Pair<Boolean, String> = try {
        when (a.optString("type")) {
            "set_alarm" -> alarm(ctx, a)
            "set_timer" -> timer(ctx, a)
            "add_calendar_event" -> calendar(ctx, a)
            "open_url" -> openUrl(ctx, a)
            "tv_play" -> tvPlay(ctx, a)
            else -> Pair(false, "Is app version ko '${a.optString("type")}' nahi aata; app update kijiye.")
        }
    } catch (e: Exception) {
        Pair(false, e.message ?: e.javaClass.simpleName)
    }

    /** Android won't open screens from the background, so a tap on the notification opens the link. */
    private fun openUrl(ctx: Context, a: JSONObject): Pair<Boolean, String> {
        val url = a.optString("url")
        if (!url.startsWith("http://") && !url.startsWith("https://")) return Pair(false, "Link sahi nahi hai")
        val title = a.optString("title").ifBlank { android.net.Uri.parse(url).host ?: url }
        val view = Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url))
        Notify.tapToOpen(ctx, (url.hashCode() and 0x7fffffff) % 100000 + 300_000, "Hoola: $title", "Tap karke kholiye", view)
        return Pair(true, "Notification bheja hai; tap karte hi khul jayega")
    }

    /** Hoola TV while the app is closed: a tap on the notification opens the channel in Hoola's player. */
    private fun tvPlay(ctx: Context, a: JSONObject): Pair<Boolean, String> {
        val ch = a.optString("channel")
        if (ch.isBlank()) return Pair(false, "Channel nahi mila")
        val open = Intent(ctx, MainActivity::class.java).setData(android.net.Uri.parse("santosh://tv?ch=" + android.net.Uri.encode(ch)))
        Notify.tapToOpen(ctx, (ch.hashCode() and 0x7fffffff) % 100000 + 400_000, "Hoola TV: ${a.optString("name", "channel")}",
            "Tap karke dekhiye", open)
        return Pair(true, "Notification bheja hai; tap karte hi channel chalega")
    }

    private fun hhmm(h: Int, m: Int) = String.format("%02d:%02d", h, m)

    private fun alarm(ctx: Context, a: JSONObject): Pair<Boolean, String> {
        val h = a.optInt("hour")
        val m = a.optInt("minute")
        val label = a.optString("label", "Hoola alarm").ifBlank { "Hoola alarm" }
        val days = a.optJSONArray("days") ?: JSONArray()
        val at = nextTime(h, m, days, System.currentTimeMillis())
        val id = (System.currentTimeMillis() % 1_000_000).toInt() + 10_000
        val spec = JSONObject().put("id", id).put("at", at).put("label", label).put("hour", h).put("minute", m).put("days", days)
        val exact = schedule(ctx, spec)
        val note = if (exact) "" else " (thoda aage-peeche baj sakta hai)"
        return Pair(true, "App band tha, isliye Hoola ka apna alarm ${hhmm(h, m)} par set kiya$note")
    }

    private fun timer(ctx: Context, a: JSONObject): Pair<Boolean, String> {
        val secs = a.optLong("seconds")
        if (secs <= 0) return Pair(false, "Timer ka samay sahi nahi hai")
        val label = a.optString("label", "Hoola timer").ifBlank { "Hoola timer" }
        val at = System.currentTimeMillis() + secs * 1000
        val c = Calendar.getInstance().apply { timeInMillis = at }
        val id = (System.currentTimeMillis() % 1_000_000).toInt() + 10_000
        val spec = JSONObject().put("id", id).put("at", at).put("label", label)
            .put("hour", c.get(Calendar.HOUR_OF_DAY)).put("minute", c.get(Calendar.MINUTE)).put("days", JSONArray())
        schedule(ctx, spec)
        val mins = (secs + 59) / 60
        return Pair(true, "Timer chalu: $mins minute baad bajega")
    }

    /** Next moment at h:m on one of [days] (or the next h:m when there are no days). */
    fun nextTime(h: Int, m: Int, days: JSONArray, from: Long): Long {
        val c = Calendar.getInstance().apply {
            timeInMillis = from
            set(Calendar.HOUR_OF_DAY, h); set(Calendar.MINUTE, m); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
        }
        val wanted = (0 until days.length()).mapNotNull { DAYS[days.optString(it)] }.toSet()
        for (i in 0..8) {
            if (c.timeInMillis > from && (wanted.isEmpty() || c.get(Calendar.DAY_OF_WEEK) in wanted)) return c.timeInMillis
            c.add(Calendar.DAY_OF_MONTH, 1)
        }
        return c.timeInMillis
    }

    /** Arms the alarm; returns false when only an inexact alarm was allowed. */
    fun schedule(ctx: Context, spec: JSONObject): Boolean {
        Store.putAlarm(ctx, spec)
        val id = spec.getInt("id")
        val at = spec.getLong("at")
        val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val fire = Intent(ctx, AlarmReceiver::class.java).setAction(AlarmReceiver.FIRE).putExtra("id", id)
        val pi = PendingIntent.getBroadcast(ctx, id, fire, Notify.piFlags())
        val canExact = Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()
        return try {
            if (!canExact) throw SecurityException("no exact alarms")
            am.setAlarmClock(AlarmManager.AlarmClockInfo(at, Notify.openApp(ctx, id + 2)), pi)
            true
        } catch (_: SecurityException) {
            if (Build.VERSION.SDK_INT >= 23) am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi) else am.set(AlarmManager.RTC_WAKEUP, at, pi)
            false
        }
    }

    private fun calendar(ctx: Context, a: JSONObject): Pair<Boolean, String> {
        val title = a.optString("title", "Hoola").ifBlank { "Hoola" }
        val start = a.optLong("start_ms")
        val end = a.optLong("end_ms").let { if (it > start) it else start + 3600_000L }
        val granted = Build.VERSION.SDK_INT < 23 ||
            ctx.checkSelfPermission(Manifest.permission.WRITE_CALENDAR) == PackageManager.PERMISSION_GRANTED
        val calId = if (granted) writableCalendar(ctx) else null
        if (calId != null) {
            val v = ContentValues().apply {
                put(CalendarContract.Events.CALENDAR_ID, calId)
                put(CalendarContract.Events.TITLE, title)
                put(CalendarContract.Events.DTSTART, start)
                put(CalendarContract.Events.DTEND, end)
                put(CalendarContract.Events.EVENT_TIMEZONE, TimeZone.getDefault().id)
                put(CalendarContract.Events.EVENT_LOCATION, a.optString("location", ""))
                put(CalendarContract.Events.DESCRIPTION, a.optString("notes", ""))
                put(CalendarContract.Events.HAS_ALARM, 1)
            }
            val uri = ctx.contentResolver.insert(CalendarContract.Events.CONTENT_URI, v)
            val eventId = uri?.lastPathSegment?.toLongOrNull()
            if (eventId != null) {
                val r = ContentValues().apply {
                    put(CalendarContract.Reminders.EVENT_ID, eventId)
                    put(CalendarContract.Reminders.MINUTES, 15)
                    put(CalendarContract.Reminders.METHOD, CalendarContract.Reminders.METHOD_ALERT)
                }
                try { ctx.contentResolver.insert(CalendarContract.Reminders.CONTENT_URI, r) } catch (_: Exception) {}
                return Pair(true, "Calendar mein seedha save kar diya")
            }
        }
        // no calendar permission: one tap on the notification opens the filled-in calendar screen
        val insert = Intent(Intent.ACTION_INSERT).setData(CalendarContract.Events.CONTENT_URI)
            .putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, start)
            .putExtra(CalendarContract.EXTRA_EVENT_END_TIME, end)
            .putExtra(CalendarContract.Events.TITLE, title)
            .putExtra(CalendarContract.Events.EVENT_LOCATION, a.optString("location", ""))
            .putExtra(CalendarContract.Events.DESCRIPTION, a.optString("notes", ""))
        Notify.tapToOpen(ctx, (start / 1000 % 100000).toInt() + 200_000, "Calendar: $title", "Tap karke save kijiye", insert)
        return Pair(false, "Calendar permission nahi hai; notification bheja hai, tap karke save karein")
    }

    private fun writableCalendar(ctx: Context): Long? {
        val proj = arrayOf(CalendarContract.Calendars._ID, CalendarContract.Calendars.IS_PRIMARY)
        val sel = "${CalendarContract.Calendars.CALENDAR_ACCESS_LEVEL} >= ? AND ${CalendarContract.Calendars.VISIBLE} = 1"
        val args = arrayOf(CalendarContract.Calendars.CAL_ACCESS_CONTRIBUTOR.toString())
        var first: Long? = null
        ctx.contentResolver.query(CalendarContract.Calendars.CONTENT_URI, proj, sel, args, null)?.use { c ->
            while (c.moveToNext()) {
                val id = c.getLong(0)
                if (first == null) first = id
                if (c.getInt(1) == 1) return id
            }
        }
        return first
    }
}
