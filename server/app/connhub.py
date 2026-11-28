"""v0.999.183 CONNECTORS PAGE: what Hoola did inside her apps, and her Pause switch.

The Connectors section is its own page now (/console/connectors). Two things it needs that did not exist:

- ACTIVITY: one row each time Hoola used one of her connected apps (Email, Calendar, Drive, Sheets, Docs, Forms,
  Slides, Photos, her YouTube channel, Business Profile, IndiaMART, any Composio app). Written by the tool funnel
  (`santosh._run_tool` -> `record`), best-effort, never able to break a call. A row keeps the app, the step's plain
  label, where it was asked from (chat / call / routine / an AI employee) and how it ended (done / asked you /
  failed / paused). It keeps NO content: no mail text, no file names, no arguments.
- PAUSE: her one switch that stops Hoola from using every connected app (`paused`); `gate` is checked in the same
  funnel before the tool runs, and a refused call is logged as 'paused'.

Tables self-heal (registered in db.init_db as well), the per-tenant log is capped and swept after 120 days.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, now, session

log = logging.getLogger("santosh.connhub")

KEEP_DAYS = 120
MAX_PER_TENANT = 5000
PAUSED_LINE = ("Every app is paused in Connectors, so Hoola is not using her apps right now. Tell her she can turn "
               "this off in Connectors > Limits & safety.")


class ConnActivity(Base):
    __tablename__ = "conn_activity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    app: Mapped[str] = mapped_column(String(64), index=True)       # gmail-style key or a Composio toolkit slug
    tool: Mapped[str] = mapped_column(String(80), default="")
    what: Mapped[str] = mapped_column(String(160), default="")
    source: Mapped[str] = mapped_column(String(16), default="chat")   # chat | call | routine | employee
    outcome: Mapped[str] = mapped_column(String(12), default="done")  # done | asked | failed | paused
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class ConnPrefs(Base):
    __tablename__ = "conn_prefs"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_ready = False


def ensure_table() -> None:
    global _ready
    if _ready:
        return
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        ConnActivity.__table__.create(eng, checkfirst=True)
        ConnPrefs.__table__.create(eng, checkfirst=True)
    _ready = True


# ------------------------------------------------------------------ which app a tool works in
APP_NAMES = {"mail": "Email", "calendar": "Calendar", "drive": "Drive", "docs": "Docs", "sheets": "Sheets",
             "forms": "Forms", "slides": "Slides", "photos": "Photos", "youtube": "YouTube",
             "business": "Business Profile", "indiamart": "IndiaMART"}
_PREFIX = (("email_", "mail"), ("calendar_", "calendar"), ("sheet_", "sheets"), ("sheets_", "sheets"),
           ("form_", "forms"), ("slides_", "slides"), ("photos_", "photos"), ("gbp_", "business"),
           ("indiamart_", "indiamart"))
# YouTube tools that work in HER channel (search / watch / play read the public site, not her account)
_YT_OWN = {"youtube_my_channel", "youtube_my_videos", "youtube_upload", "youtube_update_video", "youtube_reply",
           "youtube_comments", "youtube_playlist", "youtube_analytics"}
_READS = re.compile(r"(_read|_find|_list|_info|_details|_agenda|_check|_thread|_threads|_drafts|_accounts|_contacts|"
                    r"_responses|_summary|_free_slots|_storage|_biggest|_changes|_revisions|_shared_drives|_albums|"
                    r"_picked|_numbers|_locations|_analytics|_my_channel|_my_videos|_comments|_khoj|_detail|_query|"
                    r"_trash_list|_bulk_status|_settings)$")


def classify(name: str, args: dict | None = None) -> str:
    """The app a tool call works in ('' = not one of her connected apps)."""
    n = (name or "").strip()
    a = args or {}
    if n == "drive_create_doc":
        return "docs"
    if n.startswith("drive_") and n not in ("drivers", "drivers_dekho"):
        return "drive"
    if n in _YT_OWN:
        return "youtube"
    for p, k in _PREFIX:
        if n.startswith(p):
            return k
    if n == "bazar_run":
        pid = str(a.get("pack_id") or "")
        if pid.startswith("cmp-"):
            return re.sub(r"[^a-z0-9_]", "", pid[4:].lower())[:60]
    return ""


def _what(name: str, args: dict | None) -> str:
    if name == "bazar_run":
        slug = str((args or {}).get("tool") or "")
        tk = str((args or {}).get("pack_id") or "")[4:].upper()
        if tk and slug.upper().startswith(tk + "_"):
            slug = slug[len(tk) + 1:]
        words = slug.replace("_", " ").strip().lower()
        return (words[:1].upper() + words[1:])[:150] if words else "Used the app"
    try:
        from . import lang
        lab = lang.label(name)
    except Exception:   # noqa: BLE001
        lab = name.replace("_", " ").capitalize()
    return str(lab or name)[:150]


def _asked(out: Any) -> bool:
    """A result that waits for her tap (an approval / send / delete card)."""
    if not isinstance(out, dict):
        return False
    if any(k in out for k in ("card", "approval", "approval_id", "needs_tap", "card_id")):
        return True
    st = str(out.get("status") or "").lower()
    return st in ("pending", "needs_approval", "awaiting_approval", "card", "waiting")


def _source(actor: str, conversation_id: str) -> str:
    a = (actor or "").lower()
    if a.startswith("routine") or a == "wake":
        return "routine"
    if a.startswith("team:") or a.startswith("agent") or a.startswith("employee"):
        return "employee"
    try:
        from .db import Conversation
        with session() as s:
            c = s.get(Conversation, conversation_id) if conversation_id else None
            if c is not None and (c.kind or "") == "call":
                return "call"
    except Exception:   # noqa: BLE001
        pass
    return "chat"


def record(tenant: str, conversation_id: str, name: str, args: dict | None, out: Any, ok: bool,
           actor: str = "", outcome: str = "") -> None:
    """One activity row. Best-effort: never raises."""
    try:
        app = classify(name, args)
        if not app or not tenant:
            return
        if not outcome:
            outcome = "failed" if not ok else ("asked" if _asked(out) else "done")
        ensure_table()
        with session() as s:
            s.add(ConnActivity(tenant_id=tenant[:64], app=app, tool=name[:80], what=_what(name, args),
                               source=_source(actor, conversation_id), outcome=outcome,
                               conversation_id=(conversation_id or "")[:64]))
            n = s.scalar(select(func.count()).select_from(ConnActivity).where(ConnActivity.tenant_id == tenant)) or 0
            if n > MAX_PER_TENANT:
                old = s.scalars(select(ConnActivity.id).where(ConnActivity.tenant_id == tenant)
                                .order_by(ConnActivity.id).limit(n - MAX_PER_TENANT)).all()
                if old:
                    s.execute(delete(ConnActivity).where(ConnActivity.id.in_(old)))
    except Exception:   # noqa: BLE001
        log.debug("connector activity not written", exc_info=True)


def forget_old(days: int = KEEP_DAYS) -> int:
    try:
        ensure_table()
        cut = now() - timedelta(days=days)
        with session() as s:
            r = s.execute(delete(ConnActivity).where(ConnActivity.created_at < cut))
            return int(r.rowcount or 0)
    except Exception:   # noqa: BLE001
        return 0


# ------------------------------------------------------------------ her Pause switch
def paused(tenant: str) -> bool:
    if not tenant:
        return False
    try:
        ensure_table()
        with session() as s:
            p = s.get(ConnPrefs, tenant[:64])
            return bool(p and p.paused)
    except Exception:   # noqa: BLE001
        return False


def set_paused(tenant: str, on: bool) -> dict:
    ensure_table()
    with session() as s:
        p = s.get(ConnPrefs, tenant[:64])
        if p is None:
            p = ConnPrefs(tenant_id=tenant[:64])
            s.add(p)
        p.paused = bool(on)
        p.updated_at = now()
    return safety(tenant)


def gate(tenant: str, name: str, args: dict | None) -> str:
    """'' = go ahead; else the line the model gets because she paused every app."""
    if classify(name, args) and paused(tenant):
        return PAUSED_LINE
    return ""


# ------------------------------------------------------------------ what the page reads
def _aware(d: datetime | None) -> datetime:
    if d is None:
        return now()
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _month_start() -> datetime:
    t = now()
    return datetime(t.year, t.month, 1, tzinfo=timezone.utc)


def activity(tenant: str, app: str = "", days: int = 30, limit: int = 60, before: int = 0,
             outcome: str = "") -> dict:
    ensure_table()
    days = max(1, min(int(days or 30), KEEP_DAYS))
    limit = max(1, min(int(limit or 60), 200))
    since = now() - timedelta(days=days)
    with session() as s:
        q = select(ConnActivity).where(ConnActivity.tenant_id == tenant, ConnActivity.created_at >= since)
        if app:
            q = q.where(ConnActivity.app == app[:64])
        if outcome in ("done", "asked", "failed", "paused"):
            q = q.where(ConnActivity.outcome == outcome)
        if before:
            q = q.where(ConnActivity.id < int(before))
        rows = s.scalars(q.order_by(ConnActivity.id.desc()).limit(limit + 1)).all()
    more = len(rows) > limit
    rows = rows[:limit]
    return {"rows": [{"id": r.id, "app": r.app, "app_name": APP_NAMES.get(r.app, ""), "what": r.what,
                      "source": r.source, "outcome": r.outcome, "conversation_id": r.conversation_id,
                      "at": _aware(r.created_at).isoformat()} for r in rows],
            "more": more, "days": days}


def summary(tenant: str) -> dict:
    """The numbers on the page: this month's actions, the week by app, her Pause switch."""
    ensure_table()
    month, week = _month_start(), now() - timedelta(days=7)
    with session() as s:
        m = s.execute(select(ConnActivity.outcome, func.count()).where(
            ConnActivity.tenant_id == tenant, ConnActivity.created_at >= month).group_by(ConnActivity.outcome)).all()
        w = s.execute(select(ConnActivity.app, ConnActivity.outcome, func.count()).where(
            ConnActivity.tenant_id == tenant, ConnActivity.created_at >= week)
            .group_by(ConnActivity.app, ConnActivity.outcome)).all()
        last = s.execute(select(ConnActivity.app, func.max(ConnActivity.created_at)).where(
            ConnActivity.tenant_id == tenant).group_by(ConnActivity.app)).all()
    by_out = {k: int(v) for k, v in m}
    apps: dict[str, dict] = {}
    for a, o, c in w:
        d = apps.setdefault(a, {"done": 0, "asked": 0, "failed": 0, "paused": 0})
        d[o] = d.get(o, 0) + int(c)
    return {"month": {"total": sum(by_out.values()), **{k: by_out.get(k, 0) for k in ("done", "asked", "failed", "paused")}},
            "week": apps,
            "last": {a: _aware(t).isoformat() for a, t in last if t},
            "paused": paused(tenant)}


def safety(tenant: str) -> dict:
    return {"paused": paused(tenant),
            "always": [
                {"name": "Ask before every send", "note": "Mail, messages and posts wait for your yes."},
                {"name": "Ask before every share, delete or payment", "note": "Files, rows, mail and money."},
                {"name": "Text inside your apps is only data", "note": "Hoola never follows instructions written inside an email, file or web page."},
            ]}


from pydantic import BaseModel  # noqa: E402


class PauseIn(BaseModel):
    paused: bool


def mount(app, current_tenant, require_key) -> None:
    from fastapi import Depends

    @app.get("/api/connectors/activity", dependencies=[Depends(require_key)])
    def conn_activity(app_key: str = "", days: int = 30, limit: int = 60, before: int = 0, outcome: str = "",
                      tenant: str = Depends(current_tenant)):
        return activity(tenant, app_key, days, limit, before, outcome)

    @app.get("/api/connectors/summary", dependencies=[Depends(require_key)])
    def conn_summary(tenant: str = Depends(current_tenant)):
        return summary(tenant)

    @app.get("/api/connectors/safety", dependencies=[Depends(require_key)])
    def conn_safety(tenant: str = Depends(current_tenant)):
        return safety(tenant)

    @app.put("/api/connectors/safety", dependencies=[Depends(require_key)])
    def conn_safety_put(body: PauseIn, tenant: str = Depends(current_tenant)):
        return set_paused(tenant, body.paused)
