"""v0.743 SAAF INSAANI - the console keeps its design and talks like a person (owner: "DO NOT CHANGE EXISTING DESIGN BUT
MAKE IT MORE USER FRIENDLY AND HUMAN MADE NATIVE" -> GO on the canvas)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def test_switch_reaches_the_console(env, monkeypatch):
    from app.config import get_settings
    from app import main
    c = TestClient(main.app)
    assert c.get("/api/console/config").json()["human"] is False          # conftest pins the old wording
    monkeypatch.setenv("CONSOLE_HUMAN", "true"); get_settings.cache_clear()
    assert c.get("/api/console/config").json()["human"] is True
    monkeypatch.delenv("CONSOLE_HUMAN"); get_settings.cache_clear()
    assert get_settings().console_human is True                          # default on


def test_the_old_words_stay_when_off_and_the_new_ones_are_there():
    js = (CON / "v2.js").read_text()
    for old in ("'Slide for Haan'", "'Mana'", "'Retry'", "'✅ What was done'", "Ask anything, attach a file"):
        assert old in js, old                                              # off = byte-for-byte the old console
    for new in ("Good afternoon", "waiting for your OK", "need${QUEUE.length === 1 ? 's' : ''} you", " of ${money(",
                "'Ask again'", "Good answer", "Not right", "Slide to approve", "Not now",
                "Nothing happens until you approve.", "For example:", "min so far"):
        assert new in js, new
    css = (CON / "v2.css").read_text()
    assert "html.human #app .pill svg{stroke:var(--pri)}" in css          # one-colour start icons
    assert "ae-role-n" in (CON / "employees.js").read_text()               # what a role needs, on its card


def test_home_reads_like_a_person_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    started = (datetime.now(timezone.utc) - timedelta(minutes=6, seconds=10)).isoformat()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def config(route):
        r = route.fetch(); d = r.json(); d["human"] = True
        route.fulfill(response=r, body=json.dumps(d))

    def kaam(route):
        route.fulfill(json={"jobs": [{"state": "working", "title": "Bakery website", "label": "Website",
                                      "stage": "Writing the price list", "pct": -1, "started_at": started,
                                      "conversation_id": ""}]})
    pg.route("**/api/console/config", config)
    pg.route("**/api/kaam", kaam)
    pg.goto(base + "/console/")
    for _ in range(80):
        if "working on one job" in (pg.locator(".tagline").text_content() or ""):
            break
        pg.wait_for_timeout(100)
    assert pg.evaluate("document.documentElement.classList.contains('human')")
    assert "working on one job for you right now" in pg.locator(".tagline").text_content()
    g = pg.locator("#greet").text_content()
    assert g.startswith(("Good morning", "Good afternoon", "Good evening")), g
    card = pg.locator("#jobGrid .job").first.text_content()
    assert "Writing the price list" in card and "6 min so far" in card and "Working" in card, card
    assert pg.locator("#jobGrid .jbar").count() == 0                       # no made-up progress bar
    assert "1 working" in pg.locator("#snav").text_content()
    assert "For example" in (pg.locator("#msg").get_attribute("placeholder") or "")
    assert not errs, errs
    ctx.close()
