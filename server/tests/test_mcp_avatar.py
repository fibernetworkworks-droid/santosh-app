"""The avatar knows the MCP servers the owner connected, and uses their tools directly, in chat and in calls."""
import asyncio
import contextlib
import json
import time
from types import SimpleNamespace

import pytest
from google.genai import types

from tests.test_campaign_flow import last_result, text, tool
from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_custom_mcp import FakeRemote, _probe, mcp  # noqa: F401  (fixture)


class SeeingClaude:
    """Scripted model that also keeps the system prompt and tool list it was given."""

    def __init__(self, script):
        self.script = list(script)
        self.seen = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.seen.append({"system": kw["system"], "tools": [t["name"] for t in kw["tools"]],
                          "schemas": {t["name"]: t for t in kw["tools"]}})
        step = self.script.pop(0)
        blocks = step(kw["messages"]) if callable(step) else step
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return SimpleNamespace(content=blocks, stop_reason=stop)


def _add(svc, url="https://tools.example.com/mcp", ref="aranjan/kite-mcp", status=200, name=""):
    return svc.mcp_add("default", url, ref=ref, name=name, probe_client=_probe(status))


@pytest.fixture(autouse=True)
def _fresh():
    from app.agent import mcp_live
    mcp_live._cache.clear()
    yield
    mcp_live._cache.clear()


def test_snapshot_and_what_the_avatar_is_told(mcp):  # noqa: F811
    from app.agent import mcp_live
    svc = mcp["svc"]
    assert "abhi koi nahi" in mcp_live.prompt_block(mcp_live.snapshot("default"), {})
    ready = _add(svc)
    locked = _add(svc, "https://secure.example.com/mcp", ref="", status=401, name="Notion")
    snap = mcp_live.snapshot("default")
    by = {s["pack_id"]: s for s in snap}
    assert by[ready["pack_id"]]["status"] == "ready" and [t["name"] for t in by[ready["pack_id"]]["tools"]] == ["get_holdings", "createIssue"]
    assert by[locked["pack_id"]]["status"] == "needs_link" and by[locked["pack_id"]]["tools"] == []
    defs, route = mcp_live.tool_defs(snap, 40)
    names = [d["name"] for d in defs]
    assert names == ["mcp_kite_mcp__get_holdings", "mcp_kite_mcp__createissue"]
    assert route["mcp_kite_mcp__createissue"] == (ready["pack_id"], "createIssue")
    assert "confirm card" in defs[1]["description"] and "confirm" not in defs[0]["description"]
    block = mcp_live.prompt_block(snap, route)
    assert "kite-mcp" in block and "get_holdings" in block and "Notion" in block and "sign-in baaki" in block
    # over the limit: the rest stay reachable through bazar_run, and the avatar is told so
    defs1, route1 = mcp_live.tool_defs(snap, 1)
    assert len(defs1) == 1 and f"bazar_run pack_id={ready['pack_id']}" in mcp_live.prompt_block(snap, route1)


def test_odd_schemas_are_made_safe():
    from app.agent import mcp_live
    sc, hint = mcp_live._clean_schema({"$schema": "x", "type": "object", "properties": {"a": {"$ref": "#/$defs/A"}},
                                       "$defs": {"A": {"type": "string"}}})
    assert sc == {"type": "object", "properties": {}, "additionalProperties": True} and "$ref" in hint
    sc, hint = mcp_live._clean_schema({"properties": {"q": {"type": "string"}}})
    assert sc == {"type": "object", "properties": {"q": {"type": "string"}}} and hint == ""
    assert mcp_live._clean_schema(None)[0]["type"] == "object"


def test_a_slow_server_never_holds_up_the_reply(mcp, monkeypatch):  # noqa: F811
    from app.agent import mcp_live
    from app.bazar.connectors.mcp_remote import McpExecutor
    _add(mcp["svc"])
    McpExecutor._cache.clear()
    monkeypatch.setattr(mcp_live, "FETCH_TIMEOUT_S", 0.3)
    monkeypatch.setattr(FakeRemote, "list_tools", lambda self: time.sleep(2) or [])
    t = time.time()
    snap = mcp_live.snapshot("default")
    assert time.time() - t < 1.5 and snap[0]["status"] == "slow"
    assert "abhi jawab nahi de raha" in mcp_live.prompt_block(snap, {})


def test_chat_avatar_knows_and_uses_its_mcp(mcp):  # noqa: F811
    from app.agent import run_turn, set_client
    svc, conv = mcp["svc"], mcp["conv"]
    out = _add(svc)
    got = {}

    def after_read(msgs):
        got["read"] = json.loads(last_result(msgs)["content"])
        return tool("mcp_kite_mcp__createissue", {"title": "Bug"}, 2)

    def after_write(msgs):
        got["write"] = json.loads(last_result(msgs)["content"])
        return text("Holdings dekh liye. Issue banane ke liye Approve dabaiye.")

    claude = SeeingClaude([tool("mcp_kite_mcp__get_holdings", {}, 1), after_read, after_write])
    set_client(claude)
    reply = asyncio.run(run_turn(conv, "Mere kite pe holdings dikhao aur ek bug issue bana do", tenant_id="default"))
    first = claude.seen[0]
    assert "Jude hue MCP servers" in first["system"] and "kite-mcp" in first["system"]
    assert {"mcp_kite_mcp__get_holdings", "mcp_kite_mcp__createissue", "bazar_run"} <= set(first["tools"])
    assert got["read"]["data"]["tool"] == "get_holdings"                    # the read ran on the server
    assert got["write"]["needs_approval"] is True                            # the write waits for the owner's tap
    assert [c[2] for c in FakeRemote.calls] == ["get_holdings"]
    assert "Approve" in reply
    _ = out


def test_chat_survives_a_tool_schema_the_model_refuses(mcp):  # noqa: F811
    from app.agent import run_turn, set_client
    _add(mcp["svc"])

    class Picky(SeeingClaude):
        async def _create(self, **kw):
            if any(t["name"].startswith("mcp_") for t in kw["tools"]):
                raise RuntimeError("Error 400: tools.40.input_schema: JSON schema is invalid")
            return await super()._create(**kw)

    claude = Picky([text("Kite server juda hai, bazar_run se kaam karunga.")])
    set_client(claude)
    reply = asyncio.run(run_turn(mcp["conv"], "kaun se MCP jude hain?", tenant_id="default"))
    assert "Kite" in reply and "kite-mcp" in claude.seen[0]["system"]
    assert not any(n.startswith("mcp_") for n in claude.seen[0]["tools"])


def test_voice_call_knows_and_uses_its_mcp(mcp, monkeypatch):  # noqa: F811
    from fastapi.testclient import TestClient

    from app import main, voice
    from tests.test_voice import FakeSession, _connector, _gemini_env, read_events, wait_until
    _gemini_env(monkeypatch)
    _add(mcp["svc"])
    fake = FakeSession([[types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
        types.FunctionCall(id="k1", name="mcp_kite_mcp__get_holdings", args={})]))]])

    async def send_tool_response(function_responses):
        fake.tool_responses.extend(function_responses)
    fake.send_tool_response = send_tool_response
    configs = []
    _connector(monkeypatch, fake, configs=configs)
    with TestClient(main.app) as c:
        with c.websocket_connect(f"/api/voice/ws?conv={mcp['conv']}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            assert wait_until(lambda: fake.tool_responses, timeout=6)
            ws.send_text(json.dumps({"type": "end"}))
    cfg = configs[0]
    names = {d.name for d in cfg.tools[0].function_declarations}
    assert {"mcp_kite_mcp__get_holdings", "mcp_kite_mcp__createissue", "bazar_run"} <= names
    prompt = cfg.system_instruction.parts[0].text
    assert "Jude hue MCP servers" in prompt and "kite-mcp" in prompt
    r = fake.tool_responses[0]
    assert r.id == "k1" and r.response["result"]["data"]["tool"] == "get_holdings"
    _ = voice


def test_voice_call_goes_on_when_gemini_refuses_an_mcp_schema(mcp, monkeypatch):  # noqa: F811
    from fastapi.testclient import TestClient

    from app import main, voice
    from tests.test_voice import FakeSession, _gemini_env, read_events
    _gemini_env(monkeypatch)
    _add(mcp["svc"])
    fake = FakeSession([])
    configs = []

    @contextlib.asynccontextmanager
    async def picky(config):
        configs.append(config)
        if any(d.name.startswith("mcp_") for d in config.tools[0].function_declarations):
            raise Exception("1007 Invalid JSON payload: function_declarations[90].parameters: unsupported schema")
        yield fake

    monkeypatch.setattr(voice, "connector", picky)
    with TestClient(main.app) as c:
        with c.websocket_connect(f"/api/voice/ws?conv={mcp['conv']}") as ws:
            assert read_events(ws, lambda e: e["type"] in ("ready", "error"))[-1]["type"] == "ready"
            ws.send_text(json.dumps({"type": "end"}))
    last = configs[-1]
    assert not any(d.name.startswith("mcp_") for d in last.tools[0].function_declarations)
    assert "kite-mcp" in last.system_instruction.parts[0].text      # still known; reachable through bazar_run
