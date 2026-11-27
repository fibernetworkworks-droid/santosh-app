"""PUBLIC FINANCE DESK: the Public Sector employee's own section, built like Digital Assets and Community - its own chat (kind 'public')
with the desk block + the public-sector tool in view; scheme rules each with a source, cases checked against them and the caseworker's
decision recorded (never made); over- and underpayments; a payment run reconciled with accounts kept only as a fingerprint and the last
4; deposit cover up to HER limit; banks' returns against HER thresholds and the period before; inspection findings; development projects;
read-only team roles; the downloads; nothing paid, awarded or refused; and the desk walked in a real browser."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"
D = lambda n: (date.today() + timedelta(days=n)).isoformat()      # noqa: E731
BEN = "Beneficiary ID,Amount,Account Number\nB1,100,4111111111111111\nB2,100,22223333\nB3,150,22223333\nB4,100,5555\n"
PAY = "Beneficiary ID,Payment Ref,Amount,Account Number\nB1,P1,100,4111111111111111\nB1,P1b,100,4111111111111111\nB2,P2,90,22223333\nB3,P3,150,22223333\nX9,P9,500,99990000\n"
RET = "Payment Ref,Status\nP1,success\nP1b,success\nP2,success\nP3,failed\nP9,success\n"


@pytest.fixture
def pb(env):
    from app import pbchat as PB
    PB._OF.clear()
    PB._BLOCK.clear()
    return PB


def _desk(pb, country="GB", currency="GBP"):
    return pb.setup(T, {"name": "Benefits office", "country": country, "currency": currency, "size": "institution"})["desk"]["id"]


def test_hire_setup_chat_block_and_wiring(pb):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert pb.summary(T)["hired"] is False
    hire.hire(T, "public_finance", trust="seekh")
    d = pb.summary(T)
    assert d["hired"] and d["workspace"] is None and "never pays" in d["foot"]
    assert "Set up your desk" in pb.greeting(T) and "No desk set up yet" in pb.block(T)
    ws = _desk(pb)
    d = pb.summary(T)
    assert d["workspace"]["id"] == ws and d["can_write"] and d["desk"]["g2p"]["empty"]
    chat = pb.current(T)
    assert pb.is_public(chat["id"]) and pb.owns(T, chat["id"])
    pb.forget(T)
    assert "<public_desk>" in pb.block(T) and "named official" in pb.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_pbc.is_public(conversation_id)" in src and "adm.admit_families(_pbc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["public_finance"] in pb.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"public")' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/public")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "pbdesk.js" in r.text
    html = (root / "server/app/static/console/pbdesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "mktdesk.css", "cmdesk.css", "dgdesk.css", "pbdesk.css", "pbdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/public')" in (root / "server/app/static/console/v2.js").read_text()
    assert "public_finance: 'pbdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/public'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_casework_overpay_g2p(pb):
    from app.employee import hire
    hire.hire(T, "public_finance", trust="seekh")
    ws = _desk(pb)
    with pytest.raises(pb.PbDeskError, match="source"):
        pb.do(T, "scheme", {"workspace": ws, "name": "Help", "tests": "income <= 100"})
    pb.do(T, "scheme", {"workspace": ws, "name": "Family help", "source": "Act 2021 s.4", "tests": "income <= 12000\nchildren >= 1\nresident == yes",
                        "base": 50, "per_field": "children", "per_value": 20, "max": 100, "evidence": "proof of income\nbirth certificate"})
    r = pb.do(T, "case", {"workspace": ws, "ref": "C-1", "household": "income, 9000\nchildren, 2\nresident, yes", "evidence_held": "proof of income"})
    s = r["schemes"][0]
    assert s["state"] == "meets the rules" and s["amount"] == 90 and s["evidence_missing"] == ["birth certificate"]
    r = pb.do(T, "case", {"workspace": ws, "ref": "C-2", "household": "income, 15000\nchildren, 1"})
    assert r["schemes"][0]["state"] == "does not meet" and r["schemes"][0]["unknown_fields"] == ["resident"]
    needs = " | ".join(x["say"] for x in pb.summary(T)["desk"]["needs"])
    assert "waits for a caseworker" in needs
    n = pb._state(T, ws)["cases"][0]["n"]
    pb.do(T, "decision", {"workspace": ws, "n": n, "decision": "Awarded 90 a month from June"})
    assert pb._state(T, ws)["cases"][0]["decision"].startswith("Awarded")
    with pytest.raises(pb.PbDeskError, match="action"):
        pb.do(T, "award", {"workspace": ws})
    # overpayments
    pb.do(T, "upload", {"workspace": ws, "kind": "due", "text": "Case,Period,Amount\nC-1,2026-01,90\nC-1,2026-02,90\nC-2,2026-01,0\n"})
    pb.do(T, "upload", {"workspace": ws, "kind": "paid", "text": "Case,Period,Amount\nC-1,2026-01,90\nC-1,2026-02,120\nC-2,2026-01,40\n"})
    op = pb.do(T, "overpay", {"workspace": ws})
    assert op["overpaid"] == 70 and op["cases"][0]["case"] == "C-2"
    # the payment run: accounts never kept whole
    for k, t in (("beneficiaries", BEN), ("payments", PAY), ("bank_return", RET)):
        pb.do(T, "upload", {"workspace": ws, "kind": k, "text": t})
    st = pb._state(T, ws)
    assert "4111111111111111" not in str(st) and st["payments"][0]["account_4"] == "…1111"
    g = pb.do(T, "g2p", {"workspace": ws})
    assert g["paid_twice"][0]["id"] == "B1" and g["wrong_amount"][0]["id"] == "B2" and g["failed"][0]["id"] == "B3"
    assert g["never_sent"][0]["id"] == "B4" and g["not_on_the_list"][0]["id"] == "X9" and g["shared_accounts"][0]["account"] == "…3333"


def test_deposit_supervision_inspections_projects(pb):
    from app.employee import hire
    hire.hire(T, "public_finance", trust="seekh")
    ws = _desk(pb, "KE", "KES")
    pb.do(T, "upload", {"workspace": ws, "kind": "accounts", "text": "Account,Holders,Balance\n111,D1,900000\n222,D1;D2,200000\n333,D3,50000\n444,,10\n"})
    assert pb.do(T, "deposit", {"workspace": ws})["need_limit"]
    pb.do(T, "upload", {"workspace": ws, "kind": "loans", "text": "Depositor,Due\nD3,20000\n"})
    pb.do(T, "upload", {"workspace": ws, "kind": "depositors", "text": "ID,Name,DOB\nD1,Ann Lee,1980-01-01\nD9,ann lee,1980-01-01\nD3,Bo,1990-02-02\n"})
    assert "Ann" not in str(pb._state(T, ws)["depositors"])
    pb.do(T, "settings", {"workspace": ws, "deposit": {"limit": 500000, "set_off": True, "source": "Deposit Insurance Act s.12"}})
    dp = pb.do(T, "deposit", {"workspace": ws})
    d1 = next(x for x in dp["depositors"] if x["depositor"] == "D1")
    assert d1["eligible"] == 1000000 and d1["covered"] == 500000 and dp["above_cover_total"] == 500000
    assert next(x for x in dp["depositors"] if x["depositor"] == "D3")["covered"] == 30000 and len(dp["records_to_fix"]) == 2
    # supervision
    pb.do(T, "upload", {"workspace": ws, "kind": "returns", "text": "Bank,Capital,RWA,NPL,Loans\nA,12,100,3,100\nB,9,100,12,100\n", "period_label": "2026 Q2"})
    assert pb.do(T, "supervision", {"workspace": ws})["need_thresholds"]
    pb.do(T, "settings", {"workspace": ws, "thresholds": {"car_min": 10.5, "npl_max": 10}})
    pb.do(T, "upload", {"workspace": ws, "kind": "returns", "text": "Bank,Capital,RWA,NPL,Loans\nA,13,100,3,100\nB,8,100,14,100\n", "period_label": "2026 Q3", "new_period": True})
    sv = pb.do(T, "supervision", {"workspace": ws})
    assert sv["in_breach"] == ["B"] and sv["previous_period"] == "2026 Q2" and next(x for x in sv["banks"] if x["bank"] == "A")["moves"]["car_points"] == 1
    # inspections
    pb.do(T, "upload", {"workspace": ws, "kind": "findings", "text": f"ID,Area,Owner,Due,Status\nF1,Credit risk,Ops,{D(-5)},open\nF2,AML,,{D(10)},open\nF3,IT,IT,{D(-2)},closed\n"})
    pb.do(T, "upload", {"workspace": ws, "kind": "earlier", "text": "ID,Area\nE1,credit risk\n"})
    ins = pb.do(T, "inspections", {"workspace": ws})
    assert ins["overdue"] == ["F1"] and ins["without_owner"] == ["F2"] and ins["repeat"] == ["F1"]
    f1 = next(x for x in ins["findings"] if x["id"] == "F1")
    pb.do(T, "close_finding", {"workspace": ws, "n": f1["n"]})
    assert pb.do(T, "inspections", {"workspace": ws})["overdue"] == []
    # a development project
    pb.do(T, "project", {"workspace": ws, "name": "Water", "donor": "Bank X", "tranches": "T1, 1000, baseline survey, yes\nT2, 2000, audit; report, yes",
                         "conditions_met": "baseline survey\nreport", "budget": "pipes, 1500\ntraining, 500", "indicators": "households connected, 1000, 640",
                         "eligible": "goods\nworks"})
    pb.do(T, "upload", {"workspace": ws, "kind": "spending", "project": "Water", "text": "ID,Line,Category,Amount\nS1,pipes,goods,1200\nS2,pipes,works,600\nS3,training,travel,100\n"})
    p = pb.do(T, "projects", {"workspace": ws})["projects"][0]
    assert p["released_before_conditions"] == ["T2"] and p["over_budget"] == ["pipes"] and p["ineligible"][0]["category"] == "travel"
    needs = " | ".join(x["say"] for x in pb.summary(T)["desk"]["needs"])
    assert "depositor record" in needs and "In breach" in needs and "released before" in needs


def test_roles_routes_downloads(pb, monkeypatch):
    from app.employee import hire
    from app.fin.desks import books_ent as E
    from app.main import app
    hire.hire(T, "public_finance", trust="seekh")
    ws = _desk(pb)
    for k, t in (("beneficiaries", BEN), ("payments", PAY), ("bank_return", RET)):
        pb.do(T, "upload", {"workspace": ws, "kind": k, "text": t})
    real = E.access
    monkeypatch.setattr(E, "access", lambda caller, w: {**real(T, w), "role": "viewer", "name": "Bo"} if caller == "bo" else real(caller, w))
    assert pb.do("bo", "g2p", {"workspace": ws})["approved"] == 4
    with pytest.raises(pb.PbDeskError, match="read this desk"):
        pb.do("bo", "settings", {"workspace": ws, "run_name": "x"})
    c = TestClient(app)
    assert c.get("/api/public/desk").json()["workspace"]["id"] == ws
    r = c.get(f"/api/public/download?workspace={ws}&what=g2p")
    assert r.status_code == 200 and "paid twice" in r.text and "4111111111111111" not in r.text
    assert c.post("/api/public/do/pay_now", json={"workspace": ws}).status_code in (400, 403)
    assert c.get("/api/public/chat").json()["id"]


@pytest.fixture
def pb_server(pb, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "public_finance", trust="seekh")
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


def test_desk_in_a_real_browser(pb, pb_server, tmp_path):
    base, browser, key = pb_server
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
    pg.goto(base + "/console/public")
    pg.wait_for_selector("text=Set up your public finance desk", timeout=20000)
    snap(pg, "pb-setup-1440")
    pg.fill("form[data-form=setup] [name=country]", "GB")
    pg.fill("form[data-form=setup] [name=currency]", "GBP")
    pg.click("form[data-form=setup] [type=submit]")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    ws = pb.summary(T)["workspace"]["id"]
    # casework
    go(pg, "#/cases", "text=Scheme rules")
    pg.click("text=Add a scheme")
    pg.fill("form[data-form=scheme] [name=name]", "Family help")
    pg.fill("form[data-form=scheme] [name=source]", "Social Security Act 2021, s.4")
    pg.fill("form[data-form=scheme] [name=tests]", "income <= 12000\nchildren >= 1\nresident == yes")
    pg.fill("form[data-form=scheme] [name=evidence]", "proof of income\nbirth certificate")
    pg.fill("form[data-form=scheme] [name=base]", "50")
    pg.fill("form[data-form=scheme] [name=per_field]", "children")
    pg.fill("form[data-form=scheme] [name=per_value]", "20")
    pg.click("form[data-form=scheme] [type=submit]")
    pg.wait_for_selector("form[data-form=case]", timeout=20000)
    pg.fill("form[data-form=case] [name=ref]", "C-1")
    pg.fill("form[data-form=case] [name=household]", "income, 9000\nchildren, 2\nresident, yes")
    pg.fill("form[data-form=case] [name=evidence_held]", "proof of income")
    pg.click("form[data-form=case] [type=submit]")
    pg.wait_for_selector(".pb-res.ok", timeout=20000)
    pg.fill("form[data-form=case] [name=ref]", "C-2")
    pg.fill("form[data-form=case] [name=household]", "income, 15000\nchildren, 1")
    pg.click("form[data-form=case] [type=submit]")
    pg.wait_for_selector(".pb-res.bad", timeout=20000)
    pg.click("summary:has-text('C-1')")
    pg.fill("details:has(summary:has-text('C-1')) form[data-form=decision] [name=decision]", "Awarded 90 a month")
    pg.click("details:has(summary:has-text('C-1')) form[data-form=decision] [type=submit]")
    pg.wait_for_selector(".pb-dec", timeout=20000)
    snap(pg, "pb-cases-1440")
    # overpayments
    go(pg, "#/overpay", "form[data-kind=due]")
    up(pg, "due", "d.csv", "Case,Period,Amount\nC-1,2026-01,90\nC-1,2026-02,90\n", "text=Cases checked")
    up(pg, "paid", "p.csv", "Case,Period,Amount\nC-1,2026-01,90\nC-1,2026-02,120\nC-2,2026-01,40\n", "text=Cases with a difference")
    snap(pg, "pb-overpay-1440")
    # payment run
    go(pg, "#/g2p", "form[data-kind=beneficiaries]")
    up(pg, "beneficiaries", "b.csv", BEN, "text=Approved")
    up(pg, "payments", "f.csv", PAY, "text=Paid twice")
    up(pg, "bank_return", "r.csv", RET, "text=Failed at the bank")
    assert "4111111111111111" not in pg.content()
    snap(pg, "pb-g2p-1440")
    # deposit cover
    go(pg, "#/deposit", "form[data-form=deposit]")
    pg.fill("form[data-form=deposit] [name=limit]", "500000")
    pg.select_option("form[data-form=deposit] [name=set_off]", "true")
    pg.click("form[data-form=deposit] [type=submit]")
    pg.wait_for_selector("text=Saved", timeout=20000)
    up(pg, "accounts", "a.csv", "Account,Holders,Balance\n111,D1,900000\n222,D1;D2,200000\n333,D3,50000\n444,,10\n", ".pb-cov")
    up(pg, "depositors", "dd.csv", "ID,Name,DOB\nD1,Ann Lee,1980-01-01\nD9,ann lee,1980-01-01\n", "text=one person under two IDs")
    snap(pg, "pb-deposit-1440")
    # settings + supervision
    go(pg, "#/settings", "form[data-form=thresholds]")
    pg.fill("form[data-form=thresholds] [name=car_min]", "10.5")
    pg.fill("form[data-form=thresholds] [name=npl_max]", "10")
    pg.click("form[data-form=thresholds] [type=submit]")
    pg.wait_for_selector("text=Saved", timeout=20000)
    snap(pg, "pb-settings-1440")
    go(pg, "#/supervision", "form[data-form=returns]")
    f = tmp_path / "ret.csv"
    f.write_text("Bank,Capital,RWA,NPL,Loans\nAlpha,12,100,3,100\nBeta,9,100,12,100\nGamma,15,100,4,100\nDelta,13,100,5,100\n")
    pg.fill("form[data-form=returns] [name=period_label]", "2026 Q3")
    pg.set_input_files("form[data-form=returns] input[type=file]", str(f))
    pg.wait_for_selector(".pb-car", timeout=20000)
    snap(pg, "pb-supervision-1440")
    # inspections
    go(pg, "#/inspections", "form[data-kind=findings]")
    up(pg, "findings", "fi.csv", f"ID,Area,Owner,Due,Status\nF1,Credit risk,Ops,{D(-5)},open\nF2,AML,,{D(10)},open\n", "text=Open, by owner")
    pg.click("[data-closef]")
    pg.wait_for_selector("text=Marked closed", timeout=20000)
    snap(pg, "pb-inspections-1440")
    # a project
    go(pg, "#/devfin", "form[data-form=project]")
    pg.fill("form[data-form=project] [name=name]", "Water")
    pg.fill("form[data-form=project] [name=tranches]", "T1, 1000, baseline survey, yes\nT2, 2000, audit; report, yes")
    pg.fill("form[data-form=project] [name=conditions_met]", "baseline survey\nreport")
    pg.fill("form[data-form=project] [name=budget]", "pipes, 1500\ntraining, 500")
    pg.fill("form[data-form=project] [name=indicators]", "households connected, 1000, 640")
    pg.fill("form[data-form=project] [name=eligible]", "goods\nworks")
    pg.click("form[data-form=project] [type=submit]")
    pg.wait_for_selector(".pb-bud", timeout=20000)
    up(pg, "spending", "s.csv", "ID,Project,Line,Category,Amount\nS1,Water,pipes,goods,1200\nS2,Water,pipes,works,600\nS3,Water,training,travel,100\n", "text=Outside the eligible")
    snap(pg, "pb-devfin-1440")
    go(pg, "#/today", ".cs-hero")
    pg.wait_for_selector(".iv-donut", timeout=20000)
    snap(pg, "pb-today-1440")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".iv-donut", "today"), ("#/cases", ".pb-scheme", "cases"), ("#/overpay", ".mk-bars", "overpay"),
                             ("#/g2p", ".pb-exs", "g2p"), ("#/deposit", ".pb-cov", "deposit"), ("#/supervision", ".pb-car", "supervision"),
                             ("#/inspections", ".mk-bars", "inspections"), ("#/devfin", ".pb-bud", "devfin"), ("#/settings", "form[data-form=thresholds]", "settings")):
        pg.goto(base + "/console/public" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"pb-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#pbPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
