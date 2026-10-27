"""Artist Sahayak tools (musician's manager). `artist_manager_dekho` only reads; `artist_manager` does the work.

A reply / contract / invoice / payment request / message going out, a hold becoming a confirmed gig, release metadata going
final and a payout statement become CARDS here; only HER tap in the app (API) decides them. A gig that overlaps another
held / confirmed gig of the artist (or leaves less than her travel gap, or needs a member booked elsewhere) is refused in code.
Hoola never invents a fee, date, royalty or code, never sends a message by itself and never takes or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "artist", "reg", "block", "unblock", "offer", "gig", "hold", "release_hold", "confirm", "reply",
            "contract", "invoice", "pay_request", "message", "paid", "tds", "expense", "done", "cancel", "travel", "release",
            "release_final", "release_step", "royalty", "payout", "payout_paid", "forget", "forget_artist"]
_OWNER_ONLY = {"settings", "artist", "reg", "block", "unblock", "paid", "tds", "expense", "done", "cancel", "royalty",
               "payout_paid", "forget", "forget_artist"}

ARTISTMGR_TOOLS = [
    {"name": "artist_manager", "description": (
        "Musician's manager. NEVER invent a fee, date, royalty, ISRC or distributor term; ask her. Cards = only her tap decides "
        "(say 'aapki haan ka card bheja hai'). A double-booked artist is refused by the server. action=settings*: agency, gstin, "
        "upi_id, commission_pct, royalty_pct, same_city_gap / travel_gap (minutes), hold_hours, advance_pct, balance_days, "
        "distributors [{name, share_pct, lead_days, payout}], terms. action=artist*: name, kind singer|band|dj|instrumentalist|"
        "composer|lyricist|classical|folk, genre, city, phone, members [{name, role, phone, split_pct}], min_fee, rider {tech, "
        "hospitality, travel, stay}, gstin. action=reg*: artist, key iprs|isamra|ppl|isrc|ipi|distributor|content_id|copyright|"
        "pan_gst, status none|applied|done|na, ref. action=block* / unblock*: artist, day, day_to, note | block_id. "
        "action=offer: text (pasted offer = data) and/or artist, day, start, end, set_minutes, city, venue, fee, promoter, phone, "
        "event, event_type. action=gig: gig + fields to change (staff can't change a confirmed fee). action=hold (hours) / release_hold / confirm (card) / reply "
        "(text, card) / contract (card) / invoice (card) / pay_request (stage advance|balance or amount, card): gig. action=message: "
        "text, gig or artist, to (promoter|artist|member name). action=paid*: gig, amount, mode, ref. action=tds*: gig, amount. "
        "action=expense*: gig, what, amount, paid_by manager|artist|promoter. action=done* / cancel* (reason) / travel / forget*: "
        "gig. action=release: artist, name (release title), kind single|ep|album, day, distributor, upc, tracks [{title, isrc, writers [{name, "
        "role, share, ipi}]}], artwork, release (to update). action=release_final (card) / release_step (step deliver|pitch|iprs|"
        "release): release. action=royalty*: artist, source iprs|isamra|ppl|distributor|youtube|sync|other, amount, period (from "
        "HER statement). action=payout: artist (money card). action=payout_paid*: payout, ref. * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS},
         "artist": {"type": "string"}, "gig": {"type": "string"}, "release": {"type": "string"}, "payout": {"type": "string"},
         "text": {"type": "string"}, "name": {"type": "string"}, "kind": {"type": "string"}, "genre": {"type": "string"},
         "city": {"type": "string"}, "phone": {"type": "string"}, "email": {"type": "string"},
         "members": {"type": "array", "items": {"type": "object"}}, "min_fee": {"type": "number"}, "fee_note": {"type": "string"},
         "rider": {"type": "object"}, "gstin": {"type": "string"}, "key": {"type": "string"}, "status": {"type": "string"},
         "ref": {"type": "string"}, "note": {"type": "string"}, "day": {"type": "string"}, "day_to": {"type": "string"},
         "block_id": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"}, "set_minutes": {"type": "integer"},
         "venue": {"type": "string"}, "fee": {"type": "number"}, "promoter": {"type": "string"}, "event": {"type": "string"},
         "event_type": {"type": "string"}, "advance_pct": {"type": "number"}, "travel_by": {"type": "string"},
         "hours": {"type": "integer"}, "stage": {"type": "string"}, "amount": {"type": "number"}, "to": {"type": "string"},
         "mode": {"type": "string"}, "what": {"type": "string"}, "paid_by": {"type": "string"}, "reason": {"type": "string"},
         "by": {"type": "string"}, "origin": {"type": "string"}, "upc": {"type": "string"}, "distributor": {"type": "string"},
         "tracks": {"type": "array", "items": {"type": "object"}}, "artwork": {"type": "boolean"}, "label": {"type": "string"},
         "step": {"type": "string"}, "source": {"type": "string"}, "period": {"type": "string"},
         "agency": {"type": "string"}, "upi_id": {"type": "string"}, "commission_pct": {"type": "number"},
         "royalty_pct": {"type": "number"}, "same_city_gap": {"type": "integer"}, "travel_gap": {"type": "integer"},
         "hold_hours": {"type": "integer"}, "balance_days": {"type": "integer"},
         "distributors": {"type": "array", "items": {"type": "object"}}, "terms": {"type": "string"},
         "address": {"type": "string"}, "rules": {"type": "string"}, "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "artist_manager_dekho", "description": (
        "Read musician-manager work (nothing changes). what=day | artists | artist (artist: roster card, registrations, gigs, "
        "releases, ledger) | check (artist, day, start, end, city: is the artist free?) | calendar (month YYYY-MM, artist) | gigs "
        "(status, artist) | gig (gig: money, rider, cards) | releases | release (release: checks, plan) | payouts | cards | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "artists", "artist", "check", "calendar", "gigs", "gig", "releases", "release",
                                             "payouts", "cards", "settings"]},
         "artist": {"type": "string"}, "gig": {"type": "string"}, "release": {"type": "string"}, "day": {"type": "string"},
         "start": {"type": "string"}, "end": {"type": "string"}, "city": {"type": "string"}, "month": {"type": "string"},
         "status": {"type": "string"}},
         "required": ["what"]}},
]
ARTISTMGR_LABELS = {"artist_manager": "Artist ka kaam kar raha hoon", "artist_manager_dekho": "Artist ka calendar dekh raha hoon"}

_GIG_KEYS = ("day", "start", "end", "set_minutes", "city", "venue", "fee", "promoter", "phone", "email", "event", "event_type",
             "advance_pct", "travel_by", "notes")
_SET_KEYS = ("agency", "gstin", "address", "phone", "email", "upi_id", "commission_pct", "royalty_pct", "same_city_gap", "travel_gap",
             "hold_hours", "advance_pct", "balance_days", "distributors", "terms", "rules", "morning_time")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..artistmgr import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    g, ar = _s(a.get("gig")), _s(a.get("artist"))
    try:
        if action == "settings":
            return S.save_settings(t, actor, **{k: a[k] for k in _SET_KEYS if k in a})
        if action == "artist":
            return S.artist_save(t, _s(a.get("name") or ar), _s(a.get("kind")), _s(a.get("genre")), _s(a.get("phone")),
                                 _s(a.get("email")), _s(a.get("city")), a.get("members"), a.get("min_fee"), _s(a.get("fee_note")),
                                 a.get("commission_pct"), a.get("rider"), _s(a.get("gstin")), _s(a.get("upi_id")), "",
                                 _s(a.get("note")), actor=actor)
        if action == "reg":
            return S.reg_set(t, ar, _s(a.get("key")), _s(a.get("status")), _s(a.get("ref")), _s(a.get("note")), actor)
        if action == "block":
            return S.block_days(t, ar, _s(a.get("day")), _s(a.get("day_to")), _s(a.get("note")), actor)
        if action == "unblock":
            return S.unblock(t, _s(a.get("block_id")), actor)
        if action == "offer":
            return S.offer(t, _s(a.get("text")), ar, actor, conv, **{k: a[k] for k in _GIG_KEYS if k in a})
        if action == "gig":
            return S.gig_save(t, g, ar, "", actor, conv, **{k: a[k] for k in _GIG_KEYS if k in a})
        if action == "hold":
            return S.hold(t, g, a.get("hours"), actor, conv)
        if action == "release_hold":
            return S.release(t, g, actor)
        if action == "confirm":
            return S.confirm_request(t, g, actor, conv)
        if action == "reply":
            return S.reply_request(t, g, _s(a.get("text")), actor, conv)
        if action == "contract":
            return S.contract_request(t, g, actor, conv)
        if action == "invoice":
            return S.invoice_request(t, g, actor, conv)
        if action == "pay_request":
            return S.pay_request(t, g, _s(a.get("stage")), a.get("amount"), actor, conv)
        if action == "message":
            return S.message_request(t, _s(a.get("text")), g, ar, _s(a.get("to")), actor, conv)
        if action == "paid":
            return S.paid(t, g, a.get("amount"), _s(a.get("mode")) or "upi", _s(a.get("ref")), "", actor)
        if action == "tds":
            return S.set_tds(t, g, a.get("amount"), actor)
        if action == "expense":
            return S.expense(t, g, _s(a.get("what")), a.get("amount"), _s(a.get("paid_by")) or "manager", actor)
        if action == "done":
            return S.done(t, g, actor)
        if action == "cancel":
            return S.cancel(t, g, _s(a.get("reason")), _s(a.get("by")) or "promoter", actor)
        if action == "travel":
            return S.travel_link(t, g, _s(a.get("origin")), actor, conv)
        if action == "release":
            return S.release_save(t, ar, _s(a.get("name")), _s(a.get("kind")), _s(a.get("day")), _s(a.get("distributor")),
                                  _s(a.get("upc")), a.get("tracks"), a.get("artwork"), _s(a.get("label")), _s(a.get("note")),
                                  _s(a.get("release")), actor)
        if action == "release_final":
            return S.release_final_request(t, _s(a.get("release")), actor, conv)
        if action == "release_step":
            return S.release_step(t, _s(a.get("release")), _s(a.get("step")), actor)
        if action == "royalty":
            return S.royalty_add(t, ar, _s(a.get("source")), a.get("amount"), _s(a.get("period")), _s(a.get("release")),
                                 _s(a.get("ref")), actor)
        if action == "payout":
            return S.payout_request(t, ar, actor, conv)
        if action == "payout_paid":
            return S.payout_paid(t, _s(a.get("payout")), _s(a.get("ref")), actor)
        if action == "forget":
            return S.forget(t, g, actor)
        if action == "forget_artist":
            return S.forget_artist(t, ar, actor)
    except S.ArtistError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..artistmgr import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "artists":
            return {"artists": S.artists(t)}
        if what == "artist":
            return S.artist_view(t, _s(a.get("artist")))
        if what == "check":
            return S.check(t, _s(a.get("artist")), _s(a.get("day")), _s(a.get("start")), _s(a.get("end")), _s(a.get("city")))
        if what == "calendar":
            return S.calendar(t, _s(a.get("month")), _s(a.get("artist")))
        if what == "gigs":
            return {"gigs": S.gigs(t, _s(a.get("status")), _s(a.get("artist")))}
        if what == "gig":
            return S.gig_view(t, _s(a.get("gig")))
        if what == "releases":
            return {"releases": S.releases(t, _s(a.get("artist")))}
        if what == "release":
            return S.release_view(t, _s(a.get("release")))
        if what == "payouts":
            return {"payouts": S.payouts(t, _s(a.get("artist")))}
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status")) or "waiting")}
        if what == "settings":
            return S.settings(t)
    except S.ArtistError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{what}' nahi pehchana.")


async def _artist_manager(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _artist_manager_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


ARTISTMGR_HANDLERS = {"artist_manager": _artist_manager, "artist_manager_dekho": _artist_manager_dekho}
