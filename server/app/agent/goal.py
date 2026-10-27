"""v0.186 Lamba kaam pakka: goals that survive the turn.

A goal is a plan the brain itself writes with the `kaam_plan` tool (set / step / add / show / finish). While a goal
for this conversation has open steps (status `working`), the agent turn does not stop on text, the caps rise
(config AGENT_GOAL_*), failures get the "ek doosra tareeka try karta hoon" ladder (pakka), and when the turn must
end anyway, ONE background continuation turn is scheduled (`maybe_continue`), so a long job keeps going across
turns instead of dying at the first reply.

Every change publishes a `goal` event ({id, title, stage, pct, status, steps}) on the bus:
- kaamwatch watches it (KINDS["goal"]) -> live progress lines in chat, quiet notes into her call, stuck alarms;
- it is a card kind (not LOCAL) -> one card per goal id, updated in place, in chat and in the call;
- push only when it blocks on her or finishes.

Nothing here pays, sends or approves anything: every gate (cards, money taps, OTP) stays exactly where it was.
`blocked_on_her` is only for a real dependency: her tap, an OTP, a missing fact.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session
from ..events import bus

log = logging.getLogger("santosh.goal")

MAX_STEPS = 15               # kaam_plan set cap
STATS = {"set": 0, "finished": 0, "blocked": 0, "continued": 0, "refused": 0, "stopped_by_her": 0}

# conversations whose owner pressed Rokiye on the goal (the goal stops, the chat stays usable)
_STOPPED: set[str] = set()


class GoalRun(Base):
    __tablename__ = "goal_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    goal: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[str] = mapped_column(Text, default="[]")            # JSON [{n, text, state, note}]
    status: Mapped[str] = mapped_column(String(12), default="working")  # working|done|blocked|stopped|failed
    reason: Mapped[str] = mapped_column(Text, default="")             # why it ended / what it needs from her
    rounds: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _row_view(r: GoalRun) -> dict[str, Any]:
    try:
        steps = json.loads(r.steps or "[]")
    except ValueError:
        steps = []
    done = sum(1 for x in steps if x.get("state") == "done")
    stage = next((x["text"] for x in steps if x.get("state") == "current"), "")
    pct = round(100 * done / len(steps)) if steps else 0
    return {"id": r.id, "conversation_id": r.conversation_id, "goal": r.goal or "", "steps": steps,
            "status": r.status or "working",
            "reason": r.reason or "", "rounds": r.rounds or 1, "done": done, "total": len(steps),
            "stage": stage, "pct": pct,
            "updated_at": (_aware(r.updated_at) or now()).isoformat()}


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _publish(conv: str, view: dict[str, Any]) -> None:
    """The goal card event: kind `goal`, one card per goal id (card_key goal:id:<id>)."""
    stage = view["stage"] or (view["reason"] if view["status"] in ("blocked", "failed", "stopped") else "")
    bus.publish(conv, "goal", {"id": view["id"], "title": view["goal"], "status": view["status"],
                               "stage": stage[:120], "pct": view["pct"], "steps": view["steps"][:15],
                               "done": view["done"], "total": view["total"], "reason": view["reason"][:200]})


def _mutate(tenant: str, goal_id: str, fn) -> dict[str, Any]:
    """Load, mutate, save in ONE write txn; publish after it closes (SQLite one writer)."""
    with session() as s:
        r = s.get(GoalRun, goal_id)
        if r is None or r.tenant_id != tenant:
            raise ValueError(f"goal {goal_id} nahi mila")
        fn(r)
        r.updated_at = now()
        view = _row_view(r)
        conv = r.conversation_id
    _publish(conv, view)
    return view


# ---------------------------------------------------------------- kaam_plan actions (called from goal_tools)
def set_goal(tenant: str, conv: str, goal: str, steps: list[str]) -> dict[str, Any]:
    """A new goal for this conversation: any previous working goal is marked stopped (one plan at a time)."""
    steps = [str(x).strip()[:200] for x in (steps or []) if str(x).strip()][:MAX_STEPS]
    if not goal.strip() or not steps:
        raise ValueError("goal aur kam se kam ek step chahiye")
    _STOPPED.discard(conv)
    with session() as s:
        for r in s.scalars(select(GoalRun).where(GoalRun.conversation_id == conv, GoalRun.status == "working")).all():
            r.status, r.reason, r.updated_at = "stopped", "naya plan ban gaya", now()
        r = GoalRun(tenant_id=tenant, conversation_id=conv, goal=goal.strip()[:500],
                    steps=json.dumps([{"n": i + 1, "text": t, "state": "pending", "note": ""} for i, t in enumerate(steps)],
                                     ensure_ascii=False))
        s.add(r)
        s.flush()                       # the id default lands before the card is published
        STATS["set"] += 1
        view = _row_view(r)
    _publish(conv, view)
    return view


def mark_step(tenant: str, goal_id: str, n: int, state: str, note: str = "", conv: str = "") -> dict[str, Any]:
    """step n done|failed|skipped|current — recorded on the card, published live."""
    del conv  # the row knows its conversation
    if state not in ("done", "failed", "skipped", "current", "pending"):
        raise ValueError("state done|failed|skipped|current|pending")

    def fn(r: GoalRun):
        try:
            steps = json.loads(r.steps or "[]")
        except ValueError:
            steps = []
        hit = next((x for x in steps if x.get("n") == n), None)
        if hit is None:
            raise ValueError(f"step {n} plan mein nahi hai (1..{len(steps)})")
        hit["state"], hit["note"] = state, str(note or "")[:200]
        r.steps = json.dumps(steps, ensure_ascii=False)

    return _mutate(tenant, goal_id, fn)


def add_step(tenant: str, goal_id: str, text: str, conv: str = "") -> dict[str, Any]:
    del conv
    def fn(r: GoalRun):
        try:
            steps = json.loads(r.steps or "[]")
        except ValueError:
            steps = []
        if len(steps) >= MAX_STEPS:
            raise ValueError(f"plan mein pehle hi {MAX_STEPS} steps hain")
        steps.append({"n": len(steps) + 1, "text": str(text).strip()[:200], "state": "pending", "note": ""})
        r.steps = json.dumps(steps, ensure_ascii=False)

    return _mutate(tenant, goal_id, fn)


def _load(tenant: str, goal_id: str) -> GoalRun | None:
    with session() as s:
        r = s.get(GoalRun, goal_id)
        return r if r is not None and r.tenant_id == tenant else None


def show(tenant: str, goal_id: str) -> dict[str, Any]:
    r = _load(tenant, goal_id)
    if r is None:
        raise ValueError(f"goal {goal_id} nahi mila")
    return _row_view(r)


def finish(tenant: str, goal_id: str, outcome: str, reason: str = "", conv: str = "") -> dict[str, Any]:
    """done | blocked_on_her | failed | stopped. blocked_on_her = only a real dependency on her (tap / OTP / fact)."""
    del conv
    why = {"done": "done", "blocked_on_her": "blocked", "failed": "failed", "stopped": "stopped"}.get(outcome)
    if why is None:
        raise ValueError("outcome done|blocked_on_her|failed|stopped")

    def fn(r: GoalRun):
        r.status, r.reason = why, str(reason or "")[:400]
        STATS["finished" if why == "done" else "blocked" if why == "blocked" else "refused"] += 1

    return _mutate(tenant, goal_id, fn)


def active_for(conv: str) -> dict[str, Any] | None:
    """The working goal of this conversation, or None. `goal is on` for the turn = this returns a row."""
    if conv in _STOPPED:
        return None
    with session() as s:
        r = s.scalars(select(GoalRun).where(GoalRun.conversation_id == conv, GoalRun.status == "working")
                      .order_by(GoalRun.updated_at.desc())).first()
        return _row_view(r) if r is not None else None


def mark_stopped(conv: str) -> None:
    """She pressed Rokiye on the goal: the working goal stops now (continuations refuse this conversation)."""
    _STOPPED.add(conv)
    with session() as s:
        for r in s.scalars(select(GoalRun).where(GoalRun.conversation_id == conv, GoalRun.status == "working")).all():
            r.status, r.reason, r.updated_at = "stopped", "aapne roka", now()
            _publish(conv, _row_view(r))


def steps_left(view: dict[str, Any]) -> list[dict[str, Any]]:
    return [x for x in (view.get("steps") or []) if x.get("state") in ("pending", "current", "failed")]


def nudge_text(view: dict[str, Any]) -> str:
    """The continue nudge: what is left, and the ladder for a stuck step."""
    left = steps_left(view)
    lines = "; ".join(f"{x['n']}. {x['text']}" for x in left[:8])
    return (f"[System: goal \"{view['goal']}\" ke yeh steps baaki hain: {lines}. Agle step par kaam karo tools se. "
            "Atke ho to doosra tareeka: pichhla fix -> google_search/web_sources -> docs padho (open_website) -> "
            "doosra tool/route. Har step hone par kaam_plan step n done/failed likho. Sirf sach mein uski zaroorat ho "
            "tabhi kaam_plan finish blocked_on_her (uska tap / OTP / ek fact jo tumhare paas nahi). Text mein mat ruko.]")


# ---------------------------------------------------------------- carry on across turns
def goal_block(conv: str) -> str:
    """The 'GOAL JAARI HAI' block for every new turn in this chat (her message or a continuation)."""
    view = active_for(conv)
    if view is None:
        return ""
    left = steps_left(view)
    done = [x for x in (view.get("steps") or []) if x.get("state") == "done"]
    tried = [f"{x['n']}. {x['text']}" + (f" ({x['note']})" if x.get("note") else "")
             for x in (view.get("steps") or []) if x.get("state") in ("failed", "skipped")]
    out = [f"GOAL JAARI HAI (aapka apna lamba kaam; ise poora karo, text par mat ruko): {view['goal']}",
           f"- Ho chuke: {len(done)}/{view['total']} steps."]
    if left:
        out.append("- Baaki: " + "; ".join(f"{x['n']}. {x['text']}" for x in left[:10]))
    if tried:
        out.append("- Inme dikkat aayi thi: " + "; ".join(tried[:4]) + " (doosra tareeka try karo).")
    out.append("- Har step hone par kaam_plan step n done/failed likho; poora hone par kaam_plan finish done.")
    return "\n".join(out)


def _waiting_on_her(conv: str) -> bool:
    """A real dependency on her right now: an open card that needs her tap / answer in this chat."""
    try:
        from ..events import needs_her, card_key
        from ..db import Event
        with session() as s:
            rows = s.scalars(select(Event).where(Event.conversation_id == conv)
                             .order_by(Event.id.desc()).limit(40)).all()
        seen: set[str] = set()
        for e in rows:
            p = e.payload if isinstance(e.payload, dict) else {}
            k = card_key(e.kind, p, e.id)
            if k in seen:
                continue
            seen.add(k)
            if needs_her(e.kind, p):
                return True
        return False
    except Exception:
        log.exception("waiting_on_her check failed")
        return False


def maybe_continue(conv: str, tenant: str, actor: str = "owner") -> bool:
    """The turn ended with the goal still working: schedule ONE background continuation turn.
    Refuses: blocked on her (a waiting card), Rokiye, rounds / minutes limits, budget, non-owner/routine turns."""
    st = get_settings()
    if not st.agent_goal:
        return False
    if actor not in ("owner", "routine") or actor.startswith("approved:"):
        STATS["refused"] += 1
        return False
    view = active_for(conv)
    if view is None:
        return False
    if _waiting_on_her(conv):
        log.info("goal %s waits on her; no continuation", view["id"])
        STATS["refused"] += 1
        return False
    rounds, mins = 0, 0.0
    with session() as s:               # bookkeeping txn closes BEFORE finish() opens its own (SQLite one writer)
        r = s.get(GoalRun, view["id"])
        if r is None:
            return False
        rounds, mins = r.rounds, (now() - (_aware(r.started_at) or now())).total_seconds() / 60
        if rounds < st.agent_goal_rounds and mins < st.agent_goal_minutes:
            r.rounds += 1
    if rounds >= st.agent_goal_rounds:
        finish(tenant, view["id"], "failed", f"{rounds} rounds poore; baaki: {view['stage'] or 'steps'}")
        return False
    if mins >= st.agent_goal_minutes:
        finish(tenant, view["id"], "failed", f"{int(mins)} minute ho gaye; baaki: {view['stage'] or 'steps'}")
        return False
    left = steps_left(view)
    from .santosh import _bg, run_turn, LAST_OUTCOME
    ask = f"[Goal jaari: {view['goal']} — baaki steps: " + "; ".join(f"{x['n']}. {x['text']}" for x in left[:8]) + \
        ". Aage badho, har step kaam_plan se likho, poora hone par finish done.]"
    _bg(_continuation(conv, tenant, ask, view["id"]))
    LAST_OUTCOME[conv] = {"outcome": "continuing", "left": f"{view['done']}/{view['total']} steps done, {len(left)} baaki",
                          "goal": view["goal"], "at": time.time()}
    STATS["continued"] += 1
    return True


async def _continuation(conv: str, tenant: str, ask: str, goal_id: str) -> None:
    """One background turn that keeps the goal going. Never raises into the caller's context."""
    await asyncio.sleep(2.5)          # let the original turn's final writes / events settle first
    try:
        from .santosh import run_turn, LAST_OUTCOME
        out = await run_turn(conv, ask, tenant_id=tenant, actor="routine")
        LAST_OUTCOME[conv] = {"outcome": "continuing", "left": str(out or "")[:300], "goal": goal_id, "at": time.time()}
        v = active_for(conv)
        if v is not None and steps_left(v):
            log.info("goal %s still open after continuation; rounds cap will decide the rest", goal_id)
    except Exception:
        log.exception("goal continuation failed")
