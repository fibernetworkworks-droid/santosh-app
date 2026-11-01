"""v0.383 PAKKI NEEV: indexed links between an app's rows (an order's items, a class's students) - no full-list scans.

Every row id is `row_<12 hex>`. The same before_flush moment the journal uses sees every write, and every top-level
value of a row that IS a row id becomes one line here {site, coll, row, field, value} - no schema lookup inside the
flush, nothing a write path can skip. `children(site, coll, field, parent)` is then one indexed query instead of a JSON
text scan of the whole list. Rows written before v0.383 are indexed once per app on first use (`ensure_indexed`)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy import Index, Integer, String, delete, event, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..db import Base, session
from ..site import webapp as W

log = logging.getLogger(__name__)
ROW_ID = re.compile(r"^row_[0-9a-f]{12}$")
STATS = {"indexed": 0, "lookups": 0, "backfilled": 0}
_DONE: set[str] = set()


class AppRef(Base):
    __tablename__ = "app_refs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(String(40))
    coll: Mapped[str] = mapped_column(String(40))
    row_id: Mapped[str] = mapped_column(String(40), index=True)
    field: Mapped[str] = mapped_column(String(40))
    value: Mapped[str] = mapped_column(String(40))
    __table_args__ = (Index("ix_app_refs_lookup", "site_id", "value", "coll", "field"),)


_OK = False


def ensure_table() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        AppRef.__table__.create(_db._engine, checkfirst=True)
        _OK = True


def _links(data: str | None) -> list[tuple[str, str]]:
    try:
        d = json.loads(data or "{}")
    except ValueError:
        return []
    return [(k, v) for k, v in d.items() if isinstance(v, str) and not k.startswith("_") and ROW_ID.match(v)][:40]


@event.listens_for(Session, "before_flush")
def _index(sess: Session, _ctx, _instances) -> None:
    try:
        touched = []
        for obj in list(sess.new) + [o for o in sess.dirty if sess.is_modified(o)]:
            if isinstance(obj, W.SiteAppRow) and str(obj.site_id or "").startswith("app:") and not obj.coll.startswith("_"):
                touched.append((obj, False))
        for obj in list(sess.deleted):
            if isinstance(obj, W.SiteAppRow) and str(obj.site_id or "").startswith("app:"):
                touched.append((obj, True))
        if not touched:
            return
        ensure_table()
        for obj, gone in touched:
            if not obj.id:
                from ..db import new_id
                obj.id = new_id("row")
            sess.execute(delete(AppRef).where(AppRef.row_id == obj.id))
            if gone:
                continue
            for k, v in _links(obj.data):
                sess.add(AppRef(site_id=obj.site_id, coll=obj.coll, row_id=obj.id, field=k, value=v))
                STATS["indexed"] += 1
    except Exception:                                # noqa: BLE001 - the index never blocks her app's write
        log.exception("app refs index failed")


def ensure_indexed(site: str) -> None:
    """Rows from before v0.383 get their links indexed once (per process, per app; cheap when already done)."""
    if site in _DONE:
        return
    ensure_table()
    with session() as s:
        have = s.scalar(select(AppRef.id).where(AppRef.site_id == site).limit(1))
        marker = s.scalar(select(W.SiteAppRow.id).where(W.SiteAppRow.site_id == site, W.SiteAppRow.coll == "_refs_v1").limit(1))
        if marker is None:
            rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site)).all()
            if have:
                s.execute(delete(AppRef).where(AppRef.site_id == site))
            for x in rows:
                if x.coll.startswith("_"):
                    continue
                for k, v in _links(x.data):
                    s.add(AppRef(site_id=site, coll=x.coll, row_id=x.id, field=k, value=v))
                    STATS["backfilled"] += 1
            s.add(W.SiteAppRow(site_id=site, coll="_refs_v1", owner="", data="{}"))
    _DONE.add(site)


def child_ids(site: str, coll: str, field: str, parent: str, cap: int = 2000) -> list[str]:
    ensure_indexed(site)
    STATS["lookups"] += 1
    with session() as s:
        return list(s.scalars(select(AppRef.row_id).where(AppRef.site_id == site, AppRef.value == parent, AppRef.coll == coll,
                                                         AppRef.field == field).limit(cap)).all())


def child_rows(site: str, coll: str, field: str, parent: str, cap: int = 2000) -> list[W.SiteAppRow]:
    ids = child_ids(site, coll, field, parent, cap)
    if not ids:
        return []
    out: list[Any] = []
    with session() as s:
        for i in range(0, len(ids), 500):
            got = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.id.in_(ids[i:i + 500]))).all()
            for x in got:
                s.expunge(x)
            out += got
    out.sort(key=lambda x: (x.created_at.isoformat() if x.created_at else "", x.id))
    return out
