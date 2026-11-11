"""D8a HOOLA DESIGN PLUGIN RUNTIME - the server half (docs/HOOLA_DESIGN_PLAN.md section 8, D8a).

A plugin = {manifest: {id, name, version, description, permissions, ui, menu: [{label, command}]}, code: "<js>"}.
Permissions are exactly: read, edit, export, storage, net:<https host>. Nothing else exists.

What lives here
  table design_plugins      one row per (tenant, plugin id): manifest JSON, code, code_sha (sha256 of the code),
                            enabled, granted_permissions + granted_for_sha (her approval is bound to ONE code hash:
                            a code change leaves the old grant behind and every run is refused until she approves
                            again), storage (the plugin's own small key-value store), created_by / created_at.
  routes (signed in, under /api/design, mounted by api.make_router via mount(r, current_tenant, pub)):
    GET    /plugins                      -> {plugins: [summary]}          (no code)
    POST   /plugins {manifest, code}     -> {plugin}   install, or replace the code of one with the same id
    GET    /plugins/{id}                 -> {plugin}   with the code (the editor, the review dialog)
    PATCH  /plugins/{id} {enabled}       -> {plugin}
    POST   /plugins/{id}/grant {permissions, code_sha} -> {plugin}   a subset of the manifest's, for THIS code
    DELETE /plugins/{id}                 -> {ok}
    GET    /plugins/{id}/run             -> {plugin, code, permissions}  only when enabled AND approved for this code
    GET/PUT /plugins/{id}/storage        -> {data}     needs the storage grant; 256 KB a plugin
    POST   /plugins/{id}/fetch {url, method, body?, base64?, headers?}
                                         -> {status, ok, url, contentType, encoding: text|base64, body}
  public: GET /api/design/plugin-frame   the sandboxed RUNNER PAGE, generated here (no file on disk): the runner
                                         script (static/console/design/plugin-runner.js) inlined and allowed by its
                                         sha256 hash, under the page's OWN CSP (see FRAME_CSP).

THE FETCH PROXY (the only way a plugin reaches the network)
  https only, port 443, no user:password in the address, the host must be one of the plugin's GRANTED net: hosts
  (exact match), then the house SSRF guard (agent/scrape_tools._guard_url: public addresses only, after DNS); the
  address the connection really reached is checked AGAIN after connecting (DNS rebinding); redirects are followed by
  hand, at most 3, only to the SAME host over https (each re-guarded); 2 MB answer cap, 10 s time cap, 256 KB request
  body cap; the request carries ONLY the plugin's own allowlisted headers - never her token, never a cookie (the
  outgoing client has no cookie jar and no environment proxy). 120 fetches a minute per plugin.
  Tests monkeypatch `_http` (the one network seam) and the resolver - no real network.
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import re
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import Boolean, DateTime, Index, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, new_id, now, session

CODE_MAX = 200 * 1024                  # one plugin's code
STORAGE_MAX = 256 * 1024               # one plugin's own key-value store (JSON)
FETCH_BODY_MAX = 256 * 1024            # what a plugin may send out in one fetch
FETCH_ANSWER_MAX = 2 * 1024 * 1024     # what comes back
FETCH_TIMEOUT_S = 10.0
FETCH_REDIRECTS = 3
FETCH_PER_MIN = 120
PLUGINS_MAX = 100                      # plugins one account may keep
NET_HOSTS_MAX = 10
MENU_MAX = 20
BASE_PERMS = ("read", "edit", "export", "storage")
_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_CMD = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")
_HOST = re.compile(r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_HEADER_OK = {"accept", "accept-language", "content-type", "authorization", "x-api-key"}
_HEADER_NO = re.compile(r"^(x-forwarded|x-real-ip|x-client-ip|forwarded|cookie|host|proxy-)", re.I)
RUNNER_FILE = Path(__file__).resolve().parent.parent / "static" / "console" / "design" / "plugin-runner.js"


# ================================================================================ the table
class DesignPlugin(Base):
    __tablename__ = "design_plugins"
    __table_args__ = (Index("ix_design_plugins_tenant_plugin", "tenant_id", "plugin_id", unique=True),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dpl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    plugin_id: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[str] = mapped_column(Text, default="{}")
    code: Mapped[str] = mapped_column(Text, default="")
    code_sha: Mapped[str] = mapped_column(String(64), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_permissions: Mapped[str] = mapped_column(Text, default="[]")
    granted_for_sha: Mapped[str] = mapped_column(String(64), default="")
    storage: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_ready_for: int | None = None


def ensure_table() -> None:
    """Create design_plugins in place on a database that never saw it; keyed on the engine (every test opens one)."""
    global _ready_for
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None:
        _db.init_db()
        eng = _db._engine
    if _ready_for == id(eng):
        return
    DesignPlugin.__table__.create(eng, checkfirst=True)
    _db.add_missing_columns_for(eng, DesignPlugin.__table__)
    _ready_for = id(eng)


# ================================================================================ validation
class PluginError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def _text(v: Any, cap: int, what: str, need: bool = False) -> str:
    if v is None:
        v = ""
    if not isinstance(v, str):
        raise PluginError(f"The plugin's {what} must be text.")
    v = " ".join(v.split()) if what != "description" else v.strip()
    if len(v) > cap:
        raise PluginError(f"The plugin's {what} is longer than {cap} characters.")
    if need and not v:
        raise PluginError(f"The plugin needs a {what}.")
    return v


def perm_ok(p: Any) -> bool:
    if not isinstance(p, str):
        return False
    if p in BASE_PERMS:
        return True
    if p.startswith("net:"):
        host = p[4:]
        if not _HOST.match(host):
            return False
        try:                                 # an address written as numbers is not a host name
            ipaddress.ip_address(host)
            return False
        except ValueError:
            return True
    return False


def clean_manifest(m: Any) -> dict:
    """The manifest as stored: only the known fields, every one checked. Raises PluginError (422) in plain words."""
    if not isinstance(m, dict):
        raise PluginError("The manifest must be an object.")
    pid = m.get("id")
    if not isinstance(pid, str) or not _ID.match(pid):
        raise PluginError("The plugin id must be 2-64 characters: small letters, digits, '.', '_' or '-'.")
    name = _text(m.get("name"), 80, "name", need=True)
    version = _text(m.get("version") or "1.0.0", 20, "version")
    desc = _text(m.get("description"), 500, "description")
    perms_in = m.get("permissions") or []
    if not isinstance(perms_in, list):
        raise PluginError("permissions must be a list.")
    perms: list[str] = []
    for p in perms_in:
        if isinstance(p, str) and p.startswith("net:"):
            p = "net:" + p[4:].strip().lower()
        if not perm_ok(p):
            raise PluginError(f"'{str(p)[:80]}' is not a permission. Use read, edit, export, storage or net:<host name>.")
        if p not in perms:
            perms.append(p)
    if sum(1 for p in perms if p.startswith("net:")) > NET_HOSTS_MAX:
        raise PluginError(f"A plugin may ask for at most {NET_HOSTS_MAX} hosts.")
    ui = m.get("ui", False)
    if not isinstance(ui, bool):
        raise PluginError("ui must be true or false.")
    menu_in = m.get("menu") or []
    if not isinstance(menu_in, list) or len(menu_in) > MENU_MAX:
        raise PluginError(f"menu must be a list of at most {MENU_MAX} commands.")
    menu, seen = [], set()
    for item in menu_in:
        if not isinstance(item, dict):
            raise PluginError("Every menu entry needs a label and a command.")
        label = _text(item.get("label"), 60, "menu label", need=True)
        cmd = item.get("command")
        if not isinstance(cmd, str) or not _CMD.match(cmd):
            raise PluginError("A menu command is 1-40 letters, digits, '.', '_' or '-'.")
        if cmd in seen:
            raise PluginError(f"The command '{cmd}' is in the menu twice.")
        seen.add(cmd)
        menu.append({"label": label, "command": cmd})
    if not menu:
        menu = [{"label": "Run", "command": "run"}]
    return {"id": pid, "name": name, "version": version, "description": desc, "permissions": perms, "ui": ui, "menu": menu}


def clean_code(code: Any) -> str:
    if not isinstance(code, str):
        raise PluginError("The plugin's code must be text.")
    if len(code.encode("utf-8")) > CODE_MAX:
        raise PluginError(f"The plugin's code is larger than {CODE_MAX // 1024} KB.")
    if not code.strip():
        raise PluginError("The plugin has no code.")
    return code


def sha(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


# ================================================================================ rows
def _load(v: str | None, default):
    try:
        out = json.loads(v) if v else default
    except ValueError:
        return default
    return out if isinstance(out, type(default)) else default


def _row_out(row: DesignPlugin, with_code: bool = False) -> dict:
    granted = _load(row.granted_permissions, [])
    approved = bool(row.granted_for_sha) and row.granted_for_sha == row.code_sha
    out = {"id": row.plugin_id, "manifest": _load(row.manifest, {}), "code_sha": row.code_sha, "enabled": bool(row.enabled),
           "granted": granted if approved else [], "approved": approved,
           # a grant made for older code: she must look again (the code changed after she approved it)
           "needs_review": not approved, "stale_grant": bool(row.granted_for_sha) and not approved,
           "created_by": row.created_by or "", "created_at": as_utc(row.created_at).isoformat() if row.created_at else None,
           "updated_at": as_utc(row.updated_at).isoformat() if row.updated_at else None,
           "code_bytes": len((row.code or "").encode("utf-8"))}
    if with_code:
        out["code"] = row.code or ""
    return out


def _own(s, tenant: str, pid: str) -> DesignPlugin | None:
    return s.scalar(select(DesignPlugin).where(DesignPlugin.tenant_id == tenant, DesignPlugin.plugin_id == pid))


def list_plugins(tenant: str) -> list[dict]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(DesignPlugin).where(DesignPlugin.tenant_id == tenant).order_by(DesignPlugin.created_at)).all()
        return [_row_out(r) for r in rows]


def get_plugin(tenant: str, pid: str, with_code: bool = True) -> dict | None:
    ensure_table()
    with session() as s:
        row = _own(s, tenant, pid)
        return _row_out(row, with_code) if row else None


def install(tenant: str, manifest: Any, code: Any, by: str) -> dict:
    """A new plugin, or new code / manifest for one with the same id. The approval is NOT carried over to new code:
    it stays bound to the old hash, so every run is refused until she approves this code."""
    m, c = clean_manifest(manifest), clean_code(code)
    ensure_table()
    with session() as s:
        row = _own(s, tenant, m["id"])
        if row is None:
            count = len(s.scalars(select(DesignPlugin.id).where(DesignPlugin.tenant_id == tenant)).all())
            if count >= PLUGINS_MAX:
                raise PluginError(f"You can keep at most {PLUGINS_MAX} plugins. Remove one first.", 409)
            row = DesignPlugin(tenant_id=tenant, plugin_id=m["id"], created_by=(by or "")[:200], enabled=True)
            s.add(row)
        row.manifest = json.dumps(m, separators=(",", ":"))
        row.code = c
        row.code_sha = sha(c)
        row.updated_at = now()
        if row.granted_for_sha == row.code_sha:       # the same code again: her approval still fits it
            keep = [p for p in _load(row.granted_permissions, []) if p in m["permissions"]]
            row.granted_permissions = json.dumps(keep)
        s.flush()
        return _row_out(row, True)


def set_enabled(tenant: str, pid: str, enabled: bool) -> dict | None:
    ensure_table()
    with session() as s:
        row = _own(s, tenant, pid)
        if row is None:
            return None
        row.enabled = bool(enabled)
        row.updated_at = now()
        s.flush()
        return _row_out(row)


def grant(tenant: str, pid: str, permissions: Any, code_sha: Any) -> dict | None:
    ensure_table()
    with session() as s:
        row = _own(s, tenant, pid)
        if row is None:
            return None
        if not isinstance(code_sha, str) or not _SHA.match(code_sha):
            raise PluginError("Say which code you approved (code_sha).")
        if code_sha != row.code_sha:
            raise PluginError("The plugin's code changed after you looked at it. Look at it again before you approve it.", 409)
        asked = _load(row.manifest, {}).get("permissions") or []
        if not isinstance(permissions, list) or any(not isinstance(p, str) for p in permissions):
            raise PluginError("permissions must be a list of names.")
        extra = [p for p in permissions if p not in asked]
        if extra:
            raise PluginError(f"The plugin did not ask for {', '.join(extra[:5])}: only what it asks for can be approved.")
        keep = []
        for p in permissions:
            if p not in keep:
                keep.append(p)
        row.granted_permissions = json.dumps(keep)
        row.granted_for_sha = row.code_sha
        row.updated_at = now()
        s.flush()
        return _row_out(row)


def remove(tenant: str, pid: str) -> bool:
    ensure_table()
    with session() as s:
        row = _own(s, tenant, pid)
        if row is None:
            return False
        s.delete(row)
        return True


def runnable(tenant: str, pid: str) -> dict:
    """The plugin as it may run now, or a PluginError that says why not."""
    ensure_table()
    with session() as s:
        row = _own(s, tenant, pid)
        if row is None:
            raise PluginError("Plugin not found", 404)
        if not row.enabled:
            raise PluginError("This plugin is switched off. Switch it on in Plugins > Manage.", 409)
        if not row.granted_for_sha or row.granted_for_sha != row.code_sha:
            raise PluginError("This plugin's code has not been approved by you yet. Look at it and approve it in Plugins > Manage.", 409)
        return {"plugin": _row_out(row), "code": row.code or "", "permissions": _load(row.granted_permissions, [])}


def _needs(tenant: str, pid: str, perm_test) -> dict:
    got = runnable(tenant, pid)
    if not perm_test(got["permissions"]):
        raise PluginError("You did not give this plugin that permission.", 403)
    return got


def storage_get(tenant: str, pid: str) -> dict:
    _needs(tenant, pid, lambda ps: "storage" in ps)
    with session() as s:
        row = _own(s, tenant, pid)
        return _load(row.storage if row else None, {})


def storage_put(tenant: str, pid: str, data: Any) -> dict:
    if not isinstance(data, dict):
        raise PluginError("The plugin's storage is an object of keys.")
    text = json.dumps(data, separators=(",", ":"))
    if len(text.encode("utf-8")) > STORAGE_MAX:
        raise PluginError(f"A plugin may keep at most {STORAGE_MAX // 1024} KB.", 413)
    _needs(tenant, pid, lambda ps: "storage" in ps)
    with session() as s:
        row = _own(s, tenant, pid)
        row.storage = text
        row.updated_at = now()
        return data


# ================================================================================ the fetch proxy
class _Window:
    def __init__(self, limit: int, per_s: float = 60.0):
        self.limit, self.per_s, self.hits = limit, per_s, {}

    def allow(self, key: str) -> bool:
        t = time.monotonic()
        q = self.hits.setdefault(key, deque())
        while q and q[0] <= t - self.per_s:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(t)
        return True

    def reset(self) -> None:
        self.hits.clear()


FETCHES = _Window(FETCH_PER_MIN)


def _guard(url: str) -> None:
    """The house SSRF guard (the scrape lane's: public addresses only, checked after DNS)."""
    from ..agent.scrape_tools import _guard_url
    from ..agent.tools import ToolError
    try:
        _guard_url(url)
    except ToolError as e:
        raise PluginError(f"That address can not be reached from a plugin: {e}", 403) from None


def check_target(url: Any, hosts: list[str]) -> str:
    """https, the default port, no credentials in the address, one of the GRANTED hosts, then the SSRF guard."""
    if not isinstance(url, str) or not url or len(url) > 4096:
        raise PluginError("Give the address to fetch (url).")
    u = urlparse(url.strip())
    if u.scheme != "https":
        raise PluginError("A plugin may only fetch https:// addresses.", 403)
    if u.username or u.password:
        raise PluginError("An address with a user name or password in it is refused.", 403)
    host = (u.hostname or "").lower()
    try:
        port = u.port
    except ValueError:
        raise PluginError("That address has a broken port.", 403) from None
    if port not in (None, 443):
        raise PluginError("A plugin may only fetch over the normal https port.", 403)
    if host not in hosts:
        raise PluginError(f"This plugin may not talk to {host or 'that address'}: you did not give it that host.", 403)
    _guard(u.geturl())
    return u.geturl()


def _peer_ok(peer: str | None) -> bool:
    if not peer:
        return True                          # the seam could not tell: the guard before the call stands
    try:
        return ipaddress.ip_address(peer.split("%")[0]).is_global
    except ValueError:
        return False


async def _http(method: str, url: str, headers: dict, body: bytes | None, timeout: float, cap: int) -> dict:
    """THE network seam: one request, no redirects followed, no cookies, no environment proxy, at most cap + 1 bytes
    read. -> {status, headers: {lower name: value}, content: bytes, too_big: bool, peer: ip or None}.
    Tests monkeypatch exactly this."""
    import httpx                                     # lazy: importing this module must not need it
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout), follow_redirects=False, trust_env=False,
                                 headers={"User-Agent": "HoolaDesignPlugin/1"}) as cl:
        async with cl.stream(method, url, headers=headers, content=body) as r:
            peer = None
            try:
                ns = r.extensions.get("network_stream")
                addr = ns.get_extra_info("server_addr") if ns is not None else None
                peer = str(addr[0]) if addr else None
            except Exception:                        # noqa: BLE001 - the seam's own belt
                peer = None
            if not _peer_ok(peer):
                return {"status": 0, "headers": {}, "content": b"", "too_big": False, "peer": peer}
            chunks, size, too_big = [], 0, False
            async for chunk in r.aiter_bytes():
                size += len(chunk)
                if size > cap:
                    too_big = True
                    break
                chunks.append(chunk)
            return {"status": r.status_code, "headers": {k.lower(): v for k, v in r.headers.items()},
                    "content": b"".join(chunks), "too_big": too_big, "peer": peer}


def _out_headers(h: Any) -> dict:
    out: dict[str, str] = {}
    if not isinstance(h, dict):
        return out
    for k, v in list(h.items())[:20]:
        if not isinstance(k, str) or not isinstance(v, str) or len(k) > 64 or len(v) > 4096:
            continue
        key = k.strip().lower()
        if _HEADER_NO.match(key) or "\n" in v or "\r" in v:
            continue
        if key in _HEADER_OK or (key.startswith("x-") and re.match(r"^x-[a-z0-9-]{1,60}$", key)):
            out[key] = v
    return out


async def proxy_fetch(tenant: str, pid: str, req: Any) -> dict:
    from .room import bg
    if not isinstance(req, dict):
        raise PluginError("Send {url, method}.")
    got = await bg(runnable, tenant, pid)
    hosts = [p[4:] for p in got["permissions"] if isinstance(p, str) and p.startswith("net:")]
    if not hosts:
        raise PluginError("You did not give this plugin any host to talk to.", 403)
    method = str(req.get("method") or "GET").upper()
    if method not in ("GET", "POST"):
        raise PluginError("A plugin may only GET or POST.")
    body = None
    if method == "POST":
        raw = req.get("body")
        if raw is not None and not isinstance(raw, str):
            raise PluginError("The body must be text (or base64 with base64: true).")
        if raw:
            if req.get("base64"):
                try:
                    body = base64.b64decode(raw, validate=True)
                except (ValueError, TypeError):
                    raise PluginError("The body is not valid base64.") from None
            else:
                body = raw.encode("utf-8")
            if len(body) > FETCH_BODY_MAX:
                raise PluginError(f"A plugin may send at most {FETCH_BODY_MAX // 1024} KB.", 413)
    url = check_target(req.get("url"), hosts)
    if not FETCHES.allow(f"{tenant}\n{pid}"):
        raise PluginError("This plugin is fetching too often. Wait a minute.", 429)
    headers = _out_headers(req.get("headers"))
    host = urlparse(url).hostname
    deadline = time.monotonic() + FETCH_TIMEOUT_S
    for _ in range(FETCH_REDIRECTS + 1):
        left = deadline - time.monotonic()
        if left <= 0:
            raise PluginError("The other site took too long to answer.", 504)
        try:
            ans = await _http(method, url, headers, body, left, FETCH_ANSWER_MAX)
        except PluginError:
            raise
        except Exception as e:                       # noqa: BLE001 - a network failure, said plainly
            name = type(e).__name__
            if "Timeout" in name:
                raise PluginError("The other site took too long to answer.", 504) from None
            raise PluginError("The other site could not be reached.", 502) from None
        if not _peer_ok(ans.get("peer")) or ans.get("status") == 0:
            raise PluginError("That address leads into a private network: refused.", 403)
        status = int(ans.get("status") or 0)
        if status in (301, 302, 303, 307, 308):
            loc = (ans.get("headers") or {}).get("location") or ""
            nxt = urljoin(url, loc)
            pu = urlparse(nxt)
            if pu.scheme != "https" or (pu.hostname or "").lower() != host:
                raise PluginError("The site sent the plugin on to another address: refused.", 403)
            url = check_target(nxt, hosts)
            if status == 303 or (status in (301, 302) and method == "POST"):
                method, body = "GET", None
            continue
        if ans.get("too_big"):
            raise PluginError(f"The answer is larger than {FETCH_ANSWER_MAX // (1024 * 1024)} MB.", 413)
        content: bytes = ans.get("content") or b""
        ctype = str((ans.get("headers") or {}).get("content-type") or "")[:200]
        textual = bool(re.match(r"^(text/|application/(json|xml|javascript|[\w.+-]*\+json|[\w.+-]*\+xml)|image/svg\+xml)", ctype.lower()))
        if textual:
            try:
                return {"status": status, "ok": 200 <= status < 300, "url": url, "contentType": ctype,
                        "encoding": "text", "body": content.decode("utf-8")}
            except UnicodeDecodeError:
                pass
        return {"status": status, "ok": 200 <= status < 300, "url": url, "contentType": ctype,
                "encoding": "base64", "body": base64.b64encode(content).decode("ascii")}
    raise PluginError("The site sent the plugin round in circles: refused.", 403)


# ================================================================================ the runner page
def _runner_script() -> str:
    return RUNNER_FILE.read_text("utf-8")


def frame_page() -> tuple[str, str]:
    """The runner page + its CSP. The page is OURS only: its one script is plugin-runner.js, inlined and allowed by
    its hash. Plugin code never runs in this document - the runner starts it in a Web Worker made from a blob."""
    js = _runner_script()
    if "</script" in js.lower():
        raise RuntimeError("plugin-runner.js must not contain a closing script tag")
    digest = base64.b64encode(hashlib.sha256(js.encode("utf-8")).digest()).decode("ascii")
    html = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"robots\" content=\"noindex\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Plugin</title>"
            "<style>html,body{margin:0;padding:0;background:transparent;font:13px/1.45 system-ui,-apple-system,'Segoe UI',sans-serif;color:#1A1A1F}"
            "@media (prefers-color-scheme: dark){html,body{color:#ECEAF8}}#hp-ui{padding:12px}</style>"
            "</head><body><div id=\"hp-ui\"></div><script>" + js + "</script></body></html>")
    return html, FRAME_CSP.format(hash=digest)


# Why this is safe (the runner page, served with these headers, inside <iframe sandbox="allow-scripts">):
#  - the iframe has NO allow-same-origin, so this document's origin is OPAQUE: it can not read the console's
#    localStorage (her token), cookies, IndexedDB or DOM, and the console's origin is not its origin;
#  - script-src = the runner's own hash only: no inline handler, no other script, and NO 'unsafe-eval' - plugin
#    code is not evaluated here at all, it runs in a Worker built from a blob (worker-src blob:), and the Worker
#    inherits this policy (so eval / new Function / importScripts are refused inside it too);
#  - connect-src 'none' (fetch, XHR, WebSocket, EventSource, beacons - in the page AND in its Worker), img-src
#    data: blob: only, font-src / frame-src / object-src / media-src fall back to default-src 'none': nothing leaves
#    this page by itself, all network goes through the host -> the server proxy above;
#  - form-action 'none' + no allow-forms, no allow-popups, no allow-top-navigation, no allow-modals on the iframe;
#  - frame-ancestors 'self': only the console may embed it. The console's own CSP is untouched (frame-src 'self'
#    already allows this same-origin URL, and it also bars this frame from navigating itself to another site).
FRAME_CSP = ("default-src 'none'; script-src 'sha256-{hash}'; worker-src blob:; connect-src 'none'; img-src data: blob:; "
             "style-src 'unsafe-inline'; font-src 'none'; media-src 'none'; object-src 'none'; frame-src 'none'; "
             "child-src 'none'; manifest-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'")
FRAME_HEADERS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store",
                 "Permissions-Policy": "camera=(), microphone=(), geolocation=(), usb=(), serial=(), hid=(), bluetooth=(), "
                                       "payment=(), clipboard-read=(), clipboard-write=(), display-capture=()"}


# ================================================================================ the routes
async def _json(request: Request, cap: int) -> Any:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > cap:
        raise HTTPException(413, f"The request is larger than {cap // 1024} KB.")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > cap:
            raise HTTPException(413, f"The request is larger than {cap // 1024} KB.")
        chunks.append(chunk)
    try:
        return json.loads(b"".join(chunks) or b"{}")
    except ValueError:
        raise HTTPException(400, "Send JSON.") from None


def _http_error(e: PluginError) -> HTTPException:
    return HTTPException(e.status, str(e))


def mount(r, current_tenant, pub=None) -> None:
    """The plugin routes on the design router (key + switch already checked by it) and the public runner page."""
    from . import store
    from .room import bg

    @r.get("/plugins")
    async def plugins_list(tenant: str = Depends(current_tenant)):
        return {"plugins": await bg(list_plugins, tenant)}

    @r.post("/plugins")
    async def plugins_install(request: Request, tenant: str = Depends(current_tenant)):
        body = await _json(request, CODE_MAX + 64 * 1024)
        if not isinstance(body, dict):
            raise HTTPException(400, "Send {manifest, code}.")
        try:
            by = await bg(store.who, tenant)
            return {"plugin": await bg(install, tenant, body.get("manifest"), body.get("code"), by)}
        except PluginError as e:
            raise _http_error(e) from None

    @r.get("/plugins/{pid}")
    async def plugins_one(pid: str, tenant: str = Depends(current_tenant)):
        got = await bg(get_plugin, tenant, pid, True)
        if got is None:
            raise HTTPException(404, "Plugin not found")
        return {"plugin": got}

    @r.patch("/plugins/{pid}")
    async def plugins_patch(pid: str, request: Request, tenant: str = Depends(current_tenant)):
        body = await _json(request, 4096)
        if not isinstance(body, dict) or not isinstance(body.get("enabled"), bool):
            raise HTTPException(422, "Send {enabled: true | false}.")
        got = await bg(set_enabled, tenant, pid, body["enabled"])
        if got is None:
            raise HTTPException(404, "Plugin not found")
        return {"plugin": got}

    @r.post("/plugins/{pid}/grant")
    async def plugins_grant(pid: str, request: Request, tenant: str = Depends(current_tenant)):
        body = await _json(request, 16 * 1024)
        if not isinstance(body, dict):
            raise HTTPException(400, "Send {permissions, code_sha}.")
        try:
            got = await bg(grant, tenant, pid, body.get("permissions"), body.get("code_sha"))
        except PluginError as e:
            raise _http_error(e) from None
        if got is None:
            raise HTTPException(404, "Plugin not found")
        return {"plugin": got}

    @r.delete("/plugins/{pid}")
    async def plugins_delete(pid: str, tenant: str = Depends(current_tenant)):
        if not await bg(remove, tenant, pid):
            raise HTTPException(404, "Plugin not found")
        return {"ok": True}

    @r.get("/plugins/{pid}/run")
    async def plugins_run(pid: str, tenant: str = Depends(current_tenant)):
        try:
            return await bg(runnable, tenant, pid)
        except PluginError as e:
            raise _http_error(e) from None

    @r.get("/plugins/{pid}/storage")
    async def plugins_storage_get(pid: str, tenant: str = Depends(current_tenant)):
        try:
            return {"data": await bg(storage_get, tenant, pid)}
        except PluginError as e:
            raise _http_error(e) from None

    @r.put("/plugins/{pid}/storage")
    async def plugins_storage_put(pid: str, request: Request, tenant: str = Depends(current_tenant)):
        body = await _json(request, STORAGE_MAX + 4096)
        if not isinstance(body, dict):
            raise HTTPException(400, "Send {data}.")
        try:
            return {"data": await bg(storage_put, tenant, pid, body.get("data"))}
        except PluginError as e:
            raise _http_error(e) from None

    @r.post("/plugins/{pid}/fetch")
    async def plugins_fetch(pid: str, request: Request, tenant: str = Depends(current_tenant)):
        body = await _json(request, FETCH_BODY_MAX * 2 + 16 * 1024)
        try:
            return await proxy_fetch(tenant, pid, body)
        except PluginError as e:
            raise _http_error(e) from None

    if pub is not None:
        from .api import _on

        @pub.get("/plugin-frame", dependencies=[Depends(_on)])
        async def plugin_frame():
            """The sandboxed runner page. No sign-in on purpose: an iframe can not send her key, and the page holds
            nothing - it only ever talks to the editor that embeds it, through postMessage."""
            html, csp = frame_page()
            return Response(html, media_type="text/html; charset=utf-8", headers={**FRAME_HEADERS, "Content-Security-Policy": csp})
