package hoola.kit

// Made by Hoola App Sahayak (v0.319 APP FEATURES). Phone features a screen uses with one call, each the way the stores
// allow it: photos through Android's own Photo Picker (no storage permission at all), shrunk on the phone and sent by the
// outbox (the server re-encodes them, so GPS / camera data never reach anyone); location only while the app is open,
// after a plain explanation and the system dialog; UPI to the business's own UPI ID and the customer's "I have paid"
// with her UPI reference (the business checks its own bank - the app never sees money).

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.location.Location
import android.location.LocationManager
import android.net.Uri
import android.util.LruCache
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.location.LocationManagerCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import java.io.File
import java.util.Locale
import java.util.UUID
import kotlin.coroutines.resume

/** Photos of this app: a picked photo waits on the phone as "local:<file>" until the outbox sends it. */
object Photos {
    private val cache = LruCache<String, ImageBitmap>(24)

    /** The picked photo, at most 1600 px on its long side, as a JPEG in the app's own cache (null = it would not open). */
    fun shrink(ctx: Context, uri: Uri): String? = try {
        val cr = ctx.contentResolver
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        cr.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        var sample = 1
        while (bounds.outWidth / (sample * 2) >= 1600 || bounds.outHeight / (sample * 2) >= 1600) sample *= 2
        val bmp = cr.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample }) }
        if (bmp == null) null else {
            val scale = minOf(1f, 1600f / maxOf(bmp.width, bmp.height))
            val out = if (scale < 1f) Bitmap.createScaledBitmap(bmp, (bmp.width * scale).toInt(), (bmp.height * scale).toInt(), true) else bmp
            val dir = File(ctx.cacheDir, "hoola_up").apply { mkdirs() }
            val f = File(dir, UUID.randomUUID().toString().replace("-", "") + ".jpg")
            f.outputStream().use { out.compress(Bitmap.CompressFormat.JPEG, 85, it) }
            f.absolutePath
        }
    } catch (_: Exception) {
        null
    }

    /** A photo for the screen: a local one from the phone, else the server's copy (signed in), cached. */
    suspend fun load(src: String): ImageBitmap? {
        cache.get(src)?.let { return it }
        val bytes = withContext(Dispatchers.IO) {
            if (src.startsWith("local:")) {
                try { File(src.removePrefix("local:")).readBytes() } catch (_: Exception) { null }
            } else if (src.startsWith("f_")) Cloud.bytes("/files/$src", Auth.token()) else null
        } ?: return null
        val bmp = withContext(Dispatchers.Default) { BitmapFactory.decodeByteArray(bytes, 0, bytes.size) } ?: return null
        val img = bmp.asImageBitmap()
        cache.put(src, img)
        return img
    }
}

/** A photo from the app's server (file id) or one still on this phone ("local:..."). */
@Composable
fun RemotePhoto(src: String, modifier: Modifier = Modifier, description: String = "") {
    val img by produceState<ImageBitmap?>(null, src) { value = Photos.load(src) }
    Box(modifier.clip(RoundedCornerShape(H.look.radius * 0.7f)).background(H.c.tint), contentAlignment = Alignment.Center) {
        val i = img
        if (i != null) Image(i, contentDescription = description.ifEmpty { null }, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxWidth().height(180.dp))
        else HIcon("image", tint = H.c.muted)
    }
}

/** A photo box for a form: the system Photo Picker (no permission), the photo shrunk and kept until the outbox sends it.
 *  The key is the list's photo field key (e.g. "photo"). */
@Composable
fun PhotoField(label: String, key: String) {
    val c = ctx()
    val scope = rememberCoroutineScope()
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) scope.launch {
            val p = withContext(Dispatchers.IO) { Photos.shrink(c, uri) }
            if (p != null) AppState.form[key] = "local:$p" else Act.toast(c, Strings.photoFailed)
        }
    }
    val v = AppState.form[key].orEmpty()
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Label(label)
        if (v.isNotEmpty()) RemotePhoto(v, Modifier.fillMaxWidth().height(180.dp), label)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Btn(if (v.isEmpty()) Strings.addPhoto else Strings.changePhoto, kind = BtnKind.Tonal, icon = "camera", small = true) {
                pick.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            }
            if (v.isNotEmpty()) Btn(Strings.remove, kind = BtnKind.Ghost, small = true) { AppState.form.remove(key) }
        }
    }
}

/** Where the phone is, only while the app is open (approximate is enough for an address). */
object Places {
    fun allowed(ctx: Context): Boolean =
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED

    @SuppressLint("MissingPermission")
    suspend fun here(ctx: Context): String? {
        if (!allowed(ctx)) return null
        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as? LocationManager ?: return null
        val provider = when {
            lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
            lm.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
            else -> return null
        }
        val loc: Location? = try {
            withTimeoutOrNull(15_000) {
                suspendCancellableCoroutine { cont ->
                    val signal: android.os.CancellationSignal? = null
                    LocationManagerCompat.getCurrentLocation(lm, provider, signal, ContextCompat.getMainExecutor(ctx),
                        androidx.core.util.Consumer<Location?> { l -> if (cont.isActive) cont.resume(l) })
                }
            } ?: lm.getLastKnownLocation(provider)
        } catch (_: SecurityException) {
            null
        } catch (_: Exception) {
            null
        }
        return loc?.let { String.format(Locale.US, "%.6f,%.6f", it.latitude, it.longitude) }
    }
}

/** "Use my location" for a form: a plain explanation first, then Android's own dialog, then "lat,lng" in the field. */
@Composable
fun LocationField(label: String, key: String) {
    val c = ctx()
    val scope = rememberCoroutineScope()
    var ask by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    val find: () -> Unit = {
        busy = true
        scope.launch {
            val at = Places.here(c)
            busy = false
            if (at != null) AppState.form[key] = at else Act.toast(c, Strings.locationFailed)
        }
    }
    val perm = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { res ->
        if (res.values.any { it }) find() else Act.toast(c, Strings.locationDenied)
    }
    val v = AppState.form[key].orEmpty()
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Label(label)
        if (v.isNotEmpty()) Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Small(v)
            Btn(Strings.openMap, kind = BtnKind.Ghost, small = true) { Act.maps(c, v) }
        }
        Btn(if (busy) Strings.finding else Strings.useMyLocation, kind = BtnKind.Tonal, icon = "pin", small = true, enabled = !busy) {
            if (Places.allowed(c)) find() else ask = true
        }
    }
    if (ask) AlertDialog(
        onDismissRequest = { ask = false },
        title = { Text(Strings.locationTitle) },
        text = { Text(Strings.locationWhy) },
        confirmButton = {
            TextButton(onClick = {
                ask = false
                perm.launch(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION, Manifest.permission.ACCESS_FINE_LOCATION))
            }) { Text(Strings.cont) }
        },
        dismissButton = { TextButton(onClick = { ask = false }) { Text(Strings.later) } },
    )
}

/** For the customer's own UPI order: pay in her UPI app (to the business's own UPI ID), then say so with the UPI
 *  reference. The order then reads "Customer says paid" until the business checks its bank and marks it Verified. */
@Composable
fun PaidBox(coll: String, row: Item) {
    val c = ctx()
    var ask by remember { mutableStateOf(false) }
    var utr by remember { mutableStateOf("") }
    val total = row.n("total")
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Btn(Strings.payUpi + if (total > 0) " " + rupees(total) else "", kind = BtnKind.Primary, icon = "pay", small = true) {
            Act.payUpi(c, total, "Order " + row.id.takeLast(6))
        }
        Btn(Strings.iPaid, kind = BtnKind.Tonal, small = true) { ask = true }
    }
    if (ask) AlertDialog(
        onDismissRequest = { ask = false },
        title = { Text(Strings.iPaid) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(Strings.utrWhy)
                OutlinedTextField(value = utr, onValueChange = { v -> utr = v.filter { it.isLetterOrDigit() }.take(24) },
                    label = { Text(Strings.utr) }, singleLine = true)
            }
        },
        confirmButton = {
            TextButton(enabled = utr.length >= 6, onClick = {
                ask = false
                Db.paid(coll, row.id, utr)
                Act.toast(c, Strings.paidSaid)
            }) { Text(Strings.cont) }
        },
        dismissButton = { TextButton(onClick = { ask = false }) { Text(Strings.later) } },
    )
}
