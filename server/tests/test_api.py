import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import OutboundMessage, Template, session

from .conftest import SAMPLE


def client(monkeypatch, env, **extra):
    for k, v in extra.items():
        monkeypatch.setattr(env["settings"], k, v)
    from app.main import app
    return TestClient(app)


def test_conversation_upload_and_auth(env, monkeypatch):
    with client(monkeypatch, env, api_key="secret") as c:
        assert c.post("/api/conversations").status_code == 401
        h = {"Authorization": "Bearer secret"}
        conv = c.post("/api/conversations", headers=h).json()["id"]
        r = c.post("/api/leads/upload", headers=h, data={"conversation_id": conv},
                   files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/csv")})
        assert r.status_code == 200 and r.json()["valid"] == 11
        bad = c.post("/api/leads/upload", headers=h, files={"file": ("x.csv", b"foo,bar\n1,2\n", "text/csv")})
        assert bad.status_code == 400 and "phone column" in bad.json()["detail"]
        msgs = c.get(f"/api/conversations/{conv}/messages", headers=h).json()["messages"]
        assert msgs and "Santosh" in msgs[0]["text"]
        assert c.get("/healthz").json()["dry_run"] is True


def test_webhook_verify_signature_and_statuses(env, monkeypatch):
    with client(monkeypatch, env, wa_verify_token="vt", wa_app_secret="appsecret") as c:
        ok = c.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "42"})
        assert ok.text == "42"
        assert c.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "no", "hub.challenge": "1"}).status_code == 403

        # set up a campaign with one message already handed to Meta
        from app import campaigns as camp
        from app.db import Conversation
        from app.leads import import_leads
        res = import_leads(SAMPLE.name, SAMPLE.read_bytes(), "default")
        with session() as s:
            conv = Conversation(tenant_id="default"); s.add(conv); s.flush(); conv_id = conv.id
            t = Template(tenant_id="default", name="t1", language="hi", category="MARKETING",
                         body="Namaste {{1}}, aaj ka offer dekhiye.", meta_id="999", status="PENDING")
            s.add(t); s.flush(); tid = t.id
        v = camp.create_campaign(tenant_id="default", conversation_id=conv_id, title="W", lead_list_id=res.list_id,
                                 template_id=tid, param_mapping=[{"source": "lead_name"}], consent_confirmed=True,
                                 auto_send=True)
        with session() as s:
            m = s.scalars(select(OutboundMessage).where(OutboundMessage.campaign_id == v["id"])).first()
            m.wa_message_id, m.status = "wamid.ABC", "sent"
            phone = m.phone

        body = {"entry": [{"changes": [
            {"field": "messages", "value": {"statuses": [{"id": "wamid.ABC", "status": "read", "recipient_id": phone}],
                                            "messages": [{"from": phone, "text": {"body": "Price kya hai?"}}]}},
            {"field": "message_template_status_update", "value": {"event": "APPROVED", "message_template_id": 999}}]}]}
        raw = json.dumps(body).encode()
        assert c.post("/webhooks/whatsapp", content=raw, headers={"x-hub-signature-256": "sha256=bad"}).status_code == 401
        sig = "sha256=" + hmac.new(b"appsecret", raw, hashlib.sha256).hexdigest()
        r = c.post("/webhooks/whatsapp", content=raw, headers={"x-hub-signature-256": sig, "content-type": "application/json"})
        assert r.status_code == 200
        with session() as s:
            m = s.scalars(select(OutboundMessage).where(OutboundMessage.wa_message_id == "wamid.ABC")).one()
            assert m.status == "read" and m.replied
            assert s.get(Template, tid).status == "APPROVED"
        # a late "delivered" must not downgrade "read"
        raw2 = json.dumps({"entry": [{"changes": [{"field": "messages", "value": {"statuses": [
            {"id": "wamid.ABC", "status": "delivered", "recipient_id": phone}]}}]}]}).encode()
        sig2 = "sha256=" + hmac.new(b"appsecret", raw2, hashlib.sha256).hexdigest()
        c.post("/webhooks/whatsapp", content=raw2, headers={"x-hub-signature-256": sig2})
        with session() as s:
            assert s.scalars(select(OutboundMessage.status).where(OutboundMessage.wa_message_id == "wamid.ABC")).one() == "read"
