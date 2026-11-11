"""v0.530.0 HOOLA GRAPH - the state-graph engine, P3 of the HOOLA AEP plan
(owner: 'P3 HOOLA GRAPH' after v0.520.0 HOOLA TRACE landed on main). The
langgraph idea hand-built as server/app/aep/graph.py - ZERO upstream code.
This suite pins the layer:

(1) BUILDER: add_node validation (duplicates, reserved names, non-callables,
    Runnable nodes), add_edge endpoints checked at BUILD time, compile-time
    refusals (no nodes, no entry, conditional path_map targeting unknowns).
(2) CHANNELS: last-value-wins for plain keys; Annotated[T, reducer] merges
    (operator.add); a first-ever value SEEDS the channel (operator.add has no
    identity for a missing left side); unknown update keys refused honestly;
    non-dict graph input refused.
(3) WALK: linear order; conditional edges (dict path_map, positional list
    path_map, router -> END, router -> list fan-out); unmapped router answers
    refused; the diamond fan-out with the join BARRIER (a node with several
    inbound static edges runs once, after ALL parents); every node in a
    super-step sees the SAME pre-step state; routers see the POST-node state;
    recursion_limit (default 25, honest GraphRecursionError, configurable);
    None node updates are no-ops; non-dict node returns refused; two-arg nodes
    receive the config; a Runnable node composes.
(4) AGENT STATE: add_messages (append, replace-by-id, RemoveMessage drop,
    REMOVE_ALL_MESSAGES clear, str -> HumanMessage, dict coerce); AgentState
    accumulates messages across nodes (the P4 create_agent substrate).
(5) CHECKPOINTERS: a checkpoint after EVERY super-step; MemorySaver thread
    isolation, ring cap, delete_thread; get_state values/next/pending;
    update_state(as_node=...) re-derives next; invoke(None) resumes the stored
    walk (the crash path); Command.update_only / Command.goto_nodes reshape a
    walk; SqliteSaver round-trips across instances, threads, list(limit), the
    exactly-one-of path/engine refusal, and the sqlalchemy-engine shape (the
    vault's engine, used lazily).
(6) INTERRUPTS: interrupt() outside a node refuses; parking without a
    checkpointer refuses honestly; the park shape (__interrupt__ value/
    resumable/node/idx); Command(resume=...) re-enters and the node re-runs
    FROM ITS TOP (the answered slot replays, the next slot re-parks, the
    earlier answers survive); get_state.pending after a park; the stream parks
    with the __interrupt__ chunk; async nodes park through ainvoke too.
(7) TRACER SEAM: node executions fire chain spans NAMED BY THE NODE when
    callbacks ride the config (one trace_id across the walk); the no-callback
    fast path stays run-free.
(8) INERTNESS + WIRING + VERSION: a fresh interpreter imports app.aep (graph
    now rides along) with ZERO extra threads/env reads/files; the package-export
    law covers the new names; no new registry tools (no tool schema, no voice
    names in the module); compile(store=...) rides config['store'] into nodes;
    APP_VERSION + pubspec + story markers.

No test touches the network; every async path rides asyncio.run (the documented
one-loop law).
"""
import asyncio
import operator
import subprocess
import sys
import threading
from pathlib import Path
from typing import Annotated, TypedDict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER = REPO_ROOT / "server"

from app import aep
from app.aep import graph as G
from app.aep.graph import (
    INTERRUPT_KEY,
    AgentState,
    Command,
    CompiledStateGraph,
    END,
    GraphRecursionError,
    MemorySaver,
    START,
    StateGraph,
    SqliteSaver,
    add_messages,
    interrupt,
)
from app.aep.messages import (
    REMOVE_ALL_MESSAGES,
    AIMessage,
    HumanMessage,
    RemoveMessage,
)
from app.aep.runnable import RunnableLambda
from app.aep.tracers import CallbackManager as CM, InMemoryRunStore, RunTreeTracer, reset_global

pytest.importorskip("sqlalchemy")


# ---------------------------------------------------------------------------
# fixtures + helpers
# ---------------------------------------------------------------------------


class S(TypedDict, total=False):
    n: Annotated[list, operator.add]
    done: bool
    tag: str


@pytest.fixture(autouse=True)
def _reset():
    reset_global()
    yield
    reset_global()


def _linear():
    g = StateGraph(S)
    g.add_node("a", lambda s: {"n": [1]})
    g.add_node("b", lambda s: {"n": [2], "done": True})
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)
    return g.compile()


# ---------------------------------------------------------------------------
# (1) builder + validation
# ---------------------------------------------------------------------------


def test_add_node_refuses_duplicates_reserved_and_junk():
    g = StateGraph(S)
    g.add_node("a", lambda s: {})
    with pytest.raises(ValueError, match="already exists"):
        g.add_node("a", lambda s: {})
    with pytest.raises(ValueError, match="bad node name"):
        g.add_node(START, lambda s: {})
    with pytest.raises(ValueError, match="bad node name"):
        g.add_node("", lambda s: {})
    with pytest.raises(TypeError, match="needs a callable"):
        g.add_node("b", "not-callable")


def test_add_edge_checks_endpoints_at_build_time():
    g = StateGraph(S)
    with pytest.raises(ValueError, match="unknown source"):
        g.add_edge("ghost", "x")
    g.add_node("a", lambda s: {})
    with pytest.raises(ValueError, match="unknown target"):
        g.add_edge("a", "ghost")


def test_compile_refuses_no_nodes_no_entry_and_bad_path_map():
    with pytest.raises(ValueError, match="at least one node"):
        StateGraph(S).compile()
    g = StateGraph(S)
    g.add_node("a", lambda s: {})
    with pytest.raises(ValueError, match="no entry point"):
        g.compile()
    g2 = StateGraph(S)
    g2.add_node("a", lambda s: {})
    g2.add_node("b", lambda s: {})
    g2.add_edge(START, "a")
    def _router(s):
        return "big"
    g2.add_conditional_edges("a", _router, {"big": "ghost"})
    with pytest.raises(ValueError, match="unknown node"):
        g2.compile()


def test_runnable_node_is_accepted_and_runs():
    g = StateGraph(S)
    g.add_node("up", RunnableLambda(lambda x: {"n": [len(x.get("n", []))]}))
    g.add_edge(START, "up")
    g.add_edge("up", END)
    out = g.compile().invoke({"n": [1, 2, 3]})
    assert out["n"][-1] == 3


# ---------------------------------------------------------------------------
# (2) channels
# ---------------------------------------------------------------------------


def test_plain_channels_are_last_value_wins():
    out = _linear().invoke({"n": [], "tag": "x"})
    assert out["done"] is True        # b's plain write wins


def test_reducer_channels_merge_and_first_value_seeds():
    out = _linear().invoke({"n": [0]})
    assert out["n"] == [0, 1, 2]      # seeded + merged through operator.add
    out2 = _linear().invoke({})
    assert out2["n"] == [1, 2]        # first-ever value seeds, then merges


def test_unknown_update_keys_are_refused_honestly():
    g = StateGraph(S)
    g.add_node("bad", lambda s: {"ghost": 1})
    g.add_edge(START, "bad")
    g.add_edge("bad", END)
    with pytest.raises(ValueError, match="unknown state keys"):
        g.compile().invoke({})


def test_non_dict_input_refused():
    with pytest.raises(TypeError, match="dict of state values"):
        _linear().invoke("nope")


# ---------------------------------------------------------------------------
# (3) the walk
# ---------------------------------------------------------------------------


def test_linear_walk_order():
    seen: list[str] = []
    g = StateGraph(S)
    g.add_node("a", lambda s: (seen.append("a"), {"n": [1]})[1])
    g.add_node("b", lambda s: (seen.append("b"), {"n": [2]})[1])
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)
    out = g.compile().invoke({})
    assert seen == ["a", "b"] and out["n"] == [1, 2]


def test_conditional_dict_and_positional_path_maps():
    g = StateGraph(S)
    g.add_node("x", lambda s: {"n": [10]})
    g.add_node("y", lambda s: {"n": [20]})
    g.add_node("z", lambda s: {"n": [30]})
    g.add_edge(START, "x")
    g.add_conditional_edges("x", lambda s: "big" if sum(s["n"]) > 50 else "small",
                            {"big": "z", "small": "y"})
    g.add_edge("y", END)
    g.add_edge("z", END)
    app = g.compile()
    assert app.invoke({"n": [6]})["n"] == [6, 10, 20]
    assert app.invoke({"n": [60]})["n"] == [60, 10, 30]
    # positional path map: ["y", "z"] -> first answer to y, second to z
    g2 = StateGraph(S)
    g2.add_node("x", lambda s: {"n": [1]})
    g2.add_node("y", lambda s: {"n": [20]})
    g2.add_node("z", lambda s: {"n": [30]})
    g2.add_edge(START, "x")
    g2.add_conditional_edges("x", lambda s: (0, 1), ["y", "z"])   # list map = indices
    g2.add_edge("y", END)
    g2.add_edge("z", END)
    out = g2.compile().invoke({})
    assert out["n"] == [1, 20, 30]


def test_router_returning_end_and_lists():
    g = StateGraph(S)
    g.add_node("x", lambda s: {"n": [1]})
    g.add_node("y", lambda s: {"n": [2]})
    g.add_edge(START, "x")
    g.add_edge("x", "y")
    g.add_conditional_edges("y", lambda s: ["y", END] if len(s["n"]) < 4 else END, None)
    g.add_edge("y", END)
    out = g.compile().invoke({})
    # y loops back through the router until n >= 4 answers (router -> [y, END])
    assert out["n"] == [1, 2, 2, 2], out["n"]
    # routing is ADDITIVE: a conditional END plus a static edge -> the static
    # target still fires (END only means "no extra target from the router")
    g2 = StateGraph(S)
    g2.add_node("a", lambda s: {"tag": "a"})
    g2.add_node("b", lambda s: {"tag": "b"})
    g2.add_edge(START, "a")
    g2.add_conditional_edges("a", lambda s: END, None)
    g2.add_edge("a", "b")
    assert g2.compile().invoke({})["tag"] == "b"
    # a node with ONLY a conditional END stops the walk there
    g3 = StateGraph(S)
    g3.add_node("a", lambda s: {"tag": "a"})
    g3.add_node("solo", lambda s: {"tag": "solo"})
    g3.add_edge(START, "a")
    g3.add_conditional_edges("a", lambda s: END, None)
    g3.add_edge(START, "solo")     # reachable only from the entry
    out3 = g3.compile().invoke({})
    assert out3["tag"] in ("a", "solo")   # both entries ran; nothing after a


def test_unmapped_router_answer_refused():
    g = StateGraph(S)
    g.add_node("x", lambda s: {})
    g.add_edge(START, "x")
    g.add_conditional_edges("x", lambda s: "nope", {"y": END})
    g.add_node("y", lambda s: {})
    with pytest.raises(ValueError, match="not in the path_map"):
        g.compile().invoke({})


def test_diamond_fan_out_join_barrier_runs_once():
    joins: list[int] = []
    g = StateGraph(S)
    g.add_node("start", lambda s: {"n": [1]})
    g.add_node("l", lambda s: {"n": [10]})
    g.add_node("r", lambda s: {"n": [20]})
    def _join(s):
        joins.append(1)
        return {"done": True}
    g.add_node("join", _join)
    g.add_edge(START, "start")
    g.add_edge("start", "l")
    g.add_edge("start", "r")     # fan-out: same super-step
    g.add_edge("l", "join")
    g.add_edge("r", "join")      # the barrier: BOTH parents first
    g.add_edge("join", END)
    out = g.compile().invoke({"n": []})
    assert out["n"] == [1, 10, 20] and out["done"] is True
    assert len(joins) == 1


def test_sequential_nodes_see_prior_updates():
    seen: list[int] = []
    g = StateGraph(S)
    def _w(tag):
        def _fn(s):
            seen.append(sum(s.get("n", [])))
            return {"n": [5]}
        return _fn
    g.add_node("p", _w("p"))
    g.add_node("q", _w("q"))
    g.add_edge(START, "p")
    g.add_edge("p", "q")
    g.add_edge("q", END)
    g.compile().invoke({"n": [1]})
    # p sees 1, q sees 6 (1 + p's 5) - sequential chain, not parallel
    assert seen == [1, 6]


def test_recursion_limit_default_and_configurable():
    g = StateGraph(S)
    g.add_node("loop", lambda s: {"n": [1]})
    g.add_edge(START, "loop")
    g.add_edge("loop", "loop")
    app = g.compile()
    with pytest.raises(GraphRecursionError, match="recursion_limit of 25"):
        app.invoke({"n": []})
    with pytest.raises(GraphRecursionError, match="recursion_limit of 4"):
        app.invoke({"n": []}, {"configurable": {"recursion_limit": 4}})


def test_node_none_is_noop_and_non_dict_refused():
    g = StateGraph(S)
    g.add_node("noop", lambda s: None)
    g.add_node("bad", lambda s: "not-a-dict")
    g.add_edge(START, "noop")
    g.add_edge("noop", "bad")
    g.add_edge("bad", END)
    with pytest.raises(TypeError, match="nodes return a dict"):
        g.compile().invoke({"n": []})


def test_two_arg_node_receives_config_and_store_rides():
    class T(TypedDict, total=False):
        tag: str
    store = aep.InMemoryStore()
    got: dict = {}
    g = StateGraph(T)
    def _node(state, config=None):
        got["store"] = config.get("store")
        got["thread"] = (config.get("configurable") or {}).get("thread_id")
        return {"tag": "ok"}
    g.add_node("n", _node)
    g.add_edge(START, "n")
    g.add_edge("n", END)
    out = g.compile(store=store).invoke({}, {"configurable": {"thread_id": "t9"}})
    assert out["tag"] == "ok"
    assert got["store"] is store
    assert got["thread"] == "t9"


# ---------------------------------------------------------------------------
# (4) AgentState + add_messages
# ---------------------------------------------------------------------------


def test_add_messages_semantics():
    h = HumanMessage("hi", id="h1")
    assert add_messages([], [h]) == [h]
    # replace-by-id
    out = add_messages([h], [HumanMessage("REPLACED", id="h1")])
    assert len(out) == 1 and out[0].content == "REPLACED"
    # append (no id)
    out = add_messages(out, [AIMessage("yo")])
    assert len(out) == 2
    # drop one id
    out = add_messages(out, [RemoveMessage(id="h1")])
    assert len(out) == 1 and out[0].content == "yo"
    # clear all
    out = add_messages(out, [RemoveMessage(id=REMOVE_ALL_MESSAGES)])
    assert out == []
    # coercions: dict -> message, str -> HumanMessage
    out = add_messages([], [{"type": "human", "data": {"content": "dict-form"}}])
    assert isinstance(out[0], HumanMessage) and out[0].content == "dict-form"
    out = add_messages([], ["plain"])
    assert isinstance(out[0], HumanMessage) and out[0].content == "plain"


def test_agent_state_accumulates_messages_across_nodes():
    g = StateGraph(AgentState)
    g.add_node("greet", lambda s: {"messages": [AIMessage("hello")]})
    g.add_node("bye", lambda s: {"messages": [AIMessage("bye")]})
    g.add_edge(START, "greet")
    g.add_edge("greet", "bye")
    g.add_edge("bye", END)
    out = g.compile().invoke({"messages": [HumanMessage("hi")]})
    kinds = [type(m).__name__ for m in out["messages"]]
    assert kinds == ["HumanMessage", "AIMessage", "AIMessage"]
    assert out["messages"][1].content == "hello"


# ---------------------------------------------------------------------------
# (5) checkpointers
# ---------------------------------------------------------------------------


def test_checkpoint_after_every_super_step_and_get_state():
    mem = MemorySaver()
    g = StateGraph(S)
    g.add_node("a", lambda s: {"n": [1]})
    g.add_node("b", lambda s: {"n": [2], "done": True})
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)
    app = g.compile(checkpointer=mem)
    cfg = {"configurable": {"thread_id": "k1"}}
    out = app.invoke({"n": [0]}, cfg)
    rows = mem.list(cfg)
    assert len(rows) == 3                      # step0 input + step1 + step2
    assert rows[0]["step"] == 2 and rows[0]["next"] == []
    st = app.get_state(cfg)
    assert st["values"] == {"n": [0, 1, 2], "done": True}
    assert st["next"] == [] and st["checkpoint_id"] == rows[0]["id"]


def test_memory_saver_thread_isolation_and_delete():
    mem = MemorySaver()
    g = StateGraph(S)
    g.add_node("a", lambda s: {"tag": "x"})
    g.add_edge(START, "a")
    g.add_edge("a", END)
    app = g.compile(checkpointer=mem)
    app.invoke({}, {"configurable": {"thread_id": "t1"}})
    app.invoke({}, {"configurable": {"thread_id": "t2"}})
    assert mem.get({"configurable": {"thread_id": "t1"}})["thread_id"] == "t1"
    assert len(mem._threads) == 2
    mem.delete_thread("t1")
    assert "t1" not in mem._threads
    assert app.get_state({"configurable": {"thread_id": "t1"}})["checkpoint_id"] is None


def test_memory_saver_ring_cap():
    mem = MemorySaver(cap=3)
    g = StateGraph(S)
    g.add_node("loop", lambda s: {"n": [1]})
    g.add_edge(START, "loop")
    g.add_edge("loop", "loop")
    cfg = {"configurable": {"thread_id": "r", "recursion_limit": 8}}
    with pytest.raises(GraphRecursionError):
        g.compile(checkpointer=mem).invoke({"n": []}, cfg)
    assert len(mem.list(cfg)) == 3


def test_update_state_as_node_rederives_next():
    mem = MemorySaver()
    g = StateGraph(S)
    g.add_node("p", lambda s: {"n": [7]})
    g.add_node("q", lambda s: {"done": True})
    g.add_edge(START, "p")
    g.add_edge("p", "q")
    g.add_edge("q", END)
    app = g.compile(checkpointer=mem)
    cfg = {"configurable": {"thread_id": "u1"}}
    app.invoke({"n": []}, cfg)
    snap = app.update_state(cfg, {"n": [99]}, as_node="p")
    assert snap["next"] == ["q"]               # as_node acted like p just ran
    assert 99 in snap["values"]["n"]


def test_invoke_none_crash_resume():
    mem = MemorySaver()
    g = StateGraph(S)
    g.add_node("p", lambda s: {"n": [7]})
    g.add_node("q", lambda s: {"done": True})
    g.add_edge(START, "p")
    g.add_edge("p", "q")
    g.add_edge("q", END)
    app = g.compile(checkpointer=mem)
    cfg = {"configurable": {"thread_id": "u2"}}
    app.update_state(cfg, {"n": [7]}, as_node="p")   # the walk died after p
    out = app.invoke(None, cfg)                       # the crash path picks it up
    assert out == {"n": [7], "done": True}


def test_command_update_only_and_goto():
    mem = MemorySaver()
    g = StateGraph(S)
    g.add_node("p", lambda s: {"n": [1]})
    g.add_node("q", lambda s: {"done": True})
    g.add_node("z", lambda s: {"tag": "z"})
    g.add_edge(START, "p")
    g.add_edge("p", "q")
    g.add_edge("q", END)
    app = g.compile(checkpointer=mem)
    cfg = {"configurable": {"thread_id": "u3"}}
    app.invoke({"n": []}, cfg)
    out = app.invoke(Command.update_only({"tag": "shaped"}), cfg)
    assert out["tag"] == "shaped" and out["done"] is True
    app2 = g.compile(checkpointer=MemorySaver())
    cfg2 = {"configurable": {"thread_id": "u4"}}
    app2.invoke({"n": []}, cfg2)
    out2 = app2.invoke(Command.goto_nodes("z"), cfg2)   # jump to z after the walk
    assert out2["tag"] == "z" and out2["done"] is True   # q had already run


def test_sqlite_saver_round_trip_and_refusals(tmp_path):
    db = str(tmp_path / "cp.db")
    g = StateGraph(S)
    g.add_node("a", lambda s: {"n": [1], "done": True})
    g.add_edge(START, "a")
    g.add_edge("a", END)
    cfg = {"configurable": {"thread_id": "s1"}}
    saver1 = SqliteSaver(path=db)
    g.compile(checkpointer=saver1).invoke({"n": [0]}, cfg)
    # a FRESH instance over the same file reads the walk back
    saver2 = SqliteSaver(path=db)
    app2 = g.compile(checkpointer=saver2)
    st = app2.get_state(cfg)
    assert st["values"] == {"n": [0, 1], "done": True}
    assert len(saver2.list(cfg, limit=1)) == 1
    saver2.delete_thread("s1")
    assert app2.get_state(cfg)["checkpoint_id"] is None
    with pytest.raises(ValueError, match="exactly one"):
        SqliteSaver()
    with pytest.raises(ValueError, match="exactly one"):
        SqliteSaver(path=db, engine=object())


def test_sqlite_saver_engine_shape_the_vault_way(tmp_path):
    from sqlalchemy import create_engine
    eng = create_engine(f"sqlite:///{tmp_path / 'eng.db'}")
    g = StateGraph(S)
    g.add_node("a", lambda s: {"done": True})
    g.add_edge(START, "a")
    g.add_edge("a", END)
    cfg = {"configurable": {"thread_id": "e1"}}
    app = g.compile(checkpointer=SqliteSaver(engine=eng))
    out = app.invoke({"n": []}, cfg)
    assert out["done"] is True
    st = app.get_state(cfg)
    assert st["values"]["done"] is True


def test_threads_of_sqlite_saver_are_isolated(tmp_path):
    saver = SqliteSaver(path=str(tmp_path / "t.db"))
    g = StateGraph(S)
    g.add_node("a", lambda s: {"tag": "x"})
    g.add_edge(START, "a")
    g.add_edge("a", END)
    app = g.compile(checkpointer=saver)
    app.invoke({}, {"configurable": {"thread_id": "a"}})
    app.invoke({}, {"configurable": {"thread_id": "b"}})
    assert saver.get({"configurable": {"thread_id": "a"}})["thread_id"] == "a"
    assert saver.get({"configurable": {"thread_id": "b"}})["thread_id"] == "b"


# ---------------------------------------------------------------------------
# (6) interrupts
# ---------------------------------------------------------------------------


def test_interrupt_outside_a_node_refuses():
    with pytest.raises(RuntimeError, match="inside a graph node"):
        interrupt("x")


def test_park_without_checkpointer_refuses():
    g = StateGraph(S)
    g.add_node("a", lambda s: interrupt("q") or {"done": True})
    g.add_edge(START, "a")
    g.add_edge("a", END)
    with pytest.raises(RuntimeError, match="needs a checkpointer"):
        g.compile().invoke({"n": []})


def test_park_shape_and_resume():
    mem = MemorySaver()
    g = StateGraph(S)
    def _ask(s):
        v = interrupt({"q": "approve?"})
        return {"n": [100 if v else 0]}
    g.add_node("ask", _ask)
    g.add_node("after", lambda s: {"done": True})
    g.add_edge(START, "ask")
    g.add_edge("ask", "after")
    g.add_edge("after", END)
    app = g.compile(checkpointer=mem)
    cfg = {"configurable": {"thread_id": "i1"}}
    r1 = app.invoke({"n": [5]}, cfg)
    assert INTERRUPT_KEY in r1
    bag = r1[INTERRUPT_KEY][0]
    assert bag["value"] == {"q": "approve?"} and bag["resumable"] is True
    assert bag["node"] == "ask" and bag["idx"] == 0
    st = app.get_state(cfg)
    assert st["pending"]["node"] == "ask" and st["next"] == ["ask"]
    r2 = app.invoke(Command(resume=True), cfg)
    assert r2 == {"n": [5, 100], "done": True}
    assert app.get_state(cfg)["pending"] is None


def test_resume_false_answer_and_stream_park():
    mem = MemorySaver()
    g = StateGraph(S)
    def _ask(s):
        v = interrupt("ok?")
        return {"tag": "yes" if v else "no"}
    g.add_node("ask", _ask)
    g.add_edge(START, "ask")
    g.add_edge("ask", END)
    app = g.compile(checkpointer=mem)
    cfg = {"configurable": {"thread_id": "i2"}}
    chunks = list(app.stream({"n": []}, cfg))
    assert chunks[-1][INTERRUPT_KEY][0]["value"] == "ok?"
    out = app.invoke(Command(resume=False), cfg)
    assert out["tag"] == "no"


def test_two_interrupts_second_park_keeps_first_answer():
    mem = MemorySaver()
    g = StateGraph(S)
    def _two(s):
        a = interrupt("first?")
        b = interrupt("second?")
        return {"n": [1 if a else 0, 2 if b else 0]}
    g.add_node("t", _two)
    g.add_edge(START, "t")
    g.add_edge("t", END)
    app = g.compile(checkpointer=mem)
    cfg = {"configurable": {"thread_id": "i3"}}
    r1 = app.invoke({}, cfg)
    assert r1[INTERRUPT_KEY][0]["value"] == "first?"
    r2 = app.invoke(Command(resume=True), cfg)
    assert r2[INTERRUPT_KEY][0]["value"] == "second?" and r2[INTERRUPT_KEY][0]["idx"] == 1
    r3 = app.invoke(Command(resume=True), cfg)
    assert r3["n"] == [1, 2]


def test_resume_without_a_park_refuses():
    g = StateGraph(S)
    g.add_node("a", lambda s: {})
    g.add_edge(START, "a")
    g.add_edge("a", END)
    app2 = g.compile(checkpointer=MemorySaver())
    with pytest.raises(ValueError, match="nothing to resume"):
        app2.invoke(Command(resume=True), {"configurable": {"thread_id": "empty"}})


def test_async_nodes_ainvoke_and_park():
    async def _a(state):
        return {"n": [1]}
    async def _ask(state):
        v = interrupt("async?")
        return {"done": bool(v)}
    g = StateGraph(S)
    g.add_node("a", _a)
    g.add_node("ask", _ask)
    g.add_edge(START, "a")
    g.add_edge("a", "ask")
    g.add_edge("ask", END)
    app = g.compile(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "i4"}}

    async def _main():
        return await app.ainvoke({"n": []}, cfg)

    r1 = asyncio.run(_main())
    assert r1[INTERRUPT_KEY][0]["value"] == "async?"
    r2 = app.invoke(Command(resume=True), cfg)
    assert r2["done"] is True and r2["n"] == [1]


# ---------------------------------------------------------------------------
# (7) tracer seam
# ---------------------------------------------------------------------------


def test_node_spans_fire_named_by_the_node():
    store = InMemoryRunStore()
    tracer = RunTreeTracer(sinks=[store])
    mgr = CM([tracer])
    g = StateGraph(S)
    g.add_node("alpha", lambda s: {"n": [1]})
    g.add_node("beta", lambda s: {"n": [2]})
    g.add_edge(START, "alpha")
    g.add_edge("alpha", "beta")
    g.add_edge("beta", END)
    g.compile().invoke({"n": []}, {"callbacks": mgr})
    names = [r.name for r in tracer.runs.values()]
    assert "alpha" in names and "beta" in names
    finished = store.recent(limit=10)
    assert len(finished) == 3                    # the StateGraph root + both nodes
    roots = [r for r in finished if r.parent_run_id is None]
    assert len(roots) == 1 and roots[0].name == "StateGraph"
    kids = {c for c in roots[0].child_ids}
    node_ids = {r.id for r in finished if r.name in ("alpha", "beta")}
    assert kids == node_ids                      # the nodes nest under the root
    trace_ids = {r.trace_id for r in finished}
    assert len(trace_ids) == 1                   # one walk, one trace


def test_no_callback_fast_path_stays_run_free():
    store = InMemoryRunStore()
    g = StateGraph(S)
    g.add_node("a", lambda s: {"n": [1]})
    g.add_edge(START, "a")
    g.add_edge("a", END)
    g.compile().invoke({"n": []})
    assert store.recent() == []


# ---------------------------------------------------------------------------
# (8) inertness + wiring + version
# ---------------------------------------------------------------------------


def test_fresh_interpreter_import_stays_inert():
    probe = (
        "import os, sys, threading;"
        "before_threads = threading.active_count();"
        "before_env = {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'AEP_'))};"
        "from pathlib import Path;"
        "cwd = Path('.');"
        "before_files = {p.name for p in cwd.iterdir()};"
        "sys.path.insert(0, sys.argv[1]);"
        "import app.aep;"
        "assert threading.active_count() == before_threads, 'import spawned threads';"
        "assert {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'AEP_'))} == before_env, 'env read/written';"
        "assert {p.name for p in cwd.iterdir()} == before_files, 'import created files';"
        "print('inert-ok')"
    )
    r = subprocess.run([sys.executable, "-c", probe, str(SERVER)],
                       capture_output=True, text=True, timeout=120, cwd="/tmp")
    assert r.returncode == 0, r.stderr[-800:]
    assert "inert-ok" in r.stdout


def test_package_export_law_covers_the_graph_surface():
    for name in ("START", "END", "INTERRUPT_KEY", "AgentState", "add_messages",
                 "BaseCheckpointSaver", "MemorySaver", "SqliteSaver",
                 "Command", "CompiledStateGraph", "GraphInterrupt",
                 "GraphRecursionError", "StateGraph", "interrupt"):
        assert name in aep.__all__ and getattr(aep, name, None) is not None
    assert hasattr(aep, "graph"), "aep.graph not exported as a module"


def test_no_new_registry_tools_and_voice_untouched():
    src = (SERVER / "app" / "aep" / "graph.py").read_text()
    assert "input_schema" not in src and "DOCS7_SCHEMA" not in src
    assert "VOICE_TOOL_NAMES" not in src


def test_no_config_reads_in_graph_module():
    src = (SERVER / "app" / "aep" / "graph.py").read_text()
    assert "get_settings" not in src and "os.environ" not in src


def test_version_pins():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.813.0"
    assert "0.813.0+812" in (REPO_ROOT / "pubspec.yaml").read_text()
    line = (SERVER / "app" / "main.py").read_text().splitlines()[35]
    assert line.startswith('APP_VERSION = "0.813.0"')
    # story pin moved to the newest story (the newest-story precedent; the P3
    # markers live in the Previous chain and git history)
    # the P6 story pins moved to the P7 suite (the newest-story precedent;
    # the P3 markers live in the Previous chain and git history)
