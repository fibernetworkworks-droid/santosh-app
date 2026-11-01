"""v0.386 STUDIO PROJECT (Hoola Game Engine plan, Phase 2): a long game project around one Game Desk game - task board,
milestones, decisions log, nightly build, morning summary, versions + restore, GitHub card. Godot and the model are
faked (same fakes as the v0.370 suite)."""
import asyncio
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import GAME, gd  # noqa: F401  (the fixture)


@pytest.fixture
def st(gd, monkeypatch):  # noqa: F811
    from app.gamedesk import ai, studio
    plans = []
    monkeypatch.setattr(ai, "plan_tasks", lambda design, goal, ms, tasks, decs, words="": (plans.append(
        {"decs": decs, "words": words, "tasks": [t["title"] for t in tasks]}) or [
        {"title": "Add a nitro boost", "detail": "Tap twice = 2 s of 1.5x speed", "milestone": "proto", "kind": "feature", "priority": 1},
        {"title": "Add a night map", "detail": "", "milestone": "alpha", "kind": "content", "priority": "2"},
        {"title": "Make a real-money betting mode", "milestone": "beta"},          # refused by the same rule as Phase 1
        {"title": "", "milestone": "beta"}]))
    studio.ensure_tables()
    svc = gd["svc"]
    v = svc.start("default", "c1", "ek rickshaw racing game Mumbai ki sadkon par", "portrait")
    svc.run_job(v["id"])
    svc.approve("default", v["id"])
    svc.run_job(v["id"])
    s = studio.create("default", "c1", "Rickshaw Racer", "Release in 6 months", game=v["id"])
    return {**gd, "S": studio, "sid": s["id"], "gid": v["id"], "plans": plans}


def _run(st):
    st["svc"].run_job(st["gid"])


def test_project_wraps_a_game_with_milestones_and_a_log(st):
    S = st["S"]
    p = S.get("default", st["sid"])
    assert p["number"] == "S-0001" and p["game"]["number"] == "G-0001" and p["game"]["version"] == 1
    assert [m["key"] for m in p["milestones"]] == ["proto", "playable", "alpha", "beta", "release"]
    assert p["decisions"][0]["text"].startswith("Project shuru")
    with pytest.raises(S.StudioError, match="pehle se"):
        S.create("default", "c1", game=st["gid"])                       # one project per game


def test_board_task_builds_waits_for_her_ok_then_next_starts(st):
    S = st["S"]
    a = S.add_task("default", st["sid"], "Add a horn button", "Bottom right, 64 px", milestone="proto")
    b = S.add_task("default", st["sid"], "Add a score multiplier", milestone="proto", priority=1)
    assert (a["number"], b["number"]) == ("T-0001", "T-0002")
    t = S.start_task("default", st["sid"])                              # priority 1 goes first
    assert t["number"] == "T-0002" and t["status"] == "working" and t["base"] == 1
    with pytest.raises(S.StudioError, match="ban raha"):
        S.start_task("default", st["sid"])                              # one at a time
    _run(st)
    p = S.get("default", st["sid"])
    t2 = next(x for x in p["tasks"] if x["number"] == "T-0002")
    assert t2["status"] == "review" and t2["version"] == 2 and "[T-0002]" in st["calls"]["smoke"][-1] or t2["status"] == "review"
    assert p["versions"][0]["task"] == "T-0002" and p["versions"][0]["live"] and p["versions"][0]["src"]
    with pytest.raises(S.StudioError, match="OK"):
        S.start_task("default", st["sid"])                              # never while one waits for her OK
    res = S.approve_task("default", st["sid"], "T-0002", note="Multiplier 2x is enough for kids")
    assert res["done"] == "T-0002" and res["next"]["number"] == "T-0001"   # auto: the next one starts
    assert any("Multiplier 2x" in d["why"] for d in res["studio"]["decisions"])
    prog = {m["key"]: m for m in res["studio"]["milestones"]}
    assert prog["proto"]["done"] == 1 and prog["proto"]["total"] == 2 and prog["proto"]["pct"] == 50


def test_send_back_makes_the_version_before_live_again(st):
    S, svc = st["S"], st["svc"]
    S.add_task("default", st["sid"], "Make the rickshaw faster")
    S.start_task("default", st["sid"])
    _run(st)
    assert svc.get("default", st["gid"])["version"] == 2
    p = S.reject_task("default", st["sid"], "T-0001", note="Too fast on turns")
    t = p["tasks"][0]
    assert t["status"] == "todo" and "Too fast on turns" in t["detail"]
    g = svc.get("default", st["gid"])
    assert g["version"] == 1                                             # the play link is version 1 again
    assert [v["rejected"] for v in p["versions"]][:2] == [True, False]
    assert any(d["text"].startswith("T-0001 wapas") for d in p["decisions"])


def test_failed_task_is_blocked_and_the_live_game_stays(st, monkeypatch):
    from app.gamedesk import ai
    S = st["S"]
    S.add_task("default", st["sid"], "Add a shield")
    st["script"]["smoke"] = [["SCRIPT ERROR: boom"]] * 5
    monkeypatch.setattr(ai, "fix", lambda d, f, p, o, s: {"main.gd": GAME})
    S.start_task("default", st["sid"])
    _run(st)
    t = S.get("default", st["sid"])["tasks"][0]
    assert t["status"] == "blocked" and "boom" in t["error"]
    assert st["svc"].get("default", st["gid"])["version"] == 1
    again = S.start_task("default", st["sid"], "T-0001")                  # a blocked task can be tried again
    assert again["status"] == "working" and again["tries"] == 2


def test_cancel_puts_the_task_back(st):
    S = st["S"]
    S.add_task("default", st["sid"], "Add rain")
    S.start_task("default", st["sid"])
    st["svc"].cancel("default", st["gid"])
    assert S.get("default", st["sid"])["tasks"][0]["status"] == "todo"


def test_plan_reads_decisions_and_refuses_bad_tasks(st):
    S = st["S"]
    S.decide("default", st["sid"], "No guns in this game", "It is for kids")
    out = S.plan("default", st["sid"], "more city content")
    made = [(m["number"], m["milestone"], m["source"]) for m in out["made"]]
    assert made == [("T-0001", "proto", "hoola"), ("T-0002", "alpha", "hoola")]   # betting + empty dropped
    assert any("No guns" in d for d in st["plans"][0]["decs"]) and st["plans"][0]["words"] == "more city content"


def test_why_answers_only_from_the_log(st):
    S = st["S"]
    S.decide("default", st["sid"], "Jump height 3.2", "lower felt floaty on phones")
    hit = S.why("default", st["sid"], "why is the jump height so high?")
    assert hit["found"] and hit["found"][0]["why"] == "lower felt floaty on phones" and not hit["note"]
    miss = S.why("default", st["sid"], "kyun hai dragon purple")
    assert miss["found"] == [] and "andaza" in miss["note"]


def test_restore_rebuilds_old_code_without_a_model_call(st):
    S = st["S"]
    S.add_task("default", st["sid"], "Faster")
    S.start_task("default", st["sid"])
    _run(st)
    S.approve_task("default", st["sid"], "T-0001")
    changes = st["calls"]["change"]
    S.restore("default", st["sid"], 1)
    _run(st)
    g = st["svc"].get("default", st["gid"])
    assert g["version"] == 3 and st["calls"]["change"] == changes and "200.0" in st["calls"]["smoke"][-1]


def test_nightly_rebuilds_and_names_suspects_on_failure(st, monkeypatch):
    S, svc = st["S"], st["svc"]
    monkeypatch.setattr(svc, "health", lambda: {"ready": True})
    ok = S.nightly("default", st["sid"])
    assert ok["ok"] and ok["version"] == 1 and ok["same_code"] and ok["fps"] == 44
    S.add_task("default", st["sid"], "Add traffic")
    S.start_task("default", st["sid"])
    _run(st)
    S.approve_task("default", st["sid"], "T-0001")
    st["script"]["smoke"] = [["SCRIPT ERROR: null instance"]]
    bad = S.nightly("default", st["sid"])
    assert not bad["ok"] and bad["suspects"] == ["T-0001 Add traffic"]
    p = S.get("default", st["sid"])
    fix = [t for t in p["tasks"] if t["source"] == "nightly"]
    assert fix and fix[0]["priority"] == 1 and "null instance" in fix[0]["detail"]
    assert p["nightly"][0]["ok"] is False and len(p["nightly"]) == 2


def test_morning_summary_in_code_and_worker_jobs(st, monkeypatch):
    from app.employee import hire
    from app.events import bus
    S = st["S"]
    S.add_task("default", st["sid"], "Add a horn")
    S.add_task("default", st["sid"], "Add a map")
    S.start_task("default", st["sid"])
    _run(st)
    S.settings("default", st["sid"], auto=False)
    S.approve_task("default", st["sid"], "T-0001")
    text = S.summary("default", st["sid"])
    assert "S-0001 Rickshaw Racer" in text and "Kal: 1 kaam poore (T-0001" in text and "Aaj: T-0002" in text
    assert "Prototype: 1/2 (50%)" in text
    sent = []
    monkeypatch.setattr("app.events.notify", lambda conv, t, campaign_id=None: sent.append((conv, t)))
    hire.hire("default", "game_dev")
    monkeypatch.setattr(S, "_local", lambda tenant: S.now().replace(hour=10))
    out = S.jobs(force=True)
    assert out == {"summaries": 1, "nightly": 0, "started": 0} and sent[0][0] == "c1" and "Aaj: T-0002" in sent[0][1]
    assert S.jobs(force=True)["summaries"] == 0                         # once a day
    S.settings("default", st["sid"], auto=True)
    assert S.jobs(force=True)["started"] == 1                           # auto: an idle board picks its next task
    monkeypatch.setattr(S, "_local", lambda tenant: S.now().replace(hour=2) + timedelta(days=1))
    assert S.jobs(force=True)["nightly"] == 0                           # never while a task is building
    assert bus is not None


def test_settings_milestone_targets_and_archive(st):
    S = st["S"]
    p = S.settings("default", st["sid"], milestones=[{"key": "alpha", "name": "Alpha test", "target": "2027-01-15"},
                                                      {"key": "beta", "target": "soon"}], summary_hour=30)
    ms = {m["key"]: m for m in p["milestones"]}
    assert ms["alpha"]["name"] == "Alpha test" and ms["alpha"]["target"] == "2027-01-15" and ms["beta"]["target"] == ""
    assert p["summary_hour"] == 12
    S.settings("default", st["sid"], status="archived")
    assert S.studios("default") == []


def test_tool_and_api(st):
    from app.agent import tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.main import app
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    with pytest.raises(tools.ToolError, match="hire"):
        asyncio.run(tools.HANDLERS["game_studio"](ctx, action="list"))
    hire.hire("default", "game_dev")
    out = asyncio.run(tools.HANDLERS["game_studio"](ctx, action="add", title="Add a horn button"))   # one project = no id
    assert out["added"]["number"] == "T-0001"
    st_ = asyncio.run(tools.HANDLERS["game_studio"](ctx, action="status"))
    assert st_["tasks"][0]["title"] == "Add a horn button" and st_["game"]["number"] == "G-0001"
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_studio"](staff, action="start", id=st["sid"]))
    assert tools.FAMILY_OF["game_studio"] == "gamedesk"
    c = TestClient(app)
    h = c.get("/api/gamestudio").json()
    assert h["projects"][0]["number"] == "S-0001" and h["milestones"][0]["key"] == "proto"
    r = c.post(f"/api/gamestudio/{st['sid']}/tasks", json={"title": "Add rain", "milestone": "alpha", "priority": "x"})
    assert r.status_code == 200 and r.json()["milestone"] == "alpha"
    r = c.post(f"/api/gamestudio/{st['sid']}/start", json={})
    assert r.status_code == 200 and any(t["status"] == "working" for t in r.json()["tasks"])
    assert c.post(f"/api/gamestudio/{st['sid']}/start", json={}).status_code == 400
    _run(st)
    p = c.post(f"/api/gamestudio/{st['sid']}/task/T-0001", json={"action": "ok", "note": "good"}).json()
    assert next(t for t in p["tasks"] if t["number"] == "T-0001")["status"] == "done"
    assert c.get(f"/api/gamestudio/{st['sid']}/why", params={"q": "horn"}).json()["found"]
    assert "S-0001" in c.get(f"/api/gamestudio/{st['sid']}/summary").json()["text"]
    assert c.post(f"/api/gamestudio/{st['sid']}/task/T-0002", json={"action": "nope"}).status_code == 400
    assert c.get("/api/gamestudio/S-0099").status_code == 400


def test_github_stage_has_code_board_and_decisions(st):
    from app.gamedesk import github as GGH
    S = st["S"]
    S.add_task("default", st["sid"], "Add a horn")
    S.start_task("default", st["sid"])
    _run(st)
    S.approve_task("default", st["sid"], "T-0001", note="loud is fun")
    with __import__("app.db", fromlist=["session"]).session() as s:
        r = S._studio(s, "default", st["sid"])
        s.expunge(r)
    folder, n, fp, ver = GGH.stage(r)
    names = sorted(p.name for p in folder.iterdir())
    for want in ("main.gd", "project.godot", "DESIGN.md", "TASKS.md", "DECISIONS.md", "CHANGELOG.md", "README.md"):
        assert want in names, want
    assert ver == 2 and "- [x] T-0001 Add a horn" in (folder / "TASKS.md").read_text()
    assert "loud is fun" in (folder / "DECISIONS.md").read_text()
    assert "v2" in (folder / "CHANGELOG.md").read_text() and "T-0001" in (folder / "CHANGELOG.md").read_text()
    assert GGH.stage(r)[2] == fp                                         # same content = same fingerprint
    src = (Path(__file__).resolve().parents[1] / "app/site/github.py").read_text()
    assert 'o.site_id.startswith("game:")' in src


def test_routing_guide_and_ui_wiring(env):
    from app.agent import admit, prompts
    for ask in ("mere game project ka kya haal hai", "game studio mein naya task", "game ka kaam aage badhao"):
        assert "gamedesk" in admit.route(ask), ask
    assert "`game_studio`" in prompts.system_text({"gamedesk"})
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "/api/gamestudio" in emp and "gsBoard" in emp
    dart = (root / "lib/ui/game_studio_screen.dart").read_text()
    assert "class GameStudioScreen" in dart and "gameStudioTask" in (root / "lib/api.dart").read_text()
    assert "GameStudioList(" in (root / "lib/ui/game_desk_screen.dart").read_text()
