"""v0.59 Padho aur pehchano: OCR, QR / UPI, bills, PDF kaam, same-photo cache, India calendar / money / IFSC / PIN."""
import asyncio
import base64
import io
import json
import os
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

FIX = Path(__file__).parent / "fixtures"
needs_tess = pytest.mark.skipif(not shutil.which("tesseract"), reason="no tesseract binary")


def _text_png(lines, size=(1400, 700), font=None, fs=42):
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(font), fs) if font else ImageFont.load_default(size=fs)
    y = 30
    for line in lines:
        d.text((40, y), line, fill="black", font=f)
        y += int(fs * 1.6)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _qr_png(text, scale=8):
    import segno
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="png", scale=scale, border=4)
    return buf.getvalue()


def _ctx():
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id="c1")


# ---------------------------------------------------------------- OCR
@needs_tess
def test_ocr_reads_an_english_bill_photo(env):
    from app import ocr
    ocr.reset()
    png = _text_png(["MAHARASHTRA STATE ELECTRICITY DISTRIBUTION", "Consumer No: 330012345678",
                     "Bill Amount (Rs.) : 1,234.50", "Due Date: 28-10-2026"])
    r = ocr.read(png, "hinglish")
    assert r and "Consumer" in r["text"] and "1,234.50" in r["text"] and r["good"] and r["conf"] > 60


@needs_tess
def test_ocr_reads_hindi_when_the_model_is_installed(env, monkeypatch):
    from app import ocr
    tess = os.environ.get("HOOLA_TEST_TESSDATA")
    if not tess or not Path(tess, "hin.traineddata").exists():
        pytest.skip("set HOOLA_TEST_TESSDATA to a folder with hin.traineddata")
    monkeypatch.setattr(ocr, "TESSDATA", Path(tess))
    ocr.reset()
    png = _text_png(["बिजली का बिल", "कुल देय राशि 850 रुपये", "अंतिम तिथि 25-10-2026"], font=FIX / "NotoSansDevanagari-Regular.ttf")
    r = ocr.read(png, "hindi")
    assert r and "hin" in r["langs"] and "बिजली" in r["text"] and "850" in r["text"]
    ocr.reset()


def test_ocr_missing_binary_is_quiet(env, monkeypatch):
    from app import ocr
    monkeypatch.setattr(ocr, "_bin", lambda: None)
    assert ocr.read(b"x") is None and ocr.read_pdf(b"x") is None


# ---------------------------------------------------------------- QR / UPI
def test_upi_qr_says_who_gets_the_money_and_warns(env):
    from app import qrread
    codes = qrread.scan(_qr_png("upi://pay?pa=refund.desk@ybl&pn=Customer%20Care&am=4999&tn=Refund%20cashback%20receive&cu=INR"))
    assert len(codes) == 1
    c = codes[0]
    assert c["kind"] == "upi" and c["payee_vpa"] == "refund.desk@ybl" and c["amount"] == 4999.0 and c["never_pays"]
    assert c["risky"] and any("thagi" in w for w in c["warnings"]) and any("JAAYENGE" in w for w in c["warnings"])
    assert "sirf JAATE" in c["say"]
    shop = qrread.describe("upi://pay?pa=ramstores@okaxis&pn=Ram%20Stores&mc=5411")
    assert shop["kind"] == "upi" and not shop["risky"] and shop["merchant"] and shop["amount"] is None
    auto = qrread.describe("upi://mandate?pa=x@ybl&pn=X&am=199&recur=MONTHLY")
    assert auto["risky"] and any("AUTOPAY" in w for w in auto["warnings"])


def test_einvoice_qr_and_other_codes(env):
    from app import qrread
    data = {"SellerGstin": "27AAPFU0939F1ZV", "BuyerGstin": "29AAACR5055K1Z4", "DocNo": "INV/77", "DocTyp": "INV",
            "DocDt": "05/10/2026", "TotInvVal": 11800, "ItemCnt": 2, "MainHsnCode": "8517", "Irn": "a" * 64}
    body = base64.urlsafe_b64encode(json.dumps({"data": json.dumps(data), "iss": "NIC"}).encode()).decode().rstrip("=")
    token = "eyJhbGciOiJSUzI1NiJ9." + body + "." + "s" * 300
    c = qrread.describe(token)
    assert c["kind"] == "gst_invoice" and c["invoice"]["doc_no"] == "INV/77" and c["invoice"]["seller_gstin_valid"]
    assert qrread.describe("https://example.org/x")["kind"] == "link"
    assert qrread.describe("8901234567890", "EAN13")["kind"] == "product"
    w = qrread.describe("WIFI:S:Ghar;T:WPA;P:secret123;;")
    assert w["kind"] == "wifi" and "secret123" not in json.dumps(w)


def test_chat_upload_with_upi_qr_tells_the_agent(env):
    from app import chatfiles
    out = chatfiles.store("default", "scan.png", _qr_png("upi://pay?pa=lucky.draw@ibl&pn=Prize&am=2000&tn=lottery%20winner"))
    assert out["codes"][0]["kind"] == "upi"
    ctx = chatfiles.context("default", [out["file_id"]])
    assert "QR/barcode found" in ctx and "lucky.draw@ibl" in ctx and "never pay" in ctx


# ---------------------------------------------------------------- bills
def test_bill_templates_pick_the_biller():
    from app import billparse
    b = billparse.parse("MSEDCL Mahavitaran\nConsumer No: 330012345678\nBill Date: 05-10-2026 Bill No: 2610-55443\n"
                        "Bill Amount (Rs.) : 1,234.50\nDue Date: 20-11-2026\n")
    assert b["template"] == "msedcl" and b["kind"] == "electricity" and b["amount"] == 1234.5
    assert b["due_date"] == "2026-11-20" and b["consumer_no"] == "330012345678" and "reminder" in b["next"]
    j = billparse.parse("Reliance Jio Infocomm  Bill Number: JIO123456  Amount Payable Rs. 699.00 Pay by 15/11/2026")
    assert j["template"] == "jio" and j["amount"] == 699.0 and j["due_date"] == "2026-11-15"
    g = billparse.parse("Shree Ganesh Traders Invoice No: SGT/221 Total Payable ₹ 12,300 Due date: 01/12/2026")
    assert g["template"] == "generic" and g["amount"] == 12300.0
    assert billparse.parse("Kal milte hain, chai peeyenge") is None


@needs_tess
def test_file_read_photo_gives_text_bill_and_qr_without_vision(env, monkeypatch):
    from app import chatfiles
    from app.agent.file_tools import file_read
    from app.net import media
    called = []
    monkeypatch.setattr(media, "_claude_see", lambda *a, **k: called.append(1) or "photo")
    im = Image.open(io.BytesIO(_text_png(["BSNL Bharat Sanchar Nigam Limited", "Bill No: KL889911",
                                          "Amount Payable Rs. 589.00", "Due Date: 28-11-2026"], size=(1400, 900))))
    qr = Image.open(io.BytesIO(_qr_png("upi://pay?pa=bsnl.billdesk@hdfcbank&pn=BSNL", scale=5)))
    im.paste(qr, (1000, 480))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    f = chatfiles.store("default", "bill.png", buf.getvalue())
    out = asyncio.run(file_read(_ctx(), f["file_id"]))
    assert "589.00" in out["text"] and out["ocr"]["good"]
    assert out["bill"]["template"] == "bsnl" and out["bill"]["amount"] == 589.0
    assert out["codes"][0]["payee_vpa"] == "bsnl.billdesk@hdfcbank"
    assert not called                                   # our own OCR was enough: no paid vision call
    asyncio.run(file_read(_ctx(), f["file_id"], look=True))
    assert called


def test_same_photo_is_seen_once(env, monkeypatch):
    from app.net import media
    calls = []
    monkeypatch.setattr(media, "_claude_see", lambda *a, **k: calls.append(1) or "Ek lal board")
    png = _text_png(["Ram Stores"], size=(500, 300))
    info = media.analyse("a.png", "image/png", png)
    assert media.understand("default", info, "a.png", "image/png", png) == "Ek lal board"
    im = Image.open(io.BytesIO(png)).convert("RGB")
    jpg = io.BytesIO()
    im.save(jpg, "JPEG", quality=70)                    # WhatsApp re-compresses: still the same picture
    assert media.understand("default", info, "a.jpg", "image/jpeg", jpg.getvalue()) == "Ek lal board"
    assert len(calls) == 1
    other = _text_png(["Shyam Medical", "24 x 7"], size=(500, 300))
    media.understand("default", media.analyse("b.png", "image/png", other), "b.png", "image/png", other)
    assert len(calls) == 2
    assert media.understand("other-owner", info, "a.png", "image/png", png) and len(calls) == 3   # never shared


# ---------------------------------------------------------------- PDFs
def _pdf(title, pages=1):
    from app.net import media
    return media.make_pdf(title, ("Line of text\n" * 40 + "\f") * pages)


def test_pdf_merge_pages_rotate_and_info(env):
    from app import pdftools
    a, b = _pdf("A"), _pdf("B")
    m = pdftools.merge([("a.pdf", a), ("b.pdf", b)])
    n = pdftools.info(m)["pages"]
    assert n == pdftools.info(a)["pages"] + pdftools.info(b)["pages"]
    one = pdftools.pick(m, "1")
    assert pdftools.info(one)["pages"] == 1
    assert pdftools.pages_from("2-3, 1, 9", 4) == [1, 2, 0]
    with pytest.raises(pdftools.PdfError):
        pdftools.pages_from("x", 3)
    r = pdftools.rotate(one, 90)
    import pikepdf
    rp = pikepdf.open(io.BytesIO(r))
    assert int(rp.pages[0].Rotate) == 90
    with pytest.raises(pdftools.PdfError):
        pdftools.merge([("a.pdf", a)])


def test_pdf_smaller_shrinks_big_photos(env):
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from app import pdftools
    import random
    random.seed(1)
    im = Image.effect_noise((2600, 2000), 60).convert("RGB")
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawImage(ImageReader(im), 20, 20, width=550, height=420)
    c.save()
    big = buf.getvalue()
    small = pdftools.shrink(big)
    assert len(small) < len(big) * 0.7 and pdftools.info(small)["pages"] == 1


def test_locked_pdf_is_never_opened(env):
    import pikepdf
    from app import pdftools
    src = pikepdf.open(io.BytesIO(_pdf("Secret")))
    buf = io.BytesIO()
    src.save(buf, encryption=pikepdf.Encryption(owner="o", user="u"))
    with pytest.raises(pdftools.PdfError) as e:
        pdftools.info(buf.getvalue())
    assert "password chat mein mat" in str(e.value)


def test_pdf_signature_check(env, tmp_path):
    pytest.importorskip("pyhanko")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers
    from app import pdftools
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Hoola Test Signer")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(7).not_valid_before(now).not_valid_after(now.replace(year=now.year + 1))
            .sign(key, hashes.SHA256()))
    (tmp_path / "k.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                       serialization.NoEncryption()))
    (tmp_path / "c.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    signer = signers.SimpleSigner.load(str(tmp_path / "k.pem"), str(tmp_path / "c.pem"))
    out = io.BytesIO()
    signers.sign_pdf(IncrementalPdfFileWriter(io.BytesIO(_pdf("Certificate"))),
                     signers.PdfSignatureMetadata(field_name="Sig1"), signer=signer, output=out)
    v = pdftools.verify(out.getvalue())
    s = v["signatures"][0]
    assert s["intact"] and "Hoola Test Signer" in s["signer"] and not s["trusted"] and "nahi badli" in v["say"]
    tampered = bytearray(out.getvalue())
    i = tampered.find(b"Line of text")
    tampered[i:i + 4] = b"LINE"
    v2 = pdftools.verify(bytes(tampered))
    assert "badli gayi" in v2["say"]
    assert pdftools.verify(_pdf("plain"))["signatures"] == []


def test_pdf_tool_makes_a_new_file(env):
    from app.agent.tools import HANDLERS
    from app.mailbox import service as ms
    a = ms.store_bytes("default", "a.pdf", _pdf("A"), "mail")
    b = ms.store_bytes("default", "b.pdf", _pdf("B"), "mail")
    out = asyncio.run(HANDLERS["pdf_tools"](_ctx(), action="merge", file_ids=[a.id, b.id], name="Dono"))
    assert out["file_id"] and out["name"] == "Dono.pdf" and out["pages"] >= 2
    i = asyncio.run(HANDLERS["pdf_tools"](_ctx(), action="info", file_id=out["file_id"]))
    assert i["pages"] == out["pages"]


# ---------------------------------------------------------------- India
def test_money_words_and_format():
    from app.india import money as m
    assert m.words(225000) == "do lakh pachchees hazaar"
    assert m.words(1234567, "hi") == "बारह लाख चौंतीस हज़ार पाँच सौ सड़सठ"
    assert m.words(1500000000, "en") == "one hundred fifty crore"
    assert m.rupees_words(1234.05, "en") == "Rupees one thousand two hundred thirty-four and five paise only"
    assert m.inr(1234567.5) == "₹12,34,567.50" and m.inr(999) == "₹999" and m.short(12000000) == "₹1.2 crore"
    assert m.gstin_ok("27AAPFU0939F1ZV") and not m.gstin_ok("27AAPFU0939F1ZW") and not m.gstin_ok("99AAPFU0939F1ZV")
    assert m.gstin_info("27AAPFU0939F1ZV")["state"] == "Maharashtra"


def test_panchang_matches_real_moon_phases():
    from app.india import days as D
    for when, phase in (("2026-01-03T10:03", 180), ("2026-01-18T19:52", 0), ("2026-03-03T11:38", 180),
                        ("2025-10-21T12:25", 0)):
        e = D.elongation(datetime.fromisoformat(when).replace(tzinfo=timezone.utc))
        assert abs((e - phase + 180) % 360 - 180) < 0.05
    diwali = D.panchang(date(2025, 10, 21), "pune")
    assert diwali["tithi"] == "Amavasya" and diwali["month_amanta"] == "Ashwin" and diwali["tithi_ends"].startswith("21 Oct 17:")
    nxt = D.next_tithi("ekadashi", date(2026, 10, 20), 4)
    assert [x["date"] for x in nxt] == ["2026-10-22", "2026-11-05", "2026-11-20", "2026-12-04"]
    assert nxt[2]["kshaya"] and nxt[2]["tithi"] == "Ekadashi"
    sr = D.sunrise(date(2026, 10, 20), 18.52, 73.86)
    assert (sr.hour, sr.minute // 10) == (6, 2)


def test_holidays_and_bank_day():
    from app.india import days as D
    oct26 = D.holidays_for(2026, "Maharashtra", month=10)
    assert any(h["name"] == "Dussehra" and h["date"] == "2026-10-20" for h in oct26)
    assert D.state_code("", "pune") == "MH" and D.state_code("tamil nadu") == "TN"
    sun = D.day_info(date(2026, 10, 25), city="pune")
    assert sun["bank_closed_likely"] and sun["panchang"]["vaar"] == "Ravivar"
    second_sat = D.day_info(date(2026, 11, 14), city="pune")
    assert second_sat["bank_closed_likely"]
    assert not D.day_info(date(2026, 11, 13), city="pune")["bank_closed_likely"]


def test_ifsc_and_pincode_offline():
    from app.india import ifsc, pincode
    assert ifsc.valid("HDFC0000001") and ifsc.valid("SBIN0000001") and not ifsc.valid("HDFC000001") and not ifsc.valid("ZZZZ0000001")
    r = ifsc.lookup("hdfc0000001")
    assert r["valid"] and r["bank"] == "HDFC Bank"
    assert "11 akshar" in ifsc.lookup("123")["say"]
    assert pincode.valid("444101") and pincode.valid("411001") and not pincode.valid("000000") and not pincode.valid("100000")
    assert pincode.find_in("Khanapur Ves, Akot 444 101, Akola") == ["444101"]


def test_ifsc_branch_details_from_the_release(env, monkeypatch):
    import httpx
    import tarfile
    from app.india import ifsc
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        body = json.dumps({"HDFC0000001": {"BANK": "HDFC Bank", "BRANCH": "NARIMAN POINT", "CITY": "MUMBAI", "UPI": True}}).encode()
        ti = tarfile.TarInfo("by-bank/HDFC.json")
        ti.size = len(body)
        tf.addfile(ti, io.BytesIO(body))
        evil = tarfile.TarInfo("../../evil.json")
        evil.size = 2
        tf.addfile(evil, io.BytesIO(b"{}"))
    monkeypatch.setattr(ifsc, "_transport", httpx.MockTransport(lambda req: httpx.Response(200, content=buf.getvalue())))
    assert ifsc.refresh() == 1 and not Path("evil.json").exists()
    r = ifsc.lookup("HDFC0000001")
    assert r["branch"] == "NARIMAN POINT" and r["upi"] is True


def test_india_info_tool(env):
    from app.agent.tools import HANDLERS, TOOLS
    names = {t["name"] for t in TOOLS}
    assert {"india_info", "pdf_tools"} <= names
    run = lambda **a: asyncio.run(HANDLERS["india_info"](_ctx(), **a))
    assert run(action="words", amount=225000)["words"].startswith("do lakh pachchees hazaar")
    assert run(action="gstin", code="27AAPFU0939F1ZV")["valid"]
    assert run(action="pincode", code="444101")["valid"]
    assert run(action="next", what="purnima", date="2026-10-01", count=2)["dates"][0]["date"] == "2026-10-26"
    assert any(h["name"] == "Republic Day" and h["kind"] == "public"
               for h in run(action="holidays", year=2026, month=1, city="pune")["holidays"])
    assert run(action="panchang", date="2025-10-21", city="pune")["tithi"] == "Amavasya"
    from app.voice import VOICE_TOOL_NAMES
    from app.employee.roles import kind_of
    assert "india_info" in VOICE_TOOL_NAMES and kind_of("india_info") == "read"
