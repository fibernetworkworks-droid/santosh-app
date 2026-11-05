"""v0.474.0 SCRAPLING — Hoola can scrape any website smoothly (owner: "NOW DEPLOY THIS SCRAPER FOR HOOLA ---
THUS HOOLA CAN SCRAP ANY WEBSITE SMOOTHLY").

Built on the Scrapling library (BSD-3-Clause, v0.5 PyPI: github.com/D4Vinci/Scrapling) — 13.8k stars,
lxml-based parser (~100x faster than BeautifulSoup), curl_cffi fetcher with TLS-fingerprint impersonation,
and the killer feature: ADAPTIVE scraping — remember an element once (Simhash text similarity + DOM-tree
relative positioning) and Scrapling re-finds it by itself after the site redesigns.

What this adds that open_website / browse_web do NOT do:
- STRUCTURED extraction: CSS/XPath selectors -> JSON rows (product lists, tables, directories)
- BULK: the same selector across many pages in one call (scrape_many), or a polite same-host crawl (scrape_site)
- ADAPTIVE memory per tenant: elements are remembered in data/scraping/<tenant>/elements.db, so a saved
  extraction keeps working when the site's HTML changes (css(adaptive=True, auto_save=True))
- STEALTH reads for sites that block plain fetchers: real browser engine (Scrapling StealthyFetcher),
  OFF by default behind the `scrape_stealth_enabled` setting (RAM guard after MEM-CURE v0.208.1: no
  browser is ever launched by these tools unless the owner turns that setting on; the default engine is
  pure HTTP via curl_cffi, no browser, no heavy RAM).

Safety rails, all server-side before any fetch:
- SSRF guard: only http/https; the host must resolve to a PUBLIC ip (loopback / RFC1918 / link-local /
  169.254.169.254 metadata / ULA never fetched); known TOCTOU limit: the fetcher re-resolves DNS (documented).
- robots.txt gate (setting scrape_respect_robots, default True): disallowed paths are refused honestly.
- Caps everywhere: output chars (24k default / 60k hard), 15 urls in scrape_many, 25 pages in scrape_site,
  60 s per fetch. Everything runs in asyncio.to_thread (house pattern) and outputs pass operator.browser
  mask_ids like every other tool.
"""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from .tools import Ctx, ToolError

_MAX_TEXT = 24_000          # default chat-side cap for page content
_HARD_TEXT = 60_000         # never return more than this, even if asked
_MAX_URLS = 15              # scrape_many cap
_MAX_SITE_PAGES = 25        # scrape_site cap
_MAX_TIMEOUT = 60           # per-fetch cap, seconds
_ROBOTS_TTL = 3600          # robots.txt cache per host, seconds
_STEALTH_SEM = threading.BoundedSemaphore(1)   # one stealth browser at a time (MEM-CURE RAM discipline)
# v0.481 FIRECRAWL CORE - the engine-waterfall ideas, house-sized:
_MAX_MAP_FETCHES = 8        # scrape_map fetches at most this many pages to harvest links
_MAX_MAP_URLS = 200         # scrape_map cap on returned urls
_CACHE_ROWS = 300           # per-tenant page cache LRU cap (rows)
_BRAIN_TEXT = 14_000        # page text handed to the brain for schema extraction
_BRAIN_MAX_TOKENS = 2_000   # hard cap on one schema-extraction brain call
_STEALTHY_TITLES = ("just a moment", "attention required", "access denied", "unusual traffic",
                    "are you a robot", "verify you are human", "bot verification")
_STEALTHY_SCRIPTS = ("challenge-platform", "cf-browser-verification", "cf_chl_opt",
                     "enable javascript and cookies to continue")

_ROBOTS_CACHE: dict[str, tuple[float, Any]] = {}   # host -> (expiry, ProtegoRobot)


# --------------------------------------------------------------------------- guards

def _guard_url(url: str) -> str:
    """SSRF guard: normalise, then only public http(s) hosts pass. Raises ToolError otherwise."""
    url = str(url or "").strip()
    if not url:
        raise ToolError("Give the website link (url)")
    if "://" not in url:
        url = "https://" + url
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        raise ToolError("Only http(s) links can be scraped")
    host = u.hostname
    if not host:
        raise ToolError("That link has no website address in it")
    try:
        literal = ipaddress.ip_address(host)
        ips = [literal]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            raise ToolError(f"Yeh address ({host}) resolve nahi hua — link check kar lein ya site down ho sakti hai")
        ips = [ipaddress.ip_address(i[4][0]) for i in infos] or []
        if not ips:
            raise ToolError(f"Yeh address ({host}) resolve nahi hua")
    for ip in ips:
        if not ip.is_global:
            raise ToolError(f"Yeh address ({host}) andar ke network ka hai (private/loopback) — scraping sirf public websites par chalti hai")
    return u.geturl()


def _tenant_dir(tenant_id: str) -> str:
    """data/scraping/<safe-tenant>/ - everything the scrape lane remembers lives here."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", str(tenant_id or "x"))[:48] or "x"
    p = Path("data") / "scraping" / safe
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def _storage_path(tenant_id: str) -> str:
    """Per-tenant adaptive-element memory (SQLite): data/scraping/<safe-tenant>/elements.db."""
    return str(Path(_tenant_dir(tenant_id)) / "elements.db")


def _cap(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[...content truncated, {len(text) - limit} chars more — narrow it with a css selector]"


def _masked(v: Any) -> Any:
    """ID numbers in what comes back are masked before the chat model reads it (same rule as web_tools)."""
    from ..operator.browser import mask_ids
    if isinstance(v, str):
        return mask_ids(v)
    if isinstance(v, dict):
        return {k: _masked(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_masked(x) for x in v]
    return v


# --------------------------------------------------------------------------- robots

def _robots_allowed(url: str, timeout: int = 8) -> bool:
    """robots.txt of the site decides (setting scrape_respect_robots). Unknown / unreachable robots = allow.

    NOTE on protego's signature: it is can_fetch(url, user_agent) — the classic (user_agent, url) order
    of robotparser would silently always-return-True, so the argument order here is deliberate.
    """
    from ..config import get_settings
    if not get_settings().scrape_respect_robots:
        return True
    u = urlparse(url)
    host = u.hostname or ""
    now_ = time.time()
    cached = _ROBOTS_CACHE.get(host)
    rp = None
    if cached and cached[0] > now_:
        rp = cached[1]
    else:
        from protego import Protego
        try:
            from scrapling.fetchers import Fetcher
            r = Fetcher.get(f"{u.scheme}://{host}/robots.txt", timeout=timeout, follow_redirects=True)
            rp = Protego.parse(r.get_all_text(separator="\n")[:64_000])
        except Exception:
            rp = None                     # no robots / fetch failed -> fail open
        _ROBOTS_CACHE[host] = (now_ + _ROBOTS_TTL, rp)
    if rp is None:
        return True
    return bool(rp.can_fetch(url, "*"))


async def _robots_ok(url: str) -> bool:
    """robots check off the event loop (it may fetch robots.txt over the network)."""
    return await asyncio.to_thread(_robots_allowed, url)


# --------------------------------------------------------------------------- fetch core

def _fetch(url: str, tenant_id: str, timeout: int = 25, adaptive: bool = False):
    """One public page through Scrapling's curl_cffi engine (TLS-impersonated chrome, no browser)."""
    from scrapling.fetchers import Fetcher
    timeout = max(5, min(int(timeout or 25), _MAX_TIMEOUT))
    sel_cfg: dict[str, Any] = {}
    if adaptive:
        sel_cfg = {"adaptive": True, "storage_args": {"storage_file": _storage_path(tenant_id)}}
    return Fetcher.get(url, timeout=timeout, follow_redirects=True, selector_config=sel_cfg)


def _split_xpath(selector: str) -> tuple[str, str]:
    """"xpath://div[@id]" -> ("xpath", ...) ; plain css -> ("css", ...)."""
    s = str(selector or "").strip()
    if s.lower().startswith("xpath:"):
        return "xpath", s[6:].strip()
    return "css", s


def _pick(page: Any, selector: str, adaptive: bool = False, identifier: str = "", auto_save: bool = False):
    kind, sel = _split_xpath(selector)
    if not sel:
        raise ToolError("Give a css selector (e.g. 'article.product_pod') or 'xpath://ul[@id=\"list\"]'")
    host = (urlparse(page.url or "").hostname or "").replace("www.", "")
    ident = f"{host}:{identifier}" if identifier else host
    if kind == "xpath":
        return page.xpath(sel)
    return page.css(sel, adaptive=adaptive, auto_save=auto_save, identifier=ident or host)


def _field_value(el: Any, spec: str) -> Any:
    """'h3 a@title' -> title attribute of the h3 a inside el; 'p.price' -> its deep text; '@href' -> el's own attr."""
    spec = str(spec or "").strip()
    if not spec or spec == "@":
        return None
    if spec.startswith("@"):
        return el.attrib.get(spec[1:])
    sel, attr = spec, None
    if "@" in spec:
        sel, attr = spec.rsplit("@", 1)
    try:
        found = el.css(sel) if sel else [el]
    except Exception:
        return None
    if not found:
        return None
    node = found[0]
    if attr:
        return node.attrib.get(attr)
    try:
        deep = node.get_all_text(separator=" ").strip()
    except Exception:
        deep = ""
    return (deep or (node.text or "")).strip()[:2000]


# --------------------------------------------------------------------------- block detection (v0.481)

def _blocked(page: Any) -> str | None:
    """Firecrawl-waterfall idea, tightened: does this answer look like a bot-block, not a page?
    Only strong signals escalate: a block status, a challenge title, or a SMALL body carrying a
    challenge fingerprint (the size gate keeps a normal article that merely mentions captcha
    from ever escalating). Returns a short reason, or None when the page looks real."""
    try:
        status = int(getattr(page, "status", 0) or 0)
    except Exception:
        status = 0
    if status in (401, 403, 429):
        return f"HTTP {status}"
    try:
        t = page.css("title")
        title = (t[0].text or "").strip().lower()[:200] if t else ""
    except Exception:
        title = ""
    for m in _STEALTHY_TITLES:
        if m in title:
            return f"challenge title ('{m}')"
    try:
        text = page.get_all_text(separator=" ") or ""
    except Exception:
        text = ""
    if 0 < len(text) < 2500:
        low = text.lower()
        for m in _STEALTHY_SCRIPTS:
            if m in low:
                return f"challenge script ('{m}')"
    return None


# --------------------------------------------------------------------------- page cache (v0.481)

def _cache_get(tenant_id: str, url: str, max_age) -> dict[str, Any] | None:
    """Cached page inside max_age seconds (per-tenant SQLite). max_age None/<=0 -> never read."""
    from ..config import get_settings
    if not get_settings().scrape_cache_enabled or max_age is None or int(max_age or 0) <= 0:
        return None
    import sqlite3
    try:
        con = sqlite3.connect(str(Path(_tenant_dir(tenant_id)) / "cache.db"))
        try:
            row = con.execute("SELECT fetched_at, status, title, markdown, text FROM page_cache WHERE url = ?",
                              (url,)).fetchone()
        finally:
            con.close()
    except Exception:
        return None
    if not row:
        return None
    age = time.time() - float(row[0] or 0)
    if age > int(max_age):
        return None
    return {"age": int(age), "status": int(row[1] or 0), "title": row[2] or "",
            "markdown": row[3] or "", "text": row[4] or ""}


def _cache_put(tenant_id: str, url: str, status: int, title: str, markdown: str, text: str) -> None:
    from ..config import get_settings
    if not get_settings().scrape_cache_enabled or int(status or 0) >= 400 or not url:
        return
    import sqlite3
    try:
        con = sqlite3.connect(str(Path(_tenant_dir(tenant_id)) / "cache.db"))
        try:
            con.execute("CREATE TABLE IF NOT EXISTS page_cache (url TEXT PRIMARY KEY, fetched_at REAL, "
                        "status INTEGER, title TEXT, markdown TEXT, text TEXT)")
            con.execute("INSERT INTO page_cache (url, fetched_at, status, title, markdown, text) VALUES (?,?,?,?,?,?) "
                        "ON CONFLICT(url) DO UPDATE SET fetched_at=excluded.fetched_at, status=excluded.status, "
                        "title=excluded.title, markdown=excluded.markdown, text=excluded.text",
                        (url, time.time(), int(status), (title or "")[:500],
                         (markdown or "")[:_HARD_TEXT], (text or "")[:_HARD_TEXT]))
            con.execute("DELETE FROM page_cache WHERE url IN (SELECT url FROM page_cache "
                        "ORDER BY fetched_at DESC LIMIT -1 OFFSET ?)", (_CACHE_ROWS,))
            con.commit()
        finally:
            con.close()
    except Exception:
        pass                                    # the cache never breaks a scrape


def _cache_put_page(tenant_id: str, page: Any) -> None:
    """Write-through: remember the page-level markdown + text (2xx only, best effort)."""
    try:
        status = int(getattr(page, "status", 0) or 0)
        if status >= 400:
            return
        try:
            md = page.markdown()
        except Exception:
            md = ""
        try:
            txt = page.get_all_text(separator="\n")
        except Exception:
            txt = ""
        try:
            t = page.css("title")
            title = (t[0].text.strip() if t else "")
        except Exception:
            title = ""
        _cache_put(tenant_id, getattr(page, "url", "") or "", status, title, md or "", txt or "")
    except Exception:
        pass


# --------------------------------------------------------------------------- stealth core (v0.481)

def _stealth_fetch(url: str, timeout: int = 90, wait_selector: str = "", solve_cloudflare: bool = False):
    """One StealthyFetcher.fetch with the house discipline - the SEMAPHORE IS THE CALLER'S JOB."""
    from scrapling.fetchers import StealthyFetcher
    kw: dict[str, Any] = {"headless": True,
                          # StealthyFetcher timeout is MILLISECONDS (default 30_000) - seconds in, ms out
                          "timeout": max(30_000, min(int(timeout or 90), 180) * 1000),
                          "solve_cloudflare": bool(solve_cloudflare)}
    if wait_selector:
        kw["wait_selector"] = str(wait_selector)[:300]
    return StealthyFetcher.fetch(url, **kw)


# --------------------------------------------------------------------------- brain extraction (v0.481)

def _json_loose(text: str):
    """The brain's answer -> JSON: direct, then a fenced block ANYWHERE in the answer, then the first
    balanced {..}/[..] run."""
    import json as _json
    if not text:
        return None
    s = text.strip()
    try:
        return _json.loads(s)
    except Exception:
        pass
    m = re.search(r"```[a-zA-Z0-9_-]*\s*(.*?)\s*```", s, re.S)
    if m:
        try:
            return _json.loads(m.group(1).strip())
        except Exception:
            pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = s.find(open_ch)
        if start < 0:
            continue
        depth = 0
        for i in range(start, len(s)):
            c = s[i]
            if c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return _json.loads(s[start:i + 1])
                    except Exception:
                        break
    return None


async def _extract_brain(system: str, user: str) -> tuple[str, str]:
    """The pakka pattern (coder/observer shape): cheap brain first, Claude fallback. (text, label)."""
    from ..agent import llm
    msgs = [{"role": "user", "content": [{"type": "text", "text": user}]}]
    cheap = llm.cheap_brain()
    if cheap:
        try:
            blocks, _, _ = await llm.openai_create(cheap, system, [], msgs, _BRAIN_MAX_TOKENS)
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text"), f"cheap:{cheap}"
        except Exception:
            pass
    from ..config import get_settings
    if get_settings().anthropic_api_key:
        from .santosh import get_client
        resp = await get_client().messages.create(model=get_settings().anthropic_model,
                                                  max_tokens=_BRAIN_MAX_TOKENS, system=system,
                                                  messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text"), "claude"
    raise ToolError("Is VPS par extraction brain configured nahi hai — schema extraction ke liye ek brain chahiye")


# --------------------------------------------------------------------------- handlers

async def scrape_page(ctx: Ctx, url, format="markdown", css=None, include_links=False, max_chars=24000, timeout=25, max_age=None, **_):
    """Fast public-page read (no browser). Returns title + clean content; links optional.
    v0.481: pass max_age (seconds) to serve the page from the tenant cache when fresh; css and
    include_links always read the live page (they need the DOM). Successful reads write through."""
    url = await asyncio.to_thread(_guard_url, url)
    if not await _robots_ok(url):
        raise ToolError("Is site ke robots.txt ne is page ke liye bots ko mana kiya hai (respect_robots on) — user se poochh kar scrape_stealth ya browse_web try kar sakte hain")
    limit = max(500, min(int(max_chars or _MAX_TEXT), _HARD_TEXT))
    fmt = str(format or "markdown").lower()
    if not css and not include_links:      # v0.481 cache read BEFORE the fetch — zero outbound when fresh
        hit = await asyncio.to_thread(_cache_get, ctx.tenant_id, url, max_age)
        if hit:
            content = hit["markdown"] if fmt != "text" else hit["text"]
            if not content:                 # one of the two stored forms may be empty
                content = hit["text"] if fmt != "text" else hit["markdown"]
            if content:
                return _masked({"status": hit["status"], "url": url, "title": hit["title"],
                                "engine": "cache", "cached": True, "age_s": hit["age"],
                                "content": _cap(content, limit)})
    try:
        page = await asyncio.to_thread(_fetch, url, ctx.tenant_id, timeout)
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Fetch failed: {str(e)[:300]}")
    if page.status >= 400:
        raise ToolError(f"Site ne {page.status} bheja ({page.reason}) — page nahi mila")
    if css:
        hits = _pick(page, css)
        if not hits:
            return {"status": page.status, "url": page.url, "count": 0,
                    "content": "", "note": "css selector se kuch nahi mila — selector check karein"}
        parts = [h.html_content if fmt == "html" else (h.markdown() if fmt == "markdown" and hasattr(h, "markdown") else h.get_all_text(separator="\n")) for h in hits[:20]]
        content = ("\n\n---\n\n").join(p for p in parts if p)
    elif fmt == "html":
        content = page.html_content
    elif fmt == "text":
        content = page.get_all_text(separator="\n")
    else:
        try:
            content = page.markdown()
        except Exception:                 # markdownify missing -> text fallback
            content = page.get_all_text(separator="\n")
    out: dict[str, Any] = {"status": page.status, "url": page.url,
                           "title": (page.css("title")[0].text.strip() if page.css("title") else ""),
                           "content": _cap(content or "", limit)}
    await asyncio.to_thread(_cache_put_page, ctx.tenant_id, page)   # v0.481 write-through
    if include_links:
        links = []
        for a in page.css("a[href]")[:80]:
            href = a.attrib.get("href") or ""
            if href.startswith(("javascript:", "mailto:", "tel:")):
                continue
            links.append({"text": (a.text or "").strip()[:120], "href": urljoin(page.url, href)[:500]})
            if len(links) >= 60:
                break
        out["links"] = links
    return _masked(out)


async def scrape_extract(ctx: Ctx, url, selector, fields=None, attr=None, adaptive=True, similar=False, identifier="items", limit=100, timeout=25, **_):
    """Structured rows out of one page: CSS/XPath selector (+ optional per-field map) -> JSON. Adaptive memory."""
    url = await asyncio.to_thread(_guard_url, url)
    if not await _robots_ok(url):
        raise ToolError("Is site ke robots.txt ne is page ke liye bots ko mana kiya hai (respect_robots on)")
    try:
        limit = max(1, min(int(limit or 100), 500))
    except Exception:
        limit = 100
    try:
        page = await asyncio.to_thread(_fetch, url, ctx.tenant_id, timeout, adaptive=bool(adaptive))
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Fetch failed: {str(e)[:300]}")
    if page.status >= 400:
        raise ToolError(f"Site ne {page.status} bheja ({page.reason})")
    hits = await asyncio.to_thread(_pick, page, selector, bool(adaptive), str(identifier or "items"), bool(adaptive))
    if len(hits) == 1 and similar:
        try:
            sibs = hits[0].find_similar()      # siblings only, the matched one is not included
            if sibs:
                hits = [hits[0]] + list(sibs)
        except Exception:
            pass
    rows: list[dict[str, Any]] = []
    fields_map = fields if isinstance(fields, dict) else None
    for el in hits[:limit]:
        if fields_map:
            row = {k: _field_value(el, spec) for k, spec in fields_map.items()}
        elif attr:
            row = {attr: el.attrib.get(str(attr))}
        else:
            row = {"text": (el.text or "").strip()[:2000]}
        rows.append(row)
    return _masked({"status": page.status, "url": page.url, "selector": selector,
                    "count": len(rows), "rows": rows, "adaptive": bool(adaptive),
                    "note": ("Adaptive memory: agle runs par site badle to bhi yeh selector khud doondh lega (per-tenant)." if adaptive and rows else "")})


async def scrape_many(ctx: Ctx, urls, selector, fields=None, attr=None, adaptive=False, identifier="items", limit_per_page=50, timeout=20, **_):
    """Same selector across up to 15 pages (e.g. 15 product pages). Per-page rows + errors, robots respected."""
    if not isinstance(urls, list) or not urls:
        raise ToolError("Give the list of page urls (max 15)")
    urls = [str(u) for u in urls if str(u).strip()][:_MAX_URLS]
    if not urls:
        raise ToolError("Give the list of page urls (max 15)")
    results: list[dict[str, Any]] = []
    try:
        per = max(1, min(int(limit_per_page or 50), 200))
    except Exception:
        per = 50
    seen_hosts: set[str] = set()
    for u in urls:
        try:
            gu = await asyncio.to_thread(_guard_url, u)
            host = urlparse(gu).hostname or ""
            if host not in seen_hosts:
                if not await _robots_ok(gu):
                    results.append({"url": u, "error": "robots.txt in path ko mana karta hai"})
                    seen_hosts.add(host)
                    continue
                seen_hosts.add(host)
            page = await asyncio.to_thread(_fetch, gu, ctx.tenant_id, timeout, adaptive=bool(adaptive))
            if page.status >= 400:
                results.append({"url": u, "error": f"HTTP {page.status}"})
                continue
            hits = await asyncio.to_thread(_pick, page, selector, bool(adaptive), str(identifier or "items"), bool(adaptive))
            rows = []
            for el in hits[:per]:
                if isinstance(fields, dict) and fields:
                    rows.append({k: _field_value(el, spec) for k, spec in fields.items()})
                elif attr:
                    rows.append({str(attr): el.attrib.get(str(attr))})
                else:
                    rows.append({"text": (el.text or "").strip()[:2000]})
            results.append({"url": u, "status": page.status, "count": len(rows), "rows": rows})
        except ToolError as e:
            results.append({"url": u, "error": str(e)[:200]})
        except Exception as e:
            results.append({"url": u, "error": str(e)[:200]})
        await asyncio.sleep(0.25)          # polite
    ok = sum(1 for r in results if r.get("rows") is not None)
    return _masked({"pages": len(results), "pages_ok": ok, "results": results})


async def scrape_site(ctx: Ctx, start_url, max_pages=15, include=None, max_chars_per_page=1200, timeout=20, **_):
    """Polite same-host crawl (BFS, robots + caps): map a site / find where the data lives."""
    start = await asyncio.to_thread(_guard_url, start_url)
    if not await _robots_ok(start):
        raise ToolError("Is site ke robots.txt ne bots ko mana kiya hai (respect_robots on)")
    try:
        want = max(1, min(int(max_pages or 15), _MAX_SITE_PAGES))
    except Exception:
        want = 15
    try:
        per_head = max(300, min(int(max_chars_per_page or 1200), 4000))
    except Exception:
        per_head = 1200
    pat = None
    if include:
        try:
            pat = re.compile(str(include))
        except re.error:
            raise ToolError("include pattern valid regex nahi hai")
    start_host = urlparse(start).hostname or ""
    seen: set[str] = {start}
    queue = [start]
    pages: list[dict[str, Any]] = []
    skipped_robots = 0
    while queue and len(pages) < want:
        u = queue.pop(0)
        try:
            page = await asyncio.to_thread(_fetch, u, ctx.tenant_id, timeout)
        except Exception as e:
            pages.append({"url": u, "error": str(e)[:160]})
            continue
        head = page.get_all_text(separator="\n") if page.status < 400 else ""
        pages.append({"url": page.url or u, "status": page.status,
                      "title": (page.css("title")[0].text.strip() if page.css("title") else ""),
                      "text_head": head[:per_head]})
        for a in page.css("a[href]"):
            href = a.attrib.get("href") or ""
            if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            nxt = urljoin(page.url or u, href).split("#")[0]
            try:
                nu = urlparse(nxt)
            except Exception:
                continue
            if nu.scheme not in ("http", "https") or (nu.hostname or "") != start_host:
                continue
            if pat and not pat.search(nxt):
                continue
            if nu.geturl() in seen:
                continue
            seen.add(nu.geturl())
            if not await _robots_ok(nu.geturl()):   # str, not the ParseResult (live-caught bug)
                skipped_robots += 1
                continue
            queue.append(nu.geturl())
            if len(queue) > 200:
                break
        await asyncio.sleep(0.4)           # politeness
    return _masked({"start": start, "host": start_host, "pages_found": len(pages),
                    "skipped_by_robots": skipped_robots, "pages": pages[:want],
                    "note": "Data jis page par hai uska url uthakar scrape_extract chalayein — rows JSON mein aayengi"})


async def scrape_stealth(ctx: Ctx, url, format="markdown", css=None, wait_selector=None, solve_cloudflare=False, max_chars=24000, timeout=90, **_):
    """Anti-bot / JavaScript pages: Scrapling's stealth browser engine. Needs scrape_stealth_enabled=True + `scrapling install`."""
    from ..config import get_settings
    s = get_settings()
    if not s.scrape_stealth_enabled:
        raise ToolError("Stealth scraping is VPS par band hai (RAM guard). Owner 'scrape_stealth_enabled=true' setting on kare aur ek baar 'scrapling install' chalaye — uske baad Cloudflare/anti-bot sites bhi khulengi. Tab tak open_website/browse_web use karein.")
    url = await asyncio.to_thread(_guard_url, url)
    limit = max(500, min(int(max_chars or _MAX_TEXT), _HARD_TEXT))
    try:
        from scrapling.fetchers import StealthyFetcher
    except Exception as e:
        raise ToolError(f"Stealth engine load nahi hua: {str(e)[:200]}")
    if _STEALTH_SEM.acquire(blocking=False) is False:
        raise ToolError("Ek stealth browser already chal raha hai — ek minute baad try karein")
    try:
        def _run():
            kw: dict[str, Any] = {"headless": True,
                                  # StealthyFetcher timeout is MILLISECONDS (default 30_000) — seconds in, ms out
                                  "timeout": max(30_000, min(int(timeout or 90), 180) * 1000),
                                  "solve_cloudflare": bool(solve_cloudflare)}
            if wait_selector:
                kw["wait_selector"] = str(wait_selector)[:300]
            return StealthyFetcher.fetch(url, **kw)
        page = await asyncio.to_thread(_run)
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Stealth fetch failed: {str(e)[:300]}")
    finally:
        try:
            _STEALTH_SEM.release()
        except Exception:
            pass
    if page.status >= 400:
        raise ToolError(f"Site ne {page.status} bheja ({page.reason})")
    fmt = str(format or "markdown").lower()
    if css:
        hits = _pick(page, css)
        parts = [h.html_content if fmt == "html" else h.get_all_text(separator="\n") for h in hits[:20]]
        content = ("\n\n---\n\n").join(p for p in parts if p)
    elif fmt == "text":
        content = page.get_all_text(separator="\n")
    else:
        try:
            content = page.markdown()
        except Exception:
            content = page.get_all_text(separator="\n")
    return _masked({"status": page.status, "url": page.url, "engine": "scrapling-stealth",
                    "title": (page.css("title")[0].text.strip() if page.css("title") else ""),
                    "content": _cap(content or "", limit)})


async def scrape(ctx: Ctx, url, format="markdown", css=None, include_links=False, max_chars=24000, timeout=25, max_age=None, stealth="auto", **_):
    """THE one door (v0.481, the Firecrawl waterfall idea): fast HTTP first; on a block signature it
    escalates ITSELF to the stealth browser (when enabled). Cache-aware. stealth: auto|never|always."""
    from ..config import get_settings
    s = get_settings()
    url = await asyncio.to_thread(_guard_url, url)
    if not await _robots_ok(url):
        raise ToolError("Is site ke robots.txt ne is page ke liye bots ko mana kiya hai (respect_robots on)")
    limit = max(500, min(int(max_chars or _MAX_TEXT), _HARD_TEXT))
    fmt = str(format or "markdown").lower()
    mode = str(stealth or "auto").lower()
    if mode not in ("auto", "never", "always"):
        mode = "auto"
    if mode == "always" and not s.scrape_stealth_enabled:
        raise ToolError("Stealth scraping is VPS par band hai (RAM guard). Owner 'scrape_stealth_enabled=true' on kare aur ek baar 'scrapling install' chalaye.")
    if mode != "always" and not css and not include_links:
        hit = await asyncio.to_thread(_cache_get, ctx.tenant_id, url,
                                      max_age if max_age is not None else s.scrape_cache_max_age)
        if hit:
            content = hit["markdown"] if fmt != "text" else hit["text"]
            if not content:                 # one of the two stored forms may be empty
                content = hit["text"] if fmt != "text" else hit["markdown"]
            if content:
                return _masked({"status": hit["status"], "url": url, "title": hit["title"], "engine": "cache",
                                "cached": True, "age_s": hit["age"], "escalated": False,
                                "content": _cap(content, limit)})
    page = None
    engine, escalated, block = "http", False, None
    if mode != "always":
        try:
            page = await asyncio.to_thread(_fetch, url, ctx.tenant_id, timeout)
        except ToolError:
            raise
        except Exception as e:
            block = f"fetch failed ({str(e)[:140]})"
        else:
            block = await asyncio.to_thread(_blocked, page)
    escalate = (mode == "always") or (mode == "auto" and bool(block))
    if escalate and s.scrape_stealth_enabled:
        if _STEALTH_SEM.acquire(blocking=False) is False:
            raise ToolError("Ek stealth browser already chal raha hai — ek minute baad try karein")
        try:
            page = await asyncio.to_thread(_stealth_fetch, url, timeout)
            engine, escalated = "stealth", True
            block = await asyncio.to_thread(_blocked, page)
        except Exception as e:
            raise ToolError(f"Stealth fetch failed: {str(e)[:300]}")
        finally:
            try:
                _STEALTH_SEM.release()
            except Exception:
                pass
    elif block and page is None:
        raise ToolError(f"Fetch failed: {block}")
    elif mode == "auto" and block and not s.scrape_stealth_enabled:
        raise ToolError(f"Site ne block kiya ({block}) — stealth is VPS par band hai (RAM guard). Owner "
                        "'scrape_stealth_enabled=true' on kare aur ek baar 'scrapling install' chalaye, phir yeh "
                        "door khud advance mode mein khulega. Tab tak browse_web try karein.")
    if page is None:
        raise ToolError("Fetch failed — site tak pahunch nahi paye")
    if page.status >= 400:
        if escalated:
            raise ToolError(f"Site ne block kiya ({block}) — advance mode ne bhi nahi khola. browse_web try karein.")
        raise ToolError(f"Site ne {page.status} bheja ({getattr(page, 'reason', '')}) — page nahi mila")
    if css:
        hits = _pick(page, css)
        if not hits:
            return {"status": page.status, "url": page.url, "engine": engine, "escalated": escalated, "count": 0,
                    "content": "", "note": "css selector se kuch nahi mila — selector check karein"}
        parts = [h.html_content if fmt == "html" else (h.markdown() if fmt == "markdown" and hasattr(h, "markdown") else h.get_all_text(separator="\n")) for h in hits[:20]]
        content = ("\n\n---\n\n").join(p for p in parts if p)
    elif fmt == "html":
        content = page.html_content
    elif fmt == "text":
        content = page.get_all_text(separator="\n")
    else:
        try:
            content = page.markdown()
        except Exception:
            content = page.get_all_text(separator="\n")
    await asyncio.to_thread(_cache_put_page, ctx.tenant_id, page)
    out: dict[str, Any] = {"status": page.status, "url": page.url, "engine": engine, "escalated": escalated,
                           "title": (page.css("title")[0].text.strip() if page.css("title") else ""),
                           "content": _cap(content or "", limit)}
    if block:
        out["block_note"] = block
    return _masked(out)


async def scrape_map(ctx: Ctx, url, include=None, max_urls=100, max_pages=5, timeout=15, **_):
    """Links-only discovery (v0.481, the Firecrawl /map shape): fetch a few pages, harvest SAME-SITE urls,
    no content — the cheap 'is site par ka kahan hai' pass before scrape_extract/scrape."""
    start = await asyncio.to_thread(_guard_url, url)
    if not await _robots_ok(start):
        raise ToolError("Is site ke robots.txt ne bots ko mana kiya hai (respect_robots on)")
    try:
        want_urls = max(1, min(int(max_urls or 100), _MAX_MAP_URLS))
    except Exception:
        want_urls = 100
    try:
        want_pages = max(1, min(int(max_pages or 5), _MAX_MAP_FETCHES))
    except Exception:
        want_pages = 5
    pat = None
    if include:
        try:
            pat = re.compile(str(include))
        except re.error:
            raise ToolError("include pattern valid regex nahi hai")
    start_host = urlparse(start).hostname or ""
    seen: set[str] = {start}
    queue = [start]
    urls: list[str] = [start]
    fetched = 0
    skipped_robots = 0
    while queue and fetched < want_pages and len(urls) < want_urls:
        u = queue.pop(0)
        try:
            page = await asyncio.to_thread(_fetch, u, ctx.tenant_id, timeout)
        except Exception:
            continue
        fetched += 1
        if page.status >= 400:
            continue
        for a in page.css("a[href]"):
            href = a.attrib.get("href") or ""
            if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            nxt = urljoin(page.url or u, href).split("#")[0]
            try:
                nu = urlparse(nxt)
            except Exception:
                continue
            if nu.scheme not in ("http", "https") or (nu.hostname or "") != start_host:
                continue
            if pat and not pat.search(nxt):
                continue
            if nu.geturl() in seen:
                continue
            seen.add(nu.geturl())
            if not await _robots_ok(nu.geturl()):
                skipped_robots += 1
                continue
            urls.append(nu.geturl())
            if len(queue) < 200:
                queue.append(nu.geturl())
        await asyncio.sleep(0.3)           # politeness
    urls = urls[:want_urls]
    return _masked({"start": start, "host": start_host, "pages_fetched": fetched,
                    "urls_found": len(urls), "urls": urls, "skipped_by_robots": skipped_robots,
                    "note": "Jis url par data hai us par scrape_extract (css) ya scrape_extract_json (schema) chalayein"})


async def scrape_extract_json(ctx: Ctx, url, schema=None, prompt=None, limit=50, max_chars=24000, timeout=25, **_):
    """No stable css? (v0.481, the Firecrawl /extract idea on the house brain): the page is fetched and read,
    and ONE capped brain call turns it into JSON rows matching the schema you give."""
    import json as _json
    url = await asyncio.to_thread(_guard_url, url)
    if not await _robots_ok(url):
        raise ToolError("Is site ke robots.txt ne is page ke liye bots ko mana kiya hai (respect_robots on)")
    try:
        limit = max(1, min(int(limit or 50), 50))
    except Exception:
        limit = 50
    try:
        page = await asyncio.to_thread(_fetch, url, ctx.tenant_id, timeout)
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Fetch failed: {str(e)[:300]}")
    if page.status >= 400:
        raise ToolError(f"Site ne {page.status} bheja ({getattr(page, 'reason', '')})")
    try:
        text = page.markdown()
    except Exception:
        text = page.get_all_text(separator="\n")
    text = (text or "")[:_BRAIN_TEXT]
    try:
        title = (page.css("title")[0].text.strip() if page.css("title") else "")
    except Exception:
        title = ""
    ask = str(prompt or "").strip() or "Extract every data item on this page (products, entries, rows, facts) as JSON."
    parts = [ask, "Output ONLY valid JSON — no prose, no markdown fences. If the page has a list of items output "
             "a JSON array of objects; otherwise one JSON object."]
    if isinstance(schema, dict) and schema:
        parts.insert(1, "The JSON MUST match this schema exactly: " + _json.dumps(schema, ensure_ascii=False))
    parts.append(f"Page title: {title}")
    parts.append("Page content:")
    parts.append(text)
    answer, brain = await _extract_brain("You turn web page text into strict JSON. Answer with JSON only.", "\n\n".join(parts))
    data = _json_loose(answer)
    if data is None:
        raise ToolError("Brain ne JSON nahi bheja — page shayad bina structure ka hai. scrape_page ka content "
                        "khud padh lein, ya scrape_extract (css selector) try karein.")
    if isinstance(data, list):
        data = data[:limit]
        count = len(data)
    else:
        count = 1
    return _masked({"url": getattr(page, "url", url), "status": page.status, "count": count,
                    "data": data, "brain": brain})


SCRAPE_TOOLS = [
    {"name": "scrape_page", "description": (
        "Fetch and read a PUBLIC webpage fast (Scrapling engine: TLS-impersonated HTTP, no browser, 1-3 s). "
        "Use for single pages: an article, a price page, a notice, a government circular, any link the user gives. "
        "Returns the page title + clean content (markdown by default; 'text' or 'html' also), optionally the links. "
        "Narrow a huge page with css ('div#main', 'table.gradeA'). "
        "If content comes back nearly empty the page is JavaScript-built or blocking bots: try scrape_stealth "
        "(if enabled) or browse_web. Not for pages needing login — browse_web / computer_operator for those."),
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string", "description": "Full link, or a domain like example.com/prices"},
         "format": {"type": "string", "enum": ["markdown", "text", "html"], "description": "Default markdown"},
         "css": {"type": "string", "description": "Optional css to return only matching parts"},
         "include_links": {"type": "boolean", "description": "Add up to 60 outgoing links (text + href)"},
         "max_chars": {"type": "integer", "description": "Content cap, default 24000"}},
         "required": ["url"]}},
    {"name": "scrape_extract", "description": (
        "Pull STRUCTURED data out of a webpage as JSON rows (Scrapling): product lists, price tables, directories, "
        "job/lead listings, exam results. Give ONE css selector that matches a repeating element "
        "('article.product_pod', 'table tr', 'li.card'); optional fields map turns each element into a row: "
        "{'title': 'h3 a@title', 'price': 'p.price_color', 'link': 'a@href'} ('@attr' takes an attribute, plain "
        "css takes text; prefix 'xpath:' for an XPath selector). ADAPTIVE by default: Hoola remembers these "
        "elements per site, so when the site's design changes later the same call still finds them (auto-heal). "
        "similar=true expands one matched card into all its siblings. This is the tool for 'iska data nikaalo'."),
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string", "description": "The page with the data"},
         "selector": {"type": "string", "description": "css for the repeating element (or 'xpath:...' )"},
         "fields": {"type": "object", "description": "Row fields: name -> 'css@attr' or 'css' (text)", "additionalProperties": {"type": "string"}},
         "attr": {"type": "string", "description": "Shorthand when you only want one attribute of each match"},
         "adaptive": {"type": "boolean", "description": "Remember the element per tenant and auto-heal after site changes (default true)"},
         "similar": {"type": "boolean", "description": "Matched only one card? Expand to all similar cards"},
         "identifier": {"type": "string", "description": "Name for the saved element memory, e.g. 'product_cards'"},
         "limit": {"type": "integer", "description": "Max rows (default 100, cap 500)"},
         "timeout": {"type": "integer", "description": "Seconds, default 25"}},
         "required": ["url", "selector"]}},
    {"name": "scrape_many", "description": (
        "Run the SAME scrape_extract selector on MANY pages (max 15) in one call — e.g. 15 product detail pages, "
        "every notice page of a portal. Give the urls list + selector (+ optional fields map). Returns per-page "
        "rows plus per-page errors, so one dead page never kills the batch. Polite (small pause between fetches)."),
     "input_schema": {"type": "object", "properties": {
         "urls": {"type": "array", "items": {"type": "string"}, "description": "Up to 15 page urls"},
         "selector": {"type": "string"}, "fields": {"type": "object", "additionalProperties": {"type": "string"}},
         "attr": {"type": "string"}, "adaptive": {"type": "boolean"},
         "identifier": {"type": "string"}, "limit_per_page": {"type": "integer", "description": "Default 50"},
         "timeout": {"type": "integer", "description": "Per page, default 20"}},
         "required": ["urls", "selector"]}},
    {"name": "scrape_site", "description": (
        "Walk a website the way a crawler does: starts at one url and follows SAME-SITE links (BFS, max 25 pages, "
        "robots.txt respected, small polite delays). Use it to MAP a site or a section — 'is site par ka kahan "
        "hai', find the page with the price list / results / notices — then call scrape_extract on the right page "
        "for the actual data. 'include' narrows the crawl with a regex on the urls (e.g. '/notices?'). Returns "
        "each page's title + first text. Not for JS-only sites."),
     "input_schema": {"type": "object", "properties": {
         "start_url": {"type": "string"},
         "max_pages": {"type": "integer", "description": "Default 15, cap 25"},
         "include": {"type": "string", "description": "Regex the crawled urls must match, e.g. '/product/'"},
         "max_chars_per_page": {"type": "integer", "description": "Text head per page, default 1200"},
         "timeout": {"type": "integer", "description": "Per page, default 20"}},
         "required": ["start_url"]}},
    {"name": "scrape_stealth", "description": (
        "Last resort for sites that BLOCK plain fetchers (Cloudflare challenge, heavy anti-bot) or build the page "
        "in JavaScript: Scrapling's stealth browser engine (real browser fingerprints, optional Cloudflare "
        "challenge solving). Only AFTER scrape_page came back empty/blocked, and only when stealth scraping is "
        "enabled on the server (it launches a real browser = RAM). Slow (30-90 s), one at a time. "
        "Login/typing/forms stay with browse_web / computer_operator."),
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string"},
         "format": {"type": "string", "enum": ["markdown", "text", "html"]},
         "css": {"type": "string", "description": "Optional css to return only matching parts"},
         "wait_selector": {"type": "string", "description": "css to wait for before reading"},
         "solve_cloudflare": {"type": "boolean", "description": "Try to pass a Cloudflare challenge (default false)"},
         "max_chars": {"type": "integer"}, "timeout": {"type": "integer", "description": "Default 90"}},
         "required": ["url"]}},
    {"name": "scrape", "description": (
        "THE default door to read a public page (v0.481, Firecrawl-style waterfall): fast HTTP first (1-3 s), and "
        "when the site blocks bots (401/403/429 or a Cloudflare-style challenge) it ESCALATES BY ITSELF to the "
        "stealth browser — if stealth is enabled on the server. Cache-aware: repeat reads within max_age seconds "
        "come back instantly from the tenant cache. Use this instead of scrape_page when a site might be stubborn; "
        "stealth='never' makes it HTTP-only. Login/typing/forms stay with browse_web / computer_operator."),
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string", "description": "Full link, or a domain like example.com/prices"},
         "format": {"type": "string", "enum": ["markdown", "text", "html"], "description": "Default markdown"},
         "css": {"type": "string", "description": "Optional css to return only matching parts"},
         "include_links": {"type": "boolean", "description": "Add up to 60 outgoing links (text + href)"},
         "max_chars": {"type": "integer", "description": "Content cap, default 24000"},
         "timeout": {"type": "integer", "description": "Seconds, default 25"},
         "max_age": {"type": "integer", "description": "Serve from the tenant cache if fetched within this many seconds (0 = always fresh); default 1800"},
         "stealth": {"type": "string", "enum": ["auto", "never", "always"], "description": "auto = escalate to the stealth browser on a block (default); never = HTTP only; always = stealth directly"}},
         "required": ["url"]}},
    {"name": "scrape_map", "description": (
        "Quick site MAP without reading pages (v0.481): fetches a few pages (max 8), harvests same-site urls "
        "(max 200, robots respected) and returns just the link list — 'is site par ka kahan hai' in one cheap "
        "call. 'include' filters urls with a regex (e.g. '/product/'). Then point scrape_extract / scrape at the "
        "right url for the actual data. Not for JS-only sites."),
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string", "description": "Where to start (homepage or a section)"},
         "include": {"type": "string", "description": "Regex the harvested urls must match, e.g. '/product/'"},
         "max_urls": {"type": "integer", "description": "Default 100, cap 200"},
         "max_pages": {"type": "integer", "description": "Pages fetched to harvest links, default 5, cap 8"},
         "timeout": {"type": "integer", "description": "Per page, default 15"}},
         "required": ["url"]}},
    {"name": "scrape_extract_json", "description": (
        "Page data as JSON WITHOUT a css selector (v0.481): give a JSON schema (and optionally a prompt) and the "
        "page is fetched, read, and ONE brain call turns it into JSON that matches the schema. Use when the page "
        "has no clean repeating element for scrape_extract, or she wants the whole page summarised into fields. "
        "One capped call per page (rows max 50); costs a brain call, so prefer scrape_extract when a css exists."),
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string"},
         "schema": {"type": "object", "description": "JSON schema the output must match, e.g. {'type':'array', 'items':{'type':'object','properties':{'product':{'type':'string'},'price':{'type':'string'}}}}"},
         "prompt": {"type": "string", "description": "What to pull out, in words (optional)"},
         "limit": {"type": "integer", "description": "Max rows (default 50, cap 50)"},
         "timeout": {"type": "integer", "description": "Seconds, default 25"}},
         "required": ["url"]}},
]

SCRAPE_LABELS = {"scrape_page": "Website turant khol kar padh raha hoon",
                 "scrape_extract": "Website se data nikaal raha hoon",
                 "scrape_many": "Kayi pages se data nikaal raha hoon",
                 "scrape_site": "Poori site padh kar map bana raha hoon",
                 "scrape_stealth": "Website advanced mode mein khol raha hoon",
                 "scrape": "Website khol raha hoon (auto mode)",
                 "scrape_map": "Site ka url-naksha bana raha hoon",
                 "scrape_extract_json": "Page padh kar JSON data bana raha hoon"}

SCRAPE_HANDLERS = {"scrape_page": scrape_page, "scrape_extract": scrape_extract, "scrape_many": scrape_many,
                   "scrape_site": scrape_site, "scrape_stealth": scrape_stealth, "scrape": scrape,
                   "scrape_map": scrape_map, "scrape_extract_json": scrape_extract_json}
