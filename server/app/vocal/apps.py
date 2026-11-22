"""v0.999.124 HOOLA VOCAL - "For your own apps": her app keys and her webhooks (Settings page).

- App keys: `hv_live_...` made for her own programs. The whole key is shown ONCE; Hoola keeps only its SHA-256 and the
  last 4 characters. Up to 5 keys; removing one stops it at once. Everything an app makes uses HER credits, and runs
  under the same rules as her pages (no credits = refused before any engine call).
  Doors (public, the key in `Authorization: Bearer`): GET /api/vocal/v1/voices, POST /api/vocal/v1/speech,
  GET /api/vocal/v1/sounds/{id}. At most 120 calls an hour per key.
- Webhooks: up to 3 https addresses of HER server, on a public address only (never Hoola's own machine or a private
  network; checked again before every send). Events: sound.ready, dub.ready, dub.failed. Every POST carries
  `X-Hoola-Signature: t=<unix time>,v1=<hex HMAC-SHA256 of "<t>.<body>" with the hook's secret>`; the secret is shown
  once and kept sealed. 3 tries (now, 5 s, 30 s), no redirects followed, 10 s each; the last answer is shown.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import socket
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import service as V

log = logging.getLogger("santosh.vocal.apps")
KEY_PREFIX = "hv_live_"
MAX_KEYS = 5
MAX_HOOKS = 3
EVENTS = ("sound.ready", "dub.ready", "dub.failed")
RATE_HOUR = 120
_ILOCK = threading.Lock()
_RATE: dict[str, list[float]] = {}
_RESOLVE = None                 # tests: a fake resolver for the private-address guard


def _apps(d: dict[str, Any]) -> dict[str, Any]:
    a = d.get("apps") if isinstance(d.get("apps"), dict) else {}
    a.setdefault("keys", [])
    a.setdefault("hooks", [])
    d["apps"] = a
    return a


def _index_path() -> Path:
    p = Path("data") / "vocal" / "_appkeys.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _index() -> dict[str, Any]:
    try:
        d = json.loads(_index_path().read_text("utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:   # noqa: BLE001
        return {}


def _index_save(d: dict[str, Any]) -> None:
    p = _index_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d), "utf-8")
    tmp.replace(p)


def _sha(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _public_key(k: dict[str, Any]) -> dict[str, Any]:
    return {x: k.get(x) for x in ("id", "name", "last4", "made", "used_at", "calls")}


# ---------------------------------------------------------------- app keys
def keys_list(tenant: str) -> list[dict[str, Any]]:
    return [_public_key(k) for k in _apps(V._load(tenant))["keys"]]


def key_new(tenant: str, name: Any) -> dict[str, Any]:
    name = V._clean(name, 40) or "My app"
    full = KEY_PREFIX + secrets.token_urlsafe(30)
    row = {"id": V._id("vk"), "name": name, "sha": _sha(full), "last4": full[-4:], "made": V._now(), "used_at": "", "calls": 0}
    with V._LOCK:
        d = V._load(tenant)
        a = _apps(d)
        if len(a["keys"]) >= MAX_KEYS:
            raise V.VocalError(f"Up to {MAX_KEYS} app keys. Remove one first.")
        a["keys"].insert(0, row)
        V._store(tenant, d)
    with _ILOCK:
        idx = _index()
        idx[row["sha"]] = {"tenant": tenant, "kid": row["id"]}
        _index_save(idx)
    return {**_public_key(row), "key": full,
            "note": "Copy this key now. It is shown only once; Hoola keeps only a fingerprint of it."}


def key_remove(tenant: str, kid: str) -> dict[str, Any]:
    with V._LOCK:
        d = V._load(tenant)
        a = _apps(d)
        k = next((x for x in a["keys"] if x["id"] == kid), None)
        if not k:
            raise V.VocalError("That app key was not found.")
        a["keys"].remove(k)
        V._store(tenant, d)
    with _ILOCK:
        idx = _index()
        idx.pop(k["sha"], None)
        _index_save(idx)
    return {"removed": kid}


def who(auth: str) -> tuple[str, str]:
    """(tenant, key id) for a Bearer app key, or raises. Counts the call and keeps the hourly limit."""
    tok = str(auth or "").strip()
    if tok.lower().startswith("bearer "):
        tok = tok[7:].strip()
    if not tok.startswith(KEY_PREFIX) or len(tok) > 120:
        raise PermissionError("Send your Hoola Vocal app key as Authorization: Bearer hv_live_...")
    sha = _sha(tok)
    hit = _index().get(sha)
    if not hit:
        raise PermissionError("That app key is not known. It may have been removed.")
    tenant, kid = hit["tenant"], hit["kid"]
    now = time.time()
    with _ILOCK:
        seen = [t for t in _RATE.get(kid, []) if now - t < 3600]
        if len(seen) >= RATE_HOUR:
            _RATE[kid] = seen
            raise OverflowError(f"This app key made {RATE_HOUR} calls in the last hour. Wait a little.")
        seen.append(now)
        _RATE[kid] = seen
    with V._LOCK:
        d = V._load(tenant)
        k = next((x for x in _apps(d)["keys"] if x["id"] == kid and x["sha"] == sha), None)
        if not k:
            raise PermissionError("That app key is not known. It may have been removed.")
        k["used_at"] = V._now()
        k["calls"] = int(k.get("calls") or 0) + 1
        V._store(tenant, d)
    return tenant, kid


# ---------------------------------------------------------------- webhooks
def _check_url(url: str) -> str:
    u = str(url or "").strip()
    try:
        p = urlparse(u)
    except ValueError:
        raise V.VocalError("That address could not be read.") from None
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise V.VocalError("Use an https:// address of your own server, without a user name or password in it.")
    if len(u) > 400:
        raise V.VocalError("That address is too long.")
    host = p.hostname.lower()
    if host in ("localhost",) or host.endswith((".local", ".internal", ".localhost")):
        raise V.VocalError("That address is on a private network. Hoola sends only to public addresses.")
    try:
        infos = (_RESOLVE or socket.getaddrinfo)(host, p.port or 443)
    except socket.gaierror:
        raise V.VocalError(f"Could not find the address of {host}.") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise V.VocalError(f"{host} is on a private address. Hoola sends only to public addresses.")
    return u


def _public_hook(h: dict[str, Any]) -> dict[str, Any]:
    return {x: h.get(x) for x in ("id", "url", "events", "made", "last_at", "last_status", "last_event")}


def hooks_list(tenant: str) -> list[dict[str, Any]]:
    return [_public_hook(h) for h in _apps(V._load(tenant))["hooks"]]


def hook_add(tenant: str, url: Any, events: Any = None) -> dict[str, Any]:
    from ..bazar.security import vault
    u = _check_url(str(url or ""))
    ev = [e for e in (events or EVENTS) if e in EVENTS] or list(EVENTS)
    secret = "whsec_" + secrets.token_urlsafe(24)
    row = {"id": V._id("vh"), "url": u, "events": ev, "secret": vault().seal(secret), "made": V._now(),
           "last_at": "", "last_status": "", "last_event": ""}
    with V._LOCK:
        d = V._load(tenant)
        a = _apps(d)
        if len(a["hooks"]) >= MAX_HOOKS:
            raise V.VocalError(f"Up to {MAX_HOOKS} webhooks. Remove one first.")
        if any(h["url"] == u for h in a["hooks"]):
            raise V.VocalError("That address is already a webhook.")
        a["hooks"].append(row)
        V._store(tenant, d)
    return {**_public_hook(row), "secret": secret,
            "note": "Copy the signing secret now. It is shown only once."}


def hook_remove(tenant: str, hid: str) -> dict[str, Any]:
    with V._LOCK:
        d = V._load(tenant)
        a = _apps(d)
        h = next((x for x in a["hooks"] if x["id"] == hid), None)
        if not h:
            raise V.VocalError("That webhook was not found.")
        a["hooks"].remove(h)
        V._store(tenant, d)
    return {"removed": hid}


def sign(secret: str, ts: int, body: bytes) -> str:
    return hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()


def _payload(event: str, row: dict[str, Any]) -> dict[str, Any]:
    from ..config import get_settings
    base = (getattr(get_settings(), "public_base_url", "") or "").rstrip("/")
    if event.startswith("dub."):
        return {"event": event, "id": row.get("id"), "name": row.get("name"), "status": row.get("status"),
                "made": row.get("made"), "error": row.get("error") or "",
                "langs": [{"code": x.get("code"), "status": x.get("status"),
                           "video": f"{base}/api/vocal/v1/sounds/{x['video_id']}" if x.get("video_id") else ""}
                          for x in row.get("langs") or []]}
    return {"event": event, "id": row.get("id"), "kind": row.get("kind"), "title": row.get("title"),
            "made": row.get("made"), "seconds": row.get("seconds"), "lang": row.get("lang"), "credits": row.get("credits"),
            "format": row.get("ext"), "download": f"{base}/api/vocal/v1/sounds/{row.get('id')}"}


def _http_post(url: str, body: bytes, headers: dict[str, str]):     # the one network seam (tests replace it)
    import httpx
    return httpx.post(url, content=body, headers=headers, timeout=10, follow_redirects=False)


WAITS = (0, 5, 30)


def _deliver(tenant: str, hid: str, url: str, secret: str, event: str, body: bytes) -> None:
    status = ""
    for w in WAITS:
        if w:
            time.sleep(w)
        try:
            _check_url(url)
            ts = int(time.time())
            r = _http_post(url, body, {"Content-Type": "application/json", "User-Agent": "Hoola-Vocal-Webhook/1",
                                       "X-Hoola-Event": event, "X-Hoola-Signature": f"t={ts},v1={sign(secret, ts, body)}"})
            status = str(r.status_code)
            if 200 <= r.status_code < 300:
                break
        except V.VocalError as e:
            status = f"refused: {e}"
            break
        except Exception as e:   # noqa: BLE001
            status = f"no answer ({type(e).__name__})"
    with V._LOCK:
        d = V._load(tenant)
        h = next((x for x in _apps(d)["hooks"] if x["id"] == hid), None)
        if h is not None:
            h.update(last_at=V._now(), last_status=status[:120], last_event=event)
            V._store(tenant, d)


SYNC = False        # tests: deliver in the caller's thread


def notify(tenant: str, event: str, row: dict[str, Any]) -> int:
    """Send one event to every webhook of hers that wants it. Returns how many sends were started."""
    from ..bazar.security import vault
    hooks = [h for h in _apps(V._load(tenant))["hooks"] if event in (h.get("events") or EVENTS)]
    if not hooks:
        return 0
    body = json.dumps(_payload(event, row), ensure_ascii=False).encode()
    n = 0
    for h in hooks:
        try:
            secret = vault().open(h["secret"])
        except Exception:   # noqa: BLE001
            log.warning("vocal webhook %s secret cannot be opened", h.get("id"))
            continue
        args = (tenant, h["id"], h["url"], secret, event, body)
        if SYNC:
            _deliver(*args)
        else:
            threading.Thread(target=_deliver, args=args, daemon=True, name=f"vocal-hook-{h['id']}").start()
        n += 1
    return n


def hook_test(tenant: str, hid: str) -> dict[str, Any]:
    """A test event, sent now; the answer is returned (and kept as the hook's last answer)."""
    from ..bazar.security import vault
    h = next((x for x in _apps(V._load(tenant))["hooks"] if x["id"] == hid), None)
    if not h:
        raise V.VocalError("That webhook was not found.")
    body = json.dumps({"event": "test", "id": "vo_test", "made": V._now(),
                       "note": "This is a test from Hoola Vocal."}).encode()
    _deliver(tenant, hid, h["url"], vault().open(h["secret"]), "test", body)
    return next(_public_hook(x) for x in _apps(V._load(tenant))["hooks"] if x["id"] == hid)


def view(tenant: str) -> dict[str, Any]:
    return {"keys": keys_list(tenant), "hooks": hooks_list(tenant), "events": list(EVENTS), "max_keys": MAX_KEYS,
            "max_hooks": MAX_HOOKS, "rate_hour": RATE_HOUR,
            "doors": [{"method": "GET", "path": "/api/vocal/v1/voices", "does": "Your voices and Hoola's"},
                      {"method": "POST", "path": "/api/vocal/v1/speech", "does": "Words in, one take out (the sound file)"},
                      {"method": "GET", "path": "/api/vocal/v1/sounds/{id}", "does": "A sound you made, by its id"}],
            "signature": "X-Hoola-Signature: t=<unix time>,v1=<hex HMAC-SHA256 of \"<t>.<body>\" with the signing secret>"}
