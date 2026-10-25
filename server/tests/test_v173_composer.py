"""v0.173 Composer steering (phase 3), server side: her message carries its client_id to the chat, she can take a
queued message back (it never reaches the model, the bubble leaves the chat and the exports), the turn already
running with it refuses (Rokiye is for that), and the raw truth stays in the JSON backup."""
import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

KEY = "owner-key-composer-tests"
CID = "cid-take-back-12345"


def _on(monkeypatch):
    monkeypatch.setenv("CONSOLE_V2", "true")
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture()
def _no_title(monkeypatch):
    from app.agent import pakka
    monkeypatch.setattr(pakka, "_ask", lambda *a, **k: _async("Ek sawaal"))


def _async(v):
    async def _f(*a, **k):
        return v
    return _f


def _conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def test_message_event_carries_client_id_for_steering(env, monkeypatch, _no_title):
    _on(monkeypatch)
    conv = _conv()
    from tests.test_campaign_flow import ScriptedClaude, text
    from app.agent import set_client
    set_client(ScriptedClaude([text("Jawab.")]))
    from app.main import app
    H = {"Authorization": f"Bearer {KEY}"}
    with TestClient(app) as c:
        r = c.post(f"/api/conversations/{conv}/messages", json={"text": "namaste", "client_id": "cid-echo-123456"},
                   headers=H)
        assert r.status_code == 202
        evs = c.get(f"/api/conversations/{conv}/timeline", headers=H).json()["events"]
        mine = [e for e in evs if e["kind"] == "message" and e["payload"].get("client_id")]
        assert mine and mine[0]["payload"]["client_id"] == "cid-echo-123456"


def test_takeback_hides_the_queued_message_and_the_model_never_hears_it(env, monkeypatch):
    _on(monkeypatch)
    conv = _conv()
    from app.events import bus
    bus.publish(conv, "message", {"role": "user", "text": "yeh wapas leni hai", "source": "user", "client_id": CID})
    from app.main import app
    H = {"Authorization": f"Bearer {KEY}"}
    with TestClient(app) as c:
        r = c.post(f"/api/conversations/{conv}/takeback", json={"client_id": CID}, headers=H)
        assert r.status_code == 200 and r.json()["taken"] is True
        # the story no longer shows it (default and steps=1 alike)
        for q in ({}, {"steps": "1"}):
            evs = c.get(f"/api/conversations/{conv}/timeline", headers=H, params=q).json()["events"]
            assert not [e for e in evs if e["kind"] == "message" and e["payload"].get("client_id")]
        # the Markdown export skips it; the JSON backup keeps the raw truth
        assert "yeh wapas leni hai" not in c.get(f"/api/conversations/{conv}/export", headers=H).text
        data = c.get(f"/api/conversations/{conv}/export?fmt=json", headers=H).json()
        assert any(e["kind"] == "message" and e["payload"].get("taken_back") for e in data["events"])
    # run_turn with that client_id returns at once: nothing runs, nothing is published
    from tests.test_campaign_flow import ScriptedClaude, text
    from app.agent import set_client, santosh
    brain = ScriptedClaude([text("yeh kabhi nahi aana chahiye")])
    set_client(brain)
    q = bus.subscribe(conv)
    out = asyncio.run(santosh.run_turn(conv, "yeh wapas leni hai", tenant_id="default", client_id=CID))
    while not q.empty():
        q.get_nowait()
    bus.unsubscribe(conv, q)
    assert out == "" and brain.calls == []          # the held message never reaches the model
    assert not santosh.message_running(conv, CID)   # and nothing pretends to run with it


def test_takeback_refuses_a_turn_already_running_with_it(env, monkeypatch):
    _on(monkeypatch)
    conv = _conv()
    from app.events import bus
    bus.publish(conv, "message", {"role": "user", "text": "chal padi hai", "source": "user", "client_id": CID})
    from app.agent import santosh
    from app.main import app, chat_takeback, TakebackIn
    santosh._active_msg[conv] = CID
    lock = santosh._locks[conv]

    async def _busy():
        async with lock:   # the turn holds the chat right now
            with pytest.raises(HTTPException) as ei:
                chat_takeback(conv, TakebackIn(client_id=CID), "default")
            assert ei.value.status_code == 409

    asyncio.run(_busy())
    santosh._active_msg.pop(conv, None)
    # without the lock it is queued (or done) again: the endpoint answers normally
    with TestClient(app) as c:
        H = {"Authorization": f"Bearer {KEY}"}
        assert c.post(f"/api/conversations/{conv}/takeback", json={"client_id": CID}, headers=H).status_code == 200


def test_takeback_twice_is_a_polite_404(env, monkeypatch):
    _on(monkeypatch)
    conv = _conv()
    from app.events import bus
    bus.publish(conv, "message", {"role": "user", "text": "do baar nahi", "source": "user", "client_id": CID})
    from app.main import app
    H = {"Authorization": f"Bearer {KEY}"}
    with TestClient(app) as c:
        assert c.post(f"/api/conversations/{conv}/takeback", json={"client_id": CID}, headers=H).status_code == 200
        assert c.post(f"/api/conversations/{conv}/takeback", json={"client_id": CID}, headers=H).status_code == 404
        assert c.post(f"/api/conversations/{conv}/takeback", json={"client_id": "cid-unknown-00000"},
                      headers=H).status_code == 404
