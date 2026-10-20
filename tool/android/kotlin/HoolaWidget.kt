package com.newtika.santosh

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.widget.RemoteViews

/** v0.63 Home-screen widget: Hoola's name, the last thing Hoola said, the next reminder, and two big buttons:
 *  "Bolo" (voice call) and "Likho" (the small chat). Plain RemoteViews, no extra library. */
class HoolaWidget : AppWidgetProvider() {
    override fun onUpdate(ctx: Context, mgr: AppWidgetManager, ids: IntArray) {
        for (id in ids) mgr.updateAppWidget(id, views(ctx))
    }

    companion object {
        private fun prefs(ctx: Context) = ctx.getSharedPreferences("santosh_native", Context.MODE_PRIVATE)

        fun save(ctx: Context, name: String?, last: String?, next: String?) {
            val e = prefs(ctx).edit()
            if (name != null) e.putString("w_name", name)
            if (last != null) e.putString("w_last", last.replace(Regex("[*_#`]"), "").take(220))
            if (next != null) e.putString("w_next", next.take(120))
            e.apply()
            update(ctx)
        }

        fun update(ctx: Context) {
            val mgr = AppWidgetManager.getInstance(ctx)
            val ids = mgr.getAppWidgetIds(ComponentName(ctx, HoolaWidget::class.java))
            if (ids.isEmpty()) return
            val v = views(ctx)
            for (id in ids) mgr.updateAppWidget(id, v)
        }

        fun count(ctx: Context): Int =
            AppWidgetManager.getInstance(ctx).getAppWidgetIds(ComponentName(ctx, HoolaWidget::class.java)).size

        /** Asks the launcher to put the widget on the home screen (Android 8+, launcher must support it). */
        fun pin(ctx: Context): Boolean {
            if (Build.VERSION.SDK_INT < 26) return false
            val mgr = AppWidgetManager.getInstance(ctx)
            if (!mgr.isRequestPinAppWidgetSupported) return false
            return mgr.requestPinAppWidget(ComponentName(ctx, HoolaWidget::class.java), null, null)
        }

        private fun views(ctx: Context): RemoteViews {
            val p = prefs(ctx)
            val v = RemoteViews(ctx.packageName, R.layout.hoola_widget)
            v.setTextViewText(R.id.w_name, p.getString("w_name", "")?.ifBlank { "Hoola" } ?: "Hoola")
            v.setTextViewText(R.id.w_last, p.getString("w_last", "")?.ifBlank { "Namaste! Bolo ya likho, main sun raha hoon." } ?: "")
            val next = p.getString("w_next", "") ?: ""
            v.setTextViewText(R.id.w_next, if (next.isBlank()) "Koi reminder nahi" else "⏰ $next")
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            val talk = Intent(ctx, MainActivity::class.java).setAction(WakeService.ACTION_WAKE).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            v.setOnClickPendingIntent(R.id.w_talk, PendingIntent.getActivity(ctx, 41, talk, flags))
            val write = Intent(ctx, BubbleActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            v.setOnClickPendingIntent(R.id.w_write, PendingIntent.getActivity(ctx, 42, write, flags))
            val open = Intent(ctx, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            v.setOnClickPendingIntent(R.id.w_body, PendingIntent.getActivity(ctx, 43, open, flags))
            return v
        }
    }
}
