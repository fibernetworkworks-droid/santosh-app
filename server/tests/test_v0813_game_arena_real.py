"""v0.813 GAME ARENA made runnable (owner: "GO ARENA"): the Arena had never scored a real game. Its tests replaced
`_one_card` with a stand-in, and the real one read `<version>/web` - a folder no build ever had - so the first real
run would have reported every game as "no playable build". Here the REAL `_one_card` runs on a real game row, and a
free self-check proves the Arena can measure a known-good game before any rupee is spent."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]
ROOT = SERVER.parent


@pytest.fixture
def arena(env, tmp_path, monkeypatch):
    monkeypatch.setenv("GAME_DIR", str(tmp_path / "games"))
    monkeypatch.setenv("PUBLIC_BASE_URL", "")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.gamedesk import arena as A
    from app.gamedesk import service as G
    G.ensure_table()
    A.ensure_tables()
    return A, G


def _game(G, tenant, with_build=True, folder="build"):
    from app.db import session
    with session() as s:
        r = G.GameProject(tenant_id=tenant, number="G-0001", title="T", brief="a game", status="done", pct=100, design="# T",
                          token="tok" + os.urandom(6).hex(), versions=[{"n": 1, "ok": True, "files": ["main.gd"], "at": "2026-11-11T10:00:00"}])
        s.add(r)
        s.flush()
        s.expunge(r)
    v = G._vdir(r, 1)
    (v / "proj").mkdir(parents=True)
    (v / "proj" / "main.gd").write_text("extends Node\n# tap to jump, collect coins, game_over\n")
    if with_build:
        (v / folder).mkdir(parents=True)
        (v / folder / "index.html").write_text("<!doctype html>")
    return r.id


def test_the_real_card_plays_the_build_folder_that_exists(arena, monkeypatch):
    A, G = arena
    gid = _game(G, A.TENANT)
    seen = []

    def play(build, orientation, out, seconds=12):
        seen.append(build)
        return {"started": True, "load_s": 1.0, "fps": 40.0, "errors": 0, "error_list": [], "responds": True,
                "reached_end": True, "events": ["game_over"], "state_keys": ["score"], "shots": [], "runs": 3, "frames": 100}
    monkeypatch.setattr(A, "play", play)
    monkeypatch.setattr(A, "judge", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no judge without pictures")))
    b = {"id": "b1", "genre": "runner", "orientation": "portrait", "brief": "x"}
    c = A._one_card(b, builder=lambda _b: (gid, 0.0, 0.0))
    assert len(seen) == 1 and seen[0].name == "build" and (seen[0] / "index.html").is_file()
    assert c["playable"] and c["started"] and c["responds"] and c["game"] == gid and c["dna"]
    assert "NOT ASSESSED" in c["fun"]


def test_a_game_with_no_build_is_said_plainly_and_nothing_is_played(arena, monkeypatch):
    A, G = arena
    monkeypatch.setattr(A, "play", lambda *a, **k: (_ for _ in ()).throw(AssertionError("nothing to play")))
    b = {"id": "b1", "genre": "runner", "orientation": "portrait", "brief": "x"}
    for gid in (_game(G, A.TENANT, with_build=False), _game(G, A.TENANT, folder="web")):   # 'web' is the old wrong folder
        c = A._one_card(b, builder=lambda _b, gid=gid: (gid, 0.0, 0.0))
        assert not c["started"] and not c["playable"] and c["errors"] == 0


def test_the_judge_can_be_left_out(arena, monkeypatch, tmp_path):
    A, G = arena
    gid = _game(G, A.TENANT)
    shot = tmp_path / "s.png"
    shot.write_bytes(b"\x89PNG....")
    monkeypatch.setattr(A, "play", lambda *a, **k: {"started": True, "errors": 0, "error_list": [], "responds": True, "reached_end": False,
                                                    "events": [], "state_keys": [], "shots": [shot]})
    called = []
    monkeypatch.setattr(A, "judge", lambda images, played, brief: called.append(1) or {"overall": 7, "scores": {"looks": 7}})
    b = {"id": "b1", "genre": "runner", "orientation": "portrait", "brief": "x"}
    assert A._one_card(b, builder=lambda _b: (gid, 0.0, 0.0), judge_it=False)["judge"] is None and not called
    assert A._one_card(b, builder=lambda _b: (gid, 0.0, 0.0))["judge"]["overall"] == 7 and called == [1]


def test_selfcheck_scores_the_proof_game_and_cleans_up(arena, monkeypatch, tmp_path):
    A, G = arena
    from app.gamedesk import kit3d
    monkeypatch.setattr(G, "health", lambda: {"installed": True, "web_templates": True, "ready": True, "version": "4.7.2"})

    def proof(tenant="", conv="", save=False, shots_to=None):
        job = tmp_path / "job"
        (job / "proj").mkdir(parents=True, exist_ok=True)
        (job / "proj" / "main.gd").write_text(kit3d.proof_main())
        (job / "build").mkdir(exist_ok=True)
        (job / "build" / "index.html").write_text("<!doctype html>")
        return {"ok": True, "game": kit3d._keep(tenant, conv, job, {"download_bytes": 1, "seconds": 1}, {"fps": 30, "shots": []})}
    monkeypatch.setattr(kit3d, "proof", proof)
    monkeypatch.setattr(A, "play", lambda build, o, out, seconds=12: {"started": True, "load_s": 2.0, "fps": 30.0, "errors": 0,
                        "error_list": [], "responds": True, "reached_end": False, "events": [], "state_keys": ["state"], "shots": []})
    r = A.selfcheck()
    assert r["ok"] and r["proof_built"] and r["briefs"] == {"count": 500, "unique": 500, "genres": 20, "set": A.SET_V}
    assert r["card"]["playable"] and r["dna"]
    assert G.projects(A.TENANT) == [], "the check leaves no game behind"
    # a scorer that cannot play the known-good game is NOT ready, and says why
    monkeypatch.setattr(A, "play", lambda *a, **k: {"started": False, "errors": 0, "error_list": [], "responds": False,
                                                    "reached_end": False, "events": [], "state_keys": [], "shots": []})
    bad = A.selfcheck()
    assert not bad["ok"] and "could not start" in bad["why"]
    monkeypatch.setattr(kit3d, "proof", lambda **k: {"ok": False, "smoke": {"ok": False, "errors": ["x"]}})
    assert "did not build" in A.selfcheck()["why"]
    monkeypatch.setattr(G, "health", lambda: {"installed": False, "web_templates": False, "ready": False})
    assert "not installed" in A.selfcheck()["why"]


def test_the_cli_and_the_server_jobs():
    main = (SERVER / "app" / "gamedesk" / "__main__.py").read_text(encoding="utf-8")
    for word in ('["arena"]', '"check"', '"run"', '"status"', "--budget", "background=False"):
        assert word in main, word
    ops = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text(encoding="utf-8")
    for job in ("game_arena_check", "game_arena_try", "game_arena_status"):
        assert f"- {job}" in ops and f"{job})" in ops, job
    assert "arena run --n 3 --budget 150" in ops and "arena check" in ops
    src = (SERVER / "app" / "gamedesk" / "arena.py").read_text(encoding="utf-8")
    assert '/ "web"' not in src.replace('`<version>/web`', ""), "no code path reads the folder that never existed"


def _godot() -> str:
    from app.gamedesk import engine
    return engine.find() or ""


@pytest.mark.skipif(not (_godot() and os.environ.get("HOOLA_CHROMIUM")), reason="needs Godot and a Chromium")
def test_real_engine_the_arena_measures_the_proof_game(arena):
    A, G = arena
    from app.gamedesk import engine
    if engine.templates_dir() is None:
        pytest.skip("Godot's web export templates are not installed here")
    r = A.selfcheck()
    assert r["ok"], r
    assert r["card"]["started"] and r["card"]["responds"] and r["card"]["errors"] == 0 and r["card"]["state_keys"] >= 1
