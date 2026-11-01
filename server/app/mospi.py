"""v0.348 MOSPI BUILT IN: official Government of India statistics from MoSPI's own MCP server (eSankhyiki).

https://mcp.mospi.gov.in/mcp (streamable HTTP, no login, no session, read-only). Four tools, one workflow:
  list_datasets -> get_indicators(dataset) -> get_metadata(dataset, indicator_code / base_year ...) -> get_data(dataset, filters)
31 datasets: CPI, WPI, IIP, NAS (GDP), PLFS (jobs), ASI, HCES, NFHS, AISHE, UDISE, ENERGY, GENDER, RBI ...
Built in for every user (no Connect tap), so "CPI kitni hai" is answered from MoSPI itself, never from a search summary.
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from .config import get_settings

URL = "https://mcp.mospi.gov.in/mcp"
PROTOCOL = "2025-06-18"
TOOLS = {"datasets": "list_datasets", "indicators": "get_indicators", "metadata": "get_metadata", "data": "get_data"}
TTL = {"list_datasets": 6 * 3600, "get_indicators": 6 * 3600, "get_metadata": 3600, "get_data": 900}
_CACHE: dict[str, tuple[float, Any]] = {}
STATS = {"calls": 0, "cached": 0, "errors": 0}


class MospiError(Exception):
    pass


def _url() -> str:
    return (getattr(get_settings(), "mospi_mcp_url", "") or URL).strip()


def _parse(text: str, ctype: str) -> dict[str, Any]:
    if "event-stream" in ctype or text.lstrip().startswith(("event:", "data:")):
        for d in reversed([ln[5:].strip() for ln in text.splitlines() if ln.startswith("data:")]):
            try:
                msg = json.loads(d)
            except ValueError:
                continue
            if isinstance(msg, dict) and ("result" in msg or "error" in msg):
                return msg
        raise MospiError("MoSPI ka jawab samajh nahi aaya.")
    try:
        return json.loads(text)
    except ValueError:
        raise MospiError("MoSPI ka jawab samajh nahi aaya.")


async def _rpc(name: str, args: dict[str, Any], timeout: float = 60.0) -> dict[str, Any]:
    body = {"jsonrpc": "2.0", "id": int(time.time() * 1000) % 1_000_000_000, "method": "tools/call",
            "params": {"name": name, "arguments": args}}
    STATS["calls"] += 1
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(_url(), json=body, headers={"Content-Type": "application/json",
                                                          "Accept": "application/json, text/event-stream",
                                                          "MCP-Protocol-Version": PROTOCOL})
    except httpx.HTTPError as e:
        STATS["errors"] += 1
        raise MospiError("MoSPI abhi jawab nahi de raha (network). Thodi der mein phir dekhte hain.") from e
    if r.status_code >= 400:
        STATS["errors"] += 1
        raise MospiError(f"MoSPI ne mana kiya (HTTP {r.status_code}).")
    msg = _parse(r.text, r.headers.get("content-type", ""))
    if msg.get("error"):
        STATS["errors"] += 1
        raise MospiError("MoSPI: " + str((msg["error"] or {}).get("message") or "error")[:300])
    return msg.get("result") or {}


def _clean(args: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (args or {}).items():
        if v is None or v == "" or v == {}:
            continue
        if k == "filters" and isinstance(v, dict):
            v = {str(fk): (fv if isinstance(fv, (int, float, bool)) else str(fv)) for fk, fv in v.items()
                 if fv not in (None, "")}
        out[k] = v
    return out


async def call(action: str, **args: Any) -> Any:
    """One MoSPI step. The answer is MoSPI's own structured content (or its text when it sent no structure)."""
    tool = TOOLS.get(str(action or "").strip().lower())
    if not tool:
        raise MospiError("action = datasets | indicators | metadata | data")
    a = {} if tool == "list_datasets" else _clean(args)
    if tool != "list_datasets" and not a.get("dataset"):
        raise MospiError("dataset chahiye (jaise CPI, IIP, NAS, PLFS) - pehle action=datasets.")
    if tool == "get_data" and isinstance(a.get("filters"), dict):
        a["filters"].setdefault("limit", "50")
    key = tool + ":" + json.dumps({k: v for k, v in a.items() if k != "user_query"}, sort_keys=True, ensure_ascii=False)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL[tool]:
        STATS["cached"] += 1
        return hit[1]
    res = await _rpc(tool, a)
    texts = [c.get("text", "") for c in res.get("content") or [] if isinstance(c, dict) and c.get("type") == "text"]
    if res.get("isError"):
        raise MospiError("MoSPI: " + (" ".join(texts).strip() or "is query ka data nahi mila")[:400])
    out: Any = res.get("structuredContent")
    if out is None:
        for t in texts:
            try:
                out = json.loads(t)
                break
            except ValueError:
                continue
    if out is None:
        out = "\n".join(texts)
    if len(_CACHE) > 300:
        _CACHE.clear()
    _CACHE[key] = (time.time(), out)
    return out
