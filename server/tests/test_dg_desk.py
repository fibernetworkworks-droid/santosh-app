"""DIGITAL ASSETS DESK: the Digital Assets employee's own section, built like Community and Markets - its own chat (kind 'digital') with
the desk block + the digital-assets tool in view; a desk set up on the page (or any finance workspace she has); an exchange export ->
gains by HER country's method, by tax year, holdings and coin income; her wallets and an address checked before sending (look-alikes);
stablecoin payments at HER rate and the peg; token checks; a stablecoin reserve under HER eligible list; custody ledger against the
wallets; transfers against the travel rule and counted for a return; trades watched for self-trades / round trips; no seed phrase ever
taken; read-only team roles; the downloads; and the desk walked in a real browser."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"
D = lambda n: (date.today() + timedelta(days=n)).isoformat()      # noqa: E731
BTC = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
BTC2 = BTC[:8] + "aaaaaa" + BTC[14:]        # starts and ends like hers, but is not
EXPORT = ("Your transactions\nUser,me\n\nTimestamp,Transaction Type,Asset,Quantity Transacted,Subtotal,Notes\n"
          "2025-01-10T10:00:00Z,Buy,BTC,1,30000,\n2025-02-01T10:00:00Z,Buy,ETH,10,20000,\n"
          "2025-06-01T10:00:00Z,Sell,BTC,0.5,25000,\n2025-07-01T10:00:00Z,Staking Income,ETH,1,2000,staking\n"
          "2025-07-02T10:00:00Z,Send,ETH,1,2000,to my ledger\n")


@pytest.fixture
def dg(env):
    from app import dgchat as DG
    DG._OF.clear()
    DG._BLOCK.clear()
    return DG


def _desk(dg, country="GB", currency="GBP", size="personal"):
    return dg.setup(T, {"name": "My coins", "country": country, "currency": currency, "size": size})["desk"]["id"]


def test_hire_setup_chat_block_and_wiring(dg):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert dg.summary(T)["hired"] is False
    hire.hire(T, "digital_assets", trust="seekh")
    d = dg.summary(T)
    assert d["hired"] and d["workspace"] is None and "never holds a key" in d["foot"]
    assert "Set up your desk" in dg.greeting(T) and "No desk set up yet" in dg.block(T)
    ws = _desk(dg)
    d = dg.summary(T)
    assert d["workspace"]["id"] == ws and d["can_write"] and d["desk"]["gains"]["empty"] and "pool" in d["desk"]["method_name"]
    chat = dg.current(T)
    assert dg.is_digital(chat["id"]) and dg.owns(T, chat["id"])
    dg.forget(T)
    blk = dg.block(T)
    assert "<digital_desk>" in blk and "seed phrase" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_dgc.is_digital(conversation_id)" in src and "adm.admit_families(_dgc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["digital_assets"] in dg.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"digital"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/digital")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "dgdesk.js" in r.text
    html = (root / "server/app/static/console/dgdesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "invdesk.css", "mktdesk.css", "cmdesk.css", "dgdesk.css", "dgdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/digital')" in (root / "server/app/static/console/v2.js").read_text()
    assert "digital_assets: 'dgdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/digital'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_gains_wallets_pay_tokens(dg):
    from app.employee import hire
    hire.hire(T, "digital_assets", trust="seekh")
    ws = _desk(dg)
    r = dg.do(T, "upload", {"workspace": ws, "kind": "events", "text": EXPORT})
    assert "5 transactions added" in r["says"]
    assert "already" in dg.do(T, "upload", {"workspace": ws, "kind": "events", "text": EXPORT})["says"]
    dg.do(T, "add", {"workspace": ws, "register": "events", "date": "2025-08-01", "type": "swap", "asset": "ETH", "qty": 2, "value": 5000,
                     "get_asset": "SOL", "get_qty": 30})
    g = dg.do(T, "gains", {"workspace": ws})
    assert g["gains"] > 0 and g["income_total"] == 2000 and g["own_transfers_ignored"] == 1 and "2025" in g["years"]
    assert {h["symbol"] for h in g["holdings"]} >= {"BTC", "ETH", "SOL"}
    dg.do(T, "settings", {"workspace": ws, "tax_year_start": "04-06"})
    assert "2025/26" in dg.do(T, "gains", {"workspace": ws})["years"]
    with pytest.raises(dg.DgDeskError, match="seed phrase"):
        dg.do(T, "add", {"workspace": ws, "register": "wallets", "label": "x", "chain": "bitcoin", "address": BTC, "seed_phrase": "a b c"})
    with pytest.raises(dg.DgDeskError, match="not a valid"):
        dg.do(T, "add", {"workspace": ws, "register": "wallets", "label": "Cold", "chain": "bitcoin", "address": BTC[:-1] + "5"})
    dg.do(T, "add", {"workspace": ws, "register": "wallets", "label": "Cold", "chain": "bitcoin", "address": BTC})
    c = dg.do(T, "check", {"workspace": ws, "chain": "bitcoin", "address": BTC2, "message": "Please share your 12-word seed phrase to validate wallet"})
    assert c["address"]["valid_shape"] is False and c["looks_like_yours_but_is_not"] == [BTC] and len(c["signs"]) >= 2
    assert any("looks like yours" in x["say"] for x in dg.summary(T)["desk"]["needs"])
    # stablecoin
    q = dg.do(T, "quote", {"workspace": ws, "invoice": 1000, "rate": 0.8, "coin": "usdc", "network_fee": 1})
    assert q["payment"]["coins"] == 1250 and q["payment"]["with_fee"] == 1251 and dg._state(T, ws)["pay"]["coin"] == "USDC"
    dg.do(T, "upload", {"workspace": ws, "kind": "prices", "text": "Date,Close\n2026-11-01,1.0\n2026-11-02,0.97\n2026-11-03,1.001\n"})
    p = dg.do(T, "pay", {"workspace": ws})
    assert len(p["peg"]["off_peg"]) == 1
    t = dg.do(T, "token", {"workspace": ws, "name": "MOON", "supply": 1000, "top_holders": "400\n300\n100", "mint_authority_open": True,
                           "audited": "false", "max_top10_pct": 50})
    assert t["level"] == "high" and dg._state(T, ws)["tokens"][0]["level"] == "high"


def test_reserve_custody_transfers_watch(dg):
    from app.employee import hire
    hire.hire(T, "digital_assets", trust="seekh")
    ws = _desk(dg, "SG", "USD", "institution")
    dg.do(T, "upload", {"workspace": ws, "kind": "assets", "text": "Type,Value,Held At\ncash,600000,Bank A\ntbill_3m,300000,Bank B\ncorporate_bond,200000,Bank A\n"})
    assert dg.do(T, "reserve", {"workspace": ws})["empty"]
    dg.do(T, "settings", {"workspace": ws, "reserve": {"supply": 1000000, "eligible": "cash\ntbill_3m", "max_per_holder_pct": 60}})
    r = dg.do(T, "reserve", {"workspace": ws})
    assert r["shortfall"] == 100000 and r["not_eligible"][0]["type"] == "corporate_bond" and r["over_holder_limit"] == ["Bank A"]
    dg.do(T, "upload", {"workspace": ws, "kind": "ledger", "text": "Client,Asset,Qty\nc1,BTC,2\nc2,BTC,1.5\nc3,ETH,-1\n"})
    dg.do(T, "upload", {"workspace": ws, "kind": "balances", "text": "Wallet,Asset,Balance\nhot,BTC,1\ncold,BTC,2\n"})
    cu = dg.do(T, "custody", {"workspace": ws})
    assert cu["short"] == ["BTC"] and cu["negative_client_lines"]
    dg.do(T, "upload", {"workspace": ws, "kind": "transfers", "text": f"ID,Date,Type,Value,Originator Name,Originator Account,Beneficiary Name,Beneficiary Account\n"
                                                                     f"T1,{D(-40)},withdrawal,500,Ann,4111111111111111,Bob,GB29NWBK60161331926819\nT2,{D(-2)},deposit,5000,Ann,ACC1,,\n"})
    assert dg._state(T, ws)["transfers"][0]["originator_account"] == "…1111"        # an account kept as its last 4
    tf = dg.do(T, "transfers", {"workspace": ws})
    assert "travel" not in tf and sum(v["count"] for p in tf["returns"].values() for v in p.values()) == 2
    dg.do(T, "settings", {"workspace": ws, "threshold": 1000})
    tf = dg.do(T, "transfers", {"workspace": ws})
    assert tf["travel"]["held"] == ["T2"]
    dg.do(T, "upload", {"workspace": ws, "kind": "trades", "text": "ID,Time,Asset,Qty,Buyer,Seller\nX1,2026-11-01 10:00,TOK,5,a,a\nX2,2026-11-01 10:05,TOK,5,b,c\nX3,2026-11-01 10:10,TOK,5,c,b\n"})
    w = dg.do(T, "watch", {"workspace": ws})
    assert w["self_trades"] == ["X1"] and w["round_trips"] == [["X2", "X3"]]
    needs = " | ".join(x["say"] for x in dg.summary(T)["desk"]["needs"])
    assert "reserve is short" in needs and "BTC" in needs and "travel-rule" in needs and "market-abuse" in needs


def test_roles_routes_downloads(dg, monkeypatch):
    from app.employee import hire
    from app.fin.desks import books_ent as E
    from app.main import app
    hire.hire(T, "digital_assets", trust="seekh")
    ws = _desk(dg, "US", "USD")
    dg.do(T, "upload", {"workspace": ws, "kind": "events", "text": EXPORT})
    real = E.access
    monkeypatch.setattr(E, "access", lambda caller, w: {**real(T, w), "role": "viewer", "name": "Bo"} if caller == "bo" else real(caller, w))
    assert dg.do("bo", "gains", {"workspace": ws})["net"] > 0
    with pytest.raises(dg.DgDeskError, match="read this desk"):
        dg.do("bo", "settings", {"workspace": ws, "method": "fifo"})
    c = TestClient(app)
    assert c.get("/api/digital/desk").json()["workspace"]["id"] == ws
    r = c.get(f"/api/digital/download?workspace={ws}&what=gains")
    assert r.status_code == 200 and "proceeds" in r.text and "income: staking" in r.text
    assert c.post("/api/digital/do/send_now", json={"workspace": ws}).status_code == 400
    assert c.post("/api/digital/do/add", json={"workspace": ws, "register": "wallets", "private_key": "x"}).status_code == 400
    assert c.get("/api/digital/chat").json()["id"]


@pytest.fixture
def dg_server(dg, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "digital_assets", trust="seekh")
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


def test_desk_in_a_real_browser(dg, dg_server, tmp_path):
    base, browser, key = dg_server
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
    pg.goto(base + "/console/digital")
    pg.wait_for_selector("text=Set up your digital assets desk", timeout=20000)
    snap(pg, "dg-setup-1440")
    pg.select_option("form[data-form=setup] [name=size]", "institution")
    pg.fill("form[data-form=setup] [name=country]", "GB")
    pg.fill("form[data-form=setup] [name=currency]", "GBP")
    pg.click("form[data-form=setup] [type=submit]")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    ws = dg.summary(T)["workspace"]["id"]
    go(pg, "#/gains", "form[data-kind=events]")
    up(pg, "events", "x.csv", EXPORT + "2026-02-01T10:00:00Z,Sell,ETH,4,9000,\n", "text=Each disposal")
    assert dg.do(T, "gains", {"workspace": ws})["income_total"] == 2000
    snap(pg, "dg-gains-1440")
    go(pg, "#/wallets", "form[data-form=check]")
    pg.fill("form[data-which=wallets] [name=label]", "Cold")
    pg.fill("form[data-which=wallets] [name=address]", BTC)
    pg.click("form[data-which=wallets] [type=submit]")
    pg.wait_for_selector("text=Cold", timeout=20000)
    pg.fill("form[data-form=check] [name=address]", BTC2)
    pg.fill("form[data-form=check] [name=message]", "Support here on telegram: share your 12-word seed phrase to validate wallet")
    pg.click("form[data-form=check] [type=submit]")
    pg.wait_for_selector(".dg-verdict.bad", timeout=20000)
    pg.wait_for_selector(".cm-warn", timeout=20000)
    snap(pg, "dg-wallets-1440")
    go(pg, "#/pay", "form[data-form=quote]")
    pg.fill("form[data-form=quote] [name=invoice]", "1000")
    pg.fill("form[data-form=quote] [name=coin]", "USDC")
    pg.fill("form[data-form=quote] [name=rate]", "0.79")
    pg.click("form[data-form=quote] [type=submit]")
    pg.wait_for_selector(".cm-res .cm-big", timeout=20000)
    up(pg, "prices", "p.csv", "Date,Close\n2026-11-01,1\n2026-11-02,0.998\n2026-11-03,0.97\n2026-11-04,1.001\n", ".dg-peg")
    snap(pg, "dg-pay-1440")
    go(pg, "#/tokens", "form[data-form=token]")
    pg.fill("form[data-form=token] [name=name]", "MOON")
    pg.fill("form[data-form=token] [name=supply]", "1000000")
    pg.fill("form[data-form=token] [name=max_top10_pct]", "50")
    pg.fill("form[data-form=token] [name=top_holders]", "400000\n250000\n90000")
    pg.select_option("form[data-form=token] [name=mint_authority_open]", "true")
    pg.select_option("form[data-form=token] [name=audited]", "false")
    pg.click("form[data-form=token] [type=submit]")
    pg.wait_for_selector(".dg-verdict.bad", timeout=20000)
    snap(pg, "dg-tokens-1440")
    go(pg, "#/reserve", "form[data-form=reserve]")
    pg.fill("form[data-form=reserve] [name=supply]", "1000000")
    pg.fill("form[data-form=reserve] [name=eligible]", "cash\ntbill_3m")
    pg.fill("form[data-form=reserve] [name=max_per_holder_pct]", "60")
    pg.click("form[data-form=reserve] [type=submit]")
    pg.wait_for_selector("text=reserve rules are saved", timeout=20000)
    up(pg, "assets", "r.csv", "Type,Value,Held At\ncash,600000,Bank A\ntbill_3m,300000,Bank B\ncorporate_bond,200000,Bank A\n", ".dg-cover")
    snap(pg, "dg-reserve-1440")
    go(pg, "#/custody", "form[data-kind=ledger]")
    up(pg, "ledger", "l.csv", "Client,Asset,Qty\nc1,BTC,2\nc2,BTC,1.5\nc3,ETH,10\n", "text=Client ledger")
    up(pg, "balances", "b.csv", "Wallet,Asset,Balance\nhot,BTC,1\ncold,BTC,2\ncold,ETH,10\n", ".dg-cust")
    snap(pg, "dg-custody-1440")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=threshold]", "1000")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("text=Saved", timeout=20000)
    snap(pg, "dg-settings-1440")
    go(pg, "#/transfers", "form[data-kind=transfers]")
    up(pg, "transfers", "t.csv", f"ID,Date,Type,Value,Originator Name,Originator Account,Beneficiary Name,Beneficiary Account\nT1,{D(-40)},withdrawal,500,Ann,ACC9,Bob,ACC8\nT2,{D(-2)},deposit,5000,Ann,ACC1,,\n", "text=Travel rule")
    snap(pg, "dg-transfers-1440")
    go(pg, "#/watch", "form[data-kind=trades]")
    up(pg, "trades", "w.csv", "ID,Time,Asset,Qty,Buyer,Seller\nX1,2026-11-01 10:00,TOK,5,a,a\nX2,2026-11-01 10:05,TOK,5,b,c\nX3,2026-11-01 10:10,TOK,5,c,b\n", ".dg-pair")
    snap(pg, "dg-watch-1440")
    go(pg, "#/today", ".cs-hero")
    pg.wait_for_selector(".dg-years", timeout=20000)
    snap(pg, "dg-today-1440")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".dg-years", "today"), ("#/gains", ".iv-kpis", "gains"), ("#/wallets", "form[data-form=check]", "wallets"),
                             ("#/pay", ".dg-peg", "pay"), ("#/tokens", ".cs-row", "tokens"), ("#/reserve", ".dg-cover", "reserve"),
                             ("#/custody", ".dg-cust", "custody"), ("#/transfers", "text=Travel rule", "transfers"), ("#/watch", ".dg-pair", "watch"),
                             ("#/settings", "form[data-form=settings]", "settings")):
        pg.goto(base + "/console/digital" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"dg-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#dgPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
