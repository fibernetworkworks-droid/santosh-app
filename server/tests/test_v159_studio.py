"""v0.159 The full Video Studio in the app: her choices on the 'Naya video' screens (voice, captions + look, music, quality),
the price sheet line by line (same numbers as the card), live progress, places and products as references, caption
styles in the final video, add / remove / redo a shot, 'Rok do', hide a project, better brief, voice samples, API routes.
Same fake providers as v0.157 (studio_fakes)."""
import asyncio
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_v157_studio import SHOTS, T, _her, _settle, fake, ff  # noqa: E402,F401  (fake = the shared fixture)

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
P = "Gautam Buddha"


@pytest.fixture
def studio(fake, tmp_path, monkeypatch):
    from app.studio import service as ss
    mp3 = tmp_path / "song.mp3"
    ff("-f", "lavfi", "-i", "sine=f=330:d=4", str(mp3))
    monkeypatch.setattr(ss, "_lyria", lambda prompt: mp3.read_bytes())
    yield fake
    ss._painting.clear()
    ss._reviewing.clear()


def _make(tmp_path, prefs=None):
    from app.studio import service as ss
    photo = _her(tmp_path, "meera.png", "-f", "lavfi", "-i", "color=c=0xd9a066:s=600x800:d=1", "-frames:v", "1")

    async def go():
        v = await ss.create(T, P, "9:16", "cinematic", "Hindi", "Bodhi tree at dawn", "", prefs)
        await ss.character(T, P, "Meera", "young Indian woman in a yellow saree", [photo], consent=True)
        await ss.storyboard(T, P, SHOTS)
        return v
    return asyncio.run(go())


def test_her_choices_and_the_price_sheet_match_the_card(studio, tmp_path):
    from app.studio import service as ss
    v = _make(tmp_path, {"voice": "female", "captions": True, "caption_style": "words", "music": "calm", "quality": "final"})
    assert v["prefs"]["caption_style"] == "words" and v["prefs"]["music"] == "calm" and v["prefs"]["voice"] == "Kore"

    async def go():
        st = await ss.studio(T)
        view = ss.view(T, st.load(P))
        hd = view["estimates"]["final"]
        assert hd["keyframes"] == 5 and hd["music"] == "calm" and hd["lipsync_shots"] == 2
        parts = hd["video_inr"] + hd["keyframes_inr"] + hd["lipsync_inr"] + hd["music_inr"]
        assert abs(parts - hd["inr"]) <= 3                                   # rupee rounding only
        assert view["next"]["kind"] == "keyframes" and view["next"]["inr"] == ss._inr(5 * ss.KEYFRAME_USD)
        assert view["shots"][0]["model_label"] == "Wan 3.0" and view["shots"][2]["model_label"] == "Sync 3 lip sync"
        assert view["phase"] == "storyboard" and view["shots"][0]["phase"] == "new"
        card = await ss.generate(T, P, "final")
        a = st.load(P)["approvals"][card["waiting_owner"]]
        assert a["usd"] == hd["usd"] and a["music"] == "calm" and a["keyframes"] == 5 and a["video_inr"] == hd["video_inr"]
        assert abs(a["cap_usd"] - (a["usd"] - 5 * ss.KEYFRAME_USD - ss.MUSIC_USD)) < 1e-6
        await ss.decide(T, card["waiting_owner"], True)
        await _settle(P)
        p = st.load(P)
        assert p["music"]["mood"] == "calm"                                  # her music came with the same tap
        assert all(s.get("keyframe") for s in p["shots"])
        assert p["spent_usd"] <= a["usd"] + 1e-6
        view = ss.view(T, p)
        pr = view["progress"]
        assert pr["total"] == 5 and pr["done"] == 5 and pr["pct"] == 100 and pr["eta_s"] == 0 and pr["spent_inr"] > 0
        assert view["step"] == 5 and view["next"]["kind"] == "assemble" and view["music_info"]["url"]
        assert all(s["phase"] == "done" for s in view["shots"])
        s3 = next(s for s in view["shots"] if s["id"] == "s3")
        assert s3["line_url"]                                                 # her spoken line can be played back
        assert view["estimates"]["final"]["music"] == ""                      # music is not charged twice
    asyncio.run(go())


def test_places_and_products_keep_their_look(studio, tmp_path):
    from app.studio import service as ss
    _make(tmp_path)
    river = _her(tmp_path, "river.png", "-f", "lavfi", "-i", "color=c=0x3e6b8b:s=800x600:d=1", "-frames:v", "1")
    pack = _her(tmp_path, "pack.png", "-f", "lavfi", "-i", "color=c=0xffb15c:s=600x600:d=1", "-frames:v", "1")

    async def go():
        st = await ss.studio(T)
        await ss.character(T, P, "Nadi kinara", "bodhi tree by a calm river", [river], consent=False, kind="place")
        await ss.character(T, P, "Chai packet", "red tea packet", [pack], consent=False, kind="product")
        with pytest.raises(ss.StudioJobError):
            await ss.character(T, P, "Raju", "a man", [river], consent=False, kind="person")
        p = st.load(P)
        assert p["characters"]["Nadi kinara"]["kind"] == "place"
        shot = {**p["shots"][0], "characters": ["Nadi kinara", "Meera", "Chai packet"]}
        prompt, refs = st.keyframe_prompt(p, shot)
        assert "The setting is Nadi kinara" in prompt and "same product shape" in prompt and len(refs) == 3
        assert st.speaker_of(p, {"characters": ["Nadi kinara", "Meera"]}) == "Meera"
        v = ss.view(T, p)
        kinds = {c["name"]: c["kind"] for c in v["character_list"]}
        assert kinds == {"Meera": "person", "Nadi kinara": "place", "Chai packet": "product"}
        assert all(c["image"] for c in v["character_list"])
    asyncio.run(go())


def test_caption_styles_and_the_final_video(studio, tmp_path):
    from app.studio import service as ss
    from app.studio.studio import caption_texts
    w = caption_texts("मन शांत ठेवा तेच खरे सुख", 6, "words")
    assert len(w) == 3 and w[0]["start"] == 0.2 and w[-1]["end"] <= 6 and all(not x["box"] for x in w)
    assert caption_texts("Asli chai", 5, "plain")[0]["box"] is True
    assert caption_texts("Asli chai", 5, "nonsense")[0]["box"] is False      # unknown = bold
    _make(tmp_path)
    logo = _her(tmp_path, "logo.png", "-f", "lavfi", "-i", "color=c=white:s=200x200:d=1", "-frames:v", "1")

    async def go():
        st = await ss.studio(T)
        await ss.logo(T, P, logo, "top-right")
        v = await ss.settings(T, P, {"caption_style": "plain", "logo_position": "bottom", "style": "documentary"})
        assert v["prefs"]["caption_style"] == "plain" and v["logo_info"]["position"] == "bottom" and v["style"] == "documentary"
        with pytest.raises(ss.StudioJobError):
            await ss.settings(T, P, {"logo_position": "moon"})
        await ss.generate(T, P, "preview")
        await _settle(P)
        r = await ss.assemble(T, P)
        assert r["status"] == "assembling"
        await asyncio.wait_for(asyncio.shield(ss._assembling[P]), 300) if P in ss._assembling else None
        v = ss.view(T, st.load(P))
        assert v["outputs"] and v["outputs"][-1]["preview"] and v["outputs"][-1]["mb"] > 0
        assert v["next"]["kind"] in ("keyframes", "generate")             # a preview is not the real video yet
    asyncio.run(go())


def test_add_remove_redo_cancel_and_hide(studio, tmp_path, monkeypatch):
    from app.studio import service as ss
    _make(tmp_path)

    async def go():
        st = await ss.studio(T)
        await st.update(P, lambda q: q["shots"][0].update(keyframe=str(st.pdir(P) / "x.jpg")))
        (st.pdir(P) / "x.jpg").write_bytes(b"\xff\xd8\xff")
        v = await ss.add_shot(T, P, {"prompt": "Close-up of the chai cup", "duration": 4, "keyframe": "/etc/passwd"}, after="s1")
        ids = [s["id"] for s in v["shots"]]
        assert ids[1] == "s6" and len(ids) == 6
        p = st.load(P)
        assert p["shots"][0]["keyframe"].endswith("x.jpg")                    # existing pictures stay
        assert not p["shots"][1].get("keyframe")                              # nothing planted from outside
        v = await ss.delete_shot(T, P, "s6")
        assert [s["id"] for s in v["shots"]] == ["s1", "s2", "s3", "s4", "s5"]
        with pytest.raises(ss.StudioJobError):
            await ss.delete_shot(T, P, "nope")
        card = await ss.redo_shot(T, P, "s1", "haath goad mein rakhein")
        assert card["waiting_owner"]
        a = st.load(P)["approvals"][card["waiting_owner"]]
        assert a["shot_ids"] == ["s1"] and a["quality"] == "final"
        assert st.load(P)["shots"][0]["prompt"].endswith("Change: haath goad mein rakhein.")
        card2 = await ss.redo_shot(T, P, "s1", "roshni kam")                  # a second change replaces the first
        assert "goad" not in st.load(P)["shots"][0]["prompt"] and card2["waiting_owner"]
        # Rok do: running shots stop, the watcher ends
        monkeypatch.setattr(st, "poll_s", 5)
        await ss.generate(T, P, "preview")
        r = await ss.cancel(T, P)
        assert r["cancelled"] >= 0
        await _settle(P, 30)
        assert not any(j["state"] in ("queued", "submitted", "running", "retrying") for j in st.load(P)["jobs"].values())
        spent = ss.month_spent(T)
        await ss.hide(T, P)
        assert P not in [x["project"] for x in ss.listing(T)] and ss.month_spent(T) == spent
        assert ss.latest(T) != P
    asyncio.run(go())


def test_better_brief_and_voice_samples(studio, monkeypatch):
    from app.studio import service as ss

    async def write(system, prompt, max_tokens=12000):
        assert "invent prices" in system and "Rs 99" in prompt
        return "Brief: Subah ki chai, Rs 99 ka combo, ant mein line: 'Aaj hi aaiye'"
    monkeypatch.setattr(ss, "_write", write)

    async def go():
        r = await ss.improve_brief("chai combo Rs 99", "Hindi", 20)
        assert r["brief"].startswith("Subah") and "Rs 99" in r["brief"]
        with pytest.raises(ss.StudioJobError):
            await ss.improve_brief("ab", "Hindi")
        s1 = await ss.voice_sample(T, "female", "Marathi")
        s2 = await ss.voice_sample(T, "female", "Marathi")
        assert s1["url"].startswith("/api/studio/files/") and s1["url"] == s2["url"]
        assert any(v == "Kore" for _t, v in studio["said"])
    asyncio.run(go())


def test_api_routes(studio, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.studio import service as ss

    async def write(system, prompt, max_tokens=12000):
        return "Ek shaant subah"
    monkeypatch.setattr(ss, "_write", write)
    h = {"Authorization": "Bearer test-key"}
    with TestClient(app) as c:
        r = c.post("/api/studio/projects", json={"name": P, "brief": "", "voice": "male", "caption_style": "plain",
                                                 "music": "cinematic", "quality": "premium"}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["prefs"]["quality"] == "premium" and r.json()["quality_pref"] == "premium"
        r = c.post(f"/api/studio/projects/{P}/shots", json={"prompt": "Dawn over the river", "duration": 5}, headers=h)
        assert r.status_code == 200, r.text and len(r.json()["shots"]) == 1
        r = c.post(f"/api/studio/projects/{P}/shots", json={"prompt": "Birds fly up", "duration": 4}, headers=h)
        sid = r.json()["shots"][-1]["id"]
        assert c.delete(f"/api/studio/projects/{P}/shots/{sid}", headers=h).status_code == 200
        r = c.post(f"/api/studio/projects/{P}/settings", json={"caption_style": "words", "captions": False}, headers=h)
        assert r.json()["prefs"]["caption_style"] == "words" and r.json()["prefs"]["captions"] is False
        assert c.post("/api/studio/improve", json={"brief": "subah"}, headers=h).json()["brief"] == "Ek shaant subah"
        assert c.get("/api/studio/voice_sample?voice=male&language=Hindi", headers=h).json()["url"]
        home = c.get("/api/studio", headers=h).json()
        assert "calm" in home["moods"] and home["projects"][0]["project"] == P
        assert c.post(f"/api/studio/projects/{P}/cancel", headers=h).json()["cancelled"] == 0
        assert c.delete(f"/api/studio/projects/{P}", headers=h).status_code == 200
        assert not c.get("/api/studio", headers=h).json()["projects"]


def test_ai_made_character_is_painted_once_after_her_tap(studio, tmp_path):
    from app.studio import service as ss
    _make(tmp_path)

    async def go():
        st = await ss.studio(T)
        card = await ss.character_generate(T, P, "Bhikshu", "an old Buddhist monk in a saffron robe", "person", "male")
        a = st.load(P)["approvals"][card["waiting_owner"]]
        assert a["models"] == ["nano-banana-pro"] and a["usd"] == ss.KEYFRAME_USD and "Bhikshu" not in st.load(P)["characters"]
        n = len(studio["painted"])
        await ss.decide(T, card["waiting_owner"], True)
        await _settle(P)
        p = st.load(P)
        c = p["characters"]["Bhikshu"]
        assert c["kind"] == "person" and c["generated"] == "nano-banana-pro" and c["voice"]
        assert len(studio["painted"]) == n + 1 and "reference photo of an old Buddhist monk" in studio["painted"][-1]["prompt"]
        assert any("character Bhikshu" in e["what"] for e in p["ledger"])
        card = await ss.character_generate(T, P, "Ghat", "stone steps down to a calm river at dawn", "place")
        await ss.decide(T, card["waiting_owner"], True)
        await _settle(P)
        assert st.load(P)["characters"]["Ghat"]["kind"] == "place" and studio["painted"][-1]["aspect"] == "16:9"
    asyncio.run(go())
