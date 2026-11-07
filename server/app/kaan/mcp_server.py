"""KAAN W5 MCP server: her ears over the Model Context Protocol, stdio door.

The same 18 actions the `kaan` tool serves, now reachable from any MCP client
(Claude Desktop, another agent's house client) on HER box: one tool named `kaan`
with the action enum - the house law travels with the door (actions, not tools).
Dispatch goes through agent.kaan_tools._sync itself, so the MCP door can never
drift from the tool door: same gates (audio ingest rides kaan_audio), same honest
refusals, same notes. Actor is `owner` by construction - this server runs on her
machine with her env; pairing her MCP client here is pairing a device, physically.

The wire is line-delimited JSON-RPC 2.0 (initialize / tools/list / tools/call /
ping), protocol 2025-06-18 - the version the house MCP client (aep.mcp) speaks.
Zero new pip, zero network on import (the inertness law): every import happens on
the first request, never at module load.

Run:  $CORE/.venv/bin/python -m app.kaan.mcp_server        (HOOLA_TENANT env picks the tenant)
"""
from __future__ import annotations

import json
from typing import Any

PROTOCOL_VERSION = "2025-06-18"          # aep.mcp.PROTOCOL_VERSION - one wire, both sides
JSONRPC = "2.0"
_PARSE_ERROR = -32700
_METHOD_NOT_FOUND = -32601
_BAD_PARAMS = -32602

_SERVER_INFO_NAME = "hoola-kaan"


def _version() -> str:
    try:
        from ..main import APP_VERSION   # lazy + late: the version truth is app.main's
        return APP_VERSION
    except Exception:                    # noqa: BLE001 - a broken import must not fake a version
        return "unknown"


def _tenant() -> str:
    import os
    t = os.environ.get("HOOLA_TENANT", "").strip()
    if t:
        return t
    try:
        from ..config import get_settings
        return get_settings().tenant_id
    except Exception:                    # noqa: BLE001 - config off -> the house default
        return "default"


def _dispatch(tenant: str, args: dict[str, Any]) -> dict[str, Any]:
    """ONE dispatch path with the agent tool: kaan_tools._sync on a minimal owner Ctx."""
    from ..agent.kaan_tools import _sync
    from ..agent.tools import Ctx
    action = str(args.get("action") or "")
    ctx = Ctx(tenant_id=tenant, conversation_id=str(args.get("conversation_id") or ""))
    return _sync(ctx, action, args)


def _tool_call(tenant: str, params: dict[str, Any]) -> dict[str, Any]:
    """tools/call -> MCP content result; an honest refusal is isError=True, never a crash."""
    name = str((params or {}).get("name") or "")
    args = (params or {}).get("arguments") or {}
    if name != "kaan":
        return {"content": [{"type": "text", "text": f"unknown tool '{name}' - this server serves exactly one tool: kaan."}],
                "isError": True}
    try:
        out = _dispatch(tenant, dict(args))
    except Exception as e:               # noqa: BLE001 - ValueError / KaanError / LiveError land here
        return {"content": [{"type": "text", "text": str(e)}], "isError": True}
    return {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}],
            "structuredContent": out, "isError": False}


def handle(req: dict[str, Any], tenant: str) -> dict[str, Any] | None:
    """One JSON-RPC request -> one response envelope (None for notifications)."""
    method = str(req.get("method") or "")
    rid = req.get("id")
    if rid is None:                      # a notification: acknowledge nothing, answer nothing
        return None

    def result(res: Any) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC, "id": rid, "result": res}

    def err(code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC, "id": rid, "error": {"code": code, "message": message}}

    if method == "initialize":
        return result({"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}},
                       "serverInfo": {"name": _SERVER_INFO_NAME, "version": _version()}})
    if method == "ping":
        return result({})
    if method == "tools/list":
        from ..agent.kaan_tools import KAAN_TOOLS
        return result({"tools": [dict(KAAN_TOOLS[0])]})
    if method == "tools/call":
        params = req.get("params")
        if not isinstance(params, dict):
            return err(_BAD_PARAMS, "tools/call needs params: {name, arguments}")
        return result(_tool_call(tenant, params))
    return err(_METHOD_NOT_FOUND, f"method '{method}' is not known - initialize, tools/list, tools/call, ping.")


def respond(line: str, tenant: str) -> dict[str, Any] | None:
    """One stdin line -> one response (None when nothing may be written back)."""
    try:
        req = json.loads(line)
    except ValueError:
        return {"jsonrpc": JSONRPC, "id": None, "error": {"code": _PARSE_ERROR, "message": "Parse error"}}
    if not isinstance(req, dict):
        return {"jsonrpc": JSONRPC, "id": None, "error": {"code": _PARSE_ERROR, "message": "Parse error"}}
    return handle(req, tenant)


def main() -> None:
    import sys
    tenant = _tenant()
    for line in sys.stdin:
        out = respond(line, tenant)
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
