"""v0.424 JODO (App Sahayak Pillar F, Phase 54): her apps talk to outside services - couriers, SMS, email, WhatsApp
Business, Google Sheets / Calendar, Zoho / QuickBooks, KYC - through DECLARED HTTP actions, never free-form code.

An ACTION is data: {key, label, method, url, headers, query, body, body_type, auth, trigger, coll, status, map, staff,
retries, per_min}. Placeholders {{row.x}} {{app.name}} {{facts.x}} {{now}} {{run.id}} {{secret.x}} fill it at run time.
  * HER APPROVAL: a new or changed action does NOTHING until she approves it; the approval is bound to a hash of the
    exact action (method, URL, what leaves, what comes back), so any change needs approving again (tested).
  * HER SECRETS: typed in the app, sealed (vault) on arrival, returned by NO route, never in a run log or an error
    (every secret value is scrubbed from what we keep).
  * WHERE IT MAY GO: https only, the host she approved, the address resolved and refused when it is private / loopback /
    link-local / metadata (no reaching into Hoola's own network), redirects not followed, 1 MB answers at most.
  * HOW OFTEN: per-action and per-app limits per minute; retries only when it is safe (GET, or the action sends an
    idempotency key); a POST that timed out is `ambiguous`, never silently sent again.
  * WHAT COMES BACK is DATA: mapped only into fields that exist on that list, through each field's own type check
    (a status only to one of its options); nothing in an answer is ever an instruction to Hoola.
  * TRIGGERS: her tap (console / phone), a staff button in the app (only if she allowed it), a new row, a status
    reached. Automatic runs are queued at once and done in the background - the customer's order never waits on a
    courier; a crash leaves the run queued and the worker picks it up.
  * INBOUND webhooks: /api/app-api/<key>/hook/<hook> with HER secret (HMAC-SHA256 hex / base64 of the body in a header
    she names, or a shared token header); the payload is data, mapped into a row matched by a field.
  * AADHAAR-FREE: an action whose URL / fields / mapping mention Aadhaar is refused (KYC only via licensed providers
    with PAN / other documents)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import re
import secrets as _secrets
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"runs": 0, "ok": 0, "failed": 0, "refused": 0, "hooks": 0, "hooks_bad": 0, "ambiguous": 0}
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
TRIGGERS = ("manual", "create", "status", "remind", "queue")   # v0.459: a time before a booking / a queue turn near
QUEUE_COLL = "_queue"                                     # v0.459 the clinic queue's tokens (site/livesite.py)
TOOL_RE = re.compile(r"[A-Z][A-Z0-9_]{2,99}")
AUTH_TYPES = ("none", "bearer", "basic", "header", "query", "login_token", "oauth_refresh", "google_sa")
MAX_ACTIONS = 40
MAX_BODY = 1_000_000
TIMEOUT = 15.0
APP_PER_MIN = 300
NO_AADHAAR = re.compile(r"aadh?aa?r|\buidai\b", re.I)
PH = re.compile(r"\{\{\s*([a-z_]+)(?:\.([A-Za-z0-9_\-]+))?\s*\}\}")

_TRANSPORT: httpx.BaseTransport | None = None
_RESOLVE = None                                           # tests: a fake resolver for the private-address guard


def set_transport(t: httpx.BaseTransport | None, resolve=None) -> None:
    global _TRANSPORT, _RESOLVE
    _TRANSPORT, _RESOLVE = t, resolve


class ConnError(W.AppError):
    pass


class AppConnSecret(Base):
    __tablename__ = "app_conn_secret"
    id: Mapped[str] = mapped_column(String(90), primary_key=True)          # app id | name
    app_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(40))
    sealed: Mapped[str] = mapped_column(Text)
    added: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AppConnRun(Base):
    __tablename__ = "app_conn_run"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    app_id: Mapped[str] = mapped_column(String(40), index=True)
    action: Mapped[str] = mapped_column(String(40))
    trigger: Mapped[str] = mapped_column(String(12))
    row_id: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(12), default="queued")    # queued | running | ok | failed | refused | ambiguous
    code: Mapped[int] = mapped_column(Integer, default=0)
    ms: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    done: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_OK = False


def ensure_tables() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        for t in (AppConnSecret, AppConnRun):
            t.__table__.create(_db._engine, checkfirst=True)
        _OK = True


def _j(s: Any, d: Any) -> Any:
    try:
        v = json.loads(s) if isinstance(s, str) and s else d
    except ValueError:
        return d
    return v if v is not None else d


def _site(r: AppProject) -> str:
    return "app:" + r.id


def _cfg(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    return dict(BE.ensure(r).get("connect") or {})


def _save(r: AppProject, fn) -> None:
    from . import backend as BE

    def go(be):
        c = dict(be.get("connect") or {})
        fn(c)
        be["connect"] = c
    BE.patch_backend(r, fn=go)


# ---------------------------------------------------------------- secrets (sealed, never returned)
def set_secret(r: AppProject, name: str, value: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", str(name or "")):
        raise ConnError("Secret name: lowercase letters / digits / _ only.", 400)
    v = str(value or "")
    if not v.strip() or len(v) > 8000:
        raise ConnError("The secret is empty or too long.", 400)
    from ..bazar.security import vault
    ensure_tables()
    with session() as s:
        x = s.get(AppConnSecret, f"{r.id}|{name}")
        if x is None:
            x = AppConnSecret(id=f"{r.id}|{name}", app_id=r.id, name=name, sealed="")
            s.add(x)
        x.sealed, x.added = vault().seal(v), now()
    return {"ok": True, "name": name}


def forget_secret(r: AppProject, name: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        x = s.get(AppConnSecret, f"{r.id}|{name}")
        if x is not None:
            s.delete(x)
    return {"ok": True}


def _secrets_of(r: AppProject) -> dict[str, str]:
    ensure_tables()
    from ..bazar.security import vault
    out: dict[str, str] = {}
    with session() as s:
        for x in s.scalars(select(AppConnSecret).where(AppConnSecret.app_id == r.id)).all():
            try:
                out[x.name] = vault().open(x.sealed)
            except Exception:                                # noqa: BLE001
                log.warning("connector secret %s could not be opened", x.name)
    return out


def _secret_names(r: AppProject) -> list[str]:
    ensure_tables()
    with session() as s:
        return sorted(x.name for x in s.scalars(select(AppConnSecret).where(AppConnSecret.app_id == r.id)).all())


# ---------------------------------------------------------------- an action: check, hash, approve
def _host_ok(host: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)+", host or "")) \
        and not host.endswith((".local", ".internal", ".localhost"))


def _clean(a: dict[str, Any], sch: dict[str, Any]) -> dict[str, Any]:
    """An action as she (or a pack) declared it -> the checked shape, or ConnError naming the problem."""
    key = str(a.get("key") or "").strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", key):
        raise ConnError("Action key: lowercase letters / digits / _ only.", 400)
    if str(a.get("kind") or "") == "composio":
        return _clean_composio(a, key, sch)
    method = str(a.get("method") or "POST").upper()
    if method not in METHODS:
        raise ConnError("Method: GET / POST / PUT / PATCH / DELETE.", 400)
    url = str(a.get("url") or "").strip()
    u = urlparse(url.replace("{{", "").replace("}}", ""))
    if u.scheme != "https" or not _host_ok((u.hostname or "").lower()) or u.username or u.password or u.port not in (None, 443):
        raise ConnError("The address must be https://<public host>/... (no user:password / port).", 400)
    if PH.search(urlparse(url).netloc or ""):
        raise ConnError("{{...}} is not allowed in the host - write the host in full.", 400)
    colls, coll, trig, status, when = _when(a, sch)
    auth = dict(a.get("auth") or {"type": "none"})
    if auth.get("type") not in AUTH_TYPES:
        raise ConnError("Auth: " + " | ".join(AUTH_TYPES), 400)
    if auth.get("type") in ("login_token", "oauth_refresh"):
        tu = urlparse(str(auth.get("url") or ""))
        if tu.scheme != "https" or not _host_ok((tu.hostname or "").lower()):
            raise ConnError("The token address must also be an https public host.", 400)
    mp = {str(k): str(v) for k, v in (a.get("map") or {}).items()}
    if mp and coll == QUEUE_COLL:
        raise ConnError("A queue token does not write a reply back (leave the map empty).", 400)
    if mp:
        if not coll:
            raise ConnError("Which list should the reply go to? (coll)", 400)
        own = {f["key"] for f in colls[coll]["fields"]}
        bad = [k for k in mp if k not in own]
        if bad:
            raise ConnError(f"These fields are not in the list: {', '.join(bad)} (add the field to the list first).", 400)
        if any(not re.fullmatch(r"\$(\.[A-Za-z0-9_\-]+|\[\d+\])*", v) for v in mp.values()):
            raise ConnError("A map path looks like $.data.awb or $.items[0].id.", 400)
    body_type = str(a.get("body_type") or "json")
    if body_type not in ("json", "form", "none"):
        raise ConnError("Body: json | form | none.", 400)
    out = {"key": key, "label": str(a.get("label") or key)[:80], "method": method, "url": url[:2000],
           "headers": {str(k)[:60]: str(v)[:2000] for k, v in (a.get("headers") or {}).items()},
           "query": {str(k)[:60]: v for k, v in (a.get("query") or {}).items()},
           "body": a.get("body"), "body_type": body_type, "auth": auth, "trigger": trig, "coll": coll, "status": status,
           "map": mp, "staff": bool(a.get("staff")), "retries": max(0, min(3, int(a.get("retries") or 0))),
           "per_min": max(1, min(600, int(a.get("per_min") or 30))), "idem": str(a.get("idem") or "")[:60],
           "pack": str(a.get("pack") or "")[:30], "note": str(a.get("note") or "")[:300], **when}
    if NO_AADHAAR.search(json.dumps({k: out[k] for k in ("url", "headers", "query", "body", "map")}, default=str)):
        raise ConnError("Hoola does not run Aadhaar connectors - do KYC with PAN / another document through a licensed provider.", 400)
    if len(json.dumps(out, default=str)) > 30000:
        raise ConnError("The action is too large.", 400)
    return out


def _when(a: dict[str, Any], sch: dict[str, Any]) -> tuple[dict[str, Any], str, str, str, dict[str, Any]]:
    """The list + the moment an action runs: (lists, coll, trigger, status, extra keys for remind)."""
    colls = {c["key"]: c for c in sch.get("collections") or []}
    coll = str(a.get("coll") or "")
    trig = str(a.get("trigger") or "manual")
    if trig not in TRIGGERS:
        raise ConnError("Trigger: " + " | ".join(TRIGGERS) + ".", 400)
    if trig == "queue" or coll == QUEUE_COLL:           # v0.459 the clinic queue: only 'your turn is near'
        if trig != "queue" or coll not in ("", QUEUE_COLL):
            raise ConnError("A queue needs trigger 'queue' and list '_queue'.", 400)
        return colls, QUEUE_COLL, trig, "", {}
    if coll and coll not in colls:
        raise ConnError(f"List '{coll}' is not in the app.", 400)
    if trig in ("create", "status", "remind") and not coll:
        raise ConnError("An automatic action needs a list.", 400)
    status = str(a.get("status") or "")
    if trig == "status":
        opts = next((f.get("options") or [] for f in colls[coll]["fields"] if f["key"] == "status"), [])
        if status not in opts:
            raise ConnError("Choose the status from the list's options.", 400)
    when: dict[str, Any] = {}
    if trig == "remind":                                # v0.459 a reminder before a booking's date (+ time)
        own = {f["key"]: f for f in colls[coll]["fields"]}
        df, tf = str(a.get("date_field") or "date"), str(a.get("time_field") or "")
        if df not in own:
            raise ConnError(f"A reminder needs a date field ('{df}' is not in the list).", 400)
        if tf and tf not in own:
            raise ConnError(f"Time field '{tf}' is not in the list.", 400)
        try:
            before = int(a.get("before_min") or 120)
        except (TypeError, ValueError):
            raise ConnError("How many minutes before? (a number)", 400)
        if not 5 <= before <= 7 * 24 * 60:
            raise ConnError("A reminder can be from 5 minutes to 7 days before.", 400)
        when = {"date_field": df, "time_field": tf, "before_min": before}
    return colls, coll, trig, status, when


def _clean_composio(a: dict[str, Any], key: str, sch: dict[str, Any]) -> dict[str, Any]:
    """v0.459 a Composio app SHE connected (Slack, Notion, HubSpot...) as a site / app action: the tool slug + its
    arguments, filled from the row. Runs on HER Composio account only; no secrets of hers ride in the arguments."""
    toolkit = str(a.get("toolkit") or "").strip().lower()
    tool = str(a.get("tool") or "").strip().upper()
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,59}", toolkit) or not TOOL_RE.fullmatch(tool) or not tool.startswith(toolkit.upper() + "_"):
        raise ConnError("Composio: toolkit (for example slack) + that app's tool (for example SLACK_SEND_MESSAGE).", 400)
    args = a.get("args") if isinstance(a.get("args"), dict) else {}
    if any(m.group(1) == "secret" for m in PH.finditer(json.dumps(args, default=str))):
        raise ConnError("No {{secret...}} in Composio arguments - Composio holds the app's sign-in.", 400)
    colls, coll, trig, status, when = _when(a, sch)
    out = {"key": key, "kind": "composio", "label": str(a.get("label") or key)[:80], "toolkit": toolkit, "tool": tool, "args": args,
           "method": "POST", "url": "https://backend.composio.dev/" + tool.lower(), "headers": {}, "query": {}, "body": None,
           "body_type": "none", "auth": {"type": "none"}, "trigger": trig, "coll": coll, "status": status, "map": {},
           "staff": bool(a.get("staff")), "retries": 0, "per_min": max(1, min(120, int(a.get("per_min") or 20))), "idem": "",
           "pack": str(a.get("pack") or "")[:30], "note": str(a.get("note") or "")[:300], **when}
    if NO_AADHAAR.search(json.dumps(args, default=str)):
        raise ConnError("Hoola does not run Aadhaar connectors.", 400)
    if len(json.dumps(out, default=str)) > 30000:
        raise ConnError("The action is too large.", 400)
    return out


def _hash(a: dict[str, Any]) -> str:
    keep = {k: a.get(k) for k in ("method", "url", "headers", "query", "body", "body_type", "auth", "trigger", "coll", "status",
                                  "map", "staff", "idem")}
    for k in ("kind", "toolkit", "tool", "args", "date_field", "time_field", "before_min"):   # v0.459 (absent = the old hash)
        if a.get(k) not in (None, "", {}):
            keep[k] = a.get(k)
    return hashlib.sha256(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()[:16]


def what_leaves(a: dict[str, Any]) -> dict[str, Any]:
    """For her approval card: the host, and which of her data / secrets the action sends."""
    blob = json.dumps({k: a.get(k) for k in ("url", "headers", "query", "body", "args")}, default=str) + json.dumps(a.get("auth"), default=str)
    rows = sorted({m.group(2) for m in PH.finditer(blob) if m.group(1) == "row" and m.group(2)})
    secs = sorted({m.group(2) for m in PH.finditer(blob) if m.group(1) == "secret" and m.group(2)} |
                  {v for k, v in (a.get("auth") or {}).items() if k.endswith("secret") or k in ("token", "key", "password", "user")
                   if isinstance(v, str) and re.fullmatch(r"[a-z][a-z0-9_]*", v)})
    return {"host": (urlparse(a["url"]).hostname or "").lower(), "method": a["method"], "fields": rows, "secrets": secs,
            "writes_back": sorted((a.get("map") or {}).keys()), "when": a["trigger"] + (f" ({a['coll']}" + (f" -> {a['status']}" if a.get("status") else "") + ")" if a.get("coll") else "")}


def save_action(r: AppProject, a: dict[str, Any]) -> dict[str, Any]:
    """Add / change an action. It is NOT approved until her tap on the approval card (a change clears an old approval)."""
    from . import backend as BE
    act = _clean(a, BE.schema(r))

    def fn(c):
        acts = [x for x in c.get("actions") or [] if x.get("key") != act["key"]]
        if len(acts) >= MAX_ACTIONS:
            raise ConnError(f"An app cannot have more than {MAX_ACTIONS} actions.", 400)
        old = next((x for x in c.get("actions") or [] if x.get("key") == act["key"]), {})
        act["approved"] = old.get("approved") if (old.get("approved") or {}).get("hash") == _hash(act) else None
        c["actions"] = acts + [act]
    _save(r, fn)
    return status(r)


def approve(r: AppProject, key: str, her_tap: bool = False) -> dict[str, Any]:
    if not her_tap:
        raise ConnError("A connector is switched on only by your tap.", 403)

    def fn(c):
        for x in c.get("actions") or []:
            if x.get("key") == key:
                x["approved"] = {"hash": _hash(x), "at": now().isoformat()}
                return
        raise ConnError("Action not found.", 404)
    _save(r, fn)
    return status(r)


def remove_action(r: AppProject, key: str) -> dict[str, Any]:
    _save(r, lambda c: c.__setitem__("actions", [x for x in c.get("actions") or [] if x.get("key") != key]))
    return status(r)


def _action(r: AppProject, key: str) -> dict[str, Any]:
    a = next((x for x in _cfg(r).get("actions") or [] if x.get("key") == key), None)
    if a is None:
        raise ConnError("Action not found.", 404)
    return a


def _approved(a: dict[str, Any]) -> bool:
    ap = a.get("approved") or {}
    return bool(ap) and ap.get("hash") == _hash(a)


# ---------------------------------------------------------------- filling + calling
def _facts(r: AppProject) -> dict[str, Any]:
    try:
        from . import service as AS
        return dict((AS._load(r.id) or {}).get("facts") or {})
    except Exception:                                        # noqa: BLE001
        return {}


def _fill(v: Any, ctx: dict[str, dict[str, Any]], used: set[str]) -> Any:
    if isinstance(v, dict):
        return {k: _fill(x, ctx, used) for k, x in v.items()}
    if isinstance(v, list):
        return [_fill(x, ctx, used) for x in v]
    if not isinstance(v, str):
        return v
    whole = PH.fullmatch(v.strip())
    if whole:                                                # "{{row.total}}" keeps its number type
        got = _get(ctx, whole.group(1), whole.group(2), used)
        return got if got is not None else ""
    return PH.sub(lambda m: "" if _get(ctx, m.group(1), m.group(2), used) is None else str(_get(ctx, m.group(1), m.group(2), used)), v)


def _get(ctx: dict[str, Any], ns: str, key: str | None, used: set[str]) -> Any:
    if ns == "now":
        return now().isoformat()
    if ns == "today":
        return now().date().isoformat()
    space = ctx.get(ns)
    if space is None or key is None:
        return None
    if ns == "secret":
        used.add(key)
    return space.get(key)


def _path(d: Any, path: str) -> Any:
    cur = d
    for part in re.findall(r"\.([A-Za-z0-9_\-]+)|\[(\d+)\]", path[1:]):
        if part[0]:
            cur = cur.get(part[0]) if isinstance(cur, dict) else None
        else:
            i = int(part[1])
            cur = cur[i] if isinstance(cur, list) and i < len(cur) else None
        if cur is None:
            return None
    return cur


def _guard_host(host: str) -> None:
    """The address must be public: never Hoola's own machine, the VPS network or a cloud metadata service."""
    try:
        infos = (_RESOLVE or socket.getaddrinfo)(host, 443)
    except socket.gaierror:
        raise ConnError(f"Could not find the address of {host} (DNS).", 502)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ConnError(f"{host} is on a private address - Hoola does not go there.", 400)


def _http(method: str, url: str, **kw) -> httpx.Response:
    _guard_host((urlparse(url).hostname or "").lower())
    with httpx.Client(timeout=TIMEOUT, transport=_TRANSPORT, follow_redirects=False) as c:
        with c.stream(method, url, **kw) as resp:
            chunks, size = [], 0
            for ch in resp.iter_bytes():
                size += len(ch)
                if size > MAX_BODY:
                    raise ConnError("The reply is larger than 1 MB.", 502)
                chunks.append(ch)
            return httpx.Response(resp.status_code, headers=resp.headers, content=b"".join(chunks))


_TOKENS: dict[str, tuple[str, float]] = {}
_RATE: dict[str, list[float]] = {}
_RLOCK = threading.Lock()


def _token(r: AppProject, auth: dict[str, Any], sec: dict[str, str]) -> str:
    """login_token / oauth_refresh / google_sa -> a short-lived access token, cached in memory only."""
    kind = auth["type"]
    ck = hashlib.sha256(f"{r.id}|{json.dumps(auth, sort_keys=True)}".encode()).hexdigest()
    hit = _TOKENS.get(ck)
    if hit and hit[1] > time.time() + 60:
        return hit[0]
    if kind == "google_sa":
        sa = json.loads(sec.get(auth.get("secret", "google_sa"), "{}") or "{}")
        import jwt as _jwt
        t0 = int(time.time())
        assertion = _jwt.encode({"iss": sa.get("client_email"), "scope": auth.get("scope", "https://www.googleapis.com/auth/spreadsheets"),
                                 "aud": "https://oauth2.googleapis.com/token", "iat": t0, "exp": t0 + 3600},
                                sa.get("private_key", ""), algorithm="RS256")
        resp = _http("POST", "https://oauth2.googleapis.com/token",
                     data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion})
        d = resp.json() if resp.status_code < 400 else {}
        tok, ttl = d.get("access_token", ""), float(d.get("expires_in") or 3000)
    elif kind == "login_token":
        ctx = {"secret": sec}
        body = _fill(auth.get("body") or {}, ctx, set())
        resp = _http("POST", auth["url"], json=body)
        d = resp.json() if resp.status_code < 400 else {}
        tok, ttl = str(_path(d, auth.get("token_path") or "$.token") or ""), float(auth.get("ttl") or 36000)
    else:                                                    # oauth_refresh (Zoho / QuickBooks / any refresh-token grant)
        rt_name = auth.get("refresh_secret") or "refresh_token"
        form = {"grant_type": "refresh_token", "refresh_token": sec.get(rt_name, "")}
        kw: dict[str, Any] = {}
        if auth.get("client_in") == "basic":
            kw["auth"] = (sec.get(auth.get("client_id_secret") or "client_id", ""), sec.get(auth.get("client_secret_secret") or "client_secret", ""))
        else:
            form.update({"client_id": sec.get(auth.get("client_id_secret") or "client_id", ""),
                         "client_secret": sec.get(auth.get("client_secret_secret") or "client_secret", "")})
        resp = _http("POST", auth["url"], data=form, headers={"Accept": "application/json"}, **kw)
        d = resp.json() if resp.status_code < 400 else {}
        tok, ttl = d.get("access_token", ""), float(d.get("expires_in") or 3000)
        if d.get("refresh_token") and d["refresh_token"] != sec.get(rt_name):   # QuickBooks rotates it: keep the new one
            set_secret(r, rt_name, d["refresh_token"])
    if not tok:
        raise ConnError(f"No token received ({resp.status_code}) - check the key / refresh token again.", 401)
    _TOKENS[ck] = (tok, time.time() + ttl)
    return tok


def _rate_ok(key: str, per_min: int) -> bool:
    t = time.time()
    with _RLOCK:
        hits = [x for x in _RATE.get(key, []) if t - x < 60]
        if len(hits) >= per_min:
            _RATE[key] = hits
            return False
        _RATE[key] = hits + [t]
        return True


def _scrub(text: str, sec: dict[str, str]) -> str:
    out = str(text or "")
    for v in sorted((v for v in sec.values() if v and len(v) >= 4), key=len, reverse=True):
        out = out.replace(v, "•••")
    return out[:600]


def _row_ctx(r: AppProject, row_id: str) -> tuple[dict[str, Any], str]:
    if not row_id:
        return {}, ""
    with session() as s:
        x = s.get(W.SiteAppRow, row_id)
        if x is None or x.site_id != _site(r):
            raise ConnError("Entry not found.", 404)
        d = _j(x.data, {})
        coll = x.coll
    d = {k: v for k, v in d.items() if not str(k).startswith("_")}
    d["id"] = row_id
    return d, coll


def _call(r: AppProject, a: dict[str, Any], row_id: str, run_id: str) -> tuple[int, Any, str]:
    if a.get("kind") == "composio":
        return _call_composio(r, a, row_id, run_id)
    sec = _secrets_of(r)
    row, coll = _row_ctx(r, row_id)
    if a.get("coll") and row_id and coll != a["coll"]:
        raise ConnError("This entry is not from this action's list.", 400)
    ctx = {"row": row, "app": {"name": r.name or "", "id": r.id}, "facts": _facts(r), "run": {"id": run_id}, "secret": sec}
    used: set[str] = set()
    url = _fill(a["url"], ctx, used)
    if (urlparse(url).hostname or "").lower() != (urlparse(a["url"].replace("{{", "").replace("}}", "")).hostname or "").lower():
        raise ConnError("The host has changed - the action runs only on the approved host.", 400)
    headers = {k: str(_fill(v, ctx, used)) for k, v in (a.get("headers") or {}).items()}
    query = _fill(a.get("query") or {}, ctx, used)
    auth = a.get("auth") or {"type": "none"}
    t = auth.get("type")
    if t == "bearer":
        headers["Authorization"] = (auth.get("prefix") or "Bearer") + " " + sec.get(auth.get("secret") or "token", "")
    elif t == "basic":
        headers["Authorization"] = "Basic " + base64.b64encode(
            f"{sec.get(auth.get('user') or 'user', '')}:{sec.get(auth.get('password') or 'password', '')}".encode()).decode()
    elif t == "header":
        headers[auth.get("name") or "x-api-key"] = (auth.get("prefix") + " " if auth.get("prefix") else "") + sec.get(auth.get("secret") or "key", "")
    elif t == "query":
        query = dict(query, **{auth.get("name") or "key": sec.get(auth.get("secret") or "key", "")})
    elif t in ("login_token", "oauth_refresh", "google_sa"):
        headers["Authorization"] = (auth.get("prefix") or "Bearer") + " " + _token(r, auth, sec)
    if a.get("idem"):
        headers[a["idem"]] = run_id
    kw: dict[str, Any] = {"headers": headers}
    if query:
        url = url + ("&" if "?" in url else "?") + urlencode({k: ("" if v is None else v) for k, v in query.items()})
    if a["method"] != "GET" and a.get("body_type") != "none" and a.get("body") is not None:
        body = _fill(a["body"], ctx, used)
        if a.get("body_type") == "form":
            kw["data"] = {k: (json.dumps(v) if isinstance(v, (dict, list)) else ("" if v is None else str(v))) for k, v in (body or {}).items()}
        else:
            kw["json"] = body
    t0 = time.time()
    resp = _http(a["method"], url, **kw)
    ms = int((time.time() - t0) * 1000)
    try:
        data: Any = resp.json()
    except ValueError:
        data = resp.text
    return resp.status_code, data, _scrub(f"{resp.status_code} in {ms} ms", sec)


_COMPOSIO = None                                          # tests: a fake Composio client


def _call_composio(r: AppProject, a: dict[str, Any], row_id: str, run_id: str) -> tuple[int, Any, str]:
    """Her Composio account for that app (the server finds it from HER tenant, never from the action)."""
    from ..bazar import composio as cmp
    row, coll = _row_ctx(r, row_id)
    if a.get("coll") and row_id and coll != a["coll"]:
        raise ConnError("This entry is not from this action's list.", 400)
    args = _fill(a.get("args") or {}, {"row": row, "app": {"name": r.name or "", "id": r.id}, "facts": _facts(r), "run": {"id": run_id}}, set())
    client = _COMPOSIO or cmp.client()
    if _COMPOSIO is None and not cmp.configured():
        raise ConnError("Composio apps are not switched on on the server yet.", 409)
    user = cmp.composio_user(r.tenant_id)
    with session() as s:
        _, ca = cmp.account(s, user, a["toolkit"], check=_COMPOSIO is None)
        if not ca and cmp.mode(a["toolkit"]) != "no_auth":
            raise ConnError(f"{a['toolkit']} is not connected in your Hoola (Connect > Apps).", 409)
        try:
            cmp.take_call(s, user)
        except cmp.CapReached as e:
            raise ConnError(str(e), 429)
    t0 = time.time()
    try:
        res = client.execute(a["tool"], user, ca, args if isinstance(args, dict) else {})
    except cmp.ComposioError as e:
        return int(getattr(e, "status", 0) or 502), {"error": str(e)[:300]}, f"composio {a['tool']}"
    ms = int((time.time() - t0) * 1000)
    if not res.get("successful", True):
        return 422, {"error": str(res.get("error") or "")[:300]}, f"composio {a['tool']} in {ms} ms"
    return 200, res.get("data"), f"composio {a['tool']} in {ms} ms"


def _write_back(r: AppProject, a: dict[str, Any], row_id: str, data: Any) -> list[str]:
    """The answer is DATA: only into fields that exist on that list, each through its own type check."""
    if not a.get("map") or not row_id or not isinstance(data, (dict, list)):
        return []
    from . import backend as BE
    c = W.coll(BE.schema(r), a["coll"])
    fields = {f["key"]: f for f in c["fields"]}
    put: dict[str, Any] = {}
    for key, path in a["map"].items():
        v = _path(data, path)
        if v is None or isinstance(v, (dict, list)):
            continue
        try:
            put[key] = W._value(dict(fields[key], required=False), v)
        except W.AppError:
            continue                                           # a value that does not fit the field is dropped, never forced
    if put:
        BE._merge(row_id, put)
    return sorted(put)


# ---------------------------------------------------------------- runs
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="app-connect")


def run(r: AppProject, key: str, row_id: str = "", trigger: str = "manual", wait: bool = True) -> dict[str, Any]:
    a = _action(r, key)
    if not _approved(a):
        STATS["refused"] += 1
        raise ConnError("This action is not approved yet (or has changed) - your tap is needed first.", 409)
    ensure_tables()
    rid = new_id("crun")
    with session() as s:
        s.add(AppConnRun(id=rid, app_id=r.id, action=key, trigger=trigger, row_id=row_id or ""))
    if wait:
        return _do(r, rid)
    _POOL.submit(_safe_do, r, rid)
    return {"run": rid, "status": "queued"}


def _safe_do(r: AppProject, rid: str) -> None:
    try:
        _do(r, rid)
    except Exception:                                          # noqa: BLE001
        log.exception("connector run %s", rid)


def _do(r: AppProject, rid: str) -> dict[str, Any]:
    with session() as s:
        x = s.get(AppConnRun, rid)
        if x is None or x.status not in ("queued",):
            return {"run": rid, "status": x.status if x else "gone"}
        x.status = "running"
        key, row_id = x.action, x.row_id
    STATS["runs"] += 1
    try:
        a = _action(r, key)
        if not _approved(a):
            raise ConnError("The action is not approved.", 409)
        if not _rate_ok(f"{r.id}|{key}", int(a.get("per_min") or 30)) or not _rate_ok(f"{r.id}|*", APP_PER_MIN):
            raise ConnError("It ran too many times this minute - try again in a little while.", 429)
        safe_retry = a["method"] in ("GET",) or bool(a.get("idem"))
        tries, code, data, note, wrote = 0, 0, None, "", []
        while True:
            tries += 1
            try:
                code, data, note = _call(r, a, row_id, rid)
            except httpx.TimeoutException:
                if safe_retry and tries <= int(a.get("retries") or 0):
                    time.sleep(min(4, tries))
                    continue
                st = "failed" if safe_retry else "ambiguous"
                STATS["ambiguous" if st == "ambiguous" else "failed"] += 1
                _finish(rid, st, 0, tries, "no reply in time" + ("" if safe_retry else " - it may have gone through; Hoola will not send it again"))
                return {"run": rid, "status": st}
            except httpx.HTTPError as e:
                _finish(rid, "failed", 0, tries, f"could not reach it ({type(e).__name__})")
                STATS["failed"] += 1
                return {"run": rid, "status": "failed"}
            if (code == 429 or code >= 500) and tries <= int(a.get("retries") or 0) and (safe_retry or code == 429):
                time.sleep(min(4, tries))
                continue
            break
        if 200 <= code < 300:
            wrote = _write_back(r, a, row_id, data)
            STATS["ok"] += 1
            _finish(rid, "ok", code, tries, note + (f"; wrote: {', '.join(wrote)}" if wrote else ""))
            return {"run": rid, "status": "ok", "code": code, "wrote": wrote}
        STATS["failed"] += 1
        sec = _secrets_of(r)
        why = _scrub(json.dumps(data, ensure_ascii=False)[:300] if not isinstance(data, str) else data[:300], sec)
        _finish(rid, "failed", code, tries, f"{note}: {why}")
        return {"run": rid, "status": "failed", "code": code}
    except ConnError as e:
        _finish(rid, "refused" if e.code in (400, 409, 429) else "failed", 0, 0, str(e))
        STATS["refused"] += 1
        return {"run": rid, "status": "refused", "why": str(e)}


def _finish(rid: str, st: str, code: int, tries: int, note: str) -> None:
    with session() as s:
        x = s.get(AppConnRun, rid)
        keep = (x.note or "") if (x.note or "").startswith("[") else ""      # v0.459 a reminder's booking time stays
        x.status, x.code, x.attempts, x.note, x.done = st, code, tries, (keep + " " + note).strip()[:600], now()
        if x.created:
            x.ms = int((now() - (x.created if x.created.tzinfo else x.created.replace(tzinfo=timezone.utc))).total_seconds() * 1000)


def fire(r: AppProject, coll: str, row_id: str, event: str, status_: str = "") -> int:
    """A new row / a status reached: queue every approved action listening for it (never blocks the request)."""
    n = 0
    try:
        acts = _cfg(r).get("actions") or []
    except Exception:                                          # noqa: BLE001
        return 0
    for a in acts:
        if a.get("coll") != coll or a.get("trigger") != event or not _approved(a):
            continue
        if event == "status" and a.get("status") != status_:
            continue
        try:
            run(r, a["key"], row_id, event, wait=False)
            n += 1
        except ConnError:
            pass
    return n


def staff_run(r: AppProject, w: W.Who, key: str, row_id: str) -> dict[str, Any]:
    """A staff button in the app: only for actions she allowed staff to run, on a row of that action's list."""
    if not w.staff or w.m is None:
        raise ConnError("Staff only.", 403)
    a = _action(r, key)
    if not a.get("staff") or a.get("trigger") != "manual":
        raise ConnError("This action cannot be run from the app.", 403)
    W.rate(f"conn-staff:{r.id}:{w.m.id}", 20, 60)
    got = run(r, key, row_id, "staff", wait=True)
    return {"status": got.get("status"), "wrote": got.get("wrote", [])}


def tick(force: bool = False) -> int:
    """Runs queued for more than a minute (the server restarted mid-way) are done now; running > 10 min = failed."""
    ensure_tables()
    try:
        remind_tick()                                         # v0.459 reminders before a booking
    except Exception:                                          # noqa: BLE001
        log.exception("connector reminders")
    cut = now() - timedelta(seconds=60)
    with session() as s:
        stuck = s.scalars(select(AppConnRun).where(AppConnRun.status == "queued", AppConnRun.created <= cut,
                                                   AppConnRun.created >= now() - timedelta(hours=6)).limit(50)).all()
        todo = [(x.id, x.app_id) for x in stuck]
        for x in s.scalars(select(AppConnRun).where(AppConnRun.status == "running", AppConnRun.created <= now() - timedelta(minutes=10))).all():
            x.status, x.note = "ambiguous", "the server stopped midway - it may have gone through; Hoola will not send it again"
    n = 0
    for rid, app_id in todo:
        with session() as s:
            a = s.get(AppProject, app_id)
            if a is not None:
                s.expunge(a)
        if a is not None:
            _safe_do(a, rid)
            n += 1
    return n


# ---------------------------------------------------------------- v0.459 reminders before a booking (SMS / WhatsApp / email)
IST = timezone(timedelta(hours=5, minutes=30))
REMIND_SCAN = 5000


def _start_of(d: dict[str, Any], a: dict[str, Any]) -> datetime | None:
    """A booking's date (+ time) as an IST moment; a date with no time = 9 am."""
    raw = str(d.get(a.get("date_field") or "date") or "").strip()[:10]
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if not m:
        return None
    hh, mm = 9, 0
    t = str(d.get(a.get("time_field") or "") or "").strip() if a.get("time_field") else ""
    tm = re.match(r"(\d{1,2})[:.](\d{2})\s*([ap]\.?m\.?)?", t, re.I)
    if tm:
        hh, mm = int(tm.group(1)), int(tm.group(2))
        ap = (tm.group(3) or "").lower()[:1]
        if ap == "p" and hh < 12:
            hh += 12
        if ap == "a" and hh == 12:
            hh = 0
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), min(hh, 23), min(mm, 59), tzinfo=IST)
    except ValueError:
        return None


def due_reminders(r: AppProject, at: datetime | None = None) -> list[tuple[str, str, str]]:
    """(action key, row id) whose reminder is due now and was not sent for this booking time. Cancelled rows never."""
    at = at or now()
    out: list[tuple[str, str, str]] = []
    acts = [x for x in _cfg(r).get("actions") or [] if x.get("trigger") == "remind" and _approved(x)]
    if not acts:
        return out
    ensure_tables()
    with session() as s:
        for a in acts:
            rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.coll == a["coll"],
                                                        W.SiteAppRow.created_at >= at - timedelta(days=120))
                             .order_by(W.SiteAppRow.created_at.desc()).limit(REMIND_SCAN)).all()
            for x in rows:
                d = _j(x.data, {})
                if re.search(r"cancel|radd|reject", str(d.get("status") or ""), re.I):
                    continue
                st = _start_of(d, a)
                if st is None or not (st - timedelta(minutes=int(a.get("before_min") or 120)) <= at < st):
                    continue
                stamp = st.strftime("%Y-%m-%d %H:%M")
                sent = s.scalar(select(AppConnRun.id).where(AppConnRun.app_id == r.id, AppConnRun.action == a["key"],
                                                            AppConnRun.row_id == x.id, AppConnRun.trigger == "remind",
                                                            AppConnRun.note.like(f"%[{stamp}]%")).limit(1))
                if sent is None:
                    out.append((a["key"], x.id, stamp))
    return out


def remind_tick(at: datetime | None = None) -> int:
    """Every app with an approved reminder action: queue the due ones (each booking time once)."""
    ensure_tables()
    with session() as s:
        apps = s.scalars(select(AppProject).where(AppProject.backend.like('%"trigger": "remind"%'))).all()
        for x in apps:
            s.expunge(x)
    n = 0
    for r in apps:
        for key, row_id, stamp in due_reminders(r, at):
            rid = new_id("crun")
            with session() as s:
                s.add(AppConnRun(id=rid, app_id=r.id, action=key, trigger="remind", row_id=row_id, note=f"[{stamp}]"))
            _POOL.submit(_safe_do, r, rid)
            n += 1
    return n


# ---------------------------------------------------------------- inbound webhooks (her outside service calls the app)
def save_hook(r: AppProject, h: dict[str, Any]) -> dict[str, Any]:
    from . import backend as BE
    sch = BE.schema(r)
    key = str(h.get("key") or "").strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", key):
        raise ConnError("Hook key: lowercase letters / digits / _ only.", 400)
    coll = str(h.get("coll") or "")
    c = next((x for x in sch["collections"] if x["key"] == coll), None)
    if c is None:
        raise ConnError("A list is needed.", 400)
    own = {f["key"] for f in c["fields"]}
    match = {str(k): str(v) for k, v in (h.get("match") or {}).items()}
    sets = {str(k): str(v) for k, v in (h.get("set") or {}).items()}
    if len(match) != 1 or not set(match) <= own or not sets or not set(sets) <= own:
        raise ConnError("match = one field (for example awb), set = fields that are in the list.", 400)
    sig = dict(h.get("sig") or {"type": "hmac_hex", "header": "x-signature"})
    if sig.get("type") not in ("hmac_hex", "hmac_b64", "token"):
        raise ConnError("Signature: hmac_hex | hmac_b64 | token.", 400)
    if NO_AADHAAR.search(json.dumps({"m": match, "s": sets})):
        raise ConnError("No Aadhaar hooks.", 400)
    secret = _secrets.token_urlsafe(24)
    hook = {"key": key, "coll": coll, "match": match, "set": sets, "sig": {"type": sig["type"], "header": str(sig.get("header") or "x-signature")[:60].lower()},
            "secret_name": f"hook_{key}"}
    set_secret(r, hook["secret_name"], str(h.get("secret") or secret))

    def fn(cf):
        cf["hooks"] = [x for x in cf.get("hooks") or [] if x.get("key") != key] + [hook]
    _save(r, fn)
    return {**status(r), "new_secret": None if h.get("secret") else secret,
            "say": "This secret is shown only now - put it in your service (Hoola will not show it again)."}


def hook(r: AppProject, key: str, headers: dict[str, str], raw: bytes) -> dict[str, Any]:
    h = next((x for x in _cfg(r).get("hooks") or [] if x.get("key") == key), None)
    if h is None:
        raise ConnError("Hook not found.", 404)
    sec = _secrets_of(r).get(h["secret_name"], "")
    got = {k.lower(): v for k, v in headers.items()}.get(h["sig"]["header"], "")
    t = h["sig"]["type"]
    if t == "token":
        ok = bool(sec) and hmac.compare_digest(got, sec)
    else:
        mac = hmac.new(sec.encode(), raw, hashlib.sha256).digest()
        want = mac.hex() if t == "hmac_hex" else base64.b64encode(mac).decode()
        ok = bool(sec) and hmac.compare_digest(got.removeprefix("sha256="), want)
    if not ok:
        STATS["hooks_bad"] += 1
        raise ConnError("Wrong signature.", 401)
    STATS["hooks"] += 1
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        raise ConnError("Not JSON.", 400)
    (mk, mpath), = h["match"].items()
    want_v = _path(data, mpath)
    if want_v in (None, ""):
        return {"ok": True, "matched": 0}
    from . import backend as BE
    c = W.coll(BE.schema(r), h["coll"])
    fields = {f["key"]: f for f in c["fields"]}
    with session() as s:
        rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.coll == h["coll"])
                         .order_by(W.SiteAppRow.created_at.desc()).limit(5000)).all()
        hit = next((x.id for x in rows if str(_j(x.data, {}).get(mk) or "") == str(want_v)), None)
    if hit is None:
        return {"ok": True, "matched": 0}
    put: dict[str, Any] = {}
    for k, p in h["set"].items():
        v = _path(data, p)
        if v is None or isinstance(v, (dict, list)) or k == mk:
            continue
        try:
            put[k] = W._value(dict(fields[k], required=False), v)
        except W.AppError:
            continue
    if put:
        BE._merge(hit, put)
        if "status" in put:
            try:
                BE.status_moved(r, hit, str(put["status"]))
            except Exception:                                  # noqa: BLE001
                log.debug("hook status", exc_info=True)
    return {"ok": True, "matched": 1, "set": sorted(put)}


def remove_hook(r: AppProject, key: str) -> dict[str, Any]:
    _save(r, lambda c: c.__setitem__("hooks", [x for x in c.get("hooks") or [] if x.get("key") != key]))
    forget_secret(r, f"hook_{key}")
    return status(r)


def apply_pack(r: AppProject, pack: str, settings: dict[str, Any], secrets: dict[str, str] | None = None) -> dict[str, Any]:
    """A ready pack: her secrets (sealed) + the actions it drafts (each still waits for her approval tap)."""
    from . import connect_packs as P
    if pack not in P.PACKS:
        raise ConnError("Pack not found.", 404)
    for name, v in (secrets or {}).items():
        if name in P.PACKS[pack]["secrets"] and str(v or "").strip():
            set_secret(r, name, str(v))
    try:
        acts = P.actions_for(pack, settings or {})
    except ValueError:
        raise ConnError("Pack not found.", 404)
    made, problems = [], []
    for a in acts:
        try:
            save_action(r, a)
            made.append(a["key"])
        except ConnError as e:
            problems.append(f"{a['key']}: {e}")
    return {**status(r), "made": made, "problems": problems, "note": P.PACKS[pack]["note"], "not_verified": P.NOT_VERIFIED}


# ---------------------------------------------------------------- what she sees / the app sees
def status(r: AppProject) -> dict[str, Any]:
    from . import connect_packs as P
    cfg = _cfg(r)
    ensure_tables()
    with session() as s:
        runs = s.scalars(select(AppConnRun).where(AppConnRun.app_id == r.id).order_by(AppConnRun.created.desc()).limit(40)).all()
        rv = [{"id": x.id, "action": x.action, "trigger": x.trigger, "row": x.row_id, "status": x.status, "code": x.code,
               "attempts": x.attempts, "note": x.note, "at": x.created.isoformat() if x.created else ""} for x in runs]
    base = ""
    try:
        from . import service as AS
        base = (AS._settings().public_base_url or "").rstrip("/")
    except Exception:                                          # noqa: BLE001
        pass
    key = str(_j(r.android, {}).get("app_key") or "")
    return {"actions": [{**a, "approved": _approved(a), "leaves": what_leaves(a)} for a in cfg.get("actions") or []],
            "hooks": [{**h, "url": f"{base}/api/app-api/{key}/hook/{h['key']}"} for h in cfg.get("hooks") or []],
            "secrets": [n for n in _secret_names(r) if not n.startswith("hook_")], "runs": rv, "packs": P.catalog()}


def staff_buttons(r: AppProject) -> list[dict[str, str]]:
    return [{"key": a["key"], "label": a["label"], "coll": a["coll"]} for a in _cfg(r).get("actions") or []
            if a.get("staff") and a.get("trigger") == "manual" and a.get("coll") and _approved(a)]
