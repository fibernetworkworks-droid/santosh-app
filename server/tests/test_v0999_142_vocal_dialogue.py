"""v0.999.143 DIALOGUE, PREMIUM - the server half: line times, a pause after a line, a line that cuts in, making one line
again, each voice on its own track, subtitles, and scripts from a document that name their page and check their
figures. No network: the engines are faked at their seams (the fixtures of the v0.999.96 suite)."""
import io
import wave
import zipfile

import pytest

from app.vocal import gvoice as GV
from app.vocal import service as V
from app.vocal import talk as TK
from tests.test_v0999_96_vocal_redesign_server import client, eleven, run, tone, vg  # noqa: F401

CAST = {"Kabir": "hv_Puck", "Meera": "hv_Kore"}
LINES = [{"speaker": "Kabir", "text": "[cheerful] Welcome back to Sweet Talk."},
         {"speaker": "Meera", "text": "Thanks, Kabir. It is our busiest week.", "pause": 1},
         {"speaker": "Kabir", "text": "Four hundred? In one day?", "cut": True},
         {"speaker": "Meera", "text": "In one day."}]


def secs(b):
    with wave.open(io.BytesIO(b)) as w:
        return w.getnframes() / w.getframerate()


def test_join_timed_puts_a_pause_after_a_line_and_overlaps_a_cut_in():
    a, b, c = tone(1.0), tone(1.0), tone(1.0)
    data, t = TK.join_timed([a, b, c], [0.3, 1.3, 0.3], [False, False, True])
    assert t[0] == (0.0, 1.0)
    assert t[1][0] == pytest.approx(1.3, abs=0.01)                     # the usual quiet
    assert t[2][0] < t[1][1] and t[1][1] - t[2][0] == pytest.approx(TK.CUT_S, abs=0.01)   # starts before line 2 ends
    assert secs(data) == pytest.approx(t[2][1], abs=0.01)
    plain, t2 = TK.join_timed([a, b, c], [0.3, 1.3, 0.3], [False, False, False])
    assert t2[2][0] == pytest.approx(t2[1][1] + 1.3, abs=0.01)         # the pause after line 2


def test_line_by_line_talk_keeps_line_times_and_each_line(vg):
    row = run(V.dialogue("t1", LINES, CAST, lang="en"))
    segs = row["segments"]
    assert [s["speaker"] for s in segs] == ["Kabir", "Meera", "Kabir", "Meera"] and row["timing_est"] is False
    assert segs[0]["text"] == "[cheerful] Welcome back to Sweet Talk."               # her words, for subtitles
    assert segs[1]["pause"] == 1 and segs[2]["cut"] is True and segs[0]["cut"] is False
    assert segs[2]["start"] < segs[1]["end"]                                         # it cuts in
    assert segs[3]["start"] - segs[2]["end"] == pytest.approx(V.LINE_GAP_S, abs=0.01)
    files = sorted(TK.parts_dir("t1", row["id"]).glob("*.wav"))
    assert len(files) == 4 and len(vg) == 4


def test_making_one_line_again_speaks_only_that_line(vg, client):
    row = run(V.dialogue("t1", LINES, CAST, lang="en"))
    before = len(vg)
    r = client.post(f"/api/vocal/dialogue/{row['id']}/line", json={"n": 3, "text": "In a single day!"})
    assert r.status_code == 200, r.text
    new = r.json()
    assert len(vg) == before + 1 and vg[-1][4] == "In a single day!"                   # one line spoken, not four
    assert new["take"] == "B" and new["job"] == row["job"] and new["from_take"] == row["id"] and new["remade"] == 3
    assert [s["text"] for s in new["segments"]][:3] == [s["text"] for s in row["segments"]][:3]
    assert new["segments"][3]["text"] == "In a single day!" and "Meera: In a single day!" in new["text"]
    assert any(h["id"] == row["id"] for h in V._load("t1")["history"])               # the old take stays
    assert len(list(TK.parts_dir("t1", new["id"]).glob("*.wav"))) == 4
    other = client.post(f"/api/vocal/dialogue/{row['id']}/line", json={"n": 0, "speaker": "Asha"})
    assert other.status_code == 422 and "does not speak in this talk" in other.json()["detail"]
    swap = client.post(f"/api/vocal/dialogue/{row['id']}/line", json={"n": 0, "speaker": "Meera"}).json()
    assert swap["segments"][0]["speaker"] == "Meera" and vg[-1][1] == "Kore"
    assert client.post(f"/api/vocal/dialogue/{row['id']}/line", json={"n": 9}).status_code == 422


def test_each_voice_on_its_own_track_and_subtitles(vg, client):
    row = run(V.dialogue("t1", LINES, CAST, lang="en"))
    r = client.get(f"/api/vocal/dialogue/{row['id']}/voices")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(r.content))
    wavs = [n for n in z.namelist() if n.endswith(".wav")]
    assert wavs == ["01 Kabir.wav", "02 Meera.wav"]
    lens = [secs(z.read(n)) for n in wavs]
    assert lens[0] == pytest.approx(lens[1]) and lens[0] >= row["segments"][-1]["end"]   # the same length, lined up
    assert b"Made with AI" in z.read(wavs[0]) or b"AI" in z.read(wavs[0])[-200:]
    srt = client.get(f"/api/vocal/dialogue/{row['id']}/subtitles").text
    assert "1\n00:00:00,000 --> " in srt and "Kabir: Welcome back to Sweet Talk." in srt and "[cheerful]" not in srt
    vtt = client.get(f"/api/vocal/dialogue/{row['id']}/subtitles?fmt=vtt")
    assert vtt.text.startswith("WEBVTT") and "NOTE" not in vtt.text and vtt.headers["content-disposition"].endswith('.vtt"')


def test_a_natural_take_writes_pauses_in_and_says_what_it_cannot_split(vg, monkeypatch, client):
    asked = []
    monkeypatch.setattr(GV, "_multi_call", lambda contents, speakers: asked.append(contents) or b"\x01\x00" * 48000)
    row = run(V.dialogue("t1", LINES, CAST, mode="natural", lang="en"))
    body = asked[0].split("\n", 1)[1]
    assert "Thanks, Kabir. It is our busiest week —" in body                          # cut off: the next line cuts in
    assert row["timing_est"] is True and len(row["segments"]) == 4
    assert row["segments"][-1]["end"] == pytest.approx(row["seconds"], abs=0.1)
    assert not TK.parts_dir("t1", row["id"]).exists()
    r = client.get(f"/api/vocal/dialogue/{row['id']}/voices")
    assert r.status_code == 422 and "natural take is one recording" in r.json()["detail"]
    assert client.post(f"/api/vocal/dialogue/{row['id']}/line", json={"n": 0}).status_code == 422
    assert "NOTE The times are shared out by line length" in client.get(f"/api/vocal/dialogue/{row['id']}/subtitles?fmt=vtt").text
    rows = TK.natural_text([("A", "Hello there."), ("B", "Hi."), ("A", "Bye.")], [(1.0, False), (0, False), (0, False)])
    assert rows[0][1] == "Hello there. …"


def test_reactions_are_their_own_pieces_and_removing_a_talk_removes_its_lines(vg):
    lines = [{"speaker": "Asha", "text": "Welcome to the show, today we talk about bread and the people who bake it.", "pause": 0.5},
             {"speaker": "Kofi", "text": "Thank you, it is good to be here."},
             {"speaker": "Asha", "text": "Tell us how you started baking at home during the long rainy season."}]
    row = run(V.dialogue("t1", lines, {"Asha": "hv_Kore", "Kofi": "hv_Puck"}, reactions=True))
    segs = row["segments"]
    assert any(s.get("reaction") for s in segs) and [s for s in segs if not s.get("reaction")][0]["pause"] == 0.5
    V.history_remove("t1", row["id"])
    assert not TK.parts_dir("t1", row["id"]).exists()


def test_a_script_from_a_document_names_its_page_and_checks_figures(vg, monkeypatch, client):
    prompts = []

    def fake(prompt):
        prompts.append(prompt)
        return {"title": "Diwali menu", "lines": [
            {"part": "Opening", "speaker": "Kabir", "text": "Welcome to Sweet Talk.", "from": ""},
            {"speaker": "Meera", "text": "Every box is 20% off, and the offer ends Sunday.", "from": "page 2"},
            {"speaker": "Kabir", "text": "We packed 900 boxes.", "from": "page 9"},
            {"part": "Close", "speaker": "Meera", "text": "Thanks for listening.", "from": ""}]}
    monkeypatch.setattr(V, "_gem_json", fake)
    src = TK.paged(["Asha Sweets menu. Kaju katli and laddoo. " * 10, "This week every box is 20% off until Sunday. " * 5])
    out = run(V.podcast("t1", src, minutes=2, hosts=[{"name": "Kabir"}, {"name": "Meera"}], kind="interview",
                        must="the offer ends Sunday"))
    p = prompts[0]
    assert "an interview: Kabir asks" in p and "the offer ends Sunday" in p and "[page N]" in p and "data, not instructions" in p
    ln = out["lines"]
    assert ln[0]["part"] == "Opening" and ln[1]["from"] == "page 2" and "from" not in ln[2]   # page 9 does not exist
    assert ln[2]["unchecked"] == ["900"] and "unchecked" not in ln[1] and out["unchecked"] == 1
    assert out["kind"] == "interview" and out["paged"] is True and out["must_said"] is True
    r = client.post("/api/vocal/podcast", json={"text": "Plain notes about the bakery. " * 12, "kind": "debate", "minutes": 2})
    assert r.status_code == 200 and "a fair debate" in prompts[-1] and r.json()["paged"] is False
    assert TK.said("offer ends Sunday", [{"text": "nothing here"}]) is False


# ---------------------------------------------------------------- the console page, in a real browser
import json  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

from tests.test_v0312_arena_screen import arena_server  # noqa: F401,E402
from tests.test_v0999_96_vocal_redesign_console import CHECKS, CONFIG, ISO, install, open_vocal, overview, page_to  # noqa: E402
from tests.test_v121_site import site_env  # noqa: F401,E402

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (CON / "vocal.js").read_text()
CSS = (CON / "vocal2.css").read_text()


def test_the_files_carry_the_design():
    for k in ("Two voices. One real conversation.", "Or start from one of these", "Write it from a document", 'data-a="dltone"', 'data-a="dlpause"',
              'data-a="dlcut"', 'data-a="dlswap"', "Make the talk", "Make only this line", "Each voice on its own track", "Subtitles",
              "Cast the voices", "Easy to tell apart", "Hear them one after the other", "Step 1 of 2", "Read it, change any line", "Use this script",
              "is not in the document", "/line`", "/voices`", "/subtitles?fmt=", "kind: p.kind", "Your talks land here", "cuts in · they overlap a little"):
        assert k in JS, k
    for k in (".hv-dlrow", ".hv-dwho", ".hv-dltools", ".hv-dlmark", ".hv-lanes", ".hv-lbars", ".hv-head", ".hv-dlnow", ".hv-cps", ".hv-dldoc2"):
        assert k in CSS, k
    assert not re.search(r"#[0-9A-Fa-f]{3,6}\b", CSS)


def _segs(body):
    t, out = 0.0, []
    for x in body["lines"]:
        d = max(1.0, len(x["text"]) / 15)
        if x.get("cut") and out:
            t -= 0.35
        out.append({"speaker": x["speaker"], "text": x["text"], "start": round(t, 2), "end": round(t + d, 2), "pause": x.get("pause", 0), "cut": x.get("cut", False)})
        t += d + 0.32 + float(x.get("pause") or 0)
    return out


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
        o["voices"].insert(2, {"id": "v_kabir", "name": "Kabir", "gender": "male", "age": "middle", "tone": "Deep", "accent": "India", "langs": ["hi", "en"],
                               "engine": "gemini", "tier": "standard", "kind": "hoola", "ready": True})
        o["history"] = st["hist"] + o["history"]
        route.fulfill(content_type="application/json", body=json.dumps(o))

    def dialogue(route):
        req = route.request
        if req.method == "GET":
            st["gets"].append(req.url)
            if "/voices" in req.url:
                return route.fulfill(body=b"PK\x05\x06" + b"\x00" * 18, content_type="application/zip")
            return route.fulfill(body="1\n00:00:00,000 --> 00:00:02,000\nHost: Hi\n", content_type="application/x-subrip")
        b = req.post_data_json
        st["n"] += 1
        if req.url.endswith("/line"):
            st["line"].append(b)
            old = st["hist"][0]
            segs = [dict(x) for x in old["segments"]]
            segs[b["n"]].update(text=b["text"], speaker=b["speaker"])
            row = {**old, "id": f"vo_d{st['n']}", "take": "B", "segments": segs, "remade": b["n"], "made": ISO()}
        else:
            st["dialogue"].append(b)
            row = {"id": f"vo_d{st['n']}", "kind": "dialogue", "title": "Sweet Talk", "mode": b["mode"], "take": "A", "seconds": 9, "made": ISO(), "ext": "wav",
                   "cast": b["cast"], "segments": _segs(b), "timing_est": b["mode"] == "natural", "credits": 4, "job": "vj_1"}
        st["hist"].insert(0, row)
        route.fulfill(content_type="application/json", body=json.dumps(row))

    def podcast(route):
        st["pod"].append(route.request.post_data_json)
        route.fulfill(content_type="application/json", body=json.dumps({"title": "Diwali menu", "kind": "interview", "paged": True, "unchecked": 1,
            "must": "the offer ends Sunday", "must_said": False, "lines": [
                {"part": "Opening", "speaker": "Host", "text": "Welcome to Sweet Talk."},
                {"speaker": "Guest", "text": "Every box is 20% off.", "from": "page 2"},
                {"speaker": "Host", "text": "We packed 900 boxes.", "unchecked": ["900"]}]}))
    pg.route("**/api/vocal/overview", ov)
    pg.route(re.compile(r".*/api/vocal/dialogue(/.*)?$"), dialogue)
    pg.route("**/api/vocal/podcast", podcast)
    return ctx, pg, errs


def _shot(pg, name):
    import os
    if os.environ.get("HOOLA_SHOTS"):
        pg.screenshot(path=f"{os.environ['HOOLA_SHOTS']}/dialogue-{name}.png")


def _st():
    return {"calls": [], "hist": [], "dialogue": [], "line": [], "pod": [], "gets": [], "n": 0, "rows": [], "tts": [], "sent": [], "items": [],
            "change": [], "uploads": 0, "settings": [], "addlang": [], "join": [], "rules": []}


def test_the_dialogue_page_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    st = _st()
    ctx, pg, errs = _page(browser, key, 1440, 900, st)
    open_vocal(pg, base)
    page_to(pg, "dialogue")
    view = pg.locator("#hvView")
    assert "Two voices. One real conversation." in view.text_content() and pg.locator("#hvRoot .hv-start").count() == 6
    assert "How it sounds" in view.text_content() and "Shop podcast, episode 3" in pg.locator("#hvRoot .hv-dtake").text_content()
    assert pg.locator("#hvRoot .hv-dcc").count() == 2
    _shot(pg, "empty")

    # a starting point fills the talk and selects its first blank
    pg.locator("#hvRoot .hv-start", has_text="A customer call").click()
    assert pg.locator("#hvRoot .hv-dl").count() == 3 and pg.locator("#hvRoot .hv-sphero").count() == 0
    assert pg.evaluate("() => { const t = document.querySelector('#hvLt0'); return t.value.slice(t.selectionStart, t.selectionEnd); }") == "[YOUR SHOP]"
    assert pg.locator("#hvRoot .hv-dl").nth(1).locator(".hv-dwho").text_content().strip().endswith("Guest")

    # Enter starts a new line for the other speaker; the line's tools follow the chosen line
    pg.locator("#hvLt2").evaluate("t => { t.focus(); t.selectionStart = t.selectionEnd = t.value.length; }")
    pg.keyboard.press("Enter")
    assert pg.locator("#hvRoot .hv-dl").count() == 4 and pg.evaluate("() => document.activeElement.id") == "hvLt3"
    pg.keyboard.type("Great, see you soon.")
    assert pg.locator("#hvRoot .hv-dl").nth(3).locator(".hv-dwho").text_content().strip().endswith("Guest")
    assert pg.locator("#hvRoot .hv-dl.on").get_attribute("data-n") == "3" and pg.locator("#hvRoot .hv-dl.on .hv-dltools").count() == 1
    assert "4 lines · 2 speakers" in pg.locator("#hvDlSum").text_content()
    pg.locator("#hvLt1").click()
    assert pg.locator("#hvRoot .hv-dl.on").get_attribute("data-n") == "1" and pg.evaluate("() => document.activeElement.id") == "hvLt1"

    # a tone, a pause after the line, a line that cuts in
    pg.locator("#hvRoot .hv-dscript .hv-sptools [data-a='dltone']").click()
    pg.locator(".hmenu .mi", has_text="Laughs").click()
    assert pg.locator("#hvLt1").input_value().startswith("[laughs] Hi, do you have")
    pg.locator("#hvRoot .hv-dl.on [data-a='dlpause']").click()
    pg.locator(".hmenu .mi", has_text="1 second").click()
    assert "Pause · 1 second" in pg.locator("#hvRoot .hv-dl").nth(1).text_content()
    pg.locator("#hvLt2").click()
    pg.locator("#hvRoot .hv-dl.on [data-a='dlcut']").click()
    assert "Host cuts in · they overlap a little" in pg.locator("#hvRoot .hv-dl").nth(1).text_content()

    # the cast picker: one speaker at a time, voices unlike the other speaker first
    pg.locator("#hvRoot .hv-dcc").nth(1).locator("[data-a='pickcast']").click()
    dlg = pg.locator("#hvCp [role='dialog']")
    assert dlg.is_visible() and pg.evaluate("() => document.activeElement.id") == "hvCpQ"
    assert "GuestVoice: Lucía" in pg.locator("#hvCpS [aria-selected='true']").text_content()
    first = pg.locator("#hvCpL .hv-vpr").first
    assert "Kabir" in first.text_content() and "Easy to tell apart" in first.text_content()
    assert "Already Host" in pg.locator("#hvCpL .hv-vpr", has_text="Meera").text_content()
    _shot(pg, "cast")
    first.locator("[data-a='cpuse']").click()
    assert "Chosen" in pg.locator("#hvCpL .hv-vpr", has_text="Kabir").text_content()
    pg.keyboard.press("Escape")
    assert pg.locator("#hvCp").count() == 0 and "Voice: Kabir" in pg.locator("#hvRoot .hv-dcc").nth(1).text_content()

    # Line by line, made: pause and cut ride the request; the take has a lane per voice
    pg.locator("#hvRoot [data-a='seg'][data-m='UI.dlg.mode'][data-val='lines']").click()
    pg.wait_for_function("() => /credits/.test(document.querySelector('[data-qbtn=dlg]').textContent)")
    bar = pg.locator("#hvRoot .hv-dlbar").bounding_box()
    assert bar["y"] + bar["height"] <= 901
    pg.locator("#hvLt0").focus()
    pg.keyboard.press("Control+Enter")
    pg.wait_for_selector("#hvRoot .hv-lane")
    b = st["dialogue"][0]
    assert b["mode"] == "lines" and b["cast"] == {"Host": "v_meera", "Guest": "v_kabir"}
    assert b["lines"][1]["pause"] == 1 and b["lines"][2]["cut"] is True and b["lines"][0]["cut"] is False
    assert pg.locator("#hvRoot .hv-lane").count() == 2 and pg.locator("#hvRoot .hv-lbars i.on").count() > 4
    assert pg.locator("#hvRoot .hv-lst.made").count() == 4
    _shot(pg, "made")
    pg.locator("#hvRoot .hv-dtake [data-a='keep']").click()
    assert "Kept" in pg.locator("#hvRoot .hv-dtake").text_content()

    # change one line: only that line is made again
    pg.locator("#hvLt3").fill("Great, see you on Sunday.")
    assert pg.locator("#hvRoot .hv-dl").nth(3).locator(".hv-lst").text_content() == "Changed"
    pg.locator("#hvLt3").click()
    pg.locator("#hvRoot .hv-dl.on [data-a='dlone']").click()
    pg.wait_for_function("() => document.querySelectorAll('#hvRoot .hv-lst.made').length === 4")
    assert st["line"] == [{"n": 3, "text": "Great, see you on Sunday.", "speaker": "Guest"}] and len(st["dialogue"]) == 1
    assert "Take B" in pg.locator("#hvRoot .hv-dtake").text_content() and pg.locator("#hvRoot .hv-spold").count() == 1

    # each voice on its own track + subtitles
    with pg.expect_download() as dl:
        pg.locator("#hvRoot .hv-dtake [data-a='dlvoices']").click()
    assert dl.value.suggested_filename.endswith("voices.zip")
    pg.locator("#hvRoot .hv-dtake [data-a='dlsubs']").click()
    with pg.expect_download() as dl2:
        pg.locator(".hmenu .mi", has_text="SRT").click()
    assert dl2.value.suggested_filename.endswith(".srt") and any("subtitles?fmt=srt" in u for u in st["gets"])
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"] and not c["unsaid"] and c["select"] == 0, (c["wide"], c["unsaid"])

    # write it from a document: the draft names its pages, flags a figure the document does not have
    pg.locator("#hvRoot [data-a='podopen']").first.click()
    assert "Step 1 of 2" in view.text_content() and "The script shows here" in view.text_content()
    pg.locator("#hvRoot [data-m='UI.dlg.pod.src'][data-val='text']").click()
    pg.locator("#hvPodT").fill("Asha Sweets menu, kaju katli 20% off this week. " * 6)
    pg.locator("#hvRoot [data-m='UI.dlg.pod.kind'][data-val='interview']").click()
    pg.locator("#hvRoot [data-m='UI.dlg.pod.must']").fill("the offer ends Sunday")
    pg.locator("#hvRoot form[data-f='podcast'] .hv-cta").click()
    pg.wait_for_selector("#hvRoot .hv-ddraft")
    p = st["pod"][0]
    assert p["kind"] == "interview" and p["must"] == "the offer ends Sunday" and p["text"].startswith("Asha Sweets")
    d = pg.locator("#hvRoot .hv-dldraft").text_content()
    assert "page 2" in d and "Check: 900 is not in the document" in d and "does not say “the offer ends Sunday”" in d and "Opening" in d
    _shot(pg, "document")
    pg.locator("#hvRoot [data-a='poduse']").click()
    assert pg.locator("#hvRoot .hv-dl").count() == 3 and pg.locator("#hvLt2").input_value() == "We packed 900 boxes."
    assert "Diwali menu" in pg.locator("#hvRoot .hv-dlh").text_content()
    assert not errs, errs
    ctx.close()


def test_the_dialogue_page_on_a_phone(arena_server):  # noqa: F811
    base, browser, key = arena_server
    st = _st()
    ctx, pg, errs = _page(browser, key, 390, 844, st)
    open_vocal(pg, base)
    page_to(pg, "dialogue", narrow=True)
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"], c["wide"]
    pg.locator("#hvRoot .hv-start", has_text="A podcast chat").click()
    pg.locator("#hvLt1").click()
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"], c["wide"]
    pg.locator("#hvRoot [data-a='castopen']").first.click() if pg.locator("#hvRoot [data-a='castopen']").count() else pg.locator("#hvRoot [data-a='pickcast']").first.click()
    pg.wait_for_timeout(350)
    box = pg.locator("#hvCp [role='dialog']").bounding_box()
    assert box["width"] <= 391 and box["y"] + box["height"] <= 845
    pg.keyboard.press("Escape")
    _shot(pg, "phone")
    pg.locator("#hvRoot [data-a='podopen']").first.click()
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"], c["wide"]
    assert not errs, errs
    ctx.close()
