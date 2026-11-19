"""v0.459 WEB PUSH (web Step 5, W6): a website member's browser gets a notification - her order moved, the shop replied in
chat, her queue turn is near - ONLY after the visitor said yes twice: the site's own "Notify me" button (a tap, never on
page load) and then the browser's own permission prompt. No yes = nothing stored, nothing sent.

Standards, written here with `cryptography` (no extra package on her VPS):
  * RFC 8291 message encryption (aes128gcm): a fresh ECDH P-256 key per message with the browser's p256dh key, HKDF with
    the browser's 16-byte auth secret; the push service (Google / Mozilla / Apple / Microsoft) only ever sees ciphertext.
  * RFC 8292 VAPID: an ES256 JWT (aud = the push service origin, 12 h) identifies Hoola's server. The VAPID key pair is
    DERIVED from the server secret (HKDF), so it never has to be stored and never changes between restarts.
  * WHERE IT MAY GO: only the browser makers' push services (an endpoint on any other host is refused at subscribe, so a
    "subscription" can never make the server call an address of someone's choosing).
  * A 404 / 410 from the push service = the visitor turned it off: the subscription is deleted. Each member keeps at most
    5 browsers; one push is a few hundred bytes (title + line + where to open), never her data beyond that line."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import struct
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session
from . import webapp as W

log = logging.getLogger(__name__)
STATS = {"subscribed": 0, "sent": 0, "gone": 0, "failed": 0, "refused": 0}
PUSH_HOSTS = ("fcm.googleapis.com", "updates.push.services.mozilla.com", "web.push.apple.com")
PUSH_SUFFIX = (".push.services.mozilla.com", ".notify.windows.com", ".push.apple.com")
MAX_PER_MEMBER = 5
RS = 4096
TTL = 24 * 3600
SUB = "mailto:support@ainewtika.com"

_TRANSPORT: httpx.BaseTransport | None = None


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


class SitePushSub(Base):
    __tablename__ = "site_push_sub"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)              # sha256(endpoint)
    site_id: Mapped[str] = mapped_column(String(48), index=True)               # the app backend id (app:<pid>)
    member: Mapped[str] = mapped_column(String(40), index=True)
    endpoint: Mapped[str] = mapped_column(Text)
    p256dh: Mapped[str] = mapped_column(String(120))
    auth: Mapped[str] = mapped_column(String(40))
    ua: Mapped[str] = mapped_column(String(160), default="")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    fails: Mapped[int] = mapped_column(Integer, default=0)


_OK = False


def ensure_table() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        SitePushSub.__table__.create(_db._engine, checkfirst=True)
        _OK = True


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64u(s: str) -> bytes:
    s = str(s or "").strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _hkdf(salt: bytes, ikm: bytes, info: bytes, n: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=n, salt=salt, info=info).derive(ikm)


# ---------------------------------------------------------------- VAPID (the server's identity, derived, never stored)
_KEY: ec.EllipticCurvePrivateKey | None = None
_N = int("FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551", 16)


def _vapid() -> ec.EllipticCurvePrivateKey:
    global _KEY
    if _KEY is None:
        raw = _hkdf(b"hoola-vapid-v1", W._secret(), b"web push vapid key", 48)
        _KEY = ec.derive_private_key(int.from_bytes(raw, "big") % (_N - 1) + 1, ec.SECP256R1())
    return _KEY


def _pub_bytes(k: ec.EllipticCurvePublicKey) -> bytes:
    return k.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def public_key() -> str:
    """The applicationServerKey the page passes to pushManager.subscribe()."""
    return b64u(_pub_bytes(_vapid().public_key()))


def vapid_header(endpoint: str, at: float | None = None) -> str:
    u = urlparse(endpoint)
    claims = {"aud": f"{u.scheme}://{u.netloc}", "exp": int((at or time.time()) + 12 * 3600), "sub": SUB}
    head = b64u(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    body = b64u(json.dumps(claims, separators=(",", ":")).encode())
    der = _vapid().sign(f"{head}.{body}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    sig = b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    return f"vapid t={head}.{body}.{sig}, k={public_key()}"


# ---------------------------------------------------------------- RFC 8291 encryption
def encrypt(payload: bytes, p256dh: str, auth: str, salt: bytes | None = None,
            eph: ec.EllipticCurvePrivateKey | None = None) -> bytes:
    """One aes128gcm record: header (salt | rs | keyid = our one-time public key) + ciphertext."""
    ua_pub_b = unb64u(p256dh)
    auth_b = unb64u(auth)
    if len(ua_pub_b) != 65 or ua_pub_b[0] != 4 or len(auth_b) != 16:
        raise W.AppError("The browser's push key is not right.", 400)
    ua_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub_b)
    eph = eph or ec.generate_private_key(ec.SECP256R1())
    as_pub_b = _pub_bytes(eph.public_key())
    secret = eph.exchange(ec.ECDH(), ua_pub)
    ikm = _hkdf(auth_b, secret, b"WebPush: info\x00" + ua_pub_b + as_pub_b, 32)
    salt = salt or os.urandom(16)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    if len(payload) > RS - 17 - 1:
        raise W.AppError("The notification is too long.", 400)
    ct = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    return salt + struct.pack("!L", RS) + bytes([len(as_pub_b)]) + as_pub_b + ct


# ---------------------------------------------------------------- the visitor's yes
def host_ok(endpoint: str) -> bool:
    u = urlparse(str(endpoint or ""))
    h = (u.hostname or "").lower()
    return u.scheme == "https" and u.port in (None, 443) and not u.username and (h in PUSH_HOSTS or h.endswith(PUSH_SUFFIX))


_HAS: dict[str, tuple[float, bool]] = {}


def subscribe(site: str, w: W.Who, body: dict[str, Any], ua: str = "") -> dict[str, Any]:
    """A signed-in member's browser, after her tap + the browser's permission. {endpoint, keys: {p256dh, auth}, consent}."""
    if w.m is None:
        raise W.AppError("Sign in first.", 401)
    if body.get("consent") is not True:
        raise W.AppError("Notifications only with your yes (tap).", 400)
    ep = str(body.get("endpoint") or "").strip()
    keys = body.get("keys") if isinstance(body.get("keys"), dict) else {}
    if len(ep) > 1000 or not host_ok(ep):
        STATS["refused"] += 1
        raise W.AppError("This browser push service is not recognised.", 400)
    p256, au = str(keys.get("p256dh") or ""), str(keys.get("auth") or "")
    try:
        ok = len(unb64u(p256)) == 65 and len(unb64u(au)) == 16
    except (ValueError, TypeError):
        ok = False
    if not ok:
        raise W.AppError("The browser's push key is not right.", 400)
    W.rate(f"push-sub:{site}:{w.m.id}", 10, 3600)
    ensure_table()
    sid = hashlib.sha256(ep.encode()).hexdigest()[:40]
    with session() as s:
        x = s.get(SitePushSub, sid)
        if x is None:
            mine = s.scalars(select(SitePushSub).where(SitePushSub.site_id == site, SitePushSub.member == w.m.id)
                             .order_by(SitePushSub.created.asc())).all()
            for old in mine[: max(0, len(mine) - MAX_PER_MEMBER + 1)]:
                s.delete(old)
            s.add(SitePushSub(id=sid, site_id=site, member=w.m.id, endpoint=ep, p256dh=p256[:120], auth=au[:40], ua=ua[:160]))
        else:                                               # the same browser, now someone else signed in / new keys
            x.site_id, x.member, x.p256dh, x.auth, x.fails = site, w.m.id, p256[:120], au[:40], 0
    _HAS.pop(site, None)
    STATS["subscribed"] += 1
    return {"ok": True, "on": True}


def unsubscribe(site: str, w: W.Who, body: dict[str, Any]) -> dict[str, Any]:
    ensure_table()
    ep = str(body.get("endpoint") or "")
    with session() as s:
        x = s.get(SitePushSub, hashlib.sha256(ep.encode()).hexdigest()[:40]) if ep else None
        if x is not None and x.site_id == site and (w.m is None or x.member == w.m.id):
            s.delete(x)
    _HAS.pop(site, None)
    return {"ok": True, "on": False}


def forget_member(site: str, member: str) -> int:
    """Her account deleted / she said stop everywhere: every browser of hers forgotten."""
    ensure_table()
    with session() as s:
        xs = s.scalars(select(SitePushSub).where(SitePushSub.site_id == site, SitePushSub.member == member)).all()
        for x in xs:
            s.delete(x)
    _HAS.pop(site, None)
    return len(xs)


def has_subs(site: str) -> bool:
    hit = _HAS.get(site)
    if hit and time.monotonic() - hit[0] < 60:
        return hit[1]
    ensure_table()
    with session() as s:
        got = s.scalar(select(SitePushSub.id).where(SitePushSub.site_id == site).limit(1)) is not None
    _HAS[site] = (time.monotonic(), got)
    return got


# ---------------------------------------------------------------- sending
def send(site: str, members: list[str], title: str, body: str, url: str = "/", tag: str = "") -> int:
    if not members:
        return 0
    ensure_table()
    with session() as s:
        subs = s.scalars(select(SitePushSub).where(SitePushSub.site_id == site, SitePushSub.member.in_(list(members)[:500]))).all()
        for x in subs:
            s.expunge(x)
    msg = json.dumps({"title": str(title or "")[:80], "body": str(body or "")[:200], "url": str(url or "/")[:300],
                      "tag": str(tag or "")[:60]}, ensure_ascii=False).encode()
    n = 0
    with httpx.Client(timeout=10.0, transport=_TRANSPORT, follow_redirects=False) as c:
        for x in subs:
            if not host_ok(x.endpoint):
                continue
            try:
                data = encrypt(msg, x.p256dh, x.auth)
                resp = c.post(x.endpoint, content=data, headers={"TTL": str(TTL), "Content-Encoding": "aes128gcm",
                                                                 "Content-Type": "application/octet-stream", "Urgency": "normal",
                                                                 "Authorization": vapid_header(x.endpoint)})
            except (httpx.HTTPError, W.AppError, ValueError):
                STATS["failed"] += 1
                _fail(x.id, False)
                continue
            if resp.status_code in (404, 410):              # she turned it off in the browser
                STATS["gone"] += 1
                _fail(x.id, True)
            elif 200 <= resp.status_code < 300:
                STATS["sent"] += 1
                n += 1
            else:
                STATS["failed"] += 1
                _fail(x.id, False)
    return n


def _fail(sid: str, gone: bool) -> None:
    with session() as s:
        x = s.get(SitePushSub, sid)
        if x is None:
            return
        x.fails = (x.fails or 0) + 1
        if gone or x.fails >= 10:
            s.delete(x)


def later(site: str, members: list[str], title: str, body: str, url: str = "/", tag: str = "") -> None:
    """Fire and forget (an order write never waits for a push service). A site nobody subscribed on costs one cached read."""
    if not members or not has_subs(site):
        return
    try:
        from .. import push as P
        P._pool.submit(send, site, list(members), title, body, url, tag)
    except Exception:                                         # noqa: BLE001
        log.debug("web push later", exc_info=True)


def status(site: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        n = len(s.scalars(select(SitePushSub.id).where(SitePushSub.site_id == site)).all())
    return {"browsers": n, "stats": dict(STATS)}
