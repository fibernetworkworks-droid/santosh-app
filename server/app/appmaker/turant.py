"""v0.367 TURANT (App Sahayak Phase 31, owner: "START PHASE 31"): instant notifications for the Android apps Hoola builds.

The apps checked for news every 15+ minutes (Android's JobScheduler). With TURANT on, the server pushes the same events at
once through Firebase Cloud Messaging (HTTP v1) - Google's official push - using Newtika's own Firebase project (the
service account Hoola's phone app already uses, `fcm_service_account_file` on the VPS). Switching it on (her tap only)
registers the app's package in that Firebase project through Google's official Firebase Management API and keeps the
google-services config on the app; the NEXT build carries Firebase Messaging (gen.fcm_config). The phone sends its token to
the app's own backend after sign-in (POST /api/app-api/<key>/push-token); tokens are SiteAppRow rows coll "_push" owned by
the account (gone with the account). Events: her row moved (status / paid) -> the customer; a new order / booking / request
-> staff; a row given to someone -> that person. A push carries a title and one line only. iPhone keeps its background
check (an Apple push key from her account is a later step). Without the service account nothing changes."""
from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

import httpx
from sqlalchemy import select

from ..config import get_settings
from ..db import session
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger("santosh.appmaker.turant")
COLL = "_push"
MGMT = "https://firebase.googleapis.com/v1beta1"
SCOPES = ["https://www.googleapis.com/auth/firebase", "https://www.googleapis.com/auth/cloud-platform"]
STATS = {"enabled": 0, "tokens": 0, "sent": 0, "failed": 0, "dropped": 0}
_mgmt_creds = None


class TurantError(W.AppError):
    pass


def configured() -> bool:
    return bool(get_settings().fcm_service_account_file)


def _mgmt():
    """(credentials with the Firebase Management scopes, project id) from the same service account file."""
    global _mgmt_creds
    from google.oauth2 import service_account
    path = get_settings().fcm_service_account_file
    with open(path, encoding="utf-8") as f:
        info = json.load(f)
    if _mgmt_creds is None:
        _mgmt_creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    if not _mgmt_creds.valid:
        import google.auth.transport.requests
        _mgmt_creds.refresh(google.auth.transport.requests.Request())
    return _mgmt_creds, info["project_id"]


def _call(method: str, url: str, body: dict | None = None) -> dict[str, Any]:
    creds, _p = _mgmt()
    r = httpx.request(method, url, json=body, headers={"Authorization": f"Bearer {creds.token}"}, timeout=30)
    if r.status_code >= 300:
        raise TurantError(f"Firebase: {r.status_code} {r.text[:200]}", 502)
    return r.json() if r.content else {}


def state(r: AppProject) -> dict[str, Any]:
    """Read fresh (the caller's copy of the project may be older than a switch made a moment ago)."""
    from . import service as AS
    from .android import service as AN
    return dict(AN.state(AS._load(r.id)).get("fcm") or {})


def view(r: AppProject) -> dict[str, Any]:
    st = state(r)
    return {"on": bool(st.get("configs")), "configured": configured(), "packages": sorted((st.get("configs") or {}).keys()), "at": st.get("at", ""),
            "tokens": _count(r), "ios": ios_on(r), "ios_key": ios_view(r),
            "note": ("Instant notifications reach Android phones from the next build; iPhones keep the background check."
                     if configured() else "Hoola's Firebase key is not set on the server yet - the apps keep the 15-minute check.")}


def packages(r: AppProject) -> list[str]:
    """The packages this app is built under: the preview id, and the permanent Play Store package once she set it."""
    from .android import spec as SP
    from .android import store as ST
    out = [SP.app_id_for(r.id)]
    try:
        pkg = str(ST.state(r).get("package") or "")
    except Exception:                                         # noqa: BLE001
        pkg = ""
    if pkg and pkg not in out:
        out.append(pkg)
    return out


def _register(project: str, pkg: str, name: str, apps: list[dict[str, Any]]) -> str:
    hit = next((x for x in apps if x.get("packageName") == pkg), None)
    if hit is not None:
        return hit["appId"]
    op = _call("POST", f"{MGMT}/projects/{project}/androidApps", {"packageName": pkg, "displayName": name[:60]})
    for _ in range(20):                                        # a long-running operation: usually done in a few seconds
        if op.get("done"):
            break
        time.sleep(1.5)
        op = _call("GET", f"{MGMT}/{op['name']}")
    app_id = (op.get("response") or {}).get("appId")
    if not app_id:
        raise TurantError("Firebase ne app abhi register nahi kiya; thodi der baad dobara kijiye.", 502)
    return app_id


def enable(r: AppProject) -> dict[str, Any]:
    """Her tap: register the app's package(s) in Newtika's Firebase project (or find them) and keep each config for the
    next build (the preview build and the Play Store bundle use different packages)."""
    from ..db import now
    from .android import service as AN
    if not configured():
        raise TurantError("Hoola ka Firebase key server par nahi hai (FCM service account) - abhi app 15 minute wali jaanch hi karegi.", 409)
    _c, project = _mgmt()
    apps = _call("GET", f"{MGMT}/projects/{project}/androidApps?pageSize=100").get("apps") or []
    configs: dict[str, str] = {}
    for pkg in packages(r):
        app_id = _register(project, pkg, r.name or "Hoola app", apps)
        cfg = _call("GET", f"{MGMT}/projects/{project}/androidApps/{app_id}/config")
        text = base64.b64decode(cfg.get("configFileContents") or "").decode("utf-8", "replace")
        json.loads(text)                                       # must be the google-services.json
        configs[pkg] = text
    AN._put(r.id, fcm={"configs": configs, "package": packages(r)[0], "at": now().isoformat()})
    STATS["enabled"] += 1
    return view(r)


def config_for(r: AppProject, pkg: str) -> str:
    return str((state(r).get("configs") or {}).get(pkg) or "")


def disable(r: AppProject) -> dict[str, Any]:
    from .android import service as AN
    AN._put(r.id, fcm={})
    return view(r)


def register(r: AppProject, w: W.Who, token: str, platform: str = "android") -> dict[str, Any]:
    from . import backend as BE
    if w.m is None:
        raise W.AppError("Pehle login kijiye.", 401)
    token = str(token or "").strip()
    if not 20 <= len(token) <= 400 or any(ch.isspace() for ch in token):
        raise W.AppError("token galat hai.")
    site = BE.bid(r)
    with session() as s:
        for row in s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site, W.SiteAppRow.coll == COLL)).all():
            if BE._j(row.data, {}).get("token") == token:
                s.delete(row)                                  # one phone = one account at a time
        s.add(W.SiteAppRow(site_id=site, coll=COLL, owner=w.m.id,
                           data=json.dumps({"token": token, "platform": "ios" if platform == "ios" else "android"})))
    STATS["tokens"] += 1
    return {"ok": True}


def _count(r: AppProject) -> int:
    from . import backend as BE
    with session() as s:
        return len(s.scalars(select(W.SiteAppRow.id).where(W.SiteAppRow.site_id == BE.bid(r), W.SiteAppRow.coll == COLL)).all())


def _tokens(r: AppProject, members: list[str]) -> list[tuple[str, str]]:
    from . import backend as BE
    if not members:
        return []
    with session() as s:
        rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == BE.bid(r), W.SiteAppRow.coll == COLL,
                                                    W.SiteAppRow.owner.in_(members))).all()
        return [(x.id, BE._j(x.data, {}).get("token", ""), BE._j(x.data, {}).get("platform", "android")) for x in rows]


def staff_ids(r: AppProject) -> list[str]:
    from . import backend as BE
    return list(BE._staff_of(BE.bid(r)).keys())


def _drop(row_id: str) -> None:
    with session() as s:                                       # the phone uninstalled / the token rotated
        x = s.get(W.SiteAppRow, row_id)
        if x is not None:
            s.delete(x)
    STATS["dropped"] += 1


def send(r: AppProject, members: list[str], title: str, body: str, ref: str = "") -> int:
    """Push to these accounts' phones (Android through FCM when switched on, iPhone through APNs when her Apple push key
    is set - v0.368). Never raises."""
    if not members:
        return 0
    toks = _tokens(r, members)
    n = send_ios(r, [(i, t) for i, t, p in toks if p == "ios"], title, body, ref)
    andr = [(i, t) for i, t, p in toks if p != "ios"]
    if not andr or not configured() or not state(r).get("configs"):
        STATS["sent"] += n
        return n
    try:
        from .. import push as P
        creds, project = P._credentials()
    except Exception:                                         # noqa: BLE001
        log.debug("turant creds", exc_info=True)
        return n
    for row_id, tok in andr:
        msg = {"message": {"token": tok, "android": {"priority": "HIGH"},
                           "data": {"title": title[:80], "body": body[:200], "id": ref[:60]}}}
        try:
            res = httpx.post(f"https://fcm.googleapis.com/v1/projects/{project}/messages:send", json=msg,
                             headers={"Authorization": f"Bearer {creds.token}"}, timeout=15)
        except httpx.HTTPError:
            STATS["failed"] += 1
            continue
        if res.status_code == 200:
            n += 1
        elif res.status_code in (400, 404) and ("UNREGISTERED" in res.text or "INVALID_ARGUMENT" in res.text):
            _drop(row_id)
        else:
            STATS["failed"] += 1
    STATS["sent"] += n
    return n


def later(r: AppProject, members: list[str], title: str, body: str, ref: str = "") -> None:
    """Fire and forget on Hoola's push pool (an order write never waits for Google / Apple)."""
    if not members or not ((configured() and state(r).get("configs")) or ios_on(r)):
        return
    try:
        from .. import push as P
        P._pool.submit(send, r, list(members), title, body, ref)
    except Exception:                                         # noqa: BLE001
        log.debug("turant later", exc_info=True)



# ---------------------------------------------------------------- v0.368 TURANT IPHONE: Apple's push service (APNs)
# Apple sends a push only with a key from the business's OWN Apple Developer account (Certificates, IDs & Profiles > Keys >
# Apple Push Notifications service): Key ID, Team ID and the .p8 file, typed into her Hoola once, sealed by the server vault,
# never shown again, never in chat. Token-based APNs: ES256 JWT (iss = team, kid = key id, 50 minutes), HTTP/2 to
# api.push.apple.com, topic = the app's bundle id. A device token Apple calls Unregistered / BadDeviceToken is dropped.
APNS = "https://api.push.apple.com/3/device/"
_apns_jwt: dict[str, tuple[float, str]] = {}


def _ios_file(r: AppProject):
    from .android import service as AN
    return AN._dir(r) / "apns.key.sealed"


def ios_on(r: AppProject) -> bool:
    return _ios_file(r).exists()


def ios_view(r: AppProject) -> dict[str, Any]:
    if not ios_on(r):
        return {}
    try:
        k = _ios_key(r)
        return {"key_id": k["key_id"], "team_id": k["team_id"], "at": k.get("at", "")}
    except Exception:                                         # noqa: BLE001
        return {"broken": True}


def _ios_key(r: AppProject) -> dict[str, str]:
    from ..bazar.security import vault
    return json.loads(vault().open(_ios_file(r).read_text()))


def set_ios_key(r: AppProject, key_id: str, team_id: str, p8: str) -> dict[str, Any]:
    """Her Apple push key (sealed). Checked: 10-character ids and a real EC private key; never returned."""
    import re
    from ..bazar.security import vault
    from ..db import now
    key_id, team_id = str(key_id or "").strip().upper(), str(team_id or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{10}", key_id) or not re.fullmatch(r"[A-Z0-9]{10}", team_id):
        raise TurantError("Key ID aur Team ID dono 10 akshar ke hote hain (Apple Developer > Keys / Membership).")
    p8 = str(p8 or "").strip()
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        k = serialization.load_pem_private_key(p8.encode(), password=None)
        if not isinstance(k, ec.EllipticCurvePrivateKey):
            raise ValueError("not EC")
    except Exception:                                         # noqa: BLE001
        raise TurantError("Yeh .p8 key sahi nahi lagi (Apple se download ki hui AuthKey_XXXX.p8 ka poora text chahiye).")
    _ios_file(r).write_text(vault().seal(json.dumps({"key_id": key_id, "team_id": team_id, "p8": p8, "at": now().isoformat()})))
    _apns_jwt.pop(r.id, None)
    return view(r)


def clear_ios_key(r: AppProject) -> dict[str, Any]:
    f = _ios_file(r)
    if f.exists():
        f.unlink()
    _apns_jwt.pop(r.id, None)
    return view(r)


def _jwt(r: AppProject) -> str:
    hit = _apns_jwt.get(r.id)
    if hit and time.time() - hit[0] < 50 * 60:
        return hit[1]
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    k = _ios_key(r)
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    head = b64(json.dumps({"alg": "ES256", "kid": k["key_id"]}, separators=(",", ":")).encode())
    body = b64(json.dumps({"iss": k["team_id"], "iat": int(time.time())}, separators=(",", ":")).encode())
    key = serialization.load_pem_private_key(k["p8"].encode(), password=None)
    der = key.sign(f"{head}.{body}".encode(), ec.ECDSA(hashes.SHA256()))
    rr, ss = decode_dss_signature(der)
    tok = f"{head}.{body}.{b64(rr.to_bytes(32, 'big') + ss.to_bytes(32, 'big'))}"
    _apns_jwt[r.id] = (time.time(), tok)
    return tok


def _apns_client():
    """HTTP/2 client (APNs speaks only HTTP/2; needs the h2 package)."""
    return httpx.Client(http2=True, timeout=15)


def send_ios(r: AppProject, toks: list[tuple[str, str]], title: str, body: str, ref: str = "") -> int:
    if not toks or not ios_on(r):
        return 0
    try:
        from .ios import service as IS
        topic = IS.bundle_id(r)
        jwt = _jwt(r)
        client = _apns_client()
    except Exception:                                         # noqa: BLE001
        log.info("apns not ready", exc_info=True)
        return 0
    n = 0
    payload = {"aps": {"alert": {"title": title[:80], "body": body[:200]}, "sound": "default"}, "id": ref[:60]}
    with client:
        for row_id, tok in toks:
            try:
                res = client.post(APNS + tok, json=payload, headers={"authorization": f"bearer {jwt}", "apns-topic": topic,
                                                                     "apns-push-type": "alert", "apns-priority": "10"})
            except httpx.HTTPError:
                STATS["failed"] += 1
                continue
            if res.status_code == 200:
                n += 1
            elif res.status_code in (400, 410) and ("Unregistered" in res.text or "BadDeviceToken" in res.text):
                _drop(row_id)
            else:
                STATS["failed"] += 1
    return n
