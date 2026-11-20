"""v0.999.59 HOOLA SPIDER - Scrapy's way of crawling, built inside Hoola (owner: "github.com/scrapy/scrapy ---
I WANT THIS IN HOOLA -- SAME CLONE").

Scrapy (BSD-3) is read for its design; none of its code or its Twisted reactor rides this tree. The house
already had the readers (v0.474 Scrapling fetch + selectors, v0.481 page cache, v0.486 background crawl
jobs, v0.537 crawl brain); what it lacked is Scrapy's SPIDER: a saved, named recipe that says where to
start, which links to follow, what to pull out of each page, and how to clean it - run in the background
and exported as a file. That is this module.

Scrapy piece -> Hoola piece
- Spider / CrawlSpider + Rule + LinkExtractor -> a saved spec: start_urls, allowed_domains, follow rules
  (allow / deny regex, restrict css, parse yes/no), next_page selector, depth_limit.
- Selectors + ItemLoader processors -> fields {name: "css::text" | "css::attr(href)" | "css@href" |
  "xpath:..."} with "|number" / "|int" / "|url" / "|all" / "|lower" / "|upper" processors.
- Item pipelines -> strip, drop empty items, required fields, dedup by a key field, provenance (_url, _at).
- Scheduler + dupefilter -> a checkpointed frontier with canonical URL fingerprints (fragment and utm_*
  dropped, query sorted) and a depth per request.
- Downloader middlewares -> robots.txt obeyed on every URL (ROBOTSTXT_OBEY is always on), SSRF guard,
  OffsiteMiddleware (allowed_domains), RetryMiddleware (408 / 429 / 5xx + timeouts, 2 retries, Retry-After
  honoured up to 60 s), AutoThrottle (per-host delay follows the measured latency, never under
  spider_min_delay_s, doubled after 429 / 503), block detection (3 blocked pages in a row closes the run).
- Extensions -> stats (requests, statuses, items scraped / dropped, retries, robots skips, offsite) and
  CloseSpider (pagecount / itemcount / timeout) with a close reason.
- JOBDIR (pause + resume) -> the run checkpoints after every page; a worker restart resumes it.
- Feed exports -> CSV / JSON / JSON lines / Excel file cards + a Hoola dataset (data_read can read it).
- Contracts (scrapy check) -> action=check: one page fetched and parsed, nothing saved.

House walls: HTTP only (no browser), GET only, no cookies / headers / login / forms in a spec (refused by
name), public addresses only, robots always obeyed, page / item / time caps refused before the run, one
run per spider at a time, every item carries the page it came from.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

log = logging.getLogger("santosh.spider")

MAX_START = 20
MAX_PAGES = 500
MAX_ITEMS = 10_000
MAX_DEPTH = 10
MAX_MINUTES = 120
MAX_FIELDS = 40
MAX_RULES = 10
MAX_CONCURRENCY = 8
RETRY_STATUS = {408, 429, 500, 502, 503, 504, 522, 524}
RETRY_TIMES = 2
_KEEP_RUNS = 10
_RUNNING: set[str] = set()
_TASKS: set[asyncio.Task] = set()
_sleep = asyncio.sleep          # tests swap this out

# Keys a spec may never carry: a spider here reads public pages, it never signs in or sends anything.
REFUSED_KEYS = ("cookies", "cookie", "headers", "header", "auth", "login", "password", "passwd", "token",
                "formdata", "form", "method", "body", "proxy", "user_agent", "session", "otp")
PROCESSORS = ("number", "int", "url", "all", "lower", "upper", "strip", "join")


class SpiderError(Exception):
    pass


# --------------------------------------------------------------------------- the spec (Spider class as data)

def _clamp(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _check_regex(pat: str, where: str) -> str:
    pat = str(pat or "").strip()[:300]
    if not pat:
        return ""
    try:
        re.compile(pat)
    except re.error as e:
        raise SpiderError(f"{where}: '{pat}' is not a valid pattern ({e}).")
    return pat


def _refused(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).strip().lower() in REFUSED_KEYS:
                raise SpiderError(f"'{path + str(k)}' is not allowed in a spider: Hoola spiders read public pages "
                                  "only - no sign-in, cookies, headers or forms.")
            if k != "fields":
                _refused(v, f"{path}{k}.")
    elif isinstance(obj, list):
        for v in obj:
            _refused(v, path)


def _check_field(name: str, spec: str) -> str:
    spec = str(spec or "").strip()
    if not spec:
        raise SpiderError(f"Field '{name}' has no selector.")
    sel, *procs = [p.strip() for p in spec.split("|")]
    for p in procs:
        if p and p not in PROCESSORS:
            raise SpiderError(f"Field '{name}': '|{p}' is not a known step (use {', '.join(PROCESSORS)}).")
    return spec[:400]


def validate(spec: Any) -> dict[str, Any]:
    """The spider as data, checked. Unknown sizes are clamped to the caps; bad ones refused with the reason."""
    if not isinstance(spec, dict):
        raise SpiderError("The spider must be an object with start_urls and fields.")
    _refused(spec)
    starts = spec.get("start_urls") or ([spec["start_url"]] if spec.get("start_url") else [])
    if isinstance(starts, str):
        starts = [starts]
    starts = [str(u).strip() for u in starts if str(u).strip()]
    if not starts:
        raise SpiderError("Give at least one start_url.")
    if len(starts) > MAX_START:
        raise SpiderError(f"At most {MAX_START} start_urls.")
    for u in starts:
        if urlparse(u).scheme not in ("http", "https") or not urlparse(u).hostname:
            raise SpiderError(f"'{u}' is not an http(s) address.")
    allowed = spec.get("allowed_domains") or sorted({_host(u) for u in starts})
    if isinstance(allowed, str):
        allowed = [allowed]
    allowed = [str(d).lower().strip().removeprefix("www.") for d in allowed if str(d).strip()][:20]
    item = spec.get("item") or {}
    if not isinstance(item, dict):
        raise SpiderError("item must be an object: {container, fields}.")
    fields = item.get("fields") or spec.get("fields") or {}
    if not isinstance(fields, dict) or not fields:
        raise SpiderError("Give the fields to pull out, e.g. {\"title\": \"h1::text\", \"price\": \".price|number\"}.")
    if len(fields) > MAX_FIELDS:
        raise SpiderError(f"At most {MAX_FIELDS} fields.")
    fields = {str(k)[:60]: _check_field(str(k), v) for k, v in fields.items()}
    rules_in = spec.get("follow") or spec.get("rules") or []
    if isinstance(rules_in, dict):
        rules_in = [rules_in]
    if len(rules_in) > MAX_RULES:
        raise SpiderError(f"At most {MAX_RULES} follow rules.")
    rules = []
    for i, r in enumerate(rules_in):
        if isinstance(r, str):
            r = {"allow": r}
        if not isinstance(r, dict):
            raise SpiderError(f"Follow rule {i + 1} must be an object.")
        rules.append({"allow": _check_regex(r.get("allow", ""), f"rule {i + 1} allow"),
                      "deny": _check_regex(r.get("deny", ""), f"rule {i + 1} deny"),
                      "css": str(r.get("css") or r.get("restrict_css") or "")[:200],
                      "parse": bool(r.get("parse", True)), "follow": bool(r.get("follow", True))})
    pipes = spec.get("pipelines") or {}
    required = pipes.get("required") or spec.get("required") or []
    if isinstance(required, str):
        required = [required]
    dedup = str(pipes.get("dedup") or spec.get("dedup") or "").strip()
    for f in list(required) + ([dedup] if dedup and dedup != "_url" else []):
        if f not in fields:
            raise SpiderError(f"'{f}' is used in the pipelines but is not one of the fields.")
    sitemap_urls = spec.get("sitemap_urls") or []
    if isinstance(sitemap_urls, str):
        sitemap_urls = [sitemap_urls]
    sitemap_urls = [str(u).strip() for u in sitemap_urls if str(u).strip()][:5]
    for u in sitemap_urls:
        if urlparse(u).scheme not in ("http", "https") or not urlparse(u).hostname:
            raise SpiderError(f"Sitemap '{u}' is not an http(s) address.")
    sitemap = bool(spec.get("sitemap") or sitemap_urls)
    srules_in = spec.get("sitemap_rules") or []
    if isinstance(srules_in, dict):
        srules_in = [srules_in]
    sitemap_rules = []
    for i, r in enumerate(srules_in[:MAX_RULES]):
        if isinstance(r, str):
            r = {"allow": r}
        sitemap_rules.append({"allow": _check_regex(r.get("allow", ""), f"sitemap rule {i + 1}"),
                              "parse": bool(r.get("parse", True))})
    render = str(spec.get("render") or "never").lower()
    if render not in ("never", "auto", "always"):
        raise SpiderError("render must be never, auto or always.")
    name = re.sub(r"[^a-z0-9_-]+", "-", str(spec.get("name") or _host(starts[0]) or "spider").lower()).strip("-")[:40]
    return {
        "name": name or "spider",
        "start_urls": starts,
        "allowed_domains": allowed,
        "item": {"container": str(item.get("container") or spec.get("container") or "")[:200], "fields": fields},
        "follow": rules,
        "next_page": str(spec.get("next_page") or "")[:200],
        "parse_start": bool(spec.get("parse_start", True)),
        "depth_limit": _clamp(spec.get("depth_limit"), 0, MAX_DEPTH, 2),
        "max_pages": _clamp(spec.get("max_pages"), 1, MAX_PAGES, 50),
        "max_items": _clamp(spec.get("max_items"), 1, MAX_ITEMS, 1000),
        "max_minutes": _clamp(spec.get("max_minutes"), 1, MAX_MINUTES, 30),
        "pipelines": {"required": [str(f) for f in required], "dedup": dedup},
        "concurrency": _clamp(spec.get("concurrency"), 1, MAX_CONCURRENCY, 4),
        "per_host": _clamp(spec.get("per_host"), 1, 4, 2),
        "sitemap": sitemap,
        "sitemap_urls": sitemap_urls,
        "sitemap_rules": sitemap_rules,
        "sitemap_and_start": bool(spec.get("sitemap_and_start", False)),
        "render": render,
    }


# --------------------------------------------------------------------------- store (per-tenant sqlite)

def _db(tenant: str) -> Path:
    from .agent import scrape_tools as st
    return Path(st._tenant_dir(tenant)) / "spider.db"


def _con(tenant: str) -> sqlite3.Connection:
    con = sqlite3.connect(str(_db(tenant)), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS spiders (name TEXT PRIMARY KEY, spec TEXT, created_at REAL, "
                "updated_at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS spider_runs (id TEXT PRIMARY KEY, spider TEXT, spec TEXT, status TEXT, "
                "tries INTEGER DEFAULT 0, checkpoint TEXT, stats TEXT, close_reason TEXT, error TEXT, conv TEXT, "
                "created_at REAL, updated_at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS spider_items (run_id TEXT, key TEXT, seq INTEGER, url TEXT, data TEXT, "
                "PRIMARY KEY (run_id, key))")
    return con


def save_spider(tenant: str, spec: Any) -> dict[str, Any]:
    clean = validate(spec)
    now = time.time()
    con = _con(tenant)
    try:
        con.execute("INSERT INTO spiders (name, spec, created_at, updated_at) VALUES (?,?,?,?) "
                    "ON CONFLICT(name) DO UPDATE SET spec = excluded.spec, updated_at = excluded.updated_at",
                    (clean["name"], json.dumps(clean), now, now))
        con.commit()
    finally:
        con.close()
    return clean


def get_spider(tenant: str, name: str) -> dict[str, Any] | None:
    con = _con(tenant)
    try:
        r = con.execute("SELECT spec FROM spiders WHERE name = ?", (str(name),)).fetchone()
        return json.loads(r["spec"]) if r else None
    finally:
        con.close()


def list_spiders(tenant: str) -> list[dict[str, Any]]:
    con = _con(tenant)
    try:
        out = []
        for r in con.execute("SELECT name, spec, updated_at FROM spiders ORDER BY updated_at DESC").fetchall():
            s = json.loads(r["spec"])
            last = con.execute("SELECT id, status, stats FROM spider_runs WHERE spider = ? ORDER BY created_at DESC "
                               "LIMIT 1", (r["name"],)).fetchone()
            out.append({"name": r["name"], "start_urls": s["start_urls"][:3], "fields": list(s["item"]["fields"]),
                        "last_run": ({"run_id": last["id"], "status": last["status"],
                                      "items": json.loads(last["stats"] or "{}").get("items", 0)} if last else None)})
        return out
    finally:
        con.close()


def delete_spider(tenant: str, name: str) -> bool:
    con = _con(tenant)
    try:
        cur = con.execute("DELETE FROM spiders WHERE name = ?", (str(name),))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    d = dict(r)
    for k in ("spec", "checkpoint", "stats"):
        try:
            d[k] = json.loads(d.get(k) or "{}")
        except Exception:
            d[k] = {}
    return d


def start_run(tenant: str, name: str, conv: str = "") -> dict[str, Any]:
    spec = get_spider(tenant, name)
    if spec is None:
        raise SpiderError(f"No spider called '{name}'. Save it first.")
    con = _con(tenant)
    try:
        live = con.execute("SELECT * FROM spider_runs WHERE spider = ? AND status IN ('queued','running') "
                           "ORDER BY created_at DESC LIMIT 1", (spec["name"],)).fetchone()
        if live is not None:
            out = _row(live)
            out["_created"] = False
            return out
        rid = "sp_" + uuid.uuid4().hex[:12]
        now = time.time()
        from .config import get_settings
        st_ = get_settings()
        browser_on = bool(getattr(st_, "spider_browser_enabled", False)) and bool(getattr(st_, "scrape_stealth_enabled", False))
        if spec.get("render") == "always" and not browser_on:
            raise SpiderError("This spider asks for the browser on every page (render=always), but the spider "
                              "browser is off on this server. The owner turns it on with SPIDER_BROWSER_ENABLED=true "
                              "and SCRAPE_STEALTH_ENABLED=true (and 'scrapling install' once); or use render=auto / never.")
        queue = [{"url": u, "depth": 0, "parse": spec["parse_start"], "retry": 0,
                  "render": spec.get("render") == "always"} for u in spec["start_urls"]]
        cp = {"queue": queue, "seen": [fingerprint(u) for u in spec["start_urls"]], "delays": {}, "blocked_row": 0,
              "started": now}
        con.execute("INSERT INTO spider_runs (id, spider, spec, status, checkpoint, stats, conv, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)", (rid, spec["name"], json.dumps(spec), "queued", json.dumps(cp),
                                                   json.dumps(_stats0()), conv, now, now))
        con.commit()
        out = _row(con.execute("SELECT * FROM spider_runs WHERE id = ?", (rid,)).fetchone())
        out["_created"] = True
        _forget_old(con, spec["name"])
        return out
    finally:
        con.close()


def _forget_old(con: sqlite3.Connection, spider: str) -> None:
    old = con.execute("SELECT id FROM spider_runs WHERE spider = ? AND status NOT IN ('queued','running') "
                      "ORDER BY created_at DESC LIMIT -1 OFFSET ?", (spider, _KEEP_RUNS)).fetchall()
    for r in old:
        con.execute("DELETE FROM spider_items WHERE run_id = ?", (r["id"],))
        con.execute("DELETE FROM spider_runs WHERE id = ?", (r["id"],))
    con.commit()


def get_run(tenant: str, run_id: str = "") -> dict[str, Any] | None:
    con = _con(tenant)
    try:
        if run_id:
            r = con.execute("SELECT * FROM spider_runs WHERE id = ?", (run_id,)).fetchone()
        else:
            r = con.execute("SELECT * FROM spider_runs ORDER BY created_at DESC LIMIT 1").fetchone()
        return _row(r)
    finally:
        con.close()


def stop_run(tenant: str, run_id: str) -> bool:
    con = _con(tenant)
    try:
        cur = con.execute("UPDATE spider_runs SET status = 'stopped', close_reason = 'stopped by her', updated_at = ? "
                          "WHERE id = ? AND status IN ('queued','running')", (time.time(), run_id))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


def _save(tenant: str, run_id: str, **f: Any) -> None:
    for k in ("checkpoint", "stats"):
        if k in f and not isinstance(f[k], str):
            f[k] = json.dumps(f[k])
    f.setdefault("updated_at", time.time())
    con = _con(tenant)
    try:
        con.execute(f"UPDATE spider_runs SET {', '.join(k + ' = ?' for k in f)} WHERE id = ?", (*f.values(), run_id))
        con.commit()
    finally:
        con.close()


def items(tenant: str, run_id: str, offset: int = 0, limit: int = 20) -> tuple[list[dict], int]:
    con = _con(tenant)
    try:
        total = con.execute("SELECT COUNT(*) FROM spider_items WHERE run_id = ?", (run_id,)).fetchone()[0]
        rows = con.execute("SELECT data FROM spider_items WHERE run_id = ? ORDER BY seq LIMIT ? OFFSET ?",
                           (run_id, max(1, int(limit)), max(0, int(offset)))).fetchall()
        return [json.loads(r["data"]) for r in rows], int(total)
    finally:
        con.close()


def _put_items(tenant: str, run_id: str, rows: list[tuple[str, str, dict]], start_seq: int) -> int:
    """Insert items; a key already stored (dedup pipeline) is ignored. Returns how many were new."""
    con = _con(tenant)
    try:
        n = 0
        for key, url, data in rows:
            cur = con.execute("INSERT OR IGNORE INTO spider_items (run_id, key, seq, url, data) VALUES (?,?,?,?,?)",
                              (run_id, key, start_seq + n, url, json.dumps(data, ensure_ascii=False)))
            n += cur.rowcount
        con.commit()
        return n
    finally:
        con.close()


# --------------------------------------------------------------------------- scheduler pieces

_TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_eid$|ref$)", re.I)


def canonical(url: str) -> str:
    p = urlparse(url)
    q = sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not _TRACKING.match(k))
    path = p.path or "/"
    return urlunparse((p.scheme.lower(), (p.netloc or "").lower(), path, "", urlencode(q), ""))


def fingerprint(url: str) -> str:
    return hashlib.sha1(canonical(url).encode()).hexdigest()[:16]


def offsite(url: str, allowed: list[str]) -> bool:
    h = _host(url)
    return not any(h == d or h.endswith("." + d) for d in allowed)


def _stats0() -> dict[str, Any]:
    return {"requests": 0, "responses": {}, "items": 0, "dropped": 0, "duplicates": 0, "retries": 0,
            "robots_skipped": 0, "offsite": 0, "blocked": 0, "errors": 0, "max_depth_seen": 0}


# --------------------------------------------------------------------------- parsing (selectors + loaders)

_SCRAPY_ATTR = re.compile(r"::attr\(([^)]+)\)\s*$")


def _select(el: Any, sel: str) -> list[Any]:
    sel = sel.strip()
    if sel.lower().startswith("xpath:"):
        try:
            return list(el.xpath(sel[6:].strip()))
        except Exception:
            return []
    try:
        return list(el.css(sel))
    except Exception:
        return []


def _text_of(node: Any) -> str:
    if isinstance(node, str):
        return node.strip()
    try:
        t = node.get_all_text(separator=" ").strip()
    except Exception:
        t = ""
    return (t or str(getattr(node, "text", "") or "")).strip()


def _values(el: Any, sel: str) -> list[str]:
    """'h1::text' / 'a::attr(href)' (Scrapy) / 'a@href' (Hoola) / 'xpath:...' / '@href' (the element's own)."""
    sel = sel.strip()
    attr = None
    m = _SCRAPY_ATTR.search(sel)
    if m:
        attr, sel = m.group(1).strip(), sel[:m.start()]
    elif sel.endswith("::text"):
        sel = sel[:-6]
    elif not sel.lower().startswith("xpath:") and "@" in sel:
        sel, attr = sel.rsplit("@", 1)
    sel = sel.strip()
    nodes = [el] if not sel else _select(el, sel)
    out = []
    for n in nodes:
        if attr:
            v = getattr(n, "attrib", {}).get(attr) if not isinstance(n, str) else None
        else:
            v = _text_of(n)
        if v not in (None, ""):
            out.append(re.sub(r"\s+", " ", str(v)).strip()[:2000])
    return out


_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _process(vals: list[str], procs: list[str], base: str) -> Any:
    if "url" in procs:
        vals = [urljoin(base, v) for v in vals]
    if "lower" in procs:
        vals = [v.lower() for v in vals]
    if "upper" in procs:
        vals = [v.upper() for v in vals]
    if "number" in procs or "int" in procs:
        nums = []
        for v in vals:
            m = _NUM.search(v.replace("₹", ""))
            if m:
                n = float(m.group(0).replace(",", ""))
                nums.append(int(n) if "int" in procs or n.is_integer() else n)
        vals = nums
    if "all" in procs:
        return vals
    if "join" in procs:
        return " ".join(str(v) for v in vals)
    return vals[0] if vals else None


def extract(page: Any, spec: dict[str, Any], url: str) -> list[dict[str, Any]]:
    """One page -> its items (the parse callback)."""
    item = spec["item"]
    boxes = _select(page, item["container"]) if item.get("container") else [page]
    out = []
    for box in boxes:
        row: dict[str, Any] = {}
        for name, fs in item["fields"].items():
            sel, *procs = [p.strip() for p in fs.split("|")]
            row[name] = _process(_values(box, sel), [p for p in procs if p], url)
        out.append(row)
    return out


def pipeline(rows: list[dict[str, Any]], spec: dict[str, Any], url: str) -> tuple[list[tuple[str, str, dict]], int]:
    """Item pipelines: drop empty, drop missing required, key for dedup, provenance. Returns (kept, dropped)."""
    req = spec["pipelines"]["required"]
    dedup = spec["pipelines"]["dedup"]
    kept, dropped = [], 0
    for r in rows:
        if all(v in (None, "", []) for v in r.values()):
            dropped += 1
            continue
        if any(r.get(f) in (None, "", []) for f in req):
            dropped += 1
            continue
        if dedup == "_url":
            key = fingerprint(url)
        elif dedup:
            key = hashlib.sha1(json.dumps(r.get(dedup), sort_keys=True, default=str).encode()).hexdigest()[:20]
        else:
            key = hashlib.sha1(json.dumps(r, sort_keys=True, default=str).encode()).hexdigest()[:20]
        kept.append((key, url, r | {"_url": url, "_at": time.strftime("%Y-%m-%d %H:%M", time.gmtime())}))
    return kept, dropped


def links(page: Any, spec: dict[str, Any], url: str, depth: int, parse_here: bool) -> list[dict[str, Any]]:
    """LinkExtractor + Rules + next_page. Each link carries whether its page is parsed for items."""
    out: list[dict[str, Any]] = []
    if spec.get("next_page"):
        for href in _values(page, spec["next_page"] if "@" in spec["next_page"] or "::attr" in spec["next_page"]
                            else spec["next_page"] + "::attr(href)")[:1]:
            out.append({"url": urljoin(url, href), "depth": depth, "parse": parse_here, "retry": 0, "next": True})
    if depth >= spec["depth_limit"]:
        return out
    for r in spec["follow"]:
        if not r["follow"]:
            continue
        area = _select(page, r["css"]) if r["css"] else [page]
        for a in area:
            for href in _values(a, "a::attr(href)"):
                full = urljoin(url, href).split("#")[0]
                if urlparse(full).scheme not in ("http", "https"):
                    continue
                if r["allow"] and not re.search(r["allow"], full):
                    continue
                if r["deny"] and re.search(r["deny"], full):
                    continue
                out.append({"url": full, "depth": depth + 1, "parse": r["parse"], "retry": 0})
    return out


# --------------------------------------------------------------------------- the engine

def _retry_after(page: Any) -> float:
    try:
        v = (getattr(page, "headers", {}) or {}).get("retry-after") or (getattr(page, "headers", {}) or {}).get("Retry-After")
        return min(60.0, float(v))
    except Exception:
        return 0.0


def _limit_reason(spec: dict[str, Any], stats: dict[str, Any], cp: dict[str, Any], queue: list) -> str:
    started = float(cp.get("started") or time.time())
    if stats["items"] >= spec["max_items"]:
        return f"item limit reached ({spec['max_items']})"
    if stats["requests"] >= spec["max_pages"]:
        return f"page limit reached ({spec['max_pages']})"
    if time.time() - started > spec["max_minutes"] * 60:
        return f"time limit reached ({spec['max_minutes']} min)"
    if int(cp.get("blocked_row") or 0) >= 3:
        return "the site blocked 3 pages in a row"
    if not queue:
        return "finished - no pages left to read"
    return ""


def _batch(queue: list[dict], spec: dict[str, Any], room: int) -> tuple[list[dict], list[dict]]:
    """CONCURRENT_REQUESTS + CONCURRENT_REQUESTS_PER_DOMAIN: up to `concurrency` requests, at most
    `per_host` of them for one site; requests still waiting for a retry time stay in the queue."""
    take, keep, per = [], [], {}
    now = time.time()
    limit = min(int(spec.get("concurrency", 4)), max(1, room))
    for req in queue:
        h = _host(req["url"])
        if (len(take) < limit and per.get(h, 0) < int(spec.get("per_host", 2))
                and float(req.get("not_before") or 0) <= now + 0.5):
            take.append(req)
            per[h] = per.get(h, 0) + 1
        else:
            keep.append(req)
    if not take and keep:                 # everything is waiting for a retry time: take the soonest
        keep.sort(key=lambda r: float(r.get("not_before") or 0))
        take, keep = [keep[0]], keep[1:]
    return take, keep


async def _render(url: str) -> Any:
    """One page through the stealth browser (JavaScript drawn). One browser on the server at a time."""
    from .agent import scrape_tools as st

    def go():
        if not st._STEALTH_SEM.acquire(timeout=120):
            raise RuntimeError("the browser is busy")
        try:
            return st._stealth_fetch(url, timeout=60)
        finally:
            st._STEALTH_SEM.release()
    return await asyncio.to_thread(go)


async def _fetch_one(tenant: str, req: dict, start_in: float) -> tuple[dict, Any, int, float, str]:
    """(req, page, status, latency, note). Robots + guard + fetch for one request; never raises."""
    from .agent import scrape_tools as st
    from .agent.tools import ToolError
    await _sleep(max(0.0, start_in, float(req.get("not_before") or 0) - time.time()))
    url = req["url"]
    try:
        url = await asyncio.to_thread(st._guard_url, url)
    except ToolError:
        return req, None, -1, 0.0, "guard"
    if not await st._robots_ok(url):
        return req, None, -2, 0.0, "robots"
    t0 = time.time()
    if req.get("render"):
        try:
            page = await _render(url)
            return req, page, int(getattr(page, "status", 0) or 0), time.time() - t0, "rendered"
        except Exception as e:          # noqa: BLE001
            log.info("spider render failed %s: %s", url, str(e)[:120])
            return req, None, 0, time.time() - t0, "render failed"
    try:
        page = await asyncio.to_thread(st._fetch, url, tenant)
        return req, page, int(getattr(page, "status", 0) or 0), time.time() - t0, ""
    except Exception as e:              # noqa: BLE001
        log.info("spider fetch failed %s: %s", url, str(e)[:120])
        return req, None, 0, time.time() - t0, "fetch failed"


def _looks_empty(page: Any, why_blocked: str) -> bool:
    if why_blocked and "empty shell" in why_blocked:
        return True
    try:
        text = page.get_all_text(separator=" ") or ""
    except Exception:
        text = ""
    return len(text.strip()) < 400


async def _sitemap_urls(spec: dict[str, Any]) -> tuple[list[str], list[str]]:
    """SitemapSpider: every page the site lists in its own sitemap (robots.txt Sitemap: lines, indexes, .gz)."""
    import httpx

    from .agent import scrape_tools as st
    from .crawl import seed as _seed
    from .web import UA
    want = spec["max_pages"] * 4
    urls: list[str] = []
    notes: list[str] = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": UA}) as c:
        for start in (spec.get("sitemap_urls") or spec["start_urls"])[:5]:
            r = await _seed.from_sitemaps(start, c, guard=st._guard_url, max_urls=want)
            urls.extend(u for u in r.urls if u not in urls)
            notes.extend(r.notes[:3])
            if len(urls) >= want:
                break
    return urls[:want], notes[:6]


def _sitemap_queue(spec: dict[str, Any], urls: list[str]) -> list[dict]:
    rules = spec.get("sitemap_rules") or [{"allow": "", "parse": True}]
    out = []
    for u in urls:
        for r in rules:
            if r.get("allow") and not re.search(r["allow"], u):
                continue
            out.append({"url": u, "depth": 0, "parse": bool(r.get("parse", True)), "retry": 0})
            break
    return out


async def run(tenant: str, run_id: str) -> None:
    """The crawl loop: a batch of requests at a time (several sites in parallel, a polite gap between two
    requests to the same site), checkpoint after every batch, honest close reason."""
    from .agent import scrape_tools as st
    from .config import get_settings
    s = get_settings()
    min_delay = float(getattr(s, "spider_min_delay_s", 1.0))
    browser_on = bool(getattr(s, "spider_browser_enabled", False)) and bool(getattr(s, "scrape_stealth_enabled", False))
    try:
        while True:
            row = get_run(tenant, run_id)
            if row is None or row["status"] not in ("running",):
                return
            spec, cp, stats = row["spec"], row["checkpoint"], row["stats"] or _stats0()
            queue = list(cp.get("queue") or [])
            seen = set(cp.get("seen") or [])
            if spec.get("sitemap") and not cp.get("sitemap_done"):
                found, notes = await _sitemap_urls(spec)
                q2 = _sitemap_queue(spec, found)
                fresh = [q for q in q2 if fingerprint(q["url"]) not in seen
                         and not offsite(q["url"], spec["allowed_domains"])]
                seen.update(fingerprint(q["url"]) for q in fresh)
                queue = (queue if spec.get("sitemap_and_start") else []) + fresh
                cp.update(sitemap_done=True, sitemap_found=len(found), sitemap_notes=notes)
                _save(tenant, run_id, checkpoint=cp | {"queue": queue, "seen": sorted(seen)}, stats=stats)
                continue
            reason = _limit_reason(spec, stats, cp, queue)
            if reason:
                _save(tenant, run_id, status="done", close_reason=reason, stats=stats, checkpoint=cp)
                _tell_done(tenant, row, stats, reason)
                return
            take, queue = _batch(queue, spec, spec["max_pages"] - stats["requests"])
            delays = dict(cp.get("delays") or {})
            last_at = dict(cp.get("last_at") or {})
            now = time.time()
            jobs = []
            for req in take:
                h = _host(req["url"])
                gap = float(delays.get(h, min_delay))
                at = max(now, float(last_at.get(h, 0)) + gap)      # DOWNLOAD_DELAY per site, across batches
                last_at[h] = at
                jobs.append(_fetch_one(tenant, req, at - now))
            cp["last_at"] = last_at
            results = await asyncio.gather(*jobs)
            for req, page, status, latency, note in results:
                if status == -1:
                    stats["errors"] += 1
                    continue
                if status == -2:
                    stats["robots_skipped"] += 1
                    continue
                stats["requests"] += 1
                if note == "rendered":
                    stats["rendered"] = stats.get("rendered", 0) + 1
                stats["responses"][str(status)] = stats["responses"].get(str(status), 0) + 1
                h = _host(req["url"])
                wait = float(delays.get(h, min_delay))
                new_delay = max(min_delay, (wait + latency) / 2)        # AutoThrottle
                if status in (429, 503):
                    new_delay = min(30.0, max(wait, min_delay) * 2)
                delays[h] = round(min(30.0, new_delay), 2)
                if page is None or status in RETRY_STATUS:
                    if int(req.get("retry", 0)) < RETRY_TIMES:
                        stats["retries"] += 1
                        ra = _retry_after(page) if page is not None else 0
                        queue.append(req | {"retry": int(req.get("retry", 0)) + 1,
                                            "not_before": time.time() + max(ra, 2.0 * (req.get("retry", 0) + 1))})
                    else:
                        stats["errors"] += 1
                    continue
                blk = await asyncio.to_thread(st._blocked, page)
                final = getattr(page, "url", "") or req["url"]
                rows = await asyncio.to_thread(extract, page, spec, final) if req.get("parse") else []
                kept, dropped = pipeline(rows, spec, final) if rows else ([], 0)
                wants_render = (not req.get("render") and spec.get("render") == "auto" and browser_on
                                and stats.get("rendered", 0) < int(getattr(s, "spider_browser_pages", 50))
                                and (bool(blk) or (req.get("parse") and not kept and _looks_empty(page, blk or ""))))
                if wants_render:
                    queue.insert(0, req | {"render": True, "not_before": 0})
                    stats["render_asked"] = stats.get("render_asked", 0) + 1
                    continue
                if blk or status >= 400:
                    if blk:
                        stats["blocked"] += 1
                        cp["blocked_row"] = int(cp.get("blocked_row") or 0) + 1
                        cp["last_block"] = str(blk)[:140]
                    else:
                        stats["errors"] += 1
                    continue
                cp["blocked_row"] = 0
                room = spec["max_items"] - stats["items"]
                kept = kept[:max(0, room)]
                new = _put_items(tenant, run_id, kept, stats["items"]) if kept else 0
                stats["items"] += new
                stats["duplicates"] += len(kept) - new
                stats["dropped"] += dropped
                for nxt in await asyncio.to_thread(links, page, spec, final, int(req.get("depth", 0)),
                                                   bool(req.get("parse"))):
                    if offsite(nxt["url"], spec["allowed_domains"]):
                        stats["offsite"] += 1
                        continue
                    fp = fingerprint(nxt["url"])
                    if fp in seen:
                        continue
                    if len(queue) >= spec["max_pages"] * 4:
                        break
                    seen.add(fp)
                    if spec.get("render") == "always":
                        nxt["render"] = True
                    stats["max_depth_seen"] = max(stats["max_depth_seen"], nxt["depth"])
                    if nxt.get("next"):
                        queue.insert(0, {k: v for k, v in nxt.items() if k != "next"})
                    else:
                        queue.append(nxt)
            cp["delays"] = delays
            _save(tenant, run_id, checkpoint=cp | {"queue": queue, "seen": sorted(seen)}, stats=stats)
    except asyncio.CancelledError:
        try:
            _save(tenant, run_id, status="queued", error="worker stopped - continues from its checkpoint")
        except Exception:
            pass
        raise
    except Exception as e:     # noqa: BLE001
        log.exception("spider run %s failed", run_id)
        try:
            _save(tenant, run_id, status="queued", error=str(e)[:300])
        except Exception:
            pass


def _tell_done(tenant: str, row: dict[str, Any], stats: dict[str, Any], reason: str) -> None:
    try:
        from . import convs, events
        conv = row.get("conv") or convs.notice_chat(tenant)
        if conv:
            events.notify(conv, f"Spider '{row['spider']}' finished: {stats['items']} items from "
                                f"{stats['requests']} pages ({reason}). Ask to export it as CSV or Excel "
                                f"(run {row['id']}).")
    except Exception:   # noqa: BLE001
        pass


# --------------------------------------------------------------------------- worker tick

def _candidates(stale_s: int) -> list[tuple[str, str]]:
    root = Path("data") / "scraping"
    out: list[tuple[str, str]] = []
    if not root.is_dir():
        return out
    now = time.time()
    for db in sorted(root.glob("*/spider.db")):
        try:
            con = sqlite3.connect(str(db), timeout=5)
            rows = con.execute("SELECT id FROM spider_runs WHERE status = 'queued' OR (status = 'running' AND "
                               "updated_at < ?) ORDER BY created_at LIMIT 8", (now - max(30, stale_s),)).fetchall()
            con.close()
            out.extend((db.parent.name, r[0]) for r in rows)
        except Exception:
            continue
    return out


def _claim(tenant: str, run_id: str, tries_max: int) -> bool:
    con = _con(tenant)
    try:
        cur = con.execute("UPDATE spider_runs SET status = 'running', tries = tries + 1, updated_at = ? WHERE id = ? "
                          "AND status IN ('queued','running') AND tries < ?", (time.time(), run_id, tries_max))
        con.commit()
        if cur.rowcount:
            return True
        con.execute("UPDATE spider_runs SET status = 'failed', close_reason = 'stopped after repeated failures', "
                    "updated_at = ? WHERE id = ? AND status IN ('queued','running')", (time.time(), run_id))
        con.commit()
        return False
    finally:
        con.close()


async def tick() -> int:
    from .config import get_settings
    s = get_settings()
    if not getattr(s, "spider_enabled", True):
        return 0
    budget = max(0, int(getattr(s, "spider_max_running", 2)) - len(_RUNNING))
    started = 0
    for tenant, rid in _candidates(int(getattr(s, "spider_stale_s", 180))):
        if started >= budget:
            break
        key = f"{tenant}:{rid}"
        if key in _RUNNING or not _claim(tenant, rid, int(getattr(s, "spider_tries", 3))):
            continue
        _RUNNING.add(key)
        t = asyncio.ensure_future(run(tenant, rid))
        _TASKS.add(t)

        def _done(_t, key=key):
            _TASKS.discard(_t)
            _RUNNING.discard(key)
        t.add_done_callback(_done)
        started += 1
    return started


async def drain() -> None:
    while _TASKS:
        await asyncio.gather(*list(_TASKS), return_exceptions=True)


# --------------------------------------------------------------------------- feed exports

def export_bytes(rows: list[dict[str, Any]], fmt: str) -> tuple[bytes, str]:
    fmt = (fmt or "csv").lower()
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)

    def cell(v: Any) -> Any:
        if isinstance(v, (list, dict)):
            v = json.dumps(v, ensure_ascii=False)
        if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
            v = "'" + v          # spreadsheet formula injection guard
        return v

    if fmt == "json":
        return json.dumps(rows, ensure_ascii=False, indent=1).encode(), ".json"
    if fmt in ("jsonl", "jsonlines"):
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows).encode(), ".jsonl"
    if fmt in ("xlsx", "excel"):
        from openpyxl import Workbook
        import io
        wb = Workbook()
        ws = wb.active
        ws.title = "items"
        ws.append(cols)
        for r in rows:
            ws.append([cell(r.get(c)) for c in cols])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), ".xlsx"
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([cell(r.get(c)) if r.get(c) is not None else "" for c in cols])
    return ("﻿" + buf.getvalue()).encode(), ".csv"
