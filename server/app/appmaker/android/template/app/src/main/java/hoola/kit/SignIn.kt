package hoola.kit

// Made by Hoola App Sahayak (v0.453 SURAKSHIT LOGIN). The ways into the app and the user's own security page.
//
// The OTP box is the app's OWN box: the 6 digits go straight to this app's server and are never stored here, shown
// again or written to a log. Google / Apple give the app an ID token, and the SERVER checks its signature, audience
// and the single-use nonce before any account exists - the phone's word is never enough. A staff account with 2FA on
// finishes at the authenticator code.

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import kotlinx.coroutines.launch
import org.json.JSONObject

object Ways {
    private fun sign(): JSONObject = AppData.backend().optJSONObject("sign") ?: JSONObject()
    private fun list(): List<String> {
        val a = sign().optJSONArray("ways") ?: return listOf("email_password")
        return (0 until a.length()).map { a.optString(it) }
    }
    val otp: Boolean get() = list().contains("phone_otp")
    val google: Boolean get() = list().contains("google")
    val apple: Boolean get() = list().contains("apple")
    val password: Boolean get() = list().contains("email_password") || list().isEmpty()
    val serverClientId: String get() = sign().optString("google_server_client_id", "")
    val consentNeeded: Boolean get() = sign().optBoolean("consent", true)
}

/** The whole sign-in screen: whichever ways she turned on, plus the second step when a staff account needs it. */
@Composable
fun SignInScreen() {
    val nav = LocalNav.current
    val c = ctx()
    val scope = rememberCoroutineScope()
    var step by remember { mutableStateOf(if (Ways.otp) "otp" else "password") }
    var busy by remember { mutableStateOf(false) }
    var err by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var pw by remember { mutableStateOf("") }
    var consent by remember { mutableStateOf(false) }
    val done: (String?) -> Unit = { e ->
        busy = false
        when {
            e == null -> {
                pw = ""
                Store.put(c, "ever_signed_in", "1")
                if (!nav.back()) nav.go(SCREEN_ACCOUNT)
            }
            e == NEED_2FA -> { step = "two_fa"; err = "" }
            else -> err = e
        }
    }
    Page(if (step == "two_fa") Strings.sg2fa else Strings.loginTitle) {
        if (step == "two_fa") {
            block { Body(Strings.sg2faWhy) }
            block { Field(Strings.sgCode, "sg_2fa", keyboard = KeyboardType.NumberPassword) }
            block {
                Btn(if (busy) Strings.sending else Strings.cont, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
                    busy = true; err = ""
                    scope.launch { done(Auth.twoFa(c, AppState.form["sg_2fa"] ?: "")) }
                }
            }
            if (err.isNotEmpty()) block { Pill(err, "bad") }
            return@Page
        }
        block { Body(Strings.loginWhy) }
        if (Ways.consentNeeded) block { CheckRow(Strings.sgConsent, "sg_consent") }
        if (step == "otp") {
            block { Field(Strings.sgPhone, "sg_phone", keyboard = KeyboardType.Phone) }
            if (phone.isEmpty()) {
                block {
                    Btn(if (busy) Strings.sending else Strings.sgSendCode, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
                        busy = true; err = ""
                        val p = AppState.form["sg_phone"] ?: ""
                        scope.launch {
                            val e = Auth.otpStart(p)
                            busy = false
                            if (e == null) { phone = p; err = "" } else err = e
                        }
                    }
                }
            } else {
                block { Small(Strings.sgSentTo + " " + phone) }
                block { Field(Strings.sgCode, "sg_code", keyboard = KeyboardType.NumberPassword) }
                block { Field(Strings.name, "sg_name") }
                block {
                    Btn(if (busy) Strings.sending else Strings.cont, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
                        busy = true; err = ""
                        scope.launch {
                            done(Auth.otpCheck(c, phone, AppState.form["sg_code"] ?: "", AppState.form["sg_name"] ?: "",
                                AppState.form["sg_consent"] == "1"))
                        }
                    }
                }
                block { Btn(Strings.sgAgain, kind = BtnKind.Ghost, small = true) { phone = ""; err = "" } }
            }
        }
        if (step == "password") {
            block { Field(Strings.email, "auth_email", keyboard = KeyboardType.Email) }
            block { PasswordBox(pw) { pw = it } }
            block {
                Btn(if (busy) Strings.sending else Strings.login, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
                    busy = true; err = ""
                    scope.launch { done(Auth.login(c, AppState.form["auth_email"] ?: "", pw)) }
                }
            }
            if (Db.signupOpen) block {
                Btn(Strings.newHere, kind = BtnKind.Ghost, small = true) {
                    busy = true; err = ""
                    scope.launch {
                        done(Auth.signup(c, AppState.form["auth_email"] ?: "", pw, AppState.form["auth_name"] ?: ""))
                    }
                }
            }
        }
        if (err.isNotEmpty()) block { Pill(err, "bad") }
        if (Ways.google) {
            block {
                GoogleButton(enabled = !busy) { token, nonce ->
                    busy = true; err = ""
                    scope.launch {
                        done(Auth.social(c, "google", token, nonce, AppState.form["sg_name"] ?: "",
                            AppState.form["sg_consent"] == "1"))
                    }
                }
            }
        }
        if (Ways.otp && Ways.password) {
            block {
                Btn(if (step == "otp") Strings.sgUseEmail else Strings.sgUsePhone, kind = BtnKind.Ghost, small = true) {
                    step = if (step == "otp") "password" else "otp"
                    err = ""
                }
            }
        }
        block { Small(Strings.sgNever) }
    }
}

/** This account's logins and its second step - the user's own page, not the owner's. */
@Composable
fun SecurityScreen() {
    val c = ctx()
    val nav = LocalNav.current
    val scope = rememberCoroutineScope()
    var data by remember { mutableStateOf<Item?>(null) }
    var tick by remember { mutableIntStateOf(0) }
    var busy by remember { mutableStateOf(false) }
    var secret by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    LaunchedEffect(Auth.me.value, tick) {
        val r = Cloud.call("GET", "/security", null, Auth.token())
        data = if (r.ok) Item(r.body) else null
    }
    val act: (String, JSONObject) -> Unit = { what, body ->
        busy = true
        scope.launch {
            val r = Cloud.call("POST", "/security/$what", body, Auth.token())
            busy = false
            if (r.ok) {
                if (what == "2fa-start") secret = r.body.optString("secret", "")
                if (what == "2fa-on") { secret = ""; note = Strings.sg2faOn }
                if (what == "end-all") Auth.logout(c)
                tick++
            } else note = r.error.ifEmpty { Strings.tryAgain }
        }
    }
    Page(Strings.sgSecurity) {
        val d = data
        if (Auth.me.value == null) {
            block { Empty("user", Strings.notSignedIn, Strings.loginWhy, Strings.login) { nav.go(SCREEN_LOGIN) } }
            return@Page
        }
        if (d == null) { block { Small(Strings.loading) }; return@Page }
        block { SectionHeader(Strings.sgLogins) }
        d.list("sessions").forEach { s ->
            block {
                HCard {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Title(s.s("device"))
                            Small(s.s("how") + " · " + s.s("ip") + (if (s.b("this")) " · " + Strings.sgThisPhone else ""))
                        }
                        if (!s.b("this")) {
                            Btn(Strings.sgEnd, kind = BtnKind.Outline, small = true, enabled = !busy) {
                                act("end", JSONObject().put("id", s.id))
                            }
                        }
                    }
                }
            }
        }
        block {
            Btn(Strings.sgEndAll, kind = BtnKind.Outline, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
                act("end-all", JSONObject())
            }
        }
        if (d.b("staff")) {
            block { SectionHeader(Strings.sg2fa) }
            block { Small(if (d.b("two_fa")) Strings.sg2faIsOn else Strings.sg2faWhy) }
            if (secret.isNotEmpty()) {
                block { Small(Strings.sg2faAdd) }
                block { HCard { Title(secret) } }
                block { Field(Strings.sgCode, "sg_on", keyboard = KeyboardType.NumberPassword) }
                block {
                    Btn(Strings.cont, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
                        act("2fa-on", JSONObject().put("code", AppState.form["sg_on"] ?: ""))
                    }
                }
            } else if (!d.b("two_fa")) {
                block { Btn(Strings.sg2faStart, modifier = Modifier.fillMaxWidth(), enabled = !busy) { act("2fa-start", JSONObject()) } }
            } else if (!d.b("two_fa_required")) {
                block { Field(Strings.sgCode, "sg_off", keyboard = KeyboardType.NumberPassword) }
                block {
                    Btn(Strings.sg2faOff, kind = BtnKind.Outline, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
                        act("2fa-off", JSONObject().put("code", AppState.form["sg_off"] ?: ""))
                    }
                }
            } else {
                block { Small(Strings.sg2faMust) }
            }
        }
        block { SectionHeader(Strings.sgMyData) }
        block { Small(Strings.sgMyDataWhy) }
        block {
            Btn(Strings.sgMyDataGet, kind = BtnKind.Tonal, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
                busy = true
                scope.launch {
                    val r = Cloud.call("GET", "/my-data", null, Auth.token())
                    busy = false
                    note = if (r.ok) Strings.sgMyDataReady else r.error.ifEmpty { Strings.tryAgain }
                    if (r.ok) Act.copy(c, r.body.toString().take(100000), Strings.sgMyDataReady)
                }
            }
        }
        if (nav.screens.contains("delete_account")) {
            block { Btn(Strings.deleteTitle, kind = BtnKind.Danger, modifier = Modifier.fillMaxWidth()) { nav.go("delete_account") } }
        }
        if (note.isNotEmpty()) block { Pill(note, "info") }
    }
}
