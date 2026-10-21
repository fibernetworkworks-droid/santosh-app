package com.newtika.santosh

import android.app.ActivityManager
import android.app.ApplicationExitInfo
import android.content.Context
import android.os.Build
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter

/** v0.69 When Hoola closes by itself, find out why and get better next time.
 *  - Java / Kotlin crashes: the stack trace is written to a file before the app dies.
 *  - Native crashes and ANRs (Android 11+): read back from Android's own exit records on the next start.
 *  - A crash during a voice call turns on "safe voice" (no on-device VAD model, no call service) for this app
 *    version, so the next call works; a new app version tries the full call again. */
object CrashGuard {
    private const val PREFS = "hoola_crash"
    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private fun file(ctx: Context) = File(ctx.filesDir, "last_crash.txt")
    @Volatile private var installed = false

    private fun versionCode(ctx: Context): Long = try {
        val pi = ctx.packageManager.getPackageInfo(ctx.packageName, 0)
        if (Build.VERSION.SDK_INT >= 28) pi.longVersionCode else @Suppress("DEPRECATION") pi.versionCode.toLong()
    } catch (_: Exception) { 0L }

    fun install(ctx: Context) {
        if (installed) return
        installed = true
        val app = ctx.applicationContext
        // the first time the recorder runs, Android's older exit records (from before it existed) are not news
        try {
            val p = prefs(app)
            if (!p.contains("seen_exit")) p.edit().putLong("seen_exit", System.currentTimeMillis()).apply()
        } catch (_: Exception) {}
        val prev = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            try {
                val sw = StringWriter()
                e.printStackTrace(PrintWriter(sw))
                val inCall = prefs(app).getBoolean("in_call", false)
                file(app).writeText("thread=${t.name} in_call=$inCall version=${versionCode(app)} sdk=${Build.VERSION.SDK_INT} " +
                    "device=${Build.MANUFACTURER} ${Build.MODEL}\n" + sw.toString().take(12000))
            } catch (_: Throwable) {}
            prev?.uncaughtException(t, e)
        }
    }

    /** Called when a voice call starts / ends (commit: it must be on disk if the process dies next). */
    fun markCall(ctx: Context, on: Boolean) {
        try { prefs(ctx).edit().putBoolean("in_call", on).commit() } catch (_: Exception) {}
    }

    fun safeVoice(ctx: Context): Boolean {
        val p = prefs(ctx)
        return p.getBoolean("safe_voice", false) && p.getLong("safe_voice_version", -1) == versionCode(ctx)
    }

    fun setSafeVoice(ctx: Context, on: Boolean) {
        prefs(ctx).edit().putBoolean("safe_voice", on).putLong("safe_voice_version", versionCode(ctx)).apply()
    }

    /** Printable pieces of a binary tombstone (library and function names of the native backtrace). */
    private fun strings(b: ByteArray, max: Int): String {
        val out = StringBuilder()
        val cur = StringBuilder()
        for (x in b) {
            val c = x.toInt() and 0xff
            if (c in 32..126) cur.append(c.toChar()) else {
                if (cur.length >= 5) out.append(cur).append('\n')
                cur.setLength(0)
                if (out.length > max) break
            }
        }
        return out.toString().take(max)
    }

    /** The newest crash not reported yet, or null. Reading it marks it as reported. */
    fun pending(ctx: Context): Map<String, Any>? {
        val p = prefs(ctx)
        val inCallAtDeath = p.getBoolean("in_call", false)
        var out: MutableMap<String, Any>? = null
        val f = file(ctx)
        if (f.exists()) {
            val txt = try { f.readText() } catch (_: Exception) { "" }
            f.delete()
            out = mutableMapOf("kind" to "java", "text" to txt, "during_call" to txt.contains("in_call=true"))
        }
        if (out == null && Build.VERSION.SDK_INT >= 30) {
            try {
                val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                val seen = p.getLong("seen_exit", 0L)
                val e = am.getHistoricalProcessExitReasons(ctx.packageName, 0, 5).firstOrNull {
                    it.timestamp > seen && it.reason in listOf(ApplicationExitInfo.REASON_CRASH, ApplicationExitInfo.REASON_CRASH_NATIVE,
                        ApplicationExitInfo.REASON_ANR)
                }
                if (e != null) {
                    p.edit().putLong("seen_exit", e.timestamp).apply()
                    val kind = when (e.reason) { ApplicationExitInfo.REASON_CRASH_NATIVE -> "native"; ApplicationExitInfo.REASON_ANR -> "anr"; else -> "crash" }
                    var trace = ""
                    try {
                        e.traceInputStream?.use { s -> val bytes = s.readBytes(); trace = if (kind == "anr") String(bytes).take(8000) else strings(bytes, 8000) }
                    } catch (_: Exception) {}
                    out = mutableMapOf("kind" to kind, "during_call" to inCallAtDeath,
                        "text" to "reason=$kind description=${e.description ?: ""} importance=${e.importance} " +
                            "sdk=${Build.VERSION.SDK_INT} device=${Build.MANUFACTURER} ${Build.MODEL} version=${versionCode(ctx)}\n$trace")
                }
            } catch (_: Exception) {}
        }
        if (out != null) {
            out["at"] = System.currentTimeMillis()
            if (out["during_call"] == true) {
                setSafeVoice(ctx, true)
                out["safe_voice"] = true
            }
        }
        markCall(ctx, false)
        return out
    }
}
