"""Email: reading the inbox, drafting a threaded reply, and the approval-before-send gate."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app import mail
from app.agent.tools import Ctx, ToolError, dispatch
from app.db import EmailDraft, session
from tests.test_life import conv_ctx


INBOX = {
    "101": {"id": "101", "from": "Ramesh Patil", "from_email": "ramesh@vendor.in",
            "to": "me@shop.in", "cc": "", "subject": "Quotation for 10 routers",
            "date": "Sun, 18 Oct 2026 10:00:00 +0530", "message_id": "<abc@vendor.in>", "references": "",
            "body": "Namaste, kya aap 10 routers ka quotation bhej sakte hain? Dhanyavaad, Ramesh", "truncated": False},
}


@pytest.fixture
def mailbox(monkeypatch):
    monkeypatch.setattr(mail, "configured", lambda: True)
    sent = []

    async def fake_fetch(limit=10, unread_only=False, search=None, mailbox="INBOX"):
        return [{"id": v["id"], "from": v["from"], "from_email": v["from_email"], "subject": v["subject"],
                 "date": v["date"], "unread": True} for v in INBOX.values()]

    async def fake_read(uid, mailbox="INBOX", mark_seen=True):
        if uid not in INBOX:
            raise mail.MailError("not found")
        return dict(INBOX[uid])

    async def fake_send(to_addr, subject, body, cc="", in_reply_to=None, references=None):
        sent.append({"to": to_addr, "subject": subject, "body": body, "cc": cc, "in_reply_to": in_reply_to})
        return "<sent-id@shop.in>"

    monkeypatch.setattr(mail, "fetch_recent", fake_fetch)
    monkeypatch.setattr(mail, "read_email", fake_read)
    monkeypatch.setattr(mail, "send_email", fake_send)
    return sent


def test_check_read_and_draft_reply_threads(mailbox):
    ctx = conv_ctx()
    lst = asyncio.run(dispatch("email_check", {"unread_only": True}, ctx))
    assert lst["count"] == 1 and lst["emails"][0]["from_email"] == "ramesh@vendor.in"
    full = asyncio.run(dispatch("email_read", {"id": "101"}, ctx))
    assert "quotation" in full["body"].lower()
    out = asyncio.run(dispatch("email_draft", {"reply_to_id": "101", "body": "Ji Ramesh, 10 routers ka quotation attach kar raha hoon. - Meghana"}, ctx))
    assert out["status"] == "pending_approval"
    with session() as s:
        d = s.get(EmailDraft, out["draft_id"])
        assert d.to_addr == "ramesh@vendor.in"           # replied to the sender
        assert d.subject == "Re: Quotation for 10 routers"  # threaded subject
        assert d.in_reply_to == "<abc@vendor.in>" and d.status == "pending"
    assert mailbox == []                                  # nothing sent yet


def test_draft_needs_recipient(mailbox):
    ctx = conv_ctx()
    with pytest.raises(ToolError, match="email address|Kis email"):
        asyncio.run(dispatch("email_draft", {"body": "hello"}, ctx))


def test_send_only_after_approval(env, monkeypatch, mailbox):
    from app import main
    from app.config import get_settings
    get_settings.cache_clear()   # mailbox fixture already forces mail.configured() True
    ctx = conv_ctx()
    out = asyncio.run(dispatch("email_draft", {"to": "ramesh@vendor.in", "subject": "Hi", "body": "Test"}, ctx))
    did = out["draft_id"]
    with TestClient(main.app) as c:
        assert "email" in c.get("/healthz").json()["features"]
        pend = c.get("/api/emails/pending").json()["emails"]
        assert any(e["id"] == did for e in pend)
        # approve with an edit
        r = c.post(f"/api/emails/{did}/send", json={"body": "Final text"})
        assert r.status_code == 200 and r.json()["status"] == "sent"
    assert len(mailbox) == 1 and mailbox[0]["to"] == "ramesh@vendor.in" and mailbox[0]["body"] == "Final text"
    with session() as s:
        assert s.get(EmailDraft, did).status == "sent"


def test_cancel_draft_is_not_sent(env, monkeypatch, mailbox):
    from app import main
    from app.config import get_settings
    get_settings.cache_clear()
    ctx = conv_ctx()
    did = asyncio.run(dispatch("email_draft", {"to": "x@y.in", "subject": "s", "body": "b"}, ctx))["draft_id"]
    with TestClient(main.app) as c:
        assert c.post(f"/api/emails/{did}/cancel").status_code == 200
        assert all(e["id"] != did for e in c.get("/api/emails/pending").json()["emails"])
    assert mailbox == []


def test_provider_autodetect():
    from app.config import get_settings
    get_settings.cache_clear()
    import os
    os.environ["EMAIL_ADDRESS"] = "meghana@gmail.com"
    os.environ["EMAIL_PASSWORD"] = "app-pass"
    get_settings.cache_clear()
    imap, iport, smtp, sport = mail._hosts()
    assert imap == "imap.gmail.com" and smtp == "smtp.gmail.com" and sport == 587
    for k in ("EMAIL_ADDRESS", "EMAIL_PASSWORD"):
        os.environ.pop(k, None)
    get_settings.cache_clear()
