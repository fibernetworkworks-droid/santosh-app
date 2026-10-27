package com.newtika.santosh

import android.app.Activity
import android.content.Context
import android.content.DialogInterface
import android.hardware.biometrics.BiometricManager
import android.hardware.biometrics.BiometricPrompt
import android.os.Build
import android.os.CancellationSignal
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyPermanentlyInvalidatedException
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.UUID

/**
 * v0.97 Fingerprint-signed approvals. An EC P-256 key lives inside Android Keystore (StrongBox when the phone has it);
 * it can sign only right after a strong fingerprint / face check and is voided when a new fingerprint is added. Only
 * the public key leaves the phone. The server sends a message naming the exact money card; BiometricPrompt shows the
 * card's title and amount and the key signs that message. Android 9+ only (framework BiometricPrompt + CryptoObject);
 * older phones keep the slide.
 */
object ApproveKey {
    private const val ALIAS = "hoola_approve_v1"
    private const val PREFS = "hoola_approve"

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun deviceId(ctx: Context): String {
        val p = prefs(ctx)
        return p.getString("device_id", null) ?: UUID.randomUUID().toString().also { p.edit().putString("device_id", it).apply() }
    }

    private fun ks(): KeyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    /** 0 = ready, 1 = no strong biometric enrolled, 2 = no hardware / Android too old. */
    private fun biometric(ctx: Context): Int {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) return 2
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                when (ctx.getSystemService(BiometricManager::class.java)
                    .canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)) {
                    BiometricManager.BIOMETRIC_SUCCESS -> 0
                    BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> 1
                    else -> 2
                }
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                @Suppress("DEPRECATION")
                when (ctx.getSystemService(BiometricManager::class.java).canAuthenticate()) {
                    BiometricManager.BIOMETRIC_SUCCESS -> 0
                    BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> 1
                    else -> 2
                }
            } else {
                @Suppress("DEPRECATION")
                val fm = ctx.getSystemService(android.hardware.fingerprint.FingerprintManager::class.java)
                if (fm == null || !fm.isHardwareDetected) 2 else if (!fm.hasEnrolledFingerprints()) 1 else 0
            }
        } catch (_: Throwable) { 2 }
    }

    fun info(ctx: Context): Map<String, Any?> {
        val b = biometric(ctx)
        val has = try { ks().containsAlias(ALIAS) } catch (_: Throwable) { false }
        return mapOf("supported" to (b != 2), "enrolled" to (b == 0), "has_key" to has,
            "device_id" to deviceId(ctx), "strongbox" to prefs(ctx).getBoolean("strongbox", false),
            "model" to "${Build.MANUFACTURER} ${Build.MODEL}".trim())
    }

    private fun generate(strongBox: Boolean) {
        val b = KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_SIGN)
            .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setUserAuthenticationRequired(true)
            .setInvalidatedByBiometricEnrollment(true)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            b.setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
        }
        if (strongBox && Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) b.setIsStrongBoxBacked(true)
        val g = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore")
        g.initialize(b.build())
        g.generateKeyPair()
    }

    /** A fresh key (any old one is replaced). {public_key, device_id, strongbox} or {error}. */
    fun create(ctx: Context): Map<String, Any?> {
        when (biometric(ctx)) {
            2 -> return mapOf("error" to "not_supported")
            1 -> return mapOf("error" to "no_fingerprint")
        }
        return try {
            try { ks().deleteEntry(ALIAS) } catch (_: Throwable) {}
            var strong = Build.VERSION.SDK_INT >= Build.VERSION_CODES.P
            try { generate(strong) } catch (_: Throwable) { strong = false; generate(false) }
            prefs(ctx).edit().putBoolean("strongbox", strong).apply()
            val pub = ks().getCertificate(ALIAS).publicKey.encoded
            mapOf("public_key" to Base64.encodeToString(pub, Base64.NO_WRAP), "device_id" to deviceId(ctx), "strongbox" to strong)
        } catch (t: Throwable) {
            mapOf("error" to (t.message ?: t.javaClass.simpleName).take(200))
        }
    }

    fun delete(ctx: Context): Boolean = try { ks().deleteEntry(ALIAS); true } catch (_: Throwable) { false }

    /** Fingerprint, then sign [message]. Calls back once with {signature, device_id} or {error}. */
    fun sign(act: Activity, message: String, title: String, subtitle: String, done: (Map<String, Any?>) -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) { done(mapOf("error" to "not_supported")); return }
        var answered = false
        fun once(m: Map<String, Any?>) { if (!answered) { answered = true; done(m) } }
        val sig: Signature
        try {
            val key = ks().getKey(ALIAS, null) as? PrivateKey ?: run { once(mapOf("error" to "no_key")); return }
            sig = Signature.getInstance("SHA256withECDSA")
            sig.initSign(key)
        } catch (_: KeyPermanentlyInvalidatedException) {
            once(mapOf("error" to "key_invalidated")); return     // a new fingerprint was added: set the phone up again
        } catch (t: Throwable) {
            once(mapOf("error" to (t.message ?: t.javaClass.simpleName).take(200))); return
        }
        try {
            val exec = act.mainExecutor
            val prompt = BiometricPrompt.Builder(act)
                .setTitle(title.take(80).ifBlank { "Haan dene ke liye fingerprint" })
                .setSubtitle(subtitle.take(120))
                .setDescription("Sirf aap hi yeh haan de sakti / sakte hain.")
                .setNegativeButton("Rehne do", exec, DialogInterface.OnClickListener { _, _ -> once(mapOf("error" to "cancelled")) })
                .build()
            prompt.authenticate(BiometricPrompt.CryptoObject(sig), CancellationSignal(), exec,
                object : BiometricPrompt.AuthenticationCallback() {
                    override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                        try {
                            val s = result.cryptoObject?.signature ?: sig
                            s.update(message.toByteArray(Charsets.UTF_8))
                            once(mapOf("signature" to Base64.encodeToString(s.sign(), Base64.NO_WRAP),
                                "device_id" to deviceId(act)))
                        } catch (t: Throwable) {
                            once(mapOf("error" to (t.message ?: "sign_failed").take(200)))
                        }
                    }

                    override fun onAuthenticationError(code: Int, msg: CharSequence?) {
                        once(mapOf("error" to if (code == BiometricPrompt.BIOMETRIC_ERROR_USER_CANCELED ||
                            code == BiometricPrompt.BIOMETRIC_ERROR_CANCELED) "cancelled" else (msg?.toString() ?: "error $code")))
                    }
                })
        } catch (t: Throwable) {
            once(mapOf("error" to (t.message ?: t.javaClass.simpleName).take(200)))
        }
    }
}
