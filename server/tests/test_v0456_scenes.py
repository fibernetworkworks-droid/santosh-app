"""v0.456 SCENES AS CHECKED DATA - the ceiling (docs/GAME_MOAT_PLAN.md §5.2).

Every Hoola game was at most 12 GDScript files on one plain root node, building every node in code. Right for
match-3 / idle / runner, where one engine plus Bible data IS the game; false for a platformer, where the game IS its
scenes. So scenes become data: the model writes a SPEC, Hoola checks it and GENERATES the .tscn, and the real engine
loads it before she ever sees it.

THE SECURITY RESULT THAT SHAPES ALL OF THIS, measured in Godot 4.7.2 before the design: a
`[sub_resource type="GDScript"]` embedded in a .tscn RUNS, and the embedded script reached `DirAccess` - which
guard.py has banned in every .gd file since v0.370. A scene the model could write freehand is therefore a hole
straight through the only thing protecting her games. These tests pin that it is shut in three independent places:
the spec checker, the generator, and the build guard.
"""
from pathlib import Path

import pytest

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)

SCRIPTS = {"level.gd": "extends Node2D\n", "player.gd": "extends CharacterBody2D\n", "coin.gd": "extends Area2D\n"}
COIN = {"name": "Coin", "root": {"type": "Area2D", "name": "Coin", "script": "coin.gd", "children": [
    {"type": "CollisionShape2D", "name": "Shape", "shape": {"kind": "circle", "radius": 8}},
    {"type": "ColorRect", "name": "Dot", "props": {"size": [12, 12], "color": "#FFD23F"}}]}}


def _level(coins: int = 3) -> dict:
    return {"name": "Level1", "root": {"type": "Node2D", "name": "Level", "script": "level.gd", "children": [
        {"type": "CharacterBody2D", "name": "Player", "script": "player.gd", "props": {"position": [100, 300]},
         "children": [
             {"type": "CollisionShape2D", "name": "Shape", "shape": {"kind": "rect", "size": [24, 48]}},
             {"type": "ColorRect", "name": "Body", "props": {"size": [24, 48], "color": "#4CC2FF"}},
             {"type": "AnimationPlayer", "name": "Anim", "animations": [
                 {"name": "idle", "length": 0.6, "loop": True,
                  "tracks": [{"path": "Body:position", "keys": [[0, [0, 0]], [0.3, [0, -6]], [0.6, [0, 0]]]}]}]}]}]
        + [{"instance": "coin.tscn", "name": f"Coin{i}", "props": {"position": [160 + 40 * i, 250]}}
           for i in range(1, coins + 1)]}}


# ================================================================ the hole, shut in three places
SMUGGLE = [("source", "extends Node\nfunc _ready(): DirAccess.open('user://')"),
           ("script/source", "evil"), ("code", "evil"), ("script_source", "evil"), ("gdscript", "evil")]


def test_a_spec_may_never_carry_script_source():
    from app.gamedesk import scene as S
    for key, val in SMUGGLE:
        spec = {"name": "S1", "root": {"type": "Node2D", "name": "R",
                                       "children": [{"type": "Node", "name": "X", key: val}]}}
        bad = S.check(spec, {"level.gd"}, set())
        assert any("script source" in b for b in bad), f"{key!r} was NOT refused: {bad}"
        with pytest.raises(S.SceneError):
            S.build(spec, {"level.gd"}, set())


def test_the_generator_refuses_to_emit_an_embedded_script():
    """Defence in depth: this module is the only writer of a .tscn, but a bug in it must not become the hole."""
    from app.gamedesk import scene as S
    assert S.BANNED_TEXT.search('[sub_resource type="GDScript" id="x"]')
    assert S.BANNED_TEXT.search('script/source = "x"')
    assert S.BANNED_TEXT.search("Expression.new()") and S.BANNED_TEXT.search("ClassDB.instantiate")
    good = S.build(COIN, set(SCRIPTS), set())
    assert not S.BANNED_TEXT.search(good) and good.startswith("[gd_scene")


def test_the_build_guard_scans_scenes_even_though_hoola_wrote_them():
    from app.gamedesk import guard
    ok = {"main.gd": "extends Node\n"}
    assert guard.problems(ok, {"a.tscn": '[gd_scene load_steps=1 format=3]\n[node name="R" type="Node2D"]\n'}) == []
    smug = guard.problems(ok, {"a.tscn": '[gd_scene]\n[sub_resource type="GDScript" id="x"]\nscript/source = "e"\n'})
    assert any("may never carry script source" in p for p in smug)
    assert any("lowercase .tscn" in p for p in guard.problems(ok, {"Evil.TSCN": "[gd_scene"}))
    assert any("outside the game" in p for p in guard.problems(ok, {"a.tscn": '[gd_scene load_steps=1 format=3]\npath="res://../x"'}))
    assert any("not a Godot scene file" in p for p in guard.problems(ok, {"a.tscn": "extends Node\n"}))
    assert guard.problems(ok) == [], "a game with no scenes must be unaffected"


# ================================================================ the checker
def test_every_refusal_that_keeps_a_scene_checkable():
    from app.gamedesk import scene as S
    R = lambda **kw: {"name": "S1", "root": {"type": "Node2D", "name": "R", **kw}}   # noqa: E731
    cases = [
        ("unknown node type", R(children=[{"type": "NoSuchThing", "name": "X"}]), "hangs the load"),
        ("script not in the game", R(children=[{"type": "Node", "name": "X", "script": "evil.gd"}]), "not a file of this game"),
        ("instance not in the game", R(children=[{"instance": "nope.tscn", "name": "X"}]), "not a scene of this game"),
        ("type and instance", R(children=[{"type": "Node", "name": "X", "instance": "coin.tscn"}]), "not both"),
        ("duplicate siblings", R(children=[{"type": "Node", "name": "X"}, {"type": "Node", "name": "X"}]), "both called"),
        ("a path as a name", R(children=[{"type": "Node", "name": "../etc"}]), "not allowed"),
        ("a property we do not write", R(children=[{"type": "Node", "name": "X", "props": {"os_execute": "rm"}}]), "does not write the property"),
        ("animations on the wrong node", R(children=[{"type": "Node", "name": "X", "animations": [
            {"name": "a", "tracks": [{"path": "X:position", "keys": [[0, [0, 0]]]}]}]}]), "belong on an AnimationPlayer"),
        ("keys going backwards", R(children=[{"type": "AnimationPlayer", "name": "A", "animations": [
            {"name": "a", "tracks": [{"path": "B:position", "keys": [[1, [0, 0]], [0, [0, 0]]]}]}]}]), "forward in time"),
    ]
    for label, spec, want in cases:
        bad = S.check(spec, {"coin.gd"}, {"coin.tscn"})
        assert any(want in b for b in bad), f"{label}: not refused -> {bad}"
    assert any("cannot itself be an instance" in b
               for b in S.check({"name": "S1", "root": {"instance": "coin.tscn", "name": "R"}}, set(), {"coin.tscn"}))
    big = {"name": "S1", "root": {"type": "Node2D", "name": "R",
                                  "children": [{"type": "Node", "name": f"N{i}"} for i in range(S.MAX_NODES + 20)]}}
    assert any("split it" in b for b in S.check(big, set(), set()))
    assert S.check(COIN, set(SCRIPTS), set()) == [], "a good spec must pass cleanly"


def test_instancing_loops_and_the_root_scene_are_refused():
    from app.gamedesk import scene as S
    _, probs = S.build_all([{"name": "Loop", "root": {"type": "Node2D", "name": "R", "children": [
        {"instance": "loop.tscn", "name": "Me"}]}}], set(SCRIPTS))
    assert any("instancing itself" in p for p in probs)
    _, probs = S.build_all([{"name": "Main", "root": {"type": "Node2D", "name": "R"}}], set(SCRIPTS))
    assert any("own root scene" in p for p in probs)
    _, probs = S.build_all([COIN, dict(COIN)], set(SCRIPTS))
    assert any("both called" in p for p in probs)
    _, probs = S.build_all([{"name": f"S{i}", "root": {"type": "Node2D", "name": "R"}} for i in range(S.MAX_SCENES + 2)],
                           set(SCRIPTS))
    assert any("max" in p for p in probs)


# ================================================================ the generated file, against the measured format
def test_the_generated_tscn_matches_the_format_the_engine_wants():
    from app.gamedesk import scene as S
    files, probs = S.build_all([COIN, _level(2)], set(SCRIPTS))
    assert probs == [] and sorted(files) == ["coin.tscn", "level1.tscn"]
    lvl = files["level1.tscn"]
    nodes = [ln for ln in lvl.splitlines() if ln.startswith("[node ")]
    # measured in Godot 4.7.2: a child of the ROOT is parent=".", and deeper paths do NOT repeat the root's name
    assert nodes[0] == '[node name="Level" type="Node2D"]'
    assert '[node name="Player" type="CharacterBody2D" parent="."]' in nodes
    assert '[node name="Body" type="ColorRect" parent="Player"]' in nodes
    assert not any('parent="Level' in n for n in nodes), "the root's own name must never appear in a parent path"
    assert 'instance=ExtResource(' in lvl and 'path="res://coin.tscn"' in lvl
    assert lvl.count("[node name=") == 7                                  # root + player + 3 children + 2 coins
    steps = int(lvl.split("load_steps=")[1].split()[0])
    assert steps == lvl.count("[ext_resource ") + lvl.count("[sub_resource ") + 1
    assert 'type="Animation"' in lvl and 'type="AnimationLibrary"' in lvl and 'loop_mode = 1' in lvl
    assert "Color(0.298" in lvl and "Vector2(100.0, 300.0)" in lvl         # #4CC2FF and the position
    assert 'size = Vector2(24.0, 48.0)' in lvl                            # the RectangleShape2D


# ================================================================ proved in the real engine
def _godot() -> bool:
    from app.gamedesk import engine
    return bool(engine.find())


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_loads_the_generated_scenes_and_instances_multiply(tmp_path):
    """The ceiling, measured: a 25-node SPEC becomes 65 live nodes because each instance expands."""
    from app.gamedesk import scene as S
    files, probs = S.build_all([COIN, _level(20)], set(SCRIPTS))
    assert probs == []
    spec_nodes = files["level1.tscn"].count("[node name=")
    rep = S.verify(files, SCRIPTS, tmp_path / "job")
    assert rep["verdict"] == "PASS", rep
    assert rep["loaded"] == rep["of"] == 2
    lvl = next(r for r in rep["scenes"] if r["scene"] == "level1.tscn")
    coin = next(r for r in rep["scenes"] if r["scene"] == "coin.tscn")
    assert coin["nodes"] == 3 and coin["loaded"] is True
    assert spec_nodes == 25, spec_nodes
    assert lvl["nodes"] == 65, f"20 coins x 3 nodes + 5 own = 65, engine said {lvl['nodes']}"
    assert lvl["nodes"] > spec_nodes * 2, "instancing is what multiplies content - that is the point"
    assert lvl["animations"] == ["idle"], "the animation must really be in the loaded scene"


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_a_scene_the_engine_cannot_load_is_a_FAIL_not_a_pass(tmp_path):
    """An unknown node type HANGS Godot's load rather than erroring, so 'never finished' must itself fail."""
    from app.gamedesk import scene as S
    broken = S.build(COIN, set(SCRIPTS), set()).replace('type="Area2D"', 'type="NoSuchNodeTypeAtAll"')
    rep = S.verify({"coin.tscn": broken}, SCRIPTS, tmp_path / "bad")
    assert rep["verdict"] == "FAIL"
    assert not rep.get("loaded") or any(not r["loaded"] for r in rep.get("scenes", []))


# ================================================================ the flow, the build, the tool
def test_a_scene_reaches_a_build_only_after_her_tap(st, monkeypatch):  # noqa: F811
    from app.gamedesk import ai
    from app.gamedesk import scene as S
    from app.gamedesk import service as G
    monkeypatch.setattr(S, "verify", lambda *a, **k: {"verdict": "PASS", "scenes": [
        {"scene": "coin.tscn", "loaded": True, "nodes": 3, "animations": []}], "loaded": 1, "of": 1, "why": "ok"})
    monkeypatch.setattr(ai, "scene_spec", lambda *a, **k: dict(COIN))
    monkeypatch.setattr(S, "_scripts_of", lambda t, g: dict(SCRIPTS))
    assert S.for_game("default", st["gid"]) == {}, "no approved scene = a build exactly as before"
    out = S.propose("default", st["sid"], "a coin the player picks up")
    assert out["status"] == "draft" and out["nodes"] == 3 and out["verdict"] == "PASS"
    assert S.for_game("default", st["gid"]) == {}, "a DRAFT must not reach the build"
    S.approve("default", st["sid"], "Coin")
    got = S.for_game("default", st["gid"])
    assert sorted(got) == ["coin.tscn"] and got["coin.tscn"].startswith("[gd_scene")
    S.reject("default", st["sid"], "Coin")
    assert S.for_game("default", st["gid"]) == {}, "rejecting takes it back out"
    v = S.view("default", st["sid"])
    assert v["scenes"][0]["name"] == "Coin" and "TileMaps" in v["not_built"]
    assert "never writes a .tscn" in v["how"]


def test_a_scene_that_did_not_load_can_never_be_approved(st, monkeypatch):  # noqa: F811
    from app.gamedesk import ai
    from app.gamedesk import scene as S
    monkeypatch.setattr(S, "verify", lambda *a, **k: {"verdict": "FAIL", "scenes": [], "why": "it did not load"})
    monkeypatch.setattr(ai, "scene_spec", lambda *a, **k: dict(COIN))
    monkeypatch.setattr(S, "_scripts_of", lambda t, g: dict(SCRIPTS))
    out = S.propose("default", st["sid"], "a coin")
    assert out["status"] == "failed" and "nahi khula" in out["say"]
    with pytest.raises(S.SceneError, match="khula hi nahi"):
        S.approve("default", st["sid"], "Coin")


def test_the_model_is_told_the_rules_and_never_writes_a_scene():
    from app.gamedesk import ai
    assert "never write a .tscn" in ai.SCENE or "never writes a .tscn" in ai.SCENE.replace("You never write", "never write")
    assert "MAY NEVER CARRY SCRIPT SOURCE" in ai.SCENE and "escapes Hoola's code guard" in ai.SCENE
    assert "INSTANCES ARE HOW CONTENT SCALES" in ai.SCENE
    assert "TileMaps, 3D and shaders are NOT available" in ai.SCENE
    assert "SCENES (v0.456)" in ai.GUIDE and "Never write a .tscn yourself" in ai.GUIDE


def test_api_tool_and_routing(st, monkeypatch):  # noqa: F811
    import asyncio

    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.gamedesk import ai
    from app.gamedesk import scene as S
    from app.main import app
    from fastapi.testclient import TestClient
    monkeypatch.setattr(S, "verify", lambda *a, **k: {"verdict": "PASS", "scenes": [
        {"scene": "coin.tscn", "loaded": True, "nodes": 3, "animations": []}], "loaded": 1, "of": 1, "why": "ok"})
    monkeypatch.setattr(ai, "scene_spec", lambda *a, **k: dict(COIN))
    monkeypatch.setattr(S, "_scripts_of", lambda t, g: dict(SCRIPTS))
    hire.hire("default", "game_dev")
    c = TestClient(app)
    assert c.get(f"/api/gamedesk/scenes/{st['sid']}").json()["limits"]["scenes"] == S.MAX_SCENES
    assert c.post(f"/api/gamedesk/scenes/{st['sid']}", json={"words": "a coin"}).json()["status"] == "draft"
    assert c.post(f"/api/gamedesk/scenes/{st['sid']}/Coin/approve").json()["status"] == "approved"
    assert c.post(f"/api/gamedesk/scenes/{st['sid']}/Coin/reject").json()["status"] == "rejected"
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    lst = asyncio.run(tools.HANDLERS["game_scenes"](ctx, action="list", id=st["sid"]))
    assert lst["scenes"][0]["name"] == "Coin" and "TileMaps" in lst["not_built"]
    with pytest.raises(tools.ToolError, match="ek line"):
        asyncio.run(tools.HANDLERS["game_scenes"](ctx, action="new", id=st["sid"], words="x"))
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_scenes"](staff, action="approve", id=st["sid"], name="Coin"))
    assert tools.FAMILY_OF["game_scenes"] == "gamedesk"
    desc = next(t["description"] for t in tools.TOOLS if t["name"] == "game_scenes")
    assert "NEVER WRITES A .tscn" in desc and "escape the code guard" in desc and "NOT available" in desc
    for ask in ("mere game ka naya level scene banao", "platformer level chahiye"):
        assert "gamedesk" in admit.route(ask), ask
    root = Path(__file__).resolve().parents[2]
    assert "scenes" in (root / "server/app/gamedesk/service.py").read_text()
