"""Hoola Notebook visuals, drawn by Chromium (offline: every request except data: is blocked) so Hindi / Marathi /
other Indian scripts are shaped right: slide decks, video frames, infographics, mind maps and printable reports.

Nine looks like NotebookLM's video styles: classic, whiteboard, watercolor, retro_print, heritage, paper_craft, kawaii,
anime, custom. Fonts are the open-licence families bundled for Website Sahayak (app/site/assets/fonts)."""
from __future__ import annotations

import base64
import html
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

FONT_DIR = Path(__file__).resolve().parent.parent / "site" / "assets" / "fonts"
AI_LABEL = "AI se bana · Hoola"

STYLES: dict[str, dict[str, str]] = {
    "classic": {"label": "Classic", "head": "poppins", "body": "inter", "bg": "#F5F7FC", "ink": "#121A33", "muted": "#566079",
                "accent": "#3D5AFE", "accent2": "#00A99D", "card": "#FFFFFF", "line": "#DDE3F0",
                "img": "clean modern flat vector illustration, soft gradients, minimal shapes, professional editorial style"},
    "whiteboard": {"label": "Whiteboard", "head": "kalam", "body": "kalam", "bg": "#FFFFFF", "ink": "#1E1E1E", "muted": "#555555",
                   "accent": "#E63946", "accent2": "#1D70B8", "card": "#FFFFFF", "line": "#1E1E1E",
                   "img": "hand-drawn black marker sketch on a whiteboard, simple doodles, a few red and blue marker accents, plain white background"},
    "watercolor": {"label": "Watercolor", "head": "fraunces", "body": "nunito", "bg": "#FBF6EE", "ink": "#2B2D42", "muted": "#6B6F80",
                   "accent": "#2F6FD0", "accent2": "#E07A5F", "card": "rgba(255,255,255,.72)", "line": "#E8DCCB",
                   "img": "soft watercolor painting illustration, gentle washes of colour, visible paper texture, pastel tones"},
    "retro_print": {"label": "Retro print", "head": "dm-serif-display", "body": "josefin-sans", "bg": "#F2E8D5", "ink": "#1F2A36",
                    "muted": "#55606E", "accent": "#D7263D", "accent2": "#1B998B", "card": "#FBF5E9", "line": "#1F2A36",
                    "img": "retro risograph print illustration, halftone dots, limited palette of mustard, teal and red, vintage poster"},
    "heritage": {"label": "Heritage", "head": "rozha-one", "body": "laila", "bg": "#F6E9D2", "ink": "#3B1414", "muted": "#6D4C41",
                 "accent": "#8C1C13", "accent2": "#B8860B", "card": "#FFF8EC", "line": "#C9A227",
                 "img": "traditional Indian miniature painting style illustration, rich maroon and gold, intricate borders and patterns"},
    "paper_craft": {"label": "Paper-craft", "head": "baloo-2", "body": "nunito", "bg": "#E9F5F3", "ink": "#22313F", "muted": "#4F6272",
                    "accent": "#FF7F51", "accent2": "#2EC4B6", "card": "#FFFFFF", "line": "#CFE3E0",
                    "img": "layered paper-craft cut-out illustration, 3D paper layers with soft shadows, bright cheerful colours"},
    "kawaii": {"label": "Kawaii", "head": "baloo-2", "body": "nunito", "bg": "#FFF0F6", "ink": "#4A2C40", "muted": "#8A6A7E",
               "accent": "#FF5FA2", "accent2": "#5EB8FF", "card": "#FFFFFF", "line": "#FFD3E6",
               "img": "cute kawaii illustration, pastel colours, rounded friendly characters with happy faces, simple and soft"},
    "anime": {"label": "Anime", "head": "bricolage-grotesque", "body": "outfit", "bg": "#15112E", "ink": "#FFFFFF", "muted": "#C9C3EE",
              "accent": "#FFD23F", "accent2": "#FF4D8D", "card": "rgba(255,255,255,.08)", "line": "rgba(255,255,255,.18)",
              "img": "vibrant anime-style illustration, dynamic composition, cel shading, bright saturated colours"},
}
STYLES["custom"] = {**STYLES["classic"], "label": "Custom"}

DECO = {
    "classic": "radial-gradient(1200px 600px at 100% 0%, rgba(61,90,254,.10), transparent 60%),"
               "radial-gradient(900px 500px at 0% 100%, rgba(0,169,157,.10), transparent 60%)",
    "whiteboard": "linear-gradient(rgba(0,0,0,.035) 1px, transparent 1px) 0 0/40px 40px,"
                  "linear-gradient(90deg, rgba(0,0,0,.035) 1px, transparent 1px) 0 0/40px 40px",
    "watercolor": "radial-gradient(420px 300px at 92% 12%, rgba(47,111,208,.18), transparent 70%),"
                  "radial-gradient(520px 360px at 6% 92%, rgba(224,122,95,.20), transparent 70%),"
                  "radial-gradient(380px 260px at 60% 70%, rgba(129,178,154,.16), transparent 70%)",
    "retro_print": "radial-gradient(rgba(31,42,54,.10) 1.4px, transparent 1.6px) 0 0/14px 14px",
    "heritage": "linear-gradient(135deg, rgba(184,134,11,.10) 25%, transparent 25%) 0 0/36px 36px,"
                "linear-gradient(225deg, rgba(184,134,11,.10) 25%, transparent 25%) 0 0/36px 36px",
    "paper_craft": "radial-gradient(700px 420px at 100% 0%, rgba(46,196,182,.22), transparent 65%),"
                   "radial-gradient(700px 420px at 0% 100%, rgba(255,127,81,.20), transparent 65%)",
    "kawaii": "radial-gradient(rgba(255,95,162,.16) 3px, transparent 3.5px) 0 0/48px 48px,"
              "radial-gradient(rgba(94,184,255,.16) 3px, transparent 3.5px) 24px 24px/48px 48px",
    "anime": "repeating-linear-gradient(115deg, rgba(255,255,255,.035) 0 2px, transparent 2px 26px),"
             "radial-gradient(900px 600px at 85% 15%, rgba(255,77,141,.35), transparent 60%),"
             "radial-gradient(900px 600px at 10% 90%, rgba(106,44,255,.45), transparent 60%)",
}
DECO["custom"] = DECO["classic"]


def style_of(name: str) -> dict[str, str]:
    return {**STYLES.get(name if name in STYLES else "classic"), "key": name if name in STYLES else "classic"}


def esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def inline(s: Any) -> str:
    """Escaped text with **bold** and *italic*."""
    t = esc(s)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    return t


# ---------------------------------------------------------------- fonts
@lru_cache(maxsize=64)
def _font_file(fam: str, subset: str, weight: int) -> str:
    p = FONT_DIR / f"{fam}-{subset}-{weight}.woff2"
    if not p.exists():
        return ""
    return "data:font/woff2;base64," + base64.b64encode(p.read_bytes()).decode()


def font_css(st: dict[str, str]) -> str:
    out = []
    for fam in dict.fromkeys([st["head"], st["body"], "mukta"]):
        for subset, rng in (("latin", "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD,U+20B9"),
                            ("devanagari", "U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+20B9,U+25CC,U+A830-A839,U+A8E0-A8FF")):
            for wt in (400, 700):
                src = _font_file(fam, subset, wt)
                if src:
                    out.append(f"@font-face{{font-family:'{fam}';src:url({src}) format('woff2');font-weight:{wt};"
                               f"font-display:block;unicode-range:{rng}}}")
    return "".join(out)


def base_css(st: dict[str, str], w: int, h: int) -> str:
    fallback = "'mukta','Noto Sans','Noto Sans Devanagari','Noto Sans Bengali','Noto Sans Tamil','Noto Sans Telugu'," \
               "'Noto Sans Kannada','Noto Sans Malayalam','Noto Sans Gujarati','Noto Sans Gurmukhi','Noto Sans Oriya'," \
               "'Noto Naskh Arabic','Noto Sans CJK SC','Noto Color Emoji',sans-serif"
    dark = st["key"] == "anime"
    return (font_css(st) + f"""
:root{{--bg:{st['bg']};--ink:{st['ink']};--muted:{st['muted']};--a:{st['accent']};--b:{st['accent2']};--card:{st['card']};--line:{st['line']}}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{w}px;height:{h}px;overflow:hidden}}
body{{background:var(--bg);color:var(--ink);font-family:'{st['body']}',{fallback};-webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility}}
.page{{position:relative;width:{w}px;height:{h}px;overflow:hidden;background:{DECO.get(st['key'], DECO['classic'])},var(--bg)}}
h1,h2,h3,.head{{font-family:'{st['head']}',{fallback};font-weight:700;line-height:1.12;letter-spacing:{'0' if st['key'] in ('whiteboard', 'heritage') else '-.01em'}}}
b{{font-weight:700;color:{'var(--a)' if not dark else 'var(--a)'}}}
.muted{{color:var(--muted)}}
.label{{position:absolute;right:28px;bottom:18px;font-size:15px;color:var(--muted);opacity:.85;font-family:'{st['body']}',{fallback}}}
.src{{position:absolute;left:64px;bottom:20px;font-size:15px;color:var(--muted)}}
.card{{background:var(--card);border-radius:{'4px' if st['key'] in ('retro_print', 'whiteboard') else '22px'};
  {'border:3px solid var(--line);' if st['key'] in ('retro_print', 'whiteboard', 'heritage') else 'box-shadow:0 10px 30px rgba(20,30,60,.10);'}}}
.pic{{object-fit:cover;border-radius:{'6px' if st['key'] in ('retro_print', 'whiteboard') else '26px'};
  {'border:3px solid var(--ink);' if st['key'] in ('whiteboard', 'retro_print') else ''}{'box-shadow:0 14px 34px rgba(0,0,0,.18);' if st['key'] not in ('whiteboard',) else ''}}}
.heritage-frame{{position:absolute;inset:18px;border:4px double var(--b);border-radius:6px;pointer-events:none}}
.paper{{box-shadow:0 2px 0 rgba(0,0,0,.05),6px 8px 0 rgba(0,0,0,.08)}}
""")


FIT_JS = """<script>
(function(){
  function over(el){return el.scrollHeight>el.clientHeight+2||el.scrollWidth>el.clientWidth+2;}
  var els=document.querySelectorAll('.fit');
  for(var k=0;k<els.length;k++){var el=els[k];var fs=parseFloat(getComputedStyle(el).fontSize);var i=0;
    if(el.classList.contains('grow')){var cap=fs*(parseFloat(el.dataset.max||'1.6'));
      while(!over(el)&&fs<cap&&i<60){fs*=1.05;el.style.fontSize=fs+'px';i++;}}
    i=0;while(over(el)&&fs>9&&i<80){fs*=0.96;el.style.fontSize=fs+'px';i++;}
    if(over(el)){window.__overflow=(window.__overflow||0)+1;}}
})();
</script>"""


def doc(st: dict[str, str], w: int, h: int, body: str, extra_css: str = "", label: bool = True, lang: str = "") -> str:
    deco = '<div class="heritage-frame"></div>' if st["key"] == "heritage" else ""
    lab = f'<div class="label">{AI_LABEL}</div>' if label else ""
    return (f"<!doctype html><html lang='{esc(lang or 'en')}'><head><meta charset='utf-8'><style>{base_css(st, w, h)}{extra_css}</style>"
            f"</head><body><div class='page'>{deco}{body}{lab}</div>{FIT_JS}</body></html>")


def data_uri(data: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode()


# ---------------------------------------------------------------- slides (1600 x 900)
SW, SH = 1600, 900
SLIDE_CSS = """
.sl{position:absolute;inset:0;padding:70px 80px 64px 80px;display:flex;flex-direction:column}
.kicker{font-size:22px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--b);margin-bottom:14px}
.ttl{font-size:64px;margin-bottom:26px;max-width:100%}
.row{display:flex;gap:56px;flex:1;min-height:0}
.col{flex:1;min-width:0;display:flex;flex-direction:column;min-height:0}
.fit{flex:1;min-height:0;overflow:hidden;font-size:36px;display:flex;flex-direction:column;justify-content:center}
.fit p{font-size:1em;line-height:1.42;margin-bottom:.55em}
ul.pts{list-style:none}
ul.pts li{position:relative;padding-left:1.25em;font-size:1em;line-height:1.36;margin-bottom:.55em}
ul.pts li:before{content:'';position:absolute;left:0;top:.5em;width:.5em;height:.5em;border-radius:50%;background:var(--a)}
.pic-col{flex:0 0 40%;display:flex;align-items:center;justify-content:center}
.art{width:100%;height:100%;max-height:660px}
.pic-col img{width:100%;height:100%;max-height:640px}
.title-slide .ttl{font-size:92px;margin-bottom:24px}
.title-slide .sub{font-size:40px;color:var(--muted);line-height:1.35}
.bar{width:140px;height:10px;border-radius:6px;background:linear-gradient(90deg,var(--a),var(--b));margin-bottom:34px}
.stats{display:flex;gap:30px;flex:1;align-items:center}
.stat{flex:1;padding:46px 38px;display:flex;flex-direction:column;justify-content:center;min-height:300px}
.stat .v{font-size:118px;color:var(--a);font-weight:700;line-height:1}
.stat .l{font-size:34px;margin-top:20px;line-height:1.3}
.quote{font-size:72px;line-height:1.22;flex:1;display:flex;align-items:center}
.quote:before{content:'“';font-size:200px;color:var(--a);line-height:.6;margin-right:20px;align-self:flex-start}
.who{font-size:28px;color:var(--muted);margin-top:20px}
.tl{display:flex;gap:26px;flex:1;align-items:center}
.step{flex:1;padding:36px 30px;position:relative;min-height:320px;display:flex;flex-direction:column}
.step .n{font-size:28px;font-weight:700;color:#fff;background:var(--a);border-radius:999px;width:62px;height:62px;display:flex;
  align-items:center;justify-content:center;margin-bottom:18px}
.step .d{font-size:32px;font-weight:700;color:var(--b);margin-bottom:12px}
.step .x{font-size:34px;line-height:1.32;flex:1;justify-content:flex-start}
.section-n{font-size:200px;font-weight:700;color:var(--a);opacity:.9;line-height:1}
.two .card{padding:40px 44px}
.two h3{font-size:46px;margin-bottom:22px;color:var(--a)}
.big-pic{flex:1;display:flex;gap:40px;min-height:0}
.big-pic img{flex:0 0 56%;height:100%}
.big-pic .fit{font-size:38px}
"""


def _pts(items: list[str]) -> str:
    return "<ul class='pts'>" + "".join(f"<li>{inline(x)}</li>" for x in items if str(x).strip()) + "</ul>"


def slide_html(sl: dict[str, Any], st: dict[str, str], n: int, total: int, img: bytes | None = None,
               label: bool = False, lang: str = "") -> str:
    lay = sl.get("layout") or "bullets"
    title = sl.get("title") or ""
    pts = [str(x) for x in (sl.get("bullets") or [])]
    body = str(sl.get("body") or "")
    pic = f"<img class='pic' src='{data_uri(img, 'image/jpeg' if img[:2] == bytes([0xFF, 0xD8]) else 'image/png')}'>" if img else ""
    kick = f"<div class='kicker'>{esc(sl.get('kicker') or '')}</div>" if sl.get("kicker") else ""
    if lay == "title":
        inner = (f"<div class='sl title-slide'><div class='row'><div class='col' style='justify-content:center'>{kick}"
                 f"<div class='bar'></div><h1 class='ttl'>{inline(title)}</h1><div class='sub'>{inline(sl.get('subtitle') or body)}</div>"
                 f"</div><div class='pic-col'>{pic or art_svg(st, n)}</div></div></div>")
    elif lay == "section":
        inner = (f"<div class='sl'><div class='row'><div class='col' style='justify-content:center'><div class='section-n'>{esc(sl.get('number') or n)}</div>"
                 f"<h1 class='ttl' style='font-size:84px'>{inline(title)}</h1><div class='sub muted' style='font-size:36px;line-height:1.35'>{inline(body)}</div></div>"
                 f"<div class='pic-col' style='flex-basis:34%'>{pic or art_svg(st, n)}</div></div></div>")
    elif lay == "stats" and sl.get("stats"):
        cards = "".join(f"<div class='stat card'><div class='v head'>{esc(s.get('value'))}</div><div class='l'>{inline(s.get('label'))}</div></div>"
                        for s in (sl.get("stats") or [])[:4] if isinstance(s, dict))
        inner = f"<div class='sl'>{kick}<h2 class='ttl'>{inline(title)}</h2><div class='stats'>{cards}</div>" + \
                (f"<div class='fit' style='flex:0 0 auto;max-height:150px;margin-top:26px;font-size:28px'><p>{inline(body)}</p></div>" if body else "") + "</div>"
    elif lay == "quote":
        inner = (f"<div class='sl'>{kick}<div class='quote head'>{inline(sl.get('quote') or body)}</div>"
                 f"<div class='who'>{inline(sl.get('who') or title)}</div></div>")
    elif lay == "timeline" and sl.get("steps"):
        steps = "".join(f"<div class='step card'><div class='n'>{i + 1}</div><div class='d'>{inline(s.get('when') or '')}</div>"
                        f"<div class='x fit'>{inline(s.get('text') or '')}</div></div>"
                        for i, s in enumerate((sl.get("steps") or [])[:6]) if isinstance(s, dict))
        inner = f"<div class='sl'>{kick}<h2 class='ttl'>{inline(title)}</h2><div class='tl'>{steps}</div></div>"
    elif lay == "two_col" and (sl.get("left") or sl.get("right")):
        L, R = sl.get("left") or {}, sl.get("right") or {}
        inner = (f"<div class='sl two'>{kick}<h2 class='ttl'>{inline(title)}</h2><div class='row'>"
                 f"<div class='col card'><h3>{inline(L.get('heading'))}</h3><div class='fit grow' data-max='1.3'>{_pts(L.get('points') or [])}</div></div>"
                 f"<div class='col card'><h3>{inline(R.get('heading'))}</h3><div class='fit grow' data-max='1.3'>{_pts(R.get('points') or [])}</div></div>"
                 f"</div></div>")
    elif lay == "image" and pic:
        inner = (f"<div class='sl'>{kick}<h2 class='ttl'>{inline(title)}</h2><div class='big-pic'>{pic}"
                 f"<div class='fit' style='font-size:32px'>{('<p>' + inline(body) + '</p>') if body else ''}{_pts(pts)}</div></div></div>")
    else:   # bullets / closing / anything else
        text = (f"<p>{inline(body)}</p>" if body else "") + _pts(pts)
        inner = (f"<div class='sl'>{kick}<h2 class='ttl'>{inline(title)}</h2><div class='row'><div class='col'><div class='fit grow' data-max='1.35'>{text}</div></div>"
                 f"{f'<div class=pic-col>{pic}</div>' if pic else ''}</div></div>")
    srcs = sl.get("sources") or []
    foot = f"<div class='src'>Sources: {esc(', '.join('S' + str(s) for s in srcs[:6]))}</div>" if srcs else ""
    num = f"<div class='label' style='left:auto;right:{'250px' if label else '28px'}'>{n} / {total}</div>"
    return doc(st, SW, SH, inner + foot + num, SLIDE_CSS, label=label, lang=lang)


def art_svg(st: dict[str, str], seed: int = 0) -> str:
    """A decorative panel for slides without a picture, drawn in the style's own manner (never anyone's logo)."""
    a, b, ink, k = st["accent"], st["accent2"], st["ink"], st["key"]
    r = (seed * 37) % 60
    if k == "whiteboard":
        body = (f"<circle cx='300' cy='300' r='210' fill='none' stroke='{ink}' stroke-width='7' stroke-dasharray='560 30'/>"
                f"<path d='M140 330 C220 220 330 420 460 260' stroke='{a}' stroke-width='9' fill='none' stroke-linecap='round'/>"
                f"<path d='M180 200 l60 0 M180 230 l110 0 M180 400 l140 0' stroke='{b}' stroke-width='8' stroke-linecap='round'/>"
                f"<path d='M420 420 l40 40 m0 -40 l-40 40' stroke='{a}' stroke-width='8' stroke-linecap='round'/>")
    elif k == "heritage":
        petals = "".join(f"<ellipse cx='300' cy='170' rx='38' ry='110' fill='{a if i % 2 else b}' opacity='.85' "
                         f"transform='rotate({i * 30} 300 300)'/>" for i in range(12))
        body = (f"<circle cx='300' cy='300' r='250' fill='none' stroke='{b}' stroke-width='6'/>"
                f"<circle cx='300' cy='300' r='230' fill='none' stroke='{a}' stroke-width='2' stroke-dasharray='6 10'/>"
                f"{petals}<circle cx='300' cy='300' r='70' fill='{st['bg']}' stroke='{b}' stroke-width='6'/>"
                f"<circle cx='300' cy='300' r='28' fill='{a}'/>")
    elif k == "anime":
        rays = "".join(f"<polygon points='300,300 {300 + 320 * math.cos(i * 0.4):.0f},{300 + 320 * math.sin(i * 0.4):.0f} "
                       f"{300 + 320 * math.cos(i * 0.4 + 0.12):.0f},{300 + 320 * math.sin(i * 0.4 + 0.12):.0f}' "
                       f"fill='{a if i % 2 else b}' opacity='.55'/>" for i in range(16))
        body = (f"{rays}<circle cx='300' cy='300' r='150' fill='{b}'/><circle cx='300' cy='300' r='105' fill='{a}'/>"
                f"<polygon points='300,215 322,280 390,280 335,320 356,385 300,345 244,385 265,320 210,280 278,280' fill='#fff'/>")
    elif k == "kawaii":
        body = (f"<circle cx='300' cy='320' r='200' fill='{a}' opacity='.9'/><circle cx='230' cy='300' r='20' fill='{ink}'/>"
                f"<circle cx='370' cy='300' r='20' fill='{ink}'/><circle cx='238' cy='292' r='6' fill='#fff'/><circle cx='378' cy='292' r='6' fill='#fff'/>"
                f"<path d='M265 350 q35 32 70 0' stroke='{ink}' stroke-width='9' fill='none' stroke-linecap='round'/>"
                f"<ellipse cx='195' cy='350' rx='26' ry='14' fill='#fff' opacity='.55'/><ellipse cx='405' cy='350' rx='26' ry='14' fill='#fff' opacity='.55'/>"
                f"<circle cx='120' cy='120' r='34' fill='{b}'/><circle cx='480' cy='130' r='22' fill='{b}' opacity='.7'/><circle cx='500' cy='500' r='30' fill='{b}' opacity='.6'/>")
    elif k == "retro_print":
        dots = "".join(f"<circle cx='{x}' cy='{y}' r='{max(1, 13 - ((x - 300) ** 2 + (y - 300) ** 2) ** .5 / 22):.1f}' fill='{a}'/>"
                       for x in range(90, 520, 26) for y in range(90, 520, 26) if ((x - 300) ** 2 + (y - 300) ** 2) < 230 ** 2)
        body = f"<rect x='60' y='60' width='480' height='480' fill='{b}' opacity='.18'/>{dots}<rect x='60' y='60' width='480' height='480' fill='none' stroke='{ink}' stroke-width='6'/>"
    elif k == "paper_craft":
        body = "".join(f"<path d='M{60 + i * 22} {520 - i * 34} Q300 {160 + i * 40 - r} {540 - i * 22} {520 - i * 34} Z' fill='{c}' "
                       f"style='filter:drop-shadow(0 8px 10px rgba(0,0,0,.18))'/>"
                       for i, c in enumerate([b, a, "#FFD166", "#FFFFFF", b]))
    elif k == "watercolor":
        body = (f"<defs><filter id='w'><feTurbulence baseFrequency='.02' numOctaves='3' seed='{seed}'/><feDisplacementMap in='SourceGraphic' scale='40'/>"
                f"<feGaussianBlur stdDeviation='6'/></filter></defs>"
                f"<circle cx='260' cy='260' r='170' fill='{a}' opacity='.35' filter='url(#w)'/>"
                f"<circle cx='360' cy='350' r='150' fill='{b}' opacity='.35' filter='url(#w)'/>"
                f"<circle cx='300' cy='200' r='90' fill='#81B29A' opacity='.35' filter='url(#w)'/>")
    else:
        body = (f"<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='{a}'/><stop offset='1' stop-color='{b}'/></linearGradient></defs>"
                f"<circle cx='320' cy='280' r='220' fill='url(#g)' opacity='.92'/><circle cx='170' cy='430' r='90' fill='{b}' opacity='.55'/>"
                f"<rect x='360' y='360' width='170' height='170' rx='34' fill='{a}' opacity='.35' transform='rotate({12 + r} 445 445)'/>"
                f"<circle cx='470' cy='140' r='40' fill='none' stroke='{a}' stroke-width='10' opacity='.6'/>")
    return f"<svg class='art' viewBox='0 0 600 600' xmlns='http://www.w3.org/2000/svg'>{body}</svg>"


def image_page_html(img: bytes, w: int, h: int) -> str:
    """One picture as one PDF page of its own size (painted infographic)."""
    mime = "image/png" if img[:4] == bytes([137, 80, 78, 71]) else "image/jpeg"
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>@page{{size:{w}px {h}px;margin:0}}*{{margin:0;padding:0}}"
            f"img{{width:{w}px;height:{h}px;display:block}}</style></head><body><img src='{data_uri(img, mime)}'></body></html>")


def deck_pdf_html(pages: list[bytes]) -> str:
    """All slide PNGs on 16:9 pages (what the PDF download is printed from)."""
    imgs = "".join(f"<div class='p'><img src='{data_uri(p, 'image/png' if p[:4] == bytes([137, 80, 78, 71]) else 'image/jpeg')}'></div>"
                   for p in pages)
    return ("<!doctype html><html><head><meta charset='utf-8'><style>@page{size:1600px 900px;margin:0}*{margin:0;padding:0}"
            ".p{width:1600px;height:900px;page-break-after:always;overflow:hidden}.p img{width:1600px;height:900px;display:block}"
            f"</style></head><body>{imgs}</body></html>")


# ---------------------------------------------------------------- video frames (same 16:9 look, bigger type)
def scene_html(sc: dict[str, Any], st: dict[str, str], n: int, total: int, img: bytes | None, lang: str = "") -> str:
    sl = {"layout": "title" if n == 1 else ("image" if img else "bullets"), "title": sc.get("headline") or "",
          "subtitle": sc.get("sub") or "", "bullets": (sc.get("points") or [])[:4], "body": "" if img else sc.get("sub") or "",
          "kicker": sc.get("kicker") or ""}
    if img and n != 1:
        sl["layout"] = "image"
    if sc.get("stats") and not img:
        sl.update(layout="stats", stats=sc["stats"])
    return slide_html(sl, st, n, total, img, label=True, lang=lang)


# ---------------------------------------------------------------- infographic
INFO_SIZES = {"portrait": (1200, 2000), "landscape": (2000, 1200), "square": (1600, 1600)}
INFO_CSS = """
.ig{position:absolute;inset:0;padding:70px 70px 60px;display:flex;flex-direction:column}
.ig h1{font-size:76px;margin-bottom:10px}
.ig .sub{font-size:30px;color:var(--muted);margin-bottom:34px;line-height:1.35}
.ig .body{flex:1;min-height:0;overflow:hidden;font-size:26px;display:flex;flex-direction:column;justify-content:space-evenly}
.hero{display:flex;align-items:center;gap:28px;padding:30px 34px;margin-bottom:.9em;border-radius:24px;
  background:linear-gradient(135deg,var(--a),var(--b));color:#fff}
.hero .v{font-size:3.4em;font-weight:700;line-height:1}
.hero .l{font-size:1.25em;line-height:1.3}
.grid{display:grid;gap:.9em;margin-bottom:.9em}
.sec{padding:1em 1.1em}
.sec .ic{font-size:1.9em;line-height:1;margin-bottom:.25em}
.sec h3{font-size:1.25em;margin-bottom:.3em;color:var(--a)}
.sec p{font-size:1em;line-height:1.38}
.sec ul{margin-top:.3em;padding-left:1.1em}
.sec li{font-size:.95em;line-height:1.35;margin-bottom:.2em}
.stats{display:flex;gap:.8em;margin-bottom:.9em}
.st{flex:1;padding:.8em;text-align:center}
.st .v{font-size:2.2em;font-weight:700;color:var(--a);line-height:1.05}
.st .l{font-size:.9em;margin-top:.3em;line-height:1.25}
.steps{display:flex;gap:.7em;margin-bottom:.9em}
.stp{flex:1;padding:.8em;position:relative}
.stp .n{display:inline-flex;width:1.7em;height:1.7em;border-radius:50%;background:var(--b);color:#fff;font-weight:700;
  align-items:center;justify-content:center;margin-bottom:.3em}
.stp p{font-size:.95em;line-height:1.3}
.take{padding:1em 1.2em;border-left:10px solid var(--a);font-size:1.1em;line-height:1.4}
"""


def infographic_html(spec: dict[str, Any], st: dict[str, str], orientation: str, lang: str = "") -> tuple[str, int, int]:
    w, h = INFO_SIZES.get(orientation, INFO_SIZES["portrait"])
    cols = 3 if orientation == "landscape" else 2
    secs = [s for s in (spec.get("sections") or []) if isinstance(s, dict)][:9]
    hero = spec.get("hero") if isinstance(spec.get("hero"), dict) else None
    stats = [s for s in (spec.get("stats") or []) if isinstance(s, dict)][:4]
    steps = [str(s) for s in (spec.get("steps") or []) if str(s).strip()][:6]
    parts = []
    if hero and hero.get("value"):
        parts.append(f"<div class='hero'><div class='v head'>{esc(hero['value'])}</div><div class='l'>{inline(hero.get('label'))}</div></div>")
    if stats:
        parts.append("<div class='stats'>" + "".join(f"<div class='st card'><div class='v head'>{esc(s.get('value'))}</div>"
                                                    f"<div class='l'>{inline(s.get('label'))}</div></div>" for s in stats) + "</div>")
    if secs:
        parts.append(f"<div class='grid' style='grid-template-columns:repeat({cols},1fr)'>" + "".join(
            f"<div class='sec card'><div class='ic'>{esc(s.get('icon') or '•')}</div><h3>{inline(s.get('heading'))}</h3>"
            f"<p>{inline(s.get('text') or '')}</p>" + (("<ul>" + "".join(f"<li>{inline(p)}</li>" for p in (s.get('points') or [])[:4]) + "</ul>")
                                                         if s.get("points") else "") + "</div>" for s in secs) + "</div>")
    if steps:
        parts.append("<div class='steps'>" + "".join(f"<div class='stp card'><span class='n'>{i + 1}</span><p>{inline(x)}</p></div>"
                                                    for i, x in enumerate(steps)) + "</div>")
    if spec.get("takeaway"):
        parts.append(f"<div class='take card'>{inline(spec['takeaway'])}</div>")
    srcs = spec.get("sources") or []
    foot = f"<div class='src'>Sources: {esc(', '.join('S' + str(s) for s in srcs[:8]))}</div>" if srcs else ""
    body = (f"<div class='ig'><h1>{inline(spec.get('title'))}</h1><div class='sub'>{inline(spec.get('subtitle') or '')}</div>"
            f"<div class='body fit grow' data-max='2.2'>{''.join(parts)}</div></div>{foot}")
    return doc(st, w, h, body, INFO_CSS, label=True, lang=lang), w, h


# ---------------------------------------------------------------- mind map
def _wrap(label: str, n: int = 24) -> list[str]:
    words, lines, cur = str(label).split(), [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > n and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    if cur:
        lines.append(cur)
    return lines[:3] or [""]


def mindmap_svg(root: dict[str, Any], st: dict[str, str]) -> tuple[str, int, int]:
    """A left-to-right tree: root on the left, branches coloured, curved links. Returns (html, w, h)."""
    palette = [st["accent"], st["accent2"], "#F59E0B", "#10B981", "#8B5CF6", "#EF4444", "#0EA5E9", "#D946EF"]
    PAD, GAP_Y = 16, 18
    nodes: list[dict] = []

    def walk(n: dict, depth: int, color: str) -> dict:
        kids = [k for k in (n.get("children") or []) if isinstance(k, dict)][:8] if depth < 4 else []
        lines = _wrap(n.get("label") or "", 22 if depth else 18)
        fs = 30 if depth == 0 else 24 if depth == 1 else 21
        w = int(max(len(x) for x in lines) * fs * 0.56) + PAD * 2 + 10
        h = len(lines) * int(fs * 1.25) + PAD * 2 - 6
        me = {"lines": lines, "fs": fs, "w": max(w, 90), "h": h, "depth": depth, "color": color, "kids": []}
        for i, k in enumerate(kids):
            me["kids"].append(walk(k, depth + 1, palette[i % len(palette)] if depth == 0 else color))
        nodes.append(me)
        return me

    tree = walk(root, 0, st["ink"] if st["key"] != "anime" else st["accent"])
    col_w: dict[int, int] = {}
    for nd in nodes:
        col_w[nd["depth"]] = max(col_w.get(nd["depth"], 0), nd["w"])
    xs, x = {}, 60
    for d in sorted(col_w):
        xs[d] = x
        x += col_w[d] + 90

    def height(nd: dict) -> int:
        if not nd["kids"]:
            return nd["h"] + GAP_Y
        return max(nd["h"] + GAP_Y, sum(height(k) for k in nd["kids"]))

    def place(nd: dict, top: int) -> None:
        hh = height(nd)
        nd["x"] = xs[nd["depth"]]
        nd["y"] = top + hh / 2 - nd["h"] / 2
        t = top + (hh - sum(height(k) for k in nd["kids"])) / 2 if nd["kids"] else top
        for k in nd["kids"]:
            place(k, t)
            t += height(k)

    total_h = height(tree)
    place(tree, 60)
    W, H = int(x + 20), int(total_h + 120)
    W, H = max(W, 900), max(H, 600)
    dark = st["key"] == "anime"
    out = []

    def draw(nd: dict) -> None:
        for k in nd["kids"]:
            x1, y1 = nd["x"] + nd["w"], nd["y"] + nd["h"] / 2
            x2, y2 = k["x"], k["y"] + k["h"] / 2
            mx = (x1 + x2) / 2
            out.append(f"<path d='M{x1:.0f},{y1:.0f} C{mx:.0f},{y1:.0f} {mx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}' "
                       f"stroke='{k['color']}' stroke-width='{4 if nd['depth'] == 0 else 3}' fill='none' opacity='.75'/>")
            draw(k)
        root_ = nd["depth"] == 0
        fill = nd["color"] if root_ or nd["depth"] == 1 else ("rgba(255,255,255,.08)" if dark else "#FFFFFF")
        ink = "#FFFFFF" if (root_ or nd["depth"] == 1) else st["ink"]
        out.append(f"<rect x='{nd['x']:.0f}' y='{nd['y']:.0f}' width='{nd['w']}' height='{nd['h']}' rx='{18 if root_ else 14}' "
                   f"fill='{fill}' stroke='{nd['color']}' stroke-width='{0 if (root_ or nd['depth'] == 1) else 2.5}'/>")
        lh = int(nd["fs"] * 1.25)
        y0 = nd["y"] + (nd["h"] - lh * len(nd["lines"])) / 2 + nd["fs"] * 0.95
        for i, ln in enumerate(nd["lines"]):
            out.append(f"<text x='{nd['x'] + nd['w'] / 2:.0f}' y='{y0 + i * lh:.0f}' text-anchor='middle' font-size='{nd['fs']}' "
                       f"font-weight='{700 if nd['depth'] < 2 else 400}' fill='{ink}'>{esc(ln)}</text>")

    draw(tree)
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}' "
           f"style='font-family:\"{st['head']}\",\"mukta\",\"Noto Sans\",sans-serif'>{''.join(out)}</svg>")
    return doc(st, W, H, svg, "", label=True), W, H


def count_nodes(n: dict[str, Any]) -> int:
    return 1 + sum(count_nodes(k) for k in (n.get("children") or []) if isinstance(k, dict))


# ---------------------------------------------------------------- reports (Markdown -> print HTML)
def md_to_html(md: str) -> str:
    lines = (md or "").replace("\r", "").split("\n")
    out, i, in_ul, in_ol = [], 0, False, False

    def close():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
        if in_ol:
            out.append("</ol>")
        in_ul = in_ol = False

    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            close()
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>" +
                       "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</table>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", ln)
        if m:
            close()
            lv = len(m.group(1))
            out.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>")
        elif re.match(r"^\s*[-*•]\s+", ln):
            if not in_ul:
                close()
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(re.sub(r'^\s*[-*•]\s+', '', ln))}</li>")
        elif re.match(r"^\s*\d+[.)]\s+", ln):
            if not in_ol:
                close()
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline(re.sub(r'^\s*\d+[.)]\s+', '', ln))}</li>")
        elif ln.strip().startswith(">"):
            close()
            out.append(f"<blockquote>{inline(ln.strip().lstrip('>').strip())}</blockquote>")
        elif re.match(r"^\s*(-{3,}|\*{3,})\s*$", ln):
            close()
            out.append("<hr>")
        elif not ln.strip():
            close()
        else:
            close()
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    close()
    return "".join(out)


def report_html(title: str, md: str, lang: str = "") -> str:
    st = style_of("classic")
    css = font_css(st) + """
@page{size:A4;margin:18mm 16mm}
body{font-family:'inter','mukta','Noto Sans',sans-serif;color:#1d2433;font-size:11.5pt;line-height:1.55}
h1{font-family:'poppins','mukta',sans-serif;font-size:22pt;color:#202a62;margin:0 0 6pt}
h2{font-family:'poppins','mukta',sans-serif;font-size:15pt;color:#3D5AFE;margin:16pt 0 6pt}
h3{font-family:'poppins','mukta',sans-serif;font-size:12.5pt;margin:12pt 0 4pt}
p{margin:0 0 7pt} ul,ol{margin:0 0 8pt 18pt} li{margin-bottom:3pt}
table{border-collapse:collapse;width:100%;margin:8pt 0;font-size:10pt} th,td{border:1px solid #cfd6e6;padding:5pt 6pt;text-align:left;vertical-align:top}
th{background:#eef1fb} blockquote{border-left:4px solid #3D5AFE;padding:4pt 10pt;color:#4a5470;margin:8pt 0}
.meta{color:#6b7488;font-size:9.5pt;margin-bottom:14pt}
"""
    return (f"<!doctype html><html lang='{esc(lang or 'en')}'><head><meta charset='utf-8'><style>{css}</style></head><body>"
            f"<h1>{inline(title)}</h1><div class='meta'>Hoola Notebook · {AI_LABEL}</div>{md_to_html(md)}</body></html>")


# ---------------------------------------------------------------- Chromium
class RenderError(Exception):
    pass


def available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


def _launch(p):
    kw = {"args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--font-render-hinting=none",
                   "--force-color-profile=srgb"]}
    if os.environ.get("HOOLA_CHROMIUM"):
        kw["executable_path"] = os.environ["HOOLA_CHROMIUM"]
    return p.chromium.launch(**kw)


def shoot(pages: list[tuple[str, int, int]], scale: float = 1.0, jpeg: bool = False) -> list[dict[str, Any]]:
    """[(html, w, h)] -> [{data, overflow}] screenshots (PNG, or JPEG for video frames)."""
    if not available():
        raise RenderError("Iske liye server par Playwright + Chromium chahiye (deploy/setup_motion.sh).")
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as p:
        b = _launch(p)
        try:
            for doc_, w, h in pages:
                ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=scale, offline=True)
                page = ctx.new_page()
                page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(("data:", "about:", "blob:")) else r.abort())
                page.set_content(doc_, wait_until="load", timeout=60000)
                try:
                    page.evaluate("document.fonts.ready.then(()=>true)")
                except Exception:
                    pass
                over = page.evaluate("window.__overflow || 0")
                data = page.screenshot(type="jpeg", quality=90) if jpeg else page.screenshot(type="png")
                out.append({"data": data, "overflow": over})
                ctx.close()
        finally:
            b.close()
    return out


def pdf(doc_: str, width: str = "", height: str = "") -> bytes:
    if not available():
        raise RenderError("PDF ke liye server par Playwright + Chromium chahiye.")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = _launch(p)
        try:
            ctx = b.new_context(offline=True)
            page = ctx.new_page()
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(("data:", "about:", "blob:")) else r.abort())
            page.set_content(doc_, wait_until="load", timeout=120000)
            try:
                page.evaluate("document.fonts.ready.then(()=>true)")
            except Exception:
                pass
            kw = {"print_background": True, "prefer_css_page_size": True}
            if width and height:
                kw.update(width=width, height=height, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
            return page.pdf(**kw)
        finally:
            b.close()
