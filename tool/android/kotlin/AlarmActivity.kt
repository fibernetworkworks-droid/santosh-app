package com.newtika.santosh

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/** Full-screen ringing alarm (works over the lock screen). */
class AlarmActivity : Activity() {
    private var alarmId = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON)
        }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        alarmId = intent.getIntExtra("id", 0)
        val d = resources.displayMetrics.density

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding((32 * d).toInt(), 0, (32 * d).toInt(), 0)
            background = GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM, intArrayOf(Color.parseColor("#2E1065"), Color.parseColor("#6D28D9"), Color.parseColor("#A21CAF")))
        }
        fun text(t: String, sp: Float, bold: Boolean, alpha: Float = 1f) = TextView(this).apply {
            text = t; textSize = sp; setTextColor(Color.WHITE); this.alpha = alpha; gravity = Gravity.CENTER
            if (bold) setTypeface(typeface, Typeface.BOLD)
        }
        root.addView(text("Santosh", 18f, true, .8f))
        root.addView(text(intent.getStringExtra("time") ?: "", 72f, true))
        root.addView(text(intent.getStringExtra("label") ?: "Alarm", 22f, false, .95f))
        val stop = Button(this).apply {
            text = "Band karo"
            textSize = 20f
            setTextColor(Color.parseColor("#4C1D95"))
            background = GradientDrawable().apply { cornerRadius = 40 * d; setColor(Color.WHITE) }
            setOnClickListener { Notify.cancel(this@AlarmActivity, alarmId); finish() }
        }
        root.addView(stop, LinearLayout.LayoutParams((220 * d).toInt(), (64 * d).toInt()).apply { topMargin = (56 * d).toInt() })
        setContentView(root)
    }
}
