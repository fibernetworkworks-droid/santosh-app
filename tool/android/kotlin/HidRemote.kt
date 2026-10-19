package com.newtika.santosh

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothClass
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothHidDevice
import android.bluetooth.BluetoothHidDeviceAppSdpSettings
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.content.Context
import android.util.Log
import android.annotation.TargetApi
import org.json.JSONObject
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * "Santosh Remote": the phone registers as a Bluetooth keyboard + consumer-control remote (Android 9+
 * BluetoothHidDevice). The TV pairs with it once from its Bluetooth settings; after that Santosh can press volume,
 * home, back, arrows, OK and type into search boxes.
 *
 * [RemoteService] keeps the registration alive while the user wants TV control; Android drops it when the process dies.
 */
@TargetApi(28)
@SuppressLint("MissingPermission") // BLUETOOTH_CONNECT is checked by the caller before any call
class HidRemote private constructor(private val context: Context) {
    private val adapter: BluetoothAdapter? =
        (context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter
    private val callbackExec = Executors.newSingleThreadExecutor()
    @Volatile private var hid: BluetoothHidDevice? = null
    @Volatile private var registered = false
    @Volatile private var host: BluetoothDevice? = null
    @Volatile private var ready = CountDownLatch(1)

    private val callback = object : BluetoothHidDevice.Callback() {
        override fun onAppStatusChanged(pluggedDevice: BluetoothDevice?, registered: Boolean) {
            this@HidRemote.registered = registered
            if (pluggedDevice != null) host = pluggedDevice
            if (registered) ready.countDown()
        }

        override fun onConnectionStateChanged(device: BluetoothDevice?, state: Int) {
            if (device == null) return
            if (state == BluetoothProfile.STATE_CONNECTED) host = device
            else if (state == BluetoothProfile.STATE_DISCONNECTED && host == device) host = null
        }
    }

    /** Register the HID app. Safe to call repeatedly. */
    fun start() {
        val a = adapter ?: throw HomeDeviceException("This phone has no Bluetooth.")
        if (!a.isEnabled) throw HomeDeviceException("Turn on Bluetooth to control the TV.")
        if (registered || hid != null) return
        ready = CountDownLatch(1)
        a.getProfileProxy(context, object : BluetoothProfile.ServiceListener {
            override fun onServiceConnected(profile: Int, proxy: BluetoothProfile) {
                val h = proxy as BluetoothHidDevice
                hid = h
                val sdp = BluetoothHidDeviceAppSdpSettings(
                    "Santosh Remote", "Santosh TV remote", "Newtika",
                    BluetoothHidDevice.SUBCLASS1_COMBO, DESCRIPTOR,
                )
                h.registerApp(sdp, null, null, callbackExec, callback)
            }

            override fun onServiceDisconnected(profile: Int) {
                registered = false
                hid = null
            }
        }, BluetoothProfile.HID_DEVICE)
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
    }

    /** Connect to the TV (already paired). Uses the saved address, else the last host, else the only paired TV. */
    private fun ensureConnected(address: String?): BluetoothDevice {
        start()
        if (!registered && !ready.await(4, TimeUnit.SECONDS)) throw HomeDeviceException("Bluetooth remote is still starting. Try again.")
        val h = hid ?: throw HomeDeviceException("Bluetooth remote not available.")
        host?.let { if (h.getConnectionState(it) == BluetoothProfile.STATE_CONNECTED) return it }
        val bonded = adapter?.bondedDevices.orEmpty()
        val target = when {
            address != null -> bonded.firstOrNull { it.address.equals(address, ignoreCase = true) }
            host != null -> host
            else -> bonded.singleOrNull { it.bluetoothClass?.majorDeviceClass == BluetoothClass.Device.Major.AUDIO_VIDEO }
        } ?: throw HomeDeviceException("Pair the TV with 'Santosh Remote' first (TV › Settings › Bluetooth / Remotes & accessories).")
        h.connect(target)
        repeat(30) {
            if (h.getConnectionState(target) == BluetoothProfile.STATE_CONNECTED) {
                host = target
                return target
            }
            Thread.sleep(100)
        }
        throw HomeDeviceException("The TV didn't accept the Bluetooth remote. Is it on and nearby?")
    }

    fun run(op: JSONObject, address: String?) {
        val dev = ensureConnected(address)
        val h = hid ?: throw HomeDeviceException("Bluetooth remote not available.")
        when (op.getString("op")) {
            "consumer" -> {
                val usage = op.getInt("usage")
                repeat(op.optInt("repeat", 1).coerceIn(1, 20)) {
                    h.sendReport(dev, ID_CONSUMER, byteArrayOf((usage and 0xFF).toByte(), ((usage shr 8) and 0xFF).toByte()))
                    Thread.sleep(PRESS_MS)
                    h.sendReport(dev, ID_CONSUMER, byteArrayOf(0, 0))
                    Thread.sleep(GAP_MS)
                }
            }
            "keys" -> {
                val reports = op.getJSONArray("reports")
                for (i in 0 until reports.length()) {
                    val r = reports.getJSONArray(i)
                    val mod = r.getInt(0).toByte()
                    val key = r.getInt(1).toByte()
                    h.sendReport(dev, ID_KEYBOARD, byteArrayOf(mod, 0, key, 0, 0, 0, 0, 0))
                    Thread.sleep(PRESS_MS)
                    h.sendReport(dev, ID_KEYBOARD, ByteArray(8))
                    Thread.sleep(GAP_MS)
                }
            }
            else -> throw HomeDeviceException("Unknown TV op ${op.optString("op")}")
        }
    }

    companion object {
        private const val ID_KEYBOARD = 1
        private const val ID_CONSUMER = 2
        private const val PRESS_MS = 35L
        private const val GAP_MS = 60L

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
