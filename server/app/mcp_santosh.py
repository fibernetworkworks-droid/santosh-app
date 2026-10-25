"""Santosh MCP server (v0.182): a small read-only slice of Santosh, served to any MCP client.

Who calls it:
    Claude Desktop, Cursor, Windsurf, or any MCP host, added by the user with a bearer token
    from POST /api/mcp/santosh/tokens (shown once, stored hashed).

What it serves (v1, 7 read-only tools):
    notebook_list, notebook_open, notebook_ask (save forced off),
    drive_find, drive_list_folder, drive_read_file, drive_storage.

What is NOT served in v1:
    Writes / approval cards / background jobs (drive_share, drive_trash, notebook_delete,
    notebook_studio, notebook_make, drive_upload, drive_create_doc). Those need either an
    elicitation surface or the app's own confirm card; add per-client once we build that.

Safety:
    Every tool is readOnlyHint=True. Tokens are SHA-256 hashed. Rate limit is per-token
    (60/min) so a leaked token or a looping client can't hammer Drive / Notebook.

Layout:
    Full URL:  {PUBLIC_BASE_URL}/santosh/mcp
    Mounted at /santosh, inner path /mcp — the /mcp prefix is already used by Commerce.
"""
from __future__ import annotations

import hashlib
import secrets
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import anyio.to_thread
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from .agent.drive_tools import DRIVE_HANDLERS
from .agent.notebook_tools import NOTEBOOK_HANDLERS
from .agent.tools import Ctx
from .bazar.db import McpSantoshToken, session_factory
from .bazar.service import ensure_user
from .config import get_settings

try:  # mcp>=2; the whole module is skipped by main.py if unavailable
    from mcp.server.mcpserver import MCPServer
    from mcp.types import ToolAnnotations
except ImportError:  # pragma: no cover
    MCPServer = None  # type: ignore[assignment]
    ToolAnnotations = None  # type: ignore[assignment]

MOUNT_PREFIX = "/santosh"
INNER_PATH = "/mcp"
MOUNT_PATH = MOUNT_PREFIX + INNER_PATH

INSTRUCTIONS = """Santosh (read-only): the user's own notebooks and Google Drive.

Notebooks are Hoola's NotebookLM equivalent — sources (URLs, PDFs, notes) and cited Q&A.
Drive is the user's own Google Drive.

All tools are read-only. Anything that would create, modify, share or delete is deliberately
absent from v1; if the user asks for that, tell them to do it in the Santosh app. Notebook
answers carry [n] citations to exact source passages — quote them to the user."""


# ----------------------------------------------------------------------------- tokens
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(session, user_id: str, label: str = "") -> str:
    token = "snt_santosh_" + secrets.token_urlsafe(32)
    session.add(McpSantoshToken(user_id=user_id, token_hash=hash_token(token), label=label[:80]))
    session.flush()
    return token


def resource_url() -> str:
    return get_settings().public_base_url.rstrip("/") + MOUNT_PATH


class DbTokenVerifier:
    async def verify_token(self, token: str):
        from mcp.server.auth.provider import AccessToken

        def lookup():
            with session_factory() as db:
                row = db.scalars(select(McpSantoshToken).where(
                    McpSantoshToken.token_hash == hash_token(token),
                    McpSantoshToken.revoked.is_(False))).first()
                return (row.user_id, row.label) if row else None
        found = await anyio.to_thread.run_sync(lookup)
        if not found:
            return None
        uid, label = found
        return AccessToken(token=token, client_id=label or "santosh-client",
                           scopes=["notebook:read", "drive:read"], subject=uid,
                           resource=resource_url())


# ----------------------------------------------------------------------------- per-call ctx
def _current_user_id() -> str:
    from mcp.server.auth.middleware.auth_context import get_access_token
    tok = get_access_token()
    if tok is None or not tok.subject:
        raise RuntimeError("Not signed in to Santosh.")
    return tok.subject


@contextmanager
def _ctx(tool_name: str) -> Iterator[Ctx]:
    """Ctx for a handler call — actor='mcp:<tool>', conversation_id empty (no live card published)."""
    user_id = _current_user_id()
    yield Ctx(tenant_id=user_id, conversation_id="", actor=f"mcp:{tool_name}")


# ----------------------------------------------------------------------------- MCP server
def build_server(user_resolver=None):
    if MCPServer is None:
        raise RuntimeError("mcp>=2 not installed")
    from mcp.server.auth.settings import AuthSettings

    st = get_settings()
    base = st.public_base_url.rstrip("/")
    kwargs: dict[str, Any] = {}
    if user_resolver is None:
        kwargs = {"token_verifier": DbTokenVerifier(),
                  "auth": AuthSettings(issuer_url=base, resource_server_url=resource_url(),
                                       validate_token_resource=False)}
    srv = MCPServer("santosh-readonly", title="Santosh (read-only)",
                    instructions=INSTRUCTIONS, version="0.1.0",
                    website_url="https://www.ainewtika.com", **kwargs)
    ro = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

    @srv.tool(annotations=ro)
    async def notebook_list() -> dict:
        """The user's Hoola notebooks (title, id, source count)."""
        with _ctx("notebook_list") as ctx:
            return await NOTEBOOK_HANDLERS["notebook_list"](ctx)

    @srv.tool(annotations=ro)
    async def notebook_open(notebook: str) -> dict:
        """A notebook's sources, notes, studio items and chat settings.
        Pass the notebook's name or id (from notebook_list)."""
        with _ctx("notebook_open") as ctx:
            return await NOTEBOOK_HANDLERS["notebook_open"](ctx, notebook=notebook)

    @srv.tool(annotations=ro)
    async def notebook_ask(notebook: str, question: str) -> dict:
        """Ask a question answered only from the notebook's ticked sources, with [n] citations.
        Saving is disabled in MCP for now — this is a pure read."""
        with _ctx("notebook_ask") as ctx:
            return await NOTEBOOK_HANDLERS["notebook_ask"](ctx, notebook=notebook,
                                                          question=question, save=False)

    @srv.tool(annotations=ro)
    async def drive_find(query: str = "", kind: str = "any", starred: bool = False,
                         shared_with_me: bool = False, modified_days: int = 0,
                         limit: int = 20) -> dict:
        """Search Drive. Empty query = recent files. kind: any|pdf|doc|sheet|slides|image|video|folder.
        modified_days limits to files changed in the last N days (0 = no limit)."""
        with _ctx("drive_find") as ctx:
            return await DRIVE_HANDLERS["drive_find"](
                ctx, query=query, kind=kind, starred=starred, shared_with_me=shared_with_me,
                modified_days=modified_days or None, limit=limit)

    @srv.tool(annotations=ro)
    async def drive_list_folder(folder: str = "", limit: int = 50) -> dict:
        """List a Drive folder (name, link, or id; empty = My Drive)."""
        with _ctx("drive_list_folder") as ctx:
            return await DRIVE_HANDLERS["drive_list_folder"](
                ctx, folder=folder or None, limit=limit)

    @srv.tool(annotations=ro)
    async def drive_read_file(file: str) -> dict:
        """Read a Drive file's text (Google Docs/Sheets/Slides, PDF, Word, Excel, CSV, text).
        Pass the file's id, Drive link, or name."""
        with _ctx("drive_read_file") as ctx:
            return await DRIVE_HANDLERS["drive_read_file"](ctx, file=file)

    @srv.tool(annotations=ro)
    async def drive_storage() -> dict:
        """Drive usage, connected accounts, recent files."""
        with _ctx("drive_storage") as ctx:
            return await DRIVE_HANDLERS["drive_storage"](ctx)

    return srv


# ----------------------------------------------------------------------------- API router (inlined)
class TokenIn(BaseModel):
    label: str = Field(default="My AI assistant", max_length=80)


def _db():
    s = session_factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def app_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter(prefix="/api/mcp/santosh", tags=["mcp-santosh"],
                  dependencies=[Depends(require_key)])

    @r.post("/tokens")
    def create_token(body: TokenIn, tenant: str = Depends(current_tenant), s=Depends(_db)):
        """Issue a bearer token for /santosh/mcp. Shown only once; stored as SHA-256."""
        ensure_user(s, tenant)
        s.flush()
        tok = issue_token(s, tenant, body.label)
        return {
            "token": tok,
            "mcp_url": resource_url(),
            "label": body.label,
            "header": "Authorization: Bearer <token>",
            "note": ("Shown only once. Read-only access to your notebooks and Google Drive. "
                     "Revoke any time from the Santosh app."),
        }

    @r.get("/tokens")
    def list_tokens(tenant: str = Depends(current_tenant), s=Depends(_db)):
        rows = s.scalars(select(McpSantoshToken).where(
            McpSantoshToken.user_id == tenant
        ).order_by(McpSantoshToken.created_at.desc())).all()
        return {
            "tokens": [{"id": t.id, "label": t.label,
                        "created_at": t.created_at.isoformat(timespec="minutes"),
                        "revoked": t.revoked} for t in rows],
            "mcp_url": resource_url(),
        }

    @r.delete("/tokens/{tid}")
    def revoke_token(tid: str, tenant: str = Depends(current_tenant), s=Depends(_db)):
        t = s.get(McpSantoshToken, tid)
        if not t or t.user_id != tenant:
            raise HTTPException(404, "Token not found")
        t.revoked = True
        return {"revoked": tid}

    return r


# ----------------------------------------------------------------------------- FastAPI mount
class _Mount:
    """The per-token rate limit, then the MCP app built at startup (SDK's session manager runs once)."""

    def __init__(self, per_minute: int):
        from .bazar.commerce.mcp_server import RateLimit
        self.inner = None
        self.limited = RateLimit(self._call, per_minute)

    async def _call(self, scope, receive, send):
        if self.inner is None:
            await send({"type": "http.response.start", "status": 503,
                        "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"Santosh MCP is starting"})
            return
        await self.inner(scope, receive, send)

    async def __call__(self, scope, receive, send):
        await self.limited(scope, receive, send)

    @asynccontextmanager
    async def running(self):
        inner = build_server().streamable_http_app(
            streamable_http_path=INNER_PATH, host="0.0.0.0")
        async with inner.router.lifespan_context(inner):
            self.inner = inner
            try:
                yield
            finally:
                self.inner = None


def mount(app, require_key, current_tenant):
    """Mount /santosh/mcp + /api/mcp/santosh/* on the given FastAPI app.
    Called from main.py right after bazar_commerce.mount(...). Chains the lifespan."""
    app.include_router(app_router(require_key, current_tenant))
    try:
        import mcp.server.mcpserver  # noqa: F401
    except ImportError:
        import logging
        logging.getLogger("santosh.mcp_santosh").warning(
            "Santosh MCP not mounted: needs mcp>=2")
        return None
    m = _Mount(60)
    app.mount(MOUNT_PREFIX, m)
    outer = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(a):
        async with m.running():
            async with outer(a) as state:
                yield state

    app.router.lifespan_context = lifespan
    app.state.mcp_santosh = m
    return m
