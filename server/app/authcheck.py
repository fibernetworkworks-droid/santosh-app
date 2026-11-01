"""v0.391 KHULA DARWAZA - is the server's own front door locked? (owner: "GO A")

`main._resolve_tenant` / `require_key` treat a request with NO login as the owner whenever API_KEY is empty (a convenience
from the single-user days). On a public server that means anyone who finds the address can act as the owner. This module
only REPORTS - it never changes who gets in, so nothing on her phone or console can break because of it:
- warn_if_open(): one loud log line at startup when API_KEY is empty;
- `python -m app.authcheck [--url http://127.0.0.1:8077]`: says whether API_KEY is set (never its value) and asks the
  RUNNING server for /api/me with no login - 401 = locked, 200 = OPEN. vps-ops job `auth_check`."""
from __future__ import annotations

import logging
import sys

log = logging.getLogger("hoola.authcheck")

OPEN_LINE = ("API_KEY is EMPTY: a request with no login is treated as the OWNER. Set API_KEY in the server .env "
             "(a long random value) and restart - the phone and console sign in with their own login and keep working.")


def key_set() -> bool:
    from .config import get_settings
    return bool((get_settings().api_key or "").strip())


def warn_if_open() -> bool:
    """Log once at startup; True when the door is open."""
    if key_set():
        return False
    log.warning(OPEN_LINE)
    return True


def probe(url: str) -> tuple[int, str]:
    """Ask the running server for /api/me with NO login. (status, verdict)"""
    import httpx
    try:
        r = httpx.get(url.rstrip("/") + "/api/me", timeout=10)
    except Exception as e:  # noqa: BLE001
        return 0, f"could not reach {url}: {str(e)[:120]}"
    if r.status_code == 401:
        return 401, "LOCKED - a request with no login is refused (good)"
    if r.status_code == 200:
        return 200, "OPEN - a request with no login got the owner's /api/me. Set API_KEY in .env and restart."
    return r.status_code, f"unexpected answer {r.status_code}"


def lines(url: str = "") -> list[str]:
    out = [f"API_KEY in this server's settings: {'set' if key_set() else 'EMPTY'}"]
    if url:
        code, verdict = probe(url)
        out.append(f"Live check {url}/api/me with no login: {code} -> {verdict}")
    if not key_set():
        out.append(OPEN_LINE)
    return out


def main(argv: list[str]) -> int:
    url = argv[argv.index("--url") + 1] if "--url" in argv and len(argv) > argv.index("--url") + 1 else ""
    print("\n".join(lines(url)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
