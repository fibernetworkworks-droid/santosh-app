package hoola.app.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
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
        OrderBtn("Place order")
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
        block { Field("Name", "name") }
        block { Field("Mobile number", "phone", keyboard = KeyboardType.Phone) }
        block { Field("Delivery address", "address", lines = 3, hint = "House, street, area") }
        block { CheckRow("Leave at the door", "door") }
        block { Chips(listOf("Cash on delivery", "UPI"), "pay") }
        if (AppState.picks["pay"] == "UPI" && total > 0) block {
            Btn("Pay ${rupees(total)} by UPI", kind = BtnKind.Tonal, icon = "pay") { Act.payUpi(c, total, "Order from app") }
        }
        block { Btn(if (Auth.signedIn) "My orders" else "Sign in", kind = BtnKind.Ghost) { nav.go(if (Auth.signedIn) "hoola_account" else "hoola_login") } }
    }
}
