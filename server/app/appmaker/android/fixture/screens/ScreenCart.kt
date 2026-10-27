package hoola.app.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import hoola.kit.*

@Composable
fun ScreenCart() {
    val nav = LocalNav.current
    val c = ctx()
    val lines = AppState.cartItems("products")
    val total = AppState.cartTotal("products")
    Page("Cart", back = false, bottomBar = {
        Column(Modifier.weight(1f)) {
            Small("Total")
            Price(total, big = true)
        }
        Btn("Pay ${rupees(total)}", enabled = total > 0, icon = "pay") { Act.payUpi(c, total, "Order from app") }
    }) {
        if (lines.isEmpty()) {
            block { Empty("cart", "Your cart is empty", "Add something you like", "Shop now") { nav.go("home") } }
        }
        lines.forEach { (p, q) ->
            block {
                HCard {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Title(p.name)
                            Price(p.price * q)
                        }
                        Stepper(q) { AppState.setQty(p.id, it) }
                    }
                }
            }
        }
        block { HDivider() }
        block { KeyValues(listOf("Items" to "${AppState.cartCount}", "Delivery" to "Free", "To pay" to rupees(total))) }
        block { Field("Delivery address", "address", lines = 3, hint = "House, street, area") }
        block { CheckRow("Leave at the door", "door") }
        block { Segmented(listOf("UPI", "Cash on delivery"), "paymode") }
    }
}
