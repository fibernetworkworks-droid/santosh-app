"""v0.567 KOI BHI DESIGN (web Step 7 part 3 = W9 of docs/WEB_PLATFORM_PLAN.md): her website starts from HER design.

Three ways in, one result - a DESIGN REFERENCE (Hoola's own words for a visual system, never someone's files):
- a SCREENSHOT she sends (any website or picture she likes): the colours are MEASURED from the pixels (Pillow), the style,
  type family, corner shape and section order are READ by Opus vision; no text, logo, name or photo is ever taken from it.
- her FIGMA file: read through Figma's own REST API with HER personal access token (typed in the console, sealed, returned
  by no route): the fills, text styles, corner radii and top-level frame names of HER file, plus the words in her frames
  (her content, so it may be used).
- her OWN old website's address: only after she PROVES it is hers (it is already one of her Hoola addresses, or a TXT record
  `_hoola-own.<domain>` / a `<meta name="hoola-own">` tag carries her token). Then up to 12 of its pages are read (robots.txt
  respected, public addresses only): her words, phone / email / WhatsApp / address, menu, her photos, her colours and fonts.

`read` makes a PREVIEW (nothing written, kept 24 hours under a token); `use` (her tap) puts the reference on a site: the
FIRST of the 3 looks is then hers - her colours, her type (mapped to a font pair Hoola ships), her corners, her section order -
built in Hoola's own design kit, and the other two stay Hoola's alternatives. With no site named, `use` starts a new one from
the old site's or the Figma file's own words. The copy guard still applies: "make it exactly like <someone's> site" is refused;
a screenshot only ever gives a style (colours, type family, layout ideas), never content.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import logging
import re
import secrets
import time
from collections import Counter
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session
from . import taxonomy as T

log = logging.getLogger("santosh.site.inspire")


class InspireError(Exception):
    def __init__(self, msg: str, code: int = 400, extra: dict[str, Any] | None = None):
        super().__init__(msg)
        self.code = code
        self.extra = extra or {}


class SiteFigmaKey(Base):
    """Her Figma personal access token, sealed (accounts.encrypt); no route returns it."""
    __tablename__ = "site_figma_keys"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    token_enc: Mapped[str] = mapped_column(Text, default="")
    hint: Mapped[str] = mapped_column(String(16), default="")
    created_at = mapped_column(DateTime(timezone=True), default=now)


_OK = False
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
PAGES_MAX, IMAGES_MAX, PAGE_BYTES, IMG_BYTES = 12, 12, 1_500_000, 6_000_000
PREVIEW_TTL = 86400
_TRANSPORT: httpx.BaseTransport | None = None          # tests


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def ensure_tables() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        SiteFigmaKey.__table__.create(_db._engine, checkfirst=True)
        _OK = True


# ---------------------------------------------------------------- the design system words
# head font families by kind (every pair also carries a Devanagari face, so Hindi pages keep working)
HEAD_KIND = {"serif": ["fraunces_inter", "lora_dm", "playfair_lato", "cormorant_manrope", "dmserif_dm", "spectral_inter", "martel_mukta"],
             "sans": ["inter_inter", "jakarta_inter", "manrope_inter", "outfit_inter", "urbanist_mukta", "poppins_mukta",
                      "instrument_inter", "archivo_inter", "sora_nunito", "space_dm"],
             "display": ["syne_inter", "bricolage_inter", "teko_hind", "khand_mukta", "rozha_hind", "eczar_hind"],
             "rounded": ["nunito_hind", "baloo_mukta", "palanquin_hind"],
             "handwritten": ["kalam_mukta", "yatra_hind"],
             "mono": ["space_dm", "inter_inter"]}
SERIF_WORDS = ("serif", "playfair", "lora", "merriweather", "garamond", "times", "georgia", "fraunces", "cormorant",
               "spectral", "baskerville", "bodoni", "libre caslon", "crimson", "martel", "noto serif", "pt serif")
ROUND_WORDS = ("nunito", "baloo", "quicksand", "rounded", "varela", "comfortaa", "fredoka")
HAND_WORDS = ("kalam", "caveat", "pacifico", "dancing", "satisfy", "handlee", "patrick hand", "yatra")
DISPLAY_WORDS = ("syne", "bricolage", "teko", "khand", "bebas", "anton", "oswald", "rozha", "eczar", "abril", "monoton")
MONO_WORDS = ("mono", "code", "courier", "consolas")


def font_kind(family: str) -> str:
    f = (family or "").lower()
    for words, kind in ((MONO_WORDS, "mono"), (HAND_WORDS, "handwritten"), (ROUND_WORDS, "rounded"),
                        (DISPLAY_WORDS, "display"), (SERIF_WORDS, "serif")):
        if any(w in f for w in words):
            return kind
    return "sans"


def font_pair(head_kind: str, family: str = "") -> str:
    """A pair Hoola ships: the exact family when Hoola has it, else the first pair of that kind."""
    f = (family or "").lower().strip()
    if f:
        for key, v in T.FONTS.items():
            if v["head"].lower() == f:
                return key
    for key in HEAD_KIND.get(head_kind) or HEAD_KIND["sans"]:
        if key in T.FONTS:
            return key
    return "inter_inter"


def _rel_lum(hx: str) -> float:
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hx[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _sat(hx: str) -> float:
    r, g, b = (int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5))
    mx, mn = max(r, g, b), min(r, g, b)
    return 0.0 if mx == 0 else (mx - mn) / mx


def _hex(v: Any) -> str:
    s = str(v or "").strip()
    if re.fullmatch(r"#?[0-9A-Fa-f]{3}", s):
        s = "#" + "".join(c * 2 for c in s.lstrip("#"))
    if re.fullmatch(r"[0-9A-Fa-f]{6}", s):
        s = "#" + s
    return s.upper() if HEX.match(s) else ""


def roles_from(colours: list[tuple[str, float]]) -> dict[str, str]:
    """Measured colours (hex, share) -> page roles: the commonest light-or-dark one is the page, the most saturated others
    are the brand colours. Nothing here is a guess dressed as a fact: each role is one of HER colours."""
    cs: list[tuple[str, float]] = []
    for c, w in sorted(((c, w) for c, w in colours if HEX.match(c)), key=lambda x: -x[1]):
        near = next((i for i, (k, _) in enumerate(cs) if _dist(k, c) < 30), None)
        if near is not None:                                # an anti-aliased twin of a colour already counted
            cs[near] = (cs[near][0], cs[near][1] + w)
        else:
            cs.append((c, w))
    total = sum(w for _, w in cs) or 1
    cs = [(c, w) for c, w in cs if w / total >= 0.015] or cs[:1]   # edge blends (< 1.5% of the picture) are not her colours
    if not cs:
        return {}
    bg = cs[0][0]
    dark = _rel_lum(bg) < 0.2
    rest = [c for c, _ in cs[1:]]
    vivid = [c for c in rest if _sat(c) > 0.25 and 0.05 < _rel_lum(c) < 0.85]   # largest area first = her main brand colour
    calm = [c for c in rest if c not in vivid]
    ink = next((c for c in calm if abs(_rel_lum(c) - _rel_lum(bg)) > 0.5), "#F5F5F5" if dark else "#111111")
    surface = next((c for c in calm if c != ink and abs(_rel_lum(c) - _rel_lum(bg)) < 0.12), bg)
    out = {"bg": bg, "ink": ink, "surface": surface, "dark": dark}
    if vivid:
        out["primary"] = vivid[0]
        out["accent"] = next((c for c in vivid[1:] if abs(_rel_lum(c) - _rel_lum(vivid[0])) > 0.05 or _hue_far(c, vivid[0])),
                             vivid[0])
    return out


def _dist(a: str, b: str) -> float:
    return sum((int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) ** 2 for i in (1, 3, 5)) ** 0.5


def _hue_far(a: str, b: str) -> bool:
    import colorsys
    ha = colorsys.rgb_to_hsv(*(int(a[i:i + 2], 16) / 255 for i in (1, 3, 5)))[0]
    hb = colorsys.rgb_to_hsv(*(int(b[i:i + 2], 16) / 255 for i in (1, 3, 5)))[0]
    d = abs(ha - hb)
    return min(d, 1 - d) > 0.08


def image_colours(data: bytes, n: int = 16) -> list[tuple[str, float]]:
    """The picture's own colours by share (Pillow fast-octree on a small copy: it keeps a flat colour exact, where
    median-cut averaged a small blue band ~17 units away)."""
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((320, 320))
    q = im.quantize(colors=n, method=Image.Quantize.FASTOCTREE)
    pal = q.getpalette() or []
    counts = sorted(q.getcolors() or [], key=lambda x: -x[0])
    total = sum(c for c, _ in counts) or 1
    out = []
    for c, i in counts:
        r, g, b = pal[i * 3:i * 3 + 3]
        out.append((f"#{r:02X}{g:02X}{b:02X}", round(c / total, 3)))
    return out


def pick_style(head_kind: str, dark: bool, radius: int, vivid: bool, said: str = "") -> str:
    if said in T.STYLES:
        return said
    if dark:
        return "luxury_dark" if head_kind == "serif" else "tech_gradient"
    if head_kind == "serif":
        return "editorial_calm"
    if head_kind in ("rounded", "handwritten"):
        return "playful_bright" if vivid else "warm_local"
    if head_kind == "display":
        return "bold_modern"
    if radius <= 2 and not vivid:
        return "minimal_swiss"
    return "corporate_trust" if not vivid else "bold_modern"


SECTION_WORDS = {"hero": ("hero", "banner", "header", "top"), "services_grid": ("service", "what we do", "offer"),
                 "products_grid": ("product", "shop", "collection", "catalog"), "menu_list": ("menu", "food"),
                 "gallery_masonry": ("gallery", "photos", "work"), "process_steps": ("process", "how it works", "steps"),
                 "stats_counters": ("stats", "numbers", "counter"), "reviews": ("review", "testimonial", "what people say"),
                 "pricing_table": ("pricing", "price", "plans", "packages"), "faq": ("faq", "questions"),
                 "team": ("team", "doctors", "staff", "faculty"), "timeline_history": ("history", "timeline", "journey"),
                 "cta_band": ("cta", "call to action", "get started"), "contact_block": ("contact", "reach us", "enquiry"),
                 "map_hours": ("map", "hours", "location", "visit us"), "booking_slots": ("booking", "appointment"),
                 "courses_list": ("course", "classes", "programs"), "portfolio_grid": ("portfolio", "projects"),
                 "blog_list": ("blog", "news", "articles"), "intro_story": ("about", "story", "who we are"),
                 "offers_banner": ("offer", "sale", "discount"), "logos_marquee": ("clients", "logos", "partners"),
                 "video_showcase": ("video",), "certificates_trust": ("certificate", "awards", "trust")}


def section_of(name: str) -> str:
    n = (name or "").lower()
    for sec, words in SECTION_WORDS.items():
        if any(w in n for w in words) and sec in T.SECTIONS:
            return sec
    return ""


def normalise(source: str, raw: dict[str, Any], measured: list[tuple[str, float]] | None = None,
              content: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every reader ends here: one checked reference, only words Hoola's kit understands."""
    roles = roles_from(measured or [])
    for k in ("bg", "surface", "ink", "primary", "accent"):
        v = _hex(raw.get(k))
        if v and k not in roles:
            roles[k] = v
        elif v and k in ("primary", "accent") and source != "screenshot":
            roles[k] = v                                # Figma / her site name the brand colour itself
    if "dark" not in roles and roles.get("bg"):
        roles["dark"] = _rel_lum(roles["bg"]) < 0.2
    hk = raw.get("head_kind") if raw.get("head_kind") in HEAD_KIND else font_kind(str(raw.get("head_family") or ""))
    fonts = font_pair(hk, str(raw.get("head_family") or ""))
    try:
        radius = max(0, min(40, int(float(raw.get("radius_px") or 0))))
    except (TypeError, ValueError):
        radius = 8
    vivid = bool(roles.get("primary")) and _sat(roles["primary"]) > 0.45
    style = pick_style(hk, bool(roles.get("dark")), radius, vivid, str(raw.get("style") or ""))
    secs = []
    for s in raw.get("sections") or []:
        s = str(s)
        k = s if s in T.SECTIONS else section_of(s)
        if k and k not in secs:
            secs.append(k)
    notes = re.sub(r"\s+", " ", str(raw.get("notes") or ""))[:400]
    overrides = {k: roles[k] for k in ("bg", "surface", "ink", "primary", "accent") if HEX.match(str(roles.get(k, "")))}
    overrides["radius"] = radius
    overrides["fonts"] = fonts
    return {"source": source, "style": style, "style_label": T.STYLES[style]["label"], "fonts": fonts,
            "head": T.FONTS[fonts]["head"], "body": T.FONTS[fonts]["body"], "head_kind": hk, "radius": radius,
            "dark": bool(roles.get("dark")), "overrides": overrides, "sections": secs[:12], "notes": notes,
            "palette": [c for c, _ in (measured or [])][:8], "content": content or {}}


# ---------------------------------------------------------------- 1. a screenshot
VISION = """You look at a picture of a web page design and describe its VISUAL SYSTEM in Hoola's words - never its content.
Return JSON: {"style": one of %s, "head_kind": "serif|sans|display|rounded|handwritten|mono", "body_kind": "serif|sans",
"radius_px": number (corner roundness of cards / buttons), "density": "airy|balanced|dense", "dark": true/false,
"primary": "#RRGGBB" (the main button / brand colour you see), "accent": "#RRGGBB",
"sections": [the page's sections top to bottom, each one of %s],
"notes": "max 300 characters: layout and shape ideas in YOUR OWN words (grid, spacing, image treatment, shapes, motion feel)"}.
NEVER copy any text, name, logo, phone number, address or slogan from the picture; never describe a person."""


def from_screenshot(tenant: str, file_id: str = "", data: bytes | None = None) -> dict[str, Any]:
    from PIL import Image
    if file_id and not data:
        from ..mailbox import service as ms
        try:
            _n, _m, data = ms.load_files(tenant, [{"type": "file", "file_id": file_id}])[0]
        except Exception as e:
            raise InspireError(f"Screenshot {file_id} nahi mili: {e}", 404)
    if not data or len(data) > 20_000_000:
        raise InspireError("Screenshot khaali hai ya 20 MB se badi.")
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise InspireError("Yeh tasveer khul nahi rahi (PNG / JPEG / WebP bhejiye).")
    im.thumbnail((1600, 1600))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    jpg = buf.getvalue()
    measured = image_colours(jpg)
    raw: dict[str, Any] = {}
    try:
        from . import ai as AI
        raw = AI.ask_json(VISION % (list(T.STYLES), list(T.SECTIONS)), "Describe this design's visual system.", 1200,
                          "build", [jpg]) or {}
    except Exception as e:                                     # noqa: BLE001 - colours alone still make a usable look
        log.info("screenshot vision skipped: %s", e)
    ref = normalise("screenshot", raw, measured)
    ref["read_by"] = "colours measured + design read by Opus" if raw else "colours measured (design reading not available)"
    return ref


# ---------------------------------------------------------------- 2. her Figma file
def set_figma_token(tenant: str, token: str) -> dict[str, Any]:
    from ..accounts import encrypt
    t = (token or "").strip()
    if not re.fullmatch(r"fig[a-z]_[A-Za-z0-9_\-]{20,120}|[A-Za-z0-9_\-]{30,120}", t):
        raise InspireError("Yeh Figma personal access token jaisa nahi lagta (Figma > Settings > Security > Personal access tokens).")
    ensure_tables()
    with session() as s:
        row = s.get(SiteFigmaKey, tenant) or SiteFigmaKey(tenant_id=tenant)
        row.token_enc, row.hint = encrypt(t) or "", t[-4:]
        s.merge(row)
    return {"ok": True, "hint": "..." + t[-4:], "say": "Figma token rakh liya (band karke). Ab apni Figma file ka link bhejiye."}


def figma_status(tenant: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        row = s.get(SiteFigmaKey, tenant)
    return {"linked": bool(row and row.token_enc), "hint": ("..." + row.hint) if row and row.hint else ""}


def forget_figma(tenant: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        row = s.get(SiteFigmaKey, tenant)
        if row:
            s.delete(row)
    return {"ok": True}


def _figma_token(tenant: str) -> str:
    from ..accounts import decrypt
    ensure_tables()
    with session() as s:
        row = s.get(SiteFigmaKey, tenant)
    tok = decrypt(row.token_enc) if row and row.token_enc else ""
    if not tok:
        raise InspireError("Pehle apna Figma token jodiye: console > Website > Design se shuru > Figma (chat mein kabhi nahi).", 409)
    return tok


def figma_key(url: str) -> str:
    m = re.search(r"figma\.com/(?:file|design|proto)/([A-Za-z0-9]{10,64})", url or "")
    if not m:
        raise InspireError("Figma file ka link chahiye (figma.com/design/<key>/...).")
    return m.group(1)


def _walk(node: dict[str, Any], out: dict[str, Any], depth: int = 0) -> None:
    if out["n"] > 6000 or depth > 12:
        return
    out["n"] += 1
    for f in node.get("fills") or []:
        if isinstance(f, dict) and f.get("type") == "SOLID" and f.get("visible", True) and f.get("color"):
            c = f["color"]
            hx = "#%02X%02X%02X" % tuple(int(round(float(c.get(k, 0)) * 255)) for k in ("r", "g", "b"))
            area = 1.0
            bb = node.get("absoluteBoundingBox") or {}
            if bb.get("width") and bb.get("height"):
                area = float(bb["width"]) * float(bb["height"])
            out["fills"][hx] += area * float(f.get("opacity", 1) or 1)
    if node.get("type") == "TEXT":
        st = node.get("style") or {}
        if st.get("fontFamily"):
            out["fonts"][(st["fontFamily"], round(float(st.get("fontSize") or 0)))] += len(node.get("characters") or "")
        txt = re.sub(r"\s+", " ", str(node.get("characters") or "")).strip()
        if txt and len(out["texts"]) < 400:
            out["texts"].append(txt[:400])
    if isinstance(node.get("cornerRadius"), (int, float)):
        out["radii"].append(float(node["cornerRadius"]))
    for ch in node.get("children") or []:
        if isinstance(ch, dict):
            _walk(ch, out, depth + 1)


def from_figma(tenant: str, url: str) -> dict[str, Any]:
    key = figma_key(url)
    tok = _figma_token(tenant)
    try:
        with httpx.Client(timeout=40, transport=_TRANSPORT) as c:
            r = c.get(f"https://api.figma.com/v1/files/{key}", params={"depth": 4}, headers={"X-Figma-Token": tok})
    except httpx.HTTPError as e:
        raise InspireError(f"Figma se baat nahi hui: {e}", 502)
    if r.status_code in (401, 403):
        raise InspireError("Figma ne mana kiya: token galat / purana hai, ya yeh file aapke account ki nahi.", 403)
    if r.status_code == 404:
        raise InspireError("Figma file nahi mili.", 404)
    if r.status_code != 200:
        raise InspireError(f"Figma ka jawaab {r.status_code}.", 502)
    doc = r.json()
    out = {"n": 0, "fills": Counter(), "fonts": Counter(), "texts": [], "radii": []}
    frames: list[str] = []
    pages = (doc.get("document") or {}).get("children") or []
    first = pages[0] if pages else {}
    for fr in (first.get("children") or [])[:40]:
        if isinstance(fr, dict) and fr.get("type") in ("FRAME", "SECTION", "COMPONENT", "INSTANCE", "GROUP"):
            frames.append(str(fr.get("name") or ""))
            for ch in fr.get("children") or []:
                if isinstance(ch, dict) and ch.get("type") in ("FRAME", "SECTION", "GROUP", "INSTANCE"):
                    frames.append(str(ch.get("name") or ""))
    _walk(first, out)
    total = sum(out["fills"].values()) or 1
    measured = [(c, round(w / total, 3)) for c, w in out["fills"].most_common(8)]
    big = max(out["fonts"].items(), key=lambda kv: (kv[0][1], kv[1]), default=(("", 0), 0))[0][0]
    radii = sorted(out["radii"])
    raw = {"head_family": big, "radius_px": radii[len(radii) // 2] if radii else 8, "sections": frames,
           "notes": f"From her Figma file '{str(doc.get('name') or '')[:60]}': {len(frames)} frames read."}
    content = {"name": str(doc.get("name") or "")[:120], "texts": out["texts"][:120]}
    ref = normalise("figma", raw, measured, content)
    ref["read_by"] = f"Figma API: {out['n']} layers, {len(out['fonts'])} text styles"
    return ref


# ---------------------------------------------------------------- 3. her OWN old website
def _secret() -> bytes:
    from ..config import get_settings
    st = get_settings()
    return (str(getattr(st, "api_key", "") or "") + "|hoola-own").encode()


def apex(host: str) -> str:
    h = (host or "").lower().strip(".")
    h = h[4:] if h.startswith("www.") else h
    return h


def own_token(tenant: str, host: str) -> str:
    return "hoola-own-" + hmac.new(_secret(), f"{tenant}|{apex(host)}".encode(), hashlib.sha256).hexdigest()[:20]


def _already_hers(tenant: str, host: str) -> bool:
    a = apex(host)
    try:
        from .hosting_models import SiteHost
        with session() as s:
            if any(apex(h.hostname) == a for h in s.scalars(select(SiteHost).where(SiteHost.tenant_id == tenant)).all()):
                return True
    except Exception:
        log.debug("host check failed", exc_info=True)
    try:
        from .domains import domains as _doms
        if any(apex(str(d.get("domain") or "")) == a for d in _doms(tenant)):
            return True
    except Exception:
        log.debug("domain check failed", exc_info=True)
    return False


def proof(tenant: str, url: str) -> dict[str, Any]:
    host = (urlparse(url if "//" in url else "https://" + url).hostname or "").lower()
    tok = own_token(tenant, host)
    return {"domain": apex(host), "txt_name": f"_hoola-own.{apex(host)}", "txt_value": tok,
            "meta": f'<meta name="hoola-own" content="{tok}">',
            "say": (f"Yeh site aapki hai, yeh dikhane ke liye do mein se ek kijiye: (1) DNS mein TXT record "
                    f"_hoola-own.{apex(host)} = {tok}, ya (2) site ke home page ke <head> mein yeh tag: "
                    f'<meta name="hoola-own" content="{tok}">. Phir dobara bhejiye.')}


def _owned(tenant: str, host: str, home_html: str) -> bool:
    if _already_hers(tenant, host):
        return True
    tok = own_token(tenant, host)
    m = re.search(r"""<meta[^>]+name=["']hoola-own["'][^>]*content=["']([^"']+)""", home_html or "", re.I) or \
        re.search(r"""<meta[^>]+content=["']([^"']+)["'][^>]*name=["']hoola-own["']""", home_html or "", re.I)
    if m and hmac.compare_digest(m.group(1).strip(), tok):
        return True
    try:
        from . import dns as D
        vals = D.lookup(f"_hoola-own.{apex(host)}", "TXT")
        flat = " ".join(" ".join(v) if isinstance(v, list) else str(v) for v in (vals.values() if isinstance(vals, dict) else vals))
        return tok in flat
    except Exception:
        log.debug("txt proof lookup failed", exc_info=True)
        return False


def _get(c: httpx.Client, url: str, cap: int, want: str = "text/html") -> tuple[bytes, str] | None:
    from ..appmaker import connect as CN
    u = urlparse(url)
    if u.scheme not in ("https", "http") or not u.hostname or u.username:
        return None
    try:
        CN._guard_host(u.hostname.lower())                 # public addresses only (never Hoola's own network)
    except Exception as e:                                 # noqa: BLE001 - the guard's own words, as her error
        raise InspireError(str(e), 400)
    try:
        with c.stream("GET", url) as r:
            if r.status_code != 200:
                return None
            ct = r.headers.get("content-type", "")
            if want and not ct.startswith(want):
                return None
            buf = bytearray()
            for ch in r.iter_bytes():
                buf.extend(ch)
                if len(buf) > cap:
                    return None
            return bytes(buf), str(r.url)
    except httpx.HTTPError:
        return None


def _robots_ok(c: httpx.Client, base: str) -> callable:
    got = _get(c, urljoin(base, "/robots.txt"), 200_000, want="")
    dis: list[str] = []
    if got:
        on = False
        for line in got[0].decode("utf-8", "replace").splitlines():
            line = line.split("#", 1)[0].strip()
            if line.lower().startswith("user-agent:"):
                on = line.split(":", 1)[1].strip() in ("*", "HoolaDesign")
            elif on and line.lower().startswith("disallow:"):
                p = line.split(":", 1)[1].strip()
                if p:
                    dis.append(p)
    return lambda path: not any(path.startswith(p) for p in dis)


def _strip(x: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", x or ""))).strip()


def read_page(html: str) -> dict[str, Any]:
    title = _strip((re.search(r"(?is)<title[^>]*>(.*?)</title>", html) or [None, ""])[1])[:140]
    site_name = (re.search(r"""(?i)<meta[^>]+property=["']og:site_name["'][^>]*content=["']([^"']+)""", html) or [None, ""])[1]
    heads = [_strip(h)[:160] for h in re.findall(r"(?is)<h[1-3][^>]*>(.*?)</h[1-3]>", html)][:20]
    paras = [p for p in (_strip(x) for x in re.findall(r"(?is)<p[^>]*>(.*?)</p>", html)) if len(p) > 40][:20]
    items = [i for i in (_strip(x) for x in re.findall(r"(?is)<li[^>]*>(.*?)</li>", html)) if 3 < len(i) < 120][:40]
    tels = re.findall(r"""href=["']tel:([+\d\s\-]{8,})""", html)
    mails = re.findall(r"""href=["']mailto:([^"'?]+)""", html)
    was = re.findall(r"""wa\.me/(\d{10,13})""", html)
    pins = sorted((t for t in (_strip(m.group(2)) for m in re.finditer(r"(?is)<(address|footer|p|li|span|div)[^>]*>(.*?)</\1>", html))
                   if re.search(r"\b[1-9]\d{5}\b", t) and 10 <= len(t) <= 220), key=len)
    return {"title": title, "site_name": unescape(site_name)[:120], "heads": heads, "paras": paras, "items": items,
            "phones": sorted({re.sub(r"\D", "", t)[-10:] for t in tels if len(re.sub(r'\D', '', t)) >= 10})[:3],
            "emails": sorted(set(m.strip() for m in mails))[:3], "whatsapp": sorted(set(was))[:2],
            "address": pins[0][:200] if pins else ""}


CSS_HEX = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b")


def css_design(css: str) -> dict[str, Any]:
    cols = Counter(_hex(m) for m in CSS_HEX.findall(css or ""))
    cols.pop("", None)
    fams = Counter()
    for m in re.findall(r"font-family\s*:\s*([^;}{]+)", css or "", re.I):
        f = m.split(",")[0].strip().strip("'\"")
        if f and not f.startswith("var(") and f.lower() not in ("inherit", "initial", "sans-serif", "serif", "system-ui"):
            fams[f] += 1
    radii = [int(x) for x in re.findall(r"border-radius\s*:\s*(\d{1,2})px", css or "", re.I)]
    total = sum(cols.values()) or 1
    return {"colours": [(c, round(n / total, 3)) for c, n in cols.most_common(10)],
            "font": fams.most_common(1)[0][0] if fams else "", "radius": sorted(radii)[len(radii) // 2] if radii else None}


def from_site(tenant: str, url: str) -> dict[str, Any]:
    u = urlparse(url if "//" in url else "https://" + url)
    if not u.hostname:
        raise InspireError("Website ka pura address chahiye (jaise https://meri-dukaan.in).")
    base = f"{u.scheme or 'https'}://{u.hostname}"
    host = u.hostname.lower()
    with httpx.Client(timeout=15, follow_redirects=True, transport=_TRANSPORT,
                      headers={"User-Agent": "HoolaDesign/1.0 (her own site, rebuilt in Hoola)"}) as c:
        home = _get(c, base + "/", PAGE_BYTES)
        if not home:
            raise InspireError(f"{host} ka home page nahi khula.", 502)
        home_html = home[0].decode("utf-8", "replace")
        if not _owned(tenant, host, home_html):
            raise InspireError("Pehle dikhaiye ki yeh website aapki hai.", 403, {"proof": proof(tenant, url)})
        allowed = _robots_ok(c, base)
        links: list[str] = []
        for href in re.findall(r"""<a[^>]+href=["']([^"'#]+)""", home_html, re.I):
            full = urljoin(base + "/", href)
            pu = urlparse(full)
            if (pu.hostname or "").lower() not in (host, "www." + apex(host), apex(host)):
                continue
            path = pu.path or "/"
            if re.search(r"\.(pdf|jpe?g|png|webp|gif|zip|mp4|svg|css|js)$", path, re.I) or path in ("/", ""):
                continue
            if path not in links and allowed(path):
                links.append(path)
        pages = [("/", home_html)]
        for path in links[:PAGES_MAX - 1]:
            got = _get(c, base + path, PAGE_BYTES)
            if got:
                pages.append((path, got[0].decode("utf-8", "replace")))
        css = ""
        for href in re.findall(r"""<link[^>]+rel=["']stylesheet["'][^>]*href=["']([^"']+)""", home_html, re.I)[:3]:
            full = urljoin(base + "/", href)
            if (urlparse(full).hostname or "").lower().endswith(apex(host)):
                got = _get(c, full, 800_000, want="")
                if got:
                    css += got[0].decode("utf-8", "replace")
        css += " ".join(re.findall(r"(?is)<style[^>]*>(.*?)</style>", home_html))
        imgs: list[tuple[str, str]] = []
        for path, html in pages:
            for m in re.finditer(r"""<img[^>]+src=["']([^"']+)["'][^>]*>""", html, re.I):
                src = urljoin(base + path, m.group(1))
                alt = (re.search(r"""alt=["']([^"']*)""", m.group(0)) or [None, ""])[1]
                if src.startswith("https://") and (urlparse(src).hostname or "").lower().endswith(apex(host)) and \
                        not re.search(r"(logo|icon|sprite|pixel|spacer)", src, re.I) and src not in [x for x, _ in imgs]:
                    imgs.append((src, unescape(alt)[:120]))
        photos: list[dict[str, Any]] = []
        for src, alt in imgs[:IMAGES_MAX * 2]:
            if len(photos) >= IMAGES_MAX:
                break
            got = _get(c, src, IMG_BYTES, want="image/")
            if not got:
                continue
            try:
                from PIL import Image
                w, h = Image.open(io.BytesIO(got[0])).size
            except Exception:
                continue
            if min(w, h) < 300:
                continue
            photos.append({"bytes": got[0], "about": alt, "src": src})
    read = [read_page(h) for _, h in pages]
    home_r = read[0]
    content = {"name": home_r["site_name"] or home_r["title"].split("|")[0].split("-")[0].strip(),
               "phone": next((p for r in read for p in r["phones"]), ""), "email": next((m for r in read for m in r["emails"]), ""),
               "whatsapp": next((w for r in read for w in r["whatsapp"]), ""), "address": next((r["address"] for r in read if r["address"]), ""),
               "about": (next((r["paras"][0] for (pth, _), r in zip(pages, read) if r["paras"] and
                               re.search(r"about|story|hamare|parichay", pth + " " + r["title"], re.I)), "")
                         or max((p for r in read for p in r["paras"]), key=len, default=""))[:800],
               "services": list(dict.fromkeys(h for r in read[1:] for h in r["heads"]))[:20],
               "pages": [{"path": p, "title": r["title"]} for (p, _), r in zip(pages, read)],
               "photos": len(photos)}
    cd = css_design(css)
    raw = {"head_family": cd["font"], "radius_px": cd["radius"] if cd["radius"] is not None else 8,
           "sections": [h for h in home_r["heads"]],
           "notes": f"Rebuilt from her own site {apex(host)}: {len(pages)} pages read."}
    ref = normalise("site", raw, cd["colours"], content)
    ref["read_by"] = f"{len(pages)} pages of {apex(host)} (robots.txt respected), {len(photos)} of her photos"
    ref["_photos"] = photos
    return ref


# ---------------------------------------------------------------- preview -> her tap
def _dir(tenant: str) -> Path:
    from . import build as B
    d = B.root().parent / "site_inspire" / re.sub(r"[^\w-]", "_", tenant)
    d.mkdir(parents=True, exist_ok=True)
    return d


def read(tenant: str, source: str, value: str = "", file_id: str = "", data: bytes | None = None) -> dict[str, Any]:
    """Read a design and keep it as a PREVIEW (nothing on any site changes)."""
    if source == "screenshot":
        ref = from_screenshot(tenant, file_id=file_id or value, data=data)
    elif source == "figma":
        ref = from_figma(tenant, value)
    elif source == "site":
        ref = from_site(tenant, value)
    else:
        raise InspireError("source = screenshot | figma | site")
    photos = ref.pop("_photos", [])
    tok = secrets.token_urlsafe(9)
    d = _dir(tenant) / tok
    d.mkdir()
    for i, p in enumerate(photos):
        (d / f"p{i:02d}.bin").write_bytes(p["bytes"])
    (d / "ref.json").write_text(json.dumps({**ref, "photos": [{"file": f"p{i:02d}.bin", "about": p["about"]}
                                                             for i, p in enumerate(photos)], "at": time.time()}))
    for old in _dir(tenant).iterdir():                      # day-old previews go
        try:
            if old.is_dir() and time.time() - old.stat().st_mtime > PREVIEW_TTL:
                import shutil
                shutil.rmtree(old, ignore_errors=True)
        except OSError:
            pass
    c = ref["content"]
    say = (f"Design padh liya ({ref['read_by']}): {ref['style_label']} andaaz, {ref['head']} + {ref['body']} font, "
           f"corners {ref['radius']}px, {'gehra' if ref['dark'] else 'halka'} rang"
           + (f", rang {', '.join(list(ref['overrides'].get(k, '') for k in ('primary', 'accent') if ref['overrides'].get(k)))}" if ref['overrides'].get('primary') else "")
           + (f"; sections: {', '.join(T.label_of(s) for s in ref['sections'][:6])}" if ref["sections"] else "")
           + (f"; unki site se: naam '{c.get('name')}', {c.get('photos', 0)} photos, {len(c.get('services') or [])} services" if ref["source"] == "site" else "")
           + ". Pehla look isi design se banega - 'haan, yahi design lagao' kahiye.")
    return {"token": tok, "ref": ref, "say": say}


def _load_preview(tenant: str, token: str) -> tuple[dict[str, Any], Path]:
    if not re.fullmatch(r"[\w-]{6,40}", token or ""):
        raise InspireError("Design preview ka token galat hai.")
    d = _dir(tenant) / token
    try:
        ref = json.loads((d / "ref.json").read_text())
    except (OSError, ValueError):
        raise InspireError("Woh design preview purana ho gaya; dobara bhejiye.", 404)
    if time.time() - float(ref.get("at") or 0) > PREVIEW_TTL:
        raise InspireError("Woh design preview purana ho gaya; dobara bhejiye.", 404)
    return ref, d


def use(tenant: str, token: str, ref_site: str = "", conv: str = "", brief: str = "") -> dict[str, Any]:
    """HER tap: the reference goes on a site (new when none is named) and the looks are made again with look 1 = hers."""
    from . import service as S
    from .models import Site
    ref, d = _load_preview(tenant, token)
    c = ref.get("content") or {}
    if ref_site:
        with session() as s:
            if S._find(s, tenant, ref_site).status == "building":
                raise InspireError("Website abhi ban rahi hai; banne ke baad design lagaiye.", 409)
    if not ref_site:
        words = brief or " ".join(x for x in [c.get("name") or "", c.get("about") or "", ", ".join((c.get("services") or [])[:6]),
                                              " ".join((c.get("texts") or [])[:6])] if x)[:1500]
        if not words.strip():
            raise InspireError("Kis cheez ki website hai, ek line mein bataiye (design ke saath).")
        answers = {k: c[k] for k in ("phone", "email", "address", "whatsapp") if c.get(k)}
        v = S.new(tenant, words, conv, name=c.get("name") or "", answers=answers)
        ref_site = v["id"]
    with session() as s:
        r = S._find(s, tenant, ref_site)
        facts = S._j(r.facts, {})
        facts["design_ref"] = {k: ref[k] for k in ("source", "style", "fonts", "head", "body", "radius", "dark", "overrides",
                                                   "sections", "notes", "read_by")}
        for k in ("phone", "email", "address", "whatsapp"):
            if c.get(k) and not facts.get(k):
                facts[k] = c[k]
        r.facts = S._jd(facts)
        status, rid = r.status, r.id
        s.flush()
    added = 0
    for p in ref.get("photos") or []:                       # her own photos from her own site
        try:
            S.add_photo(tenant, rid, data=(d / p["file"]).read_bytes(), about=p.get("about") or "")
            added += 1
        except Exception as e:                              # noqa: BLE001 - one bad photo never stops the rest
            log.info("inspire photo skipped: %s", e)
    remade = False
    if status in ("looks", "ready", "stopped", "failed"):
        with session() as s:
            r = s.get(Site, rid)
            r.status, r.stage, r.looks, r.stop, r.error = "looks", "look", "[]", False, ""
            r.updated_at = now()
        S._start(rid, "looks")
        remade = True
    say = ("Aapka design lag gaya: " + ("teen naye look ban rahe hain, pehla aapke design se." if remade else
           "plan pakka karte hi teen look banenge, pehla aapke design se.")
           + (f" Aapki purani site ki {added} photos bhi le li." if added else ""))
    return {"ok": True, "site": rid, "remade_looks": remade, "photos_added": added, "say": say}


def look_zero(facts: dict[str, Any]) -> dict[str, Any] | None:
    """The reference that makes look 1 hers (used by service._make_looks), or None."""
    ref = facts.get("design_ref")
    if not isinstance(ref, dict) or ref.get("style") not in T.STYLES:
        return None
    return ref


def brief_note(ref: dict[str, Any]) -> str:
    secs = ", ".join(T.label_of(s) for s in (ref.get("sections") or [])[:10])
    return ("\n\nHER OWN DESIGN REFERENCE (this look must follow it - her colours, her type, her corner shape; built in "
            f"Hoola's kit, never copied): read from her {ref.get('source')}; {ref.get('notes') or ''}"
            + (f" Section order she uses: {secs}." if secs else ""))
