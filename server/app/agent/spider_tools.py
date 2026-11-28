"""v0.999.59 HOOLA SPIDER - the one `spider` tool over app/spider.py (Scrapy's way of crawling, inside Hoola).

Actions: save (a named spider recipe) / check (one page, nothing saved - Scrapy's `check`) / run (in the
background) / status / stop / items / export (CSV / Excel / JSON / JSON lines file card + a dataset) /
list / show / delete.
"""
from __future__ import annotations

import asyncio
from typing import Any

from .. import spider as SP
from .tools import Ctx, ToolError


def _fmt(run: dict[str, Any]) -> dict[str, Any]:
    st = run.get("stats") or {}
    cp = run.get("checkpoint") or {}
    return {"run_id": run["id"], "spider": run["spider"], "status": run["status"],
            "pages_read": st.get("requests", 0), "items": st.get("items", 0), "dropped": st.get("dropped", 0),
            "duplicates": st.get("duplicates", 0), "retries": st.get("retries", 0),
            "skipped_by_robots": st.get("robots_skipped", 0), "offsite_links": st.get("offsite", 0),
            "blocked": st.get("blocked", 0), "errors": st.get("errors", 0), "statuses": st.get("responses", {}),
            "rendered_in_browser": st.get("rendered", 0), "sitemap_pages_found": cp.get("sitemap_found"),
            "queue_left": len(cp.get("queue") or []), "close_reason": run.get("close_reason") or "",
            "last_block": cp.get("last_block") or "", "error": run.get("error") or ""}


async def spider(ctx: Ctx, action="list", name="", spec=None, run_id="", url="", offset=0, limit=10,
                 format="csv", **_: Any):
    action = str(action or "list").lower()
    t = ctx.tenant_id
    try:
        if action == "save":
            if not isinstance(spec, dict):
                raise ToolError("Give spec = {name, start_urls, item: {container, fields}, follow, next_page, ...}.")
            if name:
                spec = {**spec, "name": name}
            clean = await asyncio.to_thread(SP.save_spider, t, spec)
            return {"saved": clean["name"], "spider": clean,
                    "note": "Saved. Try it on one page with action=check before a full run."}
        if action == "check":
            sp = SP.validate(spec) if isinstance(spec, dict) else await asyncio.to_thread(SP.get_spider, t, name)
            if sp is None:
                raise ToolError(f"No spider called '{name}'.")
            return await _check(ctx, sp, url or sp["start_urls"][0])
        if action == "run":
            r = await asyncio.to_thread(SP.start_run, t, name, ctx.conversation_id)
            return {**_fmt(r), "new": r["_created"],
                    "note": ("Started in the background - say it STARTED, not finished. The chat is told when it "
                             "ends." if r["_created"] else "This spider is already running; this is that run.")}
        if action in ("status", "stop"):
            r = await asyncio.to_thread(SP.get_run, t, run_id)
            if r is None:
                raise ToolError("No spider run yet.")
            if action == "stop":
                ok = await asyncio.to_thread(SP.stop_run, t, r["id"])
                r = await asyncio.to_thread(SP.get_run, t, r["id"])
                return {**_fmt(r), "stopped": ok, "note": "Items already found are kept."}
            return _fmt(r)
        if action == "items":
            r = await asyncio.to_thread(SP.get_run, t, run_id)
            if r is None:
                raise ToolError("No spider run yet.")
            rows, total = await asyncio.to_thread(SP.items, t, r["id"], int(offset or 0), min(50, int(limit or 10)))
            return {"run_id": r["id"], "status": r["status"], "total": total, "offset": int(offset or 0), "items": rows}
        if action == "export":
            r = await asyncio.to_thread(SP.get_run, t, run_id)
            if r is None:
                raise ToolError("No spider run yet.")
            rows, total = await asyncio.to_thread(SP.items, t, r["id"], 0, SP.MAX_ITEMS)
            if not rows:
                raise ToolError("This run has no items yet.")
            data, ext = await asyncio.to_thread(SP.export_bytes, rows, str(format or "csv"))
            from .. import datasets as D
            from .make_tools import _deliver, _safe
            ds = await asyncio.to_thread(D.save, t, rows, f"spider {r['spider']}", f"spider:{r['id']}")
            view = await asyncio.to_thread(_deliver, ctx, _safe(f"{r['spider']}-{r['id'][-6:]}", ext), data, "spider")
            return view | {"items": total, "dataset": ds["id"], "partial": r["status"] in ("queued", "running"),
                           "note": "The file card is in the chat."}
        if action == "show":
            sp = await asyncio.to_thread(SP.get_spider, t, name)
            if sp is None:
                raise ToolError(f"No spider called '{name}'.")
            return {"spider": sp}
        if action == "delete":
            return {"deleted": await asyncio.to_thread(SP.delete_spider, t, name)}
        return {"spiders": await asyncio.to_thread(SP.list_spiders, t)}
    except SP.SpiderError as e:
        raise ToolError(str(e))


async def _check(ctx: Ctx, sp: dict[str, Any], url: str) -> dict[str, Any]:
    """Scrapy's contracts / `scrapy parse`: fetch one page, show the items and links. Nothing is saved."""
    from . import scrape_tools as st
    url = await asyncio.to_thread(st._guard_url, url)
    if not await st._robots_ok(url):
        raise ToolError("robots.txt of this site does not allow reading that page.")
    from ..config import get_settings
    s = get_settings()
    browser_on = bool(getattr(s, "spider_browser_enabled", False)) and bool(getattr(s, "scrape_stealth_enabled", False))
    rendered = False
    if sp.get("render") == "always" and browser_on:
        page, rendered = await SP._render(url), True
    else:
        page = await asyncio.to_thread(st._fetch, url, ctx.tenant_id)
    status = int(getattr(page, "status", 0) or 0)
    blk = await asyncio.to_thread(st._blocked, page)
    if (not rendered and sp.get("render") == "auto" and browser_on
            and (blk or SP._looks_empty(page, blk or ""))):
        page, rendered = await SP._render(url), True
        status = int(getattr(page, "status", 0) or 0)
        blk = await asyncio.to_thread(st._blocked, page)
    browser_note = ""
    if sp.get("render") in ("auto", "always") and not browser_on:
        browser_note = (" The spider browser is off on this server, so JavaScript pages are read as plain HTML "
                        "(owner: SPIDER_BROWSER_ENABLED=true + SCRAPE_STEALTH_ENABLED=true).")
    if blk or status >= 400:
        return {"url": url, "status": status, "ok": False, "blocked": blk or "",
                "note": "The page did not answer normally, so nothing could be checked."}
    final = getattr(page, "url", "") or url
    rows = await asyncio.to_thread(SP.extract, page, sp, final)
    kept, dropped = SP.pipeline(rows, sp, final)
    nxt = await asyncio.to_thread(SP.links, page, sp, final, 0, sp["parse_start"])
    follow = [n["url"] for n in nxt if not SP.offsite(n["url"], sp["allowed_domains"])]
    empty = [f for f in sp["item"]["fields"] if all(k[2].get(f) in (None, "", []) for k in kept)] if kept else []
    sitemap = None
    if sp.get("sitemap"):
        found, notes = await SP._sitemap_urls(sp | {"max_pages": min(sp["max_pages"], 50)})
        q = SP._sitemap_queue(sp, found)
        sitemap = {"found": len(found), "would_read": len(q), "sample": [x["url"] for x in q[:8]], "notes": notes}
    return {"url": final, "status": status, "ok": bool(kept), "items_found": len(kept), "dropped": dropped,
            "rendered_in_browser": rendered, "sitemap": sitemap,
            "sample": [k[2] for k in kept[:5]], "fields_always_empty": empty,
            "links_to_follow": len(follow), "link_sample": follow[:8],
            "note": ("Check only - nothing saved." + (" Some fields came back empty on every item: fix their "
                                                       "selectors." if empty else "") + browser_note)}


SPIDER_TOOLS = [
    {"name": "spider", "description": (
        "Hoola Spider - Scrapy's way of crawling (v0.999.59, v0.999.60). A SPIDER is a saved recipe: where to start "
        "(start_urls), which links to follow (follow rules with allow / deny regex + optional css area, "
        "next_page for pagination, depth_limit), what to pull out of each page (item.container css for one "
        "box per item + item.fields {name: selector}) and how to clean it (pipelines.required, pipelines.dedup "
        "= a field name or '_url'). Selectors: 'h2::text', 'a::attr(href)', 'a@href', 'xpath://h1', with steps "
        "'|number' '|int' '|url' '|all' '|lower' '|join'. Order: save -> check (one page, nothing saved; fix "
        "empty fields) -> run (background, polite: robots.txt always obeyed, per-site delay, retries, page / "
        "item / time limits) -> status / items -> export (csv | xlsx | json | jsonl file card + dataset). Faster: concurrency (1-8 pages at once, at most per_host 1-4 for one site, each site still waits its "
        "polite delay). SitemapSpider: sitemap=true (or sitemap_urls) reads every page the site lists in its own "
        "sitemap instead of following links; sitemap_rules [{allow, parse}] pick which. JavaScript pages: render "
        "'auto' (the browser only when a page comes back empty or blocked) or 'always' - needs the owner's "
        "spider browser switch; one browser page at a time. Use "
        "for MANY items across MANY pages of a public site (a whole catalogue with prices, all listings of a "
        "directory, every notice). One page = scrape_extract; plain page text over a site = crawl_start. Never "
        "for pages behind a login, and a spec with cookies / headers / forms is refused."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["save", "check", "run", "status", "stop", "items", "export", "list",
                                                "show", "delete"]},
         "name": {"type": "string", "description": "The spider's name (save / check / run / show / delete)"},
         "spec": {"type": "object", "description": (
             "For save (or check without saving): {start_urls: [..], allowed_domains?: [..], item: {container?: "
             "'article.product', fields: {title: 'h3 a::attr(title)', price: '.price|number', link: 'a::attr(href)|url'}}, "
             "follow?: [{allow: '/catalogue/', deny?: '', css?: '', parse?: true}], next_page?: 'li.next a', "
             "depth_limit?: 2, max_pages?: 50 (cap 500), max_items?: 1000 (cap 10000), max_minutes?: 30, "
             "pipelines?: {required: ['title'], dedup: 'link'}, concurrency?: 4, per_host?: 2, sitemap?: false, "
             "sitemap_urls?: [..], sitemap_rules?: [{allow: '/product/', parse: true}], render?: 'never'|'auto'|'always'}")},
         "run_id": {"type": "string", "description": "status / stop / items / export; empty = latest run"},
         "url": {"type": "string", "description": "check: the page to test (default the first start url)"},
         "offset": {"type": "integer"}, "limit": {"type": "integer", "description": "items: up to 50"},
         "format": {"type": "string", "enum": ["csv", "xlsx", "json", "jsonl"], "description": "export format"}},
         "required": ["action"]}},
]

SPIDER_LABELS = {"spider": "Working with a web spider"}
SPIDER_HANDLERS = {"spider": spider}
