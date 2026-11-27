"""MARKETS DESK: the Markets & Post-Trade employee's own section, built like Investments, Payments and Institution - its own chat
(kind 'markets') with the desk block + the markets tool in view; a desk set up on the page (or any finance workspace she has);
positions in her books and the custodian's file -> the reconciliation and its breaks, cash too; trades against confirmations; settlements
-> fails by age with HER penalty rate, marked settled by her; corporate actions worked out on her positions; dividends -> reclaims at HER
treaty rates with the claim date; margin calls after HER haircuts; best execution; settlement instructions; comparables; the disclosure
calendar from HER rules; read-only team roles; the downloads; nothing placed, cancelled or affirmed; and the desk walked in a real browser."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def mk(env):
    from app import mktchat as MK
    MK._OF.clear()
    MK._BLOCK.clear()
    return MK


def _desk(mk, country="GB", currency="GBP"):
    return mk.setup(T, {"name": "Ops desk", "country": country, "currency": currency, "size": "business"})["desk"]["id"]


BOOKS = "Account,ISIN,Quantity\nA1,GB0001,100\nA1,GB0002,50\nA2,GB0001,30\n"
CUST = "Safekeeping Account,Security ID,Settled Position\nA1,GB0001,100\nA1,GB0002,45\nA2,GB0003,10\n"
D = lambda n: (date.today() + timedelta(days=n)).isoformat()      # noqa: E731
TRADES = f"Trade ID,B/S,ISIN,Account,Quantity,Price,Trade Date\nT1,B,GB0001,A1,100,10.00,{D(-3)}\nT2,S,GB0002,A1,20,5.00,{D(-3)}\nT3,B,GB0003,A2,5,7,{D(-1)}\n"
CONFS = f"Trade ID,Side,ISIN,Account,Quantity,Price,Trade Date\nT1,BUY,GB0001,A1,100,10.00,{D(-3)}\nT2,SELL,GB0002,A1,20,5.10,{D(-3)}\nT9,BUY,GB0009,A1,1,1,{D(-2)}\n"
SETTLE = f"Settlement ID,ISIN,Counterparty,Settlement Amount,Intended Settlement Date,Status\nS1,GB0001,Big Bank,10000,{D(-8)},\nS2,GB0002,Big Bank,500,{D(-2)},\nS3,GB0003,Small Co,700,{D(2)},\nS4,GB0004,X,1,{D(-30)},settled\n"
DIVS = f"Pay Date,Symbol,Country,Gross,Tax Withheld\n{D(-200)},USCO,US,1000,300\n{D(-2000)},DECO,DE,500,132\n{D(-50)},FRCO,FR,400,100\n"


def test_hire_setup_chat_block_and_wiring(mk):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert mk.summary(T)["hired"] is False
    hire.hire(T, "markets_desk", trust="seekh")
    d = mk.summary(T)
    assert d["hired"] and d["workspace"] is None and "never places" in d["foot"]
    assert "Set up your desk" in mk.greeting(T) and "No desk set up yet" in mk.block(T)
    with pytest.raises(mk.MktDeskError):
        mk.setup(T, {"name": "X", "country": "GBR", "currency": "GBP"})
    ws = _desk(mk)
    d = mk.summary(T)
    assert d["workspace"]["id"] == ws and d["role"] == "owner" and d["can_write"] and d["desk"]["recon"]["empty"]
    chat = mk.current(T)
    assert mk.is_markets(chat["id"]) and mk.owns(T, chat["id"])
    mk.forget(T)
    blk = mk.block(T)
    assert "<markets_desk>" in blk and "never places" in blk and "call-back" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_mkc.is_markets(conversation_id)" in src and "adm.admit_families(_mkc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["markets_desk"] in mk.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"investments", "markets"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/markets")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "mktdesk.js" in r.text
    html = (root / "server/app/static/console/mktdesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "moneydesk.css", "cashdesk.css", "instdesk.css", "invdesk.css", "mktdesk.css", "mktdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/markets')" in (root / "server/app/static/console/v2.js").read_text()
    assert "markets_desk: 'mktdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/markets'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_recon_confirms_and_fails(mk):
    from app.employee import hire
    hire.hire(T, "markets_desk", trust="seekh")
    ws = _desk(mk)
    assert "3 positions in your books read" in mk.do(T, "upload", {"workspace": ws, "kind": "books", "text": BOOKS})["says"]
    mk.do(T, "upload", {"workspace": ws, "kind": "custodian", "text": CUST, "custodian_name": "Big Custodian"})
    r = mk.do(T, "recon", {"workspace": ws})
    kinds = {(b["account"], b["symbol"]): (b["break"], b["difference"]) for b in r["breaks"]}
    assert r["matched"] == 1 and kinds == {("A1", "GB0002"): ("quantity", 5.0), ("A2", "GB0001"): ("missing at the custodian", 30.0),
                                          ("A2", "GB0003"): ("missing in our books", -10.0)}
    mk.do(T, "add", {"workspace": ws, "register": "cash_books", "account": "a1", "currency": "gbp", "amount": "1000"})
    mk.do(T, "add", {"workspace": ws, "register": "cash_custodian", "account": "A1", "currency": "GBP", "amount": "990"})
    assert mk.do(T, "recon", {"workspace": ws})["cash_breaks"][0]["difference"] == 10.0
    mk.do(T, "settings", {"workspace": ws, "tolerance": 5})
    assert ("A1", "GB0002") not in {(b["account"], b["symbol"]) for b in mk.do(T, "recon", {"workspace": ws})["breaks"]}
    # confirmations
    assert "3 trades added" in mk.do(T, "upload", {"workspace": ws, "kind": "trades", "text": TRADES})["says"]
    assert "already on the desk" in mk.do(T, "upload", {"workspace": ws, "kind": "trades", "text": TRADES})["says"]
    mk.do(T, "upload", {"workspace": ws, "kind": "confirms", "text": CONFS})
    c = mk.do(T, "confirm", {"workspace": ws})
    assert c["matched"] == ["T1"] and c["unconfirmed"] == ["T3"] and c["confirms_with_no_trade"] == ["T9"]
    assert c["breaks"][0]["id"] == "T2" and c["breaks"][0]["differences"][0]["field"] == "price" and c["affirmed"] is False
    mk.do(T, "settings", {"workspace": ws, "price_tolerance": 0.2})
    assert mk.do(T, "confirm", {"workspace": ws})["breaks"] == []
    # fails: penalty only at HER rate
    mk.do(T, "upload", {"workspace": ws, "kind": "settlements", "text": SETTLE})
    f = mk.do(T, "fails", {"workspace": ws})
    assert [x["id"] for x in f["fails"]] == ["S1", "S2"] and isinstance(f["penalty"], str) and f["due_soon"][0]["id"] == "S3"
    mk.do(T, "settings", {"workspace": ws, "penalty_bp": 1})
    f = mk.do(T, "fails", {"workspace": ws})
    assert f["penalty"] == 8.1 and f["by_age"]["6-10 days"] == 1      # 10000 x 1bp x 8 days + 500 x 1bp x 2
    n1 = f["fails"][0]["n"]
    mk.do(T, "settle", {"workspace": ws, "n": n1})
    assert [x["id"] for x in mk.do(T, "fails", {"workspace": ws})["fails"]] == ["S2"]
    k = mk.summary(T)["desk"]
    says = " | ".join(x["say"] for x in k["needs"])
    assert "position break" in says and "not confirmed" in says and "with no trade" in says and "settlement failed" in says
    assert k["counts"]["trades"] == 3


def test_actions_reclaims_margin_bestex_ssi_comps_calendar(mk):
    from app.employee import hire
    hire.hire(T, "markets_desk", trust="seekh")
    ws = _desk(mk)
    mk.do(T, "upload", {"workspace": ws, "kind": "books", "text": "Account,ISIN,Quantity\nA1,ACME,101\nA2,ACME,50\n"})
    r = mk.do(T, "corp_action", {"workspace": ws, "type": "stock_dividend", "symbol": "acme", "ratio": "1:10", "record_date": D(-1),
                                 "cash_in_lieu_price": "20"})
    ent = {e["account"]: e for e in r["entitlements"]}
    assert ent["A1"]["new_shares"] == 10 and ent["A1"]["fraction"] == 0.1 and ent["A1"]["cash_in_lieu"] == 2.0 and r["totals"]["new_shares"] == 15
    d = mk.do(T, "corp_action", {"workspace": ws, "type": "cash_dividend", "symbol": "ACME", "rate": "0.5", "withholding_pct": "15", "record_date": D(-1)})
    assert d["totals"]["gross"] == 75.5 and d["totals"]["net"] == 64.18
    with pytest.raises(mk.MktDeskError, match="No position in ZZZ"):
        mk.do(T, "corp_action", {"workspace": ws, "type": "split", "symbol": "ZZZ", "ratio": "2:1", "record_date": D(-1)})
    assert len(mk.summary(T)["desk"]["events"]) == 2
    # reclaims at HER treaty rates
    mk.do(T, "upload", {"workspace": ws, "kind": "dividends", "text": DIVS})
    rl = mk.do(T, "reclaims", {"workspace": ws})
    assert set(rl["no_treaty_rate_given_for"]) == {"US", "DE", "FR"}
    mk.do(T, "settings", {"workspace": ws, "treaty": "US, 15\nDE, 15\nFR, 12.8", "claim_years": "US, 3\nDE, 4"})
    rl = mk.do(T, "reclaims", {"workspace": ws})
    by = {c["country"]: c for c in rl["claims"]}
    assert by["US"]["reclaimable"] == 150.0 and by["DE"]["expired"] and by["FR"]["claim_by"] is None and rl["no_period_for"] == ["FR"]
    assert rl["reclaimable"] == 150.0 + 48.8 and rl["expired"] == 57.0
    # margin
    with pytest.raises(mk.MktDeskError, match="haircuts"):
        mk.do(T, "margin", {"workspace": ws, "requirement": 1000, "collateral": "GILT, 800"})
    mk.do(T, "settings", {"workspace": ws, "haircuts": "BOND, 5\nEQUITY, 25"})
    m = mk.do(T, "margin", {"workspace": ws, "requirement": 1000, "collateral": "GILT, 800, bond\nACME, 200, equity", "due": D(1), "counterparty": "CCP"})
    assert m["collateral_after_haircuts"] == 910.0 and m["shortfall"] == 90.0 and "Please provide 90.00" in m["notice"]
    assert "Margin shortfall" in " | ".join(x["say"] for x in mk.summary(T)["desk"]["needs"])
    # best execution, SSI, comps, calendar
    mk.do(T, "upload", {"workspace": ws, "kind": "executions", "text": "ID,Side,Quantity,Price,Arrival Price\nE1,buy,100,10.05,10\nE2,sell,100,9.99,10\nE3,buy,10,9.9,10\n"})
    mk.do(T, "settings", {"workspace": ws, "slip_bp": 20})
    b = mk.do(T, "best_ex", {"workspace": ws})
    assert b["executions"][0]["id"] == "E1" and b["executions"][0]["slippage_bp"] == 50.0 and [x["id"] for x in b["over"]] == ["E1"] and b["better"] == 1
    mk.do(T, "add", {"workspace": ws, "register": "instructions", "counterparty": "Big Bank", "currency": "EUR", "bic": "DEUTDEFF", "account": "1",
                     "iban": "DE89370400440532013000"})
    mk.do(T, "upload", {"workspace": ws, "kind": "instructions", "text": "Counterparty,Currency,BIC,Account,IBAN\nBig Bank,EUR,DEUTDEFF,2,DE00370400440532013000\n"})
    s = mk.do(T, "ssi", {"workspace": ws})
    assert s["bad"] == 1 and any("call-back" in p for p in s["instructions"][1]["problems"])
    mk.do(T, "upload", {"workspace": ws, "kind": "peers", "text": "Name,EV,EBITDA,Revenue,Price,EPS\nP1,1000,100,500,20,2\nP2,2000,100,1000,30,2\n"})
    mk.do(T, "settings", {"workspace": ws, "target": {"name": "Us", "ebitda": 50}})
    cp = mk.do(T, "comps", {"workspace": ws})
    assert cp["multiples"]["ev_ebitda"]["median"] == 15.0 and cp["implied_for_target"]["ev_ebitda"]["median"] == 750.0
    assert mk.do(T, "calendar", {"workspace": ws})["empty"]
    mk.do(T, "settings", {"workspace": ws, "period_ends": f"{D(-10)}\n{D(80)}", "ir_rules": "Half-year report, 30\nTrading statement, 5"})
    cl = mk.do(T, "calendar", {"workspace": ws})
    assert cl["next"][0]["what"] == "Half-year report" and cl["next"][0]["days_left"] == 20
    with pytest.raises(Exception):
        mk.do(T, "affirm", {"workspace": ws})


def test_roles_routes_and_downloads(mk):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "markets_desk", trust="seekh")
    ws = _desk(mk)
    c = TestClient(app)
    assert c.get("/api/markets/desk").json()["workspace"]["id"] == ws
    assert c.post("/api/markets/do/nope", json={"workspace": ws}).status_code == 400
    assert c.post("/api/markets/do/place_order", json={"workspace": ws}).status_code == 400
    assert c.post("/api/markets/do/upload", json={"workspace": ws, "kind": "books", "text": BOOKS}).status_code == 200
    assert c.post("/api/markets/do/upload", json={"workspace": ws, "kind": "custodian", "text": "a,b\n1,2\n"}).status_code == 400
    assert c.post("/api/markets/do/upload", json={"workspace": ws, "kind": "custodian", "text": CUST}).status_code == 200
    r = c.get("/api/markets/download", params={"workspace": ws, "what": "breaks"})
    assert r.status_code == 200 and "missing in our books" in r.text
    assert c.get("/api/markets/download", params={"workspace": ws, "what": "fails"}).status_code == 400
    assert c.get("/api/markets/download", params={"workspace": ws, "what": "nope"}).status_code == 400
    assert c.get("/api/markets/chat").json()["id"]
    assert c.put("/api/markets/workspace", json={"workspace": "nope"}).status_code == 400
    assert c.post("/api/markets/setup", json={"country": "G", "currency": "GBP"}).status_code == 400
    from app.fin.desks import books_ent as E
    from unittest import mock
    with mock.patch.object(E, "access", return_value={"owner": T, "role": "viewer", "id": "v1", "name": "Vi", "workspace": ws}):
        assert len(mk.do("v1", "recon", {"workspace": ws})["breaks"]) == 3
        with pytest.raises(mk.MktDeskError, match="can read this desk but not change it"):
            mk.do("v1", "add", {"workspace": ws, "register": "books", "account": "A", "symbol": "X", "qty": 1})


@pytest.fixture
def mk_server(mk, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "markets_desk", trust="seekh")
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


def test_desk_in_a_real_browser(mk, mk_server, tmp_path):
    base, browser, key = mk_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route):
        pg.evaluate(f"location.hash = '{route}'")

    def up(pg, kind, name, text):
        f = tmp_path / name
        f.write_text(text)
        pg.set_input_files(f"form[data-kind={kind}] input[type=file]", str(f))

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/markets")
    pg.wait_for_selector("text=Set up your markets desk", timeout=20000)
    snap(pg, "mk-setup-1440")
    pg.fill("form[data-form=setup] [name=country]", "GB")
    pg.fill("form[data-form=setup] [name=currency]", "GBP")
    pg.click("form[data-form=setup] [type=submit]")
    pg.wait_for_selector(".cs-hero", timeout=20000)
    ws = mk.summary(T)["workspace"]["id"]
    # reconciliation: both files uploaded in the page
    go(pg, "#/recon")
    pg.wait_for_selector("form[data-kind=books]", timeout=20000)
    up(pg, "books", "books.csv", BOOKS)
    pg.wait_for_selector("text=positions in your books read", timeout=20000)
    pg.fill("form[data-kind=custodian] [name=custodian_name]", "Big Custodian")
    up(pg, "custodian", "cust.csv", CUST)
    pg.wait_for_selector("text=Position breaks", timeout=20000)
    assert pg.locator("#mkPage table.iv-tb tbody tr").count() == 3
    pg.click("[data-ask]")
    assert "About:" in pg.inner_text("#sdCtx")
    snap(pg, "mk-recon-1440")
    # trades & settlement
    go(pg, "#/settle")
    pg.wait_for_selector("form[data-kind=trades]", timeout=20000)
    up(pg, "trades", "trades.csv", TRADES)
    pg.wait_for_selector("text=3 trades added", timeout=20000)
    up(pg, "confirms", "confs.csv", CONFS)
    pg.wait_for_selector("text=Confirmations that differ", timeout=20000)
    up(pg, "settlements", "settle.csv", SETTLE)
    pg.wait_for_selector("text=Failed settlements", timeout=20000)
    pg.click("[data-settle]")
    pg.wait_for_selector("text=Marked settled", timeout=20000)
    assert [x["id"] for x in mk.do(T, "fails", {"workspace": ws})["fails"]] == ["S2"]
    snap(pg, "mk-settle-1440")
    # corporate actions on her books
    go(pg, "#/actions")
    pg.wait_for_selector("form[data-form=ca]", timeout=20000)
    pg.select_option("form[data-form=ca] [name=type]", "cash_dividend")
    assert not pg.is_visible("form[data-form=ca] [name=ratio]")
    pg.fill("form[data-form=ca] [name=symbol]", "GB0001")
    pg.fill("form[data-form=ca] [name=record_date]", D(-1))
    pg.fill("form[data-form=ca] [name=rate]", "0.5")
    pg.fill("form[data-form=ca] [name=withholding_pct]", "20")
    pg.click("form[data-form=ca] [type=submit]")
    pg.wait_for_selector("text=Worked out before", timeout=20000)
    assert "52.00" in pg.inner_text("#mkPage")       # 130 held x 0.50 = 65.00 gross, 80% net
    snap(pg, "mk-actions-1440")
    # reclaims
    go(pg, "#/reclaims")
    up(pg, "dividends", "divs.csv", DIVS)
    pg.wait_for_selector("text=No treaty rate for", timeout=20000)
    mk.do(T, "settings", {"workspace": ws, "treaty": "US, 15\nDE, 15\nFR, 12.8", "claim_years": "US, 3\nDE, 4\nFR, 2"})
    pg.click("#sdRefresh")
    pg.wait_for_selector("#mkPage .mk-bars", timeout=20000)
    snap(pg, "mk-reclaims-1440")
    # margin
    go(pg, "#/margin")
    pg.fill("form[data-form=margin] [name=requirement]", "1000")
    pg.fill("form[data-form=margin] [name=collateral]", "GILT, 800, bond\nACME, 200, equity")
    pg.fill("form[data-form=margin] [name=haircuts]", "BOND, 5\nEQUITY, 25")
    pg.fill("form[data-form=margin] [name=counterparty]", "Client A")
    pg.click("form[data-form=margin] [type=submit]")
    pg.wait_for_selector(".mk-notice", timeout=20000)
    assert "90.00" in pg.inner_text(".mk-notice")
    snap(pg, "mk-margin-1440")
    # best execution
    go(pg, "#/bestex")
    up(pg, "executions", "ex.csv", "ID,Side,Symbol,Quantity,Price,Arrival Price\nE1,buy,GB0001,100,10.05,10\nE2,sell,GB0002,100,9.99,10\nE3,buy,GB0003,10,9.9,10\n")
    pg.wait_for_selector("text=Worst first", timeout=20000)
    snap(pg, "mk-bestex-1440")
    # instructions
    go(pg, "#/ssi")
    up(pg, "instructions", "ssi.csv", "Counterparty,Currency,BIC,Account,IBAN\nBig Bank,EUR,DEUTDEFF,1,DE89370400440532013000\nBig Bank,EUR,DEUTDEFF,2,DE00370400440532013000\nSmall,USD,BAD,3,\n")
    pg.wait_for_selector(".mk-prob", timeout=20000)
    snap(pg, "mk-ssi-1440")
    # comparables + calendar
    go(pg, "#/research")
    up(pg, "peers", "peers.csv", "Name,EV,EBITDA,Revenue,Price,EPS\nP1,1000,100,500,20,2\nP2,2000,100,1000,30,2\nP3,1500,120,800,25,1.5\n")
    pg.wait_for_selector("text=The table", timeout=20000)
    pg.fill("form[data-form=target] [name=name]", "Us")
    pg.fill("form[data-form=target] [name=ebitda]", "50")
    pg.click("form[data-form=target] [type=submit]")
    pg.wait_for_selector(".mk-range", timeout=20000)
    pg.fill("form[data-form=cal] [name=period_ends]", f"{D(-10)}\n{D(80)}")
    pg.fill("form[data-form=cal] [name=ir_rules]", "Half-year report, 30\nTrading statement, 5")
    pg.click("form[data-form=cal] [type=submit]")
    pg.wait_for_selector(".mk-tl", timeout=20000)
    snap(pg, "mk-research-1440")
    go(pg, "#/settings")
    pg.wait_for_selector("form[data-form=rates]", timeout=20000)
    pg.fill("form[data-form=settings] [name=penalty_bp]", "1")
    pg.fill("form[data-form=settings] [name=slip_bp]", "20")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("text=Saved", timeout=20000)
    assert mk.summary(T)["desk"]["settings"]["penalty_bp"] == 1
    snap(pg, "mk-settings-1440")
    go(pg, "#/today")
    pg.wait_for_selector(".iv-donut", timeout=20000)
    pg.wait_for_selector(".mk-tl", timeout=20000)
    snap(pg, "mk-today-1440")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".iv-donut", "today"), ("#/recon", ".iv-tb", "recon"), ("#/settle", ".mk-diff", "settle"),
                             ("#/actions", ".iv-sale", "actions"), ("#/reclaims", ".mk-bars", "reclaims"), ("#/margin", ".iv-tb", "margin"),
                             ("#/bestex", ".cs-chart", "bestex"), ("#/ssi", ".mk-prob", "ssi"), ("#/research", ".mk-range", "research"),
                             ("#/settings", "form[data-form=rates]", "settings")):
        pg.goto(base + "/console/markets" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"mk-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#mkPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
