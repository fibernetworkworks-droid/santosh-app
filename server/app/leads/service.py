"""The LEADS engine's work (docs/LEADS_PLAN.md sections 4, 5.4-5.6, 7): the run store, the deduper, the
provenance gate, the exports and the outreach LEDGER.

Honesty rules encoded here, not remembered anywhere:
- add_row() refuses a row without provenance (source_lane in rules.LANES + source_url). No row without a source
  is ever stored, so no export can ever ship one by accident - and export_csv() still re-checks (belt).
- plan() refuses an unbuilt lane BY NAME with the phase that builds it. L0 (her data) is the only P0 lane.
- campaign_list() is the ONLY hand-off to the WhatsApp campaign desk, it copies ONLY rows with a phone, it
  pre-fills consent False for every scraped/her row, and it writes the LeadOutreach ledger - the sending side
  still goes through the campaign desk's own consent machinery. The engine itself never sends.
- forget() deletes rows (and their list refs) on her word; the day's cap ledger survives the deletion, so the
  day's count cannot be reset by forgetting (the v0.190.1 lesson inverted: some state must outlive erasure).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus, urlparse

from sqlalchemy.exc import IntegrityError

from .. import leadscap
from .importer import normalize_phone
from .models import LeadContact, LeadListRef, LeadOutreach, LeadRun, ensure_tables
from . import rules as R

PARSER_VERSION = "v0.690.0-her1"        # the L0 her-data reader; every row names the code that read its source
PARSER_INDIAMART = "v0.690.0-im1"       # the REGISTRY lane: IndiaMART's own MCP server via app/indiamart.py
PARSER_PLACES = "v0.690.0-pl1"          # the OFFICIAL_API lane: the existing maps tools (nearby + details on tap)
PARSER_ENRICH = "v0.690.0-en1"          # the P2 enrich pass reads the business's OWN website (enrich.py)
PARSER_SCRAPE = "v0.690.0-gm1"          # the P3 SCRAPE lane: the Google Maps PUBLIC listing parser (gmaps_parse)
PARSER_VENDOR = "v0.690.0-vd1"          # the P4 VENDOR lane: the licensed vendor's rows (leads/vendor.py contract)

# mapsbill.MapsCapped arrives here re-raised as maps.MapsError (maps._bill's own law: "a cap hit becomes a
# MapsError"), with this stable text inside - so the cap and an ordinary MapsError are told apart by MARK,
# not by hope: the cap ABORTS the list / stops the buying, an ordinary error just skips the cell.
_MAPSCAP_MARK = "Google Maps budget"

_LEAD_FIELDS = ("name", "category", "address", "city", "state", "pincode", "phone", "website", "email")
_ID_FIELDS = ("kgmid", "cid", "place_id")            # the listing ids the identity key reads (plan 5.4)
_NUM_FIELDS = ("rating", "review_count", "lat", "lng")  # FACTS only, the count never the text


class LeadsError(ValueError):
    """A refusal the card can show as-is (Hinglish, the reason named)."""


# ---------------------------------------------------------------- identity (plan 5.4)
def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip()).lower()


def identity_key(row: dict) -> tuple[str, str]:
    """The row's natural key, strongest first: an explicit listing id (kgmid/cid/place_id - P3's lanes will hand
    these), else the E.164 phone (her data), else a normalised name+ADDRESS hash (gosom's deduper idea). A name
    alone is not an identity - 'Patil Clinic' exists in every city - so a row with neither phone nor address is
    refused, not guessed into the store."""
    for t in ("kgmid", "cid", "place_id"):
        v = str(row.get(t) or "").strip()
        if v:
            return t, v
    phone = normalize_phone(row.get("phone"))
    if phone:
        return "phone_e164", phone
    name, addr = _norm(row.get("name")), _norm(row.get("address") or row.get("city"))
    if name and addr:
        h = hashlib.sha1(f"{name}|{addr}".encode("utf-8")).hexdigest()[:20]
        return "name_address", h
    raise LeadsError("Row mein na phone hai na (naam + address) - bina key ki row store nahi hoti (dedup sambhav nahi).")


# ---------------------------------------------------------------- the plan card (PLAN PEHLE)
def plan(tenant: str, ask: str, lanes: list[str] | None = None, place: str = "", planned_rows: int = 0) -> dict:
    """The card BEFORE anything runs: lanes (refused by name if unbuilt), the caps, the one question if her ask
    is vague. Returns {"ok": bool, ...}; a refusal card never raises - the caller shows it and stops.
    v0.543.0: a SCRAPE lane ask first meets the per-tenant opt-in gate (OFF by default - the amended rule;
    no session may move it) - the refusal names the opt-in and the one act that turns it on.
    v0.544.0: a VENDOR lane ask meets the CONFIGURATION gate the same way (the research R6 gate): no vendor
    named -> the lane is absent and the refusal names the exact config; an estimate over the run cap is a
    cap refusal whose numbers are the receipt (a REFUSED run card carries them)."""
    lanes = [l.upper() for l in (lanes or ["HER_DATA"])]
    unknown = [l for l in lanes if l not in R.LANES]
    unbuilt = [l for l in lanes if l not in R.LANE_BUILT]
    card: dict[str, Any] = {"ok": True, "kind": "leads_plan", "tenant": tenant, "ask": ask, "place": place,
                            "lanes": lanes, "caps": leadscap.caps(), "planned_rows": planned_rows,
                            "parser_version": PARSER_VERSION}
    if unknown or unbuilt:
        card["ok"] = False
        card["refused_lanes"] = unknown + unbuilt
        card["why"] = [f"{l} abhi built nahi hai - {R.LANE_ARRIVES.get(l, 'aage ek phase mein')} aayega "
                       f"(plan: docs/LEADS_PLAN.md)" for l in unbuilt] + \
                      [f"{l} koi lane hi nahi hai - lanes hain: {', '.join(R.LANES)}" for l in unknown]
        card["lanes"] = [l for l in lanes if l in R.LANE_BUILT]
        if not card["lanes"]:
            if not str(place or "").strip():
                card["need"] = R.ONE_QUESTION            # the refusal carries the one question too
            return card
    if "SCRAPE" in lanes and not scrape_opted_in(tenant):
        card["ok"] = False
        card["refused_lanes"] = ["SCRAPE"]
        card["why"] = [R.SCRAPE_OFF]
        card["lanes"] = [l for l in lanes if l != "SCRAPE"] or []
        card["opt_in"] = {"on": False, "default": "OFF",
                          "how": "leads_run action=scrape_optin on=true (ya POST /api/leads/scrape-optin)"}
        return card
    if "VENDOR" in lanes:
        from . import vendor as V
        vok, vwhy, vkind = V.check(tenant, planned_rows)
        if not vok:
            card["ok"] = False
            # the unknown-lane block above may already have named its lanes - the vendor gate EXTENDS the
            # refusal (BOGUS + VENDOR both named), it never replaces what the card already refused
            card["refused_lanes"] = list(dict.fromkeys((card.get("refused_lanes") or []) + ["VENDOR"]))
            card["why"] = (card.get("why") or []) + ([vwhy] if vkind == "config" else [])
            if vkind == "cap":
                card["cap_refusal"] = vwhy          # a cap refusal rides cap_refusal (the receipt)
            card["vendor"] = {**V.config_snapshot(), "absent": "vendor configure nahi hai to lane card par bhi nahi"}
            card["lanes"] = [l for l in lanes if l != "VENDOR"] or []
            if not card["lanes"] and not str(place or "").strip():
                card["need"] = R.ONE_QUESTION
            return card
        vs = V.config_snapshot()
        card["vendor"] = {"name": vs["name"], "price_per_row_inr": vs["price_per_row_inr"],
                          "estimate_inr": V.estimate_inr(planned_rows), "run_cap_inr": vs["run_cap_inr"],
                          "priced": "BEFORE the run - estimate crossing the cap refuses at plan time"}
    if not str(ask or "").strip() or (not str(place or "").strip() and any(l != "HER_DATA" for l in card["lanes"])):
        card["ok"] = False
        card["need"] = R.ONE_QUESTION
        return card
    try:
        card["cap_check"] = leadscap.check_run(tenant, planned_rows)
    except leadscap.LeadsCapped as e:
        card["ok"] = False
        card["cap_refusal"] = str(e)
    return card


# ---------------------------------------------------------------- the run (L0: her data)
def _clean_row(row: dict) -> dict:
    """One business row from her data or a lane -> the store's fields, house-laws applied (E.164 phone, facts
    only). v0.541.0: the listing ids (kgmid/cid/place_id) and the numeric facts (rating, review COUNT, lat/lng)
    now ride through too - the P0 version silently dropped them, which would have made every official-lane row
    lose its place_id and fall to a name+address hash."""
    out: dict[str, Any] = {}
    for f in _LEAD_FIELDS:
        v = row.get(f)
        if v is None and f == "phone":
            v = row.get("mobile") or row.get("whatsapp")
        out[f] = str(v).strip() if v is not None else ""
    for f in _ID_FIELDS:
        v = row.get(f)
        if v not in (None, ""):
            out[f] = str(v).strip()
    for f in _NUM_FIELDS:
        if row.get(f) not in (None, ""):
            out[f] = row[f]
    phone = normalize_phone(out.get("phone"))
    out["phone"] = phone or ""
    return out


def run_her_data(tenant: str, ask: str, rows: list[dict], source_name: str, place: str = "",
                 lanes: list[str] | None = None, actor: str = "owner") -> dict:
    """L0: her own data into the store, one row per business, provenance = the file/list's name. PLAN PEHLE: the
    caps are checked before the first row is written; a cap refusal is a REFUSED run card, an UNBUILT lane or a
    vague ask raises (nothing to run at all). v0.543.0: the lane is pinned to HER_DATA by name - her file's rows
    are never allowed to ride another lane's provenance (a mislabelled source is worse than no source)."""
    ensure_tables()
    lanes = [str(l).upper() for l in (lanes or ["HER_DATA"])]
    if any(l != "HER_DATA" for l in lanes):
        raise LeadsError("Her data hamesha HER_DATA lane se jaata hai - doosri lane ki provenance uski file par "
                         "nahi likhi jaati (galat source bina source se bura hai).")
    p = plan(tenant, ask, lanes, place, planned_rows=len(rows or []))
    run = _new_run(tenant, ask, place, lanes, p)
    if not p["ok"]:
        why = "; ".join(p.get("why") or [])
        if why or p.get("need"):
            _delete_run(run.id)          # a lane / ask refusal leaves NO run row behind - nothing was run
            raise LeadsError(why or p.get("need", ""))
        _finish(run, "REFUSED", error=p.get("cap_refusal", ""))
        return {"ok": False, "run": run_card(run.id), "plan": p}
    _status(run, "RUNNING")
    found = kept = duped = refused = 0
    for raw in rows or []:
        found += 1
        try:
            row = _clean_row(raw)
            ktype, kval = identity_key(row)
        except LeadsError:
            refused += 1
            continue
        if not kval:
            refused += 1
            continue
        try:
            _write_row(tenant, run, ktype, kval, row, source_lane="HER_DATA",
                       source_url=str(source_name or "her-data")[:500])
            kept += 1
        except LeadsError as e:
            if "already" in str(e):
                duped += 1
            else:
                refused += 1
    leadscap.record(tenant, kept)
    _counters(run, found, kept, duped, refused)
    _finish(run, "DONE")
    return {"ok": True, "run": run_card(run.id)}   # re-read: the counters / status live in the DB, not the detached object


# ---------------------------------------------------------------- the REGISTRY lane (P1: IndiaMART, official MCP)
async def run_indiamart(tenant: str, ask: str, search_term: str, city: str = "", cities: list[str] | None = None,
                        biztype: str = "", place: str = "", max_rows: int = 200) -> dict:
    """P1's REGISTRY lane: IndiaMART's OWN MCP server through the existing app/indiamart.py (official route, no
    sign-in, free) - sellers for a product in up to 5 cities. PLAN PEHLE: the cap refuses at plan time on
    max_rows. The one search per city is bounded (max_rows), the seller is the row (one BUSINESS one row - the
    same company behind five products is ONE lead, counted duped), provenance is the product's IndiaMART page."""
    ensure_tables()
    from .. import indiamart
    search_term = str(search_term or "").strip()
    if not search_term:
        raise LeadsError("Kaunsa product dhoondhna hai? Naam bataiye (jaise 'cement', 'LED bulb').")
    raw_rows = max(1, int(max_rows or 200))
    city_list: list[str] = []
    for c in [str(city or "").strip()] + [str(c).strip() for c in (cities or [])]:
        if c and c.lower() not in [x.lower() for x in city_list]:
            city_list.append(c)
    city_list = city_list[: indiamart.MAX_CITIES]
    p = plan(tenant, ask, ["REGISTRY"], place or (city_list[0] if city_list else ""), planned_rows=raw_rows)
    run = _new_run(tenant, ask, place or (city_list[0] if city_list else ""), ["REGISTRY"], p)
    if not p["ok"]:
        why = "; ".join(p.get("why") or [])
        if why or p.get("need"):
            _delete_run(run.id)
            raise LeadsError(why or p.get("need", ""))
        _finish(run, "REFUSED", error=p.get("cap_refusal", ""))
        return {"ok": False, "run": run_card(run.id), "plan": p}
    max_rows = min(raw_rows, leadscap.caps()["per_run"])          # the ask was checked RAW; now the working bound
    _status(run, "RUNNING")
    found = kept = duped = refused = calls = 0
    stopped_by_bound = False
    for c in city_list or [""]:
        if found >= max_rows:
            stopped_by_bound = True
            break
        try:
            res = await indiamart.search(search_term, city=c, biztype=str(biztype or "").strip())
        except indiamart.IndiaMartError as e:
            _finish(run, "ABORTED", error=str(e))
            leadscap.record(tenant, kept)
            _counters(run, found, kept, duped, refused)
            return {"ok": False, "run": run_card(run.id), "error": str(e)}
        calls += 1
        for prod in res.get("products") or []:
            if found >= max_rows:
                stopped_by_bound = True
                break
            if not isinstance(prod, dict):
                refused += 1
                continue
            found += 1
            row = _clean_row({"name": prod.get("company") or prod.get("title") or "",
                              "category": prod.get("category") or search_term,
                              "address": prod.get("location") or "",
                              "city": prod.get("city") or c,
                              "phone": prod.get("phone") or "", "website": "", "email": ""})
            url = str(prod.get("url") or "")
            if not url.startswith("http"):
                url = "https://dir.indiamart.com/search.mp?ss=" + quote_plus(search_term)
            try:
                _write_row(tenant, run, *_identity_of(row), row, source_lane="REGISTRY",
                           source_url=url[:500], parser_version=PARSER_INDIAMART)
                kept += 1
            except LeadsError as e:
                if "already" in str(e):
                    duped += 1
                else:
                    refused += 1
    leadscap.record(tenant, kept)
    _counters(run, found, kept, duped, refused)
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.bill = json.dumps({"lane": "REGISTRY", "sku": "indiamart.mcp.search", "calls": calls,
                                 "inr": 0.0, "cities": city_list,
                                 "note": "IndiaMART ka apna MCP server - official route, abhi ke liye muft"})
    _finish(run, "DONE")
    return {"ok": True, "run": run_card(run.id),
            "bound": {"max_rows": max_rows, "stopped_by_bound": stopped_by_bound}}


# ---------------------------------------------------------------- the OFFICIAL_API lane (P1: the existing maps tools)
def _identity_of(row: dict) -> tuple[str, str]:
    return identity_key(row)


def place_cells(center: dict, sweep_km: float, cell_km: float, max_cells: int = 400) -> list[dict]:
    """Circle of `sweep_km` around the centre, tiled into overlapping maps_nearby circles of radius `cell_km`
    (spacing 1.5x the radius, so the tiles overlap by a quarter - a dukaan on the seam shows up twice and the
    deduper collapses it). The 20-result ceiling of Nearby Search is beaten by tiling, never by hoping."""
    import math
    sweep_km = max(0.5, min(float(sweep_km or 5), 50.0))
    cell_km = max(0.5, min(float(cell_km or 2), min(sweep_km, 50.0)))
    lat0, lng0 = float(center["lat"]), float(center["lng"])
    step_lat = cell_km * 1.5 / 111.0
    step_lng = cell_km * 1.5 / max(0.2, math.cos(math.radians(lat0))) / 111.0
    n = int(math.ceil(sweep_km / (cell_km * 1.5)))
    cells: list[dict] = []
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            lat, lng = lat0 + i * step_lat, lng0 + j * step_lng
            d = math.hypot((lat - lat0) * 111.0, (lng - lng0) * 111.0 * math.cos(math.radians(lat0)))
            if d <= sweep_km + cell_km * 0.5:
                cells.append({"lat": round(lat, 6), "lng": round(lng, 6), "radius_m": int(cell_km * 1000)})
    if len(cells) > max_cells:
        raise LeadsError(f"Yeh sweep {len(cells)} cells banata hai - ek run ka limit {max_cells} hai. "
                         f"Sweep chhota kijiye (sweep_km/cell_km), ya sheher ke tukdon mein chalaiye.")
    return cells


async def run_places(tenant: str, ask: str, kinds, near: str, sweep_km: float = 5.0, cell_km: float = 2.0,
                     details: bool = False, place: str = "", max_rows: int = 1000) -> dict:
    """P1's OFFICIAL_API lane: Google Places through the EXISTING maps tools only - maps.resolve for the centre,
    maps.nearby for the list (billed by mapsbill, cap refuses BEFORE the call), and maps.place_details bought
    for at most `details_max` places (the maps_place economics: phone/website are the expensive fields and are
    bought per place, never hoarded for a whole list). NO new Google client code; the MapsPlaceCache six-column
    rule is untouched - this store keeps its OWN rules (business facts + provenance + fetched_at, plan section 8).
    A MapsCapped mid-list ABORTS the run with the cap named; mid-details it only stops the buying."""
    ensure_tables()
    from .. import maps, mapsbill
    from ..config import get_settings
    kinds_l = [str(k).strip() for k in (kinds if isinstance(kinds, list) else [kinds]) if str(k).strip()]
    if not kinds_l:
        raise LeadsError("Kis tarah ki jagah dhoondhni hai? Google place types bataiye (jaise pharmacy, "
                         "hardware_store, restaurant).")
    if not str(near or "").strip():
        raise LeadsError("Kahan dhoondhna hai? Jagah ka naam bataiye (jaise 'Pune', 'Karol Bagh Delhi').")
    if not maps.configured():
        raise LeadsError("Google Maps abhi connect nahi hai (server par GOOGLE_MAPS_API_KEY set nahi hai).")
    raw_rows = max(1, int(max_rows or 1000))
    p = plan(tenant, ask, ["OFFICIAL_API"], place or str(near).strip(), planned_rows=raw_rows)
    if not p["ok"]:
        why = "; ".join(p.get("why") or [])
        if why or p.get("need"):
            raise LeadsError(why or p.get("need", ""))     # no run row: nothing ran, no cells yet either
        # cap refusal still gets its REFUSED card (the numbers are the receipt) - and NOT one billed call:
        # a run that is refused before it starts must not spend a geocode to deliver its own refusal
        run0 = _new_run(tenant, ask, place or str(near).strip(), ["OFFICIAL_API"], p)
        _finish(run0, "REFUSED", error=p.get("cap_refusal", ""))
        return {"ok": False, "run": run_card(run0.id), "plan": p}
    max_rows = min(raw_rows, leadscap.caps()["per_run"])          # the ask was checked RAW; now the working bound
    try:
        center = await maps.resolve(str(near).strip(), tenant, near=None)
    except maps.MapsError as e:
        raise LeadsError(f"Jagah resolve nahi hui: {e}") from None
    if not center or center.get("lat") is None:
        raise LeadsError(f"'{near}' Google Maps par nahi mila - sheher / area ka naam dobara bataiye.")
    cells = place_cells(center, sweep_km, cell_km)
    run = _new_run(tenant, ask, place or str(near).strip(), ["OFFICIAL_API"], p)
    _status(run, "RUNNING")
    found = kept = duped = refused = nearby_calls = detail_calls = 0
    errors: list[str] = []
    details_stopped = False
    details_max = min(max(0, int(get_settings().leads_places_details_per_run)), len(cells) * 20)
    bill_before = mapsbill.usage(tenant)["inr"]
    to_detail: list[str] = []
    for cell in cells:
        if found >= max_rows:
            break
        try:
            places = await maps.nearby({"lat": cell["lat"], "lng": cell["lng"]}, kinds_l,
                                       radius_m=cell["radius_m"], limit=min(20, max_rows - found),
                                       rank="popularity", tenant_id=tenant)
        except maps.MapsError as e:
            if _MAPSCAP_MARK in str(e):        # mapsbill refused BEFORE the call - ABORT, never truncate
                _finish(run, "ABORTED", error=f"Google Maps ka cap: {e}")
                leadscap.record(tenant, kept)
                _counters(run, found, kept, duped, refused)
                return {"ok": False, "run": run_card(run.id), "error": f"Google Maps ka cap: {e}",
                        "bill": {"inr_spent": round(mapsbill.usage(tenant)["inr"] - bill_before, 4)}}
            errors.append(str(e)[:200])
            continue
        nearby_calls += 1
        for pl in places:
            if found >= max_rows:
                break
            if not isinstance(pl, dict) or not pl.get("place_id"):
                refused += 1
                continue
            found += 1
            row = _clean_row({"place_id": pl.get("place_id"), "name": pl.get("name") or "",
                              "category": pl.get("type") or ", ".join(kinds_l),
                              "address": pl.get("address") or "",
                              "city": center.get("name") or str(near).strip(),
                              "phone": pl.get("phone") or "", "website": pl.get("website") or "",
                              "rating": pl.get("rating"), "review_count": pl.get("reviews"),
                              "lat": pl.get("lat"), "lng": pl.get("lng")})
            src = pl.get("maps_link") or f"https://www.google.com/maps/place/?q=place_id:{pl['place_id']}"
            try:
                _write_row(tenant, run, *_identity_of(row), row, source_lane="OFFICIAL_API",
                           source_url=src[:500], parser_version=PARSER_PLACES)
                kept += 1
                if details and not row.get("phone"):
                    to_detail.append(pl["place_id"])
            except LeadsError as e:
                if "already" in str(e):
                    duped += 1
                else:
                    refused += 1
    bought = 0
    for pid in to_detail[: max(0, details_max)]:
        try:
            d = await maps.place_details(pid, tenant_id=tenant)
        except maps.MapsError as e:
            if _MAPSCAP_MARK in str(e):        # the cap cut the buying, not the run: the list rows stay
                details_stopped = True
                errors.append(f"details cap: {e}"[:200])
                break
            errors.append(str(e)[:200])
            continue
        detail_calls += 1
        apply_details(tenant, pid, d)
        bought += 1
    leadscap.record(tenant, kept)
    _counters(run, found, kept, duped, refused)
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.bill = json.dumps({"lane": "OFFICIAL_API", "sku_nearby": mapsbill.SKU_NEARBY_PRO,
                                 "nearby_calls": nearby_calls, "details_calls": detail_calls,
                                 "details_max": details_max, "details_stopped": details_stopped,
                                 "inr": round(mapsbill.usage(tenant)["inr"] - bill_before, 4),
                                 "attribution": "Google", "note": "list maps.nearby se, details maps.place_details se - "
                                 "existing maps tools, mapsbill cap ke neeche"})
            r.error = "; ".join(errors)[:600]
    _finish(run, "DONE")
    return {"ok": True, "run": run_card(run.id),
            "center": {"name": center.get("name", ""), "lat": center["lat"], "lng": center["lng"]},
            "cells": len(cells), "kinds": kinds_l, "sweep_km": sweep_km, "cell_km": cell_km,
            "details": {"requested": bool(details), "bought": bought, "max": details_max,
                        "stopped_by_cap": details_stopped},
            "errors": errors[:5]}


def apply_details(tenant: str, key_value: str, data: dict) -> bool:
    """One maps.place_details answer onto its stored row: phone (E.164), website, rating, review COUNT. Only
    these facts move; provenance stays as it was (the row's source is still the nearby list that found it)."""
    ensure_tables()
    with _s() as s:
        c = s.query(LeadContact).filter(LeadContact.tenant_id == tenant, LeadContact.key_type == "place_id",
                                        LeadContact.key_value == str(key_value)).first()
        if c is None:
            return False
        if data.get("phone"):
            c.phone = normalize_phone(data.get("phone")) or c.phone
        if data.get("website"):
            c.website = str(data["website"]).strip()[:300]
        if data.get("rating") not in (None, ""):
            c.rating = float(data["rating"])
        if data.get("reviews") not in (None, ""):
            c.review_count = int(data["reviews"])
        return True


# ---------------------------------------------------------------- the enrich pass (P2, the business's OWN site)
def apply_enrich(tenant: str, row_id: str, data: dict) -> bool:
    """One site-pass answer onto its stored row: email (only into an EMPTY slot - the pass never overwrites an
    email another source gave), email_grade (always refreshed - deliverability is a NOW answer), socials, and
    the enrichment's own provenance (enriched_from + enrich_note + enriched_at)."""
    ensure_tables()
    with _s() as s:
        c = s.query(LeadContact).filter(LeadContact.tenant_id == tenant, LeadContact.id == str(row_id)).first()
        if c is None:
            return False
        new_email = str(data.get("email") or "").strip().lower()
        if new_email and not (c.email or "").strip():
            c.email = new_email[:200]
        grade = str(data.get("email_grade") or "").strip()
        if grade in R.EMAIL_GRADES:
            c.email_grade = grade
        elif not grade and new_email and not (c.email or "").strip():
            c.email_grade = ""                              # a fresh email with no grade never ships as pakka
        socials = data.get("socials")
        if isinstance(socials, dict) and socials:
            c.socials = {k: str(v)[:300] for k, v in socials.items() if str(v).strip()}
        c.enriched_from = str(data.get("enriched_from") or "")[:300]
        c.enrich_note = str(data.get("enrich_note") or "")[:600]
        c.enriched_at = datetime.now(timezone.utc)
        return True


def _enrich_targets(tenant: str, row_ids: list[str] | None, q: str, city: str, category: str, lane: str,
                    run_id: str) -> list[LeadContact]:
    """The rows a pass may read: kept rows (opt-out honoured) WITH a website. Named row_ids win over the
    filters; with no row_ids the filters pick. Every target is re-read on every pass - deliverability is a NOW
    answer, so re-grading an old email is work, not waste."""
    ensure_tables()
    conds = [LeadContact.tenant_id == tenant, LeadContact.opt_out.is_(False), LeadContact.website != ""]
    with _s() as s:
        if row_ids:
            got = (s.query(LeadContact).filter(*conds, LeadContact.id.in_([r for r in row_ids if r]))
                   .order_by(LeadContact.fetched_at.desc(), LeadContact.id).all())
        else:
            more = _filters(tenant, q, city, category, lane, False, False, False)
            if run_id:
                more.append(LeadContact.run_id == str(run_id))
            got = (s.query(LeadContact).filter(*conds, *more)
                   .order_by(LeadContact.fetched_at.desc(), LeadContact.id)
                   .limit(max(1, min(2000, leadscap.caps()["per_run"]))).all())
        s.expunge_all()
        return list(got)


async def enrich(tenant: str, ask: str = "", row_ids: list[str] | None = None, q: str = "", city: str = "",
                 category: str = "", lane: str = "", run_id: str = "", use_model: bool = True,
                 fanout: bool = False) -> dict:
    """P2 ENRICHMENT (docs/LEADS_PLAN.md section 6): a bounded crawl-brain pass over kept rows' OWN websites -
    emails + socials read, deliverability graded (pakka / sadak_tak / galat, DNS -> MX -> disposable, NO SMTP
    probe), the best email picked by ONE billed model call per row (usage.run_meter catches the spend - the
    research/bill.py pattern), every dead site a recorded result and never a crash.

    Enrichment is NOT a source lane (the plan says so) - the run's lanes list stays empty and the plan card
    carries kind=enrich. The cap is a PLAN-TIME refusal (the house law): more eligible rows than
    leads_enrich_rows_per_run and the pass refuses with the number named, never truncates quietly.

    v0.544.0 P4 SCALE: fanout=True runs the SAME per-row body across the HOOLA GRAPH (leads/scale.py:
    dispatch -> static chunk fan-out -> join barrier, at most leads_enrich_fanout_max site passes in flight,
    politeness still 1 req/s per site). The graph only COMPUTES; the store writes happen after the barrier,
    one writer at a time - the same apply_enrich calls, the same provenance, the same counters as the serial
    pass. fanout=False (the default) is the P2 walk, unchanged."""
    import asyncio as _asyncio
    from ..config import get_settings as _gs
    from . import enrich as E

    cap = int(leadscap.caps()["enrich_rows_per_run"])
    targets = _enrich_targets(tenant, [r for r in (row_ids or []) if str(r).strip()], q, city, category, lane, run_id)
    if len(targets) > cap:
        raise LeadsError(f"Enrich cap: {cap} rows per pass hai (LEADS_ENRICH_ROWS_PER_RUN), aapke filter par "
                         f"{len(targets)} rows bethi hain. Filter ghaatiye ya row_ids dijiye - chupke se "
                         f"truncate nahi hota.")
    fan_max = max(1, int(_gs().leads_enrich_fanout_max))
    plan_card = {"kind": "enrich", "cap_rows": cap, "targeted": len(targets), "use_model": bool(use_model),
                 "mode": "graph_fanout" if fanout else "serial",
                 "max_in_flight": fan_max if fanout else 1,
                 "robots": "scrape_respect_robots (default True)", "politeness": "1 req/s per site",
                 "site_pages_max": E.SITE_PAGES_MAX, "smtp_probe": "NOT BUILT"}
    run = _new_run(tenant, ask or "enrichment pass", "", [], plan_card)
    _status(run, "RUNNING")

    acc: dict = {}
    enriched = dead = blocked = no_email = 0
    picks: dict[str, int] = {"ai": 0, "rule": 0, "single": 0, "none": 0}
    details: list[dict] = []
    errors: list[str] = []

    async def _one(row: LeadContact) -> dict | None:
        """The per-row body, shared verbatim by the serial walk and the graph fan-out: NO store writes here
        (the fan-out applies after the join barrier - one writer at a time, SQLite-safe)."""
        site = (row.website or "").strip()
        if not site:
            return None
        try:
            res = await _asyncio.to_thread(E.site_pass, site, tenant)
        except Exception as e:                       # noqa: BLE001 - one bad site never kills the pass
            return {"kind": "error", "error": f"{row.name or row.id}: {e}"}
        pages = res.get("pages") or []
        alive = [p for p in pages if p.get("status") and not p.get("blocked")]
        if not res.get("blocked") and not alive and pages:
            # the plan's card ask: a dead site yields galat, not a crash - an email whose domain IS the
            # dead site cannot receive mail any more
            grade = ""
            note = f"site dead: {pages[0].get('dead', '')[:150]}"
            if (row.email or "").strip():
                dom = (row.email.rsplit("@", 1)[-1] if "@" in row.email else "")
                sdom = (urlparse(site).hostname or "").replace("www.", "")
                if dom and sdom and (dom == sdom or dom.endswith("." + sdom) or sdom.endswith("." + dom)):
                    grade = "galat"
                    note += " - email_grade galat (site hi mari hui hai)"
            return {"kind": "dead", "grade": grade,
                    "apply": {"email_grade": grade, "enriched_from": site, "enrich_note": note, "socials": {}},
                    "detail": {"id": row.id, "name": row.name, "result": "dead_site", "grade": grade}}
        if res.get("blocked") and not alive:
            return {"kind": "blocked",
                    "apply": {"enriched_from": site, "enrich_note": f"blocked: {res['blocked'][0][:150]}",
                              "socials": {}},
                    "detail": {"id": row.id, "name": row.name, "result": "blocked"}}
        emails = list(res.get("emails") or [])
        email, reason, pick = "", "", "none"
        got_email = False
        if emails:
            if use_model:
                be = await E.best_email(emails, row.name or "")
                email, reason, pick = be.get("email", ""), be.get("reason", ""), be.get("pick", "rule")
            else:
                email = E.rank_emails(emails, row.name or "")[0]
                reason, pick = "use_model=false - rule rank", "rule"
            got_email = True
        # the grade belongs to the email the ROW ends up with: the pass's pick only lands in an EMPTY
        # slot, so a row keeping its own email is graded on ITS email - never on somebody else's
        final_email = (email if (email and not (row.email or "").strip()) else (row.email or "").strip())
        grade = E.grade_email(final_email) if final_email else ""
        socials = res.get("socials") or {}
        if final_email == (row.email or "").strip() and (row.email or "").strip():
            note = f"email already tha ({final_email}) - naya email nahi likha, grade taaza kiya"
        else:
            note = f"{pick}: {reason}".strip(": ")
        wrote = bool((email and not (row.email or "").strip()) or grade or socials or note)
        return {"kind": "normal", "no_email": not got_email, "pick": pick, "wrote": wrote,
                "apply": ({"email": email, "email_grade": grade, "socials": socials,
                           "enriched_from": site, "enrich_note": note} if wrote else None),
                "detail": {"id": row.id, "name": row.name, "result": "enriched" if wrote else "unchanged",
                           "email": email, "grade": grade, "pick": pick,
                           "socials": sorted(socials.keys()), "pages": len(alive)}}

    def _absorb(rres: dict | None) -> None:
        """The fold: counters + the store write + the detail row - identical for both modes."""
        nonlocal enriched, dead, blocked, no_email
        if rres is None:
            return
        k = rres.get("kind")
        if k == "error":
            errors.append(rres["error"])
            return
        if k == "dead":
            dead += 1
            if rres.get("grade"):
                enriched += 1
        elif k == "blocked":
            blocked += 1
        else:
            if rres.get("no_email"):
                no_email += 1
            if rres.get("wrote"):
                enriched += 1
            picks[rres.get("pick", "none")] = picks.get(rres.get("pick", "none"), 0) + 1
        if rres.get("apply"):
            apply_enrich(tenant, rres["detail"]["id"], rres["apply"])
        details.append(rres["detail"])

    meter = None
    if use_model:
        from .. import usage
        meter = usage.run_meter(acc)
        meter.__enter__()
    try:
        fmeta: dict = {}
        if fanout:
            from . import scale
            fres = await scale.enrich_fanout(list(targets), _one, max_in_flight=fan_max)
            for rres in fres["results"]:                 # after the BARRIER: one writer, same fold
                _absorb(rres)
            fmeta = {"chunks": fres.get("chunks"), "seconds": fres.get("seconds")}
        else:
            for row in targets:                          # the P2 walk: compute, then apply, row by row
                _absorb(await _one(row))
        if meter is not None:
            meter.__exit__(None, None, None)
            meter = None
        from .. import usage as _usage
        bill = {"model_calls": int(acc.get("calls", 0)), "tok_in": int(acc.get("tok_in", 0)),
                "tok_out": int(acc.get("tok_out", 0)), "inr": round(float(acc.get("usd", 0.0)) * _usage.usd_inr(), 4),
                "picks": picks, "sites_read": len(targets), "site_pages": E.SITE_PAGES_MAX,
                "note": "websites muft (scrape stack), model calls run_meter mein naape gaye (research/bill pattern)"}
        _counters(run, len(targets), enriched, 0, dead + blocked)
        with _s() as s:
            r = s.get(LeadRun, run.id)
            if r:
                r.bill = json.dumps(bill, ensure_ascii=False)[:4000]
        _finish(run, "DONE", "; ".join(errors)[:300])
        return {"ok": True, "run": run_card(run.id),
                "mode": plan_card["mode"], "max_in_flight": plan_card["max_in_flight"], **fmeta,
                "enriched": enriched, "dead_site": dead, "blocked": blocked, "no_email": no_email,
                "picks": picks, "details": details[:50], "errors": errors[:5]}
    except Exception as e:                               # noqa: BLE001 - the run card names what died
        if meter is not None:
            try:
                meter.__exit__(type(e), e, e.__traceback__)
            except Exception:                            # noqa: BLE001
                pass
        _finish(run, "ABORTED", str(e))
        return {"ok": False, "run": run_card(run.id), "error": str(e)}


# ---------------------------------------------------------------- the SCRAPE opt-in (P3, the permission slip)
def scrape_opted_in(tenant: str) -> bool:
    """The lane's permission state for a tenant - OFF unless SHE flipped it (the amended rule: 'opt-in per
    tenant and OFF by default ... which no session may move'). Reads lead_scrape_optins; no row = OFF."""
    ensure_tables()
    from .models import LeadScrapeOptIn
    with _s() as s:
        row = s.get(LeadScrapeOptIn, tenant)
        return bool(row.on) if row is not None else False


def set_scrape_optin(tenant: str, on: bool, actor: str = "owner") -> dict:
    """HER act, recorded: the flip lands in lead_scrape_optins with the actor and the walls quoted (the
    permission slip always carries what it permits). Turning OFF is the same kind of act - the lane refuses
    again from that moment; nothing in the store is deleted (rows keep their provenance)."""
    ensure_tables()
    from .models import LeadScrapeOptIn
    walls = " | ".join(R.SCRAPE_WALLS)
    with _s() as s:
        row = s.get(LeadScrapeOptIn, tenant)
        if row is None:
            row = LeadScrapeOptIn(tenant_id=tenant)
            s.add(row)
            s.flush()
        row.on = bool(on)
        row.actor = str(actor or "owner")[:64]
        row.note = walls[:2000]
        row.at = datetime.now(timezone.utc)
    return {"ok": True, "tenant": tenant, "scrape_optin": bool(on), "actor": str(actor or "owner"),
            "walls": R.SCRAPE_WALLS,
            "note": "on karne par bhi walls wahin rahengi - Google Maps public listings, politeness 1 req/s, "
                    "provenance har row ka, engine kabhi khud kuch nahi bhejta"}


# ---------------------------------------------------------------- the SCRAPE lane (P3, the owner's explicit ask)
def _checkpoint_scrape(run: LeadRun, plan_dict: dict) -> None:
    """The resume checkpoint: the plan JSON (cells WITH their statuses) written back after every cell - a
    crashed run continues the GRID, not just the file (plan 5.5; the research/store.py pattern)."""
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.plan = json.dumps(plan_dict, ensure_ascii=False, default=str)[:400_000]


def _cell_status_cells(cells: list[dict]) -> tuple[int, int]:
    done = sum(1 for c in cells if c.get("status") == "done")
    return done, len(cells)


async def run_scrape(tenant: str, ask: str, query: str, near: str = "", center: dict | None = None,
                     sweep_km: float = 3.0, zoom: int = 15, max_rows: int = 1000, place: str = "",
                     resume_run_id: str = "", hl: str = "en", gl: str = "in") -> dict:
    """P3's SCRAPE lane (docs/LEADS_PLAN.md sections 4 L2, 5, 8): the Google Maps PUBLIC LISTING lane, behind
    the per-tenant opt-in that is OFF until she flips it (set_scrape_optin - the amended CLAUDE.md rule rode
    this lane's own commit).

    THE SHAPE: grid.bbox_cells cuts her sweep into zoom cells; each cell walks PAGES_PER_CELL_MAX search pages
    (20 listings a page, the ~120 ceiling) through the EXISTING scrape stack (SSRF guard, curl_cffi, proxy
    policy - scrape.py), paced at 1 req/s per host (MAX_CONCURRENCY 2 named, one host in P3 so politeness
    paces). gmaps_parse reads the business FACTS only (rules.STORE_BOUNDARY: no review text, no photos, no
    popular times - the parser's field list is the wall).

    THE HONESTY: caps refused AT PLAN TIME (per-run rows, per-day rows, the cell ceiling - numbers named); a
    block page / CAPTCHA wall HARD-ABORTS the run with the wall named (crawl.blocked.why_blocked - Hoola backs
    off and reports, it does NOT muscle through, rules.NEVER); a parse tripwire (no APP_INITIALIZATION_STATE on
    two consecutive cells) aborts with 'layout badla' instead of quietly harvesting nothing; every row carries
    source_lane=SCRAPE + the exact search page it was read from + parser_version; the bill names the politeness
    spend (HTTP requests, zero rupees - one geocode via the existing maps.resolve when a name had to be
    resolved, billed by mapsbill as it always is); the zoom ladder's next step is chosen from the MEASURED
    per-cell yields, recorded on the card.

    THE RESUME: every cell's status lands in the run's plan JSON after every cell (plan 5.5). resume_run_id
    continues THAT grid - done cells are never re-fetched, a DONE run's resume is a no-op card with zero
    fetches (the BADA CATALOGUE idempotency law)."""
    ensure_tables()
    from . import grid as G, gmaps_parse as GP, scrape as SC
    from ..crawl import blocked as _blocked

    query = str(query or "").strip()
    if not query:
        raise LeadsError("Kis dhandhe ki list? Query bataiye (jaise 'dentists', 'hardware store', 'cafe').")
    if not scrape_opted_in(tenant):
        raise LeadsError(R.SCRAPE_OFF)              # the opt-in gate BEFORE any plan work - the rule is a wall
    zoom = int(zoom or G.ZOOM_DEFAULT)
    try:
        G.cell_km(zoom)                             # the ladder is written, an unknown zoom is refused
    except G.GridError as e:
        raise LeadsError(str(e)) from None
    raw_rows = max(1, int(max_rows or 1000))
    # the where-label: her place word, else the near word, else the pin's name/coordinates - a centre pin IS
    # an answer to the one question's second half (the ask carries the what, the pin carries the where)
    pin = center if isinstance(center, dict) and center.get("lat") is not None else None
    where_label = (str(place or "").strip() or str(near or "").strip()
                   or str((pin or {}).get("name") or "").strip()
                   or (f"{pin['lat']:.4f},{pin['lng']:.4f}" if pin else ""))
    p = plan(tenant, ask, ["SCRAPE"], where_label, planned_rows=raw_rows)
    if not p["ok"]:
        why = "; ".join(p.get("why") or [])
        if why or p.get("need"):
            raise LeadsError(why or p.get("need", ""))     # nothing ran: no run row, no fetch
        run0 = _new_run(tenant, ask, where_label, ["SCRAPE"], p)
        _finish(run0, "REFUSED", error=p.get("cap_refusal", ""))
        return {"ok": False, "run": run_card(run0.id), "plan": p}
    max_rows = min(raw_rows, leadscap.caps()["per_run"])       # the ask was checked RAW; now the working bound
    pages_max = max(1, min(leadscap.caps()["scrape_pages_per_cell"], GP.PAGES_PER_CELL_MAX))

    resumed_plan: dict | None = None
    run: LeadRun | None = None
    if resume_run_id:
        with _s() as s:
            r0 = s.get(LeadRun, str(resume_run_id))
            if r0 is None or r0.tenant_id != tenant:
                raise LeadsError("Resume ka run nahi mila (ya doosre tenant ka hai).")
            lanes0 = json.loads(r0.lanes or "[]")
            if "SCRAPE" not in lanes0:
                raise LeadsError("Woh run SCRAPE lane ka nahi hai - resume sirf usi grid par.")
            resumed_plan = json.loads(r0.plan or "{}")
        if resumed_plan.get("kind") != "scrape":
            raise LeadsError("Us run ka plan scrape grid ka nahi hai - resume nahi ho sakta.")
        run = LeadRun(id=r0.id, tenant_id=r0.tenant_id)      # a detached handle; the row itself stays
        for k in ("query", "center", "sweep_km", "zoom", "hl", "gl"):
            if k in resumed_plan:
                if k == "query":
                    query = str(resumed_plan[k])
                elif k == "zoom":
                    zoom = int(resumed_plan[k])
                elif k == "center":
                    center = resumed_plan[k]
    geocode_inr = 0.0
    if not resumed_plan:
        center = dict(center) if isinstance(center, dict) and center.get("lat") is not None else None
        if center is None:
            near = str(near or "").strip()
            if not near:
                raise LeadsError("Kahan? near (jaise 'Pune', 'Karol Bagh Delhi') ya center {lat, lng} dijiye.")
            from .. import maps, mapsbill
            if not maps.configured():
                raise LeadsError("Google Maps abhi connect nahi hai (server par GOOGLE_MAPS_API_KEY set nahi hai) "
                                 "- center {lat, lng} de dijiye to bina resolve ke bhi chal jaayega.")
            bill_before = mapsbill.usage(tenant)["inr"]
            try:
                c = await maps.resolve(near, tenant, near=None)
            except maps.MapsError as e:
                raise LeadsError(f"Jagah resolve nahi hui: {e}") from None
            if not c or c.get("lat") is None:
                raise LeadsError(f"'{near}' Google Maps par nahi mila - sheher / area ka naam dobara bataiye.")
            center = {"lat": c["lat"], "lng": c["lng"], "name": c.get("name") or near}
            geocode_inr = round(mapsbill.usage(tenant)["inr"] - bill_before, 4)
        try:
            cells = G.bbox_cells(center, float(sweep_km or 3.0), zoom, max_cells=leadscap.caps()["scrape_max_cells"])
        except G.GridError as e:
            raise LeadsError(str(e)) from None
        plan_dict: dict[str, Any] = {"kind": "scrape", "query": query, "center": center,
                                     "sweep_km": float(sweep_km or 3.0), "zoom": zoom,
                                     "cell_km": G.cell_km(zoom), "hl": str(hl or "en"), "gl": str(gl or "in"),
                                     "pages_per_cell": pages_max, "page_size": GP.PAGE_SIZE,
                                     "max_rows": max_rows, "cells": cells,
                                     "politeness": {"per_host_1s": SC.GOOGLE_MIN_INTERVAL,
                                                    "max_concurrency": SC.MAX_CONCURRENCY,
                                                    "robots": "google host: owner ask 5 Nov 2026; doosre hosts: "
                                                              "robots.txt obeyed (CLAUDE.md amended v0.543.0)"},
                                     "store_boundary": "facts only - no review text, no photos, no popular times"}
        run = _new_run(tenant, ask, where_label or (center or {}).get("name") or "", ["SCRAPE"],
                       plan_dict, plan_cap=400_000)
    else:
        plan_dict = resumed_plan
        cells = plan_dict.get("cells") or []
        if not cells:
            raise LeadsError("Resume ke plan mein cells nahi hain - naya run chalaiye.")
        plan_dict.setdefault("resumed_at", datetime.now(timezone.utc).isoformat())
    already = _cell_status_cells(cells)
    if already[0] >= len(cells):
        return {"ok": True, "run": run_card(run.id), "no_op": True,
                "note": "yeh plan pehle hi poora ho chuka hai - resume no-op (BADA CATALOGUE idempotency law), "
                        "ek bhi fetch nahi hua"}
    _status(run, "RUNNING")

    found = kept = duped = refused = http_calls = 0
    stopped_by_bound = False
    errors: list[str] = []
    parse_dead_streak = 0
    abort_reason = ""
    for cell in cells:
        if found >= max_rows:
            stopped_by_bound = True
            break
        if cell.get("status") == "done":
            continue                                # the resume law: a done cell is never re-fetched
        # a retried cell (blocked / error from a previous attempt) starts CLEAN - the resume IS the fresh
        # attempt, and a cell that succeeds now must land as "done", not carry its old scar forever
        cell["status"], cell["error"] = "pending", ""
        cell_found = cell_kept = cell_duped = cell_refused = 0
        for page in range(pages_max):
            if found >= max_rows:
                stopped_by_bound = True
                break
            url = GP.search_url(query, cell["lat"], cell["lng"], cell["zoom"], page,
                                hl=plan_dict.get("hl", "en"), gl=plan_dict.get("gl", "in"))
            if not SC._robots_ok(url):
                cell["status"], cell["error"] = "error", "robots: not allowed"
                break
            SC._polite(GP.SEARCH_HOST)              # per-host 1 req/s - the politeness cap, BEFORE the fetch
            try:
                page_obj = SC._get(url, tenant)
            except Exception as e:                  # noqa: BLE001 - one dead fetch is one skipped cell, named
                cell["status"], cell["error"] = "error", f"fetch: {str(e)[:140]}"
                errors.append(f"cell {cell['i']},{cell['j']}: fetch {str(e)[:80]}")
                break
            http_calls += 1
            html = getattr(page_obj, "html_content", "") or ""
            status = int(getattr(page_obj, "status", 0) or 0)
            why = _blocked.why_blocked(html, status, url)
            if why:
                # the wall is named and the run STOPS - Hoola backs off and reports, it does not muscle
                abort_reason = f"block wall: {why} @ {url}"
                cell["status"], cell["error"] = "blocked", abort_reason[:200]
                errors.append(abort_reason[:200])
                break
            try:
                entries = GP.places(html)
            except GP.GmapsParseError as e:
                cell["status"], cell["error"] = "error", f"parse: {str(e)[:140]}"
                errors.append(f"cell {cell['i']},{cell['j']}: parse {str(e)[:80]}")
                parse_dead_streak += 1
                break
            parse_dead_streak = 0
            if not entries:
                break                               # short/empty page = the cell's last page (honest sparse)
            cell["pages"] = int(cell.get("pages") or 0) + 1
            for er in entries:
                if found >= max_rows:               # the bound is checked PER ROW - a page never overshoots it
                    stopped_by_bound = True
                    break
                found += 1
                cell_found += 1
                row = _clean_row({"name": er.get("name"), "category": er.get("category") or query,
                                  "address": er.get("address"), "city": (center or {}).get("name") or place,
                                  "phone": er.get("phone"), "website": er.get("website"),
                                  "kgmid": er.get("kgmid"), "cid": er.get("cid"), "place_id": er.get("place_id"),
                                  "rating": er.get("rating"), "review_count": er.get("review_count"),
                                  "lat": er.get("lat"), "lng": er.get("lng")})
                try:
                    _write_row(tenant, run, *_identity_of(row), row, source_lane="SCRAPE",
                               source_url=url[:500], parser_version=PARSER_SCRAPE)
                    kept += 1
                    cell_kept += 1
                except LeadsError as e:
                    if "already" in str(e):
                        duped += 1
                        cell_duped += 1
                    else:
                        refused += 1
                        cell_refused += 1
            if len(entries) < GP.PAGE_SIZE:
                break                               # a short page is the last page - no page 2 fetch
        if cell.get("status") == "pending":
            cell["status"] = "done"
        elif cell.get("status") == "error" and cell.get("error", "").startswith("parse"):
            if parse_dead_streak >= 2:
                # the LOUD tripwire: two consecutive cells that are not search pages at all - the layout moved
                # (or the whole lane is being served a wall the blocked check could not name). Abort, say why.
                abort_reason = (f"layout badla ya page block hai: do lagataar cells ne APP_INITIALIZATION_STATE "
                                f"nahi diya ({str(cell.get('error'))[:120]})")
                errors.append(abort_reason)
        cell["found"], cell["kept"], cell["duped"], cell["refused"] = cell_found, cell_kept, cell_duped, cell_refused
        _checkpoint_scrape(run, plan_dict)
        if abort_reason:
            break
    _counters(run, found, kept, duped, refused)
    leadscap.record(tenant, kept)
    done_cells = sum(1 for c in cells if c.get("status") == "done")
    yields = [int(c.get("found") or 0) for c in cells if c.get("status") == "done"]
    ladder = G.choose_zoom(yields, zoom)
    if abort_reason:
        _checkpoint_scrape(run, plan_dict)
        _finish(run, "ABORTED", abort_reason[:600])
        return {"ok": False, "run": run_card(run.id), "error": abort_reason,
                "cells": {"done": done_cells, "total": len(cells)}, "bill": {"http_requests": http_calls},
                "note": "run wahin ruk gaya jahan wall mili - jo rows aayi thi woh provenance ke saath store mein hain"}
    bill = {"lane": "SCRAPE", "http_requests": http_calls, "cells_done": done_cells, "cells_total": len(cells),
            "pages_per_cell": pages_max, "page_size": GP.PAGE_SIZE, "inr": 0.0,
            "geocode_inr": geocode_inr, "yield_per_cell": yields, "ladder": ladder,
            "politeness": {"per_host_1s": SC.GOOGLE_MIN_INTERVAL, "max_concurrency": SC.MAX_CONCURRENCY},
            "note": "public listing pages, politeness paced (1 req/s) - API spend sirf ek geocode (resolve), "
                    "mapsbill ke neeche; scrape rows muft"}
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.bill = json.dumps(bill, ensure_ascii=False)[:4000]
            r.error = "; ".join(errors)[:600]
    _checkpoint_scrape(run, plan_dict)
    _finish(run, "DONE")
    return {"ok": True, "run": run_card(run.id),
            "center": {"name": (center or {}).get("name", ""), "lat": (center or {}).get("lat"),
                       "lng": (center or {}).get("lng")},
            "cells": {"done": done_cells, "total": len(cells), "zoom": zoom, "cell_km": G.cell_km(zoom)},
            "stopped_by_bound": stopped_by_bound, "ladder": ladder, "errors": errors[:5]}


# ---------------------------------------------------------------- the VENDOR lane (P4, the licensed vendor)
async def run_vendor(tenant: str, ask: str, query: str, city: str = "", max_rows: int = 1000,
                     place: str = "") -> dict:
    """P4's VENDOR lane (docs/LEADS_PLAN.md sections 4 L3, 10 P4, 12.4): ONE licensed lead-data vendor behind
    the same leads_run job shape (the research R6 pattern, leads/vendor.py). The lane is CONFIG-gated the way
    SCRAPE is opt-in gated: no vendor named (plan 12.4 is HER decision) -> the refusal names the exact config
    and nothing runs; the per-row price prices the run on the plan card BEFORE it starts and an estimate over
    the run cap is a REFUSED card whose numbers are the receipt - never a run that starts and then discovers
    its bill. ONE vendor call per run, never retried (the R6 never-pays-twice law: the vendor may bill per
    call). Every vendor row must carry its OWN source_url (Hoola's provenance law extends to vendor rows - a
    row without its record page is refused, never stored), rides the same _clean_row / identity ladder /
    dedup as every other lane, and lands with source_lane=VENDOR + parser_version. The bill uses the vendor's
    OWN reported cost when the vendor gave one and says so; otherwise it is the ESTIMATE (rows delivered x
    price) - and says so (the R6 honest-cost law)."""
    ensure_tables()
    from . import vendor as V
    from ..config import get_settings
    query = str(query or "").strip()
    if not query:
        raise LeadsError("Vendor se kya mangwana hai? Query bataiye (jaise 'dentists Pune', 'LED wholesalers Delhi').")
    raw_rows = max(1, int(max_rows or 1000))
    vok, vwhy, vkind = V.check(tenant, raw_rows)
    if not vok and vkind == "config":
        raise LeadsError(vwhy)              # nothing ran: no run row, no call, no spend - the fix is named
    p = plan(tenant, ask, ["VENDOR"], place or str(city or "").strip(), planned_rows=raw_rows)
    if not p["ok"]:
        why = "; ".join(p.get("why") or [])
        if why or p.get("need"):
            raise LeadsError(why or p.get("need", ""))
        run0 = _new_run(tenant, ask, place or str(city or "").strip(), ["VENDOR"], p)
        _finish(run0, "REFUSED", error=p.get("cap_refusal", ""))
        return {"ok": False, "run": run_card(run0.id), "plan": p}
    max_rows = min(raw_rows, leadscap.caps()["per_run"])       # the ask was checked RAW; now the working bound
    run = _new_run(tenant, ask, place or str(city or "").strip(), ["VENDOR"], p)
    _status(run, "RUNNING")
    found = kept = duped = refused = 0
    stopped_by_bound = False
    try:
        rows, meta = await V.search(query, str(city or "").strip(), max_rows, tenant)
    except V.VendorError as e:
        _finish(run, "ABORTED", str(e))
        leadscap.record(tenant, kept)
        _counters(run, found, kept, duped, refused)
        return {"ok": False, "run": run_card(run.id), "error": str(e)}
    for raw in rows or []:
        if found >= max_rows:
            stopped_by_bound = True
            break
        if not isinstance(raw, dict):
            refused += 1
            continue
        src = str(raw.get("source_url") or "").strip()
        if not src.startswith(("http://", "https://")):
            refused += 1                       # the provenance gate extends to vendor rows - refused, named
            continue
        found += 1
        row = _clean_row(raw)
        try:
            _write_row(tenant, run, *_identity_of(row), row, source_lane="VENDOR",
                       source_url=src[:500], parser_version=PARSER_VENDOR)
            kept += 1
        except LeadsError as e:
            if "already" in str(e):
                duped += 1
            else:
                refused += 1
    leadscap.record(tenant, kept)
    _counters(run, found, kept, duped, refused)
    st = get_settings()
    price = float(st.leads_vendor_price_per_row_inr or 0.0)
    est_before = V.estimate_inr(raw_rows, st)
    actual = meta["cost_inr"] if meta["reported"] else round(price * found, 4)
    bill = {"lane": "VENDOR", "vendor": str(st.leads_vendor_name or "").strip(),
            "rows_returned": found, "rows_kept": kept, "price_per_row_inr": price,
            "estimate_inr_before": est_before, "inr": actual,
            "cost_reported_by_vendor": bool(meta["reported"]),
            "note": ("vendor ne apna khud ka cost_inr bataya - bill uska number hai"
                     if meta["reported"] else
                     "ESTIMATE - vendor ne cost report nahi kiya (rows delivered x price; plan-time estimate "
                     "raw_rows par bana tha)")}
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.bill = json.dumps(bill, ensure_ascii=False)[:4000]
    _finish(run, "DONE")
    return {"ok": True, "run": run_card(run.id),
            "vendor": {"name": bill["vendor"], "price_per_row_inr": price},
            "stopped_by_bound": stopped_by_bound}


def _new_run(tenant: str, ask: str, place: str, lanes: list[str], plan_card: dict, plan_cap: int = 8000) -> LeadRun:
    with _s() as s:
        run = LeadRun(tenant_id=tenant, ask=ask[:3000], place=place[:200], lanes=json.dumps(lanes),
                      plan=json.dumps(plan_card, ensure_ascii=False, default=str)[:plan_cap],
                      provenance=json.dumps({"parser_version": PARSER_VERSION, "engine": "hoola-leads", "v": 1}))
        s.add(run)
        s.flush()
        s.expunge(run)
        return run


def _s():
    from ..db import session
    return session()


def _status(run: LeadRun, status: str) -> None:
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.status = status
            if status == "DONE":
                r.finished_at = datetime.now(timezone.utc)


def _counters(run: LeadRun, found: int, kept: int, duped: int, refused: int) -> None:
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.found, r.kept, r.duped, r.refused = found, kept, duped, refused


def _finish(run: LeadRun, status: str, error: str = "") -> None:
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.status = status
            r.finished_at = datetime.now(timezone.utc)
            if error:
                r.error = error[:600]


def _delete_run(run_id: str) -> None:
    with _s() as s:
        r = s.get(LeadRun, run_id)
        if r:
            s.delete(r)


# ---------------------------------------------------------------- the store (provenance gate + dedup)
def add_row(tenant: str, row: dict, source_lane: str, source_url: str, run_id: str = "",
            parser_version: str = PARSER_VERSION) -> dict:
    """One row into the store. The provenance gate FIRST: no source_lane from rules.LANES, no source_url - no row.
    A duplicate key is not an error: the card says 'already' and the caller counts it as duped."""
    ensure_tables()
    if source_lane not in R.LANES:
        raise LeadsError(f"source_lane '{source_lane}' galat hai - lanes: {', '.join(R.LANES)}. "
                         f"Bina valid source ki row store nahi hoti.")
    if not str(source_url or "").strip():
        raise LeadsError("source_url khaali hai - har row ke saath uska source zaroori hai (provenance).")
    row = _clean_row(row)
    ktype, kval = identity_key(row)
    return _write_row(tenant, None, ktype, kval, row, str(run_id or ""), source_lane, source_url[:500], parser_version)


def _write_row(tenant: str, run: LeadRun | None, ktype: str, kval: str, row: dict, run_id: str = "",
               source_lane: str = "", source_url: str = "", parser_version: str = PARSER_VERSION) -> dict:
    if run is not None:
        run_id = run.id
    with _s() as s:
        exists = s.query(LeadContact).filter(LeadContact.tenant_id == tenant, LeadContact.key_type == ktype,
                                             LeadContact.key_value == kval).first()
        if exists is not None:
            raise LeadsError(f"already: {ktype}/{kval}")
        try:
            c = LeadContact(tenant_id=tenant, run_id=run_id, key_type=ktype, key_value=kval[:120],
                            name=row.get("name", "")[:200], category=row.get("category", "")[:120],
                            address=row.get("address", ""), city=row.get("city", "")[:80],
                            state=row.get("state", "")[:80], pincode=row.get("pincode", "")[:10],
                            phone=row.get("phone", ""), website=row.get("website", "")[:300],
                            email=row.get("email", "")[:200], source_lane=source_lane, source_url=source_url,
                            parser_version=parser_version)
            if row.get("rating") not in (None, ""):
                c.rating = float(row["rating"])
            if row.get("review_count") not in (None, ""):
                c.review_count = int(row["review_count"])
            if row.get("lat") not in (None, "") and row.get("lng") not in (None, ""):
                c.lat, c.lng = float(row["lat"]), float(row["lng"])
            s.add(c)
            s.flush()
            return view_row(c)
        except IntegrityError:
            raise LeadsError(f"already: {ktype}/{kval}") from None


def view_row(c: LeadContact) -> dict:
    return {"id": c.id, "run_id": c.run_id, "key_type": c.key_type, "key_value": c.key_value, "name": c.name,
            "category": c.category, "address": c.address, "city": c.city, "state": c.state, "pincode": c.pincode,
            "phone": c.phone, "website": c.website, "email": c.email, "email_grade": c.email_grade,
            "socials": c.socials or {}, "rating": c.rating, "review_count": c.review_count, "lat": c.lat,
            "lng": c.lng, "source_lane": c.source_lane, "source_url": c.source_url,
            "parser_version": c.parser_version, "opt_out": bool(c.opt_out), "fetched_at": _iso(c.fetched_at),
            "enriched_at": _iso(c.enriched_at), "enriched_from": c.enriched_from, "enrich_note": c.enrich_note}


def _iso(d: datetime | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


# ---------------------------------------------------------------- reading the store
def _filters(tenant: str, q: str = "", city: str = "", category: str = "", lane: str = "",
             has_phone: bool = False, has_email: bool = False, opt_out: bool | None = None):
    conds = [LeadContact.tenant_id == tenant]
    if q:
        like = f"%{q.strip().lower()}%"
        conds.append(LeadContact.name.ilike(like) | LeadContact.category.ilike(like) | LeadContact.address.ilike(like))
    if city:
        conds.append(LeadContact.city.ilike(f"%{city.strip()}%"))
    if category:
        conds.append(LeadContact.category.ilike(f"%{category.strip()}%"))
    if lane:
        conds.append(LeadContact.source_lane == lane.upper())
    if has_phone:
        conds.append(LeadContact.phone != "")
    if has_email:
        conds.append(LeadContact.email != "")
    if opt_out is not None:
        conds.append(LeadContact.opt_out == bool(opt_out))
    return conds


def rows(tenant: str, q: str = "", city: str = "", category: str = "", lane: str = "", has_phone: bool = False,
         has_email: bool = False, opt_out: bool | None = None, limit: int = 50, offset: int = 0) -> dict:
    ensure_tables()
    conds = _filters(tenant, q, city, category, lane, has_phone, has_email, opt_out)
    with _s() as s:
        total = s.query(LeadContact).filter(*conds).count()
        got = (s.query(LeadContact).filter(*conds).order_by(LeadContact.fetched_at.desc(), LeadContact.id)
               .offset(max(0, offset)).limit(min(max(1, limit), 500)).all())
        return {"total": total, "rows": [view_row(c) for c in got], "limit": limit, "offset": offset}


def store_summary(tenant: str) -> dict:
    ensure_tables()
    with _s() as s:
        base = s.query(LeadContact).filter(LeadContact.tenant_id == tenant)
        return {"rows": base.count(), "with_phone": base.filter(LeadContact.phone != "").count(),
                "with_email": base.filter(LeadContact.email != "").count(),
                "opted_out": base.filter(LeadContact.opt_out.is_(True)).count(),
                "by_lane": {l: base.filter(LeadContact.source_lane == l).count() for l in R.LANES}}


# ---------------------------------------------------------------- the runs
def _view(run: LeadRun) -> dict:
    return {"id": run.id, "tenant": run.tenant_id, "ask": run.ask, "place": run.place, "lanes": json.loads(run.lanes or "[]"),
            "plan": json.loads(run.plan or "{}"), "status": run.status, "found": run.found, "kept": run.kept,
            "duped": run.duped, "refused": run.refused, "bill": json.loads(run.bill or "{}"),
            "provenance": json.loads(run.provenance or "{}"), "error": run.error,
            "created_at": _iso(run.created_at), "finished_at": _iso(run.finished_at)}


def run_card(run_id: str) -> dict | None:
    ensure_tables()
    with _s() as s:
        r = s.get(LeadRun, run_id)
        return _view(r) if r else None


def runs(tenant: str, limit: int = 20) -> list[dict]:
    ensure_tables()
    with _s() as s:
        got = (s.query(LeadRun).filter(LeadRun.tenant_id == tenant).order_by(LeadRun.created_at.desc())
               .limit(min(max(1, limit), 100)).all())
        return [_view(r) for r in got]


# ---------------------------------------------------------------- exports (provenance belt)
EXPORT_COLUMNS = ("name", "phone", "category", "address", "city", "state", "pincode", "email", "email_grade",
                  "website", "socials", "rating", "review_count", "lat", "lng", "key_type", "key_value",
                  "source_lane", "source_url", "parser_version", "fetched_at", "opt_out", "run_id")


def export_csv(tenant: str, q: str = "", city: str = "", category: str = "", lane: str = "",
               has_phone: bool = False, has_email: bool = False, run_id: str = "", opt_out: bool | None = False) -> dict:
    """The export that refuses to ship an unprovenanced row (the verify gate). opt_out rows are EXCLUDED by
    default - the campaign desk honours opt-out, so a raw export must not smuggle them in either."""
    ensure_tables()
    conds = _filters(tenant, q, city, category, lane, has_phone, has_email, opt_out)
    if run_id:
        conds.append(LeadContact.run_id == run_id)
    with _s() as s:
        got = (s.query(LeadContact).filter(*conds).order_by(LeadContact.fetched_at.desc())
               .limit(20000).all())
        unprovenanced = [c.id for c in got if not c.source_lane or not c.source_url]
        if unprovenanced:
            raise LeadsError(f"{len(unprovenanced)} rows bina provenance ke hain (ids: {', '.join(unprovenanced[:5])}..."
                             f") - export REFUSE: bina source ki row jaati hi nahi.")
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(EXPORT_COLUMNS)
        for c in got:
            w.writerow([c.name, c.phone, c.category, c.address, c.city, c.state, c.pincode, c.email, c.email_grade,
                        c.website, json.dumps(c.socials or {}, ensure_ascii=False), "" if c.rating is None else c.rating,
                        "" if c.review_count is None else c.review_count, "" if c.lat is None else c.lat,
                        "" if c.lng is None else c.lng, c.key_type, c.key_value, c.source_lane, c.source_url,
                        c.parser_version, _iso(c.fetched_at), int(bool(c.opt_out)), c.run_id])
        name = f"leads-export-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{len(got)}.csv"
        return {"filename": name, "rows": len(got), "csv": buf.getvalue(),
                "provenance": {"every_row_has": ["source_lane", "source_url", "parser_version", "fetched_at"]}}


# ---------------------------------------------------------------- outreach LEDGER + campaign hand-off
def campaign_list(tenant: str, name: str, q: str = "", city: str = "", category: str = "", lane: str = "",
                  has_phone: bool = True, run_id: str = "", confirm: bool = False) -> dict:
    """HER tap arrives here: copy selected rows into a LeadList the campaign desk consumes. Only rows WITH a
    phone can go (campaigns call phones), consent is pre-filled False for every copied row (the sending side
    still needs the desk's consent machinery), and the whole act lands in the LeadOutreach ledger.
    v0.545.0 P5: TWO taps - confirm=False (the default) returns the CONFIRM CARD and creates NOTHING (no list,
    no refs, no ledger rows: the plan's "her tap, confirm card"), confirm=True is the second tap that builds.
    The card names the numbers BEFORE anything moves: rows that can go, rows without a phone that stay, and
    the opt_out rows the filter already excluded (the campaign desk honours opt-out again at send time)."""
    ensure_tables()
    conds = _filters(tenant, q, city, category, lane, True, False, False)
    if run_id:
        conds.append(LeadContact.run_id == run_id)
    all_conds = _filters(tenant, q, city, category, lane, False, False, None)
    if run_id:
        all_conds.append(LeadContact.run_id == run_id)
    from ..db import Lead, LeadList
    with _s() as s:
        got = s.query(LeadContact).filter(*conds).order_by(LeadContact.fetched_at.desc()).limit(20000).all()
        no_phone = (s.query(LeadContact).filter(*all_conds, LeadContact.phone == "").count())
        opt_out_excluded = (s.query(LeadContact).filter(*all_conds, LeadContact.opt_out.is_(True)).count())
        if not confirm:
            return {"ok": True, "kind": "leads_handoff_confirm", "confirm_required": True,
                    "list_name": name[:200], "rows": len(got), "rows_without_phone": no_phone,
                    "opt_out_excluded": opt_out_excluded, "run_id": run_id,
                    "consent": "har row consent=False - bhejna campaign desk ke consent machinery se hi hoga",
                    "never": R.NEVER[0],
                    "confirm": R.HANDOFF_CONFIRM}
        if not got:
            raise LeadsError("Is filter par phone waali koi row nahi - campaign list khaali rahegi.")
        ll = LeadList(tenant_id=tenant, name=name[:200], source_filename=f"leads-store:{run_id or 'store'}",
                      columns=["name", "phone"], has_consent_column=True, total_rows=len(got), valid=len(got),
                      invalid=0, duplicates=0, opted_in=0)
        s.add(ll)
        s.flush()
        for c in got:
            l = Lead(name=c.name or None, phone=c.phone, opted_in=False,
                     extra={"lead_contact_id": c.id, "source_lane": c.source_lane, "source_url": c.source_url,
                            "category": c.category, "city": c.city})
            l.list_id = ll.id
            s.add(l)
            s.flush()
            s.add(LeadListRef(tenant_id=tenant, contact_id=c.id, lead_row_id=l.id, list_id=ll.id))
            s.add(LeadOutreach(tenant_id=tenant, contact_id=c.id, kind="campaign_list", ref=ll.id, desk="campaign"))
        return {"ok": True, "kind": "leads_handoff", "confirmed": True, "list_id": ll.id, "name": ll.name,
                "rows": len(got), "rows_without_phone": no_phone, "opt_out_excluded": opt_out_excluded,
                "consent": "har row consent=False - bhejna campaign desk ke consent machinery se hi hoga",
                "note": "engine ne khud kuch nahi bheja; sirf list bani (uske doosre tap par)"}


def outreach_log(tenant: str, kind: str = "", limit: int = 200) -> dict:
    """The opt-out ledger, READABLE (P5): every outreach event - which row left the store, through which desk,
    when, against which list / campaign / draft. A forgotten row's events stay (the history is not the person);
    its name shows as gone."""
    ensure_tables()
    with _s() as s:
        q = s.query(LeadOutreach).filter(LeadOutreach.tenant_id == tenant)
        if kind:
            if kind not in R.OUTREACH_KINDS:
                raise LeadsError(f"kind '{kind}' koi outreach kind nahi hai - kinds hain: "
                                 f"{', '.join(R.OUTREACH_KINDS)}")
            q = q.filter(LeadOutreach.kind == kind)
        got = q.order_by(LeadOutreach.at.desc(), LeadOutreach.id).limit(min(max(1, int(limit)), 1000)).all()
        ids = list({r.contact_id for r in got if r.contact_id})
        live = {c.id: c for c in s.query(LeadContact).filter(LeadContact.id.in_(ids)).all()} if ids else {}
        items = [{"id": r.id, "kind": r.kind, "desk": r.desk, "ref": r.ref, "at": _iso(r.at),
                  "contact_id": r.contact_id,
                  "name": (live[r.contact_id].name or "(naam nahi)") if r.contact_id in live else "(row miti hui)",
                  "key_type": live[r.contact_id].key_type if r.contact_id in live else "",
                  "key_value": live[r.contact_id].key_value if r.contact_id in live else "",
                  "phone": live[r.contact_id].phone if r.contact_id in live else ""} for r in got]
        by_kind: dict[str, int] = {}
        for it in items:
            by_kind[it["kind"]] = by_kind.get(it["kind"], 0) + 1
        return {"kind": "leads_outreach_log", "events": items, "count": len(items), "by_kind": by_kind,
                "never": R.NEVER[0]}


def record_outreach(tenant: str, contact_ids: list[str], kind: str, ref: str, desk: str) -> int:
    """The desk-side ledger write (campaign_sent / email_sent) - called BY the desks when SHE taps, never by a run.
    v0.545.0: the kind and the desk are CHECKED against rules.OUTREACH_KINDS / OUTREACH_DESKS - a desk cannot
    invent a ledger kind (the vocabulary is one place, rules.py)."""
    ensure_tables()
    if kind not in R.OUTREACH_KINDS:
        raise LeadsError(f"kind '{kind}' koi outreach kind nahi hai - kinds hain: {', '.join(R.OUTREACH_KINDS)}")
    if desk not in R.OUTREACH_DESKS:
        raise LeadsError(f"desk '{desk}' koi desk nahi hai - desks hain: {', '.join(R.OUTREACH_DESKS)}")
    with _s() as s:
        n = 0
        for cid in contact_ids:
            s.add(LeadOutreach(tenant_id=tenant, contact_id=cid, kind=kind[:20], ref=ref[:120], desk=desk[:20]))
            n += 1
        return n


def note_campaign_sends(tenant: str, campaign_id: str, lead_row_ids: list[int]) -> int:
    """worker.send_batches calls this AFTER each successful WhatsApp template send: every OutboundMessage whose
    lead row is a leads-store COPY (LeadListRef) gets its campaign_sent ledger row - the ledger records the
    moment of truth (the send), not the queueing. Lead rows that are not store copies (her own imported lists)
    stay out of this ledger - they were never leads-store rows."""
    ids = [int(x) for x in (lead_row_ids or []) if x]
    if not ids:
        return 0
    ensure_tables()
    with _s() as s:
        refs = s.query(LeadListRef).filter(LeadListRef.tenant_id == tenant,
                                           LeadListRef.lead_row_id.in_(ids)).all()
        for r in refs:
            s.add(LeadOutreach(tenant_id=tenant, contact_id=r.contact_id, kind="campaign_sent",
                               ref=str(campaign_id)[:120], desk="campaign"))
        return len(refs)


def note_email_sends(tenant: str, addrs: list[str], ref: str) -> int:
    """mailbox.service.send_draft calls this AFTER an email leaves: the lead_contacts rows whose email is one of
    the draft's recipients get their email_sent ledger row. The match is by the row's own email address - an
    address the store never saw records nothing (honest ledger, no guessed joins)."""
    clean = list({str(a or "").strip().lower() for a in (addrs or []) if str(a or "").strip()})
    if not clean:
        return 0
    ensure_tables()
    with _s() as s:
        got = s.query(LeadContact).filter(LeadContact.tenant_id == tenant, LeadContact.email.in_(clean)).all()
        for c in got:
            s.add(LeadOutreach(tenant_id=tenant, contact_id=c.id, kind="email_sent",
                               ref=str(ref)[:120], desk="email"))
        return len(got)


def set_opt_out(tenant: str, contact_id: str, opt_out: bool = True) -> dict:
    ensure_tables()
    with _s() as s:
        c = s.get(LeadContact, contact_id)
        if c is None or c.tenant_id != tenant:
            raise LeadsError("Row nahi mili.")
        c.opt_out = bool(opt_out)
        return {"ok": True, "id": c.id, "opt_out": bool(c.opt_out)}


# ---------------------------------------------------------------- forget (the DPO duty)
def forget(tenant: str, run_id: str = "", row_ids: list[str] | None = None, all_rows: bool = False) -> dict:
    """Delete rows / a whole run's rows on her word. The cap ledger survives (the day's count is history, not
    personal data). Returns the counts, says the DPDP duty in the card."""
    ensure_tables()
    if not run_id and not row_ids and not all_rows:
        raise LeadsError("Kya delete karna hai: run_id, ya row_ids, ya all_rows=True (sab).")
    with _s() as s:
        conds = [LeadContact.tenant_id == tenant]
        if run_id:
            conds.append(LeadContact.run_id == run_id)
        if row_ids:
            conds.append(LeadContact.id.in_(list(row_ids)))
        if all_rows:
            conds = [LeadContact.tenant_id == tenant]
        query = s.query(LeadContact).filter(*conds)
        n = query.count()
        ids = [c.id for c in query.all()]
        if ids:
            s.query(LeadListRef).filter(LeadListRef.tenant_id == tenant, LeadListRef.contact_id.in_(ids)).delete(synchronize_session=False)
        query.delete(synchronize_session=False)
        if run_id:
            r = s.get(LeadRun, run_id)
            if r is not None and r.tenant_id == tenant:
                s.delete(r)
        return {"ok": True, "deleted": n, "dpdp": "purpose limitation + erasure (DPO duty) - cap ledger rakha "
                "gaya kyunki woh din ka hisaab hai, personal data nahi"}
