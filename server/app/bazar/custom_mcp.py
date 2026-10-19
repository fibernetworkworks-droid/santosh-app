"""MCP servers the user adds to Santosh (from the directory or any https address).

Safety:
- only public https addresses; private, loopback, link-local and cloud-metadata addresses are refused
  (checked when added and again before every call), so a server address can never reach our own network;
- tools are read-only unless their name plainly reads (get/list/search...); everything else becomes a confirm
  card that shows the exact call, and only the frozen call runs after the user taps Approve;
- API keys are entered in the app (never in chat) and stored encrypted, like every other account link.
"""
from __future__ import annotations

import ipaddress
import json
import re
import secrets
import socket
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select

from . import directory
from .db import Connection, CustomMcp
from .packs.registry import Pack, add_resolver

MAX_PER_USER = 50
BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata"}


class UrlError(ValueError):
    pass


def check_url(url: str) -> str:
    url = (url or "").strip()
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname:
        raise UrlError("MCP address must start with https://")
    host = u.hostname.lower()
    if host in BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        raise UrlError("That address is not reachable from Santosh's server.")
    try:
        infos = socket.getaddrinfo(host, u.port or 443, proto=socket.IPPROTO_TCP)
    except OSError:
        raise UrlError(f"Could not find {host}. Check the address.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise UrlError("That address points to a private network; Santosh only connects to public MCP servers.")
    return url


def provider_of(row_id: str) -> str:
    return "custom:" + row_id


def to_pack(row: CustomMcp) -> Pack:
    entry = directory.get(row.directory_ref) if row.directory_ref else None
    words = set(re.findall(r"[a-z0-9]{3,}", f"{row.name} {row.directory_ref}".lower()))
    return Pack(id=row.id, name=row.name, category="My MCP servers", sub_category=(entry or {}).get("f", "MCP server"),
                pack_type="Custom MCP", layer="L1", phase="MVP", priority="P1",
                description=(row.description or (entry or {}).get("d", "") or "MCP server you added")[:400],
                notes="caution" if row.caution else "", master_list_row=0, executor="mcp",
                config={"provider": provider_of(row.id), "endpoint": row.url, "custom": True, "auth": row.auth,
                        "key_header": row.key_header, "owner": row.user_id, "caution": row.caution},
                tools=[], keywords=sorted(words)[:20])


def _resolve(pack_id: str) -> Pack | None:
    if not pack_id.startswith("mcp-"):
        return None
    from .db import session_factory
    s = session_factory()
    try:
        row = s.get(CustomMcp, pack_id)
        return to_pack(row) if row and row.status == "active" else None
    finally:
        s.close()


add_resolver(_resolve)


def user_rows(s, user_id: str) -> list[CustomMcp]:
    return list(s.scalars(select(CustomMcp).where(CustomMcp.user_id == user_id, CustomMcp.status == "active")
                          .order_by(CustomMcp.created_at)).all())


def create(s, user_id: str, url: str, name: str = "", ref: str = "", description: str = "") -> CustomMcp:
    url = check_url(url)
    rows = user_rows(s, user_id)
    for r in rows:
        if r.url.rstrip("/") == url.rstrip("/"):
            return r
    if len(rows) >= MAX_PER_USER:
        raise UrlError(f"You can add up to {MAX_PER_USER} MCP servers. Remove one first.")
    entry = directory.get(ref) if ref else None
    if entry and entry.get("blocked"):
        raise UrlError("Santosh does not connect unofficial personal-WhatsApp automation. "
                       "Use the official WhatsApp Business Platform instead.")
    if not name:
        name = entry["r"].split("/")[-1] if entry else (urlparse(url).hostname or "MCP server")
    row = CustomMcp(id="mcp-" + secrets.token_hex(5), user_id=user_id, name=name[:120], url=url,
                    directory_ref=entry["r"] if entry else (ref if ref.startswith("featured:") else ""),
                    description=(description or (entry or {}).get("d", ""))[:1000],
                    caution=bool(entry and entry["c"]))
    s.add(row)
    s.flush()
    return row


def headers_for(s, pack: Pack, user_id: str) -> dict[str, str] | None:
    """Auth headers for a custom server. None = the user must still link it (OAuth) or add its key."""
    cfg = pack.config
    if cfg.get("auth") == "none":
        return {}
    conn = s.scalars(select(Connection).where(Connection.user_id == user_id, Connection.provider == cfg["provider"],
                                              Connection.status == "active")).first()
    if not conn:
        return None
    if cfg.get("auth") == "key":
        from .security import vault
        b = json.loads(vault().open(conn.token_enc))
        h, v = b.get("header") or "Authorization", b["key"]
        if h.lower() == "authorization" and not re.match(r"(?i)(bearer|basic|token)\s", v):
            v = "Bearer " + v
        return {h: v}
    from .mcp_auth import access_token
    return {"Authorization": "Bearer " + access_token(s, conn)}


def save_key(s, row: CustomMcp, key: str, header: str = "") -> None:
    from .security import vault
    key = (key or "").strip()
    if not key or len(key) > 4000:
        raise UrlError("Paste the API key or token for this server.")
    header = (header or "Authorization").strip()
    if not re.fullmatch(r"[A-Za-z0-9-]{1,60}", header):
        raise UrlError("Header name can have letters, digits and '-' only.")
    for c in s.scalars(select(Connection).where(Connection.user_id == row.user_id,
                                                Connection.provider == provider_of(row.id))).all():
        c.status = "replaced"
    s.add(Connection(user_id=row.user_id, provider=provider_of(row.id),
                     token_enc=vault().seal(json.dumps({"key": key, "header": header})), status="active"))
    row.auth, row.key_header = "key", header
    s.flush()


def public(row: CustomMcp, status: str) -> dict[str, Any]:
    out = {"pack_id": row.id, "name": row.name, "url": row.url, "auth": row.auth, "status": status,
           "directory_ref": row.directory_ref, "does": row.description[:300]}
    if row.caution:
        out["caution"] = True
    return out


def probe(url: str, headers: dict[str, str] | None = None, client=None) -> tuple[str, str]:
    """Knock on the server with an MCP initialize call. Returns (result, note): ok | auth | error."""
    import httpx

    def guard(req: httpx.Request) -> None:
        check_url(str(req.url))
    own = client is None
    client = client or httpx.Client(timeout=15, follow_redirects=True, event_hooks={"request": [guard]})
    body = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "Santosh", "version": "1"}}}
    try:
        r = client.post(url, json=body, headers={"Accept": "application/json, text/event-stream", **(headers or {})})
    except UrlError as e:
        return "error", str(e)
    except httpx.HTTPError as e:
        return "error", f"Server not reachable ({type(e).__name__})"
    finally:
        if own:
            client.close()
    if r.status_code in (401, 403):
        return "auth", r.headers.get("www-authenticate", "")
    if r.status_code in (404, 405):
        return "error", ("No MCP endpoint at this address. Use the server's MCP URL (often ending in /mcp); "
                         "older SSE-only servers are not supported.")
    if r.status_code >= 400:
        return "error", f"Server answered {r.status_code}: {r.text[:160]}"
    return "ok", ""
