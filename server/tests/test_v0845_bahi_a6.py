"""v0.844 BAHI A6 - bills in, checked: read -> cross-checked DRAFT -> register only on her tap. No network, no OCR needed (text path)."""
import pytest

MINE = "27ADCPI1932N1ZH"
SUP = "27AAGCB1286Q1ZB"     # replaced below by a check-digit-valid GSTIN
GOOD = """ACME SUPPLIES PVT LTD
Tax Invoice
GSTIN: {sup}
Invoice No: ACM/26/0042
Invoice Date: 05-10-2026
Bill To: Meghana Ingle  GSTIN: {mine}
HSN 8471  Qty 2
Taxable Value 10,000.00
CGST @9% 900.00
SGST @9% 900.00
Grand Total 11,800.00
"""


def _valid_gstin(prefix14: str) -> str:
    from app.appmaker.gst import valid_gstin
    import string
    for ch in string.digits + string.ascii_uppercase:
        if valid_gstin(prefix14 + ch):
            return prefix14 + ch
    raise AssertionError("no check char")


@pytest.fixture
def a6(env, monkeypatch):
    from app.bahi import connect, intake
    sup = _valid_gstin("27AABCA1234B1Z")
    monkeypatch.setattr(connect, "supplier_check", lambda tenant, g, filing=True: {"status": "active", "source": "API Setu (GSTN)", "notes": []})
    yield intake, sup


def txt(sup, **kw):
    t = GOOD.format(sup=sup, mine=MINE)
    for a, b in kw.items():
        t = t.replace(*b) if isinstance(b, tuple) else t
    return t


def test_a_clean_bill_is_read_and_every_check_passes(a6):
    intake, sup = a6
    r = intake.intake_text("t1", MINE, txt(sup))
    f = r["fields"]
    assert f["supplier_gstin"] == sup and f["buyer_gstin"] == MINE and f["number"] == "ACM/26/0042" and f["date"] == "2026-10-05"
    assert (f["taxable"], f["cgst"], f["sgst"], f["total"]) == (10000.0, 900.0, 900.0, 11800.0) and "8471" in f["hsn"] and f["party_name"].startswith("ACME")
    assert r["state"] == "ready" and r["confidence"] >= 0.9 and not [c for c in r["checks"] if c["level"] == "error"]
    assert intake.intake_text("t1", MINE, txt(sup))["already"]            # the same text twice makes one draft


def test_arithmetic_wrong_gstin_and_state_mismatch_are_caught(a6):
    intake, sup = a6
    bad = intake.intake_text("t1", MINE, txt(sup, a=("11,800.00", "11,900.00")))
    assert any("difference Rs -100" in c["text"] for c in bad["checks"]) and bad["state"] == "needs_you" and bad["confidence"] < 0.9
    other = _valid_gstin("29AABCB1234C1Z")
    wrong = intake.intake_text("t1", MINE, txt(sup).replace(MINE, other))
    assert any("addressed to GSTIN" in c["text"] and "cannot take credit" in c["text"] for c in wrong["checks"])
    inter = intake.intake_text("t1", MINE, txt(_valid_gstin("29AABCA1234B1Z"), a=("x", "x")).replace("INV", "INV").replace("ACM/26/0042", "ACM/26/0043"))
    assert any("another state" in c["text"] and "IGST" in c["text"] for c in inter["checks"])
    ugly = intake.intake_text("t1", MINE, txt(sup).replace("SGST @9% 900.00", "SGST @9% 700.00").replace("ACM/26/0042", "ACM/26/0044"))
    assert any("CGST" in c["text"] and "should be equal" in c["text"] for c in ugly["checks"])


def test_a_cancelled_supplier_and_a_bad_check_digit_block_credit(a6, monkeypatch):
    intake, sup = a6
    from app.bahi import connect
    monkeypatch.setattr(connect, "supplier_check", lambda tenant, g, filing=True: {"status": "cancelled", "source": "API Setu (GSTN)", "notes": []})
    r = intake.intake_text("t1", MINE, txt(sup))
    assert any("cancelled" in c["text"] and "not allowed" in c["text"] for c in r["checks"])
    r2 = intake.intake_text("t1", MINE, txt(sup).replace(sup, sup[:-1] + ("0" if sup[-1] != "0" else "1")).replace("ACM/26/0042", "ACM/26/0099"))
    assert any("check digit" in c["text"] for c in r2["checks"])


def test_confirm_needs_the_errors_fixed_or_accepted_and_only_then_enters_the_register(a6):
    intake, sup = a6
    from app.bahi.models import AccDoc
    from app.db import session
    r = intake.intake_text("t1", MINE, txt(sup, a=("11,800.00", "11,900.00")))
    with session() as s:
        assert s.query(AccDoc).count() == 0                                     # a draft is not in the register
    with pytest.raises(intake.IntakeError) as e:
        intake.confirm("t1", r["id"], {})
    assert "Fix first" in str(e.value)
    ok = intake.confirm("t1", r["id"], {"total": "11800"})
    assert ok["status"] == "confirmed" and ok["doc_id"]
    with session() as s:
        d = s.get(AccDoc, ok["doc_id"])
        assert d.direction == "in" and d.source == "intake" and d.party_gstin == sup and d.total == 11800 and d.cgst == 900 and d.gstin == MINE
        assert "every check passed" in d.reason
    with pytest.raises(intake.IntakeError):
        intake.confirm("t1", r["id"], {})                                       # not twice
    # the same bill again is now a duplicate of what is held
    again = intake.intake_text("t1", MINE, txt(sup) + " ")
    assert any("already in your register" in c["text"] for c in again["checks"])
    forced = intake.confirm("t1", again["id"], {}, accept_errors=True)
    assert forced["status"] == "confirmed"
    with session() as s:
        assert "accepted by you" in s.get(AccDoc, forced["doc_id"]).reason
    assert intake.reject("t1", intake.intake_text("t1", MINE, txt(sup).replace("ACM/26/0042", "ACM/26/0050"))["id"])["status"] == "rejected"
    assert intake.listing("t1", "draft") == [] or all(x["status"] == "draft" for x in intake.listing("t1", "draft"))


def test_other_tenants_cannot_touch_a_draft_and_bad_input_is_refused(a6):
    intake, sup = a6
    r = intake.intake_text("t1", MINE, txt(sup))
    with pytest.raises(intake.IntakeError):
        intake.confirm("t2", r["id"], {})
    with pytest.raises(intake.IntakeError):
        intake.intake_text("t1", "27ADCPI1932N1ZX", txt(sup))
    with pytest.raises(intake.IntakeError):
        intake.intake_text("t1", MINE, "too short")


def test_wiring_and_the_register_sync_leaves_intake_rows_alone(a6):
    intake, sup = a6
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for route in ("/api/bahi/bills/intake", "/api/bahi/bills\"", "/api/bahi/bills/{bill_id}/confirm", "/api/bahi/bills/{bill_id}/reject"):
        assert route in api
    js = (root / "static/console/bahi.js").read_text()
    assert "blconfirm" in js and "accept_errors: true" in js
    r = intake.intake_text("t1", MINE, txt(sup))
    ok = intake.confirm("t1", r["id"], {})
    from app.bahi import register
    register.sync("t1", months=["2026-10"])                                       # reads the other engines; must not mark our row gone
    from app.bahi.models import AccDoc
    from app.db import session
    with session() as s:
        assert s.get(AccDoc, ok["doc_id"]).status == "confirmed"
