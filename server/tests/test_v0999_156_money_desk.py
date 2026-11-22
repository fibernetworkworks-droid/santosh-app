"""v0.999.156 MONEY SAFETY DESK: the Money Safety Assistant's own section like the business desks - its own chat (kind
'money', kept out of her chat lists) with the desk block + the money-safety tool in view, the desk routes (country, cases,
her state taps), every Open desk door, and the desk's pages walked in a real browser (check a message, draft a refund
claim, mark it sent, the deposit check)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def md(env):
    from app import moneychat as MC
    MC._OF.clear()
    MC._BLOCK.clear()
    return MC


def test_hire_chat_block_and_wiring(md):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert md.summary(T)["hired"] is False
    hire.hire(T, "paisa_sahayak", trust="seekh")
    d = md.summary(T)
    assert d["hired"] and d["open"] == 0 and d["country"] == "" and "GB" in d["countries"]
    chat = md.current(T)
    assert md.is_money(chat["id"]) and md.owns(T, chat["id"]) and md.current(T)["id"] == chat["id"]
    assert "your country" in md.greeting(T)
    blk = md.block(T)
    assert "<money_safety_desk>" in blk and "SHE sends it" in blk and "PIN, OTP" in blk and "not set yet" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_mnc.is_money(conversation_id)" in src and "adm.admit_families(_mnc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["paisa_sahayak"] in md.FAMILIES
    for f in ("callconv.py", "convs.py"):
        assert '"vocal", "money")' in (root / "server/app" / f).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/money")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "moneydesk.js" in r.text
    html = (root / "server/app/static/console/moneydesk.html").read_text()
    for f in ("chatkit.js", "quality.js", "seodesk.css", "moneydesk.css", "moneydesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    assert "location.assign('/console/money')" in (root / "server/app/static/console/v2.js").read_text()
    assert "paisa_sahayak: 'moneydesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/money'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_money_chat_kept_out_of_her_chat_lists(md):
    from sqlalchemy import select
    from app import callconv
    from app.db import Conversation, session
    from app.employee import hire
    hire.hire(T, "paisa_sahayak", trust="seekh")
    cid = md.new_chat(T)["id"]
    with session() as s:
        ids = [c.id for c in s.scalars(select(Conversation).where(Conversation.tenant_id == T, callconv.not_call())).all()]
    assert cid not in ids


def test_country_cases_and_her_taps(md):
    from app.employee import hire
    from app.fin.desks import safety as SF
    hire.hire(T, "paisa_sahayak", trust="seekh")
    with pytest.raises(md.MoneyError):
        md.set_country(T, "United Kingdom")
    md.set_country(T, "gb")
    assert md.summary(T)["country"] == "GB" and "Her country: GB" in md.block(T)
    out = SF.run(T, "refund_claim", {"country": "GB", "txn_date": "2026-11-20", "amount": 640, "account": "12344821"})
    cid = out["case_id"]
    d = md.summary(T)
    assert d["open"] == 1 and d["to_send"] == 1
    c = md.case(T, cid)
    assert "ending 4821" in c["letter"] and "12344821" not in c["letter"]
    assert c["time_limits"] and all(t["kind"] in ("deadline", "reminder", "not_confirmed", "unknown") for t in c["time_limits"])
    assert c["route"] and c["evidence"]                      # kept with the case, not only in the page's memory
    with pytest.raises(md.MoneyError):
        md.set_state(T, cid, "paid")
    assert md.set_state(T, cid, "sent")["state"] == "sent"
    assert md.summary(T)["to_send"] == 0
    assert md.set_state(T, cid, "closed")["state"] == "closed" and md.summary(T)["open"] == 0
    with pytest.raises(md.MoneyError):
        md.case("someone-else", cid)                         # another tenant never sees it


def test_routes(md):
    from app.main import app
    from app.employee import hire
    c = TestClient(app)
    assert c.get("/api/money/desk").json()["hired"] is False
    hire.hire(T, "paisa_sahayak", trust="seekh")
    assert c.put("/api/money/country", json={"country": "xx1"}).status_code == 400
    assert c.put("/api/money/country", json={"country": "GB"}).json() == {"country": "GB"}
    r = c.post("/api/fin/safety/card_dispute", json={"country": "GB", "txn_date": "2026-11-12", "reason": "charged_twice"})
    assert r.status_code == 200, r.text
    cid = r.json()["case_id"]
    assert c.get(f"/api/money/cases/{cid}").json()["letter"]
    assert c.post(f"/api/money/cases/{cid}/state", json={"state": "sent"}).json()["state"] == "sent"
    assert c.post(f"/api/money/cases/{cid}/state", json={"state": "nope"}).status_code == 400
    assert c.get("/api/money/cases/nope").status_code == 404
    chat = c.get("/api/money/chat").json()["id"]
    assert c.get(f"/api/money/chat/{chat}/ok").json() == {"ok": True}


@pytest.fixture
def md_server(md, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "paisa_sahayak", trust="seekh")
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
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_money_desk_in_a_real_browser(md_server):
    import os
    base, browser, key = md_server
    errors = []
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/money")
        pg.wait_for_selector("#sdTabs [data-tab='today']", timeout=20000)
        pg.wait_for_function("() => document.querySelector('#sdThread').innerText.includes('never ask for your PIN')", timeout=20000)
        pg.evaluate("document.querySelector('#sdChat').__keep = 1")
        for tab, want in (("check", "Before you pay anyone"), ("cases", "Start a case"), ("deposit", "Is my money protected"),
                          ("settings", "What it will never do"), ("today", "Choose your country")):
            pg.click(f"#sdTabs [data-tab='{tab}']")
            try:
                pg.wait_for_function("(w) => document.querySelector('#mdPage').innerText.includes(w)", arg=want, timeout=10000)
            except Exception:
                raise AssertionError(f"{tab}: errors={errors} page={pg.inner_text('#mdPage')[:500]!r}")
            assert pg.evaluate("document.querySelector('#sdChat').__keep") == 1
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        ctx.close()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    # choose the country
    pg.goto(base + "/console/money#/settings")
    pg.wait_for_selector("form[data-form=country] select")
    pg.select_option("form[data-form=country] select", "GB")
    pg.click("form[data-form=country] button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#mdSite').innerText.includes('United Kingdom')", timeout=10000)
    # check a message
    pg.goto(base + "/console/money#/check")
    pg.wait_for_selector("#mdMsg")
    pg.fill("#mdMsg", "Royal Mail: your parcel is held. Pay the 1.99 fee within 24 hours at http://royalmail-redeliver.co/pay and share the OTP")
    pg.click("form[data-form=check] button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('If you already paid')", timeout=10000)
    assert "sign" in pg.inner_text("#mdPage")
    # draft a refund claim -> the case page -> I've sent it
    pg.click("[data-go='new/refund_claim']")
    pg.wait_for_selector("form[data-form=new] input[name=amount]")
    pg.fill("form[data-form=new] input[name=amount]", "640")
    pg.fill("form[data-form=new] input[name=account]", "4821")
    pg.click("form[data-form=new] button[type=submit]")
    pg.wait_for_function("() => location.hash.startsWith('#/case/') && document.querySelector('.md-letter')", timeout=15000)
    txt = pg.inner_text("#mdPage")
    assert "ending 4821" in txt and "Time limits" in txt and "You send this yourself" in txt
    shots = os.environ.get("HOOLA_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/money-case.png")
    pg.click("[data-state='sent']")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Sent · waiting')", timeout=10000)
    # the deposit check
    pg.goto(base + "/console/money#/deposit")
    pg.wait_for_selector("[data-bank='0']")
    pg.fill("[data-bank='0']", "Bank One")
    pg.fill("[data-amt='0']", "107000")
    pg.click("form[data-form=deposit] button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Bank by bank')", timeout=10000)
    if shots:
        pg.screenshot(path=f"{shots}/money-deposit.png")
        pg.goto(base + "/console/money#/today")
        pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Open cases')", timeout=10000)
        pg.screenshot(path=f"{shots}/money-today.png")
    ctx.close()
    assert not errors, errors
