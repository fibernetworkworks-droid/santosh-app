"""v0.273 INDIAMART: live B2B product, price and supplier search from IndiaMART's own MCP server.

Official route only: IndiaMART hosts the endpoint itself (https://imgpt.indiamart.com/mcp, streamable HTTP, server
"indiamart-marketplace"). It needs no sign-in and holds no session, so every call is one JSON-RPC POST. It offers
three tools; Hoola uses two of them, both read-only:
  search_products(query, search_term, city, brand, specifications, min_price, max_price, biztype)
  get_product_detail(displayid)
The third (log_client_event) is their widget's own logging ("Not for model use") and is never called from here.

What comes back is the SELLERS' text (titles, descriptions, specs): data, never instructions. Hoola never places an
order or contacts a seller from here - the seller's phone is shown, the call is her tap.

Images: the console's CSP allows only its own origin, so pictures go through `img_url()` -> /api/indiamart/img, a
signed proxy that fetches IndiaMART's image hosts only (no open proxy). The phone loads the direct image URL.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
import statistics
import time
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import httpx

from .config import get_settings

log = logging.getLogger("santosh.indiamart")

MCP_URL = "https://imgpt.indiamart.com/mcp"
PROTOCOL = "2025-06-18"
BIZTYPES = ("manufacturer", "exporter", "wholesaler", "retailer")
MAX_CITIES = 5
SEARCH_TTL = 15 * 60          # prices move; a quarter hour keeps a conversation fast without going stale
DETAIL_TTL = 60 * 60
IMG_MAX = 4 * 1024 * 1024

_CACHE: dict[str, tuple[float, Any]] = {}
_PDP: dict[str, str] = {}      # product id -> its IndiaMART page (from the search that found it)
_CACHE_MAX = 400
STATS: dict[str, int] = {"calls": 0, "cached": 0, "errors": 0}


class IndiaMartError(Exception):
    pass


# ---------------------------------------------------------------- MCP transport
def _url() -> str:
    return (getattr(get_settings(), "indiamart_mcp_url", "") or MCP_URL).strip()


def _parse(text: str, ctype: str) -> dict[str, Any]:
    """The server answers as SSE (`event: message` / `data: {...}`) or plain JSON."""
    if "event-stream" in ctype or text.lstrip().startswith(("event:", "data:")):
        datas = [ln[5:].strip() for ln in text.splitlines() if ln.startswith("data:")]
        for d in reversed(datas):
            try:
                msg = json.loads(d)
            except ValueError:
                continue
            if isinstance(msg, dict) and ("result" in msg or "error" in msg):
                return msg
        raise IndiaMartError("IndiaMART ka jawab samajh nahi aaya.")
    try:
        return json.loads(text)
    except ValueError:
        raise IndiaMartError("IndiaMART ka jawab samajh nahi aaya.")


async def _rpc(method: str, params: dict[str, Any], timeout: float = 40.0) -> dict[str, Any]:
    body = {"jsonrpc": "2.0", "id": int(time.time() * 1000) % 1_000_000_000, "method": method, "params": params}
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": PROTOCOL, "User-Agent": "Hoola/1.0 (+https://hoola.ainewtika.com)"}
    STATS["calls"] += 1
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(_url(), json=body, headers=headers)
    except httpx.HTTPError as e:
        STATS["errors"] += 1
        raise IndiaMartError("IndiaMART abhi jawab nahi de raha (network). Thodi der mein phir try karte hain.") from e
    if r.status_code >= 400:
        STATS["errors"] += 1
        raise IndiaMartError(f"IndiaMART ne mana kiya (HTTP {r.status_code}). Thodi der mein phir try karte hain.")
    msg = _parse(r.text, r.headers.get("content-type", ""))
    if msg.get("error"):
        STATS["errors"] += 1
        raise IndiaMartError("IndiaMART: " + str((msg["error"] or {}).get("message") or "error")[:200])
    return msg.get("result") or {}


async def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name not in ("search_products", "get_product_detail"):
        raise IndiaMartError("This IndiaMART tool is not used by Hoola.")
    res = await _rpc("tools/call", {"name": name, "arguments": args})
    if res.get("isError"):
        txt = " ".join(c.get("text", "") for c in res.get("content") or [] if isinstance(c, dict))
        raise IndiaMartError("IndiaMART: " + (txt.strip() or "search nahi ho saka")[:200])
    sc = res.get("structuredContent")
    if isinstance(sc, dict):
        return sc
    for c in res.get("content") or []:          # older servers put the JSON in a text part
        if isinstance(c, dict) and c.get("type") == "text":
            try:
                v = json.loads(c.get("text") or "")
                if isinstance(v, dict):
                    return v
            except ValueError:
                pass
    return {}


def _cache_get(key: str, ttl: int) -> Any:
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < ttl:
        STATS["cached"] += 1
        return hit[1]
    return None


def _cache_put(key: str, val: Any) -> None:
    if len(_CACHE) >= _CACHE_MAX:
        for k, _ in sorted(_CACHE.items(), key=lambda kv: kv[1][0])[: _CACHE_MAX // 4]:
            _CACHE.pop(k, None)
    _CACHE[key] = (time.time(), val)


# ---------------------------------------------------------------- images
def _sig(u: str) -> str:
    st = get_settings()
    key = st.secret_key or "santosh-dev-secret"
    return hmac.new(f"indiamart-img:{key}".encode(), u.encode(), hashlib.sha256).hexdigest()[:32]


def image_host_ok(u: str) -> bool:
    try:
        p = urlparse(u)
    except ValueError:
        return False
    h = (p.hostname or "").lower()
    return p.scheme == "https" and (h == "imimg.com" or h.endswith(".imimg.com") or h == "imgpt.indiamart.com"
                                    or h.endswith(".indiamart.com"))


def direct_image(u: str) -> str:
    """IndiaMART wraps pictures in its own /api/image-proxy?url=<imimg url>; the phone loads the real file."""
    u = str(u or "").strip()
    if not u:
        return ""
    try:
        p = urlparse(u)
        if p.path.endswith("/image-proxy"):
            inner = (parse_qs(p.query).get("url") or [""])[0]
            if inner and image_host_ok(inner):
                return inner
    except ValueError:
        return ""
    return u if image_host_ok(u) else ""


def img_url(u: str) -> str:
    u = direct_image(u)
    return f"/api/indiamart/img?u={quote(u, safe='')}&s={_sig(u)}" if u else ""


def img_ok(u: str, s: str) -> bool:
    return bool(u) and image_host_ok(u) and hmac.compare_digest(_sig(u), str(s or ""))


async def fetch_image(u: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as c:
        r = await c.get(u, headers={"User-Agent": "Hoola/1.0", "Accept": "image/*"})
    ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
    if r.status_code != 200 or not ctype.startswith("image/") or ctype == "image/svg+xml" or len(r.content) > IMG_MAX:
        raise IndiaMartError("image not available")
    return r.content, ctype


# ---------------------------------------------------------------- shaping
def _s(v: Any, n: int = 300) -> str:
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip()[:n]


def _specs(isq: Any, n: int = 14) -> list[list[str]]:
    out: list[list[str]] = []
    for x in isq if isinstance(isq, list) else []:
        k, _, v = str(x).partition("==")
        if k.strip() and v.strip():
            out.append([_s(k, 60), _s(v, 120)])
        if len(out) >= n:
            break
    return out


def _unit(price: str) -> str:
    m = re.search(r"/\s*([A-Za-z][\w .]{0,24})$", price or "")
    return m.group(1).strip() if m else ""


def _num(v: Any) -> float | None:
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _product(p: dict[str, Any], wanted_city: str = "") -> dict[str, Any]:
    price = _s(p.get("price"), 60)
    image = direct_image(p.get("thumbnail") or "")
    city = _s(p.get("city") or p.get("location"), 60)
    return {
        "id": _s(p.get("id"), 40),
        "title": _s(p.get("title"), 160),
        "price": price or "Price on request",
        "price_value": _num(p.get("priceValue")),
        "unit": _unit(price),
        "image": image,
        "img": img_url(image),
        "brand": _s(p.get("brand"), 60),
        "category": _s(p.get("category"), 80),
        "company": _s(p.get("companyname"), 120),
        "city": city,
        "location": _s(p.get("location"), 80),
        "in_city": bool(wanted_city) and city.lower() == wanted_city.lower(),
        "phone": re.sub(r"[^\d+]", "", str(p.get("phone") or ""))[:16],
        "specs": _specs(p.get("isq"), 8),
        "moq": _s(p.get("moq"), 20),
        "moq_unit": _s(p.get("moqUnit"), 24),
        "rating": _s(p.get("rating"), 8),
        "rating_count": _s(p.get("ratingCount"), 10),
        "gst_verified": bool(p.get("gstVerified")),
        "trust_seal": bool(p.get("trustSeal")),
        "member_since": _s(p.get("memberSinceDisplay"), 40),
        "response_rate": _s(p.get("responseRate"), 10),
        "url": _s(p.get("pdpurl"), 400),
        "description": _s(p.get("description"), 300),
    }


def price_stats(products: list[dict[str, Any]]) -> dict[str, Any]:
    """The price band in the MAIN unit only: a per-tonne listing must not stretch a per-bag band."""
    priced = [p for p in products if p.get("price_value")]
    if not priced:
        return {"priced": 0}
    units = [(p.get("unit") or "").lower() for p in priced]
    main = max(set(units), key=lambda u: (units.count(u), u != ""))
    same = [p for p in priced if (p.get("unit") or "").lower() == main] or priced
    vals = sorted(p["price_value"] for p in same)
    unit = next((p["unit"] for p in same if p.get("unit")), "")
    return {"priced": len(vals), "min": vals[0], "max": vals[-1], "median": statistics.median(vals), "unit": unit,
            "other_units": len(priced) - len(same)}


def by_city(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """City -> how many listings and the price band, cheapest city first."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in products:
        groups.setdefault(p.get("city") or "Other", []).append(p)
    rows = [{"city": c, "count": len(ps), **price_stats(ps)} for c, ps in groups.items()]
    rows.sort(key=lambda r: (r.get("min") is None, r.get("min") or 0, -r["count"]))
    return rows


def rupees(v: Any) -> str:
    f = _num(v)
    if f is None:
        return ""
    n = int(round(f))
    s = str(n)
    if len(s) > 3:          # Indian grouping 12,34,567
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = head + "," + tail
    return "₹" + s + (f"{f - n:.2f}"[1:] if abs(f - n) >= 0.005 else "")


# ---------------------------------------------------------------- public
def _args(search_term: str, query: str, city: str, brand: str, specifications: Any, min_price: Any,
          max_price: Any, biztype: str) -> dict[str, Any]:
    a: dict[str, Any] = {"query": _s(query or search_term, 300) or _s(search_term, 120),
                         "search_term": _s(search_term, 120)}
    if _s(city, 40):
        a["city"] = _s(city, 40)
    if _s(brand, 60):
        a["brand"] = _s(brand, 60)
    if isinstance(specifications, dict):
        sp = {_s(k, 40): _s(v, 60) for k, v in list(specifications.items())[:8] if _s(k, 40) and _s(v, 60)}
        if sp:
            a["specifications"] = sp
    lo, hi = _num(min_price), _num(max_price)
    if lo:
        a["min_price"] = lo
    if hi:
        a["max_price"] = hi
    if lo and hi and lo > hi:
        a["min_price"], a["max_price"] = hi, lo
    bt = _s(biztype, 20).lower()
    if bt in BIZTYPES:
        a["biztype"] = bt
    return a


async def search(search_term: str, query: str = "", city: str = "", brand: str = "", specifications: Any = None,
                 min_price: Any = None, max_price: Any = None, biztype: str = "") -> dict[str, Any]:
    if not _s(search_term):
        raise IndiaMartError("Kaunsa product dhoondhna hai? Naam bataiye (jaise 'cement', 'LED bulb').")
    a = _args(search_term, query, city, brand, specifications, min_price, max_price, biztype)
    key = "s:" + json.dumps({k: v for k, v in a.items() if k != "query"}, sort_keys=True, ensure_ascii=False).lower()
    hit = _cache_get(key, SEARCH_TTL)
    if hit is not None:
        return hit
    raw = await call_tool("search_products", a)
    products = [_product(p, a.get("city", "")) for p in raw.get("products") or [] if isinstance(p, dict) and p.get("id")]
    for p in products:
        if p["url"].startswith("https://") and len(_PDP) < 5000:
            _PDP[p["id"]] = p["url"]
    out = {"search_term": raw.get("search_term") or a["search_term"], "city": a.get("city", ""),
           "filters": raw.get("filters") or {}, "exact": raw.get("exact_filter_match"),
           "products": products, "stats": price_stats(products), "at": raw.get("timestamp") or ""}
    _cache_put(key, out)
    return out


async def search_cities(search_term: str, cities: list[str], **kw: Any) -> list[dict[str, Any]]:
    """One search per city, side by side (IndiaMART ranks toward one city per call)."""
    seen: list[str] = []
    for c in cities:
        c = _s(c, 40)
        if c and c.lower() not in [x.lower() for x in seen]:
            seen.append(c)
    seen = seen[:MAX_CITIES]
    res = await asyncio.gather(*(search(search_term, city=c, **kw) for c in seen), return_exceptions=True)
    out = []
    for c, r in zip(seen, res):
        if isinstance(r, BaseException):
            out.append({"city": c, "error": str(r)[:200], "products": [], "stats": {"priced": 0}})
        else:
            out.append(r)
    return out


async def detail(displayid: str) -> dict[str, Any]:
    pid = re.sub(r"\D", "", str(displayid or ""))[:20]
    if not pid:
        raise IndiaMartError("Product id chahiye (IndiaMART search ke result se).")
    hit = _cache_get("d:" + pid, DETAIL_TTL)
    if hit is not None:
        return hit
    raw = (await call_tool("get_product_detail", {"displayid": pid})).get("product") or {}
    if not raw:
        raise IndiaMartError("Is product ki details IndiaMART par nahi mili.")
    price = raw.get("price") if isinstance(raw.get("price"), dict) else {}
    moq = raw.get("moq") if isinstance(raw.get("moq"), dict) else {}
    co = raw.get("company") if isinstance(raw.get("company"), dict) else {}
    ct = raw.get("contact") if isinstance(raw.get("contact"), dict) else {}
    ph = ct.get("phone") if isinstance(ct.get("phone"), dict) else {}
    cat = raw.get("category") if isinstance(raw.get("category"), dict) else {}
    lg = raw.get("logistics") if isinstance(raw.get("logistics"), dict) else {}
    images = [direct_image(u) for u in (raw.get("images") or [])[:8] if isinstance(u, str)]
    images = [u for u in images if u]
    since = _s(co.get("memberSince"), 20)[:10]
    out = {
        "id": pid, "title": _s(raw.get("title"), 200),
        "price": _s(price.get("display"), 60) or ("Price on request" if price.get("hidden") else ""),
        "unit": _unit(_s(price.get("display"), 60).replace(" / ", "/")),
        "images": images, "imgs": [img_url(u) for u in images],
        "moq": " ".join(x for x in (_s(moq.get("value"), 20), _s(moq.get("unit"), 24)) if x),
        "specs": _specs(raw.get("isq"), 24),
        "description": _s(raw.get("description"), 1200),
        "hindi_name": _s(raw.get("hindiName"), 80),
        "brochure": _s(raw.get("brochureUrl"), 400),
        "brand": _s(cat.get("brand"), 60), "category": _s(cat.get("mcat") or cat.get("group"), 80),
        "company": {"name": _s(co.get("name"), 120), "address": _s(co.get("address"), 240),
                    "city": _s(co.get("city"), 60), "state": _s(co.get("state"), 60),
                    "member_since": since, "established": _s(co.get("yearEstablished"), 8),
                    "rating": _s(co.get("rating"), 8), "quality_score": _s(co.get("qualityScore"), 6),
                    "response_rate": _s(co.get("responseRate"), 6)},
        "phone": re.sub(r"[^\d+]", "", str(ph.get("tel") or ph.get("display") or ""))[:16],
        "phone_display": _s(ph.get("display"), 30),
        "mobile_verified": bool(ct.get("mobileVerified")), "email_verified": bool(ct.get("emailVerified")),
        "delivery": _s(lg.get("deliveryTime"), 60), "packaging": _s(lg.get("packagingDetails"), 120),
        "capacity": _s(lg.get("productionCapacity"), 80), "dispatch_port": _s(lg.get("portOfDispatch"), 60),
        "price_updated": _s(lg.get("lastPriceUpdateDate"), 24),
        "url": _PDP.get(pid) or "https://dir.indiamart.com/search.mp?ss=" + quote(_s(raw.get("title"), 120)),
    }
    _cache_put("d:" + pid, out)
    return out
