"""Her admin consoles over the OFFICIAL APIs, with HER consent. Read-only by default; a change is sent only from
`service.decide_change(by_tap=True)` (her app tap) and only when she connected in `manage` mode.

Google Workspace: OAuth with her admin account (the server's Google OAuth client, PUBLIC_BASE_URL/auth/google/callback; states
start with "ita_"). Microsoft 365: HER Entra app registration (directory id + app id + client secret typed only in the app,
sealed with the bazar vault) -> client-credentials token; she grants admin consent at the adminconsent link.
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from ..db import as_utc, now, session
from .models import ItadminConn

log = logging.getLogger("santosh.itadmin.conn")

G_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
G_TOKEN = "https://oauth2.googleapis.com/token"
G_DIR = "https://admin.googleapis.com/admin/directory/v1/"
G_LIC = "https://licensing.googleapis.com/apps/licensing/v1/product/"
G_READ = ["https://www.googleapis.com/auth/admin.directory.user.readonly",
          "https://www.googleapis.com/auth/admin.directory.device.mobile.readonly",
          "https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly",
          "https://www.googleapis.com/auth/apps.licensing"]
G_MANAGE = ["https://www.googleapis.com/auth/admin.directory.user"]
# Google Workspace product / SKU ids (Licensing API product "Google-Apps"); names come back from the API too
G_PRODUCT = "Google-Apps"
G_SKUS = {"1010020027": "Business Starter", "1010020028": "Business Standard", "1010020025": "Business Plus",
          "1010020026": "Enterprise Standard", "1010020020": "Enterprise Plus"}
MS_GRAPH = "https://graph.microsoft.com/v1.0/"
MS_READ_PERMS = ["User.Read.All", "LicenseAssignment.Read.All", "Device.Read.All", "DeviceManagementManagedDevices.Read.All",
                 "RoleManagement.Read.Directory"]
MS_MANAGE_PERMS = ["User.EnableDisableAccount.All", "User.RevokeSessions.All", "LicenseAssignment.ReadWrite.All"]
MS_SKUS = {"O365_BUSINESS_ESSENTIALS": "Microsoft 365 Business Basic", "O365_BUSINESS_PREMIUM": "Microsoft 365 Business Standard",
           "SPB": "Microsoft 365 Business Premium", "O365_BUSINESS": "Microsoft 365 Apps for business",
           "EXCHANGESTANDARD": "Exchange Online (Plan 1)", "ENTERPRISEPACK": "Office 365 E3"}

_HTTP: httpx.Client | None = None


class ConnError(Exception):
    pass


def set_http(c: httpx.Client | None) -> None:
    global _HTTP
    _HTTP = c


def _client() -> tuple[httpx.Client, bool]:
    if _HTTP is not None:
        return _HTTP, False
    return httpx.Client(timeout=25, follow_redirects=False), True


def _vault():
    from ..bazar.security import vault
    return vault()


def _seal(v: str) -> str:
    return _vault().seal(v) if v else ""


def _open(v: str) -> str:
    try:
        return _vault().open(v) if v else ""
    except ValueError:
        return ""


def _row(s, tenant: str, provider: str) -> ItadminConn | None:
    return s.get(ItadminConn, f"{tenant}:{provider}")


def _req(method: str, url: str, token: str = "", body: Any = None, form: dict | None = None) -> tuple[int, Any]:
    c, own = _client()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        if form is not None:
            r = c.request(method, url, data=form, headers=headers)
        elif body is not None:
            r = c.request(method, url, json=body, headers=headers)
        else:
            r = c.request(method, url, headers=headers)
    except httpx.HTTPError as e:
        raise ConnError(f"Server se baat nahi hui ({type(e).__name__}).")
    finally:
        if own:
            c.close()
    try:
        data = r.json() if r.content else {}
    except ValueError:
        data = {"text": r.text[:300]}
    return r.status_code, data


def _err(data: Any) -> str:
    if isinstance(data, dict):
        e = data.get("error")
        if isinstance(e, dict):
            return str(e.get("message") or e.get("code") or "")[:240]
        if e:
            return str(data.get("error_description") or e)[:240]
    return ""


# ---------------------------------------------------------------- status
def status(tenant: str) -> dict:
    out = {}
    with session() as s:
        for p in ("google", "microsoft"):
            r = _row(s, tenant, p)
            out[p] = None if r is None else {
                "mode": r.mode, "account": r.account, "client_id": r.client_id, "status": r.status, "last_error": r.last_error,
                "last_sync": r.last_sync.isoformat(timespec="minutes") if r.last_sync else "", "note": json.loads(r.sync_note or "{}")}
    out["google_ready"] = google_ready()
    out["ms_permissions"] = {"read": MS_READ_PERMS, "manage": MS_MANAGE_PERMS}
    out["google_scopes"] = {"read": G_READ, "manage": G_MANAGE}
    return out


def mode_of(tenant: str, provider: str) -> str:
    with session() as s:
        r = _row(s, tenant, provider)
        return r.mode if r and r.status == "ok" else ""


def forget(tenant: str, provider: str) -> dict:
    with session() as s:
        r = _row(s, tenant, provider)
        if r is not None:
            s.delete(r)
    return {"removed": provider, "say": f"{provider} ka admin judaav hata diya (Hoola ke paas ab koi token nahi)."}


# ---------------------------------------------------------------- Google
def google_ready() -> bool:
    from ..config import get_settings
    st = get_settings()
    return bool(st.google_oauth_client_id and st.google_oauth_client_secret and st.public_base_url)


def is_link_state(state: str) -> bool:
    return (state or "").startswith("ita_")


def _redirect() -> str:
    from ..config import get_settings
    return get_settings().public_base_url.rstrip("/") + "/auth/google/callback"


def google_start(tenant: str, mode: str = "read") -> str:
    from ..config import get_settings
    from ..db import MailLinkState
    if not google_ready():
        raise ConnError("Google Workspace jodne ke liye server par Google sign-in (GOOGLE_OAUTH_CLIENT_ID / SECRET, PUBLIC_BASE_URL) chahiye.")
    mode = "manage" if mode == "manage" else "read"
    state = f"ita_{mode[0]}_" + secrets.token_urlsafe(20)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="itadmin"))
    scopes = ["openid", "email"] + G_READ + (G_MANAGE if mode == "manage" else [])
    q = {"client_id": get_settings().google_oauth_client_id, "redirect_uri": _redirect(), "response_type": "code",
         "scope": " ".join(scopes), "access_type": "offline", "prompt": "consent", "state": state}
    return G_AUTH + "?" + urlencode(q)


def google_finish(code: str, state: str) -> dict:
    from ..config import get_settings
    from ..db import MailLinkState
    st = get_settings()
    with session() as s:
        row = s.get(MailLinkState, state)
        if row is None or row.provider != "itadmin" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise ConnError("Yeh link purana ho gaya. App se dobara 'Google Workspace jodiye' dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    mode = "manage" if state.startswith("ita_m_") else "read"
    code_, tok = _req("POST", G_TOKEN, form={"code": code, "client_id": st.google_oauth_client_id, "client_secret": st.google_oauth_client_secret,
                                             "redirect_uri": _redirect(), "grant_type": "authorization_code"})
    if code_ != 200 or not tok.get("access_token"):
        raise ConnError("Google ne token nahi diya: " + (_err(tok) or str(code_)))
    granted = (tok.get("scope") or "").split()
    if G_READ[0] not in granted:
        raise ConnError("Users dekhne ki permission nahi di gayi (admin account se jodiye aur sab box tick kijiye).")
    if mode == "manage" and G_MANAGE[0] not in granted:
        mode = "read"
    if not tok.get("refresh_token"):
        raise ConnError("Google se refresh token nahi mila; dobara jodiye.")
    c2, info = _req("GET", "https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
    with session() as s:
        r = _row(s, tenant, "google") or ItadminConn(id=f"{tenant}:google", tenant_id=tenant, provider="google")
        s.add(r)
        r.mode, r.account = mode, str((info or {}).get("email") or "").lower()[:160]
        r.access_sealed, r.refresh_sealed = _seal(tok["access_token"]), _seal(tok["refresh_token"])
        r.scopes = " ".join(granted)[:2000]
        r.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        r.status, r.last_error = "ok", ""
        acct = r.account
    return {"tenant": tenant, "account": acct, "mode": mode}


def _g_token(tenant: str) -> str:
    from ..config import get_settings
    with session() as s:
        r = _row(s, tenant, "google")
        if r is None:
            raise ConnError("Google Workspace abhi juda nahi.")
        exp = as_utc(r.expiry)
        if exp and exp > now() + timedelta(seconds=90) and r.access_sealed:
            return _open(r.access_sealed)
        refresh = _open(r.refresh_sealed)
    st = get_settings()
    c, tok = _req("POST", G_TOKEN, form={"client_id": st.google_oauth_client_id, "client_secret": st.google_oauth_client_secret,
                                         "refresh_token": refresh, "grant_type": "refresh_token"})
    with session() as s:
        r = _row(s, tenant, "google")
        if c != 200 or not tok.get("access_token"):
            r.status, r.last_error = "error", (_err(tok) or str(c))[:300]
            raise ConnError("Google Workspace ka login expire ho gaya; dobara jodiye.")
        r.access_sealed = _seal(tok["access_token"])
        r.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        return tok["access_token"]


def _g_pages(token: str, url: str, key: str, limit: int = 2000) -> tuple[list[dict], str]:
    out, nxt, err = [], "", ""
    for _ in range(40):
        u = url + (("&" if "?" in url else "?") + "pageToken=" + quote(nxt) if nxt else "")
        c, data = _req("GET", u, token)
        if c != 200:
            return out, _err(data) or f"HTTP {c}"
        out += data.get(key) or []
        nxt = data.get("nextPageToken") or ""
        if not nxt or len(out) >= limit:
            break
    return out, err


def google_pull(tenant: str) -> dict:
    t = _g_token(tenant)
    users, e1 = _g_pages(t, G_DIR + "users?customer=my_customer&maxResults=200&projection=basic", "users")
    if e1 and not users:
        raise ConnError("Google ne users list nahi di: " + e1)
    mobile, e2 = _g_pages(t, G_DIR + "customer/my_customer/devices/mobile?maxResults=100", "mobiledevices")
    chrome, e3 = _g_pages(t, G_DIR + "customer/my_customer/devices/chromeos?maxResults=100", "chromeosdevices")
    lic, e4 = _g_pages(t, G_LIC + G_PRODUCT + "/users?customerId=my_customer&maxResults=100", "items")
    return {"users": users, "mobile": mobile, "chrome": chrome, "licences": lic,
            "notes": {k: v for k, v in (("mobile", e2), ("chromeos", e3), ("licences", e4)) if v}}


# ---------------------------------------------------------------- Microsoft
def ms_save(tenant: str, directory_id: str, client_id: str, client_secret: str, mode: str = "read") -> dict:
    d, cid, sec = (directory_id or "").strip(), (client_id or "").strip(), (client_secret or "").strip()
    if not d or not cid or not sec:
        raise ConnError("Directory (tenant) ID, Application (client) ID aur client secret teeno chahiye (sirf app mein likhiye).")
    tok = _ms_token(d, cid, sec)            # verify it works before keeping it
    with session() as s:
        r = _row(s, tenant, "microsoft") or ItadminConn(id=f"{tenant}:microsoft", tenant_id=tenant, provider="microsoft")
        s.add(r)
        r.mode = "manage" if mode == "manage" else "read"
        r.account, r.client_id, r.secret_sealed = d[:160], cid[:120], _seal(sec)
        r.access_sealed, r.expiry = _seal(tok["access_token"]), now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        r.status, r.last_error = "ok", ""
    return {"provider": "microsoft", "mode": r.mode, "consent_url": ms_consent_url(d, cid),
            "say": "Microsoft 365 jud gaya (secret band tijori mein, kabhi dikhaya nahi jayega). Admin consent na diya ho to link kholiye."}


def ms_consent_url(directory_id: str, client_id: str) -> str:
    return f"https://login.microsoftonline.com/{quote(directory_id)}/adminconsent?client_id={quote(client_id)}"


def _ms_token(d: str, cid: str, sec: str) -> dict:
    c, tok = _req("POST", f"https://login.microsoftonline.com/{quote(d)}/oauth2/v2.0/token",
                  form={"client_id": cid, "client_secret": sec, "scope": "https://graph.microsoft.com/.default",
                        "grant_type": "client_credentials"})
    if c != 200 or not tok.get("access_token"):
        raise ConnError("Microsoft ne token nahi diya (IDs / secret / consent dekhiye): " + (_err(tok) or str(c)))
    return tok


def _m_token(tenant: str) -> str:
    with session() as s:
        r = _row(s, tenant, "microsoft")
        if r is None:
            raise ConnError("Microsoft 365 abhi juda nahi.")
        exp = as_utc(r.expiry)
        if exp and exp > now() + timedelta(seconds=90) and r.access_sealed:
            return _open(r.access_sealed)
        d, cid, sec = r.account, r.client_id, _open(r.secret_sealed)
    try:
        tok = _ms_token(d, cid, sec)
    except ConnError as e:
        with session() as s:
            r = _row(s, tenant, "microsoft")
            r.status, r.last_error = "error", str(e)[:300]
        raise
    with session() as s:
        r = _row(s, tenant, "microsoft")
        r.access_sealed = _seal(tok["access_token"])
        r.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
    return tok["access_token"]


def _m_pages(token: str, url: str, limit: int = 3000) -> tuple[list[dict], str]:
    out, u = [], url
    for _ in range(40):
        c, data = _req("GET", u, token)
        if c != 200:
            return out, _err(data) or f"HTTP {c}"
        out += data.get("value") or []
        u = data.get("@odata.nextLink") or ""
        if not u or len(out) >= limit or not u.startswith(MS_GRAPH):
            break
    return out, ""


def ms_pull(tenant: str) -> dict:
    t = _m_token(tenant)
    skus, e1 = _m_pages(t, MS_GRAPH + "subscribedSkus")
    users, e2 = _m_pages(t, MS_GRAPH + "users?$select=id,displayName,userPrincipalName,mail,accountEnabled,assignedLicenses,jobTitle,department&$top=999")
    if e2 and not users:
        raise ConnError("Microsoft ne users list nahi di: " + e2)
    devices, e3 = _m_pages(t, MS_GRAPH + "deviceManagement/managedDevices?$select=id,deviceName,serialNumber,operatingSystem,osVersion,userPrincipalName,model,manufacturer")
    roles, e4 = _m_pages(t, MS_GRAPH + "directoryRoles?$expand=members($select=id)")
    return {"skus": skus, "users": users, "devices": devices, "roles": roles,
            "notes": {k: v for k, v in (("licences", e1), ("devices", e3), ("roles", e4)) if v}}


# ---------------------------------------------------------------- the ONE write path (called only after her tap)
def execute(tenant: str, provider: str, api: dict) -> dict:
    if mode_of(tenant, provider) != "manage":
        raise ConnError("Admin judaav sirf 'dekhne' (read) wala hai: badlaav console mein khud kijiye.")
    method, url = str(api.get("method") or ""), str(api.get("url") or "")
    allowed = (G_DIR + "users/", G_LIC) if provider == "google" else (MS_GRAPH + "users/",)
    if method not in ("PATCH", "POST", "DELETE") or not url.startswith(allowed):
        raise ConnError("Yeh call allowed nahi.")
    t = _g_token(tenant) if provider == "google" else _m_token(tenant)
    c, data = _req(method, url, t, body=api.get("body"))
    if c not in (200, 201, 202, 204):
        raise ConnError(f"{provider} ne mana kiya (HTTP {c}): {_err(data) or 'permission dekhiye'}")
    return {"http": c}
