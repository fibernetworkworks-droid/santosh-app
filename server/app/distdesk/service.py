"""The Distributed Systems Engineer's engine: retry policies and call chains worked out (backoff, jitter, deadlines, how retries
multiply), quorums and placement across zones, histories checked for linearizability (hers, or made by the fault-injection
simulator), and TLA+ specs - starters, the TLC output read back, the CI workflow. All code - no model, no money - and nothing runs
on her systems. Pasted histories and output are DATA."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import linear as LN, quorum as QU, retry as RT, sim as SM, tla as TL

log = logging.getLogger("santosh.distdesk")

KINDS = ("retry", "chain", "quorum", "history", "sim", "tlc")
PRE = {"retry": "R", "chain": "C", "quorum": "Q", "history": "H", "sim": "J", "tlc": "T"}
FIELDS = ("system", "fail_rate", "clients", "specs_dir", "branch", "tla_version")
KEEP = 400
MAX_TEXT = 2_000_000


class DistError(ValueError):
    pass


class XItem(Base):
    __tablename__ = "distdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ds"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(10), default="retry")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class XSettings(Base):
    __tablename__ = "distdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    system: Mapped[str] = mapped_column(String(120), default="")
    fail_rate: Mapped[float] = mapped_column(Float, default=1.0)
    clients: Mapped[int] = mapped_column(Integer, default=1000)
    specs_dir: Mapped[str] = mapped_column(String(120), default="specs")
    branch: Mapped[str] = mapped_column(String(80), default="main")
    tla_version: Mapped[str] = mapped_column(String(20), default=TL.TLA_VERSION)


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


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    if f.get("system") is not None:
        c["system"] = str(f["system"])[:120]
    if f.get("fail_rate") not in (None, ""):
        try:
            v = float(f["fail_rate"])
        except (TypeError, ValueError):
            raise DistError("Failure rate: 0 to 100 %.")
        v = v / 100 if v > 1 else v
        if not 0 <= v <= 1:
            raise DistError("Failure rate: 0 to 100 %.")
        c["fail_rate"] = v
    if f.get("clients") not in (None, ""):
        try:
            v = int(float(f["clients"]))
        except (TypeError, ValueError):
            raise DistError("Clients: 1 to 100,000.")
        if not 1 <= v <= 100_000:
            raise DistError("Clients: 1 to 100,000.")
        c["clients"] = v
    for k in ("specs_dir", "branch"):
        if f.get(k) not in (None, ""):
            if not TL._SAFE.match(str(f[k])) or ".." in str(f[k]):
                raise DistError(f"{k}: letters, digits and ./_- only.")
            c[k] = str(f[k])
    if f.get("tla_version") not in (None, ""):
        if not re.fullmatch(r"v\d+\.\d+\.\d+", str(f["tla_version"])):
            raise DistError("TLA+ tools version: like v1.8.0.")
        c["tla_version"] = str(f["tla_version"])
    with session() as s:
        r = s.get(XSettings, tenant)
        if r is None:
            r = XSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    bad = any(i.get("sev") == "bad" for i in res.get("issues") or [])
    if kind == "retry":
        return {"worst_ms": res.get("worst_ms"), "load": res.get("load_factor"), "jitter": (res.get("policy") or {}).get("jitter"), "bad": bad,
                "issues": len(res.get("issues") or [])}
    if kind == "chain":
        return {"amplification": res.get("amplification"), "hops": len(res.get("hops") or []), "bad": bad, "issues": len(res.get("issues") or [])}
    if kind == "quorum":
        return {"n": res.get("n"), "mode": res.get("mode"), "overlap": res.get("overlap"), "bad": bad, "issues": len(res.get("issues") or [])}
    if kind == "history":
        return {"result": res.get("result"), "ops": res.get("ops"), "bad": res.get("result") == "fail"}
    if kind == "sim":
        ch = res.get("check") or {}
        return {"protocol": (res.get("config") or {}).get("protocol"), "result": ch.get("result"), "ops": ch.get("ops"),
                "lost": len(res.get("lost_writes") or []), "bad": ch.get("result") == "fail" or bool(res.get("lost_writes"))}
    if kind == "tlc":
        return {"result": res.get("result"), "invariant": res.get("invariant"), "distinct": res.get("distinct"),
                "bad": res.get("result") not in ("pass",)}
    return {}


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
            raise DistError("Not found.")
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
            raise DistError("The settings must be JSON.")
        if isinstance(d, dict):
            return d
    return {}


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise DistError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise DistError("That is longer than 2,000,000 characters.")
    try:
        if kind == "retry":
            res = RT.analyse(inp, float(inp.get("fail_rate", st["fail_rate"])), int(inp.get("clients", st["clients"])))
            p = res["policy"]
            auto = f"Retry: {p['attempts']} tries, {p['base_ms']:g} ms x{p['multiplier']:g}, {p['jitter']} jitter"
        elif kind == "chain":
            hops = inp.get("hops") if isinstance(inp.get("hops"), list) else None
            if hops is None:
                raise DistError("Give the services in order, outermost first.")
            res = RT.chain(hops)
            auto = "Chain: " + " -> ".join(h["name"] for h in res["hops"])
        elif kind == "quorum":
            zones = inp.get("zones") if isinstance(inp.get("zones"), list) and inp.get("zones") else None
            res = QU.analyse(inp.get("n", 3), inp.get("r"), inp.get("w"), zones, str(inp.get("mode") or "quorum"))
            auto = (f"Consensus: {res['n']} voters" if res["mode"] == "consensus" else f"Quorum N={res['n']} R={res['read_quorum']} W={res['write_quorum']}") + \
                   (f" across {len(zones)} zones" if zones else "")
        elif kind == "history":
            if not text.strip():
                raise DistError("Paste the history first.")
            res = LN.check(text)
            auto = f"History: {res['ops']} operations, {res['processes']} processes"
        elif kind == "sim":
            preset = str(inp.get("preset") or "")
            cfg = {**SM.PRESETS.get(preset, {}), **{k: v for k, v in inp.items() if k != "preset"}}
            res = SM.run(cfg)
            text = res.pop("history")
            auto = f"Simulation: {res['config']['protocol']}, {res['config']['replicas']} replicas, seed {res['config']['seed']}"
        else:
            if not text.strip():
                raise DistError("Paste the TLC output first.")
            res = TL.read_output(text)
            if not res["ok"]:
                raise DistError(res["error"])
            auto = "TLC: " + ({"pass": "no error", "invariant": f"{res['invariant']} violated"}.get(res["result"], res["result"]))
    except (RT.RetryError, QU.QuorumError, LN.HistoryError, SM.SimError) as e:
        raise DistError(str(e))
    with session() as s:
        n = len(s.scalars(select(XItem.id).where(XItem.tenant_id == tenant, XItem.kind == kind)).all()) + 1
        r = XItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        if kind in ("history", "tlc") and _brief(kind, res).get("bad") is False:
            r.status = "fixed"
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
        raise DistError("Status: open | fixed | ignored")
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


def spec(key: str, fixed: bool = True) -> dict[str, Any]:
    try:
        return TL.template(key, fixed)
    except ValueError as e:
        raise DistError(str(e))


def workflow(tenant: str, **over: Any) -> dict[str, Any]:
    st = {**settings(tenant), **{k: v for k, v in over.items() if v not in (None, "")}}
    try:
        return TL.workflow(st["specs_dir"], st["tla_version"], st["branch"])
    except ValueError as e:
        raise DistError(str(e))


def health() -> dict[str, Any]:
    return {"protocols": SM.PROTOCOLS, "presets": list(SM.PRESETS), "jitters": list(RT.JITTERS),
            "specs": [{"key": k, "title": v["title"], "about": v["about"], "switch": v["switch"]} for k, v in TL.TEMPLATES.items()],
            "limits": {"history_ops_per_key": LN.MAX_OPS, "sim": SM.LIMITS}}
