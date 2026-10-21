package com.newtika.santosh

import android.app.Notification
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * v0.84 Galla: a shop's UPI sales without writing anything down.
 *
 * Only after the owner turns it on in Hoola AND gives notification access in Android settings herself. Only the
 * payment apps she picked are looked at (merchant apps by default: PhonePe Business, Paytm for Business, Google Pay for
 * Business, BharatPe for Business). Every other app's notification is ignored at once. A notification counts only if it
 * is a plain 'money received' alert: anything with an OTP / PIN / password, money sent, requests, failures, refunds,
 * cashback, settlements, wallet top-ups, offers, bills or daily summaries is dropped. The full text never leaves the
 * phone: only amount, time, app, the payer's first name and the last 4 digits of the reference are sent to her own
 * Hoola server. Same rules as server/app/galla/parse.py (a test keeps the word lists in step).
 */
object PayAlerts {
    private const val TAG = "HoolaGalla"
    val APPS = linkedMapOf(
        "com.phonepe.app.business" to "PhonePe Business",
        "com.paytm.business" to "Paytm for Business",
        "com.google.android.apps.nbu.paisa.merchant" to "Google Pay for Business",
        "com.bharatpe.app" to "BharatPe for Business",
        "com.phonepe.app" to "PhonePe",
        "com.google.android.apps.nbu.paisa.user" to "Google Pay",
        "net.one97.paytm" to "Paytm",
        "in.org.npci.upiapp" to "BHIM",
    )
    private val DEFAULT = setOf("com.phonepe.app.business", "com.paytm.business",
        "com.google.android.apps.nbu.paisa.merchant", "com.bharatpe.app")

    private val SECRET = Regex("""\botp\b|one[\s-]?time|pass(?:word|code)|\bm?pin\b|\bcvv\b|verification code""", RegexOption.IGNORE_CASE)
    private val NOT_CREDIT = Regex(
        """\b(sent|paid to|you paid|debited|debit|withdrawn|request(?:ed|ing)?|requests|collect request|failed|failure|""" +
        """declined|pending|refund(?:ed)?|reversed|cashback|reward|scratch|offer|win|won|bill|due|reminder|recharge|""" +
        """loan|emi|insurance|transfer(?:red)? to|kyc|settle|settled|settlement|summary|total|payments|transactions|wallet|""" +
        """statement)\b|भेजे|कटे|डेबिट|कुल""", RegexOption.IGNORE_CASE)
    private val CREDIT = Regex(
        """\b(received|receive|paid you|has paid|credited|credit of|collected|payment successful from)\b|जमा|प्राप्त|मिले|मिला|आए|आये""",
        RegexOption.IGNORE_CASE)
    private val AMOUNT = Regex("""(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)""", RegexOption.IGNORE_CASE)
    private val PAYER_FROM = Regex("""\bfrom\s+([A-Za-z][A-Za-z .'&-]{1,40})""", RegexOption.IGNORE_CASE)
    private val PAYER_BY = Regex("""\b(?:credited|paid)\b.*?\bby\s+([A-Za-z][A-Za-z .'&-]{1,40})""", RegexOption.IGNORE_CASE)
    private val PAYER_PAID = Regex("""^\s*([A-Za-z][A-Za-z .'&-]{1,40}?)\s+(?:has\s+)?paid you""", RegexOption.IGNORE_CASE)
    private val REF = Regex("""(?:utr|rrn|ref(?:erence)?(?:\s*no\.?)?|txn(?:\s*id)?|upi\s*ref(?:\.|erence)?(?:\s*no\.?)?)[\s:#.-]*([0-9]{6,})""",
        RegexOption.IGNORE_CASE)
    private val SKIP_NAMES = setOf("mr", "mrs", "ms", "shri", "smt", "dr", "upi", "via", "the")

    private fun p(ctx: Context) = ctx.getSharedPreferences("hoola_galla", Context.MODE_PRIVATE)

    fun on(ctx: Context) = p(ctx).getBoolean("on", false)
    fun apps(ctx: Context): Set<String> = p(ctx).getStringSet("apps", null) ?: DEFAULT

    fun set(ctx: Context, on: Boolean, apps: List<String>?) {
        val e = p(ctx).edit().putBoolean("on", on)
        if (apps != null) e.putStringSet("apps", apps.filter { APPS.containsKey(it) }.toSet())
        e.apply()
        if (on) flush(ctx)
    }

    fun granted(ctx: Context): Boolean {
        val flat = Settings.Secure.getString(ctx.contentResolver, "enabled_notification_listeners") ?: return false
        val me = ComponentName(ctx, HoolaPayListener::class.java).flattenToString()
        return flat.split(":").any { it == me }
    }

    fun openSettings(ctx: Context) {
        val i = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        try { ctx.startActivity(i) } catch (_: Exception) {
            ctx.startActivity(Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
    }

    fun info(ctx: Context): Map<String, Any> = mapOf(
        "on" to on(ctx), "granted" to granted(ctx), "apps" to apps(ctx).toList(),
        "pending" to JSONArray(p(ctx).getString("queue", "[]")).length(),
        "last_sent" to p(ctx).getLong("last_sent", 0L), "sent_total" to p(ctx).getInt("sent_total", 0),
        "all" to APPS.map { mapOf("package" to it.key, "label" to it.value, "business" to DEFAULT.contains(it.key)) })

    private fun firstName(raw: String): String {
        val w = raw.replace(Regex("[^A-Za-z .'-]"), " ").trim().split(Regex("\\s+"))
            .filter { it.isNotEmpty() && !SKIP_NAMES.contains(it.lowercase().trim('.')) }
        if (w.isEmpty()) return ""
        val n = w[0].take(20).lowercase()
        return n.replaceFirstChar { it.uppercase() }
    }

    /** {amount, payer, ref_tail} for a plain credit, else null. */
    fun parse(title: String, text: String): JSONObject? {
        val full = "$title $text".replace(Regex("\\s+"), " ").trim()
        if (full.isEmpty() || SECRET.containsMatchIn(full)) return null
        if (!CREDIT.containsMatchIn(full) || NOT_CREDIT.containsMatchIn(full)) return null
        val m = AMOUNT.find(full) ?: return null
        val amt = m.groupValues[1].replace(",", "").toDoubleOrNull() ?: return null
        if (amt <= 0 || amt > 200000) return null
        val pm = PAYER_PAID.find(text) ?: PAYER_PAID.find(title) ?: PAYER_FROM.find(full) ?: PAYER_BY.find(full)
        val ref = REF.find(full)?.groupValues?.get(1)?.takeLast(4) ?: ""
        return JSONObject().put("amount", amt).put("payer", pm?.let { firstName(it.groupValues[1]) } ?: "").put("ref_tail", ref)
    }

    fun onPosted(ctx: Context, sbn: StatusBarNotification) {
        if (!on(ctx)) return
        val pkg = sbn.packageName ?: return
        if (!apps(ctx).contains(pkg)) return
        val ex = sbn.notification?.extras ?: return
        if ((sbn.notification.flags and Notification.FLAG_GROUP_SUMMARY) != 0) return
        val title = ex.getCharSequence(Notification.EXTRA_TITLE)?.toString() ?: ""
        val text = (ex.getCharSequence(Notification.EXTRA_BIG_TEXT) ?: ex.getCharSequence(Notification.EXTRA_TEXT))?.toString() ?: ""
        val got = parse(title, text) ?: return
        val key = sha1("${sbn.key}|${got.optDouble("amount")}|${got.optString("ref_tail")}|${sbn.postTime / 60000}")
        got.put("app", pkg).put("at_ms", sbn.postTime).put("key", key)
        queue(ctx, got)
        flush(ctx)
    }

    private fun sha1(s: String): String =
        MessageDigest.getInstance("SHA-1").digest(s.toByteArray()).joinToString("") { "%02x".format(it) }

    @Synchronized
    private fun queue(ctx: Context, item: JSONObject) {
        val arr = JSONArray(p(ctx).getString("queue", "[]"))
        for (i in 0 until arr.length()) if (arr.getJSONObject(i).optString("key") == item.optString("key")) return
        arr.put(item)
        val out = JSONArray()
        val start = if (arr.length() > 500) arr.length() - 500 else 0
        for (i in start until arr.length()) out.put(arr.get(i))
        p(ctx).edit().putString("queue", out.toString()).commit()
    }

    @Volatile private var sending = false

    /** Sends what is waiting to her server; kept on the phone (up to 500) until the server says it got them. */
    fun flush(ctx: Context) {
        if (sending) return
        val server = Store.server(ctx)
        if (server.isEmpty()) return
        val app = ctx.applicationContext
        sending = true
        Thread {
            try {
                val batch = synchronized(this) { JSONArray(p(app).getString("queue", "[]")) }
                if (batch.length() > 0) {
                    val c = URL("${server.trimEnd('/')}/api/galla/alerts").openConnection() as HttpURLConnection
                    c.requestMethod = "POST"
                    c.connectTimeout = 15000
                    c.readTimeout = 20000
                    c.doOutput = true
                    c.setRequestProperty("Content-Type", "application/json")
                    val key = Store.key(app)
                    if (key.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $key")
                    c.outputStream.use { it.write(JSONObject().put("items", batch).toString().toByteArray(Charsets.UTF_8)) }
                    val code = c.responseCode
                    c.disconnect()
                    if (code in 200..299) {
                        synchronized(this) {
                            val now = JSONArray(p(app).getString("queue", "[]"))
                            val sentKeys = HashSet<String>()
                            for (i in 0 until batch.length()) sentKeys.add(batch.getJSONObject(i).optString("key"))
                            val keep = JSONArray()
                            for (i in 0 until now.length()) if (!sentKeys.contains(now.getJSONObject(i).optString("key"))) keep.put(now.get(i))
                            p(app).edit().putString("queue", keep.toString())
                                .putLong("last_sent", System.currentTimeMillis())
                                .putInt("sent_total", p(app).getInt("sent_total", 0) + batch.length()).commit()
                        }
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "galla send failed (kept for later)", e)
            } finally {
                sending = false
            }
        }.start()
    }
}

/** Android's notification access entry point. Does nothing unless the owner switched Galla on in Hoola. */
class HoolaPayListener : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        if (sbn == null) return
        try {
            PayAlerts.onPosted(this, sbn)
        } catch (e: Exception) {
            Log.w("HoolaGalla", "alert skipped", e)
        }
    }

    override fun onListenerConnected() {
        try { PayAlerts.flush(this) } catch (_: Exception) {}
    }
}
