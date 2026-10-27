"""v0.65 Hoola Video Editor: watch -> plan (validated, problems fed back) -> captions on the edited timeline -> render ->
self-check with a fix round -> delivered version -> changes in plain words (v2 from cache) + tool / API / employee."""
import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def _clip(tmp: Path, name="talk.mp4", dur=8):
    p = tmp / name
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc=s=320x240:r=25:d={dur}", "-f", "lavfi", "-i",
                    f"aevalsrc='0.5*sin(2*PI*440*t)*between(mod(t,2),0,1.2)':s=48000:d={dur}",
                    "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(p)], check=True)
    return p.read_bytes()


def _upload(tenant, name, data):
    from app import chatfiles
    return chatfiles.store(tenant, name, data)["file_id"]


class Brain:
    def __init__(self):
        self.prompts, self.looks = [], 0

    def watch(self, data, mime, duration, script=""):
        return {"summary": "Ek dukaan ka tour", "language": "hi", "mood": "energetic",
                "transcript": [{"start": 0.1, "end": 1.1, "text": "Namaste doston aaj"}, {"start": 2.0, "end": 3.1, "text": "naya stock aaya hai"},
                               {"start": 4.1, "end": 5.1, "text": "zaroor aaiye"}],
                "highlights": [{"start": 2.0, "end": 3.2, "why": "naya stock", "score": 9}], "thumbnail_time": 2.5}

    def think(self, system, prompt):
        self.prompts.append(prompt)
        if len(self.prompts) == 1:          # first answer uses a file that isn't hers: must come back with the problem
            return {"timeline": {"clips": [{"src": "/etc/passwd"}]}}
        if "OWNER WANTS THIS CHANGE" in prompt:
            return {"timeline": {"output": {"fit": "blur"}, "clips": [
                {"src": "src1.mp4", "in": 2.0, "out": 3.2, "texts": [{"text": "NAYA STOCK", "position": "top", "size": 90}]},
                {"src": "src1.mp4", "in": 0.0, "out": 1.2}]},
                "title": "Naya stock", "notes": "Title bada kar diya", "hashtags": ["#shop"]}
        return {"timeline": {"output": {"fit": "blur", "aspect": "16:9"}, "clips": [
                {"src": "src1.mp4", "in": 2.0, "out": 3.2, "texts": [{"text": "Naya stock", "position": "top"}]},
                {"src": "src1.mp4", "in": 0.0, "out": 1.2}]},
                "title": "Naya stock aaya", "post_caption": "Aaj hi aaiye!", "hashtags": ["#shop", "#newstock"],
                "thumbnail_time": 0.5, "notes": "Hook pehle, phir namaste."}

    def look(self, png, system, prompt):
        self.looks += 1
        assert png[:4] == b"\x89PNG"
        if self.looks == 1:
            return {"ok": False, "score": 4, "problems": ["text thoda chhota"], "fix": "make the top text bigger"}
        return {"ok": True, "score": 8, "problems": []}


@pytest.fixture
def brain(monkeypatch):
    from app.videoedit import brain as b
    fake = Brain()
    monkeypatch.setattr(b, "watch", fake.watch)
    monkeypatch.setattr(b, "think", fake.think)
    monkeypatch.setattr(b, "look", fake.look)
    return fake


def test_full_edit_then_change(env, brain, tmp_path):
    from app.videoedit import service as vs
    fid = _upload("default", "talk.mp4", _clip(tmp_path))
    v = vs.start("default", [fid], "Dukaan ki reel, naya stock dikhao", "reel", 20, True)
    assert v["status"] == "queued" and v["platform_label"] == "Instagram Reel"
    done = vs.run_job(v["id"])
    assert done["status"] == "done", done
    ver = done["latest"]
    assert ver["n"] == 1 and ver["width"] == 1080 and ver["height"] == 1920     # the platform's shape, not the planner's 16:9
    assert abs(ver["duration"] - 2.4) < 0.05 and ver["thumb"] and ver["file_id"] and ver["url"].startswith("/api/video/files/")
    assert ver["check"]["ok"] and ver["check"]["score"] == 8
    # the first plan named a file that isn't hers -> sent back; the self-check asked for a fix -> re-planned once
    assert any("not one of the files" in p for p in brain.prompts[1:2]) and brain.looks == 2
    assert any("SENIOR EDITOR" in p and "make the top text bigger" in p for p in brain.prompts)
    assert done["post_caption"] == "Aaj hi aaiye!" and "#shop" in done["hashtags"]
    ws = vs._ws("default", v["id"])
    srt = (ws / "captions.srt").read_text()
    assert "naya stock aaya hai" in srt and "Namaste doston aaj" in srt and "zaroor" not in srt   # 4.1-5.1 s was cut out
    first = srt.split("\n")[1]
    assert first.startswith("00:00:00,0")            # "naya stock" (source 2.0 s) is now at the start
    # the link works, a wrong signature doesn't
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = c.get(ver["url"])
    assert r.status_code == 200 and r.content[4:8] == b"ftyp"
    assert c.get(ver["url"].replace("sig=", "sig=x")).status_code == 404
    # a note in the chat for the agent + the owner
    from app.db import Message, session
    with session() as s:
        notes = [m.display for m in s.query(Message).filter(Message.role == "assistant").all() if m.display and "Video taiyaar" in m.display]
    assert notes and "Kuch badalna ho" in notes[-1]
    # a change in plain words -> v2, clips that didn't change come from the cache
    vs.revise("default", v["id"], "title bada karo")
    d2 = vs.run_job(v["id"])
    assert d2["status"] == "done" and len(d2["versions"]) == 2 and d2["latest"]["change"] == "title bada karo"
    assert d2["latest"]["from_cache"] >= 1 and d2["pending"] == ""
    assert "CURRENT TIMELINE" in brain.prompts[-1]


def test_plan_too_long_is_refused_and_errors_are_plain(env, brain, tmp_path, monkeypatch):
    from app.videoedit import brain as b
    from app.videoedit import service as vs
    fid = _upload("default", "talk.mp4", _clip(tmp_path, dur=8))
    monkeypatch.setattr(b, "think", lambda system, prompt: {"timeline": {"clips": [{"src": "src1.mp4", "in": 0, "out": 8}]}})
    v = vs.start("default", [fid], "x", "status", 5, False)
    monkeypatch.setattr(vs, "PLATFORMS", {**vs.PLATFORMS, "status": {**vs.PLATFORMS["status"], "max": 5}})
    with pytest.raises(vs.VideoError) as e:
        vs.run_job(v["id"])
    assert "at most 5 s" in str(e.value)
    vs._safe_run(v["id"])
    got = vs.get("default", v["id"])
    assert got["status"] == "failed" and "3 baar" in got["error"]


def test_start_checks_files_and_options(env, tmp_path):
    from app.videoedit import service as vs
    with pytest.raises(vs.VideoError):
        vs.start("default", [], "x")
    doc = _upload("default", "notes.txt", b"hello world")
    with pytest.raises(vs.VideoError):
        vs.start("default", [doc], "x")
    from io import BytesIO
    from PIL import Image
    b = BytesIO()
    Image.new("RGB", (400, 400), "red").save(b, "PNG")
    one = _upload("default", "p.png", b.getvalue())
    with pytest.raises(vs.VideoError):
        vs.start("default", [one], "x")                      # one photo is not a video
    vid = _upload("default", "talk.mp4", _clip(tmp_path, dur=3))
    v = vs.start("default", [vid, one], "x", "nonsense", 9999, True, logo_file_id=one)
    assert v["platform"] == "reel" and v["length_s"] == 90 and v["sources"][1]["kind"] == "image"
    with pytest.raises(vs.VideoError):
        vs.revise("default", v["id"], "title bada")         # still queued
    assert vs.cancel("default", v["id"])["status"] == "cancelled"
    assert vs.run_job(v["id"])["status"] == "cancelled"
    with pytest.raises(vs.VideoError):
        vs.get("someone-else", v["id"])


def test_captions_follow_cuts_and_speed(env, tmp_path):
    from app.vedit import load_timeline
    from app.videoedit import captions
    (tmp_path / "a.mp4").write_bytes(_clip(tmp_path, "a.mp4", 8))
    words = captions.words_from_segments([{"start": 1.0, "end": 2.0, "text": "ek do"}, {"start": 5.0, "end": 6.0, "text": "teen char"}], 8)
    assert [w["word"] for w in words] == ["ek", "do", "teen", "char"]
    tl = load_timeline({"clips": [{"src": "a.mp4", "in": 4.0, "out": 6.0, "speed": 2.0},
                                  {"src": "a.mp4", "in": 0.5, "out": 2.5}]}, str(tmp_path))
    placed = captions.place({"a.mp4": words}, tl, ["a.mp4", "a.mp4"])
    assert [w["word"] for w in placed] == ["teen", "char", "ek", "do"]
    assert abs(placed[0]["start"] - 0.5) < 0.05 and placed[1]["end"] <= 1.0 + 1e-6       # 2x speed halves the times
    assert abs(placed[2]["start"] - 1.5) < 0.05                                           # clip 2 starts at 1.0 s
    srt = captions.srt(captions.cues(placed))
    assert srt.count("-->") >= 2 and "teen char" in srt


def test_tool_api_and_employee(env, tmp_path):
    from app.agent.tools import HANDLERS, TOOLS, Ctx
    from app.employee.roles import ROLES, duty_of, kind_of
    from app.voice import VOICE_TOOL_NAMES
    fid = _upload("default", "talk.mp4", _clip(tmp_path, dur=3))
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    out = asyncio.run(HANDLERS["video_edit"](ctx, action="start", file_ids=[fid], brief="status bana do", platform="status"))
    assert out["status"] == "queued" and "Do not poll" in out["note_for_you"]
    st = asyncio.run(HANDLERS["video_edit"](ctx, action="status"))
    assert st["id"] == out["job_id"]
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    j = c.get("/api/video/jobs").json()
    assert j["jobs"][0]["id"] == out["job_id"] and any(p["id"] == "youtube" for p in j["platforms"])
    assert c.post("/api/video/jobs", json={"file_ids": []}).status_code == 400
    assert c.post(f"/api/video/jobs/{out['job_id']}/cancel").json()["status"] == "cancelled"
    assert any(t["name"] == "video_edit" for t in TOOLS) and "video_edit" in VOICE_TOOL_NAMES
    assert duty_of("video_edit") == "video" and kind_of("video_edit") == "action"
    assert "video" in ROLES["video_editor"]["duties"] and "video" in ROLES["marketing"]["duties"]
