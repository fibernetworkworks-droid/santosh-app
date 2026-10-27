"""Kitab Sahayak rules: pure functions (no DB). Chapters, word counts, proof / copy checks by code (English, Hindi, Marathi),
spelling-consistency queries, quotes that may need permission, similarity against her sources, ISBN check digits, public
domain in India, royalty slabs from HER contract, platform maths from HER numbers, legal deposit date, sources."""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import unicodedata
from datetime import date, timedelta
from typing import Any

PASSES = ("developmental", "line", "copy", "proof")
PASS_LABEL = {"developmental": "Developmental (kahani / dhaancha)", "line": "Line edit (vakya, lay)",
              "copy": "Copy edit (grammar, consistency)", "proof": "Proofread (typo, spacing)"}
KINDS = ("fiction", "nonfiction", "poetry", "academic", "children", "translation")
FORMATS = ("paperback", "hardback", "ebook", "audiobook")
STATUS = ("drafting", "editing", "submission", "production", "published", "done")
LANG_LABEL = {"hi": "Hindi", "mr": "Marathi", "en": "English"}

DEV = re.compile(r"[ऀ-ॿ]")
NUKTA, CHANDRA, ANUSVARA = "़", "ँ", "ं"

# Starter royalty norms (NOT rules: her contract decides). Shown so she can compare an offer.
ROYALTY_NORMS = ("Trade publishers in India often offer about 7.5-10% of MRP on print (sometimes slabs that rise with copies "
                 "sold) and 15-25% of net receipts on e-books; these are market notes, not law. Your contract decides.")

# KDP (kdp.amazon.com help G200634560, read 23 Oct 2026): Amazon.in eBook 70% only for list price Rs 99-599 and, for sales to
# customers in India, only when enrolled in KDP Select (90-day Amazon-only e-book exclusivity); 35% Rs 49-10,999 (by file size).
KDP = {"in_70_min": 99, "in_70_max": 599, "in_35_min": 49, "in_35_max": 10999,
       "note": ("KDP Amazon.in: 70% sirf Rs 99-599 list price par aur India ki bikri ke liye KDP Select (90 din sirf Amazon par "
                "e-book) zaroori; warna 35%. 70% mein delivery cost katti hai. AI se bana text / cover / anuvaad ho to KDP par "
                "batana padta hai. Shartein badalti hain: KDP help page dekh kar pakka kijiye.")}

SOURCES = [
    ("ISBN free from RRRNA (Raja Rammohun Roy National Agency, Ministry of Education) at isbn.gov.in; separate ISBN per format",
     "https://www.agileregulatory.com/blogs/how-to-apply-for-issn-isbn-in-india", "2026-08-27"),
    ("Copyright registration of a literary work: Rs 500 government fee per work (Form XIV, copyright.gov.in), 30-day objection "
     "window after the diary number", "https://qwikfilings.com/?p=375818", "2024-25 fee table (read 2026-10-23)"),
    ("Delivery of Books and Newspapers (Public Libraries) Act 1954 s.3: one copy each to the National Library Kolkata and three "
     "public libraries within 30 days of publication", "https://spicyip.com/2026/07/the-forgotten-half-of-the-copyright-bargain-legal-deposit-part-2.html",
     "2026-07-02"),
    ("KDP Amazon.in 70% band Rs 99-599 + KDP Select for India sales; 35% Rs 49-10,999", "https://kdp.amazon.com/en_US/help/topic/G200634560",
     "read 2026-10-23"),
    ("Self-publishing in India 2026: Notion Press 50-75% on direct sales, Pothi ~50%, packages vary", "https://kdpindia.com/self-publishing-platforms-compared/",
     "2026"),
    ("GST on printed books 0% (HSN 4901), children's picture books 0% (4903), notebooks 18% after GST 2.0 (22 Sep 2025)",
     "https://disytax.com/?p=24574", "2026-09-07"),
    ("Author royalty to a publisher: reverse charge (publisher pays) under Notification 13/2017-CT(R); 18% under heading 9973 "
     "(SAC 997334) per one reading, not changed by GST 2.0", "https://www.caclubindia.com/articles/12-or-18-the-gst-royalty-dilemma-54943.asp",
     "2026-03-23"),
    ("TDS s.393(1) Income-tax Act 2025 (old 194J): professional fees 10%, Rs 50,000 a year", "https://studycafe.in/tds-rate-chart-for-fy-2026-2027-under-income-tax-act-2025-420727.html",
     "2026-05-14"),
    ("Copyright Act 1957: s.17 first owner, s.18-19 assignment in writing (s.19(5): 5 years if not stated, s.19(6): India if "
     "not stated), s.22 life + 60 years, s.52(1)(a) fair dealing for criticism / review with acknowledgement, s.57 moral rights",
     "https://en.wikipedia.org/wiki/Copyright_law_of_India", "read 2026-10-23"),
]


def digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def text_hash(t: str) -> str:
    return hashlib.sha256((t or "").encode()).hexdigest()[:24]


def clean(s: Any, n: int = 400) -> str:
    """Her / outside text kept as data; OTP / PIN values and card-like numbers removed."""
    t = str(s or "")
    t = re.sub(r"(?i)\b(otp|pin|cvv|password|passcode)\b\s*[:=]?\s*\S+", r"\1 [hataya]", t)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    return t.strip()[:n]


# ---------------------------------------------------------------- language, words, chapters
def lang_of(text: str, default: str = "en") -> str:
    t = text or ""
    dev = len(DEV.findall(t))
    lat = len(re.findall(r"[A-Za-z]", t))
    if dev < max(20, lat * 0.5):
        return "en" if lat else default
    mr = len(re.findall(r"(?:आहे|नाही|आणि|होते|झाले|म्हणून|त्याच्या|तिच्या|आम्ही|मला|तुम्ही)", t))
    hi = len(re.findall(r"(?:\sहै|नहीं|और|था|थी|के\s|में|हूँ|हैं|उसने|मुझे)", t))
    return "mr" if mr > hi else "hi"


def words(text: str) -> int:
    return len([w for w in re.findall(r"\S+", text or "") if re.search(r"[\wऀ-ॿ]", w)])


_HEAD = re.compile(r"^\s{0,3}(?:#{1,3}\s+.+|(?:chapter|ch\.|part|prologue|epilogue|अध्याय|प्रकरण|भाग|पाठ|प्रस्तावना|उपसंहार)"
                   r"(?:\s+[\wऀ-ॿ.\-:]+){0,10})\s*$", re.I)


def split_chapters(text: str) -> list[tuple[str, str]]:
    """Headings (Chapter 3, अध्याय ५, प्रकरण, '# Title') start chapters; no headings = one chapter."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    out: list[tuple[str, list[str]]] = []
    cur_t, cur = "", []
    for ln in lines:
        if _HEAD.match(ln) and len(ln.strip()) <= 120:
            if cur_t or any(x.strip() for x in cur):
                out.append((cur_t, cur))
            cur_t, cur = ln.strip().lstrip("#").strip(), []
        else:
            cur.append(ln)
    if cur_t or any(x.strip() for x in cur):
        out.append((cur_t, cur))
    res = []
    for i, (t, body) in enumerate(out):
        b = "\n".join(body).strip("\n")
        if not t and not b.strip():
            continue
        res.append((t or f"Chapter {i + 1}", b))
    return res


def readability(text: str) -> dict[str, Any]:
    t = text or ""
    sents = [s for s in re.split(r"(?<=[.!?।])\s+", t) if words(s)]
    paras = [p for p in re.split(r"\n\s*\n", t) if p.strip()]
    lens = [words(s) for s in sents]
    dialogue = len(re.findall(r"[\"“”]", t)) // 2
    return {"words": words(t), "sentences": len(sents), "paragraphs": len(paras),
            "avg_sentence": round(sum(lens) / len(lens), 1) if lens else 0,
            "long_sentences": sum(1 for n in lens if n > 35), "dialogue_lines": dialogue,
            "long_paragraphs": sum(1 for p in paras if words(p) > 250)}


# ---------------------------------------------------------------- proof / copy checks by code
def _ctx(text: str, at: int, n: int = 24) -> str:
    return text[max(0, at - n):at]


def _sug(text: str, at: int, src: str, dst: str | None, kind: str, why: str, pass_: str = "proof") -> dict[str, Any]:
    return {"at": at, "src": src, "dst": dst, "kind": kind, "why": why, "pass": pass_, "ctx": _ctx(text, at)}


def code_checks(text: str, lang: str, style: dict | None = None) -> list[dict[str, Any]]:
    """Mechanical issues only (never style or meaning). Each = exact span in HER text + a replacement she may accept."""
    st = style or {}
    ignore = {(a, b) for a, b in (tuple(x) for x in st.get("ignore", []) if isinstance(x, (list, tuple)) and len(x) == 2)}
    conv = st.get("conventions") or {}
    out: list[dict[str, Any]] = []
    t = text or ""
    for m in re.finditer(r"(?<![\wऀ-ॿ])([\wऀ-ॿ]+)(\s+)\1(?![\wऀ-ॿ])", t, re.I):
        w = m.group(1)
        if w.isdigit() or w.lower() in ("ha", "na", "bye", "very", "so", "no", "jaldi", "dheere"):
            continue
        if DEV.search(w) and w in ("धीरे", "जल्दी", "बार", "कभी", "हाँ", "ना", "चल", "हळू", "पटकन"):
            continue
        out.append(_sug(t, m.start(), m.group(0), w, "repeat", f"'{w}' do baar likha gaya"))
    for m in re.finditer(r"(?<=\S)( {2,})(?=\S)", t):
        out.append(_sug(t, m.start(), m.group(0), " ", "spacing", "do space"))
    for m in re.finditer(r"(?<=[\wऀ-ॿ])( +)([,;:!?।])", t):
        out.append(_sug(t, m.start(), m.group(0), m.group(2), "spacing", "chinh se pehle space nahi"))
    if lang == "en":
        for m in re.finditer(r"(?<=[a-z])([,;])(?=[A-Za-z])", t):
            out.append(_sug(t, m.start(), m.group(1), m.group(1) + " ", "spacing", "comma ke baad space"))
        for m in re.finditer(r"(?<=[a-z]{2})\.(?=[A-Z][a-z])", t):
            out.append(_sug(t, m.start(), ".", ". ", "spacing", "full stop ke baad space"))
        for m in re.finditer(r"(?:^|(?<=[.!?]\s))([a-z])(?=[a-z]+\b)", t):
            if m.start() == 0 and t[:1].islower():
                out.append(_sug(t, m.start(), m.group(1), m.group(1).upper(), "capital", "vakya bade akshar se"))
            elif m.start() > 0:
                out.append(_sug(t, m.start(), m.group(1), m.group(1).upper(), "capital", "vakya bade akshar se"))
    if lang in ("hi", "mr"):
        stop = conv.get("full_stop") or ("danda" if lang == "hi" else "period")
        if stop == "danda":
            for m in re.finditer(r"(?<=[ऀ-ॿ])\.(?=\s|$)", t):
                out.append(_sug(t, m.start(), ".", "।", "punctuation", "Hindi mein purn viram (।) aapki style sheet ke hisaab se"))
        else:
            for m in re.finditer(r"(?<=[ऀ-ॿ])।(?=\s|$)", t):
                out.append(_sug(t, m.start(), "।", ".", "punctuation", "aapki style sheet: purn viram ke liye '.'"))
        for m in re.finditer(r"([ा-ौॢॣ])\1", t):
            out.append(_sug(t, m.start(), m.group(0), m.group(1), "unicode", "matra do baar lagi"))
        for m in re.finditer(r"[​‌‍﻿](?![्])", t):
            if m.group(0) in "‌‍" and m.start() > 0 and t[m.start() - 1] == "्":
                continue
            out.append(_sug(t, m.start(), m.group(0), "", "unicode", "chhupa hua (zero-width) nishaan"))
    q = conv.get("quotes")
    if q == "curly":
        for m in re.finditer(r'"([^"\n]{1,300})"', t):
            out.append(_sug(t, m.start(), m.group(0), "“" + m.group(1) + "”", "punctuation", "style sheet: curly quotes"))
    elif q == "straight":
        for m in re.finditer(r"“([^”\n]{1,300})”", t):
            out.append(_sug(t, m.start(), m.group(0), '"' + m.group(1) + '"', "punctuation", "style sheet: straight quotes"))
    for wrong, right in (st.get("spellings") or {}).items():
        if not wrong or wrong == right:
            continue
        for m in re.finditer(r"(?<![\wऀ-ॿ])" + re.escape(wrong) + r"(?![\wऀ-ॿ])", t):
            out.append(_sug(t, m.start(), wrong, right, "consistency", f"style sheet: '{right}' likhna tay hai", "copy"))
    seen, res = set(), []
    for s in sorted(out, key=lambda x: x["at"]):
        k = (s["at"], s["src"])
        if k in seen or (s["src"], s["dst"]) in ignore:
            continue
        seen.add(k)
        res.append(s)
    return res


_UKUS = [("colour", "color"), ("favourite", "favorite"), ("honour", "honor"), ("organise", "organize"), ("realise", "realize"),
         ("centre", "center"), ("theatre", "theater"), ("travelled", "traveled"), ("grey", "gray"), ("programme", "program"),
         ("analyse", "analyze"), ("defence", "defense"), ("neighbour", "neighbor"), ("labour", "labor"), ("jewellery", "jewelry")]


_STOP = {"The", "Then", "And", "But", "When", "What", "Where", "Who", "Why", "How", "This", "That", "There", "They", "She", "Her",
         "His", "Him", "Its", "One", "Our", "Your", "Yes", "Not", "Chapter", "Part", "Woh", "Yeh", "Aur", "Par", "Lekin", "Jab", "Phir"}


def _deva_key(w: str) -> str:
    return w.replace(NUKTA, "").replace(CHANDRA, ANUSVARA)


def variants(text: str, style: dict | None = None) -> list[dict[str, Any]]:
    """Consistency QUERIES (no change by themselves): the same word / name in two spellings. She picks one -> style sheet."""
    st = style or {}
    decided = set((st.get("spellings") or {}).keys()) | set((st.get("spellings") or {}).values())
    t = text or ""
    out = []
    low = t.lower()
    for uk, us in _UKUS:
        a = len(re.findall(r"\b" + uk + r"\b", low))
        b = len(re.findall(r"\b" + us + r"\b", low))
        if a and b and uk not in decided and us not in decided:
            out.append({"words": {uk: a, us: b}, "why": "British aur American dono spelling: ek tay kijiye"})
    groups: dict[str, dict[str, int]] = {}
    for w in re.findall(r"[ऀ-ॿ]+", t):
        if len(w) < 3:
            continue
        groups.setdefault(_deva_key(w), {}).setdefault(w, 0)
        groups[_deva_key(w)][w] += 1
    for k, g in groups.items():
        if len(g) > 1 and not (set(g) & decided):
            out.append({"words": g, "why": "nukta / chandrabindu alag-alag: ek tay kijiye"})
    names: dict[str, int] = {}
    lowers = set(re.findall(r"\b[a-z]{3,}\b", t))
    for m in re.finditer(r"\b([A-Z][a-z]{2,})\b", t):
        w = m.group(1)
        if w.lower() in lowers or w in _STOP:
            continue
        names[w] = names.get(w, 0) + 1
    keys = sorted(names)
    done = set()
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if (a, b) in done or a in decided or b in decided:
                continue
            if a[0] == b[0] and difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.65 and abs(len(a) - len(b)) <= 2:
                done.add((a, b))
                out.append({"words": {a: names[a], b: names[b]}, "why": "naam do tarah likha hai: kaunsa sahi?"})
    return out[:40]


# ---------------------------------------------------------------- quotes / permissions / similarity
_LYRIC = re.compile(r"(?i)\b(song|lyrics?|gaana|geet|गीत|गाना|गाणे|kavita|poem|कविता|शेर|ghazal|ग़ज़ल)\b")


def quotes(text: str, min_words: int = 25) -> list[dict[str, Any]]:
    """Quoted passages long enough to need a look (copyright of others' words), lyrics / poems at any length, block quotes."""
    t = text or ""
    out = []
    for m in re.finditer(r"[“\"]([^”\"]{20,4000})[”\"]", t):
        q = m.group(1).strip()
        n = words(q)
        around = t[max(0, m.start() - 120):m.start()] + " " + t[m.end():m.end() + 80]
        lyric = bool(_LYRIC.search(around))
        if n >= min_words or (lyric and n >= 4):
            out.append({"excerpt": " ".join(q.split()[:12]), "words": n, "kind": "lyrics" if lyric else "prose", "at": m.start()})
    for m in re.finditer(r"(?m)^(?:>\s?.+\n?){2,}", t):
        q = re.sub(r"(?m)^>\s?", "", m.group(0)).strip()
        out.append({"excerpt": " ".join(q.split()[:12]), "words": words(q), "kind": "epigraph", "at": m.start()})
    return out


def _shingles(text: str, n: int = 6) -> list[str]:
    w = [x.lower() for x in re.findall(r"[\wऀ-ॿ]+", text or "")]
    return [" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))]


def similarity(text: str, source: str, n: int = 6) -> dict[str, Any]:
    """How much of her text appears word for word in a source she gave (6-word runs). A signal, never a verdict."""
    a, b = _shingles(text, n), set(_shingles(source, n))
    if not a:
        return {"pct": 0.0, "longest": 0, "examples": []}
    hit = [i for i, s in enumerate(a) if s in b]
    longest, run, prev = 0, 0, -2
    starts, cur_start = [], 0
    for i in hit:
        if i == prev + 1:
            run += 1
        else:
            if run:
                starts.append((run, cur_start))
            run, cur_start = 1, i
        prev = i
        longest = max(longest, run)
    if run:
        starts.append((run, cur_start))
    ex = [a[s] for r, s in sorted(starts, reverse=True)[:3]]
    return {"pct": round(100 * len(hit) / len(a), 1), "longest": (longest + n - 1) if longest else 0, "examples": ex}


def distinct_sentences(text: str, k: int = 3) -> list[str]:
    s = [x.strip() for x in re.split(r"(?<=[.!?।])\s+", text or "") if 14 <= words(x) <= 40 and not re.search(r"[“”\"]", x)]
    s.sort(key=lambda x: -len(set(x.lower().split())))
    return s[:k]


def pd_india(death_year: int | None, year: int) -> bool | None:
    """s.22: copyright runs 60 years from the calendar year after the author's death. None = can't say."""
    if not death_year:
        return None
    return year >= int(death_year) + 61


# ---------------------------------------------------------------- ISBN
def isbn_norm(v: str) -> str:
    return re.sub(r"[^0-9Xx]", "", str(v or "")).upper()


def isbn_ok(v: str) -> bool:
    s = isbn_norm(v)
    if len(s) == 13 and s.isdigit() and s[:3] in ("978", "979"):
        tot = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(s[:12]))
        return (10 - tot % 10) % 10 == int(s[12])
    if len(s) == 10 and s[:9].isdigit():
        tot = sum((10 - i) * int(c) for i, c in enumerate(s[:9]))
        chk = (11 - tot % 11) % 11
        return (("X" if chk == 10 else str(chk)) == s[9])
    return False


def isbn_pretty(v: str) -> str:
    s = isbn_norm(v)
    return f"{s[:3]}-{s[3:5]}-{s[5:10]}-{s[10:12]}-{s[12:]}" if len(s) == 13 else s


# ---------------------------------------------------------------- royalty (HER contract) and platforms (HER numbers)
def _num(v) -> float | None:
    if v is None or v == "" or isinstance(v, bool):
        return None
    try:
        return float(str(v).replace(",", "").replace("₹", "").strip())
    except ValueError:
        return None


def clean_slabs(slabs: Any) -> list[dict[str, Any]]:
    out = []
    for s in slabs or []:
        if not isinstance(s, dict):
            continue
        pct = _num(s.get("pct"))
        if pct is None or not 0 < pct <= 100:
            raise ValueError("Har slab ka % chahiye (0-100).")
        upto = s.get("upto")
        out.append({"upto": int(_num(upto)) if _num(upto) else None, "pct": pct})
    out.sort(key=lambda x: (x["upto"] is None, x["upto"] or 0))
    if out and out[-1]["upto"] is not None:
        out.append({"upto": None, "pct": out[-1]["pct"]})
    return out


def royalty(slabs: list[dict], units_before: int, units: int, per_unit: float | None) -> float | None:
    """Units moved through slabs (cumulative over the book's life). per_unit = MRP (mrp basis) or net per copy."""
    if per_unit is None or not slabs:
        return None
    left, start, total = max(0, units), max(0, units_before), 0.0
    lo = 0
    for s in slabs:
        hi = s["upto"]
        if hi is not None and start >= hi:
            lo = hi
            continue
        room = left if hi is None else min(left, hi - max(start, lo))
        if room > 0:
            total += room * per_unit * s["pct"] / 100.0
            left -= room
            start += room
        lo = hi or lo
        if left <= 0:
            break
    return round(total, 2)


def ebook_kdp(price: float | None, plan: str, delivery: float | None = None, select: bool = False) -> dict[str, Any]:
    if price is None:
        return {"royalty": None, "say": "List price batayiye (aapka)."}
    notes = []
    if plan == "70":
        if not (KDP["in_70_min"] <= price <= KDP["in_70_max"]):
            notes.append(f"70% sirf Rs {KDP['in_70_min']}-{KDP['in_70_max']} par; is daam par 35% hi milega.")
            plan = "35"
        elif not select:
            notes.append("India ki bikri par 70% ke liye KDP Select zaroori (90 din e-book sirf Amazon par).")
    if plan == "70":
        if delivery is None:
            return {"royalty": None, "plan": "70", "notes": notes + ["Delivery cost (KDP ki report se) batayiye; tab hisaab."]}
        return {"royalty": round(0.70 * (price - delivery), 2), "plan": "70", "notes": notes}
    return {"royalty": round(0.35 * price, 2), "plan": "35", "notes": notes}


def pod(mrp: float | None, print_cost: float | None, share_pct: float | None) -> dict[str, Any]:
    """Print on demand (Pothi / Notion Press style): (MRP - printing) x her share %. Every number is hers / the platform's."""
    miss = [n for n, v in (("MRP", mrp), ("print cost", print_cost), ("aapka hissa %", share_pct)) if v is None]
    if miss:
        return {"royalty": None, "missing": miss, "say": "Chahiye: " + ", ".join(miss)}
    margin = mrp - print_cost
    if margin <= 0:
        return {"royalty": 0.0, "say": "MRP printing se kam hai: har copy par ghata."}
    return {"royalty": round(margin * share_pct / 100.0, 2), "margin": round(margin, 2)}


def legal_deposit_due(published: date) -> date:
    return published + timedelta(days=30)


# ---------------------------------------------------------------- checklists
CHECK_ITEMS = [
    ("isbn", "ISBN har format ka (isbn.gov.in, muft; title page, verso page, cover, PAN / Udyam)"),
    ("verso", "Copyright / verso page (© saal + naam, ISBN, edition, publisher, printer, keemat)"),
    ("permissions", "Doosron ke shabd / kavita / gaane / photo ki likhit anumati"),
    ("copyright_reg", "Copyright registration (copyright.gov.in, Form XIV; zaroori nahi, saboot ke liye achha)"),
    ("contract", "Publisher contract padha: hak kitne saal, kahan, kaunse format, royalty, hisaab kab"),
    ("ai_disclosure", "AI se bana text / cover / anuvaad hai to platform ko batana (KDP poochta hai)"),
    ("cover_credits", "Cover photo / font / art ka licence"),
    ("proof_copy", "Printed proof copy dekhi"),
    ("legal_deposit", "Chhapne ke 30 din ke andar 4 copy: National Library Kolkata + 3 public libraries (Delivery of Books Act 1954)"),
]
SELFPUB = {
    "kdp": ["KDP account (tax info, bank)", "e-book: 35% / 70% chuna (70% = Rs 99-599 + India ke liye KDP Select)",
            "paperback: print cost ke baad royalty dekhi", "AI content sawaal ka jawab", "cover + interior file preview"],
    "pothi": ["Pothi par account", "PDF interior + cover", "MRP aur unka print cost dekha", "ISBN unka ya apna"],
    "notionpress": ["Plan / package padha (paise wala ya muft)", "royalty % aur kis par", "ISBN kiske naam", "contract ki muddat"],
}
CHECK_STATUS = ("todo", "doing", "done", "na")


def verso_lines(book: dict, year: int) -> list[str]:
    f = book.get("facts") or {}
    who = book.get("author") or "[lekhak ka naam]"
    out = [f"© {f.get('year') or year} {who}. All rights reserved.",
           f"First published {f.get('year') or year} by {f.get('publisher') or '[publisher / imprint]'}"
           + (f", {f['address']}" if f.get("address") else ""),
           "No part of this book may be reproduced in any form without written permission of the copyright holder, except "
           "brief quotations in reviews."]
    for fmt, isbn in (book.get("isbns") or {}).items():
        out.append(f"ISBN {isbn_pretty(isbn)} ({fmt})")
    if not book.get("isbns"):
        out.append("ISBN [har format ka alag]")
    out.append(f"Price: {f['price']}" if f.get("price") else "Price: [MRP]")
    out.append(f"Printed by {f['printer']}" if f.get("printer") else "Printed by: [printer]")
    if book.get("kind") in ("fiction", "children"):
        out.append("This is a work of fiction. Names, characters and incidents are the author's imagination; any resemblance "
                   "to actual persons is coincidental.")
    if f.get("ai"):
        out.append(f"AI note: {f['ai']}")
    return out
