"""Item 8a: proxy rotation as POLICY. Hand-built (the port law).

Pure computation: this module decides WHICH proxy a fetch should use next. It never opens a connection -
the caller hands the chosen value to whichever fetcher it is using, so there is one place that knows the
rotation rules and no second idea of how to fetch.

Hoola's scrape lane has no proxy support at all today (only `browser_upstream_proxy`, v0.89, a single
fixed office proxy for the browser worker). What this adds:

  * round-robin across a list, with a DIRECT sentinel meaning "no proxy this time" so a list can mix her
    own egress with proxied egress;
  * SESSION-STICKY leases, because a multi-step flow that changes IP between steps logs itself out;
  * failure accounting - a proxy that keeps failing is rested rather than retried for ever;
  * secrets never logged: `safe()` is the only representation that may be printed, and a test pins that a
    password never appears in it.

NOT built, deliberately: minting rotating residential proxies from a commercial provider's API. crawl4ai
has `set_nstproxy(token, ...)`, which turns a block into "buy your way through". Whether Hoola ever pays a
residential-proxy provider to defeat a site that said no is the owner's commercial and ethical call, not a
default this file should quietly make for her.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

DIRECT = "DIRECT"          # the sentinel: use this server's own egress for this fetch
_SECRET = re.compile(r"(?<=//)([^:/@]+):([^@/]+)(?=@)")


@dataclass
class Proxy:
    url: str                        # http://user:pass@host:port, or DIRECT
    label: str = ""
    fails: int = 0
    last_fail: float = 0.0
    uses: int = 0

    @property
    def is_direct(self) -> bool:
        return self.url.strip().upper() == DIRECT

    def safe(self) -> str:
        """The ONLY form that may be logged or shown. Credentials are replaced, never shortened."""
        if self.is_direct:
            return DIRECT
        return _SECRET.sub(lambda m: f"{m.group(1)}:***", self.url)

    def __str__(self) -> str:        # so an accidental f-string cannot leak the password
        return self.safe()


def parse(spec: str) -> Proxy:
    """Accepts a URL, the `ip:port:user:pass` shorthand, or DIRECT."""
    s = (spec or "").strip()
    if not s or s.upper() == DIRECT:
        return Proxy(url=DIRECT)
    if "://" in s:
        u = urlparse(s)
        if not u.hostname:
            raise ValueError(f"proxy has no host: {spec!r}")
        return Proxy(url=s, label=f"{u.hostname}:{u.port or ''}")
    bits = s.split(":")
    if len(bits) == 2:
        return Proxy(url=f"http://{bits[0]}:{bits[1]}", label=f"{bits[0]}:{bits[1]}")
    if len(bits) == 4:
        host, port, user, pw = bits
        return Proxy(url=f"http://{user}:{pw}@{host}:{port}", label=f"{host}:{port}")
    raise ValueError(f"cannot read proxy {spec!r}; use a URL, ip:port, ip:port:user:pass or DIRECT")


class Rotation:
    """Round-robin with sticky sessions and failure resting."""

    def __init__(self, specs: list[str] | None = None, max_fails: int = 3, rest_s: float = 300.0,
                 lease_s: float = 600.0) -> None:
        self.pool: list[Proxy] = [parse(s) for s in (specs or [])] or [Proxy(url=DIRECT)]
        self.max_fails, self.rest_s, self.lease_s = max_fails, float(rest_s), float(lease_s)
        self._i = 0
        self._leases: dict[str, tuple[Proxy, float]] = {}

    # ---- availability
    def _rested(self, p: Proxy, now: float) -> bool:
        return p.fails < self.max_fails or (now - p.last_fail) > self.rest_s

    def available(self, now: float | None = None) -> list[Proxy]:
        now = now or time.monotonic()
        return [p for p in self.pool if self._rested(p, now)]

    # ---- choosing
    def next(self, session: str = "", now: float | None = None) -> Proxy:
        """The proxy to use. With a `session`, the same one comes back until its lease expires - a flow
        that changes IP mid-way logs itself out, which looks exactly like being blocked."""
        now = now or time.monotonic()
        if session:
            got = self._leases.get(session)
            if got and (now - got[1]) < self.lease_s and self._rested(got[0], now):
                got[0].uses += 1
                return got[0]
        pool = self.available(now)
        if not pool:                      # everything is resting: fall back to her own egress, honestly
            d = next((p for p in self.pool if p.is_direct), None)
            return d or self.pool[0]
        p = pool[self._i % len(pool)]
        self._i = (self._i + 1) % max(1, len(pool))
        p.uses += 1
        if session:
            self._leases[session] = (p, now)
        return p

    def release(self, session: str) -> None:
        self._leases.pop(session, None)

    def failed(self, p: Proxy, now: float | None = None) -> None:
        p.fails += 1
        p.last_fail = now or time.monotonic()
        for s, (lp, _) in list(self._leases.items()):
            if lp is p and p.fails >= self.max_fails:
                del self._leases[s]       # a dead proxy must not keep a session pinned to it

    def ok(self, p: Proxy) -> None:
        p.fails = 0

    def sweep(self, now: float | None = None) -> int:
        now = now or time.monotonic()
        dead = [s for s, (_, t) in self._leases.items() if (now - t) >= self.lease_s]
        for s in dead:
            del self._leases[s]
        return len(dead)

    def report(self) -> list[dict]:
        """Safe to log and safe to show her: no credentials, ever."""
        return [{"proxy": p.safe(), "label": p.label, "uses": p.uses, "fails": p.fails,
                 "resting": p.fails >= self.max_fails} for p in self.pool]
