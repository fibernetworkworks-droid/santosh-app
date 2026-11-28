"""A pipeline's run history read job by job: how often each job fails and whether it is failing now, typical and slow durations
(median, p95, the last run against them, a slowdown over the last runs), runs past her time limit, row counts that suddenly
drop to zero or move far from normal, and how stale each job's data is (the last successful finish against the latest time in
the history, or the time she gives). Input: a CSV of runs - job, start, end (or a duration), status, and rows if known."""
from __future__ import annotations

import re
import statistics as stx
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from ..mldesk.table import TableError, num, read
from .common import finder, finish, mins, minutes, pct


class RunsError(TableError):
    pass


_OK = {"success", "succeeded", "ok", "passed", "pass", "done", "completed", "complete", "finished", "true", "1", "green"}
_FAIL = {"failed", "failure", "fail", "error", "errored", "false", "0", "red", "upstream_failed", "timeout", "timed_out", "killed", "cancelled", "canceled", "aborted"}


def _col(head: list[str], *names: str) -> int | None:
    low = [h.lower().strip() for h in head]
    for n in names:
        if n in low:
            return low.index(n)
    for n in names:
        for i, h in enumerate(low):
            if n in h:
                return i
    return None


def _ts(v: str) -> datetime | None:
    v = str(v or "").strip()
    if not v:
        return None
    if re.fullmatch(r"\d{10}(\.\d+)?", v):
        return datetime.fromtimestamp(float(v), timezone.utc)
    if re.fullmatch(r"\d{13}", v):
        return datetime.fromtimestamp(int(v) / 1000, timezone.utc)
    v2 = v.replace("Z", "+00:00").replace("/", "-")
    v2 = re.sub(r"(\d{2}:\d{2}:\d{2})\.(\d{6})\d+", r"\1.\2", v2)
    for f in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"):
        try:
            d = datetime.fromisoformat(v2) if f is None else datetime.strptime(v2, f)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def analyse(text: str, sla: float | None = None, freshness_h: float | None = None, as_of: str = "") -> dict[str, Any]:
    head, rows = read(text, "The run history")
    ij = _col(head, "job", "task", "task_id", "dag_id", "pipeline", "name", "model", "dag")
    ist = _col(head, "start", "start_time", "started", "started_at", "start_date", "execution_date", "logical_date")
    ie = _col(head, "end", "end_time", "ended", "ended_at", "finished", "finished_at", "end_date", "completed_at")
    idu = _col(head, "duration", "duration_s", "seconds", "minutes", "elapsed", "runtime", "run_time")
    ist_ = _col(head, "status", "state", "result", "outcome", "success")
    irw = _col(head, "rows", "row_count", "records", "rows_written", "rows_affected", "count")
    if ij is None:
        ij = None
    if ist_ is None:
        raise RunsError("The history needs a status column (success / failed).")
    if ist is None and idu is None:
        raise RunsError("The history needs a start time or a duration column.")
    unit = "s" if idu is not None and re.search(r"(_s|sec|seconds)$", head[idu].lower()) else ("m" if idu is not None and "min" in head[idu].lower() else "s")
    issues, add = finder()
    jobs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unread = 0
    for r in rows:
        st = r[ist_].strip().lower()
        ok = True if st in _OK else False if st in _FAIL else None
        if ok is None and st in ("running", "queued", "scheduled", "up_for_retry", "retry", "skipped", "pending"):
            continue
        if ok is None:
            unread += 1
            continue
        s = _ts(r[ist]) if ist is not None else None
        e = _ts(r[ie]) if ie is not None else None
        d = None
        if idu is not None:
            d = minutes(r[idu], unit)
        if d is None and s and e:
            d = (e - s).total_seconds() / 60
        if s and not e and d is not None:
            from datetime import timedelta
            e = s + timedelta(minutes=d)
        rw = num(r[irw]) if irw is not None else None
        jobs[r[ij].strip() if ij is not None else "pipeline"].append({"start": s, "end": e, "min": d, "ok": ok, "rows": rw})
    if not jobs:
        raise RunsError("No finished runs found - the status column must say success or failed.")
    if unread:
        add("info", "Status", f"{unread} row(s) had a status not read as success or failure and were left out.", "")
    allt = [x["end"] or x["start"] for v in jobs.values() for x in v if (x["end"] or x["start"])]
    now = _ts(as_of) if as_of else (max(allt) if allt else None)
    out = []
    for name, runs in jobs.items():
        runs.sort(key=lambda x: x["start"] or x["end"] or datetime.min.replace(tzinfo=timezone.utc))
        fails = [x for x in runs if not x["ok"]]
        d_ok = [x["min"] for x in runs if x["ok"] and x["min"] is not None]
        streak = 0
        for x in reversed(runs):
            if x["ok"]:
                break
            streak += 1
        j: dict[str, Any] = {"job": name, "runs": len(runs), "failed": len(fails), "fail_rate": len(fails) / len(runs), "failing_now": streak,
                             "series": [[(x["start"] or x["end"]).isoformat() if (x["start"] or x["end"]) else str(i), x["min"], x["ok"], x["rows"]] for i, x in enumerate(runs[-60:])]}
        if d_ok:
            med = stx.median(d_ok)
            j.update(median=med, p95=pct(d_ok, 0.95), last=next((x["min"] for x in reversed(runs) if x["min"] is not None), None), max=max(d_ok))
            if j["last"] is not None and len(d_ok) >= 5 and j["last"] > 2 * med and j["last"] - med > 1:
                add("warn", "Slow", f"{name}: the last run took {mins(j['last'])} against a typical {mins(med)}.", "Look for more input data, a lost partition filter or a busier cluster.", name)
            if len(d_ok) >= 10:
                a, b = stx.median(d_ok[:len(d_ok) // 2]), stx.median(d_ok[len(d_ok) // 2:])
                j["trend"] = (b - a) / a if a else 0
                if a and b > 1.3 * a and b - a > 1:
                    add("warn", "Slowing", f"{name} got {(b / a - 1) * 100:.0f}% slower (median {mins(a)} -> {mins(b)} over the history).", "Data growth: check it scales (incremental loads, partitions).", name)
            if sla:
                over = [x for x in d_ok if x > sla]
                j["over_sla"] = len(over)
                if over:
                    add("bad" if len(over) / len(d_ok) > 0.1 else "warn", "Time limit", f"{name} ran past {mins(sla)} in {len(over)} of {len(d_ok)} successful runs.", "", name)
        if streak:
            add("bad", "Failing", f"{name} has failed its last {streak} run(s).", "Fix it before downstream jobs read stale data.", name)
        elif len(fails) >= 2 and j["fail_rate"] >= 0.1:
            add("warn", "Flaky", f"{name} failed {len(fails)} of {len(runs)} runs ({j['fail_rate'] * 100:.0f}%).", "Find the cause (timeouts, a flaky source) - retries hide it.", name)
        rws = [x["rows"] for x in runs if x["ok"] and x["rows"] is not None]
        if len(rws) >= 5:
            med_r = stx.median(rws[:-1])
            j["rows_median"], j["rows_last"] = med_r, rws[-1]
            if rws[-1] == 0 and med_r > 0:
                add("bad", "Rows", f"{name} succeeded but wrote 0 rows (usually {med_r:,.0f}).", "A green run with no data - check the source and the filters; add a row-count check that fails.", name)
            elif med_r > 0 and (rws[-1] < 0.5 * med_r or rws[-1] > 2 * med_r):
                add("warn", "Rows", f"{name} wrote {rws[-1]:,.0f} rows against a usual {med_r:,.0f}.", "", name)
        last_ok = next((x["end"] or x["start"] for x in reversed(runs) if x["ok"] and (x["end"] or x["start"])), None)
        if last_ok and now:
            age = (now - last_ok).total_seconds() / 3600
            j["age_h"] = age
            if freshness_h and age > freshness_h:
                add("bad", "Stale", f"{name}'s data is {age:.1f} h old - past the {freshness_h:g} h limit.", "", name)
        out.append(j)
    out.sort(key=lambda j: (-j["failing_now"], -j["fail_rate"], j["job"]))
    tot = sum(j["runs"] for j in out)
    fl = sum(j["failed"] for j in out)
    res = {"jobs": out, "runs": tot, "failed": fl, "as_of": now.isoformat() if now else None,
           "verdict": f"{len(out)} job(s), {tot:,} runs, {fl:,} failed" + (f"; {sum(1 for j in out if j['failing_now'])} failing now" if any(j['failing_now'] for j in out) else ""),
           "note": "Read from the history you pasted; 'now' is the latest time in it unless you give one. Durations of failed runs are left out of the timings."}
    return finish(res, issues)
