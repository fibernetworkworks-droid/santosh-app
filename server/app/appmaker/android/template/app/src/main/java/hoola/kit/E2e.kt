package hoola.kit

// Made by Hoola App Sahayak (v0.314). Debug builds only (MainActivity starts it only when BuildConfig.DEBUG and the
// extra hoola_e2e is set): Hoola's emulator test drives the REAL kit against a real Hoola server - create an account,
// put the first product in the cart, place the order through the outbox, and check the server's copy (priced by the
// server, sent exactly once even when the same write goes twice). The result is one logcat line: HOOLA_E2E OK | FAIL.

import android.content.Context
import android.util.Log
import kotlinx.coroutines.delay
import org.json.JSONObject

object E2e {
    private fun say(line: String) { Log.i("HOOLA_E2E", line) }

    suspend fun run(ctx: Context) {
        try {
            val why = steps(ctx)
            say(if (why == null) "HOOLA_E2E OK" else "HOOLA_E2E FAIL $why")
        } catch (e: Exception) {
            say("HOOLA_E2E FAIL crash ${e.javaClass.simpleName}: ${e.message}")
        }
    }

    private suspend fun steps(ctx: Context): String? {
        if (!Cloud.ready) return "cloud not ready"
        val email = "e2e${System.currentTimeMillis()}@example.com"
        Auth.signup(ctx, email, "hoola-e2e-pass", "E2E Tester")?.let { return "signup: $it" }
        if (!Auth.signedIn) return "not signed in after signup"
        say("signed up $email")
        val order = Db.orderList
        if (order.isEmpty()) return "no order list in the backend"
        val first = AppData.list("products").firstOrNull() ?: return "no products"
        AppState.cart.clear()
        AppState.add(first.id, 2)
        AppState.form["name"] = "E2E Tester"
        AppState.form["phone"] = "9876543210"
        AppState.form["address"] = "12 Test Road, Pune"
        Db.submit(order)?.let { return "submit: $it" }
        if (Db.pending.value < 1) return "order did not go into the outbox"
        var tries = 0
        while (Db.pending.value > 0 && tries < 20) { Db.sync(); delay(500); tries++ }
        if (Db.pending.value > 0) return "outbox not sent: ${Db.lastError.value}"
        if (!Db.refresh(order)) return "refresh failed"
        val rows = Db.rows(order)
        val mine = rows.firstOrNull { !it.b("pending") } ?: return "order not on the server"
        val want = first.price * 2
        if (want > 0 && kotlin.math.abs(mine.n("total") - want) > 0.01) return "total ${mine.n("total")} != $want"
        say("order ${mine.id} total ${mine.n("total")} status ${mine.s("status")}")
        // the same write twice (a retry after a lost answer) must give the same row
        val body = JSONObject().put("cid", "e2eDedup${System.currentTimeMillis()}").put("name", "E2E Tester").put("phone", "9876543210")
            .put("cart", org.json.JSONArray().put(JSONObject().put("id", first.id).put("qty", 1)))
        val a = Cloud.call("POST", "/c/$order", JSONObject(body.toString()), Auth.token())
        val b = Cloud.call("POST", "/c/$order", JSONObject(body.toString()), Auth.token())
        if (!a.ok || !b.ok) return "dedup calls failed ${a.code} ${b.code}"
        if (a.body.optString("id") != b.body.optString("id")) return "same write made two rows"
        say("dedup ok ${a.body.optString("id")}")
        // the account screen's data path: a signed-out user sees nothing private
        val before = Db.rows(order).size
        Auth.logout(ctx)
        if (Db.rows(order).isNotEmpty()) return "rows stayed after sign out ($before before)"
        Auth.login(ctx, email, "hoola-e2e-pass")?.let { return "login: $it" }
        if (!Db.refresh(order) || Db.rows(order).size < 2) return "rows after login: ${Db.rows(order).size}"
        say("login again ok, ${Db.rows(order).size} orders")
        return null
    }
}
