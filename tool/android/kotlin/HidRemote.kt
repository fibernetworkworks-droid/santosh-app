package com.newtika.santosh

import android.annotation.SuppressLint
import android.annotation.TargetApi
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothHidDevice
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
 * "Hoola Remote": the phone registers as a Bluetooth keyboard + consumer-control remote (Android 9+
 * BluetoothHidDevice). After the TV is paired once, Hoola can press volume, home, back, arrows, OK and type.
 *
 * v0.35 fixes (it "didn't work"):
 *  - registration is retried when Android refuses it or the profile proxy drops (before: stuck forever after one miss)
 *  - the phone can connect to the TV itself ([connectTo]); before, only the TV could start the pairing, and TVs
 *    list the phone under its own Bluetooth name, not "Santosh Remote", so people never found it
 *  - the TV's address is remembered on the phone, so commands work after the app restarts
 *  - connection waits for the real callback (up to 12 s) instead of 3 s, and every report is checked
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
                remember(device)
                connectedLatch.countDown()
            } else if (state == BluetoothProfile.STATE_DISCONNECTED && host?.address == device.address) {
                host = null
            }
        }
    }

    val isRegistered: Boolean get() = registered
    fun savedAddress(): String? = prefs.getString("tv", null)
    private fun remember(d: BluetoothDevice) { prefs.edit().putString("tv", d.address).apply() }

    fun connectedHost(): BluetoothDevice? {
        val h = hid ?: return null
        return try {
            h.getConnectedDevices().firstOrNull() ?: host?.takeIf { h.getConnectionState(it) == BluetoothProfile.STATE_CONNECTED }
        } catch (_: Exception) { null }
    }

    /** Register the HID app. Safe to call repeatedly; retries when a previous registration failed. */
    @Synchronized
    fun start() {
        val a = adapter ?: throw HomeDeviceException("This phone has no Bluetooth.")
        if (!a.isEnabled) throw HomeDeviceException("bluetooth_off")
        if (registered) return
        val h = hid
        if (h != null) {           // proxy is there but the app isn't registered (refused, or dropped): try again
            register(h)
            return
        }
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
        val sdp = BluetoothHidDeviceAppSdpSettings(
            "Hoola Remote", "Hoola TV remote", "Newtika",
            BluetoothHidDevice.SUBCLASS1_COMBO, DESCRIPTOR,
        )
        val ok = try { h.registerApp(sdp, null, null, callbackExec, callback) } catch (e: Exception) {
            Log.w(HomeDevices.TAG, "HID registerApp", e)
            false
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
        start()
        if (!registered) {
            ready.await(5, TimeUnit.SECONDS)
            if (!registered) {
                start()           // one retry (registerApp is refused right after Bluetooth turns on on some phones)
                ready.await(4, TimeUnit.SECONDS)
            }
        }
        if (!registered) throw HomeDeviceException("The Bluetooth remote couldn't start. Turn Bluetooth off and on, then try again.")
        return hid ?: throw HomeDeviceException("Bluetooth remote not available.")
    }

    /** Connect to this TV now (pairing first if needed is done by the caller). True when connected. */
    fun connectTo(device: BluetoothDevice, waitMs: Long = 12000): Boolean {
        val h = awaitRegistered()
        if (h.getConnectionState(device) == BluetoothProfile.STATE_CONNECTED) {
            host = device
            remember(device)
            return true
        }
        connectedHost()?.let { if (it.address != device.address) h.disconnect(it) }   // one host at a time
        connectedLatch = CountDownLatch(1)
        if (!h.connect(device)) return false
        connectedLatch.await(waitMs, TimeUnit.MILLISECONDS)
        val ok = h.getConnectionState(device) == BluetoothProfile.STATE_CONNECTED
        if (ok) {
            host = device
            remember(device)
        }
        return ok
    }

    fun disconnect(): Boolean {
        val h = hid ?: return false
        val d = connectedHost() ?: return false
        return h.disconnect(d)
    }

    /** The TV to use: the given address, else the connected one, the remembered one, or the only paired TV. */
    private fun ensureConnected(address: String?): BluetoothDevice {
        val h = awaitRegistered()
        connectedHost()?.let { if (address == null || it.address.equals(address, ignoreCase = true)) return it }
        val bonded = adapter?.bondedDevices.orEmpty()
        val want = address ?: savedAddress()
        val target = (if (want != null) bonded.firstOrNull { it.address.equals(want, ignoreCase = true) } else null)
            ?: bonded.filter { BtControl.kindOf(it) == "tv" }.singleOrNull()
            ?: throw HomeDeviceException("Pair the TV with Hoola first: say \"TV ko Bluetooth se jodo\" or open Ghar > TV.")
        if (connectTo(target) || h.getConnectionState(target) == BluetoothProfile.STATE_CONNECTED) return target
        throw HomeDeviceException("The TV didn't accept the Bluetooth remote. Is it on and nearby? (If it was reset, pair it again.)")
    }

    private fun send(h: BluetoothHidDevice, dev: BluetoothDevice, id: Int, data: ByteArray) {
        if (!h.sendReport(dev, id, data)) throw HomeDeviceException("The TV disconnected the Bluetooth remote. Try again.")
    }

    fun run(op: JSONObject, address: String?) {
        val dev = ensureConnected(address)
        val h = hid ?: throw HomeDeviceException("Bluetooth remote not available.")
        when (op.getString("op")) {
            "consumer" -> {
                val usage = op.getInt("usage")
                repeat(op.optInt("repeat", 1).coerceIn(1, 20)) {
                    send(h, dev, ID_CONSUMER, byteArrayOf((usage and 0xFF).toByte(), ((usage shr 8) and 0xFF).toByte()))
                    Thread.sleep(PRESS_MS)
                    send(h, dev, ID_CONSUMER, byteArrayOf(0, 0))
                    Thread.sleep(GAP_MS)
                }
            }
            "keys" -> {
                val reports = op.getJSONArray("reports")
                for (i in 0 until reports.length()) {
                    val r = reports.getJSONArray(i)
                    val mod = r.getInt(0).toByte()
                    val key = r.getInt(1).toByte()
                    send(h, dev, ID_KEYBOARD, byteArrayOf(mod, 0, key, 0, 0, 0, 0, 0))
                    Thread.sleep(PRESS_MS)
                    send(h, dev, ID_KEYBOARD, ByteArray(8))
                    Thread.sleep(GAP_MS)
                }
            }
            else -> throw HomeDeviceException("Unknown TV op ${op.optString("op")}")
        }
    }

    companion object {
        private const val ID_KEYBOARD = 1
        private const val ID_CONSUMER = 2
        private const val PRESS_MS = 40L
        private const val GAP_MS = 70L

        /** Report map: ID 1 = boot-style keyboard (modifier, reserved, 6 keys); ID 2 = 16-bit consumer control. */
        val DESCRIPTOR: ByteArray = intArrayOf(
            0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x85, ID_KEYBOARD,
            0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02,
            0x95, 0x01, 0x75, 0x08, 0x81, 0x01,
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
