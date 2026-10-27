"""v0.63 "Naya Hoola aaya hai": the newest phone-app release on GitHub (the same releases CI publishes).

latest() -> {tag, version, build, apk_url, size, sha256, notes, published_at} from the repo's releases (tags like
v0.63.0-b120 with an app-release.apk asset; the desktop-latest release is skipped). Cached 10 minutes. The phone checks
the APK's SHA-256 (GitHub's own asset digest), package name and signing key before Android's installer asks the owner.
"""
from __future__ import annotations

import re
import time
from typing import Any

TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-b(\d+)$")
_cache: dict[str, Any] = {"at": 0.0, "value": None}
_transport = None    # tests


def _repo() -> str:
    from .config import get_settings
    return (getattr(get_settings(), "app_release_repo", "") or "fibernetworkworks-droid/santosh-app").strip()


def vtuple(v: str) -> tuple[int, int, int]:
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", (v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def newer(latest: str, current: str) -> bool:
    return vtuple(latest) > vtuple(current)


def _notes(body: str) -> str:
    body = re.sub(r"\r", "", body or "")
    body = re.sub(r"(?m)^\s*(Co-Authored-By|Claude-Session):.*$", "", body)
    return body.strip()[:1200]


def latest(force: bool = False) -> dict[str, Any] | None:
    if not force and _cache["value"] is not None and time.time() - _cache["at"] < 600:
        return _cache["value"]
    import httpx
    url = f"https://api.github.com/repos/{_repo()}/releases?per_page=15"
    try:
        with httpx.Client(timeout=15, transport=_transport, follow_redirects=True) as c:
            r = c.get(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "Hoola-update-check"})
        rows = r.json() if r.status_code == 200 else []
    except Exception:
        rows = []
    best = None
    for rel in rows if isinstance(rows, list) else []:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        m = TAG.match(rel.get("tag_name") or "")
        if not m:
            continue
        apk = next((a for a in rel.get("assets") or [] if a.get("name") == "app-release.apk"), None)
        if not apk or not str(apk.get("browser_download_url", "")).startswith("https://github.com/"):
            continue
        key = tuple(int(x) for x in m.groups())
        if best and key <= best[0]:
            continue
        digest = str(apk.get("digest") or "")
        best = (key, {"tag": rel["tag_name"], "version": ".".join(m.groups()[:3]), "build": int(m.group(4)),
                      "apk_url": apk["browser_download_url"], "size": int(apk.get("size") or 0),
                      "sha256": digest.split(":", 1)[1] if digest.startswith("sha256:") else "",
                      "notes": _notes(rel.get("body") or rel.get("name") or ""), "published_at": rel.get("published_at")})
    value = best[1] if best else None
    if value or _cache["value"] is None:
        _cache.update(at=time.time(), value=value)
    return value or _cache["value"]


def check(current: str) -> dict[str, Any]:
    rel = latest()
    if not rel:
        return {"available": False, "current": current, "say": "Abhi update check nahi ho paya."}
    return rel | {"available": newer(rel["version"], current), "current": current}
