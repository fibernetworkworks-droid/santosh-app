"""v0.475 R4 LAMBA KAAM - research that runs in the BACKGROUND, survives a restart, tells her what it is doing, and reports itself.

A real report is 10-40 minutes of searching and reading; inside one chat turn it was capped at 900 s and died with the process. Here
`research_run` PERSISTS a run (`research/store.py`) and returns at once; the worker slot (`tick`, ~20 s) starts it and picks it up again
if it stopped heartbeating (a pm2 restart, a crash) FROM ITS CHECKPOINT - the goals already finished are kept, only the rest of the round
is run, and the clock already used stays used. The same pattern as the background agent crews (agent/team.py).

  narration   every search / read / note / calc / finish becomes a live step line carrying the goal's number ("Goal 3/6 - reading
              cbse.gov.in"), in her language (the plan card knew it); each finished goal updates the job's progress line.
  finish      one `research_run` event -> kaamwatch -> kaam_followup -> a WAKE turn: the real brain gets the dossier by the tool
              `research_status result`, writes the report in her words, and the R3 check runs on it (the wake turn is treated as a
              hard, held answer). She is told once, at the start, and once, with the report.
  stop        `research_status stop` (Rokiye) - the run ends at its next step and keeps what it found.
  what is lost on a restart: a goal that was mid-way loses its partial notes and is run again from its start; finished goals are not.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from ..db import now
from ..events import bus
from . import bill
from . import engine as E
from . import store

log = logging.getLogger("santosh.research.runner")

REPORT_MARK = "<research_report_due"
STATS = {"started": 0, "resumed": 0, "done": 0, "failed": 0, "stopped": 0}
_RUNNING: set[str] = set()
_BG: set = set()
_deps_factory = None            # tests replace it: (ctx, settings) -> E.Deps


def is_report_due(text: str) -> bool:
    return REPORT_MARK in str(text or "")


# ---------------------------------------------------------------- narration in her language
_LINES = {
    "search": ("{g}/{n} - khoj raha hoon: {d}", "{g}/{n} - searching: {d}"),
    "read": ("{g}/{n} - padh raha hoon: {d}", "{g}/{n} - reading: {d}"),
    "note": ("{g}/{n} - {d} se baat note ki", "{g}/{n} - noted a finding from {d}"),
    "calc": ("{g}/{n} - hisaab kar raha hoon: {d}", "{g}/{n} - working out: {d}"),
    "finish": ("{g}/{n} - yeh sawal poora", "{g}/{n} - this question is done"),
    "wait": ("{g}/{n} - intezaar: {d}", "{g}/{n} - waiting: {d}"),          # v0.477 R6 a vendor's run is going on
}


def line(kind: str, hi: bool, g: int, n: int, detail: str) -> str:
    tpl = _LINES.get(kind, _LINES["search"])[0 if hi else 1]
    return tpl.format(g=g, n=n, d=(detail or "")[:60])


def progress_text(p: dict, hi: bool) -> str:
    if hi:
        return f"{p.get('goals_done', 0)}/{p.get('goals_total', 0)} sawal poore, {p.get('pages', 0)} pages padhe, {p.get('notes', 0)} baatein note"
    return f"{p.get('goals_done', 0)}/{p.get('goals_total', 0)} questions done, {p.get('pages', 0)} pages read, {p.get('notes', 0)} findings noted"


# ---------------------------------------------------------------- start / stop / status
def start(tenant: str, conv: str, question: str, goals: list[str], over: dict | None = None, hi: bool = True,
          asked: list[str] | None = None, engine: str = "hoola") -> str:
    rid = store.create(tenant, conv, question, goals, {"over": over or {}, "hi": hi, "asked": asked or [], "engine": engine or "hoola"})
    STATS["started"] += 1
    _publish(conv, rid, question, "queued", "shuru ho raha hai" if hi else "starting")
    return rid


def stop(tenant: str, run_id: str) -> str:
    v = store.get(run_id)
    if v is None or v["tenant"] != tenant:
        return "missing"
    if v["status"] in ("done", "failed", "stopped"):
        return v["status"]
    store.set_status(run_id, "stopped", "owner ne roka")
    _RUNNING.discard(run_id)
    STATS["stopped"] += 1
    _publish(v["conv"], run_id, v["question"], "stopped", "owner ne rok diya")
    return "stopped"


def _publish(conv: str, rid: str, question: str, status: str, say: str, stage: str = "") -> None:
    try:       # kaamwatch shapes it -> kaam_followup (a finished one wakes the brain to write the report)
        bus.publish(conv, "research_run", {"id": rid, "number": f"research {rid[-4:]}", "name": question[:60], "status": status,
                                           "say": say, **({"stage": stage} if stage else {})})
    except Exception:       # noqa: BLE001
        log.debug("research publish failed", exc_info=True)


# ---------------------------------------------------------------- one run
def _build_deps(tenant: str, conv: str, run_id: str, hi: bool, settings, total: int = 0, base: dict | None = None) -> E.Deps:
    from ..agent.tools import Ctx
    if _deps_factory is not None:
        d = _deps_factory(Ctx(tenant_id=tenant, conversation_id=conv, actor="owner"), settings)
    else:
        from ..agent import research_tools as RT
        d = RT._deps(Ctx(tenant_id=tenant, conversation_id=conv, actor="owner"), settings)
    meter = bill.Meter(tenant, run_id, base=base)          # v0.476 R5: a restarted run starts from what it had already spent
    prog = {"goals_total": total, "goals_done": 0, "pages": 0, "notes": 0, "now": "", "round": 1}
    last = {"t": 0.0}
    order: dict[str, int] = {}

    def num(goal: str) -> int:
        return order.setdefault(goal, len(order) + 1)

    def step(goal: str, kind: str, detail: str) -> None:
        if kind == "search":
            meter.counts["searches"] += 1
        elif kind == "read":
            meter.counts["fetches"] += 1
        g, n = num(goal), max(prog["goals_total"], len(order))
        txt = line(kind, hi, g, n, detail)
        prog["now"] = txt
        try:
            bus.publish(conv, "step", {"tool": "research", "label": txt, "state": "running", "id": f"rs-{run_id[-6:]}-{g}",
                                       "args": {"goal": goal[:120]}})
        except Exception:       # noqa: BLE001
            pass
        if time.time() - last["t"] > 5:          # heartbeat + progress, not a DB write per step
            last["t"] = time.time()
            store.touch(run_id, dict(prog))

    def checkpoint(cp: dict) -> None:
        results = cp.get("results") or []
        prog.update({"goals_done": len(results), "round": cp.get("round", 1),
                     "goals_total": max(prog["goals_total"], len(results), len(cp.get("todo") or []) +
                                        sum(1 for r in results if r.get("round") != cp.get("round"))),
                     "pages": len(cp.get("pages") or {}), "notes": sum(len(r.get("notes", [])) for r in results)})
        store.save_checkpoint(run_id, cp, dict(prog))
        store.set_cost(run_id, meter.breakdown())
        _publish(conv, run_id, cp.get("question", ""), "running", progress_text(prog, hi), stage=progress_text(prog, hi))

    def stopped() -> bool:
        v = store.get(run_id)
        if v is None or v["status"] == "stopped":
            return True
        try:
            from ..agent import santosh
            return conv in santosh._stopped
        except Exception:       # noqa: BLE001
            return False

    d.stopped, d.step, d.checkpoint = stopped, step, checkpoint
    d.afford, d.cost = meter.afford, meter.breakdown
    d.__dict__["_prog"], d.__dict__["_meter"] = prog, meter
    return d


class _StoppedMarker(Exception):
    """A vendor run was stopped by her: recorded already (status + what it spent); nothing more to report."""


async def _vendor_job(engine: str, run_id: str, v: dict, deps: E.Deps, pol: E.Policy, st) -> dict:
    """v0.477 R6: start (or RE-ATTACH to) the vendor's run, wait for it, then re-check every claim with Hoola's own fetch. The same dossier as the own engine."""
    from . import vendors
    meter = deps.__dict__["_meter"]
    resume_id = str(((v.get("checkpoint") or {}).get("vendor") or {}).get("run_id") or "")

    def on_id(rid: str) -> None:                                 # the vendor's run id is written the moment it exists: a restart re-attaches
        store.save_checkpoint(run_id, {"vendor": {"engine": engine, "run_id": rid}}, {"goals_total": 1, "goals_done": 0, "now": engine})
        store.set_cost(run_id, meter.breakdown())
    try:
        return await vendors.gather(engine, v["question"], list(v["goals"]), pol, deps, meter, st, over=v["policy"].get("over") or {}, on_id=on_id,
                                    on_cost=lambda: store.set_cost(run_id, meter.breakdown()), resume_id=resume_id)
    except vendors.StoppedByHer:
        store.finish(run_id, "stopped", None, "", cost=meter.breakdown())
        raise _StoppedMarker()


async def run_background(run_id: str) -> None:
    """One persisted run end to end. Never raises (except CancelledError); every outcome is recorded and reported."""
    from ..config import get_settings
    st = get_settings()
    v = store.get(run_id)
    if v is None or v["status"] not in ("queued", "running"):
        return
    tenant, conv, question = v["tenant"], v["conv"], v["question"]
    hi = bool(v["policy"].get("hi", True))
    engine = str(v["policy"].get("engine") or "hoola")
    _RUNNING.add(run_id)
    store.set_status(run_id, "running", only_from=("queued", "running"))
    try:
        pol = E.Policy.from_settings(st, bg=True, **(v["policy"].get("over") or {}))
        goals = list(v["goals"])
        deps = _build_deps(tenant, conv, run_id, hi, st, total=(1 if engine != "hoola" else (len(goals) or 1)), base=v.get("cost") or None)
        if v["tries"] > 1 and v["checkpoint"]:
            STATS["resumed"] += 1
        from .. import usage
        usage.bind(tenant, "research")                           # her research is hers: counted under her, as "Research"
        with usage.run_meter(deps.__dict__["_meter"].acc):       # v0.476 R5: this run's own model calls, nobody else's
            if engine == "hoola":
                d = await E.run(question, goals, pol, deps, asked_urls=v["policy"].get("asked") or [], resume=v["checkpoint"] or None)
            else:                                                # v0.477 R6: a vendor gathers, Hoola verifies
                d = await _vendor_job(engine, run_id, v, deps, pol, st)
        cost = d.get("cost") or {}
        stopped_now = (store.get(run_id) or {}).get("status") == "stopped"
        s = d["stats"]
        if stopped_now:
            store.finish(run_id, "stopped", None, "", cost=cost)          # a stopped run still spent what it spent
            return
        if s["pages_read"] == 0 and s["verified_notes"] == 0:
            store.finish(run_id, "failed", d, "no readable pages were found", cost=cost)
            STATS["failed"] += 1
            _publish(conv, run_id, question, "failed",
                     "koi padhne layak page nahi mila" if hi else "no readable pages were found")
        else:
            store.finish(run_id, "done", d, cost=cost)
            STATS["done"] += 1
            tail = (f" - KHARCHA seema par ruk gaya (Rs {cost.get('total_inr', 0):.0f})" if hi else f" - stopped at the cost ceiling (Rs {cost.get('total_inr', 0):.0f})") \
                if cost.get("stopped_by_cost") else ""
            say = (f"report likhne ko taiyaar: {s['pages_read']} pages, {s['verified_notes']}/{s['notes']} baatein verified{tail}"
                   if hi else f"ready to write: {s['pages_read']} pages, {s['verified_notes']}/{s['notes']} findings verified{tail}")
            _publish(conv, run_id, question, "done", say)
    except asyncio.CancelledError:
        raise
    except _StoppedMarker:
        pass
    except Exception as e:      # noqa: BLE001
        log.exception("background research %s failed", run_id)
        store.finish(run_id, "failed", None, f"{type(e).__name__}: {str(e)[:200]}")
        STATS["failed"] += 1
        _publish(conv, run_id, question, "failed", "research beech mein ruk gaya" if hi else "the research stopped part-way")
    finally:
        _RUNNING.discard(run_id)


def _bg_done(t) -> None:
    _BG.discard(t)
    if not t.cancelled() and t.exception():
        log.error("research task ended with %r", t.exception())


async def tick() -> int:
    """The worker slot (~20 s): start queued runs, pick a stalled one up again from its checkpoint, forget old rows."""
    from ..config import get_settings
    st = get_settings()
    if not getattr(st, "research_engine_on", True) or not getattr(st, "research_background", True):
        return 0
    ids = store.candidates(now() - timedelta(seconds=int(getattr(st, "research_bg_stale_s", 180))),
                           int(getattr(st, "research_bg_max_running", 2)), int(getattr(st, "research_bg_tries", 3)))
    started = 0
    for rid in ids:
        if rid in _RUNNING:
            continue
        with_tries = None
        from ..db import session
        with session() as s:
            row = s.get(store.ResearchRun, rid)
            if row is None or row.status not in ("queued", "running"):
                continue
            row.tries, row.status, row.updated_at = row.tries + 1, "running", now()
            with_tries = row.tries
        _RUNNING.add(rid)
        t = asyncio.ensure_future(run_background(rid))
        _BG.add(t)
        t.add_done_callback(_bg_done)
        started += 1
        log.info("research run %s started (try %s)", rid, with_tries)
    if started == 0:
        store.forget_old()
    return started


def status(tenant: str, conv: str = "", run_id: str = "") -> list[dict[str, Any]]:
    out = []
    for v in store.recent(tenant, conv, 8):
        if run_id and v["id"] != run_id:
            continue
        hi = bool(v["policy"].get("hi", True))
        out.append({"id": v["id"], "status": v["status"], "question": v["question"][:160], "tries": v["tries"],
                    "progress": progress_text(v["progress"], hi) if v["progress"] else "", "now": v["progress"].get("now", ""),
                    "error": v["error"], "has_report": v["dossier"] is not None, "cost_inr": round(v.get("cost_inr", 0.0), 2),
                    "engine": v["policy"].get("engine", "hoola")})
    return out
