"""v0.999.169 HOOLA INTERACTIVE REBUILD (owner: "GO BUILD" on the design canvas; contract docs/HOOLA_INTERACTIVE_REBUILD.md):
the video speaks in a Vocal voice, a face engine she chooses makes her photo talk (price card first, her tap), the
Engines page reads what is really connected, live agents answer only from her facts (on her website too, with a minute
cap), B-roll shots without people, app keys + signed webhooks, the Interactive chat plans drafts, and the vendors are
called in the shapes their own specs give."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.interactive import apps as AP
from app.interactive import engines as EN
from app.interactive import live as LV
from app.interactive import studio as S
from app.interactive import vendors as VD

DRAFT = {"title": "Diwali offer", "closing": "Order today",
         "scenes": [{"say": "Is Diwali, apni mithas double karein.", "look": {"kind": "title", "text": "Diwali offer"}},
                    {"say": "Kaju katli par 20 percent ki chhoot.", "look": {"kind": "price", "new": "Rs 512", "old": "Rs 640"}}]}
ASK = "A Diwali offer video for my sweet shop - 20% off kaju katli, now Rs 512 instead of Rs 640"
PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


@pytest.fixture()
def ix(env, monkeypatch, tmp_path):
    monkeypatch.setenv("INTERACTIVE_PAGE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(S, "_root", lambda: tmp_path)
    monkeypatch.setattr(S, "_brain", lambda system, prompt: json.loads(json.dumps(DRAFT)))
    S._JOBS.clear()
    LV._VISITS.clear()
    yield tmp_path
    S._JOBS.clear()
    get_settings.cache_clear()


def keys(monkeypatch, **kw):
    for k, v in kw.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()


def face(tmp_path):
    p = tmp_path / "me.png"
    p.write_bytes(PNG)
    return S.add_avatar("default", "Meghana", str(p), consent=True, filename="me.png")


def wav_bytes(n=24000):
    import io
    import wave
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00\x00" * n)
    return b.getvalue()


def wait_done(pid, s=10):
    t = time.time()
    while time.time() - t < s:
        j = S.job_view("default", pid)
        if j["done"]:
            return j
        time.sleep(0.05)
    raise AssertionError("the make did not finish")


# ------------------------------------------------------------------ engines + price
def test_engines_page_reads_what_is_connected(ix, monkeypatch):
    v = EN.view("default")
    jobs = {e["job"] for e in v["engines"]}
    assert jobs == {"video", "live", "broll"}
    kling = next(e for e in v["engines"] if e["id"] == "kling")
    assert not kling["ready"] and kling["status"] == "Add KIE_API_KEY"
    assert next(e for e in v["engines"] if e["id"] == "voice_only")["ready"]
    keys(monkeypatch, KIE_API_KEY="k-test")
    assert next(e for e in EN.view("default")["engines"] if e["id"] == "kling")["ready"]
    assert EN.set_default("default", "kling")["video"] == "kling"
    with pytest.raises(EN.EngineError, match="not connected"):
        EN.set_default("default", "heygen")
    assert "k-test" not in json.dumps(EN.view("default"))                    # a key never leaves the server


def test_price_card_before_a_paid_face(ix, monkeypatch):
    q = EN.quote("kling", 30, voice_credits=4)
    assert q["face_credits"] == round(3.03 * 0.5 / 0.001) and q["credits"] == q["face_credits"] + 4
    with pytest.raises(EN.EngineError, match="Confirm the price"):
        EN.check_quote(q, "")
    EN.check_quote(q, q["key"])
    EN.check_quote(EN.quote("hoola", 30, voice_credits=4), "")              # Hoola standard: only the voice, no price tap


def test_face_engine_needs_a_face_and_the_tap(ix, monkeypatch):
    keys(monkeypatch, KIE_API_KEY="k-test")
    p = S.draft("default", ASK, engine="kling")
    assert p["engine"] == "kling"
    assert any("pick a face" in w for w in S.engine_problems("default", p))
    a = face(ix)
    S.save("default", p["id"], {"avatar_id": a["id"], "face_layout": "full"})
    with pytest.raises(S.StudioError, match="Confirm the price"):
        S.make("default", p["id"], voicer=lambda s, l: b"RIFF")
    said, made = [], {}

    def voicer(sentence, lang):
        said.append(sentence)
        return wav_bytes()

    def fake_face(eid, photo, name, wav, secs, cancel, on_wait):
        made.update(eid=eid, photo=photo, wav=len(wav))
        return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 2000

    q = S.quote_for("default", S.project("default", p["id"]))
    S.make("default", p["id"], quote_key=q["key"], voicer=voicer, face=fake_face)
    j = wait_done(p["id"])
    assert j["status"] == "ready", j
    assert said == [s["say"] for s in p["scenes"]] and made["eid"] == "kling" and made["photo"] == PNG
    v = S.project("default", p["id"])["video"]
    assert v["engine"] == "kling" and v["ai_mark"] and S.video_path("default", p["id"]).is_file()


def test_hoola_standard_speaks_in_a_vocal_voice(ix, monkeypatch):
    from app.studio import frames
    got = {}

    def film(tenant, spec, files=None, out_name="", on_stage=None, cancel=None, voicer=None, voice_out=None):
        got["line"] = voicer("Namaste", "hi")
        out = ix / "f.mp4"
        out.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100)
        return {"ok": True, "mp4_path": str(out), "duration_s": 5}

    p = S.draft("default", ASK, lang="mr")                                  # Marathi and any other Vocal language
    assert p["lang"] == "mr"
    S.make("default", p["id"], film=film, voicer=lambda s, l: b"WAV:" + s.encode())
    assert wait_done(p["id"])["status"] == "ready" and got["line"] == b"WAV:Namaste"
    import inspect
    assert {"voicer", "voice_out"} <= set(inspect.signature(frames.do_avatar_film).parameters)


def test_frames_use_the_voicer_not_the_lab(ix, monkeypatch):
    import shutil
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe is not on this machine")
    from app.studio import frames
    from app.interactive import lab
    monkeypatch.setattr(lab, "configured", lambda: False)
    seen = []
    import wave, io

    def wav():
        b = io.BytesIO()
        with wave.open(b, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b"\x00\x00" * 24000)
        return b.getvalue()

    monkeypatch.setattr(frames, "do_render", lambda tenant, html, files, out_name="": {"ok": True, "mp4_path": "x"})
    from app.videoedit import captions
    monkeypatch.setattr(captions, "whisper_words", lambda *a, **k: None)
    res = frames.do_avatar_film("default", {"shape": "talking_head", "lang": "hi", "scenes": [{"say": "Namaste ji", "look": {"kind": "none"}}]},
                                voicer=lambda s, l: (seen.append(s), wav())[1], voice_out=str(ix / "v.wav"))
    assert res["ok"] and seen == ["Namaste ji"] and (ix / "v.wav").stat().st_size > 1000


# ------------------------------------------------------------------ live agents
def test_live_agent_answers_only_from_her_facts(ix):
    a = LV.agent_save("default", {"name": "Shop helper", "knows": "Open 9 am to 9 pm. Kaju katli Rs 1,100 a kg.", "lang": "en"})
    assert LV.answer(LV._find(S._load("default"), a["id"]), "price?", think=lambda s, p: {"answer": "Kaju katli is Rs 1,100 a kg."}) == "Kaju katli is Rs 1,100 a kg."
    made_up = LV.answer(LV._find(S._load("default"), a["id"]), "delivery?", think=lambda s, p: {"answer": "Delivery is Rs 40."})
    assert "don't have that" in made_up                                       # 40 is in no fact of hers: never said
    out = LV.ask("default", a["id"], "timings?", think=lambda s, p: {"answer": "We open at 9 am."}, speak=lambda t, l: b"RIFF" + b"\x00" * 60)
    assert out["answer"] == "We open at 9 am." and out["audio"]
    with pytest.raises(LV.LiveError, match="what it should know"):
        LV.agent_save("default", {"name": "x", "knows": "short"})


def test_published_agent_answers_only_on_her_site(ix, monkeypatch):
    a = LV.agent_save("default", {"name": "Shop helper", "knows": "Open 9 am to 9 pm every day of the week.", "lang": "en"})
    pub = LV.publish("default", a["id"], True, ["https://myshop.in/"])
    assert pub["token"].startswith("ia_pub_") and "agent.js" in pub["embed"] and pub["sites"] == ["myshop.in"]
    monkeypatch.setattr(LV, "answer", lambda agent, q, think=None: "We open at 9 am.")
    monkeypatch.setattr(LV.VO, "speaker", lambda *a, **k: (lambda t, l: b"RIFF" + b"\x00" * 60))
    with pytest.raises(LV.LiveError, match="its own website"):
        LV.public_ask(pub["token"], "hi", "https://evil.example", "1.2.3.4")
    assert LV.public_ask(pub["token"], "hi", "https://www.myshop.in", "1.2.3.4")["answer"] == "We open at 9 am."
    for _ in range(LV.VISITOR_RATE[0] - 1):
        LV.public_ask(pub["token"], "hi", "https://myshop.in", "1.2.3.4")
    with pytest.raises(LV.LiveError, match="Too many"):
        LV.public_ask(pub["token"], "hi", "https://myshop.in", "1.2.3.4")
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = c.post(f"/api/interactive/pub/{pub['token']}/ask", json={"text": "hi"}, headers={"origin": "https://myshop.in"})
    assert r.headers.get("access-control-allow-origin") == "*"
    LV.publish("default", a["id"], False)
    with pytest.raises(LV.LiveError, match="not published"):
        LV.public_info(pub["token"], "https://myshop.in")


def test_minutes_cap_stops_an_agent(ix):
    a = LV.agent_save("default", {"name": "Helper", "knows": "Open 9 am to 9 pm every day of the week.", "minutes_day": 1})
    LV._spend("default", a["id"], 61)
    with pytest.raises(LV.LiveError, match="used its minutes"):
        LV.ask("default", a["id"], "hi", think=lambda s, p: {"answer": "ok"}, speak=lambda t, l: b"")


def test_broll_never_people_and_price_first(ix, monkeypatch):
    with pytest.raises(LV.LiveError, match="without people"):
        LV.broll_make("default", "A smiling woman holding a sweet box")
    with pytest.raises(LV.LiveError, match="Confirm the price"):
        LV.broll_make("default", "Slow pan over trays of kaju katli in warm light")
    q = EN.quote("gemini_broll", 6.0)
    row = LV.broll_make("default", "Slow pan over trays of kaju katli in warm light", quote_key=q["key"],
                        runner=lambda *a: b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 500)
    for _ in range(100):
        if next(r for r in S._load("default")["broll"] if r["id"] == row["id"])["status"] != "making":
            break
        time.sleep(0.05)
    assert LV.broll_path("default", row["id"]) is not None


# ------------------------------------------------------------------ app keys + webhooks + doors
def test_app_key_makes_a_draft_and_only_her_key_works(ix, monkeypatch):
    k = AP.key_new("default", "My app")
    assert k["key"].startswith("hi_live_") and "sha" not in json.dumps(AP.keys_list("default"))
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    assert c.get("/api/interactive/v1/engines").status_code == 401
    h = {"Authorization": f"Bearer {k['key']}"}
    r = c.post("/api/interactive/v1/videos", json={"brief": ASK, "lang": "hi"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"].startswith("iv_") and body["quote"]["line"]
    assert c.get(f"/api/interactive/v1/videos/{body['id']}", headers=h).json()["status"] == "draft"
    assert c.get(f"/api/interactive/v1/videos/{body['id']}/file", headers=h).status_code == 404
    AP.key_remove("default", k["id"])
    assert c.get("/api/interactive/v1/engines", headers=h).status_code == 401


def test_webhook_is_signed(ix, monkeypatch):
    from app.vocal import apps as VA
    monkeypatch.setattr(VA, "_RESOLVE", lambda host, port: [(0, 0, 0, "", ("93.184.216.34", 443))])
    sent = []
    monkeypatch.setattr(VA, "_http_post", lambda url, body, headers: (sent.append((url, body, headers)), type("R", (), {"status_code": 200})())[1])
    monkeypatch.setattr(VA, "WAITS", (0,))
    monkeypatch.setattr(AP, "SYNC", True)
    hk = AP.hook_add("default", "https://example.com/hook")
    p = S.draft("default", ASK)
    assert AP.notify("default", "video.ready", p) == 1
    url, body, headers = sent[0]
    t, v1 = headers["X-Hoola-Signature"].split(",")
    assert VA.sign(hk["secret"], int(t[2:]), body) == v1[3:] and json.loads(body)["event"] == "video.ready"
    with pytest.raises(S.StudioError, match="private"):
        monkeypatch.setattr(VA, "_RESOLVE", lambda host, port: [(0, 0, 0, "", ("10.0.0.5", 443))])
        AP.hook_add("default", "https://inside.example.com/x")


# ------------------------------------------------------------------ vendors, in their own shapes
class Fake:
    def __init__(self, answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, method, url, *, headers, json_body=None, files=None, data=None, timeout=120):
        self.calls.append((method, url, headers, json_body))
        return self.answers.pop(0)


def nowait(poll, cancel, on_wait, label, limit_s=0, every=0.0):
    r = poll()
    assert r["state"] == "success", r
    return r


def test_heygen_runway_hedra_shapes(ix, monkeypatch):
    f = Fake([(200, {"data": {"asset_id": "img1"}}), (200, {"data": {"asset_id": "aud1"}}), (200, {"data": {"video_id": "v1"}}),
              (200, {"data": {"status": "completed", "video_url": "https://cdn.heygen.com/v.mp4"}})])
    monkeypatch.setattr(VD, "_http", f)
    assert VD.heygen_face("hk", PNG, "me.png", b"RIFF", 10, None, None, nowait) == "https://cdn.heygen.com/v.mp4"
    body = f.calls[2][3]
    assert body["type"] == "image" and body["image"] == {"type": "asset_id", "asset_id": "img1"} and body["audio_asset_id"] == "aud1"
    assert f.calls[0][2] == {"x-api-key": "hk"}

    f = Fake([(200, {"id": "av1"}), (200, {"status": "READY"}), (200, {"id": "t1"}), (200, {"status": "SUCCEEDED", "output": ["https://r.example/o.mp4"]})])
    monkeypatch.setattr(VD, "_http", f)
    assert VD.runway_face("rk", PNG, "me.png", b"RIFF", 10, None, None, nowait) == "https://r.example/o.mp4"
    assert f.calls[0][2]["X-Runway-Version"] == "2024-11-06" and f.calls[2][3]["model"] == "gwm1_avatars"
    assert f.calls[2][3]["avatar"] == {"type": "custom", "avatarId": "av1"} and f.calls[2][3]["speech"]["type"] == "audio"

    f = Fake([(201, {"url": "https://h.example/i"}), (201, {"url": "https://h.example/a"}), (202, {"job_id": "j1"}),
              (200, {"status": "COMPLETED"}), (200, {"outputs": [{"url": "https://h.example/o.mp4"}]})])
    monkeypatch.setattr(VD, "_http", f)
    assert VD.hedra_face("id:sec", PNG, "me.png", b"RIFF", 10, None, None, nowait) == "https://h.example/o.mp4"
    inp = f.calls[2][3]["input"]
    assert f.calls[0][2]["Authorization"] == "Key id:sec" and {"prompt", "aspect_ratio", "resolution", "start_image", "audio"} <= set(inp)


def test_vendor_refusal_is_said_and_scrubbed(ix, monkeypatch):
    monkeypatch.setattr(VD, "_http", Fake([(402, {"error": {"message": "balance too low for key hk-secret"}})]))
    with pytest.raises(EN.EngineError, match="no credit left") as e:
        VD._heygen_asset("hk-secret", PNG, "f.png", "image/png")
    assert "hk-secret" not in str(e.value)


def test_live_face_passes(ix, monkeypatch):
    agent = {"name": "Helper", "face_ref": "face_123", "knows": "Open 9 to 9", "opening": "Hello"}
    f = Fake([(200, {"session_token": "simli-tok"})])
    monkeypatch.setattr(VD, "_http", f)
    s = VD.simli_session("sk", agent)
    assert s["token"] == "simli-tok" and s["sample_rate"] == 16000 and f.calls[0][3]["faceId"] == "face_123"
    f = Fake([(200, {"sessionToken": "anam-tok"})])
    monkeypatch.setattr(VD, "_http", f)
    assert VD.anam_session("ak", agent)["token"] == "anam-tok" and f.calls[0][3]["personaConfig"]["enableAudioPassthrough"] is True
    f = Fake([(200, {"conversation_url": "https://tavus.daily.co/abc", "conversation_id": "c1"})])
    monkeypatch.setattr(VD, "_http", f)
    assert VD.tavus_session("tk", agent)["url"].startswith("https://") and f.calls[0][3]["pal_id"] == "face_123"
    with pytest.raises(EN.EngineError, match="face id"):
        VD.simli_session("sk", {"name": "x"})


def test_gemini_omni_shot_shape(ix, monkeypatch):
    import base64
    f = Fake([(200, {"steps": [{"type": "model_output", "content": [{"type": "video", "data": base64.b64encode(b"MP4").decode()}]}]})])
    monkeypatch.setattr(VD, "_http", f)
    assert VD.gemini_video("gk", "A shop counter", 6, "9:16", None, None, nowait) == b"MP4"
    b = f.calls[0][3]
    assert b["model"] == "gemini-omni-1.2-flash" and b["response_format"] == {"type": "video", "aspect_ratio": "9:16", "resolution": "720p", "duration": "6s"}


# ------------------------------------------------------------------ the chat + the page
def test_interactive_chat_is_its_own_and_plans_drafts(ix, monkeypatch):
    import asyncio
    from app import interactivechat as IC
    from app.agent import create_tools as CT
    from app.agent.tools import Ctx, ToolError
    c = IC.new_chat("default")
    assert IC.is_interactive(c["id"]) and IC.owns("default", c["id"])
    assert "talking_video" in IC.block("default", c["id"])
    with pytest.raises(ToolError, match="Interactive page"):
        asyncio.run(CT._talking_video(Ctx(tenant_id="default", conversation_id="not-a-chat"), {"brief": ASK}))
    r = asyncio.run(CT._talking_video(Ctx(tenant_id="default", conversation_id=c["id"]), {"brief": ASK, "language": "hi"}))
    assert r["status"] == "draft" and "nothing is made" in r["note"]
    assert IC.chat_items("default", c["id"])[0]["quote"]["line"]
    from app import callconv
    assert '"books", "interactive")' in Path(callconv.__file__).read_text("utf-8")


def test_console_page_is_the_new_frame():
    root = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    assert "data-v=" not in js and "Interactive chat" in js and "'Faces and voices'" in js
    for page in ("chat", "studio", "templates", "apps", "avatars", "voices", "live", "projects", "brand", "engines", "developers", "settings"):
        assert f"    {page}() {{" in js, page
    assert "Not connected yet" not in js                                     # every control is wired or said plainly
    assert all(line.startswith(("#hxRoot", "@", " ", "}", "/*", "")) for line in css.splitlines() if line and not line.startswith(("   ", "  ")))
    html = (root / "v2.html").read_text("utf-8")
    assert "interactive2.css" in html
