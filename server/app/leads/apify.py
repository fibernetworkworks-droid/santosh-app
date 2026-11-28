"""v0.999.62 APIFY LANE - Apify's ready-made scrapers as one more leads source (owner: "GO APIFY -- CHANGE THE RULE
FOR THIS Instagram / Facebook / LinkedIn / TikTok profiles").

The owner moved her own leads wall on 20 Nov 2026: PUBLIC BUSINESS profiles on Instagram, Facebook, LinkedIn and
TikTok may now be gathered, through Apify, with HER Apify token and HER Apify credit. This module is that lane and
nothing wider. The walls it keeps (rules.APIFY_WALLS, quoted on her opt-in slip):

- opt-in per tenant, OFF by default (her tap, recorded with who + when + the walls);
- her own Apify token on the server only (APIFY_TOKEN), and APIFY_TERMS_ACK naming "apify" - she has read
  Apify's terms and the platforms' terms herself; Hoola does not assume it;
- NEVER a login: Hoola writes every scraper input itself from fixed templates; an input that carries cookies,
  a session, a password or a login is refused before any call, and no scraper is given her accounts;
- BUSINESS profiles only: a social row is kept only when it carries a business signal (a business / creator
  account flag, a business category, or a public business email / phone / website); private accounts and
  personal profiles are refused and counted - India's DPDP Act is about people's personal data, and a
  business's public contact is what a lead is;
- a dollar ceiling per run sent to Apify itself (maxTotalChargeUsd) and checked again on Apify's own reported
  usage; a run never retried (never pays twice);
- every row carries its profile / page link as provenance; the engine NEVER contacts anyone - outreach stays her
  tap on the campaign / email desks; opt-out and forget work on these rows like any other.

Apify API used (docs.apify.com/api/v2 - written to the documented shape, NOT VERIFIED against a live account):
  POST /v2/acts/{actor}/runs?maxItems=N&maxTotalChargeUsd=X   body = the actor input     -> data.id, defaultDatasetId
  GET  /v2/actor-runs/{id}?waitForFinish=60                                              -> data.status, usageTotalUsd
  GET  /v2/datasets/{datasetId}/items?clean=true&format=json&limit=N                     -> [items]
  POST /v2/actor-runs/{id}/abort
Auth: Authorization: Bearer <APIFY_TOKEN> (the token only ever rides the header).
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import time
from typing import Any

import httpx

API = "https://api.apify.com/v2"
_transport: httpx.AsyncBaseTransport | None = None      # tests plug in httpx.MockTransport
_sleep = asyncio.sleep

# Which scrapers (Apify "actors") and the inputs Hoola writes for them. {query} {city} {max} {urls} {handles}
# are filled by Hoola. Each default is a public Apify Store actor named from memory - NOT VERIFIED; apify_check
# runs it on 3 rows first, and the owner can swap any actor with APIFY_ACTOR_<PLATFORM> + APIFY_INPUT_<PLATFORM>.
PLATFORMS: dict[str, dict[str, Any]] = {
    "instagram": {"actor": "apify/instagram-scraper", "social": True,
                  "search": {"search": "{query}", "searchType": "user", "searchLimit": "{max}",
                             "resultsType": "details", "resultsLimit": 1},
                  "urls": {"directUrls": "{urls}", "resultsType": "details", "resultsLimit": 1}},
    "tiktok": {"actor": "clockworks/tiktok-scraper", "social": True,
               "search": {"searchQueries": ["{query}"], "searchSection": "/user", "maxProfilesPerQuery": "{max}",
                          "resultsPerPage": 1},
               "urls": {"profiles": "{handles}", "resultsPerPage": 1}},
    "facebook": {"actor": "apify/facebook-pages-scraper", "social": True, "pages": True,
                 "search": None,
                 "urls": {"startUrls": "{url_objs}"}},
    "linkedin": {"actor": "harvestapi/linkedin-company-search", "social": True, "pages": True,
                 "search": {"searchQuery": "{query}", "locations": ["{city}"], "maxItems": "{max}"},
                 "urls": None},
    "google_maps": {"actor": "compass/crawler-google-places", "social": False,
                    "search": {"searchStringsArray": ["{query}"], "locationQuery": "{city}",
                               "maxCrawledPlacesPerSearch": "{max}", "language": "en"},
                    "urls": None},
    "contacts": {"actor": "vdrmota/contact-info-scraper", "social": False,
                 "search": None,
                 "urls": {"startUrls": "{url_objs}", "maxRequestsPerStartUrl": 5, "sameDomain": True}},
}
REFUSED_INPUT = ("cookie", "cookies", "session", "sessionid", "sessioncookie", "li_at", "login", "password",
                 "passwd", "username_password", "auth", "token", "credentials", "otp")


class ApifyError(Exception):
    """A refusal or a failed call, said plainly (never carries the token)."""


def _st():
    from ..config import get_settings
    return get_settings()


def _csv(s: str) -> set[str]:
    return {x.strip().lower() for x in str(s or "").split(",") if x.strip()}


def platform(name: str) -> dict[str, Any]:
    p = str(name or "").lower().strip().replace(" ", "_").replace("-", "_")
    p = {"insta": "instagram", "ig": "instagram", "fb": "facebook", "maps": "google_maps", "gmaps": "google_maps",
         "website_contacts": "contacts", "websites": "contacts"}.get(p, p)
    if p not in PLATFORMS:
        raise ApifyError(f"'{name}' is not an Apify platform here - use one of: {', '.join(PLATFORMS)}.")
    out = copy.deepcopy(PLATFORMS[p]) | {"name": p}
    st = _st()
    actor = str(getattr(st, f"apify_actor_{p}", "") or "").strip()
    if actor:
        out["actor"] = actor
        raw = str(getattr(st, f"apify_input_{p}", "") or "").strip()
        if raw:
            try:
                tpl = json.loads(raw)
            except ValueError:
                raise ApifyError(f"APIFY_INPUT_{p.upper()} is not valid JSON.") from None
            out["search"] = tpl if "{query}" in raw else out.get("search")
            out["urls"] = tpl if ("{urls}" in raw or "{url_objs}" in raw or "{handles}" in raw) else out.get("urls")
    return out


def _deny_logins(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            low = re.sub(r"[^a-z_]", "", str(k).lower())
            if low in REFUSED_INPUT or any(w in low for w in ("cookie", "session", "password", "login")):
                raise ApifyError(f"The scraper input has '{path}{k}' - Hoola never gives a scraper a login, cookie or "
                                 "session. Pick a scraper that works on public pages without signing in.")
            _deny_logins(v, f"{path}{k}.")
    elif isinstance(obj, list):
        for v in obj:
            _deny_logins(v, path)


def _fill(tpl: Any, vals: dict[str, Any]) -> Any:
    if isinstance(tpl, dict):
        return {k: _fill(v, vals) for k, v in tpl.items()}
    if isinstance(tpl, list):
        out = []
        for v in tpl:
            f = _fill(v, vals)
            if isinstance(v, str) and v in ("{urls}", "{url_objs}", "{handles}"):
                out.extend(f)
            else:
                out.append(f)
        return out
    if isinstance(tpl, str):
        if tpl in ("{urls}", "{url_objs}", "{handles}", "{max}"):
            return vals[tpl[1:-1]]
        return re.sub(r"\{(query|city)\}", lambda m: str(vals.get(m.group(1)) or ""), tpl)
    return tpl


def _handle(u: str) -> str:
    u = u.strip().rstrip("/")
    return u.rsplit("/", 1)[-1].lstrip("@") if "/" in u else u.lstrip("@")


def build_input(p: dict[str, Any], query: str, city: str, urls: list[str], max_rows: int) -> dict[str, Any]:
    urls = [u.strip() for u in (urls or []) if str(u).strip()][:200]
    for u in urls:
        if not (u.startswith("https://") or u.startswith("http://")) and p["name"] not in ("instagram", "tiktok"):
            raise ApifyError(f"'{u}' is not a web address.")
    if urls:
        tpl = p.get("urls")
        if not tpl:
            raise ApifyError(f"The {p['name']} scraper here takes a search, not a list of links - give query + city.")
    else:
        tpl = p.get("search")
        if not tpl:
            raise ApifyError(f"The {p['name']} scraper here needs links (urls) - for example the business pages' "
                             "addresses. A keyword search is not offered for it.")
        if not str(query or "").strip():
            raise ApifyError("What to search for? Give query (for example 'bakery Pune').")
    q = str(query or "").strip()
    if city and p["name"] in ("instagram", "tiktok") and city.lower() not in q.lower():
        q = f"{q} {city}".strip()
    vals = {"query": q, "city": str(city or "").strip(), "max": max(1, int(max_rows)),
            "urls": urls, "url_objs": [{"url": u} for u in urls], "handles": [_handle(u) for u in urls]}
    inp = _fill(tpl, vals)
    _deny_logins(inp)
    return inp


# ---------------------------------------------------------------- the gate

def config_snapshot() -> dict[str, Any]:
    st = _st()
    return {"token_set": bool(str(getattr(st, "apify_token", "") or "").strip()),
            "terms_ack": "apify" in _csv(getattr(st, "apify_terms_ack", "")),
            "max_usd_per_run": float(getattr(st, "apify_max_usd_per_run", 5.0) or 0.0),
            "usd_inr": float(getattr(st, "usage_usd_inr", 88.0) or 88.0),
            "platforms": {k: platform(k)["actor"] for k in PLATFORMS}}


def check(tenant: str) -> tuple[bool, str]:
    from . import service as S
    st = _st()
    if not str(getattr(st, "apify_token", "") or "").strip():
        return False, ("The Apify lane needs your Apify API token on the server: put APIFY_TOKEN=<token> in the VPS "
                       ".env (Apify Console > Settings > API & Integrations). Never paste it in chat.")
    if "apify" not in _csv(getattr(st, "apify_terms_ack", "")):
        return False, ("Read Apify's terms and the platforms' terms yourself, then set APIFY_TERMS_ACK=apify in the "
                       "VPS .env - the scraping is yours, on your Apify account, so this act is yours.")
    if float(getattr(st, "apify_max_usd_per_run", 0) or 0) <= 0:
        return False, "APIFY_MAX_USD_PER_RUN is 0, so no run can have a ceiling - set it (for example 5)."
    if not S.apify_opted_in(tenant):
        return False, ("The Apify lane is OFF for your account (off by default). It turns on only with your tap: "
                       "leads_run action=apify_optin on=true.")
    return True, ""


# ---------------------------------------------------------------- the calls

def _hdr() -> dict[str, str]:
    return {"Authorization": f"Bearer {str(_st().apify_token).strip()}", "content-type": "application/json"}


def _safe(text: str) -> str:
    tok = str(getattr(_st(), "apify_token", "") or "")
    t = (text or "")[:200]
    return t.replace(tok, "***") if tok else t


async def _req(c: httpx.AsyncClient, method: str, path: str, **kw: Any) -> dict[str, Any]:
    try:
        r = await c.request(method, path, headers=_hdr(), **kw)
    except httpx.HTTPError as e:
        raise ApifyError(f"Apify could not be reached ({type(e).__name__}).") from None
    if r.status_code in (401, 403):
        raise ApifyError(f"Apify refused the token ({r.status_code}) - check APIFY_TOKEN.")
    if r.status_code == 402:
        raise ApifyError("Your Apify account is out of credit (402) - add credit at console.apify.com.")
    if r.status_code == 404:
        raise ApifyError(f"Apify does not know this scraper or run (404): {path.split('?')[0]}.")
    if r.status_code >= 400:
        raise ApifyError(f"Apify returned {r.status_code}: {_safe(r.text)}")
    try:
        js = r.json()
    except ValueError:
        raise ApifyError("Apify did not answer in JSON.") from None
    return js


async def start(actor: str, inp: dict[str, Any], max_rows: int, max_usd: float) -> dict[str, Any]:
    """Start one actor run. NEVER retried (Apify may bill for a started run)."""
    aid = actor.replace("/", "~")
    async with httpx.AsyncClient(base_url=API, timeout=60, transport=_transport) as c:
        js = await _req(c, "POST", f"/acts/{aid}/runs",
                        params={"maxItems": max(1, int(max_rows)), "maxTotalChargeUsd": round(float(max_usd), 2)},
                        json=inp)
    d = js.get("data") or {}
    if not d.get("id"):
        raise ApifyError("Apify did not return a run id.")
    return d


async def wait(run_id: str, seconds: int) -> dict[str, Any]:
    """Wait up to `seconds` for the run to end (Apify's own waitForFinish, 60 s a call)."""
    t0 = time.time()
    async with httpx.AsyncClient(base_url=API, timeout=90, transport=_transport) as c:
        while True:
            js = await _req(c, "GET", f"/actor-runs/{run_id}", params={"waitForFinish": 60})
            d = js.get("data") or {}
            if d.get("status") in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT", "TIMED_OUT"):
                return d
            if time.time() - t0 >= seconds:
                return d
            await _sleep(2)


async def items(dataset_id: str, limit: int) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(base_url=API, timeout=120, transport=_transport) as c:
        js = await _req(c, "GET", f"/datasets/{dataset_id}/items",
                        params={"clean": "true", "format": "json", "limit": max(1, int(limit))})
    if isinstance(js, dict):
        js = js.get("items") or js.get("data") or []
    return [x for x in js if isinstance(x, dict)]


async def abort(run_id: str) -> None:
    async with httpx.AsyncClient(base_url=API, timeout=30, transport=_transport) as c:
        await _req(c, "POST", f"/actor-runs/{run_id}/abort")


# ---------------------------------------------------------------- rows

def _first(d: dict, *keys: str) -> Any:
    for k in keys:
        v = d.get(k)
        if isinstance(v, list):
            v = next((x for x in v if x), None)
        if isinstance(v, dict):
            v = v.get("url") or v.get("value") or v.get("name")
        if v not in (None, "", []):
            return v
    return None


def to_row(p: dict[str, Any], it: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """One Apify item -> a lead row, or (None, why it was refused)."""
    name = p["name"]
    if it.get("isPrivate") or it.get("private") or it.get("privateAccount"):
        return None, "private account"
    handle = _first(it, "username", "uniqueId", "userName", "handle")
    url = _first(it, "url", "profileUrl", "pageUrl", "linkedinUrl", "companyUrl", "inputUrl", "facebookUrl")
    if not url and handle:
        url = {"instagram": f"https://www.instagram.com/{handle}/",
               "tiktok": f"https://www.tiktok.com/@{handle}"}.get(name)
    row = {
        "name": _first(it, "fullName", "title", "pageName", "companyName", "name", "nickname", "nickName") or handle or "",
        "phone": _first(it, "businessPhoneNumber", "publicPhoneNumber", "contactPhoneNumber", "phone", "phones",
                        "phoneNumber", "phoneUnformatted"),
        "email": _first(it, "businessEmail", "publicEmail", "email", "emails"),
        "website": _first(it, "externalUrl", "website", "websites", "bioLink", "websiteUrl", "domain"),
        "category": _first(it, "businessCategoryName", "categoryName", "category", "categories", "industry",
                           "industries"),
        "address": _first(it, "address", "businessAddress", "street", "headquarter", "location"),
        "city": _first(it, "city", "businessCity", "addressCity"),
        "rating": _first(it, "totalScore", "rating"),
        "review_count": _first(it, "reviewsCount", "reviewCount"),
        "lat": (it.get("location") or {}).get("lat") if isinstance(it.get("location"), dict) else it.get("lat"),
        "lng": (it.get("location") or {}).get("lng") if isinstance(it.get("location"), dict) else it.get("lng"),
        "place_id": it.get("placeId"),
        "cid": it.get("cid"),
    }
    row = {k: (str(v).strip() if isinstance(v, (str, int, float)) and k not in ("rating", "review_count", "lat", "lng")
               else v) for k, v in row.items() if v not in (None, "")}
    for k in ("address", "city", "category"):
        if isinstance(row.get(k), (dict, list)):
            row[k] = json.dumps(row[k], ensure_ascii=False)[:200]
    if not url or not str(url).startswith(("http://", "https://")):
        return None, "no link to the profile / page (provenance)"
    if p.get("social") and not p.get("pages"):
        biz = (it.get("isBusinessAccount") or it.get("is_business_account") or it.get("isBusiness")
               or it.get("businessCategoryName") or it.get("commerceUserInfo") or it.get("category")
               or row.get("email") or row.get("phone") or row.get("website"))
        if not biz:
            return None, "personal profile (no business signal)"
    if p.get("social"):
        socials = {name: str(url)[:300]}
        f = _first(it, "followersCount", "followers", "fans", "followerCount")
        if f is not None:
            socials[f"{name}_followers"] = f
        row["socials"] = socials
        row["profile_url"] = str(url)[:300]
    return row, str(url)[:500]
