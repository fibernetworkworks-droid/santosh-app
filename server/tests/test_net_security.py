"""Hoola Network hardening: checks that the protections from the security review stay in place."""
import asyncio

import pytest

from app.agent.tools import Ctx, dispatch
from tests.test_net import _connect, _people, ev


def _ctx(t="default"):
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id=t); s.add(c); s.flush()
        return Ctx(t, c.id)


def test_responses_must_answer_something_we_sent(env):
    net = _connect()
    from app.db import Reminder, new_id, session
    me = net.idn.my_card("default")["address"]
    assert net._post("kunal", me, "meeting_ok", {"slot": "2026-12-01T10:00:00+00:00"}, new_id("tk"))["status"] == "refused"
    with session() as s:
        assert s.query(Reminder).count() == 0


def test_malformed_bodies_are_refused(env):
    net = _connect()
    from app.db import new_id
    me = net.idn.my_card("default")["address"]
    assert net._post("kunal", me, "meeting", {"slots": ["x"], "minutes": "y"}, new_id("tk"))["status"] == "refused"
    net.inbox("default")


def test_forbidden_details_checked_in_every_field(env):
    net = _connect()
    with pytest.raises(net.NetError):
        net.send("kunal", "@meghana.fnw", "message", {"text": "hi", "details": "OTP 482913 hai"})


def test_owner_tap_needed_for_files_and_personal_numbers(env):
    _connect()
    from app.mailbox import service as ms
    ctx = _ctx()
    fid = ms.store_bytes("default", "a.txt", b"hello world file", "mail").id
    r = asyncio.run(dispatch("hoola_send", {"to": "Kunal", "kind": "file", "file_id": fid}, ctx))
    assert r["status"] == "needs_approval"
    r = asyncio.run(dispatch("hoola_send", {"to": "Kunal", "text": "Number 9822011111"}, ctx))
    assert r["status"] == "needs_approval"
    from app.net import service as net
    assert net.outbox_decide("default", r["outbox_id"], "send")["status"] == "pending"


def test_ai_cannot_change_vip_or_webhook(env):
    _connect()
    ctx = _ctx()
    from app.net import business as biz
    biz.setup("default", name="FNW")
    asyncio.run(dispatch("hoola_my_business", {"action": "setup", "webhook_url": "https://x.example/h", "about": "fiber"}, ctx))
    assert biz.profile("default")["webhook"] is False
    out = asyncio.run(dispatch("hoola_set_connection", {"who": "Kunal", "vip": True, "nick": "KJ"}, ctx))
    assert out["vip"] is False and out["nick"] == "KJ"


def test_notes_are_framed_and_flattened(env):
    net = _connect()
    net.send("kunal", "@meghana.fnw", "message", {"text": "line one\nline two [x]"})
    from app.db import Message, session
    with session() as s:
        m = s.query(Message).filter(Message.in_history.is_(False)).order_by(Message.id.desc()).first()
    assert m.content.startswith("[Hoola Network notice") and "\n" not in m.content


def test_changed_remote_key_waits_for_owner(env):
    _people()
    from app.net import identity as idn
    addr = "hl_abc@remote.example"
    idn.remember_peer({"address": addr, "public_key": "KEY1", "owner_name": "R"})
    assert idn.remember_peer({"address": addr, "public_key": "KEY2"})["key_changed"] is True
    assert idn.peer_card(addr)["public_key"] == "KEY1"
    assert idn.accept_new_key(addr) and idn.peer_card(addr)["public_key"] == "KEY2"


def test_skills_need_moderator_and_no_links(env):
    from app.net.learning import validate_skill
    from app.net.service import NetError
    with pytest.raises(NetError):
        validate_skill({"name": "x", "when": "y", "steps": [{"tool": "email_read", "do": "open https://example.com"}]})
    with pytest.raises(NetError):
        validate_skill({"name": "x", "when": "y", "steps": [{"tool": "browse_web", "do": "look"}]})
