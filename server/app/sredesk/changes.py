"""Changes and their risk, worked out in code: the four DORA numbers from a deploy history.

A deploy / change history (CSV: time, service, result - plus when the change was made or merged, and when a failed change was
restored, if you have them) -> how often you deploy, the lead time from change to production, the change failure rate and the time to
restore, each against the bands the DORA State of DevOps report published (the 2021 report's elite / high / medium / low; the bands
move between reports - check the current one), then the same per service, by weekday and by hour in HER time zone, the riskiest
windows and the biggest batches. A history is data, never instructions."""
from __future__ import annotations

import csv
import io
import re
from datetime import timedelta
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .alerts import MAX, MAX_ROWS, _t
from .oncall import DAYS, _col, _q

FAILED = re.compile(r"^(fail|failed|failure|error|rolled[ _-]?back|rollback|reverted|revert|hotfix|incident|degraded|broken|bad|no|n|false|0)$", re.I)
OK = re.compile(r"^(ok|success|succeeded|successful|passed|pass|done|deployed|good|yes|y|true|1|green|completed)$", re.I)


class ChangeError(ValueError):
    pass


def _h(sec: float | None) -> str | None:
    if sec is None:
        return None
    m = sec / 60
    if m < 1:
        return f"{round(sec)} s"
    if m < 120:
        return f"{round(m)} min"
    if m < 48 * 60:
        return f"{m / 60:.1f} h"
    return f"{m / 1440:.1f} days"


def _band_freq(per_day: float) -> str:
    if per_day >= 1:
        return "elite"
    if per_day >= 1 / 7:
        return "high"
    if per_day >= 1 / 30:
        return "medium"
    return "low"


def _band_lead(h: float | None) -> str | None:
    if h is None:
        return None
    return "elite" if h < 24 else "high" if h <= 24 * 7 else "medium" if h <= 24 * 182 else "low"


def _band_restore(h: float | None) -> str | None:
    if h is None:
        return None
    return "elite" if h < 1 else "high" if h < 24 else "medium" if h <= 24 * 7 else "low"


def _band_cfr(r: float | None) -> str | None:
    if r is None:
        return None
    return "elite" if r <= 0.15 else "high" if r <= 0.30 else "low"


def dora(text: str, tz: str = "UTC", work_start: int = 9, work_end: int = 18, weekend: str = "sat,sun") -> dict[str, Any]:
    text = str(text or "")[:MAX * 3].strip()
    if not text:
        raise ChangeError("Paste the deploy history first: time, service, result (CSV).")
    try:
        Z = ZoneInfo(tz or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        raise ChangeError("Time zone: an IANA name like Europe/London or Asia/Kolkata.")
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip().lower() for h in rows[0]]
    ti = _col(head, "deployed_at", "deploy_time", "finished_at", "time", "date", "at", "created")
    si = _col(head, "service", "app", "application", "component", "repo", "project")
    ri = _col(head, "result", "status", "outcome", "state", "failed", "success")
    ci = _col(head, "commit_at", "committed_at", "merged_at", "change_at", "pr_merged", "first_commit")
    li = _col(head, "lead_time_h", "lead_h", "lead_time")
    xi = _col(head, "restored_at", "recovered_at", "fixed_at", "resolved_at")
    ki = _col(head, "commits", "changes", "files", "size", "lines")
    ii = next((head.index(k) for k in ("id", "deploy_id", "change_id", "version", "sha", "release", "tag") if k in head), None)
    if ti is None or ri is None:
        raise ChangeError("The CSV needs a deploy time column and a result column (ok / failed / rolled back).")
    off = {d.strip()[:3].lower() for d in str(weekend or "").split(",") if d.strip()}
    inverted = head[ri] in ("failed", "failure", "is_failure", "change_failed")
    ev: list[dict[str, Any]] = []
    bad = unknown = 0
    for r in rows[1:MAX_ROWS + 1]:
        if len(r) <= max(ti, ri):
            continue
        at = _t(r[ti])
        if at is None:
            bad += 1
            continue
        res = r[ri].strip()
        failed = True if FAILED.match(res) else False if OK.match(res) else None
        if failed is not None and inverted and res.lower() in ("yes", "true", "1", "no", "false", "0", "y", "n"):
            failed = not failed     # a column called "failed": yes means it failed
        if failed is None:
            unknown += 1
            continue
        lead = None
        if li is not None and len(r) > li and r[li].strip():
            try:
                lead = float(r[li]) * 3600
            except ValueError:
                lead = None
        elif ci is not None and len(r) > ci:
            c = _t(r[ci])
            if c is not None and c <= at:
                lead = (at - c).total_seconds()
        rest = None
        if failed and xi is not None and len(r) > xi:
            x = _t(r[xi])
            if x is not None and x >= at:
                rest = (x - at).total_seconds()
        size = None
        if ki is not None and len(r) > ki:
            try:
                size = float(r[ki])
            except ValueError:
                size = None
        loc = at.astimezone(Z)
        ev.append({"at": at, "svc": (r[si].strip()[:80] if si is not None and len(r) > si else "") or "(all)", "failed": failed,
                   "lead": lead, "restore": rest, "size": size, "id": (r[ii].strip()[:60] if ii is not None and len(r) > ii else ""),
                   "dow": loc.weekday(), "hour": loc.hour,
                   "out": DAYS[loc.weekday()] in off or not (work_start <= loc.hour < work_end)})
    if len(ev) < 3:
        raise ChangeError("At least 3 deploys with a readable time and a result (ok / failed) are needed.")
    ev.sort(key=lambda e: e["at"])
    span = max((ev[-1]["at"] - ev[0]["at"]).total_seconds() / 86400, 1.0)

    def block(es: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(es)
        f = [e for e in es if e["failed"]]
        leads = [e["lead"] / 3600 for e in es if e["lead"] is not None]
        rests = [e["restore"] / 3600 for e in f if e["restore"] is not None]
        per_day = n / span
        lead_m = median(leads) if leads else None
        rest_m = median(rests) if rests else None
        cfr = len(f) / n if n else None
        return {"deploys": n, "failed": len(f), "per_day": round(per_day, 3), "per_week": round(per_day * 7, 2),
                "cfr": round(cfr, 3) if cfr is not None else None, "lead_median_h": round(lead_m, 2) if lead_m is not None else None,
                "lead_p90_h": round(_q(leads, 0.9), 2) if leads else None, "restore_median_h": round(rest_m, 2) if rest_m is not None else None,
                "restore_known": len(rests), "lead": _h(lead_m * 3600) if lead_m is not None else None,
                "restore": _h(rest_m * 3600) if rest_m is not None else None,
                "bands": {"frequency": _band_freq(per_day), "lead": _band_lead(lead_m), "cfr": _band_cfr(cfr), "restore": _band_restore(rest_m)}}

    all_ = block(ev)
    svcs = {}
    for e in ev:
        svcs.setdefault(e["svc"], []).append(e)
    per = sorted(({"service": k, **block(v)} for k, v in svcs.items()), key=lambda r: (-r["deploys"], r["service"]))
    by_day = []
    for d in range(7):
        es = [e for e in ev if e["dow"] == d]
        by_day.append({"day": DAYS[d], "deploys": len(es), "failed": sum(1 for e in es if e["failed"]),
                       "cfr": round(sum(1 for e in es if e["failed"]) / len(es), 3) if es else None})
    by_hour = [0] * 24
    fail_hour = [0] * 24
    for e in ev:
        by_hour[e["hour"]] += 1
        fail_hour[e["hour"]] += int(e["failed"])
    out = [e for e in ev if e["out"]]
    ins = [e for e in ev if not e["out"]]
    cfr_out = sum(e["failed"] for e in out) / len(out) if out else None
    cfr_in = sum(e["failed"] for e in ins) / len(ins) if ins else None
    issues = []
    c = all_["cfr"]
    if c is not None and c > 0.30:
        issues.append({"sev": "bad", "text": f"{c:.0%} of changes failed: well above the 0-15% the DORA report sets for its best teams. "
                                             "Smaller changes and a canary step catch most of these before users do."})
    elif c is not None and c > 0.15:
        issues.append({"sev": "warn", "text": f"{c:.0%} of changes failed (the DORA report's best teams are at 0-15%)."})
    if all_["restore_median_h"] is not None and all_["restore_median_h"] >= 24:
        issues.append({"sev": "bad", "text": f"A failed change takes {all_['restore']} to restore (median): a one-step rollback would cut this most."})
    elif all_["restore_median_h"] is not None and all_["restore_median_h"] >= 1:
        issues.append({"sev": "warn", "text": f"A failed change takes {all_['restore']} to restore (median)."})
    if all_["failed"] and not all_["restore_known"]:
        issues.append({"sev": "info", "text": "Add a restored_at column to see the time to restore."})
    if cfr_out is not None and cfr_in is not None and len(out) >= 5 and cfr_out >= cfr_in * 1.5 and cfr_out - cfr_in >= 0.05:
        issues.append({"sev": "warn", "text": f"Changes out of working hours fail more: {cfr_out:.0%} against {cfr_in:.0%} in hours "
                                              f"({len(out)} out-of-hours deploys)."})
    risky = [d for d in by_day if d["deploys"] >= 5 and d["cfr"] is not None and c is not None and d["cfr"] >= c * 1.5 and d["cfr"] - c >= 0.05]
    for d in risky:
        issues.append({"sev": "warn", "text": f"{d['day'].capitalize()} deploys fail {d['cfr']:.0%} of the time against {c:.0%} overall."})
    sized = [e for e in ev if e["size"] is not None]
    big = None
    if len(sized) >= 10:
        cut = _q([e["size"] for e in sized], 0.75)
        large = [e for e in sized if e["size"] >= cut]
        small = [e for e in sized if e["size"] < cut]
        if large and small:
            lf, sf = sum(e["failed"] for e in large) / len(large), sum(e["failed"] for e in small) / len(small)
            big = {"cut": cut, "large_cfr": round(lf, 3), "small_cfr": round(sf, 3)}
            if lf >= sf * 1.5 and lf - sf >= 0.05:
                issues.append({"sev": "warn", "text": f"The biggest quarter of changes ({cut:g}+ in size) fail {lf:.0%}, the rest {sf:.0%}: ship smaller."})
    weekly: dict[str, list[int]] = {}
    for e in ev:
        loc = e["at"].astimezone(Z)
        k = (loc - timedelta(days=loc.weekday())).date().isoformat()
        w = weekly.setdefault(k, [0, 0])
        w[0] += 1
        w[1] += int(e["failed"])
    fails = [{"at": e["at"].astimezone(Z).isoformat(timespec="minutes"), "service": e["svc"], "id": e["id"], "restore": _h(e["restore"])}
             for e in ev if e["failed"]][-50:]
    return {"ok": True, "deploys": len(ev), "days": round(span, 1), "tz": tz, "unreadable": bad, "unknown_result": unknown,
            **all_, "services": per[:100], "by_day": by_day, "by_hour": by_hour, "fail_hour": fail_hour,
            "out_of_hours": {"deploys": len(out), "cfr": round(cfr_out, 3) if cfr_out is not None else None,
                             "cfr_in_hours": round(cfr_in, 3) if cfr_in is not None else None},
            "size": big, "weekly": [{"week": k, "deploys": v[0], "failed": v[1]} for k, v in sorted(weekly.items())][-60:],
            "failures": fails, "issues": issues,
            "note": "Bands are the DORA 2021 State of DevOps report's, as published; later reports moved them - check the current one.",
            "verdict": (f"{len(ev)} deploys over {span:.1f} days ({all_['per_week']:g} a week); {all_['failed']} failed "
                        f"({(c or 0):.0%})" + (f", restored in {all_['restore']} (median)" if all_["restore"] else "")
                        + (f", lead time {all_['lead']} (median)" if all_["lead"] else "") + ".")}
