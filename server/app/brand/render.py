"""v0.118 Brand Sahayak renderer: one design -> an HTML page per size -> PNG / JPEG / print PDF through Chromium.

Pages are built here as plain HTML + CSS + inline SVG (motifs drawn by Hoola, never anyone's logo or artwork), fonts are
the bundled OFL fonts inlined as data: URLs, and the browser runs offline with every request blocked, so a poster can never
pull anything from the internet. A small script fits the text: the whole type scale shrinks until nothing overflows the
safe area, and what still does not fit is reported back (so Hoola can say "headline chhoti kariye").
Proofs carry a diagonal "PROOF" mark; finals (only after her Haan) don't.
"""
from __future__ import annotations

import base64
import html as _html
import json
import logging
import math
import os
import random
from pathlib import Path
from typing import Any

from . import rules as R

log = logging.getLogger("santosh.brand")
FONT_DIR = Path(__file__).resolve().parent.parent / "motion" / "assets" / "fonts"
_FONTS: dict[str, str] = {}


class RenderError(Exception):
    pass


def available() -> str:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return "playwright"
    return ""


def _font_css() -> str:
    if "css" in _FONTS:
        return _FONTS["css"]
    faces = []
    for fam, files in (("Poppins", [("poppins-latin-400-normal.woff2", 400), ("poppins-latin-600-normal.woff2", 600),
                                     ("poppins-latin-800-normal.woff2", 800)]),
                       ("Mukta", [("mukta-devanagari-400-normal.woff2", 400), ("mukta-devanagari-700-normal.woff2", 700),
                                  ("mukta-devanagari-800-normal.woff2", 800), ("mukta-latin-400-normal.woff2", 400),
                                  ("mukta-latin-700-normal.woff2", 700), ("mukta-latin-800-normal.woff2", 800)])):
        for fn, w in files:
            p = FONT_DIR / fn
            if p.exists():
                b64 = base64.b64encode(p.read_bytes()).decode()
                rng = "unicode-range:U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+20B9,U+25CC,U+A830-A839,U+A8E0-A8FF;" \
                    if "devanagari" in fn else ""
                faces.append(f"@font-face{{font-family:'{fam}';font-weight:{w};font-display:block;{rng}"
                             f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    _FONTS["css"] = "\n".join(faces)
    return _FONTS["css"]


def esc(s: Any) -> str:
    return _html.escape(str(s or ""), quote=True)


# ---------------------------------------------------------------- motifs (original, simple geometry)
def motif_svg(kind: str, colors: list[str], w: float, h: float, seed: int = 7) -> str:
    rnd = random.Random(seed)
    c0, c1, c2 = (colors + ["#F5A623", "#FFD36E", "#FFFFFF"])[:3]
    parts: list[str] = []
    u = min(w, h) / 100
    if kind == "diya":
        n = 5 if w > h * 0.9 else 3
        for i in range(n):
            cx = w * (i + 0.5) / n
            cy = h - u * 4.5
            s = u * (3.2 if i % 2 else 4)
            parts.append(f'<ellipse cx="{cx:.0f}" cy="{cy - s * 2.2:.0f}" rx="{s * 0.9:.0f}" ry="{s * 1.6:.0f}" fill="url(#flame)"/>')
            parts.append(f'<path d="M{cx - s * 2:.0f},{cy - s * 0.6:.0f} Q{cx:.0f},{cy + s * 1.6:.0f} {cx + s * 2:.0f},'
                         f'{cy - s * 0.6:.0f} Z" fill="{c0}" stroke="{c2}" stroke-width="{u * 0.5:.1f}"/>')
            parts.append(f'<circle cx="{cx:.0f}" cy="{cy - s * 1.1:.0f}" r="{s * 0.9:.0f}" fill="url(#glow)"/>')
        defs = (f'<radialGradient id="flame" cx="50%" cy="70%" r="60%"><stop offset="0" stop-color="#FFFFFF"/>'
                f'<stop offset=".35" stop-color="{c2}"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></radialGradient>'
                f'<radialGradient id="glow"><stop offset="0" stop-color="{c2}" stop-opacity=".55"/>'
                f'<stop offset="1" stop-color="{c2}" stop-opacity="0"/></radialGradient>')
        for _ in range(28):
            x, y, r = rnd.random() * w, rnd.random() * h * 0.6, u * rnd.uniform(0.2, 0.7)
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{c2}" opacity="{rnd.uniform(.3, .9):.2f}"/>')
        return _svg(w, h, defs, parts)
    if kind == "rangoli":
        cx, cy, R0 = w * 0.85, h * 0.12, u * 22
        for ring, (cnt, col) in enumerate(((16, c1), (12, c2), (8, c0))):
            rr = R0 * (1 - ring * 0.28)
            for k in range(cnt):
                a = 360 * k / cnt
                parts.append(f'<ellipse cx="{cx:.0f}" cy="{cy - rr * 0.55:.0f}" rx="{rr * 0.18:.0f}" ry="{rr * 0.45:.0f}" '
                             f'fill="{col}" opacity=".85" transform="rotate({a:.1f} {cx:.0f} {cy:.0f})"/>')
        parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{R0 * 0.16:.0f}" fill="{c2}"/>')
        cx2, cy2 = w * 0.1, h * 0.92
        for k in range(12):
            parts.append(f'<ellipse cx="{cx2:.0f}" cy="{cy2 - R0 * 0.35:.0f}" rx="{R0 * 0.1:.0f}" ry="{R0 * 0.3:.0f}" fill="{c1}" '
                         f'opacity=".7" transform="rotate({30 * k} {cx2:.0f} {cy2:.0f})"/>')
        return _svg(w, h, "", parts)
    if kind == "toran":
        y0 = u * 2
        n = max(9, int(w / (u * 7)))
        pts = []
        for i in range(n + 1):
            x = w * i / n
            y = y0 + math.sin(math.pi * i / n) * u * 6
            pts.append((x, y))
        parts.append('<polyline points="' + " ".join(f"{x:.0f},{y:.0f}" for x, y in pts) +
                     f'" fill="none" stroke="{c2}" stroke-width="{u * 0.5:.1f}"/>')
        for i, (x, y) in enumerate(pts[1:-1], 1):
            col = c1 if i % 2 else c2
            parts.append(f'<path d="M{x - u * 1.6:.0f},{y:.0f} L{x:.0f},{y + u * 6:.0f} L{x + u * 1.6:.0f},{y:.0f} Z" '
                         f'fill="#2E7D32" opacity=".9"/>')
            parts.append(f'<circle cx="{x:.0f}" cy="{y + u * 1.4:.0f}" r="{u * 2.2:.1f}" fill="{col}"/>')
            parts.append(f'<circle cx="{x:.0f}" cy="{y + u * 1.4:.0f}" r="{u * 1.1:.1f}" fill="{c0}" opacity=".35"/>')
        return _svg(w, h, "", parts)
    if kind == "kite":
        for i in range(4):
            x, y, s = w * rnd.uniform(.08, .92), h * rnd.uniform(.05, .35), u * rnd.uniform(5, 9)
            col = (c0, c1, c2, "#E83F6F")[i % 4]
            parts.append(f'<path d="M{x:.0f},{y - s:.0f} L{x + s * .8:.0f},{y:.0f} L{x:.0f},{y + s * 1.2:.0f} '
                         f'L{x - s * .8:.0f},{y:.0f} Z" fill="{col}" transform="rotate({rnd.uniform(-25, 25):.0f} {x:.0f} {y:.0f})"/>')
            parts.append(f'<path d="M{x:.0f},{y + s * 1.2:.0f} q{s * .4:.0f},{s:.0f} {-s * .2:.0f},{s * 2.2:.0f}" fill="none" '
                         f'stroke="{c2}" stroke-width="{u * .35:.1f}"/>')
        return _svg(w, h, "", parts)
    if kind == "splash":
        for i in range(22):
            x, y, r = w * rnd.random(), h * rnd.random(), u * rnd.uniform(2, 11)
            col = (c0, c1, c2)[i % 3]
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="{col}" opacity="{rnd.uniform(.25, .6):.2f}"/>')
        return _svg(w, h, "", parts)
    if kind == "moon":
        cx, cy, r = w * 0.8, h * 0.16, u * 11
        parts.append(f'<mask id="cm"><rect width="{w:.0f}" height="{h:.0f}" fill="white"/>'
                     f'<circle cx="{cx + r * .45:.0f}" cy="{cy - r * .2:.0f}" r="{r * .9:.0f}" fill="black"/></mask>')
        parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="{c1}" mask="url(#cm)"/>')
        for _ in range(14):
            parts.append(_star(w * rnd.random(), h * rnd.random() * .5, u * rnd.uniform(.6, 1.6), c2, rnd.uniform(.4, .9)))
        return _svg(w, h, "", parts)
    if kind == "tree":
        cx, base, s = w * 0.84, h * 0.34, u * 12
        for k in range(3):
            top = base - s * (k + 1) * .55
            parts.append(f'<path d="M{cx:.0f},{top - s * .5:.0f} L{cx + s * (1 - k * .22):.0f},{top + s * .55:.0f} '
                         f'L{cx - s * (1 - k * .22):.0f},{top + s * .55:.0f} Z" fill="{c0}"/>')
        parts.append(_star(cx, base - s * 2.4, u * 2.4, c2, 1))
        for _ in range(16):
            parts.append(_star(w * rnd.random(), h * rnd.random() * .45, u * rnd.uniform(.4, 1.2), c2, rnd.uniform(.4, .9)))
        return _svg(w, h, "", parts)
    if kind == "waves":
        parts.append(f'<path d="M0,0 L{w:.0f},0 L{w:.0f},{u * 6:.0f} C{w * .7:.0f},{u * 16:.0f} {w * .3:.0f},{-u * 2:.0f} '
                     f'0,{u * 12:.0f} Z" fill="{c0}" opacity=".9"/>')
        parts.append(f'<path d="M0,{h:.0f} L{w:.0f},{h:.0f} L{w:.0f},{h - u * 12:.0f} C{w * .7:.0f},{h + u * 2:.0f} '
                     f'{w * .3:.0f},{h - u * 16:.0f} 0,{h - u * 6:.0f} Z" fill="{c2}" opacity=".9"/>')
        return _svg(w, h, "", parts)
    # sparkle (default) - soft stars + two blurred circles
    parts.append(f'<circle cx="{w * .92:.0f}" cy="{h * .08:.0f}" r="{u * 26:.0f}" fill="{c1}" opacity=".22"/>')
    parts.append(f'<circle cx="{w * .05:.0f}" cy="{h * .95:.0f}" r="{u * 20:.0f}" fill="{c2}" opacity=".18"/>')
    for _ in range(18):
        parts.append(_star(w * rnd.random(), h * rnd.random(), u * rnd.uniform(.5, 1.8), c2, rnd.uniform(.35, .95)))
    return _svg(w, h, "", parts)


def _star(x: float, y: float, s: float, col: str, op: float) -> str:
    return (f'<path d="M{x:.1f},{y - s * 2:.1f} Q{x:.1f},{y:.1f} {x + s * 2:.1f},{y:.1f} Q{x:.1f},{y:.1f} {x:.1f},{y + s * 2:.1f} '
            f'Q{x:.1f},{y:.1f} {x - s * 2:.1f},{y:.1f} Q{x:.1f},{y:.1f} {x:.1f},{y - s * 2:.1f} Z" fill="{col}" opacity="{op:.2f}"/>')


def _svg(w: float, h: float, defs: str, parts: list[str]) -> str:
    return (f'<svg class="motif" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none">'
            f'<defs>{defs}</defs>{"".join(parts)}</svg>')


# ---------------------------------------------------------------- the page
def frame(size: str) -> dict[str, Any]:
    """Page geometry in CSS px: screens = their pixel size; paper = mm at 96 dpi plus bleed on every side."""
    s = R.SIZES[size]
    if s.get("print"):
        bleed = s.get("bleed", 0)
        wmm, hmm = s["mm"][0] + 2 * bleed, s["mm"][1] + 2 * bleed
        w, h = wmm / 25.4 * 96, hmm / 25.4 * 96
        pad = (bleed + 6) / 25.4 * 96
        return {"w": w, "h": h, "top": pad, "bottom": pad, "side": pad, "mm": (wmm, hmm), "out_w": s["w"], "out_h": s["h"],
                "print": True}
    st, sb = s.get("safe", (60, 60))
    return {"w": s["w"], "h": s["h"], "top": st, "bottom": sb, "side": max(48, s["w"] * 0.06), "out_w": s["w"],
            "out_h": s["h"], "print": False}


def page(d: dict[str, Any], kit: dict[str, Any], size: str, proof: bool = True, photo: str = "", logo: str = "",
         bg_image: str = "", seed: int = 7) -> str:
    """d = {headline, sub, offer, cta, date, body, greeting, layout, kind, festival{...}, show_contact, theme}"""
    f = frame(size)
    w, h = f["w"], f["h"]
    asp = R.aspect(size) if not f["print"] else ("wide" if w > h * 1.4 else "portrait")
    cols = kit.get("colors") or {}
    primary = cols.get("primary") or "#1565C0"
    secondary = cols.get("secondary") or R.mix(primary, "#FFFFFF", 0.35)
    accent = cols.get("accent") or "#F5A623"
    dark = cols.get("dark") or "#111111"
    light = cols.get("light") or "#FFFFFF"
    layout = d.get("layout") or "hero"
    if layout in ("photo", "split") and not photo:
        layout = "hero"
    fest = d.get("festival") or {}
    if layout == "festival":
        fc = (fest.get("colors") or []) + [primary, accent, light]
        bg1, bg2 = fc[0], R.mix(fc[0], "#000000", 0.35)
        motif_cols = [fc[1], fc[2] if len(fc) > 2 else accent, "#FFF4D6"]
    elif layout in ("minimal",):
        bg1 = bg2 = light
        motif_cols = [primary, accent, secondary]
    elif layout == "offer":
        bg1, bg2 = dark, R.mix(dark, primary, 0.45)
        motif_cols = [accent, secondary, light]
    else:
        bg1, bg2 = primary, R.mix(primary, dark, 0.4)
        motif_cols = [secondary, accent, light]
    if layout == "festival" and (fest.get("motif") == "diya"):
        f["bottom"] = f["bottom"] + unit_of(w, h) * 15
    if layout in ("photo", "split") and asp not in ("wide", "banner"):
        badge_top = f"calc(50% - {unit_of(w, h) * 13:.0f}px)"
    else:
        badge_top = f"{f['top'] + unit_of(w, h) * 15:.0f}px"
    on_bg = R.best_text(R.mix(bg1, bg2, 0.5), [light, dark])
    on_accent = R.best_text(accent, [dark, light])
    on_panel = R.best_text(light, [dark, primary])
    head_font = "'Mukta','Poppins'" if kit.get("font") == "mukta" else "'Poppins','Mukta'"
    body_font = "'Mukta','Poppins'"
    unit = min(w, h) / 100
    big = {"tall": 1.0, "portrait": 1.0, "square": 0.95, "wide": 1.15, "banner": 1.35}.get(asp, 1.0)
    motif = (fest.get("motif") if layout == "festival" else d.get("motif")) or ("sparkle" if layout in ("hero", "offer") else "")
    motif_html = motif_svg(motif, motif_cols, w, h, seed) if motif else ""
    logo_html = f'<img class="logo" src="{logo}" alt="">' if logo else ""
    name = esc(kit.get("name"))
    tagline = esc(kit.get("tagline"))
    contact = _contact_line(kit) if d.get("show_contact", True) else ""
    headline, sub, offer = esc(d.get("headline")), esc(d.get("sub")), esc(d.get("offer"))
    cta, date_line, greeting = esc(d.get("cta")), esc(d.get("date")), esc(d.get("greeting"))
    body_items = [esc(x) for x in (d.get("body") or [])][:5]
    chips = "".join(f'<span class="chip">{x}</span>' for x in body_items)
    badge = f'<div class="badge"><span>{offer}</span></div>' if offer and layout not in ("offer", "festival") else ""
    photo_html = f'<div class="ph"><img src="{photo}" alt=""></div>' if photo and layout in ("photo", "split") else ""
    bgimg = f'<img class="bgimg" src="{bg_image}" alt="">' if bg_image else ""
    ai_tag = '<div class="aitag">AI image</div>' if bg_image else ""
    mark = ""
    if proof:
        mark = ('<div class="wm">' + "".join(f'<span>PROOF · {name or "Hoola"} · draft</span>' for _ in range(14)) + "</div>"
                '<div class="ribbon">PROOF</div>')

    if layout == "festival":
        center = (f'<div class="mid"><div class="greet" data-k>{greeting or headline}</div>'
                  f'{f"<div class=head2 data-k>{headline}</div>" if greeting and headline else ""}'
                  f'{f"<div class=sub data-k>{sub}</div>" if sub else ""}</div>'
                  f'<div class="card">{logo_html}<div><div class="bname">{name}</div>'
                  f'{f"<div class=tag>{tagline}</div>" if tagline else ""}</div></div>')
    elif layout == "offer":
        center = (f'<div class="top">{logo_html}<div class="bname">{name}</div></div>'
                  f'<div class="mid">{f"<div class=eyebrow>{date_line}</div>" if date_line else ""}'
                  f'<div class="head" data-k>{headline}</div>'
                  f'{f"<div class=big><span>{offer}</span></div>" if offer else ""}'
                  f'{f"<div class=sub data-k>{sub}</div>" if sub else ""}'
                  f'{f"<div class=chips>{chips}</div>" if chips else ""}</div>'
                  f'{f"<div class=cta>{cta}</div>" if cta else ""}')
    elif layout in ("photo", "split"):
        center = (f'<div class="panel"><div class="top">{logo_html}<div class="bname">{name}</div></div>'
                  f'{f"<div class=eyebrow>{date_line}</div>" if date_line else ""}'
                  f'<div class="head" data-k>{headline}</div>{f"<div class=sub data-k>{sub}</div>" if sub else ""}'
                  f'{f"<div class=chips>{chips}</div>" if chips else ""}'
                  f'{f"<div class=cta>{cta}</div>" if cta else ""}</div>')
    else:   # hero / minimal
        center = (f'<div class="top">{logo_html}<div class="bname">{name}</div></div>'
                  f'<div class="mid">{f"<div class=eyebrow>{date_line}</div>" if date_line else ""}'
                  f'<div class="head" data-k>{headline}</div>{f"<div class=sub data-k>{sub}</div>" if sub else ""}'
                  f'{f"<div class=chips>{chips}</div>" if chips else ""}</div>'
                  f'{f"<div class=cta>{cta}</div>" if cta else ""}')
    foot = f'<div class="foot">{contact}</div>' if contact else ""

    css = f"""
{_font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{w:.1f}px;height:{h:.1f}px;overflow:hidden;background:{bg1}}}
@page{{size:{w:.1f}px {h:.1f}px;margin:0}}
body{{-webkit-font-smoothing:antialiased;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
:root{{--u:{unit:.3f}px;--k:1;--big:{big};--p:{primary};--s:{secondary};--a:{accent};--d:{dark};--l:{light};
--on-bg:{on_bg};--on-a:{on_accent};--on-panel:{on_panel}}}
.stage{{position:relative;width:{w:.1f}px;height:{h:.1f}px;overflow:hidden;color:var(--on-bg);font-family:{body_font},sans-serif;
background:linear-gradient(150deg,{bg1} 0%,{bg2} 100%)}}
.bgimg{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.55}}
.motif{{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}}
.safe{{position:absolute;left:{f['side']:.0f}px;right:{f['side']:.0f}px;top:{f['top']:.0f}px;bottom:{f['bottom']:.0f}px;
display:flex;flex-direction:column;gap:calc(var(--u)*2.2*var(--k))}}
.top{{display:flex;align-items:center;gap:calc(var(--u)*2.4)}}
.logo{{max-height:calc(var(--u)*11);max-width:calc(var(--u)*30);object-fit:contain;border-radius:calc(var(--u)*1.2)}}
.bname{{font-family:{head_font},sans-serif;font-weight:700;font-size:calc(var(--u)*4.2*var(--k));letter-spacing:.01em;line-height:1.1}}
.mid{{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;justify-content:center;gap:calc(var(--u)*2.4*var(--k))}}
.eyebrow{{display:inline-block;align-self:flex-start;font-weight:700;font-size:calc(var(--u)*3.4*var(--k));padding:calc(var(--u)*.9) calc(var(--u)*2.4);
border-radius:999px;background:var(--a);color:var(--on-a)}}
.head{{font-family:{head_font},sans-serif;font-weight:800;line-height:1.04;letter-spacing:-.015em;
font-size:calc(var(--u)*11*var(--k)*var(--big));overflow-wrap:break-word}}
.head2{{font-family:{head_font},sans-serif;font-weight:700;font-size:calc(var(--u)*5.6*var(--k));line-height:1.15}}
.sub{{font-size:calc(var(--u)*4.4*var(--k)*var(--big));line-height:1.3;opacity:.95;max-width:92%}}
.chips{{display:flex;flex-wrap:wrap;gap:calc(var(--u)*1.4)}}
.chip{{font-size:calc(var(--u)*3.3*var(--k));font-weight:600;padding:calc(var(--u)*.8) calc(var(--u)*2);border-radius:999px;
border:calc(var(--u)*.3) solid currentColor;opacity:.95}}
.badge{{position:absolute;right:{f['side']:.0f}px;top:{badge_top};width:calc(var(--u)*24);height:calc(var(--u)*24);border-radius:50%;
background:var(--a);color:var(--on-a);display:flex;align-items:center;justify-content:center;text-align:center;transform:rotate(-10deg);
box-shadow:0 calc(var(--u)*1) calc(var(--u)*3) rgba(0,0,0,.25);padding:calc(var(--u)*2)}}
.badge span{{font-family:{head_font},sans-serif;font-weight:800;font-size:calc(var(--u)*5.2*var(--k));line-height:1}}
.cta{{align-self:flex-start;font-weight:800;font-size:calc(var(--u)*4.2*var(--k));padding:calc(var(--u)*1.8) calc(var(--u)*4.4);
border-radius:999px;background:var(--a);color:var(--on-a);box-shadow:0 calc(var(--u)*.8) calc(var(--u)*2.4) rgba(0,0,0,.2)}}
.foot{{margin-top:calc(var(--u)*1);display:flex;flex-wrap:wrap;gap:calc(var(--u)*1.2) calc(var(--u)*3);font-size:calc(var(--u)*3.2*var(--k));font-weight:600;
padding-top:calc(var(--u)*1.6);border-top:calc(var(--u)*.25) solid currentColor;opacity:.95}}
.foot b{{font-weight:800}}
.greet{{font-family:'Mukta','Poppins',sans-serif;font-weight:800;line-height:1.05;text-align:center;
font-size:calc(var(--u)*13*var(--k)*var(--big));color:#FFF4D6;text-shadow:0 calc(var(--u)*.6) calc(var(--u)*2.4) rgba(0,0,0,.35)}}
.festival .mid{{align-items:center;text-align:center}}
.festival .sub{{max-width:100%}}
.card{{display:flex;align-items:center;gap:calc(var(--u)*2.4);background:var(--l);color:var(--on-panel);border-radius:calc(var(--u)*3);
padding:calc(var(--u)*2.2) calc(var(--u)*3);align-self:center;max-width:100%}}
.card .tag{{font-size:calc(var(--u)*3*var(--k));opacity:.8}}
.minimal .stage{{color:var(--on-panel)}}
.minimal .safe{{border-left:calc(var(--u)*1.6) solid var(--p);padding-left:calc(var(--u)*4)}}
.minimal .head{{color:{primary if R.readable(light, primary, True) else R.best_text(light, [dark])}}}
.offer .big{{align-self:flex-start;background:var(--a);color:var(--on-a);border-radius:calc(var(--u)*3);transform:rotate(-2deg);
padding:calc(var(--u)*2) calc(var(--u)*4)}}
.offer .big span{{font-family:{head_font},sans-serif;font-weight:800;font-size:calc(var(--u)*15*var(--k)*var(--big));line-height:1}}
.photo .ph,.split .ph{{position:absolute;left:0;right:0;top:0;height:{'100%' if asp in ('wide', 'banner') else '50%'};
{'width:48%;left:auto;right:0;' if asp in ('wide', 'banner') else ''}}}
.ph img{{width:100%;height:100%;object-fit:cover;display:block}}
.photo .safe,.split .safe{{{'right:52%;' if asp in ('wide', 'banner') else f'top:calc(50% + {f["top"] * .2:.0f}px);'}}}
.photo .stage,.split .stage{{background:var(--l);color:var(--on-panel)}}
.panel{{display:flex;flex-direction:column;gap:calc(var(--u)*1.8*var(--k));flex:1 1 auto;min-height:0;justify-content:center;position:relative}}
.aitag{{position:absolute;right:calc(var(--u)*1.5);bottom:calc(var(--u)*1.2);font:600 calc(var(--u)*1.8) 'Poppins',sans-serif;
color:#fff;background:rgba(0,0,0,.45);padding:calc(var(--u)*.3) calc(var(--u)*1);border-radius:calc(var(--u)*.6)}}
.wm{{position:absolute;inset:-30%;display:flex;flex-wrap:wrap;gap:calc(var(--u)*9) calc(var(--u)*6);transform:rotate(-28deg);
align-content:center;justify-content:center;pointer-events:none;z-index:9}}
.wm span{{font:800 calc(var(--u)*4) 'Poppins',sans-serif;color:rgba(255,255,255,.22);text-shadow:0 0 2px rgba(0,0,0,.25);white-space:nowrap}}
.ribbon{{position:absolute;right:calc(var(--u)*-9);top:calc(var(--u)*4);transform:rotate(45deg);background:#E53935;color:#fff;
font:800 calc(var(--u)*3) 'Poppins',sans-serif;padding:calc(var(--u)*.8) calc(var(--u)*12);z-index:10}}
"""
    fit = """
<script>
(function(){
  var r=document.documentElement, safe=document.querySelector('.safe'), k=1, loops=0;
  function over(){ if(!safe) return false;
    if(safe.scrollHeight>safe.clientHeight+1||safe.scrollWidth>safe.clientWidth+1) return true;
    var boxes=safe.querySelectorAll('.mid,.panel');
    for(var j=0;j<boxes.length;j++){ if(boxes[j].scrollHeight>boxes[j].clientHeight+1) return true; }
    var els=safe.querySelectorAll('.head,.greet,.sub,.chip,.bname,.foot,.cta,.big span');
    for(var i=0;i<els.length;i++){ if(els[i].scrollWidth>els[i].clientWidth+2) return true; }
    return false; }
  while(over() && k>0.5 && loops<40){ k=k*0.95; loops++; r.style.setProperty('--k',k.toFixed(3)); }
  window.__fit={k:k, overflow:over()};
})();
</script>"""
    cls = f"{layout} {asp}"
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>'
            f'<body class="{cls}"><div class="stage">{bgimg}{photo_html}{motif_html}<div class="safe">{center}{foot}</div>{badge}{ai_tag}{mark}</div>'
            f'{fit}</body></html>')


def unit_of(w: float, h: float) -> float:
    return min(w, h) / 100


def _contact_line(kit: dict[str, Any]) -> str:
    c = kit.get("contact") or {}
    bits = []
    if c.get("phone"):
        bits.append(f"<span>☎ <b>{esc(c['phone'])}</b></span>")
    if c.get("whatsapp") and c.get("whatsapp") != c.get("phone"):
        bits.append(f"<span>WhatsApp <b>{esc(c['whatsapp'])}</b></span>")
    if c.get("website"):
        bits.append(f"<span>{esc(c['website'])}</span>")
    if c.get("instagram"):
        bits.append(f"<span>@{esc(str(c['instagram']).lstrip('@'))}</span>")
    if c.get("address"):
        bits.append(f"<span>{esc(c['address'])}</span>")
    return "".join(bits)


# ---------------------------------------------------------------- browser
def _launch(p):
    kw = {"args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--font-render-hinting=none",
                   "--force-color-profile=srgb"]}
    if os.environ.get("HOOLA_CHROMIUM"):
        kw["executable_path"] = os.environ["HOOLA_CHROMIUM"]
    return p.chromium.launch(**kw)


def render(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """jobs: {html, size, out: 'png'|'jpg'|'pdf', scale_to (px wide, optional)} -> {data, fit:{k, overflow}, w, h}."""
    if available():
        raise RenderError("Poster banane ke liye server par Playwright + Chromium chahiye (deploy/setup_motion.sh).")
    from playwright.sync_api import sync_playwright
    out: list[dict[str, Any]] = []
    with sync_playwright() as p:
        b = _launch(p)
        try:
            for j in jobs:
                f = frame(j["size"])
                target_w = j.get("scale_to") or f["out_w"]
                scale = max(0.2, min(4.0, target_w / f["w"]))
                ctx = b.new_context(viewport={"width": int(round(f["w"])), "height": int(round(f["h"]))},
                                    device_scale_factor=scale if j.get("out") != "pdf" else 1, offline=True)
                page = ctx.new_page()
                page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(("data:", "about:", "blob:")) else r.abort())
                page.set_content(j["html"], wait_until="load", timeout=30000)
                try:
                    page.evaluate("document.fonts.ready.then(()=>true)")
                except Exception:
                    pass
                fit = page.evaluate("window.__fit || {k:1, overflow:false}")
                if j.get("out") == "pdf":
                    wmm, hmm = f.get("mm") or (f["w"] / 96 * 25.4, f["h"] / 96 * 25.4)
                    data = page.pdf(width=f"{wmm:.1f}mm", height=f"{hmm:.1f}mm", print_background=True,
                                    margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
                elif j.get("out") == "jpg":
                    data = page.screenshot(type="jpeg", quality=int(j.get("quality") or 90), full_page=False)
                else:
                    data = page.screenshot(type="png", full_page=False)
                out.append({"data": data, "fit": fit, "w": int(round(f["w"] * scale)), "h": int(round(f["h"] * scale))})
                ctx.close()
        finally:
            b.close()
    return out


def data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def safe_image(data: bytes, max_px: int = 2400, keep_alpha: bool = False) -> tuple[bytes, str, tuple[int, int]]:
    """Her photo / logo re-encoded by Pillow (EXIF / GPS dropped, size capped) -> (bytes, mime, (w, h))."""
    import io

    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im)
    alpha = keep_alpha and (im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info))
    im = im.convert("RGBA" if alpha else "RGB")
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    if alpha:
        im.save(buf, "PNG", optimize=True)
        return buf.getvalue(), "image/png", im.size
    im.save(buf, "JPEG", quality=90, optimize=True)
    return buf.getvalue(), "image/jpeg", im.size


def dump(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False)
