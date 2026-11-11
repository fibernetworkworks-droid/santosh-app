package hoola.kit

// Made by Hoola App Sahayak (v0.802 DEVICE). Five phone features a screen uses with one call, none of them needs a new
// library and none asks for a dangerous permission:
// - BiometricLock: fingerprint / face (or the phone's own PIN / pattern) before a private screen, through the phone's own
//   BiometricPrompt (Android 9+). The app never sees the fingerprint, the face or the PIN - the system only says yes / no.
//   Android 8 phones get the phone's own screen-lock check instead. USE_BIOMETRIC is in the manifest only when a screen
//   uses this (gen.uses_biometric).
// - RateAppButton: opens the app's own Play Store page (the Play app, or the web page when Play is missing).
// - AddToCalendarButton: the phone's calendar app opens with the event filled in; the user saves it. No permission.
// - PickContactButton: the phone's contact picker, ONE contact's name + number chosen by the user. No READ_CONTACTS: the
//   picker gives the app a one-time read of only the row the user picked.

import android.app.Activity
import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.hardware.biometrics.BiometricManager
import android.hardware.biometrics.BiometricPrompt
import android.net.Uri
import android.os.Build
import android.os.CancellationSignal
import android.provider.CalendarContract
import android.provider.ContactsContract
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

object Device {
    /** Fingerprint / face / the phone's own lock, then onOk. Android 9+ (older phones: use BiometricLock, it covers them). */
    fun askBiometric(ctx: Context, reason: String, onOk: () -> Unit, onFail: () -> Unit = {}) {
        if (Build.VERSION.SDK_INT < 28) { Act.toast(ctx, Strings.lockOld); onFail(); return }
        try {
            val exec = ctx.mainExecutor
            val b = BiometricPrompt.Builder(ctx).setTitle(Strings.unlockTitle).setSubtitle(reason.take(120))
            if (Build.VERSION.SDK_INT >= 30) {
                b.setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_WEAK or BiometricManager.Authenticators.DEVICE_CREDENTIAL)
            } else if (Build.VERSION.SDK_INT >= 29) {
                @Suppress("DEPRECATION") b.setDeviceCredentialAllowed(true)
            } else {
                b.setNegativeButton(Strings.later, exec) { _, _ -> onFail() }
            }
            b.build().authenticate(CancellationSignal(), exec, object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult?) { onOk() }
                override fun onAuthenticationError(errorCode: Int, errString: CharSequence?) {
                    when (errorCode) {
                        // no fingerprint / face set up, or no sensor: the phone itself is the only lock there is
                        BiometricPrompt.BIOMETRIC_ERROR_NO_BIOMETRICS, BiometricPrompt.BIOMETRIC_ERROR_HW_NOT_PRESENT,
                        BiometricPrompt.BIOMETRIC_ERROR_HW_UNAVAILABLE, BiometricPrompt.BIOMETRIC_ERROR_NO_DEVICE_CREDENTIAL -> noLock(ctx, onOk, onFail)
                        BiometricPrompt.BIOMETRIC_ERROR_USER_CANCELED, BiometricPrompt.BIOMETRIC_ERROR_CANCELED -> onFail()
                        else -> { Act.toast(ctx, Strings.lockFailed); onFail() }
                    }
                }
            })
        } catch (_: Exception) {
            noLock(ctx, onOk, onFail)
        }
    }

    /** No fingerprint / face to check: a phone with no screen lock at all opens (anyone holding it could open it anyway);
     *  a phone WITH a screen lock stays shut and says so (nothing is let through on an error). */
    private fun noLock(ctx: Context, onOk: () -> Unit, onFail: () -> Unit) {
        val km = ctx.getSystemService(Context.KEYGUARD_SERVICE) as? KeyguardManager
        if (km == null || !km.isKeyguardSecure) { Act.toast(ctx, Strings.noLock); onOk() }
        else { Act.toast(ctx, Strings.lockFailed); onFail() }
    }

    /** The app's own Play Store page (to rate it): the Play app, else the web page. */
    fun askForReview(ctx: Context) {
        val id = ctx.packageName
        if (!Act.open(ctx, "market://details?id=$id")) Act.open(ctx, "https://play.google.com/store/apps/details?id=$id")
    }

    /** The phone's calendar app with the event filled in (the user taps Save there). Times are epoch milliseconds. */
    fun addToCalendar(ctx: Context, title: String, startMillis: Long, endMillis: Long, location: String = "", notes: String = "") {
        try {
            val end = if (endMillis > startMillis) endMillis else startMillis + 60 * 60 * 1000L
            val i = Intent(Intent.ACTION_INSERT).setData(CalendarContract.Events.CONTENT_URI)
                .putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, startMillis)
                .putExtra(CalendarContract.EXTRA_EVENT_END_TIME, end)
                .putExtra(CalendarContract.Events.TITLE, title.take(200))
                .putExtra(CalendarContract.Events.EVENT_LOCATION, location.take(300))
                .putExtra(CalendarContract.Events.DESCRIPTION, notes.take(2000))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(i)
        } catch (_: Exception) {
            Act.toast(ctx, Strings.noCalendar)
        }
    }

    internal fun pickedContact(ctx: Context, uri: Uri?): Pair<String, String>? {
        if (uri == null) return null
        return try {
            val cols = arrayOf(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME, ContactsContract.CommonDataKinds.Phone.NUMBER)
            ctx.contentResolver.query(uri, cols, null, null, null)?.use { cur ->
                if (!cur.moveToFirst()) null
                else Pair(cur.getString(0).orEmpty().take(100), cur.getString(1).orEmpty().take(30))
            }
        } catch (_: Exception) {
            null
        }
    }
}

/** A lock card for a private screen: tap = fingerprint / face / the phone's PIN, then onOk (show the screen). Android 8
 *  phones get the phone's own screen-lock check. Use it as: if (!open) BiometricLock(T("..."), onOk = { open = true }). */
@Composable
fun BiometricLock(reason: String, onOk: () -> Unit) {
    val c = ctx()
    val old = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { r ->
        if (r.resultCode == Activity.RESULT_OK) onOk() else Act.toast(c, Strings.lockFailed)
    }
    HCard {
        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) {
            HIcon("lock", size = 34.dp, tint = H.c.primaryText)
            Title(Strings.unlockTitle)
            if (reason.isNotEmpty()) Small(reason)
            Btn(Strings.unlock, icon = "shield") {
                if (Build.VERSION.SDK_INT >= 28) {
                    Device.askBiometric(c, reason, onOk)
                } else {
                    val km = c.getSystemService(Context.KEYGUARD_SERVICE) as? KeyguardManager
                    @Suppress("DEPRECATION")
                    val i = if (km != null && km.isKeyguardSecure) km.createConfirmDeviceCredentialIntent(Strings.unlockTitle, reason) else null
                    if (i == null) { Act.toast(c, Strings.noLock); onOk() }
                    else try { old.launch(i) } catch (_: Exception) { Act.toast(c, Strings.lockFailed) }
                }
            }
        }
    }
}

/** "Rate this app": opens the app's own Play Store page. */
@Composable
fun RateAppButton() {
    val c = ctx()
    Btn(Strings.rateApp, kind = BtnKind.Tonal, icon = "star", small = true) { Device.askForReview(c) }
}

/** "Add to calendar": the phone's calendar opens with the event filled in. startMillis / endMillis = epoch milliseconds. */
@Composable
fun AddToCalendarButton(title: String, startMillis: Long, endMillis: Long, location: String = "", notes: String = "") {
    val c = ctx()
    Btn(Strings.addCalendar, kind = BtnKind.Tonal, icon = "calendar", small = true) {
        Device.addToCalendar(c, title, startMillis, endMillis, location, notes)
    }
}

/** "Pick from contacts": the phone's contact picker; onPicked(name, phone) gets the one contact the user chose. */
@Composable
fun PickContactButton(onPicked: (name: String, phone: String) -> Unit) {
    val c = ctx()
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { r ->
        if (r.resultCode == Activity.RESULT_OK) {
            val got = Device.pickedContact(c, r.data?.data)
            if (got != null && got.second.isNotBlank()) onPicked(got.first, got.second) else Act.toast(c, Strings.noContact)
        }
    }
    Btn(Strings.pickContact, kind = BtnKind.Tonal, icon = "user", small = true) {
        try { pick.launch(Intent(Intent.ACTION_PICK, ContactsContract.CommonDataKinds.Phone.CONTENT_URI)) }
        catch (_: Exception) { Act.toast(c, Strings.noContact) }
    }
}
