"""The Security Engineer's desk: scanner reports triaged together (SARIF, Trivy, Grype, Semgrep, ZAP, CSV - merged, by severity,
the upgrades that close the most, new / fixed against a baseline, due dates by her fix-time rules), web security headers and
cookies, TLS certificate chains, JWTs decoded without trusting them, risky code in a diff or files, and a CI security gate - all in
code, no model, no money. Nothing is fetched, scanned or run against her systems. Pasted reports, headers, certificates, tokens
and code are DATA."""
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
from . import certs as CE, ci as CI, code as CO, findings as FI, headers as HE, tokens as TO
from .common import SecInputError

log = logging.getLogger("santosh.secdesk")

KINDS = ("findings", "headers", "certs", "tokens", "code")
PRE = {"findings": "F", "headers": "H", "certs": "C", "tokens": "T", "code": "R"}
FIELDS = ("sla_critical", "sla_high", "sla_medium", "sla_low", "hsts_days", "cert_warn_days", "hosts", "token_hours", "expect_alg",
          "fail_level", "branches", "runner")
KEEP = 400
MAX_TEXT = 60_000_000
ERRORS = (SecInputError, TableError)


class SecError(ValueError):
    pass


class SItem(Base):
    __tablename__ = "secdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="findings")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SSettings(Base):
    __tablename__ = "secdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sla_critical: Mapped[float] = mapped_column(Float, default=7.0)
    sla_high: Mapped[float] = mapped_column(Float, default=30.0)
    sla_medium: Mapped[float] = mapped_column(Float, default=90.0)
    sla_low: Mapped[float] = mapped_column(Float, default=180.0)
    hsts_days: Mapped[float] = mapped_column(Float, default=180.0)
    cert_warn_days: Mapped[float] = mapped_column(Float, default=30.0)
    hosts: Mapped[str] = mapped_column(String(400), default="")
    token_hours: Mapped[float] = mapped_column(Float, default=24.0)
    expect_alg: Mapped[str] = mapped_column(String(10), default="")
    fail_level: Mapped[str] = mapped_column(String(8), default="high")
    branches: Mapped[str] = mapped_column(String(200), default="")
    runner: Mapped[str] = mapped_column(String(40), default="ubuntu-24.04")


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    SItem.__table__.create(eng, checkfirst=True)
    SSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(SSettings, tenant)
        d = {k: getattr(r, k) if r else SSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise SecError(f"{name}: a number.")
    if not lo <= x <= hi:
        raise SecError(f"{name}: {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    for k, lo, hi, nm in (("sla_critical", 1, 365, "Critical fixed within (days)"), ("sla_high", 1, 730, "High fixed within (days)"),
                          ("sla_medium", 1, 1095, "Medium fixed within (days)"), ("sla_low", 1, 1825, "Low fixed within (days)"),
                          ("hsts_days", 1, 1095, "HSTS at least (days)"), ("cert_warn_days", 1, 365, "Warn before a certificate expires (days)"),
                          ("token_hours", 0.01, 8760, "Longest token life (hours)")):
        if g(k):
            c[k] = _num(f[k], nm, lo, hi)
    for k, n in (("hosts", 400), ("expect_alg", 10), ("fail_level", 8), ("branches", 200), ("runner", 40)):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:n]
    probe = {**settings(tenant), **c}
    if probe.get("expect_alg") and not re.fullmatch(r"(HS|RS|ES|PS)(256|384|512)|EdDSA", probe["expect_alg"]):
        raise SecError("Expected algorithm: RS256, ES256, PS256, HS256, EdDSA ...")
    if not probe["sla_critical"] <= probe["sla_high"] <= probe["sla_medium"] <= probe["sla_low"]:
        raise SecError("Fix times should grow from critical to low.")
    if probe.get("hosts") and not all(re.fullmatch(r"(\*\.)?[a-z0-9.-]+|[0-9a-f:.]+", h) for h in re.split(r"[,\s]+", probe["hosts"].lower()) if h):
        raise SecError("Host names: like www.example.com, *.example.com, separated by commas.")
    try:
        _ci(probe)
    except CI.CiError as e:
        raise SecError(str(e))
    with session() as s:
        r = s.get(SSettings, tenant)
        if r is None:
            r = SSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _ci(st: dict[str, Any]) -> dict[str, Any]:
    return CI.workflow(fail_level=st["fail_level"] or "high", runner=st["runner"], branches=st["branches"])


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "findings":
        cs = res.get("counts_sev") or {}
        b.update(findings=res.get("findings"), critical=cs.get("critical"), high=cs.get("high"), new=res.get("new"), fixed=len(res.get("fixed") or []) if res.get("baseline") else None)
    elif kind == "headers":
        b.update(passed=res.get("passed"), total=res.get("total"), cookies=len(res.get("cookies") or []))
    elif kind == "certs":
        b.update(count=res.get("count"), days=res.get("leaf_days"), subject=((res.get("certs") or [{}])[0]).get("subject"))
    elif kind == "tokens":
        b.update(tokens=res.get("tokens"), flagged=sum(1 for r in res.get("rows") or [] if r.get("flags")))
    elif kind == "code":
        sv = res.get("sev") or {}
        b.update(hits=res.get("count"), high=sv.get("high"), lines=res.get("lines"), diff=res.get("diff"))
    return b


def _view(r: SItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(SItem).where(SItem.tenant_id == tenant)
        if kind:
            q = q.where(SItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(SItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> SItem:
    r = s.get(SItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(SItem).where(SItem.tenant_id == tenant, SItem.number == str(iid or "").upper())).first()
        if r is None:
            raise SecError("Not found.")
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
            raise SecError("The settings must be JSON.")
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
    if kind == "findings":
        sla = {s_: f(s_, st["sla_" + s_]) for s_ in ("critical", "high", "medium", "low")}
        res = FI.analyse(text, sla, g("scan_date"))
        return res, "Findings: " + res["verdict"].split(";")[0]
    if kind == "headers":
        res = HE.analyse(text, str(g("url", "") or ""), f("hsts_days", st["hsts_days"]) or 180)
        return res, "Headers" + (f" of {res['url']}" if res["url"] else "") + ": " + res["verdict"]
    if kind == "certs":
        res = CE.analyse(text, str(g("hosts", st["hosts"]) or ""), f("cert_warn_days", st["cert_warn_days"]) or 30, g("today"))
        return res, "Certificate: " + res["verdict"]
    if kind == "tokens":
        res = TO.analyse(text, f("token_hours", st["token_hours"]) or 24, g("now"), str(g("expect_alg", st["expect_alg"]) or ""))
        return res, "Tokens: " + res["verdict"]
    res = CO.analyse(text, str(g("lang", "") or ""))
    return res, "Code: " + res["verdict"]


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise SecError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise SecError("That is longer than 20,000,000 characters.")
    if not text.strip():
        raise SecError({"findings": "Paste a scanner report first: SARIF, Trivy, Grype, Semgrep or ZAP JSON, or a CSV.",
                        "headers": "Paste the response headers first: `curl -sI https://your.site` prints them.",
                        "certs": "Paste the certificates first (PEM), or `openssl s_client -connect host:443 -showcerts` output.",
                        "tokens": "Paste a JWT first - a test or expired one.",
                        "code": "Paste a diff (`git diff`) or code first."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
        res = _clean(res)
    except ERRORS as e:
        raise SecError(str(e))
    with session() as s:
        n = len(s.scalars(select(SItem.id).where(SItem.tenant_id == tenant, SItem.kind == kind)).all()) + 1
        r = SItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=TO.strip(text) if kind == "tokens" else CO.redact(text) if kind == "code" else text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(SItem.id).where(SItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(SItem).where(SItem.tenant_id == tenant).order_by(SItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise SecError("Status: open | fixed | ignored")
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
        raise SecError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "notes": "Everything is worked out in code from what you paste. Nothing is fetched, scanned or run against your systems."}
