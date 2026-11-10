"""v0.706 GMAIL GEHRI JAANCH (owner: "GO DEEP IN GMAIL --- FIND ALL POSSIBLE FLAWS"): three audits of the Gmail lane;
the speed, safety and wrong-answer faults fixed here are pinned below."""
from __future__ import annotations

import httpx
import pytest

from app.mailbox import gmail
from app.mailbox.base import MailError


def _box(handler, shared=False, monkeypatch=None):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    if shared:
        monkeypatch.setattr(gmail, "_shared", lambda: client)
        return gmail.GmailBox("k", "me@x.com", lambda fresh: "tok")
    return gmail.GmailBox("k", "me@x.com", lambda fresh: "tok", client=client)


def _msg(i):
    return {"id": f"m{i}", "threadId": "t1", "labelIds": ["INBOX"], "snippet": "hello " * 60,
            "payload": {"mimeType": "text/plain", "headers": [{"name": "From", "value": f"A{i} <a{i}@x.com>"},
                                                              {"name": "Subject", "value": f"S{i}"}]}}


def test_list_runs_in_parallel_on_the_shared_client_and_says_more(monkeypatch):
    calls = []

    def h(req):
        calls.append(req.url.path)
        if req.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": f"m{i}"} for i in range(12)], "nextPageToken": "n"})
        return httpx.Response(200, json=_msg(int(req.url.path.rsplit("m", 1)[1])))
    b = _box(h, shared=True, monkeypatch=monkeypatch)
    out = b.list("promotions", limit=12)
    assert [o["id"] for o in out] == [f"m{i}" for i in range(12)]          # order kept
    assert len(calls) == 13 and b.last_more is True


def test_rate_limit_is_retried(monkeypatch):
    monkeypatch.setattr(gmail.time, "sleep", lambda s: None)
    n = {"c": 0}

    def h(req):
        n["c"] += 1
        return httpx.Response(429, json={}) if n["c"] < 3 else httpx.Response(200, json={"historyId": "5"})
    assert _box(h).profile()["historyId"] == "5" and n["c"] == 3


def test_thread_with_a_reply_message_id(monkeypatch):
    def h(req):
        p = req.url.path
        if p.endswith("/threads/reply9"):
            return httpx.Response(404, json={})
        if p.endswith("/messages/reply9"):
            return httpx.Response(200, json={"id": "reply9", "threadId": "first1"})
        if p.endswith("/threads/first1"):
            return httpx.Response(200, json={"id": "first1", "messages": []})
        return httpx.Response(404, json={})
    out = _box(h).thread("reply9")
    assert isinstance(out, dict)
    _box(h).thread("th:first1")          # a th: ref no longer 404s


def test_history_sends_the_page_token():
    seen = {}

    def h(req):
        seen.update(dict(req.url.params))
        return httpx.Response(200, json={})
    _box(h).history("100", page_token="p2")
    assert seen.get("pageToken") == "p2"


def test_primary_category():
    seen = {}

    def h(req):
        import json
        seen.update(json.loads(req.content or b"{}"))
        return httpx.Response(200, json={})
    _box(h).set_category(["m1"], "primary")
    assert "CATEGORY_PERSONAL" in seen.get("addLabelIds", [])


def test_thread_trash_needs_a_card(env):
    from app.mailbox import service as ms
    with pytest.raises(MailError) as e:
        ms.thread_act("default", ["google~th:t1"], "trash")
    assert "email_delete" in str(e.value)


def test_slim_rows():
    from app.mailbox import service as ms
    big = {"emails": [{"id": "g~1", "to": "me", "message_id": "<x@y>", "account": "a", "starred": False,
                       "important": False, "unread": True, "snippet": "z" * 300, "subject": "Hi"}]}
    r = ms.slim(big)["emails"][0]
    assert "to" not in r and "message_id" not in r and "starred" not in r and r["unread"] is True
    assert len(r["snippet"]) <= 141


def test_near_miss_address(env):
    from app.agent import email_tools as et
    from app.mailbox import contacts
    contacts.learn("default", [("Kunal", "kunaltlgt23@gmail.com")], 1.0)
    warn = et._near_miss("default", "kunaltelgote23@gmail.com")
    assert warn and "kunaltlgt23@gmail.com" in warn[0]
    assert et._near_miss("default", "kunaltlgt23@gmail.com") == []


def test_replace_id_cancels_the_old_card(env):
    from app.agent import email_tools as et
    from app.agent.tools import Ctx
    from app.db import Conversation, EmailDraft, session
    with session() as s:
        s.add(Conversation(id="c1", tenant_id="default"))
        s.add(EmailDraft(id="eml_old", tenant_id="default", conversation_id="c1", to_addr="a@x.com", subject="s",
                         body="b", status="pending"))
    et._cancel_pending(Ctx(tenant_id="default", conversation_id="c1"), "eml_old")
    with session() as s:
        assert s.get(EmailDraft, "eml_old").status == "cancelled"


def test_wiring_pins():
    src = open("app/mailbox/service.py").read()
    assert "getaddresses" in src and 'bcc=mime.dec(orig.get("Bcc"))' in src
    et = open("app/agent/email_tools.py").read()
    assert "acct = box.key" in et and "replace_id" in et and "ms.slim(" in et
