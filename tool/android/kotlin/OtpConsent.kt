package com.newtika.santosh

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import androidx.core.content.ContextCompat
import com.google.android.gms.auth.api.phone.SmsRetriever
import com.google.android.gms.common.api.CommonStatusCodes
import com.google.android.gms.common.api.Status
import io.flutter.plugin.common.MethodChannel

/**
 * v0.83 Google's SMS User Consent API: while a website job waits for an OTP, the next OTP SMS shows Android's own
 * one-tap "Allow Hoola to read this message?" sheet. Only on her Allow does the app see that ONE message; we take the
 * code out of it and send only the digits to the waiting box. No READ_SMS / RECEIVE_SMS permission (Play-safe).
 * A message that looks like a bank / payment OTP is never filled (money rule: she enters those herself).
 */
object OtpConsent {
    const val REQ = 4711
    private var pending: MethodChannel.Result? = null
    private var receiver: BroadcastReceiver? = null
    private var waitingIntent: Intent? = null     // the consent sheet arrived while Hoola was not on screen
    private var digits = 0
    private var appCtx: Context? = null
    @Volatile var current: Activity? = null       // the live MainActivity (set in onResume)

    private val MONEY = Regex("(?i)\\b(debit(ed)?|credit(ed)?|txn|transaction|a/c|acct|account|rs\\.?|inr|amount|pay(ment)?|upi|card|purchase|spent|withdraw)\\b|₹")

    fun start(act: Activity, wantDigits: Int, result: MethodChannel.Result) {
        finish(null)                               // an older wait is replaced by the new one
        pending = result
        digits = wantDigits
        current = act
        appCtx = act.applicationContext
        try {
            SmsRetriever.getClient(act).startSmsUserConsent(null)
        } catch (t: Throwable) {
            finish(mapOf("error" to "unavailable"))
            return
        }
        val r = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context, intent: Intent) {
                if (intent.action != SmsRetriever.SMS_RETRIEVED_ACTION) return
                val extras = intent.extras ?: return
                @Suppress("DEPRECATION")
                val status = extras.get(SmsRetriever.EXTRA_STATUS) as? Status ?: return
                when (status.statusCode) {
                    CommonStatusCodes.SUCCESS -> {
                        val consent: Intent? = if (Build.VERSION.SDK_INT >= 33)
                            extras.getParcelable(SmsRetriever.EXTRA_CONSENT_INTENT, Intent::class.java)
                        else @Suppress("DEPRECATION") extras.getParcelable(SmsRetriever.EXTRA_CONSENT_INTENT)
                        if (consent == null) { finish(mapOf("error" to "no_sheet")); return }
                        val a = current
                        if (MainActivity.visible && a != null) launch(a, consent) else waitingIntent = consent
                    }
                    CommonStatusCodes.TIMEOUT -> finish(mapOf("error" to "timeout"))
                }
            }
        }
        receiver = r
        try {
            ContextCompat.registerReceiver(act.applicationContext, r, IntentFilter(SmsRetriever.SMS_RETRIEVED_ACTION),
                SmsRetriever.SEND_PERMISSION, null, ContextCompat.RECEIVER_EXPORTED)
        } catch (t: Throwable) {
            receiver = null
            finish(mapOf("error" to "unavailable"))
        }
    }

    /** Hoola came back on screen: show a consent sheet that arrived meanwhile. */
    fun onResume(act: Activity) {
        current = act
        val w = waitingIntent ?: return
        waitingIntent = null
        launch(act, w)
    }

    private fun launch(act: Activity, consent: Intent) {
        try {
            act.startActivityForResult(consent, REQ)
        } catch (t: Throwable) {
            finish(mapOf("error" to "no_sheet"))
        }
    }

    /** From MainActivity.onActivityResult. */
    fun onResult(resultCode: Int, data: Intent?) {
        if (resultCode != Activity.RESULT_OK || data == null) { finish(mapOf("error" to "denied")); return }
        val sms = data.getStringExtra(SmsRetriever.EXTRA_SMS_MESSAGE) ?: ""
        if (MONEY.containsMatchIn(sms)) { finish(mapOf("error" to "bank")); return }
        val code = pick(sms)
        finish(if (code != null) mapOf("code" to code) else mapOf("error" to "no_code"))
    }

    private fun pick(sms: String): String? {
        val near = Regex("(?i)(?:otp|code|verification|one.?time|पासवर्ड|कोड|ओटीपी)\\D{0,30}?(\\d{4,8})").find(sms)?.groupValues?.get(1)
        val all = Regex("(?<!\\d)\\d{4,8}(?!\\d)").findAll(sms).map { it.value }.toList()
        if (digits in 4..8) {
            if (near != null && near.length == digits) return near
            all.firstOrNull { it.length == digits }?.let { return it }
            return null
        }
        return near ?: all.firstOrNull()
    }

    fun cancel() = finish(mapOf("error" to "cancelled"))

    private fun finish(value: Map<String, String>?) {
        receiver?.let { r -> try { appCtx?.unregisterReceiver(r) } catch (_: Throwable) {} }
        receiver = null
        waitingIntent = null
        val p = pending
        pending = null
        try { p?.success(value) } catch (_: Throwable) {}
    }
}
