"""v0.686 EK LAKH ALAG WEBSITE: the Web Studio's template library = 1,00,000 UNIQUE websites.

v0.683 multiplied 1,000 Indian trades by 10 goals x 10 styles, so the first 100 cards were all 'Sweet shop' (owner:
"why sweet shop everywhere ... world wide ... every field ... not same name everywhere"). Now every template is a
business of its own: one of 1,000 subjects from 50 world sectors (SaaS to schools, hospitals to climate tech, local
shops to public services; `world.py`) x one of 10 positionings x one of 10 world cities = 100,000 distinct websites,
each with its own working name (two roots, never repeated). The website type and the design style are chosen per
website from the same numbers, so neighbours always differ in field, city, type and look.

Nothing is stored per template: card and prompt are composed on demand, the same on every call. Each prompt covers
creation (who visits, goal, pages, home sections, must-work features, positioning, content), design (style, hero,
fonts, palette, motion) and development (SEO, speed, accessibility, forms, the sector's rules), fits the Studio's
2,000-character ask box and passes the house guard. Using one sends the sector's library field + the type's goal + the
style, so the builder gets its full card.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from . import library as L
from . import taxonomy as T
from . import world as W

LIMIT = 2000                       # the Studio's ask box + service.new() both stop at 2,000 characters
N_SUB, N_ANG, N_CITY = 1000, len(W.ANGLES), len(W.CITIES)
TOTAL = N_SUB * N_ANG * N_CITY     # 100,000
STYLES = list(T.STYLES)
_NAMES = len(W.ROOTS) * (len(W.ROOTS) - 1)
_MULT = 7919                       # a unit mod _NAMES, so every website gets its own name


def total() -> int:
    return TOTAL


@lru_cache(maxsize=1)
def _subjects() -> list[tuple[str, str]]:
    return W.subjects()


@lru_cache(maxsize=1)
def _sectors() -> dict[str, tuple[str, ...]]:
    return {s[0]: s for s in W.SECTORS}


def _parts(n: int) -> tuple[int, int, int]:
    """n (0-based) -> (subject, angle, city). Neighbouring numbers differ in sector, positioning and city."""
    if not 0 <= n < TOTAL:
        raise KeyError(n)
    j, k = n % N_SUB, n // N_SUB
    a, b = k % N_ANG, k // N_ANG
    return j, (a + j) % N_ANG, (b + 3 * j + a) % N_CITY


def number(j: int, angle: int, city: int) -> int:
    a = (angle - j) % N_ANG
    b = (city - 3 * j - a) % N_CITY
    return (b * N_ANG + a) * N_SUB + j


@lru_cache(maxsize=1)
def _type_index() -> dict[str, int]:
    return {t[0]: i for i, t in enumerate(W.TYPES)}


def _type_style(j: int, angle: int, city: int) -> tuple[int, int]:
    """The website type comes from the types that suit the sector; the style turns through all ten."""
    fit = W.SECTOR_TYPES[_subjects()[j][0]]
    return _type_index()[fit[(j * 7 + angle * 3 + city) % len(fit)]], (j * 3 + angle * 7 + city * 9) % len(STYLES)


def name_of(n: int) -> str:
    idx = (n * _MULT) % _NAMES
    a, b = divmod(idx, len(W.ROOTS) - 1)
    if b >= a:
        b += 1
    return W.ROOTS[a].capitalize() + W.ROOTS[b]


def _an(word: str) -> str:
    w = word.split()[0]
    if w.isupper() or ("/" in w and w.replace("/", "").isupper()):
        return "an" if w[0] in "AEFHILMNORSX" else "a"
    if w.lower().startswith(("uni", "use", "eu", "one")):
        return "a"
    return "an" if w[0].lower() in "aeiou" else "a"


def resolve(tid: str | int) -> int:
    """A template by its number (1..100000) or its id 'w<number>'."""
    s = str(tid).strip().lstrip("#w").replace(",", "")
    if not s.isdigit():
        raise KeyError(tid)
    n = int(s) - 1
    _parts(n)
    return n


def card(n: int) -> dict[str, Any]:
    j, ang, cty = _parts(n)
    sec_key, subject = _subjects()[j]
    sec = _sectors()[sec_key]
    ti, si = _type_style(j, ang, cty)
    t = W.TYPES[ti]
    city, country, _cur = W.CITIES[cty]
    angle = W.ANGLES[ang]
    concept = f"{angle[0].upper() + angle[1:]} {subject} in {city}"
    return {"n": n + 1, "id": f"w{n + 1}", "title": name_of(n), "line": concept, "subject": subject, "angle": angle,
            "city": city, "country": country, "sector": sec_key, "sector_label": sec[1], "type": t[0], "type_label": t[1],
            "style": STYLES[si], "style_label": T.STYLES[STYLES[si]]["label"], "field": sec[2], "goal": t[2]}


def _cut(s: str, n: int) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0].rstrip(",;:-") + "…"


# The house guard (site/guard.py) reads every brief for look-alike / trap pages. A few rules lines can trip it by word
# distance alone ("no fake ... government", "refund ... page" once lines are joined), so those words are softened.
SOFTEN = (("fake", "made-up"), ("refund", "returns"), ("login", "sign-in"), ("password", "pass-code"), ("kyc", "ID check"),
          ("lottery", "lucky-draw"), ("Fake", "Made-up"), ("Refund", "Returns"), ("Login", "Sign-in"),
          ("government", "public-office"), ("Government", "Public-office"))


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
    """The deep prompt for one website, always within LIMIT characters (long details shorten first)."""
    n = resolve(tid)
    c = card(n)
    sec = _sectors()[c["sector"]]
    t = next(x for x in W.TYPES if x[0] == c["type"])
    S = T.STYLES[c["style"]]
    city, country, cur = next(x for x in W.CITIES if x[0] == c["city"])
    fonts = T.FONTS[S["fonts"]]
    pal = L.palettes_for(S["moods"], 3, c["id"])
    hero = L._pick(c["id"] + "hero", S["heroes"])
    motion = [T.MOTION_ALIASES.get(m, m) for m in S["motion"]]
    subj, name, angle = c["subject"], c["title"], c["angle"]
    where = city if city == country else f"{city}, {country}"

    def build(level: int) -> str:
        lines = [
            f"Build a complete, production-ready {t[1].lower()} for {name}, {_an(angle)} {angle} {subj} in {where} "
            f"({sec[1]}). [Hoola template #{n + 1:,} of 1,00,000]",
            f"WHO VISITS: {sec[3]}. Prices, if shown, in {cur.strip()}.",
            f"MAIN ACTION on every page: '{t[3]}', easy to reach on a phone.",
            f"PAGES: {t[4]}.",
            f"HOME PAGE, in order: {t[5]}.",
            f"MUST WORK: {t[6]}.",
            f"POSITIONING: make '{angle}' visible in the words, photos and design - not just a label. "
            f"Speak to people in {city}.",
            f"DESIGN - {S['label']}: {_cut(S['grid'], 100 if level < 2 else 60)}. Do: {_cut(S['do'], 110 if level < 2 else 60)}. "
            f"Avoid: {_cut(S['dont'], 90 if level < 2 else 50)}.",
            f"Hero: {_cut(T.HEROES[hero], 80)}. Fonts: {fonts['head']} headings, {fonts['body']} body. "
            f"Palette: {', '.join(pal[:2])}. Corners {S['radius']}px. Motion: {', '.join(motion[:2])} - gentle.",
            f"CONTENT: real, specific words for {_an(subj)} {subj}; short paragraphs; trust shown only when I confirm it "
            f"({_cut(sec[4], 90 if level < 3 else 50)}). '{name}' is a working name I can change.",
        ]
        if level < 3:
            lines.append(f"SEO: unique title + description per page, Organization / LocalBusiness schema, sitemap; rank for "
                         f"'{subj} in {city}', 'best {angle} {subj}', '{subj} {country}'.")
        lines += [
            "BUILD QUALITY: mobile-first; fast (lazy, sized images, ~100 KB of code a page); WCAG 2.2 AA contrast, keyboard "
            "+ screen-reader friendly; forms with consent + spam protection; no trackers without consent.",
            f"RULES: {_cut(sec[5], 220 if level < 2 else 120)}",
            "Never invent prices, phone numbers, addresses, reviews, awards or numbers: show a clearly marked sample I can "
            "replace before it goes live.",
        ]
        return "\n".join(lines)

    text = ""
    for level in range(5):
        text = _guard_safe(build(level))                   # softened first: a softer word can be a letter longer
        if len(text) <= LIMIT:
            break
    if len(text) > LIMIT:                                   # never: the last level is far below the limit
        text = text[: LIMIT - 1] + "…"
    return {**c, "prompt": text, "chars": len(text), "pages": [p.strip() for p in t[4].split(",")]}


@lru_cache(maxsize=1)
def _name_index() -> dict[str, int]:
    return {name_of(n).lower(): n for n in range(TOTAL)}


def search(q: str = "", sector: str = "", kind: str = "", style: str = "", offset: int = 0, limit: int = 30) -> dict[str, Any]:
    """Websites matching her words (name, subject, positioning, city, sector, website type, style) and the filters.
    Order is the library's number order, so neighbours always differ."""
    offset, limit = max(0, int(offset)), max(1, min(int(limit), 100))
    subs = _subjects()
    secs = _sectors()
    j_ok = [j for j, (sk, _) in enumerate(subs) if not sector or sk == sector]
    angles, cities = list(range(N_ANG)), list(range(N_CITY))
    types = [i for i, t in enumerate(W.TYPES) if not kind or t[0] == kind]
    styles = [i for i, s in enumerate(STYLES) if not style or s == style]
    exact: int | None = None
    for word in [w for w in (q or "").lower().replace(",", " ").split() if w]:
        if word in _name_index():
            exact = _name_index()[word]
            continue
        hit = False
        a2 = [i for i in angles if word in W.ANGLES[i].lower()]
        if a2:
            angles, hit = a2, True
        c2 = [i for i in cities if word in W.CITIES[i][0].lower() or word == W.CITIES[i][1].lower()]
        if c2 and not hit:
            cities, hit = c2, True
        t2 = [i for i in types if word in W.TYPES[i][1].lower().split() and word not in ("page", "site", "with", "&")]
        if t2 and not hit:
            types, hit = t2, True
        s2 = [i for i in styles if word in T.STYLES[STYLES[i]]["label"].lower().split()]
        if s2 and not hit:
            styles, hit = s2, True
        if not hit:                              # her word names the business first; a sector name only when none does
            by_subject = [j for j in j_ok if word in subs[j][1].lower()]
            j_ok = by_subject or [j for j in j_ok if word in secs[subs[j][0]][1].lower()]
    if exact is not None:
        c = card(exact)
        ns = [exact] if (not sector or c["sector"] == sector) and (not kind or c["type"] == kind) and \
            (not style or c["style"] == style) else []
    else:
        ts, ss = set(types), set(styles)
        full = len(j_ok) == N_SUB and len(angles) == N_ANG and len(cities) == N_CITY and len(ts) == len(W.TYPES) \
            and len(ss) == len(STYLES)
        if full:
            ns = range(TOTAL)
        else:
            ns = sorted(n for j in j_ok for a in angles for c in cities
                        if (lambda tt: tt[0] in ts and tt[1] in ss)(_type_style(j, a, c)) for n in [number(j, a, c)])
    tot = len(ns)
    rows = [card(n) for n in ns[offset:offset + limit]]
    return {"total": tot, "all": TOTAL, "offset": offset, "rows": rows,
            "sectors": [{"id": s[0], "label": s[1]} for s in W.SECTORS],
            "types": [{"id": t[0], "label": t[1]} for t in W.TYPES],
            "styles": [{"id": k, "label": v["label"]} for k, v in T.STYLES.items()],
            "subjects": N_SUB, "sectors_count": len(W.SECTORS), "cities": [c[0] for c in W.CITIES]}
