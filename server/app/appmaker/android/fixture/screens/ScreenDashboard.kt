package hoola.app.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import hoola.kit.*

@Composable
fun ScreenDashboard() {
    val nav = LocalNav.current
    val orders = AppData.list("orders")
    Page("Dashboard", back = true) {
        block {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Kpi("₹48,200", "Today", Modifier.weight(1f))
                Kpi("37", "Orders", Modifier.weight(1f))
                Kpi("4.6", "Rating", Modifier.weight(1f))
            }
        }
        block { BarChart(listOf(3f, 5f, 2f, 8f, 6f, 9f, 4f), listOf("M", "T", "W", "T", "F", "S", "S")) }
        block { Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) { Ring(0.72f, "Target"); Meter(0.4f, Modifier.weight(1f)) } }
        block { Timeline(listOf("Placed" to true, "Packed" to true, "On the way" to false, "Delivered" to false), now = 1) }
        block { DataTable(listOf("Order", "Amount", "Status"), orders.map { listOf(it.name, rupees(it.price), it.s("status")) }) { i -> nav.open("home", "orders", orders[i].id) } }
        block { Kanban(listOf("New" to listOf("Lead 1", "Lead 2"), "Won" to listOf("Lead 3"))) }
        block { MapBox(listOf(0.2f to 0.3f, 0.5f to 0.6f, 0.8f to 0.4f), route = true, label = "Today's route") }
        block { Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { Avatar("Ravi Kumar"); Pill("Active", "ok"); Pill("Late", "warn") } }
        block { QrBox(seed = "member-42") }
        block { SwitchRow("Notify me", "notify", "Order updates only") }
        block { OtpBoxes() }
        block { ListRow("Settings", "Language, alerts", icon = "settings") { nav.go("profile") } }
        block { Blank("GSTIN") }
    }
}

