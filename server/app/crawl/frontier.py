"""Item 3: best-first crawling with real filters. Hand-built (the port law).

The gap: `crawl_jobs.run_job` keeps a plain FIFO list - `queue.pop(0)` / `queue.append` - so page 19 of a
20-page budget is whatever breadth-first happened to reach, not the most promising link found. And the only
filter is a same-host check plus an optional `include` substring.

This gives the frontier a priority queue, a membership filter that does not grow without bound, five URL
scorers and five URL filters. Pure computation: URLs in, ordered URLs out. No fetching here.

A note on the membership filter: a crawl's `seen` list is a Python list in the checkpoint today, so every
`nxt in seen` is O(n) and the JSON grows with it. `Seen` below is a Bloom filter (bitset + k hashes from one
blake2b digest, no dependency) with the exact set kept alongside while it is small, so a 20-page crawl is
exact and a 10,000-page crawl is bounded. A Bloom filter can say "maybe seen" for a URL never seen - the
cost is one skipped link, never a duplicate fetch, which is the right way round for politeness.
"""
from __future__ import annotations

import hashlib
import heapq
import math
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .bm25 import words


# ---------------------------------------------------------------- membership, bounded
class Seen:
    """Bloom filter + an exact set while it is cheap. `add` returns True when the url is new."""

    def __init__(self, capacity: int = 20_000, error: float = 0.01, exact_upto: int = 2_000) -> None:
        capacity = max(1, int(capacity))
        self.m = max(64, int(-capacity * math.log(max(1e-9, error)) / (math.log(2) ** 2)))
        self.k = max(1, min(8, round((self.m / capacity) * math.log(2))))
        self.bits = bytearray((self.m + 7) // 8)
        self.n = 0
        self.exact: set[str] | None = set()
        self._exact_upto = int(exact_upto)

    def _idx(self, s: str):
        d = hashlib.blake2b(s.encode("utf-8", "replace"), digest_size=16).digest()
        a = int.from_bytes(d[:8], "big")
        b = int.from_bytes(d[8:], "big") | 1
        for i in range(self.k):
            yield (a + i * b) % self.m

    def __contains__(self, s: str) -> bool:
        if self.exact is not None:
            return s in self.exact
        return all(self.bits[i >> 3] & (1 << (i & 7)) for i in self._idx(s))

    def add(self, s: str) -> bool:
        if s in self:
            return False
        for i in self._idx(s):
            self.bits[i >> 3] |= 1 << (i & 7)
        self.n += 1
        if self.exact is not None:
            self.exact.add(s)
            if len(self.exact) > self._exact_upto:
                self.exact = None          # hand over to the bloom filter; memory stops growing
        return True

    def __len__(self) -> int:
        return self.n


# ---------------------------------------------------------------- scorers
@dataclass
class Scored:
    url: str
    score: float
    parts: dict = field(default_factory=dict)


def keyword_relevance(url: str, anchor: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    u = urlparse(url)
    blob = set(words(f"{anchor} {u.path} {u.query}".replace("/", " ").replace("-", " ").replace("_", " ")))
    kw = set(words(" ".join(keywords)))
    return (len(blob & kw) / float(len(kw))) if kw else 0.0


def path_depth(url: str, ideal: int = 2) -> float:
    """Shallow pages are usually indexes, very deep ones usually noise. Peaks at `ideal`."""
    segs = [s for s in urlparse(url).path.split("/") if s]
    d = len(segs)
    return 1.0 / (1.0 + abs(d - max(0, ideal)))


_GOOD_EXT = re.compile(r"\.(?:html?|php|aspx?|jsp)$", re.I)
_BAD_EXT = re.compile(r"\.(?:jpe?g|png|gif|webp|svg|ico|css|js|zip|gz|tar|exe|dmg|mp4|mp3|avi|woff2?|ttf)$", re.I)
_DOC_EXT = re.compile(r"\.(?:pdf|docx?|xlsx?|csv|pptx?)$", re.I)


def content_type(url: str) -> float:
    p = urlparse(url).path
    if _BAD_EXT.search(p):
        return 0.0
    if _DOC_EXT.search(p):
        return 0.6
    if _GOOD_EXT.search(p) or "." not in p.rsplit("/", 1)[-1]:
        return 1.0
    return 0.4


_YEAR = re.compile(r"/(20[0-2]\d|19\d\d)(?:/|-|_|$)")


def freshness(url: str, now_year: int | None = None) -> float:
    """A year in the path is the only date signal a URL reliably carries. No year = neutral 0.5."""
    m = _YEAR.search(urlparse(url).path)
    if not m:
        return 0.5
    try:
        y = int(m.group(1))
    except ValueError:
        return 0.5
    now = now_year or time.gmtime().tm_year
    age = max(0, now - y)
    return max(0.0, min(1.0, 1.0 - age / 12.0))


def novelty(url: str, vocab: set[str]) -> float:
    terms = set(words(urlparse(url).path.replace("/", " ").replace("-", " ").replace("_", " ")))
    return (len(terms - vocab) / float(len(terms))) if terms else 0.0


DEFAULT_WEIGHTS = {"keyword": 0.45, "depth": 0.15, "content_type": 0.20, "freshness": 0.10, "novelty": 0.10}


def score_url(url: str, anchor: str = "", keywords: list[str] | None = None, vocab: set[str] | None = None,
              weights: dict | None = None, ideal_depth: int = 2) -> Scored:
    """One composite 0..1 score, with its parts kept so a card can say WHY a link was chosen."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    parts = {
        "keyword": keyword_relevance(url, anchor, keywords or []),
        "depth": path_depth(url, ideal_depth),
        "content_type": content_type(url),
        "freshness": freshness(url),
        "novelty": novelty(url, vocab or set()),
    }
    tot = sum(w.get(k, 0.0) for k in parts) or 1.0
    s = sum(parts[k] * w.get(k, 0.0) for k in parts) / tot
    # a URL we can never usefully read is out, whatever else it scores
    if parts["content_type"] <= 0.0:
        s = 0.0
    return Scored(url=url, score=round(s, 4), parts={k: round(v, 4) for k, v in parts.items()})


# ---------------------------------------------------------------- filters
@dataclass
class Filters:
    """All optional. `allow`/`deny` are regexes on the whole URL; hosts are matched on the registrable part."""
    same_host_as: str = ""
    allow_hosts: tuple[str, ...] = ()
    deny_hosts: tuple[str, ...] = ()
    allow: str = ""
    deny: str = ""
    max_depth: int = 6
    include: str = ""                 # the v0.486 substring gate, kept so existing jobs behave the same
    skip_extensions: bool = True
    max_query_params: int = 6         # a long query string is usually a filter/sort permutation trap

    def reasons(self, url: str) -> str:
        """'' when the url passes, else a short human reason. One function so the crawl can RECORD why."""
        try:
            u = urlparse(url)
        except Exception:
            return "unparseable"
        if u.scheme not in ("http", "https"):
            return f"scheme {u.scheme or '?'}"
        host = (u.hostname or "").lower()
        if not host:
            return "no host"
        if self.same_host_as:
            want = (urlparse(self.same_host_as).hostname or "").lower()
            if want and host != want and not host.endswith("." + want):
                return f"other host ({host})"
        if self.allow_hosts and not any(host == h or host.endswith("." + h) for h in self.allow_hosts):
            return f"host not allowed ({host})"
        if any(host == h or host.endswith("." + h) for h in self.deny_hosts):
            return f"host denied ({host})"
        if self.skip_extensions and _BAD_EXT.search(u.path):
            return "not a page (asset)"
        segs = [s for s in u.path.split("/") if s]
        if len(segs) > max(0, self.max_depth):
            return f"too deep ({len(segs)})"
        if self.include and self.include.lower() not in url.lower():
            return f"missing include ({self.include!r})"
        if self.allow and not re.search(self.allow, url, re.I):
            return "no allow match"
        if self.deny and re.search(self.deny, url, re.I):
            return "deny match"
        if u.query and len(u.query.split("&")) > max(0, self.max_query_params):
            return "query-param trap"
        return ""

    def ok(self, url: str) -> bool:
        return self.reasons(url) == ""


# ---------------------------------------------------------------- the frontier
class Frontier:
    """Best-first: always hand back the highest-scoring link not yet taken.

    `mode` is "best" (priority), "bfs" (first in, first out) or "dfs" (last in, first out), so the existing
    crawl can keep its exact behaviour by asking for "bfs".
    """

    def __init__(self, keywords: list[str] | None = None, filters: Filters | None = None,
                 mode: str = "best", capacity: int = 20_000, weights: dict | None = None) -> None:
        self.keywords = list(keywords or [])
        self.filters = filters or Filters()
        self.mode = str(mode or "best").lower()
        self.weights = weights
        self.seen = Seen(capacity=capacity)
        self._heap: list[tuple[float, int, str, int]] = []
        self._fifo: list[tuple[str, int]] = []
        self._tick = 0
        self.vocab: set[str] = set()
        self.rejected: dict[str, str] = {}
        self.taken = 0

    def learn(self, text: str) -> None:
        """Feed read page text so `novelty` means something."""
        self.vocab |= set(words(text))

    def push(self, url: str, anchor: str = "", depth: int = 0) -> bool:
        url = (url or "").strip()
        if not url:
            return False
        why = self.filters.reasons(url)
        if why:
            if len(self.rejected) < 500:
                self.rejected[url] = why
            return False
        if not self.seen.add(url):
            return False
        if self.mode == "best":
            s = score_url(url, anchor, self.keywords, self.vocab, self.weights)
            self._tick += 1
            heapq.heappush(self._heap, (-s.score, self._tick, url, depth))
        else:
            self._fifo.append((url, depth))
        return True

    def push_many(self, links: list[dict], depth: int = 0) -> int:
        return sum(1 for ln in links
                   if self.push((ln.get("url") or ""), ln.get("text") or "", depth))

    def pop(self) -> tuple[str, int] | None:
        if self.mode == "best":
            if not self._heap:
                return None
            _, _, url, depth = heapq.heappop(self._heap)
            self.taken += 1
            return url, depth
        if not self._fifo:
            return None
        url, depth = self._fifo.pop(0) if self.mode == "bfs" else self._fifo.pop()
        self.taken += 1
        return url, depth

    def peek_scores(self, n: int = 5) -> list[Scored]:
        """The next n, with their parts - for the card, so she can see what it is about to read."""
        out = []
        for neg, _, url, _ in heapq.nsmallest(n, self._heap) if self.mode == "best" else []:
            out.append(score_url(url, "", self.keywords, self.vocab, self.weights))
        return out

    def __len__(self) -> int:
        return len(self._heap) if self.mode == "best" else len(self._fifo)
