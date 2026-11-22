"""v0.999.33 WIRED (owner: "NOW CHECK DOES EVERY THING IS WIRE PROPERLY OR NOT" after v0.999.29): the wiring check found
(1) the credits under every box were read once, when a page opened - they never went down as Hoola worked (console
studios, Hoola Code, the phone's rows); now they are read again when she comes back to the page and every minute, and a
redraw never pulls the button out from under an open menu; (2) three places still showed AI spend in rupees - App
Studio's Health 'AI cost (30 days)', a Hoola Code session's 'Cost so far', Hoola Code's 'Usage this month' - now credits,
at the server's own rupee rate for a credit (her shop's sales and delivery fees stay rupees: that is real money);
(3) every studio's browser test now checks the tier + credits under ITS typing box from the server's real routes, and a
pick there is the tier the server runs her work on (tests/_hq_wiring.py)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
LIB = ROOT / "lib/ui"
TESTS = ROOT / "server/tests"


def _r(p):
    return (CON / p).read_text()


def test_the_console_piece_reads_her_credits_again():
    q = _r("quality.js")
    assert "addEventListener('focus', fresh)" in q and "document.addEventListener('visibilitychange', fresh)" in q
    assert "setInterval(fresh, 60000)" in q and "Date.now() - LAST < 20000" in q and "LAST = Date.now()" in q
    assert "if (MENU) { LATER = true; return; }" in q and "if (LATER) draw();" in q          # never under an open menu


def test_hoola_code_reads_her_credits_again():
    c = _r("code.js")
    assert "addEventListener('focus', qFresh)" in c and "setInterval(qFresh, 60000)" in c and "Q_AT = Date.now();" in c
    assert "if (document.querySelector('.hmenu')) return;" in c


def test_the_phone_row_reads_her_credits_again():
    q = (LIB / "shell/hoola_quality.dart").read_text()
    assert "Timer.periodic(const Duration(seconds: 60), (_) => _fresh())" in q and "_tick?.cancel();" in q
    assert "_hoolaWalletAt = DateTime.now();" in q and "inSeconds >= 30" in q and "import 'dart:async';" in q


def test_ai_spend_is_credits_everywhere_left():
    q = _r("quality.js")
    assert "function credits(inr)" in q and "RATE = +c.inr_per_credit" in q and "return {mount, refresh, use, credits," in q
    assert "HoolaQuality.credits(cost.inr)" in _r("appstudio.js")
    c = _r("code.js")
    assert "const rs = n => 'Rs '" not in c and "if (+c?.inr_per_credit > 0) RATE = +c.inr_per_credit;" in c
    assert "inr(h.sales)" in _r("appstudio.js")                                              # her shop's money stays rupees


def test_every_studio_browser_test_checks_its_own_box():
    want = {"test_chatkit_webstudio.py": ['quality_under(page, "#wsTh")', 'pick_low(page, "#wsTh", hq_t)',
                                          'quality_under(page, "#wsAsk")', 'quality_under(page, "#wsRev")',
                                          'quality_under(page, "#aeBar")'],
            "test_chatkit_appstudio_gamedev.py": ['quality_under(pg, "form[data-form=thread]")', 'quality_under(w.pg, "#gdvBar")'],
            "test_chatkit_code_auto.py": ['quality_under(pg, "#hcaBar")'],
            "test_chatkit_small_panels.py": ['quality_under(pg, ".hdai-foot")']}
    for f, needles in want.items():
        s = (TESTS / f).read_text()
        for n in needles:
            assert n in s, (f, n)
    h = (TESTS / "_hq_wiring.py").read_text()
    assert "W.grant(t, \"topup\"" in h and "tiers.set_tier(t, tier)" in h and "assert tiers.chosen(tenant) == \"low\"" in h


def test_every_page_loads_the_piece_before_the_script_that_starts_it():
    """Hoola Design started it before the page had loaded it: the spot under Ask Hoola stayed empty."""
    for page, starter in (("webstudio.html", "webstudio.js"), ("appstudio.html", "appstudio.js"), ("gamedev.html", "gamedev.js"),
                          ("hoolacode.html", "hoolacode.js"), ("design/design.html", "design/hd-ui.js")):
        html = _r(page)
        q, st = html.index("/static/console/quality.js?v="), html.index("/static/console/" + starter + "?v=")
        assert q < st, (page, "quality.js must load before " + starter)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.140"
