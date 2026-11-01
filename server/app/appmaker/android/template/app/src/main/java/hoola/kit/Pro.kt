package hoola.kit

// Made by Hoola App Sahayak (v0.340 HAR FEATURE 2). Three phone features a screen uses with one call:
// - ScanField: a barcode / QR code read by Google's code scanner (Google Play services shows its own camera screen; the
//   app itself needs NO camera permission and never sees the camera), or typed when the phone has no scanner.
// - StatsBlock: the staff dashboard - counts, status mix, rows per day (a bar chart drawn here, no chart library) and the
//   money total, from the app's own server (staff only; customers never see the business's numbers).
// - Inbox: every update the app was told about (order moved, new order for staff), kept on the phone, newest first.

import android.content.Context
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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
