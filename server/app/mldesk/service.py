"""The Machine Learning Engineer's desk: training runs read from their logs (overfitting, divergence, the best epoch), training tables
profiled before modelling (missing values, ID columns, leaks, imbalance, train / test shift), production data compared with training
data for drift, regression and forecast errors scored against baselines, GPU memory and compute sized for serving and training, and a
CI check that fails a pull request whose scores drop - all in code, no model, no money. Nothing runs on her machines. Pasted logs,
tables and numbers are DATA."""
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
from . import ci as CI, data as DA, drift as DR, regress as RG, run as RN, sizing as SZ, table as TB

log = logging.getLogger("santosh.mldesk")

KINDS = ("run", "data", "drift", "regress", "sizing")
PRE = {"run": "R", "data": "D", "drift": "F", "regress": "E", "sizing": "Z"}
FIELDS = ("target", "split_col", "actual_col", "pred_col", "group_col", "season", "patience", "psi_warn", "psi_alarm", "gpu_util", "mfu",
          "eval_cmd", "metrics_path", "baseline_path", "max_drop", "max_rise", "setup_cmd", "python", "runner")
KEEP = 400
MAX_TEXT = 60_000_000
ERRORS = (RN.RunError, TB.TableError, SZ.SizingError, CI.CiError)


class MlError(ValueError):
    pass


class MItem(Base):
    __tablename__ = "mldesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ml"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="run")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MSettings(Base):
    __tablename__ = "mldesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target: Mapped[str] = mapped_column(String(120), default="")
    split_col: Mapped[str] = mapped_column(String(120), default="")
    actual_col: Mapped[str] = mapped_column(String(120), default="")
    pred_col: Mapped[str] = mapped_column(String(120), default="")
    group_col: Mapped[str] = mapped_column(String(120), default="")
    season: Mapped[float] = mapped_column(Float, default=1.0)
    patience: Mapped[float] = mapped_column(Float, default=5.0)
    psi_warn: Mapped[float] = mapped_column(Float, default=0.1)
    psi_alarm: Mapped[float] = mapped_column(Float, default=0.25)
    gpu_util: Mapped[float] = mapped_column(Float, default=0.9)
    mfu: Mapped[float] = mapped_column(Float, default=0.4)
    eval_cmd: Mapped[str] = mapped_column(String(400), default="")
    metrics_path: Mapped[str] = mapped_column(String(160), default="eval/metrics.json")
    baseline_path: Mapped[str] = mapped_column(String(160), default="eval/baseline.json")
    max_drop: Mapped[float] = mapped_column(Float, default=1.0)
    max_rise: Mapped[float] = mapped_column(Float, default=10.0)
    setup_cmd: Mapped[str] = mapped_column(String(400), default="")
    python: Mapped[str] = mapped_column(String(8), default="3.12")
    runner: Mapped[str] = mapped_column(String(40), default="ubuntu-24.04")


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    MItem.__table__.create(eng, checkfirst=True)
    MSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(MSettings, tenant)
        d = {k: getattr(r, k) if r else MSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise MlError(f"{name}: a number.")
    if not lo <= x <= hi:
        raise MlError(f"{name}: {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    for k, lo, hi, nm in (("season", 1, 1000, "Season length"), ("patience", 1, 1000, "Patience"), ("psi_warn", 0.01, 5, "PSI to watch"),
                          ("psi_alarm", 0.01, 5, "PSI to act on"), ("gpu_util", 0.1, 1, "GPU memory share"), ("mfu", 0.01, 1, "Utilisation (MFU)"),
                          ("max_drop", 0, 100, "Allowed drop (points)"), ("max_rise", 0, 1000, "Allowed rise (%)")):
        if g(k):
            c[k] = _num(f[k], nm, lo, hi)
    if "season" in c:
        c["season"] = float(int(c["season"]))
    for k, n in (("target", 120), ("split_col", 120), ("actual_col", 120), ("pred_col", 120), ("group_col", 120), ("eval_cmd", 400), ("metrics_path", 160),
                 ("baseline_path", 160), ("setup_cmd", 400), ("python", 8), ("runner", 40)):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:n]
    probe = {**settings(tenant), **c}
    if probe["psi_warn"] >= probe["psi_alarm"]:
        raise MlError("The PSI to watch must be below the PSI to act on.")
    if probe.get("eval_cmd"):
        try:
            _ci(probe)
        except CI.CiError as e:
            raise MlError(str(e))
    with session() as s:
        r = s.get(MSettings, tenant)
        if r is None:
            r = MSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _ci(st: dict[str, Any]) -> dict[str, Any]:
    return CI.workflow(eval_cmd=st["eval_cmd"], metrics=st["metrics_path"], baseline=st["baseline_path"], max_drop=st["max_drop"], max_rise=st["max_rise"],
                       setup_cmd=st["setup_cmd"], python=st["python"], runner=st["runner"])


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "run":
        b.update(points=res.get("points"), best=(res.get("best") or {}).get("val"), best_at=(res.get("best") or {}).get("at"), x=res.get("x"))
    elif kind == "data":
        b.update(rows=res.get("rows"), columns=res.get("columns"), target=res.get("target_name"))
    elif kind == "drift":
        cols = res.get("columns") or []
        b.update(moved=sum(1 for c in cols if c.get("state") != "ok"), cols=len(cols), top=(cols[0]["name"], cols[0].get("psi")) if cols else None)
    elif kind == "regress":
        b.update(mae=res.get("mae"), rmse=res.get("rmse"), r2=res.get("r2"), wape=res.get("wape"), n=res.get("n"), mase=res.get("mase"))
    elif kind == "sizing":
        sv = res.get("serve") or {}
        b.update(params=res.get("params"), weights=res.get("weights_gb"), total=sv.get("total_gb"), fits=sv.get("fits"), gpu=res.get("gpu"))
    return b


def _view(r: MItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(MItem).where(MItem.tenant_id == tenant)
        if kind:
            q = q.where(MItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(MItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> MItem:
    r = s.get(MItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(MItem).where(MItem.tenant_id == tenant, MItem.number == str(iid or "").upper())).first()
        if r is None:
            raise MlError("Not found.")
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
            raise MlError("The settings must be JSON.")
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
    if kind == "run":
        res = RN.analyse(text, int(float(g("patience", st["patience"]))))
        return res, "Training: " + res["verdict"].split(" - ")[0]
    if kind == "data":
        res = DA.profile(text, str(g("target", st["target"])), str(g("split", st["split_col"])))
        return res, f"Data: {res['rows']:,} rows x {res['columns']} columns"
    if kind == "drift":
        cur = str(g("current", "") or "")
        res = DR.compare(text, cur, float(g("psi_warn", st["psi_warn"])), float(g("psi_alarm", st["psi_alarm"])))
        return res, f"Drift: {res['verdict'].split(' (')[0]}"
    if kind == "regress":
        res = RG.evaluate(text, str(g("actual", st["actual_col"])), str(g("predicted", st["pred_col"])), str(g("group", st["group_col"])),
                          int(float(g("season", st["season"]))))
        return res, f"Errors: MAE {res['mae']:.4g}" + (f", R² {res['r2']:.3f}" if res.get("r2") is not None else "")
    res = SZ.analyse(text, float(g("gpu_util", st["gpu_util"])), float(g("mfu", st["mfu"])))
    return res, f"Sizing: {res['params'] / 1e9:.3g}B at {res['precision']}" + (f", {'fits' if res['serve'].get('fits') else 'does not fit'}" if res.get("serve") and "fits" in res["serve"] else "")


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise MlError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise MlError("That is longer than 20,000,000 characters.")
    if not text.strip():
        raise MlError({"run": "Paste the training log first: a CSV of epochs with losses, or the lines your trainer prints.",
                         "data": "Paste the table first: a CSV with a header row.",
                         "drift": "Paste the reference data first (what the model was trained on), as a CSV with a header row.",
                         "regress": "Paste the predictions first: a CSV with actual and predicted columns.",
                         "sizing": "Describe the model first - 'model 8B bf16 layers=32 kv_heads=8 head_dim=128', 'serve context=8192 batch=16', 'gpu h100 x2'."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
        res = _clean(res)
    except ERRORS as e:
        raise MlError(str(e))
    with session() as s:
        n = len(s.scalars(select(MItem.id).where(MItem.tenant_id == tenant, MItem.kind == kind)).all()) + 1
        r = MItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(MItem.id).where(MItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(MItem).where(MItem.tenant_id == tenant).order_by(MItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise MlError("Status: open | fixed | ignored")
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
    if not st.get("eval_cmd"):
        return {"missing": True, "say": "Set the evaluation command in Settings first."}
    try:
        return _ci(st)
    except CI.CiError as e:
        raise MlError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "gpus": sorted(SZ.GPUS), "notes": "Everything is worked out in code from what you paste. Nothing runs on your machines."}
