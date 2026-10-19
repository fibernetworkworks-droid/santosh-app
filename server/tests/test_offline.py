"""Phone offline -> Santosh emails a digest of his updates."""
import asyncio
from datetime import datetime, timedelta, timezone


def test_digest_only_when_phone_silent(env, monkeypatch):
    monkeypatch.setenv("EMAIL_ADDRESS", "owner@gmail.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-pass")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import mail, offline
    from app.db import Conversation, PhoneSeen, session
    from app.events import notify
    offline._touched.clear()
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); conv = c.id
    offline.touch("default")
    notify(conv, "Yaad dila raha hoon: dawai ka samay")
    assert offline.due_digests() == []            # phone just seen: no email
    with session() as s:
        s.get(PhoneSeen, "default").at = datetime.now(timezone.utc) - timedelta(minutes=45)
    sent = []

    async def fake_send(to, subject, body, **kw):
        sent.append((to, subject, body))
    monkeypatch.setattr(mail, "send_email", fake_send)
    assert asyncio.run(offline.send_due()) == 1
    to, subject, body = sent[0]
    assert to == "owner@gmail.com" and "dawai ka samay" in body and "Payment kabhi email se nahi" in body
    assert asyncio.run(offline.send_due()) == 0   # nothing new / not again within 30 min


def test_wake_config(env, monkeypatch, tmp_path):
    """Santosh Wake needs no keys: always available with the built-in model; the server can push a newer one."""
    from fastapi.testclient import TestClient
    from app import main
    from app.config import get_settings
    c = TestClient(main.app)
    j = c.get("/api/wake").json()
    assert j["available"] and j["engine"] == "santosh-wake" and j["custom_model"] is False and j["threshold"] == 0.5
    assert c.get("/api/wake/keyword").status_code == 404
    model = tmp_path / "hey_santosh.onnx"
    model.write_bytes(b"ONNX")
    monkeypatch.setenv("WAKE_KEYWORD_FILE", str(model))
    monkeypatch.setenv("WAKE_SENSITIVITY", "0.8")
    get_settings.cache_clear()
    j = c.get("/api/wake").json()
    assert j["custom_model"] and j["version"] != "builtin" and j["threshold"] == 0.3
    assert c.get("/api/wake/keyword").content == b"ONNX"
