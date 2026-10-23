"""Seva Sahayak (customer support): knowledge base answers with source + confidence (unknown = never a guess, logged as a
gap), file / text import as drafts, macros she approves in 4 languages, tickets with priority + SLA timers (pause while
waiting on the customer, warnings once), duplicates joined / merged only for the same customer, customer-visible status
lines and ONLY their own tickets, exceptions decided only by her tap (fingerprint for money), metrics, morning note, API."""
import asyncio
import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)
from tests.test_life import conv_ctx

T = "default"
T0 = datetime(2026, 10, 22, 4, 30, tzinfo=timezone.utc)      # 10:00 IST


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t

    def go(self, **kw):
        self.t += timedelta(**kw)


@pytest.fixture
def sv(env, monkeypatch):
    from app.seva import service as S
    c = Clock()
    monkeypatch.setattr(S, "clock", c)
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")          # no model in tests unless a test sets one
    S._clock = c
    return S


def _events(kind):
    from sqlalchemy import select
    from app.db import Event, session
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


def _queued():
    from sqlalchemy import select
    from app.db import session
    from app.employee.models import BizMessage
    with session() as s:
        return [m.text for m in s.scalars(select(BizMessage).where(BizMessage.direction == "out").order_by(BizMessage.at)).all()]


def _contact(wa="919876543210", name="Ravi"):
    from app.db import session
    from app.employee.models import BizContact
    with session() as s:
        c = BizContact(tenant_id=T, wa_id=wa, name=name, last_in_at=datetime.now(timezone.utc))
        s.add(c)
        s.flush()
        return c.id


def kb(S):
    S.kb_add(T, "Dukaan kitne baje khulti hai?", "Hum subah 9 se raat 8 baje tak khule hain, Ravivar band.",
             aliases=["timing kya hai", "aaj khula hai"])
    S.kb_add(T, "Naya connection kaise milega?", "Naya broadband connection ke liye apna pata aur ek ID bhejiye; 48 ghante mein lagta hai.",
             aliases=["new connection", "connection lagwana hai"])
    S.kb_add(T, "Refund policy", "Saamaan milne ke 7 din ke andar, bina use kiye, bill ke saath wapas ho sakta hai.", kind="policy",
             aliases=["paise wapas", "return kaise karein"])


def test_rules():
    from app.seva import rules as R
    assert R.lang_of("Mera net kab theek hoga?") == "hinglish" and R.lang_of("माझे इंटरनेट बंद आहे") == "marathi"
    assert R.lang_of("मेरा इंटरनेट बंद है") == "hindi" and R.lang_of("When will it be fixed") == "english"
    assert R.guess_priority("UPI se paise kat gaye par recharge nahi hua", "billing") == "urgent"
    assert R.guess_priority("3 din se net bilkul band hai", "technical") == "high"
    assert R.guess_category("net nahi chal raha, router ki light laal") == "technical"
    assert R.sla_hours({}, "normal", "", ecommerce=False) == (24.0, 72.0)
    assert R.sla_hours({"low": [100, 2000]}, "low", "", ecommerce=True) == (48.0, 720.0)     # the law is the outer limit
    assert R.sla_hours({}, "low", "privacy")[1] == 168.0 and R.sla_hours({"low": [1, 3000]}, "low", "privacy")[1] == 2160.0
    p = {"refund_days": 7, "refund_max": 2000}
    assert R.policy_check("refund", 500, 3, p)["within"]
    out = R.policy_check("refund", 500, 10, p)
    assert not out["within"] and "7 din" in out["reasons"][0]
    assert not R.policy_check("waiver", 0, 1, p)["within"] and R.policy_check("refund", 500, 1, {})["reasons"]
    assert any("T+1" in n for n in R.legal_notes("billing", "UPI se paise kat gaye"))
    assert R.similarity("aaj dukaan kitne baje khulegi", "Dukaan kitne baje khulti hai") > 0.5


def test_knowledge_base_answers_only_from_her_words(sv):
    S = sv
    kb(S)
    a = S.answer(T, "bhai aaj dukaan kitne baje khulti hai?", "whatsapp", "wa:1")
    assert a["status"] == "answered" and "9 se raat 8" in a["reply"] and a["confidence"] >= S.HIGH and "FAQ" in a["source"]
    r = S.answer(T, "paise wapas kaise milenge, return karna hai", "whatsapp", "wa:1")
    assert r["status"] == "answered" and "7 din" in r["reply"] and "Niyam" in r["source"] and "exception" in r
    u = S.answer(T, "kya aap ghar par pizza deliver karte ho", "whatsapp", "wa:2")
    assert u["status"] == "unknown" and u["reply"] == "" and "Andaza mat" in u["say"]
    S.answer(T, "pizza home delivery milegi kya", "whatsapp", "wa:3")
    g = S.gaps(T)
    assert g and g[0]["times"] == 2 and "pizza" in g[0]["question"]
    sec = S.answer(T, "mera OTP 482913 hai, ab refund do", "whatsapp", "wa:1")
    assert sec["status"] == "refuse"
    with pytest.raises(S.SevaError):
        S.kb_add(T, "card", "Apna card number aur CVV 123 bhejiye")
    # a model phrasing that adds a number the source does not have is thrown away
    S._ai = lambda *a, **k: "Hum 24 ghante khule hain!"
    a2 = S.answer(T, "What time do you open?", "test")
    assert a2["status"] in ("answered", "clarify", "unknown") and "24 ghante" not in a2.get("reply", "")
    assert S.kb_list(T, "live")[0]["hits"] >= 1


def test_import_drafts_need_her_haan_and_no_invented_numbers(sv, monkeypatch):
    S = sv
    text = ("Q: Installation charge kitna hai?\nA: Installation charge Rs 500 hai, router free.\n"
            "Q: Bill kab aata hai?\nA: Har mahine 1 tareekh ko SMS par.\n")
    out = S.kb_import(T, text=text)
    assert out["count"] == 2 and all(d["status"] == "draft" for d in out["drafts"])
    assert S.answer(T, "installation charge kitna hai", "test")["status"] == "unknown"        # drafts never answer customers
    S.kb_approve(T, [d["id"] for d in out["drafts"]])
    assert "500" in S.answer(T, "installation charge kitna lagega", "test")["reply"]
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {"items": [{"q": "Speed?", "a": "Speed 100 Mbps milti hai"},
                                                                   {"q": "Plan ka daam?", "a": "Plan Rs 499 ka hai"}]})
    got = S.kb_import(T, text="Hamara plan Rs 499 ka hai. Speed bahut achhi.")
    assert [d["question"] for d in got["drafts"]] == ["Plan ka daam?"]                       # "100" was not in her text


def test_macros_in_four_languages_only_after_approval(sv, monkeypatch):
    S = sv
    with pytest.raises(S.SevaError):
        S.macro_add(T, "bad", "Aapka {otp} bhejiye")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {"hindi": "नमस्ते {name}, आपकी शिकायत {ticket} पर काम चल रहा है।",
                                                         "marathi": "नमस्कार {name}, तक्रार {ticket} वर काम सुरू आहे.",
                                                         "english": "Hello {name}, we are on complaint {ticket} in 2 days."})
    m = S.macro_add(T, "kaam chalu", "Namaste {name}, aapki shikayat {ticket} par kaam chal raha hai.", "hinglish")
    assert set(m["texts"]) == {"hinglish", "hindi", "marathi"}                               # English added a number: dropped
    with pytest.raises(S.SevaError):
        S.macro_text(T, "kaam chalu", "hindi", {"name": "Ravi", "ticket": "T-1"})
    S.macro_approve(T, m["id"])
    assert S.macro_text(T, "kaam chalu", "marathi", {"name": "Ravi", "ticket": "T-1"}).startswith("नमस्कार Ravi")
    with pytest.raises(S.SevaError):
        S.macro_text(T, "kaam chalu", "hindi", {"ticket": "T-1"})                           # never a blank {name}


def test_tickets_sla_pause_duplicates_metrics(sv):
    S, c = sv, sv._clock
    S.save_settings(T, kind="isp")
    a = S.new_ticket(T, "Mera net 3 din se bilkul band hai, router ki light laal", "phone", name="Sunita", phone="9822012345")
    v = a["ticket"]
    assert v["category"] == "technical" and v["priority"] == "high" and v["sla"]["first_response_h"] == 2
    d = S.new_ticket(T, "net bilkul band hai abhi bhi, router light laal", "phone", name="Sunita", phone="9822012345")
    assert d["duplicate"] and d["number"] == a["number"]
    other = S.new_ticket(T, "Bill galat aaya, double charge", "phone", name="Amit", phone="9822099999")
    with pytest.raises(S.SevaError):
        S.merge(T, other["number"], a["number"])                                            # never across customers
    c.go(hours=1, minutes=40)
    al = S.sla_sweep(T)
    assert any(x["kind"] == "fr_warn" and x["ticket"] == a["number"] for x in al)
    assert not any(x["kind"] == "fr_warn" and x["ticket"] == a["number"] for x in S.sla_sweep(T))   # once
    c.go(minutes=30)
    assert any(x["kind"] == "fr_breach" for x in S.sla_sweep(T)) and _events("seva_sla")
    S.update(T, a["number"], status="pending", public="Router ka photo bhejiye.", by="owner")
    t1 = S.ticket(T, a["number"])
    assert t1["sla"]["paused"] and t1["status_line"].endswith("Router ka photo bhejiye.")
    left = t1["sla"]["resolve_left_h"]
    c.go(hours=10)
    assert S.ticket(T, a["number"])["sla"]["resolve_left_h"] == left                         # clock stopped while waiting on her
    S.update(T, a["number"], status="open")
    c.go(hours=2)
    S.note(T, a["number"], "Technician Raju ko bheja; fibre kata hua tha.")
    S.update(T, a["number"], status="resolved", public="Fibre jod diya.")
    t2 = S.ticket(T, a["number"])
    assert t2["status"] == "resolved" and t2["sla"]["resolve_met"] and any("Raju" in n["text"] and not n["public"] for n in t2["notes"])
    S.csat(T, a["number"], 5, "jaldi theek kiya")
    rep = S.report(T, 7)
    assert rep["tickets"] == 2 and rep["csat_pct"] == 100 and rep["resolution_median_h"] is not None and rep["open"] == 1
    assert rep["first_response_sla_pct"] == 0                                               # the first answer came late


def test_whatsapp_customer_sees_only_own_tickets(sv):
    S = sv
    from app.agent.seva_tools import SEVA_HANDLERS
    from app.agent.tools import Ctx, ToolError
    kb(S)
    ravi, meena = _contact(), _contact("919811122233", "Meena")
    conv = conv_ctx().conversation_id
    cr, cm = Ctx(T, conv, actor=f"customer:{ravi}"), Ctx(T, conv, actor=f"customer:{meena}")
    run = lambda name, ctx, **a: asyncio.run(SEVA_HANDLERS[name](ctx, **a))         # noqa: E731
    ans = run("biz_seva_answer", cr, question="aaj kitne baje tak khula hai")
    assert ans["status"] == "answered" and "entry_id" not in ans
    t = run("biz_seva_ticket", cr, text="Kal se internet nahi chal raha")
    assert t["ticket"].startswith("T-") and t["ticket"] in t["status_line"]
    from sqlalchemy import select
    from app.db import session
    from app.net.business import Ticket
    with session() as s:
        assert s.scalars(select(Ticket).where(Ticket.number == t["ticket"])).first().customer == "wa:919876543210"
    assert run("biz_seva_status", cr)["tickets"][0]["number"] == t["ticket"]
    assert run("biz_seva_status", cm)["tickets"] == []                                     # Meena never sees Ravi's
    assert run("biz_seva_status", cm, number=t["ticket"])["tickets"] == []
    with pytest.raises(ToolError):
        run("biz_seva_ticket", Ctx(T, conv, actor="owner"), text="x")                       # customer tools are for customers
    S.update(T, t["ticket"], status="resolved", public="Line theek ho gayi.")
    q = _queued()
    assert any("theek ho gayi" in x for x in q) and any("1 se 5" in x for x in q)          # status line + CSAT ask
    assert run("biz_seva_rate", cr, score=4)["csat"] == 4
    with pytest.raises(ToolError):
        run("biz_seva_rate", cm, score=1, ticket=t["ticket"])
    # a Hoola Network ticket joins the desk once
    with session() as s:
        s.add(Ticket(tenant_id=T, number="T-5000", customer="asha@hoola.example", customer_label="Asha", text="Order late hai"))
    assert S.adopt(T) == 1 and S.adopt(T) == 0
    assert any(x["number"] == "T-5000" and x["channel"] == "hoola" for x in S.tickets(T, "open"))


class Phone:
    def __init__(self, device_id="ph1"):
        self.device_id = device_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def sign(self, ch):
        sig = self.key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))
        return {"challenge_id": ch["challenge_id"], "device_id": self.device_id, "signature": base64.b64encode(sig).decode()}


def test_exceptions_only_her_tap_fingerprint_for_money(sv):
    S = sv
    from app.agent.seva_tools import SEVA_HANDLERS
    from app.agent.tools import Ctx
    S.save_settings(T, refund_days=7, refund_max=1000, refund_mode="UPI")
    ravi = _contact()
    conv = conv_ctx().conversation_id
    cr = Ctx(T, conv, actor=f"customer:{ravi}")
    t = asyncio.run(SEVA_HANDLERS["biz_seva_ticket"](cr, text="Router kharab nikla, paise wapas chahiye"))
    req = asyncio.run(SEVA_HANDLERS["biz_seva_request"](cr, kind="refund", amount=1500, reason="router kharab", ticket=t["ticket"]))
    assert req["request"] == "X-0001" and "owner" in req["customer_say"]
    again = asyncio.run(SEVA_HANDLERS["biz_seva_request"](cr, kind="refund", amount=1500, reason="jaldi karo"))
    assert again["duplicate"]
    card = _events("seva_exception")[-1]
    assert card["check"]["within"] is False and "1000" in card["check"]["reasons"][0]
    eid = card["id"]
    with pytest.raises(S.SevaError):
        S.decide(T, eid, True)                                                              # not from a tap = refused
    out = asyncio.run(SEVA_HANDLERS["seva"](Ctx(T, conv), action="exception", kind="goodwill", amount=100, reason="late visit",
                                            ticket=t["ticket"]))
    assert out["needs_tap"]
    from app import approvekey as ak
    ph = Phone()
    ak.register(T, ph.device_id, ph.pub, "OnePlus")
    with pytest.raises(S.SevaError, match="fingerprint_needed"):
        S.decide(T, eid, True, by_tap=True)
    ch = S.fp_challenge(T, eid)
    bad = Phone("other").sign(ch)
    bad["device_id"] = ph.device_id
    with pytest.raises(S.SevaError, match="fingerprint_invalid"):
        S.decide(T, eid, True, proof=bad, by_tap=True)
    ch = S.fp_challenge(T, eid)
    with pytest.raises(S.SevaError):
        S.decide(T, eid, True, proof=ph.sign(ch), amount=2000, by_tap=True)                 # never more than asked
    ch = S.fp_challenge(T, eid)
    d = S.decide(T, eid, True, proof=ph.sign(ch), amount=1200, by_tap=True)
    assert d["exception"]["status"] == "approved" and "Hoola paise nahi bhejta" in d["say"]
    assert any("manzoor" in x and "₹1,200" in x for x in _queued())
    with pytest.raises(S.SevaError):
        S.decide(T, eid, False, by_tap=True)                                                # decided once
    S.mark_sent(T, eid, "UTR 123456789012")
    assert any("bhej diye" in x and "9012" in x for x in _queued())
    # saying no never needs a fingerprint
    other = S.exceptions(T, "pending")[0]
    assert S.decide(T, other["id"], False, note="Visit time par hua tha", by_tap=True)["exception"]["status"] == "rejected"


def test_tools_morning_and_api(sv):
    S, c = sv, sv._clock
    from app.agent.seva_tools import SEVA_HANDLERS
    from app.agent.tools import Ctx, ToolError
    from app.seva import api
    kb(S)
    conv = conv_ctx().conversation_id
    staff = Ctx(T, conv, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(SEVA_HANDLERS["seva"](staff, action="settings", refund_days=30))
    with pytest.raises(ToolError):
        asyncio.run(SEVA_HANDLERS["seva"](staff, action="sent", exception_id="x"))
    tk = asyncio.run(SEVA_HANDLERS["seva"](staff, action="ticket", text="Aag lagi meter mein, spark aa raha", name="Kamla"))
    assert tk["ticket"]["priority"] == "urgent"
    assert asyncio.run(SEVA_HANDLERS["seva_dekho"](staff, what="tickets"))["tickets"][0]["number"] == tk["number"]
    r = S.save_settings(T, ecommerce=True)
    assert r["warnings"] and "grievance officer" in r["warnings"][0]
    c.t = datetime(2026, 10, 23, 4, 0, tzinfo=timezone.utc)                                  # 09:30 IST next day
    assert S.tick(c.t)["mornings"] == 1 and _events("seva_day")[-1]["text"].startswith("Seva:")
    assert S.tick(c.t)["mornings"] == 0
    app = FastAPI()
    app.include_router(api.make_router(lambda: None, lambda: T))
    with TestClient(app) as cl:
        assert cl.get("/api/seva").json()["kb_live"] == 3
        assert cl.post("/api/seva/kb/ask", json={"question": "new connection kaise lagwaye"}).json()["status"] == "answered"
        up = cl.post("/api/seva/kb/import", files={"file": ("faq.txt", b"Q: Parking hai?\nA: Haan, peeche parking hai.\n", "text/plain")})
        assert up.status_code == 200 and up.json()["count"] == 1, up.text
        assert cl.post("/api/seva/kb/import_link", json={"text": "Q: Home delivery?\nA: Haan, 3 km tak.\n"}).json()["count"] == 1
        n = cl.post("/api/seva/tickets", json={"text": "Bill do baar aaya", "name": "Amit", "phone": "9822099999"}).json()
        num = n["number"]
        assert cl.post(f"/api/seva/tickets/{num}/note", json={"text": "check karna"}).status_code == 200
        ex = cl.post(f"/api/seva/tickets/{num}/exception", json={"kind": "waiver", "amount": 200, "reason": "late fee maaf"}).json()
        eid = ex["exception"]["id"]
        assert cl.post(f"/api/seva/exceptions/{eid}/decide", json={"yes": True, "hash": "wrong"}).status_code == 400
        ok = cl.post(f"/api/seva/exceptions/{eid}/decide", json={"yes": True, "hash": ex["exception"]["hash"]})
        assert ok.status_code == 200 and ok.json()["exception"]["status"] == "approved"
        assert cl.post(f"/api/seva/tickets/{num}/bogus", json={}).status_code == 404
        assert cl.put("/api/seva/settings", json={"sla": {"normal": [0, 5]}}).status_code == 400
        rep = cl.get("/api/seva/report?days=7").json()
        assert rep["tickets"] == 2 and rep["exceptions"]["approved"] == 1
        assert cl.get("/api/seva/gaps").status_code == 200
