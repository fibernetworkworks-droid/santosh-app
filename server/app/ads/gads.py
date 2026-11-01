"""v0.396 YOUTUBE ADS (plan Y2): her own Google Ads account through the official Google Ads API (REST, v26 - field names from
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
    st = get_settings()
    return bool(st.google_ads_developer_token and st.google_oauth_client_id and st.google_oauth_client_secret
                and st.public_base_url)


# ---------------------------------------------------------------- connecting (Google sign-in with adwords)
def is_link_state(state: str) -> bool:
    return (state or "").startswith("gad_")


def connect_url(tenant: str) -> str:
    from .. import accounts as acc
    from ..mailbox import accounts as mail_acc
    if not configured():
        raise GAdsError("Server par Google Ads abhi set nahi hai (.env: GOOGLE_ADS_DEVELOPER_TOKEN + Google sign-in).")
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
            raise GAdsError("Yeh link purana ho gaya. Dobara 'Connect Google Ads' dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "redirect_uri": acc._redirect_uri(), "grant_type": "authorization_code"})
        if SCOPE not in (tok.get("scope") or "").split():
            raise GAdsError("Google Ads ki permission nahi di gayi. Dobara jodte waqt Google Ads allow kijiye.")
        info = mail_acc._get("https://openidconnect.googleapis.com/v1/userinfo", tok["access_token"])
    except mail_acc.MailError as e:
        raise GAdsError(str(e))
    if not tok.get("refresh_token"):
        raise GAdsError("Google se refresh token nahi mila; dobara jodiye.")
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
            raise GAdsError("Google Ads abhi juda nahi hai: Social Desk par 'Connect Google Ads' dabaiye.")
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
        raise GAdsError("Google Ads ka login khatam: dobara 'Connect Google Ads' dabaiye.")
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
        headers = {"Authorization": f"Bearer {token}", "developer-token": st.google_ads_developer_token,
                   "Content-Type": "application/json"}
        if st.google_ads_login_customer_id:
            headers["login-customer-id"] = re.sub(r"\D", "", st.google_ads_login_customer_id)
        c = _http or httpx.Client(timeout=60)
        try:
            r = c.request(method, f"{API}/{st.google_ads_api_version}/{path}", json=body, headers=headers)
        except httpx.HTTPError as e:
            raise GAdsError(f"Google Ads se baat nahi hui ({type(e).__name__}).")
        finally:
            if _http is None:
                c.close()
        if r.status_code == 401 and attempt == 0:
            continue
        if r.status_code >= 400:
            raise GAdsError(_error_text(r))
        return r.json() if r.content else {}
    raise GAdsError("Google Ads ne login nahi maana.")


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
                if "DEVELOPER_TOKEN_NOT_APPROVED" in code or "not approved" in m.lower():
                    return ("Google Ads: Hoola ka developer token abhi sirf test accounts ke liye hai (Basic access approval "
                            "baaki). Asli account par yeh tab chalega jab Google approve karega.")
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
            raise GAdsError("Google Ads abhi juda nahi hai.")
        c = next((x for x in _j(a.customers, []) if x["id"] == cid), None)
        if c is None:
            raise GAdsError("Yeh ad account aapke login mein nahi mila.")
        if c.get("manager"):
            raise GAdsError("Yeh manager (MCC) account hai; jis account mein ads chalte hain woh chuniye.")
        a.customer_id, a.currency = cid, c.get("currency") or ""
    return {"customer_id": cid, "currency": c.get("currency") or ""}


def _cid(tenant: str) -> tuple[str, str]:
    with session() as s:
        a = s.scalars(select(GAdsAccount).where(GAdsAccount.tenant_id == tenant)).first()
        if a is None:
            raise GAdsError("Google Ads abhi juda nahi hai: 'Connect Google Ads' dabaiye.")
        if not a.customer_id:
            raise GAdsError("Pehle chuniye kaunse Google Ads account mein YouTube ads chalenge.")
        return a.customer_id, a.currency


# ---------------------------------------------------------------- reading her YouTube ads
_METRIC_SETS = ("metrics.video_trueview_views", "metrics.video_views", "")


def read(tenant: str, days: int = 30) -> dict[str, Any]:
    """Her YouTube campaigns (VIDEO + DEMAND_GEN) by day -> the Ads desk's report rows (platform google)."""
    from . import service as ads
    cid, cur = _cid(tenant)
    rows, err = None, ""
    for views in _METRIC_SETS:
        q = ("SELECT segments.date, campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, "
             "campaign_budget.amount_micros, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions"
             + (f", {views}" if views else "") + " FROM campaign WHERE campaign.advertising_channel_type IN ('VIDEO', 'DEMAND_GEN') "
             f"AND segments.date DURING LAST_{30 if days >= 30 else 14 if days >= 14 else 7}_DAYS")
        try:
            rows = search(tenant, cid, q)
            break
        except GAdsError as e:
            err = str(e)
            if "UNRECOGNIZED_FIELD" not in err and "unrecognized field" not in err.lower() and "video_" not in err:
                raise
    if rows is None:
        raise GAdsError(err or "Google Ads report nahi mila.")
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
            report = ads.import_report(tenant, data=out.getvalue().encode(), name="google_ads_youtube.csv", platform="google")
        except Exception as e:   # noqa: BLE001 - the numbers still show here
            log.info("ads desk import skipped: %s", e)
    with session() as s:
        a = s.scalars(select(GAdsAccount).where(GAdsAccount.tenant_id == tenant)).first()
        a.last_read = now()
    for v in camps.values():
        v["spend"] = round(v["spend"], 2)
        v["cpv"] = round(v["spend"] / v["views"], 2) if v["views"] else None
        v["ctr"] = round(100 * v["clicks"] / v["impressions"], 2) if v["impressions"] else None
    return {"currency": cur, "campaigns": sorted(camps.values(), key=lambda x: -x["spend"]), "rows": len(rows),
            "ads_desk": (report or {}).get("say", "")}


# ---------------------------------------------------------------- drafts (in Hoola only)
def _cap() -> int:
    return int(getattr(get_settings(), "gads_max_daily", 2000) or 2000)


def draft_problems(d: GAdsDraft) -> list[str]:
    from .rules import banned, financial
    out = []
    hs, ds = _j(d.headlines, []), _j(d.descriptions, [])
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", d.video_id or ""):
        out.append("YouTube video chuniye (aapke channel ka public / unlisted video).")
    if not (LIMITS["headlines"][0] <= len(hs) <= LIMITS["headlines"][1]):
        out.append("1 se 5 headlines chahiye.")
    out += [f"Headline '{h[:20]}...' {LIMITS['headline']} akshar se lambi hai." for h in hs if len(h) > LIMITS["headline"]]
    if not d.long_headline or len(d.long_headline) > LIMITS["long_headline"]:
        out.append(f"Long headline chahiye ({LIMITS['long_headline']} akshar tak).")
    if not (LIMITS["descriptions"][0] <= len(ds) <= LIMITS["descriptions"][1]):
        out.append("1 se 5 descriptions chahiye.")
    out += [f"Description {LIMITS['description']} akshar se lambi hai." for x in ds if len(x) > LIMITS["description"]]
    if not d.business or len(d.business) > LIMITS["business"]:
        out.append(f"Business ka naam chahiye ({LIMITS['business']} akshar tak).")
    if not re.match(r"^https://[^\s/]+\.[^\s]+", d.final_url or ""):
        out.append("Ad kahan le jaye: website / WhatsApp link (https://...) chahiye.")
    if not d.logo_asset:
        out.append("Logo chahiye (chaukor photo, jaise 1200x1200).")
    if not (1 <= int(d.daily or 0) <= _cap()):
        out.append(f"Roz ka budget 1 se {_cap()} ke beech rakhiye (Hoola ki seema).")
    if not (1 <= int(d.days or 0) <= 30):
        out.append("Kitne din chalana hai: 1 se 30.")
    text = " ".join(hs + ds + [d.long_headline, d.business])
    out += banned(text)
    if financial(text):
        out.append("Paisa / investment wala ad: Google ki financial services verification aur SEBI niyam pehle; Hoola aisa ad nahi banata.")
    return out


def _draft_view(d: GAdsDraft) -> dict[str, Any]:
    return {"id": d.id, "video_id": d.video_id, "video_title": d.video_title, "daily": d.daily, "days": d.days,
            "total": d.daily * d.days, "final_url": d.final_url, "business": d.business, "headlines": _j(d.headlines, []),
            "long_headline": d.long_headline, "descriptions": _j(d.descriptions, []), "languages": _j(d.languages, []),
            "logo_asset": d.logo_asset, "status": d.status, "campaign": d.campaign, "stop_on": d.stop_on, "error": d.error,
            "problems": draft_problems(d) if d.status in ("draft", "checked", "failed") else []}


def new_draft(tenant: str, video_id: str = "", **kw: Any) -> dict[str, Any]:
    """A draft from one of her videos, pre-filled from her Social Desk facts (all editable)."""
    from ..social.desk import SocialDesk, SocialMedia
    ensure_tables()
    vid = str(video_id or "").strip()
    with session() as s:
        d0 = s.get(SocialDesk, tenant)
        prof = _j(d0.profile, {}) if d0 is not None else {}
        m = s.scalars(select(SocialMedia).where(SocialMedia.tenant_id == tenant, SocialMedia.platform == "youtube",
                                                SocialMedia.media_id == vid)).first() if vid else None
        title = (m.caption if m is not None else "") or ""
    biz = str(prof.get("business") or "")[:LIMITS["business"]]
    city = str(prof.get("city") or "")
    sells = str(prof.get("sells") or "").split(",")[0].strip()
    heads = [h for h in [title[:LIMITS["headline"]], (f"{sells} in {city}" if sells and city else sells)[:LIMITS["headline"]],
                         (f"{biz} - {city}" if city else biz)[:LIMITS["headline"]]] if h][:3]
    d = GAdsDraft(tenant_id=tenant, video_id=vid, video_title=title[:200], business=biz,
                  headlines=json.dumps(kw.get("headlines") or heads, ensure_ascii=False),
                  long_headline=str(kw.get("long_headline") or (f"{biz}: {sells}" + (f", {city}" if city else ""))).strip(": ")[:LIMITS["long_headline"]],
                  descriptions=json.dumps(kw.get("descriptions") or [f"{sells or biz} - abhi call / WhatsApp kijiye."[:LIMITS["description"]]],
                                          ensure_ascii=False),
                  final_url=str(kw.get("final_url") or prof.get("website") or ""),
                  daily=int(kw.get("daily") or 300), days=int(kw.get("days") or 3))
    with session() as s:
        s.add(d)
        s.flush()
        return _draft_view(d)


def set_draft(tenant: str, did: str, **kw: Any) -> dict[str, Any]:
    with session() as s:
        d = s.get(GAdsDraft, did)
        if d is None or d.tenant_id != tenant:
            raise GAdsError("Yeh ad draft nahi mila.")
        if d.status not in ("draft", "checked", "failed"):
            raise GAdsError("Yeh ad Google mein ban chuka; badlav Google Ads mein kijiye ya naya draft banaiye.")
        for f in ("video_id", "final_url", "business", "long_headline", "logo_asset"):
            if kw.get(f) is not None:
                setattr(d, f, str(kw[f]).strip()[:300])
        for f in ("headlines", "descriptions", "languages"):
            if isinstance(kw.get(f), list):
                setattr(d, f, json.dumps([str(x).strip() for x in kw[f] if str(x).strip()][:5], ensure_ascii=False))
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


def _logo_b64(tenant: str, asset_id: str) -> str:
    from pathlib import Path

    from ..social.publish import SocialAsset
    with session() as s:
        a = s.get(SocialAsset, asset_id)
        if a is None or a.tenant_id != tenant or a.kind != "image":
            raise GAdsError("Logo photo nahi mili; dobara jodiye.")
        return base64.b64encode(Path(a.path).read_bytes()).decode()


def _send(tenant: str, did: str, validate_only: bool) -> dict[str, Any]:
    cid, _cur = _cid(tenant)
    with session() as s:
        d = s.get(GAdsDraft, did)
        if d is None or d.tenant_id != tenant:
            raise GAdsError("Yeh ad draft nahi mila.")
        bad = draft_problems(d)
        if bad:
            raise GAdsError(" ".join(bad))
        if d.status not in ("draft", "checked", "failed"):
            raise GAdsError("Yeh ad pehle hi Google mein ban chuka.")
        s.expunge(d)
    body = {"mutateOperations": _ops(cid, d, _logo_b64(tenant, d.logo_asset)), "validateOnly": validate_only}
    return _call(tenant, "POST", f"customers/{cid}/googleAds:mutate", body)


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
        raise GAdsError("Start karne se pehle haan chahiye: is ad par roz ka budget kharch hoga.")
    with session() as s:
        d = s.get(GAdsDraft, did)
        if d is None or d.tenant_id != tenant:
            raise GAdsError("Yeh ad nahi mila.")
        if d.status not in ("created", "paused"):
            raise GAdsError("Pehle ad ko Google mein (paused) banaiye.")
        if int(d.daily) > _cap():
            raise GAdsError(f"Roz ka budget Hoola ki seema ({_cap()}) se zyada hai.")
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
            raise GAdsError("Yeh ad nahi mila.")
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
                                  text=f"YouTube ad for '{v['video_title'][:60]}' finished its {v['days']} days and is paused."))
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
    return {"configured": configured(), "account": acc, "drafts": drafts(tenant) if acc else [], "cap": _cap(), "videos": vids}
