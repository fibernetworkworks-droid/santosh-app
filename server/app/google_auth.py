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


def has_google(tenant_id: str) -> bool:
    with session() as s:
        return _google_conn(s, tenant_id) is not None


def credentials_for(tenant_id: str, scopes=None):
    """A google.oauth2.credentials.Credentials that refreshes itself and persists the new access token."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
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
    if not creds.valid:
        try:
            creds.refresh(Request())
            with session() as s:
                conn = _google_conn(s, tenant_id)
                if conn:
                    conn.access_token_enc = accounts.encrypt(creds.token)
                    if creds.expiry:
                        conn.expiry = creds.expiry
        except Exception as e:
            log.warning("google token refresh failed for %s: %s", tenant_id, e)
            raise
    return creds
