"""v0.999.169 PAYROLL DESK: the Payroll employee's own section, built like Books & Accounts - its own chat (kind 'payroll') with the
desk block + the payroll tool in view; pay inputs that arrive by themselves and are checked in code (her people, the period, her
hours limit, never twice); the change list against the last run; approval on the hash she saw (a second person above her limit),
which locks the run and posts the wage journal to the books; Paid from the bank line; the payment file (account numbers never
kept); payslips in each person's language; a country starting list whose rules stay 'check this' until a person checks them; the
team roles; and the desk walked in a real browser."""
from __future__ import annotations

import base64
from datetime import date

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def pr(env):
    from app import payrollchat as PC
    PC._OF.clear()
    PC._BLOCK.clear()
    return PC


def _setup(name="Lumen Studio", cc="GB", cur="GBP", size="business"):
    from app.fin import profile as PR
    pv = PR.preview({"size": size, "countries": [cc], "currency": cur, "name": name, "wants": ["payroll"]})
    return PR.apply(T, pv["answers"], pv["hash"])["id"]


def _rules(ws):
    from app.fin.desks import payroll as PY
    PY.run(T, "settings", {"workspace": ws, "country": "GB", "frequency": "monthly", "source": "my accountant, 2026 rates",
                           "contributions": [{"name": "Pension", "employee_pct": 5, "employer_pct": 3, "base": "gross"}],
                           "income_tax": {"method": "flat", "flat_pct": 20},
                           "filings": [{"name": "Monthly return", "every": "monthly", "due_day": 22}]})


def test_hire_chat_block_and_wiring(pr):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert pr.summary(T)["hired"] is False
    hire.hire(T, "payroll_worldwide", trust="seekh")
    d = pr.summary(T)
    assert d["hired"] and d["workspace"] is None
    chat = pr.current(T)
    assert pr.is_payroll(chat["id"]) and pr.owns(T, chat["id"]) and pr.current(T)["id"] == chat["id"]
    assert "Set up your business" in pr.greeting(T)
    blk = pr.block(T)
    assert "<payroll_desk>" in blk and "never approve a payroll" in blk and "No business set up yet" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_prc.is_payroll(conversation_id)" in src and "adm.admit_families(_prc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["payroll_worldwide"] in pr.FAMILIES
    for f in ("callconv.py", "convs.py"):
        assert '"books", "payroll")' in (root / "server/app" / f).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/payroll")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "payrolldesk.js" in r.text
    html = (root / "server/app/static/console/payrolldesk.html").read_text()
    for f in ("chatkit.js", "seodesk.css", "booksdesk.css", "payrolldesk.css", "payrolldesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    assert "location.assign('/console/payroll')" in (root / "server/app/static/console/v2.js").read_text()
    assert "payroll_worldwide: 'payrolldesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/payroll'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()
    assert "payroll_desk_jobs" in (root / "server/app/worker.py").read_text()


def test_inputs_checked_changes_and_proration(pr):
    from app.employee import hire
    from app.fin.desks import payroll as PY
    from app.fin.desks import payroll_desk as PD
    hire.hire(T, "payroll_worldwide", trust="seekh")
    ws = _setup()
    _rules(ws)
    PY.run(T, "employee", {"workspace": ws, "name": "Meera Shah", "annual": 36000, "start": "2025-01-01"})
    PY.run(T, "employee", {"workspace": ws, "name": "Anil Kumar", "hourly": 15, "start": "2025-01-01"})
    r = PD.run(T, "prepare", ws, {"period": "2026-10"}, "me")
    assert r["status"] == "draft" and len(r["people"]) == 2
    PD.run(T, "approve", ws, {"period": "2026-10", "hash": r["hash"]}, "me")
    # November: a pay rise, a joiner on the 10th, timesheet rows - one good, one misspelt, one outside the period, one too many hours
    PY.run(T, "employee", {"workspace": ws, "name": "Meera Shah", "annual": 37440, "from": "2026-11-01"})
    PY.run(T, "employee", {"workspace": ws, "name": "Priya Rao", "annual": 36000, "start": "2026-11-10"})
    csv = ("Name,Hours,Overtime hours,Date\nAnil Kumar,150,6,\nA. Kumarr,4,,\nAnil Kumar,8,,2026-12-02\n"
           "Meera Shah,999,,\n").encode()
    got = PD.take_rows(T, ws, PD.rows_of_file("timesheet.csv", csv), "upload", "2026-11", "file1", "timesheet.csv")
    assert got["checked"] == 1 and got["waiting"] == 3
    again = PD.take_rows(T, ws, PD.rows_of_file("timesheet.csv", csv), "upload", "2026-11", "file1", "timesheet.csv")
    assert again["already"] == 4 and again["checked"] == 0
    items = PD.inputs(T, ws, "2026-11")["items"]
    why = {i["name"]: " ".join(i["why"]) for i in items if i["status"] == "waiting"}
    assert "did you mean Anil Kumar" in why["A. Kumarr"]
    assert any("outside 2026-11" in w for w in why.values()) and any("over your limit" in w for w in why.values())
    # the same hours again from another file are never counted twice
    dup = PD.take_rows(T, ws, [{"name": "Anil Kumar", "hours": 150}], "email", "2026-11", "mail1", "hours.xlsx")
    assert dup["waiting"] == 1
    assert "already has hours" in " ".join(next(i for i in PD.inputs(T, ws, "2026-11", "waiting")["items"] if i["file"] == "hours.xlsx")["why"])
    # she matches the misspelt row by hand; a one-off row of hours for Anil is then a second "hours" -> waits
    misspelt = next(i for i in items if i["name"] == "A. Kumarr")
    m = PD.match(T, ws, misspelt["id"], "anil-kumar")["input"]
    assert m["pid"] == "anil-kumar" and m["status"] == "waiting" and "already has hours" in " ".join(m["why"])
    PD.drop(T, ws, misspelt["id"])
    run = PD.run(T, "prepare", ws, {"period": "2026-11"}, "me")
    by = {p["name"]: p for p in run["people"]}
    assert by["Anil Kumar"]["gross"] == round(150 * 15 + 6 * 15 * 1.5, 2)
    assert by["Priya Rao"]["gross"] == round(3000 * 21 / 30, 2)                      # joined the 10th: 21 of 30 days
    ch = {c["name"]: c["why"] for c in run["changes"]}
    assert "new this period" in ch["Priya Rao"] and "joined 2026-11-10" in ch["Priya Rao"]
    assert any("pay changed from 36000.0 to 37440.0" in w for w in ch["Meera Shah"])
    assert "6 h overtime" in ch["Anil Kumar"]


def test_approval_journal_paid_pay_file_and_limit(pr):
    from app.employee import hire
    from app.fin import spine as SP
    from app.fin.desks import books as BK
    from app.fin.desks import payroll as PY
    from app.fin.desks import payroll_desk as PD
    hire.hire(T, "payroll_worldwide", trust="seekh")
    ws = _setup()
    _rules(ws)
    PY.run(T, "employee", {"workspace": ws, "name": "Meera Shah", "annual": 36000, "payee_ref": "MEERA S", "lang": "de",
                           "email": "meera@example.com"})
    PY.run(T, "employee", {"workspace": ws, "name": "Anil Kumar", "per_period": 2000})
    with pytest.raises(PY.PayrollError, match="approved payroll"):
        PD.run(T, "pay_file", ws, {"period": "2026-11"})
    r = PD.run(T, "prepare", ws, {"period": "2026-11"}, "Ravi <ravi@x>")
    with pytest.raises(PY.PayrollError, match="changed after you looked"):
        PD.run(T, "approve", ws, {"period": "2026-11", "hash": "nope"}, "me")
    PD.run(T, "desk_settings", ws, {"approve_limit": 1000}, "me")
    with pytest.raises(PY.PayrollError, match="someone other than"):
        PD.run(T, "approve", ws, {"period": "2026-11", "hash": r["hash"]}, "Ravi <ravi@x>")
    ok = PD.run(T, "approve", ws, {"period": "2026-11", "hash": r["hash"]}, "Owner <owner@x>")
    assert ok["status"] == "approved" and ok["journal_posted"] is True
    with pytest.raises(PY.PayrollError, match="never recalculated"):
        PD.run(T, "prepare", ws, {"period": "2026-11"}, "me")
    bal = BK.balances(T, ws)
    t = r["totals"]
    assert bal["6300"] == round(t["gross"] * 100) and bal["2210"] == -round(t["net"] * 100)
    csvf = PD.run(T, "pay_file", ws, {"period": "2026-11"})
    assert "MEERA S" in csvf["text"] and "iban" not in csvf["text"].lower()
    with pytest.raises(PY.PayrollError, match="IBAN"):
        PD.run(T, "pay_file", ws, {"period": "2026-11", "format": "pain001", "from": {"iban": "GB33BUKB20201555555555"}})
    x = PD.run(T, "pay_file", ws, {"period": "2026-11", "format": "pain001", "from": {"iban": "GB33BUKB20201555555555"},
                                   "accounts": {"meera-shah": {"iban": "GB94BARC10201530093459"}, "anil-kumar": {"iban": "GB29NWBK60161331926819"}}})
    assert "<Cd>SALA</Cd>" in x["text"] and "GB94BARC10201530093459" in x["text"]
    assert "GB94BARC" not in str(PD._c(T, ws))                                       # never kept
    # Paid only when the bank line arrives
    assert PD.paid_check(T, ws, "2026-11")["runs"][0]["paid"] is False
    SP.import_rows(T, ws, [{"day": date.today().isoformat(), "amount": -t["net"], "narration": "Salaries November"}],
                   "Main account", "GBP", "test", "b1", "me")
    assert PD.paid_check(T, ws, "2026-11")["runs"][0]["paid"] is True
    assert PD._flow(PD._c(T, ws), "2026-11")["status"] == "paid"
    name, pdf, to = PD.payslip_pdf(T, ws, "2026-11", "meera-shah")
    assert pdf.startswith(b"%PDF") and to == "meera@example.com" and name.endswith(".pdf")


def test_starting_list_rules_must_be_checked(pr):
    from app.employee import hire
    from app.fin import pack as P
    from app.fin.desks import payroll as PY
    from app.fin.desks import payroll_desk as PD
    hire.hire(T, "payroll_worldwide", trust="seekh")
    for cc in ("IN", "GB", "US", "SG", "AU", "AE"):
        sl = PD.starting_list(cc)
        assert sl["list"] and sl["where"] and "check this" in sl["says"]
        import json
        assert P.validate(json.load(open(P.__file__.rsplit("/", 1)[0] + f"/packs/{cc}.json"))) == []
    assert PD.starting_list("DE")["list"] is None
    india = PD.starting_list("IN")["list"]
    assert [c["name"] for c in india["contributions"]][:2] == ["Provident Fund (EPF)", "Employees' State Insurance (ESI)"]
    ws = _setup(cc="IN", cur="INR")
    PY.run(T, "employee", {"workspace": ws, "name": "Sita", "per_period": 18000})
    PY.run(T, "employee", {"workspace": ws, "name": "Ravi", "per_period": 30000})
    out = PD.run(T, "apply_starting_list", ws, {"country": "IN"}, "me")
    assert out["rules"] == 4
    with pytest.raises(PY.PayrollError, match="nobody has checked"):
        PD.run(T, "prepare", ws, {"period": "2026-11"}, "me")
    for r in PD.rules(T, ws)["rules"]:
        assert r["status"] == "check"
        left = PD.check_rule(T, ws, {"key": r["key"], "source": "https://www.epfindia.gov.in rates page"}, "Owner <o@x>")["left"]
    assert left == 0
    run = PD.run(T, "prepare", ws, {"period": "2026-11"}, "me")
    by = {p["name"]: {c["name"]: c for c in p["contributions"]} for p in run["people"]}
    assert by["Sita"]["Employees' State Insurance (ESI)"]["employee"] == 135.0          # 0.75% of 18,000
    assert by["Ravi"]["Employees' State Insurance (ESI)"]["employee"] == 0              # above 21,000: not due
    assert by["Ravi"]["Provident Fund (EPF)"]["employee"] == 1800.0                    # 12% of the 15,000 ceiling
    assert all(r["status"] == "checked" and r["by"] for r in PD.rules(T, ws)["rules"])


def test_roles_and_routes(pr):
    from app.employee import hire
    from app.fin.desks import payroll_desk as PD
    from app.main import app
    assert PD.allowed("accountant", "prepare") and not PD.allowed("accountant", "approve")
    assert PD.allowed("approver", "approve") and not PD.allowed("approver", "employee")
    assert not PD.allowed("viewer", "payslip_pdf") and PD.allowed("auditor", "desk") and PD.allowed("owner", "approve")
    c = TestClient(app)
    assert c.get("/api/payroll/desk").json()["hired"] is False
    hire.hire(T, "payroll_worldwide", trust="seekh")
    ws = _setup()
    _rules(ws)
    d = c.get("/api/payroll/desk").json()
    assert d["workspace"]["id"] == ws and d["desk"]["rules_set"] is True and d["role"] == "owner"
    assert c.put("/api/payroll/workspace", json={"workspace": "nope"}).status_code == 400
    r = c.post("/api/payroll/do/employee", json={"workspace": ws, "name": "Meera Shah", "annual": 36000, "hours": 0})
    assert r.status_code == 200, r.text
    up = c.post("/api/payroll/do/upload", json={"workspace": ws, "name": "t.csv",
                                                "data_b64": base64.b64encode(b"Name,Bonus\nMeera Shah,500\n").decode()})
    assert up.status_code == 200 and up.json()["checked"] == 1
    assert c.post("/api/payroll/in", json={"rows": []}).status_code == 401
    key = c.post("/api/payroll/do/api_key", json={"workspace": ws}).json()["key"]
    r = c.post("/api/payroll/in", headers={"Authorization": f"Bearer {key}"}, json={"rows": [{"name": "Meera Shah", "commission": 50}]})
    assert r.status_code == 200 and r.json()["checked"] == 1
    p = c.post("/api/payroll/do/prepare", json={"workspace": ws}).json()
    per = p["period"]
    gross = p["people"][0]["gross"]
    assert gross == 3000 + 500 + 50
    assert c.get(f"/api/payroll/payslip?workspace={ws}&period={per}&employee=meera-shah").content.startswith(b"%PDF")
    chat = c.get("/api/payroll/chat").json()["id"]
    assert c.get(f"/api/payroll/chat/{chat}/ok").json() == {"ok": True}
    assert c.post("/api/payroll/do/approve", json={"workspace": ws, "period": per, "hash": p["hash"],
                                                   }).status_code == 200


@pytest.fixture
def pr_server(pr, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "payroll_worldwide", trust="seekh")
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


def test_payroll_desk_in_a_real_browser(pr_server, tmp_path):
    import os
    base, browser, key = pr_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors = []
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/payroll")
        if vp["width"] == 1440:
            pg.wait_for_selector("form[data-form=setup]", timeout=20000)
            pg.fill("#pfSN", "Lumen Studio")
            pg.fill("#pfSC", "GB")
            pg.fill("#pfSK", "GBP")
            pg.click("form[data-form=setup] button[type=submit]")
            pg.click("[data-setupok]", timeout=15000)
            pg.wait_for_selector("[data-startlist=GB]", timeout=20000)
            pg.click("[data-startlist=GB]")
            pg.wait_for_selector("form[data-form=check]", timeout=20000)
            while pg.locator("form[data-form=check]").count():
                f = pg.locator("form[data-form=check]").first
                f.locator("input").fill("https://www.gov.uk/guidance/rates-and-thresholds-for-employers")
                n = pg.locator("form[data-form=check]").count()
                f.locator("button").click()
                pg.wait_for_function(f"() => document.querySelectorAll('form[data-form=check]').length < {n} && document.querySelector('#mdPage').innerText.includes('Country rules')", timeout=20000)
            pg.goto(base + "/console/payroll#/people")
            pg.wait_for_selector("form[data-form=person]", timeout=20000)
            pg.fill("#ppN", "Meera Shah")
            pg.fill("#ppA", "36000")
            pg.click("form[data-form=person] button[type=submit]")
            pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Meera Shah')", timeout=20000)
            pg.goto(base + "/console/payroll#/inputs")
            up = tmp_path / "hours.csv"
            up.write_text("Name,Bonus\nMeera Shah,250\nNobody Here,10\n")
            pg.wait_for_selector("#inUp", timeout=20000)
            pg.set_input_files("#inUp", str(up))
            pg.click("form[data-form=upload] button[type=submit]")
            pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Nobody Here')", timeout=20000)
            assert "no one called Nobody Here" in pg.inner_text("#mdPage")
            pg.goto(base + "/console/payroll#/run")
            pg.click("[data-prepare]", timeout=20000)
            pg.wait_for_selector("[data-approve]", timeout=20000)
            assert "bonus 250" in pg.inner_text("#mdPage")
            if shots:
                pg.screenshot(path=os.path.join(shots, "payroll_run.png"), full_page=True)
            pg.click("[data-approve]")
            pg.wait_for_selector("[data-csv]", timeout=20000)
            assert "Approved" in pg.inner_text("#mdPage")
            pg.goto(base + "/console/payroll#/today")
            pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Pay period')", timeout=20000)
        else:
            pg.wait_for_function("() => document.querySelector('#mdPage') && document.querySelector('#mdPage').innerText.includes('Pay period')", timeout=20000)
            wide = pg.evaluate("() => document.documentElement.scrollWidth")
            assert wide <= 392, wide
        if shots:
            pg.screenshot(path=os.path.join(shots, f"payroll_today_{vp['width']}.png"), full_page=True)
        ctx.close()
    assert not errors, errors
