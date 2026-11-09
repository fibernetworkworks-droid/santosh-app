"""v0.646 ALAG CALL, EK YAAD (owner: "KEEP CHAT AND VOICE CALL SECTION SEPERATE BUT SHARE A MEMORY" -> GO on
docs/CALL_CHAT_SPLIT_PLAN.md): a call gets its own record, the chat stays clean, both share one memory, and
nothing she already heard on a call becomes a notification."""
from __future__ import annotations

import inspect
import types

from app.db import Conversation, session

T = "default"


def _chat(cid: str, project: str | None = None, incognito: bool | None = None) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, project_id=project, incognito=incognito))
    return cid


def _clear():
    from app import callconv
    callconv._KIND.clear()
    callconv._ORIGIN.clear()


def test_call_record_shares_the_chats_scope(env):
    from app import callconv
    _clear()
    _chat("chatA", project="proj1", incognito=None)
    cid = callconv.open_for(T, "chatA", "")
    with session() as s:
        c = s.get(Conversation, cid)
        assert (c.kind, c.origin_conv, c.project_id) == ("call", "chatA", "proj1")
    assert callconv.is_call(cid) and not callconv.is_call("chatA")
    assert callconv.origin_of(cid) == "chatA" and callconv.chat_of(cid) == "chatA" and callconv.chat_of("chatA") == "chatA"
    # a call started while she was looking at a call record belongs to that record's chat
    again = callconv.open_for(T, cid, "")
    assert callconv.origin_of(again) == "chatA"
    from app.fence import chats_in
    assert cid in chats_in(T, "chatA")            # same memory scope: facts / diary / jobs shared by the fence


def test_incognito_chat_gives_an_incognito_call(env):
    from app import callconv
    from app.fence import is_incognito
    _clear()
    _chat("secret", incognito=True)
    cid = callconv.open_for(T, "secret", "")
    assert is_incognito(cid)


def test_call_records_stay_out_of_the_chat_list_and_focus(env):
    from app import callconv, chats, convs
    _clear()
    _chat("chatB")
    cid = callconv.open_for(T, "chatB", "")
    from app.agent.santosh import _save
    _save(cid, "user", "[Voice call] mail check karo", display="mail check karo")
    ids = [c["id"] for c in chats.chat_list(T)]
    assert cid not in ids
    assert cid not in [c["id"] for c in convs.chats(T)]
    convs._CACHE.clear()
    convs.mark(T, "chatB")
    convs._CACHE.clear()
    convs.mark(T, cid)                            # a call record is never "the chat she is in"
    assert convs.current(T) == "chatB"


def test_call_notes_live_on_the_chat_so_the_next_call_hears_them(env):
    from app import callconv, yaad
    _clear()
    _chat("chatC")
    first = callconv.open_for(T, "chatC", "")
    yaad.note_call_followup(first, T, "pichhli call ka kaam ho gaya")
    nxt = callconv.open_for(T, "chatC", "")
    assert yaad.take_call_followup(nxt) == "pichhli call ka kaam ho gaya"


def test_memory_both_ways(env):
    from app import callconv
    from app.agent.santosh import _save
    _clear()
    _chat("chatD")
    _save("chatD", "user", "kal ki meeting 4 baje hai", display="kal ki meeting 4 baje hai")
    _save("chatD", "assistant", [{"type": "text", "text": "Theek hai"}], display="Theek hai")
    cid = callconv.open_for(T, "chatD", "")
    blk = callconv.chat_block(cid)                # chat -> call
    assert "RECENT IN THE CHAT" in blk and "4 baje" in blk
    assert callconv.chat_block("chatD") == ""     # a chat turn does not read itself this way
    callconv.save_summary(cid, "📞 Call ka hisaab (3 min): Sharma ji ko mail\nHo gaya: mail bheja", 180)
    with session() as s:
        c = s.get(Conversation, cid)
        assert c.title == "📞 Sharma ji ko mail" and c.call_seconds == 180
    rb = callconv.recent_block(T, "chatD")        # call -> chat
    assert "RECENT CALLS" in rb and "Sharma ji ko mail" in rb
    assert callconv.recent_block(T, cid) == ""    # a call record's own turns do not list calls
    rows = callconv.recent(T)
    assert rows[0]["id"] == cid and rows[0]["seconds"] == 180


def test_recent_calls_respect_the_session_fence(env):
    from app import callconv
    _clear()
    _chat("work", project="clientX")
    _chat("home")
    cid = callconv.open_for(T, "work", "")
    callconv.save_summary(cid, "📞 Call ka hisaab (1 min): client X quote", 60)
    assert "client X" in callconv.recent_block(T, "work")
    assert callconv.recent_block(T, "home") == ""   # a general chat never recalls a Session's call


def test_brain_turn_reads_the_chat_and_chat_turn_reads_calls():
    from app.agent import santosh
    src = inspect.getsource(santosh._brain_memory)
    assert '("chat", lambda: _callconv.chat_block(conversation_id))' in src
    # v0.648: the chat reads recent calls through the diary's call section (the separate block was a duplicate)
    assert "_callconv.recent_block, tenant_id, conversation_id" not in inspect.getsource(santosh)


def test_no_notification_for_what_she_heard_on_a_call(env, monkeypatch):
    from app import callconv, push, voice
    _clear()
    _chat("chatE")
    cid = callconv.open_for(T, "chatE", "")
    monkeypatch.setattr(voice, "ACTIVE", {cid: [object()], "chatE": [object()]})
    assert push._heard_on_call(cid, "message") is True       # the call's spoken answer
    assert push._heard_on_call(cid, "bazar_approval") is True  # a card on the live call's screen
    assert push._heard_on_call("chatE", "bazar_approval") is False   # a card made in the chat still notifies
    monkeypatch.setattr(voice, "ACTIVE", {})
    assert push._heard_on_call(cid, "message") is False      # the call ended: a late result IS news


def test_a_split_call_is_live_under_both_keys(env, monkeypatch):
    from app import callconv, voice
    _clear()
    _chat("chatF")
    cid = callconv.open_for(T, "chatF", "")
    fake = types.SimpleNamespace(ctx=types.SimpleNamespace(conversation_id=cid), call_id="call123")
    monkeypatch.setattr(voice, "ACTIVE", {})
    me = (None, fake)
    fake._live_keys = types.MethodType(voice.Call._live_keys, fake)
    voice.Call._register(fake, me)
    assert voice.ACTIVE[cid] == [me] and voice.ACTIVE["chatF"] == [me]
    with session() as s:
        assert s.get(Conversation, cid).call_id == "call123"
    voice.Call._unregister(fake, me)
    assert voice.ACTIVE[cid] == [] and voice.ACTIVE["chatF"] == []


def test_the_socket_splits_only_when_the_phone_asks():
    from app import main
    src = inspect.getsource(main.voice_ws)
    assert 'split == "1" and st.call_split' in src and "_cc.open_for, tenant, conv" in src
    assert "_cc.chat_of(call.conv) != _cc.chat_of(conv)" in src   # resume matches the chat behind the record
    from app.config import Settings
    assert Settings().call_split is True


def test_receipt_stays_on_the_call_record():
    from app import callreceipt, events
    assert "call_receipt" in events.LOCAL_KINDS
    assert "callconv.save_summary(conv" in inspect.getsource(callreceipt.make)


def test_calls_route(env):
    from fastapi.testclient import TestClient
    from app import callconv
    from app.config import get_settings
    from app.main import app
    _clear()
    _chat("chatG")
    cid = callconv.open_for(T, "chatG", "")
    key = get_settings().api_key
    h = {"Authorization": f"Bearer {key}"} if key else {}
    with TestClient(app) as cl:
        r = cl.get("/api/calls", headers=h)
        assert r.status_code == 200 and r.json()["calls"][0]["id"] == cid
        assert cid not in [c["id"] for c in cl.get("/api/conversations", headers=h).json()["conversations"]]


def test_a_split_call_end_to_end_keeps_the_chat_clean(env, monkeypatch):
    """A real call over the socket (fake Gemini): with split=1 the words and the tool land on the call record, the
    chat gets nothing, the phone still gets its alarm on the chat's live stream, and the record is in Calls."""
    import contextlib
    import json
    from fastapi.testclient import TestClient
    from app import callconv, main, voice
    from app.db import DeviceAction, Message
    from tests.test_voice import FakeSession, make_turns
    _clear()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from app.config import get_settings
    get_settings.cache_clear()
    fake = FakeSession(make_turns())

    @contextlib.asynccontextmanager
    async def fake_connect(config):
        yield fake

    monkeypatch.setattr(voice, "connector", fake_connect)
    with TestClient(main.app) as c:
        chat = c.post("/api/conversations").json()["id"]
        events = []
        with c.websocket_connect(f"/api/voice/ws?conv={chat}&voice=Achird&lang=hi-IN&split=1") as ws:
            ws.send_bytes(b"\x00\x01" * 320)
            while True:
                m = ws.receive()
                if m.get("text"):
                    ev = json.loads(m["text"])
                    events.append(ev)
                    if ev["type"] == "turn_done" and sum(1 for e in events if e["type"] == "turn_done") == 2:
                        break
            ws.send_text(json.dumps({"type": "end"}))
        ready = events[0]
        rec = ready["conv"]
        assert ready["type"] == "ready" and rec != chat and callconv.origin_of(rec) == chat
        listed = [x["id"] for x in c.get("/api/calls").json()["calls"]]
        assert rec in listed
        assert rec not in [x["id"] for x in c.get("/api/conversations").json()["conversations"]]
    with session() as s:
        chat_rows = [(m.role, m.display) for m in s.query(Message).filter_by(conversation_id=chat)]
        in_chat = sum(1 for r, d in chat_rows if r == "user" or "alarm" in (d or "") or "ek second" in (d or ""))
        in_call = [m.display for m in s.query(Message).filter_by(conversation_id=rec)]
        assert s.query(DeviceAction).filter_by(conversation_id=rec, type="set_alarm").count() == 1
        assert s.get(Conversation, rec).call_id == ready["call_id"]
    assert in_chat == 0, chat_rows                            # the chat stays the chat (only its own greeting)
    assert "Kal subah saat baje ka alarm laga do" in in_call   # the call's words are on its own record


def test_an_old_phone_without_split_keeps_the_call_on_the_chat():
    src = inspect.getsource(__import__("app.main", fromlist=["x"]).voice_ws)
    assert src.index('split == "1"') < src.index("v.Call(ws, conv")
