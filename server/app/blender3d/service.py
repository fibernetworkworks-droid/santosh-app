"""3D Studio jobs: her words (+ photos) -> Blender script -> checked -> run in the box -> fixed from real errors -> render
looked at -> delivered (renders with the 'AI se bana' label, GLB / STL / OBJ / FBX / USDZ / .blend as her files, turntable
MP4) + a live `blender3d` card. Changes in her words make a new version from the current script.

Nothing here spends money (only model calls, counted as feature '3d' in AI kharcha) and nothing is sent or posted."""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session
from ..events import bus
from . import ai, guard, sandbox

log = logging.getLogger("santosh.blender3d")

FORMATS = ("glb", "stl", "obj", "fbx", "usdz", "blend")
VIEWS = ("three_quarter", "front", "side", "back", "top", "low")
QUALITY = {"preview": {"samples": 24, "width": 1024, "height": 1024},
           "final": {"samples": 96, "width": 1600, "height": 1600}}
ASPECTS = {"1:1": (1, 1), "4:5": (4, 5), "9:16": (9, 16), "16:9": (16, 9), "3:4": (3, 4), "4:3": (4, 3)}
MAX_PHOTOS = 6
MAX_EXPORT_MB = 60
KEEP = 60
FIX_ROUNDS = 3
STATS = {"runs": 0, "ok": 0, "guard_refused": 0, "fixed": 0, "looks": 0, "failed": 0}

_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="blender3d")
_RUNNING: dict[str, dict] = {}            # project id -> sandbox holder (to kill on cancel)
_LOCK = threading.Lock()


class B3Error(Exception):
    pass


class Blender3D(Base):
    __tablename__ = "blender3d_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("b3d"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    number: Mapped[str] = mapped_column(String(16), default="")
    title: Mapped[str] = mapped_column(String(120), default="")
    brief: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="queued")   # queued|writing|building|rendering|checking|done|failed|cancelled
    stage: Mapped[str] = mapped_column(String(120), default="")
    pct: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    pending: Mapped[dict] = mapped_column(JSON, default=dict)           # what the next run does {mode, words, code ...}
    versions: Mapped[list] = mapped_column(JSON, default=list)
    actor: Mapped[str] = mapped_column(String(64), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- folders, links
def root() -> Path:
    p = Path(os.environ.get("BLENDER3D_DIR", "./data/blender3d"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _pdir(tenant: str, pid: str) -> Path:
    safe = re.sub(r"[^\w-]", "_", tenant)[:64] or "t"
    return root() / safe / pid


def _sig(pid: str, name: str, exp: int) -> str:
    st = get_settings()
    key = st.secret_key or st.api_key or "hoola-3d"
    return hmac.new(f"b3d:{key}".encode(), f"{pid}/{name}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def file_url(pid: str, name: str, days: int = 10) -> str:
    exp = int(time.time()) + days * 86400
    return f"/api/blender3d/files/{pid}/{name}?exp={exp}&sig={_sig(pid, name, exp)}"


def file_path(pid: str, name: str, exp: int, sig: str) -> Path | None:
    if exp < time.time() or not hmac.compare_digest(_sig(pid, name, exp), sig or ""):
        return None
    if not re.fullmatch(r"v\d{1,3}/[\w\-. ]{1,80}", name or "") or ".." in name:
        return None
    with session() as s:
        row = s.get(Blender3D, pid)
        if row is None:
            return None
        p = _pdir(row.tenant_id, pid) / name
    return p if p.is_file() else None


def _ai_label(png: bytes) -> bytes:
    try:
        from .. import photogen
        return photogen.label(png)
    except Exception:
        return png


# ---------------------------------------------------------------- views
def view(r: Blender3D, full: bool = False) -> dict[str, Any]:
    vers = r.versions or []
    last = vers[-1] if vers else {}
    d = {"id": r.id, "number": r.number, "title": r.title or r.brief[:60], "brief": r.brief[:400], "status": r.status,
         "stage": r.stage, "pct": r.pct, "error": r.error, "options": {k: v for k, v in (r.options or {}).items()
                                                                         if k != "photo_paths"},
         "version": last.get("n", 0), "versions": len(vers), "notes": last.get("notes", ""),
         "renders": last.get("renders", []), "video": last.get("video"), "exports": last.get("exports", {}),
         "stats": _short_stats(last.get("stats") or {}), "look": last.get("look"), "warnings": last.get("warnings", [])[:6],
         "print_check": last.get("print_check"), "created_at": r.created_at.isoformat() if r.created_at else None}
    if full:
        d["history"] = [{"n": v.get("n"), "words": v.get("words", ""), "notes": v.get("notes", ""),
                         "renders": v.get("renders", [])[:1], "at": v.get("at")} for v in vers]
        d["script"] = last.get("script", "")
        d["objects"] = (last.get("stats") or {}).get("objects", [])
    return d


def _short_stats(st: dict) -> dict:
    return {k: st.get(k) for k in ("count", "tris", "size_m", "materials") if k in st}


def _publish(r: Blender3D, **extra) -> None:
    if r.conversation_id:
        try:
            bus.publish(r.conversation_id, "blender3d", {**view(r), **extra})
        except Exception as e:
            log.info("3d publish: %s", e)


def _save(r: Blender3D, **fields) -> Blender3D:
    with session() as s:
        row = s.get(Blender3D, r.id)
        for k, v in fields.items():
            setattr(row, k, v)
            setattr(r, k, v)
        row.updated_at = now()
    return r


def _stage(r: Blender3D, status: str, stage: str, pct: int) -> None:
    _save(r, status=status, stage=stage, pct=pct)
    _publish(r)


# ---------------------------------------------------------------- starting jobs
def _clean_opts(o: dict[str, Any]) -> dict[str, Any]:
    o = dict(o or {})
    fm = [f for f in (o.get("exports") or []) if f in FORMATS]
    vw = [v for v in (o.get("views") or []) if v in VIEWS][:4]
    q = o.get("quality") if o.get("quality") in QUALITY else "preview"
    aspect = o.get("aspect") if o.get("aspect") in ASPECTS else "1:1"
    tt = o.get("turntable")
    tt = 36 if tt is True else (max(0, min(int(tt or 0), 72)) if str(tt or "0").isdigit() else 0)
    pr = bool(o.get("print"))
    if pr and "stl" not in fm:
        fm.append("stl")
    return {"exports": fm or (["stl", "glb"] if pr else ["glb"]), "views": vw or ["three_quarter"], "quality": q,
            "aspect": aspect, "turntable": tt, "print": pr, "style": str(o.get("style") or "")[:200],
            "background": str(o.get("background") or "#f4f4f6")[:9], "transparent": bool(o.get("transparent")),
            "photos": [str(x) for x in (o.get("photos") or [])][:MAX_PHOTOS]}


def _limits(tenant: str) -> None:
    with session() as s:
        rows = s.scalars(select(Blender3D).where(Blender3D.tenant_id == tenant)).all()
    busy = [r for r in rows if r.status in ("queued", "writing", "building", "rendering", "checking")]
    if len(busy) >= 3:
        raise B3Error("3 kaam pehle se chal rahe hain; ek khatam hone dijiye.")
    day = datetime.now(timezone.utc) - timedelta(days=1)
    runs = sum(1 for r in rows for v in (r.versions or []) if (v.get("at") or "") >= day.isoformat())
    if runs >= int(os.environ.get("BLENDER_DAY_RUNS", "40")):
        raise B3Error("Aaj ke 3D kaam ki seema poori ho gayi; kal phir.")


def _number(tenant: str) -> str:
    with session() as s:
        n = len(s.scalars(select(Blender3D.id).where(Blender3D.tenant_id == tenant)).all())
    return f"B3-{n + 1:04d}"


def problem(brief: str) -> str:
    """Asks Hoola never builds (same rules as photo_banao: fake IDs / notes / seals, famous people, emblems)."""
    try:
        from .. import photogen
        why = photogen.problem(brief, edit=False)
        if why:
            return why
    except Exception:
        pass
    if re.search(r"\b(gun|pistol|rifle|firearm|bandook|katta|silencer|suppressor|grenade|bomb|explosive|knuckle ?duster)\b",
                 brief or "", re.I) and re.search(r"\b(print|stl|working|real|asli|chalne wala|functional)\b", brief or "", re.I):
        return "Hathiyar ke chalne wale / print hone wale parts Hoola nahi banata."
    return ""


def start(tenant: str, conv: str, brief: str, options: dict[str, Any] | None = None, actor: str = "owner",
          code: str = "", title: str = "") -> dict[str, Any]:
    brief = re.sub(r"\s+", " ", str(brief or "")).strip()[:2000]
    if not brief and not code:
        raise B3Error("Kya banana hai? Do-teen line mein bataiye (cheez, rang, size, kis kaam ke liye).")
    why = problem(brief)
    if why:
        raise B3Error(why)
    if code:
        p = guard.problems(code)
        if p:
            STATS["guard_refused"] += 1
            raise guard.GuardError(p)
    _limits(tenant)
    opts = _clean_opts(options or {})
    r = Blender3D(tenant_id=tenant, conversation_id=conv or "", number=_number(tenant), brief=brief or (title or "3D script"),
                  title=(title or "")[:120], options=opts, actor=actor or "owner",
                  pending={"mode": "code" if code else "new", "code": code or ""})
    with session() as s:
        s.add(r)
    _prune(tenant)
    _publish(r)
    _submit(r.id)
    return view(r)


def change(tenant: str, pid: str, words: str = "", options: dict[str, Any] | None = None) -> dict[str, Any]:
    r = _get(tenant, pid)
    if r.status in ("queued", "writing", "building", "rendering", "checking"):
        raise B3Error("Abhi bana raha hoon; khatam hote hi badlav bataiye.")
    if not r.versions:
        raise B3Error("Abhi koi version bana nahi; pehle naya banwaiye.")
    words = re.sub(r"\s+", " ", str(words or "")).strip()[:1500]
    if words:
        why = problem(words)
        if why:
            raise B3Error(why)
    _limits(tenant)
    opts = _clean_opts({**(r.options or {}), **(options or {})})
    mode = "change" if words else "again"          # again = same script, new render / export settings
    _save(r, options=opts, pending={"mode": mode, "words": words}, status="queued", stage="line mein", pct=0, error="")
    _publish(r)
    _submit(r.id)
    return view(r)


def run_code(tenant: str, conv: str, code: str, title: str = "", pid: str = "", options: dict | None = None,
             actor: str = "owner") -> dict[str, Any]:
    """The chat model's own Blender script (what Blender MCP calls execute code): guard first, then the box."""
    p = guard.problems(code)
    if p:
        STATS["guard_refused"] += 1
        raise guard.GuardError(p)
    if pid:
        r = _get(tenant, pid)
        if r.status in ("queued", "writing", "building", "rendering", "checking"):
            raise B3Error("Abhi bana raha hoon; khatam hone dijiye.")
        _limits(tenant)
        _save(r, options=_clean_opts({**(r.options or {}), **(options or {})}), pending={"mode": "code", "code": code},
              status="queued", stage="line mein", pct=0, error="")
        _publish(r)
        _submit(r.id)
        return view(r)
    return start(tenant, conv, title or "Hoola ki script", options, actor, code=code, title=title)


def cancel(tenant: str, pid: str) -> dict[str, Any]:
    r = _get(tenant, pid)
    h = _RUNNING.get(pid)
    if h:
        sandbox.kill(h)
    if r.status not in ("done", "failed"):
        _save(r, status="cancelled", stage="rok diya", error="")
        _publish(r)
    return view(r)


def delete(tenant: str, pid: str) -> None:
    r = _get(tenant, pid)
    cancel(tenant, pid) if r.status not in ("done", "failed", "cancelled") else None
    shutil.rmtree(_pdir(tenant, pid), ignore_errors=True)
    with session() as s:
        row = s.get(Blender3D, pid)
        if row is not None:
            s.delete(row)


def _get(tenant: str, pid: str) -> Blender3D:
    with session() as s:
        r = s.get(Blender3D, pid)
        if r is None:
            r = s.scalars(select(Blender3D).where(Blender3D.tenant_id == tenant, Blender3D.number == str(pid).upper())).first()
        if r is None or r.tenant_id != tenant:
            raise B3Error("Ye 3D kaam nahi mila.")
        s.expunge(r)
        return r


def get(tenant: str, pid: str) -> dict[str, Any]:
    return view(_get(tenant, pid), full=True)


def projects(tenant: str, limit: int = 30) -> list[dict[str, Any]]:
    _heal(tenant)
    with session() as s:
        rows = s.scalars(select(Blender3D).where(Blender3D.tenant_id == tenant)
                         .order_by(Blender3D.created_at.desc()).limit(limit)).all()
    return [view(r) for r in rows]


def _heal(tenant: str) -> None:
    """A job that was running when the server restarted is said plainly, not left spinning."""
    with session() as s:
        for r in s.scalars(select(Blender3D).where(Blender3D.tenant_id == tenant)).all():
            if r.status in ("writing", "building", "rendering", "checking") and r.id not in _RUNNING:
                upd = r.updated_at if r.updated_at.tzinfo else r.updated_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - upd > timedelta(minutes=20):
                    r.status, r.error = "failed", "server restart ho gaya tha; 'dobara' boliye"


def _prune(tenant: str) -> None:
    with session() as s:
        rows = s.scalars(select(Blender3D).where(Blender3D.tenant_id == tenant).order_by(Blender3D.created_at.desc())).all()
        for r in rows[KEEP:]:
            shutil.rmtree(_pdir(tenant, r.id), ignore_errors=True)
            s.delete(r)


def _submit(pid: str) -> None:
    if os.environ.get("BLENDER3D_WORKER", "true").lower() in ("0", "false", "off"):
        return                                   # tests call run_job themselves
    _POOL.submit(_safe_run, pid)


def _safe_run(pid: str) -> None:
    try:
        run_job(pid)
    except Exception as e:  # never kill the pool thread
        log.exception("3d job %s: %s", pid, e)


# ---------------------------------------------------------------- the job
def _photos(r: Blender3D, pdir: Path) -> tuple[dict[str, str], list[bytes]]:
    """Her photos copied in (re-encoded: EXIF / GPS dropped), named p1.jpg ... -> {name: path}, reference bytes."""
    from ..mailbox import service as ms
    out, refs = {}, []
    inp = pdir / "inputs"
    inp.mkdir(parents=True, exist_ok=True)
    for i, fid in enumerate((r.options or {}).get("photos") or [], 1):
        try:
            f = ms._file_row(r.tenant_id, fid)
            raw = Path(f.stored_path).read_bytes()
            from PIL import Image
            im = Image.open(io.BytesIO(raw))
            im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
            im.thumbnail((2048, 2048))
            buf = io.BytesIO()
            name = f"p{i}.png" if im.mode == "RGBA" else f"p{i}.jpg"
            im.save(buf, "PNG" if name.endswith("png") else "JPEG", quality=90)
            (inp / name).write_bytes(buf.getvalue())
            out[name.split(".")[0]] = str(inp / name)
            if len(refs) < 2:
                small = im.convert("RGB")
                small.thumbnail((1024, 1024))
                b2 = io.BytesIO()
                small.save(b2, "JPEG", quality=85)
                refs.append(b2.getvalue())
        except Exception as e:
            log.info("3d photo %s skipped: %s", fid, e)
    return out, refs


def _fonts() -> dict[str, str]:
    base = Path(__file__).resolve().parents[1]
    f = {}
    for key, rel in (("devanagari", "videoedit/fonts/NotoSansDevanagari-Bold.ttf"),):
        if (base / rel).is_file():
            f[key] = str(base / rel)
    return f


def _job_dict(r: Blender3D, vdir: Path, script: Path, inputs: dict[str, str]) -> dict[str, Any]:
    o = r.options or {}
    q = dict(QUALITY[o.get("quality", "preview")])
    a, b = ASPECTS.get(o.get("aspect", "1:1"), (1, 1))
    side = q["width"]
    if a != b:
        q["width"], q["height"] = (side, int(side * b / a)) if a > b else (int(side * a / b), side)
    q.update({"views": o.get("views") or ["three_quarter"], "turntable": int(o.get("turntable") or 0),
              "transparent": bool(o.get("transparent")), "background": o.get("background", "#f4f4f6"),
              "threads": int(os.environ.get("BLENDER_THREADS", "2"))})
    base = re.sub(r"[^\w-]+", "_", (r.title or r.number or "hoola_3d"))[:40].strip("_") or "hoola_3d"
    return {"script": str(script), "render": q, "exports": o.get("exports") or ["glb"], "inputs": inputs,
            "fonts": _fonts(), "print": bool(o.get("print")), "base": base, "seed": 7}


def _try(r: Blender3D, vdir: Path, code: str, inputs: dict[str, str], brief: str, names: list[str],
         holder: dict) -> tuple[str, dict[str, Any], list[str]]:
    """Guard + run, fixing from real problems up to FIX_ROUNDS times. -> (final code, result, notes of what was fixed)"""
    fixed: list[str] = []
    res: dict[str, Any] = {"ok": False, "errors": ["kuch nahi chala"]}
    for rnd in range(FIX_ROUNDS + 1):
        if holder.get("cancelled"):
            return code, {"ok": False, "errors": ["rok diya gaya"], "cancelled": True}, fixed
        probs = guard.problems(code)
        if probs:
            STATS["guard_refused"] += 1
            res = {"ok": False, "errors": probs}
        else:
            _stage(r, "building", f"Blender mein bana raha hoon{' (sudhaar ' + str(rnd) + ')' if rnd else ''}", 30 + rnd * 10)
            script = vdir / "scene.py"
            script.write_text(code, encoding="utf-8")
            STATS["runs"] += 1
            res = sandbox.run(vdir, _job_dict(r, vdir, script, inputs), holder=holder)
            if res.get("ok") or res.get("cancelled"):
                return code, res, fixed
        if rnd == FIX_ROUNDS or res.get("timeout") and rnd >= 1:
            break
        _stage(r, "writing", "galti theek kar raha hoon", 25 + rnd * 10)
        new = ai.fix(brief, code, list(res.get("errors") or [])[:10], names, bool((r.options or {}).get("print")))
        if not new.get("code"):
            break
        fixed.append("; ".join(res.get("errors") or [])[:160])
        STATS["fixed"] += 1
        code = new["code"]
    return code, res, fixed


def run_job(pid: str) -> None:
    from .. import usage
    with session() as s:
        r = s.get(Blender3D, pid)
        if r is None or r.status == "cancelled":
            return
        s.expunge(r)
    holder: dict = {}
    _RUNNING[pid] = holder
    try:
        with usage.scope(r.tenant_id, "3d"):
            _run(r, holder)
    except (ai.AiError, sandbox.SandboxError, B3Error) as e:
        STATS["failed"] += 1
        _save(r, status="failed", error=str(e)[:400], stage="")
        _publish(r)
    except Exception as e:
        STATS["failed"] += 1
        log.exception("3d %s", pid)
        _save(r, status="failed", error=f"andar ki galti: {e}"[:400], stage="")
        _publish(r)
    finally:
        _RUNNING.pop(pid, None)


def _run(r: Blender3D, holder: dict) -> None:
    if not sandbox.find():
        raise sandbox.SandboxError("Blender is server par install nahi hai (deploy/setup_blender.sh chalaiye)")
    pend = dict(r.pending or {})
    mode = pend.get("mode", "new")
    vers = list(r.versions or [])
    n = (vers[-1]["n"] + 1) if vers else 1
    pdir = _pdir(r.tenant_id, r.id)
    vdir = pdir / f"v{n}"
    shutil.rmtree(vdir, ignore_errors=True)
    vdir.mkdir(parents=True, exist_ok=True)
    inputs, refs = _photos(r, pdir)
    names = list(inputs)
    pr = bool((r.options or {}).get("print"))
    title, notes = r.title, ""
    _stage(r, "writing", "3D ka plan likh raha hoon", 10)
    if mode == "code":
        code = pend.get("code", "")
    elif mode == "again":
        code = vers[-1].get("script", "")
    elif mode == "change":
        out = ai.change(r.brief, vers[-1].get("script", ""), pend.get("words", ""), names, pr)
        code, notes = out.get("code", ""), out.get("notes", "")
    else:
        out = ai.write(r.brief, names, refs, pr, (r.options or {}).get("style", ""))
        code, notes, title = out.get("code", ""), out.get("notes", ""), out.get("title") or r.title
    if not code:
        raise B3Error("Script nahi likh paya (model ne khaali jawab diya); dobara try kijiye.")
    if title and title != r.title:
        _save(r, title=title[:120])
    code, res, fixed = _try(r, vdir, code, inputs, r.brief, names, holder)
    if res.get("cancelled"):
        return
    look = None
    if res.get("ok") and res.get("renders") and mode in ("new", "change") and \
            os.environ.get("BLENDER_LOOK", "true").lower() not in ("0", "false", "off"):
        _stage(r, "checking", "render dekh kar jaanch raha hoon", 80)
        try:
            png = (vdir / res["renders"][0]["file"]).read_bytes()
            look = ai.look(r.brief + (" | change: " + pend.get("words", "") if mode == "change" else ""), png)
            STATS["looks"] += 1
            if not look["ok"] and look.get("fix"):
                _stage(r, "writing", "render mein kami dikhi, sudhaar raha hoon", 84)
                out = ai.change(r.brief, code, pend.get("words", "") or "match the ask better", names, pr, look["fix"])
                if out.get("code"):
                    v2 = pdir / f"v{n}b"
                    shutil.rmtree(v2, ignore_errors=True)
                    v2.mkdir(parents=True)
                    code2, res2, _ = _try(r, v2, out["code"], inputs, r.brief, names, holder)
                    if res2.get("ok"):
                        look2 = ai.look(r.brief, (v2 / res2["renders"][0]["file"]).read_bytes()) if res2.get("renders") else look
                        if look2["score"] >= look["score"]:
                            shutil.rmtree(vdir, ignore_errors=True)
                            v2.rename(vdir)
                            code, res, look = code2, res2, {**look2, "improved": True}
                            notes = out.get("notes") or notes
                    shutil.rmtree(v2, ignore_errors=True)
        except Exception as e:
            log.info("3d look: %s", e)
    if not res.get("ok"):
        err = "; ".join(res.get("errors") or ["Blender mein nahi bana"])[:500]
        vers.append({"n": n, "script": code, "words": pend.get("words", ""), "notes": notes, "ok": False, "error": err,
                     "at": datetime.now(timezone.utc).isoformat()})
        STATS["failed"] += 1
        _save(r, status="failed", error=err, stage="", versions=vers, pending={})
        _publish(r)
        return
    _stage(r, "rendering", "files taiyaar kar raha hoon", 92)
    ver = _deliver(r, n, vdir, code, res, pend, notes, look, fixed)
    vers.append(ver)
    STATS["ok"] += 1
    _save(r, status="done", stage="taiyaar", pct=100, error="", versions=vers, pending={})
    _publish(r, push=True, say=_say(r, ver))


def _deliver(r: Blender3D, n: int, vdir: Path, code: str, res: dict, pend: dict, notes: str, look, fixed) -> dict:
    from ..mailbox import service as ms
    from ..pc.service import public_file
    renders = []
    for item in res.get("renders") or []:
        p = vdir / item["file"]
        if not p.is_file():
            continue
        png = _ai_label(p.read_bytes())
        p.write_bytes(png)
        row = ms.store_bytes(r.tenant_id, f"{r.number} {item['view']}.png", png, "to_phone")
        renders.append({"view": item["view"], "url": file_url(r.id, f"v{n}/{item['file']}"), "file_id": row.id,
                        "name": public_file(row)["name"]})
    video = None
    frames = res.get("frames") or []
    if frames and shutil.which("ffmpeg"):
        mp4 = vdir / "turntable.mp4"
        try:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", str(vdir / "turn_%03d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)],
                           timeout=180, check=True)
            row = ms.store_bytes(r.tenant_id, f"{r.number} turntable.mp4", mp4.read_bytes(), "to_phone")
            video = {"url": file_url(r.id, f"v{n}/turntable.mp4"), "file_id": row.id}
            for f in frames:
                (vdir / f).unlink(missing_ok=True)
        except Exception as e:
            log.info("3d turntable: %s", e)
    exports = {}
    for fmt, fname in (res.get("exports") or {}).items():
        p = vdir / fname
        if not p.is_file():
            continue
        mb = p.stat().st_size / 1e6
        if mb > MAX_EXPORT_MB:
            exports[fmt] = {"name": fname, "mb": round(mb, 1), "too_big": True}
            continue
        row = ms.store_bytes(r.tenant_id, f"{r.number} {fname}", p.read_bytes(), "to_phone")
        exports[fmt] = {"name": fname, "mb": round(mb, 2), "file_id": row.id, "url": file_url(r.id, f"v{n}/{fname}")}
    stats = res.get("stats") or {}
    pc = None
    if (r.options or {}).get("print"):
        bad = [o["name"] for o in stats.get("objects", []) if o.get("open_edges")]
        size = stats.get("size_m") or [0, 0, 0]
        pc = {"closed": not bad, "open_parts": bad[:8], "size_mm": [round(v * 1000, 1) for v in size],
              "say": ("Print ke liye theek: sab hisse band (closed) hain." if not bad else
                      f"Print se pehle dekhiye: {', '.join(bad[:4])} mein khule kinare hain.")}
    (vdir / "scene.py").write_text(code, encoding="utf-8")
    return {"n": n, "script": code, "words": pend.get("words", ""), "notes": notes, "ok": True, "renders": renders,
            "video": video, "exports": exports, "stats": stats, "warnings": (res.get("warnings") or [])[:10],
            "look": look, "fixed": fixed[:4], "print_check": pc, "seconds": res.get("wall_s"),
            "isolated": res.get("isolated"), "blender": res.get("blender"), "at": datetime.now(timezone.utc).isoformat()}


def _say(r: Blender3D, ver: dict) -> str:
    st = ver.get("stats") or {}
    size = st.get("size_m") or []
    sz = " x ".join(f"{v:g}" for v in size) + " m" if size else ""
    bits = [f"{r.number} taiyaar: {r.title or '3D model'}", sz, f"files: {', '.join(ver.get('exports') or {}) or 'render'}"]
    if ver.get("print_check"):
        bits.append(ver["print_check"]["say"])
    return " · ".join(b for b in bits if b)


def health() -> dict[str, Any]:
    h = sandbox.health()
    return {**h, "stats": dict(STATS)}
