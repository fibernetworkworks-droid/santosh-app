"""v0.416 QA FARM + BUG TRACKER (Hoola Game Engine plan, Phase 5): seeded bots on phone-like speeds play a DEBUG web
build (release builds hide script errors - found live), golden start screens, speed against the last run, numbered
bugs with the exact repro, fixes as board tasks that close only when the same bot cannot find the bug again. The bot
itself is faked here (it runs for real in the sandbox / VPS checks)."""
import asyncio
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


def _png(color):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (360, 640), color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def q(st, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setenv("GAME_CREW_REVIEW", "off")
    from app.gamedesk import qa as Q
    Q.ensure_table()
    build = tmp_path / "build_debug"
    build.mkdir()
    (build / "index.html").write_text("<html>")
    script = {"err": {}, "fps": 50, "start": (20, 40, 60), "state": True}
    seen = []

    def fake(build_, out, orientation, bot, seed=1, seconds=10, profile="desktop", actions=None):
        out.mkdir(parents=True, exist_ok=True)
        (out / "start.png").write_bytes(_png(script["start"]))
        (out / "end.png").write_bytes(_png((90, 90, 90)))
        acts = actions if actions is not None else Q._actions(bot, seed, seconds, 360, 640)
        seen.append({"bot": bot, "seed": seed, "profile": profile, "replay": actions is not None, "n": len(acts)})
        errs = list(script["err"].get(bot, []))
        return {"bot": bot, "seed": seed, "profile": profile, "ok": not errs, "errors": errs, "warnings": [],
                "shots": ["start.png", "end.png"], "fps": [script["fps"]] * 3, "load_s": 1.2, "frames": 300,
                "state": {"score": 3} if script["state"] else {}, "events": ["game_over"] if script["state"] else [],
                "game_overs": 1, "restarts": 1, "actions": acts, "stuck_s": 0.0, "mem_mb": 30}
    monkeypatch.setattr(Q, "run_bot", fake)
    return {**st, "Q": Q, "build": build, "script": script, "seen": seen}


def _farm(q, **kw):
    return q["Q"].farm("default", q["sid"], build=q["build"], version=1, **kw)


def test_bots_are_seeded_replays(env):
    from app.gamedesk import qa as Q
    a, b, c = Q._actions("monkey", 1, 10, 360, 640), Q._actions("monkey", 1, 10, 360, 640), Q._actions("monkey", 2, 10, 360, 640)
    assert a == b and a != c and len(a) > 10                                    # same seed = the same play, exactly
    assert Q._actions("idle", 1, 10, 360, 640) == []
    assert {x["a"] for x in Q._actions("keys", 1, 10, 360, 640)} == {"key"}
    assert set(Q.PROFILES) == {"desktop", "mid_phone", "low_phone"} and Q.PROFILES["mid_phone"]["cpu"] == 4
    assert Q.diff_share(_png((10, 10, 10)), _png((10, 10, 10))) == 0 and Q.diff_share(_png((0, 0, 0)), _png((255, 255, 255))) == 1


def test_a_crash_becomes_one_numbered_bug_with_its_repro(q):
    Q = q["Q"]
    q["script"]["err"] = {"keys": ["SCRIPT ERROR: Cannot call method 'queue_free' on a null value."]}
    rep = _farm(q)
    assert rep["verdict"] == "FAIL" and rep["filed"][0]["what"] == "new" and len(rep["runs"]) == len(Q.PLAN)
    bugs = Q.bugs("default", q["sid"])
    b = bugs["bugs"][0]
    assert b["number"] == "B-0001" and b["severity"] == "crash" and "queue_free" in b["title"]
    assert b["repro"]["bot"] == "keys" and b["repro"]["seed"] == 1 and b["steps"] > 0 and bugs["crash_open"] == 1
    rep = _farm(q)                                                               # the same crash again = counted, not new
    assert Q.bugs("default", q["sid"])["bugs"][0]["seen"] >= 2 and len(Q.bugs("default", q["sid"])["bugs"]) == 1
    assert any(s["replay"] and s["bot"] == "keys" for s in q["seen"])          # its own repro was replayed exactly


def test_fix_closes_only_when_the_bot_cannot_find_it_and_regressions_reopen(q):
    Q, S = q["Q"], q["S"]
    q["script"]["err"] = {"keys": ["SCRIPT ERROR: Invalid access to property 'x' on a null value."]}
    _farm(q)
    res = Q.fix_bug("default", q["sid"], "B-0001")
    t = res["task"]
    assert res["bug"]["status"] == "fixing" and t["kind"] == "fix" and t["priority"] == 1
    assert t["criteria"][0]["by"] == "test" and "QA bot 'keys' (seed 1, desktop) no longer finds B-0001" == t["criteria"][0]["text"]
    with pytest.raises(Q.QaError, match="bot"):
        Q.set_bug("default", q["sid"], "B-0001", "fixed")                       # she cannot just say fixed for a bot bug
    q["script"]["err"] = {}
    rep = _farm(q)
    assert rep["fixed"] == ["B-0001"] and Q.bugs("default", q["sid"])["bugs"][0]["status"] == "fixed"
    q["script"]["err"] = {"keys": ["SCRIPT ERROR: Invalid access to property 'x' on a null value."]}
    rep = _farm(q)
    b = Q.bugs("default", q["sid"])["bugs"][0]
    assert b["status"] == "open" and b["regression"] == 1 and any("regression" in x for x in rep["blockers"])
    assert any(d["text"].startswith("QA v1: FAIL") for d in S.get("default", q["sid"])["decisions"])


def test_golden_screen_needs_her_ok_then_guards_the_look(q):
    Q = q["Q"]
    rep = _farm(q)
    assert rep["golden"]["verdict"] == "none" and any("NOT ASSESSED" in c for c in rep["concerns"])
    Q.approve_golden("default", q["sid"])
    rep = _farm(q)
    assert rep["golden"]["verdict"] == "same" and rep["verdict"] == "PASS"
    q["script"]["start"] = (250, 250, 250)
    rep = _farm(q)
    assert rep["golden"]["verdict"] == "different" and rep["verdict"] == "CONCERNS" and rep["golden"]["diff"] > 0.5


def test_speed_drop_and_a_silent_game_are_concerns(q):
    Q = q["Q"]
    _farm(q)
    q["script"]["fps"] = 20
    rep = _farm(q)
    assert any("speed dropped" in c for c in rep["concerns"]) and any(b["severity"] == "perf" for b in Q.bugs("default", q["sid"])["bugs"])
    q["script"]["state"] = False
    rep = _farm(q)
    assert any("reports no state" in c for c in rep["concerns"])


def test_not_assessed_is_never_a_pass(q, monkeypatch):
    Q = q["Q"]
    monkeypatch.setattr(Q, "_debug_build", lambda proj, qd: (None, "Godot ka debug Web template nahi mila"))
    rep = Q.farm("default", q["sid"])
    assert rep["verdict"] == "NOT ASSESSED" and "debug Web template" in rep["missing"][0]
    rel = q["build"].parent / "build"
    rel.mkdir()
    (rel / "index.html").write_text("x")
    rep = Q.farm("default", q["sid"], build=rel, version=1)
    assert any("release build" in c for c in rep["concerns"])                    # hidden errors are said out loud


def test_her_bug_report_gate_and_summary(q):
    Q, S = q["Q"], q["S"]
    b = Q.report_bug("default", q["sid"], "The jump button does nothing on my phone", "Redmi 9", "major")
    assert b["number"] == "B-0001" and b["source"] == "her"
    assert Q.set_bug("default", q["sid"], "B-0001", "wontfix")["status"] == "wontfix"
    q["script"]["err"] = {"monkey": ["SCRIPT ERROR: Out of bounds get index '5'."]}
    _farm(q)
    S.add_task("default", q["sid"], "Add a horn", milestone="proto")
    g = S.gate("default", q["sid"], "proto")
    assert g["verdict"] == "FAIL" and any("crash / blocker" in x for x in g["blockers"]) and g["facts"]["qa"]["verdict"] == "FAIL"
    assert "QA bots: FAIL" in S.summary("default", q["sid"])
    assert S.get("default", q["sid"])["qa"]["crash_open"] == 1


def test_nightly_runs_the_farm_on_the_fresh_build(q, monkeypatch):
    Q, S, svc = q["Q"], q["S"], q["svc"]
    got = {}
    monkeypatch.setattr(svc, "health", lambda: {"ready": True})
    monkeypatch.setattr(Q, "farm", lambda tenant, sid, proj=None, version=0, **k: got.update(proj=proj, version=version) or
                        {"verdict": "PASS", "filed": [], "fixed": []})
    res = S.nightly("default", q["sid"])
    assert res["ok"] and res["qa"]["verdict"] == "PASS" and got["version"] == 1 and got["proj"].name == "proj"


def test_debug_export_probe_and_guide(env):
    root = Path(__file__).resolve().parents[1]
    eng = (root / "app/gamedesk/engine.py").read_text()
    assert '"--export-debug" if debug else "--export-release"' in eng and "web_nothreads_debug.zip" in eng
    assert "templates/web_nothreads_debug.zip" in (root / "deploy/setup_godot.py").read_text()
    from app.gamedesk import ai, template
    assert "func state(key: String, value: Variant)" in template.PROBE and "func event(name: String)" in template.PROBE
    assert 'HoolaProbe.event("game_over")' in ai.GUIDE
    qa = (root / "app/gamedesk/qa.py").read_text()
    assert "c.focus()" in qa                                                     # keys only reach a focused canvas


def test_tool_api_and_ui(q):
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.main import app
    Q = q["Q"]
    q["script"]["err"] = {"tapper": ["SCRIPT ERROR: Division by zero error."]}
    _farm(q)
    hire.hire("default", "game_dev")
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    out = asyncio.run(tools.HANDLERS["game_qa"](ctx, action="bugs"))
    assert out["crash_open"] == 1 and out["bugs"][0]["number"] == "B-0001" and out["last"]["verdict"] == "FAIL"
    out = asyncio.run(tools.HANDLERS["game_qa"](ctx, action="fix", bug="B-0001"))
    assert out["task"] == "T-0001"
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_qa"](staff, action="run"))
    assert tools.FAMILY_OF["game_qa"] == "gamedesk"
    for ask in ("mere game ki qa karo", "game ke bug dikhao", "game test chalao"):
        assert "gamedesk" in admit.route(ask), ask
    c = TestClient(app)
    d = c.get(f"/api/gamestudio/{q['sid']}/qa").json()
    assert d["open"] == 1 and d["last"]["verdict"] == "FAIL" and d["last"]["runs"][0]["shot_urls"]
    shot = c.get(d["last"]["runs"][0]["shot_urls"][0])
    assert shot.status_code == 200 and shot.headers["content-type"] == "image/png"
    assert c.get(d["last"]["runs"][0]["shot_urls"][0].replace("sig=", "sig=0")).status_code == 404
    assert c.post(f"/api/gamestudio/{q['sid']}/bugs", json={"title": "Coins vanish after level 2"}).json()["number"] == "B-0002"
    assert c.post(f"/api/gamestudio/{q['sid']}/bugs/B-0002/duplicate").json()["status"] == "duplicate"
    assert c.post(f"/api/gamestudio/{q['sid']}/qa/golden", json={}).status_code == 200
    assert c.post(f"/api/gamestudio/{q['sid']}/qa/run").json()["started"] is False      # worker off in tests
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "gsQa" in emp and "/qa/run" in emp
    assert "GameQaScreen" in (root / "lib/ui/game_qa_screen.dart").read_text()
    assert "gameQaRun" in (root / "lib/api.dart").read_text()


def test_every_build_is_played_as_a_debug_build_when_it_can_be(gd, monkeypatch):  # noqa: F811
    """Found on a real build: a crash on the Space key passed the release-build playtest and went live. Now each build is
    also exported with the debug template and THAT is played (the play link keeps the release build); without the
    template it plays the release build as before. The debug build is never kept."""
    from app.gamedesk import engine, playtest
    svc = gd["svc"]
    played = []
    orig_export = engine.export_web

    def export(job, holder=None, debug=False):
        if debug:
            (job / "build_debug").mkdir(parents=True, exist_ok=True)
            (job / "build_debug" / "index.html").write_text("dbg")
            return {"ok": True, "errors": []}
        return orig_export(job, holder)
    monkeypatch.setattr(engine, "export_web", export)
    monkeypatch.setattr(engine, "debug_template", lambda: True)
    orig_run = playtest.run
    monkeypatch.setattr(playtest, "run", lambda build, out, orientation="portrait", seconds=8: played.append(build.name) or orig_run(build, out, orientation))
    v = svc.start("default", "", "ek tap wala game jismein chai ka cup udta hai", "portrait")
    svc.run_job(v["id"])
    svc.approve("default", v["id"])
    svc.run_job(v["id"])
    assert played == ["build_debug"] and svc.get("default", v["id"])["status"] == "done"
    vdir = svc._vdir(svc._get("default", v["id"]), 1)
    assert not (vdir / "build_debug").exists() and (vdir / "build" / "index.html").is_file()
    monkeypatch.setattr(engine, "debug_template", lambda: False)
    played.clear()
    svc.change("default", v["id"], "faster")
    svc.run_job(v["id"])
    assert played == ["build"]
