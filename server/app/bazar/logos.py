"""Real logos for plugins and MCP servers, fetched from each brand's OWN website (its apple-touch-icon / favicon) or,
for directory MCP servers, the brand site / listing picture / GitHub organisation, else a drawn HD tile (so every
directory server has a logo). They are fetched once on the server, turned into a
256 px PNG and kept on disk, so phones load them fast from Hoola and never call third parties themselves.

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
SIZE = 256          # HD: crisp at 3x on a 64 dp tile
MAX_BYTES = 1_500_000
VERSION = "2"       # bump to re-fetch every cached logo (and phones load the new path)
GOOD_PX = 180       # an icon this big needs no other source
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
    return f"/api/logo/pack/{pack_id}?v={VERSION}" if pack_id in domains() else None


def featured_logo(fid: str) -> str | None:
    return f"/api/logo/feat/{fid}?v={VERSION}" if f"feat:{fid}" in domains() else None


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
    return f"/api/logo/gh/{owner}?v={VERSION}" if owner else None


def composio_logo(slug: str) -> str:
    """v0.298 every Composio app gets a tile: its own logo, else its website's icon, else a drawn HD tile."""
    return f"/api/logo/cmp/{slug}?v={VERSION}"


def custom_logo(row) -> str | None:
    """An MCP server the owner added: its directory publisher's avatar, else the server host's own site."""
    from . import directory
    entry = directory.get(row.directory_ref) if row.directory_ref and not row.directory_ref.startswith("featured:") else None
    if row.directory_ref.startswith("featured:"):
        return featured_logo(row.directory_ref.split(":", 1)[1])
    if entry and entry.get("id"):
        return f"/api/logo/dir/{entry['id']}?v={directory.LOGO_VERSION}"
    if entry and github_owner(entry.get("l")):
        return directory_logo(entry.get("l"))
    return f"/api/logo/mcp/{row.id}?v={VERSION}"


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
        return ("url", f"https://github.com/{key}.png?size=256") if _OWNER.match(key) else None
    if kind == "dir":
        from . import directory
        return ("dir", key) if directory.logo_sources(key) is not None else None
    if kind == "cmp":
        from . import composio
        return ("cmp", key) if key in composio.catalog() else None
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
    # a normal browser's headers: many Indian brand sites (behind Akamai / Cloudflare) refuse bot-looking requests
    return httpx.Client(timeout=8, follow_redirects=True, event_hooks={"request": [guard]}, headers={
        "User-Agent": ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/129.0 Mobile Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/png,image/*;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8"})


def _svg_png(data: bytes) -> bytes | None:
    """v0.298 an SVG logo (Composio's are SVG) -> a 512 px PNG. resvg-py is optional: without it SVGs are skipped and
    the next source is used."""
    head = data[:1200].lstrip().lower()
    if not (head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head) or b"<svg" in head[:300]):
        return None
    try:
        import resvg_py
    except ImportError:
        return None
    try:
        return bytes(resvg_py.svg_to_bytes(svg_string=data.decode("utf-8", "ignore"), width=512, height=512))
    except Exception:
        return None


def _png(data: bytes) -> tuple[bytes, int] | None:
    """Any image -> square 128 px PNG (transparent padding). Returns (png, original width) or None."""
    from PIL import Image
    svg = _svg_png(data)
    if svg:
        data = svg
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
    box = im.getchannel("A").getbbox()            # drop empty transparent margins so the mark fills the tile
    if box and (box[2] - box[0]) >= 12 and (box[3] - box[1]) >= 12:
        im = im.crop(box)
    cw, ch = im.size
    side = int(max(cw, ch) * 1.06)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - cw) // 2, (side - ch) // 2))
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
    if "html" in r.headers.get("content-type", "") and b"<svg" not in r.content[:400].lower():
        return None
    return r.content


def _manifest_icons(client, manifest_url: str) -> list[tuple[int, str]]:
    """Icons from the site's web app manifest (usually 192 and 512 px: the sharpest the brand publishes)."""
    try:
        r = client.get(manifest_url)
        if r.status_code != 200 or len(r.content) > 300_000:
            return []
        data = r.json()
    except Exception:
        return []
    out = []
    for ic in (data.get("icons") or [])[:20]:
        if not isinstance(ic, dict) or not ic.get("src"):
            continue
        if "svg" in str(ic.get("type") or "") or str(ic["src"]).endswith(".svg"):
            continue
        size = max([int(x) for x in re.findall(r"(\d+)x\d+", str(ic.get("sizes") or ""))] or [0])
        url = str(r.url.join(str(ic["src"])))
        if url.startswith("https://"):
            out.append((size or 192, url))
    return out


def _icon_links(client, domain: str) -> list[str]:
    """Icons the homepage itself declares, manifest icons included (largest first)."""
    try:
        r = client.get(f"https://{domain}/")
    except Exception:
        return []
    if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
        return []
    found = []
    for tag in re.findall(r"<link\b[^>]*>", r.text[:300_000], re.I):
        rel = re.search(r'rel=["\']([^"\']+)["\']', tag, re.I)
        href = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
        if rel and href and rel.group(1).lower().strip() == "manifest":
            found += _manifest_icons(client, str(r.url.join(href.group(1))))
            break
    for tag in re.findall(r"<link\b[^>]*>", r.text[:200_000], re.I):
        rel = re.search(r'rel=["\']([^"\']+)["\']', tag, re.I)
        href = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
        if not rel or not href or "icon" not in rel.group(1).lower():
            continue
        if href.group(1).lower().endswith(".svg"):
            continue
        size = re.search(r'sizes=["\'](\d+)x', tag, re.I)
        url = str(r.url.join(href.group(1)))
        if url.startswith("https://"):
            found.append((int(size.group(1)) if size else (180 if "apple" in rel.group(1).lower() else 32), url))
    return [u for _, u in sorted(found, reverse=True)]


def fetch(kind: str, target: str, client=None) -> bytes | None:
    """The best real logo for a domain (or a direct url), as a 256 px PNG. A directory server ('dir') always gets one:
    its brand site, the listing's picture, its GitHub organisation, else a drawn HD tile."""
    if kind == "dir":
        return dir_logo(target, client)
    if kind == "cmp":
        return cmp_logo(target, client)
    got = fetch_sized(kind, target, client)
    return got[0] if got else None


DIR_MIN_PX = 96      # smaller than this looks blurry on a 64 dp tile: use the next source
DIR_BUDGET_S = 12.0  # then the drawn tile now, and the real sources again after MISS_RETRY_S


def _flat(png: bytes) -> bool:
    """GitHub's default avatar (identicon: a 5x5 pattern in one colour on #F0F0F0 grey) is not a logo."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(png)).convert("RGB").resize((64, 64), Image.NEAREST)
    except Exception:
        return True
    colors = im.getcolors(64 * 64) or []
    grey = sum(n for n, c in colors if all(abs(v - 240) <= 4 for v in c))
    buckets: dict[tuple, int] = {}
    for n, c in colors:                              # near colours together (resizing leaves soft edges)
        k = tuple(v // 48 for v in c)
        buckets[k] = buckets.get(k, 0) + n
    big = [k for k, n in buckets.items() if n > 80]  # colour groups covering more than 2% of the picture
    return grey > 64 * 64 * 0.4 and len(big) <= 4


def dir_logo(eid: str, client=None) -> bytes:
    from . import directory
    own = client is None
    client = client or _client()
    try:
        deadline = time.time() + DIR_BUDGET_S          # a phone is waiting: never hang on a slow site
        tries: list[str] = []
        for kind, target in directory.logo_sources(eid) or []:
            if kind == "gh":
                if _OWNER.match(target):
                    tries.append(f"https://github.com/{target}.png?size=256")
            elif kind == "domain":     # the icon Google indexes for the brand (256 px), then the site's own touch icon
                tries += [f"https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL"
                          f"&url=https://{target}&size=256", f"https://{target}/apple-touch-icon.png",
                          f"https://www.{target}/apple-touch-icon.png"]
            else:
                tries.append(target)
        for url in tries:
            if time.time() > deadline:
                break
            try:
                got = fetch_sized("url", url, client)
            except Exception:
                got = None
            if got and got[1] >= DIR_MIN_PX and not (url.startswith("https://github.com/") and _flat(got[0])):
                return got[0]
    finally:
        if own:
            client.close()
    title, field = directory.monogram_of(eid)
    return monogram(title, field)


def cmp_sources(slug: str) -> list[str]:
    """Where a Composio app's logo may come from, all from Composio's own catalogue: its logo address, then the icon of
    the app's own website (app_url), the way Google indexes it, then the site's touch icon."""
    from . import composio
    a = composio.catalog().get(slug) or {}
    out = []
    if str(a.get("logo") or "").startswith("https://"):
        out.append(a["logo"])
    host = urlparse(str(a.get("app_url") or "")).hostname or ""
    d = _registrable(host) if host else ""
    if d and _DOMAIN.match(d):
        out += [f"https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL"
                f"&url=https://{d}&size=256", f"https://{d}/apple-touch-icon.png", f"https://www.{d}/apple-touch-icon.png"]
    return out


def cmp_logo(slug: str, client=None) -> bytes:
    from . import composio
    own = client is None
    client = client or _client()
    try:
        deadline = time.time() + DIR_BUDGET_S          # a phone is waiting: never hang on a slow site
        for url in cmp_sources(slug):
            if time.time() > deadline:
                break
            try:
                got = fetch_sized("url", url, client)
            except Exception:
                got = None
            if got and got[1] >= 48:
                return got[0]
    finally:
        if own:
            client.close()
    return monogram(*cmp_monogram(slug))


def cmp_monogram(slug: str) -> tuple[str, str]:
    from . import composio
    a = composio.catalog().get(slug) or {}
    return str(a.get("name") or slug), CMP_FIELD.get((a.get("cats") or [""])[0].lower(), "")


CMP_FIELD = {"communication": "Communication", "productivity": "Productivity", "crm": "Business & CRM",
             "developer tools": "Developer Tools", "marketing": "Marketing & SEO", "finance": "Finance & Payments",
             "accounting": "Finance & Payments", "ai": "AI & Agents", "analytics": "Data & Analytics",
             "design": "Design & Media", "e-commerce": "E-commerce", "ecommerce": "E-commerce", "security": "Security",
             "social media": "Social Media", "storage": "Files & Documents", "documents": "Files & Documents",
             "education": "Education & Research", "health": "Health & Science", "travel": "Maps & Travel"}


CAT_COLORS = {  # two-stop gradients per category (deep -> bright), so a drawn tile still says what kind of server it is
    "Developer Tools": ((30, 41, 99), (79, 70, 229)), "AI & Agents": ((88, 28, 135), (192, 38, 211)),
    "Search & Web": ((12, 74, 110), (14, 165, 233)), "Browser Automation": ((15, 76, 92), (6, 182, 212)),
    "Databases": ((20, 83, 45), (34, 197, 94)), "Data & Analytics": ((30, 58, 138), (59, 130, 246)),
    "Cloud & DevOps": ((12, 74, 110), (56, 189, 248)), "Security": ((127, 29, 29), (239, 68, 68)),
    "Communication": ((6, 95, 70), (16, 185, 129)), "Productivity": ((124, 45, 18), (249, 115, 22)),
    "Knowledge & Memory": ((76, 29, 149), (139, 92, 246)), "Finance & Payments": ((20, 83, 45), (132, 204, 22)),
    "Crypto & Web3": ((120, 53, 15), (245, 158, 11)), "Marketing & SEO": ((131, 24, 67), (236, 72, 153)),
    "Social Media": ((30, 64, 175), (96, 165, 250)), "E-commerce": ((154, 52, 18), (251, 146, 60)),
    "Design & Media": ((112, 26, 117), (217, 70, 239)), "Files & Documents": ((51, 65, 85), (100, 116, 139)),
    "Maps & Travel": ((19, 78, 74), (20, 184, 166)), "Health & Science": ((22, 101, 52), (74, 222, 128)),
    "Education & Research": ((30, 27, 75), (99, 102, 241)), "Gaming": ((76, 5, 25), (225, 29, 72)),
    "IoT & Hardware": ((54, 83, 20), (163, 230, 53)), "Business & CRM": ((23, 37, 84), (37, 99, 235)),
}
FONT = HERE.parent / "fonts" / "Poppins-Bold.ttf"   # OFL, Latin subset (app/fonts/OFL-Poppins.txt)


def initials(title: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9]+", title or "") if w.lower() not in ("the", "and", "of", "for", "mcp")]
    if not words:
        return "M"
    if len(words) == 1:
        w = words[0]
        caps = [c for c in w[1:] if c.isupper()]      # "GitHub" -> GH, "OpenAI" -> OA
        return (w[0] + caps[0]).upper() if caps else w[0].upper()
    return (words[0][0] + words[1][0]).upper()


def monogram(title: str, field: str = "") -> bytes:
    """A clean HD tile (256 px): rounded square, category gradient tuned by the name, 1-2 letters."""
    from PIL import Image, ImageDraw, ImageFont
    a, b = CAT_COLORS.get(field, ((31, 41, 55), (75, 85, 99)))
    h = int(hashlib.sha1((title or "").encode()).hexdigest()[:2], 16) / 255 - 0.5   # small shift so tiles differ
    a = tuple(max(0, min(255, int(x + h * 30))) for x in a)
    b = tuple(max(0, min(255, int(x - h * 30))) for x in b)
    big = SIZE * 2
    grad = Image.new("RGBA", (big, big))
    px = grad.load()
    for y in range(big):
        for x in range(0, big, 4):
            t = (x + y) / (2 * big)
            c = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)
            for k in range(4):
                px[x + k, y] = c
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.23), fill=255)
    tile = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    tile.paste(grad, (0, 0), mask)
    glow = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((-big * 0.3, -big * 0.55, big * 1.0, big * 0.45), fill=(255, 255, 255, 34))
    tile = Image.alpha_composite(tile, Image.composite(glow, Image.new("RGBA", (big, big), (0, 0, 0, 0)), mask))
    text = initials(title)
    try:
        font = ImageFont.truetype(str(FONT), int(big * (0.42 if len(text) > 1 else 0.5)))
    except OSError:
        font = ImageFont.load_default()
    d = ImageDraw.Draw(tile)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
    pos = ((big - (x1 - x0)) / 2 - x0, (big - (y1 - y0)) / 2 - y0)
    d.text((pos[0], pos[1] + big * 0.012), text, font=font, fill=(0, 0, 0, 60))
    d.text(pos, text, font=font, fill=(255, 255, 255, 255))
    out = io.BytesIO()
    tile.resize((SIZE, SIZE), Image.LANCZOS).save(out, "PNG", optimize=True)
    return out.getvalue()


def fetch_sized(kind: str, target: str, client=None) -> tuple[bytes, int] | None:
    """(256 px PNG, the source's own width) of the best logo for a domain or a direct url."""
    own = client is None
    client = client or _client()
    try:
        if kind == "url":
            data = _get(client, target)
            return _png(data) if data else None
        best: tuple[bytes, int] | None = None
        hosts = [target] if target.count(".") >= 2 else [target, "www." + target]
        tried: set[str] = set()
        candidates = []
        for h in hosts:                 # what the homepage declares first: manifest icons are 192-512 px
            candidates += _icon_links(client, h)
        for h in hosts:
            candidates += [f"https://{h}/apple-touch-icon.png", f"https://{h}/apple-touch-icon-precomposed.png"]
        for h in hosts:
            candidates.append(f"https://{h}/favicon.ico")
        # when the brand's site blocks servers or only has a tiny favicon: the same icon as Google / DuckDuckGo index it
        candidates += [f"https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL"
                       f"&url=https://{target}&size=256",
                       f"https://icons.duckduckgo.com/ip3/{target}.ico"]
        for url in candidates:
            if url in tried:
                continue
            tried.add(url)
            data = _get(client, url)
            got = _png(data) if data else None
            if got and got[1] >= 32 and (best is None or got[1] > best[1]):
                best = got
            if best and best[1] >= GOOD_PX:
                break
        return best
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
        try:                     # v0.298 then every Composio app's logo, gently (cached files make later starts instant)
            from . import composio
            slugs = list(composio.catalog()) if composio.configured() else []
        except Exception:
            slugs = []
        m = 0
        for slug in slugs:
            try:
                if logo("cmp", slug):
                    m += 1
            except Exception:
                log.exception("logo cmp:%s failed", slug)
            time.sleep(pause_s)
        if slugs:
            log.info("composio logos ready: %s of %s", m, len(slugs))
    threading.Thread(target=go, daemon=True, name="logo-warm").start()


def logo(kind: str, key: str) -> bytes | None:
    """Cached logo PNG, fetched on first use. None = this one has no logo we can show."""
    target = resolve(kind, key)
    if target is None:
        return None
    name = hashlib.sha256(f"v{VERSION}:{kind}:{key}:{target[1]}".encode()).hexdigest()[:24]
    png, miss = CACHE_DIR / f"{name}.png", CACHE_DIR / f"{name}.miss"
    drawn = CACHE_DIR / f"{name}.drawn"
    if png.exists() and not (drawn.exists() and time.time() - drawn.stat().st_mtime > MISS_RETRY_S):
        return png.read_bytes()
    if miss.exists() and time.time() - miss.stat().st_mtime < MISS_RETRY_S:
        return None
    with _locks_guard:
        lock = _locks.setdefault(name, threading.Lock())
    with lock:
        if png.exists() and not drawn.exists():
            return png.read_bytes()
        data = fetch(*target)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if data:
            png.write_bytes(data)
            miss.unlink(missing_ok=True)
            if kind in ("dir", "cmp"):
                from . import directory
                is_drawn = data == (monogram(*directory.monogram_of(key)) if kind == "dir" else monogram(*cmp_monogram(key)))
                if is_drawn:
                    drawn.touch()
                else:
                    drawn.unlink(missing_ok=True)
        else:
            miss.touch()
            log.info("no logo for %s:%s (%s)", kind, key, target[1])
        return data
