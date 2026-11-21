"""v0.999.68 ULTIMATE PC PLAN P0 - the step record of every PC job (docs/HOOLA_ULTIMATE_PC_PLAN.md).

Every action the PC operator takes is written down with the screenshot the model acted on, so a job can be read back
step by step (the exam's evidence now, the replay page in P6, the self-improving builder in P8):

    data/pc_trace/<tenant>/<job id>/meta.json      task, PC kind, started / ended, status, summary, steps
    data/pc_trace/<tenant>/<job id>/steps.jsonl    one line per step: n, t, tool, action, args (masked), window, thought
    data/pc_trace/<tenant>/<job id>/NNN.jpg|png    the screen the model saw when it chose that step

Typed text and every argument are masked (ID / card / bank numbers) before they are written; passwords never reach the
operator, so they cannot be here. Kept: the newest 200 jobs and 14 days per person. Writing never breaks a job: every
failure is swallowed (a step record is evidence, not a dependency)."""
from __future__ import annotations

import json
import logging
import re
import shutil
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.pc.trace")

KEEP_JOBS = 200
KEEP_DAYS = 14
MAX_SHOT = 600_000          # bytes; a bigger frame is skipped (the step line stays)
_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def root() -> Path:
    import os
    return Path(os.environ.get("PC_TRACE_DIR", "data/pc_trace"))


def _dir(tenant: str, job: str) -> Path:
    return root() / _SAFE.sub("_", str(tenant or "default"))[:64] / _SAFE.sub("_", str(job or "job"))[:64]


def _mask(v: Any) -> Any:
    try:
        from ..pii import mask_sensitive
    except Exception:   # noqa: BLE001
        def mask_sensitive(x, mark="######"):  # type: ignore[no-redef]
            return x
    if isinstance(v, str):
        return mask_sensitive(v)[:600]
    if isinstance(v, dict):
        return {str(k)[:40]: _mask(x) for k, x in list(v.items())[:30]}
    if isinstance(v, list):
        return [_mask(x) for x in v[:30]]
    return v


def _ext(b: bytes) -> str:
    return "png" if b[:8] == b"\x89PNG\r\n\x1a\n" else "jpg"


def start(op: Any) -> None:
    try:
        d = _dir(op.tenant, op.id)
        d.mkdir(parents=True, exist_ok=True)
        meta = {"job": op.id, "tenant": op.tenant, "conv": op.conv, "task": _mask(str(op.task or "")),
                "kind": op.kind or "her_pc", "device": getattr(op, "device_id", "") or "",
                "started": int(time.time()), "ended": None, "status": "running", "steps": 0}
        (d / "meta.json").write_text(json.dumps(meta))
        _sweep(op.tenant)
    except Exception:   # noqa: BLE001
        log.debug("trace start failed", exc_info=True)


def step(op: Any, tool: str, args: dict | None) -> None:
    """Called once per action, right before it runs (the frame is the screen the model chose it on)."""
    try:
        d = _dir(op.tenant, op.id)
        if not (d / "meta.json").exists():
            start(op)
        n = int(op.step or 0)
        shot = ""
        frame = getattr(op, "frame", None)
        if frame and len(frame) <= MAX_SHOT:
            shot = f"{n:03d}.{_ext(frame)}"
            (d / shot).write_bytes(frame)
        line = {"n": n, "t": round(time.time(), 2), "tool": str(tool)[:40], "action": str(op.action or "")[:160],
                "args": _mask(dict(args or {})), "window": str(op.window or "")[:160], "shot": shot,
                "brain": str(getattr(op, "brain", "") or "")}
        if getattr(op, "thought_fresh", False) and op.thought:
            line["thought"] = _mask(str(op.thought))[:300]
        with (d / "steps.jsonl").open("a") as fh:
            fh.write(json.dumps(line) + "\n")
    except Exception:   # noqa: BLE001
        log.debug("trace step failed", exc_info=True)


def finish(op: Any) -> None:
    try:
        d = _dir(op.tenant, op.id)
        p = d / "meta.json"
        meta = json.loads(p.read_text()) if p.exists() else {"job": op.id, "tenant": op.tenant}
        meta.update(ended=int(time.time()), status=str(op.status or ""), steps=int(op.step or 0),
                    summary=_mask(str(op.summary or op.reason or ""))[:600])
        if getattr(op, "frame", None) and len(op.frame) <= MAX_SHOT:
            meta["final_shot"] = f"end.{_ext(op.frame)}"
            (d / meta["final_shot"]).write_bytes(op.frame)
        d.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(meta))
    except Exception:   # noqa: BLE001
        log.debug("trace finish failed", exc_info=True)


def _sweep(tenant: str) -> None:
    base = root() / _SAFE.sub("_", str(tenant or "default"))[:64]
    if not base.is_dir():
        return
    jobs = sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    cut = time.time() - KEEP_DAYS * 86400
    for i, p in enumerate(jobs):
        if i >= KEEP_JOBS or p.stat().st_mtime < cut:
            shutil.rmtree(p, ignore_errors=True)


# ---------------------------------------------------------------- reading
def jobs(tenant: str, limit: int = 50) -> list[dict]:
    base = root() / _SAFE.sub("_", str(tenant or "default"))[:64]
    out = []
    if base.is_dir():
        for p in sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                out.append(json.loads((p / "meta.json").read_text()))
            except Exception:   # noqa: BLE001
                continue
    return out


def read(tenant: str, job: str) -> dict | None:
    d = _dir(tenant, job)
    if not (d / "meta.json").exists():
        return None
    meta = json.loads((d / "meta.json").read_text())
    steps = []
    if (d / "steps.jsonl").exists():
        for ln in (d / "steps.jsonl").read_text().splitlines():
            try:
                steps.append(json.loads(ln))
            except Exception:   # noqa: BLE001
                continue
    return {**meta, "steps_list": steps}


def shot_path(tenant: str, job: str, name: str) -> Path | None:
    if not re.fullmatch(r"(\d{3}|end)\.(jpg|png)", name or ""):
        return None
    p = _dir(tenant, job) / name
    return p if p.is_file() else None


def mount(app, current_tenant, require_key) -> None:
    from fastapi import APIRouter, Depends, HTTPException
    from fastapi.responses import FileResponse

    r = APIRouter(prefix="/api/pc/trace", dependencies=[Depends(require_key)])

    @r.get("")
    def t_list(limit: int = 50, tenant: str = Depends(current_tenant)):
        return {"jobs": jobs(tenant, max(1, min(int(limit), 200)))}

    @r.get("/{job}")
    def t_one(job: str, tenant: str = Depends(current_tenant)):
        out = read(tenant, job)
        if out is None:
            raise HTTPException(404, "Not found.")
        return out

    @r.get("/{job}/{name}")
    def t_shot(job: str, name: str, tenant: str = Depends(current_tenant)):
        p = shot_path(tenant, job, name)
        if p is None:
            raise HTTPException(404, "Not found.")
        return FileResponse(p, media_type="image/png" if name.endswith(".png") else "image/jpeg",
                            headers={"Cache-Control": "private, max-age=86400"})

    app.include_router(r)
