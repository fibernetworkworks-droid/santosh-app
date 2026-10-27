package hoola.kit

// Made by Hoola App Sahayak. HoolaKit is fixed code owned by Newtika; generated screens only use it.

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** The colours of one mode (light or dark), exactly the design tokens of the approved design. */
@Immutable
data class HoolaColors(
    val bg: Color, val surface: Color, val ink: Color, val muted: Color, val line: Color,
    val primary: Color, val onPrimary: Color, val accent: Color, val onAccent: Color,
    val primaryText: Color, val accentText: Color, val tint: Color, val tint2: Color,
    val dark: Boolean,
)

/** Everything the design decided: colours of both modes, shapes, fonts and the structure (navigation, FAB, cards ...). */
@Immutable
data class HoolaLook(
    val light: HoolaColors,
    val dark: HoolaColors,
    val mode: String,            // light | dark | both
    val radius: Dp,
    val buttonRadius: Dp,
    val card: String,            // elevated | outlined | filled | glass | block | neumorphic | mesh | image_overlay | stacked | ticket
    val button: String,          // rounded | pill | square | chunky | gradient | soft
    val header: String,          // large_title | center_title | brand_bar | greeting | search_bar | ...
    val nav: String,             // bar | bar_labels | bar_minimal | floating_pill | drawer | drawer_bar | rail | top_tabs | ...
    val fab: String,             // none | regular | small | large | extended | speed_dial | menu | docked
    val transition: String,      // push | fade_through | axis_x | axis_y | zoom | ...
    val headFont: FontFamily,
    val bodyFont: FontFamily,
    val language: String,        // en | hi | mr | hinglish
)

@Immutable
data class HoolaType(
    val display: TextStyle, val h1: TextStyle, val h2: TextStyle, val title: TextStyle, val body: TextStyle,
    val small: TextStyle, val label: TextStyle, val price: TextStyle,
)

val LocalLook = staticCompositionLocalOf<HoolaLook> { error("HoolaTheme missing") }
val LocalColors = staticCompositionLocalOf<HoolaColors> { error("HoolaTheme missing") }
val LocalType = staticCompositionLocalOf<HoolaType> { error("HoolaTheme missing") }

/** Short names the screens use: H.c.primary, H.t.title, H.look.radius. */
object H {
    val c: HoolaColors @Composable get() = LocalColors.current
    val t: HoolaType @Composable get() = LocalType.current
    val look: HoolaLook @Composable get() = LocalLook.current
}

fun typeOf(look: HoolaLook, c: HoolaColors): HoolaType {
    val hf = look.headFont
    val bf = look.bodyFont
    return HoolaType(
        display = TextStyle(fontFamily = hf, fontWeight = FontWeight.Bold, fontSize = 32.sp, lineHeight = 38.sp, color = c.ink),
        h1 = TextStyle(fontFamily = hf, fontWeight = FontWeight.Bold, fontSize = 24.sp, lineHeight = 30.sp, color = c.ink),
        h2 = TextStyle(fontFamily = hf, fontWeight = FontWeight.Bold, fontSize = 19.sp, lineHeight = 25.sp, color = c.ink),
        title = TextStyle(fontFamily = hf, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 22.sp, color = c.ink),
        body = TextStyle(fontFamily = bf, fontWeight = FontWeight.Normal, fontSize = 15.sp, lineHeight = 22.sp, color = c.ink),
        small = TextStyle(fontFamily = bf, fontWeight = FontWeight.Normal, fontSize = 13.sp, lineHeight = 18.sp, color = c.muted),
        label = TextStyle(fontFamily = bf, fontWeight = FontWeight.SemiBold, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.6.sp, color = c.muted),
        price = TextStyle(fontFamily = hf, fontWeight = FontWeight.Bold, fontSize = 17.sp, lineHeight = 22.sp, color = c.primaryText),
    )
}

@Composable
fun HoolaTheme(look: HoolaLook, content: @Composable () -> Unit) {
    val sysDark = isSystemInDarkTheme()
    val dark = when (look.mode) { "dark" -> true; "light" -> false; else -> sysDark }
    val c = if (dark) look.dark else look.light
    val scheme = if (dark) darkColorScheme(
        primary = c.primary, onPrimary = c.onPrimary, secondary = c.accent, onSecondary = c.onAccent,
        background = c.bg, onBackground = c.ink, surface = c.surface, onSurface = c.ink, outline = c.line,
        surfaceVariant = c.tint, onSurfaceVariant = c.muted,
    ) else lightColorScheme(
        primary = c.primary, onPrimary = c.onPrimary, secondary = c.accent, onSecondary = c.onAccent,
        background = c.bg, onBackground = c.ink, surface = c.surface, onSurface = c.ink, outline = c.line,
        surfaceVariant = c.tint, onSurfaceVariant = c.muted,
    )
    CompositionLocalProvider(LocalLook provides look, LocalColors provides c, LocalType provides typeOf(look, c)) {
        MaterialTheme(colorScheme = scheme, content = content)
    }
}

fun hex(s: String): Color {
    val v = s.removePrefix("#")
    return try {
        when (v.length) {
            6 -> Color(("FF$v").toLong(16))
            8 -> Color(v.toLong(16))
            else -> Color.Gray
        }
    } catch (_: NumberFormatException) { Color.Gray }
}

val Space4: Dp = 4.dp
val Space8: Dp = 8.dp
val Space12: Dp = 12.dp
val Space16: Dp = 16.dp
val Space24: Dp = 24.dp
