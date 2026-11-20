package com.newtika.santosh

import android.util.Base64
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.Mac
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * v0.999.57 HOOLA CRED on the phone: the same zero-knowledge vault as the console, done with Android's own crypto so
 * 600,000 PBKDF2 rounds take a second or two. Master password -> PBKDF2-SHA256 -> AES-256-GCM key that unwraps the
 * random vault key; each item is AES-256-GCM JSON. Nothing here is stored: the Dart side holds the vault key in memory
 * while unlocked and forgets it on lock. Runs off the main thread (the caller posts the result back).
 */
object CredCrypto {
    private val rnd = SecureRandom()
    private fun b64(b: ByteArray) = Base64.encodeToString(b, Base64.NO_WRAP)
    private fun unb64(s: String) = Base64.decode(s, Base64.DEFAULT)

    private fun kek(pw: String, salt: ByteArray, iters: Int): ByteArray {
        val spec = PBEKeySpec(pw.toCharArray(), salt, iters, 256)
        try {
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).encoded
        } finally {
            spec.clearPassword()
        }
    }

    private fun gcm(mode: Int, key: ByteArray, iv: ByteArray): Cipher =
        Cipher.getInstance("AES/GCM/NoPadding").apply { init(mode, SecretKeySpec(key, "AES"), GCMParameterSpec(128, iv)) }

    private fun seal(key: ByteArray, plain: ByteArray): Map<String, String> {
        val iv = ByteArray(12).also { rnd.nextBytes(it) }
        return mapOf("iv" to b64(iv), "ct" to b64(gcm(Cipher.ENCRYPT_MODE, key, iv).doFinal(plain)))
    }

    private fun open(key: ByteArray, iv: String, ct: String): ByteArray = gcm(Cipher.DECRYPT_MODE, key, unb64(iv)).doFinal(unb64(ct))

    /** Her master password opens the wrapped vault key; a wrong one throws (the GCM tag fails). */
    fun unwrap(pw: String, salt: String, iters: Int, iv: String, ct: String): String {
        val k = kek(pw, unb64(salt), iters)
        try {
            return b64(open(k, iv, ct))
        } finally {
            k.fill(0)
        }
    }

    /** A new vault: a random salt and vault key, the key wrapped with her master password. */
    fun create(pw: String, iters: Int): Map<String, Any> {
        val salt = ByteArray(16).also { rnd.nextBytes(it) }
        val vk = ByteArray(32).also { rnd.nextBytes(it) }
        val k = kek(pw, salt, iters)
        try {
            return mapOf("salt" to b64(salt), "iters" to iters, "wrapped" to seal(k, vk), "key" to b64(vk))
        } finally {
            k.fill(0); vk.fill(0)
        }
    }

    /** A new master password: the same vault key wrapped again (her items stay as they are). */
    fun rewrap(newPw: String, key: String, iters: Int): Map<String, Any> {
        val salt = ByteArray(16).also { rnd.nextBytes(it) }
        val k = kek(newPw, salt, iters)
        try {
            return mapOf("salt" to b64(salt), "iters" to iters, "wrapped" to seal(k, unb64(key)))
        } finally {
            k.fill(0)
        }
    }

    /** Many items at once: each {iv, ct} -> its text, or "" when one cannot be opened. */
    fun openMany(key: String, boxes: List<Map<String, String>>): List<String> {
        val k = unb64(key)
        try {
            return boxes.map { b -> try { String(open(k, b["iv"] ?: "", b["ct"] ?: ""), Charsets.UTF_8) } catch (_: Throwable) { "" } }
        } finally {
            k.fill(0)
        }
    }

    fun sealText(key: String, text: String): Map<String, String> {
        val k = unb64(key)
        try {
            return seal(k, text.toByteArray(Charsets.UTF_8))
        } finally {
            k.fill(0)
        }
    }

    /** RFC 6238 2-step code (SHA-1, 6 digits, 30 s) from a base32 secret; "" when it is not one. */
    fun totp(secret: String, atMs: Long = System.currentTimeMillis()): String {
        val alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
        val clean = secret.uppercase().filter { it in alpha }
        if (clean.length < 16) return ""
        val out = java.io.ByteArrayOutputStream()
        var buf = 0
        var bits = 0
        for (ch in clean) {
            buf = ((buf shl 5) or alpha.indexOf(ch)) and 0xffff; bits += 5
            if (bits >= 8) { out.write((buf shr (bits - 8)) and 0xff); bits -= 8 }
        }
        var ctr = atMs / 1000 / 30
        val msg = ByteArray(8)
        for (i in 7 downTo 0) { msg[i] = (ctr and 0xff).toByte(); ctr = ctr shr 8 }
        val mac = Mac.getInstance("HmacSHA1").apply { init(SecretKeySpec(out.toByteArray(), "HmacSHA1")) }.doFinal(msg)
        val o = mac[19].toInt() and 0x0f
        val n = ((mac[o].toInt() and 0x7f) shl 24) or ((mac[o + 1].toInt() and 0xff) shl 16) or
            ((mac[o + 2].toInt() and 0xff) shl 8) or (mac[o + 3].toInt() and 0xff)
        return (n % 1_000_000).toString().padStart(6, '0')
    }
}
