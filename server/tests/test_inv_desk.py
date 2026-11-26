"""INVESTMENTS DESK: the Investments & Wealth employee's own section, built like Payments, Firm Practice and Institution - its own chat
(kind 'investments') with the desk block + the investments tool in view; a portfolio set up on the desk (or any finance workspace she has);
trades from a broker CSV or a form -> capital gains by tax lot in her country's method, grouped by tax year, with the wash-sale rule;
holdings (CSV, form, or built from the trades) at HER prices -> value, weights, allocation, over her limit, drift from her target mix, the
losses she could realise; options and futures -> the most she can lose; the fee and retirement plans at HER assumptions (never Hoola's);
the scam check with its history; a fund's NAV with its history; read-only team roles; the downloads; and the desk walked in a real browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def iv(env):
    from app import invchat as IV
    IV._OF.clear()
    IV._BLOCK.clear()
    return IV


def _pf(iv, country="US", currency="USD"):
    return iv.setup(T, {"name": "My investments", "country": country, "currency": currency, "size": "personal"})["portfolio"]["id"]


TRADES = ("Trade Date,Action,Symbol,Quantity,Price,Commission\n"
          "2025-01-10,BUY,ACME,10,100,1\n"
          "2025-06-01,SELL,ACME,10,80,1\n"
          "2025-06-15,BUY,ACME,10,85,1\n"
          "2024-02-01,BUY,ZED,5,200,0\n"
          "2025-08-01,SELL,ZED,5,260,0\n")


def test_hire_setup_chat_block_and_wiring(iv):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert iv.summary(T)["hired"] is False
    hire.hire(T, "investments_desk", trust="seekh")
    d = iv.summary(T)
    assert d["hired"] and d["workspace"] is None and "never places" in d["foot"]
    assert "Set up your portfolio" in iv.greeting(T) and "No portfolio set up yet" in iv.block(T)
    with pytest.raises(iv.InvDeskError):
        iv.setup(T, {"name": "X", "country": "USA", "currency": "USD"})
    ws = _pf(iv)
    d = iv.summary(T)
    assert d["workspace"]["id"] == ws and d["role"] == "owner" and d["can_write"]
    assert d["desk"]["country"] == "US" and "wash-sale" in d["desk"]["method_name"]
    chat = iv.current(T)
    assert iv.is_investments(chat["id"]) and iv.owns(T, chat["id"])
    iv.forget(T)
    blk = iv.block(T)
    assert "<investments_desk>" in blk and "never places" in blk and "never assume a return" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_ivc.is_investments(conversation_id)" in src and "adm.admit_families(_ivc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["investments_desk"] in iv.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"institution", "investments"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/investments")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "invdesk.js" in r.text
    html = (root / "server/app/static/console/invdesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "moneydesk.css", "cashdesk.css", "creditdesk.css", "instdesk.css", "invdesk.css", "invdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/investments')" in (root / "server/app/static/console/v2.js").read_text()
    assert "investments_desk: 'invdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/investments'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_trades_gains_tax_year_and_wash_sale(iv):
    from app.employee import hire
    hire.hire(T, "investments_desk", trust="seekh")
    ws = _pf(iv)
    r = iv.do(T, "upload", {"workspace": ws, "kind": "trades", "text": TRADES, "name": "broker.csv"})
    assert r["rows"] == 5 and "5 trades added" in r["says"]
    again = iv.do(T, "upload", {"workspace": ws, "kind": "trades", "text": TRADES})
    assert "already on the desk" in again["says"]
    g = iv.do(T, "gains", {"workspace": ws})
    acme = next(x for x in g["disposals"] if x["symbol"] == "ACME")
    assert acme["disallowed"] > 0 and g["disallowed_losses"] == acme["disallowed"]          # bought back inside 30 days: the loss waits
    zed = next(x for x in g["disposals"] if x["symbol"] == "ZED")
    assert zed["gain"] == 300.0 and zed["parts"][0]["term"] == "long"
    assert [y["year"] for y in g["years"]] == ["2025"] and g["years"][0]["sales"] == 2
    h = iv.do(T, "from_trades", {"workspace": ws})
    assert h["holdings"] == 1 and h["no_price"] == ["ACME"]
    d = iv.summary(T)["desk"]
    assert any("losses do not count yet" in n["say"] for n in d["needs"]) and any("has no price" in n["say"] for n in d["needs"])
    with pytest.raises(iv.InvDeskError):
        iv.do(T, "trade", {"workspace": ws, "date": "2025-09-01", "side": "short", "symbol": "X", "qty": 1, "price": 1})
    iv.do(T, "trade", {"workspace": ws, "date": "2025-09-01", "side": "sell", "symbol": "ACME", "qty": 4, "price": 90})
    assert len(iv.do(T, "gains", {"workspace": ws})["disposals"]) == 3
    iv.do(T, "settings", {"workspace": ws, "country": "GB"})
    g2 = iv.do(T, "gains", {"workspace": ws})
    assert g2["method"] == "uk_share_id" and {y["year"] for y in g2["years"]} == {"2025-26"}
    assert iv.tax_year("GB", "2026-04-05") == "2025-26" and iv.tax_year("GB", "2026-04-06") == "2026-27" and iv.tax_year("IN", "2026-03-31") == "2025-26"
    with pytest.raises(iv.InvDeskError):
        iv.do(T, "settings", {"workspace": ws, "method": "lifo"})
    from app.main import app
    c = TestClient(app)
    r = c.get(f"/api/investments/download?workspace={ws}&what=gains")
    assert r.status_code == 200 and b"tax year" in r.content and b"tax on these gains is not worked out" in r.content


def test_portfolio_harvest_plans_risk_scam_nav(iv):
    from app.employee import hire
    hire.hire(T, "investments_desk", trust="seekh")
    ws = _pf(iv)
    iv.do(T, "upload", {"workspace": ws, "kind": "holdings", "prices_on": "2026-01-02",
                        "text": "symbol,qty,price,cost,asset_class\nVWRL,100,110,9000,ETF\nACME,50,40,3000,equity\nGILT,10,95,1000,bond\n"})
    p = iv.do(T, "portfolio", {"workspace": ws})
    assert p["total"] == 13950.0 and p["allocation"]["funds"] > 78 and p["prices_on"] == "2026-01-02"
    iv.do(T, "settings", {"workspace": ws, "max_pct": 50, "targets": {"funds": 60, "shares": 20, "bonds": 20}})
    p = iv.do(T, "portfolio", {"workspace": ws})
    assert p["over_your_limit"] == ["VWRL"] and any(x["class"] == "funds" and x["off"] > 5 for x in p["drift"])
    with pytest.raises(iv.InvDeskError):
        iv.do(T, "settings", {"workspace": ws, "targets": {"funds": 60, "shares": 20}})
    d = iv.summary(T)["desk"]
    assert any("over your 50% limit" in n["say"] for n in d["needs"]) and any("days ago" in n["say"] for n in d["needs"])
    iv.do(T, "prices", {"workspace": ws, "prices": {"ACME": "50"}, "prices_on": "2026-01-09"})
    hv = iv.do(T, "harvest", {"workspace": ws})
    assert [x["symbol"] for x in hv["losses"]] == ["ACME", "GILT"] and hv["losses"][0]["unrealised_loss"] == -500.0 and hv["total"] == -550.0
    with pytest.raises(iv.InvDeskError):
        iv.do(T, "plan", {"workspace": ws, "which": "fees", "years": 10})                   # never a return Hoola assumed
    f = iv.do(T, "plan", {"workspace": ws, "which": "fees", "years": 10, "fee_pct": 1, "return_pct": 5})
    assert f["kept"]["amount"] == 14450.0 and f["fees_cost"] > 0
    with pytest.raises(iv.InvDeskError):
        iv.do(T, "plan", {"workspace": ws, "which": "retire", "withdraw": 2000})            # inflation not given yet
    rt = iv.do(T, "plan", {"workspace": ws, "which": "retire", "withdraw": 2000, "inflation_pct": 2})
    assert rt["runs_out_in_year"] and iv.summary(T)["desk"]["assume"] == {"return_pct": 5.0, "inflation_pct": 2.0}
    iv.do(T, "position", {"workspace": ws, "type": "call", "side": "short", "symbol": "ACME", "strike": 60, "premium": 2, "qty": 1, "multiplier": 100,
                          "expiry": "2099-01-01"})
    with pytest.raises(iv.InvDeskError):
        iv.do(T, "position", {"workspace": ws, "type": "swap"})
    rk = iv.do(T, "risk", {"workspace": ws})
    assert rk["positions"][0]["most_you_can_lose"] == "unlimited" and rk["unlimited"] == [1]
    sc = iv.do(T, "scam", {"workspace": ws, "text": "Guaranteed 20% a month, act now, join our WhatsApp group", "firm": "Quick Gains Ltd",
                           "register": "Real Advisers Ltd\nOther Co"})
    assert sc["level"] == "high" and sc["on_your_register"] is False and iv.summary(T)["desk"]["scams"][0]["firm"] == "Quick Gains Ltd"
    nv = iv.do(T, "nav", {"workspace": ws, "fund": "Growth Fund", "assets": "Shares, 1000000\nCash, 50000", "liabilities": "Fees due, 10000",
                          "units": 100000, "reported_nav": 10.5, "tolerance_bp": 1})
    assert nv["nav_per_unit"] == 10.4 and nv["break"] is True
    assert any("NAV break" in n["say"] for n in iv.summary(T)["desk"]["needs"])
    from app.fin import laws as L
    with pytest.raises(L.Refused):
        iv._engine(T, "x", "place_order", {})
    iv.do(T, "remove", {"workspace": ws, "register": "positions", "n": 1})
    assert iv.summary(T)["desk"]["positions_count"] == 0


def test_roles_and_routes(iv):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "investments_desk", trust="seekh")
    ws = _pf(iv)
    c = TestClient(app)
    assert c.get("/api/investments/desk").json()["workspace"]["id"] == ws
    assert c.post("/api/investments/do/nope", json={"workspace": ws}).status_code == 400
    assert c.post("/api/investments/do/place_order", json={"workspace": ws}).status_code == 400
    assert c.post("/api/investments/do/trade", json={"workspace": ws, "date": "2025-01-02", "side": "buy", "symbol": "a", "qty": 2, "price": 5}).status_code == 200
    assert c.get("/api/investments/chat").json()["id"]
    assert c.put("/api/investments/workspace", json={"workspace": "nope"}).status_code == 400
    assert c.get("/api/investments/download", params={"workspace": ws, "what": "holdings"}).status_code == 200
    assert c.get("/api/investments/download", params={"workspace": ws, "what": "nope"}).status_code == 400
    assert c.post("/api/investments/setup", json={"country": "G", "currency": "GBP"}).status_code == 400
    # a viewer someone put on the portfolio reads it but cannot change it
    from app.fin.desks import books_ent as E
    from unittest import mock
    with mock.patch.object(E, "access", return_value={"owner": T, "role": "viewer", "id": "v1", "name": "Vi", "workspace": ws}):
        assert iv.do("v1", "gains", {"workspace": ws})["trades"] == 1
        with pytest.raises(iv.InvDeskError, match="can read this desk but not change it"):
            iv.do("v1", "trade", {"workspace": ws, "date": "2025-01-02", "side": "buy", "symbol": "a", "qty": 1, "price": 5})


@pytest.fixture
def iv_server(iv, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "investments_desk", trust="seekh")
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


def test_desk_in_a_real_browser(iv, iv_server, tmp_path):
    base, browser, key = iv_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route):
        pg.evaluate(f"location.hash = '{route}'")

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/investments")
    pg.wait_for_selector("text=Set up your portfolio", timeout=20000)
    snap(pg, "inv-setup-1440")
    pg.fill("form[data-form=setup] [name=country]", "US")
    pg.fill("form[data-form=setup] [name=currency]", "USD")
    pg.click("form[data-form=setup] [type=submit]")
    pg.wait_for_selector(".cs-hero", timeout=20000)
    ws = iv.summary(T)["workspace"]["id"]
    # gains: upload the broker file in the page
    go(pg, "#/gains")
    pg.wait_for_selector("text=Upload trades", timeout=20000)
    f = tmp_path / "broker.csv"
    f.write_text(TRADES)
    pg.set_input_files("form[data-kind=trades] input[type=file]", str(f))
    pg.wait_for_selector(".iv-sale", timeout=20000)
    pg.click(".iv-sale:has(.cs-tag.warn) summary")
    pg.wait_for_selector("text=loss not allowed now", timeout=20000)
    pg.fill("form[data-form=trade] [name=date]", "2025-09-01")
    pg.fill("form[data-form=trade] [name=symbol]", "ZED")
    pg.fill("form[data-form=trade] [name=qty]", "1")
    pg.fill("form[data-form=trade] [name=price]", "100")
    pg.click("form[data-form=trade] [type=submit]")
    pg.wait_for_selector("text=Trade added", timeout=20000)          # a buy after the sale: the desk keeps it
    snap(pg, "inv-gains-1440")
    # portfolio: build from the trades, give the prices, see the ring
    iv.do(T, "settings", {"workspace": ws, "max_pct": 40, "targets": {"shares": 70, "funds": 30}})
    go(pg, "#/portfolio")
    pg.wait_for_selector("[data-fromtrades]", timeout=20000)
    pg.on("dialog", lambda d: d.accept())
    pg.click("[data-fromtrades]")
    pg.wait_for_selector("input.iv-px[name=ACME]", timeout=20000)
    pg.fill("input.iv-px[name=ACME]", "70")
    pg.fill("input.iv-px[name=ZED]", "250")
    pg.click("form[data-form=prices] [type=submit]")
    pg.wait_for_selector("text=2 prices saved", timeout=20000)
    pg.wait_for_selector(".iv-drift", timeout=20000)
    assert iv.do(T, "portfolio", {"workspace": ws})["total"] == 950.0
    snap(pg, "inv-portfolio-1440")
    # plans: her assumptions, then both plans with their charts
    go(pg, "#/plans")
    pg.wait_for_selector("form[data-form=assume]", timeout=20000)
    pg.fill("form[data-form=assume] [name=return_pct]", "5")
    pg.fill("form[data-form=assume] [name=inflation_pct]", "2")
    pg.click("form[data-form=assume] [type=submit]")
    pg.wait_for_selector("text=assumptions are saved", timeout=20000)
    pg.fill("form[data-which=fees] [name=fee_pct]", "1")
    pg.click("form[data-which=fees] [type=submit]")
    pg.wait_for_selector("text=Fees cost you", timeout=20000)
    pg.fill("form[data-which=retire] [name=withdraw]", "100")
    pg.click("form[data-which=retire] [type=submit]")
    pg.wait_for_selector("text=Runs out", timeout=20000)
    snap(pg, "inv-plans-1440")
    # options & futures
    go(pg, "#/derivatives")
    pg.wait_for_selector("form[data-form=position]", timeout=20000)
    pg.select_option("form[data-form=position] [name=side]", "short")
    pg.fill("form[data-form=position] [name=strike]", "60")
    pg.fill("form[data-form=position] [name=premium]", "2")
    pg.fill("form[data-form=position] [name=multiplier]", "100")
    pg.click("form[data-form=position] [type=submit]")
    pg.wait_for_selector(".iv-p.risk", timeout=20000)
    snap(pg, "inv-derivatives-1440")
    # scam check
    go(pg, "#/scam")
    pg.fill("form[data-form=scam] [name=text]", "Guaranteed 20% a month, act now, send money to my account")
    pg.fill("form[data-form=scam] [name=firm]", "Quick Gains")
    pg.click("form[data-form=scam] [type=submit]")
    pg.wait_for_selector(".iv-verdict.bad", timeout=20000)
    snap(pg, "inv-scam-1440")
    # fund NAV
    go(pg, "#/funds")
    pg.fill("form[data-form=nav] [name=units]", "1000")
    pg.fill("form[data-form=nav] [name=assets]", "Shares, 10500")
    pg.fill("form[data-form=nav] [name=reported_nav]", "10.5")
    pg.click("form[data-form=nav] [type=submit]")
    pg.wait_for_selector("text=Within tolerance", timeout=20000)
    snap(pg, "inv-funds-1440")
    go(pg, "#/settings")
    pg.wait_for_selector("form[data-form=targets]", timeout=20000)
    pg.fill("form[data-form=settings] [name=country]", "GB")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("text=Saved", timeout=20000)
    assert iv.summary(T)["desk"]["country"] == "GB"
    snap(pg, "inv-settings-1440")
    go(pg, "#/today")
    pg.wait_for_selector(".iv-donut", timeout=20000)
    snap(pg, "inv-today-1440")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".iv-donut", "today"), ("#/portfolio", ".iv-tb", "portfolio"), ("#/gains", ".iv-sale", "gains"),
                             ("#/plans", "form[data-form=assume]", "plans"), ("#/derivatives", ".iv-p", "derivatives"), ("#/scam", "text=Offers you checked", "scam"),
                             ("#/funds", ".iv-fund", "funds"), ("#/settings", "form[data-form=targets]", "settings")):
        pg.goto(base + "/console/investments" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"inv-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#ivPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
