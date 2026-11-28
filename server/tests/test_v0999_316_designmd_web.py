"""v0.999.316 DESIGN.md (front end): the design catalog under the Studio's chat box, one design's page, the design card
in the box, her own DESIGN.md checked first - walked in a real browser at computer and phone width, light and dark."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (ROOT / "webstudio.js").read_text()
CSS = (ROOT / "webstudio.css").read_text()
NO_SIDEWAYS = "document.documentElement.scrollWidth <= innerWidth + 1"


def test_the_pieces_are_wired():
    assert "${designSection()}" in JS and "loadDesigns();" in JS
    assert "if (p[0] === 'design' && p[1])" in JS and "openDesign(decodeURIComponent(p[1]))" in JS
    assert "...designBody()" in JS and JS.count("...designBody()") == 2                 # Build and Plan both carry it
    assert "design_look: DESIGN.id" in JS and "design_md: S(DESIGN.text)" in JS
    assert "sandbox=\"allow-same-origin\"" in JS and "allow-scripts" not in JS.split("wsDFrame")[1][:400]
    assert "else if (kind === 'dmd') await checkDesignMd(f);" in JS
    assert ".dcatalog{" in CSS and ".dth{" in CSS and "@media (max-width:760px)" in CSS


def _ctx(browser, key, w, h, scheme="light"):
    ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    return ctx


def test_catalog_design_page_and_the_box_in_a_browser(arena_server, site_env):
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    for scheme in ("light", "dark"):
        ctx = _ctx(browser, key, 1440, 900, scheme)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/console/web#/")
        page.wait_for_selector("#wsDGrid .dcard[href]", timeout=20000)
        # 11 drawn designs + the bring-your-own card, the chips, Show all
        assert page.locator("#wsDGrid a.dcard").count() == 11
        assert page.locator("#wsDGrid .dup").count() == 1
        assert page.locator("#wsDCats .chip").count() >= 8
        page.click("[data-dx='more']")
        assert page.locator("#wsDGrid a.dcard").count() == 84
        page.click("#wsDCats [data-v='fin']")
        n = page.locator("#wsDGrid a.dcard").count()
        assert 0 < n < 20 and page.locator("#wsDGrid .dup").count() == 0
        page.click("#wsDCats [data-v='all']")
        page.fill("#wsDQ", "midnight")
        page.wait_for_timeout(400)
        assert page.locator("#wsDGrid a.dcard").count() == 1
        # every drawn card paints its own colours (not the Studio's)
        bg = page.evaluate("getComputedStyle(document.querySelector('#wsDGrid .dth')).backgroundColor")
        assert bg == "rgb(1, 1, 2)", bg
        if shots:
            page.fill("#wsDQ", "")
            page.wait_for_timeout(400)
            page.locator("#wsDesigns").screenshot(path=f"{shots}/designs-{scheme}.png")
            page.fill("#wsDQ", "midnight")
            page.wait_for_timeout(400)
        page.click("#wsDGrid a.dcard")
        page.wait_for_selector(".dpage .dh1", timeout=20000)
        assert page.locator(".dh1").inner_text() == "Midnight product"
        fr = page.frame_locator("#wsDFrame")
        fr.locator("h1").wait_for(timeout=15000)
        assert "your own words" in fr.locator("h1").inner_text().lower()
        assert page.locator(".dnote").count() == 0                       # dark is its own mode
        page.click("[data-dx='mode'][data-v='light']")
        page.wait_for_selector(".dnote")
        assert "mode=light" in page.get_attribute("#wsDFrame", "src")
        page.click("[data-dx='dev'][data-v='phone']")
        assert page.evaluate("document.querySelector('#wsDFrame').getBoundingClientRect().width") <= 392
        if shots:
            page.screenshot(path=f"{shots}/design-page-{scheme}.png", full_page=False)
        page.click("[data-dx='tab'][data-v='md']")
        for _ in range(60):
            if page.locator("#wsDMd").inner_text().startswith("---"):
                break
            page.wait_for_timeout(250)
        assert page.locator("#wsDMd").inner_text().startswith("---")
        assert page.locator(".drules li").count() >= 3 and page.locator(".dsw2").count() == 6
        page.fill("#wsDPrompt", "Build a website for [your business] in the Midnight product look, please.")
        page.click(".dpromptc [data-dx='use']")
        page.wait_for_selector("#wsDChip .dattach", timeout=15000)
        assert "Midnight product" in page.locator("#wsDChip").inner_text()
        assert page.input_value("#wsAsk").startswith("Build a website for [your business] in the Midnight")
        assert page.evaluate("document.activeElement.id") == "wsAsk"
        # the design rides the send; a refusal keeps her words AND the design card
        sent = {}

        def stop(route):
            sent["body"] = json.loads(route.request.post_data or "{}")
            route.fulfill(status=400, content_type="application/json", body=json.dumps({"detail": "Stopped by the test."}))
        page.route("**/api/sites", lambda r: stop(r) if r.request.method == "POST" else r.continue_())
        page.fill("#wsAsk", "A website for Sharma Sweets in this look")
        page.keyboard.press("Enter")
        page.wait_for_selector("#wsAskWork .bad", timeout=20000)
        assert sent["body"]["design_look"] == "linear-app" and sent["body"]["brief"].startswith("A website for Sharma")
        assert page.locator("#wsDChip .dattach").count() == 1
        page.click("[data-dx='clear']")
        assert page.locator("#wsDChip .dattach").count() == 0
        # her own DESIGN.md: checked first, then in the box
        page.click("form.ask [data-dx='mdopen']")
        page.wait_for_selector("form[data-form='dmd']")
        page.click("form[data-form='dmd'] summary")
        page.fill("form[data-form='dmd'] textarea", "---\nname: Mine\ncolors:\n  primary: \"#0a7c42\"\n  canvas: \"#fffdf7\"\n---\n## Colors\nGreen.\n## Overview\nCalm.\n")
        page.click("form[data-form='dmd'] [type=submit]")
        page.wait_for_selector("form[data-form='dmd'] [data-dx='mduse']", timeout=15000)
        assert "section" in page.locator("form[data-form='dmd'] .dlint").inner_text().lower()   # out of order, said
        page.click("[data-dx='mduse']")
        page.wait_for_selector("#wsDChip .dattach")
        assert "Mine" in page.locator("#wsDChip").inner_text() and "your file" in page.locator("#wsDChip").inner_text()
        ctx.close()
    # phone: two cards a row, no sideways scroll, the design page stacks
    ctx = _ctx(browser, key, 390, 820)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/console/web#/")
    page.wait_for_selector("#wsDGrid .dcard[href]", timeout=20000)
    assert page.evaluate(NO_SIDEWAYS), page.evaluate("[document.documentElement.scrollWidth, innerWidth]")
    tops = page.evaluate("[...document.querySelectorAll('#wsDGrid .dcard')].slice(0,3).map(e => Math.round(e.getBoundingClientRect().top))")
    assert tops[0] == tops[1] != tops[2], tops
    if shots:
        page.locator("#wsDesigns").screenshot(path=f"{shots}/designs-phone.png")
    page.goto(base + "/console/web#/design/claude")
    page.wait_for_selector(".dpage .dh1", timeout=20000)
    page.wait_for_timeout(400)
    assert page.evaluate(NO_SIDEWAYS), page.evaluate("[document.documentElement.scrollWidth, innerWidth]")
    ctx.close()
    assert not errors, errors
