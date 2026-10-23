"""v0.68 Hoola Video Studio (the owner's hoola-studio engine) inside Hoola, against fake OpenRouter / fal servers that
follow the documented APIs and return real MP4 files (her tests/fakes.py).

brief -> character from HER photo (consent asked) -> storyboard (problems listed together) -> free preview -> paid draft
as a price card (nothing spent before her tap, monthly ceiling) -> Haan -> real cost recorded -> review -> narration /
music / logo from her files and Hoola's free beds -> final 1080x1920 video with the AI label -> her file + signed link."""
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
import studio_fakes as fakes  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
T = "default"


def ff(*a):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)


def _her(tmp: Path, name: str, *args) -> str:
    from app import chatfiles
    p = tmp / name
    ff(*args, str(p))
    return chatfiles.store(T, name, p.read_bytes())["file_id"]


@pytest.fixture
def fake(env, monkeypatch, tmp_path):
    srv = fakes.serve(0)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    for k, v in {"OPENROUTER_API_KEY": "test-or", "STUDIO_OPENROUTER_URL": base + "/openrouter/api/v1",
                 "STUDIO_FAL_URL": base + "/fal", "STUDIO_POLL_S": "0.2", "STUDIO_ALLOW_PRIVATE": "1",
                 "STUDIO_MONTH_USD": "3", "GEMINI_API_KEY": ""}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    fakes.LOG.clear()
    yield base
    srv.shutdown()
    from app.studio import service as ss
    ss._studios.clear()
    ss._watchers.clear()
    ss._assembling.clear()


async def _settle(tenant: str, project: str, seconds: float = 90):
    from app.studio import service as ss
    st = await ss.studio(tenant)
    await st.wait(project, seconds)
    for t in list(ss._watchers.values()):
        await asyncio.wait_for(asyncio.shield(t), seconds)


def test_studio_end_to_end(fake, tmp_path, monkeypatch):
    from app.studio import service as ss
    from app.videoedit import brain
    monkeypatch.setattr(brain, "look", lambda png, system, prompt: {"matches": True, "score": 8, "problems": []})
    photo = _her(tmp_path, "santosh.png", "-f", "lavfi", "-i", "color=c=0xd9a066:s=600x800:d=1", "-frames:v", "1")
    logo = _her(tmp_path, "logo.png", "-f", "lavfi", "-i", "color=c=orange:s=300x120:d=1", "-frames:v", "1")
    vo = _her(tmp_path, "vo.wav", "-f", "lavfi", "-i", "sine=f=300:d=3")
    P = "Diwali Saree Reel"

    async def go():
        v = await ss.create(T, P, "9:16", "indian_wedding", "Hindi", "Diwali offer reel for a saree shop", "")
        assert v["project"] == P and v["spent_usd"] == 0
        with pytest.raises(ss.StudioJobError):        # a real person's photo needs her word about consent
            await ss.character(T, P, "Santosh", "friendly young Indian man, glasses", [photo], consent=False)
        await ss.character(T, P, "Santosh", "friendly young Indian man, glasses, orange hoodie", [photo], consent=True)
        with pytest.raises(ss.StudioJobError) as e:
            await ss.storyboard(T, P, [{"prompt": "", "duration": 40, "characters": ["Nobody"], "camera": "spin"}])
        assert "unknown character" in str(e.value) and "camera" in str(e.value) and "duration" in str(e.value)
        r = await ss.storyboard(T, P, [
            {"prompt": "Santosh waves at the camera in a diya-lit courtyard at dusk", "duration": 5, "camera": "dolly_in",
             "characters": ["Santosh"], "dialogue": "Namaste! Diwali offer shuru!", "caption": "दिवाली ऑफर शुरू!",
             "transition": "fade", "start_image": "/etc/passwd"},
            {"prompt": "A purple Banarasi silk saree flows on a mannequin, gold border catching the light", "duration": 4,
             "camera": "orbit", "voiceover": "Pure Banarasi silk", "caption": "Pure Banarasi silk"}])
        assert r["shots"] == 2 and r["estimate"]["inr"] > 0
        p = ss._load(T, P)
        assert not p["shots"][0].get("start_image")       # a path from the model is never used, only her file_ids
        # free preview runs at once, no card
        g = await ss.generate(T, P, "preview")
        assert g["started"] == 2 and g["usd"] == 0
        await _settle(T, P)
        assert all(s["state"] == "done" for s in ss.view(T, ss._load(T, P))["shots"])
        # paid draft: a price card, nothing runs or is spent before her tap
        fakes.LOG.clear()
        card = await ss.generate(T, P, "draft")
        assert card["waiting_owner"] and card["inr"] > 0 and "Haan" in card["say"]
        assert not [x for x in fakes.LOG if x.get("path") == "/openrouter/api/v1/videos"]
        p = ss._load(T, P)
        assert p["spent_usd"] == 0 and p["approvals"][card["waiting_owner"]]["status"] == "pending"
        # she says no to a second card -> nothing
        card2 = await ss.generate(T, P, "draft", ["s2"])
        assert (await ss.decide(T, card2["waiting_owner"], False))["status"] == "rejected"
        # Haan -> Seedance 2.0 Fast via OpenRouter with her photo as a reference image
        a = await ss.decide(T, card["waiting_owner"], True)
        assert a["status"] == "approved"
        await _settle(T, P)
        subs = [x for x in fakes.LOG if x.get("path") == "/openrouter/api/v1/videos" and "body" in x]
        b = next(x for x in subs if "waves" in x["body"]["prompt"])
        assert len(subs) == 2 and b["auth"] == "Bearer test-or" and b["body"]["model"] == "bytedance/seedance-2.0-fast"
        assert b["body"]["aspect_ratio"] == "9:16" and b["body"]["resolution"] == "720p"
        assert b["fetched"] == ["data"] and "Reference image 1 shows Santosh" in b["body"]["prompt"]
        assert 'says in Hindi' in b["body"]["prompt"] and "Namaste" in b["body"]["prompt"]
        p = ss._load(T, P)
        real = round(0.0123 * 5, 4) + round(0.0123 * 4, 4)
        assert abs(p["spent_usd"] - real) < 0.001 and all("[actual]" in e["what"] for e in p["ledger"])
        assert all(ss.view(T, p)["shots"][i]["quality"] == "draft" for i in range(2))
        # the month ceiling: a final run bigger than what is left is refused before any card
        with pytest.raises(ss.StudioJobError) as e:
            await ss.generate(T, P, "final", variants=4)
        assert "seema" in str(e.value)
        rv = await ss.review(T, P, "s1")
        assert rv["look"]["score"] == 8 and rv["sheet_url"].startswith("/api/studio/files/")
        assert (await ss.voiceover(T, P, "s2", file_id=vo))["seconds"] > 2
        assert (await ss.music(T, P, mood="festive"))["music"] == "music.wav"
        await ss.logo(T, P, logo)
        r = await ss.assemble(T, P)
        assert r["status"] == "assembling"
        await asyncio.wait_for(asyncio.shield(ss._assembling[P]), 300) if P in ss._assembling else None
        v = ss.view(T, ss._load(T, P))
        assert v["outputs"] and v["outputs"][-1]["file_id"] and not v["outputs"][-1]["preview"]
        return v
    try:
        v = asyncio.run(go())
    finally:
        ss._studios.clear()
    out = v["outputs"][-1]
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    got = c.get(out["url"])
    assert got.status_code == 200 and got.content[4:8] == b"ftyp"
    assert c.get(out["url"].replace("/files/default/", "/files/default/1")).status_code == 404
    f = Path("data/studio/default/projects") / "diwali-saree-reel" / "final"
    mp4 = next(f.glob("*.mp4"))
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(mp4)],
                                     capture_output=True, text=True).stdout)
    vs = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (vs["width"], vs["height"]) == (1080, 1920) and any(s["codec_type"] == "audio" for s in info["streams"])
    from app.db import Message, session
    with session() as s:
        notes = [m.display or "" for m in s.query(Message).filter(Message.role == "assistant").all()]
    assert any("video taiyaar" in n and "AI-generated" in n for n in notes)
    assert any("draft shot taiyaar" in n for n in notes)


def test_tool_api_push_and_guards(fake, tmp_path):
    from app.agent.tools import HANDLERS, TOOLS, Ctx, ToolError
    from app.employee.roles import duty_of
    from app.push import render
    from app.studio import providers
    from app.voice import VOICE_TOOL_NAMES
    ctx = Ctx(tenant_id=T, conversation_id="c1")
    run = lambda **a: asyncio.run(HANDLERS["video_studio"](ctx, **a))  # noqa: E731
    assert "STORYBOARD" in run(action="guide")["guide"]
    m = run(action="models")
    assert "openrouter" in m["ready"] and any(x["model"] == "or-seedance-2" for x in m["models"])
    with pytest.raises(ToolError):
        run(action="show")                               # no project yet
    assert run(action="create", name="Chai ad", aspect="16:9")["aspect"] == "16:9"
    with pytest.raises(ToolError):                       # someone else's / unknown file
        run(action="character", name="X", description="y", file_ids=["file_nothere1"], consent=True)
    run(action="storyboard", shots=[{"prompt": "Masala chai steam rising by a window", "duration": 4, "camera": "dolly_in"}])
    est = run(action="estimate", quality="final")
    assert est["inr"] > 0 and est["shots"][0]["model"] == "or-wan-3"          # v0.157 HD scene = Wan 3.0
    card = run(action="generate", quality="final")
    assert card["waiting_owner"]
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    h = c.get("/api/studio").json()
    assert h["projects"][0]["approvals"][0]["id"] == card["waiting_owner"] and h["month_limit_usd"] == 3
    assert c.post("/api/studio/approvals/sanothere", json={"yes": True}).status_code == 400
    t = render("studio_approval", {"status": "pending", "inr": 51, "project": "Chai ad", "shots": 1}, "Santosh")
    assert t and "₹51" in t[0]
    assert any(x["name"] == "video_studio" for x in TOOLS) and "video_studio" in VOICE_TOOL_NAMES
    assert duty_of("video_studio") == "video"
    # downloads from a provider reply may never reach a local address
    import os
    os.environ.pop("STUDIO_ALLOW_PRIVATE", None)
    with pytest.raises(providers.ProviderError):
        asyncio.run(providers.download("http://127.0.0.1:8077/api/secret", tmp_path / "x.mp4"))
