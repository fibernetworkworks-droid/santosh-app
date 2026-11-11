"""v0.655 KAAM DIKHE: the step log of a website job, shown live in the Web Studio like Lovable shows its work.

Every real stage of a build (pictures, art directions, sections, screenshots, checks, fixes) records one step with the
time it started and the time it ended; a step that counts (sections 7 of 18) carries done / total. The log is a small
JSON file beside the site's files, written under a lock, so the looks' worker threads and the API read the same thing.
Nothing here is estimated: a step's time is the clock between two real calls, and a step still running has no end.
A new job starts a fresh log when the last one ended more than RUN_GAP seconds ago.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

from . import build as B

log = logging.getLogger(__name__)
_LOCK = threading.Lock()
RUN_GAP = 600          # a step after 10 quiet minutes starts a new job's log
MAX_STEPS = 60

# the build's own step lines are Hinglish (they also go to her chat); the Studio's chrome is English
EN = {
    "Planning three designs": "Planning three designs",
    "Writing the top of every look": "Writing the top of every look",
    "Pick a look": "Three looks ready: pick one",
    "Writing every page for the looks": "Writing every page for the looks",
    "Making photos for your business": "Making photos for your business",
    "Making the design kit": "Making the design kit",
    "Running checks": "Checking speed, phone view, contrast and links",
    "Fixing what the checks found": "Fixing what the checks found",
    "Website ready": "Website ready",
    "Paused": "Paused",
    "Stopped with a problem": "Stopped with a problem",
    "The looks could not be made": "The looks could not be made",
    "The build hit a problem": "The build hit a problem",
    "Some things were not found": "Some things were not found",
    "Reviewing my own work and improving it": "Reviewing my own work and improving it",
}


def _path(tenant: str, site_id: str) -> Path:
    return B.site_dir(tenant, site_id) / "activity.json"


def _read(p: Path) -> dict[str, Any]:
    try:
        d = json.loads(p.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _write(p: Path, d: dict[str, Any]) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False))
    tmp.replace(p)


def _en(label: str) -> str:
    return EN.get(label, label)


def _num(note: str) -> str:
    m = re.search(r"\d+", note or "")
    return m.group(0) if m else ""


# the English note for a known step (the Hinglish one goes to her chat); "" = no note for that step
NOTE_EN = {
    "Planning three designs": lambda n: f"{_num(n)} designs at once" if _num(n) else "",
    "Making photos for your business": lambda n: f"{_num(n)} photos" if _num(n) else "",
    "Making the design kit": lambda n: "buttons, cards and headings, the same on every page",
    "Running checks": lambda n: "speed · phone view · contrast · links",
    "Fixing what the checks found": lambda n: f"{_num(n)} parts" if _num(n) else "",
    "Paused": lambda n: "paused when you asked",
    "Pick a look": lambda n: "",
}


def note_en(label: str, note: str) -> str:
    """The note to show beside a step: English for the build's own Hinglish lines, the text itself otherwise."""
    f = NOTE_EN.get(label)
    if f:
        return f(note or "")
    return "" if label in EN and label not in ("Website ready",) and re.search(r"\b(raha|rahi|hai|hain|ke|ki|ka|ek)\b", note or "") else (note or "")


def _close_running(steps: list[dict], t: float, state: str = "done") -> None:
    for s in steps:
        if s.get("state") == "run":
            s["state"], s["end"] = state, t


def _fresh(d: dict[str, Any], t: float) -> dict[str, Any]:
    steps = d.get("steps") or []
    running = any(s.get("state") == "run" for s in steps)
    last = max([s.get("end") or s.get("at") or 0 for s in steps] or [0])
    if not steps or (not running and t - last > RUN_GAP) or d.get("closed"):
        return {"started": t, "steps": []}
    return d


def step(tenant: str, site_id: str, label: str, note: str = "", key: str = "", done: int | None = None,
         total: int | None = None, alongside: bool = False) -> None:
    """Start a step (the running one ends now), or update the running step with the same key (a count moving).
    alongside=True: a step that runs beside the others (the photos during the art directions) and ends nothing."""
    try:
        t = time.time()
        p = _path(tenant, site_id)
        with _LOCK:
            d = _fresh(_read(p), t)
            steps = d["steps"]
            cur = next((s for s in reversed(steps) if key and s.get("key") == key and s.get("state") == "run"), None)
            if cur is None:
                if not alongside:
                    _close_running(steps, t)
                cur = {"label": _en(label)[:120], "key": key, "at": t, "state": "run"}
                steps.append(cur)
            if note:
                cur["note"] = str(note)[:160]
            if done is not None:
                cur["done"] = int(done)
            if total is not None:
                cur["total"] = int(total)
            d["steps"] = steps[-MAX_STEPS:]
            d["updated"] = t
            _write(p, d)
    except Exception:
        log.info("activity step not written", exc_info=True)


def end(tenant: str, site_id: str, label: str = "", note: str = "", state: str = "done") -> None:
    """The job is over (done / waiting for her / error / paused): every running step ends; the end itself is a step."""
    try:
        t = time.time()
        p = _path(tenant, site_id)
        with _LOCK:
            d = _read(p)
            if not d.get("steps"):
                return
            steps = d["steps"]
            _close_running(steps, t, "error" if state == "error" else "done")
            if label:
                steps.append({"label": _en(label)[:120], "note": str(note)[:160], "at": t, "end": t,
                              "state": "error" if state == "error" else "done", "final": True})
            d["steps"], d["closed"], d["updated"], d["ended"] = steps[-MAX_STEPS:], True, t, t
            _write(p, d)
    except Exception:
        log.info("activity end not written", exc_info=True)


def read(tenant: str, site_id: str) -> dict[str, Any]:
    """What the Studio draws: the steps, when the job started, and the server's clock (the screen corrects its own)."""
    d = _read(_path(tenant, site_id))
    return {"started": d.get("started"), "ended": d.get("ended"), "steps": d.get("steps") or [], "now": time.time()}
