"""v0.423 GAME DESK ROLES, Phase 7 batch 4 (Game Desk plan phase 5): the Simulation Software Engineer (orbit / flight /
driving models validated against textbook cases, sources cited, scenarios repeatable; HoolaSim's GDScript step checked
in the real Godot), the Digital Twin Architect (traceable numbers, read-only, an event engine checked against exact
answers and queueing theory, NOT ASSESSED without her real week) and the VFX Pipeline TD (naming, ACES colour measured,
a real ACEScg EXR read back, render queue with re-queue + cost per shot, frames traced to scene versions)."""
import asyncio
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


# ================================================================ simulators
@pytest.mark.parametrize("kind", ["orbit", "flight", "driving"])
def test_every_model_passes_its_reference_cases(kind):
    from app.gamedesk import sim as S
    r = S.simulate(kind, {})
    assert r["verdict"] == "PASS", [c for c in r["cases"] if not c["ok"]]
    assert r["source"] and "RK4" in r["integrator"]


def test_orbits_at_any_inclination_and_the_physics_is_right():
    from app.gamedesk import sim as S
    sso = S.simulate("orbit", {"alt_km": 800, "inc_deg": 98})
    assert sso["verdict"] == "PASS"
    node = next(c for c in sso["cases"] if c["case"] == "J2 node regression")
    assert node["measured"].startswith("0.9")                                  # sun-synchronous: about +0.99 deg / day
    geo = S.simulate("orbit", {"alt_km": 35786, "inc_deg": 0.1, "dt_s": 60, "hours": 24})
    assert next(c for c in geo["cases"] if c["case"] == "two-body period")["measured"] == pytest.approx(86164, abs=2)


def test_scenarios_and_refusals():
    from app.gamedesk import sim as S
    a = S.simulate("flight", {}, {"events": [{"kind": "gust", "t": 20, "w_mps": 3}]})
    b = S.simulate("flight", {})
    assert a["fingerprint"] != b["fingerprint"] and a["verdict"] == "PASS"            # the gust changes the log; still valid
    assert S.guess_kind("ek satellite ka orbit") == "orbit" and S.guess_kind("car on a curve") == "driving"
    assert S.REFUSE.search("missile guidance simulator") and not S.REFUSE.search("flight training simulator")


def test_sim_store_and_refusal(st, monkeypatch):  # noqa: F811
    from app.gamedesk import engine, packs
    from app.gamedesk import sim as S
    monkeypatch.setattr(engine, "find", lambda: "")
    with pytest.raises(S.SimError, match="Hathiyar"):
        S.setup("default", words="a missile targeting simulator")
    v = S.setup("default", kind="orbit", studio=st["sid"])
    assert v["status"] == "draft" and set(v["files"]) == {"log.csv", "plot.png"}
    sig = v["files"]["log.csv"].split("sig=")[1]
    assert S.sim_file(v["id"], "log.csv", sig).read_text().startswith("t_s,x_km")
    S.approve("default", v["id"])
    txt = packs.for_game("default", st["gid"])["hoola_sim.gd"][0]
    assert "func step(" in txt and "J2 :=" in txt
    f = S.setup("default", kind="flight", studio=st["sid"])
    S.approve("default", f["id"])
    assert packs.for_game("default", st["gid"])["hoola_sim.gd"]                   # the orbit one stays the game's


# ================================================================ digital twin
def test_twin_engine_checks_and_traceability():
    from app.gamedesk import twin as T
    rep = T.evaluate(T.EXAMPLE)
    assert rep["verdict"] == "PASS", [c for c in rep["checks"] if not c["ok"]]
    assert any("NOT ASSESSED" in c["note"] for c in rep["checks"]) and not rep["validated"]
    names = [c["check"] for c in rep["checks"]]
    assert "line engine: one steady station" in names and "random queueing vs theory (M/M/3)" in names
    assert rep["base"]["bottleneck"] == "welding"
    w = {x["what_if"]: x for x in rep["what_ifs"]}
    assert w["one more machine at welding"]["change_pct"] > 0 and w["a second shift"]["change_pct"] > 50
    bad = json.loads(json.dumps(T.EXAMPLE))
    bad["stations"][0]["cycle_s"] = {"value": 40}
    bad["stations"][1]["mtbf_h"]["source"] = "tag:NOT.THERE"
    m = T.check_model(bad)
    assert any("no source" in e for e in m["errors"]) and any("not in the data map" in e for e in m["errors"])
    w2 = json.loads(json.dumps(T.EXAMPLE))
    w2["data_map"].append({"tag": "LINE1.CUT.Speed", "kind": "opcua-write", "asset": "cutting"})
    assert any("not a READ" in e for e in T.check_model(w2)["errors"])


def test_twin_against_her_week_and_store(st):  # noqa: F811
    from app.gamedesk import twin as T
    ok = T.setup("default", actual=[540, 560, 548])
    assert ok["status"] == "draft" and ok["report"]["validated"] and "layout.png" in ok["files"]
    far = T.setup("default", actual=[300, 310, 305])
    assert far["status"] == "failed" and any("against her real week" in c["check"] and not c["ok"] for c in far["report"]["checks"])
    with pytest.raises(T.TwinError, match="command"):
        T.setup("default", words="send a setpoint to the press")
    with pytest.raises(T.TwinError):
        T.apply("default", "")


# ================================================================ VFX pipeline
def test_colour_exr_queue_and_manifest():
    from app.gamedesk import vfx as V
    rep, rq = V.evaluate(V.clean_plan({}))
    assert rep["verdict"] == "PASS", [c for c in rep["checks"] if not c["ok"]]
    assert abs(float(V.logc3_decode(np.array([0.391007]))[0]) - 0.18) < 0.002
    assert abs(float(V.slog3_decode(np.array([420 / 1023]))[0]) - 0.18) < 0.002
    img = V.test_frame()
    back, info = V.read_exr(V.write_exr(img))
    assert np.array_equal(back, img.astype(np.float16).astype(np.float32)) and info["chromaticities"][0] == pytest.approx(0.713, abs=1e-4)
    assert all(V.NAME_RE.match(m["file"]) for m in rq["manifest"]) and len(rq["manifest"]) + len(rq["failed"]) == rq["frames"]
    assert not V.NAME_RE.match("Hoola_OP_sh10_comp_v1.1001.exr")
    bad = V.colour_checks(V.clean_plan({"sources": [{"name": "x", "space": "mystery"}], "view": ""}))
    assert len(bad["errors"]) == 2
    heavy, _ = V.evaluate(V.clean_plan({"fail_rate": 0.5}))
    q = heavy["queue"]
    assert q["requeued"] > 0 and q["frames"] == 144                                 # every frame done or named


def test_vfx_store_kit(st):  # noqa: F811
    from app.gamedesk import vfx as V
    v = V.setup("default")
    assert v["status"] == "draft"
    sig = v["files"]["kit.zip"].split("sig=")[1]
    z = zipfile.ZipFile(io.BytesIO(V.vfx_file(v["id"], "kit.zip", sig).read_bytes()))
    assert {"manifest.json", "hoola_render.py", "test_frame_acescg.exr", "README.txt"} <= set(z.namelist())
    back, info = V.read_exr(z.read("test_frame_acescg.exr"))
    assert info["w"] == 64 and "not run on" in z.read("hoola_render.py").decode().lower()


# ================================================================ tools / API / hire / UI
def test_tools_api_hire_and_ui(st, monkeypatch):  # noqa: F811
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.gamedesk import engine
    from app.main import app
    monkeypatch.setattr(engine, "find", lambda: "")
    for k in ("sim_dev", "twin_arch", "vfx_td"):
        assert hire.CATALOG[k]["live"]
    assert not [k for k, e in hire.CATALOG.items() if e.get("group") == hire.GAME_GROUP and not e["live"]]   # all ten live
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    with pytest.raises(tools.ToolError, match="is not hired"):   # English since d84057023 (tools wave 3)
        asyncio.run(tools.HANDLERS["game_twin"](ctx, action="setup"))
    c = TestClient(app)
    assert c.post("/api/gamedesk/vfx", json={}).status_code == 400
    for k in ("sim_dev", "twin_arch", "vfx_td"):
        hire.hire("default", k)
    out = asyncio.run(tools.HANDLERS["game_sim"](ctx, action="setup", kind="driving"))
    assert out["number"] == "M-001" and out["report"]["verdict"] == "PASS"
    with pytest.raises(tools.ToolError, match="Hathiyar"):
        asyncio.run(tools.HANDLERS["game_sim"](ctx, action="setup", words="bomb targeting"))
    out = asyncio.run(tools.HANDLERS["game_twin"](ctx, action="setup"))
    assert out["number"] == "D-001" and "never writes" in out["read_only"]
    out = asyncio.run(tools.HANDLERS["game_vfx"](ctx, action="setup"))
    assert out["number"] == "V-001" and out["report"]["verdict"] == "PASS"
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_vfx"](staff, action="setup"))
    assert tools.FAMILY_OF["game_sim"] == tools.FAMILY_OF["game_twin"] == tools.FAMILY_OF["game_vfx"] == "gamedesk"
    for ask in ("ek flight simulator chahiye training ke liye", "factory ka digital twin banao", "vfx pipeline aur render farm"):
        assert "gamedesk" in admit.route(ask), ask
    d = c.get("/api/gamedesk/sim").json()
    assert d["hired"] and d["setups"][0]["kind"] == "driving" and "orbit" in d["kinds"]
    t = c.get("/api/gamedesk/twin").json()
    assert t["setups"][0]["number"] == "D-001" and t["example"]["stations"]
    lay = t["setups"][0]["files"]["layout.png"]
    assert c.get(lay).headers["content-type"] == "image/png"
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "gsSim" in emp and "gsTwin" in emp and "gsVfx" in emp and "twin_arch: 'gamedesk'" in emp
    scr = (root / "lib/ui/game_roles_screen.dart").read_text()
    assert "class GameSimScreen" in scr and "class GameTwinScreen" in scr and "class GameVfxScreen" in scr
    from app.gamedesk import ai
    assert "HoolaSim" in ai.GUIDE


def _godot() -> bool:
    from app.gamedesk import engine
    return bool(engine.find())


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_orbit_step_matches(tmp_path):
    from app.gamedesk import sim as S
    cc = S.godot_cross_check(S.clean_params("orbit", {}), tmp_path)
    assert cc["ok"], cc
