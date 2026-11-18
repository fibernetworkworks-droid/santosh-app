"""v0.846 BAHI A7 - bank + UPI reconciliation, stored: import, read narrations, propose matches with reasons, confirm, learn payers, reconcile."""
import pytest

CSV = """Date,Narration,Debit,Credit,Balance
01-10-2026,UPI/123456789012/ACME TRADERS/acme@okhdfc/Payment,,11800.00,111800.00
03-10-2026,NEFT-N123456789ABCD-BETA SUPPLIES-BILL/778,5900.00,,105900.00
04-10-2026,UPI/222233334444/RAJ KUMAR/raj@ybl/ok,,2500.00,108400.00
05-10-2026,CHQ NO 004567 CLG,3000.00,,105400.00
06-10-2026,BANK CHARGES SMS ALERT,50.00,,105350.00
06-10-2026,UPI/555566667777/PRIYA/priya@okaxis/hi,,700.00,106050.00
06-10-2026,UPI/555566667777/PRIYA/priya@okaxis/hi,,700.00,106750.00
"""
MINE = "27ADCPI1932N1ZH"


@pytest.fixture
def a7(env):
    from app.bahi import bank
    from app.bahi.models import AccDoc, ensure_tables
    from app.db import session
    ensure_tables()
    with session() as s:
        def doc(n, d, party, total, direction="out", kind="inv"):
            s.add(AccDoc(tenant_id="t1", gstin=MINE, period=d[:7], direction=direction, kind=kind, number=n, doc_date=d, party_name=party,
                         total=total, taxable=total / 1.18, source="app", source_ref=n))
        doc("INV-101", "2026-09-28", "Acme Traders Pvt Ltd", 11800)       # name + amount (and UPI id learnable)
        doc("INV-102", "2026-09-30", "Raj Kumar", 2500)                   # one fits
        doc("INV-103", "2026-09-30", "Somebody Else", 2500)               # a second 2500 sale - ambiguity for any other 2500
        doc("BILL-778", "2026-09-25", "Beta Supplies", 5900, "in", "bill")  # invoice number inside the NEFT narration
        doc("INV-104", "2026-10-02", "Gamma", 9999)                       # books-only
        s.commit()
    return bank


def test_narrations_are_read_in_the_common_styles(a7):
    r = a7.read_narration
    assert r("UPI/123456789012/ACME TRADERS/acme@okhdfc/Payment") | {} == {"mode": "upi", "ref": "123456789012", "payer": "ACME TRADERS", "vpa": "acme@okhdfc"}
    h = r("UPI-RAJ KUMAR-raj@ybl-YESB0YBLUPI-409912345678-Payment")
    assert h["mode"] == "upi" and h["ref"] == "409912345678" and h["payer"] == "RAJ KUMAR" and h["vpa"] == "raj@ybl"
    n = r("NEFT-N123456789ABCD-BETA SUPPLIES-BILL/778")
    assert n["mode"] == "neft" and n["ref"] == "N123456789ABCD" and n["payer"] == "BETA SUPPLIES"
    assert r("CHQ NO 004567 CLG") == {"mode": "cheque", "ref": "004567", "payer": "", "vpa": ""}
    assert r("BANK CHARGES SMS ALERT")["mode"] == "other"


def test_import_is_stored_once_and_identical_lines_on_one_day_are_both_kept(a7):
    r = a7.import_text("t1", "HDFC current", "stmt.csv", CSV.encode())
    assert r["read"] == 7 and r["added"] == 7 and r["from"] == "2026-10-01" and r["to"] == "2026-10-06"
    again = a7.import_text("t1", "HDFC current", "stmt.csv", CSV.encode())
    assert again["added"] == 0 and again["already_there"] == 7
    assert len(a7.lines("t1")) == 7
    assert a7.lines("other") == []
    with pytest.raises(a7.BankError):
        a7.import_text("t1", "x", "bad.csv", b"hello,world\n1,2\n")


def test_matches_are_proposals_with_reasons_and_only_confirmed_ones_link(a7):
    a7.import_text("t1", "HDFC", "s.csv", CSV.encode())
    m = a7.match("t1")
    assert m["proposed"] == 3
    by = {l["narration"][:20]: l for l in a7.lines("t1")}
    acme = by["UPI/123456789012/ACM"]
    assert acme["status"] == "proposed" and acme["match"]["kind"] == "name_amount" and "Acme" in acme["match"]["reason"] and acme["match"]["confidence"] == 0.85
    neft = by["NEFT-N123456789ABCD-"]
    assert neft["match"]["kind"] == "invoice_no" and neft["match"]["confidence"] >= 0.95 and "778" in neft["match"]["reason"]
    raj = by["UPI/222233334444/RAJ"]
    assert raj["match"]["kind"] == "name_amount"                     # the name picks Raj Kumar's out of two 2500 sales
    assert by["CHQ NO 004567 CLG"[:20]]["status"] == "open" and by["BANK CHARGES SMS ALERT"[:20]]["category"] == "fees"
    assert [l for l in a7.lines("t1") if l["status"] == "matched"] == []      # nothing linked without her
    assert a7.confirm("t1", [acme["id"], neft["id"]], min_conf=0.9)["matched"] == 1      # only the 0.97 one passes the bar
    assert a7.confirm("t1", [acme["id"]])["matched"] == 1
    assert a7.unmatch("t1", acme["id"])["status"] == "open"


def test_a_confirmed_payer_is_recognised_next_time(a7):
    a7.import_text("t1", "HDFC", "s.csv", CSV.encode())
    a7.match("t1")
    acme = next(l for l in a7.lines("t1") if l["vpa"] == "acme@okhdfc")
    a7.confirm("t1", [acme["id"]])
    from app.bahi.models import AccDoc
    from app.db import session
    with session() as s:
        s.add(AccDoc(tenant_id="t1", gstin=MINE, period="2026-10", direction="out", kind="inv", number="INV-200", doc_date="2026-10-10", party_name="Acme Traders Pvt Ltd",
                     total=4000, source="app", source_ref="INV-200"))
        s.commit()
    a7.import_text("t1", "HDFC", "s2.csv", b"Date,Narration,Debit,Credit,Balance\n20-10-2026,UPI/999900001111/SOMEONE ELSE/acme@okhdfc/pay,,4000.00,0\n")
    a7.match("t1")
    nxt = next(l for l in a7.lines("t1") if l["ref"] == "999900001111")
    assert nxt["match"]["kind"] == "known_payer" and "confirmed earlier" in nxt["match"]["reason"]


def test_settlement_split_categorise_and_the_stored_month_statement(a7):
    a7.import_text("t1", "HDFC", "s.csv", CSV.encode() + b"08-10-2026,RAZORPAY SETTLEMENT UTR9988776655,,9764.00,0\n")
    assert a7.attach_settlements("t1", [{"id": "setl_1", "amount": 9764.00, "fees": 200.0, "tax": 36.0, "utr": "UTR9988776655"}])["attached"] == 1
    st = next(l for l in a7.lines("t1") if "RAZORPAY" in l["narration"])
    assert st["settlement"]["gross"] == 10000.0 and st["settlement"]["fees"] == 200.0 and st["settlement"]["gst_on_fees"] == 36.0 and st["status"] == "matched"
    op = next(l for l in a7.lines("t1") if l["mode"] == "cheque")
    assert a7.categorise("t1", op["id"], "Vendor Cheque!")["category"] == "vendor cheque"
    a7.match("t1")
    acme = next(l for l in a7.lines("t1") if l["vpa"] == "acme@okhdfc")
    a7.confirm("t1", [acme["id"]])
    rec = a7.reconcile("t1", "2026-10")
    assert rec["matched"]["count"] >= 2 and rec["lines"] == 8 and rec["credits"] > 0
    assert any(b["narration"].startswith("CHQ") for b in rec["bank_only"]) and rec["uncleared_cheques"]
    assert any(b["number"] == "INV-104" and "receivable" in b["side"] for b in rec["books_only"])
    assert a7.stored("t1", "2026-10")["lines"] == 8
    with pytest.raises(a7.BankError):
        a7.reconcile("t1", "2026-01")
    with pytest.raises(a7.BankError):
        a7.stored("t1", "2026-05")


def test_mt940_and_a_locked_pdf_password_is_never_kept(a7):
    mt = (":20:STMT\n:25:123/456\n:60F:C261001INR100000,00\n:61:2610050105C1500,00NTRFNONREF//1\n:86:UPI/333344445555/DEV/dev@upi/pay\n"
          ":61:2610060106D400,50NCHQ004568\n:86:CHQ 004568\n:62F:C261006INR101099,50\n")
    r = a7.import_text("t1", "SBI", "s.sta", mt.encode())
    assert r["added"] == 2
    ls = {l["ref"]: l for l in a7.lines("t1")}
    assert ls["333344445555"]["credit"] == 1500.0 and ls["333344445555"]["mode"] == "upi"
    import io
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(200, 200)
    w.encrypt("s3cret")
    buf = io.BytesIO()
    w.write(buf)
    with pytest.raises(a7.BankError) as e:
        a7.import_text("t1", "x", "locked.pdf", buf.getvalue())
    assert "password" in str(e.value).lower()
    with pytest.raises(a7.BankError) as e:
        a7.import_text("t1", "x", "locked.pdf", buf.getvalue(), "wrong")
    assert "did not open" in str(e.value)
    from app.bahi.models import AccBankLine
    from app.db import session
    with session() as s:
        assert "s3cret" not in " ".join(str(getattr(l, c.name)) for l in s.query(AccBankLine).all() for c in AccBankLine.__table__.columns)


def test_wiring(a7):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for r in ("import", "match", "lines", "confirm", "unmatch", "categorise", "settlements", "reconcile"):
        assert f"/api/bahi/bank/{r}" in api
    js = (root / "static/console/bahi.js").read_text()
    assert "kconfirm" in js and "krecon" in js and "kimp" in js
