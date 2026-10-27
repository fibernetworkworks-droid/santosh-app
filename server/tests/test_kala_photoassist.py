"""Photo Sahayak: rules (kinds, times, overlap with buffer, checks, releases, GST / TDS, refund tiers), shoots with NO double
booking (hold / confirm card / tap / move all refused in code, per shooter, multi-day), holds that expire, cards decided only by
HER tap with the hash (stale on change), money cards with her real fingerprint, culling signals with EXIF stripped, releases,
edits, delivery via her own link, invoice + receipts, cancel by policy, DPDP forget, worker, tools + API."""
import asyncio
import base64
import io
from datetime import date, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.photoassist.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)        # 10:30 am IST


@pytest.fixture
def pa(env, monkeypatch, tmp_path):
    from app.photoassist import service as S
    monkeypatch.setenv("PHOTOASSIST_DIR", str(tmp_path / "pa"))
    events, stored = [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    monkeypatch.setattr(S, "_see", lambda jpeg: "")
    clk = {"t": NOW}
    monkeypatch.setattr(S, "clock", lambda: clk["t"])
    S.EVENTS, S.STORED, S.CLK = events, stored, clk
    return S


def _studio(S):
    S.save_settings(T, studio="Lens Kahani Studio", gstin="27AAPFU0939F1ZV", upi_id="lenskahani@okicici", phone="9876543210",
                    buffer_minutes=60)
    S.package_save(T, "Wedding Gold", 85000, "day", "2 photographers, 400 edited photos, album", edits=40)
    S.package_save(T, "Product Basic", 500, "photo", "white background")
    S.gear_save(T, "Sony A7 IV", "camera", serial="SN1")
    S.gear_save(T, "DJI Mini 4 Pro", "drone", weight_g=249)


def _shoot(S, day="2026-12-12", start="16:00", end="23:00", **kw):
    args = dict(kind="shaadi", client="Priya Joshi", phone="9822012345", day=day, start=start, end=end,
                location="Shubh Mangal Lawns, Pune", lines=[{"package": "Wedding Gold"}])
    args.update(kw)
    return S.shoot_save(T, **args)["shoot"]


class Phone:
    def __init__(self, device_id):
        self.device_id = device_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def sign(self, ch):
        sig = self.key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))
        return {"challenge_id": ch["challenge_id"], "device_id": self.device_id, "signature": base64.b64encode(sig).decode()}


def _jpeg(kind="sharp", gps=False):
    from PIL import Image, ImageDraw, ImageFilter
    im = Image.new("RGB", (640, 480), (200, 180, 160))
    d = ImageDraw.Draw(im)
    for x in range(0, 640, 20):
        for y in range(0, 480, 20):
            if (x // 20 + y // 20) % 2:
                d.rectangle([x, y, x + 19, y + 19], fill=(20, 20, 20))
    if kind == "blur":
        im = im.filter(ImageFilter.GaussianBlur(14))
    if kind == "dark":
        im = Image.new("RGB", (640, 480), (5, 5, 5))
    bio = io.BytesIO()
    if gps:
        ex = Image.Exif()
        ex[0x0110] = "Pixel 9"                                        # camera model
        ex[0x8825] = {1: "N", 2: (18.0, 31.0, 0.0)}                   # GPS IFD
        im.save(bio, "JPEG", exif=ex)
    else:
        im.save(bio, "JPEG")
    return bio.getvalue()


def test_rules():
    from app.photoassist import rules as R
    assert R.kind_of("pre wedding shoot Lonavala") == "pre_wedding" and R.kind_of("shaadi ki photography") == "wedding"
    assert R.kind_of("amazon listing ke liye product") == "product" and R.kind_of("naamkaran") == "newborn"
    assert R.hhmm("shaam 4 baje") == "16:00" and R.hhmm("4 pm") == "16:00" and R.hhmm("subah 7:30") == "07:30" and R.hhmm("") == ""
    w1 = R.windows("2026-12-12", "", "10:00", "13:00")
    assert R.overlap(w1, R.windows("2026-12-12", "", "13:30", "16:00"), 60)            # inside the 60-min travel gap
    assert not R.overlap(w1, R.windows("2026-12-12", "", "15:00", "18:00"), 60)
    assert R.overlap(R.windows("2026-12-11", "2026-12-13", "", ""), w1, 0)             # multi-day = whole days
    assert R.overlap(R.windows("2026-12-11", "", "20:00", "02:00"), R.windows("2026-12-12", "", "01:00", "03:00"), 0)
    assert R.place_kind("Shaniwar Wada fort Pune") == "monument" and R.place_kind("Taj hotel lawn") == "venue"
    ch = R.shoot_checks("pre_wedding", "Golconda fort near airport", "monument", True, False, False, {})
    keys = {c["key"] for c in ch}
    assert {"asi", "drone_uin", "drone_rpc", "drone_ins", "drone_zone", "drone_airport", "drone_asi"} <= keys
    assert "minor" in {c["key"] for c in R.shoot_checks("newborn", "", "private", False, False, False, {})}
    assert "release" in {c["key"] for c in R.shoot_checks("product", "", "studio", False, True, False, {})}
    t = R.release_text("minor", "Lens", "Aarav", "Neha", "", ["portfolio"], "Newborn shoot S-0001", "en")
    assert "Neha" in t and "Aarav" in t and "withdraw" in t and "s.6" in t
    assert "anumati" in R.release_text("property", "Lens", "Ramesh", "", "Flat 4B", ["advertising"], "shoot", "hi")
    g = R.gst_split(1000, 18, "27", "27")
    assert g["cgst"] == 90 and g["sgst"] == 90 and g["igst"] == 0
    assert R.gst_split(1000, 18, "27", "29")["igst"] == 180 and R.gst_split(1000, 0, "27", "27")["tax"] == 0
    assert R.tds_note("personal", "wedding", 90000) == "" and "s.393" in R.tds_note("business", "product", 90000)
    pol = R.DEFAULT_CANCEL
    assert R.refund_pct(pol, 70) == 75 and R.refund_pct(pol, 40) == 50 and R.refund_pct(pol, 2) == 0
    assert R.unfair_policy([{"days_before": 30, "refund_pct": 0}]) and not R.unfair_policy(pol)
    assert R.clean("OTP 482913 card 4111 1111 1111 1111") == "OTP [hataya] card [hataya]"
    assert R.https_link("https://drive.google.com/x") and not R.https_link("http://x.com") and not R.https_link("https://10.0.0.1/a")
    assert R.cull_hint({"sharpness": 10})[0] == "reject" and R.cull_hint({"sharpness": 120})[0] == "keep"
    assert R.cull_hint({"sharpness": 120, "dup_of": "a.jpg"})[0] == "maybe"


def test_no_double_booking(pa):
    S = pa
    _studio(S)
    a = _shoot(S)
    assert a["number"] == "S-0001" and a["status"] == "draft" and a["kind"] == "wedding"
    v = S.shoot_view(T, "S-0001")
    assert any(r["must"] for r in v["shot_list"]) and any("Sony" in g["item"] for g in v["gear_list"])
    assert v["quote"]["total"] == 100300.0 and v["quote"]["gst"]["cgst"] == 7650.0      # 85,000 + 18% CGST/SGST (her state)
    S.hold(T, "S-0001")
    # same shooter, overlapping (inside the 60-min gap) -> refused everywhere
    b = _shoot(S, start="11:00", end="15:30", client="Rohan")
    with pytest.raises(S.PhotoError, match="Double booking"):
        S.hold(T, b["number"])
    with pytest.raises(S.PhotoError, match="Double booking"):
        S.confirm_request(T, b["number"])
    assert S.free(T, "2026-12-12", "11:00", "15:30")["free"] is False
    assert S.free(T, "2026-12-12", "09:00", "13:00")["free"] is True
    # a second shooter on the same evening is fine
    c = _shoot(S, client="Asha", shooters=["ravi"])
    assert S.hold(T, c["number"])["shoot"]["status"] == "hold"
    # multi-day wedding of the main shooter over the 12th clashes with the held evening
    d = _shoot(S, day="2026-12-11", end_day="2026-12-13", start="", end="", client="Kapoor")
    with pytest.raises(S.PhotoError):
        S.hold(T, d["number"])
    # past dates refused
    with pytest.raises(S.PhotoError, match="Beeti"):
        _shoot(S, day="2026-10-01")
    # the held shoot expires by itself -> slot free
    S.CLK["t"] = NOW + timedelta(hours=49)
    assert S.free(T, "2026-12-12", "11:00", "15:30")["free"] is True
    assert S.hold(T, b["number"])["shoot"]["status"] == "hold"
    # moving a held shoot onto another held one is refused
    S.shoot_save(T, "S-0001", start="06:00", end="08:00")
    assert S.hold(T, "S-0001")["shoot"]["status"] == "hold"
    with pytest.raises(S.PhotoError, match="Double booking"):
        S.shoot_save(T, "S-0001", day="2026-12-12", start="12:00", end="14:00")


def test_cards_only_her_tap_and_stale(pa):
    S = pa
    _studio(S)
    _shoot(S)
    S.hold(T, "S-0001")
    q = S.quote_request(T, "S-0001")
    assert q["status"] == "needs_tap" and ("photoassist_card", ) == (S.EVENTS[-1][0],)
    with pytest.raises(S.PhotoError, match="tap"):
        S.decide(T, q["card"]["id"], True, q["card"]["hash"])
    with pytest.raises(S.PhotoError):
        S.decide(T, q["card"]["id"], True, "wrong", by_tap=True)
    # same card twice = the same waiting card
    assert S.quote_request(T, "S-0001")["existing"] is True
    ok = S.decide(T, q["card"]["id"], True, q["card"]["hash"], by_tap=True)
    assert ok["card"]["status"] == "approved" and ok["draft"]["wa"].startswith("https://wa.me/919822012345")
    assert S.STORED[-1][1].startswith(b"%PDF")
    # terms: copyright line (s.17(b)) + separate portfolio choice
    ct = S.contract_request(T, "S-0001")
    assert "s.17(b)" in ct["card"]["show"]["copyright_text"]
    # a change after the card -> stale at the tap
    cf = S.confirm_request(T, "S-0001")
    S.shoot_save(T, "S-0001", lines=[{"package": "Wedding Gold"}, {"name": "Album extra", "price": 12000}])
    with pytest.raises(S.PhotoError, match="badal"):
        S.decide(T, cf["card"]["id"], True, cf["card"]["hash"], by_tap=True)
    assert S.card_view(T, cf["card"]["id"])["status"] == "stale"
    # price blank = no client card
    S.shoot_save(T, "S-0001", lines=[{"name": "Mystery item"}])
    with pytest.raises(S.PhotoError, match="daam"):
        S.quote_request(T, "S-0001")
    S.shoot_save(T, "S-0001", lines=[{"package": "Wedding Gold"}])
    cf = S.confirm_request(T, "S-0001")
    # someone else grabbed the slot after the card was made: the tap itself refuses
    S.CLK["t"] = NOW + timedelta(hours=49)                         # S-0001's hold lapsed
    other = _shoot(S, client="Late Client", start="17:00", end="20:00")
    S.hold(T, other["number"])
    with pytest.raises(S.PhotoError):
        S.decide(T, cf["card"]["id"], True, cf["card"]["hash"], by_tap=True)
    S.release_hold(T, other["number"])
    cf = S.confirm_request(T, "S-0001")
    r = S.decide(T, cf["card"]["id"], True, cf["card"]["hash"], by_tap=True)
    v = S.shoot_view(T, "S-0001")
    assert v["status"] == "confirmed" and len(v["stages"]) == 3 and abs(sum(x["amount"] for x in v["stages"]) - v["quote"]["total"]) < 0.01
    # pay request -> UPI to HER UPI ID
    p = S.pay_request(T, "S-0001")
    pr = S.decide(T, p["card"]["id"], True, p["card"]["hash"], by_tap=True)
    assert "upi://pay?pa=lenskahani%40okicici" in pr["draft"]["upi"]
    # receipts by her only
    with pytest.raises(S.PhotoError, match="owner"):
        S.paid(T, "S-0001", 30000, actor="staff:1")
    rc = S.paid(T, "S-0001", 30090, "upi", "UTR998877")
    assert rc["receipt"].startswith("R/2627/") and S.receipt_pdf(T, "S-0001", rc["receipt"]).startswith(b"%PDF")
    assert S.shoot_view(T, "S-0001")["stages"][0]["paid"] is True


def test_money_cards_fingerprint_cancel_refund(pa):
    S = pa
    from app import approvekey as ak
    _studio(S)
    _shoot(S)
    d = S.discount_request(T, "S-0001", 5000, reason="repeat client")
    phone = Phone("phone-1")
    ak.register(T, phone.device_id, phone.pub, "Pixel")
    with pytest.raises(S.PhotoError) as e:
        S.decide(T, d["card"]["id"], True, d["card"]["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.card_challenge(T, d["card"]["id"])
    with pytest.raises(S.PhotoError, match="fingerprint_invalid"):
        S.decide(T, d["card"]["id"], True, d["card"]["hash"], proof=Phone("phone-1").sign(ch), by_tap=True)
    ch = S.card_challenge(T, d["card"]["id"])
    S.decide(T, d["card"]["id"], True, d["card"]["hash"], proof=phone.sign(ch), by_tap=True)
    assert S.quote(T, "S-0001")["discount"] == 5000
    # cancel 50 days before by the client: 50% of what was paid, refund card (fingerprint)
    S.paid(T, "S-0001", 20000)
    out = S.cancel(T, "S-0001", "date change", "client")
    assert "50%" in out["say"] and out["card"]["show"]["amount"] == 10000.0
    assert S.free(T, "2026-12-12", "16:00", "23:00")["free"] is True
    with pytest.raises(S.PhotoError, match="refund"):
        S.refund_sent(T, "S-0001")
    with pytest.raises(S.PhotoError, match="refund"):
        S.forget(T, "S-0001")
    ch = S.card_challenge(T, out["card"]["id"])
    S.decide(T, out["card"]["id"], True, out["card"]["hash"], proof=phone.sign(ch), by_tap=True)
    assert "10,000" in S.refund_sent(T, "S-0001", "UTR1")["say"]
    f = S.forget(T, "S-0001")
    v = S.shoot_view(T, "S-0001")
    assert v["client"] == "Client (hataya)" and v["phone"] == "" and v["refunded"] == 10000.0 and "hata di" in f["say"]


def test_culling_releases_edits_delivery_invoice(pa, tmp_path):
    S = pa
    _studio(S)
    _shoot(S)
    S.hold(T, "S-0001")
    cf = S.confirm_request(T, "S-0001")
    S.decide(T, cf["card"]["id"], True, cf["card"]["hash"], by_tap=True)
    # culling: blurry / dark / duplicate signals, EXIF (GPS + camera) gone from what is kept
    out = S.cull(T, "S-0001", files=[("a.jpg", _jpeg("sharp", gps=True)), ("b.jpg", _jpeg("blur")), ("c.jpg", _jpeg("dark")),
                                     ("d.jpg", _jpeg("sharp"))])
    hints = {p["name"]: p["hint"] for p in out["photos"]}
    assert hints["a.jpg"] == "keep" and hints["b.jpg"] == "reject" and hints["c.jpg"] in ("reject", "maybe")
    assert hints["d.jpg"] == "maybe" and any("duplicate" in w for w in out["photos"][3]["why"])
    from PIL import Image
    path, _ = S.photo_file(T, out["photos"][0]["id"])
    kept = Image.open(path)
    assert not kept.getexif() and 0x8825 not in kept.getexif()
    assert "ishaare" in out["say"]
    S.pick(T, [out["photos"][1]["id"]], "keep")                     # she decides, not Hoola
    assert S.shoot_view(T, "S-0001")["photos"][1]["pick"] == "keep"
    # vision note is used only as a signal
    S_see = S._see
    S._see = lambda jpeg: '{"faces": 2, "eyes_closed": true, "note": "dulhan ki aankh band"}'
    o2 = S.cull(T, "S-0001", files=[("e.jpg", _jpeg("sharp"))])
    S._see = S_see
    assert any("aankhein band" in w for w in o2["photos"][0]["why"])
    # releases: minor needs a guardian; signed needs a proof photo
    with pytest.raises(S.PhotoError, match="guardian"):
        S.release_new(T, "S-0001", "minor", "Aarav")
    rl = S.release_new(T, "S-0001", "minor", "Aarav", "Neha Joshi", uses=["portfolio", "social_media"])
    assert S.release_pdf(T, rl["release"]["id"]).startswith(b"%PDF")
    with pytest.raises(S.PhotoError, match="proof"):
        S.release_signed(T, rl["release"]["id"])
    sg = S.release_signed(T, rl["release"]["id"], _jpeg("sharp", gps=True))
    assert sg["release"]["status"] == "signed"
    p, _ = S.release_proof(T, rl["release"]["id"])
    assert not Image.open(p).getexif()
    S.release_withdraw(T, rl["release"]["id"])
    assert S.shoot_view(T, "S-0001")["releases"][0]["status"] == "withdrawn"
    with pytest.raises(S.PhotoError, match="wapas"):
        S.release_signed(T, rl["release"]["id"], _jpeg())
    # edits counted vs the package's retouches
    for i in range(41):
        S.edit(T, "S-0001", f"IMG_{i}.jpg", "skin smooth karo")
    e = S.edit(T, "S-0001", index=1, status="done")
    assert e["edits"]["included"] == 40 and e["edits"]["extra"] == 1 and "daam" in e["say"]
    # delivery only via her https link, a card, then the message draft
    with pytest.raises(S.PhotoError, match="https"):
        S.delivery_request(T, "S-0001", "http://example.com/x")
    S.mark_shot(T, "S-0001")
    dl = S.delivery_request(T, "S-0001", "https://drive.google.com/drive/folders/abc", "400 photos", "2027-01-31")
    assert any("baaki" in w for w in dl["card"]["show"]["warn"])
    r = S.decide(T, dl["card"]["id"], True, dl["card"]["hash"], by_tap=True)
    assert "drive.google.com" in r["draft"]["text"] and S.shoot_view(T, "S-0001")["status"] == "delivered"
    inv = S.invoice_request(T, "S-0001")
    ri = S.decide(T, inv["card"]["id"], True, inv["card"]["hash"], by_tap=True)
    assert "INV/2627/0001" in ri["say"] and S.STORED[-1][1].startswith(b"%PDF")


def test_worker_and_day(pa):
    S = pa
    _studio(S)
    S.save_settings(T, rpc_number="RPC-123", rpc_until="2026-11-10")
    _shoot(S, day="2026-10-24", start="10:00", end="14:00", drone=True, location="Aga Khan Palace monument")
    S.hold(T, "S-0001")
    cf = S.confirm_request(T, "S-0001")
    S.decide(T, cf["card"]["id"], True, cf["card"]["hash"], by_tap=True)
    v = S.shoot_view(T, "S-0001")
    keys = {c["key"] for c in v["checks"]}
    assert "asi" in keys and "drone_zone" in keys and "drone_uin" not in keys      # nano drone (249 g)
    S.checks_tick(T, "S-0001", "asi")
    assert next(c for c in S.shoot_view(T, "S-0001")["checks"] if c["key"] == "asi")["done"] is True
    S.EVENTS.clear()
    out = S.tick(NOW)
    says = " ".join(p["say"] for k, p in S.EVENTS if k == "photoassist_alert")
    assert "Kal S-0001" in says and "RPC" in says and out["alerts"] >= 2
    assert any(k == "photoassist_day" for k, _ in S.EVENTS)                       # 10:30 IST > 08:00 morning time
    n = len(S.EVENTS)
    S.tick(NOW + timedelta(minutes=1))
    assert len(S.EVENTS) == n                                                     # once each
    d = S.day(T)
    assert d["tomorrow"] and "Kal" in d["say"]
    # delivery reminder after the shoot
    S.CLK["t"] = NOW + timedelta(days=2)
    S.mark_shot(T, "S-0001")
    S.save_settings(T, delivery_days=3)
    S.tick(NOW + timedelta(days=2))
    assert any(p.get("kind") == "delivery" for k, p in S.EVENTS if k == "photoassist_alert")


def test_tools_and_api(pa):
    S = pa
    from app.agent.photoassist_tools import PHOTOASSIST_HANDLERS, PHOTOASSIST_TOOLS
    from app.agent.tools import ToolError
    for t in PHOTOASSIST_TOOLS:
        props = t["input_schema"]["properties"]
        assert all(r in props for r in t["input_schema"]["required"])
    ctx = conv_ctx()

    def run(_tool, c=ctx, **a):
        return asyncio.run(PHOTOASSIST_HANDLERS[_tool](c, **a))
    run("photo_assist", action="settings", studio="Lens Kahani", upi_id="lens@okhdfc")
    run("photo_assist", action="package", name="Portrait", price=4000, unit="shoot")
    sh = run("photo_assist", action="shoot", kind="portrait", client="Meera", phone="9822012345", day="2026-11-20", start="shaam 5 baje",
             end="7 pm", lines=[{"package": "Portrait"}])
    assert sh["shoot"]["start"] == "17:00" and sh["shoot"]["end"] == "19:00"
    run("photo_assist", action="hold", shoot="S-0001")
    staff = conv_ctx()
    staff.actor = "staff:1"
    with pytest.raises(ToolError, match="owner"):
        run("photo_assist", c=staff, action="paid", shoot="S-0001", amount=100)
    with pytest.raises(ToolError, match="owner"):
        run("photo_assist", c=staff, action="discount", shoot="S-0001", amount=100)
    cust = conv_ctx()
    cust.actor = "customer:wa:1"
    with pytest.raises(ToolError):
        run("photo_assist", c=cust, action="shoot", client="x")
    card = run("photo_assist", c=staff, action="confirm", shoot="S-0001")
    assert card["status"] == "needs_tap" and S.shoot_view(T, "S-0001")["status"] == "hold"       # tool can't decide
    assert run("photo_assist_dekho", what="free", day="2026-11-20", start="18:00", end="20:00")["free"] is False
    assert run("photo_assist_dekho", what="day")["waiting"] == 1

    from app.photoassist.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/photoassist").status_code == 200
    cid, h = card["card"]["id"], card["card"]["hash"]
    assert c.post(f"/api/photoassist/cards/{cid}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    r = c.post(f"/api/photoassist/cards/{cid}/decide", json={"yes": True, "hash": h})
    assert r.status_code == 200 and r.json()["card"]["status"] == "approved"
    assert c.get("/api/photoassist/shoots/S-0001").json()["status"] == "confirmed"
    assert c.get("/api/photoassist/shoots/S-0001/quote.pdf").content.startswith(b"%PDF")
    up = c.post("/api/photoassist/shoots/S-0001/cull", files={"file": ("x.jpg", _jpeg(), "image/jpeg")}, data={"look": "false"})
    assert up.status_code == 200 and up.json()["photos"][0]["hint"] == "keep"
    pid = up.json()["photos"][0]["id"]
    assert c.get(f"/api/photoassist/photos/{pid}").status_code == 200
    rl = c.post("/api/photoassist/shoots/S-0001/release_new", json={"kind": "model", "person": "Meera", "uses": ["portfolio"]}).json()
    rid = rl["release"]["id"]
    assert c.post(f"/api/photoassist/releases/{rid}/proof", files={"file": ("s.jpg", _jpeg(), "image/jpeg")}).json()["release"]["status"] == "signed"
    assert c.get("/api/photoassist/calendar", params={"month": "2026-11"}).json()["shoots"]
    assert c.put("/api/photoassist/settings", json={"upi_id": "not a upi"}).status_code == 400
    two = c.post("/api/photoassist/shoots", json={"kind": "event", "client": "X", "day": "2026-11-20", "start": "18:00", "end": "21:00"}).json()
    assert c.post(f"/api/photoassist/shoots/{two['shoot']['number']}/hold").status_code == 400                     # double booking
    assert c.post("/api/photoassist/shoots/S-0001/nope").status_code == 404
