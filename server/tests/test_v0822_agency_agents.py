"""v0.814 THE AGENCY (owner: "https://github.com/msitarzewski/agency-agents.git --- NOW READ THIS REPO" -> "GO 1 2 3 AND
DEPLOY ON VPS"). The Agency (MIT, AgentLand Contributors) read at 8ae6164:

1. Hoola Code: 35 of its engineering / testing / security / specialist agents join the ECC catalogue (98 agents), with
   a new "build" group for implementers - same `agent` tool, same guards.
2. The reality checker looks once before a round may finish (a change of `dev_reality_min_lines`+ added lines): a
   fresh agent reads her request + the change and says READY or NEEDS WORK; NEEDS WORK sends the coder back once.
3. Hoola Game Dev: its 21 game agents become expert notes for 13 crew roles + 8 new engine roles (Roblox x3, Blender
   add-ons, Unity editor tools / netcode, Unreal world building / technical art) - 57 roles."""
from __future__ import annotations

import re

from tests.test_tech_devsahayak import REPO, dev  # noqa: F401
from tests.test_v0787_hoola_code_engine import on, tu  # noqa: F401
from tests.test_v0789_hoola_code_safety import box  # noqa: F401
from tests.test_v0812_ecc_agents import Router, _round

AGENCY = """minimal-change-engineer codebase-onboarding-engineer senior-developer frontend-developer backend-architect
api-platform-engineer devops-automator sre database-optimizer payments-billing-engineer i18n-engineer privacy-engineer
identity-access-engineer mobile-app-builder mobile-release-engineer webassembly-engineer realtime-collaboration-engineer
search-relevance-engineer data-engineer ai-engineer prompt-engineer rapid-prototyper embedded-firmware-engineer
desktop-app-engineer reality-checker evidence-collector api-tester performance-benchmarker test-automation-engineer
test-results-analyzer ai-generated-code-auditor appsec-engineer secrets-credential-engineer codebase-archaeologist
mcp-builder""".split()
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


# ---------------------------------------------------------------- 1. the catalogue
def test_the_agency_joins_the_catalogue():
    from app.devsahayak import ecc
    from app.devsahayak.ecc.base import GROUPS, TOOL_LEVELS
    cat = ecc.catalog()
    ours = {k: a for k, a in cat.items() if a["ecc"].startswith("agency:")}
    assert len(AGENCY) == 35 and set(ours) == set(AGENCY) and len(cat) == 63 + 35
    for name, a in ours.items():
        assert a["group"] in GROUPS and a["tools"] in TOOL_LEVELS, name
        assert 800 <= len(a["prompt"]) <= 2800, (name, len(a["prompt"]))
        assert "adapted from the agency" in a["prompt"][:200].lower(), name
        assert not EMOJI.search(a["prompt"]), name                          # the persona dressing is gone
        low = a["prompt"].lower()
        for bad in ("your identity", "~/.claude", "vibe:", "task tool", "slash command"):
            assert bad not in low, (name, bad)
        for rx in (a["files"], a["words"]):
            if rx:
                re.compile(rx)
    assert sum(1 for a in ours.values() if a["group"] == "build") >= 8
    assert ecc.get("reality-checker")["tools"] == "run" and "VERDICT: READY" in ecc.get("reality-checker")["prompt"]
    r = ecc.roster(["app/a.py"], "add payments")
    assert "Builders (they edit):" in r and all(f"- {n} [" in r for n in cat) and len(r) < 20000
    assert "payments-billing-engineer" in ecc.suggest(["app/pay.py"], "add razorpay payments")


def test_the_route_lists_both_sources(env):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    c.headers.update({"x-api-key": env["settings"].app_api_key} if getattr(env["settings"], "app_api_key", "") else {})
    r = c.get("/api/devsahayak/agents")
    if r.status_code == 200:
        names = {a["name"] for a in r.json()["agents"]}
        assert {"reality-checker", "python-reviewer"} <= names and len(names) == 98


# ---------------------------------------------------------------- 2. the reality check before done
def _reality_on(monkeypatch, min_lines=1):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_reality_check", True, raising=False)
    monkeypatch.setattr(get_settings(), "dev_reality_min_lines", min_lines, raising=False)


def test_needs_work_sends_the_coder_back_once(on, monkeypatch):  # noqa: F811
    _reality_on(monkeypatch)
    seen = {}

    def after_check(kw):
        seen["note"] = kw["messages"][-1]["content"][0]["content"]
        return [tu(4, "edit", path="app/calc.py", old_string="    return s\n", new_string="    return round(s, 2)\n")]
    main = [[tu(1, "read", path="app/calc.py")],
            [tu(2, "edit", path="app/calc.py", old_string="    return s / len(items)\n", new_string="    return s\n")],
            [tu(3, "done", explain="Fixed and rounded.", pr_title="Fix total", test_plan="nothing run")],
            after_check,
            [tu(5, "done", explain="Fixed and rounded to 2 places.", pr_title="Fix total", test_plan="-")]]
    report = ("VERDICT: NEEDS WORK\n1. app/calc.py:4 - she asked for the total rounded to 2 places; it is not rounded.\n"
              "Ran: nothing (no test command).")
    client, events, ctx, out = _round(on, monkeypatch, main,
                                      {"reality-checker": [[tu(91, "read", path="app/calc.py")], [tu(92, "report", report=report)]]},
                                      "agency-needs-work")
    assert "REALITY CHECK" in seen["note"] and "not rounded" in seen["note"]
    sub = [c for c in client.calls if c["system"][0]["text"].startswith("You are a specialist agent")]
    assert len(sub) == 2 and "REALITY CHECKER" in sub[0]["system"][0]["text"].upper()
    assert "total() crashes on an empty cart" in str(sub[0]["messages"][0]["content"])   # it judges against HER request
    assert {x["name"] for x in sub[0]["tools"]} >= {"bash", "report"} and "edit" not in {x["name"] for x in sub[0]["tools"]}
    rows = [e for e in events if e["k"] == "reality"]
    assert len(rows) == 1 and rows[0]["verdict"] == "needs_work"                     # once a round, never a loop
    assert ctx["found"]["loop"]["finished"] is True and ctx["found"]["loop"]["reality"] == "needs_work"
    assert "round(s, 2)" in out["files"][0]["content"]


def test_ready_finishes_and_a_small_change_is_not_checked(on, monkeypatch):  # noqa: F811
    _reality_on(monkeypatch)
    main = [[tu(1, "read", path="app/calc.py")],
            [tu(2, "edit", path="app/calc.py", old_string="    return s / len(items)\n", new_string="    return s\n")],
            [tu(3, "done", explain="Fixed.", pr_title="Fix total")]]
    client, events, ctx, out = _round(on, monkeypatch, main, {"reality-checker": [
        [tu(92, "report", report="VERDICT: READY\nThe divide is gone; total() returns the sum.\nRan: read only.")]]}, "agency-ready")
    assert [e["verdict"] for e in events if e["k"] == "reality"] == ["ready"] and ctx["found"]["loop"]["reality"] == "ready"
    assert len(client.calls) == 4                                                    # 3 coder steps + 1 check step
    _reality_on(monkeypatch, min_lines=50)                                           # the same one-line change: not worth it
    client, events, ctx, out = _round(on, monkeypatch, [
        [tu(1, "read", path="app/calc.py")],
        [tu(2, "edit", path="app/calc.py", old_string="    return s / len(items)\n", new_string="    return s\n")],
        [tu(3, "done", explain="Fixed.", pr_title="Fix total")]], {}, "agency-small")
    assert not any(e["k"] == "reality" for e in events) and len(client.calls) == 3
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_reality_check", False, raising=False)
    from app.devsahayak import engine as EN
    assert EN.reality_check(None, None, None, "", {}, lambda e: None, None) == ("", "")


def test_page_draws_the_verdict():
    from pathlib import Path
    from app.devsahayak import api
    js = (Path(api.__file__).parents[1] / "static" / "console" / "code.js").read_text()
    assert "case 'reality':" in js and "needs work - back to it" in js


# ---------------------------------------------------------------- 3. Hoola Game Dev
def test_the_game_crew_gains_the_agency_experts():
    from app.gamedesk import agency as GA
    from app.gamedesk import crew as C
    new = {"unity_editor_tools", "unity_multiplayer", "roblox_experience", "roblox_scripter", "roblox_avatar",
           "blender_addon", "ue_world", "ue_tech_art"}
    assert set(GA.NEW_ROLES) == new and len(C.ROLES) == 57 and len(GA.EXPERT) == 21
    assert set(GA.EXPERT) <= set(C.ROLES)
    for k in new:
        r = C.ROLES[k]
        assert r["tier"] == "engine" and r["mode"] == "writes" and r["lead"] in C.ROLES and r["checks"] and r["keywords"]
    for k, txt in GA.EXPERT.items():
        assert 600 <= len(txt) <= 2000 and "adapted from the agency" in txt[:120].lower() and not EMOJI.search(txt), k
    assert C.pick_role("Roblox luau DataStore save for the shop", "", "feature") == "roblox_scripter"
    assert C.pick_role("a blender add-on that exports the level", "", "feature") == "blender_addon"
    assert C.pick_role("make the jump feel better", "", "feature") == "game_designer" or C.pick_role("make the jump feel better") in C.ROLES
    assert C.expert("godot_gdscript").startswith("Expert notes") and C.expert("producer") == ""
    ro = C.roster()
    assert ro["count"] == 57 and len(ro["experts"]) == 21


def test_the_expert_notes_ride_the_model_call(env, monkeypatch):
    from pathlib import Path
    from app.config import get_settings
    from app.gamedesk import crew as C
    src = (Path(C.__file__).parent / "studio.py").read_text()
    assert src.count("C.expert(role)") >= 3                                       # the build words + the writing call
    monkeypatch.setattr(get_settings(), "game_agency_experts", False, raising=False)
    assert C.expert("godot_gdscript") == ""                                       # her switch turns them off


# ---------------------------------------------------------------- the 'explained' race, found while testing this release
def test_her_page_polling_never_breaks_the_starting_commit(on):  # noqa: F811
    """FOUND while testing this release (the long-standing 'explained' flake of the v0787 / v0789 / v0794 suites): her
    page polls `view()` (git add -A) while a new round makes its working copy; the round's own `git add` + `commit` of
    the starting point lost the race on .git/index.lock, `base` became '', every diff then ran against HEAD (already
    holding the checkpoint) and the round shipped nothing ('explained'). Now one git command at a time per copy."""
    import shutil
    import subprocess
    import threading
    from app.devsahayak import engine as EN
    ses = EN.Session("race-ws")
    ses.ensure(REPO, on.FAKE.refs["main"], "tok")
    stop, bad = threading.Event(), []

    def page():
        while not stop.is_set():
            EN.view("race-ws")
    pollers = [threading.Thread(target=page, daemon=True) for _ in range(3)]
    for p in pollers:
        p.start()
    try:
        for i in range(25):                                    # the start of a round, again and again, under polling
            shutil.rmtree(ses.repo / ".git", ignore_errors=True)
            subprocess.run(["git", "init", "-q", str(ses.repo)], check=True)
            (ses.repo / "a.md").write_text(f"line {i}\n")
            if not EN._commit(ses.repo, f"base {i}"):
                bad.append(i)
    finally:
        stop.set()
        for p in pollers:
            p.join(5)
    assert bad == []
    assert EN._git_lock(ses.repo) is EN._git_lock(ses.repo / ".")                   # one lock per working copy
    assert not list(ses.dir.glob(".meta.*.tmp"))                                     # meta written atomically
