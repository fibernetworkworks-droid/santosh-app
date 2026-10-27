"""Yatra Sahayak (travel agent): rail rules (ARP / Tatkal / chart), pasted-quote parsing + comparison, visa / passport /
documents, trips with IDs only as locker references, itinerary with invented times / fares scrubbed, booking card decided
only by her tap (then the Order karo operator job, which stops at payment), client quote with her markup + PDF, partner API
(Amadeus fake), worker reminders, tools (owner / staff / customer) and API."""
import asyncio
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.travel.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
IST = ZoneInfo("Asia/Kolkata")


def aadhaar():
    from app.idvault import verhoeff_ok
    for d in range(10):
        n = "23456789012" + str(d)
        if verhoeff_ok(n):
            return n
    raise AssertionError


@pytest.fixture
def tv(env, monkeypatch):
    from app.travel import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_ask_json", lambda system, prompt: {})
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def test_rail_rules_quotes_and_documents():
    from app.travel import rules as R
    t = R.tatkal_open(date(2026, 12, 20), "3A")
    assert t["at"] == "2026-12-19T10:00" and t["agents_from"] == "2026-12-19T10:30" and t["ac"]
    assert R.tatkal_open(date(2026, 12, 20), "sleeper")["at"] == "2026-12-19T11:00"
    assert R.arp_open(date(2026, 12, 20)) == datetime(2026, 10, 21, 8, 0)
    assert R.chart_time(datetime(2026, 12, 20, 16, 30)) == datetime(2026, 12, 20, 8, 30)
    assert R.chart_time(datetime(2026, 12, 20, 9, 0)) == datetime(2026, 12, 19, 21, 0)
    assert R.chart_time(datetime(2026, 12, 20, 2, 0)) == datetime(2026, 12, 19, 20, 0)
    assert R.norm_class("3ac") == "3A" and R.norm_quota("tatkaal") == "TQ" and R.norm_quota("premium tatkal") == "PT"
    q = R.parse_quotes("1. IndiGo 6E 5123 06:10-08:25 ₹4,850 non-refundable\n"
                       "2. Air India AI 865 09:00 - 11:20 Rs 5,600 refundable\n"
                       "3. Hotel Sea View 3* rating 4.2 ₹3,200/night\n"
                       "4. Hotel Palm Grove 4.6/5 Rs. 4,100 per night\n"
                       "5. Konkan Kanya 10111 SL 23:05 10:30")
    assert [x["mode"] for x in q] == ["flight", "flight", "hotel", "hotel", "train"]
    assert q[0]["price_paise"] == 485000 and q[0]["duration_min"] == 135 and q[0]["code"] == "6E 5123" and q[0]["refundable"] is False
    assert q[1]["refundable"] is True and q[2]["stars"] == 3 and q[2]["rating"] == 4.2 and q[2]["per_night"]
    assert q[3]["rating"] == 4.6 and q[4]["price_paise"] is None and q[4]["code"] == "10111" and q[4]["cls"] == "SL"
    assert q[4]["duration_min"] == 11 * 60 + 25                      # overnight
    rows = [dict(x, id=f"o{i}") for i, x in enumerate(q)]
    c = R.compare(rows, nights=3)
    assert c["flight"]["cheapest"] == "o0" and c["flight"]["fastest"] == "o0"
    assert c["hotel"]["cheapest"] == "o2" and c["hotel"]["best_rated"] == "o3"
    assert next(r for r in c["hotel"]["rows"] if r["id"] == "o2")["total_paise"] == 960000
    assert "daam pata nahi" in c["train"]["rows"][0]["tags"]
    assert R.country_of("Dubai 5 din") == "uae" and R.country_of("Paris honeymoon") == "france" and R.country_of("Goa trip") == ""
    assert R.visa_info("nepal")["need"] is False and "official" in R.visa_info("thailand")["say"]
    assert R.visa_info("france")["name"].startswith("Schengen")
    assert R.passport_check("2027-03-01", "2026-12-28", "uae")["ok"] is False
    assert R.passport_check("2027-08-01", "2026-12-28", "uae")["ok"] is True
    assert R.passport_check("2027-04-15", "2026-12-28", "france")["ok"] is True       # Schengen: 3 months
    docs = R.doc_checklist({"modes": {"flight", "hotel"}, "international": True, "country": "france",
                            "travellers": [{"name": "Riya", "age": 8}]})
    ids = {d["id"] for d in docs}
    assert {"passport", "visa", "insurance", "flight_id", "hotel_voucher", "minor_Riya"} <= ids
    assert next(d for d in docs if d["id"] == "insurance")["must"] is True
    dom = {d["id"] for d in R.doc_checklist({"modes": {"train"}, "tatkal": True, "travellers": []})}
    assert {"train_id", "tatkal_aadhaar"} <= dom and "passport" not in dom
    assert "Garam kapde / jacket" in R.packing(4, 12, "manali") and "Swimwear" in R.packing(3, 4, "goa beach")
    assert R.maps_link("Calangute Beach", "Goa").startswith("https://www.google.com/maps/search/?api=1&query=Calangute")


def test_trip_ids_only_as_locker_refs_and_itinerary(tv):
    S = tv
    from app import idvault
    from app.db import session
    from app.travel.models import TravelTrip
    num = aadhaar()
    out = S.new_trip(T, "Goa family trip", destination="Goa", origin="Pune", start_date="24-12-2026", end_date="27-12-2026",
                     travellers=[{"name": "Meghana", "age": 34, "id_kind": "aadhaar", "id_number": num},
                                 {"name": "Riya", "age": 8}], prefs="beach, veg khana; papa ka aadhaar " + num, budget="40000")
    trip = out["trip"]
    assert trip["number"] == "T-0001" and trip["days"] == 4 and trip["budget"] == "₹40,000"
    m = trip["travellers"][0]
    assert m["id_ref"].startswith("{id:") and m["id_masked"].endswith(num[-4:]) and "id_number" not in m
    with session() as s:
        row = s.get(TravelTrip, trip["id"])
        raw = row.travellers + row.prefs
    assert num not in raw and "{id:" in row.prefs                 # never stored in plain
    assert idvault.resolve(T, m["id_ref"])[0] == num
    assert any("25 Dec" in h["say"] for h in S.get_trip(T, "T-0001")["holidays"])   # Christmas inside the trip
    assert kinds(S)[-1] == "travel_trip"
    # model invents a time, a fee and a phone -> scrubbed; real places get maps links
    S._ask_json = lambda system, prompt: {"days": [{"day": 1, "title": "Calangute", "items": [
        {"place": "Calangute Beach", "what": "Shaam 5:30 pm tak beach, entry ₹200", "note": "Call 9876543210"}]},
        {"day": 2, "title": "Old Goa", "items": [{"place": "Basilica of Bom Jesus", "what": "darshan", "note": ""}]}],
        "tips": ["Taxi ₹1,500 mein milegi"]}
    it = S.plan_itinerary(T, "T-0001")["itinerary"]
    d1 = it["days"][0]["items"][0]
    assert "5:30" not in d1["what"] and "₹200" not in d1["what"] and "[samay?]" in d1["what"] and "[daam?]" in d1["what"]
    assert "9876543210" not in d1["note"] and d1["map"].startswith("https://www.google.com/maps")
    assert it["source"] == "ai" and "[daam?]" in it["tips"][0] and it["days"][0]["date"] == "2026-12-24"
    S._ask_json = lambda system, prompt: {}
    it2 = S.plan_itinerary(T, "T-0001")["itinerary"]
    assert it2["source"] == "template" and len(it2["days"]) == 4 and it2["days"][-1]["title"] == "Wapsi"
    with pytest.raises(S.TravelError):
        S.traveller(T, "T-0001", "add", name="X", id_ref="{id:nonexistent1}")
    S.traveller(T, "T-0001", "add", name="Riya", berth="lower")
    assert S.get_trip(T, "T-0001")["travellers"][1]["berth"] == "lower"


def test_options_compare_train_windows_and_docs(tv):
    S = tv
    S.new_trip(T, destination="Goa", origin="Mumbai", start_date="2026-12-24", end_date="2026-12-27",
               travellers=[{"name": "Meghana", "age": 34}])
    r = S.add_options(T, "T-0001", "IndiGo 6E 5123 06:10-07:25 ₹4,850\nAir India AI 865 09:00-10:20 ₹3,900\n"
                                    "Hotel Sea View rating 4.2 ₹3,200/night\nHotel Palm 4.6/5 ₹4,100 per night")
    assert len(r["options"]) == 4
    S.add_options(T, "T-0001", options=[{"mode": "train", "name": "Konkan Kanya", "code": "10111", "cls": "3A", "quota": "TQ",
                                         "depart": "23:05", "arrive": "10:30"}])
    c = S.compare(T, "T-0001")
    assert "sabse sasta Air India" in c["say"] and c["nights"] == 3
    assert c["compare"]["hotel"]["rows"][0]["total_paise"] == 960000
    assert c["links"]["train"][0]["url"].startswith("https://www.irctc.co.in")
    v = S.get_trip(T, "T-0001")
    w = v["windows"][0]
    assert w["arp_open"] == "2026-10-25T08:00" and w["tatkal"]["at"] == "2026-12-23T10:00" and w["chart"] == "2026-12-24T15:05"
    assert "tatkal_aadhaar" in {d["id"] for d in v["docs"]}
    out = S.doc_mark(T, "T-0001", "train_id", True)
    assert "Har yatri ka original photo ID (train)" not in out["say"]
    ti = S.train_info("20-12-2026", "SL", "09:00", "TQ")
    assert ti["tatkal"]["at"] == "2026-12-19T11:00" and ti["chart"] == "2026-12-19T21:00" and "IRCTC" in ti["say"]
    with pytest.raises(S.TravelError):
        S.add_options(T, "T-0001", "kuch nahi")


def test_booking_only_on_her_tap_then_operator_stops_at_payment(tv, monkeypatch):
    S = tv
    from app.agent.tools import ToolError
    from app.agent.travel_tools import TRAVEL_HANDLERS
    num = aadhaar()
    S.new_trip(T, destination="Goa", origin="Mumbai", start_date="2026-12-24", end_date="2026-12-27",
               travellers=[{"name": "Meghana", "age": 34, "id_kind": "aadhaar", "id_number": num}])
    opt = S.add_options(T, "T-0001", options=[{"mode": "train", "name": "Konkan Kanya", "code": "10111", "cls": "3A",
                                               "depart": "23:05", "price": 1450}])["options"][0]
    ctx = conv_ctx()
    out = asyncio.run(TRAVEL_HANDLERS["travel"](ctx, action="book", trip="T-0001", option=opt["id"]))
    assert out["status"] == "needs_tap" and out["booking"]["status"] == "waiting" and kinds(S)[-1] == "travel_booking"
    card = out["booking"]["card"]
    assert card["site"] == "irctc" and card["travellers"][0]["id"].endswith(num[-4:]) and num not in json.dumps(card)
    bid, h = out["booking"]["id"], out["booking"]["hash"]
    again = S.booking_request(T, "T-0001", opt["id"])                     # same card, not a second one
    assert again["booking"]["id"] == bid
    with pytest.raises(S.TravelError):
        S.decide_booking(T, bid, True, h)                                  # not a tap
    with pytest.raises(S.TravelError):
        S.decide_booking(T, bid, True, "wrong", by_tap=True)
    calls = []

    def fake_order(tenant, what, conversation_id="", site="", budget="", when="", address="", notes="", compare=None, created_by="owner"):
        calls.append({"what": what, "site": site, "budget": budget, "when": when})
        return {"id": "shop1", "status": "working", "say": "IRCTC par taiyaar kar raha hoon, payment par rukunga."}
    from app.shop import service as shop
    monkeypatch.setattr(shop, "order", fake_order)
    # the option changes after the card -> the old hash no longer matches
    from app.db import session
    from app.travel.models import TravelOption
    with session() as s:
        s.get(TravelOption, opt["id"]).price_paise = 160000
    with pytest.raises(S.TravelError):
        S.decide_booking(T, bid, True, h, by_tap=True)
    fresh = S.booking_request(T, "T-0001", opt["id"])["booking"]
    assert fresh["id"] == bid and fresh["hash"] != h
    res = S.decide_booking(T, bid, True, fresh["hash"], by_tap=True)
    assert res["booking"]["status"] == "working" and calls and calls[0]["site"] == "irctc" and calls[0]["when"] == "2026-12-24"
    assert "{id:" in calls[0]["what"] and num not in calls[0]["what"] and "Stop at payment" in calls[0]["what"]
    assert S.decide_booking(T, bid, True, fresh["hash"], by_tap=True)["say"].startswith("Is card par faisla")
    with pytest.raises(ToolError):                                        # staff can't mark booked
        ctx2 = conv_ctx()
        ctx2.actor = "staff:abc"
        asyncio.run(TRAVEL_HANDLERS["travel"](ctx2, action="booked", booking=bid, pnr="4512345678"))
    done = asyncio.run(TRAVEL_HANDLERS["travel"](ctx, action="booked", booking=bid, pnr="4512345678", paid="1600"))
    assert done["booking"]["status"] == "booked" and done["booking"]["pnr"] == "4512345678"
    assert S.get_trip(T, "T-0001")["status"] == "booked"
    # a hotel without a Hoola-run site: she books herself from the link
    h2 = S.add_options(T, "T-0001", options=[{"mode": "cab", "name": "Local cab", "price": 2500}])["options"][0]
    b2 = S.booking_request(T, "T-0001", h2["id"])["booking"]
    r2 = S.decide_booking(T, b2["id"], True, b2["hash"], by_tap=True)
    assert r2["booking"]["status"] == "self"
    b3 = S.booking_request(T, "T-0001", opt["id"])                         # already booked
    assert "pehle se" in b3["say"]


def test_client_quote_with_her_markup_needs_tap(tv, monkeypatch):
    S = tv
    S.save_settings(T, mode="agency", agency_name="Ingle Tours", contact="+91 8956555723", markup_pct=10, markup_flat="500",
                    gst_pct=18, terms="50% advance\nCancellation as per airline / hotel")
    S.new_trip(T, destination="Goa", start_date="2026-12-24", end_date="2026-12-27", client_name="Patil ji",
               client_phone="9822012345", travellers=[{"name": "A", "age": 40}, {"name": "B", "age": 38}])
    assert S.get_trip(T, "T-0001")["for_client"] is True
    o = S.add_options(T, "T-0001", "Air India AI 865 09:00-10:20 ₹8,000\nHotel Palm 4.6/5 ₹4,000 per night\nCab Innova airport")["options"]
    for x in o:
        S.choose(T, "T-0001", x["id"])
    with pytest.raises(S.TravelError) as e:
        S.quote_request(T, "T-0001")
    assert "daam nahi pata" in str(e.value)
    S.choose(T, "T-0001", o[2]["id"], on=False)
    q = S.quote_request(T, "T-0001")
    card = q["quote"]["card"]
    assert card["cost_paise"] == 800000 + 1200000 and card["markup_paise"] == 200000 + 50000
    assert card["total_paise"] == 2000000 + 250000 + 45000 and card["per_person"] == "₹11,475"
    with pytest.raises(S.TravelError):
        S.decide_quote(T, q["quote"]["id"], True, q["quote"]["hash"])
    stored = {}
    from app import chatfiles
    monkeypatch.setattr(chatfiles, "store", lambda tenant, name, data, ct="": stored.update(name=name, data=data) or {"file_id": "f1", "name": name})
    r = S.decide_quote(T, q["quote"]["id"], True, q["quote"]["hash"], by_tap=True)
    assert r["quote"]["status"] == "approved" and stored["data"][:4] == b"%PDF" and stored["name"].startswith("Quote-Q-0001")
    assert r["drafts"]["whatsapp"].startswith("https://wa.me/919822012345") and "₹22,950" in r["drafts"]["text"]
    assert S.get_trip(T, "T-0001")["status"] == "quoted"
    q2 = S.quote_request(T, "T-0001")
    S.add_options(T, "T-0001", options=[{"mode": "bus", "name": "Neeta", "price": 900}])
    assert S.quote_request(T, "T-0001")["quote"]["number"] == "Q-0003"
    with pytest.raises(S.TravelError):                                     # older card went stale
        S.decide_quote(T, q2["quote"]["id"], True, q2["quote"]["hash"], by_tap=True)


def test_partner_api_amadeus_fake(tv):
    S = tv
    from app.travel import adapters as A
    seen = []

    def handler(req: httpx.Request):
        seen.append(req.url.path)
        if req.url.path == "/v1/security/oauth2/token":
            body = req.content.decode()
            return httpx.Response(200 if "client_secret=s3cret" in body else 401, json={"access_token": "tok"})
        if req.url.path == "/v2/shopping/flight-offers":
            assert req.headers["Authorization"] == "Bearer tok" and req.url.params["originLocationCode"] == "BOM"
            return httpx.Response(200, json={"data": [
                {"id": "1", "price": {"grandTotal": "4321.00", "currency": "INR"},
                 "itineraries": [{"duration": "PT1H15M", "segments": [{"carrierCode": "6E", "number": "5123",
                                                                       "departure": {"at": "2026-12-24T06:10:00"},
                                                                       "arrival": {"at": "2026-12-24T07:25:00"}}]}]}],
                "dictionaries": {"carriers": {"6E": "INDIGO"}}})
        return httpx.Response(404)
    A.set_transport(httpx.MockTransport(handler))
    try:
        with pytest.raises(S.TravelError):
            S.partner_set(T, "amadeus", "k", "wrong")
        S.partner_set(T, "amadeus", "k", "s3cret")
        st = S.settings(T)
        assert st["partners"][0]["provider"] == "amadeus" and "s3cret" not in json.dumps(st)
        from app.db import session
        from app.travel.models import TravelSettings
        with session() as s:
            assert "s3cret" not in s.get(TravelSettings, T).partner
        S.new_trip(T, destination="Goa", start_date="2026-12-24", end_date="2026-12-27", travellers=[{"name": "A", "age": 30}])
        r = S.partner_search(T, "T-0001", "amadeus", "BOM", "GOI")
        o = r["options"][0]
        assert o["price_paise"] == 432100 and o["code"] == "6E 5123" and o["duration_min"] == 75 and o["source"] == "partner:amadeus"
        assert o["depart"] == "06:10" and "Indigo" in o["name"]
    finally:
        A.set_transport(None)


def test_reminders_once_each(tv):
    S = tv
    S.new_trip(T, destination="Goa", origin="Mumbai", start_date="2026-12-24", end_date="2026-12-27",
               travellers=[{"name": "A", "age": 30}])
    o = S.add_options(T, "T-0001", options=[
        {"mode": "train", "name": "Konkan Kanya", "cls": "3A", "quota": "TQ", "depart": "23:05", "day": "2026-12-24"},
        {"mode": "flight", "name": "AI 866", "leg": "back", "depart": "18:00", "day": "2026-12-27"}])["options"]
    for x in o:
        S.choose(T, "T-0001", x["id"])

    def at(y, mo, d, h, mi):
        return datetime(y, mo, d, h, mi, tzinfo=IST)
    S.EVENTS.clear()
    S.tick(at(2026, 10, 25, 7, 45))                         # ARP opens 08:00 on 25 Oct
    S.tick(at(2026, 10, 25, 7, 50))
    rem = [p for k, p in S.EVENTS if k == "travel_reminder"]
    assert [p["kind"] for p in rem] == ["arp"]
    S.tick(at(2026, 12, 23, 9, 40))                         # Tatkal 10:00 on 23 Dec
    S.tick(at(2026, 12, 23, 19, 0))                         # eve of the trip
    rem = [p["kind"] for k, p in S.EVENTS if k == "travel_reminder"]
    assert rem.count("tatkal") == 1 and rem.count("eve") == 1
    S.tick(at(2026, 12, 25, 19, 0))                         # web check-in window of the 27 Dec flight
    S.tick(at(2026, 12, 26, 9, 0))
    rem = [p["kind"] for k, p in S.EVENTS if k == "travel_reminder"]
    assert rem.count("checkin") == 1
    assert any(k == "travel_day" for k, _ in S.EVENTS)


def test_tools_and_api(tv):
    S = tv
    from app.agent.tools import ToolError
    from app.agent.travel_tools import TRAVEL_HANDLERS, TRAVEL_LABELS, TRAVEL_TOOLS
    assert {t["name"] for t in TRAVEL_TOOLS} == set(TRAVEL_HANDLERS) == set(TRAVEL_LABELS)
    ctx = conv_ctx()
    out = asyncio.run(TRAVEL_HANDLERS["travel"](ctx, action="new", destination="Dubai", start_date="2027-01-10",
                                                end_date="2027-01-14", travellers=[{"name": "A", "age": 30, "passport_expiry": "2027-03-01"}]))
    assert out["trip"]["country"] == "uae" and any(p["ok"] is False for p in out["trip"]["passport"])
    cust = conv_ctx()
    cust.actor = "customer:wa:91999"
    with pytest.raises(ToolError):
        asyncio.run(TRAVEL_HANDLERS["travel"](cust, action="new", destination="Goa"))
    staff = conv_ctx()
    staff.actor = "staff:s1"
    with pytest.raises(ToolError):
        asyncio.run(TRAVEL_HANDLERS["travel"](staff, action="settings", markup_pct=50))
    v = asyncio.run(TRAVEL_HANDLERS["travel_dekho"](ctx, what="visa", country="Bangkok"))
    assert v["country"] == "thailand" and v["need"] is None
    tr = asyncio.run(TRAVEL_HANDLERS["travel_dekho"](ctx, what="train", day="2026-12-20", cls="2A", quota="TQ"))
    assert tr["tatkal"]["at"].endswith("10:00")
    assert "decide" not in json.dumps(TRAVEL_TOOLS[0]["input_schema"]["properties"]["action"])
    from app.travel.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    r = c.post("/api/travel/trips", json={"destination": "Goa", "origin": "Pune", "start_date": "24-12-2026",
                                          "end_date": "26-12-2026", "travellers": [{"name": "M", "age": 34}]})
    assert r.status_code == 200
    ref = r.json()["trip"]["number"]
    r = c.post(f"/api/travel/trips/{ref}/options", json={"text": "Neeta Volvo 22:00-06:00 ₹1,200"})
    oid = r.json()["options"][0]["id"]
    assert r.json()["options"][0]["mode"] == "bus"
    b = c.post(f"/api/travel/trips/{ref}/book", json={"option": oid}).json()["booking"]
    r = c.post(f"/api/travel/bookings/{b['id']}/decide", json={"yes": False, "hash": b["hash"]})
    assert r.status_code == 200 and r.json()["booking"]["status"] == "rejected"
    assert c.get("/api/travel").json()["trips"]
    assert c.get(f"/api/travel/trips/{ref}/compare").json()["compare"]["bus"]["rows"]
    assert c.post("/api/travel/trips", json={}).status_code == 400
    assert c.get("/api/travel/train", params={"day": "2026-12-20"}).json()["arp_open"] == "2026-10-21T08:00"
    assert c.post(f"/api/travel/trips/{ref}/forget").status_code == 400          # trip still open
    c.post(f"/api/travel/trips/{ref}/cancel")
    assert c.post(f"/api/travel/trips/{ref}/forget").status_code == 200
