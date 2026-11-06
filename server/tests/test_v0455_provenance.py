"""v0.455 PROVENANCE + THE UNDER-18 RULE SAID OUT LOUD (docs/GAME_MOAT_PLAN.md §5.1 items 3 and 4).

Steam's Content Survey, Unity's Asset Store and Fab all put the AI disclosure on whoever publishes, and she could not
answer honestly because nothing recorded which model made which file. And AI output may not be hers at all (US
Copyright Office Jan 2025: prompt-only output is not copyrightable; India s.2(d)(vi) + the 2026 rejection of an AI as
author), so the human acts Hoola already records are the only protectable part - they had just never been collected.

What these tests pin, because each is a way the record could lie:
- the model that wrote a build is recorded ON the build, per thread, and a FALLBACK to the cheap brain is named;
- a code-made sound (preset + seed) and a Blender mesh are NEVER counted as generative - declaring them on a survey
  would be a false statement;
- her own uploaded file is neither generated nor procedural: it is hers;
- only APPROVED assets ship, so a made-and-never-approved asset is off the survey;
- the live-generated answer is a plain No, because the game calls no model while it runs;
- the GDScript is printed as a JUDGEMENT CALL with both readings, never decided for her;
- nothing ever claims the declaration is correct;
- the DPDP under-18 rule is stated wherever telemetry is offered, with its one narrow school exception.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


# ================================================================ the model that wrote the code
def test_the_model_is_recorded_per_thread_and_a_fallback_is_named():
    import threading

    from app.gamedesk import ai
    assert ai.used() == []
    ai._mark("claude-opus-5-5")
    ai._mark("claude-opus-5-5")                                    # deduped
    ai._mark("fallback: the cheap brain, not Claude")
    got = ai.used()
    assert got == ["claude-opus-5-5", "fallback: the cheap brain, not Claude"]
    assert any("fallback" in m for m in got), "a different model must be named as one"
    assert ai.used() == [], "used() clears, so a caller records exactly its own call"
    out = []

    def other():
        ai._mark("some-other-model")
        out.append(ai.used())
    t = threading.Thread(target=other)
    t.start()
    t.join()
    ai._mark("mine")
    assert out[0] == ["some-other-model"] and ai.used() == ["mine"], "parallel builds must not mix records"
    assert "_mark(model)" in open("app/gamedesk/ai.py").read(), "the real call sites must mark"
    assert '"models": ai.used()' in open("app/gamedesk/service.py").read(), "a build must write it down"


def test_a_build_carries_its_models_and_an_old_build_says_it_did_not(st):  # noqa: F811
    from app.db import session
    from app.gamedesk import provenance as P
    from app.gamedesk import service as G
    c = P.code_record("default", st["gid"])
    assert c["runtime_generation"] is False and "calls no model while it runs" in c["runtime_note"]
    assert c["unrecorded"] is True and "before v0.455" in c["note"]      # the fixture built before the field existed
    with session() as s:
        g = s.get(G.GameProject, st["gid"])
        vers = [dict(v) for v in (g.versions or [])]
        vers[-1]["models"] = ["claude-opus-5-5"]
        g.versions = vers
    c = P.code_record("default", st["gid"])
    assert c["models_live_build"] == ["claude-opus-5-5"] and c["unrecorded"] is False
    assert "GDScript written by" in c["note"] and c["source_hash"]


# ================================================================ generated vs code-made vs hers
def _asset(st, key, kind, source, approved=1, model=None, cost=3.0, words="a red bird"):
    from app.db import session
    from app.gamedesk import assets as A
    A.ensure_table()
    with session() as s:
        a = A.GameAsset(tenant_id="default", studio_id=st["sid"], key=key, kind=kind, words=words,
                        spec={"seed": 7, "preset": "coin"} if source == "synth" else {},
                        status="approved" if approved else "draft", version=max(1, approved), approved=approved,
                        history=[{"v": max(1, approved), "file": f"{key}.png", "at": "2026-11-05T10:00:00",
                                  "source": source, "meta": {"model": model} if model else {}, "cost_inr": cost}])
        s.add(a)
    return key


def test_code_made_and_her_own_files_are_never_counted_as_generated(st):  # noqa: F811
    from app.gamedesk import provenance as P
    _asset(st, "hero", "sprite", "photogen", model="photogen-2")
    _asset(st, "coin_pick", "sfx", "synth", cost=0)
    _asset(st, "tree", "model", "blender", cost=0)
    _asset(st, "logo", "ui", "upload", cost=0)
    _asset(st, "unused", "sprite", "photogen", approved=0, model="photogen-2")
    a = P.assets_record("default", st["sid"])
    assert a["counts"] == {"in_the_game": 4, "generative": 1, "procedural": 2, "hers": 1, "unknown": 0,
                           "made_but_never_approved": 1}
    assert [x["key"] for x in a["generative"]] == ["hero"]
    assert {x["key"] for x in a["procedural"]} == {"coin_pick", "tree"}
    assert [x["key"] for x in a["hers"]] == ["logo"]
    assert "false statement" in a["procedural_warning"]
    assert "never approved" in a["note"]
    sfx = next(x for x in a["procedural"] if x["key"] == "coin_pick")
    assert sfx["seed"] == 7 and sfx["preset"] == "coin" and "no model" in sfx["how"]
    hero = a["generative"][0]
    assert hero["model"] == "photogen-2" and hero["prompt"] == "a red bird" and hero["cost_inr"] == 3.0


def test_an_unclassifiable_source_is_named_not_guessed(st):  # noqa: F811
    from app.gamedesk import provenance as P
    _asset(st, "odd", "sprite", "something_new", model=None)
    a = P.assets_record("default", st["sid"])
    assert len(a["unknown"]) == 1 and a["unknown"][0]["kind_of_making"] == "unknown"
    sv = P.steam_survey("default", st["sid"])
    assert any("cannot classify" in u for u in sv["unknowns"])


# ================================================================ the human record
def test_the_human_record_collects_her_acts_and_warns_when_it_is_thin(st):  # noqa: F811
    from app.gamedesk import provenance as P
    thin = P.human_record("default", st["sid"])
    assert thin["counts"]["total_acts"] < 5 and thin["thin_warning"]
    assert "not copyrightable" in thin["why_it_matters"] and "not legal advice" in thin["why_it_matters"]
    S = st["S"]
    from app.db import session
    with session() as s:
        r = S._studio(s, "default", st["sid"])
        for i in range(3):
            S._decide(r, f"jump feels better at 3.2 ({i})", why="tested both", by="her")
    _asset(st, "hero2", "sprite", "photogen", approved=2, model="photogen-2")   # she chose v2 of 2
    _asset(st, "mine", "ui", "upload", cost=0)
    S.add_task("default", st["sid"], "Make the coin sound softer", source="her")
    rec = P.human_record("default", st["sid"])
    # 3 of mine + "Project shuru" from create(), which IS her act and is correctly logged by="her"
    assert rec["counts"]["decisions"] == 4 and rec["counts"]["uploaded"] == 1
    assert sum(1 for d in rec["decisions_she_made"] if "jump feels better" in (d["text"] or "")) == 3
    assert any("Project shuru" in (d["text"] or "") for d in rec["decisions_she_made"])
    assert rec["counts"]["her_tasks"] >= 1 and rec["counts"]["total_acts"] >= 5
    assert rec["thin_warning"] == "", "with real acts recorded the warning must go"
    assert any(d["why"] == "tested both" for d in rec["decisions_she_made"])
    assert [p["key"] for p in rec["asset_versions_she_chose"]] == ["hero2"]


# ================================================================ the store answers
def test_steam_answers_are_drafted_never_decided_for_her(st):  # noqa: F811
    from app.db import session
    from app.gamedesk import provenance as P
    from app.gamedesk import service as G
    _asset(st, "hero", "sprite", "photogen", model="photogen-2")
    _asset(st, "tune", "music", "lyria", model="lyria-2")
    _asset(st, "coin_pick", "sfx", "synth", cost=0)
    with session() as s:
        g = s.get(G.GameProject, st["gid"])
        vers = [dict(v) for v in (g.versions or [])]
        vers[-1]["models"] = ["claude-opus-5-5"]
        g.versions = vers
    sv = P.steam_survey("default", st["sid"])
    assert sv["pre_generated"]["answer"] == "Yes"
    assert "2 generated asset(s)" in sv["pre_generated"]["draft"] and "approved by the developer" in sv["pre_generated"]["draft"]
    assert "NOT declared as AI" in sv["pre_generated"]["draft"] and "procedural generation, not" in sv["pre_generated"]["draft"]
    assert "photogen-2" in sv["pre_generated"]["models"] and "claude-opus-5-5" in sv["pre_generated"]["models"]
    assert sv["live_generated"] == {"answer": "No", "draft": sv["live_generated"]["draft"], "guardrails_needed": False}
    assert "calls no model while it runs" in sv["live_generated"]["draft"]
    jc = sv["judgement_calls"]
    assert len(jc) == 1 and jc[0]["item"] == "the game's own GDScript"
    assert jc[0]["one_reading"] and jc[0]["other_reading"] and "You do" in jc[0]["who_decides"]
    assert "YOUR promise to Valve" in sv["you_sign_it"] and "not legal advice" in sv["you_sign_it"]
    blob = str(sv).lower()
    assert "declaration is correct" not in blob and "you are compliant" not in blob


def test_no_generated_asset_means_no_tag(st):  # noqa: F811
    from app.gamedesk import provenance as P
    _asset(st, "coin_pick", "sfx", "synth", cost=0)
    d = P.disclosure_line("default", st["sid"])
    assert d["needs_tag"] is False and "No generative-AI content" in d["line"]
    assert "made by code, not by a model" in d["note"]
    _asset(st, "hero", "sprite", "photogen", model="photogen-2")
    d = P.disclosure_line("default", st["sid"])
    assert d["needs_tag"] is True and d["fab_tag"] == "CreatedWithAI"
    assert "sprite" in d["line"] and "1 asset" in d["line"] and "CreatedWithAI tag" in d["note"]


# ================================================================ the under-18 rule, said out loud
def test_the_under_18_rule_is_stated_wherever_telemetry_is_offered(st):  # noqa: F811
    from app.gamedesk import liveops as L
    from app.gamedesk import runtime as R
    txt = R.UNDER_18
    assert "UNDER 18" in txt and "section 9(3)" in txt and "200 crore" in txt
    assert "under 18, not under 13" in txt
    assert "educational institution" in txt and "not a published game" in txt
    assert R.settings("default", st["sid"])["under_18"] == txt
    assert L.dashboard("default", st["sid"])["under_18"] == txt


# ================================================================ API + tool + the sheet
def test_api_tool_and_sheet(st, monkeypatch):  # noqa: F811
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.gamedesk import provenance as P
    from app.main import app
    _asset(st, "hero", "sprite", "photogen", model="photogen-2")
    _asset(st, "coin_pick", "sfx", "synth", cost=0)
    hire.hire("default", "game_dev")
    c = TestClient(app)
    sheet = c.get(f"/api/gamedesk/provenance/{st['sid']}").json()
    assert sheet["assets"]["counts"]["generative"] == 1 and sheet["assets"]["counts"]["procedural"] == 1
    assert "recorded when the thing happened" in sheet["how_to_read_it"]
    assert sheet["steam"]["live_generated"]["answer"] == "No"
    assert c.get(f"/api/gamedesk/provenance/{st['sid']}/steam").json()["pre_generated"]["answer"] == "Yes"
    assert c.get("/api/gamedesk/provenance/nope").status_code == 400
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    out = asyncio.run(tools.HANDLERS["game_provenance"](ctx, action="sheet", id=st["sid"]))
    assert out["assets"]["generative"] == 1 and "false statement" in out["assets"]["procedural_warning"]
    assert "not copyrightable" in out["human"]["why_it_matters"]
    assert asyncio.run(tools.HANDLERS["game_provenance"](ctx, action="disclosure", id=st["sid"]))["needs_tag"] is True
    with pytest.raises(tools.ToolError, match="sheet"):
        asyncio.run(tools.HANDLERS["game_provenance"](ctx, action="nonsense", id=st["sid"]))
    assert tools.FAMILY_OF["game_provenance"] == "gamedesk"
    desc = next(t["description"] for t in tools.TOOLS if t["name"] == "game_provenance")
    assert "false statement" in desc and "she signs it" in desc and "NEVER say the declaration is correct" in desc
    for ask in ("steam survey ka jawab do", "game ka ai disclosure"):
        assert "gamedesk" in admit.route(ask), ask
    from pathlib import Path
    emp = (Path(__file__).resolve().parents[2] / "server/app/static/console/employees.js").read_text()
    assert "gsProv" in emp and "prov: gsProv" in emp and "gsPvBtn" in emp
    assert "these are what a store survey asks about" in emp and "not AI" in emp
