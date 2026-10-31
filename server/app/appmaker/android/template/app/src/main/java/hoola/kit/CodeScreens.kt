package hoola.kit

// Made by Hoola App Sahayak. Screens written by code, never by the model: splash, DPDP consent (unticked box,
// Continue disabled until ticked), notification explainer, seller details + grievance officer (E-Commerce Rules 2020),
// privacy policy and in-app account deletion (both stores require it; v0.314 it really deletes on the server).

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun SplashScreen(onDone: () -> Unit) {
    val c = H.c
    LaunchedEffect(Unit) { delay(900); onDone() }
    Box(Modifier.fillMaxSize().background(Brush.linearGradient(listOf(c.primary, c.accent))), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Box(Modifier.size(88.dp).background(c.onPrimary.copy(alpha = 0.18f), RoundedCornerShape(24.dp)), contentAlignment = Alignment.Center) {
                Text(AppData.appName.take(1).uppercase(), style = H.t.display.copy(color = c.onPrimary))
            }
            Text(AppData.appName, style = H.t.h1.copy(color = c.onPrimary), textAlign = TextAlign.Center)
            val tag = AppData.facts.s("tagline")
            if (tag.isNotEmpty()) Text(tag, style = H.t.body.copy(color = c.onPrimary.copy(alpha = 0.9f)), textAlign = TextAlign.Center)
        }
    }
}

@Composable
fun ConsentScreen(onDone: () -> Unit) {
    Page(Strings.consentTitle, back = false, large = true, bottomBar = {
        Btn(Strings.cont, modifier = Modifier.weight(1f), enabled = AppState.form["consent"] == "1") { AppState.consent.value = true; onDone() }
    }) {
        block { Body(Strings.consentWhat) }
        block { HCard { KeyValues(listOf(Strings.name to AppData.appName, Strings.phone to AppData.facts.s("phone", "-"), Strings.email to AppData.facts.s("email", "-"))) } }
        block { CheckRow(Strings.agree, "consent") }
    }
}

@Composable
fun NotifyScreen(onDone: () -> Unit) {
    Page(Strings.notifyTitle, back = false, large = true, bottomBar = {
        Btn(Strings.later, modifier = Modifier.weight(1f), kind = BtnKind.Ghost) { onDone() }
        Btn(Strings.cont, modifier = Modifier.weight(1f)) { onDone() }
    }) {
        block { Center { Box(Modifier.size(96.dp).background(H.c.tint, RoundedCornerShape(28.dp)), contentAlignment = Alignment.Center) { HIcon("bell", size = 44.dp, tint = H.c.primaryText) } } }
        block { Body(Strings.notifyWhy) }
    }
}

@Composable
fun SellerScreen() {
    val f = AppData.facts
    Page(Strings.seller) {
        block {
            HCard {
                KeyValues(listOf(
                    Strings.name to f.s("legal_name", f.s("name", "-")),
                    Strings.address to f.s("address", "-"),
                    Strings.phone to f.s("phone", "-"),
                    Strings.email to f.s("email", "-"),
                    "GSTIN" to f.s("gstin", "-"),
                ))
            }
        }
        block { H2(Strings.grievance) }
        block {
            HCard {
                KeyValues(listOf(Strings.name to f.s("grievance_name", f.s("owner", "-")), Strings.phone to f.s("grievance_phone", f.s("phone", "-")),
                    Strings.email to f.s("grievance_email", f.s("email", "-"))))
                Small(Strings.grievanceNote)
            }
        }
    }
}

@Composable
fun PrivacyScreen() {
    val paras = AppData.facts.strings("privacy")
    Page(Strings.privacy) {
        paras.forEach { p -> block { if (p.startsWith("# ")) H2(p.removePrefix("# ")) else Body(p) } }
        val url = AppData.facts.s("privacy_url")
        if (url.isNotEmpty()) block { Small(url) }
    }
}

@Composable
fun DeleteAccountScreen() {
    val context = ctx()
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    Page(Strings.deleteTitle) {
        block { Body(Strings.deleteWhat) }
        block {
            Btn(if (busy) Strings.deleting else Strings.deleteYes, kind = BtnKind.Danger, enabled = !busy,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
                AppState.form.clear(); AppState.cart.clear()
                if (!Auth.signedIn) {
                    Store.put(context, "delete_requested", "1")
                    Act.toast(context, Strings.deleteDone)
                } else {
                    // v0.314 the server removes the account and everything it made, then the phone forgets it too
                    busy = true
                    scope.launch {
                        val e = Auth.deleteAccount(context)
                        busy = false
                        Act.toast(context, e ?: Strings.deleteDone)
                    }
                }
            }
        }
    }
}
