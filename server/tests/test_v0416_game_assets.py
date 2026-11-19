"""v0.416 ASSET PIPELINE (Hoola Game Engine plan, Phase 4): style-locked art, code-made sounds, music, voice, 3D
models; every file checked in code, paid kinds only after her tap on a price card, nothing in the game before her OK;
approved assets go into the build as files + the HoolaAssets autoload. Model / picture engine / Lyria / 3D Studio
are faked; the sound synthesiser and the image pipeline (keying, fitting, palette) run for real."""
import asyncio
import base64
import io
import json
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)

PAL = ["#101820", "#FFB000", "#E4572E", "#29BF12"]


def _magenta_ball(color=(228, 87, 46), bg=(255, 0, 255), size=512):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (size, size), bg)
    ImageDraw.Draw(img).ellipse((size // 4, size // 4, size * 3 // 4, size * 3 // 4), fill=color)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def ast(st, monkeypatch):  # noqa: F811
    monkeypatch.setenv("GAME_CREW_REVIEW", "off")
    from app.gamedesk import assets as A
    from app.gamedesk import bible as B
    A.ensure_table()
    B.ensure_table()
    B.set_section("default", st["sid"], "style", {"palette": PAL, "tone": "bright"})
    pics = []
    monkeypatch.setattr("app.photogen.generate", lambda prompt, images=None, aspect="1:1", quality="fast": (
        pics.append({"prompt": prompt, "aspect": aspect, "quality": quality}) or (_magenta_ball(), "fake-image")))
    return {**st, "A": A, "B": B, "pics": pics}


def test_sounds_are_made_in_code_and_repeatable(env):
    from app.gamedesk import assets as A
    from app.gamedesk import sfx
    a, pa = sfx.make("coin", 7)
    b, _ = sfx.make("coin", 7)
    c, _ = sfx.make("coin", 8)
    assert a == b and a != c and pa["preset"] == "coin"                                   # same seed = same bytes
    for p in sfx.PRESETS:
        data, _ = sfx.make(p, 1)
        checks, meta = A.check_file("sfx", data, "wav", {}, {})
        assert not checks["errors"], (p, checks)
        assert 0.02 <= meta["seconds"] <= 3 and 0.8 < meta["peak"] < 0.95, p              # -1 dBFS
    with pytest.raises(sfx.SfxError):
        sfx.make("boom", 1)


def test_free_sound_waits_for_her_ok_then_enters_the_game(ast):
    A, S, svc = ast["A"], ast["S"], ast["svc"]
    v = A.request("default", ast["sid"], "sfx", "sfx_coin", "coin", preset="coin", seed=3)
    assert v["status"] == "making" and v["cost_inr"] == 0                                 # free = no card
    v = A.make("default", v["id"])
    assert v["status"] == "draft" and v["version"] == 1 and not v["checks"]["errors"] and v["url"].startswith("/api/gamestudio/asset/")
    assert A.for_game("default", ast["gid"]) is None                                      # nothing before her OK
    v = A.approve("default", ast["sid"], "sfx_coin")
    assert v["approved"] == 1 and v["status"] == "approved"
    gdsrc, files = A.for_game("default", ast["gid"])
    assert "res://assets/sfx_coin.wav" in gdsrc and "func play(" in gdsrc and list(files) == ["assets/sfx_coin.wav"]
    assert 'const CREDITS := ""' in gdsrc                                                 # a code-made sound is not AI art
    calls = ast["calls"]["change"] + ast["calls"]["code"]
    A.apply("default", ast["sid"])
    svc.run_job(ast["gid"])
    g = svc._get("default", ast["gid"])
    proj = svc._vdir(g, 2) / "proj"
    assert (proj / "assets" / "sfx_coin.wav").read_bytes() == (A._dir("default", ast["sid"], "sfx_coin") / "v1.wav").read_bytes()
    assert 'HoolaAssets="*res://hoola_assets.gd"' in (proj / "project.godot").read_text()
    assert svc.get("default", ast["gid"])["version"] == 2 and ast["calls"]["change"] + ast["calls"]["code"] == calls
    assert g.versions[-1]["assets"] == ["assets/sfx_coin.wav"]
    assert any(d["text"].startswith("Asset sfx_coin v1 OK") for d in S.get("default", ast["sid"])["decisions"])


def test_paid_art_needs_her_tap_and_is_style_locked(ast):
    A = ast["A"]
    v = A.request("default", ast["sid"], "sprite", "red_bat", "a red bat with big ears", size=128)
    assert v["status"] == "priced" and v["cost_inr"] == 3 and not ast["pics"]          # nothing spent yet
    card = A.assets("default", ast["sid"])["card"]
    assert card["total_inr"] == 3 and card["items"][0]["key"] == "red_bat"
    with pytest.raises(A.AssetError):
        A.make("default", v["id"])                                                       # not started without the tap
    A.spend("default", ast["sid"], [v["id"]])
    v = A.make("default", v["id"])
    p = ast["pics"][0]["prompt"]
    assert "magenta" in p and "#E4572E" in p and "not from any existing game" in p and ast["pics"][0]["aspect"] == "1:1"
    m = v["meta"]
    assert (m["w"], m["h"]) == (128, 128) and m["clear_edges"] == 1.0 and m["palette_share"] == 1.0 and 0.2 < m["cover"] < 0.9
    assert v["status"] == "draft" and v["spent_inr"] == 3 and not v["checks"]["errors"]
    png = (A._dir("default", ast["sid"], "red_bat") / "v1.png").read_bytes()
    from PIL import Image
    im = Image.open(io.BytesIO(png))
    assert im.mode == "RGBA" and im.getpixel((0, 0))[3] == 0 and "AI-generated" in im.info.get("Comment", "")
    A.approve("default", ast["sid"], "red_bat")
    assert "made with AI" in A.for_game("default", ast["gid"])[0]                         # credits on the title screen


def test_checks_refuse_a_bad_picture_and_strict_snaps(ast, monkeypatch):
    A = ast["A"]
    monkeypatch.setattr("app.photogen.generate", lambda *a, **k: (_magenta_ball(bg=(20, 200, 220)), "fake"))
    v = A.request("default", ast["sid"], "sprite", "ghost", "a ghost")
    A.spend("default", ast["sid"], [v["id"]])
    v = A.make("default", v["id"])
    assert v["status"] == "failed" and "transparent background" in v["error"]             # no magenta -> not keyed
    with pytest.raises(A.AssetError, match="failed its check"):
        A.approve("default", ast["sid"], "ghost")
    monkeypatch.setattr("app.photogen.generate", lambda *a, **k: (_magenta_ball(color=(30, 90, 250)), "fake"))
    v = A.request("default", ast["sid"], "sprite", "blue_ball", "a ball", palette_lock="check")
    A.spend("default", ast["sid"], [v["id"]])
    v = A.make("default", v["id"])
    assert v["meta"]["palette_share"] < 0.5 and any("palette" in w for w in v["checks"]["warnings"])
    v = A.request("default", ast["sid"], "sprite", "blue_ball", "a ball", palette_lock="strict")
    A.spend("default", ast["sid"], [v["id"]])
    v = A.make("default", v["id"])
    assert v["version"] == 2 and v["meta"]["palette_share"] >= 0.99                       # snapped to the palette


def test_background_fits_the_game_screen(ast):
    A = ast["A"]
    v = A.request("default", ast["sid"], "background", "bg_l1", "a busy market at dawn")
    A.spend("default", ast["sid"], [v["id"]])
    v = A.make("default", v["id"])
    assert (v["meta"]["w"], v["meta"]["h"]) == (720, 1280) and ast["pics"][-1]["aspect"] == "9:16" and v["status"] == "draft"


def test_music_voice_and_model(ast, monkeypatch):
    A = ast["A"]

    def tone(seconds, rate=22050):
        import math
        import struct
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
            w.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(i / 8))) for i in range(int(seconds * rate))))
        return buf.getvalue()
    seen = {}

    async def song(**kw):
        seen.update(kw)
        return {"bytes": tone(12), "ext": ".wav", "model": "fake-lyria"}

    async def voice(text, voice_name="", language="Hindi", style="friendly", speed=1.0, tenant=""):
        return {"bytes": tone(1.5), "ext": ".wav", "voice": "Kore"}
    monkeypatch.setattr("app.create.service.song", song)
    monkeypatch.setattr("app.create.service.voice", voice)
    m = A.request("default", ast["sid"], "music", "music_main", "happy chase")
    assert m["status"] == "priced" and m["cost_inr"] == 7
    A.spend("default", ast["sid"], [m["id"]])
    m = A.make("default", m["id"])
    assert seen["vocals"] == "instrumental" and "loop" in seen["brief"]
    assert m["status"] == "draft" and m["history"][0]["url"] and 11 < m["meta"]["seconds"] < 13
    assert (A._dir("default", ast["sid"], "music_main") / "v1.ogg").read_bytes()[:4] == b"OggS"   # web format
    with pytest.raises(A.AssetError, match="text"):
        A.request("default", ast["sid"], "voice", "vo_hello", "greeting")
    vo = A.request("default", ast["sid"], "voice", "vo_hello", "greeting", text="Namaste! Chalo khelein.")
    A.spend("default", ast["sid"], [vo["id"]])
    assert A.make("default", vo["id"])["status"] == "draft"

    from app.blender3d import service as B3
    glb = Path(A._dir("default", ast["sid"], "tmp")) / "x.glb"
    monkeypatch.setattr(B3, "start", lambda tenant, conv, brief, options=None, title="", **k: {"id": "b3d_1"})
    m3 = A.make("default", A.request("default", ast["sid"], "model", "crate", "a wooden crate")["id"])
    assert m3["job"] == "b3d_1" and m3["status"] == "making"
    d = Path(B3._pdir("default", "b3d_1")) / "v1"
    d.mkdir(parents=True, exist_ok=True)
    (d / "crate.glb").write_bytes(b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 64)
    monkeypatch.setattr(B3, "get", lambda tenant, pid: {"status": "done", "version": 1, "number": "3D-0001",
                                                        "exports": {"glb": {"name": "crate.glb"}}, "stats": {"tris": 420}})
    assert A.collect_models("default") == 1
    crate = next(a for a in A.assets("default", ast["sid"])["assets"] if a["key"] == "crate")
    assert crate["status"] == "draft" and crate["meta"]["tris"] == 420 and crate["source"] == "blender"


def test_upload_is_checked_by_its_bytes(ast):
    A = ast["A"]
    v = A.upload("default", ast["sid"], "sprite", "hero", base64.b64encode(_magenta_ball(color=(16, 24, 32))).decode(), "her hero")
    assert v["status"] == "draft" and v["source"] == "her upload" and v["meta"]["w"] == 128
    with pytest.raises(A.AssetError, match="PNG or JPEG"):
        A.upload("default", ast["sid"], "sprite", "bad", base64.b64encode(b"MZ\x90\x00not a picture").decode())
    with pytest.raises(A.AssetError, match="WAV, OGG"):
        A.upload("default", ast["sid"], "sfx", "bad2", base64.b64encode(b"<html>").decode())
    A.approve("default", ast["sid"], "hero")
    assert 'const CREDITS := ""' in A.for_game("default", ast["gid"])[0]                 # her own art is not AI-made


def test_suggest_follows_the_bible(ast):
    A, B = ast["A"], ast["B"]
    B.set_entity("default", ast["sid"], "enemy", {"id": "bat", "name": "Red Bat", "color": "#E4572E"})
    B.set_entity("default", ast["sid"], "item", {"id": "gem", "name": "Gem", "color": "#FFB000"})
    B.set_entity("default", ast["sid"], "level", {"id": "l1", "name": "Market", "order": 1, "waves": [{"enemy": "bat", "count": 2}]})
    sug = {(x["key"], x["kind"]) for x in A.suggest("default", ast["sid"])}
    assert {("bat", "sprite"), ("gem", "icon"), ("bg_l1", "background"), ("sfx_jump", "sfx"), ("music_main", "music")} <= sug
    A.request("default", ast["sid"], "sfx", "sfx_jump", preset="jump")
    assert ("sfx_jump", "sfx") not in {(x["key"], x["kind"]) for x in A.suggest("default", ast["sid"])}


def test_tool_api_links_and_ui(ast, monkeypatch):
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.main import app
    A = ast["A"]
    hire.hire("default", "game_dev")
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    out = asyncio.run(tools.HANDLERS["game_assets"](ctx, action="make", kind="sprite", key="red_bat", words="a red bat"))
    assert out["status"] == "priced" and "ONLY her tap" in out["note"] and not ast["pics"]
    assert "spend" not in json.dumps(tools.HANDLERS["game_assets"].__code__.co_names)        # the tool cannot spend
    out = asyncio.run(tools.HANDLERS["game_assets"](ctx, action="make", kind="sfx", key="sfx_jump", preset="jump"))
    assert out["status"] == "making"
    assert tools.FAMILY_OF["game_assets"] == "gamedesk"
    for ask in ("mere game ke liye sprite banao", "game music chahiye", "game assets dikhao"):
        assert "gamedesk" in admit.route(ask), ask
    c = TestClient(app)
    lst = c.get(f"/api/gamestudio/{ast['sid']}/assets").json()
    rb = next(a for a in lst["assets"] if a["key"] == "red_bat")
    assert lst["card"]["total_inr"] == 3 and rb["status"] == "priced"
    r = c.post(f"/api/gamestudio/{ast['sid']}/assets/spend", json={"ids": [rb["id"]]})
    assert r.status_code == 200 and next(a for a in r.json()["assets"] if a["key"] == "red_bat")["status"] == "making"
    A.make("default", rb["id"])
    url = next(a for a in c.get(f"/api/gamestudio/{ast['sid']}/assets").json()["assets"] if a["key"] == "red_bat")["url"]
    got = c.get(url)
    assert got.status_code == 200 and got.headers["content-type"] == "image/png"
    assert c.get(url.replace("sig=", "sig=x")).status_code == 404
    assert c.post(f"/api/gamestudio/{ast['sid']}/assets/red_bat/approve", json={}).status_code == 200
    assert c.post(f"/api/gamestudio/{ast['sid']}/assets", json={"kind": "sprite", "key": "!!!", "words": ""}).status_code == 400
    assert c.post(f"/api/gamestudio/{ast['sid']}/assets", json={"kind": "sprite", "key": "note", "words": "a fake aadhaar card"}).status_code == 400
    assert ast["S"].get("default", ast["sid"])["assets"]["in_game"] == 1
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "gsAssets" in emp and "/assets/spend" in emp
    assert "GameAssetsScreen" in (root / "lib/ui/game_assets_screen.dart").read_text()
    assert "gameAssetsSpend" in (root / "lib/api.dart").read_text()
