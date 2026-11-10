"""G0 of docs/LANGGRAPH_TURN_PLAN.md: the chat turn on an official LangGraph StateGraph (`chat_graph`).

The SAME scripted conversation runs through the old while-loop (chat_graph off) and the graph (chat_graph on), and
both must leave the same saved rows, the same sequence of published events and the same final reply - because both
call the same step functions (santosh._turn_model / _turn_after_model / _turn_tools ...)."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from tests.test_bazar import bz  # noqa: F401  (fixture)


def tu(i, name, **inp):
    return {"type": "tool_use", "id": f"tu_{i}", "name": name, "input": inp}


def txt(t):
    return [{"type": "text", "text": t}]


class Scripted:
    """Plays back (blocks, stop) steps; stop defaults to tool_use / end_turn like the real API."""

    def __init__(self, script):
        self.script = [s for s in script]
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.calls += 1
        step = self.script.pop(0) if self.script else txt("(script ended)")
        stop = None
        if isinstance(step, tuple):
            step, stop = step
        if stop is None:
            stop = "tool_use" if any(b["type"] == "tool_use" for b in step) else "end_turn"
        return SimpleNamespace(content=json.loads(json.dumps(step)), stop_reason=stop)


def _settings(monkeypatch, graph: bool, extra: dict | None = None):
    monkeypatch.setenv("CHAT_GRAPH", "true" if graph else "false")
    monkeypatch.setenv("CONSOLE_V2", "false")      # no live deltas: the stored events are what is compared
    monkeypatch.setenv("CONSOLE_STREAM", "false")
    monkeypatch.setenv("DRAFT_CHECK_AI", "false")
    for k, v in (extra or {}).items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    return get_settings()


def _fake_dispatch(monkeypatch):
    from app.agent import santosh
    from app.agent.tools import ToolError

    async def dispatch(name, args, ctx):
        if name == "list_reminders" and (args or {}).get("boom"):
            raise ToolError("reminder store is down")
        return {"ok": True, "tool": name, "args": args, "rows": [1, 2, 3]}

    monkeypatch.setattr(santosh, "dispatch", dispatch)


def _new_conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def _rows(conv):
    from app.db import Message, session
    with session() as s:
        ms = s.execute(select(Message).where(Message.conversation_id == conv).order_by(Message.id)).scalars().all()
        return [(m.role, m.display) for m in ms]


def _kinds(conv):
    from app.db import Event, session
    with session() as s:
        evs = s.execute(select(Event).where(Event.conversation_id == conv).order_by(Event.id)).scalars().all()
        out = []
        for e in evs:
            p = e.payload or {}
            tag = p.get("state") or p.get("role") or ""
            out.append(f"{e.kind}:{tag}")
        return out


def _run(monkeypatch, graph: bool, script, ask: str, extra=None):
    _settings(monkeypatch, graph, extra)
    _fake_dispatch(monkeypatch)
    from app.agent import run_turn, santosh, set_client
    client = Scripted(script)
    set_client(client)
    conv = _new_conv()
    out = asyncio.run(asyncio.wait_for(run_turn(conv, ask, tenant_id="default"), 120))
    return {"out": out, "rows": _rows(conv), "kinds": _kinds(conv), "calls": client.calls,
            "outcome": (santosh.LAST_OUTCOME.get(conv) or {}).get("outcome"), "conv": conv}


def _both(monkeypatch, script, ask, extra=None):
    from app.agent import turngraph
    n0 = turngraph.STATS["turns"]
    old = _run(monkeypatch, False, list(script), ask, extra)
    assert turngraph.STATS["turns"] == n0               # the old loop answered
    new = _run(monkeypatch, True, list(script), ask, extra)
    assert turngraph.STATS["turns"] == n0 + 1           # the graph answered
    assert new["out"] == old["out"]
    assert new["rows"] == old["rows"]
    assert new["kinds"] == old["kinds"]
    assert new["calls"] == old["calls"]
    assert new["outcome"] == old["outcome"]
    return old, new


def test_switch_is_off_by_default(env):  # noqa: F811
    from app.config import Settings
    assert Settings.model_fields["chat_graph"].default is False
    from app.agent import turngraph
    assert turngraph.AVAILABLE


def test_plain_answer_same_on_both_paths(bz, monkeypatch):  # noqa: F811
    old, new = _both(monkeypatch, [txt("Namaste ji, bataiye kya karna hai.")], "namaste")
    assert old["out"] == "Namaste ji, bataiye kya karna hai."
    assert old["outcome"] == "talk"


def test_one_tool_then_answer(bz, monkeypatch):  # noqa: F811
    old, new = _both(monkeypatch, [[tu(1, "list_reminders")], txt("Aapke 3 reminder hain.")], "mere reminders batao")
    assert old["out"] == "Aapke 3 reminder hain."
    assert any(k == "step:running" for k in old["kinds"]) and any(k == "step:done" for k in old["kinds"])
    assert old["outcome"] == "done"


def test_two_parallel_safe_tools(bz, monkeypatch):  # noqa: F811
    old, new = _both(monkeypatch, [[tu(1, "google_search", query="a"), tu(2, "maps_search", query="b")],
                                   txt("Dono mil gaye.")], "dono dhoondo")
    assert old["out"] == "Dono mil gaye."
    assert old["kinds"].count("step:done") == 2


def test_tool_error(bz, monkeypatch):  # noqa: F811
    old, new = _both(monkeypatch, [[tu(1, "list_reminders", boom=True)], txt("Reminder abhi nahi mil paye.")],
                     "reminders batao")
    assert "nahi mil paye" in old["out"]
    assert "step:error" in old["kinds"]


def test_false_sent_claim_is_nudged_then_answered(bz, monkeypatch):  # noqa: F811
    extra = {"CHAT_PLAIN_LOOP": "true"}
    old, new = _both(monkeypatch, [txt("I've sent the email to Ravi."),
                                   txt("I have not sent anything yet - shall I draft the email to Ravi?")],
                     "ravi ko email bhejo", extra)
    assert old["calls"] == 2                          # the plain check sent the false claim back once
    assert "not sent" in old["out"]


def test_max_tokens_cut_continues(bz, monkeypatch):  # noqa: F811
    old, new = _both(monkeypatch, [(txt("Pehla hissa"), "max_tokens"), txt("aur doosra hissa.")], "lamba likho")
    assert old["calls"] == 2


def test_step_cap(bz, monkeypatch):  # noqa: F811
    extra = {"AGENT_MAX_STEPS": "2", "AGENT_GOAL": "false"}
    script = [[tu(1, "google_search", query="one")], [tu(2, "google_search", query="two")],
              [tu(3, "google_search", query="three")]]
    old, new = _both(monkeypatch, script, "kuch dhoondo", extra)
    assert "not finished yet" in old["out"]
    assert old["calls"] == 2
    assert old["outcome"] == "partial"


def test_checkpoint_is_written(bz, monkeypatch):  # noqa: F811
    r = _run(monkeypatch, True, [[tu(1, "list_reminders")], txt("Aapke 3 reminder hain.")], "reminders batao",
             {"CHAT_GRAPH_KEEP_FINISHED": "true"})   # G1 deletes a finished turn's checkpoints unless kept
    from app.agent import turngraph
    from app.config import get_settings
    rows = asyncio.run(turngraph.checkpoints(get_settings(), r["conv"]))
    assert rows, "no checkpoint written"
    last = rows[0]["values"]
    assert last.get("final_text") == "Aapke 3 reminder hain."
    assert last.get("outcome") == "done"
    roles = [m.get("role") for m in last.get("messages") or []]
    assert roles[-2:] == ["user", "assistant"] and "tool_result" in json.dumps(last["messages"])
    assert not turngraph._RUNS                         # the live objects are gone after the turn


def test_old_path_never_touches_the_graph(bz, monkeypatch):  # noqa: F811
    from app.agent import turngraph

    async def boom(*a, **k):
        raise AssertionError("graph ran with chat_graph off")

    monkeypatch.setattr(turngraph, "run_steps", boom)
    r = _run(monkeypatch, False, [txt("ok")], "hello")
    assert r["out"] == "ok"


def test_context_vars_set_in_one_node_reach_the_next(bz, monkeypatch):  # noqa: F811
    """LangGraph runs every node in its own task; the turn's ASK_NOW (set in prepare) and model / effort (set in the
    model node) must still be what a tool sees - as in the old single-task loop."""
    seen = {}
    for graph in (False, True):
        _settings(monkeypatch, graph)
        from app.agent import run_turn, santosh, set_client

        async def dispatch(name, args, ctx, _g=graph):
            seen[_g] = (santosh.ASK_NOW.get(), santosh._MODEL_NOW.get(), santosh._EFFORT_NOW.get())
            return {"ok": True}

        monkeypatch.setattr(santosh, "dispatch", dispatch)
        set_client(Scripted([[tu(1, "list_reminders")], txt("ok")]))
        asyncio.run(run_turn(_new_conv(), "mere reminders batao", tenant_id="default"))
    assert seen[True] == seen[False]
    assert seen[True][0] == "mere reminders batao"
