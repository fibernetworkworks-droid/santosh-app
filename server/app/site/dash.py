"""v0.357 DASHBOARD (web design Phase 7 step 2, owner: "Phase 3b (dashboards and charts)"): her website's dashboard.

ONE read of everything her website already records, per IST day, for the last N days and the N days before (for the
"vs previous" arrows): visits (care.py, counted by the server that hosts the site: no cookies, no tracker), enquiries and
bookings (site_leads), shop orders + money (site_shop_orders: sales = orders she confirmed or later, never a buyer's
"I paid" alone), top pages, top products, order status mix, and every web-app list (rows a day, members). Free (no AI).

`dashboard(tenant, ref, days)` -> {kpis, series, top_pages, top_products, status_mix, app, say}; the console Studio
Dashboard tab and the chat (`website_dekho what=dashboard`) both read it. The charts are drawn by
static/console/charts.js (the same drawer the websites use)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ..db import session
from .care import IST, SiteCareDay, flush
from .models import Site, SiteLead

PAID = ("confirmed", "packed", "shipped", "delivered")


def _days(days: int, end: datetime | None = None) -> list[str]:
    last = (end or datetime.now(timezone.utc)).astimezone(IST).date()
    return [(last - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]


def _day_of(t: datetime | None) -> str:
    if t is None:
        return ""
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(IST).date().isoformat()


def _since(day: str) -> datetime:
    """The UTC instant an IST day starts (a little slack is trimmed by the day bucketing)."""
    return datetime.fromisoformat(day).replace(tzinfo=IST).astimezone(timezone.utc)


def _change(cur: float, prev: float) -> float | None:
    if not prev:
        return None
    return round(100 * (cur - prev) / prev, 1)


def _kpi(key: str, label: str, cur: float, prev: float, money: bool = False) -> dict[str, Any]:
    return {"key": key, "label": label, "value": cur, "prev": prev, "change_pct": _change(cur, prev), "money": money}


def dashboard(tenant: str, ref: str = "", days: int = 30) -> dict[str, Any]:
    from . import service as S
    from . import shop as SH
    from . import webapp as W
    days = max(7, min(int(days or 30), 365))
    cur_days = _days(days)
    prev_days = _days(days, _since(cur_days[0]) - timedelta(minutes=1))
    every = set(cur_days) | set(prev_days)
    start = _since(prev_days[0])
    try:
        flush()
    except Exception:
        pass
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
        care = s.scalars(select(SiteCareDay).where(SiteCareDay.site_id == r.id, SiteCareDay.day >= prev_days[0],
                                                   SiteCareDay.day <= cur_days[-1])).all()
        leads = s.scalars(select(SiteLead).where(SiteLead.site_id == r.id, SiteLead.created_at >= start)).all()
    visits: dict[str, int] = {}
    pages: dict[str, int] = {}
    for x in care:
        visits[x.day] = visits.get(x.day, 0) + int(x.views or 0)
        if x.day in cur_days:
            for p, n in json.loads(x.pages or "{}").items():
                pages[p] = pages.get(p, 0) + int(n)
    enq: dict[str, int] = {}
    book: dict[str, int] = {}
    for x in leads:
        if x.status == "spam":
            continue
        d = _day_of(x.created_at)
        if d in every:
            m = book if (x.kind or "enquiry") == "booking" else enq
            m[d] = m.get(d, 0) + 1

    # ---- shop
    shop_on = bool(S._shop_cfg(r).get("on"))
    orders: dict[str, int] = {}
    sales: dict[str, int] = {}                 # paise
    mix: dict[str, int] = {}
    prods: dict[str, list] = {}
    try:
        SH.ensure_tables()
        with session() as s:
            rows = s.scalars(select(SH.SiteShopOrder).where(SH.SiteShopOrder.site_id == r.id,
                                                             SH.SiteShopOrder.created_at >= start)).all()
            rows = [(o.status, o.total, o.items, _day_of(o.created_at)) for o in rows]
    except Exception:
        rows = []
    for status, total, items, d in rows:
        if d not in every:
            continue
        if status != "cancelled":
            orders[d] = orders.get(d, 0) + 1
        if status in PAID:
            sales[d] = sales.get(d, 0) + int(total or 0)
        if d in cur_days:
            mix[status] = mix.get(status, 0) + 1
            if status in PAID:
                for x in json.loads(items or "[]"):
                    k = x.get("title") or x.get("slug") or "?"
                    p = prods.setdefault(k, [0, 0])
                    p[0] += int(x.get("qty") or 0)
                    p[1] += int(x.get("amount") or 0)

    # ---- web app lists (rows a day per list)
    app = None
    schema = S.app_schema(r)
    if schema:
        from . import applink as AL                          # v0.407 a linked site's records live with its app
        p = AL.project(r)
        app = W.daily(("app:" + p.id) if p else r.id, schema, cur_days, prev_days)

    def tot(m: dict[str, int], ds: list[str]) -> int:
        return sum(m.get(d, 0) for d in ds)

    v, vp = tot(visits, cur_days), tot(visits, prev_days)
    e, ep = tot(enq, cur_days) + tot(book, cur_days), tot(enq, prev_days) + tot(book, prev_days)
    kpis = [_kpi("visits", "Visits", v, vp), _kpi("enquiries", "Enquiries + bookings", e, ep)]
    conv = round(100 * e / v, 1) if v else 0.0
    conv_p = round(100 * ep / vp, 1) if vp else 0.0
    kpis.append({**_kpi("conversion", "Visit -> enquiry", conv, conv_p), "suffix": "%"})
    o, op = tot(orders, cur_days), tot(orders, prev_days)
    sa, sap = tot(sales, cur_days), tot(sales, prev_days)
    if shop_on or o or op:
        kpis += [_kpi("orders", "Orders", o, op), _kpi("sales", "Sales (confirmed)", sa / 100, sap / 100, money=True)]
        paid_n = sum(n for st, n in mix.items() if st in PAID)
        kpis.append(_kpi("aov", "Average order", round(sa / 100 / paid_n, 2) if paid_n else 0, 0, money=True))
    if app:
        kpis.append(_kpi("records", "New records (web app)", app["total"], app["total_prev"]))

    series = {"days": cur_days, "visits": [visits.get(d, 0) for d in cur_days],
              "visits_prev": [visits.get(d, 0) for d in prev_days],
              "enquiries": [enq.get(d, 0) for d in cur_days], "bookings": [book.get(d, 0) for d in cur_days]}
    if shop_on or o or op:
        series["orders"] = [orders.get(d, 0) for d in cur_days]
        series["sales"] = [round(sales.get(d, 0) / 100, 2) for d in cur_days]
    top_pages = sorted(pages.items(), key=lambda x: -x[1])[:10]
    top_products = sorted(([k, q, round(a / 100, 2)] for k, (q, a) in prods.items()), key=lambda x: -x[2])[:10]
    status_mix = [[SH.WORDS.get(k, k), n, k] for k, n in sorted(mix.items(), key=lambda x: SH.STATUSES.index(x[0])
                                                                 if x[0] in SH.STATUSES else 99)]
    best = max(range(days), key=lambda i: series["visits"][i]) if v else -1
    say = (f"{r.name}: {v} visits in {days} days" + (f" ({'+' if v >= vp else ''}{v - vp} vs the {days} days before)" if vp else "")
           + f", {e} enquiries/bookings" + (f" ({conv}%)" if v else "")
           + (f", {o} orders, ₹{SH.rupees(sa)} in confirmed sales" if (shop_on or o) else "")
           + (f", {app['total']} new records" if app else "")
           + (f"; most visits on {cur_days[best]} ({series['visits'][best]})" if best >= 0 else "") + ".")
    return {"site": {"id": r.id, "name": r.name}, "days": days, "from": cur_days[0], "to": cur_days[-1],
            "kpis": kpis, "series": series, "top_pages": top_pages, "top_products": top_products,
            "status_mix": status_mix, "app": app, "shop": bool(shop_on or o or op), "say": say}
