package com.newtika.santosh

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import org.json.JSONObject
import java.io.BufferedReader
import java.io.IOException
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

/**
 * Keeps a live link to Santosh Core while the app is closed: shows Santosh's messages as notifications
 * and carries out phone actions (alarm, timer, calendar) by itself.
 */
class SantoshService : Service() {
    companion object {
        @Volatile var running = false

        fun start(ctx: Context) {
            Store.setEnabled(ctx, true)
            val i = Intent(ctx, SantoshService::class.java)
            if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i) else ctx.startService(i)
            running = true   // Android starts it a moment later; report it as on right away
        }

        fun stop(ctx: Context) {
            running = false
            ctx.stopService(Intent(ctx, SantoshService::class.java))
        }
    }

    @Volatile private var stopping = false
    @Volatile private var conn: HttpURLConnection? = null
    private var worker: Thread? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        Notify.channels(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val n = Notify.service(this, "Hoola duty par hai", "App band ho tab bhi aapke kaam chal rahe hain")
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(Notify.SERVICE_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_REMOTE_MESSAGING)
        } else {
            startForeground(Notify.SERVICE_ID, n)
        }
        if (!Store.enabled(this) || Store.server(this).isEmpty()) {
            running = false
            stopSelf()
            return START_NOT_STICKY
        }
        running = true
        if (worker?.isAlive == true) {
            reconnect()   // settings may have changed (new chat, new key): reopen with fresh values
        } else {
            stopping = false
            worker = Thread({ loop() }, "santosh-stream").also { it.isDaemon = true; it.start() }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        stopping = true
        running = false
        reconnect()
        worker?.interrupt()
        super.onDestroy()
    }

    private fun reconnect() {
        val c = conn ?: return
        Thread { try { c.disconnect() } catch (_: Exception) {} }.start()
    }

    private fun pause(ms: Long) {
        try { Thread.sleep(ms) } catch (_: InterruptedException) {}
    }

    private fun loop() {
        var backoff = 2000L
        while (!stopping) {
            val server = Store.server(this).trimEnd('/')
            val key = Store.key(this)
            val conv = Store.conv(this)
            if (server.isEmpty() || conv.isEmpty()) { pause(30000); continue }
            try {
                val c = URL("$server/api/conversations/$conv/events?after=${Store.lastId(this)}").openConnection() as HttpURLConnection
                c.connectTimeout = 15000
                c.readTimeout = 60000          // the server pings every 15 s
                c.setRequestProperty("Accept", "text/event-stream")
                if (key.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $key")
                conn = c
                val code = c.responseCode
                if (code == 401 || code == 404) {
                    Store.setStatus(this, if (code == 401) "API key galat hai" else "Chat nahi mila, app kholiye")
                    c.disconnect()
                    pause(300000)
                    continue
                }
                if (code != 200) throw IOException("HTTP $code")
                Store.setStatus(this, "connected")
                backoff = 2000L
                val reader = BufferedReader(InputStreamReader(c.inputStream, Charsets.UTF_8))
                val buf = StringBuilder()
                while (!stopping) {
                    val line = reader.readLine() ?: break
                    if (line.startsWith("data:")) {
                        buf.append(line.substring(5).trimStart())
                    } else if (line.isEmpty() && buf.isNotEmpty()) {
                        val data = buf.toString()
                        buf.setLength(0)
                        try { handle(JSONObject(data)) } catch (e: Exception) { /* one bad event never stops the stream */ }
                    }
                }
                c.disconnect()
            } catch (e: Exception) {
                if (!stopping) Store.setStatus(this, "offline: ${e.message ?: e.javaClass.simpleName}")
            }
            if (!stopping) {
                pause(backoff)
                backoff = minOf(backoff * 2, 60000L)
            }
        }
    }

    private fun handle(ev: JSONObject) {
        val id = ev.optLong("id")
        if (id <= Store.lastId(this)) return
        Store.setLastId(this, id)
        val payload = ev.optJSONObject("payload") ?: JSONObject()
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        val wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "santosh:event")
        wl.acquire(20000)
        try {
            when (ev.optString("kind")) {
                "message" -> if (payload.optString("role") == "assistant" && !MainActivity.visible &&
                    !Actions.tooOld(ev.optString("at"), 10)) {
                    Notify.message(this, payload.optString("text"), id)
                }
                "device_action" -> {
                    if (MainActivity.visible) return          // the app on screen does it itself
                    if (Actions.tooOld(ev.optString("at"))) return
                    val actionId = payload.optString("id")
                    if (!Store.claim(this, actionId)) return
                    val (ok, detail) = Actions.run(this, payload)
                    postResult(actionId, ok, detail)
                    if (!ok) Notify.message(this, "Phone par yeh nahi ho paya: $detail", id)
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
            val body = JSONObject().put("ok", ok).put("detail", detail).toString().toByteArray(Charsets.UTF_8)
            c.outputStream.use { it.write(body) }
            c.responseCode
            c.disconnect()
        } catch (_: Exception) {
        }
    }
}
