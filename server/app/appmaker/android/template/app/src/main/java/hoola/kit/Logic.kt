package hoola.kit

// Made by Hoola App Sahayak. v0.380 DIMAAG: the app's own logic on the phone - the SERVER decides every rule;
// these pieces only show what it says: linked rows (a picker + the parent's name), the workflow buttons this account may
// press, an approval waiting (and Approve / Reject when it is this account's turn), a row's linked children with "Add".

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

object Logic {
    /** The name of a linked row as the server sent it ("Sharma Traders" for customer = row_...). */
    fun refLabel(r: Item, key: String): String = r.o.optJSONObject("_labels")?.optString(key, "") ?: ""

    /** A row's title: the list's naming field, else its first filled text field. */
    fun title(coll: String, r: Item): String {
        val lf = Db.labelField(coll)
        if (lf.isNotEmpty() && r.has(lf)) return refLabel(r, lf).ifEmpty { r.s(lf) }
        val f = Db.fields(coll).firstOrNull { it.s("type") in listOf("text", "long_text", "phone", "email") && r.has(it.s("key")) }
        return f?.let { r.s(it.s("key")) } ?: Db.label(coll)
    }

    /** A value for showing: a link shows its row's name, never the id. */
    fun show(r: Item, f: Item): String = if (f.s("type") == "ref") refLabel(r, f.s("key")).ifEmpty { r.s(f.s("key")) } else r.s(f.s("key"))

    /** A function she marked callable (a price / EMI calculator) - runs on the server in its locked box. */
    suspend fun call(name: String, vararg args: Any?): String {
        val a = JSONArray()
        args.forEach { a.put(it ?: JSONObject.NULL) }
        val r = Cloud.call("POST", "/fn/$name", JSONObject().put("args", a), Auth.token())
        return if (r.ok) r.body.opt("result")?.toString() ?: "" else r.error.ifEmpty { Strings.tryAgain }
    }
}

/** Pick a row of another list (customer for an invoice, class for a student). The id travels; the name shows. */
@Composable
fun RefField(label: String, key: String, to: String, values: MutableMap<String, String> = AppState.picks) {
    val rows = liveRows(to)
    var open by remember(key) { mutableStateOf(false) }
    val cur = values[key] ?: ""
    val name = rows.firstOrNull { it.id == cur }?.let { Logic.title(to, it) } ?: ""
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Small(T(label))
        Btn(if (name.isNotEmpty()) name else Strings.choose + " " + T(Db.label(to)), kind = BtnKind.Outline, small = true) { open = !open }
        if (open) {
            var q by remember(key) { mutableStateOf("") }
            if (rows.size > 6) OutlinedTextField(value = q, onValueChange = { q = it.take(40) }, singleLine = true,
                modifier = Modifier.fillMaxWidth(), placeholder = { Text(Strings.search) })
            rows.filter { q.isBlank() || Logic.title(to, it).lowercase().contains(q.trim().lowercase()) }.take(40).forEach { r ->
                ListRow(Logic.title(to, r), chevron = false, trailing = if (r.id == cur) "✓" else "") {
                    values[key] = r.id
                    open = false
                }
            }
            if (rows.isEmpty()) Small(Strings.nothingYet)
        }
    }
}

/** The workflow on a row card: an approval waiting (+ Approve / Reject when it is this account's turn), else the steps
 *  this account may take now. The server checks every press again (who, required fields, conditions). */
@Composable
fun WorkflowBox(coll: String, r: Item) {
    if (r.b("pending")) return
    val c = ctx()
    val scope = rememberCoroutineScope()
    val p = r.o.optJSONObject("_pending")
    if (p != null) {
        Column(Modifier.padding(top = 6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Pill(T(p.optString("label")) + " · " + Strings.needsApproval + " (" + Strings.step + " " + p.optInt("step") + "/" + p.optInt("of") + ")", "warn")
            Small(Strings.waitingFor + ": " + T(p.optString("waiting_for")))
            if (p.optBoolean("can_decide")) {
                var note by remember(r.id) { mutableStateOf("") }
                var busy by remember(r.id) { mutableStateOf(false) }
                OutlinedTextField(value = note, onValueChange = { note = it.take(300) }, modifier = Modifier.fillMaxWidth(),
                    placeholder = { Text(Strings.note) }, maxLines = 2)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("approve" to Strings.approve, "reject" to Strings.reject).forEach { (d, label) ->
                        Btn(label, kind = if (d == "approve") BtnKind.Primary else BtnKind.Danger, small = true, enabled = !busy) {
                            busy = true
                            scope.launch {
                                val res = Cloud.call("POST", "/approvals/" + p.optString("id"), JSONObject().put("decision", d).put("note", note.trim()), Auth.token())
                                busy = false
                                Act.toast(c, if (res.ok) res.body.optString("say", Strings.done) else res.error.ifEmpty { if (res.offline) Strings.offline else Strings.tryAgain })
                                Db.refresh(coll)
                            }
                        }
                    }
                }
            }
        }
        return
    }
    val acts = r.list("_actions")
    if (acts.isEmpty()) return
    Row(Modifier.horizontalScroll(rememberScrollState()).padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        acts.forEach { a ->
            Btn(T(a.s("label")) + if (a.b("approval")) " *" else "", kind = BtnKind.Tonal, small = true) {
                Db.update(coll, r.id, mapOf(Db.workflowField(coll) to a.s("to")))
                if (a.b("approval")) Act.toast(c, T(a.s("label")) + ": " + Strings.needsApproval)
            }
        }
    }
}

/** A row's linked children (an order's items, a class's students) + Add (the link filled in). Needs a network. */
@Composable
fun RelatedBlock(coll: String, r: Item) {
    if (r.b("pending")) return
    val rels = Db.relations(coll)
    if (rels.isEmpty()) return
    rels.forEach { rel ->
        val kid = rel.s("coll")
        var rows by remember(r.id, rel.s("name")) { mutableStateOf<List<Item>?>(null) }
        var adding by remember(r.id, rel.s("name")) { mutableStateOf(false) }
        var tick by remember(r.id, rel.s("name")) { mutableStateOf(0) }
        LaunchedEffect(r.id, rel.s("name"), tick) {
            val res = Cloud.call("GET", "/c/$coll/${r.id}/related/${rel.s("name")}", null, Auth.token())
            rows = if (res.ok) arrList(res.body.optJSONArray("rows")) else emptyList()
        }
        Column(Modifier.padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            val list = rows
            SectionHeader(T(rel.s("label")) + if (!list.isNullOrEmpty()) " (${list.size})" else "",
                action = if (Db.mayCreate(kid)) Strings.add else "") { adding = !adding }
            list?.take(30)?.forEach { k ->
                val fs = Db.fields(kid).filter { it.s("key") != rel.s("field") && k.has(it.s("key")) && it.s("type") != "photo" }
                ListRow(Logic.title(kid, k), sub = fs.drop(1).take(3).joinToString(" · ") { T(it.s("label")) + ": " + Logic.show(k, it) },
                    chevron = false, trailing = k.s("status"))
            }
            if (adding) AutoForm(kid, mapOf(rel.s("field") to r.id)) { adding = false; tick++ ; Db.kick() }
        }
    }
}

/** Every field of a list as a form (text, number, date, choice, yes / no, link) - for the lists no screen was drawn for.
 *  Formula and workflow fields are the server's: never in a form. `preset` = fields already decided (the parent link). */
@Composable
fun AutoForm(coll: String, preset: Map<String, String> = emptyMap(), onDone: () -> Unit = {}) {
    val c = ctx()
    val vals = remember(coll, preset.toString()) { mutableStateMapOf<String, String>().also { it.putAll(preset) } }
    val fields = Db.fields(coll).filter { f ->
        !f.b("computed") && !f.b("workflow") && f.s("key") !in preset && (!f.b("admin_only") || Auth.isStaff) &&
            f.s("type") in listOf("text", "long_text", "number", "phone", "email", "date", "choice", "yes_no", "ref")
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        fields.forEach { f ->
            val k = f.s("key")
            val label = T(f.s("label")) + if (f.b("required")) " *" else ""
            when (f.s("type")) {
                "ref" -> RefField(label, k, f.s("to"), vals)
                "choice" -> {
                    Small(label)
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        f.strings("options").forEach { o -> Chip(T(o), selected = (vals[k] ?: f.s("default")) == o) { vals[k] = o } }
                    }
                }
                "yes_no" -> Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Chip(label, selected = vals[k] == "true") { vals[k] = if (vals[k] == "true") "false" else "true" }
                }
                else -> OutlinedTextField(value = vals[k] ?: "", onValueChange = { vals[k] = it.take(if (f.s("type") == "long_text") 4000 else 300) },
                    label = { Text(label) }, modifier = Modifier.fillMaxWidth(), singleLine = f.s("type") != "long_text",
                    placeholder = { if (f.s("type") == "date") Text("YYYY-MM-DD") },
                    keyboardOptions = KeyboardOptions(keyboardType = when (f.s("type")) {
                        "number" -> KeyboardType.Decimal; "phone" -> KeyboardType.Phone; "email" -> KeyboardType.Email; else -> KeyboardType.Text }))
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Btn(Strings.save, small = true) {
                val miss = fields.firstOrNull { it.b("required") && (vals[it.s("key")] ?: "").isBlank() }
                if (miss != null) { Act.toast(c, T(miss.s("label")) + ": " + Strings.required); return@Btn }
                val data = vals.filterValues { it.isNotBlank() }.mapValues { it.value.trim() as Any? }
                val show = data.toMutableMap()
                fields.filter { it.s("type") == "ref" }.forEach { f -> show[f.s("key")] = data[f.s("key")] }
                Db.create(coll, data, show)
                onDone()
            }
            Btn(Strings.cancel, kind = BtnKind.Ghost, small = true) { onDone() }
        }
    }
}

/** Kit screen "hoola_approvals": what waits for this account's decision (+ what this account asked for). */
@Composable
fun ApprovalsScreen() {
    if (!Auth.signedIn) {
        Page(Strings.approvals) { block { Small(Strings.loginFirst) } }
        return
    }
    var items by remember { mutableStateOf<List<Item>?>(null) }
    var tick by remember { mutableStateOf(0) }
    LaunchedEffect(Auth.me.value, tick) {
        val r = Cloud.call("GET", "/approvals", null, Auth.token())
        items = if (r.ok) arrList(r.body.optJSONArray("approvals")) else emptyList()
    }
    Page(Strings.approvals) {
        val list = items
        if (list == null) block { Small(Strings.loading) }
        else if (list.isEmpty()) block { Empty("check", Strings.noApprovals) }
        list?.forEach { a -> block { ApprovalCard(a) { tick++ } } }
    }
}

@Composable
private fun ApprovalCard(a: Item, onDone: () -> Unit) {
    val c = ctx()
    val scope = rememberCoroutineScope()
    HCard {
        Title(a.s("title").ifEmpty { T(a.s("label")) })
        Small(T(a.s("label")) + ": " + T(a.s("from")) + " → " + T(a.s("to")) + " · " + Strings.step + " " + a.i("step") + "/" + a.i("of"))
        if (a.s("maker").isNotEmpty()) Small(Strings.askedBy + ": " + a.s("maker"))
        if (a.s("waiting_for").isNotEmpty()) Pill(Strings.waitingFor + ": " + T(a.s("waiting_for")), "warn")
        a.list("decisions").forEach { d -> Small("✓ " + d.s("by") + " · " + d.s("decision") + (if (d.s("note").isNotEmpty()) " · " + d.s("note") else "")) }
        if (a.b("can_decide")) {
            var note by remember(a.id) { mutableStateOf("") }
            var busy by remember(a.id) { mutableStateOf(false) }
            OutlinedTextField(value = note, onValueChange = { note = it.take(300) }, modifier = Modifier.fillMaxWidth(),
                placeholder = { Text(Strings.note) }, maxLines = 2)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("approve" to Strings.approve, "reject" to Strings.reject).forEach { (d, label) ->
                    Btn(label, kind = if (d == "approve") BtnKind.Primary else BtnKind.Danger, small = true, enabled = !busy) {
                        busy = true
                        scope.launch {
                            val res = Cloud.call("POST", "/approvals/" + a.id, JSONObject().put("decision", d).put("note", note.trim()), Auth.token())
                            busy = false
                            Act.toast(c, if (res.ok) res.body.optString("say", Strings.done) else res.error.ifEmpty { if (res.offline) Strings.offline else Strings.tryAgain })
                            onDone()
                        }
                    }
                }
            }
        }
    }
}

/** Kit screen "hoola_data" (staff): every list of the app - rows + Add as a form. A list her logic added later
 *  works here at once, before any screen is redrawn for it. */
@Composable
fun DataScreen() {
    if (!Auth.signedIn || !Auth.isStaff) {
        Page(Strings.allLists) { block { Small(Strings.staffOnly) } }
        return
    }
    var open by remember { mutableStateOf("") }
    var adding by remember { mutableStateOf(false) }
    Page(if (open.isEmpty()) Strings.allLists else T(Db.label(open))) {
        if (open.isEmpty()) {
            Db.collections().forEach { coll ->
                block { ListRow(T(Db.label(coll)), sub = Db.fields(coll).take(4).joinToString(", ") { T(it.s("label")) }) { open = coll; adding = false } }
            }
        } else {
            block {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Btn(Strings.back, kind = BtnKind.Ghost, small = true) { open = ""; adding = false }
                    if (Db.mayCreate(open)) Btn(Strings.add, small = true) { adding = !adding }
                }
            }
            if (adding) block { AutoForm(open) { adding = false } }
            block { LiveRowsBlock(open) }
        }
    }
}
