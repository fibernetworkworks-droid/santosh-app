"""v0.541 SEO INTEL - DataForSEO, the paid data the official Google APIs do not give: competitor domains, the keywords a
site ranks for, keyword gaps, backlinks / referring domains and exact Google positions (owner: "GO S1 + DATAFORSEO").

Why this is allowed, said plainly: Google gives no API for another site's rankings or for anyone's backlinks, and Hoola
scrapes nothing itself. DataForSEO is a commercial data company with its own API, and it gathers this data on its side.
Using it is HER choice - her own DataForSEO login is the default (her money, her account), Newtika's shared login only when
the server enables DATAFORSEO_SHARED - and every call is costed from the price DataForSEO itself reports, against a
monthly ceiling she sets. Endpoints and fields follow DataForSEO v3 docs (and the open-seo project, MIT, that uses them).
NOT VERIFIED against a live DataForSEO account from here."""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from typing import Any

import httpx

from ..config import get_settings
from ..db import session

log = logging.getLogger("santosh.seo.dfs")
API = "https://api.dataforseo.com"
INDIA = 2356
_http: httpx.Client | None = None


class DfsError(Exception):
    pass


def set_http(c: httpx.Client | None) -> None:
    global _http
    _http = c


def _intel(s, tenant: str, site_id: str):
    from .intel import SeoIntel
    r = s.get(SeoIntel, site_id)
    if r is None:
        r = SeoIntel(site_id=site_id, tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


# ---------------------------------------------------------------- her login (sealed) or the shared one
def save_login(tenant: str, site_id: str, login: str, password: str) -> dict[str, Any]:
    """Typed in the app only. Checked once with DataForSEO's free user_data call, then sealed; never returned."""
    from .. import accounts as acc
    login, password = str(login or "").strip(), str(password or "").strip()
    if "@" not in login or len(password) < 6:
        raise DfsError("DataForSEO ka login (email) aur API password chahiye: app.dataforseo.com > API Access.")
    info = _post_raw(login, password, "GET", "/v3/appendix/user_data", None)
    res = ((info.get("tasks") or [{}])[0].get("result") or [{}])[0] or {}
    with session() as s:
        r = _intel(s, tenant, site_id)
        r.dfs_login_enc, r.dfs_pw_enc = acc.encrypt(login), acc.encrypt(password)
        r.dfs_mask = login[:2] + "***" + login[login.index("@"):]
    bal = (res.get("money") or {}).get("balance")
    return {"connected": True, "login": login[:2] + "***" + login[login.index("@"):],
            "balance_usd": bal, "say": "DataForSEO jud gaya" + (f" (balance ${bal})" if bal is not None else "") + "."}


def forget_login(tenant: str, site_id: str) -> dict[str, Any]:
    with session() as s:
        r = _intel(s, tenant, site_id)
        r.dfs_login_enc = r.dfs_pw_enc = None
        r.dfs_mask = ""
    return {"connected": False, "say": "DataForSEO login hata diya. Chahein to app.dataforseo.com par API password bhi badal dijiye."}


def _creds(tenant: str, site_id: str) -> tuple[str, str, str]:
    from .. import accounts as acc
    with session() as s:
        r = _intel(s, tenant, site_id)
        own = (acc.decrypt(r.dfs_login_enc) if r.dfs_login_enc else "") or "", (acc.decrypt(r.dfs_pw_enc) if r.dfs_pw_enc else "") or ""
    if own[0] and own[1]:
        return own[0], own[1], "own"
    st = get_settings()
    if getattr(st, "dataforseo_shared", False) and st.dataforseo_login and st.dataforseo_password:
        return st.dataforseo_login, st.dataforseo_password, "shared"
    raise DfsError("DataForSEO juda nahi hai. SEO Desk > Search intel mein apna DataForSEO login daaliye (app.dataforseo.com, "
                   "naye account mein $1 free; phir pay-as-you-go).")


def status(tenant: str, site_id: str) -> dict[str, Any]:
    st = get_settings()
    with session() as s:
        r = _intel(s, tenant, site_id)
        own, mask, spend = bool(r.dfs_login_enc), r.dfs_mask or "", _j(r.spend, {}).get(_month(), {})
        cap = float(_j(r.settings, {}).get("dfs_cap_usd") or st.dataforseo_month_usd or 5)
    shared = bool(getattr(st, "dataforseo_shared", False) and st.dataforseo_login)
    return {"connected": own or shared, "via": "own" if own else ("shared" if shared else ""), "login": mask,
            "spent_usd": round(float(spend.get("dfs_usd") or 0), 4), "cap_usd": cap}


def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except ValueError:
        return default


# ---------------------------------------------------------------- the one call (costed, capped)
def _post_raw(login: str, password: str, method: str, path: str, body: Any) -> dict[str, Any]:
    tok = base64.b64encode(f"{login}:{password}".encode()).decode()
    c = _http or httpx.Client(timeout=90)
    try:
        r = c.request(method, API + path, json=body, headers={"Authorization": f"Basic {tok}", "Content-Type": "application/json"})
    except httpx.HTTPError as e:
        raise DfsError(f"DataForSEO se baat nahi hui ({type(e).__name__}).")
    finally:
        if _http is None:
            c.close()
    if r.status_code == 401:
        raise DfsError("DataForSEO ne login nahi maana (email / API password galat). API Access page se dobara copy kijiye.")
    try:
        js = r.json()
    except ValueError:
        raise DfsError(f"DataForSEO ka jawab samajh nahi aaya ({r.status_code}).")
    code = int(js.get("status_code") or 0)
    if r.status_code >= 400 or (code and code >= 40000):
        raise DfsError(_msg(code, str(js.get("status_message") or r.text[:200])))
    return js


def _msg(code: int, text: str) -> str:
    if code == 40200 or "payment" in text.lower() or "balance" in text.lower():
        return "DataForSEO balance khatam: app.dataforseo.com par top-up kijiye (Hoola kabhi khud paise nahi bharta)."
    if code in (40204,) or "subscription" in text.lower() or "access denied" in text.lower():
        return ("DataForSEO: is data ke liye unke account mein alag access chahiye (Backlinks API ke liye unki subscription "
                "chalu karni padti hai). " + text[:120])
    return f"DataForSEO: {text[:240]}"


def call(tenant: str, site_id: str, path: str, task: dict[str, Any]) -> list[dict[str, Any]]:
    """One task to one live endpoint. Refused BEFORE the call when this month's spend reached her ceiling; the cost DataForSEO
    reports is added after."""
    st = status(tenant, site_id)
    if st["spent_usd"] >= st["cap_usd"]:
        raise DfsError(f"Is mahine ki DataForSEO seema (${st['cap_usd']}) poori ho gayi (${st['spent_usd']} kharch). "
                       "Seema badhani ho to Search intel mein badaliye.")
    login, pw, _via = _creds(tenant, site_id)
    js = _post_raw(login, pw, "POST", path, [task])
    t = (js.get("tasks") or [{}])[0] or {}
    cost = float(js.get("cost") or t.get("cost") or 0)
    with session() as s:
        r = _intel(s, tenant, site_id)
        sp = _j(r.spend, {})
        m = sp.setdefault(_month(), {})
        m["dfs_usd"] = round(float(m.get("dfs_usd") or 0) + cost, 6)
        m["dfs_calls"] = int(m.get("dfs_calls") or 0) + 1
        r.spend = json.dumps(sp)
    tc = int(t.get("status_code") or 20000)
    if tc >= 40000:
        raise DfsError(_msg(tc, str(t.get("status_message") or "")))
    return t.get("result") or []


def _dom(d: str) -> str:
    d = str(d or "").strip().lower()
    for p in ("https://", "http://"):
        if d.startswith(p):
            d = d[len(p):]
    return d.split("/")[0].removeprefix("www.")


# ---------------------------------------------------------------- what the desk asks for
def domain_overview(tenant: str, site_id: str, domain: str) -> dict[str, Any]:
    res = call(tenant, site_id, "/v3/dataforseo_labs/google/domain_rank_overview/live",
               {"target": _dom(domain), "location_code": INDIA, "language_code": "en"})
    it = ((res[0] if res else {}).get("items") or [{}])[0] or {}
    org = (it.get("metrics") or {}).get("organic") or {}
    return {"domain": _dom(domain), "keywords": int(org.get("count") or 0), "traffic": round(float(org.get("etv") or 0)),
            "top3": int(org.get("pos_1") or 0) + int(org.get("pos_2_3") or 0), "top10": sum(int(org.get(k) or 0) for k in
                                                                                         ("pos_1", "pos_2_3", "pos_4_10"))}


def ranked_keywords(tenant: str, site_id: str, domain: str, limit: int = 200) -> list[dict[str, Any]]:
    res = call(tenant, site_id, "/v3/dataforseo_labs/google/ranked_keywords/live",
               {"target": _dom(domain), "location_code": INDIA, "language_code": "en", "limit": max(10, min(int(limit), 1000)),
                "order_by": ["keyword_data.keyword_info.search_volume,desc"]})
    out = []
    for it in ((res[0] if res else {}).get("items") or []):
        kd = it.get("keyword_data") or {}
        se = ((it.get("ranked_serp_element") or {}).get("serp_item")) or {}
        out.append({"keyword": str(kd.get("keyword") or ""), "volume": int((kd.get("keyword_info") or {}).get("search_volume") or 0),
                    "position": se.get("rank_group") or se.get("rank_absolute"), "url": str(se.get("url") or "")})
    return [x for x in out if x["keyword"]]


def competitors(tenant: str, site_id: str, domain: str, limit: int = 10) -> list[dict[str, Any]]:
    res = call(tenant, site_id, "/v3/dataforseo_labs/google/competitors_domain/live",
               {"target": _dom(domain), "location_code": INDIA, "language_code": "en", "limit": max(3, min(int(limit), 50))})
    out = []
    for it in ((res[0] if res else {}).get("items") or []):
        d = _dom(it.get("domain") or "")
        if not d or d == _dom(domain):
            continue
        org = ((it.get("full_domain_metrics") or it.get("metrics") or {}).get("organic")) or {}
        out.append({"domain": d, "shared_keywords": int(it.get("intersections") or 0),
                    "avg_position": round(float(it.get("avg_position") or 0), 1), "keywords": int(org.get("count") or 0),
                    "traffic": round(float(org.get("etv") or 0))})
    return out


def gap(tenant: str, site_id: str, mine: str, theirs: str, limit: int = 300) -> dict[str, Any]:
    """Keywords the competitor ranks for in Google's top 20 where her site is missing or below 20 - by search volume."""
    a = {x["keyword"].lower(): x for x in ranked_keywords(tenant, site_id, mine, limit)}
    b = ranked_keywords(tenant, site_id, theirs, limit)
    rows = []
    for x in b:
        if not x["position"] or int(x["position"]) > 20:
            continue
        m = a.get(x["keyword"].lower())
        if m and m["position"] and int(m["position"]) <= 20:
            continue
        rows.append({"keyword": x["keyword"], "volume": x["volume"], "their_position": x["position"], "their_url": x["url"],
                     "your_position": (m or {}).get("position")})
    rows.sort(key=lambda r: -r["volume"])
    return {"mine": _dom(mine), "theirs": _dom(theirs), "gap": rows[:60],
            "say": f"{_dom(theirs)} {len(rows)} aise shabdon par top 20 mein hai jahan aap nahi."}


def backlinks(tenant: str, site_id: str, domain: str, limit: int = 30) -> dict[str, Any]:
    target = _dom(domain)
    summ = (call(tenant, site_id, "/v3/backlinks/summary/live", {"target": target, "internal_list_limit": 5,
                                                                 "include_subdomains": True}) or [{}])[0] or {}
    refs = call(tenant, site_id, "/v3/backlinks/referring_domains/live",
                {"target": target, "limit": max(10, min(int(limit), 100)), "order_by": ["rank,desc"], "exclude_internal_backlinks": True})
    items = [{"domain": _dom(x.get("domain") or ""), "rank": int(x.get("rank") or 0), "backlinks": int(x.get("backlinks") or 0),
              "first_seen": str(x.get("first_seen") or "")[:10], "spam_score": x.get("backlinks_spam_score")}
             for x in ((refs[0] if refs else {}).get("items") or [])]
    return {"domain": target, "rank": int(summ.get("rank") or 0), "backlinks": int(summ.get("backlinks") or 0),
            "referring_domains": int(summ.get("referring_domains") or 0), "broken": int(summ.get("broken_backlinks") or 0),
            "spam_score": summ.get("backlinks_spam_score"), "top_referrers": items}


def serp(tenant: str, site_id: str, keyword: str, mine: str = "", device: str = "mobile", lang: str = "en") -> dict[str, Any]:
    """Google's organic results for one keyword in India (top 100): her exact position + who holds the top 3."""
    res = call(tenant, site_id, "/v3/serp/google/organic/live/advanced",
               {"keyword": str(keyword)[:200], "location_code": INDIA, "language_code": lang, "device": device, "depth": 100})
    items = [x for x in ((res[0] if res else {}).get("items") or []) if x.get("type") == "organic"]
    me = _dom(mine)
    pos, url = None, ""
    for x in items:
        d = _dom(x.get("domain") or x.get("url") or "")
        if me and (d == me or d.endswith("." + me)):
            pos, url = x.get("rank_group"), str(x.get("url") or "")
            break
    return {"keyword": keyword, "position": pos, "url": url,
            "top": [{"position": x.get("rank_group"), "domain": _dom(x.get("domain") or ""), "title": str(x.get("title") or "")[:90]}
                    for x in items[:3]]}


def keyword_ideas(tenant: str, site_id: str, seeds: list[str], limit: int = 40) -> list[dict[str, Any]]:
    """Fallback when her Google Ads (Keyword Planner) is not linked."""
    res = call(tenant, site_id, "/v3/dataforseo_labs/google/keyword_ideas/live",
               {"keywords": [str(s)[:80] for s in seeds[:20]], "location_code": INDIA, "language_code": "en", "limit": max(10, min(limit, 200))})
    out = []
    for it in ((res[0] if res else {}).get("items") or []):
        ki = it.get("keyword_info") or {}
        out.append({"text": str(it.get("keyword") or ""), "searches": int(ki.get("search_volume") or 0),
                    "competition": str(ki.get("competition_level") or "").lower(), "low": ki.get("low_top_of_page_bid"),
                    "high": ki.get("high_top_of_page_bid")})
    return sorted([x for x in out if x["text"]], key=lambda x: -x["searches"])
