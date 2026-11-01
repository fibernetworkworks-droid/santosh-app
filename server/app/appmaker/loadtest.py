"""v0.388 PAKKI NEEV proof: many customers at once against an app's real server - nothing oversold, nothing doubled.

    python -m app.appmaker.loadtest --base http://127.0.0.1:8077 --key ak... --product <id> --customers 1000

Each customer signs up + logs in, then ALL of them order at the same moment (1 piece each of a product with limited
stock); every 4th customer's phone "retries" the same order (same cid) at the same time, like a flaky network.
Run it ONLY against a throwaway test app (it makes real accounts and orders). The CI job runs it against 4 server
worker processes on one Postgres and then checks the database: orders == min(customers, stock), stock never < 0,
one row per cid."""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
import uuid
from typing import Any


async def run(base: str, key: str, product: str, customers: int = 1000, concurrency: int = 250,
              retry_every: int = 4) -> dict[str, Any]:
    import httpx
    api = f"{base.rstrip('/')}/api/app-api/{key}"
    lim = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    sem = asyncio.Semaphore(concurrency)
    lat: dict[str, list[float]] = {"signup": [], "order": []}
    codes: dict[str, dict[int, int]] = {"signup": {}, "login": {}, "order": {}}
    tag = uuid.uuid4().hex[:6]

    async def call(c, kind, method, path, body=None, headers=None):
        async with sem:
            t = time.perf_counter()
            for attempt in range(4):
                try:
                    r = await c.request(method, api + path, json=body, headers=headers or {})
                    break
                except httpx.HTTPError:
                    if attempt == 3:
                        codes[kind][0] = codes[kind].get(0, 0) + 1
                        return None
                    await asyncio.sleep(0.2 * (attempt + 1))
            if kind in lat:
                lat[kind].append((time.perf_counter() - t) * 1000)
            codes[kind][r.status_code] = codes[kind].get(r.status_code, 0) + 1
            return r

    async with httpx.AsyncClient(timeout=120, limits=lim) as c:
        def ip(i):                                       # each customer is a different phone (nginx sets x-real-ip)
            return {"x-real-ip": f"10.{(i >> 16) & 255}.{(i >> 8) & 255}.{i & 255}"}

        async def person(i):
            email, pw = f"lt{tag}{i}@example.com", f"pass-{tag}-{i}"
            await call(c, "signup", "POST", "/signup", {"email": email, "password": pw, "name": f"Load {i}"}, ip(i))
            r = await call(c, "login", "POST", "/login", {"email": email, "password": pw}, ip(i))
            return (r.json().get("token") if r is not None and r.status_code == 200 else "")
        t0 = time.perf_counter()
        tokens = await asyncio.gather(*(person(i) for i in range(customers)))
        t_signup = time.perf_counter() - t0
        start = asyncio.Event()

        async def order(i, tok):
            await start.wait()
            cid = f"lt{tag}{i:06d}"
            body = {"name": f"Load {i}", "phone": f"9{i:09d}"[-10:], "cid": cid, "cart": [{"id": product, "qty": 1}]}
            h = {"Authorization": "Bearer " + tok, **ip(i)}
            jobs = [call(c, "order", "POST", "/c/orders", body, h)]
            if retry_every and i % retry_every == 0:
                jobs.append(call(c, "order", "POST", "/c/orders", body, h))      # the flaky phone sends it twice
            return await asyncio.gather(*jobs)
        tasks = [asyncio.create_task(order(i, t)) for i, t in enumerate(tokens) if t]
        await asyncio.sleep(0.05)
        t1 = time.perf_counter()
        start.set()                                      # everyone presses Order at the same moment
        results = await asyncio.gather(*tasks)
        t_orders = time.perf_counter() - t1
    ok_ids: set[str] = set()
    dup_same = 0
    for rs in results:
        ids = [r.json().get("id") for r in rs if r is not None and r.status_code == 200]
        ok_ids.update(i for i in ids if i)
        if len(ids) == 2 and ids[0] == ids[1]:
            dup_same += 1

    def pct(xs, p):
        return round(sorted(xs)[min(len(xs) - 1, int(len(xs) * p))], 1) if xs else 0
    return {"customers": customers, "logged_in": sum(1 for t in tokens if t), "orders_ok": len(ok_ids),
            "retries_same_row": dup_same, "codes": {k: dict(sorted(v.items())) for k, v in codes.items()},
            "signup_s": round(t_signup, 1), "orders_s": round(t_orders, 1),
            "order_ms": {"p50": pct(lat["order"], .5), "p95": pct(lat["order"], .95), "p99": pct(lat["order"], .99),
                         "mean": round(statistics.mean(lat["order"]), 1) if lat["order"] else 0},
            "order_ids": sorted(ok_ids)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="App load test (a THROWAWAY test app only)")
    ap.add_argument("--base", required=True)
    ap.add_argument("--key", required=True, help="the app_key")
    ap.add_argument("--product", required=True, help="product id with limited stock")
    ap.add_argument("--customers", type=int, default=1000)
    ap.add_argument("--concurrency", type=int, default=250)
    a = ap.parse_args(argv)
    out = asyncio.run(run(a.base, a.key, a.product, a.customers, a.concurrency))
    out.pop("order_ids", None)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
