"""Computer Operator network self-test (run on the VPS, no AI):

    cd ~/apps/santosh-core && .venv/bin/python -m app.operator.check [https://site1 https://site2 ...]

For each site it prints, step by step, where opening it breaks: DNS -> the safety filter (NetGuard) -> TCP connect from
this server -> the real Chromium page through the filter (title, or Chrome's error code). Tells "the site / network
does not answer this server" apart from "Hoola's filter refused it"."""
from __future__ import annotations

import asyncio
import sys
import time
from urllib.parse import urlsplit

SITES = ["https://example.com", "https://www.google.com", "https://www.india.gov.in/", "https://www.incometax.gov.in/"]


async def _one(net, ctx, url: str) -> None:
    u = urlsplit(url if "://" in url else "https://" + url)
    host, port = u.hostname or "", u.port or (443 if u.scheme == "https" else 80)
    print(f"\n== {url}")
    try:
        ips = await net.resolve_all(host, port)
        print(f"OK   DNS + filter      -> {', '.join(ips[:4])}")
    except PermissionError as e:
        print(f"FAIL filter refused   -> {e}")
        return
    except Exception as e:
        print(f"FAIL DNS              -> {e}")
        return
    t0 = time.time()
    try:
        r, w = await net.open(host, port)
        w.close()
        print(f"OK   TCP connect       -> {int((time.time() - t0) * 1000)} ms")
    except Exception as e:
        print(f"FAIL TCP connect      -> {e}")
        return
    page = await ctx.new_page()
    t0 = time.time()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        title = await page.title()
        print(f"OK   Chromium page     -> HTTP {resp.status if resp else '?'} {title!r} ({time.time() - t0:.1f} s)")
        text = (await page.inner_text("body"))[:300].lower() if await page.query_selector("body") else ""
        if any(k in f"{title} {text}".lower() for k in ("access denied", "you have been blocked", "attention required",
                                                       "forbidden", "request blocked", "verify you are human")):
            print("     NOTE: the SITE itself refuses servers / bots (not Hoola's filter)")
    except Exception as e:
        print(f"FAIL Chromium page     -> {str(e).splitlines()[0][:200]}")
    finally:
        await page.close()
    if net.blocked:
        print(f"     filter refused on this page: {net.blocked[-5:]}")
        net.blocked.clear()
    if net.failed:
        print(f"     not reached from this server: {net.failed[-5:]}")
        net.failed.clear()
    print(f"     proxy: {net.stats}")


async def main(urls: list[str]) -> int:
    from playwright.async_api import async_playwright
    from .browser import STABLE_ARGS, _upstream_env
    from .netguard import NetGuard, _doh, _upstream
    _upstream_env()
    net = NetGuard()
    await net.start()
    print(f"NetGuard filter on 127.0.0.1:{net.port}")
    up = _upstream()
    print(f"Upstream (her own network): {up[0]}:{up[1]}" if up else "Upstream: none (traffic leaves from this server's IP)")
    t0 = time.time()
    doh = await asyncio.to_thread(_doh, "www.india.gov.in")
    print(("OK   DNS-over-HTTPS fallback -> " + ", ".join(doh[:2]) + f" ({int((time.time() - t0) * 1000)} ms)") if doh
          else "WARN DNS-over-HTTPS fallback not reachable (only the server's own DNS will be used)")
    from ..config import get_settings
    from .display import launch_options
    st = get_settings()
    args, what = launch_options(bool(st.operator_headless), st.operator_browser, st.operator_chromium or "")
    args["args"] = net.chrome_args() + ["--lang=en-IN"] + STABLE_ARGS
    print(f"Browser: {what}")
    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(**args)
        except Exception as e:
            print(f"FAIL Chromium start -> {str(e).splitlines()[0][:300]}\n(run: bash ~/santosh_app/server/deploy/setup_operator.sh)")
            return 1
        ctx = await browser.new_context(locale="en-IN")
        pg = await ctx.new_page()
        ua = await pg.evaluate("navigator.userAgent")
        await pg.close()
        print(f"Sites see it as: {ua}" + ("   <- 'HeadlessChrome': many sites refuse this" if "Headless" in ua else ""))
        for u in urls:
            await _one(net, ctx, u)
        await browser.close()
    await net.stop()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main([a for a in sys.argv[1:] if a.strip()] or SITES)))
