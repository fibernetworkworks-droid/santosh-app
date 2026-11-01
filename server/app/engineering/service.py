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
MAX_FIXES = 2
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="engineering")
_LOCK = threading.Lock()
FILES = ("part.step", "part.stl", "drawing.pdf", "iso.png", "front.png", "top.png", "right.png", "part.py")


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
    status: Mapped[str] = mapped_column(String(16), default="queued")   # queued|designing|building|drawing|done|failed
    stage: Mapped[str] = mapped_column(String(160), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    pending: Mapped[dict] = mapped_column(JSON, default=dict)            # {mode: new|change, words}
    versions: Mapped[list] = mapped_column(JSON, default=list)
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
                                            "at", "seconds", "words")}, "files": files})
    return {"id": r.id, "kind": r.kind, "title": r.title or "Part", "brief": r.brief, "status": r.status, "stage": r.stage,
            "error": r.error, "versions": vs, "latest": vs[-1] if vs else None,
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
                                                     EngProject.status.in_(("queued", "designing", "building", "drawing")))).first()
    if busy:
        raise EngError("Ek part abhi ban raha hai; uske poora hote hi agla shuru karenge.")


# ---------------------------------------------------------------- public actions
def start(tenant: str, conv: str, brief: str) -> dict[str, Any]:
    brief = (brief or "").strip()
    if len(brief) < 4:
        raise EngError("Part ke baare mein likhiye: kya hai, size (mm), holes, material.")
    ensure_table()
    _gate(tenant)
    with session() as s:
        r = EngProject(tenant_id=tenant, conversation_id=conv or "", brief=brief[:4000], status="queued",
                       stage="Shuru ho raha hai", pending={"mode": "new"})
        s.add(r)
        s.flush()
        pid = r.id
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
    out.append({"name": "One body", "ok": n == 1, "note": f"{n} bodies"})
    if n != 1:
        probs.append(f"the result has {n} separate bodies: union them into one solid (unless she asked for parts)")
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
    return out, probs


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
    _save(pid, status="designing", stage="Design likh raha hoon", error="")
    last = (r.versions or [])[-1] if r.versions else None
    if mode == "change" and last:
        code_prev = (_pdir(r.tenant_id, pid) / f"v{last['n']}" / "part.py").read_text(encoding="utf-8")
        d = ai.change(r.brief, code_prev, words)
    else:
        d = ai.write(r.brief)
    n = (last["n"] + 1) if last else 1
    vdir = _pdir(r.tenant_id, pid) / f"v{n}"
    t0 = time.time()
    res: dict[str, Any] = {}
    chk: list[dict[str, Any]] = []
    for attempt in range(MAX_FIXES + 1):
        probs = guard.problems(d.get("code", ""))
        if not probs:
            _save(pid, status="building", stage="Part bana raha hoon" + (f" (sudhaar {attempt})" if attempt else ""))
            res = sandbox.run(vdir, d["code"])
            probs = list(res.get("errors") or [])
            if res.get("ok"):
                chk, probs = checks(res, d.get("size") or [])
        if not probs:
            break
        if attempt == MAX_FIXES:
            if res.get("ok"):
                break                               # keep it, the failed checks show on the desk
            raise EngError("Part teen koshish mein nahi bana: " + "; ".join(probs)[:300])
        _save(pid, status="designing", stage=f"Galti theek kar raha hoon ({attempt + 1}/{MAX_FIXES})")
        fixed = ai.fix(r.brief + (f"\nCHANGE: {words}" if words else ""), d.get("code", ""), probs)
        d = {**fixed, "title": fixed.get("title") or d.get("title", ""), "size": fixed.get("size") or d.get("size") or []}
    (vdir / "part.py").write_text(d["code"], encoding="utf-8")
    _save(pid, status="drawing", stage="Views aur drawing bana raha hoon")
    mesh = json.loads((vdir / "mesh.json").read_text(encoding="utf-8"))
    for name, data in render.views(mesh).items():
        (vdir / f"{name}.png").write_bytes(data)
    title = d.get("title") or r.title or "Part"
    (vdir / "drawing.pdf").write_bytes(render.drawing_pdf(mesh, {**res, "title": title}))
    (vdir / "mesh.json").unlink(missing_ok=True)
    ver = {"n": n, "title": title, "size": d.get("size") or [], "bbox": res.get("bbox"), "volume_mm3": res.get("volume_mm3"),
           "checks": chk, "assumed": d.get("assumed", ""), "notes": d.get("notes", ""), "words": words,
           "files": [f for f in FILES if (vdir / f).exists()], "seconds": round(time.time() - t0, 1),
           "at": now().isoformat(), "day": _ist_day(datetime.now(timezone.utc))}
    rr = _save(pid, status="done", stage="Taiyaar", title=title[:120], versions=[*(r.versions or []), ver], pending={})
    bb = res.get("bbox") or {}
    bad = [c["name"] for c in chk if not c["ok"]]
    _note(rr, f"CAD part taiyaar: {title}, {bb.get('x', 0):g} x {bb.get('y', 0):g} x {bb.get('z', 0):g} mm"
              + (f" (jaanch mein dikkat: {', '.join(bad)})" if bad else "")
              + ". STEP, STL aur drawing CAD Desk par hain.")


def _own_any(pid: str) -> EngProject:
    with session() as s:
        r = s.get(EngProject, pid)
        s.expunge(r)
        return r


def health() -> dict[str, Any]:
    return {"cadquery": sandbox.installed(), "no_network": sandbox.net_isolation(), "python": sandbox.python()}


if __name__ == "__main__":   # python -m app.engineering.service  -> is the CAD engine ready on this server?
    print(json.dumps(health(), indent=2))
