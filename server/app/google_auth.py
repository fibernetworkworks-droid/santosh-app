"""Per-user Google API credentials from stored OAuth tokens (auto-refreshing).

The Google feature modules (gcal, gdrive, and later gmail) use credentials_for(tenant) when the user
signed in with Google; your single-user instance keeps using the .env app password / service account.
"""
from __future__ import annotations

import logging
import time

from sqlalchemy import select

from . import accounts
from .config import get_settings
from .db import OAuthConnection, now, session

log = logging.getLogger("santosh.google_auth")


def _user_ids(s, tenant_id: str) -> list[str]:
    """The owner tenant ('default') holds the owner's Google sign-in under their user id."""
    ids = [tenant_id]
    if tenant_id == get_settings().tenant_id:
        from .db import User
        ids += [u.id for u in s.scalars(select(User)).all() if accounts.is_owner_email(u.email)]
    return ids


def _google_conn(s, tenant_id: str):
    return s.scalars(select(OAuthConnection).where(OAuthConnection.user_id.in_(_user_ids(s, tenant_id)),
                                                   OAuthConnection.provider == "google")
                     .order_by(OAuthConnection.id.desc())).first()


class GoogleReconnect(Exception):
    """Google refused to refresh the sign-in (expired / revoked / app in Testing mode): she must connect again.
    The message is written for her (and the model)."""


def reconnect_message(email: str, err: str) -> str:
    e = (err or "").lower()
    why = ("Google ne login wapas le liya / expire kar diya" if "invalid_grant" in e or "expired" in e or "revoked" in e
           else "Google ne login refresh nahi kiya")
    msg = (f"Aapke Google account ({email or 'Google'}) ka login Hoola ke paas ab nahi chal raha ({why}). Isliye Google Drive, "
           "Gmail, Calendar, Sheets abhi nahi khul rahe. Theek karne ke liye: app mein Profile > Google Drive > "
           "'Google Drive jodiye' dabaiye aur Google ke page par saare boxes (Drive bhi) tick kijiye.")
    if "invalid_grant" in e:
        msg += (" Agar yeh har 7 din mein hota hai: Google Cloud Console > OAuth consent screen par app abhi 'Testing' mein hai; "
                "'Publish app' (In production) kijiye, tab login 7 din mein expire nahi hoga.")
    return msg


def mark_error(tenant_id: str, err: str | None) -> None:
    with session() as s:
        conn = _google_conn(s, tenant_id)
        if conn is not None:
            conn.last_error = (err or None) and str(err)[:500]


import contextvars as _cv
# v0.662 set by the worker's slots: only BACKGROUND watchers (mail watch 60 s, calendar 120 s) wait out the backoff;
# her own chat ask always tries Google again (she may have just re-linked)
BACKGROUND: "_cv.ContextVar[bool]" = _cv.ContextVar("google_background", default=False)
_DEAD: dict[str, dict] = {}
DEAD_BACKOFF_S = (1800, 7200, 21600)     # 30 min, 2 h, then every 6 h
TELL_EVERY_S = 24 * 3600


def _tok_key(creds) -> str:
    import hashlib
    return hashlib.sha256(str(getattr(creds, "refresh_token", "") or "").encode()).hexdigest()[:16]


def _note_dead(tenant_id: str, tok: str, msg: str) -> None:
    """v0.662 remember the refusal (backoff grows) and TELL her - once a day, in her chat - that mail alerts and meeting
    nudges have stopped. Before, only a chat tool that happened to touch Google said anything; the watchers failed
    in silence."""
    prev = _DEAD.get(tenant_id) or {}
    n = (prev.get("n", 0) + 1) if prev.get("tok") == tok else 1
    told = prev.get("told", 0.0) if prev.get("tok") == tok else 0.0
    _DEAD[tenant_id] = {"tok": tok, "n": n, "msg": msg, "told": told,
                        "until": time.time() + DEAD_BACKOFF_S[min(n, len(DEAD_BACKOFF_S)) - 1]}
    if time.time() - told < TELL_EVERY_S:
        return
    _DEAD[tenant_id]["told"] = time.time()
    try:
        from . import convs
        from .events import bus, notify
        conv = convs.current(tenant_id)
        if conv:
            notify(conv, msg + " Tab tak naye mail aur meeting ki khabar nahi aa payegi.")
            bus.publish(conv, "google_reconnect", {"text": msg})
    except Exception:
        log.exception("google reconnect notice failed")


def refresh(creds, tenant_id: str, email: str = "") -> None:
    """creds.refresh, but a refused refresh becomes GoogleReconnect (and is remembered for the status screen)."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    tok = _tok_key(creds)
    dead = _DEAD.get(tenant_id)
    if dead and dead["tok"] == tok and time.time() < dead["until"] and BACKGROUND.get():
        # v0.662 a refused sign-in is not asked again every minute (mail watch 60 s, calendar 120 s: her log showed
        # invalid_grant forever) - the same dead token waits out its backoff; a NEW sign-in has a new token and goes
        raise GoogleReconnect(dead["msg"])
    try:
        creds.refresh(Request())
    except RefreshError as e:
        log.warning("google sign-in refresh refused for %s: %s", tenant_id, e)
        mark_error(tenant_id, str(e))
        if not email:
            with session() as s:
                c = _google_conn(s, tenant_id)
                email = c.account_email if c else ""
        msg = reconnect_message(email, str(e))
        _note_dead(tenant_id, tok, msg)
        raise GoogleReconnect(msg) from None
    _DEAD.pop(tenant_id, None)


def has_google(tenant_id: str) -> bool:
    with session() as s:
        return _google_conn(s, tenant_id) is not None


def credentials_for(tenant_id: str, scopes=None):
    """A google.oauth2.credentials.Credentials that refreshes itself and persists the new access token."""
    from google.oauth2.credentials import Credentials
    st = get_settings()
    with session() as s:
        conn = _google_conn(s, tenant_id)
        if not conn or not conn.refresh_token_enc:
            return None
        creds = Credentials(
            token=accounts.decrypt(conn.access_token_enc),
            refresh_token=accounts.decrypt(conn.refresh_token_enc),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=st.google_oauth_client_id,
            client_secret=st.google_oauth_client_secret,
            scopes=scopes or conn.scopes.split(),
        )
        email = conn.account_email
    if not creds.valid:
        refresh(creds, tenant_id, email)
        save_token(tenant_id, creds)
    return creds


def save_token(tenant_id: str, creds) -> None:
    with session() as s:
        conn = _google_conn(s, tenant_id)
        if conn:
            conn.access_token_enc = accounts.encrypt(creds.token)
            if creds.expiry:
                conn.expiry = creds.expiry
            conn.last_error = None
