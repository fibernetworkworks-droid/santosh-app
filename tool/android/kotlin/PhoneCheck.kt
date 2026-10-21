package com.newtika.santosh

import android.annotation.SuppressLint
import android.app.ActivityManager
import android.app.NotificationManager
import android.app.usage.UsageStatsManager
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.os.PowerManager
import android.os.StatFs
import android.os.SystemClock
import android.provider.Settings
import android.telephony.TelephonyManager

/**
 * v0.90 Phone Doctor: what the phone itself says when the owner reports a fault ("phone garam hota hai", "network nahi").
 * Only facts about the phone's own state (battery, storage, memory, network, sound, a few settings, which apps were used
 * most): never messages, contacts, photos, numbers or anything typed. No new permission is asked; what Android doesn't
 * allow without one is simply left out.
 */
object PhoneCheck {
    fun collect(ctx: Context): Map<String, Any?> {
        val out = HashMap<String, Any?>()
        out["brand"] = Build.MANUFACTURER
        out["model"] = Build.MODEL
        out["sdk"] = Build.VERSION.SDK_INT
        out["android"] = Build.VERSION.RELEASE
        out["security_patch"] = if (Build.VERSION.SDK_INT >= 23) Build.VERSION.SECURITY_PATCH else ""
        out["uptime_hours"] = SystemClock.elapsedRealtime() / 3_600_000.0
        safe(out) { battery(ctx, it) }
        safe(out) { storage(it) }
        safe(out) { memory(ctx, it) }
        safe(out) { power(ctx, it) }
        safe(out) { network(ctx, it) }
        safe(out) { sound(ctx, it) }
        safe(out) { settings(ctx, it) }
        safe(out) { topApps(ctx, it) }
        return out
    }

    private inline fun safe(out: HashMap<String, Any?>, block: (HashMap<String, Any?>) -> Unit) {
        try { block(out) } catch (_: Throwable) { }
    }

    private fun battery(ctx: Context, out: HashMap<String, Any?>) {
        val i = ctx.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)) ?: return
        val level = i.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = i.getIntExtra(BatteryManager.EXTRA_SCALE, 100)
        out["battery_pct"] = if (level >= 0 && scale > 0) level * 100 / scale else null
        out["battery_temp_c"] = i.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Int.MIN_VALUE).let { if (it == Int.MIN_VALUE) null else it / 10.0 }
        out["battery_health"] = when (i.getIntExtra(BatteryManager.EXTRA_HEALTH, 0)) {
            BatteryManager.BATTERY_HEALTH_GOOD -> "good"
            BatteryManager.BATTERY_HEALTH_OVERHEAT -> "overheat"
            BatteryManager.BATTERY_HEALTH_DEAD -> "dead"
            BatteryManager.BATTERY_HEALTH_OVER_VOLTAGE -> "over_voltage"
            BatteryManager.BATTERY_HEALTH_UNSPECIFIED_FAILURE -> "failure"
            BatteryManager.BATTERY_HEALTH_COLD -> "cold"
            else -> "unknown"
        }
        out["plugged"] = when (i.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0)) {
            BatteryManager.BATTERY_PLUGGED_AC -> "ac"
            BatteryManager.BATTERY_PLUGGED_USB -> "usb"
            BatteryManager.BATTERY_PLUGGED_WIRELESS -> "wireless"
            0 -> "none"
            else -> "other"
        }
        out["charging_status"] = when (i.getIntExtra(BatteryManager.EXTRA_STATUS, 0)) {
            BatteryManager.BATTERY_STATUS_CHARGING -> "charging"
            BatteryManager.BATTERY_STATUS_FULL -> "full"
            BatteryManager.BATTERY_STATUS_DISCHARGING -> "discharging"
            BatteryManager.BATTERY_STATUS_NOT_CHARGING -> "not_charging"
            else -> "unknown"
        }
        out["battery_voltage_mv"] = i.getIntExtra(BatteryManager.EXTRA_VOLTAGE, 0)
        val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val cur = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_NOW)
        if (cur != Int.MIN_VALUE && cur != 0) {
            // most phones report microamps; a few report milliamps
            out["current_ma"] = if (kotlin.math.abs(cur) > 20_000) cur / 1000 else cur
        }
    }

    private fun storage(out: HashMap<String, Any?>) {
        val s = StatFs(Environment.getDataDirectory().path)
        val total = s.totalBytes.toDouble()
        val free = s.availableBytes.toDouble()
        out["storage_total_gb"] = total / 1e9
        out["storage_free_gb"] = free / 1e9
        out["storage_used_pct"] = if (total > 0) ((total - free) * 100 / total) else null
    }

    private fun memory(ctx: Context, out: HashMap<String, Any?>) {
        val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val mi = ActivityManager.MemoryInfo()
        am.getMemoryInfo(mi)
        out["ram_total_gb"] = mi.totalMem / 1e9
        out["ram_free_pct"] = if (mi.totalMem > 0) mi.availMem * 100.0 / mi.totalMem else null
        out["ram_low"] = mi.lowMemory
    }

    private fun power(ctx: Context, out: HashMap<String, Any?>) {
        val pm = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
        out["battery_saver"] = pm.isPowerSaveMode
        if (Build.VERSION.SDK_INT >= 29) out["thermal_status"] = pm.currentThermalStatus      // 0 none .. 6 shutdown
        if (Build.VERSION.SDK_INT >= 23) out["hoola_battery_unrestricted"] = pm.isIgnoringBatteryOptimizations(ctx.packageName)
    }

    @SuppressLint("MissingPermission")
    private fun network(ctx: Context, out: HashMap<String, Any?>) {
        out["airplane"] = Settings.Global.getInt(ctx.contentResolver, Settings.Global.AIRPLANE_MODE_ON, 0) == 1
        val tm = ctx.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        out["sim_state"] = when (tm.simState) {
            TelephonyManager.SIM_STATE_READY -> "ready"
            TelephonyManager.SIM_STATE_ABSENT -> "absent"
            TelephonyManager.SIM_STATE_PIN_REQUIRED, TelephonyManager.SIM_STATE_PUK_REQUIRED -> "locked"
            TelephonyManager.SIM_STATE_NETWORK_LOCKED -> "network_locked"
            TelephonyManager.SIM_STATE_NOT_READY -> "not_ready"
            else -> "unknown"
        }
        out["operator"] = tm.networkOperatorName ?: ""
        if (Build.VERSION.SDK_INT >= 28) {
            try { out["signal_level"] = tm.signalStrength?.level } catch (_: SecurityException) { }    // 0 none .. 4 great
        }
        val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        try {
            val caps = cm.getNetworkCapabilities(cm.activeNetwork)
            out["online"] = caps?.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED) == true
            out["on"] = when {
                caps == null -> "none"
                caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
                caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "mobile"
                caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN) -> "vpn"
                else -> "other"
            }
            out["vpn"] = caps?.hasTransport(NetworkCapabilities.TRANSPORT_VPN) == true
            out["data_saver"] = cm.restrictBackgroundStatus == ConnectivityManager.RESTRICT_BACKGROUND_STATUS_ENABLED
        } catch (_: SecurityException) { }
        try {
            val wm = ctx.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            out["wifi_on"] = wm.isWifiEnabled
        } catch (_: Exception) { }
        try {
            val bt = (ctx.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter
            out["bluetooth_on"] = bt?.isEnabled == true
        } catch (_: SecurityException) { }
    }

    private fun sound(ctx: Context, out: HashMap<String, Any?>) {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        out["ringer"] = when (am.ringerMode) {
            AudioManager.RINGER_MODE_SILENT -> "silent"
            AudioManager.RINGER_MODE_VIBRATE -> "vibrate"
            else -> "normal"
        }
        out["ring_volume_pct"] = pct(am.getStreamVolume(AudioManager.STREAM_RING), am.getStreamMaxVolume(AudioManager.STREAM_RING))
        out["media_volume_pct"] = pct(am.getStreamVolume(AudioManager.STREAM_MUSIC), am.getStreamMaxVolume(AudioManager.STREAM_MUSIC))
        out["call_volume_pct"] = pct(am.getStreamVolume(AudioManager.STREAM_VOICE_CALL), am.getStreamMaxVolume(AudioManager.STREAM_VOICE_CALL))
        val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        out["dnd"] = nm.currentInterruptionFilter > NotificationManager.INTERRUPTION_FILTER_ALL
    }

    private fun pct(v: Int, max: Int) = if (max > 0) v * 100 / max else null

    private fun settings(ctx: Context, out: HashMap<String, Any?>) {
        val cr = ctx.contentResolver
        out["auto_time"] = Settings.Global.getInt(cr, Settings.Global.AUTO_TIME, 1) == 1
        out["usb_debugging"] = Settings.Global.getInt(cr, Settings.Global.ADB_ENABLED, 0) == 1
        out["developer_options"] = Settings.Global.getInt(cr, Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) == 1
        try {
            out["brightness_auto"] = Settings.System.getInt(cr, Settings.System.SCREEN_BRIGHTNESS_MODE) ==
                Settings.System.SCREEN_BRIGHTNESS_MODE_AUTOMATIC
            out["brightness_pct"] = Settings.System.getInt(cr, Settings.System.SCREEN_BRIGHTNESS) * 100 / 255
        } catch (_: Exception) { }
        try {
            out["location_on"] = Settings.Secure.getInt(cr, Settings.Secure.LOCATION_MODE) != Settings.Secure.LOCATION_MODE_OFF
        } catch (_: Exception) { }
        out["screen_timeout_s"] = Settings.System.getInt(cr, Settings.System.SCREEN_OFF_TIMEOUT, 0) / 1000
    }

    /** The apps used longest in the last 24 h (only with the Usage Access she already gave for the reel report). */
    private fun topApps(ctx: Context, out: HashMap<String, Any?>) {
        if (!ScrollStats.allowed(ctx)) return
        val um = ctx.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val end = System.currentTimeMillis()
        val stats = um.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, end - 24 * 3_600_000L, end) ?: return
        val pm = ctx.packageManager
        val top = stats.filter { it.totalTimeInForeground > 60_000 && it.packageName != ctx.packageName }
            .groupBy { it.packageName }.mapValues { e -> e.value.sumOf { it.totalTimeInForeground } }
            .entries.sortedByDescending { it.value }.take(5)
            .map { e ->
                val label = try { pm.getApplicationLabel(pm.getApplicationInfo(e.key, 0)).toString() } catch (_: Exception) { e.key }
                mapOf("package" to e.key, "label" to label, "minutes" to (e.value / 60_000))
            }
        out["top_apps"] = top
    }

    /** Opens the Android screen for a fix. Returns false when this phone has no such screen. */
    fun openSetting(ctx: Context, key: String, pkg: String = ""): Boolean {
        val action: String? = when (key) {
            "battery_usage" -> Intent.ACTION_POWER_USAGE_SUMMARY
            "battery_saver" -> Settings.ACTION_BATTERY_SAVER_SETTINGS
            "storage" -> Settings.ACTION_INTERNAL_STORAGE_SETTINGS
            "wifi" -> Settings.ACTION_WIFI_SETTINGS
            "bluetooth" -> Settings.ACTION_BLUETOOTH_SETTINGS
            "mobile_network" -> Settings.ACTION_NETWORK_OPERATOR_SETTINGS
            "wireless" -> Settings.ACTION_WIRELESS_SETTINGS
            "airplane" -> Settings.ACTION_AIRPLANE_MODE_SETTINGS
            "data_usage" -> if (Build.VERSION.SDK_INT >= 28) Settings.ACTION_DATA_USAGE_SETTINGS else Settings.ACTION_WIRELESS_SETTINGS
            "date_time" -> Settings.ACTION_DATE_SETTINGS
            "display" -> Settings.ACTION_DISPLAY_SETTINGS
            "sound" -> Settings.ACTION_SOUND_SETTINGS
            "dnd" -> if (Build.VERSION.SDK_INT >= 23) "android.settings.ZEN_MODE_SETTINGS" else Settings.ACTION_SOUND_SETTINGS
            "apps" -> Settings.ACTION_MANAGE_APPLICATIONS_SETTINGS
            "app_info" -> Settings.ACTION_APPLICATION_DETAILS_SETTINGS
            "app_notifications" -> if (Build.VERSION.SDK_INT >= 26) Settings.ACTION_APP_NOTIFICATION_SETTINGS else Settings.ACTION_APPLICATION_DETAILS_SETTINGS
            "location" -> Settings.ACTION_LOCATION_SOURCE_SETTINGS
            "security" -> Settings.ACTION_SECURITY_SETTINGS
            "accessibility" -> Settings.ACTION_ACCESSIBILITY_SETTINGS
            "developer" -> Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS
            "system_update" -> "android.settings.SYSTEM_UPDATE_SETTINGS"
            "about" -> Settings.ACTION_DEVICE_INFO_SETTINGS
            "settings" -> Settings.ACTION_SETTINGS
            else -> null
        }
        if (action == null) return false
        val i = Intent(action).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        if (key == "app_info") i.data = Uri.parse("package:" + (pkg.ifBlank { ctx.packageName }))
        if (key == "app_notifications" && Build.VERSION.SDK_INT >= 26) i.putExtra(Settings.EXTRA_APP_PACKAGE, pkg.ifBlank { ctx.packageName })
        return try {
            ctx.startActivity(i)
            true
        } catch (_: Exception) {
            try {
                ctx.startActivity(Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                false
            } catch (_: Exception) { false }
        }
    }
}
