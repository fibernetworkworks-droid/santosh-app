"""v0.784 SAWAAL CARD (L3 of docs/LOVABLE_STUDIO_PLAN.md): before a website is built, Hoola asks up to four design
questions with things she can SEE - the feel (style), the colours (real palettes drawn as swatches), the type (font
pairs shown in their own fonts) and the front of the home page (hero layouts drawn as wireframes). Every option comes
from Hoola's own design library (site/taxonomy.py), so whatever she picks is something the builder can really make.

The card is skipped when her words already decide the design (a colour, a hex code, a font, a style name, 'like my
screenshot / Figma / old site') - asking again would be noise. Nothing here calls a model.

Her answers become look 1 the same way her own screenshot does (v0.567 KOI BHI DESIGN): `design_ref` with source
'answers', read by service._make_looks through inspire.look_zero. Looks 2 and 3 stay Hoola's alternatives."""
from __future__ import annotations

import contextvars
import re
from typing import Any

from . import library as L
from . import taxonomy as T
from .build import ASSETS, _font_slug

# the route sets this while S.new runs, so the design lands on the row BEFORE the looks job reads it (no race)
PENDING: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar("site_design_pending", default=None)

_COLOURS = ("red", "blue", "green", "yellow", "orange", "purple", "violet", "pink", "black", "white", "grey", "gray",
            "gold", "golden", "silver", "maroon", "navy", "teal", "beige", "cream", "brown", "saffron", "magenta",
            "turquoise", "pastel", "neon", "monochrome", "black and white", "laal", "lal", "neela", "nila", "hara",
            "peela", "pila", "kala", "kaala", "safed", "sunehra", "gulabi", "bhagwa", "kesari", "baingani", "aasmani")
_DESIGN_WORDS = ("screenshot", "figma", "like my old site", "my old website", "same design", "same look", "jaisa design",
                 "design jaisa", "brand colour", "brand color", "brand colours", "brand colors", "my logo colour",
                 "dark mode", "dark theme", "light theme", "colour scheme", "color scheme", "font", "typeface")
_HEX = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b")


def _has(words: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", words) is not None


def skip_reason(words: str) -> str:
    """Why no question card is needed ('' = ask). Her own words always win over Hoola's questions."""
    w = (words or "").lower()
    if _HEX.search(words or ""):
        return "her words give a colour code"
    for c in _COLOURS:
        if _has(w, c):
            return f"her words name a colour ({c})"
    for p in _DESIGN_WORDS:
        if _has(w, p):
            return f"her words already describe the design ({p})"
    for k, st in T.STYLES.items():
        if _has(w, st["label"].lower()) or _has(w, k.replace("_", " ")):
            return f"her words name a style ({st['label']})"
    names = {f[x].lower() for f in T.FONTS.values() for x in ("head", "body")}
    for n in names:
        if len(n) > 3 and _has(w, n):
            return f"her words name a font ({n})"
    return ""


def _font_url(fam: str, w: int = 600) -> str:
    for sub in ("latin", "devanagari"):
        for wt in (w, 400, 600, 700, 500):
            fn = f"{_font_slug(fam)}-{sub}-{wt}.woff2"
            if (ASSETS / "fonts" / fn).exists():
                return f"/api/site-design/font/{fn}"
    return ""


def _font_opt(key: str) -> dict[str, Any]:
    f = T.FONTS[key]
    return {"id": key, "label": f"{f['head']} + {f['body']}", "head": f["head"], "body": f["body"],
            "head_url": _font_url(f["head"], 600), "body_url": _font_url(f["body"], 400)}


def _pal_opt(key: str) -> dict[str, Any]:
    p = T.PALETTES[key]
    return {"id": key, "label": key.replace("_", " ").capitalize(), "moods": p["moods"],
            "colours": {k: p[k] for k in ("bg", "surface", "ink", "primary", "accent")}}


def wire_of(hero: str) -> str:
    """Which wireframe the Studio draws for a hero layout (read from its own description)."""
    d = T.HEROES.get(hero, "").lower()
    if any(x in d for x in ("left", "right", "split", "beside", "side")):
        return "split"
    if any(x in d for x in ("edge-to-edge", "full", "overlay", "background video", "fills")):
        return "full"
    if any(x in d for x in ("grid", "cards", "stack", "collage", "tiles", "index")):
        return "grid"
    if any(x in d for x in ("oversized", "big", "kinetic", "letters", "marquee", "strip of words")):
        return "type"
    return "centre"


def questions(words: str, field: str = "") -> dict[str, Any]:
    """{skip, why} or {skip: False, questions: [...]} - up to four cards, the first option of each picked already."""
    from ..config import get_settings
    why = "" if getattr(get_settings(), "studio_design_questions", True) else "the design questions are switched off"
    why = why or skip_reason(words)
    if why:
        return {"skip": True, "why": why, "questions": []}
    u = L.understand(words or field)
    styles = list(u.get("styles") or [])[:3]
    for s in T.STYLES:                                    # four feels: her field's three + the next different one
        if len(styles) >= 4:
            break
        if s not in styles:
            styles.append(s)
    pals: list[str] = []                                  # two for her field's first feel, one each for the next two
    for s, n in zip(styles[:3], (2, 1, 1)):
        for p in L.palettes_for(T.STYLES[s]["moods"], n=n + len(pals), seed=(words or "")[:80] + s):
            if p not in pals and len(pals) < 4:
                pals.append(p)
                n -= 1
                if n == 0:
                    break
    fonts: list[str] = []
    for s in styles:
        k = T.STYLES[s]["fonts"]
        if k in T.FONTS and k not in fonts:
            fonts.append(k)
    for k in T.FONTS:
        if len(fonts) >= 4:
            break
        if k not in fonts:
            fonts.append(k)
    heroes: list[str] = []
    for s in styles:
        for h in T.STYLES[s]["heroes"]:
            if h in T.HEROES and h not in heroes and wire_of(h) not in [wire_of(x) for x in heroes]:
                heroes.append(h)
    for h in T.HEROES:
        if len(heroes) >= 4:
            break
        if h not in heroes:
            heroes.append(h)
    qs = [
        {"id": "style", "title": "What should it feel like?", "kind": "style",
         "options": [{"id": s, "label": T.STYLES[s]["label"], "line": T.STYLES[s]["do"][:110],
                      "colours": _pal_opt(L.palettes_for(T.STYLES[s]["moods"], 1, s)[0])["colours"],
                      "font": _font_opt(T.STYLES[s]["fonts"]) if T.STYLES[s]["fonts"] in T.FONTS else None,
                      "radius": T.STYLES[s]["radius"]} for s in styles[:4]]},
        {"id": "palette", "title": "Pick the colours", "kind": "palette", "options": [_pal_opt(p) for p in pals]},
        {"id": "fonts", "title": "Pick the type", "kind": "fonts", "options": [_font_opt(k) for k in fonts[:4]]},
        {"id": "hero", "title": "The top of the home page", "kind": "hero",
         "options": [{"id": h, "label": h.replace("_", " ").capitalize(), "line": T.HEROES[h], "wire": wire_of(h)}
                     for h in heroes[:4]]},
    ]
    return {"skip": False, "why": "", "field": u.get("field_label") or "", "questions": qs}


def ref_from(answers: dict[str, Any] | None) -> dict[str, Any] | None:
    """Her picks -> a design_ref (the v0.567 shape) for look 1, or None when she picked nothing usable. Only ids from
    Hoola's own library are taken; anything else is ignored."""
    a = answers if isinstance(answers, dict) else {}
    style = a.get("style") if a.get("style") in T.STYLES else ""
    pal = a.get("palette") if a.get("palette") in T.PALETTES else ""
    fonts = a.get("fonts") if a.get("fonts") in T.FONTS else ""
    hero = a.get("hero") if a.get("hero") in T.HEROES else ""
    if not (style or pal or fonts or hero):
        return None
    st = style or "editorial_calm"
    fk = fonts or (T.STYLES[st]["fonts"] if T.STYLES[st]["fonts"] in T.FONTS else "poppins_mukta")
    radius = int(T.STYLES[st]["radius"])
    overrides: dict[str, Any] = {"radius": radius, "fonts": fk}
    dark = False
    if pal:
        p = T.PALETTES[pal]
        overrides.update({k: p[k] for k in ("bg", "surface", "ink", "primary", "accent")})
        dark = "dark" in p["moods"]
    picked = [f"feel {T.STYLES[st]['label']}" if style else "", f"colours {pal.replace('_', ' ')}" if pal else "",
              f"type {T.FONTS[fk]['head']} + {T.FONTS[fk]['body']}" if fonts else "",
              f"home page top: {T.HEROES[hero]}" if hero else ""]
    return {"source": "answers", "style": st, "fonts": fk, "head": T.FONTS[fk]["head"], "body": T.FONTS[fk]["body"],
            "radius": radius, "dark": dark, "overrides": overrides, "sections": [], "hero": hero,
            "palette_id": pal, "notes": "She chose " + "; ".join(x for x in picked if x) + ".",
            "read_by": "her answers to the design questions"}
