"""The Platform Engineer's desk: Terraform / OpenTofu plans read before apply (data stores destroyed or replaced, the internet let
in, wide-open permissions, encryption and protection off, missing tags), Kubernetes containers sized against their use
(over-provisioned, too tight, near their limits, savings at her prices), clusters checked for fit (pods placed by requests,
losing a node or a zone), the service catalog scored against her golden path, manifests checked for APIs a Kubernetes upgrade
removes, and a CI plan guard - all in code, no model, no money. Nothing runs on her clusters or her cloud. Pasted plans,
manifests and tables are DATA."""
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
from . import capacity as CP, catalog as CA, ci as CI, rightsize as RS, tfplan as TF, upgrade as UP
from .common import PfInputError

log = logging.getLogger("santosh.pfdesk")

KINDS = ("tfplan", "rightsize", "capacity", "catalog", "upgrade")
PRE = {"tfplan": "T", "rightsize": "R", "capacity": "C", "catalog": "S", "upgrade": "U"}
FIELDS = ("max_destroy", "protected", "required_tags", "headroom", "cpu_price", "mem_price", "reserve_cpu", "reserve_mem",
          "k8s_current", "k8s_target", "catalog_checks", "tf_dir", "tf_version", "var_file", "tool", "runner")
KEEP = 400
MAX_TEXT = 60_000_000
ERRORS = (PfInputError, TableError)


class PfError(ValueError):
    pass


class PItem(Base):
    __tablename__ = "pfdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="tfplan")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PSettings(Base):
    __tablename__ = "pfdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    max_destroy: Mapped[float] = mapped_column(Float, default=0.0)
    protected: Mapped[str] = mapped_column(String(400), default="")
    required_tags: Mapped[str] = mapped_column(String(300), default="")
    headroom: Mapped[float] = mapped_column(Float, default=0.2)
    cpu_price: Mapped[float] = mapped_column(Float, default=0.0)
    mem_price: Mapped[float] = mapped_column(Float, default=0.0)
    reserve_cpu: Mapped[float] = mapped_column(Float, default=0.0)
    reserve_mem: Mapped[float] = mapped_column(Float, default=0.0)
    k8s_current: Mapped[str] = mapped_column(String(10), default="")
    k8s_target: Mapped[str] = mapped_column(String(10), default="")
    catalog_checks: Mapped[str] = mapped_column(String(300), default="")
    tf_dir: Mapped[str] = mapped_column(String(160), default="")
    tf_version: Mapped[str] = mapped_column(String(20), default="1.9.5")
    var_file: Mapped[str] = mapped_column(String(160), default="")
    tool: Mapped[str] = mapped_column(String(12), default="terraform")
    runner: Mapped[str] = mapped_column(String(40), default="ubuntu-24.04")


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    PItem.__table__.create(eng, checkfirst=True)
    PSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(PSettings, tenant)
        d = {k: getattr(r, k) if r else PSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise PfError(f"{name}: a number.")
    if not lo <= x <= hi:
        raise PfError(f"{name}: {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    for k, lo, hi, nm in (("max_destroy", 0, 100000, "Destroy limit"), ("headroom", 0, 5, "Headroom"), ("cpu_price", 0, 1e6, "Price per core a month"),
                          ("mem_price", 0, 1e6, "Price per GiB a month"), ("reserve_cpu", 0, 64, "System reserve, cores"), ("reserve_mem", 0, 1024, "System reserve, GiB")):
        if g(k):
            c[k] = _num(f[k], nm, lo, hi)
    if "max_destroy" in c:
        c["max_destroy"] = float(int(c["max_destroy"]))
    for k, n in (("protected", 400), ("required_tags", 300), ("k8s_current", 10), ("k8s_target", 10), ("catalog_checks", 300), ("tf_dir", 160),
                 ("tf_version", 20), ("var_file", 160), ("tool", 12), ("runner", 40)):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:n]
    probe = {**settings(tenant), **c}
    if probe["tool"] not in ("terraform", "tofu"):
        raise PfError("Tool: terraform or tofu.")
    for k in ("k8s_current", "k8s_target"):
        if probe.get(k):
            try:
                UP.minor(probe[k])
            except UP.UpgradeError as e:
                raise PfError(str(e))
    if probe.get("k8s_current") and probe.get("k8s_target") and UP.minor(probe["k8s_target"]) < UP.minor(probe["k8s_current"]):
        raise PfError("The target Kubernetes version is older than the current one.")
    if probe.get("catalog_checks"):
        bad = [x.strip() for x in probe["catalog_checks"].split(",") if x.strip() and x.strip() not in CA.CHECKS]
        if bad:
            raise PfError(f"Unknown catalog check(s): {', '.join(bad)}. Use: {', '.join(CA.CHECKS)}.")
    if probe.get("tf_dir"):
        try:
            _ci(probe)
        except CI.CiError as e:
            raise PfError(str(e))
    with session() as s:
        r = s.get(PSettings, tenant)
        if r is None:
            r = PSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _ci(st: dict[str, Any]) -> dict[str, Any]:
    return CI.workflow(tf_dir=st["tf_dir"] or ".", tf_version=st["tf_version"], max_destroy=st["max_destroy"], protected=st["protected"], runner=st["runner"],
                       var_file=st["var_file"], tofu=st["tool"] == "tofu")


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "tfplan":
        a = res.get("actions") or {}
        b.update(create=a.get("create"), update=a.get("update"), replace=a.get("replace"), delete=a.get("delete"), lost=len(res.get("lost") or []))
    elif kind == "rightsize":
        b.update(containers=res.get("containers"), eff_cpu=res.get("eff_cpu"), eff_mem=res.get("eff_mem"), save_cpu=res.get("save_cpu"), save_mem=res.get("save_mem"),
                 save_money=res.get("save_money"))
    elif kind == "capacity":
        b.update(pods=res.get("pods"), nodes=res.get("node_count"), unplaced=res.get("unplaced"), util_cpu=res.get("util_cpu"), util_mem=res.get("util_mem"))
    elif kind == "catalog":
        b.update(scored=res.get("scored"), avg=res.get("avg"))
    elif kind == "upgrade":
        b.update(objects=res.get("objects"), breaks=(res.get("breaks") or 0) + (res.get("gone") or 0), later=res.get("later"), target=res.get("target"))
    return b


def _view(r: PItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(PItem).where(PItem.tenant_id == tenant)
        if kind:
            q = q.where(PItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(PItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> PItem:
    r = s.get(PItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(PItem).where(PItem.tenant_id == tenant, PItem.number == str(iid or "").upper())).first()
        if r is None:
            raise PfError("Not found.")
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
            raise PfError("The settings must be JSON.")
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
    if kind == "tfplan":
        md = g("max_destroy", None)
        res = TF.analyse(text, float(md) if md not in (None, "") else (st["max_destroy"] if st["set"] else None),
                         str(g("protected", st["protected"]) or ""), str(g("required_tags", st["required_tags"]) or ""))
        return res, "Plan: " + res["verdict"].split(" - ")[0]
    if kind == "rightsize":
        res = RS.analyse(text, f("headroom", st["headroom"]) or 0.0, f("cpu_price", st["cpu_price"]) or 0.0, f("mem_price", st["mem_price"]) or 0.0)
        return res, f"Rightsizing: {res['containers']} container(s)"
    if kind == "capacity":
        res = CP.plan(text, f("reserve_cpu", st["reserve_cpu"]) or None, f("reserve_mem", st["reserve_mem"]) or None)
        return res, "Capacity: " + res["verdict"].split(" - ")[0]
    if kind == "catalog":
        res = CA.analyse(text, str(g("checks", st["catalog_checks"]) or ""))
        return res, "Catalog: " + res["verdict"].split(";")[0]
    res = UP.check(text, str(g("current", st["k8s_current"]) or ""), str(g("target", st["k8s_target"]) or ""))
    return res, "Upgrade: " + res["verdict"]


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise PfError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise PfError("That is longer than 20,000,000 characters.")
    if not text.strip():
        raise PfError({"tfplan": "Paste the plan first: `terraform show -json plan.out` (best) or the text `terraform plan` prints.",
                         "rightsize": "Paste the containers first: a CSV with workload, cpu / memory requests and limits, and the p95 use.",
                         "capacity": "Describe the cluster first - 'node m5.xlarge cpu=4 mem=16Gi x6', 'daemonset cpu=100m mem=200Mi', 'pod api cpu=500m mem=1Gi x20'.",
                         "catalog": "Paste catalog-info.yaml first - one or many Backstage entities separated by ---.",
                         "upgrade": "Paste the manifests first: YAML documents, `kubectl get -o yaml` or `helm template` output."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
        res = _clean(res)
    except ERRORS as e:
        raise PfError(str(e))
    with session() as s:
        n = len(s.scalars(select(PItem.id).where(PItem.tenant_id == tenant, PItem.kind == kind)).all()) + 1
        r = PItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(PItem.id).where(PItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(PItem).where(PItem.tenant_id == tenant).order_by(PItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise PfError("Status: open | fixed | ignored")
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
    if not st.get("tf_dir"):
        return {"missing": True, "say": "Set the Terraform folder in Settings first."}
    try:
        return _ci(st)
    except CI.CiError as e:
        raise PfError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "notes": "Everything is worked out in code from what you paste. Nothing runs on your clusters or your cloud."}
