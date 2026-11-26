"""PAYMENTS DESK: the Payments employee's own section, built like the other finance desks - its own chat (kind 'payments') with the desk
block + the payments tool in view; chargeback case files (reason code -> evidence needed / missing, the response date from her window,
Visa 10.4 compelling evidence, the response letter as a PDF, the status SHE records); gateway settlement files and orders uploaded as CSV
and matched with the deposits in her imported bank statements; fees checked against her contract rate; disputes against sales by month;
failed recurring payments (the retry plan); marketplace seller payouts; the payment-firm tools; team roles; and the desk walked in a real
browser."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def py(env):
    from app import paychat as PC
    PC._OF.clear()
    PC._BLOCK.clear()
    return PC


def _ws(name="Riverside Shop", cc="GB", cur="GBP"):
    from app.fin import profile as PR
    pv = PR.preview({"size": "business", "countries": [cc], "currency": cur, "name": name, "wants": []})
    return PR.apply(T, pv["answers"], pv["hash"])["id"]


D1 = (date.today() - timedelta(days=20)).isoformat()
D2 = (date.today() - timedelta(days=13)).isoformat()
SETTLE = (f"Payout ID,Payout date,Order ID,Type,Amount\npo_1,{D1},A1,charge,100.00\npo_1,{D1},A1,fee,3.20\npo_1,{D1},A2,charge,50.00\n"
          f"po_1,{D1},A2,fee,1.70\npo_2,{D2},A3,charge,200.00\npo_2,{D2},A3,fee,6.10\npo_2,{D2},A1,refund,10.00\n")
ORDERS = f"id,amount,date\nA1,100,{D1}\nA2,50,{D1}\nA3,200,{D2}\nA4,75,{D2}\n"


def _bank(ws):
    from app.fin import spine as SP
    d = (date.today() - timedelta(days=18)).isoformat()
    SP.import_statement(T, ws, f"Date,Narration,Debit,Credit\n{d},STRIPE PAYOUT,,145.10\n{d},CASH DEPOSIT,,40.00\n", "Current", "GBP")


def test_hire_chat_block_and_wiring(py):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert py.summary(T)["hired"] is False
    hire.hire(T, "payments_desk", trust="seekh")
    d = py.summary(T)
    assert d["hired"] and d["workspace"] is None and "never submits" in d["foot"]
    chat = py.current(T)
    assert py.is_payments(chat["id"]) and py.owns(T, chat["id"])
    assert "Books & Accounts" in py.greeting(T)
    assert "<payments_desk>" in py.block(T) and "never submits a dispute response" in py.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_pyc.is_payments(conversation_id)" in src and "adm.admit_families(_pyc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["payments_desk"] in py.FAMILIES
    for f in ("callconv.py", "convs.py"):
        assert '"firm", "payments"' in (root / "server/app" / f).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/payments")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "paydesk.js" in r.text
    html = (root / "server/app/static/console/paydesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "moneydesk.css", "cashdesk.css", "creditdesk.css", "paydesk.css", "paydesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/payments')" in (root / "server/app/static/console/v2.js").read_text()
    assert "payments_desk: 'paydesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/payments'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_disputes(py):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "payments_desk", trust="seekh")
    ws = _ws()
    py.do(T, "settings", {"workspace": ws, "gateway": "Stripe", "pct": 1.5, "fixed": 0.2, "window_days": 7})
    d = py.do(T, "add_dispute", {"workspace": ws, "network": "visa", "reason_code": "13.1", "amount": 89.5, "gateway": "stripe",
                                 "transaction_id": "ch_1", "received": date.today().isoformat()})["dispute"]
    assert d["window_days"] == 7 and d["days_left"] == 7 and "too little evidence" in d["read"]["verdict"]
    with pytest.raises(py.PayDeskError, match="reason_code"):
        py.do(T, "add_dispute", {"workspace": ws, "network": "visa", "reason_code": "99", "amount": 1})
    d = py.do(T, "edit_dispute", {"workspace": ws, "n": 1, "evidence": {"proof_of_delivery": True}, "notes": "Royal Mail tracked"})["dispute"]
    assert d["read"]["verdict"] == "the evidence answers this reason code" and "signature" in d["read"]["evidence_missing"]
    with pytest.raises(py.PayDeskError, match="evidence"):
        py.do(T, "edit_dispute", {"workspace": ws, "n": 1, "evidence": {"made_up": True}})
    # Visa 10.4 with compelling evidence from her earlier transactions
    r = (date.today()).isoformat()
    d2 = py.do(T, "add_dispute", {"workspace": ws, "network": "visa", "reason_code": "10.4", "amount": 300, "received": r, "window_days": 10})["dispute"]
    prior = [{"date": (date.today() - timedelta(days=150)).isoformat(), "ip": "1.2.3.4", "device": "d1"},
             {"date": (date.today() - timedelta(days=200)).isoformat(), "ip": "1.2.3.4", "shipping": "1 High St"}]
    d2 = py.do(T, "edit_dispute", {"workspace": ws, "n": d2["n"], "prior": prior, "disputed": {"ip": "1.2.3.4", "device": "d1", "shipping": "1 High St"},
                                   "evidence": {"avs_cvv_match": True}})["dispute"]
    assert d2["read"]["compelling_evidence"]["qualifies"] and "prior_transactions" in d2["read"]["evidence_you_have"]
    pdf = TestClient(app).get("/api/payments/download", params={"workspace": ws, "what": "letter", "n": 1})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    # she records what happened; Hoola submits nothing
    with pytest.raises(py.PayDeskError, match="reference"):
        py.do(T, "status", {"workspace": ws, "n": 1, "status": "responded"})
    s = py.do(T, "status", {"workspace": ws, "n": 1, "status": "responded", "reference": "STRIPE-RESP-77"})["dispute"]
    assert s["status"] == "responded" and s["history"][-1]["reference"] == "STRIPE-RESP-77"
    from app.fin import laws as L
    with pytest.raises(L.Refused):
        py._engine(T, "x", "submit_response", {})
    needs = " | ".join(n["say"] for n in py.summary(T)["desk"]["needs"])
    assert "Dispute #2" in needs and "respond within 10 days" in needs


def test_reconcile_fees_prevention_recurring_payouts(py):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "payments_desk", trust="seekh")
    ws = _ws()
    _bank(ws)
    up = py.do(T, "upload", {"workspace": ws, "kind": "settlements", "gateway": "Stripe", "text": SETTLE, "name": "stripe.csv"})
    assert up["rows"] == 7
    with pytest.raises(py.PayDeskError, match="no column for"):
        py.do(T, "upload", {"workspace": ws, "kind": "settlements", "gateway": "stripe", "text": "a,b\n1,2\n"})
    py.do(T, "upload", {"workspace": ws, "kind": "orders", "text": ORDERS})
    r = py.do(T, "reconcile", {"workspace": ws})
    p1 = next(p for p in r["payouts"] if p["payout"] == "po_1")
    assert p1["net"] == 145.1 and p1["deposit"] and "STRIPE" in p1["deposit_narration"]
    assert r["payouts_without_deposit"] == ["po_2"] and [x["order"] for x in r["orders"]["missing_at_gateway"]] == ["A4"]
    assert r["by_gateway"]["stripe"]["fees"] == 11.0 and not r["balanced"]
    # fees vs her contract: 1.5% + 0.20 -> A1 1.70 (charged 3.20), A2 0.95 (1.70), A3 3.20 (6.10)
    py.do(T, "settings", {"workspace": ws, "gateway": "stripe", "pct": 1.5, "fixed": 0.2})
    fa = py.do(T, "fee_audit", {"workspace": ws})
    assert fa["overcharged_total"] == round(1.5 + 0.75 + 2.9, 2) and fa["by_gateway"]["stripe"] == fa["overcharged_total"]
    py.do(T, "add_dispute", {"workspace": ws, "network": "mastercard", "reason_code": "4855", "amount": 50, "received": D1})
    py.do(T, "settings", {"workspace": ws, "threshold_pct": 0.5})
    pv = py.do(T, "prevention", {"workspace": ws})
    assert pv["over"] and pv["over"][0]["dispute_pct"] > 0.5
    # failed recurring payments
    py.do(T, "upload", {"workspace": ws, "kind": "failed", "text": f"customer,amount,plan,date,reason\nmia@example.com,19,Pro,{D2},card expired\n"})
    py.do(T, "settings", {"workspace": ws, "retry_days": "2, 5"})
    dn = py.do(T, "dunning", {"workspace": ws})
    assert len(dn["customers"][0]["plan"]) == 2 and "did not go through" in dn["customers"][0]["plan"][0]["message"]
    py.do(T, "failed", {"workspace": ws, "n": dn["customers"][0]["n"], "status": "recovered"})
    assert py.do(T, "dunning", {"workspace": ws})["customers"] == []
    # marketplace payouts
    py.do(T, "upload", {"workspace": ws, "kind": "market", "text": "seller,amount,type,fee\nAnna,200,sale,2\nAnna,20,refund,\nBob,10,sale,15\n"})
    assert py.do(T, "payouts", {"workspace": ws}).get("error")
    py.do(T, "settings", {"workspace": ws, "commission_pct": 10})
    po = py.do(T, "payouts", {"workspace": ws})
    anna = next(s for s in po["sellers"] if s["seller"] == "Anna")
    assert anna["owed"] == 160.0 and next(s for s in po["sellers"] if s["seller"] == "Bob")["carry_forward"]
    csv = TestClient(app).get("/api/payments/download", params={"workspace": ws, "what": "payouts"})
    assert csv.status_code == 200 and "Anna" in csv.text
    d = py.summary(T)["desk"]
    needs = " | ".join(n["say"] for n in d["needs"])
    assert "po_2" in needs and "Fees above your contract" in needs and "Disputes" in needs
    py.forget(T)
    assert "payouts with no bank deposit: po_2" in py.block(T)


def test_firm_tools_and_roles(py):
    from app.employee import hire
    hire.hire(T, "payments_desk", trust="seekh")
    ws = _ws()
    k = py.do(T, "kyb", {"workspace": ws, "business": "Shop Ltd", "threshold_pct": 25, "documents": ["registration"],
                         "ownership": [{"owner": "Holdco", "owned": "Shop Ltd", "pct": 60}, {"owner": "Ann", "owned": "Holdco", "pct": 50, "person": True},
                                       {"owner": "Raj", "owned": "Shop Ltd", "pct": 40, "person": True}]})
    assert [b["owner"] for b in k["beneficial_owners"]] == ["Raj", "Ann"] and "ownership chart" in k["documents_missing"]
    x = py.do(T, "iso20022", {"workspace": ws, "xml": "<Document xmlns='urn:iso:std:iso:20022:tech:xsd:pain.001.001.03'><GrpHdr><MsgId>1</MsgId>"
                                                       "<CreDtTm>x</CreDtTm><NbOfTxs>2</NbOfTxs></GrpHdr></Document>"})
    assert not x["ok"] and any("NbOfTxs" in p for p in x["problems"])
    s = py.do(T, "safeguarding", {"workspace": ws, "days": [{"date": "2026-11-01", "owed_to_customers": 100, "safeguarded": 90}]})
    assert s["shortfall_days"] == ["2026-11-01"]
    with pytest.raises(py.PayDeskError, match="can read this desk"):
        _as_role(py, ws, "viewer", "add_dispute", {"network": "visa", "reason_code": "13.1", "amount": 1})
    assert "months" in _as_role(py, ws, "auditor", "prevention", {})


def _as_role(py, ws, role, part, a):
    from app.fin.desks import books_ent as E
    real = E.access
    E.access = lambda caller, w: {"owner": T, "role": role, "id": "x", "name": "Someone", "workspace": w}
    try:
        return py.do("someone-else", part, {"workspace": ws, **a})
    finally:
        E.access = real


def test_routes(py):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "payments_desk", trust="seekh")
    ws = _ws()
    c = TestClient(app)
    assert c.get("/api/payments/desk").json()["workspace"]["id"] == ws
    assert c.post("/api/payments/do/nope", json={"workspace": ws}).status_code == 400
    assert c.post("/api/payments/do/upload", json={"workspace": ws, "kind": "x", "text": ""}).status_code == 400
    assert c.get("/api/payments/chat").json()["id"]
    assert c.put("/api/payments/workspace", json={"workspace": "nope"}).status_code == 400
    assert c.get("/api/payments/download", params={"workspace": ws, "what": "doc"}).status_code == 400


@pytest.fixture
def py_server(py, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "payments_desk", trust="seekh")
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


def test_desk_in_a_real_browser(py, py_server, tmp_path):
    base, browser, key = py_server
    ws = _ws()
    _bank(ws)
    py.do(T, "settings", {"workspace": ws, "gateway": "stripe", "pct": 1.5, "fixed": 0.2, "window_days": 7, "source": "Stripe agreement"})
    py.do(T, "upload", {"workspace": ws, "kind": "orders", "text": ORDERS})
    py.do(T, "add_dispute", {"workspace": ws, "network": "mastercard", "reason_code": "4855", "amount": 50, "gateway": "stripe",
                             "received": (date.today() - timedelta(days=5)).isoformat(), "customer": "Mia"})
    py.do(T, "settings", {"workspace": ws, "threshold_pct": 0.5, "commission_pct": 10})
    py.do(T, "upload", {"workspace": ws, "kind": "failed", "text": f"customer,amount,plan,date,reason\nmia@example.com,19,Pro,{D2},card expired\n"})
    py.do(T, "upload", {"workspace": ws, "kind": "market", "text": "seller,amount,type,fee\nAnna,200,sale,2\nBob,10,sale,15\n"})
    f = tmp_path / "stripe.csv"
    f.write_text(SETTLE)
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    for w, h in ((1440, 900), (390, 844)):
        ctx = browser.new_context(viewport={"width": w, "height": h})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        if w == 1440:
            pg.goto(base + "/console/payments#/reconcile")
            pg.wait_for_selector("form[data-kind=settlements]", timeout=20000)
            pg.fill("form[data-kind=settlements] [name=gateway]", "stripe")
            pg.set_input_files("form[data-kind=settlements] [data-upfile]", str(f))
            pg.wait_for_selector("text=7 rows read from stripe.csv", timeout=20000)
            pg.wait_for_selector("text=Not found", timeout=20000)
            assert pg.locator("text=Fees above your contract").count() >= 1
            snap(pg, f"pay-reconcile-{w}")
        pg.goto(base + "/console/payments")
        pg.wait_for_selector("text=Needs you", timeout=20000)
        assert pg.locator(".cs-hero .k").count() == 4 and pg.locator(".py-chart svg rect").count() >= 1 and pg.locator(".py-gw").count() == 1
        snap(pg, f"pay-today-{w}")
        pg.goto(base + "/console/payments#/disputes/1")
        pg.wait_for_selector(".py-letter", timeout=20000)
        if w == 1440:
            pg.check("[data-ev='proof_of_delivery']")
            pg.click("[data-saveev]")
            pg.wait_for_selector("text=the evidence answers this reason code", timeout=20000)
            pg.select_option("form[data-form=status] [name=status]", "responded")
            pg.fill("form[data-form=status] [name=reference]", "MC-777")
            pg.click("form[data-form=status] [type=submit]")
            pg.wait_for_selector("text=ref MC-777", timeout=20000)
        snap(pg, f"pay-dispute-{w}")
        pg.goto(base + "/console/payments#/disputes")
        pg.wait_for_selector(".cr-filter", timeout=20000)
        if w == 1440:
            pg.fill("form[data-form=dispute] [name=reason_code]", "10.4")
            pg.fill("form[data-form=dispute] [name=amount]", "300")
            pg.fill("form[data-form=dispute] [name=window_days]", "10")
            pg.click("form[data-form=dispute] [type=submit]")
            pg.wait_for_url("**/disputes/2", timeout=20000)
            pg.wait_for_selector("text=Compelling evidence", timeout=20000)
            pg.wait_for_selector("text=Dispute added", timeout=20000)
        pg.goto(base + "/console/payments#/recurring")
        pg.wait_for_selector(".py-steps", timeout=20000)
        assert pg.locator(".cs-tag:has-text(\"Carried forward\")").count() == 1
        snap(pg, f"pay-recurring-{w}")
        pg.goto(base + "/console/payments#/firm")
        pg.wait_for_selector("text=Beneficial owners", timeout=20000)
        if w == 1440:
            pg.fill("form[data-form=kyb] [name=business]", "Shop Ltd")
            pg.fill("form[data-form=kyb] [name=threshold_pct]", "25")
            pg.fill("form[data-form=kyb] [name=ownership]", "Holdco, Shop Ltd, 60, no\nAnn, Holdco, 50, yes\nRaj, Shop Ltd, 40, yes")
            pg.click("form[data-form=kyb] [type=submit]")
            pg.wait_for_selector(".fm-out >> text=Raj", timeout=20000)
            pg.fill("form[data-form=sg] [name=days]", "2026-11-01, 120000, 118500\n2026-11-02, 100000, 100500")
            pg.click("form[data-form=sg] [type=submit]")
            pg.wait_for_selector(".py-sg .bad", timeout=20000)
        snap(pg, f"pay-firm-{w}")
        pg.goto(base + "/console/payments#/settings")
        pg.wait_for_selector("text=Gateways and your contract rates", timeout=20000)
        snap(pg, f"pay-settings-{w}")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), w
        ctx.close()
    assert not errs, errs
