"""The cloud bill read the way a FinOps practitioner reads it: an export of cost lines (the FOCUS standard columns, AWS Cost and
Usage Report, Google Cloud billing export, Azure cost details, or any CSV with a cost and a date) added up by day, service,
account, region and her owner tag; spend nobody owns; days that jumped above their own recent level and the service that did it;
the services that grew this week; credits; and the month at its current run rate against her budget. Amounts are in the
export's own currency - never converted, and two currencies are never added together."""
from __future__ import annotations

import calendar
import json
import re
from collections import defaultdict
from datetime import timedelta
from typing import Any

from ..mldesk.table import TableError, read
from .common import ClInputError, amt, col, day, finder, finish, median, money, norm


class BillError(TableError):
    pass


COST = (r"billedcost", r"effectivecost", r"lineitemunblendedcost", r"unblendedcost", r"costinbillingcurrency", r"pretaxcost",
        r"costinusd", r"cost", r"amount", r"charge", r"spend")
DATE = (r"chargeperiodstart", r"lineitemusagestartdate", r"usagestartdate", r"usagestarttime", r"usagedate", r"date", r"day",
        r"billingperiodstart", r"period")
SERVICE = (r"servicename", r"productproductname", r"productservicename", r"lineitemproductcode", r"servicedescription",
           r"metercategory", r"consumedservice", r"service", r"product")
ACCOUNT = (r"subaccountname", r"subaccountid", r"lineitemusageaccountname", r"lineitemusageaccountid", r"projectname", r"projectid",
           r"subscriptionname", r"subscriptionid", r"accountname", r"accountid", r"account", r"project", r"subscription")
REGION = (r"regionname", r"regionid", r"productregioncode", r"productregion", r"locationregion", r"resourcelocation", r"region", r"location")
CURRENCY = (r"billingcurrency", r"currency", r"currencycode")


def _tags(v: str) -> dict[str, str]:
    s = str(v or "").strip()
    if not s:
        return {}
    if s.startswith("{"):
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                return {str(k).lower().split("/")[-1].replace("user:", ""): str(x) for k, x in d.items()}
        except ValueError:
            pass
    out = {}
    for part in re.split(r"[;,|]", s.strip("{}")):
        m = re.match(r'\s*"?([^":=]+)"?\s*[:=]\s*"?([^"]*)"?\s*$', part)
        if m:
            out[m.group(1).strip().lower().replace("user:", "")] = m.group(2).strip()
    return out


def _top(d: dict[str, float], total: float, n: int = 12) -> list[dict[str, Any]]:
    rows = sorted(d.items(), key=lambda kv: -kv[1])
    out = [{"name": k, "cost": v, "share": v / total if total else 0.0} for k, v in rows[:n]]
    rest = sum(v for _, v in rows[n:])
    if rest:
        out.append({"name": f"{len(rows) - n} more", "cost": rest, "share": rest / total if total else 0.0})
    return out


def analyse(text: str, tag_key: str = "", budget: float | None = None, sens: float = 3.0, currency: str = "") -> dict[str, Any]:
    head, rows = read(text, "The bill")
    ic, idt = col(head, *COST), col(head, *DATE)
    if ic is None:
        raise BillError("The bill needs a cost column (BilledCost, EffectiveCost, lineItem/UnblendedCost, cost, CostInBillingCurrency...).")
    if idt is None:
        raise BillError("The bill needs a date column (ChargePeriodStart, lineItem/UsageStartDate, usage_start_time, Date...).")
    isv, iac, irg, icur = col(head, *SERVICE), col(head, *ACCOUNT), col(head, *REGION), col(head, *CURRENCY)
    tk = norm(tag_key) if tag_key else ""
    itag = None
    if tk:
        for i, h in enumerate(head):
            n = norm(h)
            if n == tk or (n.endswith(tk) and ("tag" in n or "label" in n)):
                itag = i
                break
    itags = col(head, r"tags", r"resourcetags", r"labels")
    issues, add = finder()
    by_day: dict[Any, float] = defaultdict(float)
    by_sd: dict[tuple[Any, str], float] = defaultdict(float)
    by = {"service": defaultdict(float), "account": defaultdict(float), "region": defaultdict(float), "owner": defaultdict(float)}
    curs: set[str] = set()
    credits = untagged = 0.0
    for r in rows:
        try:
            c = money(r[ic])
            d = day(r[idt])
        except ClInputError as e:
            raise BillError(str(e))
        if c is None or d is None:
            continue
        if icur is not None and r[icur].strip():
            curs.add(r[icur].strip().upper())
        if c < 0:
            credits += c
        sv = (r[isv] if isv is not None else "") or "(no service)"
        by_day[d] += c
        by_sd[(d, sv)] += c
        by["service"][sv] += c
        if iac is not None:
            by["account"][r[iac] or "(no account)"] += c
        if irg is not None:
            by["region"][r[irg] or "(global)"] += c
        if tk:
            own = (r[itag] if itag is not None else "") or (_tags(r[itags]).get(tag_key.lower(), "") if itags is not None else "")
            by["owner"][("(credits)" if c < 0 else own or "(untagged)")] += c
            if not own and c > 0:
                untagged += c
    if not by_day:
        raise BillError("No cost lines with both an amount and a date.")
    if len(curs) > 1:
        raise BillError(f"The bill mixes currencies ({', '.join(sorted(curs))}) - export one currency, or split it; amounts are never converted here.")
    cur = (next(iter(curs)) if curs else "") or currency
    days = sorted(by_day)
    total = sum(by_day.values())
    gross = total - credits
    series = [{"day": d.isoformat(), "cost": by_day.get(d, 0.0)} for d in (days[0] + timedelta(n) for n in range((days[-1] - days[0]).days + 1))]
    vals = [x["cost"] for x in series]
    # spikes: a day above its own previous 14 days (at least 7) by sens x the robust spread and at least 25%
    spikes = []
    for i, x in enumerate(series):
        prev = vals[max(0, i - 14):i]
        if len(prev) < 7:
            continue
        base = median(prev)
        mad = median([abs(v - base) for v in prev]) * 1.4826
        if x["cost"] > base + sens * max(mad, 0.05 * abs(base)) and x["cost"] > base * 1.25 and x["cost"] - base > 0.005 * gross:
            d = days[0] + timedelta(i)
            dprev = [days[0] + timedelta(j) for j in range(max(0, i - 14), i)]
            grow = {}
            for sv in by["service"]:
                b = median([by_sd.get((p, sv), 0.0) for p in dprev])
                grow[sv] = by_sd.get((d, sv), 0.0) - b
            who = max(grow, key=grow.get) if grow else ""
            spikes.append({"day": d.isoformat(), "cost": x["cost"], "base": base, "over": x["cost"] - base, "service": who, "service_over": grow.get(who, 0.0)})
    for s in spikes[:5]:
        add("warn", "Spike", f"{s['day']}: {amt(s['cost'], cur)} against a usual {amt(s['base'], cur)} - mostly {s['service']} (+{amt(s['service_over'], cur)}).",
            "Open that day in the cost explorer, grouped by usage type or SKU, to find the resource.", s["day"])
    movers = []
    if len(series) >= 14:
        last = {d for d in (days[-1] - timedelta(n) for n in range(7))}
        prev7 = {d for d in (days[-1] - timedelta(n) for n in range(7, 14))}
        for sv in by["service"]:
            a = sum(v for (d, s_), v in by_sd.items() if s_ == sv and d in last)
            b = sum(v for (d, s_), v in by_sd.items() if s_ == sv and d in prev7)
            if a - b > 0 and (b <= 0 or a / b > 1.05):
                movers.append({"service": sv, "last7": a, "prev7": b, "change": a - b, "ratio": (a / b) if b > 0 else None})
        movers.sort(key=lambda m: -m["change"])
        movers = movers[:8]
        for m in movers[:3]:
            if m["change"] > 0.02 * gross and (m["ratio"] is None or m["ratio"] > 1.2):
                add("info", "Growing", f"{m['service']}: {amt(m['last7'], cur)} in the last 7 days against {amt(m['prev7'], cur)} the 7 before"
                    + (f" ({(m['ratio'] - 1) * 100:.0f}% more)." if m["ratio"] else " (new)."), "Check whether the growth is planned.", m["service"])
    # the month at its run rate: the last month in the export
    lm = days[-1]
    in_month = [d for d in days if (d.year, d.month) == (lm.year, lm.month)]
    so_far = sum(by_day[d] for d in in_month)
    dim = calendar.monthrange(lm.year, lm.month)[1]
    left = dim - lm.day
    recent = vals[-7:]
    rate = sum(recent) / len(recent)
    forecast = so_far + rate * left
    month = {"month": f"{lm.year}-{lm.month:02d}", "so_far": so_far, "days_in": lm.day, "days_left": left, "rate": rate, "forecast": forecast,
             "complete": left == 0}
    if budget:
        month["budget"] = budget
        if forecast > budget:
            add("bad" if forecast > budget * 1.1 else "warn", "Budget", f"{month['month']} is heading for {amt(forecast, cur)} at the last 7 days' rate - over the budget of {amt(budget, cur)} by {amt(forecast - budget, cur)}.",
                "Find what grew (Growing, Spikes) before the month closes.")
    if tk:
        share = untagged / gross if gross else 0.0
        if share > 0.1:
            add("warn", "Untagged", f"{amt(untagged, cur)} ({share * 100:.0f}%) has no '{tag_key}' tag - nobody answers for it.",
                f"Tag the resources (or set a tag policy) so every line has a '{tag_key}'.")
        if itag is None and itags is None:
            add("info", "Tag column", f"No '{tag_key}' column or tags column found - owner totals need one.", f"Export with the '{tag_key}' tag as a column.")
    if credits:
        add("info", "Credits", f"{amt(-credits, cur)} of credits or refunds are in the bill - the total is after them.", "Credits end; plan for the bill without them.")
    res = {"currency": cur, "rows": len(rows), "first": days[0].isoformat(), "last": days[-1].isoformat(), "days": len(series), "total": total,
           "gross": gross, "credits": credits, "untagged": untagged if tk else None, "tag_key": tag_key, "series": series, "spikes": spikes,
           "movers": movers, "month": month, "by": {k: _top(v, gross) for k, v in by.items() if v},
           "columns": {"cost": head[ic], "date": head[idt], "service": head[isv] if isv is not None else None, "account": head[iac] if iac is not None else None,
                       "region": head[irg] if irg is not None else None},
           "verdict": f"{amt(total, cur)} over {len(series)} day(s), {series[0]['day']} to {series[-1]['day']}"
                      + (f"; {month['month']} heading for {amt(forecast, cur)}" if not month["complete"] else "")}
    res["note"] = (f"Amounts are added as they are in the '{head[ic]}' column, in the export's currency. The month forecast is the spend so far plus the "
                   "average of the last 7 days for each day left - a run rate, not a prediction.")
    return finish(res, issues)
