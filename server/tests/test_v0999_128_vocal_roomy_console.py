"""v0.999.128 VOCAL CHAT, ROOMY (owner: "MAKE IT MORE USER FRIENDLY AND PREMIUM WITH CHAT WIDTH FLEXIBLE" -> design canvas
claude.ai/artifact/WjcWjLf8Qgm7Rw1DnnAMou -> "GO BUILD"), walked in a real Chromium on mocked routes:
one welcome (the stored greeting is never drawn a second time, so no lone copy button under it), the box in the middle of a
fresh chat with four starters, the chat width by drag / Narrow / Balanced / Wide / Chat only (remembered), Your sounds folded
into a rail (and folded by itself while there is nothing), takes with Keep and Compare, the voice in the chat bar, and the
Your sounds button on a phone."""
import json
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v0999_96_vocal_redesign_console import CONFIG, FAKE_MIC, ISO, install, open_vocal, overview
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (ROOT / "vocal.js").read_text()
CSS = (ROOT / "vocal2.css").read_text()
GREETING = "Tell me what to say, in any language: a welcome, an ad, a story."


def test_the_files_carry_the_design():
    for k in ("What should Hoola say today?", "data-drag=\"chatw\"", "hv.chatw", "hv.chatmode", "'Chat only'", "data-a=\"unfold\"",
              "data-a=\"compare\"", "hv-keep", "New vocal chat", "Recent chats"):
        assert k in JS, k
    assert "hv-hello" not in JS and "hv-chathd" not in JS and "const IDEAS" not in JS     # the second welcome and the old header are gone
    assert "--hv-cw" in CSS and ".hv-splith" in CSS and ".hv-rail" in CSS
    assert not __import__("re").search(r"#[0-9A-Fa-f]{3,6}\b", CSS)                      # console tokens only


def _page(browser, key, w, h, st, empty=False):
    ctx = browser.new_context(viewport={"width": w, "height": h})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    ctx.add_init_script(FAKE_MIC)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:300]))
    pg.on("dialog", lambda d: d.accept())
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)
    if empty:
        def ov(route):
            o = overview()
            o["history"] = []
            route.fulfill(content_type="application/json", body=json.dumps(o))
        pg.route("**/api/vocal/overview", ov)
    return ctx, pg, errs


def _st():
    return {"calls": [], "tts": [], "sent": [], "items": [], "change": [], "uploads": 0, "settings": [], "addlang": [],
            "rows": [{"id": "g", "role": "assistant", "text": GREETING, "at": ISO(-5)}]}


def test_the_roomy_chat_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    st = _st()
    ctx, pg, errs = _page(browser, key, 1440, 900, st)
    open_vocal(pg, base)
    pg.wait_for_selector("#hvRoot .hv-hero")

    # one welcome: the hero, never the stored greeting again (and so no copy button under it)
    assert pg.locator("#hvRoot .hv-heroh").text_content() == "What should Hoola say today?"
    assert GREETING not in pg.locator("#hvRoot .hv-chat").inner_text()
    assert pg.locator("#hvRoot .hv-chat #hvAsk").count() == 1 and pg.locator("#hvRoot .hv-hero #hvAsk").count() == 1
    assert pg.locator("#hvRoot .hv-start").count() == 4
    pg.locator("#hvRoot .hv-start").first.click()
    assert "bakery" in pg.locator("#hvAsk").input_value()
    assert pg.locator("#hvRoot .hv-newchat").count() == 1                     # the sidebar's New vocal chat

    # her first words: the welcome makes room, her bubble + Hoola's reply + the set of takes
    pg.locator("#hvAsk").fill("A warm welcome for my bakery in Spanish")
    pg.locator("#hvAsk").press("Enter")
    pg.wait_for_selector("#hvRoot .hv-setc")
    assert pg.locator("#hvRoot .hv-hero").count() == 0
    pg.wait_for_function("() => document.querySelector('#hvRoot .hv-chat').innerText.includes('a little slower')")   # the reply lands word by word
    chat = pg.locator("#hvRoot .hv-chat").inner_text()
    assert GREETING not in chat and "Two takes in Hindi" in chat, chat
    assert pg.locator("#hvRoot .hv-setc .hv-av.l").text_content() == "M"      # the voice's initial
    assert pg.locator("#hvRoot #hvAv").text_content().strip() != ""           # and in the chat bar

    # Keep on a take, in place
    kb = pg.locator("#hvRoot .hv-setc .hv-keep").first
    kb.click()
    pg.wait_for_function("() => document.querySelector('#hvRoot .hv-setc .hv-keep').getAttribute('aria-pressed') === 'true'")
    assert "Kept" in pg.locator("#hvRoot .hv-setc .hv-keep").first.text_content()
    assert "vo_c0" in pg.evaluate("localStorage.getItem('hv.kept')")

    # Compare plays take A, then queues take B
    pg.locator("#hvRoot [data-a='compare']").click()
    pg.wait_for_function("() => !document.querySelector('#hvBar').hidden")
    assert pg.locator("#hvNow").text_content() == "Diwali offer · take A"      # take A is playing; B waits for it to end

    # the width: presets, drag, remembered
    def chat_w():
        return pg.evaluate("document.querySelector('#hvRoot .hv-chatpage .hv-chat').getBoundingClientRect().width")
    pg.locator("#hvRoot [data-a='cwidth'][data-val='narrow']").click()
    pg.wait_for_timeout(150)
    assert abs(chat_w() - 460) < 2
    assert pg.locator("#hvRoot [data-a='cwidth'][aria-pressed='true']").text_content() == "Narrow"
    hb = pg.locator("#hvRoot .hv-splith").bounding_box()
    pg.mouse.move(hb["x"] + 6, hb["y"] + 300)
    pg.mouse.down()
    pg.mouse.move(hb["x"] + 206, hb["y"] + 300, steps=6)
    pg.mouse.up()
    pg.wait_for_timeout(150)
    assert abs(chat_w() - 660) < 3 and pg.evaluate("+localStorage.getItem('hv.chatw')") == 660
    pg.locator("#hvRoot .hv-splith").focus()
    pg.keyboard.press("ArrowLeft")
    pg.wait_for_timeout(100)
    assert abs(chat_w() - 620) < 3
    pg.locator("#hvRoot .hv-splith").dblclick()
    pg.wait_for_timeout(100)
    assert abs(chat_w() - 640) < 3

    # Chat only: Your sounds folds into a rail, the thread is not redrawn, the rail opens it again
    marker = pg.evaluate("() => { const t = document.querySelector('#hvThread'); t.dataset.keep = '1'; return true; }")
    assert marker
    pg.locator("#hvRoot .hv-stage [data-a='cwidth'][data-val='chat']").click()
    pg.wait_for_selector("#hvRoot .hv-rail")
    assert pg.locator("#hvRoot #hvStage").count() == 0 and pg.locator("#hvRoot .hv-splith").count() == 0
    assert chat_w() > 1000
    assert pg.evaluate("document.querySelector('#hvThread').dataset.keep") == "1"
    assert pg.evaluate("localStorage.getItem('hv.chatmode')") == '"chat"'
    pg.locator("#hvRoot .hv-rail").click()
    pg.wait_for_selector("#hvRoot #hvStage")
    assert abs(chat_w() - 640) < 3

    # remembered on this computer: a new page opens at the same width
    pg.locator("#hvRoot [data-a='cwidth'][data-val='wide']").click()
    pg.wait_for_timeout(100)
    pg.reload()
    pg.wait_for_selector(".sn[data-v='vocal']", state="attached")
    pg.evaluate("document.querySelector(\".sn[data-v='vocal']\").click()")
    pg.wait_for_selector("#hvRoot .hv-chat")
    pg.wait_for_timeout(500)
    stored = pg.evaluate("+localStorage.getItem('hv.chatw')")
    assert 850 <= stored <= 880 and abs(chat_w() - stored) < 3                 # Wide, held so Your sounds keeps 320 px
    assert errs == [], errs
    ctx.close()


def test_nothing_made_yet_and_a_phone(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx, pg, errs = _page(browser, key, 1440, 900, _st(), empty=True)
    open_vocal(pg, base)
    pg.wait_for_selector("#hvRoot .hv-hero")
    assert pg.locator("#hvRoot .hv-rail").count() == 1 and pg.locator("#hvRoot #hvStage").count() == 0   # folded while empty
    assert pg.locator("#hvRoot [data-a='cwidth'][aria-pressed='true']").text_content() == "Chat only"
    pg.locator("#hvRoot .hv-rail").click()
    pg.wait_for_selector("#hvRoot #hvStage")
    assert "Nothing yet" in pg.locator("#hvRoot #hvStage").inner_text()
    assert errs == [], errs
    ctx.close()

    ctx, pg, errs = _page(browser, key, 390, 844, _st())
    open_vocal(pg, base)
    pg.wait_for_selector("#hvRoot .hv-hero")
    assert pg.evaluate("document.documentElement.scrollWidth <= 391")
    assert pg.locator("#hvRoot .hv-heromark").is_visible()                      # the top of the welcome is not cut off
    assert pg.locator("#hvRoot .hv-sndbtn").is_visible() and not pg.locator("#hvRoot .hv-widths").is_visible()
    pg.locator("#hvAsk").fill("A warm welcome for my bakery in Spanish")
    pg.locator("#hvAsk").press("Enter")
    pg.wait_for_selector("#hvRoot .hv-setc")
    row = pg.locator("#hvRoot .hv-setc .hv-take").first.bounding_box()
    assert row["height"] < 60                                                   # play, name, wave, Keep on one line
    keep = pg.locator("#hvRoot .hv-setc .hv-keep").first.bounding_box()
    assert keep["height"] >= 36
    pg.locator("#hvRoot .hv-sndbtn").click()
    pg.wait_for_function("() => document.querySelector('#hvRoot .hv-nv[aria-current=page]')?.dataset.p === 'sounds'")
    assert errs == [], errs
    ctx.close()
