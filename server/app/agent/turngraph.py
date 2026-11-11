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
"""
from __future__ import annotations

import asyncio
import contextvars
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

STATS = {"turns": 0, "fallback": 0, "no_checkpoint": 0, "resumed": 0, "cleaned": 0, "stopped_at_boundary": 0}
_RESUMABLE = ("model", "tools", "check", "finish")


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
                        "data": _data(live), **_g3(live)})


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
    return {"final_text": text, "outcome": out, "route": "end", "messages": _snapshot(live.history), **_g3(live)}


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
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "model")
    g.add_conditional_edges("model", _route, {"tools": "tools", "check": "check", "finish": "finish",
                                              "model": "model"})
    g.add_conditional_edges("check", _route, {"model": "model", "finish": "finish", "tools": "tools"})
    g.add_conditional_edges("tools", _route, {"model": "model", "finish": "finish"})
    g.add_edge("finish", END)
    return g


_BUILDER = None


def _builder():
    global _BUILDER
    if _BUILDER is None:
        _BUILDER = build()
    return _BUILDER


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


async def resumable(settings, conversation_id: str, inbox_id: str) -> bool:
    """Does the checkpointer hold an unfinished, resumable checkpoint for this inbox row's turn?"""
    if not AVAILABLE or not inbox_id:
        return False
    th = thread_id(conversation_id, inbox_id)
    async with _saver(settings, create=False) as saver:
        if saver is None:
            return False
        snap = await _builder().compile(checkpointer=saver).aget_state({"configurable": {"thread_id": th}})
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


async def resume(conversation_id: str, inbox_id: str, ctx, gender: str, history: list, settings, tenant_id: str,
                 user_text: str = "") -> str | None:
    """Continue an interrupted turn from its last checkpoint. None = nothing to resume (the caller runs it fresh).

    Rebuilds the live objects the nodes need (ctx comes from the new run_turn; settings; the breaker and the turn's
    state from the checkpoint's data; the santosh _Turn via _turn_prepare on the CHECKPOINTED messages; the live
    reply of this run) - her message is not saved again and no finished node runs again - then ainvoke(None)."""
    from . import santosh as S
    th = thread_id(conversation_id, inbox_id)
    try:
        cm = _saver(settings, create=False)
        saver = await cm.__aenter__()
    except Exception:   # noqa: BLE001
        log.exception("turn graph checkpointer could not open for resume")
        return None
    try:
        if saver is None:
            return None
        app = _builder().compile(checkpointer=saver)
        snap = await app.aget_state({"configurable": {"thread_id": th}})
        if not _resumable_snap(snap):
            return None
        vals = snap.values
        nxt = snap.next[0]
        saved = list(vals.get("messages") or [])
        data = dict(vals.get("data") or {})
        state = _restore_state(data, conversation_id, ctx, settings, user_text)
        live = _Live(conversation_id, ctx, gender, history, settings, tenant_id, user_text)   # cv taken after ASK_NOW
        live.thread = th
        live.state = state
        history[:] = json.loads(json.dumps(saved))
        t = await asyncio.create_task(S._turn_prepare(conversation_id, ctx, gender, history, settings, tenant_id,
                                                      state), context=live.cv)
        history[:] = json.loads(json.dumps(saved))      # _turn_prepare's memory notes are already in the checkpoint
        if "turn_start" in data:
            state["turn_start"] = data["turn_start"]
        t.ran_steps = int(vals.get("ran_steps") or 0)
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
        live.used.update(dict(vals.get("nudges") or {}))
        _judge(live)
        _RUNS[th] = live
        STATS["resumed"] += 1
        log.warning("turn graph: resuming %s at node %s (step %s)", th, nxt, t.ran_steps)
        try:
            out = await _invoke(app, None, settings, th)
        except _NodeCancelled as e:   # a node body cancelled (the old loop let CancelledError through): keep it
            raise asyncio.CancelledError() from e
        except Exception:
            await _cleanup(saver, th, settings)     # the turn ended in an error reply: nothing left to resume
            raise
        finally:
            _RUNS.pop(th, None)
        await _cleanup(saver, th, settings, keep_ledger=bool(out.get("stopped")))
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
    inbox_id, want_resume = turn_inbox.take_graph_turn(conversation_id)
    _tk = turnrun.take_graph(conversation_id)    # G2: the chat's ticket knows its inbox row (task-checked) - it wins
    if _tk is not None:
        inbox_id, want_resume = _tk
    if want_resume and inbox_id:
        got = await resume(conversation_id, inbox_id, ctx, gender, history, settings, tenant_id, user_text)
        if got is not None:
            STATS["turns"] += 1
            return got
        log.warning("turn graph: nothing to resume for %s:%s - running the turn fresh", conversation_id, inbox_id)
    STATS["turns"] += 1
    turn_id = inbox_id or uuid.uuid4().hex[:12]
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
            app = _builder().compile(checkpointer=saver)
            if saver is not None:
                live.thread = run_key           # the ledger only matters when a checkpoint can be resumed
                if inbox_id:                    # an earlier attempt of this inbox row left a thread: start clean
                    await _cleanup(saver, run_key, settings, force=True)
            try:
                out = await _invoke(app, inp, settings, run_key)
            except _NodeCancelled as e:   # LangGraph wraps a node's own CancelledError; the old loop let it through -
                raise asyncio.CancelledError() from e   # the checkpoint stays for a resume
            except Exception:
                await _cleanup(saver, run_key, settings)   # an error reply ends the turn: nothing to resume
                raise
            await _cleanup(saver, run_key, settings, keep_ledger=bool(out.get("stopped")))
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
