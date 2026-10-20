package com.newtika.santosh

import android.content.Context
import android.os.PowerManager
import android.util.Log
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Bluetooth and Ghar jobs that arrive while the app is closed or the screen is locked (FCM push or the background
 * event stream). Runs them natively and reports to the server, so "TV ki awaaz badhao" works from a voice call or
 * the lock screen too. The open app (Flutter) runs them itself; [Store.claim] makes sure only one side does.
 */
object PhoneJobs {
    private const val TAG = "HoolaJobs"

    /** Returns true when the event was a phone job (handled or deliberately skipped). */
    fun handle(ctx: Context, kind: String, payload: JSONObject, at: String): Boolean {
        if (kind != "home_device" && kind != "bt_request") return false
        if (MainActivity.visible) return true                 // the app on screen does it
        if (Actions.tooOld(at, 2)) return true                // never fire an old TV/AC command
        val id = if (kind == "home_device") payload.optString("command_id") else payload.optString("request_id")
        if (id.isEmpty() || !Store.claim(ctx, id)) return true
        val pm = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
        val wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "hoola:job").apply { acquire(60000) }
        val app = ctx.applicationContext
        if (kind == "home_device") {
            HomeDevices.run(app, payload.toString()) { err ->
                post(app, "/api/bazar/devices/commands/$id/result",
                    JSONObject().put("ok", err == null).put("error", err ?: ""))
                if (wl.isHeld) wl.release()
            }
        } else {
            BtControl.run(app, payload.optString("action"), payload.optJSONObject("args") ?: JSONObject()) { ok, res, err ->
                post(app, "/api/bt/requests/$id/result", JSONObject().put("ok", ok).put("result", res).put("error", err))
                if (wl.isHeld) wl.release()
            }
        }
        return true
    }

    private fun post(ctx: Context, path: String, body: JSONObject) {
        Thread {
            try {
                val c = URL("${Store.server(ctx).trimEnd('/')}$path").openConnection() as HttpURLConnection
                c.requestMethod = "POST"
                c.connectTimeout = 15000
                c.readTimeout = 15000
                c.doOutput = true
                c.setRequestProperty("Content-Type", "application/json")
                val key = Store.key(ctx)
                if (key.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $key")
                c.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
                c.responseCode
                c.disconnect()
            } catch (e: Exception) {
                Log.w(TAG, "result post failed", e)
            }
        }.start()
    }
}
