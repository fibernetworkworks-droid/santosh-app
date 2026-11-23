"""v0.999.162 SOUND EFFECTS, PREMIUM - on the server: a sound from words with how closely to follow the words, the takes
made in the background and read one by one, Stop after a take, a partly made run said plainly; Improve the words; Shape it
(trim, fades, volume, speed, backwards, smooth loop) as a new sound, free; game sounds heard without being kept, the whole
set as a ZIP, kept with a star; and the console page walked in a real Chromium."""
import io
import json
import os
import time
import wave
import zipfile
from urllib.parse import parse_qs, urlparse

import numpy as np
import pytest

from app.vocal import eleven as EL
from app.vocal import service as V
from tests.test_v0999_96_vocal_redesign_server import Resp, client, eleven, needs_ff, tone, vg  # noqa: F401

HERE = os.path.dirname(__file__)
JS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal.js"), encoding="utf-8").read()
CSS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal2.css"), encoding="utf-8").read()


def bell(seconds=2.0, rate=44100) -> bytes:
    t = np.arange(int(rate * seconds)) / rate
    x = 0.6 * np.sin(2 * np.pi * 660 * t) * np.exp(-t * 2)
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    return b.getvalue()


@pytest.fixture
def fx(vg, eleven):  # noqa: F811
    sent, replies = eleven
    mp3 = V._convert(bell(), "mp3")
    replies["sound-generation"] = lambda m, u, kw: Resp(content=mp3)
    return sent, replies


# ---------------------------------------------------------------- from words
@needs_ff
def test_a_sound_from_words_follows_her_setting_and_each_take_is_kept(fx):
    sent, _ = fx
    r = V.sfx_text("t1", "A temple bell rung once, far away", seconds=2, loop=False, takes=2, follow=0.8)
    assert r["made"] == 2 and r["failed"] == 0 and [i["take"] for i in r["items"]] == ["A", "B"]
    body = sent[-1][2]["json"]
    assert body["prompt_influence"] == 0.8 and body["duration_seconds"] == 2 and body["loop"] is False
    it = r["items"][0]
    assert it["kind"] == "sfx" and it["follow"] == 0.8 and it["length"] == 2 and it["text"].startswith("A temple bell") and 1.5 < it["seconds"] < 2.6
    r2 = V.sfx_text("t1", "rain", takes=1)                   # her default: 0.3, Auto length
    assert sent[-1][2]["json"]["prompt_influence"] == 0.3 and "duration_seconds" not in sent[-1][2]["json"] and r2["made"] == 1
    with pytest.raises(V.VocalError, match="Describe the sound"):
        V.sfx_text("t1", "x")


@needs_ff
def test_a_run_that_breaks_half_way_keeps_the_made_takes_and_says_so(fx):
    _, replies = fx
    calls = {"n": 0}
    mp3 = V._convert(bell(), "mp3")

    def flaky(m, u, kw):
        calls["n"] += 1
        return Resp(content=mp3) if calls["n"] <= 2 else Resp(status=503, body={"detail": {"message": "busy"}})
    replies["sound-generation"] = flaky
    r = V.sfx_text("t1", "Heavy rain on a tin roof", takes=4)
    assert r["made"] == 2 and r["failed"] == 2 and "after take B" in r["error"] and len(r["items"]) == 2


@needs_ff
def test_the_takes_in_the_background_land_one_by_one_and_stop_after_a_take(fx, client, monkeypatch):  # noqa: F811
    j = client.post("/api/vocal/sfx", json={"prompt": "A small dog barking twice", "takes": 3, "wait": False, "follow": 0.5}).json()
    assert j["status"] == "working" and [s["l"] for s in j["slots"]] == ["A", "B", "C"] and j["opts"]["follow"] == 0.5
    for _ in range(200):
        j = client.get(f"/api/vocal/sfx/job?id={j['id']}").json()
        if j["status"] != "working":
            break
        time.sleep(0.05)
    assert j["status"] == "done" and [s["status"] for s in j["slots"]] == ["done"] * 3 and j["result"]["made"] == 3
    assert all(s["item"]["id"].startswith("vo_") for s in j["slots"])
    # Stop after this take: the made one stays, the rest are skipped
    real = V._fx_do

    def first_only(*a, **kw):
        kw["stopped"] = lambda: True
        return real(*a, **kw)
    monkeypatch.setattr(V, "_fx_do", first_only)
    j = client.post("/api/vocal/sfx", json={"prompt": "A small dog barking twice", "takes": 4, "wait": False}).json()
    V._FX_JOBS[j["id"]]["stop"] = True
    for _ in range(200):
        j = client.get(f"/api/vocal/sfx/job?id={j['id']}").json()
        if j["status"] != "working":
            break
        time.sleep(0.05)
    assert j["status"] == "stopped" and [s["status"] for s in j["slots"]] == ["done", "skipped", "skipped", "skipped"]
    assert client.post("/api/vocal/sfx/stop", json={"id": j["id"]}).status_code == 200
    assert client.get("/api/vocal/sfx/job?id=fj_000000000000").status_code in (404, 422)


def test_words_need_elevenlabs_and_say_so(vg, client):  # noqa: F811
    r = client.post("/api/vocal/sfx", json={"prompt": "rain on a roof", "wait": False})
    assert r.status_code == 422 and "ElevenLabs key" in r.json()["detail"] and "game sounds still work" in r.json()["detail"]


def test_improve_the_words_keeps_her_sound(vg, client, monkeypatch):  # noqa: F811
    seen = []

    def gem(prompt):
        seen.append(prompt)
        return {"text": "A single temple bell struck once, heard from far away, its echo fading slowly", "why": "Said how it fades"}
    monkeypatch.setattr(V, "_gem_json", gem)
    r = client.post("/api/vocal/sfx/improve", json={"prompt": "temple bell far"}).json()
    assert r["text"].startswith("A single temple bell") and r["why"] == "Said how it fades" and r["before"] == "temple bell far"
    assert "never change it into a different sound" in seen[0] and "<<<temple bell far>>>" in seen[0]
    assert client.post("/api/vocal/sfx/improve", json={"prompt": "x"}).status_code == 422


# ---------------------------------------------------------------- game sounds
def test_game_sounds_are_heard_without_being_kept_and_the_set_is_a_zip(vg, client):  # noqa: F811
    r = client.get("/api/vocal/sfx/play?preset=coin&seed=3")
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content[:4] == b"RIFF"
    assert client.get("/api/vocal/sfx/play?preset=coin&seed=3").content == r.content     # the same number, the same sound
    assert V._load("t1")["history"] == []                                                # listening keeps nothing
    d = client.get("/api/vocal/sfx/play?preset=powerup&seed=2&download=1")
    assert 'filename="power-up-2.wav"' in d.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(client.get("/api/vocal/sfx/set?seed=4").content))
    names = z.namelist()
    assert "coin-4.wav" in names and "power-up-4.wav" in names and "README.txt" in names and len(names) == len(V.sfx_presets()) + 1
    assert client.get("/api/vocal/sfx/play?preset=nope").status_code == 422
    k = client.post("/api/vocal/sfx", json={"preset": "coin", "seed": 3}).json()
    assert k["title"] == "Coin #3" and k["engine"] == "server" and k["credits"] == 0
    s = client.post("/api/vocal/history/star", json={"id": k["id"], "on": True}).json()
    assert s["star"] is True and V._load("t1")["history"][0]["star"] is True
    assert "star" not in client.post("/api/vocal/history/star", json={"id": k["id"], "on": False}).json()


# ---------------------------------------------------------------- shape it
@needs_ff
def test_shape_it_makes_a_new_sound_and_leaves_the_take(fx, client):  # noqa: F811
    t = V.sfx_text("t1", "A temple bell rung once", seconds=2, takes=1)["items"][0]
    before = (V._home("t1") / "audio" / f"{t['id']}.mp3").read_bytes()
    r = client.post("/api/vocal/sfx/shape", json={"id": t["id"], "start": 0.2, "end": 1.6, "fade_in": 0.1, "fade_out": 0.4, "gain": 3,
                                                  "speed": 1.25, "reverse": True}).json()
    assert r["shaped_from"] == t["id"] and r["engine"] == "server" and r["credits"] == 0 and r["ext"] == "mp3"
    assert r["shaped"] == ["trimmed", "fade in 0.1 s", "fade out 0.4 s", "+3 dB", "1.25x speed", "backwards"]
    assert 1.0 < r["seconds"] < 1.2                                                   # 1.4 s at 1.25x
    assert (V._home("t1") / "audio" / f"{t['id']}.mp3").read_bytes() == before         # the take stays as it was
    lp = client.post("/api/vocal/sfx/shape", json={"id": t["id"], "loop": True}).json()
    assert lp["loop"] is True and lp["shaped"] == ["smooth loop"]
    assert "Change something first" in client.post("/api/vocal/sfx/shape", json={"id": t["id"]}).json()["detail"]
    assert "Keep at least" in client.post("/api/vocal/sfx/shape", json={"id": t["id"], "start": 1.0, "end": 1.0}).json()["detail"]
    g = V.sfx("t1", "jump", 2)
    gs = V.sfx_shape("t1", g["id"], gain=-6)
    assert gs["ext"] == "wav" and gs["preset"] == "jump" and gs["title"] == "Jump #2 · shaped"


def test_a_kept_sound_is_never_dropped_by_the_limit(vg, monkeypatch):  # noqa: F811
    monkeypatch.setattr(V, "MAX_HISTORY", 3)
    first = V.sfx("t1", "coin", 1)
    V.history_star("t1", first["id"])
    for s in range(2, 7):
        V.sfx("t1", "coin", s)
    ids = [h["id"] for h in V._load("t1")["history"]]
    assert first["id"] in ids and len(ids) == 3


def test_the_console_page_files():
    for bit in ("fxMain", "fxForm", "fxIdeas", "fxTakes", "fxShape", "fxWork", "fxGame", "fxList", "/sfx/job", "/sfx/stop", "/sfx/improve",
                "/sfx/play", "/sfx/set", "/sfx/shape", "/history/star", "Describe any sound. Hoola makes it.", "Improve the words",
                "How closely to follow your words", "Loops smoothly", "Stop after this take", "Save as a new sound", "Download the set",
                "Other versions of", "Your sound effects", "Add to the words", "Ideas to start from"):
        assert bit in JS, bit
    assert ".hv-fxtake" in CSS and ".hv-fxpad" in CSS
    v2 = open(os.path.join(HERE, "..", "app", "static", "console", "v2.js"), encoding="utf-8").read()
    assert "The server did not answer. It may be restarting" in v2                       # a 502 is said in words


# ---------------------------------------------------------------- the page in a real Chromium
from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v0999_96_vocal_redesign_console import CONFIG, ISO, install, open_vocal, overview, page_to  # noqa: E402
from tests.test_v0999_159_voice_changer import NO_SIDEWAYS, UNSAID  # noqa: E402
from tests.test_v121_site import site_env  # noqa: E402,F401

WAV = bell(0.3, 8000)
FXH = [{"id": "vo_a1a1a1a1a1a1", "kind": "sfx", "title": "A small café, cups, quiet talk", "text": "A small café, cups, quiet talk", "seconds": 12, "made": ISO(-86400 * 3),
        "ext": "mp3", "engine": "eleven", "take": "C", "job": "vj_000000000001", "credits": 3, "loop": True, "length": 12, "follow": 0.3},
       {"id": "vo_b2b2b2b2b2b2", "kind": "sfx", "title": "Power-up #1", "seconds": 0.6, "made": ISO(-86400 * 4), "ext": "wav", "engine": "server",
        "preset": "powerup", "seed": 1, "star": True}]


def fxr(pg, st):
    def route(r):
        req = r.request
        u = urlparse(req.url)
        path, qs = u.path[len("/api/vocal"):], parse_qs(u.query)
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        j = lambda d, s=200: r.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/overview":
            o = overview()
            o["history"] = st["hist"] + o["history"]
            o["sfx"] = ["blip", "click", "coin", "explosion", "hit", "hurt", "jump", "laser", "powerup", "select"]
            if st.get("noeleven"):
                o["engines"] = [{**e, "state": "off", "why": "This server has no ElevenLabs key yet."} if e["id"] == "eleven" else e for e in o["engines"]]
            return j(o)
        if path == "/quote" and (body or {}).get("job") == "sfx":
            return j({"credits": 2 * (body.get("takes") or 1), "usd": 0.002, "engine": "eleven", "line": "nothing is spent until you tap"})
        if path == "/sfx/improve":
            st["improve"].append(body)
            return j({"text": "A single temple bell struck once, far away, its echo fading slowly", "why": "Said how it fades", "before": body["prompt"]})
        if path == "/sfx" and req.method == "POST":
            st["runs"].append(body)
            if body.get("preset"):
                row = {"id": "vo_c3c3c3c3c3c3", "kind": "sfx", "title": "Laser #3", "seconds": 0.3, "made": ISO(), "ext": "wav", "engine": "server", "preset": body["preset"], "seed": body["seed"]}
                st["hist"].insert(0, row)
                return j(row)
            st["polls"] = 0
            n = body.get("takes") or 4
            return j({"id": "fj_aaaaaaaaaaaa", "status": "working", "seconds": 0, "result": None, "error": "", "opts": {**body, "follow": body.get("follow")},
                      "slots": [{"l": "ABCD"[i], "status": "now" if i == 0 else "wait", "item": None} for i in range(n)]})
        if path == "/sfx/job":
            st["polls"] += 1
            k = st["polls"]
            n = st["runs"][-1].get("takes") or 4
            items = [{"id": f"vo_d{i}d{i}d{i}d{i}d{i}d{i}", "kind": "sfx", "title": st["runs"][-1]["prompt"][:60], "text": st["runs"][-1]["prompt"], "seconds": 4.6,
                      "made": ISO(), "ext": "mp3", "engine": "eleven", "take": "ABCD"[i], "job": "vj_aaaaaaaaaaaa", "credits": 2, "length": 0, "follow": 0.3} for i in range(n)]
            if k < 3:
                return j({"id": "fj_aaaaaaaaaaaa", "status": "working", "seconds": k, "result": None, "error": "", "opts": st["runs"][-1],
                          "slots": [{"l": "ABCD"[i], "status": "done" if i < k else "now" if i == k else "wait", "item": items[i] if i < k else None} for i in range(n)]})
            for it in items:
                if it["id"] not in [h["id"] for h in st["hist"]]:
                    st["hist"].insert(0, it)
            return j({"id": "fj_aaaaaaaaaaaa", "status": "done", "seconds": 9, "error": "", "opts": st["runs"][-1],
                      "result": {"items": items, "made": n, "asked": n, "failed": 0, "error": ""},
                      "slots": [{"l": "ABCD"[i], "status": "done", "item": items[i]} for i in range(n)]})
        if path == "/sfx/shape":
            st["shape"].append(body)
            row = {"id": "vo_e5e5e5e5e5e5", "kind": "sfx", "title": "shaped", "seconds": 3.8, "made": ISO(), "ext": "mp3", "engine": "server",
                   "shaped_from": body["id"], "shaped": ["trimmed", "fade out 0.8 s"]}
            st["hist"].insert(0, row)
            return j(row)
        if path == "/history/star":
            st["star"].append(body)
            for h in st["hist"]:
                if h["id"] == body["id"]:
                    h["star"] = body["on"]
            return j({"id": body["id"], "star": body["on"]})
        if path in ("/sfx/play", "/sfx/set", "/audio"):
            st["play"].append((path, qs))
            return r.fulfill(content_type="application/zip" if path == "/sfx/set" else "audio/wav", body=WAV)
        return r.fallback()
    pg.route("**/api/vocal/**", route)


def _st(**kw):
    return {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "runs": [], "polls": 0, "improve": [],
            "shape": [], "star": [], "play": [], "hist": [dict(h) for h in FXH], **kw}


def test_sound_effects_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("HOOLA_SHOTS")
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        st = _st()
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
        pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
        install(pg, st)
        fxr(pg, st)
        open_vocal(pg, base)
        page_to(pg, "sfx", width < 600)
        # the start: describe, ideas by kind, the game strip
        pg.wait_for_selector("#hvView .hv-fxideas")
        v = pg.locator("#hvView")
        t = v.text_content()
        assert "Describe any sound. Hoola makes it." in t and "Ideas to start from" in t and "Heavy rain on a tin roof" in t and "Making a game?" in t
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/fx-{scheme}-{width}-1-start.png", full_page=True)
        pg.locator("#hvView [data-a='fxidea'][data-val='Celebrations']").click()
        pg.locator("#hvView [data-a='fxuse'][data-val='A temple bell rung once, soft echo']").click()
        assert pg.locator("#hvFx").input_value() == "A temple bell rung once, soft echo"
        pg.locator("#hvView [data-a='fxadd'][data-val='far away']").click()
        assert pg.locator("#hvFx").input_value() == "A temple bell rung once, soft echo, far away"
        assert pg.locator("#hvView [data-a='fxadd'][data-val='far away']").get_attribute("aria-pressed") == "true"
        pg.locator("#hvView [data-a='fximprove']").click()
        pg.wait_for_selector("#hvView .hv-fximp")
        assert "Said how it fades" in v.text_content() and st["improve"][-1]["prompt"].endswith("far away")
        pg.locator("#hvView [data-a='fximpuse']").click()
        assert pg.locator("#hvFx").input_value().startswith("A single temple bell")
        pg.locator("#hvView [data-a='seg'][data-m='UI.fx.seconds'][data-val='5']").click()
        pg.locator("#hvFxF").fill("8")
        assert pg.locator("[data-show-follow]").text_content() == "Close"
        pg.locator("#hvView [data-a='seg'][data-m='UI.fx.takes'][data-val='3']").click()
        if shots:
            pg.screenshot(path=f"{shots}/fx-{scheme}-{width}-2-form.png", full_page=True)
        # Make: the takes land one by one, then the takes with Shape
        pg.locator("#hvView [data-a='fxmake']").click()
        pg.wait_for_selector("#hvView .hv-fxslots")
        assert "Making your sound" in v.text_content() and pg.locator("#hvView .hv-fxslot").count() == 3
        b = st["runs"][-1]
        assert b["wait"] is False and b["seconds"] == 5 and b["takes"] == 3 and b["follow"] == 0.8 and b["prompt"].startswith("A single temple bell")
        if shots:
            pg.wait_for_function("() => document.querySelectorAll('#hvView .hv-fxslot.done').length >= 1", timeout=5000)
            pg.screenshot(path=f"{shots}/fx-{scheme}-{width}-3-working.png")
        pg.wait_for_selector("#hvView .hv-fxtakes", timeout=15000)
        assert pg.locator("#hvView .hv-fxtake").count() == 3 and "Shape take A" in v.text_content()
        pg.locator("#hvView [data-a='fxsel'][data-id='vo_d1d1d1d1d1d1']").click()
        assert "Shape take B" in v.text_content()
        pg.locator("#hvView [data-a='fxstar'][data-id='vo_d1d1d1d1d1d1']").click()
        pg.wait_for_timeout(200)
        assert st["star"][-1] == {"id": "vo_d1d1d1d1d1d1", "on": True}
        pg.locator("#hvFxSstart").fill("0.3")
        pg.locator("#hvFxSfade_out").fill("0.8")
        assert "0.3 s" in pg.locator("[data-shp-range]").text_content()
        pg.locator("#hvView [data-a='fxshp'][data-val='reverse']").click()
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/fx-{scheme}-{width}-4-takes.png", full_page=True)
        pg.locator("#hvView [data-a='fxshpsave']").click()
        pg.wait_for_selector("#hvView .hv-fxmade", timeout=5000)
        sb = st["shape"][-1]
        assert sb["id"] == "vo_d1d1d1d1d1d1" and sb["start"] == 0.3 and sb["fade_out"] == 0.8 and sb["reverse"] is True
        # game sounds: heard without keeping, versions, keep, the set
        pg.locator("#hvView [data-a='fxtab'][data-val='game']").first.click()
        pg.wait_for_selector("#hvView .hv-fxpads")
        assert pg.locator("#hvView .hv-fxpad").count() == 10 and "Download the set" in v.text_content()
        pg.locator("#hvView [data-a='fxpad'][data-val='laser']").click()
        pg.locator("#hvView [data-a='fxseed'][data-val='3']").click()
        pg.wait_for_timeout(300)
        assert any(p == "/sfx/play" and q.get("preset") == ["laser"] and q.get("seed") == ["3"] for p, q in st["play"])
        assert "Laser #3" in v.text_content() and "Other versions of Laser" in v.text_content()
        if shots:
            pg.screenshot(path=f"{shots}/fx-{scheme}-{width}-5-game.png", full_page=True)
        pg.locator("#hvView [data-a='fxkeep']").click()
        pg.wait_for_timeout(400)
        assert st["runs"][-1] == {"preset": "laser", "seed": 3} and st["star"][-1] == {"id": "vo_c3c3c3c3c3c3", "on": True}
        pg.locator("#hvView [data-a='fxset']").click()
        pg.wait_for_timeout(300)
        assert any(p == "/sfx/set" for p, _ in st["play"])
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        # your sound effects: by day, filters, more like this
        pg.locator("#hvView [data-a='fxview'][data-val='list']").click()
        pg.wait_for_selector("#hvView .hv-fxlist")
        assert "Today" in v.text_content() and "Earlier this week" in v.text_content()
        pg.locator("#hvView [data-a='fxfilt'][data-val='game']").click()
        assert pg.locator("#hvView .hv-fxli").count() == 2
        pg.locator("#hvView [data-a='fxfilt'][data-val='kept']").click()
        assert pg.locator("#hvView .hv-fxli").count() >= 2
        pg.locator("#hvView [data-a='fxfilt'][data-val='']").click()
        if shots:
            pg.screenshot(path=f"{shots}/fx-{scheme}-{width}-6-list.png", full_page=True)
        pg.locator("#hvView [data-a='fxagain'][data-id='vo_a1a1a1a1a1a1']").click()
        pg.wait_for_selector("#hvView .hv-fxtakes")
        assert pg.locator("#hvFx").input_value() == "A small café, cups, quiet talk" and pg.locator(".hv-fxsw").is_checked()
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        assert not errs, errs
        ctx.close()
    # no ElevenLabs: the words side says so and sends her to game sounds, which still work
    st = _st(noeleven=True, hist=[])
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)
    fxr(pg, st)
    open_vocal(pg, base)
    page_to(pg, "sfx")
    pg.wait_for_selector("#hvView .hv-fxnot")
    t = pg.locator("#hvView").text_content()
    assert "Sounds from words are not on this server yet" in t and "Game sounds always work" in t
    assert pg.locator("#hvView [data-a='fxmake']").is_disabled()
    if shots:
        pg.screenshot(path=f"{shots}/fx-notready.png")
    pg.locator("#hvView .hv-fxnot [data-a='fxtab'][data-val='game']").click()
    pg.wait_for_selector("#hvView .hv-fxpads")
    ctx.close()
