package hoola.kit

// Made by Hoola App Sahayak (v0.324 HOOLA QA). When the app crashes on a real user's phone, the crash (exception, the
// app's own code lines, the screen, app + Android version, phone model - no personal data, no form contents) is kept on
// the phone and sent to the business's Hoola on the next start, so Hoola can fix that screen in the next build. The
// crash still closes the app the normal Android way.

import android.content.Context
import android.os.Build
import kotlinx.coroutines.launch
import org.json.JSONObject

object CrashGuard {
    /** The screen on show (set by the app shell), so a crash says where it happened. */
    @Volatile var screen: String = ""
    private var installed = false

    fun install(ctx: Context, versionName: String) {
        if (installed) return
        installed = true
        val app = ctx.applicationContext
        val before = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            try {
                val trace = e.stackTraceToString().lines().take(60).joinToString("\n")
                val o = JSONObject().put("trace", trace.take(6000)).put("screen", screen).put("ver", versionName)
                    .put("android", Build.VERSION.SDK_INT).put("model", (Build.MANUFACTURER + " " + Build.MODEL).take(60))
                    .put("thread", t.name.take(40)).put("at", System.currentTimeMillis())
                // commit (not apply): the process is about to end
                app.getSharedPreferences("hoola_app", Context.MODE_PRIVATE).edit().putString("crash_pending", o.toString()).commit()
            } catch (_: Throwable) {
            }
            before?.uncaughtException(t, e)
        }
    }

    /** Sends a crash kept from the last run (once; kept until the server has it). */
    fun sendPending(ctx: Context) {
        val s = Store.get(ctx, "crash_pending")
        if (s.isEmpty()) return
        Db.scope.launch {
            val body = try { JSONObject(s) } catch (_: Exception) { null }
            if (body == null) {
                Store.put(ctx, "crash_pending", "")
                return@launch
            }
            val r = Cloud.call("POST", "/crash", body)
            if (r.ok || (r.code in 400..499 && r.code != 429)) Store.put(ctx, "crash_pending", "")
        }
    }
}
