package com.newtika.santosh

import android.app.Activity
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.MediaStore
import androidx.core.content.FileProvider
import java.io.File

/** v0.63 Hoola Motion: hand a finished video to WhatsApp / Instagram (Android share sheet), or save it to the gallery. */
object MediaShare {
    fun share(act: Activity, path: String, mime: String, title: String, pkg: String = ""): String? {
        val f = File(path)
        if (!f.exists() || !f.canonicalPath.startsWith(act.cacheDir.canonicalPath)) return "File nahi mili"
        val uri = FileProvider.getUriForFile(act, act.packageName + ".hoolafiles", f)
        val send = Intent(Intent.ACTION_SEND).setType(mime).putExtra(Intent.EXTRA_STREAM, uri)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        if (pkg.isNotBlank()) {          // v0.159 straight into WhatsApp / Instagram / YouTube; not installed -> the normal sheet
            try {
                act.startActivity(Intent(send).setPackage(pkg))
                return null
            } catch (e: Exception) {
            }
        }
        act.startActivity(Intent.createChooser(send, title.ifBlank { "Share" }))
        return null
    }

    /** v0.118 Brand Sahayak: a final poster into Pictures/Hoola (Android 10+ needs no permission for this). */
    fun saveImage(ctx: Context, path: String, name: String): String? {
        val f = File(path)
        if (!f.exists()) return "File nahi mili"
        if (Build.VERSION.SDK_INT < 29) return "Is phone par 'Share' se save kijiye"
        val mime = if (name.lowercase().endsWith(".png")) "image/png" else "image/jpeg"
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, name.ifBlank { "hoola.png" })
            put(MediaStore.Images.Media.MIME_TYPE, mime)
            put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/Hoola")
            put(MediaStore.Images.Media.IS_PENDING, 1)
        }
        val r = ctx.contentResolver
        val uri = r.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return "Gallery mein jagah nahi mili"
        return try {
            r.openOutputStream(uri)?.use { out -> f.inputStream().use { it.copyTo(out) } }
            values.clear(); values.put(MediaStore.Images.Media.IS_PENDING, 0)
            r.update(uri, values, null, null)
            null
        } catch (e: Exception) {
            r.delete(uri, null, null)
            "Save nahi ho paya"
        }
    }

    /** Movies/Hoola in the gallery (Android 10+ needs no permission for this). */
    fun saveVideo(ctx: Context, path: String, name: String): String? {
        val f = File(path)
        if (!f.exists()) return "File nahi mili"
        if (Build.VERSION.SDK_INT < 29) return "Is phone par 'Share' se save kijiye"
        val values = ContentValues().apply {
            put(MediaStore.Video.Media.DISPLAY_NAME, name.ifBlank { "hoola.mp4" })
            put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
            put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/Hoola")
            put(MediaStore.Video.Media.IS_PENDING, 1)
        }
        val r = ctx.contentResolver
        val uri = r.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values) ?: return "Gallery mein jagah nahi mili"
        return try {
            r.openOutputStream(uri)?.use { out -> f.inputStream().use { it.copyTo(out) } }
            values.clear(); values.put(MediaStore.Video.Media.IS_PENDING, 0)
            r.update(uri, values, null, null)
            null
        } catch (e: Exception) {
            r.delete(uri, null, null)
            "Save nahi ho paya"
        }
    }
}
