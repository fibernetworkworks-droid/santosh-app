"""Propagent Sahayak tools (real estate agent / broker). `propagent_dekho` only reads; `propagent` does the work. A listing going
public, any message to a client / owner and any paper that names money are only CARDS here: her tap in the app decides them."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

PROPAGENT_TOOLS = [
    {"name": "propagent", "description": (
        "Real estate agent / broker's coworker. Facts (price, rent, area, dates, rates) ONLY from her / the owner; never invent. "
        "action=settings (owner): business, agent_name, phone, office, state (MH...), city, rera_agent_no (MahaRERA A5..), "
        "rera_valid_until, coc (competency certificate date), gstin, gst_on, gst_pct, sale_pct (her brokerage % per side), "
        "rent_months, rates {area: {stamp_pct, cess_pct, women_less_pct, reg_pct, reg_cap, reg_flat}} (HER numbers from IGR), "
        "visit_minutes, gap_minutes, stale_days, morning_time, terms, rules. "
        "action=listing: listing (existing L-0001, else new), words (her description), purpose sale|rent|lease, kind flat|house|"
        "row_house|plot|shop|office|warehouse|land|pg, title, project, new_project (RERA project), rera_project_no, locality, city, pin, "
        "address (private), bhk, carpet_sqft, built_sqft, plot_sqft, floor, facing, furnishing, parking, age_years, price, rent, deposit, "
        "maintenance, negotiable, available_from, amenities, description, owner_name, owner_phone, owner_nri, mandate {consent, "
        "exclusive, commission_pct, months, until, file_id}, status. action=photo: listing, file_id, photo_kind photo|qr|plan (qr = "
        "MahaRERA project QR). action=describe: listing (text from her facts). action=publish: listing, where page|copy|sheet -> only "
        "a card for HER tap (never say it is live). action=unpublish. action=poster: listing (Brand Sahayak proof). "
        "action=lead: lead (existing), name, phone, role buyer|tenant, words (what they asked: '2BHK Akola 40-50 lakh'), source "
        "walk_in|call|portal|website|referral|whatsapp|hoarding|ads|cold, consent, need {budget_min, budget_max, bhk, localities, "
        "purpose, kind, furnishing, nri, loan, min_carpet}, next_when, next_what, stage, notes, no_messages. action=share: lead, "
        "listings [..] -> message card. action=message: to lead|owner, ref (lead or listing), text -> message card. "
        "action=visit: lead, listings [..], day, start -> plan + message cards. action=visit_done: visit, feedback {L-0001: liked|no|"
        "price|think}, status done|cancelled|no_show, notes. action=deal: listing, lead, price, deposit, market_value (ready reckoner, "
        "her number), token, token_mode, rate_area, women, buyer_nri, seller_nri, tenant_business, loan, society, agreement_by, "
        "registration_by, buyer_commission {pct|months|amount}, seller_commission {...}, ids_text (Aadhaar / PAN she gave -> "
        "Pehchaan Locker), ids_side buyer|seller, ids_person. action=deal_update: deal + same fields. action=deal_status: deal, status "
        "draft|token|agreement|registered|done|fell. action=check: deal, key, done. action=document: deal, doc token_receipt|offer_letter|"
        "agreement_checklist|commission_bill -> card. action=commission_got (owner): deal, side buyer|seller, amount, mode, ref. "
        "action=forget (owner): lead or listing (after the deal ends, DPDP). action=sheet (portal Excel), register (Excel)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "listing", "photo", "describe", "publish", "unpublish", "poster", "lead", "share",
                                               "message", "visit", "visit_done", "deal", "deal_update", "deal_status", "check", "document",
                                               "commission_got", "forget", "sheet", "register"]},
         "listing": {"type": "string"}, "lead": {"type": "string"}, "deal": {"type": "string"}, "visit": {"type": "string"},
         "words": {"type": "string"}, "purpose": {"type": "string"}, "kind": {"type": "string"}, "title": {"type": "string"},
         "project": {"type": "string"}, "new_project": {"type": "boolean"}, "rera_project_no": {"type": "string"},
         "locality": {"type": "string"}, "city": {"type": "string"}, "pin": {"type": "string"}, "address": {"type": "string"},
         "bhk": {"type": "integer"}, "carpet_sqft": {"type": "number"}, "built_sqft": {"type": "number"}, "plot_sqft": {"type": "number"},
         "floor": {"type": "string"}, "facing": {"type": "string"}, "furnishing": {"type": "string"}, "parking": {"type": "string"},
         "age_years": {"type": "number"}, "price": {}, "rent": {}, "deposit": {}, "maintenance": {}, "negotiable": {"type": "boolean"},
         "available_from": {"type": "string"}, "amenities": {}, "description": {"type": "string"}, "owner_name": {"type": "string"},
         "owner_phone": {"type": "string"}, "owner_nri": {"type": "boolean"}, "mandate": {"type": "object"}, "status": {"type": "string"},
         "file_id": {"type": "string"}, "photo_kind": {"type": "string"}, "where": {"type": "string"}, "name": {"type": "string"},
         "phone": {"type": "string"}, "role": {"type": "string"}, "source": {"type": "string"}, "consent": {"type": "boolean"},
         "need": {"type": "object"}, "next_when": {"type": "string"}, "next_what": {"type": "string"}, "stage": {"type": "string"},
         "notes": {"type": "string"}, "no_messages": {"type": "boolean"}, "listings": {"type": "array", "items": {"type": "string"}},
         "to": {"type": "string"}, "ref": {"type": "string"}, "text": {"type": "string"}, "day": {"type": "string"},
         "start": {"type": "string"}, "feedback": {"type": "object"}, "market_value": {}, "token": {}, "token_mode": {"type": "string"},
         "rate_area": {"type": "string"}, "women": {"type": "boolean"}, "buyer_nri": {"type": "boolean"}, "seller_nri": {"type": "boolean"},
         "tenant_business": {"type": "boolean"}, "loan": {"type": "boolean"}, "society": {"type": "boolean"},
         "agreement_by": {"type": "string"}, "registration_by": {"type": "string"}, "buyer_commission": {"type": "object"},
         "seller_commission": {"type": "object"}, "ids_text": {"type": "string"}, "ids_side": {"type": "string"},
         "ids_person": {"type": "string"}, "key": {"type": "string"}, "done": {"type": "boolean"}, "doc": {"type": "string"},
         "side": {"type": "string"}, "amount": {}, "mode": {"type": "string"}, "note": {"type": "string"},
         "business": {"type": "string"}, "agent_name": {"type": "string"}, "office": {"type": "string"}, "state": {"type": "string"},
         "rera_agent_no": {"type": "string"}, "rera_valid_until": {"type": "string"}, "coc": {"type": "string"},
         "gstin": {"type": "string"}, "gst_on": {"type": "boolean"}, "gst_pct": {"type": "number"}, "sale_pct": {"type": "number"},
         "rent_months": {"type": "number"}, "rates": {"type": "object"}, "visit_minutes": {"type": "integer"},
         "gap_minutes": {"type": "integer"}, "stale_days": {"type": "integer"}, "morning_time": {"type": "string"},
         "terms": {"type": "string"}, "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "propagent_dekho", "description": (
        "Read the property desk (nothing changes). what=day (today's visits, follow-ups, dates, cards waiting, stale listings, "
        "commission due) | listings (status, purpose, q) | listing (listing) | leads (stage, q) | lead (lead) | matches (lead: listings "
        "that fit with reasons) | buyers (listing: leads that fit) | visits (day, status) | visit (visit) | deals (status) | deal (deal: "
        "stamp duty estimate from her rates, TDS note, commission) | commission | cards (status) | settings | steps (step=rera|igr|"
        "portal|tds) | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "listings", "listing", "leads", "lead", "matches", "buyers", "visits", "visit", "deals",
                                             "deal", "commission", "cards", "settings", "steps", "rules"]},
         "listing": {"type": "string"}, "lead": {"type": "string"}, "visit": {"type": "string"}, "deal": {"type": "string"},
         "status": {"type": "string"}, "purpose": {"type": "string"}, "q": {"type": "string"}, "stage": {"type": "string"},
         "day": {"type": "string"}, "step": {"type": "string"}},
         "required": ["what"]}},
]
PROPAGENT_LABELS = {"propagent": "Property ka kaam kar raha hoon", "propagent_dekho": "Listings aur graahak dekh raha hoon"}

OWNER_ONLY = ("settings", "commission_got", "forget", "deal_status")
_LISTING_ARGS = ("purpose", "kind", "title", "project", "new_project", "rera_project_no", "locality", "city", "pin", "address", "bhk",
                 "carpet_sqft", "built_sqft", "plot_sqft", "floor", "facing", "furnishing", "parking", "age_years", "price", "rent",
                 "deposit", "maintenance", "negotiable", "available_from", "amenities", "description", "owner_name", "owner_phone",
                 "owner_nri", "mandate", "status", "notes")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _deal_kw(a: dict, S) -> dict:
    out = {k: a[k] for k in S._DEAL_KEYS if k in a}
    for side in ("buyer", "seller"):
        if isinstance(a.get(f"{side}_commission"), dict):
            out[f"{side}_commission"] = a[f"{side}_commission"]
    return out


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..propagent import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Property desk graahak ke liye nahi.")
    if action in OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "listing":
            return S.save_listing(t, _s(a.get("listing")), _s(a.get("words")), actor, conv, **{k: a[k] for k in _LISTING_ARGS if k in a})
        if action == "photo":
            if not a.get("file_id"):
                raise ToolError("file_id chahiye (photo).")
            return S.attach_file(t, _s(a.get("listing")), _s(a.get("file_id")), _s(a.get("photo_kind") or "photo"))
        if action == "describe":
            return S.describe(t, _s(a.get("listing")))
        if action == "publish":
            return S.publish_request(t, _s(a.get("listing")), _s(a.get("where") or "page"), actor, conv)
        if action == "unpublish":
            return S.unpublish(t, _s(a.get("listing")))
        if action == "poster":
            return S.poster(t, _s(a.get("listing")), conv)
        if action == "lead":
            return S.save_lead(t, _s(a.get("lead")), _s(a.get("name")), _s(a.get("phone")), _s(a.get("role")), _s(a.get("words")),
                               _s(a.get("source")), a.get("consent"), a.get("need") if isinstance(a.get("need"), dict) else None,
                               _s(a.get("next_when")), _s(a.get("next_what")), _s(a.get("notes")), _s(a.get("stage")),
                               a.get("no_messages"), actor, conv)
        if action == "share":
            return S.share_request(t, _s(a.get("lead")), a.get("listings") or None, _s(a.get("text")), actor, conv)
        if action == "message":
            return S.message_request(t, _s(a.get("to") or "lead"), _s(a.get("ref") or a.get("lead") or a.get("listing")), _s(a.get("text")),
                                     actor, conv)
        if action == "visit":
            return S.plan_visit(t, _s(a.get("lead")), list(a.get("listings") or []), _s(a.get("day")), _s(a.get("start") or "10:00"), actor, conv)
        if action == "visit_done":
            fb = a.get("feedback")
            return S.visit_done(t, _s(a.get("visit")), fb if isinstance(fb, dict) else None, _s(a.get("status") or "done"), _s(a.get("notes")))
        if action == "deal":
            return S.deal_new(t, _s(a.get("listing")), _s(a.get("lead")), actor, conv, **_deal_kw(a, S),
                              **({"ids_text": a["ids_text"], "ids_side": _s(a.get("ids_side") or "buyer"), "ids_person": _s(a.get("ids_person"))}
                                 if a.get("ids_text") else {}))
        if action == "deal_update":
            return S.deal_update(t, _s(a.get("deal")), _s(a.get("ids_text")), _s(a.get("ids_side") or "buyer"), _s(a.get("ids_person")),
                                 actor, conv, **_deal_kw(a, S))
        if action == "deal_status":
            return S.deal_status(t, _s(a.get("deal")), _s(a.get("status")), actor, _s(a.get("note")))
        if action == "check":
            return S.check_item(t, _s(a.get("deal")), _s(a.get("key")), a.get("done", True) is not False)
        if action == "document":
            return S.document_request(t, _s(a.get("deal")), _s(a.get("doc") or a.get("kind")), actor, conv)
        if action == "commission_got":
            return S.commission_received(t, _s(a.get("deal")), _s(a.get("side")), a.get("amount"), _s(a.get("mode")), _s(a.get("ref")),
                                         _s(a.get("day")))
        if action == "forget":
            if a.get("lead"):
                return S.forget_lead(t, _s(a.get("lead")))
            return S.forget_owner(t, _s(a.get("listing")))
        if action == "sheet":
            return S.portal_sheet(t, a.get("listings") or None, conv)
        if action == "register":
            return S.register_file(t, conv)
    except (S.PropError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..propagent import rules as R
    from ..propagent import service as S
    t = ctx.tenant_id
    if (getattr(ctx, "actor", "owner") or "").startswith("customer:"):
        raise ToolError("Property desk ki jaankari graahak ke liye nahi.")
    try:
        if what == "day":
            return S.day(t)
        if what == "listings":
            return {"listings": S.listings(t, _s(a.get("status")), _s(a.get("purpose")), _s(a.get("q")))}
        if what == "listing":
            return S.listing_view(t, _s(a.get("listing")))
        if what == "leads":
            return {"leads": S.leads(t, _s(a.get("stage")), _s(a.get("q")))}
        if what == "lead":
            return S.lead_view(t, _s(a.get("lead")))
        if what == "matches":
            return S.matches(t, _s(a.get("lead")))
        if what == "buyers":
            return S.buyers_for(t, _s(a.get("listing")))
        if what == "visits":
            return {"visits": S.visits(t, _s(a.get("day")), _s(a.get("status")))}
        if what == "visit":
            return S.visit_view(t, _s(a.get("visit")))
        if what == "deals":
            return {"deals": S.deals(t, _s(a.get("status")))}
        if what == "deal":
            return S.deal_view(t, _s(a.get("deal")))
        if what == "commission":
            return S.commission_report(t)
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status")))}
        if what == "settings":
            return S.settings(t)
        if what == "steps":
            return S.official_steps(_s(a.get("step") or "rera"))
        if what == "rules":
            return {"never": list(R.NEVER), "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES]}
    except (S.PropError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def propagent(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def propagent_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


PROPAGENT_HANDLERS = {"propagent": propagent, "propagent_dekho": propagent_dekho}
