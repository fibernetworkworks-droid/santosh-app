"""v0.849 BAHI A10 - month-end checklist (ticked only from records), MIS + daily line, calendar, accuracy sweep, GSTR-9 comparison. No network."""
import json
from datetime import date

import httpx
import pytest

MINE = "27ADCPI1932N1ZH"
BUYER = "29AABCU9603R1ZX"
TODAY = date(2026, 11, 12)


@pytest.fixture
def a10(env, monkeypatch):
    for k, v in {"WHITEBOOKS_EMAIL": "o@example.com", "WHITEBOOKS_GST_CLIENT_ID": "GSTS" + "x" * 36, "WHITEBOOKS_GST_CLIENT_SECRET": "s" * 40}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bahi import closing, wb
    from app.bahi.models import AccBankLine, AccDoc, AccGstConn, AccParty, AccTds, AccTwoB, ensure_tables
    from app.db import session
    ensure_tables()
    with session() as s:
        def doc(n, direction, kind, party, gstin, taxable, igst=0.0, day="2026-10-05"):
            s.add(AccDoc(tenant_id="t1", gstin=MINE, period=day[:7], direction=direction, kind=kind, number=n, doc_date=day, party_name=party, party_gstin=gstin,
                         taxable=taxable, igst=igst, total=taxable + igst, source="app", source_ref=n))
        doc("S-1", "out", "inv", "Acme Traders", BUYER, 10000, 1800)
        doc("CN-1", "out", "cn", "Acme Traders", BUYER, 1000, 180)
        doc("P-1", "in", "bill", "Beta", "27AABCB1234C1ZX", 4000, 720)
        doc("S-OLD", "out", "inv", "Late Payer", "", 500, 0, day="2026-10-02")
        doc("PB-24", "in", "bill", "Old Supplier", "27AABCB9999C1ZX", 5000, 900, day="2026-02-10")
        s.flush()
        s.add(AccBankLine(tenant_id="t1", line_hash="a", date=TODAY.isoformat(), narration="UPI in", credit=42300, status="matched"))
        s.add(AccBankLine(tenant_id="t1", line_hash="b", date=TODAY.isoformat(), narration="UPI out", debit=18900, status="open"))
        s.add(AccBankLine(tenant_id="t1", line_hash="c", date="2026-10-09", narration="CASH DEPOSIT", credit=100000, mode="cash", status="open"))
        s.add(AccTwoB(tenant_id="t1", gstin=MINE, period="102026", section="b2b", ctin="27AABCB1234C1ZX", inum="P-1", igst=720, itcavl=True, action=""))
        s.add(AccTds(tenant_id="t1", party_id="p", party_name="CA", rule_id="194J_prof", section="194J", paid_on="2026-10-10", base=60000, rate=10, tds=6000, due_on="2026-11-07"))
        s.add(AccParty(tenant_id="t1", name="Acme Traders", agreed_days=30))
        s.add(AccGstConn(tenant_id="t1", gstin=MINE, state_cd="27", gst_username="u", txn="TXN", status="connected", enabled_until="2999-01-01T00:00:00+00:00"))
        s.commit()
    monkeypatch.setattr(wb, "TRANSPORT", httpx.MockTransport(lambda r: httpx.Response(200, json={"status_cd": "1", "data": {
        "tot": {"iamt": 1620, "camt": 0, "samt": 0, "csamt": 0}, "other": {"x": "y"}}}) if "/gstr9/" in r.url.path else httpx.Response(404)))
    yield closing
    get_settings.cache_clear()


def test_the_checklist_ticks_only_what_the_records_show(a10):
    ck = a10.checklist("t1", MINE, "2026-10", TODAY)
    by = {i["key"]: i for i in ck["items"]}
    assert by["bank"]["state"] == "todo" and "unmatched" in by["bank"]["why"]
    assert by["twob"]["state"] == "todo" and "no accept" in by["twob"]["why"] and by["twob"]["due"] == "2026-11-14"
    assert by["gstr1"]["state"] == "todo" and by["gstr3b"]["state"] == "todo" and by["gstr3b"]["due"] == "2026-11-20"
    assert by["tds"]["state"] == "todo" and "6000" in by["tds"]["why"]
    assert by["payroll"]["state"] == "na" and by["accruals"]["state"] == "na" and by["closed"]["state"] == "todo"
    assert by["bills"]["state"] == "done" and not ck["ready_to_close"]
    assert ck["done"] == 1 and ck["total"] == ck["done"] + len([i for i in ck["items"] if i["state"] == "todo"])
    # a record turns a line green: a filed-event, a deposit, a decided 2B
    from app.bahi import register
    from app.bahi.models import AccTds, AccTwoB
    from app.db import session
    with session() as s:
        register._event(s, "t1", "gstr1_filed", f"{MINE}:2026-10", actor="owner")
        for t in s.query(AccTds).all():
            t.deposited_on, t.challan = "2026-11-06", "CIN123456"
        for t in s.query(AccTwoB).all():
            t.action, t.applied_at = "accept", "2026-11-10T10:00:00"
        s.commit()
    by = {i["key"]: i for i in a10.checklist("t1", MINE, "2026-10", TODAY)["items"]}
    assert by["gstr1"]["state"] == "done" and by["tds"]["state"] == "done" and by["twob"]["state"] == "done"
    with pytest.raises(a10.CloseError):
        a10.checklist("t1", MINE, "Oct", TODAY)


def test_mis_and_the_daily_cash_line(a10):
    m = a10.mis("t1", MINE, "2026-10")
    assert m["sales_taxable"] == 10000 + 500 - 1000 and m["purchases_taxable"] == 4000 and m["margin_on_purchases"] == 5500 and "not a true gross profit" in m["margin_note"]
    assert m["cash_in"] == 100000 and m["cash_out"] == 0 and m["bank_lines"] == 1          # the other two bank lines are dated today (November)
    d = a10.daily_line("t1", TODAY.isoformat())
    assert d["in"] == 42300 and d["out"] == 18900 and "Rs 42,300 came in" in d["text"] and "Rs 18,900 went out" in d["text"] and "Hoola sends nothing" in d["note"]
    assert a10.daily_line("t1", "2026-01-01")["text"].startswith("No bank movement")
    # Acme's S-1 (agreed 30 days) falls due on 2026-11-04 -> a day-before line names it
    due = a10.daily_line("t1", "2026-11-03")
    assert any(x["party"] == "Acme Traders" and x["amount"] == 11800 for x in due["due_tomorrow_from"]) and "Due tomorrow from customers: Acme Traders Rs 11,800" in due["text"]


def test_the_calendar_merges_monthly_and_yearly_dates_and_marks_unconfirmed_ones(a10):
    cal = a10.calendar("t1", MINE, TODAY)
    ids = {(x["id"], x["date"]) for x in cal["items"]}
    assert ("itc_cliff", "2026-11-30") in ids and ("advance_tax_3", "2026-12-15") in ids and any(i == "gstr3b" for i, _ in ids)
    g9 = [x for x in cal["items"] if x["id"] == "gstr9"]
    assert g9 and all(x["warning_only"] for x in g9)                                  # an unverified date is a warning only
    assert [x["date"] for x in cal["items"]] == sorted(x["date"] for x in cal["items"])
    c = cal["itc_cliff"]
    assert c["itc_cliff_for"] == "purchases dated 2025-04 to 2026-03" and c["purchase_bills"] == 1 and c["credit_in_those_bills"] == 900
    assert "Rule 37A" in cal["not_built"]


def test_the_sweep_flags_split_parties_round_cash_and_a_changed_bank(a10):
    from app.bahi.models import AccDoc, AccParty
    from app.db import session
    with session() as s:
        s.add(AccDoc(tenant_id="t1", gstin=MINE, period="2026-10", direction="in", kind="bill", number="X-1", doc_date="2026-10-11", party_name="BETA TRADERS", party_gstin="27AABCB1234C1ZX",
                     taxable=1, total=1, source="app", source_ref="X-1"))
        p = s.query(AccParty).filter_by(name="Acme Traders").one()
        p.bank_history = json.dumps([{"on": "2026-10-01"}])
        s.commit()
    sw = a10.sweep("t1")
    kinds = {f["kind"] for f in sw["flags"]}
    assert {"party_many_names", "round_cash", "bank_changed"} <= kinds
    assert any("Beta" in f["text"] and "BETA TRADERS" in f["text"] for f in sw["flags"] if f["kind"] == "party_many_names")
    assert all(f["fix"] in ("py", "bk") for f in sw["flags"]) and len(sw["not_checked"]) == 2


def test_gstr9_compares_with_the_portal_or_says_it_could_not_read_it(a10):
    r = a10.gstr9_compare("t1", MINE, "2025-26")
    assert r["compared"] and r["rows"][0]["head"] == "igst" and r["rows"][0]["portal"] == 1620
    igst = next(x for x in r["rows"] if x["head"] == "igst")
    assert igst["register"] == 0.0 and igst["diff"] == -1620.0 and igst["portal"] == 1620 and "NOT VERIFIED" in r["note"] and any("tot" in f for f in r["portal_fields_autocal"])
    with pytest.raises(a10.CloseError):
        a10.gstr9_compare("t1", MINE, "2025")
    with pytest.raises(a10.CloseError) as e:
        a10.gstr9_compare("nobody", MINE, "2025-26")
    assert "OTP" in str(e.value)


def test_wiring(a10):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for r in ("checklist", "mis", "daily", "calendar", "sweep", "gstr9"):
        assert f"/api/bahi/close/{r}" in api
    js = (root / "static/console/bahi.js").read_text()
    assert "meload" in js and "meg9" in js and "Nothing here sends, files or pays" in js
    from app.bahi import rules as RU
    assert {r["id"] for r in RU.rows("annual")} >= {"itc_cliff", "gstr9", "msme1_h1"}
