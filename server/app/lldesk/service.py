"""The Backend Systems Engineer (Low Latency)'s desk: latency runs worked out and compared, a request path's latency budget, hot-path
code read for what costs latency, struct layout and false sharing, profiles, the host's tuning and a CI check that guards a percentile
on every pull request - all in code, no model, no money. Nothing runs on her machines: fixes and workflows are text she applies
herself. Pasted samples, code, profiles and host outputs are DATA."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import budget as BU, ci as CI, hotpath as HP, latency as LA, layout as LY, profile as PR, tuning as TU

log = logging.getLogger("santosh.lldesk")

KINDS = ("latency", "budget", "code", "layout", "profile", "tuning")
PRE = {"latency": "L", "budget": "B", "code": "H", "layout": "S", "profile": "P", "tuning": "T"}
FIELDS = ("unit", "budget_unit", "target_q", "target_us", "interval_us", "abi", "line", "bench_cmd", "build_cmd", "out_file", "tolerance",
          "runs", "runner", "pin_cpu")
CI_KEYS = ("bench_cmd", "build_cmd", "out_file", "unit", "target_q", "tolerance", "runs", "runner", "pin_cpu")
KEEP = 400
MAX_TEXT = 40_000_000
ERRORS = (LA.LatencyError, BU.BudgetError, HP.CodeError, LY.LayoutError, PR.ProfileError, TU.TuneError, CI.CiError)
UNITS = ("ns", "us", "ms", "s")


class LowLatError(ValueError):
    pass


class LItem(Base):
    __tablename__ = "lldesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ll"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="latency")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LSettings(Base):
    __tablename__ = "lldesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    unit: Mapped[str] = mapped_column(String(4), default="us")
    budget_unit: Mapped[str] = mapped_column(String(4), default="ms")
    target_q: Mapped[float] = mapped_column(Float, default=99.0)
    target_us: Mapped[float] = mapped_column(Float, default=0.0)
    interval_us: Mapped[float] = mapped_column(Float, default=0.0)
    abi: Mapped[str] = mapped_column(String(8), default="lp64")
    line: Mapped[int] = mapped_column(Integer, default=64)
    bench_cmd: Mapped[str] = mapped_column(String(400), default="")
    build_cmd: Mapped[str] = mapped_column(String(400), default="")
    out_file: Mapped[str] = mapped_column(String(120), default="bench.txt")
    tolerance: Mapped[float] = mapped_column(Float, default=10.0)
    runs: Mapped[int] = mapped_column(Integer, default=3)
    runner: Mapped[str] = mapped_column(String(40), default="ubuntu-24.04")
    pin_cpu: Mapped[bool] = mapped_column(Boolean, default=True)


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    LItem.__table__.create(eng, checkfirst=True)
    LSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(LSettings, tenant)
        d = {k: getattr(r, k) if r else LSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float, whole: bool = False) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise LowLatError(f"{name}: a number.")
    if whole and x != int(x):
        raise LowLatError(f"{name}: a whole number.")
    if not lo <= x <= hi:
        raise LowLatError(f"{name}: {lo:g} to {hi:g}.")
    return int(x) if whole else x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    for k, name in (("unit", "Unit of your samples"), ("budget_unit", "Unit of the budget")):
        if g(k):
            if str(f[k]) not in UNITS:
                raise LowLatError(f"{name}: ns, us, ms or s.")
            c[k] = str(f[k])
    if g("abi"):
        if f["abi"] not in ("lp64", "llp64"):
            raise LowLatError("ABI: lp64 (Linux / macOS) or llp64 (Windows).")
        c["abi"] = f["abi"]
    if g("line"):
        c["line"] = _num(f["line"], "Cache line", 32, 128, True)
        if c["line"] not in (32, 64, 128):
            raise LowLatError("Cache line: 32, 64 or 128 bytes.")
    for k, name, lo, hi, w in (("target_q", "Percentile of your target", 50, 99.999, False), ("target_us", "Target (µs)", 0, 1e9, False),
                               ("interval_us", "Send interval (µs)", 0, 1e9, False), ("tolerance", "Tolerance (%)", 1, 200, False),
                               ("runs", "Runs on each side", 1, 9, True)):
        if g(k):
            c[k] = _num(f[k], name, lo, hi, w)
    for k in ("bench_cmd", "build_cmd", "out_file", "runner"):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:400]
    if "pin_cpu" in f:
        c["pin_cpu"] = str(f["pin_cpu"]).lower() in ("1", "true", "yes", "on")
    probe = {**settings(tenant), **c}
    if probe.get("bench_cmd"):
        try:
            _ci(probe)
        except CI.CiError as e:
            raise LowLatError(str(e))
    with session() as s:
        r = s.get(LSettings, tenant)
        if r is None:
            r = LSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _ci(st: dict[str, Any]) -> dict[str, Any]:
    return CI.workflow(bench_cmd=st["bench_cmd"], build_cmd=st["build_cmd"], out_file=st["out_file"], unit=st["unit"], quantile=st["target_q"],
                       tolerance=st["tolerance"], runs=st["runs"], runner=st["runner"], pin_cpu=st["pin_cpu"])


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "latency":
        r0 = (res.get("runs") or [{}])[0]
        q = r0.get("q") or {}
        c = (res.get("compare") or [{}])[-1] if res.get("compare") else {}
        b.update(runs=len(res.get("runs") or []), p50=q.get("50"), p99=q.get("99"), p999=q.get("99.9"), count=r0.get("count"),
                 change=((c.get("q") or {}).get("99") or {}).get("change"), verdict=c.get("verdict"),
                 target_ok=(r0.get("target") or {}).get("ok"))
    elif kind == "budget":
        b.update(p50=(res.get("q") or {}).get("50"), p99=(res.get("q") or {}).get("99"), stages=len(res.get("stages") or []),
                 target_ok=(res.get("target") or {}).get("ok"))
    elif kind == "code":
        b.update(lang=res.get("lang_name"), lines=res.get("lines"))
    elif kind == "layout":
        b.update(structs=len(res.get("structs") or []), size=((res.get("structs") or [{}])[0]).get("size"),
                 sharing=sum(1 for i in res.get("issues") or [] if "false sharing" in i.get("text", "")))
    elif kind == "profile":
        b.update(kind=res.get("kind"), top=((res.get("top") or [{}])[0]).get("sym") if res.get("top") else None,
                 cat=((res.get("cats") or [{}])[0]).get("label") if res.get("cats") else None)
    elif kind == "tuning":
        b.update(seen=len(res.get("seen") or []))
    return b


def _view(r: LItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text if len(r.text or "") <= 400_000 else (r.text[:400_000] + "\n... (cut here; the whole text was read)"),
                 inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(LItem).where(LItem.tenant_id == tenant)
        if kind:
            q = q.where(LItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(LItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> LItem:
    r = s.get(LItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(LItem).where(LItem.tenant_id == tenant, LItem.number == str(iid or "").upper())).first()
        if r is None:
            raise LowLatError("Not found.")
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
            raise LowLatError("The settings must be JSON.")
        if isinstance(d, dict):
            return d
    return {}


def _run(kind: str, text: str, inp: dict[str, Any], st: dict[str, Any]) -> tuple[dict[str, Any], str]:
    g = lambda k, d=None: inp.get(k) if inp.get(k) not in (None, "") else d   # noqa: E731
    if kind == "latency":
        res = LA.analyse(text, str(g("unit", st["unit"])), g("interval_us", st["interval_us"]), g("target_q", st["target_q"]), g("target_us", st["target_us"]))
        names = [r["name"] for r in res["runs"]]
        return res, ("Latency: " + " vs ".join(names[:3]) if len(names) > 1 else f"Latency ({res['runs'][0]['tool']})")[:120]
    if kind == "budget":
        res = BU.budget(text, str(g("unit", st["budget_unit"])), g("target_us", st["target_us"]), g("target_q", st["target_q"]))
        return res, f"Budget: {len(res['stages'])} stages"
    if kind == "code":
        res = HP.check(text, str(g("lang", "")))
        return res, f"Hot path ({res['lang_name']}, {res['lines']} lines)"
    if kind == "layout":
        res = LY.analyse(text, str(g("abi", st["abi"])), int(g("line", st["line"])))
        return res, "Layout: " + ", ".join(s["name"] for s in res["structs"][:3])
    if kind == "profile":
        res = PR.analyse(text)
        return res, f"Profile ({res['kind']})"
    res = TU.check(text)
    return res, f"Host tuning ({len(res['seen'])} parts read)"


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise LowLatError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise LowLatError("That is longer than 40,000,000 characters.")
    if not text.strip():
        raise LowLatError({"latency": "Paste the latency samples first: one per line, HdrHistogram / wrk2 output, or lines like 'p99: 1.2 ms'.",
                           "budget": "List the stages first: stage, name, p50, p99 - one per line.",
                           "code": "Paste the hot-path code first.", "layout": "Paste the struct first.",
                           "profile": "Paste perf report --stdio, folded stacks or perf stat output first.",
                           "tuning": "Paste the host's outputs first: cat /proc/cmdline, sysctl -a, lscpu, ethtool -c <nic> ..."}[kind])
    try:
        res, auto = _run(kind, text, inp, st)
    except ERRORS as e:
        raise LowLatError(str(e))
    with session() as s:
        n = len(s.scalars(select(LItem.id).where(LItem.tenant_id == tenant, LItem.kind == kind)).all()) + 1
        r = LItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(LItem.id).where(LItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(LItem).where(LItem.tenant_id == tenant).order_by(LItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise LowLatError("Status: open | fixed | ignored")
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
    if not st.get("bench_cmd"):
        return {"missing": True, "say": "Set the command that runs your benchmark in Settings first (it writes one latency per line to a file)."}
    try:
        return _ci(st)
    except CI.CiError as e:
        raise LowLatError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "langs": sorted(HP.LANGS.values()), "rules": len(HP.R), "units": list(UNITS),
            "notes": "Everything is worked out in code. Fixes and workflows are text you apply yourself; Hoola runs nothing on your machines."}
