"""v0.388 live WhatsApp (WA_DRY_RUN=false) without a server-wide number: the client starts, the worker tick runs, a business's
own number (Embedded Signup channel) still sends, and the server-number features fail with a plain error - before this the
client's constructor raised and every worker tick (reminders, social desk, approvals) failed every 2 seconds."""
import asyncio

import httpx
import pytest


def test_live_client_without_server_number_and_worker_tick(env, monkeypatch):
    monkeypatch.setenv("WA_DRY_RUN", "false")
    for k in ("WA_TOKEN", "WA_WABA_ID", "WA_PHONE_NUMBER_ID"):
        monkeypatch.setenv(k, "")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.whatsapp import client as C
    sent = []

    def handler(req: httpx.Request) -> httpx.Response:
        sent.append((str(req.url), req.headers.get("authorization")))
        return httpx.Response(200, json={"messages": [{"id": "wamid.X1"}]})
    C.set_whatsapp(None)
    wa = C.get_whatsapp()                                   # used to raise "Live WhatsApp needs WA_TOKEN..."
    assert wa.dry_run is False and wa.server_ready is False
    wa.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def run():
        assert await wa.send_text("919800000000", "Namaste", "109876543210987", "HER_TOKEN") == "wamid.X1"
        with pytest.raises(C.WhatsAppError) as e:
            await wa.send_template("919800000000", "offer", "hi", [])
        assert "server number" in str(e.value)
        with pytest.raises(C.WhatsAppError):
            await wa.send_text("919800000000", "x")                  # no number at all: plain refusal
        from app import worker
        await worker.check_approvals(force=True)                    # the tick's first step no longer raises
        await worker.send_batches()
    asyncio.run(run())
    assert sent == [("https://graph.facebook.com/v21.0/109876543210987/messages", "Bearer HER_TOKEN")]
    C.set_whatsapp(None)
    get_settings.cache_clear()
