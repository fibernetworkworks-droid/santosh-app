"""v0.157 Video Studio, best model per job: the router (Wan 3.0 / Seedance 2.5 / MiniMax H3 / Gemini Omni Flash / Sync 3),
painted opening pictures (Nano Banana Pro) with the character photo as reference, Hindi lines in our own voice +
Sync 3 lip sync (talk and dialogue shots), Claude storyboard planner, Lyria music, automatic review of paid takes.
Fake OpenRouter / Sync / Google servers (studio_fakes) return real MP4s; the picture, voice and music models are stubbed."""
import asyncio
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import studio_fakes as fakes  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
T = "default"
P = "Chai Stall Reel"


def ff(*a):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)


def _her(tmp: Path, name: str, *args) -> str:
    from app import chatfiles
    p = tmp / name
    ff(*args, str(p))
    return chatfiles.store(T, name, p.read_bytes())["file_id"]


def _jpeg(w=1080, h=1920) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), (200, 120, 40)).save(b, "JPEG")
    return b.getvalue()


@pytest.fixture
def fake(env, monkeypatch, tmp_path):
    srv = fakes.serve(0)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    for k, v in {"OPENROUTER_API_KEY": "test-or", "STUDIO_OPENROUTER_URL": base + "/openrouter/api/v1",
                 "SYNC_API_KEY": "test-sync", "STUDIO_SYNC_URL": base + "/sync",
                 "GEMINI_API_KEY": "test-gemini", "STUDIO_GEMINI_URL": base + "/google/v1beta",
                 "STUDIO_POLL_S": "0.2", "STUDIO_ALLOW_PRIVATE": "1", "STUDIO_MONTH_USD": "60"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    fakes.LOG.clear()
    from app.notebook import media
    from app.studio import service as ss
    from app.videoedit import brain
    painted = []

    def painter(prompt, aspect, refs):
        painted.append({"prompt": prompt, "aspect": aspect, "refs": list(refs)})
        return _jpeg(*ss.SIZES.get(aspect, (1080, 1920)))
    monkeypatch.setattr(ss, "_painter", painter)
    said = []
    monkeypatch.setattr(media, "tts_chunk", lambda text, voices=None, voice="": said.append((text, voice)) or b"\x01\x00" * 24000 * 2)
    looks = {"score": 8}
    monkeypatch.setattr(brain, "look", lambda png, system, prompt: {"matches": True, "score": looks["score"], "problems": ["hands"]})
    yield {"base": base, "painted": painted, "said": said, "looks": looks}
    srv.shutdown()
    ss._studios.clear()
    ss._watchers.clear()
    ss._assembling.clear()
    ss._planning.clear()


async def _settle(project: str = P, seconds: float = 120):
    from app.studio import service as ss
    for _ in range(3):
        for t in list(ss._bg_tasks) + list(ss._planning.values()):
            await asyncio.wait_for(asyncio.shield(t), seconds)
        st = await ss.studio(T)
        await st.wait(project, seconds)
        for t in list(ss._watchers.values()):
            await asyncio.wait_for(asyncio.shield(t), seconds)
        await asyncio.sleep(0.05)


SHOTS = [
    {"kind": "scene", "prompt": "Meera pours steaming masala chai into a clay kulhad at her roadside stall, warm morning light",
     "duration": 5, "characters": ["Meera"], "camera": "dolly_in", "caption": "Asli masala chai"},
    {"kind": "product", "prompt": "A steaming clay kulhad of chai on a wooden counter, hero light, slow turn", "duration": 6},
    {"kind": "talk", "dialogue": "Namaste! Aaj hi aaiye, pehla cup bilkul free.", "speaker": "Meera", "characters": ["Meera"],
     "duration": 4, "prompt": "her chai stall at dusk with fairy lights"},
    {"kind": "dialogue", "prompt": "Meera laughs with a customer at the stall", "dialogue": "Bhaiya, kya chai hai!",
     "duration": 5, "characters": ["Meera"]},
    {"kind": "link", "prompt": "the camera glides from the stall out to the busy evening street", "duration": 6},
]


def _setup(tmp_path):
    from app.studio import service as ss
    photo = _her(tmp_path, "meera.png", "-f", "lavfi", "-i", "color=c=0xd9a066:s=600x800:d=1", "-frames:v", "1")

    async def go():
        await ss.create(T, P, "9:16", "reel", "Hindi", "A reel for Meera's chai stall: first cup free today", "")
        await ss.character(T, P, "Meera", "young Indian woman in a yellow saree with a red bindi", [photo], consent=True)
        return await ss.storyboard(T, P, SHOTS)
    return asyncio.run(go())


def test_router_picks_the_best_model_per_shot(fake, tmp_path):
    from app.studio import service as ss
    r = _setup(tmp_path)
    assert r["shots"] == 5

    async def go():
        st = await ss.studio(T)
        assert st.load(P)["characters"]["Meera"]["voice"] == "Kore"          # a woman's line in a woman's voice
        hd = {x["shot"]: x for x in st.estimate(P, "final")["shots"]}
        assert {k: v["model"] for k, v in hd.items()} == {"s1": "or-wan-3", "s2": "or-minimax-h3", "s3": "sync-3",
                                                          "s4": "or-wan-3", "s5": "gemini-omni-flash"}
        assert hd["s3"]["lipsync"] and hd["s4"]["lipsync"] and not hd["s1"]["lipsync"]
        pr = {x["shot"]: x["model"] for x in st.estimate(P, "premium")["shots"]}
        assert pr["s1"] == "or-seedance-2.5" and pr["s2"] == "or-seedance-2.5" and pr["s3"] == "sync-3"
        dr = {x["shot"]: x["model"] for x in st.estimate(P, "draft")["shots"]}
        assert dr["s1"] == "or-seedance-2-fast" and dr["s2"] == "or-minimax-h3-max"
        # the Hindi line is not given to the scene model to speak (it would garble it): our voice + lip sync instead
        q = st.build(st.load(P), st.load(P)["shots"][3], "or-wan-3", "final")
        assert "no audible words" in q.prompt and "Bhaiya" not in q.prompt and "no watermark" in q.prompt
        v = ss.view(T, st.load(P))
        assert set(v["estimates"]) == {"draft", "final", "premium"} and v["estimates"]["premium"]["inr"] > v["estimates"]["final"]["inr"]
        assert [s["kind"] for s in v["shots"]] == ["scene", "product", "talk", "dialogue", "link"]
    asyncio.run(go())


def test_pictures_first_then_hd_with_hindi_lip_sync(fake, tmp_path):
    from app.studio import service as ss
    _setup(tmp_path)

    async def go():
        # 1. opening pictures: a card, then Nano Banana paints each shot with Meera's photo as the reference
        card = await ss.keyframes(T, P)
        assert card["waiting_owner"] and card["inr"] > 0 and "tasveer" in card["say"]
        assert not fake["painted"]
        await ss.decide(T, card["waiting_owner"], True)
        await _settle()
        assert len(fake["painted"]) == 5
        s1 = next(x for x in fake["painted"] if "masala chai" in x["prompt"])
        assert s1["aspect"] == "9:16" and len(s1["refs"]) == 1 and "reference photo 1" in s1["prompt"] and "No text" in s1["prompt"]
        s3 = next(x for x in fake["painted"] if "looking into the camera" in x["prompt"])
        assert "mouth closed" in s3["prompt"]
        st = await ss.studio(T)
        p = st.load(P)
        assert all(s.get("keyframe") for s in p["shots"])
        assert abs(p["spent_usd"] - 5 * ss.KEYFRAME_USD) < 1e-6
        assert all(s["keyframe"].startswith("/api/studio/files/") for s in ss.view(T, p)["shots"])
        # 2. the free preview is now an animatic made from those pictures
        g = await ss.generate(T, P, "preview", ["s1"])
        assert g["usd"] == 0
        await _settle()
        # 3. HD for the scene, the talk shot and the dialogue shot: one card, then the best model per shot
        fakes.LOG.clear()
        card = await ss.generate(T, P, "final", ["s1", "s3", "s4"])
        a = st.load(P)["approvals"][card["waiting_owner"]]
        assert a["keyframes"] == 0 and a["lipsync"] == 2 and set(a["models"]) == {"or-wan-3", "sync-3"}
        fake["looks"]["score"] = 5                                           # the review will call these weak
        await ss.decide(T, card["waiting_owner"], True)
        await _settle()
        subs = [x for x in fakes.LOG if x.get("path") == "/openrouter/api/v1/videos" and "body" in x]
        assert {b["body"]["model"] for b in subs} == {"alibaba/wan-3.0"} and len(subs) == 2
        b1 = next(b for b in subs if "masala chai" in b["body"]["prompt"])
        assert b1["body"]["frame_images"][0]["frame_type"] == "first_frame" and b1["fetched"] == ["data"]
        assert b1["body"]["resolution"] == "1080p"
        gens = [x for x in fakes.LOG if x.get("path") == "/sync/v2/generate"]
        assert len(gens) == 2 and all(g["body"]["model"] == "sync-3" for g in gens)
        kinds = sorted(tuple(i["type"] for i in g["body"]["input"]) for g in gens)
        assert kinds == [("image", "audio"), ("video", "audio")]              # talk = portrait; dialogue = the scene re-synced
        puts = [x for x in fakes.LOG if x.get("method") == "PUT"]
        assert puts and all(x["xkey"] is None for x in puts)                  # the key never goes to the upload URL
        assert any("Namaste" in t for t, v in fake["said"]) and all(v == "Kore" for t, v in fake["said"])
        p = st.load(P)
        takes = {sid: vs[-1] for sid, vs in p["variants"].items()}
        assert takes["s3"]["quality"] == "final" and takes["s4"]["lipsync"] and not takes["s4"]["lipsync_error"]
        assert (takes["s1"].get("look") or {}).get("score") == 5
        assert any("[actual]" in e["what"] for e in p["ledger"])
        v = ss.view(T, p)
        s4 = next(s for s in v["shots"] if s["id"] == "s4")
        assert s4["take_list"][-1]["lipsync"] and s4["take_list"][-1]["score"] == 5 and s4["take_list"][-1]["url"]
        # 4. HD for a shot without a picture: the picture is painted in the same card, then the video
        await st.update(P, lambda q: q["shots"][1].update(keyframe=None))
        n = len(fake["painted"])
        card = await ss.generate(T, P, "final", ["s2"])
        a = st.load(P)["approvals"][card["waiting_owner"]]
        assert a["keyframes"] == 1 and a["paint_ids"] == ["s2"] and "tasveer" in card["say"]
        await ss.decide(T, card["waiting_owner"], True)
        await _settle()
        assert len(fake["painted"]) == n + 1
        b2 = [x for x in fakes.LOG if x.get("path") == "/openrouter/api/v1/videos" and "body" in x][-1]
        assert b2["body"]["model"] == "minimax/hailuo-3" and b2["body"]["frame_images"]
    asyncio.run(go())


def test_talk_shot_needs_its_picture_and_sync_key(fake, tmp_path, monkeypatch):
    from app.studio import service as ss
    _setup(tmp_path)

    async def go():
        st = await ss.studio(T)
        with pytest.raises(Exception) as e:
            await st.generate(P, "final", ["s3"])
        assert "picture first" in str(e.value)
    asyncio.run(go())


def test_planner_writes_and_fixes_the_storyboard(fake, tmp_path, monkeypatch):
    from app.studio import service as ss
    calls = []
    good = {"title": "Chai", "shots": [
        {"id": "s1", "kind": "scene", "prompt": "A young woman in a yellow saree pours chai at a roadside stall at sunrise, "
         "steam rising, warm golden light, slow dolly in, cosy mood", "duration": 6, "camera": "dolly_in",
         "characters": ["Meera", "Nobody"], "caption": "Subah ki chai", "transition": "fade"},
        {"id": "s2", "kind": "talk", "prompt": "the stall at dusk", "dialogue": "Pehla cup free!", "speaker": "Meera",
         "characters": ["Meera"], "duration": 4, "camera": "close_up"},
        {"id": "s3", "kind": "product", "prompt": "A clay kulhad of chai on a wooden counter, hero light", "duration": 5,
         "camera": "spin360"}]}

    async def write(system, prompt, max_tokens=12000):
        calls.append((system, prompt))
        if len(calls) == 1:
            bad = json.loads(json.dumps(good))
            bad["shots"][1]["kind"] = "monologue"
            return json.dumps(bad)
        return "```json\n" + json.dumps(good) + "\n```"
    monkeypatch.setattr(ss, "_write", write)
    photo = _her(tmp_path, "meera.png", "-f", "lavfi", "-i", "color=c=0xd9a066:s=600x800:d=1", "-frames:v", "1")

    async def go():
        await ss.create(T, P, "9:16", "reel", "Hindi", "", "")
        await ss.character(T, P, "Meera", "young Indian woman in a yellow saree", [photo], consent=True)
        with pytest.raises(ss.StudioJobError):
            await ss.plan(T, P, "", 20)
        r = await ss.plan(T, P, "Chai stall reel, first cup free", 20)
        assert r["status"] == "planning"
        await _settle()
        p = (await ss.studio(T)).load(P)
        assert [s["kind"] for s in p["shots"]] == ["scene", "talk", "product"]
        assert p["shots"][0]["characters"] == ["Meera"] and p["shots"][2].get("camera") is None
        assert p["brief"] == "Chai stall reel, first cup free"
        assert len(calls) == 2 and "monologue" in calls[1][1] and "Hindi" in calls[0][1] and "dolly_in" in calls[0][0]
        assert "Meera" in calls[0][0]
    asyncio.run(go())


def test_lyria_music_is_a_card_then_a_real_track(fake, tmp_path, monkeypatch):
    from app.studio import service as ss
    _setup(tmp_path)
    mp3 = tmp_path / "song.mp3"
    ff("-f", "lavfi", "-i", "sine=f=440:d=4", str(mp3))
    asked = []
    monkeypatch.setattr(ss, "_lyria", lambda prompt: asked.append(prompt) or mp3.read_bytes())

    async def go():
        card = await ss.music(T, P, mood="festive")
        assert card["waiting_owner"] and card["usd"] == ss.MUSIC_USD and not asked
        await ss.decide(T, card["waiting_owner"], True)
        await _settle()
        p = (await ss.studio(T)).load(P)
        assert p["music"]["file"].endswith(".mp3") and "Instrumental only" in asked[0] and "shehnai" in asked[0]
        assert any("music" in e["what"] for e in p["ledger"])
        assert ss.view(T, p)["music"]
    asyncio.run(go())
