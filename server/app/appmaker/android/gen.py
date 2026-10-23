"""v0.132 App Sahayak, part 4: the native Android project for an approved app design (Kotlin + Jetpack Compose).

The server owns every Gradle file, the version catalogue, the manifest, resources and the HoolaKit (theme, icons, navigation,
components, data, actions, legal screens). The model writes ONLY one Compose file per screen (`hoola.app.screens`); a screen
that can't be made to compile is replaced by a code-made one (`fallback_screen`), so a build never fails because of a screen.

Pure standard library (CI runs `python3 gen.py spec.json outdir` without the server's packages).

spec = {app: {name, app_id, version_code, version_name, language, base_url, app_key},
        tokens: {...design tokens incl. alt (other mode)}, structure: {nav, fab, card, button, header, transition},
        tabs: [sid], start: sid, flow: [sid], code_screens: [sid],
        screens: [{id, label, tab, icon, purpose, lists, actions: [{label, go}]}],
        icons: {name: [svg path d, ...]}, fonts: {head: {400: path, 700: path}, body: {...}},
        seed: {facts, lists, demo_lists}, screens_kt: {sid: kotlin source}, preview_key: {p12_b64, password}}"""
from __future__ import annotations

import base64
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template"
KIT_FILES = ["Theme.kt", "Data.kt", "Api.kt", "Kit.kt", "Nav.kt", "Strings.kt", "Actions.kt", "CodeScreens.kt"]
CODE_SCREENS = ("splash", "consent", "notify_permission", "seller_info", "privacy", "delete_account")
ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,48}$")


def kotlin_name(sid: str) -> str:
    return "Screen" + "".join(p.capitalize() for p in re.split(r"[_\-]+", sid) if p)


def kstr(s: Any) -> str:
    """A Kotlin string literal."""
    t = str(s if s is not None else "")
    t = t.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("\n", "\\n").replace("\r", "")
    return f'"{t}"'


def _hex(v: Any, default: str = "#888888") -> str:
    s = str(v or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", s):
        return s.upper()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", s):
        return "#" + "".join(ch * 2 for ch in s[1:]).upper()
    return default


def _colors_kt(tk: dict[str, Any], dark: bool) -> str:
    g = lambda k, d="#888888": f'hex("{_hex(tk.get(k), d)}")'          # noqa: E731
    return ("HoolaColors(bg = " + g("bg", "#FFFFFF") + ", surface = " + g("surface", "#FFFFFF") + ", ink = " + g("ink", "#111111")
            + ", muted = " + g("muted", "#555555") + ", line = " + g("line", "#DDDDDD") + ", primary = " + g("primary", "#3355FF")
            + ", onPrimary = " + g("on_primary", "#FFFFFF") + ", accent = " + g("accent", "#FF8800") + ", onAccent = " + g("on_accent", "#111111")
            + ", primaryText = " + f'hex("{_hex(tk.get("primary_text") or tk.get("primary"), "#3355FF")}")'
            + ", accentText = " + f'hex("{_hex(tk.get("accent_text") or tk.get("accent"), "#AA5500")}")'
            + ", tint = " + g("tint", "#EEF0FF") + ", tint2 = " + g("tint_2", "#FFF3E6") + f", dark = {'true' if dark else 'false'})")


def tokens_kt(spec: dict[str, Any], fonts: dict[str, bool]) -> str:
    tk = spec.get("tokens") or {}
    st = {**{k: tk.get(k) for k in ("nav", "fab", "card", "button", "header", "transition")}, **(spec.get("structure") or {})}
    alt = tk.get("alt") or {}
    base_dark = bool(tk.get("dark"))
    light, dark = (alt, tk) if base_dark else (tk, alt or tk)
    mode = str(tk.get("mode") or "both")
    radius = int(float(tk.get("radius") or 16))

    def fam(which: str) -> str:
        if fonts.get(f"{which}_700") and fonts.get(f"{which}_400"):
            return (f"FontFamily(Font(R.font.{which}_400, FontWeight.Normal), Font(R.font.{which}_700, FontWeight.Bold))")
        if fonts.get(f"{which}_400"):
            return f"FontFamily(Font(R.font.{which}_400, FontWeight.Normal))"
        return "FontFamily.Default"
    s = (str(st.get(k) or d) for k, d in (("card", "elevated"), ("button", "rounded"), ("header", "large_title"), ("nav", "bar"),
                                           ("fab", "none"), ("transition", "fade_through")))
    card, button, header, nav, fab, trans = s
    lang = (spec.get("app") or {}).get("language") or "en"
    return f'''package hoola.app

// Made by Hoola App Sahayak from the approved design's tokens. Do not edit: a new design version rewrites it.

import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import hoola.kit.HoolaColors
import hoola.kit.HoolaLook
import hoola.kit.hex

object AppTokens {{
    val light = {_colors_kt(light, False)}
    val dark = {_colors_kt(dark, True)}
    val look = HoolaLook(
        light = light, dark = dark, mode = {kstr(mode)}, radius = {radius}.dp, buttonRadius = {max(6, min(radius, 28))}.dp,
        card = {kstr(card)}, button = {kstr(button)}, header = {kstr(header)}, nav = {kstr(nav)}, fab = {kstr(fab)},
        transition = {kstr(trans)}, headFont = {fam("head")}, bodyFont = {fam("body")}, language = {kstr(lang)},
    )
}}
'''


def icons_kt(icons: dict[str, list[str]]) -> str:
    rows = []
    for name in sorted(icons):
        if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            continue
        ds = ", ".join(kstr(d) for d in icons[name] if re.fullmatch(r"[0-9MmLlHhVvCcSsQqTtAaZz .,\-eE]+", d))
        rows.append(f"        {kstr(name)} to listOf({ds}),")
    body = "\n".join(rows)
    return f'''package hoola.kit

// Made by Hoola App Sahayak: the same 24 px line icons as the approved design (stroke 1.8, round caps).

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.addPathNodes
import androidx.compose.ui.unit.dp

object HIcons {{
    private val paths: Map<String, List<String>> = mapOf(
{body}
    )
    private val cache = HashMap<String, ImageVector>()
    val names: Set<String> get() = paths.keys

    fun get(name: String): ImageVector = cache.getOrPut(name) {{
        val ds = paths[name] ?: paths["dot"] ?: listOf("M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0")
        val b = ImageVector.Builder(name = name, defaultWidth = 24.dp, defaultHeight = 24.dp, viewportWidth = 24f, viewportHeight = 24f)
        ds.forEach {{ d ->
            b.addPath(pathData = addPathNodes(d), fill = null, stroke = SolidColor(Color.Black), strokeLineWidth = 1.8f,
                strokeLineCap = StrokeCap.Round, strokeLineJoin = StrokeJoin.Round)
        }}
        b.build()
    }}
}}
'''


TAB_ICONS = {"home": "home", "categories": "grid", "cart": "cart", "orders": "receipt", "profile": "user", "menu": "food",
             "services": "list", "my_bookings": "calendar", "courses": "book", "timetable": "calendar", "member_card": "qr",
             "request_service": "plus", "job_status": "wrench", "khata": "wallet", "rewards": "gift", "catalogue": "grid",
             "wishlist": "heart", "events": "ticket", "pass": "qr", "updates": "bell", "plans": "award"}
WORD_ICONS = [("dashboard", "chart"), ("report", "chart"), ("kpi", "chart"), ("lead", "users"), ("pipeline", "trend"),
              ("followup", "clock"), ("ticket", "ticket"), ("map", "pin"), ("route", "navigate"), ("task", "list"),
              ("kanban", "grid"), ("gantt", "calendar"), ("calendar", "calendar"), ("attendance", "check-circle"),
              ("leave", "calendar"), ("approval", "check-circle"), ("payslip", "receipt"), ("inventory", "package"),
              ("stock", "package"), ("scanner", "scan"), ("scan", "scan"), ("pos", "receipt"), ("invoice", "receipt"),
              ("payment", "wallet"), ("device", "wifi"), ("alert", "alert"), ("patient", "health"), ("class", "cap"),
              ("grade", "award"), ("fee", "wallet"), ("trip", "truck"), ("delivery", "truck"), ("dispatch", "truck"),
              ("vehicle", "car"), ("survey", "edit"), ("upload", "upload"), ("offline", "download"), ("chat", "chat"),
              ("announcement", "bell"), ("notification", "bell"), ("directory", "users"), ("knowledge", "book"),
              ("checklist", "check"), ("visit", "pin"), ("customer", "user"), ("target", "trend"), ("data_table", "list"),
              ("org", "users"), ("team", "users"), ("file", "file"), ("profile", "user"), ("settings", "settings")]


def icon_for(sid: str, given: str = "") -> str:
    if given:
        return given
    if sid in TAB_ICONS:
        return TAB_ICONS[sid]
    for w, ic in WORD_ICONS:
        if w in sid:
            return ic
    return "dot"


def screens_kt(spec: dict[str, Any], have: set[str]) -> str:
    """The registry: tabs, every screen id -> its composable, the legal screens, the start flow."""
    scr = [s for s in spec.get("screens", []) if ID_RE.match(s["id"])]
    ids = [s["id"] for s in scr]
    code = [c for c in spec.get("code_screens", []) if c in CODE_SCREENS]
    tabs = [t for t in spec.get("tabs", []) if t in ids]
    if not tabs:
        tabs = ids[:min(4, len(ids))]
    start = spec.get("start") if spec.get("start") in ids else (tabs[0] if tabs else ids[0])
    label = {s["id"]: s.get("label") or s["id"] for s in scr}
    icon = {s["id"]: icon_for(s["id"], s.get("icon") or "") for s in scr}
    tab_rows = ",\n        ".join(f"TabSpec({kstr(t)}, {kstr(label[t])}, {kstr(icon[t])})" for t in tabs)
    whens = "\n".join(f"            {kstr(s)} -> {kotlin_name(s)}()" for s in ids if s in have)
    code_when = {"seller_info": "SellerScreen()", "privacy": "PrivacyScreen()", "delete_account": "DeleteAccountScreen()"}
    cwhens = "\n".join(f"            {kstr(c)} -> {code_when[c]}" for c in code if c in code_when)
    all_ids = ", ".join(kstr(x) for x in ids + [c for c in code if c in code_when])
    fab = spec.get("fab") or {}
    fab_main = (f"FabAction({kstr(fab['label'])}, {kstr(fab.get('icon') or 'plus')}, {kstr(fab['go'])})"
                if fab.get("go") in ids else "null")
    fab_actions = ", ".join(f"FabAction({kstr(a['label'])}, {kstr(a.get('icon') or 'dot')}, {kstr(a['go'])})"
                            for a in (fab.get("actions") or []) if a.get("go") in ids)
    imports = "\n".join(f"import hoola.app.screens.{kotlin_name(s)}" for s in ids if s in have)
    return f'''package hoola.app

// Made by Hoola App Sahayak from the approved design: which screens exist, the tabs, the FAB and the start.

import androidx.compose.runtime.Composable
import hoola.kit.DeleteAccountScreen
import hoola.kit.Empty
import hoola.kit.FabAction
import hoola.kit.Page
import hoola.kit.PrivacyScreen
import hoola.kit.SellerScreen
import hoola.kit.TabSpec
import hoola.kit.block
{imports}

object AppScreens {{
    const val START = {kstr(start)}
    val tabs = listOf(
        {tab_rows}
    )
    val ids: Set<String> = setOf({all_ids})
    val fabMain: FabAction? = {fab_main}
    val fabActions: List<FabAction> = listOf({fab_actions})
    const val HAS_CONSENT = {"true" if "consent" in code else "false"}
    const val HAS_NOTIFY = {"true" if "notify_permission" in code else "false"}

    @Composable
    fun Show(id: String) {{
        when (id) {{
{whens}
{cwhens}
            else -> Page(id) {{ block {{ Empty("info", id) }} }}
        }}
    }}
}}
'''


def main_activity_kt(spec: dict[str, Any]) -> str:
    app = spec.get("app") or {}
    return f'''package hoola.app

// Made by Hoola App Sahayak. The app's single activity: theme from the design, splash -> consent -> notification
// explainer (first run only) -> the app shell with the design's navigation.

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.LaunchedEffect
import hoola.kit.Api
import hoola.kit.AppData
import hoola.kit.AppShell
import hoola.kit.ConsentScreen
import hoola.kit.HoolaTheme
import hoola.kit.Nav
import hoola.kit.NotifyScreen
import hoola.kit.SplashScreen
import hoola.kit.Store
import hoola.kit.Strings

object AppConfig {{
    const val BASE_URL = {kstr(app.get("base_url") or "")}
    const val APP_ID = {kstr(app.get("app_key") or "")}
}}

class MainActivity : ComponentActivity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        Strings.init(AppTokens.look.language)
        AppData.load(this)
        Api.init(AppConfig.BASE_URL, AppConfig.APP_ID)
        val seen = Store.get(this, "onboarded") == "1"
        // Debug builds only (Hoola's own checks open every screen and take its picture); release builds ignore it.
        val jump = if (BuildConfig.DEBUG) intent?.getStringExtra("hoola_screen")?.takeIf {{ it in AppScreens.ids }} else null
        setContent {{
            HoolaTheme(AppTokens.look) {{
                var stage by remember {{ mutableStateOf(if (seen || jump != null) "app" else "splash") }}
                val nav = remember {{ Nav(jump ?: AppScreens.START, AppScreens.tabs, AppScreens.ids) }}
                LaunchedEffect(Unit) {{ Api.refresh(this@MainActivity) }}
                when (stage) {{
                    "splash" -> SplashScreen {{ stage = if (AppScreens.HAS_CONSENT) "consent" else if (AppScreens.HAS_NOTIFY) "notify" else "app" }}
                    "consent" -> ConsentScreen {{ stage = if (AppScreens.HAS_NOTIFY) "notify" else "app"; if (!AppScreens.HAS_NOTIFY) Store.put(this@MainActivity, "onboarded", "1") }}
                    "notify" -> NotifyScreen {{ stage = "app"; Store.put(this@MainActivity, "onboarded", "1") }}
                    else -> AppShell(nav, AppScreens.fabMain, AppScreens.fabActions, AppData.appName) {{ id -> AppScreens.Show(id) }}
                }}
            }}
        }}
    }}
}}
'''


def manifest_xml(spec: dict[str, Any]) -> str:
    return '''<?xml version="1.0" encoding="utf-8"?>
<!-- Made by Hoola App Sahayak. Only the permissions the design's features need; restricted ones are never added. -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <application
        android:allowBackup="false"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/AppTheme"
        android:networkSecurityConfig="@xml/network_security_config">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
    <queries>
        <intent>
            <action android:name="android.intent.action.VIEW" />
            <data android:scheme="upi" />
        </intent>
    </queries>
</manifest>
'''


def _xml(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "\\'").replace('"', '\\"'))


def resources(spec: dict[str, Any], out: Path) -> None:
    app = spec.get("app") or {}
    tk = spec.get("tokens") or {}
    res = out / "app/src/main/res"
    (res / "values").mkdir(parents=True, exist_ok=True)
    name = _xml(app.get("name") or "App")
    (res / "values/strings.xml").write_text(f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <string name="app_name">{name}</string>\n</resources>\n')
    bg = _hex(tk.get("bg"), "#FFFFFF")
    dark_bg = _hex((tk.get("alt") or {}).get("bg") if not tk.get("dark") else tk.get("bg"), "#111111")
    (res / "values/colors.xml").write_text(
        f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="window_bg">{bg}</color>\n'
        f'    <color name="ic_bg">{_hex(tk.get("primary"), "#3355FF")}</color>\n</resources>\n')
    (res / "values/themes.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        '    <style name="AppTheme" parent="android:Theme.Material.Light.NoActionBar">\n'
        '        <item name="android:windowBackground">@color/window_bg</item>\n'
        '    </style>\n</resources>\n')
    (res / "values-night").mkdir(exist_ok=True)
    (res / "values-night/colors.xml").write_text(
        f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="window_bg">{dark_bg if tk.get("mode") != "light" else bg}</color>\n</resources>\n')
    (res / "xml").mkdir(exist_ok=True)
    (res / "xml/network_security_config.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<network-security-config>\n'
        '    <base-config cleartextTrafficPermitted="false" />\n</network-security-config>\n')
    # launcher icon: adaptive (minSdk 26), the app's own icon drawn on her primary colour
    icons = spec.get("icons") or {}
    glyph = icons.get(spec.get("app_icon") or "store") or icons.get("store") or icons.get("dot") or ["M8 12h8"]
    on = _hex(tk.get("on_primary"), "#FFFFFF")
    paths = "\n".join(f'        <path android:pathData="{_xml(d)}" android:strokeColor="{on}" android:strokeWidth="1.8" '
                      f'android:strokeLineCap="round" android:strokeLineJoin="round" android:fillColor="#00000000" />' for d in glyph)
    (res / "drawable").mkdir(exist_ok=True)
    (res / "drawable/ic_fg.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:width="108dp" android:height="108dp" android:viewportWidth="24" android:viewportHeight="24">\n'
        '    <group android:scaleX="0.5" android:scaleY="0.5" android:translateX="6" android:translateY="6">\n'
        f'{paths}\n    </group>\n</vector>\n')
    (res / "mipmap-anydpi-v26").mkdir(exist_ok=True)
    (res / "mipmap-anydpi-v26/ic_launcher.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_bg" />\n    <foreground android:drawable="@drawable/ic_fg" />\n'
        '    <monochrome android:drawable="@drawable/ic_fg" />\n</adaptive-icon>\n')


# ---------------------------------------------------------------- the code-made screen (always compiles)
def fallback_screen(s: dict[str, Any], ids: list[str], tabs: list[str]) -> str:
    """A plain, honest screen built only from kit blocks: title, purpose, the records of its list, its actions."""
    sid = s["id"]
    lists = [x for x in (s.get("lists") or []) if re.fullmatch(r"[a-z][a-z0-9_]*", x)]
    lst = lists[0] if lists else ""
    acts = [a for a in (s.get("actions") or []) if a.get("go") in ids and a.get("go") != sid][:4]
    tab = sid in tabs
    rows = []
    if s.get("purpose"):
        rows.append(f"        block {{ Small({kstr(s['purpose'])}) }}")
    if lst:
        nxt = next((a["go"] for a in acts), "")
        click = f"{{ nav.open({kstr(nxt)}, {kstr(lst)}, rec.id) }}" if nxt else "null"
        rows.append(f'''        val items = AppData.list({kstr(lst)})
        if (items.isEmpty()) block {{ Empty({kstr(icon_for(sid))}, {kstr(s.get("label") or sid)}) }}
        items.take(40).forEach {{ rec ->
            block {{
                HCard(onClick = {click}) {{
                    Title(rec.name)
                    val sub = listOf(rec.s("category"), rec.s("status"), rec.s("when"), rec.s("desc")).filter {{ x -> x.isNotEmpty() }}.distinct().joinToString(" · ")
                    if (sub.isNotEmpty()) Small(sub)
                    if (rec.price > 0) Price(rec.price)
                }}
            }}
        }}''')
    else:
        rows.append(f"        block {{ Empty({kstr(icon_for(sid))}, {kstr(s.get('label') or sid)}) }}")
    for a in acts:
        rows.append(f"        block {{ Btn({kstr(a.get('label') or a['go'])}, modifier = Modifier.fillMaxWidth(), kind = BtnKind.Tonal) "
                    f"{{ nav.go({kstr(a['go'])}) }} }}")
    body = "\n".join(rows)
    return f'''package hoola.app.screens

// Made by Hoola App Sahayak (simple version made by code).

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import hoola.kit.*

@Composable
fun {kotlin_name(sid)}() {{
    val nav = LocalNav.current
    Page({kstr(s.get("label") or sid)}, back = {"false" if tab else "true"}) {{
{body}
    }}
}}
'''


# ---------------------------------------------------------------- what a model-written screen may contain
ALLOWED_IMPORT = re.compile(r"^(androidx\.compose\.(foundation|material3|runtime|ui|animation)(\.[\w.]+)?(\.\*)?|hoola\.kit(\.[\w*]+)?"
                            r"|kotlin\.math\.\w+|kotlin\.random\.\w+)$")
BANNED = [
    (r"\bPasswordVisualTransformation\b|KeyboardType\.(Password|NumberPassword)", "password / PIN fields are not allowed"),
    (r"(?i)\b(card ?number|cvv|cvc|upi ?pin|mpin|atm ?pin)\b", "card / CVV / UPI PIN text is not allowed"),
    (r"\bjava\.(io|net|nio)\b|\bURL\(|HttpURLConnection|\bSocket\b|\bOkHttp", "screens never touch the network or files (the kit does)"),
    (r"\bRuntime\b|\bProcessBuilder\b|\bClass\.forName\b|::class\.java|\breflect\b", "no reflection / processes"),
    (r"\bWebView\b|\bIntent\(", "no WebView / raw intents (use Act.*)"),
    (r"\bandroidx\.compose\.material\.(?!3)|androidx\.compose\.material\.icons|\baccompanist\b", "Material 2 / icons library / Accompanist are not in the app"),
    (r"\bkapt\b|@HiltViewModel|@Inject\b|\bRoom\b", "no annotation processing"),
    (r"\bNavHost\b|rememberNavController", "navigation is LocalNav.current (no NavHost)"),
    (r"\bSharedPreferences\b|\bgetSharedPreferences\b|\bdataStore\b", "storage only through the kit"),
    (r"\bLog\.[dewiv]\(|\bprintln\(", "no logging"),
]


def scan_screen(src: str, sid: str, ids: list[str]) -> list[str]:
    """Problems that must be fixed before the screen is used (house rules, not compile errors)."""
    p: list[str] = []
    if not re.search(r"^package hoola\.app\.screens\s*$", src, re.M):
        p.append("first line must be: package hoola.app.screens")
    if not re.search(rf"@Composable\s+fun\s+{kotlin_name(sid)}\s*\(\s*\)", src):
        p.append(f"must define @Composable fun {kotlin_name(sid)}() with no parameters")
    for imp in re.findall(r"^import\s+([\w.*]+)", src, re.M):
        if not ALLOWED_IMPORT.match(imp):
            p.append(f"import not allowed: {imp}")
    for rx, why in BANNED:
        m = re.search(rx, src)
        if m:
            p.append(f"{why} ({m.group(0)})")
    for go in re.findall(r"nav\.(?:go|open)\(\s*\"([^\"]+)\"", src):
        if go not in ids:
            p.append(f'nav.go("{go}"): no such screen (use one of the SCREEN IDS)')
    if len(src) > 60000:
        p.append("screen file too long (max 60 KB)")
    if re.search(r"^\s*(class|object)\s+\w+", src, re.M) and "data class" not in src:
        p.append("screens contain only @Composable functions (no classes / objects)")
    return p


# ---------------------------------------------------------------- write the project
def write_project(spec: dict[str, Any], out: Path) -> dict[str, Any]:
    out = Path(out)
    tmp = out.with_name(out.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(TEMPLATE, tmp)
    app = spec.get("app") or {}
    app_id = str(app.get("app_id") or "in.hoola.preview.app")
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,5}", app_id):
        raise ValueError(f"bad application id {app_id}")
    rep = {"@@PROJECT@@": re.sub(r"[^A-Za-z0-9]", "", str(app.get("name") or "HoolaApp"))[:40] or "HoolaApp",
           "@@APP_ID@@": app_id, "@@VERSION_CODE@@": str(int(app.get("version_code") or 1)),
           "@@VERSION_NAME@@": re.sub(r"[^0-9A-Za-z.\-]", "", str(app.get("version_name") or "1.0")) or "1.0",
           "@@KEY_PASS@@": re.sub(r"[^A-Za-z0-9]", "", str((spec.get("preview_key") or {}).get("password") or "hoolapreview"))}
    for f in (tmp / "settings.gradle.kts", tmp / "app/build.gradle.kts"):
        t = f.read_text()
        for k, v in rep.items():
            t = t.replace(k, v)
        f.write_text(t)
    (tmp / "gradlew").chmod(0o755)
    main = tmp / "app/src/main"
    (main / "AndroidManifest.xml").write_text(manifest_xml(spec))
    resources(spec, tmp)
    fonts_have: dict[str, bool] = {}
    for which, files in (spec.get("fonts") or {}).items():
        if which not in ("head", "body"):
            continue
        for w, path in (files or {}).items():
            p = Path(str(path))
            if p.is_file() and p.suffix.lower() in (".ttf", ".otf") and str(w) in ("400", "700"):
                (main / "res/font").mkdir(parents=True, exist_ok=True)
                shutil.copy(p, main / f"res/font/{which}_{w}{p.suffix.lower()}")
                fonts_have[f"{which}_{w}"] = True
    kit = main / "java/hoola/kit"
    (kit / "Icons.kt").write_text(icons_kt(spec.get("icons") or {}))
    appd = main / "java/hoola/app"
    (appd / "screens").mkdir(parents=True, exist_ok=True)
    (appd / "AppTokens.kt").write_text(tokens_kt(spec, fonts_have))
    (appd / "MainActivity.kt").write_text(main_activity_kt(spec))
    scr = [s for s in spec.get("screens", []) if ID_RE.match(s.get("id", ""))]
    ids = [s["id"] for s in scr]
    tabs = [t for t in spec.get("tabs", []) if t in ids]
    given = spec.get("screens_kt") or {}
    made: dict[str, str] = {}
    for s in scr:
        sid = s["id"]
        src = given.get(sid)
        if src and not scan_screen(src, sid, ids):
            made[sid] = "model"
        else:
            src = fallback_screen(s, ids, tabs)
            made[sid] = "code"
        (appd / "screens" / f"{kotlin_name(sid)}.kt").write_text(src)
    (appd / "AppScreens.kt").write_text(screens_kt(spec, set(ids)))
    (main / "assets").mkdir(exist_ok=True)
    (main / "assets/seed.json").write_text(json.dumps(spec.get("seed") or {}, ensure_ascii=False))
    key = spec.get("preview_key") or {}
    if key.get("p12_b64"):
        (tmp / "keys").mkdir(exist_ok=True)
        (tmp / "keys/preview.p12").write_bytes(base64.b64decode(key["p12_b64"]))
    (tmp / ".gitignore").write_text(".gradle/\nbuild/\napp/build/\nlocal.properties\nkeys/\n")
    if out.exists():
        shutil.rmtree(out)
    tmp.rename(out)
    return {"screens": made, "files": sum(1 for _ in out.rglob("*") if _.is_file()), "app_id": app_id}


def screen_path(sid: str) -> str:
    return f"app/src/main/java/hoola/app/screens/{kotlin_name(sid)}.kt"


if __name__ == "__main__":                # CI: python3 gen.py spec.json outdir
    spec_in = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(write_project(spec_in, Path(sys.argv[2]))))
