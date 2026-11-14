"""v0.807 HOOLA CINEMA - the Create studio's Cinema section. The video engine is faked at its ONE network seam
(`kie._http`): the sandbox has no key. What is tested is everything Hoola itself decides - the exact request shape
of every model (read from the engine's own documents), what is refused before a credit is spent (no confirm, no
rights tick, no consent, the daily cap, a wrong file), files judged by their bytes, photos re-saved clean, the
finished video copied once to My creations through the link wall, and that nobody reaches another person's files."""
import asyncio
import io
import json
import os
import pathlib

import pytest

from app.cinema import kie, service as S, specs
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = pathlib.Path(__file__).resolve().parents[2]
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 64


def jpg(size=(640, 800), mode="RGB"):
    from PIL import Image
    b = io.BytesIO()
    Image.new(mode, size, (200, 120, 60) if mode == "RGB" else (200, 120, 60, 128)).save(b, "PNG" if mode == "RGBA" else "JPEG")
    return b.getvalue()


def run(c):
    return asyncio.run(c)


@pytest.fixture
def cine(tmp_path, monkeypatch):
    """A keyed server, an engine that records what it is sent, and three of HER files (photo, video, audio)."""
    monkeypatch.chdir(tmp_path)
    from app.config import get_settings
    st = get_settings()
    monkeypatch.setattr(st, "kie_api_key", "kie-secret-key", raising=False)
    monkeypatch.setattr(st, "cinema_page", True, raising=False)
    monkeypatch.setattr(st, "cinema_daily_jobs", 20, raising=False)
    files = {"photo": ("me.png", jpg(mode="RGBA")), "video": ("dance.mp4", MP4), "audio": ("line.wav", WAV),
             "text": ("notes.jpg", b"just some text, not a picture")}
    from app.create import jobs as CJ

    def owner(tenant, fid):
        if tenant != "t1" or fid not in files:
            raise CJ.JobError("not yours")
        return files[fid]
    monkeypatch.setattr(CJ, "_owner_named", owner)
    box = {"calls": [], "state": "generating", "credits": 100.0, "n": 0, "refuse": None}

    async def http(method, url, *, json_body=None, files=None, data=None, params=None, timeout=60):
        box["calls"].append({"method": method, "url": url, "json": json_body, "files": files, "data": data, "params": params})
        if box["refuse"] and "createTask" in url:
            return 200, {"code": box["refuse"], "msg": "refused"}
        if "file-stream-upload" in url:
            box["n"] += 1
            return 200, {"code": 200, "data": {"downloadUrl": f"https://tempfile.example.com/u{box['n']}{pathlib.Path(files['file'][0]).suffix}"}}
        if "createTask" in url:
            box["n"] += 1
            return 200, {"code": 200, "data": {"taskId": f"task{box['n']}"}}
        if "recordInfo" in url:
            done = box["state"] == "success"
            return 200, {"code": 200, "data": {"state": box["state"], "creditsConsumed": 42 if done else None,
                                              "resultJson": json.dumps({"resultUrls": ["https://cdn.example.com/out.mp4"]}) if done else "",
                                              "failMsg": "the face was not clear" if box["state"] == "fail" else ""}}
        if "chat/credit" in url:
            return 200, {"code": 200, "data": box["credits"]}
        return 404, {}
    monkeypatch.setattr(kie, "_http", http)
    S._BAL.update(at=0.0, value=None)
    return box


def created(box):
    return [c["json"] for c in box["calls"] if "createTask" in c["url"]]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.897.0"
    assert "0.897.0+896" in (ROOT / "pubspec.yaml").read_text()


def test_every_request_shape_matches_the_engines_own_documents():
    b = specs.build
    assert b("kling-3.0/motion-control", images=["i"], video="v") == {
        "prompt": "Match the movement of the reference video.", "input_urls": ["i"], "video_urls": ["v"], "mode": "720p", "character_orientation": "video"}
    assert b("wan/2-2-animate-move", images=["i"], video="v") == {"image_url": "i", "video_url": "v", "resolution": "720p", "nsfw_checker": True}
    assert b("wan/2-2-animate-replace", images=["i"], video="v", resolution="580p") == {
        "image_url": "i", "video_url": "v", "resolution": "580p", "nsfw_checker": True}
    assert b("happyhorse/video-edit", prompt="swap the bottle", images=["a", "b"], video="v", extras={"audio_setting": "origin"}) == {
        "prompt": "swap the bottle", "reference_image": ["a", "b"], "video_url": "v", "resolution": "1080p", "audio_setting": "origin"}
    assert b("wan/2-7-videoedit", prompt="x", images=["a"], video="v", avoid="blur")["reference_image"] == "a"      # a string here, a list above
    assert b("kling/ai-avatar-standard", images=["i"], audio="a")["prompt"]                                          # the required prompt is never empty
    assert b("omnihuman-1-5", images=["i"], audio="a") == {"image_url": "i", "audio_url": "a", "output_resolution": "1080"}
    assert b("volcengine/video-to-video-lip-sync", video="v", audio="a") == {"video_url": "v", "audio_url": "a", "mode": "lite"}
    assert b("wan/2-5-text-to-video", prompt="a b c", aspect="9:16", seconds=10)["duration"] == "10"                 # a string for this model
    assert b("bytedance/seedance-2-fast", prompt="a b c", seconds=7, sound=False) == {
        "prompt": "a b c", "resolution": "720p", "aspect_ratio": "9:16", "duration": 7, "generate_audio": False, "nsfw_checker": True}
    assert b("wan/2-5-image-to-video", prompt="steam rises", images=["i"])["image_url"] == "i"
    for bad in (dict(model="wan/2-5-text-to-video", prompt="x", seconds=7), dict(model="kling-3.0/motion-control", images=["i"]),
                dict(model="happyhorse/video-edit", video="v"), dict(model="wan/2-2-animate-move", images=["i"], video="v", resolution="1080p"),
                dict(model="wan/2-7-videoedit", video="v", images=["a", "b"]), dict(model="nope")):
        with pytest.raises(ValueError):
            b(bad.pop("model"), **bad)
    # every tool has a model, and every model that can ask the engine to filter does
    assert all(specs.models_for(t["id"]) for t in specs.TOOLS if t["engine"] == "kie")
    assert len(specs.CAMERA_MOVES) == 27 and len(specs.RESTYLES) >= 14 and len(specs.TOOLS) == 9


def test_presets_are_plain_prompt_text():
    p = specs.still_prompt("an old chai seller at dawn", "film-35", "anamorphic", "35", "f1.4", "golden")
    assert p.startswith("an old chai seller at dawn. Cinematic film still, shot on 35 mm") and "f/1.4" in p and "golden-hour" in p
    assert specs.still_prompt("a diya") == "a diya. Cinematic film still."
    with pytest.raises(ValueError):
        specs.still_prompt("  ")
    assert "Keep the original motion" in specs.restyle_prompt("clay") and specs.restyle_prompt("anime", "more rain").endswith("more rain")
    with pytest.raises(ValueError):
        specs.restyle_prompt("")
    a, c = specs.scene_prompt("mango lassi", 0, "ugc", "orbit"), specs.scene_prompt("mango lassi", 1)
    assert a != c and "mango lassi" in a and "circles" in a


def test_files_are_judged_by_their_bytes_and_photos_are_resaved_clean(cine):
    assert S.sniff(MP4)[0] == "video" and S.sniff(WAV)[0] == "audio" and S.sniff(jpg())[1] == "image/jpeg"
    assert S.sniff(b"<html>")[0] == ""
    out = S.clean_photo(jpg(mode="RGBA"))
    assert out[:3] == b"\xff\xd8\xff"                                   # a transparent PNG becomes a plain JPEG
    with pytest.raises(S.CinemaError):
        S.clean_photo(jpg(size=(120, 120)))                             # too small for every model
    with pytest.raises(S.CinemaError):
        S._take("t1", "text", "image", {"mb": 10}, "Photo")             # named .jpg, but not a picture
    with pytest.raises(S.CinemaError):
        S._take("t2", "photo", "image", {"mb": 10}, "Photo")            # another person's file


def test_motion_transfer_end_to_end(cine):
    body = {"tool": "motion", "model": "kling-3.0/motion-control", "images": ["photo"], "video": "video",
            "resolution": "1080p", "extras": {"character_orientation": "image"}}
    for missing, word in (({}, "right to use"), ({"rights": True}, "agreed"), ({"rights": True, "consent": True}, "Confirm")):
        with pytest.raises(S.CinemaError, match=word):
            run(S.start("t1", {**body, **missing}))
    assert cine["calls"] == []                                          # nothing left the server before her ticks and her tap
    r = run(S.start("t1", {**body, "rights": True, "consent": True, "confirm": True}))
    ups = [c for c in cine["calls"] if "file-stream-upload" in c["url"]]
    assert [u["files"]["file"][2] for u in ups] == ["image/jpeg", "video/mp4"]             # her PNG went out as a clean JPEG
    assert all(u["data"]["uploadPath"] == "hoola-cinema" and "me.png" not in u["files"]["file"][0] for u in ups)   # never her file name
    assert created(cine) == [{"model": "kling-3.0/motion-control", "input": {
        "prompt": "Match the movement of the reference video.", "input_urls": ["https://tempfile.example.com/u1.jpg"],
        "video_urls": ["https://tempfile.example.com/u2.mp4"], "mode": "1080p", "character_orientation": "image"}}]
    j = r["started"][0]
    assert j["tool"] == "motion" and j["status"] == "waiting" and r["today"]["used"] == 1
    assert S.jobs("t2") == []                                           # another person sees none of it

    async def fetch(url):
        assert url == "https://cdn.example.com/out.mp4"
        return "video/mp4", MP4
    S._fetch = fetch
    assert run(S.check("t1", j["id"]))["status"] == "generating"
    cine["state"] = "success"
    done = run(S.check("t1", j["id"]))
    assert done["ok"] and done["credits"] == 42 and done["item_id"].startswith("cr_")
    from app.create import jobs as CJ
    it = CJ.shelf("t1")[0]
    assert it["kind"] == "video" and it["meta"]["source"] == "Hoola Cinema" and it["meta"]["ai_made"] is True
    n = len(cine["calls"])
    run(S.check("t1", j["id"]))
    assert len(cine["calls"]) == n and len(CJ.shelf("t1")) == 1           # a finished job is never asked or saved again
    pub = run(S.overview("t1"))["jobs"][0]
    assert "task" not in pub and "url" not in pub and "kie-secret-key" not in json.dumps(run(S.overview("t1")))
    with pytest.raises(S.CinemaError):
        run(S.check("t2", j["id"]))


def test_a_result_link_must_be_a_public_https_video(cine):
    r = run(S.start("t1", {"tool": "animate", "model": "wan/2-5-image-to-video", "images": ["photo"], "prompt": "steam rises",
                           "camera": "dolly-in", "confirm": True}))
    assert created(cine)[0]["input"]["prompt"] == "steam rises A slow, smooth dolly in towards the subject."
    j = r["started"][0]
    cine["state"] = "success"

    async def fetch(url):
        return "text/html", b"<html>not a video</html>"
    S._fetch = fetch
    done = run(S.check("t1", j["id"]))
    assert done["ok"] and not done["item_id"] and "not a video" in done["save_error"]
    S._update("t1", j["id"], save_error="", url="http://169.254.169.254/latest")
    assert run(S.check("t1", j["id"]))["save_error"]                     # a private address is never fetched


def test_a_saved_character_vouches_and_a_real_person_needs_a_yes(cine):
    with pytest.raises(S.CinemaError, match="yes"):
        S.character_add("t1", "Meera", "person", ["photo"])
    with pytest.raises(S.CinemaError):
        S.character_add("t1", "Meera", "person", ["text"], consent=True)       # not a photo
    with pytest.raises(S.CinemaError):
        S.character_add("t1", "", "made", ["photo"])
    c = S.character_add("t1", "Meera", "person", ["photo", "photo"], consent=True, note="blue kurta")
    assert c["consent_at"] > 0 and len(c["photos"]) == 2
    m = S.character_add("t1", "Gullu the mascot", "made", ["photo"])
    assert m["consent_at"] == 0
    assert S.character_photo("t1", c["id"], 1).read_bytes()[:3] == b"\xff\xd8\xff"
    with pytest.raises(S.CinemaError):
        S.character_photo("t2", c["id"], 0)
    # swap with the saved character: no consent tick is asked, her rights tick still is
    with pytest.raises(S.CinemaError, match="right to use"):
        run(S.start("t1", {"tool": "swap", "character": c["id"], "video": "video", "confirm": True}))
    run(S.start("t1", {"tool": "swap", "character": c["id"], "video": "video", "rights": True, "confirm": True}))
    assert created(cine)[0] == {"model": "wan/2-2-animate-replace", "input": {
        "image_url": "https://tempfile.example.com/u1.jpg", "video_url": "https://tempfile.example.com/u2.mp4", "resolution": "480p", "nsfw_checker": True}}
    # lip sync drives the face IN the video, so a saved character never vouches for it
    with pytest.raises(S.CinemaError, match="agreed"):
        run(S.start("t1", {"tool": "lipsync", "character": c["id"], "video": "video", "audio": "audio", "rights": True, "confirm": True}))
    S.character_remove("t1", c["id"])
    assert [x["name"] for x in S.characters("t1")] == ["Gullu the mascot"]


def test_a_talking_photo_speaks_her_typed_words_in_a_hoola_voice(cine, monkeypatch):
    from app.create import service as CS
    said = []

    async def voice(text, voice_name="", language="Hindi", style="friendly", speed=1.0, tenant=""):
        said.append((text, voice_name, language, tenant))
        return {"bytes": WAV, "ext": ".wav", "voice": "Kore", "seconds": 3}
    monkeypatch.setattr(CS, "voice", voice)
    run(S.start("t1", {"tool": "talk", "model": "omnihuman-1-5", "images": ["photo"], "text": "Namaste Akola", "voice": "Kore",
                       "language": "Marathi", "consent": True, "confirm": True}))
    assert said == [("Namaste Akola", "Kore", "Marathi", "t1")]
    inp = created(cine)[0]["input"]
    assert inp["audio_url"].endswith(".wav") and inp["image_url"].endswith(".jpg") and "prompt" not in inp
    with pytest.raises(S.CinemaError, match="too long"):
        run(S.start("t1", {"tool": "talk", "model": "omnihuman-1-5", "images": ["photo"], "text": "x" * 2000, "consent": True, "confirm": True}))
    with pytest.raises(S.CinemaError, match="audio"):
        run(S.start("t1", {"tool": "talk", "images": ["photo"], "consent": True, "confirm": True}))
    run(S.start("t1", {"tool": "talk", "images": ["photo"], "audio": "audio", "consent": True, "confirm": True}))
    assert created(cine)[1]["model"] == "kling/ai-avatar-standard" and created(cine)[1]["input"]["prompt"]


def test_restyle_edit_and_what_hoola_does_not_make(cine):
    run(S.start("t1", {"tool": "restyle", "look": "madhubani", "video": "video", "rights": True, "confirm": True}))
    assert created(cine)[0]["model"] == "happyhorse/video-edit" and "Madhubani folk painting" in created(cine)[0]["input"]["prompt"]
    with pytest.raises(S.CinemaError, match="look"):
        run(S.start("t1", {"tool": "restyle", "video": "video", "rights": True, "confirm": True}))
    with pytest.raises(S.CinemaError, match="does not make"):
        run(S.start("t1", {"tool": "edit", "prompt": "make her nude", "video": "video", "rights": True, "confirm": True}))
    with pytest.raises(S.CinemaError, match="does not do"):
        run(S.start("t1", {"tool": "edit", "model": "wan/2-2-animate-replace", "prompt": "x", "video": "video", "rights": True, "confirm": True}))
    with pytest.raises(S.CinemaError, match="not a video"):
        run(S.start("t1", {"tool": "edit", "prompt": "swap the cup", "video": "photo", "rights": True, "confirm": True}))
    assert len(created(cine)) == 1


def test_the_factory_writes_different_scenes_and_starts_one_confirmed_batch(cine, monkeypatch):
    from app.studio import service as SS

    async def write(system, prompt, n):
        return 'Here you go: ["A kulhad of lassi on a wet counter.", "A child takes the first sip.", "Mangoes fall into a blender."]'
    monkeypatch.setattr(SS, "_write", write)
    r = run(S.factory_scenes("mango lassi at our shop", 3, "ugc", "orbit", "Reels"))
    assert r["written_by"] == "model" and len(r["scenes"]) == 3 and all("circles" in s for s in r["scenes"])

    async def broken(system, prompt, n):
        raise RuntimeError("no model")
    monkeypatch.setattr(SS, "_write", broken)
    r2 = run(S.factory_scenes("mango lassi at our shop", 4))
    assert r2["written_by"] == "rule" and len(set(r2["scenes"])) == 4 and r2["note"]
    assert cine["calls"] == []                                            # writing scenes spends nothing
    body = {"model": "wan/2-5-text-to-video", "scenes": r["scenes"], "aspect": "9:16", "seconds": 5}
    with pytest.raises(S.CinemaError, match="Confirm"):
        run(S.factory_start("t1", body))
    out = run(S.factory_start("t1", {**body, "confirm": True}))
    assert len(out["started"]) == 3 and len({j["batch"] for j in out["started"]}) == 1 and out["today"]["used"] == 3
    assert [c["input"]["duration"] for c in created(cine)] == ["5", "5", "5"]
    with pytest.raises(S.CinemaError):
        run(S.factory_start("t1", {**body, "scenes": ["x"] * 7, "confirm": True}))


def test_the_daily_cap_and_an_empty_account_refuse_plainly(cine, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "cinema_daily_jobs", 2, raising=False)
    go = {"tool": "animate", "model": "wan/2-5-image-to-video", "images": ["photo"], "prompt": "steam", "confirm": True}
    run(S.start("t1", go)); run(S.start("t1", go))
    n = len(cine["calls"])
    with pytest.raises(S.CinemaError, match="limit of 2") as e:
        run(S.start("t1", go))
    assert e.value.status == 429 and len(cine["calls"]) == n               # refused before any upload
    cine["refuse"] = 402
    monkeypatch.setattr(get_settings(), "cinema_daily_jobs", 20, raising=False)
    with pytest.raises(S.CinemaError, match="no credits") as e:
        run(S.start("t1", go))
    assert e.value.status == 402 and len(S.jobs("t1")) == 2                # nothing is listed for a job that never started
    monkeypatch.setattr(get_settings(), "kie_api_key", "", raising=False)
    with pytest.raises(S.CinemaError) as e:
        run(S.start("t1", go))
    assert e.value.status == 409 and "KIE_API_KEY" in str(e.value)
    ov = run(S.overview("t1"))
    assert ov["key_set"] is False and ov["setup"] and ov["connected"]["rupee_price_before"] is False


def test_the_key_never_leaves_in_an_error(cine, monkeypatch):
    async def http(method, url, **k):
        return 422, {"code": 422, "msg": "bad Bearer kie-secret-key for kie-secret-key"}
    monkeypatch.setattr(kie, "_http", http)
    with pytest.raises(kie.KieError) as e:
        run(kie.create("wan/2-5-text-to-video", {}))
    assert "kie-secret-key" not in str(e.value) and e.value.code == "BAD_INPUT"


def test_routes_are_mounted_behind_the_switch_and_no_foreign_code(site_env, monkeypatch):  # noqa: F811
    main = (ROOT / "server/app/main.py").read_text()
    assert "_cinema_router(require_key, current_tenant)" in main and '"cinema": bool(getattr(st, "cinema_page", False))' in main
    src = "".join((ROOT / "server/app/cinema" / f).read_text() for f in ("service.py", "specs.py", "kie.py", "api.py"))
    for word in ("higgsfield", "Higgsfield", "MATAI", "muapi", "composio", "airtable"):
        assert word not in src
    js = (ROOT / "server/app/static/console/cinema.js").read_text()
    assert "data-v=" not in js and "innerHTML = o." not in js and "higgsfield" not in js.lower()
    html = (ROOT / "server/app/static/console/v2.html").read_text()
    assert html.index("/static/console/cinema.js?v=") < html.index("/static/console/studio.js?v=")


OV = {"enabled": True, "key_set": True, "setup": "", "credits_left": 1234.5, "refresh_error": "", "today": {"used": 1, "cap": 20, "left": 19},
      "connected": S.connected() | {"engine": True}, "voice_ready": True, "voices": {"female": {"Kore": "Confident"}, "male": {"Puck": "Upbeat"}},
      "languages": ["Hindi", "Marathi", "English"], "character_kinds": [{"id": k, "label": v} for k, v in S.CHAR_KINDS.items()],
      "characters": [{"id": "ch_aaaaaaaaaaaa", "name": "<b>Meera</b>", "kind": "person", "note": "", "created": 1, "photos": 2}],
      "jobs": [{"id": "cj_1", "tool": "motion", "model": "kling-3.0/motion-control", "model_label": "Kling 3.0 Motion Control", "title": "<i>Dance</i>",
                "status": "generating", "done": False, "ok": False, "error": "", "credits": None, "item_id": "", "created": 1762850000},
               {"id": "cj_2", "tool": "swap", "model": "wan/2-2-animate-replace", "model_label": "Wan Animate Replace", "title": "Swap", "status": "fail",
                "done": True, "ok": False, "error": "The face was not clear.", "credits": None, "item_id": "", "created": 1762850000}],
      **specs.public()}


def test_the_page_in_a_real_browser(arena_server):  # noqa: F811
    """Hoola Cinema opens inside Create: the hub lists nine tools and Characters, every tool page opens with no script
    error and no sideways scroll, her text is never run as HTML, a job cannot start without her ticks, and the
    request that leaves carries the model, her ticks and confirm."""
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs, sent, scenes, toasts = [], [], [], []
    pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
    pg.on("dialog", lambda d: d.accept())
    pg.route("**/api/console/config", lambda r: r.fulfill(json={"app": "Hoola", "v2": True, "stream": True, "sessions": True, "panel": True,
                                                                   "projects": True, "human": True, "cinema": True}))
    pg.route("**/api/cinema", lambda r: r.fulfill(json=OV))
    pg.route("**/api/cinema/characters/**", lambda r: r.fulfill(body=jpg(), content_type="image/jpeg"))
    pg.route("**/api/create/items*", lambda r: r.fulfill(json={"items": [
        {"id": "cr_v1", "kind": "video", "title": "My reel", "file": "cr_v1.mp4", "mime": "video/mp4", "size": 10, "created": 1762850000}]}))
    pg.route("**/api/create/items/cr_v1", lambda r: r.fulfill(body=MP4, content_type="video/mp4"))
    pg.route("**/api/cinema/start", lambda r: (sent.append(r.request.post_data_json), r.fulfill(json={"started": [], "today": OV["today"]})))
    pg.route("**/api/cinema/factory/scenes", lambda r: (scenes.append(r.request.post_data_json),
                                                         r.fulfill(json={"scenes": ["Scene <one>", "Scene two"], "written_by": "rule", "note": "Written by rule."})))
    pg.route("**/api/cinema/factory/start", lambda r: (sent.append(r.request.post_data_json), r.fulfill(json={"started": [{}, {}], "asked": 2, "stopped": "", "today": OV["today"]})))
    pg.goto(base + "/console/")
    pg.wait_for_selector("#composer")
    pg.locator(".sn[data-v='creative']").click()
    pg.wait_for_selector("#cstudio button.sn[data-go='cinema']")
    assert pg.locator("#cstudio #snav button.sn[data-go]").first.get_attribute("data-go") != "artcraft"
    pg.locator("#cstudio button.sn[data-go='cinema']").click()
    pg.wait_for_selector("#cstudio .cn-stats")
    hub = pg.locator("#cstudio #view").text_content()
    assert pg.locator("#cstudio .tools .tool").count() == 10                          # nine tools + Characters
    assert "1,235" in hub and "1 of 20" in hub and "Not there yet" in hub and "<i>Dance</i>" in hub and "The face was not clear." in hub
    assert pg.locator("#cstudio #view i i, #cstudio #view b b").count() == 0           # her titles are text, never markup
    shots = os.environ.get("CONSOLE_SHOTS")

    def snap(name):
        if shots:
            pg.wait_for_timeout(700)
            pg.screenshot(path=f"{shots}/cn-{name}.png")
    snap("hub")
    for tool, said in [("still", "Focal length"), ("motion", "Body direction follows"), ("swap", "Wan Animate Replace"), ("edit", "What to change"),
                       ("restyle", "Madhubani"), ("talk", "Words to speak"), ("lipsync", "Volcengine Lip Sync"), ("animate", "Bullet time"),
                       ("factory", "How many clips"), ("characters", "A real person")]:
        pg.locator(f"#cstudio .tools [data-ct='{tool}']").click()
        pg.wait_for_selector("#cstudio .cn-head")
        t = pg.locator("#cstudio #view").text_content()
        assert said in t, tool
        assert pg.evaluate("""() => { const R = document.querySelector('#cstudio').shadowRoot, v = R.querySelector('#view'), p = R.querySelector('.panel');
            return v.scrollWidth <= v.clientWidth + 1 && !!p && [...R.querySelectorAll('.panel .pbody > *, .panel .pfoot > *')].every(e => e.getBoundingClientRect().right <= p.getBoundingClientRect().right + 1); }"""), tool
        snap(tool)
        pg.locator("#cstudio .cn-head [data-ct='hub']").click()
        pg.wait_for_selector("#cstudio .cn-stats")
    assert errs == [], errs
    # motion transfer: the saved character vouches (no consent tick shown), the rights tick is still required
    pg.locator("#cstudio .tools [data-ct='motion']").click()
    pg.wait_for_selector("#cstudio [data-cnchar]")
    assert pg.locator("#cstudio #cnConsent").count() == 1 and pg.locator("#cstudio #cnRights").count() == 1
    pg.locator("#cstudio [data-cnchar]").click()
    pg.locator("#cstudio #pop button", has_text="Meera").click()
    pg.locator("#cstudio [data-cnchar] b", has_text="Meera").wait_for()
    assert pg.locator("#cstudio #cnConsent").count() == 0 and pg.locator("#cstudio [data-cnchar] b b").count() == 0
    pg.locator("#cstudio [data-cnshelf='video']").click()
    pg.locator("#cstudio #pop button", has_text="My reel").click()
    pg.locator("#cstudio .cn-slot b", has_text="My reel").wait_for()
    pg.locator("#cstudio #cnPrompt").fill("keep the smile")
    pg.locator("#cstudio [data-cnres='1080p']").click()
    pg.locator("#cstudio #cnGo").click()
    pg.wait_for_timeout(300)
    assert sent == []                                                                  # no rights tick, nothing sent
    assert pg.locator("#cstudio #cnPrompt").input_value() == "keep the smile"         # and what she typed is still there
    pg.locator("#cstudio #cnRights").check()
    pg.locator("#cstudio #cnGo").click()
    pg.wait_for_timeout(500)
    assert len(sent) == 1
    b = sent[0]
    assert b["tool"] == "motion" and b["model"] == "kling-3.0/motion-control" and b["character"] == "ch_aaaaaaaaaaaa" and b["video"] == "cr_v1"
    assert b["rights"] is True and b["confirm"] is True and b["resolution"] == "1080p" and b["prompt"] == "keep the smile" and b["images"] == []
    # the factory: scenes are written free, shown as text, edited, then one batch
    pg.locator("#cstudio .cn-head [data-ct='hub']").click()
    pg.locator("#cstudio .tools [data-ct='factory']").click()
    pg.wait_for_selector("#cstudio #cnTopic")
    pg.locator("#cstudio #cnTopic").fill("mango lassi at our shop")
    pg.locator("#cstudio [data-cncount='-1']").click()
    pg.locator("#cstudio #cnWrite").click()
    pg.wait_for_selector("#cstudio [data-cnscene='1']")
    assert scenes == [{"topic": "mango lassi at our shop", "count": 2, "look": "", "camera": "auto", "platform": "Reels / Shorts"}]
    assert pg.locator("#cstudio [data-cnscene='0']").input_value() == "Scene <one>"
    pg.locator("#cstudio [data-cnscene='0']").fill("A kulhad of lassi")
    snap("factory-scenes")
    pg.locator("#cstudio #cnGo").click()
    pg.wait_for_timeout(500)
    assert sent[1]["scenes"] == ["A kulhad of lassi", "Scene two"] and sent[1]["confirm"] is True and sent[1]["aspect"] == "9:16"
    # the Video page now offers every camera move
    pg.locator("#cstudio button.sn[data-go='video']").click()
    pg.wait_for_selector("#cstudio [data-vcam]")
    assert pg.locator("#cstudio [data-vcam]").count() == 26
    if shots:
        pg.locator("#cstudio button.sn[data-go='cinema']").click()
        pg.locator("#cstudio .cn-head [data-ct='hub']").click()
        pg.wait_for_selector("#cstudio .cn-stats")
        snap("hub")
        pg.locator("#cstudio .tools [data-ct='characters']").click()
        snap("characters")
        pg.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        pg.locator("#cstudio button.sn[data-go='cinema']").click()
        pg.wait_for_selector("#cstudio .cn-head, #cstudio .cn-stats")
        snap("dark")
    assert errs == [], errs
