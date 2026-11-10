"""v0.544.0 P4 VENDOR LANE - one licensed lead-data vendor behind the SAME leads_run job shape (the research
R6 pattern: engine behind one job, gated, priced on the bill BEFORE the run), docs/LEADS_PLAN.md sections
4 L3, 10 P4 and 12.4.

THE HONEST STATE, said plainly: no vendor is named yet. Plan section 12.4 is HER decision - "pick the licensed
lead vendor in P4: she names the vendor and the budget". Until she names one, the lane is ABSENT: it is not
offered on a plan card, and an explicit VENDOR ask is refused with the exact config named (no stub, no
pretending - a lane that pretends to run is worse than one that refuses).

THE CONTRACT (Hoola's side of it). When she names the vendor, the adapter is written to THAT vendor's OWN
documented contract (the v0.389 SACH BOLO discipline: written to the vendor's docs, never reverse-engineered).
Until then this module speaks the ONE generic JSON contract below, and the tests prove Hoola's side against a
fake that speaks it. NOT VERIFIED, said plainly: no live vendor has ever answered this code.

  AUTH      Authorization: Bearer <key>. The key only ever rides the header - never an error, never a log.
  REQUEST   POST {LEADS_VENDOR_BASE_URL}/leads/search  body {"query", "city", "max_rows"}
  RESPONSE  200 {"results": [row, ...], "cost_inr": <optional number - the vendor's OWN reported cost>}
  ROW       REQUIRED: name + source_url (the vendor's own public record page for THIS business - Hoola's
            provenance law extends to vendor rows; a row without its source is REFUSED, never stored).
            OPTIONAL: phone/mobile, website, email, address, city, state, pincode, category, rating,
            review_count, lat, lng, place_id/kgmid/cid (the identity ladder reads them like any other lane).
  PRICING   She sets LEADS_VENDOR_PRICE_PER_ROW_INR (0 = refused: a ceiling needs a price). The plan card
            prices the run BEFORE it starts (rows x price) and refuses at plan time if the estimate crosses
            LEADS_VENDOR_RUN_CAP_INR. After the run the bill uses the vendor's OWN reported cost_inr when the
            vendor gave one (and says so); otherwise it is the ESTIMATE (rows delivered x price) - and says so.

THE GATE (check), in order: named + base URL + key set; per-row price > 0; terms acked (SHE reads the vendor's
current terms and writes the vendor's name into LEADS_VENDOR_TERMS_ACK - the act is hers, nothing is assumed);
estimate within the run cap. One call per run, NEVER retried (the vendor may bill per call - the R6
never-pays-twice law)."""
from __future__ import annotations

from typing import Any

import httpx

_transport: httpx.AsyncBaseTransport | None = None      # tests plug in httpx.MockTransport (the R6 seam)

SEARCH_PATH = "/leads/search"                            # the one documented path Hoola's side calls


class VendorError(Exception):
    """A vendor call failed in a way the run card reports (never carries the key)."""


def _csv(s: str) -> set[str]:
    return {x.strip().lower() for x in str(s or "").split(",") if x.strip()}


def contract() -> dict[str, Any]:
    """The documented wire contract, for the card and the doc - the words a later session checks against."""
    return {
        "auth": "Authorization: Bearer <LEADS_VENDOR_API_KEY> - the key only rides the header, never an error or a log",
        "request": {"method": "POST", "path": SEARCH_PATH,
                    "body": {"query": "string, required", "city": "string", "max_rows": "int 1..5000"}},
        "response": {"status": 200,
                     "body": {"results": "array of row objects",
                              "cost_inr": "optional number - the vendor's OWN reported cost for this call"}},
        "row_required": {"name": "the business's name",
                         "source_url": "the vendor's own public record page for THIS business (provenance; a row "
                                       "without it is refused, never stored)"},
        "row_optional": ("phone", "mobile", "website", "email", "address", "city", "state", "pincode", "category",
                         "rating", "review_count", "lat", "lng", "place_id", "kgmid", "cid"),
        "pricing": "LEADS_VENDOR_PRICE_PER_ROW_INR priced on the plan card BEFORE the run; estimate over "
                   "LEADS_VENDOR_RUN_CAP_INR refuses at plan time; the bill uses the vendor's reported cost_inr "
                   "when given, else says ESTIMATE",
        "written_to": "the vendor's OWN documented contract once she names the vendor (plan 12.4; SACH BOLO - "
                      "never reverse-engineered). This generic contract is Hoola's side only.",
    }


def config_snapshot(st: Any = None) -> dict[str, Any]:
    """The vendor's config state for a card - booleans and numbers only, NEVER the key itself."""
    from ..config import get_settings
    st = st or get_settings()
    price = float(st.leads_vendor_price_per_row_inr or 0.0)
    return {"name": str(st.leads_vendor_name or "").strip(),
            "base_url_set": bool(str(st.leads_vendor_base_url or "").strip()),
            "key_set": bool(str(st.leads_vendor_api_key or "").strip()),
            "price_per_row_inr": price,
            "run_cap_inr": float(st.leads_vendor_run_cap_inr or 0.0),
            "terms_ack": bool(str(st.leads_vendor_name or "").strip()
                              and str(st.leads_vendor_name or "").strip().lower() in _csv(st.leads_vendor_terms_ack)),
            "contract": contract()}


def estimate_inr(planned_rows: int, st: Any = None) -> float:
    from ..config import get_settings
    st = st or get_settings()
    return round(float(st.leads_vendor_price_per_row_inr or 0.0) * max(0, int(planned_rows or 0)), 4)


def check(tenant: str, planned_rows: int, st: Any = None) -> tuple[bool, str, str]:
    """May a VENDOR run start now? -> (ok, the first reason it may not, kind). The research R6 gate, leads-shaped.
    kind 'config' = nothing ran and there is no receipt to show (the caller raises);
    kind 'cap'    = the numbers ARE the receipt (the caller makes the REFUSED run card with them)."""
    from ..config import get_settings
    st = st or get_settings()
    name = str(st.leads_vendor_name or "").strip()
    base = str(st.leads_vendor_base_url or "").strip()
    key = str(st.leads_vendor_api_key or "").strip()
    if not name or not base or not key:
        return False, ("Vendor lane abhi khali hai - koi licensed vendor naam hua hi nahi (plan 12.4: yeh naam "
                       "aap leti hain). Isliye lane plan card par bhi nahi (no stub, no pretending). Jab vendor "
                       "taiyaar ho: LEADS_VENDOR_NAME + LEADS_VENDOR_BASE_URL + LEADS_VENDOR_API_KEY set kijiye."), "config"
    price = float(st.leads_vendor_price_per_row_inr or 0.0)
    if price <= 0:
        return False, (f"{name}: per-row price set nahi hai, to koi ceiling nahi ban sakti. Vendor ka plan padh kar "
                       "LEADS_VENDOR_PRICE_PER_ROW_INR set kijiye (rupees per row; 0 = refuse)."), "config"
    if name.lower() not in _csv(st.leads_vendor_terms_ack):
        return False, (f"{name}: uske terms (data store / show karne par) aapne padhe hi nahi mark kiye. Vendor ki "
                       f"current terms khud padhiye, phir LEADS_VENDOR_TERMS_ACK mein '{name}' likhiye - yeh act "
                       "aapka hai, hum assume nahi karte."), "config"
    est = estimate_inr(planned_rows, st)
    cap = float(st.leads_vendor_run_cap_inr or 0.0)
    if est > cap:
        return False, (f"Yeh vendor run {max(0, int(planned_rows or 0)):,} rows x Rs {price:g}/row = Rs {est:,.0f} "
                       f"ka estimate hai - ek run ka ceiling Rs {cap:,.0f} hai (LEADS_VENDOR_RUN_CAP_INR). Rows "
                       "ghataiye ya ceiling badalwaiye (aapki haan se). (Plan time par refuse - run shuru nahi "
                       "hua, ek bhi vendor call nahi hua.)"), "cap"
    return True, "", "ok"


async def search(query: str, city: str, max_rows: int, tenant_id: str) -> tuple[list[dict], dict[str, Any]]:
    """ONE vendor call under the documented contract. Never retried (the vendor may bill per call - the R6
    never-pays-twice law). Returns (rows, meta{cost_inr, reported}); a row is whatever the vendor sent - the
    service validates per row (name/key/provenance) and counts refusals, so one bad row never kills the run."""
    from ..config import get_settings
    st = get_settings()
    name = str(st.leads_vendor_name or "").strip()
    ok, why, _ = check(tenant_id, max_rows, st)
    if not ok:
        raise VendorError(why)
    key = str(st.leads_vendor_api_key or "")
    body = {"query": str(query or ""), "city": str(city or ""), "max_rows": max(1, int(max_rows or 1))}
    try:
        async with httpx.AsyncClient(base_url=str(st.leads_vendor_base_url).strip(), timeout=60,
                                     transport=_transport) as c:
            r = await c.request("POST", SEARCH_PATH, json=body,
                                headers={"Authorization": f"Bearer {key}", "content-type": "application/json"})
    except httpx.HTTPError as e:
        raise VendorError(f"{name}: vendor tak nahi pahunch paye ({type(e).__name__})") from None
    if r.status_code in (401, 403):
        raise VendorError(f"{name}: key refuse ho gayi ({r.status_code}) - LEADS_VENDOR_API_KEY check kijiye")
    if r.status_code in (402, 429):
        raise VendorError(f"{name}: credit khatam ya rate limit ({r.status_code})")
    if r.status_code >= 400:
        safe = (r.text[:200].replace(key, "***") if key else r.text[:200])
        raise VendorError(f"{name}: vendor ne {r.status_code} diya: {safe}")
    try:
        js = r.json()
    except ValueError:
        raise VendorError(f"{name}: vendor ne JSON nahi diya") from None
    if not isinstance(js, dict):
        raise VendorError(f"{name}: vendor ka jawab object nahi hai")
    rows = [x for x in (js.get("results") or []) if isinstance(x, dict)]
    cost = js.get("cost_inr")
    reported = isinstance(cost, (int, float)) and not isinstance(cost, bool)
    return rows, {"cost_inr": round(float(cost), 4) if reported else None, "reported": reported}
