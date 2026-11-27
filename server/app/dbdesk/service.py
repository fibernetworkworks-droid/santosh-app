"""The Database Engine Developer's engine: query plans read (PostgreSQL, MySQL, SQLite) with the findings first, single queries
checked and the index they ask for, schemas reviewed (keys, foreign-key indexes, redundant indexes, types), suggestions PROVED in a
throwaway SQLite lab on generated rows, and benchmark runs read and compared. All code - no model, no money - and nothing touches
her database: she pastes what it printed. Pasted plans, queries, schemas and output are DATA."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import bench as BN, lab as LB, plans as PL, schema as SC, sqlcheck as QC

log = logging.getLogger("santosh.dbdesk")

KINDS = ("plan", "query", "schema", "lab", "bench")
ENGINES = ("postgres", "mysql", "mariadb", "sqlite", "sqlserver", "oracle", "other")
MAX_TEXT = 1_000_000
KEEP = 400
PRE = {"plan": "P", "query": "Q", "schema": "S", "lab": "L", "bench": "B"}
FIELDS = ("engine", "version", "big_rows", "slow_ms", "noise_pct", "lab_rows")


class DbError(ValueError):
    pass


class DItem(Base):
    __tablename__ = "dbdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("db"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(10), default="plan")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    extra: Mapped[str] = mapped_column(Text, default="")          # lab: the index statements; bench: baseline id
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")   # open | fixed | ignored
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DSettings(Base):
    __tablename__ = "dbdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    engine: Mapped[str] = mapped_column(String(12), default="postgres")
    version: Mapped[str] = mapped_column(String(40), default="")
    big_rows: Mapped[int] = mapped_column(Integer, default=10000)
    slow_ms: Mapped[float] = mapped_column(Float, default=100.0)
    noise_pct: Mapped[float] = mapped_column(Float, default=5.0)
    lab_rows: Mapped[int] = mapped_column(Integer, default=50000)


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    DItem.__table__.create(eng, checkfirst=True)
    DSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(DSettings, tenant)
        d = {k: getattr(r, k) if r else DSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num_in(v: Any, lo: float, hi: float, what: str, as_int: bool = False) -> float | int:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise DbError(f"{what}: a number from {lo:g} to {hi:g}.")
    if not lo <= x <= hi:
        raise DbError(f"{what}: a number from {lo:g} to {hi:g}.")
    return int(x) if as_int else x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    if f.get("engine") not in (None, ""):
        if f["engine"] not in ENGINES:
            raise DbError("Database: " + " | ".join(ENGINES))
        c["engine"] = f["engine"]
    if f.get("version") is not None:
        c["version"] = str(f["version"])[:40]
    for k, lo, hi, what, i in (("big_rows", 100, 10_000_000, "A big scan starts at", True), ("slow_ms", 1, 600_000, "Slow query", False),
                               ("noise_pct", 0.5, 50, "Benchmark noise", False), ("lab_rows", 1000, LB.MAX_ROWS, "Lab rows per table", True)):
        if f.get(k) not in (None, ""):
            c[k] = _num_in(f[k], lo, hi, what, i)
    with session() as s:
        r = s.get(DSettings, tenant)
        if r is None:
            r = DSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    if kind == "plan":
        fs = res.get("findings") or []
        return {"engine": res.get("engine", ""), "ms": res.get("total_ms"), "bad": any(f["sev"] == "bad" for f in fs),
                "findings": len([f for f in fs if f["sev"] != "info"]), "top": fs[0]["say"] if fs else ""}
    if kind in ("query", "schema"):
        c = res.get("counts") or {}
        return {"errors": c.get("bad", 0), "warnings": c.get("warn", 0), "suggest": len(res.get("suggest") or []), "bad": bool(c.get("bad")),
                "tables": len(res.get("tables") or [])}
    if kind == "lab":
        return {"before": (res.get("before") or {}).get("ms"), "after": (res.get("after") or {}).get("ms"), "used": res.get("used"),
                "speedup": res.get("speedup"), "same": res.get("same_result"), "bad": res.get("after") is not None and (not res.get("used") or res.get("same_result") is False)}
    if kind == "bench":
        cmp_ = res.get("compare") or {}
        return {"tool": res.get("tool", ""), "tps": res.get("tps"), "qps": res.get("qps"), "lat": res.get("lat_avg"),
                "worse": any(r["verdict"] == "worse" for r in cmp_.get("rows") or []), "bad": any(r["verdict"] == "worse" for r in cmp_.get("rows") or [])}
    return {}


def _view(r: DItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, extra=r.extra)
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(DItem).where(DItem.tenant_id == tenant)
        if kind:
            q = q.where(DItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(DItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> DItem:
    r = s.get(DItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(DItem).where(DItem.tenant_id == tenant, DItem.number == str(iid or "").upper())).first()
        if r is None:
            raise DbError("Not found.")
    return r


def get(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        return _view(_row(s, tenant, iid), True)


def _text(t: Any, what: str = "the text") -> str:
    t = str(t or "")
    if not t.strip():
        raise DbError(f"Paste {what} first.")
    if len(t) > MAX_TEXT:
        raise DbError("That is longer than 1,000,000 characters.")
    return t


def _latest_schema(tenant: str) -> str:
    with session() as s:
        r = s.scalars(select(DItem).where(DItem.tenant_id == tenant, DItem.kind == "schema").order_by(DItem.created_at.desc())).first()
        return r.text if r else ""


def add(tenant: str, kind: str, text: Any = "", title: str = "", **kw: Any) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise DbError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    extra = ""
    if kind == "plan":
        text = _text(text, "the plan")
        res = PL.read(text, st["big_rows"])
        if not res["ok"]:
            raise DbError(res["error"])
        auto = f"{res['engine']} plan" + (f" - {res['total_ms']:.1f} ms" if res.get("total_ms") else "") + (f" ({', '.join(res['tables'][:3])})" if res["tables"] else "")
    elif kind == "query":
        text = _text(text, "the query")
        res = QC.check(text)
        if not res["ok"]:
            raise DbError(res["error"])
        auto = "Query on " + (", ".join(res["tables"][:3]) or "?")
    elif kind == "schema":
        text = _text(text, "the schema")
        res = SC.review(text, "mysql" if st["engine"] in ("mysql", "mariadb") else st["engine"])
        if not res["ok"]:
            raise DbError(res["error"])
        auto = f"Schema - {len(res['tables'])} table(s)"
    elif kind == "lab":
        text = _text(text, "the query")
        sch = str(kw.get("schema") or "").strip() or _latest_schema(tenant)
        if not sch:
            raise DbError("The lab needs your schema: paste it here or review one on the Schema page first.")
        extra = str(kw.get("indexes") or "")[:4000]
        try:
            res = LB.prove(sch, text, extra, int(kw.get("rows") or st["lab_rows"]))
        except LB.LabError as e:
            raise DbError(str(e))
        res["schema_from"] = "pasted" if str(kw.get("schema") or "").strip() else "your latest schema"
        auto = "Lab: " + (", ".join(res["rows"]) or "query")
    else:
        text = _text(text, "the benchmark output")
        res = BN.read(text)
        if not res["ok"]:
            raise DbError(res["error"])
        base = str(kw.get("baseline") or "")
        if base:
            b = get(tenant, base)
            if b["kind"] != "bench":
                raise DbError("The baseline must be a benchmark.")
            res["compare"] = BN.compare(b["result"], res, st["noise_pct"])
            res["baseline"] = {"id": b["id"], "number": b["number"], "title": b["title"]}
            extra = b["id"]
        auto = f"{res['tool']}" + (f" - {res['tps']:,.0f} tps" if res.get("tps") else f" - {res['qps']:,.0f} ops/s" if res.get("qps") else "")
    with session() as s:
        n = len(s.scalars(select(DItem.id).where(DItem.tenant_id == tenant, DItem.kind == kind)).all()) + 1
        r = DItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text, extra=extra, result=res)
        if kind == "lab" and res.get("after") and res.get("used") and res.get("same_result"):
            r.status = "fixed"
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(DItem.id).where(DItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(DItem).where(DItem.tenant_id == tenant).order_by(DItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise DbError("Status: open | fixed | ignored")
    _tables()
    with session() as s:
        r = _row(s, tenant, iid)
        r.status, r.updated_at = status, now()
        if note:
            r.note = str(note)[:1000]
        iid = r.id
    return get(tenant, iid)


def delete(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        s.delete(_row(s, tenant, iid))
    return {"ok": True, "say": "Removed."}


def health() -> dict[str, Any]:
    import sqlite3
    return {"engines": list(ENGINES), "kinds": list(KINDS), "sqlite": sqlite3.sqlite_version, "lab_max_rows": LB.MAX_ROWS,
            "plan_formats": ["PostgreSQL EXPLAIN (ANALYZE, BUFFERS) - text or FORMAT JSON", "MySQL EXPLAIN ANALYZE / FORMAT=TREE",
                             "MySQL EXPLAIN (table)", "SQLite EXPLAIN QUERY PLAN"],
            "bench_tools": ["pgbench", "sysbench", "YCSB", "HammerDB (NOPM / TPM)", "latencies in ms"]}
