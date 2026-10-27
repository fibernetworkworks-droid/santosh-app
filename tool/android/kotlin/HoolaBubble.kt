package com.newtika.santosh

import android.app.Activity
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Person
import android.content.Context
import android.content.Intent
import android.content.pm.ShortcutInfo
import android.content.pm.ShortcutManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.Icon
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

/** v0.63 The Hoola floating head, the Play-allowed way: Android's Bubbles API (Android 11+). No "draw over other
 *  apps" permission: Android itself shows the bubble for a conversation notification, and the owner can turn bubbles
 *  off from the notification at any time. Tapping the head opens [BubbleActivity], a small chat with Hoola. */
object HoolaBubble {
    const val BUBBLE_ID = 1730
    private const val CH = "hoola_bubble"
    private const val SHORTCUT = "hoola_chat"

    fun supported() = Build.VERSION.SDK_INT >= 30

    private fun nm(ctx: Context) = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    private fun prefs(ctx: Context) = ctx.getSharedPreferences("santosh_native", Context.MODE_PRIVATE)

    fun on(ctx: Context) = prefs(ctx).getBoolean("bubble_on", false)
    fun name(ctx: Context) = prefs(ctx).getString("bubble_name", "") ?.ifBlank { "Hoola" } ?: "Hoola"

    /** Bubbles allowed for Hoola in Android's settings ("All conversations can bubble" / "Selected"). */
    fun allowed(ctx: Context): Boolean {
        if (!supported()) return false
        val m = nm(ctx)
        val app = if (Build.VERSION.SDK_INT >= 31) m.bubblePreference != NotificationManager.BUBBLE_PREFERENCE_NONE
                  else @Suppress("DEPRECATION") m.areBubblesAllowed()
        val ch = m.getNotificationChannel(CH)
        return app && (ch == null || ch.canBubble())
    }

    fun openSettings(ctx: Context) {
        val i = if (Build.VERSION.SDK_INT >= 29) Intent(Settings.ACTION_APP_NOTIFICATION_BUBBLE_SETTINGS)
            .putExtra(Settings.EXTRA_APP_PACKAGE, ctx.packageName)
        else Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${ctx.packageName}"))
        try { ctx.startActivity(i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } catch (_: Exception) {}
    }

    private fun channel(ctx: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        nm(ctx).createNotificationChannel(NotificationChannel(CH, "Hoola bubble", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "Hoola ka floating head (bubble) aur uske jawab"
            setSound(null, null)
            enableVibration(false)
            setShowBadge(false)
            if (Build.VERSION.SDK_INT >= 29) setAllowBubbles(true)
        })
    }

    private fun hoola(ctx: Context): Person = Person.Builder().setName(name(ctx)).setKey("hoola")
        .setIcon(Icon.createWithResource(ctx, R.mipmap.ic_launcher)).setBot(true).setImportant(true).build()

    private fun shortcut(ctx: Context) {
        val sm = ctx.getSystemService(ShortcutManager::class.java) ?: return
        val open = Intent(ctx, BubbleActivity::class.java).setAction(Intent.ACTION_VIEW)
        val b = ShortcutInfo.Builder(ctx, SHORTCUT)
            .setShortLabel(name(ctx))
            .setLongLabel("${name(ctx)} se baat")
            .setIcon(Icon.createWithResource(ctx, R.mipmap.ic_launcher))
            .setIntent(open)
            .setPerson(hoola(ctx))
            .setLongLived(true)
            .setCategories(setOf("com.newtika.santosh.category.CHAT"))
        try { sm.pushDynamicShortcut(b.build()) } catch (_: Exception) { try { sm.addDynamicShortcuts(listOf(b.build())) } catch (_: Exception) {} }
    }

    /** Shows (or refreshes) the floating head. text = the newest line from Hoola, '' for the quiet "I'm here" head. */
    fun show(ctx: Context, text: String = "", alert: Boolean = false) {
        if (!supported()) return
        channel(ctx)
        shortcut(ctx)
        val me = Person.Builder().setName("Aap").setKey("me").build()
        val style = Notification.MessagingStyle(me)
        val line = text.replace(Regex("[*_#`]"), "").ifBlank { "Main yahan hoon. Kuch bhi poochhiye." }
        style.addMessage(Notification.MessagingStyle.Message(line, System.currentTimeMillis(), hoola(ctx)))
        val pi = PendingIntent.getActivity(ctx, 31, Intent(ctx, BubbleActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE)      // bubbles need a mutable intent
        val meta = Notification.BubbleMetadata.Builder(pi, Icon.createWithResource(ctx, R.mipmap.ic_launcher))
            .setDesiredHeight(640)
            .setAutoExpandBubble(false)
            .setSuppressNotification(!alert)
            .build()
        val n = Notification.Builder(ctx, CH)
            .setSmallIcon(R.drawable.ic_stat_santosh)
            .setContentTitle(name(ctx))
            .setContentText(line)
            .setStyle(style)
            .setShortcutId(SHORTCUT)
            .addPerson(hoola(ctx))
            .setBubbleMetadata(meta)
            .setCategory(Notification.CATEGORY_MESSAGE)
            .setOnlyAlertOnce(!alert)
            .setContentIntent(pi)
            .build()
        nm(ctx).notify(BUBBLE_ID, n)
    }

    fun hide(ctx: Context) {
        nm(ctx).cancel(BUBBLE_ID)
    }

    fun setOn(ctx: Context, on: Boolean, name: String) {
        prefs(ctx).edit().putBoolean("bubble_on", on).putString("bubble_name", name).apply()
        if (on) show(ctx) else hide(ctx)
    }

    /** A new Hoola reply while the head is on: the head shows a dot and the line. */
    fun onReply(ctx: Context, text: String) {
        if (on(ctx) && supported()) try { show(ctx, text, alert = false) } catch (_: Exception) {}
    }
}

/** The small chat inside the bubble (also opened by the widget's "Likho"). Talks to the same Hoola chat as the app,
 *  with the server address / key the app saved. Mic = opens the app straight into a voice call. */
class BubbleActivity : Activity() {
    private val main = Handler(Looper.getMainLooper())
    private lateinit var list: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var input: EditText
    private lateinit var status: TextView
    private var lastId = 0L
    private var pollUntil = 0L
    private var visible = false

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun round(color: Int, r: Int = 18) = GradientDrawable().apply { setColor(color); cornerRadius = dp(r).toFloat() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#120E2A"))
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
        val head = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        head.addView(TextView(this).apply {
            text = HoolaBubble.name(this@BubbleActivity)
            setTextColor(Color.WHITE); textSize = 18f; typeface = Typeface.DEFAULT_BOLD
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        head.addView(Button(this).apply {
            text = "App kholo"; isAllCaps = false; textSize = 12f
            setOnClickListener { startActivity(Intent(this@BubbleActivity, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
        })
        root.addView(head)
        status = TextView(this).apply { setTextColor(Color.parseColor("#9C96C2")); textSize = 11.5f }
        root.addView(status)
        list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(0, dp(6), 0, dp(6)) }
        scroll = ScrollView(this).apply { addView(list); isFillViewport = true }
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        input = EditText(this).apply {
            hint = "Hoola se kahiye…"; setHintTextColor(Color.parseColor("#9C96C2")); setTextColor(Color.WHITE)
            background = round(Color.parseColor("#221A47"), 22); setPadding(dp(14), dp(10), dp(14), dp(10))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            maxLines = 4; imeOptions = EditorInfo.IME_ACTION_SEND
            setOnEditorActionListener { _, a, _ -> if (a == EditorInfo.IME_ACTION_SEND) { send(); true } else false }
        }
        row.addView(input, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        row.addView(Button(this).apply { text = "➤"; setOnClickListener { send() } })
        row.addView(Button(this).apply {
            text = "🎙"; contentDescription = "Voice call"
            setOnClickListener {
                startActivity(Intent(this@BubbleActivity, MainActivity::class.java).setAction(WakeService.ACTION_WAKE)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }
        })
        root.addView(row)
        setContentView(root)
        if (intent?.getStringExtra("text")?.isNotBlank() == true) input.setText(intent.getStringExtra("text"))
    }

    override fun onResume() {
        super.onResume()
        visible = true
        load()
        pollUntil = System.currentTimeMillis() + 20_000
        poll()
    }

    override fun onPause() {
        visible = false
        super.onPause()
    }

    private fun ready(): Boolean = Store.server(this).isNotBlank() && Store.chatConv(this).isNotBlank()

    private fun http(method: String, path: String, body: JSONObject? = null): String? {
        val c = URL("${Store.server(this).trimEnd('/')}$path").openConnection() as HttpURLConnection
        return try {
            c.requestMethod = method
            c.connectTimeout = 10000; c.readTimeout = 15000
            val key = Store.key(this)
            if (key.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $key")
            if (body != null) {
                c.doOutput = true
                c.setRequestProperty("Content-Type", "application/json")
                c.outputStream.use { it.write(body.toString().toByteArray()) }
            }
            if (c.responseCode in 200..299) c.inputStream.bufferedReader().readText() else null
        } catch (_: Exception) { null } finally { c.disconnect() }
    }

    private fun load() {
        if (!ready()) { status.text = "Pehle Hoola app kholkar sign in kijiye."; return }
        Thread {
            val txt = http("GET", "/api/conversations/${Store.chatConv(this)}/messages?limit=14")
            main.post {
                if (txt == null) { status.text = "Server se nahi jud paye. Internet dekhiye."; return@post }
                val arr = try { JSONObject(txt).optJSONArray("messages") } catch (_: Exception) { null } ?: JSONArray()
                val lastRole = if (arr.length() > 0) arr.getJSONObject(arr.length() - 1).optString("role") else ""
                if (lastRole != "user") status.text = ""
                val newest = if (arr.length() > 0) arr.getJSONObject(arr.length() - 1).optLong("id") else 0L
                if (newest == lastId && list.childCount > 0) return@post
                lastId = newest
                list.removeAllViews()
                for (i in 0 until arr.length()) {
                    val m = arr.getJSONObject(i)
                    bubble(m.optString("role") == "user", m.optString("text"))
                }
                scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
            }
        }.start()
    }

    private fun bubble(mine: Boolean, text: String) {
        val t = TextView(this).apply {
            this.text = text.replace(Regex("[*_#`]"), "")
            setTextColor(Color.WHITE); textSize = 14.5f
            background = round(Color.parseColor(if (mine) "#6D3FE0" else "#2A2350"))
            setPadding(dp(12), dp(8), dp(12), dp(8))
            setTextIsSelectable(true)
        }
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            gravity = if (mine) Gravity.END else Gravity.START
            setMargins(if (mine) dp(40) else 0, dp(4), if (mine) 0 else dp(40), dp(4))
        }
        list.addView(t, lp)
    }

    private fun send() {
        val text = input.text.toString().trim()
        if (text.isEmpty() || !ready()) return
        input.setText("")
        bubble(true, text)
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
        status.text = "${HoolaBubble.name(this)} soch raha hai…"
        Thread {
            val body = JSONObject().put("text", text).put("client_id", "bubble-" + UUID.randomUUID().toString().take(18))
            var ok = false
            for (i in 0 until 3) {
                if (http("POST", "/api/conversations/${Store.chatConv(this)}/messages", body) != null) { ok = true; break }
                Thread.sleep(1200L * (i + 1))
            }
            main.post {
                if (!ok) { status.text = "Bhej nahi paye. Dobara koshish kijiye."; input.setText(text); return@post }
                pollUntil = System.currentTimeMillis() + 120_000
                poll()
            }
        }.start()
    }

    private fun poll() {
        main.removeCallbacksAndMessages("poll")
        if (!visible || System.currentTimeMillis() > pollUntil) { if (status.text.endsWith("…")) status.text = ""; return }
        main.postAtTime({ load(); poll() }, "poll", android.os.SystemClock.uptimeMillis() + 2500)
    }
}
