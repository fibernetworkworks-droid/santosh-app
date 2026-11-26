"""CREDIT & LENDING DESK: the Credit & Lending employee's own section, built like Payroll, Tax and Cash & Treasury - its own chat (kind
'credit') with the desk block + the credit tool in view; borrowing (the APR by her country's method, offers side by side, invoice finance,
the readiness pack); applications (figures each with a source, the borrower's statement, her policy limits and rules, the memo, the key
facts, the conditions, the decision recorded as the named person's); the loan book (due against paid, days past due, payments that
happened, collections contacts checked against her contact rules and never sent); early warning and the ECL working paper; team roles;
the downloads; and the desk walked in a real browser."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def cr(env):
    from app import creditchat as CR
    CR._OF.clear()
    CR._BLOCK.clear()
    return CR


def _ws(name="Riverside Lending", cc="GB", cur="GBP"):
    from app.fin import profile as PR
    pv = PR.preview({"size": "business", "countries": [cc], "currency": cur, "name": name, "wants": []})
    return PR.apply(T, pv["answers"], pv["hash"])["id"]


def _months_ago(n: int, day: int = 5) -> str:
    d = date.today().replace(day=1)
    for _ in range(n):
        d = (d - timedelta(days=1)).replace(day=1)
    return d.replace(day=day).isoformat()


ROWS = ("date,narration,amount\n2026-06-01,SALES,9000\n2026-06-05,LOAN EMI,-800\n2026-07-01,SALES,9500\n2026-07-05,LOAN EMI,-800\n"
        "2026-07-09,CHQ RTN UNPAID,-120\n2026-08-01,SALES,9200\n2026-08-05,LOAN EMI,-800\n")


def test_hire_chat_block_and_wiring(cr):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert cr.summary(T)["hired"] is False
    hire.hire(T, "credit_lending", trust="seekh")
    d = cr.summary(T)
    assert d["hired"] and d["workspace"] is None and "approves or declines nothing" in d["foot"]
    chat = cr.current(T)
    assert cr.is_credit(chat["id"]) and cr.owns(T, chat["id"]) and cr.current(T)["id"] == chat["id"]
    assert "Books & Accounts" in cr.greeting(T)
    blk = cr.block(T)
    assert "<credit_desk>" in blk and "never approve, decline or pay out" in blk and "No business set up yet" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_crc.is_credit(conversation_id)" in src and "adm.admit_families(_crc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["credit_lending"] in cr.FAMILIES
    for f in ("callconv.py", "convs.py"):
        assert '"tax", "cash", "credit"' in (root / "server/app" / f).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/credit")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "creditdesk.js" in r.text
    html = (root / "server/app/static/console/creditdesk.html").read_text()
    for f in ("chatkit.js", "seodesk.css", "moneydesk.css", "cashdesk.css", "creditdesk.css", "creditdesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    assert "location.assign('/console/credit')" in (root / "server/app/static/console/v2.js").read_text()
    assert "credit_lending: 'creditdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/credit'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_borrowing_apr_offers_and_invoice_finance(cr):
    from app.employee import hire
    hire.hire(T, "credit_lending", trust="seekh")
    ws = _ws()
    a = cr.do(T, "apr", {"workspace": ws, "amount": 10000, "rate": 0, "term": 12, "payment": 900, "fee_pct": 0})
    assert a["method"] == "eu_annual" and a["cost_of_credit"] == 800 and a["apr_pct"] > 14     # GB = annual equivalent rate
    assert "check this" in cr.method_view(T, ws)["from"]
    cr.do(T, "add_offer", {"workspace": ws, "name": "Bank A", "amount": 20000, "rate": 8, "term": 36, "fee_pct": 2})
    cr.do(T, "add_offer", {"workspace": ws, "name": "Lender B", "amount": 20000, "rate": 7, "term": 36, "fees_upfront": 900})
    c = cr.do(T, "compare", {"workspace": ws})
    assert c["cheapest_by_total_cost"] == "Bank A" and c["offers"][0]["n"] == 1 and c["offers"][1]["apr_pct"] > c["offers"][0]["apr_pct"]
    with pytest.raises(cr.CreditDeskError, match="rate"):
        cr.do(T, "add_offer", {"workspace": ws, "name": "No rate", "amount": 1000, "term": 12})
    cr.do(T, "remove_offer", {"workspace": ws, "n": 2})
    assert [o["name"] for o in cr.do(T, "compare", {"workspace": ws})["offers"]] == ["Bank A"]
    f = cr.do(T, "invoice_finance", {"workspace": ws, "invoice": 10000, "advance_pct": 80, "fee_pct": 2, "days": 45})
    assert f["money_now"] == 7800 and f["cost"] == 200 and f["cost_a_year_pct"] > 20
    # her own method beats the country's remembered one
    cr.do(T, "method", {"workspace": ws, "method": "nominal_irr", "source": "our regulator's page"})
    m = cr.method_view(T, ws)
    assert m["method"] == "nominal_irr" and m["checked"]
    assert cr.do(T, "apr", {"workspace": ws, "amount": 10000, "rate": 10, "term": 12})["method"] == "nominal_irr"
    with pytest.raises(cr.CreditDeskError):
        cr.do(T, "method", {"workspace": ws, "method": "guess"})


def test_applications_memo_rules_kfs_and_decision(cr):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "credit_lending", trust="seekh")
    ws = _ws()
    a = cr.do(T, "add_app", {"workspace": ws, "borrower": "Leaf & Co", "amount": 25000, "purpose": "new oven", "rate": 11, "term": 36})["app"]
    n = a["n"]
    with pytest.raises(cr.CreditDeskError, match="source"):
        cr.do(T, "app_figure", {"workspace": ws, "n": n, "name": "ebitda", "value": 40000})       # no source = not used
    cr.do(T, "app_figure", {"workspace": ws, "n": n, "name": "EBITDA", "value": 40000, "source": "2025 accounts p3"})
    cr.do(T, "app_figure", {"workspace": ws, "n": n, "name": "debt_service", "value": 36000, "source": "2025 accounts p5"})
    cr.do(T, "edit_app", {"workspace": ws, "n": n, "rows_csv": ROWS})
    cr.do(T, "policy", {"workspace": ws, "ratio": "dscr", "limit": 1.25})
    cr.do(T, "rule", {"workspace": ws, "code": "MIN_TRADING", "field": "months_trading", "op": ">=", "value": "24"})
    with pytest.raises(cr.CreditDeskError, match="discrimination"):
        cr.do(T, "rule", {"workspace": ws, "code": "X", "field": "religion", "op": "==", "value": "a"})
    with pytest.raises(cr.CreditDeskError, match="discrimination"):
        cr.do(T, "app_field", {"workspace": ws, "n": n, "field": "pincode", "value": "400001"})
    cr.do(T, "app_field", {"workspace": ws, "n": n, "field": "months_trading", "value": "18"})
    cr.do(T, "condition", {"workspace": ws, "n": n, "name": "Signed guarantee", "status": "missing", "due": "2026-01-01"})
    cr.do(T, "condition", {"workspace": ws, "n": n, "name": "Insurance", "status": "received"})
    with pytest.raises(cr.CreditDeskError, match="waived_by"):
        cr.do(T, "condition", {"workspace": ws, "n": n, "name": "Valuation", "status": "waived"})
    o = cr.do(T, "app", {"workspace": ws, "n": n})
    assert o["memo"]["ratios"]["dscr"]["value"] == 1.11 and o["memo"]["policy_flags"]                 # below her 1.25
    assert o["analysis"]["figures"]["bounced_items"]["value"] == 1 and o["rows_count"] == 7
    assert o["rules"]["rule_hits"][0]["code"] == "MIN_TRADING"
    assert o["kfs"]["apr"]["apr_pct"] > 11 and "DRAFT" in o["kfs"]["kfs_markdown"]
    assert o["checklist"]["missing"] == ["Signed guarantee"] and not o["checklist"]["ready_to_draw"]
    assert "no score" in o["memo"]["decider"]
    d = cr.summary(T)["desk"]
    assert any("past their date" in x["say"] for x in d["needs"])
    c = TestClient(app)
    pdf = c.get("/api/credit/download", params={"workspace": ws, "what": "memo", "n": n})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    md = c.get("/api/credit/download", params={"workspace": ws, "what": "memo_md", "n": n})
    assert md.status_code == 200 and "S1: 2025 accounts p3" in md.text
    kf = c.get("/api/credit/download", params={"workspace": ws, "what": "kfs", "n": n})
    assert kf.status_code == 200 and "Key Fact Statement" in kf.text
    # Hoola records the named person's decision - it never makes one
    with pytest.raises(cr.CreditDeskError, match="decided_by"):
        cr.do(T, "close_app", {"workspace": ws, "n": n, "outcome": "approved"})
    cr.do(T, "close_app", {"workspace": ws, "n": n, "decided_by": "Credit committee", "outcome": "Agreed at 20,000 with a guarantee"})
    assert cr.do(T, "app", {"workspace": ws, "n": n})["status"] == "closed"
    from app.fin import laws as L
    with pytest.raises(L.Refused):
        cr._engine(T, "x", "approve", {})
    with pytest.raises(cr.CreditDeskError, match="Not a Credit"):
        cr.do(T, "approve", {"workspace": ws})


def test_loan_book_collections_risk_and_roles(cr):
    from app.employee import hire
    hire.hire(T, "credit_lending", trust="seekh")
    ws = _ws()
    st = _months_ago(4)
    lv = cr.do(T, "add_loan", {"workspace": ws, "name": "Mia's Cafe", "side": "lent", "amount": 12000, "rate": 9, "term": 24, "start": st,
                               "tz": "Europe/London"})["loan"]
    assert lv["payment"] == 548.22 and lv["arrears"] > 0 and lv["days_past_due"] > 90 and lv["bucket"] == "90+"
    with pytest.raises(cr.CreditDeskError, match="has happened"):
        cr.do(T, "payment", {"workspace": ws, "n": 1, "amount": 10, "date": (date.today() + timedelta(days=3)).isoformat()})
    lv = cr.do(T, "payment", {"workspace": ws, "n": 1, "amount": 548.22, "date": st})["loan"]
    assert lv["paid_so_far"] == 548.22 and lv["outstanding"] < 12000 and lv["rising"]
    cr.do(T, "add_loan", {"workspace": ws, "name": "High St Bank", "side": "borrowed", "amount": 30000, "rate": 7.5, "term": 60,
                          "start": (date.today() + timedelta(days=3)).isoformat()})
    b = cr.do(T, "book", {"workspace": ws})
    assert b["lent"]["count"] == 1 and b["lent"]["in_arrears"] == 1 and b["borrowed"]["due_soon"][0]["name"] == "High St Bank"
    needs = " | ".join(x["say"] for x in cr.summary(T)["desk"]["needs"])
    assert "days past due" in needs and "High St Bank" in needs and "PD and LGD" in needs and "contact rules" in needs
    # collections: checked against her rules + Hoola's floor, logged as planned, never sent
    cr.do(T, "contact_rules", {"workspace": ws, "from_hour": 9, "to_hour": 19, "per_week": 2, "channels": ["call", "email"], "no_days": ["sun"]})
    with pytest.raises(cr.CreditDeskError, match="outside 09:00-19:00"):
        cr.do(T, "collect", {"workspace": ws, "borrower": "Mia's Cafe", "channel": "call", "when": "2026-12-01T20:30", "message": "Hello"})
    with pytest.raises(cr.CreditDeskError, match="threatens"):
        cr.do(T, "collect", {"workspace": ws, "borrower": "Mia's Cafe", "channel": "call", "when": "2026-12-01T10:00",
                             "message": "We will call the police"})
    with pytest.raises(cr.CreditDeskError, match="only the borrower"):
        cr.do(T, "collect", {"workspace": ws, "borrower": "Mia's Cafe", "channel": "call", "when": "2026-12-01T10:00", "to": "employer"})
    with pytest.raises(cr.CreditDeskError, match="whatsapp"):
        cr.do(T, "collect", {"workspace": ws, "borrower": "Mia's Cafe", "channel": "whatsapp", "when": "2026-12-01T10:00"})
    ok = cr.do(T, "collect", {"workspace": ws, "borrower": "Mia's Cafe", "channel": "call", "when": "2026-12-01T10:00",
                              "message": "Hello, a payment was due. Can we agree a date?"})
    assert ok["contact"]["planned"] and ok["contact"]["tz"] == "Europe/London" and "does not send" in ok["says"]
    assert cr.do(T, "contacts", {"workspace": ws})["log"][0]["channel"] == "call"
    # risk: early warning + ECL only with her own PD / LGD
    r = cr.do(T, "risk", {"workspace": ws})
    assert r["ews"] and r["ecl"] is None and r["needs_pd_lgd"][0]["name"] == "Mia's Cafe"
    with pytest.raises(cr.CreditDeskError, match="between 0 and 1"):
        cr.do(T, "edit_loan", {"workspace": ws, "n": 1, "pd": 5})
    cr.do(T, "edit_loan", {"workspace": ws, "n": 1, "pd": 0.05, "lgd": 0.4})
    r = cr.do(T, "risk", {"workspace": ws})
    e = r["ecl"]
    assert e["by_stage"]["stage3"] > 0 and e["total_ecl"] == round(e["rows"][0]["ead"] * 0.4, 2)          # 90+ days = stage 3, PD 1
    # downloads + roles
    from app.main import app
    csv = TestClient(app).get("/api/credit/download", params={"workspace": ws, "what": "book"})
    assert csv.status_code == 200 and "Mia's Cafe" in csv.text and "pays out nothing" in csv.text
    with pytest.raises(cr.CreditDeskError, match="can read this desk"):
        _as_role(cr, ws, "viewer", "payment", {"n": 1, "amount": 1})
    assert "loans" in _as_role(cr, ws, "auditor", "book", {})
    cr.do(T, "remove_loan", {"workspace": ws, "n": 2})
    assert cr.do(T, "book", {"workspace": ws})["borrowed"]["count"] == 0
    cr.forget(T)
    assert "Lent: 1 loans" in cr.block(T) and "in arrears" in cr.greeting(T)


def _as_role(cr, ws, role, part, a):
    from app.fin.desks import books_ent as E
    real = E.access
    E.access = lambda caller, w: {"owner": T, "role": role, "id": "x", "name": "Someone", "workspace": w}
    try:
        return cr.do("someone-else", part, {"workspace": ws, **a})
    finally:
        E.access = real


def test_routes(cr):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "credit_lending", trust="seekh")
    ws = _ws()
    c = TestClient(app)
    d = c.get("/api/credit/desk").json()
    assert d["hired"] and d["workspace"]["id"] == ws and d["desk"]["method"]["method"] == "eu_annual"
    assert c.post("/api/credit/do/add_loan", json={"workspace": ws, "name": "A", "amount": 100, "rate": 5, "term": 6,
                                                   "start": "2026-01-05"}).status_code == 200
    assert c.post("/api/credit/do/nope", json={"workspace": ws}).status_code == 400
    assert c.post("/api/credit/do/add_loan", json={"workspace": ws, "name": "A", "amount": 100, "term": 6, "start": "x"}).status_code == 400
    assert c.get("/api/credit/chat").json()["id"]
    assert c.put("/api/credit/workspace", json={"workspace": "nope"}).status_code == 400
    assert c.get("/api/credit/download", params={"workspace": ws, "what": "doc"}).status_code == 400


@pytest.fixture
def cr_server(cr, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "credit_lending", trust="seekh")
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


def test_desk_in_a_real_browser(cr, cr_server):
    base, browser, key = cr_server
    ws = _ws()
    cr.do(T, "add_loan", {"workspace": ws, "name": "Mia's Cafe", "side": "lent", "amount": 12000, "rate": 9, "term": 24,
                          "start": _months_ago(4), "tz": "Europe/London"})
    cr.do(T, "payment", {"workspace": ws, "n": 1, "amount": 548.22, "date": _months_ago(4)})
    cr.do(T, "add_loan", {"workspace": ws, "name": "Oak Joinery", "side": "lent", "amount": 8000, "rate": 10, "term": 12,
                          "start": _months_ago(1, 1), "pd": 0.02, "lgd": 0.45})
    cr.do(T, "add_loan", {"workspace": ws, "name": "High St Bank", "side": "borrowed", "amount": 30000, "rate": 7.5, "term": 60,
                          "start": (date.today() + timedelta(days=3)).isoformat()})
    a = cr.do(T, "add_app", {"workspace": ws, "borrower": "Leaf & Co", "amount": 25000, "purpose": "new oven", "rate": 11, "term": 36})["app"]
    cr.do(T, "app_figure", {"workspace": ws, "n": a["n"], "name": "ebitda", "value": 40000, "source": "2025 accounts p3"})
    cr.do(T, "app_figure", {"workspace": ws, "n": a["n"], "name": "debt_service", "value": 15000, "source": "2025 accounts p5"})
    cr.do(T, "edit_app", {"workspace": ws, "n": a["n"], "rows_csv": ROWS})
    cr.do(T, "condition", {"workspace": ws, "n": a["n"], "name": "Signed guarantee", "status": "missing", "due": "2026-01-01"})
    cr.do(T, "condition", {"workspace": ws, "n": a["n"], "name": "Insurance", "status": "received"})
    cr.do(T, "add_offer", {"workspace": ws, "name": "Bank A", "amount": 20000, "rate": 8, "term": 36, "fee_pct": 2})
    cr.do(T, "add_offer", {"workspace": ws, "name": "Lender B", "amount": 20000, "rate": 7, "term": 36, "fees_upfront": 900})
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
        pg.goto(base + "/console/credit")
        pg.wait_for_selector("text=Needs you", timeout=20000)
        assert pg.locator(".cr-hero").count() == 1 and pg.locator(".cr-age span").count() >= 2
        assert pg.locator(".md-kpi").count() == 4
        snap(pg, f"credit-today-{w}")
        pg.goto(base + "/console/credit#/borrow")
        pg.wait_for_selector(".cr-offer.best", timeout=20000)
        pg.click("[data-aprgo]")
        pg.wait_for_selector(".cr-apr .v", timeout=20000)
        if w == 1440:
            pg.click("[data-ready]")
            pg.wait_for_selector("text=/Make it again|Try again/", timeout=20000)
        snap(pg, f"credit-borrow-{w}")
        pg.goto(base + "/console/credit#/apps")
        pg.wait_for_selector(".cr-app", timeout=20000)
        pg.click(".cr-app")
        pg.wait_for_selector(".cr-ratio", timeout=20000)
        assert pg.locator("text=Key facts draft").count() == 1 and pg.locator(".cr-st").count() >= 2
        snap(pg, f"credit-app-{w}")
        pg.goto(base + "/console/credit#/loans")
        pg.wait_for_selector("text=Add a loan" if w == 1440 else ".cs-wk", timeout=20000)
        snap(pg, f"credit-loans-{w}")
        pg.goto(base + "/console/credit#/loans/1")
        pg.wait_for_selector("text=Before you contact", timeout=20000)
        if w == 1440:
            pg.fill("form[data-form=collect] [name=when]", "2026-12-01T22:30")
            pg.click("[data-collect]")
            pg.wait_for_selector(".cr-verdict.bad", timeout=20000)
            pg.fill("form[data-form=collect] [name=when]", "2026-12-01T10:30")
            pg.fill("form[data-form=collect] [name=message]", "Hello, a payment was due. Can we agree a date?")
            pg.click("[data-collect]")
            pg.wait_for_selector(".cr-verdict.ok", timeout=20000)
            pg.fill("form[data-form=pay] [name=amount]", "200")
            pg.click("form[data-form=pay] [type=submit]")
            pg.wait_for_selector("text=Payment recorded", timeout=20000)
        snap(pg, f"credit-loan-{w}")
        pg.goto(base + "/console/credit#/risk")
        pg.wait_for_selector("text=ECL working paper", timeout=20000)
        pg.wait_for_selector(".cr-stages", timeout=20000)
        snap(pg, f"credit-risk-{w}")
        pg.goto(base + "/console/credit#/settings")
        pg.wait_for_selector("text=Collections contact rules", timeout=20000)
        if w == 1440:
            pg.fill("form[data-form=rule] [name=code]", "MIN_TRADING")
            pg.fill("form[data-form=rule] [name=field]", "months_trading")
            pg.fill("form[data-form=rule] [name=value]", "24")
            pg.click("form[data-form=rule] [type=submit]")
            pg.wait_for_selector("td >> text=MIN_TRADING", timeout=20000)
        snap(pg, f"credit-settings-{w}")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), w
        ctx.close()
    assert not errs, errs
