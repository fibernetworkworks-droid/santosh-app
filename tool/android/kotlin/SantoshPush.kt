package com.newtika.santosh

import android.content.Context
import android.os.PowerManager
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Firebase Cloud Messaging: how Santosh reaches the phone when the app is closed or the screen is locked
 * (Google Play's recommended way; no always-on connection). The server sends a push only when the app isn't
 * connected. A push carries one Santosh event:
 *   message / approval / artifact / file -> a notification (title + body made by the server)
 *   device_action                         -> alarm / timer / calendar done on the phone, result reported back
 */
class SantoshPush : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        Store.setPushToken(this, token)
        register(this, token)
    }

    override fun onMessageReceived(msg: RemoteMessage) {
        val d = msg.data
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        val wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "santosh:push")
        wl.acquire(20000)
        try {
            val eventId = d["event_id"]?.toLongOrNull() ?: System.currentTimeMillis()
            when (d["kind"]) {
                "device_action" -> {
                    if (MainActivity.visible) return
                    val payload = try { JSONObject(d["payload"] ?: "{}") } catch (_: Exception) { JSONObject() }
                    if (Actions.tooOld(d["at"] ?: "")) return
                    val actionId = payload.optString("id")
                    if (actionId.isEmpty() || !Store.claim(this, actionId)) return
                    val (ok, detail) = Actions.run(this, payload)
                    postResult(actionId, ok, detail)
                    if (!ok) Notify.message(this, "Phone par yeh nahi ho paya: $detail", eventId)
                }
                "home_device", "bt_request" -> {
                    val payload = try { JSONObject(d["payload"] ?: "{}") } catch (_: Exception) { JSONObject() }
                    PhoneJobs.handle(this, d["kind"] ?: "", payload, d["at"] ?: "")
                }
                else -> {
                    if (MainActivity.visible) return          // the open app shows it in the chat
                    val body = d["body"] ?: ""
                    val title = d["title"] ?: ""
                    if (body.isNotBlank()) Notify.message(this, if (title.isNotBlank() && title != "Hoola") "$title: $body" else body, eventId)
                }
            }
        } finally {
            if (wl.isHeld) wl.release()
        }
    }

    private fun postResult(actionId: String, ok: Boolean, detail: String) {
        try {
            val c = URL("${Store.server(this).trimEnd('/')}/api/device-actions/$actionId/result").openConnection() as HttpURLConnection
            c.requestMethod = "POST"
            c.connectTimeout = 15000
            c.readTimeout = 15000
            c.doOutput = true
            c.setRequestProperty("Content-Type", "application/json")
            val key = Store.key(this)
            if (key.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $key")
            c.outputStream.use { it.write(JSONObject().put("ok", ok).put("detail", detail).toString().toByteArray(Charsets.UTF_8)) }
            c.responseCode
            c.disconnect()
        } catch (_: Exception) {
        }
    }

    companion object {
        /** Tell Santosh's server where to send pushes for this phone (also called by the app on every start). */
        fun register(ctx: Context, token: String) {
            val server = Store.server(ctx).trimEnd('/')
            if (server.isEmpty() || token.isEmpty()) return
            Thread {
                try {
                    val c = URL("$server/api/push/token").openConnection() as HttpURLConnection
                    c.requestMethod = "POST"
                    c.connectTimeout = 15000
                    c.readTimeout = 15000
                    c.doOutput = true
                    c.setRequestProperty("Content-Type", "application/json")
                    val key = Store.key(ctx)
                    if (key.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $key")
                    c.outputStream.use { it.write(JSONObject().put("token", token).put("platform", "android").toString().toByteArray(Charsets.UTF_8)) }
                    c.responseCode
                    c.disconnect()
                } catch (_: Exception) {
                }
            }.start()
        }

        /** Ask Firebase for this phone's token (async); saves and registers it. Safe when Firebase isn't set up. */
        fun init(ctx: Context, server: String, key: String) {
            Store.saveLink(ctx, server, key)
            try {
                com.google.firebase.messaging.FirebaseMessaging.getInstance().token.addOnCompleteListener { t ->
                    if (t.isSuccessful) {
                        val tok = t.result ?: return@addOnCompleteListener
                        Store.setPushToken(ctx, tok)
                        register(ctx, tok)
                    }
                }
            } catch (_: Throwable) {
            }
        }
    }
}
