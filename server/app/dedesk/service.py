"""The Data Engineer's desk: pipelines read as graphs (loops, the critical path, the run window), table schemas checked against
their contracts (breaking and safe changes), source and target reconciled row by row on a key, run histories read job by job
(failures, slow runs, row counts, stale data), table storage read from a file listing (small files, partition skew, formats,
scan cost), and a CI check that runs her data tests and fails a pull request that breaks a table's shape - all in code, no
model, no money. Nothing runs on her machines or her warehouse. Pasted pipelines, schemas, data and logs are DATA."""
from __future__ import annotations

import json
import logging
import math

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from ..mldesk.table import TableError
from . import ci as CI, contract as CT, dag as DG, recon as RC, runs as RU, storage as SG
from .common import DeInputError

log = logging.getLogger("santosh.dedesk")

KINDS = ("dag", "schema", "recon", "runs", "storage")
PRE = {"dag": "P", "schema": "S", "recon": "R", "runs": "J", "storage": "F"}
FIELDS = ("key_cols", "tolerance", "window_min", "sla_min", "freshness_h", "small_mb", "target_mb", "price_tb",
          "test_cmd", "setup_cmd", "schema_path", "contract_path", "python", "runner")
KEEP = 400
MAX_TEXT = 60_000_000
ERRORS = (DeInputError, TableError)


class DeError(ValueError):
    pass


class DItem(Base):
    __tablename__ = "dedesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("de"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="dag")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DSettings(Base):
    __tablename__ = "dedesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    key_cols: Mapped[str] = mapped_column(String(200), default="")
    tolerance: Mapped[float] = mapped_column(Float, default=0.0)
    window_min: Mapped[float] = mapped_column(Float, default=0.0)
    sla_min: Mapped[float] = mapped_column(Float, default=0.0)
    freshness_h: Mapped[float] = mapped_column(Float, default=0.0)
    small_mb: Mapped[float] = mapped_column(Float, default=32.0)
    target_mb: Mapped[float] = mapped_column(Float, default=256.0)
    price_tb: Mapped[float] = mapped_column(Float, default=0.0)
    test_cmd: Mapped[str] = mapped_column(String(400), default="")
    setup_cmd: Mapped[str] = mapped_column(String(400), default="")
    schema_path: Mapped[str] = mapped_column(String(160), default="")
    contract_path: Mapped[str] = mapped_column(String(160), default="")
    python: Mapped[str] = mapped_column(String(8), default="3.12")
    runner: Mapped[str] = mapped_column(String(40), default="ubuntu-24.04")


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


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise DeError(f"{name}: a number.")
    if not lo <= x <= hi:
        raise DeError(f"{name}: {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    for k, lo, hi, nm in (("tolerance", 0, 1e12, "Tolerance"), ("window_min", 0, 100000, "Run window (minutes)"), ("sla_min", 0, 100000, "Time limit (minutes)"),
                          ("freshness_h", 0, 100000, "Freshness (hours)"), ("small_mb", 0.01, 100000, "Small file size (MB)"), ("target_mb", 1, 100000, "Target file size (MB)"),
                          ("price_tb", 0, 100000, "Price per TB scanned")):
        if g(k):
            c[k] = _num(f[k], nm, lo, hi)
    for k, n in (("key_cols", 200), ("test_cmd", 400), ("setup_cmd", 400), ("schema_path", 160), ("contract_path", 160), ("python", 8), ("runner", 40)):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:n]
    probe = {**settings(tenant), **c}
    if probe["small_mb"] >= probe["target_mb"]:
        raise DeError("The small-file size must be below the target file size.")
    if probe.get("test_cmd") or probe.get("schema_path") or probe.get("contract_path"):
        try:
            _ci({**probe, "test_cmd": probe.get("test_cmd") or "true"})
        except CI.CiError as e:
            raise DeError(str(e))
    with session() as s:
        r = s.get(DSettings, tenant)
        if r is None:
            r = DSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _ci(st: dict[str, Any]) -> dict[str, Any]:
    return CI.workflow(test_cmd=st["test_cmd"], schema=st["schema_path"], contract=st["contract_path"], setup_cmd=st["setup_cmd"], python=st["python"], runner=st["runner"])


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "dag":
        cr = res.get("critical") or {}
        b.update(tasks=res.get("tasks"), levels=len(res.get("levels") or []), crit=cr.get("minutes"), loop=bool(res.get("cycle")))
    elif kind == "schema":
        b.update(mode=res.get("mode"), cols=res.get("new_cols") or len(res.get("columns") or []), breaking=res.get("breaking"), changes=len(res.get("changes") or []))
    elif kind == "recon":
        b.update(rows=res.get("source_rows"), missing=res.get("missing"), extra=res.get("extra"), changed=res.get("changed"))
    elif kind == "runs":
        jobs = res.get("jobs") or []
        b.update(jobs=len(jobs), runs=res.get("runs"), failed=res.get("failed"), failing=sum(1 for j in jobs if j.get("failing_now")))
    elif kind == "storage":
        b.update(files=res.get("files"), total=res.get("total"), small=res.get("small"), parts=(res.get("partitions") or {}).get("count"))
    return b


def _view(r: DItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
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
            raise DeError("Not found.")
    return r


def get(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        return _view(_row(s, tenant, iid), True)


def _dict(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if isinstance(v, str) and v.strip():
        try:
            d = json.loads(v)
        except ValueError:
            raise DeError("The settings must be JSON.")
        if isinstance(d, dict):
            return d
    return {}


def _clean(v: Any) -> Any:
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, set):
        return sorted(_clean(x) for x in v)
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        return _clean(v.item())
    return v


def _run(tenant: str, kind: str, text: str, inp: dict[str, Any], st: dict[str, Any]) -> tuple[dict[str, Any], str]:
    g = lambda k, d=None: inp.get(k) if inp.get(k) not in (None, "") else d   # noqa: E731
    f = lambda k, d: float(g(k, d)) if g(k, d) not in (None, "") else None   # noqa: E731
    if kind == "dag":
        res = DG.analyse(text, f("window", st["window_min"]) or None)
        return res, "Pipeline: " + res["verdict"].split(";")[0]
    if kind == "schema":
        res = CT.compare(text, str(g("new", "") or ""))
        return res, "Schema: " + res["verdict"].split(" - ")[0]
    if kind == "recon":
        res = RC.reconcile(text, str(g("target", "") or ""), str(g("key", st["key_cols"]) or ""), f("tolerance", st["tolerance"]) or 0.0, str(g("ignore", "") or ""))
        return res, "Reconcile: " + res["verdict"]
    if kind == "runs":
        res = RU.analyse(text, f("sla", st["sla_min"]) or None, f("freshness", st["freshness_h"]) or None, str(g("as_of", "") or ""))
        return res, "Runs: " + res["verdict"].split(";")[0]
    res = SG.analyse(text, f("small_mb", st["small_mb"]) or 32, f("target_mb", st["target_mb"]) or 256, f("price_tb", st["price_tb"]) or None)
    return res, "Storage: " + res["verdict"]


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise DeError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise DeError("That is longer than 20,000,000 characters.")
    if not text.strip():
        raise DeError({"dag": "Paste the pipeline first: 'extract >> transform >> load', 'a -> b', 'orders: stg_orders, stg_customers', or a dbt manifest.json.",
                         "schema": "Paste the contract first: a CREATE TABLE, a JSON Schema / Avro record, a YAML column list or lines 'name type'.",
                         "recon": "Paste the source first: a CSV with a header row and the key column.",
                         "runs": "Paste the run history first: a CSV with job, start, end (or duration) and status.",
                         "storage": "Paste a file listing first: aws s3 ls --recursive, gsutil ls -l, hdfs dfs -ls -R or path,size lines."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
        res = _clean(res)
    except ERRORS as e:
        raise DeError(str(e))
    with session() as s:
        n = len(s.scalars(select(DItem.id).where(DItem.tenant_id == tenant, DItem.kind == kind)).all()) + 1
        r = DItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
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
        raise DeError("Status: open | fixed | ignored")
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


def ci_for(tenant: str) -> dict[str, Any]:
    st = settings(tenant)
    if not st.get("test_cmd"):
        return {"missing": True, "say": "Set the data test command in Settings first."}
    try:
        return _ci(st)
    except CI.CiError as e:
        raise DeError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "notes": "Everything is worked out in code from what you paste. Nothing runs on your machines or your warehouse."}
