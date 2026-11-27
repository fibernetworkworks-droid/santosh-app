"""v0.999.248 HOOLA ROUTE R8: past runs as working material.

- search: find runs by a value anywhere in their data (an order number, an email, an error word)
- start data + run again: a new run with the data a past run started with
- a past run's data in the editor (stepdata.data run_id=) and pinned from that run
- keeping: per-route keep_runs_days / keep_runs (forget_old_runs honours them)
- insights: runs, failure rate, working time, slow and failing steps, time saved - from a small tally that
  outlives the runs themselves (kept runs are cleared; the tally is not)

Every value that comes back is masked the house way (ID numbers + card / bank / tax numbers).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

FINAL = ("done", "failed", "stopped", "incomplete")
SEARCH_MIN, SEARCH_MAX = 2, 200
SNIPPET = 70
DAYS_ALLOWED = (1, 7, 30, 90)


class RunsError(ValueError):
    pass


def _mask(v: Any) -> Any:
    from ..agent import dhara_tools as D
    from ..pii import mask_sensitive
    v = D._masked(v)
    if isinstance(v, str):
        return mask_sensitive(v)
    if isinstance(v, dict):
        return {k: _mask(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_mask(x) for x in v]
    return v


def _json(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------------------------------- search

def _snippet(text: str, q: str) -> str:
    i = text.lower().find(q.lower())
    if i < 0:
        return ""
    a, b = max(0, i - SNIPPET), min(len(text), i + len(q) + SNIPPET)
    return ("…" if a else "") + text[a:b] + ("…" if b < len(text) else "")


def _where(ctx: dict, log: list, err: str, q: str) -> tuple[str, str]:
    """Where in the run the value is, and a short piece of text around it."""
    ql = q.lower()
    t = _json(start_data({"context": ctx}))
    if ql in t.lower():
        return "start data", _snippet(t, q)
    for sid, x in (ctx.get("steps") or {}).items():
        if isinstance(x, dict):
            t = _json(x.get("output"))
            if ql in t.lower():
                return f"step {sid}", _snippet(t, q)
    vars_ = {k: v for k, v in (ctx.get("vars") or {}).items() if not str(k).startswith("_") and k != "resume_url"}
    t = _json(vars_)
    if ql in t.lower():
        return "variables", _snippet(t, q)
    if err and ql in err.lower():
        return "error", _snippet(err, q)
    for e in log or []:
        t = _json(e)
        if ql in t.lower():
            return f"step {e.get('id') or '?'}", _snippet(t, q)
    return "", ""


def search(tenant: str, q: str, wf_id: str = "", status: str = "", limit: int = 30) -> dict:
    """Runs whose start data, step outputs, log or error hold the value (any case). Newest first."""
    from ..agent import dhara_tools as D
    q = str(q or "").strip()
    if len(q) < SEARCH_MIN:
        raise RunsError(f"Search for at least {SEARCH_MIN} characters")
    q = q[:SEARCH_MAX]
    like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    where = ["(context LIKE ? ESCAPE '\\' OR steps_log LIKE ? ESCAPE '\\' OR error LIKE ? ESCAPE '\\')"]
    args: list[Any] = [like, like, like]
    if wf_id:
        where.append("workflow_id = ?"); args.append(wf_id)
    if status:
        where.append("status = ?"); args.append(status)
    con = D._con(tenant)
    try:
        rows = con.execute("SELECT * FROM runs WHERE " + " AND ".join(where) + " ORDER BY created_at DESC LIMIT ?",
                           (*args, max(1, min(int(limit or 30), 100)))).fetchall()
    finally:
        con.close()
    out = []
    for r in rows:
        d = D._run_row(r)
        found, snip = _where(d.get("context") or {}, d.get("steps_log") or [], d.get("error") or "", q)
        if not found:             # the value matched only inside Hoola's own bookkeeping (a pin, a timer)
            continue
        out.append({"id": d["id"], "route": d["wf_name"], "route_id": d["workflow_id"], "status": d["status"],
                    "steps_done": d["cursor"], "error": (d.get("error") or "")[:300],
                    "pause_reason": d.get("pause_reason") or "", "summary": d.get("summary"),
                    "at": d.get("created_at"), "next_wake_at": d.get("next_wake_at"),
                    "found_in": found, "match": snip})
    return {"q": q, "runs": _mask(out)}


# ---------------------------------------------------------------------------------------------------- run again

def start_data(run: dict) -> dict:
    """What the run started with (kept apart since R8; older runs: their variables without Hoola's own)."""
    ctx = run.get("context") or {}
    if isinstance(ctx.get("_start"), dict):
        return dict(ctx["_start"])
    return {k: v for k, v in (ctx.get("vars") or {}).items() if not str(k).startswith("_") and k != "resume_url"}


def failed_step(run: dict) -> str:
    for e in reversed(run.get("steps_log") or []):
        if str(e.get("status") or "") in ("failed", "error"):
            return str(e.get("id") or "")
    return ""


def rerun(tenant: str, run_id: str) -> dict:
    """A NEW run of the same route with the data the old run started with. The old run is untouched."""
    from ..agent import dhara_tools as D
    old = D.get_run(tenant, run_id)
    if old is None:
        raise RunsError("Run not found")
    wf = D.get_workflow(tenant, wf_id=old["workflow_id"])
    if wf is None:
        raise RunsError("The route of this run is gone")
    st = dict(wf.get("settings") or {})
    cap = int(st.get("runs_per_day") or 0)
    if cap and D._runs_today(tenant, wf["id"]) >= cap:
        raise RunsError(f"This route already ran {cap} times today (its daily limit)")
    rid = D.create_run(tenant, wf, start_data(old))
    return {"run_id": rid, "status": "queued", "from_run": run_id, "route_id": wf["id"]}


def pin_from_run(tenant: str, wf: dict, run_id: str, steps: list | None = None, trigger: bool = True) -> dict:
    """Her pins from a past run: the start data and each step's output, so a test works on that exact data."""
    from ..agent import dhara_tools as D
    from . import stepdata as SD
    old = D.get_run(tenant, run_id)
    if old is None or old["workflow_id"] != wf["id"]:
        raise RunsError("That run is not a run of this route")
    ctx = old.get("context") or {}
    live = {s["id"]: s for s in SD._all(wf.get("steps") or [])}
    want = set(steps) if steps else None
    pinned, skipped = [], []
    last = {str(e.get("id")): str(e.get("status") or "") for e in old.get("steps_log") or []}
    if trigger:
        try:
            SD.set_pin(tenant, wf, "trigger", start_data(old))
            pinned.append("trigger")
        except ValueError as e:
            skipped.append({"step": "trigger", "why": str(e)})
    for sid, x in (ctx.get("steps") or {}).items():
        if sid not in live or (want is not None and sid not in want) or not isinstance(x, dict):
            continue
        if live[sid].get("type") in SD.NO_PIN or x.get("output") is None or last.get(sid) in ("error", "failed"):
            continue                       # a step that failed in that run gave nothing worth testing with
        try:
            SD.set_pin(tenant, wf, sid, x.get("output"))
            pinned.append(sid)
        except ValueError as e:
            skipped.append({"step": sid, "why": str(e)})
    return {"pinned": pinned, "skipped": skipped, "pins": sorted(SD.pins(tenant, wf["id"]))}


# ---------------------------------------------------------------------------------------------------- keeping

KEEP_DAYS_MAX = 3650
KEEP_RUNS_MAX = 20000
KEEP_CEILING = 20000          # a route that names only days still keeps at most this many runs


def keeping(settings: dict, keep_days: int, keep: int) -> tuple[int, int] | None:
    """(days, count) a route keeps its finished runs for, or None = the server's default."""
    d, k = settings.get("keep_runs_days"), settings.get("keep_runs")
    if not d and not k:
        return None
    return (int(d) if d else KEEP_DAYS_MAX, int(k) if k else KEEP_CEILING)


# ---------------------------------------------------------------------------------------------------- tally

def _tcon(tenant: str):
    from ..agent import dhara_tools as D
    con = D._con(tenant)
    con.execute("CREATE TABLE IF NOT EXISTS route_tally (workflow_id TEXT, hour INTEGER, done INTEGER DEFAULT 0, "
                "failed INTEGER DEFAULT 0, secs REAL DEFAULT 0, timed INTEGER DEFAULT 0, "
                "PRIMARY KEY (workflow_id, hour))")
    con.execute("CREATE TABLE IF NOT EXISTS route_step_tally (workflow_id TEXT, day INTEGER, step TEXT, "
                "n INTEGER DEFAULT 0, ms REAL DEFAULT 0, fails INTEGER DEFAULT 0, PRIMARY KEY (workflow_id, day, step))")
    # one row per counted run: a failed run retried to done moves from failed to done, never counted twice
    con.execute("CREATE TABLE IF NOT EXISTS route_tallied (run_id TEXT PRIMARY KEY, workflow_id TEXT, hour INTEGER, "
                "status TEXT, secs REAL, timed INTEGER)")
    return con


def tally(tenant: str, wf_id: str, status: str, run_id: str) -> None:
    """Called at a run's honest end (done / failed). Never raises."""
    from ..agent import dhara_tools as D
    try:
        run = D.get_run(tenant, run_id) or {}
        ctx = run.get("context") or {}
        now_ = time.time()
        secs = ctx.get("_active_s")
        if secs is None and run.get("started_at"):
            secs = now_ - float(run["started_at"])
        timed = 0 if secs is None else 1
        secs = float(secs or 0.0)
        good = 1 if status == "done" else 0
        hour, day = int(now_ // 3600), int(now_ // 86400)
        con = _tcon(tenant)
        try:
            old = con.execute("SELECT * FROM route_tallied WHERE run_id = ?", (run_id,)).fetchone()
            if old is not None:                       # counted before (it failed, then was retried): take that back
                ogood = 1 if old["status"] == "done" else 0
                con.execute("UPDATE route_tally SET done = done - ?, failed = failed - ?, secs = secs - ?, "
                            "timed = timed - ? WHERE workflow_id = ? AND hour = ?",
                            (ogood, 1 - ogood, float(old["secs"] or 0), int(old["timed"] or 0),
                             old["workflow_id"], old["hour"]))
            con.execute("INSERT OR IGNORE INTO route_tally (workflow_id, hour) VALUES (?, ?)", (wf_id, hour))
            con.execute("UPDATE route_tally SET done = done + ?, failed = failed + ?, secs = secs + ?, timed = timed + ? "
                        "WHERE workflow_id = ? AND hour = ?", (good, 1 - good, secs, timed, wf_id, hour))
            con.execute("INSERT OR REPLACE INTO route_tallied (run_id, workflow_id, hour, status, secs, timed) "
                        "VALUES (?,?,?,?,?,?)", (run_id, wf_id, hour, status, secs, timed))
            seen = set()
            for e in reversed(run.get("steps_log") or []):    # a retried run's steps count once, as they ended
                sid, st = str(e.get("id") or ""), str(e.get("status") or "")
                if not sid or st == "retry" or sid in seen or (old is not None and st == "ok"):
                    continue
                seen.add(sid)
                con.execute("INSERT OR IGNORE INTO route_step_tally (workflow_id, day, step) VALUES (?, ?, ?)",
                            (wf_id, day, sid))
                con.execute("UPDATE route_step_tally SET n = n + 1, ms = ms + ?, fails = fails + ? "
                            "WHERE workflow_id = ? AND day = ? AND step = ?",
                            (float(e.get("ms") or 0), 1 if st in ("error", "failed") else 0, wf_id, day, sid))
            con.execute("DELETE FROM route_tallied WHERE hour < ?", (hour - 24 * 400,))
            con.commit()
        finally:
            con.close()
    except Exception:   # noqa: BLE001 - counting never breaks a run
        pass


# ---------------------------------------------------------------------------------------------------- insights

def _tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(str(name or "UTC"))
    except Exception:   # noqa: BLE001
        return ZoneInfo("UTC")


def insights(tenant: str, days: int = 7, wf_id: str = "", tz: str = "UTC") -> dict:
    from ..agent import dhara_tools as D
    days = int(days) if int(days or 0) in DAYS_ALLOWED else 7
    zone = _tz(tz)
    now_ = time.time()
    since, prev = now_ - days * 86400, now_ - 2 * days * 86400
    wfs = {w["id"]: w for w in D.list_workflows(tenant, limit=5000)}
    con = _tcon(tenant)
    try:
        q = "SELECT * FROM route_tally WHERE hour >= ?" + (" AND workflow_id = ?" if wf_id else "")
        rows = con.execute(q, (int(prev // 3600), *([wf_id] if wf_id else []))).fetchall()
        q2 = "SELECT * FROM route_step_tally WHERE day >= ?" + (" AND workflow_id = ?" if wf_id else "")
        srows = con.execute(q2, (int(since // 86400), *([wf_id] if wf_id else []))).fetchall()
        q3 = ("SELECT workflow_id, status, COUNT(*) FROM runs WHERE created_at >= ? AND status IN ('stopped','incomplete')"
              + (" AND workflow_id = ?" if wf_id else "") + " GROUP BY workflow_id, status")
        stopped = con.execute(q3, (since, *([wf_id] if wf_id else []))).fetchall()
    finally:
        con.close()

    def blank():
        return {"done": 0, "failed": 0, "secs": 0.0, "timed": 0}

    per: dict[str, dict] = {}
    before: dict[str, dict] = {}
    series: dict[str, dict] = {}
    for r in rows:
        at = int(r["hour"]) * 3600
        tgt = per if at >= since else before
        b = tgt.setdefault(r["workflow_id"], blank())
        for k in ("done", "failed", "secs", "timed"):
            b[k] += r[k] or 0
        if at >= since:
            key = datetime.fromtimestamp(at, timezone.utc).astimezone(zone).strftime("%Y-%m-%d")
            s = series.setdefault(key, {"done": 0, "failed": 0})
            s["done"] += r["done"] or 0
            s["failed"] += r["failed"] or 0
    stops: dict[str, int] = {}
    for wid, _st, n in stopped:
        stops[wid] = stops.get(wid, 0) + int(n)

    def figures(b: dict, wf: dict | None) -> dict:
        n = b["done"] + b["failed"]
        mins = float((wf or {}).get("settings", {}).get("minutes_saved") or 0)
        return {"runs": n, "done": b["done"], "failed": b["failed"],
                "failure_rate": round(100.0 * b["failed"] / n, 1) if n else 0.0,
                "avg_s": round(b["secs"] / b["timed"], 1) if b["timed"] else None,
                "minutes_saved": round(b["done"] * mins, 1) if mins else 0.0,
                "minutes_per_run": mins}

    routes = []
    for wid in set(per) | set(before) | ({wf_id} if wf_id and wf_id in wfs else set()):
        wf = wfs.get(wid)
        f = figures(per.get(wid, blank()), wf)
        p = figures(before.get(wid, blank()), wf)
        routes.append({"id": wid, "name": (wf or {}).get("name") or "(deleted route)", "enabled": bool((wf or {}).get("enabled")),
                       **f, "stopped": stops.get(wid, 0), "before": {"runs": p["runs"], "failure_rate": p["failure_rate"]}})
    routes.sort(key=lambda x: (-x["runs"], x["name"]))

    tot = blank()
    saved = 0.0
    for r in routes:
        tot["done"] += r["done"]
        tot["failed"] += r["failed"]
        saved += r["minutes_saved"]
    secs = sum(per.get(w, blank())["secs"] for w in per)
    timed = sum(per.get(w, blank())["timed"] for w in per)
    pn = sum(b["done"] + b["failed"] for b in before.values())
    pf = sum(b["failed"] for b in before.values())
    n = tot["done"] + tot["failed"]

    steps: dict[tuple[str, str], dict] = {}
    for r in srows:
        k = (r["workflow_id"], r["step"])
        s = steps.setdefault(k, {"n": 0, "ms": 0.0, "fails": 0})
        s["n"] += r["n"] or 0
        s["ms"] += r["ms"] or 0
        s["fails"] += r["fails"] or 0
    srank = [{"route_id": w, "route": (wfs.get(w) or {}).get("name") or "(deleted route)", "step": sid,
              "runs": s["n"], "avg_ms": round(s["ms"] / s["n"]) if s["n"] else 0, "fails": s["fails"]}
             for (w, sid), s in steps.items() if s["n"]]
    slow = sorted(srank, key=lambda x: -x["avg_ms"])[:5]
    failing = sorted([x for x in srank if x["fails"]], key=lambda x: -x["fails"])[:5]

    day_keys = []
    for i in range(days - 1, -1, -1):
        day_keys.append(datetime.fromtimestamp(now_ - i * 86400, timezone.utc).astimezone(zone).strftime("%Y-%m-%d"))
    return {"days": days, "tz": str(zone.key),
            "totals": {"runs": n, "done": tot["done"], "failed": tot["failed"],
                       "failure_rate": round(100.0 * tot["failed"] / n, 1) if n else 0.0,
                       "avg_s": round(secs / timed, 1) if timed else None,
                       "minutes_saved": round(saved, 1),
                       "before": {"runs": pn, "failure_rate": round(100.0 * pf / pn, 1) if pn else 0.0}},
            "series": [{"day": d, **series.get(d, {"done": 0, "failed": 0})} for d in day_keys],
            "routes": routes, "slow_steps": slow, "failing_steps": failing,
            "note": "Counted from the end of each run since Hoola Route R8; runs before that are not in these figures."}
