package com.newtika.santosh

import android.app.Activity
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInfo
import android.content.pm.PackageInstaller
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/** v0.63 In-app update for the GitHub APK build only (manifest meta-data hoola.channel = github). A Play Store
 *  build is made with HOOLA_CHANNEL=play: patch_android removes REQUEST_INSTALL_PACKAGES and this whole flow is off
 *  (Play bans apps that update themselves).
 *
 *  Safety: the APK is downloaded over https from the release the server named, its SHA-256 must match the digest
 *  GitHub published for that asset, its package name must be ours and it must be signed with the SAME key as the
 *  installed app. Android then shows its own "Update?" screen: the owner taps Install. */
object AppUpdate {
    const val ACTION_STATUS = "com.newtika.santosh.UPDATE_STATUS"
    @Volatile private var pct = -1
    @Volatile private var stop = false
    @Volatile private var busy = false

    fun channel(ctx: Context): String = try {
        val ai = ctx.packageManager.getApplicationInfo(ctx.packageName, PackageManager.GET_META_DATA)
        ai.metaData?.getString("hoola.channel") ?: "github"
    } catch (_: Exception) { "github" }

    fun info(ctx: Context): Map<String, Any?> {
        val pi = ctx.packageManager.getPackageInfo(ctx.packageName, 0)
        @Suppress("DEPRECATION")
        val code = if (Build.VERSION.SDK_INT >= 28) pi.longVersionCode else pi.versionCode.toLong()
        val can = Build.VERSION.SDK_INT < 26 || ctx.packageManager.canRequestPackageInstalls()
        return mapOf("version" to (pi.versionName ?: ""), "build" to code, "channel" to channel(ctx), "can_install" to can,
            "busy" to busy)
    }

    fun openInstallPermission(ctx: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        try {
            ctx.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${ctx.packageName}"))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (_: Exception) {}
    }

    fun progress(): Int = pct
    fun cancel() { stop = true }

    /** Downloads + checks the APK on a background thread; done(path, error) on that thread. */
    fun download(ctx: Context, url: String, sha256: String, size: Long, done: (String?, String?) -> Unit) {
        if (channel(ctx) != "github") { done(null, "Is version mein app khud update nahi hota (Play Store se update kijiye)."); return }
        if (busy) { done(null, "Update pehle se chal raha hai."); return }
        if (!url.startsWith("https://github.com/") && !url.startsWith("https://objects.githubusercontent.com/")) {
            done(null, "Update ka link GitHub ka nahi hai, isliye nahi liya."); return
        }
        busy = true; stop = false; pct = 0
        Thread {
            val dir = File(ctx.cacheDir, "updates").apply { mkdirs() }
            dir.listFiles()?.forEach { it.delete() }
            val out = File(dir, "hoola-update.apk")
            try {
                var link = url
                var c: HttpURLConnection? = null
                for (hop in 0 until 5) {                          // GitHub -> its download host (https only)
                    c = (URL(link).openConnection() as HttpURLConnection).apply {
                        instanceFollowRedirects = false; connectTimeout = 15000; readTimeout = 30000
                        setRequestProperty("User-Agent", "Hoola-updater")
                    }
                    val code = c.responseCode
                    if (code in 300..399) {
                        val next = c.getHeaderField("Location") ?: break
                        c.disconnect()
                        if (!next.startsWith("https://")) throw IllegalStateException("insecure redirect")
                        link = next
                        continue
                    }
                    break
                }
                val conn = c ?: throw IllegalStateException("no connection")
                if (conn.responseCode != 200) throw IllegalStateException("HTTP ${conn.responseCode}")
                val total = if (size > 0) size else conn.contentLengthLong
                val md = MessageDigest.getInstance("SHA-256")
                var got = 0L
                conn.inputStream.use { inp ->
                    out.outputStream().use { o ->
                        val buf = ByteArray(128 * 1024)
                        while (true) {
                            if (stop) throw InterruptedException("cancelled")
                            val r = inp.read(buf)
                            if (r < 0) break
                            o.write(buf, 0, r); md.update(buf, 0, r); got += r
                            if (total > 0) pct = ((got * 100) / total).toInt().coerceIn(0, 99)
                            if (got > 400L * 1024 * 1024) throw IllegalStateException("too big")
                        }
                    }
                }
                conn.disconnect()
                val hex = md.digest().joinToString("") { "%02x".format(it) }
                val want = sha256.removePrefix("sha256:").lowercase()
                if (want.isNotEmpty() && want != hex) throw SecurityException("checksum")
                check(ctx, out)
                pct = 100
                busy = false
                done(out.absolutePath, null)
            } catch (e: Exception) {
                out.delete()
                busy = false; pct = -1
                done(null, when {
                    e is InterruptedException -> "cancelled"
                    e is SecurityException && e.message == "checksum" -> "Download kharab aaya (checksum match nahi hua). Dobara try kijiye."
                    e is SecurityException -> e.message
                    else -> "Download nahi ho paya (${e.message ?: e.javaClass.simpleName})."
                })
            }
        }.start()
    }

    @Suppress("DEPRECATION")
    private fun signers(pi: PackageInfo?): Set<String> {
        if (pi == null) return emptySet()
        val sigs = if (Build.VERSION.SDK_INT >= 28) pi.signingInfo?.apkContentsSigners else pi.signatures
        return sigs?.map { s -> MessageDigest.getInstance("SHA-256").digest(s.toByteArray()).joinToString("") { "%02x".format(it) } }?.toSet()
            ?: emptySet()
    }

    @Suppress("DEPRECATION")
    private fun check(ctx: Context, apk: File) {
        val pm = ctx.packageManager
        val flag = if (Build.VERSION.SDK_INT >= 28) PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES
        val arch = pm.getPackageArchiveInfo(apk.absolutePath, flag) ?: throw SecurityException("Yeh file sahi APK nahi hai.")
        if (arch.packageName != ctx.packageName) throw SecurityException("Yeh APK Hoola ka nahi hai.")
        val mine = signers(pm.getPackageInfo(ctx.packageName, flag))
        val theirs = signers(arch)
        if (mine.isEmpty() || theirs.isEmpty() || mine.intersect(theirs).isEmpty()) {
            throw SecurityException("Naye APK ka signature is app se alag hai, isliye update nahi kiya.")
        }
    }

    /** Hands the checked APK to Android's installer; Android asks the owner. Status comes back to MainActivity. */
    fun install(act: Activity, path: String): String? {
        if (channel(act) != "github") return "play"
        if (Build.VERSION.SDK_INT >= 26 && !act.packageManager.canRequestPackageInstalls()) {
            openInstallPermission(act)
            return "permission"
        }
        return try {
            val f = File(path)
            val pi = act.packageManager.packageInstaller
            val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
            params.setAppPackageName(act.packageName)
            if (Build.VERSION.SDK_INT >= 31) params.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_REQUIRED)
            val id = pi.createSession(params)
            pi.openSession(id).use { s ->
                f.inputStream().use { inp -> s.openWrite("hoola.apk", 0, f.length()).use { o -> inp.copyTo(o); s.fsync(o) } }
                val i = Intent(act, MainActivity::class.java).setAction(ACTION_STATUS).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
                val flags = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
                s.commit(PendingIntent.getActivity(act, 51, i, flags).intentSender)
            }
            null
        } catch (e: Exception) {
            "Install shuru nahi hua (${e.message ?: e.javaClass.simpleName})."
        }
    }

    /** From MainActivity when the installer reports back. Returns a link message for Flutter, or null. */
    @Suppress("DEPRECATION")
    fun onStatus(act: Activity, intent: Intent): String? {
        val st = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, -999)
        if (st == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            val confirm = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                          else intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
            if (confirm != null) try { act.startActivity(confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } catch (_: Exception) {}
            return null
        }
        val msg = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: ""
        return "update:" + org.json.JSONObject().put("status", st).put("ok", st == PackageInstaller.STATUS_SUCCESS)
            .put("message", msg.take(200)).toString()
    }
}
