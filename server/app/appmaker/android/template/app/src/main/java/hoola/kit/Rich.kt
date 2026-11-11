package hoola.kit

// Made by Hoola App Sahayak (v0.425 RANG). Rich pieces for any app, all native Compose (no web views, no extra libraries):
// fields - SignatureField, PhotosField (up to 6), VideoField (system picker, no permission), AudioField (a voice note,
// microphone asked only when the user taps Record), RichTextField (bold / italic / list as plain markdown);
// showing - RichText, PhotosStrip, VideoPlayer / AudioPlayer (a 15-minute signed address, the phone's own player),
// PdfViewer (Android's PdfRenderer, one page at a time); blocks - CalendarBlock, KanbanBlock, GanttBlock, LineChart,
// PieChart, Carousel, OnboardingPager. Everything a user adds waits in the outbox like a photo until the server has it.

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.net.Uri
import android.os.Build
import android.os.ParcelFileDescriptor
import android.widget.MediaController
import android.widget.VideoView
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.time.LocalDate
import java.time.YearMonth
import java.util.UUID

private fun cacheFile(ctx: Context, ext: String): File =
    File(File(ctx.cacheDir, "hoola_up").apply { mkdirs() }, UUID.randomUUID().toString().replace("-", "") + ext)

/** A 15-minute signed address for the phone's own player (players cannot send the sign-in token). */
suspend fun mediaUrl(fid: String): String? {
    if (!fid.startsWith("f_")) return null
    val r = Cloud.call("POST", "/files/$fid/link", JSONObject(), Auth.token())
    val p = r.body.optString("path")
    return if (r.ok && p.isNotEmpty()) Cloud.baseUrl + p else null
}

// ---------------------------------------------------------------- fields
/** Sign with a finger; saved as a picture of the signature (white background) in the outbox. */
@Composable
fun SignatureField(label: String, key: String) {
    val c = ctx()
    val strokes = remember(key) { mutableStateListOf<List<Offset>>() }
    var current by remember(key) { mutableStateOf<List<Offset>>(emptyList()) }
    var box by remember { mutableStateOf(IntSize.Zero) }
    val v = AppState.form[key].orEmpty()
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Label(label)
        if (v.isNotEmpty()) {
            RemotePhoto(v, Modifier.fillMaxWidth().height(140.dp), label)
            Btn(Strings.signAgain, kind = BtnKind.Ghost, small = true) { AppState.form.remove(key); strokes.clear() }
            return@Column
        }
        Canvas(Modifier.fillMaxWidth().height(160.dp).clip(RoundedCornerShape(12.dp)).background(Color.White)
            .border(1.dp, H.c.line, RoundedCornerShape(12.dp)).onSizeChanged { box = it }.semantics { contentDescription = label }
            .pointerInput(key) {
                detectDragGestures(onDragStart = { current = listOf(it) }, onDragEnd = { if (current.size > 1) strokes.add(current); current = emptyList() }) { ch, _ ->
                    current = current + ch.position
                }
            }) {
            (strokes + listOf(current)).forEach { s ->
                if (s.size > 1) {
                    val p = Path().apply { moveTo(s[0].x, s[0].y); s.drop(1).forEach { lineTo(it.x, it.y) } }
                    drawPath(p, Color(0xFF111111), style = Stroke(width = 5f))
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Btn(Strings.useSignature, kind = BtnKind.Tonal, small = true, enabled = strokes.isNotEmpty()) {
                val path = saveSignature(c, strokes, box)
                if (path != null) AppState.form[key] = "local:$path" else Act.toast(c, Strings.tryAgain)
            }
            Btn(Strings.clearWord, kind = BtnKind.Ghost, small = true) { strokes.clear() }
        }
    }
}

private fun saveSignature(ctx: Context, strokes: List<List<Offset>>, box: IntSize): String? = try {
    val w = box.width.coerceIn(200, 1600)
    val h = box.height.coerceIn(100, 800)
    val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
    val cv = android.graphics.Canvas(bmp)
    cv.drawColor(android.graphics.Color.WHITE)
    val paint = android.graphics.Paint().apply { color = android.graphics.Color.BLACK; strokeWidth = 5f; style = android.graphics.Paint.Style.STROKE; isAntiAlias = true }
    strokes.forEach { s ->
        val p = android.graphics.Path()
        p.moveTo(s[0].x, s[0].y)
        s.drop(1).forEach { p.lineTo(it.x, it.y) }
        cv.drawPath(p, paint)
    }
    val f = cacheFile(ctx, ".jpg")
    f.outputStream().use { bmp.compress(Bitmap.CompressFormat.JPEG, 92, it) }
    f.absolutePath
} catch (_: Exception) {
    null
}

/** Up to [max] photos in one field (system Photo Picker, no permission); each waits in the outbox until sent. */
@Composable
fun PhotosField(label: String, key: String, max: Int = 6) {
    val c = ctx()
    val scope = rememberCoroutineScope()
    val have = AppState.form[key].orEmpty().split(",").map { it.trim() }.filter { it.isNotEmpty() }
    val left = (max - have.size).coerceAtLeast(1)
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(maxOf(2, left))) { uris ->
        if (uris.isNotEmpty()) scope.launch {
            val got = withContext(Dispatchers.IO) { uris.take(left).mapNotNull { Photos.shrink(c, it) } }
            AppState.form[key] = (have + got.map { "local:$it" }).take(max).joinToString(",")
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Label("$label (${have.size}/$max)")
        if (have.isNotEmpty()) PhotosStrip(have.joinToString(","))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (have.size < max) Btn(Strings.addPhotos, kind = BtnKind.Tonal, icon = "camera", small = true) {
                pick.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            }
            if (have.isNotEmpty()) Btn(Strings.remove, kind = BtnKind.Ghost, small = true) { AppState.form.remove(key) }
        }
    }
}

/** The photos of a multi-photo field in a row (tap one to see it large). */
@Composable
fun PhotosStrip(ids: String) {
    val list = ids.split(",").map { it.trim() }.filter { it.isNotEmpty() }
    var big by remember(ids) { mutableStateOf("") }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            list.forEachIndexed { i, s ->      // v0.802 a photo-only tap target says what it is to TalkBack
                Box(Modifier.size(84.dp).clickable(role = Role.Button) { big = if (big == s) "" else s }) { RemotePhoto(s, Modifier.size(84.dp), Strings.photo + " ${i + 1}") }
            }
        }
        if (big.isNotEmpty()) RemotePhoto(big, Modifier.fillMaxWidth().height(240.dp))
    }
}

/** A short video from the phone's gallery (system picker, no permission), at most 50 MB. */
@Composable
fun VideoField(label: String, key: String) {
    val c = ctx()
    val scope = rememberCoroutineScope()
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) scope.launch {
            val p = withContext(Dispatchers.IO) { copyMedia(c, uri, ".mp4", 50L * 1024 * 1024) }
            if (p != null) AppState.form[key] = "local:$p" else Act.toast(c, Strings.videoTooBig)
        }
    }
    val v = AppState.form[key].orEmpty()
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Label(label)
        if (v.isNotEmpty()) Small(if (v.startsWith("local:")) Strings.videoReady else Strings.videoSaved)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Btn(if (v.isEmpty()) Strings.addVideo else Strings.changeVideo, kind = BtnKind.Tonal, icon = "camera", small = true) {
                pick.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly))
            }
            if (v.isNotEmpty()) Btn(Strings.remove, kind = BtnKind.Ghost, small = true) { AppState.form.remove(key) }
        }
    }
}

private fun copyMedia(ctx: Context, uri: Uri, ext: String, cap: Long): String? = try {
    val f = cacheFile(ctx, ext)
    var n = 0L
    ctx.contentResolver.openInputStream(uri)?.use { inp ->
        f.outputStream().use { out ->
            val buf = ByteArray(64 * 1024)
            while (true) {
                val k = inp.read(buf)
                if (k <= 0) break
                n += k
                if (n > cap) throw IllegalStateException("too big")
                out.write(buf, 0, k)
            }
        }
    }
    if (n == 0L) null else f.absolutePath
} catch (_: Exception) {
    null
}

/** A voice note (up to 2 minutes). The microphone is asked for only when the user taps Record; nothing records otherwise. */
@Composable
fun AudioField(label: String, key: String) {
    val c = ctx()
    val scope = rememberCoroutineScope()
    var rec by remember { mutableStateOf<MediaRecorder?>(null) }
    var file by remember { mutableStateOf<File?>(null) }
    var secs by remember { mutableIntStateOf(0) }
    val start: () -> Unit = {
        try {
            val f = cacheFile(c, ".m4a")
            val m = if (Build.VERSION.SDK_INT >= 31) MediaRecorder(c) else @Suppress("DEPRECATION") MediaRecorder()
            m.setAudioSource(MediaRecorder.AudioSource.MIC)
            m.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            m.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            m.setAudioEncodingBitRate(64000)
            m.setAudioSamplingRate(44100)
            m.setMaxDuration(120_000)
            m.setOutputFile(f.absolutePath)
            m.prepare(); m.start()
            rec = m; file = f; secs = 0
            scope.launch { while (rec != null && secs < 120) { delay(1000); secs += 1 } }
        } catch (_: Exception) {
            Act.toast(c, Strings.tryAgain)
        }
    }
    val stop: () -> Unit = {
        try { rec?.stop() } catch (_: Exception) {}
        rec?.release(); rec = null
        file?.let { if (it.length() > 0) AppState.form[key] = "local:${it.absolutePath}" }
    }
    val perm = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok -> if (ok) start() else Act.toast(c, Strings.micDenied) }
    DisposableEffect(Unit) { onDispose { try { rec?.release() } catch (_: Exception) {} } }
    val v = AppState.form[key].orEmpty()
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Label(label)
        if (rec != null) Small(Strings.recording + " ${secs}s / 120s")
        else if (v.isNotEmpty()) AudioPlayer(v)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (rec == null) Btn(if (v.isEmpty()) Strings.record else Strings.recordAgain, kind = BtnKind.Tonal, icon = "mic", small = true) {
                if (ContextCompat.checkSelfPermission(c, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) start()
                else perm.launch(Manifest.permission.RECORD_AUDIO)
            } else Btn(Strings.stopWord, kind = BtnKind.Danger, small = true) { stop() }
            if (v.isNotEmpty() && rec == null) Btn(Strings.remove, kind = BtnKind.Ghost, small = true) { AppState.form.remove(key) }
        }
    }
}

/** Formatted text kept as plain markdown: **bold**, _italic_, "- " lists. */
@Composable
fun RichTextField(label: String, key: String) {
    var tv by remember(key) { mutableStateOf(TextFieldValue(AppState.form[key].orEmpty())) }
    fun wrap(a: String, b: String) {
        val s = tv.selection
        val t = tv.text
        val mid = t.substring(s.min, s.max)
        val nt = t.substring(0, s.min) + a + mid + b + t.substring(s.max)
        tv = TextFieldValue(nt.take(4000), TextRange((s.min + a.length + mid.length).coerceAtMost(nt.length)))
        AppState.form[key] = tv.text
    }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Label(label)
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Chip("B") { wrap("**", "**") }
            Chip("I") { wrap("_", "_") }
            Chip("• " + Strings.listWord) { wrap(if (tv.text.isEmpty() || tv.text.endsWith("\n")) "- " else "\n- ", "") }
        }
        OutlinedTextField(value = tv, onValueChange = { tv = it.copy(text = it.text.take(4000)); AppState.form[key] = tv.text },
            modifier = Modifier.fillMaxWidth(), minLines = 4)
        if (tv.text.isNotBlank()) RichText(tv.text)
    }
}

/** Markdown words as styled text (headings, bold, italic, lists) - never HTML. */
@Composable
fun RichText(text: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        text.lines().forEach { raw ->
            val line = raw.trimEnd()
            when {
                line.startsWith("# ") -> Title(line.removePrefix("# "))
                line.startsWith("- ") || line.startsWith("* ") -> Text(inline("•  " + line.drop(2)), style = H.t.body)
                line.isBlank() -> Box(Modifier.height(4.dp))
                else -> Text(inline(line), style = H.t.body)
            }
        }
    }
}

private fun inline(s: String) = buildAnnotatedString {
    var i = 0
    val re = Regex("""\*\*(.+?)\*\*|_(.+?)_""")
    for (m in re.findAll(s)) {
        append(s.substring(i, m.range.first))
        if (m.groupValues[1].isNotEmpty()) withStyle(SpanStyle(fontWeight = FontWeight.SemiBold)) { append(m.groupValues[1]) }
        else withStyle(SpanStyle(fontStyle = FontStyle.Italic)) { append(m.groupValues[2]) }
        i = m.range.last + 1
    }
    append(s.substring(i))
}

// ---------------------------------------------------------------- players + PDF
/** A saved video: Play opens the phone's own player on a short-lived signed address. */
@Composable
fun VideoPlayer(src: String) {
    var url by remember(src) { mutableStateOf<String?>(null) }
    var want by remember(src) { mutableStateOf(false) }
    LaunchedEffect(want, src) {
        if (want && url == null) url = if (src.startsWith("local:")) Uri.fromFile(File(src.removePrefix("local:"))).toString() else mediaUrl(src)
    }
    val u = url
    if (!want) Btn(Strings.playVideo, kind = BtnKind.Tonal, icon = "play", small = true) { want = true }
    else if (u == null) Small(Strings.opening)
    else AndroidView(modifier = Modifier.fillMaxWidth().aspectRatio(16f / 9f), factory = { cx ->
        VideoView(cx).apply {
            setMediaController(MediaController(cx).also { it.setAnchorView(this) })
            setVideoURI(Uri.parse(u))
            setOnPreparedListener { start() }
        }
    })
}

/** A voice note: play / pause with the phone's own player. */
@Composable
fun AudioPlayer(src: String) {
    var mp by remember(src) { mutableStateOf<MediaPlayer?>(null) }
    var playing by remember(src) { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    DisposableEffect(src) { onDispose { try { mp?.release() } catch (_: Exception) {} } }
    Btn(if (playing) Strings.pauseWord else Strings.playWord, kind = BtnKind.Outline, icon = "play", small = true) {
        val m = mp
        if (m != null) {
            if (m.isPlaying) { m.pause(); playing = false } else { m.start(); playing = true }
            return@Btn
        }
        scope.launch {
            val u = if (src.startsWith("local:")) src.removePrefix("local:") else mediaUrl(src) ?: return@launch
            try {
                val p = MediaPlayer()
                p.setDataSource(u)
                p.setOnPreparedListener { it.start(); playing = true }
                p.setOnCompletionListener { playing = false }
                p.prepareAsync()
                mp = p
            } catch (_: Exception) {
            }
        }
    }
}

/** A PDF inside the app, one page at a time (Android's own PdfRenderer; nothing in the PDF can run). */
@Composable
fun PdfViewer(fid: String) {
    val c = ctx()
    var file by remember(fid) { mutableStateOf<File?>(null) }
    var page by remember(fid) { mutableIntStateOf(0) }
    var count by remember(fid) { mutableIntStateOf(0) }
    var bmp by remember(fid) { mutableStateOf<Bitmap?>(null) }
    var failed by remember(fid) { mutableStateOf(false) }
    LaunchedEffect(fid) {
        val bytes = Cloud.bytes("/files/$fid", Auth.token())
        if (bytes == null) { failed = true; return@LaunchedEffect }
        file = withContext(Dispatchers.IO) { cacheFile(c, ".pdf").also { it.writeBytes(bytes) } }
    }
    LaunchedEffect(file, page) {
        val f = file ?: return@LaunchedEffect
        bmp = withContext(Dispatchers.IO) {
            try {
                ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY).use { pfd ->
                    PdfRenderer(pfd).use { pr ->
                        count = pr.pageCount
                        pr.openPage(page.coerceIn(0, pr.pageCount - 1)).use { pg ->
                            val w = 1080
                            val h = (w.toFloat() * pg.height / pg.width).toInt().coerceAtMost(2400)
                            Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888).also { b ->
                                b.eraseColor(android.graphics.Color.WHITE)
                                pg.render(b, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                            }
                        }
                    }
                }
            } catch (_: Exception) {
                failed = true; null
            }
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        val b = bmp
        when {
            failed -> Small(Strings.pdfFailed)
            b == null -> Small(Strings.opening)
            else -> Image(b.asImageBitmap(), contentDescription = Strings.pageWord + " ${page + 1}", modifier = Modifier.fillMaxWidth())
        }
        if (count > 1) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Btn(Strings.prevWord, kind = BtnKind.Ghost, small = true, enabled = page > 0) { page -= 1 }
            Small("${Strings.pageWord} ${page + 1} / $count")
            Btn(Strings.nextWord, kind = BtnKind.Ghost, small = true, enabled = page < count - 1) { page += 1 }
        }
    }
}

// ---------------------------------------------------------------- blocks
private fun head(r: Item): String = listOf("name", "title", "service", "item", "subject").map { r.s(it) }.firstOrNull { it.isNotEmpty() } ?: r.id.takeLast(6)

/** A month calendar of a list's rows by their date field; tap a day to see its rows. */
@Composable
fun CalendarBlock(coll: String, dateKey: String = "date") {
    val rows = liveRows(coll)
    var month by remember { mutableStateOf(YearMonth.now()) }
    var day by remember { mutableStateOf<LocalDate?>(null) }
    val byDay = rows.groupBy { it.s(dateKey).take(10) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Btn("‹", kind = BtnKind.Ghost, small = true) { month = month.minusMonths(1) }
            Title(month.month.name.lowercase().replaceFirstChar { it.uppercase() } + " " + month.year)
            Btn("›", kind = BtnKind.Ghost, small = true) { month = month.plusMonths(1) }
        }
        val first = month.atDay(1)
        val lead = (first.dayOfWeek.value + 6) % 7
        val cells = List(lead) { null } + (1..month.lengthOfMonth()).map { month.atDay(it) }
        cells.chunked(7).forEach { week ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                (week + List(7 - week.size) { null }).forEach { d ->
                    val n = d?.let { byDay[it.toString()]?.size } ?: 0
                    Box(Modifier.weight(1f).height(44.dp).clip(RoundedCornerShape(8.dp))
                        .background(if (d != null && d == day) H.c.primary.copy(alpha = 0.18f) else if (n > 0) H.c.tint else Color.Transparent)
                        .clickable(enabled = d != null) { day = d }, contentAlignment = androidx.compose.ui.Alignment.Center) {
                        if (d != null) Column(horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
                            Small(d.dayOfMonth.toString())
                            if (n > 0) Small("•$n")
                        }
                    }
                }
            }
        }
        day?.let { d ->
            val list = byDay[d.toString()].orEmpty()
            Small(d.toString() + " · " + list.size)
            list.take(20).forEach { r -> HCard { Body(head(r)); Small(listOf(r.s("time"), T(r.s("status"))).filter { it.isNotEmpty() }.joinToString(" · ")) } }
        }
    }
}

/** A board with one column per status; staff move a card with a tap (the server checks every move). */
@Composable
fun KanbanBlock(coll: String) {
    val rows = liveRows(coll)
    val opts = Db.fields(coll).firstOrNull { it.s("key") == "status" }?.strings("options").orEmpty()
    var open by remember { mutableStateOf("") }
    if (opts.isEmpty()) { Small(Strings.nothingYet); return }
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        opts.forEach { st ->
            Column(Modifier.width(220.dp).clip(RoundedCornerShape(12.dp)).background(H.c.tint).padding(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                val list = rows.filter { it.s("status") == st }
                Title(T(st) + " (${list.size})")
                list.take(30).forEach { r ->
                    HCard(onClick = { open = if (open == r.id) "" else r.id }) {
                        Body(head(r))
                        if (open == r.id && Auth.isStaff && !r.b("pending") && Team.mayWork(r)) {
                            opts.filter { it != st }.forEach { to -> Chip("→ " + T(to)) { Db.update(coll, r.id, mapOf("status" to to)); open = "" } }
                        }
                    }
                }
            }
        }
    }
}

/** A timeline of rows between two date fields (projects, jobs, bookings). */
@Composable
fun GanttBlock(coll: String, startKey: String = "start", endKey: String = "end") {
    val rows = liveRows(coll).mapNotNull { r ->
        val a = runCatching { LocalDate.parse(r.s(startKey).take(10)) }.getOrNull()
        val b = runCatching { LocalDate.parse(r.s(endKey).take(10)) }.getOrNull() ?: a
        if (a == null || b == null) null else Triple(r, a, if (b.isBefore(a)) a else b)
    }.take(40)
    if (rows.isEmpty()) { Small(Strings.nothingYet); return }
    val lo = rows.minOf { it.second }
    val hi = rows.maxOf { it.third }
    val span = (hi.toEpochDay() - lo.toEpochDay() + 1).coerceAtLeast(1)
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Small("$lo → $hi")
        rows.forEach { (r, a, b) ->
            Small(head(r))
            BoxWithConstraints(Modifier.fillMaxWidth().height(14.dp).clip(RoundedCornerShape(7.dp)).background(H.c.tint)) {
                val x = maxWidth * ((a.toEpochDay() - lo.toEpochDay()).toFloat() / span)
                val w = maxWidth * ((b.toEpochDay() - a.toEpochDay() + 1).toFloat() / span)
                Box(Modifier.offset(x = x).width(w).height(14.dp).clip(RoundedCornerShape(7.dp)).background(H.c.primary))
            }
        }
    }
}

/** A line over the values (e.g. sales per day). */
@Composable
fun LineChart(values: List<Float>, labels: List<String> = emptyList(), height: androidx.compose.ui.unit.Dp = 140.dp) {
    if (values.size < 2) { Small(Strings.nothingYet); return }
    val col = H.c.primary
    val grid = H.c.line
    Column {
        Canvas(Modifier.fillMaxWidth().height(height)) {
            val mx = (values.maxOrNull() ?: 1f).coerceAtLeast(1e-6f)
            val mn = minOf(0f, values.minOrNull() ?: 0f)
            val sx = size.width / (values.size - 1)
            fun y(v: Float) = size.height - (v - mn) / (mx - mn) * size.height
            drawLine(grid, Offset(0f, size.height), Offset(size.width, size.height), 2f)
            val p = Path().apply { moveTo(0f, y(values[0])); values.forEachIndexed { i, v -> if (i > 0) lineTo(i * sx, y(v)) } }
            drawPath(p, col, style = Stroke(width = 5f))
        }
        if (labels.isNotEmpty()) Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Small(labels.first()); Small(labels.last()) }
    }
}

/** A donut of shares with its legend. */
@Composable
fun PieChart(values: List<Float>, labels: List<String>) {
    val total = values.sum()
    if (total <= 0f) { Small(Strings.nothingYet); return }
    val base = H.c.primary
    val colors = listOf(base, H.c.accent, base.copy(alpha = 0.55f), H.c.accent.copy(alpha = 0.55f), base.copy(alpha = 0.3f), H.c.muted)
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
        Canvas(Modifier.size(120.dp)) {
            var a = -90f
            values.forEachIndexed { i, v ->
                val sweep = v / total * 360f
                drawArc(colors[i % colors.size], a, sweep, false, style = Stroke(width = 28f), size = Size(size.width, size.height))
                a += sweep
            }
        }
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            labels.zip(values).forEachIndexed { i, (l, v) ->
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Box(Modifier.size(10.dp).clip(RoundedCornerShape(5.dp)).background(colors[i % colors.size]))
                    Small("$l · ${(v / total * 100).toInt()}%")
                }
            }
        }
    }
}

/** Swipe through photos (her pictures or a row's photos). */
@Composable
fun Carousel(photos: List<String>, height: androidx.compose.ui.unit.Dp = 220.dp) {
    if (photos.isEmpty()) return
    val st = rememberPagerState(pageCount = { photos.size })
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        HorizontalPager(state = st, modifier = Modifier.fillMaxWidth().height(height)) { i -> RemotePhoto(photos[i], Modifier.fillMaxWidth().height(height)) }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
            repeat(photos.size) { i ->
                Box(Modifier.padding(3.dp).size(if (i == st.currentPage) 8.dp else 6.dp).clip(RoundedCornerShape(4.dp))
                    .background(if (i == st.currentPage) H.c.primary else H.c.line))
            }
        }
    }
}

/** First-open pages (title + words); Done calls [onDone] (the caller remembers it was seen). */
@Composable
fun OnboardingPager(pages: List<Pair<String, String>>, onDone: () -> Unit) {
    if (pages.isEmpty()) { LaunchedEffect(Unit) { onDone() }; return }
    val st = rememberPagerState(pageCount = { pages.size })
    val scope = rememberCoroutineScope()
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        HorizontalPager(state = st, modifier = Modifier.fillMaxWidth().height(260.dp)) { i ->
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(pages[i].first, style = H.t.h1)
                Body(pages[i].second)
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Btn(Strings.skipWord, kind = BtnKind.Ghost, small = true) { onDone() }
            val last = st.currentPage >= pages.size - 1
            Btn(if (last) Strings.doneWord else Strings.nextWord, small = true) {
                if (last) onDone() else scope.launch { st.animateScrollToPage(st.currentPage + 1) }
            }
        }
    }
}
