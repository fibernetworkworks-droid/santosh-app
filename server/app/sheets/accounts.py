"""Which Google accounts Santosh can use for a person's Google Sheets, and connecting one.

Order: accounts connected in the app (Profile > Google Sheets) -> their Google sign-in (if it granted Sheets) ->
for the server owner only, the server's service account (sees just the sheets shared with its email).
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select

from .. import accounts as acc
from ..config import get_settings
from ..db import MailLinkState, SheetsAccount, as_utc, now, session
from ..mailbox import accounts as mail_acc
from .client import NotConnected, SheetError, SheetsClient

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SCOPES = ["openid", "email", "profile", SHEETS_SCOPE,
          "https://www.googleapis.com/auth/drive.metadata.readonly",   # find sheets by name
          "https://www.googleapis.com/auth/drive.file"]                # share the sheets Santosh creates
SEARCH_SCOPES = ("https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.readonly",
                 "https://www.googleapis.com/auth/drive.metadata.readonly", "https://www.googleapis.com/auth/drive.metadata")


def _token(account_id: str, force: bool) -> str:
    st = get_settings()
    with session() as s:
        a = s.get(SheetsAccount, account_id)
        if a is None:
            raise NotConnected("Yeh Google account ab Santosh se juda nahi hai.")
        exp = as_utc(a.expiry)
        if not force and a.access_token_enc and exp and exp > now() + timedelta(seconds=90):
            return acc.decrypt(a.access_token_enc) or ""
        refresh = acc.decrypt(a.refresh_token_enc)
    if not refresh:
        raise SheetError("Google Sheets ka login expire ho gaya. Profile > Google Sheets se dobara jodiye.")
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "refresh_token": refresh, "grant_type": "refresh_token"})
    except Exception as e:
        with session() as s:
            a = s.get(SheetsAccount, account_id)
            if a:
                a.status, a.last_error = "error", str(e)[:500]
        raise SheetError(f"Google login refresh nahi hua: {e}")
    with session() as s:
        a = s.get(SheetsAccount, account_id)
        a.access_token_enc = acc.encrypt(tok["access_token"])
        if tok.get("refresh_token"):
            a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
    return tok["access_token"]


_sa_cache: dict[str, Any] = {}


def _service_account_token(force: bool) -> str:
    from google.auth.transport.requests import Request
    from .. import gdrive
    creds = _sa_cache.get("creds")
    if creds is None:
        try:
            creds = gdrive._creds()
        except gdrive.DriveError as e:
            raise SheetError(str(e))
        _sa_cache["creds"] = creds
    if force or not creds.valid:
        creds.refresh(Request())
    return creds.token


def _service_account_email() -> str:
    import json
    import os
    st = get_settings()
    try:
        if st.google_sa_json.strip():
            return json.loads(st.google_sa_json).get("client_email", "service-account")
        if st.google_sa_file and os.path.exists(st.google_sa_file):
            return json.load(open(st.google_sa_file)).get("client_email", "service-account")
    except Exception:
        pass
    return "service-account"


def _signin_conn(s, tenant: str):
    from ..google_auth import _google_conn
    c = _google_conn(s, tenant)
    if c and SHEETS_SCOPE in (c.scopes or "").split() and c.refresh_token_enc:
        return c
    return None


def clients(tenant: str) -> list[SheetsClient]:
    from .. import gdrive
    st = get_settings()
    out: list[SheetsClient] = []
    with session() as s:
        rows = s.scalars(select(SheetsAccount).where(SheetsAccount.tenant_id == tenant)
                         .order_by(SheetsAccount.is_default.desc(), SheetsAccount.created_at)).all()
        out += [SheetsClient(a.id, a.address, lambda force, i=a.id: _token(i, force), "google", mail_acc._http) for a in rows]
        c = _signin_conn(s, tenant)
        if c and c.account_email.lower() not in {b.address for b in out}:
            scopes = set((c.scopes or "").split())
            out.append(SheetsClient("google", c.account_email, mail_acc._signin_token(tenant), "google", mail_acc._http,
                                    can_search=bool(scopes & set(SEARCH_SCOPES))))
    if tenant == st.tenant_id and gdrive.configured(None):
        out.append(SheetsClient("service", _service_account_email(), _service_account_token, "service", mail_acc._http))
    return out


def has_sheets(tenant: str) -> bool:
    try:
        return bool(clients(tenant))
    except Exception:
        return False


def get_client(tenant: str, which: str | None = None) -> SheetsClient:
    cs = clients(tenant)
    if not cs:
        raise NotConnected("Aapki Google Sheets abhi Santosh se judi nahi hain. App mein Profile > Google Sheets > "
                           "'Google Sheets jodiye' dabaiye.")
    if not which:
        return cs[0]
    w = which.strip().lower()
    for c in cs:
        if c.key.lower() == w or c.address == w:
            return c
    raise SheetError(f"'{which}' account nahi mila. Jude hue: {', '.join(c.address for c in cs)}")


def views(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        status = {a.id: (a.status, a.last_error) for a in s.scalars(select(SheetsAccount).where(SheetsAccount.tenant_id == tenant))}
    out = []
    for i, c in enumerate(clients(tenant)):
        st, err = status.get(c.key, ("ok", ""))
        out.append({"key": c.key, "kind": c.kind, "address": c.address, "default": i == 0, "status": st, "error": err,
                    "removable": c.key not in ("google", "service"), "can_search": c.can_search})
    return out


def remove(tenant: str, key: str) -> bool:
    with session() as s:
        a = s.get(SheetsAccount, key)
        if a is None or a.tenant_id != tenant:
            return False
        s.delete(a)
    return True


# ---------------- connecting ----------------
def oauth_ready() -> bool:
    return mail_acc.oauth_ready("google")


def is_link_state(state: str) -> bool:
    return (state or "").startswith("gsh_")


def start_link(tenant: str, login_hint: str = "") -> str:
    if not oauth_ready():
        raise SheetError("Google Sheets jodne ke liye server par Google sign-in (GOOGLE_OAUTH_CLIENT_ID/SECRET, "
                         "PUBLIC_BASE_URL, SECRET_KEY) set hona chahiye.")
    st = get_settings()
    state = "gsh_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="sheets"))
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
        if row is None or row.provider != "sheets" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise SheetError("Yeh link purana ho gaya. App se dobara 'Google Sheets jodiye' dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "redirect_uri": acc._redirect_uri(), "grant_type": "authorization_code"})
        if SHEETS_SCOPE not in (tok.get("scope") or "").split():
            raise SheetError("Sheets ki permission nahi di gayi. Dobara jodte waqt 'Google Sheets dekhna aur badalna' allow kijiye.")
        info = mail_acc._get("https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
    except mail_acc.MailError as e:
        raise SheetError(str(e))
    address = (info.get("email") or "").lower()
    if "@" not in address or not tok.get("refresh_token"):
        raise SheetError("Google se account ya refresh token nahi mila; dobara jodiye.")
    with session() as s:
        n = len(s.scalars(select(SheetsAccount.id).where(SheetsAccount.tenant_id == tenant)).all())
        a = s.scalar(select(SheetsAccount).where(SheetsAccount.tenant_id == tenant, SheetsAccount.address == address))
        if a is None:
            a = SheetsAccount(tenant_id=tenant, address=address, is_default=(n == 0))
            s.add(a)
        a.display_name = info.get("name", "") or a.display_name
        a.access_token_enc = acc.encrypt(tok["access_token"])
        a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
        s.flush()
        return {"key": a.id, "address": address, "tenant": tenant}
