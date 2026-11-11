"""v0.785 HOOLA AI APPS - D0: the app object, its draft and its versions.

Laws (each one has a test):
  - Going live is HER tap, bound to the hash of the draft she saw (a draft changed underneath her is refused, 409).
  - A published version is never edited. Restore = the old soul published again as the NEWEST version.
  - A draft that fails the soul checker cannot be published.
  - Public addresses are random codes, never the app id; every read and write is fenced to the tenant.
"""
from __future__ import annotations

import json
import logging
import secrets
from typing import Any

from ..db import now, session
from . import soul as SO
from .models import AiApp, AiAppVersion, ensure_tables

log = logging.getLogger("santosh.aiapps")
MAX_APPS = 25


class AppError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


def _j(s: str | None, d: Any) -> Any:
    try:
        v = json.loads(s or "")
        return v if v is not None else d
    except (TypeError, ValueError):
        return d


def view(a: AiApp, full: bool = False) -> dict[str, Any]:
    out = {"id": a.id, "name": a.name, "kind": a.kind, "status": a.status, "code": a.code,
           "live_version": a.live_version, "draft_hash": a.draft_hash, "template": a.template, "origin": a.origin,
           "channels": _j(a.channels, {}), "created": a.created_at.isoformat() if a.created_at else "",
           "updated": a.updated_at.isoformat() if a.updated_at else "",
           "changed_since_live": bool(a.live_version) and a.draft_hash != _live_hash(a)}
    if full:
        out["draft"] = _j(a.draft, {})
    return out


def _live_hash(a: AiApp) -> str:
    if not a.live_version:
        return ""
    with session() as s:
        v = s.query(AiAppVersion).filter(AiAppVersion.app_id == a.id, AiAppVersion.version == a.live_version).first()
        return v.hash if v is not None else ""


def _row(s, tenant: str, ref: str) -> AiApp:
    a = s.get(AiApp, ref)
    if a is None:
        a = s.query(AiApp).filter(AiApp.tenant_id == tenant, AiApp.code == ref).first()
    if a is None or a.tenant_id != tenant:
        raise AppError("This AI app was not found.", 404)
    return a


def _code() -> str:
    return secrets.token_urlsafe(9).replace("-", "x").replace("_", "y")[:12]


def create(tenant: str, name: str = "", kind: str = "chat", soul: dict[str, Any] | None = None,
           origin: str = "blank", template: str = "") -> dict[str, Any]:
    ensure_tables()
    got = SO.check(soul if soul is not None else SO.blank(name, kind))
    sl = got["soul"]
    if name:
        sl["name"] = name[:SO.CAPS["name"]]
    with session() as s:
        n = s.query(AiApp).filter(AiApp.tenant_id == tenant).count()
        if n >= MAX_APPS:
            raise AppError(f"You already have {MAX_APPS} AI apps; delete one first.", 409)
        a = AiApp(tenant_id=tenant, name=sl["name"], kind=sl["kind"], code=_code(), draft=json.dumps(sl, ensure_ascii=False),
                  draft_hash=SO.hash_of(sl), origin=origin[:12], template=template[:40],
                  channels=json.dumps({"page": True, "embed": True, "api": False, "mcp": False, "whatsapp": ""}))
        s.add(a)
        s.flush()
        s.expunge(a)
    return {**view(a, full=True), "errors": got["errors"], "warnings": got["warnings"]}


def get(tenant: str, ref: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        a = _row(s, tenant, ref)
        s.expunge(a)
    out = view(a, full=True)
    out["check"] = {k: v for k, v in SO.check(out["draft"]).items() if k != "soul"}
    bl = SO.blanks(out["draft"])
    if bl:      # shown with the checker's errors, so the console's 'Must be fixed before publishing' lists them
        out["check"]["errors"] = list(out["check"].get("errors") or []) + [
            "Fill in before publishing (customers would see these): " + ", ".join(bl[:6])]
    return out


def row(tenant: str, ref: str) -> AiApp:
    ensure_tables()
    with session() as s:
        a = _row(s, tenant, ref)
        s.expunge(a)
    return a


def by_code(code: str) -> AiApp | None:
    """The PUBLIC lookup (chat page, embed, MCP). Only a live app answers the public."""
    ensure_tables()
    if not code or len(code) > 24:
        return None
    with session() as s:
        a = s.query(AiApp).filter(AiApp.code == code).first()
        if a is None:
            return None
        s.expunge(a)
    return a


def apps(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        rows = s.query(AiApp).filter(AiApp.tenant_id == tenant).order_by(AiApp.updated_at.desc()).all()
        for r in rows:
            s.expunge(r)
    return [view(r) for r in rows]


def save_draft(tenant: str, ref: str, soul: dict[str, Any]) -> dict[str, Any]:
    """Her edits. The draft is checked and kept even with errors (she fixes them); only publish needs it clean."""
    ensure_tables()
    got = SO.check(soul)
    sl = got["soul"]
    with session() as s:
        a = _row(s, tenant, ref)
        a.draft = json.dumps(sl, ensure_ascii=False)
        a.draft_hash = SO.hash_of(sl)
        a.name, a.kind, a.updated_at = sl["name"], sl["kind"], now()
        s.flush()
        s.expunge(a)
    return {**view(a, full=True), "errors": got["errors"], "warnings": got["warnings"]}


def publish(tenant: str, ref: str, h: str, note: str = "", by: str = "owner") -> dict[str, Any]:
    """HER TAP. `h` is the draft hash she was looking at."""
    ensure_tables()
    with session() as s:
        a = _row(s, tenant, ref)
        if not h or h != a.draft_hash:
            raise AppError("The draft changed since you looked at it; check it again, then publish.", 409)
        got = SO.check(_j(a.draft, {}))
        if got["errors"]:
            raise AppError("Fix this first: " + got["errors"][0], 422)
        bl = SO.blanks(got["soul"])
        if bl:
            raise AppError("Fill in these blanks first - customers would see them: " + ", ".join(bl[:5]), 422)
        nxt = (s.query(AiAppVersion).filter(AiAppVersion.app_id == a.id).count()) + 1
        v = AiAppVersion(app_id=a.id, tenant_id=tenant, version=nxt, soul=json.dumps(got["soul"], ensure_ascii=False),
                         hash=SO.hash_of(got["soul"]), note=str(note or "")[:500], op="publish", by=by[:40])
        s.add(v)
        a.live_version, a.status, a.updated_at = nxt, "live", now()
        s.flush()
        s.expunge(a)
    return {**view(a), "version": nxt, "says": f"'{a.name}' is live (version {nxt})."}


def versions(tenant: str, ref: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        a = _row(s, tenant, ref)
        rows = (s.query(AiAppVersion).filter(AiAppVersion.app_id == a.id).order_by(AiAppVersion.version.desc()).all())
        live = a.live_version
        out = [{"version": v.version, "hash": v.hash, "note": v.note, "op": v.op, "by": v.by, "live": v.version == live,
                "at": v.created_at.isoformat() if v.created_at else ""} for v in rows]
    return out


def restore(tenant: str, ref: str, version: int, by: str = "owner") -> dict[str, Any]:
    """HER TAP: an old version becomes the newest one (and the draft), history untouched."""
    ensure_tables()
    with session() as s:
        a = _row(s, tenant, ref)
        old = s.query(AiAppVersion).filter(AiAppVersion.app_id == a.id, AiAppVersion.version == int(version)).first()
        if old is None:
            raise AppError(f"Version {version} does not exist.", 404)
        nxt = s.query(AiAppVersion).filter(AiAppVersion.app_id == a.id).count() + 1
        s.add(AiAppVersion(app_id=a.id, tenant_id=tenant, version=nxt, soul=old.soul, hash=old.hash,
                           note=f"restored from version {old.version}", op="restore", by=by[:40]))
        a.draft, a.draft_hash = old.soul, old.hash
        a.live_version, a.status, a.updated_at = nxt, "live", now()
        s.flush()
        s.expunge(a)
    return {**view(a), "version": nxt, "says": f"Version {version} is live again, as version {nxt}."}


def set_status(tenant: str, ref: str, status: str) -> dict[str, Any]:
    """Pause stops every channel at once; resume needs a published version."""
    if status not in ("live", "paused"):
        raise AppError("status: live | paused")
    with session() as s:
        a = _row(s, tenant, ref)
        if status == "live" and not a.live_version:
            raise AppError("Publish it first.", 409)
        a.status, a.updated_at = status, now()
        s.flush()
        s.expunge(a)
    return view(a)


def set_channels(tenant: str, ref: str, **kw: Any) -> dict[str, Any]:
    allowed = {"page", "embed", "api", "mcp", "whatsapp"}
    with session() as s:
        a = _row(s, tenant, ref)
        ch = _j(a.channels, {})
        for k, v in kw.items():
            if k in allowed:
                ch[k] = (str(v or "")[:40] if k == "whatsapp" else bool(v))
        a.channels, a.updated_at = json.dumps(ch), now()
        s.flush()
        s.expunge(a)
    return view(a)


def delete(tenant: str, ref: str) -> dict[str, Any]:
    from .models import AiAppKey, AiAppMessage, AiAppSession
    with session() as s:
        a = _row(s, tenant, ref)
        for t in (AiAppVersion, AiAppKey, AiAppSession, AiAppMessage):
            s.query(t).filter(t.app_id == a.id).delete(synchronize_session=False)
        name = a.name
        s.delete(a)
    return {"ok": True, "says": f"'{name}' and its logs are deleted."}


def live_soul(a: AiApp) -> tuple[dict[str, Any], int]:
    """The soul that answers the PUBLIC: the live version, never the draft."""
    if not a.live_version:
        return {}, 0
    with session() as s:
        v = s.query(AiAppVersion).filter(AiAppVersion.app_id == a.id, AiAppVersion.version == a.live_version).first()
        return (_j(v.soul, {}), a.live_version) if v is not None else ({}, 0)


def draft_soul(a: AiApp) -> dict[str, Any]:
    return SO.check(_j(a.draft, {}))["soul"]
