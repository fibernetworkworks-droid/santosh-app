"""Shikayat Sahayak (complaint handler): sector deadlines, logging with proof (EXIF / GPS / PDF metadata stripped), tracking
and reminders, closure checklist, polite closing drafts that never promise unapproved money, compensation only on her tap
(hash + fingerprint), repeat customer / product patterns, reopen, tickets, register Excel, customer-safe WhatsApp tools, API."""
import asyncio
import base64
import io
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.shikayat.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def sk(env, monkeypatch, tmp_path):
    from app.shikayat import service as S
    monkeypatch.setattr(S, "DATA_ROOT", tmp_path / "shikayat")
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")          # no model: templates
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    notes = []
    monkeypatch.setattr(S, "_note", lambda tenant, text, conv="": notes.append(text))
    S.events, S.notes = events, notes
    return S


def _jpeg_with_gps() -> bytes:
    from PIL import Image
    img = Image.new("RGB", (64, 48), (200, 30, 30))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"                 # Make
    exif[0x8825] = {1: "N", 2: (18.0, 31.0, 12.0), 3: "E", 4: (73.0, 51.0, 0.0)}   # GPS IFD
    out = io.BytesIO()
    img.save(out, "JPEG", exif=exif)
    return out.getvalue()


def _png_with_text() -> bytes:
    from PIL import Image, PngImagePlugin
    img = Image.new("RGB", (40, 40), (10, 200, 10))
    info = PngImagePlugin.PngInfo()
    info.add_text("Location", "Akot 444101")
    out = io.BytesIO()
    img.save(out, "PNG", pnginfo=info)
    return out.getvalue()


def _pdf_with_author() -> bytes:
    import pikepdf
    pdf = pikepdf.new()
    pdf.add_blank_page()
    with pdf.open_metadata() as m:
        m["dc:creator"] = ["Secret Person"]
    pdf.docinfo["/Author"] = "Secret Person"
    out = io.BytesIO()
    pdf.save(out)
    return out.getvalue()


def test_rules():
    from app.shikayat import rules as R
    t0 = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)
    d = R.deadlines(t0, "ecommerce")
    assert d["ack_by"] == t0 + timedelta(hours=48) and d["due_at"] == t0 + timedelta(days=30)
    assert R.deadlines(t0, "insurance")["due_at"] == t0 + timedelta(days=14)
    assert R.deadlines(t0, "electricity")["due_at"] == t0 + timedelta(days=45)
    assert R.deadlines(t0, "securities")["due_at"] == t0 + timedelta(days=21)
    capped = R.deadlines(t0, "bank", resolve_days=60)                      # longer than RBI's 30: capped, said
    assert capped["due_at"] == t0 + timedelta(days=30) and capped["notes"]
    assert R.deadlines(t0, "general", resolve_days=60)["due_at"] == t0 + timedelta(days=60)   # no regulator: her choice
    assert R.deadlines(t0, "bank", resolve_days=7)["due_at"] == t0 + timedelta(days=7)        # shorter is always fine
    assert R.deadlines(t0, "general", severity="urgent")["ack_by"] == t0 + timedelta(hours=4)
    assert R.norm_sector("broadband FTTH") == "telecom" and R.norm_sector("bima agent") == "insurance"
    assert "product_defect" in R.guess_causes("geyser 3 din mein band ho gaya, kaam nahi kar raha")
    assert R.guess_severity("current laga bachche ko")[0] == "urgent"
    sev, fl = R.guess_severity("main consumer court jaunga")
    assert sev == "high" and "legal_threat" in fl
    txt, hit = R.scrub("mera card 4111 1111 1111 1111 hai aur OTP 482913 aaya")
    assert hit and "4111" not in txt and "482913" not in txt
    assert R.commission_for(40_00_000) == "District Commission" and R.commission_for(1_50_00_000) == "State Commission"
    assert R.commission_for(3_00_00_000) == "National Commission"
    from datetime import date
    assert R.limitation(date(2026, 10, 23)) == date(2028, 10, 23)
    assert "RBI Ombudsman" in R.route_line("bank") and "Insurance Ombudsman" in R.route_line("insurance")


def test_log_with_proof_metadata_stripped(sk):
    from PIL import Image
    S = sk
    out = S.log_complaint(T, "Mixer 2 din mein kharab ho gaya, motor se dhuan nahi par band. Card 4111 1111 1111 1111 se liya",
                          customer="Ramesh Patil", phone="+91 98900 11111", channel="whatsapp", product="Bajaj Mixer 750W", amount=3200)
    v = out["case"]
    assert v["number"] == "SH-0001" and v["phone"] == "9890011111" and "4111" not in v["text"]
    assert "product_defect" in v["causes"] and v["stage"] == "new" and "Pavti" in out["say"]
    assert S.events[-1][0] == "shikayat_case"
    # photo with GPS: re-encoded, no EXIF left
    p = S.add_proof(T, "SH-0001", _jpeg_with_gps(), "IMG_2026.jpg")
    assert p["kind"] == "photo" and p["cleaned"]
    path, mime = S.proof_file(T, p["id"])
    img = Image.open(path)
    assert mime == "image/jpeg" and len(img.getexif()) == 0 and b"GPS" not in path.read_bytes() and b"PhoneMaker" not in path.read_bytes()
    # screenshot PNG: text chunk gone
    q = S.add_proof(T, "SH-0001", _png_with_text(), "Screenshot_123.png", stage="complaint")
    qp, _ = S.proof_file(T, q["id"])
    assert q["kind"] == "screenshot" and b"Akot" not in qp.read_bytes() and Image.open(qp).size == (40, 40)
    # PDF: author / XMP removed
    d = S.add_proof(T, "SH-0001", _pdf_with_author(), "bill.pdf")
    dp, _ = S.proof_file(T, d["id"])
    assert d["kind"] == "doc" and d["cleaned"] and b"Secret Person" not in dp.read_bytes()
    with pytest.raises(S.ShikayatError):
        S.add_proof(T, "SH-0001", b"MZ\x90\x00" + b"\x00" * 200, "invoice.pdf.exe")
    c = S.case(T, "SH-0001")
    assert len(c["proofs"]) == 3 and c["commission"] == "District Commission"
    # same complaint again within minutes = same case
    again = S.log_complaint(T, v["text"], customer="Ramesh Patil", phone="9890011111", channel="whatsapp", product="Bajaj Mixer 750W")
    assert again.get("duplicate") and again["case"]["number"] == "SH-0001"


def test_patterns_and_tracking_and_reminders(sk, monkeypatch):
    S = sk
    S.save_settings(T, sector="ecommerce", business="Ingle Electronics", team=[{"name": "Sandesh", "phone": "9000000001"}])
    a = S.log_complaint(T, "Mixer ka jar toota aaya", customer="A", phone="9000000011", product="Bajaj Mixer 750W")
    S.log_complaint(T, "Mixer ki motor garam", customer="B", phone="9000000022", product="Bajaj Mixer 750W")
    c3 = S.log_complaint(T, "Mixer chalta nahi", customer="C", phone="9000000033", product="bajaj mixer 750w")
    assert "product_pattern" in c3["case"]["flags"] and "supplier" in c3["say"]
    r = S.log_complaint(T, "Delivery late aayi aur staff ne badtameezi ki", customer="A", phone="9000000011", product="Fan")
    assert "repeat_customer" in r["case"]["flags"]
    with pytest.raises(S.ShikayatError):
        S.update(T, a["case"]["number"], owner="Ramu")                 # not in the team
    u = S.update(T, a["case"]["number"], stage="investigating", owner="Sandesh", note="supplier se baat")
    assert u["case"]["stage"] == "investigating" and u["case"]["owner"] == "Sandesh"
    with pytest.raises(S.ShikayatError):
        S.update(T, r["case"]["number"], stage="rejected", note="no")   # reason too short
    with pytest.raises(S.ShikayatError):
        S.update(T, a["case"]["number"], stage="closed")               # close only through the checklist
    S.ack(T, a["case"]["number"], "WhatsApp")
    d = S.day(T)
    assert d["open"] == 4 and d["no_ack"] == 3
    # time travel: 47 h later -> "ack soon" for the three without pavti, once only
    t0 = datetime.now(timezone.utc)
    sent = S.tick(t0 + timedelta(hours=44))
    assert sent >= 1 and any("pavti" in n for n in S.notes)
    n0 = len(S.notes)
    S.tick(t0 + timedelta(hours=45))
    assert all("pavti" not in x for x in S.notes[n0:])                    # same reminder not twice
    S.tick(t0 + timedelta(days=31))
    assert any("tareekh nikal gayi" in x for x in S.notes)
    assert S.day(T)["open"] == 4


def test_close_flow_checklist_messages_reopen(sk, monkeypatch):
    S = sk
    S.save_settings(T, sector="bank", business="Akot Credit Co")
    v = S.log_complaint(T, "EMI do baar kati", customer="Sunita Deshmukh", phone="9822012345", product="Gold loan")["case"]
    assert "billing" in v["causes"]
    with pytest.raises(S.ShikayatError):
        S.message(T, v["number"], "close")                     # nothing resolved yet
    ack = S.message(T, v["number"], "ack")
    assert v["number"] in ack["text"] and ack["wa_link"].startswith("https://wa.me/919822012345") and not ack["business_ok"]
    S.mark_told(T, v["number"], "whatsapp", "ack")
    assert S.case(T, v["number"])["stage"] == "acknowledged"
    res = S.resolve(T, v["number"], "Doosri EMI ka paisa khaate mein wapas daal diya gaya hai")
    assert res["case"]["stage"] == "resolved" and "Band karne se pehle" in res["say"]
    with pytest.raises(S.ShikayatError):
        S.close(T, v["number"])                                # proof / told / confirmed missing
    # the model's polish that adds money is refused -> template kept
    monkeypatch.setattr(S, "_ai", lambda *a, **k: f"{v['number']}: aapko ₹500 cashback bhi milega!")
    m = S.message(T, v["number"], "close")
    assert "₹500" not in m["text"] and "RBI Ombudsman" in m["text"]          # regulated: the honest next step is in the reply
    good = m["text"].replace("Asuvidha", "asuvidha")
    monkeypatch.setattr(S, "_ai", lambda *a, **k: good)
    assert S.message(T, v["number"], "close")["text"] == good
    S.mark_told(T, v["number"], "whatsapp")
    S.note(T, v["number"], "bank statement dekha")
    with pytest.raises(S.ShikayatError):
        S.close(T, v["number"])                                # still no proof of fix / confirmation
    with pytest.raises(S.ShikayatError):
        S.close(T, v["number"], force=True, reason="")         # force needs a reason
    nf = S.confirm(T, v["number"], fixed=False, feedback="paisa abhi nahi aaya")
    assert nf["case"]["stage"] == "reopened"
    S.resolve(T, v["number"], "Refund NEFT se bheja, UTR customer ko diya", fix_proof="bank statement ka screenshot")
    S.mark_told(T, v["number"], "whatsapp")
    S.confirm(T, v["number"], fixed=True, satisfaction=4)
    cl = S.close(T, v["number"])
    assert cl["case"]["stage"] == "closed" and cl["case"]["satisfaction"] == 4
    assert "billing" in S.settings(T)["learned"]
    # reopen inside 30 days = the same case; after = a new linked case
    ro = S.reopen(T, v["number"], "phir kati")
    assert ro["case"]["number"] == v["number"] and ro["case"]["reopen_count"] == 2
    S.resolve(T, v["number"], "Wapas kiya", fix_proof="statement")
    S.mark_told(T, v["number"])
    S.confirm(T, v["number"], True)
    S.close(T, v["number"])
    real = S._now
    monkeypatch.setattr(S, "_now", lambda: real() + timedelta(days=45))
    nw = S.reopen(T, v["number"], "teesri baar")
    assert nw["case"]["number"] != v["number"] and "nayi shikayat" in nw["say"]
    # reject needs a reason and its letter names the routes
    S.update(T, nw["case"]["number"], stage="rejected", note="Statement mein koi doosri katauti nahi dikhi.")
    rj = S.message(T, nw["case"]["number"], "reject")
    assert "Statement mein" in rj["text"] and "Ombudsman" in rj["text"]


class Phone:
    def __init__(self, device_id):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        self.device_id = device_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def sign(self, ch):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        sig = self.key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))
        return {"challenge_id": ch["challenge_id"], "device_id": self.device_id, "signature": base64.b64encode(sig).decode()}


def _client():
    from app.shikayat.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    return TestClient(app)


def test_compensation_only_on_her_tap(sk, monkeypatch):
    S = sk
    from app import approvekey as ak
    S.save_settings(T, comp_limit=1000, month_limit=1500)
    v = S.log_complaint(T, "Cooler galat model aaya", customer="Kiran", phone="9890022222", product="Cooler", amount=9000)["case"]
    with pytest.raises(S.ShikayatError):
        S.comp_request(T, v["number"], "refund")                   # money without an amount
    r = S.comp_request(T, v["number"], "refund", 1200, reason="galat model, wapsi")
    cid, h = r["comp"]["id"], r["comp"]["hash"]
    assert r["needs_tap"] and any("seema" in x for x in r["comp"]["checks"]) and S.events[-1][0] == "shikayat_comp"
    with pytest.raises(S.ShikayatError):
        S.decide_comp(T, cid, True, h)                              # not from the app tap
    with pytest.raises(S.ShikayatError):
        S.close(T, v["number"], force=True, reason="jaldi hai")     # a pending card blocks closing even with force
    c = _client()
    assert c.post(f"/api/shikayat/comp/{cid}/decide", json={"yes": True, "hash": "x"}).status_code == 400   # wrong card
    # her phone has a fingerprint key -> money needs its signature
    ph = Phone("pixel-1")
    ak.register(T, ph.device_id, ph.pub, "Pixel")
    assert c.post(f"/api/shikayat/comp/{cid}/decide", json={"yes": True, "hash": h}).status_code == 428
    ch = c.post(f"/api/shikayat/comp/{cid}/challenge").json()
    assert "|shikayat|" in ch["message"] and ch["show"]["amount"] == "₹1,200"
    other = Phone("thief")
    bad = other.sign(ch)
    bad["device_id"] = ph.device_id
    assert c.post(f"/api/shikayat/comp/{cid}/decide", json={"yes": True, "hash": h, "proof": bad}).status_code == 428
    ch = c.post(f"/api/shikayat/comp/{cid}/challenge").json()
    ok = c.post(f"/api/shikayat/comp/{cid}/decide", json={"yes": True, "hash": h, "proof": ph.sign(ch)})
    assert ok.status_code == 200, ok.text
    assert ok.json()["comp"]["status"] == "approved" and "Aap khud dijiye" in ok.json()["say"]
    S.resolve(T, v["number"], "Sahi model badal diya", fix_proof="delivery photo")
    m = S.message(T, v["number"], "close")
    assert "₹1,200" in m["text"]                                    # only what she approved
    # rejection never needs a fingerprint
    r2 = S.comp_request(T, v["number"], "goodwill", 400, reason="pareshani")
    assert any("mahine" in x for x in r2["comp"]["checks"])
    assert c.post(f"/api/shikayat/comp/{r2['comp']['id']}/decide", json={"yes": False, "hash": r2["comp"]["hash"]}).json()["comp"]["status"] == "rejected"
    with pytest.raises(S.ShikayatError):
        S.close(T, v["number"])                                      # approved but not given yet
    g = c.post(f"/api/shikayat/comp/{cid}/given", json={"how": "UPI", "ref": "UTR 1234567890"}).json()
    assert g["comp"]["status"] == "given" and g["comp"]["given_how"].endswith("7890")
    # sending a message that names money she did not approve is refused
    monkeypatch.setattr("app.employee.inbox.send", None)
    with pytest.raises(S.ShikayatError):
        asyncio.run(S.send_business(T, v["number"], "Aapko ₹5,000 milenge"))


def test_tools_actor_rules_tickets_customer_tools(sk):
    from app.agent.shikayat_tools import SHIKAYAT_BIZ_HANDLERS, SHIKAYAT_HANDLERS, SHIKAYAT_LABELS, SHIKAYAT_TOOLS
    from app.agent.tools import Ctx, ToolError
    S = sk
    assert {t["name"] for t in SHIKAYAT_TOOLS} == set(SHIKAYAT_HANDLERS) == set(SHIKAYAT_LABELS)
    ctx = conv_ctx()

    def run(name, actor="owner", **a):
        return asyncio.run(SHIKAYAT_HANDLERS[name](Ctx(T, ctx.conversation_id, actor=actor), **a))

    out = run("shikayat", action="log", text="Internet 2 din se band, speed nahi", customer="Patil", phone="9890033333",
              channel="call", sector="isp")
    num = out["case"]["number"]
    assert out["case"]["sector"] == "telecom" and "technical" in out["case"]["causes"]
    assert run("shikayat_dekho", what="routes", sector="telecom")["routes"][0]["id"] == "telecom_appellate"
    with pytest.raises(ToolError):
        run("shikayat", actor="staff:x", action="settings", sector="bank")
    with pytest.raises(ToolError):
        run("shikayat", actor="staff:x", action="close", case=num, force=True, reason="bas")
    c = run("shikayat", actor="staff:x", action="comp", case=num, kind="discount", amount=200, reason="2 din band")
    assert c["needs_tap"] and c["comp"]["status"] == "pending"
    with pytest.raises(ToolError):
        run("shikayat", actor="staff:x", action="comp_given", comp=c["comp"]["number"])
    assert run("shikayat_dekho", what="case", case=num)["comps"][0]["status"] == "pending"
    assert run("shikayat_dekho", what="day")["comp_pending"] == 1
    # a Hoola Network / WhatsApp ticket becomes a complaint once
    from app.db import session
    from app.net.business import Ticket
    with session() as s:
        s.add(Ticket(tenant_id=T, number="TK-7", customer="wa:919811112222", customer_label="Asha (WhatsApp …2222)",
                     text="Router ki light laal hai", category="network"))
    imp = run("shikayat", action="import_tickets")
    assert len(imp["imported"]) == 1 and run("shikayat", action="import_tickets")["imported"] == []
    tc = S.case(T, imp["imported"][0])
    assert tc["ticket_ref"] == "TK-7" and tc["phone"] == "9811112222" and tc["channel"] == "whatsapp"
    # the WhatsApp customer: only their own complaints
    from app.employee.models import BizContact
    with session() as s:
        b = BizContact(tenant_id=T, wa_id="919811112222", name="Asha")
        s.add(b)
        s.flush()
        bid = b.id
    cctx = Ctx(T, ctx.conversation_id, actor=f"customer:{bid}")
    got = asyncio.run(SHIKAYAT_BIZ_HANDLERS["biz_shikayat"](cctx, text="Bill mein zyada paise lage", product="Plan 499"))
    assert got["number"].startswith("SH-") and "vaada" in got["note"]
    st = asyncio.run(SHIKAYAT_BIZ_HANDLERS["biz_shikayat_status"](cctx))["complaints"]
    assert len(st) == 2 and all("Patil" not in str(x) for x in st)
    with pytest.raises(ToolError):
        asyncio.run(SHIKAYAT_BIZ_HANDLERS["biz_shikayat"](cctx, text="mera OTP 123456 hai"))
    with pytest.raises(ToolError):
        asyncio.run(SHIKAYAT_BIZ_HANDLERS["biz_shikayat_status"](Ctx(T, ctx.conversation_id, actor="owner")))
    # forget (DPDP erasure)
    f = run("shikayat", action="forget", phone="9811112222")
    assert f["forgotten"] == 2 and S.cases(T, "", "9811112222") == []


def test_api_register_summary(sk):
    import openpyxl
    del sk
    c = _client()
    r = c.put("/api/shikayat/settings", json={"sector": "insurance", "resolve_days": 30, "business": "Bima Seva"})
    assert r.status_code == 200 and r.json()["effective"]["resolve_days"] == 14 and r.json()["notes"]     # capped to IRDAI 14
    r = c.post("/api/shikayat/cases", json={"text": "Claim ka jawab nahi aaya, koi call nahi uthata", "customer": "Meera",
                                            "phone": "9890044444", "product": "Health policy"})
    assert r.status_code == 200, r.text
    cid = r.json()["case"]["id"]
    up = c.post(f"/api/shikayat/cases/{cid}/proof", files={"file": ("photo.jpg", _jpeg_with_gps(), "image/jpeg")},
                data={"stage": "complaint"})
    assert up.status_code == 200 and up.json()["cleaned"]
    g = c.get(f"/api/shikayat/proof/{up.json()['id']}")
    assert g.status_code == 200 and g.headers["content-type"] == "image/jpeg"
    assert c.post(f"/api/shikayat/cases/{cid}/ack", json={}).json()["case"]["stage"] == "acknowledged"
    assert c.post(f"/api/shikayat/cases/{cid}/resolve", json={"resolution": "Claim settle, cheque bheja", "fix_proof": "settlement letter"}).status_code == 200
    assert c.post(f"/api/shikayat/cases/{cid}/close", json={}).status_code == 400            # not told / confirmed
    c.post(f"/api/shikayat/cases/{cid}/told", json={"kind": "close"})
    c.post(f"/api/shikayat/cases/{cid}/confirm", json={"fixed": True, "satisfaction": 5})
    assert c.post(f"/api/shikayat/cases/{cid}/close", json={}).json()["case"]["stage"] == "closed"
    assert c.post(f"/api/shikayat/cases/{cid}/bogus", json={}).status_code == 404
    home = c.get("/api/shikayat").json()
    assert "insurance" in home["sectors"] and home["day"]["open"] == 0
    sm = c.get("/api/shikayat/summary").json()
    assert sm["received"] == 1 and sm["disposed"] == 1 and sm["closed_in_time_pct"] == 100 and sm["satisfaction_avg"] == 5
    reg = c.post("/api/shikayat/register", json={}).json()
    from app.mailbox import service as ms
    from pathlib import Path
    data = Path(ms._file_row(T, reg["file"]["file_id"]).stored_path).read_bytes()
    wb = openpyxl.load_workbook(io.BytesIO(data))
    assert wb.sheetnames == ["Register", "Summary"]
    rows = list(wb["Register"].iter_rows(values_only=True))
    assert rows[0][0] == "No" and rows[1][0] == "SH-0001" and rows[1][3] == "...4444"
    assert any(r[0] == "Received during month" and r[1] == 1 for r in wb["Summary"].iter_rows(values_only=True))


def test_video_metadata_and_business_send(sk, monkeypatch, tmp_path):
    import shutil
    import subprocess
    S = sk
    v = S.log_complaint(T, "Fridge se paani tapak raha hai", customer="Neha", phone="9890055555", product="Fridge")["case"]
    if shutil.which("ffmpeg"):
        src = tmp_path / "in.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=64x48:d=1", "-metadata",
                        "location=+18.5204+073.8567/", "-metadata", "title=SecretTitle", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)],
                       check=True, capture_output=True)
        raw = src.read_bytes()
        assert b"SecretTitle" in raw
        p = S.add_proof(T, v["number"], raw, "VID_2026.mp4")
        path, mime = S.proof_file(T, p["id"])
        body = path.read_bytes()
        assert p["kind"] == "video" and p["cleaned"] and mime == "video/mp4" and b"SecretTitle" not in body and b"+18.5204" not in body
    # business WhatsApp only through her tap, only to a customer who wrote to the business
    with pytest.raises(S.ShikayatError):
        asyncio.run(S.send_business(T, v["number"], "Namaste, theek ho gaya"))
    from app.db import session
    from app.employee.models import BizContact
    with session() as s:
        b = BizContact(tenant_id=T, wa_id="919890055555", name="Neha", last_in_at=datetime.now(timezone.utc))
        s.add(b)
        s.flush()
        bid = b.id
    S.resolve(T, v["number"], "Pipe badal diya", fix_proof="photo")
    m = S.message(T, v["number"], "close")
    assert m["business_ok"] and m["contact_id"] == bid
    sent = []

    async def fake_send(tenant, contact_id, text, by="owner", force=False):
        sent.append((contact_id, text, by))
        return {"ok": True}
    monkeypatch.setattr("app.employee.inbox.send", fake_send)
    r = asyncio.run(S.send_business(T, v["number"], m["text"]))
    assert sent == [(bid, m["text"], "owner")] and S.case(T, v["number"])["told_at"] and "bataya" in r["say"]
