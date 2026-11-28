"""The Virtualization / Hypervisor Engineer's desk: container configs checked against the Pod Security Standards, Dockerfiles,
seccomp profiles checked and made from a trace, libvirt VM definitions, host capacity and failover, CPU flags for live migration,
and the CI workflow that runs her container hardened - all in code, no model, no money. Nothing is changed on her hosts: fixes,
profiles and workflows are text she applies herself. Pasted configs, traces and XML are DATA."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import ci as CI, container as CO, cpu as CP, domain as DO, plan as PL, seccomp as SC

log = logging.getLogger("santosh.virtdesk")

KINDS = ("container", "seccomp", "trace", "domain", "plan", "cpu")
PRE = {"container": "C", "seccomp": "S", "trace": "T", "domain": "V", "plan": "P", "cpu": "U"}
FIELDS = ("arch", "target", "uid", "vcpu_ratio", "ram_ratio", "reserve_gb", "reserve_cores", "failures", "image", "dockerfile",
          "context", "seccomp_file", "port", "health", "memory", "pids", "cpus", "net_bind")
KEEP = 400
MAX_TEXT = 3_000_000
ERRORS = (CO.ContainerError, SC.SeccompError, DO.DomainError, PL.PlanError, CP.CpuError, CI.CiError)


class VirtError(ValueError):
    pass


class XItem(Base):
    __tablename__ = "virtdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("vt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="container")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class XSettings(Base):
    __tablename__ = "virtdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    arch: Mapped[str] = mapped_column(String(12), default="x86_64")
    target: Mapped[str] = mapped_column(String(12), default="restricted")
    uid: Mapped[int] = mapped_column(Integer, default=10001)
    vcpu_ratio: Mapped[float] = mapped_column(Float, default=4.0)
    ram_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    reserve_gb: Mapped[float] = mapped_column(Float, default=4.0)
    reserve_cores: Mapped[float] = mapped_column(Float, default=1.0)
    failures: Mapped[int] = mapped_column(Integer, default=1)
    image: Mapped[str] = mapped_column(String(220), default="")
    dockerfile: Mapped[str] = mapped_column(String(200), default="Dockerfile")
    context: Mapped[str] = mapped_column(String(200), default=".")
    seccomp_file: Mapped[str] = mapped_column(String(200), default="")
    port: Mapped[int] = mapped_column(Integer, default=0)
    health: Mapped[str] = mapped_column(String(220), default="")
    memory: Mapped[str] = mapped_column(String(12), default="512m")
    pids: Mapped[int] = mapped_column(Integer, default=256)
    cpus: Mapped[str] = mapped_column(String(8), default="1")
    net_bind: Mapped[bool] = mapped_column(Boolean, default=False)


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    XItem.__table__.create(eng, checkfirst=True)
    XSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(XSettings, tenant)
        d = {k: getattr(r, k) if r else XSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float, whole: bool = False) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise VirtError(f"{name}: a number.")
    if whole and x != int(x):
        raise VirtError(f"{name}: a whole number.")
    if not lo <= x <= hi:
        raise VirtError(f"{name}: {lo:g} to {hi:g}.")
    return int(x) if whole else x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    if g("arch"):
        a = str(f["arch"]).lower()
        if a not in ("x86_64", "aarch64"):
            raise VirtError("Architecture: x86_64 or aarch64.")
        c["arch"] = a
    if g("target"):
        if f["target"] not in ("baseline", "restricted"):
            raise VirtError("Level to meet: baseline or restricted.")
        c["target"] = f["target"]
    for k, name, lo, hi, w in (("uid", "User id", 1, 2 ** 31, True), ("vcpu_ratio", "vCPUs per core", 0.1, 32, False),
                               ("ram_ratio", "RAM overcommit", 0.5, 4, False), ("reserve_gb", "RAM kept for the host", 0, 1024, False),
                               ("reserve_cores", "Cores kept for the host", 0, 64, False), ("failures", "Hosts it must survive losing", 0, 2, True),
                               ("port", "Port", 0, 65535, True), ("pids", "Process limit", 16, 100000, True)):
        if g(k):
            c[k] = _num(f[k], name, lo, hi, w)
    for k in ("image", "dockerfile", "context", "seccomp_file", "health", "memory", "cpus"):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:220]
    if "net_bind" in f:
        c["net_bind"] = str(f["net_bind"]).lower() in ("1", "true", "yes", "on")
    probe = {**settings(tenant), **c}
    try:
        CI.workflow(**{k: probe[k] for k in ("image", "dockerfile", "context", "seccomp_file", "uid", "port", "health", "memory", "pids", "cpus", "net_bind")})
    except CI.CiError as e:
        raise VirtError(str(e))
    with session() as s:
        r = s.get(XSettings, tenant)
        if r is None:
            r = XSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "container":
        b.update(format=res.get("format"), level=res.get("level"), n=len(res.get("containers") or []), meets=res.get("meets"), target=res.get("target"))
    elif kind == "seccomp":
        b.update(mode=res.get("mode"), allowed=res.get("allowed"), of=res.get("of"), risky=len([r for r in res.get("risky") or [] if r["sev"] != "info"]))
    elif kind == "trace":
        b.update(allowed=res.get("allowed"), seen=res.get("seen"), risky=len([r for r in res.get("risky") or [] if r["sev"] != "info"]), bad=False)
    elif kind == "domain":
        b.update(vcpus=res.get("vcpus"), gib=res.get("memory_gib"), migratable=res.get("migratable"))
    elif kind == "plan":
        b.update(vms=res.get("vms"), hosts=len(res.get("hosts") or []), survives=res.get("survives"), unplaced=len(res.get("unplaced") or []),
                 ratio=(res.get("totals") or {}).get("vcpu_per_core"))
    elif kind == "cpu":
        b.update(hosts=len(res.get("hosts") or []), level=res.get("common_level"), same=res.get("same"))
    return b


def _view(r: XItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(XItem).where(XItem.tenant_id == tenant)
        if kind:
            q = q.where(XItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(XItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> XItem:
    r = s.get(XItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(XItem).where(XItem.tenant_id == tenant, XItem.number == str(iid or "").upper())).first()
        if r is None:
            raise VirtError("Not found.")
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
            raise VirtError("The settings must be JSON.")
        if isinstance(d, dict):
            return d
    return {}


def _run(kind: str, text: str, inp: dict[str, Any], st: dict[str, Any]) -> tuple[dict[str, Any], str]:
    g = lambda k, d=None: inp.get(k) if inp.get(k) not in (None, "") else d   # noqa: E731
    if kind == "container":
        res = CO.check(text, int(g("uid", st["uid"])), str(g("target", st["target"])))
        what = {"kubernetes": "Kubernetes", "compose": "Compose", "docker": "docker run", "podman": "podman run", "oci": "OCI config", "dockerfile": "Dockerfile"}
        first = (res["containers"][0]["name"] if res["containers"] else "")
        return res, f"{what.get(res['format'], res['format'])}: {first}"[:120] if first else f"{what.get(res['format'], res['format'])}"
    if kind == "seccomp":
        res = SC.check(text, str(g("arch", st["arch"])))
        return res, f"Seccomp profile ({res['mode']}, {res['allowed']} open)"
    if kind == "trace":
        res = SC.generate(text, str(g("arch", st["arch"])), str(g("base", "1")).lower() not in ("0", "false", "no"))
        return res, f"Profile from a {res['kind']} ({res['allowed']} syscalls)"
    if kind == "domain":
        res = DO.check(text)
        return res, f"VM {res['name']}"
    if kind == "plan":
        res = PL.plan(text, g("vcpu_ratio", st["vcpu_ratio"]), g("ram_ratio", st["ram_ratio"]), g("reserve_gb", st["reserve_gb"]),
                      g("reserve_cores", st["reserve_cores"]), g("failures", st["failures"]))
        return res, f"Capacity: {res['vms']} VMs on {len(res['hosts'])} hosts"
    res = CP.compare(text)
    return res, f"CPU flags of {len(res['hosts'])} host(s)"


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise VirtError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise VirtError("That is longer than 3,000,000 characters.")
    if not text.strip():
        raise VirtError({"container": "Paste the config first: Kubernetes YAML, a Compose file, a docker run line, config.json or a Dockerfile.",
                         "seccomp": "Paste the seccomp profile (JSON) first.", "trace": "Paste the strace output or syscall names first.",
                         "domain": "Paste the VM's XML first (virsh dumpxml <name>).", "plan": "List the hosts and VMs first.",
                         "cpu": "Paste each host's CPU flags first."}[kind])
    try:
        res, auto = _run(kind, text, inp, st)
    except ERRORS as e:
        raise VirtError(str(e))
    with session() as s:
        n = len(s.scalars(select(XItem.id).where(XItem.tenant_id == tenant, XItem.kind == kind)).all()) + 1
        r = XItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(XItem.id).where(XItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(XItem).where(XItem.tenant_id == tenant).order_by(XItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise VirtError("Status: open | fixed | ignored")
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


def ci_for(tenant: str, **over: Any) -> dict[str, Any]:
    st = {**settings(tenant), **{k: v for k, v in over.items() if v not in (None, "")}}
    try:
        return CI.workflow(**{k: st[k] for k in ("image", "dockerfile", "context", "seccomp_file", "uid", "port", "health", "memory", "pids", "cpus", "net_bind")})
    except CI.CiError as e:
        raise VirtError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "levels": [lv for lv, _ in CP.LEVELS], "arches": sorted(SC.NR), "syscalls": {a: len(v) for a, v in SC.NR.items()},
            "baseline_caps": sorted(CO.BASE_CAPS),
            "notes": "Everything is worked out in code. Fixes, profiles and workflows are text you apply yourself; Hoola changes nothing on your hosts."}
