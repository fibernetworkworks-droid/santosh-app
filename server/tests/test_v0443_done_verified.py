"""v0.443 DONE = VERIFIED (long-task report items 1 + 2, RCA fix 7).

1. `kaam_plan finish done` no longer closes a goal card on the model's word: `verify.gate` checks in CODE that the
   files / pages / links / datasets in `made` are really there and that every step's own `check` holds. A failure
   reopens the failing step and the goal stays `working`; `unknown` (a link that could not be reached) never blocks.
2. The free fake-done check (`draftcheck.fake_done`) runs in goal mode too - a goal could tick its own steps and
   claim "bhej diya" with only reads behind it."""
import asyncio

import pytest
from sqlalchemy import select

import app.agent.santosh as santosh
from app.agent import goal as G
from app.agent import verify as V
from app.agent.tools import Ctx
from app.config import get_settings
from app.db import Artifact, ArtifactVersion, Conversation, ListItem, PcFile, Reminder, now, session


def run(coro):
    return asyncio.run(coro)


def _conv(conv="c_ver", tenant="default"):
    with session() as s:
        if s.get(Conversation, conv) is None:
            s.add(Conversation(id=conv, tenant_id=tenant, title="t"))
    return conv


def _file(tmp_path, tenant="default", name="report.pdf", fid="file_v1aa11", pages=3, rows=0, slides=0, body=b"x" * 64):
    p = tmp_path / name
    if name.endswith(".pdf") and pages:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(p), pagesize=A4)
        for i in range(pages):
            c.drawString(50, 800, f"page {i}")
            c.showPage()
        c.save()
    elif name.endswith(".xlsx"):
        from openpyxl import Workbook
        wb = Workbook()
        wb.active.append(["head"])
        for i in range(rows):
            wb.active.append([i])
        wb.save(p)
    else:
        p.write_bytes(body)
    with session() as s:
        s.add(PcFile(id=fid, tenant_id=tenant, device_id="", direction="to_phone", name=name,
                     size=p.stat().st_size, sha256="x", stored_path=str(p)))
    return p


def _artifact(tenant="default", aid="art_v1aa11", ready=True, html="<p>hello</p>"):
    with session() as s:
        s.add(Artifact(id=aid, tenant_id=tenant, conversation_id="c_ver", title="EMI page",
                       version=1 if ready else 0, status="ready" if ready else "building"))
        if ready:
            s.add(ArtifactVersion(artifact_id=aid, version=1, html=html))
    return aid


# ---------------- the pieces

def test_file_checks_record_disk_and_emptiness(env, tmp_path):
    _file(tmp_path, fid="file_ok2211")
    assert V.check_file_id("default", "file_ok2211")["state"] == "ok"
    assert V.check_file_id("default", "file_nope3311")["state"] == "failed"      # never made
    assert V.check_file_id("other", "file_ok2211")["state"] == "failed"          # another tenant's file
    p = _file(tmp_path, fid="file_gone4411", name="gone.pdf")
    p.unlink()
    r = V.check_file_id("default", "file_gone4411")
    assert r["state"] == "failed" and "disk par nahi" in r["why"]
    _file(tmp_path, fid="file_empty5511", name="empty.csv", body=b"")
    assert "khaali" in V.check_file_id("default", "file_empty5511")["why"]


def test_artifact_and_filename_checks(env, tmp_path):
    _artifact(aid="art_ready2211")
    assert V.check_artifact("default", "art_ready2211")["state"] == "ok"
    _artifact(aid="art_building3311", ready=False)
    assert V.check_artifact("default", "art_building3311")["state"] == "failed"
    _artifact(aid="art_blank4411", html="   ")
    assert "khaali" in V.check_artifact("default", "art_blank4411")["why"]
    assert V.check_artifact("default", "art_missing5511")["state"] == "failed"
    _file(tmp_path, fid="file_n16611", name="sales.xlsx", rows=4)
    assert V.check_filename("default", "sales.xlsx")["state"] == "ok"
    assert V.check_filename("default", "ghost.xlsx")["state"] == "failed"


def test_link_check_404_is_a_failure_but_unreachable_is_unknown(env, monkeypatch):
    class _R:
        def __init__(self, code):
            self.status_code = code

    class _C:
        def __init__(self, code, refuse_head=False):
            self.code, self.refuse_head = code, refuse_head

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def head(self, url):
            return _R(405 if self.refuse_head else self.code)

        def get(self, url, headers=None):
            return _R(self.code)

    import httpx
    monkeypatch.setattr(get_settings(), "goal_verify_links", True)   # conftest keeps the suite offline; this test
    #                                                                 is the link checker itself (httpx is faked)
    monkeypatch.setattr(httpx, "Client", lambda **k: _C(200))
    assert V.check_link("https://x.in/a")["state"] == "ok"
    monkeypatch.setattr(httpx, "Client", lambda **k: _C(404))
    assert V.check_link("https://x.in/a")["state"] == "failed"
    monkeypatch.setattr(httpx, "Client", lambda **k: _C(503))
    assert V.check_link("https://x.in/a")["state"] == "unknown"     # her VPS down is not her job being wrong
    monkeypatch.setattr(httpx, "Client", lambda **k: _C(200, refuse_head=True))
    assert V.check_link("https://x.in/a")["state"] == "ok"          # HEAD refused -> ranged GET

    def boom(**k):
        raise RuntimeError("dns")
    monkeypatch.setattr(httpx, "Client", boom)
    assert V.check_link("https://x.in/a")["state"] == "unknown"
    monkeypatch.setattr(get_settings(), "goal_verify_links", False)
    r = V.check_link("https://x.in/a")
    assert r["state"] == "unknown" and "band hai" in r["why"]        # the switch: no call at all


def test_dataset_check(env):
    from app import datasets as D
    doc = D.save("default", [{"a": 1}, {"a": 2}], name="evs")
    ds = doc["dataset"] if isinstance(doc, dict) and "dataset" in doc else doc.get("id") or doc.get("ds")
    assert V.check_dataset("default", f"yeh {ds} bana")["state"] == "ok"
    assert V.check_dataset("default", "ds_notthere00")["state"] == "failed"
    assert V.check_dataset("default", "koi prose line") is None     # nothing checkable -> no row


def test_check_made_skips_prose_and_caps_links(env, tmp_path, monkeypatch):
    _file(tmp_path, fid="file_m17711", name="r.pdf")
    monkeypatch.setattr(V, "check_link", lambda u: V._ok(u, "200"))
    rows = V.check_made("default", ["file_m17711", "Report bana diya aur bhej diya", "ghost.pdf"])
    assert [r["state"] for r in rows] == ["ok", "failed"]           # the prose line makes no row
    many = [f"https://x.in/{i}" for i in range(V.MAX_LINKS + 2)]
    rows = V.check_made("default", many)
    assert sum(1 for r in rows if r["state"] == "unknown") == 2     # over the cap: said, never silently passed


# ---------------- the step's own check

def test_step_checks(env, tmp_path, monkeypatch):
    conv = _conv()
    _file(tmp_path, fid="file_s18811", name="plan.pdf", pages=3)
    assert V.check_step("default", conv, {"n": 1, "state": "done", "check": "file_pages>=3",
                                          "note": "file_s18811"})["state"] == "ok"
    r = V.check_step("default", conv, {"n": 1, "state": "done", "check": "file_pages>=5", "note": "file_s18811"})
    assert r["state"] == "failed" and "3 pages hain" in r["why"]
    _file(tmp_path, fid="file_s29911", name="rows.xlsx", rows=30)
    assert V.check_step("default", conv, {"n": 2, "state": "done", "check": "file_rows>=30",
                                          "note": "file_s29911"})["state"] == "ok"
    assert V.check_step("default", conv, {"n": 2, "state": "done", "check": "file_rows>=31",
                                          "note": "file_s29911"})["state"] == "failed"
    with session() as s:
        s.add(Reminder(tenant_id="default", conversation_id=conv, text="a", due_at=now()))
        s.add(ListItem(tenant_id="default", list_name="Diwali", text="diye"))
    assert V.check_step("default", conv, {"n": 3, "state": "done", "check": "reminder>=1"})["state"] == "ok"
    assert V.check_step("default", conv, {"n": 3, "state": "done", "check": "reminder>=3"})["state"] == "failed"
    assert V.check_step("default", conv, {"n": 4, "state": "done", "check": "list:diwali>=1"})["state"] == "ok"
    assert V.check_step("default", conv, {"n": 4, "state": "done", "check": "list:diwali>=9"})["state"] == "failed"
    calls = [{"tool": "mospi", "ok": True}, {"tool": "pylab", "ok": False}]
    assert V.check_step("default", conv, {"n": 5, "state": "done", "check": "tool:mospi"}, calls)["state"] == "ok"
    assert V.check_step("default", conv, {"n": 5, "state": "done", "check": "tool:pylab"}, calls)["state"] == "failed"
    _artifact(aid="art_s16611")
    assert V.check_step("default", conv, {"n": 6, "state": "done", "check": "artifact"})["state"] == "ok"
    assert V.check_step("default", conv, {"n": 7, "state": "done", "check": ""}) is None          # no check
    assert V.check_step("default", conv, {"n": 8, "state": "done",
                                          "check": "ajeeb_check"})["state"] == "unknown"          # never a failure
    monkeypatch.setattr(V, "check_link", lambda u: V._ok(u, "200"))
    assert V.check_step("default", conv, {"n": 9, "state": "done", "check": "link_ok",
                                          "note": "https://x.in/a"})["state"] == "ok"
    assert V.check_step("default", conv, {"n": 9, "state": "done", "check": "link_ok",
                                          "note": "no link here"})["state"] == "failed"


def test_gate_passes_unknowns_blocks_failures_and_never_raises(env, tmp_path, monkeypatch):
    conv = _conv()
    _file(tmp_path, fid="file_g1a0a0", name="g.pdf", pages=2)
    out = V.gate("default", conv, ["file_g1a0a0"], [{"n": 1, "state": "done", "check": "file_pages>=2",
                                                 "note": "file_g1a0a0"}])
    assert out["ok"] and out["checked"] == 2
    monkeypatch.setattr(V, "check_link", lambda u: V._unknown(u, "timeout"))
    out = V.gate("default", conv, ["https://x.in/a"], [])
    assert out["ok"] and out["unknown"] and "Check nahi ho paya" in out["line"]
    out = V.gate("default", conv, ["ghost.pdf"], [])
    assert not out["ok"] and "ghost.pdf" in out["line"]
    out = V.gate("default", conv, [], [{"n": 2, "state": "pending", "check": "file_pages>=9"}])
    assert out["ok"] and out["checked"] == 0                       # a step not claimed done is not checked

    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(V, "check_made", boom)
    out = V.gate("default", conv, ["file_g1a0a0"], [])
    assert out["ok"] and out["unknown"]                             # a broken check never breaks her job


# ---------------- finish() through the gate

def test_finish_done_is_refused_when_the_file_is_not_there(env):
    conv = _conv("c_ver2")
    v = G.set_goal("default", conv, "report banao", ["data lao", "PDF banao"])
    G.mark_step("default", v["id"], 1, "done")
    G.mark_step("default", v["id"], 2, "done", note="file_ghost1313")
    held = G.finish("default", v["id"], "done", "ho gaya", conv, made=["report_final.pdf"])
    assert held["verified"] is False and held["status"] == "working"
    steps = held["steps"]
    assert steps[1]["state"] == "current" and "not found in the check" in steps[1]["note"]
    with session() as s:
        row = s.scalars(select(G.GoalRun).where(G.GoalRun.id == v["id"])).first()
        assert row.status == "working" and "Check pending" in row.reason


def test_finish_done_closes_when_the_file_is_really_there(env, tmp_path):
    conv = _conv("c_ver3")
    _file(tmp_path, fid="file_real1212", name="final.pdf", pages=4)
    v = G.set_goal("default", conv, "report banao", [{"text": "PDF banao", "check": "file_pages>=4"}])
    G.mark_step("default", v["id"], 1, "done", note="file_real1212")
    out = G.finish("default", v["id"], "done", "ban gaya", conv, made=["file_real1212"])
    assert out.get("verified") is not False and out["status"] == "done"
    assert out["report"]["hua"]


def test_only_done_passes_the_gate_and_the_switch_turns_it_off(env, monkeypatch):
    conv = _conv("c_ver4")
    for outcome, want in (("blocked_on_her", "blocked"), ("failed", "failed"), ("stopped", "stopped")):
        v = G.set_goal("default", conv, "g", ["s"])
        G.mark_step("default", v["id"], 1, "done")
        out = G.finish("default", v["id"], outcome, "why", conv, made=["ghost.pdf"])
        assert out["status"] == want and out.get("verified") is not False
    st = get_settings()
    monkeypatch.setattr(st, "goal_verify", False)
    v = G.set_goal("default", conv, "g", ["s"])
    G.mark_step("default", v["id"], 1, "done")
    assert G.finish("default", v["id"], "done", "", conv, made=["ghost.pdf"])["status"] == "done"


def test_the_tool_tells_the_model_to_really_do_it(env):
    from app.agent.goal_tools import kaam_plan
    conv = _conv("c_ver5")
    ctx = Ctx(tenant_id="default", conversation_id=conv)
    ctx.calls = [{"tool": "google_search", "ok": True}]
    run(kaam_plan(ctx, action="set", goal="report", steps=[{"text": "PDF banao", "check": "file_pages>=2"}]))
    run(kaam_plan(ctx, action="step", n=1, state="done", reason="ban gaya"))
    out = run(kaam_plan(ctx, action="finish", outcome="done", reason="ho gaya", made=["report.pdf"]))
    assert out["verified"] is False and "jaanch fail" in out["result"]
    assert out["failures"] and "finish done" in out["note"]
    assert "card_shows" not in out                      # no four-part report for a job that did not finish


def test_a_step_can_carry_its_check_from_set_step_and_add(env):
    conv = _conv("c_ver6")
    v = G.set_goal("default", conv, "g", [{"text": "a", "check": "file_pages>=2"}, "b"])
    assert v["steps"][0]["check"] == "file_pages>=2" and v["steps"][1]["check"] == ""
    v = G.mark_step("default", v["id"], 2, "done", check="reminder>=2")
    assert v["steps"][1]["check"] == "reminder>=2"
    v = G.add_step("default", v["id"], "c", check="link_ok")
    assert v["steps"][2]["check"] == "link_ok"


# ---------------- item 2: the free fake-done check works in goal mode too

def _state(calls, goal=None):
    return {"calls": calls, "goal": goal, "breaker": santosh.Breaker() if hasattr(santosh, "Breaker") else None}


def test_an_earlier_round_that_really_did_it_is_never_nudged(env):
    """v0.443: a long job works over several rounds. A later round that only ticks the last step and reports must
    NOT be called a false claim - the question is asked of the WHOLE job through the harness log."""
    from app.agent import draftcheck, eventlog
    from app.agent.breaker import Breaker
    conv = _conv("c_ver9")
    v = G.set_goal("default", conv, "mail bhejo", ["likho", "bhejo"])
    since = G.started_at(v["id"])
    state = {"calls": [{"tool": "kaam_plan", "ok": True}], "breaker": Breaker(), "goal": v, "request": "mail bhejo"}
    assert draftcheck.fake_done(dict(state), "Mail bhej diya.", conv, since)        # nothing has run yet
    eventlog.log_event("default", conv, "tool_result", {"tool": "email_send", "ok": True}, "turn_1", "owner")
    assert draftcheck.fake_done(dict(state), "Mail bhej diya.", conv, since) == ""  # round 1 really sent it
    assert draftcheck.nothing_ran_in_job(conv, since) is False
    assert draftcheck.nothing_ran_in_job("c_other", since) is True


def test_fake_done_now_runs_in_goal_mode(env, monkeypatch):
    from app.agent.breaker import Breaker
    conv = _conv("c_ver7")
    v = G.set_goal("default", conv, "mail bhejo", ["draft likho", "bhej do"])
    st = get_settings()
    state = {"calls": [{"tool": "google_search", "ok": True}], "breaker": Breaker(), "goal": v, "request": "mail bhejo"}
    nudge = run(santosh._pakka_check(state, "Mail bhej diya, ho gaya.", st, True, conv))
    assert "nothing that could do it" in nudge                     # was silent before v0.440
    state2 = {"calls": [{"tool": "email_send", "ok": True}], "breaker": Breaker(), "goal": v, "request": "x"}
    assert run(santosh._pakka_check(state2, "Mail bhej diya.", st, True, conv)) == ""   # a real send is fine


def test_the_goals_own_honest_line_never_trips_it(env):
    from app.agent.breaker import Breaker
    conv = _conv("c_ver8")
    v = G.set_goal("default", conv, "g", ["a", "b"])
    st = get_settings()
    line = "Goal jaari hai: 1/2 steps ho gaye (g); 1 baaki hain - main background mein aage badh raha hoon."
    state = {"calls": [{"tool": "google_search", "ok": True}], "breaker": Breaker(), "goal": v, "request": "g"}
    assert run(santosh._pakka_check(state, line, st, True, conv)) == ""


@pytest.mark.parametrize("name", ["_goal_open"])
def test_the_goal_mode_exemption_is_gone(name):
    assert not hasattr(santosh, name)
