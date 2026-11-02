package hoola.kit

// Made by Hoola App Sahayak (v0.442). The OFF version of the Google button: it draws nothing and pulls in no library.
// When the owner turns Google sign-in on, the build replaces this file with the Credential Manager version and adds
// androidx.credentials + googleid to this app's libraries - so an app that does not use Google carries neither.

import androidx.compose.runtime.Composable

@Composable
fun GoogleButton(enabled: Boolean, onToken: (String, String) -> Unit) {
}
