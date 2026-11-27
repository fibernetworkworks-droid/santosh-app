"""TECHNICAL WRITER DESK: the Technical writer's own section, built like the finance desks - its own chat (kind 'docs') with the desk
block + the docs tools in view; products she connects (made in Hoola, her proved live site, GitHub read-only, her files); docs written
only from the product ([blank] for what it does not know) with checks; her own edits kept; Word / PDF / Markdown; publishing only by
her tap with the card hash; GLOBAL: docs in the languages of her users anywhere (right-to-left printed right to left, personal data
of any country covered), Hinglish only when she picks it; the GitHub token only in its own part; walked in a browser."""
from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

from tests.test_tech_docwriter import T, _make_app, dw   # noqa: F401


@pytest.fixture
def ddk(dw, monkeypatch):        # noqa: F811
    from app import dwchat as D
    D._OF.clear()
    D._BLOCK.clear()

    def fake_ai(system, prompt, max_tokens=2500):
        if "Cart" in prompt:
            return json.dumps({"title": "Your cart", "body": "Your cart shows what you picked.\n\n1. Tap **Order karo** to order."})
        return json.dumps({"title": "Home", "body": "The home screen of the shop.\n\n1. Tap **Dukaan kholo** to start."})
    monkeypatch.setattr(dw, "_ai", fake_ai)
    return D


def _hire():
    from app.employee import hire
    hire.hire(T, "docs_writer", trust="seekh")


def test_hire_chat_block_and_wiring(ddk):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert ddk.summary(T)["hired"] is False and "Hire me from AI Employees" in ddk.greeting(T)
    with pytest.raises(PermissionError):
        ddk.do(T, "write", {})
    _hire()
    d = ddk.summary(T)
    assert d["hired"] and "without your tap" in d["foot"]
    assert d["desk"]["needs"][0]["go"] == "sources"
    chat = ddk.current(T)
    assert ddk.is_docs(chat["id"]) and ddk.owns(T, chat["id"])
    assert "<docs_desk>" in ddk.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_dwc.is_docs(conversation_id)" in src and "adm.admit_families(_dwc.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"docs"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/docs")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "dwdesk.js" in r.text
    html = (root / "server/app/static/console/dwdesk.html").read_text()
    for x in ("chatkit.js", "ardesk.css", "dwdesk.css", "dwdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/docs')" in (root / "server/app/static/console/v2.js").read_text()
    assert "docs_writer: 'dwdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["docs_writer"]["desk"] == "dwdesk"
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["docs_writer"] in ddk.FAMILIES


def test_guards(ddk):
    _hire()
    tok = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2"
    with pytest.raises(PermissionError):
        ddk.do(T, "add_product", {"kind": "github", "ref": tok})              # a token never outside the GitHub part
    with pytest.raises(PermissionError):
        ddk.do(T, "settings", {"tone": "friendly", "token": tok})
    with pytest.raises(PermissionError):
        ddk.do(T, "flow", {"product": "x", "name": "Login", "steps": ["fill \"Password\" = x"], "device": "my password is hunter2"})
    ok = ddk.do(T, "settings", {"rules": ["Never say the password is required twice"]})   # her rules are data
    assert ok["rules"]
    with pytest.raises(ddk.DwDeskError):
        ddk.do(T, "nope", {})
    _make_app(T)
    p = ddk.do(T, "add_product", {"kind": "hoola_app", "ref": "A-0001"})["product"]
    d = ddk.do(T, "write", {"product": p["id"], "kind": "quickstart", "lang": "en"})["doc"]
    from app.employee import hire
    hire.pause(T, "docs_writer")
    assert ddk.do(T, "doc_get", {"doc": d["id"]})["number"] == d["number"]   # reads still work
    with pytest.raises(PermissionError):
        ddk.do(T, "write", {"product": p["id"], "kind": "faq"})


def test_write_edit_publish_by_tap(ddk):
    _hire()
    _make_app(T)
    p = ddk.do(T, "add_product", {"kind": "hoola_app", "ref": "A-0001"})["product"]
    out = ddk.do(T, "write", {"product": p["id"], "kind": "manual", "lang": "en", "words": "for shop owners"})
    v = out["doc"]
    assert v["kind"] == "manual" and len(v["section_list"]) == 2
    k = ddk.summary(T)["desk"]
    assert k["docs"][0]["id"] == v["id"] and ("User manual", 1) in k["by_kind"] and ("English", 1) in k["by_lang"]
    sec = v["section_list"][1]["id"]
    e = ddk.do(T, "edit", {"doc": v["id"], "section": sec, "body": "Your cart lists what you picked. Tap **Order karo**."})
    assert next(x for x in e["doc"]["section_list"] if x["id"] == sec)["by"] == "her"
    card = ddk.do(T, "publish", {"doc": v["id"], "dest": "page"})
    assert card["status"] == "needs_tap"
    k = ddk.summary(T)["desk"]
    assert k["waiting"] == 1 and any("waits for your tap" in n["say"] for n in k["needs"])
    with pytest.raises(ddk.DwDeskError):
        ddk.do(T, "decide", {"doc": v["id"], "hash": "x" * 64, "yes": True})
    r = ddk.do(T, "decide", {"doc": v["id"], "hash": card["card"]["hash"], "yes": True})
    assert r["ok"] and r["url"]
    got = ddk.do(T, "doc_get", {"doc": v["id"]})
    assert got["status"] == "published" and got["page"]
    files = ddk.do(T, "files", {"doc": v["id"], "formats": ["md", "docx"]})
    assert all(f.get("url") for f in files["files"])
    ddk.do(T, "unpage", {"doc": v["id"]})
    assert not ddk.do(T, "doc_get", {"doc": v["id"]})["page"]


def test_global_languages_and_privacy(ddk):
    from app.docwriter import rules as R
    _hire()
    for name, code in (("Spanish", "es"), ("arabic", "ar"), ("Japanese", "ja"), ("pt", "pt"), ("hinglish", "hinglish"), ("Chinese", "zh")):
        assert R.lang_of(name, "") == code, name
    s = ddk.do(T, "settings", {"langs": ["es", "en", "ar", "nonsense"]})
    assert s["langs"] == ["es", "en", "ar"]
    k = ddk.summary(T)["desk"]
    assert {"es", "ar", "hinglish", "ja"} <= {x["code"] for x in k["langs"]}
    _make_app(T)
    p = ddk.do(T, "add_product", {"kind": "hoola_app", "ref": "A-0001"})["product"]
    v = ddk.do(T, "write", {"product": p["id"], "kind": "quickstart"})["doc"]
    assert v["lang"] == "es"                                                  # her first language, not Hinglish
    a = ddk.do(T, "write", {"product": p["id"], "kind": "faq", "lang": "ar"})["doc"]
    from app.docwriter import service as S
    from app.docwriter.models import DocDoc
    from app.db import session
    with session() as s_:
        html = S.doc_html(T, s_.get(DocDoc, a["id"]))
    assert 'lang="ar" dir="rtl"' in html
    masked = R.mask_text("Call +44 20 7946 0958, +1 (415) 555-2671 or +91 98765 43210; version 2.4.1", ["help@shop.com"])
    assert masked.count("[removed]") == 3 and "2.4.1" in masked
    with pytest.raises(ddk.DwDeskError, match="Spanish"):
        ddk.do(T, "translate", {"doc": v["id"], "to": "klingon"})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def dw_server(ddk, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(ddk, dw_server):
    base, browser, key = dw_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []
    _make_app(T)

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/docs")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # settings: who reads, languages
    go(pg, "#/settings", "form[data-form=dwset]")
    pg.fill("form[data-form=dwset] [name=product_name]", "Sharma Kirana")
    pg.fill("form[data-form=dwset] [name=audience]", "Shop owners, first time with the app")
    pg.check("form[data-form=dwset] input[name=langs][value=es]")
    pg.click("form[data-form=dwset] [type=submit]")
    pg.wait_for_selector("#dwSite:has-text('Sharma Kirana')", timeout=20000)
    snap(pg, "dw-settings-1440")
    # sources: connect the app made in Hoola
    go(pg, "#/sources", "form[data-form=addprod]")
    pg.fill("form[data-form=addprod] [name=ref]", "A-0001")
    pg.click("form[data-form=addprod] [type=submit]")
    pg.wait_for_selector(".dw-prod", timeout=30000)
    snap(pg, "dw-sources-1440")
    # write a manual -> the doc opens with its sections and screenshot
    go(pg, "#/write", "form[data-form=write]")
    pg.click("label.dw-kind:has-text('User manual')")
    pg.select_option("form[data-form=write] [name=lang]", "en")
    pg.fill("form[data-form=write] [name=words]", "For shop owners who just signed up")
    snap(pg, "dw-write-1440")
    pg.click("form[data-form=write] [type=submit]")
    pg.wait_for_selector("details.dw-sec", timeout=60000)
    pg.click("details.dw-sec summary")
    pg.wait_for_selector("details.dw-sec[open] .dw-shots img[src^='blob:']", timeout=20000)
    # her own words in a section
    pg.click("details.dw-sec[open] [data-editsec]")
    pg.fill("form[data-form=edit] [name=body]", "The home screen of your shop. Tap **Dukaan kholo** to start.")
    pg.click("form[data-form=edit] [type=submit]")
    pg.wait_for_selector("text=edited by you", timeout=20000)
    snap(pg, "dw-doc-1440")
    # publish card -> her tap (twice: the page asks again, no browser dialog)
    pg.click("form[data-form=publish] [type=submit]")
    pg.wait_for_selector("[data-dec][data-yes='1']", timeout=30000)
    pg.click("[data-dec][data-yes='1']")
    pg.wait_for_selector("text=Tap again to make it public", timeout=10000)
    pg.click("[data-dec][data-yes='1']")
    pg.wait_for_selector("text=Public at", timeout=30000)
    pg.click("[data-files]")
    pg.wait_for_selector("text=Files ready", timeout=30000)
    go(pg, "#/docs", "table.tb")
    snap(pg, "dw-docs-1440")
    go(pg, "#/screens", "text=Screenshots")
    go(pg, "#/today", "text=Your docs by kind")
    snap(pg, "dw-today-1440")
    did = pg.evaluate("document.querySelector('[data-doc]').dataset.doc")
    for route, sel in (("#/today", "text=Needs you"), ("#/write", "form[data-form=write]"), ("#/docs", "table.tb"), (f"#/docs/{did}", "details.dw-sec"),
                       ("#/sources", "form[data-form=addprod]"), ("#/screens", "text=Screenshots"), ("#/settings", "form[data-form=dwset]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#dwPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        if route.startswith("#/docs/"):
            snap(pg, "dw-doc-390")
    snap(pg, "dw-settings-390")
    assert not errs, errs
