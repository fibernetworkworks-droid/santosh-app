"""Google Search, website reading and the private-address guard."""
import asyncio
import socket

import httpx
import pytest

from app import web
from app.agent.tools import Ctx, ToolError, dispatch
from app.db import DeviceAction, session
from tests.test_life import conv_ctx


def fake_dns(monkeypatch, table):
    def gai(host, *a, **k):
        if host not in table:
            raise socket.gaierror("nope")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (table[host], 0))]
    monkeypatch.setattr(web.socket, "getaddrinfo", gai)


@pytest.mark.parametrize("url", ["http://localhost:8077/healthz", "http://127.0.0.1/", "http://10.0.0.5/admin",
                                 "http://169.254.169.254/latest/meta-data", "http://172.18.0.1:8077/", "file:///etc/passwd",
                                 "https://example.com:2222/"])
def test_private_and_odd_urls_refused(monkeypatch, url):
    fake_dns(monkeypatch, {"localhost": "127.0.0.1", "127.0.0.1": "127.0.0.1", "10.0.0.5": "10.0.0.5",
                           "169.254.169.254": "169.254.169.254", "172.18.0.1": "172.18.0.1", "example.com": "93.184.216.34"})
    with pytest.raises(web.WebError):
        asyncio.run(web.open_website(url))


def test_open_website_reads_text_and_blocks_redirect_to_private(monkeypatch):
    fake_dns(monkeypatch, {"shop.example.in": "93.184.216.34", "evil.example.in": "93.184.216.35", "internal": "10.1.1.1"})
    page = """<html><head><title>Sharma Electronics &amp; Co</title><style>.x{}</style></head>
      <body><nav><a href="/about">About us</a></nav><h1>LED TV 43 inch</h1><p>Price: ₹21,499</p>
      <script>var hidden = 'nope';</script><p>Open 10am to 9pm, Akola</p></body></html>"""

    def handler(req):
        if req.url.host == "shop.example.in":
            return httpx.Response(200, html=page)
        return httpx.Response(302, headers={"location": "http://internal/secret"})

    monkeypatch.setattr(web, "_transport", httpx.MockTransport(handler))
    r = asyncio.run(web.open_website("shop.example.in/tv"))
    assert r["title"] == "Sharma Electronics & Co"
    assert "₹21,499" in r["text"] and "Open 10am to 9pm" in r["text"] and "hidden" not in r["text"]
    assert {"text": "About us", "url": "https://shop.example.in/about"} in r["links"]
    with pytest.raises(web.WebError):
        asyncio.run(web.open_website("https://evil.example.in/"))


def test_google_search_uses_gemini_grounding(env, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    from app.config import get_settings
    get_settings.cache_clear()
    from google.genai import types
    seen = {}

    class Models:
        async def generate_content(self, model, contents, config):
            seen["model"], seen["tools"] = model, config.tools
            if model == "gemini-flash-latest":
                raise Exception("404 model not found")
            return types.GenerateContentResponse(candidates=[types.Candidate(
                content=types.Content(role="model", parts=[types.Part(text="Akola mein aaj petrol ₹104.50 hai.")]),
                grounding_metadata=types.GroundingMetadata(
                    web_search_queries=["petrol price akola today"],
                    grounding_chunks=[types.GroundingChunk(web=types.GroundingChunkWeb(uri="https://x.in/akola", title="x.in"))]))])

    class FakeClient:
        def __init__(self, **k):
            self.aio = type("A", (), {"models": Models()})()

    import google.genai
    monkeypatch.setattr(google.genai, "Client", FakeClient)
    ctx = conv_ctx()
    out = asyncio.run(dispatch("google_search", {"query": "petrol price Akola"}, ctx))
    assert out["answer"].startswith("Akola") and out["sources"] == [{"title": "x.in", "url": "https://x.in/akola"}]
    assert seen["model"] == "gemini-3.5-flash" and seen["tools"][0].google_search is not None   # fell back past a missing model


def test_open_on_phone_creates_device_action(env):
    ctx = conv_ctx()
    out = asyncio.run(dispatch("open_on_phone", {"url": "irctc.co.in"}, ctx))
    assert out["sent_to_phone"]
    with session() as s:
        a = s.query(DeviceAction).filter_by(conversation_id=ctx.conversation_id).one()
        assert a.type == "open_url" and a.payload["url"] == "https://irctc.co.in"


def test_search_without_key_is_a_clear_tool_error(env):
    with pytest.raises(ToolError, match="GEMINI_API_KEY"):
        asyncio.run(dispatch("google_search", {"query": "x"}, Ctx("default", "c")))
