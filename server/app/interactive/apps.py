"""v0.999.169 HOOLA INTERACTIVE REBUILD - "For your own apps": app keys + signed webhooks (the Vocal apps pattern, R5).

- App keys `hi_live_...` for her own programs. The whole key is shown ONCE; Hoola keeps its SHA-256 and the last 4
  characters. Up to 5 keys; removing one stops it at once. Everything an app makes uses HER credits and runs under the
  same rules as her pages (consent, numbers only from her words, a paid engine only with the price confirmed).
  Doors (public, `Authorization: Bearer hi_live_...`, 120 calls an hour per key):
      GET  /api/interactive/v1/engines         the engines and which are connected
      GET  /api/interactive/v1/avatars         her faces (with consent on record)
      POST /api/interactive/v1/videos          a script in -> a draft + its price card (nothing is spent)
      POST /api/interactive/v1/videos/{id}/make   {quote_key} -> starts the make (the price she agreed to)
      GET  /api/interactive/v1/videos/{id}      status, steps, and the download address when ready
      GET  /api/interactive/v1/videos/{id}/file the finished MP4
- Webhooks: up to 3 https addresses of HER server, public addresses only (Vocal's guard, checked before every send).
  Events video.ready, video.failed. `X-Hoola-Signature: t=<unix>,v1=<hex HMAC-SHA256 of "<t>.<body>">`.
"""
from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from . import studio as S

log = logging.getLogger("santosh.interactive.apps")
KEY_PREFIX = "hi_live_"
MAX_KEYS = 5
MAX_HOOKS = 3
EVENTS = ("video.ready", "video.failed")
RATE_HOUR = 120
_ILOCK = threading.Lock()
_RATE: dict[str, list[float]] = {}
SYNC = False        # tests: deliver in the caller's thread


def _apps(d: dict[str, Any]) -> dict[str, Any]:
    a = d.get("apps") if isinstance(d.get("apps"), dict) else {}
    a.setdefault("keys", [])
    a.setdefault("hooks", [])
    d["apps"] = a
    return a


def _index_path() -> Path:
    p = Path("data") / "interactive" / "_appkeys.json"
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
    import hashlib
    return hashlib.sha256(key.encode()).hexdigest()


def _id(prefix: str) -> str:
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _public_key(k: dict[str, Any]) -> dict[str, Any]:
    return {x: k.get(x) for x in ("id", "name", "last4", "made", "used_at", "calls")}


def keys_list(tenant: str) -> list[dict[str, Any]]:
    return [_public_key(k) for k in _apps(S._load(tenant))["keys"]]


def key_new(tenant: str, name: Any) -> dict[str, Any]:
    name = " ".join(str(name or "").split())[:40] or "My app"
    full = KEY_PREFIX + secrets.token_urlsafe(30)
    row = {"id": _id("ik"), "name": name, "sha": _sha(full), "last4": full[-4:], "made": S._now_iso(), "used_at": "", "calls": 0}
    with S._LOCK:
        d = S._load(tenant)
        a = _apps(d)
        if len(a["keys"]) >= MAX_KEYS:
            raise S.StudioError(f"Up to {MAX_KEYS} app keys. Remove one first.")
        a["keys"].insert(0, row)
        S._store(tenant, d)
    with _ILOCK:
        idx = _index()
        idx[row["sha"]] = {"tenant": tenant, "kid": row["id"]}
        _index_save(idx)
    return {**_public_key(row), "key": full, "note": "Copy this key now. It is shown only once; Hoola keeps only a fingerprint of it."}


def key_remove(tenant: str, kid: str) -> dict[str, Any]:
    with S._LOCK:
        d = S._load(tenant)
        a = _apps(d)
        k = next((x for x in a["keys"] if x["id"] == kid), None)
        if not k:
            raise S.StudioError("That app key was not found.")
        a["keys"].remove(k)
        S._store(tenant, d)
    with _ILOCK:
        idx = _index()
        idx.pop(k["sha"], None)
        _index_save(idx)
    return {"removed": kid}


def who(auth: str) -> tuple[str, str]:
    tok = str(auth or "").strip()
    if tok.lower().startswith("bearer "):
        tok = tok[7:].strip()
    if not tok.startswith(KEY_PREFIX) or len(tok) > 120:
        raise PermissionError("Send your Hoola Interactive app key as Authorization: Bearer hi_live_...")
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
    with S._LOCK:
        d = S._load(tenant)
        k = next((x for x in _apps(d)["keys"] if x["id"] == kid and x["sha"] == sha), None)
        if not k:
            raise PermissionError("That app key is not known. It may have been removed.")
        k["used_at"] = S._now_iso()
        k["calls"] = int(k.get("calls") or 0) + 1
        S._store(tenant, d)
    return tenant, kid


# ---------------------------------------------------------------- webhooks
def _check_url(url: str) -> str:
    from ..vocal import apps as VA
    from ..vocal import service as V
    try:
        return VA._check_url(url)
    except V.VocalError as e:
        raise S.StudioError(str(e)) from None


def _public_hook(h: dict[str, Any]) -> dict[str, Any]:
    return {x: h.get(x) for x in ("id", "url", "events", "made", "last_at", "last_status", "last_event")}


def hooks_list(tenant: str) -> list[dict[str, Any]]:
    return [_public_hook(h) for h in _apps(S._load(tenant))["hooks"]]


def hook_add(tenant: str, url: Any, events: Any = None) -> dict[str, Any]:
    from ..bazar.security import vault
    u = _check_url(str(url or ""))
    ev = [e for e in (events or EVENTS) if e in EVENTS] or list(EVENTS)
    secret = "whsec_" + secrets.token_urlsafe(24)
    row = {"id": _id("ih"), "url": u, "events": ev, "secret": vault().seal(secret), "made": S._now_iso(),
           "last_at": "", "last_status": "", "last_event": ""}
    with S._LOCK:
        d = S._load(tenant)
        a = _apps(d)
        if len(a["hooks"]) >= MAX_HOOKS:
            raise S.StudioError(f"Up to {MAX_HOOKS} webhooks. Remove one first.")
        if any(h["url"] == u for h in a["hooks"]):
            raise S.StudioError("That address is already a webhook.")
        a["hooks"].append(row)
        S._store(tenant, d)
    return {**_public_hook(row), "secret": secret, "note": "Copy the signing secret now. It is shown only once."}


def hook_remove(tenant: str, hid: str) -> dict[str, Any]:
    with S._LOCK:
        d = S._load(tenant)
        a = _apps(d)
        h = next((x for x in a["hooks"] if x["id"] == hid), None)
        if not h:
            raise S.StudioError("That webhook was not found.")
        a["hooks"].remove(h)
        S._store(tenant, d)
    return {"removed": hid}


def _payload(event: str, p: dict[str, Any]) -> dict[str, Any]:
    from ..config import get_settings
    base = (getattr(get_settings(), "public_base_url", "") or "").rstrip("/")
    v = p.get("video") or {}
    return {"event": event, "id": p.get("id"), "title": p.get("title"), "status": p.get("status"),
            "lang": p.get("lang"), "engine": v.get("engine") or p.get("engine"), "seconds": v.get("duration"),
            "credits": v.get("credits"), "error": p.get("error") or "",
            "download": f"{base}/api/interactive/v1/videos/{p.get('id')}/file" if p.get("status") == "ready" else ""}


def _deliver(tenant: str, hid: str, url: str, secret: str, event: str, body: bytes) -> None:
    from ..vocal import apps as VA
    status = ""
    for w in VA.WAITS:
        if w:
            time.sleep(w)
        try:
            _check_url(url)
            ts = int(time.time())
            r = VA._http_post(url, body, {"Content-Type": "application/json", "User-Agent": "Hoola-Interactive-Webhook/1",
                                          "X-Hoola-Event": event, "X-Hoola-Signature": f"t={ts},v1={VA.sign(secret, ts, body)}"})
            status = str(r.status_code)
            if 200 <= r.status_code < 300:
                break
        except S.StudioError as e:
            status = f"refused: {e}"
            break
        except Exception as e:   # noqa: BLE001
            status = f"no answer ({type(e).__name__})"
    with S._LOCK:
        d = S._load(tenant)
        h = next((x for x in _apps(d)["hooks"] if x["id"] == hid), None)
        if h is not None:
            h.update(last_at=S._now_iso(), last_status=status[:120], last_event=event)
            S._store(tenant, d)


def notify(tenant: str, event: str, project: dict[str, Any]) -> int:
    from ..bazar.security import vault
    hooks = [h for h in _apps(S._load(tenant))["hooks"] if event in (h.get("events") or EVENTS)]
    if not hooks:
        return 0
    body = json.dumps(_payload(event, project), ensure_ascii=False).encode()
    n = 0
    for h in hooks:
        try:
            secret = vault().open(h["secret"])
        except Exception:   # noqa: BLE001
            continue
        args = (tenant, h["id"], h["url"], secret, event, body)
        if SYNC:
            _deliver(*args)
        else:
            threading.Thread(target=_deliver, args=args, daemon=True, name=f"interactive-hook-{h['id']}").start()
        n += 1
    return n


def hook_test(tenant: str, hid: str) -> dict[str, Any]:
    from ..bazar.security import vault
    h = next((x for x in _apps(S._load(tenant))["hooks"] if x["id"] == hid), None)
    if not h:
        raise S.StudioError("That webhook was not found.")
    body = json.dumps({"event": "test", "id": "iv_test", "made": S._now_iso(),
                       "note": "This is a test from Hoola Interactive."}).encode()
    _deliver(tenant, hid, h["url"], vault().open(h["secret"]), "test", body)
    return next(_public_hook(x) for x in _apps(S._load(tenant))["hooks"] if x["id"] == hid)


def view(tenant: str) -> dict[str, Any]:
    return {"keys": keys_list(tenant), "hooks": hooks_list(tenant), "events": list(EVENTS), "max_keys": MAX_KEYS,
            "max_hooks": MAX_HOOKS, "rate_hour": RATE_HOUR,
            "doors": [{"method": "GET", "path": "/api/interactive/v1/engines", "does": "The engines and which are connected"},
                      {"method": "GET", "path": "/api/interactive/v1/avatars", "does": "Your faces"},
                      {"method": "POST", "path": "/api/interactive/v1/videos", "does": "A script in, a draft and its price out"},
                      {"method": "POST", "path": "/api/interactive/v1/videos/{id}/make", "does": "Make it at the price you confirmed"},
                      {"method": "GET", "path": "/api/interactive/v1/videos/{id}", "does": "Status and the download address"},
                      {"method": "GET", "path": "/api/interactive/v1/videos/{id}/file", "does": "The finished MP4"}],
            "signature": "X-Hoola-Signature: t=<unix time>,v1=<hex HMAC-SHA256 of \"<t>.<body>\" with the signing secret>"}
