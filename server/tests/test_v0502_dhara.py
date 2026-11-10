"""v0.510.0 DHARA - her workflows (the n8n idea, house-sized, end to end).

Owner: "DEVLOPE A N8N CLONE FOR HOOLA AI END TO END" (after the full READ of n8n v2.47.0; zero n8n
code - the fair-code license keeps it out of this tree, the idea is rebuilt on house rails).

What is tested FOR REAL (all offline): the graph validator (types, ids, caps, nesting, denylist,
expressions), the safe expression resolver (typed dig, mixed text, injection-refusing paths), the
engine (sequential steps, condition then/else, loop + {{item}} + cap, set, notify cap, tool steps on
the REAL registry with actor="routine", approval park -> her haan -> resume PAST the gate, stop
between steps, soft vs fail-fast errors, wall-clock cap), the checkpoint (cursor + context + log
written per step, resume after a simulated death runs no step twice), the tick (scheduled enqueue +
missed-once, sleeper wake, approval expiry, tries exhausted = failed honestly, keep-runs forget),
the webhook (202 + {{vars.body}}, bad token 401, throttle 429, disabled 401, kill switch 503), the
tools' shapes (save/update honesty, list board, runs pagination), tenant isolation, mask_ids, the
registry pin (542, the magic21 tool rode in v0.512) and the version pin.
"""
import asyncio
import hashlib
import json
import shutil
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

from app.agent import dhara_tools as D
from app.agent.tools import Ctx, TOOLS, HANDLERS, TOOL_LABELS, FAMILY_OF

CTX = Ctx(tenant_id="dh-test-tenant", conversation_id="c1")
CTX2 = Ctx(tenant_id="dh-other-tenant", conversation_id="c2")


def _wipe(tenant):
    shutil.rmtree(Path("data") / "dhara" / tenant, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Every test: no politeness sleeps, empty tenant dirs, no in-process tasks."""
    monkeypatch.setattr(D, "polite_s", 0)
    D._RUNNING.clear()
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)
    yield
    D._RUNNING.clear()
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)


def _run(coro):
    return asyncio.run(coro)


def _flow1_steps():
    return [
        {"id": "who", "type": "set", "name": "who", "value": "Malika"},
        {"id": "check", "type": "condition", "left": "{{vars.who}}", "op": "eq", "right": "Malika",
         "then": [{"id": "hi", "type": "set", "name": "msg", "value": "pranam {{vars.who}}"}],
         "else": [{"id": "bye", "type": "set", "name": "msg", "value": "alvida"}]},
    ]


# ---------------------------------------------------------------- registry / family

def test_registry_5_dhara_tools():
    names = {t["name"] for t in D.DHARA_TOOLS}
    assert {"dhara_save", "dhara_run", "dhara_runs", "dhara_control", "dhara_list"} <= names
    assert set(D.DHARA_LABELS) == set(D.DHARA_HANDLERS) == names
    global_names = {t["name"] for t in TOOLS}
    assert names <= global_names
    for n in names:
        assert n in HANDLERS and n in TOOL_LABELS, n
    assert len(TOOLS) == 621, "617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " "581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 536 (v0.501, docs7 in) + 5 dhara tools + 1 magic21 (v0.512) + 1 dhara_dsl (their v0.514) + 10 construction (v0.522) + 1 crew_run (v0.523) + 2 from main's v0.533 CRAWL BRAIN wiring (healed in v0.537: red on pristine main) + 1 reach (v0.559 REACH MANCH) + 1 speckit (v0.569 SPEC SUTRA)"


def test_family_map():
    for n in ("dhara_save", "dhara_run", "dhara_runs", "dhara_control", "dhara_list", "dhara_dsl"):
        assert FAMILY_OF.get(n) == "dhara", n


# ---------------------------------------------------------------- dhara_save / validation

def test_save_creates_then_updates_same_id():
    a = _run(D.dhara_save(CTX, name="my flow", steps=_flow1_steps(), description="pehla"))
    assert a["created"] is True and a["name"] == "my_flow" and a["steps"] == 2
    b = _run(D.dhara_save(CTX, name="my_flow", steps=_flow1_steps(), description="badla"))
    assert b["created"] is False and b["workflow_id"] == a["workflow_id"]
    wf = D.get_workflow(CTX.tenant_id, name="my_flow")
    assert wf["description"] == "badla"


def test_save_validation_refuses_garbage():
    with pytest.raises(Exception):  # empty
        _run(D.dhara_save(CTX, name="x1", steps=[]))
    with pytest.raises(Exception):  # unknown type
        _run(D.dhara_save(CTX, name="x2", steps=[{"id": "a", "type": "magic"}]))
    with pytest.raises(Exception):  # dup ids
        _run(D.dhara_save(CTX, name="x3", steps=[{"id": "a", "type": "set", "name": "v", "value": 1},
                                                 {"id": "a", "type": "set", "name": "w", "value": 2}]))
    with pytest.raises(Exception):  # same-turn card tool denied
        _run(D.dhara_save(CTX, name="x4", steps=[{"id": "a", "type": "tool", "name": "ask_form"}]))
    with pytest.raises(Exception):  # bad condition op
        _run(D.dhara_save(CTX, name="x5", steps=[{"id": "a", "type": "condition", "left": "1", "op": "~", "right": "2"}]))
    with pytest.raises(Exception):  # loop without body
        _run(D.dhara_save(CTX, name="x6", steps=[{"id": "a", "type": "loop", "items": "{{vars.x}}"}]))
    with pytest.raises(Exception):  # approval without question
        _run(D.dhara_save(CTX, name="x7", steps=[{"id": "a", "type": "approval"}]))
    with pytest.raises(Exception):  # >40 steps
        _run(D.dhara_save(CTX, name="x8", steps=[{"id": f"s{i}", "type": "set", "name": f"v{i}", "value": 1}
                                                 for i in range(41)]))
    with pytest.raises(Exception):  # oversized expression
        _run(D.dhara_save(CTX, name="x9", steps=[{"id": "a", "type": "set", "name": "v", "value": "x" * 3000}]))
    with pytest.raises(Exception):  # nesting cap: condition inside condition's then
        _run(D.dhara_save(CTX, name="x10", steps=[
            {"id": "a", "type": "condition", "left": "1", "op": "eq", "right": "1",
             "then": [{"id": "b", "type": "condition", "left": "1", "op": "eq", "right": "1",
                       "then": [{"id": "c", "type": "set", "name": "v", "value": 1}]}]}]))
    with pytest.raises(Exception):  # bad step id shape
        _run(D.dhara_save(CTX, name="x11", steps=[{"id": "BAD ID!", "type": "set", "name": "v", "value": 1}]))


def test_save_schedule_trigger_needs_spec_and_webhook_hides_token():
    with pytest.raises(Exception):
        _run(D.dhara_save(CTX, name="s1", steps=_flow1_steps(), trigger="schedule"))
    with pytest.raises(Exception):
        _run(D.dhara_save(CTX, name="s2", steps=_flow1_steps(), trigger="cron"))
    out = _run(D.dhara_save(CTX, name="s3", steps=_flow1_steps(), trigger="webhook"))
    assert "webhook_note" in out and "keep it safe" in out["webhook_note"]
    wf = D.get_workflow(CTX.tenant_id, name="s3")
    assert wf["token_hash"] and len(wf["token_hash"]) == 64  # sha256 hex, never the token itself


def test_save_schedule_sets_next_due():
    out = _run(D.dhara_save(CTX, name="sch", steps=_flow1_steps(), trigger="schedule",
                            trigger_spec={"every_hours": 24, "at": ["09:30"]}))
    wf = D.get_workflow(CTX.tenant_id, name="sch")
    assert wf["next_due_at"] and wf["next_due_at"] > time.time()
    _ = out


# ---------------------------------------------------------------- expressions

def test_expression_resolver_typed_and_mixed():
    ctx = {"vars": {"n": 5, "s": "Haan"}, "steps": {"a": {"output": {"total": 42, "items": ["x", "y"]}}}, "item": None}
    assert D.resolve("{{vars.n}}", ctx) == 5
    assert D.resolve("{{steps.a.output.total}}", ctx) == 42
    assert D.resolve("{{steps.a.output.items.1}}", ctx) == "y"
    assert D.resolve("malika {{vars.s}}?", ctx) == "malika Haan?"
    assert D.resolve("{{vars.nada}}", ctx) is None
    assert D.resolve({"deep": ["{{vars.n}}", "x {{vars.s}}"]}, ctx) == {"deep": [5, "x Haan"]}
    # injection-shaped paths dig to None, never execute
    assert D.resolve("{{__import__os}}", ctx) is None
    assert D.resolve("{{vars.n.__class__}}", ctx) is None
    assert D._cmp("Haan", "eq", "Haan") and not D._cmp("Nahi", "eq", "Haan")
    assert D._cmp(10, "gt", 9) and D._cmp(9, "lt", 10)
    assert D._cmp("Google notice", "contains", "notice")
    assert D._cmp(None, "empty", "") and not D._cmp("x", "empty", "")


# ---------------------------------------------------------------- engine

def test_run_full_flow_done_with_checkpoint():
    _run(D.dhara_save(CTX, name="flow", steps=_flow1_steps()))
    r = _run(D.dhara_run(CTX, name="flow", vars={"who": "Malika"}))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done" and run["cursor"] == 2
    assert run["context"]["vars"]["msg"] == "pranam Malika"
    assert [(s["id"], s["status"]) for s in run["steps_log"]] == [("who", "ok"), ("check", "ok")]
    assert all("ms" in s for s in run["steps_log"])


def test_run_condition_else_branch():
    steps = [{"id": "check", "type": "condition", "left": "{{vars.who}}", "op": "eq", "right": "Malika",
              "then": [{"id": "hi", "type": "set", "name": "msg", "value": "pranam"}],
              "else": [{"id": "bye", "type": "set", "name": "msg", "value": "alvida"}]}]
    _run(D.dhara_save(CTX, name="flow2", steps=steps))
    r = _run(D.dhara_run(CTX, name="flow2", vars={"who": "Koi Aur"}))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["context"]["vars"]["msg"] == "alvida"


def test_run_loop_with_item_and_output():
    steps = [
        {"id": "prep", "type": "set", "name": "items", "value": [1, 2, 3]},
        {"id": "lp", "type": "loop", "items": "{{vars.items}}",
         "body": [{"id": "touch", "type": "set", "name": "last", "value": "{{item}}"}]},
        {"id": "out", "type": "set", "name": "n", "value": "{{steps.lp.output.iterations}}"},
    ]
    _run(D.dhara_save(CTX, name="looper", steps=steps))
    r = _run(D.dhara_run(CTX, name="looper"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done"
    assert run["context"]["vars"]["n"] == 3 and run["context"]["vars"]["last"] == 3


def test_run_tool_step_rides_real_registry_as_routine():
    _run(D.dhara_save(CTX, name="board", steps=[{"id": "ls", "type": "tool", "name": "dhara_list"}]))
    r = _run(D.dhara_run(CTX, name="board"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done"
    assert run["context"]["steps"]["ls"]["output"]["count"] >= 1


def test_run_unknown_tool_fails_honestly():
    _run(D.dhara_save(CTX, name="bad", steps=[{"id": "t", "type": "tool", "name": "no_such_tool"}]))
    r = _run(D.dhara_run(CTX, name="bad"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "failed" and "not in the registry" in run["error"]
    assert run["steps_log"][-1]["status"] == "error"


def test_run_soft_step_continues_failfast_stops():
    steps = [
        {"id": "ok1", "type": "set", "name": "a", "value": "1"},
        {"id": "bad", "type": "tool", "name": "no_such_tool", "soft": True},
        {"id": "ok2", "type": "set", "name": "b", "value": "2"},
    ]
    _run(D.dhara_save(CTX, name="softy", steps=steps))
    r = _run(D.dhara_run(CTX, name="softy"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done" and run["context"]["vars"]["b"] == "2"
    assert any(s["status"] == "error" for s in run["steps_log"])
    # fail-fast: the same bad step without soft stops the run at it
    steps[1].pop("soft")
    _run(D.dhara_save(CTX, name="hardy", steps=steps))
    r2 = _run(D.dhara_run(CTX, name="hardy"))
    _run(D.drain())
    run2 = D.get_run(CTX.tenant_id, r2["run_id"])
    assert run2["status"] == "failed" and run2["context"]["vars"].get("b") is None


class _NS:
    """A settings stand-in: the lane reads every knob with getattr(s, name, default)."""
    def __init__(self, **kw):
        self.dhara_enabled = True
        self.dhara_max_steps = 40
        self.dhara_loop_max = 50
        self.dhara_run_timeout_s = 600
        self.dhara_max_running = 1
        self.dhara_stale_s = 180
        self.dhara_tries = 3
        self.dhara_keep_runs_days = 30
        self.dhara_approval_hours = 24
        self.dhara_webhook_enabled = True
        for k, v in kw.items():
            setattr(self, k, v)


def _patch_settings(monkeypatch, **kw):
    import app.config as cfg
    monkeypatch.setattr(cfg, "get_settings", lambda: _NS(**kw))


def test_run_wall_clock_cap(monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    _patch_settings(monkeypatch, dhara_run_timeout_s=0)
    _run(D.dhara_save(CTX, name="slow", steps=[{"id": "a", "type": "wait", "duration_s": 2}]))
    r = _run(D.dhara_run(CTX, name="slow"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "failed" and "wall-clock" in run["error"]


def test_approval_parks_then_her_haan_resumes_past_the_gate():
    _run(D.dhara_save(CTX, name="gate", steps=[
        {"id": "gate", "type": "approval", "question": "bhej dun?"},
        {"id": "after", "type": "set", "name": "flag", "value": "haan-mil-gaya"}]))
    r = _run(D.dhara_run(CTX, name="gate"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "waiting_approval" and run["cursor"] == 0
    assert run["steps_log"][-1]["status"] == "waiting_approval"
    # approve moves the cursor PAST the gate (else the resumed run parks forever - the bug the suite caught)
    out = _run(D.dhara_control(CTX, action="approve", run_id=r["run_id"]))
    assert out["status"] == "queued"
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done" and run["context"]["vars"]["flag"] == "haan-mil-gaya"
    assert any(s["status"] == "approved" for s in run["steps_log"])


def test_approval_approve_on_non_waiting_is_honest():
    _run(D.dhara_save(CTX, name="plain", steps=[{"id": "a", "type": "set", "name": "v", "value": "1"}]))
    r = _run(D.dhara_run(CTX, name="plain"))
    _run(D.drain())
    out = _run(D.dhara_control(CTX, action="approve", run_id=r["run_id"]))
    assert "not waiting" in out["note"]


def test_stop_between_steps_keeps_finished_log():
    steps = [{"id": "first", "type": "set", "name": "v1", "value": 1},
             {"id": "w", "type": "wait", "duration_s": 3600},
             {"id": "never", "type": "set", "name": "v3", "value": 3}]
    _run(D.dhara_save(CTX, name="stoppable", steps=steps))
    r = _run(D.dhara_run(CTX, name="stoppable"))
    _run(D.drain())
    parked = D.get_run(CTX.tenant_id, r["run_id"])
    assert parked["status"] == "sleeping" and parked["cursor"] == 2
    out = _run(D.dhara_control(CTX, action="stop", run_id=r["run_id"]))
    assert out["status"] == "stopped"
    again = _run(D.dhara_control(CTX, action="stop", run_id=r["run_id"]))
    assert "already stopped" in again["note"]
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "stopped" and len(run["steps_log"]) == 2
    assert "never" not in [s["id"] for s in run["steps_log"]]


def test_wait_parks_then_tick_wakes():
    _run(D.dhara_save(CTX, name="waiter", steps=[
        {"id": "w", "type": "wait", "duration_s": 3600},
        {"id": "after", "type": "set", "name": "done_flag", "value": "jaag gaya"}]))
    r = _run(D.dhara_run(CTX, name="waiter"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "sleeping" and run["next_wake_at"] and run["next_wake_at"] > time.time()
    assert run["cursor"] == 1, "the wait step itself is checkpointed as done"
    # the wake: next_wake_at passes, the tick parks it back to queued and claims it
    D.update_run(CTX.tenant_id, r["run_id"], next_wake_at=time.time() - 1)
    n = _run(D.tick())
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done" and run["context"]["vars"]["done_flag"] == "jaag gaya"
    _ = n


def test_notify_cap():
    steps = [{"id": f"n{i}", "type": "notify", "text": f"line {i}"} for i in range(7)]
    _run(D.dhara_save(CTX, name="spammer", steps=steps))
    r = _run(D.dhara_run(CTX, name="spammer"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done"
    sent = [s for s in run["steps_log"] if s.get("output") == '{"sent": true}']
    skipped = [s for s in run["steps_log"] if "cap" in str(s.get("output", ""))]
    assert len(sent) == D._NOTIFY_MAX and len(skipped) == 7 - D._NOTIFY_MAX


# ---------------------------------------------------------------- the checkpoint: death + resume

def test_checkpoint_resume_runs_no_step_twice(monkeypatch):
    """A run dies between steps (the process is 'killed'); the next tick resumes FROM THE CHECKPOINT."""
    calls = []
    real_exec = D._exec_one

    async def killing_exec(tenant, conv, step, ctx, run_id):
        calls.append(step["id"])
        if step["id"] == "boom":  # the process dies right after this step's side effect
            raise RuntimeError("pm2 restart in the middle")
        return await real_exec(tenant, conv, step, ctx, run_id)

    monkeypatch.setattr(D, "_exec_one", killing_exec)
    steps = [{"id": "a", "type": "set", "name": "a", "value": 1},
             {"id": "boom", "type": "set", "name": "b", "value": 2},
             {"id": "c", "type": "set", "name": "c", "value": 3}]
    _run(D.dhara_save(CTX, name="resume", steps=steps))
    r = _run(D.dhara_run(CTX, name="resume"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "failed" and run["cursor"] == 1  # steps a done, boom's raise caught
    assert calls.count("a") == 1
    # the tick resumes it from the checkpoint: 'a' must NOT run again
    calls.clear()

    async def counting_exec(tenant, conv, step, ctx_, run_id_):
        calls.append(step["id"])
        return await real_exec(tenant, conv, step, ctx_, run_id_)

    monkeypatch.setattr(D, "_exec_one", counting_exec)
    D.update_run(CTX.tenant_id, r["run_id"], status="queued", tries=0)
    _run(D.tick())
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done" and run["context"]["vars"]["c"] == 3
    assert "a" not in calls and calls.count("boom") == 1, "a finished step never runs twice"


# ---------------------------------------------------------------- tick: schedules, tries, expiry, forget

def _set_due(tenant, name, due_ts):
    con = D._con(tenant)
    con.execute("UPDATE workflows SET next_due_at = ? WHERE name = ?", (due_ts, name))
    con.commit()
    con.close()


def test_tick_fires_due_schedule_once_and_advances(monkeypatch):
    _run(D.dhara_save(CTX, name="morning", steps=[{"id": "a", "type": "set", "name": "v", "value": "subah"}],
                      trigger="schedule", trigger_spec={"every_hours": 24, "at": ["09:30"]}))
    _set_due(CTX.tenant_id, "morning", time.time() - 10)
    n = _run(D.tick())
    _run(D.drain())
    assert n >= 1
    runs = D.list_runs(CTX.tenant_id, limit=5)
    assert len(runs) == 1 and runs[0]["status"] == "done"
    wf = D.get_workflow(CTX.tenant_id, name="morning")
    assert wf["next_due_at"] > time.time(), "next_due advanced: no burst"
    # a second tick right away fires nothing
    n2 = _run(D.tick())
    assert n2 == 0


def test_tick_missed_schedule_flags_missed():
    _run(D.dhara_save(CTX, name="late", steps=[{"id": "a", "type": "set", "name": "v", "value": "x"}],
                      trigger="schedule", trigger_spec={"every_hours": 24, "at": ["09:30"]}))
    _set_due(CTX.tenant_id, "late", time.time() - 7200)  # >1h late: missed
    _run(D.tick())
    _run(D.drain())
    runs = D.list_runs(CTX.tenant_id, limit=5)
    assert runs[0]["missed"] is True


def test_next_due_ist_math():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    ist = ZoneInfo("Asia/Kolkata")
    wf = {"trigger_spec": {"every_hours": 24, "at": ["09:30"]}}
    # 2026-11-04 10:00 IST -> next 09:30 is tomorrow
    base = datetime(2026, 11, 4, 10, 0, tzinfo=ist).timestamp()
    nxt = D.next_due(wf, from_ts=base)
    nd = datetime.fromtimestamp(nxt, ist)
    assert (nd.day, nd.hour, nd.minute) == (5, 9, 30)
    # 08:00 -> today 09:30
    base2 = datetime(2026, 11, 4, 8, 0, tzinfo=ist).timestamp()
    nd2 = datetime.fromtimestamp(D.next_due(wf, from_ts=base2), ist)
    assert (nd2.day, nd2.hour) == (4, 9)
    # no 'at': every_hours from now
    wf2 = {"trigger_spec": {"every_hours": 3}}
    assert abs(D.next_due(wf2, from_ts=base) - (base + 3 * 3600)) < 1


def test_tick_tries_exhausted_fails_honestly(monkeypatch):
    _run(D.dhara_save(CTX, name="cursed", steps=[{"id": "a", "type": "set", "name": "v", "value": 1}]))
    r = _run(D.dhara_run(CTX, name="cursed"))
    # exhaust tries WITHOUT ever executing
    D.update_run(CTX.tenant_id, r["run_id"], tries=99, status="queued")
    # the claim refuses; the tick's sweep fails it honestly
    assert D._claim(CTX.tenant_id, r["run_id"], 3) is False
    monkeypatch.setattr(D, "_claimants", lambda t, s: [])
    _run(D.tick())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "failed" and "tries" in run["error"]


def test_tick_expires_stale_approvals(monkeypatch):
    _run(D.dhara_save(CTX, name="gate2", steps=[{"id": "g", "type": "approval", "question": "haan?"}]))
    r = _run(D.dhara_run(CTX, name="gate2"))
    _run(D.drain())
    assert D.get_run(CTX.tenant_id, r["run_id"])["status"] == "waiting_approval"
    _patch_settings(monkeypatch, dhara_approval_hours=1)
    D.update_run(CTX.tenant_id, r["run_id"], updated_at=time.time() - 7200)
    _run(D.tick())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "failed" and "approval" in run["error"]


def test_forget_old_runs_keeps_recent():
    _run(D.dhara_save(CTX, name="oldy", steps=[{"id": "a", "type": "set", "name": "v", "value": 1}]))
    r = _run(D.dhara_run(CTX, name="oldy"))
    _run(D.drain())
    D.update_run(CTX.tenant_id, r["run_id"], updated_at=time.time() - 40 * 86400)
    gone = D.forget_old_runs(CTX.tenant_id, keep_days=30)
    assert gone == 1 and D.get_run(CTX.tenant_id, r["run_id"]) is None


# ---------------------------------------------------------------- webhook

def _mint_hook_token(tenant, name):
    tok = "hooktest-" + name
    con = D._con(tenant)
    con.execute("UPDATE workflows SET token_hash = ? WHERE name = ?",
                (hashlib.sha256(tok.encode()).hexdigest(), name))
    con.commit()
    con.close()
    return tok


def test_webhook_enqueues_with_body_and_refuses_bad_tokens():
    _run(D.dhara_save(CTX, name="hooked", steps=[{"id": "a", "type": "set", "name": "x", "value": "1"}],
                      trigger="webhook"))
    tok = _mint_hook_token(CTX.tenant_id, "hooked")
    out = D.webhook_enqueue(tok, {"order_id": "A-1"})
    assert out["ok"] is True and out["status"] == 202 and out["run_id"].startswith("rn_")
    run = D.get_run(CTX.tenant_id, out["run_id"])
    assert run["context"]["vars"]["body"] == {"order_id": "A-1"}
    assert D.webhook_enqueue("wrong-token", {})["status"] == 401
    # throttle: a second run of the SAME workflow inside 6 s is refused (10/min ceiling)
    second = D.webhook_enqueue(tok, {"again": True})
    assert second["status"] == 429
    # disabled workflow: the token stops working
    _run(D.dhara_control(CTX, action="disable", name="hooked"))
    time.sleep(6.2)  # past the throttle window so we test the DISABLED path, not the throttle
    assert D.webhook_enqueue(tok, {})["status"] == 401


def test_webhook_kill_switch(monkeypatch):
    _patch_settings(monkeypatch, dhara_webhook_enabled=False)
    out = D.webhook_enqueue("anything", {})
    assert out["status"] == 503 and "off" in out["error"]


# ---------------------------------------------------------------- tools: runs / list / control / disabled

def test_dhara_runs_shapes_and_pagination():
    _run(D.dhara_save(CTX, name="paged", steps=[{"id": "a", "type": "set", "name": "v", "value": 1}]))
    for _ in range(3):
        _run(D.dhara_run(CTX, name="paged"))
        _run(D.drain())
    listing = _run(D.dhara_runs(CTX))
    assert listing["count"] == 3
    one = _run(D.dhara_runs(CTX, run_id=listing["runs"][0]["run_id"]))
    assert one["status"] == "done" and one["steps_log"][0]["id"] == "a"
    with pytest.raises(Exception):
        _run(D.dhara_runs(CTX, run_id="rn_nope"))


def test_dhara_list_is_the_board():
    _run(D.dhara_save(CTX, name="boardw", steps=_flow1_steps(), trigger="schedule",
                      trigger_spec={"every_hours": 24, "at": ["09:30"]}))
    _run(D.dhara_run(CTX, name="boardw"))
    _run(D.drain())
    board = _run(D.dhara_list(CTX))
    row = board["workflows"][0]
    assert row["name"] == "boardw" and row["trigger"] == "schedule" and row["enabled"] is True
    assert row["last_run"]["status"] == "done" and row["next_due_at"]


def test_control_enable_disable_roundtrip():
    _run(D.dhara_save(CTX, name="switchy", steps=_flow1_steps()))
    off = _run(D.dhara_control(CTX, action="disable", name="switchy"))
    assert off["enabled"] is False
    with pytest.raises(Exception):
        _run(D.dhara_run(CTX, name="switchy"))
    on = _run(D.dhara_control(CTX, action="enable", name="switchy"))
    assert on["enabled"] is True
    with pytest.raises(Exception):
        _run(D.dhara_control(CTX, action="explode"))


def test_disabled_flag_honest(monkeypatch):
    _patch_settings(monkeypatch, dhara_enabled=False)
    with pytest.raises(Exception) as e:
        _run(D.dhara_save(CTX, name="nope", steps=_flow1_steps()))
    assert "turned off" in str(e.value)
    with pytest.raises(Exception):
        _run(D.dhara_list(CTX))
    assert _run(D.tick()) == 0


# ---------------------------------------------------------------- isolation + masking + version

def test_tenant_isolation():
    _run(D.dhara_save(CTX, name="private", steps=_flow1_steps()))
    _run(D.dhara_save(CTX2, name="private", steps=[{"id": "z", "type": "set", "name": "v", "value": 9}]))
    r2 = _run(D.dhara_run(CTX2, name="private"))
    _run(D.drain())
    mine = D.get_workflow(CTX.tenant_id, name="private")
    theirs = D.get_workflow(CTX2.tenant_id, name="private")
    assert mine["id"] != theirs["id"]
    assert D.get_run(CTX.tenant_id, r2["run_id"]) is None
    assert len(_run(D.dhara_list(CTX))["workflows"]) == 1


def test_outputs_pass_mask_ids():
    _run(D.dhara_save(CTX, name="masked", steps=[
        {"id": "a", "type": "set", "name": "aadhaar_like", "value": "2341 2345 6789"}]))
    r = _run(D.dhara_run(CTX, name="masked"))
    _run(D.drain())
    one = _run(D.dhara_runs(CTX, run_id=r["run_id"]))
    raw = json.dumps(one)
    assert "2341 2345 6789" not in raw, "an id-number-looking value must be masked in what the model reads"


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.767.0"
    from pathlib import Path
    pub = Path(__file__).resolve().parents[2] / "pubspec.yaml"
    assert "0.767.0+766" in pub.read_text()
