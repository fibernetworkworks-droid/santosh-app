"""Real logos for plugins and MCP servers, fetched from each brand's OWN website (its apple-touch-icon / favicon) or,
for directory MCP servers, the publisher's GitHub avatar. They are fetched once on the server, turned into a
128 px PNG and kept on disk, so phones load them fast from Hoola and never call third parties themselves.

Logos are only ever looked up for things in Hoola's own lists (a pack id, a featured connector, a directory entry,
an MCP server the owner added); the server never fetches an address a request makes up. Every request goes to a
public https address only (checked before each hop, redirects included). Generic plugins (shop templates, Hoola's
own skills) have no brand: the app draws a category icon for them.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

log = logging.getLogger("santosh.logos")

HERE = Path(__file__).parent
DOMAINS_FILE = HERE / "logo_domains.json"
CACHE_DIR = Path("data") / "logos"
SIZE = 128
MAX_BYTES = 600_000
MISS_RETRY_S = 3 * 24 * 3600
_DOMAIN = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
_OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_domains: dict[str, str] | None = None


# ----------------------------------------------------------------------------- what has a logo
def domains() -> dict[str, str]:
    """pack id / 'feat:<id>' -> the brand's official domain (researched list; null = no known site)."""
    global _domains
    if _domains is None:
        try:
            raw = json.loads(DOMAINS_FILE.read_text())
        except (OSError, ValueError):
            raw = {}
        _domains = {k: v.lower().removeprefix("www.") for k, v in raw.items()
                    if isinstance(v, str) and not k.startswith("_") and _DOMAIN.match(v.lower().removeprefix("www."))}
    return _domains


def pack_logo(pack_id: str) -> str | None:
    """App path of a pack's logo, or None when the pack has no brand (the app shows a category icon)."""
    return f"/api/logo/pack/{pack_id}" if pack_id in domains() else None


def featured_logo(fid: str) -> str | None:
    return f"/api/logo/feat/{fid}" if f"feat:{fid}" in domains() else None


def github_owner(url: str | None) -> str | None:
    if not url:
        return None
    u = urlparse(url)
    if u.hostname not in ("github.com", "www.github.com"):
        return None
    parts = [p for p in u.path.split("/") if p]
    return parts[0] if parts and _OWNER.match(parts[0]) else None


def directory_logo(github_url: str | None) -> str | None:
    owner = github_owner(github_url)
    return f"/api/logo/gh/{owner}" if owner else None


def custom_logo(row) -> str | None:
    """An MCP server the owner added: its directory publisher's avatar, else the server host's own site."""
    from . import directory
    entry = directory.get(row.directory_ref) if row.directory_ref and not row.directory_ref.startswith("featured:") else None
    if row.directory_ref.startswith("featured:"):
        return featured_logo(row.directory_ref.split(":", 1)[1])
    if entry and github_owner(entry.get("l")):
        return directory_logo(entry.get("l"))
    return f"/api/logo/mcp/{row.id}"


def _registrable(host: str) -> str:
    parts = host.lower().removeprefix("www.").split(".")
    keep = 3 if len(parts) >= 3 and parts[-2] in ("co", "gov", "org", "net", "ac", "nic", "com", "edu", "res") else 2
    return ".".join(parts[-keep:])


def resolve(kind: str, key: str) -> tuple[str, str] | None:
    """('domain', d) or ('url', u) for a logo the server may fetch, or None."""
    if kind == "pack":
        d = domains().get(key)
        return ("domain", d) if d else None
    if kind == "feat":
        d = domains().get("feat:" + key)
        return ("domain", d) if d else None
    if kind == "tv":
        from ..tv import catalog
        c = catalog.get(key)
        src = (c or {}).get("logo_src") or ""
        return ("url", src) if src.startswith("https://") else None
    if kind == "gh":
        return ("url", f"https://github.com/{key}.png?size=128") if _OWNER.match(key) else None
    if kind == "mcp":
        from .db import CustomMcp, session_factory
        s = session_factory()
        try:
            row = s.get(CustomMcp, key)
            host = urlparse(row.url).hostname if row is not None and row.status == "active" else None
        finally:
            s.close()
        if host:
            d = _registrable(host)
            return ("domain", d) if _DOMAIN.match(d) else None
    return None


# ----------------------------------------------------------------------------- fetching
def _client():
    import httpx

    def guard(req: httpx.Request) -> None:
        from .custom_mcp import check_url
        check_url(str(req.url))   # https and a public address only, at every hop
    return httpx.Client(timeout=6, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (HoolaLogo/1.0)"},
                        event_hooks={"request": [guard]})


def _png(data: bytes) -> tuple[bytes, int] | None:
    """Any image -> square 128 px PNG (transparent padding). Returns (png, original width) or None."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data))
        if getattr(im, "n_frames", 1) > 1 or im.format == "ICO":
            # ICO / multi-size: take the largest frame
            best = None
            for i in range(getattr(im, "n_frames", 1)):
                im.seek(i)
                if best is None or im.size[0] > best.size[0]:
                    best = im.copy()
            im = best
        im = im.convert("RGBA")
    except Exception:
        return None
    w, h = im.size
    if w < 16 or h < 16:
        return None
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2))
    canvas = canvas.resize((SIZE, SIZE), Image.LANCZOS)
    out = io.BytesIO()
    canvas.save(out, "PNG", optimize=True)
    return out.getvalue(), w


def _get(client, url: str) -> bytes | None:
    try:
        r = client.get(url)
    except Exception:
        return None
    if r.status_code != 200 or not r.content or len(r.content) > MAX_BYTES:
        return None
    if "html" in r.headers.get("content-type", ""):
        return None
    return r.content


def _icon_links(client, domain: str) -> list[str]:
    """Icons the homepage itself declares (largest first)."""
    try:
        r = client.get(f"https://{domain}/")
    except Exception:
        return []
    if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
        return []
    found = []
    for tag in re.findall(r"<link\b[^>]*>", r.text[:200_000], re.I):
        rel = re.search(r'rel=["\']([^"\']+)["\']', tag, re.I)
        href = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
        if not rel or not href or "icon" not in rel.group(1).lower():
            continue
        size = re.search(r'sizes=["\'](\d+)x', tag, re.I)
        url = str(r.url.join(href.group(1)))
        if url.startswith("https://"):
            found.append((int(size.group(1)) if size else (180 if "apple" in rel.group(1).lower() else 32), url))
    return [u for _, u in sorted(found, reverse=True)]


def fetch(kind: str, target: str, client=None) -> bytes | None:
    """The best real logo for a domain (or a direct url), as a 128 px PNG."""
    own = client is None
    client = client or _client()
    try:
        if kind == "url":
            data = _get(client, target)
            got = _png(data) if data else None
            return got[0] if got else None
        best: tuple[bytes, int] | None = None
        hosts = [target] if target.count(".") >= 2 else [target, "www." + target]
        tried: set[str] = set()
        candidates = []
        for h in hosts:
            candidates += [f"https://{h}/apple-touch-icon.png", f"https://{h}/apple-touch-icon-precomposed.png"]
        for h in hosts:
            candidates += _icon_links(client, h)
        for h in hosts:
            candidates.append(f"https://{h}/favicon.ico")
        for url in candidates:
            if url in tried:
                continue
            tried.add(url)
            data = _get(client, url)
            got = _png(data) if data else None
            if got and (best is None or got[1] > best[1]):
                best = got
            if best and best[1] >= 120:
                break
        return best[0] if best else None
    finally:
        if own:
            client.close()


_warming = False


def warm_in_background(pause_s: float = 0.4) -> None:
    """After start-up: fetch every listed logo once (one at a time), so phones never wait for the first fetch."""
    global _warming
    if _warming:
        return
    _warming = True

    def go():
        time.sleep(20)   # let the server settle first
        n = 0
        for k in list(domains()):
            kind, key = ("feat", k[5:]) if k.startswith("feat:") else ("pack", k)
            try:
                if logo(kind, key):
                    n += 1
            except Exception:
                log.exception("logo %s failed", k)
            time.sleep(pause_s)
        log.info("logos ready: %s of %s", n, len(domains()))
    threading.Thread(target=go, daemon=True, name="logo-warm").start()


def logo(kind: str, key: str) -> bytes | None:
    """Cached logo PNG, fetched on first use. None = this one has no logo we can show."""
    target = resolve(kind, key)
    if target is None:
        return None
    name = hashlib.sha256(f"{kind}:{key}:{target[1]}".encode()).hexdigest()[:24]
    png, miss = CACHE_DIR / f"{name}.png", CACHE_DIR / f"{name}.miss"
    if png.exists():
        return png.read_bytes()
    if miss.exists() and time.time() - miss.stat().st_mtime < MISS_RETRY_S:
        return None
    with _locks_guard:
        lock = _locks.setdefault(name, threading.Lock())
    with lock:
        if png.exists():
            return png.read_bytes()
        data = fetch(*target)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if data:
            png.write_bytes(data)
            miss.unlink(missing_ok=True)
        else:
            miss.touch()
            log.info("no logo for %s:%s (%s)", kind, key, target[1])
        return data
