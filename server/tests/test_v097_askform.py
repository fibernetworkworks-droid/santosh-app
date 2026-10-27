"""v0.97 Secure form card: several questions on one card; IDs into the locker; never OTP / password / card."""
import asyncio

import pytest


def _conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def _events(conv, kind):
    from app.db import Event, session
    import json
    with session() as s:
        return [e.payload if isinstance(e.payload, dict) else json.loads(e.payload)
                for e in s.query(Event).filter_by(conversation_id=conv, kind=kind).all()]


FIELDS = [{"name": "naam", "label": "Yatri ka naam", "kind": "text", "value": "Meghana"},
          {"name": "tareekh", "label": "Kis din", "kind": "date"},
          {"name": "class", "label": "Class", "kind": "choice", "options": ["SL", "3A", "2A"]},
          {"name": "mobile", "label": "Mobile", "kind": "phone"},
          {"name": "aadhaar", "label": "Aadhaar number", "kind": "id", "required": False}]


def test_tool_sends_a_card_and_refuses_secret_fields(env):
    from app.agent.tools import Ctx, ToolError, dispatch
    conv = _conv()
    ctx = Ctx(tenant_id="default", conversation_id=conv)
    r = asyncio.run(dispatch("ask_form", {"title": "Train ticket", "why": "IRCTC booking", "fields": FIELDS}, ctx))
    assert r["status"] == "sent" and r["fields"][0] == "Yatri ka naam"
    card = _events(conv, "ask_form")[-1]
    assert card["status"] == "pending" and card["fields"][0]["value"] == "Meghana" and card["fields"][2]["options"] == ["SL", "3A", "2A"]
    for bad in ("OTP", "Login password", "Card number", "UPI PIN", "CVV"):
        with pytest.raises(ToolError, match="form mein nahi"):
            asyncio.run(dispatch("ask_form", {"title": "x", "fields": [{"label": bad}]}, ctx))
    # a postal PIN code is fine
    asyncio.run(dispatch("ask_form", {"title": "Pata", "fields": [{"label": "PIN code", "kind": "number"},
                                                                  {"label": "Shehar"}, {"label": "Gali"}]}, ctx))


def test_answers_are_checked_and_ids_go_to_the_locker(env, monkeypatch):
    from fastapi.testclient import TestClient

    from app import askform, main
    conv = _conv()
    v = askform.create("default", conv, "Train ticket", FIELDS)
    ran = []

    async def fake_turn(conversation_id, text, tenant_id=None, voice=False, context="", **k):
        ran.append((conversation_id, text, context))
        return "ok"
    monkeypatch.setattr(main, "run_turn", fake_turn)
    with TestClient(main.app) as c:
        bad = c.post(f"/api/forms/{v['id']}/answer", json={"values": {"naam": "Meghana", "tareekh": "kal", "class": "3A",
                                                                       "mobile": "98765 43210"}})
        assert bad.status_code == 400 and "tareekh" in bad.json()["detail"]
        bad = c.post(f"/api/forms/{v['id']}/answer", json={"values": {"naam": "Meghana", "tareekh": "2026-11-02",
                                                                       "class": "1A", "mobile": "9876543210"}})
        assert bad.status_code == 400 and "list" in bad.json()["detail"]
        ok = c.post(f"/api/forms/{v['id']}/answer", json={"values": {
            "naam": "Meghana", "tareekh": "2026-11-02", "class": "3A", "mobile": "+91 98765 43210",
            "aadhaar": "2345 6789 0124"}})
        assert ok.status_code == 200 and ok.json()["went_to"] == "chat"
        again = c.post(f"/api/forms/{v['id']}/answer", json={"values": {}})
        assert again.status_code == 400
    conv_id, shown, context = ran[0]
    assert conv_id == conv and shown == "Form bhara: Train ticket"
    assert "- Class: 3A" in context and "- Mobile: 9876543210" in context
    assert "2345 6789 0124" not in context and "234567890124" not in context        # the model never sees the number
    assert "{id:" in context or "[ID:" in context
    stored = askform.get("default", v["id"])["answers"]
    assert "0124" in stored["aadhaar"] and "2345" not in stored["aadhaar"]


def test_cancel_and_live_call_route(env, monkeypatch):
    from fastapi.testclient import TestClient

    from app import askform, main, voice
    conv = _conv()
    v = askform.create("default", conv, "Pata", [{"label": "Shehar"}, {"label": "Gali"}, {"label": "PIN code", "kind": "number"}])
    told = []
    monkeypatch.setattr(voice, "inject", lambda c, t: told.append((c, t)) or 1)
    monkeypatch.setattr(main, "run_turn", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no chat turn in a call")))
    with TestClient(main.app) as c:
        r = c.post(f"/api/forms/{v['id']}/answer", json={"values": {"shehar": "Akola", "gali": "Khanapur Ves", "pin_code": "444101"}})
        assert r.json()["went_to"] == "call" and "Akola" in told[0][1]
        v2 = askform.create("default", conv, "Aur", [{"label": "A"}, {"label": "B"}, {"label": "C"}])
        assert c.post(f"/api/forms/{v2['id']}/cancel").json()["status"] == "cancelled"
        assert "band kiya" in told[-1][1]
