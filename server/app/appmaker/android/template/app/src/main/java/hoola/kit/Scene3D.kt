package hoola.kit

// Made by Hoola App Sahayak (v0.140). The app's own 3D scene from its design DNA: Hoola's server renders the same scene the
// approved prototype drew (three.js, lights, materials) into assets/scenes/<name>.png; natively it stays alive - it
// floats, breathes and turns a little under the finger. No 3D engine, no network, works on every phone.

import android.graphics.BitmapFactory
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics

/** The app's 3D scene NAME (from its design DNA). shape = "square" | "tall" | "wide" | "short". */
@Composable
fun Scene3D(name: String, modifier: Modifier = Modifier, shape: String = "square", description: String = "") {
    val ctx = LocalContext.current
    val img: ImageBitmap? = remember(name) {
        try {
            ctx.assets.open("scenes/$name.png").use { BitmapFactory.decodeStream(it) }?.asImageBitmap()
        } catch (e: Exception) {
            null
        }
    }
    val ratio = when (shape) {
        "tall" -> 0.75f
        "wide" -> 1.6f
        "short" -> 2f
        else -> 1f
    }
    val t = rememberInfiniteTransition(label = "scene3d")
    val lift by t.animateFloat(
        initialValue = -1f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2800, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "lift",
    )
    val sway by t.animateFloat(
        initialValue = -1f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(4600, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "sway",
    )
    var dragX by remember { mutableFloatStateOf(0f) }
    var dragY by remember { mutableFloatStateOf(0f) }
    val c = H.c
    Box(
        modifier
            .fillMaxWidth()
            .aspectRatio(ratio)
            .clip(RoundedCornerShape(H.look.radius))
            .background(Brush.radialGradient(listOf(c.tint, c.bg)))
            .pointerInput(name) {
                detectDragGestures(onDragEnd = { dragX = 0f; dragY = 0f }) { change, amount ->
                    change.consume()
                    dragX = (dragX + amount.x / 12f).coerceIn(-18f, 18f)
                    dragY = (dragY - amount.y / 12f).coerceIn(-14f, 14f)
                }
            }
            .semantics { contentDescription = description.ifBlank { name } },
        contentAlignment = Alignment.Center,
    ) {
        if (img != null) {
            Image(
                bitmap = img,
                contentDescription = null,
                modifier = Modifier.fillMaxSize().graphicsLayer {
                    translationY = lift * 6f * density
                    rotationZ = sway * 2.5f
                    rotationY = dragX + sway * 4f
                    rotationX = dragY
                    cameraDistance = 14f * density
                    val s = 1f + (lift + 1f) * 0.012f
                    scaleX = s
                    scaleY = s
                },
                contentScale = ContentScale.Fit,
            )
        }
    }
}
