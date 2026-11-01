"""v0.390 PAKKI NEEV (App Sahayak Pillar B): every app's data can be brought back - to a snapshot or to ANY minute.

  * JOURNAL: one SQLAlchemy hook (before_flush) sees EVERY write to an app's rows - from the app, her Hoola, the logic
    engine, stock / coupons / khata, anything - and writes {row, op, before, after} in the SAME transaction. No write
    path can skip it (the audit list `_audit` is left out: it is itself a log).
  * SNAPSHOTS: the app's whole data (rows + accounts + backend settings) as one gzip JSON file - every day by the worker,
    and before every risky change (logic applied, a data change, a restore). Newest 14 daily + 20 "before" kept.
  * POINT-IN-TIME RESTORE: the newest snapshot before that minute + the journal replayed up to it. Restoring is HER tap:
    it first takes a "before restore" snapshot (so a restore can itself be undone), then replaces the app's rows.
  * EXPORT: her data as a ZIP (a CSV per list + JSON), accounts WITHOUT password hashes.
The journal keeps 35 days; older entries are only removed once a newer snapshot covers them."""
from __future__ import annotations

import csv
import gzip
import io
import json
import logging
import re
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, event, inspect, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..db import Base, now, session
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"journal": 0, "snapshots": 0, "restores": 0, "exports": 0}
KEEP_DAILY, KEEP_BEFORE, JOURNAL_DAYS = 14, 20, 35
SKIP = {"_audit", "_refs_v1"}
NAME = re.compile(r"^(\d{8}-\d{6})-(daily|before|manual)\.json\.gz$")


class AppJournal(Base):
    __tablename__ = "app_journal"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    row_id: Mapped[str] = mapped_column(String(40), index=True)
    coll: Mapped[str] = mapped_column(String(40), default="")
    op: Mapped[str] = mapped_column(String(8))                     # insert | update | delete
    owner: Mapped[str] = mapped_column(String(40), default="")
    before: Mapped[str] = mapped_column(Text, default="")
    after: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[str] = mapped_column(String(40), default="")   # the row's own created_at (kept on a restore)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    pushed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)   # v0.396 already in her own database (write-through)


_OK = False


def ensure_table() -> None:
    """Self-heal for databases born before this table (CLAUDE.md rule)."""
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        AppJournal.__table__.create(_db._engine, checkfirst=True)
        _OK = True


# ---------------------------------------------------------------- the journal hook (every write, every path)
def _is_app(site: str) -> bool:
    return str(site or "").startswith("app:")


@event.listens_for(Session, "before_flush")
def _journal(sess: Session, _ctx, _instances) -> None:
    try:
        rows = []
        for obj in list(sess.new):
            if isinstance(obj, W.SiteAppRow) and _is_app(obj.site_id) and obj.coll not in SKIP:
                rows.append(("insert", obj, "", obj.data or "{}"))
        for obj in list(sess.dirty):
            if isinstance(obj, W.SiteAppRow) and _is_app(obj.site_id) and obj.coll not in SKIP and sess.is_modified(obj):
                h = inspect(obj).attrs.data.history
                old = h.deleted[0] if h.deleted else None
                if old is None or old == obj.data:
                    continue
                rows.append(("update", obj, old, obj.data or "{}"))
        for obj in list(sess.deleted):
            if isinstance(obj, W.SiteAppRow) and _is_app(obj.site_id) and obj.coll not in SKIP:
                h = inspect(obj).attrs.data.history
                old = (h.deleted[0] if h.deleted else None) or obj.data or "{}"
                rows.append(("delete", obj, old, ""))
        if not rows:
            return
        ensure_table()
        for op, obj, before, after in rows:
            if not obj.id:                      # a new row gets its id at flush: give it one now so the journal can name it
                from ..db import new_id
                obj.id = new_id("row")
            created = obj.created_at.isoformat() if obj.created_at else now().isoformat()
            j = AppJournal(site_id=obj.site_id, row_id=obj.id, coll=obj.coll, op=op, owner=obj.owner or "",
                           before=before, after=after, created=created)
            sess.add(j)
            STATS["journal"] += 1
            from . import owndb as OD                   # v0.396 APNA DATABASE: queued for the write-through to her database
            OD.stash(sess, obj.site_id, (op, obj.id, obj.coll, obj.owner or "", before, after, created), j)
    except Exception:                           # noqa: BLE001 - the journal never blocks her app's write
        log.exception("app journal failed")


# ---------------------------------------------------------------- snapshots
def _dir(r: AppProject) -> Path:
    from . import kit as K
    d = K.app_dir(r.tenant_id, r.id) / "backend" / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _site(r: AppProject) -> str:
    return "app:" + r.id


def _dump(r: AppProject) -> dict[str, Any]:
    ensure_table()
    with session() as s:                                # journal position FIRST: a write landing in between is both in the
        jid = s.scalar(select(AppJournal.id).where(AppJournal.site_id == _site(r)).order_by(AppJournal.id.desc()).limit(1)) or 0
        rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r))).all()   # rows and replayed (idempotent)
        mems = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == _site(r))).all()
        app = s.get(AppProject, r.id)
        return {"app": r.id, "number": r.number, "at": now().isoformat(), "journal_id": int(jid), "v": 1,
                "backend": json.loads(app.backend or "{}") if app is not None else {},
                "rows": [{"id": x.id, "coll": x.coll, "owner": x.owner or "", "data": x.data or "{}",
                          "created": x.created_at.isoformat() if x.created_at else "",
                          "updated": x.updated_at.isoformat() if x.updated_at else ""} for x in rows],
                "members": [{"id": m.id, "email": m.email, "name": m.name, "pw": m.pw, "role": m.role, "gen": m.gen or 0,
                             "created": m.created_at.isoformat() if m.created_at else ""} for m in mems]}


def snapshot(r: AppProject, why: str = "", kind: str = "before") -> dict[str, Any]:
    """The whole app's data into one file. kind: daily | before (a risky change) | manual (her button)."""
    kind = kind if kind in ("daily", "before", "manual") else "before"
    d = _dump(r)
    d["why"] = str(why or kind)[:120]
    name = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + f"-{kind}.json.gz"
    p = _dir(r) / name
    n = 0
    while p.exists():                                   # two snapshots in one second
        n += 1
        p = _dir(r) / name.replace(f"-{kind}", f"-{kind}{n}")
    raw = json.dumps(d, ensure_ascii=False).encode()
    tmp = p.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress(raw, 6))
    tmp.replace(p)                                      # never a half-written backup file
    STATS["snapshots"] += 1
    _prune(r)
    return {"name": p.name, "kind": kind, "why": d["why"], "rows": len(d["rows"]), "members": len(d["members"]),
            "bytes": p.stat().st_size, "at": d["at"]}


def _list(r: AppProject) -> list[Path]:
    return sorted((p for p in _dir(r).glob("*.json.gz") if p.is_file()), key=lambda p: p.name)


def _kind(p: Path) -> str:
    m = re.search(r"-(daily|before|manual)\d*\.json\.gz$", p.name)
    return m.group(1) if m else "before"


def _prune(r: AppProject) -> None:
    files = _list(r)
    for kind, keep in (("daily", KEEP_DAILY), ("before", KEEP_BEFORE), ("manual", KEEP_BEFORE)):
        mine = [p for p in files if _kind(p) == kind]
        for p in mine[:-keep] if len(mine) > keep else []:
            p.unlink(missing_ok=True)


def _read(p: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(p.read_bytes()).decode())


def snapshots(r: AppProject) -> list[dict[str, Any]]:
    out = []
    for p in reversed(_list(r)):
        try:
            d = _read(p)
            out.append({"name": p.name, "kind": _kind(p), "at": d.get("at", ""), "why": d.get("why", ""),
                        "rows": len(d.get("rows") or []), "bytes": p.stat().st_size})
        except Exception:                               # noqa: BLE001 - a damaged file is listed as such
            out.append({"name": p.name, "kind": _kind(p), "at": "", "why": "unreadable", "rows": 0, "bytes": p.stat().st_size})
    return out


# ---------------------------------------------------------------- restore (snapshot or any minute)
def _state_at(r: AppProject, at: datetime | None, name: str = "") -> tuple[dict[str, Any], dict[str, Any]]:
    """The app's rows {id: row} at that moment (+ the snapshot it started from)."""
    files = _list(r)
    if name:
        base = next((p for p in files if p.name == name), None)
        if base is None:
            raise W.AppError("Yeh backup nahi mila.", 404)
        snap = _read(base)
        rows = {x["id"]: x for x in snap["rows"]}
        return rows, snap
    at = at or datetime.now(timezone.utc)
    cands = []
    for p in files:
        try:
            dt = datetime.strptime(p.name[:15], "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt <= at:
            cands.append(p)
    if not cands:
        raise W.AppError("Us samay se pehle ka koi backup nahi; usse pehle ka data wapas nahi aa sakta.", 404)
    snap = _read(cands[-1])
    rows = {x["id"]: x for x in snap["rows"]}
    ensure_table()
    with session() as s:
        js = s.scalars(select(AppJournal).where(AppJournal.site_id == _site(r), AppJournal.id > int(snap.get("journal_id") or 0),
                                                AppJournal.at <= at).order_by(AppJournal.id)).all()
        for j in js:
            if j.op == "delete":
                rows.pop(j.row_id, None)
            else:
                old = rows.get(j.row_id) or {}
                rows[j.row_id] = {"id": j.row_id, "coll": j.coll, "owner": j.owner, "data": j.after,
                                  "created": old.get("created") or j.created, "updated": j.at.isoformat() if j.at else ""}
    return rows, snap


def preview(r: AppProject, at: str = "", name: str = "") -> dict[str, Any]:
    """What a restore WOULD do (nothing changes): counts per list then vs now, rows that come back / go / change."""
    when = _parse_at(at) if at else None
    then, snap = _state_at(r, when, name)
    with session() as s:
        cur = {x.id: x for x in s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r))).all()}
    def per(rows):
        out: dict[str, int] = {}
        for x in rows:
            c = x["coll"] if isinstance(x, dict) else x.coll
            if not c.startswith("_"):
                out[c] = out.get(c, 0) + 1
        return out
    back = [i for i in then if i not in cur]
    gone = [i for i in cur if i not in then and not cur[i].coll.startswith("_audit")]
    changed = [i for i in then if i in cur and (cur[i].data or "{}") != then[i]["data"]]
    return {"from": snap.get("at"), "to": (when.isoformat() if when else snap.get("at")), "lists_then": per(then.values()),
            "lists_now": per(cur.values()), "come_back": len(back), "go_away": len(gone), "change": len(changed)}


def restore(r: AppProject, at: str = "", name: str = "", members: bool = False, by: str = "owner") -> dict[str, Any]:
    """HER TAP. The app's rows become exactly what they were (a snapshot, or a minute): first a 'before restore' snapshot."""
    from . import locks as LK
    when = _parse_at(at) if at else None
    then, snap = _state_at(r, when, name)
    safety = snapshot(r, f"before restore to {when.isoformat()[:16] if when else name}", "before")
    with LK.app(r.id), session() as s:
        cur = {x.id: x for x in s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r))).all()}
        n_del = n_add = n_chg = 0
        for rid, x in cur.items():
            if x.coll in SKIP:
                continue
            if rid not in then:
                s.delete(x)
                n_del += 1
        for rid, y in then.items():
            if y["coll"] in SKIP:
                continue
            x = cur.get(rid)
            if x is None:
                s.add(W.SiteAppRow(id=rid, site_id=_site(r), coll=y["coll"], owner=y.get("owner") or "", data=y["data"],
                                   created_at=_dt(y.get("created")) or now(), updated_at=now()))
                n_add += 1
            elif (x.data or "{}") != y["data"] or x.coll != y["coll"] or (x.owner or "") != (y.get("owner") or ""):
                x.data, x.coll, x.owner, x.updated_at = y["data"], y["coll"], y.get("owner") or "", now()
                n_chg += 1
        if members and snap.get("members") is not None:   # accounts too (only when she asks: people may have joined since)
            have = {m.id: m for m in s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == _site(r))).all()}
            for m in snap["members"]:
                if m["id"] not in have:
                    s.add(W.SiteAppMember(id=m["id"], site_id=_site(r), email=m["email"], name=m["name"], pw=m["pw"],
                                          role=m["role"], gen=int(m.get("gen") or 0) + 1))
    STATS["restores"] += 1
    try:
        from .logic import engine as LE
        LE.audit(r, "restore", by=by, what=f"to {when.isoformat()[:16] if when else name}: {n_add} back, {n_del} removed, "
                                            f"{n_chg} changed (safety copy {safety['name']})")
    except Exception:                                   # noqa: BLE001
        log.debug("restore audit", exc_info=True)
    return {"restored_to": when.isoformat() if when else snap.get("at"), "came_back": n_add, "removed": n_del, "changed": n_chg,
            "safety": safety["name"],
            "say": f"Data wapas aa gaya ({n_add} wapas, {n_del} hate, {n_chg} badle). Isse pehle ki copy '{safety['name']}' "
                   "rakhi hai - galti ho to usi par wapas ja sakte hain."}


def _parse_at(at: str) -> datetime:
    s = str(at or "").strip().replace(" ", "T")
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise W.AppError("Samay YYYY-MM-DDTHH:MM (IST) mein dijiye.")
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))     # her clock
    return d.astimezone(timezone.utc)


def _dt(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


# ---------------------------------------------------------------- export (her data, her ZIP)
def export(r: AppProject) -> bytes:
    """A ZIP: one CSV per list (Excel-safe cells), data.json (everything), accounts.csv (no password hashes)."""
    from . import backend as BE
    sch = BE.schema(r)
    with session() as s:
        rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r)).order_by(W.SiteAppRow.created_at)).all()
        mems = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == _site(r))).all()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        alld: dict[str, list] = {}
        for c in sch["collections"]:
            keys = [f["key"] for f in c["fields"]]
            out = io.StringIO()
            wr = csv.writer(out)
            wr.writerow(["id", "created", *[f["label"] for f in c["fields"]]])
            mine = [x for x in rows if x.coll == c["key"]]
            for x in mine:
                d = json.loads(x.data or "{}")
                wr.writerow([x.id, x.created_at.isoformat() if x.created_at else "", *[_cell(d.get(k)) for k in keys]])
                alld.setdefault(c["key"], []).append({"id": x.id, "created": x.created_at.isoformat() if x.created_at else "", **d})
            z.writestr(f"{c['key']}.csv", "﻿" + out.getvalue())
        acc = io.StringIO()
        wr = csv.writer(acc)
        wr.writerow(["id", "name", "email", "role", "since"])
        for m in mems:
            wr.writerow([m.id, _cell(m.name), _cell(m.email), m.role, m.created_at.isoformat() if m.created_at else ""])
        z.writestr("accounts.csv", "﻿" + acc.getvalue())
        z.writestr("data.json", json.dumps({"app": r.name, "number": r.number, "exported": now().isoformat(),
                                            "lists": alld}, ensure_ascii=False, indent=1))
        z.writestr("README.txt", f"{r.name} ({r.number}) - data exported {now().isoformat()[:16]} UTC.\n"
                                 "One CSV per list (opens in Excel), data.json = everything, accounts.csv = the app's accounts "
                                 "(passwords are never exported).\n")
    STATS["exports"] += 1
    return buf.getvalue()


def _cell(v: Any) -> str:
    s = v if isinstance(v, str) else (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else ("" if v is None else str(v)))
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s       # a cell never runs as a spreadsheet formula


# ---------------------------------------------------------------- the worker's daily job
_last = 0.0


def daily_tick(force: bool = False) -> int:
    """Once an hour: every app with a backend whose newest daily snapshot is older than a day gets one; old journal pruned."""
    global _last
    if not force and time.time() - _last < 3600:
        return 0
    _last = time.time()
    with session() as s:
        apps = s.scalars(select(AppProject).where(AppProject.backend.like('%"schema"%'))).all()
        for a in apps:
            s.expunge(a)
    made = 0
    for r in apps:
        try:
            daily = [p for p in _list(r) if _kind(p) == "daily"]
            if daily:
                last = datetime.strptime(daily[-1].name[:15], "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - last < timedelta(hours=23):
                    continue
            with session() as s:
                has = s.scalar(select(W.SiteAppRow.id).where(W.SiteAppRow.site_id == _site(r)).limit(1))
            if not has:
                continue
            snapshot(r, "daily", "daily")
            made += 1
            from . import meter as MT                   # files + writes against her limits, once a day
            MT.daily_watch(r)
        except Exception:                               # noqa: BLE001 - one app never stops the others
            log.exception("daily snapshot failed for %s", r.id)
    prune_journal()
    return made


def prune_journal(days: int = JOURNAL_DAYS) -> int:
    ensure_table()
    cut = datetime.now(timezone.utc) - timedelta(days=days)
    with session() as s:
        old = s.scalars(select(AppJournal).where(AppJournal.at < cut).limit(20000)).all()
        for j in old:
            s.delete(j)
    return len(old)
