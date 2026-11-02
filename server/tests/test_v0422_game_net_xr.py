"""v0.422 GAME DESK ROLES, Phase 7 batch 3 (Game Desk plan phase 4): the Multiplayer Network Programmer (bots over three
networks through an authoritative server with prediction, reconciliation, interpolation and lag compensation; desync
must be 0; the Godot netcode run itself with a server and three clients) and the AR / VR Interaction Engineer (comfort
rules in code, gestures scored on synthetic hands and cross-checked in Godot, a WebXR demo room). Two netcode bugs the
bot run found are pinned: a late OLDER snapshot must never be applied, and lost tail inputs must be resent."""
import asyncio
import io
import zipfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


# ================================================================ netcode: the bot run
def test_desync_is_zero_on_every_network_and_seed():
    from app.gamedesk import netcode as N
    for over in ({}, {"players": 48, "tick": 60, "send": 30}, {"players": 4, "speed": 900, "size": 16}):
        inp = N.clean_inputs(over)
        for seed in (1, 2, 3):
            for key, net in N.NETWORKS.items():
                r = N.simulate(inp, net, seed=seed)
                assert r["desync_px_max"] == 0, (over, seed, key, r)


def test_the_two_bugs_the_bots_found_stay_fixed():
    from app.gamedesk import netcode as N
    inp = N.clean_inputs({})
    r = N.simulate(inp, N.NETWORKS["mobile"], seed=1)
    assert r["stale_snapshots_dropped"] > 0                          # late older snapshots arrive - and are dropped
    assert r["inputs_skipped"] == 0                                  # resends: nothing had to be skipped
    assert r["up_bps_per_player"] > N.simulate(inp, N.NETWORKS["good"], seed=1)["up_bps_per_player"]   # the stated cost
    assert "if int(s[\"tick\"]) <= newest" in N.GD_NET and "func unacked()" in N.GD_NET


def test_judge_names_failures_and_states_numbers():
    from app.gamedesk import netcode as N
    inp = N.clean_inputs({})
    runs = {k: N.simulate(inp, n) for k, n in N.NETWORKS.items()}
    j = N.judge(runs, inp, {k: N.simulate(inp, n) for k, n in N.NETWORKS.items()})
    assert j["verdict"] == "PASS", [c for c in j["checks"] if not c["ok"]]
    bw = next(c for c in j["checks"] if c["check"] == "bandwidth stated")
    assert "B/s down" in bw["note"] and "without them" in bw["note"]
    lag = next(c for c in j["checks"] if c["check"] == "lag compensation")
    assert runs["plan"]["lagcomp_agree"] > runs["plan"]["no_lagcomp_agree"]
    bad = {k: dict(v) for k, v in runs.items()}
    bad["plan"]["desync_px_max"] = 3.5
    bad["plan"]["corr_p95_px"] = 99
    j = N.judge(bad, inp, None)
    assert j["verdict"] == "FAIL" and any("desync" in c["check"] and not c["ok"] for c in j["checks"])
    assert any(c["check"].startswith("rubber") and not c["ok"] for c in j["checks"])
    assert lag["ok"]


def test_netcode_flow_kit_and_never_in_the_game_yet(st, monkeypatch):  # noqa: F811
    from app.gamedesk import netcode as N
    from app.gamedesk import packs
    v = N.setup("default", inputs={"players": 8}, studio=st["sid"], run_now=False)
    out = N.run(v["id"], real_engine=False)
    assert out["status"] == "draft" and out["report"]["verdict"] == "PASS"
    assert any("NOT ASSESSED" in c["note"] for c in out["report"]["checks"])
    sig = out["files"]["kit.zip"].split("sig=")[1]
    p = N.net_file(v["id"], "kit.zip", sig)
    z = zipfile.ZipFile(io.BytesIO(p.read_bytes()))
    assert {"server/server.gd", "server/hoola_net.gd", "server/Dockerfile", "client/hoola_net.gd"} <= set(z.namelist())
    assert N.net_file(v["id"], "kit.zip", "0" * 16) is None
    with pytest.raises(N.NetError, match="wss"):
        N.set_server("default", v["id"], "http://evil.example/x")
    assert N.set_server("default", v["id"], "wss://game.example.in/play")["server_url"] == "wss://game.example.in/play"
    N.approve("default", v["id"])
    assert "hoola_net.gd" not in packs.for_game("default", st["gid"])                # not inside the game build yet
    with pytest.raises(N.NetError, match="network"):
        N.apply("default", st["sid"])


# ================================================================ XR: comfort + gestures
def test_comfort_rules_name_every_problem():
    from app.gamedesk import xr as X
    ok = X.comfort(X.clean_settings({}))
    assert ok["errors"] == [] and any("NOT ASSESSED" in p for p in ok["passed"])
    bad = X.comfort(X.clean_settings({"locomotion": "smooth", "vignette": False, "turn": "smooth", "seated": False,
                                      "ui_m": 0.5, "text_deg": 0.8}))
    assert len(bad["errors"]) == 5
    assert X.comfort(X.clean_settings({"locomotion": "smooth", "vignette": True}))["errors"] == []


def test_gestures_on_the_synthetic_set():
    from app.gamedesk import xr as X
    sc = X.score(X.test_set())
    assert sc["accuracy"] >= 0.95 and sc["samples"] == 240
    assert sc["per_gesture"]["pinch"] >= 0.95 and sc["confusion"]["pinch"]["grab"] == 0
    rng = np.random.default_rng(1)
    fist = X.hand({k: 1.0 for k in X.FINGERS}, 0.0, rng, 1.0, 0.0)
    flat = X.hand({k: 0.0 for k in X.FINGERS}, 0.0, rng, 1.0, 0.0)
    pinch = X.hand({"index": 0.35, "middle": 0.1, "ring": 0.1, "little": 0.1}, 1.0, rng, 1.0, 0.0)
    assert (X.classify(fist), X.classify(flat), X.classify(pinch)) == ("grab", "open", "pinch")


def test_xr_flow_into_the_build(st, monkeypatch):  # noqa: F811
    from app.gamedesk import engine, guard, packs, template
    from app.gamedesk import xr as X
    monkeypatch.setattr(engine, "find", lambda: "")
    v = X.setup("default", settings={"snap_deg": 45}, studio=st["sid"], run_now=False)
    out = X.run(v["id"])
    assert out["status"] == "draft" and out["report"]["verdict"] == "PASS"
    X.approve("default", v["id"])
    got = packs.for_game("default", st["gid"])
    txt = got["hoola_xr.gd"][0]
    assert "func gesture(" in txt and '"snap_deg": 45' in txt and "func teleport(" in txt
    assert guard.problems({"main.gd": "extends Node\n", "hoola_xr.gd": txt}) == []
    assert 'HoolaXR="*res://hoola_xr.gd"' in template.files("t", "landscape", {"main.gd": "", "hoola_xr.gd": txt})["project.godot"]
    bad = X.setup("default", settings={"turn": "smooth"}, run_now=False)
    assert X.run(bad["id"])["status"] == "failed"
    with pytest.raises(X.XrError):
        X.approve("default", bad["id"])


def test_tools_api_hire_and_ui(st, monkeypatch):  # noqa: F811
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.gamedesk import netcode as N
    from app.gamedesk import xr as X
    from app.main import app
    monkeypatch.setattr(N, "_pool", lambda: type("X", (), {"submit": staticmethod(lambda *a, **k: None)})())
    monkeypatch.setattr(X, "_POOL", type("X", (), {"submit": staticmethod(lambda *a, **k: None)})())
    assert hire.CATALOG["netcode_dev"]["live"] and hire.CATALOG["xr_dev"]["live"]
    soon = sorted(k for k, e in hire.CATALOG.items() if e.get("group") == hire.GAME_GROUP and not e["live"])
    assert "netcode_dev" not in soon and "xr_dev" not in soon                    # (v0.423: the last three went live too)
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    with pytest.raises(tools.ToolError, match="hired nahi"):
        asyncio.run(tools.HANDLERS["game_net"](ctx, action="setup"))
    c = TestClient(app)
    assert c.post("/api/gamedesk/xr", json={}).status_code == 400
    hire.hire("default", "netcode_dev")
    hire.hire("default", "xr_dev")
    out = asyncio.run(tools.HANDLERS["game_net"](ctx, action="setup", words="16 players, 240 px/s"))
    assert out["number"] == "N-001" and out["status"] == "testing" and "Hoola hosts no" in out["hosting"]
    out = asyncio.run(tools.HANDLERS["game_xr"](ctx, action="setup", words="AR on a phone"))
    assert out["number"] == "X-001" and "not measured" in out["headset_fps"]
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_xr"](staff, action="approve", setup="X-001"))
    assert tools.FAMILY_OF["game_net"] == tools.FAMILY_OF["game_xr"] == "gamedesk"
    for ask in ("mere game ko multiplayer banao", "ek vr game headset ke liye", "game server ka netcode"):
        assert "gamedesk" in admit.route(ask), ask
    d = c.get("/api/gamedesk/net").json()
    assert d["hired"] and d["setups"][0]["number"] == "N-001" and "plan" in d["networks"]
    assert c.post(f"/api/gamedesk/net/{d['setups'][0]['id']}/server", json={"url": "ftp://x"}).status_code == 400
    x = c.get("/api/gamedesk/xr").json()
    assert x["hired"] and x["setups"][0]["settings"]["mode"] == "ar"
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "gsNet" in emp and "gsXr" in emp and "netcode_dev: 'gamedesk'" in emp and "Shown → read as" in emp
    scr = (root / "lib/ui/game_roles_screen.dart").read_text()
    assert "class GameNetScreen" in scr and "class GameXrScreen" in scr
    from app.gamedesk import ai
    assert "HoolaXR" in ai.GUIDE


def _godot() -> bool:
    from app.gamedesk import engine
    return bool(engine.find())


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_netcode_and_gestures(tmp_path):
    from app.gamedesk import netcode as N
    from app.gamedesk import xr as X
    g = N.godot_lab(N.clean_inputs({}), N.NETWORKS["plan"], tmp_path / "net")
    assert g["desync_px_max"] == 0 and g["remote_ok"] and g["snapshots"] > 100
    s = X.test_set(n=10)
    cc = X.godot_cross_check(X.clean_settings({}), s, tmp_path / "xr")
    assert cc["agree"] == cc["samples"] == 40
