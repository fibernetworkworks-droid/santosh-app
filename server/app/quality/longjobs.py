"""v0.347 LAMBE KAAM KI REPORT - how her real long jobs went, from what Hoola already records (no model call, no cost).

Three records, read side by side:
- agent_task_runs (pakka.record): every working turn - outcome done / partial / stuck / stopped / talk, steps, failures,
  what was left, seconds;
- goal_runs (kaam_plan / the server's plan): every long job's card - working / done / blocked / stopped / failed, rounds,
  restarts picked up, why it ended;
- harness_events turn_failed: the turns that never reached pakka.record at all (turn timeout, a crash).
`python -m app.quality longjobs [--hours 24]`; vps-ops job `long_jobs`. Her words are already masked when they are
stored (pakka.mask); the report shows at most 90 characters of each."""
from __future__ import annotations

import json
from collections import Counter
from datetime import timedelta
from typing import Any

LONG_STEPS = 4          # a working turn with at least this many tool steps counts as a long job
SHOW = 12               # unfinished jobs listed one by one


def _clip(text: str, n: int = 90) -> str:
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def report(hours: int = 24) -> dict[str, Any]:
    from sqlalchemy import select

    from ..agent.eventlog import HarnessEvent, ensure_table
    from ..agent.goal import GoalRun
    from ..agent.pakka import TaskRun
    from ..db import now, session
    since = now() - timedelta(hours=max(1, int(hours)))
    ensure_table()
    with session() as s:
        runs = s.scalars(select(TaskRun).where(TaskRun.created_at >= since).order_by(TaskRun.created_at)).all()
        goals = s.scalars(select(GoalRun).where(GoalRun.updated_at >= since).order_by(GoalRun.updated_at)).all()
        fails = s.scalars(select(HarnessEvent).where(HarnessEvent.kind == "turn_failed",
                                                     HarnessEvent.created_at >= since)
                          .order_by(HarnessEvent.id)).all()
        long_runs = [r for r in runs if (r.steps or 0) >= LONG_STEPS and r.outcome != "talk"]
        outcomes = Counter(r.outcome for r in long_runs)
        unfinished = [{"at": r.created_at.isoformat(), "outcome": r.outcome, "steps": r.steps,
                       "failures": r.failures, "minutes": round((r.seconds or 0) / 60, 1),
                       "ask": _clip(r.request), "left": _clip(r.left, 120),
                       "tools": (json.loads(r.tools or "[]") or [])[-4:]}
                      for r in long_runs if r.outcome != "done"]
        gstat = Counter(g.status or "working" for g in goals)
        gview = [{"status": g.status, "goal": _clip(g.goal), "rounds": g.rounds or 1, "recovered": g.recovered or 0,
                  "reason": _clip(g.reason, 120), "hold": g.hold or ""}
                 for g in goals if (g.status or "working") != "done"]
        failed = []
        for e in fails:
            try:
                line = json.loads(e.payload or "{}").get("line", "")
            except ValueError:
                line = ""
            failed.append({"at": e.created_at.isoformat() if e.created_at else "", "line": _clip(line, 140)})
    reasons = Counter("timeout" if "timeout" in f["line"].lower() else "error" for f in failed)
    done = outcomes.get("done", 0)
    total = len(long_runs)
    return {"hours": hours, "long_jobs": total, "done": done,
            "done_pct": round(100 * done / total) if total else None, "outcomes": dict(outcomes),
            "plans": len(goals), "plan_status": dict(gstat), "turn_failures": len(failed),
            "failure_kinds": dict(reasons), "unfinished": unfinished[-SHOW:], "plans_open": gview[-SHOW:],
            "failures": failed[-SHOW:]}


def lines(rep: dict[str, Any]) -> list[str]:
    h = rep["hours"]
    if not rep["long_jobs"] and not rep["plans"] and not rep["turn_failures"]:
        return [f"Long jobs, last {h} h: none ran."]
    pct = f" ({rep['done_pct']}%)" if rep["done_pct"] is not None else ""
    out = [f"Long jobs, last {h} h: {rep['long_jobs']} ran ({LONG_STEPS}+ steps), {rep['done']} finished{pct}. "
           f"Outcomes {rep['outcomes'] or '{}'}.",
           f"Plan cards: {rep['plans']} ({rep['plan_status'] or '{}'}). Turns that died before the end: "
           f"{rep['turn_failures']} {rep['failure_kinds'] or ''}".rstrip()]
    if rep["unfinished"]:
        out.append("Not finished:")
        for u in rep["unfinished"]:
            tail = f" - left: {u['left']}" if u["left"] else ""
            out.append(f"  - [{u['outcome']}] {u['ask']} ({u['steps']} steps, {u['failures']} failed, "
                       f"{u['minutes']} min, last tools {', '.join(u['tools'])}){tail}")
    if rep["plans_open"]:
        out.append("Plan cards not done:")
        for g in rep["plans_open"]:
            extra = f", picked up after restart x{g['recovered']}" if g["recovered"] else ""
            why = f" - {g['reason']}" if g["reason"] else ""
            out.append(f"  - [{g['status']}{'/' + g['hold'] if g['hold'] else ''}] {g['goal']} "
                       f"(rounds {g['rounds']}{extra}){why}")
    if rep["failures"]:
        out.append("Turns that died:")
        out += [f"  - {f['at'][:16]} {f['line']}" for f in rep["failures"]]
    return out
