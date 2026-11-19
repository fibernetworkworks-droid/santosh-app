"""v0.421 GAME DESK ROLES, Phase 7 batch 2 (Game Desk plan phase 3): the Spatial Audio Systems Programmer (binaural
renderer + reverb zones, every claim MEASURED: ear-to-ear timing per direction, level by side, 6 dB per doubling, zone
RT60 measured back, -16 LUFS / -1 dBFS, rendered twice; HoolaAudio) and the Haptic Feedback Systems Engineer (one
pattern per meaning checked for the motor, battery per play, off switch always, AHAP / Android / DRV2605 kit with the C
driver compiled; HoolaHaptics). The last test runs both autoloads in the REAL Godot when it is installed."""
import asyncio
import io
import json
import os
import zipfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


# ================================================================ audio: the measurements
def test_directions_follow_the_head_model():
    from app.gamedesk import audio as A
    d = A.measure_directions()
    assert d["itd_ok"] and d["side_ok"] and d["ild_grows"]
    by = {r["az"]: r for r in d["rows"]}
    assert by[0]["itd_us"] == 0 and by[90]["itd_us"] > 600 and by[-90]["itd_us"] < -600     # right = left ear later
    assert by[30]["ild_db"] > 0 > by[-30]["ild_db"]
    assert abs(by[150]["itd_us"] - by[30]["itd_us"]) < 1                                     # cone of confusion: same cue
    assert A.woodworth_itd(90) == pytest.approx(0.0875 / 343 * (np.pi / 2 + 1), rel=1e-9)


def test_distance_occlusion_reverb_and_loudness_are_measured():
    from app.gamedesk import audio as A
    assert A.measure_distance(1.0)["steps_db"] == [-6.02, -6.02, -6.02]
    o = A.measure_occlusion()
    assert o["ok"] and o["high_drop_db"] < o["low_drop_db"] - 6
    for rt in (0.3, 1.2, 3.0):
        assert A.measured_rt60(A.reverb_ir(rt, 3)) == pytest.approx(rt, rel=0.1)
    x = A.pink(1, 3.0)
    y, lim = A.normalise(np.stack([x, x], axis=1))
    assert abs(A.lufs(y) + 16) <= 0.3 and not lim
    burst = np.zeros((A.SR * 2, 2))
    burst[1000] = 1.0
    y, lim = A.normalise(burst)                                   # one click cannot reach -16 LUFS without clipping
    assert lim and np.abs(y).max() <= 10 ** (-1 / 20) + 1e-6


def test_render_judge_and_failures_are_named():
    from app.gamedesk import audio as A
    p = A.clean_plan({"zones": [{"key": "room", "rt60": 0.6}, {"key": "cave", "rt60": 3.0}], "min_d": 2})
    r = A.render(p)
    j = A.judge(r, A.render(p))
    assert j["verdict"] == "PASS", [c for c in j["checks"] if not c["ok"]]
    assert "cone of confusion" in j["limits"]
    r2 = json.loads(json.dumps({k: v for k, v in r.items() if k != "files"}))
    r2["zones"][0]["ok"] = False
    r2["fingerprint"] = "x"
    j = A.judge({**r2, "files": {}}, {**r2, "fingerprint": "y"})
    assert j["verdict"] == "FAIL" and any(not c["ok"] and "room" in c["check"] for c in j["checks"])
    assert not next(c for c in j["checks"] if c["check"] == "same render twice")["ok"]
    for name, data in r["files"].items():
        import wave
        w = wave.open(io.BytesIO(data))
        assert w.getnchannels() == 2 and w.getframerate() == 48000, name


def test_plan_is_clamped_and_words_read():
    from app.gamedesk import audio as A
    p = A.clean_plan({"zones": [{"key": "Big Hall!", "rt60": 99}, {"key": "x", "rt60": "bad"}], "min_d": 0, "max_d": 1e9})
    assert p["zones"][0] == {"key": "bighall", "rt60": 6.0, "wet": 0.3} and p["min_d"] == 0.1 and p["max_d"] == 500
    w = A.from_words("ek cave aur ek hall, max distance 30 m")
    assert {z["key"] for z in w["zones"]} == {"cave", "hall"} and w["max_d"] == 30


# ================================================================ haptics: the checks
def test_library_patterns_differ_and_fit_every_motor():
    from app.gamedesk import haptics as H
    assert H.check(H.LIBRARY, "phone_lra")["errors"] == []
    pats = H.from_words("jump, coin, hit, game over, level up")
    assert set(pats) == {"jump", "coin", "hit", "game_over", "level_up"}
    assert any("shorter than 30 ms" in e for e in H.check(pats, "phone_erm")["errors"])    # as picked: too short for ERM
    for act in H.ACTUATORS:
        fitted, _n = H.fit(pats, act)
        assert H.check(fitted, act)["errors"] == [], act


def test_haptic_failures_are_named():
    from app.gamedesk import haptics as H
    same = {"a": [{"t": 0, "d": 20, "a": 0.6, "s": 0.5}], "b": [{"t": 0, "d": 22, "a": 0.62, "s": 0.5}]}
    assert any("feel the same" in e for e in H.check(same, "phone_lra")["errors"])
    gap = {"x": [{"t": 0, "d": 20, "a": 1, "s": 1}, {"t": 30, "d": 20, "a": 1, "s": 1}]}
    assert any("10 ms gap" in e for e in H.check(gap, "phone_lra")["errors"])
    rows = H.check({"hit": [{"t": 0, "d": 100, "a": 1.0, "s": 0}]}, "phone_lra")["rows"]
    assert rows["hit"]["energy_mj"] == pytest.approx(9.0) and rows["hit"]["per_1000_plays_mwh"] == pytest.approx(2.5)


def test_kit_ahap_android_and_a_compiled_driver():
    from app.gamedesk import haptics as H
    pats = H.fit(H.from_words("jump coin hit"), "drv2605_lra")[0]
    data, info = H.kit_zip(pats, "drv2605_lra")
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    assert {"ios/jump.ahap", "ios/HoolaHaptics.swift", "android/HoolaHaptics.kt", "device/hoola_haptics_drv2605.c"} <= names
    doc = json.loads(z.read("ios/hit.ahap"))
    assert H.ahap_ok(doc) == [] and doc["Pattern"][0]["Event"]["EventType"] == "HapticContinuous"
    assert H.ahap_ok({"Version": 1.0, "Pattern": [{"Event": {"EventType": "Buzz", "Time": -1}}]})
    kt = z.read("android/HoolaHaptics.kt").decode()
    assert "createWaveform" in kt and "var enabled = true" in kt and "intensity" in kt
    assert "hoola_enabled" in z.read("device/hoola_haptics_drv2605.c").decode()
    assert info["ahap_errors"] == []
    assert info["drv2605_compile"]["status"] in ("PASS", "NOT ASSESSED")
    import shutil
    if shutil.which("gcc") or shutil.which("cc") or shutil.which("clang"):
        assert info["drv2605_compile"]["status"] == "PASS", info
        bad = H.compile_c("int main(void) { return undefined_thing; }")
        assert bad["status"] == "FAIL"
    tm, am = H.android_waveform([{"t": 0, "d": 20, "a": 0.5, "s": 0}, {"t": 60, "d": 30, "a": 1.0, "s": 0}])
    assert tm == [0, 20, 40, 30] and am == [0, 128, 0, 255]


# ================================================================ flows into the build + tools / API / UI
def test_audio_and_haptics_go_into_the_build(st, monkeypatch):  # noqa: F811
    from app.gamedesk import audio as A
    from app.gamedesk import guard, packs, template
    from app.gamedesk import haptics as H
    a = A.setup("default", plan={"zones": [{"key": "hall", "rt60": 1.8}]}, studio=st["sid"], run_now=False)
    with pytest.raises(A.AudioError, match="still running"):
        A.approve("default", a["id"])
    out = A.run(a["id"])
    assert out["status"] == "draft" and set(out["files"]) == {"walkaround.wav", "distance.wav", "zones.wav"}
    sig = out["files"]["zones.wav"].split("sig=")[1]
    assert A.audio_file(a["id"], "zones.wav", sig) and A.audio_file(a["id"], "zones.wav", "0" * 16) is None
    h = H.make("default", words="jump aur coin", studio=st["sid"])
    assert h["status"] == "draft" and h["report"]["verdict"] == "PASS"
    assert not {"hoola_audio.gd", "hoola_haptics.gd"} & set(packs.for_game("default", st["gid"]))
    A.approve("default", "A-001")
    H.approve("default", "H-001")
    got = packs.for_game("default", st["gid"])
    assert {"hoola_audio.gd", "hoola_haptics.gd"} <= set(got)                    # (+ HoolaRuntime, v0.425)
    files = {"main.gd": "extends Node\n", **{k: v[0] for k, v in got.items()}}
    assert guard.problems(files) == []
    proj = template.files("t", "portrait", files)["project.godot"]
    assert 'HoolaAudio="*res://hoola_audio.gd"' in proj and 'HoolaHaptics="*res://hoola_haptics.gd"' in proj
    assert "HoolaZone_" in got["hoola_audio.gd"][0] and "user://hoola_haptics.cfg" in got["hoola_haptics.gd"][0]
    bad = H.make("default", patterns={"a": [{"t": 0, "d": 3, "a": 1, "s": 1}]}, actuator="phone_lra")
    assert bad["status"] == "failed" and any("3 ms pulse" in e for e in bad["report"]["errors"])   # her numbers: checked, never changed
    with pytest.raises(H.HapticsError):
        H.approve("default", bad["id"])
    A.apply("default", st["sid"])
    st["svc"].run_job(st["gid"])
    built = list(Path(os.environ["GAME_DIR"]).rglob("v2/proj/hoola_haptics.gd"))
    assert built and (built[0].parent / "hoola_audio.gd").is_file()


def test_tools_api_hire_and_ui(st, monkeypatch):  # noqa: F811
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.gamedesk import audio as A
    from app.main import app
    monkeypatch.setattr(A, "_POOL", type("X", (), {"submit": staticmethod(lambda *a, **k: None)})())
    assert hire.CATALOG["audio_dev"]["live"] and hire.CATALOG["haptics_dev"]["live"]
    soon = [k for k, e in hire.CATALOG.items() if e.get("group") == hire.GAME_GROUP and not e["live"]]
    assert "audio_dev" not in soon and "haptics_dev" not in soon                 # (later batches went live too)
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    with pytest.raises(tools.ToolError, match="is not hired"):   # English since d84057023 (tools wave 3)
        asyncio.run(tools.HANDLERS["game_haptics"](ctx, action="make", words="jump"))
    c = TestClient(app)
    assert c.post("/api/gamedesk/haptics", json={"words": "jump"}).status_code == 400
    hire.hire("default", "audio_dev")
    hire.hire("default", "haptics_dev")
    out = asyncio.run(tools.HANDLERS["game_haptics"](ctx, action="make", words="jump coin hit", actuator="controller"))
    assert out["number"] == "H-001" and out["verdict"] == "PASS" and out["drv2605_compile"] in ("PASS", "NOT ASSESSED")
    out = asyncio.run(tools.HANDLERS["game_audio"](ctx, action="setup", words="cave and hall"))
    assert out["status"] == "testing" and {z["key"] for z in out["zones"]} == {"cave", "hall"}
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_audio"](staff, action="approve", setup="A-001"))
    assert tools.FAMILY_OF["game_audio"] == tools.FAMILY_OF["game_haptics"] == "gamedesk"
    for ask in ("mere game mein 3d sound chahiye", "game ke liye haptic vibration pattern banao"):
        assert "gamedesk" in admit.route(ask), ask
    d = c.get("/api/gamedesk/haptics").json()
    assert d["hired"] and d["sets"][0]["number"] == "H-001" and "drv2605_lra" in d["actuators"]
    kit = d["sets"][0]["files"]["kit.zip"]
    assert c.get(kit).headers["content-type"] == "application/zip"
    assert c.post(f"/api/gamedesk/haptics/{d['sets'][0]['id']}/approve").json()["status"] == "approved"
    a = c.get("/api/gamedesk/audio").json()
    assert a["hired"] and a["setups"][0]["number"] == "A-001" and a["zone_presets"]["cave"] == 3.0
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "gsAudio" in emp and "gsHaptics" in emp and "navigator.vibrate" in emp and "haptics_dev: 'gamedesk'" in emp
    scr = (root / "lib/ui/game_roles_screen.dart").read_text()
    assert "class GameAudioScreen" in scr and "class GameHapticsScreen" in scr
    assert "gamePackNew" in (root / "lib/api.dart").read_text()
    from app.gamedesk import ai
    assert "HoolaAudio" in ai.GUIDE and "HoolaHaptics" in ai.GUIDE


def _godot() -> bool:
    from app.gamedesk import engine
    return bool(engine.find())


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_runs_both_autoloads(tmp_path):
    from app.gamedesk import audio as A
    from app.gamedesk import engine, template
    from app.gamedesk import haptics as H
    main = ('extends Node\nfunc _ready() -> void:\n\tHoolaAudio.set_zone("cave")\n\tvar p := HoolaAudio.player3d(AudioStreamWAV.new())\n'
            '\tadd_child(p)\n\tHoolaAudio.occlude(p, true)\n\tprint("HOOLA_T ", p.bus, " ", HoolaHaptics.names().size())\n'
            '\tHoolaHaptics.set_intensity(0.4)\n\tHoolaHaptics.play("hit")\n')
    scripts = {"main.gd": main, "hoola_audio.gd": A.gd(A.clean_plan({"zones": [{"key": "cave", "rt60": 3}]}), "PASS"),
               "hoola_haptics.gd": H.gd(H.fit(H.from_words("jump hit"), "phone_lra")[0])}
    (tmp_path / "proj").mkdir()
    for name, txt in template.files("t", "landscape", scripts).items():
        (tmp_path / "proj" / name).write_text(txt)
    sm = engine.smoke(tmp_path, frames=60)
    assert sm["ok"], sm["errors"]
    assert "HOOLA_T HoolaOccluded 2" in (tmp_path / "smoke.log").read_text()
