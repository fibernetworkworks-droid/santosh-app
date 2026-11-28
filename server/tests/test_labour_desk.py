"""LABOUR & WAGES DESK (Construction & Real Estate): a site labour desk for any construction company in any country. People and
their papers with a renewal radar; a per-person muster that is never edited (counter-rows), with the checks a person decides on
(two sites, one device marking many, the gate, lapsed papers, hours, after approval); wage working papers with overtime by HER
country's rule (India 2x, US 1.5x over 40 h, UK her contract), the floor check, advances under her cap, deductions from HER rows,
prepared -> checked -> approved on the hash, payment files, paid from her bank reference; levies on their bases and tax withheld
by status with the year's limits; subcontractor evidence with gaps named and nothing held by itself; the chat drafts, a person
posts; walked in a browser at 1440 and 390."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest

T = "default"


@pytest.fixture
def ld(env):
    from app.labourdesk import service as S
    from app.labourdesk.core import _READY
    _READY.clear()
    return S


def _d(n: int = 0) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def _setup(S, country="IN"):
    S.run(T, "save_settings", {"company": "Riverside Builders", "country": country, "region": "MH", "pay_cycle": "weekly", "day_hours": 8})
    S.run(T, "save_site", {"name": "Tower B", "project": "Riverside Towers", "planned": 30})
    S.run(T, "save_site", {"name": "Tower C"})
    S.run(T, "save_employer", {"name": "Kumar Steel Fixers", "status": "firm", "tax_id": "AAAPK1234K", "tax_id_ok": True, "checked_by": "Meera"})
    S.run(T, "save_worker", {"name": "Raju Kamble", "trade": "Mason", "gang": "Gang 5", "site": "Tower B", "id_number": "123456789012", "bank_account": "001122334455"})
    S.run(T, "save_worker", {"name": "Sunita Pawar", "trade": "Helper", "gang": "Gang 5", "site": "Tower B"})
    S.run(T, "save_worker", {"name": "Vinod Shinde", "trade": "Bar bender", "employer": "Kumar Steel Fixers", "site": "Tower B"})
    S.run(T, "save_rate", {"trade": "Mason", "rate": 900, "basis": "day", "wef": "2026-01-01", "source": "our rate card 2026"})
    S.run(T, "save_rate", {"trade": "Helper", "rate": 600, "basis": "day", "wef": "2026-01-01", "source": "our rate card 2026"})
    S.run(T, "save_rate", {"kind": "floor", "trade": "Mason", "rate": 750, "basis": "day", "wef": "2026-01-01",
                           "source": "Maharashtra minimum wages notification (skilled, zone I), Oct 2026"})


# ---------------------------------------------------------------- settings and the country packs
def test_settings_packs_and_global(ld):
    S = ld
    from app.labourdesk.core import LabourError
    from app.labourdesk import packs as P
    st = S.run(T, "save_settings", {"country": "IN"})
    assert st["currency"] == "INR" and st["ot"]["x"] == 2.0 and st["ot"]["basis"] == "day"
    assert "induction" in st["required"]
    assert P.ot("US")["basis"] == "week" and P.ot("US")["after"] == 40 and P.ot("US")["x"] == 1.5
    assert P.ot("GB")["basis"] == "contract" and P.ot("ZZ")["id"] == "gen-ot"
    assert any(r["id"] == "gb-cis" for r in P.pack("GB")["withholding"]) and not P.pack("IN")["levies"][0]["rate_pct"]
    assert all(r["check"] for r in P.LEVIES if r["rate_pct"] is None)
    with pytest.raises(LabourError, match="three-letter"):
        S.run(T, "save_settings", {"currency": "rupees"})
    with pytest.raises(LabourError, match="write where the rate comes from"):
        S.run(T, "save_settings", {"deductions": [{"name": "PF", "pct": 12}]})


# ---------------------------------------------------------------- people, papers, the radar
def test_people_papers_and_radar(ld):
    S = ld
    _setup(S)
    ws = {w["name"]: w for w in S.run(T, "workers", {})["workers"]}
    raju = ws["Raju Kamble"]
    assert raju["id_last4"] == "9012" and raju["bank_last4"] == "4455" and raju["employer"] == "Riverside Builders"
    assert ws["Vinod Shinde"]["employer"] == "Kumar Steel Fixers"
    import json
    assert "123456789012" not in json.dumps(S.run(T, "worker", {"id": raju["id"]}))
    S.run(T, "save_paper", {"whose": "worker", "owner": "Raju", "kind": "induction", "valid_to": _d(-10), "number": "IND-99-4471"})
    S.run(T, "save_paper", {"whose": "company", "kind": "licence", "name": "Contract-labour licence", "valid_to": _d(-45)})
    S.run(T, "save_paper", {"whose": "employer", "owner": "Kumar Steel Fixers", "kind": "insurance", "valid_to": _d(3)})
    rd = S.run(T, "radar", {})
    bands = {r["name"]: r["band"] for r in rd["rows"]}
    assert bands["Contract-labour licence"] == "60" and bands["induction"] == "14" and bands["insurance"] == "lapsed"
    r = S.run(T, "import_workers", {"text": "name,trade,gang,employer\nRaju Kamble,Mason,Gang 5,\nKavita Jadhav,Helper,Gang 5,\nAsha Bhosale,Helper,Gang 5,"})
    assert r["saved"] == 3 and r["already"] == 1


# ---------------------------------------------------------------- the muster
def test_muster_checks_and_counter_rows(ld):
    S = ld
    from app.labourdesk.core import LabourError
    _setup(S)
    S.run(T, "save_paper", {"whose": "worker", "owner": "Raju Kamble", "kind": "induction", "valid_to": _d(5)})   # lapsed 5 days ago
    with pytest.raises(LabourError, match="Who is doing"):
        S.run(T, "mark", {"site": "Tower B", "marks": [{"name": "Raju Kamble", "status": "P"}]})
    r = S.run(T, "mark", {"site": "Tower B", "who": "Foreman Patil", "source": "voice",
                          "marks": [{"name": "Raju Kamble", "status": "P", "ot_hours": 2}, {"name": "Sunita", "status": "half"},
                                    {"name": "Ramesh Gaikwad", "status": "P"}, {"employer": "Kumar Steel Fixers", "gang": "Steel", "count": 40}]})
    assert r["saved"] == 2 and r["heads"] == 1 and r["unknown"][0]["name"] == "Ramesh Gaikwad"
    S.run(T, "mark", {"site": "Tower C", "who": "Foreman More", "marks": [{"name": "Raju Kamble", "status": "P"}]})
    S.run(T, "gate", {"site": "Tower B", "count": 40})
    d = S.run(T, "day", {})
    kinds = {f["kind"] for f in d["flags"]}
    assert {"two_sites", "gate", "papers"} <= kinds
    b = next(x for x in d["sites"] if x["site"] == "Tower B")
    assert b["total"] == 42 and b["gate"] == 40
    assert any("lapsed" in f["text"] and "site engineer decides" in f["text"] for f in d["flags"])
    # a correction is a new row; the first one stays
    m = next(p for g in b["gangs"] for p in g["people"] if p["name"] == "Raju Kamble")
    with pytest.raises(LabourError, match="Why"):
        S.run(T, "correct", {"id": m["mark_id"], "who": "Engineer Joshi"})
    S.run(T, "correct", {"id": m["mark_id"], "who": "Engineer Joshi", "reason": "He was at Tower C", "status": "A"})
    d = S.run(T, "day", {})
    assert "two_sites" not in {f["kind"] for f in d["flags"]} and d["corrections"][0]["reason"] == "He was at Tower C"
    from app.db import session
    from app.labourdesk.models import LdMark
    with session() as s:
        assert s.get(LdMark, m["mark_id"]).value == 1.0
    # the unknown name is matched by a person, never guessed
    u = d["unknown"][0]
    S.run(T, "save_worker", {"name": "Ramesh Gaikwad", "trade": "Helper"})
    S.run(T, "resolve", {"id": u["id"], "worker": "Ramesh Gaikwad", "who": "Foreman Patil"})
    assert not S.run(T, "day", {})["unknown"]
    # the engineer approves; a change afterwards is named
    with pytest.raises(PermissionError):
        S.run(T, "close_day", {"site": "Tower B", "who": "x"}, actor="tool")
    S.run(T, "close_day", {"site": "Tower B", "who": "Engineer Joshi"})
    S.run(T, "mark", {"site": "Tower B", "who": "Foreman Patil", "marks": [{"name": "Sunita Pawar", "status": "P"}]})
    assert any(f["kind"] == "after_close" for f in S.run(T, "day", {})["flags"])
    # one device checking many people in inside a minute
    csvt = "name,day,in,out\n" + "\n".join(f"{n},{_d(1)},08:0{i % 2},17:00" for i, n in enumerate(["Raju Kamble", "Sunita Pawar", "Ramesh Gaikwad"] * 1))
    S.run(T, "save_settings", {"burst": 2})
    S.run(T, "import_device", {"site": "Tower B", "text": csvt, "device": "GATE-1"})
    assert any(f["kind"] == "burst" for f in S.run(T, "day", {"day": _d(1)})["flags"])


# ---------------------------------------------------------------- wages
def _week_marks(S, who="Foreman Patil"):
    for n in range(1, 7):
        S.run(T, "mark", {"site": "Tower B", "who": who, "day": _d(n),
                          "marks": [{"name": "Raju Kamble", "status": "P", "ot_hours": 2 if n <= 2 else 0}, {"name": "Sunita Pawar", "status": "P"},
                                    {"name": "Vinod Shinde", "status": "P"}]})


def test_wage_run_india_overtime_floor_chain_and_hash(ld):
    S = ld
    from app.labourdesk.core import LabourError
    _setup(S)
    S.run(T, "save_settings", {"deductions": [{"name": "PF (employee)", "pct": 12, "base": "basic", "cap": 15000, "employer_pct": 12,
                                               "source": "EPF scheme rate, checked by our payroll adviser"}]})
    _week_marks(S)
    S.run(T, "record_advance", {"worker": "Raju Kamble", "amount": 20000, "who": "Meera"})
    r = S.run(T, "draft_run", {"start": _d(6), "end": _d(1)}, actor="tool")
    assert r["status"] == "draft" and {ln["name"] for ln in r["lines"]} == {"Raju Kamble", "Sunita Pawar"}   # own gangs only
    raju = next(ln for ln in r["lines"] if ln["name"] == "Raju Kamble")
    assert raju["days"] == 6 and raju["basic"] == 5400 and raju["ot_hours"] == 4
    assert raju["ot_x"] == 2.0 and raju["ot_pay"] == pytest.approx(4 * 900 / 8 * 2)      # India: twice the ordinary rate
    assert raju["deductions"][0]["amount"] == pytest.approx(648)
    cap = (raju["gross"] - 648) * 0.5
    assert raju["advance"] == pytest.approx(round(cap, 2)) and raju["net"] == pytest.approx(raju["gross"] - 648 - raju["advance"])
    assert any("held to" in c["text"] for c in raju["checks"])
    sun = next(ln for ln in r["lines"] if ln["name"] == "Sunita Pawar")
    assert any("No minimum rate on file for Helper" in c["text"] for c in sun["checks"])
    assert any("At or above the minimum" in c["text"] for c in raju["checks"])
    # below the floor blocks the check
    S.run(T, "save_rate", {"kind": "floor", "trade": "Helper", "rate": 650, "basis": "day", "wef": "2026-01-01", "source": "MH notification Oct 2026 (unskilled)"})
    r = S.run(T, "run", {"id": r["id"]})
    assert r["bad"] == 1 and any("below the minimum 650.00 a day (MH notification Oct 2026" in c["text"] for ln in r["lines"] for c in ln["checks"])
    with pytest.raises(LabourError, match="must be fixed first"):
        S.run(T, "check_run", {"id": r["id"], "who": "Meera"})
    S.run(T, "save_rate", {"trade": "Helper", "rate": 700, "basis": "day", "wef": "2026-06-01", "source": "our rate card, Jun 2026"})
    # the chain: preparer, checker, approver are three people; the tool cannot do any of it
    for part in ("check_run", "approve_run", "mark_paid"):
        with pytest.raises(PermissionError):
            S.run(T, part, {"id": r["id"], "who": "x"}, actor="tool")
    S.run(T, "check_run", {"id": r["id"], "who": "Meera"})
    with pytest.raises(LabourError, match="different person"):
        S.run(T, "approve_run", {"id": r["id"], "who": "Meera"})
    with pytest.raises(LabourError, match="only an approved run"):
        S.run(T, "payment_file", {"id": r["id"]})
    a = S.run(T, "approve_run", {"id": r["id"], "who": "Arjun Rao"})
    assert a["status"] == "approved"
    # a change after approval sends it back to draft
    S.run(T, "mark", {"site": "Tower B", "who": "Foreman Patil", "day": _d(3), "marks": [{"name": "Sunita Pawar", "status": "A"}]})
    v = S.run(T, "run", {"id": r["id"]})
    assert v["status"] == "draft" and v["stale"] and any("back to draft" in x["text"] for x in v["log"])
    S.run(T, "check_run", {"id": r["id"], "who": "Meera"})
    S.run(T, "approve_run", {"id": r["id"], "who": "Arjun Rao"})
    # payment files: names + last 4 only, or accounts typed for this one file (never through the chat)
    pf = S.run(T, "payment_file", {"id": r["id"], "format": "csv"})
    assert "4455" in pf["file"] and "001122334455" not in pf["file"]
    with pytest.raises(PermissionError):
        S.run(T, "payment_file", {"id": r["id"], "format": "in_bulk", "accounts": {"Raju Kamble": {"account": "001122334455", "ifsc": "SBIN0001234"}}}, actor="tool")
    with pytest.raises(LabourError, match="IFSC for Sunita Pawar"):
        S.run(T, "payment_file", {"id": r["id"], "format": "in_bulk", "accounts": {"Raju Kamble": {"account": "001122334455", "ifsc": "SBIN0001234"}}})
    pf = S.run(T, "payment_file", {"id": r["id"], "format": "in_bulk", "accounts": {"Raju Kamble": {"account": "001122334455", "ifsc": "SBIN0001234"},
                                                                                   "Sunita Pawar": {"account": "998877665544", "ifsc": "HDFC0000123"}}})
    assert "001122334455" in pf["file"] and "never kept" in pf["note"]
    from app.db import session
    from app.labourdesk.models import LdRun
    with session() as s:
        assert "001122334455" not in str(s.get(LdRun, r["id"]).log) + str(s.get(LdRun, r["id"]).paid)
    with pytest.raises(LabourError, match="bank's reference"):
        S.run(T, "mark_paid", {"id": r["id"], "who": "Meera"})
    p = S.run(T, "mark_paid", {"id": r["id"], "who": "Meera", "ref": "NEFT-B88213", "failed": {"Sunita Pawar": "account closed"}})
    assert p["status"] == "paid" and p["paid"]["failed"]
    adv = S.run(T, "advances", {})["rows"][0]
    assert adv["recovered"] == pytest.approx(raju["advance"]) and adv["left"] == pytest.approx(20000 - raju["advance"])
    assert S.run(T, "payslips", {"id": r["id"]})["slips"][0]["rows"][-1][0] == "Net pay"
    # nobody is paid twice for the same days
    r2 = S.run(T, "draft_run", {"start": _d(3), "end": _d(1)})
    assert r2["bad"] >= 1 and any("paid twice" in c["text"] for ln in r2["lines"] for c in ln["checks"])


def test_overtime_by_country(ld):
    S = ld
    _setup(S, "US")
    S.run(T, "save_rate", {"trade": "Mason", "rate": 30, "basis": "hour", "wef": "2026-01-01", "source": "our union scale"})
    monday = date.today() - timedelta(days=date.today().weekday() + 7)
    for i in range(5):
        S.run(T, "mark", {"site": "Tower B", "who": "Sam", "day": (monday + timedelta(days=i)).isoformat(), "marks": [{"name": "Raju Kamble", "status": "P", "hours": 9}]})
    r = S.run(T, "draft_run", {"start": monday.isoformat(), "end": (monday + timedelta(days=6)).isoformat()})
    raju = next(ln for ln in r["lines"] if ln["name"] == "Raju Kamble")
    assert raju["ot_hours"] == 5 and raju["normal_hours"] == 40 and raju["ot_x"] == 1.5
    assert raju["basic"] == 1200 and raju["ot_pay"] == pytest.approx(5 * 30 * 1.5)       # US: 1.5x after 40 hours a week
    # UK: no statutory premium - her contract decides; with none written, overtime cannot be paid
    S.run(T, "save_settings", {"country": "GB", "currency": "GBP"})
    S.run(T, "mark", {"site": "Tower B", "who": "Sam", "day": _d(1), "marks": [{"name": "Raju Kamble", "status": "P", "ot_hours": 2}]})
    v = S.run(T, "draft_run", {"start": _d(1), "end": _d(1)})
    assert any("write your contract's overtime multiplier" in c["text"] for ln in v["lines"] for c in ln["checks"])
    S.run(T, "save_settings", {"ot_x": 1.5})
    v = S.run(T, "run", {"id": v["id"]})
    assert next(ln for ln in v["lines"] if ln["name"] == "Raju Kamble")["ot_x"] == 1.5
    # India: her contract may only go higher than the country rule
    S.run(T, "save_settings", {"country": "IN", "ot_x": 1.5})
    assert S.run(T, "run", {"id": v["id"]})["ot"]["x"] == 2.0


def test_second_approver_above_limit(ld):
    S = ld
    from app.labourdesk.core import LabourError
    _setup(S)
    S.run(T, "save_settings", {"second_limit": 1000})
    S.run(T, "save_rate", {"kind": "floor", "trade": "Helper", "rate": 500, "basis": "day", "wef": "2026-01-01", "source": "MH notification"})
    _week_marks(S)
    r = S.run(T, "draft_run", {"start": _d(6), "end": _d(1), "who": "Kiran"})
    S.run(T, "check_run", {"id": r["id"], "who": "Meera"})
    with pytest.raises(LabourError, match="second approver"):
        S.run(T, "approve_run", {"id": r["id"], "who": "Arjun"})
    with pytest.raises(LabourError, match="different person"):
        S.run(T, "approve_run", {"id": r["id"], "who": "Kiran", "who2": "Arjun"})
    assert S.run(T, "approve_run", {"id": r["id"], "who": "Arjun", "who2": "Divya"})["approved_by2"] == "Divya"


# ---------------------------------------------------------------- levies, withholding, the calendar
def test_levies_withholding_and_calendar(ld):
    S = ld
    from app.labourdesk.core import LabourError
    _setup(S)
    with pytest.raises(LabourError, match="No levy rule"):
        S.run(T, "draft_levy", {"base_amount": 23600000, "ref": "RA bill 14"})
    with pytest.raises(PermissionError):
        S.run(T, "use_pack", {"pack_id": "in-cess", "who": "x"}, actor="tool")
    with pytest.raises(LabourError, match="check this"):
        S.run(T, "use_pack", {"pack_id": "in-cess", "who": "Meera"})
    with pytest.raises(LabourError, match="gives no rate"):
        S.run(T, "use_pack", {"pack_id": "in-cess", "who": "Meera", "source": "Maharashtra BOCW board notification"})
    S.run(T, "use_pack", {"pack_id": "in-cess", "who": "Meera", "source": "Maharashtra BOCW board notification", "rate_pct": 1})
    lv = S.run(T, "draft_levy", {"base_amount": 23600000, "ref": "RA bill 14", "day": _d(5), "base_source": "certified cost on RA bill 14"})
    assert lv["amount"] == 236000 and "1% of 23,600,000.00" in lv["how"]
    S.run(T, "mark_levy_paid", {"id": lv["id"], "who": "Meera", "receipt": "CHALLAN-2026-7781"})
    assert S.run(T, "levies", {})["rows"][0]["receipt_last4"] == "7781"
    # India withholding: firm 2%, no checked id 20%, the year's limit counted with catch-up
    S.run(T, "use_pack", {"pack_id": "in-393", "who": "Meera"})
    p = S.run(T, "add_payment", {"employer": "Kumar Steel Fixers", "amount": 840000})
    assert p["withheld"] == 16800 and p["rate_pct"] == 2
    S.run(T, "save_employer", {"name": "Patil Shuttering", "status": "firm"})
    assert S.run(T, "add_payment", {"employer": "Patil Shuttering", "amount": 50000})["rate_pct"] == 20
    S.run(T, "save_employer", {"name": "Om Sai", "status": "individual", "tax_id": "BBBPS1111B", "tax_id_ok": True, "checked_by": "Meera"})
    assert S.run(T, "add_payment", {"employer": "Om Sai", "amount": 25000})["withheld"] == 0
    assert S.run(T, "add_payment", {"employer": "Om Sai", "amount": 25000})["withheld"] == 0
    third = S.run(T, "add_payment", {"employer": "Om Sai", "amount": 60000})       # 1,10,000 this year: past 1,00,000
    assert third["withheld"] == pytest.approx(1100) and "includes 50,000.00 paid earlier" in third["why"]
    cal = S.run(T, "calendar", {})["items"]
    assert any(i["what"].startswith("Deposit the tax withheld") for i in cal)
    m = date.today().strftime("%Y-%m")
    S.run(T, "mark_deposited", {"month": m, "who": "Meera", "receipt": "ITNS281-00991"})
    assert not any(i["what"] == f"Deposit the tax withheld in {m}" for i in S.run(T, "calendar", {})["items"])
    # a rule past its review date refuses
    from app.db import session
    from app.labourdesk.models import LdRule
    with session() as s:
        for r in s.query(LdRule).all():
            r.review_by = _d(1)
    with pytest.raises(LabourError, match="review date"):
        S.run(T, "add_payment", {"employer": "Kumar Steel Fixers", "amount": 1000})


def test_uk_cis_and_queensland_levy(ld):
    S = ld
    _setup(S, "GB")
    S.run(T, "use_pack", {"pack_id": "gb-cis", "who": "Jo"})
    S.run(T, "save_employer", {"name": "Northgate Drylining", "status": "registered"})
    p = S.run(T, "add_payment", {"employer": "Northgate Drylining", "amount": 10000, "materials": 2000})
    assert p["rate_pct"] == 30 and p["withheld"] == 2400 and p["base"] == 8000     # unverified with HMRC = 30%, materials out
    S.run(T, "save_employer", {"name": "Northgate Drylining", "status": "registered", "tax_id_ok": True, "checked_by": "Jo"})
    assert S.run(T, "add_payment", {"employer": "Northgate Drylining", "amount": 10000, "materials": 2000})["withheld"] == 1600
    S.run(T, "save_settings", {"country": "AU", "region": "QLD", "currency": "AUD"})
    S.run(T, "use_pack", {"pack_id": "au-qld", "who": "Jo"})
    assert S.run(T, "draft_levy", {"base_amount": 2000000, "ref": "Contract 7"})["amount"] == 11500


# ---------------------------------------------------------------- subcontractor evidence
def test_subcontractor_evidence_gaps_and_decision(ld):
    S = ld
    _setup(S)
    S.run(T, "save_worker", {"name": "Prakash Jadhav", "trade": "Bar bender", "employer": "Kumar Steel Fixers"})
    for n in (1, 2):
        S.run(T, "mark", {"site": "Tower B", "who": "Foreman", "day": _d(n), "marks": [{"name": "Vinod Shinde", "status": "P"}, {"name": "Prakash Jadhav", "status": "P"}]})
    p = S.run(T, "period", {"start": _d(6), "end": _d(0)})
    row = p["rows"][0]
    assert row["people"] == 2 and "no payment proof for 2 people" in row["say"]
    S.run(T, "add_evidence", {"employer": "Kumar Steel Fixers", "start": _d(6), "end": _d(0), "kind": "payment", "names": ["Vinod Shinde"]})
    S.run(T, "add_evidence", {"employer": "Kumar Steel Fixers", "start": _d(6), "end": _d(0), "kind": "register", "people": 2})
    row = S.run(T, "period", {"start": _d(6), "end": _d(0)})["rows"][0]
    pay = next(i for i in row["items"] if i["kind"] == "payment")
    assert pay["state"] == "part" and pay["missing_names"] == ["Prakash Jadhav"]
    d = S.run(T, "draft_hold", {"employer": "Kumar Steel Fixers", "start": _d(6), "end": _d(0)}, actor="tool")
    assert "Prakash Jadhav" in d["text"] and S.run(T, "period", {"start": _d(6), "end": _d(0)})["rows"][0]["decision"]["status"] == "draft"   # nothing held by itself
    with pytest.raises(PermissionError):
        S.run(T, "decide_hold", {"id": d["id"], "decision": "hold", "who": "x"}, actor="tool")
    S.run(T, "decide_hold", {"id": d["id"], "decision": "hold", "who": "Arjun Rao"})
    assert S.run(T, "period", {"start": _d(6), "end": _d(0)})["rows"][0]["decision"]["status"] == "hold"


def test_today_and_old_rows_once(ld):
    S = ld
    from app.construction import labour as OLD
    OLD.licence(T, "contract_labour", number="CLL/2025/114471", holder="Shree Ganesh Labour", site="Tower B", valid_to=_d(-20))
    OLD.wage_rate(T, "Carpenter", 850, source="old rate card")
    S.run(T, "today", {})
    S.run(T, "today", {})
    assert len([p for p in S.run(T, "papers", {})["rows"] if p["number_last4"] == "4471"]) == 1
    assert any(r["trade"].lower() == "carpenter" for r in S.run(T, "rates", {})["rows"])
    _setup(S)
    _week_marks(S)
    t = S.run(T, "today", {})
    assert t["tiles"]["sites_total"] == 2 and t["chart"]["rows"][-2]["own"] == 2 and t["chart"]["planned"] == 30
    assert any(n["go"] == "workers" for n in t["needs"])


# ---------------------------------------------------------------- the chat, the tool and the wiring
def test_chat_tool_and_wiring(ld):
    import asyncio
    from pathlib import Path
    from fastapi.testclient import TestClient
    from app import labourchat as C
    from app.agent.tools import Ctx, FAMILY_OF, HANDLERS, ToolError
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    C.forget(T)
    assert C.summary(T)["hired"] is False and "Hire me from AI Employees" in C.greeting(T)
    with pytest.raises(PermissionError):
        C.do(T, "save_site", {"name": "Tower Z"})
    hire.hire(T, "const_labour", trust="seekh")
    d = C.summary(T)
    assert d["hired"] and "pays nobody" in d["foot"] and any(n["go"] == "settings" for n in d["desk"]["needs"])
    chat = C.current(T)
    assert C.is_labour(chat["id"]) and C.owns(T, chat["id"]) and "<labour_desk>" in C.block(T)
    _setup(ld)
    C.forget(T)
    assert "INR" in C.block(T) and "Tower B" in C.block(T) and "2x beyond 8 hours a day" in C.block(T)
    assert FAMILY_OF["labour_desk"] in C.FAMILIES and "labour_desk" in HANDLERS
    ctx = Ctx(tenant_id=T, conversation_id=chat["id"])
    r = asyncio.run(HANDLERS["labour_desk"](ctx, action="mark", site="Tower B", who="Foreman Patil", source="voice",
                                            marks=[{"name": "Raju Kamble", "status": "P"}, {"name": "Nobody Known", "status": "P"}]))
    assert r["saved"] == 1 and r["unknown"][0]["name"] == "Nobody Known"
    for tap in ("close_day", "check_run", "approve_run", "mark_paid", "record_advance", "use_pack", "decide_hold", "mark_levy_paid"):
        with pytest.raises(ToolError):
            asyncio.run(HANDLERS["labour_desk"](ctx, action=tap, id="x", who="x", site="Tower B"))
    with pytest.raises(PermissionError):
        C.do(T, "save_site", {"name": "my password is hunter2"})
    assert C.do(T, "close_day", {"site": "Tower B", "who": "Engineer Joshi"})["say"].startswith("Muster")
    hire.pause(T, "const_labour")
    assert C.do(T, "workers", {})["workers"]
    with pytest.raises(PermissionError):
        C.do(T, "save_site", {"name": "Tower Y"})
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "is_labour(conversation_id)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"labour"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/labour")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "labourdesk.js" in r.text
    html = (root / "server/app/static/console/labourdesk.html").read_text()
    for x in ("chatkit.js", "labourdesk.css", "labourdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "/console/labour" in (root / "server/app/static/console/v2.js").read_text()
    assert "const_labour = 'labourdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "/console/labour" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def lb_server(ld, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "const_labour", trust="seekh")
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
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(ld, lb_server):
    base, browser, key = lb_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    def toast(pg, text):
        pg.wait_for_selector(f"#toast:has-text('{text}')", timeout=20000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/labour")
    pg.wait_for_selector(".sk-greet", timeout=20000)
    assert "Start here" in pg.inner_text("#lbPage")
    snap(pg, "lb-today-empty-1440")
    # settings: company, a site, rates
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=company]", "Riverside Builders")
    pg.fill("form[data-form=settings] [name=country]", "IN")
    pg.fill("form[data-form=settings] [name=region]", "MH")
    pg.fill("form[data-form=settings] [name=currency]", "INR")
    pg.click("form[data-form=settings] button")
    toast(pg, "Settings saved")
    assert "Riverside Builders" in pg.inner_text("#lbSite") and "INR" in pg.inner_text("#lbSite")
    pg.fill("form[data-form=site] [name=name]", "Tower B")
    pg.fill("form[data-form=site] [name=planned]", "30")
    pg.click("form[data-form=site] button")
    pg.wait_for_selector("#lbPage :text('Tower B')", timeout=20000)
    for kind, trade, rate, src in (("pay", "Mason", "900", "Riverside rate card 2026"), ("floor", "Mason", "750", "MH minimum wages notification Oct 2026")):
        pg.select_option("form[data-form=rate] [name=kind]", kind)
        pg.fill("form[data-form=rate] [name=trade]", trade)
        pg.fill("form[data-form=rate] [name=rate]", rate)
        pg.fill("form[data-form=rate] [name=source]", src)
        pg.click("form[data-form=rate] button")
        toast(pg, "Minimum rate saved" if kind == "floor" else "Pay rate saved")
        pg.wait_for_selector(f"#lbPage .cs-row :text('{src}')", timeout=20000)
    snap(pg, "lb-settings-1440")
    # workers
    go(pg, "#/workers", "form[data-form=importworkers]")
    pg.fill("form[data-form=importworkers] [name=text]", "name,trade,gang,site\nRaju Kamble,Mason,Gang 5,Tower B\nSunita Pawar,Mason,Gang 5,Tower B")
    pg.click("form[data-form=importworkers] button")
    toast(pg, "2 worker(s) saved")
    pg.wait_for_selector("table.lb-wk :text('Raju Kamble')", timeout=20000)
    snap(pg, "lb-workers-1440")
    # the muster: tap P / A, overtime, send
    go(pg, "#/muster", "form[data-form=mustermark]")
    rows = pg.locator(".lb-ln")
    assert rows.count() == 2
    pg.click(".lb-ln:has-text('Raju Kamble') button.p")
    pg.fill(".lb-ln:has-text('Raju Kamble') input.lb-ot", "2")
    pg.click(".lb-ln:has-text('Sunita Pawar') button.p")
    pg.fill("form[data-form=mustermark] [name=who]", "Foreman Patil")
    pg.click("form[data-form=mustermark] button[type=submit]")
    toast(pg, "2 mark(s) saved")
    pg.wait_for_selector("form[data-form=closeday]", timeout=20000)
    pg.fill("form[data-form=closeday] [name=who]", "Engineer Joshi")
    pg.click("form[data-form=closeday] button")
    pg.wait_for_selector("#lbPage :text('approved by Engineer Joshi')", timeout=20000)
    snap(pg, "lb-muster-1440")
    # wages: prepare, check, approve, file, paid
    today = pg.evaluate("document.querySelector('#lbPage') && (new Date()).toISOString().slice(0,10)")
    go(pg, "#/wages", "form[data-form=draftrun]")
    pg.fill("form[data-form=draftrun] [name=start]", (date.fromisoformat(today) - timedelta(days=3)).isoformat())
    pg.fill("form[data-form=draftrun] [name=end]", (date.fromisoformat(today) + timedelta(days=1)).isoformat())
    pg.click("form[data-form=draftrun] button")
    pg.wait_for_selector("form[data-form=checkrun]", timeout=30000)
    txt = pg.inner_text("#lbPage")
    assert "Raju Kamble" in txt and "2×" in txt
    pg.fill("form[data-form=checkrun] [name=who]", "Meera")
    pg.click("form[data-form=checkrun] button")
    pg.wait_for_selector("form[data-form=approverun]", timeout=20000)
    pg.fill("form[data-form=approverun] [name=who]", "Arjun Rao")
    pg.click("form[data-form=approverun] button")
    pg.wait_for_selector("form[data-form=paid]", timeout=20000)
    with pg.expect_download() as dl:
        pg.click("[data-file=csv]")
    assert dl.value.suggested_filename.endswith("-csv.csv")
    pg.fill("form[data-form=paid] [name=ref]", "NEFT-B88213")
    pg.fill("form[data-form=paid] [name=who]", "Meera")
    pg.click("form[data-form=paid] button")
    pg.wait_for_selector("#lbPage :text('reference NEFT-B88213')", timeout=20000)
    pg.click("[data-slips]")
    pg.wait_for_selector(".lb-slip", timeout=20000)
    snap(pg, "lb-run-1440")
    # levies: take the cess row with its source and rate, then a bill
    go(pg, "#/levies", "#lbPage .sd-h")
    pg.wait_for_selector("form[data-form=usepack][data-id=in-cess]", state="attached", timeout=20000)
    pg.evaluate("document.querySelector('form[data-form=usepack][data-id=in-cess]').closest('details').open = true")
    pg.fill("form[data-form=usepack][data-id=in-cess] [name=source]", "Maharashtra BOCW board notification")
    pg.fill("form[data-form=usepack][data-id=in-cess] [name=rate_pct]", "1")
    pg.fill("form[data-form=usepack][data-id=in-cess] [name=who]", "Meera")
    pg.click("form[data-form=usepack][data-id=in-cess] button")
    pg.wait_for_selector("form[data-form=levy]", timeout=20000)
    pg.fill("form[data-form=levy] [name=ref]", "RA bill 14")
    pg.fill("form[data-form=levy] [name=base_amount]", "23600000")
    pg.click("form[data-form=levy] button")
    toast(pg, "Due by")
    pg.wait_for_selector("#lbPage td:has-text('RA bill 14')", timeout=20000)
    assert "2,36,000" in pg.inner_text("#lbPage") or "236,000" in pg.inner_text("#lbPage")
    snap(pg, "lb-levies-1440")
    go(pg, "#/subs", "#lbPage .sd-h")
    go(pg, "#/reports", "#lbPage :text('Wage register')")
    snap(pg, "lb-reports-1440")
    go(pg, "#/today", ".sk-greet")
    assert pg.locator(".cs-hero").count() == 1 and pg.locator(".lb-bars").count() == 1
    snap(pg, "lb-today-1440")
    # the phone: every page fits; the foreman's muster works offline
    ph = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    ph.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pp = ph.new_page()
    pp.on("pageerror", lambda e: errs.append("phone: " + str(e)))
    pp.goto(base + "/console/labour")
    pp.wait_for_selector(".sk-greet", timeout=20000)
    for tab in ("today", "muster", "workers", "wages", "levies", "subs", "reports", "settings"):
        go(pp, "#/" + tab, "#lbPage .sd-h")
        pp.wait_for_timeout(400)
        w = pp.evaluate("document.documentElement.scrollWidth")
        page_w = pp.evaluate("document.querySelector('#lbPage').scrollWidth")
        assert w <= 391, (tab, w)
        assert page_w <= 391, (tab, page_w)
        snap(pp, f"lb-{tab}-390")
    go(pp, "#/muster", "form[data-form=mustermark]")
    ph.set_offline(True)
    pp.click(".lb-ln:has-text('Sunita Pawar') button.a")
    pp.fill("form[data-form=mustermark] [name=who]", "Foreman Patil")
    pp.click("form[data-form=mustermark] button[type=submit]")
    toast(pp, "saved on this device")
    assert pp.evaluate("JSON.parse(localStorage.getItem('hoola.labour.queue')).length") == 1
    ph.set_offline(False)
    pp.evaluate("window.dispatchEvent(new Event('online'))")
    for _ in range(100):
        if pp.evaluate("JSON.parse(localStorage.getItem('hoola.labour.queue') || '[]').length") == 0:
            break
        pp.wait_for_timeout(200)
    assert pp.evaluate("JSON.parse(localStorage.getItem('hoola.labour.queue') || '[]').length") == 0
    toast(pp, "muster(s) sent")
    errs = [e for e in errs if "Failed to fetch" not in e and "ERR_INTERNET_DISCONNECTED" not in e]
    assert not errs, errs
