"""v0.897 EK CHAT EK JAGAH (owner: "NOW CURRENTLY ALL CHAT IS COME IN ONE SESSION. CHECK THE APP SIDE CODE FIRST"):
the phone still read every chat with the v0.158 one-chat rule - each chat's timeline + live stream also carried every
card (files, pages, approvals, drafts) of all her other chats, so every chat looked like the same one. The phone now
asks `own` (+ `calls` on the timeline): this chat and the calls made from it only, like the console since v0.227.4.
Old apps without the flag keep the old stream."""
import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def _ids(r):
    return [e["id"] for e in r.json()["events"]]


def test_own_timeline_keeps_other_chats_out_but_its_calls_in(env):
    from app import main, callconv
    from app.events import bus, calls_of
    with TestClient(main.app) as c:
        a = c.post("/api/conversations").json()["id"]
        b = c.post("/api/conversations").json()["id"]
        tenant = "default"
        from app.db import Conversation, session
        with session() as s:
            tenant = s.get(Conversation, a).tenant_id
        other = bus.publish(b, "pc_file", {"name": "b_report.pdf", "id": "f-b"})["id"]
        call = callconv.open_for(tenant, a, "call-1")
        assert calls_of(a) == [call]
        from_call = bus.publish(call, "pc_file", {"name": "made_on_the_call.pdf", "id": "f-call"})["id"]
        old = c.get(f"/api/conversations/{a}/timeline")                          # old apps: the one-chat rule
        assert other in _ids(old) and from_call in _ids(old)
        own = c.get(f"/api/conversations/{a}/timeline", params={"own": "true", "calls": "true"})
        assert other not in _ids(own)                                             # chat B's file stays in chat B
        assert from_call in _ids(own)                                             # a call made from A belongs to A
        assert own.json()["last_event_id"] >= from_call
        head = c.get(f"/api/conversations/{a}/timeline/head", params={"own": "true"}).json()
        assert other not in head["ids"] and from_call in head["ids"]
        mine_b = c.get(f"/api/conversations/{b}/timeline", params={"own": "true", "calls": "true"})
        assert other in _ids(mine_b) and from_call not in _ids(mine_b)
        # the catch-up of the own stream: the same rule
        back = [e["id"] for e in bus.backlog(a, 0, 500, tenant, True)]
        assert other not in back and from_call in back
        assert bus.last_id(a, tenant, True) >= from_call


def test_own_live_stream_hears_its_calls_not_other_chats(env):
    from app import main, callconv
    from app.events import bus

    async def run():
        with TestClient(main.app) as c:
            a = c.post("/api/conversations").json()["id"]
            b = c.post("/api/conversations").json()["id"]
            from app.db import Conversation, session
            with session() as s:
                tenant = s.get(Conversation, a).tenant_id
            call = callconv.open_for(tenant, a, "call-2")
            mine = bus.subscribe(a, tenant, own=True)
            legacy = bus.subscribe(a, tenant)
            try:
                bus.publish(b, "pc_file", {"name": "b.pdf", "id": "x1"})
                bus.publish(call, "pc_file", {"name": "call.pdf", "id": "x2"})
                await asyncio.sleep(0)
                got = []
                while not mine.empty():
                    got.append(mine.get_nowait()["payload"]["name"])
                old = []
                while not legacy.empty():
                    old.append(legacy.get_nowait()["payload"]["name"])
                assert got == ["call.pdf"]                 # chat B's file never reaches chat A on the phone
                assert "b.pdf" in old and "call.pdf" in old and old.count("call.pdf") == 1   # old apps: as before, once
            finally:
                bus.unsubscribe(a, mine)
                bus.unsubscribe(a, legacy)

    asyncio.run(run())


def test_phone_asks_for_its_own_chat_and_new_chat_lets_the_old_one_go():
    api = (ROOT / "lib/api.dart").read_text()
    assert "if (own) 'own': '1'" in api and "'own': 'true', 'calls': 'true'" in api
    assert "'n': '$n', 'own': 'true'" in api and "if (reuse) 'reuse': 'true'" in api
    state = (ROOT / "lib/state.dart").read_text()
    assert "Future<void> newChat({bool incognito = false})" in state
    assert "conversationId = null;            // from here nothing can go into the old chat" in state
    assert "if (conv != conversationId) return;   // v0.897 she moved to another chat" in state
    for f in ("lib/ui/shell/hoola_shell.dart", "lib/ui/chat/hoola_chat.dart", "lib/ui/chat_screen.dart"):
        assert "connect(fresh: true" not in (ROOT / f).read_text(), f   # every New chat button uses newChat


def test_version():
    from app import main
    assert main.APP_VERSION == "0.905.0"
