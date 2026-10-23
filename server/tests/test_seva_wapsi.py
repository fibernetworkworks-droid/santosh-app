"""Wapsi Sahayak (returns & refunds desk): policy from her words, the check by code (seller fault never 'reject'),
photos with metadata stripped, pickup (manual + fake Shiprocket), QC, the refund sum by code, the refund card that ONLY
her tap (card hash + fingerprint when a phone key is active) approves, refund done with UTR, credit note, gateway
read-back (fake Razorpay), fraud signals, tools (owner-only, customer-safe biz tools), API, morning note."""
import asyncio
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.wapsi.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 23)
POLICY = ("7 din return, kapde 10 din mein return, innerwear aur cosmetics return nahi hota. tag lage hone chahiye. "
          "man badalne par 10% restocking fee katenge. exchange milega. refund original mode mein. "
          "electronics ke liye unboxing video chahiye. pickup charge ₹60. refund 5 din mein")


def jpeg(color=(200, 30, 30), exif_date="2026:10:20 10:00:00", size=(800, 600)) -> bytes:
    from PIL import Image
    im = Image.new("RGB", size, color)
    ex = Image.Exif()
    ex[306] = exif_date
    ex[271] = "TestCam"
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=ex.tobytes())
    return buf.getvalue()


@pytest.fixture
def wp(env, monkeypatch, tmp_path):
    from app.wapsi import service as S
    monkeypatch.setattr(S, "today", lambda t: DAY)
    monkeypatch.setenv("WAPSI_DIR", str(tmp_path / "wapsi"))
    monkeypatch.setattr(S, "_see", lambda jpg, prompt: json.dumps({"product_visible": True, "matches_order": True, "damage_visible": True,
                                                                   "damage": "kurti phati", "packaging_visible": True, "label_visible": True,
                                                                   "looks_used": False, "note": "phata hua dikh raha"}))
    return S


def setup(S):
    S.save_settings(T, business="Riya Fashions", state="Maharashtra", address="Akot, Akola",
                    warehouse={"name": "Riya Fashions", "phone": "9822000000", "address": "Shop 4, Main Rd", "city": "Akot", "state": "Maharashtra",
                               "pincode": "444101"})
    return S.set_policy(T, POLICY)


def test_rules():
    from app.wapsi import rules as R
    p, got = R.parse_policy(POLICY)
    assert p["window_days"] == {"default": 7, "clothes": 10} and set(p["non_returnable"]) == {"innerwear", "cosmetics"}
    assert p["need_tags"] and p["restocking_pct"] == 10 and p["reverse_fee"] == 60 and p["video_for"] == ["electronics"]
    assert p["exchange"] and p["refund_mode"] == "original" and p["refund_days"] == 5 and len(got) >= 8
    assert R.reason_of("size chhota hai") == "size_fit" and R.reason_of("screen tooti aayi") == "damaged"
    assert R.reason_of("galat colour bheja") == "wrong_item" and R.category_of("Blue cotton kurti") == "clothes"
    items = [{"name": "Lipstick", "category": "cosmetics", "qty": 1, "price": 499}]
    on = DAY
    # change of mind on a non-returnable item -> reject suggestion; the same item arriving broken -> never reject
    assert R.check(p, "changed_mind", items, date(2026, 10, 20), on, {})["verdict"] == "reject_suggest"
    broken = R.check(p, "damaged", items, date(2026, 10, 20), on, {"photos": 0})
    assert broken["verdict"] == "ask_more" and broken["fault"] and any("photo" in a.lower() for a in broken["asks"])
    assert R.check(p, "damaged", items, date(2026, 10, 20), on, {"photos": 2, "look": {"damage_seen": True}})["verdict"] == "approve"
    # out of window: change of mind = reject suggestion, a defect = her decision, not a reject
    k = [{"name": "Kurti", "category": "clothes", "qty": 1, "price": 899}]
    assert R.check(p, "size_fit", k, date(2026, 10, 1), on, {})["verdict"] == "reject_suggest"
    assert R.check(p, "size_fit", k, date(2026, 10, 15), on, {})["verdict"] == "approve"      # 8 days, clothes have 10
    assert R.check(p, "defective", k, date(2026, 9, 1), on, {"photos": 1})["verdict"] == "ask_more"
    # refund sum: coupon pro-rata, restocking + pickup fee only for change of mind, shipping back when it was her fault
    items2 = [{"name": "Kurti", "qty": 1, "price": 1000, "gst_pct": 5, "order_qty": 1}, {"name": "Dupatta", "qty": 1, "price": 500, "gst_pct": 5}]
    order = {"items_total": 1500, "coupon": 150, "shipping": 60}
    c = R.refund_calc(p, "size_fit", items2[:1], order)
    assert c["lines"][0]["coupon_share"] == 100 and c["items_value"] == 900
    assert [d["amount"] for d in c["deductions"]] == [90.0, 60.0] and c["add"] == [] and c["total"] == 750
    f = R.refund_calc(p, "damaged", items2[:1], order)
    assert f["deductions"] == [] and f["add"][0]["amount"] == 60 and f["total"] == 960
    assert f["gst"]["taxable"] == round(900 / 1.05, 2) and f["gst"]["cgst"] + f["gst"]["sgst"] == f["gst"]["tax"]
    assert R.refund_calc(p, "damaged", items2[:1], order, same_state=False)["gst"]["igst"] == f["gst"]["tax"]
    assert R.refund_calc(p, "size_fit", items2, order)["add"] == []
    whole = R.refund_calc({**p, "ship_back_on_full": True}, "size_fit", items2, order)
    assert any("poora order" in a["what"] for a in whole["add"])
    # store credit is never forced; COD goes to the customer's own UPI
    m, notes = R.refund_mode({**p, "refund_mode": "store_credit"}, "size_fit", "", "upi")
    assert m == "original" and "zabardasti" in notes[0]
    assert R.refund_mode(p, "size_fit", "store_credit", "upi")[0] == "store_credit"
    assert R.refund_mode(p, "damaged", "", "cod")[0] == "upi"
    sig = R.signals([{"days_ago": 10, "reason": "size_fit"}, {"days_ago": 30, "reason": "changed_mind"}, {"days_ago": 50, "reason": "quality"}],
                    {"reason": "size_fit", "categories": ["clothes"], "value": 900}, {"checklist": {"not_empty": False}})
    kinds = {s["kind"] for s in sig}
    assert {"serial_returner", "wardrobing", "empty_box"} <= kinds


def test_full_flow_her_tap_only(wp):
    S = wp
    pol = setup(S)
    assert "Wapas nahi" in " ".join(pol["understood"]) and pol["policy"]["window_days"]["clothes"] == 10
    r = S.new_return(T, order_ref="ORD-551", customer={"name": "Sneha Patil", "phone": "+91 98765 43210", "address": "12 MG Rd",
                                                       "city": "Pune", "pincode": "411001"},
                     items=[{"name": "Blue cotton kurti", "qty": 1, "price": 1000, "gst_pct": 5, "hsn": "6204"}],
                     reason_text="kurti phati hui aayi", delivered_on="2026-10-21",
                     order={"items_total": 1000, "shipping": 60, "pay_mode": "prepaid", "gateway": "razorpay", "payment_id": "pay_ABC123",
                            "invoice_no": "INV-77", "date": "2026-10-18"})
    v = r["return"]
    assert v["number"] == "R-0001" and v["reason"] == "damaged" and v["check"]["verdict"] == "ask_more" and v["customer"]["state"] == "Maharashtra"
    # photo with EXIF: stored re-encoded without it, the date kept only as a signal
    out = S.add_photo(T, "R-0001", jpeg(), "IMG_1.jpg", "customer")
    from PIL import Image
    path, mime = S.photo_file(T, out["photo_id"])
    assert mime == "image/jpeg" and len(Image.open(path).getexif()) == 0 and Path(path).parent.name == v["id"]
    v = out["return"]
    assert v["look"]["damage_seen"] is True and v["check"]["verdict"] == "approve"
    assert v["photos"][0]["taken_on"] == "2026-10-20" and any(s["kind"] == "old_photo" for s in v["signals"])
    d = S.decide(T, "R-0001", "approve")
    assert d["return"]["status"] == "pickup_manual" and "Courier API nahi juda" in d["say"] and "manzoor" in d["message"]["text"]
    assert d["message"]["whatsapp"].startswith("https://wa.me/919876543210")
    S.set_awb(T, "R-0001", "SR12345678", "Delhivery")
    assert S.received(T, "R-0001")["qc_list"][0]["key"] == "same_item"
    with pytest.raises(S.WapsiError):
        S.prepare_refund(T, "R-0002")
    q = S.qc(T, "R-0001", {"same_item": True, "qty_ok": True, "not_empty": True, "tags_ok": True}, notes="phata hua, sahi")
    rf = q["refund"]
    assert rf["status"] == "waiting" and rf["amount"] == 1060 and rf["mode"] == "original"      # her fault: no fee, delivery charge back
    assert S.return_view(T, "R-0001")["status"] == "refund_waiting"
    # nothing but her tap approves: done before approval refused, a wrong card hash refused
    with pytest.raises(S.WapsiError):
        S.refund_done(T, rf["id"], "UTR123456")
    with pytest.raises(S.WapsiError):
        S.decide_refund(T, rf["id"], True, "deadbeef")
    card = S.approval_card(T, rf["id"])
    assert card["amount"] == "₹1,060" and card["hash"] == rf["hash"]
    ok = S.decide_refund(T, rf["id"], True, rf["hash"])
    assert ok["refund"]["status"] == "approved" and ok["refund"]["credit_note"] == "CN/2627/0001"
    assert ok["how"]["dashboard"].endswith("/payments/pay_ABC123") and ok["how"]["api_request"]["amount"] == 106000
    assert S.approval_card(T, rf["id"]) is None
    pdf = S.credit_note_pdf(T, rf["id"])
    assert pdf[:4] == b"%PDF"
    with pytest.raises(S.WapsiError):
        S.refund_done(T, rf["id"], "x")
    done = S.refund_done(T, rf["id"], "RRN998877")
    assert done["refund"]["status"] == "done" and "RRN998877" in done["message"]["text"]
    assert S.return_view(T, "R-0001")["status"] == "refunded"
    assert S.register_file(T)["file"]["name"] == "Returns_register.xlsx"
    assert S.customer_returns(T, "919876543210")[0]["refund_ref"] == "RRN998877"


def test_change_of_mind_rules_and_rejects(wp):
    S = wp
    setup(S)
    a = S.new_return(T, customer={"name": "Asha", "phone": "9811111111"}, items="Lipstick x1 @ 499", reason="changed_mind", delivered_on="2026-10-22")
    assert a["return"]["check"]["verdict"] == "reject_suggest"
    with pytest.raises(S.WapsiError):
        S.decide(T, a["return"]["number"], "reject")                      # a reason is required
    rj = S.decide(T, a["return"]["number"], "reject", reason="Cosmetics policy mein wapas nahi")
    assert rj["return"]["status"] == "rejected" and "Cosmetics" in rj["message"]["text"]
    # size: approved, QC partial with her deduction, restocking + pickup fee, then she says no on the card -> back to QC
    b = S.new_return(T, customer={"name": "Asha", "phone": "9811111111"}, items=[{"name": "Kurti", "qty": 1, "price": 800}],
                     reason="size_fit", delivered_on="2026-10-20", order={"items_total": 800, "shipping": 50})
    n = b["return"]["number"]
    S.decide(T, n, "approve")
    S.received(T, n)
    with pytest.raises(S.WapsiError):
        S.qc(T, n, {"same_item": True, "tags_ok": False}, result="partial", deduction=100)
    q = S.qc(T, n, {"same_item": True, "tags_ok": False}, result="partial", deduction=100, deduction_reason="tag kata hua")
    rf = q["refund"]
    assert rf["amount"] == 800 - 80 - 60 - 100
    no = S.decide_refund(T, rf["id"], False, rf["hash"], "graahak se baat karungi")
    assert no["refund"]["status"] == "rejected" and S.return_view(T, n)["status"] == "qc_passed"
    again = S.prepare_refund(T, n, mode="store_credit")
    assert again["refund"]["mode"] == "store_credit" and again["refund"]["id"] != rf["id"]
    # damaged lipstick (non-returnable) can't be refused: the warning comes with a reject
    c = S.new_return(T, customer={"name": "Asha", "phone": "9811111111"}, items="Lipstick 499", reason_text="toota hua aaya", delivered_on="2026-10-22")
    assert c["return"]["check"]["verdict"] != "reject_suggest" and c["return"]["check"]["fault"]
    assert "E-Commerce" in S.decide(T, c["return"]["number"], "reject", reason="nahi")["say"]
    sig = S.return_view(T, c["return"]["number"])["signals"]
    assert any(s["kind"] == "serial_returner" for s in sig) is False      # only 2 others yet
    assert S.customer_view(T, "9811111111")["returns"] == 3


def test_shiprocket_and_gateway_fakes(wp, monkeypatch):
    S = wp
    from app.wapsi import couriers, pg
    setup(S)
    calls = []

    def sr(req: httpx.Request):
        calls.append((req.method, req.url.path))
        p = req.url.path
        if p.endswith("/auth/login"):
            return httpx.Response(200, json={"token": "tok123"})
        if p.startswith("/v1/external"):
            assert req.headers.get("authorization") == "Bearer tok123"
        if p.endswith("/orders/create/return"):
            body = json.loads(req.content)
            assert body["pickup_pincode"] == "411001" and body["shipping_pincode"] == "444101" and body["order_items"][0]["qc_enable"]
            return httpx.Response(200, json={"order_id": 991, "shipment_id": 7771, "status": "RETURN PENDING"})
        if p.endswith("/courier/assign/awb"):
            assert json.loads(req.content)["is_return"] == 1
            return httpx.Response(200, json={"awb_assign_status": 1, "response": {"data": {"awb_code": "AWB7771", "courier_name": "Xpressbees"}}})
        if "/courier/track/shipment/7771" in p:
            return httpx.Response(200, json={"tracking_data": {"shipment_track": [{"current_status": "Delivered"}],
                                                               "shipment_track_activities": [{"date": "2026-10-25", "activity": "Delivered", "location": "Akot"}]}})
        if "/v1/payments/pay_X1/refunds" in p:
            assert req.headers.get("authorization", "").startswith("Basic ")
            return httpx.Response(200, json={"items": [{"id": "rfnd_1", "receipt": "RF-0001", "status": "processed", "amount": 89900,
                                                        "acquirer_data": {"arn": "ARN5566"}}]})
        return httpx.Response(404, json={"message": "nope"})

    tr = httpx.MockTransport(sr)
    couriers.set_transport(tr)
    pg.set_transport(tr)
    try:
        S.set_keys(T, "shiprocket", {"email": "api@riya.in", "password": "x" * 10})
        S.set_keys(T, "razorpay", {"key_id": "rzp_live_x", "key_secret": "s" * 20})
        assert S.settings(T)["courier"] == "shiprocket" and "password" not in json.dumps(S.settings(T))
        r = S.new_return(T, customer={"name": "Sneha P", "phone": "9876543210", "address": "12 MG Rd", "city": "Pune", "pincode": "411001"},
                         items=[{"name": "Kurti", "qty": 1, "price": 899}], reason="wrong_item", delivered_on="2026-10-22",
                         order={"pay_mode": "upi", "gateway": "razorpay", "payment_id": "pay_X1"})
        n = r["return"]["number"]
        S.add_photo(T, n, jpeg(exif_date="2026:10:22 18:00:00"), "a.jpg")
        d = S.decide(T, n, "approve")
        assert d["return"]["status"] == "pickup_booked" and d["return"]["pickup"]["awb"] == "AWB7771"
        t = S.track(T, n)
        assert t["status"] == "received" and t["pickup"]["events"][0]["where"] == "Akot"
        rf = S.qc(T, n, {"same_item": True, "qty_ok": True, "not_empty": True})["refund"]
        assert rf["amount"] == 899
        with pytest.raises(S.WapsiError):
            S.pg_check(T, rf["id"])                                          # not approved yet
        S.decide_refund(T, rf["id"], True, rf["hash"])
        with pytest.raises(S.WapsiError):
            S.pg_send(T, rf["id"])                                           # API refunds off on this server
        got = S.pg_check(T, rf["id"])
        assert got["refund"]["status"] == "done" and got["refund"]["utr"] == "ARN5566"
        assert ("POST", "/v1/external/orders/create/return") in calls
    finally:
        couriers.set_transport(None)
        pg.set_transport(None)


def test_tools_api_and_customer(wp, monkeypatch):
    from app.agent.tools import Ctx, ToolError
    from app.agent.wapsi_tools import WAPSI_BIZ_HANDLERS, WAPSI_HANDLERS
    from app.wapsi import api as wapi
    S = wp
    setup(S)
    ctx = conv_ctx()
    run = lambda tool, c=ctx, **a: asyncio.run(WAPSI_HANDLERS[tool](c, **a))    # noqa: E731
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        run("wapsi", staff, action="policy", text="3 din return")
    with pytest.raises(ToolError):
        run("wapsi", action="settings", password="abc")
    r = run("wapsi", action="new", customer={"name": "Ravi", "phone": "9000000001"}, items="Earbuds x1 @ 1499",
            reason_text="ek side se awaaz nahi", delivered_on="2026-10-21", order={"pay_mode": "cod"})
    n = r["return"]["number"]
    assert r["return"]["reason"] == "defective" and r["return"]["items"][0]["category"] == "electronics"
    with pytest.raises(ToolError):
        run("wapsi", staff, action="decide", ref=n, decision="approve")
    assert run("wapsi_dekho", what="returns")["returns"][0]["number"] == n
    assert "E-Commerce" in json.dumps(run("wapsi_dekho", what="rules"))
    # customer on the business WhatsApp: only their own, only records
    from app.db import session
    from app.employee.models import BizContact
    with session() as s:
        c = BizContact(tenant_id=T, wa_id="919000000002", name="Meena")
        s.add(c)
        s.flush()
        cid = c.id
    cust = Ctx(T, ctx.conversation_id, actor=f"customer:{cid}")
    st = asyncio.run(WAPSI_BIZ_HANDLERS["biz_return_start"](cust, items="Saree 1 @ 2500", reason="rang alag hai, galat saree aayi"))
    assert st["number"].startswith("R-") and "owner" in st["note"]
    mine = asyncio.run(WAPSI_BIZ_HANDLERS["biz_return_status"](cust))["returns"]
    assert len(mine) == 1 and mine[0]["what"].startswith("Saree")
    with pytest.raises(ToolError):
        asyncio.run(WAPSI_BIZ_HANDLERS["biz_return_status"](ctx))           # the owner's chat is not a customer
    # API: the refund decide route is her tap; with a phone key active it needs the fingerprint (428)
    app = FastAPI()
    app.include_router(wapi.make_router(lambda: None, lambda: "default"))
    cl = TestClient(app)
    assert cl.get("/api/wapsi").json()["settings"]["business"] == "Riya Fashions"
    rid = cl.get(f"/api/wapsi/returns/{n}").json()["id"]
    assert cl.post(f"/api/wapsi/returns/{rid}/photo", files={"file": ("p.jpg", jpeg(), "image/jpeg")}, data={"stage": "customer"}).status_code == 200
    assert cl.post(f"/api/wapsi/returns/{rid}/decide", json={"decision": "approve"}).json()["return"]["status"] == "pickup_manual"
    assert cl.post(f"/api/wapsi/returns/{rid}/pickup", json={"awb": "DL99887766"}).status_code == 200
    cl.post(f"/api/wapsi/returns/{rid}/received")
    q = cl.post(f"/api/wapsi/returns/{rid}/qc", json={"checklist": {"same_item": True, "serial_ok": True, "works_ok": False}, "result": "pass"}).json()
    assert "UPI ID" in q["say"] or q["refund"]["mode"] == "upi"
    rf = cl.post(f"/api/wapsi/returns/{rid}/refund", json={"mode": "upi", "upi": "ravi@okicici"}).json()["refund"]
    from app import approvekey as ak
    seen = {}
    monkeypatch.setattr(ak, "active_on", lambda t: True)

    def verify(t, kind, target, proof):
        seen["kind"] = kind
        if not proof:
            raise ak.ApproveError("fingerprint_needed")
    monkeypatch.setattr(ak, "verify", verify)
    assert cl.post(f"/api/wapsi/refunds/{rf['id']}/decide", json={"yes": True, "hash": rf["hash"]}).status_code == 428
    assert cl.post(f"/api/wapsi/refunds/{rf['id']}/decide", json={"yes": True, "hash": "bad", "proof": {"x": 1}}).status_code == 400
    ok = cl.post(f"/api/wapsi/refunds/{rf['id']}/decide", json={"yes": True, "hash": rf["hash"], "proof": {"x": 1}}).json()
    assert seen["kind"] == "wapsi" and ok["refund"]["status"] == "approved"
    assert ok["how"]["upi_link"].startswith("upi://pay") and "am=1499.00" in ok["how"]["upi_link"]
    assert cl.post(f"/api/wapsi/refunds/{rf['id']}/done", json={"utr": "412345678901"}).json()["refund"]["status"] == "done"
    assert cl.get(f"/api/wapsi/refunds/{rf['id']}/credit_note.pdf").content[:4] == b"%PDF"
    assert cl.get("/api/wapsi/photos/nope").status_code == 404
    assert cl.post("/api/wapsi/policy", json={"text": "15 din return"}).json()["policy"]["window_days"]["default"] == 15


def test_morning_tick(wp, monkeypatch):
    S = wp
    setup(S)
    S.new_return(T, customer={"name": "Kiran", "phone": "9123456789"}, items="Shirt x1 @ 700", reason="size_fit", delivered_on="2026-10-22")
    with S.session() as s:
        st = s.get(S.WapsiSettings, T)
        st.morning_time = "09:00"
    out = S.tick(datetime(2026, 10, 23, 4, 0, tzinfo=timezone.utc))        # 9:30 IST
    assert out["mornings"] == 1
    assert "naye return" in S.day(T)["say"]
    assert S.tick(datetime(2026, 10, 23, 4, 30, tzinfo=timezone.utc))["mornings"] == 0
    assert "WAPSI" in S.prompt_block(T)
