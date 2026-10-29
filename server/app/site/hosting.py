"""v0.122 Hosting + launch: a checked version goes live ONLY on her tap, on a free Hoola address (<name>.<SITES_BASE_DOMAIN>)
and / or her own domain. Her domain is joined through Cloudflare for SaaS (official custom hostnames API on Hoola's zone:
SSL issued by Cloudflare, her visitors' traffic proxied to Hoola's server), or through her own Cloudflare zone (proxied
to Hoola's server). The files are served by Hoola's server (`serve`, used by the HTTP middleware) from data/hosted/<host>.

Every launch keeps the previous live copy, so rollback is instant (also only on her tap). Uptime is checked every 5 min;
two misses in a row = a card + push with the reason."""
from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import re
import shutil
import ssl
import socket
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select

from ..db import now, session
from . import build as B
from . import dns as D
from .hosting_models import SiteHost
from .models import Site, SiteVersion

log = logging.getLogger("santosh.site")
RESERVED = {"www", "api", "admin", "mail", "smtp", "ftp", "hoola", "santosh", "app", "origin", "sites", "cdn", "static", "ns1",
            "ns2", "test", "dev", "staging", "support", "help", "login", "secure", "pay", "upi", "bank", "kyc", "otp"}
_MAP: dict[str, Any] = {"at": 0.0, "hosts": {}}
_MAP_LOCK = threading.Lock()
_TRANSPORT: httpx.BaseTransport | None = None


class HostError(Exception):
    pass


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def _st():
    from ..config import get_settings
    return get_settings()


def cfg() -> dict[str, Any]:
    st = _st()
    return {"base": (getattr(st, "sites_base_domain", "") or "").lower().strip("."),
            "origin": (getattr(st, "sites_origin", "") or "").lower().strip("."),
            "origin_ip": getattr(st, "sites_origin_ip", "") or "",
            "cf_token": getattr(st, "sites_cf_token", "") or "", "cf_zone": getattr(st, "sites_cf_zone_id", "") or ""}


def saas_on() -> bool:
    c = cfg()
    return bool(c["cf_token"] and c["cf_zone"] and c["origin"])


def hosted_root() -> Path:
    p = Path(os.environ.get("SITE_HOSTED_DIR", "data/hosted"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (ValueError, TypeError):
        return default


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from . import service as S
    S._publish(tenant, kind, payload, conv)


# ---------------------------------------------------------------- names
_DV_CONS = dict(zip("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह", "k kh g gh n ch chh j jh n t th d dh n t th d dh n p ph b bh m y r l v sh sh s h".split()))
_DV_VOW = dict(zip("अआइईउऊऋएऐओऔ", "a aa i ee u oo ri e ai o au".split()))
_DV_SIGN = dict(zip("ािीुूृेैोौ", "aa i ee u oo ri e ai o au".split()))


def translit(text: str) -> str:
    """Devanagari -> plain Latin for addresses (Hindi / Marathi names): शर्मा स्वीट्स -> sharma sweets."""
    out, i, t = [], 0, text or ""
    while i < len(t):
        ch = t[i]
        nxt = t[i + 1] if i + 1 < len(t) else ""
        if ch in _DV_CONS:
            out.append(_DV_CONS[ch])
            if nxt == "\u094d":                       # halant: no vowel
                i += 2
                continue
            if nxt in _DV_SIGN:
                out.append(_DV_SIGN[nxt])
                i += 2
                continue
            after = t[i + 1] if i + 1 < len(t) else " "
            if after in "\u0902\u0901":
                out.append("a")
            elif not (after.isspace() or after in "।,." or i + 1 >= len(t)):
                out.append("a")
        elif ch in _DV_VOW:
            out.append(_DV_VOW[ch])
        elif ch in "\u0902\u0901":
            out.append("n")
        elif ch == "\u093c" or ch == "\u0903":
            pass
        else:
            out.append(ch)
        i += 1
    return re.sub(r"aa\b", "a", "".join(out))


def slug_for(name: str) -> str:
    t = unicodedata.normalize("NFKD", translit(name or "")).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"&", " and ", t)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:40].strip("-") or "site"


def free_host(r: Site) -> str:
    c = cfg()
    if not c["base"]:
        raise HostError("Free Hoola address abhi chalu nahi (server par SITES_BASE_DOMAIN set nahi).")
    from .guard import name_problem
    base = slug_for(r.name or (r.number or "site"))
    if base in RESERVED or name_problem(base):
        base = f"{base}-site"
    with session() as s:
        mine = s.scalars(select(SiteHost).where(SiteHost.site_id == r.id, SiteHost.kind == "free",
                                                SiteHost.status != "removed")).first()
        if mine:
            return mine.hostname
        cand, n = base, 1
        while s.scalars(select(SiteHost).where(SiteHost.hostname == f"{cand}.{c['base']}", SiteHost.status != "removed")).first():
            n += 1
            cand = f"{base}-{n}"
    return f"{cand}.{c['base']}"


# ---------------------------------------------------------------- serving (middleware)
def host_map(force: bool = False) -> dict[str, dict[str, Any]]:
    with _MAP_LOCK:
        if not force and time.time() - _MAP["at"] < 20:
            return _MAP["hosts"]
        hosts: dict[str, dict[str, Any]] = {}
        try:
            with session() as s:
                for h in s.scalars(select(SiteHost).where(SiteHost.status.in_(("active", "pending")),
                                                          SiteHost.live_version > 0)).all():
                    hosts[h.hostname] = {"site": h.site_id, "role": h.role, "tenant": h.tenant_id}
        except Exception:
            log.debug("host map failed", exc_info=True)
        main = {v["site"]: k for k, v in hosts.items() if v["role"] == "main"}
        for k, v in hosts.items():
            v["main"] = main.get(v["site"], k)
        _MAP.update(at=time.time(), hosts=hosts)
    if force:
        _edge_sync(hosts)
    return hosts


def _edge_sync(hosts: dict[str, dict[str, Any]]) -> None:
    """v0.224 the folder nginx serves from follows every launch / rollback / take-down at once."""
    try:
        from . import edge
        edge.sync(hosts)
    except Exception:
        log.exception("edge sync failed")


BOTS = re.compile(r"hoolauptime|bot\b|bot/|crawl|spider|slurp|lighthouse|headlesschrome|python-httpx|python-requests|"
                  r"curl/|wget/|uptime|monitor|preview|facebookexternalhit|whatsapp", re.I)


def is_bot(ua: str) -> bool:
    """v0.223 Hoola's own uptime check (every 5 min = ~288 'visits' a day per address) and crawlers are not her visitors."""
    return bool(BOTS.search(ua or ""))


def serve(host: str, path: str, ua: str = "", inm: str = "") -> tuple[int, bytes, str, dict[str, str]] | None:
    """(status, body, content type, headers) for a hosted site, or None when this host is not one of ours."""
    host = (host or "").lower().split(":")[0].strip(".")
    m = host_map().get(host)
    if not m:
        return None
    if m["role"] == "apex" and m["main"] != host:
        return 301, b"", "text/plain", {"Location": f"https://{m['main']}{path or '/'}"}
    root = hosted_root() / host
    if not root.exists():
        root = hosted_root() / m["main"]
    rel = (path or "/").split("?")[0].lstrip("/")
    f = root / rel
    if not rel or rel.endswith("/"):
        f = f / "index.html"
    try:
        f = f.resolve()
        f.relative_to(root.resolve())
    except (ValueError, OSError):
        return 404, b"not found", "text/plain", {}
    if f.is_dir():
        if not (path or "").endswith("/"):
            return 301, b"", "text/plain", {"Location": (path or "/") + "/"}
        f = f / "index.html"
    if not f.is_file() or f.name == "_headers":
        nf = root / "404.html"
        if not is_bot(ua):
            _count(m, path, 404)
        return 404, (nf.read_bytes() if nf.exists() else b"not found"), "text/html; charset=utf-8", _sec_headers(m)
    ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    if f.suffix == ".avif":
        ctype = "image/avif"
    if f.suffix == ".woff2":
        ctype = "font/woff2"
    if ctype.startswith("text/") or ctype in ("application/javascript", "image/svg+xml", "application/xml"):
        ctype += "; charset=utf-8"
    h = _sec_headers(m)
    h["Cache-Control"] = "public, max-age=604800" if "/assets/" in f.as_posix() else "public, max-age=300, must-revalidate"
    if ctype.startswith("text/html") and not is_bot(ua):
        _count(m, path, 200)
    st = f.stat()
    etag = f'"{st.st_mtime_ns:x}-{st.st_size:x}"'      # v0.224 repeat visits get 304 instead of the whole file
    h["ETag"] = etag
    if inm and etag in [x.strip() for x in inm.split(",")]:
        return 304, b"", ctype, h
    return 200, f.read_bytes(), ctype, h


def _count(m: dict[str, Any], path: str, status: int) -> None:
    """v0.124 page views for her care note: site + page + day only (no IP, no cookie, no tracker)."""
    try:
        from . import care
        care.count_view(m.get("site", ""), m.get("tenant", ""), path, status)
    except Exception:
        log.debug("count failed", exc_info=True)


def _sec_headers(m: dict[str, Any]) -> dict[str, str]:
    from . import service as S
    base = (_st().public_base_url or "").rstrip("/")
    h = dict(B.security_headers(base + "/api/site-forms/x" if base else ""))
    h["Strict-Transport-Security"] = "max-age=31536000"
    return h


# ---------------------------------------------------------------- launch (her tap)
def _live_hash(r: Site, hosts: list[str]) -> str:
    vdir = B.out_dir(r.tenant_id, r.id, r.version)
    fp = B.fingerprint(vdir) if vdir.exists() else ""
    return hashlib.sha256(f"{r.id}|{r.version}|{','.join(sorted(hosts))}|{fp}".encode()).hexdigest()[:16]


def _hosts_of(r: Site, include_pending: bool = True) -> list[SiteHost]:
    with session() as s:
        q = select(SiteHost).where(SiteHost.site_id == r.id, SiteHost.status != "removed")
        rows = s.scalars(q).all()
        for x in rows:
            s.expunge(x)
    return [x for x in rows if include_pending or x.status == "active"]


def blockers(r: Site) -> list[str]:
    chk = _j(r.checks, {})
    out = [b["text"] for b in chk.get("blocking", [])]
    blanks = (chk.get("scores") or {}).get("blanks", 0)
    if blanks:
        out.append(f"{blanks} jagah [blank] baaki hai (phone / daam / naam jo pata nahi tha); pehle bata dijiye")
    if r.status != "ready":
        out.append(f"website abhi '{r.status}' hai")
    if not r.version:
        out.append("abhi koi version nahi bana")
    return out


def launch_request(tenant: str, ref: str, free: bool = True, conv: str = "") -> dict[str, Any]:
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    hosts = [h.hostname for h in _hosts_of(r) if h.kind == "custom"]
    if free or not hosts:
        try:
            hosts.append(free_host(r))
        except HostError as e:
            if not hosts:
                raise
            log.info("no free host: %s", e)
    blk = blockers(r)
    card = {"site": S.view(r, False), "hosts": hosts, "version": r.version, "blockers": blk, "hash": _live_hash(r, hosts),
            "scores": _j(r.scores, {}), "preview": S.preview_url(r), "kind": "launch",
            "say": ("Live karne se pehle: " + "; ".join(blk[:3])) if blk else
                   f"v{r.version} ko {', '.join(hosts)} par live karein? Aapki haan chahiye."}
    _publish(tenant, "site_launch", {**card, "push": not blk}, conv or r.conv)
    return card


def launch(tenant: str, ref: str, hash_: str, free: bool = True) -> dict[str, Any]:
    """ONLY from her tap (API). Publishes the checked version to its hosts."""
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    blk = blockers(r)
    if blk:
        raise HostError("Live nahi kar sakte: " + "; ".join(blk[:4]))
    hosts = [h.hostname for h in _hosts_of(r) if h.kind == "custom"]
    if free or not hosts:
        hosts.append(free_host(r))
    if hash_ != _live_hash(r, hosts):
        raise HostError("Website card ke baad badal gayi; naya 'live karo' card dekhiye.")
    main = _main_host(r, hosts)
    _publish_files(r, main, r.version)
    with session() as s:
        for h in hosts:
            row = s.scalars(select(SiteHost).where(SiteHost.hostname == h, SiteHost.status != "removed")).first()
            kind = "custom" if not (cfg()["base"] and h.endswith("." + cfg()["base"])) else "free"
            if row is None:
                row = SiteHost(tenant_id=tenant, site_id=r.id, hostname=h, kind=kind,
                               role="main" if h == main else ("apex" if kind == "custom" and h.count(".") == 1 else "www"))
                s.add(row)
            row.live_version = r.version
            row.launched_at = now()
            if row.kind == "free":
                row.status = "active"
        site = s.get(Site, r.id)
        site.stage = "launch" if any(_is_pending(h) for h in hosts) else "care"
    host_map(force=True)
    for h in hosts:
        if h != main:
            _link(main, h)
    from .library import learn
    learn(r.field, "section", [x["type"] for p in _j(r.plan, {}).get("pages", []) for x in p.get("sections", [])])
    url = f"https://{main}/"
    out = {"ok": True, "url": url, "hosts": hosts, "version": r.version,
           "say": f"Live! {url} (v{r.version})." + (" Aapke domain par DNS / SSL poora hote hi wahan bhi khulegi." if any(
               _is_pending(h) for h in hosts) else "")}
    _publish(tenant, "site_live", {**out, "site": S.view(S._load(r.id), False)}, r.conv)
    return out


def _is_pending(hostname: str) -> bool:
    with session() as s:
        h = s.scalars(select(SiteHost).where(SiteHost.hostname == hostname, SiteHost.status != "removed")).first()
        return bool(h and h.status == "pending")


def _main_host(r: Site, hosts: list[str]) -> str:
    custom_www = [h for h in hosts if h.startswith("www.")]
    custom = [h for h in hosts if not (cfg()["base"] and h.endswith("." + cfg()["base"]))]
    return (custom_www or custom or hosts)[0]


def _publish_files(r: Site, host: str, version: int) -> None:
    """Rebuild the version for the live address (canonical, sitemap, indexable) and swap it in atomically."""
    from . import service as S
    ctx = S._ctx(r)
    ctx["noindex"] = False
    secs = S._sections(r)
    root = hosted_root()
    tmp = root / f".{host}.new"
    old = root / f".{host}.old"
    live = root / host
    photos = {p["name"]: p for p in _j(r.photos, [])}
    # the sections of this version are the current sources; for older versions copy that version's files
    if version == r.version:
        B.assemble(ctx, ctx["plan"], secs, photos, tmp, f"https://{host}", S.form_endpoint(r))
    else:
        src = B.out_dir(r.tenant_id, r.id, version)
        if not src.exists():
            raise HostError(f"v{version} ab nahi hai (sirf aakhri 20 rakhe jaate hain).")
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(src, tmp)
        _make_indexable(tmp, f"https://{host}")
    if old.exists():
        shutil.rmtree(old)
    if live.exists() and not live.is_symlink():
        live.rename(old)
    elif live.is_symlink():
        live.unlink()
    tmp.rename(live)


def _make_indexable(out: Path, base_url: str) -> None:
    for f in out.rglob("*.html"):
        t = f.read_text(encoding="utf-8")
        t = t.replace('<meta name="robots" content="noindex">', "")
        f.write_text(t, encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n")


def _link(main: str, other: str) -> None:
    """Other hosts of the same site serve the same files (apex redirects to main in `serve`)."""
    root = hosted_root()
    p = root / other
    if p.is_symlink() or p.exists():
        if p.is_symlink():
            p.unlink()
        else:
            shutil.rmtree(p)
    try:
        p.symlink_to(main, target_is_directory=True)        # v0.224 relative: survives a move / a backup restore
    except OSError:
        shutil.copytree(root / main, p)


def rollback_request(tenant: str, ref: str, version: int, conv: str = "") -> dict[str, Any]:
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
        ok = s.scalars(select(SiteVersion).where(SiteVersion.site_id == r.id, SiteVersion.version == int(version))).first()
    if not ok or not B.out_dir(tenant, r.id, int(version)).exists():
        raise HostError(f"v{version} nahi mila.")
    live = [h for h in _hosts_of(r) if h.live_version]
    if not live:
        raise HostError("Website abhi live nahi hai.")
    h = hashlib.sha256(f"rollback|{r.id}|{version}|{live[0].live_version}".encode()).hexdigest()[:16]
    card = {"kind": "rollback", "site": S.view(r, False), "version": int(version), "from": live[0].live_version,
            "hosts": [x.hostname for x in live], "hash": h,
            "say": f"Live site v{live[0].live_version} se v{version} par wapas karein? Aapki haan chahiye."}
    _publish(tenant, "site_launch", {**card, "push": True}, conv or r.conv)
    return card


def rollback(tenant: str, ref: str, version: int, hash_: str) -> dict[str, Any]:
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    live = [h for h in _hosts_of(r) if h.live_version]
    if not live:
        raise HostError("Website abhi live nahi hai.")
    h = hashlib.sha256(f"rollback|{r.id}|{version}|{live[0].live_version}".encode()).hexdigest()[:16]
    if h != hash_:
        raise HostError("Card purana ho gaya; naya dekhiye.")
    main = _main_host(r, [x.hostname for x in live])
    _publish_files(r, main, int(version))
    with session() as s:
        for x in s.scalars(select(SiteHost).where(SiteHost.site_id == r.id, SiteHost.status != "removed")).all():
            x.live_version = int(version)
    host_map(force=True)
    out = {"ok": True, "version": int(version), "say": f"Live site ab v{version} hai (wapas kar diya)."}
    _publish(tenant, "site_live", {**out, "url": f"https://{main}/", "site": S.view(S._load(r.id), False)}, r.conv)
    return out


def has_hosts(site_id: str) -> bool:
    with session() as s:
        return s.scalars(select(SiteHost).where(SiteHost.site_id == site_id, SiteHost.status != "removed")).first() is not None


class _Gone:
    """A removed address, copied out of its session (its row's status change commits)."""
    def __init__(self, hostname: str, cf_id: str):
        self.hostname, self.cf_id = hostname, cf_id


def _drop_host(row: "_Gone | SiteHost", files: bool = True) -> None:
    """v0.223 one address leaves for good: its Cloudflare custom hostname (quota / bill) and its served files.
    Caller marks the row removed in its own session. files=False when another live address may still point at
    this folder (the free address is a link to the main one)."""
    if row.cf_id and saas_on():
        try:
            from .cf import Cloudflare
            Cloudflare(cfg()["cf_token"]).custom_hostname_delete(cfg()["cf_zone"], row.cf_id)
        except Exception:
            log.info("custom hostname delete failed", exc_info=True)
    if not files:
        return
    p = hosted_root() / row.hostname
    if p.is_symlink():
        p.unlink()
    elif p.exists():
        shutil.rmtree(p, ignore_errors=True)


def take_down(tenant: str, ref: str) -> dict[str, Any]:
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        rows = s.scalars(select(SiteHost).where(SiteHost.site_id == r.id, SiteHost.status != "removed")).all()
        names = [x.hostname for x in rows]
        drop = [_Gone(x.hostname, x.cf_id or "") for x in rows]     # plain copies: the status change must commit
        for x in rows:
            x.status = "removed"
    for x in drop:
        _drop_host(x)
    host_map(force=True)
    return {"ok": True, "say": f"Website band kar di ({', '.join(names)})." if names else "Website kahin live nahi thi."}


# ---------------------------------------------------------------- her own domain
def connect_domain(tenant: str, ref: str, domain: str, conv: str = "") -> dict[str, Any]:
    """Her domain -> pending hosts + the DNS plan card (applied only on her tap)."""
    from . import service as S
    from .cf import CfError, Cloudflare
    from .guard import name_problem
    d = D.norm_domain(domain)
    bad = name_problem(d.split(".")[0])
    if bad:
        raise HostError(bad)
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
        taken = s.scalars(select(SiteHost).where(SiteHost.hostname.in_((d, f"www.{d}")), SiteHost.status != "removed",
                                                 SiteHost.site_id != r.id)).first()
    if taken:
        raise HostError(f"{d} pehle se ek doosri Hoola website se juda hai.")
    loc = D.where_is(tenant, d)
    c = cfg()
    apex_ok = loc["provider"] == "cloudflare" or (loc["provider"] == "porkbun" and saas_on())   # Porkbun: ALIAS at the apex
    verify: list[dict[str, Any]] = []
    rows: list[SiteHost] = []
    names = [f"www.{d}"] + ([d] if apex_ok else [])
    if saas_on():
        mode, target = "saas", c["origin"]
        cf = Cloudflare(c["cf_token"])
        for n in names:
            try:
                ch = cf.custom_hostname_find(c["cf_zone"], n) or cf.custom_hostname_create(c["cf_zone"], n)
            except CfError as e:
                raise HostError(f"Hoola Hosting mein {n} nahi jud paya: {e}")
            ov = ch.get("ownership_verification") or {}
            if ov.get("name") and ov.get("value"):
                verify.append({"type": ov.get("type", "txt").upper(), "name": ov["name"], "value": ov["value"],
                               "why": "Cloudflare ko dikhana ki domain aapka hai"})
            for vr in (ch.get("ssl") or {}).get("validation_records") or []:
                if vr.get("txt_name") and vr.get("txt_value"):
                    verify.append({"type": "TXT", "name": vr["txt_name"], "value": vr["txt_value"], "why": "SSL (https) jaanch"})
            rows.append(SiteHost(tenant_id=tenant, site_id=r.id, hostname=n, kind="custom",
                                 role="main" if n.startswith("www.") else "apex", status="pending", cf_id=ch.get("id", ""),
                                 ssl_status=(ch.get("ssl") or {}).get("status", ""), verify=json.dumps(verify)))
    elif loc["provider"] == "cloudflare" and c["origin_ip"]:
        mode, target = "proxy", c["origin_ip"]
        for n in names:
            rows.append(SiteHost(tenant_id=tenant, site_id=r.id, hostname=n, kind="custom",
                                 role="main" if n.startswith("www.") else "apex", status="pending"))
    else:
        raise HostError("Aapka domain jodne ke liye: ya to server par Hoola Hosting (Cloudflare for SaaS) chalu ho, ya domain "
                        "ka DNS aapke apne Cloudflare account mein ho aur uska token Hoola mein juda ho (Website > Hosting).")
    keep = {x.hostname for x in rows}
    gone: list[_Gone] = []
    with session() as s:
        for old in s.scalars(select(SiteHost).where(SiteHost.site_id == r.id, SiteHost.kind == "custom",
                                                    SiteHost.status != "removed")).all():
            old.status = "removed"
            if not (old.hostname in keep and old.cf_id and any(x.cf_id == old.cf_id for x in rows)):
                gone.append(_Gone(old.hostname, old.cf_id or ""))
        for x in rows:
            s.add(x)
    for x in gone:          # v0.223 the old domain's Cloudflare hostname goes too (it stayed, costing quota)
        _drop_host(x, files=False)
    host_map(force=True)
    desired = D.website_records(d, mode, target, verify, apex_flatten=apex_ok)
    try:
        pl = D.make_plan(tenant, r.id, d, desired, "website")
    except D.DnsError as e:
        raise HostError(str(e))
    card = {"kind": "dns", "site": S.view(r, False), "domain": d, "plan": pl, "mode": mode,
            "say": (f"{d} ke liye {pl['todo']} DNS badlav: aapki haan par Hoola laga dega." if pl["provider"] in ("cloudflare", "porkbun")
                    else f"{d} ke liye yeh {pl['todo']} records apne domain ki company ki site par daaliye (steps card mein).")}
    if not apex_ok:
        card["say"] += f" Bina www wala {d} kholne ke liye apni domain company mein '{d} -> www.{d}' forwarding laga dijiye."
    _publish(tenant, "site_dns", {**card, "push": True}, conv or r.conv)
    return card


def dns_apply(tenant: str, plan_id: str, hash_: str) -> dict[str, Any]:
    out = D.apply(tenant, plan_id, hash_)
    p = D.get_plan(tenant, plan_id)
    _publish(tenant, "site_dns", {"kind": "dns_done", "plan": D.view(p), "say": out["say"], "push": False})
    return out


# ---------------------------------------------------------------- watching (worker)
def watch(tenant: str = "") -> int:
    """Pending custom hosts -> active when DNS + SSL are ready; active hosts -> uptime. Returns hosts checked."""
    n = 0
    with session() as s:
        q = select(SiteHost).where(SiteHost.status.in_(("pending", "active")), SiteHost.live_version > 0)
        if tenant:
            q = q.where(SiteHost.tenant_id == tenant)
        rows = s.scalars(q).all()
        for x in rows:
            s.expunge(x)
    for h in rows:
        last = h.last_check.replace(tzinfo=h.last_check.tzinfo or timezone.utc) if h.last_check else None
        gap = 60 if h.status == "pending" else 300
        if last and (datetime.now(timezone.utc) - last).total_seconds() < gap:
            continue
        n += 1
        try:
            if h.status == "pending":
                _check_pending(h)
            else:
                _check_up(h)
        except Exception:
            log.exception("host watch failed for %s", h.hostname)
    return n


def _check_pending(h: SiteHost) -> None:
    from .cf import CfError, Cloudflare
    st, ssl_st, prob = "pending", h.ssl_status, ""
    if h.cf_id and saas_on():
        try:
            ch = Cloudflare(cfg()["cf_token"]).custom_hostname_get(cfg()["cf_zone"], h.cf_id)
            ssl_st = (ch.get("ssl") or {}).get("status", "")
            if ch.get("status") == "active" and ssl_st == "active":
                st = "active"
            else:
                errs = (ch.get("verification_errors") or []) + [e.get("message", "") for e in (ch.get("ssl") or {}).get("validation_errors") or []]
                prob = "; ".join(str(e) for e in errs if e)[:300]
        except CfError as e:
            prob = str(e)
    else:
        if _fetch_ok(h.hostname):
            st = "active"
    with session() as s:
        row = s.get(SiteHost, h.id)
        row.status, row.ssl_status, row.problem, row.last_check = st, ssl_st, prob, now()
    if st == "active":
        host_map(force=True)
        _publish(h.tenant_id, "site_live", {"ok": True, "url": f"https://{h.hostname}/", "hosts": [h.hostname],
                                            "say": f"{h.hostname} par website khul gayi (https ke saath)."})


def _fetch_ok(host: str) -> bool:
    try:
        with httpx.Client(timeout=12, follow_redirects=True, transport=_TRANSPORT) as c:
            r = c.get(f"https://{host}/", headers={"User-Agent": "HoolaUptime/1.0"})
        return r.status_code == 200 and 'name="generator" content="Hoola"' in r.text
    except Exception:
        return False


def _check_up(h: SiteHost) -> None:
    _record(h, _fetch_ok(h.hostname))


def _record(h: SiteHost, ok: bool, why: str = "", source: str = "inside") -> None:
    """One uptime answer for an address (Hoola's own check every 5 min, or the outside checker). Two misses in a row =
    one card + push; back up = one note."""
    if h.role == "main":
        try:
            from . import care
            care.count_check(h.site_id, h.tenant_id, ok)
        except Exception:
            log.debug("care check count failed", exc_info=True)
    with session() as s:
        row = s.get(SiteHost, h.id)
        row.last_check = now()
        back = False
        if ok:
            back = row.down_told
            row.fails, row.down_told, row.problem = 0, False, ""
        else:
            row.fails = (row.fails or 0) + 1
            row.problem = why or "site nahi khuli (DNS / SSL / server)"
        fails, told = row.fails, row.down_told
        if not ok and fails >= 2 and not told:
            row.down_told = True
    if not ok and fails >= 2 and not told:
        why = why or _why_down(h.hostname)
        where = " (bahar se jaanch)" if source == "outside" else ""
        _publish(h.tenant_id, "site_down", {"host": h.hostname, "say": f"{h.hostname} nahi khul rahi{where}: {why}", "push": True})
    elif ok and back:
        _publish(h.tenant_id, "site_down", {"host": h.hostname, "ok": True, "say": f"{h.hostname} phir se chal rahi hai.", "push": False})


# ---------------------------------------------------------------- v0.224 the outside checker (GitHub Actions, off this box)
def uptime_key_ok(key: str) -> bool:
    import hmac
    want = getattr(_st(), "sites_uptime_key", "") or ""
    return bool(want) and len(want) >= 16 and hmac.compare_digest(want, key or "")


def uptime_targets() -> list[str]:
    """The live addresses the outside checker should open (main + www only; nothing about her)."""
    with session() as s:
        rows = s.scalars(select(SiteHost).where(SiteHost.status == "active", SiteHost.live_version > 0)).all()
        return sorted({x.hostname for x in rows if x.role != "apex"})


def outside_report(results: list[dict[str, Any]]) -> int:
    """What the outside checker saw (ok / status / error per address). Same counters and cards as Hoola's own check;
    the outside view also sees the times this whole server was down. Unknown addresses are ignored."""
    n = 0
    seen = set()
    for r in results[:500]:
        host = str(r.get("host") or "").lower().strip(".")
        if not host or host in seen:
            continue
        seen.add(host)
        with session() as s:
            h = s.scalars(select(SiteHost).where(SiteHost.hostname == host, SiteHost.status == "active")).first()
            if h is None:
                continue
            s.expunge(h)
        ok = bool(r.get("ok"))
        why = "" if ok else re_clean(f"HTTP {r.get('status') or '-'} {r.get('error') or ''}")
        _record(h, ok, why, source="outside")
        n += 1
    return n


def re_clean(t: str) -> str:
    return re.sub(r"[^\w .:/()-]+", "", t).strip()[:120]


def _why_down(host: str) -> str:
    a = D.lookup(host, "A")
    cn = D.lookup(host, "CNAME")
    if not any(v and v != ["?"] for v in list(a.values()) + list(cn.values())):
        return "DNS mein iska record nahi mil raha (domain expire / record hata?)"
    days = ssl_days(host)
    if days is not None and days < 0:
        return "SSL certificate khatam ho gaya"
    return "server jawab nahi de raha; Hoola dekh raha hai"


def ssl_days(host: str) -> int | None:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                exp = ss.getpeercert()["notAfter"]
        dt = datetime.strptime(exp, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        return (dt - datetime.now(timezone.utc)).days
    except Exception:
        return None


def status(tenant: str, ref: str) -> dict[str, Any]:
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    hs = _hosts_of(r)
    return {"hosts": [{"host": h.hostname, "kind": h.kind, "role": h.role, "status": h.status, "ssl": h.ssl_status,
                       "live_version": h.live_version, "problem": h.problem,
                       "launched_at": h.launched_at.isoformat() if h.launched_at else ""} for h in hs],
            "dns": D.plans(tenant, r.id, 10), "saas": saas_on(), "free_base": cfg()["base"],
            "keys": D.keys(tenant)}
