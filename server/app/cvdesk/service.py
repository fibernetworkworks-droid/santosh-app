"""The Computer Vision Engineer's desk: object detectors scored the COCO way (mAP, per class, by size, the errors), classifiers scored
(per-class F1, confusion, calibration, ROC), labelled datasets checked before training (bad boxes, duplicates, leaks between splits,
imbalance), cameras and lenses worked out (field of view, pixels on target, the lens needed, blur, depth of field, stereo error,
calibration files), pipeline speed against the frame rate, and a CI check that fails a pull request whose scores drop - all in code,
no model, no money. Nothing runs on her cameras or machines. Pasted labels, predictions and logs are DATA."""
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
from . import camera as CA, ci as CI, classify as CL, dataset as DS, detect as DT, pipeline as PL

log = logging.getLogger("santosh.cvdesk")

KINDS = ("detect", "classify", "dataset", "camera", "pipeline")
PRE = {"detect": "D", "classify": "C", "dataset": "L", "camera": "K", "pipeline": "P"}
FIELDS = ("box_fmt", "score_thr", "iou_thr", "class_names", "img_size", "min_px", "target_fps", "eval_cmd", "metrics_path", "baseline_path",
          "max_drop", "max_rise", "setup_cmd", "python", "runner")
KEEP = 400
MAX_TEXT = 60_000_000
ERRORS = (DT.DetectError, CL.ClassifyError, DS.DatasetError, CA.CameraError, PL.PipelineError, CI.CiError)


class CvError(ValueError):
    pass


class VItem(Base):
    __tablename__ = "cvdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="detect")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VSettings(Base):
    __tablename__ = "cvdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    box_fmt: Mapped[str] = mapped_column(String(6), default="xyxy")
    score_thr: Mapped[float] = mapped_column(Float, default=0.25)
    iou_thr: Mapped[float] = mapped_column(Float, default=0.5)
    class_names: Mapped[str] = mapped_column(Text, default="")
    img_size: Mapped[str] = mapped_column(String(20), default="")
    min_px: Mapped[float] = mapped_column(Float, default=20.0)
    target_fps: Mapped[float] = mapped_column(Float, default=0.0)
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
    VItem.__table__.create(eng, checkfirst=True)
    VSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(VSettings, tenant)
        d = {k: getattr(r, k) if r else VSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise CvError(f"{name}: a number.")
    if not lo <= x <= hi:
        raise CvError(f"{name}: {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    if g("box_fmt"):
        if f["box_fmt"] not in ("xyxy", "xywh"):
            raise CvError("Box format: xyxy (x1 y1 x2 y2) or xywh (x y width height, as COCO).")
        c["box_fmt"] = f["box_fmt"]
    for k, lo, hi, nm in (("score_thr", 0, 1, "Score threshold"), ("iou_thr", 0.05, 0.95, "IoU threshold"), ("min_px", 1, 1000, "Smallest object (px)"),
                          ("target_fps", 0, 10000, "Target frame rate"), ("max_drop", 0, 100, "Allowed drop (points)"), ("max_rise", 0, 1000, "Allowed rise (%)")):
        if g(k):
            c[k] = _num(f[k], nm, lo, hi)
    if f.get("img_size") is not None:
        v = str(f["img_size"]).strip()
        if v and not re.fullmatch(r"\d+\s*[x×]\s*\d+", v):
            raise CvError("Image size: width x height, e.g. 1920x1080.")
        c["img_size"] = v[:20]
    if f.get("class_names") is not None:
        c["class_names"] = ", ".join(x.strip() for x in re.split(r"[,\n]", str(f["class_names"])) if x.strip())[:8000]
    for k, n in (("eval_cmd", 400), ("metrics_path", 160), ("baseline_path", 160), ("setup_cmd", 400), ("python", 8), ("runner", 40)):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:n]
    probe = {**settings(tenant), **c}
    if probe.get("eval_cmd"):
        try:
            _ci(probe)
        except CI.CiError as e:
            raise CvError(str(e))
    with session() as s:
        r = s.get(VSettings, tenant)
        if r is None:
            r = VSettings(tenant_id=tenant)
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
    if kind == "detect":
        b.update(map=res.get("map"), map50=res.get("map50"), images=res.get("images"), classes=len([c for c in res.get("classes") or [] if c.get("gt")]),
                 f1=(res.get("at") or {}).get("f1"))
    elif kind == "classify":
        b.update(acc=res.get("accuracy"), f1=res.get("macro_f1"), n=res.get("n"), auc=(res.get("binary") or {}).get("auc"))
    elif kind == "dataset":
        b.update(images=res.get("images"), boxes=res.get("boxes"), classes=len(res.get("classes") or []), fmt=res.get("format"))
    elif kind == "camera":
        cam = res.get("camera") or {}
        b.update(hfov=cam.get("hfov"), W=cam.get("W"), H=cam.get("H"), answers=len(res.get("answers") or []), calib=bool(res.get("calib")))
    elif kind == "pipeline":
        b.update(fps=res.get("par_fps"), latency=res.get("latency"), p99=(res.get("samples") or {}).get("p99"))
    return b


def _view(r: VItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(VItem).where(VItem.tenant_id == tenant)
        if kind:
            q = q.where(VItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(VItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> VItem:
    r = s.get(VItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(VItem).where(VItem.tenant_id == tenant, VItem.number == str(iid or "").upper())).first()
        if r is None:
            raise CvError("Not found.")
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
            raise CvError("The settings must be JSON.")
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
    if kind == "detect":
        pred = str(g("pred", "") or "")
        if not pred.strip():
            raise CvError("Paste the model's predictions too (one per line: image class score x1 y1 x2 y2, or a COCO results list).")
        res = DT.evaluate(text, pred, str(g("box_fmt", st["box_fmt"])), float(g("score_thr", st["score_thr"])), float(g("iou_thr", st["iou_thr"])),
                          str(g("names", st["class_names"])))
        pc = lambda v: "—" if v is None else f"{v * 100:.1f}"   # noqa: E731
        return res, f"Detection: mAP {pc(res['map'])}, AP50 {pc(res['map50'])}"
    if kind == "classify":
        res = CL.evaluate(text, str(g("positive", "")), str(g("need", "")))
        return res, f"Classification: {res['accuracy'] * 100:.1f}% accurate, macro F1 {res['macro_f1']:.3f}"
    if kind == "dataset":
        res = DS.check(text, str(g("names", st["class_names"])), str(g("img_size", st["img_size"])), float(g("min_px", 8)))
        return res, f"Dataset: {res['images']:,} images, {res['boxes']:,} boxes ({res['format']})"
    if kind == "camera":
        res = CA.analyse(text, str(g("ask", "")), float(g("min_px", st["min_px"])))
        cam = res["camera"]
        return res, f"Camera: {cam['W']}x{cam['H']}" + (f", {cam['hfov']:.0f}° wide" if cam.get("hfov") else "")
    res = PL.analyse(text, g("target_fps", st["target_fps"] or ""), float(g("min_px", st["min_px"])))
    return res, ("Speed: " + res["verdict"].split(";")[0])[:120]


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise CvError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise CvError("That is longer than 20,000,000 characters.")
    if not text.strip():
        raise CvError({"detect": "Paste the ground truth first: one box per line (image class x1 y1 x2 y2) or a COCO JSON.",
                         "classify": "One image per line first: image, true class, predicted class (and the score).",
                         "dataset": "Paste the labels first: YOLO files under '## path/name.txt' headers, or a COCO JSON.",
                         "camera": "Describe the camera first - 'sensor pixel=2.9um res=1920x1080 lens=6mm' - or paste a calibration file.",
                         "pipeline": "One stage per line first - 'inference 18ms gpu' - or latency samples, one number a line."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
        res = _clean(res)
    except ERRORS as e:
        raise CvError(str(e))
    with session() as s:
        n = len(s.scalars(select(VItem.id).where(VItem.tenant_id == tenant, VItem.kind == kind)).all()) + 1
        r = VItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(VItem.id).where(VItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(VItem).where(VItem.tenant_id == tenant).order_by(VItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise CvError("Status: open | fixed | ignored")
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
        raise CvError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "notes": "Everything is worked out in code from what you paste. Nothing runs on your cameras or your machines."}
