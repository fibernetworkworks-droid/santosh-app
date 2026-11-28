"""The Cloud Engineer's desk: the cloud bill added up by day, service, account, region and owner (spikes, growth, the month at
its run rate against her budget), resources nobody uses (unattached disks, unused addresses, stopped and idle machines, old
snapshots), commitments sized from her own usage, access policies read for what lets too much in (AWS, Google Cloud, Azure),
networks checked for overlaps and open admin ports, and a CI access guard - all in code, no model, no money. Nothing runs on her
cloud. Pasted bills, inventories and policies are DATA."""
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
from . import bill as BL, ci as CI, commit as CM, iam as IA, network as NW, waste as WS
from .common import ClInputError

log = logging.getLogger("santosh.cldesk")

KINDS = ("bill", "waste", "commit", "iam", "network")
PRE = {"bill": "B", "waste": "W", "commit": "C", "iam": "A", "network": "N"}
FIELDS = ("currency", "budget", "tag_key", "sens", "idle_cpu", "keep_days", "od_rate", "commit_rate", "discount", "current_commit",
          "provider", "policy_dir", "runner")
KEEP = 400
MAX_TEXT = 60_000_000
ERRORS = (ClInputError, TableError)


class ClError(ValueError):
    pass


class CItem(Base):
    __tablename__ = "cldesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="bill")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CSettings(Base):
    __tablename__ = "cldesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    currency: Mapped[str] = mapped_column(String(8), default="")
    budget: Mapped[float] = mapped_column(Float, default=0.0)
    tag_key: Mapped[str] = mapped_column(String(60), default="")
    sens: Mapped[float] = mapped_column(Float, default=3.0)
    idle_cpu: Mapped[float] = mapped_column(Float, default=5.0)
    keep_days: Mapped[float] = mapped_column(Float, default=90.0)
    od_rate: Mapped[float] = mapped_column(Float, default=0.0)
    commit_rate: Mapped[float] = mapped_column(Float, default=0.0)
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    current_commit: Mapped[float] = mapped_column(Float, default=0.0)
    provider: Mapped[str] = mapped_column(String(10), default="aws")
    policy_dir: Mapped[str] = mapped_column(String(160), default="")
    runner: Mapped[str] = mapped_column(String(40), default="ubuntu-24.04")


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    CItem.__table__.create(eng, checkfirst=True)
    CSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(CSettings, tenant)
        d = {k: getattr(r, k) if r else CSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ClError(f"{name}: a number.")
    if not lo <= x <= hi:
        raise ClError(f"{name}: {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    for k, lo, hi, nm in (("budget", 0, 1e12, "Monthly budget"), ("sens", 1, 10, "Spike sensitivity"), ("idle_cpu", 0, 100, "Idle CPU line, %"),
                          ("keep_days", 1, 3650, "Keep days"), ("od_rate", 0, 1e6, "On-demand price per unit-hour"),
                          ("commit_rate", 0, 1e6, "Committed price per unit-hour"), ("discount", 0, 0.99, "Commitment discount"),
                          ("current_commit", 0, 1e9, "Current commitment")):
        if g(k):
            c[k] = _num(f[k], nm, lo, hi)
    for k, n in (("currency", 8), ("tag_key", 60), ("provider", 10), ("policy_dir", 160), ("runner", 40)):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:n]
    if "currency" in c:
        c["currency"] = c["currency"].upper()
        if c["currency"] and not re.fullmatch(r"[A-Z]{3}", c["currency"]):
            raise ClError("Currency: a three-letter code such as USD, EUR, INR.")
    probe = {**settings(tenant), **c}
    if probe["provider"] not in ("aws", "azure", "gcp", "other"):
        raise ClError("Provider: aws, azure, gcp or other.")
    if probe.get("od_rate") and probe.get("commit_rate") and probe["commit_rate"] >= probe["od_rate"]:
        raise ClError("The committed price must be below the on-demand price.")
    if probe.get("policy_dir"):
        try:
            _ci(probe)
        except CI.CiError as e:
            raise ClError(str(e))
    with session() as s:
        r = s.get(CSettings, tenant)
        if r is None:
            r = CSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _ci(st: dict[str, Any]) -> dict[str, Any]:
    return CI.workflow(policy_dir=st["policy_dir"] or "policies", runner=st["runner"])


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "bill":
        b.update(total=res.get("total"), days=res.get("days"), forecast=(res.get("month") or {}).get("forecast"), spikes=len(res.get("spikes") or []),
                 currency=res.get("currency"))
    elif kind == "waste":
        b.update(resources=res.get("resources"), found=len(res.get("found") or []), save=res.get("save"), currency=res.get("currency"))
    elif kind == "commit":
        b.update(best=(res.get("best") or {}).get("commit"), save_pct=(res.get("best") or {}).get("save_pct"), save=(res.get("best") or {}).get("save"),
                 util=((res.get("current") or {}).get("util")), currency=res.get("currency"))
    elif kind == "iam":
        b.update(statements=res.get("statements"), flagged=res.get("flagged"), kinds=res.get("kinds"))
    elif kind == "network":
        b.update(vpcs=len(res.get("vpcs") or []), subnets=len(res.get("subnets") or []), rules=len(res.get("rules") or []), plans=len(res.get("plans") or []))
    return b


def _view(r: CItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(CItem).where(CItem.tenant_id == tenant)
        if kind:
            q = q.where(CItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(CItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> CItem:
    r = s.get(CItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(CItem).where(CItem.tenant_id == tenant, CItem.number == str(iid or "").upper())).first()
        if r is None:
            raise ClError("Not found.")
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
            raise ClError("The settings must be JSON.")
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
    cur = str(g("currency", st["currency"]) or "")
    if kind == "bill":
        res = BL.analyse(text, str(g("tag_key", st["tag_key"]) or ""), f("budget", st["budget"]) or None, f("sens", st["sens"]) or 3.0, cur)
        return res, "Bill: " + res["verdict"].split(";")[0]
    if kind == "waste":
        res = WS.analyse(text, f("idle_cpu", st["idle_cpu"]) or 5.0, f("keep_days", st["keep_days"]) or 90.0, g("today"), cur)
        return res, "Waste: " + res["verdict"]
    if kind == "commit":
        od, cr, dc = f("od_rate", st["od_rate"]) or None, f("commit_rate", st["commit_rate"]) or None, f("discount", st["discount"]) or None
        cc = f("current", st["current_commit"]) if g("current") not in (None, "") or st["current_commit"] else None
        res = CM.plan(text, od, cr, dc, cc, str(g("unit", "") or ""), cur)
        return res, "Commitment: " + res["verdict"]
    if kind == "iam":
        res = IA.analyse(text)
        return res, "Access: " + res["verdict"]
    res = NW.analyse(text, str(g("provider", st["provider"]) or "aws"))
    return res, "Network: " + res["verdict"]


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise ClError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise ClError("That is longer than 20,000,000 characters.")
    if not text.strip():
        raise ClError({"bill": "Paste the bill first: a cost export (FOCUS, AWS Cost and Usage Report, Google Cloud billing export, Azure cost details) as CSV.",
                       "waste": "Paste the inventory first: a CSV with id, type, state, attached, CPU use, age and monthly cost.",
                       "commit": "Paste the usage first: a CSV of time and usage (instance-hours, vCPUs, or on-demand spend per hour).",
                       "iam": "Paste a policy first: AWS IAM JSON, `gcloud ... get-iam-policy --format=json` or `az role assignment list`.",
                       "network": "Describe the network first: 'vpc prod 10.0.0.0/16', 'subnet app-a 10.0.1.0/24 vpc=prod', 'rule web in tcp 22 0.0.0.0/0'."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
        res = _clean(res)
    except ERRORS as e:
        raise ClError(str(e))
    with session() as s:
        n = len(s.scalars(select(CItem.id).where(CItem.tenant_id == tenant, CItem.kind == kind)).all()) + 1
        r = CItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(CItem.id).where(CItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(CItem).where(CItem.tenant_id == tenant).order_by(CItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise ClError("Status: open | fixed | ignored")
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
    if not st.get("policy_dir"):
        return {"missing": True, "say": "Set the policy folder in Settings first."}
    try:
        return _ci(st)
    except CI.CiError as e:
        raise ClError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "notes": "Everything is worked out in code from what you paste. Nothing runs on your cloud."}
