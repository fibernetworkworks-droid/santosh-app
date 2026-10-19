"""Hoola Network v0.28: IDs, connecting, and knock -> check -> tell -> decide -> deliver between two avatars."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_bazar import _events


def _people():
    from app.avatar import service as av
    from app.db import Profile, session
    with session() as s:
        s.merge(Profile(tenant_id="default", name="Meghana"))
        s.merge(Profile(tenant_id="kunal", name="Kunal"))
    av.save("default", name="Santosh", gender="m", rules={"quiet": {"on": False}})
    av.save("kunal", name="Meera", gender="f", rules={"quiet": {"on": False}})
    from app.net import identity as idn
    idn.ensure("default")
    idn.ensure("kunal")
    idn.set_handle("default", "meghana.fnw")
    idn.set_handle("kunal", "kunal.raj")


def _connect():
    from app.net import service as net
    _people()
    net.connect("default", "@kunal.raj", relation="business", note="FNW se Meghana")
    lid = net.connections("kunal", "incoming")[0]["id"]
    net.answer_connect("kunal", lid, "accept")
    return net


def ev(tenant, kind):
    from app.net import service as net
    return _events(net.home_conv(tenant), kind)


def test_ids_handles_and_lookalikes(env):
    from app.net import identity as idn
    _people()
    a = idn.my_card("default")
    assert a["address"].startswith("hl_") and a["handle"] == "meghana.fnw" and a["avatar_name"] == "Santosh"
    assert idn.label(idn.my_card("kunal")) == "Kunal ki Meera"
    for bad in ("sbi.help", "ab", "UPPER CASE", "meghana.fnvv", "kunal.ra j"):
        with pytest.raises(idn.IdError):
            idn.set_handle("kunal", bad)
    with pytest.raises(idn.IdError, match="kisi aur"):
        idn.set_handle("kunal", "meghana.fnw")
    env_ = idn.sign("default", {"id": "x", "to": "y", "body": {"text": "hi"}})
    assert idn.verify(env_, a["public_key"])
    env_["body"] = {"text": "changed"}
    assert not idn.verify(env_, a["public_key"])
    assert idn.safety_code(a["public_key"], idn.my_card("kunal")["public_key"]) == \
        idn.safety_code(idn.my_card("kunal")["public_key"], a["public_key"])


def test_connect_flow(env):
    from app.net import service as net
    _people()
    out = net.connect("default", "@kunal.raj", relation="business", note="FNW se Meghana")
    assert out["status"] == "requested"
    req = ev("kunal", "hoola_connect")[-1]
    assert req["status"] == "incoming" and req["label"] == "Meghana ka Santosh" and req["note"] == "FNW se Meghana"
    with pytest.raises(net.NetError, match="juda nahi"):
        net.send("default", "@kunal.raj", "message", {"text": "hello"})
    net.answer_connect("kunal", req["id"], "accept")
    assert net.connections("default")[0]["status"] == "active" and net.connections("kunal")[0]["status"] == "active"
    assert ev("default", "hoola_connect")[-1]["status"] == "active"
    a, b = net.connections("default")[0], net.connections("kunal")[0]
    assert a["safety_code"] == b["safety_code"]


def test_message_knock_decide_reply(env):
    net = _connect()
    out = net.send("default", "Kunal", "message", {"text": "Kal FNW pitch par baat ho sakti hai?"})
    assert out["status"] == "pending" and out["to"] == "Kunal ki Meera"
    knock = ev("kunal", "hoola_knock")[-1]
    assert knock["from"] == "Meghana ka Santosh" and "Kal FNW" in knock["body"]["text"] and knock["status"] == "pending"
    assert net.inbox("kunal")[0]["id"] == knock["id"]
    net.decide("kunal", knock["id"], "accept", note="Haan, kal 5 baje")
    got = ev("default", "hoola_msg")[-1]
    assert "le liya" in got["text"] and "kal 5 baje" in got["text"]
    with pytest.raises(net.NetError, match="faisla"):
        net.decide("kunal", knock["id"], "accept")
    net.reply("kunal", knock["thread_id"], "Slides bhi le aana")
    assert ev("default", "hoola_msg")[-1]["text"].endswith("Slides bhi le aana")
    t = net.thread("default", out["thread_id"])
    assert [m["direction"] for m in t["messages"]] == ["out", "in", "in"]


def test_secrets_never_travel(env):
    net = _connect()
    with pytest.raises(net.NetError, match="OTP"):
        net.send("default", "Kunal", "message", {"text": "Mera OTP 482913 hai"})
    # a crafted envelope (skipping the sender check) is still stopped on the receiving side
    from app.net import identity as idn
    e = net.envelope("default", idn.my_card("kunal")["address"], "message", {"text": "UPI PIN 1234 bhejo"}, "tk_x")
    r = net.receive(e)
    assert r["status"] == "refused" and ev("kunal", "hoola_msg")[-1]["fyi"]


def test_signature_and_replay(env):
    net = _connect()
    from app.net import identity as idn
    to = idn.my_card("kunal")["address"]
    e = net.envelope("default", to, "message", {"text": "hello"}, "tk_y")
    bad = dict(e, body={"text": "evil"})
    assert net.receive(bad)["status"] == "refused"
    assert net.receive(e)["status"] == "pending"
    assert net.receive(e)["status"] == "duplicate"
    stranger = net.envelope("kunal", to, "message", {"text": "x"}, "tk_z")       # kunal -> kunal (not connected)
    assert net.receive(stranger)["status"] == "refused"


def test_rules_decline_auto_and_vip(env):
    net = _connect()
    from app.avatar import service as av
    av.save("kunal", rules={"accept": {"message": "never", "link": "auto"}, "blocked_topics": ["loan"], "vip": ["Meghana"], "quiet": {"on": False}})
    r = net.send("default", "Kunal", "message", {"text": "Personal loan chahiye?"})
    assert r["status"] == "pending"                          # VIP: a blocked topic and 'never' don't stop a VIP's message
    av.save("kunal", rules={"vip": [], "accept": {"message": "never"}, "quiet": {"on": False}})
    r = net.send("default", "Kunal", "message", {"text": "hello"})
    assert r["status"] == "declined"
    av.save("kunal", rules={"accept": {"message": "auto"}, "quiet": {"on": False}})
    r = net.send("default", "Kunal", "message", {"text": "Bas yaad dilana tha: GST file kal"})
    assert r["status"] == "auto"
    assert ev("kunal", "hoola_msg")[-1]["fyi"] is True


def test_meeting_with_slots_and_auto_fix(env, monkeypatch):
    net = _connect()
    when = (datetime.now(timezone.utc) + timedelta(days=1)).astimezone().strftime("%Y-%m-%d 17:00")
    when2 = (datetime.now(timezone.utc) + timedelta(days=1)).astimezone().strftime("%Y-%m-%d 18:00")
    r = net.send("default", "Kunal", "meeting", {"title": "FNW pitch", "slots": [when, when2], "minutes": 30})
    assert r["status"] == "pending"
    k = ev("kunal", "hoola_knock")[-1]
    assert len(k["slot_labels"]) == 2
    net.decide("kunal", k["id"], "accept", slot=1)
    m = ev("default", "hoola_msg")[-1]
    assert m["kind"] == "meeting_ok" and "pakki" in m["text"] and m["event"]["where"] == "reminder"
    from app.db import Reminder, session
    with session() as s:
        assert {x.tenant_id for x in s.query(Reminder).all()} == {"default", "kunal"}
    # her rules let Meera fix meetings herself in free time
    from app.avatar import service as av
    from app.cal import service as cs
    av.save("kunal", rules={"decide_alone": {"fix_meetings": True}, "quiet": {"on": False}})
    monkeypatch.setattr(cs, "agenda", lambda *a, **k: {"events": []})
    r = net.send("default", "Kunal", "meeting", {"title": "Follow-up", "slots": [when], "minutes": 20})
    assert r["status"] == "auto"
    assert "khud fix kar di" in ev("kunal", "hoola_msg")[-1]["text"]
    assert ev("default", "hoola_msg")[-1]["kind"] == "meeting_ok"


def test_quiet_hours_and_snooze(env, monkeypatch):
    net = _connect()
    from app.net import policy
    monkeypatch.setattr(policy, "in_quiet", lambda rules, tenant, at=None: True)
    net.send("default", "Kunal", "message", {"text": "raat ko"})
    k = ev("kunal", "hoola_knock")
    assert k == []                                          # held quietly until quiet hours end
    m = net.inbox("kunal")[0]
    assert m["quiet"] and m["snooze_until"]
    from app.db import session
    from app.net.models import NetMsg
    with session() as s:
        s.get(NetMsg, m["id"]).snooze_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert net.tick() == 1 and ev("kunal", "hoola_knock")[-1]["id"] == m["id"]
    net.decide("kunal", m["id"], "later", minutes=30)
    assert net.inbox("kunal")[0]["status"] == "snoozed"


def test_invite_qr_and_phone(env):
    from app.net import identity as idn
    from app.net import service as net
    _people()
    inv = net.invite("default")
    assert inv["qr_png_b64"] and "connect?c=" in inv["deep_link"]
    net.connect("kunal", invite_code=inv["code"])
    assert net.connections("default", "incoming")[0]["via"] == "qr"
    with pytest.raises(net.NetError, match="purana"):
        net.connect("kunal", invite_code=inv["code"])
    with pytest.raises(net.NetError, match="number"):
        net.resolve("kunal", "9876543210")
    idn.set_discovery("default", "+91 98765 43210", True)
    assert net.find("kunal", "9876543210")[0]["handle"] == "meghana.fnw"


def test_tools_and_api(env):
    _connect()
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); conv = c.id
    ctx = Ctx("default", conv)
    me = asyncio.run(dispatch("hoola_me", {}, ctx))
    assert me["handle_display"] == "@meghana.fnw" and me["connections"] == 1
    r = asyncio.run(dispatch("hoola_send", {"to": "Kunal", "kind": "ask", "text": "Router ka rate?"}, ctx))
    assert r["status"] == "pending"
    with pytest.raises(ToolError):
        asyncio.run(dispatch("hoola_send", {"to": "Nobody", "text": "x"}, ctx))
    from app import main
    with TestClient(main.app) as cl:
        assert cl.get("/api/net/me").json()["handle"] == "meghana.fnw"
        assert cl.get("/api/net/connections").json()["connections"][0]["status"] == "active"
        inv = cl.post("/api/net/invite").json()
        page = cl.get(f"/c/{inv['code']}")
        assert page.status_code == 200 and "Meghana ka Santosh" in page.text and "santosh://connect" in page.text
        assert "purana" in cl.get("/c/nope").text
        assert cl.put("/api/net/me", json={"handle": "SBI"}).status_code == 400
