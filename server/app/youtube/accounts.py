"""Which YouTube channels (Google accounts) a person connected, and connecting one.

Order: accounts connected in the app (Profile > YouTube) -> their Google sign-in (if it granted YouTube).
Public lookups (search, any video's stats) also work without sign-in through the server's YOUTUBE_API_KEY.
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select

from .. import accounts as acc
from ..config import get_settings
from ..db import MailLinkState, as_utc, now, session
from ..mailbox import accounts as mail_acc
from .client import NotConnected, YouTubeClient, YTError
from .models import YouTubeAccount

YT_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"        # read + manage the channel, comments
SCOPES = ["openid", "email", "profile", YT_SCOPE,
          "https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]

def _token(account_id: str, force: bool) -> str:
    st = get_settings()
    with session() as s:
        a = s.get(YouTubeAccount, account_id)
        if a is None:
            raise NotConnected("Yeh Google account ab Santosh se juda nahi hai.")
        exp = as_utc(a.expiry)
        if not force and a.access_token_enc and exp and exp > now() + timedelta(seconds=90):
            return acc.decrypt(a.access_token_enc) or ""
        refresh = acc.decrypt(a.refresh_token_enc)
    if not refresh:
        raise YTError("YouTube ka login expire ho gaya. Profile > YouTube se dobara jodiye.")
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "refresh_token": refresh, "grant_type": "refresh_token"})
    except Exception as e:
        with session() as s:
            a = s.get(YouTubeAccount, account_id)
            if a:
                a.status, a.last_error = "error", str(e)[:500]
        raise YTError(f"Google login refresh nahi hua: {e}")
    with session() as s:
        a = s.get(YouTubeAccount, account_id)
        a.access_token_enc = acc.encrypt(tok["access_token"])
        if tok.get("refresh_token"):
            a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
    return tok["access_token"]


def _signin_conn(s, tenant: str):
    from ..google_auth import _google_conn
    c = _google_conn(s, tenant)
    if c and YT_SCOPE in (c.scopes or "").split() and c.refresh_token_enc:
        return c
    return None


def clients(tenant: str) -> list[YouTubeClient]:
    st = get_settings()
    out: list[YouTubeClient] = []
    with session() as s:
        rows = s.scalars(select(YouTubeAccount).where(YouTubeAccount.tenant_id == tenant)
                         .order_by(YouTubeAccount.is_default.desc(), YouTubeAccount.created_at)).all()
        out += [YouTubeClient(a.id, a.address, lambda force, i=a.id: _token(i, force), st.youtube_api_key, mail_acc._http)
                for a in rows]
        c = _signin_conn(s, tenant)
        if c and c.account_email.lower() not in {b.address for b in out}:
            out.append(YouTubeClient("google", c.account_email, mail_acc._signin_token(tenant), st.youtube_api_key, mail_acc._http))
    return out


def public_client(tenant: str) -> YouTubeClient:
    """For search / any public video: the server key, else the user's own sign-in."""
    st = get_settings()
    if st.youtube_api_key:
        return YouTubeClient("public", "", None, st.youtube_api_key, mail_acc._http)
    cs = clients(tenant)
    if cs:
        return cs[0]
    raise NotConnected("YouTube dhoondhne ke liye server par YOUTUBE_API_KEY chahiye, ya Profile > YouTube se apna "
                       "Google account jodiye.")


def has_youtube(tenant: str) -> bool:
    try:
        return bool(clients(tenant))
    except Exception:
        return False


def get_client(tenant: str, which: str | None = None) -> YouTubeClient:
    cs = clients(tenant)
    if not cs:
        raise NotConnected("Aapka YouTube channel abhi Santosh se juda nahi hai. App mein Profile > YouTube > "
                           "'YouTube jodiye' dabaiye.")
    if not which:
        return cs[0]
    w = which.strip().lower()
    for c in cs:
        if c.key.lower() == w or c.address == w:
            return c
    raise YTError(f"'{which}' account nahi mila. Jude hue: {', '.join(c.address for c in cs)}")


def views(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(YouTubeAccount).where(YouTubeAccount.tenant_id == tenant)).all()
        status = {a.id: (a.status, a.last_error) for a in rows}
        chans = {a.id: a.channel_title for a in rows}
    out = []
    for i, c in enumerate(clients(tenant)):
        st, err = status.get(c.key, ("ok", ""))
        out.append({"key": c.key, "kind": "google", "address": c.address, "default": i == 0, "status": st, "error": err,
                    "removable": c.key != "google", "channel": chans.get(c.key, "")})
    return out


def remove(tenant: str, key: str) -> bool:
    with session() as s:
        a = s.get(YouTubeAccount, key)
        if a is None or a.tenant_id != tenant:
            return False
        s.delete(a)
    return True


# ---------------- connecting ----------------
def oauth_ready() -> bool:
    return mail_acc.oauth_ready("google")


def is_link_state(state: str) -> bool:
    return (state or "").startswith("gyt_")


def start_link(tenant: str, login_hint: str = "") -> str:
    if not oauth_ready():
        raise YTError("YouTube jodne ke liye server par Google sign-in (GOOGLE_OAUTH_CLIENT_ID/SECRET, "
                         "PUBLIC_BASE_URL, SECRET_KEY) set hona chahiye.")
    st = get_settings()
    state = "gyt_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="youtube"))
    q = {"client_id": st.google_oauth_client_id, "redirect_uri": acc._redirect_uri(), "response_type": "code",
         "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent", "state": state,
         "include_granted_scopes": "true"}
    if login_hint:
        q["login_hint"] = login_hint
    return mail_acc.GOOGLE_AUTH + "?" + urlencode(q)


def finish_link(code: str, state: str) -> dict[str, Any]:
    st = get_settings()
    with session() as s:
        row = s.get(MailLinkState, state)
        if row is None or row.provider != "youtube" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise YTError("Yeh link purana ho gaya. App se dobara 'YouTube jodiye' dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "redirect_uri": acc._redirect_uri(), "grant_type": "authorization_code"})
        if YT_SCOPE not in (tok.get("scope") or "").split():
            raise YTError("YouTube ki permission nahi di gayi. Dobara jodte waqt 'YouTube account manage karna' allow kijiye.")
        info = mail_acc._get("https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
    except mail_acc.MailError as e:
        raise YTError(str(e))
    address = (info.get("email") or "").lower()
    if "@" not in address or not tok.get("refresh_token"):
        raise YTError("Google se account ya refresh token nahi mila; dobara jodiye.")
    with session() as s:
        n = len(s.scalars(select(YouTubeAccount.id).where(YouTubeAccount.tenant_id == tenant)).all())
        a = s.scalar(select(YouTubeAccount).where(YouTubeAccount.tenant_id == tenant, YouTubeAccount.address == address))
        if a is None:
            a = YouTubeAccount(tenant_id=tenant, address=address, is_default=(n == 0))
            s.add(a)
        a.access_token_enc = acc.encrypt(tok["access_token"])
        a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
        s.flush()
        key = a.id
    channel = ""
    try:      # remember which channel this is
        ch = YouTubeClient(key, address, lambda force: _token(key, force), "", mail_acc._http).get(
            "/channels", auth=True, part="snippet", mine="true").get("items", [])
        if ch:
            with session() as s:
                row = s.get(YouTubeAccount, key)
                row.channel_id, row.channel_title = ch[0]["id"], ch[0]["snippet"].get("title", "")[:200]
                channel = row.channel_title
    except YTError:
        pass
    return {"key": key, "address": address, "tenant": tenant, "channel": channel}
