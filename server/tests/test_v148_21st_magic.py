"""v0.148 21st.dev Magic (21st.dev's own remote MCP, https://21st.dev/api/mcp, key in the x-api-key header) as a Hoola
connection: key only in the app, generate / inspiration / logo tools run like reads (they only return code), her
'pehle poochho' switch still wins, other tools still ask."""
import socket

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)

TOOLS = ["generate", "get_inspiration", "search_logo", "21st_magic_component_builder", "update_component"]
FAKE_KEY = "an" + "_" + "k" * 32   # built at runtime: not a real key


class FakeMagic:
    calls: list = []

    def __init__(self, url, headers):
        self.url, self.headers = url, headers

    def list_tools(self):
        return [{"name": t, "description": t, "input_schema": {"type": "object"}} for t in TOOLS]

    def call_tool(self, name, args):
        FakeMagic.calls.append((name, args, self.url, dict(self.headers)))
        return {"is_error": False, "text": "export default function Hero() { return <section/> }", "data": {"tool": name}}


@pytest.fixture
def mg(bz, monkeypatch):  # noqa: F811
    from app.bazar import custom_mcp, service
    from app.bazar.agent.toolbox import default_executors
    from app.bazar.connectors.mcp_remote import McpExecutor
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo",
                        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("76.76.21.21", 443))])
    ex = default_executors()
    ex["mcp"] = McpExecutor(remote_factory=lambda url, h: FakeMagic(url, h))
    McpExecutor._cache.clear()
    service.set_executors(ex)
    FakeMagic.calls = []
    return bz


def _probe(status):
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, json={})))


def test_featured_entry():
    from app.bazar import featured
    c = featured.get("21st-magic")
    assert c["url"] == "https://21st.dev/api/mcp" and c["auth"] == "api_key" and c["key_header"] == "x-api-key"
    assert not c.get("caution") and "generate" in c["options"]["reads"]
    pub = featured.public(c)
    assert "21st.dev/mcp" in pub["how_to_connect"] and "never in chat" in pub["how_to_connect"]


def test_key_only_in_app_then_tools_run_like_reads(mg):
    svc, conv = mg["svc"], mg["conv"]
    with pytest.raises(Exception, match="never in chat"):
        svc.mcp_connect_featured("default", "21st-magic", probe_client=_probe(200))
    out = svc.mcp_connect_featured("default", "21st-magic", key=FAKE_KEY, probe_client=_probe(200))
    assert out["status"] == "ready"
    pid = out["pack_id"]
    mine = [p for p in svc.find("default", "21st magic ui component")["packs"] if p["pack_id"] == pid][0]
    tiers = {t["tool"]: t["tier"] for t in mine["tools"]}
    for t in ("generate", "get_inspiration", "search_logo", "21st_magic_component_builder"):
        assert tiers[t] == 0, t
    assert tiers["update_component"] >= 2                    # not documented as output-only -> still asks
    r = svc.run("default", conv, pid, "generate", {"message": "pricing section, 3 plans, saffron"})
    assert r["data"]["tool"] == "generate"
    name, args, url, headers = FakeMagic.calls[-1]
    assert url == "https://21st.dev/api/mcp" and headers["x-api-key"] == FAKE_KEY and "Authorization" not in headers
    w = svc.run("default", conv, pid, "update_component", {"id": "x"})
    assert w["needs_approval"] is True
    # her "pehle poochho" switch on generate wins over the documented read
    from app import mcp_prefs
    mcp_prefs.set_pref("default", pid, "generate", TOOLS, ask=True)
    r = svc.run("default", conv, pid, "generate", {"message": "hero"})
    assert r["needs_approval"] is True
    view = {v["name"]: v for v in mcp_prefs.view("default", pid, [{"name": t} for t in TOOLS])}
    assert view["search_logo"]["default_ask"] is False and view["generate"]["ask"] is True


def test_prompt_lines():
    from app import voice
    from app.agent import prompts
    assert "21ST MAGIC" in voice.PERSONA and "featured=21st-magic" in open(prompts.__file__).read()
