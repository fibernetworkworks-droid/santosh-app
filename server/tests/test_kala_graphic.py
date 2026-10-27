"""Graphic Sahayak: rules (print preflight of images / PDFs, font + asset licences, clone / emblem refusals, GST split, CMYK,
copyright assignment blanks, trade-mark help), clients with their own brand kits, jobs with HER prices only, proofs drawn by the
brand engine in the CLIENT's kit (real Chromium), revision rounds counted in code (extra round only by her tap), her uploaded
artwork preflighted against the printer's spec, every outgoing step (quote / proof / extra / handover / print order / invoice /
discount / message) only by HER tap with the card's hash, discount with her real fingerprint, handover pack ZIP, DPDP forget,
worker, tools + API."""
import asyncio
import base64
import io
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.graphic.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)        # 10:30 am IST


@pytest.fixture
def gd(env, monkeypatch, tmp_path):
    from app.graphic import service as S
    monkeypatch.setenv("GRAPHIC_DIR", str(tmp_path / "graphic"))
    events, stored, files = [], [], {}
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    monkeypatch.setattr(S, "_load_file", lambda tenant, fid: files[fid])
    monkeypatch.setattr(S, "_ai_words", lambda system, prompt: {})
    clk = {"t": NOW}
    monkeypatch.setattr(S, "clock", lambda: clk["t"])
    S.EVENTS, S.STORED, S.FILES, S.CLK = events, stored, files, clk
    return S


class Phone:
    def __init__(self, device_id):
        self.device_id = device_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def sign(self, ch):
        sig = self.key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))
        return {"challenge_id": ch["challenge_id"], "device_id": self.device_id, "signature": base64.b64encode(sig).decode()}


def _png(w, h, mode="RGB", color=(200, 30, 30)):
    from PIL import Image
    buf = io.BytesIO()
    im = Image.new(mode, (w, h), color if mode != "CMYK" else (0, 80, 80, 0))
    im.save(buf, "TIFF" if mode == "CMYK" else "PNG")
    return buf.getvalue()


def _pdf_page(w_mm, h_mm):
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w_mm * mm, h_mm * mm))
    c.setFont("Helvetica", 10)
    c.drawString(10, 10, "Ramesh Sweets")
    c.save()
    return buf.getvalue()


def _studio(S, gstin="27AAPFU0939F1ZV"):
    S.save_settings(T, studio="Kala Studio", designer="Meera Joshi", gstin=gstin, upi_id="kala@okicici", phone="9876543210",
                    extra_round=1500, rounds=2)


def _client(S, **kw):
    base = dict(name="Ramesh Patil", business="Ramesh Sweets", phone="9822012345", kind="business",
                colors={"primary": "#7A1F3D", "accent": "#F5A623"}, tagline="Shuddh desi ghee", contact={"phone": "9822012345"})
    base.update(kw)
    return S.client_save(T, **base)["client"]


def test_rules():
    from app.graphic import rules as R
    card = R.format_spec("visiting_card")
    assert card["mm"] == (89.0, 51.0) and card["bleed"] == 3 and card["dpi"] == 300 and card["color"] == "cmyk"
    # 89+6 x 51+6 mm at 300 dpi = 1122 x 673 px; same size, CMYK -> ok
    ok = R.preflight(_png(1122, 673, "CMYK"), "card.tif", card)
    assert ok["ok"] and ok["dpi"] >= 299 and not [i for i in ok["issues"] if i["level"] != "info"]
    # trim size only (no bleed) + RGB + low dpi
    bad = R.preflight(_png(525, 301), "card.png", card)
    texts = " ".join(i["text"] for i in bad["issues"])
    assert not bad["ok"] and "Bleed nahi" in texts and "CMYK" in texts and "Resolution kam" in texts
    # a PDF at trim size: no bleed + Helvetica not embedded
    p = R.preflight(_pdf_page(89, 51), "card.pdf", card)
    t2 = " ".join(i["text"] for i in p["issues"])
    assert not p["ok"] and "Bleed nahi" in t2 and "Helvetica" in t2
    p2 = R.preflight(_pdf_page(95, 57), "card.pdf", card)
    assert not [i for i in p2["issues"] if "naap" in i["text"] or "Bleed" in i["text"]] and p2["fonts_unembedded"]
    assert R.preflight(_pdf_page(200, 100), "x.pdf", card)["issues"][0]["text"].startswith("Page ka naap")
    flex = R.format_spec("flex_6x3")
    assert flex["wide"] and flex["dpi"] == 100
    # licences
    assert R.asset_verdict({"kind": "font", "name": "Poppins", "source": "Google Fonts"})["rule"] == "share"
    assert R.asset_verdict({"kind": "font", "name": "Myriad Pro", "source": "Adobe Fonts"})["rule"] == "no_files"
    assert R.asset_verdict({"kind": "font", "name": "Cool Script", "source": "dafont free for personal use"})["level"] == "block"
    assert R.asset_verdict({"kind": "image", "name": "x.jpg", "licence": ""})["level"] == "block"
    assert R.asset_verdict({"kind": "image", "name": "y.jpg", "licence": "stock_paid"})["level"] == "warn"
    # refusals
    assert R.clone_problem("Starbucks ka logo hubahu copy kar do") and not R.clone_problem("naya logo, coffee feel")
    # money
    g = R.gst_lines(10000, 18, "27", "29")
    assert g["kind"] == "igst" and g["tax"] == 1800
    g2 = R.gst_lines(10000, 18, "27", "27")
    assert g2["kind"] == "cgst_sgst" and [r["amount"] for r in g2["rows"]] == [900, 900]
    assert R.gst_lines(10000, 18, "27", "27", export=True, lut=True)["tax"] == 0
    assert "poochh" in R.tds_note("business", None, 60000) and "nahi katta" in R.tds_note("individual", None, 1)
    assert R.hex_to_cmyk("#FFFFFF") == (0, 0, 0, 0) and R.hex_to_cmyk("#000000") == (0, 0, 0, 100)
    a = R.assignment_text("Meera", "Ramesh Sweets", "Logo")
    assert any("5 saal" in b for b in a["blanks"]) and "s.19" in a["note"]
    h = R.tm_help("Ramesh Sweets", "mithai shop")
    assert {c["class"] for c in h["classes"]} >= {30} and "tmrsearch.ipindia.gov.in" in h["links"][0]
    assert R.kind_of("visiting card chahiye") == "visiting_card" and R.kind_of("naya logo") == "logo"
    assert "[hataya]" in R.clean("mera otp 445566 hai, card 4111 1111 1111 1111")


def test_client_job_quote_card_only_her_tap(gd):
    S = gd
    _studio(S)
    with pytest.raises(S.GraphicError):
        S.client_save(T, name="X", phone="12345")
    c = _client(S)
    assert c["number"] == "C-001" and c["colors"]["primary"] == "#7A1F3D" and c["cmyk"]["primary"][3] > 0
    with pytest.raises(S.GraphicError):           # Emblems Act
        S.job_save(T, client="Ramesh Sweets", brief="Diwali poster with Ashoka Chakra and tiranga")
    with pytest.raises(S.GraphicError):           # clone
        S.job_save(T, client="C-001", brief="Haldiram jaisa hi logo hubahu copy karo")
    j = S.job_save(T, client="C-001", kind="social", brief="Diwali offer post: kaju katli 20% off", facts="Kaju katli 20% off",
                   due="2026-10-30")["job"]
    assert j["number"] == "G-0001" and j["sizes"] == ["insta_post", "story", "insta_square"] and j["quote"]["missing"]
    with pytest.raises(S.GraphicError) as e:      # no price -> no quote (Hoola never prices)
        S.quote_request(T, "G-0001")
    assert "daam" in str(e.value)
    with pytest.raises(S.GraphicError):           # staff can't set prices
        S.job_save(T, "G-0001", actor="staff:s1", lines=[{"name": "3 posts", "rate": 3000}])
    S.job_save(T, "G-0001", lines=[{"name": "Diwali posts (3 size)", "qty": 1, "rate": 3000}], rounds=1, extra_round_price=800)
    q = S.job_view(T, "G-0001")["quote"]
    assert q["total"] == 3540 and q["gst"]["kind"] == "cgst_sgst" and q["advance"] == 1770
    c1 = S.quote_request(T, "G-0001")
    assert c1["status"] == "needs_tap" and S.EVENTS[-1][0] == "graphic_card"
    with pytest.raises(S.GraphicError):
        S.decide(T, c1["card"]["id"], True, c1["card"]["hash"])          # no tap = refused
    with pytest.raises(S.GraphicError):
        S.decide(T, c1["card"]["id"], True, "wrong", by_tap=True)
    r = S.decide(T, c1["card"]["id"], True, c1["card"]["hash"], by_tap=True)
    assert r["card"]["status"] == "approved" and r["draft"]["wa"].startswith("https://wa.me/919822012345")
    assert S.STORED[-1][0] == "G-0001_quotation.pdf" and S.STORED[-1][1][:5] == b"%PDF-"
    assert S.job_view(T, "G-0001")["status"] == "quoted"
    with pytest.raises(S.GraphicError):
        S.accepted(T, "G-0001", "")
    S.accepted(T, "G-0001", "Ramesh ji: 'theek hai, shuru karo' (WhatsApp)")
    # a change after a card makes it stale
    c2 = S.message_request(T, "G-0001", "Kal tak pehla proof bhejungi")
    S.job_save(T, "G-0001", title="Diwali posts")
    with pytest.raises(S.GraphicError):
        S.decide(T, c2["card"]["id"], True, c2["card"]["hash"], by_tap=True)
    assert S.card_view(T, c2["card"]["id"])["status"] == "stale"
    with pytest.raises(S.GraphicError):
        S.message_request(T, "G-0001", "Apna OTP bhejiye")


def test_render_in_client_kit_and_revision_rounds(gd):
    S = gd
    _studio(S)
    _client(S)
    S.job_save(T, client="C-001", kind="social", brief="Diwali offer", facts="Kaju katli 20% off", sizes=["insta_square"],
               lines=[{"name": "Post", "rate": 2000}], rounds=1)
    words = {"headline": "Kaju Katli 20% OFF", "sub": "Ramesh Sweets ki Diwali", "cta": "Aaj hi aaiye"}
    v1 = S.proof_render(T, "G-0001", words=words)["version"]
    assert v1["n"] == 1 and v1["round"] == 0 and v1["proofs"]["insta_square"].endswith("proof_v1_insta_square.jpg")
    p, mime = S.file_path(T, "G-0001", "proof_v1_insta_square.jpg")
    assert mime == "image/jpeg" and p.read_bytes()[:2] == b"\xff\xd8"
    # the proof is in the CLIENT's kit (maroon), never her own brand kit
    from PIL import Image
    im = Image.open(p).convert("RGB")
    r_, g_, b_ = im.getpixel((5, im.size[1] // 2))
    assert r_ > g_ and r_ > b_
    v2 = S.proof_render(T, "G-0001", words={**words, "cta": "Aaj hi order"})["version"]
    assert v2["round"] == 0                                          # rework before the client saw it: no round
    with pytest.raises(S.GraphicError):
        S.feedback(T, "G-0001", "font bada karo")                     # nothing sent yet
    ps = S.proof_send(T, "G-0001")
    S.decide(T, ps["card"]["id"], True, ps["card"]["hash"], by_tap=True)
    assert S.job_view(T, "G-0001")["version_list"][-1]["status"] == "sent"
    assert S.feedback(T, "G-0001", "Headline aur bada, peela kam")["rounds_left"] == 1
    v3 = S.proof_render(T, "G-0001", words={**words, "headline": "KAJU KATLI 20% OFF"})["version"]
    assert v3["round"] == 1
    ps = S.proof_send(T, "G-0001")
    S.decide(T, ps["card"]["id"], True, ps["card"]["hash"], by_tap=True)
    f2 = S.feedback(T, "G-0001", "ek aur badlav: background laal")
    assert f2["rounds_left"] == 0 and "extra" in f2["say"].lower()
    with pytest.raises(S.GraphicError) as e:                          # rounds used up: refused in code
        S.proof_render(T, "G-0001", words=words)
    assert "round" in str(e.value)
    S.save_settings(T, extra_round="")
    S.job_save(T, "G-0001", extra_round_price="")
    with pytest.raises(S.GraphicError):                               # no extra price written
        S.extra_request(T, "G-0001")
    S.job_save(T, "G-0001", extra_round_price=700)
    with pytest.raises(S.GraphicError):
        S.waive_round(T, "G-0001", actor="staff:s1")
    ex = S.extra_request(T, "G-0001")
    S.decide(T, ex["card"]["id"], True, ex["card"]["hash"], by_tap=True)
    v4 = S.proof_render(T, "G-0001", words=words)["version"]
    assert v4["round"] == 2
    q = S.job_view(T, "G-0001")["quote"]
    assert any(ln["name"] == "Extra revision round" and ln["amount"] == 700 for ln in q["lines"])


def test_upload_preflight_print_order_handover_invoice(gd):
    S = gd
    _studio(S)
    _client(S)
    S.vendor_save(T, "Shree Printers", "9811122233", does="digital, visiting cards", spec={"color": "cmyk", "dpi": 300, "bleed": 3})
    S.job_save(T, client="C-001", kind="visiting_card", brief="Visiting card, maroon", vendor="Shree",
               lines=[{"name": "Visiting card design", "rate": 1500}], print_job={"qty": 500, "stock": "350 gsm matt"})
    with pytest.raises(S.GraphicError):                                # the engine has no visiting-card size
        S.proof_render(T, "G-0001", words={"headline": "x"})
    S.FILES["fx"] = ("card.png", _png(525, 301))
    up = S.proof_upload(T, "G-0001", file_id="fx")
    assert up["preflight"]["ok"] is False and up["version"]["blocks"]
    ps = S.proof_send(T, "G-0001")
    S.decide(T, ps["card"]["id"], True, ps["card"]["hash"], by_tap=True)
    S.client_approved(T, "G-0001", 1, "Client: 'ok final'")
    with pytest.raises(S.GraphicError) as e:                          # print order refused while the file fails preflight
        S.vendor_request(T, "G-0001")
    assert "Bleed" in str(e.value)
    S.feedback(T, "G-0001", "printer ne bleed maanga")
    up2 = S.proof_upload(T, "G-0001", data=_png(1122, 673, "CMYK"), name="card.tif")
    assert up2["preflight"]["ok"] and up2["version"]["round"] == 1
    ps = S.proof_send(T, "G-0001", 2)
    S.decide(T, ps["card"]["id"], True, ps["card"]["hash"], by_tap=True)
    S.client_approved(T, "G-0001", 2, "Client: 'perfect'")
    vo = S.vendor_request(T, "G-0001")
    r = S.decide(T, vo["card"]["id"], True, vo["card"]["hash"], by_tap=True)
    assert "500 copies" in r["draft"]["text"] and r["draft"]["wa"].startswith("https://wa.me/919811122233")
    # licences: a 'personal use' font blocks the handover
    S.asset_add(T, "G-0001", "Cool Script", "font", "dafont free for personal use")
    S.asset_add(T, "G-0001", "Poppins", "font", "Google Fonts")
    with pytest.raises(S.GraphicError) as e:
        S.handover_request(T, "G-0001")
    assert "personal" in str(e.value)
    S.asset_remove(T, "G-0001", "Cool Script")
    with pytest.raises(S.GraphicError) as e:                          # money still due
        S.handover_request(T, "G-0001")
    assert "baaki" in str(e.value)
    with pytest.raises(S.GraphicError):
        S.paid(T, "G-0001", 1770, actor="staff:s1")
    inv = S.invoice_request(T, "G-0001", "advance")
    assert inv["card"]["show"]["amount"] == 885 and inv["card"]["show"]["upi"] == "kala@okicici"
    ri = S.decide(T, inv["card"]["id"], True, inv["card"]["hash"], by_tap=True)
    assert ri["invoice"] == "INV/2627/0001" and ri["draft"]["upi"].startswith("upi://pay?pa=kala%40okicici")
    with pytest.raises(S.GraphicError):
        S.invoice_request(T, "G-0001", "advance")
    S.paid(T, "G-0001", 885, "upi", "UTR998877")
    fin = S.invoice_request(T, "G-0001", "final")
    assert fin["card"]["show"]["amount"] == 885
    S.decide(T, fin["card"]["id"], True, fin["card"]["hash"], by_tap=True)
    S.paid(T, "G-0001", 885)
    ho = S.handover_request(T, "G-0001")
    sh = ho["card"]["show"]
    assert sh["files"][0]["name"].endswith(".tif") and "Assignor" in sh["assignment"]
    rh = S.decide(T, ho["card"]["id"], True, ho["card"]["hash"], by_tap=True)
    z = zipfile.ZipFile(io.BytesIO(S.STORED[-1][1]))
    names = z.namelist()
    assert "README.txt" in names and "copyright-assignment-DRAFT.pdf" in names and any(n.endswith(".tif") for n in names)
    readme = z.read("README.txt").decode()
    assert "Poppins" in readme and "CMYK" in readme
    assert S.job_view(T, "G-0001")["status"] == "delivered" and rh["card"]["status"] == "approved"


def test_render_handover_finals_and_igst(gd):
    S = gd
    _studio(S)
    _client(S, name="Asha Rao", business="Asha Bakes", gstin="29AAGCB7383J1Z4", colors={"primary": "#1E5631"})
    S.job_save(T, client="C-001", kind="poster", sizes=["insta_square"], facts="Fresh cakes daily",
               lines=[{"name": "Poster", "rate": 5000}])
    q = S.job_view(T, "G-0001")["quote"]
    assert q["gst"]["kind"] == "igst" and q["total"] == 5900                  # Maharashtra -> Karnataka
    S.proof_render(T, "G-0001", words={"headline": "Fresh Cakes Daily"})
    ps = S.proof_send(T, "G-0001")
    S.decide(T, ps["card"]["id"], True, ps["card"]["hash"], by_tap=True)
    S.client_approved(T, "G-0001", 1, "ok")
    with pytest.raises(S.GraphicError):
        S.handover_request(T, "G-0001", force=True, actor="staff:s1")
    ho = S.handover_request(T, "G-0001", force=True)                         # her choice: files before payment
    S.decide(T, ho["card"]["id"], True, ho["card"]["hash"], by_tap=True)
    z = zipfile.ZipFile(io.BytesIO(S.STORED[-1][1]))
    assert z.read("G-0001-insta_square.png")[:8] == b"\x89PNG\r\n\x1a\n"


def test_discount_fingerprint_tm_and_forget(gd, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    S = gd
    _studio(S, gstin="")
    _client(S)
    S.job_save(T, client="C-001", kind="logo", brief="Mithai shop ka logo", lines=[{"name": "Logo", "rate": 10000}])
    v = S.job_view(T, "G-0001")
    assert v["quote"]["total"] == 10000 and "GSTIN nahi" in v["quote"]["gst_note"]
    with pytest.raises(S.GraphicError):
        S.discount_request(T, "G-0001", amount=20000)
    d = S.discount_request(T, "G-0001", amount=1000, reason="Purana client")
    from app import approvekey as ak
    phone = Phone("phone-1")
    ak.register(T, phone.device_id, phone.pub, "Pixel")
    with pytest.raises(S.GraphicError) as e:
        S.decide(T, d["card"]["id"], True, d["card"]["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.card_challenge(T, d["card"]["id"])
    with pytest.raises(S.GraphicError):
        S.decide(T, d["card"]["id"], True, d["card"]["hash"], proof=Phone("phone-1").sign(ch), by_tap=True)
    ch = S.card_challenge(T, d["card"]["id"])
    S.decide(T, d["card"]["id"], True, d["card"]["hash"], proof=phone.sign(ch), by_tap=True)
    assert S.job_view(T, "G-0001")["quote"]["total"] == 9000
    h = S.tm_help(T, "G-0001")
    assert any(c["class"] == 30 for c in h["classes"])
    with pytest.raises(S.GraphicError):
        S.tm_record(T, "G-0001", "maybe")
    assert "jokhim" in S.tm_record(T, "G-0001", "registered_same", [30])["say"]
    with pytest.raises(S.GraphicError):
        S.forget_client(T, "C-001")
    S.cancel(T, "G-0001", "client ne mana kiya")
    S.forget_client(T, "C-001")
    cv = S.client_view(T, "C-001")
    assert cv["phone"] == "" and cv["forgotten"] and cv["jobs"][0]["number"] == "G-0001"
    assert S.job_view(T, "G-0001")["brief"].startswith("[hataya")


def test_tick_tools_and_api(gd):
    S = gd
    _studio(S)
    _client(S)
    S.job_save(T, client="C-001", kind="social", sizes=["insta_square"], due="2026-10-24", lines=[{"name": "Post", "rate": 1000}])
    S.EVENTS.clear()
    assert S.tick(NOW)["alerts"] >= 1 and any(k == "graphic_alert" for k, _ in S.EVENTS)
    assert S.tick(NOW)["alerts"] == 0                                      # once each
    assert S.tick(NOW + timedelta(days=3))["alerts"] >= 1                  # now late
    from app.agent.graphic_tools import GRAPHIC_HANDLERS, GRAPHIC_TOOLS
    from app.agent.tools import ToolError
    for t in GRAPHIC_TOOLS:
        assert set(t["input_schema"]["required"]) <= set(t["input_schema"]["properties"])
    ctx = conv_ctx()
    r = asyncio.run(GRAPHIC_HANDLERS["graphic_dekho"](ctx, what="job", job="G-0001"))
    assert r["number"] == "G-0001"
    r = asyncio.run(GRAPHIC_HANDLERS["graphic"](ctx, action="quote_send", job="G-0001"))
    assert r["status"] == "needs_tap"
    ctx.actor = "staff:s1"
    with pytest.raises(ToolError):
        asyncio.run(GRAPHIC_HANDLERS["graphic"](ctx, action="paid", job="G-0001", amount=500))
    ctx.actor = "customer:wa:9822012345"
    with pytest.raises(ToolError):
        asyncio.run(GRAPHIC_HANDLERS["graphic"](ctx, action="job", client="C-001", brief="x"))
    from app.graphic.api import make_router
    app_ = FastAPI()
    app_.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app_)
    assert c.get("/api/graphic").json()["day"]["say"]
    card = c.get("/api/graphic/cards").json()["cards"][0]
    assert c.post(f"/api/graphic/cards/{card['id']}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    ok = c.post(f"/api/graphic/cards/{card['id']}/decide", json={"yes": True, "hash": card["hash"]}).json()
    assert ok["card"]["status"] == "approved"
    r = c.post("/api/graphic/jobs/G-0001/upload", files={"file": ("a.png", _png(1080, 1080), "image/png")}).json()
    assert r["version"]["n"] == 1
    assert c.get(f"/api/graphic/files/G-0001/{r['version']['file_name']}").status_code == 200
    assert c.get("/api/graphic/files/G-0001/..%2Fsecret").status_code in (400, 404)
    assert c.get("/api/graphic/jobs/G-0001/quote.pdf").content[:5] == b"%PDF-"
