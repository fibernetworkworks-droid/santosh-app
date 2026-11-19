"""v0.348 MOSPI BUILT IN: official Government of India statistics from MoSPI's own MCP server (eSankhyiki).

https://mcp.mospi.gov.in/mcp (streamable HTTP, no login, no session, read-only). Four tools, one workflow:
  list_datasets -> get_indicators(dataset) -> get_metadata(dataset, indicator_code / base_year ...) -> get_data(dataset, filters)
31 datasets: CPI, WPI, IIP, NAS (GDP), PLFS (jobs), ASI, HCES, NFHS, AISHE, UDISE, ENERGY, GENDER, RBI ...
Built in for every user (no Connect tap), so "CPI kitni hai" is answered from MoSPI itself, never from a search summary.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from .config import get_settings

URL = "https://mcp.mospi.gov.in/mcp"
PROTOCOL = "2025-06-18"
TOOLS = {"datasets": "list_datasets", "indicators": "get_indicators", "metadata": "get_metadata", "data": "get_data"}
TTL = {"list_datasets": 6 * 3600, "get_indicators": 6 * 3600, "get_metadata": 3600, "get_data": 900}
_CACHE: dict[str, tuple[float, Any]] = {}
STATS = {"calls": 0, "cached": 0, "errors": 0, "retries": 0}
LAST_ERROR: dict[str, Any] = {}     # v0.349 the exact reason of the last failure (vps check / logs), never shown raw to her
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
           "MCP-Protocol-Version": PROTOCOL, "User-Agent": "Hoola/1.0 (+https://hoola.ainewtika.com; MoSPI eSankhyiki MCP client)"}
log = logging.getLogger("santosh.mospi")


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
        raise MospiError("Could not read MoSPI's answer.")
    try:
        return json.loads(text)
    except ValueError:
        raise MospiError("Could not read MoSPI's answer.")


def _why(e: BaseException) -> str:
    """The network failure in plain words (timeout / DNS / refused / TLS), for the log and the vps check."""
    n = type(e).__name__
    t = str(e)[:160]
    if isinstance(e, httpx.TimeoutException):
        return f"timeout ({n})"
    if "Name or service not known" in t or "getaddrinfo" in t or "nodename" in t:
        return f"DNS failed ({n})"
    if "refused" in t.lower():
        return f"connection refused ({n})"
    if "SSL" in t or "certificate" in t.lower():
        return f"TLS problem ({n}: {t})"
    return f"{n}: {t}"


async def _rpc(name: str, args: dict[str, Any], timeout: float = 45.0) -> dict[str, Any]:
    """One tools/call. v0.349: a network failure (timeout, connect, DNS) is tried once more after a short pause; the
    exact reason is logged and kept in LAST_ERROR; HTTP refusals carry their status code."""
    body = {"jsonrpc": "2.0", "id": int(time.time() * 1000) % 1_000_000_000, "method": "tools/call",
            "params": {"name": name, "arguments": args}}
    STATS["calls"] += 1
    tmo = httpx.Timeout(timeout, connect=10.0)
    r = None
    for attempt in (1, 2):
        try:
            async with httpx.AsyncClient(timeout=tmo, follow_redirects=True) as c:
                r = await c.post(_url(), json=body, headers=HEADERS)
            break
        except httpx.HTTPError as e:
            why = _why(e)
            LAST_ERROR.update(at=time.time(), tool=name, why=why, attempt=attempt)
            log.warning("MoSPI %s attempt %d failed: %s", name, attempt, why)
            if attempt == 2:
                STATS["errors"] += 1
                raise MospiError(f"MoSPI's server could not be reached right now ({why}). Let's look again in a little while.") from e
            STATS["retries"] += 1
            await asyncio.sleep(1.5)
    assert r is not None
    if r.status_code >= 400:
        STATS["errors"] += 1
        LAST_ERROR.update(at=time.time(), tool=name, why=f"HTTP {r.status_code}", body=r.text[:200])
        log.warning("MoSPI %s refused: HTTP %s %s", name, r.status_code, r.text[:200].replace("\n", " "))
        raise MospiError(f"MoSPI refused (HTTP {r.status_code}).")
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
        raise MospiError("a dataset is needed (for example CPI, IIP, NAS, PLFS) - run action=datasets first.")
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
        raise MospiError("MoSPI: " + (" ".join(texts).strip() or "no data was found for this query")[:400])
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


def check() -> dict[str, Any]:
    """`python -m app.mospi check` on the VPS: can this server reach MoSPI, and how fast? (one free read call)."""
    t = time.time()
    try:
        out = asyncio.run(_rpc("list_datasets", {}))
        n = len(((out.get("structuredContent") or {}).get("datasets") or {})) if isinstance(out, dict) else 0
        if not n:
            for c in out.get("content") or []:
                try:
                    n = len(json.loads(c.get("text", "")).get("datasets") or {})
                except (ValueError, AttributeError):
                    pass
        return {"ok": True, "datasets": n, "seconds": round(time.time() - t, 2), "url": _url()}
    except MospiError as e:
        return {"ok": False, "error": str(e), "detail": dict(LAST_ERROR), "seconds": round(time.time() - t, 2),
                "url": _url()}


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["check"]:
        print(json.dumps(check(), indent=1, default=str))
    else:
        print("usage: python -m app.mospi check")
