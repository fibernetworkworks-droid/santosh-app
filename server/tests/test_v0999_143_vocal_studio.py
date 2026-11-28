"""v0.999.143 STUDIO, PREMIUM - the server half: import preview (parts, front matter unticked, author, cover), the
reading's people across the book (merge / keep apart / small parts to the narrator), the sound check, and the audiobook
(spoken AI line, even loudness, cover + author, one MP3 per chapter). No network: Gemini is faked; ffmpeg is real."""
import io
import json
import subprocess
import zipfile

import pytest

from app.vocal import book as BK
from app.vocal import service as V
from tests.test_v0999_96_vocal_redesign_server import client, needs_ff, run, vg  # noqa: F401

BOOK = """Contents

Chapter 1 .......... 1
Chapter 2 .......... 9

Chapter 1: The Island

The island was small enough to walk around before breakfast. Elias kept the lamp.

"Keep the light burning," said Elias.

"Whatever happens?" asked Ada.

"Whatever happens," said Elias.

Chapter 2: The Storm

The storm came at night and the boats stayed in.

"Not tonight, little one," said Papa.

"Count the steps," said Father.
"""

def _png():
    import struct
    import zlib

    def chunk(t, b):
        return struct.pack(">I", len(b)) + t + b + struct.pack(">I", zlib.crc32(t + b) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x1f\x3a\x5f" * 8 for _ in range(8))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


PNG = _png()


def test_split_and_front_matter():
    parts = BK.split(BOOK)
    titles = [p["title"] for p in parts]
    assert any("Island" in t for t in titles) and any("Storm" in t for t in titles)
    assert BK.front_matter("Contents", "Chapter 1 .... 1\nChapter 2 .... 9")
    assert not BK.front_matter("Chapter 1: The Island", "The island was small enough to walk around before breakfast. " * 5)


def test_preview_saves_nothing_and_unticks_front_matter(vg):
    pv = BK.preview("t1", text=BOOK, title="The Lighthouse Keeper")
    assert pv["title"] == "The Lighthouse Keeper" and V._load("t1")["projects"] == []
    story = [p for p in pv["parts"] if not p["skip"]]
    assert len(story) >= 2 and all(p["seconds"] > 0 and p["credits"] >= 0 for p in story)
    assert pv["words"] == sum(p["words"] for p in story)


def test_import_keeps_only_the_ticked_parts_with_author_and_cover(vg, client):
    pv = client.post("/api/vocal/project/import/preview", json={"text": BOOK, "title": "LH"}).json()
    keep = [p["n"] for p in pv["parts"] if "Storm" in p["title"]]
    p = client.post("/api/vocal/project/import", json={"text": BOOK, "title": "LH", "keep": keep, "author": "Asha Rao"}).json()
    assert [c["title"] for c in p["chapters"]] == [pv["parts"][keep[0]]["title"]] and p["author"] == "Asha Rao"
    assert client.post("/api/vocal/project/import", json={"text": BOOK, "keep": []}).status_code == 422
    ext = BK.keep_cover("t1", p["id"], PNG)
    assert ext == "png"
    with V._LOCK:
        d = V._load("t1")
        V._project(d, p["id"])["cover"] = ext
        V._store("t1", d)
    r = client.get(f"/api/vocal/project/cover?id={p['id']}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    with pytest.raises(V.VocalError):
        BK.keep_cover("t1", p["id"], b"not a picture")
    V.project_remove("t1", p["id"])
    assert not list((V._home("t1") / "covers").glob(f"{p['id']}.*"))


def _with_people(pid):
    """The people as project_cast would set them (Gemini is not called here)."""
    with V._LOCK:
        d = V._load("t1")
        p = V._project(d, pid)
        p["chapters"][0]["paragraphs"] = [
            {"who": "Narrator", "text": "The island was small."},
            {"who": "Elias", "text": "Keep the light burning."},
            {"who": "Ada", "text": "Whatever happens?"},
            {"who": "Elias", "text": "Whatever happens."},
            {"who": "Elias", "text": "Go to bed."}]
        p["chapters"][1]["paragraphs"] = [
            {"who": "Narrator", "text": "The storm came."},
            {"who": "Papa", "text": "Not tonight, little one."},
            {"who": "Father", "text": "Count the steps."}]
        V._store("t1", d)


def test_people_merge_apart_and_small_parts(vg, client):
    p = V.project_save("t1", title="LH", voice="hv_Kore", lang="en",
                       chapters=[{"title": "One", "text": "a\n\nb"}, {"title": "Two", "text": "c\n\nd"}])
    _with_people(p["id"])
    pe = client.get(f"/api/vocal/project/people?id={p['id']}").json()
    names = {x["name"]: x for x in pe["people"]}
    assert names["Elias"]["lines"] == 3 and names["Narrator"]["chapters"] == [0, 1]
    sug = pe["suggestions"]
    assert any({s["a"], s["b"]} == {"Papa", "Father"} for s in sug)
    client.post("/api/vocal/project/people/apart", json={"id": p["id"], "a": "Papa", "b": "Father"})
    assert not client.get(f"/api/vocal/project/people?id={p['id']}").json()["suggestions"]
    client.post("/api/vocal/project/people/merge", json={"id": p["id"], "keep": "Father", "drop": "Papa"})
    names = {x["name"]: x for x in client.get(f"/api/vocal/project/people?id={p['id']}").json()["people"]}
    assert "Papa" not in names and names["Father"]["lines"] == 2
    client.put("/api/vocal/project/people", json={"id": p["id"], "small": True, "voices": {"Elias": "hv_Puck"}})
    pe = client.get(f"/api/vocal/project/people?id={p['id']}").json()
    names = {x["name"]: x for x in pe["people"]}
    assert names["Ada"]["small"] and names["Father"]["small"] and not names["Elias"]["small"]
    assert names["Elias"]["voice"] == "hv_Puck"
    # a small part is read in the narrator's voice
    d = V._load("t1")
    pp = V._project(d, p["id"])
    k_ada = V._para_key(d, pp, {"who": "Ada", "text": "Whatever happens?"})
    k_nar = V._para_key(d, pp, {"who": "Narrator", "text": "Whatever happens?"})
    assert k_ada[0] == k_nar[0]


@needs_ff
def test_sound_check_and_the_audiobook(vg, client):
    p = V.project_save("t1", title="LH", voice="hv_Kore", lang="en", author="Asha Rao",
                       chapters=[{"title": "One", "text": "First paragraph.\n\nSecond one."}, {"title": "Two", "text": "Third."}])
    ck = client.get(f"/api/vocal/project/check?id={p['id']}").json()
    assert not ck["ready"] and ck["missing"] == [0, 1] and ck["checks"][0]["ok"] is False
    assert client.post("/api/vocal/project/export", json={"id": p["id"], "format": "m4b"}).status_code == 422
    run(V.chapter_make("t1", p["id"], 0))
    run(V.chapter_make("t1", p["id"], 1))
    ck = client.get(f"/api/vocal/project/check?id={p['id']}").json()
    ids = {c["id"]: c for c in ck["checks"]}
    assert ck["ready"] and ids["made"]["ok"] and "LUFS" in ids["loud"]["value"] and "dB" in ids["peak"]["value"]
    assert ids["voices"]["ok"] and ids["gap"]["ok"]
    assert V._load("t1")["projects"][0]["loud"]
    # one paragraph's kept recording
    assert client.get(f"/api/vocal/project/para?id={p['id']}&n=0&k=1").status_code == 200
    assert client.get(f"/api/vocal/project/para?id={p['id']}&n=0&k=9").status_code == 404
    BK.keep_cover("t1", p["id"], PNG)
    with V._LOCK:
        d = V._load("t1")
        V._project(d, p["id"])["cover"] = "png"
        V._store("t1", d)
    row = client.post("/api/vocal/project/export", json={"id": p["id"], "format": "m4b", "even": True, "intro": True}).json()
    f, _ = V.audio_file("t1", row["id"])
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_chapters", "-show_format", "-show_streams", "-of", "json", str(f)],
                                   capture_output=True, timeout=60).stdout)
    titles = [c["tags"]["title"] for c in pr["chapters"]]
    assert titles == ["Made with AI voices", "One", "Two"]
    tags = {k.lower(): v for k, v in pr["format"]["tags"].items()}
    assert tags.get("artist") == "Asha Rao" and "Made by AI" in tags.get("comment", "")
    assert any(s.get("codec_type") == "video" for s in pr["streams"])         # the cover inside
    z = client.post("/api/vocal/project/export", json={"id": p["id"], "format": "mp3zip", "intro": True}).json()
    f, _ = V.audio_file("t1", z["id"])
    names = zipfile.ZipFile(io.BytesIO(f.read_bytes())).namelist()
    assert names == ["00 - Made with AI voices.mp3", "01 - One.mp3", "02 - Two.mp3"]
    # the old export call (no intro asked) stays as it was
    w = client.post("/api/vocal/project/export", json={"id": p["id"], "format": "wav"}).json()
    assert w["ext"] == "wav"


def test_pace_and_gap_are_kept(vg):
    p = V.project_save("t1", title="X", voice="hv_Kore", chapters=[{"title": "A", "text": "Hello there."}], pace=1.1, gap=2.5)
    assert p["pace"] == 1.1 and p["gap"] == 2.5
    p = V.project_save("t1", pid=p["id"], title="X", voice="hv_Kore", chapters=[{"title": "A", "text": "Hello there."}], gap=99)
    assert p["gap"] == 5.0


# ---------------------------------------------------------------- the console page, in a real browser
import re  # noqa: E402
from pathlib import Path  # noqa: E402

from tests.test_v0312_arena_screen import arena_server  # noqa: F401,E402
from tests.test_v0999_96_vocal_redesign_console import CONFIG, ISO, install, open_vocal, overview, page_to  # noqa: E402
from tests.test_v121_site import site_env  # noqa: F401,E402

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (CON / "vocal.js").read_text()
CSS = (CON / "vocal2.css").read_text()


def test_the_files_carry_the_design():
    for k in ("Turn any book into an audiobook.", "Drop a book here", "Your readings", "Check the chapters", "will be read", "Create the reading",
              "Nothing is spent now.", "Who reads whom", "Make the audiobook", "The narrator reads small parts", "Make them one", "Keep apart",
              "Sound check", "Measured on Hoola’s server, free", "Download the audiobook", "Putting the book together is free", "Changed since it was read",
              "Who says it", "Quiet between chapters", "The whole book", "/project/import/preview", "/project/people", "/project/para", "people/merge"):
        assert k in JS, k
    for k in (".hv-libhero", ".hv-sdrop", ".hv-shelf", ".hv-cover", ".hv-parts", ".hv-tick", ".hv-page", ".hv-pg.on", ".hv-pdot", ".hv-strip", ".hv-person", ".hv-checks"):
        assert k in CSS, k
    assert not re.search(r"#[0-9A-Fa-f]{3,6}\b", CSS)


def _book():
    seg = lambda who, text, v: {"who": who, "text": text, "seconds": 2, "voice": v}  # noqa: E731
    a1, a2 = "The island was small enough to walk around before breakfast.", "“Keep the light burning,” said Elias."
    b1, b2 = "The wind came first, then the rain.", "“Is anyone up there?” asked Ada."
    return {"id": "vp_1", "title": "The Lighthouse Keeper", "author": "Asha Rao", "lang": "en", "voice": "v_meera", "made": ISO(-7200),
            "cast": {"Narrator": "v_meera", "Elias": "v_thandi", "Ada": "v_lucia"}, "pace": 0.95, "gap": 2,
            "chapters": [
                {"title": "The Island", "text": f"{a1}\n\n{a2}", "audio": "vo_aaaaaaaaaaaa", "seconds": 62, "made": ISO(-172800),
                 "paragraphs": [{"who": "Narrator", "text": a1}, {"who": "Elias", "text": a2}],
                 "segments": [seg("Narrator", a1, "v_meera"), seg("Elias", a2, "v_thandi")]},
                {"title": "The Storm", "text": f"{b1}\n\n{b2}", "audio": "vo_bbbbbbbbbbbb", "seconds": 40,
                 "paragraphs": [{"who": "Narrator", "text": b1}, {"who": "Ada", "text": b2}],
                 "segments": [seg("Narrator", b1, "v_meera"), seg("Ada", "“Is anyone there?” asked Ada.", "v_lucia")]},
                {"title": "The Rescue", "text": "Morning came, grey and quiet."}]}


PREVIEW = {"title": "The Lighthouse Keeper", "author": "Asha Rao", "lang": "en", "cover": "", "max_chapters": 60, "words": 900, "chars": 5000, "seconds": 360, "credits": 30,
           "parts": [{"n": 0, "title": "Contents", "first": "Chapter 1 .... 1", "words": 12, "chars": 60, "skip": True, "why": "Not the story", "seconds": 5, "credits": 0},
                     {"n": 1, "title": "Chapter 1: The Island", "first": "The island was small.", "words": 400, "chars": 2200, "skip": False, "why": "", "seconds": 160, "credits": 12},
                     {"n": 2, "title": "Chapter 2: The Storm", "first": "The wind came first.", "words": 300, "chars": 1600, "skip": False, "why": "", "seconds": 120, "credits": 10},
                     {"n": 3, "title": "Chapter 3: The Rescue", "first": "Morning came.", "words": 200, "chars": 1200, "skip": False, "why": "", "seconds": 80, "credits": 8}]}

PEOPLE = {"found": 2, "total": 3, "small": False, "small_lines": 3,
          "suggestions": [{"a": "Papa", "b": "Father", "why": "“Papa” and “Father” may be the same person."}],
          "people": [{"name": "Narrator", "lines": 12, "chapters": [0, 1], "quote": "The island was small.", "voice": "v_meera", "small": False},
                     {"name": "Elias", "lines": 8, "chapters": [0], "quote": "“Keep the light burning.”", "voice": "v_thandi", "small": False},
                     {"name": "Papa", "lines": 2, "chapters": [1], "quote": "“Not tonight.”", "voice": "", "small": False},
                     {"name": "Father", "lines": 1, "chapters": [1], "quote": "“Count the steps.”", "voice": "", "small": False}]}


def _page(browser, key, w, h, st):
    ctx = browser.new_context(viewport={"width": w, "height": h}, accept_downloads=True)
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:300]))
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)

    def ov(route):
        o = overview()
        o["projects"] = st["projects"]
        o["history"] = st["hist"] + o["history"]
        route.fulfill(content_type="application/json", body=json.dumps(o))

    def proj(route):
        req = route.request
        path = req.url.split("/api/vocal", 1)[1].split("?")[0]
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        st["proj"].append((req.method, path, body))
        j = lambda d, s=200: route.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/project/import/preview":
            return j(PREVIEW)
        if path == "/project/import":
            p = {**_book(), "id": "vp_2", "title": body.get("title") or "X", "author": body.get("author") or ""}
            st["projects"].insert(0, p)
            return j(p)
        if path == "/project/people/merge":
            st["people"]["people"] = [x for x in st["people"]["people"] if x["name"] != body["drop"]]
            st["people"]["suggestions"] = []
            return j(st["people"])
        if path == "/project/people" and req.method == "PUT":
            if "small" in body:
                st["people"]["small"] = body["small"]
                for x in st["people"]["people"]:
                    x["small"] = body["small"] and x["name"] != "Narrator" and x["lines"] < 3
            return j(st["people"])
        if path == "/project/people":
            return j(st["people"])
        if path == "/project/check":
            p = st["projects"][0]
            missing = [i for i, c in enumerate(p["chapters"]) if not c.get("audio")]
            return j({"ready": not missing, "missing": missing, "chapters": len(p["chapters"]), "made": len(p["chapters"]) - len(missing), "seconds": 102, "gap": 2, "ffmpeg": True,
                      "checks": [{"id": "made", "name": "Every chapter made", "ok": not missing, "note": "Chapter 3 is not made yet." if missing else "All chapters are made.", "value": "2 of 3"},
                                 {"id": "loud", "name": "Loudness", "ok": True, "note": "Even across chapters, right for listening apps.", "value": "-19.2 LUFS"}]})
        if path == "/project/export":
            st["export"].append(body)
            row = {"id": "vo_book", "kind": "book", "title": "The Lighthouse Keeper", "ext": "m4b", "seconds": 102, "made": ISO()}
            st["hist"].insert(0, row)
            return j(row)
        if path == "/project/para" and req.method == "PUT":
            p = st["projects"][0]
            p["chapters"][int(body["n"])]["paragraphs"][int(body["k"])]["who"] = body["who"]
            return j(p)
        if path == "/project/para":
            return route.fulfill(body=b"RIFF\x24\x00\x00\x00WAVEfmt ", content_type="audio/wav")
        if path == "/project":
            p = st["projects"][0]
            p.update({k: v for k, v in body.items() if k in ("title", "pace", "gap", "author")})
            for c, nc in zip(p["chapters"], body["chapters"]):
                c.update(nc)
            return j(p)
        return j({"detail": "not mocked"}, 404)
    pg.route("**/api/vocal/overview", ov)
    pg.route(re.compile(r".*/api/vocal/project(/.*)?(\?.*)?$"), proj)
    return ctx, pg, errs


def _shot(pg, name):
    import os
    if os.environ.get("HOOLA_SHOTS"):
        pg.wait_for_timeout(350)
        pg.screenshot(path=f"{os.environ['HOOLA_SHOTS']}/studio-{name}.png")


def _st():
    return {"calls": [], "hist": [], "proj": [], "export": [], "projects": [_book()], "people": json.loads(json.dumps(PEOPLE)), "rows": [], "tts": [], "sent": [],
            "items": [], "change": [], "uploads": 0, "settings": [], "addlang": [], "join": [], "rules": []}


def test_the_studio_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    st = _st()
    ctx, pg, errs = _page(browser, key, 1440, 900, st)
    open_vocal(pg, base)
    page_to(pg, "studio")
    view = pg.locator("#hvView")
    assert "Turn any book into an audiobook." in view.text_content() and pg.locator("#hvRoot .hv-bookc").count() == 1
    card = pg.locator("#hvRoot .hv-bookc").first.text_content()
    assert "The Lighthouse Keeper" in card and "2 of 3 made · continue" in card and "3 voices" in card
    _shot(pg, "library")

    # import: the chapters are looked at first, the part that is not the story left out
    pg.locator("#hvTopR [data-a='impopen']").click()
    pg.locator("#hvRoot .hv-seg [data-val='text']").click()
    pg.locator("#hvImT").fill("Contents\n\nChapter 1: The Island\n\nThe island was small.")
    pg.locator("#hvRoot form[data-f='import'] button:not([type=button])").click()
    pg.wait_for_selector("#hvRoot .hv-parts")
    assert pg.locator("#hvRoot .hv-part").count() == 4 and pg.locator("#hvRoot .hv-part.off").count() == 1
    assert "3 of 4 will be read" in view.text_content() and "Not the story" in view.text_content()
    assert "30 credits" in pg.locator("#hvRoot .hv-tot").text_content()
    pg.locator("#hvRoot [data-a='imptick'][data-n='3']").click()
    assert "2 of 4 will be read" in view.text_content() and pg.locator("#hvRoot [data-a='imptick'][data-n='3']").get_attribute("aria-checked") == "false"
    pg.locator("#hvImA").fill("A. Rao")
    _shot(pg, "import")
    pg.locator("#hvRoot [data-a='impmake']").click()
    pg.wait_for_selector("#hvRoot .hv-reading")
    imp = [b for m, p, b in st["proj"] if p == "/project/import"][-1]
    assert imp["keep"] == [1, 2] and imp["author"] == "A. Rao" and imp["text"].startswith("Contents")
    st["projects"][:] = [x for x in st["projects"] if x["id"] == "vp_1"]      # the mock works on one reading from here
    pg.locator("#hvRoot .hv-chaps [data-a='go'][data-p='studio']").click()

    # the reading: the chapters with their states, a page of the book with each paragraph's state
    pg.locator("#hvRoot .hv-bookc", has_text="The Lighthouse Keeper").last.click()
    pg.wait_for_selector("#hvRoot .hv-reading")
    chs = pg.locator("#hvRoot .hv-chap")
    assert chs.count() == 3 and "1:02" in chs.nth(0).text_content() and "Changed" in chs.nth(1).text_content() and "Not made" in chs.nth(2).text_content()
    assert pg.locator("#hvRoot .hv-strip span.made").count() == 1 and pg.locator("#hvRoot .hv-strip span.changed").count() == 1
    assert "Saved" in pg.locator("#hvTopR").text_content()
    chs.nth(1).click()
    assert pg.locator("#hvRoot .hv-pg").count() == 2 and pg.locator("#hvRoot .hv-pdot.changed").count() == 1
    assert "1 paragraph changed" in pg.locator("#hvRoot .hv-thisch").text_content()
    assert pg.locator("#hvRoot .hv-q").count() == 1
    pg.locator("#hvRoot .hv-pg").nth(1).click()
    assert "Changed since it was read" in pg.locator("#hvRoot .hv-pgbar").text_content()
    _shot(pg, "reading")
    pg.locator("#hvRoot .hv-pg").nth(0).click()
    pg.locator("#hvRoot [data-a='paraplay']").click()
    pg.wait_for_function("() => document.querySelector('#hvNow')?.textContent.includes('paragraph 1')")
    pg.locator("#hvRoot [data-a='parawho']").click()
    pg.locator(".hm-item, [role=menuitem], [role=menuitemradio]", has_text="Elias").first.click()
    pg.wait_for_function("() => document.querySelectorAll('#hvRoot .hv-q').length === 2")
    who = [b for m, p, b in st["proj"] if p == "/project/para" and m == "PUT"][-1]
    assert who == {"id": "vp_1", "n": 1, "k": 0, "who": "Elias"}

    # changing the words: the page becomes the editor, the top bar says it is not saved
    pg.locator("#hvRoot .hv-pgtools [data-a='edit']").click()
    pg.locator("#hvChX").evaluate("t => { t.focus(); t.selectionStart = t.selectionEnd = t.value.length; }")
    pg.keyboard.type(" More.")
    assert "Not saved yet" in pg.locator("#hvTopR").text_content()
    pg.locator("#hvTopR [data-a='saveproj']").click()
    pg.wait_for_function("() => document.querySelector('#hvTopR').textContent.includes('Saved')")

    # who reads whom
    pg.locator("#hvTopR [data-a='sdopen'][data-k='people']").click()
    pg.wait_for_selector("#hvSd .hv-person")
    sd = pg.locator("#hvSd")
    assert sd.locator(".hv-person").count() == 4 and "may be the same person" in sd.text_content() and "1 chapter has not been looked at yet" in sd.text_content()
    _shot(pg, "people")
    sd.locator("[data-a='pplmerge']").click()
    pg.wait_for_function("() => document.querySelectorAll('#hvSd .hv-person').length === 3")
    sd.locator("[data-a='pplsmall']").click()
    pg.wait_for_function("() => document.querySelector('#hvSd [data-a=pplsmall]').getAttribute('aria-checked') === 'true'")
    assert "read by the narrator" in sd.text_content()
    pg.keyboard.press("Escape")
    assert pg.locator("#hvSd").count() == 0
    assert pg.evaluate("() => document.activeElement?.dataset?.a") == "sdopen"

    # make the audiobook: not ready = the button says why; the whole book made = the file
    pg.locator("#hvTopR [data-a='sdopen'][data-k='book']").click()
    pg.wait_for_selector("#hvSd .hv-checks")
    dl = pg.locator("#hvSd [data-a='abgo']")
    assert dl.is_disabled() and "not made yet" in pg.locator("#hvSd").text_content() and pg.locator("#hvSd [data-a='abmake']").count() == 1
    _shot(pg, "book-notready")
    pg.keyboard.press("Escape")
    st["projects"][0]["chapters"][2].update(audio="vo_c3", seconds=20, segments=[{"who": "Narrator", "text": "Morning came, grey and quiet.", "seconds": 2}])
    pg.evaluate("() => document.querySelector('#hvRoot .hv-chaps [data-a=go][data-p=studio]').click()")
    pg.locator("#hvRoot .hv-bookc", has_text="The Lighthouse Keeper").last.click()
    pg.wait_for_selector("#hvRoot .hv-reading")
    pg.locator("#hvTopR [data-a='sdopen'][data-k='book']").click()
    pg.wait_for_selector("#hvSd .hv-checks")
    pg.locator("#hvSd [data-a='abfmt'][data-val='mp3zip']").click()
    pg.locator("#hvSd [data-a='abfmt'][data-val='m4b']").click()
    assert not pg.locator("#hvSd [data-a='abgo']").is_disabled()
    _shot(pg, "book")
    with pg.expect_download() as d:
        pg.locator("#hvSd [data-a='abgo']").click()
    assert d.value.suggested_filename.endswith(".m4b")
    assert st["export"][-1] == {"id": "vp_1", "format": "m4b", "even": True, "intro": True}
    assert not errs, errs
    ctx.close()


def test_the_studio_fits_a_phone(arena_server):  # noqa: F811
    base, browser, key = arena_server
    st = _st()
    ctx, pg, errs = _page(browser, key, 390, 844, st)
    open_vocal(pg, base)
    page_to(pg, "studio", narrow=True)
    wide = "() => document.querySelector('#hvView').scrollWidth - document.querySelector('#hvView').clientWidth"
    assert pg.evaluate(wide) <= 1
    _shot(pg, "phone-library")
    pg.locator("#hvRoot .hv-bookc").first.click()
    pg.wait_for_selector("#hvRoot .hv-reading")
    assert pg.evaluate(wide) <= 1
    _shot(pg, "phone-reading")
    pg.locator("#hvTopR [data-a='sdopen'][data-k='people']").click()
    pg.wait_for_selector("#hvSd .hv-person")
    over = pg.evaluate("() => { const b = document.querySelector('#hvSd .hv-vp').getBoundingClientRect(); return b.left < -1 || b.right > innerWidth + 1; }")
    assert not over
    _shot(pg, "phone-people")
    assert not errs, errs
    ctx.close()
