"""HOOLA PROMPTING P12 PROOF (docs/HOOLA_PROMPTING_PLAN.md part 11, row P12): "the P0 card again on everything + ten
real users' four numbers before / after".

P0 measured a HAND-FILLED brief against her raw line - the ceiling of the idea. P12 adds the arm that matters now that
P1-P11 exist: the brief HOOLA fills itself from her raw line (brief.understand + the engine dialect). Three parts:

1. FREE (no model call, runs anywhere): for the web + script asks of the P0 set, how many of the must-have items are
   already in her raw line, in Hoola's own brief (code-only fill), and in the hand-filled brief - so "Hoola's brief
   recovers X% of what a perfect brief adds". Facts kept, nothing invented, no magic phrase. The 10 sections the P0
   card has no engine runner for are listed as NOT COVERED by the live card, with their code checks (every starter
   recipe renders and scores >= 70).
2. LIVE (spends model calls, needs --budget-inr): the P0 live card with a third arm, `hoola`, through the same real
   engines and the same scorer; per section: raw, Hoola's brief, hand brief, and Hoola's share of the ceiling.
3. USERS: up to ten users who share their results (shape only), each with enough judged runs: their four numbers
   (kept rate, redos per kept, rupees per kept, minutes to kept) in the FIRST half of their Hoola Prompting history
   against the SECOND half. Users are numbered, never named. "Before" here means their first prompts, not life before
   Hoola: the ledger only sees prompts made in Hoola Prompting - said on the table.

    python -m app.quality prompt proof                         # free part + users
    python -m app.quality prompt proof --live --budget-inr N [--limit 2] [--section web]
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from . import promptcard as PC
from .prompt_asks import ASKS

PROOF_V = 1
USERS = 10
LIVE_SECTIONS = ("web", "image", "script")


# ---------------------------------------------------------------- Hoola's own brief for a P0 ask
def hoola_text(ask: dict, use_model: bool = False) -> dict[str, Any]:
    """Her raw line -> the brief Hoola fills -> the words the engine gets. use_model=False = code alone (free)."""
    from ..prompting import brief as B
    from ..prompting import dialect as D
    b = B.understand(PC.TENANT, ask["raw"], ask["section"], use_model=use_model)
    out = D.render(b)
    size = ((b.get("slots") or {}).get("size") or {}).get("value", "")
    return {"text": out["run"].get("text") or out["prompt"], "prompt": out["prompt"], "score": B.score(b)["score"],
            "aspect": size if size in ("1:1", "4:5", "9:16", "16:9") else "", "missing": list(b.get("missing") or [])}


def _cover(text: str, must: list[list[str]]) -> float:
    hits = PC.must_hits(text, must)
    return sum(hits) / len(hits) if hits else 0.0


def free_proof(asks: list[dict] | None = None) -> dict[str, Any]:
    items = [a for a in (asks if asks is not None else ASKS) if a["section"] in ("web", "script")]
    rows = []
    for a in items:
        try:
            h = hoola_text(a, use_model=False)
        except Exception as e:      # noqa: BLE001 - one ask Hoola cannot read is a row, not a dead card
            rows.append({"id": a["id"], "section": a["section"], "error": str(e)[:200]})
            continue
        raw, hoo, hand = _cover(a["raw"], a["must"]), _cover(h["prompt"], a["must"]), _cover(a["brief"], a["must"])
        bad_inv = PC.invented(h["prompt"], a["raw"])
        rows.append({"id": a["id"], "section": a["section"], "lang": a["lang"], "raw": round(raw, 3), "hoola": round(hoo, 3),
                     "hand": round(hand, 3), "score": h["score"], "asks_for": len(h["missing"]), "invented": bad_inv,
                     "magic": any(m in h["prompt"].lower() for m in PC.MAGIC)})
    by: dict[str, Any] = {}
    for s in ("web", "script"):
        rr = [r for r in rows if r["section"] == s and "error" not in r]
        if not rr:
            continue
        m = lambda k: round(sum(r[k] for r in rr) / len(rr), 3)   # noqa: E731
        raw, hoo, hand = m("raw"), m("hoola"), m("hand")
        share = round((hoo - raw) / (hand - raw), 2) if hand - raw > 0.01 else None
        by[s] = {"asks": len(rr), "raw": raw, "hoola": hoo, "hand": hand, "share_of_ceiling": share,
                 "invented": sum(1 for r in rr if r["invented"]), "magic": sum(1 for r in rr if r["magic"]),
                 "questions_left": round(sum(r["asks_for"] for r in rr) / len(rr), 1)}
    return {"rows": rows, "sections": by, "errors": sum(1 for r in rows if "error" in r),
            "not_covered": not_covered(),
            "note": "Free part: words only, no engine run. Hoola's brief here is filled by code alone (no model); the "
                    "live card adds the one model call and runs every arm through the real engines."}


def not_covered() -> list[dict[str, Any]]:
    """Sections the live card has no engine runner for - with the code checks that DO run for them."""
    from ..prompting import anatomy as A
    from ..prompting import brief as B
    from ..prompting import dialect as D
    from ..prompting import recipes as R
    out = []
    for sec in A.ORDER:
        if sec in LIVE_SECTIONS:
            continue
        mine = [r for r in R.RECIPES if r["section"] == sec]
        ok = 0
        for r in mine:
            try:
                b = R.use(r["id"], {x["key"]: x["eg"] for x in r["blanks"]})["brief"]
                if D.render(b)["prompt"] and B.score(b)["score"] >= 70:
                    ok += 1
            except Exception:       # noqa: BLE001
                pass
        out.append({"section": sec, "label": A.SECTIONS[sec]["label"], "recipes": len(mine), "recipes_ok": ok,
                    "why": "no engine runner in the prompt card yet - code checks only"})
    return out


# ---------------------------------------------------------------- live: the P0 card with Hoola's own arm
async def _run_hoola(ask: dict) -> dict[str, Any]:
    from .. import usage
    t0 = time.time()
    with usage.run_meter() as acc:
        try:
            h = await asyncio.to_thread(hoola_text, ask, True)       # the one small model call that fills the brief
            a2 = {**ask, "hoola_text": h["text"], "hoola_aspect": h["aspect"]}
            sec = ask["section"]
            if sec == "web":
                text, depth = await asyncio.to_thread(PC._web_plan, h["text"])
                out = {"text": text, "engine": depth, "given": h["text"]}
            elif sec == "script":
                from ..create import service as CS
                out = {"text": await CS.write("script", h["text"]), "given": h["text"]}
            else:
                from .. import photogen
                from .run import _dir
                made = await asyncio.to_thread(photogen.make, h["text"], None, a2["hoola_aspect"], "fast")
                folder = _dir() / "promptcard-img"
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / f"{ask['id']}-hoola.png"
                path.write_bytes(made["png"])
                read = await PC._read_picture(made["png"], ask["must"])
                out = {"answers": read["a"], "file": str(path), "flat_inr": float(made.get("cost_inr") or 0)}
        except Exception as e:      # noqa: BLE001
            return {"error": str(e)[:240], "inr": round(acc["usd"] * usage.usd_inr(), 2), "seconds": round(time.time() - t0, 1)}
    inr = acc["usd"] * usage.usd_inr() + (out.get("flat_inr") or 0)
    sc = PC.score_image(ask, out["answers"]) if ask["section"] == "image" else PC.score_text(ask, out["text"], out["given"], out.get("engine"))
    return {**sc, "inr": round(inr, 2), "seconds": round(time.time() - t0, 1)}


async def live_proof(asks: list[dict] | None = None, budget_inr: float = 0.0) -> dict[str, Any]:
    if budget_inr <= 0:
        raise ValueError("a live proof card needs --budget-inr N (the whole card's rupee ceiling)")
    from .. import usage
    usage.install()
    usage.bind(tenant=PC.TENANT, feature="quality")
    items = asks if asks is not None else ASKS
    order: list[dict] = []
    by = {s: [a for a in items if a["section"] == s] for s in LIVE_SECTIONS}
    for i in range(max((len(v) for v in by.values()), default=0)):
        order += [by[s][i] for s in LIVE_SECTIONS if i < len(by[s])]
    rows, spent, stopped = [], 0.0, ""
    for a in order:
        need = 3 * PC.ASSUMED_INR[a["section"]]
        if spent + need > budget_inr:
            stopped = f"budget: Rs {round(spent, 2)} spent of {budget_inr}"
            continue
        raw, hand, hoo = await PC._arm(a, "raw"), await PC._arm(a, "brief"), await _run_hoola(a)
        spent += sum(x.get("inr", 0.0) for x in (raw, hand, hoo))
        row = {"id": a["id"], "section": a["section"], "lang": a["lang"], "raw": raw, "brief": hand, "hoola": hoo}
        if all("error" not in x for x in (raw, hand, hoo)):
            row["gain"] = round(hand["score"] - raw["score"], 1)
            row["hoola_gain"] = round(hoo["score"] - raw["score"], 1)
        rows.append(row)
    secs = {}
    for s in LIVE_SECTIONS:
        done = [r for r in rows if r["section"] == s and "gain" in r]
        if not done:
            secs[s] = {"pairs": 0}
            continue
        g = round(sum(r["gain"] for r in done) / len(done), 1)
        hg = round(sum(r["hoola_gain"] for r in done) / len(done), 1)
        secs[s] = {"pairs": len(done), "hand_gain": g, "hoola_gain": hg,
                   "share_of_ceiling": round(hg / g, 2) if g > 1 else None,
                   "hoola_wins": sum(1 for r in done if r["hoola_gain"] > PC.WIN_MARGIN),
                   "hoola_losses": sum(1 for r in done if r["hoola_gain"] < -PC.WIN_MARGIN)}
    return {"kind": "live", "sections": secs, "rows": rows, "inr": round(spent, 2), "budget_inr": budget_inr, "stopped": stopped}


# ---------------------------------------------------------------- ten real users: first half vs second half
def users_table(days: int = 365) -> dict[str, Any]:
    from ..db import as_utc
    from ..prompting import ledger as L
    L.ensure_table()
    rows = L._rows(None, days)
    by: dict[str, list] = {}
    for r in rows:
        if r.tenant_id == PC.TENANT:
            continue
        by.setdefault(r.tenant_id, []).append(r)
    ready = []
    for t, rr in by.items():
        rr.sort(key=lambda r: as_utc(r.handed_at))
        graded = [r for r in rr if r.grade in L.GRADES and r.grade != "unused"]
        if len(graded) >= 2 * L.MIN_RUNS:
            ready.append((len(graded), rr))
    ready.sort(key=lambda x: -x[0])
    out = []
    for n, (_, rr) in enumerate(ready[:USERS], 1):
        half = len(rr) // 2
        out.append({"user": f"User {n}", "runs": len(rr), "before": L._four(rr[:half]), "after": L._four(rr[half:])})
    return {"users": out, "have": len(ready), "want": USERS, "min_graded": 2 * L.MIN_RUNS,
            "note": "Before = the first half of each user's prompts made in Hoola Prompting, after = the second half. The "
                    "ledger only sees prompts made in Hoola Prompting, so this is not 'life before Hoola'. Only users who "
                    "share their results (shape only) are counted; users are numbered, never named."}


def proof(asks: list[dict] | None = None) -> dict[str, Any]:
    return {"kind": "proof", "v": PROOF_V, "at": int(time.time()), "free": free_proof(asks), "users": users_table(),
            "live": last_live()}


def save(card: dict, label: str = "") -> dict:
    from .run import _dir
    card = {**card, "label": label}
    name = f"promptproof-{card.get('kind', 'proof')}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1))
    card["file"] = name
    return card


def last_live() -> dict[str, Any] | None:
    from .run import _dir
    for p in sorted(_dir().glob("promptproof-live-*.json"), reverse=True)[:1]:
        try:
            d = json.loads(p.read_text())
            return {"file": p.name, "sections": d.get("sections"), "inr": d.get("inr"), "stopped": d.get("stopped")}
        except (OSError, ValueError):
            return None
    return None


def lines(card: dict) -> list[str]:
    out = []
    if card.get("kind") == "live":
        out.append(f"Prompt PROOF (LIVE): Rs {card['inr']} of {card['budget_inr']}" + (f" - {card['stopped']}" if card.get("stopped") else ""))
        for s, d in card["sections"].items():
            if not d.get("pairs"):
                out.append(f"  {s.upper():6} no finished rows")
                continue
            out.append(f"  {s.upper():6} {d['pairs']} rows: hand brief +{d['hand_gain']}, Hoola's brief +{d['hoola_gain']}"
                       + (f" ({round(d['share_of_ceiling'] * 100)}% of the ceiling)" if d.get("share_of_ceiling") is not None else "")
                       + f"; Hoola won {d['hoola_wins']}, lost {d['hoola_losses']}")
        return out
    f = card["free"]
    out.append(f"Prompt PROOF (free, v{card['v']}): Hoola's own brief vs her raw line vs the hand-filled brief")
    for s, d in f["sections"].items():
        out.append(f"  {s.upper():6} must items in the prompt: raw {round(d['raw'] * 100)}%, Hoola {round(d['hoola'] * 100)}%, "
                   f"hand {round(d['hand'] * 100)}%" + (f" = {round(d['share_of_ceiling'] * 100)}% of what a perfect brief adds"
                                                         if d["share_of_ceiling"] is not None else "")
                   + f"; invented {d['invented']}, magic {d['magic']}, questions left {d['questions_left']}")
    if f["errors"]:
        out.append(f"  {f['errors']} asks Hoola could not read")
    for n in f["not_covered"]:
        out.append(f"  {n['label']}: {n['why']} ({n['recipes_ok']}/{n['recipes']} recipes render and score >= 70)")
    u = card["users"]
    out.append(f"  users with enough results: {u['have']} of {u['want']} (each needs {u['min_graded']} judged)")
    for x in u["users"]:
        b, a = x["before"], x["after"]
        out.append(f"    {x['user']}: kept {b['kept_rate']}% -> {a['kept_rate']}%, redos per kept {b['redos_per_kept']} -> "
                   f"{a['redos_per_kept']}, Rs per kept {b['inr_per_kept']} -> {a['inr_per_kept']}, minutes {b['minutes_to_kept']} -> {a['minutes_to_kept']}")
    if card.get("live"):
        out.append(f"  last live proof: {card['live']['file']} (Rs {card['live']['inr']})")
    else:
        out.append("  no live proof yet: python -m app.quality prompt proof --live --budget-inr N [--limit 2]")
    return out
