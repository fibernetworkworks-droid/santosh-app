package com.newtika.santosh

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import android.os.Handler
import android.os.Looper
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

/** Flutter host + the "santosh/native" channel that controls the background service. */
class MainActivity : FlutterActivity() {
    companion object {
        /** True while the app is on screen; the service then leaves notifications and phone actions to Flutter. */
        @Volatile var visible = false
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        RemoteService.restore(this)   // the Bluetooth TV remote comes back on if the owner had it on
        micChannel(flutterEngine)
        val callCh = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "santosh/call")
        CallService.onHangup = { main.post { try { callCh.invokeMethod("hangup", null) } catch (_: Exception) {} } }
        // call audio trouble (another app has the audio, the microphone or speaker was lost) goes to the call screen
        VoiceAudio.onState = { state, detail ->
            main.post { try { callCh.invokeMethod("audio", mapOf("state" to state, "detail" to detail)) } catch (_: Exception) {} }
        }
        linkChannel(flutterEngine)
        handleIntent(intent)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "santosh/native").setMethodCallHandler { call, result ->
            try {
                when (call.method) {
                    "startService" -> {
                        Store.saveConfig(
                            this,
                            call.argument<String>("server") ?: "",
                            call.argument<String>("key") ?: "",
                            call.argument<String>("conv") ?: "",
                            (call.argument<Number>("after") ?: 0).toLong()
                        )
                        SantoshService.start(this)
                        result.success(true)
                    }
                    "stopService" -> {
                        Store.setEnabled(this, false)
                        SantoshService.stop(this)
                        result.success(true)
                    }
                    "isRunning" -> result.success(SantoshService.running)
                    "pushInit" -> {
                        SantoshPush.init(this, call.argument<String>("server") ?: "", call.argument<String>("key") ?: "")
                        result.success(Store.pushToken(this))
                    }
                    "wakeStart" -> {
                        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 44)
                            result.success("permission")
                        } else {
                            WakeService.status = "Shuru ho raha hai…"
                            WakeService.start(this)
                            result.success("ok")
                        }
                    }
                    "wakeStop" -> { WakeService.stop(this); WakeService.status = "Band"; result.success(null) }
                    "wakeStatus" -> result.success(mapOf("on" to WakeService.running, "wanted" to WakeService.wanted(this), "status" to WakeService.status))
                    "wakeResume" -> { WakeService.resume(this); result.success(null) }
                    "wakePause" -> { WakeService.pauseFor(this); result.success(null) }
                    "isLocked" -> result.success(keyguardLocked())
                    "requestUnlock" -> requestUnlock { ok -> result.success(ok) }
                    "leaveLockScreen" -> { leaveLockScreen(); result.success(null) }
                    "hasLocation" -> result.success(hasLocation())
                    "askLocation" -> {
                        if (!hasLocation()) requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION), 43)
                        result.success(null)
                    }
                    "location" -> currentLocation { loc -> result.success(loc) }
                    "openExternal" -> result.success(openExternal(call.argument<String>("url") ?: "", call.argument<String>("package") ?: ""))
                    "status" -> result.success(Store.status(this))
                    "claim" -> result.success(Store.claim(this, call.argument<String>("id") ?: ""))
                    "batteryOptimized" -> result.success(batteryOptimized())
                    "askBattery" -> { askBattery(); result.success(null) }
                    "exactAlarms" -> result.success(exactAlarmsAllowed())
                    "callStatus" -> result.success(mapOf("running" to CallService.running, "problem" to CallService.problem,
                        "notifications" to notificationsAllowed(), "brand" to Build.MANUFACTURER.lowercase(),
                        "batteryOptimized" to batteryOptimized()))
                    "openAutostart" -> { openAutostart(); result.success(null) }
                    "openNotificationSettings" -> {
                        try {
                            startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName))
                        } catch (_: Exception) {
                            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
                        }
                        result.success(null)
                    }
                    "askExactAlarms" -> { askExactAlarms(); result.success(null) }
                    "hasCalendar" -> result.success(hasCalendar())
                    "askCalendar" -> {
                        if (Build.VERSION.SDK_INT >= 23) {
                            requestPermissions(arrayOf(Manifest.permission.READ_CALENDAR, Manifest.permission.WRITE_CALENDAR), 41)
                        }
                        result.success(null)
                    }
                    "voiceStart" -> {
                        val err = VoiceAudio.start(this)
                        if (err == "permission") requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 42)
                        if (err == null) CallService.start(this)   // keeps the call alive when the screen locks
                        result.success(err)
                    }
                    "voicePlay" -> { (call.arguments as? ByteArray)?.let { VoiceAudio.play(it) }; result.success(null) }
                    "voiceFlush" -> { VoiceAudio.flush(); result.success(null) }
                    "voiceStop" -> { VoiceAudio.stop(this); CallService.stop(this); result.success(null) }
                    // ---- Ghar: home devices (IR AC, Bluetooth TV remote, DIAL, music) ----
                    "homeCaps" -> result.success(HomeDevices.caps(this))
                    "homePaired" -> result.success(HomeDevices.paired(this))
                    "homeAskBluetooth" -> {
                        askBluetooth()
                        result.success(HomeDevices.hasBluetoothPermission(this) && BtControl.canScan(this))
                    }
                    "usageAllowed" -> result.success(ScrollStats.allowed(this))
                    "usageSettings" -> { ScrollStats.openSettings(this); result.success(null) }
                    "usageDays" -> {
                        val days = (call.argument<Number>("days") ?: 7).toInt()
                        Thread {
                            val r = try { ScrollStats.collect(this, days) } catch (_: Exception) { emptyList() }
                            main.post { result.success(r) }
                        }.start()
                    }
                    "compressVideo" -> {
                        VideoShrink.run(this, call.argument<String>("path") ?: "", (call.argument<Number>("mb") ?: 24).toInt(),
                            (call.argument<Number>("clipMs") ?: 0).toLong()) { out, err ->
                            main.post { result.success(mapOf("path" to out, "error" to err)) }
                        }
                    }
                    "compressProgress" -> result.success(VideoShrink.progress())
                    "compressCancel" -> { VideoShrink.cancel(); result.success(null) }
                    "bgHealth" -> result.success(bgHealth())
                    "openMakerBattery" -> { openMakerBattery(); result.success(null) }
                    "openMakerPerms" -> { openMakerPerms(); result.success(null) }
                    "btRun" -> {
                        val action = call.argument<String>("action") ?: "status"
                        val args = try { org.json.JSONObject(call.argument<String>("args") ?: "{}") } catch (_: Exception) { org.json.JSONObject() }
                        BtControl.run(this, action, args) { ok, res, err ->
                            if (err == "permission") main.post { askBluetooth() }
                            main.post {
                                result.success(mapOf("ok" to ok, "result" to BtControl.toMap(res), "error" to err))
                            }
                        }
                    }
                    "homeRemote" -> {
                        if (call.argument<Boolean>("on") == true) {
                            val r = RemoteService.start(this)
                            if (r == "permission") askBluetooth()
                            result.success(r)
                        } else {
                            RemoteService.stop(this)
                            result.success("ok")
                        }
                    }
                    "homeDiscoverable" -> {
                        val r = try {
                            startActivity(Intent(android.bluetooth.BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE)
                                .putExtra(android.bluetooth.BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, 120))
                            "ok"
                        } catch (e: Exception) {
                            "Bluetooth settings nahi khul paye"
                        }
                        result.success(r)
                    }
                    "homeRun" -> {
                        val json = call.argument<String>("action") ?: ""
                        HomeDevices.run(this, json) { err -> main.post { result.success(err ?: "ok") } }
                    }
                    else -> result.notImplemented()
                }
            } catch (e: Exception) {
                result.error("native", e.message, null)
            }
        }
    }

    private val main = Handler(Looper.getMainLooper())

    /** "Nearby devices" (Android 12+: connect, scan, advertise); older phones need location to scan. */
    private fun askBluetooth() {
        if (Build.VERSION.SDK_INT >= 31) {
            val need = arrayOf(Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_ADVERTISE)
                .filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
            if (need.isNotEmpty()) requestPermissions(need.toTypedArray(), 45)
        } else if (!hasLocation()) {
            requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION), 46)
        }
    }

    @Volatile private var linkSink: EventChannel.EventSink? = null
    @Volatile private var pendingLink: String? = null

    private fun linkChannel(flutterEngine: FlutterEngine) {
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, "santosh/links").setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink) {
                linkSink = events
                pendingLink?.let { main.post { events.success(it) }; pendingLink = null }
            }

            override fun onCancel(arguments: Any?) { linkSink = null }
        })
    }

    private fun keyguardLocked(): Boolean =
        (getSystemService(KEYGUARD_SERVICE) as android.app.KeyguardManager).isKeyguardLocked

    /** Only a voice call may show over the lock screen; everything else asks to unlock first. */
    private fun showOverLock(on: Boolean) {
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(on)
            setTurnScreenOn(on)
        } else {
            @Suppress("DEPRECATION")
            val f = android.view.WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or android.view.WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
            if (on) window.addFlags(f) else window.clearFlags(f)
        }
    }

    private fun requestUnlock(done: (Boolean) -> Unit) {
        if (!keyguardLocked()) { done(true); return }
        if (Build.VERSION.SDK_INT >= 26) {
            (getSystemService(KEYGUARD_SERVICE) as android.app.KeyguardManager).requestDismissKeyguard(this,
                object : android.app.KeyguardManager.KeyguardDismissCallback() {
                    override fun onDismissSucceeded() { showOverLock(false); done(true) }
                    override fun onDismissCancelled() { done(false) }
                    override fun onDismissError() { done(false) }
                })
        } else done(false)
    }

    private fun leaveLockScreen() {
        if (keyguardLocked()) {
            showOverLock(false)
            moveTaskToBack(true)
        } else showOverLock(false)
        WakeService.resume(this)
    }

    override fun onStop() {
        super.onStop()
        showOverLock(false)   // never stay above the lock screen after the call is gone
    }

    /** v0.49 "Share to Hoola" from any app: files are copied into the app's cache (25 MB each, max 6) and handed to
     *  Flutter as `share:{"files":[{path,name,size}],"text":...}`; nothing is uploaded until the owner sends. */
    private val BIG_VIDEO = 2L * 1024 * 1024 * 1024

    private fun sharedPayload(intent: Intent): String? {
        val uris = ArrayList<Uri>()
        if (intent.action == Intent.ACTION_SEND) {
            @Suppress("DEPRECATION")
            (if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
             else intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM))?.let { uris.add(it) }
        } else {
            @Suppress("DEPRECATION")
            (if (Build.VERSION.SDK_INT >= 33) intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java)
             else intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM))?.let { uris.addAll(it) }
        }
        val text = (intent.getStringExtra(Intent.EXTRA_TEXT) ?: "") .let {
            val subj = intent.getStringExtra(Intent.EXTRA_SUBJECT) ?: ""
            if (subj.isNotBlank() && !it.contains(subj)) "$subj\n$it" else it
        }.trim()
        val dir = java.io.File(cacheDir, "shared").apply { mkdirs() }
        dir.listFiles()?.forEach { f -> if (System.currentTimeMillis() - f.lastModified() > 6 * 3600_000L) f.delete() }
        val files = org.json.JSONArray()
        var skipped = 0
        val skippedNames = ArrayList<String>()
        for (u in uris.take(6)) {
            try {
                var name = "file"
                var size = -1L
                contentResolver.query(u, null, null, null, null)?.use { c ->
                    if (c.moveToFirst()) {
                        val ni = c.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                        val si = c.getColumnIndex(android.provider.OpenableColumns.SIZE)
                        if (ni >= 0) name = c.getString(ni) ?: name
                        if (si >= 0 && !c.isNull(si)) size = c.getLong(si)
                    }
                }
                val mime = (contentResolver.getType(u) ?: "").lowercase()
                val isVideo = mime.startsWith("video/") || Regex("(?i)\\.(mp4|mov|m4v|3gp|mkv|webm)$").containsMatchIn(name)
                // v0.56 a big video is kept (Hoola makes it smaller before it goes); other big files can't go
                val limit = if (isVideo) BIG_VIDEO else 25L * 1024 * 1024
                if (size > limit || (size > 0 && size + 64L * 1024 * 1024 > cacheDir.usableSpace)) { skipped++; skippedNames.add(name); continue }
                val safe = name.replace(Regex("[^\\w.\\- ()]"), "_").take(120).ifBlank { "file" }
                val out = java.io.File(dir, "${System.currentTimeMillis()}_$safe")
                var n = 0L
                contentResolver.openInputStream(u)?.use { inp ->
                    out.outputStream().use { o ->
                        val buf = ByteArray(64 * 1024)
                        while (true) {
                            val r = inp.read(buf)
                            if (r < 0) break
                            n += r
                            if (n > limit) break
                            o.write(buf, 0, r)
                        }
                    }
                }
                if (n > limit || n == 0L) { out.delete(); skipped++; skippedNames.add(name); continue }
                val big = n > 25L * 1024 * 1024
                files.put(org.json.JSONObject().put("path", out.absolutePath).put("name", name).put("size", n)
                    .put("mime", mime).put("video", isVideo).put("big", big))
            } catch (_: Exception) { skipped++ }
        }
        if (uris.size > 6) skipped += uris.size - 6
        if (files.length() == 0 && text.isEmpty()) return null
        return "share:" + org.json.JSONObject().put("files", files).put("text", text).put("skipped", skipped)
            .put("skipped_names", org.json.JSONArray(skippedNames.take(6))).toString()
    }

    /** v0.56 What Android itself knows about Hoola running in the background: battery optimisation, "restricted",
     *  the standby bucket, and how the app's process ended lately (Android 11+), so the app can say "your phone stopped
     *  Hoola 3 times this week" and open the right page. Read-only. */
    private fun bgHealth(): Map<String, Any?> {
        val am = getSystemService(ACTIVITY_SERVICE) as android.app.ActivityManager
        val exits = ArrayList<Map<String, Any?>>()
        if (Build.VERSION.SDK_INT >= 30) {
            try {
                for (e in am.getHistoricalProcessExitReasons(packageName, 0, 30)) {
                    exits.add(mapOf("ts" to e.timestamp, "reason" to e.reason, "importance" to e.importance,
                        "desc" to (e.description ?: "").take(160), "process" to e.processName))
                }
            } catch (_: Exception) {}
        }
        val restricted = if (Build.VERSION.SDK_INT >= 28) try { am.isBackgroundRestricted } catch (_: Exception) { false } else false
        val bucket = if (Build.VERSION.SDK_INT >= 28) try {
            (getSystemService(USAGE_STATS_SERVICE) as android.app.usage.UsageStatsManager).appStandbyBucket
        } catch (_: Exception) { 0 } else 0
        return mapOf("brand" to Build.MANUFACTURER.lowercase(), "model" to Build.MODEL, "sdk" to Build.VERSION.SDK_INT,
            "battery_optimized" to batteryOptimized(), "background_restricted" to restricted, "standby_bucket" to bucket,
            "notifications" to notificationsAllowed(), "exits" to exits)
    }

    private fun tryOpen(tries: List<Intent>): Boolean {
        for (i in tries) {
            try { startActivity(i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return true } catch (_: Exception) {}
        }
        return false
    }

    /** The phone maker's own battery-saver page for Hoola (MIUI / HyperOS, ColorOS, Funtouch / OriginOS, One UI). */
    private fun openMakerBattery() {
        val pkg = packageName
        val label = try { packageManager.getApplicationLabel(applicationInfo).toString() } catch (_: Exception) { "Hoola" }
        val ok = tryOpen(listOf(
            Intent().setClassName("com.miui.powerkeeper", "com.miui.powerkeeper.ui.HiddenAppsConfigActivity")
                .putExtra("package_name", pkg).putExtra("package_label", label),
            Intent().setClassName("com.coloros.oppoguardelf", "com.coloros.powermanager.fuelgaue.PowerUsageModelActivity"),
            Intent().setClassName("com.coloros.oppoguardelf", "com.coloros.powermanager.fuelgaue.PowerSaverModeActivity"),
            Intent().setClassName("com.oplus.battery", "com.oplus.powermanager.fuelgaue.PowerUsageModelActivity"),
            Intent().setClassName("com.vivo.abe", "com.vivo.applicationbehaviorengine.ui.ExcessivePowerManagerActivity"),
            Intent().setClassName("com.iqoo.powersaving", "com.iqoo.powersaving.PowerSavingManagerActivity"),
            Intent().setClassName("com.samsung.android.lool", "com.samsung.android.sm.battery.ui.BatteryActivity"),
            Intent().setClassName("com.samsung.android.sm_cn", "com.samsung.android.sm.battery.ui.BatteryActivity")))
        if (!ok) askBattery()
    }

    /** MIUI "Other permissions" (show on lock screen, pop-up windows from the background), else app info. */
    private fun openMakerPerms() {
        val pkg = packageName
        tryOpen(listOf(
            Intent("miui.intent.action.APP_PERM_EDITOR").setClassName("com.miui.securitycenter",
                "com.miui.permcenter.permissions.PermissionsEditorActivity").putExtra("extra_pkgname", pkg),
            Intent("miui.intent.action.APP_PERM_EDITOR").setClassName("com.miui.securitycenter",
                "com.miui.permcenter.permissions.AppPermissionsEditorActivity").putExtra("extra_pkgname", pkg),
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).setData(Uri.parse("package:$pkg"))))
    }

    private fun handleIntent(intent: Intent?) {
        val action = intent?.action
        if (action == Intent.ACTION_SEND || action == Intent.ACTION_SEND_MULTIPLE) {
            val copy = Intent(intent!!)
            intent?.action = null   // don't share the same thing again on a config change
            // v0.56 copying a big video takes seconds: off the main thread, so the app never freezes ("not responding")
            Thread {
                val msg = try { sharedPayload(copy) } catch (_: Exception) { null } ?: return@Thread
                main.post {
                    val sink = linkSink
                    if (sink != null) sink.success(msg) else pendingLink = msg
                }
            }.start()
            return
        }
        if (action == WakeService.ACTION_WAKE || action == Intent.ACTION_ASSIST || action == "android.intent.action.VOICE_COMMAND") {
            val locked = keyguardLocked()
            if (locked && action == WakeService.ACTION_WAKE) showOverLock(true)
            (getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager).cancel(WakeService.HEARD_ID)
            val msg = if (locked) "wake:locked" else "wake:open"
            val sink = linkSink
            if (sink != null) main.post { sink.success(msg) } else pendingLink = msg
            return
        }
        val data = intent?.data ?: return
        val msg = when {
            data.scheme == "santosh" && data.host == "auth" -> data.getQueryParameter("session") ?: return
            (data.scheme == "santosh" || data.scheme == "hoola") && data.host == "connect" -> "connect:" + (data.getQueryParameter("c") ?: return)
            data.scheme == "santosh" && data.host == "bazar" -> "bazar:linked=" + (data.getQueryParameter("linked") ?: "0")
            data.scheme == "santosh" && data.host == "tv" -> "tv:" + (data.getQueryParameter("ch") ?: return)
            data.scheme == "santosh" && data.host == "mail" -> "mail:ok=" + (data.getQueryParameter("ok") ?: "0")
            data.scheme == "santosh" && data.host == "calendar" -> "calendar:ok=" + (data.getQueryParameter("ok") ?: "0")
            data.scheme == "santosh" && data.host in setOf("sheets", "drive", "forms", "slides", "photos", "youtube") -> data.host + ":ok=" + (data.getQueryParameter("ok") ?: "0")
            else -> return
        }
        val sink = linkSink
        if (sink != null) main.post { sink.success(msg) } else pendingLink = msg
    }

    private fun hasLocation(): Boolean =
        checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    /** One fresh fix (Android 11+), else the newest last-known position. Null without permission. */
    @android.annotation.SuppressLint("MissingPermission")
    private fun currentLocation(done: (Map<String, Any>?) -> Unit) {
        if (!hasLocation()) { done(null); return }
        val lm = getSystemService(LOCATION_SERVICE) as android.location.LocationManager
        fun pack(l: android.location.Location?): Map<String, Any>? =
            l?.let { mapOf("lat" to it.latitude, "lng" to it.longitude, "accuracy" to it.accuracy.toDouble(), "time" to it.time) }
        val providers = lm.getProviders(true)
        var best: android.location.Location? = null
        for (p in providers) {
            val l = try { lm.getLastKnownLocation(p) } catch (_: Exception) { null } ?: continue
            if (best == null || l.time > best!!.time) best = l
        }
        val fresh = best != null && System.currentTimeMillis() - best!!.time < 2 * 60 * 1000
        if (fresh || Build.VERSION.SDK_INT < Build.VERSION_CODES.R) { done(pack(best)); return }
        val provider = when {
            providers.contains(android.location.LocationManager.FUSED_PROVIDER) -> android.location.LocationManager.FUSED_PROVIDER
            providers.contains(android.location.LocationManager.NETWORK_PROVIDER) -> android.location.LocationManager.NETWORK_PROVIDER
            providers.contains(android.location.LocationManager.GPS_PROVIDER) -> android.location.LocationManager.GPS_PROVIDER
            else -> null
        }
        if (provider == null) { done(pack(best)); return }
        var answered = false
        val fallback = best
        val signal = android.os.CancellationSignal()
        main.postDelayed({ if (!answered) { answered = true; signal.cancel(); done(pack(fallback)) } }, 8000)
        try {
            lm.getCurrentLocation(provider, signal, mainExecutor) { l ->
                if (!answered) { answered = true; done(pack(l ?: fallback)) }
            }
        } catch (_: Exception) {
            if (!answered) { answered = true; done(pack(fallback)) }
        }
    }

    private fun installed(pkg: String): Boolean = try {
        packageManager.getPackageInfo(pkg, 0); true
    } catch (_: Exception) { false }

    /** Opens a UPI payment, an app link or an app. Only called from a user tap, so Android allows it.
     *  Santosh never sees the UPI PIN: the user types it in their UPI app. */
    private fun openExternal(url: String, pkg: String): String {
        try {
            if (url.isNotBlank()) {
                val uri = Uri.parse(url)
                val scheme = uri.scheme ?: ""
                // "tel" only opens the dialer with the number filled in (SOS 112/108); the user presses call
                if (scheme !in setOf("upi", "tez", "phonepe", "paytmmp", "https", "http", "intent", "tel")) return "Link sahi nahi hai"
                if (scheme in setOf("upi", "tez", "phonepe", "paytmmp")) {
                    // prefer the chosen app; fall back to the standard upi:// chooser (every UPI app handles it)
                    if (pkg.isNotBlank() && installed(pkg)) {
                        val generic = Uri.parse("upi://pay?" + (uri.encodedQuery ?: ""))
                        val i = Intent(Intent.ACTION_VIEW, generic).setPackage(pkg).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        try { startActivity(i); return "ok" } catch (_: Exception) {}
                        try { startActivity(Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return "ok" } catch (_: Exception) {}
                    }
                    val generic = Intent(Intent.ACTION_VIEW, Uri.parse("upi://pay?" + (uri.encodedQuery ?: "")))
                    startActivity(Intent.createChooser(generic, "Kis UPI app se pay karein?").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                    return "ok"
                }
                val i = Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                if (pkg.isNotBlank() && installed(pkg)) i.setPackage(pkg)
                try { startActivity(i); return "ok" } catch (_: Exception) { i.setPackage(null); startActivity(i); return "ok" }
            }
            if (pkg.isNotBlank()) {
                val launch = packageManager.getLaunchIntentForPackage(pkg)
                if (launch != null) { startActivity(launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return "ok" }
                try {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$pkg")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                } catch (_: Exception) {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=$pkg")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                }
                return "App install nahi hai; Play Store khol diya"
            }
            return "Kholne ke liye kuch nahi mila"
        } catch (e: Exception) {
            return "Nahi khul paya: ${e.message ?: e.javaClass.simpleName}"
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun micChannel(flutterEngine: FlutterEngine) {
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, "santosh/vad").setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink) {
                Thread { SileroVad.init(applicationContext); SileroVad.reset() }.start()
                VoiceAudio.vadSink = { p -> main.post { events.success(p.toDouble()) } }
            }

            override fun onCancel(arguments: Any?) {
                VoiceAudio.vadSink = null
            }
        })
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, "santosh/mic").setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink) {
                VoiceAudio.sink = { bytes -> main.post { events.success(bytes) } }
            }

            override fun onCancel(arguments: Any?) {
                VoiceAudio.sink = null
            }
        })
    }

    override fun onDestroy() {
        VoiceAudio.stop(this)
        CallService.stop(this)
        CallService.onHangup = null
        VoiceAudio.onState = null
        super.onDestroy()
    }

    override fun onResume() {
        super.onResume()
        visible = true
        // "Hey Santosh" after a phone restart: Android lets the mic service start only while the app is open
        if (WakeService.wanted(this) && !WakeService.running &&
            checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            try { WakeService.start(this) } catch (_: Exception) {}
        }
        Notify.clearMessages(this)
    }

    override fun onPause() {
        visible = false
        super.onPause()
    }

    private fun batteryOptimized(): Boolean {
        if (Build.VERSION.SDK_INT < 23) return false
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        return !pm.isIgnoringBatteryOptimizations(packageName)
    }

    /** Opens Android's battery settings for Santosh (Play policy: no direct "ignore optimizations" request). */
    private fun askBattery() {
        if (Build.VERSION.SDK_INT < 23) return
        val tries = listOf(
            Intent("android.settings.APP_BATTERY_SETTINGS").setData(Uri.parse("package:$packageName")),   // Android 14+
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).setData(Uri.parse("package:$packageName")),
            Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
        for (i in tries) {
            try { startActivity(i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return } catch (_: Exception) {}
        }
    }

    private fun notificationsAllowed(): Boolean {
        val nm = getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager
        return if (Build.VERSION.SDK_INT >= 24) nm.areNotificationsEnabled() else true
    }

    /** Phone makers' own "autostart / background activity" screens (Vivo, Oppo, Realme, Xiaomi...), else app info. */
    private fun openAutostart() {
        val pkg = packageName
        val tries = listOf(
            Intent().setClassName("com.vivo.permissionmanager", "com.vivo.permissionmanager.activity.BgStartUpManagerActivity"),
            Intent().setClassName("com.iqoo.secure", "com.iqoo.secure.ui.phoneoptimize.BgStartUpManager"),
            Intent().setClassName("com.iqoo.secure", "com.iqoo.secure.ui.phoneoptimize.AddWhiteListActivity"),
            Intent().setClassName("com.coloros.safecenter", "com.coloros.safecenter.permission.startup.StartupAppListActivity"),
            Intent().setClassName("com.coloros.safecenter", "com.coloros.safecenter.startupapp.StartupAppListActivity"),
            Intent().setClassName("com.oppo.safe", "com.oppo.safe.permission.startup.StartupAppListActivity"),
            Intent().setClassName("com.miui.securitycenter", "com.miui.permcenter.autostart.AutoStartManagementActivity"),
            Intent().setClassName("com.huawei.systemmanager", "com.huawei.systemmanager.startupmgr.ui.StartupNormalAppListActivity"),
            Intent("android.settings.APP_BATTERY_SETTINGS").setData(Uri.parse("package:$pkg")),
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).setData(Uri.parse("package:$pkg")))
        for (i in tries) {
            try { startActivity(i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return } catch (_: Exception) {}
        }
    }

    private fun exactAlarmsAllowed(): Boolean {
        if (Build.VERSION.SDK_INT < 31) return true
        val am = getSystemService(ALARM_SERVICE) as android.app.AlarmManager
        return am.canScheduleExactAlarms()
    }

    private fun askExactAlarms() {
        if (Build.VERSION.SDK_INT < 31) return
        try {
            startActivity(Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM, Uri.parse("package:$packageName")))
        } catch (_: Exception) {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
        }
    }

    private fun hasCalendar(): Boolean =
        Build.VERSION.SDK_INT < 23 || checkSelfPermission(Manifest.permission.WRITE_CALENDAR) == PackageManager.PERMISSION_GRANTED
}
