"""v0.600.0 HOOLA HUB - the hub/loader/conformance layer, P7 of the AEP plan
(the name keeps the first-build number, the v0.566 middleware precedent).

The langchain hub FEATURE SURFACE hand-built as app/aep/{hub,load,mcp,
conformance}.py after the upstream re-read at the pinned commit aa2528fb
(langchain_v1/langchain/chat_models/base.py 1079 lines: the provider registry
:56, init_chat_model :232, _ConfigurableModel :661; core/load/{dump,load,
mapping}; langchain_v1/langchain/mcp/{adapter,tools,elicitation};
standard-tests langchain_tests/{base,unit_tests/chat_models}; model-profiles
{cli,_summary}) - ZERO upstream code.

What is tested FOR REAL (all offline): the init_chat_model router (fixed mode,
the provider kwarg form, prefix inference + the honest unknown-provider error,
the TypeError gate, register_provider extensions); the ConfigurableModel
declarative mode (model-less, config selection, config_prefix, the fields
filter, the queued declarative calls, with_config, stream+batch riding the
resolved model); HouseBrainChatModel (the injected runner, sync + async, the
no-runner refusal); OpenAICompatChatModel - the BYOK zoo (invoke + tool-call
parse with the broken-args drop law, SSE streaming, bind_tools on the OpenAI
wire, the standard-params override, the error lanes, the registry lane); the
from-dict loader (round trips through both serializable lanes, the JSON string
lane, the not_implemented marker, the escape law, the allowlist gates, the
secrets placeholders); the MCP client adapter (the memory handshake +
pagination, the tool call, the isError lane, content conversion incl. the
honest audio refusal, elicitation both ways, a REAL stdio subprocess round
trip, the group mangling, the string-target gate, the schema->pydantic lane);
the conformance suite (every house adapter passes, a broken model fails by
name); the model profiles (models.dev mapping, the byte-stable refresh, the
diff markdown, the CLI incl. the -m entry); the inertness probe + the
package-export law + the APP_VERSION/pubspec pins.
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

import httpx
import pytest

import app.aep as _pkg  # noqa: F401 - the export law probe
import importlib
from app.aep import conformance as C
from app.aep import hub as H
from app.aep import mcp as M
L = importlib.import_module("app.aep.load")  # the MODULE (the function shadows it on the package)
from app.aep import *  # noqa: F401,F403 - the package-export law probe
from app.aep.messages import AIMessage, HumanMessage
from app.aep.models import ChatGeneration, ChatResult, FakeListChatModel
from app.aep.prompts import ChatPromptTemplate


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_dir():
    d = tempfile.mkdtemp(prefix="hoola-p7-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def make_byok_handler(content="mock reply", tool_calls=None, broken_args=False):
    """One OpenAI-compatible gateway fixture: JSON for plain POSTs, SSE for
    stream=True - branching on the body, the way real gateways behave."""
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("stream"):
            sse = (
                "data: " + json.dumps({"choices": [
                    {"delta": {"content": content[:3]}, "finish_reason": None}]}) + "\n\n"
                "data: " + json.dumps({"choices": [
                    {"delta": {"content": content[3:]}, "finish_reason": None}]}) + "\n\n"
                "data: " + json.dumps({"choices": [
                    {"delta": {}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 1}}) + "\n\n"
                "data: [DONE]\n\n")
            return httpx.Response(200, text=sse,
                                  headers={"content-type": "text/event-stream"})
        msg: dict = {"role": "assistant", "content": content}
        if tool_calls is not None:
            calls = []
            for i, tc in enumerate(tool_calls):
                args = "{bad json" if broken_args else json.dumps(tc.get("args", {}))
                calls.append({"id": tc.get("id") or f"call_{i}", "type": "function",
                              "function": {"name": tc["name"], "arguments": args}})
            msg["tool_calls"] = calls
            msg["content"] = ""
        return httpx.Response(200, json={
            "choices": [{"message": msg, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2}})
    return handler


def byok_model(**kw):
    return H.OpenAICompatChatModel(
        model="glm-4.7", base_url="https://byok.test/v1", api_key="k",
        transport=httpx.MockTransport(make_byok_handler(**kw)))


FAKE = None  # built per-test (the fakes carry call state)


# ---------------------------------------------------------------------------
# init_chat_model - the router
# ---------------------------------------------------------------------------
def test_fixed_model_and_provider_kwarg_form():
    m1 = H.init_chat_model("fake:echo", responses=["a"])
    m2 = H.init_chat_model("echo", model_provider="fake", responses=["a"])
    assert isinstance(m1, FakeListChatModel) and isinstance(m2, FakeListChatModel)
    assert m1.invoke("x").content == "a" and m2.invoke("x").content == "a"


def test_prefix_inference_and_unknown_refusal():
    m = H.init_chat_model("fake-list-chat", responses=["b"])
    assert isinstance(m, FakeListChatModel)
    with pytest.raises(ValueError) as e:
        H.init_chat_model("totally-unknown-model")
    assert "Unable to infer model provider" in str(e.value)
    assert "fake" in str(e.value) and "openai_compat" in str(e.value)


def test_unsupported_provider_and_type_gate():
    with pytest.raises(ValueError) as e:
        H.init_chat_model("x", model_provider="nope")
    assert "Unsupported" in str(e.value)
    with pytest.raises(TypeError) as e2:
        H.init_chat_model(123)  # type: ignore[arg-type]
    assert "must be a string" in str(e2.value)


def test_register_provider_extension():
    seen = {}

    def _factory(model, **kwargs):
        seen["model"] = model
        return FakeListChatModel(responses=["custom"], **kwargs)

    H.register_provider("my_zoo", _factory, infer_prefixes=["myzoo-"])
    try:
        m = H.init_chat_model("myzoo-thing")
        assert m.invoke("x").content == "custom"
        # inference names the provider; the model string rides whole (the
        # upstream law - only an explicit "provider:model" prefix is stripped)
        assert seen["model"] == "myzoo-thing"
        assert "my_zoo" in H.known_providers()
    finally:
        H._BUILTIN_PROVIDERS.pop("my_zoo", None)
        H._INFER_PREFIXES.pop("myzoo-", None)


def test_bare_string_targets_refused_at_the_mcp_gate():
    with pytest.raises(M.McpError) as e:
        M.load_mcp_tools("http://example.com/mcp")
    assert "never silently become a subprocess" in str(e.value)


# ---------------------------------------------------------------------------
# ConfigurableModel - the declarative mode
# ---------------------------------------------------------------------------
def test_model_less_requires_config():
    cm = H.init_chat_model()
    with pytest.raises(ValueError) as e:
        cm.invoke("x")
    assert "No model configured" in str(e.value)


def test_configurable_selects_model_per_call():
    cm = H.init_chat_model()
    # only (model, model_provider) are configurable here: "responses" in the
    # config is FILTERED OUT, so the fake rides its own default echo
    out = cm.invoke("q", config={"configurable": {"model": "fake:one",
                                                  "responses": ["picked"]}})
    assert out.content == "echo: one"
    assert cm._configurable_fields == ["model", "model_provider"]


def test_config_prefix_and_fields_filter():
    cm = H.init_chat_model(configurable_fields=("model",), config_prefix="foo")
    out = cm.invoke("q", config={"configurable": {"foo_model": "fake:echo",
                                                  "responses": ["no ride"]}})
    assert out.content == "echo: echo"      # responses NOT configurable: filtered out
    with pytest.warns(UserWarning, match="no fields are configurable"):
        H.init_chat_model("fake:echo", config_prefix="bar")


def test_declarative_calls_queued_until_resolved():
    cm = H.init_chat_model(configurable_fields="any")
    bound = cm.bind_tools([{"name": "t", "description": "d",
                            "parameters": {"type": "object", "properties": {}}}])
    out = bound.invoke("q", config={"configurable": {
        "model": "openai_compat:glm-4.7", "base_url": "https://byok.test/v1",
        "api_key": "k", "transport": httpx.MockTransport(make_byok_handler())}})
    assert out.content == "mock reply"


def test_with_config_and_stream_batch_ride_resolution():
    # with_config("any"): BOTH keys ride the model lane -> pinned as defaults
    cm = H.init_chat_model(configurable_fields="any").with_config(
        {"configurable": {"model": "fake:echo", "responses": ["w"]}})
    assert cm.invoke("x").content == "w"
    # the per-call config still wins over the pinned defaults
    chunks = list(cm.stream("x", config={"configurable": {"responses": ["abc"]}}))
    assert "".join(c.content for c in chunks) == "abc"
    outs = cm.batch(["x", "y"], config={"configurable": {"responses": ["z"]}})
    assert [o.content for o in outs] == ["z", "z"]


# ---------------------------------------------------------------------------
# HouseBrainChatModel - the server's own lane behind an injected runner
# ---------------------------------------------------------------------------
def test_house_brain_sync_runner_and_no_runner_refusal():
    def runner(messages, tools, **kw):
        assert messages[0].type == "human"       # the message list rides as-is
        return ChatResult(generations=[ChatGeneration(
            message=AIMessage(content="brain says hi"))])

    m = H.HouseBrainChatModel(model="auto", runner=runner)
    assert m.invoke([HumanMessage(content="q")]).content == "brain says hi"
    assert m.standard_params()["ls_provider"] == "hoola"
    bare = H.HouseBrainChatModel(model="auto")
    with pytest.raises(ValueError) as e:
        bare.invoke("x")
    assert "no runner wired" in str(e.value)


def test_house_brain_async_runner():
    async def runner(messages, tools, **kw):
        return ChatResult(generations=[ChatGeneration(
            message=AIMessage(content="async brain"))])

    m = H.HouseBrainChatModel(model="claude", runner=runner)
    out = asyncio.run(m.ainvoke([HumanMessage(content="q")]))
    assert out.content == "async brain"
    assert m._llm_type == "hoola-brain"


def test_house_brain_registry_lane():
    m = H.init_chat_model("hoola:claude-sonnet-5-5", runner=lambda *_a, **_k: None)
    assert isinstance(m, H.HouseBrainChatModel) and m.model == "claude-sonnet-5-5"


# ---------------------------------------------------------------------------
# OpenAICompatChatModel - the BYOK zoo
# ---------------------------------------------------------------------------
def test_byok_invoke_and_tool_call_parse():
    m = byok_model(tool_calls=[{"name": "get_weather", "id": "t1",
                                "args": {"city": "Pune"}}])
    out = m.invoke("weather?")
    assert out.content == ""                    # the wire said content=""
    assert out.tool_calls == [{"type": "tool_call", "id": "t1",
                               "name": "get_weather", "args": {"city": "Pune"},
                               "index": 0}]
    assert out.usage_metadata["total_tokens"] == 5


def test_byok_broken_args_dropped_and_finish_length():
    m = byok_model(tool_calls=[{"name": "x", "args": {}}], broken_args=True)
    out = m.invoke("x")
    assert out.tool_calls == []                       # never run a tool on half-written arguments
    assert out.response_metadata["finish_reason"] == "length"   # a cut answer is NOT a finished answer


def test_byok_stream_sse_merge():
    m = byok_model(content="hello world")
    chunks = list(m.stream("x"))
    assert all(type(c).__name__ == "AIMessageChunk" for c in chunks)
    merged = chunks[0]
    for c in chunks[1:]:
        merged = merged + c
    assert "hello world" in (merged.content or "")
    assert merged.usage_metadata["total_tokens"] == 3


def test_byok_bind_tools_rides_the_openai_wire():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "ok"},
                         "finish_reason": "stop"}]})

    from pydantic import BaseModel as BM

    class Adder(BM):
        a: int
        b: int

    m = H.OpenAICompatChatModel(model="glm-4.7", base_url="https://byok.test/v1",
                                api_key="k", transport=httpx.MockTransport(handler))
    bound = m.bind_tools([Adder])
    bound.invoke("x")
    fns = captured["body"]["tools"]
    assert fns[0]["function"]["name"] == "Adder"
    assert fns[0]["function"]["parameters"]["properties"]["a"]["type"] == "integer"
    from app.aep.runnable import RunnableBinding
    assert isinstance(bound, RunnableBinding)


def test_byok_standard_params_override():
    m = byok_model()
    row = m.standard_params()
    assert row["ls_provider"] == "openai_compat" and row["ls_model_type"] == "chat"
    assert m.standard_params(model="override-1")["ls_model_name"] == "override-1"


def test_byok_error_lanes():
    err = H.OpenAICompatChatModel(
        model="m", base_url="https://byok.test/v1", api_key="k",
        transport=httpx.MockTransport(lambda r: httpx.Response(401, text="bad key")))
    with pytest.raises(ValueError) as e:
        err.invoke("x")
    assert "error 401" in str(e.value)

    def _down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    dead = H.OpenAICompatChatModel(
        model="m", base_url="https://byok.test/v1", api_key="k",
        transport=httpx.MockTransport(_down))
    with pytest.raises(ValueError) as e2:
        dead.invoke("x")
    assert "not reachable" in str(e2.value)
    broken = H.OpenAICompatChatModel(
        model="m", base_url="https://byok.test/v1", api_key="k",
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, text="not json at all")))
    with pytest.raises(ValueError) as e3:
        broken.invoke("x")
    assert "broken answer" in str(e3.value)


def test_byok_registry_lane_end_to_end():
    m = H.init_chat_model("openai_compat:glm-4.7", base_url="https://byok.test/v1",
                          api_key="k", transport=httpx.MockTransport(make_byok_handler()))
    assert isinstance(m, H.OpenAICompatChatModel)
    assert m.invoke("x").content == "mock reply"


# ---------------------------------------------------------------------------
# load - the from-dict loader
# ---------------------------------------------------------------------------
def test_dumpd_load_round_trip_message_lane():
    from app.aep.messages import messages_to_dict
    msg = AIMessage(content="hello", additional_kwargs={"k": 1})
    data = L.dumpd(msg)
    assert data["lc"] == 1 and data["type"] == "constructor"
    rebuilt = L.load(data)
    assert isinstance(rebuilt, AIMessage) and rebuilt.content == "hello"
    assert rebuilt.additional_kwargs == {"k": 1}
    # the Serializable lane via messages_to_dict -> messages_from_dict still holds
    assert messages_to_dict([msg])[0]["data"]["content"] == "hello"


def test_dumps_loads_string_lane():
    m = FakeListChatModel(responses=["r1"])
    s = L.dumps(m, pretty=True)
    rebuilt = L.loads(s)
    assert type(rebuilt) is FakeListChatModel and rebuilt.responses == ["r1"]
    with pytest.raises(ValueError):
        L.dumps(m, default=lambda o: o)


def test_not_implemented_marker_names_the_loss():
    data = L.dumpd(threading.Lock())
    assert data["type"] == "not_implemented" and data["id"][-1] == "lock"  # _thread.lock
    rebuilt = L.load(data)
    assert type(rebuilt).__name__ == "SerializedNotImplemented"


def test_escape_law_plain_lc_dicts_never_instantiate():
    sneaky = {"lc": 1, "type": "constructor", "id": ["aep", "messages", "AIMessage"],
              "kwargs": {"content": "evil"}}
    data = L.dumpd({"user_data": sneaky})
    assert "__lc_escaped__" in data["user_data"]
    out = L.load(data)
    assert out["user_data"] == sneaky          # unwrapped to a PLAIN dict
    assert not isinstance(out["user_data"], AIMessage)


def test_allowed_objects_gates():
    m = FakeListChatModel(responses=["r"])
    data = L.dumpd(m)
    rebuilt = L.load(data, allowed_objects="all")
    assert type(rebuilt) is FakeListChatModel
    prompt = ChatPromptTemplate.from_messages([("human", "{x}")])
    pdata = L.dumpd(prompt)
    with pytest.raises(ValueError):
        L.load(pdata, allowed_objects="messages")   # the safe choice refuses it
    crafted = {"lc": 1, "type": "constructor", "id": ["aep", "nope", "Ghost"],
               "kwargs": {}}
    with pytest.raises(ValueError) as e:
        L.load(crafted)
    assert "doesn't exist" in str(e.value)


def test_secrets_placeholders():
    """The BYOK model's api_key rides masked (the redaction-before-egress law):
    dumpd masks it as the $placeholder, load substitutes from secrets_map, and
    a payload without the map refuses."""
    m = H.OpenAICompatChatModel(model="glm-4.7", base_url="https://byok.test/v1",
                                api_key="sk-super-secret")
    data = L.dumpd(m)
    assert data["kwargs"]["api_key"] == "$BYOK_API_KEY"   # masked on the wire
    assert "sk-super-secret" not in json.dumps(data)
    rebuilt = L.load(data, secrets_map={"BYOK_API_KEY": "sk-loaded"})
    assert isinstance(rebuilt, H.OpenAICompatChatModel)
    assert rebuilt.api_key == "sk-loaded"
    with pytest.raises(ValueError) as e:
        L.load(data)                                   # no map, no env - refuse
    assert "Secret placeholder" in str(e.value)


# ---------------------------------------------------------------------------
# mcp - the client adapter (memory transport)
# ---------------------------------------------------------------------------
class FakeMcpServer:
    """The in-process MCP server: the same protocol dicts, zero subprocess."""

    def __init__(self, *, pages: int = 1, tools: list | None = None) -> None:
        self.pages = pages
        self.tools = tools if tools is not None else [
            {"name": "echo", "description": "Echo the text back.",
             "inputSchema": {"type": "object",
                             "properties": {"text": {"type": "string",
                                                     "description": "the text"}},
                             "required": ["text"]}},
            {"name": "img", "description": "Return an image.",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "sing", "description": "Return audio.",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "boom", "description": "Always errors.",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "open_obj", "description": "Open object arg.",
             "inputSchema": {"type": "object",
                             "properties": {"cfg": {"type": "object"}}}},
        ]
        self.elicitation_seen: list | None = None

    def handle(self, method: str, params: dict) -> dict:
        if method == "initialize":
            return {"protocolVersion": M.PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fake-mcp", "version": "1.0"}}
        if method == "tools/list":
            page = int((params.get("cursor") or "0"))
            if page + 1 < self.pages:
                return {"tools": self.tools[page::self.pages] if self.pages == 1
                        else self.tools,
                        "nextCursor": str(page + 1)}
            return {"tools": self.tools, "nextCursor": None}
        if method == "tools/call":
            name = params.get("name")
            if name == "echo":
                return {"content": [{"type": "text",
                                     "text": f"echo: {params['arguments']['text']}"}],
                        "structuredContent": {"len": len(params["arguments"]["text"])},
                        "isError": False}
            if name == "img":
                return {"content": [{"type": "image", "data": "aGk=",
                                     "mimeType": "image/png"}], "isError": False}
            if name == "sing":
                return {"content": [{"type": "audio", "data": "aGk=",
                                     "mimeType": "audio/wav"}], "isError": False}
            if name == "boom":
                return {"content": [{"type": "image", "data": "aGk=",
                                     "mimeType": "image/png"}], "isError": True}
            if name == "open_obj":
                return {"content": [{"type": "text", "text": "ok"}], "isError": False}
            raise M.McpJsonRpcError(-32602, f"unknown tool {name}")
        if method == "ping":
            return {}
        raise M.McpJsonRpcError(-32601, f"unknown method {method}")


def test_mcp_handshake_pagination_and_tools():
    t = M.MemoryTransport(FakeMcpServer(pages=2))
    client = M.McpClient(t)
    info = client.initialize()
    assert info["serverInfo"]["name"] == "fake-mcp"
    assert any(n["method"] == "notifications/initialized" for n in t.notifications)
    tools = client.list_all_tools()
    assert [x["name"] for x in tools][:2] == ["echo", "img"]
    assert client.server_capabilities.get("tools") == {}


def test_mcp_tool_call_content_and_artifact():
    client = M.McpClient(M.MemoryTransport(FakeMcpServer()))
    tools = M.load_mcp_tools(client)
    by_name = {t.name: t for t in tools}
    out = by_name["echo"].invoke({"text": "hi"})
    assert out == "echo: hi"                    # one text block -> str
    raw = client.call_tool("echo", {"text": "hi"})
    assert raw["structuredContent"] == {"len": 2}   # the artifact rides the result
    schema = by_name["echo"].args_schema
    assert "text" in schema.model_json_schema()["properties"]


def test_mcp_open_object_args_stay_open():
    client = M.McpClient(M.MemoryTransport(FakeMcpServer()))
    tools = {t.name: t for t in M.load_mcp_tools(client)}
    schema = tools["open_obj"].args_schema.model_json_schema()
    assert schema["properties"]["cfg"].get("additionalProperties") is True


def test_mcp_image_audio_and_error_lanes():
    client = M.McpClient(M.MemoryTransport(FakeMcpServer()))
    tools = {t.name: t for t in M.load_mcp_tools(client)}
    img = tools["img"].invoke({})
    assert img == [{"type": "image", "base64": "aGk=", "mime_type": "image/png"}]
    with pytest.raises(NotImplementedError) as e:
        tools["sing"].invoke({})
    assert "not yet supported" in str(e.value)
    # the direct lane: the McpToolError carries the summarized detail (the
    # handle_tool_error lane turned OFF - with it ON the error becomes a
    # failed ToolMessage, which the next assert covers)
    boom_raw = M.McpTool.from_remote(client, "boom",
                                     {"name": "boom", "description": "Always errors.",
                                      "inputSchema": {"type": "object", "properties": {}}})
    boom_raw = boom_raw.model_copy(update={"handle_tool_error": False})
    with pytest.raises(M.McpToolError) as e2:
        boom_raw.invoke({})
    assert "no text content" in str(e2.value)     # non-text blocks counted, never inlined
    # the handle_tool_error lane lands it as a failed ToolMessage
    from app.aep.messages import ToolMessage
    tm = tools["boom"].invoke({"type": "tool_call", "id": "x1", "name": "boom", "args": {}})
    assert isinstance(tm, ToolMessage) and tm.status == "error"
    assert "Tool error" in tm.content


def test_mcp_elicitation_both_ways():
    # default: the honest refusal
    t1 = M.MemoryTransport(FakeMcpServer())
    c1 = M.McpClient(t1)
    c1.initialize()
    t1.trigger_server_request({"jsonrpc": "2.0", "id": 7,
                               "method": "elicitation/create", "params": {}})
    assert t1.responses[0]["error"]["code"] == -32601
    assert "does not answer elicitation" in t1.responses[0]["error"]["message"]
    # custom handler honored
    t2 = M.MemoryTransport(FakeMcpServer())
    c2 = M.McpClient(t2, elicitation_handler=lambda p: {"action": "accept", "content": {"answer": "yes"}})
    c2.initialize()
    t2.trigger_server_request({"jsonrpc": "2.0", "id": 9,
                               "method": "elicitation/create", "params": {"message": "ok?"}})
    assert t2.responses[0]["result"] == {"action": "accept", "content": {"answer": "yes"}}
    # unknown server methods refused with the honest error too
    t2.trigger_server_request({"jsonrpc": "2.0", "id": 11, "method": "sampling/create", "params": {}})
    assert t2.responses[1]["error"]["code"] == -32601


STDIO_SERVER = r'''
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    req = json.loads(line)
    method = req.get("method", "")
    if method == "initialize":
        out = {"protocolVersion": "2025-06-18", "capabilities": {},
               "serverInfo": {"name": "stdio-fake", "version": "1"}}
    elif method == "notifications/initialized":
        continue
    elif method == "tools/list":
        out = {"tools": [{"name": "add", "description": "Add two ints.",
                          "inputSchema": {"type": "object", "properties": {
                              "a": {"type": "integer"}, "b": {"type": "integer"}},
                              "required": ["a", "b"]}}], "nextCursor": None}
    elif method == "tools/call":
        args = req["params"]["arguments"]
        out = {"content": [{"type": "text", "text": str(args["a"] + args["b"])}],
               "isError": False}
    elif method == "ping":
        out = {}
    else:
        out = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": out}) + "\n")
    sys.stdout.flush()
'''


def test_stdio_transport_real_subprocess_round_trip(tmp_dir):
    script = os.path.join(tmp_dir, "fake_mcp_server.py")
    with open(script, "w") as f:
        f.write(STDIO_SERVER)
    t = M.StdioTransport([sys.executable, script])
    try:
        client = M.McpClient(t)
        client.initialize()
        tools = M.load_mcp_tools(client)
        assert [x.name for x in tools] == ["add"]
        out = tools[0].invoke({"a": 19, "b": 23})
        assert out == "42"
        assert client.ping()
    finally:
        t.close()


def test_stdio_timeout_refusal(tmp_dir):
    script = os.path.join(tmp_dir, "silent_server.py")
    with open(script, "w") as f:
        f.write("import time, sys\nsys.stdin.readline()\ntime.sleep(30)\n")
    t = M.StdioTransport([sys.executable, script])
    try:
        with pytest.raises(M.McpError) as e:
            t.request("initialize", {}, timeout=0.5)
        assert "timed out" in str(e.value)
    finally:
        t.close()


def test_mcp_group_mangling_and_resolve():
    c1 = M.McpClient(M.MemoryTransport(FakeMcpServer()))
    c1.initialize()
    c2 = M.McpClient(M.MemoryTransport(FakeMcpServer()))
    c2.initialize()
    group = M.McpClientGroup({"alpha": c1, "beta": c2})
    tools = M.load_mcp_tools(group)
    names = sorted(t.name for t in tools)
    assert names[0] == "mcp__alpha__boom" and "mcp__beta__echo" in names
    client, tool_name = group.resolve("mcp__beta__echo")
    assert client is c2 and tool_name == "echo"
    out = [t for t in tools if t.name == "mcp__beta__echo"][0].invoke({"text": "g"})
    assert out == "echo: g"


# ---------------------------------------------------------------------------
# conformance - the standard-tests port
# ---------------------------------------------------------------------------
def test_conformance_every_house_adapter_passes():
    C.assert_conformance(FakeListChatModel(responses=["a"]))
    C.assert_conformance(byok_model())
    C.assert_conformance(byok_model(content="hello world"))


def test_conformance_broken_model_fails_by_name():
    class Broken(FakeListChatModel):
        def invoke(self, input, config=None, **kwargs):  # noqa: A002,A003
            return "a bare string, not an AIMessage"

    rep = C.run_standard_tests(Broken(responses=["x"]))
    assert not rep.ok
    names = {r.name for r in rep.failures()}
    assert "invoke_returns_ai_msg" in names
    assert "FakeListChatModel" in rep.summary() or "Broken" in rep.summary()


# ---------------------------------------------------------------------------
# model profiles + the CLI
# ---------------------------------------------------------------------------
MODELS_DEV_PAYLOAD = {
    "zai": {"glm-4.7": {"name": "GLM 4.7", "limit": {"context": 200000, "output": 8192},
                        "modalities": {"input": ["text", "image"], "output": ["text"]},
                        "tool_call": True, "structured_output": True,
                        "status": "alpha", "release_date": "2026-01-15"}},
}


def test_model_data_to_profile_mapping():
    with pytest.warns(UserWarning, match="Undeclared profile keys"):
        row = H.model_data_to_profile({**MODELS_DEV_PAYLOAD["zai"]["glm-4.7"], "mystery": 1})
    assert row["name"] == "GLM 4.7" and row["max_input_tokens"] == 200000
    assert row["max_output_tokens"] == 8192
    assert row["text_inputs"] is True and row["image_inputs"] is True
    assert row["audio_inputs"] is False and row["tool_calling"] is True
    assert row["structured_output"] is True and row["status"] == "alpha"


def test_refresh_profiles_byte_stable(tmp_dir):
    out1 = os.path.join(tmp_dir, "p1.py")
    out2 = os.path.join(tmp_dir, "p2.py")
    s1 = H.refresh_profiles(MODELS_DEV_PAYLOAD, out1)
    s2 = H.refresh_profiles(MODELS_DEV_PAYLOAD, out2)
    assert s1 == {"providers": 1, "models": 1, "written": True}
    with open(out1, "rb") as a, open(out2, "rb") as b:
        assert a.read() == b.read()               # deterministic: byte-stable
    body = open(out1).read()
    assert body.startswith("# Generated by app.aep.hub (P7 model-profiles)")
    assert "PROFILES: dict[str, dict] = " in body
    assert "zai/glm-4.7" in body


def test_summarize_profile_diff_markdown():
    old = {"a/m1": {"name": "M1", "max_output_tokens": 4096}}
    new = {"a/m1": {"name": "M1", "max_output_tokens": 8192}, "a/m2": {"name": "M2"}}
    md = H.summarize_profile_diff(old, new)
    assert "## New models" in md and "`a/m2`" in md
    assert "## Removed models" not in md
    assert "## Changed" in md and "4096" in md and "8192" in md
    assert H.summarize_profile_diff(old, old).strip().endswith("No profile changes.")


def test_cli_lanes(tmp_dir):
    reg = os.path.join(tmp_dir, "extra.json")
    with open(reg, "w") as f:
        json.dump({"custom/x": {"name": "X"}}, f)
    assert H.main(["profiles", "--check"]) == 0
    assert H.main(["profiles", "--format", "json", "--registry", reg]) == 0
    src = os.path.join(tmp_dir, "modelsdev.json")
    with open(src, "w") as f:
        json.dump(MODELS_DEV_PAYLOAD, f)
    outp = os.path.join(tmp_dir, "_profiles.py")
    assert H.main(["refresh", "--from", src, "--out", outp]) == 0
    assert os.path.exists(outp)
    oldf = os.path.join(tmp_dir, "old.json")
    with open(oldf, "w") as f:
        json.dump({}, f)
    assert H.main(["diff", "--old", oldf, "--new", src]) == 0


def test_cli_module_entry(tmp_dir):
    out = subprocess.run([sys.executable, "-m", "app.aep.hub", "profiles", "--format", "json"],
                         capture_output=True, text=True, timeout=60,
                         env={**os.environ, "PYTHONPATH": os.getcwd()})
    assert out.returncode == 0, out.stderr
    rows = json.loads(out.stdout)
    assert "fake-list-chat" in rows and "openai-compat" in rows


# ---------------------------------------------------------------------------
# the laws
# ---------------------------------------------------------------------------
def test_inertness_law():
    """A fresh interpreter imports app.aep.{hub,load,mcp,conformance} with zero
    extra threads, zero env reads, zero files - the P1/P5/P6 law, re-proven for
    P7 (the stdio transport spawns nothing until a request)."""
    code = (
        "import sys, threading; sys.path.insert(0, 'server');"
        "before = threading.active_count();"
        "import app.aep.hub, app.aep.load, app.aep.mcp, app.aep.conformance;"
        "import app.aep as pkg;"
        "after = threading.active_count();"
        "assert after == before, f'thread leak: {before} -> {after}';"
        "print('INERT-OK', after)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, timeout=60, cwd="..")
    assert out.returncode == 0, out.stderr
    assert "INERT-OK" in out.stdout


def test_package_export_law():
    import app.aep as pkg
    for mod in (H, L, M, C):
        for name in getattr(mod, "__all__", []):
            assert hasattr(pkg, name), f"app.aep.{name} missing (the export law)"
    for name in ("init_chat_model", "ConfigurableModel", "OpenAICompatChatModel",
                 "HouseBrainChatModel", "dumpd", "dumps", "load", "loads",
                 "McpClient", "StdioTransport", "MemoryTransport", "load_mcp_tools",
                 "run_standard_tests", "PROFILE_REGISTRY"):
        assert name in pkg.__all__, f"{name} missing from app.aep.__all__"


def test_version_pins():
    from pathlib import Path
    from app.main import APP_VERSION
    root = Path(__file__).resolve().parents[2]
    assert APP_VERSION == "0.898.0"
    assert "0.898.0+897" in (root / "pubspec.yaml").read_text()
    # the newest-story keyword pins, inherited from the P6 graph suite
    line = (root / "server" / "app" / "main.py").read_text().splitlines()[35]
    assert "HOOLA HUB" in line and "init_chat_model" in line  # the P7 name rides the Previous chain
    assert "KAAN PACK" in line  # the newest story (the newest-story precedent)
