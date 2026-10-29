"""v0.224 Daily off-server backup of the websites themselves.

Litestream (v0.49) streams only the database. The websites live as files on this one server's disk: the published sites
(data/hosted) and what they are built from (each site's `src`: written sections + her photos). A lost disk = every live
customer website gone and nothing to rebuild from. Now, once a day after 03:00 IST, one tar.gz of those two goes to an
S3-compatible bucket (AWS S3, Cloudflare R2, Backblaze B2, DigitalOcean Spaces, MinIO), signed with AWS Signature V4 here
(no new dependency); copies older than SITES_BACKUP_KEEP_DAYS are deleted. Off unless SITES_BACKUP_BUCKET + keys are set.

Restore (on a new server, to a folder first):  python -m app.site.backup restore 2026-10-29 /tmp/sites-restore"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx

log = logging.getLogger("santosh.site")
IST = timezone(timedelta(hours=5, minutes=30))
PREFIX = "hoola/sites/"
_TRANSPORT: httpx.BaseTransport | None = None


class BackupError(Exception):
    pass


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def _cfg() -> dict[str, Any]:
    from ..config import get_settings
    st = get_settings()
    region = (st.sites_backup_region or "auto").strip()
    return {"bucket": (st.sites_backup_bucket or "").strip(), "endpoint": (st.sites_backup_endpoint or "").rstrip("/"),
            "region": "us-east-1" if region in ("", "auto") and not st.sites_backup_endpoint else (region or "auto"),
            "key_id": st.sites_backup_key_id or "", "secret": st.sites_backup_secret or "",
            "keep": max(1, int(st.sites_backup_keep_days or 14))}


def enabled() -> bool:
    c = _cfg()
    return bool(c["bucket"] and c["key_id"] and c["secret"])


# ---------------------------------------------------------------- S3 with Signature V4
def _url(c: dict[str, Any], key: str = "", query: str = "") -> str:
    base = c["endpoint"] or f"https://s3.{c['region']}.amazonaws.com"
    return f"{base}/{c['bucket']}" + (f"/{quote(key, safe='/-_.~')}" if key else "") + (f"?{query}" if query else "")


def _sign(c: dict[str, Any], method: str, url: str, when: datetime | None = None) -> dict[str, str]:
    u = urlparse(url)
    t = when or datetime.now(timezone.utc)
    amz, day = t.strftime("%Y%m%dT%H%M%SZ"), t.strftime("%Y%m%d")
    payload = "UNSIGNED-PAYLOAD"
    q = "&".join(sorted(p if "=" in p else p + "=" for p in u.query.split("&") if p)) if u.query else ""
    headers = {"host": u.netloc, "x-amz-content-sha256": payload, "x-amz-date": amz}
    signed = ";".join(sorted(headers))
    canonical = "\n".join([method, u.path or "/", q, "".join(f"{k}:{headers[k]}\n" for k in sorted(headers)), signed, payload])
    scope = f"{day}/{c['region']}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = ("AWS4" + c["secret"]).encode()
    for part in (day, c["region"], "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    return {"x-amz-content-sha256": payload, "x-amz-date": amz,
            "Authorization": f"AWS4-HMAC-SHA256 Credential={c['key_id']}/{scope}, SignedHeaders={signed}, Signature={sig}"}


def _req(method: str, key: str = "", query: str = "", content: Any = None) -> httpx.Response:
    c = _cfg()
    url = _url(c, key, query)
    with httpx.Client(timeout=600, transport=_TRANSPORT) as cl:
        r = cl.request(method, url, headers=_sign(c, method, url), content=content)
    if r.status_code >= 300:
        raise BackupError(f"{method} {key or c['bucket']}: HTTP {r.status_code} {r.text[:200]}")
    return r


def keys(prefix: str = PREFIX) -> list[str]:
    out, token = [], ""
    for _ in range(50):
        q = "list-type=2&prefix=" + quote(prefix, safe="") + (f"&continuation-token={quote(token, safe='')}" if token else "")
        root = ET.fromstring(_req("GET", "", q).content)
        ns = re.match(r"\{.*\}", root.tag)
        ns = ns.group(0) if ns else ""
        out += [e.text or "" for e in root.iter(f"{ns}Key")]
        token = (root.findtext(f"{ns}NextContinuationToken") or "").strip()
        if not token:
            break
    return out


# ---------------------------------------------------------------- the archive
def _roots() -> tuple[Path, Path]:
    from . import build as B
    from . import hosting as H
    return H.hosted_root(), B.root()                              # data/hosted, data/sites


def make_archive(dest: Path) -> dict[str, int]:
    """data/hosted (published sites; links between addresses kept as links) + every site's src (sections + photos)."""
    hosted, sites = _roots()
    files = 0
    with tarfile.open(dest, "w:gz") as tar:
        if hosted.exists():
            for p in sorted(hosted.iterdir()):
                if p.name.startswith("."):
                    continue                     # .new / .old swap folders
                if p.is_symlink():               # another address of the same site: kept as a link to its sibling
                    ti = tarfile.TarInfo(f"hosted/{p.name}")
                    ti.type, ti.linkname = tarfile.SYMTYPE, Path(os.readlink(p)).name
                    tar.addfile(ti)
                    files += 1
                    continue
                tar.add(p, arcname=f"hosted/{p.name}", recursive=True)
                files += sum(1 for _ in p.rglob("*"))
        if sites.exists():
            for src in sorted(sites.glob("*/*/src")):
                rel = src.relative_to(sites)
                tar.add(src, arcname=f"sites/{rel.as_posix()}", recursive=True)
                files += sum(1 for _ in src.rglob("*"))
    return {"files": files, "bytes": dest.stat().st_size}


def _state() -> Path:
    hosted, _ = _roots()
    return hosted.parent / "sites_backup.json"


def run(day: str = "") -> dict[str, Any]:
    if not enabled():
        raise BackupError("Website backup band hai (SITES_BACKUP_BUCKET / keys set nahi).")
    day = day or datetime.now(IST).strftime("%Y-%m-%d")
    key = f"{PREFIX}{day}.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        arc = Path(tmp) / "sites.tar.gz"
        info = make_archive(arc)
        with arc.open("rb") as f:
            _req("PUT", key, content=f)
    cut = (datetime.now(IST) - timedelta(days=_cfg()["keep"])).strftime("%Y-%m-%d")
    pruned = 0
    for k in keys():
        m = re.search(r"(\d{4}-\d{2}-\d{2})\.tar\.gz$", k)
        if m and m.group(1) < cut:
            _req("DELETE", k)
            pruned += 1
    out = {"ok": True, "key": key, "pruned": pruned, **info}
    _state().write_text(json.dumps({"day": day, **out}))
    log.info("website backup done: %s", out)
    return out


def daily(now: datetime | None = None) -> dict[str, Any] | None:
    """Worker: once a day after 03:00 IST. A failure is logged and tried again on the next tick."""
    if not enabled():
        return None
    t = (now or datetime.now(timezone.utc)).astimezone(IST)
    if t.hour < 3:
        return None
    day = t.strftime("%Y-%m-%d")
    try:
        last = json.loads(_state().read_text()).get("day")
    except (OSError, ValueError):
        last = ""
    if last == day:
        return None
    try:
        return run(day)
    except Exception as e:
        log.warning("website backup failed: %s", e)
        return {"ok": False, "error": str(e)[:300]}


def status() -> dict[str, Any]:
    try:
        last = json.loads(_state().read_text())
    except (OSError, ValueError):
        last = {}
    return {"enabled": enabled(), "last": last}


def restore(day: str, into: Path) -> dict[str, int]:
    """Download one day's archive and unpack it into `into` (never outside it; links that point outside are skipped).
    Copy hosted/ and sites/ back into data/ yourself after looking at them."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day or ""):
        raise BackupError("Date YYYY-MM-DD chahiye.")
    into.mkdir(parents=True, exist_ok=True)
    root = into.resolve()
    data = _req("GET", f"{PREFIX}{day}.tar.gz").content
    n = 0
    with tempfile.TemporaryDirectory() as tmp:
        arc = Path(tmp) / "a.tar.gz"
        arc.write_bytes(data)
        with tarfile.open(arc, "r:gz") as tar:
            for m in tar.getmembers():
                target = (root / m.name).resolve()
                if root not in target.parents and target != root:
                    continue
                if m.issym() or m.islnk():
                    link = (target.parent / m.linkname).resolve()
                    if root not in link.parents:
                        continue
                if not (m.isfile() or m.isdir() or m.issym()):
                    continue
                tar.extract(m, root, filter="data") if sys.version_info >= (3, 12) else tar.extract(m, root)
                n += 1
    return {"restored": n}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["run"]:
        print(json.dumps(run(a[1] if len(a) > 1 else "")))
    elif a[:1] == ["restore"] and len(a) == 3:
        print(json.dumps(restore(a[1], Path(a[2]))))
    else:
        print("usage: python -m app.site.backup run [YYYY-MM-DD] | restore YYYY-MM-DD <folder>")
        sys.exit(2)
