"""Which Google accounts Santosh can use for a person's Google Forms, and connecting one.

Order: accounts connected in the app (Profile > Google Forms) -> their Google sign-in (if it granted Forms access).
There is no service-account route: a form belongs to a person.
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
from .client import FormError, FormsClient, NotConnected
from .models import FormsAccount

FORMS_SCOPE = "https://www.googleapis.com/auth/forms.body"
SCOPES = ["openid", "email", "profile", FORMS_SCOPE,
          "https://www.googleapis.com/auth/forms.responses.readonly",
          "https://www.googleapis.com/auth/drive.metadata.readonly",   # find forms by name
          "https://www.googleapis.com/auth/drive.file"]                # share the forms Santosh creates
SEARCH_SCOPES = ("https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.readonly",
                 "https://www.googleapis.com/auth/drive.metadata.readonly", "https://www.googleapis.com/auth/drive.metadata")


def _token(account_id: str, force: bool) -> str:
    st = get_settings()
    with session() as s:
        a = s.get(FormsAccount, account_id)
        if a is None:
            raise NotConnected("Yeh Google account ab Santosh se juda nahi hai.")
        exp = as_utc(a.expiry)
        if not force and a.access_token_enc and exp and exp > now() + timedelta(seconds=90):
            return acc.decrypt(a.access_token_enc) or ""
        refresh = acc.decrypt(a.refresh_token_enc)
    if not refresh:
        raise FormError("Google Forms ka login expire ho gaya. Profile > Google Forms se dobara jodiye.")
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "refresh_token": refresh, "grant_type": "refresh_token"})
    except Exception as e:
        with session() as s:
            a = s.get(FormsAccount, account_id)
            if a:
                a.status, a.last_error = "error", str(e)[:500]
        raise FormError(f"Google login refresh nahi hua: {e}")
    with session() as s:
        a = s.get(FormsAccount, account_id)
        a.access_token_enc = acc.encrypt(tok["access_token"])
        if tok.get("refresh_token"):
            a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
    return tok["access_token"]


def _signin_conn(s, tenant: str):
    from ..google_auth import _google_conn
    c = _google_conn(s, tenant)
    if c and FORMS_SCOPE in (c.scopes or "").split() and c.refresh_token_enc:
        return c
    return None


def clients(tenant: str) -> list[FormsClient]:
    out: list[FormsClient] = []
    with session() as s:
        rows = s.scalars(select(FormsAccount).where(FormsAccount.tenant_id == tenant)
                         .order_by(FormsAccount.is_default.desc(), FormsAccount.created_at)).all()
        out += [FormsClient(a.id, a.address, lambda force, i=a.id: _token(i, force), mail_acc._http) for a in rows]
        c = _signin_conn(s, tenant)
        if c and c.account_email.lower() not in {b.address for b in out}:
            scopes = set((c.scopes or "").split())
            out.append(FormsClient("google", c.account_email, mail_acc._signin_token(tenant), mail_acc._http,
                                   can_search=bool(scopes & set(SEARCH_SCOPES))))
    return out


def has_forms(tenant: str) -> bool:
    try:
        return bool(clients(tenant))
    except Exception:
        return False


def get_client(tenant: str, which: str | None = None) -> FormsClient:
    cs = clients(tenant)
    if not cs:
        raise NotConnected("Aapke Google Forms abhi Santosh se jude nahi hain. App mein Profile > Google Forms > "
                           "'Google Forms jodiye' dabaiye.")
    if not which:
        return cs[0]
    w = which.strip().lower()
    for c in cs:
        if c.key.lower() == w or c.address == w:
            return c
    raise FormError(f"'{which}' account nahi mila. Jude hue: {', '.join(c.address for c in cs)}")


def views(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        status = {a.id: (a.status, a.last_error) for a in s.scalars(select(FormsAccount).where(FormsAccount.tenant_id == tenant))}
    out = []
    for i, c in enumerate(clients(tenant)):
        st, err = status.get(c.key, ("ok", ""))
        out.append({"key": c.key, "address": c.address, "default": i == 0, "status": st, "error": err,
                    "removable": c.key != "google", "can_search": c.can_search})
    return out


def remove(tenant: str, key: str) -> bool:
    with session() as s:
        a = s.get(FormsAccount, key)
        if a is None or a.tenant_id != tenant:
            return False
        s.delete(a)
    return True


# ---------------- connecting ----------------
def oauth_ready() -> bool:
    return mail_acc.oauth_ready("google")


def is_link_state(state: str) -> bool:
    return (state or "").startswith("gfm_")


def start_link(tenant: str, login_hint: str = "") -> str:
    if not oauth_ready():
        raise FormError("Google Forms jodne ke liye server par Google sign-in (GOOGLE_OAUTH_CLIENT_ID/SECRET, "
                        "PUBLIC_BASE_URL, SECRET_KEY) set hona chahiye.")
    st = get_settings()
    state = "gfm_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="forms"))
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
        if row is None or row.provider != "forms" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise FormError("Yeh link purana ho gaya. App se dobara 'Google Forms jodiye' dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "redirect_uri": acc._redirect_uri(), "grant_type": "authorization_code"})
        if FORMS_SCOPE not in (tok.get("scope") or "").split():
            raise FormError("Forms ki permission nahi di gayi. Dobara jodte waqt 'Google Forms dekhna aur banana' allow kijiye.")
        info = mail_acc._get("https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
    except mail_acc.MailError as e:
        raise FormError(str(e))
    address = (info.get("email") or "").lower()
    if "@" not in address or not tok.get("refresh_token"):
        raise FormError("Google se account ya refresh token nahi mila; dobara jodiye.")
    with session() as s:
        n = len(s.scalars(select(FormsAccount.id).where(FormsAccount.tenant_id == tenant)).all())
        a = s.scalar(select(FormsAccount).where(FormsAccount.tenant_id == tenant, FormsAccount.address == address))
        if a is None:
            a = FormsAccount(tenant_id=tenant, address=address, is_default=(n == 0))
            s.add(a)
        a.display_name = info.get("name", "") or a.display_name
        a.access_token_enc = acc.encrypt(tok["access_token"])
        a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
        s.flush()
        return {"key": a.id, "address": address, "tenant": tenant}
