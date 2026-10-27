package com.newtika.santosh

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.net.InetSocketAddress
import java.security.SecureRandom
import java.security.cert.X509Certificate
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocket
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

/**
 * Hoola TV on the big screen: plays a free channel on a Chromecast, Android TV or Google TV on the same Wi-Fi, using
 * the Cast v2 protocol and the TV's built-in Default Media Receiver (no extra app on the TV).
 *
 * Finding TVs: Wi-Fi service discovery (_googlecast._tcp). Talking to a TV: TLS on its port 8009 (Cast devices use
 * their own certificates, so any certificate is accepted; only on the local network address the TV announced).
 * Messages: a tiny protobuf "CastMessage" with JSON inside.
 */
object CastClient {
    private const val TAG = "HoolaCast"
    private const val RECEIVER = "CC1AD845"            // Google's Default Media Receiver
    private const val NS_CONN = "urn:x-cast:com.google.cast.tp.connection"
    private const val NS_HEART = "urn:x-cast:com.google.cast.tp.heartbeat"
    private const val NS_RECV = "urn:x-cast:com.google.cast.receiver"
    private const val NS_MEDIA = "urn:x-cast:com.google.cast.media"

    class CastException(val code: String) : Exception(code)

    data class Tv(val name: String, val model: String, val host: String, val port: Int)

    @Volatile private var known: List<Tv> = emptyList()
    @Volatile private var knownAt = 0L

    fun run(ctx: Context, action: String, args: JSONObject): JSONObject = when (action) {
        "cast_tvs" -> JSONObject().put("tvs", JSONArray(discover(ctx, true).map { JSONObject().put("name", it.name).put("model", it.model) }))
        "cast_play" -> play(ctx, args)
        "cast_stop" -> stop(ctx, args)
        else -> throw CastException("unknown")
    }

    // ------------------------------------------------------------------ finding TVs
    fun discover(ctx: Context, fresh: Boolean = false): List<Tv> {
        if (!fresh && known.isNotEmpty() && System.currentTimeMillis() - knownAt < 120_000) return known
        val wifi = ctx.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        if (!wifi.isWifiEnabled) throw CastException("no_wifi")
        val lock = wifi.createMulticastLock("hoola-cast").apply { setReferenceCounted(false); acquire() }
        val nsd = ctx.getSystemService(Context.NSD_SERVICE) as NsdManager
        val found = mutableListOf<NsdServiceInfo>()
        val listener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType: String) {}
            override fun onDiscoveryStopped(serviceType: String) {}
            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {}
            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {}
            override fun onServiceLost(serviceInfo: NsdServiceInfo) {}
            override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                synchronized(found) { if (found.none { it.serviceName == serviceInfo.serviceName }) found.add(serviceInfo) }
            }
        }
        val tvs = mutableListOf<Tv>()
        try {
            nsd.discoverServices("_googlecast._tcp", NsdManager.PROTOCOL_DNS_SD, listener)
            Thread.sleep(3500)
            try { nsd.stopServiceDiscovery(listener) } catch (_: Exception) {}
            val list = synchronized(found) { found.toList() }
            for (s in list.take(12)) {
                val r = resolve(nsd, s) ?: continue
                @Suppress("DEPRECATION") val host = r.host?.hostAddress ?: continue
                val attrs = r.attributes
                val fn = attrs["fn"]?.let { String(it) } ?: r.serviceName
                val md = attrs["md"]?.let { String(it) } ?: ""
                if (tvs.none { it.host == host }) tvs.add(Tv(fn.take(60), md.take(60), host, r.port))
            }
        } finally {
            try { lock.release() } catch (_: Exception) {}
        }
        known = tvs
        knownAt = System.currentTimeMillis()
        return tvs
    }

    @Suppress("DEPRECATION")
    private fun resolve(nsd: NsdManager, s: NsdServiceInfo): NsdServiceInfo? {
        val latch = CountDownLatch(1)
        var out: NsdServiceInfo? = null
        try {
            nsd.resolveService(s, object : NsdManager.ResolveListener {
                override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) { latch.countDown() }
                override fun onServiceResolved(serviceInfo: NsdServiceInfo) { out = serviceInfo; latch.countDown() }
            })
            latch.await(3, TimeUnit.SECONDS)
        } catch (e: Exception) {
            Log.w(TAG, "resolve failed", e)
        }
        return out
    }

    private fun pick(ctx: Context, want: String): Tv {
        var tvs = discover(ctx)
        if (tvs.isEmpty()) tvs = discover(ctx, true)
        if (tvs.isEmpty()) throw CastException("no_cast_tv")
        if (want.isBlank()) return tvs.first()
        val w = want.lowercase()
        return tvs.firstOrNull { it.name.lowercase() == w } ?: tvs.firstOrNull { it.name.lowercase().contains(w) } ?: tvs.first()
    }

    // ------------------------------------------------------------------ playing
    private fun play(ctx: Context, args: JSONObject): JSONObject {
        val url = args.optString("url")
        if (!url.startsWith("https://")) throw CastException("cast_refused")
        val tv = pick(ctx, args.optString("tv"))
        Session(tv).use { s ->
            s.send("sender-0", "receiver-0", NS_CONN, JSONObject().put("type", "CONNECT"))
            s.send("sender-0", "receiver-0", NS_RECV, JSONObject().put("type", "LAUNCH").put("appId", RECEIVER).put("requestId", 1))
            val app = s.waitFor(20_000) { ns, m ->
                if (ns != NS_RECV || m.optString("type") != "RECEIVER_STATUS") null
                else m.optJSONObject("status")?.optJSONArray("applications")?.let { apps ->
                    (0 until apps.length()).map { apps.getJSONObject(it) }.firstOrNull { it.optString("appId") == RECEIVER }
                }
            } ?: throw CastException("cast_timeout")
            val transport = app.optString("transportId")
            s.send("sender-0", transport, NS_CONN, JSONObject().put("type", "CONNECT"))
            val meta = JSONObject().put("metadataType", 0).put("title", args.optString("title", "Hoola TV"))
                .put("subtitle", "Hoola TV")
            if (args.optString("logo").startsWith("https://")) meta.put("images", JSONArray().put(JSONObject().put("url", args.optString("logo"))))
            val media = JSONObject().put("contentId", url).put("contentUrl", url).put("contentType", "application/x-mpegURL")
                .put("streamType", "LIVE").put("metadata", meta)
            s.send("sender-0", transport, NS_MEDIA, JSONObject().put("type", "LOAD").put("requestId", 2)
                .put("sessionId", app.optString("sessionId")).put("media", media).put("autoplay", true))
            val st = s.waitFor(20_000) { ns, m ->
                if (ns != NS_MEDIA) null
                else when (m.optString("type")) {
                    "LOAD_FAILED", "LOAD_CANCELLED", "INVALID_REQUEST", "ERROR" -> JSONObject().put("failed", true)
                    "MEDIA_STATUS" -> m.optJSONArray("status")?.optJSONObject(0)?.let { ms ->
                        val ps = ms.optString("playerState")
                        if (ps == "PLAYING" || ps == "BUFFERING") JSONObject().put("state", ps)
                        else if (ps == "IDLE" && ms.optString("idleReason") == "ERROR") JSONObject().put("failed", true) else null
                    }
                    else -> null
                }
            } ?: throw CastException("cast_timeout")
            if (st.optBoolean("failed")) throw CastException("cast_refused")
            return JSONObject().put("playing", true).put("tv_name", tv.name).put("player_state", st.optString("state"))
        }
    }

    private fun stop(ctx: Context, args: JSONObject): JSONObject {
        val tv = pick(ctx, args.optString("tv"))
        Session(tv).use { s ->
            s.send("sender-0", "receiver-0", NS_CONN, JSONObject().put("type", "CONNECT"))
            s.send("sender-0", "receiver-0", NS_RECV, JSONObject().put("type", "GET_STATUS").put("requestId", 1))
            val app = s.waitFor(8_000) { ns, m ->
                if (ns != NS_RECV || m.optString("type") != "RECEIVER_STATUS") null
                else (m.optJSONObject("status")?.optJSONArray("applications")?.let { apps ->
                    (0 until apps.length()).map { apps.getJSONObject(it) }.firstOrNull { it.optString("appId") == RECEIVER }
                } ?: JSONObject())
            }
            val sid = app?.optString("sessionId").orEmpty()
            if (sid.isNotEmpty()) s.send("sender-0", "receiver-0", NS_RECV, JSONObject().put("type", "STOP").put("sessionId", sid).put("requestId", 2))
            return JSONObject().put("stopped", true).put("tv_name", tv.name)
        }
    }

    // ------------------------------------------------------------------ one TLS connection to a TV
    private class Session(tv: Tv) : AutoCloseable {
        private val socket: SSLSocket
        private val out: DataOutputStream
        private val inp: DataInputStream

        init {
            val trustAll = arrayOf<TrustManager>(object : X509TrustManager {
                override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
                override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
                override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
            })
            val ssl = SSLContext.getInstance("TLS").apply { init(null, trustAll, SecureRandom()) }
            val raw = java.net.Socket()
            try {
                raw.connect(InetSocketAddress(tv.host, tv.port), 5000)
            } catch (e: Exception) {
                throw CastException("cast_timeout")
            }
            socket = ssl.socketFactory.createSocket(raw, tv.host, tv.port, true) as SSLSocket
            socket.soTimeout = 6000
            socket.startHandshake()
            socket.soTimeout = 1000
            out = DataOutputStream(socket.outputStream)
            inp = DataInputStream(socket.inputStream)
        }

        fun send(src: String, dst: String, ns: String, payload: JSONObject) {
            val msg = encode(src, dst, ns, payload.toString())
            synchronized(out) {
                out.writeInt(msg.size)
                out.write(msg)
                out.flush()
            }
        }

        /** Reads messages until [match] returns a value (answers heartbeat pings meanwhile). */
        fun <T> waitFor(ms: Long, match: (String, JSONObject) -> T?): T? {
            val end = System.currentTimeMillis() + ms
            while (System.currentTimeMillis() < end) {
                val len = try { inp.readInt() } catch (_: java.net.SocketTimeoutException) { continue }
                if (len <= 0 || len > 1_000_000) return null
                val buf = ByteArray(len)
                inp.readFully(buf)
                val (src, ns, text) = decode(buf)
                val json = try { JSONObject(text) } catch (_: Exception) { continue }
                if (ns == NS_HEART && json.optString("type") == "PING") {
                    send("sender-0", src.ifEmpty { "receiver-0" }, NS_HEART, JSONObject().put("type", "PONG"))
                    continue
                }
                match(ns, json)?.let { return it }
            }
            return null
        }

        override fun close() {
            try { socket.close() } catch (_: Exception) {}
        }
    }

    // ------------------------------------------------------------------ CastMessage protobuf (fields 1-6)
    private fun varint(o: ByteArrayOutputStream, v: Int) {
        var x = v
        while (x and 0x7F.inv() != 0) { o.write((x and 0x7F) or 0x80); x = x ushr 7 }
        o.write(x)
    }

    private fun str(o: ByteArrayOutputStream, field: Int, s: String) {
        val b = s.toByteArray(Charsets.UTF_8)
        varint(o, (field shl 3) or 2)
        varint(o, b.size)
        o.write(b)
    }

    fun encode(src: String, dst: String, ns: String, payload: String): ByteArray {
        val o = ByteArrayOutputStream()
        varint(o, (1 shl 3) or 0); varint(o, 0)        // protocol_version CASTV2_1_0
        str(o, 2, src)
        str(o, 3, dst)
        str(o, 4, ns)
        varint(o, (5 shl 3) or 0); varint(o, 0)        // payload_type STRING
        str(o, 6, payload)
        return o.toByteArray()
    }

    /** (source_id, namespace, payload_utf8) */
    fun decode(b: ByteArray): Triple<String, String, String> {
        var i = 0
        var src = ""
        var ns = ""
        var text = ""
        fun readVarint(): Long {
            var shift = 0
            var r = 0L
            while (i < b.size) {
                val x = b[i++].toInt() and 0xFF
                r = r or ((x and 0x7F).toLong() shl shift)
                if (x and 0x80 == 0) break
                shift += 7
            }
            return r
        }
        while (i < b.size) {
            val key = readVarint().toInt()
            val field = key ushr 3
            when (key and 7) {
                0 -> readVarint()
                2 -> {
                    val len = readVarint().toInt()
                    if (len < 0 || i + len > b.size) break
                    val s = String(b, i, len, Charsets.UTF_8)
                    i += len
                    when (field) { 2 -> src = s; 4 -> ns = s; 6 -> text = s }
                }
                else -> break
            }
        }
        return Triple(src, ns, text)
    }
}
