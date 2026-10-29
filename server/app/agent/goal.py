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
import re
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
STATS = {"waited_job": 0, "set": 0, "finished": 0, "blocked": 0, "continued": 0, "refused": 0, "stopped_by_her": 0, "paused": 0,
         "resumed": 0, "recovered": 0, "limit_asked": 0, "limit_reopened": 0,
         "milestones": 0, "reports": 0, "plan_early": 0}

# v0.223 goals whose background round is scheduled / running in THIS process (the recovery sweep never doubles them)
_PENDING: dict[str, int] = {}


def _pend(goal_id: str, d: int) -> None:
    n = _PENDING.get(goal_id, 0) + d
    if n > 0:
        _PENDING[goal_id] = n
    else:
        _PENDING.pop(goal_id, None)
LIMIT = "limit"

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
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # v0.221 waiting on her
    paused_s: Mapped[int | None] = mapped_column(Integer, nullable=True)       # v0.221 seconds spent waiting on her
    origin: Mapped[str | None] = mapped_column(String(16), nullable=True)      # v0.222 who asked: owner | routine
    recovered: Mapped[int | None] = mapped_column(Integer, nullable=True)      # v0.223 picked up after a restart (times)
    hold: Mapped[str | None] = mapped_column(String(16), nullable=True)        # v0.223 "limit" = waiting for her "aage badho"
    report: Mapped[str | None] = mapped_column(Text, nullable=True)            # v0.228 the four-part final report (JSON)
    milestones: Mapped[int | None] = mapped_column(Integer, nullable=True)     # v0.228 milestone pushes sent for this job
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
            "stage": stage, "pct": pct, "hold": r.hold or "", "report": _report_of(r),
            "updated_at": (_aware(r.updated_at) or now()).isoformat()}


def _report_of(r: GoalRun) -> dict[str, Any] | None:
    try:
        v = json.loads(r.report) if r.report else None
    except ValueError:
        v = None
    return v if isinstance(v, dict) else None


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _publish(conv: str, view: dict[str, Any]) -> None:
    """The goal card event: kind `goal`, one card per goal id (card_key goal:id:<id>)."""
    stage = view["stage"] or (view["reason"] if view["status"] in ("blocked", "failed", "stopped") else "")
    bus.publish(conv, "goal", {"id": view["id"], "title": view["goal"], "status": view["status"],
                               "stage": stage[:120], "pct": view["pct"], "steps": view["steps"][:15],
                               "done": view["done"], "total": view["total"], "reason": view["reason"][:200],
                               "hold": view.get("hold", ""),   # v0.223 "limit" = the card asks "Aage badhaun?"
                               "report": view.get("report"),   # v0.228 kya hua / kya bana / kya baaki / aapko kya karna hai
                               "milestone": view.get("milestone", "")})   # v0.228 set ONLY on the one event that pushes


def _mutate(tenant: str, goal_id: str, fn, milestone: list[str] | None = None) -> dict[str, Any]:
    """Load, mutate, save in ONE write txn; publish after it closes (SQLite one writer)."""
    with session() as s:
        r = s.get(GoalRun, goal_id)
        if r is None or r.tenant_id != tenant:
            raise ValueError(f"goal {goal_id} nahi mila")
        fn(r)
        r.updated_at = now()
        view = _row_view(r)
        conv = r.conversation_id
    if milestone:
        view = {**view, "milestone": milestone[0]}
    _publish(conv, view)
    return view


# ---------------------------------------------------------------- kaam_plan actions (called from goal_tools)
def hers(actor: str) -> bool:
    """v0.222 a turn that carries HER own authority: her words, her tap (approved:), or a background round of a long
    job SHE asked for (actor "goal"). Routines, wake turns, staff and customers are not hers."""
    a = actor or "owner"
    return a in ("owner", "goal") or a.startswith("approved:")


def round_actor(origin: str | None) -> str:
    """v0.222 the actor a background round runs as: her own job keeps her authority ("goal" - the employee gate and
    the monthly background limit treat it as her own chat); a routine's job stays a routine. Goals written before
    v0.222 (origin unknown) keep the old routine behaviour."""
    return "goal" if origin in ("owner", "goal") else "routine"


def set_goal(tenant: str, conv: str, goal: str, steps: list[str], origin: str = "") -> dict[str, Any]:
    """A new goal for this conversation: any previous working goal is marked stopped (one plan at a time).
    v0.222 `origin` = whose job it is (the actor of the turn that wrote the plan)."""
    steps = [str(x).strip()[:200] for x in (steps or []) if str(x).strip()][:MAX_STEPS]
    if not goal.strip() or not steps:
        raise ValueError("goal aur kam se kam ek step chahiye")
    _STOPPED.discard(conv)
    with session() as s:
        for r in s.scalars(select(GoalRun).where(GoalRun.conversation_id == conv, GoalRun.status == "working")).all():
            r.status, r.reason, r.updated_at = "stopped", "naya plan ban gaya", now()
        r = GoalRun(tenant_id=tenant, conversation_id=conv, goal=goal.strip()[:500],
                    steps=json.dumps([{"n": i + 1, "text": t, "state": "pending", "note": ""} for i, t in enumerate(steps)],
                                     ensure_ascii=False),
                    origin=("owner" if hers(origin) else "routine") if origin else None)
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
        if state == "done" and (r.status or "working") == "working":
            mark = _milestone(sum(1 for x in steps if x.get("state") == "done"), len(steps), r.milestones or 0)
            if mark:
                r.milestones = (r.milestones or 0) + 1
                ms.append(mark)
                STATS["milestones"] += 1

    ms: list[str] = []
    view = _mutate(tenant, goal_id, fn, milestone=ms)
    return view


def _milestone(done: int, total: int, sent: int) -> str:
    """v0.228 a long job she is not watching tells her when it crosses a real milestone - never every step.
    Jobs of 4+ steps only; thresholds 1/2 (4-5 steps) or 1/3 and 2/3 (6+); at most agent_goal_milestones per job;
    never on the last step (the done push says that)."""
    cap = int(getattr(get_settings(), "agent_goal_milestones", 2) or 0)
    if total < 4 or done >= total or sent >= cap:
        return ""
    marks = [total / 2] if total < 6 else [total / 3, 2 * total / 3]
    if sent >= len(marks) or done < marks[sent]:
        return ""
    return f"{done}/{total}"


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


_LINK = re.compile(r"https?://[^\s)\]>\"']+|\b[\w./-]+\.(?:pdf|docx|xlsx|pptx|csv|zip|png|jpe?g|mp4|html)\b", re.I)


def build_report(steps: list[dict[str, Any]], status: str, summary: str = "", made: list[str] | None = None,
                 left: str = "", your_turn: str = "") -> dict[str, Any]:
    """v0.228 the standard four-part final report, like Claude's end-of-job summary:
    kya hua (what was done) / kya bana (links, files) / kya baaki (what is left) / aapko kya karna hai (her part).
    Built by code from the plan itself, so it is never empty or invented: done steps ARE what happened, steps not done
    ARE what is left, links / file names come from her model's own list plus the step notes."""
    done = [x for x in steps if x.get("state") == "done"]
    not_done = [x for x in steps if x.get("state") in ("pending", "current", "failed")]
    hua = [f"{x['text']}" + (f" — {x['note']}" if x.get("note") else "") for x in done][:10]
    bana: list[str] = []
    for m in list(made or []) + [x.get("note") or "" for x in done]:
        for hit in _LINK.findall(str(m)) or ([str(m).strip()] if m in (made or []) else []):
            hit = hit.strip()[:240]
            if hit and hit not in bana:
                bana.append(hit)
    baaki = [f"{x['text']}" + (" (atka)" if x.get("state") == "failed" else "") for x in not_done][:10]
    if left.strip():
        baaki.append(left.strip()[:300])
    turn = your_turn.strip()[:300] or (
        "Kuch nahi — sab ho gaya." if status == "done" and not baaki else
        "Aage badhane ke liye bas 'haan aage badho' likhiye ya boliye." if baaki and status != "blocked" else "")
    return {"summary": str(summary or "").strip()[:400], "hua": hua, "bana": bana[:10], "baaki": baaki[:10],
            "aapka": turn}


def report_text(rep: dict[str, Any]) -> str:
    """The same report as plain chat text (her final message, the push body, the call note)."""
    out = []
    if rep.get("summary"):
        out.append(rep["summary"])
    if rep.get("hua"):
        out.append("✅ Kya hua:\n" + "\n".join(f"• {x}" for x in rep["hua"]))
    if rep.get("bana"):
        out.append("📎 Kya bana:\n" + "\n".join(f"• {x}" for x in rep["bana"]))
    if rep.get("baaki"):
        out.append("⏳ Kya baaki hai:\n" + "\n".join(f"• {x}" for x in rep["baaki"]))
    if rep.get("aapka"):
        out.append("👉 Aapko kya karna hai: " + rep["aapka"])
    return "\n\n".join(out)


def finish(tenant: str, goal_id: str, outcome: str, reason: str = "", conv: str = "", made: list[str] | None = None,
           left: str = "", your_turn: str = "") -> dict[str, Any]:
    """done | blocked_on_her | failed | stopped. blocked_on_her = only a real dependency on her (tap / OTP / fact).
    v0.228 every finish carries the four-part report (kya hua / kya bana / kya baaki / aapko kya karna hai)."""
    del conv
    why = {"done": "done", "blocked_on_her": "blocked", "failed": "failed", "stopped": "stopped"}.get(outcome)
    if why is None:
        raise ValueError("outcome done|blocked_on_her|failed|stopped")

    def fn(r: GoalRun):
        r.status, r.reason = why, str(reason or "")[:400]
        try:
            steps = json.loads(r.steps or "[]")
        except ValueError:
            steps = []
        mine = your_turn or (reason if why == "blocked" else "")
        r.report = json.dumps(build_report(steps, why, reason, made, left, mine), ensure_ascii=False)
        STATS["reports"] += 1
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


def started_at(goal_id: str) -> datetime | None:
    """v0.221 when this goal began (yaad keeps every exchange since then in the rich form)."""
    with session() as s:
        r = s.get(GoalRun, goal_id)
        return _aware(r.started_at) if r is not None else None


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
            "tabhi kaam_plan finish blocked_on_her (uska tap / OTP / ek fact jo tumhare paas nahi). Text mein mat ruko. "
            "Har bade step ke baad EK chhoti line likho (kya mila / kya bana, aur ab kya kar rahe ho), phir agla tool.]")


# ---------------------------------------------------------------- v0.228 plan up front for clearly big asks
_SEQ = re.compile(r"\b(?:phir|fir|uske\s+baad|iske\s+baad|then|after\s+that|and\s+then|aur\s+phir|saath\s+hi|"
                  r"next|finally|aakhir\s+mein|end\s+to\s+end|step\s+by\s+step|poora\s+(?:kaam|project|setup)|"
                  r"sab\s+kuch|फिर|उसके\s+बाद)\b", re.I)
_LIST = re.compile(r"(?m)^\s*(?:\d{1,2}[.)]|[-*•])\s+\S")
_VERB = re.compile(r"\b(?:bana|banao|bhej|bhejo|likh|likho|nikal|nikalo|dhoondh|dhundh|check|compare|update|"
                   r"download|upload|book|order|create|make|send|write|find|research|analy[sz]e|fill|set\s*up|"
                   r"install|deploy|report|summary|list)\w*", re.I)


def looks_big(text: str) -> bool:
    """v0.228 does her ask clearly need several steps? Then the plan comes FIRST (Claude writes its todo list before
    the work, not at step 24). Word rules only, never a model call: sequence words / a list / many actions."""
    t = (text or "").strip()
    if not t or t.startswith("["):
        return False
    words = len(t.split())
    seq = len(_SEQ.findall(t))
    items = len(_LIST.findall(t))
    verbs = len(_VERB.findall(t))
    return items >= 3 or seq >= 2 or (seq >= 1 and verbs >= 3) or (verbs >= 4 and words >= 25) or words >= 80


PLAN_FIRST = ("[System: yeh kaam kai steps ka lagta hai. Sabse PEHLA tool call `kaam_plan set` ho — goal uske shabdon "
              "mein, concrete steps. Phir step by step kaam karo, aur har bade step ke baad ek chhoti line mein batao "
              "kya hua aur aage kya. Aakhir mein `kaam_plan finish` (made = links / files jo bane).]")
PLAN_NOW = ("[System: tum kai steps se kaam kar rahe ho par plan nahi likha. Abhi `kaam_plan set` karo (jo ho chuka "
            "use done likho), taaki use card par dikhe kya ho raha hai aur kya baaki hai. Phir aage badho.]")
# v0.257 CHALTE CHALTE BOLO. v0.240 told this line to carry no number and no link, which left it empty filler
# ("Bills ban rahe hain"). Claude's between-step line IS the number - "the live site is on v0.256.0, the same commit
# as main (213d505). Creating the checkpoint branch next." One sentence: what the tool really returned + what you are
# doing now. Still no bullets, no headings, no step dumps - that part of CHHOTA JAWAB stands.
_NARRATE = ("[System: ab use EK chhoti line batao — ek ya do vaakya, jaise ek sathi kaam karte hue bolta hai. "
            "Do cheezein us line mein: (1) abhi ke tool se jo SACH mila — asli number / id / naam / link, tool ke "
            "result se, banaya hua nahi; (2) ab turant kya kar rahe ho. Jaise: 'Live site v0.256.0 par hai, wahi "
            "commit jo main par hai — ab checkpoint branch bana raha hoon.' Koi bullet, koi heading, koi step-by-step "
            "list, koi emoji nahi. Agar kaam ab POORA ho gaya hai to yeh line mat likho — seedha aakhri jawab do.{fact}]")


def narrate_line(facts: object = None) -> str:
    """The between-steps ask, with the true fact the tools just returned (app/agent/say.py) handed back to the model."""
    seen = [" ".join(str(f).split()) for f in (facts or []) if str(f or "").strip()]
    tail = ""
    if seen:
        tail = " Abhi ke tool results se sach: " + " · ".join(seen[-2:]) + " — isi mein se lo, naya mat banao."
    return _NARRATE.format(fact=tail)


NARRATE = _NARRATE.format(fact="")      # the bare ask, kept for anything that imports the constant


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


JOB_WAIT_S = 60 * 60     # v0.238 a job that has not moved for an hour no longer holds the goal (it may be dead)


def _waiting_on_job(conv: str) -> bool:
    """v0.238 a background job of this chat (cloud PC, website, video...) is still running and moving: the goal
    WAITS for it instead of starting a round every few seconds that only says "still running" (the 100-repo PDF
    loop). The job's own finish wakes the chat (kaam_followup) and resume_tick picks the goal up again."""
    try:
        from datetime import timedelta
        from ..kaamwatch import KaamJob
        cut = now() - timedelta(seconds=JOB_WAIT_S)
        with session() as s:
            rows = s.scalars(select(KaamJob).where(KaamJob.conversation_id == conv, KaamJob.state == "working")
                             .limit(20)).all()
            return any((_aware(r.moved_at) or _aware(r.updated_at) or now()) >= cut for r in rows)
    except Exception:
        log.exception("waiting_on_job check failed")
        return False


def maybe_continue(conv: str, tenant: str, actor: str = "owner") -> bool:
    """The turn ended with the goal still working: schedule ONE background continuation turn.
    Refuses: blocked on her (a waiting card), Rokiye, rounds / minutes limits, budget, non-owner/routine turns."""
    st = get_settings()
    if not st.agent_goal:
        return False
    if not (hers(actor) or actor == "routine"):
        STATS["refused"] += 1
        return False
    view = active_for(conv)
    if view is None:
        return False
    if _waiting_on_her(conv):
        log.info("goal %s waits on her; paused until she answers", view["id"])
        STATS["refused"] += 1
        _pause(view["id"])         # v0.221 the resume sweep restarts it once her card is answered
        return False
    if _waiting_on_job(conv):
        log.info("goal %s waits for a running job; paused until it finishes", view["id"])
        STATS["waited_job"] += 1
        _pause(view["id"])         # v0.238 waiting time never counts; resume_tick restarts it when the job ends
        return False
    return _schedule(conv, tenant, view, count_round=True)


def _working_minutes(r: GoalRun) -> float:
    """v0.221 minutes the goal really worked: time spent waiting on her (paused) never counts."""
    total = (now() - (_aware(r.started_at) or now())).total_seconds()
    waited = int(r.paused_s or 0)
    if r.paused_at is not None:
        waited += max(0, int((now() - _aware(r.paused_at)).total_seconds()))
    return max(0.0, total - waited) / 60


def _pause(goal_id: str) -> None:
    with session() as s:
        r = s.get(GoalRun, goal_id)
        if r is not None and r.paused_at is None:
            r.paused_at = now()
            STATS["paused"] += 1


def _schedule(conv: str, tenant: str, view: dict[str, Any], count_round: bool) -> bool:
    st = get_settings()
    rounds, mins, who = 0, 0.0, "routine"
    with session() as s:               # bookkeeping txn closes BEFORE finish() opens its own (SQLite one writer)
        r = s.get(GoalRun, view["id"])
        if r is None:
            return False
        if r.paused_at is not None:    # waiting is over: bank the waited time
            r.paused_s = int(r.paused_s or 0) + max(0, int((now() - _aware(r.paused_at)).total_seconds()))
            r.paused_at = None
        rounds, mins = r.rounds, _working_minutes(r)
        who = round_actor(r.origin)
        if not count_round:
            rounds = min(rounds, st.agent_goal_rounds - 1)   # a resume after her answer never uses up a round
        elif rounds < st.agent_goal_rounds and mins < st.agent_goal_minutes:
            r.rounds += 1
    if rounds >= st.agent_goal_rounds or mins >= st.agent_goal_minutes:
        why = f"{rounds} rounds poore" if rounds >= st.agent_goal_rounds else f"{int(mins)} minute ho gaye"
        if getattr(st, "agent_goal_ask_on_limit", True):
            _hold_for_limit(tenant, view)    # v0.223 like Claude: stop and ASK, never throw the job away
        else:
            finish(tenant, view["id"], "failed", f"{why}; baaki: {view['stage'] or 'steps'}")
        return False
    left = steps_left(view)
    from .santosh import _bg, run_turn, LAST_OUTCOME
    ask = f"[Goal jaari: {view['goal']} — baaki steps: " + "; ".join(f"{x['n']}. {x['text']}" for x in left[:8]) + \
        ". Aage badho, har step kaam_plan se likho, poora hone par finish done.]"
    _pend(view["id"], 1)
    _bg(_continuation(conv, tenant, ask, view["id"], who))
    LAST_OUTCOME[conv] = {"outcome": "continuing", "left": f"{view['done']}/{view['total']} steps done, {len(left)} baaki",
                          "goal": view["goal"], "at": time.time()}
    STATS["continued"] += 1
    return True


def resume_tick() -> int:
    """v0.221 worker sweep: a goal that paused because it needed HER (a card, an OTP, an answer) restarts by itself
    once nothing waits on her any more - before, the job sat half-done until she happened to type again.
    Never when she pressed Rokiye, never while a turn holds the chat, never for goals paused longer than
    agent_goal_resume_hours."""
    st = get_settings()
    if not (st.agent_goal and st.agent_goal_resume):
        return 0
    from datetime import timedelta
    cutoff = now() - timedelta(hours=max(1, st.agent_goal_resume_hours))
    with session() as s:
        rows = s.scalars(select(GoalRun).where(GoalRun.status == "working", GoalRun.paused_at.is_not(None))
                         .limit(50)).all()
        todo = [(r.id, r.tenant_id, r.conversation_id, _aware(r.paused_at)) for r in rows]
    n = 0
    from .santosh import _locks
    for gid, tenant, conv, at in todo:
        if conv in _STOPPED:
            continue
        if at is not None and at < cutoff:
            continue                     # too old: she moved on; her next message still sees the GOAL JAARI block
        if conv in _locks and _locks[conv].locked():
            continue                     # a turn is running in this chat: it carries the goal itself
        if _waiting_on_her(conv) or _waiting_on_job(conv):
            continue
        view = active_for(conv)
        if view is None or view["id"] != gid or not steps_left(view):
            _clear_pause(gid)
            continue
        if _schedule(conv, tenant, view, count_round=False):
            STATS["resumed"] += 1
            n += 1
    return n


def _clear_pause(goal_id: str) -> None:
    with session() as s:
        r = s.get(GoalRun, goal_id)
        if r is not None:
            r.paused_at = None


async def _continuation(conv: str, tenant: str, ask: str, goal_id: str, actor: str = "routine") -> None:
    """One background turn that keeps the goal going. Never raises into the caller's context."""
    await asyncio.sleep(2.5)          # let the original turn's final writes / events settle first
    try:
        v0 = active_for(conv)
        if v0 is None or v0["id"] != goal_id or not steps_left(v0):
            return                         # v0.223 finished / stopped / replaced while this round waited: nothing to do
        from .santosh import run_turn, LAST_OUTCOME
        out = await run_turn(conv, ask, tenant_id=tenant, actor=actor)
        LAST_OUTCOME[conv] = {"outcome": "continuing", "left": str(out or "")[:300], "goal": goal_id, "at": time.time()}
        v = active_for(conv)
        if v is not None and steps_left(v):
            log.info("goal %s still open after continuation; rounds cap will decide the rest", goal_id)
    except Exception:
        log.exception("goal continuation failed")
    finally:
        _pend(goal_id, -1)


# ---------------------------------------------------------------- v0.223 PHASE A: limits ask, restarts recover
def _hold_for_limit(tenant: str, view: dict[str, Any]) -> None:
    """The rounds / minutes budget is used up: the job STOPS AND ASKS (status blocked, hold=limit) instead of being
    marked failed. Her "haan aage badho" (or the card's button) gives it a fresh budget from where it stopped."""
    left = steps_left(view)
    reason = (f"Itna kaam ho gaya ({view['done']}/{view['total']} steps). Baaki: "
              + "; ".join(x["text"] for x in left[:3]) + (" ..." if len(left) > 3 else "")
              + ". Aage badhaun? Bas 'haan aage badho' likhiye / boliye.")

    def fn(r: GoalRun):
        r.status, r.hold, r.reason = "blocked", LIMIT, reason[:400]
        r.paused_at = None
    _mutate(tenant, view["id"], fn)
    STATS["limit_asked"] += 1


def held_for_limit(conv: str) -> dict[str, Any] | None:
    """The newest goal of this chat when it is waiting for her 'aage badho' after a used-up budget."""
    with session() as s:
        r = s.scalars(select(GoalRun).where(GoalRun.conversation_id == conv)
                      .order_by(GoalRun.updated_at.desc())).first()
        if r is None or r.status != "blocked" or r.hold != LIMIT:
            return None
        return _row_view(r)


CONTINUE_WORDS = ("aage badh", "aage badho", "aage chalo", "continue", "jaari rakho", "chalu rakho", "karte raho",
                  "poora karo", "khatam karo", "aage karo", "keep going", "go on", "आगे बढ़", "जारी रखो")


def wants_continue(text: str) -> bool:
    """Her words say 'carry on' (or a pure yes) - only then is a limit-held job reopened by a chat message."""
    t = (text or "").strip().lower()
    if not t or len(t) > 160:
        return False
    if any(w in t for w in CONTINUE_WORDS):
        return True
    try:
        from .. import approval_words
        return approval_words.is_pure_approval(t)
    except Exception:
        return False


def reopen(tenant: str, conv: str) -> dict[str, Any] | None:
    """Her yes after a used-up budget: the SAME goal works again with a fresh budget (rounds, minutes), done steps kept."""
    view = held_for_limit(conv)
    if view is None:
        return None
    _STOPPED.discard(conv)

    def fn(r: GoalRun):
        r.status, r.hold, r.reason = "working", None, ""
        r.rounds, r.started_at, r.paused_at, r.paused_s = 1, now(), None, 0
    out = _mutate(tenant, view["id"], fn)
    STATS["limit_reopened"] += 1
    return out


def continue_now(tenant: str, conv: str) -> dict[str, Any] | None:
    """The card's 'Aage badhao' button: reopen with a fresh budget AND start the next round right away."""
    view = reopen(tenant, conv)
    if view is None:
        return None
    from .santosh import _locks
    if not (conv in _locks and _locks[conv].locked()):
        who = "goal"                      # she pressed the button herself: this round carries her authority
        left = steps_left(view)
        ask = f"[Goal jaari: {view['goal']} — baaki steps: " + "; ".join(f"{x['n']}. {x['text']}" for x in left[:8]) + \
            ". Owner ne kaha aage badho. Aage badho, har step kaam_plan se likho, poora hone par finish done.]"
        from .santosh import _bg
        _pend(view["id"], 1)
        _bg(_continuation(conv, tenant, ask, view["id"], who))
    return view


def recover_tick() -> int:
    """v0.223 restart-proof long jobs: a goal still 'working' that nothing is running any more (the server restarted
    mid-round, or a round died) is picked up again - like Claude, a crash never silently throws the work away.
    Only when: not moved for agent_goal_recover_after_s, no turn holds the chat, no round of it pending in this
    process, nothing waits on her (then it pauses for the resume sweep), and at most agent_goal_recover_max times.
    A recovery never uses up a round."""
    st = get_settings()
    if not (st.agent_goal and getattr(st, "agent_goal_recover", True)):
        return 0
    from datetime import timedelta
    t = now()
    old = t - timedelta(seconds=max(60, int(getattr(st, "agent_goal_recover_after_s", 600))))
    too_old = t - timedelta(hours=max(1, st.agent_goal_resume_hours))
    with session() as s:
        rows = s.scalars(select(GoalRun).where(GoalRun.status == "working", GoalRun.paused_at.is_(None))
                         .limit(50)).all()
        todo = [(r.id, r.tenant_id, r.conversation_id, _aware(r.updated_at), int(r.recovered or 0)) for r in rows]
    from .santosh import _locks
    n = 0
    for gid, tenant, conv, upd, times in todo:
        if gid in _PENDING or conv in _STOPPED:
            continue
        if upd is None or upd > old or upd < too_old:
            continue                         # still moving, or so old she has moved on (her next message carries it)
        if conv in _locks and _locks[conv].locked():
            continue                         # a turn is running it right now
        if _waiting_on_her(conv) or _waiting_on_job(conv):
            _pause(gid)                      # the resume sweep restarts it once she answers
            continue
        view = active_for(conv)
        if view is None or view["id"] != gid or not steps_left(view):
            continue
        if times >= max(1, int(getattr(st, "agent_goal_recover_max", 3))):
            _hold_for_limit(tenant, view)    # restarted too often: stop and ask her instead of looping
            continue

        def bump(r: GoalRun):
            r.recovered = int(r.recovered or 0) + 1
        _mutate(tenant, gid, bump)
        try:
            from ..db import Message
            line = f"Server dobara chalu hua — aapka kaam \"{view['goal'][:80]}\" wahin se aage badha raha hoon " \
                   f"({view['done']}/{view['total']} steps ho chuke)."
            with session() as s:
                s.add(Message(conversation_id=conv, role="assistant", content=line, display=line,
                              in_history=False, delivered_to_agent=True))
            bus.publish(conv, "message", {"role": "assistant", "text": line, "source": "goal"})
        except Exception:
            log.exception("recovery note failed")
        if _schedule(conv, tenant, view, count_round=False):
            STATS["recovered"] += 1
            n += 1
    return n
