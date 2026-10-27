"""Her Google Business Profile reviews over the official API (scope business.manage; Google must have approved API
access for the Cloud project). Read: accounts -> locations -> reviews. Write: ONE reply, only from `service.reply_decide`
(her tap). OAuth helpers are the same ones SEO Sahayak (v0.103) uses for Search Console; the http client defaults to SEO's.

Endpoints (developers.google.com/my-business, checked 23 Oct 2026):
  GET  https://mybusinessaccountmanagement.googleapis.com/v1/accounts
  GET  https://mybusinessbusinessinformation.googleapis.com/v1/{account}/locations?readMask=name,title
  GET  https://mybusiness.googleapis.com/v4/{account}/{location}/reviews?pageSize=50&pageToken=
  PUT  https://mybusiness.googleapis.com/v4/{review name}/reply  {"comment": "..."}
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx

from ..db import now, session
from .models import FbGoogle

log = logging.getLogger("santosh.feedback.gbp")
SCOPE = "https://www.googleapis.com/auth/business.manage"
ACCOUNTS = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
INFO = "https://mybusinessbusinessinformation.googleapis.com/v1/"
V4 = "https://mybusiness.googleapis.com/v4/"
STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
_HTTP: httpx.Client | None = None


class GbpError(Exception):
    pass


def set_http(c: httpx.Client | None) -> None:
    global _HTTP
    _HTTP = c


def _client() -> tuple[httpx.Client, bool]:
    if _HTTP is not None:
        return _HTTP, False
    try:
        from ..seo.service import _client as seo_client       # SEO Sahayak's client (tests may inject one there)
        return seo_client()
    except Exception:
        return httpx.Client(timeout=30, follow_redirects=False), True


def ready() -> bool:
    from ..mailbox import accounts as mail_acc
    return mail_acc.oauth_ready("google")


def is_link_state(state: str) -> bool:
    return (state or "").startswith("fbk_")


def start_link(tenant: str) -> str:
    from .. import accounts as acc
    from ..config import get_settings
    from ..db import MailLinkState
    from ..mailbox import accounts as mail_acc
    if not ready():
        raise GbpError("Google Business Profile jodne ke liye server par Google sign-in (GOOGLE_OAUTH_CLIENT_ID / SECRET, "
                       "PUBLIC_BASE_URL) chahiye.")
    st = get_settings()
    state = "fbk_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="feedback"))
    q = {"client_id": st.google_oauth_client_id, "redirect_uri": acc._redirect_uri(), "response_type": "code",
         "scope": " ".join(["openid", "email", SCOPE]), "access_type": "offline", "prompt": "consent", "state": state,
         "include_granted_scopes": "true"}
    return mail_acc.GOOGLE_AUTH + "?" + urlencode(q)


def finish_link(code: str, state: str) -> dict:
    from .. import accounts as acc
    from ..config import get_settings
    from ..db import MailLinkState, as_utc
    from ..mailbox import accounts as mail_acc
    st = get_settings()
    with session() as s:
        row = s.get(MailLinkState, state)
        if row is None or row.provider != "feedback" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise GbpError("Yeh link purana ho gaya. App se dobara 'Google reviews jodiye' dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "redirect_uri": acc._redirect_uri(), "grant_type": "authorization_code"})
        if SCOPE not in (tok.get("scope") or "").split():
            raise GbpError("Business Profile dekhne ki permission nahi di gayi.")
        info = mail_acc._get("https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
    except mail_acc.MailError as e:
        raise GbpError(str(e))
    if not tok.get("refresh_token"):
        raise GbpError("Google se refresh token nahi mila; dobara jodiye.")
    with session() as s:
        g = s.get(FbGoogle, tenant) or FbGoogle(tenant_id=tenant)
        s.add(g)
        g.address = (info.get("email") or "").lower()
        g.access_token_enc = acc.encrypt(tok["access_token"])
        g.refresh_token_enc = acc.encrypt(tok["refresh_token"])
        g.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        g.status, g.last_error = "ok", ""
        addr = g.address
    try:
        pick_location(tenant)
    except GbpError:
        pass
    return {"address": addr, "tenant": tenant}


def _token(tenant: str, force: bool = False) -> str:
    from .. import accounts as acc
    from ..config import get_settings
    from ..db import as_utc
    from ..mailbox import accounts as mail_acc
    with session() as s:
        g = s.get(FbGoogle, tenant)
        if g is None:
            raise GbpError("Google Business Profile abhi juda nahi. Feedback > Sources > 'Google reviews jodiye'.")
        exp = as_utc(g.expiry)
        if not force and g.access_token_enc and exp and exp > now() + timedelta(seconds=90):
            return acc.decrypt(g.access_token_enc) or ""
        refresh = acc.decrypt(g.refresh_token_enc)
    st = get_settings()
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"client_id": st.google_oauth_client_id, "client_secret": st.google_oauth_client_secret,
                                                     "refresh_token": refresh, "grant_type": "refresh_token"})
    except Exception as e:
        with session() as s:
            g = s.get(FbGoogle, tenant)
            if g:
                g.status, g.last_error = "error", str(e)[:400]
        raise GbpError("Google Business Profile ka login expire ho gaya; dobara jodiye.")
    with session() as s:
        g = s.get(FbGoogle, tenant)
        g.access_token_enc = acc.encrypt(tok["access_token"])
        g.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        g.status = "ok"
    return tok["access_token"]


def _call(tenant: str, method: str, url: str, body: dict | None = None) -> dict:
    c, own = _client()
    try:
        for force in (False, True):
            h = {"Authorization": f"Bearer {_token(tenant, force)}"}
            try:
                r = c.request(method, url, headers=h, json=body, timeout=40)
            except httpx.HTTPError as e:
                raise GbpError(f"Google se baat nahi hui ({type(e).__name__}).")
            if r.status_code == 401 and not force:
                continue
            if r.status_code == 403:
                raise GbpError("Google ne mana kiya: is account ke paas yeh Business Profile nahi, ya Cloud project ko "
                               "Business Profile API ki manzoori abhi nahi mili.")
            if r.status_code == 429:
                raise GbpError("Google ki limit poori; thodi der baad.")
            if r.status_code >= 400:
                raise GbpError(f"Google: {r.text[:200]}")
            return r.json() if r.content else {}
    finally:
        if own:
            c.close()
    raise GbpError("Google login nahi chala.")


def status(tenant: str) -> dict:
    with session() as s:
        g = s.get(FbGoogle, tenant)
        return {"connected": bool(g), "address": g.address if g else "", "status": g.status if g else "",
                "location": g.location if g else "", "location_title": g.location_title if g else "",
                "last_sync": g.last_sync.isoformat() if g and g.last_sync else "", "error": g.last_error if g else "",
                "can_link": ready()}


def locations(tenant: str) -> list[dict]:
    out = []
    accts = _call(tenant, "GET", ACCOUNTS).get("accounts") or []
    for a in accts[:10]:
        nxt = ""
        for _ in range(5):
            q = {"readMask": "name,title", "pageSize": 100}
            if nxt:
                q["pageToken"] = nxt
            d = _call(tenant, "GET", INFO + a["name"] + "/locations?" + urlencode(q))
            for loc in d.get("locations") or []:
                lid = (loc.get("name") or "").split("/")[-1]
                out.append({"location": f"{a['name']}/locations/{lid}", "title": loc.get("title") or "", "account": a.get("accountName") or ""})
            nxt = d.get("nextPageToken") or ""
            if not nxt:
                break
    return out


def pick_location(tenant: str, location: str = "") -> dict:
    locs = locations(tenant)
    if not locs:
        raise GbpError("Is Google account mein koi Business Profile location nahi mili.")
    pick = next((x for x in locs if x["location"] == location), None) if location else locs[0]
    if pick is None:
        raise GbpError("Woh location is account mein nahi.")
    with session() as s:
        g = s.get(FbGoogle, tenant)
        g.location, g.location_title = pick["location"], pick["title"]
    return {"location": pick, "all": locs}


def reviews(tenant: str, limit: int = 500) -> list[dict]:
    with session() as s:
        g = s.get(FbGoogle, tenant)
        loc = g.location if g else ""
    if not loc:
        loc = pick_location(tenant)["location"]["location"]
    out: list[dict] = []
    nxt = ""
    while len(out) < limit:
        q = {"pageSize": 50}
        if nxt:
            q["pageToken"] = nxt
        d = _call(tenant, "GET", V4 + loc + "/reviews?" + urlencode(q))
        for r in d.get("reviews") or []:
            out.append(review_view(r))
        nxt = d.get("nextPageToken") or ""
        if not nxt:
            break
    with session() as s:
        g = s.get(FbGoogle, tenant)
        if g:
            g.last_sync, g.last_error = now(), ""
    return out


def _original(text: str) -> str:
    """Google puts '(Translated by Google) ... (Original) ...' in comment: keep her customer's own words."""
    t = text or ""
    if "(Original)" in t:
        return t.split("(Original)", 1)[1].strip()
    if t.startswith("(Translated by Google)"):
        return t.replace("(Translated by Google)", "", 1).strip()
    return t.strip()


def review_view(r: dict) -> dict:
    reply = (r.get("reviewReply") or {}).get("comment") or ""
    when = r.get("createTime") or r.get("updateTime") or ""
    try:
        at = datetime.fromisoformat(when.replace("Z", "+00:00"))
    except ValueError:
        at = now()
    return {"id": r.get("reviewId") or (r.get("name") or "").split("/")[-1], "name": r.get("name") or "",
            "author": ((r.get("reviewer") or {}).get("displayName") or "")[:120],
            "anonymous": bool((r.get("reviewer") or {}).get("isAnonymous")),
            "stars": STARS.get(str(r.get("starRating") or "").upper()), "text": _original(r.get("comment") or ""), "at": at,
            "reply": reply, "reply_state": (r.get("reviewReply") or {}).get("reviewReplyState") or ""}


def put_reply(tenant: str, review_name: str, text: str) -> dict:
    if not review_name or "/reviews/" not in review_name:
        raise GbpError("Is review ka Google naam nahi mila.")
    return _call(tenant, "PUT", V4 + review_name + "/reply", {"comment": text})


def forget(tenant: str) -> dict:
    with session() as s:
        g = s.get(FbGoogle, tenant)
        if g:
            s.delete(g)
    return {"say": "Google Business Profile ka judaav hata diya (Google account > Security > third-party access se bhi hata sakti hain)."}
