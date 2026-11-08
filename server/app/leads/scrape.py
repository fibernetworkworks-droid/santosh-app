"""v0.543.0 P3 THE SCRAPE LANE - the fetch boundaries (the reuse law: nothing new is built that the house has).

The runner in service.py never touches the network itself - these four boundaries stand between it and the
world, exactly the way enrich.py stood between the P2 pass and its sites (tests fake THESE, zero network):

  GUARD   `scrape_tools._guard_url` - the SSRF gate (public http(s) hosts only) before anything leaves.
  FETCH   `scrape_tools._fetch`     - the same curl_cffi (TLS-impersonated, no browser) fetcher the whole
          scrape stack uses, proxy-policy aware. NO second fetch client is written here; the leadscard
          guard `scrape_uses_existing_stack` reads this module's source to prove it.
  ROBOTS  the amended CLAUDE.md rule (this commit) says: "robots.txt obeyed on every non-Google host". So
          the Google lane rides the owner's explicit ask of 5 Nov 2026 (the plan states the ToS reality
          once, plainly), and EVERY non-Google host this lane ever touches goes through the existing
          `_robots_allowed` gate, fail-closed in spirit: an unknown host still gets its robots read first.
  POLITE  per-host 1 request/second (GOOGLE_MIN_INTERVAL) and the concurrency ceiling named (MAX_CONCURRENCY
          = 2, plan 5.6). P3 runs ONE host, so the politeness sleep is what actually paces the run - the
          constant names the ceiling a second host would ride.

A block page / CAPTCHA wall is NOT muscle-able: the runner sees `crawl.blocked.why_blocked`'s answer and
ABORTS the run with the wall named (rules.NEVER; the v0.78 one-word CAPTCHA rule is never extended to
unattended runs). No proxy minting, no rotation policy of our own - if SHE supplies proxies in .env, the
existing `_fetch` policy path already rotates them.
"""
from __future__ import annotations

import time

PARSER_SCRAPE = "v0.691.0-gm1"    # the scrape lane's reader version (rows carry it as parser_version)

GOOGLE_MIN_INTERVAL = 1.0         # >= 1s between fetches to the same host (plan 5.6 politeness cap)
MAX_CONCURRENCY = 2               # the named ceiling (plan 5.6); one host in P3, so politeness paces the run
FETCH_TIMEOUT = 25
_GOOGLE_SUFFIX = ".google.com"


def _is_google_host(url: str) -> bool:
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower()
    return host == "google.com" or host.endswith(_GOOGLE_SUFFIX)


_LAST_HIT: dict[str, float] = {}


def _polite(host: str) -> None:
    """Per-host 1 request/second: the same host never sees two fetches inside GOOGLE_MIN_INTERVAL (the
    enrich pass's _polite, same shape - one dict of last hits, one monotonic wait)."""
    wait = GOOGLE_MIN_INTERVAL - (time.monotonic() - _LAST_HIT.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _LAST_HIT[host] = time.monotonic()


def _robots_ok(url: str) -> bool:
    """robots.txt gate, per the AMENDED rule: obeyed on every non-Google host. Google hosts return True here
    and the amendment in CLAUDE.md (this commit) is where that exception is written down; any non-Google
    host the lane ever meets goes through the existing scrape_tools gate."""
    if _is_google_host(url):
        return True                                # owner's explicit ask 5 Nov 2026; CLAUDE.md rule text says so
    from ..agent.scrape_tools import _robots_allowed
    return _robots_allowed(url)


def _get(url: str, tenant_id: str):
    """One public page through the EXISTING scrape stack (SSRF guard + curl_cffi + proxy policy)."""
    from ..agent.scrape_tools import _fetch, _guard_url
    return _fetch(_guard_url(url), tenant_id, timeout=FETCH_TIMEOUT)
