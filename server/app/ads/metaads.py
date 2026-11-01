"""v0.417 META ADS (built as 0.409) (ad plan A1): her own Facebook / Instagram ad account through Meta's official Marketing API, one tap.

Before this the Ads desk could read her Meta ads and apply the budget changes she tapped - but only after she pasted a
system-user token from Business Settings, which almost no shop owner can do. Now:
  1. Connect: Facebook Login on Hoola's Meta app with ads_management + ads_read (+ her Pages, which every ad is shown as).
     The 60-day token is sealed; Hoola lists her ad accounts and Pages; one account = chosen at once. Everything the Ads
     desk already did (read insights, money leaks, budget changes on her tap) works on this login unchanged.
  2. Draft (in Hoola only): an ad with ONE goal an Indian shop understands -
        whatsapp   people tap and land in her WhatsApp chat (click-to-WhatsApp)
        messenger  ... in her Page's Messenger
        instagram  ... in her Instagram Direct
        website    visits to her website / shop page
        boost      more people see one of her Page posts
     her picture (a Social Desk asset) + words from her facts, daily budget x days, India or her cities (+ km), ages.
     ASCI / banned-category / money-ad checks from the Ads desk rules; a daily cap (META_ADS_MAX_DAILY).
  3. Check with Meta (free, validate_only) -> Create in HER ad account, everything PAUSED (campaign, ad set, ad).
  4. Start = her tap after a confirm: the ad set gets an end time (Meta itself stops it after her days), then the ad,
     ad set and campaign go ACTIVE. Pause any time. Hoola also marks it finished after the last day and tells her.
Hoola never moves money on its own; money ads (loans, investing) are refused like the YouTube ads.
Needs on the server: META_APP_ID / META_APP_SECRET (the same HOOLA app), PUBLIC_BASE_URL, the redirect
<base>/api/ads/meta/callback saved in the Meta app, and - for anyone but the app's own testers - Meta's App Review for
ads_management / ads_read (Marketing API Full Access). Optional META_ADS_CONFIG_ID = a Facebook Login for Business
configuration holding these permissions."""
from __future__ import annotations

import base64
import json
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, MailLinkState, as_utc, new_id, now, session
from . import service as A

log = logging.getLogger("santosh.ads.meta")
SCOPES = ["ads_management", "ads_read", "business_management", "pages_show_list", "pages_read_engagement"]
GOALS = ("whatsapp", "messenger", "instagram", "website", "boost")
GOAL_LABEL = {"whatsapp": "Chats on WhatsApp", "messenger": "Chats on Messenger", "instagram": "Chats on Instagram",
              "website": "Website visits", "boost": "Boost a Page post"}
SPECIAL = ("HOUSING", "EMPLOYMENT", "FINANCIAL_PRODUCTS_SERVICES")
LIMITS = {"text": 600, "headline": 40, "description": 30}       # Meta's recommended lengths (longer is cut off on phones)
EDITABLE = ("draft", "checked", "failed")


class MetaAdsError(Exception):
    pass


class MetaAdDraft(Base):
    """A Facebook / Instagram ad she is shaping. Lives only in Hoola until she taps Create (paused in Meta) and Start."""
    __tablename__ = "meta_ad_drafts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mad"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    goal: Mapped[str] = mapped_column(String(12), default="whatsapp")
    page_id: Mapped[str] = mapped_column(String(30), default="")
    post_id: Mapped[str] = mapped_column(String(60), default="")          # boost: <page>_<post> or the post id alone
    image_asset: Mapped[str] = mapped_column(String(40), default="")      # social publish SocialAsset id
    text: Mapped[str] = mapped_column(Text, default="")                   # primary text
    headline: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(String(120), default="")
    link: Mapped[str] = mapped_column(Text, default="")                   # website goal
    platforms: Mapped[str] = mapped_column(String(12), default="both")    # both | facebook | instagram
    cities: Mapped[str] = mapped_column(Text, default="[]")               # names; empty = all India
    radius_km: Mapped[int] = mapped_column(Integer, default=25)
    age_min: Mapped[int] = mapped_column(Integer, default=18)
    age_max: Mapped[int] = mapped_column(Integer, default=65)
    gender: Mapped[str] = mapped_column(String(8), default="all")        # all | men | women
    special: Mapped[str] = mapped_column(String(40), default="")          # Meta special ad category, if any
    daily: Mapped[int] = mapped_column(Integer, default=300)              # whole units of her account currency a day
    days: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(12), default="draft")      # draft | checked | created | running | paused | ended | failed
    campaign_id: Mapped[str] = mapped_column(String(30), default="")
    adset_id: Mapped[str] = mapped_column(String(30), default="")
    ad_id: Mapped[str] = mapped_column(String(30), default="")
    stop_on: Mapped[str] = mapped_column(String(10), default="")          # last day it may run (her local date)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_READY: set[int] = set()


def ensure_tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        MetaAdDraft.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except ValueError:
        return default


def _cap() -> int:
    return int(getattr(get_settings(), "meta_ads_max_daily", 2000) or 2000)


def configured() -> bool:
    st = get_settings()
    return bool(st.meta_app_id and st.meta_app_secret and st.public_base_url)


def _ver() -> str:
    return getattr(get_settings(), "meta_graph_version", "") or "v26.0"


def redirect_uri() -> str:
    """Must be saved, character for character, in the HOOLA Meta app (Facebook Login > Valid OAuth Redirect URIs)."""
    return get_settings().public_base_url.rstrip("/") + "/api/ads/meta/callback"


def _g(method: str, path: str, token: str, params: dict | None = None) -> dict[str, Any]:
    """The Ads desk's own Graph call (one place for errors); nested values go as JSON, like Meta's docs show."""
    p = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in (params or {}).items() if v is not None}
    try:
        return A._graph(method, path, token, p)
    except A.AdsError as e:
        raise MetaAdsError(str(e))


# ---------------------------------------------------------------- connecting (Facebook Login with the ads permissions)
def is_link_state(state: str) -> bool:
    return (state or "").startswith("mad_")


def connect_url(tenant: str) -> str:
    if not configured():
        raise MetaAdsError("Server par Meta app ki keys abhi nahi lagi (.env: META_APP_ID / META_APP_SECRET, PUBLIC_BASE_URL).")
    st = get_settings()
    state = "mad_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="metaads"))
    q = {"client_id": st.meta_app_id, "redirect_uri": redirect_uri(), "state": state, "response_type": "code"}
    cfg = getattr(st, "meta_ads_config_id", "")
    if cfg:
        q["config_id"] = cfg
    else:
        q["scope"] = ",".join(SCOPES)
    return f"https://www.facebook.com/{_ver()}/dialog/oauth?" + urlencode(q)


def _exchange(code: str) -> tuple[str, int]:
    st = get_settings()
    app = f"{st.meta_app_id}|{st.meta_app_secret}"          # the app token; this endpoint is authorised by client_secret
    short = _g("GET", "oauth/access_token", app, {"client_id": st.meta_app_id, "client_secret": st.meta_app_secret,
                                                 "redirect_uri": redirect_uri(), "code": code})
    tok = str(short.get("access_token") or "")
    if not tok:
        raise MetaAdsError("Facebook ne token nahi diya; dobara 'Connect with Facebook' dabaiye.")
    try:
        long = _g("GET", "oauth/access_token", app, {"grant_type": "fb_exchange_token", "client_id": st.meta_app_id,
                                                    "client_secret": st.meta_app_secret, "fb_exchange_token": tok})
        if long.get("access_token"):
            return str(long["access_token"]), int(long.get("expires_in") or 60 * 86400)
    except MetaAdsError as e:
        log.info("long-lived exchange failed: %s", e)
    return tok, int(short.get("expires_in") or 3600)


def _granted(token: str) -> set[str]:
    try:
        js = _g("GET", "me/permissions", token)
    except MetaAdsError:
        return set()
    return {str(p.get("permission")) for p in js.get("data") or [] if p.get("status") == "granted"}


def _accounts(token: str) -> list[dict[str, Any]]:
    js = _g("GET", "me/adaccounts", token, {"fields": "account_id,name,currency,account_status,business{name}", "limit": 50})
    out = []
    for a in js.get("data") or []:
        aid = re.sub(r"\D", "", str(a.get("account_id") or a.get("id") or ""))
        if aid:
            out.append({"id": "act_" + aid, "name": str(a.get("name") or "")[:160], "currency": str(a.get("currency") or ""),
                        "active": a.get("account_status") in (1, None), "business": str((a.get("business") or {}).get("name") or "")})
    return out


def _pages(token: str) -> list[dict[str, Any]]:
    try:
        js = _g("GET", "me/accounts", token, {"fields": "id,name,instagram_business_account{id,username}", "limit": 50})
    except MetaAdsError:
        js = _g("GET", "me/accounts", token, {"fields": "id,name", "limit": 50})
    out = []
    for p in js.get("data") or []:
        ig = p.get("instagram_business_account") or {}
        out.append({"id": str(p.get("id") or ""), "name": str(p.get("name") or "")[:160],
                    "ig_id": str(ig.get("id") or ""), "ig": str(ig.get("username") or "")})
    return [p for p in out if p["id"]]


def finish_link(code: str, state: str) -> dict[str, Any]:
    from ..bazar.security import vault
    with session() as s:
        row = s.get(MailLinkState, state)
        if row is None or row.provider != "metaads" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise MetaAdsError("Yeh link purana ho gaya. Dobara 'Connect with Facebook' dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    token, life = _exchange(code)
    got = _granted(token)
    if got and not {"ads_management", "ads_read"} & got:
        raise MetaAdsError("Facebook par ads ki permission nahi di gayi. Dobara jodte waqt 'ad accounts' allow kijiye.")
    accts, pages = _accounts(token), _pages(token)
    with session() as s:
        r = A._row(s, tenant)
        r.meta_token, r.meta_checked = vault().seal(token), now()
        r.meta_via, r.meta_expires = "login", now() + timedelta(seconds=life)
        r.meta_accounts, r.meta_pages = json.dumps(accts, ensure_ascii=False), json.dumps(pages, ensure_ascii=False)
        r.meta_scopes = ",".join(sorted(got))[:500]
        if r.meta_account and r.meta_account not in {a["id"] for a in accts}:
            r.meta_account = r.meta_name = r.meta_currency = ""      # the old account is not in this login
        if not r.meta_page and len(pages) == 1:
            r.meta_page = pages[0]["id"]
    usable = [a for a in accts if a["active"]]
    if len(usable) == 1:
        choose(tenant, usable[0]["id"])
    return {"accounts": [a["name"] or a["id"] for a in accts], "pages": [p["name"] for p in pages],
            "chosen": len(usable) == 1}


def choose(tenant: str, account: str = "", page: str = "") -> dict[str, Any]:
    with session() as s:
        r = A._row(s, tenant)
        if r.meta_via != "login":
            raise MetaAdsError("Pehle 'Connect with Facebook' dabaiye.")
        if account:
            a = next((x for x in _j(r.meta_accounts, []) if x["id"] == account), None)
            if a is None:
                raise MetaAdsError("Yeh ad account aapke Facebook login mein nahi mila.")
            if not a.get("active"):
                raise MetaAdsError("Yeh ad account Meta mein band / ruka hua hai (Ads Manager > Account status dekhiye).")
            r.meta_account, r.meta_name, r.meta_currency = a["id"], a["name"], a["currency"]
        if page:
            if page not in {p["id"] for p in _j(r.meta_pages, [])}:
                raise MetaAdsError("Yeh Page aapke Facebook login mein nahi mila.")
            r.meta_page = page
        return {"account": r.meta_account, "name": r.meta_name, "currency": r.meta_currency, "page": r.meta_page}


def _ctx(tenant: str) -> tuple[str, str, str, str]:
    """(ad account, token, currency, page) - or a clear line about what is missing."""
    acct, tok = A._token(tenant)
    with session() as s:
        r = A._row(s, tenant)
        cur, page, exp = r.meta_currency, r.meta_page, as_utc(r.meta_expires)
    if exp and exp < now():
        raise MetaAdsError("Facebook login purana ho gaya (60 din). 'Connect with Facebook' dobara dabaiye.")
    return acct, tok, cur, page


# ---------------------------------------------------------------- drafts (in Hoola only)
def _page_of(tenant: str, page_id: str) -> dict[str, Any] | None:
    with session() as s:
        r = s.get(A.AdsSettings, tenant)
        pages = _j(r.meta_pages, []) if r is not None else []
    return next((p for p in pages if p["id"] == page_id), None)


def draft_problems(tenant: str, d: MetaAdDraft) -> list[str]:
    from .rules import banned, financial
    out = []
    if d.goal not in GOALS:
        out.append("Ad ka maqsad chuniye: WhatsApp / Messenger / Instagram chats, website ya post boost.")
    page = _page_of(tenant, d.page_id)
    if page is None:
        out.append("Facebook Page chuniye - har ad kisi Page ke naam se chalta hai.")
    if d.goal == "instagram" and page is not None and not page.get("ig_id"):
        out.append("Is Page se koi Instagram professional account juda nahi hai (Page settings > Linked accounts).")
    if d.goal == "boost":
        if not re.fullmatch(r"(\d{5,25}_)?\d{5,25}", d.post_id or ""):
            out.append("Kaunsi Page post boost karni hai, chuniye.")
    else:
        if not d.image_asset:
            out.append("Ad ki photo chahiye (chaukor ya 4:5, jaise 1080x1080).")
        if not d.text.strip():
            out.append("Ad ka text chahiye.")
        if len(d.text) > LIMITS["text"]:
            out.append(f"Text {LIMITS['text']} akshar se lamba hai.")
        if len(d.headline) > LIMITS["headline"]:
            out.append(f"Headline {LIMITS['headline']} akshar tak rakhiye (phone par kat jaati hai).")
        if len(d.description) > LIMITS["description"]:
            out.append(f"Description {LIMITS['description']} akshar tak.")
    if d.goal == "website" and not re.match(r"^https://[^\s/]+\.[^\s]+", d.link or ""):
        out.append("Website ka address (https://...) chahiye.")
    if d.platforms not in ("both", "facebook", "instagram"):
        out.append("Kahan dikhana hai: dono / sirf Facebook / sirf Instagram.")
    if d.goal == "instagram" and d.platforms == "facebook":
        out.append("Instagram chats wala ad Instagram par hi chalega.")
    if not (13 <= d.age_min <= d.age_max <= 65) or d.age_min < 18:
        out.append("Umar 18 se 65 ke beech.")
    if d.gender not in ("all", "men", "women"):
        out.append("Gender: all / men / women.")
    if d.special and d.special not in SPECIAL:
        out.append("Special ad category: HOUSING / EMPLOYMENT / FINANCIAL_PRODUCTS_SERVICES ya khaali.")
    if not (1 <= int(d.radius_km or 0) <= 80):
        out.append("Sheher ke aas-paas 1 se 80 km.")
    if not (1 <= int(d.daily or 0) <= _cap()):
        out.append(f"Roz ka budget 1 se {_cap()} ke beech rakhiye (Hoola ki seema).")
    if not (1 <= int(d.days or 0) <= 30):
        out.append("Kitne din chalana hai: 1 se 30.")
    words = " ".join([d.text, d.headline, d.description])
    out += banned(words)
    if financial(words):
        out.append("Paisa / loan / investment wala ad: Meta ki financial services category aur SEBI niyam pehle; Hoola aisa ad nahi banata.")
    return out


def _view(tenant: str, d: MetaAdDraft) -> dict[str, Any]:
    page = _page_of(tenant, d.page_id) or {}
    return {"id": d.id, "goal": d.goal, "goal_label": GOAL_LABEL.get(d.goal, d.goal), "page_id": d.page_id,
            "page": page.get("name", ""), "ig": page.get("ig", ""), "post_id": d.post_id, "image_asset": d.image_asset,
            "text": d.text, "headline": d.headline, "description": d.description, "link": d.link, "platforms": d.platforms,
            "cities": _j(d.cities, []), "radius_km": d.radius_km, "age_min": d.age_min, "age_max": d.age_max,
            "gender": d.gender, "special": d.special, "daily": d.daily, "days": d.days, "total": d.daily * d.days,
            "status": d.status, "campaign_id": d.campaign_id, "ad_id": d.ad_id, "stop_on": d.stop_on, "error": d.error,
            "problems": draft_problems(tenant, d) if d.status in EDITABLE else []}


def _apply(d: MetaAdDraft, kw: dict[str, Any]) -> None:
    for f, n in (("goal", 12), ("page_id", 30), ("post_id", 60), ("image_asset", 40), ("headline", 120),
                 ("description", 120), ("link", 600), ("platforms", 12), ("gender", 8), ("special", 40)):
        if kw.get(f) is not None:
            setattr(d, f, str(kw[f]).strip()[:n])
    if kw.get("text") is not None:
        d.text = str(kw["text"]).strip()[:2000]
    if isinstance(kw.get("cities"), list):
        d.cities = json.dumps([str(c).strip()[:60] for c in kw["cities"] if str(c).strip()][:10], ensure_ascii=False)
    for f in ("daily", "days", "radius_km", "age_min", "age_max"):
        if kw.get(f) is not None:
            setattr(d, f, int(kw[f]))
    if d.post_id and "_" not in d.post_id and d.page_id:
        d.post_id = f"{d.page_id}_{d.post_id}"


def new_draft(tenant: str, goal: str = "whatsapp", **kw: Any) -> dict[str, Any]:
    """A draft pre-filled from her Social Desk / Ads desk facts (all editable). Nothing reaches Meta."""
    from ..social.desk import SocialDesk
    ensure_tables()
    with session() as s:
        r = A._row(s, tenant)
        page, biz, offer = r.meta_page, r.business, r.offer
        d0 = s.get(SocialDesk, tenant)
        prof = _j(d0.profile, {}) if d0 is not None else {}
    biz = biz or str(prof.get("business") or "")
    city = str(prof.get("city") or "")
    sells = (offer or str(prof.get("sells") or "")).strip()
    ask = {"whatsapp": "WhatsApp par message kijiye", "messenger": "Message kijiye", "instagram": "DM kijiye",
           "website": "Abhi dekhiye", "boost": ""}.get(goal, "")
    text = (f"{biz}" + (f", {city}" if city else "") + (f": {sells}" if sells else "") + (f". {ask}." if ask else "")).strip(" :.,")
    d = MetaAdDraft(tenant_id=tenant, goal=goal if goal in GOALS else "whatsapp", page_id=page,
                    text=text[:LIMITS["text"]], headline=(sells.split(",")[0].strip() or biz)[:LIMITS["headline"]],
                    link=str(prof.get("website") or ""), cities=json.dumps([city] if city else [], ensure_ascii=False))
    _apply(d, kw)
    with session() as s:
        s.add(d)
        s.flush()
        return _view(tenant, d)


def set_draft(tenant: str, did: str, **kw: Any) -> dict[str, Any]:
    with session() as s:
        d = s.get(MetaAdDraft, did)
        if d is None or d.tenant_id != tenant:
            raise MetaAdsError("Yeh ad draft nahi mila.")
        if d.status not in EDITABLE:
            raise MetaAdsError("Yeh ad Meta mein ban chuka; badlav Ads Manager mein kijiye ya naya draft banaiye.")
        _apply(d, kw)
        d.status, d.error = "draft", ""
        return _view(tenant, d)


def drafts(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [_view(tenant, d) for d in s.scalars(select(MetaAdDraft).where(MetaAdDraft.tenant_id == tenant)
                                                     .order_by(MetaAdDraft.created_at.desc())).all()[:20]]


# ---------------------------------------------------------------- the Meta objects (one goal -> one recipe)
RECIPE = {   # objective, optimization goal, destination, call to action, the link Meta's own docs use for chat ads
    "whatsapp": ("OUTCOME_ENGAGEMENT", "CONVERSATIONS", "WHATSAPP", "WHATSAPP_MESSAGE", "https://api.whatsapp.com/send"),
    "messenger": ("OUTCOME_ENGAGEMENT", "CONVERSATIONS", "MESSENGER", "MESSAGE_PAGE", "https://fb.com/messenger_doc/"),
    "instagram": ("OUTCOME_ENGAGEMENT", "CONVERSATIONS", "INSTAGRAM_DIRECT", "INSTAGRAM_MESSAGE", "https://www.instagram.com/"),
    "website": ("OUTCOME_TRAFFIC", "LINK_CLICKS", "WEBSITE", "LEARN_MORE", ""),
    "boost": ("OUTCOME_ENGAGEMENT", "POST_ENGAGEMENT", "ON_POST", "", ""),
}
APP_DEST = {"whatsapp": "WHATSAPP", "messenger": "MESSENGER", "instagram": "INSTAGRAM_DIRECT"}


def _cities(token: str, names: list[str], km: int) -> list[dict[str, Any]]:
    out = []
    for n in names[:10]:
        js = _g("GET", "search", token, {"type": "adgeolocation", "location_types": ["city"], "country_code": "IN", "q": n, "limit": 1})
        hit = (js.get("data") or [None])[0]
        if not hit or not hit.get("key"):
            raise MetaAdsError(f"Meta ko '{n}' sheher nahi mila; naam English mein likhiye (jaise Akola).")
        out.append({"key": str(hit["key"]), "radius": int(km), "distance_unit": "kilometer"})
    return out


def _targeting(d: MetaAdDraft, cities: list[dict[str, Any]]) -> dict[str, Any]:
    t: dict[str, Any] = {"geo_locations": {"cities": cities} if cities else {"countries": ["IN"]}}
    custom = d.age_min != 18 or d.age_max != 65 or d.gender != "all"
    if d.special:                                     # Meta does not allow age / gender choices in these categories
        custom = False
    elif custom:
        t["age_min"], t["age_max"] = d.age_min, d.age_max
        if d.gender != "all":
            t["genders"] = [1 if d.gender == "men" else 2]
    t["targeting_automation"] = {"advantage_audience": 0 if custom else 1}
    plats = {"facebook": ["facebook"], "instagram": ["instagram"]}.get("instagram" if d.goal == "instagram" else d.platforms)
    if plats:
        t["publisher_platforms"] = plats
    return t


def _campaign(d: MetaAdDraft, name: str) -> dict[str, Any]:
    return {"name": name, "objective": RECIPE[d.goal][0], "status": "PAUSED",
            "special_ad_categories": [d.special] if d.special else [], "is_adset_budget_sharing_enabled": False}


def _creative(tenant: str, d: MetaAdDraft, acct: str, token: str, name: str) -> dict[str, Any]:
    if d.goal == "boost":
        return {"name": name, "object_story_id": d.post_id}
    from ..social.publish import SocialAsset
    with session() as s:
        a = s.get(SocialAsset, d.image_asset)
        if a is None or a.tenant_id != tenant or a.kind != "image":
            raise MetaAdsError("Ad ki photo nahi mili; dobara jodiye.")
        data = Path(a.path).read_bytes()
    up = _g("POST", f"{acct}/adimages", token, {"bytes": base64.b64encode(data).decode()})
    img = next(iter((up.get("images") or {}).values()), {})
    if not img.get("hash"):
        raise MetaAdsError("Meta ne photo nahi li; doosri photo try kijiye.")
    goal = d.goal
    link = d.link if goal == "website" else RECIPE[goal][4]
    cta: dict[str, Any] = {"type": RECIPE[goal][3]}
    cta["value"] = {"link": d.link} if goal == "website" else {"app_destination": APP_DEST[goal]}
    ld = {"message": d.text, "link": link, "image_hash": img["hash"], "call_to_action": cta}
    if d.headline:
        ld["name"] = d.headline
    if d.description:
        ld["description"] = d.description
    spec: dict[str, Any] = {"page_id": d.page_id, "link_data": ld}
    ig = (_page_of(tenant, d.page_id) or {}).get("ig_id")
    if ig and d.platforms != "facebook":
        spec["instagram_user_id"] = ig
    return {"name": name, "object_story_spec": spec}


def _load(tenant: str, did: str) -> MetaAdDraft:
    with session() as s:
        d = s.get(MetaAdDraft, did)
        if d is None or d.tenant_id != tenant:
            raise MetaAdsError("Yeh ad draft nahi mila.")
        s.expunge(d)
    return d


def _ready(tenant: str, did: str) -> MetaAdDraft:
    d = _load(tenant, did)
    if d.status not in EDITABLE:
        raise MetaAdsError("Yeh ad pehle hi Meta mein ban chuka.")
    bad = draft_problems(tenant, d)
    if bad:
        raise MetaAdsError(" ".join(bad))
    return d


def _mark(tenant: str, did: str, **kw: Any) -> dict[str, Any]:
    with session() as s:
        d = s.get(MetaAdDraft, did)
        for k, v in kw.items():
            setattr(d, k, v)
        return _view(tenant, d)


def check(tenant: str, did: str) -> dict[str, Any]:
    """Free: Meta checks the campaign (validate_only) and the cities are looked up - nothing is created, nothing spends."""
    d = _ready(tenant, did)
    acct, tok, _cur, _page = _ctx(tenant)
    try:
        _cities(tok, _j(d.cities, []), d.radius_km)
        _g("POST", f"{acct}/campaigns", tok, {**_campaign(d, "Hoola check"), "execution_options": ["validate_only"]})
    except MetaAdsError as e:
        _mark(tenant, did, status="failed", error=str(e)[:600])
        raise
    return _mark(tenant, did, status="checked", error="")


def create(tenant: str, did: str) -> dict[str, Any]:
    """Her tap: campaign, ad set and ad are made in HER ad account, all PAUSED (nothing spends until she taps Start)."""
    d = _ready(tenant, did)
    acct, tok, _cur, _page = _ctx(tenant)
    stamp = now().strftime("%Y-%m-%d %H:%M")
    name = f"Hoola - {GOAL_LABEL[d.goal]} - {stamp}"
    made: dict[str, str] = {}
    try:
        cities = _cities(tok, _j(d.cities, []), d.radius_km)
        made["campaign_id"] = str(_g("POST", f"{acct}/campaigns", tok, _campaign(d, name)).get("id") or "")
        objective, opt, dest, _cta, _link = RECIPE[d.goal]
        adset = {"name": name + " ad set", "campaign_id": made["campaign_id"], "status": "PAUSED",
                 "daily_budget": int(d.daily) * 100,                 # minor units (paise for INR), Meta's rule
                 "billing_event": "IMPRESSIONS", "optimization_goal": opt, "destination_type": dest,
                 "bid_strategy": "LOWEST_COST_WITHOUT_CAP", "targeting": _targeting(d, cities)}
        if d.goal in APP_DEST:
            adset["promoted_object"] = {"page_id": d.page_id}
        made["adset_id"] = str(_g("POST", f"{acct}/adsets", tok, adset).get("id") or "")
        cr = _g("POST", f"{acct}/adcreatives", tok, _creative(tenant, d, acct, tok, name + " creative"))
        made["ad_id"] = str(_g("POST", f"{acct}/ads", tok, {"name": name + " ad", "adset_id": made["adset_id"],
                                                            "creative": {"creative_id": str(cr.get("id") or "")},
                                                            "status": "PAUSED"}).get("id") or "")
    except MetaAdsError as e:
        left = f" Ek adhoora, PAUSED campaign '{name}' Ads Manager mein reh gaya - wahan delete kar sakti hain." if made.get("campaign_id") else ""
        _mark(tenant, did, status="failed", error=(str(e) + left)[:600], **made)
        raise MetaAdsError(str(e) + left)
    return _mark(tenant, did, status="created", error="", **made)


def start(tenant: str, did: str, confirm: bool = False) -> dict[str, Any]:
    """Her tap after a confirm: Meta may now spend up to the daily budget; Meta itself stops the ad set after her days."""
    from ..social.desk import _local
    if not confirm:
        raise MetaAdsError("Start karne se pehle haan chahiye: is ad par roz ka budget kharch hoga.")
    d = _load(tenant, did)
    if d.status not in ("created", "paused") or not (d.campaign_id and d.adset_id and d.ad_id):
        raise MetaAdsError("Pehle ad ko Meta mein (paused) banaiye.")
    if int(d.daily) > _cap():
        raise MetaAdsError(f"Roz ka budget Hoola ki seema ({_cap()}) se zyada hai.")
    _acct, tok, _cur, _page = _ctx(tenant)
    end = datetime.now(timezone.utc) + timedelta(days=max(1, int(d.days)))
    _g("POST", d.adset_id, tok, {"end_time": end.strftime("%Y-%m-%dT%H:%M:%S+0000")})
    for oid in (d.ad_id, d.adset_id, d.campaign_id):          # the campaign last: nothing runs half-set
        _g("POST", oid, tok, {"status": "ACTIVE"})
    stop_on = (_local(tenant).date() + timedelta(days=max(1, int(d.days)) - 1)).isoformat()
    return _mark(tenant, did, status="running", started_at=now(), stop_on=stop_on, error="")


def pause(tenant: str, did: str, ended: bool = False) -> dict[str, Any]:
    d = _load(tenant, did)
    if not d.campaign_id:
        raise MetaAdsError("Yeh ad Meta mein bana hi nahi.")
    _acct, tok, _cur, _page = _ctx(tenant)
    _g("POST", d.campaign_id, tok, {"status": "PAUSED"})
    return _mark(tenant, did, status="ended" if ended else "paused")


def daily_watch(tenant: str) -> dict[str, Any]:
    """Every day: ads past their last day are paused (Meta's end time already stopped them) and she is told once."""
    from ..social.desk import SocialEvent, _local
    ensure_tables()
    today = _local(tenant).date().isoformat()
    out = {"ended": 0}
    with session() as s:
        due = [d.id for d in s.scalars(select(MetaAdDraft).where(MetaAdDraft.tenant_id == tenant, MetaAdDraft.status == "running")).all()
               if d.stop_on and d.stop_on < today]
    for did in due:
        try:
            v = pause(tenant, did, ended=True)
            out["ended"] += 1
            with session() as s:
                s.add(SocialEvent(tenant_id=tenant, kind="note", level="info",
                                  text=f"Facebook / Instagram ad ({v['goal_label']}) finished its {v['days']} days and is paused."))
        except (MetaAdsError, A.AdsError) as e:
            log.info("meta auto-pause failed: %s", e)
    return out


def linked(tenant: str) -> bool:
    with session() as s:
        r = s.get(A.AdsSettings, tenant)
        return bool(r is not None and r.meta_token)


def page_posts(tenant: str, limit: int = 15) -> list[dict[str, Any]]:
    """Her Page's recent posts (for Boost), read with the ads login."""
    _acct, tok, _cur, page = _ctx(tenant)
    if not page:
        return []
    js = _g("GET", f"{page}/posts", tok, {"fields": "id,message,created_time,permalink_url", "limit": min(limit, 25)})
    return [{"id": str(p.get("id") or ""), "text": str(p.get("message") or "")[:120], "date": str(p.get("created_time") or "")[:10],
             "link": str(p.get("permalink_url") or "")} for p in js.get("data") or [] if p.get("id")]


def view(tenant: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        r = s.get(A.AdsSettings, tenant)
        acc = None
        if r is not None and r.meta_token:
            exp = as_utc(r.meta_expires)
            acc = {"via": r.meta_via or "token", "account": r.meta_account, "name": r.meta_name, "currency": r.meta_currency,
                   "page": r.meta_page, "accounts": _j(r.meta_accounts, []), "pages": _j(r.meta_pages, []),
                   "expires": exp.isoformat() if exp else "",
                   "renew": bool(exp and exp < now() + timedelta(days=7))}
    return {"configured": configured(), "account": acc, "drafts": drafts(tenant) if acc else [], "cap": _cap(),
            "goals": GOAL_LABEL}
