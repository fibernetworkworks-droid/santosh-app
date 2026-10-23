"""Logistics Sahayak: e-way bill rules (limits, validity, ODC, extension window, 180-day document age), her words -> times,
shipments with GSTIN checks, e-way bill readiness -> card -> ONLY her tap files it (manual JSON or a fake GSP), stale cards,
tracking only from real updates + location shares + courier desk, delay / EWB expiry / silence alerts once each, customer
drafts she sends (business WhatsApp only on her tap), LR / challan / packing PDFs, POD photo with EXIF stripped, tools, API."""
import asyncio
import io
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.logistics.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
UTC = timezone.utc


def gstin(state: str, pan: str = "ABCDE1234F", ent: str = "1") -> str:
    from app.india.money import _GST_CHARS
    body = f"{state}{pan}{ent}Z"
    total = 0
    for i, ch in enumerate(body):
        prod = _GST_CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += prod // 36 + prod % 36
    return body + _GST_CHARS[(36 - total % 36) % 36]


MINE = gstin("27", "AAACI1234K")
NAG = gstin("27", "BBBCS5678L")
GOA = gstin("30", "CCCDG9012M")


@pytest.fixture
def lg(env, monkeypatch, tmp_path):
    from app.logistics import service as S
    monkeypatch.setenv("LOGISTICS_DIR", str(tmp_path / "logi"))
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    S.EVENTS = events
    S.save_settings(T, firm="Ingle Traders", role="trader", gstin=MINE, address="Main Road", place="Akot", pincode="444101",
                    phone="8956555723", morning_time="08:30")
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def test_rules():
    from app.logistics import rules as R
    assert R.ewb_needed(60000, "27", "30")["needed"] and not R.ewb_needed(80000, "27", "27")["needed"]
    assert R.ewb_needed(120000, "27", "27")["needed"] and R.ewb_needed(60000, "19", "19")["needed"]
    assert R.validity_days(450) == 3 and R.validity_days(200) == 1 and R.validity_days(201) == 2 and R.validity_days(45, odc=True) == 3
    ist = timezone(timedelta(hours=5, minutes=30))
    start = datetime(2026, 10, 23, 15, 0, tzinfo=ist)
    up = R.valid_upto(start, 150)
    assert up == datetime(2026, 10, 24, 23, 59, 59, tzinfo=ist)
    assert R.ewb_alert(up, up - timedelta(hours=3))["kind"] == "ewb_expiring"
    assert R.ewb_alert(up, up + timedelta(hours=2))["kind"] == "ewb_expired" and "extension abhi" in R.ewb_alert(up, up + timedelta(hours=2))["text"]
    assert "Naya EWB" in R.ewb_alert(up, up + timedelta(hours=9))["text"]
    assert R.ewb_alert(up, up - timedelta(days=3)) is None
    assert R.vehicle_ok("MH 30 AB 1234") and R.vehicle_ok("22BH1234AA") and not R.vehicle_ok("MH30")
    loc = R.parse_location("Main yahan hoon https://maps.google.com/?q=20.7002,77.0082 driver")
    assert loc["lat"] == 20.7002 and "20.70020,77.00820" in loc["maps"]
    assert R.parse_location("https://maps.app.goo.gl/AbC123")["lat"] is None and R.parse_location("koi link nahi") is None
    assert R.status_from_words("gaadi nikal gayi bhai") == "dispatched" and R.status_from_words("naka par rok liya") == "held"
    assert R.status_from_words("maal utar gaya, unload ho gaya") == "delivered" and R.status_from_words("chai pi rahe") == ""
    cap = R.liability_cap(5000, 300000)
    assert cap["cap"] == 50000 and R.liability_cap(5000, 20000)["cap"] == 20000
    t = R.customer_text("dispatch", {"name": "Ramesh Sharma", "business": "Ingle Traders"})
    assert "Ramesh" in t and "[gaadi no.]" in t and "[pahunchne ka samay]" in t       # unknowns are blanks, never guessed
    assert R.uqc("bori") == "BAG" and R.uqc("KGS") == "KGS"


def test_when(lg):
    S = lg
    base = datetime(2026, 10, 23, 6, 0, tzinfo=UTC)               # 11:30 IST
    ist = lambda d: d.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert ist(S.when("kal shaam", T, base)).strftime("%d %H:%M") == "24 18:00"
    assert ist(S.when("parso 11 baje subah", T, base)).strftime("%d %H") == "25 11"
    assert ist(S.when("25-10-2026 6 pm", T, base)).strftime("%d %H") == "25 18"
    assert S.when("2 din", T, base) == base + timedelta(days=2)
    assert S.when("5 ghante", T, base) == base + timedelta(hours=5)
    assert S.when("jab bhi", T, base) is None


def ship(S, **kw):
    args = dict(consignee="Sharma Hardware", consignee_gstin=GOA, consignee_address="Panaji Market", consignee_place="Panaji",
                consignee_pincode="403001", consignee_phone="9876543210",
                goods=[{"name": "Cement OPC 53", "hsn": "2523", "qty": 120, "unit": "bag", "value": 45600, "gst": 18},
                       {"name": "TMT bar", "hsn": "7214", "qty": 1, "unit": "ton", "value": 52000, "gst": 18}],
                doc_no="INV-45", doc_date="2026-10-22", vehicle_no="MH30AB1234", transporter_name="Shree Roadlines", distance_km=640,
                freight=18000, freight_by="to_pay", packages=121, package_kind="bag", weight_kg=7000)
    args.update(kw)
    return S.new_shipment(T, **args)


def test_shipment_ewb_her_tap_manual(lg):
    S = lg
    with pytest.raises(S.LogiError):
        S.new_shipment(T, "Bad Co", consignee_gstin="27ABCDE1234F1Z1")
    assert not S.shipments(T)
    r = ship(S, vehicle_no="", distance_km=0)
    v = r["shipment"]
    assert v["number"] == "S-0001" and v["ewb"]["needed"] and not v["ewb"]["intra"]
    assert any("E-way bill chahiye" in w for w in v["warnings"]) and any("Doori" in w for w in v["warnings"])
    rd = S.ewb_ready(T, "S-0001")
    assert any("Doori" in b for b in rd["blockers"])
    with pytest.raises(S.LogiError):
        S.ewb_request(T, "S-0001")                                   # blockers stop the card
    S.update_shipment(T, "S-0001", distance_km=640, vehicle_no="MH30AB1234")
    rd = S.ewb_ready(T, "INV-45")
    p = rd["payload"]
    assert not rd["blockers"] and rd["validity_days"] == 4
    assert p["fromGstin"] == MINE and p["toStateCode"] == 30 and p["igstValue"] == round(97600 * 0.18, 2) and p["cgstValue"] == 0
    assert p["itemList"][0]["hsnCode"] == 2523 and p["itemList"][0]["qtyUnit"] == "BAG" and p["vehicleNo"] == "MH30AB1234"
    card = S.ewb_request(T, "S-0001")
    assert card["status"] == "needs_tap" and "logistics_ewb" in kinds(S)
    a = card["ask"]
    with pytest.raises(S.LogiError):
        S.decide_ewb(T, a["id"], True, a["hash"])                    # not a tap = refused
    with pytest.raises(S.LogiError):
        S.decide_ewb(T, a["id"], True, "wrong", by_tap=True)
    res = S.decide_ewb(T, a["id"], True, a["hash"], by_tap=True)
    assert res["ask"]["status"] == "manual" and res["files"] and "Bulk" in " ".join(res["result"]["steps"])
    assert "pc_file" in kinds(S)
    with pytest.raises(S.LogiError):
        S.decide_ewb(T, a["id"], True, a["hash"], by_tap=True)       # once only
    with pytest.raises(S.LogiError):
        S.ewb_set(T, "S-0001", "1234")
    r = S.ewb_set(T, "S-0001", "3410 1234 5678")
    assert r["shipment"]["ewb"]["no"] == "341012345678" and r["shipment"]["ewb"]["valid_upto"]
    # a changed shipment makes an old card stale
    S.update_shipment(T, "S-0001", vehicle_no="MH30AB9999")
    card2 = S.ewb_request(T, "S-0001")
    S.update_shipment(T, "S-0001", distance_km=700)
    with pytest.raises(S.LogiError):
        S.decide_ewb(T, card2["ask"]["id"], True, card2["ask"]["hash"], by_tap=True)


def test_gsp_and_part_b(lg):
    S = lg
    from app.logistics import ewb as E
    calls = []

    def handler(req: httpx.Request):
        body = json.loads(req.content)
        calls.append((req.url.path, body.get("action"), dict(req.headers)))
        if body.get("action") == "ACCESSTOKEN":
            return httpx.Response(200, json={"status": "1", "authtoken": "tok123"})
        if body["action"] == "GENEWAYBILL":
            assert req.headers["authtoken"] == "tok123" and body["docNo"] == "INV-45"
            return httpx.Response(200, json={"status": "1", "data": {"ewayBillNo": 351002003004, "ewayBillDate": "23/10/2026 11:30:00 AM",
                                                                       "validUpto": "26/10/2026 11:59:00 PM"}})
        if body["action"] == "VEHEWB":
            return httpx.Response(200, json={"status": "1", "data": {"vehUpdDate": "24/10/2026 09:00:00 AM", "validUpto": "26/10/2026 11:59:00 PM"}})
        return httpx.Response(400, json={"status": "0", "error": {"message": "bad"}})

    E.set_transport(httpx.MockTransport(handler))
    try:
        with pytest.raises(S.LogiError):
            S.set_ewb_keys(T, "gsp", {"base_url": "https://gsp.example.in"})
        info = S.set_ewb_keys(T, "gsp", {"base_url": "https://gsp.example.in", "client_id": "c", "client_secret": "s", "gstin": MINE,
                                         "username": "apiuser", "password": "pw"})
        assert info["joined"] and "pw" not in json.dumps(S.settings(T))         # never shown back
        ship(S)
        a = S.ewb_request(T, "S-0001")["ask"]
        r = S.decide_ewb(T, a["id"], True, a["hash"], by_tap=True)
        assert r["ask"]["status"] == "done" and r["shipment"]["ewb"]["no"] == "351002003004" and "26 Oct" in r["shipment"]["ewb"]["valid_upto"]
        with pytest.raises(S.LogiError):
            S.ewb_request(T, "S-0001", "part_b", vehicle_no="MH30XY4321")      # reason needed
        b = S.ewb_request(T, "S-0001", "part_b", vehicle_no="MH30XY4321", reason="breakdown")["ask"]
        r = S.decide_ewb(T, b["id"], True, b["hash"], by_tap=True)
        assert r["shipment"]["vehicle_no"] == "MH30XY4321" and [c[1] for c in calls].count("VEHEWB") == 1
        rej = S.ewb_request(T, "S-0001", "part_b", vehicle_no="MH30XY0001", reason="others")["ask"]
        assert S.decide_ewb(T, rej["id"], False, rej["hash"], by_tap=True)["ask"]["status"] == "rejected"
        assert [c[1] for c in calls].count("VEHEWB") == 1
    finally:
        E.set_transport(None)


def test_tracking_drafts_alerts(lg, monkeypatch):
    S = lg
    ship(S, eta="")
    with pytest.raises(S.LogiError):
        S.update(T, "S-0001")                                         # nothing to say = refused
    base = S._now()
    r = S.update(T, "S-0001", text="gaadi nikal gayi Akot se", eta=(base + timedelta(hours=1)).isoformat(), source="driver")
    v = r["shipment"]
    assert v["status"] == "dispatched" and v["dispatch_at"] and r["drafts"]
    m = r["drafts"][0]
    assert m["kind"] == "dispatch" and m["wa_link"].startswith("https://wa.me/919876543210") and "MH30AB1234" in m["text"]
    assert m["status"] == "draft" and "logistics_update" in kinds(S)
    with pytest.raises(S.LogiError):
        S.update(T, "S-0001", status="delayed")                       # a delay needs its real reason
    loc = S.location(T, "MH30AB1234", "driver ki location https://www.google.com/maps/@19.0760,72.8777,15z")
    assert loc["location"]["lat"] == 19.076
    with pytest.raises(S.LogiError):
        S.location(T, "S-0001", "pata nahi")
    # alerts: late vs ETA, EWB expiring, silence; each once
    late_at = base + timedelta(hours=13)                               # ETA + 12 h, no news for 13 h
    S.ewb_set(T, "S-0001", "351002003004", valid_upto=(late_at + timedelta(hours=3)).isoformat())
    al = S.check_alerts(T, late_at)
    ks = {a["kind"] for a in al}
    assert {"late", "ewb_expiring", "silent"} <= ks, ks
    assert S.check_alerts(T, late_at) == []
    out = S.tick(late_at + timedelta(minutes=1))
    assert out["alerts"] == 0
    monkeypatch.setattr(S, "_now", lambda: late_at)
    b = S.board(T)
    assert b["moving"] and b["late"] and "late" in b["say"]
    S.message_sent(T, m["id"])
    assert S.get(T, "S-0001")["messages"][0]["status"] in ("sent", "draft")


def test_business_whatsapp_only_on_tap(lg, monkeypatch):
    S = lg
    from app.db import session
    from app.employee import inbox
    from app.employee.models import BizContact
    r = ship(S)
    m = S.draft(T, r["shipment"]["id"], "in_transit", where="Belgaum")["message"]
    assert "Belgaum" in m["text"]
    sent = []

    async def fake_send(tenant, cid, text, by="owner", force=False):
        sent.append(text)
        return {"ok": True}

    monkeypatch.setattr(inbox, "send", fake_send)
    with pytest.raises(S.LogiError):
        asyncio.run(S.send_business(T, m["id"], m["hash"]))            # not a tap
    with pytest.raises(S.LogiError):
        asyncio.run(S.send_business(T, m["id"], m["hash"], by_tap=True))   # never wrote to the business number
    with session() as s:
        s.add(BizContact(tenant_id=T, wa_id="919876543210", name="Sharma"))
    with pytest.raises(S.LogiError):
        asyncio.run(S.send_business(T, m["id"], m["hash"], by_tap=True))   # still has a [blank] (ETA unknown)
    m2 = S.edit_message(T, m["id"], "Namaste, aapka maal Belgaum ke paas hai, kal shaam tak.")["message"]
    with pytest.raises(S.LogiError):
        asyncio.run(S.send_business(T, m["id"], m["hash"], by_tap=True))   # old hash
    out = asyncio.run(S.send_business(T, m["id"], m2["hash"], by_tap=True))
    assert out["message"]["via"] == "business" and sent == [m2["text"]]


def test_docs_pod_and_courier(lg, monkeypatch, tmp_path):
    S = lg
    S.save_settings(T, carrier_reg="MH/CR/2024/117", gta_rate=5, terms="Maal ki packing consignor ki zimmedari.")
    ship(S)
    d = S.documents(T, "S-0001", ["lr", "packing", "challan", "invoice"])
    assert len(d["files"]) == 3 and any("Thok" in n for n in d["notes"])
    v = S.get(T, "S-0001")
    assert v["lr_no"].startswith("LR/2627/") and v["doc_type"] == "challan" and v["doc_no"].startswith("DC/2627/")
    pdf, no = S.lr_pdf(T, "S-0001")
    assert pdf[:4] == b"%PDF" and no == v["lr_no"] and pdf.count(b"/Type /Page") >= 3
    # POD photo: EXIF / GPS removed, delivered, damage -> claim notice line
    from PIL import Image
    im = Image.new("RGB", (800, 600), (200, 180, 160))
    ex = Image.Exif()
    ex[0x010F] = "PhoneMaker"
    ex[0x8825] = {1: "N", 2: (20.0, 42.0, 0.0)}
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=ex)
    p = S.add_photo(T, "S-0001", buf.getvalue(), "pod", receiver="Raju", damaged=True, remarks="2 bag phate")
    assert p["shipment"]["status"] == "delivered" and p["notes"] and "180 din" in p["notes"][0]
    stored = Image.open(S.photo_file(T, p["photo"]["id"]))
    assert not dict(stored.getexif())
    assert any(mm["kind"] == "delivered" for mm in S.get(T, "S-0001")["messages"])
    with pytest.raises(S.LogiError):
        S.add_photo(T, "S-0001", b"not an image")
    # courier: statuses only from the courier desk
    ship(S, consignee="Patil Stores", consignee_gstin=NAG, consignee_place="Nagpur", consignee_pincode="440001", vehicle_no="",
         courier="delhivery", awb="1234567890123", fleet="courier", mode="courier")
    t = S.track(T, "1234567890123")
    assert "Courier desk" in t["say"] and "delhivery" in t["say"] and t["shipment"]["status"] == "booked"   # no key: her courier's page
    monkeypatch.setattr(S, "_courier_track", lambda tenant, courier, awb: {"status": "out_for_delivery", "events": [
        {"at": "2026-10-24T07:00:00", "what": "Out for delivery", "where": "Nagpur hub"}]})
    t = S.track(T, "S-0002")
    assert t["shipment"]["status"] == "out_for_delivery" and t["new_events"] == 1
    assert S.track(T, "S-0002")["new_events"] == 0


def test_tools_and_api(lg):
    S = lg
    from app.agent.logistics_tools import LOGISTICS_HANDLERS as H
    from app.agent.tools import ToolError
    ctx = conv_ctx()
    r = asyncio.run(H["logistics"](ctx, action="new", consignee="Sharma Hardware", consignee_gstin=GOA, consignee_pincode="403001",
                                   goods_text="cement 120 bag @ 380", doc_no="INV-46", doc_date="2026-10-22", vehicle_no="MH30AB1234",
                                   distance_km=640))
    assert r["shipment"]["value"] == 45600
    asyncio.run(H["logistics"](ctx, action="edit", shipment="S-0001",
                               goods=[{"name": "Cement", "hsn": "2523", "qty": 120, "unit": "bag", "value": 45600, "gst": 18}]))
    c = asyncio.run(H["logistics"](ctx, action="ewb", shipment="S-0001"))
    assert c["status"] == "needs_tap" and "hash" not in json.dumps(c)          # the model never gets the hash
    staff = conv_ctx()
    staff.actor = "staff:abc"
    with pytest.raises(ToolError):
        asyncio.run(H["logistics"](staff, action="ewb_number", shipment="S-0001", ewb_no="351002003004"))
    cust = conv_ctx()
    cust.actor = "customer:wa:9999"
    with pytest.raises(ToolError):
        asyncio.run(H["logistics_dekho"](ctx, what="nonsense"))
    with pytest.raises(ToolError):
        asyncio.run(H["logistics"](cust, action="update", shipment="S-0001", text="delivered"))
    b = asyncio.run(H["logistics_dekho"](ctx, what="board"))
    assert "ewb_missing" in b
    from app.logistics.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    with TestClient(app) as cl:
        o = cl.get("/api/logistics").json()
        assert o["shipments"] and o["board"]["say"]
        ask = S.EVENTS[[k for k, _ in S.EVENTS].index("logistics_ewb")][1]["ask"]
        assert cl.post(f"/api/logistics/ewb/{ask['id']}/decide", json={"yes": True, "hash": "x"}).status_code == 400
        d = cl.post(f"/api/logistics/ewb/{ask['id']}/decide", json={"yes": True, "hash": ask["hash"]}).json()
        assert d["ask"]["status"] == "manual"
        assert cl.post("/api/logistics/shipments/S-0001/ewb_number", json={"ewb_no": "351002003004"}).json()["shipment"]["ewb"]["no"]
        u = cl.post("/api/logistics/shipments/S-0001/update", json={"text": "out for delivery hai"}).json()
        assert u["shipment"]["status"] == "out_for_delivery"
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (100, 100)).save(buf, "PNG")
        ph = cl.post("/api/logistics/shipments/S-0001/photo", files={"file": ("pod.png", buf.getvalue(), "image/png")},
                     data={"stage": "pod", "receiver": "Raju"}).json()
        assert ph["shipment"]["status"] == "delivered"
        assert cl.get(f"/api/logistics/photos/{ph['photo']['id']}").status_code == 200
        assert cl.post("/api/logistics/register").json()["file"]["name"].endswith(".xlsx")
