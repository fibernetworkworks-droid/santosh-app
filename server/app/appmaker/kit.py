"""v0.128 The app UI kit: design tokens per style, 80 original line icons, the native-looking shell drawn by code
(status bar, Android navigation bar / iOS tab bar, back buttons), the six screens that are always written by code
(splash, DPDP consent, notification pre-ask, seller details + grievance officer, privacy policy, delete account) and
the assembly of every screen into one clickable prototype:

  data/apps/<tenant>/<app>/live/ index.html (all screens, ?s=<screen>&p=android|ios), all.html (every screen at once),
  assets/{app-kit.css, proto.js, tokens.css, screens.css, icon.svg, logo.*, fonts/...}

The same tokens and screen specs are the contract the native Kotlin / SwiftUI build (next version) follows."""
from __future__ import annotations

import html as _html
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

from ..site import build as SB
from ..site import taxonomy as ST
from . import taxonomy as T

log = logging.getLogger("santosh.app")
ASSETS = Path(__file__).resolve().parent / "assets"
PLATFORMS = ("android", "ios")


def root() -> Path:
    return Path(os.environ.get("APP_DIR", "data/apps"))


def app_dir(tenant: str, app_id: str) -> Path:
    p = root() / re.sub(r"[^\w-]", "_", tenant)[:64] / re.sub(r"[^\w-]", "_", app_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def src_dir(tenant: str, app_id: str) -> Path:
    p = app_dir(tenant, app_id) / "src" / "screens"
    p.mkdir(parents=True, exist_ok=True)
    return p.parent


def esc(s: Any) -> str:
    return _html.escape(str(s or ""), quote=True)


# ---------------------------------------------------------------- tokens (v0.128.1: any colour, any font, full structure, light + dark)
STRUCT_KEYS = ("nav", "fab", "card", "button", "header", "transition", "texture")
VAR_KEYS = ("bg", "surface", "ink", "muted", "line", "primary", "on_primary", "accent", "on_accent", "primary_text", "accent_text")


def _lum(hexc: str) -> float:
    h = hexc.lstrip("#")
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return 1.0
    f = [(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4) for c in (r, g, b)]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def _colors(palette: str, brand: dict[str, str] | None, ov: dict[str, Any]) -> dict[str, str]:
    from . import colors as CL
    pal = CL.palettes().get(palette) or CL.palettes()["paper_ink"]
    out = {k: pal[k] for k in ("bg", "surface", "ink", "primary", "accent")}
    for k in ("primary", "accent"):
        if brand and SB._hex_ok(brand.get(k, "")):
            out[k] = brand[k]
    for k in ("bg", "surface", "ink", "primary", "accent"):
        if SB._hex_ok(str(ov.get(k, ""))):
            out[k] = ov[k]
    return out


def tokens(style: str, palette: str, brand: dict[str, str] | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Colours (palette < her brand < what she asked), font pair or named fonts, the style's structure (any part
    replaceable), light / dark mode + the other mode's colours, all contrast-fixed."""
    from . import colors as CL
    from . import designsys as DS
    from . import fonts as FN
    style = style if style in T.STYLES else "clean_commerce"
    st = T.STYLES[style]
    ov = dict(overrides or {})
    cols = _colors(palette, brand, ov)
    tk = SB.tokens("editorial_calm", "paper_ink", None, {**cols, "radius": ov.get("radius", st["radius"])})
    pair = FN.pairs().get(ov.get("fonts") or st["fonts"]) or FN.pairs()[st["fonts"]]
    head, body, deva = pair["head"], pair["body"], pair["deva"]
    for k, slot in (("font_head", "head"), ("font_body", "body")):
        if ov.get(k):
            rec = FN.find(str(ov[k]))
            if rec:
                head, body = (rec["family"], body) if slot == "head" else (head, rec["family"])
    tables = {"nav": DS.NAV, "fab": DS.FAB, "card": DS.CARDS, "button": DS.BUTTONS, "header": DS.HEADERS}
    struct = {}
    for k in STRUCT_KEYS:
        v = ov.get(k, st[k])
        if k == "transition":
            v = v if v in {m["web"] for m in DS.MOTION.values() if m["kind"] == "transition"} else st[k]
        elif k == "texture":
            v = v if (v in DS.TEXTURES or v == "") else st[k]
        else:
            v = v if v in tables[k] else st[k]
        struct[k] = v
    dark = _lum(tk["bg"]) < 0.2
    mode = ov.get("mode") if ov.get("mode") in ("light", "dark", "both") else "both"
    if dark:
        other = CL.harmony(tk["primary"], "complementary", False, tk["accent"])
    else:
        other = CL.dark_of(tk)
    alt = SB.tokens("editorial_calm", "paper_ink", None, {**{k: other[k] for k in ("bg", "surface", "ink", "primary", "accent")},
                                                         "radius": ov.get("radius", st["radius"])})
    if (mode == "dark" and not dark) or (mode == "light" and dark):     # she wants the other mode as the app's own
        tk, alt, dark = alt, tk, not dark
    tk.update({"style": style, "palette": palette, "fonts": ov.get("fonts") or st["fonts"], "head": head, "body": body,
               "deva": deva, **struct, "dark": dark, "mode": mode, "alt": {k: alt[k] for k in VAR_KEYS},
               "colors_from": ov.get("colors_from", "")})
    return tk


def font_files(tk: dict[str, Any], language: str = "") -> list[tuple[str, str, int, Path]]:
    """[(family, subset, weight, file)] the prototype needs: head + body (latin), the Devanagari face, and the face of
    her language's script (Bengali, Tamil, Telugu ... ) when the app is in that language."""
    from . import fonts as FN
    want: list[tuple[str, tuple[str, ...]]] = [(tk["head"], ("latin",)), (tk["body"], ("latin",)), (tk["deva"], ("devanagari", "latin"))]
    script = FN.SCRIPT_OF_LANG.get(language or "")
    if script and script != "devanagari":
        want.append((FN.SCRIPT_DEFAULT[script], (script, "latin")))
    out, seen = [], set()
    for fam, subs in want:
        for sub, w, f in FN.ensure(fam, subs):
            if (fam, sub, w) not in seen:
                seen.add((fam, sub, w))
                out.append((fam, sub, w, f))
    return out


def _vars(t: dict[str, Any]) -> str:
    return (f"--c-bg:{t['bg']};--c-surface:{t['surface']};--c-ink:{t['ink']};--c-muted:{t['muted']};--c-line:{t['line']};"
            f"--c-primary:{t['primary']};--c-on-primary:{t['on_primary']};--c-accent:{t['accent']};--c-on-accent:{t['on_accent']};"
            f"--c-primary-text:{t['primary_text']};--c-accent-text:{t['accent_text']};"
            f"--c-tint:color-mix(in srgb,{t['primary']} 12%,{t['surface']});--c-tint-2:color-mix(in srgb,{t['accent']} 14%,{t['surface']});"
            f"--c-scrim:{'rgba(0,0,0,.6)' if _lum(t['bg']) < 0.2 else 'rgba(15,15,20,.42)'};"
            f"--neu-hi:{'rgba(255,255,255,.07)' if _lum(t['bg']) < 0.2 else 'rgba(255,255,255,.9)'};"
            f"--neu-lo:{'rgba(0,0,0,.55)' if _lum(t['bg']) < 0.2 else 'color-mix(in srgb,' + t['ink'] + ' 16%,transparent)'};")


def tokens_css(tk: dict[str, Any], fonts: list[tuple[str, str, int, str]] | None = None) -> str:
    """tokens.css (in assets/): @font-face per script, the base colours, the other mode under body.mode-alt, textures."""
    from . import designsys as DS
    from . import fonts as FN
    faces = FN.face_css(fonts or [])
    script_fams = "".join(f",'{f}'" for f in dict.fromkeys(x[0] for x in (fonts or []) if x[1] not in ("latin", "devanagari")))
    head = f"'{tk['head']}','{tk['deva']}'{script_fams},system-ui,sans-serif"
    body = f"'{tk['body']}','{tk['deva']}'{script_fams},system-ui,sans-serif"
    root = (":root{" + _vars(tk) + f"--font-head:{head};--font-body:{body};--radius:{tk['radius']}px;--gutter:20px;"
            f"--btn-radius:{_btn_radius(tk)};--card-radius:{max(4, int(tk['radius']))}px" + "}")
    alt = "body.mode-alt{" + _vars({**tk, **tk["alt"]}) + "}"
    return "\n".join([faces, root, alt, DS.textures_css(tk), DS.textures_css({**tk, **tk["alt"]}, True)])


def _btn_radius(tk: dict[str, Any]) -> str:
    return {"pill": "999px", "square": "4px", "chunky": f"{max(10, int(tk['radius']))}px", "soft": "18px",
            "gradient": "999px"}.get(tk.get("button", ""), f"{max(8, int(tk['radius']) - 2)}px")


# ---------------------------------------------------------------- 80 line icons (original, 24 px grid, stroke = currentColor)
_C = lambda cx, cy, r: f'<circle cx="{cx}" cy="{cy}" r="{r}"/>'          # noqa: E731
_R = lambda x, y, w, h, rx=0: f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>'  # noqa: E731
_P = lambda d: f'<path d="{d}"/>'                                         # noqa: E731
ICONS: dict[str, str] = {
    "home": _P("M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"),
    "search": _C(11, 11, 7) + _P("M20 20l-4-4"),
    "cart": _P("M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.6L21 8H6") + _C(10, 20.5, 1.3) + _C(18, 20.5, 1.3),
    "bag": _P("M5 8h14l-1 12H6z") + _P("M9 8V6a3 3 0 0 1 6 0v2"),
    "user": _C(12, 8, 4) + _P("M4 21a8 8 0 0 1 16 0"),
    "users": _C(9, 8, 3.5) + _P("M2.5 20a6.5 6.5 0 0 1 13 0") + _P("M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6 6 0 0 1 3.5 6"),
    "bell": _P("M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z") + _P("M10 21h4"),
    "heart": _P("M12 20s-7-4.4-9-9a5 5 0 0 1 9-3 5 5 0 0 1 9 3c-2 4.6-9 9-9 9z"),
    "star": _P("M12 3l2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"),
    "plus": _P("M12 5v14M5 12h14"), "minus": _P("M5 12h14"), "x": _P("M6 6l12 12M18 6L6 18"), "check": _P("M5 12l5 5L20 7"),
    "chev-r": _P("M9 6l6 6-6 6"), "chev-l": _P("M15 6l-6 6 6 6"), "chev-d": _P("M6 9l6 6 6-6"), "chev-u": _P("M6 15l6-6 6 6"),
    "arrow-l": _P("M19 12H5M11 6l-6 6 6 6"), "arrow-r": _P("M5 12h14M13 6l6 6-6 6"),
    "menu": _P("M4 7h16M4 12h16M4 17h16"), "filter": _P("M4 6h16M7 12h10M10 18h4"),
    "sort": _P("M7 4v16M3 16l4 4 4-4M17 20V4M13 8l4-4 4 4"),
    "pin": _P("M12 21s-7-6.3-7-12a7 7 0 0 1 14 0c0 5.7-7 12-7 12z") + _C(12, 9, 2.5),
    "clock": _C(12, 12, 9) + _P("M12 7v5l3 2"),
    "calendar": _R(3, 5, 18, 16, 2) + _P("M3 10h18M8 3v4M16 3v4"),
    "phone": _P("M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"),
    "chat": _P("M4 5h16v11H9l-5 4z"), "mail": _R(3, 5, 18, 14, 2) + _P("M3 7l9 6 9-6"),
    "share": _C(18, 5, 2.5) + _C(6, 12, 2.5) + _C(18, 19, 2.5) + _P("M8.2 10.8l7.6-4.4M8.2 13.2l7.6 4.4"),
    "settings": _C(12, 12, 3) + _P("M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"),
    "gift": _R(3, 8, 18, 5) + _P("M5 13v8h14v-8M12 8v13") + _P("M12 8S10 3 7.5 4.5 9 8 12 8zM12 8s2-5 4.5-3.5S15 8 12 8z"),
    "tag": _P("M3 12V4h8l10 10-8 8z") + _C(7.5, 7.5, 1.3), "percent": _P("M19 5L5 19") + _C(7, 7, 2.5) + _C(17, 17, 2.5),
    "truck": _P("M2 6h11v10H2zM13 9h4l4 4v3h-8") + _C(6, 18, 2) + _C(17, 18, 2),
    "package": _P("M3 7l9-4 9 4v10l-9 4-9-4z") + _P("M3 7l9 4 9-4M12 11v10"),
    "receipt": _P("M6 3h12v18l-3-2-3 2-3-2-3 2z") + _P("M9 8h6M9 12h6"),
    "wallet": _R(3, 6, 18, 14, 2) + _P("M3 10h18") + _C(16.5, 15, 1.2),
    "pay": _R(3, 6, 18, 12, 2) + _P("M7 12h4M14 10l3 2-3 2"),
    "qr": _R(3, 3, 7, 7) + _R(14, 3, 7, 7) + _R(3, 14, 7, 7) + _P("M14 14h3v3h-3zM18 18h3v3h-3zM14 20v1M20 14v1"),
    "scan": _P("M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4M4 12h16"),
    "camera": _P("M4 8h3l2-3h6l2 3h3v12H4z") + _C(12, 13.5, 3.5),
    "image": _R(3, 4, 18, 16, 2) + _C(8.5, 9.5, 1.8) + _P("M21 16l-5-5L5 20"),
    "play": _C(12, 12, 9) + _P("M10 8.5v7l6-3.5z"),
    "book": _P("M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z") + _P("M8 7h7"),
    "cap": _P("M2 9l10-5 10 5-10 5z") + _P("M6 11v5c3 2.5 9 2.5 12 0v-5"),
    "file": _P("M6 3h8l5 5v13H6z") + _P("M14 3v5h5"), "edit": _P("M4 20h4L19 9l-4-4L4 16z"),
    "trash": _P("M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14"),
    "info": _C(12, 12, 9) + _P("M12 11v6M12 7.5v.5"), "help": _C(12, 12, 9) + _P("M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4M12 17v.5"),
    "shield": _P("M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z") + _P("M8.5 12l2.5 2.5 4.5-4.5"),
    "lock": _R(5, 11, 14, 10, 2) + _P("M8 11V8a4 4 0 0 1 8 0v3"), "logout": _P("M10 4H5v16h5M14 8l4 4-4 4M18 12H9"),
    "globe": _C(12, 12, 9) + _P("M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"),
    "lang": _P("M4 5h9M8.5 3v2M6 5c0 4 3 7 6 8M11 5c-1 4-4 7-7 8") + _P("M13 21l4-9 4 9M14.5 18h5"),
    "leaf": _P("M5 19C5 9 11 4 20 4c0 9-5 15-15 15z") + _P("M5 19l8-8"),
    "cake": _P("M4 21h16v-7H4z") + _P("M4 17c2 1 4-1 6 0s4 1 6 0 3-1 4 0M12 14v-4M12 7.5v.5M8 14v-3h8v3"),
    "cup": _P("M4 8h13v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5z") + _P("M17 10h2a2 2 0 0 1 0 4h-2M8 3v2M12 3v2"),
    "food": _P("M4 3v8a3 3 0 0 0 3 3v7M10 3v8M7 3v6M17 21V3c-2 1-3 4-3 8h3"),
    "scissors": _C(6, 7, 2.5) + _C(6, 17, 2.5) + _P("M8 8.5L20 18M8 15.5L20 6"),
    "tooth": _P("M8 3C5 3 3.5 5.5 4 8.5c.4 2.6 1.6 4 2 7 .3 2.5 1 5.5 2.5 5.5S10 18 12 18s2 3 3.5 3 2.2-3 2.5-5.5c.4-3 1.6-4.4 2-7C20.5 5.5 19 3 16 3c-1.6 0-2.6 1-4 1S9.6 3 8 3z"),
    "health": _P("M9 3h6v6h6v6h-6v6H9v-6H3V9h6z"), "dumbbell": _P("M2 12h20M5 8v8M8 6v12M16 6v12M19 8v8"),
    "wrench": _P("M14.5 3.5a5 5 0 0 0-6 6.2L3 15.2 5 19l3.8-2 5.5-5.5a5 5 0 0 0 6.2-6l-3 3-2.5-.5-.5-2.5z"),
    "wifi": _P("M2 9a15 15 0 0 1 20 0M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0") + _C(12, 19, 1),
    "bolt": _P("M13 2L4 14h7l-1 8 9-12h-7z"), "refresh": _P("M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"),
    "download": _P("M12 4v12M7 11l5 5 5-5M4 20h16"), "upload": _P("M12 20V8M7 13l5-5 5 5M4 4h16"),
    "ticket": _P("M3 7h18v4a2 2 0 0 0 0 4v4H3v-4a2 2 0 0 0 0-4z") + _P("M14 7v2M14 12v2M14 17v2"),
    "mic": _R(9, 3, 6, 11, 3) + _P("M5 11a7 7 0 0 0 14 0M12 18v3"),
    "list": _P("M9 6h11M9 12h11M9 18h11") + _C(4.5, 6, 1) + _C(4.5, 12, 1) + _C(4.5, 18, 1),
    "grid": _R(3, 3, 7, 7, 1) + _R(14, 3, 7, 7, 1) + _R(3, 14, 7, 7, 1) + _R(14, 14, 7, 7, 1),
    "navigate": _P("M3 11l18-8-8 18-2-8z"),
    "store": _P("M3 9l2-5h14l2 5M3 9h18v3a3 3 0 0 1-6 0 3 3 0 0 1-6 0 3 3 0 0 1-6 0zM5 12v9h14v-9M10 21v-5h4v5"),
    "award": _C(12, 9, 6) + _P("M8.5 14l-1.5 7 5-3 5 3-1.5-7"), "chart": _P("M4 20V10M10 20V4M16 20v-7M22 20H2"),
    "trend": _P("M3 17l6-6 4 4 8-8M15 7h6v6"), "rupee": _P("M7 4h10M7 8h10M7 4c6 0 6 8 0 8l8 8"),
    "coin": _C(12, 12, 9) + _P("M9 8h6M9 11h6M9 8c4 0 4 6 0 6l5 4"),
    "hourglass": _P("M6 3h12M6 21h12M7 3c0 5 10 7 10 18M17 3c0 5-10 7-10 18"),
    "check-circle": _C(12, 12, 9) + _P("M8 12l3 3 5-6"), "alert": _P("M12 3l10 18H2z") + _P("M12 10v5M12 18v.5"),
    "eye": _P("M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z") + _C(12, 12, 3),
    "sun": _C(12, 12, 4) + _P("M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6 19 19M5 19l1.4-1.4M17.6 6.4 19 5"),
    "moon": _P("M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z"),
    "car": _P("M3 16v-4l2-5h14l2 5v4z") + _C(7, 17, 2) + _C(17, 17, 2) + _P("M3 12h18"),
    "paw": _C(7, 9, 1.8) + _C(12, 6, 1.8) + _C(17, 9, 1.8) + _P("M7.5 18c0-3 2-6 4.5-6s4.5 3 4.5 6c0 2-2 2-4.5 1.5C9.5 20 7.5 20 7.5 18z"),
    "flame": _P("M12 3c3 4 4 6 4 8a4 4 0 0 1-8 0c0-2 1-4 4-8z") + _P("M5 17h14l-2 4H7z"),
    "music": _P("M9 18V5l11-2v13") + _C(6.5, 18, 2.5) + _C(17.5, 16, 2.5),
    "key": _C(8, 15, 4) + _P("M11 12l9-9M17 6l3 3"), "home-repair": _P("M3 11l9-7 9 7M6 9v11h12V9") + _P("M10 20v-5h4v5"),
    "spark": _P("M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"),
    "dot": _C(12, 12, 3), "more": _C(5, 12, 1.4) + _C(12, 12, 1.4) + _C(19, 12, 1.4),
}
_BACK = {"android": ICONS["arrow-l"], "ios": ICONS["chev-l"]}
TAB_ICON = {"home": "home", "categories": "grid", "cart": "cart", "orders": "receipt", "profile": "user", "menu": "food",
            "services": "list", "my_bookings": "calendar", "courses": "book", "timetable": "calendar", "member_card": "qr",
            "request_service": "plus", "job_status": "wrench", "khata": "wallet", "rewards": "gift", "catalogue": "grid",
            "wishlist": "heart", "events": "ticket", "pass": "qr", "updates": "bell", "plans": "award"}


def icon_svg(name: str, cls: str = "ic") -> str:
    body = ICONS.get(name) or ICONS["dot"]
    return (f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def app_icon_svg(tk: dict[str, Any], name: str) -> str:
    letter = esc((re.sub(r"[^\wऀ-ॿ]", "", name or "") or "H")[:1].upper())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{tk["primary"]}"/><stop offset="1" stop-color="{tk["accent"]}"/></linearGradient></defs>'
            f'<rect width="512" height="512" rx="112" fill="url(#g)"/><circle cx="400" cy="112" r="64" fill="#fff" opacity=".14"/>'
            f'<text x="256" y="338" text-anchor="middle" font-family="{esc(tk["head"])},sans-serif" font-weight="700" font-size="260" '
            f'fill="{tk["on_primary"]}">{letter}</text></svg>')


# ---------------------------------------------------------------- text the code screens use (English / Hindi)
L10N: dict[str, dict[str, str]] = {
    "en": {"consent_t": "Before we start", "consent_lead": "We keep only what we need to serve you, and you can take it back any time.",
           "what": "What we keep", "why": "Why", "your_rights": "Your rights", "agree": "I agree to this use of my details",
           "continue": "Continue", "notify_t": "Get updates that matter", "notify_lead": "We tell you when your order, booking or "
           "payment changes, and about offers only if you want them.", "notify_yes": "Yes, notify me", "later": "Not now",
           "seller_t": "Seller details", "grievance": "Grievance officer", "grievance_note": "We acknowledge every complaint within "
           "48 hours and resolve it within one month.", "privacy_t": "Privacy policy", "delete_t": "Delete my account",
           "delete_lead": "This deletes your account and your personal details from this app.", "delete_keep": "Bills we must keep by "
           "law (GST records) are kept for the period the law asks, then deleted.", "delete_btn": "Delete my account",
           "delete_confirm": "Yes, delete everything", "cancel": "Cancel", "deleted": "Request received: your account will be deleted within 7 days.",
           "phone": "Phone", "email": "Email", "address": "Address", "name": "Legal name", "hours": "Timings", "back": "Back"},
    "hi": {"consent_t": "शुरू करने से पहले", "consent_lead": "हम सिर्फ़ उतनी जानकारी रखते हैं जितनी आपकी सेवा के लिए ज़रूरी है; आप कभी भी सहमति वापस ले सकते हैं।",
           "what": "हम क्या रखते हैं", "why": "क्यों", "your_rights": "आपके अधिकार", "agree": "मैं अपनी जानकारी के इस उपयोग के लिए सहमत हूँ",
           "continue": "आगे बढ़ें", "notify_t": "ज़रूरी अपडेट पाएं", "notify_lead": "ऑर्डर, बुकिंग या पेमेंट बदलने पर हम बताएँगे; ऑफ़र सिर्फ़ आपकी मर्ज़ी से।",
           "notify_yes": "हाँ, बताइए", "later": "अभी नहीं", "seller_t": "विक्रेता की जानकारी", "grievance": "शिकायत अधिकारी",
           "grievance_note": "हर शिकायत 48 घंटे में दर्ज और एक महीने में हल की जाती है।", "privacy_t": "प्राइवेसी नीति",
           "delete_t": "मेरा अकाउंट हटाएँ", "delete_lead": "इससे आपका अकाउंट और आपकी निजी जानकारी इस ऐप से हट जाएगी।",
           "delete_keep": "कानून के अनुसार ज़रूरी बिल (GST रिकॉर्ड) उतने समय रखे जाते हैं जितना कानून कहता है, फिर हटा दिए जाते हैं।",
           "delete_btn": "मेरा अकाउंट हटाएँ", "delete_confirm": "हाँ, सब हटाएँ", "cancel": "रद्द करें",
           "deleted": "अनुरोध मिला: 7 दिन में आपका अकाउंट हट जाएगा।", "phone": "फ़ोन", "email": "ईमेल", "address": "पता",
           "name": "कानूनी नाम", "hours": "समय", "back": "वापस"},
}
DATA_KEPT = {
    "shop": ["name and phone number (login, order updates)", "delivery address (only for delivery)", "orders and bills"],
    "food_order": ["name and phone number (login, order updates)", "delivery address (only for delivery)", "orders and bills"],
    "booking": ["name and phone number (login, reminders)", "your bookings and visit history"],
    "learning": ["student / parent name and phone number", "classes, attendance, test scores and fees"],
    "membership": ["name and phone number", "plan, check-ins and progress you enter"],
    "service_request": ["name, phone number and service address", "your requests, photos you add, bills and warranty"],
    "khata": ["name and phone number", "your purchases on credit, payments and points"],
    "catalogue": ["name and phone number (only if you log in)", "items you save and enquiries you send"],
    "events": ["name and phone number", "your registrations and passes"],
    "community": ["nothing unless you contact us or donate (then name, phone number and donation receipts)"],
}


def _t(lang: str, k: str) -> str:
    return (L10N.get("hi" if lang == "hi" else "en") or L10N["en"]).get(k) or L10N["en"][k]


def _ab(title: str, back: bool = True) -> str:
    b = '<button class="ab-back" data-back aria-label="Back"></button>' if back else ""
    return f'<header class="ab">{b}<h1 class="ab-title">{esc(title)}</h1></header>'


def _kv(rows: list[tuple[str, str]]) -> str:
    return '<dl class="kv">' + "".join(f"<dt>{esc(k)}</dt><dd>{esc(v) if v else '<em class=blank>[' + esc(k) + ']</em>'}</dd>"
                                       for k, v in rows) + "</dl>"


def code_screen(sid: str, ctx: dict[str, Any]) -> str:
    """The six legal / system screens, written by code from her facts (never by the model)."""
    f, lang, name = ctx.get("facts") or {}, ctx.get("language") or "en", ctx.get("name") or ""
    goal = ctx.get("goal") or "shop"
    regs = f.get("registrations") or {}
    nxt = ctx.get("first") or "home"
    if sid == "splash":
        tag = esc(f.get("tagline") or "")
        return (f'<section id="scr-splash" class="scr splash" data-screen="splash" data-auto="{esc(nxt)}">'
                f'<div class="splash-in" data-m="pop"><img class="splash-icon" src="assets/icon.svg" alt="{esc(name)} icon">'
                f'<p class="t-h1">{esc(name) or "<em class=blank>[name]</em>"}</p>' + (f'<p class="t-body">{tag}</p>' if tag else "")
                + '<div class="splash-dots" aria-hidden="true"><i></i><i></i><i></i></div></div></section>')
    if sid == "consent":
        kept = "".join(f"<li>{esc(x)}</li>" for x in DATA_KEPT.get(goal, DATA_KEPT["shop"]))
        return (f'<section id="scr-consent" class="scr" data-screen="consent">{_ab(_t(lang, "consent_t"), False)}<div class="body">'
                f'<p class="t-body">{esc(_t(lang, "consent_lead"))}</p><div class="card"><p class="t-label">{esc(_t(lang, "what"))}</p>'
                f'<ul class="bul">{kept}</ul><p class="t-label">{esc(_t(lang, "why"))}</p><p class="t-small">To give you the '
                f'service you ask for in this app. We never sell your details. Payments happen in your own UPI app.</p>'
                f'<p class="t-label">{esc(_t(lang, "your_rights"))}</p><p class="t-small">See, correct or delete your details, or '
                f'withdraw consent, from Profile; complaints go to our grievance officer, then the Data Protection Board of India.</p>'
                f'</div><label class="check-row"><input type="checkbox" data-consent> <span>{esc(_t(lang, "agree"))}</span></label>'
                f'<button class="btn btn-primary btn-block" data-go="{esc(ctx.get("after_consent") or nxt)}" data-needs-consent disabled>'
                f'{esc(_t(lang, "continue"))}</button><button class="btn btn-ghost btn-sm" data-go="privacy">'
                f'{esc(_t(lang, "privacy_t"))}</button></div></section>')
    if sid == "notify_permission":
        return (f'<section id="scr-notify_permission" class="scr" data-screen="notify_permission">{_ab("", True)}'
                f'<div class="body center"><div class="hero-ic" data-m="pop">{icon_svg("bell")}</div>'
                f'<p class="t-h1">{esc(_t(lang, "notify_t"))}</p><p class="t-body muted">{esc(_t(lang, "notify_lead"))}</p>'
                f'<button class="btn btn-primary btn-block" data-go="{esc(nxt)}" data-toast="OK">{esc(_t(lang, "notify_yes"))}</button>'
                f'<button class="btn btn-ghost btn-block" data-go="{esc(nxt)}">{esc(_t(lang, "later"))}</button></div></section>')
    if sid == "seller_info":
        rows = [(_t(lang, "name"), f.get("legal_name") or name), (_t(lang, "address"), f.get("address") or ""),
                (_t(lang, "phone"), f.get("phone") or f.get("whatsapp") or ""), (_t(lang, "email"), f.get("email") or "")]
        for k, label in (("gstin", "GSTIN"), ("fssai", "FSSAI"), ("drug_licence", "Drug licence"), ("rera", "RERA"),
                         ("registration", "Registration")):
            if regs.get(k):
                rows.append((label, regs[k]))
        g = [(_t(lang, "name").replace("Legal ", "").replace("कानूनी ", ""), f.get("grievance_officer") or f.get("owner") or ""),
             (_t(lang, "phone"), f.get("grievance_phone") or f.get("phone") or ""), (_t(lang, "email"), f.get("grievance_email") or f.get("email") or "")]
        return (f'<section id="scr-seller_info" class="scr" data-screen="seller_info">{_ab(_t(lang, "seller_t"))}<div class="body">'
                f'<div class="card">{_kv(rows)}</div><p class="t-label">{esc(_t(lang, "grievance"))}</p><div class="card">{_kv(g)}'
                f'<p class="t-small muted">{esc(_t(lang, "grievance_note"))}</p></div></div></section>')
    if sid == "privacy":
        who = esc(name) or "<em class=blank>[name]</em>"
        kept = "".join(f"<li>{esc(x)}</li>" for x in DATA_KEPT.get(goal, DATA_KEPT["shop"]))
        contact = esc(f.get("grievance_email") or f.get("email") or f.get("phone") or "") or "<em class=blank>[contact]</em>"
        return (f'<section id="scr-privacy" class="scr" data-screen="privacy">{_ab(_t(lang, "privacy_t"))}<div class="body prose">'
                f'<p>This app is run by {who}. This policy says what we collect, why, and your choices.</p>'
                f'<h2>What we collect</h2><ul class="bul">{kept}</ul><h2>Why</h2><p>Only to provide the service you ask for '
                f'(orders, bookings, reminders, bills) and to answer you. We do not sell or rent your details and we do not show '
                f'ads from other companies.</p><h2>Who else sees it</h2><p>Nobody, except service providers that help us run '
                f'the app (hosting, messages) under contract, and authorities when the law requires. Payments are made in your '
                f'own UPI app; we never see your card or UPI PIN.</p><h2>How long</h2><p>While your account is active; bills '
                f'are kept as tax law requires. Delete your account any time from Profile.</p><h2>Your rights</h2><p>See, '
                f'correct or delete your details and withdraw consent (Digital Personal Data Protection Act, 2023). If we do '
                f'not resolve a complaint you may approach the Data Protection Board of India.</p><h2>Children</h2><p>Users '
                f'under 18 use the app only with a parent\'s consent; we do not track them or show them ads.</p>'
                f'<h2>Contact</h2><p>{contact}</p></div></section>')
    if sid == "delete_account":
        return (f'<section id="scr-delete_account" class="scr" data-screen="delete_account">{_ab(_t(lang, "delete_t"))}'
                f'<div class="body"><div class="hero-ic danger">{icon_svg("trash")}</div><p class="t-body">{esc(_t(lang, "delete_lead"))}</p>'
                f'<p class="t-small muted">{esc(_t(lang, "delete_keep"))}</p><button class="btn btn-danger btn-block" '
                f'data-sheet="del-sure">{esc(_t(lang, "delete_btn"))}</button></div><div class="sheet" id="del-sure" role="dialog">'
                f'<div class="sheet-handle"></div><p class="t-title">{esc(_t(lang, "delete_t"))}?</p><button class="btn btn-danger '
                f'btn-block" data-close data-toast="{esc(_t(lang, "deleted"))}">{esc(_t(lang, "delete_confirm"))}</button>'
                f'<button class="btn btn-ghost btn-block" data-close>{esc(_t(lang, "cancel"))}</button></div></section>')
    raise KeyError(sid)


# ---------------------------------------------------------------- the shell + assembly
STATUS = {"android": ('<div class="sb sb-android" aria-hidden="true"><span>9:41</span><span class="sb-ic">'
                      + icon_svg("wifi", "sbi") + '<i class="sb-sig"></i><i class="sb-bat"></i></span></div>'),
          "ios": ('<div class="sb sb-ios" aria-hidden="true"><span>9:41</span><i class="sb-island"></i><span class="sb-ic">'
                  '<i class="sb-sig"></i>' + icon_svg("wifi", "sbi") + '<i class="sb-bat"></i></span></div>')}


def expand(html: str) -> str:
    """<i data-ic="cart"></i> -> inline SVG; back buttons get both platform glyphs; the logo placeholder gets its file."""
    def ic(m: re.Match) -> str:
        attrs = m.group(1)
        name = re.search(r'data-ic=["\']([\w-]+)["\']', attrs)
        cls = re.search(r'class=["\']([^"\']*)["\']', attrs)
        return icon_svg(name.group(1) if name else "dot", "ic " + (cls.group(1) if cls else "")).replace('class="ic "', 'class="ic"')
    html = re.sub(r"<i\b([^>]*\bdata-ic=[^>]*)>\s*</i>", ic, html)
    html = re.sub(r'(<button\b[^>]*class="[^"]*\bab-back\b[^"]*"[^>]*>)\s*(</button>)',
                  lambda m: m.group(1) + icon_svg("arrow-l", "ic back-a") + icon_svg("chev-l", "ic back-i") + m.group(2), html)
    html = re.sub(r"<img\b([^>]*\bdata-logo\b[^>]*?)\s*/?>",
                  lambda m: "<img" + re.sub(r'\ssrc=["\'][^"\']*["\']', "", m.group(1)) + ' src="assets/logo.png">', html)
    return html


PRIMARY = {"shop": ("cart", "cart"), "food_order": ("cart", "cart"), "booking": ("slot_picker", "calendar"),
           "learning": ("courses", "book"), "membership": ("checkin", "qr"), "service_request": ("request_service", "plus"),
           "khata": ("payment", "pay"), "catalogue": ("enquiry", "chat"), "events": ("events", "ticket"), "community": ("donate", "heart")}
GO_ICON = {"cart": "cart", "checkout": "bag", "payment": "pay", "slot_picker": "calendar", "services": "list", "courses": "book",
           "timetable": "calendar", "checkin": "qr", "member_card": "qr", "request_service": "plus", "job_status": "wrench",
           "khata": "wallet", "enquiry": "chat", "events": "ticket", "donate": "heart", "search": "search", "offers": "tag",
           "orders": "receipt", "store_info": "store", "support": "help", "notifications": "bell", "profile": "user",
           "privacy": "shield", "seller_info": "info", "delete_account": "trash", "menu": "food", "updates": "bell",
           "gallery": "image", "rewards": "gift", "wishlist": "heart", "my_bookings": "calendar", "plans": "award"}


def tabbar(plan: dict[str, Any], labels: dict[str, str], tk: dict[str, Any] | None = None) -> str:
    tk = tk or {}
    tabs = plan.get("tabs", [])
    items = [f'<button class="tab" data-go="{esc(t)}" data-tabbtn="{esc(t)}"><span class="tab-pill">'
             f'{icon_svg(TAB_ICON.get(t, GO_ICON.get(t, "dot")))}</span><span class="tab-l">{esc(labels.get(t) or t)}</span></button>'
             for t in tabs]
    if tk.get("nav") == "bottom_app_bar" and tk.get("fab") == "docked":       # leave the middle for the docked button
        items.insert(len(items) // 2 + len(items) % 2, '<span class="tab-gap" aria-hidden="true"></span>')
    return f'<nav class="tabbar" aria-label="Main">{"".join(items)}</nav>'


def drawer(plan: dict[str, Any], labels: dict[str, str], name: str, tk: dict[str, Any]) -> str:
    """Side bar for drawer / drawer_bar / side_sheet navigation: tabs, the other screens, then the legal ones."""
    if tk.get("nav") not in ("drawer", "drawer_bar", "side_sheet", "rail"):
        return ""
    tabs = plan.get("tabs", [])
    flow = set(plan.get("flow", [])) - set(tabs)
    rest = [s for s in plan.get("screens", []) if s not in tabs and s not in flow and s not in ("login", "onboarding")]
    legal = [s for s in ("seller_info", "privacy", "delete_account") if s in plan.get("code_screens", [])]

    def row(sid: str) -> str:
        lab = labels.get(sid) or T.CODE_SCREENS.get(sid, {}).get("label") or sid
        return (f'<button class="dr-item" data-go="{esc(sid)}" data-close data-tabbtn-d="{esc(sid)}">'
                f'{icon_svg(TAB_ICON.get(sid, GO_ICON.get(sid, "dot")))}<span>{esc(lab)}</span></button>')
    side = "end" if tk.get("nav") == "side_sheet" else "start"
    return (f'<aside class="drawer drawer-{side}" id="hk-drawer" aria-label="Menu"><div class="dr-head"><img class="logo" '
            f'src="assets/logo.png" alt=""><div><p class="t-title">{esc(name) or "App"}</p><p class="t-small muted">Menu</p></div></div>'
            f'<div class="dr-list">{"".join(row(t) for t in tabs)}<div class="sep"></div>{"".join(row(s) for s in rest)}'
            f'<div class="sep"></div>{"".join(row(s) for s in legal)}</div></aside>')


def fab_html(ctx: dict[str, Any], labels: dict[str, str]) -> str:
    tk, plan = ctx["tokens"], ctx["plan"]
    kind = tk.get("fab") or "none"
    target, ic = PRIMARY.get(ctx.get("goal") or "", ("", "plus"))
    known = set(plan.get("screens", []))
    if kind == "none" or target not in known:
        return ""
    lab = esc(labels.get(target) or target)
    if kind in ("speed_dial", "menu"):
        acts = [s for s in plan.get("flow", []) + plan.get("screens", []) if s in known and s != target and s not in plan.get("tabs", [])]
        acts = list(dict.fromkeys([target] + acts))[:3]
        minis = "".join(f'<button class="fab-mini" data-go="{esc(a)}" data-fab-close>{icon_svg(GO_ICON.get(a, "dot"))}'
                        f'<span>{esc(labels.get(a) or a)}</span></button>' for a in acts)
        return (f'<div class="fabx fab-{kind}" data-fab><div class="fab-actions">{minis}</div><button class="fab-main" data-fab-toggle '
                f'aria-label="Actions">{icon_svg("plus")}</button></div>')
    words = f'<span class="fab-l">{lab}</span>' if kind == "extended" else ""
    return (f'<div class="fabx fab-{kind}" data-fab><button class="fab-main" data-go="{esc(target)}" aria-label="{lab}">'
            f'{icon_svg(ic)}{words}</button></div>')


def _menu_button(h: str) -> str:
    """Hamburger into a tab screen's app bar (drawer navigation)."""
    btn = f'<button class="ab-menu" data-drawer aria-label="Menu">{icon_svg("menu")}</button>'
    return re.sub(r'(<header\b[^>]*class="[^"]*\bab\b[^"]*"[^>]*>)', lambda m: m.group(1) + btn, h, count=1)


def assemble(ctx: dict[str, Any], screens: dict[str, dict[str, Any]], out: Path, only_ready: bool = False) -> dict[str, Any]:
    """Write the clickable prototype. ctx: name, tokens, plan {screens, tabs, code_screens, labels}, facts, language,
    goal, logo_path, platform. screens: {sid: {"html", "css"}} written by the model (missing ones show a 'being designed'
    placeholder unless only_ready)."""
    tk, plan = ctx["tokens"], ctx["plan"]
    tmp = out.with_name(out.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "assets" / "fonts").mkdir(parents=True)
    shutil.copy(ASSETS / "app-kit.css", tmp / "assets" / "app-kit.css")
    shutil.copy(ASSETS / "proto.js", tmp / "assets" / "proto.js")
    faces = []
    for fam, sub, w, f in font_files(tk, ctx.get("language") or ""):
        name = f"{re.sub(r'[^a-z0-9]+', '-', fam.lower()).strip('-')}-{sub}-{w}.woff2"
        shutil.copy(f, tmp / "assets" / "fonts" / name)
        faces.append((fam, sub, w, f"fonts/{name}"))
    (tmp / "assets" / "tokens.css").write_text(tokens_css(tk, faces))
    (tmp / "assets" / "icon.svg").write_text(app_icon_svg(tk, ctx.get("name") or ""))
    logo = ctx.get("logo_path") or ""
    if logo and Path(logo).is_file():
        shutil.copy(logo, tmp / "assets" / "logo.png")
    else:
        (tmp / "assets" / "logo.png").write_bytes(_png_from_icon(tk))
    labels = plan.get("labels") or {}
    order: list[str] = []
    first_code = [c for c in plan.get("code_screens", []) if c in ("splash", "consent")]
    order += first_code + list(plan.get("screens", [])) + [c for c in plan.get("code_screens", []) if c not in first_code]
    tabs = set(plan.get("tabs", []))
    first = plan.get("start") or (plan.get("screens") or ["home"])[0]
    cctx = {**ctx, "first": "consent" if "consent" in plan.get("code_screens", []) else first,
            "after_consent": "notify_permission" if "notify_permission" in plan.get("code_screens", []) else first}
    parts, css = [], []
    missing: list[str] = []
    for sid in order:
        if sid in T.CODE_SCREENS:
            if sid == "splash":
                h = code_screen(sid, cctx)
            elif sid == "notify_permission":
                h = code_screen(sid, {**ctx, "first": first})
            else:
                h = code_screen(sid, {**ctx, "first": first, "after_consent": cctx["after_consent"]})
        elif sid in screens:
            h = screens[sid]["html"]
            css.append(screens[sid].get("css") or "")
        else:
            missing.append(sid)
            if only_ready:
                continue
            h = (f'<section id="scr-{esc(sid)}" class="scr pending" data-screen="{esc(sid)}"><header class="ab"><button class="ab-back" '
                 f'data-back aria-label="Back"></button><h1 class="ab-title">{esc(labels.get(sid) or sid)}</h1></header><div class="body center">'
                 f'<div class="sk sk-card"></div><div class="sk sk-line"></div><div class="sk sk-line short"></div>'
                 f'<p class="t-small muted">Design ban raha hai…</p></div></section>')
        h = expand(h)
        if sid in tabs:
            h = re.sub(r"<section\b", '<section data-tabbed="1"', h, count=1)
            if tk.get("nav") in ("drawer", "drawer_bar", "side_sheet"):
                h = _menu_button(h)
        parts.append(h)
    (tmp / "assets" / "screens.css").write_text("\n".join(css))
    body_cls = (f'p-{ctx.get("platform") or "android"} st-{tk.get("style")} card-{tk.get("card")} btn-{tk.get("button")} '
                f'nav-{tk.get("nav")} fabk-{tk.get("fab")} hd-{tk.get("header")} tr-{tk.get("transition")}'
                + (f' tex-{tk["texture"]}' if tk.get("texture") else "") + (" dark" if tk.get("dark") else ""))
    all_html = "".join(parts)
    three = '<script src="assets/three.min.js"></script>' if 'class="obj3d' in all_html or "class='obj3d" in all_html else ""
    if three:
        shutil.copy(ASSETS / "three.min.js", tmp / "assets" / "three.min.js")
    lang = (ctx.get("language") or "en") if (ctx.get("language") or "en") != "hinglish" else "en"
    name = esc(ctx.get("name") or "App")
    head = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="noindex">'
            f'<title>{name} · app design</title><link rel="icon" href="assets/icon.svg"><link rel="stylesheet" href="assets/tokens.css">'
            f'<link rel="stylesheet" href="assets/app-kit.css"><link rel="stylesheet" href="assets/screens.css"></head>')
    tools = ('<div class="proto-tools" aria-label="Preview controls"><button data-plat="android">Android</button>'
             '<button data-plat="ios">iPhone</button><button data-mode>' + ("Light" if tk.get("dark") else "Dark") +
             '</button><a href="all.html">Sab screens</a></div>')
    page = (head + f'<body class="{body_cls}" data-start="{esc("splash" if "splash" in plan.get("code_screens", []) else first)}" '
            f'data-home="{esc(first)}" data-base="{"dark" if tk.get("dark") else "light"}" data-mode-kind="{esc(tk.get("mode") or "both")}">'
            f'{tools}<div class="device"><div class="frame">{STATUS["android"]}{STATUS["ios"]}'
            f'<main class="screens">{all_html}</main>{tabbar(plan, labels, tk)}{fab_html(ctx, labels)}'
            f'{drawer(plan, labels, ctx.get("name") or "", tk)}<div class="scrim-d" data-close></div><div class="toast" role="status"></div>'
            f'<i class="homebar" aria-hidden="true"></i></div></div>{three}<script src="assets/proto.js"></script></body></html>')
    (tmp / "index.html").write_text(page)
    tiles = "".join(f'<a class="tile" href="index.html?s={esc(s)}"><img loading="lazy" src="__shots/thumb/{esc(s)}-android.jpg" '
                    f'alt="{esc(labels.get(s) or s)}"><span>{esc(labels.get(s) or T.CODE_SCREENS.get(s, {}).get("label") or s)}</span></a>'
                    for s in order if s in screens or s in T.CODE_SCREENS)
    (tmp / "all.html").write_text(head + f'<body class="overview {body_cls}"><h1>{name}: {len(order)} screens</h1>'
                                  f'<p><a href="index.html">Prototype kholo (tap karke chalaiye)</a></p><div class="tiles">{tiles}</div></body></html>')
    if plan.get("blueprint"):           # v0.131: schema / ER page / Room entities ride with every prototype version
        from . import blueprint as BPm
        try:
            BPm.write_files(plan["blueprint"], tmp, ctx.get("name") or "")
        except Exception:
            log.warning("blueprint files skipped", exc_info=True)
    if out.exists():
        old = out.with_name(out.name + ".old")
        if old.exists():
            shutil.rmtree(old)
        out.rename(old)
        tmp.rename(out)
        shutil.rmtree(old, ignore_errors=True)
    else:
        tmp.rename(out)
    return {"screens": len(parts), "missing": missing, "order": order}


def _png_from_icon(tk: dict[str, Any]) -> bytes:
    """A small PNG logo (primary -> accent tile) when she has no logo yet."""
    import io
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (256, 256), tk["primary"])
    d = ImageDraw.Draw(img)
    d.ellipse((150, 20, 236, 106), fill=tk["accent"])
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def spec_of(screens: dict[str, dict[str, Any]], ctx: dict[str, Any]) -> dict[str, Any]:
    """The design contract for the native build: tokens, navigation, every screen's purpose / data / actions / links."""
    plan = ctx["plan"]
    out_screens = []
    for sid in plan.get("screens", []):
        s = screens.get(sid) or {}
        gos = sorted(set(re.findall(r'data-go=["\']([\w-]+)["\']', s.get("html") or "")))
        out_screens.append({"id": sid, "label": (plan.get("labels") or {}).get(sid, sid), "tab": sid in plan.get("tabs", []),
                            "design": (plan.get("designs") or {}).get(sid, ""), "spec": s.get("spec") or {}, "goes_to": gos})
    for sid in plan.get("code_screens", []):
        out_screens.append({"id": sid, "label": T.CODE_SCREENS[sid]["label"], "tab": False, "code": True, "spec": {}, "goes_to": []})
    tk = ctx["tokens"]
    return {"app": ctx.get("name") or "", "goal": ctx.get("goal"), "language": ctx.get("language"),
            "tokens": {k: tk.get(k) for k in ("bg", "surface", "ink", "muted", "line", "primary", "on_primary", "accent",
                                               "on_accent", "radius", "head", "body", "deva", "style", "mode")},
            "dark_tokens" if not tk.get("dark") else "light_tokens": tk.get("alt") or {},
            "structure": _structure_spec(tk),
            "motion": _motion_spec(tk),
            "tabs": plan.get("tabs", []), "flow": plan.get("flow", []), "screens": out_screens,
            "rules": plan.get("rules", []), "legal": plan.get("legal", []),
            "blueprint": _blueprint_spec(plan.get("blueprint") or {})}


def _blueprint_spec(bp: dict[str, Any]) -> dict[str, Any]:
    if not bp:
        return {}
    from . import blueprint as BPm
    v = BPm.view(bp)
    return {**v, "login_plan": bp.get("login"), "caps_full": (bp.get("caps") or {}).get("caps", []),
            "plist": (bp.get("caps") or {}).get("plist", []), "files": ["blueprint/schema.sql", "blueprint/schema-plain.sql",
                                                                        "blueprint/app.sqlite.sql", "blueprint/Entities.kt",
                                                                        "blueprint/er.mmd", "blueprint/er.html"]}


def _structure_spec(tk: dict[str, Any]) -> dict[str, Any]:
    from . import designsys as DS
    return {"nav": {"id": tk.get("nav"), **DS.NAV.get(tk.get("nav") or "", {})},
            "fab": {"id": tk.get("fab"), **DS.FAB.get(tk.get("fab") or "", {})},
            "card": {"id": tk.get("card"), "desc": DS.CARDS.get(tk.get("card") or "", "")},
            "button": {"id": tk.get("button"), "desc": DS.BUTTONS.get(tk.get("button") or "", "")},
            "header": {"id": tk.get("header"), "desc": DS.HEADERS.get(tk.get("header") or "", "")},
            "texture": tk.get("texture") or "", "transition": tk.get("transition")}


def _motion_spec(tk: dict[str, Any]) -> list[dict[str, str]]:
    from . import designsys as DS
    st = T.STYLES.get(tk.get("style") or "") or {}
    keys = [f"t_{tk.get('transition')}"] + list(st.get("motion", []))
    return [{"id": k, **DS.MOTION[k]} for k in keys if k in DS.MOTION]


def design_hash(screens: dict[str, dict[str, Any]], ctx: dict[str, Any]) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(json.dumps({k: ctx["tokens"].get(k) for k in sorted(ctx["tokens"])}, sort_keys=True, default=str).encode())
    h.update(json.dumps(ctx["plan"].get("tabs", [])).encode())
    h.update(str((ctx["plan"].get("blueprint") or {}).get("hash") or "").encode())
    for sid in ctx["plan"].get("screens", []):
        s = screens.get(sid) or {}
        h.update(sid.encode() + (s.get("html") or "").encode() + (s.get("css") or "").encode())
    return h.hexdigest()[:24]
