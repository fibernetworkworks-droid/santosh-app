"""v0.395 GAME BIBLE + SPECS AS DATA (Hoola Game Engine plan, Phase 3): templates per kind, validators in code,
seeded balance simulation, curve-made numbers, drafts for her OK, the Bible inside the game (HoolaBible.DATA) and a
data-only rebuild with no model call. Godot and the model are faked (the v0.370 / v0.386 fixtures)."""
import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import GAME, gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)

PAL = ["#101820", "#FFB000", "#E4572E", "#29BF12"]


def _base(B, st_):
    B.set_section("default", st_["sid"], "style", {"palette": PAL, "tone": "bright, kind"})
    B.set_section("default", st_["sid"], "terms", {"glossary": {"Chai": "tea"}, "banned": ["kill"]})
    B.set_entity("default", st_["sid"], "enemy", {"id": "bat", "name": "Red Bat", "tier": 1, "hp": 20, "damage": 5,
                                                  "attack_rate": 0.5, "accuracy": 0.5, "color": "#E4572E"})
    B.set_entity("default", st_["sid"], "enemy", {"id": "crow", "name": "Storm Crow", "tier": 3, "hp": 60, "damage": 9,
                                                  "attack_rate": 0.8, "accuracy": 0.6, "color": "#101820"})
    B.set_entity("default", st_["sid"], "level", {"id": "l1", "name": "Market", "order": 1, "duration_s": 40,
                                                  "waves": [{"enemy": "bat", "count": 3, "at_s": 2}], "reward_coins": 20})
    return B.set_entity("default", st_["sid"], "level", {"id": "l2", "name": "Rooftops", "order": 2, "duration_s": 60,
                                                         "waves": [{"enemy": "crow", "count": 6, "at_s": 3}], "reward_coins": 30})


@pytest.fixture
def bb(st):  # noqa: F811
    from app.gamedesk import bible as B
    B.ensure_table()
    return {**st, "B": B}


def test_templates_shape_every_entity(bb):
    B = bb["B"]
    e, errs = B.clean_entity("enemy", {"name": "Red Bat", "hp": "40", "junk": 1})
    assert not errs and e["id"] == "red_bat" and e["hp"] == 40 and "junk" not in e and e["behaviour"] == "chase"
    assert set(e) == {"id", *B.KINDS["enemy"]["fields"]}                    # the 50th enemy has the shape of the 1st
    _e, errs = B.clean_entity("enemy", {"id": "x", "name": "X", "hp": 0, "behaviour": "fly", "color": "red"})
    assert any("hp = 0" in x for x in errs) and any("behaviour" in x for x in errs) and any("colour" in x for x in errs)
    _e, errs = B.clean_entity("item", {"id": "gem", "name": "Gem", "price_inr": 99})
    assert any("real money" in x for x in errs)


def test_validators_refuse_bad_changes(bb):
    B, sid = bb["B"], bb["sid"]
    v = _base(B, bb)
    assert v["version"] == 6 and not v["check"]["errors"]
    with pytest.raises(B.BibleError, match="palette"):                      # style lock
        B.set_entity("default", sid, "enemy", {"id": "ghost", "name": "Ghost", "color": "#123456"})
    with pytest.raises(B.BibleError, match="not in the Bible"):             # broken reference
        B.set_entity("default", sid, "level", {"id": "l3", "name": "Sky", "order": 3, "waves": [{"enemy": "dragon", "count": 1}]})
    with pytest.raises(B.BibleError, match="banned"):
        B.set_entity("default", sid, "quest", {"id": "q1", "name": "Kill them all", "goal": "defeat", "target": "bat"})
    B.set_entity("default", sid, "quest", {"id": "q1", "name": "First flight", "goal": "defeat", "target": "bat"})
    B.set_entity("default", sid, "quest", {"id": "q2", "name": "Second", "requires": ["q1"]})
    with pytest.raises(B.BibleError, match="quest loop"):
        B.set_entity("default", sid, "quest", {"id": "q1", "name": "First flight", "requires": ["q2"]})
    with pytest.raises(B.BibleError, match="real-money"):
        B.set_entity("default", sid, "item", {"id": "box", "name": "Lucky", "notes": "a loot box for coins"})
    v = B.set_entity("default", sid, "enemy", {"id": "bat2", "name": "Red Bat", "color": "#E4572E", "tier": 1})
    assert any("used by" in w for w in v["check"]["warnings"])               # a warning is shown, not refused
    assert v["version"] == 9                                                 # refused changes were never saved


def test_simulation_is_seeded_and_flags_spikes(bb):
    B, sid = bb["B"], bb["sid"]
    _base(B, bb)
    a = B.sim("default", sid, 200)
    b = B.sim("default", sid, 200)
    assert a["ok"] and a == b and a["seed"] == b["seed"]                    # same Bible = same numbers
    l1, l2 = a["levels"]
    assert l1["win_rate"] > 0.9 and l2["win_rate"] < l1["win_rate"]
    assert any("spike" in f or "too hard" in f for f in a["flags"]), a["flags"]
    B.set_section("default", sid, "player", {"hp": 1000, "damage": 40})
    c = B.sim("default", sid, 200)
    assert c["seed"] != a["seed"] and c["levels"][1]["win_rate"] > l2["win_rate"]
    B.set_entity("default", sid, "item", {"id": "wings", "name": "Wings", "tier": 1, "effect": "speed", "price": 45, "color": "#FFB000"})
    B.set_entity("default", sid, "item", {"id": "crown", "name": "Crown", "tier": 9, "effect": "life", "price": 99999, "color": "#FFB000"})
    e = B.sim("default", sid, 100)
    items = {i["id"]: i for i in e["economy"]["items"]}
    assert items["wings"]["levels_to_afford"] in (1, 2) and items["crown"]["levels_to_afford"] is None
    assert any("Crown costs 99999" in f for f in e["flags"])


def test_curves_make_the_numbers_not_the_model(bb, monkeypatch):
    from app.gamedesk import ai
    B, sid = bb["B"], bb["sid"]
    _base(B, bb)
    monkeypatch.setattr(ai, "ask", lambda system, prompt, max_tokens=0: json.dumps([
        {"id": "moth", "name": "Night Moth", "tier": 2, "hp": 99999, "behaviour": "zigzag", "color": "#29BF12"},
        {"id": "bat", "name": "Copy Bat", "tier": 4, "behaviour": "dash", "color": "#E4572E"},
        {"id": "bad", "name": "Bad", "tier": 2, "behaviour": "teleport", "color": "#29BF12"}]))
    v = B.generate("default", sid, "enemy", 3, "night enemies")
    d = v["draft"]
    assert v["version"] == 6 and [e["id"] for e in d["add"]] == ["moth", "bat_2"]          # invalid one dropped, id kept unique
    moth = d["add"][0]
    assert moth["hp"] == round(20 * 1.35) and moth["hp"] != 99999                             # curve, not the model
    assert d["add"][1]["hp"] == round(20 * 1.35 ** 3)
    v = B.accept("default", sid, ["moth"])
    assert v["version"] == 7 and not v["draft"] and [e["id"] for e in v["data"]["entities"]["enemy"]] == ["bat", "crow", "moth"]
    B.set_section("default", sid, "curves", {"enemy": {"hp": [30, 1.5]}})
    v = B.recurve("default", sid, "enemy")
    hp = {e["id"]: e["hp"] for e in v["data"]["entities"]["enemy"]}
    assert hp == {"bat": 30, "crow": round(30 * 1.5 ** 2), "moth": 45}
    with pytest.raises(B.BibleError, match="growth"):
        B.set_section("default", sid, "curves", {"enemy": {"hp": [30, 9]}})


def test_draft_goes_stale_and_seed_from_design(bb, monkeypatch):
    from app.gamedesk import ai
    B, sid = bb["B"], bb["sid"]
    monkeypatch.setattr(ai, "ask", lambda system, prompt, max_tokens=0: json.dumps({
        "meta": {"title": "Rickshaw Racer", "pillars": ["speed", "city"]}, "style": {"palette": PAL + ["nothex"]},
        "player": {"hp": 80}, "entities": {"enemy": [{"id": "potholes", "name": "Pothole", "tier": 1, "color": "#999999"}],
                                           "level": [{"id": "l1", "name": "Dadar", "order": 1, "waves": [{"enemy": "potholes"}, {"enemy": "ghost"}]}]}}))
    v = B.seed("default", sid)
    rep = v["draft"]["replace"]
    assert rep["style"]["palette"] == PAL and rep["entities"]["enemy"][0]["color"] == PAL[0]   # kept inside the palette
    assert [w["enemy"] for w in rep["entities"]["level"][0]["waves"]] == ["potholes"]           # broken ref dropped
    assert v["version"] == 0                                                                    # a draft, not the Bible
    B.set_section("default", sid, "meta", {"genre": "racing"})                                 # the Bible moves under it
    with pytest.raises(B.BibleError, match="badal gayi"):
        B.accept("default", sid)
    B.reject("default", sid)
    with pytest.raises(B.BibleError, match="draft"):
        B.accept("default", sid)


def test_bible_goes_into_the_game_and_data_rebuild_needs_no_model(bb):
    B, sid, svc = bb["B"], bb["sid"], bb["svc"]
    _base(B, bb)
    code_calls = bb["calls"]["change"] + bb["calls"]["code"]
    B.apply("default", sid)
    svc.run_job(bb["gid"])
    g = svc.get("default", bb["gid"])
    assert g["version"] == 2 and bb["calls"]["change"] + bb["calls"]["code"] == code_calls      # no model call
    proj = svc._vdir(svc._get("default", bb["gid"]), 2) / "proj"
    src = (proj / "hoola_bible.gd").read_text()
    assert src.startswith("extends Node") and 'HoolaBible="*res://hoola_bible.gd"' in (proj / "project.godot").read_text() and "const VERSION := 6" in src and '"Red Bat"' in src
    assert '"by_id"' in src and "\t" in src and not __import__("app.gamedesk.guard", fromlist=["problems"]).problems(
        {"main.gd": GAME, "hoola_bible.gd": src})
    v = B.view("default", sid)
    assert v["applied"] == 6
    p = bb["S"].get("default", sid)
    assert p["bible"]["version"] == 6 and p["bible"]["applied"] == 6 and p["versions"][0]["bible"] == 6
    # a task build also carries the Bible, and the model's copy of it is replaced by Hoola's own
    bb["S"].add_task("default", sid, "Faster bats")
    bb["S"].start_task("default", sid)
    svc.run_job(bb["gid"])
    assert '"Red Bat"' in (svc._vdir(svc._get("default", bb["gid"]), 3) / "proj" / "hoola_bible.gd").read_text()
    with pytest.raises(B.BibleError):
        B.set_entity("default", sid, "enemy", {"id": "x1", "name": "Bad", "color": "#000001"})
    assert B.view("default", sid)["applied"] == 6


def test_gd_strings_are_escaped(bb):
    B = bb["B"]
    src = B.gd({**B.empty(), "meta": {"title": 'Say "hi"\\\n<b>', "pillars": []}}, 1)
    assert '"Say \\"hi\\"\\\\\\n<b>"' in src


def test_tool_api_and_routing(bb):
    from app.agent import admit, prompts, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.main import app
    B, sid = bb["B"], bb["sid"]
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    with pytest.raises(tools.ToolError, match="hire"):
        asyncio.run(tools.HANDLERS["game_bible"](ctx, action="show"))
    hire.hire("default", "game_dev")
    asyncio.run(tools.HANDLERS["game_bible"](ctx, action="section", section="style", value={"palette": PAL}))
    out = asyncio.run(tools.HANDLERS["game_bible"](ctx, action="set", kind="enemy",
                                                   entity={"id": "bat", "name": "Red Bat", "color": "#E4572E"}))
    assert out["version"] == 2 and out["entities"]["enemy"][0]["name"] == "Red Bat"
    with pytest.raises(tools.ToolError, match="palette"):
        asyncio.run(tools.HANDLERS["game_bible"](ctx, action="set", kind="enemy", entity={"id": "b2", "name": "B", "color": "#000002"}))
    tpl = asyncio.run(tools.HANDLERS["game_bible"](ctx, action="template", kind="level"))
    assert "waves" in tpl["fields"]
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_bible"](staff, action="apply"))
    assert tools.FAMILY_OF["game_bible"] == "gamedesk"
    c = TestClient(app)
    r = c.get(f"/api/gamestudio/{sid}/bible").json()
    assert r["version"] == 2 and "enemy" in r["templates"] and r["check"]["errors"] == []
    r = c.post(f"/api/gamestudio/{sid}/bible/entity", json={"kind": "enemy", "entity": {"id": "crow", "name": "Crow", "color": "#101820"}})
    assert r.status_code == 200 and r.json()["counts"]["enemy"] == 2
    assert c.post(f"/api/gamestudio/{sid}/bible/entity", json={"kind": "enemy", "entity": {"id": "z", "name": "Z", "color": "#000003"}}).status_code == 400
    assert c.delete(f"/api/gamestudio/{sid}/bible/entity/enemy/crow").json()["counts"]["enemy"] == 1
    assert c.post(f"/api/gamestudio/{sid}/bible/simulate", json={"runs": 50}).json()["ok"]
    assert c.post(f"/api/gamestudio/{sid}/bible/nope", json={}).status_code == 404
    for ask in ("game bible mein naya enemy jodo", "mere game ka balance pass karo", "level design dikhao"):
        assert "gamedesk" in admit.route(ask), ask
    assert "`game_bible`" in prompts.system_text({"gamedesk"})
    root = Path(__file__).resolve().parents[2]
    assert "gsBible" in (root / "server/app/static/console/employees.js").read_text()
    assert "GameBibleScreen" in (root / "lib/ui/game_bible_screen.dart").read_text()
    assert "gameBible(" in (root / "lib/api.dart").read_text()


def test_class_name_helpers_work_after_the_import_step(env):
    """v0.395 banned class_name (a real run showed it 'not declared' headless). v0.406 found the root cause - no
    class cache without an import - so smoke() imports first and class_name is allowed again; only Hoola's own
    autoload names stay refused. (Rewritten from the v0.395 ban to the new truth, not deleted.)"""
    from app.gamedesk import ai, guard
    assert not guard.problems({"main.gd": "extends Node\n", "h.gd": "class_name H\nextends RefCounted\n"})
    bad = guard.problems({"main.gd": "extends Node\n", "h.gd": "class_name HoolaBible\nextends RefCounted\n"})
    assert bad and "Hoola's own name" in bad[0]
    assert "`class_name Foo`" in ai.GUIDE and 'preload("res://foo.gd")' in ai.GUIDE
    src = (Path(__file__).resolve().parents[1] / "app/gamedesk/engine.py").read_text()
    assert '"--import"' in src and src.index('"--import"') < src.index('"--quit-after"')
