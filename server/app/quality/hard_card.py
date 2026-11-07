"""v0.438 SOCH KE JAWAB step 7 - the HARD CARD: hard questions with known right answers, run through Hoola's REAL
pipeline and scored (owner: "GO STEP 7").

Steps 1-6 (v0.272 / v0.429 / v0.430 / v0.433 / v0.436 / v0.437) changed how a hard ask is handled - spotted, Opus with
thinking and room, pylab for every number, a reasoning recipe, a held self-check, deep research - but nothing measured
whether the ANSWERS got right. This card does, two ways:
- free_card(): no model - is every ask spotted as hard, does pylab ride with it, does the recipe carry its kind line,
  is a research ask routed to research. CI pins it.
- live_card(): ONE real turn per ask on the tenant "__quality__" (never her chats, never her budget), exactly what she
  would get (run.py's runner), then scored IN CODE: the right numbers found within tolerance (Indian commas, lakh /
  crore read), the must-have points present, pylab used for a calculation, sources (2+ links) for research, the
  self-check ran; optional Opus judge (0-10) for the open-ended asks.
The answer key was computed in Python, never written from memory. HARD_CARD_V moves only with a deliberate change.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

HARD_CARD_V = 1


def N(*vals, tol: float = 0.006, abs_tol: float = 0.0) -> dict:
    """A number that must appear: any of vals, within relative tol (or abs_tol)."""
    return {"num": list(vals), "tol": tol, "abs": abs_tol}


def K(*words) -> dict:
    """A point that must appear: any of these words / phrases (case-insensitive)."""
    return {"any": list(words)}


CALC = "calc"
SET: list[dict] = [
    # ---------------------------------------------------------------- money maths (exact answers)
    {"id": "emi", "kind": CALC, "quick": True, "text": "20 lakh ke home loan ki EMI kitni banegi 9% pe 20 saal ke liye, total interest bhi batao",
     "expect": [N(17994.52), N(2318684.59, 23.19e5, tol=0.004)]},
    {"id": "breakeven", "kind": CALC, "quick": True,
     "text": "Meri bakery ka fixed cost 80,000 mahina hai, ek cake 450 ka bikta hai aur banane mein 260 lagta hai. Break-even kitne cake pe hoga?",
     "expect": [N(421.05, 422, tol=0.003)]},
    {"id": "cagr", "kind": CALC, "quick": True, "text": "Sales 2021 mein 40 lakh thi aur 2025 mein 95 lakh, CAGR kitna hua?",
     "expect": [N(24.14, abs_tol=0.15)]},
    {"id": "sip", "kind": CALC, "text": "Har mahine 15,000 ki SIP 12% saalana return pe 15 saal mein kitni banegi?",
     "expect": [N(7493702.96, 7568639.99, 74.94e5, 75.69e5, tol=0.01)]},
    {"id": "solar", "kind": CALC, "quick": True,
     "text": "I invest 5 lakh in a solar plant that saves 9,000 a month. Calculate the payback period and yearly return.",
     "expect": [N(55.56, 4.63, 4.6, tol=0.01), N(21.6, abs_tol=0.2)]},
    {"id": "price_volume", "kind": CALC,
     "text": "Mera margin abhi 18% hai. Agar main price 10% badhaun aur volume 6% gire, to profit kitna percent badhega ya ghatega?",
     "expect": [N(46.22, 46.2, abs_tol=0.4)]},
    {"id": "doubling", "kind": CALC, "quick": True, "text": "Ek company 15% saalana growth se badh rahi hai, kitne saal mein revenue double hoga?",
     "expect": [N(4.96, 4.959, 5.0, abs_tol=0.06)]},
    {"id": "fd_quarterly", "kind": CALC, "text": "5 lakh ki FD 8% pe quarterly compounding ke saath 5 saal baad kitni hogi?",
     "expect": [N(742973.70, 7.43e5, tol=0.003)]},
    {"id": "gst_add", "kind": CALC, "quick": True, "text": "4,500 ke item pe 18% GST jod ke total kitna hoga aur GST kitna?",
     "expect": [N(5310), N(810)]},
    {"id": "real_return", "kind": CALC, "text": "If inflation is 6% and my FD gives 7%, what is my real return? Explain with numbers.",
     "expect": [N(0.94, 0.943, 1.0, abs_tol=0.07)]},
    {"id": "ltv_cac", "kind": CALC, "text": "Our CAC is 1,200 and LTV is 3,000. Is the business healthy? What should we change?",
     "expect": [N(2.5, abs_tol=0.01), K("3", "3:1", "3x", "three")]},
    {"id": "discounts", "kind": CALC, "quick": True, "text": "Pehle 20% discount phir uspe 10% aur - kul kitna discount hua?",
     "expect": [N(28, abs_tol=0.1)]},
    {"id": "unit_econ", "kind": CALC,
     "text": "Work out the unit economics of my tiffin service: 120 per meal, 70 food cost, 15 delivery, 300 meals a day",
     "expect": [N(35), N(10500, tol=0.001)]},
    # ---------------------------------------------------------------- word problems / logic
    {"id": "trains", "kind": CALC, "quick": True,
     "text": "Ek train 60 km/h, doosri 40 km/h, 300 km door se aamne saamne chal rahi hain, kab milengi? step by step samjhao",
     "expect": [N(3)]},
    {"id": "ages", "kind": CALC, "text": "Pita ki umar bete se 3 guna hai, 10 saal baad 2 guna hogi, dono ki umar kya hai? logic samjhao",
     "expect": [N(10), N(30)]},
    {"id": "dice", "kind": CALC, "text": "What is the probability of getting at least one six in four throws of a dice?",
     "expect": [N(51.77, 0.5177, 51.8, tol=0.003, abs_tol=0.0)]},
    {"id": "equation", "kind": CALC, "quick": True, "text": "Solve 3x + 7 = 2x - 5 and explain each step", "expect": [N(-12)]},
    {"id": "machines", "kind": CALC, "text": "Ek sawaal hal karo: 5 machines 5 minute mein 5 widget banati hain, 100 machines 100 widget kitni der mein?",
     "expect": [N(5), K("5 minute", "5 min", "five minutes", "paanch minute")]},
    {"id": "workers", "kind": CALC, "text": "Ek project 3 log 12 din mein karte hain, 4 log kitne din mein karenge? explain",
     "expect": [N(9)]},
    {"id": "root2", "kind": "proof", "text": "Prove that root 2 is irrational",
     "expect": [K("contradiction", "virodh"), K("even", "sam "), K("lowest terms", "coprime", "co-prime", "no common factor",
                                                                   "simplest form", "gcd")]},
    {"id": "boxes", "kind": "proof", "text": "Ek paheli hal karo: teen dabbe hain, sab galat label wale - apples, oranges, mixed. Ek fal nikal ke kaise pata karein?",
     "expect": [K("mixed", "mix", "dono")]},
    # ---------------------------------------------------------------- rules / decisions (stable facts + judge)
    {"id": "gst_scheme", "kind": "rules",
     "text": "Compare GST composition vs regular scheme for my 80 lakh turnover kirana shop and recommend",
     "expect": [K("1.5 crore", "150 lakh", "1,50,00,000", "1.5 cr"), K("1%", "1 %", "one percent"),
                K("input tax credit", "ITC")], "judge": True},
    {"id": "tds_194j", "kind": "rules",
     "text": "Freelancer ko 60,000 professional fees diye to TDS kaatna padega ya nahi, kis section mein aur kitna?",
     "expect": [K("194J", "194 J"), K("10%", "10 %"), N(6000)], "judge": True},
    {"id": "rent_buy", "kind": "decision", "text": "Ghar kharidna better hai ya kiraye pe rehna? 60 lakh ka flat, rent 18,000. Numbers ke saath batao",
     "expect": [N(216000, 2.16e5, 3.6, abs_tol=0.0, tol=0.01)], "judge": True},
    {"id": "ads_rootcause", "kind": "diagnosis", "text": "Ads pe kharcha badhaya par orders nahi badhe, kyun? kya galat ho raha hai",
     "expect": [K("conversion", "landing", "website", "page"), K("target", "audience")], "judge": True},
    {"id": "gtm", "kind": "plan", "text": "Plan a 6-month go-to-market strategy for an Indian SaaS startup with budget 10 lakh",
     "expect": [K("month 1", "month one", "mahina 1", "phase", "weeks 1"), K("budget", "10 lakh", "₹10")], "judge": True},
    # ---------------------------------------------------------------- research (sources)
    {"id": "research_cpi", "kind": "research",
     "text": "Research karo: India ki latest CPI inflation kitni hai aur pichhle 6 mahine ka trend kya hai - sources ke saath",
     "expect": [K("mospi", "MoSPI", "Ministry of Statistics", "mospi.gov.in")], "judge": True},
    {"id": "research_ev", "kind": "research",
     "text": "Do deep research on the Indian electric two-wheeler market in 2025 with sources: size, top players, growth",
     "expect": [K("ola", "ather", "tvs", "bajaj", "hero")], "judge": True},
]
QUICK = [a["id"] for a in SET if a.get("quick")]


# ---------------------------------------------------------------- reading numbers the Indian way
_NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?:\s*(?:lakh|lac|crore|cr\b|k\b))?", re.I)


def numbers(text: str) -> list[float]:
    """Every number in a reply: 17,994.52 / ₹17,994 / 23.18 lakh / 1.5 crore / -12."""
    out = []
    for m in _NUM.finditer(str(text or "").replace("₹", " ").replace("−", "-")):
        raw = m.group(0).lower()
        mult = 1.0
        if "lakh" in raw or "lac" in raw:
            mult = 1e5
        elif "crore" in raw or re.search(r"cr\b", raw):
            mult = 1e7
        elif raw.endswith("k"):
            mult = 1e3
        digits = re.sub(r"[^\d.\-]", "", raw.split()[0] if " " in raw else re.sub(r"[a-z]+$", "", raw))
        try:
            out.append(float(digits) * mult)
        except ValueError:
            continue
    return out


def _num_ok(want: dict, found: list[float]) -> bool:
    for v in want["num"]:
        for f in found:
            if want.get("abs") and abs(f - v) <= want["abs"]:
                return True
            if v and abs(f - v) <= abs(v) * want.get("tol", 0.006):
                return True
            if v == 0 and abs(f) <= want.get("abs", 0):
                return True
    return False


def score_answer(item: dict, reply: str, tools: list[str] | None = None) -> dict:
    """In code: the expected points found, and the behaviour that should have happened."""
    found = numbers(reply)
    low = str(reply or "").lower()
    misses = []
    for e in item.get("expect", []):
        if "num" in e and not _num_ok(e, found):
            misses.append("number " + " / ".join(f"{v:g}" for v in e["num"][:2]))
        if "any" in e and not any(w.lower() in low for w in e["any"]):
            misses.append("point " + " / ".join(e["any"][:2]))
    tools = list(tools or [])
    links = len(set(re.findall(r"https?://[^\s)\]>]+", reply or "")))
    need = []
    if item["kind"] == CALC and "pylab" not in tools:
        need.append("pylab not used")
    if item["kind"] == "research" and links < 2:
        need.append(f"{links} source link(s)")
    return {"id": item["id"], "kind": item["kind"], "right": not misses, "misses": misses, "behaviour_ok": not need,
            "behaviour": need, "pylab": "pylab" in tools, "checked": "jaanch" in tools, "links": links}


# ---------------------------------------------------------------- the free card
def free_card(items: list[dict] | None = None) -> dict:
    from ..agent import admit, hard
    from ..config import get_settings
    st = get_settings()
    rows = []
    for a in items or SET:
        v = hard.assess(a["text"])
        names = {t["name"] for t in (admit.plan_for(a["text"], st).specs())}
        rec = hard.recipe(v["why"])
        rows.append({"id": a["id"], "kind": a["kind"], "hard": v["hard"] or v.get("maybe", False), "by_rules": v["hard"],
                     "pylab": "pylab" in names, "kind_line": rec != hard.RECIPE_CORE,
                     "research": hard.research_wanted(a["text"])})
    n = len(rows)
    return {"kind": "free", "set": HARD_CARD_V, "asks": n, "hard": sum(r["hard"] for r in rows),
            "pylab": sum(r["pylab"] for r in rows), "kind_lines": sum(r["kind_line"] for r in rows),
            "research_ok": sum(r["research"] for r in rows if r["kind"] == "research"),
            "research_asks": sum(1 for r in rows if r["kind"] == "research"), "rows": rows}


# ---------------------------------------------------------------- the live card
JUDGE = """You grade ONE answer an Indian AI coworker gave to a hard question. Score 0-10 on substance only:
correctness of facts and numbers, soundness of the reasoning, whether it answers every part, stated assumptions and
honest uncertainty, a clear recommendation where one was asked. Never reward length or style. A made-up figure, rule or
source caps the score at 3. Reply ONLY JSON: {"score": 0-10, "why": "<one short line>"}"""


async def _judge(item: dict, reply: str, settings) -> dict | None:
    import asyncio
    try:
        from ..agent.santosh import get_client
        resp = await asyncio.wait_for(get_client().messages.create(
            model=getattr(settings, "agent_hard_model", "") or settings.anthropic_model, max_tokens=300, system=JUDGE,
            messages=[{"role": "user", "content": f"QUESTION:\n{item['text']}\n\nANSWER:\n{reply[:9000]}"}]), timeout=90)
        raw = "".join(str(b.get("text") if isinstance(b, dict) else getattr(b, "text", "")) for b in resp.content)
        m = re.search(r"\{.*\}", raw, re.S)
        v = json.loads(m.group(0)) if m else {}
        return {"score": max(0, min(10, int(v.get("score", 0)))), "why": str(v.get("why", ""))[:200]}
    except Exception:
        return None


class _Catch(logging.Handler):
    """v0.439 the turn's own warnings (a refused model, 'error ref ...: <the real exception>'): her 0/28 run printed
    nothing because every failed turn's apology was scored as an answer and the logs went to 2>/dev/null."""

    def __init__(self):
        super().__init__(logging.WARNING)
        self.lines: list[str] = []

    def emit(self, record):
        try:
            self.lines.append(record.getMessage()[:400])
        except Exception:
            pass


async def _one(item: dict, tenant: str, judge: bool) -> dict:
    from ..agent import santosh
    from ..config import get_settings
    from .run import _calls_of, _new_conv
    conv = _new_conv(tenant)
    t0 = time.time()
    catch = _Catch()
    root = logging.getLogger()
    root.addHandler(catch)
    try:
        reply = await santosh.run_turn(conv, item["text"], tenant_id=tenant)
    except Exception as e:   # noqa: BLE001 - one broken ask is a row, not a dead card
        return {"id": item["id"], "kind": item["kind"], "error": str(e)[:200], "right": False, "behaviour_ok": False}
    finally:
        root.removeHandler(catch)
    failed = _failed(conv)
    if failed:   # the turn died and she got the apology line: that is an ERROR row with the real cause, never a score
        why = [x for x in catch.lines if "error ref" in x or "failed" in x or "refused" in x] or catch.lines
        return {"id": item["id"], "kind": item["kind"], "right": False, "behaviour_ok": False,
                "error": (why[-1] if why else (reply or "turn failed"))[:300], "reply": (reply or "")[:300],
                "log": catch.lines[-6:], "seconds": round(time.time() - t0, 1), "conv": conv}
    tools = [str(c.get("tool")) for c in _calls_of(conv)]
    row = score_answer(item, reply or "", tools)
    row.update({"seconds": round(time.time() - t0, 1), "tools": tools[:20], "reply": (reply or "")[:1500], "conv": conv,
                "log": catch.lines[-6:]})
    if judge and item.get("judge"):
        row["judge"] = await _judge(item, reply or "", get_settings())
    return row


def _failed(conv: str) -> bool:
    """Did this turn publish its error / budget line (source error / budget) instead of an answer? (the saved events)"""
    from sqlalchemy import select

    from ..db import Event, session
    with session() as s:
        for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "message")).all():
            p = e.payload or {}
            if p.get("role") == "assistant" and p.get("source") in ("error", "budget"):
                return True
    return False


async def live_card(items: list[dict] | None = None, judge: bool = False, tenant: str = "") -> dict:
    from .run import TENANT
    rows = []
    for a in items or SET:
        rows.append(await _one(a, tenant or TENANT, judge))
        if len(rows) >= 3 and all("error" in r for r in rows):
            break            # v0.439 three dead turns in a row: the cause is printed, the other asks are not wasted
    done = [r for r in rows if "error" not in r]
    calc = [r for r in done if r["kind"] == CALC]
    res = [r for r in done if r["kind"] == "research"]
    judged = [r["judge"]["score"] for r in done if r.get("judge")]
    return {"kind": "live", "set": HARD_CARD_V, "asks": len(rows), "planned": len(items or SET), "answered": len(done),
            "right": sum(r["right"] for r in done), "pylab_used": sum(r["pylab"] for r in calc), "calc_asks": len(calc),
            "sourced": sum(r["links"] >= 2 for r in res), "research_asks": len(res),
            "checked": sum(r.get("checked", False) for r in done), "errors": len(rows) - len(done),
            "judge_avg": round(sum(judged) / len(judged), 1) if judged else None,
            "median_s": sorted(r["seconds"] for r in done)[len(done) // 2] if done else None, "rows": rows}


async def ping() -> list[str]:
    """v0.439 one tiny real call per model with the hard turn's own settings (thinking, effort, streamed), then the
    same call plain: the API's own words say which part it refuses. A few paise."""
    from ..agent import santosh
    from ..config import get_settings
    st = get_settings()
    out = [f"key set: {bool(st.anthropic_api_key)}, chat model {st.anthropic_model}, hard model "
           f"{getattr(st, 'agent_hard_model', '')}, effort {getattr(st, 'agent_hard_effort', '')}"]
    shapes = [("plain", {}), ("thinking", {"thinking": {"type": "adaptive"}}),
              ("thinking+effort", {"thinking": {"type": "adaptive"},
                                   "extra_body": {"output_config": {"effort": getattr(st, "agent_hard_effort", "") or "high"}}})]
    for model in dict.fromkeys([getattr(st, "agent_hard_model", "") or "", st.anthropic_model]):
        if not model:
            continue
        for name, extra in shapes:
            t0 = time.time()
            try:
                api = santosh.get_client().messages
                async with api.stream(model=model, max_tokens=2000, messages=[{"role": "user", "content": "2+2? one word"}],
                                      **extra) as s:
                    msg = await s.get_final_message()
                text = "".join(getattr(b, "text", "") for b in msg.content)
                out.append(f"  {model} {name}: OK ({time.time() - t0:.1f} s) {text.strip()[:40]!r}")
            except Exception as e:   # noqa: BLE001 - the error IS the answer here
                out.append(f"  {model} {name}: FAILED {type(e).__name__}: {str(e)[:300]}")
    return out


def pick(only: str = "", limit: int = 0, quick: bool = False) -> list[dict]:
    items = [a for a in SET if (not quick or a.get("quick"))]
    if only:
        want = {x.strip() for x in only.split(",") if x.strip()}
        items = [a for a in items if a["id"] in want]
    return items[:limit] if limit else items


def save(card: dict, label: str = "") -> dict:
    from .run import _dir
    card = {**card, "label": label, "at": int(time.time())}
    name = f"hardcard-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1))
    card["file"] = name
    return card


def saved() -> list[dict]:
    from .run import _dir
    out = []
    for p in sorted(_dir().glob("hardcard-*.json"), reverse=True)[:30]:
        try:
            d = json.loads(p.read_text())
            out.append({"file": p.name, "kind": d.get("kind"), "at": d.get("at"), "label": d.get("label"),
                        "asks": d.get("asks"), "right": d.get("right"), "judge_avg": d.get("judge_avg")})
        except Exception:
            continue
    return out


def lines(card: dict) -> list[str]:
    if card.get("kind") == "free":
        return [f"Hard card (free, set v{card['set']}): spotted hard {card['hard']}/{card['asks']}, pylab in view "
                f"{card['pylab']}/{card['asks']}, own recipe line {card['kind_lines']}/{card['asks']}, research routed "
                f"{card['research_ok']}/{card['research_asks']}"] + \
               [f"  - {r['id']}: not spotted" for r in card["rows"] if not r["hard"]]
    out = [f"Hard card (live, set v{card['set']}): RIGHT {card['right']}/{card['answered']}, pylab used "
           f"{card['pylab_used']}/{card['calc_asks']} calculations, sourced research {card['sourced']}/"
           f"{card['research_asks']}, self-check ran {card['checked']}/{card['answered']}, errors {card['errors']}"
           + (f", judge avg {card['judge_avg']}/10" if card.get("judge_avg") is not None else "")
           + (f", median {card['median_s']} s" if card.get("median_s") is not None else "")]
    if card.get("planned") and card["planned"] > card["asks"]:
        out.append(f"  STOPPED after {card['asks']} of {card['planned']}: every turn failed - the cause is below")
    first = next((r for r in card["rows"] if "error" in r and r.get("log")), None)
    if first:
        out.append("  first failure, the server's own log lines:")
        out += [f"    | {x}" for x in first["log"]]
    for r in card["rows"]:
        if "error" in r:
            out.append(f"  - {r['id']}: ERROR {r['error']}")
        elif not r["right"] or not r["behaviour_ok"]:
            out.append(f"  - {r['id']}: " + "; ".join((["missed " + ", ".join(r["misses"])] if r["misses"] else []) +
                                                      r["behaviour"]))
    return out
