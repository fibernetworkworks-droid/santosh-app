"""Wave-2 (P1) packs through Santosh's Bazar service: new billers, business PDFs (owner-only download), udhar,
attendance + salary slips, rent receipts, EMI, scam check, SOS, bank SMS readers, handoffs and P1 shop templates."""
import calendar
from pathlib import Path

import pytest

from tests.test_bazar import _events, bz  # noqa: F401  (fixture)


def make_gstin(prefix14: str) -> str:
    from app.bazar.connectors.native2 import CHARS
    total = 0
    for i, ch in enumerate(prefix14):
        prod = CHARS.index(ch) * (2 if i % 2 else 1)
        total += prod // 36 + prod % 36
    return prefix14 + CHARS[(36 - total % 36) % 36]


def test_water_bill_and_fastag_demo(bz):
    svc, conv = bz["svc"], bz["conv"]
    bill = svc.run("default", conv, "akola-municipal-corp", "fetch_bill", {"consumer_or_property_id": "AMC-77812"})
    assert bill["demo"] is True and bill["amount_paise"] > 0
    pay = svc.run("default", conv, "akola-municipal-corp", "pay_bill", {"bill_ref": bill["bill_ref"]})
    assert pay["needs_approval"] and pay["card"]["payee"] == "Akola Municipal Corp"
    tag = svc.run("default", conv, "sbi-fastag", "fetch_bill", {"vehicle_number": "MH30AB1234"})
    pay = svc.run("default", conv, "sbi-fastag", "pay_bill", {"bill_ref": tag["bill_ref"]})
    assert pay["card"]["payee"] == "SBI FASTag" and pay["card"]["title"].startswith("[DEMO]")
    assert svc.find("default", "akola municipal corp pani bill")["packs"][0]["pack_id"] == "akola-municipal-corp"


def test_gstin_validation(bz):
    from app.bazar.connectors.base import ToolError
    from app.bazar.connectors.native2 import gstin_valid
    good = make_gstin("27AAPFN1234A1Z")
    assert gstin_valid(good) and gstin_valid(good.lower())
    assert not gstin_valid(good[:-1] + ("0" if good[-1] != "0" else "1"))
    assert not gstin_valid("99AAPFN1234A1Z5")  # no such state code
    with pytest.raises(ToolError, match="GSTIN"):
        bz["svc"].run("default", bz["conv"], "gst-invoice-maker", "set_business", {"name": "X", "gstin": good[:-1] + "#"})


def test_gst_invoice_pdf_owner_only(bz, monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("EMAIL_ADDRESS", "owner@gmail.com")
    from app.config import get_settings
    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app import accounts, main
    from app.db import Conversation, User, session
    svc = bz["svc"]
    with session() as s:
        s.add_all([User(id="usr_owner", email="owner@gmail.com"), User(id="usr_kunal", email="kunal@gmail.com")])
        conv = Conversation(tenant_id="usr_kunal")
        s.add(conv)
        s.flush()
        conv = conv.id
    seller = make_gstin("27AAPFN1234A1Z")
    svc.run("usr_kunal", conv, "gst-invoice-maker", "set_business",
            {"name": "Newtika Demo Traders", "gstin": seller, "address": "Akola", "upi_id": "newtika.demo@okaxis"})
    inv = svc.run("usr_kunal", conv, "gst-invoice-maker", "create_invoice", {"customer_name": "Sai Agencies", "items": [
        {"name": "Fiber patch cord", "qty": 2, "rate": 1000, "gst_rate": 18, "hsn": "8544"}]})
    assert inv["total"] == "₹2,360" and inv["tax_split"] == "CGST + SGST" and inv["number"].startswith("INV/")
    assert inv["download"] == f"/api/bazar/files/{inv['doc_id']}" and "download card" in inv["phone"]
    assert "am=2360.00" in inv["payment_link"]
    inv2 = svc.run("usr_kunal", conv, "gst-invoice-maker", "create_invoice", {"customer_name": "Blr Co", "customer_state": "Karnataka",
                                                                             "items": [{"name": "ONT", "qty": 1, "rate": 2500, "gst_rate": 18}]})
    assert inv2["tax_split"] == "IGST" and inv2["number"].endswith("0002")
    card = _events(conv, "pc_file")[0]
    assert card["source"] == "bazar" and card["doc_id"] == inv["doc_id"] and card["name"].endswith(".pdf") and card["size"] > 500

    c = TestClient(main.app)
    kunal = {"Authorization": f"Bearer {accounts.issue_session('usr_kunal')}"}
    owner = {"Authorization": f"Bearer {accounts.issue_session('usr_owner')}"}
    r = c.get(f"/api/bazar/files/{inv['doc_id']}", headers=kunal)
    assert r.status_code == 200 and r.content[:4] == b"%PDF" and r.headers["content-type"] == "application/pdf"
    assert c.get(f"/api/bazar/files/{inv['doc_id']}", headers=owner).status_code == 404   # someone else's file
    assert c.get(f"/api/bazar/files/{inv['doc_id']}/link", headers=owner).status_code == 404
    assert len(c.get("/api/bazar/files", headers=kunal).json()["files"]) == 2
    assert c.get("/api/bazar/files", headers=owner).json()["files"] == []
    # the chat card's signed link works without a header; a tampered one does not
    assert c.get(card["url"]).content[:4] == b"%PDF"
    fresh = c.get(f"/api/bazar/files/{inv['doc_id']}/link", headers=kunal).json()["url"]
    assert c.get(fresh).status_code == 200
    assert c.get(card["url"].replace("sig=", "sig=0")).status_code == 403
    assert c.get(card["url"].replace(inv["doc_id"], inv2["doc_id"])).status_code == 403


def test_quotation(bz):
    q = bz["svc"].run("default", bz["conv"], "quotation-maker", "create_quotation", {"customer_name": "Patil Sir", "valid_days": 10, "items": [
        {"name": "FTTH installation", "qty": 1, "rate": 1500}, {"name": "Router", "qty": 1, "rate": 2000, "gst_rate": 18}]})
    assert q["total"] == "₹3,860" and q["number"].startswith("QT/") and q["doc_id"]
    assert _events(bz["conv"], "pc_file")[-1]["kind"] == "quotation"


def test_udhar_ledger_and_reminders_need_tap(bz):
    svc, conv = bz["svc"], bz["conv"]
    assert svc.run("default", conv, "udhar-credit-reminder", "add_udhar", {"customer": "Ramesh", "amount_rupees": 500})["total_due"] == "₹500"
    assert svc.run("default", conv, "udhar-credit-reminder", "settle_udhar", {"customer": "ramesh", "amount_rupees": 200})["still_due"] == "₹300"
    svc.run("default", conv, "udhar-credit-reminder", "add_udhar", {"customer": "Sunil", "amount_rupees": 150, "phone": "919800000009"})
    assert svc.run("default", conv, "udhar-credit-reminder", "list_udhar", {})["total_outstanding"] == "₹450"
    r = svc.run("default", conv, "udhar-credit-reminder", "send_udhar_reminders", {})
    assert r["needs_approval"] and r["card"]["title"] == "Send udhar reminders to 1 customers"
    res = svc.decide("default", r["approval_id"], "approve")
    assert res["open"]["kind"] == "links" and res["open"]["links"][0]["url"].startswith("https://wa.me/919800000009?text=")


def test_attendance_and_salary_slips(bz):
    svc, conv = bz["svc"], bz["conv"]
    from app.bazar.connectors.timeparse import ist_now
    svc.run("default", conv, "staff-attendance", "add_staff", {"name": "Raju", "monthly_salary_rupees": 12000, "paid_leaves": 1})
    svc.run("default", conv, "staff-attendance", "add_staff", {"name": "Sita", "monthly_salary_rupees": 9000})
    m = svc.run("default", conv, "staff-attendance", "mark_attendance", {"present": ["raju"], "absent": ["Sita", "Raju"], "half_day": []})
    assert m["marked"] == {"Raju": "absent", "Sita": "absent"}
    month = ist_now().strftime("%Y-%m")
    rep = svc.run("default", conv, "staff-attendance", "attendance_report", {"month": month})
    assert {s["name"]: s["absent"] for s in rep["staff"]} == {"Raju": 1, "Sita": 1}
    out = svc.run("default", conv, "salary-slip-generator", "salary_slips", {"month": month})
    nets = {s["staff"]: s["net_pay"] for s in out["slips"]}
    days = calendar.monthrange(*map(int, month.split("-")))[1]
    assert nets["Raju"] == "₹12,000"   # 1 paid leave covers the absence
    assert nets["Sita"] == f"₹{round(9000 * (days - 1) / days):,}"
    cards = [c for c in _events(conv, "pc_file") if c["kind"] == "salary_slip"]
    assert len(cards) == 2
    from app.bazar.db import GeneratedDoc
    from app.db import session
    with session() as s:
        docs = s.query(GeneratedDoc).filter_by(user_id="default", kind="salary_slip").all()
        assert len(docs) == 2 and all(Path(d.file_name).read_bytes()[:4] == b"%PDF" for d in docs)


def test_rent_receipts(bz):
    out = bz["svc"].run("default", bz["conv"], "rent-receipt-generator", "rent_receipts", {
        "landlord_name": "S. Patil", "property_address": "Akola", "monthly_rent_rupees": 10000, "from_month": "2026-04", "to_month": "2027-03"})
    assert len(out["receipts"]) == 12 and "PAN" in out["note"]
    assert len([c for c in _events(bz["conv"], "pc_file") if c["kind"] == "rent_receipt"]) == 12


def test_emi(bz):
    r = bz["svc"].run("default", bz["conv"], "loan-emi-calculator-and-tracker", "emi_calc",
                      {"principal_rupees": 1000000, "annual_rate_percent": 9, "months": 240})
    assert r["emi"].startswith("₹8,997") and r["months"] == 240


def test_scam_check(bz):
    r = bz["svc"].run("default", bz["conv"], "scam-message-checker", "check_message", {
        "text": "Dear customer your electricity will be disconnected tonight. Update KYC at bit.ly/xyz and share OTP"})
    assert r["verdict"] == "very likely a scam" and any("1930" in d for d in r["do"])
    ok = bz["svc"].run("default", bz["conv"], "scam-message-checker", "check_message", {"text": "Meeting at 5, see you"})
    assert ok["verdict"] == "no common scam signs found"


def test_sos_shows_numbers_and_whatsapp_links(bz):
    svc, conv = bz["svc"], bz["conv"]
    svc.add_contact("default", "Anil", phone="9800000011", relation="family")
    r = svc.run("default", conv, "emergency-sos", "sos", {"message": "Accident near bus stand", "lat": 20.7, "lng": 77.0})
    assert r["alerted"] == [] and "Call 112" in r["message"]
    assert {c["number"] for c in r["call_now"]} >= {"112", "108"}
    urls = [l["url"] for l in r["share_links"]]
    assert urls[:2] == ["tel:112", "tel:108"]
    assert any(u.startswith("https://wa.me/919800000011?text=") and "maps.google.com" in u for u in urls)
    assert urls[-1].startswith("https://wa.me/?text=")   # pick any contact in the user's own WhatsApp
    ev = _events(conv, "bazar_open")[-1]
    assert ev["kind"] == "links" and ev["label"].startswith("SOS")


def test_reader_ignores_otps_and_summarises(bz):
    svc, conv = bz["svc"], bz["conv"]
    out = svc.run("default", conv, "hdfc-bank", "import_messages", {"messages": [
        "Rs.1,240.00 debited from A/c XX1234 on 12-10-26 to VPA zomato@icici. Avl Bal Rs 18,500.00 -HDFC Bank. Never share OTP",
        "INR 45,000.00 credited to A/c XX1234 on 01-10-26 by NEFT-SALARY. -HDFC Bank",
        "Your OTP for login is 554433. Do not share it with anyone.",
    ]})
    assert out["transactions"] == 2 and out["skipped"] == 1 and out["last_balance"] == "₹18,500"
    from app.bazar.db import SpendEntry
    from app.db import session
    with session() as s:
        raws = [e.raw for e in s.query(SpendEntry).filter_by(user_id="default").all()]
    assert len(raws) == 2 and not any("554433" in r for r in raws)
    summ = svc.run("default", conv, "hdfc-bank", "summary", {"month": "2026-10"})
    assert summ["money_out"] == "₹1,240" and summ["money_in"] == "₹45,000" and summ["last_balance"] == "₹18,500"
    card = svc.run("default", conv, "icici-bank", "import_messages", {"messages": [
        "ICICI Bank Credit Card XX9012: Total amount due Rs 7,450.00, minimum Rs 380. Due date 05-11-2026."]})
    assert card["card_dues"][0]["amount"] == "₹7,450"
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError):   # readers have no money tools
        svc.run("default", conv, "hdfc-bank", "pay_bill", {})
    svc.run("default", conv, "hdfc-bank", "open_app", {"purpose": "check balance"})
    ev = _events(conv, "bazar_open")[-1]
    assert ev["kind"] == "app" and ev["url"].startswith("https://play.google.com/store/search")


def test_handoff_prepare_opens_official_site(bz):
    svc, conv = bz["svc"], bz["conv"]
    r = svc.run("default", conv, "passport-seva", "prepare", {"goal": "Apply for a fresh passport", "details": {"city": "Akola"}})
    assert r["open"]["web_verified"] and "Open button" in r["phone"]
    ev = _events(conv, "bazar_open")[-1]
    assert ev["kind"] == "links" and ev["links"][0]["url"] == "https://www.passportindia.gov.in"
    assert ev["links"][1]["url"].startswith("https://play.google.com/store/search")
    # an unverified website is never opened directly: Play Store search only
    from app.bazar.packs.registry import registry
    pid = next(p.id for p in registry().by_executor("handoff") if not p.config.get("web_verified"))
    svc.run("default", conv, pid, "prepare", {"goal": "book"})
    ev = _events(conv, "bazar_open")[-1]
    assert ev["kind"] == "app" and ev["url"].startswith("https://play.google.com/")


def test_p1_shop_template_no_shop_yet(bz):
    svc = bz["svc"]
    hit = next(p for p in svc.find("default", "tailor blouse stitching")["packs"] if p["pack_id"] == "tailor")
    assert hit["status"] == "no_shop_yet" and "tools" not in hit
    svc.create_shop("default", {"template_id": "tailor", "name": "Lakshmi Tailors", "owner_phone": "9800000020",
                                "upi_id": "lakshmi.tailor@okaxis", "aliases": ["lakshmi tailor"], "slots": ["Tomorrow 11 am"]})
    hit = next(p for p in svc.find("default", "tailor blouse stitching")["packs"] if p["pack_id"] == "tailor")
    assert hit["status"] == "ready"


def test_recipe_maps_to_core_lists_and_meal_plan_uses_them(bz):
    svc, conv = bz["svc"], bz["conv"]
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="list_add"):
        svc.run("default", conv, "recipe-to-cart", "ingredients_to_list", {"ingredients": ["besan"]})
    svc.run("default", conv, "meal-planner", "save_meal_plan", {"plan": {"Mon": "poha"}, "groceries": ["Poha", "poha", "Peanuts"]})
    from app.db import ListItem, session
    with session() as s:
        assert sorted(i.text for i in s.query(ListItem).filter_by(tenant_id="default", list_name="shopping")) == ["Peanuts", "Poha"]
