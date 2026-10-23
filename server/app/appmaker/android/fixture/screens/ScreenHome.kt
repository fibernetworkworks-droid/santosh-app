package hoola.app.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import hoola.kit.*

@Composable
fun ScreenHome() {
    val nav = LocalNav.current
    val c = ctx()
    var cat by remember { mutableStateOf("") }
    val items = AppData.list("products").filter { cat.isEmpty() || it.s("category") == cat }
    Page(AppData.appName, back = false, large = true, subtitle = AppData.facts.s("tagline"), actions = {
        IconBtn("cart", "Cart", badge = AppState.cartCount) { nav.go("cart") }
    }) {
        block { SearchBox() }
        block { Banner("Fresh today", "Free delivery above ₹499", "Order now") { nav.go("cart") } }
        block { SectionHeader("Categories") }
        block { Chips(AppData.categories("products"), "cat") { cat = it } }
        block { SectionHeader("Best sellers", "See all") { nav.go("categories") } }
        block {
            Rail(items.take(6)) { p ->
                HCard(onClick = { nav.open("product", "products", p.id) }) {
                    Ph("bag", ratio = 1.2f)
                    Title(p.name)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Price(p.price)
                        AddButton(p.id)
                    }
                }
            }
        }
        block {
            Grid(items, columns = 2) { p ->
                HCard(onClick = { nav.open("product", "products", p.id) }) {
                    Ph("package", variant = 1)
                    Title(p.name)
                    Small(p.s("unit"))
                    Price(p.price, old = p.price * 1.1)
                }
            }
        }
        block {
            HCard(tint = true) {
                Column(Modifier.padding(4.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    H2("Need help?")
                    FactText("hours", "opening hours")
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Btn("Call", kind = BtnKind.Tonal, icon = "phone", small = true) { Act.call(c) }
                        Btn("WhatsApp", kind = BtnKind.Outline, icon = "chat", small = true) { Act.whatsapp(c, "Hello") }
                    }
                }
            }
        }
    }
}
