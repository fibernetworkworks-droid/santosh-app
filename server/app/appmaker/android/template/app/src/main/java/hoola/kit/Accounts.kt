package hoola.kit

// Made by Hoola App Sahayak (v0.314 ASLI APP). Written by code, never by the model: sign in / create account (the only
// password box in the app, sent once over https and never stored), and My account: the user's own orders / bookings with
// their live status, writes still on their way, sign out. A staff account sees everyone's rows and moves their status.

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
private fun PasswordBox(value: String, onChange: (String) -> Unit) {
    val c = H.c
    OutlinedTextField(
        value = value,
        onValueChange = { onChange(it.take(128)) },
        label = { Text(Strings.password) },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        shape = RoundedCornerShape(H.look.radius * 0.7f),
        colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = c.primary, unfocusedBorderColor = c.line, focusedLabelColor = c.primaryText),
    )
}

@Composable
fun AuthScreen() {
    val nav = LocalNav.current
    val c = ctx()
    val scope = rememberCoroutineScope()
    var signup by remember { mutableStateOf(Db.signupOpen && Store.get(c, "ever_signed_in") != "1") }
    var busy by remember { mutableStateOf(false) }
    var err by remember { mutableStateOf("") }
    var pw by remember { mutableStateOf("") }
    Page(if (signup) Strings.signupTitle else Strings.loginTitle, bottomBar = {
        Btn(if (busy) Strings.sending else if (signup) Strings.signup else Strings.login, modifier = Modifier.weight(1f), enabled = !busy) {
            busy = true
            err = ""
            scope.launch {
                val email = AppState.form["auth_email"] ?: ""
                val e = if (signup) Auth.signup(c, email, pw, AppState.form["auth_name"] ?: "") else Auth.login(c, email, pw)
                busy = false
                if (e == null) {
                    pw = ""
                    Store.put(c, "ever_signed_in", "1")
                    if (!nav.back()) nav.go(SCREEN_ACCOUNT)
                } else err = e
            }
        }
    }) {
        block { Body(if (signup) Strings.signupWhy else Strings.loginWhy) }
        if (signup) block { Field(Strings.name, "auth_name") }
        block { Field(Strings.email, "auth_email", keyboard = KeyboardType.Email) }
        block { PasswordBox(pw) { pw = it } }
        if (err.isNotEmpty()) block { Pill(err, "bad") }
        if (Db.signupOpen) block {
            Btn(if (signup) Strings.haveAccount else Strings.newHere, kind = BtnKind.Ghost, small = true) { signup = !signup; err = "" }
        }
    }
}

private val DONE = setOf("Delivered", "Done", "Confirmed", "Active", "Enrolled", "Replied", "Closed", "Registered")
private val BAD = setOf("Cancelled", "Expired")

private fun statusKind(s: String): String = when (s) {
    in DONE -> "ok"
    in BAD -> "bad"
    else -> "info"
}

@Composable
fun AccountScreen() {
    val nav = LocalNav.current
    val c = ctx()
    val me = Auth.me.value
    Page(Strings.account) {
        if (me == null) {
            block { Empty("user", Strings.notSignedIn, Strings.loginWhy, Strings.login) { nav.go(SCREEN_LOGIN) } }
        } else {
            block {
                HCard {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Avatar(Auth.name)
                        Column {
                            Title(Auth.name)
                            Small(me.s("email") + if (Auth.isStaff) " · " + Strings.staff else "")
                        }
                    }
                }
            }
        }
        if (me != null) block {                                   // v0.340 the updates inbox (order moved, new orders)
            val n = Inbox.unread.value
            Btn(Strings.inbox + if (n > 0) " ($n)" else "", kind = BtnKind.Tonal, icon = "bell", modifier = Modifier.fillMaxWidth()) { nav.go("hoola_inbox") }
        }
        if (me != null) block {                                   // v0.378 BAAT: chat with the shop / customers' messages
            Btn(if (Auth.isStaff) Strings.customerMessages else Strings.chat, kind = BtnKind.Tonal, icon = "chat",
                modifier = Modifier.fillMaxWidth()) { nav.go("hoola_chat") }
        }
        if (me != null && Auth.isStaff && Db.approvalsOn) block {   // v0.382 DIMAAG: approvals waiting for this account
            Btn(Strings.approvals, kind = BtnKind.Tonal, icon = "check", modifier = Modifier.fillMaxWidth()) { nav.go("hoola_approvals") }
        }
        if (me != null && Auth.isStaff) block {                   // v0.382 every list of the app (new lists work before a redesign)
            Btn(Strings.allLists, kind = BtnKind.Tonal, icon = "list", modifier = Modifier.fillMaxWidth()) { nav.go("hoola_data") }
        }
        if (me != null) block { KhataBlock() }                     // v0.359 udhaar: hers / who owes (staff)
        if (me != null && Auth.isStaff) block { StatsBlock() }     // v0.340 the staff dashboard
        if (me != null && Auth.isStaff) block { StopsBlock() }     // v0.350 the open stops with a location, nearest first
        if (me != null && Auth.isStaff && Track.on) block { ShiftBlock() }   // v0.412 NAKSHA LIVE: Start / End shift
        if (me != null && !Auth.isStaff && Pay.plansOn) block { PlansBlock() }   // v0.419 AutoPay plans + her own, with Cancel
        if (me != null && Auth.isStaff && Track.on) block { RidersMap() }    // v0.412 every rider on shift, live
        block { LanguagePicker() }                                 // v0.347 the app's words in her language
        if (Db.pending.value > 0) block { Pill("${Db.pending.value} ${Strings.pending}", "warn") }
        if (Db.lastError.value.isNotEmpty()) block { Pill(Db.lastError.value, "bad") }
        Db.collections().forEach { coll ->
            val read = Db.rule(coll, "read")
            val visible = read == "public" || (me != null && (read != "admin" || Auth.isStaff))
            if (visible) block { RowsSection(coll) }
        }
        if (me != null) block {
            Btn(Strings.logout, kind = BtnKind.Ghost, modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) { Auth.logout(c) }
        }
    }
}

/** One of the app's server lists as cards: the user's own rows (a staff account: everyone's, with status chips). */
@Composable
fun LiveRowsBlock(coll: String) = RowsSection(coll)

@Composable
private fun RowsSection(coll: String) {
    val all = liveRows(coll)
    val fields = Db.fields(coll)
    // v0.319 search (any field) + a status filter, on the phone (works offline on the cached rows)
    var q by remember(coll) { mutableStateOf("") }
    var st by remember(coll) { mutableStateOf("") }
    val opts = fields.firstOrNull { it.s("key") == "status" }?.strings("options").orEmpty()
    // v0.352 My work: only the rows given to this staff account
    var mineOnly by remember(coll) { mutableStateOf(false) }
    val meId = Auth.me.value?.id ?: ""
    val anyMine = Auth.isStaff && all.any { it.s("assigned_to") == meId && meId.isNotEmpty() }
    val rows = all.filter { r -> (st.isEmpty() || r.s("status") == st) && (q.isBlank() || r.o.toString().lowercase().contains(q.trim().lowercase()))
        && (!mineOnly || r.s("assigned_to") == meId) }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SectionHeader(T(Db.label(coll)) + if (all.isNotEmpty()) " (${all.size})" else "")
        if (Auth.isStaff && Db.rule(coll, "read") == "own") Small(Strings.staffView)
        if (anyMine || mineOnly) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Chip(Strings.myWork, selected = mineOnly) { mineOnly = !mineOnly }
        }
        if (all.size > 4) {
            OutlinedTextField(value = q, onValueChange = { q = it.take(60) }, singleLine = true, modifier = Modifier.fillMaxWidth(),
                placeholder = { Text(Strings.search) }, shape = RoundedCornerShape(H.look.radius * 0.7f))
            if (opts.isNotEmpty()) Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Chip(Strings.all, selected = st.isEmpty()) { st = "" }
                opts.forEach { o -> Chip(T(o), selected = st == o) { st = if (st == o) "" else o } }
            }
        }
        if (rows.isEmpty()) Small(Strings.nothingYet)
        rows.take(60).forEach { r -> RowCard(coll, r, fields) }
    }
}

@Composable
private fun RowCard(coll: String, r: Item, fields: List<Item>) {
    val c = ctx()
    val head = fields.firstOrNull { it.s("type") in listOf("text", "long_text") && r.has(it.s("key")) && it.s("key") != "utr" }
    HCard {
        Title(if (Db.labelField(coll).isNotEmpty()) Logic.title(coll, r) else head?.let { r.s(it.s("key")) } ?: Db.label(coll), maxLines = 3)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            val status = r.s("status")
            if (r.b("pending")) Pill(Strings.sending, "warn") else if (status.isNotEmpty()) Pill(T(status), statusKind(status))
            val paid = r.s("paid")
            if (paid.isNotEmpty() && paid != "No") Pill(T(paid), if (paid == "Verified") "ok" else "warn")
            if (r.has("total") && r.n("total") > 0) Title(rupees(r.n("total")))
        }
        fields.filter { it.s("type") == "photo" && r.has(it.s("key")) }.take(2).forEach { f ->
            RemotePhoto(r.s(f.s("key")), Modifier.fillMaxWidth().padding(top = 6.dp), f.s("label"))
        }
        fields.filter { it !== head && it.s("key") !in listOf("status", "total", "paid") && it.s("type") != "photo" && r.has(it.s("key")) }
            .take(6).forEach { f ->
                if (f.s("type") == "location") {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Small(T(f.s("label")) + ": " + r.s(f.s("key")))
                        Btn(Strings.openMap, kind = BtnKind.Ghost, small = true) { Act.maps(c, r.s(f.s("key"))) }
                    }
                } else Small(T(f.s("label")) + ": " + Logic.show(r, f), maxLines = 4)     // v0.382 a link shows its row's name
            }
        // v0.319 the customer's own UPI order: pay to the business's UPI ID, then "I have paid" + the UPI reference
        if (!Auth.isStaff && coll == Db.orderList && !r.b("pending") && r.s("pay") == "UPI" && r.s("paid", "No") == "No"
            && r.s("status") != "Cancelled") {
            PaidBox(coll, r)
        }
        // v0.352 the customer sees the first name of the person on her row
        if (!Auth.isStaff && r.s("assigned_name").isNotEmpty()) Small(r.s("assigned_name") + " " + Strings.onIt)
        if (r.s("slot_label").isNotEmpty()) Small(Strings.pickSlot + ": " + r.s("slot_label"))      // v0.371 SLOT
        SlotChange(coll, r)                                                                       // v0.377 change the time
        if (r.s("delivery_note").isNotEmpty()) Small(r.s("delivery_note"), maxLines = 4)
        TrackButton(coll, r)                                      // v0.412 NAKSHA LIVE: the rider on a map while it is on its way
        PayButton(coll, r)                                        // v0.419 PAISA: pay online through the shop's own gateway
        RateBox(coll, r)                                          // v0.353 the customer rates her finished row once
        ReceiptButton(coll, r)                                    // v0.354 the receipt PDF of a finished row
        CreditButton(coll, r)                                     // v0.359 staff: this order on credit (udhaar)
        AssignBox(coll, r)
        if (Db.workflowField(coll).isNotEmpty()) {                // v0.382 DIMAAG: the server's workflow steps + approvals
            if (Team.mayWork(r)) WorkflowBox(coll, r)
        } else {
        val stf = fields.firstOrNull { it.s("key") == "status" }
        if (Auth.isStaff && stf != null && !r.b("pending") && Team.mayWork(r)) {
            Row(Modifier.horizontalScroll(rememberScrollState()).padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                stf.strings("options").forEach { opt ->
                    Chip(T(opt), selected = r.s("status") == opt) { if (r.s("status") != opt) Db.update(coll, r.id, mapOf("status" to opt)) }
                }
            }
        }
        }
        RelatedBlock(coll, r)                                     // v0.382 linked rows (items of an order...) + Add
    }
}
