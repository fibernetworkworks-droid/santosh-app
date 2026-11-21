"""v0.999.29 QUALITY EVERYWHERE (owner: "NOW CHECK EVERY CHAT PANEL ... HAS THIS LLM RANGE OR NOT" -> the audit -> "GO BUILD
1 AND 2"): 1. the chat's quality tier (Normal / Ultra asks first / High / Medium / Low) and her credits under the typing
box of Web Studio (home, a site's thread, the plan, React apps), App Studio (home, an app's thread), Game Dev (home, a
game's thread), Hoola Design (Ask Hoola), Hoola Auto (each agent), and on the phone in Hoola Code sessions, Notebook,
the Guru tutor and Hoola Auto agents; 2. no rupees there: Web Studio's turn cost and Hoola Auto's costs and caps show
credits (the server's rupee rate for a credit rides GET /api/credits). Left out on purpose (her decisions): Hoola
Computer, the voice call, the media studios, AI Apps."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
LIB = ROOT / "lib/ui"


def _r(p):
    return (CON / p).read_text()


# ------------------------------------------------------------------------------------------------ the console piece
def test_one_piece_carries_the_chats_five_and_credits_and_no_rupees():
    q = _r("quality.js")
    assert "ROWS = ['', 'ultra', 'high', 'medium', 'low']" in q and "'/api/model/tier'" in q and "'/api/credits?country='" in q
    assert "Recommended" in q and "⚠ Up to 70× credit" in q and "🔒 Buy credits" in q and "Use Ultra?" in q
    assert "confirm_ultra: id === 'ultra'" in q and "free today" in q and " credits`" in q
    assert "Rs " not in q and "rs_step" not in q and "₹" not in q


def test_every_studio_loads_it_and_starts_it():
    for page in ("webstudio.html", "appstudio.html", "gamedev.html", "hoolacode.html", "design/design.html"):
        assert '/static/console/quality.js?v=' in _r(page), page
    for mod in ("webstudio.js", "appstudio.js", "gamedev.js", "hoolacode.js"):
        assert "window.HoolaQuality?.use(api);" in _r(mod), mod
    assert "window.HoolaQuality?.use(" in _r("design/hd-ui.js")


def test_a_spot_under_every_typing_box():
    ws, aps, gd = _r("webstudio.js"), _r("appstudio.js"), _r("gamedev.js")
    assert ws.count("data-hoola-quality") == 2 and "'Change anything in the plan…', quality: true" in ws    # home, thread, plan
    assert "'Tell Hoola what to change…', quality: true" in _r("appengine.js")                             # React apps
    assert aps.count("data-hoola-quality") == 2                                                              # home, thread
    assert gd.count("data-hoola-quality") == 1 and "'Ask Hoola for a change…', quality: true" in gd          # home, thread
    assert "or tell it what to change`, quality: true" in _r("hoolaauto.js")                                # every agent
    assert "'data-hoola-quality': ''" in _r("design/hd-ai.js")                                              # Ask Hoola
    kit = _r("chatkit.js")
    assert "if (o.quality && !host.nextElementSibling?.classList.contains('hck-under'))" in kit
    for left_out in ("computer.js", "aiapps.js"):                                                            # her decisions
        assert "quality: true" not in _r(left_out) and "data-hoola-quality" not in _r(left_out)


def test_no_rupees_in_web_studio_or_hoola_auto():
    ws = _r("webstudio.js")
    assert "'Rs ' + v.toFixed" not in ws and "' credits')" in ws and "(Number(x.usd) || 0) * 1000" in ws
    au = _r("hoolaauto.js")
    assert "const rs = n => credits(n).toLocaleString('en-US') + ' credits';" in au
    assert "Cost cap (credits)" in au and "Cost cap (Rs)" not in au and "{cap_inr: Math.round(v * RATE)}" in au
    assert "inr_per_credit" in au


def test_the_credits_overview_gives_the_rupee_rate(env, monkeypatch):
    monkeypatch.setenv("CREDITS_ON", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import usage
    from app.main import app
    body = TestClient(app).get("/api/credits?country=IN").json()
    assert abs(body["inr_per_credit"] - usage.usd_inr() * 0.001) < 1e-4
    get_settings.cache_clear()


# ------------------------------------------------------------------------------------------------ the phone
def test_the_phone_screens_carry_the_row_and_no_model_or_rupees():
    q = (LIB / "shell/hoola_quality.dart").read_text()
    assert "class HoolaQualityRow" in q and "HoolaQualityChip(app: widget.app)" in q and "HoolaCreditsPage(app: widget.app)" in q
    assert "String hoolaCreditsOf(dynamic inr)" in q and "v['inr_per_credit']" in q
    for f in ("code/code_session.dart", "notebook_screen.dart", "guru_screen.dart", "hoola_auto.dart"):
        assert "HoolaQualityRow(app: widget.app)" in (LIB / f).read_text(), f
    assert "model_label" not in (LIB / "code/code_session.dart").read_text()
    au = (LIB / "hoola_auto.dart").read_text()
    assert "hcS(sess['model'])" not in au and "String _rs(dynamic v) => hoolaCreditsOf(v);" in au and "'Rs " not in au


# ------------------------------------------------------------------------------------------------ in a real browser
def test_the_studios_show_it_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs, puts = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    T = {"available": True, "selected": "high", "locked": False}

    def tier(r):
        if r.request.method == "PUT":
            puts.append(r.request.post_data_json); T["selected"] = r.request.post_data_json["tier"]
        r.fulfill(json=T)
    pg.route("**/api/model/tier", tier)
    pg.route("**/api/credits?**", lambda r: r.fulfill(json={"wallet": {"on": True, "exempt": False, "unlocked": True, "paid_left": 4820,
                                                                         "plan": "plus", "plan_name": "Plus", "plan_left": 4820},
                                                              "prices": {"plans": [{"id": "plus", "credits": 5400}]}}))
    shots = os.environ.get("HOOLA_SHOTS")
    for url, name in (("/console/web", "web"), ("/console/apps", "apps"), ("/console/games", "games")):
        pg.goto(base + url)
        pg.wait_for_selector(".hq-btn", timeout=20000)
        assert pg.locator(".hq-btn").first.text_content() == "High", url
        assert pg.locator(".hq-cr").first.text_content() == "4,820 credits", url
        pg.locator(".hq-btn").first.click()
        pg.wait_for_selector(".hq-menu.on")
        rows = [x.split("Recommended")[0].split("⚠")[0].strip() for x in pg.locator(".hq-menu .hq-mi").all_text_contents()]
        assert rows == ["Normal", "Ultra", "High", "Medium", "Low"], (url, rows)
        assert "Rs" not in pg.locator(".hq-menu").text_content()
        if shots:
            pg.wait_for_timeout(250); pg.screenshot(path=os.path.join(shots, f"q29-{name}.png"))
        pg.keyboard.press("Escape")
    pg.locator(".hq-btn").first.click()
    pg.locator(".hq-menu .hq-mi", has_text="Ultra").click()                                     # Ultra asks first
    pg.wait_for_selector(".hq-menu.on >> text=Use Ultra?")
    pg.locator(".hq-menu .hq-b.pri").click()
    pg.wait_for_function("() => document.querySelector('.hq-btn').textContent === 'Ultra'")
    assert puts[-1] == {"tier": "ultra", "confirm_ultra": True}
    assert not errs, errs
    ctx.close()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.80"
