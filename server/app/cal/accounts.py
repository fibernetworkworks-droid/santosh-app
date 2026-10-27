"""Which Google Calendars a person has connected, and connecting one.

Order: calendars connected in the app (Profile > Calendar, default first) -> the calendar of their Google sign-in
(if it granted calendar access) -> for the server owner only, the .env Gmail over CalDAV (older route).
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select

from .. import accounts as acc
from ..config import get_settings
from ..db import CalendarAccount, MailLinkState, as_utc, now, session
from ..mailbox import accounts as mail_acc
from .caldav_cal import CaldavCal
from .google import CalError, GoogleCal, NotConnected

CAL_SCOPE = "https://www.googleapis.com/auth/calendar"
SCOPES = ["openid", "email", "profile", CAL_SCOPE]


def _token(account_id: str, force: bool) -> str:
    st = get_settings()
    with session() as s:
        a = s.get(CalendarAccount, account_id)
        if a is None:
            raise NotConnected("Yeh calendar ab Santosh se juda nahi hai.")
        exp = as_utc(a.expiry)
        if not force and a.access_token_enc and exp and exp > now() + timedelta(seconds=90):
            return acc.decrypt(a.access_token_enc) or ""
        refresh = acc.decrypt(a.refresh_token_enc)
    if not refresh:
        raise CalError("Calendar ka login expire ho gaya. App mein Profile > Calendar se dobara jodiye.")
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "refresh_token": refresh, "grant_type": "refresh_token"})
    except Exception as e:
        with session() as s:
            a = s.get(CalendarAccount, account_id)
            if a:
                a.status, a.last_error = "error", str(e)[:500]
        raise CalError(f"Calendar login refresh nahi hua: {e}")
    with session() as s:
        a = s.get(CalendarAccount, account_id)
        a.access_token_enc = acc.encrypt(tok["access_token"])
        if tok.get("refresh_token"):
            a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
    return tok["access_token"]


def _signin_conn(s, tenant: str):
    from ..google_auth import _google_conn
    c = _google_conn(s, tenant)
    if c and CAL_SCOPE in (c.scopes or "").split() and c.refresh_token_enc:
        return c
    return None


def boxes(tenant: str) -> list:
    from .. import gcal
    st = get_settings()
    out: list = []
    with session() as s:
        rows = s.scalars(select(CalendarAccount).where(CalendarAccount.tenant_id == tenant)
                         .order_by(CalendarAccount.is_default.desc(), CalendarAccount.created_at)).all()
        out += [GoogleCal(a.id, a.address, lambda force, i=a.id: _token(i, force), a.display_name, mail_acc._http)
                for a in rows]
        c = _signin_conn(s, tenant)
        if c and c.account_email.lower() not in {b.address for b in out}:
            out.append(GoogleCal("google", c.account_email, mail_acc._signin_token(tenant), "", mail_acc._http))
    if tenant == st.tenant_id and gcal.configured() and st.email_address.lower() not in {b.address for b in out}:
        out.append(CaldavCal(st.email_address))
    return out


def has_calendar(tenant: str) -> bool:
    try:
        return bool(boxes(tenant))
    except Exception:
        return False


def get_box(tenant: str, which: str | None = None):
    bs = boxes(tenant)
    if not bs:
        raise NotConnected("Aapka Google Calendar abhi Santosh se juda nahi hai. App mein Profile > Calendar > "
                           "'Google Calendar jodiye' dabaiye. Tab tak add_calendar_event se phone calendar mein daal sakte hain.")
    if not which:
        return bs[0]
    w = which.strip().lower()
    for b in bs:
        if b.key.lower() == w or b.address == w:
            return b
    raise CalError(f"'{which}' calendar account nahi mila. Jude hue: {', '.join(b.address for b in bs)}")


def views(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        status = {a.id: (a.status, a.last_error) for a in s.scalars(select(CalendarAccount)
                                                                     .where(CalendarAccount.tenant_id == tenant))}
    out = []
    for i, b in enumerate(boxes(tenant)):
        st, err = status.get(b.key, ("ok", ""))
        out.append({"key": b.key, "kind": b.kind, "address": b.address, "default": i == 0, "status": st, "error": err,
                    "removable": b.key not in ("google", "env"), "full": b.kind == "google"})
    return out


def remove(tenant: str, key: str) -> bool:
    with session() as s:
        a = s.get(CalendarAccount, key)
        if a is None or a.tenant_id != tenant:
            return False
        s.delete(a)
    return True


def set_default(tenant: str, key: str) -> None:
    with session() as s:
        rows = s.scalars(select(CalendarAccount).where(CalendarAccount.tenant_id == tenant)).all()
        if key not in {a.id for a in rows}:
            raise CalError("Sirf app mein jude calendar ko default bana sakte hain.")
        for a in rows:
            a.is_default = a.id == key


# ---------------- connecting ----------------
def oauth_ready() -> bool:
    return mail_acc.oauth_ready("google")


def is_link_state(state: str) -> bool:
    return (state or "").startswith("cal_")


def start_link(tenant: str, login_hint: str = "") -> str:
    if not oauth_ready():
        raise CalError("Google Calendar jodne ke liye server par Google sign-in (GOOGLE_OAUTH_CLIENT_ID/SECRET, "
                       "PUBLIC_BASE_URL, SECRET_KEY) set hona chahiye.")
    st = get_settings()
    state = "cal_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="gcal"))
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
        if row is None or row.provider != "gcal" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise CalError("Yeh link purana ho gaya. App se dobara 'Google Calendar jodiye' dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "redirect_uri": acc._redirect_uri(), "grant_type": "authorization_code"})
        if CAL_SCOPE not in (tok.get("scope") or "").split():
            raise CalError("Calendar ki permission nahi di gayi. Dobara jodte waqt 'Calendar dekhna aur badalna' allow kijiye.")
        info = mail_acc._get("https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
    except mail_acc.MailError as e:
        raise CalError(str(e))
    address = (info.get("email") or "").lower()
    if "@" not in address:
        raise CalError("Google account se email nahi mila.")
    if not tok.get("refresh_token"):
        raise CalError("Google ne refresh token nahi diya; dobara jodiye.")
    with session() as s:
        n = len(s.scalars(select(CalendarAccount.id).where(CalendarAccount.tenant_id == tenant)).all())
        a = s.scalar(select(CalendarAccount).where(CalendarAccount.tenant_id == tenant, CalendarAccount.address == address))
        if a is None:
            a = CalendarAccount(tenant_id=tenant, address=address, is_default=(n == 0))
            s.add(a)
        a.display_name = info.get("name", "") or a.display_name
        a.access_token_enc = acc.encrypt(tok["access_token"])
        a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
        s.flush()
        return {"key": a.id, "address": address, "tenant": tenant}
