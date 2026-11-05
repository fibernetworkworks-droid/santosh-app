"""v0.534 WEBSITE LOAD PROOF (web Step 6, W10: "load test before launch of big sites: thousands of visitors + orders, no
lost or double orders").

`run()` drives a REAL server (any number of worker processes) the way a sale-day crowd would:
  * VISITORS open the catalogue - listing pages, item pages, the filter index - from the site's own files;
  * BUYERS check out through the public shop API from many addresses at once, a "hot" product with little stock taking
    most of the crowd, and every RETRY_EVERY-th buyer sending the same checkout twice at the same moment (a double tap /
    a slow network);
then `verify()` reads the database and proves: every accepted checkout is exactly one order (no lost order, no double
order for a retried one), no two orders share a number, stock never went below zero and the stock taken equals what
the orders say, and the server never answered 500.

It never runs against her live shop (it places real orders): the proof builds its own throwaway marketplace
(tests/test_v0531_bada_catalogue.py, CI app-load.yml with 4 workers on Postgres)."""
from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any

RETRY_EVERY = 4


async def _visitor(c, base: str, paths: list[str], n: int, codes: dict[int, int], times: list[float]) -> None:
    for _ in range(n):
        p = random.choice(paths)
        t0 = time.perf_counter()
        try:
            r = await c.get(base + p, headers={"Accept-Encoding": "gzip"})
            codes[r.status_code] = codes.get(r.status_code, 0) + 1
        except Exception:                                    # noqa: BLE001
            codes[0] = codes.get(0, 0) + 1
        times.append(time.perf_counter() - t0)


async def _buyer(c, api: str, i: int, slug: str, out: dict[str, Any]) -> None:
    body = {"name": f"Buyer {i}", "phone": f"9{i:09d}"[-10:], "address": f"{i} Station Road, Akola", "pincode": "444001",
            "method": "cod", "items": [{"slug": slug, "qty": 1}], "cid": f"lt-{i}"}
    hdr = {"X-Real-IP": f"10.{(i >> 16) & 255}.{(i >> 8) & 255}.{i & 255}"}
    tries = 2 if i % RETRY_EVERY == 0 else 1

    async def one():
        try:
            r = await c.post(api + "/order", json=body, headers=hdr)
            return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})
        except Exception:                                    # noqa: BLE001
            return 0, {}
    got = await asyncio.gather(*[one() for _ in range(tries)])
    for code, j in got:
        out["codes"][code] = out["codes"].get(code, 0) + 1
        if code == 200 and j.get("number"):
            out["ok"].setdefault(body["cid"], set()).add(j["number"])
    if tries == 2:
        out["retried"] += 1


async def run(page_base: str, api: str, item_paths: list[str], buy: list[str], hot: str = "", visitors: int = 2000,
              pages_each: int = 3, buyers: int = 500, hot_share: float = 0.4, concurrency: int = 200) -> dict[str, Any]:
    import httpx
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    out: dict[str, Any] = {"codes": {}, "ok": {}, "retried": 0}
    vcodes: dict[int, int] = {}
    times: list[float] = []
    sem = asyncio.Semaphore(concurrency)
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0, limits=limits) as c:
        async def guard(coro):
            async with sem:
                await coro
        jobs = [guard(_visitor(c, page_base, item_paths, pages_each, vcodes, times)) for _ in range(visitors)]
        rnd = random.Random(7)
        for i in range(1, buyers + 1):
            slug = hot if hot and rnd.random() < hot_share else rnd.choice(buy)
            jobs.append(guard(_buyer(c, api, i, slug, out)))
        rnd.shuffle(jobs)
        await asyncio.gather(*jobs)
    took = time.perf_counter() - t0
    times.sort()
    pct = lambda q: round(times[min(len(times) - 1, int(q * len(times)))] * 1000) if times else 0  # noqa: E731
    return {"seconds": round(took, 1), "visitors": visitors, "page_views": len(times), "page_codes": vcodes,
            "page_p50_ms": pct(0.5), "page_p95_ms": pct(0.95), "buyers": buyers, "retried": out["retried"],
            "order_codes": out["codes"], "accepted": {k: sorted(v) for k, v in out["ok"].items()}}


def verify(site_id: str, before: dict[str, int | None], res: dict[str, Any]) -> dict[str, Any]:
    """The database after the crowd: one order per accepted checkout, unique numbers, stock never below zero and equal to
    what the orders took. Returns the findings (empty problems = passed)."""
    from sqlalchemy import select
    from ..db import session
    from . import shop as SH
    with session() as s:
        orders = s.scalars(select(SH.SiteShopOrder).where(SH.SiteShopOrder.site_id == site_id)).all()
        prods = {p.slug: p.stock for p in s.scalars(select(SH.SiteShopProduct).where(SH.SiteShopProduct.site_id == site_id)).all()}
        rows = [(o.cid, o.number, json.loads(o.items or "[]")) for o in orders]
    problems = []
    acc = res["accepted"]
    by_cid: dict[str, list[str]] = {}
    for cid, num, _ in rows:
        by_cid.setdefault(cid or "", []).append(num)
    double = [c for c, v in by_cid.items() if c and len(v) > 1]
    if double:
        problems.append(f"{len(double)} checkouts became two orders")
    split = [c for c, nums in acc.items() if len(nums) > 1]
    if split:
        problems.append(f"{len(split)} retried checkouts got two different numbers")
    lost = [c for c in acc if c not in by_cid]
    if lost:
        problems.append(f"{len(lost)} accepted checkouts have no order")
    nums = [n for _, n, _ in rows]
    if len(set(nums)) != len(nums):
        problems.append(f"{len(nums) - len(set(nums))} order numbers used twice")
    taken: dict[str, int] = {}
    for _, _, items in rows:
        for ln in items:
            taken[ln["slug"]] = taken.get(ln["slug"], 0) + int(ln["qty"])
    for sg, st in before.items():
        if st is None:
            continue
        now_st = prods.get(sg)
        if now_st is None or now_st < 0:
            problems.append(f"{sg}: stock {now_st}")
        elif st - now_st != taken.get(sg, 0):
            problems.append(f"{sg}: stock moved {st - now_st}, orders took {taken.get(sg, 0)}")
    if res["order_codes"].get(500) or res["page_codes"].get(500):
        problems.append("server answered 500")
    return {"orders": len(rows), "accepted": len(acc), "sold_out_refusals": res["order_codes"].get(409, 0),
            "problems": problems, "passed": not problems}
