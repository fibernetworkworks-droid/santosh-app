"""v0.224 Hosted websites served by nginx itself, so a Hoola restart / deploy / crash no longer takes every customer site down.

Before: every visitor's request went through Hoola's own Python process (`hosting.serve` in the HTTP middleware). Each pm2
restart (14 in 5 hours during the memory spiral) made every live website unreachable for the restart.

Now:
  * `sync()` keeps an "enabled" folder: one symlink per address that may be served (active / pending with a live version),
    pointing at that site's published folder in data/hosted. Taken-down, deleted or re-joined addresses vanish from it.
    nginx serves `root <enabled>/$host` - no reload is ever needed when a site goes live or comes down.
  * `nginx_conf()` writes the server block (`python -m app.site.edge conf`). Security headers match `build.security_headers`,
    the apex of her domain redirects to www, only `/api/site-forms/` reaches Hoola, every other `/api/` is 404, and a host
    nginx does not know falls back to Hoola (which still serves it the old way).
  * Visits: nginx writes a small access log only for requests it served from the enabled folder; `ingest_log()` (worker)
    reads the new lines and counts HTML pages (bots and Hoola's uptime check are skipped) - same counters as before.
Python serving stays as the fallback (no nginx, or a host not yet synced)."""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.site")
LOG_FORMAT = "hoola_sites"
FIELDS = ("host", "status", "method", "uri", "ctype", "ua")


def _beside_hosted(name: str) -> Path:
    from . import hosting as H
    return H.hosted_root().parent / name


def enabled_root() -> Path:
    p = Path(os.environ.get("SITE_ENABLED_DIR") or _beside_hosted("hosted_enabled"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def access_log() -> Path:
    return Path(os.environ.get("SITE_ACCESS_LOG") or _beside_hosted("hosted_access.log"))


def _state_file() -> Path:
    return access_log().with_suffix(".offset")


# ---------------------------------------------------------------- the enabled folder
def sync(hosts: dict[str, dict[str, Any]] | None = None) -> dict[str, int]:
    """Make <enabled>/<host> -> <hosted>/<folder> exactly for the addresses that may be served. Apex addresses are left
    out on purpose: nginx sends them to www. Returns counts (added / removed / kept)."""
    from . import hosting as H
    if hosts is None:
        hosts = H.host_map()
    root = enabled_root()
    hosted = H.hosted_root().resolve()
    want: dict[str, Path] = {}
    for host, m in hosts.items():
        if m.get("role") == "apex" and m.get("main") != host:
            continue
        if not re.fullmatch(r"[a-z0-9.-]{1,253}", host) or ".." in host:
            continue
        folder = hosted / host
        if not folder.exists():
            folder = hosted / m.get("main", host)
        if folder.exists():
            want[host] = folder.resolve()
    out = {"added": 0, "removed": 0, "kept": 0}
    for p in root.iterdir():
        if p.name.startswith("."):
            continue
        if p.name not in want:
            if p.is_symlink() or p.is_file():
                p.unlink()
            out["removed"] += 1
    for host, target in want.items():
        p = root / host
        if p.is_symlink() and Path(os.readlink(p)) == target:
            out["kept"] += 1
            continue
        tmp = root / f".{host}.tmp"
        if tmp.is_symlink() or tmp.exists():
            tmp.unlink()
        tmp.symlink_to(target, target_is_directory=True)
        os.replace(tmp, p)            # atomic: nginx never sees the address missing
        out["added"] += 1
    return out


# ---------------------------------------------------------------- nginx server block
def _headers(base_url: str) -> list[tuple[str, str]]:
    from . import build as B
    h = B.security_headers(base_url.rstrip("/") + "/api/site-forms/x" if base_url else "")
    h["Strict-Transport-Security"] = "max-age=31536000"
    return list(h.items())


def nginx_conf(base_url: str = "", app: str = "http://127.0.0.1:8077", enabled: str = "", access: str = "",
               cert: str = "/etc/ssl/hoolasites-origin.pem", key: str = "/etc/ssl/hoolasites-origin.key",
               listen_http: str = "80", listen_https: str = "443", ssl: bool = True) -> str:
    """The default_server block for website hosts. The API host keeps its own server block (nginx-santosh.conf)."""
    from ..config import get_settings
    base_url = base_url or (get_settings().public_base_url or "")
    enabled = enabled or str(enabled_root().resolve())
    access = access or str(access_log().resolve())
    hdr = "\n".join(f'        add_header {k} "{v}" always;' for k, v in _headers(base_url))
    proxy = f"            proxy_pass {app};"     # headers are set once for the whole server (not allowed inside 'if')
    tls = (f"    listen {listen_https} ssl default_server;\n    ssl_certificate     {cert};\n    ssl_certificate_key {key};\n"
           if ssl else "")
    return f"""# Hoola hosted websites (v0.224) - generated by `python -m app.site.edge conf`. Put this in http {{ }}.
log_format {LOG_FORMAT} '$host\\t$status\\t$request_method\\t$request_uri\\t$sent_http_content_type\\t$http_user_agent';

server {{
    listen {listen_http} default_server;
{tls}    server_name _;
    client_max_body_size 1m;
    root {enabled}/$host;
    index index.html;
    server_tokens off;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    gzip on;
    gzip_types text/css application/javascript image/svg+xml application/xml text/plain application/json;

    # served by nginx itself only when the address is live in the enabled folder
    set $hoola_live 0;
    if (-d {enabled}/$host) {{ set $hoola_live 1; }}
    # the bare domain of her site goes to www (its www is live, the bare one is not in the folder)
    set $hoola_apex "$hoola_live";
    if (-d {enabled}/www.$host) {{ set $hoola_apex "${{hoola_apex}}w"; }}
    if ($hoola_apex = "0w") {{ return 301 https://www.$host$request_uri; }}
    access_log {access} {LOG_FORMAT} if=$hoola_live;

    # her enquiry form is the only part of Hoola a site address reaches
    location ^~ /api/site-forms/ {{
{proxy}
    }}
    location ^~ /api/ {{
        if ($hoola_live = 0) {{
{proxy}
        }}
        return 404;
    }}
    location = /_headers {{ return 404; }}
    location ^~ /assets/ {{
        if ($hoola_live = 0) {{
{proxy}
        }}
{hdr}
        add_header Cache-Control "public, max-age=604800" always;
        try_files $uri =404;
    }}
    location / {{
        if ($hoola_live = 0) {{
{proxy}
        }}
        if (-d $request_filename) {{ rewrite [^/]$ $uri/ permanent; }}
{hdr}
        add_header Cache-Control "public, max-age=300, must-revalidate" always;
        try_files $uri $uri/index.html =404;
    }}
    error_page 404 /404.html;
    location = /404.html {{
{hdr}
        internal;
    }}
}}
"""


# ---------------------------------------------------------------- visits from nginx's log
def _is_page(uri: str, ctype: str) -> bool:
    if ctype:
        return ctype.lower().startswith("text/html")
    last = uri.rsplit("/", 1)[-1]
    return not last or last.endswith(".html") or "." not in last


def ingest_log(limit_bytes: int = 8 * 1024 * 1024) -> int:
    """Count the HTML pages nginx served since the last read (bots / uptime checks skipped). Survives log rotation:
    a log smaller than the saved offset, or a different file, starts again from 0. Returns pages counted."""
    from . import care
    from . import hosting as H
    path = access_log()
    if not path.exists():
        return 0
    st = path.stat()
    sf = _state_file()
    try:
        saved = json.loads(sf.read_text())
    except (OSError, ValueError):
        saved = {}
    off = int(saved.get("offset") or 0)
    if saved.get("inode") != st.st_ino or off > st.st_size:
        off = 0
    hosts = H.host_map()
    counted = 0
    with path.open("rb") as f:
        f.seek(off)
        chunk = f.read(limit_bytes)
    end = chunk.rfind(b"\n")
    if end < 0:
        return 0
    chunk = chunk[:end + 1]
    for raw in chunk.splitlines():
        parts = raw.decode("utf-8", "replace").split("\t")
        if len(parts) < len(FIELDS):
            continue
        row = dict(zip(FIELDS, parts))
        if row["method"] not in ("GET", "HEAD") or H.is_bot(row["ua"]):
            continue
        try:
            status = int(row["status"])
        except ValueError:
            continue
        row["uri"] = row["uri"].split("?", 1)[0]
        if status not in (200, 404) or not _is_page(row["uri"], row["ctype"]):
            continue
        m = hosts.get(row["host"].lower())
        if not m:
            continue
        care.count_view(m.get("site", ""), m.get("tenant", ""), row["uri"], status)
        counted += 1
    sf.write_text(json.dumps({"offset": off + len(chunk), "inode": st.st_ino}))
    return counted


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("conf", "sync"):
        print("usage: python -m app.site.edge conf [--no-ssl] [--app http://127.0.0.1:8077] [--cert PATH --key PATH] | sync")
        return 2
    if argv[0] == "sync":
        print(json.dumps(sync()))
        return 0
    kw: dict[str, Any] = {}
    it = iter(argv[1:])
    for a in it:
        if a == "--no-ssl":
            kw["ssl"] = False
        elif a in ("--app", "--cert", "--key", "--base"):
            kw[{"--app": "app", "--cert": "cert", "--key": "key", "--base": "base_url"}[a]] = next(it, "")
    print(nginx_conf(**kw))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
