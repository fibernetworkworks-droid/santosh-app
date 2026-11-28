"""v0.999.297 ROUTE HOME REDESIGN (owner: design canvas claude.ai/artifact/5Dnd2VzFM6euExAUs8jf4d -> "GO BUILD THE DESIGN").

The Route home as designed: a greeting in her time of day with one plain line of where things stand, the ask box with its
three ways in and three examples to try, one band of this week's numbers (with last week and a trend line from the server),
her routes beside what needs her and what runs next, templates; a first day shows the three steps instead of empty numbers.
The sidebar is grouped (Build, Data and accounts) and its foot shows today's runs hour by hour.
"""
import time

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0999_232_route_editor import BASE, _client, _open, _ready, _run, _wipe, br  # noqa: F401

from app.agent import dhara_tools as D
from app.agent.tools import Ctx


def test_summary_carries_last_week_and_the_hours(bz):
    c, t = _client()
    _wipe(t)
    try:
        ctx = Ctx(tenant_id=t, conversation_id="")
        _run(D.dhara_save(ctx, name="weekly_one", steps=[{"id": "n", "type": "notify", "text": "hi"}]))
        wf = D.get_workflow(t, name="weekly_one")
        _run(D.execute_run(t, D.create_run(t, wf)))
        con = D._con(t)       # one run from last week
        try:
            con.execute("UPDATE runs SET created_at = ?", (time.time() - 9 * 86400,))
            con.commit()
        finally:
            con.close()
        _run(D.execute_run(t, D.create_run(t, wf)))
        s = c.get("/api/route/summary").json()
        assert s["runs_7d"] == 1 and s["runs_prev_7d"] == 1
        assert len(s["week_days"]) == 7 and s["week_days"][-1] == 1 and sum(s["week_days"]) == 1
        assert len(s["hours12"]) == 12 and s["hours12"][-1] == 1
        assert s["failed_30d"] == 0
    finally:
        _wipe(t)


def test_the_page_is_built_to_the_design():
    js, css, html = (BASE / "route.js").read_text(), (BASE / "route.css").read_text(), (BASE / "route.html").read_text()
    for part in ("rh-band", "rh-cols", "rh-need", "rh-tl", "rh-steps", "rh-try", "findForm", "FIND_KEY", "comingUp(", "trend(",
                 "What should run by itself?", "Bring in from n8n or Make", "Good morning", "sf-bars", 'class="stack"'):
        assert part in js, part
    for part in (".rh-band{", ".rh-cols{", ".rh-need{", ".rh-tl{", ".rh-steps{", ".rh-spark", ".sf-bars{", ".stack .ap + .ap"):
        assert part in css, part
    assert '<div class="sl">Build</div>' in html and '<div class="sl">Data and accounts</div>' in html
    assert "prompt(" not in js and "confirm(" not in js


def test_the_home_in_a_real_browser(br):
    base, b, key, t = br
    for w, h in ((1440, 900), (390, 844)):
        p, errs = _open(b, key, w, h)
        p.goto(base)
        _ready(p)
        txt = p.inner_text("#main")
        assert "What should run by itself?" in txt and "Runs this week" in txt and "Coming up" in txt and "Your routes" in txt
        assert p.locator(".rh-band .rh-cell").count() == 4
        assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"sideways scroll at {w}"
        p.click(".rh-ex >> nth=0")
        assert p.input_value("#askText").startswith("Every morning at 9") and p.is_enabled("#askGo")
        p.fill("#findQ", "order")
        p.press("#findQ", "Enter")
        p.wait_for_selector("#rq")
        assert p.input_value("#rq") == "order" and "order to sheet" in p.inner_text("#rtable")
        assert not errs, errs
        p.context.close()
    # a first day: the three steps instead of empty numbers
    _wipe(t)
    p, errs = _open(b, key, 1440, 900)
    p.goto(base)
    _ready(p)
    assert p.locator(".rh-steps .rh-step").count() == 3 and p.locator(".rh-band").count() == 0
    assert "Switch it on" in p.inner_text("#main")
    assert not errs, errs
    p.context.close()


def test_version():
    from app.main import APP_VERSION
    assert tuple(int(x) for x in APP_VERSION.split(".")) >= (0, 999, 297)
