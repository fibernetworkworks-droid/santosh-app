"""v0.785 HOOLA AI APPS - D2: API keys for one app + the service API.

Laws (each one has a test):
  - A key is shown ONCE, at creation. Only its sha256 is kept; a list never carries it (the last 4 characters only).
  - A key opens only ITS app, only while that app is live and its `api` (or `mcp`) channel is on; a revoked key is dead.
  - Every key has limits she set: calls a minute, calls an hour, calls running at once. Over a limit = 429 with
    Retry-After, before the model is called.
  - The service API is a visitor channel like the page: the same runtime, the same traps, the same cost cap.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Any, Iterator

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ..db import now, session
from . import runtime as RT
from . import store as ST
from .models import AiApp, AiAppKey, ensure_tables

PREFIX = "aik_"
MAX_KEYS = 10
BOUNDS = {"rpm": (1, 120), "rph": (1, 5000), "concurrent": (1, 10)}
DEFAULTS = {"rpm": 20, "rph": 300, "concurrent": 3}


class LimitError(Exception):
    """Over a key's limit. `retry_after` = whole seconds until the next call can go."""

    def __init__(self, msg: str, retry_after: int):
        super().__init__(msg)
        self.retry_after = max(1, int(retry_after))


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _bound(name: str, v: Any) -> int:
    lo, hi = BOUNDS[name]
    try:
        n = int(v if v is not None else DEFAULTS[name])
    except (TypeError, ValueError):
        raise ST.AppError(f"{name} must be a whole number ({lo}-{hi}).")
    if n < lo or n > hi:
        raise ST.AppError(f"{name} must be between {lo} and {hi}.")
    return n


def _view(k: AiAppKey) -> dict[str, Any]:
    return {"id": k.id, "name": k.name, "tail": k.tail, "revoked": bool(k.revoked),
            "limits": {"rpm": k.rpm, "rph": k.rph, "concurrent": k.concurrent},
            "last_used": k.last_used_at.isoformat() if k.last_used_at else "",
            "created": k.created_at.isoformat() if k.created_at else ""}


# ---------------------------------------------------------------- keys (owner)
def create(tenant: str, ref: str, name: str = "", rpm: Any = None, rph: Any = None, concurrent: Any = None) -> dict[str, Any]:
    ensure_tables()
    a = ST.row(tenant, ref)
    lim = {"rpm": _bound("rpm", rpm), "rph": _bound("rph", rph), "concurrent": _bound("concurrent", concurrent)}
    key = PREFIX + secrets.token_urlsafe(32)
    with session() as s:
        n = s.query(AiAppKey).filter(AiAppKey.app_id == a.id, AiAppKey.revoked.is_(False)).count()
        if n >= MAX_KEYS:
            raise ST.AppError(f"This app already has {MAX_KEYS} keys; revoke one first.", 409)
        k = AiAppKey(app_id=a.id, tenant_id=tenant, name=str(name or "API key").strip()[:80] or "API key",
                     key_hash=_hash(key), tail=key[-4:], **lim)
        s.add(k)
        s.flush()
        s.expunge(k)
    return {**_view(k), "key": key,
            "says": "Copy this key now - it is shown only once. Hoola keeps only a fingerprint of it."}


def list_keys(tenant: str, ref: str) -> list[dict[str, Any]]:
    ensure_tables()
    a = ST.row(tenant, ref)
    with session() as s:
        rows = s.query(AiAppKey).filter(AiAppKey.app_id == a.id).order_by(AiAppKey.created_at.desc()).all()
        return [_view(k) for k in rows]


def revoke(tenant: str, ref: str, kid: str) -> dict[str, Any]:
    ensure_tables()
    a = ST.row(tenant, ref)
    with session() as s:
        k = s.get(AiAppKey, kid)
        if k is None or k.app_id != a.id or k.tenant_id != tenant:
            raise ST.AppError("That key was not found.", 404)
        k.revoked = True
        out = _view(k)
    LIMITER.forget(kid)
    return {**out, "says": f"Key ...{out['tail']} is revoked; calls with it now fail."}


def resolve(key: str, channel: str = "api") -> tuple[AiApp, AiAppKey] | None:
    """A presented key -> (its app, the key row), or None: unknown, revoked, app not live, or the channel is off."""
    ensure_tables()
    key = str(key or "").strip()
    if not key.startswith(PREFIX) or len(key) > 120:
        return None
    with session() as s:
        k = s.query(AiAppKey).filter(AiAppKey.key_hash == _hash(key)).first()
        if k is None or k.revoked:
            return None
        a = s.get(AiApp, k.app_id)
        if a is None or a.tenant_id != k.tenant_id or a.status != "live" or not a.live_version:
            return None
        if not ST._j(a.channels, {}).get(channel):
            return None
        k.last_used_at = now()
        s.flush()
        s.expunge(k)
        s.expunge(a)
    return a, k


# ---------------------------------------------------------------- limits (in memory, per key)
class Limiter:
    """Sliding-window calls a minute / an hour + a running-at-once counter, per key id. One process; a restart forgets."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}
        self._running: dict[str, int] = {}

    def forget(self, kid: str) -> None:
        with self._lock:
            self._hits.pop(kid, None)
            self._running.pop(kid, None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
            self._running.clear()

    def check(self, kid: str, rpm: int, rph: int, concurrent: int, clock: float | None = None) -> None:
        t = time.monotonic() if clock is None else clock
        with self._lock:
            q = self._hits.setdefault(kid, deque())
            while q and t - q[0] >= 3600:
                q.popleft()
            last_min = [x for x in q if t - x < 60]
            if len(last_min) >= rpm:
                raise LimitError(f"Limit reached: {rpm} calls a minute.", 60 - (t - last_min[0]) + 1)
            if len(q) >= rph:
                raise LimitError(f"Limit reached: {rph} calls an hour.", 3600 - (t - q[0]) + 1)
            if self._running.get(kid, 0) >= concurrent:
                raise LimitError(f"Limit reached: {concurrent} calls at once.", 2)
            q.append(t)

    @contextmanager
    def running(self, kid: str, concurrent: int) -> Iterator[None]:
        with self._lock:
            if self._running.get(kid, 0) >= concurrent:
                raise LimitError(f"Limit reached: {concurrent} calls at once.", 2)
            self._running[kid] = self._running.get(kid, 0) + 1
        try:
            yield
        finally:
            with self._lock:
                self._running[kid] = max(0, self._running.get(kid, 1) - 1)

    @contextmanager
    def call(self, k: AiAppKey) -> Iterator[None]:
        """Count one call against the key, then hold a running slot for as long as it runs."""
        self.check(k.id, k.rpm, k.rph, k.concurrent)
        with self.running(k.id, k.concurrent):
            yield


LIMITER = Limiter()


def service_answer(a: AiApp, text: str, user: str = "", inputs: dict[str, Any] | None = None,
                   channel: str = "api") -> dict[str, Any]:
    """One answer for an API / MCP caller: the session is the caller's user id (one conversation per user)."""
    user = str(user or "").strip()[:120]
    sid = RT.session_for(a, visitor=user, channel=channel) if user else ""
    if not sid:
        sid, _tok = RT.open_session(a, channel, visitor=user, consent=True)
    out = RT.answer(a, text=text, channel=channel, session_id=sid, inputs=inputs)
    return {"reply": out.get("reply", ""), "outcome": out.get("outcome", ""), "sources": out.get("sources") or [],
            "message_id": out.get("message_id", ""), "session_id": sid}


def bearer(request) -> str:
    return request.headers.get("authorization", "").removeprefix("Bearer ").strip()


# ---------------------------------------------------------------- routes
def make_router(require_key, current_tenant):
    """Owner key routes (/api/aiapps/{id}/keys) + the PUBLIC service API (/api/aiapp-api/v1/chat, app key only)."""
    r = APIRouter()

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except ST.AppError as e:
            raise HTTPException(e.code, str(e))

    @r.get("/api/aiapps/{ref}/keys", dependencies=[Depends(require_key)])
    async def keys_list(ref: str, tenant: str = Depends(current_tenant)):
        return {"keys": await run(list_keys, tenant, ref)}

    @r.post("/api/aiapps/{ref}/keys", dependencies=[Depends(require_key)])
    async def keys_create(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = dict(body or {})
        return await run(create, tenant, ref, str(b.get("name") or ""), b.get("rpm"), b.get("rph"), b.get("concurrent"))

    @r.delete("/api/aiapps/{ref}/keys/{kid}", dependencies=[Depends(require_key)])
    async def keys_revoke(ref: str, kid: str, tenant: str = Depends(current_tenant)):
        return await run(revoke, tenant, ref, kid)

    @r.post("/api/aiapp-api/v1/chat")
    async def service_chat(request: Request, body: dict = Body(default={})):
        got = await asyncio.to_thread(resolve, bearer(request), "api")
        if got is None:
            return JSONResponse({"error": "Missing, wrong or revoked AI app key (or the app is not live / API is off)."},
                                status_code=401)
        a, k = got
        b = dict(body or {})
        text = str(b.get("text") or "")
        if len(text) > RT.MAX_Q:
            raise HTTPException(413, f"text is longer than {RT.MAX_Q} characters.")
        inputs = b.get("inputs") if isinstance(b.get("inputs"), dict) else None
        try:
            with LIMITER.call(k):
                return await asyncio.to_thread(service_answer, a, text, str(b.get("user") or ""), inputs, "api")
        except LimitError as e:
            return JSONResponse({"error": str(e)}, status_code=429, headers={"Retry-After": str(e.retry_after)})
        except ST.AppError as e:
            raise HTTPException(e.code, str(e))

    return r
