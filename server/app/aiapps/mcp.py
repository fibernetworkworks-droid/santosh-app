"""v0.785 HOOLA AI APPS - D2: one app as an MCP server (POST /mcp/aiapp/{code}, JSON-RPC 2.0).

One tool, `ask`. The caller needs a Bearer key of THIS app, the app must be live and its `mcp` channel on; the key's
limits apply exactly as on the service API. The tool's description is the app's PUBLIC name only - never her facts.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import keys as K
from . import store as ST

PROTOCOL = "2025-06-18"
SERVER = {"name": "hoola-aiapp", "version": "1.0"}


def _err(rid: Any, code: int, msg: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}}


def _ok(rid: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def tool_spec(a) -> dict[str, Any]:
    name = a.name or "this business"
    return {"name": "ask", "description": f"Ask {name}'s AI assistant a question (answers only about this business).",
            "inputSchema": {"type": "object", "properties": {
                "text": {"type": "string", "description": "The question"},
                "user": {"type": "string", "description": "A stable id for the person asking (keeps one conversation)"},
                "inputs": {"type": "object", "description": "Form fields, for a form app"}},
                "required": ["text"]}}


def make_router(require_key, current_tenant):  # noqa: ARG001 - the house signature; the app key is the auth here
    r = APIRouter()

    @r.post("/mcp/aiapp/{code}")
    async def mcp(code: str, request: Request):
        try:
            msg = await request.json()
        except Exception:                               # noqa: BLE001
            return JSONResponse(_err(None, -32700, "Parse error"), status_code=400)
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            return JSONResponse(_err(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request"),
                                status_code=400)
        rid, method = msg.get("id"), msg["method"]
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        got = await asyncio.to_thread(K.resolve, K.bearer(request), "mcp")
        if got is None or got[0].code != code:
            return JSONResponse(_err(rid, -32001, "Unauthorized: a valid key of this AI app is needed, the app must be live "
                                              "and its MCP channel on."), status_code=401)
        a, k = got
        if method.startswith("notifications/"):
            return JSONResponse(None, status_code=202)
        if method == "initialize":
            pv = str(params.get("protocolVersion") or PROTOCOL)[:20]
            return _ok(rid, {"protocolVersion": pv, "capabilities": {"tools": {"listChanged": False}},
                             "serverInfo": SERVER, "instructions": f"One tool, ask: questions for {a.name}."})
        if method == "ping":
            return _ok(rid, {})
        if method == "tools/list":
            return _ok(rid, {"tools": [tool_spec(a)]})
        if method == "tools/call":
            if params.get("name") != "ask":
                return _err(rid, -32602, f"Unknown tool: {params.get('name')!r}")
            args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            text = str(args.get("text") or "")
            if not text.strip() and not isinstance(args.get("inputs"), dict):
                return _err(rid, -32602, "text is required")
            inputs = args.get("inputs") if isinstance(args.get("inputs"), dict) else None
            try:
                with K.LIMITER.call(k):
                    out = await asyncio.to_thread(K.service_answer, a, text[:2000], str(args.get("user") or ""), inputs,
                                                  "mcp")
            except K.LimitError as e:
                return JSONResponse(_err(rid, -32029, str(e)), status_code=429, headers={"Retry-After": str(e.retry_after)})
            except ST.AppError as e:
                return _ok(rid, {"content": [{"type": "text", "text": str(e)}], "isError": True})
            return _ok(rid, {"content": [{"type": "text", "text": out["reply"]}], "isError": False})
        return _err(rid, -32601, f"Method not found: {method}")

    return r
