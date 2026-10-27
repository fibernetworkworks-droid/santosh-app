"""v0.158 chat in order + cards where she looks + call-scoped cards + self-check (and the 3D theatre gone)."""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

KEY = "owner-key-for-chat-tests"


@pytest.fixture
def api(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import convs, main
    convs._CACHE.clear()
    with TestClient(main.app) as c:
        yield c, get_settings()
    get_settings.cache_clear()


H = {"Authorization": f"Bearer {KEY}"}


def _conv(tenant):
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


def test_5000_events_timeline_in_order_cards_once_latest_state(api):
    c, st = api
    from app.events import bus, timeline, head
    t = st.tenant_id
    conv = _conv(t)
    # an approval that starts early and still waits at the end (must not be lost above the page)
    bus.publish(conv, "bazar_approval", {"id": "ap1", "title": "Bijli bill", "status": "pending"})
    expected = []
    for i in range(1200):
        bus.publish(conv, "step", {"tool": "x", "state": "running", "id": f"s{i}"})       # live-only noise
        bus.publish(conv, "typing", {"on": True})
        bus.publish(conv, "work", {"id": f"w{i}", "phase": "start"})
        ev = bus.publish(conv, "message", {"role": "user" if i % 2 else "assistant", "text": f"m{i}"})
        expected.append(("message", f"m{i}"))
        if i % 50 == 0:   # a board card that updates many times stays ONE card, in its latest state, at its first place
            bus.publish(conv, "app_board", {"id": f"A{i}", "pct": 0})
            expected.append(("app_board", f"A{i}"))
        if i % 50 == 10:
            bus.publish(conv, "app_board", {"id": f"A{i - 10}", "pct": 100, "status": "ready"})
    tl = timeline(conv, t, 60)
    evs = tl["events"]
    ids = [e["id"] for e in evs]
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    assert evs[0]["kind"] == "bazar_approval" and evs[0]["payload"]["status"] == "pending"    # waiting card kept
    page = [e for e in evs[1:]]
    assert len(page) == 60 and not any(e["kind"] in ("step", "typing", "work") for e in evs)
    names = [(e["kind"], e["payload"].get("text") or e["payload"].get("id")) for e in page]
    assert names == expected[-60:]
    boards = [e for e in page if e["kind"] == "app_board"]
    assert boards and all(b["payload"]["pct"] == 100 for b in boards[:-1])
    assert tl["has_more"] and tl["last_event_id"] >= ev["id"]
    # older page goes back in order without overlap
    older = timeline(conv, t, 60, before=tl["before"])["events"]
    assert older[-1]["id"] < page[0]["id"] and [e["id"] for e in older] == sorted(e["id"] for e in older)
    assert [(e["kind"], e["payload"].get("text") or e["payload"].get("id")) for e in older] == expected[-120:-60]
    h = head(conv, t, 40)
    assert h["ids"] == [e["id"] for e in page[-40:]]
    # the API gives the same
    r = c.get(f"/api/conversations/{conv}/timeline?limit=60", headers=H).json()
    assert [e["id"] for e in r["events"]] == ids


def test_cards_from_other_chats_reach_the_chat_she_reads(api):
    c, st = api
    from app.events import bus, timeline
    t = st.tenant_id
    phone = _conv(t)
    bus.publish(phone, "message", {"role": "user", "text": "app bana do"})
    console = _conv(t)                                   # the console made a newer chat
    bus.publish(console, "app_board", {"id": "A-1", "status": "ready"})
    bus.publish(console, "bazar_approval", {"id": "ap9", "status": "pending", "title": "Order"})
    bus.publish(console, "gyaan_sources", {"id": "g1"})   # answer sources stay in their own chat
    bus.publish(console, "message", {"role": "assistant", "text": "console reply"})
    other = _conv("someone-else")
    bus.publish(other, "app_board", {"id": "X-1"})       # never another owner's
    kinds = [(e["kind"], e["conv"]) for e in timeline(phone, t)["events"]]
    assert ("app_board", console) in kinds and ("bazar_approval", console) in kinds
    assert not any(k == "gyaan_sources" or (k == "message" and cv == console) for k, cv in kinds)
    assert not any(cv == other for _, cv in kinds)
    # live catch-up also brings them (the reconnecting phone)
    back = bus.backlog(phone, 0, 500, t)
    assert any(e["kind"] == "app_board" and e["conv"] == console for e in back)
    w = c.get("/api/chat/waiting", headers=H).json()["waiting"]
    assert any(x["kind"] == "bazar_approval" for x in w)


def test_live_fanout_and_stream_pages_until_now(api):
    c, st = api
    from app import main
    from app.events import bus
    t = st.tenant_id
    a, b = _conv(t), _conv(t)

    async def run():
        q = bus.subscribe(a, t)
        bus.publish(b, "pg_write", {"id": "W-1", "status": "pending"})       # made in chat b
        bus.publish(b, "message", {"role": "assistant", "text": "only in b"})
        got = [q.get_nowait() for _ in range(q.qsize())]
        bus.unsubscribe(a, q)
        assert [g["kind"] for g in got] == ["pg_write"]
        # a phone that was away: everything after its cursor, in order, then the replay_end marker
        first = bus.publish(a, "message", {"role": "user", "text": "start"})["id"]
        for i in range(1300):
            bus.publish(a, "message", {"role": "assistant", "text": f"r{i}"})

        class Req:
            headers = {}

            async def is_disconnected(self):
                return True

        resp = await main.events(a, Req(), after=first, tenant=t)
        chunks = []
        async for ch in resp.body_iterator:
            chunks.append(ch if isinstance(ch, str) else ch.decode())
        body = "".join(chunks)
        assert body.count("data: ") == 1301 and '"replay_end"' in body and '"r1299"' in body
        main.REPLAY_MAX = 1000
        resp = await main.events(a, Req(), after=1, tenant=t)        # too far behind: told to reload in order
        body = "".join([ch if isinstance(ch, str) else ch.decode() async for ch in resp.body_iterator])
        main.REPLAY_MAX = 3000
        assert '"resync"' in body and '"replay_end"' in body
        resp = await main.events(a, Req(), after=0, tenant=t)        # fresh open: nothing replayed (timeline did it)
        body = "".join([ch if isinstance(ch, str) else ch.decode() async for ch in resp.body_iterator])
        assert body.count("data: ") == 1 and '"replay_end"' in body

    asyncio.run(run())


def test_her_chat_is_never_lost(api):
    c, st = api
    t = st.tenant_id
    first = c.get("/api/bootstrap", headers=H).json()["conversation_id"]
    assert c.post(f"/api/conversations/{first}/messages", json={"text": "pehli baat"}, headers=H).status_code == 202
    # sign-in / re-install: no saved chat id -> her chat, not a new empty one
    assert c.get("/api/bootstrap", headers=H).json()["conversation_id"] == first
    new = c.get("/api/bootstrap?new=true", headers=H).json()
    assert new["conversation_new"] and new["conversation_id"] != first
    chats = c.get("/api/conversations", headers=H).json()
    assert {x["id"] for x in chats["conversations"]} >= {first, new["conversation_id"]}
    assert chats["current"] == new["conversation_id"]
    old = [x for x in chats["conversations"] if x["id"] == first][0]
    assert old["title"] == "pehli baat"
    c.post(f"/api/conversations/{first}/open", headers=H)
    from app import convs
    assert convs.current(t) == first
    from app.net.service import home_conv
    from app.bazar import service as bz
    from app.db import session
    assert home_conv(t) == first
    with session() as s:
        assert bz.latest_conversation(s, t) == first


def test_call_tags_cards_and_learns_what_to_keep_out(api):
    c, st = api
    from app.events import CALL, bus
    t = st.tenant_id
    conv = _conv(t)

    async def tool_in_call():
        CALL.set("call-xyz")
        await asyncio.sleep(0)
        return await asyncio.to_thread(bus.publish, conv, "browser", {"session_id": "b1", "status": "running"})

    tagged = asyncio.run(tool_in_call())
    plain = bus.publish(conv, "browser", {"session_id": "b2", "status": "running"})
    assert tagged["call"] == "call-xyz" and plain["call"] is None
    from app.events import timeline
    tl = {e["payload"]["session_id"]: e for e in timeline(conv, t)["events"] if e["kind"] == "browser"}
    assert tl["b1"]["call"] == "call-xyz" and tl["b2"]["call"] is None
    for i in range(2):
        r = c.post(f"/api/voice/calls/c{i}/cards", headers=H, json={"conversation_id": conv, "cards": [
            {"kind": "seva_day", "title": "Subah", "dismissed": True},
            {"kind": "bazar", "title": "Bill", "dismissed": True},          # money: never held back
            {"kind": "operator_task", "title": "Site", "used": True, "tagged": True}]}).json()
    assert r["rules"]["hold"] == ["seva_day"]
    assert c.get("/api/voice/card_rules", headers=H).json()["hold"] == ["seva_day"]
    c.post("/api/chat/heal", headers=H, json={"reason": "missing 3", "data": {"missing": 3}})
    h = c.get("/api/chat/health", headers=H).json()
    assert h["self_fixes_7d"] == 1 and h["held_in_calls"] == ["seva_day"] and h["current"]


def test_theatre_is_gone_everywhere():
    root = Path(__file__).resolve().parents[2]
    assert not (root / "assets" / "theatre").exists() and not (root / "lib" / "ui" / "work_theatre.dart").exists()
    assert not (root / "server" / "app" / "theatre.py").exists()
    assert "assets/theatre" not in (root / "pubspec.yaml").read_text()
    for f in list((root / "lib").rglob("*.dart")) + [root / "server" / "app" / "static" / "console" / "app.js"]:
        txt = f.read_text()
        assert "WorkTheatre" not in txt and "theatre/index.html" not in txt, f
    from app import livework
    ev = livework.event("t1", "email_check", "Mail dekh raha hoon", "start", {}, None)
    assert ev["phase"] == "start" and ev["label"]
