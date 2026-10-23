"""Banquet Sahayak: rules (slots, enquiry words, refund policy, GST, noise), venue numbers only from her, enquiry -> Telecaller +
free halls, holds that expire and a double-booked hall + slot refused in code, quotation by code with GST per line, every
client-facing step / hold -> confirmed / discount / refund / payment request only by HER tap with the card's hash (money cards with
her real fingerprint), final count lock, BEO, receipts, cancel by her policy, post-event bill, DPDP forget, worker, tools + API."""
import asyncio
import base64
from datetime import date, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.banquet.models  # noqa: F401  (tables for the env fixture's init_db)
import app.telecall.service  # noqa: F401
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)        # 10:30 am IST


@pytest.fixture
def bq(env, monkeypatch):
    from app.banquet import service as S
    events, stored = [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    clk = {"t": NOW}
    monkeypatch.setattr(S, "clock", lambda: clk["t"])
    S.EVENTS, S.STORED, S.CLK = events, stored, clk
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def _venue(S):
    S.save_settings(T, venue="Shubh Mangal Lawns", gstin="27AAPFU0939F1ZV", upi_id="shubhmangal@okicici", phone="9876543210")
    S.hall_save(T, "Kamal Hall", "hall", seated=300, floating=500, rent=50000, rent_full=90000)
    S.hall_save(T, "Green Lawn", "lawn", seated=600, floating=1000)
    S.package_save(T, "Silver Veg", 650, "veg", "paneer, dal makhani, 2 sweets", min_plates=150)
    S.package_save(T, "Jain Thali", 700, "jain")
    S.extra_save(T, "Stage decor", 40000, "decor")
    S.extra_save(T, "Deluxe room", 4500, "rooms")
    S.extra_save(T, "DJ", 15000, "dj")


def _booking(S, client="Sunil Patil", phone="9822012345", day="2026-12-12", slot="evening", hall="Kamal Hall"):
    return S.booking_save(T, client=client, phone=phone, hall=hall, day=day, slot=slot, event_type="shaadi", guests=250,
                          guarantee=200, menu=[{"package": "Silver Veg"}],
                          extras=[{"name": "Stage decor"}, {"name": "Deluxe room", "qty": 2, "nights": 1}])["booking"]


class Phone:
    def __init__(self, device_id):
        self.device_id = device_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def sign(self, ch):
        sig = self.key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))
        return {"challenge_id": ch["challenge_id"], "device_id": self.device_id, "signature": base64.b64encode(sig).decode()}


def test_rules():
    from app.banquet import rules as R
    assert R.slots_clash("full", "morning") and R.slots_clash("evening", "evening") and not R.slots_clash("morning", "evening")
    assert R.slot_of("shaam ka function") == "evening" and R.slot_of("pura din") == "full" and R.slot_of("lunch") == "morning"
    t0 = date(2026, 10, 23)
    e = R.parse_enquiry("Namaste, mera naam Rahul Sharma hai. 12 Dec ko shaadi reception chahiye, 300 log, pure veg, "
                        "budget 5 lakh. Call 98220 12345. OTP 123456", t0)
    assert e["phone"] == "9822012345" and e["date"] == "2026-12-12" and e["guests"] == 300 and e["diet"] == "veg"
    assert e["event_type"] == "wedding" and e["budget"] == 500000 and e["name"] == "Rahul Sharma"
    assert R.date_of("5/1", t0) == date(2027, 1, 5) and R.date_of("2026-11-30", t0) == date(2026, 11, 30)
    assert R.clean("otp 123456 card 4111 1111 1111 1111") == "otp [hataya] card [hataya]"
    pol = R.DEFAULT_CANCEL
    assert R.refund_for(pol, 100, 100000) == (90.0, 90000.0) and R.refund_for(pol, 40, 100000)[0] == 50
    assert R.refund_for(pol, 3, 100000) == (0.0, 0.0)
    probs, notes = R.check_cancel([{"days_before": 60, "refund_pct": 0}])
    assert not probs and any("unfair" in n for n in notes)
    assert R.check_cancel([{"days_before": 10, "refund_pct": 150}])[0]
    assert R.policy_lines(pol)[0].startswith("90+ din pehle")
    assert R.room_gst(4500) == 5 and R.room_gst(9000) == 18 and R.food_gst(False) == 5 and R.food_gst(True) == 18
    assert R.gst_split(1000, 5) == {"cgst": 25.0, "sgst": 25.0, "tax": 50.0}
    assert sum(R.split_amount(100001, R.DEFAULT_STAGES)) == 100001
    assert "10 tak" in R.noise_note("lawn", "23:30", "22:00") or "22:00 tak" in R.noise_note("lawn", "23:30", "22:00")
    assert "Band hall" in R.noise_note("hall", "23:30")
    assert R.plates_billed(250, 200, None) == 250 and R.plates_billed(150, 200) == 200 and R.plates_billed(250, 200, 220) == 220 and R.plates_billed(250, None) == 250


def test_venue_numbers_only_from_her_and_enquiry(bq):
    S = bq
    with pytest.raises(S.BanquetError):
        S.package_save(T, "Gold Non-veg")                                    # no price = refused, never guessed
    with pytest.raises(S.BanquetError):
        S.save_settings(T, gstin="27AAPFU0939F1ZX")
    with pytest.raises(S.BanquetError):
        S.save_settings(T, stages=[{"label": "Advance", "pct": 40}])
    with pytest.raises(S.BanquetError):
        S.hall_save(T, "Terrace")                                              # no capacity
    out = S.save_settings(T, cancel=[{"days_before": 60, "refund_pct": 0}, {"days_before": 0, "refund_pct": 0}])
    assert "unfair" in out["say"]
    S.save_settings(T, cancel=[])                                              # back to the starter
    _venue(S)
    assert S.settings(T)["cancel_starter"] and S.settings(T)["gst_food"] == 5
    e = S.enquiry(T, text="Hi, 300 guests shaadi 12/12 shaam ko, veg. Priya 9988776655", source="whatsapp")
    lead = e["lead"]
    assert lead["number"] == "E-0001" and lead["phone"] == "9988776655" and lead["day"] == "2026-12-12" and lead["slot"] == "evening"
    assert lead["tele_lead"]                                                   # linked to the Telecaller list
    from app.telecall import service as tc
    assert any(x["phone"] == "9988776655" for x in tc.leads(T))
    names = [h["hall"]["name"] for h in e["availability"]["halls"] if h["free"] and h["fits"]]
    assert names == ["Kamal Hall", "Green Lawn"] or set(names) == {"Kamal Hall", "Green Lawn"}
    again = S.enquiry(T, phone="9988776655", guests=350)
    assert not again["fresh"] and again["lead"]["guests"] == 350
    with pytest.raises(S.BanquetError):
        S.enquiry(T, name="X", day="2026-10-01")                               # past date
    with pytest.raises(S.BanquetError):
        S.lead_update(T, "E-0001", status="lost")                              # needs a reason


def test_holds_expire_and_double_booking_refused(bq):
    S = bq
    _venue(S)
    b1 = _booking(S)
    b2 = _booking(S, "Anita Rao", "9811122233", slot="full")
    S.hold(T, b1["number"])
    with pytest.raises(S.BanquetError) as e:
        S.hold(T, b2["number"])                                               # full day clashes with the evening hold
    assert "Double booking" in str(e.value)
    with pytest.raises(S.BanquetError):
        S.close_slot(T, "Kamal Hall", "2026-12-12", "evening")                # even her own block can't sit on a hold
    assert S.free(T, "2026-12-12", "morning")["halls"][0]["free"]             # morning of the same hall is free
    card = S.confirm_request(T, b1["number"])
    assert card["status"] == "needs_tap" and "banquet_card" in kinds(S)
    with pytest.raises(S.BanquetError):
        S.decide(T, card["card"]["id"], True, card["card"]["hash"])          # not from the tool
    # the hold runs out before her tap: the card goes stale, the slot is free for the other client
    S.CLK["t"] = NOW + timedelta(hours=49)
    out = S.tick(S.CLK["t"])
    assert out["expired"] == 1 and "banquet_alert" in kinds(S)
    S.hold(T, b2["number"])
    with pytest.raises(S.BanquetError):
        S.decide(T, card["card"]["id"], True, card["card"]["hash"], by_tap=True)
    assert S.card_view(T, card["card"]["id"])["status"] == "stale"
    with pytest.raises(S.BanquetError):
        S.confirm_request(T, b1["number"])                                     # a new card is refused too: slot taken
    c2 = S.confirm_request(T, b2["number"])
    d = S.decide(T, c2["card"]["id"], True, c2["card"]["hash"], by_tap=True)
    assert d["booking"]["status"] == "confirmed" and "wa.me/919811122233" in d["draft"]["wa"]
    cal = S.calendar(T, "2026-12")
    assert [x["kind"] for x in cal["days"]["2026-12-12"]] == ["confirmed"]
    with pytest.raises(S.BanquetError):                                       # moving another booking onto it is refused too
        S.booking_save(T, b1["number"], slot="morning")
        S.hold(T, b1["number"])


def test_quote_gst_and_her_tap(bq):
    S = bq
    _venue(S)
    b = _booking(S)
    q = S.quote(T, b["number"])["quote"]
    food = q["lines"][0]
    assert food["qty"] == 250 and food["amount"] == 250 * 650 and food["gst_pct"] == 5
    hall = [x for x in q["lines"] if x["kind"] == "hall"][0]
    assert hall["amount"] == 50000 and hall["gst_pct"] == 5                   # hall bundled with her food = composite at food rate
    room = [x for x in q["lines"] if "room" in x["name"].lower()][0]
    assert room["amount"] == 9000 and room["gst_pct"] == 5                    # room tariff <= 7,500 -> 5%
    decor = [x for x in q["lines"] if x["name"] == "Stage decor"][0]
    assert decor["gst_pct"] == 18
    sub = 250 * 650 + 50000 + 9000 + 40000
    assert q["subtotal"] == sub and q["total"] == pytest.approx(sub + (162500 + 50000 + 9000) * 0.05 + 40000 * 0.18)
    assert all(g["cgst"] + g["sgst"] == pytest.approx(g["tax"]) for g in q["gst"])
    # specified premises: food + hall at 18%
    S.save_settings(T, specified=True)
    assert S.quote(T, b["number"])["quote"]["lines"][0]["gst_pct"] == 18
    S.save_settings(T, specified=False)
    # a blank blocks the card
    blank = S.booking_save(T, client="X", phone="9822000000", hall="Green Lawn", day="2026-12-20", slot="evening",
                           extras=[{"name": "Fireworks"}])["booking"]
    with pytest.raises(S.BanquetError) as e:
        S.quote_request(T, blank["number"])
    assert "daam?" in str(e.value)
    c = S.quote_request(T, b["number"])
    assert c["card"]["show"]["cancel_lines"]                                   # refund policy shown upfront
    again = S.quote_request(T, b["number"])
    assert again.get("existing")
    with pytest.raises(S.BanquetError):
        S.decide(T, c["card"]["id"], True, "bad", by_tap=True)
    S.booking_save(T, b["number"], guests=280)                               # changed after the card -> stale
    with pytest.raises(S.BanquetError):
        S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    c = S.quote_request(T, b["number"])
    d = S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    assert "wa.me/919822012345" in d["draft"]["wa"] and S.STORED[-1][0].endswith("_quotation.pdf")
    assert S.STORED[-1][1].startswith(b"%PDF")
    no = S.message_request(T, b["number"], "Kal site visit 11 baje?")
    r = S.decide(T, no["card"]["id"], False, no["card"]["hash"], by_tap=True)
    assert r["card"]["status"] == "rejected"
    with pytest.raises(S.BanquetError):
        S.message_request(T, b["number"], "Apna OTP bhejiye")


def test_money_cards_fingerprint_cancel_refund(bq, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    S = bq
    _venue(S)
    b = _booking(S)
    S.hold(T, b["number"])
    c = S.confirm_request(T, b["number"])
    S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    with pytest.raises(S.BanquetError):
        S.paid(T, b["number"], 50000, actor="staff:s1")
    p = S.paid(T, b["number"], 70000, "upi", "UTR998877665544")
    assert p["receipt"].startswith("R/2627/") and S.booking_view(T, b["number"])["stages"][0]["paid"]
    assert S.receipt_pdf(T, b["number"], p["receipt"]).startswith(b"%PDF")
    d = S.discount_request(T, b["number"], amount=10000, reason="Repeat client")
    from app import approvekey as ak
    phone = Phone("phone-1")
    ak.register(T, phone.device_id, phone.pub, "Pixel")
    with pytest.raises(S.BanquetError) as e:
        S.decide(T, d["card"]["id"], True, d["card"]["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.card_challenge(T, d["card"]["id"])
    with pytest.raises(S.BanquetError):
        S.decide(T, d["card"]["id"], True, d["card"]["hash"], proof=Phone("phone-1").sign(ch), by_tap=True)
    ch = S.card_challenge(T, d["card"]["id"])
    S.decide(T, d["card"]["id"], True, d["card"]["hash"], proof=phone.sign(ch), by_tap=True)
    v = S.booking_view(T, b["number"])
    assert v["discount"] == 10000 and v["quote"]["discount"] == 10000
    # cancelled 50 days before: her policy = 50% of what was paid, on a fingerprint card; hall freed at once
    with pytest.raises(S.BanquetError):
        S.cancel(T, b["number"], "", actor="owner")
    out = S.cancel(T, b["number"], "Family mein shok")
    assert out["card"]["show"]["amount"] == 35000 and out["card"]["show"]["pct"] == 50
    assert S.free(T, "2026-12-12", "evening")["halls"][0]["free"]
    with pytest.raises(S.BanquetError):
        S.forget(T, b["number"])                                              # refund not settled yet
    ch = S.card_challenge(T, out["card"]["id"])
    r = S.decide(T, out["card"]["id"], True, out["card"]["hash"], proof=phone.sign(ch), by_tap=True)
    assert "wa.me" in r["draft"]["wa"] and "Hoola paise nahi bhejta" in r["say"]
    S.refund_sent(T, b["number"], "UTR1122")
    assert S.booking_view(T, b["number"])["refunded"] == 35000
    S.forget(T, b["number"])
    v = S.booking_view(T, b["number"])
    assert v["phone"] == "" and v["client"] == "Client (hataya)" and v["paid"] == 70000


def test_count_lock_beo_bill_and_tick(bq):
    S = bq
    _venue(S)
    S.save_settings(T, morning_time="09:00")
    b = _booking(S, day="2026-11-10", hall="Green Lawn", slot="evening")
    S.booking_save(T, b["number"], menu=[{"package": "Silver Veg", "plates": 200}, {"package": "Jain Thali", "plates": 30}],
                   timeline=[{"at": "19:00", "what": "Baraat"}], beo_notes="Stage east side")
    S.hold(T, b["number"])
    c = S.confirm_request(T, b["number"])
    S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    S.set_count(T, b["number"], 240)
    # lock: 3 days before (7 Nov); tick on 5 Nov reminds, on 7 Nov locks
    S.CLK["t"] = datetime(2026, 11, 5, 4, 0, tzinfo=timezone.utc)
    o = S.tick(S.CLK["t"])
    assert o["alerts"] >= 1 and o["morning"] == 1
    assert S.tick(S.CLK["t"])["morning"] == 0
    S.CLK["t"] = datetime(2026, 11, 7, 4, 0, tzinfo=timezone.utc)
    assert S.tick(S.CLK["t"])["locked"] == 1
    with pytest.raises(S.BanquetError):
        S.set_count(T, b["number"], 200)                                      # after the lock it can't go down
    with pytest.raises(S.BanquetError):
        S.set_count(T, b["number"], 260, actor="staff:s1")
    S.set_count(T, b["number"], 260)
    beo = S.beo(T, b["number"])
    assert beo["beo"]["food"][1]["diet"] == "Jain" and "Khuli jagah" in beo["beo"]["noise"]
    assert S.STORED[-1][0].endswith("_BEO.pdf")
    with pytest.raises(S.BanquetError):
        S.bill_request(T, b["number"], actual=255)                            # before the event
    S.CLK["t"] = datetime(2026, 11, 11, 4, 0, tzinfo=timezone.utc)
    S.paid(T, b["number"], 100000)
    bl = S.bill_request(T, b["number"], actual=255)
    sh = bl["card"]["show"]
    assert sh["paid"] == 100000 and sh["balance"] == pytest.approx(sh["total"] - 100000)
    with pytest.raises(S.BanquetError):
        S.done(T, b["number"])                                                # no bill yet
    d = S.decide(T, bl["card"]["id"], True, bl["card"]["hash"], by_tap=True)
    assert "upi://pay" in d["draft"]["upi"] and S.STORED[-1][0].endswith("_bill.pdf")
    assert S.done(T, b["number"])["booking"]["status"] == "done"


def test_tools_actors_and_api(bq):
    S = bq
    from app.agent.banquet_tools import BANQUET_HANDLERS, BANQUET_TOOLS
    from app.agent.tools import ToolError
    assert {t["name"] for t in BANQUET_TOOLS} == {"banquet", "banquet_dekho"} == set(BANQUET_HANDLERS)
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(BANQUET_HANDLERS[tool](ctx, **a))  # noqa: E731
    run("banquet", action="hall", name="Kamal Hall", seated=200, floating=300, rent=40000)
    run("banquet", action="package", name="Veg Deluxe", price=800, diet="veg")
    e = run("banquet", action="enquiry", text="Main Meera, engagement 15 Jan 2027 subah, 150 log, 9811100022")
    bk = run("banquet", action="booking", lead=e["lead"]["number"], hall="Kamal Hall", menu=[{"package": "Veg Deluxe"}])["booking"]
    assert bk["day"] == "2027-01-15" and bk["slot"] == "morning" and bk["client"] == "Meera"
    run("banquet", action="hold", booking=bk["number"])
    sent = run("banquet", action="quote_send", booking=bk["number"])
    assert sent["status"] == "needs_tap"
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    for a in ({"action": "package", "name": "X", "price": 1}, {"action": "cancel", "booking": bk["number"], "reason": "x"},
              {"action": "paid", "booking": bk["number"], "amount": 10}):
        with pytest.raises(ToolError):
            asyncio.run(BANQUET_HANDLERS["banquet"](staff, **a))
    with pytest.raises(ToolError):
        asyncio.run(BANQUET_HANDLERS["banquet"](staff, action="booking", booking=bk["number"],
                                                 extras=[{"name": "Fireworks", "price": 5000}]))  # staff can't name prices
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(BANQUET_HANDLERS["banquet"](cust, action="enquiry", name="Y"))
    assert run("banquet_dekho", what="day")["waiting"] == 1
    assert run("banquet_dekho", what="free", day="2027-01-15", slot="subah")["halls"][0]["free"] is False

    from app.banquet.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/banquet").status_code == 200
    cid, h = sent["card"]["id"], sent["card"]["hash"]
    assert c.post(f"/api/banquet/cards/{cid}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    r = c.post(f"/api/banquet/cards/{cid}/decide", json={"yes": True, "hash": h})
    assert r.status_code == 200 and r.json()["card"]["status"] == "approved"
    assert c.get(f"/api/banquet/bookings/{bk['number']}/quote.pdf").content.startswith(b"%PDF")
    assert c.get(f"/api/banquet/bookings/{bk['number']}/terms.pdf").status_code == 200
    assert c.get("/api/banquet/calendar", params={"month": "2027-01"}).json()["days"]["2027-01-15"]
    assert c.put("/api/banquet/settings", json={"upi_id": "not a upi"}).status_code == 400
    cf = c.post(f"/api/banquet/bookings/{bk['number']}/confirm").json()
    ok = c.post(f"/api/banquet/cards/{cf['card']['id']}/decide", json={"yes": True, "hash": cf["card"]["hash"]})
    assert ok.status_code == 200 and ok.json()["booking"]["status"] == "confirmed"
    assert c.post(f"/api/banquet/bookings/{bk['number']}/nope").status_code == 404
