package hoola.kit

// Made by Hoola App Sahayak. The only ways a generated screen reaches outside the app: the phone's own dialer,
// WhatsApp chat link, share sheet, maps, and UPI to the business's OWN UPI ID (the user's UPI app asks the PIN; this app
// never sees it). Nothing is sent or paid by the app itself.

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

object Act {
    fun toast(ctx: Context, text: String) = Toast.makeText(ctx, text, Toast.LENGTH_SHORT).show()

    private fun open(ctx: Context, uri: String): Boolean = try {
        ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(uri)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); true
    } catch (_: Exception) { false }

    private fun digits(p: String): String = p.filter { it.isDigit() }.let { if (it.length == 10) "91$it" else it }

    fun call(ctx: Context, phone: String = AppData.facts.s("phone")) {
        if (phone.isBlank()) { toast(ctx, Strings.noPhone); return }
        try { ctx.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:${phone.filter { it.isDigit() || it == '+' }}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
        catch (_: Exception) { toast(ctx, Strings.noPhone) }
    }

    fun whatsapp(ctx: Context, text: String = "", phone: String = AppData.facts.s("whatsapp", AppData.facts.s("phone"))) {
        if (phone.isBlank()) { toast(ctx, Strings.noPhone); return }
        open(ctx, "https://wa.me/${digits(phone)}?text=${Uri.encode(text)}")
    }

    fun share(ctx: Context, text: String) {
        try {
            val i = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text)
            ctx.startActivity(Intent.createChooser(i, Strings.share).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (_: Exception) {}
    }

    fun maps(ctx: Context, query: String = AppData.facts.s("address")) {
        if (query.isBlank()) return
        open(ctx, "https://www.google.com/maps/search/?api=1&query=${Uri.encode(query)}")
    }

    /** UPI to the business's own UPI ID. Apps that refuse links to a person: the UPI ID is copied instead. */
    fun payUpi(ctx: Context, amount: Double, note: String) {
        val vpa = AppData.facts.s("upi_id")
        if (vpa.isBlank()) { toast(ctx, Strings.noUpi); return }
        val name = AppData.facts.s("name", "Shop")
        val am = if (amount > 0) "&am=${"%.2f".format(java.util.Locale.US, amount)}" else ""
        val uri = "upi://pay?pa=${Uri.encode(vpa)}&pn=${Uri.encode(name)}$am&cu=INR&tn=${Uri.encode(note.take(60))}"
        if (!open(ctx, uri)) copy(ctx, vpa, Strings.upiCopied)
    }

    fun copy(ctx: Context, text: String, said: String = "") {
        val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager ?: return
        cm.setPrimaryClip(ClipData.newPlainText("text", text))
        if (said.isNotEmpty()) toast(ctx, said)
    }
}

/** For screens: `val ctx = ctx()` then Act.call(ctx). */
@Composable
fun ctx(): Context = LocalContext.current
