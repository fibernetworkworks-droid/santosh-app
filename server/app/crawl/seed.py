"""Item 4: find URLs WITHOUT fetching pages. Hand-built (the port law).

The gap: `scrape_map` discovers links by fetching up to 8 pages and harvesting their HTML
(`_MAX_MAP_FETCHES = 8`). On a 10,000-page catalogue that sees almost nothing. A site's own sitemap lists
every page it wants found, in one or two cheap requests.

Two sources, both official and both cheap:

  robots.txt -> Sitemap: lines -> sitemap XML, following sitemap INDEXES (a sitemap of sitemaps) and
  gzipped .xml.gz members, to a bounded depth.

  Common Crawl's CDX index - a public archive of what the web looked like; asking it for `host/*` returns
  URLs nobody has to fetch at all.

DELIBERATELY NOT BUILT, and this is a decision not an omission: crawl4ai's DomainMapper also offers a
`robots` discovery source that mines `Disallow:` lines as a LIST OF PLACES TO GO - reading the file where
the operator wrote down what they do not want crawled, and using it as a map. Hoola reads robots.txt to
OBEY it (`scrape_respect_robots`, default True). Those two cannot live in one codebase honestly, so only
the `Sitemap:` lines are read here and `Disallow:` is left to the existing gate.

This module is the one part of app/crawl that touches the network, so:
  * every URL goes through a `guard` callable the CALLER injects (Hoola's SSRF guard), so app/crawl never
    has its own idea of what is safe to fetch;
  * caps on everything - sitemaps followed, URLs returned, bytes read, seconds spent;
  * a failure is returned as a reason, never raised into her chat.
"""
from __future__ import annotations

import gzip
import io
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
_SITEMAP_LINE = re.compile(r"^\s*sitemap\s*:\s*(\S+)", re.I | re.M)
_IS_INDEX = re.compile(r"<sitemapindex", re.I)
_LASTMOD = re.compile(r"<lastmod>\s*([^<\s]+)", re.I)

MAX_SITEMAPS = 25             # sitemap documents fetched per run
MAX_URLS = 5_000              # urls returned per run
MAX_BYTES = 8 * 1024 * 1024   # per sitemap document, after decompression
MAX_SECONDS = 45.0
CC_INDEX = "https://index.commoncrawl.org/CC-MAIN-2025-05-index"   # one recent, stable collection


@dataclass
class SeedResult:
    urls: list[str] = field(default_factory=list)
    sources: dict[str, int] = field(default_factory=dict)   # source -> how many it contributed
    sitemaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)          # honest failures, never raised

    @property
    def count(self) -> int:
        return len(self.urls)


def _decompress(body: bytes, url: str) -> str:
    if url.lower().endswith(".gz") or body[:2] == b"\x1f\x8b":
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as g:
                body = g.read(MAX_BYTES)
        except Exception:
            return ""
    try:
        return body[:MAX_BYTES].decode("utf-8", "replace")
    except Exception:
        return ""


async def _get(client, url: str, guard) -> tuple[str, str]:
    """(text, note). Never raises - a seeder that throws would take a crawl down with it."""
    try:
        if guard is not None:
            url = guard(url)
    except Exception as e:
        return "", f"{url}: guard: {str(e)[:90]}"
    try:
        r = await client.get(url, follow_redirects=True, timeout=15)
    except Exception as e:
        return "", f"{url}: {type(e).__name__}"
    if r.status_code >= 400:
        return "", f"{url}: HTTP {r.status_code}"
    return _decompress(r.content, str(r.url)), ""


async def from_sitemaps(start_url: str, client, guard=None, max_urls: int = MAX_URLS,
                        include: str = "", newer_than: str = "") -> SeedResult:
    """robots.txt -> Sitemap: -> sitemap XML, following indexes and .gz, breadth-first and bounded."""
    out = SeedResult()
    t0 = time.monotonic()
    u = urlparse(start_url)
    if u.scheme not in ("http", "https") or not u.hostname:
        out.notes.append("start url is not http(s)")
        return out
    root = f"{u.scheme}://{u.netloc}"

    txt, note = await _get(client, urljoin(root + "/", "robots.txt"), guard)
    if note:
        out.notes.append(f"robots.txt: {note.split(': ',1)[-1]}")
    queue = [m.group(1).strip() for m in _SITEMAP_LINE.finditer(txt or "")]
    if not queue:
        queue = [urljoin(root + "/", "sitemap.xml")]      # the conventional location
        out.notes.append("no Sitemap: line in robots.txt; tried /sitemap.xml")

    seen_maps: set[str] = set()
    while queue and len(out.sitemaps) < MAX_SITEMAPS and len(out.urls) < max_urls:
        if time.monotonic() - t0 > MAX_SECONDS:
            out.notes.append("sitemap walk hit its time cap")
            break
        sm = queue.pop(0)
        if sm in seen_maps:
            continue
        seen_maps.add(sm)
        body, note = await _get(client, sm, guard)
        if note:
            out.notes.append(note)
            continue
        out.sitemaps.append(sm)
        locs = [m.group(1) for m in _LOC.finditer(body)]
        if _IS_INDEX.search(body):
            for child in locs:                            # a sitemap OF sitemaps - nested, so recurse
                if child not in seen_maps:
                    queue.append(child)
            continue
        if newer_than:
            # keep a <url> block only when its lastmod is >= newer_than; blocks without one are kept
            kept = []
            for block in re.split(r"(?i)<url[\s>]", body)[1:]:
                mloc = _LOC.search(block)
                if not mloc:
                    continue
                mlm = _LASTMOD.search(block)
                if mlm and mlm.group(1)[:10] < newer_than[:10]:
                    continue
                kept.append(mloc.group(1))
            locs = kept
        for loc in locs:
            if include and include.lower() not in loc.lower():
                continue
            if loc not in out.urls:
                out.urls.append(loc)
                if len(out.urls) >= max_urls:
                    out.notes.append(f"url cap reached ({max_urls})")
                    break
    out.sources["sitemap"] = len(out.urls)
    return out


async def from_common_crawl(start_url: str, client, guard=None, max_urls: int = 1_000,
                            index: str = CC_INDEX) -> SeedResult:
    """Ask Common Crawl's CDX index what it has seen for this host. Nothing of the site is fetched."""
    import json as _json
    out = SeedResult()
    host = (urlparse(start_url).hostname or "").lower()
    if not host:
        out.notes.append("no host to ask Common Crawl about")
        return out
    q = f"{index}?url={host}/*&output=json&limit={max(1, min(int(max_urls), 5000))}&filter=status:200"
    body, note = await _get(client, q, guard)
    if note:
        out.notes.append(f"common crawl: {note.split(': ', 1)[-1]}")
        return out
    seen: set[str] = set()
    for line in (body or "").splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            rec = _json.loads(line)
        except Exception:
            continue
        url = (rec.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            out.urls.append(url)
            if len(out.urls) >= max_urls:
                break
    out.sources["common_crawl"] = len(out.urls)
    if not out.urls and not out.notes:
        out.notes.append("common crawl has no 200-status records for this host in this collection")
    return out


async def seed(start_url: str, client, guard=None, sources: tuple[str, ...] = ("sitemap",),
               max_urls: int = MAX_URLS, include: str = "", newer_than: str = "") -> SeedResult:
    """Run the chosen sources and merge, keeping first-seen order. `sources`: sitemap, common_crawl."""
    merged = SeedResult()
    for src in sources:
        s = str(src).lower().strip()
        if s == "sitemap":
            r = await from_sitemaps(start_url, client, guard, max_urls=max_urls,
                                    include=include, newer_than=newer_than)
        elif s in ("common_crawl", "cc"):
            r = await from_common_crawl(start_url, client, guard, max_urls=min(max_urls, 1_000))
        else:
            merged.notes.append(f"unknown seed source {src!r}")
            continue
        for u in r.urls:
            if u not in merged.urls:
                if include and include.lower() not in u.lower():
                    continue
                merged.urls.append(u)
                if len(merged.urls) >= max_urls:
                    break
        merged.sitemaps += r.sitemaps
        merged.notes += r.notes
        for k, v in r.sources.items():
            merged.sources[k] = v
        if len(merged.urls) >= max_urls:
            break
    return merged
