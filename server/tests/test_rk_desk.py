"""RISK DESK: the Risk Desk employee's own section, built like the Finance Desk and Public Finance - its own chat (kind 'risk') with the
desk block + the risk desk tool in view; a portfolio checked against HER mandate limits with rebalance proposals for the manager; order
tickets prepared with flags on HER limits and never placed; applications run against HER policy rules (rules on protected grounds
refused) with the credit officer's decision recorded; key fact statement drafts; the loan book by days past due and an ECL working
paper; payments checked only on HER velocity limits with accounts kept as a fingerprint and the last 4; round-trip trades as evidence;
valuations on HER cash flows; read-only team roles; the downloads; and the desk walked in a real browser."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"
D = lambda n: (date.today() + timedelta(days=n)).isoformat()      # noqa: E731
HOLD = "Symbol,Qty,Price,Sector\nINFY,100,1500,IT\nTCS,40,3500,IT\nHDFCBANK,80,1600,Banks\nITC,500,400,FMCG\n"
TGT = "Name,Target\nIT,40\nBanks,30\nFMCG,30\n"
RULES = "Field,Op,Value,Code,Severity\nfoir_pct,<=,50,FOIR_HIGH,refer\nbureau_score,>=,700,LOW_SCORE,decline\nage,>=,21,AGE_MIN,refer\n"
LOANS = f"ID,Outstanding,Oldest Due Date\nL1,100000,{D(0)}\nL2,50000,{D(-20)}\nL3,80000,{D(-70)}\nL4,120000,{D(-120)}\n"
EXP = "ID,EAD,PD,LGD,DPD\nE1,100000,0.02,0.4,0\nE2,50000,0.05,0.5,45\nE3,80000,0.1,0.6,120\n"
TXN = ("Account,Time,Amount,Device\n" + "".join(f"4111111111111111,{D(-1)}T10:0{i}:00,{2000 + i},d1\n" for i in range(6))
       + f"22223333,{D(-1)}T11:00:00,500,d1\n55556666,{D(-1)}T12:00:00,300,d1\n")
TRD = (f"Client,Symbol,Side,Qty,Price,Time\nC1,ABC,buy,1000,50,{D(-1)}T10:00:00\nC1,ABC,sell,1000,50.2,{D(-1)}T10:20:00\n"
       f"C2,XYZ,buy,500,20,{D(-1)}T10:00:00\n")


@pytest.fixture
def rk(env):
    from app import rkchat as RK
    RK._OF.clear()
    RK._BLOCK.clear()
    return RK


def _desk(rk, country="IN", currency="INR"):
    return rk.setup(T, {"name": "Acme risk", "country": country, "currency": currency, "size": "institution"})["desk"]["id"]


def test_hire_setup_chat_block_and_wiring(rk):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert rk.summary(T)["hired"] is False
    hire.hire(T, "risk_desk", trust="seekh")
    d = rk.summary(T)
    assert d["hired"] and d["workspace"] is None and "never places an order" in d["foot"]
    assert "Set up your desk" in rk.greeting(T) and "No desk set up yet" in rk.block(T)
    ws = _desk(rk)
    d = rk.summary(T)
    assert d["workspace"]["id"] == ws and d["can_write"] and d["desk"]["portfolio"]["drift"]["empty"]
    chat = rk.current(T)
    assert rk.is_risk(chat["id"]) and rk.owns(T, chat["id"])
    rk.forget(T)
    assert "<risk_desk>" in rk.block(T) and "Never say what to buy or sell" in rk.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_rkc.is_risk(conversation_id)" in src and "adm.admit_families(_rkc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["risk_desk"] in rk.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"risk"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/risk")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "rkdesk.js" in r.text
    html = (root / "server/app/static/console/rkdesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "pbdesk.css", "fodesk.css", "rkdesk.css", "rkdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/risk')" in (root / "server/app/static/console/v2.js").read_text()
    assert "risk_desk: 'rkdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/risk'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_portfolio_and_tickets(rk):
    from app.employee import hire
    hire.hire(T, "risk_desk", trust="seekh")
    ws = _desk(rk)
    rk.do(T, "upload", {"workspace": ws, "kind": "holdings", "text": HOLD})
    rk.do(T, "upload", {"workspace": ws, "kind": "targets", "text": TGT})
    pf = rk.do(T, "portfolio", {"workspace": ws})["drift"]
    assert pf["total_value"] == 618000 and pf["no_limits"] and not pf["alerts"]
    rk.do(T, "settings", {"workspace": ws, "tolerance_pct": 5, "max_single_pct": 25, "max_group_pct": 45})
    pf = rk.do(T, "portfolio", {"workspace": ws})["drift"]
    assert any("Group 'IT'" in a for a in pf["alerts"]) and pf["proposals"] and pf["to_decide"] == len(pf["proposals"])
    rk.do(T, "decide", {"workspace": ws, "key": pf["proposals"][0]["key"], "decision": "Trim IT next week - PM"})
    assert rk.do(T, "portfolio", {"workspace": ws})["drift"]["to_decide"] == len(pf["proposals"]) - 1
    # a ticket: prepared, never placed; limits are hers
    rk.do(T, "ticket", {"workspace": ws, "symbol": "itc", "side": "sell", "qty": 800, "order_type": "limit", "price": 400, "ltp": 402})
    tk = rk.do(T, "portfolio", {"workspace": ws})["tickets"]
    t0 = tk["rows"][0]
    assert t0["placed"] is False and t0["worst"] == "stop" and "more than the 500 you hold" in t0["flags"][0]["text"] and tk["missing_limits"]
    assert "INR" in t0["confirm_text"] and "Rs" not in t0["confirm_text"]
    rk.do(T, "settings", {"workspace": ws, "max_pct_of_portfolio": 5, "rates": {"brokerage_pct": 0.03, "brokerage_cap": 20}})
    rk.do(T, "ticket", {"workspace": ws, "symbol": "TCS", "side": "buy", "qty": 20, "price": 3500, "ltp": 3480})
    t1 = rk.do(T, "portfolio", {"workspace": ws})["tickets"]["rows"][1]
    assert t1["worst"] == "check" and "your own limit is 5" in t1["flags"][0]["text"] and t1["ticket"]["est_charges"]["brokerage"] == 20
    with pytest.raises(rk.RkDeskError, match="action"):
        rk.do(T, "place_order", {"workspace": ws})


def test_credit_book_watch_value(rk):
    from app.employee import hire
    hire.hire(T, "risk_desk", trust="seekh")
    ws = _desk(rk)
    rk.do(T, "applicant", {"workspace": ws, "name": "Asha Rao", "income_monthly": 80000, "obligations_monthly": 30000, "requested_emi": 20000,
                           "fields": "bureau_score = 680; age = 34"})
    assert rk.do(T, "credit", {"workspace": ws})["applicants"][0]["need_rules"]
    with pytest.raises(rk.RkDeskError, match="ground for discrimination"):
        rk.do(T, "upload", {"workspace": ws, "kind": "rules", "text": "Field,Op,Value\nreligion,==,x\n"}) if False else rk.do(T, "add", {"workspace": ws, "register": "rules", "field": "religion", "op": "==", "value": "x"})
    with pytest.raises(rk.RkDeskError, match="not kept"):
        rk.do(T, "applicant", {"workspace": ws, "name": "B", "fields": "caste = x"})
    rk.do(T, "upload", {"workspace": ws, "kind": "rules", "text": RULES})
    ap = rk.do(T, "credit", {"workspace": ws})["applicants"][0]
    assert ap["foir_pct"] == 62.5 and ap["exceptions"] == ["FOIR_HIGH", "LOW_SCORE"] and not ap["decision"]
    rk.do(T, "decide", {"workspace": ws, "key": ap["key"], "decision": "Referred to committee - Credit officer"})
    assert rk.do(T, "credit", {"workspace": ws})["to_decide"] == 0
    rk.do(T, "offer", {"workspace": ws, "borrower": "Asha Rao", "lender": "Acme Finance", "amount": 500000, "rate": 12, "months": 36, "fee_pct": 1})
    of = rk.do(T, "credit", {"workspace": ws})["offers"][0]
    assert "Key Fact Statement (DRAFT)" in of["kfs"] and of["computed"]["money_received"] == 495000
    # loan book
    rk.do(T, "upload", {"workspace": ws, "kind": "loans", "text": LOANS})
    dp = rk.do(T, "book", {"workspace": ws})["dpd"]
    assert dp["buckets"]["NPA-suggested"] == 120000 and dp["buckets"]["SMA-2(61-90)"] == 80000 and not dp["npa_yours"] and dp["to_decide"] == 1
    rk.do(T, "upload", {"workspace": ws, "kind": "exposures", "text": EXP})
    el = rk.do(T, "book", {"workspace": ws})["ecl"]
    assert el["by_stage"]["stage3"] == 48000 and el["flags"]
    with pytest.raises(rk.RkDeskError, match="between 0 and 1"):
        rk.do(T, "add", {"workspace": ws, "register": "exposures", "id": "E9", "ead": 10, "pd": 2, "lgd": 0.4})
    # surveillance: her limits only, accounts never kept
    rk.do(T, "upload", {"workspace": ws, "kind": "txns", "text": TXN})
    st = rk._state(T, ws)
    assert "4111111111111111" not in str(st) and st["txns"][0]["account_4"] == "…1111"
    assert rk.do(T, "watch", {"workspace": ws})["velocity"]["need_limits"]
    rk.do(T, "settings", {"workspace": ws, "window_minutes": 10, "max_count": 5})
    vc = rk.do(T, "watch", {"workspace": ws})["velocity"]
    rules = {h["rule"]: h for h in vc["rule_hits"]}
    assert rules["velocity"]["account"] == "…1111" and rules["velocity"]["count"] == 6 and sorted(rules["shared_device"]["accounts"]) == ["…1111", "…3333", "…6666"]
    rk.do(T, "decide", {"workspace": ws, "key": rules["velocity"]["key"], "decision": "Released - customer confirmed by call"})
    assert rk.do(T, "watch", {"workspace": ws})["velocity"]["open"] == 1
    rk.do(T, "upload", {"workspace": ws, "kind": "trades", "text": TRD})
    tr = rk.do(T, "watch", {"workspace": ws})["trips"]
    assert len(tr["round_trips"]) == 1 and tr["round_trips"][0]["client"] == "C1" and tr["open"] == 1
    # valuation on her cash flows
    with pytest.raises(rk.RkDeskError, match="higher than the terminal"):
        rk.do(T, "model", {"workspace": ws, "name": "Acme", "cashflows": "100, 110", "discount_pct": 3, "terminal_growth_pct": 4})
    rk.do(T, "model", {"workspace": ws, "name": "Acme", "cashflows": "100, 110, 120", "discount_pct": 12, "terminal_growth_pct": 4, "net_debt": 200, "shares": 10})
    m = rk.do(T, "value", {"workspace": ws})["models"][0]
    assert m["equity_value"] == m["enterprise_value"] - 200 and len(m["sensitivity"]) == 5 and m["per_share"]
    needs = " | ".join(x["say"] for x in rk.summary(T)["desk"]["needs"])
    assert "for the credit team to classify" in needs and "round-trip pattern" in needs and "terminal value" in needs


def test_roles_routes_downloads(rk, monkeypatch):
    from app.employee import hire
    from app.fin.desks import books_ent as E
    from app.main import app
    hire.hire(T, "risk_desk", trust="seekh")
    ws = _desk(rk, "GB", "GBP")
    rk.do(T, "upload", {"workspace": ws, "kind": "holdings", "text": HOLD})
    real = E.access
    monkeypatch.setattr(E, "access", lambda caller, w: {**real(T, w), "role": "viewer", "name": "Bo"} if caller == "bo" else real(caller, w))
    assert rk.do("bo", "portfolio", {"workspace": ws})["drift"]["total_value"] == 618000
    with pytest.raises(rk.RkDeskError, match="read this desk"):
        rk.do("bo", "settings", {"workspace": ws, "max_count": 1})
    c = TestClient(app)
    assert c.get("/api/riskdesk/desk").json()["workspace"]["id"] == ws
    r = c.get(f"/api/riskdesk/download?workspace={ws}&what=weights")
    assert r.status_code == 200 and "INFY" in r.text
    rk.do(T, "offer", {"workspace": ws, "borrower": "Bolt Ltd", "amount": 10000, "rate": 10, "months": 12})
    n = rk._state(T, ws)["offers"][0]["n"]
    r = c.get(f"/api/riskdesk/download?workspace={ws}&what=kfs:{n}")
    assert r.status_code == 200 and "Key Fact Statement" in r.text
    assert c.post("/api/riskdesk/do/place_order", json={"workspace": ws}).status_code in (400, 403)
    assert c.post("/api/riskdesk/do/add", json={"workspace": ws, "register": "txns", "account": "4111111111111111", "ts": D(0) + "T10:00:00",
                                                "amount": 10, "cvv": "123"}).status_code == 403
    assert c.get("/api/riskdesk/chat").json()["id"]


@pytest.fixture
def rk_server(rk, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "risk_desk", trust="seekh")
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


def test_desk_in_a_real_browser(rk, rk_server, tmp_path):
    base, browser, key = rk_server
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
        for tries in (1, 2, 3):
            pg.wait_for_timeout(250)
            pg.set_input_files(f"form[data-kind={kind}] input[type=file]", str(f))
            try:
                pg.wait_for_selector(wait, timeout=10000 if tries < 3 else 20000)
                break
            except Exception:
                if tries == 3:
                    raise

    def fill(pg, form, vals):
        for n, v in vals:
            sel = f"form[data-form={form}] [name={n}]"
            if pg.eval_on_selector(sel, "e => e.tagName") == "SELECT":
                pg.select_option(sel, v)
            else:
                pg.fill(sel, v)
        pg.click(f"form[data-form={form}] [type=submit]")

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/risk")
    pg.wait_for_selector("text=Set up your risk desk", timeout=20000)
    snap(pg, "rk-setup-1440")
    pg.fill("form[data-form=setup] [name=country]", "IN")
    pg.fill("form[data-form=setup] [name=currency]", "INR")
    pg.click("form[data-form=setup] [type=submit]")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # settings first: her limits
    go(pg, "#/settings", "form[data-form=limits]")
    fill(pg, "limits", (("tolerance_pct", "5"), ("max_single_pct", "25"), ("max_group_pct", "45")))
    pg.wait_for_selector("text=Saved", timeout=20000)
    fill(pg, "orders", (("max_pct_of_portfolio", "5"), ("max_price_deviation_pct", "3"), ("brokerage_pct", "0.03"), ("brokerage_cap", "20")))
    pg.wait_for_timeout(700)
    fill(pg, "watchset", (("window_minutes", "10"), ("max_count", "5")))
    pg.wait_for_timeout(700)
    snap(pg, "rk-settings-1440")
    # portfolio + a ticket
    go(pg, "#/portfolio", "form[data-kind=holdings]")
    up(pg, "holdings", "h.csv", HOLD, "text=Weights")
    up(pg, "targets", "t.csv", TGT, "text=Rebalance proposals")
    fill(pg, "ticket", (("symbol", "ITC"), ("side", "sell"), ("qty", "800"), ("price", "400"), ("ltp", "402")))
    pg.wait_for_selector(".rk-flag.stop", timeout=20000)
    pg.fill("form[data-form=decide][data-key='ticket:1'] [name=decision]", "Cancelled - the quantity was a typo")
    pg.click("form[data-form=decide][data-key='ticket:1'] [type=submit]")
    pg.wait_for_selector(".pb-dec", timeout=20000)
    snap(pg, "rk-portfolio-1440")
    # applications + rules + key facts
    go(pg, "#/credit", "form[data-kind=rules]")
    up(pg, "rules", "r.csv", RULES, "text=LOW_SCORE")
    fill(pg, "applicant", (("name", "Asha Rao"), ("product", "Personal loan"), ("amount", "500000"), ("income_monthly", "80000"),
                           ("obligations_monthly", "30000"), ("requested_emi", "20000"), ("fields", "bureau_score = 680; age = 34")))
    pg.wait_for_selector(".cm-gauge", timeout=20000)
    fill(pg, "offer", (("borrower", "Asha Rao"), ("lender", "Acme Finance"), ("amount", "500000"), ("rate", "12"), ("months", "36"), ("fee_pct", "1")))
    pg.wait_for_selector("text=Money received", timeout=20000)
    snap(pg, "rk-credit-1440")
    # loan book
    go(pg, "#/book", "form[data-kind=loans]")
    up(pg, "loans", "l.csv", LOANS, ".fo-age")
    up(pg, "exposures", "e.csv", EXP, ".iv-donut")
    snap(pg, "rk-book-1440")
    # surveillance
    go(pg, "#/watch", "form[data-kind=txns]")
    up(pg, "txns", "p.csv", TXN, "text=Account …1111")
    assert "4111111111111111" not in pg.content()
    up(pg, "trades", "tr.csv", TRD, "text=Round trip")
    snap(pg, "rk-watch-1440")
    # valuation
    go(pg, "#/value", "form[data-form=model]")
    fill(pg, "model", (("name", "Acme Ltd"), ("cashflows", "120, 135, 150, 160, 170"), ("discount_pct", "12"), ("terminal_growth_pct", "4"),
                       ("net_debt", "200"), ("shares", "10")))
    pg.wait_for_selector(".rk-sens", timeout=20000)
    snap(pg, "rk-value-1440")
    go(pg, "#/today", ".cs-hero")
    pg.wait_for_selector(".iv-donut", timeout=20000)
    snap(pg, "rk-today-1440")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".iv-donut", "today"), ("#/portfolio", ".rk-flag", "portfolio"), ("#/credit", ".cm-gauge", "credit"),
                             ("#/book", ".fo-age", "book"), ("#/watch", ".pb-res", "watch"), ("#/value", ".rk-sens", "value"),
                             ("#/settings", "form[data-form=limits]", "settings")):
        pg.goto(base + "/console/risk" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"rk-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#rkPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
