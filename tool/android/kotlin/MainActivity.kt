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
        micChannel(flutterEngine)
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
                    "status" -> result.success(Store.status(this))
                    "claim" -> result.success(Store.claim(this, call.argument<String>("id") ?: ""))
                    "batteryOptimized" -> result.success(batteryOptimized())
                    "askBattery" -> { askBattery(); result.success(null) }
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
                        result.success(err)
                    }
                    "voicePlay" -> { (call.arguments as? ByteArray)?.let { VoiceAudio.play(it) }; result.success(null) }
                    "voiceFlush" -> { VoiceAudio.flush(); result.success(null) }
                    "voiceStop" -> { VoiceAudio.stop(this); result.success(null) }
                    else -> result.notImplemented()
                }
            } catch (e: Exception) {
                result.error("native", e.message, null)
            }
        }
    }

    private val main = Handler(Looper.getMainLooper())

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

    private fun handleIntent(intent: Intent?) {
        val data = intent?.data ?: return
        if (data.scheme == "santosh" && data.host == "auth") {
            val token = data.getQueryParameter("session") ?: return
            val sink = linkSink
            if (sink != null) main.post { sink.success(token) } else pendingLink = token
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun micChannel(flutterEngine: FlutterEngine) {
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
        super.onDestroy()
    }

    override fun onResume() {
        super.onResume()
        visible = true
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

    private fun askBattery() {
        if (Build.VERSION.SDK_INT < 23) return
        try {
            startActivity(Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName")))
        } catch (e: Exception) {
            startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
        }
    }

    private fun hasCalendar(): Boolean =
        Build.VERSION.SDK_INT < 23 || checkSelfPermission(Manifest.permission.WRITE_CALENDAR) == PackageManager.PERMISSION_GRANTED
}
