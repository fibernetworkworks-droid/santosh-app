"""v0.34 federation: Hoola avatars on different servers talk the same way, over HTTPS.

- Each server has its own Ed25519 server key and publishes a card at /.well-known/hoola.json (and an A2A-style
  agent card at /.well-known/agent-card.json).
- An avatar elsewhere is addressed handle@domain (or uid@domain). /hoola/lookup on that server returns the public
  avatar card (no phone numbers, nothing private).
- Envelopes go to https://<domain>/hoola/inbox. The sending server signs (domain, date, sha256 of the body); the
  receiving server checks that signature with the sender server's published key, that the envelope's sender belongs
  to that domain, the date (5 minutes), and then the avatar's own signature, replay list and the owner's rules as
  for any local message.
- Files are fetched by the receiving server from the sender's /hoola/share/<id> with a signed request, once, only
  for the avatar they were sent to.
- Only public https hosts are contacted (no private / loopback addresses), and an operator block list applies.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from email.utils import formatdate, parsedate_to_datetime
from typing import Any

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from ..config import get_settings
from . import identity as idn

PROTOCOL = "hoola-net/1"
SKEW = 300
_http: httpx.Client | None = None            # tests inject a MockTransport client
_cards: dict[str, tuple[float, dict[str, Any]]] = {}
_rate: dict[str, list[float]] = {}


class FedError(Exception):
    pass


def set_http(c: httpx.Client | None) -> None:
    global _http
    _http = c
    _cards.clear()


def enabled() -> bool:
    return bool(getattr(get_settings(), "hoola_federation", True))


def blocked(domain: str) -> bool:
    raw = getattr(get_settings(), "hoola_blocked_servers", "") or ""
    return (domain or "").lower() in {d.strip().lower() for d in raw.split(",") if d.strip()}


def base_url(domain: str) -> str:
    """https://<domain>, or an override from HOOLA_SERVERS (json {domain: url}) for custom ports."""
    try:
        over = json.loads(getattr(get_settings(), "hoola_servers", "") or "{}")
    except ValueError:
        over = {}
    url = (over.get(domain) or f"https://{domain}").rstrip("/")
    if _http is None:
        from ..bazar.custom_mcp import UrlError, check_url
        try:
            check_url(url)
        except UrlError as e:
            raise FedError(f"{domain}: {e}")
    return url


def _client() -> httpx.Client:
    return _http or httpx.Client(timeout=20, follow_redirects=False, headers={"User-Agent": "Hoola/1 (+hoola-net)"})


def _close(c: httpx.Client) -> None:
    if _http is None:
        c.close()


# ---------------------------------------------------------------- this server's key and card
def _server_key() -> Ed25519PrivateKey:
    from pathlib import Path
    st = get_settings()
    path = Path(getattr(st, "hoola_server_key_file", "") or Path(st.pc_files_dir).parent / "hoola_server_ed25519.key")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        k = Ed25519PrivateKey.generate()
        raw = k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        path.write_bytes(idn._fernet().encrypt(base64.b64encode(raw)))
        import os
        os.chmod(path, 0o600)
    raw = base64.b64decode(idn._fernet().decrypt(path.read_bytes()))
    return Ed25519PrivateKey.from_private_bytes(raw)


def server_public_key() -> str:
    pub = _server_key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(pub).decode()


def my_base() -> str:
    return (get_settings().public_base_url or f"https://{idn.domain()}").rstrip("/")


def server_card() -> dict[str, Any]:
    return {"protocol": PROTOCOL, "domain": idn.domain(), "server_key": server_public_key(), "inbox": my_base() + "/hoola/inbox",
            "lookup": my_base() + "/hoola/lookup", "share": my_base() + "/hoola/share", "software": "Hoola (Santosh core)"}


def agent_card() -> dict[str, Any]:
    """v0.116 the A2A 1.0 agent card lives in a2a.py (kept here for older callers)."""
    from . import a2a as a2a_mod
    return a2a_mod.agent_card()


def _sign_request(method: str, path: str, body: bytes) -> dict[str, str]:
    date = formatdate(usegmt=True)
    digest = hashlib.sha256(body).hexdigest()
    msg = f"{method.upper()}\n{path}\n{idn.domain()}\n{date}\n{digest}".encode()
    sig = base64.b64encode(_server_key().sign(msg)).decode()
    return {"X-Hoola-Server": idn.domain(), "Date": date, "X-Hoola-Digest": digest, "X-Hoola-Sig": sig,
            "Content-Type": "application/json"}


def _remote_card(domain: str) -> dict[str, Any]:
    hit = _cards.get(domain)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    c = _client()
    try:
        r = c.get(base_url(domain) + "/.well-known/hoola.json")
        if r.status_code != 200:
            raise FedError(f"{domain} Hoola server nahi lagta ({r.status_code}).")
        card = r.json()
    except httpx.HTTPError as e:
        raise FedError(f"{domain} se baat nahi hui ({type(e).__name__}).")
    finally:
        _close(c)
    if card.get("protocol") != PROTOCOL or (card.get("domain") or "").lower() != domain.lower() or not card.get("server_key"):
        raise FedError(f"{domain} ka Hoola card sahi nahi hai.")
    if len(_cards) > 2000:
        _cards.clear()
    _cards[domain] = (time.time(), card)
    return card


def verify_request(method: str, path: str, headers: dict[str, str], body: bytes) -> str:
    """Checks a request from another Hoola server. Returns its domain."""
    if not enabled():
        raise FedError("federation band hai")
    h = {k.lower(): v for k, v in headers.items()}
    domain = (h.get("x-hoola-server") or "").lower()
    if not domain or blocked(domain) or domain == idn.domain():
        raise FedError("server allowed nahi")
    try:
        when = parsedate_to_datetime(h.get("date", "")).timestamp()
    except Exception:
        raise FedError("date galat")
    if abs(time.time() - when) > SKEW:
        raise FedError("purani request")
    digest = hashlib.sha256(body).hexdigest()
    if digest != h.get("x-hoola-digest"):
        raise FedError("digest galat")
    card = _remote_card(domain)
    msg = f"{method.upper()}\n{path}\n{domain}\n{h.get('date')}\n{digest}".encode()
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(card["server_key"])).verify(base64.b64decode(h.get("x-hoola-sig", "")), msg)
    except Exception:
        raise FedError("server signature galat")
    if len(_rate) > 5000:
        _rate.clear()
    win = _rate.setdefault(domain, [])
    now = time.time()
    win[:] = [t for t in win if now - t < 60]
    if len(win) >= 240:
        raise FedError("bahut requests")
    win.append(now)
    return domain


# ---------------------------------------------------------------- outgoing
def send(env: dict[str, Any]) -> dict[str, Any]:
    if not enabled():
        return {"ok": False, "status": "refused", "reason": "Is server par doosre servers se judna band hai."}
    _, domain = idn.split(env["to"])
    if blocked(domain):
        return {"ok": False, "status": "refused", "reason": "Yeh server block hai."}
    try:
        _remote_card(domain)
        body = json.dumps(env, ensure_ascii=False, separators=(",", ":")).encode()
        path = "/hoola/inbox"
        c = _client()
        try:
            # always our own idea of the server's address (never a URL the remote card suggests)
            r = c.post(base_url(domain) + path, content=body, headers=_sign_request("POST", path, body))
        finally:
            _close(c)
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code >= 400:
            return {"ok": False, "status": "refused", "reason": str(data.get("detail") or data.get("reason") or r.status_code)[:200]}
        return data if isinstance(data, dict) else {"ok": True, "status": "sent"}
    except FedError as e:
        return {"ok": False, "status": "failed", "reason": str(e)}
    except httpx.HTTPError as e:
        return {"ok": False, "status": "failed", "reason": f"{domain} tak nahi pahuncha ({type(e).__name__})"}


def lookup(handle: str, domain: str) -> str:
    from .service import NetError
    handle, domain = handle.strip().lstrip("@").lower(), domain.strip().lower()
    if domain == idn.domain():
        row = idn.by_handle(handle)
        if row is None:
            raise NetError(f"@{handle} nahi mila.")
        return idn.address(row.uid)
    if not enabled() or blocked(domain):
        raise NetError("Is server se judna band hai.")
    try:
        _remote_card(domain)
        c = _client()
        try:
            r = c.get(base_url(domain) + "/hoola/lookup", params={"handle": handle})
        finally:
            _close(c)
    except (FedError, httpx.HTTPError) as e:
        raise NetError(f"@{handle}@{domain} dhoondh nahi paye: {e}")
    if r.status_code != 200:
        raise NetError(f"@{handle}@{domain} nahi mila.")
    card = r.json()
    addr = str(card.get("address") or "")
    if idn.split(addr)[1] != domain or not card.get("public_key"):
        raise NetError("Us server ka jawab sahi nahi tha.")
    card["server"] = domain
    card["handle"] = f"{card.get('handle', handle)}@{domain}"
    idn.remember_peer(card)
    return addr


def fetch_share(sender: str, share_id: str, me_addr: str) -> tuple[str, str, bytes, str]:
    from .service import NetError
    from urllib.parse import quote, unquote
    _, domain = idn.split(sender)
    if not re.fullmatch(r"sh_[\w-]{10,40}", share_id or ""):
        raise NetError("File ka pata galat hai.")
    path = f"/hoola/share/{share_id}?for={quote(me_addr, safe='')}"
    limit = 26 * 1024 * 1024
    try:
        _remote_card(domain)
        c = _client()
        try:
            with c.stream("GET", base_url(domain) + path, headers=_sign_request("GET", path, b"")) as r:
                if r.status_code != 200:
                    raise NetError("File ab uplabdh nahi hai.")
                if int(r.headers.get("content-length") or 0) > limit:
                    raise NetError("File bahut badi hai.")
                buf = bytearray()
                for chunk in r.iter_bytes():
                    buf += chunk
                    if len(buf) > limit:
                        raise NetError("File bahut badi hai.")
                headers = dict(r.headers)
        finally:
            _close(c)
    except (FedError, httpx.HTTPError) as e:
        raise NetError(f"File nahi aayi: {e}")
    name = unquote(headers.get("x-hoola-name", "file"))
    return name, headers.get("content-type", "application/octet-stream"), bytes(buf), headers.get("x-hoola-sha256", "")


# ---------------------------------------------------------------- incoming (called by the HTTP routes)
def inbox(headers: dict[str, str], body: bytes) -> dict[str, Any]:
    domain = verify_request("POST", "/hoola/inbox", headers, body)
    try:
        env = json.loads(body.decode())
    except ValueError:
        raise FedError("envelope JSON nahi")
    if not isinstance(env, dict) or idn.split(env.get("from", ""))[1] != domain:
        raise FedError("bhejne wala is server ka nahi")
    if not idn.is_local(env.get("to", "")):
        raise FedError("yeh avatar is server par nahi")
    from .service import receive
    return receive(env)


def public_lookup(handle: str) -> dict[str, Any] | None:
    row = idn.by_handle(handle)
    if row is None:
        return None
    c = idn.my_card(row.tenant_id)
    return {k: c.get(k, "") for k in ("address", "handle", "owner_name", "avatar_name", "avatar_gender", "avatar_look", "public_key", "verified",
                              "business", "language")}


def serve_share(headers: dict[str, str], share_id: str, for_addr: str) -> tuple[str, str, bytes, str]:
    from urllib.parse import quote
    domain = verify_request("GET", f"/hoola/share/{share_id}?for={quote(for_addr, safe='')}", headers, b"")
    if idn.split(for_addr)[1] != domain:
        raise FedError("yeh file us server ke liye nahi")
    from .share import fetch_share as local_fetch
    return local_fetch(share_id, for_addr)


def a2a(body: dict[str, Any]) -> dict[str, Any]:
    """v0.116 moved to a2a.rpc (A2A 1.0 + 0.3)."""
    from . import a2a as a2a_mod
    return a2a_mod.rpc(body)
