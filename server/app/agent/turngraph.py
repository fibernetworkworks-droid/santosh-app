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

Checkpointer: an AsyncSqliteSaver at <chat_graph_dir>/checkpoints.db, thread_id = "<conversation>:<turn id>". G0
writes the checkpoint; resuming from it after a restart is G1.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import uuid
from typing import Any, TypedDict

log = logging.getLogger("santosh.turngraph")

try:   # the official library (MIT). Missing on a box = the old loop answers, said once in the log
    from langgraph.graph import END, START, StateGraph
    AVAILABLE = True
except Exception:   # noqa: BLE001
    AVAILABLE = False

STATS = {"turns": 0, "fallback": 0, "no_checkpoint": 0}


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


class _Live:
    """What a turn needs that is not data: never checkpointed."""

    def __init__(self, conversation_id, ctx, gender, history, settings, tenant_id, user_text):
        self.conversation_id, self.ctx, self.gender = conversation_id, ctx, gender
        self.history, self.settings, self.tenant_id, self.user_text = history, settings, tenant_id, user_text
        self.state: dict = {}
        self.t = None                                  # santosh._Turn
        self.cv = contextvars.copy_context()           # the ONE context every node body runs in


_RUNS: dict[str, _Live] = {}


def _snapshot(history: list) -> list:
    """The messages as plain JSON data for the checkpoint (a block that is not JSON is written as text)."""
    try:
        return json.loads(json.dumps(history, ensure_ascii=False, default=str))
    except Exception:   # noqa: BLE001
        return []


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
    return {"messages": _snapshot(live.history), "ran_steps": 0, "route": "model"}


async def _model(live: _Live, state: TurnState) -> dict:
    from . import santosh as S
    t = live.t
    if not t.ran_steps < t.cap():          # the old `while ran_steps < cap` fell through to its else
        return {"route": "finish", "capped": True}
    t.ran_steps += 1
    got = await S._turn_model(t)
    if isinstance(got, str):               # Rokiye / Pause landed during the model call
        return {"route": "finish", "done": True, "final_text": got, "ran_steps": t.ran_steps,
                "messages": _snapshot(live.history)}
    blocks, stop = got
    t.blocks, t.stop = blocks, stop
    route = "check"
    if stop == "tool_use":                 # the step is recorded (saved + shown) before its tools run, as before
        route = await S._turn_after_model(t, blocks, stop)
    return {"route": route, "ran_steps": t.ran_steps, "messages": _snapshot(live.history)}


async def _check(live: _Live, state: TurnState) -> dict:
    from . import santosh as S
    t = live.t
    route = await S._turn_after_model(t, t.blocks, t.stop)
    return {"route": route, "final_text": t.final_text or "", "messages": _snapshot(live.history)}


async def _tools(live: _Live, state: TurnState) -> dict:
    from . import santosh as S
    t = live.t
    done = await S._turn_tools(t, t.blocks)
    if done is not None:                   # stuck (breaker) / stopped: the turn ends with this line
        return {"route": "finish", "done": True, "final_text": done, "messages": _snapshot(live.history)}
    return {"route": "model", "messages": _snapshot(live.history)}


async def _finish(live: _Live, state: TurnState) -> dict:
    from . import santosh as S
    t = live.t
    if state.get("done"):
        text = state.get("final_text") or ""
    elif state.get("capped"):
        text = S._turn_capped(t)
    else:
        text = S._turn_silent(t)
    text = await S._steps_end(live.conversation_id, live.ctx, live.history, live.settings, live.tenant_id,
                              live.user_text, live.state, text)
    out = (S.LAST_OUTCOME.get(live.conversation_id) or {}).get("outcome", "") if live.user_text else ""
    return {"final_text": text, "outcome": out, "route": "end", "messages": _snapshot(live.history)}


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


async def _invoke(app, inp: TurnState, settings, thread_id: str) -> dict:
    cfg = {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit(settings)}
    return await app.ainvoke(inp, cfg)


async def run_steps(conversation_id: str, ctx, gender: str, history: list, settings, tenant_id: str,
                    user_text: str = "") -> str:
    """`santosh._steps` on the graph: the same text back, the same rows, the same events."""
    from . import santosh as S
    if not AVAILABLE:
        STATS["fallback"] += 1
        log.warning("chat_graph is on but langgraph is not installed - the old loop answers")
        state = await S._steps_begin(conversation_id, ctx, history, settings, tenant_id, user_text)
        text = await S._steps_inner(conversation_id, ctx, gender, history, settings, tenant_id, state)
        return await S._steps_end(conversation_id, ctx, history, settings, tenant_id, user_text, state, text)
    STATS["turns"] += 1
    turn_id = uuid.uuid4().hex[:12]
    run_key = f"{conversation_id}:{turn_id}"
    _RUNS[run_key] = _Live(conversation_id, ctx, gender, history, settings, tenant_id, user_text)
    inp: TurnState = {"conversation_id": conversation_id, "turn_id": turn_id, "run_key": run_key,
                      "messages": [], "ran_steps": 0, "route": "", "capped": False, "done": False,
                      "final_text": "", "outcome": ""}
    try:
        saver_cm = None
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            path = checkpoint_path(settings)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            saver_cm = AsyncSqliteSaver.from_conn_string(path)
            saver = await saver_cm.__aenter__()
        except Exception:   # noqa: BLE001 - a checkpoint store that cannot open never stops her turn
            log.exception("turn graph checkpointer could not open; running without a checkpoint")
            STATS["no_checkpoint"] += 1
            saver_cm, saver = None, None
        try:
            app = _builder().compile(checkpointer=saver)
            out = await _invoke(app, inp, settings, run_key)
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
    """The checkpoints written for this chat's turns (newest first) - for tests and a later resume (G1)."""
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
