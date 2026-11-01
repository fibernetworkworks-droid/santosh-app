"""v0.357 ENGINEERING DESK service: CAD projects for the hired CAD Engineer.

Flow (background thread, one job at a time): her words -> Opus writes a CadQuery script -> guard.py -> the locked runner
(sandbox.py: no network, no secrets, limits) builds the solid and exports STEP / STL / mesh -> checks (valid solid, one
body, volume, the size the model promised vs the real box) -> up to 2 fixes from the real error -> views + drawing PDF
(render.py) -> a version on her desk + one chat line. Nothing here spends money except model calls (feature 'eng' in AI
kharcha), and nothing is sent anywhere."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session
from . import ai, guard, render, sandbox

log = logging.getLogger("santosh.engineering")
HIRE_KEY = "cad"
MAX_FIXES = 3
# v0.362 g / cm3 (common handbook values) for mass; the model names one of these keys
DENSITY = {"steel": 7.85, "stainless": 8.0, "aluminium": 2.70, "aluminum": 2.70, "brass": 8.5, "copper": 8.96,
           "cast iron": 7.2, "titanium": 4.43, "abs": 1.04, "pla": 1.24, "petg": 1.27, "nylon": 1.14, "pom": 1.41,
           "acrylic": 1.18, "polycarbonate": 1.20, "wood": 0.6, "rubber": 1.2}
MAX_IMAGES, MAX_IMAGE_BYTES = 3, 6_000_000
MAX_FILES, MAX_FILE_BYTES = 2, 40_000_000
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="engineering")
_LOCK = threading.Lock()
FILES = ("part.step", "part.stl", "part.3mf", "part.glb", "section.dxf", "drawing.pdf", "iso.png", "front.png", "top.png",
         "right.png", "part.py",
         # v0.365 after-build stage
         "analysis.pdf", "fea_0.png", "fea_1.png", "fea_2.png", "part.nc", "cam.png", "flat.dxf", "flat.png")


class EngError(Exception):
    pass


class EngProject(Base):
    __tablename__ = "eng_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("eng"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    kind: Mapped[str] = mapped_column(String(16), default="cad")
    title: Mapped[str] = mapped_column(String(120), default="")
    brief: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="queued")   # queued|designing|building|checking|drawing|done|failed
    stage: Mapped[str] = mapped_column(String(160), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    pending: Mapped[dict] = mapped_column(JSON, default=dict)            # {mode: new|change, words}
    versions: Mapped[list] = mapped_column(JSON, default=list)
    inputs: Mapped[list | None] = mapped_column(JSON, nullable=True)     # v0.362 [{name, kind: image|cad}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        EngProject.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ---------------------------------------------------------------- folders, signed links
def root() -> Path:
    p = Path(os.environ.get("ENG_DIR", "./data/engineering"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _pdir(tenant: str, pid: str) -> Path:
    return root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / pid


def _sig(pid: str, name: str, exp: int) -> str:
    st = get_settings()
    key = st.secret_key or st.api_key or "hoola-eng"
    return hmac.new(f"eng:{key}".encode(), f"{pid}/{name}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def file_url(pid: str, name: str, days: int = 10) -> str:
    exp = int(time.time()) + days * 86400
    return f"/api/eng/files/{pid}/{name}?exp={exp}&sig={_sig(pid, name, exp)}"


def file_path(pid: str, name: str, exp: int, sig: str) -> Path | None:
    if exp < time.time() or not hmac.compare_digest(_sig(pid, name, exp), sig or ""):
        return None
    if not re.fullmatch(r"v\d{1,3}/[\w\-.]{1,40}", name or "") or ".." in name or name.split("/")[1] not in FILES:
        return None
    ensure_table()
    with session() as s:
        row = s.get(EngProject, pid)
        if row is None:
            return None
        p = _pdir(row.tenant_id, pid) / name
    return p if p.is_file() else None


# ---------------------------------------------------------------- views of a project
def view(r: EngProject) -> dict[str, Any]:
    vs = []
    for v in r.versions or []:
        files = {f: file_url(r.id, f"v{v['n']}/{f}") for f in FILES if f in (v.get("files") or [])}
        vs.append({**{k: v.get(k) for k in ("n", "title", "size", "bbox", "volume_mm3", "checks", "assumed", "notes",
                                            "at", "seconds", "words", "plan", "material", "mass_g", "com", "parts",
                                            "print", "review", "expect", "analysis", "cam", "sheet")}, "files": files})
    return {"id": r.id, "kind": r.kind, "title": r.title or "Part", "brief": r.brief, "status": r.status, "stage": r.stage,
            "error": r.error, "versions": vs, "latest": vs[-1] if vs else None,
            "inputs": [i.get("name") for i in (r.inputs or [])],
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "updated_at": r.updated_at.isoformat() if r.updated_at else ""}


def _publish(r: EngProject) -> None:
    if not r.conversation_id:
        return
    try:
        from ..events import bus
        bus.publish(r.conversation_id, "eng_project", view(r))
    except Exception as e:
        log.info("eng publish: %s", e)


def _save(pid: str, **fields) -> EngProject:
    with session() as s:
        r = s.get(EngProject, pid)
        for k, v in fields.items():
            setattr(r, k, v)
        r.updated_at = now()
        s.flush()
        s.expunge(r)
    _publish(r)
    return r


# ---------------------------------------------------------------- limits + hire gate
def _ist_day(dt_: datetime) -> str:
    if dt_.tzinfo is None:
        dt_ = dt_.replace(tzinfo=timezone.utc)
    return (dt_ + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")


def runs_today(tenant: str) -> int:
    today = _ist_day(datetime.now(timezone.utc))
    with session() as s:
        rows = s.scalars(select(EngProject).where(EngProject.tenant_id == tenant)).all()
        return sum(1 for r in rows for v in (r.versions or []) if str(v.get("day")) == today)


def _gate(tenant: str) -> None:
    from ..employee import hire
    if not hire.is_working(tenant, HIRE_KEY):
        raise EngError("CAD Engineer abhi hired nahi hai (ya paused hai). Employees mein 'Hire CAD Engineer' dabaiye.")
    cap = int(os.environ.get("ENG_DAILY_PARTS", "20") or 0)
    if cap and runs_today(tenant) >= cap:
        raise EngError(f"Aaj ke {cap} CAD parts ho gaye; kal phir banenge.")
    with session() as s:
        busy = s.scalars(select(EngProject.id).where(EngProject.tenant_id == tenant,
                                                     EngProject.status.in_(("queued", "designing", "building", "checking", "drawing")))).first()
    if busy:
        raise EngError("Ek part abhi ban raha hai; uske poora hote hi agla shuru karenge.")


# ---------------------------------------------------------------- public actions
def _clean_inputs(images: list[bytes] | None, files: list[tuple[str, bytes]] | None) -> list[tuple[str, str, bytes]]:
    """[(name, kind, bytes)] after the size / type checks; raises EngError with a plain reason."""
    out: list[tuple[str, str, bytes]] = []
    for i, b in enumerate((images or [])[:MAX_IMAGES]):
        if not b or len(b) > MAX_IMAGE_BYTES:
            raise EngError("Photo 6 MB se chhoti honi chahiye.")
        ext = "png" if b[:4] == b"\x89PNG" else "jpg" if b[:2] == b"\xff\xd8" else "webp" if b[8:12] == b"WEBP" else ""
        if not ext:
            raise EngError("Sketch / photo PNG, JPG ya WEBP ho.")
        out.append((f"sketch_{i + 1}.{ext}", "image", b))
    for name, b in (files or [])[:MAX_FILES]:
        base = re.sub(r"[^\w\-. ]", "_", str(name or "")).strip()[:70] or "file"
        if not re.search(r"\.(step|stp|stl)$", base, re.I):
            raise EngError("CAD file .step / .stp / .stl honi chahiye.")
        if not b or len(b) > MAX_FILE_BYTES:
            raise EngError("CAD file 40 MB se chhoti honi chahiye.")
        head = b[:400].upper()
        if base.lower().endswith((".step", ".stp")) and b"ISO-10303-21" not in head:
            raise EngError(f"{base} asli STEP file nahi lagti.")
        out.append((base, "cad", b))
    return out


def start(tenant: str, conv: str, brief: str, images: list[bytes] | None = None,
          files: list[tuple[str, bytes]] | None = None) -> dict[str, Any]:
    brief = (brief or "").strip()
    if len(brief) < 4:
        raise EngError("Part ke baare mein likhiye: kya hai, size (mm), holes, material.")
    ins = _clean_inputs(images, files)
    ensure_table()
    _gate(tenant)
    with session() as s:
        r = EngProject(tenant_id=tenant, conversation_id=conv or "", brief=brief[:6000], status="queued",
                       stage="Shuru ho raha hai", pending={"mode": "new"},
                       inputs=[{"name": n, "kind": k} for n, k, _ in ins])
        s.add(r)
        s.flush()
        pid = r.id
    idir = _pdir(tenant, pid) / "inputs"
    for n, _k, b in ins:
        idir.mkdir(parents=True, exist_ok=True)
        (idir / n).write_bytes(b)
    _submit(pid)
    return get(tenant, pid)


def change(tenant: str, pid: str, words: str, conv: str = "") -> dict[str, Any]:
    words = (words or "").strip()
    if len(words) < 2:
        raise EngError("Kya badalna hai, likhiye (jaise 'holes 10 mm karo').")
    ensure_table()
    r = _own(tenant, pid)
    if not r.versions:
        raise EngError("Is part ka pehla version abhi bana nahi.")
    _gate(tenant)
    _save(pid, status="queued", stage="Badlav shuru", error="", pending={"mode": "change", "words": words[:1500]},
          **({"conversation_id": conv} if conv else {}))
    _submit(pid)
    return get(tenant, pid)


def _own(tenant: str, pid: str) -> EngProject:
    with session() as s:
        r = s.get(EngProject, pid)
        if r is None or r.tenant_id != tenant:
            raise EngError("Yeh project nahi mila.")
        s.expunge(r)
        return r


def get(tenant: str, pid: str) -> dict[str, Any]:
    ensure_table()
    return view(_own(tenant, pid))


def projects(tenant: str, limit: int = 30) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(EngProject).where(EngProject.tenant_id == tenant)
                         .order_by(EngProject.updated_at.desc()).limit(max(1, min(limit, 100)))).all()
        return [view(r) for r in rows]


def delete(tenant: str, pid: str) -> None:
    r = _own(tenant, pid)
    import shutil
    shutil.rmtree(_pdir(tenant, r.id), ignore_errors=True)
    with session() as s:
        s.delete(s.get(EngProject, pid))


# ---------------------------------------------------------------- the job
def _submit(pid: str) -> None:
    if os.environ.get("ENG_WORKER", "true").lower() in ("0", "false", "off"):
        return                                    # tests call run_job themselves
    _POOL.submit(run_job, pid)


def checks(res: dict[str, Any], size: list[float]) -> tuple[list[dict[str, Any]], list[str]]:
    """([{name, ok, note}], problems to send back to the model)."""
    out, probs = [], []
    ok_valid = bool(res.get("valid"))
    out.append({"name": "Valid solid", "ok": ok_valid, "note": "" if ok_valid else "the kernel says the solid is broken"})
    if not ok_valid:
        probs.append("the solid is not valid (BRep check failed): simplify fillets / booleans")
    vol = float(res.get("volume_mm3") or 0)
    out.append({"name": "Has volume", "ok": vol > 0, "note": f"{vol:,.0f} mm³"})
    if vol <= 0:
        probs.append("the result has no volume")
    n = int(res.get("solids") or 0)
    parts = res.get("parts") or []
    if parts:                                       # v0.362 an assembly: every part must be a valid solid of its own
        bad = [p["name"] for p in parts if not p.get("valid") or not p.get("volume_mm3")]
        out.append({"name": "Every part valid", "ok": not bad, "note": f"{len(parts)} parts" + (f", broken: {', '.join(bad)}" if bad else "")})
        if bad:
            probs.append(f"these assembly parts are broken or empty: {', '.join(bad)}")
    else:
        out.append({"name": "One body", "ok": n == 1, "note": f"{n} bodies"})
        if n != 1:
            probs.append(f"the result has {n} separate bodies: union them into one solid, or return a cq.Assembly "
                         "if she asked for several parts")
    bb = res.get("bbox") or {}
    real = sorted([float(bb.get("x", 0)), float(bb.get("y", 0)), float(bb.get("z", 0))])
    if len(size) == 3:
        want = sorted(size)
        miss = [(w, g) for w, g in zip(want, real) if abs(w - g) > max(0.5, 0.02 * w)]
        out.append({"name": "Size as asked", "ok": not miss,
                    "note": f"{real[0]:g} x {real[1]:g} x {real[2]:g} mm" + ("" if not miss else f" (expected {want[0]:g} x {want[1]:g} x {want[2]:g})")})
        if miss:
            probs.append(f"the bounding box is {bb.get('x')} x {bb.get('y')} x {bb.get('z')} mm but the part should be "
                         f"{size[0]:g} x {size[1]:g} x {size[2]:g} mm")
    for row in res.get("expect") or []:             # v0.365 her own numbers, measured on the B-rep
        out.append({"name": f"Asked: {row.get('name')}", "ok": bool(row.get("ok")),
                    "note": f"{row.get('got')} (wanted {row.get('want')})"})
        if not row.get("ok"):
            probs.append(f"her requirement '{row.get('name')}' fails: wanted {row.get('want')}, measured {row.get('got')}")
    return out, probs


def _analyse(vdir: Path, res: dict[str, Any], material: str = "") -> dict[str, Any]:
    """v0.365 FEA + CAM on the built part (the same locked box, Hoola's own code); a study without its own
    material uses the part's."""
    studies = [{**st, "material": st.get("material") or material or "steel"} for st in res.get("studies") or []]
    try:
        return sandbox.analyse(vdir, studies, (res.get("cam") or [None])[0])
    except sandbox.SandboxError as e:
        return {"ok": False, "errors": [str(e)[:300]], "studies": [], "cam": None}


def _weak(ana: dict[str, Any]) -> list[str]:
    """Problems that send the design back for a stronger / stiffer version."""
    out = []
    for st in ana.get("studies") or []:
        if not st.get("ok"):
            continue
        if st.get("kind") == "static" and st.get("passes") is False:
            out.append(f"too weak under her load: safety factor {st['safety_factor']} but she needs {st['min_sf']} "
                       f"(peak von Mises {st['peak_vm_away_MPa']} MPa at {st['at_peak']} mm, yield {st['yield_MPa']} MPa): "
                       "make it stronger THERE (thicker section, a rib, a bigger fillet at the corner, shorter lever) "
                       "keeping her fixed sizes and holes; keep the H.analyze call unchanged")
        rz = st.get("resonance")
        if st.get("kind") == "modal" and rz and not rz.get("ok"):
            out.append(f"resonance: natural frequencies {rz['inside']} Hz fall inside the band {rz['band_hz']} Hz she "
                       "must avoid: stiffen (ribs / thicker / shorter span) or change mass to move them out; keep H.analyze")
    return out


def _after_files(vdir: Path, res: dict[str, Any], ana: dict[str, Any], title: str, material: str) -> None:
    """v0.365 pictures + report for the after-build stage."""
    from . import report
    pics = []
    for i, st in enumerate(ana.get("studies") or []):
        sp = vdir / f"fea_{i}.json"
        if st.get("ok") and sp.exists():
            try:
                img = report.fea_view(json.loads(sp.read_text(encoding="utf-8")), st.get("scale") or {})
                img.save(vdir / f"fea_{i}.png", "PNG", optimize=True)
                pics.append(img)
            except Exception as e:
                log.info("fea picture: %s", e)
        sp.unlink(missing_ok=True)
    cam = ana.get("cam")
    cp = vdir / "cam_paths.json"
    if cam and cam.get("ok") and cp.exists():
        try:
            img = report.cam_png(json.loads(cp.read_text(encoding="utf-8")), cam.get("size") or [0, 0])
            img.save(vdir / "cam.png", "PNG", optimize=True)
            pics.append(img)
        except Exception as e:
            log.info("cam picture: %s", e)
    cp.unlink(missing_ok=True)
    if res.get("sheet"):
        try:
            (vdir / "flat.dxf").write_text(report.flat_dxf(res["sheet"]), encoding="utf-8")
            report.flat_png(res["sheet"]).save(vdir / "flat.png", "PNG", optimize=True)
        except Exception as e:
            log.info("flat pattern: %s", e)
    if ana.get("studies") or cam:
        (vdir / "analysis.pdf").write_bytes(report.analysis_pdf(title, {**res, "material": material},
                                                                ana.get("studies") or [], pics, cam))


def printability(mesh: dict[str, Any], bbox: dict[str, Any]) -> dict[str, Any]:
    """v0.362 3D printing hints from the mesh: how much surface hangs down steeper than 45 deg (needs supports) and
    whether it fits a common 220 x 220 x 250 mm bed."""
    v, tris = mesh.get("v") or [], mesh.get("t") or []
    if not v or not tris:
        return {}
    zmin = min(p[2] for p in v)
    total = over = 0.0
    for a, b, c in tris:
        pa, pb, pc = v[a], v[b], v[c]
        ux, uy, uz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]
        wx, wy, wz = pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2]
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        area = (nx * nx + ny * ny + nz * nz) ** 0.5 / 2
        total += area
        if area and nz / (2 * area) < -0.7071 and min(pa[2], pb[2], pc[2]) > zmin + 0.2:
            over += area
    dims = sorted([float(bbox.get("x", 0)), float(bbox.get("y", 0)), float(bbox.get("z", 0))])
    return {"overhang_pct": round(100 * over / total, 1) if total else 0.0,
            "fits_220_bed": dims[0] <= 220 and dims[1] <= 220 and dims[2] <= 250}


def _mass(volume_mm3: float, material: str) -> float | None:
    k = next((m for m in DENSITY if m in (material or "").lower()), None)
    return round(volume_mm3 * DENSITY[k] / 1000.0, 1) if k else None


def _inputs(r: EngProject) -> tuple[list[bytes], list[str]]:
    idir = _pdir(r.tenant_id, r.id) / "inputs"
    imgs, files = [], []
    for i in r.inputs or []:
        p = idir / str(i.get("name"))
        if not p.is_file():
            continue
        if i.get("kind") == "image":
            imgs.append(p.read_bytes())
        else:
            files.append(p.name)
    return imgs, files


def run_job(pid: str) -> None:
    from .. import usage
    with session() as s:
        r = s.get(EngProject, pid)
        if r is None:
            return
        tenant = r.tenant_id
    try:
        with usage.scope(tenant, "eng"):
            _run(pid)
    except (ai.AiError, sandbox.SandboxError, EngError) as e:
        _fail(pid, str(e))
    except Exception as e:      # never leave a project stuck "building"
        log.exception("eng job %s", pid)
        _fail(pid, f"{type(e).__name__}: {e}")


def _fail(pid: str, why: str) -> None:
    r = _save(pid, status="failed", stage="Nahi bana", error=why[:600], pending={})
    _note(r, f"CAD part '{r.title or 'part'}' nahi ban paya: {why[:200]}")


def _note(r: EngProject, text: str) -> None:
    if not r.conversation_id:
        return
    try:
        from ..events import notify
        notify(r.conversation_id, text)
    except Exception as e:
        log.info("eng note: %s", e)


def _run(pid: str) -> None:
    r = _own_any(pid)
    mode = (r.pending or {}).get("mode", "new")
    words = (r.pending or {}).get("words", "")
    imgs, files = _inputs(r)
    _save(pid, status="designing", stage="Design soch raha hoon", error="")
    last = (r.versions or [])[-1] if r.versions else None
    if mode == "change" and last:
        code_prev = (_pdir(r.tenant_id, pid) / f"v{last['n']}" / "part.py").read_text(encoding="utf-8")
        d = ai.change(r.brief, code_prev, words, files)
    else:
        d = ai.write(r.brief, imgs, files)
    n = (last["n"] + 1) if last else 1
    vdir = _pdir(r.tenant_id, pid) / f"v{n}"
    ask_txt = r.brief + (f"\nCHANGE: {words}" if words else "")
    look_rounds = int(os.environ.get("ENG_LOOK_ROUNDS", "1") or 0)
    strengthen = int(os.environ.get("ENG_STRENGTHEN_ROUNDS", "2") or 0)
    ana: dict[str, Any] = {}
    t0 = time.time()
    res: dict[str, Any] = {}
    chk: list[dict[str, Any]] = []
    review: dict[str, Any] = {}
    views: dict[str, bytes] = {}
    for attempt in range(MAX_FIXES + 1):
        probs = guard.problems(d.get("code", ""))
        views = {}
        if not probs:
            _save(pid, status="building", stage="Part bana raha hoon" + (f" (sudhaar {attempt})" if attempt else ""))
            res = sandbox.run(vdir, d["code"])
            probs = list(res.get("errors") or [])
            if res.get("ok"):
                chk, probs = checks(res, d.get("size") or [])
        if not probs and look_rounds > 0 and attempt < MAX_FIXES:
            _save(pid, status="checking", stage="Opus model ko dekh kar jaanch raha hai")
            mesh = json.loads((vdir / "mesh.json").read_text(encoding="utf-8"))
            views = render.views(mesh, 600)
            review = ai.look(ask_txt, [views[k] for k in ("iso", "front", "top", "right")])
            look_rounds -= 1
            if not review.get("ok"):
                probs = [f"design review: {p}" for p in review.get("problems") or []]
        ana = {}
        if not probs and res.get("ok") and (res.get("studies") or res.get("cam")):
            _save(pid, status="analysing", stage="Stress / heat / vibration jaanch (FEA)" if res.get("studies")
                  else "CNC G-code bana raha hoon")
            ana = _analyse(vdir, res, d.get("material") or "")
            weak = _weak(ana)
            if weak and strengthen > 0 and attempt < MAX_FIXES:
                strengthen -= 1
                probs = weak
        if not probs:
            break
        if attempt == MAX_FIXES:
            if res.get("ok"):
                break                               # keep it; failed checks / review show on the desk
            raise EngError("Part chaar koshish mein nahi bana: " + "; ".join(probs)[:300])
        _save(pid, status="designing", stage=f"Galti theek kar raha hoon ({attempt + 1}/{MAX_FIXES})")
        fixed = ai.fix(ask_txt, d.get("code", ""), probs, files,
                       [views[k] for k in ("iso", "front", "top", "right")] if views else None)
        d = {**fixed, "title": fixed.get("title") or d.get("title", ""), "size": fixed.get("size") or d.get("size") or [],
             "material": fixed.get("material") or d.get("material", ""), "plan": fixed.get("plan") or d.get("plan", "")}
    (vdir / "part.py").write_text(d["code"], encoding="utf-8")
    _save(pid, status="drawing", stage="Views aur drawing bana raha hoon")
    mesh = json.loads((vdir / "mesh.json").read_text(encoding="utf-8"))
    for name, data in render.views(mesh).items():
        (vdir / f"{name}.png").write_bytes(data)
    title = d.get("title") or r.title or "Part"
    material = d.get("material") or ""
    mass = _mass(float(res.get("volume_mm3") or 0), material)
    parts = [{**p, "mass_g": _mass(float(p.get("volume_mm3") or 0), material)} for p in res.get("parts") or []]
    hlr = {}
    hp = vdir / "hlr.json"
    if hp.exists():
        try:
            hlr = json.loads(hp.read_text(encoding="utf-8"))
        except ValueError:
            hlr = {}
    (vdir / "drawing.pdf").write_bytes(render.drawing_pdf(mesh, {**res, "title": title, "material": material,
                                                                 "mass_g": mass or 0}, hlr))
    _after_files(vdir, res, ana, title, material)
    pr = printability(mesh, res.get("bbox") or {})
    (vdir / "mesh.json").unlink(missing_ok=True)
    hp.unlink(missing_ok=True)
    ver = {"n": n, "title": title, "size": d.get("size") or [], "bbox": res.get("bbox"), "volume_mm3": res.get("volume_mm3"),
           "checks": chk, "assumed": d.get("assumed", ""), "notes": d.get("notes", ""), "words": words,
           "plan": d.get("plan", ""), "material": material, "mass_g": mass, "com": res.get("com"), "parts": parts,
           "print": pr, "review": review, "expect": res.get("expect") or [], "sheet": res.get("sheet"),
           "analysis": [_ana_card(st) for st in ana.get("studies") or []],
           "cam": {k: v for k, v in (ana.get("cam") or {}).items() if k != "paths"} or None,
           "files": [f for f in FILES if (vdir / f).exists()], "seconds": round(time.time() - t0, 1),
           "at": now().isoformat(), "day": _ist_day(datetime.now(timezone.utc))}
    rr = _save(pid, status="done", stage="Taiyaar", title=title[:120], versions=[*(r.versions or []), ver], pending={})
    bb = res.get("bbox") or {}
    bad = [c["name"] for c in chk if not c["ok"]] + (["design review"] if review and not review.get("ok") else [])
    _note(rr, f"CAD {'assembly' if parts else 'part'} taiyaar: {title}, {bb.get('x', 0):g} x {bb.get('y', 0):g} x "
              f"{bb.get('z', 0):g} mm" + (f", {len(parts)} parts" if parts else "")
              + (f", about {mass:,.0f} g ({material})" if mass else "")
              + "".join(f", {line}" for line in _ana_lines(ana))
              + (f" (jaanch mein dikkat: {', '.join(bad)})" if bad else "")
              + ". STEP, STL, 3MF, drawing CAD Desk par hain.")


def _ana_card(st: dict[str, Any]) -> dict[str, Any]:
    from .report import summary_rows
    keep = {k: st.get(k) for k in ("ok", "kind", "material", "max_disp_mm", "peak_vm_MPa", "peak_vm_away_MPa", "at_peak",
                                   "safety_factor", "min_sf", "passes", "convergence", "equilibrium_error_pct",
                                   "t_max_C", "t_min_C", "frequencies_hz", "resonance", "mesh", "error", "glued_assembly")
            if st.get(k) is not None}
    keep["lines"] = summary_rows(st)
    return keep


def _ana_lines(ana: dict[str, Any]) -> list[str]:
    out = []
    for st in ana.get("studies") or []:
        if not st.get("ok"):
            out.append(f"{st.get('kind')} analysis nahi chala")
        elif st["kind"] == "static":
            out.append(f"safety factor {st['safety_factor']:g} (max jhukav {st['max_disp_mm']:.3g} mm)")
        elif st["kind"] == "thermal":
            out.append(f"max garmi {st['t_max_C']:.3g} °C")
        else:
            out.append("pehli frequency " + (f"{st['frequencies_hz'][0]:g} Hz" if st.get("frequencies_hz") else "-"))
    cam = ana.get("cam")
    if cam:
        out.append(f"CNC G-code taiyaar (~{cam['minutes']:g} min)" if cam.get("ok") else "G-code nahi bana")
    return out


def _own_any(pid: str) -> EngProject:
    with session() as s:
        r = s.get(EngProject, pid)
        s.expunge(r)
        return r


def health() -> dict[str, Any]:
    return {"cadquery": sandbox.installed(), "no_network": sandbox.net_isolation(), "python": sandbox.python(),
            "fea": sandbox.installed("skfem"), "fast_solver": sandbox.installed("pyamg")}


if __name__ == "__main__":   # python -m app.engineering.service  -> is the CAD engine ready on this server?
    print(json.dumps(health(), indent=2))
