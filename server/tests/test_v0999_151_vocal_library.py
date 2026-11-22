"""v0.999.151 VOICE LIBRARY, PREMIUM - favourites kept on the server, the sample line of each language, and the console page
walked in a real Chromium: describe a voice (best matches, and why), kinds of voices, a quiet list with a voice print per
voice, a voice heard in her language, favourites, compare (with names hidden until she chooses), the picker's tabs."""
import json
import os
import re
from urllib.parse import urlparse

from app.vocal import service as V
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v0999_96_vocal_redesign_console import CONFIG, ISO, install, open_vocal, overview, page_to
from tests.test_v0999_96_vocal_redesign_server import client, vg  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

HERE = os.path.dirname(__file__)
JS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal.js"), encoding="utf-8").read()
CSS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal2.css"), encoding="utf-8").read()


def test_favourites_are_kept_and_the_sample_lines_ride_the_overview(vg, client):
    assert client.put("/api/vocal/voices/fav", json={"id": "hv_Kore"}).json() == {"favs": ["hv_Kore"]}
    assert client.put("/api/vocal/voices/fav", json={"id": "hv_Puck"}).json()["favs"] == ["hv_Puck", "hv_Kore"]     # newest first
    assert client.put("/api/vocal/voices/fav", json={"id": "hv_Kore", "on": False}).json()["favs"] == ["hv_Puck"]
    assert client.put("/api/vocal/voices/fav", json={"id": "hv_Nobody"}).status_code == 404                       # only a voice Hoola knows
    assert client.put("/api/vocal/voices/fav", json={"id": ""}).status_code == 422
    ov = V.overview("t1")
    assert ov["favs"] == ["hv_Puck"] and ov["sample_lines"]["hi"].startswith("Namaste") and ov["sample_lines"]["en"]


def test_the_files_carry_the_design():
    for k in ("vMatch", "VSETS", "vprint", "cmpView", "Listen without names", "Every sample speaks", "Use in Speech", "Make one like it",
              "/voices/fav", "Hear it say your words", "Open the whole library", "Favourites"):
        assert k in JS, k
    for k in ("v0.999.151 VOICE LIBRARY, PREMIUM", ".hv-vprint", ".hv-vsets", ".hv-cmpg", ".hv-vtray"):
        assert k in CSS, k
    assert not re.search(r"#[0-9A-Fa-f]{3,6}\b", CSS) and "<select" not in JS


def lib(pg, st):
    def route(r):
        req = r.request
        path = urlparse(req.url).path[len("/api/vocal"):]
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        if path == "/overview":
            o = overview()
            o["favs"] = st["favs"]
            o["sample_lines"] = {"en": "Hello, this is how I sound.", "hi": "Namaste, meri awaaz aisi sunai deti hai.", "es": "Hola, así suena mi voz."}
            o["history"] = [{**o["history"][0], "voice": "v_meera", "title": "Diwali offer"}, *o["history"][1:]]
            return r.fulfill(content_type="application/json", body=json.dumps(o))
        if path == "/voices/fav":
            st["favput"].append(body)
            st["favs"] = [x for x in st["favs"] if x != body["id"]]
            if body.get("on", True):
                st["favs"].insert(0, body["id"])
            return r.fulfill(content_type="application/json", body=json.dumps({"favs": st["favs"]}))
        if path == "/voice/preview":
            st["previews"].append(urlparse(req.url).query)
        return r.fallback()
    pg.route("**/api/vocal/**", route)


NO_SIDEWAYS = "() => document.documentElement.scrollWidth <= innerWidth + 1 && document.querySelector('#hvRoot').scrollWidth <= document.querySelector('#hvRoot').clientWidth + 1"


def test_the_voice_library_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("HOOLA_SHOTS")
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "settings": [], "addlang": [],
              "favs": [], "favput": [], "previews": []}
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
        pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
        install(pg, st)
        lib(pg, st)
        open_vocal(pg, base)
        page_to(pg, "voices", width < 600)
        pg.wait_for_selector("#hvView .hv-vrow")
        assert pg.locator("#hvView .hv-vprint").count() >= 3 and pg.locator("#hvView .hv-ava").count() == 0      # a voice print, never a letter
        assert pg.locator("#hvView .hv-vset").count() == 5
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/lib-{scheme}-{width}-1-library.png")
        # describe a voice: the best matches, and why each matched
        pg.locator("#hvVq").fill("young bright woman, Spanish")
        pg.wait_for_function("() => document.querySelector('#hvView .hv-count').textContent.includes('best match')")
        assert pg.locator("#hvView .hv-vrow").first.locator(".hv-vwhy").text_content().startswith("young") or "Spanish" in pg.locator("#hvView .hv-vrow").first.text_content()
        assert "Lucía" in pg.locator("#hvView .hv-vrow").first.text_content()
        pg.locator("#hvVq").fill("")
        pg.wait_for_function("() => !document.querySelector('#hvView .hv-count').textContent.includes('best match')")
        # the chosen voice: heard in her language, used in her sounds, a favourite
        pg.locator("#hvView [data-a='vsel'][data-id='v_meera']").click()
        det = pg.locator("#hvRoot .hv-vdetail")
        assert "Used in 1 sound" in det.text_content() and "Diwali offer" in det.text_content()
        det.locator("[data-a='vfav']").click()
        pg.wait_for_function("() => document.querySelector('#hvRoot .hv-vdetail [data-a=vfav]').getAttribute('aria-pressed') === 'true'")
        assert st["favput"][-1] == {"id": "v_meera", "on": True}
        pg.locator("#hvView [data-a='vtab'][data-val='favs']").click()
        pg.wait_for_function("() => document.querySelectorAll('#hvView .hv-vrow').length === 1")
        assert "Meera" in pg.locator("#hvView .hv-vrow").text_content()
        pg.locator("#hvView [data-a='vtab'][data-val='hoola']").click()
        pg.locator("#hvView [data-a='vsel'][data-id='v_meera']").click()
        if shots:
            pg.screenshot(path=f"{shots}/lib-{scheme}-{width}-2-voice.png")
        # compare two voices: the tray, then the page; names hidden until she chooses
        det.locator("[data-a='vcmp']").click()
        pg.locator("#hvView [data-a='vsel'][data-id='v_lucia']").click()
        pg.locator("#hvRoot .hv-vdetail [data-a='vcmp']").click()
        pg.wait_for_selector("#hvView .hv-vtray")
        assert "2 voices to compare" in pg.locator("#hvView .hv-vtray").text_content()
        pg.locator("#hvView .hv-vtray [data-a='go'][data-arg='compare']").click()
        pg.wait_for_selector("#hvView .hv-cmpc")
        assert pg.locator("#hvView .hv-cmpc").count() == 2 and "Compare voices" in pg.locator("#hvRoot .hv-crumb").text_content()
        pg.locator("#hvView [data-a='cmpblind']").click()
        assert "Voice A" in pg.locator("#hvView").text_content() and "Meera" not in pg.locator("#hvView .hv-cmpg").text_content()
        if shots:
            pg.wait_for_timeout(600)
            pg.screenshot(path=f"{shots}/lib-{scheme}-{width}-3-compare.png")
        pg.locator("#hvView [data-a='cmppick'][data-id='v_lucia']").click()
        assert "Lucía" in pg.locator("#hvView .hv-cmpg").text_content()                                        # names back after the choice
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        # the picker on Speech: Recent and Favourites
        page_to(pg, "speech", width < 600)
        pg.locator("#hvRoot [data-a='vpopen']").first.click()
        pg.wait_for_selector("#hvVp .hv-vpr")
        tabs = pg.locator("#hvVpF").text_content()
        assert "Recent" in tabs and "Favourites" in tabs
        pg.locator("#hvVpF [data-val='Favourites']").click()
        pg.wait_for_function("() => document.querySelectorAll('#hvVpL .hv-vpr').length === 1")
        if shots:
            pg.screenshot(path=f"{shots}/lib-{scheme}-{width}-4-picker.png")
        assert not errs, errs
        ctx.close()
