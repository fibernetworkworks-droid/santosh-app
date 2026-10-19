"""Which mailboxes a person has, and connecting new ones.

Order Santosh uses: mailboxes connected in the app (default first) -> the Gmail of their Google sign-in -> for the
server owner only, the mailbox in the server's .env (EMAIL_ADDRESS + app password).
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select

from .. import accounts as acc
from ..config import get_settings
from ..db import MailAccount, MailLinkState, OAuthConnection, as_utc, now, session
from .base import Box, MailError, NotConnected
from .gmail import GmailBox
from .imap import ImapBox
from .outlook import OutlookBox

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GMAIL_SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/gmail.modify"]
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
MS_SCOPES = ["offline_access", "openid", "email", "profile", "https://graph.microsoft.com/Mail.ReadWrite",
             "https://graph.microsoft.com/Mail.Send", "https://graph.microsoft.com/User.Read"]

_http: httpx.Client | None = None   # tests inject a mock transport here


def set_http(client: httpx.Client | None) -> None:
    global _http
    _http = client


def _post(url: str, data: dict) -> dict:
    c = _http or httpx.Client(timeout=25)
    try:
        r = c.post(url, data=data)
    except httpx.HTTPError as e:
        raise MailError(f"Login server se baat nahi hui ({type(e).__name__})")
    finally:
        if _http is None:
            c.close()
    if r.status_code != 200:
        raise MailError(f"Token nahi mila: {r.text[:200]}")
    return r.json()


def _get(url: str, token: str) -> dict:
    c = _http or httpx.Client(timeout=25)
    try:
        r = c.get(url, headers={"Authorization": f"Bearer {token}"})
    finally:
        if _http is None:
            c.close()
    if r.status_code != 200:
        raise MailError(f"Profile nahi mila: {r.text[:200]}")
    return r.json()


def _ms_token_url() -> str:
    return f"https://login.microsoftonline.com/{get_settings().ms_oauth_tenant or 'common'}/oauth2/v2.0/token"


# ---------------- tokens ----------------
def _oauth_token(account_id: str, force: bool) -> str:
    st = get_settings()
    with session() as s:
        a = s.get(MailAccount, account_id)
        if a is None:
            raise NotConnected("Yeh mailbox ab Santosh se judi nahi hai.")
        exp = as_utc(a.expiry)
        if not force and a.access_token_enc and exp and exp > now() + timedelta(seconds=90):
            return acc.decrypt(a.access_token_enc) or ""
        refresh = acc.decrypt(a.refresh_token_enc)
        kind = a.kind
    if not refresh:
        raise MailError("Mailbox ka login expire ho gaya. App mein Profile > Email se dobara jodiye.")
    if kind == "gmail":
        tok = _post(GOOGLE_TOKEN, {"client_id": st.google_oauth_client_id, "client_secret": st.google_oauth_client_secret,
                                   "refresh_token": refresh, "grant_type": "refresh_token"})
    else:
        tok = _post(_ms_token_url(), {"client_id": st.ms_oauth_client_id, "client_secret": st.ms_oauth_client_secret,
                                      "refresh_token": refresh, "grant_type": "refresh_token", "scope": " ".join(MS_SCOPES)})
    with session() as s:
        a = s.get(MailAccount, account_id)
        a.access_token_enc = acc.encrypt(tok["access_token"])
        if tok.get("refresh_token"):
            a.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        a.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        a.status, a.last_error = "ok", ""
    return tok["access_token"]


def _signin_token(tenant: str):
    from .. import google_auth

    def token(force: bool) -> str:
        creds = google_auth.credentials_for(tenant)
        if creds is None:
            raise NotConnected("Google sign-in nahi mila.")
        if force:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        return creds.token
    return token


# ---------------- which mailboxes ----------------
def _box_from_row(a: MailAccount) -> Box:
    if a.kind == "gmail":
        return GmailBox(a.id, a.address, lambda force, i=a.id: _oauth_token(i, force), a.display_name, a.signature, _http)
    if a.kind == "outlook":
        return OutlookBox(a.id, a.address, lambda force, i=a.id: _oauth_token(i, force), a.display_name, a.signature, _http)
    return ImapBox(a.id, a.address, acc.decrypt(a.password_enc) or "", a.display_name, a.signature,
                   a.imap_host, a.imap_port, a.smtp_host, a.smtp_port)


def _signin_conn(s, tenant: str):
    from ..google_auth import _google_conn
    c = _google_conn(s, tenant)
    if c and GMAIL_SCOPE in (c.scopes or "").split() and c.refresh_token_enc:
        return c
    return None


def env_configured() -> bool:
    st = get_settings()
    return bool(st.email_address and st.email_password)


def boxes(tenant: str) -> list[Box]:
    st = get_settings()
    out: list[Box] = []
    with session() as s:
        rows = s.scalars(select(MailAccount).where(MailAccount.tenant_id == tenant, MailAccount.kind != "_sig")
                         .order_by(MailAccount.is_default.desc(), MailAccount.created_at)).all()
        out += [_box_from_row(a) for a in rows]
        c = _signin_conn(s, tenant)
        if c and c.account_email.lower() not in {b.address for b in out}:
            out.append(GmailBox("google", c.account_email, _signin_token(tenant), "", _kv_signature(tenant, "google"), _http))
    if tenant == st.tenant_id and env_configured() and st.email_address.lower() not in {b.address for b in out}:
        out.append(ImapBox("env", st.email_address, st.email_password, st.email_sender_name, _kv_signature(tenant, "env"),
                           st.email_imap_host, st.email_imap_port, st.email_smtp_host, st.email_smtp_port))
    return out


def has_mail(tenant: str) -> bool:
    try:
        return bool(boxes(tenant))
    except Exception:
        return False


def get_box(tenant: str, which: str | None = None) -> Box:
    bs = boxes(tenant)
    if not bs:
        raise NotConnected("Aapka email abhi Santosh se juda nahi hai. App mein Profile > Email mein Gmail, Outlook ya "
                           "koi bhi email (app password se) jodiye.")
    if not which:
        return bs[0]
    w = which.strip().lower()
    for b in bs:
        if b.key.lower() == w or b.address == w:
            return b
    raise MailError(f"'{which}' mailbox nahi mili. Judi hui: {', '.join(b.address for b in bs)}")


def views(tenant: str) -> list[dict[str, Any]]:
    out = []
    with session() as s:
        status = {a.id: (a.status, a.last_error) for a in s.scalars(select(MailAccount).where(MailAccount.tenant_id == tenant))}
    for i, b in enumerate(boxes(tenant)):
        v = b.view()
        v["default"] = i == 0
        v["status"], v["error"] = status.get(b.key, ("ok", ""))
        v["removable"] = b.key not in ("google", "env")
        out.append(v)
    return out


# signatures for the mailboxes that have no MailAccount row of their own (Google sign-in / .env) are kept in a
# MailAccount row of kind "_sig" (never a real mailbox; boxes() skips them)
def _kv_signature(tenant: str, key: str) -> str:
    with session() as s:
        a = s.scalar(select(MailAccount).where(MailAccount.tenant_id == tenant, MailAccount.kind == "_sig",
                                               MailAccount.address == f"_sig:{key}"))
        return a.signature if a else ""


def set_signature(tenant: str, key: str, signature: str) -> None:
    signature = (signature or "").strip()[:2000]
    with session() as s:
        if key in ("google", "env"):
            a = s.scalar(select(MailAccount).where(MailAccount.tenant_id == tenant, MailAccount.address == f"_sig:{key}"))
            if a is None:
                a = MailAccount(tenant_id=tenant, kind="_sig", address=f"_sig:{key}")
                s.add(a)
            a.signature = signature
            return
        a = s.get(MailAccount, key)
        if a is None or a.tenant_id != tenant:
            raise MailError("Mailbox nahi mili")
        a.signature = signature


def set_default(tenant: str, key: str) -> None:
    with session() as s:
        rows = s.scalars(select(MailAccount).where(MailAccount.tenant_id == tenant, MailAccount.kind != "_sig")).all()
        if key not in {a.id for a in rows}:
            raise MailError("Sirf app mein judi mailbox ko default bana sakte hain.")
        for a in rows:
            a.is_default = a.id == key


def remove(tenant: str, key: str) -> bool:
    with session() as s:
        a = s.get(MailAccount, key)
        if a is None or a.tenant_id != tenant or a.kind == "_sig":
            return False
        s.delete(a)
    return True


def mark_error(key: str, err: str) -> None:
    with session() as s:
        a = s.get(MailAccount, key)
        if a is not None:
            a.status, a.last_error = "error", err[:500]


def _save(tenant: str, kind: str, address: str, name: str, **fields) -> dict[str, Any]:
    address = address.strip().lower()
    with session() as s:
        n = len(s.scalars(select(MailAccount.id).where(MailAccount.tenant_id == tenant, MailAccount.kind != "_sig")).all())
        a = s.scalar(select(MailAccount).where(MailAccount.tenant_id == tenant, MailAccount.address == address))
        if a is None:
            a = MailAccount(tenant_id=tenant, kind=kind, address=address, is_default=(n == 0))
            s.add(a)
        a.kind, a.display_name, a.status, a.last_error = kind, name or a.display_name or "", "ok", ""
        for k, v in fields.items():
            setattr(a, k, v)
        s.flush()
        return {"key": a.id, "kind": kind, "address": address, "name": a.display_name}


# ---------------- connecting: IMAP + app password ----------------
def connect_imap(tenant: str, address: str, password: str, name: str = "", imap_host: str = "", imap_port: int = 993,
                 smtp_host: str = "", smtp_port: int = 0) -> dict[str, Any]:
    address = (address or "").strip().lower()
    if "@" not in address or not password:
        raise MailError("Email address aur app password dono chahiye.")
    from .imap import PROVIDERS
    if address.split("@")[-1] in PROVIDERS:   # Google/Yahoo/Zoho/iCloud show app passwords in groups of 4 with spaces
        password = password.replace(" ", "")
    box = ImapBox("test", address, password, name, "", imap_host, imap_port, smtp_host, smtp_port)
    box.check()
    return _save(tenant, "imap", address, name, password_enc=acc.encrypt(password), imap_host=box.imap_host,
                 imap_port=box.imap_port, smtp_host=box.smtp_host, smtp_port=box.smtp_port)


# ---------------- connecting: OAuth (Gmail / Outlook) ----------------
def oauth_ready(provider: str) -> bool:
    st = get_settings()
    if not (st.public_base_url and st.secret_key):
        return False
    if provider == "google":
        return bool(st.google_oauth_client_id and st.google_oauth_client_secret)
    if provider == "microsoft":
        return bool(st.ms_oauth_client_id and st.ms_oauth_client_secret)
    return False


def ms_redirect_uri() -> str:
    return get_settings().public_base_url.rstrip("/") + "/auth/microsoft/callback"


def start_link(tenant: str, provider: str, login_hint: str = "") -> str:
    if provider not in ("google", "microsoft"):
        raise MailError("provider must be google or microsoft")
    if not oauth_ready(provider):
        raise MailError({"google": "Gmail jodne ke liye server par Google sign-in (GOOGLE_OAUTH_CLIENT_ID/SECRET, "
                                   "PUBLIC_BASE_URL, SECRET_KEY) set hona chahiye.",
                         "microsoft": "Outlook jodne ke liye server par MS_OAUTH_CLIENT_ID/SECRET, PUBLIC_BASE_URL aur "
                                      "SECRET_KEY set hona chahiye."}[provider])
    st = get_settings()
    state = "mail_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider=provider))
        for old in s.scalars(select(MailLinkState).where(MailLinkState.created_at < now() - timedelta(minutes=30))).all():
            s.delete(old)
    if provider == "google":
        q = {"client_id": st.google_oauth_client_id, "redirect_uri": acc._redirect_uri(), "response_type": "code",
             "scope": " ".join(GMAIL_SCOPES), "access_type": "offline", "prompt": "consent", "state": state,
             "include_granted_scopes": "true"}
        if login_hint:
            q["login_hint"] = login_hint
        return GOOGLE_AUTH + "?" + urlencode(q)
    q = {"client_id": st.ms_oauth_client_id, "redirect_uri": ms_redirect_uri(), "response_type": "code",
         "scope": " ".join(MS_SCOPES), "response_mode": "query", "state": state, "prompt": "select_account"}
    if login_hint:
        q["login_hint"] = login_hint
    return f"https://login.microsoftonline.com/{st.ms_oauth_tenant or 'common'}/oauth2/v2.0/authorize?" + urlencode(q)


def is_link_state(state: str) -> bool:
    return (state or "").startswith("mail_")


def finish_link(code: str, state: str) -> dict[str, Any]:
    st = get_settings()
    with session() as s:
        row = s.get(MailLinkState, state)
        if row is None or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise MailError("Yeh link purana ho gaya. App se dobara 'Jodiye' dabaiye.")
        tenant, provider = row.tenant_id, row.provider
        s.delete(row)
    if provider == "google":
        tok = _post(GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                   "client_secret": st.google_oauth_client_secret, "redirect_uri": acc._redirect_uri(),
                                   "grant_type": "authorization_code"})
        if GMAIL_SCOPE not in (tok.get("scope") or "").split():
            raise MailError("Gmail ki permission nahi di gayi. Dobara jodte waqt 'Gmail padhna aur bhejna' allow kijiye.")
        info = _get("https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
        address, name, kind = info.get("email", ""), info.get("name", ""), "gmail"
    else:
        tok = _post(_ms_token_url(), {"code": code, "client_id": st.ms_oauth_client_id,
                                      "client_secret": st.ms_oauth_client_secret, "redirect_uri": ms_redirect_uri(),
                                      "grant_type": "authorization_code", "scope": " ".join(MS_SCOPES)})
        info = _get("https://graph.microsoft.com/v1.0/me", tok["access_token"])
        address = info.get("mail") or info.get("userPrincipalName") or ""
        name, kind = info.get("displayName", ""), "outlook"
    if not address or "@" not in address:
        raise MailError("Account se email address nahi mila.")
    if not tok.get("refresh_token"):
        raise MailError("Login server ne refresh token nahi diya; dobara jodiye.")
    view = _save(tenant, kind, address, name, access_token_enc=acc.encrypt(tok["access_token"]),
                 refresh_token_enc=acc.encrypt(tok["refresh_token"]),
                 expiry=now() + timedelta(seconds=int(tok.get("expires_in", 3600))))
    view["tenant"] = tenant
    return view
