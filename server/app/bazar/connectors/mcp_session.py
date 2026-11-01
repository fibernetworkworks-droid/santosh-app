"""v0.344 sticky MCP sessions for servers whose login lives INSIDE one MCP session (Zerodha Kite MCP, FYERS MCP).

These servers have no OAuth: their `login` tool returns a link, she signs in on the broker's own page, and the broker
ties that login to the MCP session id (Mcp-Session-Id) the link was made in. Hoola's normal client opens a fresh
session for every call, so the login would be lost at once. This client keeps ONE session per (her account, server):
the id is stored encrypted (bz_kv, vault) and sent on every call; when the server forgets it (restart, expiry) a new
session is opened and the server itself answers "please log in" again.

Plain JSON-RPC over streamable HTTP (one POST per request, JSON or SSE answer), same result shape as McpHttpRemote.
It never sees her password / OTP / TOTP: those stay on the broker's page."""
from __future__ import annotations

import json
from typing import Any, Callable

import httpx

PROTOCOL = "2025-06-18"
TIMEOUT = 40.0


class SessionLost(Exception):
    pass


def _parse(text: str, ctype: str) -> dict[str, Any]:
    if "event-stream" in ctype or text.lstrip().startswith(("event:", "data:")):
        for d in reversed([ln[5:].strip() for ln in text.splitlines() if ln.startswith("data:")]):
            try:
                msg = json.loads(d)
            except ValueError:
                continue
            if isinstance(msg, dict) and ("result" in msg or "error" in msg):
                return msg
        return {}
    try:
        return json.loads(text) if text.strip() else {}
    except ValueError:
        return {}


class SessionRemote:
    """get_sid() -> stored session id or ""; put_sid(sid) stores it ("" forgets it)."""

    def __init__(self, url: str, get_sid: Callable[[], str], put_sid: Callable[[str], None],
                 client: httpx.Client | None = None, guard: Callable[[str], Any] | None = None):
        self.url, self.get_sid, self.put_sid = url, get_sid, put_sid
        self.client = client
        self.guard = guard
        self._n = 0

    # ------------------------------------------------------------------ transport
    def _post(self, body: dict[str, Any], sid: str) -> httpx.Response:
        from .mcp_remote import RemoteError
        if self.guard:
            self.guard(self.url)
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
             "MCP-Protocol-Version": PROTOCOL}
        if sid:
            h["Mcp-Session-Id"] = sid
        try:
            if self.client is not None:
                return self.client.post(self.url, json=body, headers=h)
            with httpx.Client(timeout=TIMEOUT, follow_redirects=False) as c:
                return c.post(self.url, json=body, headers=h)
        except httpx.HTTPError as e:
            raise RemoteError(f"network: {type(e).__name__}") from None

    def _open(self) -> str:
        from .mcp_remote import RemoteError
        self._n += 1
        r = self._post({"jsonrpc": "2.0", "id": self._n, "method": "initialize",
                        "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                                   "clientInfo": {"name": "Hoola", "version": "1"}}}, "")
        if r.status_code >= 400:
            raise RemoteError(f"HTTP {r.status_code}")
        sid = r.headers.get("mcp-session-id", "")
        if sid:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
        self.put_sid(sid)
        return sid

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        from .mcp_remote import RemoteAuthError, RemoteError
        sid = self.get_sid() or self._open()
        for attempt in (1, 2):
            self._n += 1
            r = self._post({"jsonrpc": "2.0", "id": self._n, "method": method, "params": params}, sid)
            msg = _parse(r.text, r.headers.get("content-type", ""))
            gone = r.status_code == 404 or (r.status_code == 400 and "session" in r.text.lower()) or (
                isinstance(msg.get("error"), dict) and "session" in str(msg["error"].get("message", "")).lower())
            if gone and attempt == 1:
                self.put_sid("")          # the server forgot this session: a new one (she logs in again)
                sid = self._open()
                continue
            if r.status_code in (401, 403):
                raise RemoteAuthError(r.status_code, r.headers.get("www-authenticate", ""))
            if r.status_code >= 400:
                raise RemoteError(f"HTTP {r.status_code}")
            if msg.get("error"):
                raise RemoteError(str((msg["error"] or {}).get("message") or "error")[:300])
            return msg.get("result") or {}
        raise RemoteError("session could not be opened")

    # ------------------------------------------------------------------ RemoteTools
    def list_tools(self) -> list[dict[str, Any]]:
        res = self._rpc("tools/list", {})
        out = []
        for t in res.get("tools") or []:
            ro = (t.get("annotations") or {}).get("readOnlyHint")
            out.append({"name": t.get("name", ""), "description": t.get("description") or "",
                        "input_schema": t.get("inputSchema") or {"type": "object"},
                        "read_only": ro if isinstance(ro, bool) else None})
        return [t for t in out if t["name"]]

    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        res = self._rpc("tools/call", {"name": name, "arguments": args or {}})
        texts = [c.get("text", "") for c in res.get("content") or [] if isinstance(c, dict) and c.get("type") == "text"]
        out: dict[str, Any] = {"is_error": bool(res.get("isError")), "text": "\n".join(texts)}
        if res.get("structuredContent"):
            out["data"] = res["structuredContent"]
        else:
            for t in texts:
                try:
                    out["data"] = json.loads(t)
                    break
                except ValueError:
                    continue
        return out


def store(session, user_id: str, pack_id: str) -> tuple[Callable[[], str], Callable[[str], None]]:
    """The session id lives encrypted in bz_kv under her account + this server only."""
    from ..db import KVState
    from ..security import vault
    key = f"mcp_sid:{user_id}:{pack_id}"[:200]

    def get() -> str:
        row = session.get(KVState, key)
        if row is None or not row.value:
            return ""
        try:
            return vault().open(row.value)
        except ValueError:
            return ""

    def put(sid: str) -> None:
        session.merge(KVState(key=key, value=vault().seal(sid) if sid else ""))
        session.commit()
    return get, put
