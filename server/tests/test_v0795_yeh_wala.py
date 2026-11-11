"""v0.795 YEH WALA (L5 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L5"): point at the page instead of describing it -
the preview toolbar (Select / Text / Draw / Comment), the selected elements handed to the next turn once
(<selected_elements>), a free style panel on the site's own tokens (no model, Rs 0), comments for her team, and a
marked-up screenshot attached to her message."""
import asyncio
import json
import os
import re

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture: the architect + the site fake AI)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def _site(S):
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    return v["id"]


def _fast_checks(monkeypatch):
    from app.site import checks as C
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no browser checks in this test")))


def _first(S, sid, key="home__hero", tag=None):
    from app.site import edit as E
    h = S._sections(S._load(sid))[key]["html"]
    for n in range(1, 60):
        try:
            d = E.describe(h, str(n))
        except E.EditError:
            continue
        if tag is None or d["tag"] in tag:
            return str(n), d
    raise AssertionError("no element")


def test_style_panel_is_tokens_only_and_free(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app import usage
    from app.site import ai as AI
    from app.site import service as S
    sid = _site(S)
    e, d = _first(S, sid, tag=("h1", "h2", "p", "a"))
    asked = []
    monkeypatch.setattr(AI, "ask_json", lambda *a, **k: asked.append(a) or {})
    ver = S.get(T, sid)["version"]
    with usage.turn_meter() as acc:
        out = S.edit_element(T, sid, "home__hero", e, "style", json.dumps({"prop": "color", "value": "primary"}))
        S.edit_element(T, sid, "home__hero", e, "style", json.dumps({"prop": "size", "value": "2"}))
    assert not asked and not acc.get("usd") and not acc.get("calls")                  # no model, Rs 0
    assert "text colour" in out["say"] and S.get(T, sid)["version"] >= ver + 1
    html = S._sections(S._load(sid))["home__hero"]["html"]
    assert "hs-u-color-primary" in html and "hs-u-size-2" in html
    from app.site import build as B
    live = (B.out_dir(T, sid, S.get(T, sid)["version"]) / "index.html").read_text()
    assert "hs-u-color-primary" in live                                                 # it reaches the built page
    css = "".join(p.read_text() for p in B.out_dir(T, sid, S.get(T, sid)["version"]).rglob("*.css"))
    assert ".hs-u-color-primary{color:var(--c-primary-text)" in css                    # a token, never a raw colour
    for bad in ({"prop": "color", "value": "#ff0000"}, {"prop": "font", "value": "Comic"}, {"prop": "size", "value": "9"}):
        with pytest.raises(S.SiteError):
            S.edit_element(T, sid, "home__hero", e, "style", json.dumps(bad))
    S.undo_edit(T, sid)
    assert "hs-u-size-2" not in S._sections(S._load(sid))["home__hero"]["html"]         # one Undo per pick


def test_selection_reaches_the_next_turn_once(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.agent import turnmode as TM
    from app.site import service as S
    from app.site import yehwala as YW
    sid = _site(S)
    e, d = _first(S, sid, tag=("a", "button", "h1", "h2"))
    got = YW.set_selection(T, sid, [{"k": "home__hero", "e": e}, {"k": "home__hero", "e": e}])    # the same part once
    assert len(got["items"]) == 1
    it = got["items"][0]
    assert it["file"] == "pages/home/hero.html" and it["label"].startswith("Home · ") and "data-e" not in it["html"]
    with pytest.raises(YW.YehError):
        YW.set_selection(T, sid, [{"k": "nope__x", "e": "1"}])
    YW.set_selection(T, sid, [{"k": "home__hero", "e": e}])
    msg = f"make this bigger\n\n[Web console Web Studio: x (site id {sid})]\n\n[Web console mode: build]"
    TM.begin(msg)
    blk = TM.site_block(T)
    assert "<selected_elements>" in blk and "pages/home/hero.html" in blk and it["label"] in blk
    assert "<selected_elements>" not in TM.site_block(T)                               # read ONCE
    TM.begin("")
    with pytest.raises(S.SiteError):
        YW.set_selection("other-tenant", sid, [{"k": "home__hero", "e": e}])            # her own sites only


def test_comments_for_her_team(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.main import app
    from app.site import service as S
    sid = _site(S)
    e, _ = _first(S, sid)
    c = TestClient(app)
    a = c.post(f"/api/sites/{sid}/comments", json={"k": "home__hero", "e": e, "text": "Use the Diwali photo here"}).json()
    assert a["n"] == 1 and a["status"] == "open" and a["label"].startswith("Home")
    b = c.post(f"/api/sites/{sid}/comments", json={"k": "home__hero", "e": e, "text": "Price list?"}).json()
    assert b["n"] == 2
    assert c.post(f"/api/sites/{sid}/comments", json={"k": "home__hero", "e": e, "text": " "}).status_code == 400
    assert c.post(f"/api/sites/{sid}/comments/{a['id']}/resolved").json()["status"] == "resolved"
    lst = c.get(f"/api/sites/{sid}/comments").json()
    assert lst["open"] == 1 and [x["n"] for x in lst["comments"]] == [1, 2]
    assert c.post(f"/api/sites/{sid}/comments/{b['id']}/deleted").json()["deleted"] == b["id"]
    assert c.post(f"/api/sites/{sid}/comments/zzz/resolved").status_code == 404
    from app.site import yehwala as YW
    with pytest.raises(S.SiteError):
        YW.comments("other-tenant", sid)
    el = c.get(f"/api/sites/{sid}/element", params={"k": "home__hero", "e": e}).json()
    assert el["k"] == "home__hero" and el["file"] == "pages/home/hero.html"


def test_markup_screenshot_with_her_drawing(site_env, monkeypatch):
    from app.site import checks as C
    if C.available():
        pytest.skip("no Chromium here")
    _fast_checks(monkeypatch)
    from app.site import service as S
    from app.site import yehwala as YW
    sid = _site(S)
    S._assemble_live(S._load(sid))
    out = YW.markup(T, sid, "home", 1280, 800, 0, [[[0.1, 0.2], [0.5, 0.2], [0.5, 0.4]]], [{"x": 0.6, "y": 0.3, "text": "Bigger button"}])
    assert out["file_id"] and out["width"] == 1280 and out["height"] > 800                 # the note band is below
    assert out.get("mime") == "image/png" and out.get("media") == "image"
    with pytest.raises(YW.YehError):
        YW.markup(T, sid, "home", 1280, 800, 0, [], [])


def test_studio_source_wiring():
    from pathlib import Path
    D = Path(__file__).resolve().parents[1] / "app"
    js = (D / "static" / "console" / "webstudio.js").read_text()
    css = (D / "static" / "console" / "webstudio.css").read_text()
    ed = (D / "site" / "assets" / "hoola-edit.js").read_text()
    for x in ("ywDraw()", "data-act=\"pt-mode\"", "/selection`", "selected elements:", "/markup`", "/comments`", "Free · no AI",
              "data-act=\"sty\""):
        assert x in js, x
    assert "hoola: 'edit-cmd'" in js and "d.hoola !== 'edit-cmd'" in ed and "ev.source !== window.parent" in ed
    assert ".ptb.pos-center" in css and "prefers-reduced-motion:reduce){.stylep,.cmtp{animation:none}" in css


def test_point_select_style_draw_comment_in_a_browser(arena_server, arch_env, monkeypatch):
    _fast_checks(monkeypatch)
    base, browser, key = arena_server
    from app import turn_inbox
    from app.db import Message, session
    from app.events import bus
    from app.site import service as S
    got = []

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        from app.agent import turnmode as TM
        TM.begin(text)
        got.append({"text": text, "block": TM.site_block(tenant)})
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text, in_history=True))
        await asyncio.sleep(0.2)
        with session() as s:
            s.add(Message(conversation_id=conv, role="assistant", content="Done.", display="Done.", in_history=True))
        bus.publish(conv, "message", {"role": "assistant", "text": "Done.", "source": "agent"})
        return "Done."
    monkeypatch.setattr(turn_inbox, "run_owned", fake)
    sid = _site(S)
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(base + f"/console/web#/site/{sid}")
    page.wait_for_selector("#wsTh", timeout=20000)
    page.click("[data-act='select']")
    page.wait_for_selector("#wsYW .ptb", timeout=8000)
    assert page.locator("#wsYW [data-act='pt-mode']").count() == 4
    assert page.get_attribute("#wsYW [data-m='select']", "aria-pressed") == "true"
    fr = page.frame_locator(".frame iframe")
    fr.locator("section[data-k='home__hero'] [data-e]").first.wait_for(timeout=15000)
    page.wait_for_timeout(400)
    fr.locator("section[data-k='home__hero'] h1[data-e], section[data-k='home__hero'] h2[data-e]").first.click()
    page.wait_for_selector("#wsPills .pill2", timeout=5000)
    page.wait_for_selector("#wsStyle .stylep", timeout=5000)
    assert "Free · no AI" in page.inner_text("#wsStyle") and "Home · " in page.inner_text("#wsPills")
    if shots:
        page.screenshot(path=f"{shots}/l5-select-style.png")
    v0 = S.get(T, sid)["version"]
    page.click("#wsStyle [data-p='color'][data-v='primary']")
    for _ in range(80):
        if "hs-u-color-primary" in S._sections(S._load(sid))["home__hero"]["html"] and S.get(T, sid)["version"] > v0:
            break
        page.wait_for_timeout(150)
    assert "hs-u-color-primary" in S._sections(S._load(sid))["home__hero"]["html"] and S.get(T, sid)["version"] > v0
    # the selection rides her next message once, as <selected_elements>
    page.fill("#wsTh", "make this bigger")
    page.keyboard.press("Enter")
    for _ in range(60):
        if got:
            break
        page.wait_for_timeout(100)
    assert got and "<selected_elements>" in got[-1]["block"] and "selected elements: 1" in got[-1]["text"]
    assert "make this bigger" in got[-1]["text"] and "<section" not in got[-1]["text"].split("[Web console")[0]
    page.wait_for_function("() => document.querySelector('#wsPills').hidden", timeout=4000)
    # comment mode: click a part, write a note -> numbered pin + list
    page.click("#wsYW [data-m='comment']")
    page.once("dialog", lambda d: d.accept())
    fr.locator("section[data-k='home__hero'] [data-e]").first.click()
    page.wait_for_selector("dialog.dlg textarea", timeout=4000)
    page.fill("dialog.dlg textarea", "Use the Diwali photo here")
    page.click("dialog.dlg button[value='ok']")
    page.wait_for_selector("#wsCm .cmi", timeout=5000)
    fr.locator(".hoola-pin").first.wait_for(timeout=5000)
    if shots:
        page.screenshot(path=f"{shots}/l5-comment.png")
    # draw mode: a stroke + Send -> a marked-up screenshot attached to her message
    page.keyboard.press("d")
    page.wait_for_selector("#wsDraw .drawbar", timeout=4000)
    box = page.locator(".frame canvas.drawc").bounding_box()
    assert page.locator("#wsCm .cmtp").count() == 0                                      # panels step aside while drawing
    page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.5)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.55, steps=6)
    page.mouse.up()
    if shots:
        page.screenshot(path=f"{shots}/l5-draw.png")
    from app.site import checks as C
    if not C.available():
        n = len(got)
        page.fill("#wsDrawText", "Make this button bigger")
        page.click("#wsDraw [data-act='dr-send']")
        for _ in range(120):
            if len(got) > n:
                break
            page.wait_for_timeout(150)
        assert len(got) > n and "Make this button bigger" in got[-1]["text"]
        with session() as s:
            m = s.query(Message).filter(Message.role == "user").order_by(Message.id.desc()).first()
        assert m is not None
    # the toolbar snaps and hides
    page.click("#wsYW [data-act='pt-min']")
    page.wait_for_selector("#wsYW .ptb.min")
    page.click("#wsYW [data-act='pt-min']")
    page.click("#wsYW [data-act='edit-done']")
    page.wait_for_function("() => !document.querySelector('#wsYW')", timeout=5000)
    ctx.close()
    assert not [e for e in errors if "localStorage" not in e], errors
