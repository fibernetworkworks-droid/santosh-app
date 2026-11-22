"""v0.999.148 DUBBING, PREMIUM - the server half: the matched dub in steps (heard -> translated -> her OK -> spoken ->
mixed), her words that are never translated, speaker names + voices, changed lines made again together, shorten /
read faster / who says it, languages added to the same dub, the downloads. Gemini is faked at its seams; ffmpeg is real."""
import io
import json
import subprocess
import time
import zipfile

import pytest

from app.vocal import dubbing as DB
from app.vocal import service as V
from tests.test_v0999_96_vocal_redesign_server import client, make_video, needs_ff, tone, vg  # noqa: F401

LINES = [{"start": 0.2, "end": 1.6, "speaker": "S1", "text": "Welcome to Asha Sweets.", "tr": {"Spanish": "Bienvenidos a Asha Sweets."}},
         {"start": 2.0, "end": 2.6, "speaker": "S2", "text": "No colours. Ever.", "tr": {"Spanish": "Nunca colores. Jamás, es nuestra promesa a todos."}},
         {"start": 3.0, "end": 3.8, "speaker": "S1", "text": "Order from Asha Sweets.", "tr": {"Spanish": "Pida a Asha Dulces."}}]


@pytest.fixture
def fake(monkeypatch):
    said = []

    def listen(src, names, keep):
        said.append(("listen", tuple(names), tuple(keep)))
        return {"source_language": "English", "speakers": [{"id": "S1", "gender": "female"}, {"id": "S2", "gender": "male"}],
                "lines": [{**ln, "tr": {n: ln["tr"]["Spanish"] if n == "Spanish" else f"{n} {i}" for n in names}}
                          for i, ln in enumerate(json.loads(json.dumps(LINES)))]}

    def speak(text, voice, lang_name, pace=1.0):
        said.append(("speak", text, voice, lang_name, pace))
        return tone(0.3 + ((len(text) + 3 * len(voice) + int(pace * 100)) % 9) * 0.05)
    monkeypatch.setattr(DB, "listen", listen)
    monkeypatch.setattr(DB, "speak", speak)
    monkeypatch.setattr(DB, "translate", lambda lines, lang, keep: said.append(("translate", lang)) or [f"{lang} {i}" for i in range(len(lines))])
    monkeypatch.setattr(DB, "shorter", lambda text, lang, secs, keep: said.append(("shorter", text, round(secs, 1))) or "Nunca colores.")
    return said


def _wait(did, pred, t=20):
    end = time.time() + t
    while time.time() < end:
        g = DB.view("t1", did)
        if pred(g):
            return g
        time.sleep(0.05)
    raise AssertionError(DB.view("t1", did))


def _start(tmp_path, **kw):
    vid = tmp_path / "tour.mp4"
    make_video(vid, 4)
    return V.dub_start("t1", str(vid), kw.pop("langs", ["es"]), **kw)


@needs_ff
def test_a_dub_waits_for_her_ok_then_speaks(vg, fake, tmp_path, client):
    r = _start(tmp_path, keep=["Asha Sweets"], check=True)
    g = _wait(r["id"], lambda g: g["status"] == "check")
    assert ("listen", ("Spanish",), ("Asha Sweets",)) in fake and not [x for x in fake if x[0] == "speak"]
    assert g["langs"][0]["status"] == "check" and g["langs"][0]["step"] == "check"
    assert [p["name"] for p in g["people"]] == ["Speaker 1", "Speaker 2"] and g["people"][0]["lines"] == 2
    ls = client.get(f"/api/vocal/dub/{r['id']}/lines?lang=es").json()
    assert ls["editable"] and ls["status"] == "check" and len(ls["lines"]) == 3
    assert ls["lines"][2]["kept_missing"] == ["Asha Sweets"] and ls["lines"][0]["kept_missing"] == []   # checked in code
    assert ls["lines"][1]["too_long"] and ls["lines"][1]["fit"] > 130
    client.put(f"/api/vocal/dub/{r['id']}/speakers", json={"names": {"S1": "Priya", "S2": "Rahul"}})
    assert client.post(f"/api/vocal/dub/{r['id']}/ok", json={"lang": "es"}).status_code == 200
    g = _wait(r["id"], lambda g: g["status"] == "ready")
    assert g["langs"][0]["video_id"] and g["changed"] == {"es": 0}
    sp = [x for x in fake if x[0] == "speak"]
    assert len(sp) == 3 and {x[2] for x in sp} == {"Kore", "Puck"} and all(x[3] == "Spanish" for x in sp)
    assert [p["name"] for p in g["people"]] == ["Priya", "Rahul"]
    assert client.post(f"/api/vocal/dub/{r['id']}/ok", json={"lang": "es"}).status_code == 422


@needs_ff
def test_changed_lines_are_made_again_together(vg, fake, tmp_path, client):
    r = _start(tmp_path)
    did = r["id"]
    _wait(did, lambda g: g["status"] == "ready")
    vid = DB.view("t1", did)["langs"][0]["video_id"]
    before = V.audio_file("t1", vid)[0].read_bytes()
    assert client.post(f"/api/vocal/dub/{did}/remake", json={"lang": "es"}).status_code == 422          # nothing changed
    sh = client.post(f"/api/vocal/dub/{did}/lines/1/shorten", json={"lang": "es"}).json()
    assert sh["before"].startswith("Nunca colores. Jamás") and sh["line"]["dst"] == "Nunca colores." and sh["line"]["edited"]
    client.put(f"/api/vocal/dub/{did}/lines/2", json={"lang": "es", "pace": 1.15})
    client.put(f"/api/vocal/dub/{did}/lines/0", json={"lang": "es", "speaker": "S2"})
    assert client.put(f"/api/vocal/dub/{did}/lines/0", json={"lang": "es", "speaker": "S9"}).status_code == 422
    assert DB.view("t1", did)["changed"] == {"es": 3}
    fake.clear()
    assert client.post(f"/api/vocal/dub/{did}/remake", json={"lang": "es"}).status_code == 200
    g = _wait(did, lambda g: g["status"] == "ready" and g["changed"] == {"es": 0})
    sp = [x for x in fake if x[0] == "speak"]
    assert sorted((x[1], x[2], x[4]) for x in sp) == sorted([("Nunca colores.", "Puck", 1.0), ("Pida a Asha Dulces.", "Kore", 1.15),
                                                            ("Bienvenidos a Asha Sweets.", "Puck", 1.0)])
    assert g["langs"][0]["video_id"] == vid and V.audio_file("t1", vid)[0].read_bytes() != before
    # a new voice for a person makes their lines changed
    client.put(f"/api/vocal/dub/{did}/speakers", json={"voices": {"S1": "hv_Aoede"}})
    assert DB.view("t1", did)["changed"] == {"es": 1}


@needs_ff
def test_more_languages_join_the_same_dub(vg, fake, tmp_path, client):
    r = _start(tmp_path)
    did = r["id"]
    _wait(did, lambda g: g["status"] == "ready")
    out = client.post(f"/api/vocal/dub/{did}/langs", json={"langs": ["hi"]}).json()
    assert out["id"] == did and [x["code"] for x in out["langs"]] == ["es", "hi"]
    g = _wait(did, lambda g: all(x["status"] == "ready" for x in g["langs"]))
    assert ("translate", "Hindi") in fake and len([x for x in fake if x[0] == "listen"]) == 1
    assert len(V.dubs("t1")) == 1 and g["lines"][0]["tr"]["hi"] == "Hindi 0"
    assert client.post(f"/api/vocal/dub/{did}/langs", json={"langs": ["hi"]}).status_code == 422


@needs_ff
def test_downloads_and_the_people(vg, fake, tmp_path, client):
    r = _start(tmp_path, langs=["es", "fr"])
    did = r["id"]
    _wait(did, lambda g: g["status"] == "ready")
    v = client.get(f"/api/vocal/dub/{did}/export?what=video&langs=es")
    assert v.status_code == 200 and v.headers["content-type"] == "video/mp4" and v.content[4:8] == b"ftyp"
    z = client.get(f"/api/vocal/dub/{did}/export?what=subs&langs=es,fr")
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert z.headers["content-type"] == "application/zip" and sorted(names) == ["French/tour - French.srt", "French/tour - French.vtt",
                                                                               "Spanish/tour - Spanish.srt", "Spanish/tour - Spanish.vtt"]
    s = client.get(f"/api/vocal/dub/{did}/export?what=sound&langs=es")
    assert s.headers["content-type"] == "audio/mpeg" and len(s.content) > 500
    t = client.get(f"/api/vocal/dub/{did}/export?what=voices&langs=es")
    tn = zipfile.ZipFile(io.BytesIO(t.content)).namelist()
    assert "tour - Spanish - Speaker 1.mp3" in tn and "tour - Spanish - Speaker 2.mp3" in tn and any("Original sound" in n for n in tn)
    if DB.can_burn():
        b = client.get(f"/api/vocal/dub/{did}/export?what=subbed&langs=es")
        assert b.status_code == 200 and b.content[4:8] == b"ftyp"
    assert client.get(f"/api/vocal/dub/{did}/speaker?sp=S1").headers["content-type"] == "audio/mpeg"
    assert client.get(f"/api/vocal/dub/{did}/speaker?sp=S7").status_code == 404
    assert client.get(f"/api/vocal/dub/{did}/poster").headers["content-type"] == "image/jpeg"
    assert client.get(f"/api/vocal/dub/{did}/source").status_code == 200
    assert client.get(f"/api/vocal/dub/{did}/export?what=video&langs=de").status_code == 422
    client.put(f"/api/vocal/dub/{did}/keep", json={"words": ["Asha Sweets", "asha sweets", "Kaju Katli"]})
    assert DB.view("t1", did)["keep"] == ["Asha Sweets", "Kaju Katli"]
    assert client.delete(f"/api/vocal/dub/{did}").json() == {"ok": True} and V.dubs("t1") == []


@needs_ff
def test_stop_and_a_failed_hearing(vg, fake, tmp_path, monkeypatch):
    def bad(src, names, keep):
        raise V.VocalError("No spoken line was found in this video.")
    monkeypatch.setattr(DB, "listen", bad)
    r = _start(tmp_path)
    g = _wait(r["id"], lambda g: g["status"] != "working")
    assert g["status"] == "failed" and "No spoken line" in g["langs"][0]["error"]


@needs_ff
def test_ok_after_a_stop_still_speaks(vg, fake, tmp_path, client):
    r = _start(tmp_path, check=True)
    _wait(r["id"], lambda g: g["status"] == "check")
    assert client.post(f"/api/vocal/dub/{r['id']}/stop").status_code == 200
    assert client.post(f"/api/vocal/dub/{r['id']}/ok", json={"lang": "es"}).status_code == 200
    g = _wait(r["id"], lambda g: g["status"] in ("ready", "failed"))
    assert g["status"] == "ready", g


# ------------------------------------------------------------------ the console, in a real Chromium ---
import os  # noqa: E402
import re  # noqa: E402
from urllib.parse import parse_qs, urlparse  # noqa: E402

from tests.test_v0312_arena_screen import arena_server  # noqa: F401,E402
from tests.test_v121_site import site_env  # noqa: F401,E402
from tests.test_v0999_96_vocal_redesign_console import CONFIG, ISO, install, open_vocal, page_to  # noqa: E402

HERE = os.path.dirname(__file__)
JS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal.js"), encoding="utf-8").read()
CSS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal2.css"), encoding="utf-8").read()


def test_the_files_carry_the_design():
    for k in ("hv-dubgrid", "dubNewView", "dubMaking", "dubWork", "dvVoices", "dvDownload", "dvKeep", "/export?what=", "/shorten", "/remake",
              "OK, speak the", "Let me read the lines before they are spoken", "Words to keep as they are", "of their time"):
        assert k in JS, k
    for k in ("v0.999.148 DUBBING, PREMIUM", ".hv-dubc", ".hv-dlane", ".hv-steps", ".hv-dubfoot"):
        assert k in CSS, k
    assert not re.search(r"#[0-9A-Fa-f]{3,6}\b", CSS) and "<select" not in JS


def _lines():
    return [{"n": 0, "start": 0.2, "end": 1.6, "speaker": "S1", "name": "Priya", "src": "Welcome to Asha Sweets.", "dst": "Bienvenidos a Asha Sweets.", "fit": 82, "room": 1.4, "pace": 1.0},
            {"n": 1, "start": 2.0, "end": 2.6, "speaker": "S2", "name": "Rahul", "src": "No colours. Ever.", "dst": "Nunca colores. Jamás, es nuestra promesa.", "too_long": True, "fit": 168, "room": 0.6, "pace": 1.0},
            {"n": 2, "start": 3.0, "end": 3.8, "speaker": "S1", "name": "Priya", "src": "Order from Asha Sweets.", "dst": "Pida a Asha Dulces.", "fit": 74, "room": 0.8, "pace": 1.0, "kept_missing": ["Asha Sweets"]}]


def dubs(pg, st):
    people = [{"id": "S1", "name": "Priya", "lines": 2, "seconds": 2.2, "quote": "Welcome to Asha Sweets.", "gender": "female", "voice": "Kore", "voice_id": "hv_Kore"},
              {"id": "S2", "name": "Rahul", "lines": 1, "seconds": 0.6, "quote": "No colours. Ever.", "gender": "male", "voice": "Puck", "voice_id": "hv_Puck"}]
    heard = [{"start": x["start"], "end": x["end"], "speaker": x["speaker"], "text": x["src"]} for x in _lines()]

    def dub():
        es = {"code": "es", "name": "Spanish", "status": st["es"], "step": {"check": "check", "working": "spoken", "ready": "mixed"}[st["es"]], "total": 3, "done": 1}
        if st["es"] == "ready":
            es["video_id"] = "vo_dv"
        langs = [es, {"code": "hi", "name": "Hindi", "status": "ready", "step": "mixed", "video_id": "vo_dh"}] if st["hi"] else [es]
        status = "ready" if any(x["status"] == "ready" for x in langs) and st["es"] != "working" else st["es"]
        return {"id": "db_9", "v": 2, "status": status, "mode": "matched", "title": "asha-tour.mp4", "source_lang": "English", "check": True, "seconds": 4,
                "langs": langs, "people": people, "lines": heard, "keep": st["keep"], "changed": {"es": st["changed"]}, "made": ISO(-30)}

    def route(r):
        req = r.request
        u = urlparse(req.url)
        path, qs = u.path[len("/api/vocal"):], parse_qs(u.query)
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        j = lambda d, s=200: r.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/dubs":
            return j({"dubs": [{"id": "db_9", "status": dub()["status"], "mode": "matched", "title": "asha-tour.mp4", "source_lang": "English", "seconds": 4,
                                "people": 2, "langs": [{"code": x["code"], "name": x["name"], "status": x["status"], "step": x["step"]} for x in dub()["langs"]], "made": ISO(-30)}]})
        if path == "/dub" and req.method == "POST":
            st["started"].append(body)
            return j(dub())
        if path == "/dub/db_9":
            return j(dub())
        if path == "/dub/db_9/lines":
            lang = qs.get("lang", ["es"])[0]
            return j({"lang": lang, "lines": st["lines"], "editable": True, "status": st["es"] if lang == "es" else "ready"})
        if path == "/dub/db_9/ok":
            st["ok"].append(body)
            st["es"] = "ready"
            return j(dub())
        if path.startswith("/dub/db_9/lines/") and path.endswith("/shorten"):
            n = int(path.split("/")[4])
            before = st["lines"][n]["dst"]
            st["lines"][n] = {**st["lines"][n], "dst": "Nunca colores.", "too_long": False, "fit": 92, "edited": True}
            st["changed"] = 1
            return j({"line": st["lines"][n], "before": before})
        if path.startswith("/dub/db_9/lines/") and req.method == "PUT":
            n = int(path.split("/")[4])
            st["saved"].append(body)
            if "text" in body:
                st["lines"][n] = {**st["lines"][n], "dst": body["text"], "edited": True}
            return j({**st["lines"][n]})
        if path == "/dub/db_9/remake":
            st["remake"].append(body)
            st["changed"] = 0
            return j(dub())
        if path == "/dub/db_9/keep":
            st["keep"] = body["words"]
            return j(dub())
        if path == "/dub/db_9/speakers":
            st["speakers"].append(body)
            return j(dub())
        if path in ("/dub/db_9/poster", "/dub/db_9/source", "/dub/db_9/speaker"):
            return r.fulfill(status=404, body="")
        if path == "/dub/db_9/export":
            st["export"].append({k: v[0] for k, v in qs.items()})
            return r.fulfill(content_type="application/zip", body=b"PK\x05\x06" + b"\x00" * 18,
                             headers={"content-disposition": 'attachment; filename="asha-tour - subtitles.zip"'})
        if path == "/upload" or path.endswith("/files"):
            return j({"file_id": "f_dub1"})
        return r.fallback()
    pg.route("**/api/vocal/**", route)


NO_SIDEWAYS = "() => document.documentElement.scrollWidth <= innerWidth + 1 && document.querySelector('#hvRoot').scrollWidth <= document.querySelector('#hvRoot').clientWidth + 1"


def test_a_dub_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("HOOLA_SHOTS")
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "settings": [], "addlang": [],
              "es": "check", "hi": False, "lines": _lines(), "changed": 0, "keep": ["Asha Sweets"], "started": [], "ok": [], "saved": [],
              "remake": [], "speakers": [], "export": []}
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme, accept_downloads=True)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
        pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
        install(pg, st)
        dubs(pg, st)
        open_vocal(pg, base)
        page_to(pg, "dub", width < 600)
        # 1. the library: a card per dub, its languages with where each one is
        pg.wait_for_selector("#hvView .hv-dubc")
        card = pg.locator("#hvView .hv-dubc").first
        assert "asha-tour" in card.text_content() and "Spanish" in card.text_content() and "Read the lines" in card.text_content()
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/dub-{scheme}-{width}-1-library.png")
        # 2. a new dub: her video, the languages, her words to keep, the OK switch
        with pg.expect_file_chooser() as fc:
            pg.locator("#hvView [data-a='pickfile'][data-k='dub']").first.click()
        fc.value.set_files({"name": "launch.mp4", "mimeType": "video/mp4", "buffer": b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64})
        pg.wait_for_selector("#hvView .hv-dubnew")
        assert pg.locator("#hvView [data-a='dubsw'][data-k='check']").get_attribute("aria-checked") == "true"
        pg.locator("#hvDubW").fill("Kaju Katli")
        pg.locator("#hvDubW").press("Enter")
        pg.wait_for_function("() => document.querySelector('#hvView .hv-words2').textContent.includes('Kaju Katli')")
        pg.locator("#hvView [data-a='picklang'][data-k='dubadd']").click()
        pg.locator(".hmenu .msearch input").fill("spanish")
        pg.locator(".hmenu .mi:visible", has_text="Spanish").first.click()
        pg.wait_for_function("() => document.querySelector('#hvView .hv-tot2').textContent.includes('Spanish')")
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/dub-{scheme}-{width}-2-new.png")
        pg.wait_for_function("() => !document.querySelector('#hvView [data-qbtn=dub]').disabled", timeout=10000)
        pg.locator("#hvView [data-qbtn='dub']").click()
        # 3. being made: the steps, and the lines waiting for her OK
        pg.wait_for_selector("#hvView .hv-dubmk")
        assert st["started"][0]["keep"] == ["Kaju Katli"] and st["started"][0]["check"] is True and st["started"][0]["langs"] == ["es"]
        assert "Waiting for you" in pg.locator("#hvView").text_content() and "Priya" in pg.locator("#hvView").text_content()
        if shots:
            pg.screenshot(path=f"{shots}/dub-{scheme}-{width}-3-making.png")
        pg.locator("#hvView [data-a='dubread'][data-val='es']").click()
        # 4. the lines: fit, a kept word missing, shorten it, Undo, then OK
        pg.wait_for_selector("#hvView [data-a='dubsel'][data-n='1']")
        txt = pg.locator("#hvView").text_content()
        assert "168% of their time" in txt and "too long" in txt and "“Asha Sweets” is missing" in txt and "Nothing is spoken yet" in txt
        pg.locator("#hvView [data-a='dubsel'][data-n='1']").click()
        pg.locator("#hvView [data-a='dubshort'][data-n='1']").click()
        pg.wait_for_selector("#hvView [data-a='dubundo']")
        assert "Nunca colores." in pg.locator("#hvView .hv-dline.on").text_content()
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/dub-{scheme}-{width}-4-lines.png")
        pg.locator("#hvView [data-a='dubundo']").click()
        pg.wait_for_function("() => document.querySelector('#hvView').textContent.includes('Jamás, es nuestra promesa')")
        assert st["saved"][-1]["text"].startswith("Nunca colores. Jamás")
        pg.locator("#hvView [data-a='dubok'][data-val='es']").click()
        # 5. a finished dub: the video, the tracks, Make the changes when a line changed
        pg.wait_for_function("() => !!document.querySelector('#hvView #hvDubMedia') && document.querySelector('#hvView').textContent.includes('Playing in Spanish')")
        assert st["ok"] == [{"lang": "es"}]
        ta_btn = pg.locator("#hvView [data-a='dubsel'][data-n='2']")
        ta_btn.click()
        ta = pg.locator("#hvView textarea[data-dubline='2']")
        ta.fill("Pida a Asha Sweets.")
        ta.dispatch_event("change")
        pg.wait_for_function("() => !document.querySelector('#hvView [data-a=dubremake]')?.disabled", timeout=10000)
        assert "1 line changed" in pg.locator("#hvView .hv-dubfoot").text_content()
        if shots:
            pg.screenshot(path=f"{shots}/dub-{scheme}-{width}-5-work.png")
        pg.locator("#hvView [data-a='dubremake']").click()
        pg.wait_for_function("() => document.querySelector('#hvView .hv-dubfoot')?.textContent.includes('No changes yet')")
        assert st["remake"] == [{"lang": "es"}]
        # 6. the dialogs: voices, words to keep, download
        pg.locator("#hvRoot [data-a='sdopen'][data-k='dvoices']").click()
        pg.wait_for_selector("#hvSd .hv-vp")
        names = pg.locator("#hvSd input").evaluate_all("es => es.map(e => e.value)")
        assert "Priya" in names and "Rahul" in names, names
        if shots:
            pg.screenshot(path=f"{shots}/dub-{scheme}-{width}-6-voices.png")
        pg.keyboard.press("Escape")
        pg.locator("#hvView [data-a='sdopen'][data-k='dkeep']").click()
        pg.wait_for_selector("#hvSd .hv-vp")
        assert "Asha Sweets" in pg.locator("#hvSd").text_content() + " ".join(pg.locator("#hvSd input").evaluate_all("es => es.map(e => e.value)"))
        pg.keyboard.press("Escape")
        pg.locator("#hvRoot [data-a='sdopen'][data-k='ddl']").click()
        pg.wait_for_selector("#hvSd .hv-vp")
        pg.locator("#hvSd [data-a='dldwhat'][data-val='subs']").click()
        if shots:
            pg.screenshot(path=f"{shots}/dub-{scheme}-{width}-7-download.png")
        with pg.expect_download() as dl:
            pg.locator("#hvSd [data-a='dldgo']").click()
        assert dl.value.suggested_filename.endswith(".zip") or dl.value.suggested_filename.endswith(".srt")
        assert st["export"] and st["export"][-1]["what"] == "subs" and st["export"][-1]["langs"] == "es"
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        assert not errs, errs
        ctx.close()
