"""COMMUNITY FINANCE DESK: the Community, Inclusive & Islamic Finance employee's own section, built like Markets and Investments - its
own chat (kind 'community') with the desk block + the community tool in view; a desk set up on the page (or any finance workspace she
has); a spoken / typed cash book; a savings group's members, meetings (the box cannot lend what it does not hold), who owes what and the
share-out, a closed cycle kept as a history; a rotating group or auction chit with its rounds; her loans' true cost against her income;
a field officer's collection sheet and portfolio at risk; crop plans and claims; sending money home; mobile-money fees and scam signs;
zakat and Islamic structures; read-only team roles; the downloads; no money moved; and the desk walked in a real browser."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"
D = lambda n: (date.today() + timedelta(days=n)).isoformat()      # noqa: E731


@pytest.fixture
def cm(env):
    from app import cmchat as CM
    CM._OF.clear()
    CM._BLOCK.clear()
    return CM


def _desk(cm, country="KE", currency="KES", size="business"):
    return cm.setup(T, {"name": "Umoja group", "country": country, "currency": currency, "size": size})["desk"]["id"]


def test_hire_setup_chat_block_and_wiring(cm):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert cm.summary(T)["hired"] is False
    hire.hire(T, "community_finance", trust="seekh")
    d = cm.summary(T)
    assert d["hired"] and d["workspace"] is None and "never collects" in d["foot"]
    assert "Set up your desk" in cm.greeting(T) and "No desk set up yet" in cm.block(T)
    with pytest.raises(cm.CmDeskError):
        cm.setup(T, {"name": "X", "country": "KEN", "currency": "KES"})
    ws = _desk(cm)
    d = cm.summary(T)
    assert d["workspace"]["id"] == ws and d["can_write"] and d["desk"]["cash"]["empty"] and "VSLA" in d["desk"]["style"]
    chat = cm.current(T)
    assert cm.is_community(chat["id"]) and cm.owns(T, chat["id"])
    cm.forget(T)
    blk = cm.block(T)
    assert "<community_desk>" in blk and "never collects" in blk and "scholar" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_cmc.is_community(conversation_id)" in src and "adm.admit_families(_cmc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["community_finance"] in cm.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"markets", "community"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/community")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "cmdesk.js" in r.text
    html = (root / "server/app/static/console/cmdesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "invdesk.css", "mktdesk.css", "cmdesk.css", "cmdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/community')" in (root / "server/app/static/console/v2.js").read_text()
    assert "community_finance: 'cmdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/community'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_cashbook_and_group(cm):
    from app.employee import hire
    hire.hire(T, "community_finance", trust="seekh")
    ws = _desk(cm)
    r = cm.do(T, "cash_lines", {"workspace": ws, "text": f"{D(-1)} sold tea 250\npaid rent 2000\nsold mandazi 300\nhello there", "date": D(0)})
    assert r["added"] == 3 and r["could_not_read"] == ["hello there"]
    cm.do(T, "settings", {"workspace": ws, "cash_opening": 5000})
    cb = cm.do(T, "cashbook", {"workspace": ws})
    assert cb["money_in"] == 550 and cb["money_out"] == 2000 and cb["closing"] == 3550 and cb["by_day"][-1]["balance"] == 3550
    # the group
    for nm in ("Amina", "Baraka", "Chiku"):
        cm.do(T, "add", {"workspace": ws, "register": "members", "name": nm})
    cm.do(T, "settings", {"workspace": ws, "group": {"name": "Umoja", "share_value": 100, "rate_pct": 10}})
    cm.do(T, "meeting", {"workspace": ws, "date": D(-14), "members": {"Amina": {"savings": 5}, "Baraka": {"savings": 3, "social": 50},
                                                                       "Chiku": {"savings": 2}}, "counted": 1000})
    with pytest.raises(cm.CmDeskError, match="cannot lend"):
        cm.do(T, "meeting", {"workspace": ws, "date": D(-7), "loans": "Chiku, 5000, 1"})
    assert len(cm._state(T, ws)["meetings"]) == 1                 # a refused meeting is not kept
    cm.do(T, "meeting", {"workspace": ws, "date": D(-7), "loans": "Chiku, 500, 1", "counted": 450})
    g = cm.do(T, "group", {"workspace": ws})
    assert g["cash_box"] == 500 and g["owes"] == {"Chiku": 550} and g["count_mismatches"][0]["difference"] == -50
    assert g["share_out"]["possible"] is False
    with pytest.raises(cm.CmDeskError, match="still out"):
        cm.do(T, "close_cycle", {"workspace": ws})
    with pytest.raises(cm.CmDeskError, match="fixed once"):
        cm.do(T, "settings", {"workspace": ws, "group": {"share_value": 50}})
    cm.do(T, "meeting", {"workspace": ws, "date": D(0), "members": {"Chiku": {"repay": 550}}})
    loan_m = next(m for m in cm._state(T, ws)["meetings"] if m["loans"])
    with pytest.raises(cm.CmDeskError, match="do not add up"):
        cm.do(T, "remove", {"workspace": ws, "register": "meetings", "n": loan_m["n"]})
    g = cm.do(T, "group", {"workspace": ws})
    so = g["share_out"]
    assert so["possible"] and so["pot"] == 1050 and abs(sum(so["per_member"].values()) - 1050) < 0.001 and so["per_member"]["Amina"] == 525
    d = cm.summary(T)["desk"]
    assert any("counted" in x["say"] for x in d["needs"])
    c = cm.do(T, "close_cycle", {"workspace": ws})
    st = cm._state(T, ws)
    assert c["closed"] and st["meetings"] == [] and st["cycles"][0]["pot"] == 1050 and st["group"]["opening_social"] == 50


def test_rosca_loans_field_farm_send_zakat_islamic(cm):
    from app.employee import hire
    from app.fin import laws as L
    hire.hire(T, "community_finance", trust="seekh")
    ws = _desk(cm, "IN", "INR", "personal")
    cm.do(T, "rosca_save", {"workspace": ws, "members": "Asha\nBina\nCyra\nDev", "contribution": 1000, "auction": True, "organiser_fee_pct": 5,
                       "start": D(-40), "frequency": "monthly", "written_record": "false"})
    r = cm.do(T, "rosca", {"workspace": ws})
    assert r["next"]["takes"] == "Asha" and "nothing is written down" in r["flags"] and not r["complete"]
    with pytest.raises(cm.CmDeskError, match="below the organiser"):
        cm.do(T, "rosca_round", {"workspace": ws, "bid": 100})
    for b in (800, 600, 400, 200):
        cm.do(T, "rosca_round", {"workspace": ws, "bid": b})
    r = cm.do(T, "rosca", {"workspace": ws})
    assert r["complete"] and r["next"] is None and r["rounds"][0]["taker_receives"] == 3200
    with pytest.raises(cm.CmDeskError, match="complete"):
        cm.do(T, "rosca_round", {"workspace": ws, "bid": 300})
    # her loans
    cm.do(T, "add", {"workspace": ws, "register": "loans", "lender": "MFI One", "amount": 10000, "installment": 600, "installments": 20,
                     "frequency": "weekly", "upfront_fees": 200})
    cm.do(T, "add", {"workspace": ws, "register": "loans", "lender": "App Loan", "installment": 2000, "frequency": "monthly"})
    cm.do(T, "add", {"workspace": ws, "register": "loans", "lender": "Shop credit", "installment": 500, "frequency": "monthly"})
    cm.do(T, "settings", {"workspace": ws, "income_monthly": 12000, "max_share_pct": 40})
    lo = cm.do(T, "loans", {"workspace": ws})
    assert lo["loans"][0]["cost"]["effective_yearly_pct"] > 50 and lo["repayments"]["lenders"] == 3
    assert lo["repayments"]["over_your_limit"] and "flag" in lo["repayments"]
    assert cm.do(T, "loan_check", {"workspace": ws, "amount": 5000, "installment": 300, "installments": 20, "frequency": "weekly"})["loan"]["cost"] == 1000
    # collections
    cm.do(T, "upload", {"workspace": ws, "kind": "collections", "text": "Member,Due,Collected\nA,500,500\nB,500,300\nC,500,0\n"})
    cm.do(T, "upload", {"workspace": ws, "kind": "portfolio", "text": "Borrower,Loan Balance,DPD\nA,4000,0\nB,3000,12\nC,3000,45\n"})
    f = cm.do(T, "field", {"workspace": ws})
    assert f["collection_rate_pct"] == 53.33 and f["par30_pct"] == 30 and f["by_age"]["31-60 days"] == 3000
    # farm
    cm.do(T, "crop", {"workspace": ws, "name": "Maize 2026", "unit": "kg", "area": 2, "yield_per_unit": 1500, "price": 20,
                      "costs": "seed, 8000\nfertiliser, 12000", "threshold_yield": 1500, "actual_yield": 1200, "sum_insured": 40000})
    c = cm.do(T, "crops", {"workspace": ws})["crops"][0]["result"]
    assert c["plan"]["margin"] == 40000 and c["claim"]["claim"] == 8000
    # send money
    cm.do(T, "add", {"workspace": ws, "register": "providers", "name": "A", "fee": 5, "rate": 82})
    cm.do(T, "add", {"workspace": ws, "register": "providers", "name": "B", "fee_pct": 1, "rate": 83.5})
    cm.do(T, "remit_save", {"workspace": ws, "send": 100, "mid_rate": 84, "to_currency": "INR"})
    rm = cm.do(T, "remit", {"workspace": ws})
    assert rm["most_arrives_with"] == "B" and rm["ideal"] == 8400
    cm.do(T, "upload", {"workspace": ws, "kind": "tariff", "text": "From,To,Fee\n1,1000,10\n1001,5000,25\n"})
    mm = cm.do(T, "mm_fee", {"workspace": ws, "amount": 2000, "message": "You won a prize! Send your PIN to the agent"})
    assert mm["fee"]["fee"] == 25 and len(mm["scam_signs"]) >= 2
    # zakat + islamic
    z = cm.do(T, "zakat", {"workspace": ws, "nisab_basis": "gold", "gold_price_per_gram": 7000, "cash": 300000, "bank": 400000,
                           "gold": "20, 22, jewellery", "school": "hanafi", "debts_due": 50000, "lunar_year_passed": "yes", "hawl": D(10)})
    assert z["above_nisab"] and z["zakat"] > 0 and cm._state(T, ws)["zakat_log"][0]["zakat"] == z["zakat"]
    assert any("zakat date" in x["say"] for x in cm.summary(T)["desk"]["needs"])
    m = cm.do(T, "islamic", {"workspace": ws, "structure": "murabaha", "cost": 100000, "markup_pct": 12, "installments": 12})
    assert m["sale_price"] == 112000 and "Shariah board" in m["board"]
    with pytest.raises(L.Refused):
        cm._engine(T, "owner", "send_money", {})


def test_roles_routes_downloads(cm, monkeypatch):
    from app.employee import hire
    from app.fin.desks import books_ent as E
    from app.main import app
    hire.hire(T, "community_finance", trust="seekh")
    ws = _desk(cm)
    cm.do(T, "cash_lines", {"workspace": ws, "text": "sold eggs 400"})
    for nm in ("A", "B"):
        cm.do(T, "add", {"workspace": ws, "register": "members", "name": nm})
    cm.do(T, "meeting", {"workspace": ws, "date": D(0), "members": {"A": {"savings": 100}, "B": {"savings": 50}}})
    with pytest.raises(cm.CmDeskError, match="stays on the books"):
        cm.do(T, "remove", {"workspace": ws, "register": "members", "n": 1})
    real = E.access
    monkeypatch.setattr(E, "access", lambda caller, w: {**real(T, w), "role": "viewer", "name": "Bo"} if caller == "bo" else real(caller, w))
    assert cm.do("bo", "group", {"workspace": ws})["cash_box"] == 150
    with pytest.raises(cm.CmDeskError, match="read this desk"):
        cm.do("bo", "cash_lines", {"workspace": ws, "text": "sold eggs 1"})
    c = TestClient(app)
    assert c.get("/api/community/desk").json()["workspace"]["id"] == ws
    r = c.get(f"/api/community/download?workspace={ws}&what=cashbook")
    assert r.status_code == 200 and "balance" in r.text
    r = c.get(f"/api/community/download?workspace={ws}&what=group")
    assert r.status_code == 200 and "share_out" in r.text and "A,100" in r.text
    assert c.post("/api/community/do/nothing", json={"workspace": ws}).status_code == 400
    assert c.get("/api/community/chat").json()["id"]


def test_remit_comparison_is_not_moving_money(env):
    """The F11 tool's `remit` action compares providers - the finance gate used to refuse it as 'moving money'."""
    from app.fin import core, laws as L
    from app.fin.desks import community as CM
    a = {"send": 100, "mid_rate": 84, "providers": [{"name": "A", "fee": 5, "rate": 82}]}
    assert core.run_tool(T, "owner", "community_finance", "remit", a, lambda: CM.run(T, "remit", a))["providers"]
    for act in ("remit_now", "send_remittance", "send_money", "pay"):
        assert L.act_of(act) == "move_money"


@pytest.fixture
def cm_server(cm, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "community_finance", trust="seekh")
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


def test_desk_in_a_real_browser(cm, cm_server, tmp_path):
    base, browser, key = cm_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=20000)

    def up(pg, kind, name, text):
        f = tmp_path / name
        f.write_text(text)
        pg.set_input_files(f"form[data-kind={kind}] input[type=file]", str(f))

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/community")
    pg.wait_for_selector("text=Set up your community money desk", timeout=20000)
    snap(pg, "cm-setup-1440")
    pg.fill("form[data-form=setup] [name=name]", "Umoja group")
    pg.select_option("form[data-form=setup] [name=size]", "business")
    pg.fill("form[data-form=setup] [name=country]", "KE")
    pg.fill("form[data-form=setup] [name=currency]", "KES")
    pg.click("form[data-form=setup] [type=submit]")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    ws = cm.summary(T)["workspace"]["id"]
    # the cash book: spoken lines, one it cannot read
    go(pg, "#/cash", "form[data-form=cash]")
    pg.fill("form[data-form=cash] [name=text]", f"{D(-2)} sold tea 250\n{D(-1)} paid rent 2000\nsold mandazi 900\nhello")
    pg.click("form[data-form=cash] [type=submit]")
    pg.wait_for_selector(".cm-unread", timeout=20000)
    pg.wait_for_selector(".cm-line", timeout=20000)
    assert cm._state(T, ws)["cash"][0]["amount"] == 250
    snap(pg, "cm-cash-1440")
    # the group: rules, members, two meetings
    go(pg, "#/settings", "form[data-form=grules]")
    pg.fill("form[data-form=grules] [name=name]", "Umoja")
    pg.fill("form[data-form=grules] [name=share_value]", "100")
    pg.fill("form[data-form=grules] [name=rate_pct]", "10")
    pg.fill("form[data-form=grules] [name=cycle_end]", D(20))
    pg.click("form[data-form=grules] [type=submit]")
    pg.wait_for_selector("text=rules are saved", timeout=20000)
    snap(pg, "cm-settings-1440")
    go(pg, "#/group", "form[data-which=members]")
    up(pg, "members", "m.csv", "Name,Phone\nAmina,0700\nBaraka,\nChiku,\n")
    pg.wait_for_selector("form[data-form=meeting]", timeout=20000)
    pg.fill("[name='m.Amina.savings']", "5")
    pg.fill("[name='m.Baraka.savings']", "3")
    pg.fill("[name='m.Chiku.savings']", "2")
    pg.fill("[name='m.Baraka.social']", "50")
    pg.fill("form[data-form=meeting] [name=date]", D(-14))
    pg.click("form[data-form=meeting] [type=submit]")
    pg.wait_for_selector("text=The meeting is saved", timeout=20000)
    pg.fill("form[data-form=meeting] [name=date]", D(-7))
    pg.fill("form[data-form=meeting] [name=loans]", "Chiku, 400, 1")
    pg.fill("form[data-form=meeting] [name=counted]", "590")
    pg.click("form[data-form=meeting] [type=submit]")
    pg.wait_for_selector(".cm-line", timeout=20000)
    pg.wait_for_selector("text=Count again", timeout=20000)
    assert cm.do(T, "group", {"workspace": ws})["owes"] == {"Chiku": 440}
    snap(pg, "cm-group-1440")
    # the rotating group
    go(pg, "#/rosca", "form[data-form=rosca]")
    pg.fill("form[data-form=rosca] [name=members]", "Asha\nBina\nCyra\nDev")
    pg.fill("form[data-form=rosca] [name=contribution]", "1000")
    pg.fill("form[data-form=rosca] [name=start]", D(-30))
    pg.select_option("form[data-form=rosca] [name=written_record]", "false")
    pg.click("form[data-form=rosca] [type=submit]")
    pg.wait_for_selector(".cm-rounds", timeout=20000)
    pg.click("form[data-form=round] [type=submit]")
    pg.wait_for_selector(".cm-rounds li.done", timeout=20000)
    assert cm._state(T, ws)["rosca"]["paid_rounds"] == 1
    snap(pg, "cm-rosca-1440")
    # loans + an offer
    go(pg, "#/loans", "form[data-form=offer]")
    pg.fill("form[data-which=loans] [name=lender]", "MFI One")
    pg.fill("form[data-which=loans] [name=installment]", "600")
    pg.select_option("form[data-which=loans] [name=frequency]", "weekly")
    pg.fill("form[data-which=loans] [name=amount]", "10000")
    pg.fill("form[data-which=loans] [name=installments]", "20")
    pg.click("form[data-which=loans] [type=submit]")
    pg.wait_for_selector("text=The dearest loan", timeout=20000)
    pg.fill("form[data-form=offer] [name=amount]", "5000")
    pg.fill("form[data-form=offer] [name=installment]", "300")
    pg.fill("form[data-form=offer] [name=installments]", "20")
    pg.click("form[data-form=offer] [type=submit]")
    pg.wait_for_selector(".cm-res .cm-big", timeout=20000)
    snap(pg, "cm-loans-1440")
    # collections
    go(pg, "#/field", "form[data-kind=collections]")
    up(pg, "collections", "c.csv", "Member,Due,Collected\nA,500,500\nB,500,300\n")
    pg.wait_for_selector("text=Paid short today", timeout=20000)
    up(pg, "portfolio", "p.csv", "Borrower,Loan Balance,DPD\nA,4000,0\nB,3000,45\n")
    pg.wait_for_selector("text=Late loans", timeout=20000)
    snap(pg, "cm-field-1440")
    # farm
    go(pg, "#/farm", "form[data-form=crop]")
    pg.fill("form[data-form=crop] [name=name]", "Maize 2026")
    pg.fill("form[data-form=crop] [name=unit]", "kg")
    pg.fill("form[data-form=crop] [name=area]", "2")
    pg.fill("form[data-form=crop] [name=yield_per_unit]", "1500")
    pg.fill("form[data-form=crop] [name=price]", "20")
    pg.fill("form[data-form=crop] [name=costs]", "seed, 8000\nfertiliser, 12000")
    pg.fill("form[data-form=crop] [name=threshold_yield]", "1500")
    pg.fill("form[data-form=crop] [name=actual_yield]", "1200")
    pg.fill("form[data-form=crop] [name=sum_insured]", "40000")
    pg.click("form[data-form=crop] [type=submit]")
    pg.wait_for_selector(".cm-claim", timeout=20000)
    snap(pg, "cm-farm-1440")
    # send money + a scam message
    go(pg, "#/send", "form[data-form=remit]")
    for nm, fee, rate in (("Bank A", "5", "82"), ("App B", "0", "83.5")):
        pg.fill("form[data-which=providers] [name=name]", nm)
        pg.fill("form[data-which=providers] [name=fee]", fee)
        pg.fill("form[data-which=providers] [name=rate]", rate)
        pg.click("form[data-which=providers] [type=submit]")
        pg.wait_for_selector(f"text={nm}", timeout=20000)
    pg.fill("form[data-form=remit] [name=send]", "100")
    pg.fill("form[data-form=remit] [name=mid_rate]", "84")
    pg.fill("form[data-form=remit] [name=to_currency]", "INR")
    pg.click("form[data-form=remit] [type=submit]")
    pg.wait_for_selector("text=gets the most home", timeout=20000)
    pg.fill("form[data-form=mm] [name=message]", "You won a prize, send your PIN to the agent")
    pg.click("form[data-form=mm] [type=submit]")
    pg.wait_for_selector(".cm-warn", timeout=20000)
    snap(pg, "cm-send-1440")
    # zakat + an Islamic structure
    go(pg, "#/zakat", "form[data-form=zakat]")
    pg.fill("form[data-form=zakat] [name=gold_price_per_gram]", "9000")
    pg.fill("form[data-form=zakat] [name=cash]", "300000")
    pg.fill("form[data-form=zakat] [name=bank]", "600000")
    pg.fill("form[data-form=zakat] [name=gold]", "20, 22, jewellery")
    pg.select_option("form[data-form=zakat] [name=school]", "hanafi")
    pg.select_option("form[data-form=zakat] [name=lunar_year_passed]", "yes")
    pg.click("form[data-form=zakat] [type=submit]")
    pg.wait_for_selector(".cm-nisab", timeout=20000)
    pg.select_option("form[data-form=islamic] [name=structure]", "diminishing_musharaka")
    pg.fill("form[data-form=islamic] [name=price]", "1000000")
    pg.fill("form[data-form=islamic] [name=own_contribution]", "200000")
    pg.fill("form[data-form=islamic] [name=rent_pct_per_period]", "0.8")
    pg.fill("form[data-form=islamic] [name=buyback_per_period]", "20000")
    pg.click("form[data-form=islamic] [type=submit]")
    pg.wait_for_selector("form[data-form=islamic] .cm-line", timeout=20000)
    snap(pg, "cm-zakat-1440")
    go(pg, "#/today", ".cs-hero")
    pg.wait_for_selector(".cm-line", timeout=20000)
    snap(pg, "cm-today-1440")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".cs-hero", "today"), ("#/cash", ".cm-line", "cash"), ("#/group", ".cm-meet", "group"),
                             ("#/rosca", ".cm-rounds", "rosca"), ("#/loans", ".cm-big", "loans"), ("#/field", ".mk-bars", "field"),
                             ("#/farm", ".cm-claim", "farm"), ("#/send", ".mk-bars", "send"), ("#/zakat", "form[data-form=islamic]", "zakat"),
                             ("#/settings", "form[data-form=grules]", "settings")):
        pg.goto(base + "/console/community" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"cm-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#cmPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
