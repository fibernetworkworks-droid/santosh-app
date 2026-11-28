"""The DevSecOps Engineer's desk: CI workflows read for the ways pipelines are attacked (unpinned actions, script injection, privileged
triggers running pull request code, missing permissions), SBOMs read for licences and gaps, dependency manifests read for unpinned
versions, git sources, extra indexes and lookalike names, a repository's guard rails (branch protection, secret scanning, push
protection), fix-time metrics over time, and a CI pipeline guard - all in code, no model, no money. Nothing is run, installed or
changed on her systems. Pasted workflows, SBOMs, manifests and exports are DATA."""
from __future__ import annotations

import json
import logging
import math
import re

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from ..mldesk.table import TableError
from . import ci as CI, deps as DP, metrics as ME, repo as RP, sbom as SB, workflows as WF
from .common import DsoInputError

log = logging.getLogger("santosh.dsodesk")

KINDS = ("workflows", "sbom", "deps", "repo", "metrics")
PRE = {"workflows": "W", "sbom": "S", "deps": "D", "repo": "R", "metrics": "M"}
FIELDS = ("trusted_owners", "deny_licenses", "allow_licenses", "pin_dev", "min_reviews", "need_checks", "sla_critical", "sla_high", "sla_medium",
          "sla_low", "fail_level", "runner")
KEEP = 400
MAX_TEXT = 60_000_000
ERRORS = (DsoInputError, TableError)


class DsoError(ValueError):
    pass


class DItem(Base):
    __tablename__ = "dsodesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("do"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="workflows")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DSettings(Base):
    __tablename__ = "dsodesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trusted_owners: Mapped[str] = mapped_column(String(300), default="")
    deny_licenses: Mapped[str] = mapped_column(String(400), default="AGPL-*, SSPL-*")
    allow_licenses: Mapped[str] = mapped_column(String(600), default="")
    pin_dev: Mapped[float] = mapped_column(Float, default=0.0)
    min_reviews: Mapped[float] = mapped_column(Float, default=1.0)
    need_checks: Mapped[str] = mapped_column(String(300), default="")
    sla_critical: Mapped[float] = mapped_column(Float, default=7.0)
    sla_high: Mapped[float] = mapped_column(Float, default=30.0)
    sla_medium: Mapped[float] = mapped_column(Float, default=90.0)
    sla_low: Mapped[float] = mapped_column(Float, default=180.0)
    fail_level: Mapped[str] = mapped_column(String(8), default="warn")
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
        raise DsoError(f"{name}: a number.")
    if not lo <= x <= hi:
        raise DsoError(f"{name}: {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    for k, lo, hi, nm in (("min_reviews", 0, 6, "Reviews required at least"), ("pin_dev", 0, 1, "Pin development dependencies (0 or 1)"),
                          ("sla_critical", 1, 365, "Critical fixed within (days)"), ("sla_high", 1, 730, "High fixed within (days)"),
                          ("sla_medium", 1, 1095, "Medium fixed within (days)"), ("sla_low", 1, 1825, "Low fixed within (days)")):
        if g(k):
            c[k] = _num(f[k], nm, lo, hi)
    for k in ("min_reviews", "pin_dev"):
        if k in c:
            c[k] = float(int(c[k]))
    for k, n in (("trusted_owners", 300), ("deny_licenses", 400), ("allow_licenses", 600), ("need_checks", 300), ("fail_level", 8), ("runner", 40)):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:n]
    probe = {**settings(tenant), **c}
    if not probe["sla_critical"] <= probe["sla_high"] <= probe["sla_medium"] <= probe["sla_low"]:
        raise DsoError("Fix times should grow from critical to low.")
    for k in ("deny_licenses", "allow_licenses"):
        if probe.get(k) and not all(re.fullmatch(r"[A-Za-z0-9.+*\-]{1,60}", x.strip()) for x in probe[k].split(",") if x.strip()):
            raise DsoError("Licences: SPDX ids separated by commas, * allowed (GPL-*, AGPL-3.0-only).")
    try:
        _ci(probe)
    except CI.CiError as e:
        raise DsoError(str(e))
    with session() as s:
        r = s.get(DSettings, tenant)
        if r is None:
            r = DSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _ci(st: dict[str, Any]) -> dict[str, Any]:
    return CI.workflow(fail_level=st["fail_level"] or "warn", trusted_owners=st["trusted_owners"], runner=st["runner"])


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "workflows":
        b.update(files=len(res.get("files") or []), actions=len(res.get("actions") or []), unpinned=res.get("unpinned"))
    elif kind == "sbom":
        fm = res.get("families") or {}
        b.update(components=res.get("components"), strong=fm.get("strong"), unknown=fm.get("unknown"))
    elif kind == "deps":
        b.update(deps=res.get("deps"), unpinned=res.get("unpinned"), git=res.get("git"), lookalike=res.get("lookalike"))
    elif kind == "repo":
        b.update(repo=res.get("repo"), passed=res.get("passed"), total=res.get("total"), protected=res.get("protected"))
    elif kind == "metrics":
        b.update(findings=res.get("findings"), open=res.get("open"), late=res.get("late"))
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
            raise DsoError("Not found.")
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
            raise DsoError("The settings must be JSON.")
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
    if kind == "workflows":
        res = WF.analyse(text, str(g("trusted_owners", st["trusted_owners"]) or ""))
        return res, "Workflows: " + res["verdict"]
    if kind == "sbom":
        res = SB.analyse(text, str(g("deny", st["deny_licenses"]) or ""), str(g("allow", st["allow_licenses"]) or ""))
        return res, "SBOM: " + res["verdict"].split(":")[0]
    if kind == "deps":
        res = DP.analyse(text, bool(f("pin_dev", st["pin_dev"]) or 0))
        return res, "Dependencies: " + res["verdict"]
    if kind == "repo":
        res = RP.analyse(text, int(f("min_reviews", st["min_reviews"]) or 0), str(g("need_checks", st["need_checks"]) or ""))
        return res, "Repository: " + res["verdict"]
    sla = {s_: f(s_, st["sla_" + s_]) for s_ in ("critical", "high", "medium", "low")}
    res = ME.analyse(text, sla, g("today"))
    return res, "Fix times: " + res["verdict"]


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise DsoError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise DsoError("That is longer than 20,000,000 characters.")
    if not text.strip():
        raise DsoError({"workflows": "Paste a workflow from .github/workflows first (several: '## path' before each).",
                        "sbom": "Paste an SBOM first: CycloneDX JSON or SPDX JSON.",
                        "deps": "Paste a manifest first: package.json, requirements.txt, go.mod or Cargo.toml.",
                        "repo": "Paste `gh api repos/OWNER/REPO` and its branch protection output first.",
                        "metrics": "Paste findings over time first: a CSV with id, severity, opened, closed."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
        res = _clean(res)
    except ERRORS as e:
        raise DsoError(str(e))
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
        raise DsoError("Status: open | fixed | ignored")
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
    try:
        return _ci(settings(tenant))
    except CI.CiError as e:
        raise DsoError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "notes": "Everything is worked out in code from what you paste. Nothing is run, installed or changed on your systems."}
