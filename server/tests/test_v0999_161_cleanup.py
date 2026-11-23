"""v0.999.161 CLEAN-UP, PREMIUM - on the server: Hoola listens first (loudness, loudest peak, background, loud words
that hit the top, long pauses, measured here) and says what it would pick; the clean-up runs step by step (how much noise,
where it will be heard, how long a pause), in the background with its steps and Stop, measures before and after, keeps
her recording 30 days beside it (Before, Clean again); and the console page walked in a real Chromium."""
import io
import os
import time
import wave

import numpy as np
import pytest

from app.vocal import service as V
from tests.test_v0999_96_vocal_redesign_server import Resp, client, eleven, needs_ff, tone, vg  # noqa: F401

HERE = os.path.dirname(__file__)
JS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal.js"), encoding="utf-8").read()
CSS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal2.css"), encoding="utf-8").read()


def noisy(seconds=12.0, rate=16000, gain=1.2, noise=0.02, seed=3) -> bytes:
    """Three loud 'words' with two long pauses between them, under steady hiss; the loud parts hit the top."""
    t = np.arange(int(rate * seconds)) / rate
    x = np.zeros_like(t)
    for a, b in ((0.5, 3.0), (5.5, 8.0), (9.0, 11.5)):
        m = (t >= a) & (t < b)
        x[m] = 0.9 * np.sin(2 * np.pi * 220 * t[m]) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t[m]))
    x = np.clip(x * gain + noise * np.random.default_rng(seed).standard_normal(len(t)), -1, 1)
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    return b.getvalue()


def _rec(tmp_path, **kw):
    f = tmp_path / "market interview.wav"
    f.write_bytes(noisy(**kw))
    return str(f)


@needs_ff
def test_hoola_listens_first_and_says_what_it_would_pick(vg, tmp_path):  # noqa: F811
    m = V.cleanup_listen("t1", _rec(tmp_path))
    assert abs(m["seconds"] - 12) < 0.1 and m["clips"] == 3 and m["pauses"] == 2 and m["longest"] >= 2.0
    assert -40 < m["background"] < -28 and m["peak"] > -1 and not m["partial"]
    assert m["found"] == {"noise": True, "quiet": False, "loud": True, "clips": True, "pauses": True}
    assert m["pick"] == {"noise": "strong", "denoise": True, "level": True, "silence": True}
    calm = V.cleanup_listen("t1", _rec(tmp_path, gain=0.08, noise=0.0005))
    assert calm["clips"] == 0 and calm["found"]["quiet"] and not calm["found"]["noise"] and calm["pick"]["denoise"] is False


@needs_ff
def test_a_clean_up_step_by_step_before_and_after_and_her_recording_kept(vg, tmp_path):  # noqa: F811
    out = V.cleanup("t1", _rec(tmp_path), name="market interview.wav", noise="strong", silence=True, gap=1.0, target="podcast")
    assert out["kind"] == "cleanup" and out["title"] == "market interview" and out["engine"] == "server" and out["credits"] == 0
    assert [s["t"] for s in out["steps"]] == ["Listening to your recording", "Removing background noise", "Making the voice clearer",
                                             "Shortening long pauses", "Evening out the loudness", "Checking the result"]
    assert all(s["secs"] is not None for s in out["steps"])
    b, a = out["before"], out["after"]
    assert a["background"] < b["background"] - 6                     # the hiss is lower
    assert abs(a["lufs"] + 16) < 1.5 and a["peak"] < -1.0             # podcast loudness, no more crackle
    assert a["seconds"] < b["seconds"] - 1                            # the long pauses were shortened
    assert out["done"] == ["Noise · strong", "Clearer voice", "Pauses over 1 s", "Podcast loudness"]
    assert out["src"].startswith("cl_") and out["src_secs"] == b["seconds"]
    f, h = V.source_file("t1", out["id"])
    assert f.read_bytes() == open(tmp_path / "market interview.wav", "rb").read()
    with pytest.raises(V.VocalError, match="no longer kept"):
        V.change_source("t1", out["id"])                              # a change's recording only
    again = V.cleanup("t1", "", source_of=out["id"], noise="light", silence=False, level=False)
    assert again["src"] == out["src"] and again["title"] == "market interview" and len(again["steps"]) == 4
    V.history_remove("t1", out["id"])
    assert f.is_file()                                                 # the second clean-up still needs it
    V.history_remove("t1", again["id"])
    assert not f.is_file()
    with pytest.raises(V.VocalError, match="light, medium or strong"):
        V.cleanup("t1", _rec(tmp_path), noise="max")
    with pytest.raises(V.VocalError, match="podcast, reels"):
        V.cleanup("t1", _rec(tmp_path), target="tv")
    with pytest.raises(V.VocalError, match="0.5, 1 or 2"):
        V.cleanup("t1", _rec(tmp_path), gap=3)
    with pytest.raises(V.VocalError, match="at least one thing"):
        V.cleanup("t1", _rec(tmp_path), denoise=False, voice=False, level=False)


@needs_ff
def test_lifting_the_voice_out_runs_on_elevenlabs_first(vg, eleven, tmp_path):  # noqa: F811
    sent, replies = eleven
    replies["audio-isolation"] = lambda m, u, kw: Resp(content=noisy(seconds=6.0, noise=0.0))
    out = V.cleanup("t1", _rec(tmp_path), people=True, voice=False)
    assert any(u.endswith("/v1/audio-isolation") for _, u, _ in sent)
    assert out["engine"] == "eleven" and out["credits"] > 0 and out["done"][0] == "Street sounds lifted out"
    assert out["steps"][1]["t"] == "Lifting the voice out"


@needs_ff
def test_the_background_job_its_steps_and_stop(vg, client, tmp_path, monkeypatch):  # noqa: F811
    from app.vocal import api
    rec = _rec(tmp_path)
    monkeypatch.setattr(V, "_ClStopped", V._ClStopped)
    import app.mailbox.service as ms

    class Row:
        stored_path = rec
    monkeypatch.setattr(ms, "_file_row", lambda t, fid: Row())
    r = client.post("/api/vocal/cleanup/listen", json={"file_id": "f_up1"}).json()
    assert r["clips"] == 3 and r["found"]["pauses"]
    j = client.post("/api/vocal/cleanup", json={"file_id": "f_up1", "wait": False, "noise": "medium", "target": "reels", "name": "x.wav"}).json()
    assert j["status"] == "working" and j["steps"][0]["t"] == "Listening to your recording"
    for _ in range(200):
        j = client.get(f"/api/vocal/cleanup/job?id={j['id']}").json()
        if j["status"] != "working":
            break
        time.sleep(0.1)
    assert j["status"] == "done" and all(s["state"] == "done" for s in j["steps"]) and abs(j["result"]["after"]["lufs"] + 14) < 1.5
    s = client.get(f"/api/vocal/cleanup/source?id={j['result']['id']}")
    assert s.status_code == 200 and s.headers["content-type"].startswith("audio/wav") and s.headers["cache-control"] == "private, no-store"
    # Stop: a job asked to stop ends between steps
    real = V._cleanup_do

    def slow(*a, **kw):
        kw["stopped"] = lambda: True
        return real(*a, **kw)
    monkeypatch.setattr(V, "_cleanup_do", slow)
    j = client.post("/api/vocal/cleanup", json={"file_id": "f_up1", "wait": False}).json()
    for _ in range(100):
        j = client.get(f"/api/vocal/cleanup/job?id={j['id']}").json()
        if j["status"] != "working":
            break
        time.sleep(0.05)
    assert j["status"] == "stopped" and j["result"] is None
    assert client.get("/api/vocal/cleanup/job?id=cj_000000000000").status_code in (400, 404, 422)
    assert api  # the routes are mounted from the same module


def test_the_console_page_files():
    for bit in ("clListen", "clStart", "clMain", "clWork", "clList", "clNot", "/cleanup/listen", "/cleanup/job", "/cleanup/stop",
                "'cleanup' : 'change'}/source", "Take the voice out of music", "What kind of recording is it?", "What Hoola heard",
                "Hear the difference", "Your clean-ups", "Clean again, stronger"):
        assert bit in JS, bit
    assert ".hv-cl" in CSS


# ---------------------------------------------------------------- the page in a real Chromium
import json  # noqa: E402
from urllib.parse import parse_qs, urlparse  # noqa: E402

from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v0999_96_vocal_redesign_console import CONFIG, FAKE_MIC, ISO, install, open_vocal, overview, page_to  # noqa: E402
from tests.test_v0999_159_voice_changer import NO_SIDEWAYS, UNSAID  # noqa: E402
from tests.test_v121_site import site_env  # noqa: E402,F401

HEARD = {"seconds": 134, "lufs": -27.2, "peak": -0.2, "background": -41.3, "clips": 3, "pauses": 7, "longest": 3.4, "partial": False,
         "found": {"noise": True, "quiet": True, "loud": False, "clips": True, "pauses": True},
         "pick": {"noise": "strong", "denoise": True, "level": True, "silence": True}}
AFTER = {"seconds": 118, "lufs": -16.1, "peak": -1.5, "background": -63.0, "clips": 0, "pauses": 0, "longest": 0, "partial": False}
CLH = [{"id": "vo_eeeeeeeeeeee", "kind": "cleanup", "title": "Shop greeting", "voice_name": "Noise · light · Clearer voice", "seconds": 48, "made": ISO(-3600),
        "ext": "mp3", "engine": "server", "src": "cl_aaaaaaaaaaaa", "src_secs": 48, "src_until": ISO(86400 * 29),
        "before": {**HEARD, "seconds": 48}, "after": {**AFTER, "seconds": 48}, "done": ["Noise · light", "Clearer voice", "Reels and YouTube loudness"],
        "fixes": {"denoise": True, "noise": "light", "voice": True, "level": True, "target": "reels", "silence": False, "gap": 1, "people": False, "music": False}},
       {"id": "vo_ffffffffffff", "kind": "cleanup", "title": "Song voice only", "voice_name": "Taken out of music", "seconds": 185, "made": ISO(-86400 * 40),
        "ext": "mp3", "engine": "eleven", "done": ["Taken out of music"]}]
STEPS = ["Listening to your recording", "Removing background noise", "Making the voice clearer", "Shortening long pauses", "Evening out the loudness", "Checking the result"]


def cl(pg, st):
    def route(r):
        req = r.request
        u = urlparse(req.url)
        path, qs = u.path[len("/api/vocal"):], parse_qs(u.query)
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        j = lambda d, s=200: r.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/overview":
            o = overview()
            o["history"] = st["hist"] + o["history"]
            if st.get("noserver"):
                o["engines"] = [{**e, "state": "off"} if e["id"] == "server" else e for e in o["engines"]]
            return j(o)
        if path == "/cleanup/listen":
            st["listen"].append(body)
            return j(HEARD)
        if path == "/quote" and (body or {}).get("job") == "isolate":
            return j({"credits": 40, "usd": 0.04, "engine": "eleven", "line": "nothing is spent until you tap"})
        if path == "/cleanup" and req.method == "POST":
            st["runs"].append(body)
            st["polls"] = 0
            return j({"id": "cj_aaaaaaaaaaaa", "status": "working", "seconds": 0, "result": None, "error": "", "name": body.get("name"),
                      "steps": [{"t": t, "sub": "", "state": "now" if i == 0 else "wait", "secs": None} for i, t in enumerate(STEPS)]})
        if path == "/cleanup/job":
            st["polls"] += 1
            n = st["polls"]
            if n < 3:
                return j({"id": "cj_aaaaaaaaaaaa", "status": "working", "seconds": n, "result": None, "error": "", "name": "",
                          "steps": [{"t": t, "sub": "", "state": "done" if i < n else "now" if i == n else "wait", "secs": 1.2 if i < n else None} for i, t in enumerate(STEPS)]})
            res = {"id": "vo_gggggggggggg", "kind": "cleanup", "title": "recording-cl", "voice_name": "Noise · strong", "seconds": 118, "made": ISO(),
                   "ext": "mp3", "engine": "server", "src": "cl_bbbbbbbbbbbb", "src_secs": 134, "src_until": ISO(86400 * 30),
                   "before": HEARD, "after": AFTER, "done": ["Noise · strong", "Clearer voice", "Pauses over 1 s", "Podcast loudness"],
                   "fixes": {"denoise": True, "noise": "strong", "voice": True, "level": True, "target": "podcast", "silence": True, "gap": 1, "people": False, "music": False}}
            if res["id"] not in [h["id"] for h in st["hist"]]:
                st["hist"].insert(0, res)
            return j({"id": "cj_aaaaaaaaaaaa", "status": "done", "seconds": 9, "result": res, "error": "", "name": "",
                      "steps": [{"t": t, "sub": "", "state": "done", "secs": 1.2} for t in STEPS]})
        if path == "/cleanup/source":
            st["src"].append(qs["id"][0])
            return r.fulfill(content_type="audio/wav", body=b"RIFF\x24\x00\x00\x00WAVEfmt ")
        return r.fallback()
    pg.route("**/api/vocal/**", route)


def test_clean_up_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("HOOLA_SHOTS")
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "listen": [], "runs": [], "polls": 0, "src": [],
              "hist": [dict(h) for h in CLH]}
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        ctx.add_init_script(FAKE_MIC)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
        pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
        install(pg, st)
        cl(pg, st)
        open_vocal(pg, base)
        page_to(pg, "cleanup", width < 600)
        # the start: three ways in, what can be fixed
        pg.wait_for_selector("#hvView .hv-clstart")
        v = pg.locator("#hvView")
        assert "Make any recording sound clear" in v.text_content() and "Take the voice out of music" in v.text_content()
        assert "What Hoola can fix" in v.text_content() and "Your clean-ups" in v.text_content()
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/cl-{scheme}-{width}-1-start.png")
        # record here -> uploaded -> Hoola listens and picks the fixes
        pg.locator("#hvView [data-a='rec'][data-k='cl']").click()
        pg.wait_for_selector("#hvView [data-a='recstop'][data-k='cl']")
        pg.wait_for_timeout(2200)
        pg.locator("#hvView [data-a='recstop'][data-k='cl']").click()
        pg.wait_for_selector("#hvView .hv-clheard", timeout=10000)
        t = v.text_content()
        assert "What Hoola heard" in t and "Loud words hit the top 3 times" in t and "7 long pauses" in t and "Quiet" in t
        assert st["listen"][-1]["file_id"].startswith("f_up")
        assert pg.locator("#hvView [data-m='UI.cl.silence']").is_checked()                       # picked from what it heard
        assert pg.locator("#hvView [data-a='seg'][data-m='UI.cl.noise'][data-val='strong']").get_attribute("aria-checked") == "true"
        assert "Take the voice out of music" in t and "Clean it · free" in t
        # a kind of recording sets the fixes; then a fix of her own
        pg.locator("#hvView [data-a='clkind'][data-val='phone']").click()
        assert pg.locator("#hvView [data-a='seg'][data-m='UI.cl.noise'][data-val='light']").get_attribute("aria-checked") == "true"
        assert not pg.locator("#hvView [data-m='UI.cl.silence']").is_checked()
        pg.locator("#hvView [data-a='clkind'][data-val='podcast']").click()
        pg.locator("#hvView [data-a='seg'][data-m='UI.cl.noise'][data-val='strong']").click()
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/cl-{scheme}-{width}-2-heard.png")
        # Clean it: the steps one by one, then before / after with the readings
        pg.locator("#hvView [data-a='clrun']").click()
        pg.wait_for_selector("#hvView .hv-clsteps")
        assert "Cleaning your recording" in v.text_content() and pg.locator("#hvView .hv-clsteps>li").count() == 6
        b = st["runs"][-1]
        assert b["wait"] is False and b["noise"] == "strong" and b["target"] == "podcast" and b["silence"] is True and b["gap"] == 1 and b["file_id"].startswith("f_up")
        assert b["people"] is False and b["music"] is False
        if shots:
            pg.wait_for_function("() => document.querySelectorAll('#hvView .hv-clsteps>li.done').length >= 1", timeout=5000)
            pg.screenshot(path=f"{shots}/cl-{scheme}-{width}-3-working.png")
        pg.wait_for_selector("#hvView .hv-clread", timeout=15000)
        t = v.text_content()
        assert "-27 LUFS" in t and "-16 LUFS" in t and "No more crackle" in t and "22 dB quieter" in t and "7 pauses shortened" in t
        pg.locator("#hvView [data-a='clhear'][data-val='before']").click()
        assert "on" in pg.locator("#hvView .hv-chglane.l-before").get_attribute("class")
        assert pg.locator("#hvView [data-a='clagain'][data-val='settings']").count() == 1 and pg.locator("#hvView [data-a='clagain'][data-val='stronger']").count() == 0
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/cl-{scheme}-{width}-4-done.png", full_page=True)
        # Your clean-ups: pairs, her own recording from the server, clean again stronger from the kept recording
        pg.locator("#hvView .hv-chgtop [data-a='clview'][data-val='list']").click()
        pg.wait_for_selector("#hvView .hv-chgc")
        assert pg.locator("#hvView .hv-chgc").count() == 3 and "Your recording no longer kept" in v.text_content()
        pg.locator("#hvView [data-a='clfilt'][data-val='lift']").click()
        assert pg.locator("#hvView .hv-chgc").count() == 1
        pg.locator("#hvView [data-a='clfilt'][data-val='']").click()
        pg.locator("#hvView [data-a='chgsrc'][data-id='vo_eeeeeeeeeeee']").click()
        pg.wait_for_timeout(300)
        assert "vo_eeeeeeeeeeee" in st["src"]
        if shots:
            pg.screenshot(path=f"{shots}/cl-{scheme}-{width}-5-list.png")
        pg.locator("#hvView [data-a='clopen'][data-id='vo_eeeeeeeeeeee']").click()
        pg.wait_for_selector("#hvView [data-a='clagain'][data-val='stronger']")
        pg.locator("#hvView [data-a='clagain'][data-val='stronger']").click()
        pg.wait_for_selector("#hvView .hv-clread", timeout=15000)
        b = st["runs"][-1]
        assert b["source_of"] == "vo_eeeeeeeeeeee" and b["noise"] == "medium" and b["target"] == "reels" and "file_id" not in b
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        assert not errs, errs
        ctx.close()
    # when the server cannot clean, the page says so plainly
    st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "listen": [], "runs": [], "polls": 0, "src": [], "hist": [], "noserver": True}
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)
    cl(pg, st)
    open_vocal(pg, base)
    page_to(pg, "cleanup")
    pg.wait_for_selector("#hvView .hv-chgnot")
    t = pg.locator("#hvView").text_content()
    assert "The sound tool is missing" in t and "nothing is charged" in t
    if shots:
        pg.screenshot(path=f"{shots}/cl-notready.png")
    ctx.close()
