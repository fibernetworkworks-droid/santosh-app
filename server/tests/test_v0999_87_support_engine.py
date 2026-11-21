"""SUPPORT ENGINE (G2 of docs/SUPPORT_GLOBAL_PLAN.md): understand (any language, intent, urgency, anger, "a person",
secrets) -> find -> decide in CODE -> write (the customer's language, shaped for the channel) -> check before sending
(numbers must be in the facts; no call-back / escalation / refund promise nobody made); trust level per topic and channel
(answer / draft for a person / always a person) with drafts a person sends; every WhatsApp business reply checked before
it goes (one rewrite, else a person). Walked in a real browser."""
from __future__ import annotations

import ipaddress

import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"


@pytest.fixture
def sv(env, monkeypatch):
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    from app.callcentre import knowledge as K
    monkeypatch.setattr(K, "_RESOLVE", lambda host: [ipaddress.ip_address("93.184.216.34")])
    from app import supportchat as SC
    SC._OF.clear()
    SC._BLOCK.clear()
    return S


def test_understand_any_language_and_intent(sv):
    from app.seva import engine as E
    assert E.lang_code("¿Dónde está mi pedido? Gracias") == "es"
    assert E.lang_code("Wann kommt meine Bestellung? Danke") == "de"
    assert E.lang_code("मेरा ऑर्डर कहाँ है") == "hi"
    assert E.lang_code("طلبي لم يصل") == "ar"
    assert E.lang_code("注文はどこですか") == "ja"
    assert E.lang_code("where is my parcel") == "en"
    u = E.understand
    assert u(T, "I want to talk to a real person")["intent"] == "person"
    assert u(T, "quiero hablar con una persona")["intent"] == "person"
    assert u(T, "where is my order")["intent"] == "status"
    assert u(T, "refund my money now")["intent"] == "money"
    q = u(T, "what is your refund policy?")
    assert q["intent"] == "question" and q["money"]
    assert u(T, "thanks!")["intent"] == "thanks"
    assert u(T, "this is the worst service, I will go to consumer court")["angry"]
    assert u(T, "my card number is 4111 1111 1111 1111")["secret"]


def test_decisions_in_code(sv):
    from app.seva import engine as E
    S = sv
    S.kb_add(T, "What is your refund policy?", "Refunds within 7 days of delivery, back to the same card.", "policy")
    S.kb_add(T, "What are your timings?", "10 am to 7 pm, Monday to Saturday.")
    r = E.reply
    assert r(T, "otp is 482913 please check")["decision"] == "refuse"
    assert r(T, "can I speak to a human")["decision"] == "person"
    assert r(T, "worst shop ever, fraud")["decision"] == "person"
    assert r(T, "give me a refund for order 22")["decision"] == "request"
    pol = r(T, "what is your refund policy?")
    assert pol["decision"] == "answer" and "7 days" in pol["reply"] and pol["exception"]
    ok = r(T, "what are your timings")
    assert ok["decision"] == "answer" and "10 am" in ok["reply"] and any("answered from" in w for w in ok["why"])
    assert r(T, "do you sell bicycles")["decision"] == "person"
    t = S.new_ticket(T, "router red light", "whatsapp", name="Ana", phone="919800000001")
    st = r(T, "where is my complaint", "whatsapp", "wa:919800000001")
    assert st["decision"] == "status" and t["number"] in st["reply"]


def test_trust_levels_and_drafts(sv, monkeypatch):
    from app.seva import engine as E
    S = sv
    S.kb_add(T, "What are your timings?", "10 am to 7 pm.")
    cat = E.understand(T, "what are your timings")["category"]
    assert E.trust_level(T, cat, "whatsapp") == "answer"            # nothing set = today's behaviour
    E.set_trust(T, "draft", "*", "*")
    d = E.reply(T, "what are your timings", "whatsapp", "wa:919800000002")
    assert d["decision"] == "draft" and d["reply"] == "" and d["draft_id"]
    waiting = E.drafts(T)
    assert len(waiting) == 1 and "10 am" in waiting[0]["reply"]
    E.set_trust(T, "answer", cat, "sms")                             # more specific wins
    assert E.reply(T, "what are your timings", "sms")["decision"] == "answer"
    E.set_trust(T, "person", cat, "*")
    assert E.reply(T, "what are your timings", "whatsapp")["decision"] == "person"
    from app.employee import inbox
    sent = []
    monkeypatch.setattr(inbox, "notice_by_phone", lambda t, ph, text: (sent.append((ph, text)), True)[1])
    out = E.draft_decide(T, waiting[0]["id"], "send", "We are open 10 am to 7 pm.")
    assert out["status"] == "sent" and sent == [("919800000002", "We are open 10 am to 7 pm.")]
    with pytest.raises(E.EngineError):
        E.draft_decide(T, waiting[0]["id"], "send")
    with pytest.raises(E.EngineError):
        E.set_trust(T, "maybe")


def test_language_and_channel_shape(sv, monkeypatch):
    from app.seva import engine as E
    S = sv
    S.kb_add(T, "What are your timings?", "We are open 10 am to 7 pm, Monday to Saturday.")
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "Abrimos de 10 am a 7 pm, de lunes a sábado.")
    es = E.reply(T, "¿Cuáles son los horarios de la tienda? Gracias. what are your timings", "whatsapp")
    assert es["decision"] == "answer" and es["translated"] and es["reply"].startswith("Abrimos")
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "Abrimos de 9 am a 8 pm.")          # a changed number = thrown away
    es2 = E.reply(T, "¿Cuáles son los horarios de la tienda? Gracias. what are your timings", "whatsapp")
    assert not es2["translated"] and "10 am" in es2["reply"]
    long = "This is a sentence about our service. " * 30
    assert len(E.shape(long, "sms")) <= 320 and E.shape(long, "sms").endswith(".")
    assert "http" not in E.shape("Track it at https://x.example/t/1 today.", "phone")


def test_check_before_sending(sv):
    from app.seva import engine as E
    facts = "Delivery in 3 to 5 days. Ticket SUP-12 opened."
    assert E.check_reply("Delivery takes 3 to 5 days.", facts) == []
    assert any("number 2" in p for p in E.check_reply("Delivery takes 2 days.", facts))
    assert any("no ticket" in p for p in E.check_reply("Our team will call you back today.", facts))
    assert E.check_reply("Our team will call you back.", facts, made={"handover"}) == []
    assert any("promises money" in p for p in E.check_reply("Your refund has been processed.", facts, made={"ticket"}))
    assert E.check_reply("Your refund has been processed.", facts, owner_ok=True) == []
    hist = [{"role": "user", "content": "my order 881 is late"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "biz_seva_ticket", "input": {}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": '{"ticket": "SUP-12"}'}]}]
    assert E.outgoing_problems("Ticket SUP-12 is open for order 881; the team will contact you.", "Shop hours 10-7", hist) == []
    assert E.outgoing_problems("You get 20% off next time.", "Shop hours 10-7", hist)


def test_inbox_reply_is_checked_then_rewritten_or_handed_over(sv, monkeypatch):
    import asyncio
    from app.employee import inbox
    calls = {"handover": 0}

    async def handover(ctx, reason="", **_):
        calls["handover"] += 1
        return {"ok": True}
    monkeypatch.setattr(inbox, "biz_handover", handover)
    hist = [{"role": "user", "content": "how long is delivery"}]
    sysp = "Delivery in 3 to 5 days."

    async def good(system, history, tools):
        return [{"type": "text", "text": "Delivery takes 3 to 5 days."}], "end_turn"
    monkeypatch.setattr(inbox, "_brain", good)
    assert asyncio.run(inbox._checked(T, "c1", sysp, hist, "Delivery takes 1 day.", None)) == "Delivery takes 3 to 5 days."

    async def bad(system, history, tools):
        return [{"type": "text", "text": "Delivery takes 2 days, we will call you back."}], "end_turn"
    monkeypatch.setattr(inbox, "_brain", bad)
    assert asyncio.run(inbox._checked(T, "c1", sysp, hist, "Delivery takes 1 day.", None)) == inbox.SAFE_LINE
    assert calls["handover"] == 1
    assert asyncio.run(inbox._checked(T, "c1", sysp, hist, "Delivery takes 3 to 5 days.", None)) == "Delivery takes 3 to 5 days."


def test_routes_and_tool(sv):
    from app.main import app
    from app.agent import seva_tools as ST
    S = sv
    S.kb_add(T, "What are your timings?", "10 am to 7 pm.")
    c = TestClient(app)
    r = c.post("/api/seva/engine/try", json={"text": "what are your timings", "channel": "sms"}).json()
    assert r["decision"] == "answer" and r["channel"] == "sms"
    assert c.put("/api/seva/trust", json={"level": "draft"}).json()["default"] == "draft"
    tr = c.post("/api/seva/engine/try", json={"text": "what are your timings"}).json()
    assert tr["decision"] == "draft" and c.get("/api/seva/drafts").json()["drafts"] == []    # a try never leaves a draft
    assert c.put("/api/seva/trust", json={"level": "nope"}).status_code == 400
    names = {t["name"]: t for t in ST.SEVA_TOOLS}
    for a in ("try", "trust", "draft_send", "draft_sent", "draft_discard"):
        assert a in names["seva"]["input_schema"]["properties"]["action"]["enum"]
    assert {"trust", "drafts"} <= set(names["seva_dekho"]["input_schema"]["properties"]["what"]["enum"])


@pytest.fixture
def en_server(sv, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    from app.seva import engine as E
    S = sv
    hire.hire(T, "support", trust="seekh")
    S.kb_add(T, "What are your timings?", "10 am to 7 pm, Monday to Saturday.")
    E.set_trust(T, "draft")
    E.reply(T, "what are your timings", "whatsapp", "wa:919800000003")
    E.set_trust(T, "answer")
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_engine_in_a_real_browser(en_server):
    base, browser, key = en_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/support")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Replies waiting for a person')", timeout=20000)
    pg.click("[data-draftact='sent']")
    pg.wait_for_function("() => !document.querySelector('[data-draftact]')", timeout=10000)
    pg.goto(base + "/console/support#/knowledge")
    pg.wait_for_selector("#spTest input[name=question]")
    pg.fill("#spTest input[name=question]", "can I talk to a real person")
    pg.click("#spTest button[type=submit]")
    pg.wait_for_function("() => (document.querySelector('#spTestLine') || {innerText: ''}).innerText.includes('hand it to a person')", timeout=10000)
    pg.fill("#spTest input[name=question]", "what are your timings")
    pg.select_option("#spTestCh", "sms")
    pg.click("#spTest button[type=submit]")
    pg.wait_for_function("() => (document.querySelector('#spTestLine') || {innerText: ''}).innerText.includes('10 am to 7 pm')", timeout=10000)
    assert "Hoola answers alone" in pg.inner_text("#spTestLine")
    pg.goto(base + "/console/support#/settings")
    pg.wait_for_selector("[data-trow][data-topic='*'] select")
    pg.select_option("[data-trow][data-topic='*'] select", "person")
    pg.click("[data-trow][data-topic='*'] [data-trustsave]")
    pg.wait_for_function("() => document.querySelector(\"[data-trow][data-topic='*'] select\").value === 'person'", timeout=10000)
    ctx.close()
    assert not errors, errors
