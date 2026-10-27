package com.newtika.santosh

import android.annotation.SuppressLint
import android.app.Activity
import android.app.Presentation
import android.content.Context
import android.graphics.Color
import android.hardware.display.DisplayManager
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Display
import android.view.WindowManager
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient

/**
 * v0.127 Hoola Screen: when a mini screen / TV / monitor is connected (HDMI over USB-C, or Android's wireless display),
 * Android reports it as a "presentation" display. Hoola then shows its VIEW-ONLY live board there (the server page
 * /screen/<signed token>) instead of a mirror of the phone, so the phone stays free to use. Nothing can be tapped into
 * an approval from the big screen: every Haan / payment / OTP stays on the phone.
 *
 * The board is an Android Presentation (a window on the second display owned by the open app: no overlay permission).
 * While it is showing, the phone screen is kept on so Android doesn't stop the app (the owner can switch that off).
 */
object ExtScreen {
    private const val PREFS = "hoola_screen"
    private val main = Handler(Looper.getMainLooper())
    private var shown: BoardPresentation? = null
    private var listener: DisplayManager.DisplayListener? = null
    private var host: Activity? = null

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun setup(ctx: Context, url: String?, on: Boolean?, awake: Boolean?) {
        val e = prefs(ctx).edit()
        if (url != null) e.putString("url", url)
        if (on != null) e.putBoolean("on", on)
        if (awake != null) e.putBoolean("awake", awake)
        e.apply()
        host?.let { a -> main.post { refresh(a, force = url != null) } }
    }

    fun info(ctx: Context): Map<String, Any?> {
        val d = target(ctx)
        val p = prefs(ctx)
        return mapOf("connected" to (d != null), "name" to d?.name, "showing" to (shown?.isShowing == true),
            "on" to p.getBoolean("on", true), "awake" to p.getBoolean("awake", true),
            "has_link" to !p.getString("url", "").isNullOrEmpty(),
            "width" to d?.let { metricsOf(it).first }, "height" to d?.let { metricsOf(it).second })
    }

    private fun metricsOf(d: Display): Pair<Int, Int> {
        val m = android.util.DisplayMetrics()
        @Suppress("DEPRECATION") d.getRealMetrics(m)
        return m.widthPixels to m.heightPixels
    }

    private fun target(ctx: Context): Display? = try {
        val dm = ctx.getSystemService(Context.DISPLAY_SERVICE) as DisplayManager
        dm.getDisplays(DisplayManager.DISPLAY_CATEGORY_PRESENTATION).firstOrNull { it.displayId != Display.DEFAULT_DISPLAY }
    } catch (_: Exception) { null }

    fun attach(a: Activity) {
        host = a
        if (listener == null) {
            val l = object : DisplayManager.DisplayListener {
                override fun onDisplayAdded(id: Int) { host?.let { refresh(it) } }
                override fun onDisplayRemoved(id: Int) { host?.let { refresh(it) } }
                override fun onDisplayChanged(id: Int) { host?.let { refresh(it) } }
            }
            try { (a.getSystemService(Context.DISPLAY_SERVICE) as DisplayManager).registerDisplayListener(l, main) } catch (_: Exception) {}
            listener = l
        }
        refresh(a)
    }

    fun detach(a: Activity) {
        if (host !== a) return
        listener?.let { try { (a.getSystemService(Context.DISPLAY_SERVICE) as DisplayManager).unregisterDisplayListener(it) } catch (_: Exception) {} }
        listener = null
        dismiss(a)
        host = null
    }

    private fun dismiss(a: Activity) {
        try { shown?.dismiss() } catch (_: Exception) {}
        shown = null
        try { a.window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) } catch (_: Exception) {}
    }

    fun refresh(a: Activity, force: Boolean = false) {
        try {
            val p = prefs(a)
            val url = p.getString("url", "") ?: ""
            val d = target(a)
            if (d == null || !p.getBoolean("on", true) || !url.startsWith("https://") && !url.startsWith("http://")) {
                dismiss(a); return
            }
            val cur = shown
            if (cur != null && cur.isShowing && cur.display.displayId == d.displayId && !force) return
            dismiss(a)
            val pr = BoardPresentation(a, d, url)
            pr.show()
            shown = pr
            if (p.getBoolean("awake", true)) a.window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } catch (_: Exception) {
            // WindowManager.InvalidDisplayException etc.: the screen went away while we were opening it
            shown = null
        }
    }

    private class BoardPresentation(ctx: Context, display: Display, private val url: String) : Presentation(ctx, display) {
        @SuppressLint("SetJavaScriptEnabled")
        override fun onCreate(savedInstanceState: Bundle?) {
            super.onCreate(savedInstanceState)
            window?.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            val origin = Uri.parse(url).let { "${it.scheme}://${it.authority}" }
            val w = WebView(context)
            w.setBackgroundColor(Color.parseColor("#0d1017"))
            w.settings.javaScriptEnabled = true      // the board polls its own read-only feed
            w.settings.allowFileAccess = false
            w.settings.allowContentAccess = false
            w.settings.setSupportMultipleWindows(false)
            w.webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, req: WebResourceRequest): Boolean =
                    !req.url.toString().startsWith(origin)   // stays on Hoola's own page
            }
            setContentView(w)
            w.loadUrl(url)
        }
    }
}
