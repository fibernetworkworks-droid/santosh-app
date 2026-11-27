"""The Graphics Engine Programmer's engine: shaders kept with versions, checked in code and run in HER browser (WebGL2) with a golden
picture to test later versions against; reference renders made by Hoola's own CPU path tracer; two images compared (PSNR, SSIM, heat
map); GPU validation output (Vulkan / D3D12 / Metal / OpenGL) grouped and explained; frame times and GPU passes read. Everything here
is code - no model, no money - and nothing is run on her machines or sent anywhere. Pasted logs and shaders are DATA."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import compare as CMP, frames, pathtrace, shaders, vklog

log = logging.getLogger("santosh.gfxdesk")

KINDS = ("shader", "compare", "vklog", "frames", "passes")
APIS = ("vulkan", "d3d12", "metal", "opengl", "webgpu")
MAX_TEXT = 2_000_000
MAX_VERSIONS = 30
KEEP = 300
PRE = {"shader": "S", "compare": "I", "vklog": "V", "frames": "F", "passes": "G"}


class GfxError(ValueError):
    pass


class GItem(Base):
    __tablename__ = "gfxdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(10), default="shader")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    versions: Mapped[list] = mapped_column(JSON, default=list)       # shader: [{n, src, at, note}]
    golden: Mapped[dict] = mapped_column(JSON, default=dict)         # shader: {png, version, time, at}
    status: Mapped[str] = mapped_column(String(12), default="open")   # open | fixed | ignored
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GSettings(Base):
    __tablename__ = "gfxdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    api: Mapped[str] = mapped_column(String(10), default="vulkan")
    engine: Mapped[str] = mapped_column(String(80), default="")
    gpu: Mapped[str] = mapped_column(String(120), default="")
    target_fps: Mapped[float] = mapped_column(Float, default=60.0)
    psnr_min: Mapped[float] = mapped_column(Float, default=35.0)
    ssim_min: Mapped[float] = mapped_column(Float, default=0.98)
    diff_threshold: Mapped[float] = mapped_column(Float, default=0.05)
    blur: Mapped[int] = mapped_column(Integer, default=0)


FIELDS = ("api", "engine", "gpu", "target_fps", "psnr_min", "ssim_min", "diff_threshold", "blur")
_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    GItem.__table__.create(eng, checkfirst=True)
    GSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


# ---------------------------------------------------------------- settings
def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(GSettings, tenant)
        d = {k: getattr(r, k) if r else GSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _float(v: Any, lo: float, hi: float, what: str) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise GfxError(f"{what}: a number from {lo:g} to {hi:g}.")
    if not lo <= x <= hi:
        raise GfxError(f"{what}: a number from {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    clean: dict[str, Any] = {}
    if f.get("api") not in (None, ""):
        if f["api"] not in APIS:
            raise GfxError("API: " + " | ".join(APIS))
        clean["api"] = f["api"]
    for k in ("engine", "gpu"):
        if f.get(k) is not None:
            clean[k] = str(f[k])[:120]
    lim = {"target_fps": (10, 1000, "Target FPS"), "psnr_min": (10, 80, "PSNR limit"), "ssim_min": (0.5, 1, "SSIM limit"),
           "diff_threshold": (0.001, 0.5, "Pixel difference"), "blur": (0, 8, "Blur")}
    for k, (lo, hi, what) in lim.items():
        if f.get(k) not in (None, ""):
            clean[k] = _float(f[k], lo, hi, what)
            if k == "blur":
                clean[k] = int(clean[k])
    with session() as s:
        r = s.get(GSettings, tenant)
        if r is None:
            r = GSettings(tenant_id=tenant)
            s.add(r)
        for k, v in clean.items():
            setattr(r, k, v)
    return settings(tenant)


# ---------------------------------------------------------------- items
def _brief(kind: str, res: dict[str, Any], r: GItem | None = None) -> dict[str, Any]:
    if kind == "shader":
        c = res.get("counts") or {}
        return {"lang": res.get("lang", ""), "errors": c.get("error", 0), "warnings": c.get("warning", 0), "versions": len(r.versions or []) if r else 0,
                "golden": bool(r and r.golden), "test": res.get("test") or "", "bad": bool(c.get("error")) or res.get("test") == "failed"}
    if kind == "compare":
        return {"psnr": res.get("psnr"), "ssim": res.get("ssim"), "passed": res.get("passed", False), "bad": not res.get("passed", False)}
    if kind == "vklog":
        return {"errors": res.get("errors", 0), "warnings": res.get("warnings", 0), "kinds": res.get("kinds", 0), "apis": res.get("apis", []),
                "bad": bool(res.get("errors"))}
    if kind == "frames":
        return {"avg_fps": res.get("avg_fps"), "low1_fps": res.get("low1_fps"), "stutters": res.get("stutters", 0), "bound": res.get("bound", ""),
                "bad": (res.get("over_budget") or 0) > 0.05 or bool(res.get("stutters"))}
    if kind == "passes":
        return {"total_ms": res.get("total_ms"), "over": res.get("over", False), "biggest": ((res.get("passes") or [{}])[0]).get("name", ""),
                "bad": res.get("over", False)}
    return {}


def _view(r: GItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {}, r)}
    if full:
        d.update(result=r.result or {}, text=r.text if r.kind != "shader" else "",
                 versions=[{k: v for k, v in x.items()} for x in (r.versions or [])], golden=r.golden or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 120) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(GItem).where(GItem.tenant_id == tenant)
        if kind:
            q = q.where(GItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(GItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> GItem:
    r = s.get(GItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(GItem).where(GItem.tenant_id == tenant, GItem.number == str(iid or "").upper())).first()
        if r is None:
            raise GfxError("Not found.")
    return r


def get(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        return _view(_row(s, tenant, iid), True)


def _num(s, tenant: str, kind: str) -> str:
    n = len(s.scalars(select(GItem.id).where(GItem.tenant_id == tenant, GItem.kind == kind)).all()) + 1
    return f"{PRE[kind]}-{n:04d}"


def _text(t: Any) -> str:
    t = str(t or "")
    if not t.strip():
        raise GfxError("Paste the text (or drop the file) first.")
    if len(t) > MAX_TEXT:
        raise GfxError("That is longer than 2,000,000 characters - keep the part around the problem.")
    return t


def _save(tenant: str, kind: str, title: str, text: str, res: dict[str, Any], **extra: Any) -> dict[str, Any]:
    with session() as s:
        r = GItem(tenant_id=tenant, number=_num(s, tenant, kind), kind=kind, title=str(title or "")[:200], text=text, result=res, **extra)
        s.add(r)
        s.flush()
        iid = r.id
        n = len(s.scalars(select(GItem.id).where(GItem.tenant_id == tenant)).all())
        if n > KEEP:
            for x in s.scalars(select(GItem).where(GItem.tenant_id == tenant).order_by(GItem.updated_at.asc()).limit(n - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def add(tenant: str, kind: str, text: Any = "", title: str = "", **kw: Any) -> dict[str, Any]:
    """vklog | frames | passes from pasted text; compare from two images; shader = new_shader."""
    _tables()
    if kind not in KINDS:
        raise GfxError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    if kind == "shader":
        return new_shader(tenant, kw.get("src") or text, title, kw.get("lang", ""), kw.get("stage", "fragment"))
    if kind == "compare":
        return compare(tenant, kw.get("a"), kw.get("b"), title, kw.get("blur"), kw.get("a_name", ""), kw.get("b_name", ""))
    text = _text(text)
    if kind == "vklog":
        res = vklog.parse(text)
        auto = f"Validation: {res['errors']} error(s), {res['warnings']} warning(s)" if res["messages"] else "Validation log (no messages)"
    elif kind == "frames":
        res = frames.analyse(text, st["target_fps"])
        if not res.get("ok"):
            raise GfxError(res.get("error") or "No frame times.")
        auto = f"Frames: {res['avg_fps']} FPS, 1% low {res['low1_fps']}"
    else:
        res = frames.passes(text, st["target_fps"])
        if not res.get("ok"):
            raise GfxError(res.get("error") or "No passes.")
        auto = f"GPU passes: {res['total_ms']} ms"
    return _save(tenant, kind, (str(title or "").strip() or auto), text, res)


def compare(tenant: str, a: Any, b: Any, title: str = "", blur: Any = None, a_name: str = "", b_name: str = "") -> dict[str, Any]:
    _tables()
    st = settings(tenant)
    if not a or not b:
        raise GfxError("Add both images: the reference and your render.")
    if isinstance(a, str) and a.startswith("ref:"):
        a = reference(a[4:])["png"]
        a_name = a_name or "Hoola reference"
    try:
        res = CMP.compare(a, b, st["diff_threshold"], st["blur"] if blur in (None, "") else int(blur), st["psnr_min"], st["ssim_min"])
    except CMP.CompareError as e:
        raise GfxError(str(e))
    if isinstance(a, str) and isinstance(b, str) and len(a) + len(b) < 3_500_000:
        res["a"], res["b"] = a, b
    res["a_name"], res["b_name"] = str(a_name or "Reference")[:80], str(b_name or "Your render")[:80]
    auto = f"{res['a_name']} vs {res['b_name']}"
    return _save(tenant, "compare", (str(title or "").strip() or auto), "", res, status="fixed" if res["passed"] else "open")


# ---------------------------------------------------------------- shaders
def new_shader(tenant: str, src: Any, title: str = "", lang: str = "", stage: str = "fragment") -> dict[str, Any]:
    _tables()
    src = str(src or "") or shaders.STARTER
    if len(src) > shaders.MAX:
        raise GfxError("A shader may be at most 200,000 characters.")
    res = shaders.lint(src, lang, stage)
    return _save(tenant, "shader", (str(title or "").strip() or "Shader"), "", res,
                 versions=[{"n": 1, "src": src, "at": now().isoformat(), "note": "First version"}], golden={})


def save_shader(tenant: str, iid: str, src: Any, note: str = "", lang: str = "", stage: str = "") -> dict[str, Any]:
    _tables()
    src = str(src or "")
    if not src.strip():
        raise GfxError("The shader is empty.")
    if len(src) > shaders.MAX:
        raise GfxError("A shader may be at most 200,000 characters.")
    with session() as s:
        r = _row(s, tenant, iid)
        if r.kind != "shader":
            raise GfxError("Not a shader.")
        vs = [dict(v) for v in (r.versions or [])]
        if vs and vs[-1]["src"] == src:
            return _view(r, True)
        n = (vs[-1]["n"] + 1) if vs else 1
        vs.append({"n": n, "src": src, "at": now().isoformat(), "note": str(note or "")[:200]})
        r.versions = vs[-MAX_VERSIONS:]
        old = dict(r.result or {})
        res = shaders.lint(src, lang or old.get("lang", ""), stage or old.get("stage", "fragment"))
        if r.golden:
            res["test"] = "not run"
        r.result, r.updated_at = res, now()
        iid = r.id
    return get(tenant, iid)


def run_result(tenant: str, iid: str, ok: bool, log_text: str = "", png: str = "", version: int | None = None, time: float = 1.0,
               golden: bool = False) -> dict[str, Any]:
    """What her browser said: the WebGL2 compile log, and (when it rendered) a picture at a fixed time. With golden=true the
    picture becomes the golden one; otherwise it is compared with the golden one."""
    _tables()
    st = settings(tenant)
    with session() as s:
        r = _row(s, tenant, iid)
        if r.kind != "shader":
            raise GfxError("Not a shader.")
        res = dict(r.result or {})
        res["compile"] = {"ok": bool(ok), "log": str(log_text or "")[:20_000], "version": version, "at": now().isoformat(),
                          "errors": _gl_errors(str(log_text or ""))}
        if ok and png:
            if golden:
                r.golden = {"png": png, "version": version, "time": float(time), "at": now().isoformat()}
                res["test"] = "golden set"
                res.pop("diff", None)
            elif r.golden:
                try:
                    c = CMP.compare(r.golden["png"], png, st["diff_threshold"], 0, st["psnr_min"], st["ssim_min"])
                except CMP.CompareError as e:
                    raise GfxError(str(e))
                res["diff"] = {k: c[k] for k in ("psnr", "ssim", "mean_error", "max_error", "over_share", "passed", "heatmap", "verdict", "identical")}
                res["diff"]["png"] = png
                res["test"] = "passed" if c["passed"] else "failed"
        elif not ok:
            res["test"] = "does not compile" if r.golden else res.get("test", "")
        r.result, r.updated_at = res, now()
        iid = r.id
    return get(tenant, iid)


def _gl_errors(log_text: str) -> list[dict[str, Any]]:
    out = []
    for m in re.finditer(r"(ERROR|WARNING):\s*(\d+):(\d+):\s*(.+)", log_text):
        out.append({"sev": m.group(1).lower(), "line": int(m.group(3)), "text": m.group(4).strip()[:300]})
    return out[:100]


# ---------------------------------------------------------------- the rest
def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise GfxError("Status: open | fixed | ignored")
    _tables()
    with session() as s:
        r = _row(s, tenant, iid)
        r.status, r.updated_at = status, now()
        if note:
            r.note = str(note)[:1000]
        iid = r.id
    return get(tenant, iid)


def rename(tenant: str, iid: str, title: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = _row(s, tenant, iid)
        r.title = str(title or "").strip()[:200] or r.title
        iid = r.id
    return get(tenant, iid)


def delete(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        s.delete(_row(s, tenant, iid))
    return {"ok": True, "say": "Removed."}


_REF: dict[str, dict[str, Any]] = {}


def reference(name: str) -> dict[str, Any]:
    """One of Hoola's reference scenes rendered on the server's CPU (fixed seed, so the same picture every time). Kept in memory."""
    if name not in pathtrace.SCENES:
        raise GfxError("Scene: " + " | ".join(pathtrace.SCENES))
    if name not in _REF:
        sc = pathtrace.SCENES[name]
        r = pathtrace.render(sc["scene"])
        d = {k: v for k, v in r.items() if k != "linear"}
        if name == "furnace":
            d["furnace"] = pathtrace.furnace_check(r, sc["scene"]["sky"]["top"][0])
        _REF[name] = {"name": name, "title": sc["title"], "about": sc["about"], "scene": sc["scene"], **d}
    return _REF[name]


def scenes() -> list[dict[str, Any]]:
    return [{"name": k, "title": v["title"], "about": v["about"], "width": v["scene"]["width"], "height": v["scene"]["height"],
             "samples": v["scene"]["samples"], "made": k in _REF} for k, v in pathtrace.SCENES.items()]


def render_scene(scene: dict[str, Any]) -> dict[str, Any]:
    try:
        r = pathtrace.render(scene)
    except pathtrace.SceneError as e:
        raise GfxError(str(e))
    return {k: v for k, v in r.items() if k != "linear"}


def health() -> dict[str, Any]:
    return {"scenes": scenes(), "apis": list(APIS), "kinds": list(KINDS), "langs": list(shaders.LANGS)}
