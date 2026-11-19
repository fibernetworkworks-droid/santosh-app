"""v0.693 APP STUDIO: the step log of an app job, shown live in the App Studio (the Web Studio's KAAM DIKHE, for apps).

Every real stage of an app job (looks, each screen designed, checks, fixes, Kotlin per screen, compile rounds, the device
check, the iPhone build, TestFlight) records one step with the time it started and the time it ended; a step that counts
(screen 7 of 11) carries done / total. The log is a small JSON file in the app's own folder, written under a lock, so the
design / build worker threads and the API read the same thing. Nothing is estimated: a step's time is the clock between
two real calls, and a running step has no end. A new job starts a fresh log when the last one ended over RUN_GAP ago.

The engine's own progress lines are Hinglish (they also go to her chat); the Studio's chrome is English, so every known
line is turned into English here. The hooks are fail-open: a log that cannot be written never touches the job.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.app")
_LOCK = threading.Lock()
RUN_GAP = 600
MAX_STEPS = 80

_HINGLISH = re.compile(r"\b(raha|rahi|rahe|hai|hain|ho|kar|ke|ki|ka|ek|mein|par|nahi|taiyaar|pehle|wala|wali)\b", re.I)

# fixed lines -> English
EN = {
    "Design ki jaanch (Opus)": "Reviewing the design",
    "Look chuniye": "Three looks ready: pick one",
    "Looks nahi bane": "The looks could not be made",
    "App design mein dikkat": "The design hit a problem",
    "Rok diya": "Paused",
    "Jaanch chal rahi hai": "Checking every screen",
    "Theek kar raha hoon": "Fixing what the checks found",
    "App design taiyaar": "App design ready",
    "Design pakka": "Design approved",
    "Screens Kotlin mein likh raha hoon": "Writing every screen in Kotlin",
    "Android Studio ki tarah compile ho raha hai": "Compiling the Android app",
    "TestFlight par bhej raha hoon (Apple ka signing + upload)": "Sending to TestFlight",
}
# patterned lines -> (English label, note, step key)
_PAT = [
    (re.compile(r"^Kotlin: (.+) \((\d+)/(\d+)\)$"), lambda m: ("Writing Kotlin for every screen", m.group(1), "kotlin")),
    (re.compile(r"^Swift(?:UI)?: (.+) \((\d+)/(\d+)\)$"), lambda m: ("Writing SwiftUI for every screen", m.group(1), "swift")),
    (re.compile(r"^(?:Compile ki galtiyan theek|Fixing compile errors): round (\d+)"), lambda m: ("Fixing compile errors", f"round {m.group(1)}", "")),
    (re.compile(r"^Device check: (.+?) crash"), lambda m: ("Fixing crashes found on the phone check", m.group(1), "")),
    (re.compile(r"^Simulator check: (.+?) crash"), lambda m: ("Fixing crashes found on the iPhone check", m.group(1), "")),
    (re.compile(r"^Build (\d+) (?:wapas la rahi hoon|is coming back)"), lambda m: (f"Bringing back build {m.group(1)}", "", "")),
    (re.compile(r"^(?:Theek kar raha hoon|Fixing a screen that did not compile): (.+)$"), lambda m: ("Fixing a screen that did not compile", m.group(1), "")),
    (re.compile(r"^Look (\d+): (.+)$"), lambda m: (f"Look {m.group(1)}: {m.group(2)}", "", f"look{m.group(1)}")),
]


def english(label: str, note: str = "") -> tuple[str, str, str, int | None, int | None]:
    """(label, note, key, done, total) in English for one of the engine's progress lines."""
    label = re.sub(r"\s+", " ", str(label or "")).strip()
    note = re.sub(r"\s+", " ", str(note or "")).strip()
    if label in EN:
        n = "" if _HINGLISH.search(note) else note
        return EN[label], n, "", None, None
    for rx, f in _PAT:
        m = rx.search(label)
        if m:
            lab, n, key = f(m)
            nums = re.search(r"\((\d+)/(\d+)\)$", label)
            if nums:
                return lab, n, key, int(nums.group(1)), int(nums.group(2))
            return lab, n, key, None, None
    return label, ("" if _HINGLISH.search(note) else note), "", None, None


def _path(tenant: str, app_id: str) -> Path:
    from . import kit as K
    return K.app_dir(tenant, app_id) / "activity.json"


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


def _close_running(steps: list[dict], t: float, state: str = "done") -> None:
    for s in steps:
        if s.get("state") == "run":
            s["state"], s["end"] = state, t


def _fresh(d: dict[str, Any], t: float) -> dict[str, Any]:
    steps = d.get("steps") or []
    running = any(s.get("state") == "run" for s in steps)
    last = max([s.get("end") or s.get("at") or 0 for s in steps] or [0])
    if not steps or (not running and t - last > RUN_GAP) or d.get("closed"):
        return {"started": t, "steps": [], "job": d.get("next_job") or ""}
    return d


def step(tenant: str, app_id: str, label: str, note: str = "", key: str = "", done: int | None = None,
         total: int | None = None, job: str = "") -> None:
    """Start a step (the running one ends now), or update the running step with the same key (a count moving)."""
    try:
        if not tenant or not app_id or not label:
            return
        t = time.time()
        p = _path(tenant, app_id)
        with _LOCK:
            d = _fresh(_read(p), t)
            if job and not d.get("job"):
                d["job"] = job
            steps = d["steps"]
            cur = next((s for s in reversed(steps) if key and s.get("key") == key and s.get("state") == "run"), None)
            if cur is None:
                last = steps[-1] if steps else None
                if last and last.get("state") == "run" and last.get("label") == label[:120] and not key:
                    cur = last                                  # the same line said again: one step, not two
                else:
                    _close_running(steps, t)
                    cur = {"label": label[:120], "key": key, "at": t, "state": "run"}
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
        log.info("app activity step not written", exc_info=True)


def end(tenant: str, app_id: str, label: str = "", note: str = "", state: str = "done") -> None:
    """The job is over (done / waiting for her / error / paused): every running step ends; the end itself is a step."""
    try:
        t = time.time()
        p = _path(tenant, app_id)
        with _LOCK:
            d = _read(p)
            if not d.get("steps") or d.get("closed"):
                return
            steps = d["steps"]
            bad = state == "error"
            _close_running(steps, t, "error" if bad else "done")
            if label:
                steps.append({"label": str(label)[:120], "note": str(note)[:160], "at": t, "end": t,
                              "state": "error" if bad else "done", "final": True})
            d["steps"], d["closed"], d["updated"], d["ended"] = steps[-MAX_STEPS:], True, t, t
            _write(p, d)
    except Exception:
        log.info("app activity end not written", exc_info=True)


def read(tenant: str, app_id: str) -> dict[str, Any]:
    """What the Studio draws: the steps, when the job started / ended, which job it was, and the server's clock."""
    try:
        d = _read(_path(tenant, app_id))
    except Exception:
        d = {}
    return {"started": d.get("started"), "ended": d.get("ended"), "job": d.get("job") or "",
            "steps": d.get("steps") or [], "now": time.time()}


# ---------------------------------------------------------------- the three hooks the engine calls (all fail-open)
def on_work(tenant: str, app_id: str, phase: str, label: str, note: str = "", items: list | None = None) -> None:
    """service._work: the design side (looks, every screen, checks, fixes, done / waiting / error / paused)."""
    lab, n, key, done, total = english(label, note)
    if phase == "start":
        if items and re.search(r" screen$", str(label or "")):          # one screen of the design run
            done = sum(1 for x in items if (x or {}).get("s") == "done")
            step(tenant, app_id, "Designing every screen", str(label)[:-7], "design", done, len(items), job="design")
        else:
            step(tenant, app_id, lab, n, key, done, total, job="looks" if key.startswith("look") else "design")
    elif phase in ("waiting", "done"):
        end(tenant, app_id, lab, n, "done")
    elif phase == "error":
        end(tenant, app_id, lab, str(note or "")[:160], "error")
    elif phase == "stopped":
        end(tenant, app_id, "Paused", "paused when you asked", "done")


_END = {"ready": "ready", "zip": "Project ZIP ready (no build machine)", "failed": "The build hit a problem"}


def on_build(tenant: str, app_id: str, platform: str, kw: dict[str, Any], states: dict | None = None) -> None:
    """android/ios _put + _states: 'now' lines become steps; ready / zip / failed end the job."""
    try:
        name = "iPhone" if platform == "ios" else "Android"
        st = str(kw.get("status") or "")
        if st in _END:
            if st == "ready":
                end(tenant, app_id, f"{name} app ready", "", "done")
            else:
                end(tenant, app_id, _END[st], str(kw.get("error") or kw.get("note") or "")[:160],
                    "error" if st == "failed" else "done")
            return
        line = str(kw.get("now") or "")
        if not line:
            return
        lab, n, key, done, total = english(line)
        if states is not None and key in ("kotlin", "swift") and total:
            done = sum(1 for v in states.values() if v in ("written", "code", "compiling"))
        step(tenant, app_id, lab, n, key, done, total, job=platform)
    except Exception:
        log.info("app activity build hook failed", exc_info=True)
