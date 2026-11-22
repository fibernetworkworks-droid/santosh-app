"""v0.999.156 YOUR VOICE, PREMIUM - one of her voices renamed and its consent recording played back on the server, and the
console page walked in a real Chromium: her voices as cards (filters, sample in her language, used in), the first time
(three ways, how it is made), recording with four checks read from the sound, describing with three options, changing with
before and after, and one voice (rename, consent, in your work, default, download, delete)."""
import json
import math
import os
import re
import struct
import wave
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from app.vocal import service as V
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v0999_96_vocal_redesign_console import CONFIG, ISO, install, open_vocal, overview, page_to
from tests.test_v0999_96_vocal_redesign_server import client, vg  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

HERE = os.path.dirname(__file__)
JS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal.js"), encoding="utf-8").read()
CSS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal2.css"), encoding="utf-8").read()


def wav(seconds=1.0, amp=0.3, rate=16000):
    b = BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(amp * 32767 * math.sin(i / 8))) for i in range(int(seconds * rate))))
    return b.getvalue()


def _put_voice(tenant, vid, kind="clone", consent=True):
    d = V._load(tenant)
    d["voices"].insert(0, {"id": vid, "name": "Meghana", "kind": kind, "lang": "hi", "engine": "gemini", "gid": "g1", "made": ISO(-86400),
                           "consent_at": ISO(-86400), "sample": f"{vid}.wav"})
    V._store(tenant, d)
    home = V._home(tenant) / "samples"
    home.mkdir(parents=True, exist_ok=True)
    (home / f"{vid}.wav").write_bytes(wav())
    if consent:
        (home / f"{vid}.consent.wav").write_bytes(wav(0.5))


def test_rename_and_the_consent_recording(vg, client):
    _put_voice("t1", "mv_aaaaaaaaaaaa")
    _put_voice("t1", "mv_bbbbbbbbbbbb", kind="design", consent=False)
    mine = {v["id"]: v for v in V.overview("t1")["voices"] if v.get("kind") != "hoola"}
    assert mine["mv_aaaaaaaaaaaa"]["consent_kept"] is True and mine["mv_bbbbbbbbbbbb"]["consent_kept"] is False
    r = client.patch("/api/vocal/voice", json={"id": "mv_aaaaaaaaaaaa", "name": "  Meghana, <b>warm</b>  "})
    assert r.status_code == 200 and r.json()["name"] == "Meghana, <b>warm</b>"                    # trimmed; the page escapes it
    assert client.patch("/api/vocal/voice", json={"id": "mv_aaaaaaaaaaaa", "name": "   "}).status_code == 422      # a name is needed
    assert client.patch("/api/vocal/voice", json={"id": "hv_Kore", "name": "Mine now"}).status_code in (404, 422)  # never a Hoola voice
    c = client.get("/api/vocal/voice/consent?id=mv_aaaaaaaaaaaa")
    assert c.status_code == 200 and c.content[:4] == b"RIFF" and c.headers["cache-control"].startswith("private")
    assert client.get("/api/vocal/voice/consent?id=mv_bbbbbbbbbbbb").status_code in (404, 422)                    # no consent kept for it
    assert client.get("/api/vocal/voice/consent?id=mv_zzzzzzzzzzzz").status_code in (404, 422)
    client.delete("/api/vocal/voice?id=mv_aaaaaaaaaaaa")                                                          # the proof goes with the voice
    assert not (V._home("t1") / "samples" / "mv_aaaaaaaaaaaa.consent.wav").exists()
    assert client.get("/api/vocal/voice/consent?id=mv_aaaaaaaaaaaa").status_code in (404, 422)


def test_the_files_carry_the_design():
    for k in ("yvHome", "yvFirst", "yvRecord", "yvDesign", "yvRemix", "yvDetail", "yMeter", "Make another voice",
              "A voice that is yours, in every language you work in.", "Checks on your recording", "Loud enough", "Little background noise",
              "Your consent is kept", "Hear it say your words", "Before and after, the same words", "Keep the new voice", "Make your default voice",
              "Download the sample", "Delete this voice", "/voice/consent", "'PATCH'"):
        assert k in JS, k
    for k in ("v0.999.156 Your voice", ".hv-yvgrid", ".hv-yvsteps", ".hv-recb.xl", ".hv-yvlvl", ".hv-yvopts", ".hv-yvba", ".hv-yvacts"):
        assert k in CSS, k
    assert not re.search(r"#[0-9A-Fa-f]{3,6}\b", CSS) and "<select" not in JS
    assert 'title="${n}"${id === on' not in JS                                  # sidebar tooltips only while the labels are hidden


MINE = [{"id": "v_me", "name": "Meghana", "kind": "clone", "lang": "hi", "langs": [], "any": True, "engine": "gemini", "tier": "standard", "ready": True,
         "made": ISO(-86400), "consent_at": ISO(-86400), "consent_kept": True},
        {"id": "v_teach", "name": "Kind teacher", "kind": "design", "description": "A kind older teacher, slow and clear", "langs": [], "any": True,
         "engine": "gemini", "tier": "standard", "ready": True, "made": ISO(-3600)}]


def yv(pg, st):
    def route(r):
        req = r.request
        u = urlparse(req.url)
        path, qs = u.path[len("/api/vocal"):], parse_qs(u.query)
        body = req.post_data_json if req.method in ("POST", "PUT", "PATCH") and req.post_data else None
        j = lambda d, s=200: r.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/overview":
            o = overview()
            o["voices"] = [v for v in o["voices"] if v["kind"] == "hoola"] + st["mine"]
            o["sample_lines"] = {"en": "Hello, this is how I sound.", "hi": "Namaste, meri awaaz aisi sunai deti hai."}
            o["history"] = [{**o["history"][0], "voice": "v_me", "title": "Founder message"}, *o["history"][1:]]
            o["settings"] = st["settings_now"]
            return j(o)
        if path == "/voice" and req.method == "PATCH":
            st["renamed"].append(body)
            for v in st["mine"]:
                if v["id"] == body["id"]:
                    v["name"] = body["name"]
            return j(next(v for v in st["mine"] if v["id"] == body["id"]))
        if path == "/voice" and req.method == "DELETE":
            st["deleted"].append(qs["id"][0])
            st["mine"] = [v for v in st["mine"] if v["id"] != qs["id"][0]]
            return j({"removed": qs["id"][0]})
        if path == "/voice/consent":
            st["consent"].append(qs["id"][0])
            return r.fulfill(content_type="audio/wav", body=wav(0.3))
        if path == "/voice/design":
            st["design"].append(body)
            return j({"previews": [{"pid": f"pv_{i}", "audio_id": f"vo_p{i}", "title": f"Option {i}"} for i in range(3)]})
        if path == "/voice/design/save":
            st["saved"].append(body)
            v = {"id": "v_new", "name": body["name"], "kind": "design", "langs": [], "any": True, "engine": "gemini", "tier": "standard", "ready": True, "made": ISO()}
            st["mine"].insert(0, v)
            return j(v)
        if path == "/voice/remix":
            st["remix"].append(body)
            v = {"id": "v_rx", "name": body["name"], "kind": "remix", "base": body["base"], "base_name": "Meghana", "langs": [], "any": True,
                 "engine": "gemini", "tier": "standard", "ready": True, "made": ISO()}
            st["mine"].insert(0, v)
            return j(v)
        if path == "/settings" and req.method == "PUT":
            st["settings_now"] = {**st["settings_now"], **body}
            st["settings"].append(body)
            return j({"settings": st["settings_now"]})
        return r.fallback()
    pg.route("**/api/vocal/**", route)


NO_SIDEWAYS = "() => document.documentElement.scrollWidth <= innerWidth + 1 && document.querySelector('#hvRoot').scrollWidth <= document.querySelector('#hvRoot').clientWidth + 1"


def test_your_voice_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("HOOLA_SHOTS")
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "settings": [], "addlang": [],
              "mine": [dict(v) for v in MINE], "renamed": [], "deleted": [], "consent": [], "design": [], "saved": [], "remix": [], "settings_now": {}}
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
        pg.on("dialog", lambda d: d.accept())
        pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
        install(pg, st)
        yv(pg, st)
        open_vocal(pg, base)
        narrow = width < 600
        page_to(pg, "mine", narrow)
        # her voices: a card each, the sample in her language, used in her work
        pg.wait_for_selector("#hvView .hv-yvc")
        assert pg.locator("#hvView .hv-yvc").count() == 2 and pg.locator("#hvRoot h1").count() == 1
        card = pg.locator("#hvView .hv-yvc").first
        assert "Recorded from you" in card.text_content() and "Your consent is kept" in card.text_content() and "Used in 1 sound" in card.text_content()
        pg.locator("#hvView [data-a='yvf'][data-val='design']").click()
        pg.wait_for_function("() => document.querySelectorAll('#hvView .hv-yvc').length === 1")
        assert "Kind teacher" in pg.locator("#hvView .hv-yvc").text_content()
        pg.locator("#hvView [data-a='yvf'][data-val='all']").click()
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/yv-{scheme}-{width}-1-home.png")
        # one voice: rename, the consent recording, in your work, default, download
        pg.locator("#hvView [data-a='yvopen'][data-id='v_me']").click()
        pg.wait_for_selector("#hvView .hv-yvd")
        assert "Founder message" in pg.locator("#hvView").text_content() and "Only you can use it" in pg.locator("#hvView").text_content()
        pg.locator("#hvView [data-a='yvren']").click()
        pg.locator("#hvRen").fill("Meghana, warm")
        pg.locator("#hvRen").press("Enter")
        pg.wait_for_function("() => document.querySelector('#hvView .hv-vdn')?.textContent === 'Meghana, warm'")
        assert st["renamed"] == [{"id": "v_me", "name": "Meghana, warm"}]
        pg.locator("#hvView [data-a='yvcons']").click()
        pg.wait_for_timeout(400)
        assert st["consent"] == ["v_me"]
        pg.locator("#hvView [data-a='yvdef']").click()
        pg.wait_for_function("() => document.querySelector('#hvView .hv-yvd').textContent.includes('Your default voice')")
        assert st["settings"][-1]["voice"] == "v_me"
        with pg.expect_download() as dl:
            pg.locator("#hvView [data-a='yvdl']").click()
        assert dl.value.suggested_filename.endswith("sample.wav")
        if shots:
            pg.screenshot(path=f"{shots}/yv-{scheme}-{width}-2-voice.png")
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        # describe a voice: chips add to the words, three options, pick and save opens the new voice
        pg.locator("#hvView [data-a='yvhome']").click()
        pg.locator("#hvView .hv-yvway[data-val='design']").click()
        pg.wait_for_selector("#hvDDesc")
        pg.locator("#hvDDesc").fill("A kind older teacher")
        pg.locator("#hvView [data-a='dadd'][data-val='slow']").click()
        assert pg.locator("#hvDDesc").input_value() == "A kind older teacher, slow"
        pg.locator("#hvView [data-qbtn='design']").click()
        pg.wait_for_selector("#hvView .hv-yvopt")
        assert pg.locator("#hvView .hv-yvopt").count() == 3 and st["design"][-1]["description"] == "A kind older teacher, slow"
        pg.locator("#hvView [data-a='dpick'][data-val='pv_1']").click()
        assert "Save option B" in pg.locator("#hvView [data-a='dsave']").text_content()
        if shots:
            pg.screenshot(path=f"{shots}/yv-{scheme}-{width}-3-describe.png")
        pg.locator("#hvDName").fill("Teacher two")
        pg.locator("#hvView [data-a='dsave']").click()
        pg.wait_for_function("() => document.querySelector('#hvView .hv-vdn')?.textContent === 'Teacher two'")
        assert st["saved"][-1] == {"pid": "pv_1", "name": "Teacher two"}
        # change a voice: chips write the sentence, before and after, not this one = removed
        pg.locator("#hvView [data-a='yvhome']").click()
        pg.locator("#hvView .hv-yvway[data-val='remix']").click()
        pg.locator("#hvView [data-a='rxpick'][data-k='Age'][data-val='Older']").click()
        pg.locator("#hvView [data-a='rxpick'][data-k='Pace'][data-val='Slower']").click()
        assert pg.locator("#hvRChange").input_value() == "Same voice, but older, slower"
        pg.locator("#hvRName").fill("Meghana, older")
        pg.locator("#hvView [data-qbtn='remix']").click()
        pg.wait_for_selector("#hvView .hv-yvba")
        assert st["remix"][-1]["change"] == "Same voice, but older, slower"
        if shots:
            pg.screenshot(path=f"{shots}/yv-{scheme}-{width}-4-change.png")
        pg.locator("#hvView [data-a='rxdrop']").click()
        pg.wait_for_function("() => !document.querySelector('#hvView .hv-yvba')")
        assert st["deleted"] == ["v_rx"]
        # record: the steps, the mic, and the way back; nothing recorded yet means no checks
        pg.locator("#hvView .hv-yvpick [data-val='record']").click()
        pg.wait_for_selector("#hvView .hv-yvsteps li.now")
        assert "Read the line" in pg.locator("#hvView .hv-yvsteps li.now").text_content()
        assert pg.locator("#hvView .hv-recb.xl").count() == 1 and "are checked as soon as you stop" in pg.locator("#hvView").text_content()
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/yv-{scheme}-{width}-5-record.png")
        # delete a voice from its page; with none left the first-time page shows
        pg.locator("#hvView [data-a='yvhome']").click()
        for vid in [v["id"] for v in st["mine"]]:
            pg.locator(f"#hvView [data-a='yvopen'][data-id='{vid}']").click()
            pg.locator("#hvView [data-a='yvrm']").click()
            pg.wait_for_function("v => !document.querySelector(`#hvView [data-a='yvopen'][data-id='${v}']`) && !document.querySelector('#hvView .hv-yvd')", arg=vid)
        pg.wait_for_selector("#hvView .hv-yvfirst")
        assert "A voice that is yours, in every language you work in." in pg.locator("#hvView").text_content()
        assert pg.locator("#hvView .hv-yvbw").count() == 3 and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/yv-{scheme}-{width}-6-first.png")
        assert not errs, errs
        ctx.close()
