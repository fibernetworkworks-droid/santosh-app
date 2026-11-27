"""INSURANCE AGENT DESK: the Insurance Agent Assistant's own section, built like the other finance desks - its own chat (kind
'insurance') with the desk block + the insurance tools in view; the insurer's renewal list read into the book; renewals with grace and
revival dates and message drafts she sends; cover gaps per customer; quotes compared and kept as the advice record, reaching the
customer only after her yes; claims with document ticks and the settlement clock; commission checked against the insurer's statement;
GLOBAL country packs (India checked, others 'check this' and never used until she confirms); the downloads; and the desk walked in a
real browser."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"
D = lambda n: (date.today() + timedelta(days=n)).isoformat()      # noqa: E731
LIST = ("Customer Name,Mobile,Policy No,Plan,Premium,Mode,Due Date,Sum Assured,Nominee\n"
        f"Ravi Kumar,9876543210,P-1001,Term Shield,12000,yearly,{D(5)},5000000,Sita\n"
        f"Meena Shah,9822001122,P-1002,Family Health,18000,yearly,{D(-10)},500000,\n"
        f"Arun Das,9811122233,P-1003,Endowment Plus,24000,yearly,{D(-60)},1000000,Rita\n")
STMT = "Policy No,Month,Commission\nP-1001,{m},1200\nP-1009,{m},300\n"


@pytest.fixture
def ins(env):
    from app import inschat as IN
    from app.insure import service as S
    IN._OF.clear()
    IN._BLOCK.clear()
    S._CR.clear()
    return IN


def _hire():
    from app.employee import hire
    hire.hire(T, "insurance_agent", trust="seekh")


def test_hire_setup_chat_block_and_wiring(ins):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert ins.summary(T)["hired"] is False
    assert "Hire me from AI Employees" in ins.greeting(T)
    _hire()
    d = ins.summary(T)
    assert d["hired"] and not d["set_up"] and "pays the insurer directly" in d["foot"] and d["packs"]["IN"] == "India"
    assert "Tell the desk your name" in ins.greeting(T) and "not set up yet" in ins.block(T)
    ins.setup(T, {"name": "Asha Rao", "country": "GB", "currency": "GBP"})
    d = ins.summary(T)
    assert d["set_up"] and d["desk"]["country"] == "GB" and d["desk"]["currency"] == "GBP"
    assert d["desk"]["pack"]["ombudsman"] == "Financial Ombudsman Service" and not d["desk"]["pack"]["checked"]
    chat = ins.current(T)
    assert ins.is_insurance(chat["id"]) and ins.owns(T, chat["id"])
    ins.forget(T)
    b = ins.block(T)
    assert "<insurance_desk>" in b and "check this" in b and "customer pays the insurer directly" in b
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_insc.is_insurance(conversation_id)" in src and "adm.admit_families(_insc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["bima"] in ins.FAMILIES and FAMILY_OF["bima_dekho"] in ins.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"insurance")' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/insurance")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "insdesk.js" in r.text
    html = (root / "server/app/static/console/insdesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "rkdesk.css", "insdesk.css", "insdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/insurance')" in (root / "server/app/static/console/v2.js").read_text()
    assert "insurance_agent: 'insdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/insurance'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_india_book_renewals_needs_quotes_commission(ins):
    _hire()
    ins.setup(T, {"name": "Asha Rao", "country": "IN", "currency": "INR"})
    r = ins.do(T, "import", {"text": LIST, "name": "renewals.csv", "insurer": "LIC"})
    assert r["added"] == 3
    k = ins.today_view(T)
    st = {p["number"]: p["premium_state"]["state"] for p in k["policies"]}
    assert st == {"P-1001": "due", "P-1002": "grace", "P-1003": "lapsed"}          # India: 30 days grace, 5 years revival
    lap = next(p for p in k["policies"] if p["number"] == "P-1003")
    assert lap["premium_state"]["revive_by"]
    d = {x["policy_id"]: x for x in k["renewals"]["drafts"]}
    assert len(d) == 3 and all(x["wa"].startswith("https://wa.me/") for x in d.values())
    says = " ".join(n["say"] for n in k["needs"])
    assert "grace period" in says and "can still be revived" in says and "no nominee" in says
    meena = next(c for c in k["clients"] if c["name"] == "Meena Shah")
    ins.do(T, "client", {"client": meena["id"], "income": 1200000, "whatsapp_ok": False,
                         "family": [{"name": "Raj", "relation": "spouse"}, {"name": "Tia", "relation": "daughter"}]})
    nd = ins.do(T, "needs", {"client": meena["id"]})
    assert nd["life"]["gap"] > 0 and nd["health"]["need"] > 0
    k = ins.today_view(T)
    assert not any(x["client"] == "Meena Shah" for x in k["renewals"]["drafts"])       # she said no messages
    xs = next(x for x in k["cross_sell"] if x["client"] == "Meena Shah")
    assert "No term life cover" in xs["gaps"] and "A policy with no nominee" in xs["gaps"]
    # quotes: kept as the advice record; the message only after her yes, and she sends it
    rec = ins.do(T, "recommend", {"client": meena["id"], "options": [
        {"insurer": "A Life", "plan": "Term A", "type": "term", "premium": 9000, "cover": 10000000, "csr": 98},
        {"insurer": "B Life", "plan": "Term B", "type": "term", "premium": 8000, "cover": 5000000}]})
    assert rec["options"][0]["insurer"] == "A Life"                                   # cheapest per lakh of cover first
    assert ins.today_view(T)["counts"]["advice_ready"] == 1
    msg = ins.do(T, "advice_message", {"advice_id": rec["advice_id"]})
    assert "free-look" in msg["draft"] and "30 days" in msg["draft"] and msg["wa"]
    # paid -> commission: expected vs the insurer's statement
    ravi = next(p for p in k["policies"] if p["number"] == "P-1001")
    ins.do(T, "policy", {"policy": ravi["id"], "commission_pct": 15})
    ins.do(T, "paid", {"policy": ravi["id"], "paid_on": D(0)})
    m = D(0)[:7]
    ins.do(T, "commission", {"text": STMT.format(m=m).replace("1200", "1500"), "name": "lic.csv"})
    c = ins.today_view(T)["commission"]
    row = next(x for x in c["rows"] if x["number"] == "P-1001")
    assert row["expected"] == 1800 and row["received"] == 1500 and row["state"] == "short"
    assert c["short"] == 1 and c["extra"][0]["number"] == "P-1009"
    ins.do(T, "commission", {"text": STMT.format(m=m).replace("1200", "1800")})
    assert ins.today_view(T)["commission"]["rows"][0]["state"] == "ok"                # same policy + month replaces
    cal = ins.today_view(T)["calendar"]
    assert len(cal) == 12 and sum(x["count"] for x in cal) >= 1


def test_other_country_rules_are_never_assumed(ins):
    _hire()
    ins.setup(T, {"name": "Jo", "country": "GB", "currency": "GBP"})
    ins.do(T, "import", {"text": LIST, "insurer": "Aviva"})
    k = ins.today_view(T)
    st = {p["number"]: p["premium_state"]["state"] for p in k["policies"]}
    assert st["P-1002"] == "overdue" and st["P-1003"] == "overdue"                    # no grace known: nothing assumed
    assert k["rules"]["grace_other_days"]["source"] == "check this" and k["rules"]["grace_other_days"]["value"] is None
    assert any("set your country's grace period" in n["say"] for n in k["needs"])
    assert all(p["gst_pct"] is None for p in k["policies"])
    s = ins.summary(T)
    import json
    assert "₹" not in json.dumps(s, ensure_ascii=False) and "lakh" not in json.dumps(s["desk"]["renewals"])
    meena = next(c for c in k["clients"] if c["name"] == "Meena Shah")
    nd = ins.do(T, "needs", {"client": meena["id"]})
    assert nd["health"] is None and any("rule of thumb" in g for g in nd["gaps"])
    # she confirms the suggested grace (one tap) and types a revival period from the policy
    ins.do(T, "settings", {"rules": {"grace_other_days": 30, "revival_years": 2, "reimbursement_days": 20}})
    k = ins.today_view(T)
    st = {p["number"]: p["premium_state"]["state"] for p in k["policies"]}
    assert st == {"P-1001": "due", "P-1002": "grace", "P-1003": "lapsed"} and k["rules"]["grace_other_days"]["source"] == "yours"
    ins.do(T, "settings", {"rules": {"health_base": 400000, "health_member": 50000}})
    assert ins.do(T, "needs", {"client": meena["id"]})["health"]["need"] == 400000
    # a claim's clock runs only on her settlement time
    p = next(p for p in k["policies"] if p["number"] == "P-1001")
    cl = ins.do(T, "claim", {"policy": p["id"], "kind": "health_reimbursement", "event_on": D(-40)})
    ins.do(T, "claim_update", {"claim_id": cl["claim_id"], "filed_on": D(-25), "have": ["Claim form", "Discharge summary"]})
    c = next(x for x in ins.today_view(T)["claims"] if x["id"] == cl["claim_id"])
    assert c["limit_days"] == 20 and c["overdue"] and "Financial Ombudsman Service" in c["escalate"]
    assert "Claim form" not in c["missing"] and c["missing"]
    with pytest.raises(ValueError):
        ins.do(T, "settings", {"rules": {"grace_other_days": "soon"}})


def test_routes_downloads_and_guards(ins):
    from app.main import app
    c = TestClient(app)
    assert c.post("/api/insdesk/do/client", json={"name": "X"}).status_code == 403          # not hired
    _hire()
    assert c.post("/api/insdesk/setup", json={"country": "Britain"}).status_code == 400
    assert c.post("/api/insdesk/setup", json={"name": "Asha", "country": "IN", "currency": "INR"}).status_code == 200
    assert c.get("/api/insdesk/desk").json()["set_up"]
    assert c.post("/api/insdesk/do/import", json={"text": LIST}).json()["added"] == 3
    for what, word in (("book", "P-1001"), ("renewals", "P-1002"), ("cross_sell", "No health cover"), ):
        r = c.get(f"/api/insdesk/download?what={what}")
        assert r.status_code == 200 and word in r.text, what
    assert c.get("/api/insdesk/download?what=claims").status_code == 400                     # no claims yet: said, not empty
    assert c.post("/api/insdesk/do/pay_premium", json={}).status_code == 400
    assert c.post("/api/insdesk/do/client", json={"name": "Y", "notes": "x", "otp": "123456"}).status_code == 403
    assert c.post("/api/insdesk/do/policy", json={"client": "Ravi Kumar", "insurer": "L", "number": "P-9", "pay_link": "http://x"}).status_code == 400
    assert c.get("/api/insdesk/chat").json()["id"]


@pytest.fixture
def ins_server(ins, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
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


def test_desk_in_a_real_browser(ins, ins_server, tmp_path):
    base, browser, key = ins_server
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

    def fill(pg, form, vals, extra=""):
        for n, v in vals:
            sel = f"form[data-form={form}]{extra} [name={n}]"
            if pg.eval_on_selector(sel, "e => e.tagName") == "SELECT":
                pg.select_option(sel, v)
            else:
                pg.fill(sel, v)
        pg.click(f"form[data-form={form}]{extra} [type=submit]")

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/insurance")
    pg.wait_for_selector("text=Set up your insurance desk", timeout=20000)
    snap(pg, "in-setup-1440")
    fill(pg, "setup", (("name", "Asha Rao"), ("country", "IN"), ("currency", "INR")))
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # renewals: the insurer's list
    go(pg, "#/renewals", "form[data-kind=import]")
    up(pg, "import", "renewals.csv", LIST, "text=Meena Shah")
    pg.wait_for_selector("a[href^='https://wa.me/']", timeout=20000)
    snap(pg, "in-renewals-1440")
    pg.click("[data-paid]")
    pg.wait_for_selector(".toast:not([hidden])", timeout=20000)
    # a customer: details, family, needs, a policy
    go(pg, "#/clients", "form[data-form=client]")
    fill(pg, "client", (("name", "Kiran Rao"), ("phone", "+91 98200 11111"), ("income", "900000")), ":not([data-id])")
    pg.wait_for_selector("text=Cover they need", timeout=20000)
    pg.wait_for_selector(".fo-rats", timeout=20000)
    fill(pg, "family", (("name", "Lata"),), "")
    pg.wait_for_selector("text=Lata", timeout=20000)
    pg.fill("#inC5", "500000")                       # half-typed while the policy saves ...
    pg.click(".ins-more summary") if pg.locator("details.ins-more:not([open]) summary").count() else None
    fill(pg, "policy", (("insurer", "Star"), ("plan", "Health Plus"), ("type", "health"), ("number", "H-77"), ("premium", "15000"),
                        ("cover", "500000"), ("nominee", "Lata"), ("commission_pct", "15")))
    pg.wait_for_selector("text=H-77", timeout=20000)
    assert pg.input_value("#inC5") == "500000"       # ... stays
    snap(pg, "in-client-1440")
    # cover & quotes
    go(pg, "#/sales", "form[data-form=quote]")
    fill(pg, "quote", (("insurer1", "A Life"), ("plan1", "Term A"), ("type1", "term"), ("premium1", "9000"), ("cover1", "10000000"), ("csr1", "98"),
                       ("insurer2", "B Life"), ("plan2", "Term B"), ("type2", "term"), ("premium2", "8000"), ("cover2", "5000000")))
    pg.wait_for_selector("[data-approve]", timeout=20000)
    pg.click("[data-approve]")
    pg.wait_for_selector("text=Open in WhatsApp", timeout=20000)
    fill(pg, "checklist", (("type", "term"), ("age", "48")))
    pg.wait_for_selector("text=medical test", timeout=20000)
    snap(pg, "in-sales-1440")
    # claims
    go(pg, "#/claims", "form[data-form=claim]")
    fill(pg, "claim", (("kind", "health_reimbursement"), ("amount", "60000")))
    pg.wait_for_selector("[data-tick]", timeout=20000)
    pg.click("[data-tick]")
    pg.wait_for_timeout(600)
    snap(pg, "in-claims-1440")
    # commission
    go(pg, "#/commission", "form[data-kind=commission]")
    up(pg, "commission", "stmt.csv", STMT.format(m=D(0)[:7]), "text=for premiums not recorded as paid")
    snap(pg, "in-commission-1440")
    # settings: another country's rules are 'check this'
    go(pg, "#/settings", "form[data-form=country]")
    fill(pg, "country", (("country", "SG"), ("currency", "SGD")))
    pg.wait_for_selector("[data-use]", timeout=20000)
    pg.click("[data-use]")
    pg.wait_for_selector("text=Yours", timeout=20000)
    snap(pg, "in-settings-1440")
    go(pg, "#/today", ".cs-hero")
    pg.wait_for_selector(".iv-donut", timeout=20000)
    snap(pg, "in-today-1440")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".iv-donut", "today"), ("#/clients", "table.tb", "clients"), ("#/renewals", "form[data-kind=import]", "renewals"),
                             ("#/sales", "form[data-form=quote]", "sales"), ("#/claims", ".pb-res", "claims"),
                             ("#/commission", "form[data-kind=commission]", "commission"), ("#/settings", "form[data-form=rules]", "settings")):
        pg.goto(base + "/console/insurance" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"in-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#inPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
