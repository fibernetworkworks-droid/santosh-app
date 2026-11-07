package hoola.kit

// Made by Hoola App Sahayak (v0.412 NAKSHA LIVE). Maps, a rider's location while on shift, and live tracking of one order.
// - Only when the business turned tracking on (the app's backend says `track`), and only in a build that declares the
//   location service (older builds never offer the shift button).
// - The RIDER starts it: a plain notice first (what is shared, with whom, until when), then Android's own location dialog,
//   then a visible notification for the whole shift. "End shift" stops it at once; the server also wipes the position.
// - Battery: the phone sends a point only when it has MOVED (15 m) and at most every 5 s while moving, every 30 s when standing.
// - A customer sees ONLY the rider bringing her order, only while it is on its way (the server decides, not this phone).
// - The map is MapLibre (open source) with OpenFreeMap tiles: no map key, no map bill. Its library loads from her Hoola server.

import android.Manifest
import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/** One point on a map. kind: "rider" | "dest" | "me". */
data class MapPin(val lat: Double, val lng: Double, val label: String, val kind: String = "rider")

object Track {
    /** This phone's shift (staff). */
    val onShift = mutableStateOf(false)
    /** Live rider positions from the stream: key -> (lat, lng, name, orders this viewer may know about). */
    val riders = mutableStateMapOf<String, Pair<MapPin, List<String>>>()
    /** Bumps when a rider moves: tracking screens re-read their order. */
    val tick = mutableStateOf(0)

    private fun cfg(): JSONObject? = AppData.backend().optJSONObject("track")?.takeIf { it.optBoolean("on") }
    val on: Boolean get() = cfg() != null
    val coll: String get() = cfg()?.optString("coll", "") ?: ""
    fun onTheWay(status: String): Boolean {
        val a = cfg()?.optJSONArray("statuses") ?: return false
        return (0 until a.length()).any { a.optString(it) == status }
    }

    /** This build declares the location service (an app built before tracking was turned on does not). */
    fun declared(ctx: Context): Boolean = try {
        ctx.packageManager.getServiceInfo(ComponentName(ctx, TrackService::class.java), 0); true
    } catch (_: Exception) {
        false
    }

    fun allowed(ctx: Context): Boolean =
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    suspend fun load() {
        if (!(Auth.isStaff || Auth.role == "partner") || !on) return   // v0.435 a delivery partner too
        val r = Cloud.call("GET", "/track/me", null, Auth.token())
        if (r.ok) onShift.value = r.body.optBoolean("on")
    }

    /** Start / end the shift on the server, then the service. */
    suspend fun setShift(ctx: Context, start: Boolean): String? {
        val r = Cloud.call("POST", "/track/shift", JSONObject().put("on", start), Auth.token())
        if (!r.ok) return r.error.ifEmpty { if (r.offline) Strings.offline else Strings.tryAgain }
        onShift.value = start
        if (start) startService(ctx) else ctx.stopService(Intent(ctx, TrackService::class.java))
        return null
    }

    fun startService(ctx: Context) {
        if (!declared(ctx) || !allowed(ctx)) return
        try { ContextCompat.startForegroundService(ctx, Intent(ctx, TrackService::class.java)) } catch (_: Exception) {}
    }

    /** From the live stream ("pos" events). */
    fun onPos(e: JSONObject) {
        val k = e.optString("member")
        if (e.optBoolean("off") || !e.has("lat")) {
            riders.remove(k)
        } else {
            val orders = when (val o = e.opt("orders")) {
                is JSONArray -> (0 until o.length()).map { o.optString(it) }
                is JSONObject -> o.keys().asSequence().toList()
                else -> emptyList()
            }
            riders[k] = MapPin(e.optDouble("lat"), e.optDouble("lng"), e.optString("name"), "rider") to orders
        }
        tick.value += 1
    }
}

/** The rider's location while the shift is on: a visible notification the whole time, points only when the phone moved. */
class TrackService : Service(), LocationListener {
    private var lm: LocationManager? = null
    private var slow = false
    private var stillSince = 0L
    private var sending = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val nm = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26 && nm?.getNotificationChannel(CHANNEL) == null) {
            nm?.createNotificationChannel(NotificationChannel(CHANNEL, Strings.shiftChannel, NotificationManager.IMPORTANCE_LOW))
        }
        val open = PendingIntent.getActivity(this, 0, packageManager.getLaunchIntentForPackage(packageName) ?: Intent(),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val n: Notification = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(applicationInfo.icon)
            .setContentTitle(Strings.onShift)
            .setContentText(Strings.shiftNote)
            .setOngoing(true)
            .setContentIntent(open)
            .build()
        try {
            ServiceCompat.startForeground(this, 41, n,
                if (Build.VERSION.SDK_INT >= 29) ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION else 0)
        } catch (_: Exception) {
            stopSelf(); return START_NOT_STICKY
        }
        listen(fast = true)
        return START_NOT_STICKY
    }

    @SuppressLint("MissingPermission")
    private fun listen(fast: Boolean) {
        if (!Track.allowed(this)) { stopSelf(); return }
        val m = lm ?: (getSystemService(Context.LOCATION_SERVICE) as? LocationManager) ?: return
        lm = m
        try { m.removeUpdates(this) } catch (_: Exception) {}
        slow = !fast
        val every = if (fast) 5_000L else 30_000L
        for (p in listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)) {
            try { if (m.isProviderEnabled(p)) m.requestLocationUpdates(p, every, 15f, this, Looper.getMainLooper()) } catch (_: Exception) {}
        }
    }

    override fun onLocationChanged(l: Location) {
        val moving = l.hasSpeed() && l.speed > 1f
        val now = System.currentTimeMillis()
        if (moving) { stillSince = 0; if (slow) listen(fast = true) }
        else { if (stillSince == 0L) stillSince = now; if (!slow && now - stillSince > 120_000) listen(fast = false) }
        if (sending) return
        sending = true
        val body = JSONObject().put("lat", l.latitude).put("lng", l.longitude)
        if (l.hasAccuracy()) body.put("acc", l.accuracy.toDouble())
        if (l.hasSpeed()) body.put("speed", l.speed.toDouble())
        if (l.hasBearing()) body.put("heading", l.bearing.toDouble())
        Db.scope.launch {
            val r = Cloud.call("POST", "/track/pos", body, Auth.token())
            sending = false
            if (r.code == 409 || r.code == 401 || r.code == 403) {      // the shift ended elsewhere / signed out
                Track.onShift.value = false
                stopSelf()
            }
        }
    }

    @Deprecated("old API") override fun onStatusChanged(provider: String?, status: Int, extras: android.os.Bundle?) {}
    override fun onProviderEnabled(provider: String) {}
    override fun onProviderDisabled(provider: String) {}

    override fun onDestroy() {
        try { lm?.removeUpdates(this) } catch (_: Exception) {}
        super.onDestroy()
    }

    companion object { const val CHANNEL = "hoola_shift" }
}

/** Staff: Start shift / End shift, with the notice Play requires before the location dialog. Shows nothing when tracking is off. */
@Composable
fun ShiftBlock() {
    if (!(Auth.isStaff || Auth.role == "partner") || !Track.on) return   // v0.435 a delivery partner too
    val c = ctx()
    val scope = rememberCoroutineScope()
    var ask by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    val on by Track.onShift
    LaunchedEffect(Auth.me.value) {
        Track.load()
        if (Track.onShift.value) Track.startService(c)            // the app came back: the shift keeps sharing
    }
    val go: () -> Unit = {
        busy = true
        scope.launch { Track.setShift(c, true)?.let { Act.toast(c, it) }; busy = false }
    }
    val perm = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { res ->
        if (res[Manifest.permission.ACCESS_FINE_LOCATION] == true || res[Manifest.permission.ACCESS_COARSE_LOCATION] == true) go()
        else Act.toast(c, Strings.locationDenied)
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (!Track.declared(c)) { Small(Strings.updateForShift); return@Column }
        Small(if (on) Strings.shiftOnNote else Strings.shiftOffNote)
        Btn(if (on) Strings.endShift else Strings.startShift, kind = if (on) BtnKind.Danger else BtnKind.Primary, icon = "pin",
            enabled = !busy, modifier = Modifier.fillMaxWidth()) {
            if (on) { busy = true; scope.launch { Track.setShift(c, false)?.let { Act.toast(c, it) }; busy = false } }
            else ask = true
        }
    }
    if (ask) AlertDialog(
        onDismissRequest = { ask = false },
        title = { Text(Strings.shareTitle) },
        text = { Text(Strings.shareWhy) },
        confirmButton = {
            TextButton(onClick = {
                ask = false
                if (Track.allowed(c)) go() else {
                    val want = mutableListOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
                    if (Build.VERSION.SDK_INT >= 33) want.add(Manifest.permission.POST_NOTIFICATIONS)
                    perm.launch(want.toTypedArray())
                }
            }) { Text(Strings.cont) }
        },
        dismissButton = { TextButton(onClick = { ask = false }) { Text(Strings.later) } },
    )
}

private val MAP_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/static/vendor/maplibre/maplibre-gl.css"><style>html,body,#m{margin:0;height:100%}
.p{width:16px;height:16px;border-radius:50%;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35)}
.rider{background:#1e9e5a}.dest{background:#d0453a}.me{background:#2f6fd6}</style></head><body><div id="m"></div>
<script src="/static/vendor/maplibre/maplibre-gl.js"></script><script>
var map=new maplibregl.Map({container:'m',style:'https://tiles.openfreemap.org/styles/liberty',center:[78.96,22.6],zoom:4,attributionControl:{compact:true}});
var marks=[],fitted=false;
window.HoolaMap={set:function(pins){marks.forEach(function(m){m.remove()});marks=[];var b=new maplibregl.LngLatBounds();
pins.forEach(function(p){var el=document.createElement('div');el.className='p '+p.kind;el.title=p.label;
marks.push(new maplibregl.Marker({element:el}).setLngLat([p.lng,p.lat]).setPopup(new maplibregl.Popup({offset:12}).setText(p.label)).addTo(map));b.extend([p.lng,p.lat]);});
if(pins.length===1){map.easeTo({center:[pins[0].lng,pins[0].lat],zoom:Math.max(map.getZoom(),14)});}
else if(pins.length>1){map.fitBounds(b,{padding:48,maxZoom:16,duration:fitted?600:0});fitted=true;}}};
</script></body></html>"""

/** A real map (MapLibre + OpenFreeMap, no key) with the given pins; re-drawn when they change. */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun LiveMap(pins: List<MapPin>, modifier: Modifier = Modifier.fillMaxWidth().height(280.dp)) {
    val json = JSONArray(pins.map { JSONObject().put("lat", it.lat).put("lng", it.lng).put("label", it.label).put("kind", it.kind) }).toString()
    var ready by remember { mutableStateOf(false) }
    AndroidView(modifier = modifier, factory = { cx ->
        WebView(cx).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = false
            settings.allowFileAccess = false
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView?, url: String?) { ready = true }
            }
            loadDataWithBaseURL(Cloud.baseUrl + "/", MAP_HTML, "text/html", "utf-8", null)
        }
    }, update = { v -> if (ready) v.evaluateJavascript("window.HoolaMap&&HoolaMap.set($json)", null) })
}

/** The customer's own order on its way: the rider on the map, how far, about how long; "near" / "arrived" when it happens. */
@Composable
fun TrackOrderBlock(coll: String, id: String) {
    var info by remember(id) { mutableStateOf<JSONObject?>(null) }
    val tick by Track.tick
    LaunchedEffect(id, tick / 3, Live.rev(coll)) {                // a fresh read every few moves + on any change of the order
        val r = Cloud.call("GET", "/track/c/$coll/$id", null, Auth.token())
        if (r.ok) info = r.body
    }
    val i = info ?: return
    val live = Track.riders.values.firstOrNull { id in it.second }?.first
    val rd = i.optJSONObject("rider")
    val pins = mutableListOf<MapPin>()
    val rider = live ?: rd?.takeIf { it.has("lat") }?.let { MapPin(it.optDouble("lat"), it.optDouble("lng"), it.optString("name"), "rider") }
    rider?.let { pins.add(it.copy(label = it.label.ifEmpty { Strings.rider })) }
    i.optJSONObject("dest")?.let { pins.add(MapPin(it.optDouble("lat"), it.optDouble("lng"), Strings.yourPlace, "dest")) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        when {
            i.optBoolean("arrived") -> Title(Strings.riderArrived)
            i.optBoolean("near") -> Title(Strings.riderNear)
            i.optBoolean("tracking") -> Title((rd?.optString("name") ?: Strings.rider).ifEmpty { Strings.rider } + " · " + Strings.onTheWay)
            else -> Small(Strings.notOnTheWay)
        }
        if (i.has("eta_min")) Small(Strings.about + " ${i.optInt("eta_min")} min · " + String.format(java.util.Locale.US, "%.1f km", i.optDouble("km")) + " · " + Strings.estimate)
        if (pins.isNotEmpty()) LiveMap(pins)
    }
}

/** Staff / admin: every rider on shift on one map, moving as they move. */
@Composable
fun RidersMap() {
    if (!Auth.isStaff || !Track.on) return
    var list by remember { mutableStateOf<List<Item>>(emptyList()) }
    LaunchedEffect(Unit) {
        val r = Cloud.call("GET", "/track/riders", null, Auth.token())
        if (r.ok) list = arrList(r.body.optJSONArray("riders"))
    }
    val pins = LinkedHashMap<String, MapPin>()
    list.filter { it.o.has("lat") }.forEach { pins[it.s("member")] = MapPin(it.n("lat"), it.n("lng"), it.s("name")) }
    Track.riders.forEach { (k, v) -> pins[k] = v.first }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Title(Strings.ridersOnShift + " (${pins.size})")
        if (pins.isEmpty()) Small(Strings.nobodyOnShift) else LiveMap(pins.values.toList())
    }
}

/** On a row card: "Track live" while that row is on its way (the customer's order, or any for staff). */
@Composable
fun TrackButton(coll: String, r: Item) {
    if (!Track.on || coll != Track.coll || !Track.onTheWay(r.s("status")) || r.b("pending")) return
    var open by remember(r.id) { mutableStateOf(false) }
    Btn(if (open) Strings.hideMap else Strings.trackLive, kind = BtnKind.Tonal, icon = "pin", small = true) { open = !open }
    if (open) TrackOrderBlock(coll, r.id)
}
