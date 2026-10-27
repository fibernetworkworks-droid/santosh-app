package com.newtika.santosh

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothA2dp
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothClass
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** A Bluetooth job that could not run. [code] is sent to the server: permission, bluetooth_off, needs_screen, not_found… */
class BtException(val code: String) : Exception(code)

/**
 * Hoola Bluetooth: status, paired/connected devices, nearby scan (classic + BLE), pairing, connect/disconnect and
 * making the phone the TV's remote. The server sends a job ({action, args}); the answer goes back as JSON.
 *
 * Android rules this follows: apps can't switch Bluetooth on/off silently (we show the system prompt / settings),
 * can't connect a speaker's audio profile on Android 13+ (we try, then open Bluetooth settings), and pairing always
 * shows Android's own dialog. Device names from the air are untrusted: the server cleans them.
 */
@SuppressLint("MissingPermission") // every entry checks BLUETOOTH_CONNECT / SCAN first
object BtControl {
    private const val TAG = "HoolaBt"
    private val worker = Executors.newSingleThreadExecutor()
    /** name/address of devices seen in the last scan, so "pair boAt" works right after a scan */
    private val seen = ConcurrentHashMap<String, BluetoothDevice>()

    fun run(ctx: Context, action: String, args: JSONObject, done: (Boolean, JSONObject, String) -> Unit) {
        val app = ctx.applicationContext
        worker.execute {
            try {
                done(true, execute(app, action, args), "")
            } catch (e: BtException) {
                done(false, JSONObject(), e.code)
            } catch (e: HomeDeviceException) {
                done(false, JSONObject(), e.message ?: "failed")
            } catch (e: SecurityException) {
                done(false, JSONObject(), "permission")
            } catch (e: Exception) {
                Log.w(TAG, "bt job failed", e)
                done(false, JSONObject(), e.javaClass.simpleName + ": " + (e.message ?: ""))
            }
        }
    }

    private fun adapter(ctx: Context): BluetoothAdapter? =
        (ctx.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter

    fun canConnect(ctx: Context) = Build.VERSION.SDK_INT < 31 ||
        ctx.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED

    fun canScan(ctx: Context): Boolean = if (Build.VERSION.SDK_INT >= 31) {
        ctx.checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED
    } else {
        ctx.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
    }

    private fun execute(ctx: Context, action: String, args: JSONObject): JSONObject {
        // Hoola TV on a Chromecast / Android TV goes over Wi-Fi, not Bluetooth
        if (action.startsWith("cast_")) {
            try {
                return CastClient.run(ctx, action, args)
            } catch (e: CastClient.CastException) {
                throw BtException(e.code)
            }
        }
        val a = adapter(ctx) ?: throw BtException("This phone has no Bluetooth.")
        if (action == "status") return status(ctx, a)
        if (action == "settings" || action == "turn_off") return openSettings(ctx)
        if (!canConnect(ctx)) throw BtException("permission")
        if (action == "turn_on") return turnOn(ctx, a)
        if (!a.isEnabled) throw BtException("bluetooth_off")
        return when (action) {
            "devices" -> JSONObject().put("on", true).put("devices", devices(ctx, a))
            "scan" -> scan(ctx, a, args.optString("kind"))
            "pair" -> pair(a, resolve(ctx, a, args))
            "connect" -> connect(ctx, a, resolve(ctx, a, args))
            "disconnect" -> disconnect(ctx, resolve(ctx, a, args))
            "tv_pair" -> tvPair(ctx, a, args)
            else -> throw BtException("Unknown Bluetooth action $action")
        }
    }

    // ------------------------------------------------------------------ status / devices
    private fun status(ctx: Context, a: BluetoothAdapter): JSONObject {
        val out = JSONObject().put("supported", true).put("permission", canConnect(ctx)).put("scan_permission", canScan(ctx))
            .put("tv_remote", Build.VERSION.SDK_INT >= 28).put("remote_on", RemoteService.running)
        if (Build.VERSION.SDK_INT >= 28 && canConnect(ctx)) {
            val r = HidRemote.get(ctx).state()
            out.put("tv_connected", r.optBoolean("connected")).put("tv_name", r.optString("tv"))
        }
        out.put("on", try { a.isEnabled } catch (_: SecurityException) { false })
        if (canConnect(ctx)) {
            try { out.put("phone_name", a.name ?: "") } catch (_: SecurityException) {}
            if (a.isEnabled) {
                val connected = devices(ctx, a)
                val list = JSONArray()
                for (i in 0 until connected.length()) if (connected.getJSONObject(i).optBoolean("connected")) list.put(connected.getJSONObject(i))
                out.put("devices", list)
            }
        }
        return out
    }

    fun kindOf(d: BluetoothDevice): String {
        val name = (try { d.name } catch (_: SecurityException) { null } ?: "").lowercase()
        if (Regex("\\b(tv|bravia|androidtv|android tv|fire ?tv|firestick|roku|chromecast|webos|tizen|smart ?tv)\\b").containsMatchIn(name)) return "tv"
        val cls: BluetoothClass? = try { d.bluetoothClass } catch (_: SecurityException) { null }
        val c = cls ?: return if (name.contains("bud") || name.contains("airdopes")) "headphones" else "other"
        return when (c.majorDeviceClass) {
            BluetoothClass.Device.Major.AUDIO_VIDEO -> when (c.deviceClass) {
                BluetoothClass.Device.AUDIO_VIDEO_HEADPHONES, BluetoothClass.Device.AUDIO_VIDEO_WEARABLE_HEADSET,
                BluetoothClass.Device.AUDIO_VIDEO_HANDSFREE -> "headphones"
                BluetoothClass.Device.AUDIO_VIDEO_CAR_AUDIO -> "car"
                BluetoothClass.Device.AUDIO_VIDEO_VIDEO_DISPLAY_AND_LOUDSPEAKER, BluetoothClass.Device.AUDIO_VIDEO_VIDEO_MONITOR,
                BluetoothClass.Device.AUDIO_VIDEO_SET_TOP_BOX -> "tv"
                else -> "speaker"
            }
            BluetoothClass.Device.Major.COMPUTER -> "computer"
            BluetoothClass.Device.Major.PHONE -> "phone"
            BluetoothClass.Device.Major.WEARABLE -> "watch"
            BluetoothClass.Device.Major.HEALTH -> "health"
            BluetoothClass.Device.Major.PERIPHERAL -> when {
                name.contains("mouse") -> "mouse"
                name.contains("pad") || name.contains("controller") -> "gamepad"
                else -> "keyboard"
            }
            else -> if (name.contains("bulb") || name.contains("light") || name.contains("lamp")) "light" else "other"
        }
    }

    private fun connectedAddresses(ctx: Context, a: BluetoothAdapter): Set<String> {
        val out = HashSet<String>()
        for (profile in intArrayOf(BluetoothProfile.A2DP, BluetoothProfile.HEADSET)) {
            proxy(ctx, a, profile)?.let { p ->
                try { p.connectedDevices.forEach { out.add(it.address) } } catch (_: Exception) {}
                a.closeProfileProxy(profile, p)
            }
        }
        if (Build.VERSION.SDK_INT >= 28) HidRemote.get(ctx).connectedHost()?.let { out.add(it.address) }
        return out
    }

    private fun proxy(ctx: Context, a: BluetoothAdapter, profile: Int): BluetoothProfile? {
        var got: BluetoothProfile? = null
        val latch = CountDownLatch(1)
        val ok = try {
            a.getProfileProxy(ctx, object : BluetoothProfile.ServiceListener {
                override fun onServiceConnected(p: Int, proxy: BluetoothProfile) { got = proxy; latch.countDown() }
                override fun onServiceDisconnected(p: Int) {}
            }, profile)
        } catch (_: Exception) { false }
        if (ok) latch.await(1500, TimeUnit.MILLISECONDS)
        return got
    }

    private fun describe(d: BluetoothDevice, connected: Set<String>, hidHost: String?): JSONObject {
        val o = JSONObject().put("name", (try { d.name } catch (_: SecurityException) { null }) ?: d.address)
            .put("address", d.address).put("kind", kindOf(d))
            .put("paired", d.bondState == BluetoothDevice.BOND_BONDED)
            .put("connected", connected.contains(d.address))
        if (hidHost != null && hidHost.equals(d.address, ignoreCase = true)) o.put("remote_host", true)
        return o
    }

    private fun devices(ctx: Context, a: BluetoothAdapter): JSONArray {
        val connected = connectedAddresses(ctx, a)
        val hidHost = if (Build.VERSION.SDK_INT >= 28) HidRemote.get(ctx).savedAddress() else null
        val list = a.bondedDevices.orEmpty().map { describe(it, connected, hidHost) }
            .sortedWith(compareByDescending<JSONObject> { it.optBoolean("connected") }.thenBy { it.optString("name") })
        return JSONArray().also { arr -> list.take(30).forEach { arr.put(it) } }
    }

    // ------------------------------------------------------------------ scan
    private fun scan(ctx: Context, a: BluetoothAdapter, kind: String): JSONObject {
        if (!canScan(ctx)) throw BtException("permission")
        val found = ConcurrentHashMap<String, Pair<BluetoothDevice, Int>>()
        val bleNames = ConcurrentHashMap<String, String>()
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(c: Context, i: Intent) {
                if (i.action != BluetoothDevice.ACTION_FOUND) return
                val d = deviceExtra(i) ?: return
                val rssi = i.getShortExtra(BluetoothDevice.EXTRA_RSSI, Short.MIN_VALUE).toInt()
                found[d.address] = d to rssi
            }
        }
        val filter = IntentFilter(BluetoothDevice.ACTION_FOUND)
        if (Build.VERSION.SDK_INT >= 33) ctx.registerReceiver(receiver, filter, Context.RECEIVER_EXPORTED) else ctx.registerReceiver(receiver, filter)
        val le = a.bluetoothLeScanner
        val leCb = object : ScanCallback() {
            override fun onScanResult(type: Int, r: ScanResult) {
                val name = r.scanRecord?.deviceName ?: (try { r.device.name } catch (_: SecurityException) { null })
                if (name.isNullOrBlank()) return            // unnamed BLE beacons are noise
                bleNames[r.device.address] = name
                if (!found.containsKey(r.device.address)) found[r.device.address] = r.device to r.rssi
            }
        }
        try {
            if (a.isDiscovering) a.cancelDiscovery()
            a.startDiscovery()
            try { le?.startScan(leCb) } catch (e: Exception) { Log.i(TAG, "BLE scan not started", e) }
            Thread.sleep(11000)
        } finally {
            try { a.cancelDiscovery() } catch (_: Exception) {}
            try { le?.stopScan(leCb) } catch (_: Exception) {}
            try { ctx.unregisterReceiver(receiver) } catch (_: Exception) {}
        }
        val connected = connectedAddresses(ctx, a)
        val out = JSONArray()
        found.values.sortedByDescending { it.second }.forEach { (d, rssi) ->
            val o = describe(d, connected, null).put("rssi", rssi)
            if (o.optString("name") == d.address) bleNames[d.address]?.let { o.put("name", it) }
            if (bleNames.containsKey(d.address)) o.put("ble", true)
            if (o.optString("name") == d.address && !o.optBoolean("paired")) return@forEach   // nameless: user can't pick it
            if (kind.isNotBlank() && o.optString("kind") != kind && !(kind == "speaker" && o.optString("kind") == "headphones")) return@forEach
            seen[d.address] = d
            seen[o.optString("name").lowercase()] = d
            if (out.length() < 30) out.put(o)
        }
        return JSONObject().put("on", true).put("devices", out)
    }

    private fun deviceExtra(i: Intent): BluetoothDevice? =
        if (Build.VERSION.SDK_INT >= 33) i.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE, BluetoothDevice::class.java)
        else legacyDeviceExtra(i)

    @Suppress("DEPRECATION")
    private fun legacyDeviceExtra(i: Intent): BluetoothDevice? = i.getParcelableExtra<BluetoothDevice>(BluetoothDevice.EXTRA_DEVICE)

    /** Device from {address} or {device: name}: last scan first, then paired devices. */
    private fun resolve(ctx: Context, a: BluetoothAdapter, args: JSONObject): BluetoothDevice {
        val addr = args.optString("address").uppercase()
        if (addr.isNotBlank() && BluetoothAdapter.checkBluetoothAddress(addr)) return a.getRemoteDevice(addr)
        val want = args.optString("device").trim().lowercase()
        if (want.isBlank()) throw BtException("not_found")
        seen[want]?.let { return it }
        val pool = (seen.values + a.bondedDevices.orEmpty()).distinctBy { it.address }
        val named = pool.map { it to ((try { it.name } catch (_: SecurityException) { null }) ?: "").lowercase() }
        named.firstOrNull { it.second == want }?.let { return it.first }
        val hits = named.filter { it.second.isNotBlank() && (it.second.contains(want) || want.contains(it.second)) }
        if (hits.size == 1) return hits[0].first
        if (want == "tv" || want.contains("tv")) pool.filter { kindOf(it) == "tv" }.singleOrNull()?.let { return it }
        throw BtException("not_found")
    }

    // ------------------------------------------------------------------ pair / connect
    private fun waitBond(d: BluetoothDevice, ms: Long): Boolean {
        val end = System.currentTimeMillis() + ms
        while (System.currentTimeMillis() < end) {
            when (d.bondState) {
                BluetoothDevice.BOND_BONDED -> return true
                BluetoothDevice.BOND_NONE -> if (System.currentTimeMillis() > end - ms + 3000) return false   // refused / cancelled
            }
            Thread.sleep(300)
        }
        return d.bondState == BluetoothDevice.BOND_BONDED
    }

    private fun pair(a: BluetoothAdapter, d: BluetoothDevice): JSONObject {
        val out = JSONObject()
        if (d.bondState == BluetoothDevice.BOND_BONDED) return out.put("paired", true).put("device", describe(d, emptySet(), null))
        if (a.isDiscovering) a.cancelDiscovery()
        if (d.bondState != BluetoothDevice.BOND_BONDING && !d.createBond()) throw BtException("The device refused to pair. Put it in pairing mode and try again.")
        val ok = waitBond(d, 40000)   // Android shows its own pairing dialog / notification; the user taps Pair
        return out.put("paired", ok).put("device", describe(d, emptySet(), null))
            .put("message", if (ok) "Paired" else "Pairing not finished: tap Pair on Android's dialog, or put the device in pairing mode.")
    }

    private fun connect(ctx: Context, a: BluetoothAdapter, d: BluetoothDevice): JSONObject {
        if (d.bondState != BluetoothDevice.BOND_BONDED) {
            val p = pair(a, d)
            if (!p.optBoolean("paired")) return p
            Thread.sleep(2500)        // speakers and earbuds connect themselves right after pairing
        }
        if (kindOf(d) == "tv" && Build.VERSION.SDK_INT >= 28) {
            val ok = HidRemote.get(ctx).connectTo(d)
            return JSONObject().put("connected", ok).put("device", describe(d, if (ok) setOf(d.address) else emptySet(), d.address))
        }
        if (connectedAddresses(ctx, a).contains(d.address)) return JSONObject().put("connected", true).put("device", describe(d, setOf(d.address), null))
        // Android 13+ keeps audio connect for system apps; older phones still allow it
        val tried = proxy(ctx, a, BluetoothProfile.A2DP)?.let { p ->
            val r = try { BluetoothA2dp::class.java.getMethod("connect", BluetoothDevice::class.java).invoke(p, d) as? Boolean ?: false } catch (_: Throwable) { false }
            a.closeProfileProxy(BluetoothProfile.A2DP, p)
            r
        } ?: false
        if (tried) {
            Thread.sleep(3000)
            if (connectedAddresses(ctx, a).contains(d.address)) return JSONObject().put("connected", true).put("device", describe(d, setOf(d.address), null))
        }
        return openSettings(ctx).put("connected", false).put("device", describe(d, emptySet(), null))
    }

    private fun disconnect(ctx: Context, d: BluetoothDevice): JSONObject {
        if (Build.VERSION.SDK_INT >= 28) {
            val hid = HidRemote.get(ctx)
            if (hid.connectedHost()?.address == d.address) return JSONObject().put("connected", !hid.disconnect()).put("message", "TV remote disconnected")
        }
        return openSettings(ctx).put("message", "Tap the device in Bluetooth settings to disconnect it.")
    }

    // ------------------------------------------------------------------ TV remote pairing
    private fun tvPair(ctx: Context, a: BluetoothAdapter, args: JSONObject): JSONObject {
        if (Build.VERSION.SDK_INT < 28) throw BtException("The TV remote needs Android 9 or newer.")
        val started = RemoteService.start(ctx)
        if (started != "ok") throw BtException(started)
        val hid = HidRemote.get(ctx)
        val phoneName = try { a.name ?: "" } catch (_: SecurityException) { "" }
        fun ok(d: BluetoothDevice, how: String) = JSONObject().put("connected", true).put("paired", true).put("phone_name", phoneName)
            .put("already", how == "already").put("message", if (how == "already") "The TV is already connected to Hoola Remote." else "Connected to the TV.")
            .put("device", describe(d, setOf(d.address), d.address))
        // 1) already connected: nothing to do (never pair again)
        val asked = args.optString("device").isNotBlank() || args.optString("address").isNotBlank()
        val wanted = if (asked) try { resolve(ctx, a, args) } catch (_: BtException) { null } else null
        hid.connectedHost()?.let { c -> if (wanted == null || wanted.address == c.address) return ok(c, "already") }
        // 2) paired already (the asked TV, the remembered one, any paired TV): connect, no new pairing
        val tries = hid.candidates(wanted?.takeIf { it.bondState == BluetoothDevice.BOND_BONDED }?.address)
        for (d in tries) if (hid.connectTo(d, 12000)) return ok(d, "connected")
        // 3) a TV that is not paired yet and was picked by name: pair it, then connect
        if (wanted != null && wanted.bondState != BluetoothDevice.BOND_BONDED) {
            if (a.isDiscovering) a.cancelDiscovery()
            wanted.createBond()
            if (waitBond(wanted, 40000) && hid.connectTo(wanted, 15000)) return ok(wanted, "paired")
        }
        // 4) paired but it refuses the phone as a remote, or nothing paired: the TV adds the phone itself
        if (MainActivity.visible) {
            try {
                ctx.startActivity(Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE)
                    .putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, 120).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            } catch (_: Exception) {}
        }
        val pairedButRefused = tries.isNotEmpty()
        return JSONObject().put("connected", false).put("phone_name", phoneName).put("asked", MainActivity.visible)
            .put("paired", pairedButRefused)
            .put("message", if (pairedButRefused)
                "The TV is paired but did not take the phone as a remote. Make sure the TV is on. If it still fails: on the TV forget \"$phoneName\" in Bluetooth, then add it again from Settings > Remotes & accessories."
            else "On the TV open Settings > Bluetooth / Remotes & accessories > Add, and pick \"$phoneName\".")
    }

    // ------------------------------------------------------------------ on / settings
    private fun turnOn(ctx: Context, a: BluetoothAdapter): JSONObject {
        if (a.isEnabled) return JSONObject().put("on", true).put("message", "Bluetooth is already on")
        if (!MainActivity.visible) throw BtException("needs_screen")
        ctx.startActivity(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        return JSONObject().put("on", false).put("asked", true)
    }

    private fun openSettings(ctx: Context): JSONObject {
        if (!MainActivity.visible) throw BtException("needs_screen")
        ctx.startActivity(Intent(Settings.ACTION_BLUETOOTH_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        return JSONObject().put("opened_settings", true)
    }

    /** For the Ghar screen: the same JSON shape, run from Flutter directly. */
    fun toMap(o: JSONObject): Map<String, Any?> = o.keys().asSequence().associateWith { k ->
        when (val v = o.get(k)) {
            is JSONObject -> toMap(v)
            is JSONArray -> (0 until v.length()).map { i -> v.get(i).let { if (it is JSONObject) toMap(it) else it } }
            JSONObject.NULL -> null
            else -> v
        }
    }
}
