"""v0.257 REA ENDPOINTS - the URLs, hosts, API paths and IPs written inside a program / app file, read STATICALLY.

Owner: "I TOLD HOOLA TO READ THIS EXE FILE END TO END AND EXTRACT ENDPOINTS BUT AGAIN HOOLA OPENS ITS OWN PC
INSTEAD OF USING REA". REA's actions had no way to list endpoints, so the job went to the cloud PC (install
strings / binutils there). This is the server-side answer, pure Python, no REA binary needed and the file is
never run: every printable ASCII and UTF-16LE string (6+ chars) is scanned, inside zip-based packages (apk / jar /
ipa / xapk / nupkg / whl) member by member. Secrets in what it finds (key= / token= / sig= values, AIza... / sk-...
/ ghp_... keys) are masked before anything is returned or saved. The full list is saved as a dataset (data desk),
so data_read pages it and doc_studio data=<id> turns it into a PDF / Excel.

What it cannot see: addresses built at runtime, encrypted / packed strings, and anything the program downloads.
"""
from __future__ import annotations

import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MAX_SCAN = 200 * 1024 * 1024        # bytes read from one file / member (appcheck_max_mb caps the upload itself)
MAX_MEMBER = 60 * 1024 * 1024
MAX_MEMBERS = 4000
CAP = 600                            # values kept per kind in the reply's dataset
_ZIPPY = (".apk", ".apks", ".xapk", ".apkm", ".jar", ".aar", ".ipa", ".nupkg", ".whl", ".zip", ".war", ".ear")
_SKIP_MEMBER = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ttf", ".otf", ".woff", ".woff2", ".mp3", ".mp4", ".ogg",
                ".wav", ".ico")

_ASCII = re.compile(rb"[\x20-\x7e]{6,}")
_UTF16 = re.compile(rb"(?:[\x20-\x7e]\x00){6,}")
_URL = re.compile(r"(?:https?|wss?|ftp)://(?:[^\s/@:\x00]+(?::[^\s/@\x00]*)?@)?[A-Za-z0-9.\-]+(?::\d{1,5})?(?:[/?#][A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%{}-]*)?")
_PATH = re.compile(r"(?<![A-Za-z0-9_./:])/(?:api|v\d{1,2}|graphql|rest|rpc|auth|oauth2?|login|logout|token|users?|"
                   r"admin|ws|socket\.io|upload|download|config|update|telemetry|metrics|health)"
                   r"(?:[/?][A-Za-z0-9._~/%{}:=&?-]{0,160})?(?![A-Za-z0-9])")
_TLD = ("com", "net", "org", "io", "in", "co", "app", "dev", "cloud", "ai", "xyz", "gov", "edu", "info", "biz", "me",
        "us", "uk", "de", "ru", "cn", "jp", "tech", "site", "online", "live", "tv", "gg", "so", "sh", "to", "ly")
_HOST = re.compile(r"(?<![A-Za-z0-9@._-])((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:" + "|".join(_TLD) +
                   r"))(?::\d{1,5})?(?![A-Za-z0-9-])")
_IP = re.compile(r"(?<![\d.])((?:\d{1,3}\.){3}\d{1,3})(?::(\d{1,5}))?(?![\d.])")
_NOT_HOST = re.compile(r"\.(?:dll|exe|so|sys|json|xml|png|jpg|js|css|html?|txt|cs|java|kt|class|dex|config|"
                       r"resources|pdb|ini|log|dat|bin|db)$")
# secrets inside what it finds: masked before anything leaves this module
_SECRET_Q = re.compile(r"([?&;](?:api[_-]?key|key|token|access[_-]?token|secret|client[_-]?secret|password|passwd|pwd|"
                       r"sig|signature|auth|session)=)[^&#\s\"']+", re.I)
_SECRET_V = re.compile(r"\b(?:AIza[0-9A-Za-z_\-]{30,}|sk-[A-Za-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{20,}|xox[abp]-[A-Za-z0-9-]{10,}|"
                       r"AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,})")
_USERINFO = re.compile(r"(://)[^/@\s:]+:[^/@\s]+@")


def mask(s: str) -> str:
    s = _SECRET_Q.sub(lambda m: m.group(1) + "***", s)
    s = _SECRET_V.sub("***", s)
    return _USERINFO.sub(r"\1***:***@", s)


def _strings(data: bytes):
    for m in _ASCII.finditer(data):
        yield m.group().decode("ascii", "ignore")
    for m in _UTF16.finditer(data):
        yield m.group().decode("utf-16le", "ignore")


def _ip_ok(ip: str) -> bool:
    parts = ip.split(".")
    if any(int(p) > 255 or (len(p) > 1 and p[0] == "0") for p in parts):
        return False
    return ip not in ("0.0.0.0", "255.255.255.255") and not ip.startswith(("1.0.0.", "2.0.0.", "4.0.0."))


_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _real_host(url: str) -> bool:
    """A URL whose host looks real: localhost, an IP, or lowercase labels ending in a known / two-letter TLD. Strings
    packed back to back inside big binaries make fragments like 'https://www.googliveRegionCreate' - those fail."""
    host = re.sub(r"^[a-z]+://", "", url).split("/")[0].split("?")[0].split("#")[0]
    host = host.rsplit("@", 1)[-1].split(":")[0]
    if host == "localhost" or _IP.fullmatch(host):
        return True
    labels = host.split(".")
    if len(labels) < 2 or not all(_LABEL.match(x) for x in labels):
        return False
    tld = labels[-1]
    return tld in _TLD or (len(tld) == 2 and tld.isalpha())


def _scan_text(s: str, where: str, found: dict[str, dict[str, dict]]) -> None:
    def add(kind: str, value: str) -> None:
        value = mask(value.strip().rstrip(".,;:)'\"\\"))[:300]
        if not value:
            return
        row = found[kind].get(value)
        if row is None:
            found[kind][value] = {"count": 1, "where": where}
        else:
            row["count"] += 1
    for m in _URL.finditer(s):
        if _real_host(m.group()):
            add("url", m.group())
        else:
            found["_unclear"][m.group()[:80]] = {"count": 1, "where": where}
    for m in _PATH.finditer(s):
        add("api_path", m.group())
    for m in _HOST.finditer(s):
        h = m.group(1)
        if not _NOT_HOST.search(h) and h.count(".") >= 1 and not h[0].isdigit():
            add("host", m.group())
    for m in _IP.finditer(s):
        if _ip_ok(m.group(1)):
            add("ip", m.group())


def _scan_bytes(data: bytes, where: str, found) -> int:
    n = 0
    for s in _strings(data):
        if ("." in s or "/" in s) and len(s) < 4000:
            _scan_text(s, where, found)
            n += 1
    return n


def extract(path: Path, name: str, kind: str = "") -> dict[str, Any]:
    """Scan one staged file; returns {kinds -> rows, counts, scanned, limits}. Never runs the file."""
    found: dict[str, dict[str, dict]] = defaultdict(dict)
    limits: list[str] = []
    scanned = 0
    members = 0
    low = name.lower()
    zippy = kind in ("apk", "apks", "zip") or low.endswith(_ZIPPY)
    if zippy and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist()[:MAX_MEMBERS]:
                if info.is_dir() or info.filename.lower().endswith(_SKIP_MEMBER):
                    continue
                if info.file_size > MAX_MEMBER:
                    limits.append(f"{info.filename}: {info.file_size // (1024 * 1024)} MB, skipped")
                    continue
                try:
                    data = z.read(info)
                except Exception:
                    continue
                members += 1
                scanned += _scan_bytes(data, info.filename[:120], found)
                if zipfile.is_zipfile(__import__("io").BytesIO(data)) and info.filename.lower().endswith(".apk"):
                    with zipfile.ZipFile(__import__("io").BytesIO(data)) as inner:      # split / bundled APKs
                        for ii in inner.infolist()[:MAX_MEMBERS]:
                            if ii.is_dir() or ii.file_size > MAX_MEMBER or ii.filename.lower().endswith(_SKIP_MEMBER):
                                continue
                            scanned += _scan_bytes(inner.read(ii), f"{info.filename}/{ii.filename}"[:120], found)
            if len(z.infolist()) > MAX_MEMBERS:
                limits.append(f"only the first {MAX_MEMBERS} files inside the package were read")
    else:
        size = path.stat().st_size
        with path.open("rb") as f:
            data = f.read(MAX_SCAN)
        if size > MAX_SCAN:
            limits.append(f"only the first {MAX_SCAN // (1024 * 1024)} MB were read")
        scanned = _scan_bytes(data, name[:120], found)
    # a host already inside a URL is not listed twice
    url_hosts = {re.sub(r"^[a-z]+://", "", u).split("/")[0].split("?")[0].lower() for u in found["url"]}
    for h in list(found["host"]):
        if h.lower() in url_hosts:
            found["host"].pop(h)
    unclear = len(found.pop("_unclear", {}))
    if unclear:
        limits.append(f"{unclear} URL-like fragments skipped (strings packed together inside the binary, no real host)")
    limits.append("Read statically - the file was never run. Addresses built at runtime, encrypted / packed strings "
                  "and anything it downloads later do not show here; secrets in what was found are masked (***).")
    if members:
        limits.append(f"{members} files inside the package were read")
    return {"found": found, "strings_checked": scanned, "limits": limits}


def rows_of(found: dict[str, dict[str, dict]]) -> list[dict[str, Any]]:
    rows = []
    for kind in ("url", "api_path", "host", "ip"):
        items = sorted(found.get(kind, {}).items(), key=lambda kv: (-kv[1]["count"], kv[0]))[:CAP]
        for value, meta in items:
            host = ""
            if kind == "url":
                host = re.sub(r"^[a-z]+://", "", value).split("/")[0].split("?")[0]
            elif kind in ("host", "ip"):
                host = value
            rows.append({"kind": kind, "value": value, "host": host, "count": meta["count"], "found_in": meta["where"]})
    return rows


def summary(name: str, res: dict[str, Any], dataset: dict | None) -> dict[str, Any]:
    found = res["found"]
    counts = {k: len(found.get(k, {})) for k in ("url", "api_path", "host", "ip")}
    hosts = Counter()
    for u, meta in found.get("url", {}).items():
        hosts[re.sub(r"^[a-z]+://", "", u).split("/")[0].split("?")[0]] += meta["count"]
    for h, meta in found.get("host", {}).items():
        hosts[h] += meta["count"]
    top = [u for u, _ in sorted(found.get("url", {}).items(), key=lambda kv: -kv[1]["count"])[:25]]
    paths = [p for p, _ in sorted(found.get("api_path", {}).items(), key=lambda kv: -kv[1]["count"])[:20]]
    out = {"name": name, "counts": counts, "top_hosts": [h for h, _ in hosts.most_common(15)], "urls": top,
           "api_paths": paths, "ips": list(found.get("ip", {}))[:10], "strings_checked": res["strings_checked"],
           "limits": res["limits"]}
    if dataset:
        out["dataset"] = dataset["id"]
        out["next"] = (f"Full list saved as dataset {dataset['id']} ({dataset['count']} rows: kind, value, host, count, "
                       f"found_in): data_read to page it, doc_studio data={dataset['id']} for a PDF / Excel.")
    elif not any(counts.values()):
        out["next"] = ("No addresses are written in plain text in this file (packed, encrypted or built at runtime). "
                       "Say so plainly; rea_khoj action=overview shows what the program imports and uses.")
    return out
