"""The Robotics Software Engineer's desk: robot arms worked out from their Denavit-Hartenberg tables (where the tool is, the joint
values that reach a target, singularities, joint torques), URDF models checked the way loaders and simulators read them, ROS 2 systems
read from their own tools' output (topics nobody publishes, QoS that never connects, a broken tf tree), control loops tuned from a
recorded step, moves planned as trapezoid or S-curve profiles, and a CI check that builds and tests her ROS 2 packages - all in code,
no model, no money. Nothing connects to or runs on her robots. Pasted tables, models, logs and data are DATA."""
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
from . import arm as AR, ci as CI, control as CT, motion as MO, rosgraph as RG, urdf as UR

log = logging.getLogger("santosh.rbdesk")

KINDS = ("arm", "urdf", "graph", "control", "motion")
PRE = {"arm": "A", "urdf": "U", "graph": "G", "control": "C", "motion": "V"}
FIELDS = ("dh", "length_unit", "payload_kg", "ros_distro", "packages", "urdf_path", "extra_deps", "runner", "sync")
KEEP = 400
MAX_TEXT = 20_000_000
ERRORS = (AR.ArmError, UR.UrdfError, RG.GraphError, CT.ControlError, MO.MotionError, CI.CiError)


class RbError(ValueError):
    pass


class RItem(Base):
    __tablename__ = "rbdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="arm")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RSettings(Base):
    __tablename__ = "rbdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dh: Mapped[str] = mapped_column(String(10), default="standard")
    length_unit: Mapped[str] = mapped_column(String(4), default="m")
    payload_kg: Mapped[float] = mapped_column(Float, default=0.0)
    ros_distro: Mapped[str] = mapped_column(String(12), default="jazzy")
    packages: Mapped[str] = mapped_column(String(400), default="")
    urdf_path: Mapped[str] = mapped_column(String(200), default="")
    extra_deps: Mapped[str] = mapped_column(String(400), default="")
    runner: Mapped[str] = mapped_column(String(40), default="")
    sync: Mapped[str] = mapped_column(String(4), default="yes")


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    RItem.__table__.create(eng, checkfirst=True)
    RSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(RSettings, tenant)
        d = {k: getattr(r, k) if r else RSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise RbError(f"{name}: a number.")
    if not lo <= x <= hi:
        raise RbError(f"{name}: {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    for k, opts, msg in (("dh", ("standard", "modified"), "Table kind: standard (Denavit-Hartenberg) or modified (Craig)."),
                         ("length_unit", ("m", "mm", "cm", "in"), "Lengths without a unit are in: m, mm, cm or in."),
                         ("ros_distro", tuple(CI.DISTROS), "ROS 2 version: " + ", ".join(CI.DISTROS) + "."),
                         ("sync", ("yes", "no"), "Finish every axis together: yes or no.")):
        if g(k):
            if f[k] not in opts:
                raise RbError(msg)
            c[k] = f[k]
    if g("payload_kg"):
        c["payload_kg"] = _num(f["payload_kg"], "Payload (kg)", 0, 5000)
    for k, n in (("packages", 400), ("urdf_path", 200), ("extra_deps", 400), ("runner", 40)):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:n]
    probe = {**settings(tenant), **c}
    if probe.get("packages"):
        try:
            _ci(probe)
        except CI.CiError as e:
            raise RbError(str(e))
    with session() as s:
        r = s.get(RSettings, tenant)
        if r is None:
            r = RSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _ci(st: dict[str, Any]) -> dict[str, Any]:
    return CI.workflow(distro=st["ros_distro"], packages=st["packages"], urdf=st["urdf_path"], runner=st["runner"], extra_deps=st["extra_deps"])


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "arm":
        b.update(dof=res.get("dof"), xyz=(res.get("pose") or {}).get("xyz"), ik=(res.get("ik") or {}).get("ok") if res.get("ik") else None,
                 near=res.get("near_singular"))
    elif kind == "urdf":
        b.update(name=res.get("name"), links=res.get("links"), moving=res.get("moving"), mass=res.get("mass"))
    elif kind == "graph":
        b.update(nodes=len(res.get("nodes") or []), topics=len([t for t in res.get("topics") or [] if not t.get("system")]), frames=len(res.get("tf") or []))
    elif kind == "control":
        m = res.get("metrics") or {}
        b.update(closed=res.get("closed"), overshoot=m.get("overshoot"), settle=m.get("settle"), model=bool(res.get("model")))
    elif kind == "motion":
        b.update(T=res.get("T"), axes=len(res.get("axes") or []))
    return b


def _view(r: RItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(RItem).where(RItem.tenant_id == tenant)
        if kind:
            q = q.where(RItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(RItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> RItem:
    r = s.get(RItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(RItem).where(RItem.tenant_id == tenant, RItem.number == str(iid or "").upper())).first()
        if r is None:
            raise RbError("Not found.")
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
            raise RbError("The settings must be JSON.")
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
    if kind == "arm":
        res = AR.analyse(text, g("q", ""), g("target", ""), g("payload", st["payload_kg"]), str(g("dh", st["dh"])), str(g("length_unit", st["length_unit"])))
        x, y, z = res["pose"]["xyz"]
        return res, f"Arm: {res['dof']} joints, tool at {x:.3g}, {y:.3g}, {z:.3g} m"
    if kind == "urdf":
        res = UR.check(text)
        return res, f"Model: {res['name'] or 'robot'}, {res['links']} links, {res['moving']} moving joints"[:120]
    if kind == "graph":
        res = RG.analyse(text)
        return res, ("ROS graph: " + res["verdict"].split(" - ")[0])[:120]
    if kind == "control":
        res = CT.analyse(text, str(g("mode", "auto")), g("u_step", ""), g("t_step", ""), g("kp", ""), g("ki", ""), g("kd", ""))
        m = res["metrics"]
        return res, f"Control: {'closed' if res['closed'] else 'open'} loop, {m['overshoot']:.0f}% overshoot"
    sync = str(g("sync", st["sync"])).lower() not in ("no", "false", "0")
    res = MO.analyse(text, sync)
    return res, f"Motion: {len(res['axes'])} axes, {res['T']:.3g} s"


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise RbError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise RbError("That is longer than 20,000,000 characters.")
    if not text.strip():
        raise RbError({"arm": "One joint per line first - e.g. 'j1 revolute d=0.333 a=0 alpha=-90 min=-166 max=166'.",
                         "urdf": "Paste the robot's URDF first (expand xacro with `xacro robot.urdf.xacro > robot.urdf`).",
                         "graph": "Paste `ros2 node info` for your nodes, `ros2 topic info -v` for a topic, or the tf frames first.",
                         "control": "Paste the step response first: time, measured value (and the setpoint or the command) per line.",
                         "motion": "One axis per line first - e.g. 'x 0.5m vmax=1 amax=2 jerk=20'."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
        res = _clean(res)
    except ERRORS as e:
        raise RbError(str(e))
    with session() as s:
        n = len(s.scalars(select(RItem.id).where(RItem.tenant_id == tenant, RItem.kind == kind)).all()) + 1
        r = RItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(RItem.id).where(RItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(RItem).where(RItem.tenant_id == tenant).order_by(RItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise RbError("Status: open | fixed | ignored")
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
    if not st.get("packages"):
        return {"missing": True, "say": "Set the ROS 2 version and the packages to build in Settings first."}
    try:
        return _ci(st)
    except CI.CiError as e:
        raise RbError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "distros": list(CI.DISTROS),
            "notes": "Everything is worked out in code from what you paste. Nothing connects to or runs on your robots."}
