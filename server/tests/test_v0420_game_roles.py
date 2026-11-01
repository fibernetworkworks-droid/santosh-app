"""v0.420 GAME DESK ROLES, Phase 7 batch 1 (Hoola Game Engine plan Phase 7 = Game Desk plan phase 2): the Procedural World
Generation Engineer (worlds from rules + a seed, checked in code, previewed, walkable, into the game as HoolaWorld) and
the Physics Engine Developer (settings worked out in code, proved in Godot's own physics lab, into the game as
HoolaPhysics). The engine is faked in most tests; the last two run the REAL Godot when it is installed (skipped in CI).
Two findings from real Godot 4.7.2 runs are pinned here: without CCD a body tunnels once a step passes HALF the wall
(depending on where its steps land), and only cast-ray CCD stops it (cast-shape behaved like no CCD)."""
import asyncio
import io
import json
import os
import struct
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


# ================================================================ worlds: generators + checks (pure, no database)
@pytest.mark.parametrize("kind", ["terrain", "dungeon", "city", "level"])
def test_every_kind_is_repeatable_and_passes_its_checks(kind):
    from app.gamedesk import world as W
    for seed in (1, 7, 42, 99, 2024):
        r = W.generate(kind, seed, {})
        assert r["checks"]["errors"] == [], (kind, seed, r["checks"]["errors"])
        assert r["checks"]["passed"][0].startswith("same seed = same world")
        assert r["fingerprint"] == W.generate(kind, seed, {})["fingerprint"]
    assert W.generate(kind, 1, {})["fingerprint"] != W.generate(kind, 2, {})["fingerprint"]


def test_levels_pass_for_every_jump_and_the_arc_rule_is_real():
    from app.gamedesk import world as W
    for jh, jw in ((1, 2), (2, 3), (3, 4), (5, 7), (8, 10)):
        bad = [s for s in range(25) if W.generate("level", s, {"jump_h": jh, "jump_w": jw})["checks"]["errors"]]
        assert bad == [], (jh, jw, bad)
    # the arc: full height only up to half the width; at full width the jump lands level, never higher
    assert W.can_jump(3, 2, 3, 4) and W.can_jump(0, 4, 3, 4) and not W.can_jump(1, 4, 3, 4)
    assert not W.can_jump(0, 5, 3, 4) and W.can_jump(-6, 4, 3, 4)


def test_an_impossible_level_is_caught():
    from app.gamedesk import world as W
    I = W._ids("level")
    t = np.full((12, 40), I["air"], dtype=np.uint8)
    t[9:, :10] = I["ground"]
    t[9:, 16:] = I["ground"]                           # a 6-tile gap
    t[8, 37] = I["goal"]
    g = {"tiles": t, "points": {"spawn": [1, 8], "goal": [[37, 8]], "coins": []}, "extra": {}}
    ch = W.check("level", g, {"jump_h": 3, "jump_w": 4})
    assert any("cannot be reached" in e for e in ch["errors"]) and any("stuck at x=9" in e for e in ch["errors"])
    ch = W.check("level", g, {"jump_h": 3, "jump_w": 7})
    assert ch["errors"] == []


def test_unreachable_points_and_a_stuck_spawn_are_named():
    from app.gamedesk import world as W
    I = W._ids("dungeon")
    t = np.full((10, 20), I["wall"], dtype=np.uint8)
    t[2:5, 2:6] = I["floor"]
    t[2:5, 12:16] = I["floor"]                         # a room with no corridor
    g = {"tiles": t, "points": {"spawn": [3, 3], "exit": [[13, 3]], "treasure": [[4, 3]]}, "extra": {"rooms": 2}}
    ch = W.check("dungeon", g, {"rooms": 2})
    assert any("1 of 1 exit cannot be reached" in e for e in ch["errors"])
    t2 = np.full((5, 5), I["wall"], dtype=np.uint8)
    t2[2, 2] = I["floor"]
    ch = W.check("dungeon", {"tiles": t2, "points": {"spawn": [2, 2]}, "extra": {"rooms": 1}}, {"rooms": 1})
    assert any("stuck" in e for e in ch["errors"])


def test_terrain_rivers_cities_and_params_are_clamped():
    from app.gamedesk import world as W
    r = W.generate("terrain", 11, {"rivers": 5})
    assert r["stats"]["rivers"] == 5 and r["stats"]["rivers_to_sea"] >= 4
    assert any("rivers reach the sea" in p for p in r["checks"]["passed"])
    c = W.generate("city", 11, {})
    assert "every road joins one network" in c["checks"]["passed"] and any("face a road" in p for p in c["checks"]["passed"])
    p = W.clean_params("terrain", {"w": 99999, "h": 99999, "sea": 5, "rivers": -3, "junk": 1})
    assert p["w"] * p["h"] <= W.MAX_CELLS and p["sea"] == 0.8 and p["rivers"] == 0 and "junk" not in p
    with pytest.raises(W.WorldError):
        W.clean_params("space", {})


def test_preview_heightmap_and_glb_are_real_files():
    from PIL import Image
    from app.gamedesk import world as W
    r = W.generate("terrain", 5, {"w": 64, "h": 48})
    im = Image.open(io.BytesIO(W.preview_png("terrain", r["g"])))
    assert im.size[0] >= 64 and im.mode == "RGB"
    hm = Image.open(io.BytesIO(W.heightmap_png(r["g"])))
    assert hm.size == (64, 48) and hm.mode.startswith("I")
    glb = W.terrain_glb("terrain", r["g"])
    info = W.read_glb(glb)
    assert info["vertices"] == 64 * 48 and info["triangles"] == 63 * 47 * 2
    with pytest.raises(W.WorldError):
        W.read_glb(glb[:-8])                                                       # a cut-off file is caught
    bad = bytearray(glb)
    struct.pack_into("<I", bad, 12, 8)                                             # a JSON chunk that lies about its size
    with pytest.raises(Exception):
        W.read_glb(bytes(bad))


def test_plan_from_words_without_a_model(monkeypatch):
    from app.gamedesk import ai
    from app.gamedesk import world as W
    monkeypatch.setattr(ai, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model")))
    assert W.plan_from_words("ek dungeon banao 20 rooms ka")["kind"] == "dungeon"
    assert W.plan_from_words("a city with tall towers")["kind"] == "city"
    assert W.plan_from_words("platformer level, jump karna")["kind"] == "level"
    monkeypatch.setattr(ai, "ask", lambda *a, **k: '{"kind": "terrain", "key": "Big Island!", "params": {"sea": 9, "rivers": 3}}')
    p = W.plan_from_words("a big island")
    assert p["key"] == "big_island" and p["params"]["sea"] == 0.8 and p["params"]["rivers"] == 3


# ================================================================ worlds: store, pack, build
def test_world_flow_files_signed_links_and_into_the_build(st):  # noqa: F811
    from app.gamedesk import guard, packs, template
    from app.gamedesk import world as W
    v = W.make("default", kind="dungeon", seed=5, studio=st["sid"], key="crypt")
    assert v["number"] == "W-001" and v["status"] == "draft" and v["key"] == "crypt"
    assert set(v["files"]) >= {"preview.png", "world.json"}
    url = v["files"]["preview.png"]
    wid, sig = v["id"], url.split("sig=")[1]
    assert W.world_file(wid, "preview.png", sig) is not None
    assert W.world_file(wid, "preview.png", "0" * 16) is None and W.world_file(wid, "../t.db", sig) is None
    assert packs.for_game("default", st["gid"]) == {}                              # nothing before her OK
    W.approve("default", "W-001")
    v2 = W.make("default", kind="dungeon", seed=6, studio=st["sid"], key="crypt")
    assert v2["version"] == 2
    W.approve("default", v2["id"])
    assert W.get("default", "W-001")["status"] == "rejected"                       # one approved world per key
    got = packs.for_game("default", st["gid"])
    txt = got["hoola_world.gd"][0]
    assert "const WORLDS :=" in txt and '"crypt"' in txt and "func walkable(" in txt
    files = {"main.gd": "extends Node\n", "hoola_world.gd": txt}
    assert guard.problems(files) == []
    proj = template.files("t", "portrait", files)["project.godot"]
    assert 'HoolaWorld="*res://hoola_world.gd"' in proj
    W.apply("default", st["sid"])
    st["svc"].run_job(st["gid"])
    g = st["svc"].get("default", st["gid"])
    assert g["version"] == 2
    vdir = Path(os.environ["GAME_DIR"]) / "default"
    built = list(vdir.rglob("v2/proj/hoola_world.gd"))
    assert built and "crypt" in built[0].read_text()
    assert 'HoolaWorld="*res://hoola_world.gd"' in (built[0].parent / "project.godot").read_text()


def test_model_cannot_write_the_pack_files():
    from app.gamedesk import service
    files = {"main.gd": "extends Node\n", "hoola_world.gd": "# the model's own fake", "hoola_physics.gd": "# stale"}
    service._own_packs(files, {"hoola_world.gd": ("# Hoola's", {})})
    assert files["hoola_world.gd"] == "# Hoola's" and "hoola_physics.gd" not in files
    from app.gamedesk import guard
    bad = guard.problems({"main.gd": "extends Node\nclass_name HoolaWorld\n"})
    assert any("Hoola's own name" in b for b in bad)


def test_world_demo_is_served_by_its_token(st, monkeypatch):  # noqa: F811
    from app.gamedesk import engine, playtest, service
    from app.gamedesk import world as W
    v = W.make("default", kind="terrain", seed=3, params={"w": 48, "h": 40})

    def export(job, holder=None, debug=False):
        b = job / "build"
        b.mkdir(parents=True, exist_ok=True)
        for n in ("index.html", "index.js", "index.wasm", "index.pck"):
            (b / n).write_text(n)
        return {"ok": True, "errors": [], "download_bytes": 1048576}
    monkeypatch.setattr(engine, "export_web", export)
    monkeypatch.setattr(playtest, "run", lambda build, out, orientation="portrait", seconds=8: {"ok": True, "errors": [], "fps": 50, "load_s": 1.0})
    seen = {}
    monkeypatch.setattr(engine, "smoke", lambda job, frames=600, holder=None: seen.update(main=(job / "proj" / "main.gd").read_text(),
                                                                                          proj=(job / "proj" / "project.godot").read_text()) or {"ok": True, "errors": []})
    out = W.run_demo(v["id"])
    assert out["status"] == "done" and out["numbers"]["fps_server"] == 50
    assert "Hoola world explorer" in seen["main"] and "HoolaWorld=" in seen["proj"]
    tok = out["token"] or W.get("default", v["id"])["demo"]["token"]
    W.demo                                                                        # noqa: B018 (exists)
    from app.db import session
    with session() as s:
        row = s.get(W.GameWorld, v["id"])
        row.demo_token = tok = "T" * 24
        row.demo = {**row.demo, "token": tok}
    p, media = service.play_file(tok, "index.html")
    assert p is not None and media.startswith("text/html")
    assert service.play_file(tok, "../world.json")[0] is None and service.play_file("U" * 24, "index.html")[0] is None


# ================================================================ physics: rules, judge, flow
def test_tunnelling_rule_is_half_the_wall_and_the_choice_is_in_code():
    from app.gamedesk import physics as P
    assert not P.tunnel_risk(400, 16, 60)["risk"]                  # 6.7 px a step <= 8
    assert P.tunnel_risk(900, 16, 60)["risk"]                      # 15 px a step > 8 (the real-engine finding)
    c = P.choose(P.clean_inputs({"speed": 900, "wall": 16}))
    assert c["ticks"] == 113 and not c["ccd"]
    c = P.choose(P.clean_inputs({"speed": 3000, "wall": 8}))
    assert c["ccd"] and c["ticks"] == 60 and "cast-ray" in c["why"]
    c = P.choose(P.clean_inputs({"speed": 300, "wall": 16}))
    assert not c["ccd"] and c["ticks"] == 60
    assert P.clean_inputs({"ticks": 9999, "speed": -5})["ticks"] == 240
    assert P.fall_discrete(980, 60, 60) == pytest.approx(498.1667, abs=1e-3)
    assert P.elastic(1, 2, 300) == (-100.0, 200.0) and P.projectile_range(300, 400, 980) == pytest.approx(244.898, abs=1e-3)
    assert P.from_words("bullet 2400 px/s, wall 10, 120 ticks, gravity 1500") == {"speed": 2400, "wall": 10, "ticks": 120, "gravity": 1500}


def _raw(**kw):
    base = {"fall_y": 498.1667, "fall_steps": 60, "proj_x": 239.9, "v1": -100.0, "v2": 200.0, "through_off": 5, "through_ray": 0,
            "through_shape": 5, "stack_drift": 0.2, "stack_sink": 1.7, "fall3d_y": 4.982, "engine3d": "DEFAULT", "engine2d": "DEFAULT"}
    return {**base, **kw}


def test_judge_passes_real_numbers_and_names_every_failure():
    from app.gamedesk import physics as P
    st = {**P.choose(P.clean_inputs({"speed": 3000, "wall": 8})), "speed": 3000, "wall": 8, "g3d": 9.8}
    j = P.judge(_raw(), _raw(), st)
    assert j["verdict"] == "PASS" and j["passed"] == j["total"] == 7
    tun = next(c for c in j["cases"] if c["case"].startswith("tunnelling"))
    assert tun["measured"]["without_ccd"] == "WENT THROUGH 5 of 6" and "cast-shape CCD let some through" in tun["note"]
    j = P.judge(_raw(through_ray=2), _raw(), st)
    assert j["verdict"] == "FAIL" and not next(c for c in j["cases"] if c["case"].startswith("tunnelling"))["ok"]
    assert not next(c for c in j["cases"] if c["case"] == "same run twice")["ok"]          # different results = not repeatable
    j = P.judge(_raw(fall_y=560), _raw(fall_y=560), st)
    assert not next(c for c in j["cases"] if c["case"].startswith("free fall"))["ok"]
    j = P.judge(_raw(v1=-40, v2=120), _raw(v1=-40, v2=120), st)
    assert not next(c for c in j["cases"] if c["case"] == "elastic collision")["ok"]


def test_physics_flow_lab_evidence_approval_and_the_autoload(st, monkeypatch):  # noqa: F811
    from app.gamedesk import guard, packs
    from app.gamedesk import physics as P
    labs = []
    monkeypatch.setattr(P, "_run_lab", lambda job, cfg: labs.append(cfg) or _raw(through_off=6 if cfg["ticks"] == 60 else 0))
    v = P.setup("default", inputs={"speed": 3000, "wall": 8}, studio=st["sid"], run_now=False)
    assert v["status"] == "testing" and v["settings"]["ccd"]
    with pytest.raises(P.PhysicsError, match="Lab abhi"):
        P.approve("default", v["id"])
    out = P.run_lab(v["id"])
    assert out["status"] == "draft" and out["lab"]["verdict"] == "PASS"
    assert out["lab"]["before"]["through"] == 6 and "6 of 6 bullets went through" in out["lab"]["before"]["say"]
    assert len(labs) == 3                                                          # twice + her old settings once
    assert packs.for_game("default", st["gid"]).get("hoola_physics.gd") is None    # not before her OK
    P.approve("default", "P-001")
    txt = packs.for_game("default", st["gid"])["hoola_physics.gd"][0]
    assert "CCD_MODE_CAST_RAY" in txt and "CAST_SHAPE" not in txt and '"verdict": "PASS"' in txt
    assert guard.problems({"main.gd": "extends Node\n", "hoola_physics.gd": txt}) == []
    bad = P.setup("default", inputs={"speed": 900, "wall": 16}, studio=st["sid"], run_now=False)
    monkeypatch.setattr(P, "_run_lab", lambda job, cfg: _raw(through_off=3, through_ray=3))
    out = P.run_lab(bad["id"])
    assert out["status"] == "failed" and "tunnelling" in out["error"]
    with pytest.raises(P.PhysicsError, match="PASS"):
        P.approve("default", bad["id"])


def test_physics_reads_the_bible_speed(st, monkeypatch):  # noqa: F811
    from app.gamedesk import bible as B
    from app.gamedesk import physics as P
    monkeypatch.setattr(B, "view", lambda t, sid: {"data": {"player": {"speed": 420}, "entities": {"enemy": [{"id": "bat", "speed": 2600}]}}})
    assert P.from_bible("default", st["sid"]) == {"speed": 2600.0}
    v = P.setup("default", studio=st["sid"], run_now=False)
    assert v["inputs"]["speed"] == 2600


# ================================================================ tools, API, hire cards, UI
def test_tools_api_hire_and_ui(st, monkeypatch):  # noqa: F811
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.gamedesk import physics as P
    from app.main import app
    monkeypatch.setattr(P, "_POOL", type("X", (), {"submit": staticmethod(lambda *a, **k: None)})())
    cat = hire.CATALOG
    assert cat["procgen_dev"]["live"] and cat["physics_dev"]["live"] and cat["procgen_dev"]["group"] == hire.GAME_GROUP
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    with pytest.raises(tools.ToolError, match="hired nahi"):
        asyncio.run(tools.HANDLERS["game_world"](ctx, action="make", kind="city"))
    c = TestClient(app)
    assert c.post("/api/gamedesk/worlds", json={"kind": "city"}).status_code == 400            # not hired
    hire.hire("default", "procgen_dev")
    hire.hire("default", "physics_dev")
    out = asyncio.run(tools.HANDLERS["game_world"](ctx, action="make", kind="city", seed=4))
    assert out["number"] == "W-001" and out["checks"]["errors"] == [] and out["numbers"]["w"] == 96
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_world"](staff, action="approve", world="W-001"))
    out = asyncio.run(tools.HANDLERS["game_physics"](ctx, action="setup", inputs={"speed": 3000, "wall": 8}))
    assert out["status"] == "testing" and out["settings"]["ccd"] and out["fluids"] == "not built yet"
    assert tools.FAMILY_OF["game_world"] == tools.FAMILY_OF["game_physics"] == "gamedesk"
    for ask in ("game ke liye procedural world banao", "mere game ki physics check karo", "ek dungeon generate karo game map"):
        assert "gamedesk" in admit.route(ask), ask
    d = c.get("/api/gamedesk/worlds").json()
    assert d["hired"] and d["worlds"][0]["kind"] == "city" and "level" in d["kinds"]
    w = d["worlds"][0]
    assert c.get(w["files"]["preview.png"]).headers["content-type"] == "image/png"
    assert c.post(f"/api/gamedesk/world/{w['id']}/approve").json()["status"] == "approved"
    assert c.post(f"/api/gamedesk/world/{w['id']}/explode").status_code == 404
    r = c.post("/api/gamedesk/worlds", json={"words": "", "kind": "level", "params": {"jump_h": 2, "jump_w": 3}, "seed": 8})
    assert r.status_code == 200 and r.json()["params"]["jump_h"] == 2
    p = c.get("/api/gamedesk/physics").json()
    assert p["hired"] and p["setups"][0]["number"] == "P-001" and p["defaults"]["ticks"] == 60
    assert c.post("/api/gamedesk/physics", json={"inputs": {"speed": 500, "wall": 20}}).json()["settings"]["ccd"] is False
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "gsWorld" in emp and "gsPhysics" in emp and "/api/gamedesk/worlds" in emp and "procgen_dev: 'gamedesk'" in emp
    assert "hired.procgen_dev" in (root / "server/app/static/console/v2.js").read_text()
    scr = (root / "lib/ui/game_roles_screen.dart").read_text()
    assert "class GameWorldsScreen" in scr and "class GamePhysicsScreen" in scr
    assert "gameWorldNew" in (root / "lib/api.dart").read_text() and "GameWorldsScreen" in (root / "lib/ui/game_studio_screen.dart").read_text()
    assert "HoolaWorld" in __import__("app.gamedesk.ai", fromlist=["GUIDE"]).GUIDE and "HoolaPhysics" in __import__("app.gamedesk.ai", fromlist=["GUIDE"]).GUIDE


# ================================================================ the REAL engine (skipped where Godot is not installed)
def _godot() -> bool:
    from app.gamedesk import engine
    return bool(engine.find())


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_physics_lab(tmp_path):
    from app.gamedesk import physics as P
    raw = P._run_lab(tmp_path / "a", P._lab_cfg({"ticks": 60, "gravity": 980, "speed": 3000, "wall": 8}))
    raw2 = P._run_lab(tmp_path / "b", P._lab_cfg({"ticks": 60, "gravity": 980, "speed": 3000, "wall": 8}))
    st = {**P.choose(P.clean_inputs({"speed": 3000, "wall": 8})), "speed": 3000, "wall": 8, "g3d": 9.8}
    j = P.judge(raw, raw2, st)
    assert j["verdict"] == "PASS", j["cases"]
    assert raw["through_ray"] == 0 and raw["through_off"] >= 1                  # cast-ray stops it; no CCD does not


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_world_autoload_parses_and_runs(tmp_path):
    from app.gamedesk import engine, template
    from app.gamedesk import world as W
    r = W.generate("level", 3, {"w": 60})
    row = W.GameWorld(id="gw_test", tenant_id="t", key="lvl", kind="level", seed=3, params=r["p"], version=1, fingerprint=r["fingerprint"])
    scripts = {"main.gd": W.DEMO_SIDE, W.FILE: W.gd({"lvl": W.world_data(row, r["g"])})}
    (tmp_path / "proj").mkdir()
    for name, txt in template.files("t", "landscape", scripts).items():
        (tmp_path / "proj" / name).write_text(txt)
    sm = engine.smoke(tmp_path, frames=120)
    assert sm["ok"], sm["errors"]
