"""v0.332 IPHONE (App Phase 6): the native iPhone project (Swift + SwiftUI) for the SAME approved app design the Android
app is built from.

The server owns everything: the XcodeGen project file, Info.plist, the asset catalogue (app icon drawn from the design's
icon on her primary colour), the HoolaKit in Swift (theme, shell, components, data, the app's own backend with the offline
outbox, accounts, forms, photos, location, UPI claim, privacy + in-app account deletion) and one SwiftUI file per screen.
A screen the model wrote in SwiftUI is used only if it passes the house rules (`scan_screen`); anything else gets a
code-made screen built from kit blocks (`code_screen`), so the iPhone build never fails because of a screen.

Pure standard library (the Mac runner runs `python3 gen.py spec.json outdir` without the server's packages).

Input = the Android spec (`android/spec.py` build output) plus optional `screens_swift: {sid: swift source}` and
`ios: {bundle_id, team_id, version, build}`."""
from __future__ import annotations

import base64
import json
import re
import shutil
import struct
import sys
import zlib
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,48}$")
CODE_SCREENS = ("seller_info", "privacy", "delete_account")
KIT_SCREENS = ("hoola_login", "hoola_account")
AUTH_IDS = ("login", "signup", "register", "login_staff", "otp_login", "sign_in")
MIN_IOS = "16.0"

# the design's 24 px line icon names -> the closest SF Symbol (Apple's own icon set; no icon files in the app)
SF = {
    "home": "house", "search": "magnifyingglass", "cart": "cart", "bag": "bag", "user": "person", "users": "person.2",
    "bell": "bell", "heart": "heart", "star": "star", "plus": "plus", "minus": "minus", "x": "xmark", "check": "checkmark",
    "chev-r": "chevron.right", "chev-l": "chevron.left", "chev-d": "chevron.down", "chev-u": "chevron.up",
    "arrow-l": "arrow.left", "arrow-r": "arrow.right", "menu": "line.3.horizontal", "filter": "line.3.horizontal.decrease",
    "sort": "arrow.up.arrow.down", "pin": "mappin.and.ellipse", "clock": "clock", "calendar": "calendar", "phone": "phone",
    "chat": "bubble.left", "mail": "envelope", "share": "square.and.arrow.up", "settings": "gearshape", "gift": "gift",
    "tag": "tag", "percent": "percent", "truck": "truck.box", "package": "shippingbox", "receipt": "doc.text",
    "wallet": "wallet.pass", "pay": "indianrupeesign.circle", "qr": "qrcode", "scan": "qrcode.viewfinder",
    "grid": "square.grid.2x2", "list": "list.bullet", "help": "questionmark.circle", "info": "info.circle",
    "camera": "camera", "image": "photo", "doc": "doc", "file": "doc", "book": "book", "school": "graduationcap",
    "health": "cross.case", "pill": "pills", "store": "storefront", "shop": "storefront", "food": "fork.knife",
    "car": "car", "bike": "bicycle", "map": "map", "globe": "globe", "lock": "lock", "key": "key", "edit": "pencil",
    "trash": "trash", "download": "arrow.down.circle", "upload": "arrow.up.circle", "play": "play.circle",
    "music": "music.note", "video": "video", "mic": "mic", "chart": "chart.bar", "trend": "chart.line.uptrend.xyaxis",
    "dashboard": "gauge", "briefcase": "briefcase", "tool": "wrench.and.screwdriver", "home-2": "building.2",
    "dot": "circle", "sparkle": "sparkles", "fire": "flame", "leaf": "leaf", "sun": "sun.max", "moon": "moon",
}
TAB_WORDS = [("home", "house"), ("cart", "cart"), ("order", "doc.text"), ("book", "calendar"), ("profile", "person"),
             ("account", "person"), ("search", "magnifyingglass"), ("categor", "square.grid.2x2"), ("shop", "storefront"),
             ("menu", "list.bullet"), ("help", "questionmark.circle"), ("support", "questionmark.circle"),
             ("setting", "gearshape"), ("dashboard", "gauge"), ("chat", "bubble.left"), ("notif", "bell"),
             ("wallet", "wallet.pass"), ("pay", "indianrupeesign.circle"), ("course", "book"), ("class", "graduationcap")]

FORM_WORDS = ("book", "form", "enquir", "request", "enrol", "register", "apply", "contact", "feedback", "new_", "add_")
CART_WORDS = ("cart", "checkout", "basket", "order_review")


def swift_name(sid: str) -> str:
    return "Screen" + "".join(p.capitalize() for p in re.split(r"[_\-]+", sid) if p)


def sstr(s: Any) -> str:
    """A Swift string literal."""
    t = str(s if s is not None else "")
    t = t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "").replace("\t", " ")
    return f'"{t}"'


def _hex(v: Any, default: str = "#888888") -> str:
    s = str(v or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", s):
        return s.upper()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", s):
        return "#" + "".join(ch * 2 for ch in s[1:]).upper()
    return default


def symbol_for(sid: str, icon: str = "") -> str:
    if icon in SF:
        return SF[icon]
    for w, sym in TAB_WORDS:
        if w in sid:
            return sym
    return "circle"


def _palette(tk: dict[str, Any]) -> str:
    g = lambda k, d: f'Color(hex: "{_hex(tk.get(k), d)}")'          # noqa: E731
    return ("Palette(bg: " + g("bg", "#FFFFFF") + ", surface: " + g("surface", "#FFFFFF") + ", ink: " + g("ink", "#111111")
            + ", muted: " + g("muted", "#555555") + ", line: " + g("line", "#DDDDDD") + ", primary: " + g("primary", "#3355FF")
            + ", onPrimary: " + g("on_primary", "#FFFFFF") + ", accent: " + g("accent", "#FF8800") + ", tint: " + g("tint", "#EEF0FF") + ")")


def _ids(spec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str], str]:
    scr = [s for s in spec.get("screens", []) if ID_RE.match(str(s.get("id") or ""))]
    ids = [s["id"] for s in scr]
    tabs = [t for t in spec.get("tabs", []) if t in ids][:5]          # iOS shows 5 tabs before "More"
    if not tabs:
        tabs = ids[:min(4, len(ids))]
    start = spec.get("start") if spec.get("start") in ids else (tabs[0] if tabs else (ids[0] if ids else "hoola_account"))
    return scr, ids, tabs, start


def tokens_swift(spec: dict[str, Any]) -> str:
    tk = spec.get("tokens") or {}
    alt = tk.get("alt") or {}
    light, dark = (alt, tk) if tk.get("dark") else (tk, alt or tk)
    mode = str(tk.get("mode") or "both")
    if mode not in ("light", "dark", "both"):
        mode = "both"
    radius = max(4, min(28, int(float(tk.get("radius") or 16))))
    app = spec.get("app") or {}
    scr, ids, tabs, start = _ids(spec)
    label = {s["id"]: s.get("label") or s["id"] for s in scr}
    icon = {s["id"]: symbol_for(s["id"], s.get("icon") or "") for s in scr}
    tab_rows = ",\n        ".join(f"TabSpec(id: {sstr(t)}, label: {sstr(label[t])}, symbol: {sstr(icon[t])})" for t in tabs)
    every = ids + list(CODE_SCREENS) + list(KIT_SCREENS)
    lang = str(app.get("language") or "en")
    return f'''// Made by Hoola App Sahayak from the approved design's tokens. Do not edit: a new design version rewrites it.
import SwiftUI

enum AppTokens {{
    static let appName = {sstr(app.get("name") or "App")}
    static let language = {sstr(lang if lang in ("en", "hi", "hinglish") else "en")}
    static let mode = {sstr(mode)}
    static let radius: CGFloat = {radius}
    static let light = {_palette(light)}
    static let dark = {_palette(dark)}
    static let tabs: [TabSpec] = [
        {tab_rows}
    ]
    static let screenIds: Set<String> = [{", ".join(sstr(x) for x in every)}]
    static let start = {sstr(start)}
    static let baseUrl = {sstr(app.get("base_url") or "")}
    static let appKey = {sstr(app.get("app_key") or "")}
}}
'''


def screens_swift(spec: dict[str, Any]) -> str:
    """The registry: every screen id -> its SwiftUI view (design sign-in screens -> the kit's own)."""
    scr, ids, _, _ = _ids(spec)
    cases = []
    for sid in ids:
        view = "AuthScreen()" if sid in AUTH_IDS else f"{swift_name(sid)}()"
        cases.append(f"    case {sstr(sid)}: return AnyView({view})")
    cases += ['    case "seller_info": return AnyView(SellerScreen())', '    case "privacy": return AnyView(PrivacyScreen())',
              '    case "delete_account": return AnyView(DeleteAccountScreen())', '    case "hoola_login": return AnyView(AuthScreen())',
              '    case "hoola_account": return AnyView(AccountScreen())']
    body = "\n".join(cases)
    return f'''// Made by Hoola App Sahayak from the approved design: which screens exist and which view each id opens.
import SwiftUI

@MainActor
func screenView(_ id: String) -> AnyView {{
    CrashGuard.screen(id)
    switch id {{
{body}
    default: return AnyView(Page(id) {{ Muted(Words.nothingYet) }})
    }}
}}
'''


def app_swift(spec: dict[str, Any]) -> str:
    return '''// Made by Hoola App Sahayak. The app's start: her server address + app key, saved data, the signed-in user, the outbox.
import SwiftUI

@main
struct HoolaApp: App {
    init() {
        Cloud.base = AppTokens.baseUrl
        Cloud.key = AppTokens.appKey
        #if DEBUG
        // Hoola's simulator check may point a debug build at a test server on the Mac (http://127.0.0.1 only)
        let a = ProcessInfo.processInfo.arguments
        if let i = a.firstIndex(of: "-hoola_base"), i + 1 < a.count { Cloud.base = a[i + 1] }
        #endif
        CrashGuard.install()
        AppData.shared.load()
        Auth.shared.load()
        Db.shared.load()
    }

    var body: some Scene {
        WindowGroup {
            RootView(start: HoolaApp.debugStart)
                .task {
                    await CrashGuard.sendPending()
                    await AppData.shared.refresh()
                    await Db.shared.sync()
                    #if DEBUG
                    if ProcessInfo.processInfo.arguments.contains("-hoola_e2e") { await E2e.run() }
                    #endif
                }
        }
    }

    /// Debug builds only: `-hoola_screen <id>` opens one screen directly (the simulator check photographs each one).
    static var debugStart: String? {
        #if DEBUG
        let a = ProcessInfo.processInfo.arguments
        if let i = a.firstIndex(of: "-hoola_screen"), i + 1 < a.count { return a[i + 1] }
        #endif
        return nil
    }
}
'''


# ---------------------------------------------------------------- the code-made screen (always compiles)
def code_screen(s: dict[str, Any], ids: list[str], tabs: list[str], backend: dict[str, Any] | None = None) -> str:
    """A plain, honest SwiftUI screen built only from kit blocks - the same decisions as the Android `fallback_screen`:
    a server list shows the user's REAL rows, a cart places a real order, a booking / enquiry screen gets that list's
    own form with a button that really saves, a catalogue list shows its cards, then the screen's actions."""
    sid = s["id"]
    lists = [x for x in (s.get("lists") or []) if re.fullmatch(r"[a-z][a-z0-9_]*", str(x))]
    lst = lists[0] if lists else ""
    acts = [a for a in (s.get("actions") or []) if a.get("go") in ids and a.get("go") != sid][:4]
    colls = {str(c.get("key")): c for c in (backend or {}).get("collections") or []
             if isinstance(c, dict) and ID_RE.match(str(c.get("key") or ""))}
    order = str((backend or {}).get("order") or "")
    rows: list[str] = []
    if s.get("purpose"):
        rows.append(f"            Muted({sstr(s['purpose'])})")
    form = ""
    if order in colls and any(w in sid for w in CART_WORDS):
        form = order
    elif any(w in sid for w in FORM_WORDS):
        form = next((k for k, c in colls.items() if k != order and (c.get("rules") or {}).get("create") in ("public", "member")), "")
    live = lst if lst in colls and not form else ""
    if form:
        rows.append(f"            FormBlock(coll: {sstr(form)})")
    elif live:
        rows.append(f"            RowsSection(coll: {sstr(live)})")
    elif any(w in sid for w in CART_WORDS):
        rows.append("            CartList()")
    elif lst:
        nxt = next((a["go"] for a in acts), "")
        rows.append(f"            ListBlock(list: {sstr(lst)}, next: {sstr(nxt)})")
    else:
        rows.append("            Muted(AppData.shared.facts.s(\"tagline\"))")
    if sid in ("profile", "account", "me", "my_account", "settings") and colls:
        rows.append("            AccountButton()")
    for a in acts:
        rows.append(f"            MainButton(text: {sstr(a.get('label') or a['go'])}, tonal: true) {{ Router.shared.go({sstr(a['go'])}) }}")
    body = "\n".join(rows)
    return f'''// Made by Hoola App Sahayak (simple version made by code).
import SwiftUI

struct {swift_name(sid)}: View {{
    var body: some View {{
        Page({sstr(s.get("label") or sid)}) {{
{body}
        }}
    }}
}}
'''


# ---------------------------------------------------------------- what a model-written SwiftUI screen may contain
ALLOWED_IMPORT = {"SwiftUI", "Foundation", "Charts", "MapKit", "PhotosUI"}
BANNED = [
    (r"\bSecureField\b", "password / PIN fields are not allowed (sign-in is the kit's AuthScreen)"),
    (r"(?i)\b(card ?number|cvv|cvc|upi ?pin|mpin|atm ?pin)\b", "card / CVV / UPI PIN text is not allowed"),
    (r"\bURLSession\b|\bURLRequest\b|\bNWConnection\b|\bFileManager\b", "screens never touch the network or files (the kit does)"),
    (r"\bProcess\(|\bNSClassFromString\b|\bdlopen\b|\bperform\(Selector|\bMirror\(", "no processes / reflection"),
    (r"\bWKWebView\b|\bSFSafariViewController\b|UIApplication\.shared", "no web views / raw app opens (use openLink)"),
    (r"\bUserDefaults\b|\bKeychain\b|\bSecItem\w*\b|@AppStorage", "storage only through the kit"),
    (r"\bprint\(|\bNSLog\(|\bos_log\b|\bLogger\(", "no logging"),
    (r"@main\b|\bstruct\s+\w+\s*:\s*App\b", "the app start is the kit's"),
]


def scan_screen(src: str, sid: str, ids: list[str]) -> list[str]:
    """Problems that must be fixed before a model-written screen is used (house rules, not compile errors)."""
    p: list[str] = []
    if not re.search(rf"\bstruct\s+{swift_name(sid)}\s*:\s*View\b", src):
        p.append(f"must define struct {swift_name(sid)}: View (no parameters needed to create it)")
    for imp in re.findall(r"^\s*import\s+(\w+)", src, re.M):
        if imp not in ALLOWED_IMPORT:
            p.append(f"import not allowed: {imp}")
    for rx, why in BANNED:
        m = re.search(rx, src)
        if m:
            p.append(f"{why} ({m.group(0)})")
    for go in re.findall(r"\.go\(\s*\"([^\"]+)\"", src):
        if go not in ids and go not in KIT_SCREENS and go not in CODE_SCREENS:
            p.append(f'Router.shared.go("{go}"): no such screen (use one of the SCREEN IDS)')
    if len(src) > 60000:
        p.append("screen file too long (max 60 KB)")
    if re.search(r"^\s*(final\s+)?class\s+\w+", src, re.M):
        p.append("screens contain only SwiftUI views (no classes)")
    return p


# ---------------------------------------------------------------- the app icon (a PNG drawn by code: her colour + a glyph)
def _png(w: int, h: int, px: bytearray) -> bytes:
    raw = b"".join(b"\x00" + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def icon_png(bg_hex: str, fg_hex: str, letter: str = "", size: int = 1024) -> bytes:
    """A 1024 px opaque app icon (the App Store refuses transparency): her primary colour with a soft ring and her
    initial's blocky monogram. Pure Python, no Pillow on the Mac runner."""
    bg = bytes.fromhex(_hex(bg_hex, "#3355FF")[1:])
    fg = bytes.fromhex(_hex(fg_hex, "#FFFFFF")[1:])
    px = bytearray(bg * (size * size))
    c = size / 2
    r_out, r_in = size * 0.36, size * 0.31

    def put(x: int, y: int, col: bytes, a: float = 1.0) -> None:
        i = (y * size + x) * 3
        for k in range(3):
            px[i + k] = int(px[i + k] * (1 - a) + col[k] * a)
    for y in range(size):
        dy = (y - c) ** 2
        for x in range(int(c - r_out) - 2, int(c + r_out) + 3):
            d = (dy + (x - c) ** 2) ** 0.5
            if r_in <= d <= r_out:
                put(x, y, fg, 0.9)
    glyph = _GLYPHS.get((letter or "H")[:1].upper(), _GLYPHS["H"])
    cell = int(size * 0.07)
    gx, gy = int(c - 2.5 * cell), int(c - 3.5 * cell)
    for j, row in enumerate(glyph):
        for i, ch in enumerate(row):
            if ch == "#":
                for y in range(gy + j * cell, gy + (j + 1) * cell):
                    for x in range(gx + i * cell, gx + (i + 1) * cell):
                        put(x, y, fg)
    return _png(size, size, px)


_GLYPHS = {ch: rows for ch, rows in {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
}.items()}


# ---------------------------------------------------------------- project files
def bundle_id(spec: dict[str, Any]) -> str:
    ios = spec.get("ios") or {}
    bid = str(ios.get("bundle_id") or (spec.get("app") or {}).get("app_id") or "in.hoola.preview.app")
    bid = bid.replace("_", "-")                  # an iOS bundle id allows letters, digits, '-' and '.'
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9\-]*(\.[A-Za-z][A-Za-z0-9\-]*){1,6}", bid):
        raise ValueError(f"bad bundle id {bid}")
    return bid


def uses_location(spec: dict[str, Any]) -> bool:
    return any(f.get("type") == "location" for c in ((spec.get("seed") or {}).get("backend") or {}).get("collections") or []
               for f in (c.get("fields") or []) if isinstance(f, dict))


def uses_photos(spec: dict[str, Any]) -> bool:
    return any(f.get("type") == "photo" for c in ((spec.get("seed") or {}).get("backend") or {}).get("collections") or []
               for f in (c.get("fields") or []) if isinstance(f, dict))


def project_yml(spec: dict[str, Any]) -> str:
    app = spec.get("app") or {}
    ios = spec.get("ios") or {}
    name = re.sub(r"[^A-Za-z0-9]", "", str(app.get("name") or "HoolaApp"))[:40] or "HoolaApp"
    version = re.sub(r"[^0-9.]", "", str(ios.get("version") or app.get("version_name") or "1.0")) or "1.0"
    build = str(int(ios.get("build") or app.get("version_code") or 1))
    team = re.sub(r"[^A-Z0-9]", "", str(ios.get("team_id") or ""))[:10]
    team_line = f"\n        DEVELOPMENT_TEAM: {team}" if team else ""
    return f'''# Made by Hoola App Sahayak. XcodeGen turns this into the Xcode project on the Mac (xcodegen generate).
name: {name}
options:
  bundleIdPrefix: in.hoola
  deploymentTarget:
    iOS: "{MIN_IOS}"
  createIntermediateGroups: true
settings:
  base:
    SWIFT_VERSION: "5.0"
    MARKETING_VERSION: "{version}"
    CURRENT_PROJECT_VERSION: "{build}"
    TARGETED_DEVICE_FAMILY: "1"
    ENABLE_USER_SCRIPT_SANDBOXING: YES
targets:
  App:
    type: application
    platform: iOS
    deploymentTarget: "{MIN_IOS}"
    scheme: {{}}
    sources:
      - path: Sources
      - path: Resources
    info:
      path: Info.plist
      properties: {{}}
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: {bundle_id(spec)}
        PRODUCT_NAME: "{name}"
        INFOPLIST_FILE: Info.plist
        ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
        CODE_SIGN_STYLE: Automatic{team_line}
        GENERATE_INFOPLIST_FILE: NO
'''


def _plist_str(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def info_plist(spec: dict[str, Any]) -> str:
    app = spec.get("app") or {}
    name = _plist_str(str(app.get("name") or "App"))[:30]
    extra = ""
    if uses_location(spec):
        extra += ("    <key>NSLocationWhenInUseUsageDescription</key>\n"
                  "    <string>Your location is added to your order or request only when you tap Use my location.</string>\n")
    if uses_photos(spec):
        extra += ("    <key>NSPhotoLibraryUsageDescription</key>\n"
                  "    <string>Pick a photo to send with your request. Only the photo you choose is used.</string>\n")
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>{name}</string>
    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$(PRODUCT_NAME)</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$(MARKETING_VERSION)</string>
    <key>CFBundleVersion</key>
    <string>$(CURRENT_PROJECT_VERSION)</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>ITSAppUsesNonExemptEncryption</key>
    <false/>
    <key>LSApplicationQueriesSchemes</key>
    <array>
        <string>upi</string>
        <string>tel</string>
    </array>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsLocalNetworking</key>
        <true/>
    </dict>
    <key>UILaunchScreen</key>
    <dict/>
    <key>UIApplicationSceneManifest</key>
    <dict>
        <key>UIApplicationSupportsMultipleScenes</key>
        <false/>
    </dict>
    <key>UISupportedInterfaceOrientations</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
    </array>
{extra}</dict>
</plist>
'''


def privacy_manifest() -> str:
    """PrivacyInfo.xcprivacy (Apple requires it since 2024): no tracking; UserDefaults read for the app's own data."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyTracking</key>
    <false/>
    <key>NSPrivacyTrackingDomains</key>
    <array/>
    <key>NSPrivacyCollectedDataTypes</key>
    <array/>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>CA92.1</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
'''


def write_project(spec: dict[str, Any], out: Path) -> dict[str, Any]:
    out = Path(out)
    tmp = out.with_name(out.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(TEMPLATE, tmp)
    bid = bundle_id(spec)
    src = tmp / "Sources"
    (src / "App").mkdir(parents=True, exist_ok=True)
    (src / "Screens").mkdir(parents=True, exist_ok=True)
    (src / "App/AppTokens.swift").write_text(tokens_swift(spec))
    (src / "App/AppScreens.swift").write_text(screens_swift(spec))
    (src / "App/HoolaApp.swift").write_text(app_swift(spec))
    scr, ids, tabs, _ = _ids(spec)
    backend = (spec.get("seed") or {}).get("backend") or {}
    given = spec.get("screens_swift") or {}
    made: dict[str, str] = {}
    for s in scr:
        sid = s["id"]
        if sid in AUTH_IDS:
            made[sid] = "kit"
            continue
        code = given.get(sid)
        if code and not scan_screen(code, sid, ids):
            made[sid] = "model"
        else:
            code = code_screen(s, ids, tabs, backend)
            made[sid] = "code"
        (src / "Screens" / f"{swift_name(sid)}.swift").write_text(code)
    res = tmp / "Resources"
    res.mkdir(exist_ok=True)
    (res / "seed.json").write_text(json.dumps(spec.get("seed") or {}, ensure_ascii=False))
    (res / "PrivacyInfo.xcprivacy").write_text(privacy_manifest())
    tk = spec.get("tokens") or {}
    icon_dir = res / "Assets.xcassets/AppIcon.appiconset"
    icon_dir.mkdir(parents=True, exist_ok=True)
    (res / "Assets.xcassets/Contents.json").write_text(json.dumps({"info": {"author": "hoola", "version": 1}}))
    (icon_dir / "Contents.json").write_text(json.dumps({
        "images": [{"filename": "icon.png", "idiom": "universal", "platform": "ios", "size": "1024x1024"}],
        "info": {"author": "hoola", "version": 1}}))
    name = str((spec.get("app") or {}).get("name") or "H")
    letter = next((ch for ch in name.upper() if "A" <= ch <= "Z"), "H")
    given_icon = (spec.get("ios") or {}).get("icon_png_b64")
    png = base64.b64decode(given_icon) if given_icon else icon_png(tk.get("primary") or "#3355FF", tk.get("on_primary") or "#FFFFFF", letter)
    (icon_dir / "icon.png").write_bytes(png)
    (tmp / "project.yml").write_text(project_yml(spec))
    (tmp / "Info.plist").write_text(info_plist(spec))
    # the simulator check travels with the project (screens to open, bundle id)
    qa = tmp / "hoola_qa"
    qa.mkdir(exist_ok=True)
    shutil.copy(HERE / "sim_check.sh", qa / "sim_check.sh")
    (qa / "sim_check.sh").chmod(0o755)
    (qa / "bundle.txt").write_text(bid + "\n")
    (qa / "screens.txt").write_text(" ".join([x for x in ids if x not in AUTH_IDS] + list(CODE_SCREENS) + list(KIT_SCREENS)) + "\n")
    (tmp / ".gitignore").write_text("build/\n*.xcodeproj/\nDerivedData/\nqa/\n")
    if out.exists():
        shutil.rmtree(out)
    tmp.rename(out)
    return {"screens": made, "files": sum(1 for _ in out.rglob("*") if _.is_file()), "bundle_id": bid}


def screen_path(sid: str) -> str:
    return f"Sources/Screens/{swift_name(sid)}.swift"


ERR_RE = re.compile(r"/Sources/Screens/(Screen\w+)\.swift:(\d+):\d+: error: (.+)")


def screen_errors(log: str) -> dict[str, list[str]]:
    """xcodebuild output -> {screen file name: [errors]} (a screen that won't compile is replaced by its code-made one)."""
    out: dict[str, list[str]] = {}
    for m in ERR_RE.finditer(log or ""):
        out.setdefault(m.group(1), [])
        if len(out[m.group(1)]) < 8:
            out[m.group(1)].append(f"line {m.group(2)}: {m.group(3)[:200]}")
    return out


if __name__ == "__main__":                # Mac runner / CI: python3 gen.py spec.json outdir
    spec_in = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(write_project(spec_in, Path(sys.argv[2]))))
