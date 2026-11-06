package hoola.kit

// Made by Hoola App Sahayak (v0.347 BHASHA). The app's words in the customer's language: every screen's words go through
// T("English words"); the table (assets/i18n.json, made by Hoola at build time) holds the translations; the customer picks
// the language on My account (kept on the phone). Her business data (product names, prices, rows) is shown as typed.

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.rememberScrollState
import androidx.compose.ui.Modifier
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.unit.dp
import org.json.JSONObject

object I18n {
    val lang = mutableStateOf("en")
    var langs: List<String> = listOf("en")
        private set
    var names: Map<String, String> = mapOf("en" to "English")
        private set
    private var table: Map<String, Map<String, String>> = emptyMap()
    private var fallback = "en"

    /** At app start: the table from the build + the customer's own choice (else the business's language). */
    fun load(ctx: Context, appLanguage: String) {
        fallback = appLanguage
        try {
            val o = JSONObject(ctx.assets.open("i18n.json").bufferedReader().use { it.readText() })
            val ls = o.optJSONArray("langs")
            langs = if (ls != null) List(ls.length()) { ls.getString(it) } else listOf("en")
            val nm = o.optJSONObject("names") ?: JSONObject()
            names = langs.associateWith { nm.optString(it, it) }
            val t = o.optJSONObject("t") ?: JSONObject()
            table = t.keys().asSequence().associateWith { l ->
                val m = t.getJSONObject(l)
                m.keys().asSequence().associateWith { k -> m.getString(k) }
            }
            fallback = o.optString("default", appLanguage)
        } catch (_: Exception) {
        }
        val chosen = Store.get(ctx, "hoola_lang")
        set(ctx, if (chosen.isNotEmpty() && chosen in langs) chosen else fallback, save = false)
    }

    fun set(ctx: Context, code: String, save: Boolean = true) {
        lang.value = code
        Strings.init(code)
        if (save) Store.put(ctx, "hoola_lang", code)
    }

    fun tr(s: String): String = if (lang.value == "en") s else table[lang.value]?.get(s) ?: s
}

/** The screen's words in the customer's language (English words are the key; untranslated = as written). */
fun T(s: String): String = I18n.tr(s)

/** The language choice on My account (only when the app carries more than one language). */
@Composable
fun LanguagePicker() {
    if (I18n.langs.size < 2) return
    val c = ctx()
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Label(T("Language"))
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            I18n.langs.forEach { code ->
                FilterChip(selected = I18n.lang.value == code, onClick = { I18n.set(c, code) }, label = { Text(I18n.names[code] ?: code) })
            }
        }
    }
}
