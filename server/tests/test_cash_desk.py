"""CASH & TREASURY DESK: the Cash & Treasury employee's own section, built like Payroll and Tax - its own chat (kind 'cash') with the
desk block + the cash tool in view; the 13-week forecast from her books, payroll and statements with her own expected items and the cash
she says is in the bank; a what-if on late payers; spare cash, bank fees, money in other currencies at her own dated rates; loan
covenants tested only once a person checked them against the loan agreement; the download (PDF + CSV); team roles; and the desk walked
in a real browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def cs(env):
    from app import cashchat as CC
    CC._OF.clear()
    CC._BLOCK.clear()
    return CC


def _ws(name="Riverside Bakery", cc="GB", cur="GBP"):
    from app.fin import profile as PR
    pv = PR.preview({"size": "business", "countries": [cc], "currency": cur, "name": name, "wants": []})
    return PR.apply(T, pv["answers"], pv["hash"])["id"]


def _data(ws):
    from app.fin import spine as SP
    from app.fin.desks import books as B
    SP.import_statement(T, ws, "Date,Narration,Debit,Credit\n2026-07-01,RENT 7,1000.00,\n2026-08-01,RENT 8,1000.00,\n"
                        "2026-09-01,RENT 9,1000.00,\n2026-08-20,MONTHLY FEE,5.00,\n2026-09-20,MONTHLY FEE,5.00,\n"
                        "2026-09-25,SALES,,20000.00\n", "Current", "GBP")
    B.run(T, "bill", {"workspace": ws, "party": "Supplier", "issue": "2026-10-01", "due": "2026-10-14", "issue_now": True,
                      "lines": [{"price": 300}]})
    B.run(T, "invoice", {"workspace": ws, "party": "Cafe A", "issue": "2026-09-01", "due": "2026-09-15", "issue_now": True,
                         "lines": [{"price": 500}]})


def test_hire_chat_block_and_wiring(cs):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert cs.summary(T)["hired"] is False
    hire.hire(T, "cash_treasury", trust="seekh")
    d = cs.summary(T)
    assert d["hired"] and d["workspace"] is None and "moves no money" in d["foot"]
    chat = cs.current(T)
    assert cs.is_cash(chat["id"]) and cs.owns(T, chat["id"]) and cs.current(T)["id"] == chat["id"]
    assert "Books & Accounts" in cs.greeting(T)
    blk = cs.block(T)
    assert "<cash_desk>" in blk and "move no money" in blk and "No business set up yet" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_csc.is_cash(conversation_id)" in src and "adm.admit_families(_csc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["cash_treasury"] in cs.FAMILIES
    for f in ("callconv.py", "convs.py"):
        assert '"tax", "cash"' in (root / "server/app" / f).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/cash")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "cashdesk.js" in r.text
    html = (root / "server/app/static/console/cashdesk.html").read_text()
    for f in ("chatkit.js", "seodesk.css", "moneydesk.css", "cashdesk.css", "cashdesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    assert "location.assign('/console/cash')" in (root / "server/app/static/console/v2.js").read_text()
    assert "cash_treasury: 'cashdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/cash'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_forecast_items_opening_and_what_if(cs):
    from app.employee import hire
    hire.hire(T, "cash_treasury", trust="seekh")
    ws = _ws()
    _data(ws)
    cs.do(T, "settings", {"workspace": ws, "min_cash": 15000, "weeks_buffer": 0})
    f = cs.do(T, "forecast", {"workspace": ws, "start": "2026-10-05", "weeks": 5})
    assert f["opening"] == 16990.0 and "statements" in f["opening_from"]
    assert f["overdue_invoices"] and f["weeks"][0]["in"] == 500            # the overdue invoice lands in week 1
    cs.do(T, "add_item", {"workspace": ws, "date": "2026-10-20", "amount": 4000, "direction": "out", "label": "Corporation tax"})
    cs.do(T, "opening", {"workspace": ws, "amount": 12000, "as_of": "2026-10-01"})
    f2 = cs.do(T, "forecast", {"workspace": ws, "start": "2026-10-05", "weeks": 5})
    assert f2["opening"] == 12000 and "you said" in f2["opening_from"] and f2["opening_stale"]
    lines = [ln for wk in f2["weeks"] for ln in wk["lines"]]
    assert any(ln["what"] == "Corporation tax" and ln["amount"] == -4000 for ln in lines)
    assert f2["under_minimum_weeks"] and f2["total_out"] > f["total_out"]
    later = cs.do(T, "forecast", {"workspace": ws, "start": "2026-10-05", "weeks": 5, "pay_later_days": 30})
    assert later["what_if"] == {"pay_later_days": 30}
    items = cs.do(T, "add_item", {"workspace": ws, "date": "2026-11-02", "amount": 900, "direction": "in", "label": "Grant"})["items"]
    assert [x["amount"] for x in items] == [-4000, 900]
    cs.do(T, "remove_item", {"workspace": ws, "n": items[1]["n"]})
    with pytest.raises(cs.CashDeskError):
        cs.do(T, "remove_item", {"workspace": ws, "n": 99})
    with pytest.raises(cs.CashDeskError, match="date"):
        cs.do(T, "add_item", {"workspace": ws, "date": "soon", "amount": 1, "label": "x"})
    i = cs.do(T, "idle", {"workspace": ws, "weeks_buffer": 0})
    assert "buffer" in i and "moves no money" in i["says"]
    fe = cs.do(T, "fees", {"workspace": ws})
    assert fe["total"] == 10.0 and fe["by_kind"] == {"account fee": 10.0}
    bt = cs.do(T, "backtest", {"workspace": ws})
    assert "error" in bt and "months" in bt["error"]
    # downloads
    from app.main import app
    c = TestClient(app)
    pdf = c.get("/api/cash/download", params={"workspace": ws, "what": "pdf"})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    csv = c.get("/api/cash/download", params={"workspace": ws, "what": "csv"})
    assert csv.status_code == 200 and "Corporation tax" in csv.text and "moves no money" in csv.text


def test_covenants_checked_before_tested_and_fx(cs):
    from app.employee import hire
    from app.fin.desks import books as B
    hire.hire(T, "cash_treasury", trust="seekh")
    ws = _ws()
    _data(ws)
    cs.do(T, "set_covenant", {"workspace": ws, "name": "leverage", "kind": "max_ratio", "numerator": "net_debt", "denominator": "ebitda",
                              "limit": 3})
    cs.do(T, "figure", {"workspace": ws, "name": "net_debt", "value": 70000})
    cs.do(T, "figure", {"workspace": ws, "name": "ebitda", "value": 20000})
    r = cs.do(T, "covenants", {"workspace": ws})
    assert r["to_check"] == ["leverage"] and r["results"] == []          # not tested until a person checks it
    cs.do(T, "check_covenant", {"workspace": ws, "name": "leverage"})
    r = cs.do(T, "covenants", {"workspace": ws})
    assert r["results"][0]["actual"] == 3.5 and r["breached"] == ["leverage"]
    d = cs.summary(T)["desk"]
    assert any("leverage" in n["say"] for n in d["needs"])
    cs.do(T, "set_covenant", {"workspace": ws, "name": "leverage", "kind": "max_ratio", "numerator": "net_debt", "denominator": "ebitda",
                              "limit": 4})
    assert cs.do(T, "covenants", {"workspace": ws})["to_check"] == ["leverage"]   # changed terms need checking again
    cs.do(T, "remove_covenant", {"workspace": ws, "name": "leverage"})
    assert cs.do(T, "covenants", {"workspace": ws})["covenants"] == []
    with pytest.raises(cs.CashDeskError):
        cs.do(T, "set_covenant", {"workspace": ws, "name": "x", "kind": "nope", "limit": 1})
    B.run(T, "invoice", {"workspace": ws, "party": "Paris", "issue": "2026-10-01", "currency": "EUR", "rate": 0.86,
                         "rate_date": "2026-10-01", "rate_source": "bank", "issue_now": True, "lines": [{"price": 1000}]})
    x = cs.do(T, "fx", {"workspace": ws})
    assert x["rates_missing"] == ["EUR"] and any("EUR" in n["say"] for n in cs.summary(T)["desk"]["needs"])
    cs.do(T, "rate", {"workspace": ws, "currency": "eur", "rate": 0.85})
    x = cs.do(T, "fx", {"workspace": ws, "move_pct": 10})
    eur = x["positions"][0]
    assert eur["value_in_GBP"] == 850.0 and x["total_if_all_fall"] == -85.0 and eur["rate_on"]
    with pytest.raises(cs.CashDeskError):
        cs.do(T, "rate", {"workspace": ws, "currency": "EURO", "rate": 1})
    # a viewer reads but never changes
    with pytest.raises(cs.CashDeskError, match="can read this desk"):
        _as_role(cs, ws, "viewer", "add_item", {"date": "2026-11-01", "amount": 1, "label": "x"})
    assert "positions" in _as_role(cs, ws, "auditor", "fx", {})


def _as_role(cs, ws, role, part, a):
    from app.fin.desks import books_ent as E
    real = E.access
    E.access = lambda caller, w: {"owner": T, "role": role, "id": "x", "name": "Someone", "workspace": w}
    try:
        return cs.do("someone-else", part, {"workspace": ws, **a})
    finally:
        E.access = real


def test_today_and_routes(cs):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "cash_treasury", trust="seekh")
    ws = _ws()
    c = TestClient(app)
    d = c.get("/api/cash/desk").json()
    assert d["hired"] and d["workspace"]["id"] == ws
    assert any("least cash" in n["say"] for n in d["desk"]["needs"])
    _data(ws)
    assert c.post("/api/cash/do/settings", json={"workspace": ws, "min_cash": 50000, "lag_days": 5, "exclude": "one-off, refund"}).status_code == 200
    d = c.get("/api/cash/desk").json()["desk"]
    assert d["settings"]["min_cash"] == 50000 and d["settings"]["exclude"] == ["one-off", "refund"]
    assert any("under your minimum" in n["say"] for n in d["needs"]) and any("Overdue" in n["say"] for n in d["needs"])
    assert c.post("/api/cash/do/nope", json={"workspace": ws}).status_code == 400
    assert c.get("/api/cash/chat").json()["id"]
    assert c.put("/api/cash/workspace", json={"workspace": "nope"}).status_code == 400
    assert c.get("/api/cash/download", params={"workspace": ws, "what": "doc"}).status_code == 400
    from app import cashchat as CC
    CC.forget(T)
    assert "lowest point" in CC.greeting(T) and "Forecast from" in CC.block(T)


@pytest.fixture
def cs_server(cs, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "cash_treasury", trust="seekh")
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


def test_desk_in_a_real_browser(cs, cs_server):
    from app.fin.desks import books as B
    base, browser, key = cs_server
    ws = _ws()
    _data(ws)
    from datetime import date, timedelta
    soon = (date.today() + timedelta(days=20)).isoformat()
    B.run(T, "bill", {"workspace": ws, "party": "Oven Ltd", "issue": date.today().isoformat(), "due": soon, "issue_now": True,
                      "lines": [{"price": 9000}]})
    B.run(T, "invoice", {"workspace": ws, "party": "Paris", "issue": "2026-10-01", "currency": "EUR", "rate": 0.86,
                         "rate_date": "2026-10-01", "rate_source": "bank", "issue_now": True, "lines": [{"price": 1000}]})
    cs.do(T, "settings", {"workspace": ws, "min_cash": 9000})
    cs.do(T, "set_covenant", {"workspace": ws, "name": "leverage", "kind": "max_ratio", "numerator": "net_debt", "denominator": "ebitda",
                              "limit": 3})
    cs.do(T, "figure", {"workspace": ws, "name": "net_debt", "value": 50000})
    cs.do(T, "figure", {"workspace": ws, "name": "ebitda", "value": 20000})
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []
    for w, h in ((1440, 900), (390, 844)):
        ctx = browser.new_context(viewport={"width": w, "height": h})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "/console/cash")
        pg.wait_for_selector("text=Needs you", timeout=20000)
        assert pg.locator(".cs-hero").count() == 1 and pg.locator(".cs-chart svg .line").count() == 1
        assert pg.locator(".md-kpi").count() == 4
        if shots:
            pg.screenshot(path=f"{shots}/cash-today-{w}.png", full_page=True)
        pg.goto(base + "/console/cash#/forecast")
        pg.wait_for_selector(".cs-wk", timeout=20000)
        pg.click(".cs-wk[data-wk='1']")
        pg.wait_for_selector(".cs-lines", timeout=20000)
        if w == 1440:
            pg.fill("form[data-form=item] [name=label]", "Corporation tax")
            pg.fill("form[data-form=item] [name=amount]", "2500")
            pg.fill("form[data-form=item] [name=date]", soon)
            pg.click("form[data-form=item] [type=submit]")
            pg.wait_for_selector(".cs-it >> text=Corporation tax", timeout=20000)
        pg.click("[data-late='30']")
        pg.wait_for_selector("text=If customers pay 30 days later than usual", timeout=20000)
        assert pg.locator(".cs-chart .line.wi").count() == 1
        if shots:
            pg.screenshot(path=f"{shots}/cash-forecast-{w}.png", full_page=True)
        pg.goto(base + "/console/cash#/spare")
        pg.wait_for_selector("text=At the lowest point", timeout=20000)
        pg.goto(base + "/console/cash#/fees")
        pg.wait_for_selector("text=By kind", timeout=20000)
        if shots:
            pg.screenshot(path=f"{shots}/cash-fees-{w}.png", full_page=True)
        pg.goto(base + "/console/cash#/currencies")
        pg.wait_for_selector("text=Give a rate for EUR", timeout=20000) if w == 1440 else pg.wait_for_selector("text=Your rates", timeout=20000)
        if w == 1440:
            pg.fill("form[data-form=rate] [name=currency]", "EUR")
            pg.fill("form[data-form=rate] [name=rate]", "0.85")
            pg.click("form[data-form=rate] [type=submit]")
            pg.wait_for_selector("text=0.85 GBP for 1 EUR", timeout=20000)
        if shots:
            pg.screenshot(path=f"{shots}/cash-currencies-{w}.png", full_page=True)
        pg.goto(base + "/console/cash#/covenants")
        pg.wait_for_selector(".cs-cov", timeout=20000)
        if w == 1440:
            pg.click("[data-cvcheck='leverage']")
            pg.wait_for_selector("text=Met · headroom", timeout=20000)
        if shots:
            pg.screenshot(path=f"{shots}/cash-covenants-{w}.png", full_page=True)
        pg.goto(base + "/console/cash#/settings")
        pg.wait_for_selector("text=Where the forecast comes from", timeout=20000)
        if shots:
            pg.screenshot(path=f"{shots}/cash-settings-{w}.png", full_page=True)
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), w
        ctx.close()
    assert not errs, errs
