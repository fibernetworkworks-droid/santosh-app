"""v0.478 R7 THE RUN-OFF - the R0 research card run across the engines, on the same topics, scored the same way, with a rule in CODE that decides the default.

Plan: `docs/RESEARCH_PRO_PLAN.md` R7: "the honest answer to 'which model researches perfectly'". Nothing in this module says which engine is best; it builds the
measurement and the rule, and it REFUSES to name a winner the numbers do not support. Run live it spends real model, web and vendor money, so it needs an explicit
`--budget-inr` (and a vendor engine runs only if every R6 gate is open).

THE SAME FOR EVERY ENGINE (otherwise the table compares setups, not engines)
  - the same asks (`research_asks.py`, incl. the 3 TRAPS whose subject was invented), the same sub-questions (the deterministic plan templates, no model),
    the same source policy, the same budgets;
  - the engine gathers -> a DOSSIER (Hoola's own loop, or a vendor re-checked by Hoola's own fetch) -> the SAME writer prompt and the same model writes the
    report from it (one fix round on the R3 claim check, like the product) -> the SAME scorer (`researchcard.score_report` + `claims.check_report`) reads the
    report against the pages / search excerpts / calculations that engine's run really fetched;
  - the same cost meter (model calls counted per run + the vendor line: the price she set, or the vendor's own reported cost);
  - the runs are INTERLEAVED (ask 1 on every engine, then ask 2 ...), so if the budget runs out every engine has the same coverage.
  Left out on purpose: the `first_stop_tool` check (it belongs to the whole agent, not to a research engine). `calc_in_pylab` stays: a vendor cannot compute in Hoola's
  sandbox, so its derived figures are unsupported - a real difference, shown as its own column (`right_non_calc` is shown beside `right` so it can be read both ways).

THE RULE (constants below; `decide`)
  1. An engine is ELIGIBLE only if it answered at least MIN_ANSWERED_SHARE of the asks it was given AND it did not invent a confident answer to ANY trap.
  2. If the incumbent (Hoola's own) is eligible, a challenger replaces it only by leading on `right` by at least MARGIN (15 points: with ~20 asks and one run each, a
     smaller gap is within what one re-run of the same engine can move); among challengers that clear the margin, the highest `right`, ties within 2 points -> the cheaper.
  3. If the incumbent is NOT eligible, the best eligible engine is recommended the same way.
  4. Her verdicts (`research verdict <ask> right|wrong --engine X`) OUTRANK every check: a row she marked wrong counts wrong whatever the checks said.
  5. No eligible engine / no clear lead = NO WINNER; the default stays where it is. `--apply` is a separate act of hers; nothing writes the default by itself.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import statistics
import time
from typing import Any, Awaitable, Callable

from ..research import bill, claims as C
from ..research import engine as E
from ..research import vendors as V
from . import researchcard as RC
from .research_asks import ASKS, RESEARCH_SET_V

log = logging.getLogger("santosh.quality.runoff")

RUNOFF_V = 1
MARGIN = 0.15
TIE = 0.02
MIN_ANSWERED_SHARE = 0.8
INCUMBENT = "hoola"
QUALITY_TENANT = "__quality__"

WRITER_SYSTEM = (
    "You write a research report for an Indian small-business owner from a RESEARCH DOSSIER, and from nothing else.\n"
    "Rules: every figure you write is one a note's own words carry (cite that note's source as [n]) or one a calculation in the dossier printed - never a number "
    "from memory. A note marked NOT VERIFIED, or whose figure is not in its quoted words, is stated as unconfirmed or left out. Cite only the listed sources, as "
    "[n]. Begin with a 4-6 line summary with the key numbers. Say as of when the figures are. Keep a section 'What could not be confirmed' that carries every NOT "
    "CONFIRMED item of the dossier. End with 'Sources:' and one line per source you cited: [n] title or site - link - date. If the dossier shows the thing asked "
    "about could not be found, say so plainly and give no figure for it. Write in the language of the question.")


def goals_for(ask: dict) -> list[str]:
    """The same sub-questions for every engine: the deterministic plan templates (no model call), plus the working-out question when the ask needs figures."""
    from ..agent import research_plan as P
    return list(P._fallback(P.assess(ask["text"]))["sub_questions"])[:6]


# ---------------------------------------------------------------- the writer (identical for every engine)
async def default_write(dossier: dict, ask: dict, llm) -> tuple[str, int, list[str]]:
    """(report, fix rounds used, claim findings left). One fix round when the claim check finds something, like the product."""
    text = E.render(dossier)

    async def once(extra: str = "") -> str:
        user = f"QUESTION: {ask['text']}\n\n{text}" + (f"\n\n[System: your draft had problems - fix them and write the whole report again]\n{extra}" if extra else "")
        blocks, _ = await llm(WRITER_SYSTEM, [{"role": "user", "content": [{"type": "text", "text": user}]}], [], 6000)
        return " ".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text").strip()
    report = await once()
    found = C.check_report(report, dossier)
    rounds = 0
    if found:
        report, rounds = await once("\n".join("- " + x for x in found)), 1
        found = C.check_report(report, dossier)
    return report, rounds, found


# ---------------------------------------------------------------- one engine x one ask
def _real_deps(engine: str, tenant: str):
    from ..agent import research_tools as RT
    from ..agent.tools import Ctx
    from ..config import get_settings
    return RT._deps(Ctx(tenant_id=tenant, conversation_id="runoff", actor="owner"), get_settings())


async def run_one(engine: str, ask: dict, tenant: str = QUALITY_TENANT, make_deps: Callable[[str, str], Any] | None = None,
                  write: Callable[..., Awaitable[tuple[str, int, list[str]]]] | None = None) -> dict[str, Any]:
    """Run one ask through one engine and score the report. Never raises: a failure is an ERROR row with its reason."""
    from .. import usage
    from ..config import get_settings
    from ..research import store
    st = get_settings()
    t0 = time.time()
    base = {"engine": engine, "id": ask["id"], "kind": ask["kind"], "calc": bool(ask.get("calc"))}
    deps = (make_deps or _real_deps)(engine, tenant)
    docs: list[dict] = []
    inner_fetch, inner_search = deps.fetch, deps.search

    async def fetch(url):                                    # every page the engine (or Hoola's verification) really read becomes evidence for the scorer
        got = await inner_fetch(url)
        docs.append({"tool": "open_website", "calc": False, "text": str(got.get("text") or ""), "urls": [str(got.get("url") or url)]})
        return got

    async def search(goal, qs):
        res = await inner_search(goal, qs)
        for r in res or []:
            docs.append({"tool": "web_sources", "calc": False, "text": str(r.get("excerpt") or ""), "urls": [str(r.get("url") or "")]})
        return res
    deps.fetch, deps.search = fetch, search
    meter = bill.Meter(tenant)
    deps.afford, deps.cost = meter.afford, meter.breakdown
    base_step = deps.step

    def step(goal, kind, detail):
        if kind == "search":
            meter.counts["searches"] += 1
        elif kind == "read":
            meter.counts["fetches"] += 1
        base_step(goal, kind, detail)
    deps.step = step
    goals = goals_for(ask)
    pol = E.Policy.from_settings(st, bg=True)
    try:
        usage.bind(tenant, "research")
        with usage.run_meter(meter.acc):
            if engine == "hoola":
                d = await E.run(ask["text"], goals, pol, deps)
            else:
                d = await V.gather(engine, ask["text"], goals, pol, deps, meter, st)
            report, fixes, left = await (write or (lambda dos, a: default_write(dos, a, deps.llm)))(d, ask)
    except V.StoppedByHer:
        return {**base, "error": "stopped", "right": False, "inr": meter.total_inr()}
    except Exception as e:       # noqa: BLE001 - one broken run is a row, not a dead card
        log.info("runoff %s/%s failed: %s", engine, ask["id"], e)
        _ledger(tenant, ask, goals, None, meter)
        return {**base, "error": f"{type(e).__name__}: {str(e)[:200]}", "right": False, "inr": meter.total_inr(), "seconds": round(time.time() - t0, 1)}
    for t in d.get("tasks", []):
        for c in t.get("calcs", []):
            docs.append({"tool": "pylab", "calc": True, "text": c.get("output", ""), "urls": []})
    cost = meter.breakdown()
    d["cost"] = cost
    _ledger(tenant, ask, goals, d, meter)
    a2 = {k: v for k, v in ask.items() if k != "uses"}       # first_stop_tool belongs to the whole agent, not to a research engine
    tools = ["research_run"] + (["pylab"] if any(c.get("ok") for t in d.get("tasks", []) for c in t.get("calcs", [])) else [])
    row = RC.score_report(report, docs, a2, tools, [s["url"] for s in d.get("sources", []) if s.get("read")])
    row["checks"]["claims_supported"] = not left
    if left:
        row["right"] = False
        row["failed"] = [*row["failed"], "claims_supported"]
        row["misses"] = [*row["misses"], "claims_supported: " + "; ".join(left[:3])]
    return {**base, **row, "inr": cost["total_inr"], "seconds": round(time.time() - t0, 1), "minutes": round((time.time() - t0) / 60, 2),
            "model_calls": cost.get("model_calls"), "vendor_known": (cost.get("vendor") or {}).get("known"), "pages": d["stats"]["pages_read"],
            "verified_notes": d["stats"]["verified_notes"], "notes": d["stats"]["notes"], "field_confidence": d["stats"].get("confidence"),
            "claim_findings": left, "fix_rounds": fixes, "stop_reason": d.get("stop_reason"), "report": report[:1500]}


def _ledger(tenant: str, ask: dict, goals: list[str], dossier: dict | None, meter) -> None:
    """A run-off run is a ledger row, so the budget (the day ceiling set for the card) holds across the whole card."""
    try:
        from ..research import store
        rid = store.create(tenant, "runoff", ask["text"], goals, {"runoff": True, "ask": ask["id"]})
        store.finish(rid, "done", dossier, cost=meter.breakdown())
    except Exception:       # noqa: BLE001
        log.debug("runoff ledger failed", exc_info=True)


# ---------------------------------------------------------------- the card
async def run_card(engines: list[str], asks: list[dict] | None = None, budget_inr: float = 0.0, k: int = 1, tenant: str = QUALITY_TENANT,
                   make_deps=None, write=None, progress: Callable[[str], None] = lambda s: None) -> dict[str, Any]:
    from ..config import get_settings
    if budget_inr <= 0:
        raise ValueError("a live run-off spends real money: pass --budget-inr N (rupees for the WHOLE card)")
    st = get_settings()
    items = asks or ASKS
    not_run: dict[str, str] = {}
    live = []
    for e in engines:
        ok, why = V.check(e, "", st)
        if ok:
            live.append(e)
        else:
            not_run[e] = why
    was_day, was_bg, was_gate = st.research_daily_inr, st.research_background, st.research_plan_gate
    st.research_daily_inr, st.research_background, st.research_plan_gate = float(budget_inr), False, False
    rows: list[dict] = []
    exhausted = ""
    try:
        for rep in range(max(1, k)):
            for ask in items:                                # interleaved: every engine gets ask n before any gets ask n+1
                for e in live:
                    try:
                        bill.preflight(tenant)
                    except bill.ResearchCapped as err:
                        exhausted = str(err)
                        break
                    progress(f"{e} / {ask['id']} (rep {rep + 1})")
                    r = await run_one(e, ask, tenant, make_deps, write)
                    r["rep"] = rep
                    rows.append(r)
                if exhausted:
                    break
            if exhausted:
                break
    finally:
        st.research_daily_inr, st.research_background, st.research_plan_gate = was_day, was_bg, was_gate
    planned = {e: len(items) * max(1, k) for e in live}
    table = build_table(rows, planned, not_run)
    card = {"kind": "runoff", "v": RUNOFF_V, "set": RESEARCH_SET_V, "rubric": RC.RUBRIC_V, "engines": engines, "k": k, "budget_inr": budget_inr,
            "budget_exhausted": exhausted, "asks": len(items), "rows": rows, "table": table,
            "spent_inr": round(sum(r.get("inr", 0.0) for r in rows), 2), "config": _config_snapshot(st)}
    card["decision"] = decide(table)
    return card


def _config_snapshot(st) -> dict[str, Any]:
    return {k: getattr(st, k) for k in ("research_run_cap_inr", "research_daily_inr", "research_parallel_processor", "research_exa_effort", "research_openai_model",
                                        "research_linkup_depth", "research_linkup_mode", "research_tasks_max", "research_steps", "research_pages_total",
                                        "research_rounds", "anthropic_model") if hasattr(st, k)}


# ---------------------------------------------------------------- the table
def _eff_right(r: dict, engine: str) -> bool:
    v = RC.verdict_for(r["id"], engine)
    return v["verdict"] == "right" if v else bool(r.get("right"))


def build_table(rows: list[dict], planned: dict[str, int], not_run: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for e, why in not_run.items():
        out[e] = {"not_run": why}
    for e in planned:
        mine = [r for r in rows if r["engine"] == e]
        ok = [r for r in mine if "error" not in r]
        topics = [r for r in ok if r["kind"] == "topic"]
        traps = [r for r in ok if r["kind"] == "trap"]
        non_calc = [r for r in topics if not r.get("calc")]
        per: dict[str, list[int]] = {}
        for r in topics:
            for k, v in (r.get("checks") or {}).items():
                a = per.setdefault(k, [0, 0])
                a[0] += int(bool(v))
                a[1] += 1
        mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else None          # noqa: E731
        judged = [r["judge"]["score"] for r in ok if r.get("judge")]
        out[e] = {"planned": planned[e], "answered": len(ok), "errors": len(mine) - len(ok),
                  "right": sum(_eff_right(r, e) for r in ok), "right_share": mean([float(_eff_right(r, e)) for r in ok]),
                  "right_non_calc": mean([float(_eff_right(r, e)) for r in non_calc]), "non_calc_n": len(non_calc),
                  "trap_right": sum(_eff_right(r, e) for r in traps), "traps": len(traps),
                  "per_check": {k: v for k, v in per.items()}, "claims_pass": mean([float(r["checks"].get("claims_supported", True)) for r in topics]),
                  "primary_avg": mean([r["primary_share"] for r in topics if r.get("primary_share") is not None]),
                  "corroborated_avg": mean([r["corroborated_share"] for r in topics if r.get("corroborated_share") is not None]),
                  "median_minutes": round(statistics.median([r["minutes"] for r in ok]), 1) if ok else None,
                  "inr_per_report": round(sum(r["inr"] for r in ok) / len(ok), 1) if ok else None, "inr_total": round(sum(r.get("inr", 0.0) for r in mine), 1),
                  "judge_avg": round(sum(judged) / len(judged), 1) if judged else None,
                  "hers": sum(1 for r in ok if RC.verdict_for(r["id"], e) is not None),
                  "errors_seen": sorted({r["error"][:80] for r in mine if "error" in r})[:3]}
    return out


# ---------------------------------------------------------------- the rule
def decide(table: dict[str, Any], incumbent: str = INCUMBENT) -> dict[str, Any]:
    """A RECOMMENDATION from the table by the rule in the module doc - never an action. winner None = nothing to change."""
    why: list[str] = []
    eligible: dict[str, dict] = {}
    for e, r in table.items():
        if r.get("not_run"):
            why.append(f"{e}: not run - {r['not_run']}")
        elif r["planned"] and r["answered"] < MIN_ANSWERED_SHARE * r["planned"]:
            why.append(f"{e}: answered {r['answered']} of {r['planned']} - too few to judge" + (f" (errors: {'; '.join(r['errors_seen'])})" if r["errors_seen"] else ""))
        elif r["traps"] and r["trap_right"] < r["traps"]:
            why.append(f"{e}: gave a confident answer to {r['traps'] - r['trap_right']} of {r['traps']} thing(s) that do not exist - it cannot be the default")
        elif r["right_share"] is None:
            why.append(f"{e}: nothing scored")
        else:
            eligible[e] = r
    rule = {"margin": MARGIN, "tie": TIE, "min_answered_share": MIN_ANSWERED_SHARE, "incumbent": incumbent}
    if not eligible:
        return {"winner": None, "why": why + ["no engine is eligible - the default stays where it is"], "rule": rule}
    cost = lambda e: eligible[e]["inr_per_report"] if eligible[e]["inr_per_report"] is not None else 1e9       # noqa: E731
    share = lambda e: eligible[e]["right_share"]                                                               # noqa: E731
    if incumbent in eligible:
        beat = [e for e in eligible if e != incumbent and share(e) - share(incumbent) >= MARGIN - 1e-9]
        if not beat:
            gaps = ", ".join(f"{e} {share(e) - share(incumbent):+.0%}" for e in eligible if e != incumbent)
            return {"winner": None, "why": why + [f"{incumbent} stays: no challenger leads it by {MARGIN:.0%} on right ({gaps or 'no challenger ran'})"], "rule": rule}
        best = max(share(e) for e in beat)
        close = sorted((e for e in beat if best - share(e) <= TIE + 1e-9), key=lambda e: (cost(e), -share(e)))
        w = close[0]
        return {"winner": w, "why": why + [f"{w} leads {incumbent} by {share(w) - share(incumbent):.0%} on right (>= {MARGIN:.0%})"
                                           + (f"; among {len(close)} within {TIE:.0%} of the best it is the cheapest (Rs {cost(w):.0f} a report)" if len(close) > 1 else "")], "rule": rule}
    best = max(share(e) for e in eligible)
    close = sorted((e for e in eligible if best - share(e) <= TIE + 1e-9), key=lambda e: (cost(e), -share(e)))
    w = close[0]
    return {"winner": w, "why": why + [f"{incumbent} is not eligible; {w} has the best right share ({share(w):.0%})"], "rule": rule}


def rebuild(card: dict) -> tuple[dict, dict]:
    """(table, decision) for a saved card with her CURRENT verdicts - they outrank every check, and she may have given more since the run."""
    old = card["table"]
    planned = {e: r["planned"] for e, r in old.items() if not r.get("not_run")}
    not_run = {e: r["not_run"] for e, r in old.items() if r.get("not_run")}
    table = build_table(card["rows"], planned, not_run)
    return table, decide(table)


def apply_default(decision: dict, card_file: str = "") -> dict[str, Any]:
    """Write the run-off's winner as the default ("auto"). Refuses when there is no winner. Her act: `research runoff --apply`."""
    if not decision.get("winner"):
        raise ValueError("there is no winner to apply: " + "; ".join(decision.get("why") or ["the card decided nothing"]))
    d = {"engine": decision["winner"], "decided_at": time.strftime("%Y-%m-%d %H:%M"), "from_card": card_file, "why": decision.get("why"), "rule": decision.get("rule")}
    V.default_file().write_text(json.dumps(d, ensure_ascii=False, indent=1))
    return d


def reset_default() -> bool:
    p = V.default_file()
    if p.exists():
        p.unlink()
        return True
    return False


# ---------------------------------------------------------------- free: can the run-off run, and what would it cost
def check_free(engines: list[str], n_asks: int | None = None, k: int = 1) -> dict[str, Any]:
    from ..config import get_settings
    st = get_settings()
    n = n_asks if n_asks is not None else len(ASKS)
    rows = []
    for e in engines:
        ok, why = V.check(e, "", st)
        if e == "hoola":
            m = bill.measured_per_goal(QUALITY_TENANT)
            per = (m["per_goal_inr"] * 5) if m else None
            note = "measured from the __quality__ runs" if m else "no measured cost yet - unknown until one live run"
        else:
            per = float(getattr(st, V.REGISTRY[e]["price"], 0.0)) if e in V.REGISTRY and V.REGISTRY[e].get("price") else None
            note = "the price you set (an estimate) + Hoola's own page checks and writer calls (not included)"
        rows.append({"engine": e, "ready": ok, "why_not": why, "per_report_inr": per, "note": note,
                     "card_inr": round(per * n * k, 0) if per else None})
    return {"engines": rows, "asks": n, "k": k, "set": RESEARCH_SET_V, "rubric": RC.RUBRIC_V}


def check_lines(c: dict) -> list[str]:
    out = [f"Run-off check (free): {c['asks']} asks x {c['k']} run(s), set v{c['set']}, rubric v{c['rubric']}. A live run needs --budget-inr N (rupees for the whole card)."]
    for r in c["engines"]:
        cost = f"~Rs {r['card_inr']:,.0f} for the engine alone ({r['note']})" if r["card_inr"] else f"cost unknown - {r['note']}"
        out.append(f"  {r['engine']:<10} " + ("READY" if r["ready"] else "NOT READY: " + r["why_not"]) + f"  | {cost}")
    out.append("  (the writer + Hoola's own checking of every claim cost model rupees on top, for EVERY engine; the first live run measures them)")
    return out


# ---------------------------------------------------------------- saving + printing
def save(card: dict, label: str = "") -> dict:
    from .run import _dir
    card = {**card, "label": label, "at": int(time.time())}
    name = f"researchrun-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1, default=str))
    card["file"] = name
    return card


def saved() -> list[dict]:
    from .run import _dir
    out = []
    for p in sorted(_dir().glob("researchrun-*.json"), reverse=True)[:20]:
        try:
            d = json.loads(p.read_text())
            out.append({"file": p.name, "at": d.get("at"), "label": d.get("label"), "engines": d.get("engines"), "spent_inr": d.get("spent_inr"),
                        "winner": (d.get("decision") or {}).get("winner")})
        except Exception:       # noqa: BLE001
            continue
    return out


def latest() -> dict | None:
    from .run import _dir
    for p in sorted(_dir().glob("researchrun-*.json"), reverse=True):
        try:
            d = json.loads(p.read_text())
            d["file"] = p.name
            return d
        except Exception:       # noqa: BLE001
            continue
    return None


def lines(card: dict) -> list[str]:
    t = card["table"]
    out = [f"Research run-off (set v{card['set']}, rubric v{card['rubric']}, {card['asks']} asks x {card['k']}): spent Rs {card.get('spent_inr', 0)} of a Rs {card.get('budget_inr', 0)} budget"
           + (f" - BUDGET RAN OUT, the table is partial ({card['budget_exhausted']})" if card.get("budget_exhausted") else "")]
    for e, r in t.items():
        if r.get("not_run"):
            out.append(f"  {e:<10} NOT RUN - {r['not_run']}")
            continue
        pc = r["per_check"]
        out.append(f"  {e:<10} right {r['right']}/{r['answered']} ({(r['right_share'] or 0):.0%}), without the calc asks {('%.0f%%' % (100 * r['right_non_calc'])) if r['right_non_calc'] is not None else '-'}"
                   f" | traps {r['trap_right']}/{r['traps']} | claims backed {('%.0f%%' % (100 * r['claims_pass'])) if r['claims_pass'] is not None else '-'}"
                   f" | primary {r['primary_avg']} corroborated {r['corroborated_avg']} | median {r['median_minutes']} min | Rs {r['inr_per_report']} a report"
                   + (f" | judge {r['judge_avg']}/10" if r["judge_avg"] is not None else "") + (f" | errors {r['errors']}" if r["errors"] else "")
                   + (f" | her verdicts on {r['hers']}" if r["hers"] else ""))
        weak = sorted(((v[0] / v[1], k) for k, v in pc.items() if v[1] and v[0] < v[1]))[:3]
        if weak:
            out.append("             weakest checks: " + ", ".join(f"{k} {int(100 * s)}%" for s, k in weak))
    d = card.get("decision") or {}
    out.append("  DECISION: " + (f"recommend {d['winner']} as the default" if d.get("winner") else "no winner - the default stays where it is"))
    out += [f"    - {w}" for w in d.get("why") or []]
    out.append("  (a recommendation only: `python -m app.quality research runoff --apply` is a separate act; her verdicts outrank every number above)")
    return out
