"""v0.821 HOOLA 3D CHARACTERS (owner: "GO COMPLEX 3D CHARACTERS BUILD"): the Hoola3D kit's v2 - jointed people /
robots / animals drawn in code (or her approved animated model) that walk, run, jump, strike, stagger, fall down,
wave and talk; a hero who strikes, foes with health, people who say their lines.

The wiring needs no engine. The REAL ENGINE half (skipped where Godot is not installed) proves what the characters
DO: legs swing opposite ways and stop, a strike lands once, a fallen figure stays down, two blows fell the foe in
front and never the one behind, a person says her lines in order, a real animated model plays its own clips."""
from __future__ import annotations

import re

import pytest

from app.gamedesk import guard, kit3d


def _godot() -> str:
    from app.gamedesk import engine
    return engine.find() or ""


# ================================================================ wiring
def test_the_kit_is_version_2_with_the_character_pieces():
    k = kit3d.kit()
    assert "const VERSION := 2" in k
    for piece in ("func look(", "func figure(", "func figure_from(", "func spawn_hero(", "func foe(", "func npc(",
                  "func take_act(", "func act_button(", "class Figure extends Node3D", "class Npc extends Node3D",
                  "signal enemy_defeated", "signal npc_talked", "signal strike", "func take_hit(", "func say("):
        assert piece in k, piece
    assert "\n    " not in k, "GDScript here is indented with tabs only"
    assert guard.problems({"main.gd": kit3d.proof_main(), kit3d.FILE: k}) == []


def test_the_old_pieces_are_untouched_for_games_already_built():
    k = kit3d.kit()
    # a game written against v1 calls these exactly so: same names, same argument order
    assert "func spawn_player(parent: Node, pos: Vector3, color: Color = Color(\"#FFB15C\"), speed: float = 6.0," in k
    assert "func enemy(parent: Node, pos: Vector3, patrol_to: Vector3 = Vector3.ZERO, speed: float = 2.5," in k
    assert "signal enemy_stomped(left: int)" in k and "enemy_stomped.emit(enemies_left)" in k


def test_every_look_the_model_is_told_about_exists_and_the_reverse():
    k = kit3d.kit()
    block = k[k.index("const LOOKS := {"):k.index("}\n", k.index("const LOOKS := {"))]
    have = set(re.findall(r'^\t"([a-z]+)": \{', block, re.M))
    told = set(re.findall(r'"([a-z]+)"', kit3d.API[kit3d.API.index("preset one of"):kit3d.API.index("and changes from")]))
    assert have == told and len(have) == 11, (have ^ told)
    for colour in re.findall(r'"(#[0-9A-Fa-f]+)"', block):
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}", colour), colour


def test_every_option_the_model_is_told_about_is_read_by_the_kit():
    k = kit3d.kit()
    for key in ("skin", "shirt", "pants", "shoes", "hair", "eyes", "hat_color", "height", "build", "hair_style", "hat",
                "outfit", "item", "style", "kind", "horns", "model", "attack"):
        assert f'"{key}"' in kit3d.API or key in kit3d.API, key
        assert re.search(rf'(?:s|spec)\.(?:get|has)\("{key}"|_col\(s, "{key}"', k), key
    for value in ("slim", "stocky", "long", "bun", "cap", "turban", "crown", "helmet", "antenna", "kurta", "dress",
                  "sword", "staff", "lamp", "robot", "animal"):
        assert f'"{value}"' in kit3d.API and f'"{value}"' in k, value
    for anim in ("attack", "hurt", "wave", "talk", "die"):
        assert f'"{anim}"' in kit3d.API and f'"{anim}":' in k[k.index("const ONE := {"):k.index("const ONE := {") + 200], anim


def test_the_api_names_only_what_the_kit_has():
    k = kit3d.kit()
    for name in set(re.findall(r"Hoola3D\.([a-z_0-9]+)\(", kit3d.API)):
        assert f"func {name}(" in k, name
    for sig in ("enemy_defeated", "npc_talked"):
        assert sig in kit3d.API and f"signal {sig}" in k
    assert "f.set_motion(" in kit3d.API and "func set_motion(" in k and "func play(" in k


def test_the_proof_game_uses_the_characters_and_still_writes_no_controller():
    main = kit3d.proof_main()
    for call in ("Hoola3D.spawn_hero(", "Hoola3D.foe(", "Hoola3D.npc(", "Hoola3D.figure(", "Hoola3D.npc_talked.connect("):
        assert call in main, call
    assert "CharacterBody3D" not in main and "Camera3D" not in main and "AnimationPlayer" not in main
    assert "strike" in kit3d.PROOF_DESIGN.lower() and "F to strike or talk" in kit3d.PROOF_DESIGN


def test_the_animated_model_the_engine_test_uses_is_on_disk_and_really_animated():
    from app.gamedesk import glbpack
    p = kit3d._DIR.parent / "library" / "kenney" / "platformer_character.glb"
    js, _bin = glbpack.split(p.read_bytes())
    names = {a.get("name") for a in js.get("animations", [])}
    assert {"idle", "walk", "jump"} <= names


# ================================================================ the real engine
@pytest.fixture(scope="module")
def kit_run():
    return kit3d.self_test()


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_every_look_is_built_and_a_figure_really_moves(kit_run):
    f = kit_run["checks"]["figures"]
    assert f["ok"], kit_run
    assert f["made"] == 11 and f["joints_min"] >= 7
    assert f["swing"] > 0.5 and f["opposite"], "a walking figure swings its legs, opposite ways"
    assert f["rest"] < 0.1, "a standing figure's legs come to rest"
    assert f["strikes"] == 1 and f["ended"] == "attack" and f["back"] == "idle", "one strike lands, then it stands again"
    assert f["tipped"] > 1.2 and f["still_down"], "a fallen figure lies down and stays down"
    assert f["quad_swing"] > 0.25, "an animal walks on four legs"


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_two_blows_fell_the_foe_in_front_only(kit_run):
    a = kit_run["checks"]["attack"]
    assert a["ok"], kit_run
    assert a["can"] and a["button"], "a hero with a sword can strike, and the action button shows"
    assert a["after_one"] == 1, "the first blow takes exactly one health"
    assert a["defeated"] == 1 and a["left"] == 1 and a["fell"] and a["freed"], "the second fells it, and it goes"
    assert a["behind_hp"] == 2, "a foe behind the hero is not hit"
    assert a["hp"] == 3, "striking costs the hero nothing"


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_a_person_says_her_lines_in_order(kit_run):
    n = kit_run["checks"]["npc"]
    assert n["ok"], kit_run
    assert n["heard"] == ["Dadi0", "Dadi1", "Dadi2", "Dadi2"], "lines in order, the last one repeats"
    assert n["shown"] == "Dadi: Then come to the temple", "the HUD shows what was said"
    assert n["far_said"] == 0, "a person far away says nothing"
    assert n["waved"] == "wave" and n["turned"] > 0.3, "she waves and turns to the player"


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_an_animated_model_plays_its_own_clips(kit_run):
    m = kit_run["checks"]["model"]
    assert m["ok"], kit_run
    assert abs(m["tall"] - 1.6) < 0.1, "the model is sized to the height asked for"
    assert (m["walking"], m["jumping"], m["idle"]) == ("walk", "jump", "idle")


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_the_old_rules_still_hold_with_the_new_kit(kit_run):
    c = kit_run["checks"]
    assert kit_run["ok"] and not kit_run["errors"], kit_run
    assert c["hit"]["hp"] == 2 and c["stomp"]["left"] == 0 and c["fall"]["fell"] >= 1 and c["coin"]["coins"] == 1
