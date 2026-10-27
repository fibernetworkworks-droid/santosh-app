"""Push notifications (FCM HTTP v1): token API, which events push, payload shape, dead tokens removed."""
import json
import time

import httpx
import pytest


@pytest.fixture
def pu(env, monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("FCM_SERVICE_ACCOUNT_FILE", str(tmp_path / "sa.json"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app import push
    push.reset()
    sent = []

    class Creds:
        token = "ya29.test"
    monkeypatch.setattr(push, "_credentials", lambda: (Creds(), "santosh-a583a"))

    def handler(req):
        body = json.loads(req.content)
        sent.append((str(req.url), req.headers["authorization"], body))
        if body["message"]["token"] == "dead-token-xxxxxxxx":
            return httpx.Response(404, json={"error": {"status": "NOT_FOUND", "details": [{"errorCode": "UNREGISTERED"}]}})
        return httpx.Response(200, json={"name": "projects/x/messages/1"})
    real = httpx.Client

    def fake_client(*a, **k):
        k["transport"] = httpx.MockTransport(handler)
        return real(*a, **k)
    monkeypatch.setattr(push.httpx, "Client", fake_client)
    from fastapi.testclient import TestClient
    from app import main
    from app.db import Conversation, session
    c = TestClient(main.app)
    with session() as s:
        conv = Conversation(tenant_id=get_settings().tenant_id)
        s.add(conv)
        s.flush()
        cid = conv.id
    yield {"c": c, "sent": sent, "push": push, "conv": cid}
    push.reset()
    get_settings.cache_clear()


def wait(sent, n):
    for _ in range(100):
        if len(sent) >= n:
            return
        time.sleep(0.02)


def test_register_and_push_reply_and_alarm(pu):
    c, sent = pu["c"], pu["sent"]
    assert c.post("/api/push/token", json={"token": "tok-phone-123456"}).json() == {"ok": True, "push": True}
    from app.events import bus
    bus.publish(pu["conv"], "message", {"role": "assistant", "text": "Bill ₹540 due kal hai."})
    bus.publish(pu["conv"], "message", {"role": "user", "text": "hi"})               # user's own text: no push
    bus.publish(pu["conv"], "device_action", {"id": "act_1", "type": "set_alarm", "at_ms": 1})
    bus.publish(pu["conv"], "artifact", {"id": "a1", "title": "EMI", "status": "building"})   # not ready: no push
    bus.publish(pu["conv"], "artifact", {"id": "a1", "title": "EMI Calculator", "status": "ready"})
    wait(sent, 3)
    time.sleep(0.1)
    assert len(sent) == 3
    url, auth, body = sent[0]
    assert url == "https://fcm.googleapis.com/v1/projects/santosh-a583a/messages:send" and auth == "Bearer ya29.test"
    m = body["message"]
    assert m["token"] == "tok-phone-123456" and m["android"]["priority"] == "HIGH"
    assert m["data"]["kind"] == "message" and "₹540" in m["data"]["body"] and "notification" not in m
    kinds = [b["message"]["data"]["kind"] for _, _, b in sent]
    assert sorted(kinds) == ["artifact", "device_action", "message"]
    act = next(b for _, _, b in sent if b["message"]["data"]["kind"] == "device_action")["message"]
    assert json.loads(act["data"]["payload"])["id"] == "act_1" and act["android"]["ttl"] == "600s"


def test_dead_tokens_are_removed(pu):
    c, sent = pu["c"], pu["sent"]
    c.post("/api/push/token", json={"token": "dead-token-xxxxxxxx"})
    from app.events import bus
    bus.publish(pu["conv"], "message", {"role": "assistant", "text": "hello"})
    wait(sent, 1)
    time.sleep(0.1)
    from app.db import PushToken, session
    with session() as s:
        assert s.get(PushToken, "dead-token-xxxxxxxx") is None


def test_off_without_service_account(env, monkeypatch):
    monkeypatch.delenv("FCM_SERVICE_ACCOUNT_FILE", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import push
    assert not push.configured()
    push.on_event("conv_x", {"kind": "message", "payload": {"role": "assistant", "text": "x"}})   # no error
