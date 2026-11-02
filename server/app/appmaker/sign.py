"""v0.442 SURAKSHIT LOGIN (App Sahayak Pillar I, Phase 60) - how the PEOPLE of her native apps sign in, and safely.

The engine is the one v0.434 built for her website (`site/security.py`: OTP hashed + rate limited, TOTP 2FA for staff,
sessions she can end, DPDP consent / export, audit log, permissions matrix). It works on the app backend id
(`app:<project>`), so this module OPENS it to the native apps instead of writing a second one - a customer who signed
up on the website is the same account in the phone app, and "sign out everywhere" ends both.

What is new here:
  * PHONE OTP in the native app: the code is typed only into the app's own login box (SMS Retriever / oneTimeCode
    autofill), goes straight to the server, is never shown, logged or sent to Hoola.
  * GOOGLE / APPLE sign-in, verified ON THE SERVER: the app sends the provider's ID token, and this module checks the
    signature against the provider's own published keys (Google /oauth2/v3/certs, Apple /auth/keys), then `iss`, `aud`
    (must be one of HER client ids), `exp`, `nonce` (the server's own, single-use) and the e-mail. A token the phone
    "says" is fine is never trusted. Only her PUBLIC client ids are stored - native sign-in needs no provider secret,
    so there is no key here to leak. Apple's private-relay address is kept as the e-mail, as Apple intends.
  * Her SWITCHES per app: which ways are offered, whether staff MUST have 2FA, whether new accounts are open at all.
  * Store rules in code: Sign in with Apple is offered on the iPhone build whenever Google is on (App Store 4.8), and
    in-app account deletion stays (both stores) - it was already there since v0.318.

Every function works on `family.home(r)`, so a rider / shop / staff app of one business shares its accounts.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import threading
import time
from typing import Any
from urllib.parse import urlparse

from ..db import now
from ..site import security as SEC
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"otp": 0, "social": 0, "social_bad": 0, "nonce": 0, "jwks": 0}

WAYS = ("email_password", "phone_otp", "google", "apple")
PROVIDERS: dict[str, dict[str, Any]] = {
    "google": {"label": "Sign in with Google", "iss": ("https://accounts.google.com", "accounts.google.com"),
               "jwks": "https://www.googleapis.com/oauth2/v3/certs",
               "ids": ("google_web_client_id", "google_ios_client_id"),
               "how": "Android: Credential Manager with her WEB client id as the server client id. iPhone: Google Sign-In "
                      "with her iOS client id. Both send the ID token here; the server checks it."},
    "apple": {"label": "Sign in with Apple", "iss": ("https://appleid.apple.com",),
              "jwks": "https://appleid.apple.com/auth/keys",
              "ids": ("apple_bundle_id", "apple_service_id"),
              "how": "iPhone: AuthenticationServices (audience = the app's bundle id). Android / web: her Services ID."},
}
NONCE_TTL = 600
JWKS_TTL = 3600
SKEW = 120
_JWKS: dict[str, tuple[float, dict[str, Any]]] = {}
_NONCE: dict[str, float] = {}
_LOCK = threading.Lock()
_FETCH = None                      # tests set a function(url) -> dict instead of the network


class SignError(W.AppError):
    pass


def set_fetch(fn) -> None:
    """Tests only: where the provider's public keys come from."""
    global _FETCH
    _FETCH = fn


def _home(r: AppProject) -> AppProject:
    from . import family as FA
    return FA.home(r)


def _site(r: AppProject) -> str:
    return "app:" + _home(r).id


# ---------------------------------------------------------------- her switches
def settings(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    r = _home(r)
    saved = BE._j(r.backend, {}).get("sign") or {}
    ways = [w for w in (saved.get("ways") or ["email_password"]) if w in WAYS] or ["email_password"]
    if "google" in ways and "apple" not in ways:
        ways.append("apple")                              # App Store 4.8: the iPhone build must offer Apple too
    ids = {k: str((saved.get("ids") or {}).get(k) or "") for p in PROVIDERS.values() for k in p["ids"]}
    out = {"ways": ways, "ids": ids, "staff_2fa": bool(saved.get("staff_2fa")),
           "otp_ready": bool(SEC.provider()), "signup": bool(BE.schema(r).get("signup", True)),
           "providers": {k: {"label": v["label"], "ids": list(v["ids"]), "how": v["how"]} for k, v in PROVIDERS.items()}}
    out["problems"] = problems(out)
    return out


def problems(st: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    if "phone_otp" in st["ways"] and not st["otp_ready"]:
        out["phone_otp"] = ("Mobile OTP ke liye DLT par registered SMS template + provider chahiye (server par "
                            "SITE_SMS_PROVIDER + key); tab tak login box OTP nahi dikhayega.")
    if "google" in st["ways"] and not st["ids"].get("google_web_client_id"):
        out["google"] = "Google login ke liye aapke Google Cloud project ka WEB client id chahiye (Android usi se chalta hai)."
    if "apple" in st["ways"] and not st["ids"].get("apple_bundle_id"):
        out["apple"] = "Apple login ke liye app ka bundle id chahiye (iPhone build ka, jaise in.hoola.yourapp)."
    return out


def save_settings(r: AppProject, body: dict[str, Any]) -> dict[str, Any]:
    from . import backend as BE
    r = _home(r)
    body = body if isinstance(body, dict) else {}
    cur = settings(r)
    ways = body.get("ways", cur["ways"])
    if not isinstance(ways, list):
        raise SignError("ways: list chahiye.")
    bad = [w for w in ways if w not in WAYS]
    if bad:
        raise SignError(f"Yeh login tareeka nahi hai: {', '.join(map(str, bad[:3]))}. Ho sakte hain: {', '.join(WAYS)}.")
    ways = [w for w in WAYS if w in ways]
    if not ways:
        raise SignError("Kam se kam ek login tareeka rakhna hoga.")
    ids = dict(cur["ids"])
    for k, v in (body.get("ids") or {}).items():
        if k not in ids:
            raise SignError(f"Yeh id nahi pehchani: {k}.")
        v = str(v or "").strip()[:200]
        if v and not re.fullmatch(r"[A-Za-z0-9._:\-]+", v):
            raise SignError(f"{k}: sirf akshar, ank, bindu aur dash.")
        ids[k] = v
    keep = {"ways": ways, "ids": {k: v for k, v in ids.items() if v}, "staff_2fa": bool(body.get("staff_2fa", cur["staff_2fa"]))}
    BE.patch_backend(r, set_={"sign": keep})
    return settings(r)


def public(r: AppProject) -> dict[str, Any]:
    """What the app's own login screen may show (it carries nothing secret)."""
    st = settings(r)
    ways = [w for w in st["ways"] if w != "phone_otp" or st["otp_ready"]]
    ways = [w for w in ways if w != "google" or st["ids"].get("google_web_client_id")]
    ways = [w for w in ways if w != "apple" or st["ids"].get("apple_bundle_id")]
    return {"ways": ways, "google_server_client_id": st["ids"].get("google_web_client_id", ""),
            "google_ios_client_id": st["ids"].get("google_ios_client_id", ""),
            "consent": True, "signup": st["signup"]}


# ---------------------------------------------------------------- phone OTP (hashed, rate limited, never shown)
def otp_start(r: AppProject, phone: str, ip: str = "") -> dict[str, Any]:
    st = settings(r)
    if "phone_otp" not in st["ways"]:
        raise SignError("Is app mein mobile OTP login chalu nahi hai.", 503)
    out = SEC.otp_start(_site(r), phone, ip)
    STATS["otp"] += 1
    return out


def otp_verify(r: AppProject, body: dict[str, Any], ua: str = "", ip: str = "") -> dict[str, Any]:
    from . import backend as BE
    st = settings(r)
    if "phone_otp" not in st["ways"]:
        raise SignError("Is app mein mobile OTP login chalu nahi hai.", 503)
    h = _home(r)
    return SEC.otp_verify(_site(r), BE.schema(h), str(body.get("phone") or ""), str(body.get("code") or ""),
                          str(body.get("name") or ""), bool(body.get("consent")), ua, ip)


# ---------------------------------------------------------------- e-mail + password (now with sessions + 2FA + consent)
def password_signup(r: AppProject, body: dict[str, Any], ua: str = "", ip: str = "") -> dict[str, Any]:
    from . import backend as BE
    h = _home(r)
    site = _site(r)
    if "consent" in (body or {}) and (body or {}).get("consent") is not True:
        raise SignError("Account banane ke liye privacy notice par haan (tick) zaroori hai.", 400)
    out = BE.signup(h, str((body or {}).get("email") or ""), str((body or {}).get("password") or ""),
                    str((body or {}).get("name") or ""), ip)
    m = W.member_of(site, out.get("token") or "")
    if m is not None:
        if (body or {}).get("consent") is True:
            SEC.save_consent(site, m.id, "signup")
        SEC.record(site, m, out["token"], ua, ip, "signup")
    return out


def password_login(r: AppProject, body: dict[str, Any], ua: str = "", ip: str = "") -> dict[str, Any]:
    from . import backend as BE
    h = _home(r)
    site = _site(r)
    out = BE.login(h, str((body or {}).get("email") or ""), str((body or {}).get("password") or ""), ip)
    m = W.member_of(site, out.get("token") or "")
    if m is not None and SEC.needs_2fa(site, m.email):     # the password was right; the authenticator code is step two
        return {"need_2fa": True, "ticket": SEC._ticket(site, m)}
    if m is not None:
        SEC.record(site, m, out["token"], ua, ip, "password")
    return out


# ---------------------------------------------------------------- Google / Apple: the SERVER checks the token
def nonce(r: AppProject) -> dict[str, Any]:
    """One single-use nonce per sign-in attempt, so a token caught elsewhere cannot be replayed into this app."""
    n = secrets.token_urlsafe(18)
    t = time.time()
    with _LOCK:
        for k, v in list(_NONCE.items()):
            if t - v > NONCE_TTL:
                _NONCE.pop(k, None)
        if len(_NONCE) > 20000:
            _NONCE.clear()
        _NONCE[f"{_site(r)}|{n}"] = t
    STATS["nonce"] += 1
    return {"nonce": n, "expires_in": NONCE_TTL, "sha256": hashlib.sha256(n.encode()).hexdigest()}


def _nonce_ok(site: str, n: str, claim: str, use: bool = False) -> bool:
    """Apple hashes the nonce (SHA-256 hex); Google sends it as it was given. `use` spends it (single use), and nothing
    spends it until the sign-in is otherwise fine - so a missing consent tick does not cost her the whole attempt."""
    if not n:
        return False
    with _LOCK:
        born = _NONCE.get(f"{site}|{n}")
        if born is not None and use:
            _NONCE.pop(f"{site}|{n}", None)
    if born is None or time.time() - born > NONCE_TTL:
        return False
    return hmac.compare_digest(claim, n) or hmac.compare_digest(claim.lower(), hashlib.sha256(n.encode()).hexdigest())


def _nonce_use(site: str, n: str) -> None:
    with _LOCK:
        _NONCE.pop(f"{site}|{n}", None)


def _b64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _jwks(url: str) -> dict[str, Any]:
    with _LOCK:
        hit = _JWKS.get(url)
    if hit and time.time() - hit[0] < JWKS_TTL:
        return hit[1]
    if _FETCH is not None:
        data = _FETCH(url)
    else:
        import httpx
        if (urlparse(url).hostname or "") not in ("www.googleapis.com", "appleid.apple.com"):
            raise SignError("Yeh provider ka pata nahi hai.", 400)
        with httpx.Client(timeout=10.0) as c:
            resp = c.get(url)
        if resp.status_code != 200:
            raise SignError("Login provider ki chaabiyan nahi mili; phir koshish kijiye.", 502)
        data = resp.json()
    if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
        raise SignError("Login provider ka jawab samajh nahi aaya.", 502)
    with _LOCK:
        _JWKS[url] = (time.time(), data)
    STATS["jwks"] += 1
    return data


def _verify_rs256(head: dict[str, Any], signing: bytes, sig: bytes, jwks: dict[str, Any]) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    kid, alg = str(head.get("kid") or ""), str(head.get("alg") or "")
    if alg != "RS256":                              # both providers sign ID tokens with RS256
        return False
    for k in jwks.get("keys") or []:
        if not isinstance(k, dict) or k.get("kty") != "RSA" or (kid and k.get("kid") != kid):
            continue
        try:
            n = int.from_bytes(_b64(str(k["n"])), "big")
            e = int.from_bytes(_b64(str(k["e"])), "big")
            pub = rsa.RSAPublicNumbers(e, n).public_key()
            pub.verify(sig, signing, padding.PKCS1v15(), hashes.SHA256())
            return True
        except (InvalidSignature, KeyError, ValueError, TypeError):
            continue
    return False


def verify_token(r: AppProject, provider: str, token: str, nonce_asked: str = "", need_nonce: bool = True) -> dict[str, Any]:
    """The provider's ID token -> its checked claims, or a refusal. Nothing here trusts the phone."""
    p = PROVIDERS.get(provider)
    if p is None:
        raise SignError("Login provider: google ya apple.", 400)
    st = settings(r)
    auds = [st["ids"].get(k, "") for k in p["ids"]]
    auds = [a for a in auds if a]
    if not auds:
        raise SignError(f"{p['label']} ke liye aapki client id abhi nahi daali gayi.", 503)
    parts = str(token or "").split(".")
    if len(parts) != 3 or len(token) > 8000:
        raise SignError("Login token theek nahi lagta.", 400)
    try:
        head = json.loads(_b64(parts[0]))
        body = json.loads(_b64(parts[1]))
        sig = _b64(parts[2])
    except (ValueError, TypeError):
        raise SignError("Login token padha nahi ja saka.", 400)
    if not isinstance(head, dict) or not isinstance(body, dict):
        raise SignError("Login token theek nahi lagta.", 400)
    if not _verify_rs256(head, (parts[0] + "." + parts[1]).encode(), sig, _jwks(p["jwks"])):
        STATS["social_bad"] += 1
        raise SignError("Login token ka signature galat hai.", 401)
    if str(body.get("iss") or "") not in p["iss"]:
        raise SignError("Login token kisi aur jagah se hai.", 401)
    if str(body.get("aud") or "") not in auds:
        STATS["social_bad"] += 1
        raise SignError("Yeh login token is app ke liye nahi bana.", 401)
    try:
        exp = int(body.get("exp") or 0)
        iat = int(body.get("iat") or 0)
    except (TypeError, ValueError):
        raise SignError("Login token ka samay theek nahi.", 401)
    t = time.time()
    if exp + SKEW < t or (iat and iat - SKEW > t):
        raise SignError("Login token purana ho gaya; phir se login kijiye.", 401)
    if need_nonce and not _nonce_ok(_site(r), nonce_asked, str(body.get("nonce") or "")):
        raise SignError("Login dobara shuru kijiye (nonce galat ya do baar use hua).", 401)
    sub = str(body.get("sub") or "")
    email = str(body.get("email") or "").strip().lower()[:160]
    if not sub:
        raise SignError("Login token mein account id nahi hai.", 401)
    if provider == "google" and email and body.get("email_verified") not in (True, "true"):
        raise SignError("Is Google account ka e-mail verified nahi hai.", 401)
    name = str(body.get("name") or "").strip()[:120]
    return {"sub": sub, "email": email, "name": name, "aud": str(body.get("aud") or "")}


def social_login(r: AppProject, provider: str, body: dict[str, Any], ua: str = "", ip: str = "") -> dict[str, Any]:
    """The app's Google / Apple tap: the token is checked here, then the account is found or made."""
    from . import backend as BE
    from ..db import session
    from sqlalchemy import select
    st = settings(r)
    if provider not in st["ways"]:
        raise SignError("Is app mein yeh login tareeka chalu nahi hai.", 503)
    h = _home(r)
    site = _site(r)
    asked = str((body or {}).get("nonce") or "")
    claims = verify_token(r, provider, str((body or {}).get("id_token") or ""), asked)
    email = claims["email"] or f"{provider}-{hashlib.sha256((provider + claims['sub']).encode()).hexdigest()[:16]}@{provider}.local"
    name = str((body or {}).get("name") or claims["name"] or "")[:120]
    W.ensure_tables()                              # makes the member / session / OTP tables on first need
    with session() as s:
        m = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == site, W.SiteAppMember.email == email)).first()
        fresh = m is None
        if fresh:
            if not BE.schema(h).get("signup", True):
                raise SignError("Is app par naye account band hain; dukaan se baat kijiye.", 403)
            if not (body or {}).get("consent"):
                raise SignError("Account banane ke liye privacy notice par haan (tick) zaroori hai.", 400)
            m = W.SiteAppMember(site_id=site, email=email, name=name, pw="", role="member",
                                consent=json.dumps(SEC.consent_record(provider)))
            s.add(m)
            s.flush()
        elif name and not (m.name or "").strip():
            m.name = name
        s.expunge(m)
    _nonce_use(site, asked)                       # everything else was fine: now the nonce is spent for good
    if SEC._two_fa_on(m):
        return {"need_2fa": True, "ticket": SEC._ticket(site, m)}
    tok = W.make_token(site, m)
    SEC.record(site, m, tok, ua, ip, "signup" if fresh else provider)
    STATS["social"] += 1
    return {"token": tok, "me": W.view_member(m), "new": fresh}


# ---------------------------------------------------------------- the member's own security page (in the app)
def _me(r: AppProject, w: W.Who) -> W.SiteAppMember:
    if w.m is None:
        raise SignError("Pehle login kijiye.", 401)
    return w.m


def my_security(r: AppProject, w: W.Who, token: str = "") -> dict[str, Any]:
    m = _me(r, w)
    site = _site(r)
    st = settings(r)
    two = SEC._totp_of(m)
    return {"sessions": SEC.sessions(site, m, token), "two_fa": bool(two.get("on")),
            "two_fa_required": bool(st["staff_2fa"]) and (m.role or "") in ("staff", "admin"),
            "staff": (m.role or "") in ("staff", "admin"), "ways": st["ways"],
            "consent": json.loads(m.consent) if getattr(m, "consent", None) else None}


def end_session(r: AppProject, w: W.Who, sid: str) -> dict[str, Any]:
    return SEC.end(_site(r), _me(r, w), sid)


def end_everywhere(r: AppProject, w: W.Who) -> dict[str, Any]:
    return SEC.end_all(_site(r), _me(r, w))


def two_fa_start(r: AppProject, w: W.Who) -> dict[str, Any]:
    h = _home(r)
    return SEC.two_fa_start(_site(r), _me(r, w), (h.name or "Hoola")[:40])


def two_fa_confirm(r: AppProject, w: W.Who, code: str) -> dict[str, Any]:
    return SEC.two_fa_confirm(_site(r), _me(r, w), code)


def two_fa_off(r: AppProject, w: W.Who, code: str) -> dict[str, Any]:
    st = settings(r)
    m = _me(r, w)
    if st["staff_2fa"] and (m.role or "") in ("staff", "admin"):
        raise SignError("Is app mein staff ke liye 2FA zaroori hai; maalkin hi yeh niyam badal sakti hain.", 403)
    return SEC.two_fa_off(_site(r), m, code)


def two_fa_login(r: AppProject, ticket: str, code: str, ua: str = "", ip: str = "") -> dict[str, Any]:
    return SEC.two_fa_login(_site(r), ticket, code, ua, ip)


def needs_2fa(r: AppProject, email: str):
    return SEC.needs_2fa(_site(r), email)


def my_data(r: AppProject, w: W.Who) -> dict[str, Any]:
    """DPDP: everything this account's own data, as JSON, from the app itself."""
    from . import backend as BE
    h = _home(r)
    return SEC.export(_site(r), BE.schema(h), _me(r, w))


# ---------------------------------------------------------------- her side
def view(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    h = _home(r)
    st = settings(h)
    return {"app": h.id, "number": h.number, **st, "matrix": SEC.matrix(BE.schema(h)),
            "audit": SEC.audit(_site(h), 60)}


def prompt_line(seed_backend: dict[str, Any]) -> str:
    ways = [w for w in ((seed_backend or {}).get("sign") or {}).get("ways", []) if w in WAYS]
    if not ways or ways == ["email_password"]:
        return ""
    return ("LOGIN: the kit's sign-in screen already offers " + ", ".join(ways).replace("_", " ")
            + " - never draw your own OTP / Google / Apple button and never ask for a password anywhere else.")
