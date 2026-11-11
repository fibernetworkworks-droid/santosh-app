"""G1 of docs/LANGGRAPH_TURN_PLAN.md: a graph turn (`chat_graph` on) survives a restart.

The crash is simulated the way a dying worker looks from inside the turn: a fake brain / fake tool raises
CancelledError at the chosen point, the turn's inbox row stays `running`, the in-memory state is cleared (locks, the
graph's live runs), and the restart sweep runs in a FRESH event loop. With chat_graph on the turn continues from its
checkpoint (the tool ledger decides an interrupted tool); with chat_graph off the old RESUME_NOTE re-run is unchanged."""
import asyncio
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_g0_turngraph import _new_conv, _rows, _settings, tu, txt

CRASH = "CRASH"


class Brain:
    """Scripted brain; a CRASH step raises CancelledError (the process dies during that model call)."""

    def __init__(self, script, record=None):
        self.script = list(script)
        self.calls = 0
        self.sent: list[str] = []
        self.record = record
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.calls += 1
        self.sent.append(json.dumps(kw.get("messages"), ensure_ascii=False, default=str))
        if self.record is not None:
            self.record(kw)
        step = self.script.pop(0) if self.script else txt("(script ended)")
        if step == CRASH:
            raise asyncio.CancelledError()
        stop = "tool_use" if any(b["type"] == "tool_use" for b in step) else "end_turn"
        return SimpleNamespace(content=json.loads(json.dumps(step)), stop_reason=stop)


class Tools:
    """Fake dispatch: counts calls per tool; a tool in `crash` raises CancelledError on its first call."""

    def __init__(self, crash=()):
        self.crash = set(crash)
        self.count: dict[str, int] = {}

    async def dispatch(self, name, args, ctx):
        self.count[name] = self.count.get(name, 0) + 1
        if name in self.crash:
            self.crash.discard(name)
            raise asyncio.CancelledError()
        return {"ok": True, "tool": name, "rows": [1, 2, 3]}


def _restart():
    """What a pm2 restart wipes: the chat locks, stop marks, the graph's live objects."""
    from app.agent import santosh, turngraph
    santosh._locks.clear()
    santosh._stopped.clear()
    turngraph._RUNS.clear()


def _age(rid):
    from app import turn_inbox as ti
    from app.db import now, session
    with session() as s:
        r = s.get(ti.TurnInbox, rid)
        assert r.status == "running"
        r.updated_at = now() - timedelta(minutes=10)


async def _sweep():
    from app import turn_inbox as ti
    n = await ti.sweep()
    while ti._BG:
        await asyncio.gather(*list(ti._BG), return_exceptions=True)
    return n


def _owned(conv, rid, ask):
    from app import turn_inbox as ti
    return ti.run_owned(rid, conv, ask, "default", False, client_id="c-" + rid)


def _setup(monkeypatch, graph, tools, brain, extra=None):
    _settings(monkeypatch, graph, extra)
    from app.agent import santosh, set_client
    monkeypatch.setattr(santosh, "dispatch", tools.dispatch)
    set_client(brain)


def _crash_and_resume(monkeypatch, script, ask, crash_tools=(), graph=True):
    """Run once until the CRASH, restart, sweep. Returns (conv, rid, brain, tools, sweep count)."""
    from app import turn_inbox as ti
    tools, brain = Tools(crash_tools), Brain(script)
    _setup(monkeypatch, graph, tools, brain)
    conv = _new_conv()
    rid = ti.accept("default", conv, ask, False, "", "c-x")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_owned(conv, rid, ask))
    _restart()
    _age(rid)
    n = asyncio.run(_sweep())
    return conv, rid, brain, tools, n


def _clean_run(monkeypatch, script, ask):
    from app import turn_inbox as ti
    tools, brain = Tools(), Brain(script)
    _setup(monkeypatch, True, tools, brain)
    conv = _new_conv()
    rid = ti.accept("default", conv, ask, False, "", "c-y")
    out = asyncio.run(_owned(conv, rid, ask))
    return conv, rid, out, tools


def _status(rid):
    from app import turn_inbox as ti
    from app.db import session
    with session() as s:
        return s.get(ti.TurnInbox, rid).status


def _last_reply(conv):
    rows = [d for r, d in _rows(conv) if r == "assistant" and d and not d.startswith("(Kaam:")]
    return rows[-1] if rows else ""


# (a) killed after the tools node, before the next model call -> resumes at model, the tool is not run again
def test_crash_before_next_model_call_resumes_at_model(bz, monkeypatch):  # noqa: F811
    from app.agent import turngraph
    script = [[tu(1, "list_reminders")], CRASH, txt("Aapke 3 reminder hain.")]
    r0 = turngraph.STATS["resumed"]
    conv, rid, brain, tools, n = _crash_and_resume(monkeypatch, script, "mere reminders batao")
    assert n == 1 and turngraph.STATS["resumed"] == r0 + 1
    assert tools.count == {"list_reminders": 1}             # done in the first life, never again
    assert brain.calls == 3                                  # step 1, the crashed call, the resumed call
    assert _status(rid) == "done"
    ref_conv, _, ref_out, _ = _clean_run(monkeypatch, [[tu(1, "list_reminders")], txt("Aapke 3 reminder hain.")],
                                         "mere reminders batao")
    assert _last_reply(conv) == ref_out == "Aapke 3 reminder hain."
    assert _rows(conv) == _rows(ref_conv)                    # same saved rows as an uninterrupted run


# (b) killed inside the tools node after `intent` of a SIDE-EFFECT tool -> never sent again, the model is told
def test_interrupted_send_is_not_run_again(bz, monkeypatch):  # noqa: F811
    from app.agent import toolledger as L
    line = "It is not done yet - the next step is to check the sent folder before trying again."
    script = [[tu(1, "email_send", to="ravi@x.in")], txt(line), txt(line)]
    a0 = L.STATS["ambiguous"]
    conv, rid, brain, tools, n = _crash_and_resume(monkeypatch, script, "ravi ko mail bhejo",
                                                   crash_tools=("email_send",))
    assert n == 1
    assert tools.count == {"email_send": 1}                  # the one interrupted call; resume did NOT send again
    assert L.STATS["ambiguous"] == a0 + 1
    assert "MAY ALREADY HAVE RUN" in brain.sent[1]            # the resumed model call saw the honest result
    assert not any("Server restart" in m for m in brain.sent)  # no RESUME_NOTE re-run
    assert _last_reply(conv) == line


# (c) the same for a READ-ONLY tool -> it is simply run again
def test_interrupted_read_is_run_again(bz, monkeypatch):  # noqa: F811
    from app.agent import toolledger as L
    script = [[tu(1, "list_reminders")], txt("Aapke 3 reminder hain.")]
    r0 = L.STATS["rerun_read"]
    conv, rid, brain, tools, n = _crash_and_resume(monkeypatch, script, "mere reminders batao",
                                                   crash_tools=("list_reminders",))
    assert tools.count == {"list_reminders": 2}              # interrupted once, run again on resume
    assert L.STATS["rerun_read"] == r0 + 1
    assert "MAY ALREADY HAVE RUN" not in brain.sent[-1]
    assert _last_reply(conv) == "Aapke 3 reminder hain."


# (d) a `done` ledger row is reused, never re-run (here: the send finished, the read after it was cut)
def test_done_tool_is_reused_not_run_again(bz, monkeypatch):  # noqa: F811
    from app.agent import toolledger as L
    script = [[tu(1, "email_send", to="a@b.in"), tu(2, "list_reminders")], txt("Mail gaya, 3 reminder hain.")]
    u0 = L.STATS["reused"]
    conv, rid, brain, tools, n = _crash_and_resume(monkeypatch, script, "mail bhejo aur reminders batao",
                                                   crash_tools=("list_reminders",))
    assert tools.count == {"email_send": 1, "list_reminders": 2}
    assert L.STATS["reused"] == u0 + 1
    last = json.loads(brain.sent[-1])[-1]["content"]          # the tool results the resumed model call saw
    res = {b["tool_use_id"]: b for b in last if b.get("type") == "tool_result"}
    assert '"tool": "email_send"' in res["tu_1"]["content"] and not res["tu_1"].get("is_error")
    assert _last_reply(conv) == "Mail gaya, 3 reminder hain."


# (e) the sweep: on = resume from the checkpoint (her row once, no RESUME_NOTE); off = the old re-run, unchanged
def test_sweep_resumes_on_graph_and_reruns_on_old_path(bz, monkeypatch):  # noqa: F811
    from app import turn_inbox as ti
    from app.agent import turngraph
    script = [[tu(1, "list_reminders")], CRASH, txt("Aapke 3 reminder hain.")]
    g0, o0 = ti.STATS.get("graph_resumed", 0), ti.STATS.get("resumed", 0)
    conv, rid, brain, tools, n = _crash_and_resume(monkeypatch, script, "mere reminders batao")
    assert ti.STATS.get("graph_resumed", 0) == g0 + 1 and ti.STATS.get("resumed", 0) == o0
    assert [d for r, d in _rows(conv) if r == "user" and d] == ["mere reminders batao"]
    assert not any("Server restart" in m for m in brain.sent)

    r0 = turngraph.STATS["resumed"]
    conv2, rid2, brain2, tools2, n2 = _crash_and_resume(monkeypatch, script, "mere reminders batao", graph=False)
    assert n2 == 1 and turngraph.STATS["resumed"] == r0           # the graph never ran
    assert ti.STATS.get("resumed", 0) == o0 + 1                    # the v0.657 path
    assert ti.RESUME_NOTE[:40] in brain2.sent[-1]
    assert [d for r, d in _rows(conv2) if r == "user" and d] == ["mere reminders batao"]


def test_no_checkpoint_means_old_path_even_with_graph_on(bz, monkeypatch):  # noqa: F811
    """A turn that died before any graph checkpoint (here: the row was never run) keeps today's path."""
    from app import turn_inbox as ti
    from app.db import Message, now, session
    _settings(monkeypatch, True)
    conv = _new_conv()
    rid = ti.accept("default", conv, "hello", False, "", "c-z")
    with session() as s:
        r = s.get(ti.TurnInbox, rid)
        r.status, r.updated_at, r.started_at = "running", now() - timedelta(minutes=10), r.created_at
        s.add(Message(conversation_id=conv, role="user", content="hello", display="hello", in_history=True))
    ran = []
    import app.agent as ap

    async def fake(*a, **k):
        ran.append(k)
        return "x"
    monkeypatch.setattr(ap, "run_turn", fake)
    asyncio.run(_sweep())
    assert len(ran) == 1 and ti.RESUME_NOTE in ran[0]["context"]


# (f) a finished turn leaves no checkpoints and no ledger rows; thread ids are never empty / 'default'
def test_finished_turn_is_cleaned(bz, monkeypatch):  # noqa: F811
    from app.agent import toolledger as L
    from app.agent import turngraph
    from app.config import get_settings
    conv, rid, out, _ = _clean_run(monkeypatch, [[tu(1, "list_reminders")], txt("ok")], "reminders batao")
    assert out == "ok"
    assert asyncio.run(turngraph.checkpoints(get_settings(), conv)) == []
    assert L.rows(turngraph.thread_id(conv, rid)) == []
    conv2, rid2, brain, tools, n = _crash_and_resume(monkeypatch, [[tu(1, "list_reminders")], CRASH, txt("ok")],
                                                     "reminders batao")
    assert asyncio.run(turngraph.checkpoints(get_settings(), conv2)) == []      # cleaned after the resumed END too
    assert L.rows(turngraph.thread_id(conv2, rid2)) == []
    for bad in (("", "t"), ("c", ""), ("default", "t"), ("c", "default")):
        with pytest.raises(ValueError):
            turngraph.thread_id(*bad)


def test_thread_id_is_the_inbox_row(bz, monkeypatch):  # noqa: F811
    """While the turn runs its checkpoint thread is '<conversation>:<inbox id>' (stable across a restart)."""
    from app import turn_inbox as ti
    from app.agent import turngraph
    seen = []

    async def dispatch(name, args, ctx):
        seen.extend(turngraph._RUNS.keys())
        return {"ok": True}
    _settings(monkeypatch, True)
    from app.agent import santosh, set_client
    monkeypatch.setattr(santosh, "dispatch", dispatch)
    set_client(Brain([[tu(1, "list_reminders")], txt("ok")]))
    conv = _new_conv()
    rid = ti.accept("default", conv, "reminders", False, "", "c-t")
    asyncio.run(_owned(conv, rid, "reminders"))
    assert seen == [f"{conv}:{rid}"]


# (g) G0's gap: a model choice / effort set in one node reaches a LATER model call, same on both paths
def test_model_choice_set_in_one_node_reaches_the_next_model_call(bz, monkeypatch):  # noqa: F811
    from app.agent import llm
    from app.agent import santosh
    from app import modelchoice
    monkeypatch.setattr(modelchoice, "chosen", lambda tenant: "picked/model")   # the dropdown, before the graph
    monkeypatch.setattr(santosh, "effort_for", lambda *a, **k: "high")          # set by the model node, every step
    seen = {}
    for graph in (False, True):
        rec = []

        def record(kw, _r=rec):
            _r.append((kw.get("model"), santosh._MODEL_NOW.get(), santosh._EFFORT_NOW.get(), llm.MODEL_NOW.get()))

        async def dispatch(name, args, ctx, _r=rec):   # the tools node reads what the MODEL node set
            _r.append(("tool", santosh._MODEL_NOW.get(), santosh._EFFORT_NOW.get(), llm.MODEL_NOW.get()))
            return {"ok": True}
        _settings(monkeypatch, graph)
        from app.agent import run_turn, set_client
        monkeypatch.setattr(santosh, "dispatch", dispatch)
        set_client(Brain([[tu(1, "list_reminders")], txt("ok")], record=record))
        asyncio.run(run_turn(_new_conv(), "mere reminders batao", tenant_id="default"))
        seen[graph] = rec
    assert seen[True] == seen[False]
    first, tool, second = seen[True]
    assert tool[0] == "tool"
    assert tool[1] == first[1] and tool[2] == first[2] == "high"   # model node -> tools node
    assert second[3] == first[3] == tool[3] == "picked/model"      # before the graph -> every later node
    assert first[0]                                                # the model the call really asked for
