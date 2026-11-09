"""v0.718 SEEKH MANCH ON THE CONSOLE - the HOOLA AI Video Learner panel's own lane (/api/seekh/console/*).

Owner (2026-11-09, verbatim): "NOW WE WILL DEVELOP A CONSOLE PAGE FOR IT - CHECK THE EXISTING CONSOLE DESIGN
AND IN AI EMPLOYEE SECTION BUILD THE HOOLA AI VIDEO LEARNER. In that, a panel where user can load a video and
HOOLA AI will see this and note in REALTIME. Once done, HOOLA AI will prepare a MEMORY for this. And IN THIS
PAGE ONLY user will tell HOOLA to PERFORM THIS TASK NOW - then HOOLA will use HIS BROWSER for doing that task."

The lane is thin on purpose: the watching, the two memories and the recipe replay are v0.713's organs
(server/app/seekh.py + procedures + operator recipe box) - this file only runs them as a pollable JOB so the
panel can show live progress, and lists what was learned. PERFORM is NOT an endpoint: the panel composes one
honest chat turn (the same /api/conversations/{id}/messages the composer uses), so the task runs through the
agent - the computer operator reads the draft recipe at job start and drives its own browser.

Laws (tested in test_v0716_seekh_console.py):
  THIN     no second brain: every stage shown is a real boundary of seekh.watch (on_stage), never a guess;
  OWNERS   the lane is key-protected and tenant-scoped; a job is only ever read by its own tenant;
  ONE      one watch at a time per tenant (409 carries the running id, the panel adopts it);
  HONEST   an error is the error; a lost job id (restart) says so; nothing is faked as done;
  MEMORY   in-process only: a restart drops the jobs (the LEARNED kaam lives in the two real memories).
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import OrderedDict
from typing import Any, Callable

from fastapi import APIRouter, Body, Depends, HTTPException

log = logging.getLogger("santosh.seekh_console")

MAX_JOBS = 50            # in-memory ring; done jobs older than this are dropped
JOB_TTL_S = 3600         # a done job's progress stays answerable for an hour

_JOBS: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_LOCK = threading.Lock()

# what the panel shows, in order - every entry is a real on_stage boundary of seekh.watch
STAGES = ["classify", "fetch", "notes", "distill_start", "distill", "memory", "done"]


def _now() -> float:
    return time.time()


def _snapshot(job: dict[str, Any]) -> dict[str, Any]:
    """What a poll may see - plain values only, safe to hand to JSON while the thread writes the next field."""
    stages = [{"k": s, "ts": round(t, 1)} for s, t in job["stages"]]
    return {"id": job["id"], "stage": job["stage"], "stages": stages, "title": job.get("title", ""),
            "perception": job.get("perception", ""), "done": bool(job.get("done")),
            "error": job.get("error", ""), "elapsed": round(_now() - job["started"], 1),
            "started": job["started_iso"], "result": job.get("result")}


def _prune() -> None:
    with _LOCK:
        for jid in [j for j, job in _JOBS.items()
                    if job.get("done") and _now() - job.get("ended", _now()) > JOB_TTL_S]:
            _JOBS.pop(jid, None)
        while len(_JOBS) > MAX_JOBS:                       # oldest first, running jobs last to go
            for jid, job in _JOBS.items():
                if job.get("done"):
                    _JOBS.pop(jid)
                    break
            else:
                break


def _running_for(tenant: str) -> str:
    """The tenant's live job id, if any (a done/error job never blocks a new watch)."""
    with _LOCK:
        for jid, job in reversed(_JOBS.items()):
            if job["tenant"] == tenant and not job.get("done"):
                return jid
    return ""


def _start(tenant: str, ref: str, title: str) -> str:
    from . import seekh
    jid = uuid.uuid4().hex[:16]
    job: dict[str, Any] = {"id": jid, "tenant": tenant, "stage": "queue", "stages": [],
                           "started": _now(), "started_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "title": str(title or ""), "perception": "", "done": False,
                           "error": "", "result": None, "ended": 0.0}

    def on_stage(stage: str, data: dict[str, Any]) -> None:
        with _LOCK:
            job["stages"].append((stage, _now() - job["started"]))
            job["stage"] = stage
            if stage == "classify":
                job["kind"] = str(data.get("kind") or "")
            if stage == "notes":
                job["perception"] = str(data.get("perception") or "")
            if stage == "distill" and not job.get("title"):
                job["title"] = str(data.get("title") or "")
            if stage == "memory":
                job["memory"] = {"procedure_id": data.get("procedure_id"), "recipe": data.get("recipe", "")}

    def run() -> None:
        try:
            out = seekh.watch(tenant, ref, title, "owner", on_stage=on_stage)
            with _LOCK:
                job["result"] = out
                job["done"] = True
                job["ended"] = _now()
        except Exception as e:                              # noqa: BLE001 - SeekhError and the honest rest
            with _LOCK:
                job["error"] = str(e) or e.__class__.__name__
                job["stage"] = "error"
                job["done"] = True
                job["ended"] = _now()
            log.warning("seekh console job %s failed: %s", jid, e)

    with _LOCK:
        _JOBS[jid] = job
    threading.Thread(target=run, name=f"seekh-{jid}", daemon=True).start()
    _prune()
    return jid


def make_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/seekh/console", dependencies=[Depends(require_key)])

    @r.get("/watches")
    async def watches(tenant: str = Depends(current_tenant)):
        """The memory list: what was learned from which video, newest first (seekh's own sidecar)."""
        from . import seekh
        from .config import get_settings
        st = get_settings()
        out = seekh.listing(tenant)
        today = time.strftime("%Y-%m-%d")
        return {**out, "enabled": bool(st.seekh_enabled), "max_per_day": int(st.seekh_max_per_day),
                "today": sum(1 for w in out["watches"] if str(w.get("day", "")) == today),
                "running": _running_for(tenant)}

    @r.post("/watch")
    async def watch(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Start one watch-and-learn job. The panel then polls /progress?id= for the live stages."""
        b = dict(body or {})
        ref = str(b.get("video") or "").strip()
        title = str(b.get("title") or "").strip()
        if not ref:
            raise HTTPException(422, "Kaunsa video? YouTube ka link, attach kiye video ka file_id, ya direct video URL dijiye.")
        from . import seekh
        from .config import get_settings
        if not get_settings().seekh_enabled:
            raise HTTPException(403, "Video se seekhna abhi band hai.")
        running = _running_for(tenant)
        if running:
            return {"id": running, "already_running": True}   # 200: the panel adopts the live job
        try:                                                # classify BEFORE the thread: junk is told at once
            kind, key = seekh._classify(ref)
        except seekh.SeekhError as e:
            raise HTTPException(422, str(e))
        jid = _start(tenant, ref, title)
        return {"id": jid, "kind": kind, "already_running": False}

    @r.get("/progress")
    async def progress(id: str = "", tenant: str = Depends(current_tenant)):
        """The live state of one watch job - the panel's 1.2 s pulse."""
        jid = str(id or "").strip()
        with _LOCK:
            job = _JOBS.get(jid)
            if not job or job["tenant"] != tenant:
                job = None
                mine = [j for j in _JOBS.values() if j["tenant"] == tenant and not j.get("done")]
                if len(mine) == 1:                           # a page reload mid-watch: adopt the running job
                    job = mine[0]
        if job is None:
            raise HTTPException(404, "Yeh watch nahi mila (server restart hua hoga). Naya try kijiye - jo seekh liya tha woh memory mein hai.")
        return _snapshot(job)

    return r
