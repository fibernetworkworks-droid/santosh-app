package hoola.kit

// Made by Hoola App Sahayak (v0.453). The ON version: "Continue with Google" through Android's Credential Manager.
// This file is written into the build ONLY when the owner turned Google sign-in on; then androidx.credentials and
// googleid are added to this app's libraries too. The app never sees a Google secret - it gets an ID token and hands
// it to its own server, which checks the signature, the audience (her client id) and the single-use nonce.

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.launch

@Composable
fun GoogleButton(enabled: Boolean, onToken: (String, String) -> Unit) {
    val serverId = Ways.serverClientId
    if (serverId.isEmpty()) return
    val c = ctx()
    val scope = rememberCoroutineScope()
    Btn(Strings.sgGoogle, kind = BtnKind.Outline, modifier = Modifier.fillMaxWidth(), icon = "user", enabled = enabled) {
        scope.launch {
            val nonce = Auth.nonce()
            if (nonce.isEmpty()) {
                Act.toast(c, Strings.tryAgain)
                return@launch
            }
            val opt = GetSignInWithGoogleOption.Builder(serverId).setNonce(nonce).build()
            val req = GetCredentialRequest.Builder().addCredentialOption(opt).build()
            try {
                val res = CredentialManager.create(c).getCredential(c, req)
                val cred = GoogleIdTokenCredential.createFrom(res.credential.data)
                onToken(cred.idToken, nonce)
            } catch (e: GetCredentialException) {
                Act.toast(c, Strings.tryAgain)
            }
        }
    }
}
