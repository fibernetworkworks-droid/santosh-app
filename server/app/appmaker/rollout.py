"""v0.540 DHEERE CHHODO (App Sahayak Pillar J, Phase 61, second half): a new version reaches her users a few at a
time, a bad one is stopped in minutes, and a feature can be switched off without any build at all.

Two different things, because they fail on two different clocks:

  1. STAGED ROLLOUT (the build)   - Google Play's own staged release: a production release goes out to 5 % of users,
                                    then 20, 50, 100, each step by HER tap. If the crash reports turn bad, `halt`
                                    stops it reaching anyone new within minutes, and `rollback` puts the previous
                                    build back on the track. Said plainly: Play cannot take a version off the phones
                                    that already have it - what it can do is stop the rest and ship the old one again,
                                    and those phones update to it.
  2. FEATURE FLAGS (the feature)  - a switch that lives on the SERVER and rides to the app in its schema. Turning it
                                    off is instant and needs no build, no review and no download: this is the only
                                    rollback that works in minutes, so anything risky she ships goes behind one.
                                    A flag can also be given a percentage - the same staged idea, inside one build.

The flag a phone gets is decided on the SERVER (a stable hash of the member id), never by the app, so a user does not
flip between on and off every time the app restarts, and one user's answer cannot change another's.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from ..db import now
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"staged": 0, "advanced": 0, "halted": 0, "rolled_back": 0, "flags": 0}

STAGES = (0.05, 0.2, 0.5, 1.0)          # 5 % -> 20 % -> 50 % -> everyone, one tap each
MAX_FLAGS = 24


# ---------------------------------------------------------------- feature flags (no build, instant)
def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def flags(r: AppProject) -> list[dict[str, Any]]:
    return [f for f in ((_j(r.backend, {}) or {}).get("flags") or []) if isinstance(f, dict)]


def set_flag(r: AppProject, key: str, on: bool | None = None, percent: int | None = None,
             label: str = "") -> dict[str, Any]:
    """Add or change one switch. It is live the moment this returns - the app reads it on its next call."""
    from . import backend as BE
    k = re.sub(r"[^a-z0-9_]", "", str(key or "").strip().lower().replace("-", "_").replace(" ", "_"))[:40]
    if not k:
        raise W.AppError("The flag needs a name (a-z, _).", 400)
    cur = flags(r)
    hit = next((f for f in cur if f.get("key") == k), None)
    if hit is None:
        if len(cur) >= MAX_FLAGS:
            raise W.AppError(f"No more than {MAX_FLAGS} switches.", 400)
        hit = {"key": k, "on": False, "percent": 100, "label": label or k.replace("_", " ").title(),
               "made": now().isoformat()}
        cur.append(hit)
    if on is not None:
        hit["on"] = bool(on)
    if percent is not None:
        hit["percent"] = max(0, min(100, int(percent)))
    if label:
        hit["label"] = str(label)[:60]
    hit["at"] = now().isoformat()
    BE.patch_backend(r, set_={"flags": cur})
    STATS["flags"] += 1
    return hit


def drop_flag(r: AppProject, key: str) -> dict[str, Any]:
    from . import backend as BE
    cur = [f for f in flags(r) if f.get("key") != key]
    BE.patch_backend(r, set_={"flags": cur})
    return {"ok": True, "flags": len(cur)}


def for_member(r: AppProject, member_id: str = "") -> dict[str, bool]:
    """What THIS phone is told. A percentage is decided here, by a stable hash - never by the app."""
    out: dict[str, bool] = {}
    for f in flags(r):
        if not f.get("on"):
            out[f["key"]] = False
            continue
        pct = int(f.get("percent", 100))
        if pct >= 100:
            out[f["key"]] = True
        elif pct <= 0 or not member_id:
            out[f["key"]] = False
        else:
            h = hashlib.sha256(f"{f['key']}|{member_id}".encode()).hexdigest()[:8]
            out[f["key"]] = (int(h, 16) % 100) < pct
    return out


# ---------------------------------------------------------------- Play staged rollout (the build)
def _store():
    from .android import store as ST
    return ST


def state(r: AppProject) -> dict[str, Any]:
    return _store().state(r)


def view(tenant: str, ref: str) -> dict[str, Any]:
    ST = _store()
    r = ST._load(tenant, ref)
    st = state(r)
    cur = st.get("rollout") or {}
    return {"app": r.id, "flags": flags(r), "rollout": cur, "stages": list(STAGES),
            "releases": list(reversed(st.get("releases") or []))[:5],
            "can_rollback": bool(_previous_vc(st)),
            "says": _says(cur, st)}


def _says(cur: dict[str, Any], st: dict[str, Any]) -> str:
    if not cur or not cur.get("version_code"):
        return "No staged rollout is running on production."
    pct = int(float(cur.get("fraction") or 0) * 100)
    if cur.get("status") == "halted":
        return f"v{cur.get('version_name') or cur['version_code']} is HALTED (it had reached {pct}%)."
    if cur.get("status") == "completed":
        return f"v{cur.get('version_name') or cur['version_code']} has reached everyone."
    return f"v{cur.get('version_name') or cur['version_code']} is at {pct}% of users now."


def _previous_vc(st: dict[str, Any]) -> int:
    """The version code before the one on the track now - the one `rollback` puts back."""
    rel = [x for x in (st.get("releases") or []) if x.get("track") == "production"]
    codes = sorted({int(x.get("version_code") or 0) for x in rel if x.get("version_code")})
    return codes[-2] if len(codes) >= 2 else 0


def _track(r: AppProject, releases: list[dict[str, Any]], track: str = "production") -> dict[str, Any]:
    """One Play edit: set the track's releases exactly as given, then commit. Every change here is one of those."""
    ST = _store()
    st = state(r)
    creds = ST._creds(r)
    if not creds:
        raise ST.StoreError("Add the Play Console service account key in the app first.")
    pkg = st.get("package")
    if not pkg:
        raise ST.StoreError("Complete the store setup first.")
    tok = ST._token(creds)
    eid = ST._call("POST", f"{ST.API}/{pkg}/edits", tok, {})["id"]
    out = ST._call("PUT", f"{ST.API}/{pkg}/edits/{eid}/tracks/{track}", tok, {"track": track, "releases": releases})
    ST._call("POST", f"{ST.API}/{pkg}/edits/{eid}:commit", tok)
    return out


def start(tenant: str, ref: str, her_tap: bool = False, fraction: float = STAGES[0]) -> dict[str, Any]:
    """Put the uploaded build on production for a FEW users. Production is public, so it needs her tap (v0.330)."""
    ST = _store()
    r = ST._load(tenant, ref)
    st = state(r)
    if not her_tap:
        raise ST.StoreError("Only you send it to production (public for everyone), by tapping the button in the app.")
    vc = int(st.get("last_vc") or 0)
    if not vc:
        raise ST.StoreError("Upload a build first (internal testing).")
    frac = min(1.0, max(0.0001, float(fraction)))
    rel = {"versionCodes": [str(vc)], "status": "completed" if frac >= 1 else "inProgress"}
    if frac < 1:
        rel["userFraction"] = frac
    _track(r, [rel])
    cur = {"version_code": vc, "version_name": (st.get("bundle") or {}).get("version_name", ""),
           "fraction": frac, "status": rel["status"], "at": now().isoformat(),
           "steps": [{"fraction": frac, "at": now().isoformat()}]}
    ST._put(r, rollout=cur)
    STATS["staged"] += 1
    _note(r, f"v{cur['version_name'] or vc} went to {int(frac * 100)}% of users on production. Watch the crash card; "
             "if it looks fine say 'increase the rollout', if there is a problem say 'halt the rollout'.")
    return {"ok": True, "rollout": cur, "says": _says(cur, st)}


def advance(tenant: str, ref: str, her_tap: bool = False, fraction: float = 0.0) -> dict[str, Any]:
    """Next stage (5 -> 20 -> 50 -> 100), or a fraction she names. Her tap each time: each step is more users."""
    ST = _store()
    r = ST._load(tenant, ref)
    st = state(r)
    cur = dict(st.get("rollout") or {})
    if not cur.get("version_code"):
        raise ST.StoreError("No rollout is running.")
    if not her_tap:
        raise ST.StoreError("Increasing the rollout is your tap.")
    if cur.get("status") == "completed":
        return {"ok": True, "rollout": cur, "says": "This version has already reached everyone."}
    nxt = float(fraction) if fraction else next((s for s in STAGES if s > float(cur.get("fraction") or 0)), 1.0)
    nxt = min(1.0, max(0.0001, nxt))
    rel: dict[str, Any] = {"versionCodes": [str(cur["version_code"])],
                           "status": "completed" if nxt >= 1 else "inProgress"}
    if nxt < 1:
        rel["userFraction"] = nxt
    _track(r, [rel])
    cur.update(fraction=nxt, status=rel["status"], at=now().isoformat())
    cur["steps"] = (cur.get("steps") or []) + [{"fraction": nxt, "at": now().isoformat()}]
    ST._put(r, rollout=cur)
    STATS["advanced"] += 1
    _note(r, f"Rollout is at {int(nxt * 100)}%" + (" - it now reaches everyone." if nxt >= 1 else "."))
    return {"ok": True, "rollout": cur, "says": _says(cur, st)}


def halt(tenant: str, ref: str, why: str = "") -> dict[str, Any]:
    """STOP. No new user gets this version. Her tap is not needed to stop something going wrong."""
    ST = _store()
    r = ST._load(tenant, ref)
    st = state(r)
    cur = dict(st.get("rollout") or {})
    if not cur.get("version_code") or cur.get("status") == "completed":
        raise ST.StoreError("There is no staged rollout in progress (a completed rollout cannot be halted).")
    _track(r, [{"versionCodes": [str(cur["version_code"])], "status": "halted",
                "userFraction": float(cur.get("fraction") or STAGES[0])}])
    cur.update(status="halted", at=now().isoformat(), why=str(why)[:200])
    ST._put(r, rollout=cur)
    STATS["halted"] += 1
    _note(r, f"Rollout HALTED (at {int(float(cur.get('fraction') or 0) * 100)}%). Phones that already have it keep "
             "the version - no new install / update goes out now.")
    return {"ok": True, "rollout": cur, "says": _says(cur, st)}


def rollback(tenant: str, ref: str, her_tap: bool = False) -> dict[str, Any]:
    """Put the previous build back on production. Said plainly: this does not remove the new version from the phones
    that already updated - it stops the rest and sends those phones the old build as their next update."""
    ST = _store()
    r = ST._load(tenant, ref)
    st = state(r)
    cur = dict(st.get("rollout") or {})
    prev = _previous_vc(st)
    if not prev:
        raise ST.StoreError("No build went to production before this one, so there is nothing to go back to.")
    if not her_tap:
        raise ST.StoreError("Sending the old build back is your tap.")
    rels: list[dict[str, Any]] = []
    if cur.get("version_code") and cur.get("status") != "completed":
        rels.append({"versionCodes": [str(cur["version_code"])], "status": "halted",
                     "userFraction": float(cur.get("fraction") or STAGES[0])})
    rels.append({"versionCodes": [str(prev)], "status": "completed"})
    _track(r, rels)
    cur = {"version_code": prev, "version_name": "", "fraction": 1.0, "status": "completed",
           "at": now().isoformat(), "rolled_back_from": cur.get("version_code")}
    ST._put(r, rollout=cur)
    STATS["rolled_back"] += 1
    _note(r, f"The old build (v{prev}) is back on production. Phones that already got the new one receive this old one "
             "as their next update - Play cannot remove a version from a phone.")
    return {"ok": True, "rollout": cur, "says": f"v{prev} is back on production."}


def _note(r: AppProject, text: str) -> None:
    try:
        from .android.service import _note as note
        note(r, text)
    except Exception:                                               # noqa: BLE001
        log.debug("rollout note", exc_info=True)
