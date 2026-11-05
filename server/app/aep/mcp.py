"""HOOLA AEP mcp - the Model Context Protocol client adapter, the langchain
`langchain/mcp/` idea hand-built for the house (upstream reference read at
github.com/langchain-ai/langchain @ aa2528fb, libs/langchain_v1/langchain/mcp/
{adapter.py 245 lines, tools.py 307, elicitation.py 394} - upstream rides
FastMCP; the house speaks the MCP wire itself, JSON-RPC 2.0 over stdio, because
the port law is zero new pip and zero upstream code).

v0.581.0 HOOLA HUB (P7 of the AEP plan): the client + the tool adapter.

- `StdioTransport`  - one MCP server as a subprocess (stdio, line-delimited
  JSON-RPC 2.0, a lazy reader thread with real request timeouts - the thread
  exists only from the first request, never on import: the inertness law).
- `MemoryTransport` - an in-process server object for the suites (zero
  subprocess, zero network - the tests drive the same protocol dicts).
- `McpClient`       - the session: the `initialize` handshake (protocol
  2025-06-18), `tools/list` with cursor pagination, `tools/call`, `ping`, and
  the server->client `elicitation/create` request (custom handler honored; the
  default answers with an honest error - the house never pretends a human
  spoke).
- `McpClientGroup`  - several named servers under one tool surface, names
  mangled `mcp__<server>__<tool>` and resolved back per call.
- `load_mcp_tools(target)` / `McpTools` - MCP tools as house BaseTools ready
  for create_agent: the inputSchema becomes a real pydantic args model (open
  object args stay open - upstream _normalize_mcp_schema), content blocks
  convert (text/image/file; audio refuses honestly), `isError=True` becomes a
  ToolException so the tool's handle_tool_error lane lands the server's own
  detail in a ToolMessage with status="error" (the upstream tools.py law), and
  structuredContent rides as the artifact.

A STRING TARGET MUST BE AN URL - and the house client refuses URLs: the house
client speaks stdio and in-memory only, so a bare string is rejected at the
gate (upstream adapter.py's reason stands: a string from config or a model
must never silently become a subprocess).

Inert library: no subprocess, no thread, no env read on import - the P1
kill-switch note holds for P7 too.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from .tools import BaseTool, ToolException

PROTOCOL_VERSION = "2025-06-18"
JSONRPC = "2.0"
_PARSE_ERROR = -32700
_METHOD_NOT_FOUND = -32601
_BAD_PARAMS = -32602
_CLIENT_ERROR = -32000


class McpError(RuntimeError):
    """A transport-level failure (the process died, a request timed out)."""


class McpJsonRpcError(McpError):
    """The server answered a request with a JSON-RPC error object."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"JSON-RPC error {code}: {message}")


# ---------------------------------------------------------------------------
# transports
# ---------------------------------------------------------------------------


class BaseTransport(ABC):
    """One MCP connection: request in, result out."""

    on_server_request: Callable[[dict[str, Any]], None] | None = None
    """Set by McpClient: the server->client request lane (elicitation)."""

    @abstractmethod
    def request(self, method: str, params: dict[str, Any] | None = None,
                *, timeout: float | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def notify(self, method: str, params: dict[str, Any] | None = None) -> None: ...

    def close(self) -> None:  # noqa: B027 - optional for in-memory transports
        pass


class StdioTransport(BaseTransport):
    """One MCP server as a subprocess speaking line-delimited JSON-RPC 2.0.

    The reader thread starts on the first request (never on import - the
    inertness law) and pumps responses into a slot map guarded by one
    condition; requests wait on it with a real timeout, so a wedged server
    surfaces as `McpError: timed out` instead of a blocked lane.
    """

    def __init__(self, command: str | list[str], args: list[str] | None = None,
                 env: dict[str, str] | None = None, cwd: str | None = None) -> None:
        import subprocess
        self.command = command if isinstance(command, list) else [command]
        if args:
            self.command = [*self.command, *args]
        self.env = env
        self.cwd = cwd
        self._proc: Any = None
        self._cond: threading.Condition | None = None
        self._slots: dict[int | str, dict[str, Any] | None] = {}
        self._reader: threading.Thread | None = None
        self._closed = False
        self._server_requests: list[dict[str, Any]] = []  # surfaced, never dropped
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()

    # -- internals -----------------------------------------------------------

    def _ensure_proc(self) -> Any:
        if self._proc is not None:
            return self._proc
        import subprocess
        try:
            self._proc = subprocess.Popen(  # noqa: S603 - the owner asked for this command
                self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1,
                env=self.env, cwd=self.cwd)
        except OSError as e:
            raise McpError(f"MCP server {self.command[0]!r} not startable: {e}") from e
        self._cond = threading.Condition()
        self._reader = threading.Thread(target=self._pump, daemon=True,
                                        name="hoola-aep-mcp-reader")
        self._reader.start()
        return self._proc

    def _pump(self) -> None:
        proc = self._proc
        assert proc is not None and proc.stdout is not None
        cond = self._cond
        assert cond is not None
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue
            if "method" in msg and "id" not in msg:      # a server notification
                with self._lock:
                    self._server_requests.append(msg)
                continue
            if "method" in msg and "id" in msg:           # a server REQUEST (elicitation)
                with self._lock:
                    self._server_requests.append(msg)
                handler = self.on_server_request
                if handler is not None:
                    try:
                        handler(msg)
                    except Exception:  # noqa: BLE001 - the lane must never die on a handler
                        pass
                continue
            if "id" in msg:
                with cond:
                    self._slots[msg["id"]] = msg
                    cond.notify_all()

    def _send(self, payload: dict[str, Any]) -> None:
        proc = self._ensure_proc()
        if self._closed or proc.poll() is not None:
            raise McpError("MCP server is not running")
        assert proc.stdin is not None
        try:
            with self._write_lock:
                proc.stdin.write(json.dumps(payload, default=str) + "\n")
                proc.stdin.flush()
        except (OSError, ValueError) as e:
            raise McpError(f"MCP server pipe broken: {e}") from e

    # -- the transport surface -----------------------------------------------

    def request(self, method: str, params: dict[str, Any] | None = None,
                *, timeout: float | None = None) -> dict[str, Any]:
        rid = uuid.uuid4().hex[:12]
        self._send({"jsonrpc": JSONRPC, "id": rid, "method": method,
                    "params": params or {}})
        cond = self._cond
        assert cond is not None
        deadline = None if timeout is None else time.monotonic() + timeout
        with cond:
            while self._slots.get(rid) is None:
                if self._proc is not None and self._proc.poll() is not None:
                    raise McpError(f"MCP server exited while answering {method!r}")
                if deadline is None:
                    cond.wait(0.05)
                else:
                    left = deadline - time.monotonic()
                    if left <= 0:
                        self._slots.pop(rid, None)
                        raise McpError(f"MCP request {method!r} timed out after {timeout}s")
                    cond.wait(min(left, 0.05))
            msg = self._slots.pop(rid)
        assert msg is not None
        if "error" in msg:
            err = msg["error"] or {}
            raise McpJsonRpcError(int(err.get("code", _CLIENT_ERROR)),
                                  str(err.get("message", "unknown error")),
                                  err.get("data"))
        return msg.get("result") or {}

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send({"jsonrpc": JSONRPC, "method": method, "params": params or {}})

    def respond(self, rid: Any, result: dict[str, Any] | None = None,
                error: dict[str, Any] | None = None) -> None:
        """Answer a server->client request (elicitation) on this transport."""
        payload: dict[str, Any] = {"jsonrpc": JSONRPC, "id": rid}
        if error is not None:
            payload["error"] = error
        else:
            payload["result"] = result or {}
        self._send(payload)

    def close(self) -> None:
        self._closed = True
        proc = self._proc
        if proc is None:
            return
        try:
            if proc.stdin is not None:
                proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:  # noqa: BLE001 - a dead child is a fine close state
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
        self._proc = None


class MemoryTransport(BaseTransport):
    """An in-process MCP server for the suites: the server object answers the
    same protocol dicts, zero subprocess and zero network (zero-network test
    law). `server` owes `handle(method, params)` -> result dict (raise
    `McpJsonRpcError` for protocol errors). For the server->client lane the
    stub calls `transport.trigger_server_request(req)`; the client's answer
    lands in `self.responses`."""

    def __init__(self, server: Any) -> None:
        self.server = server
        self.notifications: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []

    def request(self, method: str, params: dict[str, Any] | None = None,
                *, timeout: float | None = None) -> dict[str, Any]:  # noqa: ARG002
        return self.server.handle(method, params or {})

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self.notifications.append({"method": method, "params": params or {}})

    def trigger_server_request(self, req: dict[str, Any]) -> None:
        handler = self.on_server_request
        if handler is not None:
            handler(req)

    def respond(self, rid: Any, result: dict[str, Any] | None = None,
                error: dict[str, Any] | None = None) -> None:
        self.responses.append({"id": rid, "result": result, "error": error})


# ---------------------------------------------------------------------------
# the client session
# ---------------------------------------------------------------------------

ElicitationHandler = Callable[[dict[str, Any]], dict[str, Any]]


class McpClient:
    """One MCP session over a transport (upstream mcp/adapter.py, hand-built).

    `initialize()` performs the handshake; `tools/list` paginates;
    `tools/call` answers with the raw MCP result dict. Elicitation: a custom
    handler is honored; the default refuses with an honest error - the house
    never fakes a human answer.
    """

    def __init__(self, transport: BaseTransport, *, name: str = "hoola-aep",
                 version: str = "0.581.0",
                 elicitation_handler: ElicitationHandler | None = None,
                 timeout: float | None = None) -> None:
        self.transport = transport
        self.client_name = name
        self.client_version = version
        self.elicitation_handler = elicitation_handler
        self.timeout = timeout
        self.server_info: dict[str, Any] | None = None
        self.server_capabilities: dict[str, Any] = {}
        self._initialized = False
        if hasattr(transport, "on_server_request"):
            transport.on_server_request = self.handle_server_request

    # -- the server->client lane ----------------------------------------------

    def handle_server_request(self, req: dict[str, Any]) -> None:
        """Answer `elicitation/create`: the custom handler is honored; the
        default refuses with an honest error - the house never fakes a human
        answer (the upstream elicitation.py idea, house-shaped)."""
        rid = req.get("id")
        method = req.get("method")
        if method != "elicitation/create":
            respond = getattr(self.transport, "respond", None)
            if respond:
                respond(rid, error={"code": _METHOD_NOT_FOUND,
                                    "message": f"the house client does not serve {method!r}"})
            return
        handler = self.elicitation_handler
        respond = getattr(self.transport, "respond", None)
        if handler is None:
            if respond:
                respond(rid, error={"code": _METHOD_NOT_FOUND,
                                    "message": "this client does not answer elicitation "
                                               "(no handler wired - the honest refusal)"})
            return
        try:
            answer = handler(req.get("params") or {})
        except Exception as e:  # noqa: BLE001 - a broken handler is an error response
            if respond:
                respond(rid, error={"code": _CLIENT_ERROR, "message": f"elicitation handler failed: {e}"})
            return
        if respond:
            respond(rid, answer if isinstance(answer, dict) else {"action": "decline"})

    # -- lifecycle -----------------------------------------------------------

    def initialize(self, *, timeout: float | None = None) -> dict[str, Any]:
        result = self.transport.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": self.client_name, "version": self.client_version},
        }, timeout=timeout if timeout is not None else self.timeout)
        self.server_info = result.get("serverInfo") or None
        self.server_capabilities = result.get("capabilities") or {}
        self.transport.notify("notifications/initialized")
        self._initialized = True
        return result

    def _ensure_ready(self) -> None:
        if not self._initialized:
            self.initialize()

    # -- the surface ---------------------------------------------------------

    def list_tools(self, cursor: str | None = None) -> dict[str, Any]:
        self._ensure_ready()
        params: dict[str, Any] = {} if cursor is None else {"cursor": cursor}
        return self.transport.request("tools/list", params, timeout=self.timeout)

    def list_all_tools(self) -> list[dict[str, Any]]:
        """The full tool list across cursor pages, in server order."""
        out: list[dict[str, Any]] = []
        cursor: str | None = None
        seen_pages = 0
        while True:
            page = self.list_tools(cursor)
            out.extend(page.get("tools") or [])
            cursor = page.get("nextCursor")
            seen_pages += 1
            if not cursor or seen_pages > 100:
                break
        return out

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """The raw MCP CallToolResult dict: content / structuredContent / isError."""
        self._ensure_ready()
        result = self.transport.request("tools/call", {"name": name, "arguments": arguments or {}},
                                        timeout=self.timeout)
        return {"content": result.get("content") or [],
                "structuredContent": result.get("structuredContent"),
                "isError": bool(result.get("isError"))}

    def ping(self) -> bool:
        self.transport.request("ping", {}, timeout=self.timeout)
        return True

    def close(self) -> None:
        self.transport.close()


class McpClientGroup:
    """Several named servers under one tool surface (upstream ClientGroup idea).

    Tool names are mangled `mcp__<server>__<tool>` so two servers' tools never
    collide; `resolve` unmangles for the call.
    """

    def __init__(self, clients: dict[str, McpClient]) -> None:
        self.clients = dict(clients)

    def list_all_tools(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for server_name, client in self.clients.items():
            for tool in client.list_all_tools():
                t = dict(tool)
                t["name"] = f"mcp__{server_name}__{tool.get('name', '')}"
                out.append(t)
        return out

    def resolve(self, mangled: str) -> tuple[McpClient, str]:
        prefix = "mcp__"
        if not mangled.startswith(prefix):
            raise McpError(f"Group tool {mangled!r} is not a mangled name")
        rest = mangled[len(prefix):]
        server, _, tool = rest.partition("__")
        client = self.clients.get(server)
        if client is None:
            raise McpError(f"Group tool {mangled!r} names no known server {server!r}")
        return client, tool


# ---------------------------------------------------------------------------
# content conversion (upstream mcp/tools.py, hand-built)
# ---------------------------------------------------------------------------

def _summarize_tool_error(blocks: list[dict[str, Any]]) -> str:
    """The server's own error text; non-text blocks counted, never inlined."""
    parts = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
    if parts:
        return "\n".join(p for p in parts if p)
    if blocks:
        return ("The MCP tool reported an error with no text content "
                f"({len(blocks)} non-text content block(s)).")
    return "The MCP tool reported an error with empty content."


def _convert_block(block: dict[str, Any]) -> dict[str, Any]:
    """One MCP content block -> its house content-block dict (upstream shape)."""
    if not isinstance(block, dict):
        raise McpError(f"Unknown MCP content type: {type(block).__name__}")
    btype = block.get("type")
    if btype == "text":
        return {"type": "text", "text": block.get("text", "")}
    if btype == "image":
        return {"type": "image", "base64": block.get("data", ""),
                "mime_type": block.get("mimeType", "")}
    if btype == "audio":
        raise NotImplementedError(
            "Converting MCP audio content to a house content block is not yet "
            f"supported. Received audio with mime type: {block.get('mimeType')}")
    if btype == "resource_link":
        mime = block.get("mimeType") or None
        if mime and mime.startswith("image/"):
            return {"type": "image", "url": block.get("uri", ""), "mime_type": mime}
        return {"type": "file", "url": block.get("uri", ""), "mime_type": mime}
    if btype == "resource":
        resource = block.get("resource") or {}
        if "text" in resource:
            return {"type": "text", "text": resource.get("text", "")}
        if "blob" in resource:
            mime = resource.get("mimeType") or None
            if mime and mime.startswith("image/"):
                return {"type": "image", "base64": resource.get("blob", ""), "mime_type": mime}
            return {"type": "file", "base64": resource.get("blob", ""), "mime_type": mime}
    raise McpError(f"Unknown MCP content type: {btype!r} "
                   "(usually means the server is newer than this adapter)")


def blocks_to_content(blocks: list[dict[str, Any]]) -> str | list[dict[str, Any]]:
    """MCP content blocks -> house ToolMessage content (one text block = str)."""
    house = [_convert_block(b) for b in blocks]
    if len(house) == 1 and house[0].get("type") == "text":
        return house[0]["text"]
    return house


def _normalize_mcp_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Open object args stay open (upstream _normalize_mcp_schema ported)."""
    normalized = dict(schema or {})
    properties = (schema or {}).get("properties")
    if not isinstance(properties, dict):
        return normalized
    normalized["properties"] = dict(properties)
    for name, value in properties.items():
        if not isinstance(value, dict):
            continue
        types = value.get("type")
        is_object = types == "object" or (isinstance(types, list) and "object" in types)
        if (is_object and not value.get("properties")
                and "additionalProperties" not in value
                and "unevaluatedProperties" not in value):
            normalized["properties"][name] = {**value, "additionalProperties": True}
    return normalized


_SIMPLE_TYPES: dict[str, Any] = {"string": str, "integer": int, "number": float,
                                 "boolean": bool, "array": list, "object": dict}


def schema_dict_to_model(name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """A JSON Schema dict -> a real pydantic args model (so the house `.args`
    surface stays rich for the model-facing wire)."""
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    fields: dict[str, tuple[Any, Any]] = {}
    for pname, spec in props.items():
        spec = spec if isinstance(spec, dict) else {}
        stype = spec.get("type")
        ann: Any = Any
        if isinstance(stype, list):
            ann = tuple(_SIMPLE_TYPES.get(t, Any) for t in stype if t != "null") or Any
        elif stype in _SIMPLE_TYPES:
            ann = _SIMPLE_TYPES[stype]
        if spec.get("description"):
            fields[pname] = (ann, Field(
                default=... if pname in required else spec.get("default"),
                description=spec["description"]))
        else:
            fields[pname] = (ann, ... if pname in required else spec.get("default"))
    model = create_model(f"{name}Args", **fields)
    ap = schema.get("additionalProperties")
    if ap is False:
        model.model_config = ConfigDict(extra="forbid")
    else:
        model.model_config = ConfigDict(extra="allow")
    return model


class McpToolError(ToolException):
    """The MCP tool RAN and reported failure (isError=True) - upstream law: this
    reaches the model as a failed ToolMessage carrying the server's own detail;
    transport failures are plain McpError and stay exceptions, never output."""

    def __init__(self, summary: str, blocks: list[dict[str, Any]]) -> None:
        super().__init__(summary)
        self.blocks = blocks


class McpTool(BaseTool):
    """An MCP tool as a house BaseTool: every invocation calls through the
    client (upstream as_langchain_tool shape, hand-built)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    client_ref: Any
    remote_name: str
    tool_meta: dict[str, Any] = Field(default_factory=dict)
    args_schema_model: Any = None

    @classmethod
    def from_remote(cls, client: Any, remote_name: str, definition: dict[str, Any],
                    *, name: str | None = None, server_info: dict[str, Any] | None = None) -> "McpTool":
        schema = _normalize_mcp_schema(definition.get("inputSchema") or {})
        args_model = schema_dict_to_model(definition.get("name") or remote_name, schema)
        meta: dict[str, Any] = {}
        if definition.get("annotations") is not None:
            meta["annotations"] = definition.get("annotations")
        if definition.get("_meta") is not None:
            meta["_meta"] = definition.get("_meta")
        mcp_meta: dict[str, Any] = {}
        if meta:
            mcp_meta["tool"] = meta
        if server_info:
            mcp_meta["server"] = server_info
        return cls(name=name or definition.get("name") or remote_name,
                   description=definition.get("description") or "",
                   client_ref=client, remote_name=remote_name,
                   tool_meta=mcp_meta, args_schema_model=args_model,
                   response_format="content_and_artifact",
                   handle_tool_error=True)

    @property
    def args_schema(self) -> type[BaseModel] | None:  # type: ignore[override]
        return self.args_schema_model

    def _client(self) -> Any:
        client = self.client_ref
        if isinstance(client, McpClientGroup):
            return client.resolve(self.remote_name)
        return client

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        if args:  # a bare-string call: an MCP tool is always object-args
            raise ToolException(
                f"MCP tool {self.name!r} takes object arguments, got a bare string")
        client = self.client_ref
        call_name = self.remote_name
        if isinstance(client, McpClientGroup):
            client, call_name = client.resolve(self.remote_name)
        result = client.call_tool(call_name, kwargs)
        content = blocks_to_content(result["content"])
        if result["isError"]:
            raise McpToolError(_summarize_tool_error(result["content"]), result["content"])
        artifact = None
        if result["structuredContent"] is not None:
            artifact = {"structured_content": result["structuredContent"]}
        if artifact is not None:
            return content, artifact
        return content

    def _artifact(self, content: Any) -> Any:  # noqa: ARG002
        return None


# ---------------------------------------------------------------------------
# the load lanes
# ---------------------------------------------------------------------------


def _coerce_client(target: Any, *, elicitation_handler: ElicitationHandler | None,
                   timeout: float | None) -> McpClient:
    if isinstance(target, McpClient):
        return target
    if isinstance(target, McpClientGroup):
        return target
    if isinstance(target, BaseTransport):
        client = McpClient(target, elicitation_handler=elicitation_handler, timeout=timeout)
        client.initialize()
        return client
    if isinstance(target, dict):
        if "command" in target:
            transport = StdioTransport(target["command"], target.get("args") or [],
                                       env=target.get("env"), cwd=target.get("cwd"))
            client = McpClient(transport, elicitation_handler=elicitation_handler,
                               timeout=timeout)
            client.initialize()
            return client
        if "url" in target:
            raise McpError(
                "The house MCP client speaks stdio and in-memory transports; "
                f"an HTTP target {target['url']!r} is refused at the gate - a URL "
                "client is an honest gap, not a silent one")
        raise McpError("An MCP config dict needs 'command' (stdio); got keys "
                       f"{sorted(target)}")
    if isinstance(target, str):
        raise McpError(
            f"MCP target {target!r} is a string, so it would be read as a URL - "
            "refused at the gate (a bare string must never silently become a "
            "subprocess). Pass a config dict {'command': ...} for stdio, a "
            "MemoryTransport for in-process, or an McpClient you built.")
    raise McpError(f"Unsupported MCP target: {type(target).__name__}")


def load_mcp_tools(target: Any, *, server_name: str | None = None,
                   elicitation_handler: ElicitationHandler | None = None,
                   timeout: float | None = None,
                   close_on_exit: bool = False) -> list[BaseTool]:
    """MCP tools as house BaseTools (upstream MCPAdapter.list_tools idea).

    `target` may be a live McpClient (caller owns the lifecycle), a
    BaseTransport, or a stdio config dict - the latter two are initialized
    here; pass `close_on_exit=True` for one-shot loads, or use the `McpTools`
    context manager when the tools must outlive the call.
    """
    client = _coerce_client(target, elicitation_handler=elicitation_handler, timeout=timeout)
    try:
        definitions = client.list_all_tools()
    except Exception:
        if close_on_exit and not isinstance(target, (McpClient, BaseTransport)):
            client.close()
        raise
    tools: list[BaseTool] = []
    if isinstance(client, McpClientGroup):
        for server_name, member in client.clients.items():
            for definition in member.list_all_tools():
                mangled = f"mcp__{server_name}__{definition.get('name', '')}"
                tool = McpTool.from_remote(client, mangled, definition,
                                           name=mangled,
                                           server_info=member.server_info)
                tools.append(tool)
        return tools
    for definition in definitions:
        tool = McpTool.from_remote(client, definition.get("name") or "", definition,
                                   server_info=client.server_info)
        if server_name:
            tool.name = f"mcp__{server_name}__{tool.name}"
        tools.append(tool)
    return tools


class McpTools:
    """The context-manager lane: open the server, load the tools, close on exit.

        with McpTools({"command": "mcp-server-x"}) as tools:
            agent = create_agent(model, tools)
    """

    def __init__(self, target: Any, *, elicitation_handler: ElicitationHandler | None = None,
                 timeout: float | None = None) -> None:
        self._target = target
        self._elicitation_handler = elicitation_handler
        self._timeout = timeout
        self.client: McpClient | None = None
        self.tools: list[BaseTool] = []

    def __enter__(self) -> list[BaseTool]:
        self.client = _coerce_client(self._target,
                                     elicitation_handler=self._elicitation_handler,
                                     timeout=self._timeout)
        tools = load_mcp_tools(self.client)
        if isinstance(self.client.transport, StdioTransport) and not isinstance(
                self._target, (McpClient, BaseTransport)):
            pass  # the client owns the transport; closed on exit below
        self.tools = tools
        return tools

    def __exit__(self, *exc: Any) -> None:
        if self.client is not None and not isinstance(self._target, (McpClient, BaseTransport)):
            self.client.close()
        self.client = None
        self.tools = []


__all__ = [
    "BaseTransport", "McpClient", "McpClientGroup", "McpError", "McpJsonRpcError",
    "McpTool", "McpToolError", "McpTools", "MemoryTransport", "PROTOCOL_VERSION",
    "StdioTransport", "blocks_to_content", "load_mcp_tools", "schema_dict_to_model",
]
