"""v0.999.176 TAX DESK: the Tax (worldwide) employee's own section, built like Payroll and Books & Accounts - its own chat (kind 'tax')
with the desk block + the tax tool in view; a return worked out from her books only once a person checked every rate in it; "I
filed it" with the reference locks the period; tax letters read with the reply-by date a reminder only once she confirms it; US
sales by state and the EU One Stop Shop with each limit / rate's checked state; the personal organiser with her papers; the
download for filing (PDF + CSV); team roles; and the desk walked in a real browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def tx(env):
    from app import taxchat as TC
    TC._OF.clear()
    TC._BLOCK.clear()
    return TC


def _ws(name="Riverside Bakery", cc="GB", cur="GBP"):
    from app.fin import profile as PR
    pv = PR.preview({"size": "business", "countries": [cc], "currency": cur, "name": name, "wants": []})
    return PR.apply(T, pv["answers"], pv["hash"])["id"]


def _books(ws):
    from app.fin.desks import books as B
    B.run(T, "invoice", {"workspace": ws, "party": "Cafe A", "issue": "2026-08-01", "issue_now": True,
                         "lines": [{"price": 1000, "tax_pct": 20}, {"price": 200, "tax_pct": 5, "tax_code": "reduced"}]})
    B.run(T, "bill", {"workspace": ws, "party": "Flour Co", "issue": "2026-08-03", "issue_now": True, "lines": [{"price": 300, "tax_pct": 20}]})


def test_hire_chat_block_and_wiring(tx):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert tx.summary(T)["hired"] is False
    hire.hire(T, "tax_worldwide", trust="seekh")
    d = tx.summary(T)
    assert d["hired"] and d["workspace"] is None and "file and pay" in d["foot"]
    chat = tx.current(T)
    assert tx.is_tax(chat["id"]) and tx.owns(T, chat["id"]) and tx.current(T)["id"] == chat["id"]
    assert "Books & Accounts" in tx.greeting(T)
    blk = tx.block(T)
    assert "<tax_desk>" in blk and "never file a return" in blk and "No business set up yet" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_txc.is_tax(conversation_id)" in src and "adm.admit_families(_txc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["tax_worldwide"] in tx.FAMILIES
    for f in ("callconv.py", "convs.py"):
        assert '"interactive", "tax"' in (root / "server/app" / f).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/tax")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "taxdesk.js" in r.text
    html = (root / "server/app/static/console/taxdesk.html").read_text()
    for f in ("chatkit.js", "seodesk.css", "moneydesk.css", "taxdesk.css", "taxdesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    assert "location.assign('/console/tax')" in (root / "server/app/static/console/v2.js").read_text()
    assert "tax_worldwide: 'taxdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/tax'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_rates_checked_before_use_return_and_filed_lock(tx):
    from app.employee import hire
    hire.hire(T, "tax_worldwide", trust="seekh")
    ws = _ws()
    _books(ws)
    tx.do(T, "settings", {"workspace": ws, "country": "GB", "scheme": "vat", "period_kind": "quarterly", "due_offset_days": 37})
    tx.do(T, "set_rate", {"workspace": ws, "kind": "rates", "code": "std", "value": 20})
    tx.do(T, "set_rate", {"workspace": ws, "kind": "rates", "code": "reduced", "value": 5})
    r = tx.do(T, "return", {"workspace": ws, "period": "2026-Q3"})
    assert r["blocked"] and "rate std 20" in " ".join(r["rates_to_check"])          # not used until a person checks it
    tx.do(T, "check_rate", {"workspace": ws, "kind": "rates", "code": "std"})
    assert tx.do(T, "return", {"workspace": ws, "period": "2026-Q3"})["blocked"]     # reduced still unchecked
    tx.do(T, "check_rate", {"workspace": ws, "kind": "rates", "code": "reduced"})
    r = tx.do(T, "return", {"workspace": ws, "period": "2026-Q3"})
    b = {x["box"]: x["amount"] for x in r["boxes"]}
    assert not r.get("blocked") and b["1"] == 210 and b["4"] == 60 and r["to_pay"] == 150
    assert any("checked by a person" in c["say"] for c in r["checks"])
    assert any(not c["ok"] and "Not closed in your books" in c["say"] for c in r["checks"])
    # changing a checked rate needs checking again
    tx.do(T, "set_rate", {"workspace": ws, "kind": "rates", "code": "reduced", "value": 6})
    assert tx.do(T, "return", {"workspace": ws, "period": "2026-Q3"})["blocked"]
    tx.do(T, "check_rate", {"workspace": ws, "kind": "rates", "code": "reduced"})
    # downloads for filing
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    pdf = c.get("/api/tax/download", params={"workspace": ws, "what": "pdf", "period": "2026-Q3"})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    csv = c.get("/api/tax/download", params={"workspace": ws, "what": "csv", "period": "2026-Q3"})
    assert csv.status_code == 200 and "VAT due on sales" in csv.text and "file and pay" in csv.text
    # filing is her tap with the reference; then the period is locked
    with pytest.raises(tx.TaxDeskError, match="reference"):
        tx.do(T, "filed", {"workspace": ws, "period": "2026-Q3", "reference": ""})
    f = tx.do(T, "filed", {"workspace": ws, "period": "2026-Q3", "reference": "VAT-123456"})
    assert f["locked"] and f["filed"]["to_pay"] == r["to_pay"]
    with pytest.raises(tx.TaxDeskError, match="already marked as filed"):
        tx.do(T, "filed", {"workspace": ws, "period": "2026-Q3", "reference": "VAT-999"})
    again = tx.do(T, "return", {"workspace": ws, "period": "2026-Q3"})
    assert again["locked"] and again["filed"]["reference"] == "VAT-123456"
    with pytest.raises(PermissionError):                      # the engine never files
        from app.fin.desks import tax as TT
        TT.run(T, "file", {"workspace": ws})


def test_letters_need_her_confirm_for_the_date(tx):
    from app.employee import hire
    from app.fin.desks import tax as TT
    hire.hire(T, "tax_worldwide", trust="seekh")
    ws = _ws()
    tx.do(T, "settings", {"workspace": ws, "country": "GB"})
    L = tx.do(T, "add_letter", {"workspace": ws, "name": "HMRC letter.pdf",
                                "text": "HM Revenue & Customs. HMRC reference: XA4471829. Penalty notice. You owe £100.00. "
                                        "Please pay or appeal by 20 May 2027."})["letter"]
    assert L["authority"] == "HMRC" and L["reply_by"] == "2027-05-20" and L["state"] == "needs_you" and not L["date_confirmed"]
    cal = TT.run(T, "calendar", {"workspace": ws, "year": 2027})["items"]
    assert not any("HMRC" in x["what"] for x in cal)                          # not a reminder until she confirms
    d = tx.summary(T)["desk"]
    assert len(d["letters_waiting"]) == 1 and any("HMRC" in n["say"] for n in d["needs"])
    tx.do(T, "letter_act", {"workspace": ws, "n": L["n"], "act": "confirm_date", "reply_by": "2027-05-20"})
    cal = TT.run(T, "calendar", {"workspace": ws, "year": 2027})["items"]
    assert any("HMRC" in x["what"] and x["due"] == "2027-05-20" for x in cal)
    s = tx.do(T, "letter_act", {"workspace": ws, "n": L["n"], "act": "sent"})["letter"]
    assert s["state"] == "sent"
    assert not tx.summary(T)["desk"]["letters_waiting"]
    assert "XA4471829" in tx.do(T, "letter", {"workspace": ws, "n": L["n"]})["letter"]["text"]


def test_borders_personal_and_roles(tx):
    from app.employee import hire
    from app.fin import spine as SP
    from app.fin.desks import books as B
    from app.fin.desks import books_ent as E
    hire.hire(T, "tax_worldwide", trust="seekh")
    ws = _ws("Shop", "GB", "GBP")
    tx.do(T, "settings", {"workspace": ws, "country": "GB"})
    B.run(T, "invoice", {"workspace": ws, "party": "Berlin", "issue": "2026-08-01", "issue_now": True, "supply": {"country": "DE"},
                         "lines": [{"price": 100, "tax_pct": 19, "tax_code": "oss"}]})
    tx.do(T, "set_rate", {"workspace": ws, "kind": "oss_rates", "code": "DE", "value": 19})
    b = tx.do(T, "borders", {"workspace": ws, "period": "2026-Q3"})
    de = b["oss"]["countries"][0]
    assert de["country"] == "DE" and de["tax_due"] == 19 and de["rate_checked"] is False
    tx.do(T, "check_rate", {"workspace": ws, "kind": "oss_rates", "code": "DE"})
    assert tx.do(T, "borders", {"workspace": ws, "period": "2026-Q3"})["oss"]["countries"][0]["rate_checked"] is True
    SP.import_statement(T, ws, "Date,Narration,Debit,Credit\n2026-05-25,SALARY ACME,,3000.00\n2026-06-01,INTEREST PAID,,12.50\n",
                        "Current", "GBP")
    p = tx.do(T, "personal", {"workspace": ws, "year": 2027})
    assert p["income"].get("employment") == 3000.0 and p["papers"] and not any(x["have"] for x in p["papers"])
    first = p["papers"][0]["name"]
    tx.do(T, "paper", {"workspace": ws, "name": first, "have": True})
    assert tx.do(T, "personal", {"workspace": ws, "year": 2027})["papers"][0]["have"]
    # a viewer on her business reads but never changes or files
    with pytest.raises(tx.TaxDeskError, match="Only the owner or an approver"):
        _as_role(tx, ws, "accountant", "filed", {"period": "2026-Q3", "reference": "REF-1"})
    with pytest.raises(tx.TaxDeskError, match="can read this desk"):
        _as_role(tx, ws, "viewer", "check_rate", {"kind": "oss_rates", "code": "DE"})
    assert _as_role(tx, ws, "viewer", "rates", {})["rates"]


def _as_role(tx, ws, role, part, a):
    from app.fin.desks import books_ent as E
    real = E.access
    E.access = lambda caller, w: {"owner": T, "role": role, "id": "x", "name": "Someone", "workspace": w}
    try:
        return tx.do("someone-else", part, {"workspace": ws, **a})
    finally:
        E.access = real


def test_today_and_routes(tx):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "tax_worldwide", trust="seekh")
    ws = _ws()
    c = TestClient(app)
    d = c.get("/api/tax/desk").json()
    assert d["hired"] and d["workspace"]["id"] == ws and d["desk"]["set"] is False
    assert any("country" in n["say"] for n in d["desk"]["needs"])
    assert c.post("/api/tax/do/settings", json={"workspace": ws, "country": "GB", "period_kind": "quarterly", "due_offset_days": 37}).status_code == 200
    d = c.get("/api/tax/desk").json()["desk"]
    assert d["set"] and d["next_due"] and d["period"]
    from datetime import date
    assert all(x["due"] < date.today().isoformat() for x in d["overdue"])          # a past due return not marked filed is said
    assert all(any(x["what"] in n["say"] for n in d["needs"]) for x in d["overdue"])
    assert c.post("/api/tax/do/nope", json={"workspace": ws}).status_code == 400
    assert c.post("/api/tax/do/add_date", json={"workspace": ws, "title": "Corporation tax payment", "due": "2027-01-01"}).status_code == 200
    assert c.get("/api/tax/chat").json()["id"]
    assert c.put("/api/tax/workspace", json={"workspace": "nope"}).status_code == 400
    assert any("Corporation tax" in x["what"] for x in c.get("/api/tax/desk").json()["desk"]["dates"])


@pytest.fixture
def tx_server(tx, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "tax_worldwide", trust="seekh")
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


def test_desk_in_a_real_browser(tx, tx_server):
    base, browser, key = tx_server
    ws = _ws()
    _books(ws)
    tx.do(T, "settings", {"workspace": ws, "country": "GB", "scheme": "vat", "period_kind": "quarterly", "due_offset_days": 37})
    tx.do(T, "set_rate", {"workspace": ws, "kind": "rates", "code": "std", "value": 20})
    tx.do(T, "set_rate", {"workspace": ws, "kind": "rates", "code": "reduced", "value": 5})
    tx.do(T, "add_letter", {"workspace": ws, "text": "HMRC reference: XA4471829. Penalty notice. You owe £100.00. Please pay by 20 May 2027."})
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []
    for w, h in ((1440, 900), (390, 844)):
        ctx = browser.new_context(viewport={"width": w, "height": h})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "/console/tax")
        pg.wait_for_selector("text=Needs you", timeout=20000)
        assert pg.locator(".md-kpi").count() == 4
        if shots:
            pg.screenshot(path=f"{shots}/tax-today-{w}.png", full_page=True)
        pg.goto(base + "/console/tax#/returns/2026-Q3")
        pg.wait_for_selector("text=This return waits for you", timeout=20000)
        pg.goto(base + "/console/tax#/settings")
        pg.wait_for_selector("[data-check='rates|std']", timeout=20000)
        pg.click("[data-check='rates|std']")
        pg.wait_for_selector("[data-check='rates|reduced']", timeout=20000)
        pg.click("[data-check='rates|reduced']")
        pg.wait_for_function("() => !document.querySelector('[data-check^=\"rates|\"]')", timeout=20000)
        if shots:
            pg.screenshot(path=f"{shots}/tax-settings-{w}.png", full_page=True)
        pg.goto(base + "/console/tax#/returns/2026-Q3")
        pg.wait_for_selector("text=VAT due on sales", timeout=20000)
        assert pg.locator("[data-dl=pdf]").count() == 1
        if shots:
            pg.screenshot(path=f"{shots}/tax-return-{w}.png", full_page=True)
        pg.goto(base + "/console/tax#/letters")
        pg.wait_for_selector("text=Read from the letter · confirm", timeout=20000)
        if shots:
            pg.screenshot(path=f"{shots}/tax-letters-{w}.png", full_page=True)
        pg.goto(base + "/console/tax#/borders")
        pg.wait_for_selector("text=EU · One Stop Shop", timeout=20000)
        pg.goto(base + "/console/tax#/personal")
        pg.wait_for_selector("text=Papers for your accountant", timeout=20000)
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), w
        ctx.close()
        if w == 1440:          # a changed rate needs checking again: the phone pass checks it once more
            tx.do(T, "set_rate", {"workspace": ws, "kind": "rates", "code": "std", "value": 21})
            tx.do(T, "set_rate", {"workspace": ws, "kind": "rates", "code": "reduced", "value": 6})
    assert not errs, errs
