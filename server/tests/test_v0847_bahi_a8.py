"""v0.847 BAHI A8 - payables, receivables, TDS: party master, ageing, MSME + Rule 37 watches, reminder drafts, the TDS worksheet / register / quarter."""
from datetime import date, timedelta

import pytest

MINE = "27ADCPI1932N1ZH"
TODAY = date(2026, 11, 12)


def d(n):
    return (TODAY - timedelta(days=n)).isoformat()


@pytest.fixture
def a8(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-a8-0123456789abcdef")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bahi import payables
    from app.bahi.models import AccBankLine, AccDoc, ensure_tables
    from app.db import session
    ensure_tables()
    with session() as s:
        def doc(n, days_old, party, total, direction, igst=0.0, kind="inv"):
            s.add(AccDoc(tenant_id="t1", gstin=MINE, period=d(days_old)[:7], direction=direction, kind=kind, number=n, doc_date=d(days_old), party_name=party,
                         total=total, igst=igst, source="app", source_ref=n))
        doc("S-1", 10, "Acme", 5000, "out")                # not yet due (30 days)
        doc("S-2", 50, "Acme", 7000, "out")                # 20 days late
        doc("S-3", 140, "Beta", 3000, "out")               # 110 days late -> 90+
        doc("P-1", 20, "Tiny Mills", 10000, "in", igst=1800)   # micro supplier: due after 15 days, 5 days overdue
        doc("P-2", 190, "Old Supplier", 20000, "in", igst=3600)   # past 180 days, unpaid
        doc("P-3", 100, "Paid Co", 8000, "in", igst=1440)
        s.flush()
        paid = s.query(AccDoc).filter_by(number="P-3").one()
        s.add(AccBankLine(tenant_id="t1", line_hash="h1", date=d(90), narration="paid", debit=8000, status="matched", match_doc_id=paid.id))
        s.commit()
    payables.party_save("t1", {"name": "Tiny Mills", "msme_class": "micro", "gstin": "", "pan": "AABCT1234F"})
    payables.party_save("t1", {"name": "Beta", "no_reminders": True})
    return payables


def test_ageing_buckets_and_settled_by_a_confirmed_bank_line(a8):
    ar = a8.ageing("t1", "out", TODAY)
    acme = next(p for p in ar["parties"] if p["party"] == "Acme")
    assert acme["not_due"] == 5000 and acme["1-30"] == 7000 and acme["total"] == 12000
    assert next(p for p in ar["parties"] if p["party"] == "Beta")["90+"] == 3000 and ar["totals"]["all"] == 15000
    ap = a8.ageing("t1", "in", TODAY)
    assert "Paid Co" not in {p["party"] for p in ap["parties"]}                 # settled by the matched bank line
    assert ap["totals"]["all"] == 30000
    assert a8.ageing("other", "out", TODAY)["totals"]["all"] == 0


def test_msme_15_45_day_alarm_and_the_year_end_warning(a8):
    m = a8.msme_watch("t1", TODAY)
    assert [r["party"] for r in m["rows"]] == ["Tiny Mills"]
    r = m["rows"][0]
    assert r["limit_days"] == 15 and r["days_left"] == -5 and r["state"] == "overdue" and r["fy_end_risk"] and not r["agreed_in_writing"]
    assert "31 Mar 2027" in m["note"] and "43B(h)" in m["note"]
    a8.party_save("t1", {"name": "Tiny Mills", "agreed_days": 90})               # more than 45 is capped at 45
    r2 = a8.msme_watch("t1", TODAY)["rows"][0]
    assert r2["limit_days"] == 45 and r2["state"] == "ok" and r2["agreed_in_writing"]


def test_rule_37_watch_and_collection_reminders_respect_stop(a8):
    r = a8.rule37_watch("t1", TODAY)
    assert [x["number"] for x in r["rows"]] == ["P-2"] and r["rows"][0]["state"] == "reverse_credit" and r["rows"][0]["credit_at_stake"] == 3600
    rem = a8.reminders("t1", TODAY)
    assert [x["party"] for x in rem] == ["Acme"]                                  # Beta is stopped
    assert "S-2" in rem[0]["text"] and "20 days late" in rem[0]["text"] and rem[0]["wa_link"].startswith("https://wa.me/?text=") and "S-1" not in rem[0]["text"]


def test_the_party_master_hides_the_bank_account_and_flags_a_changed_one(a8):
    p = a8.party_save("t1", {"name": "Vendor X", "bank_account": "123456789012", "bank_ifsc": "hdfc0001234"})
    assert p["bank"] == "xxxxxxxx9012" and "123456789012" not in str(p)
    again = a8.party_save("t1", {"name": "Vendor X", "bank_account": "999988887777", "bank_ifsc": "HDFC0001234"})
    assert again["bank_changes"] == 1 and "check by phone" in again["warning"]
    from app.bahi.models import AccEvent
    from app.db import session
    with session() as s:
        assert s.query(AccEvent).filter_by(tenant_id="t1", what="party_bank_changed").count() == 1
    with pytest.raises(a8.PayError):
        a8.party_save("t1", {"name": "Bad", "gstin": "27ADCPI1932N1ZX"})
    with pytest.raises(a8.PayError):
        a8.party_save("t1", {"name": "Bad", "msme_class": "huge"})


def test_tds_worksheet_limits_rates_no_pan_and_gst_split(a8):
    pid = lambda n: next(p["id"] for p in a8.parties("t1") if p["name"] == n)   # noqa: E731
    a8.party_save("t1", {"name": "CA Firm", "pan": "ABCPD1234E", "constitution": "individual"})
    w = a8.worksheet("t1", pid("CA Firm"), "professional", 60000, "2026-10-10")
    assert w["applies"] and w["rate"] == 10.0 and w["tds"] == 6000 and w["net_to_pay"] == 54000 and w["section"] == "194J" and w["due_on"] == "2026-11-07"
    assert "item number" in w["verify"]
    low = a8.worksheet("t1", pid("CA Firm"), "professional", 20000, "2026-10-10")
    assert not low["applies"] and low["tds"] == 0 and "Below the limits" in " ".join(low["notes"])
    g = a8.worksheet("t1", pid("CA Firm"), "professional", 70800, "2026-10-10", gst_separate=True, gst_amount=10800)
    assert g["base"] == 60000 and g["tds"] == 6000 and "before GST" in " ".join(g["notes"])
    a8.party_save("t1", {"name": "Hauler", "pan": "ABCPD9999E", "constitution": "individual"})
    assert a8.worksheet("t1", pid("Hauler"), "contractor", 40000, "2026-10-10")["rate"] == 1.0          # individual: 1%
    a8.party_save("t1", {"name": "Hauler Pvt", "pan": "AABCH1234F", "constitution": "company"})
    assert a8.worksheet("t1", pid("Hauler Pvt"), "contractor", 40000, "2026-10-10")["rate"] == 2.0
    a8.party_save("t1", {"name": "No Pan Co", "pan_ok": False, "constitution": "company"})
    n = a8.worksheet("t1", pid("No Pan Co"), "contractor", 40000, "2026-10-10")
    assert n["rate"] == 20.0 and "higher rate" in " ".join(n["notes"])
    assert a8.worksheet("t1", pid("CA Firm"), "professional", 10000, "2027-03-20")["due_on"] == "2027-04-30"       # March -> 30 April
    with pytest.raises(a8.PayError):
        a8.worksheet("t1", pid("CA Firm"), "gold", 1000, "2026-10-10")


def test_the_register_deposit_quarter_and_26as(a8):
    pid = next(p["id"] for p in a8.parties("t1") if p["name"] == "Tiny Mills")
    with pytest.raises(a8.PayError):
        a8.record("t1", pid, "professional", 60000, "2026-08-10")                    # needs her confirm
    r = a8.record("t1", pid, "professional", 60000, "2026-08-10", confirm=True)
    assert r["tds"] == 6000 and r["state"] in ("overdue", "to_deposit")
    # the yearly limit counts what is already recorded: a 30k payment after a 60k one still deducts
    assert a8.worksheet("t1", pid, "professional", 30000, "2026-09-10")["applies"]
    reg = a8.register("t1", 2026)
    assert reg["to_deposit"] == 6000 and reg["overdue"] and reg["rows"][0]["interest_estimate"] >= 0
    with pytest.raises(a8.PayError):
        a8.deposit("t1", [r["id"]], "x", "2026-09-07")                               # not a real challan serial
    assert a8.deposit("t1", [r["id"]], "CIN 0510308 123", "2026-09-07")["deposited"] == 1
    assert a8.register("t1", 2026)["rows"][0]["state"] == "deposited"                # due 7 Sep, deposited 7 Sep: on time
    late = a8.record("t1", pid, "professional", 60000, "2026-09-10", confirm=True)
    a8.deposit("t1", [late["id"]], "CIN 0510308 124", "2026-11-01")                  # due 7 Oct, deposited 1 Nov: late
    assert [x for x in a8.register("t1", 2026)["rows"] if x["id"] == late["id"]][0]["state"] == "deposited_late"
    q = a8.quarter("t1", 2026, 2)
    assert q["statement"].startswith("Form 140") and q["due_on"] == "2026-10-31" and q["total_tds"] == 12000 and len(q["rows"]) == 2 and q["rows"][0]["deductee_pan"] == "AABCT1234F"
    q1 = a8.quarter("t1", 2026, 1)
    assert q1["due_on"] == "2026-07-31" and a8.quarter("t1", 2026, 3)["due_on"] == "2027-01-31" and a8.quarter("t1", 2026, 4)["due_on"] == "2027-05-31"
    with pytest.raises(a8.PayError):
        a8.quarter("t1", 2026, 5)
    m = a8.match_26as("t1", 2026, [{"party": "tiny mills", "section": "194J", "tds": 12000}])
    assert m["matched"] == 1 and m["to_check"] == 0


def test_the_tds_rules_file_is_honest_and_the_routes_exist(a8):
    from app.bahi import rules as RU
    rows = RU.rows("tds")
    assert {"194C", "194J_prof", "194J_tech", "194H", "194I_land", "194I_plant", "194A"} == {r["id"] for r in rows}
    assert all("s.393 item number not read" in r["source"] for r in rows) and all(RU.usable(r) for r in rows)
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for route in ("/api/bahi/parties", "/api/bahi/ageing", "/api/bahi/msme", "/api/bahi/rule37", "/api/bahi/reminders", "/api/bahi/tds/worksheet",
                  "/api/bahi/tds/record", "/api/bahi/tds/deposit", "/api/bahi/tds/register", "/api/bahi/tds/quarter", "/api/bahi/tds/26as"):
        assert route in api
    js = (root / "static/console/bahi.js").read_text()
    assert "pyws" in js and "pyrec" in js and "Hoola pays, deducts and files nothing" in js
