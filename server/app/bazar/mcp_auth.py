"""One-tap account linking for MCP apps (Swiggy, Zomato, Zepto, District) using the MCP authorization spec:

  protected-resource metadata -> authorization-server metadata -> Dynamic Client Registration (RFC 7591)
  -> authorize with PKCE S256 -> code exchange -> encrypted token bundle (access + rotating refresh).

The user signs in on the provider's own page (phone + OTP there); Santosh never sees their OTP.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import secrets
import time
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from sqlalchemy import select

from ..config import get_settings as core_settings
from .db import Connection, KVState
from .security import vault

TIMEOUT = 20


class LinkError(Exception):
    pass


def _origin(url: str) -> str:
    u = urlparse(url)
    return f"{u.scheme}://{u.netloc}"


def redirect_uri() -> str:
    base = core_settings().public_base_url.rstrip("/")
    if not base.startswith("https://"):
        raise LinkError("PUBLIC_BASE_URL must be an https address for app linking.")
    return f"{base}/bazar/link/callback"


def discover(resource_url: str, client: httpx.Client) -> dict[str, Any]:
    """Find the authorization server for an MCP endpoint."""
    origin = _origin(resource_url)
    path = urlparse(resource_url).path.rstrip("/")
    as_url = ""
    for cand in ([f"{origin}/.well-known/oauth-protected-resource{path}"] if path else []) + \
                [f"{origin}/.well-known/oauth-protected-resource"]:
        try:
            r = client.get(cand)
            if r.status_code == 200:
                servers = r.json().get("authorization_servers") or []
                if servers:
                    as_url = servers[0]
                    break
        except (httpx.HTTPError, ValueError):
            continue
    as_url = as_url or origin
    a = urlparse(as_url)
    as_origin, as_path = f"{a.scheme}://{a.netloc}", a.path.rstrip("/")
    cands = [f"{as_origin}/.well-known/oauth-authorization-server{as_path}", f"{as_url.rstrip('/')}/.well-known/oauth-authorization-server",
             f"{as_origin}/.well-known/openid-configuration{as_path}", f"{as_origin}/.well-known/oauth-authorization-server"]
    for cand in dict.fromkeys(cands):
        try:
            r = client.get(cand)
            if r.status_code == 200:
                meta = r.json()
                if meta.get("authorization_endpoint") and meta.get("token_endpoint"):
                    return meta
        except (httpx.HTTPError, ValueError):
            continue
    raise LinkError("This app's sign-in server could not be found.")


def _register(meta: dict[str, Any], client: httpx.Client) -> dict[str, Any]:
    reg = meta.get("registration_endpoint")
    if not reg:
        raise LinkError("This app does not allow new apps to register automatically. Partner access is needed.")
    r = client.post(reg, json={"client_name": "Santosh", "redirect_uris": [redirect_uri()],
                               "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
                               "token_endpoint_auth_method": "none"})
    if r.status_code >= 400:
        raise LinkError(f"The app refused Santosh's registration ({r.status_code}): {r.text[:160]}")
    return r.json()


def _pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def start(session, user_id: str, provider: str, resource_url: str, client: httpx.Client | None = None) -> str:
    """Returns the provider's sign-in URL. State is stored server-side for 15 minutes."""
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=True)
    try:
        meta = discover(resource_url, client)
        cache_key = f"mcp_client:{meta['issuer'] if meta.get('issuer') else meta['authorization_endpoint']}:{redirect_uri()}"
        row = session.get(KVState, cache_key)
        reg = json.loads(row.value) if row else None
        if not reg:
            reg = _register(meta, client)
            session.merge(KVState(key=cache_key, value=json.dumps(reg)))
        verifier, challenge = _pkce()
        state = secrets.token_urlsafe(24)
        session.merge(KVState(key=f"mcp_state:{state}", value=json.dumps({
            "user_id": user_id, "provider": provider, "verifier": verifier, "client_id": reg["client_id"],
            "client_secret": reg.get("client_secret", ""), "token_endpoint": meta["token_endpoint"], "resource": resource_url,
            "exp": time.time() + 900})))
        scopes = meta.get("scopes_supported") or []
        q = {"response_type": "code", "client_id": reg["client_id"], "redirect_uri": redirect_uri(), "state": state,
             "code_challenge": challenge, "code_challenge_method": "S256", "resource": resource_url}
        if "mcp:tools" in scopes:
            q["scope"] = " ".join(s for s in scopes if s.startswith("mcp:")) or "mcp:tools"
        sep = "&" if "?" in meta["authorization_endpoint"] else "?"
        return meta["authorization_endpoint"] + sep + urlencode(q)
    finally:
        if own:
            client.close()


def _token_request(endpoint: str, data: dict[str, str], client: httpx.Client) -> dict[str, Any]:
    r = client.post(endpoint, data=data, headers={"Accept": "application/json"})
    if r.status_code in (400, 415) and "invalid_grant" not in r.text:
        r = client.post(endpoint, json=data, headers={"Accept": "application/json"})  # some servers want JSON
    if r.status_code >= 400:
        raise LinkError(f"Token exchange failed ({r.status_code}): {r.text[:160]}")
    tok = r.json()
    if not tok.get("access_token"):
        raise LinkError("The app did not return an access token.")
    return tok


def finish(session, state: str, code: str, client: httpx.Client | None = None) -> tuple[str, str]:
    """Exchange the code. Returns (user_id, provider)."""
    row = session.get(KVState, f"mcp_state:{state}")
    if not row:
        raise LinkError("This sign-in link expired. Please try again from Santosh.")
    st = json.loads(row.value)
    session.delete(row)
    if time.time() > st["exp"]:
        raise LinkError("This sign-in link expired. Please try again from Santosh.")
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT)
    try:
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri(),
                "client_id": st["client_id"], "code_verifier": st["verifier"], "resource": st["resource"]}
        if st.get("client_secret"):
            data["client_secret"] = st["client_secret"]
        tok = _token_request(st["token_endpoint"], data, client)
    finally:
        if own:
            client.close()
    save(session, st["user_id"], st["provider"], tok, st)
    return st["user_id"], st["provider"]


def save(session, user_id: str, provider: str, tok: dict[str, Any], st: dict[str, Any]) -> None:
    for c in session.scalars(select(Connection).where(Connection.user_id == user_id, Connection.provider == provider)).all():
        c.status = "replaced"
    exp = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(seconds=int(tok.get("expires_in") or 3600))
    bundle = {"access_token": tok["access_token"], "refresh_token": tok.get("refresh_token", ""),
              "token_endpoint": st["token_endpoint"], "client_id": st["client_id"], "client_secret": st.get("client_secret", ""),
              "resource": st.get("resource", "")}
    session.add(Connection(user_id=user_id, provider=provider, token_enc=vault().seal(json.dumps(bundle)), status="active",
                           expires_at=exp))
    session.flush()


def access_token(session, conn: Connection, client: httpx.Client | None = None) -> str:
    """Decrypts the token; refreshes (rotating refresh token) when it is about to expire."""
    raw = vault().open(conn.token_enc) if conn.token_enc else ""
    if not raw.startswith("{"):
        return raw  # a plain token linked by the operator
    b = json.loads(raw)
    soon = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(minutes=10)
    if conn.expires_at is None or conn.expires_at > soon or not b.get("refresh_token"):
        return b["access_token"]
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT)
    try:
        data = {"grant_type": "refresh_token", "refresh_token": b["refresh_token"], "client_id": b["client_id"]}
        if b.get("client_secret"):
            data["client_secret"] = b["client_secret"]
        try:
            tok = _token_request(b["token_endpoint"], data, client)
        except LinkError:
            conn.status = "expired"
            session.flush()
            raise
    finally:
        if own:
            client.close()
    b["access_token"] = tok["access_token"]
    b["refresh_token"] = tok.get("refresh_token") or b["refresh_token"]
    conn.token_enc = vault().seal(json.dumps(b))
    conn.expires_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(seconds=int(tok.get("expires_in") or 3600))
    session.flush()
    return b["access_token"]
