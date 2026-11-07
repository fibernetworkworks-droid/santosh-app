package hoola.kit

// Made by Hoola App Sahayak (v0.325 HOOLA QA). When the app crashes on a real user's phone, the crash (exception, the
// app's own code lines, the screen, app + Android version, phone model - no personal data, no form contents) is kept on
// the phone and sent to the business's Hoola on the next start, so Hoola can fix that screen in the next build. The
// crash still closes the app the normal Android way.

import android.app.ActivityManager
import android.app.ApplicationExitInfo
import android.content.Context
import android.os.Build
import kotlinx.coroutines.launch
import org.json.JSONObject

object CrashGuard {
    /** The screen on show (set by the app shell), so a crash says where it happened. */
    @Volatile var screen: String = ""
        set(v) {
            field = v
            // v0.540 an ANR is read on the NEXT start, when this process is long gone: keep the screen on disk too
            val c = app
            if (c != null && v.isNotEmpty()) Store.put(c, "last_screen", v)
        }
    private var installed = false
    private var app: Context? = null

    fun install(ctx: Context, versionName: String) {
        if (installed) return
        installed = true
        val app = ctx.applicationContext
        this.app = app
        val before = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            try {
                val trace = e.stackTraceToString().lines().take(60).joinToString("\n")
                val o = JSONObject().put("trace", trace.take(6000)).put("screen", screen).put("ver", versionName)
                    .put("kind", "crash")
                    .put("android", Build.VERSION.SDK_INT).put("model", (Build.MANUFACTURER + " " + Build.MODEL).take(60))
                    .put("thread", t.name.take(40)).put("at", System.currentTimeMillis())
                // commit (not apply): the process is about to end
                app.getSharedPreferences("hoola_app", Context.MODE_PRIVATE).edit().putString("crash_pending", o.toString()).commit()
            } catch (_: Throwable) {
            }
            before?.uncaughtException(t, e)
        }
    }

    /**
     * v0.540 JAANCH: an ANR is not a crash - the app did not die, it stopped answering, and the user saw a frozen
     * screen. Android keeps its own record of why a process ended (API 30+), including ANRs and native crashes that
     * no Java handler can ever see, so on every start we read anything newer than the last one we read and send it.
     */
    fun readExitReasons(ctx: Context, versionName: String) {
        if (Build.VERSION.SDK_INT < 30) return
        try {
            val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
            val seen = Store.get(ctx, "seen_exit").toLongOrNull() ?: 0L
            val want = listOf(ApplicationExitInfo.REASON_ANR, ApplicationExitInfo.REASON_CRASH_NATIVE)
            val e = am.getHistoricalProcessExitReasons(ctx.packageName, 0, 5)
                .firstOrNull { it.timestamp > seen && it.reason in want } ?: return
            Store.put(ctx, "seen_exit", e.timestamp.toString())
            val kind = if (e.reason == ApplicationExitInfo.REASON_ANR) "anr" else "native"
            var trace = ""
            try {
                e.traceInputStream?.use { s -> trace = String(s.readBytes()).take(6000) }
            } catch (_: Throwable) {
            }
            val head = "reason=$kind description=${e.description ?: ""} importance=${e.importance}"
            val body = JSONObject().put("trace", (head + "\n" + trace).take(6000)).put("kind", kind)
                .put("screen", Store.get(ctx, "last_screen")).put("ver", versionName)
                .put("android", Build.VERSION.SDK_INT)
                .put("model", (Build.MANUFACTURER + " " + Build.MODEL).take(60))
            Db.scope.launch { Cloud.call("POST", "/crash", body) }
        } catch (_: Throwable) {
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
