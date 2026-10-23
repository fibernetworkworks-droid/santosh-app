"""Shaadi Sahayak: community functions with dates only from her, panchang facts without any invented muhurat, checklist counted
back, timeline + noise rule, guests / RSVP / headcount / sheet import, rooms with overbooking refused, vendors with HER quotes,
booking / payment / spend / client quote / messages only by her tap with the card's hash (money cards with her real fingerprint),
stale cards, budget, shagun register owner-only + masked + dowry list, child marriage / dowry refused, travel hand-off, DPDP
forget, worker, tools (staff / customer actors) and API."""
import asyncio
import base64
from datetime import date, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.shaadi.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def sh(env, monkeypatch):
    from app.shaadi import service as S
    events, stored = [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    monkeypatch.setattr(S, "today", lambda tenant: date(2026, 10, 23))
    S.EVENTS, S.STORED = events, stored
    return S


def _wedding(S, **kw):
    w = S.wedding_new(T, title="Priya weds Rohan", community="Marathi", bride="Priya Kulkarni", groom="Rohan Deshpande",
                      city="Pune", state="Maharashtra", venue="Shubh Lawns, Baner", budget="25 lakh",
                      dates={"sakharpuda": "2026-12-10", "haldi": "2026-12-13", "lagna": "14-12-2026", "reception": "2026-12-14"}, **kw)
    return w["wedding"]


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
    from app.shaadi import rules as R
    assert R.community_of("hum Marathi hain") == "marathi" and R.community_of("nikah hai") == "muslim"
    assert R.community_of("court marriage karni hai") == "interfaith"
    assert R.vendor_kind("Sharma Caterers") == "caterer" and R.vendor_kind("Panditji") == "pandit" and R.vendor_kind("DJ Bunty") == "dj"
    assert R.hhmm("7 pm") == 19 * 60 and R.hhmm("7:30 shaam") == 19 * 60 + 30 and R.hhmm("10") == 600 and R.hhmm("abc") is None
    assert R.noise_problem(19 * 60, 23 * 60, True) and not R.noise_problem(19 * 60, 21 * 60 + 30, True)
    assert not R.noise_problem(19 * 60, 23 * 60, False)
    assert "baal vivah" in R.age_problem(17, 25) and "baal vivah" in R.age_problem(20, 20) and R.age_problem(18, 21) == ""
    assert R.dowry_problem("dahej ki list") and not R.dowry_problem("shagun list")
    assert R.mask_name("Sunita Mehra") == "Sunita M." and R.clean("OTP 123456 card 4111 1111 1111 1111") == "OTP [hataya] card [hataya]"
    assert R.phone("+91 98220 12345") == "9822012345" and R.phone("12345") == ""


def test_wedding_functions_muhurat_panchang_checklist_timeline(sh):
    S = sh
    with pytest.raises(S.ShaadiError) as e:
        S.wedding_new(T, bride="A", groom="B", age_bride=16)
    assert "baal vivah" in str(e.value)
    w = _wedding(S)
    names = [f["name"] for f in w["functions"]]
    assert names[0] == "Sakharpuda" and "Lagna" in names and "Kelvan" in names        # community starter list
    assert w["first_date"] == "2026-12-10" and w["last_date"] == "2026-12-14" and w["community"] == "marathi"
    # muhurat: never computed; stored only as she says, with who gave it
    p = S.panchang(T, w["id"])
    lagna = [d for d in p["days"] if d["function"] == "Lagna"][0]
    assert lagna["tithi"] and lagna["nakshatra"] and lagna["muhurat"] == "" and "panditji" in lagna["muhurat_note"].lower()
    assert all(d.get("muhurat") == "" for d in p["days"] if d.get("date"))
    out = S.fn_set(T, w["id"], "lagna", start="11 am", muhurat="12:35 pm (godhuli nahi)", muhurat_by="Joshi guruji")
    assert out["function"]["muhurat"].startswith("12:35") and out["function"]["muhurat_by"] == "Joshi guruji"
    assert [d for d in S.panchang(T, w["id"])["days"] if d["function"] == "Lagna"][0]["muhurat_by"] == "Joshi guruji"
    with pytest.raises(S.ShaadiError):
        S.fn_set(T, w["id"], "haldi", date_="32-13-2026")
    clash = S.fn_set(T, w["id"], "reception", start="11:30 am")
    assert any("takra" in x for x in clash["warnings"])
    S.fn_set(T, w["id"], "reception", start="7 pm", end="11 pm")
    S.fn_set(T, w["id"], name="Mehendi", add=True)
    S.fn_set(T, w["id"], "mehendi", date_="2026-12-12", start="4 pm")
    # checklist counted back from the first function (10 Dec)
    cl = S.checklist(T, w["id"])["items"]
    venue = [c for c in cl if "Venue" in c["what"]][0]
    assert venue["due"] == (date(2026, 12, 10) - timedelta(days=210)).isoformat() and venue["state"] == "late"
    reg = [c for c in cl if "registration" in c["what"]][0]
    assert reg["due"] == (date(2026, 12, 14) + timedelta(days=30)).isoformat()      # after the LAST function
    S.checklist_mark(T, w["id"], venue["id"])
    assert [c for c in S.checklist(T, w["id"])["items"] if c["id"] == venue["id"]][0]["done"]
    # timeline: starter needs her start time; DJ after 10 pm -> noise warning
    with pytest.raises(S.ShaadiError):
        S.timeline_set(T, w["id"], "haldi", starter=True)
    S.vendor_add(T, w["id"], "DJ Bunty", "dj", "9811111111", ["reception"], quote=35000)
    tl = S.timeline_set(T, w["id"], "reception", starter=True)
    assert tl["function"]["timeline"][0]["time"] == "15:00" and any("raat 10" in x for x in tl["warnings"])
    tl = S.timeline_set(T, w["id"], "lagna", starter=True)
    assert any(r["who"] == "pandit" and r["time"].startswith("12:35") for r in tl["function"]["timeline"])
    plan = S.day_plan(T, w["id"])
    assert [d["date"] for d in plan["days"]][:2] == ["2026-12-10", "2026-12-12"]


def test_guests_rsvp_headcount_import_rooms(sh):
    S = sh
    w = _wedding(S)
    g1 = S.guest_add(T, w["id"], "Sunita Mehra", "bride", "9822012345", adults=2, kids=1, diet="veg", city="Nagpur",
                     needs_room=True, arrive="2026-12-12", depart="2026-12-15", travel_from="Nagpur")["guest"]
    S.guest_add(T, w["id"], "Anil Joshi", "groom", "9822012346", adults=3, invited=["lagna", "reception"], city="Pune")
    with pytest.raises(S.ShaadiError):
        S.guest_add(T, w["id"], "X", phone="12345")
    again = S.guest_add(T, w["id"], "Sunita Mehra ji", phone="9822012345", adults=3)        # same phone = same guest
    assert again["guest"]["id"] == g1["id"] and again["guest"]["heads"] == 4
    S.rsvp(T, w["id"], "Sunita", "haan")
    S.rsvp(T, w["id"], "Anil", "nahi", fn="reception")
    with pytest.raises(S.ShaadiError):
        S.rsvp(T, w["id"], "Anil", "yes", fn="haldi")                                      # not invited to haldi
    hc = {r["function"]: r for r in S.headcount(T, w["id"])["functions"]}
    assert hc["Lagna"]["yes"] == 4 and hc["Lagna"]["pending"] == 3 and hc["Reception"]["no"] == 3
    assert hc["Haldi"]["invited"] == 4 and hc["Lagna"]["diet_yes"] == {"veg": 4} and hc["Lagna"]["kids_yes"] == 1
    imp = S.guests_import(T, w["id"], data="Naam,Mobile,Taraf,Log\nRavi,9000000001,ladki,2\nMeena,98,ladka,1\n,,\n".encode(),
                          name="list.csv")
    assert imp["added"] == 1 and len(imp["problems"]) == 1
    assert S.guests(T, w["id"], q="Ravi")["guests"][0]["side"] == "bride"
    # rooms: overbooking refused in code, stay must fit the block
    rooms = S.room_add(T, w["id"], "Hotel Sai", "D", 4, "2026-12-12", "2026-12-15", count=2)["rooms"]
    assert [r["label"] for r in rooms] == ["D-1", "D-2"]
    ok = S.room_assign(T, w["id"], "Sunita", "D-1")
    assert ok["room"]["heads"] == 4
    with pytest.raises(S.ShaadiError) as e:
        S.room_assign(T, w["id"], "Anil", "D-1")
    assert "Overbooking" in str(e.value)
    S.guest_add(T, w["id"], "Ravi", phone="9000000001", arrive="2026-12-10", depart="2026-12-13")
    with pytest.raises(S.ShaadiError):
        S.room_assign(T, w["id"], "Ravi", "D-2")                                           # arrives before the block
    r = S.rooms(T, w["id"])
    assert r["free_beds"] == 4 and not r["waiting"]
    tl = S.travel_list(T, w["id"])
    assert tl["groups"][0]["from"] == "Nagpur" and tl["groups"][0]["heads"] == 4


def test_vendor_booking_fingerprint_stale_pay_budget(sh, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    S = sh
    w = _wedding(S)
    with pytest.raises(S.ShaadiError):
        S.vendor_add(T, w["id"], "Sharma Caterers", "caterer", schedule=[{"label": "Advance"}])     # amount never guessed
    v = S.vendor_add(T, w["id"], "Sharma Caterers", "caterer", "9811122233", ["lagna", "reception"], per_plate=650, plates=400,
                     quote_note="Veg thali, 2 sweets")["vendor"]
    assert v["quote"] == 260000
    with pytest.raises(S.ShaadiError):
        S.vendor_add(T, w["id"], vendor=v["id"], schedule=[{"label": "A", "amount": 200000}, {"label": "B", "amount": 100000}])
    S.vendor_add(T, w["id"], vendor=v["id"], schedule=[{"label": "Advance", "pct": 25, "due": "2026-10-30"},
                                                        {"label": "Shaadi ke din", "amount": 195000, "due": "2026-12-14"}])
    with pytest.raises(S.ShaadiError):
        S.book_request(T, w["id"], S.vendor_add(T, w["id"], "Phool wale", "florist")["vendor"]["id"])   # no quote -> no card
    card = S.book_request(T, w["id"], v["id"])
    c = card["card"]
    assert card["status"] == "needs_tap" and c["money"] and c["amount"] == 65000 and c["show"]["advance"]["label"] == "Advance"
    assert S.EVENTS[-1][0] == "shaadi_card"
    assert S.book_request(T, w["id"], v["id"]).get("existing")
    with pytest.raises(S.ShaadiError):
        S.decide(T, c["id"], True, c["hash"])                                             # the tool path never decides
    with pytest.raises(S.ShaadiError):
        S.decide(T, c["id"], True, "wrong", by_tap=True)
    from app import approvekey as ak
    phone = Phone("phone-1")
    ak.register(T, phone.device_id, phone.pub, "Pixel")
    with pytest.raises(S.ShaadiError) as e:
        S.decide(T, c["id"], True, c["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.challenge(T, c["id"])
    with pytest.raises(S.ShaadiError):
        S.decide(T, c["id"], True, c["hash"], proof=Phone("phone-1").sign(ch), by_tap=True)   # another key
    ch = S.challenge(T, c["id"])
    out = S.decide(T, c["id"], True, c["hash"], proof=phone.sign(ch), by_tap=True)
    assert out["card"]["status"] == "approved" and "wa.me/919811122233" in out["draft"]["wa"]
    vv = S.vendors(T, w["id"])["vendors"][0]
    assert vv["status"] == "booked" and vv["schedule"][0]["status"] == "approved"
    paid = S.mark_paid(T, w["id"], v["id"], "Advance", ref="UTR123456789")
    assert paid["vendor"]["paid"] == 65000 and paid["vendor"]["due"] == 195000
    with pytest.raises(S.ShaadiError):
        S.mark_paid(T, w["id"], v["id"], "Shaadi ke din")                                 # no Haan for that kist yet
    with pytest.raises(S.ShaadiError):
        S.mark_paid(T, w["id"], v["id"], actor="staff:s1")
    # payment card goes stale when the kist changes after the card
    pc = S.pay_request(T, w["id"], v["id"], "Shaadi ke din")["card"]
    S.vendor_add(T, w["id"], vendor=v["id"], schedule=[{"id": vv["schedule"][0]["id"], "label": "Advance", "amount": 65000},
                                                        {"id": vv["schedule"][1]["id"], "label": "Shaadi ke din", "amount": 190000}])
    with pytest.raises(S.ShaadiError) as e:
        S.decide(T, pc["id"], True, pc["hash"], by_tap=True)
    assert "badal" in str(e.value)
    assert S.cards(T, w["id"], "stale")
    # spend card + budget
    sp = S.spend_request(T, w["id"], "Mandap ke phool", "18,000", "florist", "lagna")["card"]
    ch = S.challenge(T, sp["id"])
    S.decide(T, sp["id"], True, sp["hash"], proof=phone.sign(ch), by_tap=True)
    S.budget_set(T, w["id"], 200000, "caterer", "lagna")
    b = S.budget(T, w["id"])
    lagna_cat = [r for r in b["rows"] if r["function"] == "Lagna" and r["head"] == "caterer"][0]
    assert lagna_cat["committed"] == 130000 and lagna_cat["paid"] == 32500 and lagna_cat["planned"] == 200000
    assert b["committed"] == 278000 and b["planned_total"] == 2500000
    with pytest.raises(S.ShaadiError):
        S.spend_request(T, w["id"], "dahej ka saamaan", 50000)


def test_messages_client_quote_and_dowry_gift_register(sh):
    S = sh
    w = _wedding(S)
    S.guest_add(T, w["id"], "Sunita Mehra", "bride", "9822012345")
    S.guest_add(T, w["id"], "Mama ji", "bride", "9822012399", no_messages=True)
    S.guest_add(T, w["id"], "No Phone", "groom")
    # invite text from real facts only; missing time / host stay blanks and block sending
    t = S.invite_text(T, w["id"], fn="lagna")
    assert "[samay]" in t["blanks"] and "Priya Kulkarni" in t["text"]
    with pytest.raises(S.ShaadiError):
        S.message_request(T, w["id"], fn="lagna")
    S.fn_set(T, w["id"], "lagna", start="11 am")
    m = S.message_request(T, w["id"], text="Namaste {name} ji, Lagna 14 Dec 11 baje Shubh Lawns. - Kulkarni parivaar", fn="lagna")
    c = m["card"]
    assert c["show"]["count"] == 1 and any("message nahi chahte" in x for x in c["show"]["skipped"]) and not c["money"]
    out = S.decide(T, c["id"], True, c["hash"], by_tap=True)
    assert len(out["links"]) == 1 and "Namaste%20Sunita%20ji" in out["links"][0]["wa"]
    # client quote: agency mode only, no invented fee
    with pytest.raises(S.ShaadiError):
        S.quote_request(T, w["id"])
    S.save_settings(T, mode="agency", firm="Shubh Vivah Planners", fee_mode="percent", fee_value=10, gstin="27AAPFU0939F1ZV",
                    upi_id="shubh@okhdfc")
    with pytest.raises(S.ShaadiError):
        S.quote_request(T, w["id"])                                                       # no client yet
    S.wedding_update(T, w["id"], client="Kulkarni parivaar", client_phone="9876543210")
    with pytest.raises(S.ShaadiError):
        S.quote_request(T, w["id"], lines=[{"name": "Decor package"}])                    # line without an amount
    q = S.quote_request(T, w["id"], lines=[{"name": "Haldi decor package", "amount": 40000}])["card"]
    assert q["show"]["fee"] == 250000 and q["show"]["gst"] == r(290000 * 0.18) and q["show"]["total"] == 342200
    assert sum(x["amount"] for x in q["show"]["stages"]) == 342200
    d = S.decide(T, q["id"], True, q["hash"], by_tap=True)
    assert d["file_id"] and S.STORED[-1][1].startswith(b"%PDF") and "wa.me/919876543210" in d["draft"]["wa"]
    cp = S.client_pay_request(T, w["id"], 0)["card"]
    d2 = S.decide(T, cp["id"], True, cp["hash"], by_tap=True)
    assert "upi://pay?pa=shubh%40okhdfc" in d2["upi"] and "am=102660.00" in d2["upi"]
    # shagun register: owner only, masked in the chat view, cash warning, dowry refused, Dowry Rules list PDF
    with pytest.raises(S.ShaadiError):
        S.gift_add(T, w["id"], "Sunita Mehra", 5100, actor="staff:s1")
    with pytest.raises(S.ShaadiError):
        S.gift_add(T, w["id"], "X", 100000, what="dahej")
    S.gift_add(T, w["id"], "Sunita Mehra", 5100, relation="Maushi", side="bride", for_whom="bride")
    g = S.gift_add(T, w["id"], "Ramesh Patil", 200000, relation="Kaka")
    assert g["warnings"] and "269ST" in g["warnings"][0]
    S.gift_add(T, w["id"], "Asha Joshi", 45000, kind="gold", what="Sone ki chain", relation="Nani", for_whom="groom")
    masked = S.gifts(T, w["id"])
    assert masked["total"] == 250100 and {x["giver"] for x in masked["gifts"]} == {"Sunita M.", "Ramesh P.", "Asha J."}
    assert S.gifts(T, w["id"], full=True)["gifts"][0]["giver"] == "Sunita Mehra"
    pdf = S.gift_list_pdf(T, w["id"], "bride")
    assert pdf.startswith(b"%PDF")
    assert S.gift_list_file(T, w["id"], "groom")["file_id"] and S.STORED[-1][0] == "presents_list_groom.pdf"
    with pytest.raises(S.ShaadiError):
        S.gift_list_file(T, w["id"], actor="staff:s1")
    reg = S.registration(T, w["id"])
    assert "Hindu Marriage Act" in reg["law"] and "90 din" in reg["state_note"] and reg["by"] == "2027-03-14"


def r(v):
    return round(v + 1e-9, 2)


def test_trip_forget_tick_tools_api(sh, monkeypatch):
    S = sh
    w = _wedding(S)
    S.guest_add(T, w["id"], "Sunita Mehra", "bride", "9822012345", travel_from="Nagpur", arrive="2026-12-12")
    calls = []
    from app.travel import service as TS
    monkeypatch.setattr(TS, "new_trip", lambda tenant, **kw: calls.append(kw) or {"trip": {"id": "tt1", "number": "T-0001"}})
    with pytest.raises(S.ShaadiError):
        S.to_trip(T, w["id"], "Nagpur", actor="staff:s1")
    out = S.to_trip(T, w["id"], "Nagpur")
    assert calls[0]["travellers"] == [{"name": "Sunita Mehra"}] and calls[0]["start_date"] == "2026-12-12"
    assert out["trip"]["number"] == "T-0001" and S.guests(T, w["id"])["guests"][0]["travel"]["trip"] == "tt1"
    with pytest.raises(S.ShaadiError):
        S.forget(T, w["id"])                                                              # only after done / cancelled
    # worker: tomorrow's function + checklist + payment due + morning note, once each
    S.vendor_add(T, w["id"], "Rang Decor", "decor", quote=90000, schedule=[{"label": "Advance", "amount": 20000, "due": "2026-12-09"}])
    from app.shaadi.models import ShaadiVendor
    from app.db import session
    with session() as s:
        for v in s.query(ShaadiVendor).all():
            v.status = "booked"
    S.EVENTS.clear()
    monkeypatch.setattr(S, "today", lambda tenant: date(2026, 12, 9))
    when = datetime(2026, 12, 9, 4, 0, tzinfo=timezone.utc)                              # 9:30 am IST
    res = S.tick(when)
    kinds = [k for k, _ in S.EVENTS]
    assert res["alerts"] >= 2 and "shaadi_alert" in kinds and "shaadi_day" in kinds
    assert any("Kal" in p["say"] for k, p in S.EVENTS if k == "shaadi_alert")
    S.EVENTS.clear()
    assert S.tick(when)["alerts"] == 0 and not S.EVENTS
    S.wedding_update(T, w["id"], status="done")
    f = S.forget(T, w["id"])
    assert f["guests"] == 1 and S.guests(T, w["id"])["guests"][0]["name"] == "Mehmaan 1"

    # tools
    from app.agent.shaadi_tools import SHAADI_HANDLERS, SHAADI_TOOLS
    from app.agent.tools import ToolError
    assert {t["name"] for t in SHAADI_TOOLS} == {"shaadi", "shaadi_dekho"} == set(SHAADI_HANDLERS)
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(SHAADI_HANDLERS[tool](ctx, **a))  # noqa: E731
    w2 = run("shaadi", action="new", title="Ayesha weds Imran", community="muslim", bride="Ayesha", groom="Imran",
             dates={"nikah": "2027-01-20"})["wedding"]
    assert [f["name"] for f in w2["functions"]][-2:] == ["Nikah", "Walima"]
    run("shaadi", action="vendor", wedding=w2["id"], name="Qazi sahab", kind="pandit", quote=5100)
    assert run("shaadi", action="book", wedding=w2["id"], vendor="Qazi")["status"] == "needs_tap"
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(ToolError):
        asyncio.run(SHAADI_HANDLERS["shaadi"](staff, action="gift", wedding=w2["id"], giver="X", value=100))
    with pytest.raises(ToolError):
        asyncio.run(SHAADI_HANDLERS["shaadi_dekho"](staff, what="gifts", wedding=w2["id"]))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(SHAADI_HANDLERS["shaadi"](cust, action="guest", wedding=w2["id"], name="Z"))
    assert run("shaadi_dekho", what="registration", wedding=w2["id"])["law"].startswith("Nikahnama")
    assert run("shaadi_dekho", what="day")["waiting"]

    from app.shaadi.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/shaadi").status_code == 200
    card = S.cards(T, w2["id"], "waiting")[0]
    assert c.post(f"/api/shaadi/cards/{card['id']}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    rr = c.post(f"/api/shaadi/cards/{card['id']}/decide", json={"yes": True, "hash": card["hash"]})
    assert rr.status_code == 200 and rr.json()["card"]["status"] == "approved"
    assert c.post(f"/api/shaadi/weddings/{w2['id']}/guests/import", files={"file": ("g.csv", b"Name,Phone\nZara,9811100000\n", "text/csv")}).json()["added"] == 1
    assert c.post(f"/api/shaadi/weddings/{w2['id']}/gifts", json={"giver": "Zara Khan", "value": 2100}).status_code == 200
    assert c.get(f"/api/shaadi/weddings/{w2['id']}/gifts").json()["gifts"][0]["giver"] == "Zara Khan"
    assert c.get(f"/api/shaadi/weddings/{w2['id']}/gifts/list.pdf").content.startswith(b"%PDF")
    assert c.post("/api/shaadi/weddings", json={"bride": "A", "groom": "B", "age_groom": 19}).status_code == 400


def test_invite_design_goes_to_brand(sh, monkeypatch):
    S = sh
    w = _wedding(S)
    seen = []
    from app.brand import service as BS
    monkeypatch.setattr(BS, "make", lambda tenant, **kw: seen.append(kw) or {"design": {"id": "B-0001"}})
    out = S.invite_design(T, w["id"], "lagna")
    assert out["design"]["id"] == "B-0001" and "Priya Kulkarni" in seen[0]["brief"] and "khaali" in seen[0]["brief"]
