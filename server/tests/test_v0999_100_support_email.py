"""SUPPORT EMAIL (G6 of docs/SUPPORT_GLOBAL_PLAN.md): her support address in the one support desk - read over IMAP or
through a Hoola forwarding address (signed by the owner's email worker), answered over SMTP from HER address in the same
thread with her signature and the ticket number in the subject; a reply finds its ticket (subject tag or Hoola's own
Message-ID) and goes to the person working it; "did this fix it?" answered by mail closes it; automatic mails, lists,
bounces and her own address never answered; attachments kept and a PDF's text noted; the contact form's customers
answered by mail. IMAP and SMTP are fakes here. Walked in a real browser."""
from __future__ import annotations

import email
import hashlib
import hmac
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"


def mail(frm="ana@example.com", subject="Opening hours", body="what are your timings?", **h):
    m = EmailMessage()
    m["From"] = f"Ana Rao <{frm}>"
    m["To"] = "help@shop.example"
    m["Subject"] = subject
    m["Message-ID"] = h.pop("mid", email.utils.make_msgid(domain="example.com"))
    for k, v in h.items():
        m[k.replace("_", "-")] = v
    m.set_content(body)
    return m


@pytest.fixture
def em(env, monkeypatch):
    from app.seva import service as S
    from app.seva import supportmail as SM
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    monkeypatch.setattr(S, "_note_chat", lambda *a, **k: None)
    SM._SENT.clear()
    sent, box = [], {"mails": [], "uid": 100}
    monkeypatch.setattr(SM, "_smtp_send", lambda k, msg: sent.append(msg))
    monkeypatch.setattr(SM, "_smtp_check", lambda k: None)
    monkeypatch.setattr(SM, "_imap_check", lambda k: box["uid"])

    def fetch(k, since):
        out = [(u, r) for u, r in box["mails"] if u > since]
        box["mails"] = []
        return out, max([since] + [u for u, _ in out])
    monkeypatch.setattr(SM, "_imap_fetch", fetch)
    S.kb_add(T, "What are your timings?", "10 am to 7 pm, Monday to Saturday.")
    SM.setup(T, {"address": "help@shop.example", "name": "Asha's shop", "imap_host": "imap.shop.example", "smtp_host": "smtp.shop.example",
                 "user": "help@shop.example", "password": "app-pass-123", "signature": "Asha's shop · +91 98000 00000"})

    def deliver(m):
        box["uid"] += 1
        box["mails"].append((box["uid"], bytes(m)))
        return SM.poll(T, force=True)
    yield SM, S, sent, deliver


def test_setup_seals_and_checks(em):
    SM, S, sent, deliver = em
    v = SM.view(T)
    assert v["status"] == "ok" and "Reading works" in v["note"] and "Sending works" in v["note"]
    from app.db import session
    from app.seva import channels as CH
    with session() as s:
        row = s.scalars(CH.select(CH.SevaChannel).where(CH.SevaChannel.kind == "email")).one()
        assert "app-pass-123" not in row.sealed and "app-pass-123" not in str(v)
    with pytest.raises(SM.MailError, match="support email address"):
        SM.setup(T, {"address": "not an address"})
    SM.setup(T, {"address": "help@shop.example", "signature": "New sign"})
    assert SM.view(T)["signature"] == "New sign" and SM.view(T)["imap"]              # the saved password is kept


def test_a_new_mail_is_answered_in_the_thread(em):
    SM, S, sent, deliver = em
    m = mail(mid="<q1@example.com>")
    assert deliver(m) == 1
    out = sent[-1]
    assert out["To"] == "ana@example.com" and out["From"].endswith("<help@shop.example>")
    assert out["Subject"] == "Re: Opening hours" and out["In-Reply-To"] == "<q1@example.com>"
    body = out.get_content()
    assert "10 am to 7 pm" in body and "-- \nAsha's shop" in body
    assert deliver(m) == 1 and len(sent) == 1                                     # the same mail read twice: once


def test_reply_finds_its_ticket_and_waits_for_the_person(em):
    SM, S, sent, deliver = em
    deliver(mail(subject="No internet", body="my internet is not working since morning, I want to talk to a person"))
    from app.seva import handover as H
    h = H.handovers(T, "open")[0]
    num = h["ticket"]
    out = sent[-1]
    assert f"[{num}]" in out["Subject"] and f"seva.{num}." in out["Message-ID"] and "passed this to" in out.get_content()
    n = len(sent)
    deliver(mail(subject=f"Re: No internet [{num}]", body="here is my router serial: AB123\n\nOn Mon, Hoola wrote:\n> old text",
                 In_Reply_To=out["Message-ID"]))
    assert len(sent) == n                                                         # a person has it: no auto answer
    t = S.ticket(T, num)
    assert any("router serial: AB123" in x["text"] and "old text" not in x["text"] for x in t["notes"])
    S.update(T, num, status="pending", public="Please restart the router once.")
    assert "restart the router" in sent[-1].get_content() and f"[{num}]" in sent[-1]["Subject"]


def test_did_this_fix_it_by_mail(em):
    SM, S, sent, deliver = em
    r = S.new_ticket(T, "my bill is wrong", "email", "email:ana@example.com", "Ana")
    num = r["number"]
    S.update(T, num, status="resolved", public="We corrected the bill.")
    assert any("Did this fix it?" in m.get_content() for m in sent)
    deliver(mail(subject=f"Re: Your request [{num}]", body="Yes, thanks!"))
    assert S.ticket(T, num)["status"] == "closed"


def test_never_answered_and_attachments(em):
    SM, S, sent, deliver = em
    for m in (mail(frm="mailer-daemon@example.com"), mail(frm="help@shop.example"), mail(Auto_Submitted="auto-replied"),
              mail(List_Unsubscribe="<mailto:x@y>"), mail(frm="no-reply@bank.example")):
        deliver(m)
    assert sent == []
    m = mail(subject="Invoice problem", body="please see the invoice, it is charged twice, I want to talk to a person")
    pdf = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
           b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 300]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF")
    m.add_attachment(pdf, maintype="application", subtype="pdf", filename="invoice.pdf")
    deliver(m)
    from app.seva import channels as CH
    th = CH.thread(T, "email:ana@example.com")
    assert th["messages"][0]["file"] and "invoice.pdf" in th["messages"][0]["text"]


def test_loop_guard(em):
    SM, S, sent, deliver = em
    for i in range(8):
        deliver(mail(subject=f"Hours {i}", body="what are your timings?"))
    assert len(sent) == SM.PER_HOUR                                               # a loop stops at her hourly cap


def test_forwarding_address_and_form_customers(em, monkeypatch):
    SM, S, sent, deliver = em
    from app import agentmail
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "hoola_mail_domain", "mail.hoola.example", raising=False)
    monkeypatch.setattr(get_settings(), "hoola_mail_secret", "wsecret", raising=False)
    monkeypatch.setattr(agentmail, "configured", lambda: True)
    monkeypatch.setattr(agentmail, "domain", lambda: "mail.hoola.example")
    fwd = SM.view(T)["forward"]
    assert fwd.startswith("support-") and fwd.endswith("@mail.hoola.example")
    raw = bytes(mail(frm="bo@example.com", subject="Hours?"))
    from app.main import app
    c = TestClient(app)
    bad = c.post("/api/agentmail/inbound", content=raw, headers={"x-hoola-to": fwd, "x-hoola-sig": "nope"})
    assert bad.status_code == 403
    sig = agentmail.sign(fwd, raw, "wsecret")
    ok = c.post("/api/agentmail/inbound", content=raw, headers={"x-hoola-to": fwd, "x-hoola-sig": sig})
    assert ok.status_code == 200 and sent[-1]["To"] == "bo@example.com"
    t = S.new_ticket(T, "a question from the website form", "web", "email:cy@example.com", "Cy")
    S.update(T, t["number"], status="pending", public="Which order number is it?")
    assert sent[-1]["To"] == "cy@example.com" and "Which order number" in sent[-1].get_content()


def test_routes(em):
    SM, S, sent, deliver = em
    from app.main import app
    c = TestClient(app)
    g = c.get("/api/seva/email").json()["email"]
    assert g["address"] == "help@shop.example" and "app-pass" not in str(g)
    assert c.post("/api/seva/email/check").json()["status"] == "ok"
    assert c.post("/api/seva/email/poll").json()["read"] == 0
    assert c.put("/api/seva/email", json={"address": "x"}).status_code == 400
    assert c.put("/api/seva/email", json={"address": "help@shop.example", "imap_host": "imap.x", "user": "", "password": ""}).status_code == 400


@pytest.fixture
def m_server(em, monkeypatch):
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
    hire.hire(T, "support", trust="seekh")
    SM, S, sent, deliver = em
    deliver(mail())
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
        yield f"http://127.0.0.1:{port}", browser, KEY, sent
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_email_in_a_real_browser(m_server):
    base, browser, key, sent = m_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/support#/settings")
    pg.wait_for_selector("#spMail")
    assert pg.input_value("#spMail [name=password]") == "" and pg.get_attribute("#spMail [name=password]", "type") == "password"
    pg.fill("#spMail [name=signature]", "Asha's shop, Pune")
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/email") and r.request.method == "PUT") as rr:
        pg.click("#spMail button[type=submit]")
    assert rr.value.json()["signature"] == "Asha's shop, Pune"
    pg.goto(base + "/console/support#/inbox")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Messages on your apps')", timeout=15000)
    pg.click("a[href='#/chat/email%3Aana%40example.com']")
    pg.wait_for_selector("#spChat")
    pg.fill("#spChat [name=text]", "We also open on Sundays.")
    with pg.expect_response(lambda r: "/send" in r.url):
        pg.click("#spChat button[type=submit]")
    assert "We also open on Sundays." in sent[-1].get_content() and "Asha's shop, Pune" in sent[-1].get_content()
    ctx.close()
    p2 = browser.new_context(viewport={"width": 390, "height": 900})
    p2.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    m = p2.new_page()
    m.on("pageerror", lambda e: errors.append(str(e)))
    m.goto(base + "/console/support#/settings")
    m.wait_for_selector("#spMail")
    assert m.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    p2.close()
    assert not errors, errors
