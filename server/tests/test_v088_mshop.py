"""v0.88 Mobile Dukaan Sahayak: repair jobs with photos, legal guards (IMEI, unlock proof, no passcodes), rule +
earlier-work checks, the bill waits for her Haan, ready draft with her UPI, warranty by IMEI / phone, recharges with
expiry reminders and commission, customer status on WhatsApp."""
import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx

T = "default"
IMEI = "490154203237518"            # valid Luhn
JPG = b"\xff\xd8\xff\xe0" + b"0" * 2000


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


def test_pure_helpers():
    from app.mshop.service import IMEI_CHANGE, _scrub, faults_of, imei_ok
    assert imei_ok(IMEI) and not imei_ok("490154203237519") and not imei_ok("12345")
    assert faults_of("display toota aur charging nahi ho rahi") == ["display", "charging_port"]
    assert faults_of("paani mein gir gaya") == ["water"] and faults_of("FRP lock hatana hai") == ["unlock"]
    assert faults_of("kuch ajeeb") == ["other"]
    assert _scrub("screen lock nahi khulta, password 4821 hai") == ("screen lock nahi khulta, password [hataya] hai", True)
    assert _scrub("pattern lock hai")[1] is False
    assert IMEI_CHANGE.search("imei change karna hai") and IMEI_CHANGE.search("IMEI repair") and not IMEI_CHANGE.search("display")


def test_guards_imei_unlock_duplicate(env):
    from app.mshop import service as M
    r = M.new_job(T, "Ravi", "9822000001", "Samsung", "A12", IMEI, "IMEI change karna hai", force=True)
    assert r["saved"] is False and "kanoonan" in r["say"]                      # never, even with force
    r = M.new_job(T, "Ravi", "9822000001", "Samsung", "A12", IMEI, "FRP lock hatana hai")
    assert r["saved"] is False and any("saboot" in p for p in r["check"]["problems"])
    r = M.new_job(T, "Ravi", "9822000001", "Samsung", "A12", IMEI, "FRP lock hatana hai", proof="bill dekha, naam match")
    assert r["saved"]
    r2 = M.new_job(T, "Ravi", "9822000001", "Samsung", "A12", IMEI, "speaker kharab", force=True)
    assert r2["saved"] is False and "pehle se job" in r2["say"]                # same IMEI already in the shop
    r3 = M.new_job(T, "Asha", "9822000002", "Vivo", "Y20", "490154203237519", "display toota, password 1234 hai")
    assert r3["saved"] and "[hataya]" in r3["job"]["problem"] and "password" in r3["say"].lower()
    assert any("KYM" in n for n in r3["check"]["notes"])                        # bad IMEI check digit


def test_full_repair_flow_bill_haan_ready_deliver_warranty(env, monkeypatch):
    from app.mshop import service as M
    conv = conv_ctx().conversation_id
    monkeypatch.setattr("app.employee.service.profile", lambda t: {"upi_id": "meghana@upi", "business_name": "Meghana Mobile"})
    M.save_settings(T, shop_name="Meghana Mobile", prices={"display": 1800}, warranty={"display": 30}, fix_days={"display": 1})
    r = M.new_job(T, "Ramesh Patil", "+91 98220 12345", "Xiaomi", "Redmi Note 12", IMEI, "display toota, touch nahi chalta",
                  accessories=["sim", "cover", "chocolate"], condition="back pe scratch", advance=500, conv=conv)
    assert r["saved"], r
    j = r["job"]
    assert j["number"] == "M-0001" and j["estimate"] == "₹1,800" and j["accessories"] == ["sim", "cover"]
    assert "photo" in r["say"].lower()
    # photos: from the app (kept in the shop's own store) and refused when not an image
    ph = M.add_photo(T, "1", JPG, "front.jpg", "in")
    assert ph["url"].startswith("/api/mshop/photos/")
    with pytest.raises(M.MShopError):
        M.add_photo(T, "1", b"not an image", "x.jpg")
    # part + labour, then ready: the bill waits for her Haan
    M.add_part(T, "M-0001", "Display combo", price=1500, cost=900)
    M.add_part(T, "M-0001", "", labour=300)
    out = M.set_status(T, "M-0001", "ready", conv=conv)
    assert out["bill"]["status"] == "pending" and out["bill"]["total"] == "₹1,800"
    assert _events("mshop_bill")[-1]["status"] == "pending"
    with pytest.raises(M.MShopError):
        M.ready_card(T, "M-0001")                                               # no amount to the customer before her Haan
    with pytest.raises(M.MShopError):
        M.deliver(T, "M-0001")
    d = M.decide_bill(T, "M-0001", True, conv=conv)
    card = d["ready"]
    assert card["amount"] == "₹1,800" and card["balance"] == "₹1,300" and "pa=meghana%40upi" in card["upi_link"]
    assert card["wa_link"].startswith("https://wa.me/919822012345?text=") and "Meghana Mobile" in card["text"]
    done = M.deliver(T, "M-0001", paid_now=1300, conv=conv)
    assert done["job"]["status"] == "delivered" and done["job"]["balance"] == "₹0"
    assert done["job"]["warranty_until"] == (M.today(T) + timedelta(days=30)).isoformat()
    assert "photo" in done["say"].lower()                                       # no delivery photo yet
    w = M.warranty(T, IMEI)
    assert w["found"][0]["under_warranty"] and "HAI" in w["say"]
    assert M.warranty(T, "9822012345")["found"]
    # the same phone back with the same fault: warranty claim pointed out, linked to the old job
    r = M.new_job(T, "Ramesh Patil", "9822012345", "Xiaomi", "Redmi Note 12", IMEI, "display mein lines aa rahi")
    assert r["saved"] and r["job"]["warranty_of"] == j["id"]
    assert any("warranty claim" in n for n in r["check"]["notes"])
    # earlier work feeds the next estimate (same model + fault)
    ck = M.check_job(T, "display toota", None, "Xiaomi", "Redmi Note 12")
    assert any("Isi model" in n and "₹1,800" in n for n in ck["notes"])
    assert M.slip_pdf(T, "M-0001")[:4] == b"%PDF"


def test_bill_changed_by_her_and_gst(env):
    from app.mshop import service as M
    M.save_settings(T, gstin="27ABCDE1234F1Z5", gst_on=True)
    M.new_job(T, "Neha", "9000000001", "Oppo", "A5", "", "battery jaldi khatam", estimate=1000)
    b = M.set_status(T, "1", "ready")["bill"]
    assert b["total"] == "₹1,180" and b["gst_paise"] == 18000
    M.decide_bill(T, "1", False)
    assert M.get_job(T, "1")["bill"]["status"] == "rejected"
    M.prepare_bill(T, "1")
    d = M.decide_bill(T, "1", True, total=900)
    assert d["job"]["total"] == "₹900"
    with pytest.raises(M.MShopError):
        M.save_settings(T, gstin="bad")


def test_recharges_expiry_reminders_commission(env):
    from app.mshop import service as M
    M.save_settings(T, commission={"jio": 3, "airtel": 2.5}, remind_days=2)
    r = M.add_recharge(T, "+91 98765 43210", 299, "Jio", 28, "Sunil", via="Jio POS Plus", day=(M.today(T) - timedelta(days=27)).isoformat())
    assert r["expires_on"] == (M.today(T) + timedelta(days=1)).isoformat()
    M.add_recharge(T, "9876500000", 199, "airtel", 28)
    M.add_recharge(T, "9876543210", 19, day="aaj")                            # top-up without validity: operator remembered
    due = M.due_recharges(T)
    assert [d["number"] for d in due] == ["9876543210"] and due[0]["wa_link"].startswith("https://wa.me/919876543210")
    assert "Sunil" in due[0]["text"]
    day = M.recharges_day(T)
    assert day["count"] == 2 and day["commission"] == "₹5.55"
    with pytest.raises(M.MShopError):
        M.add_recharge(T, "123", 10)
    with pytest.raises(M.MShopError):
        M.add_recharge(T, "9876543210", 10, "foo")
    M.mark_reminded(T, due[0]["id"])
    assert M.due_recharges(T)[0]["reminded"] is True


def test_day_morning_tools_role_inbox_api(env):
    from app import main
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    from app.employee.models import BizContact, EmployeeProfile
    from app.mshop import service as M
    assert roles.duty_of("mobile_shop") == "mobile_repair" and roles.kind_of("mobile_shop_dekho") == "read"
    assert roles.PRESETS["mobile_shop"]["role"] == "mobile_shop"
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    out = run("mobile_shop", action="new_job", name="Kiran", phone="9890011111", brand="Realme", model="C55",
              problem="charging port loose", promised_on="kal")
    assert out["saved"]
    with session() as s:
        from app.mshop.service import RepairJob
        s.scalars(select(RepairJob)).first().promised_on = (M.today(T) - timedelta(days=1)).isoformat()
    d = run("mobile_shop_dekho", what="today")
    assert d["late"] and "Der ho gayi" in d["text"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["mobile_shop"](staff, action="decide_bill", job="1", approve=True))
    # customer on WhatsApp sees only their own jobs
    with session() as s:
        s.add(EmployeeProfile(tenant_id=T, enabled=True, role="mobile_shop"))
        c = BizContact(tenant_id=T, wa_id="919890011111", name="Kiran")
        s.add(c)
        s.flush()
        cid = c.id
    got = asyncio.run(HANDLERS["biz_repair_status"](Ctx(T, ctx.conversation_id, actor=f"customer:{cid}")))
    assert len(got["jobs"]) == 1 and got["jobs"][0]["device"] == "Realme C55"
    with TestClient(main.app) as cl:
        assert "mobile_shop" in cl.get("/healthz").json()["features"]
        jid = cl.get("/api/mshop/jobs").json()["jobs"][0]["id"]
        up = cl.post(f"/api/mshop/jobs/{jid}/photos", files={"file": ("a.jpg", JPG, "image/jpeg")}, data={"kind": "in"})
        assert up.status_code == 200, up.text
        assert cl.get(up.json()["url"]).content == JPG
        assert cl.post(f"/api/mshop/jobs/{jid}/part", json={"name": "Charging port", "price": 400}).status_code == 200
        b = cl.post(f"/api/mshop/jobs/{jid}/status", json={"status": "ready"}).json()["bill"]
        assert b["total"] == "₹400"
        r = cl.post(f"/api/mshop/jobs/{jid}/decide", json={"approve": True}).json()
        assert r["ready"]["amount"] == "₹400"
        assert cl.post(f"/api/mshop/jobs/{jid}/deliver", json={"amount": 400}).json()["job"]["status"] == "delivered"
        assert cl.get(f"/api/mshop/jobs/{jid}/slip.pdf").content[:4] == b"%PDF"
        assert cl.post("/api/mshop/recharges", json={"number": "9890011111", "amount": 349, "operator": "airtel",
                                                     "validity_days": 28}).status_code == 200
        assert cl.get("/api/mshop/recharges").json()["day"]["count"] == 1
        assert cl.get("/api/mshop/warranty", params={"q": "9890011111"}).json()["found"]
        assert cl.post("/api/mshop/jobs/nope/status", json={"status": "ready"}).status_code == 400
        cl.put("/api/mshop/settings", json={"morning_time": "00:00", "shop_name": "Test Mobile"})
    assert M.settings(T)["shop_name"] == "Test Mobile"
