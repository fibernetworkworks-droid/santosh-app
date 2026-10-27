"""v0.92 Which websites refuse this server, remembered.

The owner's report (Oct 2026): all 10 website jobs in two weeks were "download my Aadhaar", and none finished. UIDAI
refuses the VPS's data-centre address (pages end on Chrome's error page, or the page opens but its CAPTCHA / OTP calls
never answer), and every new request walked into the same wall for minutes. Now:

  * a failed job records the sites that did not answer this server (NetGuard's `failed` list + the start site) under
    their base domain (myaadhaar.uidai.gov.in, tathya.uidai.gov.in -> uidai.gov.in);
  * before a new job starts, its site is checked: remembered as refusing (3 days, cleared by any job that works there),
    or a quick live check (DNS + a TCP handshake to 443 on a PUBLIC address, 5 s; nothing is sent) fails;
  * such a job goes to her own PC (Santosh Desktop, her home / office internet) when it is online, else she is told at
    once and plainly, with the choices (PC, phone, office proxy) - instead of minutes of retrying.
The memory is about this server's network, not about the owner: one small JSON file for the server.
A site reached through her own upstream proxy (BROWSER_UPSTREAM_PROXY) counts as reachable.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

log = logging.getLogger("santosh.operator.reach")

KEEP_S = 3 * 24 * 3600                 # a refusal is remembered this long (any success clears it)
PROBE_TIMEOUT = 5.0
_lock = threading.Lock()
_booted = False
PATH: Path | None = None               # tests point this elsewhere
STATS = {"probes": 0, "probe_fail": 0, "routed_pc": 0, "told": 0}

# sites people name without a link (Hinglish / Marathi words) -> the official address the job would open
KNOWN = [
    (r"aadh?aa?r|आधार|uidai|e-?aadhaar", "myaadhaar.uidai.gov.in"),
    (r"digi\s?locker", "www.digilocker.gov.in"),
    (r"irctc|pnr|train ticket|rail ticket", "www.irctc.co.in"),
    (r"\bepfo\b|\buan\b|provident fund|\bpf\b", "unifiedportal-mem.epfindia.gov.in"),
    (r"income ?tax|\bitr\b|\bpan\b.*(status|link)|refund status", "www.incometax.gov.in"),
    (r"passport", "www.passportindia.gov.in"),
    (r"msedcl|mahavitaran|mahadiscom", "wss.mahadiscom.in"),
    (r"\bgst\b|gstin", "www.gst.gov.in"),
]
_TWO_LEVEL = {"gov.in", "nic.in", "co.in", "org.in", "net.in", "ac.in", "edu.in", "res.in", "gen.in", "firm.in", "ind.in"}


def _path() -> Path:
    p = PATH or Path(os.environ.get("OPERATOR_REACH_FILE") or Path("data") / "operator" / "reach.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def base(host: str) -> str:
    """myaadhaar.uidai.gov.in -> uidai.gov.in, www.irctc.co.in -> irctc.co.in, a.b.example.com -> example.com."""
    h = (host or "").strip().lower().rstrip(".").split(":")[0]
    if not h or re.fullmatch(r"[\d.]+|\[?[0-9a-f:]+\]?", h):
        return h
    parts = h.split(".")
    n = 3 if ".".join(parts[-2:]) in _TWO_LEVEL else 2
    return ".".join(parts[-n:])


def host_of(url_or_host: str) -> str:
    s = (url_or_host or "").strip()
    if not s:
        return ""
    if "://" not in s:
        s = "https://" + s
    try:
        return (urlparse(s).hostname or "").lower()
    except ValueError:
        return ""


def site_for(task: str, start_url: str = "") -> str:
    """The host a job will open: its link, a web address written in the task, or a known portal named in it."""
    if start_url:
        return host_of(start_url)
    m = re.search(r"https?://[^\s'\"<>]+", task or "")
    if m:
        return host_of(m.group(0))
    m = re.search(r"\b((?:[a-z0-9-]+\.)+(?:gov\.in|nic\.in|co\.in|org\.in|in|com|org|net))\b", (task or "").lower())
    if m:
        return m.group(1)
    for pat, host in KNOWN:
        if re.search(pat, task or "", re.I):
            return host
    return ""


def _load() -> dict[str, Any]:
    try:
        return json.loads(_path().read_text())
    except (OSError, ValueError):
        return {}


def _save(d: dict[str, Any]) -> None:
    p = _path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    os.replace(tmp, p)


def note_fail(host: str, why: str = "") -> None:
    b = base(host)
    if not b or b.startswith("chrome") or "." not in b:
        return
    with _lock:
        d = _load()
        e = d.setdefault(b, {"bad": 0, "last_bad": 0, "last_ok": 0, "why": ""})
        e["bad"] += 1
        e["last_bad"] = time.time()
        e["why"] = str(why or e.get("why") or "")[:200]
        _save(d)
    log.info("site %s refuses this server (%s)", b, why)


def note_ok(host: str) -> None:
    b = base(host)
    if not b:
        return
    with _lock:
        d = _load()
        e = d.get(b)
        if e is None:
            return
        e["last_ok"] = time.time()
        e["bad"] = 0
        _save(d)


def _via_upstream(host: str) -> bool:
    raw = (os.environ.get("BROWSER_UPSTREAM_PROXY") or "").strip()
    if not raw:
        try:
            from ..config import get_settings
            raw = (get_settings().browser_upstream_proxy or "").strip()
            only = get_settings().browser_upstream_hosts or ""
        except Exception:
            only = ""
    else:
        only = os.environ.get("BROWSER_UPSTREAM_HOSTS") or ""
    if not raw:
        return False
    hosts = [h.strip().lower().lstrip(".") for h in only.split(",") if h.strip()]
    h = host.lower()
    return not hosts or any(h == x or h.endswith("." + x) for x in hosts)


def remembered(host: str) -> dict[str, Any] | None:
    """The refusal on record for this site (None = nothing recent)."""
    _bootstrap()
    e = _load().get(base(host))
    if not e or e.get("bad", 0) < 1:
        return None
    if time.time() - float(e.get("last_bad") or 0) > KEEP_S or float(e.get("last_ok") or 0) > float(e.get("last_bad") or 0):
        return None
    return e


def probe(host: str, port: int = 443, timeout: float = PROBE_TIMEOUT) -> tuple[bool, str]:
    """DNS + a TCP handshake to a PUBLIC address of the site (nothing is sent). (reachable, why-not)."""
    STATS["probes"] += 1
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return False, "naam nahi mila (DNS)"
    ips = []
    for i in infos:
        try:
            ip = ipaddress.ip_address(i[4][0].split("%")[0])
        except ValueError:
            continue
        if ip.is_global and str(ip) not in ips:
            ips.append(str(ip))
    ips.sort(key=lambda x: ":" in x)                # IPv4 first (most VPSs have no IPv6 route)
    if not ips:
        return False, "sirf andar ka (private) address"
    last = ""
    for ip in ips[:3]:
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True, ""
        except socket.timeout:
            last = "jawab nahi diya (timeout)"
        except OSError as e:
            last = type(e).__name__
    STATS["probe_fail"] += 1
    return False, last or "nahi juda"


def check(task: str, start_url: str = "", live: bool = True) -> dict[str, Any]:
    """Before a job: {site, ok, why, remembered}. ok=False = this server can't (or recently couldn't) reach the site."""
    site = site_for(task, start_url)
    if not site or _via_upstream(site):
        return {"site": site, "ok": True}
    rec = remembered(site)
    if rec:
        return {"site": site, "ok": False, "remembered": True,
                "why": rec.get("why") or "pichhli baar is server se nahi khula"}
    if not live:
        return {"site": site, "ok": True}
    ok, why = probe(site)
    if not ok:
        note_fail(site, f"live check: {why}")
    return {"site": site, "ok": ok, "why": why}


_FAILED_HOST = re.compile(r"^\[?([A-Za-z0-9.-]+\.[A-Za-z]{2,})\]?(?::\d+)?[: ]")


def learn_from_job(start_url: str, task: str, ok: bool, net_failed: list[str], last_url: str = "") -> list[str]:
    """After a job: a failed one records every site that did not answer this server; a good one clears its site."""
    site = site_for(task, start_url)
    if ok:
        if site:
            note_ok(site)
        return []
    hosts = []
    for line in net_failed or []:
        m = _FAILED_HOST.match(str(line))
        if m:
            hosts.append(m.group(1))
    if (last_url or "").startswith("chrome-error") and site:
        hosts.append(site)
    out = []
    for h in dict.fromkeys(hosts):
        if base(h) not in out:
            note_fail(h, "is server se khula nahi")
            out.append(base(h))
    return out


def _bootstrap() -> None:
    """First use on a server: learn from website jobs that already failed on Chrome's error page (last 14 days)."""
    global _booted
    if _booted:
        return
    _booted = True
    if _load():
        return
    try:
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import select

        from ..db import session
        from .models import OperatorTask
        since = datetime.now(timezone.utc) - timedelta(days=14)
        with session() as s:
            rows = s.scalars(select(OperatorTask).where(OperatorTask.created_at >= since)).all()
            seen = [(r.task, r.start_url, r.url, r.status) for r in rows]
        for task, start_url, url, status in seen:
            if status == "failed" and (url or "").startswith("chrome-error"):
                site = site_for(task, start_url)
                if site:
                    note_fail(site, "pichhle kaam mein is server se nahi khula")
    except Exception:
        log.exception("reach bootstrap")
