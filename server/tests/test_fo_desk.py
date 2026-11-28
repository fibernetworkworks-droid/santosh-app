"""FINANCE DESK ASSISTANT: the Finance Desk Assistant employee's own section, built like Public Finance and Digital Assets - its own
chat (kind 'finops') with the desk block + the finance desk tool in view; invoices owed and owing aged by party; bills matched to orders
and goods received with the approver's decision recorded (never made); tax withheld against the tax office's statement; transactions
checked only against HER cash threshold with accounts kept as a fingerprint and the last 4; names screened only against HER own list;
borrowers against HER policy floors with a credit memo draft; goals by scenario; read-only team roles; the downloads; nothing paid,
filed, blocked or approved; and the desk walked in a real browser."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"
D = lambda n: (date.today() + timedelta(days=n)).isoformat()      # noqa: E731
REC = f"Customer,Invoice No,Due Date,Amount,Paid\nAcme,I-1,{D(-120)},5000,1000\nAcme,I-2,{D(-10)},2000,0\nBolt,I-3,{D(20)},3000,0\nCyan,I-4,{D(-45)},800,800\n"
POS = "PO,Qty,Price\nP1,10,100\nP2,5,200\nP3,4,50\n"
GRN = "PO,Qty\nP1,10\nP2,3\n"
BIL = "Invoice No,PO,Qty,Price\nB1,P1,10,100\nB2,P2,5,200\nB3,P3,4,50\nB4,P9,1,10\n"
TXN = ("Account,Date,Amount,Type,Counterparty\n" + "".join(f"4111111111111111,{D(-i)},{9500 + i * 10},cash_in,\n" for i in range(4))
       + f"22223333,{D(-1)},50000,credit,Ann\n22223333,{D(-1)},49000,debit,Bo\n")


@pytest.fixture
def fo(env):
    from app import fochat as FO
    FO._OF.clear()
    FO._BLOCK.clear()
    return FO


def _desk(fo, country="GB", currency="GBP"):
    return fo.setup(T, {"name": "Acme finance", "country": country, "currency": currency, "size": "business"})["desk"]["id"]


def test_hire_setup_chat_block_and_wiring(fo):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert fo.summary(T)["hired"] is False
    hire.hire(T, "vitt_sahayak", trust="seekh")
    d = fo.summary(T)
    assert d["hired"] and d["workspace"] is None and "never pays" in d["foot"]
    assert "Set up your desk" in fo.greeting(T) and "No desk set up yet" in fo.block(T)
    ws = _desk(fo)
    d = fo.summary(T)
    assert d["workspace"]["id"] == ws and d["can_write"] and d["desk"]["match"]["empty"]
    chat = fo.current(T)
    assert fo.is_finops(chat["id"]) and fo.owns(T, chat["id"])
    fo.forget(T)
    assert "<finops_desk>" in fo.block(T) and "credit committee" in fo.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_foc.is_finops(conversation_id)" in src and "adm.admit_families(_foc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["vitt_sahayak"] in fo.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"finops"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/finops")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "fodesk.js" in r.text
    html = (root / "server/app/static/console/fodesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "mktdesk.css", "cmdesk.css", "dgdesk.css", "pbdesk.css", "fodesk.css", "fodesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/finops')" in (root / "server/app/static/console/v2.js").read_text()
    assert "vitt_sahayak: 'fodesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/finops'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_ageing_match_and_decision(fo):
    from app.employee import hire
    hire.hire(T, "vitt_sahayak", trust="seekh")
    ws = _desk(fo)
    r = fo.do(T, "upload", {"workspace": ws, "kind": "receivables", "text": REC})
    assert r["rows"] == 4
    assert "already on the desk" in fo.do(T, "upload", {"workspace": ws, "kind": "receivables", "text": REC})["says"]
    m = fo.do(T, "money", {"workspace": ws})["receivables"]
    assert m["buckets"]["90+"] == 4000 and m["buckets"]["1-30"] == 2000 and m["buckets"]["not_due"] == 3000
    assert list(m["by_party"])[0] == "Acme"
    for k, t in (("pos", POS), ("grns", GRN), ("bills", BIL)):
        fo.do(T, "upload", {"workspace": ws, "kind": k, "text": t})
    mt = fo.do(T, "match", {"workspace": ws})
    st = {x["invoice"]: x for x in mt["results"]}
    assert st["B1"]["status"] == "match" and "goods not received" in " ".join(st["B3"]["issues"]) and "PO not found" in st["B4"]["issues"]
    assert mt["hold"] == 3 and mt["held_value"] == 1210
    needs = " | ".join(x["say"] for x in fo.summary(T)["desk"]["needs"])
    assert "over 90 days late" in needs and "3 bills on hold" in needs
    with pytest.raises(fo.FoDeskError, match="key"):
        fo.do(T, "decide", {"workspace": ws, "key": "pay:B2", "decision": "pay"})
    fo.do(T, "decide", {"workspace": ws, "key": "bill:B2", "decision": "Release - 2 more units arrived, GRN to follow"})
    mt = fo.do(T, "match", {"workspace": ws})
    assert next(x for x in mt["results"] if x["invoice"] == "B2")["decision"]["decision"].startswith("Release") and mt["to_decide"] == 2
    with pytest.raises(fo.FoDeskError, match="action"):
        fo.do(T, "pay", {"workspace": ws})


def test_tax_aml_screen_credit_goals(fo):
    from app.employee import hire
    hire.hire(T, "vitt_sahayak", trust="seekh")
    ws = _desk(fo, "IN", "INR")
    fo.do(T, "upload", {"workspace": ws, "kind": "books_tds", "text": "Party,Section,TDS\nAcme,194C,1000\nBolt,194J,500\n"})
    fo.do(T, "upload", {"workspace": ws, "kind": "portal_tds", "text": "Deductor,Section,Tax Deducted\nAcme,194C,1000\nCyan,194J,300\n"})
    tx = fo.do(T, "tax", {"workspace": ws})
    assert tx["withheld"]["to_check"] == 2 and tx["advance"]["need"] and "Bolt/194J" in tx["withheld"]["what_to_ask"] and tx["withheld"]["rows"][0]["party"] == "Acme"
    fo.do(T, "settings", {"workspace": ws, "adv_liability": 100000, "adv_tds": 20000, "adv_fy": 2026})
    adv = fo.do(T, "tax", {"workspace": ws})["advance"]
    assert adv["instalments"][0]["due"] == "2026-06-15" and adv["instalments"][-1]["cumulative_amount"] == 80000
    # AML: never on a threshold of Hoola's own
    fo.do(T, "upload", {"workspace": ws, "kind": "txns", "text": TXN})
    st = fo._state(T, ws)
    assert "4111111111111111" not in str(st) and st["txns"][0]["account_4"] == "…1111"
    assert fo.do(T, "aml", {"workspace": ws})["alerts"]["need_threshold"]
    fo.do(T, "settings", {"workspace": ws, "cash_threshold": 10000})
    al = fo.do(T, "aml", {"workspace": ws})["alerts"]
    rules = {(x["account"], x["rule"]) for x in al["alerts"]}
    assert ("…1111", "structuring_like") in rules and ("…3333", "pass_through") in rules and "INR" in al["alerts"][0]["why"]
    fo.do(T, "decide", {"workspace": ws, "key": al["alerts"][0]["key"], "decision": "Closed - salary of a shop owner, documents on file"})
    assert fo.do(T, "aml", {"workspace": ws})["alerts"]["open"] == len(al["alerts"]) - 1
    # screening only against HER list
    fo.do(T, "upload", {"workspace": ws, "kind": "names", "text": "Name,Ref\nMr Rajesh Kumar,C1\nSita Rao,C2\n"})
    assert fo.do(T, "aml", {"workspace": ws})["screen"]["need_watch"]
    fo.do(T, "upload", {"workspace": ws, "kind": "watch", "text": "Name,List,Ref\nRajesh Kumaar,Own list,W1\n"})
    sc = fo.do(T, "aml", {"workspace": ws})["screen"]
    assert sc["results"][0]["possible_matches"][0]["ref"] == "W1" and not sc["results"][1]["possible_matches"] and sc["to_review"] == 1
    # credit: her floors only
    fo.do(T, "borrower", {"workspace": ws, "name": "Bolt Ltd", "purpose": "working capital", "amount": 500000, "revenue": 1000000, "ebitda": 150000,
                          "net_profit": 60000, "interest": 50000, "debt_service": 120000, "current_assets": 300000, "current_liabilities": 280000,
                          "total_debt": 400000, "net_worth": 200000, "prev_revenue": 800000})
    cr = fo.do(T, "credit", {"workspace": ws})
    b = cr["borrowers"][0]
    assert b["ratios"]["dscr"] == 1.25 and b["ratios"]["debt_to_equity"] == 2.0 and cr["no_policy"] and not b["flags"]
    fo.do(T, "settings", {"workspace": ws, "policy": {"dscr": 1.3, "debt_to_equity": 1.5}})
    b = fo.do(T, "credit", {"workspace": ws})["borrowers"][0]
    assert len(b["flags"]) == 2 and "below your floor of 1.3" in b["flags"][0] and "Credit memo (DRAFT)" in b["memo"] and "revenue: +25.0%" in b["trend"][0]
    # goals: her inflation, scenario returns
    with pytest.raises(fo.FoDeskError, match="inflation"):
        fo.do(T, "goal", {"workspace": ws, "name": "School fees", "target": 1000000, "years": 10})
    fo.do(T, "goal", {"workspace": ws, "name": "School fees", "target": 1000000, "years": 10, "inflation": 6})
    g = fo.do(T, "goals", {"workspace": ws})["goals"][0]
    assert [x["scenario"] for x in g["scenarios"]] == ["low", "mid", "high"] and g["amount_needed_then"] > 1000000


def test_roles_routes_downloads(fo, monkeypatch):
    from app.employee import hire
    from app.fin.desks import books_ent as E
    from app.main import app
    hire.hire(T, "vitt_sahayak", trust="seekh")
    ws = _desk(fo, "US", "USD")
    fo.do(T, "upload", {"workspace": ws, "kind": "receivables", "text": REC})
    assert fo.do(T, "tax", {"workspace": ws})["advance"]["not_built"]
    real = E.access
    monkeypatch.setattr(E, "access", lambda caller, w: {**real(T, w), "role": "viewer", "name": "Bo"} if caller == "bo" else real(caller, w))
    assert fo.do("bo", "money", {"workspace": ws})["receivables"]["total_outstanding"] == 9000
    with pytest.raises(fo.FoDeskError, match="read this desk"):
        fo.do("bo", "settings", {"workspace": ws, "cash_threshold": 1})
    c = TestClient(app)
    assert c.get("/api/finops/desk").json()["workspace"]["id"] == ws
    r = c.get(f"/api/finops/download?workspace={ws}&what=receivables")
    assert r.status_code == 200 and "Acme" in r.text and "90+" in r.text
    fo.do(T, "borrower", {"workspace": ws, "name": "Bolt Ltd", "revenue": 100, "ebitda": 20})
    n = fo._state(T, ws)["borrowers"][0]["n"]
    r = c.get(f"/api/finops/download?workspace={ws}&what=memo:{n}")
    assert r.status_code == 200 and "Credit memo (DRAFT)" in r.text
    assert c.post("/api/finops/do/pay_now", json={"workspace": ws}).status_code in (400, 403)
    assert c.post("/api/finops/do/add", json={"workspace": ws, "register": "txns", "account": "4111111111111111", "date": D(0),
                                              "amount": 10, "type": "credit", "cvv": "123"}).status_code == 403
    assert c.get("/api/finops/chat").json()["id"]


@pytest.fixture
def fo_server(fo, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "vitt_sahayak", trust="seekh")
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


def test_desk_in_a_real_browser(fo, fo_server, tmp_path):
    base, browser, key = fo_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=20000)

    def up(pg, kind, name, text, wait):
        f = tmp_path / name
        f.write_text(text)
        for tries in (1, 2, 3):  # a redraw that lands between the pick and its change event takes the file box away: pick again
            pg.wait_for_timeout(250)
            pg.set_input_files(f"form[data-kind={kind}] input[type=file]", str(f))
            try:
                pg.wait_for_selector(wait, timeout=10000 if tries < 3 else 20000)
                break
            except Exception:
                if tries == 3:
                    raise

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/finops")
    pg.wait_for_selector("text=Set up your finance desk", timeout=20000)
    snap(pg, "fo-setup-1440")
    pg.fill("form[data-form=setup] [name=country]", "IN")
    pg.fill("form[data-form=setup] [name=currency]", "INR")
    pg.click("form[data-form=setup] [type=submit]")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # owed and owing
    go(pg, "#/money", "form[data-kind=receivables]")
    up(pg, "receivables", "r.csv", REC, ".fo-age")
    up(pg, "payables", "p.csv", f"Supplier,Invoice No,Due Date,Amount\nZen,S-1,{D(-40)},1500\nYak,S-2,{D(5)},700\n", "text=By supplier")
    snap(pg, "fo-money-1440")
    # three-way match + the approver's decision
    go(pg, "#/match", "form[data-kind=pos]")
    up(pg, "pos", "po.csv", POS, "text=Purchase orders · 3")
    up(pg, "grns", "g.csv", GRN, "text=Goods received · 2")
    up(pg, "bills", "b.csv", BIL, "text=The bills")
    pg.fill("form[data-form=decide][data-key='bill:B2'] [name=decision]", "Release - the rest arrives Friday")
    pg.click("form[data-form=decide][data-key='bill:B2'] [type=submit]")
    pg.wait_for_selector(".pb-dec", timeout=20000)
    snap(pg, "fo-match-1440")
    # tax withheld + advance tax
    go(pg, "#/tax", "form[data-kind=books_tds]")
    up(pg, "books_tds", "bt.csv", "Party,Section,TDS\nAcme,194C,1000\nBolt,194J,500\n", "text=Parties")
    up(pg, "portal_tds", "pt.csv", "Deductor,Section,Tax Deducted\nAcme,194C,1000\nCyan,194J,300\n", "text=What to ask")
    pg.fill("form[data-form=advance] [name=adv_liability]", "100000")
    pg.fill("form[data-form=advance] [name=adv_tds]", "20000")
    pg.fill("form[data-form=advance] [name=adv_fy]", "2026")
    pg.click("form[data-form=advance] [type=submit]")
    pg.wait_for_selector(".cm-line", timeout=20000)
    snap(pg, "fo-tax-1440")
    # settings: her threshold + floors
    go(pg, "#/settings", "form[data-form=checks]")
    pg.fill("form[data-form=checks] [name=cash_threshold]", "10000")
    pg.click("form[data-form=checks] [type=submit]")
    pg.wait_for_selector("text=Saved", timeout=20000)
    pg.fill("form[data-form=policy] [name=dscr]", "1.3")
    pg.fill("form[data-form=policy] [name=debt_to_equity]", "1.5")
    pg.click("form[data-form=policy] [type=submit]")
    pg.wait_for_timeout(600)
    snap(pg, "fo-settings-1440")
    # alerts + screening
    go(pg, "#/aml", "form[data-kind=txns]")
    up(pg, "txns", "t.csv", TXN, "text=Account …1111")
    assert "4111111111111111" not in pg.content()
    up(pg, "names", "n.csv", "Name,Ref\nMr Rajesh Kumar,C1\nSita Rao,C2\n", "text=Add your own watch list")
    up(pg, "watch", "w.csv", "Name,List,Ref\nRajesh Kumaar,Own list,W1\n", ".fo-hit")
    snap(pg, "fo-aml-1440")
    # credit
    go(pg, "#/credit", "form[data-form=borrower]")
    for n, v in (("name", "Bolt Traders Ltd"), ("purpose", "Working capital"), ("amount", "500000"), ("revenue", "1000000"), ("ebitda", "150000"),
                 ("net_profit", "60000"), ("interest", "50000"), ("debt_service", "120000"), ("current_assets", "300000"),
                 ("current_liabilities", "280000"), ("total_debt", "400000"), ("net_worth", "200000"), ("prev_revenue", "800000")):
        pg.fill(f"form[data-form=borrower] [name={n}]", v)
    pg.click("form[data-form=borrower] [type=submit]")
    pg.wait_for_selector(".fo-rat", timeout=20000)
    pg.click("summary:has-text('The memo draft')")
    snap(pg, "fo-credit-1440")
    # goals
    go(pg, "#/goals", "form[data-form=goal]")
    for n, v in (("name", "School fees"), ("target", "1000000"), ("years", "10"), ("current", "50000"), ("inflation", "6")):
        pg.fill(f"form[data-form=goal] [name={n}]", v)
    pg.click("form[data-form=goal] [type=submit]")
    pg.wait_for_selector(".mk-bars", timeout=20000)
    snap(pg, "fo-goals-1440")
    go(pg, "#/today", ".cs-hero")
    pg.wait_for_selector(".iv-donut", timeout=20000)
    snap(pg, "fo-today-1440")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".iv-donut", "today"), ("#/money", ".fo-age", "money"), ("#/match", ".pb-res", "match"), ("#/tax", ".cm-line", "tax"),
                             ("#/aml", ".fo-hit", "aml"), ("#/credit", ".fo-rat", "credit"), ("#/goals", ".mk-bars", "goals"),
                             ("#/settings", "form[data-form=checks]", "settings")):
        pg.goto(base + "/console/finops" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"fo-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#foPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
