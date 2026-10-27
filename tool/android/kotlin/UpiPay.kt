package com.newtika.santosh

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * v0.109 "Paisa bhejo" result. The UPI intent (payee + amount + note + tr = Hoola's reference, filled by the server)
 * is opened FOR A RESULT, so when she comes back the UPI app's own answer (NPCI: "txnId=..&responseCode=..&
 * Status=SUCCESS&txnRef=..") reaches us. It goes straight to the server (/api/bazar/upi/result) from here, so it
 * arrives even if the Flutter screen was rebuilt. Kept on the phone until the server says 2xx.
 * Hoola never sees or types the UPI PIN; it only reads what the UPI app chose to return.
 */
object UpiPay {
    const val REQ = 7707
    private const val TAG = "HoolaUpi"
    private fun p(ctx: Context) = ctx.getSharedPreferences("hoola_upi", Context.MODE_PRIVATE)

    /** Called from openExternal for upi / tez / phonepe / paytmmp links. Returns "ok" or a reason. */
    fun open(act: Activity, uri: Uri, pkg: String, installed: (String) -> Boolean): String {
        val query = uri.encodedQuery ?: ""
        val generic = Uri.parse("upi://pay?$query")
        val ref = generic.getQueryParameter("tr") ?: ""
        var intent = Intent(Intent.ACTION_VIEW, generic)
        if (pkg.isNotBlank() && installed(pkg)) intent.setPackage(pkg)
        else intent = Intent.createChooser(intent, "Kis UPI app se pay karein?")
        // NO FLAG_ACTIVITY_NEW_TASK: with it Android cancels the result at once
        try {
            remember(act, ref, pkg)
            act.startActivityForResult(intent, REQ)
            return "ok"
        } catch (e: Exception) {
            Log.w(TAG, "open for result failed", e)
        }
        // the app's own scheme (tez:// phonepe:// paytmmp://) as a last try, still for a result
        try {
            if (uri.scheme != "upi") {
                remember(act, ref, pkg)
                act.startActivityForResult(Intent(Intent.ACTION_VIEW, uri), REQ)
                return "ok"
            }
        } catch (_: Exception) {}
        forget(act)
        return "Is phone par koi UPI app ye link nahi khol paya"
    }

    private fun remember(ctx: Context, ref: String, pkg: String) {
        p(ctx).edit().putString("ref", ref).putString("pkg", pkg).putLong("at", System.currentTimeMillis()).commit()
    }

    private fun forget(ctx: Context) { p(ctx).edit().remove("ref").remove("pkg").remove("at").commit() }

    /** onActivityResult. Some apps put the answer in "response", some in "Status"/"txnId" extras: all are read. */
    fun onResult(ctx: Context, resultCode: Int, data: Intent?) {
        var ref = p(ctx).getString("ref", "") ?: ""
        val pkg = p(ctx).getString("pkg", "") ?: ""
        forget(ctx)
        var response = data?.getStringExtra("response") ?: ""
        if (response.isBlank() && data != null) {
            val parts = mutableListOf<String>()
            for (k in listOf("Status", "status", "txnId", "responseCode", "ApprovalRefNo", "txnRef")) {
                data.getStringExtra(k)?.takeIf { it.isNotBlank() }?.let { parts.add("$k=$it") }
            }
            response = parts.joinToString("&")
        }
        if (ref.isBlank()) ref = Regex("(?i)txnRef=([A-Za-z0-9]{6,40})").find(response)?.groupValues?.get(1) ?: ""
        if (ref.isBlank()) return
        val result = when {
            response.isNotBlank() -> "ok"
            resultCode == Activity.RESULT_CANCELED -> "cancelled"
            else -> "none"
        }
        queue(ctx, JSONObject().put("txn_ref", ref).put("response", response.take(2000)).put("result", result).put("package", pkg))
    }

    /** App start: a payment left open (no answer for 30 min, e.g. the phone restarted) gets "none" so her card asks Ho gaya / Nahi hua. */
    fun onStart(ctx: Context) {
        val ref = p(ctx).getString("ref", "") ?: ""
        val at = p(ctx).getLong("at", 0L)
        // 30 min: she may still be inside the UPI app; Android delivers the result after the activity comes back
        if (ref.isNotBlank() && System.currentTimeMillis() - at > 30 * 60_000) {
            val pkg = p(ctx).getString("pkg", "") ?: ""
            forget(ctx)
            queue(ctx, JSONObject().put("txn_ref", ref).put("response", "").put("result", "none").put("package", pkg))
        } else flush(ctx)
    }

    private fun queue(ctx: Context, item: JSONObject) {
        synchronized(this) {
            val q = JSONArray(p(ctx).getString("queue", "[]"))
            q.put(item)
            val keep = JSONArray()
            for (i in maxOf(0, q.length() - 20) until q.length()) keep.put(q.get(i))
            p(ctx).edit().putString("queue", keep.toString()).commit()
        }
        flush(ctx)
    }

    @Volatile private var sending = false

    fun flush(ctx: Context) {
        val server = Store.server(ctx)
        if (server.isEmpty() || sending) return
        val app = ctx.applicationContext
        sending = true
        Thread {
            try {
                while (true) {
                    val first = synchronized(this) {
                        val q = JSONArray(p(app).getString("queue", "[]"))
                        if (q.length() == 0) null else q.getJSONObject(0)
                    } ?: break
                    val c = URL("${server.trimEnd('/')}/api/bazar/upi/result").openConnection() as HttpURLConnection
                    c.requestMethod = "POST"
                    c.connectTimeout = 15000
                    c.readTimeout = 20000
                    c.doOutput = true
                    c.setRequestProperty("Content-Type", "application/json")
                    val key = Store.key(app)
                    if (key.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $key")
                    c.outputStream.use { it.write(first.toString().toByteArray(Charsets.UTF_8)) }
                    val code = c.responseCode
                    c.disconnect()
                    // 2xx = recorded; 4xx = the server will never take it (unknown ref): drop it too
                    val gone = code in 200..299 || (code in 400..499 && code != 401 && code != 403 && code != 429)
                    if (gone) synchronized(this) {
                        val q = JSONArray(p(app).getString("queue", "[]"))
                        val keep = JSONArray()
                        for (i in 1 until q.length()) keep.put(q.get(i))
                        p(app).edit().putString("queue", keep.toString()).commit()
                    } else break
                }
            } catch (e: Exception) {
                Log.w(TAG, "upi result send failed (kept for later)", e)
            } finally {
                sending = false
            }
        }.start()
    }

    /** Which of these packages are installed (manifest <queries> lists every UPI app we offer). */
    fun installedOf(ctx: Context, pkgs: List<String>): List<String> = pkgs.filter {
        try { ctx.packageManager.getPackageInfo(it, 0); true } catch (_: Exception) { false }
    }
}
