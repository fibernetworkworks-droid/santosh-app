"""Rentdesk Sahayak (property manager): rules, units / tenants (IDs in the locker), tenancies with checks, ledger + receipts + Galla
hint + BizDue mirror, reminder DRAFTS that only her tap sends, rent change / notice / repair / deposit-deduction cards that only her
tap decides (fingerprint for money), inspections with EXIF-free photos, deposit settlement, agreement draft, DPDP forget, tools
(owner / staff / customer actors), business-WhatsApp tenant tools, worker tick and API."""
import asyncio
import io
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.rentdesk.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def rd(env, monkeypatch):
    from app.rentdesk import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def _setup(S, start=None, rent=20000, deposit=60000, **kw):
    S.save_settings(T, landlord_name="Meghana Ingle", landlord_address="Akot, Akola", state="MH", city="Pune", upi_id="meghana@upi",
                    remind_before=3, grace_days=5, morning_time="00:00")
    u = S.save_unit(T, label="Flat 302", building="Sai Residency", kind="flat", address="Baner", pin="411045",
                    inventory=["2 fan", "1 geyser"])["unit"]
    p = S.save_person(T, name="Ramesh Patil", phone="98220 12345", aadhaar="2345 6789 0124", kind="individual")["person"]
    st = start or (S.today(T) - timedelta(days=40))
    kw.setdefault("months", 11)
    t = S.new_tenancy(T, u["number"], p["number"], start=st.isoformat(), rent=rent, deposit=deposit, **kw)["tenancy"]
    return u, p, t


def test_rules():
    from app.rentdesk import rules as R
    assert R.money("20k") == 20000 and R.money("1.5 lakh") == 150000 and R.money("₹ 12,500") == 12500
    assert R.phone10("+91 98220 12345") == "9822012345" and R.phone10("12345") == ""
    assert R.end_of(date(2026, 1, 31), 11) == date(2026, 12, 30)
    assert R.periods(date(2026, 1, 10), date(2026, 12, 9), date(2026, 3, 15)) == [date(2026, 1, 10), date(2026, 2, 10), date(2026, 3, 10)]
    assert R.due_date(date(2026, 2, 20), 5, date(2026, 1, 20)) == date(2026, 3, 5)
    assert R.fy_of(date(2026, 10, 1)) == "2627" and R.fy_of(date(2027, 2, 1)) == "2627"
    assert R.repair_category("Bathroom ka nal tapak raha hai") == ("plumber", False)
    assert R.repair_category("kitchen mein gas leak ki smell")[1] is True
    sc = R.scrub("OTP hai 123456 aur card 4111 1111 1111 1111, aadhaar 2345 6789 0124, PAN ABCDE1234F")
    assert "123456" not in sc and "4111" not in sc and "2345 6789" not in sc and "ABCDE1234F" not in sc
    assert R.deposit_check("AS", "residential", 10000, 50000) and not R.deposit_check("MH", "residential", 10000, 50000)
    assert "2%" in R.tds_note("individual", 60000, "residential") and "10%" in R.tds_note("company", 60000, "commercial")
    assert "TDS nahi" in R.tds_note("individual", 30000, "residential")
    assert "RCM" in R.gst_note("shop", "commercial", True, False, "") and "RCM" not in R.gst_note("shop", "commercial", True, True, "")
    assert "forward charge" in R.gst_note("shop", "commercial", True, False, "27ABCDE1234F1Z5")
    assert "GST nahi" in R.gst_note("flat", "residential", False, False, "")
    assert "maaf" in R.gst_note("pg_bed", "residential", False, False, "", 15000)
    assert R.receipt_notes(150000, "cash", 12000, False) and len(R.receipt_notes(150000, "cash", 12000, False)) == 2
    ids = [i["id"] for i in R.checklist("MH", "leave_licence", 11, "residential")]
    assert "registration" in ids and "police" in ids and "rent_authority" not in ids
    assert "rent_authority" in [i["id"] for i in R.checklist("AS", "mta", 11, "residential")]
    worse = R.compare_inspections([{"room": "Hall", "item": "Pankhe", "condition": "good"}],
                                  [{"room": "Hall", "item": "Pankhe", "condition": "damaged"}, {"room": "Hall", "item": "Tiles", "condition": "good"}])
    assert len(worse) == 1 and worse[0]["now"] == "damaged"
    txt = R.notice_text("vacate", {"tenant": "Ramesh"})
    assert "[vacate_on]" in txt and "lawyer" in txt


def test_units_people_tenancy_and_ledger(rd, monkeypatch):
    S = rd
    u, p, t = _setup(S)
    assert u["number"] == "U-001" and u["inventory"][0] == {"item": "fan", "qty": 2}
    assert p["ids"]["aadhaar"].endswith("0124") and "2345 6789" not in str(p) and "234567890124" not in str(p)   # only masked kept
    from app import idvault
    assert any(x["kind"] == "aadhaar" and x["person"].startswith("kirayedar") for x in idvault.list_(T))
    with pytest.raises(S.RentError):
        S.save_person(T, name="X", phone="123")
    assert t["status"] == "draft" and t["kind"] == "leave_licence" and t["end"]
    assert any("s.55" in n for n in S.tenancy_view(T, t["number"])["notes"])
    # second draft for the same unit can't be activated while the first runs
    a = S.activate(T, t["number"])
    assert a["tenancy"]["status"] == "active"
    charges = a["tenancy"]["charges"]
    assert any(c["kind"] == "deposit" and c["amount"] == 60000 for c in charges)
    assert len([c for c in charges if c["kind"] == "rent"]) >= 2               # started 40 days ago
    p2 = S.save_person(T, name="Suresh", phone="9876543210")["person"]
    t2 = S.new_tenancy(T, "U-001", p2["number"], start=S.today(T).isoformat(), rent=18000)["tenancy"]
    with pytest.raises(S.RentError):
        S.activate(T, t2["number"])
    with pytest.raises(S.RentError):
        S.update_tenancy(T, t["number"], rent=25000)                          # money of a live tenancy only via a card
    # BizDue mirror
    from app.employee import inbox
    assert any(d["phone"] == "919822012345" for d in inbox.dues(T))
    # payment: oldest first (deposit, then rent), receipt numbered, Galla hint
    from app.galla import service as G
    G.add_cash(T, 80000, day=S.today(T).isoformat(), source="manual")
    with S.session() as s:
        from app.galla.service import GallaEntry
        g = s.query(GallaEntry).first()
        g.source, g.payer = "upi_alert", "RAMESH"
    out = S.receive(T, t["number"], 80000, mode="upi", ref="UTR998877")
    pay = out["payment"]
    assert pay["receipt_no"].startswith("R/") and pay["receipt_no"].endswith("0001")
    assert pay["alloc"][0]["kind"] == "deposit" and pay["alloc"][1]["kind"] == "rent"
    assert "Galla" in pay["hint"] and "ishaara" in pay["hint"]
    assert out["message"]["status"] == "draft" and "rentdesk_receipt" in kinds(S)
    with pytest.raises(S.RentError):
        S.receive(T, t["number"], 100, actor="staff:x")                       # only she says money came
    pdf = S.receipt_pdf(T, pay["id"])
    assert pdf[:4] == b"%PDF"
    link = S.pay_link(T, t["number"])
    assert link["url"].startswith("upi://pay?pa=meghana%40upi") or link["say"]
    st = S.statement(T, t["number"])
    assert st["deposit_held"] == 60000 and st["paid"] == 80000
    S.add_charge(T, t["number"], "electricity", 1450, note="MSEDCL Sep")
    with pytest.raises(S.RentError):
        S.add_charge(T, t["number"], "electricity", 100, actor="staff:x")
    v = S.void_payment(T, pay["id"])
    assert "radd" in v["say"] and S.statement(T, t["number"])["deposit_held"] == 0


def test_messages_only_on_her_tap(rd, monkeypatch):
    S = rd
    u, p, t = _setup(S, start=S.today(T) + timedelta(days=2))
    S.activate(T, t["number"])
    S.EVENTS.clear()
    r = S.tick(datetime.now(timezone.utc))
    assert r["reminders"] >= 1 and "rentdesk_message" in kinds(S)            # deposit is not reminded; rent due in 2 days is
    m = [x for x in S.messages(T) if x["kind"] == "reminder"][0]
    assert "Flat 302" in m["text"] and "meghana@upi" in m["text"] and m["wa"].startswith("https://wa.me/919822012345")
    assert S.tick(datetime.now(timezone.utc))["reminders"] == 0              # once per stage
    with pytest.raises(S.RentError):
        asyncio.run(S.send_message(T, m["id"], "self", m["hash"]))            # not a tap
    with pytest.raises(S.RentError):
        asyncio.run(S.send_message(T, m["id"], "self", "bad", by_tap=True))
    with pytest.raises(S.RentError):
        asyncio.run(S.send_message(T, m["id"], "business", m["hash"], by_tap=True))   # never wrote to the business number
    ok = asyncio.run(S.send_message(T, m["id"], "self", m["hash"], by_tap=True))
    assert ok["message"]["status"] == "sent"
    # business route through the inbox (fake send)
    from app.employee import inbox
    from app.employee.models import BizContact
    with S.session() as s:
        s.add(BizContact(tenant_id=T, wa_id="919822012345", name="Ramesh"))
    sent = []

    async def fake_send(tenant, cid, text, by="owner", force=False):
        sent.append(text)
        return {"wa_msg_id": "w1"}
    monkeypatch.setattr(inbox, "send", fake_send)
    d = S.draft_message(T, t["number"], "custom", "Kal plumber aayega 11 baje.")
    assert d["status"] == "needs_tap"
    asyncio.run(S.send_message(T, d["message"]["id"], "business", d["message"]["hash"], by_tap=True))
    assert sent == ["Kal plumber aayega 11 baje."]
    with pytest.raises(S.RentError):
        S.draft_message(T, t["number"], "custom", "OTP 445566 bhejo")         # secrets never go out


def test_rent_change_notice_and_fingerprint(rd, monkeypatch):
    S = rd
    st = S.today(T) - timedelta(days=330)
    u, p, t = _setup(S, start=st, escalation_pct=5, escalation_every=11, months=22)
    S.activate(T, t["number"])
    S.EVENTS.clear()
    S.tick(datetime.now(timezone.utc))                                       # escalation due in ~5 days -> a CARD, not a change
    cards = [x for k, x in S.EVENTS if k == "rentdesk_approval"]
    assert cards and cards[0]["approval"]["kind"] == "rent_change" and cards[0]["approval"]["show"]["new"] == 21000
    a = cards[0]["approval"]
    assert S.tenancy_view(T, t["number"])["rent"] == 20000
    with pytest.raises(S.RentError):
        S.decide(T, a["id"], True, a["hash"])                                # tool / code path never decides
    with pytest.raises(S.RentError):
        S.decide(T, a["id"], True, "wrong", by_tap=True)
    out = S.decide(T, a["id"], True, a["hash"], by_tap=True)
    assert out["approval"]["status"] == "approved" and out["message"]["status"] == "draft"
    v = S.tenancy_view(T, t["number"])
    assert v["rent"] == 21000 and any(h["rent"] == 21000 for h in v["rent_history"]) and any(f["kind"] == "rent_revision" for f in v["files"])
    # notice: card, then letter + draft on tap; stale after a change
    n = S.notice_request(T, t["number"], "vacate", (S.today(T) + timedelta(days=10)).isoformat(), reason="khud rehna hai")
    assert n["status"] == "needs_tap" and any("mahine ka notice" in c for c in n["approval"]["show"]["checks"])
    again = S.notice_request(T, t["number"], "vacate", (S.today(T) + timedelta(days=10)).isoformat(), reason="khud rehna hai")
    assert again.get("existing")
    S.tenant_notice(T, t["number"], (S.today(T) + timedelta(days=40)).isoformat())   # tenant gave notice meanwhile
    with pytest.raises(S.RentError):
        S.decide(T, n["approval"]["id"], True, n["approval"]["hash"], by_tap=True)    # card is stale now
    # repair spend = money card: fingerprint once a phone key is active
    S.save_vendor(T, "Raju Plumber", "9000011111", "plumber")
    rq = S.request_new(T, "U-001", "Bathroom ka nal leak")["request"]
    assert rq["category"] == "plumber"
    card = S.request_assign(T, rq["id"], "Raju Plumber", 1800)
    assert card["status"] == "needs_tap" and card["request"]["status"] == "waiting_haan"
    with pytest.raises(S.RentError):
        S.request_done(T, rq["id"], actor="staff:x")
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    with pytest.raises(S.RentError) as e:
        S.decide(T, card["approval"]["id"], True, card["approval"]["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.challenge(T, card["approval"]["id"])
    assert ch["message"].startswith("hoola-approve|v1|default|rentdesk|")
    monkeypatch.setattr(ak, "active_on", lambda tenant: False)
    ok = S.decide(T, card["approval"]["id"], True, card["approval"]["hash"], by_tap=True)
    assert "1,800" in ok["say"]
    assert S.request_done(T, rq["id"], paid=1800)["request"]["status"] == "done"


def test_inspection_photos_settlement_forget(rd, monkeypatch):
    from PIL import Image
    S = rd
    u, p, t = _setup(S)
    S.activate(T, t["number"])
    S.receive(T, t["number"], 60000, mode="bank")                             # deposit paid; rent still due
    mi = S.inspection_start(T, t["number"], "move_in")["inspection"]
    key = mi["items"][2]["key"]                                              # Hall pankhe
    S.inspection_update(T, mi["id"], items=[{"key": key, "condition": "good"}], meters={"electricity": 1200}, keys=2, close=True)
    # photo with GPS EXIF -> stored without it
    im = Image.new("RGB", (64, 48), "red")
    ex = Image.Exif()
    ex[0x010F] = "SecretPhoneMaker"
    ex[0x0110] = "ModelXYZ"
    bio = io.BytesIO()
    im.save(bio, "JPEG", exif=ex)
    ph = S.add_photo(T, "inspection", mi["id"], bio.getvalue(), key)["photo"]
    raw = S.photo_bytes(T, ph["id"])
    assert b"SecretPhoneMaker" not in raw and b"ModelXYZ" not in raw and not dict(Image.open(io.BytesIO(raw)).getexif())
    mo = S.inspection_start(T, t["number"], "move_out")["inspection"]
    S.inspection_update(T, mo["id"], items=[{"key": key, "condition": "toota", "note": "blade tooti"}], close=True)
    cmp = S.inspection_compare(T, t["number"])
    assert cmp["worse"] and cmp["worse"][0]["now"] == "damaged"
    se = S.settlement_start(T, t["number"])["settlement"]
    assert se["held"] == 60000 and se["dues"] > 0 and se["suggest"]
    with pytest.raises(S.RentError):
        S.settlement_line(T, se["id"], "Pankha", 0)                           # amount only from her
    S.settlement_line(T, se["id"], "Pankha blade", 1200, "move-in good, ab toota", [ph["id"]])
    card = S.settlement_request(T, se["id"])
    a = card["approval"]
    assert a["kind"] == "deduction" and a["money"] and a["show"]["deductions"] == 1200
    with pytest.raises(S.RentError):
        S.refund_paid(T, se["id"])                                            # not approved yet
    S.settlement_line(T, se["id"], "Safai", 500, "kitchen")                   # changed after the card -> stale
    with pytest.raises(S.RentError):
        S.decide(T, a["id"], True, a["hash"], by_tap=True)
    a = S.settlement_request(T, se["id"])["approval"]
    out = S.decide(T, a["id"], True, a["hash"], by_tap=True)
    sv = out["settlement"]
    assert sv["status"] == "approved" and sv["deductions"] == 1700 and sv["refund"] == round(60000 - sv["dues"] - 1700, 2)
    assert out["message"]["kind"] == "refund"
    assert S.settlement_pdf(T, se["id"])[:4] == b"%PDF"
    with pytest.raises(S.RentError):
        S.forget(T, p["number"])                                              # deposit not settled yet
    done = S.refund_paid(T, se["id"], ref="UTR12345")
    assert done["settlement"]["status"] == "paid" and S.tenancy_view(T, t["number"])["status"] == "ended"
    assert S.units(T)[0]["status"] == "vacant"
    f = S.forget(T, p["number"])
    assert "mita di" in f["say"]
    from app import idvault
    assert not any(x["person"].startswith("kirayedar") for x in idvault.list_(T))
    assert S.people(T) == [] and S.statement(T, t["number"])["paid"] > 0       # amounts kept


def test_agreement_tools_biz_and_api(rd, monkeypatch):
    S = rd
    u, p, t = _setup(S)
    ag = S.agreement_file(T, t["number"])
    assert ag["file"]["file_id"] and "stamp duty" in " ".join(ag["blanks"])      # her number, not invented
    text, blanks = S.agreement_text(T, t["number"])
    assert "DRAFT" in text and "s.55" in text and "Rs 20000" in text.replace(",", "").replace(".0", "")
    from app.agent import rentdesk_tools as RT
    from app.agent.tools import Ctx, ToolError
    ctx = conv_ctx()
    assert asyncio.run(RT.rentdesk(ctx, "activate", tenancy=t["number"]))["tenancy"]["status"] == "active"
    staff = Ctx(T, ctx.conversation_id, actor="staff:abc")
    with pytest.raises(ToolError):
        asyncio.run(RT.rentdesk(staff, "received", tenancy=t["number"], amount=100))
    with pytest.raises(ToolError):
        asyncio.run(RT.rentdesk(Ctx(T, ctx.conversation_id, actor="customer:x"), "repair", unit="U-001", text="nal"))
    r = asyncio.run(RT.rentdesk(staff, "repair", unit="U-001", text="Switch board mein chingari"))
    assert r["request"]["urgent"] and r["request"]["category"] == "electrician"
    rc = asyncio.run(RT.rentdesk(staff, "rent_change", tenancy=t["number"], new_rent=23000, **{"from": (S.today(T) + timedelta(days=100)).isoformat()}))
    assert rc["status"] == "needs_tap"
    d = asyncio.run(RT.rentdesk_dekho(ctx, "day"))
    assert d["waiting"] >= 1 and "card" in d["say"]
    assert asyncio.run(RT.rentdesk_dekho(ctx, "rules"))["sources"]
    names = {x["name"] for x in RT.RENTDESK_TOOLS}
    assert names == set(RT.RENTDESK_HANDLERS) == set(RT.RENTDESK_LABELS)
    assert {x["name"] for x in RT.RENTDESK_BIZ_TOOLS} == set(RT.RENTDESK_BIZ_HANDLERS) == set(RT.RENTDESK_BIZ_LABELS)
    # tenant on her business WhatsApp: only their own account
    from app.employee.models import BizContact
    with S.session() as s:
        c1 = BizContact(tenant_id=T, wa_id="919822012345", name="Ramesh")
        c2 = BizContact(tenant_id=T, wa_id="919999999999", name="Stranger")
        s.add_all([c1, c2])
        s.flush()
        id1, id2 = c1.id, c2.id
    mine = asyncio.run(RT.biz_rent_status(Ctx(T, ctx.conversation_id, actor=f"customer:{id1}")))
    assert mine["tenancies"] and mine["tenancies"][0]["unit"] == "Flat 302" and mine["pay_link"].startswith("upi://")
    assert asyncio.run(RT.biz_rent_status(Ctx(T, ctx.conversation_id, actor=f"customer:{id2}")))["tenancies"] == []
    rep = asyncio.run(RT.biz_rent_repair(Ctx(T, ctx.conversation_id, actor=f"customer:{id1}"), text="Geyser band hai"))
    assert rep["number"].startswith("M-")
    with pytest.raises(ToolError):
        asyncio.run(RT.biz_rent_repair(Ctx(T, ctx.conversation_id, actor=f"customer:{id2}"), text="x"))
    # API
    from app.rentdesk.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(app)
    assert cl.get("/api/rentdesk").status_code == 200
    nu = cl.post("/api/rentdesk/units", json={"label": "Shop 4", "kind": "shop", "pin": "444101"})
    assert nu.status_code == 200 and nu.json()["unit"]["use"] == "commercial"
    assert cl.post("/api/rentdesk/units", json={"label": "Bad", "pin": "12"}).status_code == 400
    aid = rc["approval"]["id"]
    assert cl.post(f"/api/rentdesk/approvals/{aid}/decide", json={"hash": "x"}).status_code == 400
    ok = cl.post(f"/api/rentdesk/approvals/{aid}/decide", json={"yes": True, "hash": rc["approval"]["hash"]})
    assert ok.status_code == 200 and ok.json()["approval"]["status"] == "approved"
    msgs = cl.get("/api/rentdesk/messages").json()["messages"]
    assert msgs
    m = msgs[0]
    assert cl.post(f"/api/rentdesk/messages/{m['id']}/send", json={"via": "self", "hash": "nope"}).status_code == 400
    assert cl.post(f"/api/rentdesk/messages/{m['id']}/send", json={"via": "self", "hash": m["hash"]}).json()["message"]["status"] == "sent"
    pay = cl.post(f"/api/rentdesk/tenancies/{t['id']}/receive", json={"amount": 6000, "mode": "cash"})
    assert pay.status_code == 200 and any("revenue stamp" in n for n in pay.json()["notes"])
    assert cl.get(f"/api/rentdesk/payments/{pay.json()['payment']['id']}/receipt.pdf").content[:4] == b"%PDF"
    assert cl.post("/api/rentdesk/register").status_code == 200
    # morning note once
    S.EVENTS.clear()
    first = S.tick(datetime.now(timezone.utc))
    assert first["morning"] == 1 and "rentdesk_day" in kinds(S)
    assert S.tick(datetime.now(timezone.utc))["morning"] == 0
