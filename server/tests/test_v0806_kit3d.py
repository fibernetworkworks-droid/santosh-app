"""v0.806 HOOLA 3D KIT (owner: "GO 3D GAMEPLAY"): the 3D gameplay pieces every small 3D game needs, written once by
Hoola - player, camera, coins, enemies, goal, HUD with touch controls - riding ONLY in a game whose design is 3D.

Two halves: the wiring (no engine needed), and the REAL ENGINE (skipped where Godot is not installed): the kit's own
rules, and Hoola's proof game won by a test player that uses the same keys a person does."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from app.gamedesk import guard, kit3d, packs, template

SERVER = Path(__file__).resolve().parents[1]
ROOT = SERVER.parent


# ================================================================ wiring
@pytest.mark.parametrize("text, want", [
    ("a 3D runner in a courtyard", True), ("3-D maze", True), ("3 D racing", True), ("a third-person adventure", True),
    ("first person walk through a haveli", True), ("low-poly island", True), ("three-dimensional puzzle", True),
    ("a 2D platformer", False), ("match-3 with diyas", False), ("30 days of chai", False), ("level 3 dungeon", False),
    ("mp3 d player", False), ("", False)])
def test_what_counts_as_a_3d_game(text, want):
    assert kit3d.wants(text) is want, text


def test_the_kit_is_a_pack_and_an_autoload():
    assert "kit3d" in packs.PACKS and kit3d.FILE in packs.files()
    assert template.HOOLA_OWN[kit3d.FILE] == "Hoola3D"
    proj = template.files("T", "landscape", {"main.gd": "extends Node\n", kit3d.FILE: kit3d.kit()})["project.godot"]
    assert 'Hoola3D="*res://hoola_3d.gd"' in proj
    plain = template.files("T", "landscape", {"main.gd": "extends Node\n"})["project.godot"]
    assert "Hoola3D" not in plain, "a 2D game's project must not change"


def test_the_kit_and_the_proof_game_pass_hoolas_own_guard():
    assert guard.problems({"main.gd": kit3d.proof_main(), kit3d.FILE: kit3d.kit()}) == []
    k = kit3d.kit()
    for piece in ("func world(", "func ground(", "func block(", "func moving_block(", "func spawn_player(",
                  "func follow_camera(", "func coin(", "func enemy(", "func goal(", "func make_hud(", "func hurt(",
                  "func model(", "func reset(", "class Player extends CharacterBody3D", "class FollowCam extends Camera3D",
                  "signal coin_taken", "signal player_hit", "signal goal_reached", "InputEventScreenTouch", "KEY_SPACE"):
        assert piece in k, piece
    assert "\n    " not in k, "GDScript here is indented with tabs only"
    # the proof game builds ONLY from the kit: no controller, camera or input code of its own
    main = kit3d.proof_main()
    assert "CharacterBody3D" not in main and "Camera3D" not in main and "is_physical_key_pressed" not in main
    assert main.count("Hoola3D.") > 20


def test_every_api_line_names_something_the_kit_really_has():
    k = kit3d.kit()
    for name in set(re.findall(r"Hoola3D\.([a-z_0-9]+)\(", kit3d.API)):
        assert f"func {name}(" in k, name
    for name in ("coins", "coins_total", "enemies_left", "player", "playing"):
        assert re.search(rf"^var {name}\b", k, re.M), name
    for sig in re.findall(r"\b(coin_taken|player_hit|player_fell|goal_reached|enemy_stomped)\b", kit3d.API):
        assert f"signal {sig}" in k, sig
    assert "hud.message(" in kit3d.API and "func message(" in k and "func clear(" in k


def test_only_a_3d_design_is_told_about_the_kit(monkeypatch):
    from app.gamedesk import ai
    seen = []
    monkeypatch.setattr(ai, "ask", lambda system, prompt, max_tokens=16000, job="game_code": seen.append(prompt) or
                        "=== main.gd ===\nextends Node\n")
    ai.code("# Diya Run\n**Pitch:** a small 3D run round a courtyard.", "landscape", (1280, 720))
    ai.code("# Chai Hop\n**Pitch:** a 2D hop over rooftops.", "portrait", (720, 1280))
    ai.fix("# Diya Run\nA third-person game.", {"main.gd": "extends Node\n"}, ["x"], "landscape", (1280, 720))
    ai.change("# Chai Hop\n2D.", {"main.gd": "extends Node\n"}, "faster", "portrait", (720, 1280))
    assert "3D KIT" in seen[0] and "Hoola3D.spawn_player" in seen[0]
    assert "3D KIT" not in seen[1]
    assert "3D KIT" in seen[2]
    assert "3D KIT" not in seen[3]
    assert "3D kit" in ai.DESIGN, "the designer is told how to shape a 3D game"


def test_the_pack_rides_only_in_a_3d_game(env):
    from app.db import session
    from app.gamedesk import service as G
    G.ensure_table()
    ids = {}
    with session() as s:
        for key, brief, design in (("three", "ek 3D game banao", "# X\n3D courtyard"), ("two", "ek runner banao", "# Y\n2D runner")):
            r = G.GameProject(tenant_id="default", number="G-1", title=key, brief=brief, design=design, status="design_ready")
            s.add(r)
            s.flush()
            ids[key] = r.id
    got = packs.for_game("default", ids["three"])
    assert kit3d.FILE in got and got[kit3d.FILE][0] == kit3d.kit()
    assert kit3d.FILE not in packs.for_game("default", ids["two"])
    assert kit3d.for_game("someone-else", ids["three"]) is None, "another tenant's game is never read"


def test_a_saved_proof_game_is_a_real_game_in_her_list(env, tmp_path, monkeypatch):
    monkeypatch.setenv("GAME_DIR", str(tmp_path / "games"))
    monkeypatch.setenv("PUBLIC_BASE_URL", "")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.gamedesk import service as G
    job = tmp_path / "job"
    (job / "proj").mkdir(parents=True)
    (job / "proj" / "main.gd").write_text(kit3d.proof_main())
    (job / "build").mkdir()
    (job / "build" / "index.html").write_text("<!doctype html><title>g</title>")
    got = kit3d._keep("default", "", job, {"download_bytes": 10 * 1048576, "seconds": 5}, {"fps": 30, "load_s": 2, "shots": []})
    v = G.get("default", got["id"])
    assert v["status"] == "done" and v["version"] == 1 and v["title"] == "Diya Run 3D"
    assert (v.get("url") or "").startswith("/play/") and kit3d.wants(v["design"])
    path, _ctype = G.play_file(v["url"].split("/play/")[1].strip("/"), "index.html")
    assert path is not None and path.is_file(), "the play link serves the saved build"
    assert kit3d.newest_tenant() == "default"


def test_the_cli_and_the_server_job_exist():
    main = (SERVER / "app" / "gamedesk" / "__main__.py").read_text(encoding="utf-8")
    assert "proof3d" in main and "--save" in main
    ops = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text(encoding="utf-8")
    assert "- game_3d_proof" in ops and "app.gamedesk proof3d --save" in ops


# ================================================================ the real engine
def _godot() -> str:
    from app.gamedesk import engine
    return engine.find() or ""


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_the_kits_own_rules_hold():
    r = kit3d.self_test()
    assert r["ok"], r
    c = r["checks"]
    assert c["hit"]["hp"] == 2, "a guard's touch costs exactly one life"
    assert c["stomp"]["left"] == 0 and c["stomp"]["hp"] == 3, "landing on a guard removes it and costs nothing"
    assert c["fall"]["fell"] >= 1 and c["fall"]["y"] > -14, "a fall brings the player back"
    assert c["touch"]["walked_m"] > 3 and c["touch"]["jump_m"] > 1.2, "the stick walks, the button jumps"
    assert c["coin"]["coins"] == 1 and c["lift"]["top_y"] > 2.5


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_the_test_player_wins_the_proof_game(tmp_path):
    from app.gamedesk import engine
    job = tmp_path / "job"
    (job / "proj").mkdir(parents=True)
    for name, txt in template.files(kit3d.PROOF_TITLE, "landscape", {"main.gd": kit3d.proof_main(), kit3d.FILE: kit3d.kit()}).items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    smoke = engine.smoke(job)
    assert smoke["ok"], smoke
    r = kit3d.play_through(job)
    assert r["ok"], r
    assert r["state"] == 3 and r["coins"] >= 5 and r["hp"] > 0 and r["top_y"] >= 1.9 and r["moved_m"] > 15
    assert not (job / "proj" / "proof_bot.gd").exists(), "the test player never enters the game's own project"


@pytest.mark.skipif(not (_godot() and os.environ.get("HOOLA_CHROMIUM")), reason="needs Godot and a Chromium for the playtest")
def test_real_godot_and_browser_the_whole_proof_passes():
    from app.gamedesk import engine
    if engine.templates_dir() is None:
        pytest.skip("Godot's web export templates are not installed here")
    r = kit3d.proof()
    assert r["ok"], {k: r.get(k) for k in ("guard", "smoke", "export", "playtest", "played", "touch", "kit")}
    assert r["touch"]["score"] >= 1, "the on-screen stick collected a coin in a real browser"
