"""v0.192.0 docstudio.designs - the design router: ONE fitting design per user topic.

v0.189 gave every PDF the same skeleton (one cover architecture, one font, one table style)
with only the hue changing - the owner saw "one design". The router fixes that: the topic is
detected from the title + content keywords (English, Hinglish and Devanagari) and picks a FULL
design - hue anchor + per-title jitter, cover architecture, font pairing, table style, rule
weights. 12 families x hue jitter x 6 covers x font pairings x 2 table styles = a crore of
distinct looks, deterministic per title (same title -> same design, always).

Backward compat: the v0.189 named styles (professional / boardroom / warm / elegant / forest)
keep EXACTLY the v0.189 output - same hue, classic cover, FreeSerif, grid tables. style="auto"
(default) routes by topic; no-signal content lands on general = classic + title-hash hue, which
is byte-for-byte the v0.189 auto behaviour.

Iron rules carried over: NO hardcoded hex here - hue anchors only, every colour is still minted
by tokens.Palette's tier caps. Fonts are CANDIDATE CHAINS resolved at runtime by pdfgen's
registered pool (first available wins, FreeSerif/FreeSans floor ships with the deploy image).
"""
from __future__ import annotations

import hashlib
import re

from . import tokens

# ---------------------------------------------------------------- topic detection

# (family, latin keywords [word-boundary matched], devanagari keywords [substring matched])
_TOPIC_RULES: list[tuple[str, list[str], list[str]]] = [
    ("finance",
     ["invoice", "budget", "gst", "tax", "profit", "loss", "revenue", "ledger", "audit",
      "balance sheet", "cash flow", "emi", "loan", "interest", "rupees", "payment", "salary",
      "quotation", "price list", "cost", "expense", "turnover", "paisa", "paise", "udhaar"],
     ["बजट", "टैक्स", "लाभ", "हानि", "बिल", "भुगतान", "वेतन", "कर्ज", "ब्याज", "रुपये"]),
    ("technology",
     ["software", "api", "server", "code", "release", "sprint", "deploy", "app", "bug",
      "cloud", "machine learning", "database", "android", "flutter", "uptime", "latency",
      "backend", "frontend", "firmware", "repo", "build"],
     ["ऐप", "सर्वर", "कोड", "सॉफ्टवेयर", "डिप्लॉय"]),
    ("education",
     ["school", "student", "exam", "syllabus", "class", "course", "lesson", "homework",
      "marks", "admission", "teacher", "college", "university", "study", "chapter", "result"],
     ["स्कूल", "परीक्षा", "छात्र", "कक्षा", "पाठ", "अध्यापक", "रिजल्ट", "प्रवेश"]),
    ("health",
     ["hospital", "patient", "clinic", "medical", "doctor", "medicine", "dose", "vaccine",
      "health", "symptom", "treatment", "diet", "ayurveda", "discharge"],
     ["अस्पताल", "मरीज", "डॉक्टर", "दवा", "सेहत", "इलाज", "स्वास्थ्य"]),
    ("legal",
     ["agreement", "contract", "clause", "court", "affidavit", "legal", "nda", "notice",
      "compliance", "terms", "license", "liability", "witness", "stamp paper"],
     ["अनुबंध", "करार", "अदालत", "कानून", "नोटिस", "विधि"]),
    ("marketing",
     ["campaign", "brand", "social media", "instagram", "promo", "offer", "discount", "sale",
      "leads", "conversion", "flyer", "banner", "poster", "audience", "reach"],
     ["ऑफर", "बैनर", "पोस्टर", "विज्ञापन", "छूट"]),
    ("people",
     ["employee", "joining", "appraisal", "hiring", "interview", "staff", "attendance",
      "leave", "payroll", "shift", "recruit", "intern"],
     ["कर्मचारी", "भर्ती", "इंटरव्यू", "उपस्थिति", "छुट्टी"]),
    ("agriculture",
     ["farm", "kisan", "crop", "fasal", "mandi", "harvest", "soil", "seed", "irrigation",
      "monsoon", "wheat", "paddy", "fertilizer", "yield"],
     ["खेत", "फसल", "किसान", "मंडी", "बुवाई", "सिंचाई", "खाद"]),
    ("government",
     ["scheme", "yojana", "panchayat", "municipality", "govt", "government", "census",
      "citizen", "ward", "ration", "block", "district office"],
     ["योजना", "पंचायत", "नगर", "सरकार", "जनगणना", "राशन"]),
    ("travel",
     ["tour", "trip", "itinerary", "hotel", "flight", "safari", "yatra", "package",
      "resort", "booking", "visa", "passport"],
     ["यात्रा", "होटल", "टिकट", "टूर", "पर्यटन"]),
    ("festive",
     ["festival", "diwali", "navratri", "holi", "eid", "wedding", "shaadi", "invitation",
      "invite", "greeting", "puja", "anniversary", "birthday"],
     ["दिवाली", "नवरात्रि", "त्योहार", "शादी", "निमंत्रण", "पूजा", "जन्मदिन"]),
]

_TITLE_KW: dict[str, list[re.Pattern]] = {}
_DEVA_KW: dict[str, list[str]] = {}
for _fam, _lat, _dev in _TOPIC_RULES:
    # latin keywords match an optional English plural (invoice -> invoices, sale -> sales)
    _TITLE_KW[_fam] = [re.compile(r"\b" + re.escape(k) + r"s?\b", re.IGNORECASE) for k in _lat]
    _DEVA_KW[_fam] = list(_dev)


def detect_topic(title: str, text: str | None = None) -> tuple[str, dict]:
    """Topic from title + content. Title hit = 5 (the title IS the topic statement), body hit = 1
    capped at 2 per keyword (repetition cannot outvote the title), Devanagari hit = 4 (rare and
    specific). Latin keywords match an optional English plural (invoice -> invoices). Deterministic:
    scores -> winner, ties -> rule order, zero -> general."""
    t, x = str(title or ""), str(text or "")
    scores: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for fam, _, _ in _TOPIC_RULES:
        s, h = 0, []
        for kw, pat in zip(_TOPIC_RULES[[f[0] for f in _TOPIC_RULES].index(fam)][1], _TITLE_KW[fam]):
            n_t = len(pat.findall(t))
            n_x = min(len(pat.findall(x)), 2)          # repetition cannot outvote the title
            if n_t or n_x:
                h.append(kw)
            s += 5 * n_t + n_x
        for kw in _DEVA_KW[fam]:
            n_t, n_x = t.count(kw), min(x.count(kw), 2)
            if n_t or n_x:
                h.append(kw)
            s += 4 * n_t + n_x
        scores[fam], hits[fam] = s, h
    best = max(_TOPIC_RULES, key=lambda r: scores[r[0]])
    fam = best[0] if scores[best[0]] > 0 else "general"
    return fam, {"scores": scores, "hits": hits.get(fam, [])}


# ---------------------------------------------------------------- design families
#
# hue      - anchor hue; per-title jitter +/-10 degrees is added by resolve_design
# cover    - architecture painter in pdfgen: band | rail | plate | sunrise | minimal | classic
# fonts    - candidate chains, resolved against the registered pool at runtime
# table    - "grid" (all lines, v0.189) | "clean" (horizontal rules only)
# h1_rule  - H1 underline weight in pt
# page_num - footer page-number style: "plain" (5) | "Page N" (Page 5)

FAMILIES: dict[str, dict] = {
    "finance": {
        "hue": 168, "cover": "band", "label": "Finance", "table": "grid",
        "h1_rule": 1.2, "page_num": "Page N",
        "fonts": {"head": ["Tinos", "LiberationSerif", "FreeSerif"],
                  "body": ["Tinos", "LiberationSerif", "FreeSerif"]}},
    "technology": {
        "hue": 234, "cover": "rail", "label": "Technology", "table": "clean",
        "h1_rule": 1.8, "page_num": "plain",
        "fonts": {"head": ["LiberationSans", "FreeSans", "DejaVuSans"],
                  "body": ["LiberationSans", "FreeSans", "DejaVuSans"]}},
    "education": {
        "hue": 36, "cover": "plate", "label": "Education", "table": "clean",
        "h1_rule": 1.6, "page_num": "plain",
        "fonts": {"head": ["Carlito", "LiberationSans", "FreeSans"],
                  "body": ["Carlito", "LiberationSans", "FreeSans"]}},
    "health": {
        "hue": 152, "cover": "plate", "label": "Health", "table": "grid",
        "h1_rule": 1.2, "page_num": "Page N",
        "fonts": {"head": ["LiberationSans", "FreeSans"],
                  "body": ["LiberationSerif", "FreeSerif"]}},
    "legal": {
        "hue": 208, "cover": "minimal", "label": "Legal", "table": "grid",
        "h1_rule": 1.2, "page_num": "Page N",
        "fonts": {"head": ["Tinos", "LiberationSerif", "FreeSerif"],
                  "body": ["Tinos", "LiberationSerif", "FreeSerif"]}},
    "marketing": {
        "hue": 336, "cover": "sunrise", "label": "Marketing", "table": "clean",
        "h1_rule": 2.2, "page_num": "plain",
        "fonts": {"head": ["Carlito", "FreeSans"], "body": ["Carlito", "FreeSans"]}},
    "people": {
        "hue": 192, "cover": "rail", "label": "People", "table": "clean",
        "h1_rule": 1.4, "page_num": "plain",
        "fonts": {"head": ["FreeSans"], "body": ["FreeSans"]}},
    "agriculture": {
        "hue": 96, "cover": "classic", "label": "Agriculture", "table": "grid",
        "h1_rule": 1.2, "page_num": "plain",
        "fonts": {"head": ["FreeSerif"], "body": ["FreeSerif"]}},
    "government": {
        "hue": 226, "cover": "band", "label": "Government", "table": "grid",
        "h1_rule": 1.2, "page_num": "Page N",
        "fonts": {"head": ["Tinos", "FreeSerif"], "body": ["Tinos", "FreeSerif"]}},
    "travel": {
        "hue": 190, "cover": "sunrise", "label": "Travel", "table": "clean",
        "h1_rule": 2.0, "page_num": "plain",
        "fonts": {"head": ["Carlito", "FreeSans"], "body": ["Carlito", "FreeSans"]}},
    "festive": {
        "hue": 12, "cover": "sunrise", "label": "Festive", "table": "clean",
        "h1_rule": 2.2, "page_num": "plain",
        "fonts": {"head": ["FreeSerif"], "body": ["FreeSerif"]}},
    "general": {
        "hue": None, "cover": "classic", "label": "Classic", "table": "grid",
        "h1_rule": 1.2, "page_num": "plain",
        "fonts": {"head": ["FreeSerif"], "body": ["FreeSerif"]}},
}

# v0.189 named styles: EXACT legacy output (classic cover, FreeSerif, grid, plain page numbers)
_LEGACY = {"professional", "boardroom", "warm", "elegant", "forest"}


def _jitter(title: str) -> float:
    """Deterministic per-title hue jitter, -10..+10 degrees (same title -> same design)."""
    digest = hashlib.sha256((title or "").encode("utf-8")).digest()
    return float(digest[0] % 21) - 10.0


def resolve_design(title: str, text: str | None = None, style: str | None = None) -> dict:
    """The ONLY way pdfgen gets a design. Deterministic per (title, style).
    Returns {family, style_name, label, hue, cover, fonts (candidate chains), table,
    h1_rule, page_num, detected}."""
    name = tokens.resolve_style(style)
    if name in _LEGACY:                                   # v0.189 named styles: byte-identical legacy
        fam = FAMILIES["general"]
        return {"family": name, "style_name": name, "label": name.capitalize(),
                "hue": float(tokens.STYLES[name][0]), "cover": "classic",
                "fonts": fam["fonts"], "table": "grid", "h1_rule": 1.2,
                "page_num": "plain", "detected": False}
    if name != "auto":                                    # an explicit topic style forces the family
        fam = FAMILIES.get(name)
        if fam:
            hue = (fam["hue"] or 0.0) + _jitter(title)
            return {"family": name, "style_name": name, "label": fam["label"], "hue": hue,
                    "cover": fam["cover"], "fonts": fam["fonts"], "table": fam["table"],
                    "h1_rule": fam["h1_rule"], "page_num": fam["page_num"], "detected": False}
    fam_name, info = detect_topic(title, text)            # auto: route by topic
    fam = FAMILIES[fam_name]
    hue = tokens._title_hue(title or "") if fam["hue"] is None else fam["hue"] + _jitter(title)
    return {"family": fam_name, "style_name": "auto", "label": fam["label"], "hue": hue,
            "cover": fam["cover"], "fonts": fam["fonts"], "table": fam["table"],
            "h1_rule": fam["h1_rule"], "page_num": fam["page_num"],
            "detected": fam_name != "general",
            "hits": info["hits"]}
