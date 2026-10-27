"""Event Sahayak: rules (kinds, heads, permits from facts, task plan, run-of-show parsing + Noise Rules check, RSVP words, money
words), event file + task plan + permissions, vendor quotes (never invented) + comparison + choice -> budget with margin, client
quotation with GST / pure agent and ONLY her tap with the card hash, vendor booking with advance needing her tap AND a real
fingerprint, venue double booking refused, spends, guests + RSVP + invite drafts on her tap, run of show + day timeline, report +
invoice draft (number only at her tap), DPDP forget, worker, tools (staff / customer actors) and API."""
import asyncio
import base64
from datetime import date, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.eventplan.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def ep(env, monkeypatch):
    from app.eventplan import service as S
    events, stored = [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    S.EVENTS, S.STORED = events, stored
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def _future(days=40) -> str:
    from app.eventplan import service as _S
    return (_S.today(T) + timedelta(days=days)).isoformat()   # her (IST) date, not the server's UTC date


def _setup(S, days=40):
    S.save_settings(T, firm="Utsav Events", gstin="27AAPFU0939F1ZV", margin_pct=15, head_margins={"venue": 5}, upi_id="utsav@okicici",
                    team=[{"name": "Riya", "phone": "9811111111", "role": "coordinator"}])
    e = S.event_save(T, "Acme dealer meet", client="Acme Pvt Ltd", client_phone="9822012345", client_state="27", day=_future(days),
                     start="18:00", end="22:30", venue="Lotus Banquet, Pune", headcount=200, budget=500000,
                     facts={"venue_kind": "hotel", "sound": True, "food": True, "music": True, "stage": True})["event"]
    S.vendor_save(T, "Lotus Banquet", "venue", "9000000001")
    S.vendor_save(T, "Annapurna Caterers", "catering", "9000000002", upi_id="annapurna@okhdfc", fssai="12345678901234")
    S.vendor_save(T, "Swaad Caterers", "catering", "9000000003")
    S.vendor_save(T, "Beat DJ", "sound", "9000000004")
    return e


def test_rules():
    from app.eventplan import rules as R
    assert R.kind_of("Annual day for Acme") == "corporate" and R.kind_of("Riya ka birthday") == "birthday"
    assert R.kind_of("tech fest at college") == "college_fest" and R.kind_of("auto expo stall") == "exhibition"
    assert R.head_of("DJ and sound") == "sound_light" and R.head_of("buffet dinner per plate") == "catering"
    p = R.permits_for({"venue_kind": "open", "sound": True, "food": True, "music": True, "alcohol": True, "headcount": 300})
    assert {"police", "loudspeaker", "fire", "fssai", "music", "liquor"} <= set(p)
    assert R.permits_for({"venue_kind": "hotel"}) == ["venue_noc"]
    plan = R.task_plan("conference", date(2026, 12, 20), date(2026, 10, 23))
    assert plan[0]["due"] == "2026-10-23"                                     # 90 days before is already past -> due now
    assert any(t["days_before"] < 0 for t in plan)
    cues, bad = R.parse_cues("18:30 Welcome by anchor (10 min) - Riya | stage\n7:00 pm Dinner music (120 min) - Beat DJ\nkuch bhi")
    assert cues[0]["time"] == "18:30" and cues[0]["who"] == "Riya" and cues[0]["where"] == "stage" and "mic" in cues[0]["av"]
    assert cues[1]["time"] == "19:00" and cues[1]["mins"] == 120 and "music" in cues[1]["av"] and bad == ["kuch bhi"]
    probs = R.cue_problems(cues + [{"time": "22:15", "mins": 30, "what": "DJ night", "who": "DJ", "av": ["music"]}])
    assert any("Noise Rules" in x for x in probs)
    assert any("takraav" in x for x in R.cue_problems([{"time": "18:00", "mins": 30, "what": "a", "who": "x", "av": []},
                                                       {"time": "18:15", "mins": 5, "what": "b", "who": "y", "av": []}]))
    assert R.rsvp_of("haan aa rahe hain +2") == ("yes", 2) and R.rsvp_of("nahi aa payenge")[0] == "no"
    assert R.rsvp_of("shayad aayenge")[0] == "maybe"
    assert R.num("1.5 lakh") == 150000 and R.num("25k") == 25000 and R.num("₹40,000") == 40000 and R.num("") is None
    assert R.gst_split(1000, 18, True)["cgst"] == 90 and R.gst_split(1000, 18, False)["igst"] == 180
    assert R.clean("OTP 123456 card 4111 1111 1111 1111") == "OTP [hataya] card [hataya]"


def test_event_tasks_permits_settings(ep):
    S = ep
    with pytest.raises(S.EventError):
        S.save_settings(T, sound_till="21:00")                               # sound limit only 22:00 .. midnight
    with pytest.raises(S.EventError):
        S.save_settings(T, gstin="27AAPFU0939F1ZX")
    e = _setup(S)
    assert e["number"] == "E-0001" and e["kind"] == "corporate"
    t = S.tasks(T, e["id"])
    assert len(t["tasks"]) >= 10 and t["no_owner"] == len(t["tasks"])
    pm = S.permits(T, e["id"])
    keys = {p["key"] for p in pm["permits"]}
    assert {"venue_noc", "loudspeaker", "fssai", "music", "structure"} <= keys and "police" not in keys
    assert all(p["apply_by"] for p in pm["permits"]) and "starter" in pm["note"]
    S.event_save(T, event=e["id"], facts={"alcohol": True})
    assert "liquor" in {p["key"] for p in S.permits(T, e["id"])["permits"]}
    S.permit_update(T, e["id"], "loudspeaker", "applied", ref="PS/123")
    assert next(p for p in S.permits(T, e["id"])["permits"] if p["key"] == "loudspeaker")["status"] == "applied"
    with pytest.raises(S.EventError):
        S.event_save(T, "Old", day="2020-01-01")
    with pytest.raises(S.EventError):
        S.event_save(T, event=e["id"], status="confirmed", actor="staff:s1")


def test_vendor_quotes_compare_budget_quote_and_her_tap(ep):
    S = ep
    e = _setup(S)
    with pytest.raises(S.EventError):
        S.vquote_add(T, e["id"], "Annapurna", None)                          # no price = refused, never guessed
    q1 = S.vquote_add(T, e["id"], "Annapurna", 650, "catering", "Veg buffet", gst_included=False, gst_pct=5, per="plate",
                      advance_pct=30, cancel_terms="7 din pehle tak 50% wapas", includes="2 starters, 4 main")["quote"]
    assert q1["qty"] == 200 and q1["base"] == 130000 and q1["gst"] == 6500
    q2 = S.vquote_add(T, e["id"], "Swaad", 120000, "catering", "Veg buffet 200 plates")["quote"]
    assert "GST" in q2["note"]
    S.vquote_add(T, e["id"], "Lotus Banquet", 80000, "venue", "Hall 6-11 pm", gst_included=True, gst_pct=18)
    c = S.compare(T, e["id"], "catering")
    qs = c["heads"][0]["quotes"]
    assert qs[0]["vendor"] == "Annapurna Caterers" and qs[0].get("tag")      # only priced-with-GST one is tagged cheapest
    assert "GST saaf nahi" in qs[1]["missing"] and "advance kitna" in qs[1]["missing"]
    S.choose_quote(T, q1["id"])
    lq = [x for x in S.compare(T, e["id"], "venue")["heads"][0]["quotes"]][0]
    b = S.choose_quote(T, lq["id"])["budget"]
    assert b["cost"] == pytest.approx(130000 + 80000 / 1.18, abs=0.02)
    b = S.budget_set(T, e["id"], [{"head": "decor", "item": "Stage backdrop"}, {"head": "permissions", "item": "PPL licence", "cost": 5000,
                                                                               "pure_agent": True}])
    assert len(b["blanks"]) == 1 and "Stage backdrop" in b["blanks"][0]
    q = S.quote_make(T, e["id"])["doc"]
    assert q["blanks"]
    with pytest.raises(S.EventError):
        S.doc_request(T, q["id"])                                             # blanks first
    line = next(x for x in b["lines"] if x["item"] == "Stage backdrop")
    S.budget_set(T, e["id"], [{"id": line["id"], "head": "decor", "item": "Stage backdrop", "cost": 40000}])
    q2 = S.quote_make(T, e["id"])["doc"]
    assert q2["number"] == "EQ-0001/R2" and not q2["blanks"] and S.doc_view(T, q["id"])["status"] == "superseded"
    t = q2["totals"]
    venue_base = 80000 / 1.18
    taxable = 130000 * 1.15 + venue_base * 1.05 + 40000 * 1.15
    assert t["taxable"] == pytest.approx(taxable, abs=0.05) and t["pure_agent"] == 5000 and t["intra"]
    assert t["total"] == pytest.approx(taxable * 1.18 + 5000, abs=0.1)
    assert S.doc_pdf(T, q2["id"]).startswith(b"%PDF")
    card = S.doc_request(T, q2["id"])
    assert card["status"] == "needs_tap" and "eventplan_doc" in kinds(S)
    with pytest.raises(S.EventError):
        S.decide_doc(T, q2["id"], True, card["doc"]["hash"])                 # the tool path never decides
    with pytest.raises(S.EventError):
        S.decide_doc(T, q2["id"], True, "bad", by_tap=True)
    with pytest.raises(S.EventError):
        S.doc_mark(T, q2["id"], "sent")
    out = S.decide_doc(T, q2["id"], True, card["doc"]["hash"], by_tap=True)
    assert out["doc"]["status"] == "approved" and "wa.me/919822012345" in out["draft"]["wa"] and S.STORED[-1][0].endswith("_quote.pdf")
    with pytest.raises(S.EventError):
        S.doc_mark(T, q2["id"], "accepted", actor="staff:s1")
    S.doc_mark(T, q2["id"], "accepted")
    assert S.event_view(T, e["id"])["status"] == "confirmed"
    with pytest.raises(S.EventError):
        S.quote_make(T, e["id"])


class Phone:
    def __init__(self, device_id):
        self.device_id = device_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def sign(self, ch):
        sig = self.key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))
        return {"challenge_id": ch["challenge_id"], "device_id": self.device_id, "signature": base64.b64encode(sig).decode()}


def test_booking_needs_her_tap_fingerprint_and_no_double_booking(ep, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    S = ep
    e = _setup(S)
    q = S.vquote_add(T, e["id"], "Annapurna", 650, "catering", "Veg buffet", gst_included=False, gst_pct=5, per="plate", advance_pct=30)["quote"]
    with pytest.raises(S.EventError):
        S.booking_request(T, e["id"], vendor="Beat DJ")                       # no quote, no amount = refused
    bk = S.booking_request(T, e["id"], quote=q["id"], arrive="16:00", advance_due=_future(10))
    b = bk["booking"]
    assert bk["status"] == "needs_tap" and b["amount"] == 136500 and b["advance"] == pytest.approx(40950)
    assert any("Client ne abhi" in c for c in b["checks"]) and "eventplan_booking" in kinds(S)
    assert S.booking_request(T, e["id"], quote=q["id"]).get("existing")
    with pytest.raises(S.EventError):
        S.decide_booking(T, b["id"], True, b["hash"])
    from app import approvekey as ak
    phone = Phone("phone-1")
    ak.register(T, phone.device_id, phone.pub, "Pixel")
    with pytest.raises(S.EventError) as ex:
        S.decide_booking(T, b["id"], True, b["hash"], by_tap=True)
    assert str(ex.value) == "fingerprint_needed"
    ch = S.booking_challenge(T, b["id"])
    with pytest.raises(S.EventError):
        S.decide_booking(T, b["id"], True, b["hash"], proof=Phone("phone-1").sign(ch), by_tap=True)
    ch = S.booking_challenge(T, b["id"])
    out = S.decide_booking(T, b["id"], True, b["hash"], proof=phone.sign(ch), by_tap=True)
    assert out["booking"]["status"] == "approved" and out["draft"]["upi"].startswith("upi://pay?pa=annapurna%40okhdfc")
    assert "16:00" in out["draft"]["text"] and "wa.me/919000000002" in out["draft"]["wa"]
    with pytest.raises(S.EventError):
        S.booking_paid(T, b["id"], actor="staff:s1")
    assert S.booking_paid(T, b["id"], 40950, "UTR 99")["booking"]["status"] == "advance_paid"
    # venue on the same day for another event -> refused
    vb = S.booking_request(T, e["id"], vendor="Lotus Banquet", amount=80000)["booking"]
    S.decide_booking(T, vb["id"], True, vb["hash"], by_tap=True)              # no advance -> no fingerprint needed
    e2 = S.event_save(T, "Sharma birthday", day=e["day"], client="Sharma")["event"]
    with pytest.raises(S.EventError) as ex:
        S.booking_request(T, e2["id"], vendor="Lotus Banquet", amount=50000)
    assert "double booking" in str(ex.value)
    tl = S.show(T, e["id"])["timeline"]
    assert any(x.get("kind") == "arrival" and x["time"] == "16:00" for x in tl)
    # spends: card, fingerprint, paid
    sp = S.spend_request(T, e["id"], "Police permission fee", 2000, "Police station", "permissions")
    assert sp["status"] == "needs_tap" and any("budget mein nahi" in c for c in sp["spend"]["checks"])
    with pytest.raises(S.EventError):
        S.decide_spend(T, sp["spend"]["id"], True, sp["spend"]["hash"], by_tap=True)
    ch = S.spend_challenge(T, sp["spend"]["id"])
    S.decide_spend(T, sp["spend"]["id"], True, sp["spend"]["hash"], proof=phone.sign(ch), by_tap=True)
    assert S.spend_paid(T, sp["spend"]["id"], "rcpt 1")["spend"]["status"] == "paid"
    assert S.budget(T, e["id"])["actual"] == pytest.approx(136500 + 80000 + 2000)


def test_guests_rsvp_invites_show_report_invoice_forget_tick(ep, monkeypatch):
    S = ep
    e = _setup(S, days=1)
    S.guests_add(T, e["id"], text="Rahul Sharma 9876543210, office\nPriya, family\nAmit 98765 43211")
    S.guests_add(T, e["id"], data=b"Name,Mobile,Group\nNeha,9876500000,office\nRahul Sharma,9876543210,office\n", name="g.csv")
    g = S.guests(T, e["id"])
    assert g["summary"]["total"] == 4
    S.guest_optout(T, e["id"], "Amit")
    m = S.message_request(T, e["id"], "invite")
    assert m["message"]["count"] == 2 and "eventplan_message" in kinds(S)     # Priya has no phone, Amit said no
    with pytest.raises(S.EventError):
        S.decide_message(T, m["message"]["id"], True, m["message"]["hash"])
    d = S.decide_message(T, m["message"]["id"], True, m["message"]["hash"], by_tap=True)
    assert len(d["links"]) == 2 and "Rahul Sharma ji" in d["links"][0]["text"] + d["links"][1]["text"]
    assert S.guests(T, e["id"])["summary"]["invited"] == 2
    with pytest.raises(S.EventError):
        S.message_request(T, e["id"], "invite")                               # everyone with a phone already invited
    with pytest.raises(S.EventError):
        S.message_request(T, e["id"], "custom", text="Aaiye [samay?] par")    # blanks never go
    S.rsvp(T, e["id"], "Rahul", "haan aa rahe hain +2")
    S.rsvp(T, e["id"], "Neha", "nahi aa payenge")
    sm = S.guests(T, e["id"])["summary"]
    assert sm["yes"] == 1 and sm["heads_yes"] == 3 and sm["no"] == 1
    v = S.show_set(T, e["id"], "18:00 Guests arrive - Riya | gate\n18:30 Welcome speech (10 min) - Anchor | stage\n22:15 DJ night (60 min) - Beat DJ")
    assert len(v["cues"]) == 3 and any("Noise Rules" in p for p in v["problems"])
    assert S.show_pdf(T, e["id"]).startswith(b"%PDF")
    with pytest.raises(S.EventError):
        S.report(T, e["id"])                                                  # event is tomorrow
    with pytest.raises(S.EventError):
        S.invoice_make(T, e["id"])
    # the event happens: move the clock two days ahead
    later = datetime.now(timezone.utc) + timedelta(days=2)
    monkeypatch.setattr(S, "clock", lambda: later)
    S.budget_set(T, e["id"], [{"head": "catering", "item": "Buffet", "cost": 100000}])
    S.client_paid(T, e["id"], 50000, "NEFT 1")
    rep = S.report(T, e["id"], attended=180, issues=["Mic 10 min band"])
    assert rep["report"]["attended"] == 180 and S.STORED[-1][0].endswith("_report.pdf")
    inv = S.invoice_make(T, e["id"])["doc"]
    assert inv["kind"] == "invoice" and inv["number"].startswith("(") and inv["totals"]["balance"] == pytest.approx(100000 * 1.15 * 1.18 - 50000, abs=0.05)
    c = S.doc_request(T, inv["id"])
    out = S.decide_doc(T, inv["id"], True, c["doc"]["hash"], by_tap=True)
    assert out["doc"]["number"].startswith("EI/") and out["draft"]["upi"].startswith("upi://pay?pa=utsav%40okicici")
    with pytest.raises(S.EventError):
        S.forget(T, e["id"], actor="staff:s1")
    f = S.forget(T, e["id"])
    assert "4 mehmaan" in f["say"] and S.guests(T, e["id"])["summary"]["total"] == 0
    assert S.event_view(T, e["id"])["client"] == "Client (hataya)"


def test_tick_once_each(ep, monkeypatch):
    S = ep
    e = _setup(S, days=1)
    _d = S.today(T)
    when = datetime(_d.year, _d.month, _d.day, 4, 0, tzinfo=timezone.utc)     # 9:30 am IST on her day
    monkeypatch.setattr(S, "clock", lambda: when)
    o1 = S.tick(when)
    o2 = S.tick(when)
    assert o1["alerts"] >= 1 and o2["alerts"] == 0 and o1["morning"] == 1 and o2["morning"] == 0
    assert "eventplan_alert" in kinds(S) and "eventplan_day" in kinds(S)
    assert any("Kal" in p["say"] for k, p in S.EVENTS if k == "eventplan_alert")
    assert S.day(T)["upcoming"]


def test_tools_actors_and_api(ep):
    S = ep
    from app.agent.eventplan_tools import EVENTPLAN_HANDLERS, EVENTPLAN_TOOLS
    from app.agent.tools import ToolError
    assert {t["name"] for t in EVENTPLAN_TOOLS} == {"event_plan", "event_plan_dekho"} == set(EVENTPLAN_HANDLERS)
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(EVENTPLAN_HANDLERS[tool](ctx, **a))  # noqa: E731
    run("event_plan", action="settings", firm="Utsav", margin_pct=10)
    ev = run("event_plan", action="event", name="Product launch X", client="X Ltd", client_phone="9811122233", day=_future(20))["event"]
    run("event_plan", action="vendor", name="Beat DJ", head="sound", phone="9000000004")
    q = run("event_plan", action="vquote", event=ev["id"], vendor="Beat DJ", amount=25000, gst_included=False, gst_pct=18)["quote"]
    run("event_plan", action="choose", quote=q["id"])
    d = run("event_plan", action="quote", event=ev["number"])["doc"]
    sent = run("event_plan", action="doc_send", doc=d["id"])
    assert sent["status"] == "needs_tap"
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(ToolError):
        asyncio.run(EVENTPLAN_HANDLERS["event_plan"](staff, action="settings", firm="Y"))
    with pytest.raises(ToolError):
        asyncio.run(EVENTPLAN_HANDLERS["event_plan"](staff, action="client_paid", event=ev["id"], amount=10))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(EVENTPLAN_HANDLERS["event_plan"](cust, action="event", name="x"))
    assert run("event_plan_dekho", what="day")["waiting"]["docs"]
    assert run("event_plan_dekho", what="event", event="Product launch X")["budget"]["cost"] == 25000

    from app.eventplan.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/eventplan").status_code == 200
    assert c.post(f"/api/eventplan/docs/{d['id']}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    r = c.post(f"/api/eventplan/docs/{d['id']}/decide", json={"yes": True, "hash": sent["doc"]["hash"]})
    assert r.status_code == 200 and r.json()["doc"]["status"] == "approved"
    assert c.get(f"/api/eventplan/docs/{d['id']}/pdf").content.startswith(b"%PDF")
    imp = c.post(f"/api/eventplan/events/{ev['id']}/guests/import", files={"file": ("g.csv", b"Name,Phone\nA,9876543210\n", "text/csv")})
    assert imp.status_code == 200 and imp.json()["added"] == 1
    bk = c.post(f"/api/eventplan/events/{ev['id']}/bookings", json={"vendor": "Beat DJ", "advance": 5000}).json()["booking"]
    assert c.post(f"/api/eventplan/bookings/{bk['id']}/decide", json={"yes": True, "hash": bk["hash"]}).status_code == 200
    assert c.put("/api/eventplan/settings", json={"fee_mode": "bad"}).status_code == 400
