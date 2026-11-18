package com.newtika.santosh

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * v0.864 R4 Yes / Not now on an approval notification (docs/HOOLA_APP_REDESIGN_PLAN.md R4).
 * Only confirm cards that move NO money carry these buttons (the server decides: push.build sets yes_card).
 * The tap goes to the same route the app uses; the server checks the card again and asks for the fingerprint
 * (428) on anything that needs it - then the notification says "Open Hoola to approve" and nothing happened.
 * A broadcast, not an activity: nothing opens on the lock screen, and the phone must be unlocked to tap an action
 * that Android marks as needing authentication (setAuthenticationRequired is applied on Android 12+).
 */
class CardActionReceiver : BroadcastReceiver() {
    companion object {
        const val ACTION = "com.newtika.santosh.CARD_ACTION"
    }

    override fun onReceive(ctx: Context, intent: Intent) {
        val card = intent.getStringExtra("card") ?: return
        val decision = intent.getStringExtra("decision") ?: return
        if (decision != "approve" && decision != "reject") return
        val nid = intent.getIntExtra("nid", 0)
        val what = (intent.getStringExtra("text") ?: "").take(120)
        val app = ctx.applicationContext
        val pending = goAsync()
        Thread {
            try {
                val code = post(app, card, decision)
                when {
                    code in 200..299 && decision == "approve" -> Notify.cardResult(app, nid, "Done: $what", false)
                    code in 200..299 -> Notify.cardResult(app, nid, "Not done: $what", false)
                    code == 428 -> Notify.cardResult(app, nid, "Open Hoola to approve this with your fingerprint.", true)
                    else -> Notify.cardResult(app, nid, "Could not answer from here. Open Hoola to see the card.", true)
                }
            } catch (_: Throwable) {
                try { Notify.cardResult(app, nid, "No connection. Open Hoola to answer the card.", true) } catch (_: Throwable) {}
            } finally {
                pending.finish()
            }
        }.start()
    }

    private fun post(ctx: Context, card: String, decision: String): Int {
        val server = Store.server(ctx).trimEnd('/')
        if (server.isEmpty()) return 0
        val safe = card.filter { it.isLetterOrDigit() || it == '_' || it == '-' }
        val c = URL("$server/api/bazar/approvals/$safe").openConnection() as HttpURLConnection
        c.requestMethod = "POST"
        c.connectTimeout = 15000
        c.readTimeout = 20000
        c.doOutput = true
        c.setRequestProperty("Content-Type", "application/json")
        val key = Store.key(ctx)
        if (key.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $key")
        c.outputStream.use { it.write(JSONObject().put("decision", decision).toString().toByteArray(Charsets.UTF_8)) }
        val code = c.responseCode
        c.disconnect()
        return code
    }
}
