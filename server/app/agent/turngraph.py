"""G0 of docs/LANGGRAPH_TURN_PLAN.md - the chat turn's think -> tools loop as an official LangGraph StateGraph.

Behind `chat_graph` (default OFF). `santosh._steps` hands the whole turn here when the switch is on; when it is off
nothing in this module runs.

THE GRAPH ONLY: no LangChain model or tool wrapper rides here. Every node calls the SAME step function the old
while-loop calls (one copy of every step, so the two paths cannot drift):

    prepare  = santosh._steps_begin (breaker, big / hard ask, goal caps, learned hint)
               + santosh._turn_prepare (brain, admission, system prompt, tools, live reply)
    model    = the step cap check + santosh._turn_model (one model call: brain fallbacks, thinking, effort, live
               stream, Rokiye mid-call); a tool_use step is recorded at once by santosh._turn_after_model
    check    = santosh._turn_after_model for an answer: the held hard answer, the plain check, the nudges (goal,
               promise, max_tokens) -> back to `model`, or the answer stands -> `finish`
    tools    = santosh._turn_tools (every tool through santosh._run_tool: approvals, money-on-her-tap, redaction,
               logging, the breaker, the parallel-safe set, steering, narration, auto plan)
    finish   = santosh._turn_capped (the step cap ran out) / santosh._turn_silent (a silent answer) and
               santosh._steps_end (outcome, LAST_OUTCOME, work diary, learning)

    START -> prepare -> model -> (tools -> model | check -> (model | finish) | finish) ; finish -> END

State: the checkpointed part is plain data (conversation, turn id, the Anthropic-format messages, the step count,
the route, the final text, the outcome). The live objects (ctx, settings, the breaker, the live reply, the turn's
locals) never go into a checkpoint - they sit in `_RUNS` under the run key for the life of the turn.

Context variables: LangGraph runs every node in its own task, so a ContextVar set in one node (the turn's effort /
model / reasoning / ASK_NOW) would be lost by the next one. Every node body therefore runs in ONE shared
`contextvars.Context` taken when the turn starts - exactly the single-task semantics of the old loop.

Checkpointer: an AsyncSqliteSaver at <chat_graph_dir>/checkpoints.db, thread_id = "<conversation>:<turn id>".

G1 (durability): the turn id is the turn_inbox row id when the turn came through the inbox (stable, so the restart
sweep can find the thread), else a fresh id. Each node also checkpoints the turn's plain-data state (`data`: the
_steps_begin dict minus live objects, the breaker's counters, the admitted families). `resume()` rebuilds the live
objects from that (never re-saving her message, never re-running a finished node) and continues the graph from its
last checkpoint. Tools on the graph path go through the tool ledger (`agent/toolledger.py`): intent before, done /
failed after; on resume a done tool is reused, an interrupted read is re-run, an interrupted send / order / delete /
payment is NOT re-run (the model is told the outcome is unknown). A turn that reaches END (or ends in an error reply)
has its checkpoints and ledger rows deleted.

G2 (one run per chat + Stop as state, `agent/turnrun.py`): the turn runs under its chat's ticket (taken in run_turn,
arrival order; the inbox row comes from the ticket, task-checked, so a background task that inherited the inbox
context can never pass itself off as that row's turn). A Stop sets the live run's flag: the model node does not make
its call when the flag is already set (it says the same line a Stop during the call says, `santosh._turn_halted`),
the tools node runs none of the step's tools (`_turn_tools`' own Stop result), every node's update carries
`stopped` into the checkpoint (never resumable), a tool cut by her Stop is `failed` / `stopped` in the ledger, and a
stopped run keeps its ledger rows (its checkpoints still go).

G4 (long jobs = ONE thread continuing). A long job (an open kaam_plan goal with steps left) has its own thread,
"<conversation>:job-<goal id>". When a turn of HER job (her own words, a round of her job, a routine's job - never a
wake, never a call's quick brain turn) reaches `finish` with steps still open, `finish` routes to the `carry` node and
the graph is compiled with interrupt_before=["carry"]: the run stops right there, checkpointed. If that turn ran on
another thread (her inbox turn, a fallback round), its newest checkpoint is copied onto the job thread (`_park`: the
latest turn's state wins - its messages are the fullest -, the job's earlier tool facts are merged in, its ledger rows
move with it). The job then continues through the existing round machinery (goal.maybe_continue -> _schedule ->
_continuation: her authority, the rounds / minutes limits and their "Shall I carry on?" ask, the waiting-on-her pause,
Rokiye), but the round does not start a fresh turn: `_continuation` sets JOB_RUN and `run_steps` resumes the job thread
with ainvoke(None) - at `carry` that is the next SEGMENT (resume() rebuilds the round's fresh per-segment state - step
budget, breaker, nudge budget, deadline - over the thread's own messages plus what the chat saved since the segment
ended: her messages, the round's "[Goal jaari ...]" line); anywhere else (a restart or a segment deadline cut it
mid-way) it is the SAME segment continuing from its last finished node, the tool ledger deciding an interrupted tool
exactly as G1 (a done tool reused, a read run again, a send / order never re-sent). A segment cut by its deadline is
parked the same way (`park_cut`), so a budget never throws the job away. A turn that reaches END cleans its own
thread, and the job threads of this chat's finished / failed / stopped goals.

G5 (outcome + ONE delivery node, `agent/turndeliver.py`). `finish` -> `deliver` -> (carry | END): every run of the graph
ends in `deliver`, the one place on the graph path that tells her the result. It puts the outcome into the state
(`result`: done / partial / stuck / stopped / failed - from her G2 Stop, the G4 job's own status, the breaker, the step
cap and the G3 facts) and the `notified` record (chat row + SSE, push, live-call note, ring - with times and the target
chat), backed by a durable turn_deliveries row keyed by the outcome's idempotency key (`dkey`, minted by prepare /
carry and checkpointed, so a resumed run delivers under the SAME key). The chat row is the one the turn's own step
already wrote and streamed (found by row id after `dmark`, the chat's newest message when the run began) - the node
writes it only when no step did, row + stamp in one transaction. Push rides that row's own `message` event
(push.on_event's gates: quiet hours, a live call, the night hold). A result that is NEWS - a finished job's wake report
(kaam_followup sets turndeliver.NEWS) or a long job that ended in a background run (a goal round, a routine) - also
gets the quiet note into her live call and the voice ring, each at most once (intent stamped before, sent after). The
jobs this reply told (the goal that ended during the run; a watched job that started and ended in it) are written as
`job:<key>:<state>` aliases: kaam_followup asks THAT record instead of its timing guess (`_answered_since`), so a long
job's final report is told exactly once, by this node, in the job's own chat.
"""
from __future__ import annotations

import asyncio
import contextvars
import copy
import json
import logging
import os
import time as _time
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from typing import Any, TypedDict

log = logging.getLogger("santosh.turngraph")

try:   # the official library (MIT). Missing on a box = the old loop answers, said once in the log
    from langgraph.graph import END, START, StateGraph
    AVAILABLE = True
except Exception:   # noqa: BLE001
    AVAILABLE = False
try:
    from langgraph.errors import NodeCancelledError as _NodeCancelled
except Exception:   # noqa: BLE001
    class _NodeCancelled(Exception):   # an older langgraph re-raises CancelledError itself
        pass

STATS = {"turns": 0, "fallback": 0, "no_checkpoint": 0, "resumed": 0, "cleaned": 0, "stopped_at_boundary": 0,
         "parked": 0, "copied": 0, "segments": 0, "job_resumed": 0, "job_fresh": 0, "job_gone": 0, "cut_parked": 0,
         "jobs_forgotten": 0}
_RESUMABLE = ("model", "tools", "check", "finish", "deliver", "carry")

# G4: the goal a round of a long job continues (set by goal._continuation around its run_turn; taken once by run_steps)
JOB_RUN: contextvars.ContextVar = contextvars.ContextVar("turngraph_job_run", default=None)
_CUT: dict[str, str] = {}      # G4: conversation -> the thread a cancelled run left behind (a segment deadline parks it)
_FACTS_KEEP = 300              # G4: a job's tool facts across all its segments (newest kept)


class TurnState(TypedDict, total=False):
    conversation_id: str
    turn_id: str
    run_key: str
    messages: list          # the turn's history (Anthropic-format dicts) as of the last node - data only
    ran_steps: int
    route: str              # where the last node sends the turn: model | tools | check | finish
    capped: bool            # the step cap ran out (the old while-else)
    done: bool              # final_text is already the turn's answer (stopped / stuck / paused)
    final_text: str
    outcome: str
    prepared: bool          # G1: prepare finished (a checkpoint before it has nothing worth resuming)
    stop: str               # G1: the last model step's stop reason (the check node needs it on resume)
    data: dict              # G1: the turn's plain-data state (see _data) - what resume rebuilds the live objects from
    stopped: bool           # G2: she stopped this run (Stop / stop words) - never resumable, checked at every node
    facts: list             # G3: one fact per tool_use of the turn (agent/turnfacts.py: did / card / read / failed /
                            # ambiguous / stopped / skipped + ledger state + object) - what the check node judges by
    decision: dict          # G3: the check node's last decision (kind, why, back = the model was sent back to work)
    decisions: list         # G3: every decision of the turn (newest last, capped)
    nudges: dict            # G3: the check node's one budget, spent per kind (turnfacts.CAPS / TOTAL)
    dkey: str               # G5: this run's delivery (idempotency) key - minted by prepare / carry, checkpointed
    dmark: int              # G5: the chat's newest message id when this run began (its reply rows come after it)
    result: str             # G5: the outcome as one word: done | partial | stuck | stopped | failed
    delivery: dict          # G5: {key, kind turn | news | job, target chat, jobs told}
    notified: dict          # G5: what she was told on which channel (chat / push / call / ring: state, time, row)


class _Live:
    """What a turn needs that is not data: never checkpointed."""

    def __init__(self, conversation_id, ctx, gender, history, settings, tenant_id, user_text):
        self.conversation_id, self.ctx, self.gender = conversation_id, ctx, gender
        self.history, self.settings, self.tenant_id, self.user_text = history, settings, tenant_id, user_text
        self.state: dict = {}
        self.t = None                                  # santosh._Turn
        self.cv = contextvars.copy_context()           # the ONE context every node body runs in
        self.thread = ""                               # G1: the checkpoint thread (the ledger's key); '' = no ledger
        self.facts: list = []                          # G3: the turn's facts / the check node's decisions + budget
        self.decisions: list = []
        self.used: dict = {}
        self.job: dict = {}                            # G4: the long job's counters (goal, segments, steps, seconds, mark)


_RUNS: dict[str, _Live] = {}


def _stop_now(live: _Live) -> bool:
    """G2 STOP AS STATE: the chat's live run was stopped (the Stop button / kaamstop both end in santosh.stop)."""
    from . import santosh as S
    from . import turnrun
    c = live.conversation_id
    return c in S._stopped or turnrun.stopped(c)


def _flag(live: _Live, out: dict) -> dict:
    """Every node's update carries the stop flag once it is set (the checkpoint then says 'stopped')."""
    if _stop_now(live):
        out["stopped"] = True
    return out


def _snapshot(history: list) -> list:
    """The messages as plain JSON data for the checkpoint (a block that is not JSON is written as text)."""
    try:
        return json.loads(json.dumps(history, ensure_ascii=False, default=str))
    except Exception:   # noqa: BLE001
        return []


def _breaker_data(b) -> dict:
    out = {}
    for k, v in vars(b).items():
        if isinstance(v, Counter):
            out[k] = dict(v)
        elif isinstance(v, set):
            out[k] = sorted(v)
        elif isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, list):
            try:
                out[k] = json.loads(json.dumps(v))
            except Exception:   # noqa: BLE001
                pass
    return out


def _data(live: _Live) -> dict:
    """The turn's state as plain data (G1): every JSON-able key of the _steps_begin dict (live objects - the breaker,
    the native tool list - are left out), the breaker's counters, the admitted tool families, the turn's final text."""
    out: dict = {}
    for k, v in (live.state or {}).items():
        if k in ("breaker", "native_tools"):
            continue
        try:
            out[k] = json.loads(json.dumps(v, ensure_ascii=False))
        except Exception:   # noqa: BLE001
            if isinstance(v, (list, dict)):
                try:
                    out[k] = json.loads(json.dumps(v, ensure_ascii=False, default=str))
                except Exception:   # noqa: BLE001
                    pass
    b = (live.state or {}).get("breaker")
    if b is not None:
        out["__breaker"] = _breaker_data(b)
    t = live.t
    if t is not None:
        out["__final_text"] = t.final_text or ""
        if t.adm is not None:
            out["__adm"] = sorted(t.adm.families)
    if live.job:
        out["__job"] = dict(live.job)
    return out


def _g3(live: _Live) -> dict:
    """G3: the facts + the check node's decisions as plain data for the checkpoint."""
    j = getattr(live.t, "judge", None) if live.t is not None else None
    return {"facts": _snapshot(live.facts), "decisions": _snapshot(live.decisions), "nudges": dict(live.used),
            "decision": dict(j.last) if (j is not None and j.last) else {}}


def _judge(live: _Live) -> None:
    """G3: the graph's check node judges the answer from the turn's facts (santosh._turn_after_model asks t.judge)."""
    from . import turnfacts
    live.t.judge = turnfacts.Judge(live.t, live.facts, live.decisions, live.used, stopped=lambda: _stop_now(live))


def _record_facts(live: _Live, n_calls: int) -> None:
    """G3: after a tools step - one fact per tool_use of the step, from its call record, its tool_result and its G1
    ledger row (never from the reply's words)."""
    from . import toolledger as L
    from . import turnfacts
    t = live.t
    try:
        calls = (t.state.get("calls") or [])[n_calls:]
        ids = {b.get("id") for b in t.blocks or [] if b.get("type") == "tool_use"}
        results = []
        for m in reversed(live.history):
            c = m.get("content")
            if m.get("role") == "user" and isinstance(c, list) and any(
                    isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in ids for b in c):
                results = c
                break
        rows = {}
        if live.thread:
            for i in ids:
                try:
                    r = L.get(live.thread, i)
                except Exception:   # noqa: BLE001
                    r = None
                if r:
                    rows[i] = r
        live.facts.extend(turnfacts.step_facts(t.blocks, results, calls, t.ran_steps, rows))
    except Exception:   # noqa: BLE001 - a fact that cannot be written never breaks her turn (the check then knows less)
        log.exception("turn facts could not be recorded")


def _node(fn):
    """Run a node body inside the turn's one Context (see the module note)."""
    async def node(state: TurnState) -> dict:
        live = _RUNS[state["run_key"]]
        return await asyncio.create_task(fn(live, state), context=live.cv)
    node.__name__ = fn.__name__
    return node


async def _prepare(live: _Live, state: TurnState) -> dict:
    from . import santosh as S
    live.state = await S._steps_begin(live.conversation_id, live.ctx, live.history, live.settings, live.tenant_id,
                                      live.user_text)
    live.t = await S._turn_prepare(live.conversation_id, live.ctx, live.gender, live.history, live.settings,
                                   live.tenant_id, live.state)
    if live.thread:
        live.t.tool_runner = _ledger_runner(live.thread)
    _judge(live)
    # a Stop that landed while preparing is seen at the model node's boundary (no model call is made)
    return _flag(live, {"messages": _snapshot(live.history), "ran_steps": 0, "route": "model", "prepared": True,
                        "data": _data(live), **_g3(live), **_dnew(state.get("run_key", ""), live.conversation_id)})


async def _model(live: _Live, state: TurnState) -> dict:
    from . import santosh as S
    t = live.t
    if not t.ran_steps < t.cap():          # the old `while ran_steps < cap` fell through to its else
        return _flag(live, {"route": "finish", "capped": True})
    if _stop_now(live):                    # G2 boundary: stopped before this step - the same line a Stop during the
        STATS["stopped_at_boundary"] += 1  # model call gives, without making the call
        got = S._turn_halted(t, "stop")
        return {"route": "finish", "done": True, "final_text": got, "ran_steps": t.ran_steps, "stopped": True,
                "messages": _snapshot(live.history), "data": _data(live)}
    t.ran_steps += 1
    got = await S._turn_model(t)
    if isinstance(got, str):               # Rokiye / Pause landed during the model call
        return _flag(live, {"route": "finish", "done": True, "final_text": got, "ran_steps": t.ran_steps,
                            "messages": _snapshot(live.history), "data": _data(live)})
    blocks, stop = got
    t.blocks, t.stop = blocks, stop
    route = "check"
    if stop == "tool_use":                 # the step is recorded (saved + shown) before its tools run, as before
        route = await S._turn_after_model(t, blocks, stop)
    return _flag(live, {"route": route, "ran_steps": t.ran_steps, "messages": _snapshot(live.history),
                        "stop": stop or "", "data": _data(live)})


async def _check(live: _Live, state: TurnState) -> dict:
    from . import santosh as S
    t = live.t
    # G2: a stopped run still keeps the answer the model already gave (as the old loop does); a nudge that sends it
    # back to work ends at the model node's boundary instead
    # G3: the one place that may send the model back to work (false claim, reminder promise, self-check, open plan
    # step, promise without action, max_tokens) - t.judge decides from the turn's facts, inside the shared step
    j = t.judge
    if j is not None:
        j.last = None
    route = await S._turn_after_model(t, t.blocks, t.stop)
    if j is not None and j.last is None:   # sent back / ended by a step the judge does not own (the held hard answer)
        j._record("hard_fix" if route == "model" else "stand",
                  "the held hard answer failed its check: one fix round" if route == "model"
                  else "the answer stands", back=(route == "model"))
    return _flag(live, {"route": route, "final_text": t.final_text or "", "messages": _snapshot(live.history),
                        "data": _data(live), **_g3(live)})


async def _tools(live: _Live, state: TurnState) -> dict:
    from . import santosh as S
    t = live.t
    # G2 boundary: a Stop already set = _turn_tools runs none of the step's tools (each gets the "tapped Stop" result,
    # the same rows as the old loop) and ends the turn with the stop line
    n_calls = len(t.state.get("calls") or [])
    try:
        done = await S._turn_tools(t, t.blocks)
    finally:
        _record_facts(live, n_calls)       # G3: what each tool really did (also when the step ends the turn)
    if done is not None:                   # stuck (breaker) / stopped: the turn ends with this line
        return _flag(live, {"route": "finish", "done": True, "final_text": done, "messages": _snapshot(live.history),
                            "data": _data(live), **_g3(live)})
    return _flag(live, {"route": "model", "messages": _snapshot(live.history), "data": _data(live), **_g3(live)})


async def _finish(live: _Live, state: TurnState) -> dict:
    from . import santosh as S
    t = live.t
    if state.get("done"):
        text = state.get("final_text") or ""
    elif state.get("capped"):
        text = S._turn_capped(t)
    else:
        text = S._turn_silent(t)
    from . import turnfacts
    note = turnfacts.left_note(live.facts)
    if note and not live.state.get("left"):
        live.state["left"] = note          # G3: a step whose outcome is unknown is never reported as done
    text = await S._steps_end(live.conversation_id, live.ctx, live.history, live.settings, live.tenant_id,
                              live.user_text, live.state, text)
    out = (S.LAST_OUTCOME.get(live.conversation_id) or {}).get("outcome", "") if live.user_text else ""
    # G4: her long job still has open steps - this run stops at the segment boundary (interrupt before `carry`) and
    # the job continues on its own thread instead of a fresh round turn
    g = _job_goal(live) if not (state.get("stopped") or _stop_now(live)) else None
    route = "end"
    if g is not None:
        live.job = _job_counts(live, g)
        route = "carry"
    return {"final_text": text, "outcome": out, "route": route, "messages": _snapshot(live.history),
            "data": _data(live), **_g3(live)}


async def _carry(live: _Live, state: TurnState) -> dict:
    """G4: the next segment of the same long-job thread. resume() already rebuilt the turn for it (the round's fresh
    per-segment state - step budget, breaker, nudge budget -, the thread's messages plus what the chat saved since the
    last segment ended, the system prompt); this node clears the last segment's ending and sends the job back to work."""
    STATS["segments"] += 1
    return _flag(live, {"route": "model", "ran_steps": 0, "capped": False, "done": False, "final_text": "",
                        "outcome": "", "stop": "", "messages": _snapshot(live.history), "data": _data(live),
                        **_g3(live), **_dnew(state.get("run_key", ""), live.conversation_id),
                        "result": "", "delivery": {}, "notified": {}})


def _dnew(run_key: str, conversation_id: str) -> dict:
    """G5: a fresh delivery key + mark for a run (a plain turn, or one segment of a long job)."""
    from . import turndeliver as D
    return {"dkey": f"turn:{run_key}:{uuid.uuid4().hex[:8]}"[:200], "dmark": D.max_msg_id(conversation_id)}


def _result(live: _Live, state: TurnState, jobs: list) -> str:
    """G5: the run's outcome as one word, from the run's own state - her Stop (G2), the long job's status (G4), the
    breaker / the outcome _steps_end wrote, the step cap, and the G3 facts (every tool failed = failed)."""
    from . import santosh as S
    c = live.conversation_id
    st = live.state or {}
    if state.get("stopped") or _stop_now(live) or st.get("halted") or c in S._stopped:
        return "stopped"
    mine = [j for j in jobs if j.get("key", "").startswith("goal:")]
    if mine:
        return {"done": "done", "failed": "failed", "stopped": "stopped"}.get(mine[0]["state"], "partial")
    b = st.get("breaker")
    lo = (S.LAST_OUTCOME.get(c) or {}).get("outcome", "") if live.user_text else ""
    if lo == "stuck" or (b is not None and getattr(b, "stopped", False)):
        return "stuck"
    if state.get("route") == "carry" or state.get("capped") or lo in ("partial", "continuing") or st.get("left"):
        return "partial"
    effects = [str((f or {}).get("effect") or "") for f in live.facts]
    if effects and all(e == "failed" for e in effects):
        return "failed"
    return "done"


async def _deliver(live: _Live, state: TurnState) -> dict:
    """G5: the ONE place on the graph path that tells her the result (see the module note and agent/turndeliver.py).
    Never raises into her turn: a delivery record that cannot be written leaves today's behaviour for that run."""
    from . import santosh as S
    from . import turndeliver as D
    c, tenant, settings = live.conversation_id, live.tenant_id, live.settings
    key = state.get("dkey") or f"turn:{state.get('run_key', '')}:legacy"
    mark = int(state.get("dmark") or 0)
    actor = getattr(live.ctx, "actor", "owner") or "owner"
    try:
        news = D.NEWS.get()
        if not (isinstance(news, dict) and news.get("conv") == c and news.get("key")):
            news = None
        t0 = float((live.state or {}).get("t0") or 0) or _time.time()
        jobs = D.ended_jobs(c, t0) if state.get("route") != "carry" else []
        result = _result(live, state, jobs)
        target = D.target_chat(c, tenant)
        if news:
            key = news["key"]
        mine = next((j for j in jobs if j["key"].startswith("goal:")), jobs[0] if jobs else None)
        kind = "news" if news else ("job" if mine else "turn")
        D.record(key, tenant, target, thread=state.get("run_key", ""), kind=kind,
                 job_key=(news or {}).get("job_key") or (mine or {}).get("key", ""),
                 job_state=(news or {}).get("state") or (mine or {}).get("state", ""), outcome=result, mark=mark)
        rec = D.get(key) or {}
        mark = int(rec.get("mark") or mark)
        # 1. the chat: the reply row the turn's own step wrote (and streamed) - found by row id, never by time
        row = None
        if not D.done(key, "chat"):
            row = D.final_row_since(target, mark, str(state.get("final_text") or "")) if target == c else None
            if row is not None:
                D.stamp(key, "chat", D.SENT, row=row, by="step", chat=target)
                D.STATS["chat_step"] += 1
            else:
                text = str(state.get("final_text") or "").strip()
                if text:          # no step wrote it (a chat that is gone, an ending with no row): once, here
                    row = D.write_chat(key, target, text)
        rec = D.get(key) or {}
        chat = rec.get("channels", {}).get("chat") or {}
        row = row or chat.get("row")
        # 2. push: the reply's own `message` event already went through push.on_event and its gates (quiet hours,
        # a live call on the chat, the night hold) - recorded, never pushed a second time
        if chat.get("state") == D.SENT and not D.done(key, "push"):
            D.stamp(key, "push", D.SENT, via="the reply's message event (push.on_event gates)")
            D.STATS["push"] += 1
        # 3. news (a wake report; a long job that ended in a background run): the live-call note + the ring, once each
        hers = actor == "owner" or actor.startswith("approved:")
        src = news or ({"job_key": mine["key"], "state": mine["state"], "title": mine.get("title", "")} if mine else {})
        if (bool(news) or bool(mine and not hers)) and not S.VOICE_BRAIN_NOW.get():
            text = D.reply_text(row) or str(state.get("final_text") or "")
            D.news_channels(key, tenant, target, text, src.get("job_key", ""), src.get("state", ""),
                            src.get("title", ""), settings)
        # 4. the jobs this reply told: kaam_followup asks these records, never a timing guess
        if chat.get("state") == D.SENT:
            if news and news.get("job_key"):    # the report this wake turn was woken for (queued before it ran)
                D.job_told(news["job_key"], news.get("state", ""), key, tenant, target, since=0.0)
            for j in jobs:                      # the jobs that ended during this run (their reports queue in it)
                D.job_told(j["key"], j["state"], key, tenant, target, since=t0)
        rec = D.get(key) or {}
        return {"result": result, "notified": rec.get("channels") or {},
                "delivery": {"key": key, "kind": kind, "target": target, "jobs": [j["key"] for j in jobs]}}
    except Exception:   # noqa: BLE001
        log.exception("turn graph: the delivery record could not be written")
        return {"result": "", "delivery": {"key": key, "error": True}}


def _job_ok(live: _Live) -> bool:
    """G4: may this turn's ending become a job segment? HER job's turns (her words, her tap, a round of her job) and a
    routine's (the round rules of goal.maybe_continue), with a checkpoint to continue from; never a wake (it never
    chains into the job), never a call's quick brain turn (it reads only the last few exchanges - a poor job context)."""
    from . import goal as _goal
    from . import santosh as S
    if not live.thread or not getattr(live.settings, "agent_goal", False):
        return False
    actor = getattr(live.ctx, "actor", "owner") or "owner"
    if actor == "wake" or not (_goal.hers(actor) or actor == "routine"):
        return False
    return not S.VOICE_BRAIN_NOW.get()


def _job_goal(live: _Live) -> dict | None:
    """G4: the chat's open long job (a working goal with steps left), when this turn may continue it."""
    if not _job_ok(live):
        return None
    from . import goal as _goal
    try:
        g = _goal.active_for(live.conversation_id)
    except Exception:   # noqa: BLE001
        log.exception("job goal check failed")
        return None
    return g if (g is not None and _goal.steps_left(g)) else None


def _max_msg_id(conversation_id: str) -> int:
    from sqlalchemy import func, select
    from ..db import Message, session
    try:
        with session() as s:
            return int(s.scalar(select(func.max(Message.id)).where(Message.conversation_id == conversation_id)) or 0)
    except Exception:   # noqa: BLE001
        log.exception("message mark failed")
        return 0


def _job_counts(live: _Live, g: dict) -> dict:
    """G4: the job's counters after this segment (they ride in the checkpoint's data, across every segment)."""
    prev = dict(live.job or {})
    if prev.get("goal") != g.get("id"):
        prev = {"goal": g.get("id"), "segments": 0, "steps": 0, "seconds": 0.0}
    t0 = float((live.state or {}).get("t0") or _time.time())
    prev["segments"] = int(prev.get("segments") or 0) + 1
    prev["steps"] = int(prev.get("steps") or 0) + int(getattr(live.t, "ran_steps", 0) or 0)
    prev["seconds"] = round(float(prev.get("seconds") or 0) + max(0.0, _time.time() - t0), 1)
    prev["mark"] = _max_msg_id(live.conversation_id)    # what the chat had saved when this segment ended
    return prev


def job_thread(conversation_id: str, goal_id: str) -> str:
    """G4: the one thread of a long job."""
    return thread_id(conversation_id, f"job-{goal_id}")


def _take_job(conversation_id: str) -> str | None:
    """The goal id a round of this chat's long job continues (once; another chat's nested turn never takes it)."""
    v = JOB_RUN.get()
    if not v or v[0] != conversation_id or not v[1]:
        return None
    JOB_RUN.set(None)
    return str(v[1])


def _job_messages(saved: list, conversation_id: str, mark: int) -> list:
    """G4: the job thread's own messages + everything the chat saved (in history) since its last segment ended: her
    messages in between, the round's own line. Repaired like a loaded history (same-role turns merged)."""
    from sqlalchemy import select
    from . import santosh as S
    from ..db import Message, session
    msgs = json.loads(json.dumps(saved or []))
    try:
        with session() as s:
            rows = s.scalars(select(Message).where(Message.conversation_id == conversation_id,
                                                   Message.in_history.is_(True), Message.id > int(mark or 0))
                             .order_by(Message.id).limit(400)).all()
            msgs += [{"role": r.role, "content": r.content} for r in rows if r.role in ("user", "assistant")]
    except Exception:   # noqa: BLE001
        log.exception("job messages since the last segment could not be read")
    return S._sanitize(json.loads(json.dumps(msgs, ensure_ascii=False, default=str)))


def _merge_facts(old: list | None, new: list | None) -> list:
    """The job's facts: the earlier segments' + this run's (one per tool_use id, the newest kept)."""
    out: dict = {}
    for i, f in enumerate(list(old or []) + list(new or [])):
        k = (f or {}).get("id") or f"_{i}"
        out.pop(k, None)
        out[k] = f
    return list(out.values())[-_FACTS_KEEP:]


def _merge_job(old: dict | None, new: dict | None, goal_id: str) -> dict:
    o = dict(old or {}) if (old or {}).get("goal") == goal_id else {}
    n = dict(new or {}) if (new or {}).get("goal") == goal_id else {}
    out = {"goal": goal_id}
    for k in ("segments", "steps"):
        out[k] = int(o.get(k) or 0) + int(n.get(k) or 0)
    out["seconds"] = round(float(o.get("seconds") or 0) + float(n.get("seconds") or 0), 1)
    out["mark"] = int(n.get("mark") or o.get("mark") or 0)
    return out


async def _park(saver, src: str, conversation_id: str, goal_id: str) -> bool:
    """G4: the job continues on its own thread. A run on the job thread already stopped there (nothing to do); a run
    on another thread is copied onto it - its newest checkpoint exactly (so the next node is kept: `carry` at a
    segment boundary, the cut node after a deadline), with the job's earlier facts / counters merged in, its ledger
    rows moved, and its own thread deleted."""
    from . import toolledger as L
    jt = job_thread(conversation_id, goal_id)
    if src == jt:
        STATS["parked"] += 1
        return True
    try:
        tup = await saver.aget_tuple({"configurable": {"thread_id": src, "checkpoint_ns": ""}})
        if tup is None:
            return False
        old = await saver.aget_tuple({"configurable": {"thread_id": jt, "checkpoint_ns": ""}})
        ck = copy.deepcopy(tup.checkpoint)
        cv = ck.setdefault("channel_values", {})
        cv["run_key"], cv["turn_id"] = jt, f"job-{goal_id}"
        oldv = ((old.checkpoint or {}).get("channel_values") or {}) if old is not None else {}
        odata = dict(oldv.get("data") or {})
        if "facts" in cv:
            cv["facts"] = _merge_facts(oldv.get("facts"), cv.get("facts"))
        if isinstance(cv.get("data"), dict):
            d = dict(cv["data"])
            d["__job"] = _merge_job(odata.get("__job"), d.get("__job"), goal_id)
            cv["data"] = d
        await saver.setup()
        await saver.adelete_thread(jt)
        cfg = await saver.aput({"configurable": {"thread_id": jt, "checkpoint_ns": ""}}, ck, tup.metadata,
                               dict(ck.get("channel_versions") or {}))
        by_task: dict = {}
        for task_id, channel, value in tup.pending_writes or []:
            by_task.setdefault(task_id, []).append((channel, value))
        for task_id, writes in by_task.items():
            await saver.aput_writes(cfg, writes, task_id)
        await _ledger(L.move, src, jt)
        await saver.adelete_thread(src)
        STATS["copied"] += 1
        STATS["parked"] += 1
        return True
    except Exception:   # noqa: BLE001 - a job that cannot be parked falls back to today's fresh round
        log.exception("turn graph: the long job could not be parked on its thread")
        return False


async def park_cut(conversation_id: str, settings, actor: str = "owner") -> bool:
    """G4 (santosh._run_turn, a turn cut by its deadline): budgets do not kill - the cut run's checkpoint becomes the
    job thread, so the next round continues from the node that was cut (the ledger decides the tool that was cut)."""
    src = _CUT.pop(conversation_id, None)
    if not AVAILABLE or not src or not getattr(settings, "agent_goal", False):
        return False
    from . import goal as _goal
    from . import santosh as S
    a = actor or "owner"
    if a == "wake" or not (_goal.hers(a) or a == "routine") or S.VOICE_BRAIN_NOW.get():
        return False
    g = _goal.active_for(conversation_id)
    if g is None or not _goal.steps_left(g):
        return False
    async with _saver(settings, create=False) as saver:
        if saver is None:
            return False
        ok = await _park(saver, src, conversation_id, g["id"])
    if ok:
        STATS["cut_parked"] += 1
        log.warning("turn graph: a cut segment of job %s is parked on its thread", g["id"])
    return ok


async def job_next(settings, conversation_id: str, goal_id: str) -> str | None:
    """G4: the node a long job's thread continues at ('carry' = the next segment; another node = the segment a
    restart / deadline cut), or None when it has nothing resumable."""
    if not AVAILABLE or not goal_id:
        return None
    try:
        async with _saver(settings, create=False) as saver:
            if saver is None:
                return None
            snap = await _compile(saver).aget_state({"configurable": {"thread_id": job_thread(conversation_id,
                                                                                               goal_id)}})
            return snap.next[0] if _resumable_snap(snap) else None
    except Exception:   # noqa: BLE001
        log.exception("job thread check failed")
        return None


async def forget_job(settings, conversation_id: str, goal_id: str) -> None:
    """G4: a job that is over (stopped / finished / replaced) leaves no thread behind."""
    if not AVAILABLE or not goal_id:
        return
    await forget_threads(settings, [job_thread(conversation_id, goal_id)])
    STATS["jobs_forgotten"] += 1


async def _forget_ended_jobs(saver, conversation_id: str, keep: str = "") -> None:
    """G4 housekeeping at a turn's END: the job threads of this chat's goals that are over (done / failed / stopped)
    go. A goal held for her answer or her 'carry on' (blocked) keeps its thread - her yes continues it."""
    from sqlalchemy import select
    from . import goal as _goal
    from . import toolledger as L
    from ..db import session
    try:
        with session() as s:
            ids = list(s.scalars(select(_goal.GoalRun.id).where(
                _goal.GoalRun.conversation_id == conversation_id,
                _goal.GoalRun.status.in_(("done", "failed", "stopped")))
                .order_by(_goal.GoalRun.updated_at.desc()).limit(5)).all())
    except Exception:   # noqa: BLE001
        log.debug("ended jobs lookup failed", exc_info=True)
        return
    for gid in ids:
        jt = job_thread(conversation_id, gid)
        if jt == keep:
            continue
        try:
            await saver.setup()
            await saver.adelete_thread(jt)
        except Exception:   # noqa: BLE001
            log.debug("job thread forget failed", exc_info=True)
        await _ledger(L.forget, jt, 0)


def _route(state: TurnState) -> str:
    return state.get("route") or "finish"


def build():
    """The turn graph (uncompiled)."""
    g = StateGraph(TurnState)
    g.add_node("prepare", _node(_prepare))
    g.add_node("model", _node(_model))
    g.add_node("check", _node(_check))
    g.add_node("tools", _node(_tools))
    g.add_node("finish", _node(_finish))
    g.add_node("deliver", _node(_deliver))  # G5: the one node that tells her the result
    g.add_node("carry", _node(_carry))      # G4: the next segment of a long job (the run stops before it)
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "model")
    g.add_conditional_edges("model", _route, {"tools": "tools", "check": "check", "finish": "finish",
                                              "model": "model"})
    g.add_conditional_edges("check", _route, {"model": "model", "finish": "finish", "tools": "tools"})
    g.add_conditional_edges("tools", _route, {"model": "model", "finish": "finish"})
    g.add_edge("finish", "deliver")
    g.add_conditional_edges("deliver", lambda s: "carry" if s.get("route") == "carry" else "end",
                            {"carry": "carry", "end": END})
    g.add_edge("carry", "model")
    return g


_BUILDER = None


def _builder():
    global _BUILDER
    if _BUILDER is None:
        _BUILDER = build()
    return _BUILDER


def _compile(saver):
    """The compiled turn graph. With a checkpointer a run stops BEFORE `carry` (G4: a long job's segment boundary is
    a checkpoint the next round continues from); without one `finish` never routes there."""
    if saver is None:
        return _builder().compile(checkpointer=None)
    return _builder().compile(checkpointer=saver, interrupt_before=["carry"])


def checkpoint_path(settings) -> str:
    d = getattr(settings, "chat_graph_dir", "") or "./data/turngraph"
    return os.path.join(d, "checkpoints.db")


def recursion_limit(settings) -> int:
    """Each model step is at most model + check + tools; the cap may rise to the goal cap mid-turn."""
    cap = max(int(getattr(settings, "agent_max_steps", 24) or 24),
              int(getattr(settings, "agent_goal_max_steps", 80) or 80))
    return 3 * cap + 10


def thread_id(conversation_id: str, turn_id: str) -> str:
    """The checkpoint thread of one turn. Never empty, never 'default' (one shared thread would mix every turn)."""
    c, t = str(conversation_id or "").strip(), str(turn_id or "").strip()
    if not c or not t or c == "default" or t == "default":
        raise ValueError(f"refusing a turn graph thread id from conversation={c!r} turn={t!r}")
    return f"{c}:{t}"


def _cfg(settings, thread: str) -> dict:
    return {"configurable": {"thread_id": thread}, "recursion_limit": recursion_limit(settings)}


async def _invoke(app, inp: TurnState | None, settings, thread_id: str) -> dict:
    return await app.ainvoke(inp, _cfg(settings, thread_id))


@asynccontextmanager
async def _saver(settings, create: bool = True):
    """The SQLite checkpointer (None when the file does not exist and create is False)."""
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    path = checkpoint_path(settings)
    if not create and not os.path.exists(path):
        yield None
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        yield saver


async def _ledger(fn, *a):
    """A ledger read / write never breaks a tool call (a failure = today's behaviour for that call). Run inline (one
    small indexed row, like every _save of the turn): a thread hop would reorder a parallel batch's results."""
    try:
        return fn(*a)
    except Exception:   # noqa: BLE001
        log.exception("tool ledger %s failed", getattr(fn, "__name__", "?"))
        return None


def _ledger_runner(thread: str):
    """The graph path's per-tool call: the ledger around santosh._run_tool (still the ONLY way a tool runs -
    approvals, money-on-her-tap, redaction and logging all live there)."""
    async def run(b: dict, args: dict, ctx, settings, mcp_route):
        from . import santosh as S
        from . import toolledger as L
        from .tools import ToolError
        name, tid = b["name"], b["id"]
        h = L.args_hash(args)
        row = await _ledger(L.get, thread, tid)
        if row and row.get("args_hash") == h:
            if row["state"] == "done":
                L.STATS["reused"] += 1
                try:
                    return json.loads(row["result"])
                except Exception:   # noqa: BLE001
                    return row["result"]
            if row["state"] == "failed":
                L.STATS["reused"] += 1
                kind, err = row.get("error_kind"), row.get("error") or ""
                if kind == "tool_error":
                    raise ToolError(err)
                if kind == "timeout":
                    raise asyncio.TimeoutError()
                raise RuntimeError(err)
            if not L.read_only(b):          # intent with no end: it may already have happened - never re-sent
                L.STATS["ambiguous"] += 1
                raise S.ToolAmbiguous(L.ambiguous_text(name))
            L.STATS["rerun_read"] += 1      # a look-up: running it again changes nothing in the world
        await _ledger(L.intent, thread, tid, name, h)
        try:
            out = await S._run_tool(name, args, ctx, settings, mcp_route)
        except ToolError as e:
            await _ledger(L.failed, thread, tid, "tool_error", str(e))
            raise
        except asyncio.TimeoutError:
            await _ledger(L.failed, thread, tid, "timeout", "")
            raise
        except asyncio.CancelledError:
            from . import turnrun
            c = getattr(ctx, "conversation_id", "") or ""
            if c and (c in S._stopped or turnrun.stopped(c)):
                # G2: SHE stopped it mid-call - the ledger says so (the run is never resumed; may have partly happened)
                await _ledger(L.failed, thread, tid, "stopped", "stopped by the owner while running")
                L.STATS["stopped"] = L.STATS.get("stopped", 0) + 1
            raise                            # cut off mid-call (a restart): stays `intent` (outcome unknown)
        except Exception as e:   # noqa: BLE001
            await _ledger(L.failed, thread, tid, "crash", f"{type(e).__name__}: {e}")
            raise
        await _ledger(L.done, thread, tid, out)
        return out
    return run


async def _cleanup(saver, thread: str, settings, force: bool = False, keep_ledger: bool = False) -> None:
    """The turn is over: its checkpoints and ledger rows go (the file must not grow without limit).
    G2 `keep_ledger`: a STOPPED run keeps its ledger rows (what ran, what was cut by her Stop) until the normal
    window ages them out; its checkpoints still go, so nothing can resume it."""
    from . import toolledger as L
    if saver is not None and (force or not getattr(settings, "chat_graph_keep_finished", False)):
        try:
            await saver.setup()               # adelete_thread does not create the tables on a fresh file
            await saver.adelete_thread(thread)
            STATS["cleaned"] += 1
        except Exception:   # noqa: BLE001
            log.exception("turn graph checkpoint cleanup failed")
    await _ledger(L.forget, "" if keep_ledger else thread,
                  float(getattr(settings, "chat_graph_ledger_keep_h", 24) or 0))


async def forget_threads(settings, threads: list[str]) -> None:
    """Housekeeping (turn_inbox sweep): threads whose inbox rows are long finished."""
    from . import toolledger as L
    if not AVAILABLE or not threads:
        return
    async with _saver(settings, create=False) as saver:
        for th in threads:
            if saver is not None:
                try:
                    await saver.setup()
                    await saver.adelete_thread(th)
                except Exception:   # noqa: BLE001
                    log.debug("checkpoint forget failed", exc_info=True)
            await _ledger(L.forget, th, 0)


def _resumable_snap(snap) -> bool:
    nxt = tuple(getattr(snap, "next", ()) or ())
    vals = getattr(snap, "values", None) or {}
    if vals.get("stopped"):                # G2: she stopped it - a restart never continues a stopped run
        return False
    return bool(nxt) and nxt[0] in _RESUMABLE and bool(vals.get("prepared")) and bool(vals.get("messages"))


async def delivery_due(settings, conversation_id: str, inbox_id: str) -> bool:
    """G5 (the restart sweep): this inbox row's turn already wrote its answer but its `finish` / `deliver` never ran -
    it is RESUMED there (the delivery completes once) instead of being marked done by the 'a final reply landed' guess."""
    if not AVAILABLE or not inbox_id:
        return False
    try:
        th = thread_id(conversation_id, inbox_id)
        async with _saver(settings, create=False) as saver:
            if saver is None:
                return False
            snap = await _compile(saver).aget_state({"configurable": {"thread_id": th}})
            return _resumable_snap(snap) and snap.next[0] in ("finish", "deliver")
    except Exception:   # noqa: BLE001
        log.exception("delivery check failed")
        return False


async def resumable(settings, conversation_id: str, inbox_id: str) -> bool:
    """Does the checkpointer hold an unfinished, resumable checkpoint for this inbox row's turn?"""
    if not AVAILABLE or not inbox_id:
        return False
    th = thread_id(conversation_id, inbox_id)
    async with _saver(settings, create=False) as saver:
        if saver is None:
            return False
        snap = await _compile(saver).aget_state({"configurable": {"thread_id": th}})
        return _resumable_snap(snap)


def _restore_state(data: dict, conversation_id: str, ctx, settings, user_text: str) -> dict:
    """The _steps_begin dict rebuilt from the checkpoint - no hard-ask judge, no procedure lookup run again."""
    from . import santosh as S
    from . import goal as _goal
    from .breaker import Breaker
    hers = (getattr(ctx, "actor", "owner") or "owner")
    S.ASK_NOW.set(user_text if (hers == "owner" or hers.startswith("approved:")) else "")
    state = {k: v for k, v in (data or {}).items() if not k.startswith("__")}
    state.setdefault("calls", [])
    state.setdefault("used", [])
    state.setdefault("request", user_text)
    state.setdefault("t0", _time.time())
    b = Breaker()
    for k, v in (data.get("__breaker") or {}).items():
        cur = getattr(b, k, None)
        if isinstance(cur, Counter):
            setattr(b, k, Counter(v or {}))
        elif isinstance(cur, set):
            setattr(b, k, set(v or []))
        else:
            setattr(b, k, v)
    state["breaker"] = b
    if "goal" in state and getattr(settings, "agent_goal", False):
        g = _goal.active_for(conversation_id)
        if g is not None:
            state["goal"] = g
    hw = state.get("hard_why") or {}
    if isinstance(hw, dict) and state.get("hard"):
        try:
            ctx.research = "research" in (hw.get("why") or [])
        except Exception:   # noqa: BLE001
            pass
    return state


_JOB_KEEP = ("auto_plan",)   # G4: per-job keys a new segment keeps (the rest of the round state starts fresh)


async def _after_run(saver, run_key: str, conversation_id: str, settings, out: dict) -> None:
    """A run's ending. G4: stopped at a long job's segment boundary -> the job is parked on its thread; else the run
    is over: its thread goes (as before), and so do the job threads of this chat's ended goals."""
    if out.get("route") == "carry" and not out.get("stopped"):
        gid = ((out.get("data") or {}).get("__job") or {}).get("goal")
        if gid and saver is not None and await _park(saver, run_key, conversation_id, gid):
            return
        log.warning("turn graph: the long job of %s could not be parked - the next round starts fresh", run_key)
    await _cleanup(saver, run_key, settings, keep_ledger=bool(out.get("stopped")))
    if saver is not None:
        await _forget_ended_jobs(saver, conversation_id, keep=run_key)


async def resume(conversation_id: str, inbox_id: str | None, ctx, gender: str, history: list, settings,
                 tenant_id: str, user_text: str = "", thread: str | None = None) -> str | None:
    """Continue an interrupted turn from its last checkpoint. None = nothing to resume (the caller runs it fresh).

    Rebuilds the live objects the nodes need (ctx comes from the new run_turn; settings; the breaker and the turn's
    state from the checkpoint's data; the santosh _Turn via _turn_prepare on the CHECKPOINTED messages; the live
    reply of this run) - her message is not saved again and no finished node runs again - then ainvoke(None).

    G4 `thread` = a long job's thread. Stopped at `carry` = its NEXT SEGMENT: the round's fresh state (_steps_begin:
    step budget, breaker, the goal caps), the thread's messages + what the chat saved since the last segment ended,
    _turn_prepare as for any round, a fresh G3 nudge budget (the job's facts are kept). Anywhere else = the segment a
    restart / deadline cut, continued exactly like a G1 resume."""
    from . import santosh as S
    th = thread or thread_id(conversation_id, inbox_id)
    try:
        cm = _saver(settings, create=False)
        saver = await cm.__aenter__()
    except Exception:   # noqa: BLE001
        log.exception("turn graph checkpointer could not open for resume")
        return None
    try:
        if saver is None:
            return None
        app = _compile(saver)
        snap = await app.aget_state({"configurable": {"thread_id": th}})
        if not _resumable_snap(snap):
            return None
        vals = snap.values
        nxt = snap.next[0]
        saved = list(vals.get("messages") or [])
        data = dict(vals.get("data") or {})
        carry = nxt == "carry"
        if carry:      # G4: the next segment of a long job
            job0 = dict(data.get("__job") or {})
            history[:] = _job_messages(saved, conversation_id, int(job0.get("mark") or 0))
            state = await S._steps_begin(conversation_id, ctx, history, settings, tenant_id, user_text)
            for k in _JOB_KEEP:
                if k in data:
                    state[k] = data[k]
        else:
            state = _restore_state(data, conversation_id, ctx, settings, user_text)
            history[:] = json.loads(json.dumps(saved))
        live = _Live(conversation_id, ctx, gender, history, settings, tenant_id, user_text)   # cv taken after ASK_NOW
        live.thread = th
        live.state = state
        live.job = dict(data.get("__job") or {})
        t = await asyncio.create_task(S._turn_prepare(conversation_id, ctx, gender, history, settings, tenant_id,
                                                      state), context=live.cv)
        if carry:      # a new segment: its notes ride on the round's line, its step budget starts at 0
            t.ran_steps, t.stop, t.final_text, t.ran_tools = 0, "", "", False
        else:
            history[:] = json.loads(json.dumps(saved))      # _turn_prepare's memory notes are already in the checkpoint
            if "turn_start" in data:
                state["turn_start"] = data["turn_start"]
            # G4: a round that continues a job's cut segment is a new round - it gets the round's step budget again
            # (the deadline is new too); a G1 inbox resume is the same turn, its count goes on
            t.ran_steps = 0 if thread else int(vals.get("ran_steps") or 0)
            t.stop = vals.get("stop") or ""
            t.final_text = data.get("__final_text") or ""
            t.ran_tools = bool(state.get("calls"))
        if nxt in ("tools", "check"):
            last = next((m for m in reversed(history) if m.get("role") == "assistant"), None)
            c = (last or {}).get("content")
            t.blocks = c if isinstance(c, list) else [{"type": "text", "text": str(c or "")}]
        fams = set(data.get("__adm") or [])
        if t.adm is not None and fams - set(t.adm.families):
            try:
                t.adm.admit_families(fams - set(t.adm.families))
            except Exception:   # noqa: BLE001
                log.debug("re-admitting families failed", exc_info=True)
        t.tool_runner = _ledger_runner(th)
        live.t = t
        live.facts[:] = list(vals.get("facts") or [])            # G3: the facts / decisions / budget so far
        live.decisions[:] = list(vals.get("decisions") or [])
        if not carry:                                             # G4: a new segment has its own nudge budget
            live.used.update(dict(vals.get("nudges") or {}))
        _judge(live)
        _RUNS[th] = live
        STATS["job_resumed" if thread else "resumed"] += 1
        log.warning("turn graph: resuming %s at node %s (step %s)", th, nxt, t.ran_steps)
        try:
            out = await _invoke(app, None, settings, th)
        except _NodeCancelled as e:   # a node body cancelled (the old loop let CancelledError through): keep it
            _CUT[conversation_id] = th
            raise asyncio.CancelledError() from e
        except asyncio.CancelledError:
            _CUT[conversation_id] = th
            raise
        except Exception:
            await _cleanup(saver, th, settings)     # the turn ended in an error reply: nothing left to resume
            raise
        finally:
            _RUNS.pop(th, None)
        await _after_run(saver, th, conversation_id, settings, out)
        return out.get("final_text") or ""
    finally:
        try:
            await cm.__aexit__(None, None, None)
        except Exception:   # noqa: BLE001
            log.debug("checkpointer close failed", exc_info=True)


async def run_steps(conversation_id: str, ctx, gender: str, history: list, settings, tenant_id: str,
                    user_text: str = "") -> str:
    """`santosh._steps` on the graph: the same text back, the same rows, the same events."""
    from . import santosh as S
    _bad = str(conversation_id or "").strip() in ("", "default")
    if not AVAILABLE or _bad:
        STATS["fallback"] += 1
        log.warning("chat_graph is on but %s - the old loop answers",
                    "this turn has no conversation id of its own" if _bad else "langgraph is not installed")
        state = await S._steps_begin(conversation_id, ctx, history, settings, tenant_id, user_text)
        text = await S._steps_inner(conversation_id, ctx, gender, history, settings, tenant_id, state)
        return await S._steps_end(conversation_id, ctx, history, settings, tenant_id, user_text, state, text)
    from .. import turn_inbox
    from . import turnrun
    _CUT.pop(conversation_id, None)
    inbox_id, want_resume = turn_inbox.take_graph_turn(conversation_id)
    _tk = turnrun.take_graph(conversation_id)    # G2: the chat's ticket knows its inbox row (task-checked) - it wins
    if _tk is not None:
        inbox_id, want_resume = _tk
    job = _take_job(conversation_id) if not inbox_id else None   # G4: a round of this chat's long job
    if want_resume and inbox_id:
        got = await resume(conversation_id, inbox_id, ctx, gender, history, settings, tenant_id, user_text)
        if got is not None:
            STATS["turns"] += 1
            return got
        log.warning("turn graph: nothing to resume for %s:%s - running the turn fresh", conversation_id, inbox_id)
    if job:
        from . import goal as _goal
        g = _goal.active_for(conversation_id) if getattr(settings, "agent_goal", False) else None
        if g is None or g.get("id") != job or not _goal.steps_left(g):
            # stopped / finished / replaced while this round waited for the chat: nothing of it runs
            STATS["job_gone"] += 1
            await forget_job(settings, conversation_id, job)
            log.info("turn graph: job %s of %s is over - its round does nothing", job, conversation_id)
            return ""
        got = await resume(conversation_id, None, ctx, gender, history, settings, tenant_id, user_text,
                           thread=job_thread(conversation_id, job))
        if got is not None:
            STATS["turns"] += 1
            return got
        STATS["job_fresh"] += 1   # no thread to continue (made on the old path, or lost): the round runs fresh ON it
    STATS["turns"] += 1
    turn_id = (f"job-{job}" if job else "") or inbox_id or uuid.uuid4().hex[:12]
    run_key = thread_id(conversation_id, turn_id)
    live = _Live(conversation_id, ctx, gender, history, settings, tenant_id, user_text)
    _RUNS[run_key] = live
    inp: TurnState = {"conversation_id": conversation_id, "turn_id": turn_id, "run_key": run_key,
                      "messages": [], "ran_steps": 0, "route": "", "capped": False, "done": False,
                      "final_text": "", "outcome": "", "prepared": False, "stop": "", "data": {}}
    try:
        saver_cm = None
        try:
            saver_cm = _saver(settings)
            saver = await saver_cm.__aenter__()
        except Exception:   # noqa: BLE001 - a checkpoint store that cannot open never stops her turn
            log.exception("turn graph checkpointer could not open; running without a checkpoint")
            STATS["no_checkpoint"] += 1
            saver_cm, saver = None, None
        try:
            app = _compile(saver)
            if saver is not None:
                live.thread = run_key           # the ledger only matters when a checkpoint can be resumed
                if inbox_id or job:             # an earlier attempt of this inbox row / job left a thread: start clean
                    await _cleanup(saver, run_key, settings, force=True)
            try:
                out = await _invoke(app, inp, settings, run_key)
            except _NodeCancelled as e:   # LangGraph wraps a node's own CancelledError; the old loop let it through -
                if saver is not None:
                    _CUT[conversation_id] = run_key
                raise asyncio.CancelledError() from e   # the checkpoint stays for a resume
            except asyncio.CancelledError:
                if saver is not None:
                    _CUT[conversation_id] = run_key   # G4: a segment deadline parks it (santosh._run_turn)
                raise
            except Exception:
                await _cleanup(saver, run_key, settings)   # an error reply ends the turn: nothing to resume
                raise
            await _after_run(saver, run_key, conversation_id, settings, out)
        finally:
            if saver_cm is not None:
                try:
                    await saver_cm.__aexit__(None, None, None)
                except Exception:   # noqa: BLE001
                    log.debug("checkpointer close failed", exc_info=True)
        return out.get("final_text") or ""
    finally:
        _RUNS.pop(run_key, None)


async def checkpoints(settings, conversation_id: str) -> list[dict[str, Any]]:
    """The checkpoints written for this chat's turns (newest first) - for tests and diagnostics."""
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    path = checkpoint_path(settings)
    if not os.path.exists(path):
        return []
    rows = []
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        async for tup in saver.alist(None):
            tid = (tup.config.get("configurable") or {}).get("thread_id", "")
            if str(tid).startswith(conversation_id + ":"):
                rows.append({"thread_id": tid, "values": (tup.checkpoint or {}).get("channel_values") or {},
                             "step": (tup.metadata or {}).get("step")})
    return rows
