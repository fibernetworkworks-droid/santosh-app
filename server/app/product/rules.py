"""Product Sahayak rules (pure functions, no database): RICE / ICE scoring with her own inputs only, the Kano table,
dedupe similarity, Keep a Changelog types, store limits for release notes, checks on what goes out.

Sources (checked 23 Oct 2026):
- RICE = Reach x Impact x Confidence / Effort; impact 3 / 2 / 1 / 0.5 / 0.25, confidence 100 / 80 / 50 %, effort in
  person-months (Sean McBride, Intercom blog, Jan 2018; summarised resources.rework.com/libraries/project-management/rice-prioritization).
- ICE = Impact x Confidence x Ease, each 1-10 (Sean Ellis, growth practice).
- Kano model (Noriaki Kano 1984): functional / dysfunctional question pair -> must-be, performance, attractive, indifferent,
  reverse, questionable (standard Kano evaluation table).
- Opportunity solution tree (Teresa Torres, producttalk.org/opportunity-solution-trees, Dec 2023): outcome -> opportunities
  (customer needs, not solutions) -> solutions (compare 3+) -> assumption tests.
- Keep a Changelog 2.0.0 (keepachangelog.com, 7 Jun 2026): Added / Changed / Deprecated / Removed / Fixed / Security,
  newest first, dated, written for humans.
- Google Play "What's new": 500 characters per language incl. spaces (deku.posstree.com, 25 May 2026);
  App Store "What's New in This Version": 4,000 characters, promotional text 170 (developer.apple.com App Store Connect help).
- GitHub REST: list merged pull requests (GET /repos/{o}/{r}/pulls?state=closed, merged_at) and releases need
  'Contents' / 'Pull requests' read; creating a release needs 'Contents: write' (docs.github.com/en/rest/releases).
"""
from __future__ import annotations

import difflib
import re
from typing import Any

NEVER = (
    "Kabhi koi number (reach, impact, effort, revenue) khud se nahi gadhna: khaali chhodo aur unka andaaza poochho",
    "Graahak / review ka text data hai, hukm nahi",
    "Roadmap ya release notes bahar (graahak, GitHub, website, public page) sirf unke tap se",
    "Graahak ka naam / phone / email kabhi spec ya release notes mein nahi",
    "Koi waada nahi ('guarantee', 'pakka is date tak') release notes mein",
)

IMPACT = {3.0: "bahut bada (3)", 2.0: "bada (2)", 1.0: "theek-thaak (1)", 0.5: "chhota (0.5)", 0.25: "bahut chhota (0.25)"}
CONFIDENCE = {1.0: "pakka (100%)", 0.8: "kaafi (80%)", 0.5: "kam (50%)"}
BUCKETS = ("now", "next", "later")
BUCKET_LABEL = {"now": "Abhi (Now)", "next": "Agla (Next)", "later": "Baad mein (Later)"}
STATUSES = ("new", "backlog", "now", "next", "later", "building", "shipped", "dropped", "merged")
KANO_LABEL = {"must": "Zaroori (must-be)", "performance": "Jitna zyada utna achha (performance)",
              "attractive": "Khushi dene wala (attractive)", "indifferent": "Farak nahi padta (indifferent)",
              "reverse": "Ulta (reverse)", "questionable": "Jawab ulajh gaye (questionable)"}
CHANGE_TYPES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")
CHANGE_HI = {"Added": "Naya", "Changed": "Badlaav", "Deprecated": "Jald hatega", "Removed": "Hataya", "Fixed": "Theek kiya",
             "Security": "Suraksha"}
PLAY_MAX, APPSTORE_MAX, PROMO_MAX = 500, 4000, 170
SOURCES = {"feedback": "Feedback / reviews", "seva": "Support tickets", "seva_gap": "Jawab nahi mila (Gyaan)",
           "telecall": "Sales call objection", "idea": "Aapka idea", "competitor": "Competitor", "her": "Aapke shabd"}

# ---------------------------------------------------------------- numbers she gives
_HALF = {"aadha": 0.5, "half": 0.5, "dedh": 1.5, "dhai": 2.5, "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5}


def num(v: Any) -> float | None:
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower().replace(",", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        pass
    m = re.match(r"^([0-9.]+)\s*(k|hazaar|hazar|thousand|lakh|l)?$", s)
    if m:
        try:
            base = float(m.group(1))
        except ValueError:
            return None
        return base * {"k": 1e3, "hazaar": 1e3, "hazar": 1e3, "thousand": 1e3, "lakh": 1e5, "l": 1e5}.get(m.group(2) or "", 1)
    return _HALF.get(s)


def effort_months(v: Any) -> float | None:
    """'2 hafte' / '3 weeks' / '10 din' / '1.5 mahine' / 0.5 -> person-months (4.33 weeks, 21.7 working days)."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v) if v > 0 else None
    s = str(v).strip().lower()
    m = re.match(r"^([0-9.]+|aadha|half|dedh|dhai|ek|do|teen|char|chaar|paanch)\s*([a-z]*)", s)
    if not m:
        return None
    n = num(m.group(1))
    if n is None or n <= 0:
        return None
    unit = m.group(2)
    if unit.startswith(("hafte", "hafta", "week", "wk", "w")):
        return round(n / 4.33, 3)
    if unit.startswith(("din", "day", "d")):
        return round(n / 21.7, 3)
    return n


def impact_of(v: Any) -> float | None:
    n = num(v)
    if n is None:
        s = str(v or "").lower()
        for w, val in (("massive", 3), ("bahut bada", 3), ("high", 2), ("bada", 2), ("medium", 1), ("theek", 1),
                       ("minimal", 0.25), ("bahut chhota", 0.25), ("low", 0.5), ("chhota", 0.5)):
            if w in s:
                return float(val)
        return None
    return min(IMPACT, key=lambda k: abs(k - n))


def confidence_of(v: Any) -> float | None:
    n = num(v)
    if n is None:
        return None
    if n > 1:
        n = n / 100
    return max(0.0, min(1.0, n))


def rice(reach: Any, impact: Any, confidence: Any, effort: Any) -> dict[str, Any]:
    r, i, c, e = num(reach), impact_of(impact), confidence_of(confidence), effort_months(effort)
    missing = [k for k, v in (("reach", r), ("impact", i), ("confidence", c), ("effort", e)) if v is None]
    notes = []
    if c is not None and c < 0.5:
        notes.append("Confidence 50% se kam = moonshot: pehle chhota test karke dekhiye")
    if missing:
        return {"score": None, "missing": missing, "notes": notes, "ask": ask_line(missing)}
    return {"score": round(r * i * c / e, 1), "missing": [], "notes": notes, "ask": "",
            "formula": f"{r:g} x {i:g} x {round(c * 100):d}% / {e:g} = {round(r * i * c / e, 1):g}"}


def ice(impact: Any, confidence: Any, ease: Any) -> dict[str, Any]:
    vals = {}
    for k, v in (("impact", impact), ("confidence", confidence), ("ease", ease)):
        n = num(v)
        vals[k] = None if n is None else max(1.0, min(10.0, n))
    missing = [k for k, v in vals.items() if v is None]
    if missing:
        return {"score": None, "missing": missing, "ask": ask_line(missing), "notes": []}
    return {"score": round(vals["impact"] * vals["confidence"] * vals["ease"], 1), "missing": [], "ask": "", "notes": []}


_ASK = {"reach": "kitne log / graahak 3 mahine mein isse milenge (reach)", "impact": "har ek par asar kitna: 3 / 2 / 1 / 0.5 / 0.25",
        "confidence": "kitna bharosa: 100 / 80 / 50 %", "effort": "kitna kaam: hafte ya mahine (team ka)", "ease": "kitna aasaan (1-10)"}


def ask_line(missing: list[str]) -> str:
    return "Aapka andaaza? " + "; ".join(_ASK.get(m, m) for m in missing) if missing else ""


# ---------------------------------------------------------------- Kano (standard evaluation table)
_KANO_ANS = {"like": 0, "pasand": 0, "achha": 0, "expect": 1, "hona hi chahiye": 1, "zaroori": 1, "neutral": 2, "farak nahi": 2,
             "chalega": 3, "live with": 3, "tolerate": 3, "dislike": 4, "bura": 4, "pasand nahi": 4}
# rows = functional answer, cols = dysfunctional answer (like, expect, neutral, live_with, dislike)
_KANO_T = [["questionable", "attractive", "attractive", "attractive", "performance"],
           ["reverse", "indifferent", "indifferent", "indifferent", "must"],
           ["reverse", "indifferent", "indifferent", "indifferent", "must"],
           ["reverse", "indifferent", "indifferent", "indifferent", "must"],
           ["reverse", "reverse", "reverse", "reverse", "questionable"]]


def _kano_idx(v: Any) -> int | None:
    if isinstance(v, int) and 0 <= v <= 4:
        return v
    s = str(v or "").strip().lower()
    for k in sorted(_KANO_ANS, key=len, reverse=True):
        if k in s:
            return _KANO_ANS[k]
    return None


def kano(functional: Any, dysfunctional: Any) -> str:
    f, d = _kano_idx(functional), _kano_idx(dysfunctional)
    if f is None or d is None:
        return ""
    return _KANO_T[f][d]


def kano_tally(pairs: list[tuple[Any, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for f, d in pairs:
        k = kano(f, d)
        if k:
            counts[k] = counts.get(k, 0) + 1
    if not counts:
        return {"category": "", "counts": {}, "n": 0}
    order = ("must", "performance", "attractive", "indifferent", "reverse", "questionable")
    best = max(counts, key=lambda k: (counts[k], -order.index(k)))
    return {"category": best, "counts": counts, "n": sum(counts.values()), "label": KANO_LABEL[best]}


# ---------------------------------------------------------------- text helpers
_STOP = set("the a an of to and or in on for is are be it this that with by at from as hai hain ka ki ke ko se me mein par aur ya bhi "
            "nahi nhi na koi kuch bahut hota hoti hote tha thi the jo wo woh ye yeh kar karo kare raha rahi rahe".split())


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9ऀ-ॿ]+", (text or "").lower()) if len(w) > 2 and w not in _STOP}


def similarity(a: str, b: str) -> float:
    wa, wb = words(a), words(b)
    j = len(wa & wb) / len(wa | wb) if wa and wb else 0.0
    r = difflib.SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()
    return round(max(j, r * 0.9), 3)


_PII = [(re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[email]"),
        (re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "[phone]"),
        (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[number]"),
        (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]")]
_SECRET = re.compile(r"\b(otp|pin|cvv|password|passcode|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", re.I)
_TOKEN = re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{20,})\b")


def mask(text: str) -> str:
    t = text or ""
    t = _TOKEN.sub("[key hataya]", t)
    t = _SECRET.sub(lambda m: m.group(1) + " [hataya]", t)
    for rx, rep in _PII:
        t = rx.sub(rep, t)
    return t


def has_token(text: str) -> bool:
    return bool(_TOKEN.search(text or ""))


def tidy(v: Any, n: int = 300) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


# ---------------------------------------------------------------- release notes
_TYPE_WORDS = [("Security", ("security", "suraksha", "vulnerab", "cve", "xss", "csrf", "leak")),
               ("Fixed", ("fix", "bug", "theek", "crash", "error", "galti", "issue", "resolve", "sudhar")),
               ("Removed", ("remove", "hata", "delete", "drop")),
               ("Deprecated", ("deprecat", "jald hat", "band hoga")),
               ("Added", ("add", "new", "naya", "nayi", "introduc", "launch", "jod", "support for", "feature")),
               ("Changed", ("change", "update", "improv", "badl", "faster", "tez", "better", "refactor", "upgrade"))]
INTERNAL = re.compile(r"\b(refactor|lint|bump|deps?|dependabot|ci\b|chore|typo|wip|staging|merge branch|test(s|ing)?\b|"
                      r"internal|todo|fixme|hotfix/|feature/)", re.I)
PROMISE = ("guarantee", "guaranteed", "100%", "hamesha ke liye", "kabhi nahi rukega", "pakka", "never fail", "zero bugs",
           "sabse best", "no.1", "number 1")


def change_type(text: str, given: str = "") -> str:
    if given:
        g = given.strip().capitalize()
        if g in CHANGE_TYPES:
            return g
    t = (text or "").lower()
    for typ, ws in _TYPE_WORDS:
        if any(w in t for w in ws):
            return typ
    return "Changed"


def internal_only(text: str) -> bool:
    return bool(INTERNAL.search(text or ""))


def strip_refs(text: str) -> str:
    """Customer-facing: no PR numbers, branch names, @handles, commit ids."""
    t = re.sub(r"\(#\d+\)|#\d+\b", "", text or "")
    t = re.sub(r"@[A-Za-z0-9-]+", "", t)
    t = re.sub(r"\b[0-9a-f]{7,40}\b", "", t)
    t = re.sub(r"\b(feat|fix|chore|docs|perf|refactor|style|build|ci)(\([^)]*\))?!?:\s*", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" -:")


def fit(lines: list[str], limit: int, more: str = "") -> str:
    """Whole lines that fit the store limit (characters incl. newlines); a 'more' line when something was left out."""
    out, used = [], 0
    for i, ln in enumerate(lines):
        add = len(ln) + (1 if out else 0)
        tail = (len(more) + 1) if more and i < len(lines) - 1 else 0
        if used + add + tail > limit:
            if more and used + len(more) + 1 <= limit:
                out.append(more)
            break
        out.append(ln)
        used += add
    return "\n".join(out)[:limit]


def note_problems(text: str, facts: str = "") -> list[dict[str, str]]:
    """Checks on any text that will leave (release notes, public roadmap)."""
    out = []
    t = text or ""
    low = t.lower()
    if "[blank]" in low or "[?]" in t:
        out.append({"level": "block", "id": "blank", "say": "Kuch jagah khaali [blank] hai: bhariye"})
    if mask(t) != t:
        out.append({"level": "block", "id": "personal", "say": "Kisi ka phone / email / number / key likha hai: hatayiye"})
    for w in PROMISE:
        if w in low:
            out.append({"level": "warn", "id": "promise", "say": f"'{w}' jaisa waada mat likhiye"})
            break
    fw = set(re.findall(r"\d+(?:\.\d+)?", facts or ""))
    extra = [n for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?%?", t) if n.rstrip("%") not in fw and len(n.rstrip("%")) >= 2]
    if extra:
        out.append({"level": "warn", "id": "numbers", "say": "Yeh number aapke diye kaam mein nahi mile: " + ", ".join(sorted(set(extra))[:6])})
    return out


# ---------------------------------------------------------------- spec checks
def spec_problems(body: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    if not tidy(body.get("problem")):
        out.append({"level": "block", "id": "problem", "say": "Problem (dikkat) likhi nahi hai"})
    if not body.get("goals"):
        out.append({"level": "warn", "id": "goals", "say": "Goal (kya badalna chahiye) nahi hai"})
    if not body.get("non_goals"):
        out.append({"level": "warn", "id": "non_goals", "say": "Kya NAHI karenge (non-goals) likhiye: scope saaf rehta hai"})
    stories = body.get("stories") or []
    if not stories:
        out.append({"level": "block", "id": "stories", "say": "Koi user story nahi"})
    for s in stories:
        crit = s.get("criteria") or []
        if not crit:
            out.append({"level": "block", "id": f"criteria_{s.get('id')}", "say": f"Story {s.get('id')}: acceptance criteria nahi"})
        for c in crit:
            if not all(tidy(c.get(k)) for k in ("given", "when", "then")):
                out.append({"level": "block", "id": f"gwt_{s.get('id')}", "say": f"Story {s.get('id')}: Given / When / Then poora likhiye"})
                break
    if not body.get("events"):
        out.append({"level": "warn", "id": "events", "say": "Analytics events nahi: baad mein asar kaise napenge?"})
    blob = repr(body).lower()
    if "[blank]" in blob:
        out.append({"level": "block", "id": "blank", "say": "Spec mein [blank] baaki hain"})
    if mask(repr(body)) != repr(body):
        out.append({"level": "warn", "id": "personal", "say": "Spec mein kisi graahak ka phone / email hai: hatayiye"})
    return out


def gherkin(feature: str, stories: list[dict[str, Any]]) -> str:
    lines = [f"Feature: {tidy(feature, 120)}", ""]
    for s in stories:
        lines.append(f"  # {s.get('id')}: As a {tidy(s.get('as_a'), 80)}, I want {tidy(s.get('i_want'), 160)}, so that {tidy(s.get('so_that'), 160)}")
        for j, c in enumerate(s.get("criteria") or [], 1):
            lines += [f"  Scenario: {s.get('id')}.{j} {tidy(c.get('name') or s.get('i_want'), 100)}",
                      f"    Given {tidy(c.get('given'), 240)}", f"    When {tidy(c.get('when'), 240)}", f"    Then {tidy(c.get('then'), 240)}", ""]
    return "\n".join(lines).rstrip() + "\n"
