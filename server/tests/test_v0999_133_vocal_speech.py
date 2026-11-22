"""v0.999.133 SPEECH, PREMIUM (owner: "NOW MAKE SPEECH SECTION MORE PREMIUM AND ADVANCE PERFECTLY --- SHOW DESIGN HERE FIRST"
-> design canvas claude.ai/artifact/B6TXccvssgFpNsR4ndVq3p -> "GO BUILD").

Server: POST /api/vocal/join puts the lines she made one by one into ONE file, in her order, at no cost; a line that is no
longer kept is named. Console: the Speech page walked in a real Chromium on mocked routes - the first open (a heading and six
ways to start), the words in a writing area with every [tone] and every dictionary word marked on a layer that lines up
with the text, Add a tone / Pause / Say it like / Improve, the voice as a card and the voice picker (search, filters, a
sample, Use, Escape), More settings folded, the Speak bar in view with the price, Ctrl + Enter, takes with Keep / Compare /
Slower, and Line by line (lines made on their own, a changed line, its own tone and voice, joined into one file); and the
page at phone width with nothing sideways."""
import json
import re
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v0999_96_vocal_redesign_console import CHECKS, CONFIG, ISO, install, open_vocal, overview, page_to
from tests.test_v0999_96_vocal_redesign_server import client, tone, vg  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (ROOT / "vocal.js").read_text()
CSS = (ROOT / "vocal2.css").read_text()


# ---------------------------------------------------------------- the server: lines joined into one file
def test_join_puts_the_lines_into_one_file(client):  # noqa: F811
    a = client.post("/api/vocal/tts", json={"text": "[warm] Welcome to the shop.", "takes": 1, "format": "wav"}).json()
    b = client.post("/api/vocal/tts", json={"text": "Everything is ten percent off.", "takes": 1, "format": "wav"}).json()
    c = client.post("/api/vocal/tts", json={"text": "See you soon.", "takes": 1, "format": "mp3"}).json()
    r = client.post("/api/vocal/join", json={"ids": [a["id"], b["id"], c["id"]], "format": "mp3"})
    assert r.status_code == 200, r.text
    row = r.json()
    assert row["kind"] == "tts" and row["voice_name"] == "3 lines" and row["credits"] == 0 and row["ext"] == "mp3"
    assert row["joined"] == [a["id"], b["id"], c["id"]] and row["title"] == "Welcome to the shop."
    assert row["seconds"] >= a["seconds"] + b["seconds"] + 0.6                    # three lines and the quiet between them
    got = client.get(f"/api/vocal/audio?id={row['id']}")
    assert got.status_code == 200 and len(got.content) > 1000
    w = client.post("/api/vocal/join", json={"ids": [a["id"], b["id"]], "format": "wav"}).json()
    assert w["ext"] == "wav" and w["seconds"] >= 0.8
    one = client.post("/api/vocal/join", json={"ids": [a["id"]]})
    assert one.status_code == 422 and "at least two lines" in one.json()["detail"]
    gone = client.post("/api/vocal/join", json={"ids": [a["id"], "vo_nothere"]})
    assert gone.status_code == 422 and "Line 2" in gone.json()["detail"]
    assert client.post("/api/vocal/join", json={"ids": [a["id"], b["id"]], "format": "exe"}).status_code == 422


# ---------------------------------------------------------------- the files keep the design
def test_the_files_carry_the_design():
    for k in ("Write it once. Hear it said well.", "Start from one of these", 'data-a="tonemenu"', 'data-a="sayas"', 'data-a="spimprove"',
              'data-a="vpopen"', "Pick a voice", "More settings", 'data-a="spmode"', "Line by line", "Download as one file",
              "Your takes land here", "hv.spmode", "hv.lines", "${A}/join", "Ctrl + Enter"):
        assert k in JS, k
    for k in (".hv-edhi", ".hv-edta", ".hv-tg", ".hv-dw", ".hv-spbar", ".hv-vp", ".hv-lnbar", "@container (max-width:980px)"):
        assert k in CSS, k
    assert not re.search(r"#[0-9A-Fa-f]{3,6}\b", CSS)                              # console tokens only


# ---------------------------------------------------------------- the console page
def _st():
    return {"calls": [], "tts": [], "sent": [], "items": [], "change": [], "uploads": 0, "settings": [], "addlang": [], "rows": [],
            "hist": [], "join": [], "rules": [], "n": 0}


def _page(browser, key, w, h, st):
    ctx = browser.new_context(viewport={"width": w, "height": h})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs, dialogs = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)[:300]))

    def dialog(d):
        dialogs.append(d.message)
        d.accept("Mithai" if "Which word" in d.message else "Mi-THAI" if "How should" in d.message else None)
    pg.on("dialog", dialog)
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)

    def ov(route):                                     # what she made stays in Your sounds (the lines read it back)
        o = overview()
        o["history"] = st["hist"] + o["history"]
        o["rules"] = o["rules"] + st["rules"]
        route.fulfill(content_type="application/json", body=json.dumps(o))

    def tts(route):
        b = route.request.post_data_json
        st["tts"].append(b)
        made = []
        for i in range(int(b.get("takes") or 1)):
            st["n"] += 1
            made.append({"id": f"vo_n{st['n']}", "kind": "tts", "title": re.sub(r"\[[^\]]*\]\s*", "", b["text"])[:60], "text": b["text"],
                         "voice": b["voice"], "voice_name": {"v_meera": "Meera", "v_lucia": "Lucía"}.get(b["voice"], "Meera"), "lang": "hi",
                         "engine": "gemini", "seconds": 3 + i, "made": ISO(), "ext": b.get("format"), "take": "ABCD"[i], "credits": 2, "style": b.get("style")})
        st["hist"][:0] = made
        route.fulfill(content_type="application/json", body=json.dumps({"items": made, "lang_name": "Hindi", "credits": 2 * len(made)}))

    def join(route):
        b = route.request.post_data_json
        st["join"].append(b)
        row = {"id": "vo_joined", "kind": "tts", "title": "Joined", "voice_name": f"{len(b['ids'])} lines", "seconds": 9, "made": ISO(),
               "ext": b.get("format"), "credits": 0, "joined": b["ids"]}
        st["hist"].insert(0, row)
        route.fulfill(content_type="application/json", body=json.dumps(row))

    def rule(route):
        b = route.request.post_data_json
        st["rules"].append({"id": "pr_new", **b})
        route.fulfill(content_type="application/json", body=json.dumps({"ok": True}))
    pg.route("**/api/vocal/overview", ov)
    pg.route("**/api/vocal/tts", tts)
    pg.route("**/api/vocal/join", join)
    pg.route("**/api/vocal/rule", rule)
    return ctx, pg, errs, dialogs


def test_the_speech_page_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    st = _st()
    ctx, pg, errs, dialogs = _page(browser, key, 1440, 900, st)
    open_vocal(pg, base)
    page_to(pg, "speech")
    view = pg.locator("#hvView")

    # the first open: a heading, six ways to start, the takes say where they will land
    assert "Write it once. Hear it said well." in view.text_content() and pg.locator("#hvRoot .hv-start").count() == 6
    assert "Your takes land here" in pg.locator("#hvRoot .hv-stage").text_content()
    assert pg.locator("#hvSpMore").is_hidden() and "Language:" in view.text_content()
    pg.locator("#hvRoot .hv-start", has_text="A short ad").click()
    assert pg.locator("#hvText").input_value().startswith("[excited] This week only at [YOUR SHOP]")
    assert pg.evaluate("() => { const t = document.querySelector('#hvText'); return t.value.slice(t.selectionStart, t.selectionEnd); }") == "[YOUR SHOP]"
    assert pg.locator("#hvRoot .hv-sphero").count() == 0 and pg.locator("#hvRoot .hv-start").count() == 0
    assert pg.locator("#hvHi .hv-tg").count() == 5                                  # [excited] [YOUR SHOP] [YOUR OFFER] [warm] [YOUR NUMBER]

    # her words: tones + dictionary words marked on the layer under the text, which lines up with it
    pg.locator("#hvText").fill("Is Diwali, Mithas par chhoot.")
    assert pg.locator("#hvHi .hv-dw").all_text_contents() == ["Mithas"] and pg.locator("#hvHi .hv-tg").count() == 0
    assert pg.locator("#hvTime").text_content() == "5 words · about 0:02"
    pg.locator("#hvText").evaluate("t => { t.focus(); t.selectionStart = t.selectionEnd = t.value.length; }")
    pg.locator("#hvRoot [data-a='tag'][data-val='pause']").click()
    pg.locator("#hvRoot [data-a='tonemenu']").click()
    assert [x.split()[0] for x in pg.locator(".hmenu .mi .mt>span").all_text_contents()][:3] == ["Warm", "Whispers", "Laughs"]
    pg.locator(".hmenu .mi", has_text="Warm").click()
    assert pg.locator("#hvText").input_value() == "Is Diwali, Mithas par chhoot. [pause] [warm] "
    assert pg.locator("#hvHi .hv-tg").all_text_contents() == ["[pause]", "[warm]"]
    al = pg.evaluate("""() => { const t = document.querySelector('#hvText'), h = document.querySelector('#hvHi'), a = getComputedStyle(t), b = getComputedStyle(h);
      return {font: a.fontFamily === b.fontFamily && a.fontSize === b.fontSize && a.lineHeight === b.lineHeight && a.paddingLeft === b.paddingLeft && a.whiteSpace === b.whiteSpace,
              lines: Math.abs(t.scrollHeight - h.scrollHeight) <= 2, serif: /Literata/.test(a.fontFamily)}; }""")
    assert al == {"font": True, "lines": True, "serif": True}, al
    assert "1 word from your dictionary" in pg.locator("#hvCount").text_content()

    # Say it like: a word read her way, saved in her dictionary
    pg.locator("#hvRoot [data-a='sayas']").click()
    pg.wait_for_timeout(600)
    assert any("Which word" in m for m in dialogs) and any("How should" in m for m in dialogs)
    assert st["rules"] and st["rules"][-1]["word"] == "Mithai" and st["rules"][-1]["say"] == "Mi-THAI"

    # the voice card and the voice picker
    assert "Meera" in pg.locator("#hvRoot .hv-vcard").text_content()
    pg.locator("#hvRoot .hv-vcard [data-a='vpopen']").click()
    dlg = pg.locator("#hvVp [role='dialog']")
    assert dlg.is_visible() and pg.evaluate("() => document.activeElement.id") == "hvVpQ"
    assert "Your voices" in pg.locator("#hvVpF").text_content() and "free" in dlg.text_content()
    pg.locator("#hvVpQ").fill("zulu")
    assert pg.locator("#hvVpL .hv-vpr").count() == 1 and "Thandi" in pg.locator("#hvVpL").text_content()
    pg.locator("#hvVpQ").fill("")
    pg.locator("#hvVpF [data-val='Your voices']").click()
    assert pg.locator("#hvVpL .hv-vpr").count() == 2 and pg.locator("#hvVpL i").count() == 0        # her voice's name is text, never markup
    pg.keyboard.press("Escape")
    assert pg.locator("#hvVp").count() == 0 and pg.evaluate("() => document.activeElement.dataset.a") == "vpopen"
    pg.locator("#hvRoot .hv-vcard [data-a='vpopen']").click()
    pg.locator("#hvVp [data-a='vpuse'][data-id='v_lucia']").click()
    assert pg.locator("#hvVp").count() == 0 and "Lucía" in pg.locator("#hvRoot .hv-vcard").text_content()
    assert pg.locator("#hvSpSum").text_content().startswith("Lucía · Warm · 1.00x · 2 takes")

    # More settings folds the language, format, engine and dictionary
    pg.locator("#hvRoot [data-a='spmore']").click()
    assert pg.locator("#hvSpMore").is_visible() and pg.locator("#hvRoot [data-a='picklang']").is_visible()
    assert pg.locator("#hvRoot [data-a='spmore']").get_attribute("aria-expanded") == "true"

    # the Speak bar stays in view with the price; Ctrl + Enter speaks
    pg.wait_for_function("() => /credits/.test(document.querySelector('[data-qbtn=speech]').textContent)")
    assert "Speak it · 4 credits" in pg.locator("[data-qbtn='speech']").text_content()
    pg.locator("#hvRoot .hv-spform").evaluate("f => { f.scrollTop = 0; }")
    bar = pg.locator("#hvRoot .hv-spbar").bounding_box()
    assert bar["y"] + bar["height"] <= 900 + 1
    pg.locator("#hvText").focus()
    pg.keyboard.press("Control+Enter")
    pg.wait_for_selector("#hvTakes .hv-sptake")
    assert len(st["tts"]) == 1 and st["tts"][0]["voice"] == "v_lucia" and st["tts"][0]["takes"] == 2
    assert pg.locator("#hvTakes .hv-sptake").count() == 2 and pg.locator("#hvRoot .hv-stage [data-a='compare']").count() == 1
    pg.locator("#hvTakes [data-a='keep']").first.click()
    assert "Kept" in pg.locator("#hvTakes .hv-sptake").first.text_content()
    pg.locator("#hvRoot .hv-stage [data-a='sptweak'][data-val='slower']").click()
    assert pg.locator("#hvRoot [data-show='S.speed']").first.text_content() == "0.90x"
    assert len(st["tts"]) == 1                                                      # a change never spends: she presses Speak it again
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"] and not c["unsaid"] and c["select"] == 0, (c["wide"], c["unsaid"])

    # Line by line: each line made on its own, a changed line, its own tone and voice, then one file
    pg.locator("#hvRoot [data-a='spmode'][data-val='lines']").click()
    assert pg.locator("#hvRoot .hv-ln").count() == 1
    pg.locator("#hvRoot [data-a='lnadd']").click()
    assert pg.locator("#hvRoot .hv-ln").count() == 2 and pg.evaluate("() => document.activeElement.dataset.line") == "1"
    pg.keyboard.type("Order before Sunday.")
    pg.wait_for_function("() => /Make 2 lines/.test(document.querySelector('[data-a=lnmakeall]')?.textContent || '')")
    assert pg.locator("#hvRoot [data-a='lnjoin']").is_disabled() and "Make every line first" in pg.locator("#hvJoinWhy").text_content()
    pg.locator("#hvRoot [data-a='lnmakeall']").click()
    pg.wait_for_function("() => document.querySelectorAll('#hvRoot .hv-lst.made').length === 2")
    lines = st["tts"][1:]
    assert [x["text"] for x in lines] == ["Is Diwali, Mithas par chhoot. [pause] [warm] ", "Order before Sunday."]
    assert all(x["takes"] == 1 and x["format"] == "wav" for x in lines)
    pg.locator("#hvRoot .hv-lnt[data-line='1']").fill("Order before Saturday.")
    assert pg.locator("#hvRoot [data-lst='1']").text_content() == "Changed" and pg.locator("#hvRoot [data-lst='0']").text_content() == "Made"
    pg.locator("#hvRoot [data-a='lnsel'][data-val='1']").click()
    assert "Line 2" in pg.locator("#hvRoot .hv-lnside").text_content()
    pg.locator("#hvRoot .hv-lnside [data-a='lntone'][data-val='excited']").click()
    assert pg.locator("#hvRoot .hv-ln").nth(1).locator(".hv-tgp").text_content() == "excited"
    assert pg.locator("#hvRoot .hv-lnt[data-line='1']").input_value() == "Order before Saturday."
    pg.locator("#hvRoot .hv-lnside [data-a='vpopen']").click()
    assert "Pick a voice for line 2" in pg.locator("#hvVp").text_content()
    pg.locator("#hvVp [data-a='vpuse'][data-id='v_meera']").click()
    assert "Meera · this line only" in pg.locator("#hvRoot .hv-ln").nth(1).text_content()
    pg.locator("#hvRoot [data-a='lnmake'][data-val='1']").click()
    pg.wait_for_function("() => document.querySelectorAll('#hvRoot .hv-lst.made').length === 2")
    assert st["tts"][-1]["text"] == "[excited] Order before Saturday." and st["tts"][-1]["voice"] == "v_meera"
    assert pg.locator("#hvRoot [data-a='lnjoin']").is_enabled()
    pg.locator("#hvRoot [data-a='lnjoin']").click()
    pg.wait_for_function("() => true")
    pg.wait_for_timeout(500)
    assert st["join"] and len(st["join"][-1]["ids"]) == 2 and st["join"][-1]["ids"][1] == st["hist"][1]["id"]
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"] and not c["unsaid"], (c["wide"], c["unsaid"])
    pg.reload()                                                                     # the mode and the made lines are remembered
    open_vocal(pg, base)
    page_to(pg, "speech")
    assert pg.locator("#hvRoot [data-a='spmode'][data-val='lines']").get_attribute("aria-selected") == "true"
    assert not errs, errs
    ctx.close()


def test_the_speech_page_on_a_phone(arena_server):  # noqa: F811
    base, browser, key = arena_server
    st = _st()
    ctx, pg, errs, _ = _page(browser, key, 390, 844, st)
    open_vocal(pg, base)
    page_to(pg, "speech", narrow=True)
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"], c["wide"]
    pg.locator("#hvText").fill("[warm] Welcome to the shop.\nEverything is ten percent off.")
    pg.locator("#hvRoot .hv-vcard [data-a='vpopen']").click()
    pg.wait_for_timeout(350)                                                        # its 180 ms rise has ended
    box = pg.locator("#hvVp [role='dialog']").bounding_box()
    assert box["width"] <= 391 and box["y"] + box["height"] <= 845                  # the picker is a sheet from the bottom
    pg.keyboard.press("Escape")
    pg.locator("#hvRoot [data-a='spmode'][data-val='lines']").click()
    assert pg.locator("#hvRoot .hv-ln").count() == 2
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"], c["wide"]
    assert not errs, errs
    ctx.close()
