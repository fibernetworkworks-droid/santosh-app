"""Tour Guide Sahayak: rules / parsers, tours with HER prices + timings, enquiries (only what is written), group file with IDs in the
locker, no overbooking / double booking in code, confirmation + guest messages + refund / discount / spend as cards only her tap
decides (fingerprint for money), day plan / safety + weather / roll call / scripts / review request / Yatra link, licences, ledger,
DPDP forget, tools (owner / staff / customer), API, worker tick."""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.tourguide.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
AADHAAR = "2345 6789 0124"


@pytest.fixture
def tg(env, monkeypatch):
    from app.tourguide import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def _setup(S, policy=True, **tk):
    S.save_settings(T, business="Pune Heritage Walks", guide_name="Meghana", phone="98220 11111", city="Pune", state="MH",
                    upi_id="meghana@okaxis", cancel_policy="24 ghante pehle tak poora refund, uske baad 50%." if policy else "",
                    morning_time="00:00", review_link="https://g.page/r/demo/review")
    kw = dict(title="Shaniwar Wada heritage walk", kind="heritage", city="Pune", duration_min=150, price_pp=600, group_max=10,
              meeting_point="Shaniwar Wada main gate", includes="guide, paani",
              places=[{"name": "Shaniwar Wada", "stop_min": 60, "open": "8:00", "close": "18:30", "closed_on": "", "ticket_in": 25,
                       "ticket_foreign": 300, "source": "ASI board", "asi": True},
                      {"name": "Kasba Ganpati", "stop_min": 30, "walk_min": 10},
                      {"name": "Lal Mahal", "stop_min": 30, "open": "09:30", "close": "17:30", "closed_on": "mon"}])
    kw.update(tk)
    return S.save_tour(T, **kw)["tour"]


def test_rules():
    from app.tourguide import rules as R
    t0 = date(2026, 10, 23)
    assert R.money("1.5k") == 1500 and R.money("₹ 2,500") == 2500 and R.money("") is None
    assert R.phone10("+91 98220 11111") == "9822011111" and R.phone10("12345") == ""
    assert R.parse_time("subah 7") == "07:00" and R.parse_time("shaam 5 baje") == "17:00" and R.parse_time("5:30 pm") == "17:30"
    assert R.parse_date("kal", t0) == date(2026, 10, 24) and R.parse_date("02/11", t0) == date(2026, 11, 2)
    assert R.days_list("Monday, shukravar") == ["mon", "fri"]
    e = R.parse_enquiry("Hi, 4 log, 02/11 ko subah 7 baje heritage walk chahiye, English guide. Call 98765 43210", t0)
    assert e == {"date": "2026-11-02", "guests": 4, "start_time": "07:00", "phone": "9876543210", "language": "en"}
    assert R.parse_enquiry("kuch bhi nahi", t0) == {}
    assert R.price_for(600, None, 10, 4) == (2400, "4 x per person")
    assert R.price_for(None, 5000, 10, 4)[0] == 5000 and R.price_for(None, None, 10, 4)[0] is None
    lines, warns = R.safety_lines("trek", "ek senior, asthma", 18, {"rain_chance_pct": 80, "max_c": 39})
    assert any("Asthma" in l for l in lines) and any("co-guide" in l for l in lines)
    assert any("Baarish" in w and "taalna" in w for w in warns) and any("Garmi" in w for w in warns)
    sc = R.scrub("OTP 445566 card 4111 1111 1111 1111 aadhaar 2345 6789 0124 PAN ABCDE1234F")
    assert "445566" not in sc and "4111" not in sc and "2345 6789" not in sc and "ABCDE1234F" not in sc
    assert "998556" in R.gst_note("guide") and "5%" in R.gst_note("tour5")
    assert len(R.SOURCES) >= 8 and all(u.startswith("https://") for _, u, _ in R.SOURCES)


def test_tours_enquiry_group_file_and_no_overbooking(tg):
    S = tg
    tour = _setup(S)
    assert tour["number"] == "TP-01" and tour["price_text"].startswith("₹600") and not tour["missing"]
    t2 = S.save_tour(T, title="Food walk", kind="food", city="Pune")
    assert set(t2["tour"]["missing"]) >= {"daam", "group size"} and "baaki" in t2["say"]
    day = S.today(T) + timedelta(days=5)
    enq = S.enquiry(T, f"Namaste, hum 4 log hain, {day.strftime('%d/%m/%Y')} subah 8 baje walk chahiye. English. 98765 43210",
                    tour="TP-01", lead_name="Anita Rao")
    b = enq["booking"]
    assert b["number"] == "B-0001" and b["guests"] == 4 and b["day"] == day.isoformat() and b["start_time"] == "08:00"
    assert b["language"] == "en" and b["phone"] == "9876543210" and b["total"] == 2400 and b["status"] == "enquiry"
    # group file: IDs and the emergency number only as locker references
    g = S.save_booking(T, b["number"], guest_list=[{"name": "Anita Rao", "age": 40, "id": AADHAAR},
                                                    {"name": "John Smith", "age": 35, "nationality": "foreign"},
                                                    {"name": "Ravi Rao"}, {"name": "Mira Rao", "age": 8}],
                       emergency_phone="9822099999", emergency_name="Suresh", special_needs="ek bachcha 8 saal")["booking"]
    assert g["guest_list"][0]["id_masked"].endswith("0124") and "2345 6789" not in str(g) and "9822099999" not in str(g)
    assert g["foreign_guests"] == 1 and g["emergency"].startswith("Suresh 98")
    from app import idvault
    assert any(x["kind"] == "aadhaar" for x in idvault.list_(T)) and any(x["kind"] == "other" for x in idvault.list_(T))
    with pytest.raises(S.TourError):
        S.save_booking(T, b["number"], notes="OTP 123456 hai")
    S.hold(T, b["number"])
    # same slot: 4 held of 10 -> 7 more = overbooking, refused in code
    b2 = S.save_booking(T, tour="TP-01", day=day.isoformat(), start_time="08:00", guests=7, lead_name="X", phone="9000000001")["booking"]
    with pytest.raises(S.TourError) as e:
        S.hold(T, b2["number"])
    assert "Overbooking" in str(e.value)
    with pytest.raises(S.TourError):
        S.confirm_request(T, b2["number"])
    S.save_booking(T, b2["number"], guests=6)
    assert S.hold(T, b2["number"])["booking"]["status"] == "held"
    # another tour of hers at an overlapping time: she is one guide -> refused; team of 2 -> fine
    t3 = S.save_tour(T, title="Temple trail", kind="temple", city="Pune", duration_min=90, price_group=3000, group_max=8,
                     meeting_point="Kasba")["tour"]
    b3 = S.save_booking(T, tour=t3["number"], day=day.isoformat(), start_time="09:00", guests=2, lead_name="Y", phone="9000000002")["booking"]
    assert b3["total"] == 3000
    with pytest.raises(S.TourError) as e:
        S.hold(T, b3["number"])
    assert "doosre tour" in str(e.value)
    S.save_settings(T, parallel_tours=2)
    assert S.hold(T, b3["number"])["booking"]["status"] == "held"
    with pytest.raises(S.TourError):
        S.save_booking(T, tour="TP-01", day=(S.today(T) - timedelta(days=1)).isoformat(), guests=2)     # past date


def test_confirmation_and_messages_only_on_her_tap(tg, monkeypatch):
    S = tg
    _setup(S, policy=False)
    day = S.today(T) + timedelta(days=3)
    b = S.save_booking(T, tour="TP-01", day=day.isoformat(), start_time="08:00", guests=3, lead_name="Anita Rao",
                       phone="9876543210")["booking"]
    with pytest.raises(S.TourError) as e:
        S.confirm_request(T, b["number"])
    assert "cancellation policy" in str(e.value)                                     # policy upfront, never skipped
    S.save_settings(T, cancel_policy="24 ghante pehle tak poora refund.")
    c = S.confirm_request(T, b["number"], advance=600)
    card = c["card"]
    assert c["status"] == "needs_tap" and card["kind"] == "confirm" and "tourguide_card" in kinds(S)
    assert "poora refund" in card["show"]["text"] and card["show"]["pay_link"].startswith("upi://pay?pa=meghana%40okaxis")
    assert card["show"]["amount"] == 1800 and card["show"]["wa"].startswith("https://wa.me/919876543210")
    assert S.confirm_request(T, b["number"], advance=600)["existing"]
    with pytest.raises(S.TourError):
        asyncio.run(S.decide(T, card["id"], True, card["hash"]))                    # code path never decides
    with pytest.raises(S.TourError):
        asyncio.run(S.decide(T, card["id"], True, "wrong", by_tap=True))
    S.save_booking(T, b["number"], guests=4)                                         # changed after the card -> stale
    with pytest.raises(S.TourError):
        asyncio.run(S.decide(T, card["id"], True, card["hash"], by_tap=True))
    assert S.booking_view(T, b["number"])["status"] == "enquiry"
    card = S.confirm_request(T, b["number"])["card"]
    out = asyncio.run(S.decide(T, card["id"], True, card["hash"], via="self", by_tap=True))
    assert out["card"]["status"] == "sent" and out["booking"]["status"] == "confirmed"
    # a guest message = card; business number only if the guest wrote to it
    m = S.message_request(T, b["number"], "custom", "Kal 7:45 tak pahunch jaiye.")["card"]
    with pytest.raises(S.TourError):
        asyncio.run(S.decide(T, m["id"], True, m["hash"], via="business", by_tap=True))
    from app.employee import inbox
    from app.employee.models import BizContact
    sent = []

    async def fake_send(tenant, cid, text, by="owner", force=False):
        sent.append(text)
        return {"ok": True}
    monkeypatch.setattr(inbox, "send", fake_send)
    with S.session() as s:
        s.add(BizContact(tenant_id=T, wa_id="919876543210", name="Anita"))
    r = asyncio.run(S.decide(T, m["id"], True, m["hash"], via="business", by_tap=True))
    assert r["card"]["status"] == "sent" and sent == ["Kal 7:45 tak pahunch jaiye."]
    with pytest.raises(S.TourError):
        S.message_request(T, b["number"], "custom", "Apna OTP 123456 bhejiye")
    rej = S.message_request(T, b["number"], "custom", "Kuch aur")["card"]
    assert asyncio.run(S.decide(T, rej["id"], False, rej["hash"], by_tap=True))["card"]["status"] == "rejected"


def test_money_cards_fingerprint_and_ledger(tg, monkeypatch):
    S = tg
    _setup(S)
    b = S.save_booking(T, tour="TP-01", day=(S.today(T) + timedelta(days=2)).isoformat(), start_time="08:00", guests=2,
                       lead_name="Ravi", phone="9876500000")["booking"]
    with pytest.raises(S.TourError):
        S.received(T, b["number"], 1200, actor="staff:x")
    S.received(T, b["number"], 1200, "upi", "UTR123456789")
    with pytest.raises(S.TourError):
        S.refund_request(T, b["number"], 1500)                                       # more than she received
    rc = S.refund_request(T, b["number"], 600, "date badli")["card"]
    assert rc["money"] and rc["show"]["policy"]
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    with pytest.raises(S.TourError) as e:
        asyncio.run(S.decide(T, rc["id"], True, rc["hash"], by_tap=True))
    assert str(e.value) == "fingerprint_needed"
    ch = S.challenge(T, rc["id"])
    assert ch["message"].startswith("hoola-approve|v1|default|tourguide|") and ch["show"]["amount"]
    monkeypatch.setattr(ak, "active_on", lambda tenant: False)
    ok = asyncio.run(S.decide(T, rc["id"], True, rc["hash"], by_tap=True))
    assert ok["card"]["status"] == "approved" and "khud" in ok["say"]
    with pytest.raises(S.TourError):
        S.paid_out(T, rc["id"], actor="staff:x")
    assert S.paid_out(T, rc["id"], "UTR99")["card"]["status"] == "done"
    d = S.discount_request(T, b["number"], pct=10, reason="repeat guest")["card"]
    assert d["show"]["amount"] == 120 and not d["money"]
    asyncio.run(S.decide(T, d["id"], True, d["hash"], by_tap=True))
    assert S.booking_view(T, b["number"])["total"] == 1080
    with pytest.raises(S.TourError):
        S.spend_request(T, "auto", None)                                             # never an invented amount
    sp = S.spend_request(T, "Auto rickshaw for group", 450, "Raju auto", b["number"])["card"]
    asyncio.run(S.decide(T, sp["id"], True, sp["hash"], by_tap=True))
    S.paid_out(T, sp["id"])
    with pytest.raises(S.TourError):
        S.ledger_add(T, "spend", 100)                                                # spends only via card
    assert "zabardasti" in S.ledger_add(T, "commission_in", 300, "Silk emporium")["say"]
    S.ledger_add(T, "tip", 200, "Ravi", b["number"])
    L = S.ledger(T)
    assert L["totals"] == {"payment": 1200, "refund": 600, "spend": 450, "commission_in": 300, "tip": 200}
    assert L["net"] == 650


def test_plan_safety_roll_script_review_travel_forget(tg, monkeypatch):
    S = tg
    _setup(S)
    on = S.today(T)
    mon = on + timedelta(days=(7 - on.weekday()) % 7 or 7)                           # a Monday: Lal Mahal is closed then
    b = S.save_booking(T, tour="TP-01", day=mon.isoformat(), start_time="07:30", guests=3, lead_name="Anita", phone="9876543210",
                       guest_list=[{"name": "Anita"}, {"name": "John", "nationality": "foreign"}, {"name": "Ravi"}])["booking"]
    p = S.day_plan(T, b["number"], publish=False)
    assert [x["name"] for x in p["stops"]] == ["Shaniwar Wada", "Kasba Ganpati", "Lal Mahal"]
    assert p["stops"][0]["arrive"] == "07:30" and p["stops"][1]["arrive"] == "08:30" and p["stops"][2]["arrive"] == "09:10"
    w = " ".join(p["warnings"])
    assert "Lal Mahal mon ko band" in w and "8:00" in w and "Kasba Ganpati" in w            # closed day, opens later, timing unknown
    assert p["stops"][1]["open"] == "pata nahi" and p["ticket_total"] == 2 * 25 + 300 and p["asi_steps"]
    S.save_tour(T, "TP-01", places=[{"name": "Shaniwar Wada", "asi": True}])
    assert S.day_plan(T, b["number"], publish=False)["ticket_total"] is None                # ASI rate not given -> blank
    _setup(S)                                                                                # (a new TP-02 with the full places)
    # weather only for today / tomorrow; Open-Meteo faked
    from app import life

    async def geo(city):
        return (18.5, 73.8, "Pune, Maharashtra")

    async def wx(lat, lon, tz="Asia/Kolkata"):
        return {"rain_chance_pct": 85, "today_max_c": 31, "today_min_c": 22, "today": "baarish",
                "tomorrow_rain_chance_pct": 10, "tomorrow_max_c": 40}
    monkeypatch.setattr(life, "geocode", geo)
    monkeypatch.setattr(life, "weather", wx)
    bt = S.save_booking(T, tour="TP-02", day=on.isoformat(), start_time="23:00", guests=2, lead_name="Z", phone="9000000009",
                        special_needs="wheelchair")["booking"]
    sf = asyncio.run(S.weather_check(T, bt["number"]))
    assert any("Baarish" in x for x in sf["warnings"]) and any("Wheelchair" in x for x in sf["lines"])
    far = asyncio.run(S.weather_check(T, b["number"]))
    assert "2 din" in far["say"] or "forecast" in far["say"] or not far["weather"]
    # roll call
    r = S.roll_call(T, b["number"], "Shaniwar Wada", present=["Anita", "Ravi"])
    assert r["missing"] == ["John"] and "tourguide_alert" in kinds(S)
    assert S.roll_call(T, b["number"], "Lal Mahal", count=3)["missing"] == []
    assert S.roll_sheet(T, b["number"])["file"]["file_id"]
    # scripts: templates; other languages only if the numbers survive
    sc = S.intro_script(T, b["number"], language="hinglish")
    assert "Meghana" in sc["text"] and "9822011111" in sc["text"] and not sc["blanks"]
    assert "नमस्ते" in S.intro_script(T, tour="TP-01", language="hi")["text"]
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {"text": "Bonjour ! Je suis Meghana ... 2 heures ... 9822011111"})
    fr = S.intro_script(T, tour="TP-01", language="french")
    assert fr["language"] == "fr" and fr["text"].startswith("Bonjour")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {"text": "Bonjour sans numéro"})
    assert "nahi ban paaya" in S.intro_script(T, tour="TP-01", language="fr")["note"]
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {"places": [{"name": "Vishrambaug Wada", "why": "1 hour, Rs 20"},
                                                                     {"name": "Shaniwar Wada"}]})
    sug = S.suggest_places(T, "TP-01")
    assert [x["name"] for x in sug["places"]] == ["Vishrambaug Wada"] and "20" not in sug["places"][0]["why"]
    # review: only after the tour, and for everyone (no gating)
    with pytest.raises(S.TourError):
        S.review_request(T, b["number"])
    td = S.save_booking(T, tour="TP-02", day=on.isoformat(), start_time="06:00", guests=2, lead_name="Done Guest",
                        phone="9000000010", guest_list=[{"name": "Done Guest", "id": AADHAAR}], emergency_phone="9822012345")["booking"]
    c = S.confirm_request(T, td["number"])["card"]
    asyncio.run(S.decide(T, c["id"], True, c["hash"], by_tap=True))
    S.set_status(T, td["number"], "done")
    rv = S.review_request(T, td["number"])["card"]
    assert rv["kind"] == "message" and "g.page" in rv["show"]["text"] and "sab saathiyon" in rv["show"]["text"]
    # Yatra Sahayak link (travel module, real)
    import app.travel.models  # noqa: F401
    tr = S.travel_link(T, b["number"], origin="Mumbai")
    assert tr["trip"].startswith("T-") and S.booking_view(T, b["number"])["travel_trip"] == tr["trip"]
    # DPDP forget: only after the tour; locker rows deleted
    with pytest.raises(S.TourError):
        S.forget(T, b["number"])
    from app import idvault
    before = len(idvault.list_(T))
    fg = S.forget(T, td["number"])
    v = S.booking_view(T, td["number"])
    assert v["forgotten"] and v["phone"] == "" and v["lead_name"].startswith("Purana") and "2 locker" in fg["say"]
    assert len(idvault.list_(T)) == before - 2


def test_tools_api_licences_and_tick(tg, monkeypatch):
    S = tg
    _setup(S)
    from app.agent import tourguide_tools as TT
    from app.agent.tools import Ctx, ToolError
    ctx = conv_ctx()
    names = {x["name"] for x in TT.TOURGUIDE_TOOLS}
    assert names == set(TT.TOURGUIDE_HANDLERS) == set(TT.TOURGUIDE_LABELS) == {"tour_guide", "tour_guide_dekho"}
    staff = Ctx(T, ctx.conversation_id, actor="staff:abc")
    cust = Ctx(T, ctx.conversation_id, actor="customer:x")
    with pytest.raises(ToolError):
        asyncio.run(TT.tour_guide(staff, "tour", title="X", price_pp=1))
    with pytest.raises(ToolError):
        asyncio.run(TT.tour_guide(cust, "enquiry", text="4 log kal"))
    with pytest.raises(ToolError):
        asyncio.run(TT.tour_guide_dekho(cust, "day"))
    tomorrow = S.today(T) + timedelta(days=1)
    b = asyncio.run(TT.tour_guide(staff, "booking", tour="TP-01", day=tomorrow.isoformat(), start_time="08:00", guests=2,
                                  lead_name="Staff Guest", phone="9123456780"))["booking"]
    with pytest.raises(ToolError):
        asyncio.run(TT.tour_guide(staff, "booking", booking=b["number"], price_total=1))
    cc = asyncio.run(TT.tour_guide(staff, "confirm", booking=b["number"]))
    assert cc["status"] == "needs_tap"
    d = asyncio.run(TT.tour_guide_dekho(ctx, "day"))
    assert d["waiting"] >= 1 and "card" in d["say"]
    assert asyncio.run(TT.tour_guide_dekho(ctx, "rules"))["sources"]
    lic = asyncio.run(TT.tour_guide(ctx, "licence", kind="iitg_heritage", ref="IITG-123", holder="Meghana",
                                    valid_to=(S.today(T) + timedelta(days=100)).isoformat()))
    assert lic["licence"]["days_left"] == 100
    with pytest.raises(ToolError):
        asyncio.run(TT.tour_guide(staff, "licence", kind="state", valid_to="01-01-2030"))
    # API
    from app.tourguide.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(app)
    ov = cl.get("/api/tourguide").json()
    assert ov["tours"] and ov["cards"] and ov["never"]
    assert cl.post("/api/tourguide/tours", json={"title": "Trek", "kind": "trek", "price_pp": "1.2k", "group_max": 12}).json()["tour"]["price_pp"] == 1200
    e = cl.post("/api/tourguide/bookings/enquiry", json={"text": "6 log parso subah 6 baje trek", "tour": "TP-02"}).json()
    assert e["booking"]["guests"] == 6 and "mobile" in e["missing"]
    cid, h = cc["card"]["id"], cc["card"]["hash"]
    assert cl.post(f"/api/tourguide/cards/{cid}/decide", json={"yes": True, "hash": "x"}).status_code == 400
    ok = cl.post(f"/api/tourguide/cards/{cid}/decide", json={"yes": True, "hash": h, "via": "self"})
    assert ok.status_code == 200 and ok.json()["booking"]["status"] == "confirmed"
    rf = cl.post(f"/api/tourguide/bookings/{b['id']}/received", json={"amount": 1200}).json()
    assert rf["booking"]["paid"] == 1200
    rc = cl.post(f"/api/tourguide/bookings/{b['id']}/refund", json={"amount": 300}).json()["card"]
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    assert cl.post(f"/api/tourguide/cards/{rc['id']}/decide", json={"yes": True, "hash": rc["hash"]}).status_code == 428
    assert cl.post(f"/api/tourguide/cards/{rc['id']}/challenge").json()["message"].startswith("hoola-approve")
    monkeypatch.setattr(ak, "active_on", lambda tenant: False)
    assert cl.get(f"/api/tourguide/bookings/{b['id']}/plan").json()["stops"]
    assert cl.post("/api/tourguide/register").status_code == 200
    assert cl.get("/api/tourguide/rules").json()["sources"]
    # worker: licence window (+ refresher), tomorrow's reminder CARD (never sent), morning note once
    S.EVENTS.clear()
    out = S.tick(datetime.now(timezone.utc))
    assert out["morning"] == 1 and "tourguide_day" in kinds(S)
    alerts = [p for k, p in S.EVENTS if k == "tourguide_alert"]
    assert any("refresher" in a["say"] for a in alerts)
    rem = [p for k, p in S.EVENTS if k == "tourguide_card" and p["card"]["show"].get("kind") == "reminder"]
    assert rem and rem[0]["card"]["status"] == "waiting" and "Shaniwar Wada main gate" in rem[0]["card"]["show"]["text"]
    S.EVENTS.clear()
    again = S.tick(datetime.now(timezone.utc))
    assert again["morning"] == 0 and again["alerts"] == 0
