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

v0.785: a running watch now SURVIVES A RESTART. Every job keeps a small record on disk beside the sidecar
(data/seekh/jobs/<id>.json: its stage, its notes so far, a heartbeat). A record whose heartbeat went quiet and
that no live process owns is picked up again - once - from the start of the video; a second loss is said plainly
and kept on her list as a failure with Try again. The same record lets any worker process answer the page's
poll. The page's run ("Do it now") is kept on the task row, so leaving the page loses nothing.

Laws (tested in test_v0716_seekh_console.py):
  THIN     no second brain: every stage shown is a real boundary of seekh.watch (on_stage), never a guess;
  OWNERS   the lane is key-protected and tenant-scoped; a job is only ever read by its own tenant;
  ONE      one watch at a time per tenant (409 carries the running id, the panel adopts it);
  HONEST   an error is the error; a lost job id (restart) says so; nothing is faked as done;
  MEMORY   the job record on disk is progress only (the LEARNED kaam lives in the two real memories).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Body, Depends, HTTPException

log = logging.getLogger("santosh.seekh_console")

MAX_JOBS = 50            # in-memory ring; done jobs older than this are dropped
JOB_TTL_S = 3600         # a done job's progress stays answerable for an hour
BEAT_S = 5.0             # v0.785 a live job stamps its disk record this often
STALE_S = 30.0           # a record this quiet, owned by no live process, is a watch the restart cut
MAX_STARTS = 2           # the first start + one pick-up after a restart
BOOT = uuid.uuid4().hex[:10]   # this process's own mark on the records it writes

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
            "error": job.get("error", ""), "elapsed": round((job.get("ended") or _now()) - job["started"], 1),
            "started": job["started_iso"], "result": job.get("result"), "ref": job.get("ref", ""),
            "kind": job.get("kind", ""), "stopped": bool(job.get("stopped")),
            "resumed": bool(job.get("resumed")), "replace": job.get("replace", ""),
            "first_note": job.get("first_note") or 0}


# ---------------------------------------------------------------- v0.785 the job's record on disk
def _jobs_dir() -> Path:
    from . import seekh
    p = seekh._dir() / "jobs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_id(jid: str) -> str:
    return "".join(c for c in str(jid or "") if c.isalnum())[:40]


def _path(jid: str) -> Path:
    return _jobs_dir() / f"{_safe_id(jid)}.json"


def _persist(job: dict[str, Any], force: bool = False) -> None:
    """Write the job's record (throttled to one write a second unless forced). Never raises."""
    try:
        if not force and _now() - float(job.get("_wrote") or 0) < 1.0:
            return
        job["_wrote"] = _now()
        with _LOCK:
            rec = {**_snapshot(job), "tenant": job["tenant"], "started_ts": job["started"],
                   "ended": job.get("ended") or 0, "pid": os.getpid(), "boot": BOOT, "beat": _now(),
                   "starts": int(job.get("starts") or 1)}
        p = _path(job["id"])
        tmp = p.with_suffix(f".{BOOT}.tmp")
        tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)
    except Exception:                                       # noqa: BLE001 - a record is progress, never the work
        log.exception("seekh job record")


def _disk(jid: str) -> dict[str, Any] | None:
    try:
        p = _path(jid)
        if not _safe_id(jid) or not p.is_file():
            return None
        v = json.loads(p.read_text(encoding="utf-8"))
        return v if isinstance(v, dict) and v.get("id") else None
    except Exception:                                       # noqa: BLE001
        return None


def _disk_all() -> list[dict[str, Any]]:
    out = []
    try:
        for p in sorted(_jobs_dir().glob("*.json")):
            try:
                v = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(v, dict) and v.get("id"):
                    out.append(v)
            except Exception:                               # noqa: BLE001
                continue
    except Exception:                                       # noqa: BLE001
        pass
    return out


def _mine(rec: dict[str, Any]) -> bool:
    """A record this very process wrote. If its job is not in memory any more it was dropped here on purpose
    (pruned, or a test cleared the ring) - never something to pick up."""
    return rec.get("boot") == BOOT and int(rec.get("pid") or 0) == os.getpid()


def _lost(rec: dict[str, Any]) -> bool:
    return (not rec.get("done")) and (not _mine(rec)) and _now() - float(rec.get("beat") or 0) > STALE_S


def _resume_on() -> bool:
    from .config import get_settings
    return bool(getattr(get_settings(), "seekh_resume", True))


def _disk_view(rec: dict[str, Any]) -> dict[str, Any]:
    """A poll answered from the record (another worker runs the job, or it finished before a restart)."""
    out = {k: rec.get(k) for k in ("id", "stage", "stages", "title", "perception", "done", "error", "started",
                                   "result", "ref", "kind", "stopped", "resumed", "replace", "first_note")}
    end = float(rec.get("ended") or 0) or _now()
    out["elapsed"] = round(max(0.0, end - float(rec.get("started_ts") or end)), 1)
    return out


def _claim(jid: str, n: int) -> bool:
    """Only one process picks a lost watch up: the one that creates this file."""
    try:
        fd = os.open(str(_jobs_dir() / f"{_safe_id(jid)}.claim{n}"), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except Exception:                                       # noqa: BLE001
        return False


def _recover(rec: dict[str, Any]) -> str:
    """A watch the restart cut: start it again once (same id, so the page's poll simply carries on); a second
    loss is recorded as a failure she can retry. Returns the id when it runs again."""
    jid, tenant = str(rec["id"]), str(rec.get("tenant") or "")
    with _LOCK:
        if jid in _JOBS:
            return jid
    if not _resume_on():
        return ""
    starts = int(rec.get("starts") or 1)
    if not _claim(jid, starts + 1):
        return ""
    if starts >= MAX_STARTS:
        why = "The server restarted while Hoola was watching this video, twice. Please start it again."
        try:
            from . import seekh
            seekh.record_failure(tenant, str(rec.get("ref") or ""), str(rec.get("title") or ""), why,
                                 replace=str(rec.get("replace") or ""))
        except Exception:                                   # noqa: BLE001
            log.exception("seekh lost job failure row")
        rec.update({"done": True, "error": why, "stage": "error", "ended": _now(), "beat": _now()})
        try:
            _path(jid).write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        except Exception:                                   # noqa: BLE001
            pass
        return ""
    log.warning("seekh: picking up watch %s after a restart (start %d)", jid, starts + 1)
    return _start(tenant, str(rec.get("ref") or ""), str(rec.get("title") or ""), jid=jid, starts=starts + 1,
                  replace=str(rec.get("replace") or ""), resumed=True)


def recover_all() -> int:
    """Startup sweep: every watch a restart cut is picked up without anyone having to open the page."""
    n = 0
    for rec in _disk_all():
        try:
            if _lost(rec) and _recover(rec):
                n += 1
        except Exception:                                   # noqa: BLE001
            log.exception("seekh recover")
    return n


def recover_later(delay_s: float = STALE_S + 15) -> None:
    """Called once at server start: wait until a cut watch's heartbeat is clearly quiet, then sweep."""
    t = threading.Timer(delay_s, lambda: recover_all())
    t.daemon = True
    t.start()


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
    try:                                                    # the records of long-finished jobs go too
        d = _jobs_dir()
        for rec in _disk_all():
            if rec.get("done") and _now() - float(rec.get("ended") or rec.get("beat") or 0) > JOB_TTL_S:
                for f in d.glob(f"{_safe_id(rec['id'])}.*"):
                    f.unlink(missing_ok=True)
    except Exception:                                       # noqa: BLE001
        pass


def _running_for(tenant: str) -> str:
    """The tenant's live job id, if any (a done/error job never blocks a new watch). Memory first; then the
    records: another worker's live job, or a cut one that is picked up right here."""
    with _LOCK:
        for jid, job in reversed(_JOBS.items()):
            if job["tenant"] == tenant and not job.get("done"):
                return jid
    for rec in _disk_all():
        if rec.get("tenant") != tenant or rec.get("done") or _mine(rec):
            continue
        if _lost(rec):
            got = _recover(rec)
            if got:
                return got
            continue
        return str(rec["id"])
    return ""


def _start(tenant: str, ref: str, title: str, jid: str = "", starts: int = 1, replace: str = "",
           resumed: bool = False) -> str:
    from . import seekh
    jid = jid or uuid.uuid4().hex[:16]
    job: dict[str, Any] = {"id": jid, "tenant": tenant, "stage": "queue", "stages": [],
                           "started": _now(), "started_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "title": str(title or ""), "perception": "", "done": False,
                           "error": "", "result": None, "ended": 0.0, "ref": str(ref or ""),
                           "cancel": threading.Event(), "stopped": False, "starts": int(starts),
                           "replace": str(replace or ""), "resumed": bool(resumed)}
    stop_flag = _jobs_dir() / f"{_safe_id(jid)}.stop"

    def on_stage(stage: str, data: dict[str, Any]) -> None:
        if stage == "partial":                             # v0.745 live notes: text only, never a stage row
            with _LOCK:
                job["perception"] = str(data.get("perception") or "")
                if not job.get("first_note") and job["perception"]:
                    job["first_note"] = max(0.1, round(_now() - job["started"], 1))   # v0.785 when the first words arrived
            _persist(job)
            return
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
        _persist(job, force=True)

    def beat() -> None:
        """The heartbeat: keeps the record fresh through the long quiet stretches, and hears a Stop pressed on
        another worker (a flag file)."""
        while not job.get("done"):
            time.sleep(BEAT_S)
            if job.get("done"):
                break
            try:
                if stop_flag.exists():
                    job["cancel"].set()
            except Exception:                               # noqa: BLE001
                pass
            _persist(job, force=True)

    def run() -> None:
        try:
            out = seekh.watch(tenant, ref, title, "owner", on_stage=on_stage, cancel=job["cancel"],
                              replace=job["replace"])
            with _LOCK:
                job["result"] = out
                job["done"] = True
                job["ended"] = _now()
        except Exception as e:                              # noqa: BLE001 - SeekhError and the honest rest
            stopped = isinstance(e, seekh.SeekhStopped)
            if not stopped:                                 # v0.745 a failed watch stays on her list with its reason
                try:
                    seekh.record_failure(tenant, ref, job.get("title", ""), str(e) or e.__class__.__name__,
                                         media=getattr(e, "media", None), replace=job["replace"])
                except Exception:                           # noqa: BLE001
                    log.exception("seekh failure row")
            with _LOCK:
                job["stopped"] = stopped
                job["error"] = str(e) or e.__class__.__name__
                job["stage"] = "error"
                job["done"] = True
                job["ended"] = _now()
            log.warning("seekh console job %s failed: %s", jid, e)
        finally:
            _persist(job, force=True)
            try:
                stop_flag.unlink(missing_ok=True)
            except Exception:                               # noqa: BLE001
                pass

    with _LOCK:
        _JOBS[jid] = job
    _persist(job, force=True)
    threading.Thread(target=run, name=f"seekh-{jid}", daemon=True).start()
    threading.Thread(target=beat, name=f"seekh-beat-{jid}", daemon=True).start()
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
        out = seekh.listing(tenant, limit=seekh.MAX_SIDECAR)
        today = time.strftime("%Y-%m-%d")
        rows = out["watches"]
        learned = [w for w in rows if w.get("status") != "failed"]
        return {**out, "enabled": bool(st.seekh_enabled), "max_per_day": int(st.seekh_max_per_day),
                "today": sum(1 for w in learned if str(w.get("day", "")) == today),
                "counts": {"learned": len(learned), "proven": sum(1 for w in learned if int(w.get("wins") or 0) > 0),
                           "steps": sum(int(w.get("steps") or 0) for w in learned),
                           "runs": sum(int(w.get("wins") or 0) + int(w.get("fails") or 0) for w in learned)},
                "running": _running_for(tenant)}

    @r.post("/watch")
    async def watch(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Start one watch-and-learn job. The panel then polls /progress?id= for the live stages.
        v0.785 `replace` = the row this watch re-learns (Re-learn / Try again): it takes that row's place."""
        b = dict(body or {})
        ref = str(b.get("video") or "").strip()
        title = str(b.get("title") or "").strip()
        replace = str(b.get("replace") or "").strip()[:80]
        if not ref:
            raise HTTPException(422, "Which video? Give a YouTube link, a video file you attached, or a direct video URL.")
        from . import seekh
        from .config import get_settings
        if not get_settings().seekh_enabled:
            raise HTTPException(403, "Learning from videos is switched off on this server.")
        running = _running_for(tenant)
        if running:
            return {"id": running, "already_running": True}   # 200: the panel adopts the live job
        try:                                                # classify BEFORE the thread: junk is told at once
            kind, key = seekh._classify(ref)
            if kind == "kept":
                seekh.media_file(tenant, key)               # a copy that is gone is said now, not after a wait
        except seekh.SeekhError as e:
            raise HTTPException(422, str(e))
        jid = _start(tenant, ref, title, replace=replace)
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
            if job is not None:
                return _snapshot(job)
        rec = _disk(jid) if jid else None                   # v0.785 not in this process: the record answers
        if rec and rec.get("tenant") == tenant and (rec.get("done") or not _mine(rec)):
            if _lost(rec):
                got = _recover(rec)
                with _LOCK:
                    job = _JOBS.get(got) if got else None
                    if job is not None:
                        return _snapshot(job)
                rec = _disk(jid) or rec
            return _disk_view(rec)
        other = _running_for(tenant)                         # a reload mid-watch on another worker / after a restart
        if other:
            with _LOCK:
                job = _JOBS.get(other)
                if job is not None:
                    return _snapshot(job)
            rec = _disk(other)
            if rec:
                return _disk_view(rec)
        raise HTTPException(404, "This watch was not found (the server probably restarted). Start it again - anything already learned is kept.")

    @r.post("/stop")
    async def stop(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """v0.745 Stop a running watch: the pipeline stops at the next chunk / stage and keeps nothing."""
        jid = str((body or {}).get("id") or "").strip()
        with _LOCK:
            job = _JOBS.get(jid)
            if job and job["tenant"] == tenant:
                if not job.get("done"):
                    job["cancel"].set()
                return {"ok": True}
        rec = _disk(jid)                                     # the job runs on another worker: leave it a flag
        if rec and rec.get("tenant") == tenant and not rec.get("done") and not _mine(rec):
            (_jobs_dir() / f"{_safe_id(jid)}.stop").write_text("1", encoding="utf-8")
            return {"ok": True}
        raise HTTPException(404, "This watch is not running.")

    @r.get("/task")
    async def task(id: str = "", tenant: str = Depends(current_tenant)):
        """v0.745 one learned task: steps with their video moments, what it needs, how it went."""
        from . import seekh
        try:
            return seekh.task(tenant, str(id or ""))
        except seekh.SeekhError as e:
            raise HTTPException(404, str(e))

    @r.delete("/task")
    async def forget(id: str = "", tenant: str = Depends(current_tenant)):
        """v0.745 Remove: the list row, its learned procedure and a never-run recipe draft."""
        from . import seekh
        try:
            return {"ok": seekh.forget(tenant, str(id or ""))}
        except seekh.SeekhError as e:
            raise HTTPException(404, str(e))

    @r.get("/media")
    async def media(id: str = "", tenant: str = Depends(current_tenant)):
        """v0.785 the learner's own copy of an uploaded video (the chat file lane is swept after 24 hours)."""
        from fastapi.responses import FileResponse
        from . import seekh
        try:
            p, mime, _name = seekh.media_file(tenant, str(id or ""))
        except seekh.SeekhError as e:
            raise HTTPException(404, str(e))
        return FileResponse(str(p), media_type=mime, headers={
            "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; media-src 'self'"})

    @r.post("/run")
    async def run_start(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """v0.785 Do it now was sent as a chat turn: remember which chat carries the run (the page comes back to
        it after a reload, and the list shows it)."""
        from . import seekh
        b = dict(body or {})
        try:
            row = seekh.run_start(tenant, str(b.get("id") or ""), str(b.get("conversation_id") or ""),
                                  int(b.get("after") or 0))
        except (seekh.SeekhError, ValueError) as e:
            raise HTTPException(404, str(e))
        return {"ok": True, "run": row.get("run")}

    @r.get("/run")
    async def run_view(id: str = "", tenant: str = Depends(current_tenant)):
        """v0.785 the open run of one task + the cards of its chat that wait for her right now."""
        from . import seekh
        try:
            return seekh.run_view(tenant, str(id or ""))
        except seekh.SeekhError as e:
            raise HTTPException(404, str(e))

    @r.post("/proven")
    async def proven(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """v0.745 her answer after a run: {id, ok}. Worked = Proven; wrong = noted. v0.785 {skip: true} closes
        the run without an answer."""
        from . import seekh
        b = dict(body or {})
        try:
            return seekh.mark(tenant, str(b.get("id") or ""), bool(b.get("ok")), skip=bool(b.get("skip")))
        except seekh.SeekhError as e:
            raise HTTPException(404, str(e))

    return r
