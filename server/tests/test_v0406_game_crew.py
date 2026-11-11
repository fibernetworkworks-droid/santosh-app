"""v0.406 HOOLA GAME CREW + GO FIX (after studying Claude-Code-Game-Studios): 49 studio roles as data, a role and
acceptance criteria on every task, evidence stamped with the code, the lead's review (screenshots + code), writing
roles, team plans, milestone gates (PASS / CONCERNS / FAIL / NOT ASSESSED) and honest "not checked" everywhere."""
import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


@pytest.fixture
def cw(st, monkeypatch):  # noqa: F811
    monkeypatch.setenv("GAME_CREW_REVIEW", "off")
    from app.gamedesk import crew
    return {**st, "C": crew}


def test_roster_is_a_whole_studio(env):
    from app.gamedesk import crew as C
    r = C.roster()
    assert r["count"] == 57 and [len(t["roles"]) for t in r["tiers"]] == [3, 8, 23, 23]   # v0.814 +8 engine roles (The Agency)
    assert {"creative_director", "technical_director", "producer"} == {k for k, v in C.ROLES.items() if v["tier"] == C.D}
    for k, v in C.ROLES.items():
        assert not v["lead"] or v["lead"] in C.ROLES, k
        assert v["mode"] in ("builds", "writes") and v["checks"] and v["lens"], k
    assert all(x in C.ROLES for t in C.TEAMS.values() for x in t["roles"]) and len(C.TEAMS) == 9
    for words, role in (("Add a nitro boost to the player", "gameplay_programmer"), ("Fix the pause menu button", "ui_programmer"),
                        ("Night level with 3 waves", "level_designer"), ("Shop prices for coins", "economy_designer"),
                        ("It lags on my phone", "performance_analyst"), ("enemy patrol ai", "ai_programmer"),
                        ("Write the store description", "community_manager"), ("Hindi language for menus", "localization_lead")):
        assert C.pick_role(words) == role, words
    assert C.builds("gameplay_programmer") and not C.builds("sound_designer") and not C.builds("unity_specialist")
    assert C.reviewer("gameplay_programmer") == "lead_programmer" and C.reviewer("creative_director") == "producer"


def test_task_gets_role_criteria_and_evidence(cw):
    S, C = cw["S"], cw["C"]
    t = S.add_task("default", cw["sid"], "Add a nitro boost to the player", criteria=[{"text": "Nitro bar shows top left", "by": "screen"},
                                                                                       {"text": "It feels fast", "by": "her"}])
    assert t["role"] == "gameplay_programmer" and t["reviewer"] == "lead_programmer" and t["verdict"] == "NOT ASSESSED"
    by = [(c["text"], c["by"]) for c in t["criteria"]]
    assert by[:2] == [("Nitro bar shows top left", "screen"), ("It feels fast", "her")]
    assert sum(1 for c in t["criteria"] if c["by"] == "test") == 2                       # Hoola's automatic checks
    S.start_task("default", cw["sid"])
    assert "Gameplay Programmer" in cw["svc"]._get("default", cw["gid"]).pending["words"]
    assert "Done when: Nitro bar shows top left" in cw["svc"]._get("default", cw["gid"]).pending["words"]
    cw["svc"].run_job(cw["gid"])
    t = S.get("default", cw["sid"])["tasks"][0]
    tests = [c for c in t["criteria"] if c["by"] == "test"]
    assert all(c["status"] == "covered" and c["evidence"]["version"] == 2 and c["evidence"]["src"] for c in tests)
    assert t["verdict"] == "COMPLETE WITH NOTES" and not t["evidence_old"]
    S.approve_task("default", cw["sid"], "T-0001")
    t = S.get("default", cw["sid"])["tasks"][0]
    assert next(c for c in t["criteria"] if c["by"] == "her")["status"] == "covered"
    assert next(c for c in t["criteria"] if c["text"].startswith("Nitro bar"))["status"] == "untested"   # nobody saw it


def test_lead_review_reads_screens_and_cannot_touch_hers(cw, monkeypatch):
    from app.gamedesk import ai
    S = cw["S"]
    seen = {}

    def fake(system, text, images, max_tokens=0):
        seen.update(system=system, text=text, n=len(images))
        return json.dumps({"criteria": [{"i": 0, "status": "covered", "why": "bar visible"},
                                        {"i": 1, "status": "covered", "why": "model tries to judge feel"},
                                        {"i": 9, "status": "failed"}], "findings": ["Bar overlaps score"], "summary": "Mostly fine"})
    monkeypatch.setattr(ai, "ask_with_images", fake)
    S.add_task("default", cw["sid"], "Add a nitro boost to the player", criteria=[{"text": "Nitro bar shows", "by": "screen"},
                                                                                  {"text": "Feels fast", "by": "her"}])
    S.start_task("default", cw["sid"])
    cw["svc"].run_job(cw["gid"])
    v = S.review_task("default", cw["sid"], "T-0001")
    assert "Lead Programmer" in seen["system"] and "Code change" in seen["text"] and seen["n"] == 1
    assert v["criteria"][0]["status"] == "covered" and v["criteria"][0]["evidence"]["by"] == "lead_programmer"
    assert v["criteria"][1]["status"] == "untested"                                       # only her OK covers 'her'
    assert v["review"]["findings"] == ["Bar overlaps score"] and v["review"]["shots_seen"] == 1
    p = S.reject_task("default", cw["sid"], "T-0001", "bar too small")
    assert all(c["status"] == "untested" for c in p["tasks"][0]["criteria"]) and not p["tasks"][0]["review"]


def test_review_runs_by_itself_when_on(cw, monkeypatch):
    from app.gamedesk import ai
    S = cw["S"]
    monkeypatch.setenv("GAME_CREW_REVIEW", "on")
    calls = []
    monkeypatch.setattr(ai, "ask_with_images", lambda s, t, i, max_tokens=0: calls.append(1) or '{"criteria": [], "findings": []}')
    S.add_task("default", cw["sid"], "Add a horn button")
    S.start_task("default", cw["sid"])
    cw["svc"].run_job(cw["gid"])
    assert calls == [1] and S.get("default", cw["sid"])["tasks"][0]["review"]["by"]


def test_writing_role_writes_and_never_builds(cw, monkeypatch):
    from app.gamedesk import ai
    S = cw["S"]
    monkeypatch.setattr(ai, "ask", lambda system, prompt, max_tokens=0: "## Sounds\n- jump: short whoosh" if "Sound Designer" in system else "x")
    t = S.add_task("default", cw["sid"], "Make the sound list for jumps and coins", role="sound_designer")
    assert t["role_mode"] == "writes"
    builds = len(cw["calls"]["smoke"])
    S.start_task("default", cw["sid"])
    assert S.get("default", cw["sid"])["tasks"][0]["status"] == "working"
    S.write_task("default", t["id"])
    t = S.get("default", cw["sid"])["tasks"][0]
    assert t["status"] == "review" and "jump: short whoosh" in t["notes"] and len(cw["calls"]["smoke"]) == builds
    S.approve_task("default", cw["sid"], "T-0001")
    assert cw["svc"].get("default", cw["gid"])["version"] == 1                             # the game did not change


def test_team_plan_uses_only_the_team(cw, monkeypatch):
    from app.gamedesk import ai
    S = cw["S"]
    got = {}

    def plan(design, goal, ms, tasks, decs, words="", roles=None):
        got["roles"] = [r["key"] for r in roles]
        return [{"title": "Design the boss attack pattern", "milestone": "alpha", "role": "game_designer",
                 "criteria": [{"text": "Boss has 3 attacks", "by": "screen"}]},
                {"title": "Write the boss victory line", "milestone": "alpha", "role": "writer"}]     # writer not in combat
    monkeypatch.setattr(ai, "plan_tasks", plan)
    out = S.plan("default", cw["sid"], "a boss fight", team="combat")
    assert got["roles"] == cw["C"].TEAMS["combat"]["roles"]
    assert [m["role"] for m in out["made"]][0] == "game_designer" and out["made"][1]["role"] in got["roles"]
    assert out["made"][0]["criteria"][0]["text"] == "Boss has 3 attacks"
    with pytest.raises(S.StudioError, match="team ="):
        S.plan("default", cw["sid"], "", team="cooking")


def test_gate_counts_in_code(cw, monkeypatch):
    S, svc = cw["S"], cw["svc"]
    g = S.gate("default", cw["sid"], "alpha")
    assert g["verdict"] == "NOT ASSESSED" and "no tasks" in g["missing"][0]
    S.add_task("default", cw["sid"], "Add a horn button", milestone="proto")
    g = S.gate("default", cw["sid"], "proto")
    assert g["verdict"] == "CONCERNS" and any("still open" in c for c in g["concerns"]) and "never" not in g["note"]
    S.start_task("default", cw["sid"])
    cw["script"]["smoke"] = [["SCRIPT ERROR: boom"]] * 5
    svc.run_job(cw["gid"])
    g = S.gate("default", cw["sid"], "proto")
    assert g["verdict"] == "FAIL" and "stuck" in g["blockers"][0]
    assert S.get("default", cw["sid"])["gates"][0]["verdict"] == "FAIL"
    assert any(d["text"] == "Gate Prototype: FAIL" for d in S.get("default", cw["sid"])["decisions"])


def test_not_assessed_is_said_out_loud(cw, monkeypatch):
    S = cw["S"]
    from app.gamedesk import bible as B
    B.ensure_table()
    sim = B.sim("default", cw["sid"])
    assert sim["verdict"] == "NOT ASSESSED" and sim["missing"] and sim["note"].startswith("Nothing was simulated")
    S.add_task("default", cw["sid"], "Add a horn")
    text = S.summary("default", cw["sid"])
    assert "jaancha NAHI gaya" in text                                                     # no nightly = not 'all fine'
    monkeypatch.setattr(cw["svc"], "health", lambda: {"ready": False})
    S._night_safe("default", cw["sid"])
    p = S.get("default", cw["sid"])
    assert p["nightly"][0]["skipped"] and p["nightly"][0]["ok"] is None
    assert "NAHI chala" in S.summary("default", cw["sid"])


def test_godot_47_notes_in_the_code_guide(env):
    from app.gamedesk import ai
    for k in ("explicit `return`", "event.device == 0", "UPDATE_WIDTH_UNIT", "TileMapLayer", "instantiate()"):
        assert k in ai.GUIDE, k
    notes = (Path(__file__).resolve().parents[2] / "THIRD_PARTY_NOTICES.md").read_text()
    assert "Claude Code Game Studios" in notes and "Copyright (c) 2026 Donchitos" in notes


def test_tool_api_and_ui(cw, monkeypatch):
    from app.agent import tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.main import app
    hire.hire("default", "game_dev")
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    out = asyncio.run(tools.HANDLERS["game_studio"](ctx, action="crew"))
    assert out["count"] == 57 and "combat" in out["teams"]
    out = asyncio.run(tools.HANDLERS["game_studio"](ctx, action="add", title="Fix the pause menu button", criteria=["Pause shows a Resume button"]))
    assert out["added"]["role"] == "ui_programmer" and out["added"]["criteria"][0]["text"] == "Pause shows a Resume button"
    g = asyncio.run(tools.HANDLERS["game_studio"](ctx, action="gate", milestone_key="proto"))
    assert g["verdict"] == "CONCERNS"
    c = TestClient(app)
    assert c.get("/api/gamestudio/crew").json()["count"] == 57
    assert c.post(f"/api/gamestudio/{cw['sid']}/gate", json={"milestone": "beta"}).json()["verdict"] == "NOT ASSESSED"
    assert c.post(f"/api/gamestudio/{cw['sid']}/task/T-0001", json={"action": "review"}).status_code == 400   # not built yet
    r = c.post(f"/api/gamestudio/{cw['sid']}/tasks", json={"title": "Write patch notes", "role": "release_manager"})
    assert r.json()["role_mode"] == "writes"
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    for k in ("gsCrew", "data-gs-gate", "/api/gamestudio/crew", "gs-crit"):
        assert k in emp, k
    dart = (root / "lib/ui/game_studio_screen.dart").read_text()
    assert "role_name" in dart and "verdict" in dart and "gate" in dart
    assert "gameStudioGate" in (root / "lib/api.dart").read_text()
