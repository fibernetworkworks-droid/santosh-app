"""v0.999.78 GET THE NUMBER (owner: "IN FRONT OF EVERY PROVIDER SHOW A FLOW PROPERLY WITHOUT MISTAKE --- A ICON NAME GET
THE NUMBER --- FOR EVERY PROVIDER").

Every phone company has a guide; the keys its steps tell her to copy are EXACTLY the keys Hoola asks for; every Hoola
address a step shows is that company's own webhook; the console and phone draw a Get the number button per company.
"""
from pathlib import Path

from app.callcentre import numberguide as NG
from app.callcentre import providers as P
from app.callcentre import rules as R

ROOT = Path(__file__).resolve().parents[2]


def test_every_company_has_a_guide():
    assert set(NG.GUIDE) == set(R.PROVIDERS)
    for k, g in NG.GUIDE.items():
        assert g["steps"], k
        if k != "fake":
            assert g["site"].startswith("https://") and g["console"].startswith("https://"), k


def test_guide_keys_are_exactly_hoolas_keys():
    for k, g in NG.GUIDE.items():
        if k == "fake":
            continue
        named = [n for st in g["steps"] if len(st) > 3 for n in st[3]]
        assert sorted(named) == sorted(n for n, _ in P.KEYS[k]), k       # nothing missing, nothing invented


def test_every_company_points_its_number_at_hoola():
    for k, g in NG.GUIDE.items():
        if k == "fake":
            continue
        copied = {c for st in g["steps"] if len(st) > 2 for c in st[2]}
        assert "answer" in copied or {"stream_url_endpoint", "after", "connect"} <= copied, k


def test_addresses_are_that_companys_own(env, monkeypatch):
    from app.callcentre import service as S
    monkeypatch.setattr(S._st(), "public_base_url", "https://hoola.example")
    st = S.settings("t-guide")
    for k in R.PROVIDERS:
        g = st["providers"][k]["guide"]
        for step in g["steps"]:
            for c in step["copy"]:
                assert f"/hook/{k}/" in c["value"], (k, c)
                assert c["label"]
    tw = st["providers"]["twilio"]["guide"]
    assert tw["steps"][-1]["title"] == "Test it"
    keys = next(s for s in tw["steps"] if s["keys"])["keys"]
    assert keys == ["Account SID", "Auth Token"]                         # the labels she sees in Hoola's key boxes


def test_console_and_phone_draw_the_button():
    js = (ROOT / "server/app/static/console/telecallerdesk.js").read_text()
    assert "Get the number" in js and "data-guide" in js and "openGuide" in js and "data-gcopy" in js
    html = (ROOT / "server/app/static/console/telecallerdesk.html").read_text()
    assert 'id="tcGuide"' in html
    dart = (ROOT / "lib/ui/callcentre_screen.dart").read_text()
    assert "Get the number" in dart and "_guide(" in dart


from tests.test_v0999_67_ai_telecaller import cc, tc_server  # noqa: E402,F401 - the desk's real-browser server


def test_get_the_number_window_in_a_real_browser(tc_server):
    import os
    base, browser, key, _ = tc_server
    from app.config import get_settings
    get_settings().public_base_url = base
    errors = []
    for width in (1440, 390):
        ctx = browser.new_context(viewport={"width": width, "height": 900})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/telecaller#/settings")
        pg.wait_for_function("() => document.querySelector('#tcPage').innerText.includes('Get a phone number')", timeout=20000)
        n = pg.evaluate("document.querySelectorAll('#tcPage tbody [data-guide]').length")
        assert n == len(R.PROVIDERS), n                                   # one button in front of every company
        for k in ("plivo", "exotel", "twilio", "jambonz"):
            pg.click(f"#tcPage tbody [data-guide='{k}']")
            pg.wait_for_selector("#tcGuide[open]")
            txt = pg.inner_text("#tcGuide")
            assert "Get the number" in txt and "Test it" in txt, txt[:300]
            assert pg.evaluate("[...document.querySelectorAll('#tcGuide code')].every(c => c.innerText.includes('/hook/'))")
            if os.environ.get("HOOLA_SHOTS"):
                pg.screenshot(path=f"{os.environ['HOOLA_SHOTS']}/guide_{k}_{width}.png")
            pg.click("#tcGuide [data-gclose]")
            pg.wait_for_selector("#tcGuide:not([open])", state="attached")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        ctx.close()
    assert not errors, errors
