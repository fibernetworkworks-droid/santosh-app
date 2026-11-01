"""v0.384 SOCIAL MEDIA MANAGER Phase 6 - LinkedIn (her own profile) through Newtika's ONE LinkedIn app:
Sign In with LinkedIn (openid profile) + Share on LinkedIn (w_member_social), the self-serve products that need no partner
review. She logs in on LinkedIn's own page; the token (60 days, LinkedIn gives no refresh token to non-partner apps) is
sealed and she is warned 7 days before it ends. A calendar post with LinkedIn ticked goes to her profile (text + one
picture) exactly as she approved it, like Instagram / Facebook.

Not here (needs LinkedIn's review of the Community Management API): posting as a Company Page, reading comments,
numbers of her LinkedIn posts. Hoola says so instead of pretending."""
from __future__ import annotations

import re
import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from ..config import get_settings
from ..db import now, session
from . import meta as M
from .desk import SocialAccount, SocialError, _event, _hired, ensure_tables

AUTH = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN = "https://www.linkedin.com/oauth/v2/accessToken"
API = "https://api.linkedin.com"
SCOPES = ["openid", "profile", "w_member_social"]
TEXT_MAX = 3000
_RESERVED = re.compile(r"([\\|{}@\[\]()<>#*_~])")


def redirect_uri() -> str:
    return get_settings().public_base_url.rstrip("/") + "/api/social/linkedin/callback"


def connect_url(tenant: str) -> str:
    from ..db import MailLinkState
    _hired(tenant)
    if not M.configured("linkedin"):
        raise SocialError("Server par LinkedIn app ki keys abhi nahi lagi (.env: LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET, PUBLIC_BASE_URL).")
    state = "soc_li_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="social_li"))
    st = get_settings()
    return AUTH + "?" + urlencode({"response_type": "code", "client_id": st.linkedin_client_id, "redirect_uri": redirect_uri(),
                                   "state": state, "scope": " ".join(SCOPES)})


def _rest_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "LinkedIn-Version": get_settings().linkedin_version,
            "X-Restli-Protocol-Version": "2.0.0"}


def _call(method: str, url: str, **kw: Any):
    c, own = M._client()
    try:
        r = c.request(method, url, timeout=60, **kw)
    except Exception as e:       # noqa: BLE001
        raise SocialError(f"LinkedIn se baat nahi hui ({type(e).__name__}).")
    finally:
        if own:
            c.close()
    if r.status_code >= 400:
        try:
            js = r.json()
            msg = js.get("message") or js.get("error_description") or js.get("error") or r.text[:200]
        except ValueError:
            msg = r.text[:200]
        e = SocialError(f"LinkedIn: {str(msg)[:220]}")
        e.code = 190 if r.status_code == 401 else r.status_code
        raise e
    return r


def finish(code: str, state: str) -> dict[str, Any]:
    from .. import accounts as acc
    from .desk import _take_state, _upsert_account
    tenant = _take_state(state, "linkedin")
    ensure_tables()
    st = get_settings()
    tok = _call("POST", TOKEN, data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri(),
                                     "client_id": st.linkedin_client_id, "client_secret": st.linkedin_client_secret}).json()
    token = str(tok.get("access_token") or "")
    if not token:
        raise SocialError("LinkedIn ne token nahi diya; dobara Connect kijiye.")
    me = _call("GET", f"{API}/v2/userinfo", headers={"Authorization": f"Bearer {token}"}).json()
    sub = str(me.get("sub") or "")
    if not sub:
        raise SocialError("LinkedIn profile nahi mila.")
    granted = str(tok.get("scope") or " ".join(SCOPES)).replace(" ", ",")
    with session() as s:
        row = _upsert_account(s, tenant, "linkedin", sub)
        row.meta_user_id = sub
        row.handle = str(me.get("name") or "")[:120]
        row.name = str(me.get("name") or "")[:200]
        row.picture = str(me.get("picture") or "")
        row.kind = "Profile"
        row.token_enc = acc.encrypt(token)
        row.expires_at = now() + timedelta(seconds=int(tok.get("expires_in") or 60 * 86400))
        row.scopes = granted
        row.status, row.last_error = "ok", ""
        name = row.name
    _event(tenant, "connect", "ok", f"Connected LinkedIn: {name}. Tick LinkedIn on a calendar post to share it on your profile.")
    return {"platform": "linkedin", "accounts": [name]}


def text_of(caption: str, hashtags: list[str]) -> str:
    """LinkedIn's post text treats \\ | { } @ [ ] ( ) < > # * _ ~ as markup - unescaped, the post is cut off there.
    At most 3 hashtags (LinkedIn readers dislike hashtag walls)."""
    body = (caption or "").split("\n#")[0].strip()
    tags = " ".join(("#" + str(h).lstrip("#")) for h in (hashtags or [])[:3])
    full = (body + ("\n\n" + tags if tags else ""))[:TEXT_MAX]
    return _RESERVED.sub(r"\\\1", full)


def publish(acc: SocialAccount, token: str, text: str, images: list[str]) -> tuple[str, str]:
    """A post on her profile: text + one picture (uploaded first, then referenced). Returns (post urn, link)."""
    author = f"urn:li:person:{acc.account_id}"
    body: dict[str, Any] = {"author": author, "commentary": text, "visibility": "PUBLIC",
                            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
                            "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    if images:
        init = _call("POST", f"{API}/rest/images?action=initializeUpload", headers=_rest_headers(token),
                     json={"initializeUploadRequest": {"owner": author}}).json().get("value") or {}
        up, urn = init.get("uploadUrl"), init.get("image")
        if not up or not urn:
            raise SocialError("LinkedIn ne photo upload ki jagah nahi di.")
        with open(images[0], "rb") as f:
            _call("PUT", up, content=f.read(), headers={"Authorization": f"Bearer {token}"})
        body["content"] = {"media": {"id": urn}}
    r = _call("POST", f"{API}/rest/posts", headers=_rest_headers(token), json=body)
    pid = r.headers.get("x-restli-id") or r.headers.get("x-linkedin-id") or ""
    return pid, (f"https://www.linkedin.com/feed/update/{pid}/" if pid else "")
