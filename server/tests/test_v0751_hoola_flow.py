"""v0.750 HOOLA FLOW (built as 0.749; their SAB PUBLIC APIS took 0.752.0, both kept) (owner: "a wisperflow of hoola - check the code" -> "first show me the design here" -> the 8-screen
canvas -> "GO"): the Kaan pack (W0-W6) as a console page. The page rides the /api/kaan/* routes as they are; /api/flow adds
only what a page needs (one overview, a transcript with its turns, rename / keep / delete). The mic sends 16 kHz mono WAV
pieces - each a whole file the server's real ffmpeg decodes on its own - and the walk runs in a real browser."""
import io
import math
import struct
import subprocess
import wave

import pytest
from fastapi.testclient import TestClient

from tests.test_v0663_kaan_w5 import H, w5_env, seed_row  # noqa: F401
from tests.test_v0618_kaan_w2 import CHUNK_S, SCRIPT, fake_decoder, pcm, window_engine
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401


@pytest.fixture()
def flow_env(w5_env):  # noqa: F811
    w5_env.setenv("FLOW_PAGE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    yield w5_env
    get_settings.cache_clear()


def client():
    from app.main import app
    return TestClient(app)


def test_switch_off_hides_every_flow_route(w5_env):  # noqa: F811
    with client() as c:
        assert c.get("/api/console/config").json()["flow"] is False             # pinned off for old suites
        assert c.get("/api/flow/overview", headers=H).status_code == 404


def test_overview_rename_keep_delete(flow_env):
    row = seed_row(flow_env, name="sharma-call.m4a", text="Sharma ji will send the quote by Friday. Theek hai.")
    tid = row["id"]
    with client() as c:
        cfg = c.get("/api/console/config").json()
        assert cfg["flow"] is True and cfg["flow_mic"] is True
        ov = c.get("/api/flow/overview", headers=H).json()
        assert ov["ready"] is True and ov["engine"]["ok"] and ov["recording"]["on"]
        it = next(x for x in ov["items"] if x["id"] == tid)
        assert it["kind"] == "file" and it["title"] == "sharma-call.m4a"
        assert ov["usage"]["cap"] == 0 and ov["retention"]["days"] == 0 and [s[0] for s in ov["styles"]][:2] == ["verbatim", "clean"]
        d = c.get(f"/api/flow/t/{tid}", headers=H).json()
        assert d["segments"] and d["kind"] == "file"
        assert c.post(f"/api/flow/t/{tid}/rename", headers=H, json={"name": "  Supplier   call "}).json()["file_name"] == "Supplier call"
        assert c.post(f"/api/flow/t/{tid}/rename", headers=H, json={"name": " "}).status_code == 400
        assert c.post(f"/api/flow/t/{tid}/pin", headers=H, json={"pinned": True}).json()["pinned"] is True
        assert c.get(f"/api/kaan/{tid}", headers=H).json()["pinned"] is True       # the W6 sweep reads the same flag
        assert c.delete(f"/api/flow/t/{tid}", headers=H).json()["deleted"] is True
        assert c.get(f"/api/flow/t/{tid}", headers=H).status_code == 404
        assert c.post(f"/api/flow/t/kn_nope/pin", headers=H, json={}).status_code == 404


def test_dictation_round_trip_names_it_dictated(flow_env, monkeypatch):
    from app.kaan import service as KS
    LV = KS.LV
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(LV.EN, "transcribe", window_engine(SCRIPT))
    with client() as c:
        sid = c.post("/api/kaan/live/start", headers=H, json={"vocab": True}).json()["id"]
        ch = c.post(f"/api/kaan/live/{sid}/chunk", headers={**H, "Content-Type": "audio/wav"}, content=pcm(CHUNK_S)).json()
        assert ch["new"] and ch["new"][0]["text"]                                  # the page shows these as they come
        tid = c.post(f"/api/kaan/live/{sid}/stop", headers=H, json={}).json()["transcript_id"]
        it = next(x for x in c.get("/api/flow/overview", headers=H).json()["items"] if x["id"] == tid)
        assert it["kind"] == "live" and it["title"].startswith("Live captions")
        c.post(f"/api/flow/t/{tid}/rename", headers=H, json={"name": "Dictation 10 Nov, 10:00"})
        it = next(x for x in c.get("/api/flow/overview", headers=H).json()["items"] if x["id"] == tid)
        assert it["kind"] == "dictated"
        clean = c.post(f"/api/kaan/{tid}/style", headers=H, json={"style": "clean"}).json()
        assert clean["rendered"]["text"]


def _browser_wav(seconds=2.0, rate=16000):
    """The same bytes flow.js writes: RIFF / fmt 16-bit PCM mono / data."""
    n = int(seconds * rate)
    data = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(n))
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    return hdr + b"data" + struct.pack("<I", len(data)) + data


def test_every_wav_piece_decodes_on_its_own_with_real_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except Exception:
        pytest.skip("ffmpeg not on this machine")
    from app.kaan import live as LV
    blob = _browser_wav(2.0)
    with wave.open(io.BytesIO(blob)) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2
    for _ in range(2):                                                              # piece 2 decodes exactly like piece 1
        out = LV._decode_chunk(blob)
        assert abs(len(out) - 2 * 16000 * 2) < 64


def test_page_files_are_wired():
    from pathlib import Path
    st = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js, v2, html = (st / "flow.js").read_text(), (st / "v2.js").read_text(), (st / "v2.html").read_text()
    assert "window.HoolaFlow =" in js and "window.HoolaFlowMic =" in js and "createScriptProcessor" in js and "'RIFF'" in js
    assert "/api/kaan/live/start" in js and "/api/kaan/transcribe" in js and "/api/flow/overview" in js
    assert "CONFIG.flow && window.HoolaFlow" in v2 and "['flow', 'Hoola Flow']" in v2 and "await flowMic()" in v2
    assert 'id="v-flow"' in html and "/static/console/flow.js?v=" in html


OV = {"ready": True, "engine": {"ok": True, "default_model": "small", "live_model": "base",
                                "ladder": [{"name": "tiny", "params": "39M", "note": "fastest"}, {"name": "small", "params": "244M", "note": "balanced"}]},
      "recording": {"on": True, "how": ""}, "speakers": {"on": True}, "voiceprint": {"on": False, "why": "Voiceprint is off."},
      "usage": {"minutes": 42.5, "cap": 0, "remaining": None, "month": "2026-11"}, "retention": {"days": 0}, "words": 2, "live_active": 0,
      "styles": [], "exports": ["srt"], "doors": {"api": "/api/kaan", "mcp": "python -m app.kaan.mcp_server"},
      "items": [{"id": "kn_1", "title": "Supplier call - <b>Sharma</b>", "kind": "file", "language": "hi", "n_turns": 3, "duration_s": 2530,
                 "text": "Sharma ji will send the quote", "created_at": "2026-11-10T09:00:00+00:00", "pinned": False, "status": "ready", "task": "transcribe"},
                {"id": "kn_2", "title": "Dictation 10 Nov", "kind": "dictated", "language": "en", "n_turns": 0, "duration_s": 41,
                 "text": "Ravi the coupon bug is fixed", "created_at": "2026-11-10T09:30:00+00:00", "pinned": False, "status": "ready", "task": "transcribe"}]}
DETAIL = {"id": "kn_1", "title": "Supplier call - <b>Sharma</b>", "file_name": "x", "kind": "file", "language": "hi", "duration_s": 2530, "model": "small",
          "task": "transcribe", "pinned": False, "text": "Sharma ji will send the quote by Friday.", "segments": [{"start": 4, "end": 9, "text": "Sharma ji"}],
          "speakers": {"turns": [{"turn": 1, "speaker": "Meghana", "start": 4, "end": 18, "text": "Next order by the 18th."},
                                 {"turn": 2, "speaker": "", "start": 19, "end": 40, "text": "Sharma ji will send the quote by Friday."}]}}
MINUTES = {"action_candidates": [{"turn": 2, "speaker": "", "cue": "will", "text": "Sharma ji will send the quote by Friday."}], "keywords": ["quote", "friday"]}


def test_the_page_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/api/console/config", lambda r: r.fulfill(json={"app": "Hoola", "v2": True, "stream": True, "sessions": True,
                                                                   "panel": True, "projects": True, "human": True, "flow": True, "flow_mic": True}))
    pg.route("**/api/flow/overview*", lambda r: r.fulfill(json=OV))
    pg.route("**/api/flow/t/kn_1", lambda r: r.fulfill(json=DETAIL))
    pg.route("**/api/kaan/kn_1/minutes", lambda r: r.fulfill(json=MINUTES))
    pg.route("**/api/kaan/kn_1/style", lambda r: r.fulfill(json={"style": "clean", "rendered": {"text": "Sharma ji will send the quote by Friday."}, "note": "clean: tidied"}))
    pg.route("**/api/kaan/vocab", lambda r: r.fulfill(json={"items": [{"term": "sharma ten", "fix_to": "SHARMA10"}, {"term": "Akola", "fix_to": ""}], "n": 2}))
    pg.goto(base + "/console/")
    pg.wait_for_selector("#composer")
    pg.wait_for_selector(".sn[data-v='flow']")
    pg.locator(".sn[data-v='flow']").click()
    pg.wait_for_selector(".hfl-starts")
    home = pg.locator(".hfl").text_content()
    assert "Speak. Hoola writes it." in home and "42.5 min" in home and "No monthly limit set" in home and "<b>Sharma</b>" in home
    assert pg.locator(".hfl-row").count() == 2
    pg.fill("#hflq", "coupon")
    assert pg.locator(".hfl-row").count() == 1
    pg.fill("#hflq", "")
    pg.locator(".hfl-row[data-tid='kn_1']").click()
    pg.wait_for_selector(".hfl-turn")
    t = pg.locator(".hfl").text_content()
    assert "Meghana" in t and "Speaker 2" in t and "Action items found" in t and "Make reminders from these" in t and "SRT subtitles" in t
    pg.locator("[data-tv='clean']").click()
    pg.wait_for_selector(".hfl-rend")
    assert "by Friday" in pg.locator(".hfl-rend").text_content()
    pg.locator("#hflrem").click()                                   # the ask lands in the chat box, not sent
    pg.wait_for_function("document.querySelector('#msg') && document.querySelector('#msg').value.includes('Make reminders')")
    pg.locator(".sn[data-v='flow']").click()                       # back to the page: it keeps the transcript she had open
    pg.wait_for_selector(".hfl-turn")
    pg.locator(".hfl-nv[data-go='words']").click()
    pg.wait_for_selector(".hfl-wr")
    w = pg.locator(".hfl").text_content()
    assert "SHARMA10" in w and "hint only" in w
    pg.locator(".hfl-nv[data-go='settings']").click()
    pg.wait_for_selector(".hfl-grid2.big")
    s = pg.locator(".hfl").text_content()
    assert "Ready on this server" in s and "Default for files" in s and "Voiceprint is off." in s and "/api/kaan" in s
    pg.locator(".hfl-nv[data-go='dictate']").click()
    pg.wait_for_selector("#hflgo")
    assert pg.locator("#hflgo").is_enabled()
    pg.locator(".hfl-nv[data-go='files']").click()
    pg.wait_for_selector("#hfldrop")
    assert pg.locator("#hflmake").is_disabled()                     # nothing chosen yet
    assert not errs, errs
    ctx.close()
