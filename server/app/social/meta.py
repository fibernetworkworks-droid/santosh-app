"""v0.348 SOCIAL MEDIA MANAGER: Hoola's one Meta app talking to Instagram and Facebook through the official APIs only.

Two sign-ins (users never type a password or a key into Hoola; each logs in on the platform's own page):
  * Instagram API with Instagram Login  - instagram.com/oauth/authorize -> short token -> 60-day token (refreshable)
  * Facebook Login for Business         - facebook.com/<v>/dialog/oauth?config_id=... -> user token -> 60-day token
                                          -> the Pages she picked, each with its own Page token
Reads in Phase 1: profile / Page, recent media / posts with their numbers (likes, comments, reach, saves, shares, views).
Nothing is published in Phase 1. Meta's signed_request (data deletion / deauthorize callbacks) is verified here.
Every call goes through _client() so tests inject a mock transport (set_http)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any
from urllib.parse import urlencode

import httpx

from ..config import get_settings

_http: httpx.Client | None = None

IG_AUTH = "https://www.instagram.com/oauth/authorize"
IG_TOKEN = "https://api.instagram.com/oauth/access_token"
IG_GRAPH = "https://graph.instagram.com"
FB_DIALOG = "https://www.facebook.com"
FB_GRAPH = "https://graph.facebook.com"

# Phase 1 asks for read access only; publishing / comments / messages are asked for in later phases (App Review per permission).
IG_SCOPES_READ = ["instagram_business_basic", "instagram_business_manage_insights"]
FB_SCOPES_READ = ["pages_show_list", "pages_read_engagement", "read_insights", "business_management"]


class MetaError(Exception):
    pass


def set_http(c: httpx.Client | None) -> None:
    global _http
    _http = c


def _client() -> tuple[httpx.Client, bool]:
    return (_http, False) if _http is not None else (httpx.Client(timeout=30), True)


def _v() -> str:
    return getattr(get_settings(), "meta_social_version", "") or "v25.0"


def redirect_uri(platform: str) -> str:
    """Must match, character for character, what is saved in the Meta app."""
    return get_settings().public_base_url.rstrip("/") + f"/api/social/{platform}/callback"


def configured(platform: str) -> bool:
    st = get_settings()
    base = bool(st.public_base_url)
    if platform == "instagram":
        return base and bool(st.instagram_app_id and st.instagram_app_secret)
    if platform == "facebook":
        return base and bool(st.meta_app_id and st.meta_app_secret)
    return False


def _req(method: str, url: str, **kw: Any) -> dict[str, Any]:
    c, own = _client()
    try:
        r = c.request(method, url, timeout=30, **kw)
    except httpx.HTTPError as e:
        raise MetaError(f"Meta se baat nahi hui ({type(e).__name__}).")
    finally:
        if own:
            c.close()
    try:
        js = r.json()
    except ValueError:
        js = {}
    if r.status_code >= 400 or (isinstance(js, dict) and js.get("error")):
        err = js.get("error") if isinstance(js, dict) else None
        msg = (err.get("message") if isinstance(err, dict) else err) or js.get("error_message") or r.text[:200]
        code = err.get("code") if isinstance(err, dict) else None
        e = MetaError(f"Meta: {str(msg)[:220]}")
        e.code = code                     # 190 = token expired / revoked; 10 / 200 = missing permission
        raise e
    return js if isinstance(js, dict) else {"data": js}


# ---------------------------------------------------------------- Instagram Login
def ig_auth_url(state: str, scopes: list[str] | None = None) -> str:
    st = get_settings()
    q = {"client_id": st.instagram_app_id, "redirect_uri": redirect_uri("instagram"), "response_type": "code",
         "scope": ",".join(scopes or IG_SCOPES_READ), "state": state}
    return IG_AUTH + "?" + urlencode(q)


def ig_exchange(code: str) -> dict[str, Any]:
    """code -> 60-day token. Instagram appends '#_' to the code in the redirect; it is not part of the code."""
    st = get_settings()
    code = (code or "").split("#")[0]
    short = _req("POST", IG_TOKEN, data={"client_id": st.instagram_app_id, "client_secret": st.instagram_app_secret,
                                         "grant_type": "authorization_code", "redirect_uri": redirect_uri("instagram"),
                                         "code": code})
    if isinstance(short.get("data"), list) and short["data"]:          # older response shape
        short = short["data"][0]
    tok = short.get("access_token")
    if not tok:
        raise MetaError("Instagram ne token nahi diya.")
    long = _req("GET", f"{IG_GRAPH}/access_token", params={"grant_type": "ig_exchange_token",
                                                           "client_secret": st.instagram_app_secret, "access_token": tok})
    perms = short.get("permissions")
    return {"access_token": long.get("access_token") or tok, "expires_in": int(long.get("expires_in") or 3600),
            "user_id": str(short.get("user_id") or ""),
            "scopes": perms if isinstance(perms, list) else str(perms or "").split(",")}


def ig_refresh(token: str) -> dict[str, Any]:
    """A 60-day Instagram token that is at least 24 hours old and still valid gets another 60 days."""
    js = _req("GET", f"{IG_GRAPH}/refresh_access_token", params={"grant_type": "ig_refresh_token", "access_token": token})
    return {"access_token": js.get("access_token") or token, "expires_in": int(js.get("expires_in") or 0)}


def ig_profile(token: str) -> dict[str, Any]:
    return _req("GET", f"{IG_GRAPH}/{_v()}/me", params={
        "fields": "user_id,username,name,account_type,profile_picture_url,followers_count,follows_count,media_count",
        "access_token": token})


def ig_media(token: str, limit: int = 50) -> list[dict[str, Any]]:
    js = _req("GET", f"{IG_GRAPH}/{_v()}/me/media", params={
        "fields": "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count",
        "limit": min(limit, 100), "access_token": token})
    return [m for m in js.get("data") or [] if isinstance(m, dict)]


IG_POST_METRICS = ("reach", "saved", "shares", "views", "total_interactions")


def ig_media_insights(token: str, media_id: str) -> dict[str, int]:
    """Per-post numbers. Metric names change across versions and media types, so ask once for all and, if refused, one by one."""
    def ask(metrics):
        js = _req("GET", f"{IG_GRAPH}/{_v()}/{media_id}/insights", params={"metric": ",".join(metrics), "access_token": token})
        out = {}
        for m in js.get("data") or []:
            vals = m.get("values") or [{}]
            v = (m.get("total_value") or {}).get("value", vals[0].get("value") if vals else None)
            if isinstance(v, (int, float)):
                out[m.get("name")] = int(v)
        return out
    try:
        return ask(IG_POST_METRICS)
    except MetaError as e:
        if getattr(e, "code", None) == 190:
            raise
        out: dict[str, int] = {}
        for m in IG_POST_METRICS:
            try:
                out.update(ask([m]))
            except MetaError as e2:
                if getattr(e2, "code", None) == 190:
                    raise
        return out


# ---------------------------------------------------------------- Facebook Login for Business (Pages)
def fb_auth_url(state: str) -> str:
    st = get_settings()
    q = {"client_id": st.meta_app_id, "redirect_uri": redirect_uri("facebook"), "state": state, "response_type": "code"}
    if st.meta_login_config_id:
        q["config_id"] = st.meta_login_config_id          # the configuration holds the permissions + asset (Page) picker
    else:
        q["scope"] = ",".join(FB_SCOPES_READ)
    return f"{FB_DIALOG}/{_v()}/dialog/oauth?" + urlencode(q)


def fb_exchange(code: str) -> dict[str, Any]:
    st = get_settings()
    short = _req("GET", f"{FB_GRAPH}/{_v()}/oauth/access_token", params={
        "client_id": st.meta_app_id, "client_secret": st.meta_app_secret, "redirect_uri": redirect_uri("facebook"), "code": code})
    long = _req("GET", f"{FB_GRAPH}/{_v()}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": st.meta_app_id, "client_secret": st.meta_app_secret,
        "fb_exchange_token": short.get("access_token", "")})
    tok = long.get("access_token") or short.get("access_token")
    if not tok:
        raise MetaError("Facebook ne token nahi diya.")
    me = _req("GET", f"{FB_GRAPH}/{_v()}/me", params={"fields": "id,name", "access_token": tok})
    return {"access_token": tok, "expires_in": int(long.get("expires_in") or 60 * 86400), "user_id": str(me.get("id") or ""),
            "name": me.get("name") or ""}


def fb_pages(user_token: str) -> list[dict[str, Any]]:
    js = _req("GET", f"{FB_GRAPH}/{_v()}/me/accounts", params={
        "fields": "id,name,access_token,category,fan_count,followers_count,picture{url},tasks", "limit": 50,
        "access_token": user_token})
    return [p for p in js.get("data") or [] if isinstance(p, dict) and p.get("access_token")]


def fb_posts(page_id: str, page_token: str, limit: int = 50) -> list[dict[str, Any]]:
    js = _req("GET", f"{FB_GRAPH}/{_v()}/{page_id}/posts", params={
        "fields": "id,message,created_time,permalink_url,status_type,shares,reactions.summary(true).limit(0),"
                  "comments.summary(true).limit(0)", "limit": min(limit, 100), "access_token": page_token})
    return [p for p in js.get("data") or [] if isinstance(p, dict)]


def fb_post_reach(post_id: str, page_token: str) -> int | None:
    """Unique people reached; Meta renames Page metrics often - a refusal just leaves reach empty."""
    for metric in ("post_impressions_unique", "post_total_media_view_unique"):
        try:
            js = _req("GET", f"{FB_GRAPH}/{_v()}/{post_id}/insights", params={"metric": metric, "access_token": page_token})
        except MetaError as e:
            if getattr(e, "code", None) == 190:
                raise
            continue
        for m in js.get("data") or []:
            vals = m.get("values") or []
            if vals and isinstance(vals[0].get("value"), (int, float)):
                return int(vals[0]["value"])
    return None


def fb_debug_token(token: str) -> dict[str, Any]:
    """Is a user token still valid, and when does it end (app token = id|secret)."""
    st = get_settings()
    js = _req("GET", f"{FB_GRAPH}/{_v()}/debug_token", params={"input_token": token,
                                                              "access_token": f"{st.meta_app_id}|{st.meta_app_secret}"})
    return js.get("data") or {}


# ---------------------------------------------------------------- Meta's callbacks (data deletion / deauthorize)
def parse_signed_request(signed: str) -> dict[str, Any]:
    """Verify Meta's signed_request (HMAC-SHA256 with the app secret - Facebook app or Instagram app) -> payload."""
    try:
        sig_b64, payload_b64 = (signed or "").split(".", 1)
    except ValueError:
        raise MetaError("signed_request galat.")
    pad = lambda x: x + "=" * (-len(x) % 4)                             # noqa: E731
    try:
        sig = base64.urlsafe_b64decode(pad(sig_b64))
        payload = json.loads(base64.urlsafe_b64decode(pad(payload_b64)))
    except (ValueError, json.JSONDecodeError):
        raise MetaError("signed_request padha nahi gaya.")
    st = get_settings()
    for secret in (st.meta_app_secret, st.instagram_app_secret):
        if secret and hmac.compare_digest(sig, hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).digest()):
            return payload
    raise MetaError("signed_request ka signature mel nahi khaata.")
