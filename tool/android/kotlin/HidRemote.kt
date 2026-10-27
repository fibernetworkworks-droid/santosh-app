package com.newtika.santosh

import android.annotation.SuppressLint
import android.annotation.TargetApi
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothHidDevice
import android.bluetooth.BluetoothHidDeviceAppQosSettings
import android.bluetooth.BluetoothHidDeviceAppSdpSettings
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * "Hoola Remote": the phone is a Bluetooth keyboard + TV remote (Android 9+ BluetoothHidDevice).
 *
 * v0.40 — built to keep working in every situation:
 *  - Already paired = never pair again: an existing bond (or a live connection) is used as is. Connecting tries the
 *    remembered TV, the connected one, then each paired TV-like device, with a reconnect + retry before giving up.
 *  - Answers the TV's GET_REPORT / SET_PROTOCOL questions (some TVs drop a remote that does not answer) and follows
 *    BOOT protocol (Samsung / LG / older TVs): keyboard reports are then sent without a report id, the way those TVs read them.
 *  - Keyboard report with an LED output report, the standard layout TVs expect.
 *  - Every press is checked; a dropped link is re-joined once and the press is sent again.
 *  - Waits a moment after a fresh connection before the first key (TVs ignore keys sent while they set the link up).
 *  - Longer press / gap timings that every TV registers; key repeat and long press are supported.
 */
@TargetApi(28)
@SuppressLint("MissingPermission") // BLUETOOTH_CONNECT is checked by the caller before any call
class HidRemote private constructor(private val context: Context) {
    private val adapter: BluetoothAdapter? =
        (context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter
    private val callbackExec = Executors.newSingleThreadExecutor()
    private val prefs = context.getSharedPreferences("hoola_bt", Context.MODE_PRIVATE)
    @Volatile private var hid: BluetoothHidDevice? = null
    @Volatile private var proxyPending = false
    @Volatile private var registered = false
    @Volatile private var host: BluetoothDevice? = null
    @Volatile private var bootProtocol = false
    @Volatile private var connectedAt = 0L
    @Volatile private var ready = CountDownLatch(1)
    @Volatile private var connectedLatch = CountDownLatch(1)

    private val callback = object : BluetoothHidDevice.Callback() {
        override fun onAppStatusChanged(pluggedDevice: BluetoothDevice?, registered: Boolean) {
            this@HidRemote.registered = registered
            if (pluggedDevice != null) host = pluggedDevice
            if (registered) ready.countDown()
        }

        override fun onConnectionStateChanged(device: BluetoothDevice?, state: Int) {
            if (device == null) return
            if (state == BluetoothProfile.STATE_CONNECTED) {
                host = device
                connectedAt = System.currentTimeMillis()
                bootProtocol = false
                remember(device)
                connectedLatch.countDown()
            } else if (state == BluetoothProfile.STATE_DISCONNECTED && host?.address == device.address) {
                host = null
            }
        }

        override fun onGetReport(device: BluetoothDevice?, type: Byte, id: Byte, bufferSize: Int) {
            val h = hid ?: return
            val d = device ?: return
            try {
                val size = when (id.toInt()) { ID_CONSUMER -> 2; else -> 8 }
                h.replyReport(d, type, id, ByteArray(size))
            } catch (e: Exception) { Log.i(HomeDevices.TAG, "replyReport", e) }
        }

        override fun onSetProtocol(device: BluetoothDevice?, protocol: Byte) {
            bootProtocol = protocol.toInt() == BluetoothHidDevice.PROTOCOL_BOOT_MODE.toInt()
        }

        override fun onSetReport(device: BluetoothDevice?, type: Byte, id: Byte, data: ByteArray?) {
            val d = device ?: return
            try { hid?.reportError(d, BluetoothHidDevice.ERROR_RSP_SUCCESS) } catch (_: Exception) {}
        }
    }

    val isRegistered: Boolean get() = registered
    fun savedAddress(): String? = prefs.getString("tv", null)
    private fun remember(d: BluetoothDevice) { prefs.edit().putString("tv", d.address).putString("tv_name", safeName(d)).apply() }
    fun savedName(): String? = prefs.getString("tv_name", null)
    private fun safeName(d: BluetoothDevice): String = try { d.name ?: d.address } catch (_: SecurityException) { d.address }

    fun connectedHost(): BluetoothDevice? {
        val h = hid ?: return null
        return try {
            h.getConnectedDevices().firstOrNull() ?: host?.takeIf { h.getConnectionState(it) == BluetoothProfile.STATE_CONNECTED }
        } catch (_: Exception) { null }
    }

    /** What the server / the avatar should know before deciding anything. */
    fun state(): JSONObject {
        val c = connectedHost()
        return JSONObject().put("registered", registered).put("connected", c != null)
            .put("tv", c?.let { safeName(it) } ?: savedName() ?: "").put("address", c?.address ?: savedAddress() ?: "")
            .put("boot_protocol", bootProtocol)
    }

    /** Register the HID app. Safe to call repeatedly; retries when a previous registration failed. */
    @Synchronized
    fun start() {
        val a = adapter ?: throw HomeDeviceException("This phone has no Bluetooth.")
        if (!a.isEnabled) throw HomeDeviceException("bluetooth_off")
        if (registered) return
        val h = hid
        if (h != null) { register(h); return }
        if (proxyPending) return
        proxyPending = true
        ready = CountDownLatch(1)
        val ok = a.getProfileProxy(context, object : BluetoothProfile.ServiceListener {
            override fun onServiceConnected(profile: Int, proxy: BluetoothProfile) {
                proxyPending = false
                val p = proxy as BluetoothHidDevice
                hid = p
                register(p)
            }

            override fun onServiceDisconnected(profile: Int) {
                proxyPending = false
                registered = false
                hid = null
            }
        }, BluetoothProfile.HID_DEVICE)
        if (!ok) {
            proxyPending = false
            throw HomeDeviceException("This phone doesn't allow apps to act as a Bluetooth remote.")
        }
    }

    private fun register(h: BluetoothHidDevice) {
        val sdp = BluetoothHidDeviceAppSdpSettings("Hoola Remote", "Hoola TV remote", "Newtika",
            BluetoothHidDevice.SUBCLASS1_COMBO, DESCRIPTOR)
        // low-latency, best-effort link: keys arrive at once and the TV does not drop an idle remote
        val qos = BluetoothHidDeviceAppQosSettings(BluetoothHidDeviceAppQosSettings.SERVICE_BEST_EFFORT,
            800, 9, 0, 11250, BluetoothHidDeviceAppQosSettings.MAX)
        val ok = try { h.registerApp(sdp, null, qos, callbackExec, callback) } catch (e: Exception) {
            Log.w(HomeDevices.TAG, "HID registerApp", e)
            try { h.registerApp(sdp, null, null, callbackExec, callback) } catch (_: Exception) { false }
        }
        if (!ok) {   // another app holds the HID slot, or a stale registration: drop ours and let the next call retry
            try { h.unregisterApp() } catch (_: Exception) {}
            registered = false
        }
    }

    fun stop() {
        try {
            hid?.unregisterApp()
            hid?.let { adapter?.closeProfileProxy(BluetoothProfile.HID_DEVICE, it) }
        } catch (e: Exception) {
            Log.w(HomeDevices.TAG, "HID stop", e)
        }
        hid = null
        registered = false
        proxyPending = false
    }

    private fun awaitRegistered(): BluetoothHidDevice {
        for (attempt in 0 until 3) {
            start()
            if (registered) break
            ready.await(if (attempt == 0) 5L else 3L, TimeUnit.SECONDS)
            if (!registered && attempt == 1) {           // a stuck registration: drop it completely and start over
                stop()
                Thread.sleep(400)
            }
        }
        if (!registered) throw HomeDeviceException("remote_not_ready")
        return hid ?: throw HomeDeviceException("remote_not_ready")
    }

    /** Connect to this TV (it must already be paired — or pairing is started by the caller). True when connected. */
    fun connectTo(device: BluetoothDevice, waitMs: Long = 8000): Boolean {
        val h = awaitRegistered()
        if (h.getConnectionState(device) == BluetoothProfile.STATE_CONNECTED) {
            host = device
            remember(device)
            return true
        }
        connectedHost()?.let { if (it.address != device.address) h.disconnect(it) }   // one TV at a time
        for (attempt in 0 until 2) {
            connectedLatch = CountDownLatch(1)
            if (h.connect(device)) {
                connectedLatch.await(waitMs, TimeUnit.MILLISECONDS)
                if (h.getConnectionState(device) == BluetoothProfile.STATE_CONNECTED) {
                    host = device
                    remember(device)
                    return true
                }
            }
            // half-open link left from before: drop it and try once more
            try { h.disconnect(device) } catch (_: Exception) {}
            Thread.sleep(700)
        }
        return false
    }

    fun disconnect(): Boolean {
        val h = hid ?: return false
        val d = connectedHost() ?: return false
        return h.disconnect(d)
    }

    /** Paired devices worth trying as the TV, best first. */
    fun candidates(preferred: String?): List<BluetoothDevice> {
        val bonded = adapter?.bondedDevices.orEmpty().toList()
        val order = mutableListOf<BluetoothDevice>()
        fun add(d: BluetoothDevice?) { if (d != null && order.none { it.address == d.address }) order.add(d) }
        // the device saved for this TV in Ghar is tried only if it really looks like a TV (not earbuds picked by mistake)
        preferred?.let { p -> add(bonded.firstOrNull { it.address.equals(p, ignoreCase = true) &&
            (BtControl.kindOf(it) == "tv" || it.address.equals(savedAddress(), ignoreCase = true)) }) }
        savedAddress()?.let { s -> add(bonded.firstOrNull { it.address.equals(s, ignoreCase = true) }) }
        bonded.filter { BtControl.kindOf(it) == "tv" }.forEach { add(it) }
        return order
    }

    /** The TV to use: already connected, else the given / remembered / paired TVs in turn. Never starts a new pairing. */
    fun ensureConnected(address: String?): BluetoothDevice {
        awaitRegistered()
        connectedHost()?.let { c -> if (address == null || c.address.equals(address, ignoreCase = true) || savedAddress() == c.address) return c }
        val list = candidates(address)
        if (list.isEmpty()) throw HomeDeviceException("tv_not_paired")
        for (d in list) if (connectTo(d)) return d
        throw HomeDeviceException("tv_not_reachable")
    }

    private fun send(h: BluetoothHidDevice, dev: BluetoothDevice, id: Int, data: ByteArray) {
        if (!h.sendReport(dev, id, data)) throw HomeDeviceException("link_dropped")
    }

    private fun keyboard(h: BluetoothHidDevice, dev: BluetoothDevice, mod: Byte, key: Byte) {
        val r = byteArrayOf(mod, 0, key, 0, 0, 0, 0, 0)
        if (bootProtocol) send(h, dev, 0, r) else send(h, dev, ID_KEYBOARD, r)
    }

    private fun keyboardUp(h: BluetoothHidDevice, dev: BluetoothDevice) {
        if (bootProtocol) send(h, dev, 0, ByteArray(8)) else send(h, dev, ID_KEYBOARD, ByteArray(8))
    }

    private fun runOnce(op: JSONObject, dev: BluetoothDevice) {
        val h = hid ?: throw HomeDeviceException("remote_not_ready")
        // a TV ignores keys while it is still setting up a fresh link
        val since = System.currentTimeMillis() - connectedAt
        if (since in 0..900) Thread.sleep(900 - since)
        val hold = op.optLong("hold_ms", 0).coerceIn(0, 3000)
        when (op.getString("op")) {
            "consumer" -> {
                val usage = op.getInt("usage")
                repeat(op.optInt("repeat", 1).coerceIn(1, 30)) {
                    // BOOT-protocol TVs only read the keyboard; media keys may be ignored there (said in the result)
                    if (!h.sendReport(dev, ID_CONSUMER, byteArrayOf((usage and 0xFF).toByte(), ((usage shr 8) and 0xFF).toByte()))) {
                        throw HomeDeviceException(if (bootProtocol) "boot_protocol" else "link_dropped")
                    }
                    Thread.sleep(if (hold > 0) hold else PRESS_MS)
                    send(h, dev, ID_CONSUMER, byteArrayOf(0, 0))
                    Thread.sleep(GAP_MS)
                }
            }
            "keys" -> {
                val reports = op.getJSONArray("reports")
                for (i in 0 until reports.length()) {
                    val r = reports.getJSONArray(i)
                    keyboard(h, dev, r.getInt(0).toByte(), r.getInt(1).toByte())
                    Thread.sleep(if (hold > 0) hold else PRESS_MS)
                    keyboardUp(h, dev)
                    Thread.sleep(if (op.optBoolean("typing")) TYPE_GAP_MS else GAP_MS)
                }
            }
            else -> throw HomeDeviceException("Unknown TV op ${op.optString("op")}")
        }
    }

    /** One remote command: connect if needed, send, and on a dropped link re-join once and send again. */
    fun run(op: JSONObject, address: String?) {
        var dev = ensureConnected(address)
        try {
            runOnce(op, dev)
        } catch (e: HomeDeviceException) {
            if (e.message != "link_dropped") throw e
            Log.i(HomeDevices.TAG, "link dropped, re-joining the TV")
            try { hid?.disconnect(dev) } catch (_: Exception) {}
            Thread.sleep(500)
            dev = ensureConnected(dev.address)
            runOnce(op, dev)
        }
    }

    companion object {
        private const val ID_KEYBOARD = 1
        private const val ID_CONSUMER = 2
        private const val PRESS_MS = 70L
        private const val GAP_MS = 110L
        private const val TYPE_GAP_MS = 60L

        /** Report map: ID 1 = keyboard (modifier, reserved, 6 keys, LED output); ID 2 = 16-bit consumer control. */
        val DESCRIPTOR: ByteArray = intArrayOf(
            0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x85, ID_KEYBOARD,
            0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02,
            0x95, 0x01, 0x75, 0x08, 0x81, 0x01,
            0x95, 0x05, 0x75, 0x01, 0x05, 0x08, 0x19, 0x01, 0x29, 0x05, 0x91, 0x02,
            0x95, 0x01, 0x75, 0x03, 0x91, 0x01,
            0x95, 0x06, 0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00,
            0xC0,
            0x05, 0x0C, 0x09, 0x01, 0xA1, 0x01, 0x85, ID_CONSUMER,
            0x15, 0x00, 0x26, 0xFF, 0x03, 0x19, 0x00, 0x2A, 0xFF, 0x03, 0x75, 0x10, 0x95, 0x01, 0x81, 0x00,
            0xC0,
        ).map { it.toByte() }.toByteArray()

        @Volatile private var instance: HidRemote? = null
        fun get(context: Context): HidRemote =
            instance ?: synchronized(this) { instance ?: HidRemote(context.applicationContext).also { instance = it } }
    }
}
