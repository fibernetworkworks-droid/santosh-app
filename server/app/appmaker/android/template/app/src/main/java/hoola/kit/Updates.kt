package hoola.kit

// Made by Hoola App Sahayak (v0.319 APP FEATURES). "Your order is Packed" / "New order: Asha" without the app open:
// Android's own JobScheduler asks the business's Hoola server what changed for this account at most every 15 minutes
// (when there is a network; Android may wait longer to save battery - no exemption is ever asked), and shows a normal
// notification. Nothing runs when nobody is signed in. Instant push (FCM) needs the business's own Firebase project:
// a later step, this works without one.

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.job.JobInfo
import android.app.job.JobParameters
import android.app.job.JobScheduler
import android.app.job.JobService
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import java.net.URLEncoder

object Updates {
    private const val JOB_ID = 47110
    private const val CHANNEL = "hoola_updates"

    /** Once per app start: remember where the server is (the job may run in a fresh process) and keep the job booked. */
    fun schedule(ctx: Context, baseUrl: String, appKey: String) {
        Store.put(ctx, "cloud_base", baseUrl)
        Store.put(ctx, "cloud_key", appKey)
        val js = ctx.getSystemService(JobScheduler::class.java) ?: return
        if (js.getPendingJob(JOB_ID) != null) return
        try {
            js.schedule(
                JobInfo.Builder(JOB_ID, ComponentName(ctx, UpdatesJob::class.java))
                    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                    .setPeriodic(15 * 60 * 1000L)
                    .setPersisted(true)
                    .build()
            )
        } catch (_: Exception) {
        }
    }

    fun canNotify(ctx: Context): Boolean = Build.VERSION.SDK_INT < 33 ||
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    /** Asks the server what changed since the last check and shows one notification per change. Returns how many. */
    suspend fun check(ctx: Context): Int {
        if (!Cloud.ready) Cloud.init(Store.get(ctx, "cloud_base"), Store.get(ctx, "cloud_key"))
        if (Auth.token().isEmpty()) Auth.load(ctx)
        if (!Cloud.ready || Auth.token().isEmpty()) return 0
        val since = Store.get(ctx, "upd_since")
        val q = if (since.isNotEmpty()) "?since=" + URLEncoder.encode(since, "UTF-8") else ""
        val r = Cloud.call("GET", "/updates$q", null, Auth.token())
        if (!r.ok) return 0
        val now = r.body.optString("now")
        if (now.isNotEmpty()) Store.put(ctx, "upd_since", now)
        if (since.isEmpty()) return 0                       // the very first check only sets the mark: no old news
        val items = r.body.optJSONArray("items") ?: return 0
        var shown = 0
        for (i in 0 until items.length()) {
            val it = items.optJSONObject(i) ?: continue
            val title = it.optString("title")
            val text = if (it.optString("kind") == "new") Strings.newEntry
            else listOf(it.optString("status"), it.optString("paid").takeIf { p -> p.isNotEmpty() && p != "No" } ?: "")
                .filter { s -> s.isNotEmpty() }.joinToString(" · ")
            if (show(ctx, it.optString("id").hashCode(), title, text)) shown++
        }
        return shown
    }

    private fun show(ctx: Context, id: Int, title: String, text: String): Boolean {
        if (!canNotify(ctx)) return false
        val nm = ctx.getSystemService(NotificationManager::class.java) ?: return false
        if (nm.getNotificationChannel(CHANNEL) == null) {
            nm.createNotificationChannel(NotificationChannel(CHANNEL, Strings.updatesChannel, NotificationManager.IMPORTANCE_DEFAULT))
        }
        val open = ctx.packageManager.getLaunchIntentForPackage(ctx.packageName)
        val pi = open?.let { PendingIntent.getActivity(ctx, id, it, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT) }
        val n = NotificationCompat.Builder(ctx, CHANNEL)
            .setSmallIcon(ctx.applicationInfo.icon)
            .setContentTitle(title.ifEmpty { AppData.appName })
            .setContentText(text)
            .setAutoCancel(true)
            .apply { if (pi != null) setContentIntent(pi) }
            .build()
        return try {
            NotificationManagerCompat.from(ctx).notify(id, n)
            true
        } catch (_: SecurityException) {
            false
        }
    }
}

/** Android runs this when it suits the battery (15 minutes at the soonest), only with a network. */
class UpdatesJob : JobService() {
    private var work: Job? = null

    override fun onStartJob(params: JobParameters): Boolean {
        work = CoroutineScope(Dispatchers.IO).launch {
            try { Updates.check(applicationContext) } catch (_: Exception) { }
            jobFinished(params, false)
        }
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean {
        work?.cancel()
        return true
    }
}
