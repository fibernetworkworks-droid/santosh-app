"""v0.999.171 PAYROLL FOR EVERY SIZE: the size page (very small .. big) with its approval chain; people linked from Excel (salary
breakup columns become their own pay parts), from a PDF read by AI (every line confirmed before it is used) and from her sheet;
attendance machine punches -> days present, hours, late days; past pay -> history; pay as building blocks (formulas worked out by
plain code, refused when they name an unknown word); the same-as-before test against a month she paid (to the cent) gating the
first preview; the preview report with its flags, breakdowns and cash needed, told in the Payroll chat; check -> approve by
different people for big sizes; the India bulk bank file; the trend and the group view; and the desk walked in a real browser."""
from __future__ import annotations

import base64
import io

import pytest

T = "default"


@pytest.fixture
def pr(env):
    from app import payrollchat as PC
    PC._OF.clear()
    PC._BLOCK.clear()
    return PC


def _ws(name="Sharma Traders", cc="IN", cur="INR"):
    from app.fin import profile as PR
    pv = PR.preview({"size": "business", "countries": [cc], "currency": cur, "name": name, "wants": ["payroll"]})
    return PR.apply(T, pv["answers"], pv["hash"])["id"]


def _rules(ws):
    from app.fin.desks import payroll as PY
    PY.run(T, "settings", {"workspace": ws, "country": "IN", "frequency": "monthly", "source": "my accountant, 2026 rates",
                           "contributions": [{"name": "PF", "employee_pct": 12, "employer_pct": 12, "upto": 15000}],
                           "income_tax": {"method": "none"}})


def _csv(rows):
    return base64.b64encode("\n".join(",".join(str(x) for x in r) for r in rows).encode()).decode()


def _xlsx(rows):
    import openpyxl
    wb = openpyxl.Workbook()
    for r in rows:
        wb.active.append(r)
    b = io.BytesIO()
    wb.save(b)
    return base64.b64encode(b.getvalue()).decode()


def test_formula_engine_is_safe_and_exact():
    from app.fin.desks import payroll_formula as FX
    from decimal import Decimal
    assert FX.evaluate("0.1 + 0.2", {}) == Decimal("0.3")
    assert FX.evaluate("overtime_hours * (basic / 208) * 1.5", {"overtime_hours": 10, "basic": 20800}) == Decimal("1500")
    assert FX.evaluate("late_days >= 3 ? 0.5 * day_pay : 0", {"late_days": 4, "day_pay": 1000}) == Decimal("500")
    assert FX.evaluate("late_days >= 3 ? 0.5 * day_pay : 0", {"late_days": 1, "day_pay": 1000}) == 0
    assert FX.evaluate("min(advance_left, 2000)", {"advance_left": 5000}) == 2000
    assert FX.evaluate("round(10 / 3, 2)", {}) == Decimal("3.33")
    notes = []
    assert FX.evaluate("5 / 0", {}, notes) == 0 and notes
    for bad in ("__import__('os')", "basic.real", "open('x')", "[1][0]", "'text'", "lambda: 1", "exec('1')"):
        with pytest.raises(FX.FormulaError):
            FX.evaluate(bad, {"basic": 1})
    assert FX.check("basic * hra_pct", {"basic"}) == ["hra_pct"]


def test_size_page_steps_and_chain(pr):
    from app.employee import hire
    from app.fin.desks import payroll_desk as PD
    hire.hire(T, "payroll_worldwide", trust="seekh")
    ws = _ws()
    d = PD.desk(T, ws)
    assert d["size"] == "" and set(d["sizes"]) == {"very_small", "small", "medium", "large", "big"}
    assert d["sizes"]["big"]["range"] == "5,000+ people" and d["sizes"]["very_small"]["range"] == "1 – 10 people"
    with pytest.raises(PD.PayrollError):
        PD.run(T, "setup_size", ws, {"size": "huge"})
    r = PD.run(T, "setup_size", ws, {"size": "large", "countries": ["IN"], "frequency": "monthly", "attendance": "machine"})
    assert r["info"]["chain"] == ["check", "approve"] and "checked" in r["says"]
    d = PD.desk(T, ws)
    assert d["size"] == "large" and d["chain"] == ["check", "approve"]
    steps = {s["key"]: s for s in d["steps"]}
    assert steps["size"]["done"] and not steps["people"]["done"] and steps["people"]["now"]
    src = PD.run(T, "sources", ws, {})
    assert [s["key"] for s in src["people"]][:2] == ["hr_system", "payroll_app"]
    names = {p["name"] for s in src["people"] for p in s.get("programs") or []}
    assert {"SAP SuccessFactors", "Workday", "RazorpayX Payroll", "Keka"} <= names
    assert all(p["state"] in ("connected", "can_connect", "not_offered", "off") for s in src["people"] for p in s.get("programs") or [])


def test_people_excel_breakup_and_pdf_confirm(pr, monkeypatch):
    from app.employee import hire
    from app.fin.desks import payroll as PY
    from app.fin.desks import payroll_desk as PD
    from app.fin.desks import payroll_flow as PF
    hire.hire(T, "payroll_worldwide", trust="seekh")
    ws = _ws()
    PD.run(T, "setup_size", ws, {"size": "small"})
    data = _xlsx([["Emp Code", "Employee Name", "Basic", "HRA", "Special Allowance", "Canteen", "PF", "Gross", "Department", "DOJ", "Email"],
                  ["E1", "Ravi Patil", 15000, 6000, 4000, 500, 1800, 25000, "Stores", "2024-04-01", "ravi@x.in"],
                  ["E2", "Sunita Rao", 20000, 8000, 2000, 0, 2400, 30000, "Sales", "01/06/2025", "sunita@x.in"],
                  ["E3", "", 10000, 0, 0, 0, 0, 10000, "Sales", "", ""],
                  ["E4", "Amit Joshi", "abc", 0, 0, 0, 0, 0, "Stores", "", "ravi@x.in"]])
    r = PD.run(T, "people_file", ws, {"name": "staff.xlsx", "data_b64": data})
    assert r["count"] == 4 and r["ready"] == 2 and not r["ai"]
    rows = {x["line"]: x for x in r["rows"]}
    ravi = rows[2]
    assert ravi["pay_kind"] == "per_period" and ravi["pay"] == 15000 and ravi["start"] == "2024-04-01"
    assert {p["name"]: p["kind"] for p in ravi["parts"]} == {"HRA": "earning", "Special Allowance": "earning", "Canteen": "deduction"}
    assert "no name" in rows[4]["problems"] and any("not a number" in w for w in rows[5]["problems"])
    assert any("same email" in w for w in rows[5]["problems"])
    with pytest.raises(PD.PayrollError):
        PD.run(T, "import_apply", ws, {"import": r["import"], "hash": "wrong"})
    got = PD.run(T, "import_apply", ws, {"import": r["import"], "hash": r["hash"]})
    assert got["added"] == 2 and got["skipped"] == 2
    people = {p["name"]: p for p in PY.run(T, "people", {"workspace": ws})["employees"]}
    assert people["Ravi Patil"]["code"] == "E1" and people["Ravi Patil"]["department"] == "Stores" and len(people["Ravi Patil"]["parts"]) == 3
    # a PDF is read by AI and each line must be confirmed before it is used
    monkeypatch.setattr("app.fin.desks.books_feed.text_of", lambda n, d: ("Ravi Patil 16000 ...", "pdf"))
    monkeypatch.setattr(PF, "_ask_ai", lambda what, text: {"rows": [
        {"name": "Ravi Patil", "code": "E1", "pay": 16000, "pay_kind": "per_period"},
        {"name": "Kiran Das", "pay": 12000, "parts": [{"name": "PF", "kind": "deduction", "amount": 1440}, {"name": "Conveyance", "amount": 1600}]}]})
    r = PD.run(T, "people_file", ws, {"name": "register.pdf", "data_b64": base64.b64encode(b"%PDF").decode()})
    assert r["ai"] and r["source"] == "pdf" and r["rows"][0]["does"] == "update Ravi Patil"
    assert [p["name"] for p in r["rows"][1]["parts"]] == ["Conveyance"]           # statutory lines come from the country rules
    with pytest.raises(PD.PayrollError):
        PD.run(T, "import_apply", ws, {"import": r["import"], "hash": r["hash"]})
    got = PD.run(T, "import_apply", ws, {"import": r["import"], "hash": r["hash"], "lines": [1]})
    assert got == {"added": 0, "updated": 1, "months": 0, "skipped": 1, "says": got["says"]}
    ravi = next(p for p in PY.run(T, "people", {"workspace": ws})["employees"] if p["name"] == "Ravi Patil")
    assert ravi["pay"] == 16000 and ravi["pay_history"][-1]["was"] == 1500000


def test_parts_attendance_history_match_preview_and_chain(pr, monkeypatch):
    from app.employee import hire
    from app.fin.desks import books_ent as E
    from app.fin.desks import payroll as PY
    from app.fin.desks import payroll_desk as PD
    hire.hire(T, "payroll_worldwide", trust="seekh")
    ws = _ws()
    _rules(ws)
    PD.run(T, "setup_size", ws, {"size": "large"})
    PY.run(T, "employee", {"workspace": ws, "name": "Ravi Patil", "per_period": 15000, "start": "2024-01-01", "code": "E1",
                           "department": "Stores", "payee_ref": "RAVI-SBI", "email": "ravi@x.in"})
    PY.run(T, "employee", {"workspace": ws, "name": "Sunita Rao", "per_period": 20000, "start": "2024-01-01", "code": "E2",
                           "department": "Sales", "payee_ref": "SUNITA-HDFC"})
    # pay as building blocks
    with pytest.raises(PD.PayrollError) as e:
        PD.run(T, "part_save", ws, {"name": "Late cut", "kind": "deduction", "formula": "late_days >= 3 ? 0.5 * dayy_pay : 0"})
    assert "dayy_pay" in str(e.value)
    PD.run(T, "part_save", ws, {"name": "HRA", "kind": "earning", "formula": "basic * 0.4"})
    PD.run(T, "part_save", ws, {"name": "Late cut", "kind": "deduction", "formula": "late_days >= 3 ? round(0.5 * day_pay, 2) : 0"})
    PD.run(T, "part_save", ws, {"name": "Sales bonus", "kind": "earning", "formula": "sales * 0.02", "applies_to": "department:Sales"})
    PD.run(T, "policy_save", ws, {"days": "thirty", "shift_start": "09:30", "grace_min": 10, "jump_pct": 20})
    # attendance machine punches for 2026-10: Ravi late 3 times
    punches = [["Emp Code", "Name", "Date", "In Time", "Out Time"]]
    for d in range(1, 27):
        if d in (4, 11, 18, 25):
            continue
        punches.append(["E1", "Ravi", f"2026-10-{d:02d}", "09:55" if d in (2, 3, 5) else "09:20", "18:00"])
    r = PD.run(T, "attendance_file", ws, {"name": "machine.csv", "data_b64": _csv(punches)})
    assert r["checked"] == 1 and "2026-10" in r["periods"]
    PD.run(T, "input_rows", ws, {"period": "2026-10", "rows": [{"name": "Sunita Rao", "sales": 100000}]})
    ins = PD.inputs(T, ws, "2026-10")["items"]
    ravi_in = next(i for i in ins if i["person"] == "Ravi Patil")
    assert ravi_in["values"]["days_present"] == 22 and ravi_in["values"]["late_days"] == 3
    # past pay: September register -> history, then the same-as-before test gates the preview
    reg = [["Emp Code", "Name", "Month", "Gross", "Net", "HRA"], ["E1", "Ravi Patil", "Sep 2026", 21000, 19200, 6000],
           ["E2", "Sunita Rao", "Sep 2026", 28000, 26200, 8000]]
    h = PD.run(T, "history_file", ws, {"name": "sep.csv", "data_b64": _csv(reg)})
    assert h["ready"] == 2
    PD.run(T, "import_apply", ws, {"import": h["import"], "hash": h["hash"]})
    with pytest.raises(PD.PayrollError) as e:
        PD.run(T, "preview", ws, {"period": "2026-10"}, "Preparer <prep@x.in>")
    assert "same-as-before" in str(e.value)
    m = PD.run(T, "match_test", ws, {"period": "2026-09"})
    assert m["status"] == "matched" and m["same"] == 2, m
    # Ravi: 15000 + HRA 6000 - PF 1800 - late cut 250 ; Sunita: 20000 + HRA 8000 + 2000 sales bonus, PF on 15000 only
    told = []
    monkeypatch.setattr("app.fin.desks.payroll_flow._tell", lambda t, line: told.append(line))
    rep = PD.run(T, "preview", ws, {"period": "2026-10"}, "Preparer <prep@x.in>")
    ppl = {p["name"]: p for p in PY._cfg(PY._ws(T, ws))["runs"]["2026-10"]["people"]}
    assert ppl["Ravi Patil"]["gross"] == 21000 and ppl["Ravi Patil"]["net"] == 21000 - 1800 - 250
    assert ppl["Sunita Rao"]["gross"] == 30000 and ppl["Sunita Rao"]["net"] == 30000 - 1800
    assert {q["name"] for q in ppl["Sunita Rao"]["parts"]} == {"HRA", "Late cut", "Sales bonus"}
    assert rep["cash_needed"] == round(rep["totals"]["net"] + sum(rep["to_authorities"].values()), 2)
    assert {g["name"] for g in rep["by"]["department"]} == {"Stores", "Sales"} and told and "2026-10" in told[0]
    # a bank payee just changed -> flagged first
    PY.run(T, "employee", {"workspace": ws, "name": "Ravi Patil", "payee_ref": "RAVI-NEW-BANK"})
    rep = PD.run(T, "preview", ws, {"period": "2026-10", "tell": False}, "Preparer <prep@x.in>")
    assert any(f["what"] == "payee" and f["level"] == "bad" for f in rep["flags"])
    # large size: check before approve, a different person at each step once there is a team
    E.team_add(T, ws, "check@x.in", "approver", "Checker", "owner")
    with pytest.raises(PD.PayrollError) as e:
        PD.run(T, "approve", ws, {"period": "2026-10", "hash": rep["hash"]}, "Owner <owner@x.in>")
    assert "checked before" in str(e.value)
    with pytest.raises(PD.PayrollError):
        PD.run(T, "check_run", ws, {"period": "2026-10", "hash": rep["hash"]}, "Preparer <prep@x.in>")
    PD.run(T, "check_run", ws, {"period": "2026-10", "hash": rep["hash"]}, "Checker <check@x.in>")
    with pytest.raises(PD.PayrollError):
        PD.run(T, "approve", ws, {"period": "2026-10", "hash": rep["hash"]}, "Checker <check@x.in>")
    out = PD.run(T, "approve", ws, {"period": "2026-10", "hash": rep["hash"]}, "Owner <owner@x.in>")
    assert out["status"] == "approved"
    f = PD.run(T, "pay_file", ws, {"period": "2026-10", "format": "in_bulk", "accounts": {
        "ravi-patil": {"account": "12345678901", "ifsc": "SBIN0001234"}, "sunita-rao": {"account": "99887766554", "ifsc": "HDFC0000123"}}})
    assert f["text"].splitlines()[0] == "Beneficiary Name,Account Number,IFSC,Amount,Narration" and "SBIN0001234" in f["text"]
    assert "12345678901" not in str(PY._ws(T, ws)["settings"])                       # never kept
    with pytest.raises(PD.PayrollError):
        PD.run(T, "pay_file", ws, {"period": "2026-10", "format": "in_bulk", "accounts": {"ravi-patil": {"account": "12", "ifsc": "x"}}})
    name, pdf = __import__("app.fin.desks.payroll_flow", fromlist=["x"]).report_pdf(T, ws, "2026-10")
    assert pdf.startswith(b"%PDF") and name.endswith(".pdf")
    tr = PD.run(T, "history_report", ws, {})
    assert [m["period"] for m in tr["months"]] == ["2026-09", "2026-10"] and tr["months"][1]["from"] == "approved"
    g = PD.run(T, "group_view", ws, {})
    assert g["companies"][0]["status"] == "approved" and "INR" in g["totals"] and g["all_approved"]


def test_match_differs_then_accepted_and_roles(pr):
    from app.employee import hire
    from app.fin.desks import payroll as PY
    from app.fin.desks import payroll_desk as PD
    hire.hire(T, "payroll_worldwide", trust="seekh")
    ws = _ws()
    _rules(ws)
    PD.run(T, "setup_size", ws, {"size": "very_small"})
    PY.run(T, "employee", {"workspace": ws, "name": "Ravi Patil", "per_period": 15000, "start": "2024-01-01"})
    reg = [["Name", "Gross", "Net"], ["Ravi Patil", 15500, 13700]]
    h = PD.run(T, "history_file", ws, {"name": "aug.csv", "data_b64": _csv(reg), "period": "2026-08"})
    PD.run(T, "import_apply", ws, {"import": h["import"], "hash": h["hash"]})
    m = PD.run(T, "match_test", ws, {"period": "2026-08"})
    assert m["status"] == "differs" and m["rows"][0]["diffs"][0]["what"] == "gross" and m["rows"][0]["diffs"][0]["by"] == -500
    assert not PD.desk(T, ws)["match"]["ok"]
    with pytest.raises(PD.PayrollError):
        PD.run(T, "match_accept", ws, {"period": "2026-08", "reason": "ok"})
    PD.run(T, "match_accept", ws, {"period": "2026-08", "reason": "August had a one-off arrear of 500"})
    assert PD.desk(T, ws)["match"]["ok"]
    PD.run(T, "part_save", ws, {"name": "Washing", "kind": "earning", "formula": "200"})
    assert not PD.desk(T, ws)["match"]["ok"]                                       # rules changed -> test again
    assert PD.allowed("accountant", "preview") and PD.allowed("approver", "check_run") and not PD.allowed("accountant", "setup_size")
    assert not PD.allowed("viewer", "report_pdf") and PD.allowed("auditor", "report")


@pytest.fixture
def pz_server(pr, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
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


def test_desk_page_walk(pz_server, tmp_path):
    """The size page, the dashboard steps, People's ways in, Pay rules and the preview report - in a real browser."""
    import os
    from app.employee import hire
    from app.fin.desks import payroll as PY
    from app.fin.desks import payroll_desk as PD
    from app import payrollchat as PC
    base, browser, key = pz_server
    hire.hire(T, "payroll_worldwide", trust="seekh")
    ws = _ws()
    _rules(ws)
    PY.run(T, "employee", {"workspace": ws, "name": "Ravi Patil", "per_period": 15000, "start": "2024-01-01", "department": "Stores"})
    PC.pick(T, ws)
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []
    for w in (1440, 390):
        ctx = browser.new_context(viewport={"width": w, "height": 900})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "/console/payroll")
        if w == 1440:
            pg.wait_for_selector("text=How many people do you pay?", timeout=20000)
            if shots:
                pg.screenshot(path=os.path.join(shots, "payroll_size.png"))
            for n in ("very_small", "small", "medium", "large", "big"):
                assert pg.locator(f".pz-size[data-size={n}]").count() == 1
            assert "5,000+ people" in pg.inner_text("#mdPage")
            pg.click(".pz-size[data-size=medium]")
            pg.click("#pzGo")
            pg.wait_for_selector(".pz-steps", timeout=20000)
            assert PD.desk(T, ws)["size"] == "medium"
            if shots:
                pg.screenshot(path=os.path.join(shots, "payroll_dashboard.png"))
        else:
            pg.wait_for_selector(".pz-steps", timeout=20000)
        assert pg.locator("[data-preview]").count() >= 1
        pg.goto(base + "/console/payroll#/people")
        pg.wait_for_selector("text=Where are your people today?", timeout=20000)
        txt = pg.inner_text("#mdPage")
        assert "Excel or CSV" in txt and "HR system" in txt and "SAP SuccessFactors" in txt
        if w == 1440:
            up = tmp_path / "staff.csv"
            up.write_text("Emp Code,Name,Basic,HRA,Department\nE7,Neha Singh,18000,7200,Sales\nE8,,1000,0,Sales\n")
            pg.set_input_files("input[data-pfile=excel]", str(up))
            pg.wait_for_selector("[data-iapply]", timeout=20000)
            assert "no name" in pg.inner_text("#mdPage")
            if shots:
                pg.screenshot(path=os.path.join(shots, "payroll_people.png"))
            pg.click("[data-iapply]")
            pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Neha Singh') && !document.querySelector('[data-iapply]')", timeout=20000)
        pg.goto(base + "/console/payroll#/rules")
        pg.wait_for_selector("text=Pay parts", timeout=20000)
        if w == 1440:
            pg.fill("#ptN", "Washing allowance")
            pg.fill("#ptF", "days_presnt * 10")
            pg.click("form[data-form=part] button[type=submit]")
            pg.wait_for_selector("#toast:not([hidden])", timeout=10000)
            assert "days_presnt" in pg.inner_text("#toast")
            pg.fill("#ptF", "200")
            pg.click("form[data-form=part] button[type=submit]")
            pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Washing allowance') && !document.querySelector('#ptN').value", timeout=20000)
        pg.goto(base + "/console/payroll#/run")
        pg.wait_for_selector("text=Run the preview", timeout=20000)
        if w == 1440:
            pg.click("[data-preview]")
            pg.wait_for_selector("text=Look at these first", timeout=20000)
            assert "Cash needed" in pg.inner_text("#mdPage") and pg.locator("[data-approve]").count() == 1
            if shots:
                pg.screenshot(path=os.path.join(shots, "payroll_preview.png"), full_page=True)
        else:
            pg.wait_for_selector("text=Look at these first", timeout=20000)
        over = pg.evaluate("document.documentElement.scrollWidth - innerWidth")
        assert over <= 1, (w, over)
        if shots:
            pg.screenshot(path=os.path.join(shots, f"payroll_run_{w}.png"), full_page=True)
        ctx.close()
    assert not errs, errs
    runs = PY._cfg(PY._ws(T, ws))["runs"]
    key_ = sorted(runs)[-1]
    assert {p["name"] for p in runs[key_]["people"]} == {"Ravi Patil", "Neha Singh"}
    neha = next(p for p in runs[key_]["people"] if p["name"] == "Neha Singh")
    assert neha["gross"] == 18000 + 7200 + 200


def test_worker_timers_do_not_clash():
    """v0.999.169 named its payroll timer `_pr_last`, the same name as the CA practice job's timers - the practice slot then
    crashed on every tick ('float' object is not subscriptable). Each job keeps its own name now."""
    from app import worker as W
    assert isinstance(W._pr_last, dict) and {"mirror", "mail", "drop"} <= set(W._pr_last)
    assert isinstance(W._payroll_last, float)
