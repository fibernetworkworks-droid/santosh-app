"""v0.999.36 HER HANDS ON THE PC (owner: "Do 2 to 7" after the research on OpenAI Dots, Grok Bot and Claude):
2 take control of the Hoola PC screen and give it back, 3 a private sign-in form the model never sees, 4 a connected app
before the screen, 5 her own Hoola PC kept across restarts, 6 her second job never throws away her first,
7 an independent check of risky steps against HER words only."""
import asyncio
import json
import time
import types

import pytest
from fastapi.testclient import TestClient

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0193_hoola_pc import FakePC, Scripted, _wire, tu
from tests.test_v0885_hoola_pc_pool import KIND, pool_hub  # noqa: F401


@pytest.fixture
def fresh_home(bz, monkeypatch):  # noqa: F811
    from app.pc import pool
    pool.HOME.clear()
    monkeypatch.setattr(pool, "_HOME_LOADED", True)
    yield pool
    pool.HOME.clear()


def _op(**kw):
    from app.pc import operator
    base = dict(id="pcop_h1", tenant="owner", conv="c1", task="GST portal par mera return file karo", kind=KIND,
                device_id="hp1")
    base.update(kw)
    return operator.Op(**base)


# ---------------------------------------------------------------- 2. take control / give it back
@pytest.mark.asyncio
async def test_takeover_holds_the_task_and_her_input_reaches_the_pc(monkeypatch):
    from app.pc import hands, operator
    operator._loop = asyncio.get_running_loop()
    sent = []

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        sent.append((action, dict(args or {}), log))
        return {"ok": True}

    async def fake_shot(op, monitor=""):
        op.frame_seq += 1
        return []
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "_shot", fake_shot)
    op = _op()
    with pytest.raises(ValueError):
        await hands.act(op, "click", 10, 20)                 # nothing reaches the PC before she takes control
    hands.take(op, True)
    assert op.takeover and op.live()["takeover"] is True
    waiting = asyncio.create_task(hands.hold(op))
    await asyncio.sleep(0.05)
    assert not waiting.done()                                # the task loop waits while she has the screen
    await hands.act(op, "click", 10.6, 20.2)
    await hands.act(op, "type", text="secret-ish words")
    await hands.act(op, "key", keys="backspace")
    await hands.act(op, "key", keys="ctrl+a")
    with pytest.raises(ValueError):
        await hands.act(op, "key", keys="super+r")           # no Win / Run keys
    assert sent[0] == ("control", {"op": "click", "x": 10, "y": 20}, False)
    assert sent[1][1] == {"op": "type", "text": "secret-ish words"} and sent[1][2] is False   # never logged
    assert sent[2][1]["keys"] == "BackSpace" and sent[3][1]["keys"] == "ctrl+a"
    hands.take(op, False)
    assert await asyncio.wait_for(waiting, 2) >= 0
    assert not op.takeover and "given it back" in op.notes[-1] and "secret-ish" not in op.notes[-1]


def test_take_control_is_only_for_hoola_pc():
    from app.pc import hands
    with pytest.raises(ValueError):
        hands.take(_op(kind=""), True)


@pytest.mark.asyncio
async def test_actions_of_the_model_are_held_while_she_has_the_screen(pool_hub, fresh_home, monkeypatch):  # noqa: F811
    from app.pc import operator
    pc = FakePC(expect_kind=KIND)
    monkeypatch.setattr(pool_hub, "call", pc.call)
    _wire(monkeypatch, Scripted([tu(1, "click", x=5, y=5), tu(2, "done", answer="ho gaya")]))
    real_think = None
    from app.pc import brain

    real_think = brain.think

    turns = []

    async def think(op, client, messages, params, retry):
        turns.append(1)
        if len(turns) > 1:
            return await real_think(op, client, messages, params, retry)
        op.takeover = True                                 # she pressed Take control while the model was thinking
        op.takeover_back = asyncio.Event()
        try:
            return await real_think(op, client, messages, params, retry)
        finally:
            asyncio.get_running_loop().call_later(0.1, lambda: (setattr(op, "takeover", False), op.takeover_back.set()))
    monkeypatch.setattr(brain, "think", think)
    r = await operator.start("owner", "c1", "kuch karo", wait=20, kind=KIND)
    assert r["status"] == "done"
    assert not [c for c in pc.calls if c[0] == "control"]  # the model's click never ran over her hands


# ---------------------------------------------------------------- 3. the private sign-in form
@pytest.mark.asyncio
async def test_sign_in_is_typed_by_the_system_and_never_seen(pool_hub, fresh_home, monkeypatch):  # noqa: F811
    from app.pc import hands, operator
    pc = FakePC(expect_kind=KIND)
    monkeypatch.setattr(pool_hub, "call", pc.call)
    claude = Scripted([tu(1, "ask_login", site="GST portal"), tu(2, "done", answer="signed in")])
    _wire(monkeypatch, claude)
    r = await operator.start("owner", "c1", "GST portal par login karke return dekho", wait=0, kind=KIND)
    op = operator.get("owner", r["session_id"])
    for _ in range(200):
        if op.login:
            break
        await asyncio.sleep(0.02)
    lg = op.live()["login"]
    assert lg["site"] == "GST portal" and lg["fields"] == "username_password"
    assert not hands.give_login(op, "wrong-id", "u", "p")
    assert hands.give_login(op, lg["id"], "meghana@gst", "Pa55-W0rd!")
    await asyncio.wait_for(op.done_event.wait(), 10)
    types_ = [c[1] for c in pc.calls if c[0] == "control"]
    assert types_ == [{"op": "type", "text": "meghana@gst"}, {"op": "key", "keys": "Tab"},
                      {"op": "type", "text": "Pa55-W0rd!"}]
    seen = json.dumps([kw.get("messages") for kw in claude.seen], default=str)
    assert "Pa55-W0rd!" not in seen and "meghana@gst" not in seen    # the model never had them
    assert op.login is None and "Pa55" not in json.dumps(op.live(), default=str)
    assert "ask_login" in {t["name"] for t in operator.TOOLS} | {t["name"] for t in operator.HOOLA_TOOLS}


def test_sign_in_route_never_keeps_the_password(env):
    from app.main import app
    c = TestClient(app)
    assert c.post("/api/computer/task/pcop_none/login", json={"id": "x", "password": "p"}).status_code == 404
    assert c.post("/api/computer/task/pcop_none/takeover", json={"on": True}).status_code == 404
    from app.computer import LoginIn
    assert "p4ss" not in repr(LoginIn(id="a", password="p4ss")) and "p4ss" not in str(LoginIn(id="a", password="p4ss"))


# ---------------------------------------------------------------- 7. the independent action checker
@pytest.mark.asyncio
async def test_checker_reads_only_her_words(monkeypatch):
    from app.pc import hands, operator
    asked = []

    async def judge(model, system, content, max_tokens=700, timeout=25):
        asked.append(content[0]["text"])
        return verdicts.pop(0)
    monkeypatch.setattr(operator, "_claude_json", judge)
    op = _op()
    op.heard = ["haan submit kar do"]
    op.elems = {5: "button 'Submit application'", 6: "link 'Next page'", 7: "button 'Pay Rs 500 fee'"}
    verdicts = [{"verdict": "allow", "why": "she asked to submit"}]
    assert await hands.check(op, "page_click", {"ref": 5}) == ("go", "she asked to submit")
    assert "haan submit kar do" in asked[0] and "Submit application" in asked[0]
    assert await hands.check(op, "page_click", {"ref": 6}) == ("go", "")          # nothing risky: no check at all
    assert len(asked) == 1
    v, why = await hands.check(op, "page_click", {"ref": 7})
    assert v == "ask" and "money" in why and len(asked) == 1                     # money always asks her
    verdicts = [{"verdict": "block", "why": "she never asked to delete"}]
    op.elems[8] = "button 'Delete account'"
    out = await hands.gate(op, "page_click", {"ref": 8})
    assert out.startswith("NOT RUN") and "never asked" in out
    op.step, op.ok_step = 10, 9                                                   # she approved it a step ago
    assert (await hands.check(op, "page_click", {"ref": 5}))[0] == "go"
    op.ok_step = 0
    op.batch_ok = True
    assert (await hands.check(op, "page_click", {"ref": 5}))[0] == "go"           # her repeat job after row 1
    op.batch_ok = False

    async def broken(*a, **k):
        raise RuntimeError("no model")
    monkeypatch.setattr(operator, "_claude_json", broken)
    assert (await hands.check(op, "page_click", {"ref": 5}))[0] == "ask"          # a checker that cannot run asks her


@pytest.mark.asyncio
async def test_checker_ask_goes_to_her_card_and_is_remembered(monkeypatch):
    from app.pc import hands, operator

    async def judge(*a, **k):
        return {"verdict": "ask", "why": "not clearly asked"}

    async def approve(op, what):
        approve.what = what
        return True
    monkeypatch.setattr(operator, "_claude_json", judge)
    monkeypatch.setattr(operator, "_approval", approve)
    op = _op(step=4)
    op.elems = {3: "button 'Send message'"}
    assert await hands.gate(op, "page_click", {"ref": 3}) is None and op.ok_step == 4
    assert "Send message" in approve.what
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "pc_action_check", False)
    assert (await hands.check(op, "page_click", {"ref": 3}))[0] == "go"


def test_page_elements_are_remembered_for_the_checker():
    from app.pc import hands
    op = _op()
    hands.remember_elements(op, [{"ref": 2, "role": "button", "name": "Submit"}, {"ref": "x"}])
    assert op.elems == {2: "button 'Submit'"}


# ---------------------------------------------------------------- 5. her own Hoola PC
def test_her_home_pc_is_kept_and_survives_a_restart(pool_hub, fresh_home):  # noqa: F811
    from app.pc import operator, pool
    pool.remember("her", "hp2")
    assert pool.HOME["her"] == "hp2" and pool._home_file().exists()
    pool.HOME.clear()
    pool._HOME_LOADED = False                       # a server restart
    assert pool.home_of("her") == "hp2"
    assert pool.pick("her").device_id == "hp2"
    fut = asyncio.get_event_loop_policy().new_event_loop().create_future()
    busy = operator.Op(id="pcop_b", tenant="someone", conv="x", task="t", kind=KIND, device_id="hp2")
    busy.task_obj = fut
    operator.OPS[busy.id] = busy
    try:
        assert pool.pick("her", since=time.time()) is None                 # she waits a little for her own PC
        assert pool.pick("her", since=time.time() - 300).device_id == "hp1"   # then another free one
        assert pool.pick("her").device_id == "hp1"
        assert pool.status("her")["home"] == "hp2"
    finally:
        operator.OPS.pop(busy.id, None)


def test_a_new_user_gets_the_pc_fewest_call_home(pool_hub, fresh_home):  # noqa: F811
    from app.pc import pool
    pool.HOME.update({"a": "hp1", "b": "hp1"})
    assert pool.pick("new").device_id == "hp2"


# ---------------------------------------------------------------- 6. her second job never throws away her first
@pytest.mark.asyncio
async def test_her_second_job_runs_beside_the_first_or_waits(pool_hub, fresh_home, monkeypatch):  # noqa: F811
    from app.pc import operator
    hold = asyncio.Event()

    async def slow(o):
        await hold.wait()
        o.status = "done"
        o.done_event.set()
    monkeypatch.setattr(operator, "_run", slow)
    first = await operator.start("owner", "c1", "Aadhaar download", wait=0, kind=KIND)
    second = await operator.start("owner", "c2", "GST return status dekho", wait=0, kind=KIND)
    a, b = operator.get("owner", first["session_id"]), operator.get("owner", second["session_id"])
    assert a.status == b.status == "running" and a.device_id != b.device_id     # two screens, two jobs at once
    third = await operator.start("owner", "c3", "IRCTC ticket status", wait=0, kind=KIND)
    assert third["status"] == "queued" and "other Hoola PC job" in third["say"]
    assert a.status == "running" and b.status == "running"                     # nothing of hers was thrown away
    hold.set()
    c = operator.get("owner", third["session_id"])
    await asyncio.wait_for(c.done_event.wait(), 10)
    assert c.status == "done"


def test_status_lists_her_other_running_jobs(env, monkeypatch):
    from app import computer
    from app.pc import operator
    loop = asyncio.new_event_loop()
    try:
        for i, t in enumerate(("Aadhaar download", "GST status")):
            o = operator.Op(id=f"pcop_s{i}", tenant="default", conv="c", task=t, kind=KIND, device_id=f"hp{i}",
                            created=time.time() + i)
            o.task_obj = loop.create_future()
            operator.OPS[o.id] = o
        run = computer._running("default", "hoola")
        assert run["task"] == "GST status" and run["others"][0]["task"] == "Aadhaar download"
        assert run["takeover"] is False
    finally:
        operator.OPS.pop("pcop_s0", None)
        operator.OPS.pop("pcop_s1", None)
        loop.close()


# ---------------------------------------------------------------- 4. a connected app before the screen
def test_connected_app_first_then_her_wish_stands(bz, monkeypatch):  # noqa: F811
    from app import google_auth
    from app.agent import pick
    from app.agent.tools import ToolError
    pick._NUDGED.clear()
    ctx = types.SimpleNamespace(tenant_id="owner", conversation_id="cx1", place="hoolapc", admit=None)
    args = {"task": "open gmail on the Hoola PC and read my latest email from the bank"}
    monkeypatch.setattr(google_auth, "has_google", lambda t: False)
    assert pick._connected_way(args["task"], "owner") == ""                     # nothing connected: no nudge
    monkeypatch.setattr(google_auth, "has_google", lambda t: True)
    with pytest.raises(ToolError) as e:
        pick._connector_first("hoola_pc_do", args["task"], ctx)
    assert "email_read" in str(e.value) and "again" in str(e.value)
    pick._connector_first("hoola_pc_do", args["task"], ctx)                     # asked again: it runs
    assert "email_" not in pick._connected_way("GST portal par return file karo", "owner")


def test_order_rules_reach_the_pc_worker_and_the_manager():
    from app.agent import pc_manager
    from app.pc import hands
    assert "CONNECTED APP first" in pc_manager.RULES and "never ask her for a password" in pc_manager.RULES.lower()
    assert "page_elements" in hands.ORDER and "ask_login" in hands.ORDER and "Take control" in hands.ORDER


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION >= "0.999.36"
