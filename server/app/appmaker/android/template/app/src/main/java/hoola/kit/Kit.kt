package hoola.kit

// Made by Hoola App Sahayak. The native twin of the web app kit the design was approved on: generated screens are
// written ONLY with these blocks (plus plain Compose foundation / material3), so every app keeps its design system.

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// ---------------------------------------------------------------- page

/** A whole screen: app bar + scrolling body (+ optional sticky bottom bar). `back` = opened from another screen. */
@Composable
fun Page(
    title: String,
    back: Boolean = true,
    large: Boolean = false,
    subtitle: String = "",
    actions: @Composable RowScope.() -> Unit = {},
    bottomBar: (@Composable RowScope.() -> Unit)? = null,
    body: LazyListScope.() -> Unit,
) {
    val c = H.c
    Column(Modifier.fillMaxSize().background(c.bg)) {
        AppBar(title, back, large, subtitle, actions)
        if (AppData.demo) DemoNote()
        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 96.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            content = body,
        )
        if (bottomBar != null) {
            Row(
                Modifier.fillMaxWidth().background(c.surface).border(BorderStroke(1.dp, c.line))
                    .padding(horizontal = 16.dp, vertical = 10.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
                content = bottomBar,
            )
        }
    }
}

@Composable
fun AppBar(title: String, back: Boolean = true, large: Boolean = false, subtitle: String = "", actions: @Composable RowScope.() -> Unit = {}) {
    val c = H.c
    val nav = LocalNav.current
    val center = H.look.header == "center_title"
    Column(Modifier.fillMaxWidth().background(c.bg).padding(horizontal = 8.dp, vertical = 6.dp)) {
        Row(Modifier.fillMaxWidth().heightIn(min = 52.dp), verticalAlignment = Alignment.CenterVertically) {
            if (back && nav.canBack) {
                IconBtn("arrow-l", Strings.back) { nav.back() }
            } else if (nav.hasDrawer) {
                IconBtn("menu", Strings.menu) { nav.openDrawer() }
            } else Spacer(Modifier.width(8.dp))
            Box(Modifier.weight(1f), contentAlignment = if (center) Alignment.Center else Alignment.CenterStart) {
                if (!large) Text(title, style = H.t.h2, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Row(verticalAlignment = Alignment.CenterVertically, content = actions)
        }
        if (large) {
            Text(title, style = H.t.h1, modifier = Modifier.padding(start = 8.dp, top = 2.dp, bottom = 2.dp))
        }
        if (subtitle.isNotEmpty()) Text(subtitle, style = H.t.small, modifier = Modifier.padding(start = 8.dp, bottom = 4.dp))
    }
}

@Composable
private fun DemoNote() {
    val c = H.c
    Text(
        Strings.demo, style = H.t.small.copy(color = c.ink),
        modifier = Modifier.fillMaxWidth().background(c.tint2).padding(horizontal = 16.dp, vertical = 6.dp),
    )
}

// ---------------------------------------------------------------- text

@Composable fun Display(text: String, modifier: Modifier = Modifier) = Text(text, style = H.t.display, modifier = modifier)
@Composable fun H1(text: String, modifier: Modifier = Modifier) = Text(text, style = H.t.h1, modifier = modifier)
@Composable fun H2(text: String, modifier: Modifier = Modifier) = Text(text, style = H.t.h2, modifier = modifier)
@Composable fun Title(text: String, modifier: Modifier = Modifier, maxLines: Int = 2) =
    Text(text, style = H.t.title, modifier = modifier, maxLines = maxLines, overflow = TextOverflow.Ellipsis)
@Composable fun Body(text: String, modifier: Modifier = Modifier, color: Color = Color.Unspecified) =
    Text(text, style = H.t.body, modifier = modifier, color = if (color == Color.Unspecified) H.c.ink else color)
@Composable fun Small(text: String, modifier: Modifier = Modifier, maxLines: Int = 3) =
    Text(text, style = H.t.small, modifier = modifier, maxLines = maxLines, overflow = TextOverflow.Ellipsis)
@Composable fun Label(text: String, modifier: Modifier = Modifier) = Text(text.uppercase(), style = H.t.label, modifier = modifier)

@Composable
fun Price(amount: Double, modifier: Modifier = Modifier, old: Double = 0.0, big: Boolean = false) {
    Row(modifier, verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(rupees(amount), style = if (big) H.t.h1.copy(color = H.c.primaryText) else H.t.price)
        if (old > amount) Text(rupees(old), style = H.t.small.copy(textDecoration = TextDecoration.LineThrough))
    }
}

/** Something the owner has not told yet: shown as a clear "[...]" chip, never invented. */
@Composable
fun Blank(what: String, modifier: Modifier = Modifier) {
    Text(
        "[$what]", style = H.t.small.copy(color = H.c.accentText, fontWeight = FontWeight.SemiBold),
        modifier = modifier.background(H.c.tint, RoundedCornerShape(6.dp)).padding(horizontal = 6.dp, vertical = 2.dp),
    )
}

/** Text of a fact, or a [blank] when she hasn't given it. */
@Composable
fun FactText(key: String, what: String, style: TextStyle = H.t.body) {
    val v = AppData.facts.s(key)
    if (v.isNotEmpty()) Text(v, style = style) else Blank(what)
}

// ---------------------------------------------------------------- surfaces

/** The design's card (elevated / outlined / filled / glass / block / neumorphic / mesh / ticket ...). */
@Composable
fun HCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    tint: Boolean = false,
    padding: Dp = 14.dp,
    content: @Composable ColumnScope.() -> Unit,
) {
    val c = H.c
    val look = H.look
    val shape = RoundedCornerShape(look.radius)
    var m = modifier.fillMaxWidth()
    m = when (look.card) {
        "elevated", "stacked" -> m.shadow(if (c.dark) 0.dp else 3.dp, shape).background(c.surface, shape)
        "outlined", "ticket" -> m.background(c.surface, shape).border(1.dp, c.line, shape)
        "filled" -> m.background(c.tint, shape)
        "glass" -> m.background(c.surface.copy(alpha = 0.72f), shape).border(1.dp, Color.White.copy(alpha = 0.35f), shape)
        "block" -> m.background(c.surface, shape).border(2.dp, c.ink, shape)
        "neumorphic" -> m.shadow(6.dp, shape, ambientColor = c.line, spotColor = c.line).background(c.surface, shape)
        "mesh" -> m.background(Brush.linearGradient(listOf(c.tint, c.surface, c.tint2)), shape)
        else -> m.shadow(if (c.dark) 0.dp else 2.dp, shape).background(c.surface, shape)
    }
    if (tint) m = m.background(c.tint, shape)
    m = m.clip(shape)
    if (onClick != null) m = m.clickable(role = Role.Button, onClick = onClick)
    Column(m.padding(padding), verticalArrangement = Arrangement.spacedBy(6.dp), content = content)
}

/** Big gradient promo / hero block. */
@Composable
fun Banner(title: String, sub: String = "", cta: String = "", onClick: (() -> Unit)? = null) {
    val c = H.c
    val shape = RoundedCornerShape(H.look.radius)
    Column(
        Modifier.fillMaxWidth().clip(shape).background(Brush.linearGradient(listOf(c.primary, c.accent)))
            .let { if (onClick != null) it.clickable(onClick = onClick) else it }.padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(title, style = H.t.h2.copy(color = c.onPrimary))
        if (sub.isNotEmpty()) Text(sub, style = H.t.body.copy(color = c.onPrimary.copy(alpha = 0.9f)))
        if (cta.isNotEmpty()) Text(cta, style = H.t.title.copy(color = c.onPrimary),
            modifier = Modifier.padding(top = 4.dp).background(Color.White.copy(alpha = 0.22f), RoundedCornerShape(50)).padding(horizontal = 14.dp, vertical = 8.dp))
    }
}

/** Placeholder art tile (no photos yet): an icon on a soft tint. */
@Composable
fun Ph(icon: String, modifier: Modifier = Modifier, ratio: Float = 1.3f, variant: Int = 0) {
    val c = H.c
    val bg = when (variant % 4) { 0 -> c.tint; 1 -> c.tint2; 2 -> c.primary.copy(alpha = 0.14f); else -> c.accent.copy(alpha = 0.16f) }
    Box(modifier.fillMaxWidth().aspectRatio(ratio).clip(RoundedCornerShape(H.look.radius * 0.8f)).background(bg), contentAlignment = Alignment.Center) {
        HIcon(icon, size = 34.dp, tint = c.primaryText)
    }
}

// ---------------------------------------------------------------- icons + buttons

@Composable
fun HIcon(name: String, modifier: Modifier = Modifier, size: Dp = 22.dp, tint: Color = Color.Unspecified, description: String? = null) {
    Icon(HIcons.get(name), contentDescription = description, modifier = modifier.size(size), tint = if (tint == Color.Unspecified) H.c.ink else tint)
}

@Composable
fun IconBtn(icon: String, description: String, badge: Int = 0, tint: Color = Color.Unspecified, onClick: () -> Unit) {
    Box(
        Modifier.size(48.dp).clip(CircleShape).clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) {
        HIcon(icon, tint = tint)
        if (badge > 0) Text(
            "$badge", style = TextStyle(fontSize = 10.sp, fontWeight = FontWeight.Bold, color = H.c.onAccent),
            modifier = Modifier.align(Alignment.TopEnd).padding(top = 6.dp, end = 6.dp).background(H.c.accent, CircleShape).padding(horizontal = 5.dp, vertical = 1.dp),
        )
    }
}

enum class BtnKind { Primary, Accent, Tonal, Outline, Ghost, Danger }

@Composable
fun Btn(
    text: String,
    modifier: Modifier = Modifier,
    kind: BtnKind = BtnKind.Primary,
    icon: String? = null,
    enabled: Boolean = true,
    small: Boolean = false,
    onClick: () -> Unit,
) {
    val c = H.c
    val look = H.look
    val shape = when (look.button) {
        "pill" -> RoundedCornerShape(50)
        "square" -> RoundedCornerShape(4.dp)
        "chunky" -> RoundedCornerShape(look.buttonRadius)
        else -> RoundedCornerShape(look.buttonRadius)
    }
    val (bg, fg, border) = when (kind) {
        BtnKind.Primary -> Triple(c.primary, c.onPrimary, null)
        BtnKind.Accent -> Triple(c.accent, c.onAccent, null)
        BtnKind.Tonal -> Triple(c.tint, c.primaryText, null)
        BtnKind.Outline -> Triple(Color.Transparent, c.primaryText, c.line)
        BtnKind.Ghost -> Triple(Color.Transparent, c.primaryText, null)
        BtnKind.Danger -> Triple(Color(0xFFC62828), Color.White, null)
    }
    var m = modifier.heightIn(min = if (small) 40.dp else 48.dp).clip(shape)
    m = if (look.button == "gradient" && kind == BtnKind.Primary) m.background(Brush.horizontalGradient(listOf(c.primary, c.accent)), shape)
    else m.background(if (enabled) bg else bg.copy(alpha = 0.4f), shape)
    if (border != null) m = m.border(1.dp, border, shape)
    if (look.button == "chunky" && kind == BtnKind.Primary) m = m.border(2.dp, c.ink, shape)
    m = m.clickable(enabled = enabled, role = Role.Button, onClick = onClick).padding(horizontal = if (small) 14.dp else 18.dp, vertical = if (small) 8.dp else 12.dp)
    Row(m, horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
        if (icon != null) { HIcon(icon, size = 18.dp, tint = fg); Spacer(Modifier.width(8.dp)) }
        Text(text, style = H.t.title.copy(color = if (enabled) fg else fg.copy(alpha = 0.6f), fontSize = if (small) 14.sp else 16.sp), maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

/** ADD that turns into a - qty + stepper for a record in the cart. */
@Composable
fun AddButton(itemId: String) {
    val q = AppState.qty(itemId)
    if (q == 0) Btn(Strings.add, small = true, kind = BtnKind.Tonal) { AppState.add(itemId) }
    else Stepper(q) { AppState.setQty(itemId, it) }
}

@Composable
fun Stepper(value: Int, min: Int = 0, max: Int = 99, onChange: (Int) -> Unit) {
    val c = H.c
    Row(
        Modifier.clip(RoundedCornerShape(50)).border(1.dp, c.line, RoundedCornerShape(50)),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconBtn("minus", Strings.less) { if (value > min) onChange(value - 1) }
        Text("$value", style = H.t.title, modifier = Modifier.widthIn(min = 22.dp), textAlign = TextAlign.Center)
        IconBtn("plus", Strings.more) { if (value < max) onChange(value + 1) }
    }
}

// ---------------------------------------------------------------- lists, chips, inputs

@Composable
fun ListRow(title: String, sub: String = "", icon: String? = null, trailing: String = "", chevron: Boolean = true, onClick: (() -> Unit)? = null) {
    val c = H.c
    Row(
        Modifier.fillMaxWidth().heightIn(min = 56.dp).clip(RoundedCornerShape(H.look.radius * 0.6f))
            .let { if (onClick != null) it.clickable(role = Role.Button, onClick = onClick) else it }.padding(vertical = 8.dp, horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (icon != null) Box(Modifier.size(40.dp).background(c.tint, RoundedCornerShape(12.dp)), contentAlignment = Alignment.Center) {
            HIcon(icon, size = 20.dp, tint = c.primaryText)
        }
        Column(Modifier.weight(1f)) {
            Title(title, maxLines = 1)
            if (sub.isNotEmpty()) Small(sub, maxLines = 2)
        }
        if (trailing.isNotEmpty()) Text(trailing, style = H.t.title.copy(color = c.primaryText))
        if (onClick != null && chevron) HIcon("chev-r", size = 18.dp, tint = c.muted)
    }
}

@Composable
fun SectionHeader(title: String, action: String = "", onAction: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth().padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(title, style = H.t.h2, modifier = Modifier.weight(1f))
        if (action.isNotEmpty() && onAction != null) Text(
            action, style = H.t.title.copy(color = H.c.primaryText, fontSize = 14.sp),
            modifier = Modifier.clip(RoundedCornerShape(8.dp)).clickable(onClick = onAction).padding(8.dp),
        )
    }
}

@Composable
fun HDivider() = Box(Modifier.fillMaxWidth().height(1.dp).background(H.c.line))

@Composable
fun Chip(text: String, selected: Boolean = false, icon: String? = null, onClick: () -> Unit) {
    val c = H.c
    Row(
        Modifier.heightIn(min = 40.dp).clip(RoundedCornerShape(50)).background(if (selected) c.primary else c.tint, RoundedCornerShape(50))
            .clickable(role = Role.Button, onClick = onClick).padding(horizontal = 14.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        if (icon != null) HIcon(icon, size = 16.dp, tint = if (selected) c.onPrimary else c.primaryText)
        Text(text, style = H.t.title.copy(fontSize = 14.sp, color = if (selected) c.onPrimary else c.primaryText), maxLines = 1)
    }
}

/** A swipe row of chips; one choice remembered under `group` (AppState.picks). */
@Composable
fun Chips(options: List<String>, group: String, onPick: (String) -> Unit = {}) {
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        options.forEach { o ->
            Chip(o, selected = AppState.picks[group] == o) {
                if (AppState.picks[group] == o) AppState.picks.remove(group) else AppState.picks[group] = o
                onPick(o)
            }
        }
    }
}

@Composable
fun Segmented(options: List<String>, group: String) {
    val c = H.c
    val chosen = AppState.picks[group] ?: options.firstOrNull() ?: ""
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(50)).background(c.tint).padding(4.dp)) {
        options.forEach { o ->
            val on = o == chosen
            Box(
                Modifier.weight(1f).heightIn(min = 40.dp).clip(RoundedCornerShape(50)).background(if (on) c.surface else Color.Transparent)
                    .clickable(role = Role.Tab) { AppState.picks[group] = o },
                contentAlignment = Alignment.Center,
            ) { Text(o, style = H.t.title.copy(fontSize = 14.sp, color = if (on) c.ink else c.muted)) }
        }
    }
}

/** A text box bound to AppState.form[key]. There is no password / PIN / card field in the kit on purpose. */
@Composable
fun Field(label: String, key: String, modifier: Modifier = Modifier, keyboard: KeyboardType = KeyboardType.Text, lines: Int = 1, hint: String = "") {
    val c = H.c
    OutlinedTextField(
        value = AppState.form[key] ?: "",
        onValueChange = { AppState.form[key] = it.take(500) },
        label = { Text(label) },
        placeholder = { if (hint.isNotEmpty()) Text(hint) },
        modifier = modifier.fillMaxWidth(),
        singleLine = lines == 1,
        minLines = lines,
        keyboardOptions = KeyboardOptions(keyboardType = keyboard),
        shape = RoundedCornerShape(H.look.radius * 0.7f),
        colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = c.primary, unfocusedBorderColor = c.line, focusedLabelColor = c.primaryText),
    )
}

@Composable
fun SearchBox(hint: String = Strings.search, modifier: Modifier = Modifier) {
    val c = H.c
    Row(
        modifier.fillMaxWidth().heightIn(min = 48.dp).clip(RoundedCornerShape(50)).background(c.tint).padding(horizontal = 14.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        HIcon("search", size = 20.dp, tint = c.muted)
        androidx.compose.foundation.text.BasicTextField(
            value = AppState.query.value, onValueChange = { AppState.query.value = it.take(80) },
            textStyle = H.t.body, singleLine = true, modifier = Modifier.weight(1f),
            decorationBox = { inner -> if (AppState.query.value.isEmpty()) Text(hint, style = H.t.body.copy(color = c.muted)); inner() },
        )
    }
}

@Composable
fun CheckRow(text: String, key: String) {
    val on = AppState.form[key] == "1"
    Row(Modifier.fillMaxWidth().clickable(role = Role.Checkbox) { AppState.form[key] = if (on) "" else "1" }.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked = on, onCheckedChange = { AppState.form[key] = if (it) "1" else "" }, colors = CheckboxDefaults.colors(checkedColor = H.c.primary))
        Body(text)
    }
}

@Composable
fun SwitchRow(text: String, key: String, sub: String = "") {
    val on = AppState.form[key] == "1"
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) { Title(text); if (sub.isNotEmpty()) Small(sub) }
        Switch(checked = on, onCheckedChange = { AppState.form[key] = if (it) "1" else "" },
            colors = SwitchDefaults.colors(checkedTrackColor = H.c.primary))
    }
}

/** OTP boxes (display only: the phone's own SMS / WhatsApp OTP autofill fills them in the live version). */
@Composable
fun OtpBoxes(length: Int = 6) {
    val c = H.c
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        repeat(length) { Box(Modifier.size(44.dp).border(1.5.dp, c.line, RoundedCornerShape(10.dp))) }
    }
}

// ---------------------------------------------------------------- display

@Composable
fun Pill(text: String, kind: String = "info") {
    val (bg, fg) = when (kind) {
        "ok" -> Color(0xFF1E9E5A).copy(alpha = 0.15f) to Color(0xFF14713F)
        "warn" -> Color(0xFFD99A00).copy(alpha = 0.18f) to Color(0xFF7A5600)
        "bad" -> Color(0xFFD93A3A).copy(alpha = 0.15f) to Color(0xFFA32020)
        else -> H.c.tint to H.c.primaryText
    }
    Text(text, style = H.t.label.copy(color = fg, letterSpacing = 0.sp), modifier = Modifier.background(bg, RoundedCornerShape(50)).padding(horizontal = 10.dp, vertical = 4.dp))
}

@Composable
fun Kpi(value: String, label: String, modifier: Modifier = Modifier) {
    HCard(modifier, padding = 12.dp) {
        Text(value, style = H.t.h1.copy(fontSize = 22.sp))
        Small(label, maxLines = 2)
    }
}

/** Two equal columns (or more) without lazy nesting: good for KPI tiles and product grids. */
@Composable
fun <T> Grid(items: List<T>, columns: Int = 2, gap: Dp = 12.dp, cell: @Composable (T) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(gap)) {
        items.chunked(columns).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(gap)) {
                row.forEach { Box(Modifier.weight(1f)) { cell(it) } }
                repeat(columns - row.size) { Spacer(Modifier.weight(1f)) }
            }
        }
    }
}

/** Horizontal swipe row of cards of a fixed width. */
@Composable
fun <T> Rail(items: List<T>, width: Dp = 160.dp, cell: @Composable (T) -> Unit) {
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        items.forEach { Box(Modifier.width(width)) { cell(it) } }
    }
}

@Composable
fun KeyValues(rows: List<Pair<String, String>>) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        rows.forEach { (k, v) ->
            Row { Text(k, style = H.t.small, modifier = Modifier.weight(0.42f)); Text(v, style = H.t.body, modifier = Modifier.weight(0.58f)) }
        }
    }
}

@Composable
fun Meter(fraction: Float, modifier: Modifier = Modifier) {
    val c = H.c
    Box(modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(50)).background(c.tint)) {
        Box(Modifier.fillMaxWidth(fraction.coerceIn(0f, 1f)).height(8.dp).background(Brush.horizontalGradient(listOf(c.primary, c.accent))))
    }
}

@Composable
fun Ring(fraction: Float, label: String, size: Dp = 96.dp) {
    val c = H.c
    Box(Modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val w = 10.dp.toPx()
            drawArc(c.tint, -90f, 360f, false, style = Stroke(w))
            drawArc(c.primary, -90f, 360f * fraction.coerceIn(0f, 1f), false, style = Stroke(w, cap = StrokeCap.Round))
        }
        Text(label, style = H.t.title)
    }
}

@Composable
fun BarChart(values: List<Float>, labels: List<String> = emptyList(), height: Dp = 140.dp) {
    val c = H.c
    val max = (values.maxOrNull() ?: 1f).coerceAtLeast(0.0001f)
    Column {
        Canvas(Modifier.fillMaxWidth().height(height)) {
            if (values.isEmpty()) return@Canvas
            val gap = 8.dp.toPx()
            val bw = (size.width - gap * (values.size - 1)) / values.size
            values.forEachIndexed { i, v ->
                val h = size.height * (v / max)
                drawRoundRect(
                    brush = Brush.verticalGradient(listOf(c.primary, c.accent)),
                    topLeft = Offset(i * (bw + gap), size.height - h), size = Size(bw, h), cornerRadius = CornerRadius(6.dp.toPx()),
                )
            }
        }
        if (labels.isNotEmpty()) Row(Modifier.fillMaxWidth()) {
            labels.forEach { Text(it, style = H.t.small.copy(fontSize = 11.sp), modifier = Modifier.weight(1f), textAlign = TextAlign.Center, maxLines = 1) }
        }
    }
}

@Composable
fun Timeline(steps: List<Pair<String, Boolean>>, now: Int = -1) {
    val c = H.c
    Column {
        steps.forEachIndexed { i, (text, done) ->
            Row(verticalAlignment = Alignment.Top) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(Modifier.size(14.dp).clip(CircleShape).background(if (done) c.primary else c.surface).border(2.dp, if (done || i == now) c.primary else c.line, CircleShape))
                    if (i < steps.size - 1) Box(Modifier.width(2.dp).height(28.dp).background(if (done) c.primary else c.line))
                }
                Spacer(Modifier.width(12.dp))
                Text(text, style = if (i == now) H.t.title else H.t.body, modifier = Modifier.padding(bottom = 10.dp))
            }
        }
    }
}

@Composable
fun Avatar(name: String, size: Dp = 44.dp) {
    val c = H.c
    val ini = name.split(" ").filter { it.isNotEmpty() }.take(2).joinToString("") { it.take(1).uppercase() }.ifEmpty { "?" }
    Box(Modifier.size(size).clip(CircleShape).background(c.tint), contentAlignment = Alignment.Center) {
        Text(ini, style = H.t.title.copy(color = c.primaryText))
    }
}

@Composable
fun Empty(icon: String, title: String, sub: String = "", action: String = "", onAction: (() -> Unit)? = null) {
    Column(Modifier.fillMaxWidth().padding(vertical = 32.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(Modifier.size(72.dp).clip(CircleShape).background(H.c.tint), contentAlignment = Alignment.Center) { HIcon(icon, size = 32.dp, tint = H.c.primaryText) }
        Title(title)
        if (sub.isNotEmpty()) Small(sub)
        if (action.isNotEmpty() && onAction != null) Btn(action, kind = BtnKind.Tonal, onClick = onAction)
    }
}

/** A dense table that scrolls sideways on a phone. */
@Composable
fun DataTable(headers: List<String>, rows: List<List<String>>, onRow: ((Int) -> Unit)? = null) {
    val c = H.c
    val shape = RoundedCornerShape(H.look.radius * 0.6f)
    Column(Modifier.fillMaxWidth().clip(shape).border(1.dp, c.line, shape).horizontalScroll(rememberScrollState())) {
        Row(Modifier.background(c.tint)) {
            headers.forEach { Text(it, style = H.t.label, modifier = Modifier.width(120.dp).padding(10.dp)) }
        }
        rows.forEachIndexed { i, r ->
            Row(Modifier.let { m -> if (onRow != null) m.clickable { onRow(i) } else m }) {
                r.forEach { Text(it, style = H.t.body.copy(fontSize = 14.sp), modifier = Modifier.width(120.dp).padding(10.dp), maxLines = 2) }
            }
            HDivider()
        }
    }
}

/** Kanban columns that scroll sideways. */
@Composable
fun Kanban(columns: List<Pair<String, List<String>>>, onCard: ((String) -> Unit)? = null) {
    val c = H.c
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        columns.forEach { (title, cards) ->
            Column(Modifier.width(240.dp).background(c.tint, RoundedCornerShape(H.look.radius)).padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row { Text(title, style = H.t.title, modifier = Modifier.weight(1f)); Text("${cards.size}", style = H.t.small) }
                cards.forEach { t ->
                    HCard(onClick = onCard?.let { f -> { f(t) } }, padding = 10.dp) { Body(t) }
                }
            }
        }
    }
}

/** A drawn map (no tiles, no key): pins at fractions of the box, an optional route through them. */
@Composable
fun MapBox(pins: List<Pair<Float, Float>>, route: Boolean = false, height: Dp = 220.dp, label: String = "") {
    val c = H.c
    Box(Modifier.fillMaxWidth().height(height).clip(RoundedCornerShape(H.look.radius)).background(c.tint)) {
        Canvas(Modifier.fillMaxSize()) {
            val step = 28.dp.toPx()
            var x = 0f
            while (x < size.width) { drawLine(c.line, Offset(x, 0f), Offset(x + size.height * 0.3f, size.height), 1.dp.toPx()); x += step }
            if (route && pins.size > 1) {
                val p = Path()
                pins.forEachIndexed { i, (fx, fy) -> if (i == 0) p.moveTo(fx * size.width, fy * size.height) else p.lineTo(fx * size.width, fy * size.height) }
                drawPath(p, c.primary, style = Stroke(4.dp.toPx(), cap = StrokeCap.Round))
            }
            pins.forEach { (fx, fy) ->
                drawCircle(c.primary, 9.dp.toPx(), Offset(fx * size.width, fy * size.height))
                drawCircle(Color.White, 3.5.dp.toPx(), Offset(fx * size.width, fy * size.height))
            }
        }
        if (label.isNotEmpty()) Text(label, style = H.t.small.copy(color = c.ink), modifier = Modifier.align(Alignment.BottomStart).padding(8.dp)
            .background(c.surface, RoundedCornerShape(6.dp)).padding(horizontal = 6.dp, vertical = 2.dp))
    }
}

/** A QR-looking block (the real code is drawn by the live version from her UPI ID / pass id). */
@Composable
fun QrBox(size: Dp = 160.dp, seed: String = "hoola") {
    val c = H.c
    Canvas(Modifier.size(size).background(Color.White, RoundedCornerShape(8.dp)).padding(10.dp)) {
        val n = 21
        val cell = this.size.width / n
        val h = seed.hashCode()
        for (y in 0 until n) for (x in 0 until n) {
            val corner = (x < 7 && y < 7) || (x >= n - 7 && y < 7) || (x < 7 && y >= n - 7)
            val on = if (corner) (x % 6 == 0 || y % 6 == 0 || (x % 6 in 2..4 && y % 6 in 2..4)) else ((x * 31 + y * 17 + h) % 3 == 0)
            if (on) drawRect(Color.Black, Offset(x * cell, y * cell), Size(cell, cell))
        }
    }
}

/** Vertical space. */
@Composable
fun Gap(height: Dp = 12.dp) = Spacer(Modifier.height(height))

/** Content inside a Page body (LazyListScope): shorthand for item { }. */
fun LazyListScope.block(content: @Composable () -> Unit) = item { content() }

@Composable
fun Center(content: @Composable BoxScope.() -> Unit) = Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center, content = content)

@Composable
fun rememberToggle(initial: Boolean = false) = remember { mutableStateOf(initial) }

@Composable
fun ToggleText(on: Boolean, yes: String, no: String) { var x by remember { mutableStateOf(on) }; Text(if (x) yes else no, style = H.t.small, modifier = Modifier.clickable { x = !x }) }
