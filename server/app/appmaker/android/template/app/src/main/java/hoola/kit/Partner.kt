package hoola.kit

// Made by Hoola App Sahayak (v0.435 PARIVAAR). The jobs screen of a delivery partner (rider) app or a partner shop app.
// Everything it shows comes from the server (/partner/jobs): which jobs this account may see, how much of each (a shop
// never gets the customer's phone), which steps are allowed now and whether a job can still be taken. This screen only
// shows that and sends the taps; the server checks every tap again.

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.json.JSONObject

object Partner {
    /** "rider" / "vendor" in a partner app's build, "" in every other app. */
    val kind: String get() = AppData.backend().optString("partner", "")
    val on: Boolean get() = kind.isNotEmpty()
}

@Composable
fun PartnerScreen() {
    Page(Strings.ptJobs, back = false) {
        block { PartnerJobsBlock() }
    }
}

@Composable
fun PartnerJobsBlock() {
    val c = ctx()
    val nav = LocalNav.current
    val scope = rememberCoroutineScope()
    var data by remember { mutableStateOf<Item?>(null) }
    var busy by remember { mutableStateOf("") }
    var tick by remember { mutableIntStateOf(0) }
    val me = Auth.me.value
    LaunchedEffect(me?.id, tick) {
        val r = Cloud.call("GET", "/partner/jobs", null, Auth.token())
        data = if (r.ok) Item(r.body)
        else Item(JSONObject().put("state", "error").put("error", if (r.offline) Strings.offline else r.error.ifEmpty { Strings.tryAgain }))
    }
    val d = data
    val send: (String, String, JSONObject) -> Unit = { id, path, body ->
        busy = id
        scope.launch {
            val r = Cloud.call("POST", path, body, Auth.token())
            busy = ""
            if (!r.ok) Act.toast(c, r.error.ifEmpty { if (r.offline) Strings.offline else Strings.tryAgain })
            tick++
        }
    }
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        val state = d?.s("state") ?: ""
        when {
            d == null -> Small(Strings.loading)
            me == null || state == "login" ->
                Empty("user", Strings.notSignedIn, Strings.ptLoginWhy, Strings.login) { nav.go(SCREEN_LOGIN) }
            state == "error" -> Empty("bell", d.s("error"), "", Strings.ptRetry) { tick++ }
            state == "waiting" -> Empty("clock", Strings.ptWaiting, Strings.ptWaitingWhy, Strings.ptRefresh) { tick++ }
            state != "active" -> Empty("truck", Strings.ptApply, Strings.ptApplyWhy, if (d.b("can_request")) Strings.ptApplyBtn else "") {
                send("apply", "/partner/request", JSONObject())
            }
            else -> {
                if (d.s("shop").isNotEmpty()) Title(d.s("shop"))
                if (d.s("kind") == "rider") ShiftBlock()
                val mine = d.list("mine")
                SectionHeader(Strings.ptMine + " (" + mine.size + ")", Strings.ptRefresh) { tick++ }
                if (mine.isEmpty()) Small(Strings.ptNone)
                mine.forEach { j -> JobCard(j, busy, send) }
                if (d.s("kind") == "rider") {
                    val offers = d.list("offers")
                    SectionHeader(Strings.ptNew + " (" + offers.size + ")")
                    if (offers.isEmpty()) Small(Strings.ptNoOffers)
                    offers.forEach { j -> JobCard(j, busy, send) }
                }
                val done = d.list("done")
                if (done.isNotEmpty()) {
                    SectionHeader(Strings.ptPast)
                    done.take(10).forEach { j -> ListRow(j.s("title"), j.s("status"), chevron = false) }
                }
            }
        }
    }
}

@Composable
private fun JobCard(j: Item, busy: String, send: (String, String, JSONObject) -> Unit) {
    val c = ctx()
    HCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Title(j.s("title"), Modifier.weight(1f))
            if (j.s("status").isNotEmpty()) Pill(T(j.s("status")))
        }
        j.strings("lines").forEach { Small(it) }
        Row(Modifier.horizontalScroll(rememberScrollState()).padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (j.b("take")) {
                Btn(if (busy == j.id) Strings.opening else Strings.ptTake, small = true, enabled = busy.isEmpty()) {
                    send(j.id, "/partner/jobs/" + j.id + "/take", JSONObject())
                }
            }
            j.strings("steps").forEach { st ->
                Btn(T(st), kind = BtnKind.Tonal, small = true, enabled = busy.isEmpty()) {
                    send(j.id, "/partner/jobs/" + j.id + "/step", JSONObject().put("status", st))
                }
            }
            if (j.s("phone").isNotEmpty()) {
                Btn(Strings.call, kind = BtnKind.Outline, small = true) { Act.call(c, j.s("phone")) }
            }
            if (j.has("lat") && j.has("lng")) {
                Btn(Strings.ptRoute, kind = BtnKind.Outline, small = true) {
                    Act.link(c, "https://www.google.com/maps/dir/?api=1&destination=" + j.n("lat") + "," + j.n("lng"))
                }
            } else if (j.s("address").isNotEmpty()) {
                Btn(Strings.ptRoute, kind = BtnKind.Outline, small = true) { Act.maps(c, j.s("address")) }
            }
        }
    }
}
