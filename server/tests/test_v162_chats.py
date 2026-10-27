"""v0.162 Many chats (CHAT_SESSIONS): one-query list with pin / archive / delete / rename, search that finds a word in a
2-week-old chat with the event to jump to, Edit and Dobara as branches that switch without losing anything, two chats
working at once, one account-wide stream, auto titles, /console/c/<id>."""
import asyncio
from types import SimpleNamespace
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.test_v161_stream import KEY, StreamingClaude, _text

H = {"Authorization": f"Bearer {KEY}"}


@pytest.fixture
def cs(env, monkeypatch):
    monkeypatch.setenv("CHAT_SESSIONS", "true")
    monkeypatch.setenv("CONSOLE_STREAM", "true")
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    with TestClient(main.app) as c:
        yield c


def _say(c, conv, text, brain):
    from app.agent import set_client
    set_client(brain)
    r = c.post(f"/api/conversations/{conv}/messages", json={"text": text}, headers=H)
    assert r.status_code == 202, r.text


def _replies(c, conv):
    tl = c.get(f"/api/conversations/{conv}/timeline", headers=H).json()
    msgs = [(e["payload"]["role"], e["payload"]["text"].strip()) for e in tl["events"] if e["kind"] == "message"
            and e["payload"].get("source") != "greeting"]
    return msgs, tl


def _history(conv):
    from app.agent.santosh import _load_history
    return json.dumps(_load_history(conv), ensure_ascii=False)


def test_list_pin_archive_rename_delete(cs):
    c = cs
    a = c.post("/api/conversations", headers=H).json()["id"]
    b = c.post("/api/conversations", headers=H).json()["id"]
    d = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, a, "pehli chat ka sawaal", StreamingClaude([[_text(["Jawab A"])]]))
    _say(c, b, "doosri chat ka sawaal", StreamingClaude([[_text(["Jawab B"])]]))
    lst = c.get("/api/conversations", headers=H).json()["conversations"]
    assert [x["id"] for x in lst][:2] == [b, a]                       # newest activity first
    assert lst[0]["title"] == "doosri chat ka sawaal" and lst[0]["busy"] is False and lst[0]["messages"] == 1
    assert c.patch(f"/api/conversations/{a}", json={"pinned": True, "title": "  GST   ka kaam "}, headers=H).status_code == 200
    lst = c.get("/api/console/conversations", headers=H).json()["conversations"]
    assert lst[0]["id"] == a and lst[0]["pinned"] and lst[0]["title"] == "GST ka kaam"
    assert c.patch(f"/api/conversations/{b}", json={"archived": True}, headers=H).json()["archived"] is True
    ids = [x["id"] for x in c.get("/api/conversations", headers=H).json()["conversations"]]
    assert b not in ids and a in ids
    assert [x["id"] for x in c.get("/api/conversations?archived=true", headers=H).json()["conversations"]] == [b]
    assert c.delete(f"/api/conversations/{d}", headers=H).json()["deleted"] is True
    assert d not in [x["id"] for x in c.get("/api/conversations", headers=H).json()["conversations"]]
    assert c.get(f"/api/conversations/{d}/timeline", headers=H).status_code == 404
    from app.db import Conversation, session
    with session() as s:                                               # soft delete: the row is still there
        assert s.get(Conversation, d).deleted is True
    # the list is one query, not 2 per chat
    from app import chats
    from sqlalchemy import event as saev
    from app.db import _engine
    n = {"q": 0}

    def count(*a, **k):
        n["q"] += 1
    saev.listen(_engine, "before_cursor_execute", count)
    try:
        for _ in range(5):
            c.post("/api/conversations", headers=H)
        n["q"] = 0
        chats.chat_list("default")
    finally:
        saev.remove(_engine, "before_cursor_execute", count)
    assert n["q"] <= 3                                                 # list + "current chat" lookups, not per chat


def test_search_finds_a_word_from_a_two_week_old_chat(cs):
    c = cs
    old = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, old, "Sharma ji ka kiraya agreement kab khatam hoga?", StreamingClaude([[_text(["Agreement 31 March ko."])]]))
    from app.db import Conversation, Event, Message, session
    with session() as s:
        two_weeks = func.datetime("now", "-14 days")
        for m in s.scalars(select(Message).where(Message.conversation_id == old)).all():
            m.created_at = m.created_at - timedelta(days=14)
        for e in s.scalars(select(Event).where(Event.conversation_id == old)).all():
            e.created_at = e.created_at - timedelta(days=14)
        s.get(Conversation, old).last_at = None
    new = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, new, "aaj ka mausam?", StreamingClaude([[_text(["Dhoop hai."])]]))
    hits = c.get("/api/conversations/search?q=agreement", headers=H).json()["results"]
    mine = [h for h in hits if h["conversation_id"] == old]
    assert mine and all(h["event_id"] > 0 for h in mine)
    user_hit = next(h for h in mine if h["role"] == "user")
    sn = user_hit["snippet"].replace("<<", "").replace(">>", "")   # v0.178: FTS snippets carry <<marks>>
    assert "kiraya agreement" in sn and user_hit["title"].startswith("Sharma ji")
    tl = c.get(f"/api/conversations/{old}/timeline", headers=H).json()
    assert user_hit["event_id"] in [e["id"] for e in tl["events"]]       # the console can jump to it
    assert c.get("/api/conversations/search?q=a", headers=H).json()["results"] == []


def test_edit_makes_a_branch_and_switching_loses_nothing(cs):
    c = cs
    conv = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, conv, "Pune ka mausam?", StreamingClaude([[_text(["Pune mein baarish."])]]))
    _say(c, conv, "aur kal?", StreamingClaude([[_text(["Kal bhi baarish."])]]))
    msgs, tl = _replies(c, conv)
    first_user = next(e for e in tl["events"] if e["kind"] == "message" and e["payload"]["role"] == "user")
    from app.db import Message, session
    with session() as s:
        rows_before = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == conv))
    from app.agent import set_client
    set_client(StreamingClaude([[_text(["Mumbai mein dhoop."])]]))
    r = c.post(f"/api/conversations/{conv}/edit", json={"event_id": first_user["id"], "text": "Mumbai ka mausam?"}, headers=H)
    assert r.status_code == 202, r.text
    g = r.json()["group"]
    msgs, tl = _replies(c, conv)
    assert msgs == [("user", "Mumbai ka mausam?"), ("assistant", "Mumbai mein dhoop.")]     # everything after it moved too
    br = tl["branches"]
    assert br == [{"id": g, "kind": "edit", "anchor": first_user["id"], "active": 1, "count": 2, "at": r.json()["event_id"]}]
    h = _history(conv)
    assert "Mumbai ka mausam" in h and "Pune" not in h and "Kal bhi" not in h
    # back to version 1: exactly as it was, and the model's history with it
    assert c.post(f"/api/conversations/{conv}/branch", json={"group": g, "index": 0}, headers=H).json()["active"] == 0
    msgs, tl = _replies(c, conv)
    assert msgs == [("user", "Pune ka mausam?"), ("assistant", "Pune mein baarish."), ("user", "aur kal?"),
                    ("assistant", "Kal bhi baarish.")]
    h = _history(conv)
    assert "Pune ka mausam" in h and "Kal bhi baarish" in h and "Mumbai" not in h
    # carry on in version 1, then flip to 2 and back: nothing lost anywhere
    _say(c, conv, "shukriya", StreamingClaude([[_text(["Swagat hai."])]]))
    c.post(f"/api/conversations/{conv}/branch", json={"group": g, "index": 1}, headers=H)
    assert _replies(c, conv)[0] == [("user", "Mumbai ka mausam?"), ("assistant", "Mumbai mein dhoop.")]
    c.post(f"/api/conversations/{conv}/branch", json={"group": g, "index": 0}, headers=H)
    assert [m[1] for m in _replies(c, conv)[0]][-2:] == ["shukriya", "Swagat hai."]
    with session() as s:
        rows_after = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == conv))
        parents = s.scalars(select(Message.parent_id).where(Message.conversation_id == conv,
                                                            Message.parent_id.is_not(None))).all()
    assert rows_after > rows_before and len(parents) == 1                # rows only ever added; the edit knows its parent
    # the phone's self-check agrees with the timeline (no reload loops)
    head = c.get(f"/api/conversations/{conv}/timeline/head", headers=H).json()
    assert head["ids"][-4:] == [e["id"] for e in _replies(c, conv)[1]["events"]][-4:]


def test_retry_is_a_branch_with_arrows(cs):
    c = cs
    conv = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, conv, "ek shayari", StreamingClaude([[_text(["Pehli shayari."])]]))
    from app.agent import set_client
    set_client(StreamingClaude([[_text(["Doosri shayari."])]]))
    assert c.post(f"/api/conversations/{conv}/retry", headers=H).status_code == 202
    msgs, tl = _replies(c, conv)
    assert msgs == [("user", "ek shayari"), ("assistant", "Doosri shayari.")]
    (b,) = tl["branches"]
    assert b["kind"] == "retry" and b["count"] == 2 and b["active"] == 1
    c.post(f"/api/conversations/{conv}/branch", json={"group": b["id"], "index": 0}, headers=H)
    assert _replies(c, conv)[0] == [("user", "ek shayari"), ("assistant", "Pehli shayari.")]
    assert "Pehli shayari" in _history(conv) and "Doosri" not in _history(conv)


def test_two_chats_work_at_once_and_both_finish(env, monkeypatch):
    monkeypatch.setenv("CHAT_SESSIONS", "true")
    monkeypatch.setenv("CONSOLE_STREAM", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import run_turn, set_client
    from app.db import Conversation, session
    from app.events import bus
    from app import chats
    with session() as s:
        a, b = Conversation(tenant_id="default"), Conversation(tenant_id="default")
        s.add_all([a, b])
        s.flush()
        a, b = a.id, b.id
    from tests.test_v161_stream import _Stream

    class ByQuestion:   # each chat gets its own answer whatever order the two turns reach the brain in
        def __init__(self):
            self.messages = SimpleNamespace(stream=self._stream, create=self._create)

        def _blocks(self, kw):
            c = kw["messages"][-1]["content"]        # her own words are the last text (memory blocks come first)
            asked = c if isinstance(c, str) else [b.get("text", "") for b in c if b.get("type") == "text"][-1]
            who = "a" if asked.strip().endswith("chat A") else "b"
            return [_text([f"{who}{i} " for i in range(30)])]

        def _stream(self, **kw):
            return _Stream(self._blocks(kw), 0.02)

        async def _create(self, **kw):
            return SimpleNamespace(content=[{"type": "text", "text": "ok"}], stop_reason="end_turn")
    set_client(ByQuestion())

    async def go():
        q = bus.subscribe_account("default")
        ta = asyncio.ensure_future(run_turn(a, "chat A", tenant_id="default"))
        await asyncio.sleep(0.15)
        busy = {x["id"]: x["busy"] for x in chats.chat_list("default")}
        tb = asyncio.ensure_future(run_turn(b, "chat B", tenant_id="default"))
        out = await asyncio.gather(ta, tb)
        evs = []
        while not q.empty():
            evs.append(q.get_nowait())
        bus.unsubscribe_account("default", q)
        return out, busy, evs

    (ra, rb), busy, evs = asyncio.run(go())
    assert busy[a] is True and busy[b] is False
    assert ra.startswith("a0") and rb.startswith("b0") and ra.strip().endswith("a29") and rb.strip().endswith("b29")
    convs_seen = {e["conv"] for e in evs if e["kind"] == "delta"}
    assert convs_seen == {a, b}                                         # one account stream carries both live
    assert {e["conv"] for e in evs if e["kind"] == "typing"} == {a, b}  # busy badges for both


def test_auto_title_page_route_config_and_switch_off(cs, monkeypatch):
    c = cs
    assert c.get("/api/console/config").json()["sessions"] is True
    page = c.get("/console/c/conv_anything")
    assert page.status_code == 200 and "Hoola Console" in page.text and "frame-ancestors 'none'" in page.headers["content-security-policy"]
    from app.agent import pakka
    asked = []

    async def fake_ask(system, text, settings):
        asked.append(text)
        return '"Pune ka mausam aaj."'
    monkeypatch.setattr(pakka, "_ask", fake_ask)
    conv = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, conv, "Pune ka mausam kaisa hai?", StreamingClaude([[_text(["Baarish hai."])]]))
    from app import chats
    t = asyncio.run(chats.auto_title("default", conv)) or next(
        x["title"] for x in c.get("/api/conversations", headers=H).json()["conversations"] if x["id"] == conv)
    assert t == "Pune ka mausam aaj" and asked and "Pune ka mausam kaisa hai?" in asked[0]
    c.patch(f"/api/conversations/{conv}", json={"title": "Mera naam"}, headers=H)
    assert asyncio.run(chats.auto_title("default", conv)) == ""         # never overwrites her title
    # switch off: the new endpoints are gone, the old list works as before
    monkeypatch.setenv("CHAT_SESSIONS", "false")
    monkeypatch.setenv("CONSOLE_V2", "false")   # v0.170 CONSOLE_V2 (default on) turns sessions on by itself
    from app.config import get_settings
    get_settings.cache_clear()
    assert c.get("/api/conversations/search?q=pune", headers=H).status_code == 404
    assert c.patch(f"/api/conversations/{conv}", json={"pinned": True}, headers=H).status_code == 404
    assert c.get("/api/console/stream", headers=H).status_code == 404
    assert c.get("/api/conversations", headers=H).status_code == 200
