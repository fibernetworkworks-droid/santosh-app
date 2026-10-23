"""Multi-tenant accounts: 'Sign in with Google' creates the user and connects Gmail/Calendar/Drive/Docs/Sheets
in one consent. Tokens are encrypted at rest; the phone holds an opaque session token.

This is the product foundation. Your single-user instance keeps working via the legacy API key.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import select

from .config import get_settings
from .db import AppSession, OAuthConnection, OAuthState, User, as_utc, now, session

log = logging.getLogger("santosh.accounts")

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"

# One consent covers sign-in + all the Google features Santosh uses.
GOOGLE_SCOPES = [
    "openid", "email", "profile",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
]


# The Hoola Console signs people in with these only: name + email are not "sensitive" scopes, so Google lets ANY
# Google account in without app verification. Gmail / Drive / Calendar are asked for separately ("Google apps jodiye").
SIGNIN_SCOPES = ["openid", "email", "profile"]


class AuthError(Exception):
    pass


class SignupClosed(AuthError):
    pass


def signup_allowed(email: str) -> bool:
    """Can this email make a NEW Hoola? Existing accounts always sign in; the server owner always may."""
    st = get_settings()
    if (getattr(st, "hoola_signup", "open") or "open").strip().lower() != "invite":
        return True
    e = (email or "").strip().lower()
    if not e or is_owner_email(e):
        return bool(e)
    for item in (getattr(st, "hoola_signup_allow", "") or "").split(","):
        item = item.strip().lower()
        if item and (e == item or (item.startswith("@") and e.endswith(item))):
            return True
    return False


# ---------------- token encryption ----------------
def _fernet():
    from cryptography.fernet import Fernet
    st = get_settings()
    if not st.secret_key:
        raise AuthError("SECRET_KEY server par set nahi hai (token encryption ke liye zaroori).")
    key = base64.urlsafe_b64encode(hashlib.sha256(st.secret_key.encode()).digest())
    return Fernet(key)


def encrypt(text: str | None) -> str | None:
    if not text:
        return None
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str | None) -> str | None:
    if not token:
        return None
    return _fernet().decrypt(token.encode()).decode()


# ---------------- OAuth ----------------
def oauth_configured() -> bool:
    st = get_settings()
    return bool(st.google_oauth_client_id and st.google_oauth_client_secret and st.public_base_url and st.secret_key)


def _redirect_uri() -> str:
    return get_settings().public_base_url.rstrip("/") + "/auth/google/callback"


def start_google(extra_state: str = "", web: bool = False, apps: bool = False) -> str:
    """Return the Google consent URL the app should open. web=True = the Hoola Console (v0.142): the callback then
    hands the browser a one-time code instead of the app's deep link. The console's sign-in asks only for name + email
    (no Google review needed for any user); apps=True is its "Google apps jodiye" step (Gmail, Drive, Calendar, Docs,
    Sheets, added to what she already granted). The phone app keeps its one consent for everything."""
    if not oauth_configured():
        raise AuthError("Google sign-in server par configure nahi hai.")
    st = get_settings()
    state = ("cw_" + ("g." if apps else "") if web else "") + secrets.token_urlsafe(24)
    with session() as s:
        s.add(OAuthState(state=state))
    signin_only = web and not apps
    params = {
        "client_id": st.google_oauth_client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SIGNIN_SCOPES if signin_only else GOOGLE_SCOPES),
        "include_granted_scopes": "true",
    }
    if signin_only:
        params["prompt"] = "select_account"   # just pick the account; no consent screen for basic profile
    else:
        params["access_type"] = "offline"     # get a refresh token
        params["prompt"] = "consent"          # ensure a refresh token every time
    params["state"] = state                   # kept last: callers read it off the end of the link
    return f"{GOOGLE_AUTH}?{urlencode(params)}"


def _consume_state(state: str) -> bool:
    cutoff = now() - timedelta(minutes=15)
    with session() as s:
        row = s.get(OAuthState, state)
        if not row:
            return False
        ok = as_utc(row.created_at) >= cutoff
        s.delete(row)
        # opportunistic cleanup of old states
        for old in s.scalars(select(OAuthState).where(OAuthState.created_at < cutoff)).all():
            s.delete(old)
        return ok


async def finish_google(code: str, state: str) -> dict:
    """Exchange the code, upsert the user, store tokens, return a session token for the app."""
    if not _consume_state(state):
        raise AuthError("Sign-in request purana ya galat hai. Dobara koshish kijiye.")
    st = get_settings()
    data = {
        "code": code,
        "client_id": st.google_oauth_client_id,
        "client_secret": st.google_oauth_client_secret,
        "redirect_uri": _redirect_uri(),
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(GOOGLE_TOKEN, data=data)
        if r.status_code != 200:
            raise AuthError(f"Google token exchange fail: {r.text[:200]}")
        tok = r.json()
        ui = await c.get(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {tok['access_token']}"})
        if ui.status_code != 200:
            raise AuthError("Google profile nahi mila.")
        info = ui.json()
    email = (info.get("email") or "").lower()
    if not email:
        raise AuthError("Google account se email nahi mila.")
    expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
    with session() as s:
        user = s.scalar(select(User).where(User.email == email))
        if not user and not signup_allowed(email):
            raise SignupClosed("Hoola abhi invite se khul raha hai. Is Google account ke liye abhi jagah nahi hai; "
                               "Hoola team se invite maangiye.")
        if not user:
            user = User(email=email, name=info.get("name", ""), google_sub=info.get("sub"))
            s.add(user)
            s.flush()
        else:
            user.name = info.get("name", user.name)
            user.google_sub = info.get("sub", user.google_sub)
        user.last_login = now()
        uid = user.id
        conn = s.scalar(select(OAuthConnection).where(OAuthConnection.user_id == uid, OAuthConnection.provider == "google"))
        if not conn:
            conn = OAuthConnection(user_id=uid, provider="google")
            s.add(conn)
        conn.account_email = email
        conn.access_token_enc = encrypt(tok["access_token"])
        if tok.get("refresh_token"):                 # Google omits it on re-consent sometimes; keep the old one
            conn.refresh_token_enc = encrypt(tok["refresh_token"])
        conn.scopes = tok.get("scope") or conn.scopes or " ".join(SIGNIN_SCOPES)
        conn.last_error = None                       # a fresh sign-in clears an old "login expired"
        conn.expiry = expiry
    sess_token = issue_session(uid)
    return {"session_token": sess_token, "user_id": uid, "email": email, "name": info.get("name", "")}


# ---------------- sessions ----------------
def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with session() as s:
        s.add(AppSession(token_hash=_hash(token), user_id=user_id))
    return token


def is_owner_email(email: str) -> bool:
    st = get_settings()
    owners = {e.strip().lower() for e in (st.owner_emails or st.email_address or "").split(",") if e.strip()}
    return bool(email) and email.strip().lower() in owners


def tenant_of_user(user_id: str) -> str:
    """Every signed-in person gets their own tenant (their user id). The server owner's Google account maps to the
    owner tenant, so their existing chats, reminders and .env-connected email/calendar/drive stay theirs alone."""
    with session() as s:
        u = s.get(User, user_id)
        if u and is_owner_email(u.email):
            return get_settings().tenant_id
    return user_id


def tenant_for_session(token: str) -> str | None:
    with session() as s:
        row = s.scalar(select(AppSession).where(AppSession.token_hash == _hash(token)))
        if not row:
            return None
        row.last_seen = now()
        return row.user_id


def user_info(user_id: str) -> dict | None:
    with session() as s:
        u = s.get(User, user_id)
        if not u:
            return None
        conns = s.scalars(select(OAuthConnection).where(OAuthConnection.user_id == user_id)).all()
        return {
            "id": u.id, "email": u.email, "name": u.name,
            "connections": [{"provider": c.provider, "account": c.account_email,
                             "scopes": c.scopes.split(), "connected_at": as_utc(c.created_at).isoformat()} for c in conns],
        }


def disconnect(user_id: str, provider: str) -> bool:
    with session() as s:
        c = s.scalar(select(OAuthConnection).where(OAuthConnection.user_id == user_id, OAuthConnection.provider == provider))
        if not c:
            return False
        s.delete(c)
        return True


def logout(token: str) -> None:
    with session() as s:
        row = s.scalar(select(AppSession).where(AppSession.token_hash == _hash(token)))
        if row:
            s.delete(row)
