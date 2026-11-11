"""HOOLA PROMPTING P0 NAAP - the PROMPT card (docs/HOOLA_PROMPTING_PLAN.md part 11).

The question P0 answers BEFORE anything is built: does a complete brief beat her rough line in Hoola's OWN engines,
and by how much, per section? Each ask runs twice through the real engine - once as her raw line, once as the
hand-filled brief - and both results are scored the same way against what she actually wanted.

    python -m app.quality prompt                       # free: the set is valid, the scorer is calibrated, the estimate
    python -m app.quality prompt --live --budget-inr 300 [--section web|image|script] [--limit N] [--only id,id] [--judge]
    python -m app.quality prompt verdict <id> raw|brief|same ["why"]     # HER pick outranks every number
    python -m app.quality prompt --status              # the saved cards + her verdicts

What runs live (and what does NOT - said plainly):
- web    = the website ARCHITECT's plan (one call, no site built, nothing saved). The plan decides every page after
           it, and it is 1 call instead of a whole build. A full build is NOT scored here.
- script = the Create script writer (the same call the Script page makes).
- image  = the Create picture engine, then ONE reader call that answers yes / no per statement from the picture.

The brief is filled BY HAND, so this measures the CEILING: the most a perfect prompt helper could add. A section that
shows no gain even here is dropped before it is built. A section that gains still has to prove (P1) that Hoola can
fill the brief itself. Thresholds in `decide()` are judgement, not measured.
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from typing import Any

from .prompt_asks import ASKS, PROMPT_SET_V, SECTIONS

RUBRIC_V = 1
TENANT = "__promptcard__"
WIN_MARGIN = 5.0             # a pair is a win only when one side leads by more than this (0-100)
BUILD_GAIN, BUILD_WINS = 10.0, 0.60
DROP_GAIN = 4.0
MIN_PAIRS = 8                # fewer finished pairs in a section = no verdict
HER_MIN = 5                  # her picks decide a section once she has judged this many pairs
WEIGHTS = {"web": {"must": 55, "facts": 20, "engine": 15, "clean": 10},
           "script": {"must": 50, "facts": 25, "engine": 10, "clean": 15},
           "image": {"must": 100}}
# ASSUMED rupees per run until a live card measures them (the free card prints these as assumed)
ASSUMED_INR = {"web": 25.0, "script": 3.0, "image": 4.0}
MAGIC = ("act as", "you are an expert", "think step by step", "take a deep breath", "i will tip", "world-class")


# ---------------------------------------------------------------- the scorer (pure code)
def norm(s: Any) -> str:
    t = str(s or "").lower().replace("\\u20b9", " rs ").replace("₹", " rs ")
    t = re.sub(r"(?<=\d),(?=\d)", "", t)
    return re.sub(r"\s+", " ", t)


def must_hits(text: str, must: list[list[str]]) -> list[bool]:
    t = norm(text)
    return [any(norm(a) in t for a in alts) for alts in must]


def _alts(f: Any) -> list[str]:
    return [str(x) for x in f] if isinstance(f, (list, tuple)) else [str(f)]


def facts_kept(text: str, facts: list) -> list[bool]:
    """A fact may be one literal or a list of spellings of the same fact (any one counts)."""
    t = norm(text)
    return [any(norm(x) in t for x in _alts(f)) for f in facts]


_MONEY = re.compile(r"(?:\brs\.?|\binr)\s*(\d[\d.]*)(?:\s*(lakh|crore|k)\b)?|(\d[\d.]*)\s*(?:rupees|rupaye|rupay)\b")
_PHONE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
_PCT = re.compile(r"(\d{1,3})\s*%")


def invented(text: str, given: str) -> list[str]:
    """Prices, phone numbers and percentages in the result that were NOT in what the engine was given."""
    t, g = norm(text), norm(given)
    nums = {x.rstrip(".") for x in re.findall(r"\d[\d.]*", g)}
    out: list[str] = []
    for m in _MONEY.finditer(t):
        n = (m.group(1) or m.group(3) or "").rstrip(".")
        if n and n not in nums:
            out.append("price " + n)
    out += ["phone " + m.group(0) for m in _PHONE.finditer(t) if m.group(0) not in g]
    out += ["percent " + m.group(1) for m in _PCT.finditer(t) if m.group(1) not in nums]
    return sorted(set(out))[:8]


def length_fit(text: str, secs: int) -> bool:
    """Rough: the whole screenplay (action + dialogue) for N seconds sits between 2 and 9 words a second."""
    n = len(str(text or "").split())
    return secs * 2 <= n <= secs * 9


def unecho(text: str, given: str) -> str:
    """The result WITHOUT what the engine was handed: an engine that pastes her brief back has made nothing. Whole
    copies and every copied line of 40+ characters are removed before anything is scored."""
    t = str(text or "")
    g = str(given or "").strip()
    for chunk in [g, *[ln.strip() for ln in g.splitlines()]]:
        if len(chunk) >= 40:
            t = t.replace(chunk, " ")
    return t


def score_text(ask: dict, text: str, given: str, engine_ok: float | None = None) -> dict[str, Any]:
    """One web / script result against what she wanted. Parts are shares 0-1; `score` is 0-100."""
    w = WEIGHTS[ask["section"]]
    text = unecho(text, given)
    mh, fk = must_hits(text, ask["must"]), facts_kept(text, ask["facts"])
    inv = invented(text, given)
    if ask["section"] == "script":
        engine_ok = 1.0 if length_fit(text, ask["secs"]) else 0.0
    parts = {"must": sum(mh) / len(mh) if mh else 1.0, "facts": sum(fk) / len(fk) if fk else 1.0,
             "engine": float(engine_ok if engine_ok is not None else 0.0), "clean": 0.0 if inv else 1.0}
    return {"score": round(sum(parts[k] * w[k] for k in w), 1), "parts": {k: round(parts[k], 3) for k in w},
            "missed": [ask["must"][i][0] for i, ok in enumerate(mh) if not ok],
            "facts_lost": [_alts(ask["facts"][i])[0] for i, ok in enumerate(fk) if not ok], "invented": inv}


def score_image(ask: dict, answers: list[bool]) -> dict[str, Any]:
    a = [bool(x) for x in answers][:len(ask["must"])]
    a += [False] * (len(ask["must"]) - len(a))
    share = sum(a) / len(a) if a else 0.0
    return {"score": round(share * 100, 1), "parts": {"must": round(share, 3)},
            "missed": [ask["must"][i] for i, ok in enumerate(a) if not ok], "facts_lost": [], "invented": []}


def winner(raw: float, brief: float) -> str:
    return "brief" if brief - raw > WIN_MARGIN else "raw" if raw - brief > WIN_MARGIN else "same"


def decide(pairs: list[dict]) -> dict[str, Any]:
    """The section verdict, by rule. `pairs` = finished rows of ONE section ({raw:{score}, brief:{score}, her?})."""
    n = len(pairs)
    if n < MIN_PAIRS:
        return {"verdict": "NOT ENOUGH", "why": f"{n} finished pairs; {MIN_PAIRS} needed", "pairs": n}
    r = sum(p["raw"]["score"] for p in pairs) / n
    b = sum(p["brief"]["score"] for p in pairs) / n
    gain = b - r
    picks = [p["her"] for p in pairs if p.get("her")]
    if len(picks) >= HER_MIN:           # HER picks outrank the checks
        share = sum(1 for x in picks if x == "brief") / len(picks)
        v = "BUILD" if share >= BUILD_WINS else "DROP" if share <= 0.35 else "RETHINK"
        return {"verdict": v, "why": f"her picks: brief better in {round(share * 100)}% of {len(picks)} pairs",
                "pairs": n, "raw_avg": round(r, 1), "brief_avg": round(b, 1), "gain": round(gain, 1), "basis": "her"}
    wins = sum(1 for p in pairs if (p.get("her") or winner(p["raw"]["score"], p["brief"]["score"])) == "brief") / n
    if gain >= BUILD_GAIN and wins >= BUILD_WINS:
        v = "BUILD"
    elif gain < DROP_GAIN:
        v = "DROP"
    else:
        v = "RETHINK"
    return {"verdict": v, "why": f"brief {round(b, 1)} vs raw {round(r, 1)} (gain {round(gain, 1)}), brief clearly "
                                 f"better in {round(wins * 100)}% of pairs", "pairs": n, "raw_avg": round(r, 1),
            "brief_avg": round(b, 1), "gain": round(gain, 1), "wins": round(wins, 3), "basis": "checks"}


# ---------------------------------------------------------------- the free card
def set_problems(asks: list[dict] | None = None) -> list[str]:
    items = asks if asks is not None else ASKS
    out: list[str] = []
    ids = [a["id"] for a in items]
    if len(set(ids)) != len(ids):
        out.append("duplicate ids")
    for s in SECTIONS:
        sec = [a for a in items if a["section"] == s]
        if asks is None and len(sec) != 20:
            out.append(f"{s}: {len(sec)} asks, 20 expected")
        if asks is None and sum(1 for a in sec if a["lang"] == "hi") != 10:
            out.append(f"{s}: not 10 Hinglish + 10 English")
    for a in items:
        raw, brief = a["raw"], a["brief"]
        if len(raw.split()) > 16:
            out.append(f"{a['id']}: the raw line is not rough ({len(raw.split())} words)")
        if len(brief) < 3 * len(raw):
            out.append(f"{a['id']}: the brief adds too little")
        if len(brief) > (1800 if a["section"] == "image" else 2000):
            out.append(f"{a['id']}: the brief is over the engine's limit ({len(brief)} chars)")
        if any(m in brief.lower() for m in MAGIC):
            out.append(f"{a['id']}: a magic phrase in the brief")
        for f in a["facts"]:
            if not any(norm(x) in norm(brief) for x in _alts(f)):
                out.append(f"{a['id']}: fact '{_alts(f)[0]}' is not in its own brief")
        if not 4 <= len(a["must"]) <= 7:
            out.append(f"{a['id']}: {len(a['must'])} must items (4-7)")
        if a["section"] == "image" and a.get("words") and a["words"] not in brief:
            out.append(f"{a['id']}: the picture's words are not in the brief")
    return out


def engine_refusals(asks: list[dict] | None = None) -> list[str]:
    """Would the engines' own free guards refuse an ask? (A refused ask would waste a live run.)"""
    out: list[str] = []
    for a in asks if asks is not None else ASKS:
        for arm in ("raw", "brief"):
            try:
                if a["section"] == "web":
                    from ..site import guard
                    bad = guard.brief_problem(a[arm][:2000]) if len(a[arm]) >= 6 else ""
                elif a["section"] == "image":
                    from .. import photogen
                    bad = photogen.problem(a[arm])
                else:
                    bad = ""
            except Exception as e:      # noqa: BLE001 - a guard that cannot load is reported, never a crash
                bad = f"guard not readable: {str(e)[:80]}"
            if bad:
                out.append(f"{a['id']} {arm}: {str(bad)[:120]}")
    return out


_GOOD_SCRIPT = ("1. INT. HOUSE - EVENING\nA boy opens the kaju katli box before the puja.\nMAA\nRuko! Pehle puja.\n"
                "Made fresh every morning in pure ghee. Kaju Katli Rs 880 per kg, gift box from Rs 299.\n"
                "Dhanteras se pehle WhatsApp par order kijiye. " + "Diwali ki mithai ghar ghar. " * 12)


def calibration() -> list[dict]:
    """Planted cases the scorer must tell apart. Each must fail for ITS OWN reason."""
    ask = next(a for a in ASKS if a["id"] == "s01")
    good = score_text(ask, _GOOD_SCRIPT, ask["brief"])
    no_must = score_text(ask, _GOOD_SCRIPT.replace("WhatsApp", "phone").replace("ghee", "oil"), ask["brief"])
    fact = score_text(ask, _GOOD_SCRIPT.replace("880", "900"), ask["brief"])
    inv = score_text(ask, _GOOD_SCRIPT + " Sirf aaj 50% off!", ask["brief"])
    long_ = score_text(ask, _GOOD_SCRIPT + " shabd" * 400, ask["brief"])
    img = next(a for a in ASKS if a["id"] == "i01")
    cases = [
        ("an honest script scores full", good["score"] == 100.0),
        ("a missing must item is named", no_must["score"] < good["score"] and "whatsapp" in no_must["missed"] and "ghee" in no_must["missed"]),
        ("a changed price = fact lost AND invented", "880" in fact["facts_lost"] and "price 900" in fact["invented"]),
        ("an invented offer is caught", "percent 50" in inv["invented"] and inv["parts"]["clean"] == 0.0),
        ("a script far too long fails the length band", long_["parts"]["engine"] == 0.0),
        ("comma / rupee forms read the same", facts_kept("only ₹14,999 today", ["14,999"]) == [True] and facts_kept("Rs 14999", ["14,999"]) == [True]),
        ("picture: 3 of 5 statements = 60", score_image(img, [True, True, True, False, False])["score"] == 60.0),
        ("her brief pasted back earns nothing", score_text(ask, ask["brief"], ask["brief"])["parts"]["must"] == 0.0),
        ("winner needs a clear lead", winner(50, 54) == "same" and winner(50, 56) == "brief" and winner(70, 60) == "raw"),
    ]

    def _pairs(r, b, n=10, her=None):
        return [{"raw": {"score": r}, "brief": {"score": b}, **({"her": her} if her else {})} for _ in range(n)]
    cases += [
        ("rule: a clear gain = BUILD", decide(_pairs(50, 75))["verdict"] == "BUILD"),
        ("rule: no gain = DROP", decide(_pairs(70, 71))["verdict"] == "DROP"),
        ("rule: a small gain = RETHINK", decide(_pairs(60, 67))["verdict"] == "RETHINK"),
        ("rule: too few pairs = no verdict", decide(_pairs(10, 90, n=3))["verdict"] == "NOT ENOUGH"),
        ("rule: her picks outrank the checks", decide(_pairs(50, 90, her="raw"))["verdict"] == "DROP"),
    ]
    return [{"case": c, "ok": bool(ok)} for c, ok in cases]


def estimate(items: list[dict]) -> dict[str, Any]:
    per = {s: 2 * sum(1 for a in items if a["section"] == s) for s in SECTIONS}
    return {"runs": per, "inr_assumed": round(sum(per[s] * ASSUMED_INR[s] for s in SECTIONS), 0),
            "per_run_assumed": dict(ASSUMED_INR)}


def free_card(asks: list[dict] | None = None) -> dict[str, Any]:
    items = asks if asks is not None else ASKS
    probs = set_problems(asks)
    cal = calibration()
    ref = engine_refusals(items)
    leak = []                    # must items her raw line ALREADY states: the brief adds nothing there
    for a in items:
        if a["section"] != "image":
            leak.append(sum(must_hits(a["raw"], a["must"])) / len(a["must"]))
    return {"kind": "free", "set": PROMPT_SET_V, "rubric": RUBRIC_V, "asks": len(items),
            "by_section": {s: sum(1 for a in items if a["section"] == s) for s in SECTIONS},
            "set_problems": probs, "calibration": cal, "calibration_ok": sum(c["ok"] for c in cal),
            "engine_refusals": ref, "raw_already_says": round(sum(leak) / len(leak), 3) if leak else None,
            "estimate": estimate(items), "ok": not probs and all(c["ok"] for c in cal) and not ref}


# ---------------------------------------------------------------- live: the three engines (each replaceable in a test)
def _web_plan(words: str) -> tuple[str, float]:
    """The architect's plan for these words (one call, no project, nothing saved) + its own depth share."""
    from ..site import architect as A
    from ..site import guard
    words = str(words)[:2000]
    bad = guard.brief_problem(words)
    if bad:
        raise RuntimeError("refused: " + str(bad)[:160])
    tier = A.size(words)
    raw = A._ask(A._system(), json.dumps({"her_words": words, "size_by_code": tier, "size_means": A.TIER_NOTE[tier]},
                                         ensure_ascii=False), 16000, "site_art")
    spec = A.clean(raw, words, tier)
    if not spec.get("pages"):
        raise RuntimeError("the architect gave no pages")
    d = A.depth(spec)
    made = {k: v for k, v in spec.items() if k != "words"}      # `words` is HER line echoed back: never scored as output
    return json.dumps(made, ensure_ascii=False), (d["passed"] / d["total"] if d["total"] else 0.0)


async def _run_web(ask: dict, arm: str) -> dict[str, Any]:
    text, depth = await asyncio.to_thread(_web_plan, ask[arm])
    return {"text": text, "engine": depth, "given": ask[arm]}


async def _run_script(ask: dict, arm: str) -> dict[str, Any]:
    from ..create import service as CS
    if arm == "brief":
        text = await CS.write("script", ask["brief"], ask["fmt"], f"{ask['secs']} seconds", ask["language"], ask["tone"])
    else:
        text = await CS.write("script", ask["raw"])
    return {"text": text, "given": ask[arm]}


_READER = ("You check ONE picture against a list of statements. Answer each only from what is visible in the picture; "
           "when unsure answer false. Reply ONLY JSON: {\"a\": [true/false per statement, same order], "
           "\"text\": \"the words you can read on the picture, or empty\"}")


async def _read_picture(png: bytes, statements: list[str]) -> dict[str, Any]:
    from ..agent.santosh import get_client
    from ..config import get_settings
    st = get_settings()
    body = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(statements))
    resp = await asyncio.wait_for(get_client().messages.create(
        model=st.anthropic_model, max_tokens=400, system=_READER,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                         "data": base64.b64encode(png).decode()}},
            {"type": "text", "text": "Statements:\n" + body}]}]), timeout=120)
    raw = "".join(str(b.get("text") if isinstance(b, dict) else getattr(b, "text", "")) for b in resp.content)
    m = re.search(r"\{.*\}", raw, re.S)
    v = json.loads(m.group(0)) if m else {}
    return {"a": [bool(x) for x in (v.get("a") or [])], "text": str(v.get("text") or "")[:300]}


async def _run_image(ask: dict, arm: str) -> dict[str, Any]:
    from .. import photogen
    from .run import _dir
    made = await asyncio.to_thread(photogen.make, ask[arm], None, ask["aspect"] if arm == "brief" else "", "fast")
    folder = _dir() / "promptcard-img"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{ask['id']}-{arm}.png"
    path.write_bytes(made["png"])
    read = await _read_picture(made["png"], ask["must"])
    return {"answers": read["a"], "seen_text": read["text"], "file": str(path), "model": made.get("model"),
            "flat_inr": float(made.get("cost_inr") or 0), "given": ask[arm]}


RUNNERS = {"web": _run_web, "script": _run_script, "image": _run_image}

_JUDGE = ("Two results, A and B, were made for the same small-business owner. You are given what she really wanted. "
          "Pick the one that serves it better; say same only when neither is clearly better. Do not reward length. "
          "Reply ONLY JSON: {\"pick\": \"A\" | \"B\" | \"same\", \"why\": \"one line\"}")


async def _judge(ask: dict, raw_text: str, brief_text: str, flip: bool) -> dict | None:
    """Blind pick for web / script. `flip` alternates which side is shown first, so position cannot favour one arm."""
    try:
        from ..agent.santosh import get_client
        from ..config import get_settings
        st = get_settings()
        a, b = (brief_text, raw_text) if flip else (raw_text, brief_text)
        resp = await asyncio.wait_for(get_client().messages.create(
            model=getattr(st, "agent_hard_model", "") or st.anthropic_model, max_tokens=200, system=_JUDGE,
            messages=[{"role": "user", "content": f"WHAT SHE WANTED:\n{ask['brief']}\n\nRESULT A:\n{a[:9000]}\n\n"
                                                  f"RESULT B:\n{b[:9000]}"}]), timeout=120)
        raw = "".join(str(x.get("text") if isinstance(x, dict) else getattr(x, "text", "")) for x in resp.content)
        m = re.search(r"\{.*\}", raw, re.S)
        v = json.loads(m.group(0)) if m else {}
        p = str(v.get("pick", "")).strip().upper()
        pick = "same" if p not in ("A", "B") else ("brief" if (p == "A") == flip else "raw")
        return {"pick": pick, "first": "brief" if flip else "raw", "why": str(v.get("why", ""))[:200]}
    except Exception:       # noqa: BLE001 - a judge that fails is no judge, never a row's failure
        return None


async def _arm(ask: dict, arm: str) -> dict[str, Any]:
    from .. import usage
    t0 = time.time()
    with usage.run_meter() as acc:
        try:
            out = await RUNNERS[ask["section"]](ask, arm)
        except Exception as e:      # noqa: BLE001 - one broken run is a row, not a dead card
            return {"error": str(e)[:240], "inr": round(acc["usd"] * usage.usd_inr(), 2), "seconds": round(time.time() - t0, 1)}
    inr = acc["usd"] * usage.usd_inr()
    if out.get("flat_inr") and acc.get("calls", 0) <= 1:      # the picture engine's own call was not metered: its flat price
        inr += out["flat_inr"]
    if ask["section"] == "image":
        sc = score_image(ask, out["answers"])
        keep = {"file": out["file"], "seen_text": out["seen_text"], "model": out.get("model")}
    else:
        sc = score_text(ask, out["text"], out["given"], out.get("engine"))
        keep = {"out": out["text"][:3000], "chars": len(out["text"])}
    return {**sc, **keep, "inr": round(inr, 2), "seconds": round(time.time() - t0, 1), "calls": acc.get("calls", 0)}


async def live_card(asks: list[dict] | None = None, budget_inr: float = 0.0, judge: bool = False) -> dict[str, Any]:
    """Every ask as a PAIR (raw, then brief). A pair starts only when the budget still has room for it, so a budget
    that runs out leaves both arms with the same coverage."""
    if budget_inr <= 0:
        raise ValueError("a live prompt card needs --budget-inr N (the whole card's rupee ceiling)")
    from .. import usage
    usage.install()
    usage.bind(tenant=TENANT, feature="quality")
    items = asks if asks is not None else ASKS
    order: list[dict] = []          # interleave the sections so a small budget still touches each one
    by = {s: [a for a in items if a["section"] == s] for s in SECTIONS}
    for i in range(max((len(v) for v in by.values()), default=0)):
        order += [by[s][i] for s in SECTIONS if i < len(by[s])]
    rows: list[dict] = []
    spent, stopped = 0.0, ""
    seen: dict[str, list[float]] = {s: [] for s in SECTIONS}
    hers = verdicts()
    for n, a in enumerate(order):
        s = a["section"]
        need = 2 * (max(seen[s]) if seen[s] else ASSUMED_INR[s])
        if spent + need > budget_inr:
            stopped = f"budget: Rs {round(spent, 2)} spent of {budget_inr}, the next {s} pair needs about Rs {round(need, 2)}"
            if all(spent + 2 * (max(seen[x]) if seen[x] else ASSUMED_INR[x]) > budget_inr for x in SECTIONS):
                break
            continue
        raw = await _arm(a, "raw")
        brief = await _arm(a, "brief")
        spent += raw.get("inr", 0.0) + brief.get("inr", 0.0)
        seen[s] += [x["inr"] for x in (raw, brief) if "error" not in x]
        row: dict[str, Any] = {"id": a["id"], "section": s, "lang": a["lang"], "ask": a["raw"], "raw": raw, "brief": brief}
        if "error" not in raw and "error" not in brief:
            row["gain"] = round(brief["score"] - raw["score"], 1)
            row["winner"] = winner(raw["score"], brief["score"])
            if judge and s != "image":
                row["judge"] = await _judge(a, raw.get("out", ""), brief.get("out", ""), flip=bool(n % 2))
        if a["id"] in hers:
            row["her"] = hers[a["id"]]["pick"]
        rows.append(row)
        if len(rows) >= 3 and all("error" in r["raw"] and "error" in r["brief"] for r in rows):
            stopped = "three dead pairs in a row: " + rows[-1]["raw"]["error"]
            break
    return summarise(rows, kind="live", planned=len(order), spent=spent, budget=budget_inr, stopped=stopped)


def summarise(rows: list[dict], kind: str = "live", planned: int = 0, spent: float = 0.0, budget: float = 0.0,
              stopped: str = "") -> dict[str, Any]:
    sections: dict[str, Any] = {}
    for s in SECTIONS:
        done = [r for r in rows if r["section"] == s and "gain" in r]
        d = decide(done)
        if done:
            keys = WEIGHTS[s].keys()
            d["parts"] = {arm: {k: round(sum(r[arm]["parts"].get(k, 0) for r in done) / len(done), 3) for k in keys}
                          for arm in ("raw", "brief")}
            d["invented"] = {arm: sum(1 for r in done if r[arm]["invented"]) for arm in ("raw", "brief")}
            d["inr_per_run"] = round(sum(r[arm]["inr"] for r in done for arm in ("raw", "brief")) / (2 * len(done)), 2)
            d["by_lang"] = {lg: round(sum(r["gain"] for r in done if r["lang"] == lg) / max(1, sum(1 for r in done if r["lang"] == lg)), 1)
                            for lg in ("hi", "en")}
            j = [r["judge"] for r in done if r.get("judge")]
            if j:
                d["judge"] = {"brief": sum(1 for x in j if x["pick"] == "brief"), "raw": sum(1 for x in j if x["pick"] == "raw"),
                              "same": sum(1 for x in j if x["pick"] == "same"),
                              "first_shown_won": sum(1 for x in j if x["pick"] == x["first"])}
        d["errors"] = sum(1 for r in rows if r["section"] == s and "gain" not in r)
        sections[s] = d
    return {"kind": kind, "set": PROMPT_SET_V, "rubric": RUBRIC_V, "asks": len(rows), "planned": planned,
            "sections": sections, "inr": round(spent, 2), "budget_inr": budget, "stopped": stopped, "rows": rows}


# ---------------------------------------------------------------- HER verdict: it outranks every number above
def _verdict_path():
    from .run import _dir
    return _dir() / "prompt_verdicts.json"


def verdicts() -> dict[str, dict]:
    try:
        return json.loads(_verdict_path().read_text())
    except Exception:
        return {}


def set_verdict(ask_id: str, pick: str, note: str = "") -> dict:
    if pick not in ("raw", "brief", "same"):
        raise ValueError("pick is raw, brief or same")
    if ask_id not in {a["id"] for a in ASKS}:
        raise ValueError("no such prompt ask: " + ask_id)
    v = verdicts()
    v[ask_id] = {"pick": pick, "note": note[:400], "at": int(time.time()), "set": PROMPT_SET_V}
    _verdict_path().write_text(json.dumps(v, ensure_ascii=False, indent=1))
    return v[ask_id]


def with_verdicts(card: dict) -> dict:
    """A saved live card re-decided with her picks as they stand now."""
    hers = verdicts()
    rows = [{**r, **({"her": hers[r["id"]]["pick"]} if r["id"] in hers else {})} for r in card.get("rows", [])]
    return summarise(rows, kind=card.get("kind", "live"), planned=card.get("planned", 0), spent=card.get("inr", 0.0),
                     budget=card.get("budget_inr", 0.0), stopped=card.get("stopped", ""))


# ---------------------------------------------------------------- picking, saving, printing
def pick(only: str = "", limit: int = 0, section: str = "") -> list[dict]:
    """`limit` is PER SECTION, so a small try still touches all three."""
    items = [a for a in ASKS if not section or a["section"] == section]
    if only:
        want = {x.strip() for x in only.split(",") if x.strip()}
        items = [a for a in items if a["id"] in want]
    if limit:
        out: list[dict] = []
        for s in SECTIONS:
            out += [a for a in items if a["section"] == s][:limit]
        items = out
    return items


def save(card: dict, label: str = "") -> dict:
    from .run import _dir
    card = {**card, "label": label, "at": int(time.time())}
    name = f"promptcard-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1))
    card["file"] = name
    return card


def saved() -> list[dict]:
    from .run import _dir
    out = []
    for p in sorted(_dir().glob("promptcard-live-*.json"), reverse=True)[:30]:
        try:
            d = json.loads(p.read_text())
            out.append({"file": p.name, "at": d.get("at"), "label": d.get("label"), "asks": d.get("asks"),
                        "inr": d.get("inr"), "stopped": d.get("stopped"),
                        "sections": {s: {k: v.get(k) for k in ("verdict", "gain", "pairs", "raw_avg", "brief_avg")}
                                     for s, v in (d.get("sections") or {}).items()}})
        except Exception:
            continue
    return out


def lines(card: dict) -> list[str]:
    if card.get("kind") == "free":
        e = card["estimate"]
        out = [f"Prompt card (free, set v{card['set']}, rubric v{card['rubric']}): {card['asks']} asks "
               f"({', '.join(f'{s} {n}' for s, n in card['by_section'].items())}), scorer calibration "
               f"{card['calibration_ok']}/{len(card['calibration'])} - {'OK' if card['ok'] else 'NOT OK'}"]
        out += [f"  set problem: {p}" for p in card["set_problems"][:12]]
        out += [f"  calibration FAILED: {c['case']}" for c in card["calibration"] if not c["ok"]]
        out += [f"  an engine guard would refuse: {r}" for r in card["engine_refusals"][:12]]
        if card.get("raw_already_says") is not None:
            out.append(f"  her raw lines already state {round(card['raw_already_says'] * 100)}% of the must items (web + script); "
                       "the rest is what a brief has to add")
        out.append(f"  a full live card = {sum(e['runs'].values())} runs ({', '.join(f'{s} {n}' for s, n in e['runs'].items())}), "
                   f"about Rs {int(e['inr_assumed'])} ASSUMED (web {e['per_run_assumed']['web']}, script "
                   f"{e['per_run_assumed']['script']}, image {e['per_run_assumed']['image']} a run - not measured yet)")
        out.append("  live: python -m app.quality prompt --live --budget-inr N [--limit 2] [--section web] [--judge]")
        return out
    out = [f"Prompt card (LIVE, set v{card['set']}, rubric v{card['rubric']}): {card['asks']} of {card['planned']} pairs, "
           f"Rs {card['inr']} of {card['budget_inr']}"]
    if card.get("stopped"):
        out.append("  stopped: " + card["stopped"])
    for s in SECTIONS:
        d = card["sections"][s]
        out.append(f"  {s.upper():6} {d['verdict']:10} {d['why']}" + (f"   [{d['errors']} failed]" if d.get("errors") else ""))
        if d.get("parts"):
            out.append("         parts raw -> brief: " + ", ".join(
                f"{k} {round(d['parts']['raw'][k] * 100)} -> {round(d['parts']['brief'][k] * 100)}" for k in d["parts"]["raw"]))
            out.append(f"         invented facts: raw {d['invented']['raw']}, brief {d['invented']['brief']} pairs; gain "
                       f"Hinglish {d['by_lang']['hi']}, English {d['by_lang']['en']}; Rs {d['inr_per_run']} a run")
        if d.get("judge"):
            j = d["judge"]
            out.append(f"         blind judge: brief {j['brief']}, raw {j['raw']}, same {j['same']} "
                       f"(first-shown side won {j['first_shown_won']} times)")
    for r in card["rows"]:
        if "gain" in r:
            out.append(f"    {r['id']} {r['winner']:5} raw {r['raw']['score']:5} brief {r['brief']['score']:5}"
                       + (f"  her: {r['her']}" if r.get("her") else "") + f"  | {r['ask'][:60]}")
        else:
            err = r["raw"].get("error") or r["brief"].get("error") or "?"
            out.append(f"    {r['id']} ERROR {err[:110]}")
    out.append("  The brief was filled BY HAND: this is the ceiling. BUILD = worth building; it does not yet prove Hoola "
               "can fill the brief itself (P1).")
    out.append("  Her pick outranks the checks: python -m app.quality prompt verdict <id> raw|brief|same")
    return out
