"""Which Google accounts Santosh can use for a person's Google Drive, and connecting one.

Order: accounts connected in the app (Profile > Google Drive) -> their Google sign-in (if it granted Drive) ->
for the server owner only, the server's service account (sees just what is shared with it / the shared folder).
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
from .client import DriveClient, DriveError, NotConnected
from .models import DriveAccount

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
SCOPES = ["openid", "email", "profile", DRIVE_SCOPE]


def _token(account_id: str, force: bool) -> str:
    st = get_settings()
    with session() as s:
        a = s.get(DriveAccount, account_id)
        if a is None:
            raise NotConnected("Yeh Google account ab Santosh se juda nahi hai.")
        exp = as_utc(a.expiry)
        if not force and a.access_token_enc and exp and exp > now() + timedelta(seconds=90):
            return acc.decrypt(a.access_token_enc) or ""
        refresh = acc.decrypt(a.refresh_token_enc)
    if not refresh:
        raise DriveError("Google Drive ka login expire ho gaya. Profile > Google Drive se dobara jodiye.")
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "refresh_token": refresh, "grant_type": "refresh_token"})
    except Exception as e:
        addr = ""
        with session() as s:
            a = s.get(DriveAccount, account_id)
            if a:
                a.status, a.last_error = "error", str(e)[:500]
                addr = a.address
        from ..google_auth import reconnect_message
        raise DriveError(reconnect_message(addr, str(e)) if "invalid_grant" in str(e)
                         else f"Google login refresh nahi hua: {e}")
    with session() as s:
        a = s.get(DriveAccount, account_id)
        a.access_token_enc = acc.encrypt(tok["access_token"])
        if tok.get("refresh_token"):
            a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
    return tok["access_token"]


_sa: dict[str, Any] = {}


def _service_token(force: bool) -> str:
    from google.auth.transport.requests import Request
    from .. import gdrive
    creds = _sa.get("creds")
    if creds is None:
        try:
            creds = gdrive._creds()
        except gdrive.DriveError as e:
            raise DriveError(str(e))
        _sa["creds"] = creds
    if force or not creds.valid:
        creds.refresh(Request())
    return creds.token


def _service_email() -> str:
    from ..sheets.accounts import _service_account_email
    return _service_account_email()


def _signin_conn(s, tenant: str):
    from ..google_auth import _google_conn
    c = _google_conn(s, tenant)
    if c and DRIVE_SCOPE in (c.scopes or "").split() and c.refresh_token_enc:
        return c
    return None


def clients(tenant: str) -> list[DriveClient]:
    from .. import gdrive
    st = get_settings()
    out: list[DriveClient] = []
    with session() as s:
        rows = s.scalars(select(DriveAccount).where(DriveAccount.tenant_id == tenant)
                         .order_by(DriveAccount.is_default.desc(), DriveAccount.created_at)).all()
        out += [DriveClient(a.id, a.address, lambda force, i=a.id: _token(i, force), "google", mail_acc._http) for a in rows]
        c = _signin_conn(s, tenant)
        if c and c.account_email.lower() not in {b.address for b in out}:
            out.append(DriveClient("google", c.account_email, mail_acc._signin_token(tenant), "google", mail_acc._http))
    if tenant == st.tenant_id and gdrive.configured(None):
        out.append(DriveClient("service", _service_email(), _service_token, "service", mail_acc._http,
                               root=st.google_drive_folder_id.strip() or "root"))
    return out


def why_not(tenant: str) -> str:
    """Why there is no Drive for her, in her words (v0.70)."""
    from ..google_auth import _google_conn, reconnect_message
    with session() as s:
        c = _google_conn(s, tenant)
        if c is not None and c.last_error:
            return reconnect_message(c.account_email, c.last_error)
        if c is not None and DRIVE_SCOPE not in (c.scopes or "").split():
            return (f"Aapne Google ({c.account_email}) se sign in kiya hai, par us waqt Google Drive ki permission (checkbox) "
                    "tick nahi hui thi, isliye Hoola Drive nahi dekh sakta. App mein Profile > Google Drive > 'Google Drive "
                    "jodiye' dabaiye aur Google ke page par 'See, edit, create and delete all of your Google Drive files' "
                    "wala box tick kijiye.")
        if c is not None and not c.refresh_token_enc:
            return reconnect_message(c.account_email, "no refresh token")
    if not oauth_ready():
        return ("Is server par Google sign-in set nahi hai (GOOGLE_OAUTH_CLIENT_ID / SECRET, PUBLIC_BASE_URL, SECRET_KEY), "
                "isliye Drive nahi jud sakta. Server set hone ke baad app mein Profile > Google Drive > 'Google Drive jodiye'.")
    return ("Aapka Google Drive abhi Hoola se juda nahi hai. App mein Profile > Google Drive > 'Google Drive jodiye' dabaiye.")


def has_drive(tenant: str) -> bool:
    try:
        return bool(clients(tenant))
    except Exception:
        return False


def get_client(tenant: str, which: str | None = None) -> DriveClient:
    cs = clients(tenant)
    if not cs:
        raise NotConnected(why_not(tenant))
    if not which:
        return cs[0]
    w = which.strip().lower()
    for c in cs:
        if c.key.lower() == w or c.address == w:
            return c
    raise DriveError(f"'{which}' account nahi mila. Jude hue: {', '.join(c.address for c in cs)}")


def views(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        status = {a.id: (a.status, a.last_error) for a in s.scalars(select(DriveAccount).where(DriveAccount.tenant_id == tenant))}
    from ..google_auth import _google_conn
    with session() as s:
        gc = _google_conn(s, tenant)
        if gc is not None and gc.last_error:
            status["google"] = ("error", gc.last_error)
    out = []
    for i, c in enumerate(clients(tenant)):
        st, err = status.get(c.key, ("ok", ""))
        out.append({"key": c.key, "kind": c.kind, "address": c.address, "default": i == 0, "status": st, "error": err,
                    "removable": c.key not in ("google", "service")})
    return out


def remove(tenant: str, key: str) -> bool:
    with session() as s:
        a = s.get(DriveAccount, key)
        if a is None or a.tenant_id != tenant:
            return False
        s.delete(a)
    return True


# ---------------- connecting ----------------
def oauth_ready() -> bool:
    return mail_acc.oauth_ready("google")


def is_link_state(state: str) -> bool:
    return (state or "").startswith("gdr_")


def start_link(tenant: str, login_hint: str = "") -> str:
    if not oauth_ready():
        raise DriveError("Google Drive jodne ke liye server par Google sign-in (GOOGLE_OAUTH_CLIENT_ID/SECRET, "
                         "PUBLIC_BASE_URL, SECRET_KEY) set hona chahiye.")
    st = get_settings()
    state = "gdr_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="drive"))
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
        if row is None or row.provider != "drive" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise DriveError("Yeh link purana ho gaya. App se dobara 'Google Drive jodiye' dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "redirect_uri": acc._redirect_uri(), "grant_type": "authorization_code"})
        if DRIVE_SCOPE not in (tok.get("scope") or "").split():
            raise DriveError("Drive ki permission nahi di gayi. Dobara jodte waqt 'Google Drive ki files dekhna aur "
                             "badalna' allow kijiye.")
        info = mail_acc._get("https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
    except mail_acc.MailError as e:
        raise DriveError(str(e))
    address = (info.get("email") or "").lower()
    if "@" not in address or not tok.get("refresh_token"):
        raise DriveError("Google se account ya refresh token nahi mila; dobara jodiye.")
    with session() as s:
        n = len(s.scalars(select(DriveAccount.id).where(DriveAccount.tenant_id == tenant)).all())
        a = s.scalar(select(DriveAccount).where(DriveAccount.tenant_id == tenant, DriveAccount.address == address))
        if a is None:
            a = DriveAccount(tenant_id=tenant, address=address, is_default=(n == 0))
            s.add(a)
        a.display_name = info.get("name", "") or a.display_name
        a.access_token_enc = acc.encrypt(tok["access_token"])
        a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
        s.flush()
        return {"key": a.id, "address": address, "tenant": tenant}
