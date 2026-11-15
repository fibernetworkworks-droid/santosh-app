"""v0.919 REAL CAMERA MOVES (owner: "I WANT REAL VIDEO AT EVERY PLACE OF CAMERA ANGLE NOT ANIMATED"): one real clip per
camera move, made through the hidden showcase film's NORMAL price cards (pictures, then draft clips - her Haan each),
cut by the server into a small looping WebP for the phone tiles."""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_MOVES = ['Auto', 'Static', 'Dolly in', 'Dolly out', 'Crash zoom', 'Orbit', 'Crane up', 'Tracking', 'Pan', 'Drone',
             'Handheld', 'Low angle']


def _go(monkeypatch):
    from app.studio import service as ss
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gem")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-or")
    ss._studios.clear()
    monkeypatch.setattr(ss, "_publish", lambda *a, **k: None)
    monkeypatch.setattr(ss, "_note", lambda *a, **k: None)
    return ss


def test_one_slot_per_phone_move_same_scene_real_camera():
    from app.studio import catalog, showcase as sc
    assert sc.CAM_IDS == ["cam_" + m.lower().replace(" ", "_") for m in APP_MOVES], "the phone's camSlot() names"
    for sid, move, cam in sc.CAMS:
        assert cam is None or cam in catalog.CAMERA
    shots = sc._cam_shots()
    assert all(sc.CAM_SCENE in s["prompt"] and s["duration"] == 5 and s["kind"] == "scene" for s in shots)
    assert {s["id"]: s.get("camera") for s in shots}["cam_orbit"] == "orbit"


def test_an_older_showcase_gets_the_camera_shots_and_keeps_its_own(env, monkeypatch):
    ss = _go(monkeypatch)
    from app.studio import showcase as sc

    async def go():
        st = await ss.studio(sc.owner())
        st.create(sc.NAME, aspect="3:4", style="cinematic", language="Hindi", budget_usd=12.0, brief="old")
        st.storyboard_set(sc.NAME, [{"id": "film0", "prompt": "old one", "duration": 5, "kind": "scene"}])
        await sc.setup()
        p = st.load(sc.NAME)
        assert [s["id"] for s in p["shots"]] == ["film0"] + sc.CAM_IDS
        assert p["shots"][0]["prompt"] == "old one"
        await sc.setup()
        assert len(st.load(sc.NAME)["shots"]) == 13, "twice = no doubles"
    asyncio.run(go())


def test_camera_cards_pictures_first_then_draft_clips(env, monkeypatch):
    ss = _go(monkeypatch)
    from app.studio import showcase as sc

    async def go():
        await sc.setup()
        (await ss.studio(sc.owner())).painter = lambda prompt, aspect, refs: b"x"   # the picture engine is "on" (never called)
        r = await sc.ask_camera()
        assert r["waiting_owner"] and abs(r["usd"] - 12 * ss.KEYFRAME_USD) < 1e-6
        await ss.decide(sc.owner(), r["waiting_owner"], False)
        st = await ss.studio(sc.owner())
        d = st.pdir(sc.NAME) / "keyframes"
        d.mkdir(parents=True, exist_ok=True)

        def fn(q):
            for s in q["shots"]:
                if s["id"].startswith("cam_"):
                    f = d / f"{s['id']}.jpg"
                    f.write_bytes(b"\xff\xd8\xff\xd9")
                    s["keyframe"] = str(f)
        await st.update(sc.NAME, fn)
        seen = {}

        async def gen(tenant, project, quality="preview", shot_ids=None, **k):
            seen.update(quality=quality, ids=shot_ids)
            return {"waiting_owner": "x"}
        monkeypatch.setattr(ss, "generate", gen)
        await sc.ask_camera()
        assert seen == {"quality": "draft", "ids": sc.CAM_IDS}
        o = sc.status()
        assert o["cams"] == 12 and o["cam_pictures"] == 12 and o["cam_clips"] == 0
    asyncio.run(go())


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg")
def test_tile_is_a_small_looping_webp(tmp_path):
    from app.studio import showcase as sc
    clip = tmp_path / "c.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=480x640:rate=24", "-t", "3",
                    "-pix_fmt", "yuv420p", str(clip)], check=True)
    t = sc.tile_of(clip)
    b = t.read_bytes()
    assert b[:4] == b"RIFF" and b[8:12] == b"WEBP" and b"ANIM" in b[:200]
    assert len(b) < 1_500_000
    assert sc.tile_of(clip) == t, "made once, then kept"


def test_routes_and_phone():
    main = (ROOT / "server/app/main.py").read_text()
    assert '"camera": showcase.ask_camera' in main and 'else "image/webp" if kind == "tile"' in main
    kit = (ROOT / "lib/ui/create/create_kit.dart").read_text()
    assert "class CrCamArt extends StatelessWidget" in kit and "/api/studio/showcase/file/${store.camSlot(move)}?kind=tile" in kit
    assert "String camSlot(String move) => 'cam_${move.toLowerCase().replaceAll(' ', '_')}';" in kit
    film = (ROOT / "lib/ui/create/create_film.dart").read_text()
    assert "_CamMaker(store: widget.store)" in film and "'/api/studio/showcase/camera'" in film
    assert "art: CrCamArt(store: _store" in (ROOT / "lib/ui/create/create_home.dart").read_text()
