"""Homestay Sahayak: rules (OTA mail / iCal reading, rates, policy refund, GST, registration), rooms / guests (IDs only in the
Pehchaan Locker), one calendar with double booking refused from every source, confirmation / messages only on her tap, Form C clock
for foreign guests, check-out turnover tasks, money cards with fingerprint, report, DPDP forget, tools (owner / staff / customer),
worker tick and API (incl. the public calendar link)."""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.homestay.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"

AIRBNB_MAIL = """Reservation confirmed - Priya Sharma arrives {ci_long}
New booking from Priya Sharma
Neem room
Check-in
{ci_long}
Checkout
{co_long}
Guests
2 adults
Confirmation code
HMABC12345
Total payout ₹ 7,650.00
Cancellation policy: Moderate"""

ICS = """BEGIN:VCALENDAR\r
PRODID:-//Airbnb Inc//Hosting Calendar 1.0//EN\r
BEGIN:VEVENT\r
DTSTART;VALUE=DATE:{a1}\r
DTEND;VALUE=DATE:{a2}\r
UID:1418fb94e984-abc@airbnb.com\r
DESCRIPTION:Reservation URL: https://www.airbnb.com/hosting/reservations/\r
 details/HMZZZ11111\\nPhone Number (Last 4 Digits): 4321\r
SUMMARY:Reserved\r
END:VEVENT\r
BEGIN:VEVENT\r
DTSTART;VALUE=DATE:{b1}\r
DTEND;VALUE=DATE:{b2}\r
UID:7f3a-blocked@airbnb.com\r
SUMMARY:Airbnb (Not available)\r
END:VEVENT\r
END:VCALENDAR\r
"""


@pytest.fixture
def hs(env, monkeypatch):
    from app.homestay import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def _setup(S, **kw):
    S.save_settings(T, business="Neem Tree Homestay", host_name="Meghana", phone="98220 11111", address="Khanapur Ves, Akot",
                    state="MH", upi_id="meghana@upi", checkin_time="12:00", checkout_time="11:00",
                    house_rules="Raat 10 ke baad shor nahi. Smoking bahar.", policy="7 din pehle 100%, 2 din pehle 50%, uske baad kuch nahi",
                    menu="breakfast 200, dinner 350", advance_pct=30, review_link="https://g.page/r/neem/review", morning_time="00:00", **kw)
    r1 = S.save_room(T, name="Neem room", base_rate=2500, weekend_rate=3000, extra_person=500, base_guests=2, max_guests=3,
                     ota_names=["Neem Room (Airbnb)"])["room"]
    r2 = S.save_room(T, name="Peepal room", base_rate=2000, max_guests=2)["room"]
    return r1, r2


def _d(S, n):
    return S.today(T) + timedelta(days=n)


def test_rules():
    from app.homestay import rules as R
    assert R.money("2.5k") == 2500 and R.money("₹ 7,650.00") == 7650 and R.phone10("+91 98220 12345") == "9822012345"
    assert R.phone_any("+44 7700 900123") == "+447700900123"
    today = date(2026, 10, 23)
    p = R.parse_ota_email(AIRBNB_MAIL.format(ci_long="Fri, 13 Nov 2026", co_long="Mon, 16 Nov 2026"), today)
    assert p["source"] == "airbnb" and p["ref"] == "HMABC12345" and p["check_in"] == "2026-11-13" and p["check_out"] == "2026-11-16"
    assert p["adults"] == 2 and p["guest_name"] == "Priya Sharma" and p["amount"] == 7650 and not p["cancelled"]
    bk = R.parse_ota_email("Booking.com\nNew booking! Booking number: 4567891234\nGuest name: John Smith\nCheck-in: 20/12/2026\n"
                           "Check-out: 22/12/2026\n2 guests\nTotal price INR 9,000", today)
    assert bk["source"] == "booking" and bk["ref"] == "4567891234" and bk["check_in"] == "2026-12-20" and bk["guest_name"] == "John Smith"
    can = R.parse_ota_email("Your reservation HMABC12345 has been cancelled by the guest. Check-in Nov 13, 2026", today)
    assert can["cancelled"] and can["ref"] == "HMABC12345"
    nothing = R.parse_ota_email("Hello, kya room khaali hai?", today)
    assert nothing["missing"] == ["check_in", "check_out"]
    ics = R.parse_ics(ICS.format(a1="20261201", a2="20261204", b1="20261210", b2="20261211"))
    assert ics["source"] == "airbnb" and len(ics["events"]) == 2
    e0, e1 = ics["events"]
    assert e0["check_in"] == "2026-12-01" and e0["check_out"] == "2026-12-04" and e0["reserved"] and e0["ref"] == "HMZZZ11111"
    assert not e1["reserved"]
    room = {"name": "Neem", "base_rate": 2500, "weekend_rate": 3000, "extra_person": 500, "base_guests": 2, "max_guests": 3}
    q = R.quote([room], date(2026, 11, 12), date(2026, 11, 15), 3, 0, [{"item": "breakfast"}, {"item": "bonfire"}], {"breakfast": 200})
    # Thu 2500 + Fri 3000 + Sat 3000, extra 1 x 3 x 500, breakfast 3 people x 3 days x 200
    assert q["subtotal"] == 2500 + 3000 + 3000 + 1500 + 1800 and q["tax"] == 0 and "bonfire ka daam (menu mein nahi)" in q["missing"]
    q2 = R.quote([room | {"base_rate": 9000, "weekend_rate": 0}], date(2026, 11, 10), date(2026, 11, 11), 2, 0, [], {}, gstin="27ABCDE1234F1Z5")
    assert q2["gst"][0]["pct"] == 18 and R.gst_rate(7500) == 5
    assert "s.9(5)" in R.gst_note("", 2500, True) and "5%" in R.gst_note("27X", 2500, False)
    pol = R.parse_policy("7 din pehle 100%, 2 din pehle 50%, uske baad kuch nahi")
    assert pol == [{"days": 7, "pct": 100}, {"days": 2, "pct": 50}, {"days": 0, "pct": 0}]
    assert R.refund_for(pol, 3000, date(2026, 11, 20), date(2026, 11, 16))["refund"] == 1500
    assert R.refund_for([], 3000, date(2026, 11, 20), date(2026, 11, 16))["refund"] is None
    sc = R.scrub("passport no: K1234567, OTP hai 445566, aadhaar 2345 6789 0124")
    assert "K1234567" not in sc and "445566" not in sc and "2345 6789" not in sc
    assert R.blanks("Kul: [kul daam?] aur [naam?]") == ["[kul daam?]", "[naam?]"]
    ids = [i["id"] for i in R.registration_items("GA", True, True, False)]
    assert "frro" in ids and "fssai" in ids and "society" not in ids
    assert R.state_info("HP")["scheme"].startswith("Himachal") and "Starter" in R.state_info("HP")["note"]
    assert "[naam?]" in R.message_text("confirmation", {})


def test_rooms_guests_calendar_and_no_double_booking(hs, monkeypatch):
    S = hs
    r1, r2 = _setup(S)
    assert r1["number"] == "R-01" and r2["number"] == "R-02" and r1["ota_names"] == ["Neem Room (Airbnb)"]
    g = S.save_guest(T, name="Anna Muller", phone="+49 151 2345 6789", country="DE", passport="C01X00T47",
                     form_c={"nationality": "German", "visa_type": "e-Tourist"})["guest"]
    assert g["foreign"] and g["ids"][0]["masked"].endswith("0T47") and "C01X00T47" not in str(g)
    from app import idvault
    assert any(x["kind"] == "passport" and x["person"].startswith("mehmaan") for x in idvault.list_(T))
    ci, co = _d(S, 10), _d(S, 13)
    b = S.new_booking(T, "Neem room", ci.isoformat(), co.isoformat(), name="Rahul Verma", phone="9822012345", adults=2,
                      addons=["breakfast"])
    bk = b["booking"]
    assert bk["status"] == "hold" and bk["total"] > 0 and bk["advance"] == round(bk["total"] * 0.3) and b["card"]["kind"] == "message"
    assert "Cancellation:" in b["card"]["show"]["text"] and "upi://pay?pa=meghana%40upi" in b["card"]["show"]["text"]
    # overlapping nights in the same room are refused, whatever the source
    with pytest.raises(S.StayError, match="DOUBLE BOOKING"):
        S.new_booking(T, "R-01", _d(S, 12).isoformat(), _d(S, 14).isoformat(), name="X", phone="9822099999")
    with pytest.raises(S.StayError, match="DOUBLE BOOKING"):
        S.block(T, "Neem room", _d(S, 11).isoformat(), _d(S, 12).isoformat())
    with pytest.raises(S.StayError, match="DOUBLE BOOKING"):
        S.new_booking(T, ["R-01", "R-02"], _d(S, 9).isoformat(), _d(S, 11).isoformat(), name="Y", phone="9822088888", source="booking")
    # check-out day = next check-in day is fine; other room is free
    nxt = S.new_booking(T, "R-01", co.isoformat(), _d(S, 15).isoformat(), name="Z", phone="9822077777")["booking"]
    assert nxt["status"] == "hold"
    S.new_booking(T, "Peepal room", ci.isoformat(), co.isoformat(), name="W", phone="9822066666", adults=2)
    with pytest.raises(S.StayError, match="jagah"):
        S.new_booking(T, "R-02", _d(S, 20).isoformat(), _d(S, 21).isoformat(), name="V", phone="9822055555", adults=4)
    with pytest.raises(S.StayError, match="DOUBLE BOOKING"):
        S.update_booking(T, nxt["number"], check_in=_d(S, 12).isoformat())
    av = S.availability(T, _d(S, 10).isoformat(), _d(S, 11).isoformat())
    assert av["free"] == []
    cal = S.calendar(T, _d(S, 10).isoformat(), 5)
    assert cal["rooms"][0]["nights"][0].startswith(bk["number"])
    # an unconfirmed hold runs out and frees the room
    later = S.clock() + timedelta(hours=25)
    monkeypatch.setattr(S, "clock", lambda: later)
    S.tick(later)
    assert S.booking_view(T, bk["number"])["booking"]["status"] == "cancelled"
    assert "homestay_alert" in kinds(S)
    S.new_booking(T, "R-01", ci.isoformat(), _d(S, 11).isoformat(), name="Q", phone="9822044444")


def test_messages_only_on_her_tap(hs):
    S = hs
    _setup(S)
    b = S.new_booking(T, "R-01", _d(S, 5).isoformat(), _d(S, 7).isoformat(), name="Rahul", phone="9822012345")
    card = b["card"]
    with pytest.raises(S.StayError, match="tap"):
        asyncio.run(S.send_message(T, card["id"], "self", card["hash"]))
    with pytest.raises(S.StayError):
        asyncio.run(S.send_message(T, card["id"], "self", "wrong", by_tap=True))
    out = asyncio.run(S.send_message(T, card["id"], "self", card["hash"], by_tap=True))
    assert out["card"]["status"] == "sent" and "pakki" in out["say"]
    assert S.booking_view(T, b["booking"]["number"])["booking"]["status"] == "confirmed"
    # a message with blanks never goes
    S.save_settings(T, review_link="")
    S.save_settings(T, business="")
    c = S.draft_message(T, b["booking"]["number"], "house_rules")["card"]
    assert "[homestay ka naam?]" in c["show"]["text"] and c["show"]["blanks"]
    with pytest.raises(S.StayError, match="khaali"):
        asyncio.run(S.send_message(T, c["id"], "self", c["hash"], by_tap=True))
    ed = S.edit_message(T, c["id"], "Namaste, raat 10 ke baad shor nahi.")["card"]
    assert asyncio.run(S.send_message(T, ed["id"], "self", ed["hash"], by_tap=True))["card"]["status"] == "sent"
    with pytest.raises(S.StayError, match="OTP"):
        S.draft_message(T, b["booking"]["number"], "custom", "Apna OTP batao")
    # a booking change after the card makes the card stale
    c2 = S.draft_message(T, b["booking"]["number"], "custom", "Kal milte hain")["card"]
    S.update_booking(T, b["booking"]["number"], check_out=_d(S, 8).isoformat())
    with pytest.raises(S.StayError, match="badal"):
        asyncio.run(S.send_message(T, c2["id"], "self", c2["hash"], by_tap=True))
    # business route needs the guest to have written to the business number
    c3 = S.draft_message(T, b["booking"]["number"], "custom", "Swagat hai")["card"]
    with pytest.raises(S.StayError, match="business number"):
        asyncio.run(S.send_message(T, c3["id"], "business", c3["hash"], by_tap=True))


def test_ota_mail_and_ical_file(hs):
    S = hs
    _setup(S)
    ci, co = _d(S, 20), _d(S, 23)
    mail = AIRBNB_MAIL.format(ci_long=ci.strftime("%a, %d %b %Y"), co_long=co.strftime("%a, %d %b %Y"))
    r = S.ota_email(T, mail)
    bk = r["booking"]
    assert bk["source"] == "airbnb" and bk["status"] == "confirmed" and bk["ota_ref"] == "HMABC12345" and bk["total"] == 7650
    assert bk["rooms"] == ["Neem room"] and "card" not in r                       # OTA guests: no auto confirmation from Hoola
    again = S.ota_email(T, mail)
    assert again["booking"]["number"] == bk["number"]
    clash = S.ota_email(T, "Booking.com Booking number: 1112223334 Guest name: Ken Ito\nCheck-in: "
                        f"{_d(S, 21).strftime('%d/%m/%Y')}\nCheck-out: {_d(S, 22).strftime('%d/%m/%Y')}\nNeem room", "")
    assert clash["status"] == "clash" and "KHATRA" in clash["say"] and ("homestay_alert", ) == (S.EVENTS[-1][0],)
    assert len(S.bookings(T)) == 1
    cancel = S.ota_email(T, "Reservation HMABC12345 cancelled by guest")
    assert cancel["booking"]["status"] == "cancelled"
    # iCal export she gives: reservations + blocks, re-import frees what disappeared, clashes listed not saved
    a1, a2, b1, b2 = _d(S, 30), _d(S, 33), _d(S, 40), _d(S, 41)
    f = lambda d: d.strftime("%Y%m%d")  # noqa: E731
    res = S.ical_import(T, ICS.format(a1=f(a1), a2=f(a2), b1=f(b1), b2=f(b2)), "R-01")
    assert len(res["made"]) == 2 and not res["clashes"]
    assert any(b["source"] == "airbnb" and b["ota_ref"] == "HMZZZ11111" for b in S.bookings(T))
    S.new_booking(T, "R-02", _d(S, 50).isoformat(), _d(S, 52).isoformat(), name="Direct", phone="9822033333")
    only_one = ICS.format(a1=f(a1), a2=f(a2), b1=f(b1), b2=f(b2)).split("BEGIN:VEVENT")
    snapshot = only_one[0] + "BEGIN:VEVENT" + only_one[1] + "END:VCALENDAR\r\n"
    res2 = S.ical_import(T, snapshot, "R-01")
    assert len(res2["removed"]) == 1 and not res2["made"]
    clash_ics = ICS.format(a1=f(_d(S, 50)), a2=f(_d(S, 51)), b1=f(b1), b2=f(b2)).replace("1418fb94e984", "zz")
    res3 = S.ical_import(T, clash_ics, "R-02")
    assert res3["clashes"] and "TAKRAV" in res3["say"]
    ics = S.ical_export(T)
    assert "Not available" in ics and "Direct" not in ics and "Priya" not in ics and ics.count("BEGIN:VEVENT") >= 2


def test_checkin_form_c_checkout_and_tasks(hs, monkeypatch):
    S = hs
    _setup(S, police_intimation=True)
    g = S.save_guest(T, name="Anna Muller", phone="+4915123456789", country="Germany", passport="C01X00T47", visa="VISA998877",
                     form_c={"nationality": "German"})["guest"]
    b = S.new_booking(T, "R-01", S.today(T).isoformat(), _d(S, 2).isoformat(), guest=g["number"], adults=1)["booking"]
    nxt = S.new_booking(T, "R-01", _d(S, 2).isoformat(), _d(S, 3).isoformat(), name="Next", phone="9822022222")["booking"]
    S.confirm(T, nxt["number"])
    with pytest.raises(S.StayError):
        S.check_in(T, b["number"], actor="staff:abc")                   # a hold needs the owner
    S.confirm(T, b["number"])
    ci = S.check_in(T, b["number"], id_seen=True)
    assert ci["booking"]["status"] == "checked_in" and any("Form C" in w for w in ci["warnings"]) and any("Thane" in w for w in ci["warnings"])
    sheet = S.form_c(T, b["number"])
    vals = {f["key"]: f["value"] for f in sheet["fields"]}
    assert "C01X00T47" not in str(sheet) and "VISA998877" not in str(sheet) and vals["passport_ref"].startswith("{id:")
    assert vals["nationality"] == "German" and "Bharat mein aane ki taarikh" in sheet["missing"] and "indianfrro" in sheet["steps"][0]
    t0 = S.clock()
    monkeypatch.setattr(S, "clock", lambda: t0 + timedelta(hours=13))
    S.tick(t0 + timedelta(hours=13))
    assert any("Form C" in p.get("say", "") for k, p in S.EVENTS if k == "homestay_alert")
    monkeypatch.setattr(S, "clock", lambda: t0 + timedelta(hours=25))
    n = len(S.EVENTS)
    S.tick(t0 + timedelta(hours=25))
    assert any("24 ghante" in p.get("say", "") for k, p in S.EVENTS[n:] if k == "homestay_alert")
    S.form_c_done(T, b["number"], "FRRO/C/123")
    monkeypatch.setattr(S, "clock", lambda: t0)
    out = S.check_out(T, b["number"])
    assert out["tasks"] == 5 and any("departure" in w for w in out["warnings"])
    ts = S.tasks(T)
    assert len(ts) == 5 and ts[0]["due"].startswith(nxt["check_in"])
    S.task_done(T, ts[0]["id"], actor="staff:abc")
    assert len(S.tasks(T)) == 4
    # review request a day later: same words for everyone, via a card
    later = t0 + timedelta(days=1, hours=2)
    monkeypatch.setattr(S, "clock", lambda: later)
    S.tick(later)
    rev = [c for c in S.cards(T) if c["sub"] == "review"]
    assert rev and "imaandaar" in rev[0]["show"]["text"] and "jaisa bhi raha" in rev[0]["show"]["text"]


def test_money_cards_fingerprint_report(hs, monkeypatch):
    S = hs
    _setup(S)
    b = S.new_booking(T, "R-01", _d(S, 10).isoformat(), _d(S, 12).isoformat(), name="Rahul", phone="9822012345")["booking"]
    pl = S.pay_link(T, b["number"])
    assert pl["kind"] == "advance" and pl["amount"] == b["advance"] and "pa=meghana%40upi" in pl["link"]
    with pytest.raises(S.StayError, match="owner"):
        S.received(T, b["number"], 1650, actor="staff:x")
    S.received(T, b["number"], 1650)
    # cancel 8 days before -> 100% of what was paid, only on her tap; money needs her fingerprint once a phone key exists
    cr = S.cancel_request(T, b["number"], "guest", "plan badla")
    card = cr["card"]
    assert card["kind"] == "cancel" and card["show"]["amount"] == 1650 and card["money"]
    with pytest.raises(S.StayError, match="tap"):
        S.decide(T, card["id"], True, card["hash"])
    from app import approvekey
    monkeypatch.setattr(approvekey, "active_on", lambda tenant: True)
    with pytest.raises(S.StayError, match="fingerprint_needed"):
        S.decide(T, card["id"], True, card["hash"], by_tap=True)
    monkeypatch.setattr(approvekey, "active_on", lambda tenant: False)
    d = S.decide(T, card["id"], True, card["hash"], by_tap=True)
    assert d["card"]["status"] == "approved" and "message" in d
    bv = S.booking_view(T, b["number"])["booking"]
    assert bv["status"] == "cancelled" and bv["refund_due"] == 1650
    with pytest.raises(S.StayError):
        S.refund_done(T, b["number"], actor="staff:x")
    assert S.refund_done(T, b["number"], ref="UTR4455")["booking"]["refunded"] == 1650
    # spend card
    sp = S.spend_request(T, "Geyser repair", 1800, "Ramesh plumber")["card"]
    with pytest.raises(S.StayError):
        S.spend_paid(T, sp["id"])
    S.decide(T, sp["id"], True, sp["hash"], by_tap=True)
    assert S.spend_paid(T, sp["id"], "cash")["card"]["status"] == "paid"
    # report: a confirmed stay this month
    first = S.today(T).replace(day=1)
    if (first + timedelta(days=3)).month == first.month:
        mo = S.new_booking(T, "R-02", (first + timedelta(days=1)).isoformat(), (first + timedelta(days=3)).isoformat(), name="M",
                           phone="9822011112", source="booking", total=4000)["booking"]
        S.received(T, mo["number"], 4000, mode="ota")
        rep = S.report(T, first.strftime("%Y-%m"))
        days = ((first.replace(day=28) + timedelta(days=4)).replace(day=1) - first).days
        assert rep["sold"] == 2 and rep["available"] == 2 * days and rep["revenue"] == 4000 and rep["adr"] == 2000
        assert rep["by_source"][0]["source"] == "Booking.com"
    reg = S.registration(T)
    assert reg["state"]["scheme"].startswith("Maharashtra") and reg["missing"]
    S.registration_update(T, number="MH/BB/123", valid_to=_d(S, 20).isoformat(), item="tourism")
    S.tick(S.clock())
    assert any(p.get("kind") == "registration" for k, p in S.EVENTS if k == "homestay_alert")


def test_forget_tools_and_api(hs, monkeypatch):
    S = hs
    _setup(S)
    g = S.save_guest(T, name="Indian Guest", phone="9822012345", aadhaar="2345 6789 0124")["guest"]
    b = S.new_booking(T, "R-01", S.today(T).isoformat(), _d(S, 1).isoformat(), guest=g["number"])["booking"]
    S.confirm(T, b["number"])
    with pytest.raises(S.StayError, match="chal rahi"):
        S.forget(T, g["number"])
    S.check_in(T, b["number"])
    S.check_out(T, b["number"])
    f = S.forget(T, g["number"])
    assert "mita" in f["say"]
    from app import idvault
    assert not any(x["kind"] == "aadhaar" for x in idvault.list_(T))
    fg = S.save_guest(T, name="Anna", phone="+4915100000000", country="DE")["guest"]
    fb = S.new_booking(T, "R-02", S.today(T).isoformat(), _d(S, 1).isoformat(), guest=fg["number"])["booking"]
    S.confirm(T, fb["number"])
    S.check_in(T, fb["number"])
    S.check_out(T, fb["number"])
    with pytest.raises(S.StayError, match="1 saal"):
        S.forget(T, fg["number"])

    # tools: staff can draft / book, can't confirm or say money came; customers refused
    from app.agent.homestay_tools import HOMESTAY_HANDLERS
    from app.agent.tools import ToolError
    ctx = conv_ctx()
    h, hd = HOMESTAY_HANDLERS["homestay"], HOMESTAY_HANDLERS["homestay_dekho"]
    out = asyncio.run(h(ctx, action="book", room="Neem room", check_in=_d(S, 30).isoformat(), nights=2, name="Tool Guest",
                        phone="9822099911"))
    num = out["booking"]["number"]
    assert out["booking"]["status"] == "hold" and out["card"]["kind"] == "message"
    ctx.actor = "staff:abc"
    with pytest.raises(ToolError):
        asyncio.run(h(ctx, action="confirm", booking=num))
    with pytest.raises(ToolError):
        asyncio.run(h(ctx, action="received", booking=num, amount=100))
    assert asyncio.run(h(ctx, action="cancel", booking=num))["status"] == "needs_tap"
    ctx.actor = "customer:wa:9198"
    with pytest.raises(ToolError):
        asyncio.run(hd(ctx, what="day"))
    ctx.actor = "owner"
    assert "say" in asyncio.run(hd(ctx, what="day"))
    assert asyncio.run(hd(ctx, what="rules"))["sources"]

    from app.homestay.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(app)
    ov = cl.get("/api/homestay")
    assert ov.status_code == 200 and ov.json()["rooms"]
    nb = cl.post("/api/homestay/bookings", json={"room": "R-02", "check_in": _d(S, 60).isoformat(), "check_out": _d(S, 62).isoformat(),
                                                 "name": "Api Guest", "phone": "9822077711"})
    assert nb.status_code == 200
    dup = cl.post("/api/homestay/bookings", json={"room": "R-02", "check_in": _d(S, 61).isoformat(), "check_out": _d(S, 63).isoformat(),
                                                  "name": "Dup", "phone": "9822077712"})
    assert dup.status_code == 400 and "DOUBLE" in dup.json()["detail"]
    card = nb.json()["card"]
    assert cl.post(f"/api/homestay/cards/{card['id']}/send", json={"via": "self", "hash": "x"}).status_code == 400
    ok = cl.post(f"/api/homestay/cards/{card['id']}/send", json={"via": "self", "hash": card["hash"]})
    assert ok.status_code == 200 and ok.json()["card"]["status"] == "sent"
    cc = cl.post(f"/api/homestay/bookings/{nb.json()['booking']['id']}/cancel", json={"by": "host"}).json()["card"]
    assert cl.post(f"/api/homestay/cards/{cc['id']}/decide", json={"hash": cc["hash"]}).status_code == 400
    link = S.settings(T)["ical_link"]
    assert cl.get(link).status_code == 200 and "VCALENDAR" in cl.get(link).text
    assert cl.get(f"/api/homestay-ical/{T}/{'x' * 24}.ics").status_code == 404
    assert cl.get("/api/homestay-ical/nobody/abcdefghijklmnopqrstuv.ics").status_code == 404
    assert cl.get("/api/homestay/report").status_code == 200
    assert cl.get("/api/homestay/rules").json()["never"]
