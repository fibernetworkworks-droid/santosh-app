"""v0.999.115 ULTIMATE PC PLAN P5 - learn once, replay: a finished job's step record becomes a routine (elements by
role + name, her own words as blanks); the replay runs those steps with NO AI on a real page; when the page changed the
AI takes over from that step (self-heal note)."""
from __future__ import annotations

import asyncio
import json
import types

import pytest

from app.pc import routines as R
from app.pc import trace
from app.pc import operator as O
from tests.test_v0999_93_ultimate_p1 import chrome_page  # noqa: F401


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("PC_TRACE_DIR", str(tmp_path / "trace"))
    monkeypatch.setenv("PC_ROUTINES_DIR", str(tmp_path / "routines"))
    return tmp_path


def _record(task, steps, status="done", conv="c1", kind="her_pc"):
    op = types.SimpleNamespace(id="pcop_rec1", tenant="t1", conv=conv, task=task, kind=kind, device_id="d1", step=0,
                               action="", window="", frame=None, thought="", thought_fresh=False, brain="q", status="running",
                               summary="", reason="", elems={})
    trace.start(op)
    for tool, args, elems in steps:
        op.step += 1
        op.elems = elems
        trace.step(op, tool, args)
    op.status = status
    trace.finish(op)
    return op.id


def test_a_good_job_becomes_a_routine_with_blanks(dirs):
    job = _record("Subscribe ops@example.org to the newsletter on the practice site", [
        ("open_url", {"url": "https://p/shadow"}, {}),
        ("page_elements", {}, {}),
        ("page_type", {"ref": 2, "text": "ops@example.org"}, {2: "input 'Work email'"}),
        ("screenshot", {}, {}),
        ("page_click", {"ref": 3}, {3: "button 'Subscribe'"}),
        ("click", {"x": 4, "y": 5}, {})])
    r = R.from_job("t1", job, "Newsletter signup")
    assert [s["tool"] for s in r["steps"]] == ["open_url", "page_type", "page_click"]
    assert r["steps"][1] == {"tool": "page_type", "target": ["input", "Work email"], "blank": "Work email"}
    assert r["blanks"] == [{"name": "Work email", "default": "ops@example.org"}] and r["pixel_steps_left_to_ai"] == 1
    assert R.find("t1", "newsletter")["id"] == r["id"] and R.listing("t1")[0]["steps"] == 3
    assert R.last_done_job("t1", "c1", "") == job
    bad = _record("x", [("page_click", {"ref": 1}, {1: "button 'Go'"})], status="partial")
    with pytest.raises(ValueError, match="finished well"):
        R.from_job("t1", bad)


class _Hub:
    """The PC answers page actions from the real Hoola PC agent (real Chromium); a screen is a tiny picture."""

    def __init__(self, act):
        self.act = act

    async def call(self, tenant, action, args=None, **kw):
        a = dict(args or {})
        if action in ("screen", "screenshot"):
            return {"image": "", "width": 10, "height": 10, "active_window": "Practice", "windows": []}
        if action == "open_url":
            await asyncio.to_thread(self.act.open_, a["url"])
            return {"ok": True, "title": "", "url": a["url"]}
        fn = getattr(self.act.a, "do_" + action)
        return await asyncio.to_thread(fn, **a)


def test_replay_runs_on_a_real_page_without_ai_and_heals_from_the_step_that_changed(chrome_page, dirs, monkeypatch):
    act, open_, ref, recs = chrome_page
    from app.pc import hands
    from app.pc.hub import hub

    async def go_gate(op, name, a):
        return None
    monkeypatch.setattr(hands, "gate", go_gate)
    holder = types.SimpleNamespace(a=act, open_=open_)
    h = _Hub(holder)
    monkeypatch.setattr(hub, "call", h.call)
    base = "https://ignored"   # open_ below navigates by page name

    def opener(url):
        open_(url.rsplit("/", 1)[-1])
    holder.open_ = opener
    job = _record("Subscribe ops@example.org on the practice site", [
        ("open_url", {"url": base + "/shadow"}, {}),
        ("page_type", {"ref": 2, "text": "ops@example.org"}, {2: "input 'Work email'"}),
        ("page_click", {"ref": 3}, {3: "button 'Subscribe'"})])
    r = R.from_job("t1", job, "Newsletter")
    op = O.Op(id="pcop_play", tenant="t1", conv="c1", task="replay", device_id="d1")
    op.replay = {**r, "values": {"Work email": "team@example.org"}}
    ok, n, note = asyncio.run(R.play(op))
    assert ok, note
    assert n == 3 and recs()["shadow"]["email"] == "team@example.org"            # the blank took her new value
    assert [t["do"] for t in op.timeline] == ["open_url", "page_type", "page_click"] and all(t.get("replay") for t in op.timeline)
    assert R.get("t1", r["id"])["runs"] == 1
    # the site changed: the button is called something else now -> the AI takes over from step 3, with the work so far
    r2 = json.loads(json.dumps(r))
    r2["steps"][2]["target"] = ["button", "Join the list"]
    op2 = O.Op(id="pcop_heal", tenant="t1", conv="c1", task="replay", device_id="d1")
    op2.replay = {**r2, "values": {}}
    ok, n, note = asyncio.run(R.play(op2))
    assert not ok and n == 2 and "step 3 (page_click) did not fit the page" in note and "Join the list" in note
    assert "never redo the steps done" in note and R.get("t1", r["id"])["healed"] == 1


def test_chat_tools_save_and_replay(dirs, monkeypatch):
    from app.agent import pc_tools as T
    from app.agent.tools import Ctx
    job = _record("Subscribe ops@example.org", [("page_type", {"ref": 2, "text": "ops@example.org"}, {2: "input 'Work email'"})])
    out = asyncio.run(T.pc_do(Ctx("t1", "c1"), "save", save_as_routine="My signup"))
    assert out["saved_routine"] == "My signup" and out["blanks"] == ["Work email"]
    seen = {}

    async def start(tenant, conv, task, **k):
        seen.update(k, task=task)
        return {"session_id": "pcop_x", "status": "running"}
    monkeypatch.setattr(O, "start", start)
    out = asyncio.run(T.pc_do(Ctx("t1", "c1"), "run it", routine="signup", values={"Work email": "a@b.co"}))
    assert seen["replay"]["values"] == {"Work email": "a@b.co"} and "Replaying the routine 'My signup'" in out["say"]
    with pytest.raises(Exception, match="No routine called"):
        asyncio.run(T.hoola_pc_do(Ctx("t1", "c1"), "x", routine="nothing like it"))
    assert job


def test_routes(env, dirs):
    from fastapi.testclient import TestClient
    from app.main import app
    job = _record("Subscribe ops@example.org", [("page_type", {"ref": 2, "text": "ops@example.org"}, {2: "input 'Work email'"})],
                  conv="")
    import app.pc.trace as T
    meta = T.read("t1", job)
    c = TestClient(app)
    # the default test tenant is 'default': record one for it too
    job2 = _record("Type hello into Notes", [("page_type", {"ref": 1, "text": "hello"}, {1: "textbox 'Notes'"})])
    import shutil
    shutil.copytree(dirs / "trace" / "t1" / job2, dirs / "trace" / "default" / job2)
    r = c.post(f"/api/pc/routines/from-job/{job2}", json={"name": "Notes"})
    assert r.status_code == 200 and r.json()["blanks"][0]["name"] == "Notes"
    assert c.get("/api/pc/routines").json()["routines"][0]["name"] == "Notes"
    rid = r.json()["id"]
    assert c.delete(f"/api/pc/routines/{rid}").json()["deleted"] is True
    assert meta and c.post("/api/pc/routines/from-job/pcop_none").status_code == 409
