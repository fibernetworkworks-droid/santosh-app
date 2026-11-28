"""SUPPORT HANDOVER (G7 of docs/SUPPORT_GLOBAL_PLAN.md): handing a customer to a person smoothly and honestly - her rules
for when (asked, anger, safety / legal / fraud words, money, VIP, two failed tries, no answer; safety and money never off),
a hand-over packet for the person (who, the problem, what Hoola checked and told them, how they feel, the deadline, a draft),
an honest line for the customer (a time only from real past waits, the next opening when closed, a call-back window on a
call), urgent ones paged, take / hand back with an instruction Hoola follows, corrections to Hoola's drafts lowering trust.
Walked in a real browser."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"
IST = ZoneInfo("Asia/Kolkata")


def ist(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=IST).astimezone(timezone.utc)


@pytest.fixture
def sv(env, monkeypatch):
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    from app import supportchat as SC
    SC._OF.clear()
    SC._BLOCK.clear()
    box = {"now": ist(2026, 11, 20, 11)}                    # Friday 11:00 in India
    monkeypatch.setattr(S, "clock", lambda: box["now"])
    told, chat, pub = [], [], []
    monkeypatch.setattr(S, "_tell", lambda tenant, tid, text, **k: (told.append(text), {"sent": "whatsapp", "text": text})[1])
    monkeypatch.setattr(S, "_note_chat", lambda tenant, text, conv="": chat.append(text))
    real_pub = S._publish
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, p, conv="": (pub.append((kind, p)), real_pub(tenant, kind, p, conv)))
    S.box, S.told, S.chat, S.pub = box, told, chat, pub
    return S


def test_when_hoola_hands_over(sv):
    from app.seva import engine as E
    from app.seva import handover as H
    S = sv
    assert E.reply(T, "I want to talk to a person", "whatsapp", "wa:919800000001")["rule"] == "asked"
    assert E.reply(T, "I will take you to consumer court, this is fraud", "whatsapp", "wa:919800000001")["rule"] == "safety"
    assert E.reply(T, "you people are useless, worst service ever", "whatsapp", "wa:919800000001")["rule"] == "angry"
    H.save(T, {"on": {"angry": False}})
    assert E.reply(T, "you people are useless, worst service ever", "whatsapp", "wa:919800000001").get("rule") != "angry"
    with pytest.raises(H.HandoverError, match="always goes to a person"):
        H.save(T, {"on": {"safety": False}})
    H.save(T, {"vip": ["+91 98000 00009"]})
    assert E.reply(T, "do you sell blue paint", "whatsapp", "wa:919800000009")["rule"] == "vip"
    assert E.reply(T, "do you sell red bricks", "whatsapp", "wa:919800000002")["rule"] == "unknown"
    assert E.reply(T, "do you sell green tiles", "whatsapp", "wa:919800000002")["rule"] == "failed"   # two tries in a row
    H.save(T, {"on": {"unknown": False, "failed": False}})
    assert E.reply(T, "do you sell glass", "whatsapp", "wa:919800000003")["decision"] == "no_answer"


def test_the_packet_and_an_honest_line(sv):
    from app.seva import handover as H
    S = sv
    old = S.new_ticket(T, "my bill was wrong last month", "whatsapp", name="Ana Rao", phone="919800000011")["number"]
    S.update(T, old, status="closed", tell=False)
    S.answer(T, "why is my internet slow", "whatsapp", "wa:919800000011")
    h = H.start(T, "wa:919800000011", "whatsapp", "the customer asked for a person", "asked", "internet is very slow since monday",
                "", "Ana Rao")
    p = h["packet"]
    assert p["customer"]["name"] == "Ana Rao" and p["customer"]["country_time_zone"] == "Asia/Kolkata" and p["customer"]["their_time"]
    assert "slow" in p["problem"] and p["hoola_checked"][0]["asked"].startswith("why is my internet")
    assert [x["number"] for x in p["tickets"]["others"]] == [old] and p["deadline"]["when"] and p["draft"].startswith("Hello Ana")
    assert "usually" not in h["customer_line"] and h["ticket"] in h["customer_line"]      # no past waits = no time promised
    for mins in (20, 30, 40):                                                             # her team's real waits
        x = H.start(T, f"wa:91980000{mins:04d}", "whatsapp", "help", "asked", f"problem number {mins}")
        S.box["now"] += timedelta(minutes=mins)
        H.take(T, x["id"], "Ravi")
    nxt = H.start(T, "wa:919800000099", "whatsapp", "help", "asked", "a new problem")
    assert "usually within about 30 minutes" in nxt["customer_line"]


def test_out_of_hours_call_back_and_urgent(sv):
    from app.seva import handover as H
    from app.seva import watch as W
    S = sv
    W.save(T, {"hours_on": True, "week": {d: (["09:00", "18:00"] if d not in ("sat", "sun") else []) for d in W.DAYS}})
    S.box["now"] = ist(2026, 11, 21, 15)                    # Saturday: closed
    h = H.start(T, "wa:919800000021", "whatsapp", "help", "asked", "my order did not come")
    assert h["out_of_hours"] and "closed right now" in h["customer_line"] and "Mon 23 Nov, 09:00" in h["customer_line"]
    c = H.start(T, "phone:919800000022", "phone", "wants a person", "asked", "call me about my plan")
    assert "call you back between Mon 23 Nov, 09:00 and Mon 23 Nov, 11:00" in c["customer_line"]
    S.chat.clear()
    u = H.start(T, "wa:919800000023", "whatsapp", "fire in the meter box", "safety", "there is fire and smoke from the meter")
    assert u["urgent"] and any("needs a person" in x for x in S.chat)                     # paged even when closed
    assert any(k == "seva_handover" and p.get("page") for k, p in S.pub)


def test_take_hand_back_and_the_instruction(sv, monkeypatch):
    from app.db import session
    from app.employee import inbox
    from app.employee.models import BizContact
    from app.seva import handover as H
    with session() as s:
        c = BizContact(tenant_id=T, wa_id="919800000031", name="Bo")
        s.add(c)
        s.flush()
        cid = c.id
    h = H.start(T, "wa:919800000031", "whatsapp", "asked", "asked", "where is my parcel", cid, "Bo")
    H.replied(T, cid, "staff:Ravi")
    assert H.get(T, h["id"])["status"] == "taken" and H.get(T, h["id"])["taken_by"] == "staff:Ravi"
    with session() as s:
        assert s.get(BizContact, cid).human is True
    with pytest.raises(H.HandoverError):
        H.hand_back(T, h["id"], "my otp is 123456")
    H.hand_back(T, h["id"], "send the tracking link and close if they confirm", "Ravi")
    with session() as s:
        assert s.get(BizContact, cid).human is False
        cc = s.get(BizContact, cid)
        s.expunge(cc)
    assert "send the tracking link" in H.back_note(T, cid)
    assert "send the tracking link" in inbox._system(T, cc)


def test_corrections_lower_trust(sv, monkeypatch):
    from app.employee import inbox
    from app.seva import engine as E
    S = sv
    monkeypatch.setattr(inbox, "notice_by_phone", lambda *a, **k: True)
    for i in range(2):
        d = E.save_draft(T, "whatsapp", "wa:919800000041", f"question {i}", "Your bill is due on the 5th.", "Knowledge", "billing")
        out = E.draft_decide(T, d["id"], "send", "Your bill is due on the 10th.")
    assert E.trust_level(T, "billing", "whatsapp") == "draft" and "corrected twice" in out["say"]
    assert any("corrected Hoola's answers on 'billing'" in x for x in S.chat)


def test_biz_handover_tool_routes_and_tools(sv):
    from app.agent import seva_tools as ST
    from app.agent.tools import Ctx
    from app.db import session
    from app.employee import inbox
    from app.employee.models import BizContact
    from app.main import app
    S = sv
    with session() as s:
        c = BizContact(tenant_id=T, wa_id="919800000051", name="Cy", last_text="my router is broken")
        s.add(c)
        s.flush()
        cid = c.id
    out = asyncio.run(inbox.biz_handover(Ctx(tenant_id=T, conversation_id="x", actor=f"customer:{cid}"), reason="asked for a person",
                                         rule="asked"))
    assert out["customer_line"] and out["ticket"] in out["customer_line"]
    cl = TestClient(app)
    ov = cl.get("/api/seva/handovers").json()
    assert ov["open"][0]["ticket"] == out["ticket"] and ov["rules"]["names"]["asked"]
    hid = ov["open"][0]["id"]
    assert cl.post(f"/api/seva/handovers/{hid}/take", json={}).json()["status"] == "taken"
    assert cl.post(f"/api/seva/handovers/{hid}/back", json={"note": "close it"}).json()["status"] == "back"
    assert cl.put("/api/seva/handover/rules", json={"on": {"money": False}}).status_code == 400
    assert cl.put("/api/seva/handover/rules", json={"vip": ["919800000052"]}).json()["vip"] == ["919800000052"]
    n = S.new_ticket(T, "please call me", "phone", name="Di", phone="919800000053")["number"]
    assert cl.post("/api/seva/handovers", json={"ticket": n, "reason": "she wants the manager"}).json()["ticket"] == n
    assert cl.get(f"/api/seva/handovers?ticket={n}").json()["handovers"][0]["rule"] == "asked"
    names = {t["name"]: t for t in ST.SEVA_TOOLS}
    assert {"handover", "hand_back", "handover_rules"} <= set(names["seva"]["input_schema"]["properties"]["action"]["enum"])
    assert "handovers" in names["seva_dekho"]["input_schema"]["properties"]["what"]["enum"]
    assert any(t["name"] == "biz_handover" and "rule" in t["input_schema"]["properties"] for t in inbox.BIZ_TOOLS)
    from app import push
    assert push.render("seva_handover", {"text": "x", "urgent": True}) and "seva_handover" in push.PUSH_KINDS


@pytest.fixture
def h_server(sv, monkeypatch):
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
    from app.seva import handover as H
    S = sv
    S.box["now"] = datetime.now(timezone.utc)
    hire.hire(T, "support", trust="seekh")
    h = H.start(T, "wa:919800000061", "whatsapp", "the customer asked for a person", "asked", "my internet is down", "", "Eli")
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
        yield f"http://127.0.0.1:{port}", browser, KEY, h
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_handover_in_a_real_browser(h_server):
    base, browser, key, h = h_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/support#/today")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Waiting for a person')", timeout=20000)
    pg.click("#spPage details summary >> text=The hand-over packet")
    assert "my internet is down" in pg.inner_text("#spPage")
    with pg.expect_response(lambda r: "/take" in r.url):
        pg.click(f"button[data-take='{h['id']}']")
    pg.wait_for_function(f"() => !document.querySelector(\"button[data-take='{h['id']}']\")", timeout=10000)
    pg.fill(f"form.spBack[data-id='{h['id']}'] [name=note]", "send the outage update and close if they confirm")
    with pg.expect_response(lambda r: "/back" in r.url) as rb:
        pg.click(f"form.spBack[data-id='{h['id']}'] button[type=submit]")
    assert rb.value.json()["status"] == "back"
    pg.goto(base + "/console/support#/settings")
    pg.wait_for_selector("#spHandRules")
    assert pg.is_disabled("#spHandRules [name=r_safety]")
    pg.fill("#spHandRules [name=vip]", "919800000070")
    with pg.expect_response(lambda r: "/api/seva/handover/rules" in r.url and r.request.method == "PUT") as rr:
        pg.click("#spHandRules button[type=submit]")
    assert rr.value.json()["vip"] == ["919800000070"]
    ctx.close()
    p2 = browser.new_context(viewport={"width": 390, "height": 900})
    p2.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    m = p2.new_page()
    m.on("pageerror", lambda e: errors.append(str(e)))
    m.goto(base + "/console/support#/today")
    m.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Open tickets')", timeout=20000)
    assert m.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    p2.close()
    assert not errors, errors
