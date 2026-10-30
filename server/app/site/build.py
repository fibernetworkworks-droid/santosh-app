"""v0.121 Turns the plan + the sections Opus wrote into real static files: sanitised HTML, scoped CSS, the motion runtime,
design tokens, bundled fonts, responsive photos (AVIF / WebP / JPEG, EXIF dropped), header / nav / footer, legal pages
(written by code from her facts, never by the model), JSON-LD, sitemap, robots, security headers.

Output: data/sites/<tenant>/<site>/v<N>/ with index.html, <page>/index.html, assets/..., ready for any static host."""
from __future__ import annotations

import hashlib
import html as _html
import io
import json
import logging
import os
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

from . import taxonomy as T

log = logging.getLogger("santosh.site")
ASSETS = Path(__file__).resolve().parent / "assets"
LEGAL_PAGES = ("privacy", "refund", "disclaimer", "terms")
WEIGHTS = (400, 500, 600, 700)        # v0.292 medium + semibold too (only the weights a page uses are downloaded)
_ICONS: dict[str, str] = {}
WIDTHS = (480, 960, 1600)


def root() -> Path:
    return Path(os.environ.get("SITE_DIR", "data/sites"))


def site_dir(tenant: str, site_id: str) -> Path:
    p = root() / re.sub(r"[^\w-]", "_", tenant)[:64] / re.sub(r"[^\w-]", "_", site_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def src_dir(tenant: str, site_id: str) -> Path:
    p = site_dir(tenant, site_id) / "src"
    (p / "sections").mkdir(parents=True, exist_ok=True)
    (p / "photos").mkdir(parents=True, exist_ok=True)
    return p


def out_dir(tenant: str, site_id: str, version: int) -> Path:
    return site_dir(tenant, site_id) / f"v{int(version)}"


def esc(s: Any) -> str:
    return _html.escape(str(s or ""), quote=True)


def page_path(slug: str) -> str:
    return "index.html" if slug == "home" else f"{slug}/index.html"


def page_url(slug: str, rel: str) -> str:
    return (rel or "./") if slug == "home" else f"{rel}{slug}/"


def rel_of(slug: str) -> str:
    return "" if slug == "home" else "../"


# ---------------------------------------------------------------- colours / tokens
def _hex_ok(c: str) -> bool:
    return bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", str(c or "")))


def tokens(style: str, palette: str, brand: dict[str, str] | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    from ..brand import rules as BR
    st = T.STYLES.get(style) or T.STYLES["editorial_calm"]
    pal = dict(T.PALETTES.get(palette) or T.PALETTES["paper_ink"])
    if brand:
        if _hex_ok(brand.get("primary", "")):
            pal["primary"] = brand["primary"]
        if _hex_ok(brand.get("accent", "")):
            pal["accent"] = brand["accent"]
    for k, v in (overrides or {}).items():
        if k in ("primary", "accent", "bg", "surface", "ink") and _hex_ok(str(v)):
            pal[k] = v
    # text must stay readable: ink vs bg >= 7, primary as a button colour gets its best text colour
    if BR.contrast(pal["bg"], pal["ink"]) < 7:
        pal["ink"] = BR.best_text(pal["bg"], ["#111111", "#F5F5F5"])
    on_p = BR.best_text(pal["primary"], ["#FFFFFF", "#111111"])
    on_a = BR.best_text(pal["accent"], ["#111111", "#FFFFFF"])
    muted = BR.mix(pal["ink"], pal["bg"], 0.38)
    if BR.contrast(pal["bg"], muted) < 4.6:
        muted = BR.mix(pal["ink"], pal["bg"], 0.25)
    line = BR.mix(pal["ink"], pal["bg"], 0.85)
    # brand colours used as TEXT (eyebrows, links, prices) must read at 4.5:1 on the page and the surface
    def text_safe(c: str) -> str:
        t = 0.0
        out = c
        while (BR.contrast(pal["bg"], out) < 4.6 or BR.contrast(pal["surface"], out) < 4.6) and t < 1:
            t += 0.08
            out = BR.mix(c, pal["ink"], t)
        return out
    primary_text, accent_text = text_safe(pal["primary"]), text_safe(pal["accent"])
    fonts = T.FONTS.get(st["fonts"]) or T.FONTS["poppins_mukta"]
    radius = int((overrides or {}).get("radius", st["radius"]) or 0)
    return {"style": style, "palette": palette, "bg": pal["bg"], "surface": pal["surface"], "ink": pal["ink"],
            "muted": muted, "line": line, "primary": pal["primary"], "on_primary": on_p, "accent": pal["accent"],
            "on_accent": on_a, "primary_text": primary_text, "accent_text": accent_text, "head": fonts["head"], "body": fonts["body"], "deva": fonts["deva"],
            "radius": max(0, min(radius, 40))}


def _font_slug(fam: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fam.lower()).strip("-")


def font_files(tk: dict[str, Any]) -> list[tuple[str, str, int, str]]:
    """[(family, subset, weight, file name)] that exist for this site's fonts."""
    out = []
    for fam in dict.fromkeys([tk["head"], tk["body"], tk["deva"]]):
        for sub in ("latin", "devanagari"):
            for w in WEIGHTS:
                fn = f"{_font_slug(fam)}-{sub}-{w}.woff2"
                if (ASSETS / "fonts" / fn).exists():
                    out.append((fam, sub, w, fn))
    return out


DEVA_RANGE = "U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+20B9,U+25CC,U+A830-A839,U+A8E0-A8FF"


def tokens_css(tk: dict[str, Any], rel: str = "") -> str:
    faces = []
    for fam, sub, w, fn in font_files(tk):
        rng = f"unicode-range:{DEVA_RANGE};" if sub == "devanagari" else ""
        faces.append(f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:normal;font-display:swap;{rng}"
                     f"src:url({rel}assets/fonts/{fn}) format('woff2')}}")
    head = f"'{tk['head']}','{tk['deva']}'"
    body = f"'{tk['body']}','{tk['deva']}'"
    return ("\n".join(faces) + "\n:root{" +
            f"--c-bg:{tk['bg']};--c-surface:{tk['surface']};--c-ink:{tk['ink']};--c-muted:{tk['muted']};--c-line:{tk['line']};"
            f"--c-primary:{tk['primary']};--c-on-primary:{tk['on_primary']};--c-accent:{tk['accent']};"
            f"--c-on-accent:{tk['on_accent']};--c-primary-text:{tk.get('primary_text', tk['primary'])};"
            f"--c-accent-text:{tk.get('accent_text', tk['accent'])};--font-head:{head};--font-body:{body};--radius:{tk['radius']}px;--gutter:20px"
            "}")


# ---------------------------------------------------------------- sanitising what the model wrote
SAFE_SCHEMES = ("tel:", "mailto:", "sms:", "#")
BAD_JS = re.compile(r"\b(fetch|XMLHttpRequest|WebSocket|EventSource|eval|Function\s*\(|importScripts|document\.cookie|"
                    r"localStorage|sessionStorage|indexedDB|navigator\.sendBeacon|window\.open|import\s*\(|\.innerHTML\s*=)", re.I)
DROP_TAGS = ("script", "iframe", "object", "embed", "link", "meta", "base", "style", "frame", "frameset", "applet", "portal")


def _ok_href(h: str) -> bool:
    h = (h or "").strip()
    if not h:
        return False
    low = h.lower()
    if low.startswith(SAFE_SCHEMES):
        return True
    if low.startswith("https://"):
        return True
    if re.match(r"^(\./|\.\./)?[\w\-/]*(\.html)?/?(#[\w-]*)?$", h):
        return True
    return False


def sanitize_section(sid: str, raw: dict[str, Any]) -> tuple[str, str, str, list[str]]:
    from bs4 import BeautifulSoup
    problems: list[str] = []
    html_in = str(raw.get("html") or "")
    soup = BeautifulSoup(html_in, "html.parser")
    for t in soup.find_all(DROP_TAGS):
        problems.append(f"removed <{t.name}>")
        t.decompose()
    for t in soup.find_all(True):
        for a in list(t.attrs):
            low = a.lower()
            v = t.attrs.get(a)
            vs = " ".join(v) if isinstance(v, list) else str(v)
            if low.startswith("on") or low in ("srcdoc", "formaction", "ping") or "javascript:" in vs.lower():
                t.attrs.pop(a, None)
                problems.append(f"removed {low}")
                continue
            if low in ("href", "xlink:href"):
                if not _ok_href(vs):
                    t.attrs.pop(a, None)
                    problems.append("removed a link that was not https / tel / mailto / page")
                    continue
                if vs.lower().startswith("https://") and t.name == "a":
                    t.attrs["rel"] = "noopener"
                    t.attrs["target"] = "_blank"
            if low in ("src", "srcset", "poster", "data", "action", "background"):
                if re.search(r"(https?:)?//|javascript:|data:(?!image/(png|jpe?g|webp|gif|svg\+xml))", vs, re.I):
                    t.attrs.pop(a, None)
                    problems.append(f"removed external {low}")
    sec = soup.find("section")
    if sec is None:
        wrap = soup.new_tag("section")
        for c in list(soup.contents):
            wrap.append(c.extract())
        soup.append(wrap)
        sec = wrap
        problems.append("wrapped in <section>")
    sec["id"] = sid
    cls = sec.get("class") or []
    if "hs" not in cls:
        sec["class"] = ["hs"] + list(cls)
    html_out = str(soup)
    css = str(raw.get("css") or "")
    css = re.sub(r"@import[^;]*;?", "", css, flags=re.I)
    css = re.sub(r"url\(\s*['\"]?(?:https?:)?//[^)]*\)", "none", css, flags=re.I)
    css = re.sub(r"expression\s*\(|behavior\s*:|-moz-binding", "", css, flags=re.I)
    css = re.sub(r"</style", "", css, flags=re.I)
    css = _scope_css(css, sid)
    js = str(raw.get("js") or "").strip()
    if js:
        if BAD_JS.search(js) or len(js) > 6000:
            problems.append("removed section script (not allowed)")
            js = ""
        else:
            js = js.replace("</script", "<\\/script")
            js = f"(function(){{try{{\n{js}\n}}catch(e){{}}}})();"
    return html_out, css, js, problems


def _scope_css(css: str, sid: str) -> str:
    """Every rule starts with #sid (keyframes / font-face / media wrappers kept, inner rules scoped)."""
    out: list[str] = []
    i, n = 0, len(css)
    pre = f"#{sid}"

    def scope_sel(sel: str) -> str:
        parts = []
        for s in sel.split(","):
            s = s.strip()
            if not s:
                continue
            if s.startswith(pre):
                parts.append(s)
            elif s in (":root", "html", "body"):
                parts.append(pre)
            else:
                parts.append(f"{pre} {s}")
        return ",".join(parts)

    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        sel = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        if sel.startswith("@keyframes") or sel.startswith("@-webkit-keyframes") or sel.startswith("@font-face"):
            if sel.startswith("@font-face"):
                pass       # fonts come only from the site's own files
            else:
                out.append(f"{sel}{{{body}}}")
        elif sel.startswith("@media") or sel.startswith("@supports") or sel.startswith("@container"):
            out.append(f"{sel}{{{_scope_css(body, sid)}}}")
        elif sel.startswith("@"):
            pass
        elif sel:
            out.append(f"{scope_sel(sel)}{{{body}}}")
        i = k
    return "\n".join(out)


# ---------------------------------------------------------------- photos
def make_photo(data: bytes, max_px: int = 2400) -> tuple[bytes, tuple[int, int]]:
    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90, optimize=True)
    return buf.getvalue(), im.size


def photo_set(src: Path, name: str, dest: Path) -> dict[str, Any]:
    from PIL import Image, features
    dest.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    w0, h0 = im.size
    made = []
    avif = features.check("avif")
    for w in WIDTHS:
        if w > w0 and made:
            break
        ww = min(w, w0)
        hh = round(h0 * ww / w0)
        r = im.resize((ww, hh), Image.LANCZOS) if ww != w0 else im
        r.save(dest / f"{name}-{w}.jpg", "JPEG", quality=80, optimize=True, progressive=True)
        r.save(dest / f"{name}-{w}.webp", "WEBP", quality=76, method=5)
        if avif:
            try:
                r.save(dest / f"{name}-{w}.avif", "AVIF", quality=55, speed=7)
            except Exception:
                avif = False
        made.append((w, ww, hh))
    return {"name": name, "w": w0, "h": h0, "sizes": made, "avif": avif}


def picture(meta: dict[str, Any], alt: str, rel: str, eager: bool = False, cls: str = "") -> str:
    name = meta["name"]
    sizes = meta.get("sizes") or []
    if not sizes:
        return ""

    def srcset(ext: str) -> str:
        return ", ".join(f"{rel}assets/img/{name}-{w}.{ext} {ww}w" for w, ww, _h in sizes)
    w, ww, hh = sizes[min(1, len(sizes) - 1)]
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    srcs = ""
    if meta.get("avif"):
        srcs += f'<source type="image/avif" srcset="{srcset("avif")}" sizes="(min-width:1100px) 50vw, 100vw">'
    srcs += f'<source type="image/webp" srcset="{srcset("webp")}" sizes="(min-width:1100px) 50vw, 100vw">'
    c = f' class="{esc(cls)}"' if cls else ""
    return (f'<picture>{srcs}<img src="{rel}assets/img/{name}-{w}.jpg" srcset="{srcset("jpg")}" '
            f'sizes="(min-width:1100px) 50vw, 100vw" width="{ww}" height="{hh}" alt="{esc(alt)}" {load} decoding="async"{c}></picture>')


def expand_images(html: str, photos: dict[str, dict[str, Any]], rel: str, first_eager: bool) -> tuple[str, list[str]]:
    missing: list[str] = []
    state = {"eager": first_eager}

    def rep(m: re.Match) -> str:
        tag = m.group(0)
        nm = re.search(r'data-hoola-img=["\']([\w-]+)["\']', tag)
        alt = re.search(r'alt=["\']([^"\']*)["\']', tag)
        cls = re.search(r'class=["\']([^"\']*)["\']', tag)
        name = nm.group(1) if nm else ""
        if name not in photos:
            missing.append(name)
            return f'<span class="blank" role="img" aria-label="{esc(alt.group(1) if alt else "photo")}">[photo: {esc(name)}]</span>'
        out = picture(photos[name], alt.group(1) if alt else "", rel, state["eager"], cls.group(1) if cls else "")
        state["eager"] = False
        return out
    return re.sub(r"<img\b[^>]*data-hoola-img=[^>]*>", rep, html), missing


# ---------------------------------------------------------------- v0.292 one icon set (Lucide, ISC) for the whole site
def icons() -> dict[str, str]:
    """name -> the inner SVG of a Lucide icon (assets/icons.json, 2,275 icons)."""
    if not _ICONS:
        _ICONS.update(json.loads((ASSETS / "icons.json").read_text())["icons"])
    return _ICONS


ICON_ALIASES = {"whatsapp": "message-circle", "call": "phone", "email": "mail", "location": "map-pin", "address": "map-pin",
                "time": "clock", "hours": "clock", "rupee": "indian-rupee", "price": "indian-rupee", "tick": "check",
                "done": "circle-check", "rating": "star", "home": "house", "doctor": "stethoscope", "delivery": "truck",
                "food": "utensils", "cart": "shopping-cart", "cake": "cake-slice", "instagram": "camera", "facebook": "users"}


def expand_icons(html: str) -> tuple[str, list[str]]:
    """<i data-icon="phone" class="x" aria-label="Call"></i> -> one inline Lucide SVG (same stroke, same size rules
    everywhere). An unknown name becomes a plain dot and is reported."""
    unknown: list[str] = []
    ic = icons()

    def rep(m: re.Match) -> str:
        tag = m.group(1)
        nm = re.search(r'data-icon=["\']([\w-]+)["\']', tag)
        name = (nm.group(1) if nm else "").lower()
        name = name if name in ic else ICON_ALIASES.get(name, name)
        inner = ic.get(name)
        if inner is None:
            unknown.append(name)
            inner = '<circle cx="12" cy="12" r="3"/>'
        cls = re.search(r'class=["\']([^"\']*)["\']', tag)
        lab = re.search(r'aria-label=["\']([^"\']*)["\']', tag)
        a11y = f'role="img" aria-label="{esc(lab.group(1))}"' if lab else 'aria-hidden="true" focusable="false"'
        return (f'<svg class="hs-ic{(" " + esc(cls.group(1))) if cls else ""}" viewBox="0 0 24 24" fill="none" '
                f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" {a11y}>{inner}</svg>')
    out = re.sub(r"(<i\b[^>]*data-icon=[^>]*>)\s*</i>", rep, html)
    out = re.sub(r"(<i\b[^>]*data-icon=[^>]*/>)", rep, out)
    return out, unknown


# ---------------------------------------------------------------- facts helpers
def digits(s: str) -> str:
    d = re.sub(r"\D", "", str(s or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    return d[-10:] if len(d) >= 10 else d


def wa_link(f: dict[str, Any], text: str = "") -> str:
    d = digits(f.get("whatsapp") or f.get("phone") or "")
    if len(d) != 10:
        return ""
    q = f"?text={_url(text)}" if text else ""
    return f"https://wa.me/91{d}{q}"


def _url(s: str) -> str:
    from urllib.parse import quote
    return quote(s or "", safe="")


def tel_link(f: dict[str, Any]) -> str:
    d = digits(f.get("phone") or "")
    return f"tel:+91{d}" if len(d) == 10 else ""


ICON_WA = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 '
           '10 0 1 0 12 2zm5.3 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .1-3.3-.8-2.8-1.2-4.6-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.9s.7-2 '
           '1-2.3c.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.8 2c.1.2.1.4 0 .5l-.4.6-.4.4c-.1.2-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.2 1 2.1 '
           '1.3 2.4 1.5.3.1.5.1.6-.1l.9-1c.2-.3.4-.2.6-.1l1.9.9c.3.1.5.2.5.3.1.2.1.7-.1 1.3z"/></svg>')
ICON_CALL = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M6.6 10.8a15.2 15.2 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7'
             '-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 '
             '3.6.1.3 0 .7-.2 1z"/></svg>')


# ---------------------------------------------------------------- page chrome (code, not the model)
def nav_pages(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in plan.get("pages", []) if p["slug"] not in LEGAL_PAGES]


def header(site: dict[str, Any], plan: dict[str, Any], slug: str, rel: str, logo: bool) -> str:
    f = site["facts"]
    links = []
    for p in nav_pages(plan):
        cur = ' aria-current="page"' if p["slug"] == slug else ""
        links.append(f'<li><a href="{page_url(p["slug"], rel)}"{cur}>{esc(p.get("nav") or p["title"])}</a></li>')
    cta = cta_button(site, rel, "btn btn-primary hs-cta")
    brand = (f'<img src="{rel}assets/img/logo.png" alt="{esc(f.get("name"))} logo" width="120" height="40">' if logo else "")
    return (f'<a class="skip" href="#main">Skip to content</a><header class="hs-head"><div class="wrap hs-bar">'
            f'<a class="hs-brand" href="{page_url("home", rel)}">{brand}<span>{esc(f.get("name") or "")}</span></a>'
            f'<nav aria-label="Main"><ul class="hs-links">{"".join(links)}</ul></nav>{cta}'
            f'<button class="hs-menu" aria-label="Menu" aria-expanded="false"><span></span><span></span><span></span></button>'
            f'</div></header>')


def cta_button(site: dict[str, Any], rel: str, cls: str) -> str:
    f, kind = site["facts"], site.get("cta") or "call"
    w, t = wa_link(f, f"Namaste, {f.get('name') or ''} - website se message"), tel_link(f)
    if kind in ("whatsapp", "order") and w:
        return f'<a class="{cls}" href="{w}" rel="noopener" target="_blank" data-m="magnetic">WhatsApp</a>'
    if kind in ("booking",) and any(p["slug"] == "booking" for p in site["plan"].get("pages", [])):
        return f'<a class="{cls}" href="{page_url("booking", rel)}" data-m="magnetic">Book now</a>'
    if t:
        return f'<a class="{cls}" href="{t}" data-m="magnetic">Call now</a>'
    if w:
        return f'<a class="{cls}" href="{w}" rel="noopener" target="_blank" data-m="magnetic">WhatsApp</a>'
    return f'<a class="{cls}" href="{page_url("contact", rel)}">Contact</a>' if any(
        p["slug"] == "contact" for p in site["plan"].get("pages", [])) else ""


def footer(site: dict[str, Any], plan: dict[str, Any], rel: str) -> str:
    f = site["facts"]
    quick = "".join(f'<li><a href="{page_url(p["slug"], rel)}">{esc(p.get("nav") or p["title"])}</a></li>' for p in nav_pages(plan))
    legal = "".join(f'<a href="{page_url(p["slug"], rel)}">{esc(p["title"])}</a>' for p in plan.get("pages", [])
                    if p["slug"] in LEGAL_PAGES)
    contact = []
    if f.get("phone"):
        contact.append(f'<li><a href="{tel_link(f)}">{esc(f["phone"])}</a></li>')
    if f.get("email"):
        contact.append(f'<li><a href="mailto:{esc(f["email"])}">{esc(f["email"])}</a></li>')
    if f.get("address"):
        contact.append(f'<li>{esc(f["address"])}</li>')
    if f.get("hours"):
        contact.append(f'<li>{esc(f["hours"])}</li>')
    regs = [f"{k.upper()}: {esc(v)}" for k, v in (f.get("registrations") or {}).items() if v]
    return (f'<footer class="hs-foot"><div class="wrap"><div class="grid g3">'
            f'<div><h3>{esc(f.get("name") or "")}</h3><p>{esc(f.get("tagline") or "")}</p></div>'
            f'<div><h3>Links</h3><ul>{quick}</ul></div><div><h3>Contact</h3><ul>{"".join(contact)}</ul></div></div>'
            f'<div class="hs-legal"><span>© <span data-year>2026</span> {esc(f.get("name") or "")}'
            f'{" · " + " · ".join(regs) if regs else ""}</span><span>{legal}</span></div>'
            + ('<p class="hs-ai-note">Is website ki kuch tasveeren AI se banayi gayi hain. / Some pictures on this site are '
               'AI-generated.</p>' if site.get("ai_photos") else "") + '</div></footer>')


def floats(site: dict[str, Any]) -> str:
    f = site["facts"]
    w, t = wa_link(f, f"Namaste, {f.get('name') or ''}"), tel_link(f)
    if not (w or t):
        return ""
    out = '<div class="hs-float">'
    if t:
        out += f'<a class="call" href="{t}" aria-label="Call">{ICON_CALL}</a>'
    if w:
        out += f'<a class="wa" href="{w}" rel="noopener" target="_blank" aria-label="WhatsApp">{ICON_WA}</a>'
    return out + "</div>"


SCHEMA_TYPE = {"restaurant": "Restaurant", "food_shop": "FoodEstablishment", "food_maker": "FoodEstablishment",
               "clinic": "MedicalClinic", "health_allied": "MedicalBusiness", "wellness": "HealthClub", "beauty": "BeautySalon",
               "school": "School", "coaching": "EducationalOrganization", "skills": "EducationalOrganization",
               "home_services": "HomeAndConstructionBusiness", "construction": "HomeAndConstructionBusiness",
               "auto": "AutoRepair", "real_estate": "RealEstateAgent", "finance": "AccountingService",
               "legal": "LegalService", "travel": "TravelAgency", "hospitality": "LodgingBusiness", "ngo": "NGO",
               "fashion": "ClothingStore", "electronics": "ElectronicsStore", "retail": "Store", "pets": "PetStore",
               "kids": "ChildCare", "sports": "SportsActivityLocation", "it": "Organization"}


def json_ld(site: dict[str, Any], base_url: str) -> str:
    f = site["facts"]
    d: dict[str, Any] = {"@context": "https://schema.org", "@type": SCHEMA_TYPE.get(site.get("industry", ""), "LocalBusiness"),
                         "name": f.get("name") or ""}
    if f.get("tagline"):
        d["description"] = f["tagline"]
    if f.get("phone"):
        d["telephone"] = "+91" + digits(f["phone"])
    if f.get("email"):
        d["email"] = f["email"]
    if f.get("address"):
        d["address"] = {"@type": "PostalAddress", "streetAddress": f["address"], "addressCountry": "IN"}
        if f.get("city"):
            d["address"]["addressLocality"] = f["city"]
    if base_url:
        d["url"] = base_url
    if f.get("hours"):
        d["openingHours"] = f["hours"]
    return json.dumps(d, ensure_ascii=False).replace("</", "<\\/")


def page_html(site: dict[str, Any], plan: dict[str, Any], page: dict[str, Any], body: str, rel: str, logo: bool,
              base_url: str) -> str:
    f = site["facts"]
    lang = {"hi": "hi", "mr": "mr", "en": "en-IN", "hinglish": "hi-Latn"}.get(site.get("language") or "en", "en-IN")
    title = f'{page["title"]} | {f.get("name") or ""}' if page["slug"] != "home" else (
        f'{f.get("name") or ""}' + (f' - {f["tagline"]}' if f.get("tagline") else ""))
    desc = page.get("description") or f.get("tagline") or ""
    canon = (base_url.rstrip("/") + "/" + ("" if page["slug"] == "home" else page["slug"] + "/")) if base_url else ""
    meta = [f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
            f"<title>{esc(title[:70])}</title>", f'<meta name="description" content="{esc(desc[:158])}">',
            f'<meta name="theme-color" content="{esc(site["tokens"]["primary"])}">',
            f'<meta property="og:title" content="{esc(title[:70])}"><meta property="og:description" content="{esc(desc[:200])}">',
            f'<meta property="og:type" content="website"><meta property="og:image" content="{rel}assets/og.jpg">',
            '<meta name="twitter:card" content="summary_large_image">',
            '<meta name="generator" content="Hoola">']
    if canon:
        meta.append(f'<link rel="canonical" href="{esc(canon)}">')
    if site.get("noindex"):
        meta.append('<meta name="robots" content="noindex">')
    pre = [fn for fam, sub, w, fn in font_files(site["tokens"]) if sub == "latin" and fam == site["tokens"]["head"] and w == 700][:1]
    links = "".join(f'<link rel="preload" href="{rel}assets/fonts/{fn}" as="font" type="font/woff2" crossorigin>' for fn in pre)
    links += f'<link rel="icon" href="{rel}assets/img/{"logo.png" if logo else "icon.svg"}">'
    links += f'<link rel="stylesheet" href="{rel}assets/site.css">'
    ld = f'<script type="application/ld+json">{json_ld(site, base_url)}</script>' if page["slug"] == "home" else ""
    notice = ""
    if "bci" in site.get("legal", []) and page["slug"] == "home":
        notice = ('<div class="wrap muted" style="padding:10px 0;font-size:.85rem">As per the rules of the Bar Council of India, '
                  'this website is for information only and is not an advertisement or solicitation. '
                  f'<a href="{page_url("disclaimer", rel)}">Disclaimer</a></div>')
    return (f'<!doctype html><html lang="{lang}"><head>{"".join(meta)}{links}{ld}</head>'
            f'<body class="look-{esc(site["tokens"]["style"])}">{header(site, plan, page["slug"], rel, logo)}{notice}'
            f'<main id="main">{body}</main>{footer(site, plan, rel)}{floats(site)}'
            f'<script src="{rel}assets/hoola-site.js" defer></script><script src="{rel}assets/site.js" defer></script>'
            f'</body></html>')


# ---------------------------------------------------------------- legal pages (code only)
def legal_page(kind: str, site: dict[str, Any]) -> str:
    f = site["facts"]
    nm = esc(f.get("name") or "We")
    owner = esc(f.get("owner") or f.get("name") or "")
    contact = " / ".join(esc(x) for x in (f.get("email"), f.get("phone")) if x) or '<em class="blank">[email / phone]</em>'
    addr = esc(f.get("address") or "") or '<em class="blank">[address]</em>'
    if kind == "privacy":
        body = (f"<h1>Privacy policy</h1><p>This policy explains how {nm} uses the details you share through this website. "
                "It follows the Digital Personal Data Protection Act, 2023.</p>"
                "<h2>What we collect</h2><p>Only what you type in our forms: your name, phone number, email (if given) and your "
                "message, plus the page you sent it from. We do not use advertising cookies or third-party trackers.</p>"
                f"<h2>Why</h2><p>To reply to your enquiry, booking or order. We do not sell or share your details with anyone "
                "for marketing.</p><h2>How long</h2><p>We keep enquiries for up to one year, or until you ask us to delete them.</p>"
                f"<h2>Your rights</h2><p>You can ask to see, correct or delete your details, or withdraw consent, by writing to "
                f"{contact}.</p><h2>Grievance officer</h2><p>{owner}, {addr}. Contact: {contact}. We reply within 7 days.</p>")
    elif kind == "refund":
        body = (f"<h1>Refund &amp; cancellation policy</h1><p>{nm} confirms every order on WhatsApp or phone before it is "
                "prepared or dispatched.</p><h2>Cancellation</h2><p>Tell us as soon as possible on the same number; orders not yet "
                "prepared can be cancelled at no charge.</p><h2>Refunds</h2><p>If an item is wrong or damaged, tell us within 24 hours "
                f"with a photo; we will replace it or refund it to your original payment method within 7 working days.</p>"
                f"<p>Contact: {contact}.</p>")
    elif kind == "disclaimer":
        if "bci" in site.get("legal", []):
            body = ("<h1>Disclaimer</h1><p>The Bar Council of India does not permit advocates to solicit work or advertise. By "
                    "using this website you agree that there has been no advertisement, solicitation, invitation or inducement of "
                    "any sort from us or any of our members, and that you are seeking information about us on your own for your "
                    "own information and use.</p><p>Information on this website is not legal advice and does not create a lawyer-"
                    "client relationship.</p>")
        else:
            body = ("<h1>Disclaimer</h1><p>Information on this website is general and for education only; it is not personal "
                    "financial advice. Investments are subject to market risks; read all scheme related documents carefully. "
                    "Past performance does not guarantee future returns.</p>")
    else:
        body = (f"<h1>Terms of use</h1><p>By using this website you agree to these terms. Content belongs to {nm}. Prices and "
                "availability shown are confirmed when you contact us.</p>")
    return f'<section id="legal-{kind}" class="hs"><div class="wrap" style="max-width:780px">{body}</div></section>'


# ---------------------------------------------------------------- whole site
def assemble(site: dict[str, Any], plan: dict[str, Any], sections: dict[str, dict[str, Any]], photos: dict[str, dict],
             out: Path, base_url: str = "", form_endpoint: str = "") -> dict[str, Any]:
    """sections: key 'page__type' -> {html, css, js} (already sanitised). Writes the site; returns {files, bytes, problems}."""
    if out.exists():
        shutil.rmtree(out)
    (out / "assets" / "img").mkdir(parents=True)
    (out / "assets" / "fonts").mkdir(parents=True)
    tk = site["tokens"]
    problems: list[str] = []
    for fam, sub, w, fn in font_files(tk):
        shutil.copy(ASSETS / "fonts" / fn, out / "assets" / "fonts" / fn)
    shutil.copy(ASSETS / "hoola-site.js", out / "assets" / "hoola-site.js")
    logo = False
    if site.get("logo_path") and Path(site["logo_path"]).exists():
        try:
            from PIL import Image
            im = Image.open(site["logo_path"]).convert("RGBA")
            im.thumbnail((360, 120))
            im.save(out / "assets" / "img" / "logo.png", "PNG", optimize=True)
            logo = True
        except Exception:
            log.info("logo copy failed", exc_info=True)
    (out / "assets" / "img" / "icon.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="{tk["primary"]}"/>'
        f'<text x="32" y="42" font-size="30" text-anchor="middle" fill="{tk["on_primary"]}" font-family="sans-serif" '
        f'font-weight="700">{esc((site["facts"].get("name") or "H")[:1].upper())}</text></svg>')
    srcdir = out.parent / "src" / "photos"
    cache = out.parent / "src" / "img"
    for name, meta in photos.items():
        src = srcdir / f"{name}.jpg"
        if not src.exists():
            continue
        stamp = cache / f"{name}.json"
        if stamp.exists() and stamp.stat().st_mtime >= src.stat().st_mtime:
            made = json.loads(stamp.read_text())
        else:       # resized once per photo, then reused by every build
            made = photo_set(src, name, cache)
            stamp.write_text(json.dumps(made))
        for f in cache.glob(f"{name}-*"):
            shutil.copy(f, out / "assets" / "img" / f.name)
        photos[name] = {**meta, **made}
    css_all = [tokens_css(tk, "../"), (ASSETS / "hoola-site.css").read_text()]
    js_all: list[str] = []
    for key, sec in sections.items():
        css_all.append(sec.get("css") or "")
        if sec.get("js"):
            js_all.append(sec["js"])
    files = 0
    for page in plan.get("pages", []):
        slug, rel = page["slug"], rel_of(page["slug"])
        if slug in LEGAL_PAGES:
            body = legal_page(slug, site)
        else:
            parts = []
            for i, s in enumerate(page.get("sections", [])):
                key = f"{slug}__{s['type']}"
                sec = sections.get(key)
                if not sec:
                    continue
                h = sec["html"]
                h, missing = expand_images(h, photos, rel, first_eager=(i == 0))
                if missing:
                    problems.append(f"{key}: photo not found: {', '.join(m for m in missing if m)}")
                h, unknown = expand_icons(h)
                if unknown:
                    problems.append(f"{key}: unknown icon: {', '.join(sorted(set(unknown)))}")
                if form_endpoint:
                    h = h.replace("data-hoola-form", f'data-hoola-form data-endpoint="{esc(form_endpoint)}"', 1) \
                        if 'data-endpoint=' not in h else h
                parts.append(h)
            body = "\n".join(parts)
        dest = out / page_path(slug)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page_html(site, plan, page, body, rel, logo, base_url), encoding="utf-8")
        files += 1
    (out / "assets" / "site.css").write_text(_min_css("\n".join(css_all)), encoding="utf-8")
    (out / "assets" / "site.js").write_text("\n".join(js_all) or "/* no section scripts */", encoding="utf-8")
    (out / "404.html").write_text(page_html(site, plan, {"slug": "home", "title": "Not found"},
                                            '<section class="hs"><div class="wrap"><h1>Page not found</h1>'
                                            f'<p><a class="btn btn-primary" href="./">Home</a></p></div></section>', "", logo, ""),
                                  encoding="utf-8")
    urls = [(base_url.rstrip("/") + "/" + ("" if p["slug"] == "home" else p["slug"] + "/")) for p in plan.get("pages", [])]
    if base_url:
        (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/'
                                         'sitemap/0.9">' + "".join(f"<url><loc>{esc(u)}</loc></url>" for u in urls) + "</urlset>")
    robots = "User-agent: *\n" + ("Disallow: /\n" if site.get("noindex") else "Allow: /\n")
    if base_url and not site.get("noindex"):
        robots += f"Sitemap: {base_url.rstrip('/')}/sitemap.xml\n"
    (out / "robots.txt").write_text(robots)
    (out / "_headers").write_text("/*\n  " + "\n  ".join(f"{k}: {v}" for k, v in security_headers(form_endpoint).items()) + "\n")
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    return {"files": sum(1 for p in out.rglob("*") if p.is_file()), "pages": files, "bytes": total, "problems": problems,
            "photos": photos}


def security_headers(form_endpoint: str = "") -> dict[str, str]:
    connect = "'self'"
    m = re.match(r"https?://[^/]+", form_endpoint or "")
    if m:
        connect += " " + m.group(0)
    return {"Content-Security-Policy": ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                                        f"script-src 'self'; font-src 'self'; connect-src {connect}; frame-ancestors 'self'; "
                                        "base-uri 'self'; form-action 'self'; object-src 'none'"),
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()", "X-Frame-Options": "SAMEORIGIN"}


def _min_css(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};:,>])\s*", r"\1", css)
    return css.replace(";}", "}").strip()


def export_zip(out: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(out).as_posix())
    return buf.getvalue()


def fingerprint(out: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(out.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(out).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:16]
