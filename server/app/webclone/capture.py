"""WEB CLONE stage 1 - capture: point at a website, keep what a Next.js rebuild needs.

A headless Chromium (playwright) loads the page, runs its JS, and the post-JS DOM is kept as the
single source of truth for the rebuild. Around it the stage collects: linked + inline CSS (each
file kept verbatim under a ``/* src: ... */`` marker), <img> sources + srcset candidates +
CSS-declared webfonts / background-images, favicons, and the original JS bundles (kept for REA,
never emitted into the rebuild). Two screenshots (1280x800 desktop, 390x844 phone) and a
manifest.json tie the bundle together.

SSRF law: the page URL and EVERY asset fetch go through scrape_tools._guard_url - private,
loopback and cloud-metadata addresses are never fetched. Caps: MAX_ASSETS files, MAX_ASSET_MB
per file; over-cap assets are skipped and named in the manifest, never fatal.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

MAX_ASSETS = 400          # distinct downloaded files (images + fonts + favicons)
MAX_ASSET_MB = 25         # per-file cap
_CSS_URL = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)")
_ASSET_SKIP = re.compile(r"^data:|^blob:|^javascript:|^mailto:|^#", re.I)


class CaptureError(Exception):
    """The page could not be captured - the message is user-facing."""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", (value or "").lower()).strip("-")[:60] or "site"


def _safe_name(url: str, content_type: str, kind: str, taken: set[str]) -> str:
    """Deterministic asset name: sha1(url)[:10] + sane extension, deduped."""
    ext = {
        "css": ".css", "js": ".js", "img": ".img", "font": ".font", "icon": ".icon",
    }.get(kind, "")
    ctype = (content_type or "").split(";")[0].strip().lower()
    table = {
        "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif",
        "image/svg+xml": ".svg", "image/x-icon": ".ico", "image/vnd.microsoft.icon": ".ico",
        "text/css": ".css", "text/javascript": ".js", "application/javascript": ".js",
        "font/woff2": ".woff2", "font/woff": ".woff", "font/ttf": ".ttf", "font/otf": ".otf",
        "application/font-woff2": ".woff2", "application/font-woff": ".woff",
        "video/mp4": ".mp4", "audio/mpeg": ".mp3", "application/pdf": ".pdf", "application/json": ".json",
    }
    if not ext or ext == ".img" or ext == ".font" or ext == ".icon":
        ext = table.get(ctype) or Path(urlparse(url).path).suffix.lower() or ".bin"
    name = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10] + ext
    while name in taken:                       # same url twice with different kinds lands once
        name = name[:10] + "-2" + name[10:]
    taken.add(name)
    return name


def _fetch(client: httpx.Client, url: str) -> tuple[bytes, str] | None:
    """One guarded fetch. Private / bad addresses return None (asset-level skip)."""
    try:
        from ..agent.scrape_tools import _guard_url
        _guard_url(url)                        # raises on private / loopback / metadata
    except Exception:
        return None
    try:
        r = client.get(url)
        if r.status_code >= 400:
            return None
        return r.content, r.headers.get("content-type", "")
    except Exception:
        return None


def _collect_refs(dom: str, page_url: str) -> dict[str, list[str]]:
    """Everything worth keeping, as absolute URLs, in first-seen order."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(dom, "html.parser")
    refs: dict[str, list[str]] = {"css": [], "img": [], "font": [], "icon": [], "js": []}

    def add(kind: str, raw: str) -> None:
        raw = (raw or "").strip()
        if not raw or _ASSET_SKIP.match(raw):
            return
        absu = urljoin(page_url, raw)
        if absu not in refs[kind]:
            refs[kind].append(absu)

    for link in soup.find_all("link"):
        rel = " ".join(link.get("rel") or []).lower()
        href = link.get("href") or ""
        if "stylesheet" in rel:
            add("css", href)
        elif "icon" in rel or "apple-touch" in rel:
            add("icon", href)
    for el in soup.find_all("style"):
        for _q, u in _CSS_URL.findall(el.get_text() or ""):
            for k in ("font", "img"):
                add(k, u)
    for el in soup.find_all("link"):
        if "preload" in " ".join(el.get("rel") or []).lower():
            as_ = (el.get("as") or "").lower()
            if as_ == "font":
                add("font", el.get("href") or "")
    for el in soup.find_all("img"):
        add("img", el.get("src") or "")
        for part in (el.get("srcset") or "").split(","):
            add("img", part.strip().split(" ")[0])
        for part in (el.get("imagesrcset") or "").split(","):
            add("img", part.strip().split(" ")[0])
    for el in soup.find_all("source"):
        for part in (el.get("srcset") or "").split(","):
            add("img", part.strip().split(" ")[0])
    for el in soup.find_all("[style]"):
        for _q, u in _CSS_URL.findall(el.get("style") or ""):
            add("img", u)
    for el in soup.find_all("script", src=True):
        add("js", el.get("src") or "")
    return refs


def _collect_css_urls(css_text: str, base: str) -> tuple[list[str], str]:
    """url() refs inside one CSS file -> absolute urls; the text is kept verbatim."""
    out: list[str] = []
    for _q, u in _CSS_URL.findall(css_text):
        u = u.strip()
        if not u or _ASSET_SKIP.match(u):
            continue
        absu = urljoin(base, u)
        if absu not in out:
            out.append(absu)
    return out, css_text


def capture(url: str, out_dir: Path, tenant_id: str = "") -> dict:
    """Load url in headless Chromium and write the bundle into out_dir. Returns the manifest."""
    from ..agent.scrape_tools import _guard_url

    page_url = _guard_url(url)                 # the page itself: private = hard fail
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    taken: set[str] = set()
    manifest: dict = {"url": page_url, "tenant": tenant_id, "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "css_files": [], "assets": [], "js_files": [], "skipped": [], "notes": []}

    # ---- 1. post-JS DOM + screenshots (playwright sync API inside the caller's worker thread)
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:                     # pragma: no cover - env without browsers
        raise CaptureError(f"Browser engine missing on this server: {e}") from e
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(page_url, wait_until="domcontentloaded", timeout=45_000)
                try:
                    page.wait_for_load_state("networkidle", timeout=12_000)
                except Exception:
                    manifest["notes"].append("network idle not reached in 12s; DOM kept as-is")
                page.wait_for_timeout(1_200)   # late animations / lazy hydration settle
                dom = page.content()
                title = page.title()
                (out_dir / "dom.html").write_text(dom, encoding="utf-8")
                try:
                    page.screenshot(path=str(out_dir / "screenshots-desktop.png"))
                except Exception:
                    manifest["skipped"].append("desktop screenshot failed")
                try:
                    mpage = browser.new_page(viewport={"width": 390, "height": 844})
                    mpage.goto(page_url, wait_until="domcontentloaded", timeout=45_000)
                    mpage.wait_for_timeout(800)
                    mpage.screenshot(path=str(out_dir / "screenshots-mobile.png"))
                    mpage.close()
                except Exception:
                    manifest["skipped"].append("mobile screenshot failed")
            finally:
                browser.close()
    except CaptureError:
        raise
    except Exception as e:
        raise CaptureError(f"Yeh website khuli hi nahi ({e.__class__.__name__}) - link check kijiye.") from e

    manifest["title"] = title
    manifest["dom_chars"] = len(dom)

    # ---- 2. assets via httpx under the same SSRF law + caps
    origin = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}"
    manifest["origin"] = origin
    refs = _collect_refs(dom, page_url)
    with httpx.Client(timeout=25, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) HoolaWebClone/0.694.0"}) as client:
        for kind in ("css", "img", "font", "icon", "js"):
            for absu in refs[kind]:
                if len(manifest["assets"]) + len(manifest["css_files"]) + len(manifest["js_files"]) >= MAX_ASSETS:
                    manifest["skipped"].append(f"asset cap {MAX_ASSETS} reached; rest skipped")
                    break
                got = _fetch(client, absu)
                if got is None:
                    manifest["skipped"].append(absu)
                    continue
                data, ctype = got
                if len(data) > MAX_ASSET_MB * 1024 * 1024:
                    manifest["skipped"].append(f"{absu}: over {MAX_ASSET_MB} MB")
                    continue
                name = _safe_name(absu, ctype, kind, taken)
                (out_dir / name).write_bytes(data)
                if kind == "css":
                    manifest["css_files"].append({"name": name, "url": absu})
                elif kind == "js":
                    manifest["js_files"].append({"name": name, "url": absu})
                else:
                    manifest["assets"].append({"name": name, "url": absu, "kind": kind})
            else:
                continue
            break

    # ---- 3. url() refs inside the captured CSS (webfonts / backgrounds)
    have = {a["url"] for a in manifest["assets"]} | {c["url"] for c in manifest["css_files"]}
    with httpx.Client(timeout=25, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) HoolaWebClone/0.694.0"}) as client:
        for entry in list(manifest["css_files"]):
            text = (out_dir / entry["name"]).read_text(encoding="utf-8", errors="replace")
            entry["url_refs"] = len(_CSS_URL.findall(text))
            for absu in _collect_css_urls(text, entry["url"])[0]:
                if absu in have or len(manifest["assets"]) >= MAX_ASSETS:
                    continue
                got = _fetch(client, absu)
                if got is None:
                    continue
                data, ctype = got
                name = _safe_name(absu, ctype, "font" if ("font" in ctype or Path(urlparse(absu).path).suffix.lower()
                                                          in (".woff2", ".woff", ".ttf", ".otf", ".eot")) else "img",
                                  taken)
                (out_dir / name).write_bytes(data)
                manifest["assets"].append({"name": name, "url": absu, "kind": "css-ref"})
                have.add(absu)

    manifest["counts"] = {"css": len(manifest["css_files"]), "assets": len(manifest["assets"]),
                          "js": len(manifest["js_files"]), "skipped": len(manifest["skipped"])}
    manifest["dom_path"] = str(out_dir / "dom.html")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest
