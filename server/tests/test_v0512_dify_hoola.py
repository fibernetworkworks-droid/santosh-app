"""v0.512.0 DIFY FOR HOOLA — the three verified deltas from the Dify READ (langgenius/dify @ 1.19.0,
887 MB, 15,838 files, modified-Apache multi-tenant license = ZERO Dify code, idea only), house-sized:

LANE A — Gyaan Annotations ("approved jawabs", their annotation-reply idea): saved answers served
BEFORE retrieval (exact on the normalized question, else stdlib difflib fuzzy >= 0.92), redaction
on save, owner-only writes, per-tenant isolation, caps, on/off, honest counting.
LANE B — DHARA ops-grade eyes (their WorkflowRunSummary + PauseReason + node_version + retry):
a computed summary (steps/parks/tries/wall/cost via the v0.476 run meter) on every honest end,
typed pause reasons, the executed step-type version in the log, and retry FROM the cursor —
safe by the checkpoint law (a finished step never runs twice), approval-expired honestly refused.
LANE C — dhara_dsl export/import (their DSL idea): portable workflow envelopes, secrets-free by
law (the webhook token never rides; values pass mask_ids), import through the SAME hard validator,
lands disabled, name-collision honest, webhook re-token on import.
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
from app.gyaan import annotations as A
from app.gyaan import store

T1, T2 = "dify512-a", "dify512-b"
CTX = Ctx(tenant_id=T1, conversation_id="c1")
CTX2 = Ctx(tenant_id=T2, conversation_id="c2")


def _run(coro):
    return asyncio.run(coro)


def _wipe_all():
    for t in (T1, T2):
        shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)
        p = store.path_of(t)
        for suffix in ("", "-wal", "-shm"):
            Path(str(p) + suffix).unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    D._RUNNING.clear()
    A.STATS.clear()
    A.STATS.update({"saves": 0, "matches": 0, "exact": 0, "fuzzy": 0, "misses": 0})
    _wipe_all()
    yield
    D._RUNNING.clear()
    _wipe_all()


class _NS:
    """A settings stand-in covering every knob both lanes read with getattr(s, name, default)."""
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
        self.dhara_summaries_enabled = True
        self.dhara_dsl_enabled = True
        self.dhara_dsl_max_kb = 64
        self.gyaan_dir = "data/gyaan"
        self.gyaan_annotation_enabled = True
        self.gyaan_annotation_fuzzy = 0.92
        self.gyaan_annotation_max = 200
        for k, v in kw.items():
            setattr(self, k, v)


def _patch_settings(monkeypatch, **kw):
    import app.config as cfg
    monkeypatch.setattr(cfg, "get_settings", lambda: _NS(**kw))


# ================================================================= LANE A — annotations

def test_annotation_save_list_delete():
    out = A.save(T1, "courier charge kya hai?", "Rs 50 per booking.", "rate card")
    assert out["ok"] and out["created"] and out["id"].startswith("pa_")
    rows = A.list_pairs(T1)
    assert rows and rows[0]["q_raw"].startswith("courier") and rows[0]["note"] == "rate card"
    gone = A.delete(T1, out["id"])
    assert gone["ok"] and A.list_pairs(T1) == []
    assert A.delete(T1, "pa_nahi")["ok"] is False


def test_annotation_exact_match_ignores_case_and_punct():
    A.save(T1, "Courier Charge kya hai?", "Rs 50 per booking.")
    m = A.match(T1, "courier charge kya hai")
    assert m["hit"] and m["how"] == "exact" and m["score"] == 1.0
    assert m["hit_card"]["title"] == "Aapka approved jawab"
    assert m["hit_card"]["text"] == "Rs 50 per booking."


def test_annotation_fuzzy_hit_above_threshold():
    A.save(T1, "gst number kya hai", "27AAPFU0939F1ZV")
    m = A.match(T1, "gst number kya hain")   # spelling variant, ratio ~0.97 > 0.92
    assert m["hit"] and m["how"] == "fuzzy" and m["score"] >= 0.92


def test_annotation_miss_below_threshold_falls_through():
    A.save(T1, "gst number kya hai", "27AAPFU0939F1ZV")
    m = A.match(T1, "gst return kab bharna hai")   # same words partially, clearly below 0.92
    assert m["hit"] is False


def test_annotation_threshold_knob(monkeypatch):
    A.save(T1, "gst number kya hai", "27AAPFU0939F1ZV")
    _patch_settings(monkeypatch, gyaan_annotation_fuzzy=0.999)
    assert A.match(T1, "gst number kya hain")["hit"] is False   # was a fuzzy hit at 0.92


def test_annotation_redaction_law_on_save():
    out = A.save(T1, "staff password kya tha", "otp 1234 hai, upar wala")
    assert out["ok"]
    stored = [p for p in A.list_pairs(T1) if p["id"] == out["id"]][0]["answer"]
    assert "1234" not in stored and "••••" in stored
    assert out["masked"] == ["secret"]   # norm.mask reports the CATEGORY, not the trigger word


def test_annotation_disabled_pair_skipped_then_on():
    out = A.save(T1, "shop timing kya hai", "10 baje se 9 baje")
    A.set_enabled(T1, out["id"], False)
    assert A.match(T1, "shop timing kya hai")["hit"] is False
    A.set_enabled(T1, out["id"], True)
    assert A.match(T1, "shop timing kya hai")["hit"] is True


def test_annotation_kill_switch(monkeypatch):
    A.save(T1, "shop timing kya hai", "10 baje se 9 baje")
    _patch_settings(monkeypatch, gyaan_annotation_enabled=False)
    assert A.match(T1, "shop timing kya hai")["hit"] is False


def test_annotation_same_question_replaces_answer():
    A.save(T1, "rent kitna hai", "Rs 18,500")
    out2 = A.save(T1, "Rent kitna hai?", "Rs 19,000 (naya agreement)")
    assert out2["ok"] and out2["created"] is False
    rows = A.list_pairs(T1)
    assert len(rows) == 1 and "19,000" in rows[0]["answer"]


def test_annotation_cap_honest(monkeypatch):
    _patch_settings(monkeypatch, gyaan_annotation_max=2)
    assert A.save(T1, "sawaal ek", "jawab ek")["ok"]
    assert A.save(T1, "sawaal do", "jawab do")["ok"]
    full = A.save(T1, "sawaal teen", "jawab teen")
    assert full["ok"] is False and "limit" in full["error"]
    # replacing an existing question never counts against the cap
    assert A.save(T1, "sawaal do", "jawab do badla")["ok"]


def test_annotation_multi_tenant_isolation():
    A.save(T1, "courier charge kya hai", "Rs 50")
    assert A.match(T2, "courier charge kya hai")["hit"] is False
    assert A.match(T1, "courier charge kya hai")["hit"] is True


def test_annotation_counts_hits():
    A.save(T1, "rent kitna hai", "Rs 18,500")
    A.match(T1, "rent kitna hai")
    A.match(T1, "rent kitna hai")
    row = A.list_pairs(T1)[0]
    assert row["hits"] == 2 and row["last_hit_at"]
    st = A.status(T1)
    assert st["pairs"] == 1 and st["stats"]["matches"] == 2 and st["stats"]["exact"] == 2


def test_gyaan_tool_save_answer_owner_gated():
    staff = Ctx(tenant_id=T1, conversation_id="c1", actor="staff")
    with pytest.raises(Exception):
        _run(_gyaan_tool(staff, "save_answer", question="q", text="a"))
    out = _run(_gyaan_tool(CTX, "save_answer", question="delivery kitne din mein",
                           text="2-3 din mein", title="policy"))
    assert out["ok"] is True
    listed = _run(_gyaan_tool(CTX, "answers"))
    assert listed["count"] == 1 and listed["answers"][0]["question"].startswith("delivery")


def test_gyaan_khojo_annotation_short_circuits_retrieval(monkeypatch):
    A.save(T1, "courier charge kya hai", "Rs 50 per booking.")
    calls = []
    import app.gyaan.search as S
    def _no_search(*a, **k):
        calls.append(1)
        return {"status": "nahi_mila", "hits": [], "say": "nahi mila", "near": []}
    monkeypatch.setattr(S, "search", _no_search)
    out = _run(_khojo(CTX, "COURIER charge kya hai"))
    assert calls == []                                            # retrieval NEVER ran
    assert out["status"] == "found" and out["annotation"]["how"] == "exact"
    assert out["hits"][0]["title"] == "Aapka approved jawab"
    assert "[1]" and out["hits"][0]["n"] == 1                     # rides the normal citation numbering
    # and a miss falls through to retrieval exactly as before
    out2 = _run(_khojo(CTX, "bilkul alag sawaal jo saved nahi hai"))
    assert calls == [1] and out2["status"] == "nahi_mila"


def test_gyaan_tool_del_and_toggle_roundtrip():
    out = _run(_gyaan_tool(CTX, "save_answer", question="q1", text="a1"))
    pid = out["id"]
    off = _run(_gyaan_tool(CTX, "answer_off", pair_id=pid))
    assert off["ok"] and off["enabled"] is False
    on = _run(_gyaan_tool(CTX, "answer_on", pair_id=pid))
    assert on["ok"]
    gone = _run(_gyaan_tool(CTX, "del_answer", pair_id=pid))
    assert gone["ok"]


async def _gyaan_tool(ctx, action, **kw):
    from app.agent.gyaan_tools import gyaan
    return await gyaan(ctx, action=action, **kw)


async def _khojo(ctx, query):
    from app.agent.gyaan_tools import gyaan_khojo
    return await gyaan_khojo(ctx, query=query)


# ================================================================= LANE B — summaries / pauses / versions / retry

def _flow():
    return [
        {"id": "who", "type": "set", "name": "who", "value": "Malika"},
        {"id": "check", "type": "condition", "left": "{{vars.who}}", "op": "eq", "right": "Malika",
         "then": [{"id": "hi", "type": "set", "name": "msg", "value": "pranam"}], "else": []},
    ]


def test_done_run_carries_summary():
    _run(D.dhara_save(CTX, name="flow", steps=_flow()))
    r = _run(D.dhara_run(CTX, name="flow", vars={"who": "Malika"}))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    s = run["summary"]
    assert s["steps_total"] == 2 and s["steps_ran"] == 2 and s["parks"] == 0
    assert s["cost"]["calls"] == 0 and s["cost"]["usd"] == 0.0
    assert s["tries"] >= 0 and s["wall_ms"] >= 0   # a manual run starts without a tick claim
    assert "fail_error" not in s


def test_failed_run_summary_has_the_exact_stop():
    _run(D.dhara_save(CTX, name="bad", steps=[{"id": "t", "type": "tool", "name": "no_such_tool"}]))
    r = _run(D.dhara_run(CTX, name="bad"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "failed"
    assert run["summary"]["steps_ran"] == 0
    assert "step 't'" in run["summary"]["fail_error"]
    assert run["steps_log"], "the fail path keeps its log (the v0.502 lesson stands)"


def test_stopped_run_carries_summary_with_parks():
    _run(D.dhara_save(CTX, name="stoppable", steps=[
        {"id": "first", "type": "set", "name": "v1", "value": 1},
        {"id": "w", "type": "wait", "duration_s": 3600},
        {"id": "never", "type": "set", "name": "v3", "value": 3}]))
    r = _run(D.dhara_run(CTX, name="stoppable"))
    _run(D.drain())
    out = _run(D.dhara_control(CTX, action="stop", run_id=r["run_id"]))
    assert out["status"] == "stopped"
    run = D.get_run(CTX.tenant_id, r["run_id"])
    s = run["summary"]
    assert s["steps_total"] == 3 and s["steps_ran"] == 2 and s["parks"] == 1
    assert "never" not in [x["id"] for x in run["steps_log"]]


def test_approval_park_is_typed_and_approve_clears_it():
    _run(D.dhara_save(CTX, name="gate", steps=[
        {"id": "gate", "type": "approval", "question": "bhej dun?"},
        {"id": "after", "type": "set", "name": "flag", "value": "haan"}]))
    r = _run(D.dhara_run(CTX, name="gate"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "waiting_approval" and run["pause_reason"] == "waiting_approval"
    assert run["summary"] is None, "a parked run has not ended — no summary yet"
    _run(D.dhara_control(CTX, action="approve", run_id=r["run_id"]))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done" and not run["pause_reason"]
    assert run["summary"]["parks"] == 1


def test_wait_park_typed_sleeping_and_wake_clears_it():
    _run(D.dhara_save(CTX, name="waiter", steps=[
        {"id": "w", "type": "wait", "duration_s": 3600},
        {"id": "after", "type": "set", "name": "flag", "value": "jaag gaya"}]))
    r = _run(D.dhara_run(CTX, name="waiter"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "sleeping" and run["pause_reason"] == "sleeping"
    D.update_run(CTX.tenant_id, r["run_id"], next_wake_at=time.time() - 1)
    _run(D.tick())
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done" and not run["pause_reason"]


def test_approval_expiry_is_typed_and_refuses_retry(monkeypatch):
    _patch_settings(monkeypatch, dhara_approval_hours=1)
    _run(D.dhara_save(CTX, name="slowgate", steps=[
        {"id": "gate", "type": "approval", "question": "bhej dun?"},
        {"id": "after", "type": "set", "name": "flag", "value": "x"}]))
    r = _run(D.dhara_run(CTX, name="slowgate"))
    _run(D.drain())
    D.update_run(CTX.tenant_id, r["run_id"], updated_at=time.time() - 2 * 3600)
    _run(D.tick())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "failed" and run["pause_reason"] == "approval_expired"
    out = _run(D.dhara_control(CTX, action="retry", run_id=r["run_id"]))
    assert out.get("ok") is False and "approving again" in out["note"]


def test_step_version_recorded_default_1():
    _run(D.dhara_save(CTX, name="flow", steps=_flow()))
    r = _run(D.dhara_run(CTX, name="flow", vars={"who": "Malika"}))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert all(e.get("v") == 1 for e in run["steps_log"])


def test_step_version_honored_when_declared():
    steps = [{"id": "a", "type": "set", "name": "v", "value": "1", "v": 2}]
    _run(D.dhara_save(CTX, name="v2flow", steps=steps))
    r = _run(D.dhara_run(CTX, name="v2flow"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["steps_log"][-1]["v"] == 2


def test_retry_resumes_from_cursor_zero_steps_twice(monkeypatch):
    """A failed run re-queues FROM ITS CURSOR; the finished step never runs twice (checkpoint law)."""
    calls = []
    async def flaky(ctx, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise D.ToolError("gateway down")
        return {"ok": True}
    import app.agent.tools as T
    monkeypatch.setitem(T.HANDLERS, "flaky_probe", flaky)
    _run(D.dhara_save(CTX, name="withflaky", steps=[
        {"id": "a", "type": "set", "name": "v1", "value": "1"},
        {"id": "f", "type": "tool", "name": "flaky_probe"},
        {"id": "c", "type": "set", "name": "v2", "value": "2"}]))
    r = _run(D.dhara_run(CTX, name="withflaky"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "failed" and run["cursor"] == 1
    out = _run(D.dhara_control(CTX, action="retry", run_id=r["run_id"]))
    assert out["status"] == "queued"
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done" and run["context"]["vars"]["v2"] == "2"
    ids = [e["id"] for e in run["steps_log"]]
    assert ids.count("a") == 1, "the finished step NEVER ran twice"
    assert ids.count("c") == 1
    assert "a" in ids and ids.index("a") < ids.index("f")
    assert run["summary"]["steps_ran"] == 3


def test_retry_honest_on_live_or_done_runs():
    _run(D.dhara_save(CTX, name="plain", steps=[{"id": "a", "type": "set", "name": "v", "value": "1"}]))
    r = _run(D.dhara_run(CTX, name="plain"))
    out = _run(D.dhara_control(CTX, action="retry", run_id=r["run_id"]))
    assert "only on a stopped" in out["note"]
    _run(D.drain())
    out2 = _run(D.dhara_control(CTX, action="retry", run_id=r["run_id"]))
    assert "only on a stopped" in out2["note"]


def test_summaries_kill_switch(monkeypatch):
    _patch_settings(monkeypatch, dhara_summaries_enabled=False)
    _run(D.dhara_save(CTX, name="flow", steps=_flow()))
    r = _run(D.dhara_run(CTX, name="flow", vars={"who": "Malika"}))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    assert run["status"] == "done" and run["summary"] is None


def test_runs_boards_carry_pause_reason_and_summary():
    _run(D.dhara_save(CTX, name="flow", steps=_flow()))
    r = _run(D.dhara_run(CTX, name="flow", vars={"who": "Malika"}))
    _run(D.drain())
    one = _run(D.dhara_runs(CTX, run_id=r["run_id"]))
    assert "pause_reason" in one and one["summary"]["steps_total"] == 2
    many = _run(D.dhara_runs(CTX))
    row = many["runs"][0]
    assert "pause_reason" in row and row["summary"]["steps_ran"] == 2


def test_run_cost_meter_wiring(monkeypatch):
    """A tool step that makes a model call lands in the run's OWN summary cost (usage.run_meter)."""
    import app.usage as U
    async def probe(ctx, **kw):
        U.record("claude-sonnet-5-5", tok_in=1000, tok_out=100)
        return {"ok": True}
    import app.agent.tools as T
    monkeypatch.setitem(T.HANDLERS, "cost_probe", probe)
    _run(D.dhara_save(CTX, name="spender", steps=[{"id": "p", "type": "tool", "name": "cost_probe"}]))
    r = _run(D.dhara_run(CTX, name="spender"))
    _run(D.drain())
    run = D.get_run(CTX.tenant_id, r["run_id"])
    cost = run["summary"]["cost"]
    assert cost["calls"] == 1 and cost["tok_in"] == 1000 and cost["tok_out"] == 100
    assert cost["usd"] > 0 and cost["inr"] > 0


def test_summary_cost_inr_conversion_unit(monkeypatch):
    import app.usage as U
    monkeypatch.setattr(U, "usd_inr", lambda: 88.0)
    s = D._summary({"cursor": 2, "tries": 1, "started_at": time.time() - 1.5, "steps_log": []},
                   2, "", {"usd": 0.5, "calls": 3, "tok_in": 100, "tok_out": 50})
    assert s["cost"]["inr"] == 44.0 and s["cost"]["calls"] == 3
    assert s["wall_ms"] >= 1400


# ================================================================= LANE C — DSL export / import

def _dsl_export(name):
    return _run(D.dhara_dsl(CTX, action="export", name=name))


def test_dsl_export_envelope_shape():
    _run(D.dhara_save(CTX, name="portable", steps=_flow(), description="le jaao"))
    out = _dsl_export("portable")
    env = out["dsl"]
    assert env["dhara_dsl"] == 1 and env["source"] == "hoola-dhara"
    assert env["name"] == "portable" and env["description"] == "le jaao"
    assert env["trigger"] == "manual" and len(env["steps"]) == 2
    assert "exported_at" in env and out["bytes"] > 0


def test_dsl_export_never_carries_the_webhook_token():
    saved = _run(D.dhara_save(CTX, name="hooked", trigger="webhook",
                              steps=[{"id": "a", "type": "set", "name": "v", "value": "1"}]))
    token = saved["webhook_note"].split(": ", 1)[1]          # the one-time reveal
    env = _dsl_export("hooked")["dsl"]
    raw = json.dumps(env)
    assert token not in raw and "token_hash" not in raw and "token" not in raw.lower().replace("token_hash_", "")


def test_dsl_export_masks_identities():
    _run(D.dhara_save(CTX, name="panny", steps=[
        {"id": "a", "type": "set", "name": "pan", "value": "owner PAN ABCPE1234F"}]))
    raw = json.dumps(_dsl_export("panny")["dsl"])
    assert "ABCPE1234F" not in raw and "XXXXXX" in raw


def test_dsl_import_runs_the_same_hard_validator():
    env = {"dhara_dsl": 1, "name": "broken", "trigger": "manual",
           "steps": [{"id": "a", "type": "magic"}]}
    with pytest.raises(Exception) as e:
        _run(D.dhara_dsl(CTX, action="import", dsl=env))
    assert "anjaan type" in str(e.value)
    with pytest.raises(Exception):
        _run(D.dhara_dsl(CTX, action="import", dsl={"nope": 1}))
    with pytest.raises(Exception):
        _run(D.dhara_dsl(CTX, action="import", dsl=json.dumps({"dhara_dsl": 2, "name": "x", "steps": _flow()})))


def test_dsl_import_lands_disabled():
    _run(D.dhara_save(CTX2, name="traveler", steps=_flow()))
    env = _run(D.dhara_dsl(CTX2, action="export", name="traveler"))["dsl"]
    out = _run(D.dhara_dsl(CTX, action="import", dsl=env))
    assert out["ok"] is True and out["enabled"] is False and "OFF" in out["note"]
    assert D.get_workflow(T1, name="traveler")["enabled"] in (0, False)


def test_dsl_import_name_collision_is_honest_and_new_name_works():
    _run(D.dhara_save(CTX, name="dupe", steps=_flow()))
    env = _dsl_export("dupe")["dsl"]
    out = _run(D.dhara_dsl(CTX, action="import", dsl=env))
    assert out["ok"] is False and out["already_exists"] is True
    out2 = _run(D.dhara_dsl(CTX, action="import", dsl=env, new_name="dupe_2"))
    assert out2["ok"] is True and out2["name"] == "dupe_2"


def test_dsl_roundtrip_export_import_export():
    _run(D.dhara_save(CTX, name="round", steps=_flow(), trigger="schedule",
                       trigger_spec={"every_hours": 6, "at": ["09:30"]}))
    env1 = _dsl_export("round")["dsl"]
    _run(D.dhara_dsl(CTX, action="import", dsl=env1, new_name="round_copy"))
    env2 = _run(D.dhara_dsl(CTX, action="export", name="round_copy"))["dsl"]
    for env in (env1, env2):
        env.pop("exported_at"), env.pop("name")
    assert env1 == env2


def test_dsl_size_cap(monkeypatch):
    _patch_settings(monkeypatch, dhara_dsl_max_kb=1)
    big = [{"id": f"s{i}", "type": "set", "name": f"v{i}", "value": "x" * 1500} for i in range(10)]
    _run(D.dhara_save(CTX, name="big", steps=big))
    with pytest.raises(Exception) as e:
        _run(D.dhara_dsl(CTX, action="export", name="big"))
    assert "too big" in str(e.value)


def test_dsl_webhook_import_mints_a_new_token_shown_once():
    _run(D.dhara_save(CTX2, name="hooky", trigger="webhook",
                      steps=[{"id": "a", "type": "set", "name": "v", "value": "1"}]))
    env = _run(D.dhara_dsl(CTX2, action="export", name="hooky"))["dsl"]
    out = _run(D.dhara_dsl(CTX, action="import", dsl=env))
    tok = out["webhook_note"].rsplit(": ", 1)[1]
    th = hashlib.sha256(tok.encode()).hexdigest()
    assert D.workflows_with_hash(T1, th)["name"] == "hooky"


def test_dsl_kill_switch(monkeypatch):
    _patch_settings(monkeypatch, dhara_dsl_enabled=False)
    with pytest.raises(Exception) as e:
        _run(D.dhara_dsl(CTX, action="export", name="x"))
    assert "turned off" in str(e.value).lower()


# ================================================================= pins

def test_registry_542_with_dhara_dsl():
    names = {t["name"] for t in D.DHARA_TOOLS}
    assert names == {"dhara_save", "dhara_run", "dhara_runs", "dhara_control", "dhara_list", "dhara_dsl"}
    assert set(D.DHARA_LABELS) == set(D.DHARA_HANDLERS) == names
    global_names = {t["name"] for t in TOOLS}
    assert names <= global_names
    for n in names:
        assert n in HANDLERS and n in TOOL_LABELS, n
    assert len(TOOLS) == 629, "626 + 1 app_engine (v0.824 APP ENGINE 1: the Web Studio React app lane - one new tool). 625 + 1 hoola_design (v0.817.0 HOOLA DESIGN: the design editor's one tool). 624 + 1 ai_app (v0.785 HOOLA AI APPS). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " "581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 541 (v0.502) + 1 magic21 (their v0.512) + 1 dhara_dsl (v0.514) + 10 construction Wave 1 (v0.522) + 1 crew_run (v0.523) + 2 from main's v0.533 CRAWL BRAIN wiring (healed in v0.537: red on pristine main) + 1 reach (v0.559 REACH MANCH) + 1 speckit (v0.569 SPEC SUTRA)"
    for n in names:
        assert FAMILY_OF.get(n) == "dhara", n


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.878.0"
