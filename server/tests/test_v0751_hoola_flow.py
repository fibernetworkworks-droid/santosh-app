"""v0.750 HOOLA FLOW (built as 0.749; their SAB PUBLIC APIS took 0.753.0, both kept) (owner: "a wisperflow of hoola - check the code" -> "first show me the design here" -> the 8-screen
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


from datetime import datetime, timedelta, timezone

_NOW = datetime.now(timezone.utc)
OV = {"ready": True, "engine": {"ok": True, "default_model": "small", "live_model": "base",
                                "ladder": [{"name": "tiny", "params": "39M", "note": "fastest"}, {"name": "small", "params": "244M", "note": "balanced"}]},
      "recording": {"on": True, "how": ""}, "speakers": {"on": True}, "voiceprint": {"on": False, "why": "Voiceprint is off."},
      "usage": {"minutes": 42.5, "cap": 0, "remaining": None, "month": "2026-11"}, "retention": {"days": 0}, "words": 2, "live_active": 0,
      "styles": [], "exports": ["srt"], "doors": {"api": "/api/kaan", "mcp": "python -m app.kaan.mcp_server"},
      "items": [{"id": "kn_2", "title": "Dictation 10 Nov", "kind": "dictated", "language": "en", "n_turns": 0, "duration_s": 30,
                 "text": "Ravi the coupon bug is fixed and the release goes out tonight", "created_at": _NOW.isoformat(), "pinned": False, "status": "ready", "task": "transcribe"},
                {"id": "kn_1", "title": "Supplier call - <b>Sharma</b>", "kind": "file", "language": "hi", "n_turns": 3, "duration_s": 2530,
                 "text": "Sharma ji will send the quote", "created_at": (_NOW - timedelta(days=1)).isoformat(), "pinned": False, "status": "ready", "task": "transcribe"}]}
DETAIL = {"id": "kn_1", "title": "Supplier call - <b>Sharma</b>", "file_name": "x", "kind": "file", "language": "hi", "duration_s": 2530, "model": "small",
          "task": "transcribe", "pinned": False, "text": "Sharma ji will send the quote by Friday.", "segments": [{"start": 4, "end": 9, "text": "Sharma ji"}],
          "speakers": {"turns": [{"turn": 1, "speaker": "Meghana", "start": 4, "end": 18, "text": "Next order by the 18th."},
                                 {"turn": 2, "speaker": "", "start": 19, "end": 40, "text": "Sharma ji will send the quote by Friday."}]}}
MINUTES = {"action_candidates": [{"turn": 2, "speaker": "", "cue": "will", "text": "Sharma ji will send the quote by Friday."}], "keywords": ["quote", "friday"]}
VOCAB = {"items": [{"term": "sharma ten", "fix_to": "SHARMA10", "note": ""}, {"term": "Akola", "fix_to": "", "note": ""},
                   {"term": "my upi", "fix_to": "meghana@okaxis", "note": "snippet"}], "n": 3}


def test_the_page_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    """v0.777 the Wispr-Flow-like page on /console/flow: sidebar, welcome + stats, history by day, the Flow bar,
    Dictionary / Snippets / Style, a transcript, settings - and the console's Hoola Flow row opens it."""
    import os
    base, browser, key = arena_server
    monkeypatch.setenv("FLOW_PAGE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(f"{e} {getattr(e, 'stack', '')} @ {pg.url}"))
    shots = os.environ.get("HOOLA_SHOTS")
    snap = (lambda n: (pg.wait_for_timeout(400), pg.screenshot(path=f"{shots}/flow_{n}.png"))) if shots else (lambda n: None)
    pg.route("**/api/console/config", lambda r: r.fulfill(json={"app": "Hoola", "v2": True, "stream": True, "sessions": True,
                                                                   "panel": True, "projects": True, "human": True, "flow": True, "flow_mic": True}))
    pg.route("**/api/me", lambda r: r.fulfill(json={"signed_in": True, "name": "Meghana Ingle", "email": "m@example.com"}))
    pg.route("**/api/flow/overview*", lambda r: r.fulfill(json=OV))
    pg.route("**/api/flow/t/kn_1", lambda r: r.fulfill(json=DETAIL))
    pg.route("**/api/kaan/kn_1/minutes", lambda r: r.fulfill(json=MINUTES))
    pg.route("**/api/kaan/kn_1/style", lambda r: r.fulfill(json={"style": "clean", "rendered": {"text": "Sharma ji will send the quote by Friday."}, "note": "clean: tidied"}))
    added = []
    pg.route("**/api/kaan/vocab", lambda r: (added.append(r.request.post_data_json), r.fulfill(json={"ok": True}))[1] if r.request.method == "POST" else r.fulfill(json=VOCAB))
    pg.goto(base + "/console/")                                     # the console row opens the page
    pg.wait_for_selector(".sn[data-v='flow']")
    pg.locator(".sn[data-v='flow']").click()
    pg.wait_for_url("**/console/flow**")
    pg.wait_for_selector(".wf-row")
    home = pg.locator(".wf-main").text_content()
    assert "Welcome back, Meghana" in home and "Hoola writes it." in home and "Hold to dictate" in home and "<b>Sharma</b>" in home
    assert "Today" in home and "Yesterday" in home and "24 WPM" in home.replace("\n", "") and "2 day streak" in home
    assert "Click or hold Space to dictate" in pg.locator("#wfbar").text_content()
    assert pg.locator(".wf-nv.on").text_content() == "Home"
    snap("home")
    pg.fill("#wfq", "coupon")
    assert pg.locator(".wf-row").count() == 1
    pg.fill("#wfq", "")
    pg.locator(".wf-row[data-tid='kn_1']").click()
    pg.wait_for_selector(".wf-turn")
    assert pg.url.endswith("#/t/kn_1")
    t = pg.locator(".wf-main").text_content()
    assert "Meghana" in t and "Speaker 2" in t and "Action items found" in t and "Make reminders from these" in t and "SRT subtitles" in t
    pg.locator("[data-tv='clean']").click()
    pg.wait_for_selector(".wf-rend")
    assert "by Friday" in pg.locator(".wf-rend").text_content()
    snap("transcript")
    pg.locator(".wf-nv[data-go='words']").click()
    pg.wait_for_selector(".wf-wr")
    w = pg.locator(".wf-main").text_content()
    assert "SHARMA10" in w and "listening hint" in w and "meghana@okaxis" not in w   # a snippet is not a dictionary word
    snap("dictionary")
    pg.locator("#wfadd").click()
    pg.fill("#wfw1", "Newtika")
    pg.locator(".wf-dlg button[type=submit]").click()
    pg.wait_for_selector(".wf-modal", state="detached")
    assert added[-1] == {"term": "Newtika", "fix_to": ""}
    pg.locator(".wf-nv[data-go='snippets']").click()
    pg.wait_for_selector(".wf-sn")
    assert "meghana@okaxis" in pg.locator(".wf-main").text_content() and pg.locator(".wf-sn").count() == 1
    pg.locator("#wfadd").click()
    pg.fill("#wfs1", "my address")
    pg.fill("#wfs2", "12 MG Road, Akola")
    pg.locator(".wf-dlg button[type=submit]").click()
    pg.wait_for_selector(".wf-modal", state="detached")
    assert added[-1] == {"term": "my address", "fix_to": "12 MG Road, Akola", "note": "snippet"}
    snap("snippets")
    pg.locator(".wf-nv[data-go='style']").click()
    pg.wait_for_selector(".wf-sty")
    pg.locator(".wf-sty[data-sty='verbatim']").click()
    assert pg.evaluate("localStorage.getItem('hoola.flow.style')") == "verbatim"
    assert pg.locator(".wf-sty[aria-checked='true']").get_attribute("data-sty") == "verbatim"
    snap("style")
    pg.locator(".wf-side [data-go='settings']").click()
    pg.wait_for_selector(".wf-sets")
    s = pg.locator(".wf-main").text_content()
    snap("settings")
    assert "Ready on this server" in s and "Default for files" in s and "Voiceprint is off." in s and "/api/kaan" in s and "As said" in s
    pg.locator(".wf-nv[data-go='live']").click()
    pg.wait_for_selector("#wfgo")
    assert pg.locator("#wfgo").is_enabled() and pg.locator("#wfbar").text_content().strip() != ""
    snap("live")
    pg.locator(".wf-nv[data-go='files']").click()
    pg.wait_for_selector("#wfdrop")
    assert pg.locator("#wfmake").is_disabled()                     # nothing chosen yet
    snap("files")
    # the Flow bar end to end: hold Space -> waveform + words so far -> release -> written in her Style, copied, on top
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=base)
    calls = []
    pg.route("**/api/kaan/live/start", lambda r: (calls.append("start"), r.fulfill(json={"id": "kl_1"}))[1])
    pg.route("**/api/kaan/live/kl_1/chunk", lambda r: r.fulfill(json={"new": [{"start": 0, "text": "hello world"}]}))
    pg.route("**/api/kaan/live/kl_1/stop", lambda r: (calls.append("stop"), r.fulfill(json={"transcript_id": "kn_9"}))[1])
    pg.route("**/api/flow/t/kn_9/rename", lambda r: r.fulfill(json={"ok": True}))
    pg.route("**/api/kaan/kn_9/style", lambda r: (calls.append(r.request.post_data_json["style"]), r.fulfill(json={"rendered": {"text": "hello world"}}))[1])
    pg.add_init_script("""navigator.mediaDevices.getUserMedia = async () => { const c = new AudioContext(), o = c.createOscillator(),
        d = c.createMediaStreamDestination(); o.connect(d); o.start(); return d.stream; };""")
    pg.goto(base + "/console/flow")
    pg.wait_for_selector("#wfpill")
    pg.keyboard.down("Space")
    pg.wait_for_selector("#wfwave")
    pg.wait_for_selector("#wflive >> text=hello world", timeout=10000)
    assert pg.locator("#wfok").is_visible() and pg.locator("#wfx").is_visible()
    snap("recording")
    pg.wait_for_timeout(600)
    pg.keyboard.up("Space")                                        # held > 0.45 s = push-to-talk: release finishes
    pg.wait_for_selector("#wfpill", timeout=10000)
    assert calls[:2] == ["start", "stop"] and calls[2] == "verbatim"   # her Style (As said, picked above) was used
    assert pg.evaluate("navigator.clipboard.readText()") == "hello world"
    assert "Copied" in pg.locator("#toast").text_content()
    pg.keyboard.press("Space")                                     # a tap keeps listening ...
    pg.wait_for_selector("#wfwave")
    pg.keyboard.press("Escape")                                    # ... and Esc cancels, nothing kept
    pg.wait_for_selector("#toast >> text=Cancelled")
    pg.goto(base + "/console/flow#/t/kn_1")                        # 'Put in the Hoola chat' -> the console chat box, not sent
    pg.wait_for_selector("#wfrem")
    pg.locator("#wfrem").click()
    pg.wait_for_url("**/console/")
    pg.wait_for_selector("#msg")
    for _ in range(50):                                            # page CSP forbids wait_for_function's eval
        if "Make reminders" in pg.input_value("#msg"):
            break
        pg.wait_for_timeout(100)
    assert "Make reminders" in pg.input_value("#msg")
    pg.set_viewport_size({"width": 390, "height": 844})             # phone width: no sideways scroll
    pg.goto(base + "/console/flow")
    pg.wait_for_selector(".wf-row")
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    snap("phone")
    pg.set_viewport_size({"width": 1360, "height": 900})
    pg.emulate_media(color_scheme="dark")
    pg.goto(base + "/console/flow#/dictionary")
    pg.wait_for_selector(".wf-wr")
    snap("dark_dictionary")
    pg.locator(".wf-nv[data-go='home']").click()
    pg.wait_for_selector(".wf-row")
    snap("dark_home")
    assert not errs, errs
    ctx.close()


def test_flow_page_route_is_switched(flow_env):  # noqa: F811
    with client() as c:
        r = c.get("/console/flow")
        assert r.status_code == 200 and "flowapp.js" in r.text and "flow.css" in r.text
        assert "microphone=(self)" in r.headers["permissions-policy"] and "script-src 'self'" in r.headers["content-security-policy"]
