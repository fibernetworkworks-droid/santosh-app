"""v0.121 The website prompt library: 1,000 field cards x 10 goals x 10 styles = 1,00,000 ready briefs, plus the design
library (300 section designs, 60 motion presets, 50 palettes, 30 font pairs, 24 hero types) and 5,000 short-ask phrases.

A few words ("mithai dukaan ki website", "क्लिनिक का पेज", "gym site chahiye booking wala") are matched to a field card
(word search with Hinglish / Devanagari / misspellings, close-spelling match, then meaning search when FastEmbed is there),
the goal is guessed from her words, and `brief()` composes the full professional brief Opus starts from.

Learning: approved sites add counts (which sections were kept, which style was chosen, which questions mattered) per
field; those counts reorder the field's sections / styles for the next owner. Only counts, never anyone's words.
"""
from __future__ import annotations

import difflib
import hashlib
import logging
import re
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import taxonomy as T

log = logging.getLogger("santosh.site")
DATA = Path(__file__).resolve().parent / "libdata"
_LOCK = threading.Lock()

FILLER = {
    "website", "websites", "site", "web", "webpage", "page", "pages", "homepage", "online", "ki", "ka", "ke", "ko", "liye",
    "banao", "banado", "bana", "do", "de", "dijiye", "chahiye", "chaiye", "chahie", "mujhe", "mera", "meri", "mere", "humara",
    "hamara", "hamari", "apna", "apni", "my", "our", "for", "a", "an", "the", "make", "create", "build", "need", "want",
    "please", "plz", "pls", "ek", "acchi", "achhi", "badhiya", "sundar", "stunning", "beautiful", "nice", "good", "new",
    "naya", "nayi", "business", "dhandha", "dhanda", "wali", "wala", "wale", "with", "and", "aur", "me", "mein", "main",
    "hai", "hain", "h", "karo", "kar", "is", "ye", "yeh", "vala", "vali", "shop", "dukaan", "dukan", "store", "centre",
    "center", "service", "services", "की", "का", "के", "लिए", "वेबसाइट", "साइट", "बनाओ", "बना", "दो", "चाहिए", "मेरी", "मेरा",
    "मेरे", "पेज", "आणि", "साठी", "माझी", "माझे", "माझा", "बनवा", "हवी", "हवे", "एक",
}
GENERIC = {"shop", "dukaan", "dukan", "store", "centre", "center", "service", "services", "wala", "wali", "classes", "class",
           "agency", "company", "studio", "clinic", "hospital", "school", "academy", "institute", "consultant", "dealer",
           "maker", "repair", "brand", "farm", "trust", "club", "point", "office", "house", "hotel"}


# ---------------------------------------------------------------- loading
# common loanwords people type in Devanagari -> the Latin word the cards use
TRANSLIT = {
    "क्लिनिक": "clinic", "जिम": "gym", "सैलून": "salon", "पार्लर": "parlour", "बेकरी": "bakery", "कैफ़े": "cafe",
    "कैफे": "cafe", "होटल": "hotel", "रेस्टोरेंट": "restaurant", "स्कूल": "school", "कोचिंग": "coaching",
    "क्लासेस": "classes", "क्लास": "classes", "डॉक्टर": "doctor", "डेंटिस्ट": "dentist", "हॉस्पिटल": "hospital",
    "मोबाइल": "mobile", "रिपेयर": "repair", "गैराज": "garage", "बुटीक": "boutique", "ट्यूशन": "tuition",
    "स्टूडियो": "studio", "फ़ोटोग्राफ़र": "photographer", "फोटोग्राफर": "photographer", "इंटरनेट": "internet",
    "ब्रॉडबैंड": "broadband", "वकील": "advocate", "सीए": "ca", "कैटरिंग": "catering", "टिफ़िन": "tiffin",
    "टिफिन": "tiffin", "योग": "yoga", "स्पा": "spa", "ट्रैवल्स": "travels", "प्रॉपर्टी": "property",
    "बिल्डर": "builder", "प्लंबर": "plumber", "इलेक्ट्रीशियन": "electrician", "एनजीओ": "ngo", "ट्रस्ट": "trust",
    "मंदिर": "mandir", "डेयरी": "dairy", "किराना": "kirana", "मेडिकल": "medical", "लैब": "lab",
}


def _norm(s: str) -> str:
    s = (s or "").lower().replace("_", " ")
    s = re.sub(r"[^\wऀ-ॿ\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=1)
def fields() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for f in sorted(DATA.glob("fields_*.txt")):
        industry = ""
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("## "):
                industry = line[3:].strip()
                continue
            if line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) != 6 or industry not in T.INDUSTRIES:
                log.warning("bad field line %s: %s", f.name, line[:80])
                continue
            fid, en, aliases, hi, mr, opts = (p.strip() for p in parts)
            o: dict[str, str] = {}
            for kv in opts.split():
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    o[k] = v
            ind = T.INDUSTRIES[industry]
            legal = list(ind["legal"])
            for flag in o.get("legal", "").split("+"):
                if flag and flag in T.LEGAL and flag not in legal:
                    legal.append(flag)
            styles = list(ind["styles"])
            if o.get("style") in T.STYLES:
                styles = [o["style"]] + [s for s in styles if s != o["style"]]
            out[fid] = {"id": fid, "en": en, "aliases": [a.strip() for a in aliases.split(",") if a.strip()],
                        "hi": hi, "mr": mr or hi, "industry": industry,
                        "goal": o.get("goal") if o.get("goal") in T.GOALS else ind["goal"],
                        "cta": o.get("cta") or ind["cta"], "legal": legal, "styles": styles}
    return out


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, dict[str, float]], list[str], dict[str, list[tuple[str, str]]]]:
    """phrase -> {field id: weight} (the card's own name 1.15, Hindi / Marathi 1.08, aliases 1.0), vocabulary, strings."""
    by_phrase: dict[str, dict[str, float]] = {}
    strings: dict[str, list[tuple[str, str]]] = {}

    def put(n: str, fid: str, w: float) -> None:
        d = by_phrase.setdefault(n, {})
        d[fid] = max(d.get(fid, 0), w)
    for fid, f in fields().items():
        cands = [(f["en"], 1.15), (fid.replace("_", " "), 1.15), (f["hi"], 1.08), (f["mr"], 1.08)] + [(a, 1.0) for a in f["aliases"]]
        ss: list[tuple[str, str]] = []
        for c, w in cands:
            n = _norm(c)
            if not n:
                continue
            ss.append((c, n))
            put(n, fid, w)
            tn = " ".join(TRANSLIT.get(x, x) for x in n.split())
            if tn != n:
                put(tn, fid, w)
            core = " ".join(x for x in n.split() if x not in FILLER)
            if core and core != n:
                put(core, fid, w * 0.95)
        strings[fid] = ss
    vocab = sorted({w for p in by_phrase for w in p.split() if len(w) >= 3})
    return by_phrase, vocab, strings


def counts() -> dict[str, int]:
    f = fields()
    return {"fields": len(f), "industries": len(T.INDUSTRIES), "goals": len(T.GOALS), "styles": len(T.STYLES),
            "briefs": len(f) * len(T.GOALS) * len(T.STYLES),
            "section_designs": sum(len(s["variants"]) for s in T.SECTIONS.values()),
            "motion_presets": len(T.MOTION_PRESETS), "palettes": len(T.PALETTES), "font_pairs": len(T.FONTS),
            "hero_types": len(T.HEROES), "phrases": len(phrases())}


# ---------------------------------------------------------------- 5,000 short-ask phrases (generated from the cards)
@lru_cache(maxsize=1)
def phrases() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for fid, f in fields().items():
        a = (f["aliases"] + [f["en"].lower()]) or [f["en"].lower()]
        a1 = a[0]
        a2 = a[1] if len(a) > 1 else f["en"].lower()
        goal = f["goal"]
        gw = T.GOALS[goal]["words"][0]
        out += [
            {"text": f"{a1} ki website", "field": fid, "goal": goal},
            {"text": f"{a2} ke liye website banao", "field": fid, "goal": goal},
            {"text": f"{f['en'].lower()} website with {gw}", "field": fid, "goal": goal},
            {"text": f"online {a1} page chahiye", "field": fid, "goal": goal},
            {"text": f"{f['hi']} की वेबसाइट", "field": fid, "goal": goal},
        ]
    return out


# ---------------------------------------------------------------- matching her words
def _tokens(text: str) -> list[str]:
    return [TRANSLIT.get(w, w) for w in _norm(text).split() if w]


def guess_goal(text: str, default: str = "") -> str:
    t = " " + _norm(text) + " "
    best, score = "", 0
    for gid, g in T.GOALS.items():
        s = sum(1 for w in g["words"] if f" {_norm(w)} " in t)
        if s > score:
            best, score = gid, s
    return best or default


def match(text: str, top: int = 5) -> list[dict[str, Any]]:
    """Her words -> best field cards [{id, en, hi, industry, score, why}] (score 0..1)."""
    by_phrase, vocab, strings = _index()
    toks = _tokens(text)
    if not toks:
        return []
    scores: dict[str, float] = {}
    why: dict[str, str] = {}

    def add(fid: str, s: float, w: str) -> None:
        if s > scores.get(fid, 0):
            scores[fid], why[fid] = s, w

    # 1. exact phrases (longest first): n-grams of her words, as typed and with Devanagari loanwords in Latin
    raw = [w for w in _norm(text).split() if w]
    for seq in ([raw, toks] if raw != toks else [toks]):
        n = len(seq)
        for size in range(min(5, n), 0, -1):
            for i in range(n - size + 1):
                gram = " ".join(seq[i:i + size])
                if size == 1 and (gram in FILLER or len(gram) < 2):
                    continue
                ids = by_phrase.get(gram)
                if ids:
                    generic = size == 1 and gram in GENERIC
                    base = (0.55 + 0.12 * size) * (0.45 if generic else 1.0) / (1 + 0.15 * (len(ids) - 1))
                    for fid, w in ids.items():
                        add(fid, min(1.0, base * w), f"'{gram}'")
    # 2. close spelling of single words (mithaai, resturant, jimm)
    if not scores or max(scores.values()) < 0.6:
        goal_words = {x for g in T.GOALS.values() for x in g["words"]}
        for w in toks:
            if w in FILLER or len(w) < 4 or w in goal_words or w in GENERIC:
                continue
            for close in difflib.get_close_matches(w, vocab, n=4, cutoff=0.8):
                for phrase, ids in by_phrase.items():
                    if close in phrase.split():
                        for fid in ids:
                            add(fid, 0.5 * difflib.SequenceMatcher(None, w, close).ratio()
                                * (0.5 if close in GENERIC else 1.0) / (1 + 0.1 * (len(ids) - 1)),
                                f"'{w}' ~ '{close}'")
    # 3. meaning (FastEmbed) when words were not enough
    if not scores or max(scores.values()) < 0.5:
        try:
            from .. import semantic
            if semantic.available():
                items = [(fid, f"{f['en']}: {', '.join(f['aliases'][:6])}") for fid, f in fields().items()]
                for fid, _t, sc in semantic.rank(text, items, top=top, floor=0.45):
                    add(fid, 0.4 + 0.4 * sc, "meaning")
        except Exception:
            log.debug("semantic match skipped", exc_info=True)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:top]
    F = fields()
    return [{"id": fid, "en": F[fid]["en"], "hi": F[fid]["hi"], "industry": F[fid]["industry"],
             "industry_label": T.INDUSTRIES[F[fid]["industry"]]["label"], "score": round(s, 3), "why": why[fid]}
            for fid, s in ranked]


def understand(text: str) -> dict[str, Any]:
    """Her short ask -> {field, goal, styles (3 for the looks), alternatives, ask (one question when two fields are close)}."""
    m = match(text)
    if not m:
        return {"field": "", "goal": guess_goal(text, "enquiry"), "styles": ["editorial_calm", "bold_modern", "warm_local"],
                "alternatives": [], "ask": "Aapka kaam / dukaan kis cheez ka hai? (jaise: mithai shop, clinic, coaching)"}
    best = m[0]
    f = fields()[best["id"]]
    goal = guess_goal(text, f["goal"])
    styles = _styles_for(best["id"], goal)
    ask = ""
    if len(m) > 1 and m[1]["score"] >= best["score"] * 0.92 and m[1]["industry"] != best["industry"]:
        ask = f"{best['en']} ya {m[1]['en']}?"
    return {"field": best["id"], "field_label": f["en"], "industry": f["industry"], "goal": goal, "styles": styles,
            "score": best["score"], "alternatives": m[1:4], "ask": ask}


# ---------------------------------------------------------------- learning (counts only)
def _stats(field: str) -> dict[str, Any]:
    try:
        from .models import SiteLibStat
        from ..db import session
        from sqlalchemy import select
        with session() as s:
            rows = s.scalars(select(SiteLibStat).where(SiteLibStat.field == field)).all()
            out: dict[str, Any] = {"style": {}, "section": {}, "question": {}, "goal": {}}
            for r in rows:
                out.setdefault(r.kind, {})[r.key] = r.count
            return out
    except Exception:
        return {"style": {}, "section": {}, "question": {}, "goal": {}}


def learn(field: str, kind: str, keys: list[str], weight: int = 1) -> None:
    """kind = style | section | question | goal. Counts only."""
    if not field or kind not in ("style", "section", "question", "goal"):
        return
    from sqlalchemy import select
    from ..db import session
    from .models import SiteLibStat
    with _LOCK, session() as s:
        for k in {str(x)[:60] for x in keys if x}:
            r = s.scalars(select(SiteLibStat).where(SiteLibStat.field == field, SiteLibStat.kind == kind,
                                                    SiteLibStat.key == k)).first()
            if r is None:
                s.add(SiteLibStat(field=field, kind=kind, key=k, count=weight))
            else:
                r.count = (r.count or 0) + weight


def _styles_for(field: str, goal: str = "") -> list[str]:
    f = fields().get(field)
    base = list(f["styles"]) if f else ["editorial_calm", "bold_modern", "warm_local"]
    learned = _stats(field).get("style", {}) if f else {}
    for st in sorted(learned, key=lambda k: -learned[k]):
        if st in T.STYLES and st not in base[:1]:
            base = [base[0], st] + [x for x in base[1:] if x != st]
            break
    pool = base + [s for s in T.STYLES if s not in base]
    out: list[str] = []
    for s in pool:
        if s not in out:
            out.append(s)
        if len(out) == 3:
            break
    return out


# ---------------------------------------------------------------- the 1,00,000 briefs
def _pick(seed: str, items: list[Any]) -> Any:
    h = int(hashlib.sha1(seed.encode()).hexdigest()[:8], 16)
    return items[h % len(items)]


def palettes_for(moods: list[str], n: int = 3, seed: str = "") -> list[str]:
    want = set(moods)
    ranked = sorted(T.PALETTES, key=lambda p: (-len(want & set(T.PALETTES[p]["moods"])),
                                               hashlib.sha1((seed + p).encode()).hexdigest()))
    return ranked[:n]


def brief_id(field: str, goal: str, style: str) -> str:
    return f"{field}.{goal}.{style}"


def brief(field: str, goal: str = "", style: str = "") -> dict[str, Any]:
    F = fields()
    if field not in F:
        raise KeyError(field)
    f = F[field]
    ind = T.INDUSTRIES[f["industry"]]
    goal = goal if goal in T.GOALS else f["goal"]
    style = style if style in T.STYLES else f["styles"][0]
    g, st = T.GOALS[goal], T.STYLES[style]
    seed = brief_id(field, goal, style)
    learned = _stats(field)

    pages = ["home"]
    for p in ind["pages"] + g["pages"]:
        if p in T.PAGES and p not in pages:
            pages.append(p)
    pages = pages[:7]
    if goal in ("catalogue", "menu_order") and "refund" not in pages:
        pages.append("refund")
    if any(x in f["legal"] for x in ("bci", "sebi")) and "disclaimer" not in pages:
        pages.append("disclaimer")
    pages.append("privacy")

    secs: list[str] = ["hero"]
    for sct in ind["sections"] + g["sections"]:
        if sct in T.SECTIONS and sct not in secs and sct != "whatsapp_float":
            secs.append(sct)
    ls = learned.get("section", {})
    if ls:
        head, rest = secs[:1], secs[1:]
        rest.sort(key=lambda x: -ls.get(x, 0))
        secs = head + rest
    secs = secs[:8]
    if f["cta"] in ("whatsapp", "order", "call") or g["cta"] in ("whatsapp", "call"):
        secs.append("whatsapp_float")
    designs = {sct: _pick(seed + sct, T.SECTIONS[sct]["variants"]) for sct in secs}
    hero = _pick(seed + "hero", st["heroes"])
    pal = palettes_for(st["moods"] + ind["moods"], 3, seed)
    fonts = T.FONTS[st["fonts"]]
    motion = [T.MOTION_ALIASES.get(m, m) for m in st["motion"]]
    questions = list(ind["questions"])
    lq = learned.get("question", {})
    if lq:
        questions.sort(key=lambda q: -lq.get(q, 0))
    questions = questions[:5]
    cta = f["cta"] if goal == f["goal"] else g["cta"]
    a1 = (f["aliases"] or [f["en"].lower()])[0]
    searches = [f"{a1} near me", f"best {f['en'].lower()} in [city]", f"{f['hi']} [city]"]
    legal = [T.LEGAL[x] for x in f["legal"]]
    text = "\n".join([
        f"WEBSITE BRIEF {seed}",
        f"Business type: {f['en']} ({f['hi']}); industry: {ind['label']}. People also call it: {', '.join(f['aliases'][:6])}.",
        f"Goal: {g['label']} - {g['brief']}",
        f"Main action everywhere: {cta}.",
        f"Design style: {st['label']} - grid: {st['grid']}; do: {st['do']}; don't: {st['dont']}; corner radius {st['radius']}px.",
        f"Hero: {T.HEROES[hero]}.",
        f"Fonts: headings {fonts['head']}, body {fonts['body']}, Devanagari {fonts['deva']}.",
        f"Palette candidates: {', '.join(pal)}.",
        f"Motion: {', '.join(motion)} (transform / opacity only, reduced-motion safe).",
        "Pages: " + ", ".join(f"{p} ({T.PAGES[p]['why']})" for p in pages),
        "Home sections: " + "; ".join(f"{T.SECTIONS[s]['label']}: {designs[s]}" for s in secs),
        f"Trust signals to use (only the ones she confirms): {', '.join(ind['trust'])}.",
        f"Photos to ask for: {', '.join(ind['photos'])}.",
        f"What customers search: {'; '.join(searches)}.",
        "Rules: " + (" ".join(legal) if legal else "general ASCI / CCPA truth-in-advertising."),
        "Never invent prices, phone numbers, addresses, years, counts, awards or reviews: leave [blank].",
    ])
    return {"id": seed, "field": field, "field_label": f["en"], "field_hi": f["hi"], "industry": f["industry"],
            "industry_label": ind["label"], "goal": goal, "goal_label": g["label"], "style": style,
            "style_label": st["label"], "cta": cta, "pages": pages, "sections": secs, "designs": designs, "hero": hero,
            "palettes": pal, "fonts": st["fonts"], "font_names": fonts, "motion": motion, "radius": st["radius"],
            "trust": ind["trust"], "photos": ind["photos"], "questions": questions, "legal": f["legal"],
            "legal_text": legal, "searches": searches, "text": text}


def browse(industry: str = "", q: str = "", limit: int = 60, offset: int = 0) -> dict[str, Any]:
    F = fields()
    if q:
        ids = [m["id"] for m in match(q, top=limit)]
    else:
        ids = [fid for fid, f in F.items() if not industry or f["industry"] == industry]
    total = len(ids)
    ids = ids[offset:offset + limit]
    inds = [{"id": k, "label": v["label"], "fields": sum(1 for f in F.values() if f["industry"] == k)}
            for k, v in T.INDUSTRIES.items()]
    return {"industries": inds, "total": total,
            "fields": [{"id": fid, "en": F[fid]["en"], "hi": F[fid]["hi"], "industry": F[fid]["industry"],
                        "goal": F[fid]["goal"], "styles": F[fid]["styles"][:3]} for fid in ids],
            "goals": [{"id": k, "label": v["label"]} for k, v in T.GOALS.items()],
            "styles": [{"id": k, "label": v["label"]} for k, v in T.STYLES.items()], "counts": counts()}
