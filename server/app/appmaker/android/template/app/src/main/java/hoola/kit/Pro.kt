package hoola.kit

// Made by Hoola App Sahayak (v0.340 HAR FEATURE 2). Three phone features a screen uses with one call:
// - ScanField: a barcode / QR code read by Google's code scanner (Google Play services shows its own camera screen; the
//   app itself needs NO camera permission and never sees the camera), or typed when the phone has no scanner.
// - StatsBlock: the staff dashboard - counts, status mix, rows per day (a bar chart drawn here, no chart library) and the
//   money total, from the app's own server (staff only; customers never see the business's numbers).
// - FileField (v0.346): a PDF document (prescription, ID proof, bill, resume) from the system file picker - no storage
//   permission; copied into the app's own cache and sent by the outbox (the server checks it is a plain PDF, 10 MB max).
// - StopsBlock (v0.350 NAKSHA): staff see every row with a location, nearest first from where they are, and open the whole
//   route in Google Maps through Google's official Maps URLs (no map key, no map tiles in the app).
// - Inbox: every update the app was told about (order moved, new order for staff), kept on the phone, newest first.

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.rememberCoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.ui.Alignment
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import org.json.JSONArray
import org.json.JSONObject

/** A barcode / QR box for a form: Scan opens Google's scanner, the code lands in AppState.form[key]; typing works too. */
@Composable
fun ScanField(label: String, key: String) {
    val c = ctx()
    val v = AppState.form[key].orEmpty()
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Label(label)
        OutlinedTextField(value = v, onValueChange = { AppState.form[key] = it.take(200) }, singleLine = true,
            modifier = Modifier.fillMaxWidth(), placeholder = { Text(Strings.scanHint) })
        Btn(Strings.scan, kind = BtnKind.Tonal, icon = "scan", small = true) { Scanner.scan(c) { code -> AppState.form[key] = code.take(200) } }
    }
}

object Scanner {
    fun scan(ctx: Context, done: (String) -> Unit) {
        try {
            val opts = GmsBarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_ALL_FORMATS).enableAutoZoom().build()
            GmsBarcodeScanning.getClient(ctx, opts).startScan()
                .addOnSuccessListener { b -> (b.rawValue ?: b.displayValue)?.let { if (it.isNotBlank()) done(it.trim()) } }
                .addOnFailureListener { Act.toast(ctx, Strings.scanFailed) }
        } catch (_: Exception) {
            Act.toast(ctx, Strings.scanFailed)
        }
    }
}

/** The staff dashboard of this app (counts, status mix, last 14 days, money). Shows nothing to customers. */
@Composable
fun StatsBlock() {
    if (!Auth.isStaff) return
    var data by remember { mutableStateOf<JSONObject?>(null) }
    var failed by remember { mutableStateOf(false) }
    LaunchedEffect(Auth.me.value) {
        val r = Cloud.call("GET", "/stats", null, Auth.token())
        if (r.ok) data = r.body else failed = true
    }
    val d = data
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Title(Strings.dashboard)
        if (d == null) {
            Small(if (failed) Strings.offline else Strings.loading)
            return@Column
        }
        val lists = d.optJSONArray("lists") ?: JSONArray()
        for (i in 0 until lists.length()) {
            val l = lists.optJSONObject(i) ?: continue
            HCard {
                Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                    Title(l.optString("label"))
                    Title(l.optInt("count").toString())
                }
                if (!l.isNull("total")) Small(Strings.total + ": " + rupees(l.optDouble("total", 0.0)))
                l.optJSONObject("rating")?.let { rt -> Small("★ " + rt.optDouble("avg") + " (" + rt.optInt("count") + ")") }   // v0.353
                val st = l.optJSONObject("status")
                if (st != null && st.length() > 0) {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 4.dp)) {
                        st.keys().asSequence().take(4).forEach { k -> Pill("$k ${st.optInt(k)}", "info") }
                    }
                }
                val daily = l.optJSONArray("daily") ?: JSONArray()
                Bars(List(daily.length()) { daily.optInt(it) }, Strings.last14 + " " + l.optString("label"))
            }
        }
        // v0.352 / v0.353 who has how much open work, and their customers' average stars
        val team = d.optJSONArray("team") ?: JSONArray()
        if (team.length() > 0) HCard {
            Title(Strings.myTeam)
            if (d.optInt("unassigned") > 0) Pill("${d.optInt("unassigned")} " + Strings.notAssigned, "warn")
            for (i in 0 until team.length()) {
                val p = team.optJSONObject(i) ?: continue
                Small(p.optString("name") + " · " + p.optInt("open") + " " + Strings.openWork +
                    if (!p.isNull("rating")) " · ★ " + p.optDouble("rating") + " (" + p.optInt("rated") + ")" else "")
            }
        }
    }
}

/** A small bar chart (one bar a day), drawn on a Canvas in the app's own colours. */
@Composable
fun Bars(values: List<Int>, description: String) {
    val bar = H.c.primary
    val base = H.c.line
    val max = (values.maxOrNull() ?: 0).coerceAtLeast(1)
    Canvas(Modifier.fillMaxWidth().height(72.dp).padding(top = 8.dp).semantics { contentDescription = "$description: ${values.joinToString(", ")}" }) {
        val n = values.size.coerceAtLeast(1)
        val gap = 4.dp.toPx()
        val w = (size.width - gap * (n - 1)) / n
        drawLine(base, Offset(0f, size.height), Offset(size.width, size.height), strokeWidth = 1.dp.toPx())
        values.forEachIndexed { i, v ->
            val h = (size.height - 2f) * v / max
            if (h > 0f) drawRoundRect(bar, Offset(i * (w + gap), size.height - h), Size(w, h), CornerRadius(3.dp.toPx(), 3.dp.toPx()))
        }
    }
}

/** What the app was told about, newest first (kept on this phone, at most 50). Updates.check adds to it. */
object Inbox {
    private const val KEY = "hoola_inbox"
    val unread = mutableStateOf(0)

    fun all(ctx: Context): List<JSONObject> = try {
        val a = JSONArray(Store.get(ctx, KEY).ifEmpty { "[]" })
        List(a.length()) { a.getJSONObject(it) }
    } catch (_: Exception) {
        emptyList()
    }

    fun add(ctx: Context, title: String, text: String, at: String) {
        val a = JSONArray().put(JSONObject().put("title", title).put("text", text).put("at", at).put("new", true))
        all(ctx).take(49).forEach { a.put(it) }
        Store.put(ctx, KEY, a.toString())
        unread.value = count(ctx)
    }

    fun count(ctx: Context): Int = all(ctx).count { it.optBoolean("new") }

    fun seen(ctx: Context) {
        val a = JSONArray()
        all(ctx).forEach { a.put(it.put("new", false)) }
        Store.put(ctx, KEY, a.toString())
        unread.value = 0
    }
}

/** The kit's inbox screen (id "hoola_inbox"). */
@Composable
fun InboxScreen() {
    val c = ctx()
    val items = remember { Inbox.all(c) }
    LaunchedEffect(Unit) { Inbox.seen(c) }
    Page(Strings.inbox) {
        if (items.isEmpty()) block { Empty("bell", Strings.inboxEmpty) }
        items.forEach { x ->
            block {
                HCard(tint = x.optBoolean("new")) {
                    Title(x.optString("title"))
                    if (x.optString("text").isNotEmpty()) Small(x.optString("text"))
                    Small(x.optString("at").take(16).replace("T", " "))
                }
            }
        }
    }
}


/** v0.346 a PDF for a form: the system file picker (no permission), at most 10 MB, sent by the outbox. */
@Composable
fun FileField(label: String, key: String) {
    val c = ctx()
    val scope = rememberCoroutineScope()
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) scope.launch {
            val got = withContext(Dispatchers.IO) { Docs.copy(c, uri) }
            if (got != null) {
                AppState.form[key] = "local:" + got.first
                AppState.form[key + "__name"] = got.second
            } else Act.toast(c, Strings.fileFailed)
        }
    }
    val v = AppState.form[key].orEmpty()
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Label(label)
        if (v.isNotEmpty()) Small("📄 " + AppState.form[key + "__name"].orEmpty().ifEmpty { "PDF" })
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Btn(if (v.isEmpty()) Strings.addFile else Strings.changeFile, kind = BtnKind.Tonal, icon = "receipt", small = true) {
                pick.launch(arrayOf("application/pdf"))
            }
            if (v.isNotEmpty()) Btn(Strings.remove, kind = BtnKind.Ghost, small = true) { AppState.form.remove(key); AppState.form.remove(key + "__name") }
        }
    }
}

object Docs {
    private const val MAX = 10 * 1024 * 1024

    /** The picked PDF copied into the app's cache -> (path, file name); null = not a PDF / too big / unreadable. */
    fun copy(ctx: Context, uri: Uri): Pair<String, String>? = try {
        var name = "document.pdf"
        ctx.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cur ->
            if (cur.moveToFirst()) name = cur.getString(0) ?: name
        }
        val bytes = ctx.contentResolver.openInputStream(uri)?.use { inp ->
            val buf = java.io.ByteArrayOutputStream()
            val chunk = ByteArray(64 * 1024)
            while (true) {
                val n = inp.read(chunk)
                if (n < 0) break
                buf.write(chunk, 0, n)
                if (buf.size() > MAX) return null
            }
            buf.toByteArray()
        } ?: return null
        if (bytes.size < 5 || String(bytes, 0, 5, Charsets.US_ASCII) != "%PDF-") null
        else {
            val f = java.io.File(ctx.cacheDir, "doc_" + java.util.UUID.randomUUID().toString() + ".pdf")
            f.writeBytes(bytes)
            Pair(f.absolutePath, name.take(80))
        }
    } catch (_: Exception) {
        null
    }
}


// ---------------------------------------------------------------- v0.350 NAKSHA: stops on a map
object Maps {
    private val LOC = Regex("""^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$""")
    val DONE = setOf("Delivered", "Done", "Completed", "Cancelled", "Closed", "Rejected")

    fun point(s: String): Pair<Double, Double>? = LOC.matchEntire(s)?.let { Pair(it.groupValues[1].toDouble(), it.groupValues[2].toDouble()) }

    /** Straight-line km between two "lat,lng" points (haversine). */
    fun km(a: String, b: String): Double? {
        val p = point(a) ?: return null
        val q = point(b) ?: return null
        val r = 6371.0
        val dLat = Math.toRadians(q.first - p.first)
        val dLng = Math.toRadians(q.second - p.second)
        val h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(Math.toRadians(p.first)) * Math.cos(Math.toRadians(q.first)) * Math.sin(dLng / 2) * Math.sin(dLng / 2)
        return 2 * r * Math.asin(Math.sqrt(h))
    }

    /** Google's official directions URL: from here (or the phone's own position) through up to 9 stops. */
    fun route(origin: String?, stops: List<String>): String {
        val s = stops.take(10)
        val u = StringBuilder("https://www.google.com/maps/dir/?api=1&travelmode=driving")
        if (!origin.isNullOrEmpty()) u.append("&origin=").append(Uri.encode(origin))
        u.append("&destination=").append(Uri.encode(s.last()))
        if (s.size > 1) u.append("&waypoints=").append(Uri.encode(s.dropLast(1).joinToString("|")))
        return u.toString()
    }
}

/** Staff: the open rows that carry a location, nearest first, each opens in Maps; "Route in Maps" for all of them. */
@Composable
fun StopsBlock() {
    if (!Auth.isStaff) return
    val c = ctx()
    val colls = Db.collections().filter { coll -> Db.fields(coll).any { it.s("type") == "location" } }
    if (colls.isEmpty()) return
    var here by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(Unit) { if (Places.allowed(c)) here = Places.here(c) }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        colls.forEach { coll ->
            val key = Db.fields(coll).first { it.s("type") == "location" }.s("key")
            val open = liveRows(coll).filter { Maps.point(it.s(key)) != null && it.s("status") !in Maps.DONE }
            val h = here
            val rows = if (h != null) open.sortedBy { Maps.km(h, it.s(key)) ?: 1e9 } else open
            Title(T("Today's stops") + " · " + T(Db.label(coll)) + " (${rows.size})")
            if (rows.isEmpty()) Small(T("No open stops with a location."))
            rows.take(20).forEach { r ->
                HCard(onClick = { Act.maps(c, r.s(key)) }) {
                    Title(listOf(r.s("name"), r.s("title"), r.s("address")).firstOrNull { it.isNotEmpty() } ?: T(Db.label(coll)))
                    val d = h?.let { Maps.km(it, r.s(key)) }
                    Small(listOfNotNull(d?.let { String.format(java.util.Locale.US, "%.1f km", it) }, r.s("status").takeIf { it.isNotEmpty() }?.let { T(it) },
                        r.s("address").takeIf { it.isNotEmpty() }).joinToString(" · "))
                }
            }
            if (rows.isNotEmpty()) Btn(T("Route in Maps"), kind = BtnKind.Tonal, icon = "pin", modifier = Modifier.fillMaxWidth()) {
                Act.open(c, Maps.route(h, rows.take(10).map { it.s(key) }))
            }
        }
    }
}

// ---------------------------------------------------------------- v0.352 KAAM BAANTO: work given to one staff member
/** The app's staff (first names only, never e-mails) for the assign buttons. `admin` = this account gives work to others. */
object Team {
    val people = mutableStateOf<List<Item>>(emptyList())
    val admin = mutableStateOf(false)
    private var loadedFor = ""

    suspend fun load(force: Boolean = false) {
        if (!Auth.isStaff) return
        val who = Auth.me.value?.id ?: ""
        if (!force && loadedFor == who && people.value.isNotEmpty()) return
        val r = Cloud.call("GET", "/team", null, Auth.token())
        if (!r.ok) return
        val a = r.body.optJSONArray("team") ?: JSONArray()
        withContext(Dispatchers.Main) {
            people.value = (0 until a.length()).mapNotNull { a.optJSONObject(it) }.map { Item(it) }
            admin.value = r.body.optBoolean("admin")
        }
        loadedFor = who
    }

    /** Whether this account may work on (change) the row: free, mine, or I am an admin. The server checks it again. */
    fun mayWork(r: Item): Boolean {
        val to = r.s("assigned_to")
        return to.isEmpty() || to == (Auth.me.value?.id ?: "") || admin.value
    }
}

/** On a staff row card: who has it, and - admin: one chip per staff member (tap again = take back); staff: "I'll take it"
 *  on a free row, "Give back" on their own. Sent through the outbox like any change (works offline). */
@Composable
fun AssignBox(coll: String, r: Item) {
    if (!Auth.isStaff || r.b("pending")) return
    LaunchedEffect(Auth.me.value) { Team.load() }
    val meId = Auth.me.value?.id ?: ""
    val to = r.s("assigned_to")
    Row(Modifier.horizontalScroll(rememberScrollState()).padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically) {
        if (to.isNotEmpty()) Pill(Strings.withPerson + ": " + (if (to == meId) Strings.you else r.s("assigned_name")), if (to == meId) "ok" else "info")
        else Pill(Strings.notAssigned, "warn")
        if (Team.admin.value) {
            Team.people.value.forEach { p ->
                Chip(p.s("name"), selected = to == p.id) { Db.update(coll, r.id, mapOf("_assign" to if (to == p.id) "" else p.id)) }
            }
        } else if (to.isEmpty()) {
            Btn(Strings.takeIt, kind = BtnKind.Ghost, small = true) { Db.update(coll, r.id, mapOf("_assign" to "me")) }
        } else if (to == meId) {
            Btn(Strings.giveBack, kind = BtnKind.Ghost, small = true) { Db.update(coll, r.id, mapOf("_assign" to "")) }
        }
    }
}

// ---------------------------------------------------------------- v0.353 RAAY: the customer's rating of a finished row
/** The stars of a rated row (customer + staff see it), e.g. "★★★★☆ 4/5 · On time". */
fun starLine(n: Int, note: String = ""): String =
    "★".repeat(n.coerceIn(0, 5)) + "☆".repeat(5 - n.coerceIn(0, 5)) + " $n/5" + if (note.isNotBlank()) " · " + note.take(120) else ""

/** On the customer's own finished row (the server says `can_rate`): 1-5 stars + a short note, sent once through the
 *  outbox (works offline). A rated row shows its stars instead. */
@Composable
fun RateBox(coll: String, r: Item) {
    val n = r.i("rating")
    if (n > 0) {
        Small(starLine(n, r.s("rating_note")), maxLines = 3)
        return
    }
    if (!r.b("can_rate") || Auth.isStaff) return
    var sent by remember(r.id) { mutableStateOf(0) }
    if (sent > 0) {
        Small(starLine(sent) + " · " + Strings.thanksRating)
        return
    }
    var stars by remember(r.id) { mutableStateOf(0) }
    var note by remember(r.id) { mutableStateOf("") }
    Column(Modifier.padding(top = 6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Small(Strings.rateIt)
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            (1..5).forEach { i -> Chip("$i ★", selected = stars == i) { stars = i } }
        }
        if (stars > 0) {
            OutlinedTextField(value = note, onValueChange = { note = it.take(300) }, modifier = Modifier.fillMaxWidth(),
                placeholder = { Text(Strings.ratingNote) }, maxLines = 3)
            Btn(Strings.sendRating, small = true) {
                Db.update(coll, r.id, mapOf("_rate" to JSONObject().put("stars", stars).put("note", note.trim())))
                sent = stars
            }
        }
    }
}

// ---------------------------------------------------------------- v0.354 RASEED: the receipt of a finished row
/** "Receipt" on a finished row (the server says `receipt`): asks the app's server for a 15-minute signed link and opens the
 *  PDF in the phone's browser - no storage permission, no file sharing. Needs a network (said plainly when there is none). */
@Composable
fun ReceiptButton(coll: String, r: Item) {
    if (!r.b("receipt") || r.b("pending")) return
    val c = ctx()
    val scope = rememberCoroutineScope()
    var busy by remember(r.id) { mutableStateOf(false) }
    val label = when (r.s("receipt_kind")) { "invoice" -> Strings.invoice; "credit_note" -> Strings.creditNote; else -> Strings.receipt }   // v0.355 / v0.356
    Btn(if (busy) Strings.loading else label, kind = BtnKind.Ghost, small = true) {
        if (busy) return@Btn
        busy = true
        scope.launch {
            val res = Cloud.call("POST", "/c/$coll/${r.id}/receipt-link", JSONObject(), Auth.token())
            busy = false
            val url = res.body.optString("url")
            if (res.ok && url.startsWith("http")) Act.open(c, url)
            else Act.toast(c, res.error.ifEmpty { if (res.offline) Strings.offline else Strings.tryAgain })
        }
    }
}


// ---------------------------------------------------------------- v0.358 COUPON: the discount code box in the cart
/** Code + Apply: the app's server says the discount for THIS cart (nothing counted yet); the order carries the code and the
 *  server applies it again from its own prices. Changing the cart asks to apply again. */
@Composable
fun CouponBox() {
    val scope = rememberCoroutineScope()
    var code by remember { mutableStateOf(AppState.coupon.value) }
    var msg by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    val total = AppState.cartTotal("products")
    LaunchedEffect(total) { if (AppState.couponOff.value > 0) { AppState.couponOff.value = 0.0; AppState.coupon.value = ""; msg = Strings.couponAgain } }
    Column(Modifier.fillMaxWidth().padding(bottom = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(value = code, onValueChange = { code = it.uppercase().filter { ch -> ch.isLetterOrDigit() }.take(16) },
                singleLine = true, modifier = Modifier.weight(1f), placeholder = { Text(Strings.couponCode) })
            Btn(if (busy) Strings.loading else Strings.apply, kind = BtnKind.Tonal, small = true) {
                if (busy || code.length < 4) return@Btn
                busy = true
                scope.launch {
                    val cart = JSONArray()
                    AppState.cartItems("products").forEach { (it, q) -> cart.put(JSONObject().put("id", it.id).put("qty", q)) }
                    val r = Cloud.call("POST", "/coupon", JSONObject().put("code", code).put("cart", cart), Auth.token())
                    busy = false
                    if (r.ok && r.body.optBoolean("ok")) {
                        AppState.coupon.value = code
                        AppState.couponOff.value = r.body.optDouble("discount", 0.0)
                        msg = Strings.couponSaved + " " + rupees(AppState.couponOff.value) + " · " + Strings.total + " " + rupees(r.body.optDouble("total", total))
                    } else {
                        AppState.coupon.value = ""; AppState.couponOff.value = 0.0
                        msg = r.body.optString("why").ifEmpty { r.error.ifEmpty { if (r.offline) Strings.offline else Strings.tryAgain } }
                    }
                }
            }
        }
        if (msg.isNotEmpty()) Small(msg)
    }
}


// ---------------------------------------------------------------- v0.359 KHATA: the customer's udhaar ledger
/** My account: a customer sees her own balance + entries; staff see who owes how much and record a payment (cash / UPI;
 *  recorded only - the app never moves money). Shows nothing when there is no khata yet. */
@Composable
fun KhataBlock() {
    if (!Auth.signedIn) return
    val scope = rememberCoroutineScope()
    var data by remember { mutableStateOf<JSONObject?>(null) }
    var tick by remember { mutableStateOf(0) }
    LaunchedEffect(Auth.me.value, tick) {
        val r = Cloud.call("GET", if (Auth.isStaff) "/khata?all=1" else "/khata", null, Auth.token())
        if (r.ok) data = r.body
    }
    val d = data ?: return
    if (!Auth.isStaff) {
        val es = d.optJSONArray("entries") ?: JSONArray()
        if (es.length() == 0) return
        HCard {
            Title(Strings.myKhata)
            val bal = d.optDouble("balance", 0.0)
            Title(if (bal > 0) Strings.due + ": " + rupees(bal) else if (bal < 0) Strings.advance + ": " + rupees(-bal) else Strings.allClear)
            for (i in 0 until minOf(es.length(), 10)) {
                val e = es.optJSONObject(i) ?: continue
                Small((if (e.optString("kind") == "credit") "+ " else "− ") + rupees(e.optDouble("amount")) + " · " + e.optString("note").ifEmpty { e.optString("mode") }
                    + " · " + e.optString("at").take(10))
            }
        }
        return
    }
    val people = d.optJSONArray("customers") ?: JSONArray()
    if (people.length() == 0) return
    HCard {
        Title(Strings.khataDues + " · " + rupees(d.optDouble("total_due", 0.0)))
        for (i in 0 until minOf(people.length(), 50)) {
            val p = people.optJSONObject(i) ?: continue
            var amt by remember(p.optString("member")) { mutableStateOf("") }
            var busy by remember(p.optString("member")) { mutableStateOf(false) }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Small(p.optString("name") + ": " + rupees(p.optDouble("balance")), modifier = Modifier.weight(1f))
                if (p.optDouble("balance") > 0) {
                    OutlinedTextField(value = amt, onValueChange = { amt = it.filter { ch -> ch.isDigit() || ch == '.' }.take(10) }, singleLine = true,
                        modifier = Modifier.width(96.dp), placeholder = { Text("₹") })
                    Btn(if (busy) Strings.loading else Strings.received, kind = BtnKind.Ghost, small = true) {
                        if (busy || amt.isEmpty()) return@Btn
                        busy = true
                        scope.launch {
                            val r = Cloud.call("POST", "/khata/${p.optString("member")}/pay", JSONObject().put("amount", amt).put("mode", "cash"), Auth.token())
                            busy = false
                            if (r.ok) { amt = ""; tick++ }
                        }
                    }
                }
            }
        }
    }
}

/** Staff on an order card: "On credit" writes the order's server total to the customer's khata (once; through the outbox). */
@Composable
fun CreditButton(coll: String, r: Item) {
    if (!Auth.isStaff || r.b("pending") || coll != Db.orderList || r.n("total") <= 0 || r.s("status") == "Cancelled") return
    if (r.b("on_credit")) { Pill(Strings.onCredit, "warn"); return }
    Btn(Strings.giveCredit, kind = BtnKind.Ghost, small = true) { Db.update(coll, r.id, mapOf("_credit" to true)) }
}


// ---------------------------------------------------------------- v0.360 DELIVERY: the fee rule + open / closed in the cart
/** The delivery fee the server will add for goods worth `goods` (the same rule, from the app content). */
fun deliveryFee(goods: Double): Double {
    val d = AppData.backend().optJSONObject("delivery") ?: return 0.0
    if (!d.isNull("free_above") && d.has("free_above") && goods >= d.optDouble("free_above")) return 0.0
    return d.optDouble("fee", 0.0)
}

/** "Delivery ₹30 · free above ₹500" (or "Free delivery"), and a plain notice when the shop is closed or delivers only to
 *  some PIN codes - the order is still taken (the server adds a note, never refuses). */
@Composable
fun DeliveryLine() {
    val d = AppData.backend().optJSONObject("delivery") ?: return
    val goods = AppState.cartTotal("products") - AppState.couponOff.value
    val fee = deliveryFee(goods)
    Column(Modifier.fillMaxWidth().padding(bottom = 6.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        val free = if (d.has("free_above") && !d.isNull("free_above")) " · " + Strings.freeAbove + " " + rupees(d.optDouble("free_above")) else ""
        Small(if (fee > 0) Strings.delivery + ": " + rupees(fee) + free else Strings.freeDelivery)
        if (!d.optBoolean("open", true)) Pill(Strings.shopClosed + if (d.optString("hours").isNotEmpty()) " (" + d.optString("hours") + ")" else "", "warn")
        if (d.optBoolean("area")) Small(Strings.areaOnly)
    }
}


// ---------------------------------------------------------------- v0.371 SLOT: the delivery time slot in the cart
/** The slots with room (fresh from the app's server: today + the days ahead), as chips; the order carries the pick and the
 *  server books it again (a slot that filled up in between = the order still goes, with a note). */
@Composable
fun SlotPicker() {
    var list by remember { mutableStateOf<List<Item>>(emptyList()) }
    var loaded by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        val r = Cloud.call("GET", "/slots", null, Auth.token())
        if (r.ok) list = arrList(r.body.optJSONArray("slots"))
        loaded = true
        if (list.none { it.s("key") == AppState.slot.value }) AppState.slot.value = ""
    }
    Column(Modifier.fillMaxWidth().padding(bottom = 6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Small(Strings.pickSlot)
        if (loaded && list.isEmpty()) Small(Strings.noSlots)
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            list.forEach { sl ->
                Chip(sl.s("day") + " · " + sl.s("label"), selected = AppState.slot.value == sl.s("key")) {
                    AppState.slot.value = if (AppState.slot.value == sl.s("key")) "" else sl.s("key")
                }
            }
        }
    }
}


// ---------------------------------------------------------------- v0.377 CHHUTTI: move an order to another free slot
/** On an order with a delivery slot: "Change time" opens the free slots; a tap asks the server (her customer before the
 *  cut-off, staff any time) and refreshes the list. Needs a network (said plainly when there is none). */
@Composable
fun SlotChange(coll: String, r: Item) {
    if (r.s("slot").isEmpty() || r.b("pending") || r.s("status") in listOf("Cancelled", "Delivered", "Done")) return
    val c = ctx()
    val scope = rememberCoroutineScope()
    var open by remember(r.id) { mutableStateOf(false) }
    var list by remember(r.id) { mutableStateOf<List<Item>>(emptyList()) }
    if (!open) {
        Btn(Strings.changeTime, kind = BtnKind.Ghost, small = true) {
            open = true
            scope.launch { val res = Cloud.call("GET", "/slots", null, Auth.token()); if (res.ok) list = arrList(res.body.optJSONArray("slots")) }
        }
        return
    }
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        list.forEach { sl ->
            Chip(sl.s("day") + " · " + sl.s("label")) {
                scope.launch {
                    val res = Cloud.call("POST", "/c/$coll/${r.id}/slot", JSONObject().put("slot", sl.s("key")), Auth.token())
                    if (res.ok) { open = false; Db.refresh(coll) }
                    else Act.toast(c, res.error.ifEmpty { if (res.offline) Strings.offline else Strings.tryAgain })
                }
            }
        }
        Chip(Strings.cancelWord) { open = false }
    }
}


// ---------------------------------------------------------------- v0.378 BAAT: chat between a customer and the shop
/** The kit's chat screen (id "hoola_chat"): a customer sees her thread with the shop and writes; staff see every customer's
 *  thread (unread first) and reply. Refreshes every 10 seconds while open; needs a network to send. */
@Composable
fun ChatScreen() {
    if (!Auth.signedIn) {
        Page(Strings.chat) { block { Small(Strings.loginFirst) } }
        return
    }
    if (Auth.isStaff) StaffChat() else ThreadView(member = "", title = Strings.chat)
}

@Composable
private fun StaffChat() {
    var open by remember { mutableStateOf("") }
    var openName by remember { mutableStateOf("") }
    var list by remember { mutableStateOf<List<Item>>(emptyList()) }
    if (open.isNotEmpty()) {
        ThreadView(member = open, title = openName) { open = "" }
        return
    }
    LaunchedEffect(Unit) {
        while (true) {
            val r = Cloud.call("GET", "/chat?all=1", null, Auth.token())
            if (r.ok) list = arrList(r.body.optJSONArray("threads"))
            kotlinx.coroutines.delay(10_000)
        }
    }
    Page(Strings.customerMessages) {
        if (list.isEmpty()) block { Small(Strings.nothingYet) }
        list.forEach { t ->
            block {
                ListRow(t.s("name") + if (t.i("unread") > 0) " (${t.i("unread")})" else "", t.s("last")) { open = t.s("member"); openName = t.s("name") }
            }
        }
    }
}

@Composable
private fun ThreadView(member: String, title: String, onBack: (() -> Unit)? = null) {
    val scope = rememberCoroutineScope()
    var msgs by remember(member) { mutableStateOf<List<Item>>(emptyList()) }
    var text by remember(member) { mutableStateOf("") }
    var err by remember(member) { mutableStateOf("") }
    val path = if (member.isEmpty()) "/chat" else "/chat/$member"
    suspend fun load() {
        val r = Cloud.call("GET", path, null, Auth.token())
        if (r.ok) msgs = arrList(r.body.optJSONArray("messages"))
    }
    LaunchedEffect(member) { while (true) { load(); kotlinx.coroutines.delay(10_000) } }
    Page(title) {
        if (onBack != null) block { Btn(Strings.back, kind = BtnKind.Ghost, small = true) { onBack() } }
        if (msgs.isEmpty()) block { Small(if (member.isEmpty()) Strings.chatHint else Strings.nothingYet) }
        msgs.takeLast(100).forEach { m ->
            block {
                val mineSide = m.b("staff") == Auth.isStaff
                Row(Modifier.fillMaxWidth(), horizontalArrangement = if (mineSide) Arrangement.End else Arrangement.Start) {
                    HCard(modifier = Modifier.fillMaxWidth(0.82f)) {
                        Small(m.s("name") + " · " + m.s("at").take(16).replace("T", " "))
                        Body(m.s("text"))
                    }
                }
            }
        }
        block {
            OutlinedTextField(value = text, onValueChange = { text = it.take(1000) }, modifier = Modifier.fillMaxWidth(),
                placeholder = { Text(Strings.typeMessage) }, maxLines = 4)
            if (err.isNotEmpty()) Small(err)
            Btn(Strings.send, modifier = Modifier.fillMaxWidth().padding(top = 6.dp)) {
                val t = text.trim()
                if (t.isEmpty()) return@Btn
                scope.launch {
                    val r = Cloud.call("POST", path, JSONObject().put("text", t), Auth.token())
                    if (r.ok) { text = ""; err = ""; load() } else err = r.error.ifEmpty { if (r.offline) Strings.offline else Strings.tryAgain }
                }
            }
        }
    }
}
