package hoola.kit

// Made by Hoola App Sahayak (v0.325 UPDATES). On start the app asks its Hoola server for the newest build; when it is
// newer than this one, a small dialog shows "What's new" and Update (the APK opens in the phone's browser and Android's
// own installer takes over - the same key, so it installs over this version and keeps the user's data). "Later" hides
// that version until a newer one comes. Store builds get the Play in-app update later; this is for preview builds.

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.unit.dp

object AppUpdate {
    /** The newer version on offer (null = none). */
    val offer = mutableStateOf<Item?>(null)

    suspend fun check(ctx: Context, myCode: Int) {
        val r = Cloud.call("GET", "/latest")
        if (!r.ok) return
        val code = r.body.optInt("version_code", 0)
        if (code <= myCode || r.body.optString("url").isEmpty()) return
        if (Store.get(ctx, "update_skip") == code.toString()) return
        offer.value = Item(r.body)
    }

    fun later(ctx: Context) {
        offer.value?.let { Store.put(ctx, "update_skip", it.i("version_code").toString()) }
        offer.value = null
    }
}

@Composable
fun UpdateDialog() {
    val o = AppUpdate.offer.value ?: return
    val c = ctx()
    AlertDialog(
        onDismissRequest = { AppUpdate.later(c) },
        title = { Text(Strings.updateTitle + " " + o.s("version_name")) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                o.strings("notes").take(5).forEach { Text("• $it") }
            }
        },
        confirmButton = { TextButton(onClick = { AppUpdate.offer.value = null; Act.link(c, o.s("url")) }) { Text(Strings.update) } },
        dismissButton = { TextButton(onClick = { AppUpdate.later(c) }) { Text(Strings.later) } },
    )
}
