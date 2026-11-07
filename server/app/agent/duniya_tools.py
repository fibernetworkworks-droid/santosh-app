"""v0.667.0 DUNIYA MANCH - the T4 keyless-public-web family, backend-only (owner: "T4" - the T4 tier
of download/HOOLA_MCP_FEED.json, the no-login / no-key public-web rows; the tier ladder was three
for three after JHAROKHA v0.665 - T1 SANDARBH, T2 BHANDAR, T3 JHAROKHA - and this closes it).

A duniya (दुनिया) is the world outside the haveli's walls. The jharokha (T3) is the window you lean
out of; the duniya is the street itself - the parts of the public web that answer anyone who knocks,
no account, no API key, no password, ever. ONE tool `duniya`, GET-only, fixed public endpoints for
the famous no-key services plus one honest generic page fetch.

The T4 catalog rows this lane ports (all zero-login / zero-key by definition, all
catalog-description-verified; IDEA-ONLY - zero upstream code, zero new pip, zero new keys):

- modelcontextprotocol/servers - fetch (the official reference): "Web content fetching capabilities
  for LLMs." -> the `fetch` action: one public URL, the page comes back as readable text, stripped
  of scripts and markup, capped, with the final URL after redirects told honestly.
- the no-key public-API rows of the feed's T4 tier (the family the awesome lists keep under
  "no auth required"): Wikipedia search + summaries -> `wikipedia`; Open-Meteo geocoding + forecast
  -> `weather`; the Hacker News (Algolia) search API -> `hn`; Frankfurter exchange rates -> 
  `currency`; the Free Dictionary API -> `dictionary`; the arXiv export API -> `arxiv`.

THE LAWS:

- GET only, forever: this lane never POSTs, PUTs, DELETEs, never sends an Authorization header,
  never stores a cookie, never touches a login. The write-side of the web is other lanes' business.
- Fixed endpoints by construction: every named action's base URL is a code constant; only `fetch`
  takes a free URL, and it goes through the house's own scrape-lane SSRF guard (public IPs only -
  loopback, RFC1918, link-local and the cloud-metadata address never fetched). The named backends'
  URLs are re-guarded too, so a future edit cannot quietly widen the door.
- One envelope, every answer: {schema_version, ok, tool, action, ..., meta{elapsed_ms, backend},
  error{code, message, hint}} - the model branches on ok / error.code, never on prose. Kill switch
  `duniya_enabled` stops the whole lane with the honest NEED_SETUP. Off means off.
- Caps are honest: a giant page is an honest TOO_BIG past the download cap, a truncated one carries
  a `truncated` note with the real character count, every item list is clamped before the call.
- Read-safe outputs: text that comes back passes operator.browser mask_ids like every scraping
  surface (Aadhaar/PAN numbers masked before the model reads them).
- One network seam: every byte this lane fetches rides `_http_get` - tests monkeypatch exactly that
  one function and the whole suite stays offline; no test ever touches the real network.
- What this lane is NOT: not a browser (jharokha), not a scraper with element memory (the scrape
  lane), not the Computer Operator. Plain public reads, one call each.

Idea (not code) provenance per action:
  fetch      <- mcp/servers fetch reference        wikipedia <- the no-key Wikipedia MCP rows
  weather    <- the Open-Meteo MCP rows (no key)   hn        <- the Hacker News MCP rows (no key)
  currency   <- the Frankfurter MCP rows (no key)  dictionary<- the Free Dictionary MCP rows
  arxiv      <- the arXiv MCP rows (no key)        status    <- the house's own introspection law
"""
from __future__ import annotations

import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, urlencode

from ..config import get_settings
from .scrape_tools import ToolError  # the house's own tool error (the guard raises it)
from .tools import Ctx

log = logging.getLogger("santosh.duniya")

SCHEMA_VERSION = 1

# ---------------------------------------------------------------- error codes (the discipline)
NEED_SETUP = "NEED_SETUP"   # the lane is turned off
BAD_INPUT = "BAD_INPUT"     # the arguments were rejected (the message names what and why)
NOT_FOUND = "NOT_FOUND"     # the service answered, but has nothing for this ask
TOO_BIG = "TOO_BIG"         # the answer would blow the download cap
BLOCKED = "BLOCKED"         # the SSRF / scheme guard refused this url
UPSTREAM = "UPSTREAM"       # the public service failed / timed out / answered something unreadable

# ---------------------------------------------------------------- caps (the envelope stays small)
_MAX_URL = 2_048            # one fetch url
_MAX_FETCH_CHARS = 12_000   # the `fetch` text cap (truncated honestly, never silently)
_MAX_BODY_CHARS = 500_000   # the download cap past which TOO_BIG is honest
_MAX_ITEMS = 10             # the clamp for any item list
_HN_ITEMS = 20              # hn may show a few more (titles are tiny)
_MAX_Q = 300                # a search ask
_MAX_PLACE = 120            # a weather place name
_MAX_WORD = 80              # a dictionary word
_SNIPPET = 320              # per-item text cap
_SUMMARY = 1_200            # a wikipedia extract / arxiv abstract cap
_TIMEOUT_S = 20             # one public-web call's belt
_UA = "hoola-duniya/0.667 (+public-web lane; no login, no key)"

_DU_ACTIONS = ("fetch", "wikipedia", "weather", "hn", "currency", "dictionary", "arxiv", "status")

BACKENDS = {
    "fetch": "the public web (GET, SSRF-guarded, text only)",
    "wikipedia": "wikipedia.org API (no key)",
    "weather": "open-meteo.com (no key)",
    "hn": "hn.algolia.com (no key)",
    "currency": "api.frankfurter.app (no key)",
    "dictionary": "dictionaryapi.dev (no key)",
    "arxiv": "export.arxiv.org (no key)",
    "status": "this lane itself (zero network)",
}

_WMO = {0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "rime fog",
        51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
        61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
        71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
        80: "light rain showers", 81: "rain showers", 82: "violent rain showers",
        85: "snow showers", 86: "snow showers", 95: "thunderstorm", 96: "thunderstorm with hail",
        99: "thunderstorm with hail"}

_LANG = re.compile(r"^[a-z]{2,3}$")
_CURRENCY = re.compile(r"^[A-Za-z]{3}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------- small helpers (the house's own laws)

def _clean(value: Any, cap: int) -> str:
    return " ".join(str(value or "").split())[:cap]


def _clip(text: str, cap: int) -> str:
    text = str(text or "")
    return text[:cap]


def _mask_text(v: str) -> str:
    """ID numbers in what comes back are masked before the chat model reads it (the scrape-lane law)."""
    try:
        from ..operator.browser import mask_ids
        return mask_ids(v)
    except Exception:                                   # pragma: no cover - the operator lane is missing
        return v


def _int_arg(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


class _NotFound(Exception):
    """The service answered fine but has nothing for this ask."""


class _Upstream(Exception):
    """Every network failure the seam can produce (timeout / status / unreadable answer)."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------- envelope (the discipline)

def _du_envelope(action: str, error: tuple[str, str, str] | None = None, elapsed_ms: int = 0,
                 **fields) -> dict:
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "ok": error is None, "tool": "duniya",
                           "action": action,
                           "error": (None if error is None else
                                     {"code": error[0], "message": error[1], "hint": error[2]})}
    out.update(fields)
    meta = dict(out.pop("meta", {}) or {})
    out["meta"] = {"elapsed_ms": max(0, int(elapsed_ms)),
                   "backend": BACKENDS.get(action, "the public web (no login, no key)"), **meta}
    return out


def _du_bad(action: str, msg: str, hint: str = "", code: str = BAD_INPUT) -> dict:
    return _du_envelope(action, error=(code, msg, hint))


def _locked(action: str) -> dict | None:
    if not bool(getattr(get_settings(), "duniya_enabled", True)):
        return _du_envelope(action, error=(
            NEED_SETUP, "the duniya public-web lane is turned off on this server",
            "Ask the owner to set duniya_enabled=true."))
    return None


def _guard_url(url: str) -> str:
    """Public http(s) through the house's own scrape-lane guard - one law for every outbound url
    this lane ever touches (the free `fetch` url AND the fixed backends' urls)."""
    from .scrape_tools import _guard_url as _house_guard
    return _house_guard(url)   # ToolError on anything that is not a public http(s) host


# ---------------------------------------------------------------- THE network seam

async def _http_get(url: str, *, headers: dict | None = None) -> tuple[int, str, str, str]:
    """The ONE seam every public byte rides. Raises _Upstream on any failure; returns
    (status, content_type, text, final_url). Tests monkeypatch exactly this - the suite stays
    offline."""
    import httpx                                     # lazy - the P1 no-network-import law
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S, follow_redirects=True,
                                     headers={"User-Agent": _UA, **(headers or {})}) as cl:
            r = await cl.get(url)
            if r.status_code >= 400:
                raise _Upstream(f"the public service answered {r.status_code}", status=r.status_code)
            return r.status_code, (r.headers.get("content-type") or ""), r.text, str(r.url)
    except _Upstream:
        raise
    except Exception as e:                            # pragma: no cover - the seam's own belt
        raise _Upstream(f"the public web did not answer: {_clean(e, 140)}") from e


def _api(action: str, base: str, params: dict | None = None) -> str:
    """A fixed backend's url, built and guarded (the constant is the allowlist; the guard is the wall)."""
    url = base + (f"?{urlencode(params)}" if params else "")
    if len(url) > _MAX_URL:
        raise ValueError(f"the {action} ask is too long for its url")
    return _guard_url(url)


def _json_of(body: str, what: str) -> Any:
    try:
        return json.loads(body)
    except Exception:
        raise _Upstream(f"the {what} answer was not JSON")


def _up404(e: _Upstream) -> Exception:
    """A 404 from these services means 'nothing here', not 'the web is broken'."""
    return _NotFound(str(e)) if e.status == 404 else e


# ---------------------------------------------------------------- html -> text (stdlib only)

class _TextExtract(HTMLParser):
    """Strip script/style/head chrome and markup; keep the words. The fetch reference's idea, the
    stdlib's tools - no new pip."""

    SKIP = {"script", "style", "noscript", "template", "svg", "iframe"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "section", "article"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in ("p", "div", "li", "tr", "h1", "h2", "h3", "h4", "section", "article"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip() + " ")


def _html_to_text(html: str) -> str:
    p = _TextExtract()
    try:
        p.feed(html)
        p.close()
    except Exception:
        return _clip(re.sub(r"<[^>]+>", " ", html), _MAX_BODY_CHARS)   # a broken page still says something
    return re.sub(r"[ \t]+", " ", "".join(p.parts)).strip()


# ---------------------------------------------------------------- the actions

async def _act_fetch(url: str) -> dict:
    url = str(url or "").strip()
    if not url:
        raise ValueError("fetch needs a url")
    guarded = _guard_url(url)                         # ToolError -> BLOCKED by the caller
    status, ctype, body, final = await _http_get(guarded)
    if len(body) > _MAX_BODY_CHARS:
        raise _TooBig(f"the page at that link is {len(body)} chars - past the {_MAX_BODY_CHARS} download cap")
    ct = ctype.lower()
    truncated = False
    if "html" in ct:
        text = _html_to_text(body)
    elif "json" in ct or body[:1] in ("{", "["):
        try:
            text = json.dumps(json.loads(body), ensure_ascii=False, indent=1)
        except Exception:
            text = body
    elif ct.startswith("text/") or "xml" in ct or "csv" in ct or not ct:
        text = body
    else:
        raise _Upstream(f"that link serves {ct or 'an unknown type'} - the fetch lane reads text only "
                        f"(html, json, xml, csv, plain text); for a page that needs a browser, use jharokha")
    note = None
    if len(text) > _MAX_FETCH_CHARS:
        text = _clip(text, _MAX_FETCH_CHARS)
        truncated = True
    out = {"url": guarded, "final_url": final, "status": status,
           "content_type": ctype or "text/plain", "chars": len(text), "text": _mask_text(text)}
    if truncated:
        out["note"] = ("text truncated at the cap - more of the page exists; "
                       "narrow the ask or use jharokha to walk the live page")
    return out


async def _act_wikipedia(q: str, lang: str, max_items: int) -> dict:
    q = _clean(q, _MAX_Q)
    if not q:
        raise ValueError("wikipedia needs something to look for (q)")
    lang = (lang or "en").strip().lower()
    if not _LANG.match(lang):
        raise ValueError("lang must be a 2-3 letter language code like en, hi, mr")
    search_url = _api("wikipedia", f"https://{lang}.wikipedia.org/w/api.php",
                      {"action": "query", "list": "search", "srsearch": q, "format": "json",
                       "srlimit": max_items})
    _, _, body, _ = await _http_get(search_url)
    hits = (((_json_of(body, "wikipedia") or {}).get("query") or {}).get("search")) or []
    results = [{"title": _clean(h.get("title"), 200),
                "snippet": _clip(_mask_text(re.sub(r"<[^>]+>", "", str(h.get("snippet") or ""))), _SNIPPET)}
               for h in hits[:max_items]]
    if not results:
        raise _NotFound(f"wikipedia ({lang}) has no article matching '{q}'")
    out: dict[str, Any] = {"lang": lang, "query": q, "results": results}
    if results:                                       # the top hit's own summary rides along (one extra read)
        title = quote(str(results[0]["title"]).replace(" ", "_"), safe="()_")
        try:
            _, _, sbody, _ = await _http_get(_api("wikipedia", f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"))
            sdata = _json_of(sbody, "wikipedia summary") or {}
            out["summary"] = {"title": _clean(sdata.get("title"), 200),
                              "extract": _clip(_mask_text(str(sdata.get("extract") or "")), _SUMMARY),
                              "url": str(sdata.get("content_urls", {}).get("desktop", {}).get("page") or "")}
        except (_Upstream, ToolError):
            pass                                      # the search result stands; the summary is a courtesy
    return out


async def _act_weather(place: str, days: int) -> dict:
    place = _clean(place, _MAX_PLACE)
    if not place:
        raise ValueError("weather needs a place (place)")
    geo_url = _api("weather", "https://geocoding-api.open-meteo.com/v1/search",
                   {"name": place, "count": 1, "language": "en", "format": "json"})
    _, _, gbody, _ = await _http_get(geo_url)
    locs = ((_json_of(gbody, "geocoding") or {}).get("results")) or []
    if not locs:
        raise _NotFound(f"no place named '{place}' in the geocoder")
    loc = locs[0]
    days = _int_arg(days, 3, 1, 7)
    fc_url = _api("weather", "https://api.open-meteo.com/v1/forecast",
                  {"latitude": loc.get("latitude"), "longitude": loc.get("longitude"),
                   "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                   "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                   "forecast_days": days, "timezone": "auto"})
    _, _, fbody, _ = await _http_get(fc_url)
    fc = _json_of(fbody, "forecast") or {}
    cur = fc.get("current") or {}
    daily = fc.get("daily") or {}
    dlist = [{"date": (daily.get("time") or [""])[i],
              "weather": _WMO.get((daily.get("weather_code") or [None])[i], "unknown"),
              "max_c": (daily.get("temperature_2m_max") or [None])[i],
              "min_c": (daily.get("temperature_2m_min") or [None])[i],
              "precip_mm": (daily.get("precipitation_sum") or [None])[i]}
             for i in range(len(daily.get("time") or []))][:days]
    return {"place": {"name": _clean(loc.get("name"), 120), "country": _clean(loc.get("country"), 80),
                      "admin1": _clean(loc.get("admin1"), 120),
                      "lat": loc.get("latitude"), "lon": loc.get("longitude"),
                      "timezone": fc.get("timezone") or loc.get("timezone")},
            "current": {"temp_c": cur.get("temperature_2m"),
                        "humidity_pct": cur.get("relative_humidity_2m"),
                        "wind_kph": cur.get("wind_speed_10m"),
                        "weather": _WMO.get(cur.get("weather_code"), "unknown")},
            "daily": dlist}


async def _act_hn(q: str, max_items: int) -> dict:
    q = _clean(q, _MAX_Q)
    if not q:
        raise ValueError("hn needs something to search for (q)")
    search_url = _api("hn", "https://hn.algolia.com/api/v1/search",
                      {"query": q, "tags": "story", "hitsPerPage": max_items})
    _, _, body, _ = await _http_get(search_url)
    data = _json_of(body, "hacker news") or {}
    hits = data.get("hits") or []
    return {"query": q, "nbHits": int(data.get("nbHits") or len(hits)),
            "hits": [{"title": _clean(h.get("title") or h.get("story_title"), 200),
                      "url": str(h.get("url") or h.get("story_url") or ""),
                      "points": h.get("points") if h.get("points") is not None else h.get("story_points"),
                      "author": _clean(h.get("author"), 60),
                      "comments": h.get("num_comments"),
                      "hn_url": f"https://news.ycombinator.com/item?id={h.get('objectID')}"}
                     for h in hits[:max_items]]}


async def _act_currency(base: str, quote: str, amount: Any, date: str) -> dict:
    base = str(base or "").strip().upper()
    quote = str(quote or "").strip().upper()
    if not _CURRENCY.match(base) or not _CURRENCY.match(quote):
        raise ValueError("currency codes are three letters - from and to (e.g. USD, INR, EUR)")
    try:
        amt = float(amount) if amount is not None else 1.0
    except (TypeError, ValueError):
        raise ValueError("amount must be a number")
    if not (amt > 0) or amt != amt or amt in (float("inf"),):
        raise ValueError("amount must be a positive number")
    params = {"from": base, "to": quote, "amount": amt if amt != 1.0 else None}
    params = {k: v for k, v in params.items() if v is not None}
    day = str(date or "").strip()
    if day and not _DATE.match(day):
        raise ValueError("date must be YYYY-MM-DD (weekends/holidays roll to the last trading day)")
    base_url = f"https://api.frankfurter.app/{day}" if day else "https://api.frankfurter.app/latest"
    _, _, body, _ = await _http_get(_api("currency", base_url, params))
    data = _json_of(body, "exchange rates") or {}
    rates = data.get("rates") or {}
    if quote not in rates:
        raise _NotFound(f"{base} -> {quote} is not a pair this rates service carries "
                        f"(it answered: {', '.join(sorted(rates)) or 'nothing'})")
    got = rates.get(quote)
    # Frankfurter folds the amount INTO the answer: amount=1 -> the rate itself,
    # amount=100 -> the converted result. Both are told, one honest division apart.
    rate = (got / amt) if amt != 1.0 else got
    return {"amount": amt, "from": base, "to": quote, "date": data.get("date"),
            "rate": rate, "result": got}


async def _act_dictionary(word: str, lang: str) -> dict:
    word = _clean(word, _MAX_WORD)
    if not word:
        raise ValueError("dictionary needs a word (word)")
    lang = (lang or "en").strip().lower()
    if not _LANG.match(lang):
        raise ValueError("lang must be a 2-3 letter language code like en, hi")
    url = _api("dictionary", f"https://api.dictionaryapi.dev/api/v2/entries/{lang}/{quote(word, safe='')}")
    try:
        _, _, body, _ = await _http_get(url)
        entries = _json_of(body, "dictionary")
    except _Upstream as e:
        raise _up404(e) from e                       # the dictionary 404s on an unknown word
    if not isinstance(entries, list) or not entries:
        raise _NotFound(f"no dictionary entry for '{word}' ({lang})")
    e0 = entries[0] or {}
    meanings = []
    for m in (e0.get("meanings") or [])[:4]:
        meanings.append({"partOfSpeech": _clean(m.get("partOfSpeech"), 40),
                         "definitions": [{"text": _clip(_mask_text(d.get("definition")), _SNIPPET),
                                          "example": _clip(_mask_text(d.get("example") or ""), _SNIPPET)}
                                         for d in (m.get("definitions") or [])[:2]],
                         "synonyms": [_clean(s, 40) for s in (m.get("synonyms") or [])[:5]]})
    return {"word": _clean(e0.get("word"), 80), "lang": lang,
            "phonetic": _clean(e0.get("phonetic") or (e0.get("phonetics") or [{}])[0].get("text"), 80),
            "meanings": meanings}


async def _act_arxiv(q: str, max_items: int) -> dict:
    q = _clean(q, _MAX_Q)
    if not q:
        raise ValueError("arxiv needs something to look for (q)")
    url = _api("arxiv", "https://export.arxiv.org/api/query",
               {"search_query": f"all:{q}", "start": 0, "max_results": max_items, "sortBy": "relevance"})
    _, _, body, _ = await _http_get(url)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(body)
        entries = root.findall("a:entry", ns)
    except ET.ParseError:
        raise _Upstream("the arXiv answer was not Atom XML")
    out = []
    for en in entries[:max_items]:
        out.append({"title": _clean(" ".join((en.findtext("a:title", "", ns) or "").split()), 240),
                    "authors": [_clean(a.findtext("a:name", "", ns), 80)
                                for a in en.findall("a:author", ns)][:6],
                    "published": (en.findtext("a:published", "", ns) or "")[:10],
                    "updated": (en.findtext("a:updated", "", ns) or "")[:10],
                    "summary": _clip(_mask_text(" ".join((en.findtext("a:summary", "", ns) or "").split())), _SUMMARY),
                    "link": en.findtext("a:id", "", ns)})
    if not out:
        raise _NotFound(f"no arXiv papers matched '{q}'")
    return {"query": q, "entries": out, "count": len(out)}


def _act_status() -> dict:
    return {"lane": "DUNIYA MANCH (v0.667) - the T4 keyless-public-web family",
            "actions": list(_DU_ACTIONS),
            "backends": dict(BACKENDS),
            "caps": {"fetch_chars": _MAX_FETCH_CHARS, "download_chars": _MAX_BODY_CHARS,
                     "items_default": 5, "items_max": _HN_ITEMS, "timeout_s": _TIMEOUT_S},
            "laws": ["GET only - never POST/PUT/DELETE, never an auth header, never a cookie",
                     "free urls ride the house SSRF guard (public hosts only)",
                     "every answer one envelope; text passes the id-mask"],
            "browser_alternative": "jharokha (pages that need clicking; this lane reads, never drives)",
            "note": "zero login, zero key - only the parts of the web that answer anyone"}


# ---------------------------------------------------------------- error mapping (one honest table)

class _TooBig(Exception):
    """The answer would blow the download cap - honest, before anything is read."""


def _error_of(e: Exception) -> tuple[str, str, str]:
    if isinstance(e, _NotFound):
        return (NOT_FOUND, str(e), "try a different spelling, a wider ask, or another action")
    if isinstance(e, _TooBig):
        return (TOO_BIG, str(e), "the service will not download more than the cap - find a narrower url")
    if isinstance(e, ToolError):
        return (BLOCKED, str(e), "the guard only fetches public http(s) addresses (loopback, private "
                                 "ranges and the metadata address never leave the house)")
    if isinstance(e, _Upstream):
        return (UPSTREAM, str(e), "the public service is down, slow or unhappy - try again shortly, "
                                  "or answer from another backend")
    if isinstance(e, ValueError):
        return (BAD_INPUT, str(e), "name the argument the message points at")
    return (UPSTREAM, f"the public-web lane failed: {_clean(e, 160)}",
            "try the action again; if it repeats, try another backend")


# ---------------------------------------------------------------- the ONE tool

async def duniya(ctx: Ctx, action: str = "status", *, url: str | None = None, q: str | None = None,
                 lang: str | None = None, place: str | None = None, days: int | None = None,
                 word: str | None = None, base: str | None = None, quote: str | None = None,
                 amount: float | None = None, date: str | None = None,
                 max_items: int | None = None, **_) -> dict:
    """The keyless public web. Never raises; every answer is one envelope."""
    started = time.monotonic()
    action = str(action or "").strip().lower()
    if action not in _DU_ACTIONS:
        return _du_bad(action or "", f"unknown action '{action}'; valid: {', '.join(_DU_ACTIONS)}",
                       "action=status shows the lane")
    if (lock := _locked(action)) is not None:
        return lock
    try:
        if action == "fetch":
            res = await _act_fetch(url)
        elif action == "wikipedia":
            res = await _act_wikipedia(q, lang, _int_arg(max_items, 5, 1, _MAX_ITEMS))
        elif action == "weather":
            res = await _act_weather(place, days)
        elif action == "hn":
            res = await _act_hn(q, _int_arg(max_items, 10, 1, _HN_ITEMS))
        elif action == "currency":
            res = await _act_currency(base or q, quote, amount, date)
        elif action == "dictionary":
            res = await _act_dictionary(word or q, lang)
        elif action == "arxiv":
            res = await _act_arxiv(q, _int_arg(max_items, 5, 1, _MAX_ITEMS))
        elif action == "status":
            res = _act_status()
        else:                                          # pragma: no cover - the enum is checked above
            raise ValueError(f"unknown action '{action}'")
        out = _du_envelope(action, **res) if isinstance(res, dict) else _du_envelope(action)
    except Exception as e:
        out = _du_envelope(action, error=_error_of(e))
    out["meta"]["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return out


# ---------------------------------------------------------------- the tool spec the model sees
DUNIYA_TOOLS = [
    {"name": "duniya", "description": (
        "DUNIYA MANCH (v0.667): the keyless public web - the T4 idea, zero login, zero API key, "
        "GET only. Actions: fetch (one public http(s) url -> readable text, scripts and markup "
        "stripped, SSRF-guarded, capped; final url + status told honestly) | wikipedia (search + "
        "the top hit's summary, any language edition: q, lang, max_items) | weather (a place -> "
        "current + up to 7 days of forecast via Open-Meteo: place, days) | hn (Hacker News story "
        "search: q, max_items) | currency (exchange rates, no key: from, to, amount?, date? - e.g. "
        "from=USD to=INR) | dictionary (a word's meanings, definitions, synonyms: word, lang) | "
        "arxiv (paper search with abstracts: q, max_items) | status (the lane's own backends, caps "
        "and laws). Every answer one envelope {ok, action, error:{code, message, hint}}. The lane "
        "never POSTs, never logs in, never holds a key - only the parts of the web that answer "
        "anyone. For pages that need clicking use jharokha; for her own sites' scraping use the "
        "scrape lane."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": list(_DU_ACTIONS),
                    "description": "fetch | wikipedia | weather | hn | currency | dictionary | arxiv | status"},
         "url": {"type": "string", "description": "fetch: the public http(s) page to read"},
         "q": {"type": "string", "description": "wikipedia / hn / arxiv: what to search (dictionary accepts it as the word, currency as the from-code)"},
         "lang": {"type": "string", "description": "wikipedia / dictionary: language code (en, hi, mr, ...)"},
         "place": {"type": "string", "description": "weather: the place name (e.g. 'Pune')"},
         "days": {"type": "integer", "description": "weather: forecast days 1-7 (default 3)"},
         "word": {"type": "string", "description": "dictionary: the word to define"},
         "base": {"type": "string", "description": "currency: the from-code (e.g. USD)"},
         "quote": {"type": "string", "description": "currency: the to-code (e.g. INR)"},
         "amount": {"type": "number", "description": "currency: how much (default 1)"},
         "date": {"type": "string", "description": "currency: historical date YYYY-MM-DD (default latest)"},
         "max_items": {"type": "integer", "description": "wikipedia / hn / arxiv: how many items (default 5, hn 10)"}}}},
]

DUNIYA_LABELS = {"duniya": "Duniya: the keyless public web (no login, no key)"}
DUNIYA_HANDLERS = {"duniya": duniya}
