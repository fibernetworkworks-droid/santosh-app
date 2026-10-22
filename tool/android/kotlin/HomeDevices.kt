package com.newtika.santosh

import android.Manifest
import android.app.SearchManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.ConsumerIrManager
import android.media.AudioManager
import android.net.wifi.WifiManager
import android.os.Build
import android.provider.MediaStore
import android.util.Log
import android.view.KeyEvent
import org.json.JSONArray
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.SocketTimeoutException
import java.net.URL
import java.util.concurrent.Executors
import kotlin.math.roundToInt

/** A device step that could not run; the message is shown to the user and sent to the server. */
class HomeDeviceException(message: String) : Exception(message)

/**
 * Santosh "Ghar": runs the home-device commands that the server builds (IR pattern, HID usages, DIAL app, media keys).
 *  - channel "phone_media": music on the phone / connected Bluetooth speaker
 *  - channel "bt_hid":     the phone as a Bluetooth keyboard + remote for the TV ("Hoola Remote"), plus DIAL on Wi-Fi
 *  - channel "ir":         the phone's IR blaster for the AC
 * Flutter reports the result to the server; this side only carries the command out.
 */
object HomeDevices {
    const val TAG = "HoolaHome"
    private val worker = Executors.newSingleThreadExecutor()

    /** Runs [actionJson] off the main thread; [done] gets null when it worked, else a short reason. */
    fun run(ctx: Context, actionJson: String, done: (String?) -> Unit) {
        val app = ctx.applicationContext
        worker.execute {
            val err = try {
                execute(app, JSONObject(actionJson))
                null
            } catch (e: HomeDeviceException) {
                e.message ?: "failed"
            } catch (e: SecurityException) {
                "permission"
            } catch (e: Exception) {
                Log.w(TAG, "device action failed", e)
                e.javaClass.simpleName + ": " + (e.message ?: "")
            }
            done(err)
        }
    }

    fun hasIr(ctx: Context): Boolean =
        (ctx.getSystemService(Context.CONSUMER_IR_SERVICE) as? ConsumerIrManager)?.hasIrEmitter() == true

    /** Android 12+ needs the "Nearby devices" permission for the Bluetooth TV remote. */
    fun hasBluetoothPermission(ctx: Context): Boolean =
        Build.VERSION.SDK_INT < 31 ||
            ctx.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED

    fun caps(ctx: Context): Map<String, Any> {
        val bt = (ctx.getSystemService(Context.BLUETOOTH_SERVICE) as? android.bluetooth.BluetoothManager)?.adapter
        return mapOf(
            "ir" to hasIr(ctx),
            "bluetooth" to (bt != null),
            "bluetooth_on" to (try { bt?.isEnabled == true } catch (_: SecurityException) { false }),
            "tv_remote" to (Build.VERSION.SDK_INT >= 28 && bt != null),
            "bt_permission" to hasBluetoothPermission(ctx),
            "bt_scan" to BtControl.canScan(ctx),
            "phone_name" to (if (hasBluetoothPermission(ctx)) (try { bt?.name } catch (_: SecurityException) { null } ?: "") else ""),
            "tv_saved" to (Build.VERSION.SDK_INT >= 28 && HidRemote.get(ctx).savedAddress() != null),
            "remote_on" to RemoteService.running,
        )
    }

    /** Paired Bluetooth devices, TVs first, so the user can pick their TV. */
    @android.annotation.SuppressLint("MissingPermission")
    fun paired(ctx: Context): List<Map<String, Any>> {
        if (!hasBluetoothPermission(ctx)) return emptyList()
        val bt = (ctx.getSystemService(Context.BLUETOOTH_SERVICE) as? android.bluetooth.BluetoothManager)?.adapter ?: return emptyList()
        return bt.bondedDevices.orEmpty().map {
            val av = it.bluetoothClass?.majorDeviceClass == android.bluetooth.BluetoothClass.Device.Major.AUDIO_VIDEO
            mapOf("name" to (it.name ?: it.address), "address" to it.address, "tv_like" to av)
        }.sortedBy { if (it["tv_like"] == true) 0 else 1 }
    }

    private fun execute(ctx: Context, action: JSONObject) {
        val channel = action.getString("channel")
        val target = action.optJSONObject("target") ?: JSONObject()
        val ops = action.getJSONArray("ops")
        when (channel) {
            "phone_media" -> runOps(ops) { MediaChannel(ctx).run(it) }
            "ir" -> runOps(ops) { IrChannel(ctx).run(it) }
            "bt_hid" -> runOps(ops) { runTvOp(ctx, it, target) }
            else -> throw HomeDeviceException("Unknown channel $channel")
        }
    }

    private fun runTvOp(ctx: Context, op: JSONObject, target: JSONObject) {
        when (op.getString("op")) {
            "dial_launch" -> {
                val launched = try {
                    DialClient(ctx).launch(op.getString("app"), target.optString("ip").ifBlank { null }, op.optString("body", ""))
                } catch (e: Exception) {
                    Log.i(TAG, "DIAL failed, using TV search instead", e)
                    false
                }
                if (!launched) runOps(op.optJSONArray("fallback") ?: JSONArray()) { runTvOp(ctx, it, target) }
            }
            "wait" -> Thread.sleep(op.optLong("ms", 500).coerceIn(0, 5000))
            else -> {
                if (!hasBluetoothPermission(ctx)) throw HomeDeviceException("permission")
                if (Build.VERSION.SDK_INT >= 28) {
                    RemoteService.start(ctx)   // keeps the remote registered so the TV stays with the phone
                    HidRemote.get(ctx).run(op, target.optString("bt_address").ifBlank { null })
                }
                else throw HomeDeviceException("TV remote needs Android 9 or newer.")
            }
        }
    }

    private fun runOps(ops: JSONArray, each: (JSONObject) -> Unit) {
        for (i in 0 until ops.length()) {
            val op = ops.getJSONObject(i)
            if (op.optString("op") == "wait") Thread.sleep(op.optLong("ms", 500).coerceIn(0, 5000)) else each(op)
        }
    }
}

/** The phone's IR blaster (Redmi, POCO, OnePlus, iQOO, Realme … models that have one). */
internal class IrChannel(context: Context) {
    private val ir = context.getSystemService(Context.CONSUMER_IR_SERVICE) as? ConsumerIrManager

    fun run(op: JSONObject) {
        if (op.getString("op") != "ir") throw HomeDeviceException("Unknown IR op ${op.optString("op")}")
        val mgr = ir
        if (mgr == null || !mgr.hasIrEmitter()) throw HomeDeviceException("This phone has no IR blaster.")
        val carrier = op.getInt("carrier_hz")
        val ranges = mgr.carrierFrequencies
        if (ranges != null && ranges.isNotEmpty() && ranges.none { carrier in it.minFrequency..it.maxFrequency }) {
            throw HomeDeviceException("This phone's IR blaster can't send at $carrier Hz.")
        }
        val arr = op.getJSONArray("pattern")
        val pattern = IntArray(arr.length()) { arr.getInt(it) }  // microseconds, mark/space alternating
        if (pattern.isEmpty() || pattern.sum() > 2_000_000) throw HomeDeviceException("IR signal is not valid.")
        mgr.transmit(carrier, pattern)
    }
}

/**
 * Music on the phone and whatever Bluetooth speaker / headphones it is connected to.
 * Media keys go to the active media session (Spotify, YouTube Music, JioSaavn, Wynk, …); volume is the music stream.
 */
internal class MediaChannel(private val context: Context) {
    private val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    fun run(op: JSONObject) {
        when (op.getString("op")) {
            "media_key" -> key(op.getString("key"))
            "volume" -> volume(op.getString("direction"), op.optInt("steps", 2), op.optInt("max_percent", 90))
            "volume_set" -> setVolume(op.getInt("percent"), op.optInt("max_percent", 90))
            "play_from_search" -> playFromSearch(op.getString("query"), op.optString("package", ""), op.optString("kind", ""), op.optString("fallback", ""))
            else -> throw HomeDeviceException("Unknown media op ${op.optString("op")}")
        }
    }

    private fun key(name: String) {
        val code = when (name) {
            "PLAY" -> KeyEvent.KEYCODE_MEDIA_PLAY
            "PAUSE" -> KeyEvent.KEYCODE_MEDIA_PAUSE
            "PLAY_PAUSE" -> KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE
            "NEXT" -> KeyEvent.KEYCODE_MEDIA_NEXT
            "PREVIOUS" -> KeyEvent.KEYCODE_MEDIA_PREVIOUS
            "STOP" -> KeyEvent.KEYCODE_MEDIA_STOP
            else -> throw HomeDeviceException("Unknown media key $name")
        }
        audio.dispatchMediaKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, code))
        audio.dispatchMediaKeyEvent(KeyEvent(KeyEvent.ACTION_UP, code))
    }

    private fun capOf(maxPercent: Int): Int {
        val max = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        return (max * maxPercent.coerceIn(0, 90) / 100.0).roundToInt()   // never above 90% (ear safety)
    }

    private fun volume(direction: String, steps: Int, maxPercent: Int) {
        val cap = capOf(maxPercent)
        for (i in 0 until steps.coerceIn(1, 10)) {
            val cur = audio.getStreamVolume(AudioManager.STREAM_MUSIC)
            if (direction == "up" && cur >= cap) break
            audio.adjustStreamVolume(
                AudioManager.STREAM_MUSIC,
                if (direction == "up") AudioManager.ADJUST_RAISE else AudioManager.ADJUST_LOWER,
                AudioManager.FLAG_SHOW_UI,
            )
        }
    }

    private fun setVolume(percent: Int, maxPercent: Int) {
        val max = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        val pct = percent.coerceIn(0, maxPercent.coerceIn(0, 90))
        audio.setStreamVolume(AudioManager.STREAM_MUSIC, (max * pct / 100.0).roundToInt(), AudioManager.FLAG_SHOW_UI)
    }

    /**
     * Android's standard "play from search" intent (what assistants and car screens use).
     * v0.126: [pkg] = the app she named (Spotify, YouTube Music, JioSaavn...), [kind] = song / artist / album / playlist.
     * Named app missing -> "app_missing". It doesn't take the intent -> its own search link ([fallback]) or just opens it.
     */
    private fun playFromSearch(query: String, pkg: String = "", kind: String = "", fallback: String = "") {
        val pm = context.packageManager
        if (pkg.isNotEmpty() && pm.getLaunchIntentForPackage(pkg) == null) throw HomeDeviceException("app_missing")
        val focus = when (kind) {
            "artist" -> "vnd.android.cursor.item/artist"
            "album" -> "vnd.android.cursor.item/album"
            "playlist" -> "vnd.android.cursor.item/playlist"
            "song" -> "vnd.android.cursor.item/audio"
            else -> "vnd.android.cursor.item/*"
        }
        val intent = Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH)
            .putExtra(SearchManager.QUERY, query)
            .putExtra(MediaStore.EXTRA_MEDIA_FOCUS, focus)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        when (kind) {
            "artist" -> intent.putExtra(MediaStore.EXTRA_MEDIA_ARTIST, query)
            "album" -> intent.putExtra(MediaStore.EXTRA_MEDIA_ALBUM, query)
            "playlist" -> intent.putExtra("android.intent.extra.playlist", query)
            "song" -> intent.putExtra(MediaStore.EXTRA_MEDIA_TITLE, query)
        }
        if (pkg.isNotEmpty()) intent.setPackage(pkg)
        if (intent.resolveActivity(pm) != null) {
            context.startActivity(intent)
            return
        }
        if (pkg.isEmpty()) throw HomeDeviceException("No music app on this phone supports 'play from search'.")
        // the app is there but doesn't take "play from search": open its own search page, else just open it
        if (fallback.isNotEmpty()) {
            val view = Intent(Intent.ACTION_VIEW, android.net.Uri.parse(fallback)).setPackage(pkg)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            if (view.resolveActivity(pm) != null) {
                context.startActivity(view)
                return
            }
        }
        val launch = pm.getLaunchIntentForPackage(pkg) ?: throw HomeDeviceException("app_missing")
        context.startActivity(launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}

/**
 * DIAL (Discovery And Launch), the open protocol smart TVs use to let phones start YouTube / Netflix.
 * 1. SSDP M-SEARCH on the home Wi-Fi  2. read Application-URL from the TV's description  3. POST to {Application-URL}/{app}.
 */
internal class DialClient(private val context: Context) {

    /** Returns true when the TV accepted the launch (HTTP 201/200). */
    fun launch(app: String, preferIp: String?, body: String): Boolean {
        val locations = discover()
        if (locations.isEmpty()) return false
        val ordered = if (preferIp != null) locations.sortedBy { if (URL(it).host == preferIp) 0 else 1 } else locations
        for (loc in ordered) {
            val appUrl = applicationUrl(loc) ?: continue
            val c = URL(appUrl.trimEnd('/') + "/" + app).openConnection() as HttpURLConnection
            c.requestMethod = "POST"
            c.connectTimeout = 3000
            c.readTimeout = 5000
            c.doOutput = true
            c.setRequestProperty("Content-Type", "text/plain; charset=\"utf-8\"")
            c.outputStream.use { it.write(body.toByteArray()) }
            val code = c.responseCode
            c.disconnect()
            if (code == 201 || code == 200) return true
        }
        return false
    }

    private fun discover(timeoutMs: Int = 2500): List<String> {
        val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        val lock = wifi.createMulticastLock("santosh-dial").apply { setReferenceCounted(false); acquire() }
        val found = linkedSetOf<String>()
        try {
            DatagramSocket().use { sock ->
                sock.soTimeout = timeoutMs
                val msg = ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\n" +
                    "ST: urn:dial-multiscreen-org:service:dial:1\r\n\r\n").toByteArray()
                sock.send(DatagramPacket(msg, msg.size, InetAddress.getByName("239.255.255.250"), 1900))
                val buf = ByteArray(2048)
                val end = System.currentTimeMillis() + timeoutMs
                while (System.currentTimeMillis() < end) {
                    val p = DatagramPacket(buf, buf.size)
                    try {
                        sock.receive(p)
                    } catch (e: SocketTimeoutException) {
                        break
                    }
                    String(p.data, 0, p.length).lineSequence()
                        .firstOrNull { it.startsWith("LOCATION:", ignoreCase = true) }
                        ?.substringAfter(':')?.trim()?.let { found.add(it) }
                }
            }
        } finally {
            lock.release()
        }
        return found.toList()
    }

    private fun applicationUrl(location: String): String? = try {
        val c = URL(location).openConnection() as HttpURLConnection
        c.connectTimeout = 3000
        c.readTimeout = 3000
        c.inputStream.use { it.readBytes() }
        val url = c.getHeaderField("Application-URL")
        c.disconnect()
        url
    } catch (e: Exception) {
        null
    }
}
