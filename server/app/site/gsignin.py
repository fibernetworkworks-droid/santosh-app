"""v0.995 B6 GOOGLE SIGN-IN FOR WEBSITES (owner: "GO B6" on docs/research/lovable/03_backend_vs_hoola.md, gap 7).

Her website's visitors could log in only with email + password or a mobile OTP; Google existed only in her native apps
(`appmaker/sign.py`, v0.455). This module turns the same checked sign-in on for a website linked to its app backend:

- She turns it on in the Studio (Cloud > Sign-in) with the WEB client id of her own Google Cloud project. Hoola keeps no
  Google secret: the page gets a Google ID token from Google Identity Services and the server checks it itself
  (`sign.verify_token`: signature against Google's published keys, issuer, audience = HER client id, expiry, a single-use
  nonce, a verified email).
- The account is the same member table the website already uses, so a visitor who signed up with a password and then
  taps Google on the same email is one person, not two. A new account still needs the privacy-notice tick.
- The page may load Google's script only while Google sign-in is on for that website: `csp()` adds Google's sign-in hosts
  to the website's Content-Security-Policy for that site alone, never for the others.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

log = logging.getLogger("santosh.site.gsignin")

# Google Identity Services, the hosts Google's own CSP guide names (script, its button frame, its calls, its button CSS)
GSI_SCRIPT = "https://accounts.google.com/gsi/client"
CSP_ADD = {"script-src": "https://accounts.google.com/gsi/client", "frame-src": "https://accounts.google.com/gsi/",
           "connect-src": "https://accounts.google.com/gsi/", "style-src": "https://accounts.google.com/gsi/style"}
CLIENT_ID = re.compile(r"^[0-9]{6,20}-[a-z0-9]{8,64}\.apps\.googleusercontent\.com$")
_CACHE: dict[str, tuple[float, bool]] = {}
_LOCK = threading.Lock()
TTL = 60


def _project(r):
    from . import applink as AL
    return AL.project(r)


def on(site_id: str) -> bool:
    """Is Google sign-in on (and usable) for this website? Cached for a minute; any failure reads as off."""
    if not site_id:
        return False
    t = time.time()
    with _LOCK:
        hit = _CACHE.get(site_id)
        if hit and t - hit[0] < TTL:
            return hit[1]
    got = False
    try:
        from ..appmaker import sign as SG
        from . import twin as TW
        from ..db import session
        from .models import Site
        rid, _ds = TW.split(site_id)
        with session() as s:
            r = s.get(Site, rid)
            if r is not None:
                s.expunge(r)
        p = _project(r) if r is not None else None
        got = bool(p is not None and "google" in SG.public(p).get("ways", []))
    except Exception:                         # noqa: BLE001 - a broken lookup never opens the CSP
        log.debug("google sign-in lookup failed", exc_info=True)
        got = False
    with _LOCK:
        _CACHE[site_id] = (t, got)
    return got


def forget(site_id: str = "") -> None:
    with _LOCK:
        if site_id:
            _CACHE.pop(site_id, None)
        else:
            _CACHE.clear()


def csp(policy: str) -> str:
    """The website's CSP with Google's sign-in hosts added to the four directives Google needs (and nothing else)."""
    parts = [d.strip() for d in policy.split(";") if d.strip()]
    out = []
    for d in parts:
        name = d.split(" ")[0]
        add = CSP_ADD.get(name)
        out.append(f"{d} {add}" if add and add not in d else d)
    return "; ".join(out)


def headers(h: dict[str, str], site_id: str) -> dict[str, str]:
    if "Content-Security-Policy" in h and on(site_id):
        h = dict(h)
        h["Content-Security-Policy"] = csp(h["Content-Security-Policy"])
    return h


# ---------------------------------------------------------------- the Studio (her settings)
def _linked(tenant: str, ref: str):
    from . import backend_tab as BT
    r, _schema, _who, p = BT._linked(tenant, ref)
    return r, p


def origins(r) -> list[str]:
    """The addresses she must list as "Authorized JavaScript origins" on her Google client: every address the website
    is served from, plus Hoola's own address (the Studio preview)."""
    from ..config import get_settings
    from . import hosting as H
    out = []
    base = (get_settings().public_base_url or "").rstrip("/")
    m = re.match(r"https?://[^/]+", base)
    for h in H._hosts_of(r):
        if h.hostname and f"https://{h.hostname}" not in out:
            out.append(f"https://{h.hostname}")
    if m and m.group(0) not in out:
        out.append(m.group(0))
    return out


def view(tenant: str, ref: str) -> dict[str, Any]:
    from ..appmaker import sign as SG
    r, p = _linked(tenant, ref)
    st = SG.settings(p)
    cid = st["ids"].get("google_web_client_id", "")
    return {"on": "google" in _saved_ways(p), "client_id": cid, "ready": "google" in SG.public(p).get("ways", []),
            "origins": origins(r), "signup": st["signup"],
            "how": ("In Google Cloud console: APIs & Services > Credentials > Create credentials > OAuth client ID > "
                    "Web application. Add every address below under Authorized JavaScript origins, then paste the "
                    "client ID here. No secret is needed: Hoola checks each sign-in with Google's public keys.")}


def _saved_ways(p) -> list[str]:
    from ..appmaker import backend as BE
    from ..appmaker import sign as SG
    h = SG._home(p)
    return [w for w in ((BE._j(h.backend, {}).get("sign") or {}).get("ways") or ["email_password"]) if w in SG.WAYS]


def save(tenant: str, ref: str, body: dict[str, Any]) -> dict[str, Any]:
    from ..appmaker import sign as SG
    from . import webapp as W
    r, p = _linked(tenant, ref)
    body = body if isinstance(body, dict) else {}
    cid = str(body.get("client_id") or "").strip()
    want = bool(body.get("on"))
    if cid and not CLIENT_ID.match(cid):
        raise W.AppError("That does not look like a Google web client ID (it ends in .apps.googleusercontent.com).", 400)
    if want and not cid and not SG.settings(p)["ids"].get("google_web_client_id"):
        raise W.AppError("Paste the web client ID from your Google Cloud project first.", 400)
    ways = [w for w in _saved_ways(p) if w != "google"] + (["google"] if want else [])
    if not ways:
        ways = ["email_password"]
    upd: dict[str, Any] = {"ways": ways}
    if cid:
        upd["ids"] = {"google_web_client_id": cid}
    SG.save_settings(p, upd)
    forget(r.id)
    forget(r.id + "~p")
    out = view(tenant, ref)
    out["say"] = ("Google sign-in is on: the login box shows \"Sign in with Google\" after the next build."
                  if out["ready"] else "Google sign-in is off.")
    return out
