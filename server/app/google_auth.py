"""Per-user Google API credentials from stored OAuth tokens (auto-refreshing).

The Google feature modules (gcal, gdrive, and later gmail) use credentials_for(tenant) when the user
signed in with Google; your single-user instance keeps using the .env app password / service account.
"""
from __future__ import annotations

import logging

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


def refresh(creds, tenant_id: str, email: str = "") -> None:
    """creds.refresh, but a refused refresh becomes GoogleReconnect (and is remembered for the status screen)."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    try:
        creds.refresh(Request())
    except RefreshError as e:
        log.warning("google sign-in refresh refused for %s: %s", tenant_id, e)
        mark_error(tenant_id, str(e))
        if not email:
            with session() as s:
                c = _google_conn(s, tenant_id)
                email = c.account_email if c else ""
        raise GoogleReconnect(reconnect_message(email, str(e))) from None


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
