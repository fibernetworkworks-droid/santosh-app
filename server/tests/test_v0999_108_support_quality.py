"""G11 SUPPORT QUALITY (docs/SUPPORT_GLOBAL_PLAN.md): the daily sample of AI answers + accuracy per topic and language +
a weak topic moving to draft only by itself; the simulated-customer card (nothing saved or sent) and the replay of last
week's questions; law packs with sources ('check this'); the AI disclosure once per customer in their language;
a customer's data exported / erased with the law's deadline, retention per channel, card / Aadhaar numbers masked; the
audit log + CSV; the Quality & law page in a browser."""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

T = "default"


@pytest.fixture
def ql(env, monkeypatch):
    from app.seva import quality as QL
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    box = {"now": datetime(2026, 11, 20, 6, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(S, "clock", lambda: box["now"])
    chat = []
    monkeypatch.setattr(S, "_note_chat", lambda tenant, text, conv="": chat.append(text))
    monkeypatch.setattr(S, "_tell", lambda tenant, tid, text, **k: {"sent": "whatsapp", "text": text})
    S.kb_add(T, "What are your timings?", "We are open 10 am to 7 pm, Monday to Saturday.")
    S.kb_add(T, "How do I pay my bill?", "Pay your bill by UPI to shop@upi or at the counter.")
    S.box, S.chat = box, chat
    return S, QL


def _ask(S, text, channel="whatsapp", n=1):
    from app.seva import engine as E
    for _ in range(n):
        E.reply(T, text, channel, "", "test")


def test_sample_marks_accuracy_and_auto_draft(ql):
    S, QL = ql
    from app.seva import engine as E
    for i in range(6):
        _ask(S, "What are your timings?")
        _ask(S, "How do I pay my bill?")
    QL.save_settings(T, {"min_marks": 4, "line": 80, "sample_n": 6})
    sm = QL.sample(T)
    assert len(sm) == 6 and {x["topic"] for x in sm} >= {S.R.guess_category("How do I pay my bill?")}
    assert sm[0]["answer"] and sm[0]["matched"]
    bill = [x for x in sm if "bill" in x["question"]]
    assert bill
    topic = bill[0]["topic"]
    assert E.trust_level(T, topic, "*") == "answer"
    ids = [x["id"] for x in sm]
    with pytest.raises(QL.QualityError):
        QL.mark(T, ids[0], "maybe")
    # mark every sampled bill answer wrong, then more until the line is crossed
    marked = 0
    for x in QL.sample(T, 50):
        if x["topic"] == topic and marked < 4:
            r = QL.mark(T, x["id"], "wrong" if marked else "right")
            marked += 1
    assert E.trust_level(T, topic, "*") == "draft" and "draft" in r["dropped"] and any("drafts them" in c for c in S.chat)
    acc = {(a["topic"], a["lang"]): a for a in QL.accuracy(T)}
    assert acc[(topic, "*")]["marks"] == 4 and acc[(topic, "*")]["right_share"] == 0.25 and (topic, "en") in acc
    assert QL.settings(T)["auto"][0]["topic"] == topic
    QL.mark(T, ids[0], "right")
    assert all(x["id"] != ids[0] for x in QL.sample(T, 50))                         # a marked answer is not shown again


def test_simulated_customers_leave_nothing_behind(ql):
    S, QL = ql
    from app.db import session
    from app.seva import engine as E
    with session() as s:
        before = s.query(S.SevaQuestion).count()
    card = QL.run_card(T)
    with session() as s:
        assert s.query(S.SevaQuestion).count() == before                             # nothing saved
        assert s.query(E.SevaDraft).count() == 0
    by = {(x["case"], x["lang"], x["channel"]): x for x in card["results"]}
    assert by[("card", "en", "web")]["decision"] == "refuse" and by[("card", "en", "web")]["passed"]
    assert by[("person", "es", "email")]["decision"] == "person"
    assert by[("angry", "en", "whatsapp")]["passed"] and by[("safety", "en", "web")]["passed"]
    assert by[("own1", "en", "web")]["decision"] in ("answer", "draft")
    assert card["total"] == len(card["results"]) and card["passed"] >= card["total"] - 6
    fails = [x for x in card["results"] if not x["passed"]]
    assert all(x["problems"] for x in fails)
    assert QL.runs(T, "card")[0]["total"] == card["total"]


def test_replay_shows_what_would_change(ql):
    S, QL = ql
    from app.seva import engine as E
    _ask(S, "What are your timings?", n=2)
    _ask(S, "Do you deliver to Pune?", n=1)
    r0 = QL.replay(T)
    assert r0["total"] == 3 and r0["changed"] == []
    S.kb_add(T, "Do you deliver to Pune?", "Yes, we deliver to Pune in 2 days.")
    r1 = QL.replay(T)
    assert len(r1["changed"]) == 1 and r1["changed"][0]["was"] == "unknown" and r1["changed"][0]["now"] == "answered"
    E.set_trust(T, "person", S.R.guess_category("What are your timings?"), "*")
    r2 = QL.replay(T)
    assert any(c["now"] == "unknown" and "timings" in c["question"] for c in r2["changed"])


def test_law_packs_have_sources_and_say_check_this(ql):
    S, QL = ql
    rows = QL.law_for(["DE"])
    ids = {r["id"] for r in rows}
    assert {"ai_eu", "gdpr", "eaa"} <= ids and "dpdp" not in ids
    assert all(r["status"] == "check this" and r["source"] for r in rows)
    assert {r["id"] for r in QL.law_for(["IN"])} >= {"dpdp", "ecom_in"}
    assert "ccpa" in {r["id"] for r in QL.law_for(["US-CA"])}
    assert QL._deadline("BR") == (15, "LGPD (Law 13.709/2018), Articles 18-19")
    assert QL._deadline("ZZ")[0] == 30 and "no written pack" in QL._deadline("ZZ")[1]


def test_ai_disclosure_once_in_their_language(ql):
    S, QL = ql
    from app.seva import channels as CH
    first = QL.disclose(T, "telegram:111", "We open at 10.", "What time do you open?")
    assert "an AI assistant" in first and first.endswith("We open at 10.")
    es = QL.disclose(T, "telegram:222", "Abrimos a las 10.", "¿A qué hora abren?")
    assert es.startswith("Soy") and "asistente de IA" in es
    CH._store(T, "c1", "telegram:111", "", "out", "hoola", first, "", "sent")
    assert QL.disclose(T, "telegram:111", "Anything else?", "thanks") == "Anything else?"          # never twice
    QL.save_settings(T, {"disclose": False})
    assert QL.disclose(T, "telegram:333", "Hi.", "hello") == "Hi."
    with QL.dry():
        QL.save_settings(T, {"disclose": True})
        assert QL.disclose(T, "telegram:444", "Hi.", "hello") == "Hi."                             # a simulation never


def test_customer_data_export_erase_and_deadlines(ql):
    S, QL = ql
    from app.seva import channels as CH
    n = S.new_ticket(T, "My router is broken", "whatsapp", phone="9811112222", name="Ana")["number"]
    CH._store(T, "c1", "wa:919811112222", "Ana", "in", "customer", "Hello, router broken", "m1", "")
    _ask(S, "What are your timings?")
    out = QL.export_customer(T, "+91 98111 12222")
    assert out["tickets"][0]["number"] == n and out["messages"][0]["text"] == "Hello, router broken"
    assert "DPDP" in out["law"]
    with pytest.raises(QL.QualityError, match="DELETE"):
        QL.delete_customer(T, "9811112222")
    gone = QL.delete_customer(T, "9811112222", "DELETE")
    assert gone["gone"]["messages"] == 1 and gone["gone"]["tickets"] == 1
    t = S.ticket(T, n)
    assert t["text"] == "(erased at the customer's request)" and "router" not in json.dumps(t)
    assert QL.export_customer(T, "9811112222")["messages"] == []
    reqs = QL.requests_(T)
    assert [r["kind"] for r in reqs][:2] == ["access", "delete"] or {r["kind"] for r in reqs} == {"access", "delete"}
    d = next(r for r in reqs if r["kind"] == "delete")
    assert d["country"] == "IN" and d["due"] and "9811112222" not in json.dumps(reqs[0]) + json.dumps(d)
    ex = QL.export_customer(T, "ana@example.com")
    assert ex["customer"] == ["email:ana@example.com"]


def test_retention_and_masking_sweep(ql):
    S, QL = ql
    from app.db import session
    from app.seva import channels as CH
    with pytest.raises(QL.QualityError, match="30 days"):
        QL.save_settings(T, {"retention": {"chat": 7}})
    QL.save_settings(T, {"retention": {"chat": 30, "tickets": 60}})
    CH._store(T, "c1", "telegram:9", "", "in", "customer", "old message", "o1", "")
    n = S.new_ticket(T, "Old problem now closed", "email", customer="email:o@q.com")["number"]
    S.update(T, n, status="closed")
    S.box["now"] += timedelta(days=61)
    CH._store(T, "c1", "telegram:9", "", "in", "customer", "my card 4111 1111 1111 1111 and aadhaar 2345 6789 0123", "n1", "")
    with session() as s:
        m = s.query(CH.SevaChatMsg).filter_by(ext_id="n1").first()
        m.text = "my card 4111 1111 1111 1111 and aadhaar 2345 6789 0123"           # as if stored before masking existed
    r = QL.sweep(T)
    assert r["chat_deleted"] == 1 and r["tickets_erased"] == 1 and r["masked"] == 2
    with session() as s:
        txt = s.query(CH.SevaChatMsg).filter_by(ext_id="n1").first().text
    assert "4111 1111" not in txt and "XXXX-1111" in txt and "XXXX-0123" in txt
    assert QL.sweep(T) == {"skipped": True}
    assert QL.mask_numbers("call 9811112222 or order 12345")[1] == 0                 # phone numbers and order numbers stay


def test_audit_log_and_csv(ql):
    S, QL = ql
    n = S.new_ticket(T, "=HYPERLINK(\"x\") broken", "email", customer="email:a@q.com")["number"]
    S.update(T, n, status="pending", note="checked the line")
    _ask(S, "What are your timings?")
    q = QL.sample(T)[0]
    QL.mark(T, q["id"], "right")
    rows = QL.audit(T)
    kinds = {r["kind"] for r in rows}
    assert {"ticket", "review", "knowledge"} <= kinds
    csv = QL.audit_csv(T)
    assert csv.startswith("when,kind,by,what") and "\n=" not in csv and ",=" not in csv


def test_routes_and_translate(ql, monkeypatch):
    S, QL = ql
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.seva.api import make_router
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(a)
    _ask(S, "What are your timings?")
    d = cl.get("/api/seva/quality").json()
    assert d["sample"] and d["law"] and "one server" in d["data_location"]
    assert cl.post(f"/api/seva/quality/marks/{d['sample'][0]['id']}", json={"mark": "right"}).json()["topic"]
    assert cl.post("/api/seva/quality/card", json={"languages": ["en"], "channels": ["web"]}).json()["total"] >= 9
    assert cl.post("/api/seva/quality/delete", json={"customer": "x@y.com"}).status_code == 400
    assert cl.get("/api/seva/quality/audit.csv").headers["content-type"].startswith("text/csv")
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "My bill is wrong, they charged me twice")
    tr = cl.post("/api/seva/translate", json={"text": "Mi factura está mal, me cobraron dos veces", "to": "en"}).json()
    assert tr["translated"] and tr["from"] == "es" and "charged me twice" in tr["text"]


# ---------------------------------------------------------------- the Quality & law page in a real browser
@pytest.fixture
def q_server(ql, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "support", trust="seekh")
    S, QL = ql
    _ask(S, "What are your timings?", n=2)
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
        yield f"http://127.0.0.1:{port}", browser, KEY, S, QL
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_quality_page_in_a_real_browser(q_server):
    base, browser, key, S, QL = q_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/support#/quality")
    pg.wait_for_selector("[data-qmark=right]")
    with pg.expect_response(lambda r: "/api/seva/quality/marks/" in r.url):
        pg.click("[data-qmark=right] >> nth=0")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('100%')", timeout=15000)
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/quality/card"), timeout=60000):
        pg.click("[data-act=runcard]")
    pg.wait_for_function("() => /simulated customers handled/.test(document.querySelector('#spPage').innerText)", timeout=20000)
    txt = pg.inner_text("#spPage").lower()
    assert "gives a card number" in txt and "check this" in txt
    pg.fill("#spData [name=customer]", "ana@example.com")
    with pg.expect_download() as dl:
        pg.click("#spData button[value=export]")
    assert json.loads(open(dl.value.path()).read())["customer"] == ["email:ana@example.com"]
    pg.wait_for_selector("[data-act=audit]")
    pg.click("[data-act=audit]")
    pg.wait_for_function("() => document.querySelector('#spAudit').innerText.length > 5", timeout=15000)
    ctx.close()
    m = browser.new_context(viewport={"width": 390, "height": 900})
    m.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    mp = m.new_page()
    mp.on("pageerror", lambda e: errors.append(str(e)))
    mp.goto(base + "/console/support#/quality")
    mp.wait_for_selector("#spQSet")
    assert mp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    m.close()
    assert not errors, errors
