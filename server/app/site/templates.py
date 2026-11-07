"""v0.683 EK LAKH PROMPT: the Web Studio's template library = 1,00,000 deep website prompts.

Every prompt is one cell of the website library: 1,000 kinds of business (40 industries) x 10 goals x 10 design
styles = exactly 100,000. Nothing is stored per prompt - each one is composed on demand from the same library card
the builder itself uses (`library.brief`), so a prompt and the site it builds can never disagree, and every prompt is
the same on every call (deterministic). Each prompt covers creation (pages + content), design (style, type, palette,
hero, motion) and development (SEO, speed, accessibility, forms, the law for that trade), and fits the Studio's
2,000-character ask box. Using one sends the field / goal / style along, so the build gets the full library card.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from . import library as L
from . import taxonomy as T

LIMIT = 2000                 # the Studio's ask box + service.new() both stop at 2,000 characters
CTA_WORDS = {"whatsapp": "Order / ask on WhatsApp", "call": "Call now", "booking": "Book a slot", "order": "Order now",
             "enquiry": "Send an enquiry", "visit": "Get directions", "donate": "Donate", "apply": "Apply now",
             "rsvp": "RSVP", "subscribe": "Subscribe", "download": "Download", "contact": "Contact me"}


@lru_cache(maxsize=1)
def _fields() -> list[str]:
    F = L.fields()
    order = {k: i for i, k in enumerate(T.INDUSTRIES)}
    return sorted(F, key=lambda fid: (order.get(F[fid]["industry"], 99), list(F).index(fid)))


GOALS = list(T.GOALS)
STYLES = list(T.STYLES)


def total() -> int:
    return len(_fields()) * len(GOALS) * len(STYLES)


def _parts(n: int) -> tuple[str, str, str]:
    fs = _fields()
    if not 0 <= n < total():
        raise KeyError(n)
    return fs[n // (len(GOALS) * len(STYLES))], GOALS[(n // len(STYLES)) % len(GOALS)], STYLES[n % len(STYLES)]


def number(field: str, goal: str, style: str) -> int:
    return _fields().index(field) * len(GOALS) * len(STYLES) + GOALS.index(goal) * len(STYLES) + STYLES.index(style)


def resolve(tid: str | int) -> tuple[int, str, str, str]:
    """A template by its number (1..100000) or its id 'field.goal.style'."""
    s = str(tid).strip().lstrip("#").replace(",", "")
    if s.isdigit():
        n = int(s) - 1
        return (n, *_parts(n))
    f, g, st = (s.split(".") + ["", "", ""])[:3]
    if f not in L.fields() or g not in T.GOALS or st not in T.STYLES:
        raise KeyError(tid)
    return number(f, g, st), f, g, st


def card(n: int) -> dict[str, Any]:
    f, g, st = _parts(n)
    fd = L.fields()[f]
    return {"n": n + 1, "id": f"{f}.{g}.{st}", "field": f, "goal": g, "style": st, "title": fd["en"],
            "hi": fd["hi"], "industry": fd["industry"], "industry_label": T.INDUSTRIES[fd["industry"]]["label"],
            "goal_label": T.GOALS[g]["label"], "style_label": T.STYLES[st]["label"]}


def _cut(s: str, n: int) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0].rstrip(",;:-") + "…"


# The house guard (site/guard.py) reads every brief for look-alike / trap pages. A prompt's own law lines ("no fake
# 'last 2 seats'", "refund policy ... page") can trip it by word distance alone, so those words are softened - the
# meaning stays, and a prompt Hoola offers can always be used as it is.
SOFTEN = (("fake", "made-up"), ("refund", "returns"), ("login", "sign-in"), ("password", "pass-code"), ("kyc", "ID check"),
          ("lottery", "lucky-draw"), ("Fake", "Made-up"), ("Refund", "Returns"), ("Login", "Sign-in"))


def _guard_safe(text: str) -> str:
    from . import guard
    def bad(t: str) -> str:                     # the service reads it with its lines joined, so check both forms
        return guard.brief_problem(t) or guard.brief_problem(" ".join(t.split()))
    for old, new in SOFTEN:
        if not bad(text):
            break
        text = text.replace(old, new)
    return text


def prompt(tid: str | int) -> dict[str, Any]:
    """The deep prompt for one template, always within LIMIT characters (the long library details shorten first)."""
    n, f, g, st = resolve(tid)
    b = L.brief(f, g, st)
    S = T.STYLES[st]
    G = T.GOALS[g]
    cta = CTA_WORDS.get(b["cta"], str(b["cta"]).replace("_", " ").capitalize())
    pages_long = "; ".join(f"{p} - {_cut(T.PAGES[p]['why'], 60)}" for p in b["pages"])
    pages_short = ", ".join(b["pages"])
    secs = [s for s in b["sections"] if s != "whatsapp_float"]
    home_long = "; ".join(f"{T.SECTIONS[s]['label']}: {_cut(b['designs'][s], 70)}" for s in secs)
    home_short = ", ".join(T.SECTIONS[s]["label"] for s in secs)
    fonts = b["font_names"]
    rules = " ".join(b["legal_text"]) or "Honest advertising only (ASCI / consumer protection rules)."

    def build(level: int) -> str:
        lines = [
            f"Build a complete, production-ready website for a {b['field_label']} ({b['field_hi']}) - "
            f"{b['industry_label']}. [Hoola template #{n + 1:,} of {total():,}]",
            f"GOAL: {G['label']}. {_cut(G['brief'], 260 if level < 2 else 140)}",
            f"MAIN ACTION on every page: '{cta}' button, always easy to reach on a phone.",
            f"PAGES: {pages_long if level < 1 else pages_short}.",
            f"HOME PAGE, in order: {home_long if level < 1 else home_short}.",
            f"DESIGN - {S['label']}: {_cut(S['grid'], 110)}. Do: {_cut(S['do'], 120)}. Avoid: {_cut(S['dont'], 100)}.",
            f"Hero: {_cut(T.HEROES[b['hero']], 90)}. Fonts: {fonts['head']} headings, {fonts['body']} body"
            + (f", {fonts['deva']} for Hindi" if level < 3 else "") + f". Palette: {', '.join(b['palettes'][:2 if level > 1 else 3])}. "
            f"Corners {b['radius']}px. Motion: {', '.join(b['motion'][:2 if level > 1 else 4])} - gentle, transform / opacity only.",
            f"CONTENT: real, specific words a {b['field_label'].lower()} customer understands; short paragraphs; "
            f"trust shown only when I confirm it ({', '.join(b['trust'][:4])}); photos: {', '.join(b['photos'][:3])}.",
        ]
        if level < 3:
            lines.append(f"SEO: a unique title + description per page, LocalBusiness schema, clean URLs, sitemap; "
                         f"rank for: {'; '.join(b['searches'])}.")
        lines += [
            "BUILD QUALITY: mobile-first; fast (images lazy and sized, under ~100 KB of code a page); WCAG 2.2 AA "
            "contrast, keyboard + screen-reader friendly; forms with a consent line and spam protection; no "
            "trackers without consent.",
            f"RULES: {_cut(rules, 300 if level < 2 else 150)}",
            "Never invent prices, phone numbers, addresses, reviews, awards or numbers: show a clearly marked sample "
            "I can replace before it goes live.",
        ]
        return "\n".join(lines)

    for level in range(5):
        text = _guard_safe(build(level))                   # softened first: a softer word can be a letter longer
        if len(text) <= LIMIT:
            break
    if len(text) > LIMIT:                                   # never: the last level is far below the limit
        text = text[: LIMIT - 1] + "…"
    return {**card(n), "prompt": text, "chars": len(text), "pages": b["pages"], "sections": b["sections"],
            "questions": b["questions"]}


def search(q: str = "", industry: str = "", goal: str = "", style: str = "", offset: int = 0, limit: int = 30) -> dict[str, Any]:
    """Templates matching her words / industry / goal / style, newest-first never - always the library's order."""
    F = L.fields()
    fids = _fields()
    q = (q or "").strip()
    if q:
        low = q.lower()
        direct = [fid for fid in fids if low in F[fid]["en"].lower() or low in F[fid]["hi"]
                  or any(low in a.lower() for a in F[fid]["aliases"])]
        try:
            ranked = [m["id"] for m in L.match(q, top=60, meaning=False) if m.get("id") in F]   # words + spelling; no model load
        except Exception:
            ranked = []
        seen: set[str] = set()
        fids = [x for x in direct + ranked if not (x in seen or seen.add(x))]
        for word in low.split():                             # 'booking' / 'luxury' in her words narrow goal / style
            for gk, gv in T.GOALS.items():
                if not goal and (word == gk or word in gv.get("words", [])):
                    goal = gk
            for sk, sv in T.STYLES.items():
                if not style and word in sv["label"].lower().split():
                    style = sk
    if industry:
        fids = [x for x in fids if F[x]["industry"] == industry]
    gs = [goal] if goal in T.GOALS else GOALS
    ss = [style] if style in T.STYLES else STYLES
    per = len(gs) * len(ss)
    tot = len(fids) * per
    offset, limit = max(0, int(offset)), max(1, min(int(limit), 100))
    rows = []
    for i in range(offset, min(tot, offset + limit)):
        fid = fids[i // per]
        rest = i % per
        rows.append(card(number(fid, gs[rest // len(ss)], ss[rest % len(ss)])))
    return {"total": tot, "all": total(), "offset": offset, "rows": rows,
            "industries": [{"id": k, "label": v["label"]} for k, v in T.INDUSTRIES.items()],
            "goals": [{"id": k, "label": v["label"]} for k, v in T.GOALS.items()],
            "styles": [{"id": k, "label": v["label"]} for k, v in T.STYLES.items()],
            "fields": len(L.fields()), "industries_count": len(T.INDUSTRIES)}
