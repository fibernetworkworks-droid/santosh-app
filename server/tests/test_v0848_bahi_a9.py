"""v0.848 BAHI A9 - Tally vouchers from the register, the monthly CA pack, close a month on its hash."""
import io
import json
import re
import zipfile
from xml.dom import minidom

import pytest

MINE = "27ADCPI1932N1ZH"
BUYER = "29AABCU9603R1ZX"


@pytest.fixture
def a9(env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from app.bahi import book
    from app.bahi.models import AccBankLine, AccDoc, AccIntake, ensure_tables
    from app.db import session
    ensure_tables()
    with session() as s:
        def doc(n, direction, kind, party, gstin, taxable, igst=0.0, cgst=0.0, sgst=0.0, total=None, day="2026-10-05"):
            tot = total if total is not None else round(taxable + igst + cgst + sgst, 2)
            s.add(AccDoc(tenant_id="t1", gstin=MINE, period=day[:7], direction=direction, kind=kind, number=n, doc_date=day, party_name=party, party_gstin=gstin,
                         taxable=taxable, igst=igst, cgst=cgst, sgst=sgst, total=tot, source="app", source_ref=n))
        doc("S-1", "out", "inv", "Acme Traders", BUYER, 1000, igst=180)
        doc("S-2", "out", "inv", "Local Shop", "", 500, cgst=45, sgst=45)
        doc("CN-1", "out", "cn", "Acme Traders", BUYER, 100, igst=18)
        doc("P-1", "in", "bill", "Beta Supplies", "27AABCB1234C1ZX", 2000, cgst=180, sgst=180, total=2361)       # 1 rupee of rounding
        doc("P-2", "in", "bill", "Tax Only Co", "29AABCU9603R1ZX", 1000, total=1180)                            # only a lump tax figure
        s.flush()
        sale = s.query(AccDoc).filter_by(number="S-1").one()
        s.add(AccBankLine(tenant_id="t1", line_hash="b1", date="2026-10-20", narration="UPI/123456789012/ACME", credit=1180, mode="upi", ref="123456789012", status="matched", match_doc_id=sale.id))
        s.add(AccBankLine(tenant_id="t1", line_hash="b2", date="2026-10-21", narration="stray", credit=99, status="open"))
        s.add(AccIntake(tenant_id="t1", gstin=MINE, status="draft", fields=json.dumps({"number": "DRAFT-9", "party_name": "Mystery"})))
        s.commit()
    return book


def test_vouchers_follow_tally_debit_credit_rules_and_use_her_ledger_names(a9):
    vs = {v["number"]: v for v in a9.vouchers("t1", MINE, "2026-10")}
    s1 = vs["S-1"]
    assert s1["type"] == "Sales" and s1["rows"][0] == ("Acme Traders", 1180.0, True) and ("Sales", 1000.0, False) in s1["rows"] and ("Output IGST", 180.0, False) in s1["rows"]
    assert sum(a for _, a, dr in s1["rows"] if dr) == sum(a for _, a, dr in s1["rows"] if not dr)           # every voucher balances
    assert [r for r in vs["S-2"]["rows"] if r[0].startswith("Output")] == [("Output CGST", 45.0, False), ("Output SGST", 45.0, False)]
    cn = vs["CN-1"]
    assert cn["type"] == "Credit Note" and cn["rows"][0][2] is False and ("Sales", 100.0, True) in cn["rows"]      # the mirror image
    p1 = vs["P-1"]
    assert p1["type"] == "Purchase" and p1["rows"][0] == ("Beta Supplies", 2361.0, False) and ("Input CGST", 180.0, True) in p1["rows"] and ("Round Off", 1.0, True) in p1["rows"]
    for v in vs.values():
        assert round(sum(a for _, a, dr in v["rows"] if dr) - sum(a for _, a, dr in v["rows"] if not dr), 2) == 0, v["number"]
    inter = vs["P-2"]
    assert ("Input IGST", 180.0, True) in inter["rows"] and not [r for r in inter["rows"] if r[0] == "Round Off"]      # a lump tax of 180 from another state is IGST, never "round off"
    rcpt = next(v for v in vs.values() if v["type"] == "Receipt")
    assert rcpt["rows"] == [("Bank Account", 1180.0, True), ("Acme Traders", 1180.0, False)] and "123456789012" in rcpt["narration"]
    assert not [v for v in vs.values() if "stray" in v["narration"]]                                            # an unmatched bank line makes no voucher
    a9.set_ledgers("t1", {"sales": "Sales A/c", "bank": "HDFC Current", "evil": "<x>"})
    again = {v["number"]: v for v in a9.vouchers("t1", MINE, "2026-10")}
    assert again["S-1"]["rows"][1][0] == "Sales A/c" and next(v for v in again.values() if v["type"] == "Receipt")["rows"][0][0] == "HDFC Current"


def test_the_tally_xml_is_well_formed_creates_party_ledgers_and_escapes(a9):
    from app.bahi.models import AccDoc
    from app.db import session
    with session() as s:
        s.add(AccDoc(tenant_id="t1", gstin=MINE, period="2026-10", direction="out", kind="inv", number="S-9", doc_date="2026-10-09", party_name="Ram & Sons <Ltd>",
                     party_gstin=BUYER, taxable=100, igst=18, total=118, source="app", source_ref="S-9"))
        s.commit()
    xml = a9.to_xml(a9.vouchers("t1", MINE, "2026-10"))
    dom = minidom.parseString(xml)                                                           # must parse
    assert dom.getElementsByTagName("ENVELOPE") and len(dom.getElementsByTagName("VOUCHER")) >= 6
    assert "Ram &amp; Sons &lt;Ltd&gt;" in xml and "<PARENT>Sundry Debtors</PARENT>" in xml and "<PARENT>Sundry Creditors</PARENT>" in xml
    assert "<DATE>20261005</DATE>" in xml and re.search(r"<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-1180.00</AMOUNT>", xml)


def test_the_pack_has_everything_lists_open_questions_and_is_the_same_zip_twice(a9):
    p = a9.build_pack("t1", MINE, "2026-10")
    z = zipfile.ZipFile(io.BytesIO(a9.pack_bytes("t1", p["id"])[1]))
    names = set(z.namelist())
    assert {"vouchers/tally-vouchers.xml", "vouchers/vouchers.json", "register.csv", "parties.csv", "worksheets/gstr2b.csv", "bank-reconciliation.json",
            "tds-register.csv", "OPEN-QUESTIONS.txt", "README.txt"} <= names
    oq = z.read("OPEN-QUESTIONS.txt").decode()
    assert "DRAFT-9" in oq and "stray" in oq and "not matched" in oq and p["open_questions"] >= 2
    assert "Nothing in this pack was filed or paid" in z.read("README.txt").decode()
    assert len(json.loads(z.read("vouchers/vouchers.json"))) == p["counts"]["vouchers"] == 6
    assert "S-1" in z.read("register.csv").decode()
    again = a9.build_pack("t1", MINE, "2026-10")
    assert again["sha"] == p["sha"] and again["id"] == p["id"] and len(a9.packs("t1", "2026-10")) == 1      # same books -> same pack, one row
    assert a9.packs("other") == []
    with pytest.raises(a9.BookError):
        a9.pack_bytes("other", p["id"])


def test_closing_a_month_needs_confirm_and_the_exact_pack_then_locks_it(a9):
    p = a9.build_pack("t1", MINE, "2026-10")
    with pytest.raises(a9.BookError):
        a9.close_month("t1", p["id"], p["sha"], False)
    with pytest.raises(a9.BookError):
        a9.close_month("t1", p["id"], "stale", True)
    out = a9.close_month("t1", p["id"], p["sha"], True)
    assert out["closed_at"] and out["closed_by"] == "owner"
    from app.bahi import register
    from app.bahi.models import AccPeriod
    from app.db import session
    with session() as s:
        assert register.locked(s, "t1", MINE, "2026-10")
        assert s.query(AccPeriod).filter_by(tenant_id="t1", period="2026-10", state="locked").count() == 1
    with pytest.raises(a9.BookError):
        a9.build_pack("t1", "bad", "2026-1")


def test_wiring(a9):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for route in ("/api/bahi/book/ledgers", "/api/bahi/book/tally.xml", "/api/bahi/pack/build", "/api/bahi/pack\"", "/api/bahi/pack/{pack_id}/download", "/api/bahi/pack/{pack_id}/close"):
        assert route in api
    js = (root / "static/console/bahi.js").read_text()
    assert "capack" in js and "caclose" in js and "pyparty" in js and "Hoola files nothing" in js
