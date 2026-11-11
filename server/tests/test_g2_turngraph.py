"""G2 of docs/LANGGRAPH_TURN_PLAN.md: ONE RUN PER CHAT and STOP AS STATE (`chat_graph` on).

Fake brain / fake tools in the style of test_g0 / test_g1. The brain answers by the ask marker of the turn it is
serving (her words are the last text block of the newest plain user message), so two turns of one chat can be told
apart in the order of model calls. A Stop is the real one (`santosh.stop`, which the Stop button and kaamstop call)."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_g0_turngraph import _new_conv, _rows, _settings, tu, txt

HALT = "Okay, I stopped the work."
MIDWAY = "The step that was running was stopped midway"


def _ask_of(messages, markers):
    for m in reversed(messages or []):
        if m.get("role") != "user":
            continue
        c = m.get("content")
        if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            continue
        texts = [c] if isinstance(c, str) else [b.get("text", "") for b in c if isinstance(b, dict) and b.get("text")]
        text = texts[-1] if texts else ""                     # her words: the LAST block (memory rides in front)
        best, at = None, -1
        for k in markers:
            i = text.rfind(k)
            if i > at:
                best, at = k, i
        return best
    return None


class Brain:
    """plan = {marker: [steps]}; each model call serves the marker of its turn. `delay` = seconds per call (a slow
    model, so a Stop on the old path lands DURING the call); `live_check` records how many runs are live."""

    def __init__(self, plan, delay=0.0, conv=None):
        self.plan = {k: list(v) for k, v in plan.items()}
        self.delay = delay
        self.order: list = []
        self.sent: list[str] = []
        self.live_max = 0
        self.conv = conv
        self.messages = SimpleNamespace(create=self._create)

    @property
    def calls(self):
        return len(self.order)

    async def _create(self, **kw):
        from app.agent import turnrun
        msgs = kw.get("messages") or []
        self.sent.append(json.dumps(msgs, ensure_ascii=False, default=str))
        who = _ask_of(msgs, list(self.plan))
        self.order.append(who)
        if self.conv is not None:
            self.live_max = max(self.live_max, sum(1 for r in turnrun._CHATS.get(self.conv, []) if r.state == "live"))
        if self.delay:
            await asyncio.sleep(self.delay)
        steps = self.plan.get(who) or []
        step = steps.pop(0) if steps else txt(f"(no more steps for {who})")
        stop = "tool_use" if any(b["type"] == "tool_use" for b in step) else "end_turn"
        return SimpleNamespace(content=json.loads(json.dumps(step)), stop_reason=stop)


class Tools:
    def __init__(self, slow=None, on_call=None):
        self.slow = dict(slow or {})          # tool -> seconds
        self.on_call = on_call                # callable(name, ctx) after the work (e.g. a Stop between steps)
        self.count: dict[str, int] = {}
        self.cancelled: list[str] = []

    async def dispatch(self, name, args, ctx):
        self.count[name] = self.count.get(name, 0) + 1
        try:
            if self.slow.get(name):
                await asyncio.sleep(self.slow[name])
        except asyncio.CancelledError:
            self.cancelled.append(name)
            raise
        if self.on_call:
            self.on_call(name, ctx)
        return {"ok": True, "tool": name}


def _setup(monkeypatch, graph, brain, tools, extra=None):
    st = _settings(monkeypatch, graph, {"AGENT_STEER": "false", "QUICK_LANE": "false", **(extra or {})})
    from app.agent import santosh, set_client
    monkeypatch.setattr(santosh, "dispatch", tools.dispatch)
    set_client(brain)
    return st


def _owned(conv, rid, ask, cid=None):
    from app import turn_inbox as ti
    return ti.run_owned(rid, conv, ask, "default", False, client_id=cid or ("c-" + str(rid)))


def _accept(conv, ask, cid):
    from app import turn_inbox as ti
    return ti.accept("default", conv, ask, False, "", cid)


def _status(rid):
    from app import turn_inbox as ti
    from app.db import session
    with session() as s:
        return s.get(ti.TurnInbox, rid).status


def _shown(conv):
    """The rows she sees (display set), without the (Kaam:) ledger note."""
    return [(r, d) for r, d in _rows(conv) if d and not d.startswith("(Kaam:")]


def _later(delay, fn, tools=None):
    """fn() `delay` seconds after the slow tool has started (when `tools` is given), else after `delay`."""
    async def go():
        while tools is not None and not tools.count:
            await asyncio.sleep(0.02)
        await asyncio.sleep(delay)
        fn()
    return go()


# 1. two messages back to back on one chat -> one run at a time, both answered, in order, no duplicate rows
def test_two_messages_one_run_at_a_time_in_order(bz, monkeypatch):  # noqa: F811
    from app.agent import turnrun
    conv = _new_conv()
    brain = Brain({"ASKA": [[tu(1, "list_reminders")], txt("answer A")], "ASKB": [txt("answer B")]}, conv=conv)
    tools = Tools(slow={"list_reminders": 0.5})
    _setup(monkeypatch, True, brain, tools)
    ra, rb = _accept(conv, "ASKA please", "ca"), _accept(conv, "ASKB please", "cb")

    async def both():
        ta = asyncio.ensure_future(_owned(conv, ra, "ASKA please"))
        await asyncio.sleep(0.15)                            # B arrives while A's tool runs
        tb = asyncio.ensure_future(_owned(conv, rb, "ASKB please"))
        await asyncio.sleep(0.1)
        assert [r.state for r in turnrun._CHATS[conv]] == ["live", "queued"]   # B is A's next input, not a 2nd run
        return await asyncio.gather(ta, tb)
    t0 = turnrun.STATS["waited"]
    outs = asyncio.run(asyncio.wait_for(both(), 60))
    assert outs == ["answer A", "answer B"]
    assert brain.order == ["ASKA", "ASKA", "ASKB"]           # B's model call only after A finished
    assert brain.live_max == 1                              # never two live runs
    assert turnrun.STATS["waited"] >= t0 + 1
    shown = _shown(conv)
    assert [d for r, d in shown if r == "user"] == ["ASKA please", "ASKB please"]
    assert [d for r, d in shown if r == "assistant"][-2:] == ["answer A", "answer B"]
    assert len([1 for r, d in shown if d == "answer A"]) == 1 and len([1 for r, d in shown if d == "answer B"]) == 1
    assert _status(ra) == _status(rb) == "done"
    assert turnrun._CHATS.get(conv) is None                 # every ticket given back


# 1b. arrival order wins even when the earlier message has more pre-lock work (the old lock let B overtake A)
def test_arrival_order_beats_prelock_work(bz, monkeypatch):  # noqa: F811
    from app.operator import service as ops
    conv = _new_conv()
    brain = Brain({"ASKA": [txt("answer A")], "ASKB": [txt("answer B")]}, conv=conv)
    _setup(monkeypatch, True, brain, Tools())
    real = ops.answer_from_chat

    async def slow_for_a(tenant, text):
        if "ASKA" in text:
            await asyncio.sleep(0.4)                         # A's pre-lock check is slow; B's is instant
        return await real(tenant, text)
    monkeypatch.setattr(ops, "answer_from_chat", slow_for_a)
    ra, rb = _accept(conv, "ASKA now", "ca2"), _accept(conv, "ASKB now", "cb2")

    async def both():
        ta = asyncio.ensure_future(_owned(conv, ra, "ASKA now"))
        await asyncio.sleep(0.02)
        tb = asyncio.ensure_future(_owned(conv, rb, "ASKB now"))
        return await asyncio.gather(ta, tb)
    assert asyncio.run(asyncio.wait_for(both(), 60)) == ["answer A", "answer B"]
    assert brain.order == ["ASKA", "ASKB"]
    assert [d for r, d in _shown(conv) if r == "user"] == ["ASKA now", "ASKB now"]


# 1c. the same inbox row started twice (a sweep race / a retry) runs once
def test_same_inbox_row_never_runs_twice(bz, monkeypatch):  # noqa: F811
    from app import turn_inbox as ti
    conv = _new_conv()
    brain = Brain({"ASKA": [[tu(1, "list_reminders")], txt("answer A")]}, conv=conv)
    _setup(monkeypatch, True, brain, Tools(slow={"list_reminders": 0.3}))
    ra = _accept(conv, "ASKA once", "c1")
    d0 = ti.STATS.get("duplicate_run", 0)

    async def twice():
        t1 = asyncio.ensure_future(_owned(conv, ra, "ASKA once"))
        await asyncio.sleep(0.05)
        t2 = asyncio.ensure_future(_owned(conv, ra, "ASKA once"))
        return await asyncio.gather(t1, t2)
    assert asyncio.run(asyncio.wait_for(twice(), 60)) == ["answer A", ""]
    assert ti.STATS.get("duplicate_run", 0) == d0 + 1
    assert brain.calls == 2
    assert [d for r, d in _shown(conv) if r == "user"] == ["ASKA once"]
    assert _status(ra) == "done"


# 1d. the restart sweep leaves a chat alone while a run of it is live OR queued (the lock is free between runs)
def test_sweep_skips_a_queued_row(bz, monkeypatch):  # noqa: F811
    from app import turn_inbox as ti
    from app.agent import santosh
    from app.db import now, session
    from datetime import timedelta
    conv = _new_conv()
    brain = Brain({"ASKA": [[tu(1, "list_reminders")], txt("answer A")], "ASKB": [txt("answer B")]}, conv=conv)
    _setup(monkeypatch, True, brain, Tools(slow={"list_reminders": 0.6}))
    ra, rb = _accept(conv, "ASKA x", "cx"), _accept(conv, "ASKB x", "cy")
    swept = []

    async def go():
        ta = asyncio.ensure_future(_owned(conv, ra, "ASKA x"))
        await asyncio.sleep(0.1)
        tb = asyncio.ensure_future(_owned(conv, rb, "ASKB x"))
        await asyncio.sleep(0.1)
        with session() as s:                              # B waits: its row looks dead to the sweep
            r = s.get(ti.TurnInbox, rb)
            r.updated_at = now() - timedelta(minutes=10)
        santosh._locks[conv]._locked = False              # the instant between two runs: the lock looks free
        try:
            swept.append(await ti.sweep())
        finally:
            santosh._locks[conv]._locked = True
        return await asyncio.gather(ta, tb)
    k0 = ti.STATS.get("skipped_busy", 0)
    assert asyncio.run(asyncio.wait_for(go(), 60)) == ["answer A", "answer B"]
    assert swept == [0] and ti.STATS.get("skipped_busy", 0) == k0 + 1
    assert brain.order == ["ASKA", "ASKA", "ASKB"]
    assert [d for r, d in _shown(conv) if r == "user"] == ["ASKA x", "ASKB x"]


# 1e. her own words while her job runs still reach the LIVE run (steer) - no second run is started for them
def test_her_words_steer_the_live_run(bz, monkeypatch):  # noqa: F811
    conv = _new_conv()
    brain = Brain({"ASKA": [[tu(1, "list_reminders")], [tu(2, "list_reminders")], txt("answer A")],
                   "ASKB": [txt("should not run")]}, conv=conv)
    _setup(monkeypatch, True, brain, Tools(slow={"list_reminders": 0.4}), {"AGENT_STEER": "true"})
    ra, rb = _accept(conv, "ASKA job", "cs1"), _accept(conv, "ASKB change it", "cs2")

    async def both():
        ta = asyncio.ensure_future(_owned(conv, ra, "ASKA job"))
        await asyncio.sleep(0.15)
        tb = asyncio.ensure_future(_owned(conv, rb, "ASKB change it"))
        return await asyncio.gather(ta, tb)
    outs = asyncio.run(asyncio.wait_for(both(), 60))
    assert outs == ["answer A", ""]                           # B was taken by the live run
    assert brain.order == ["ASKA", "ASKA", "ASKA"]
    assert "ASKB change it" in brain.sent[1]                  # the live run's next step read her words
    assert brain.live_max == 1


# 2. a wake landing while her turn runs waits its turn, then runs - both answered, hers first
def test_wake_waits_for_her_turn(bz, monkeypatch):  # noqa: F811
    from app.agent import run_turn
    conv = _new_conv()
    brain = Brain({"ASKA": [[tu(1, "list_reminders")], txt("answer A")], "WAKEJOB": [txt("job report")]}, conv=conv)
    _setup(monkeypatch, True, brain, Tools(slow={"list_reminders": 0.5}))
    ra = _accept(conv, "ASKA mine", "cw")

    async def both():
        ta = asyncio.ensure_future(_owned(conv, ra, "ASKA mine"))
        await asyncio.sleep(0.15)
        tw = asyncio.ensure_future(run_turn(conv, "[Kaam ka natija] WAKEJOB finished", tenant_id="default",
                                            actor="wake", save_user=False))
        return await asyncio.gather(ta, tw)
    assert asyncio.run(asyncio.wait_for(both(), 60)) == ["answer A", "job report"]
    assert brain.order == ["ASKA", "ASKA", "WAKEJOB"]
    assert brain.live_max == 1
    assert [d for r, d in _shown(conv) if r == "assistant"][-2:] == ["answer A", "job report"]


# 3a. Stop while the turn prepares (memory read, before the graph): STOPPED_IN_PREP on both paths, inbox 'stopped' on G2
def test_stop_during_turn_prep(bz, monkeypatch):  # noqa: F811
    from app.agent import santosh
    res = {}
    for graph in (False, True):
        conv = _new_conv()
        brain = Brain({"ASKA": [txt("should not run")]})
        _setup(monkeypatch, graph, brain, Tools())
        real = santosh._chat_memory

        async def mem(tenant_id, conversation_id, *a, _real=real, **k):
            santosh.stop(conversation_id)                  # she tapped Stop while Hoola read its memory
            return await _real(tenant_id, conversation_id, *a, **k)
        monkeypatch.setattr(santosh, "_chat_memory", mem)
        rid = _accept(conv, "ASKA prep", "cp")
        out = asyncio.run(asyncio.wait_for(_owned(conv, rid, "ASKA prep"), 60))
        res[graph] = (out, _shown(conv), brain.calls, _status(rid))
        monkeypatch.setattr(santosh, "_chat_memory", real)
    assert res[False][0] == res[True][0] == santosh.STOPPED_IN_PREP
    assert res[False][1] == res[True][1] == [("user", "ASKA prep"), ("assistant", santosh.STOPPED_IN_PREP)]
    assert res[False][2] == res[True][2] == 0
    assert res[False][3] == "done"                         # old path: unchanged (the Stop button never touched the inbox)
    assert res[True][3] == "stopped"


# 3b. Stop while the graph's prepare node runs: no model call on G2; the same rows as the old loop's halted call
def test_stop_during_graph_prepare(bz, monkeypatch):  # noqa: F811
    from app.agent import santosh, turngraph
    from app.config import get_settings
    res = {}
    for graph in (False, True):
        conv = _new_conv()
        brain = Brain({"ASKA": [txt("should not be shown")]}, delay=1.0)   # slow: the old loop's call is cut
        _setup(monkeypatch, graph, brain, Tools())
        real = santosh._turn_prepare

        async def prep(conversation_id, *a, _real=real, **k):
            t = await _real(conversation_id, *a, **k)
            santosh.stop(conversation_id)
            return t
        monkeypatch.setattr(santosh, "_turn_prepare", prep)
        rid = _accept(conv, "ASKA prepare", "cq")
        b0 = turngraph.STATS["stopped_at_boundary"]
        out = asyncio.run(asyncio.wait_for(_owned(conv, rid, "ASKA prepare"), 60))
        res[graph] = (out, _shown(conv), brain.calls, _status(rid), turngraph.STATS["stopped_at_boundary"] - b0,
                      (santosh.LAST_OUTCOME.get(conv) or {}).get("outcome"))
        monkeypatch.setattr(santosh, "_turn_prepare", real)
        if graph:
            assert asyncio.run(turngraph.checkpoints(get_settings(), conv)) == []
    assert res[False][0] == res[True][0] == HALT
    assert res[False][1] == res[True][1]
    assert res[False][5] == res[True][5] == "stopped"
    assert res[False][2] == 1 and res[True][2] == 0          # the graph never even made the call
    assert res[True][4] == 1 and res[False][4] == 0
    assert res[True][3] == "stopped"


# 4. Stop mid-tool: the tool is interrupted, the ledger says so, the turn ends stopped, the sweep never resumes it
def test_stop_mid_tool(bz, monkeypatch):  # noqa: F811
    from app import turn_inbox as ti
    from app.agent import santosh, toolledger as L, turngraph
    from app.config import get_settings
    res = {}
    for graph in (False, True):
        conv = _new_conv()
        brain = Brain({"ASKA": [[tu(1, "email_send", to="ravi@x.in")], txt("should not run")]})
        tools = Tools(slow={"email_send": 8})
        _setup(monkeypatch, graph, brain, tools)
        rid = _accept(conv, "ASKA mail", "cm")

        async def go():
            stop_soon = _later(0.2, lambda: santosh.stop(conv), tools)
            return (await asyncio.gather(_owned(conv, rid, "ASKA mail"), stop_soon))[0]
        t0 = time.monotonic()
        out = asyncio.run(asyncio.wait_for(go(), 60))
        res[graph] = dict(out=out, rows=_shown(conv), calls=brain.calls, status=_status(rid), took=time.monotonic() - t0,
                          cancelled=list(tools.cancelled), count=dict(tools.count), all=_rows(conv),
                          ledger=L.rows(turngraph.thread_id(conv, rid)), conv=conv, rid=rid)
    for g in (False, True):
        r = res[g]
        assert r["out"].startswith(HALT) and MIDWAY in r["out"]
        assert r["cancelled"] == ["email_send"] and r["count"] == {"email_send": 1}
        assert r["took"] < 4 and r["calls"] == 1
    assert res[False]["rows"] == res[True]["rows"]
    assert res[False]["status"] == "done" and res[True]["status"] == "stopped"
    led = res[True]["ledger"]
    assert led and led[0]["tool"] == "email_send" and led[0]["state"] == "failed"
    from app.db import Message, session
    from sqlalchemy import select
    with session() as s:
        tr = [m.content for m in s.scalars(select(Message).where(Message.conversation_id == res[True]["conv"])).all()
              if isinstance(m.content, list) and any(b.get("type") == "tool_result" for b in m.content)]
    assert any("Stopped by the owner while this step was running" in json.dumps(c) for c in tr)
    # the restart: nothing resumes or re-runs it
    conv, rid = res[True]["conv"], res[True]["rid"]
    assert asyncio.run(turngraph.checkpoints(get_settings(), conv)) == []
    assert asyncio.run(turngraph.resumable(get_settings(), conv, rid)) is False
    santosh._locks.clear()
    santosh._stopped.clear()
    turngraph._RUNS.clear()
    n = asyncio.run(ti.sweep())
    while ti._BG:
        asyncio.run(asyncio.wait_for(asyncio.gather(*list(ti._BG), return_exceptions=True), 30))
    assert n == 0 and _status(rid) == "stopped"


# 4b. a stopped checkpoint is never resumable, even when the process dies before the turn's END
def test_stopped_checkpoint_is_not_resumable(bz, monkeypatch):  # noqa: F811
    from app import turn_inbox as ti
    from app.agent import santosh, turngraph
    from app.config import get_settings
    from app.db import session
    conv = _new_conv()
    brain = Brain({"ASKA": [[tu(1, "email_send", to="a@b.in")], txt("x")]})
    tools = Tools(slow={"email_send": 8})
    _setup(monkeypatch, True, brain, tools)
    real = santosh._steps_end

    async def die(*a, **k):                               # the process dies inside the finish node
        raise asyncio.CancelledError()
    monkeypatch.setattr(santosh, "_steps_end", die)
    rid = _accept(conv, "ASKA die", "cd")

    async def go():
        await asyncio.gather(_owned(conv, rid, "ASKA die"), _later(0.2, lambda: santosh.stop(conv), tools))
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(asyncio.wait_for(go(), 60))
    monkeypatch.setattr(santosh, "_steps_end", real)
    cps = asyncio.run(turngraph.checkpoints(get_settings(), conv))
    assert cps and cps[0]["values"].get("stopped") is True and cps[0]["values"].get("prepared") is True
    assert asyncio.run(turngraph.resumable(get_settings(), conv, rid)) is False
    vals = dict(cps[0]["values"])                          # the very same checkpoint without the flag WOULD resume
    assert turngraph._resumable_snap(SimpleNamespace(next=("finish",), values={**vals, "stopped": False}))
    assert not turngraph._resumable_snap(SimpleNamespace(next=("finish",), values=vals))
    assert _status(rid) == "stopped"                       # marked at the moment of the Stop
    with session() as s:
        assert s.get(ti.TurnInbox, rid).status == "stopped"


# 5. Stop between steps: the step finished, the next model call never starts; the same rows as the old loop
def test_stop_between_steps(bz, monkeypatch):  # noqa: F811
    from app.agent import santosh, turngraph
    res = {}
    for graph in (False, True):
        conv = _new_conv()
        brain = Brain({"ASKA": [[tu(1, "list_reminders")], txt("should not be shown")]}, delay=0.6)
        _setup(monkeypatch, graph, brain, Tools())
        real = santosh._turn_tools

        async def tools_then_stop(t, blocks, _real=real):
            out = await _real(t, blocks)
            santosh.stop(t.conversation_id)                # she taps Stop the moment the step is done
            return out
        monkeypatch.setattr(santosh, "_turn_tools", tools_then_stop)
        rid = _accept(conv, "ASKA steps", "cb")
        b0 = turngraph.STATS["stopped_at_boundary"]
        out = asyncio.run(asyncio.wait_for(_owned(conv, rid, "ASKA steps"), 60))
        res[graph] = (out, _shown(conv), brain.calls, _status(rid), turngraph.STATS["stopped_at_boundary"] - b0)
        monkeypatch.setattr(santosh, "_turn_tools", real)
    assert res[False][0] == res[True][0] == HALT
    assert res[False][1] == res[True][1]
    assert res[False][2] == 2 and res[True][2] == 1        # old: the 2nd call starts and is cut; graph: never starts
    assert res[True][4] == 1 and res[True][3] == "stopped" and res[False][3] == "done"


# 5b. Stop inside the last tool of a step (the step's own end check): identical on both paths
def test_stop_at_end_of_tool_step(bz, monkeypatch):  # noqa: F811
    from app.agent import santosh
    res = {}
    for graph in (False, True):
        conv = _new_conv()
        brain = Brain({"ASKA": [[tu(1, "list_reminders")], txt("should not be shown")]})
        tools = Tools(on_call=lambda name, ctx: santosh.stop(ctx.conversation_id))
        _setup(monkeypatch, graph, brain, tools)
        rid = _accept(conv, "ASKA end", "ce")
        out = asyncio.run(asyncio.wait_for(_owned(conv, rid, "ASKA end"), 60))
        res[graph] = (out, _shown(conv), brain.calls, dict(tools.count))
    assert res[False] == res[True]
    assert res[True][0] == HALT and res[True][2] == 1 and res[True][3] == {"list_reminders": 1}


# 6. the switch off: no tickets, no inbox 'stopped', the old lock alone (byte-identical behaviour)
def test_old_path_unchanged_with_switch_off(bz, monkeypatch):  # noqa: F811
    from app.agent import santosh, turnrun
    conv = _new_conv()
    brain = Brain({"ASKA": [[tu(1, "list_reminders")], txt("answer A")], "ASKB": [txt("answer B")]})
    _setup(monkeypatch, False, brain, Tools(slow={"list_reminders": 0.3}))
    ra, rb = _accept(conv, "ASKA off", "co1"), _accept(conv, "ASKB off", "co2")
    k0 = dict(turnrun.STATS)
    seen = []

    async def both():
        ta = asyncio.ensure_future(_owned(conv, ra, "ASKA off"))
        await asyncio.sleep(0.1)
        seen.append((turnrun.busy(conv), turnrun.live_run(conv), santosh._locks[conv].locked()))
        tb = asyncio.ensure_future(_owned(conv, rb, "ASKB off"))
        return await asyncio.gather(ta, tb)
    assert asyncio.run(asyncio.wait_for(both(), 60)) == ["answer A", "answer B"]
    assert seen == [(False, None, True)]
    assert dict(turnrun.STATS) == k0
    assert turnrun.stop(conv) is False and turnrun.stopped(conv) is False
    assert _status(ra) == _status(rb) == "done"


# 4c. her stop WORDS (kaamstop.cancel, in a worker thread, before the lock) stop the live run the same way
def test_stop_words_stop_the_live_run(bz, monkeypatch):  # noqa: F811
    from app.agent import toolledger as L, turngraph
    conv = _new_conv()
    brain = Brain({"ASKA": [[tu(1, "email_send", to="ravi@x.in")], txt("should not run")]}, conv=conv)
    tools = Tools(slow={"email_send": 8})
    _setup(monkeypatch, True, brain, tools)
    ra, rb = _accept(conv, "ASKA mail", "cw1"), _accept(conv, "kaam roko", "cw2")

    async def both():
        ta = asyncio.ensure_future(_owned(conv, ra, "ASKA mail"))
        while not tools.count:                               # her send is running now
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.1)
        tb = asyncio.ensure_future(_owned(conv, rb, "kaam roko"))
        return await asyncio.gather(ta, tb)
    t0 = time.monotonic()
    out_a, out_b = asyncio.run(asyncio.wait_for(both(), 60))
    assert time.monotonic() - t0 < 4
    assert out_a.startswith(HALT) and MIDWAY in out_a
    assert out_b.startswith("Okay, stopped")                 # the kaamstop line (the canned path in this suite)
    assert tools.cancelled == ["email_send"] and brain.calls == 1
    assert _status(ra) == "stopped"
    assert [x["state"] for x in L.rows(turngraph.thread_id(conv, ra))] == ["failed"]
