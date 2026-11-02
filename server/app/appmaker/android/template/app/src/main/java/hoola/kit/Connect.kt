package hoola.kit

// Made by Hoola App Sahayak (v0.424 JODO). Staff buttons for the business's own connectors (courier booking, tracking,
// an SMS...): only the actions the owner APPROVED and allowed staff to run, on that action's list. The server does the
// call with her sealed keys - this app never holds a courier / SMS / accounts key - and writes the answer back into the
// row's own fields, which the list then shows.

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.json.JSONObject

object Connectors {
    fun forList(coll: String): List<Item> = arrList(AppData.backend().optJSONArray("connect")).filter { it.s("coll") == coll }
}

@Composable
fun ConnectButtons(coll: String, r: Item) {
    if (!Auth.isStaff || r.b("pending")) return
    val acts = Connectors.forList(coll)
    if (acts.isEmpty()) return
    val c = ctx()
    val scope = rememberCoroutineScope()
    var busy by remember(r.id) { mutableStateOf("") }
    Row(Modifier.horizontalScroll(rememberScrollState()).padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        acts.forEach { a ->
            Btn(if (busy == a.s("key")) Strings.opening else T(a.s("label")), kind = BtnKind.Outline, small = true, enabled = busy.isEmpty()) {
                busy = a.s("key")
                scope.launch {
                    val res = Cloud.call("POST", "/connect/${a.s("key")}/run", JSONObject().put("row", r.id), Auth.token())
                    busy = ""
                    val st = res.body.optString("status")
                    Act.toast(c, if (res.ok && st == "ok") Strings.connDone else res.error.ifEmpty { Strings.tryAgain + if (st.isNotEmpty()) " ($st)" else "" })
                    if (res.ok) Db.refresh(coll)
                }
            }
        }
    }
}
