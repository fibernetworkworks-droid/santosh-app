"""Checks the exact requests sent to Meta's Graph API, using a fake transport."""
import asyncio
import json

import httpx
import pytest

from app.whatsapp import MetaWhatsApp, WhatsAppError


def make(handler):
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"Authorization": "Bearer T"})
    return MetaWhatsApp("T", "WABA1", "PN1", "v21.0", http=http)


def test_create_template_and_send_payloads():
    seen = []

    def handler(req: httpx.Request):
        seen.append((req.method, str(req.url), json.loads(req.content or b"{}")))
        if req.url.path.endswith("/message_templates"):
            return httpx.Response(200, json={"id": "123", "status": "PENDING", "category": "MARKETING"})
        if req.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "wamid.X"}]})
        return httpx.Response(200, json={"status": "APPROVED", "name": "t"})

    wa = make(handler)
    out = asyncio.run(wa.create_template("t_1", "hi", "marketing", "Namaste {{1}}, offer hai.", ["Rahul"], "STOP"))
    assert out == {"meta_id": "123", "status": "PENDING"}
    m, url, body = seen[0]
    assert m == "POST" and url == "https://graph.facebook.com/v21.0/WABA1/message_templates"
    assert body["category"] == "MARKETING"
    assert body["components"][0] == {"type": "BODY", "text": "Namaste {{1}}, offer hai.", "example": {"body_text": [["Rahul"]]}}
    assert body["components"][1] == {"type": "FOOTER", "text": "STOP"}

    wamid = asyncio.run(wa.send_template("919876543210", "t_1", "hi", ["Rahul"]))
    assert wamid == "wamid.X"
    _, url, body = seen[1]
    assert url.endswith("/PN1/messages")
    assert body["to"] == "919876543210" and body["type"] == "template"
    assert body["template"] == {"name": "t_1", "language": {"code": "hi"},
                                "components": [{"type": "body", "parameters": [{"type": "text", "text": "Rahul"}]}]}

    st = asyncio.run(wa.get_template_status("123"))
    assert st == {"status": "APPROVED", "reason": None}


def test_errors_are_classified(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", _noop)   # skip the retry back-off
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"error": {"message": "rate", "code": 130429}})
        return httpx.Response(400, json={"error": {"message": "Recipient not on WhatsApp", "code": 131026}})

    wa = make(handler)
    with pytest.raises(WhatsAppError) as ei:
        asyncio.run(wa.send_template("919876543210", "t", "hi", []))
    assert ei.value.code == 131026 and not ei.value.retryable and calls["n"] == 2


async def _noop(*_a, **_k):
    return None


def test_live_mode_requires_credentials():
    with pytest.raises(WhatsAppError) as ei:
        MetaWhatsApp("", "", "PN")
    assert "WA_TOKEN" in str(ei.value) and "WA_WABA_ID" in str(ei.value)
