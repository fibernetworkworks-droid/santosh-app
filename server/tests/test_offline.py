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
    from fastapi.testclient import TestClient
    from app import main
    from app.config import get_settings
    c = TestClient(main.app)
    assert c.get("/api/wake").json()["available"] is False
    ppn = tmp_path / "hey.ppn"
    ppn.write_bytes(b"PPN")
    monkeypatch.setenv("PICOVOICE_ACCESS_KEY", "pv-key")
    monkeypatch.setenv("WAKE_KEYWORD_FILE", str(ppn))
    get_settings.cache_clear()
    j = c.get("/api/wake").json()
    assert j["available"] and j["access_key"] == "pv-key"
    assert c.get("/api/wake/keyword").content == b"PPN"
