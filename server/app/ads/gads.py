"""v0.401 YOUTUBE ADS (plan Y2): her own Google Ads account through the official Google Ads API (REST, v26 - field names from
Google's own AddDemandGenCampaign example). Hoola never moves money on its own:
  1. Connect: Google sign-in with the adwords permission (her account, refresh token sealed); she picks which ad account.
  2. Read: her YouTube campaigns (VIDEO + DEMAND_GEN) day by day -> the Ads desk's own report rows (platform google), so
     the existing money-leak checks, budget suggestions and weekly notes work on YouTube ads too.
  3. Draft: a YouTube video ad from one of HER videos (a boost-worthy post, or any channel video): a Demand Gen campaign
     on YouTube only (in-stream, in-feed, Shorts), daily budget + days, India + language, headlines / long headline /
     descriptions / business name from her facts, her logo; ASCI / banned-category checks (the Ads desk's rules) and a
     daily cap (GADS_MAX_DAILY). Kept in Hoola until she acts.
  4. Check with Google (free, validateOnly) -> Create in her account PAUSED (her tap; nothing spends while paused).
  5. Start = her tap after a confirm (this is when money can move); Pause any time; a campaign past its last day is
     paused by Hoola and she is told. Older in-stream "Video" campaigns cannot be created through the API - for those
     Hoola gives the Google Ads steps.
v0.425 GOOGLE ADS 2 (ad plan A2): the same link now makes the two Google campaigns an Indian shop actually buys -
  * Search - her words on Google search: keywords (with Google's own Keyword Planner ideas: monthly searches, competition,
    top-of-page bid range for HER places), not-these words, a responsive search ad (3-15 headlines of 30, 2-4
    descriptions of 90, two display paths), India or her cities, Maximize clicks.
  * Performance Max - one campaign over Search, YouTube, Display, Discover, Gmail and Maps: her photo cut by Hoola to
    Google's two shapes (1.91:1 + 1:1), logo, texts; Maximize conversions (Google needs a conversion goal in her
    account - the check says so plainly). Local campaigns were folded into Performance Max by Google in 2022, so shops
    reach Maps through this (her Business Profile is linked once in Google Ads; Hoola gives the steps).
  Same rails as YouTube: draft in Hoola -> Google check (validateOnly, free) -> Create PAUSED -> Start only on her confirm ->
  paused after its days. The read now covers every campaign type, and Search's search terms go to the Ads desk, whose
  money-leak check already finds terms that spend without converting.
Needs on the server: GOOGLE_ADS_DEVELOPER_TOKEN (Google Ads API Center; test accounts work with a test-access token,
real accounts need Basic access) and the adwords scope on Hoola's Google OAuth consent screen."""
from __future__ import annotations

import base64
import csv
import io
import json
import logging
import re
import secrets
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, MailLinkState, as_utc, new_id, now, session

log = logging.getLogger("santosh.ads.gads")
SCOPE = "https://www.googleapis.com/auth/adwords"
API = "https://googleads.googleapis.com"
INDIA = "geoTargetConstants/2356"
LANGS = {"en": "languageConstants/1000", "hi": "languageConstants/1023", "mr": "languageConstants/1034",
         "gu": "languageConstants/1029", "ta": "languageConstants/1130", "te": "languageConstants/1131",
         "kn": "languageConstants/1086", "ml": "languageConstants/1098", "bn": "languageConstants/1056",
         "pa": "languageConstants/1110"}
LIMITS = {"headline": 40, "long_headline": 90, "description": 90, "business": 25, "headlines": (1, 5), "descriptions": (1, 5)}
KINDS = ("youtube", "search", "pmax")
KIND_LABEL = {"youtube": "YouTube ad", "search": "Search ad", "pmax": "Performance Max"}
# v0.425 Google's own limits for the two new campaign kinds (responsive search ad / Performance Max asset group)
LIM = {"search": {"headline": 30, "headlines": (3, 15), "description": 90, "descriptions": (2, 4), "path": 15,
                  "keywords": (1, 20), "keyword": 80, "negatives": 30},
       "pmax": {"headline": 30, "headlines": (3, 5), "long_headline": 90, "description": 90, "descriptions": (2, 5),
                "short_description": 60, "business": 25, "images": (1, 5)}}
_http: httpx.Client | None = None


class GAdsError(Exception):
    pass


def set_http(c: httpx.Client | None) -> None:
    global _http
    _http = c


class GAdsAccount(Base):
    """Her Google Ads sign-in (refresh token sealed) and the ad account she chose."""
    __tablename__ = "gads_accounts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gad"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    email: Mapped[str] = mapped_column(String(320), default="")
    refresh_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    customers: Mapped[str] = mapped_column(Text, default="[]")          # [{id, name, currency, manager, test}]
    customer_id: Mapped[str] = mapped_column(String(20), default="")      # the ad account she picked
    currency: Mapped[str] = mapped_column(String(8), default="")
    status: Mapped[str] = mapped_column(String(12), default="ok")
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_read: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GAdsDraft(Base):
    """A YouTube ad she is shaping. Lives only in Hoola until she taps Create (paused in Google) and Start."""
    __tablename__ = "gads_drafts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gdr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    video_id: Mapped[str] = mapped_column(String(20), default="")
    video_title: Mapped[str] = mapped_column(String(200), default="")
    daily: Mapped[int] = mapped_column(Integer, default=300)              # whole units of her account currency a day
    days: Mapped[int] = mapped_column(Integer, default=3)
    final_url: Mapped[str] = mapped_column(Text, default="")
    business: Mapped[str] = mapped_column(String(40), default="")
    headlines: Mapped[str] = mapped_column(Text, default="[]")
    long_headline: Mapped[str] = mapped_column(String(120), default="")
    descriptions: Mapped[str] = mapped_column(Text, default="[]")
    languages: Mapped[str] = mapped_column(Text, default='["hi", "en"]')
    logo_asset: Mapped[str] = mapped_column(String(40), default="")       # social publish SocialAsset id (square image)
    status: Mapped[str] = mapped_column(String(12), default="draft")      # draft | checked | created | running | paused | ended | failed
    campaign: Mapped[str] = mapped_column(String(120), default="")        # customers/<id>/campaigns/<id>
    kind: Mapped[str] = mapped_column(String(10), default="youtube")      # v0.425 youtube | search | pmax
    keywords: Mapped[str] = mapped_column(Text, default="[]")             # search: phrase-match keywords
    negatives: Mapped[str] = mapped_column(Text, default="[]")            # search: words she does not want to pay for
    paths: Mapped[str] = mapped_column(Text, default="[]")                # search: display path 1 / 2
    cities: Mapped[str] = mapped_column(Text, default="[]")               # search / pmax: names; empty = all India
    images: Mapped[str] = mapped_column(Text, default="[]")               # pmax: SocialAsset ids (Hoola cuts the shapes)
    stop_on: Mapped[str] = mapped_column(String(10), default="")          # last day it may run (her local date)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_READY: set[int] = set()


def ensure_tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for t in (GAdsAccount, GAdsDraft):
            t.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except ValueError:
        return default


def configured() -> bool:
    """Google sunset developer tokens on 9 Sep 2026: access levels now belong to the Google Cloud project that owns the
    OAuth client (Google Ads API Overview page). The token is optional (sent when set, ignored by Google)."""
    st = get_settings()
    return bool(st.google_oauth_client_id and st.google_oauth_client_secret and st.public_base_url)


# ---------------------------------------------------------------- connecting (Google sign-in with adwords)
def is_link_state(state: str) -> bool:
    return (state or "").startswith("gad_")


def connect_url(tenant: str) -> str:
    from .. import accounts as acc
    from ..mailbox import accounts as mail_acc
    if not configured():
        raise GAdsError("Google sign-in is not set up on the server yet (GOOGLE_OAUTH_CLIENT_ID / SECRET, PUBLIC_BASE_URL).")
    st = get_settings()
    state = "gad_" + secrets.token_urlsafe(24)
    ensure_tables()
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="gads"))
    q = {"client_id": st.google_oauth_client_id, "redirect_uri": acc._redirect_uri(), "response_type": "code",
         "scope": "openid email " + SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
         "include_granted_scopes": "true"}
    return mail_acc.GOOGLE_AUTH + "?" + urlencode(q)


def finish_link(code: str, state: str) -> dict[str, Any]:
    from .. import accounts as acc
    from ..mailbox import accounts as mail_acc
    st = get_settings()
    ensure_tables()
    with session() as s:
        row = s.get(MailLinkState, state)
        if row is None or row.provider != "gads" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise GAdsError("This link has expired. Tap 'Connect Google Ads' again.")
        tenant = row.tenant_id
        s.delete(row)
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "redirect_uri": acc._redirect_uri(), "grant_type": "authorization_code"})
        if SCOPE not in (tok.get("scope") or "").split():
            raise GAdsError("Google Ads permission was not given. When you connect again, allow Google Ads.")
        info = mail_acc._get("https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
    except mail_acc.MailError as e:
        raise GAdsError(str(e))
    if not tok.get("refresh_token"):
        raise GAdsError("Google did not give a refresh token; connect again.")
    with session() as s:
        for old in s.scalars(select(GAdsAccount).where(GAdsAccount.tenant_id == tenant)).all():
            s.delete(old)
        a = GAdsAccount(tenant_id=tenant, email=str(info.get("email") or "").lower()[:320],
                        refresh_enc=acc.encrypt(tok["refresh_token"]), access_enc=acc.encrypt(tok["access_token"]),
                        expiry=now() + timedelta(seconds=int(tok.get("expires_in", 3600))))
        s.add(a)
    custs = list_customers(tenant)
    usable = [c for c in custs if not c.get("manager")]
    if len(usable) == 1:
        choose(tenant, usable[0]["id"])
    return {"email": str(info.get("email") or ""), "accounts": [c["name"] or c["id"] for c in custs]}


def _token(tenant: str, force: bool = False) -> tuple[str, GAdsAccount]:
    from .. import accounts as acc
    from ..mailbox import accounts as mail_acc
    st = get_settings()
    ensure_tables()
    with session() as s:
        a = s.scalars(select(GAdsAccount).where(GAdsAccount.tenant_id == tenant)).first()
        if a is None:
            raise GAdsError("Google Ads is not connected yet: tap 'Connect Google Ads' on the Social Desk.")
        s.expunge(a)
    exp = as_utc(a.expiry)
    if not force and a.access_enc and exp and exp > now() + timedelta(seconds=90):
        return acc.decrypt(a.access_enc) or "", a
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"client_id": st.google_oauth_client_id, "client_secret": st.google_oauth_client_secret,
                                                     "refresh_token": acc.decrypt(a.refresh_enc) or "", "grant_type": "refresh_token"})
    except mail_acc.MailError as e:
        with session() as s:
            r = s.get(GAdsAccount, a.id)
            r.status, r.last_error = "expired", str(e)[:300]
        raise GAdsError("The Google Ads login has expired: tap 'Connect Google Ads' again.")
    with session() as s:
        r = s.get(GAdsAccount, a.id)
        r.access_enc = acc.encrypt(tok["access_token"])
        r.expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        r.status, r.last_error = "ok", ""
    return tok["access_token"], a


def _call(tenant: str, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
    st = get_settings()
    for attempt in (0, 1):
        token, a = _token(tenant, force=attempt == 1)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if st.google_ads_developer_token:                 # optional since Google's 9 Sep 2026 change
            headers["developer-token"] = st.google_ads_developer_token
        if st.google_ads_login_customer_id:
            headers["login-customer-id"] = re.sub(r"\D", "", st.google_ads_login_customer_id)
        c = _http or httpx.Client(timeout=60)
        try:
            r = c.request(method, f"{API}/{st.google_ads_api_version}/{path}", json=body, headers=headers)
        except httpx.HTTPError as e:
            raise GAdsError(f"Could not reach Google Ads ({type(e).__name__}).")
        finally:
            if _http is None:
                c.close()
        if r.status_code == 401 and attempt == 0:
            continue
        if r.status_code >= 400:
            raise GAdsError(_error_text(r))
        return r.json() if r.content else {}
    raise GAdsError("Google Ads did not accept the login.")


def _error_text(r: httpx.Response) -> str:
    try:
        js = r.json()
        if isinstance(js, list):
            js = js[0]
        err = js.get("error") or {}
        msgs = []
        for d in err.get("details") or []:
            for e in d.get("errors") or []:
                m = e.get("message") or ""
                code = ",".join(f"{k}={v}" for k, v in (e.get("errorCode") or {}).items())
                if ("DEVELOPER_TOKEN_NOT_APPROVED" in code or "not approved" in m.lower() or "test account" in m.lower()
                        or "access level" in m.lower()):
                    return ("Google Ads: the API access of Hoola's Google Cloud project is for test accounts only for now "
                            "(Explorer / Basic access approval pending). It will work on a real account once Google approves it.")
                if "CONVERSION" in code.upper() and ("MAXIMIZE" in code.upper() or "TRACKING" in code.upper() or "NO_CONVERSION" in code.upper()):
                    return ("Google Ads: Performance Max first needs a conversion goal (Google Ads > Goals > Conversions: "
                            "call, form, WhatsApp click or purchase). Create one, then Check again.")
                msgs.append(m + (f" ({code})" if code else ""))
        return "Google Ads: " + ("; ".join(msgs)[:400] if msgs else str(err.get("message") or r.text[:300]))
    except ValueError:
        return f"Google Ads: {r.text[:300]}"


def search(tenant: str, cid: str, query: str) -> list[dict[str, Any]]:
    out, token = [], None
    for _ in range(20):
        body = {"query": query, **({"pageToken": token} if token else {})}
        js = _call(tenant, "POST", f"customers/{cid}/googleAds:search", body)
        out += js.get("results") or []
        token = js.get("nextPageToken")
        if not token:
            break
    return out


def list_customers(tenant: str) -> list[dict[str, Any]]:
    js = _call(tenant, "GET", "customers:listAccessibleCustomers")
    out = []
    for rn in (js.get("resourceNames") or [])[:20]:
        cid = rn.split("/")[-1]
        try:
            row = (search(tenant, cid, "SELECT customer.id, customer.descriptive_name, customer.currency_code, "
                                       "customer.manager, customer.test_account FROM customer LIMIT 1") or [{}])[0].get("customer") or {}
        except GAdsError as e:
            log.info("customer %s unreadable: %s", cid, e)
            continue
        out.append({"id": cid, "name": str(row.get("descriptiveName") or ""), "currency": str(row.get("currencyCode") or ""),
                    "manager": bool(row.get("manager")), "test": bool(row.get("testAccount"))})
    with session() as s:
        a = s.scalars(select(GAdsAccount).where(GAdsAccount.tenant_id == tenant)).first()
        if a is not None:
            a.customers = json.dumps(out)
    return out


def choose(tenant: str, customer_id: str) -> dict[str, Any]:
    cid = re.sub(r"\D", "", str(customer_id or ""))
    with session() as s:
        a = s.scalars(select(GAdsAccount).where(GAdsAccount.tenant_id == tenant)).first()
        if a is None:
            raise GAdsError("Google Ads is not connected yet.")
        c = next((x for x in _j(a.customers, []) if x["id"] == cid), None)
        if c is None:
            raise GAdsError("This ad account was not found in your login.")
        if c.get("manager"):
            raise GAdsError("This is a manager (MCC) account; choose the account the ads run in.")
        a.customer_id, a.currency = cid, c.get("currency") or ""
    return {"customer_id": cid, "currency": c.get("currency") or ""}


def _cid(tenant: str) -> tuple[str, str]:
    with session() as s:
        a = s.scalars(select(GAdsAccount).where(GAdsAccount.tenant_id == tenant)).first()
        if a is None:
            raise GAdsError("Google Ads is not connected yet: tap 'Connect Google Ads'.")
        if not a.customer_id:
            raise GAdsError("First choose which Google Ads account the YouTube ads will run in.")
        return a.customer_id, a.currency


# ---------------------------------------------------------------- reading her YouTube ads
_METRIC_SETS = ("metrics.video_trueview_views", "metrics.video_views", "")


def read(tenant: str, days: int = 30) -> dict[str, Any]:
    """Her Google campaigns by day (v0.425: every type - YouTube / Demand Gen, Search, Performance Max, Display) -> the Ads
    desk's report rows (platform google), plus Search's search terms as term rows (the desk finds terms that spend with
    no result)."""
    from . import service as ads
    cid, cur = _cid(tenant)
    rows, err = None, ""
    for views in _METRIC_SETS:
        q = ("SELECT segments.date, campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, "
             "campaign_budget.amount_micros, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions"
             + (f", {views}" if views else "") + " FROM campaign WHERE campaign.advertising_channel_type IN ('VIDEO', 'DEMAND_GEN', 'SEARCH', 'PERFORMANCE_MAX', "
             "'DISPLAY') AND campaign.status != 'REMOVED' "
             f"AND segments.date DURING LAST_{30 if days >= 30 else 14 if days >= 14 else 7}_DAYS")
        try:
            rows = search(tenant, cid, q)
            break
        except GAdsError as e:
            err = str(e)
            if "UNRECOGNIZED_FIELD" not in err and "unrecognized field" not in err.lower() and "video_" not in err:
                raise
    if rows is None:
        raise GAdsError(err or "No Google Ads report was returned.")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Day", "Campaign", "Status", "Cost", "Impr.", "Clicks", "Conversions", "Budget", "Views"])
    camps: dict[str, dict[str, Any]] = {}
    for r in rows:
        c, m, b = r.get("campaign") or {}, r.get("metrics") or {}, r.get("campaignBudget") or {}
        cost = int(m.get("costMicros") or 0) / 1e6
        views = int(m.get("videoTrueviewViews") or m.get("videoViews") or 0)
        w.writerow([(r.get("segments") or {}).get("date", ""), c.get("name", ""), c.get("status", ""), f"{cost:.2f}",
                    m.get("impressions", 0), m.get("clicks", 0), m.get("conversions", 0),
                    f"{int(b.get('amountMicros') or 0) / 1e6:.0f}", views])
        k = str(c.get("id") or c.get("name"))
        agg = camps.setdefault(k, {"name": c.get("name", ""), "status": c.get("status", ""), "type": c.get("advertisingChannelType", ""),
                                   "spend": 0.0, "impressions": 0, "clicks": 0, "views": 0, "conversions": 0.0})
        agg["spend"] += cost
        agg["impressions"] += int(m.get("impressions") or 0)
        agg["clicks"] += int(m.get("clicks") or 0)
        agg["views"] += views
        agg["conversions"] += float(m.get("conversions") or 0)
    report = None
    if rows:
        try:
            report = ads.import_report(tenant, data=out.getvalue().encode(), name="google_ads_campaigns.csv", platform="google")
        except Exception as e:   # noqa: BLE001 - the numbers still show here
            log.info("ads desk import skipped: %s", e)
    terms = 0
    if any((r.get("campaign") or {}).get("advertisingChannelType") == "SEARCH" for r in rows):
        try:
            terms = _read_terms(tenant, cid, days)
        except GAdsError as e:
            log.info("search terms read skipped: %s", e)
    with session() as s:
        a = s.scalars(select(GAdsAccount).where(GAdsAccount.tenant_id == tenant)).first()
        a.last_read = now()
    for v in camps.values():
        v["spend"] = round(v["spend"], 2)
        v["cpv"] = round(v["spend"] / v["views"], 2) if v["views"] else None
        v["ctr"] = round(100 * v["clicks"] / v["impressions"], 2) if v["impressions"] else None
    return {"currency": cur, "campaigns": sorted(camps.values(), key=lambda x: -x["spend"]), "rows": len(rows),
            "terms": terms, "ads_desk": (report or {}).get("say", "")}


def _read_terms(tenant: str, cid: str, days: int) -> int:
    """What people actually typed before clicking her Search ads (search_term_view), summed over the window."""
    from . import service as ads
    q = ("SELECT search_term_view.search_term, campaign.name, ad_group.name, metrics.cost_micros, metrics.impressions, "
         "metrics.clicks, metrics.conversions FROM search_term_view "
         f"WHERE segments.date DURING LAST_{30 if days >= 30 else 14 if days >= 14 else 7}_DAYS AND metrics.impressions > 0")
    rows = search(tenant, cid, q)
    agg: dict[tuple, list[float]] = {}
    for r in rows:
        t = (str((r.get("searchTermView") or {}).get("searchTerm") or ""), str((r.get("campaign") or {}).get("name") or ""),
             str((r.get("adGroup") or {}).get("name") or ""))
        m = r.get("metrics") or {}
        v = agg.setdefault(t, [0.0, 0.0, 0.0, 0.0])
        v[0] += int(m.get("costMicros") or 0) / 1e6
        v[1] += int(m.get("impressions") or 0)
        v[2] += int(m.get("clicks") or 0)
        v[3] += float(m.get("conversions") or 0)
    if not agg:
        return 0
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Search term", "Campaign", "Ad group", "Cost", "Impr.", "Clicks", "Conversions"])
    for (term, camp, grp), v in sorted(agg.items(), key=lambda kv: -kv[1][0])[:500]:
        if term:
            w.writerow([term, camp, grp, f"{v[0]:.2f}", int(v[1]), int(v[2]), round(v[3], 2)])
    ads.import_report(tenant, data=out.getvalue().encode(), name="google_search_terms.csv", platform="google")
    return len(agg)


# ---------------------------------------------------------------- drafts (in Hoola only)
def _cap() -> int:
    return int(getattr(get_settings(), "gads_max_daily", 2000) or 2000)


def _kind(d: GAdsDraft) -> str:
    return d.kind if d.kind in KINDS else "youtube"


def _common_problems(d: GAdsDraft, words: list[str]) -> list[str]:
    from .rules import banned, financial
    out = []
    if not re.match(r"^https://[^\s/]+\.[^\s]+", d.final_url or ""):
        out.append("Where the ad should lead: a website / WhatsApp link (https://...) is needed.")
    if not (1 <= int(d.daily or 0) <= _cap()):
        out.append(f"Keep the daily budget between 1 and {_cap()} (Hoola's limit).")
    if not (1 <= int(d.days or 0) <= 30):
        out.append("How many days to run: 1 to 30.")
    text = " ".join(words)
    out += banned(text)
    if financial(text):
        out.append("Money / investment ad: Google's financial services verification and SEBI rules come first; Hoola does not make such ads.")
    return out


def draft_problems(d: GAdsDraft) -> list[str]:
    k = _kind(d)
    hs, ds = _j(d.headlines, []), _j(d.descriptions, [])
    out: list[str] = []
    if k == "search":
        L = LIM["search"]
        kws, negs, paths = _j(d.keywords, []), _j(d.negatives, []), _j(d.paths, [])
        if not (L["headlines"][0] <= len(hs) <= L["headlines"][1]):
            out.append(f"A Search ad needs {L['headlines'][0]} to {L['headlines'][1]} headlines.")
        out += [f"Headline '{h[:20]}' is longer than {L['headline']} characters." for h in hs if len(h) > L["headline"]]
        if not (L["descriptions"][0] <= len(ds) <= L["descriptions"][1]):
            out.append(f"{L['descriptions'][0]} to {L['descriptions'][1]} descriptions are needed.")
        out += [f"A description is longer than {L['description']} characters." for x in ds if len(x) > L["description"]]
        if not (L["keywords"][0] <= len(kws) <= L["keywords"][1]):
            out.append(f"1 to {L['keywords'][1]} keywords are needed (what people type on Google).")
        out += [f"Keyword '{w[:20]}' is too long (up to 10 words / {L['keyword']} characters)." for w in kws
                if len(w) > L["keyword"] or len(w.split()) > 10]
        if len(negs) > L["negatives"]:
            out.append(f"Negative keywords: up to {L['negatives']}.")
        out += [f"Path '{x}' can be up to {L['path']} characters." for x in paths if len(x) > L["path"]]
        return out + _common_problems(d, hs + ds + kws)
    if k == "pmax":
        L = LIM["pmax"]
        if not (L["headlines"][0] <= len(hs) <= L["headlines"][1]):
            out.append(f"Performance Max needs {L['headlines'][0]} to {L['headlines'][1]} headlines.")
        out += [f"Headline '{h[:20]}' is longer than {L['headline']} characters." for h in hs if len(h) > L["headline"]]
        if not d.long_headline or len(d.long_headline) > L["long_headline"]:
            out.append(f"A long headline is needed (up to {L['long_headline']} characters).")
        if not (L["descriptions"][0] <= len(ds) <= L["descriptions"][1]):
            out.append(f"{L['descriptions'][0]} to {L['descriptions'][1]} descriptions are needed.")
        out += [f"A description is longer than {L['description']} characters." for x in ds if len(x) > L["description"]]
        if ds and not any(len(x) <= L["short_description"] for x in ds):
            out.append(f"One description must be {L['short_description']} characters or shorter (Google's rule).")
        if not d.business or len(d.business) > L["business"]:
            out.append(f"The business name is needed (up to {L['business']} characters).")
        if not d.logo_asset:
            out.append("A logo is needed (square picture, for example 1200x1200).")
        if not (L["images"][0] <= len(_j(d.images, [])) <= L["images"][1]):
            out.append("1 to 5 pictures are needed (Hoola crops them to both of Google's sizes).")
        return out + _common_problems(d, hs + ds + [d.long_headline, d.business])
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", d.video_id or ""):
        out.append("Choose a YouTube video (a public / unlisted video of your channel).")
    if not (LIMITS["headlines"][0] <= len(hs) <= LIMITS["headlines"][1]):
        out.append("1 to 5 headlines are needed.")
    out += [f"Headline '{h[:20]}...' is longer than {LIMITS['headline']} characters." for h in hs if len(h) > LIMITS["headline"]]
    if not d.long_headline or len(d.long_headline) > LIMITS["long_headline"]:
        out.append(f"A long headline is needed (up to {LIMITS['long_headline']} characters).")
    if not (LIMITS["descriptions"][0] <= len(ds) <= LIMITS["descriptions"][1]):
        out.append("1 to 5 descriptions are needed.")
    out += [f"A description is longer than {LIMITS['description']} characters." for x in ds if len(x) > LIMITS["description"]]
    if not d.business or len(d.business) > LIMITS["business"]:
        out.append(f"The business name is needed (up to {LIMITS['business']} characters).")
    if not d.logo_asset:
        out.append("A logo is needed (square picture, for example 1200x1200).")
    return out + _common_problems(d, hs + ds + [d.long_headline, d.business])


def _draft_view(d: GAdsDraft) -> dict[str, Any]:
    k = _kind(d)
    title = d.video_title or d.video_id if k == "youtube" else (_j(d.headlines, []) or [KIND_LABEL[k]])[0]
    return {"id": d.id, "kind": k, "kind_label": KIND_LABEL[k], "title": title, "video_id": d.video_id,
            "video_title": d.video_title, "daily": d.daily, "days": d.days,
            "total": d.daily * d.days, "final_url": d.final_url, "business": d.business, "headlines": _j(d.headlines, []),
            "long_headline": d.long_headline, "descriptions": _j(d.descriptions, []), "languages": _j(d.languages, []),
            "keywords": _j(d.keywords, []), "negatives": _j(d.negatives, []), "paths": _j(d.paths, []),
            "cities": _j(d.cities, []), "images": _j(d.images, []),
            "logo_asset": d.logo_asset, "status": d.status, "campaign": d.campaign, "stop_on": d.stop_on, "error": d.error,
            "problems": draft_problems(d) if d.status in ("draft", "checked", "failed") else []}


def _cut(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= n:
        return text
    return (text[:n].rsplit(" ", 1)[0] or text[:n]).strip(" ,.-")


def new_draft(tenant: str, video_id: str = "", kind: str = "youtube", **kw: Any) -> dict[str, Any]:
    """A draft pre-filled from her Social Desk facts (all editable). kind youtube (from one of her videos) | search | pmax."""
    from ..social.desk import SocialDesk, SocialMedia
    ensure_tables()
    kind = kind if kind in KINDS else "youtube"
    vid = str(video_id or "").strip() if kind == "youtube" else ""
    with session() as s:
        d0 = s.get(SocialDesk, tenant)
        prof = _j(d0.profile, {}) if d0 is not None else {}
        m = s.scalars(select(SocialMedia).where(SocialMedia.tenant_id == tenant, SocialMedia.platform == "youtube",
                                                SocialMedia.media_id == vid)).first() if vid else None
        title = (m.caption if m is not None else "") or ""
    biz = str(prof.get("business") or "")[:LIMITS["business"]]
    city = str(prof.get("city") or "")
    items = [x.strip() for x in str(prof.get("sells") or "").split(",") if x.strip()]
    sells = items[0] if items else ""
    if kind == "youtube":
        heads = [h for h in [title[:LIMITS["headline"]], (f"{sells} in {city}" if sells and city else sells)[:LIMITS["headline"]],
                             (f"{biz} - {city}" if city else biz)[:LIMITS["headline"]]] if h][:3]
        descs = [f"{sells or biz} - call or WhatsApp now."[:LIMITS["description"]]]
    else:
        n = LIM[kind]["headline"]
        heads = [h for h in dict.fromkeys(_cut(x, n) for x in [
            biz, f"{sells} in {city}" if sells and city else sells, *(items[1:4]),
            f"Best {sells}" if sells else "", f"{city} - {sells}" if city and sells else "", "Call today"]) if h]
        heads = heads[:LIM[kind]["headlines"][1]]
        descs = [_cut(f"{biz}: {', '.join(items[:3])}" + (f" in {city}" if city else "") + ".", 90),
                 _cut(f"{sells or biz} - call or WhatsApp now.", 60)]
        descs = [x for x in descs if x]
    d = GAdsDraft(tenant_id=tenant, kind=kind, video_id=vid, video_title=title[:200], business=biz,
                  headlines=json.dumps(kw.get("headlines") or heads, ensure_ascii=False),
                  long_headline=str(kw.get("long_headline") or (f"{biz}: {sells}" + (f", {city}" if city else ""))).strip(": ")[:LIMITS["long_headline"]],
                  descriptions=json.dumps(kw.get("descriptions") or descs, ensure_ascii=False),
                  keywords=json.dumps(kw.get("keywords") or ([f"{x} {city}".strip() for x in items[:5]] + items[:5]
                                                             if kind == "search" else []), ensure_ascii=False),
                  cities=json.dumps(kw.get("cities") if isinstance(kw.get("cities"), list) else ([city] if city and kind != "youtube" else []),
                                    ensure_ascii=False),
                  final_url=str(kw.get("final_url") or prof.get("website") or ""),
                  daily=int(kw.get("daily") or 300), days=int(kw.get("days") or (3 if kind == "youtube" else 7)))
    with session() as s:
        s.add(d)
        s.flush()
        return _draft_view(d)


def set_draft(tenant: str, did: str, **kw: Any) -> dict[str, Any]:
    with session() as s:
        d = s.get(GAdsDraft, did)
        if d is None or d.tenant_id != tenant:
            raise GAdsError("Ad draft not found.")
        if d.status not in ("draft", "checked", "failed"):
            raise GAdsError("This ad is already created in Google; change it in Google Ads or make a new draft.")
        for f in ("video_id", "final_url", "business", "long_headline", "logo_asset"):
            if kw.get(f) is not None:
                setattr(d, f, str(kw[f]).strip()[:300])
        caps = {"headlines": 15, "descriptions": 5, "languages": 5, "keywords": 20, "negatives": 30, "paths": 2,
                "cities": 10, "images": 5}
        for f, n in caps.items():
            if isinstance(kw.get(f), list):
                setattr(d, f, json.dumps([str(x).strip() for x in kw[f] if str(x).strip()][:n], ensure_ascii=False))
        for f in ("daily", "days"):
            if kw.get(f) is not None:
                setattr(d, f, int(kw[f]))
        d.status, d.error = "draft", ""
        return _draft_view(d)


def drafts(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [_draft_view(d) for d in s.scalars(select(GAdsDraft).where(GAdsDraft.tenant_id == tenant)
                                                    .order_by(GAdsDraft.created_at.desc())).all()[:20]]


# ---------------------------------------------------------------- v0.425 places + keyword ideas (Google's own services)
def geo_targets(tenant: str, names: list[str]) -> list[str]:
    """Her city names -> Google's geo target constants (GeoTargetConstantService.SuggestGeoTargetConstants, India)."""
    names = [n.strip() for n in names if str(n).strip()][:10]
    if not names:
        return [INDIA]
    js = _call(tenant, "POST", "geoTargetConstants:suggest", {"locale": "en", "countryCode": "IN",
                                                              "locationNames": {"names": names}})
    out, seen = [], set()
    for sug in js.get("geoTargetConstantSuggestions") or []:
        g = sug.get("geoTargetConstant") or {}
        rn, nm = str(g.get("resourceName") or ""), str(sug.get("searchTerm") or g.get("name") or "")
        if rn and nm.lower() not in seen and str(g.get("status") or "ENABLED") == "ENABLED":
            seen.add(nm.lower())
            out.append(rn)
    missing = [n for n in names if n.lower() not in seen]
    if missing and len(out) < len(names):
        raise GAdsError(f"Google could not find these places: {', '.join(missing)} (write the name in English, for example Akola).")
    return out


def keyword_ideas(tenant: str, seeds: list[str] | None = None, url: str = "", cities: list[str] | None = None,
                  lang: str = "en") -> dict[str, Any]:
    """Google Keyword Planner ideas for HER places (KeywordPlanIdeaService.GenerateKeywordIdeas): what people search,
    how often a month, competition and the top-of-page bid range. Read-only, free."""
    cid, cur = _cid(tenant)
    seeds = [s.strip() for s in (seeds or []) if str(s).strip()][:10]
    if not seeds and not url:
        raise GAdsError("Give a few words or a website - Google bases its ideas on them.")
    body: dict[str, Any] = {"language": LANGS.get(lang, LANGS["en"]), "geoTargetConstants": geo_targets(tenant, cities or []),
                            "keywordPlanNetwork": "GOOGLE_SEARCH", "includeAdultKeywords": False, "pageSize": 50}
    if seeds and url:
        body["keywordAndUrlSeed"] = {"url": url, "keywords": seeds}
    elif seeds:
        body["keywordSeed"] = {"keywords": seeds}
    else:
        body["urlSeed"] = {"url": url}
    js = _call(tenant, "POST", f"customers/{cid}:generateKeywordIdeas", body)
    out = []
    for r in js.get("results") or []:
        m = r.get("keywordIdeaMetrics") or {}
        out.append({"text": str(r.get("text") or ""), "searches": int(m.get("avgMonthlySearches") or 0),
                    "competition": str(m.get("competition") or "UNSPECIFIED").lower(),
                    "low": round(int(m.get("lowTopOfPageBidMicros") or 0) / 1e6, 2),
                    "high": round(int(m.get("highTopOfPageBidMicros") or 0) / 1e6, 2)})
    out = sorted([x for x in out if x["text"]], key=lambda x: -x["searches"])[:40]
    return {"currency": cur, "ideas": out,
            "note": "Google's estimates (monthly searches, top-of-page bid range); the real cost depends on competition."}


# ---------------------------------------------------------------- Google: check, create (paused), start, pause
def _ops(cid: str, d: GAdsDraft, logo_b64: str) -> list[dict[str, Any]]:
    """One atomic Mutate in Google's own order: budget, campaign, ad group, ad group criteria, assets, ad (temp ids < 0)."""
    def rn(kind: str, n: int) -> str:
        return f"customers/{cid}/{kind}/-{n}"
    budget, camp, group, logo, video = rn("campaignBudgets", 1), rn("campaigns", 2), rn("adGroups", 3), rn("assets", 4), rn("assets", 5)
    stamp = now().strftime("%Y-%m-%d %H:%M")
    ops: list[dict[str, Any]] = [
        {"campaignBudgetOperation": {"create": {"resourceName": budget, "name": f"Hoola YouTube {stamp} budget",
                                                "deliveryMethod": "STANDARD", "amountMicros": str(int(d.daily) * 1_000_000),
                                                "explicitlyShared": False}}},     # Demand Gen: no shared budgets (Google docs)
        {"campaignOperation": {"create": {"resourceName": camp, "name": f"Hoola YouTube - {(d.video_title or d.video_id)[:60]} - {stamp}",
                                          "advertisingChannelType": "DEMAND_GEN", "status": "PAUSED", "campaignBudget": budget,
                                          "containsEuPoliticalAdvertising": "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING",
                                          "targetSpend": {}}}},
        {"adGroupOperation": {"create": {"resourceName": group, "name": f"Hoola YouTube ad group {stamp}", "campaign": camp,
                                         "status": "ENABLED", "demandGenAdGroupSettings": {"channelControls": {"selectedChannels": {
                                             "youtubeInStream": True, "youtubeInFeed": True, "youtubeShorts": True,
                                             "discover": False, "gmail": False, "display": False, "maps": False}}}}}},
        {"adGroupCriterionOperation": {"create": {"adGroup": group, "location": {"geoTargetConstant": INDIA}}}},
    ]
    for lang in _j(d.languages, ["hi", "en"])[:4]:
        if lang in LANGS:
            ops.append({"adGroupCriterionOperation": {"create": {"adGroup": group, "language": {"languageConstant": LANGS[lang]}}}})
    ops += [
        {"assetOperation": {"create": {"resourceName": logo, "name": f"Hoola logo {stamp}", "type": "IMAGE",
                                       "imageAsset": {"data": logo_b64}}}},
        {"assetOperation": {"create": {"resourceName": video, "name": f"Hoola video {d.video_id} {stamp}", "type": "YOUTUBE_VIDEO",
                                       "youtubeVideoAsset": {"youtubeVideoId": d.video_id}}}},
        {"adGroupAdOperation": {"create": {"adGroup": group, "status": "ENABLED", "ad": {
            "name": f"Hoola YouTube ad {stamp}", "finalUrls": [d.final_url],
            "demandGenVideoResponsiveAd": {
                "headlines": [{"text": h} for h in _j(d.headlines, [])],
                "longHeadlines": [{"text": d.long_headline}],
                "descriptions": [{"text": x} for x in _j(d.descriptions, [])],
                "videos": [{"asset": video}], "logoImages": [{"asset": logo}],
                "businessName": {"text": d.business}}}}}},
    ]
    return ops


_EU = "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"


def _place_ops(camp: str, geos: list[str], langs: list[str]) -> list[dict[str, Any]]:
    ops = [{"campaignCriterionOperation": {"create": {"campaign": camp, "location": {"geoTargetConstant": g}}}} for g in geos]
    ops += [{"campaignCriterionOperation": {"create": {"campaign": camp, "language": {"languageConstant": LANGS[x]}}}}
            for x in langs[:4] if x in LANGS]
    return ops


def _ops_search(cid: str, d: GAdsDraft, geos: list[str]) -> list[dict[str, Any]]:
    """Search campaign (Google's AddCampaigns + AddResponsiveSearchAd examples): Maximize clicks on Google Search + search
    partners, places + languages on the campaign, one ad group of phrase-match keywords, not-these words as campaign
    negatives, one responsive search ad."""
    def rn(kind: str, n: int) -> str:
        return f"customers/{cid}/{kind}/-{n}"
    budget, camp, group = rn("campaignBudgets", 1), rn("campaigns", 2), rn("adGroups", 3)
    stamp = now().strftime("%Y-%m-%d %H:%M")
    paths = _j(d.paths, [])
    ops: list[dict[str, Any]] = [
        {"campaignBudgetOperation": {"create": {"resourceName": budget, "name": f"Hoola Search {stamp} budget",
                                                "deliveryMethod": "STANDARD", "amountMicros": str(int(d.daily) * 1_000_000),
                                                "explicitlyShared": False}}},
        {"campaignOperation": {"create": {"resourceName": camp, "name": f"Hoola Search - {(d.business or 'ads')[:40]} - {stamp}",
                                          "advertisingChannelType": "SEARCH", "status": "PAUSED", "campaignBudget": budget,
                                          "networkSettings": {"targetGoogleSearch": True, "targetSearchNetwork": True,
                                                              "targetContentNetwork": False, "targetPartnerSearchNetwork": False},
                                          "containsEuPoliticalAdvertising": _EU, "targetSpend": {}}}},
    ]
    ops += _place_ops(camp, geos, _j(d.languages, ["hi", "en"]))
    ops += [{"campaignCriterionOperation": {"create": {"campaign": camp, "negative": True,
                                                       "keyword": {"text": w, "matchType": "BROAD"}}}} for w in _j(d.negatives, [])]
    ops.append({"adGroupOperation": {"create": {"resourceName": group, "name": f"Hoola Search ad group {stamp}", "campaign": camp,
                                                "status": "ENABLED", "type": "SEARCH_STANDARD"}}})
    ops += [{"adGroupCriterionOperation": {"create": {"adGroup": group, "status": "ENABLED",
                                                      "keyword": {"text": w, "matchType": "PHRASE"}}}} for w in _j(d.keywords, [])]
    rsa: dict[str, Any] = {"headlines": [{"text": h} for h in _j(d.headlines, [])],
                           "descriptions": [{"text": x} for x in _j(d.descriptions, [])]}
    if paths[:1]:
        rsa["path1"] = paths[0]
    if paths[1:2]:
        rsa["path2"] = paths[1]
    ops.append({"adGroupAdOperation": {"create": {"adGroup": group, "status": "ENABLED",
                                                  "ad": {"finalUrls": [d.final_url], "responsiveSearchAd": rsa}}}})
    return ops


def _ops_pmax(cid: str, d: GAdsDraft, geos: list[str], logo_b64: str, pics: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """Performance Max (Google's AddPerformanceMaxCampaign example): budget (not shared), campaign PAUSED with Maximize
    conversions, places + languages, ONE asset group with its text + image assets, all in one Mutate (Google requires
    the campaign and its asset group together). Business name + logo go on the asset group (brand guidelines off)."""
    def rn(kind: str, n: int) -> str:
        return f"customers/{cid}/{kind}/-{n}"
    budget, camp, group = rn("campaignBudgets", 1), rn("campaigns", 2), rn("assetGroups", 3)
    stamp = now().strftime("%Y-%m-%d %H:%M")
    ops: list[dict[str, Any]] = [
        {"campaignBudgetOperation": {"create": {"resourceName": budget, "name": f"Hoola PMax {stamp} budget",
                                                "deliveryMethod": "STANDARD", "amountMicros": str(int(d.daily) * 1_000_000),
                                                "explicitlyShared": False}}},
        {"campaignOperation": {"create": {"resourceName": camp, "name": f"Hoola Performance Max - {(d.business or 'ads')[:40]} - {stamp}",
                                          "advertisingChannelType": "PERFORMANCE_MAX", "status": "PAUSED", "campaignBudget": budget,
                                          "containsEuPoliticalAdvertising": _EU, "brandGuidelinesEnabled": False,
                                          "maximizeConversions": {}}}},
    ]
    ops += _place_ops(camp, geos, _j(d.languages, ["hi", "en"]))
    ops.append({"assetGroupOperation": {"create": {"resourceName": group, "name": f"Hoola asset group {stamp}", "campaign": camp,
                                                   "finalUrls": [d.final_url], "status": "ENABLED"}}})
    n = [10]

    def asset(field: str, body: dict[str, Any]) -> None:
        n[0] += 1
        a = rn("assets", n[0])
        ops.append({"assetOperation": {"create": {"resourceName": a, **body}}})
        ops.append({"assetGroupAssetOperation": {"create": {"assetGroup": group, "asset": a, "fieldType": field}}})
    for h in _j(d.headlines, []):
        asset("HEADLINE", {"textAsset": {"text": h}})
    asset("LONG_HEADLINE", {"textAsset": {"text": d.long_headline}})
    for x in _j(d.descriptions, []):
        asset("DESCRIPTION", {"textAsset": {"text": x}})
    asset("BUSINESS_NAME", {"textAsset": {"text": d.business}})
    asset("LOGO", {"name": f"Hoola logo {stamp}", "type": "IMAGE", "imageAsset": {"data": logo_b64}})
    for i, (land, sq) in enumerate(pics):
        asset("MARKETING_IMAGE", {"name": f"Hoola photo {i + 1} wide {stamp}", "type": "IMAGE", "imageAsset": {"data": land}})
        asset("SQUARE_MARKETING_IMAGE", {"name": f"Hoola photo {i + 1} square {stamp}", "type": "IMAGE", "imageAsset": {"data": sq}})
    return ops


def _asset_bytes(tenant: str, asset_id: str, what: str) -> bytes:
    from pathlib import Path

    from ..social.publish import SocialAsset
    with session() as s:
        a = s.get(SocialAsset, asset_id)
        if a is None or a.tenant_id != tenant or a.kind != "image":
            raise GAdsError(f"{what} not found; add it again.")
        return Path(a.path).read_bytes()


def _logo_b64(tenant: str, asset_id: str) -> str:
    return base64.b64encode(_asset_bytes(tenant, asset_id, "Logo photo")).decode()


def shape(data: bytes, ratio: float, width: int) -> bytes:
    """Centre-crop her photo to Google's shape (1.91:1 landscape / 1:1 square) and size, as JPEG under 5 MB."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / ratio)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im = im.resize((width, int(round(width / ratio))))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=88)
    return out.getvalue()


def _pics(tenant: str, ids: list[str]) -> list[tuple[str, str]]:
    out = []
    for aid in ids[:5]:
        raw = _asset_bytes(tenant, aid, "Photo")
        out.append((base64.b64encode(shape(raw, 1.91, 1200)).decode(), base64.b64encode(shape(raw, 1.0, 1200)).decode()))
    return out


def _send(tenant: str, did: str, validate_only: bool) -> dict[str, Any]:
    cid, _cur = _cid(tenant)
    with session() as s:
        d = s.get(GAdsDraft, did)
        if d is None or d.tenant_id != tenant:
            raise GAdsError("Ad draft not found.")
        bad = draft_problems(d)
        if bad:
            raise GAdsError(" ".join(bad))
        if d.status not in ("draft", "checked", "failed"):
            raise GAdsError("This ad is already created in Google.")
        s.expunge(d)
    k = _kind(d)
    if k == "search":
        ops = _ops_search(cid, d, geo_targets(tenant, _j(d.cities, [])))
    elif k == "pmax":
        ops = _ops_pmax(cid, d, geo_targets(tenant, _j(d.cities, [])), _logo_b64(tenant, d.logo_asset), _pics(tenant, _j(d.images, [])))
    else:
        ops = _ops(cid, d, _logo_b64(tenant, d.logo_asset))
    return _call(tenant, "POST", f"customers/{cid}/googleAds:mutate", {"mutateOperations": ops, "validateOnly": validate_only})


def check(tenant: str, did: str) -> dict[str, Any]:
    """Free: Google checks the whole ad (validateOnly) - nothing is created, nothing spends."""
    try:
        _send(tenant, did, True)
    except GAdsError as e:
        with session() as s:
            d = s.get(GAdsDraft, did)
            if d is not None and d.tenant_id == tenant:
                d.status, d.error = "failed", str(e)[:600]
        raise
    with session() as s:
        d = s.get(GAdsDraft, did)
        d.status, d.error = "checked", ""
        return _draft_view(d)


def create(tenant: str, did: str) -> dict[str, Any]:
    """Her tap: the campaign is made in HER Google Ads account, PAUSED (nothing spends until she taps Start)."""
    js = _send(tenant, did, False)
    camp = ""
    for r in js.get("mutateOperationResponses") or []:
        if (r.get("campaignResult") or {}).get("resourceName"):
            camp = r["campaignResult"]["resourceName"]
    with session() as s:
        d = s.get(GAdsDraft, did)
        d.status, d.campaign, d.error = "created", camp, ""
        return _draft_view(d)


def _set_status(tenant: str, d: GAdsDraft, status: str) -> None:
    cid, _ = _cid(tenant)
    _call(tenant, "POST", f"customers/{cid}/googleAds:mutate", {"mutateOperations": [
        {"campaignOperation": {"update": {"resourceName": d.campaign, "status": status}, "updateMask": "status"}}]})


def start(tenant: str, did: str, confirm: bool = False) -> dict[str, Any]:
    """Her tap after a confirm: the campaign may now spend up to its daily budget, for its days."""
    from ..social.desk import _local
    if not confirm:
        raise GAdsError("Your approval is needed before starting: this ad will spend its daily budget.")
    with session() as s:
        d = s.get(GAdsDraft, did)
        if d is None or d.tenant_id != tenant:
            raise GAdsError("Ad not found.")
        if d.status not in ("created", "paused"):
            raise GAdsError("First create the ad in Google (paused).")
        if int(d.daily) > _cap():
            raise GAdsError(f"The daily budget is above Hoola's limit ({_cap()}).")
        s.expunge(d)
    _set_status(tenant, d, "ENABLED")
    with session() as s:
        r = s.get(GAdsDraft, did)
        r.status, r.started_at = "running", now()
        r.stop_on = (_local(tenant).date() + timedelta(days=max(1, int(r.days)) - 1)).isoformat()
        return _draft_view(r)


def pause(tenant: str, did: str, ended: bool = False) -> dict[str, Any]:
    with session() as s:
        d = s.get(GAdsDraft, did)
        if d is None or d.tenant_id != tenant or not d.campaign:
            raise GAdsError("Ad not found.")
        s.expunge(d)
    _set_status(tenant, d, "PAUSED")
    with session() as s:
        r = s.get(GAdsDraft, did)
        r.status = "ended" if ended else "paused"
        return _draft_view(r)


def daily_watch(tenant: str) -> dict[str, Any]:
    """Every day: pause ads past their last day (she is told) and refresh the numbers."""
    from ..social.desk import SocialEvent, _local
    ensure_tables()
    today = _local(tenant).date().isoformat()
    out = {"ended": 0, "read": False}
    with session() as s:
        due = [d.id for d in s.scalars(select(GAdsDraft).where(GAdsDraft.tenant_id == tenant, GAdsDraft.status == "running")).all()
               if d.stop_on and d.stop_on < today]
    for did in due:
        try:
            v = pause(tenant, did, ended=True)
            out["ended"] += 1
            with session() as s:
                s.add(SocialEvent(tenant_id=tenant, kind="note", level="info",
                                  text=f"Google {v['kind_label']} '{v['title'][:60]}' finished its {v['days']} days and is paused."))
        except GAdsError as e:
            log.info("auto-pause failed: %s", e)
    try:
        read(tenant)
        out["read"] = True
    except GAdsError as e:
        log.info("google ads read failed: %s", e)
    return out


def view(tenant: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        a = s.scalars(select(GAdsAccount).where(GAdsAccount.tenant_id == tenant)).first()
        acc = None if a is None else {"email": a.email, "customers": _j(a.customers, []), "customer_id": a.customer_id,
                                      "currency": a.currency, "status": a.status, "error": a.last_error,
                                      "last_read": as_utc(a.last_read).isoformat() if a.last_read else ""}
    from ..social.desk import SocialMedia
    with session() as s:
        vids = [{"id": m.media_id, "title": (m.caption or "")[:90], "views": m.views or 0, "fmt": m.fmt}
                for m in s.scalars(select(SocialMedia).where(SocialMedia.tenant_id == tenant, SocialMedia.platform == "youtube")
                                   .order_by(SocialMedia.posted_at.desc())).all()[:30]]
    return {"configured": configured(), "account": acc, "drafts": drafts(tenant) if acc else [], "cap": _cap(), "videos": vids,
            "kinds": KIND_LABEL}
