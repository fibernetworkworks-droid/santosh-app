package hoola.kit

// Made by Hoola App Sahayak (v0.419 PAISA). Online payment through the business's OWN gateway (Razorpay / Cashfree /
// PhonePe), only when the business joined one. "Pay online" asks the server to start a payment for the SERVER's total,
// then opens the gateway's own secure page in the browser. This app never sees a card, UPI PIN or bank detail, and it
// never decides that an order is paid: the server marks it paid only when the GATEWAY says so (its signed message or the
// server's own check), and the live stream / next refresh shows "Verified" here. AutoPay plans: the customer starts one
// and approves the mandate on the gateway's page; she can cancel any time from this app.

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject

object Pay {
    private fun cfg(): JSONObject? = AppData.backend().optJSONObject("pay")?.takeIf { it.optBoolean("on") }
    val on: Boolean get() = cfg() != null
    val plansOn: Boolean get() = cfg()?.optBoolean("plans") == true

    /** Starts a payment for this order on the server and opens the gateway's page. null = opened; else what went wrong. */
    suspend fun start(ctx: android.content.Context, coll: String, id: String): String? {
        val r = Cloud.call("POST", "/pay/c/$coll/$id/start", JSONObject(), Auth.token())
        if (!r.ok) return r.error.ifEmpty { if (r.offline) Strings.offline else Strings.tryAgain }
        val path = r.body.optString("path")
        if (path.isEmpty() || !Act.open(ctx, Cloud.baseUrl + path)) return Strings.tryAgain
        return null
    }
}

/** On the customer's own unpaid order: "Pay online" (the gateway's page), then waits for the gateway's word. */
@Composable
fun PayButton(coll: String, r: Item) {
    if (!Pay.on || Auth.isStaff || coll != Db.orderList || r.b("pending")) return
    if (r.s("paid", "No") == "Verified" || r.s("status") in setOf("Cancelled", "Rejected") || r.n("total") < 1) return
    val c = ctx()
    val scope = rememberCoroutineScope()
    var busy by remember(r.id) { mutableStateOf(false) }
    var waiting by remember(r.id) { mutableStateOf(false) }
    LaunchedEffect(waiting) {                                   // after the page opened: a few checks (live also tells us)
        if (!waiting) return@LaunchedEffect
        repeat(20) {
            delay(6000)
            val s = Cloud.call("GET", "/pay/c/$coll/${r.id}", null, Auth.token())
            if (s.ok && s.body.optBoolean("paid")) { Db.refresh(coll); waiting = false; return@LaunchedEffect }
        }
        waiting = false
    }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Btn(if (busy) Strings.opening else Strings.payOnline + " " + rupees(r.n("total")), kind = BtnKind.Primary, icon = "pay",
            small = true, enabled = !busy) {
            busy = true
            scope.launch {
                val err = Pay.start(c, coll, r.id)
                busy = false
                if (err != null) Act.toast(c, err) else waiting = true
            }
        }
        if (waiting) Small(Strings.payWaiting)
    }
}

/** AutoPay plans the business offers + this customer's own subscriptions with Cancel. Nothing when there are none. */
@Composable
fun PlansBlock() {
    if (!Pay.plansOn || !Auth.signedIn || Auth.isStaff) return
    val c = ctx()
    val scope = rememberCoroutineScope()
    var plans by remember { mutableStateOf<List<Item>>(emptyList()) }
    var subs by remember { mutableStateOf<List<Item>>(emptyList()) }
    var tick by remember { mutableStateOf(0) }
    LaunchedEffect(tick, Auth.me.value) {
        val p = Cloud.call("GET", "/pay/plans", null, Auth.token())
        if (p.ok) plans = arrList(p.body.optJSONArray("plans"))
        val s = Cloud.call("GET", "/pay/subs", null, Auth.token())
        if (s.ok) subs = arrList(s.body.optJSONArray("subs"))
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Title(Strings.autoPay)
        subs.filter { it.s("status") !in setOf("cancelled", "completed", "created") }.forEach { s ->
            HCard {
                Body(s.s("plan") + " · " + s.s("amount_rs") + " / " + T(s.s("period")))
                Small(Strings.autoPayOn + " · " + s.i("charges") + " " + Strings.charged)
                Btn(Strings.cancelAutoPay, kind = BtnKind.Outline, small = true) {
                    scope.launch {
                        val r = Cloud.call("POST", "/pay/subs/${s.s("id")}/cancel", JSONObject(), Auth.token())
                        Act.toast(c, if (r.ok) Strings.autoPayOff else r.error.ifEmpty { Strings.tryAgain })
                        tick += 1
                    }
                }
            }
        }
        plans.forEach { p ->
            HCard {
                Body(p.s("name") + " · " + p.s("amount_rs") + " / " + T(p.s("period")))
                Small(Strings.autoPayWhy.replace("{n}", p.i("count").toString()))
                Btn(Strings.startAutoPay, kind = BtnKind.Tonal, small = true, modifier = Modifier.fillMaxWidth()) {
                    scope.launch {
                        val r = Cloud.call("POST", "/pay/plans/${p.s("key")}/subscribe", JSONObject(), Auth.token())
                        val path = r.body.optString("path")
                        if (!r.ok || path.isEmpty()) Act.toast(c, r.error.ifEmpty { Strings.tryAgain })
                        else Act.open(c, Cloud.baseUrl + path)
                        tick += 1
                    }
                }
            }
        }
    }
}
