"""Hoola Motion: reels written as code, rendered to MP4 on the server, labelled as AI-made."""
import asyncio
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.motion import ai, music, render
from app.motion import service as mo

PLAN = {"brand": "Sharma Chai Point", "tagline": "Akola ki kadak chai", "emoji": "☕", "evil": "<script>",
        "colors": {"bg1": "#3b0d0c", "bg2": "red", "accent": "#fbbf24", "ink": "#fff7ed"},
        "problem": {"emoji": "😴", "tag": "SUSTI?", "title": "Subah neend nahi jaati?" * 10, "sub": "Chai chahiye"},
        "solution": {"emoji": "☕", "title": "Adrak elaichi wali chai"},
        "steps": [{"emoji": "📱", "title": "WhatsApp pe order"}, {"emoji": "🔥", "title": "5 min mein taiyaar"},
                  {"emoji": "🛵", "title": "Ghar tak delivery"}, {"emoji": "x", "title": "fourth is dropped"}],
        "proof": {"big": "1,200+", "sub": "roz grahak"}, "cta": {"title": "Aaj try kijiye", "phone": "98765 43210", "place": "Akola"}}


def test_clean_keeps_only_safe_known_fields():
    d = mo.clean("explainer", PLAN)
    assert "evil" not in d and d["colors"] == {"bg1": "#3b0d0c", "accent": "#fbbf24", "ink": "#fff7ed"}
    assert len(d["problem"]["title"]) <= 70 and len(d["steps"]) == 3
    r = mo.clean("recipe", {"dish": "Chai", "ingredients": [{"name": "doodh", "qty": "1 cup"}, {"qty": "no name"}], "steps": ["a", "", 5]})
    assert [i["name"] for i in r["ingredients"]] == ["doodh"] and r["steps"] == ["a", "5"]
    assert mo.clean("logo", {"logo": "data:image/png;base64,iVBORw0KGgo="})["logo"].startswith("data:image/png")
    assert mo.clean("logo", {"logo": "https://evil.example/x.png"})["logo"] == ""
    assert mo.clean("logo", {"logo": "data:image/svg+xml;base64,PHN2Zz4="})["logo"] == ""
    assert mo.clean("offer", {"headline": "DIWALI", "items": ["a", "b", "c", "d", "e", "f"]})["items"] == ["a", "b", "c", "d", "e"]


def test_plan_uses_the_owner_words(env, monkeypatch):
    seen = []
    monkeypatch.setattr(ai, "_llm_json", lambda prompt: seen.append(prompt) or dict(PLAN))
    p = mo.plan("explainer", "Meri chai ki dukaan, Akola, phone 98765 43210")
    assert p["title"] == "Sharma Chai Point" and p["data"]["cta"]["phone"] == "98765 43210"
    assert "NEVER invent facts" in seen[0] and "98765 43210" in seen[0]
    with pytest.raises(mo.MotionError):
        mo.plan("explainer", "")
    with pytest.raises(mo.MotionError):
        mo.plan("custom", "anything")


def test_music_beds():
    for mood in ("upbeat", "calm", "festive"):
        x = music.make(mood, 4)
        assert len(x) == 4 * music.SR and 0.3 < abs(x).max() <= 0.81
    assert music.write("none", 5, Path("/tmp/none.wav")) is None


class Inline:
    def submit(self, fn, *a):
        fn(*a)


@pytest.fixture()
def fake_render(env, monkeypatch, tmp_path):
    monkeypatch.setattr(mo.get_settings(), "motion_dir", str(tmp_path / "motion"))
    monkeypatch.setattr(mo, "_pool", Inline())
    monkeypatch.setattr(render, "available", lambda: "")
    calls = []

    def frames(kind, data, aspect="9:16", html=None, times=None, out_dir=None):
        return {"duration": 12.0, "errors": [], "shots": []}

    def video(kind, data, out_path, aspect="9:16", html=None, music=None, progress=None, title=""):
        calls.append({"kind": kind, "data": data, "aspect": aspect, "html": html, "music": music})
        Path(out_path).write_bytes(b"\x00\x00\x00\x18ftypmp42fake")
        if progress:
            progress(1.0)
        return {"duration": 12.0, "frames": 360, "size": 20, "errors": []}
    monkeypatch.setattr(render, "frames", frames)
    monkeypatch.setattr(render, "video", video)
    monkeypatch.setattr(ai, "_llm_json", lambda prompt: dict(PLAN))
    return calls


def test_make_list_play_and_delete_over_the_api(fake_render):
    from app import main
    with TestClient(main.app) as c:
        c.post("/api/conversations")
        k = c.get("/api/motion/kinds").json()
        assert [x["id"] for x in k["kinds"]] == ["explainer", "recipe", "logo", "offer", "custom"] and k["ready"] is True
        p = c.post("/api/motion/plan", json={"kind": "explainer", "brief": "chai ki dukaan"}).json()
        v = c.post("/api/motion/videos", json={"kind": "explainer", "data": p["data"], "aspect": "9:16", "music": "festive"}).json()
        got = c.get(f"/api/motion/videos/{v['id']}").json()
        assert got["status"] == "done" and got["title"] == "Sharma Chai Point" and got["ai_label"]
        assert fake_render[0]["music"] is not None and fake_render[0]["data"]["brand"] == "Sharma Chai Point"
        f = c.get(got["url"])                       # signed link, no login header
        assert f.status_code == 200 and f.headers["content-type"] == "video/mp4"
        assert c.get(got["url"].replace("sig=", "sig=0")).status_code == 403
        assert c.get("/api/motion/files/mv_nothere.mp4?exp=1&sig=x").status_code == 403
        assert [x["id"] for x in c.get("/api/motion/videos").json()["videos"]] == [v["id"]]
        assert c.post("/api/motion/videos", json={"kind": "nope"}).status_code == 400
        assert c.post("/api/motion/videos", json={"kind": "offer", "data": {}}).status_code == 400
        assert c.delete(f"/api/motion/videos/{v['id']}").json()["deleted"] is True
        assert c.get(f"/api/motion/videos/{v['id']}").status_code == 404


def test_render_failure_is_reported(fake_render, monkeypatch):
    def boom(*a, **k):
        raise render.RenderError("ffmpeg: broken")
    monkeypatch.setattr(render, "video", boom)
    v = mo.create("default", "offer", {"headline": "SALE", "big": "20% OFF"})
    got = mo.get("default", v["id"])
    assert got["status"] == "failed" and "ffmpeg" in got["error"] and "url" not in got


def test_custom_code_is_cleaned_and_checked(fake_render, monkeypatch):
    with pytest.raises(ai.AiError):
        ai.clean_html("<html><script>fetch('https://x')</script>HOOLA seek</html>")
    with pytest.raises(ai.AiError):
        ai.clean_html("<html>no time control</html>")
    h = ai.clean_html('<html><head><script src="https://cdn.example/gsap.js"></script><link rel="stylesheet" href="https://x">'
                      '</head><body><img src="https://evil/x.png"><script>window.HOOLA={duration:5,seek(t){}}</script></body></html>')
    assert "cdn.example" not in h and "evil" not in h and "<link" not in h
    page = ('<!doctype html><html><head></head><body><script>window.HOOLA={duration:6,seek(t){'
            'document.getElementById("stage").style.background="hsl("+(t*40)+",70%,40%)"}};</script></body></html>')
    monkeypatch.setattr(ai, "_llm_html", lambda prompt: "Here you go:\n" + page + "\nEnjoy")
    monkeypatch.setattr(mo, "check_custom", lambda html, aspect: None)
    v = mo.create("default", "custom", brief="Rangon ki lehar mein Happy Diwali")
    got = mo.get("default", v["id"])
    assert got["status"] == "done" and got["data"] == {"brief": "Rangon ki lehar mein Happy Diwali"}
    assert fake_render[-1]["html"].startswith("<!doctype html>") and "Enjoy" not in fake_render[-1]["html"]


def test_youtube_is_the_owners_tap(fake_render, monkeypatch):
    from app.bazar import service as bazar
    from app.youtube import service as ys
    seen = {}

    def plan_upload(tenant, conv, file_id, title, description="", privacy="private", tags=None, synthetic=False):
        seen.update(title=title, privacy=privacy, synthetic=synthetic, desc=description)
        return "ytp_1"
    monkeypatch.setattr(ys, "plan_upload", plan_upload)
    monkeypatch.setattr(bazar, "run", lambda *a, **k: {"needs_approval": True, "approval_id": "ap_1", "say": "Approve?"})
    v = mo.create("default", "logo", {"brand": "Newtika AI"})
    out = mo.to_youtube("default", "", v["id"], "", "public")
    assert out["approval_id"] == "ap_1" and seen["synthetic"] is True and seen["title"].endswith("#Shorts")
    assert "AI" in seen["desc"]


def test_avatar_makes_a_video(fake_render):
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.db import Conversation, session
    with session() as s:
        conv = Conversation(tenant_id="default")
        s.add(conv)
        s.flush()
        cid = conv.id
    out = asyncio.run(dispatch("motion_video", {"action": "make", "kind": "explainer", "brief": "chai ki dukaan"}, Ctx("default", cid)))
    assert out["status"] in ("queued", "done") and out["title"] == "Sharma Chai Point"
    lst = asyncio.run(dispatch("motion_video", {"action": "list"}, Ctx("default", cid)))
    assert lst["videos"][0]["status"] == "done"
    with pytest.raises(ToolError):
        asyncio.run(dispatch("motion_video", {"action": "make", "kind": "movie"}, Ctx("default", cid)))
    from app.voiceid.permissions import allowed
    assert allowed("trusted", "motion_video") and not allowed("family", "motion_video")


# ----------------------------------------------------------------------------- the real thing (headless Chromium)
needs_browser = pytest.mark.skipif(bool(render.available()), reason="needs playwright chromium + ffmpeg")


@needs_browser
def test_real_custom_render_and_checks(env, tmp_path):
    good = ('<!doctype html><html><head><style>#stage{background:#123}</style></head><body><div id="stage"></div><script>'
            'const b=HM.el("div","",null,"Hoola");b.style.cssText="position:absolute;font:800 12vmin Poppins;color:#fff;top:40%";'
            'HM.badge();window.HOOLA={duration:3,seek(t){b.style.left=(5+t*20)+"vw";b.style.opacity=HM.p(t,0,.5)}};'
            '</script></body></html>')
    mo.check_custom(good, "9:16")
    jitter = good.replace("b.style.left=(5+t*20)", "b.style.left=(5+Math.random()*60+t*0)").replace("HM.badge();", "HM.badge();window.R=Math.random;")
    # Math.random is seeded by the renderer, but calling it inside seek still changes frame to frame: caught
    with pytest.raises(mo.MotionError, match="alag frame"):
        mo.check_custom(jitter, "9:16")
    blank = '<!doctype html><html><body><div id="stage"></div><script>window.HOOLA={duration:3,seek(t){}}</script></body></html>'
    with pytest.raises(mo.MotionError):
        mo.check_custom(blank, "9:16")
    out = tmp_path / "c.mp4"
    wav = music.write("calm", 4, tmp_path / "m.wav")
    res = render.video("custom", {}, out, "9:16", html=good, music=wav, title="test")
    assert res["frames"] == 90 and out.stat().st_size > 5000
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format_tags=comment",
                            "-of", "json", str(out)], capture_output=True, text=True)
    info = json.loads(probe.stdout)
    assert {s["codec_type"] for s in info["streams"]} == {"video", "audio"}
    assert any(s.get("width") == 720 and s.get("height") == 1280 for s in info["streams"])
    assert "AI-generated" in info["format"]["tags"]["comment"]


@needs_browser
def test_real_templates_open_cleanly(env, tmp_path):
    for kind, data in [("explainer", mo.clean("explainer", PLAN)), ("recipe", {"dish": "Chai", "ingredients": [{"name": "doodh"}],
                       "steps": ["ubaalo"]}), ("logo", {"brand": "Newtika"}), ("offer", {"headline": "SALE", "big": "20% OFF"})]:
        for aspect in ("9:16", "16:9"):
            r = render.frames(kind, data, aspect, times=[1.0, 5.0], out_dir=tmp_path)
            assert r["errors"] == [] and r["duration"] > 5, (kind, aspect, r)


def test_crash_reports_are_kept(env, tmp_path, monkeypatch):
    from app import main
    monkeypatch.chdir(tmp_path)
    with TestClient(main.app) as c:
        assert c.post("/api/app/crash", json={"kind": "native", "text": "libonnxruntime.so SIGSEGV", "during_call": True}).json()["ok"]
        got = c.get("/api/app/crashes").json()["crashes"]
        assert got[0]["kind"] == "native" and got[0]["during_call"] is True and "onnx" in got[0]["text"]
