"""Commitments (savings plans, reserved instances, committed use discounts) sized from her own usage: given her hourly (or daily)
usage - instance-hours, vCPUs, or on-demand spend per hour - and the on-demand and committed prices (or the discount), the level
that would have cost least over the period, a safer level that keeps most of the saving with less commitment, the break-even use,
and how her current commitment did (how much of it was used, how much of the usage it covered). A commitment is paid every hour
whether it is used or not, so the answer is only as good as the period she gives being like the term ahead."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from ..mldesk.table import TableError, read
from .common import ClInputError, amt, col, finder, finish, median, num


class CommitError(TableError):
    pass


def _time(v: str) -> datetime:
    s = str(v or "").strip().replace("Z", "+00:00").replace("/", "-")
    if len(s) == 10:
        s += "T00:00:00"
    try:
        t = datetime.fromisoformat(s.replace(" ", "T", 1) if "T" not in s else s)
    except ValueError:
        raise ClInputError(f"'{v}' is not a time (use 2026-11-01 13:00).")
    return t.replace(tzinfo=None)


def _cost(us: list[float], w: float, c: float, od: float, cr: float) -> tuple[float, float, float]:
    """(total cost, commitment used, usage covered) over the period for a commitment of c units an hour."""
    used = sum(min(u, c) for u in us) * w
    over = sum(max(0.0, u - c) for u in us) * w
    hours = len(us) * w
    return c * cr * hours + over * od, used, used


def plan(text: str, od_rate: float | None = None, commit_rate: float | None = None, discount: float | None = None, current: float | None = None,
         unit: str = "", currency: str = "") -> dict[str, Any]:
    head, rows = read(text, "The usage")
    it = col(head, r"time", r"timestamp", r"hour", r"date", r"day", r"usagestart", r"usagestartdate", r"period", r"chargeperiodstart")
    iu = col(head, r"usage", r"units", r"quantity", r"instancehours", r"hours", r"vcpus?", r"vcpuhours", r"spend", r"ondemandspend", r"ondemandcost", r"cost", r"amount", r"value")
    if it is None or iu is None:
        raise CommitError("The usage needs a time column and a usage column (instance-hours, vCPUs, or on-demand spend per hour).")
    money_usage = bool(re.search(r"spend|cost|amount", head[iu], re.I))
    if money_usage:
        od = 1.0
        if discount is None and commit_rate is not None and od_rate:
            discount = 1 - commit_rate / od_rate
        if discount is None:
            raise CommitError("The usage is on-demand spend - give the discount the commitment brings (for example 0.28 for 28%).")
        cr = 1.0 - discount
    else:
        if od_rate is None:
            raise CommitError("Give the on-demand price per unit-hour (od_rate).")
        od = float(od_rate)
        if commit_rate is None and discount is None:
            raise CommitError("Give the committed price per unit-hour (commit_rate) or the discount.")
        cr = float(commit_rate) if commit_rate is not None else od * (1 - float(discount))
    if not 0 < cr < od:
        raise CommitError("The committed price must be below the on-demand price.")
    pts = []
    for r in rows:
        try:
            t, u = _time(r[it]), num(r[iu])
        except ClInputError as e:
            raise CommitError(str(e))
        if u is None:
            continue
        if u < 0:
            raise CommitError(f"{r[it]}: usage below zero.")
        pts.append((t, u))
    if len(pts) < 24:
        raise CommitError("Give at least 24 rows of usage - a week of hours is better, a month best.")
    pts.sort()
    gaps = [(b[0] - a[0]).total_seconds() / 3600 for a, b in zip(pts, pts[1:]) if b[0] > a[0]]
    step = median(gaps) if gaps else 1.0
    daily = step >= 20
    w = 24.0 if daily else max(step, 1e-9)
    us = [u / w for _, u in pts]     # units in use per hour, on average over each row
    hours = len(us) * w
    issues, add = finder()
    total_od = sum(us) * w * od
    cand = sorted(set([0.0] + us))
    best_c, best_cost = 0.0, total_od
    curve = []
    for c in cand:
        cost, _, _ = _cost(us, w, c, od, cr)
        if cost < best_cost - 1e-9:
            best_c, best_cost = c, cost
    max_save = total_od - best_cost
    safe_c = best_c
    for c in cand:
        if c > best_c:
            break
        cost, _, _ = _cost(us, w, c, od, cr)
        if total_od - cost >= 0.9 * max_save:
            safe_c = c
            break
    top = max(us)
    for c in sorted({top * i / 20 for i in range(21)} | {best_c, safe_c} | ({float(current)} if current is not None and float(current) <= top * 1.5 else set())):
        cost, used, _ = _cost(us, w, c, od, cr)
        curve.append({"commit": c, "save": total_od - cost, "util": used / (c * hours) if c else None})

    def level(c: float) -> dict[str, Any]:
        cost, used, cov = _cost(us, w, c, od, cr)
        return {"commit": c, "cost": cost, "save": total_od - cost, "save_pct": (total_od - cost) / total_od if total_od else 0.0,
                "util": used / (c * hours) if c else None, "coverage": cov / (sum(us) * w) if sum(us) else 0.0, "spend": c * cr * hours}
    best, safe = level(best_c), level(safe_c)
    cur = level(float(current)) if current is not None else None
    be = cr / od
    u_word = "of on-demand spend an hour" if money_usage else (unit or "units") + " an hour"
    if best_c > 0:
        add("info", "Best level", f"A commitment of {best_c:,.4g} {u_word} would have cost least - saving {amt(best['save'], currency)} "
            f"({best['save_pct'] * 100:.0f}%) over the {hours / 24:.0f} day(s), used {best['util'] * 100:.0f}% of the time it was paid for.",
            "Buy in steps - a part now, more after a month of steady use.")
    else:
        add("warn", "No commitment", "Over this period no commitment level beats paying on demand - the usage is too spiky for the discount.",
            "Look at the steady part again after reducing the peaks, or keep paying on demand.")
    if safe_c < best_c:
        add("info", "Safer level", f"{safe_c:,.4g} {u_word} keeps 90% of that saving ({amt(safe['save'], currency)}) with {(1 - safe_c / best_c) * 100:.0f}% less committed.",
            "Prefer it if the usage may fall during the term.")
    if cur:
        if cur["util"] is not None and cur["util"] < be:
            add("bad", "Current commitment", f"Your commitment of {float(current):,.4g} was used {cur['util'] * 100:.0f}% of the time - below the {be * 100:.0f}% it needs to pay off.",
                "Do not renew at this level; move usage onto it or let part of it expire.")
        elif cur["util"] is not None and cur["util"] < 0.95:
            add("warn", "Current commitment", f"Your commitment was used {cur['util'] * 100:.0f}% of the time; {(1 - cur['util']) * 100:.0f}% was paid for and unused.",
                "Move matching usage onto it before buying more.")
        if best_c and float(current) > best_c * 1.05 and best["save"] > cur["save"]:
            add("info", "Committed above the best level", f"Your commitment of {float(current):,.4g} is above the {best_c:,.4g} that cost least - "
                f"{amt(best['save'] - cur['save'], currency)} more was paid over the period than needed.", "Let the extra expire at renewal.")
        if float(current) < best_c * 0.8:
            add("info", "Room to commit", f"Usage stayed above your commitment: {best_c:,.4g} would have saved {amt(best['save'] - cur['save'], currency)} more.",
                "Add commitment in steps.")
    if daily:
        add("warn", "Daily rows", "The usage is per day, so dips within a day are hidden and use of a commitment looks higher than it is.", "Export hourly usage for the real figure.")
    res = {"rows": len(pts), "hours": hours, "daily": daily, "od_rate": od, "commit_rate": cr, "discount": 1 - cr / od, "breakeven": be,
           "money_usage": money_usage, "unit": u_word, "total_od": total_od, "best": best, "safe": safe, "current": cur, "curve": curve,
           "use": {"min": min(us), "p10": sorted(us)[len(us) // 10], "median": median(us), "max": top}, "currency": currency,
           "verdict": (f"Best commitment {best_c:,.4g} {u_word}, saving {best['save_pct'] * 100:.0f}%" if best_c else "No commitment beats on demand")}
    res["note"] = ("Worked out on the usage you gave, hour by hour, as if the term ahead looks the same. A commitment is paid whether it is used or "
                   "not; usage that falls during the term turns a saving into a loss. Prices are the ones you gave - check them against your provider's price list.")
    return finish(res, issues)
