"""Photo Sahayak tools (photographer's assistant). `photo_assist_dekho` only reads; `photo_assist` does the work.

Quotation / booking terms / invoice / gallery delivery / any client message, a hold becoming a confirmed shoot, payment
requests, discounts and refunds become CARDS here; only HER tap in the app decides them. A shooter already booked at an
overlapping time is refused in code. Hoola never invents a price, date or permission, never uploads her photos, never takes or
pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "package", "gear", "shoot", "hold", "release_hold", "shots", "gear_check", "check", "release",
            "release_withdraw", "cull", "pick", "edit", "quote_send", "contract_send", "confirm", "pay_request", "deliver",
            "invoice", "message", "discount", "paid", "shot", "done", "cancel", "refund_sent", "forget"]
_OWNER_ONLY = {"settings", "package", "gear", "paid", "cancel", "refund_sent", "done", "forget", "discount"}

PHOTO_ASSIST_TOOLS = [
    {"name": "photo_assist", "description": (
        "Photographer's assistant (wedding / event / product / portrait). NEVER invent a price, date, permission or availability. "
        "Cards = only her tap decides: say 'aapki haan ka card bheja hai', never 'sent / confirmed'. "
        "settings*: studio, gstin, upi_id, buffer_minutes, hold_hours, delivery_days, retention_days, copyright keep|client, stages, "
        "cancel, terms, rpc_number, rpc_until, morning_time. package*: name, price, unit, includes, edits. gear*: name, kind, serial, "
        "uin, weight_g, insured_until. shoot: shoot (to update) or new: kind, client, phone, client_kind personal|business, day, "
        "end_day, start, end, location, drone, minors, commercial, shooters [names], lines [{package, qty}|{name, price}], "
        "deliverables, notes. hold / release_hold / shot / done*: shoot (double booking refused). shots: shoot, add, tick, must. "
        "gear_check: shoot, tick (number / name / all). check: shoot, key (permission she has). release: shoot, kind "
        "model|minor|property, person, guardian, place, uses [portfolio, social_media, advertising, stock...], lang. "
        "release_withdraw: release. cull: shoot, file_ids (her photos; signals only). pick: ids, choice keep|reject|maybe|edit. "
        "edit: shoot, photo, ask (client's words = data) or index + status. quote_send | contract_send | confirm | invoice: shoot. "
        "pay_request: shoot, stage or amount. deliver: shoot, link (HER gallery link), what, expires. message: shoot, text. "
        "discount*: shoot, amount or pct, reason. paid*: shoot, amount, mode, ref. cancel*: shoot, reason, by client|studio. "
        "refund_sent* / forget*: shoot. * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS},
         "shoot": {"type": "string"}, "kind": {"type": "string"}, "client": {"type": "string"}, "phone": {"type": "string"},
         "email": {"type": "string"}, "client_kind": {"type": "string"}, "client_gstin": {"type": "string"},
         "day": {"type": "string"}, "end_day": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
         "location": {"type": "string"}, "place": {"type": "string"}, "drone": {"type": "boolean"}, "minors": {"type": "boolean"},
         "commercial": {"type": "boolean"}, "shooters": {"type": "array", "items": {"type": "string"}},
         "lines": {"type": "array", "items": {"type": "object"}}, "deliverables": {"type": "array", "items": {"type": "string"}},
         "notes": {"type": "string"}, "portfolio_ok": {"type": "string"}, "hours": {"type": "integer"},
         "add": {"type": "array", "items": {"type": "string"}}, "tick": {"type": "array", "items": {"type": "string"}},
         "must": {"type": "boolean"}, "key": {"type": "string"}, "release": {"type": "string"}, "person": {"type": "string"},
         "guardian": {"type": "string"}, "uses": {"type": "array", "items": {"type": "string"}}, "lang": {"type": "string"},
         "file_ids": {"type": "array", "items": {"type": "string"}}, "ids": {"type": "array", "items": {"type": "string"}},
         "choice": {"type": "string"}, "photo": {"type": "string"}, "ask": {"type": "string"}, "index": {"type": "integer"},
         "status": {"type": "string"}, "stage": {"type": "string"}, "amount": {"type": "number"}, "pct": {"type": "number"},
         "link": {"type": "string"}, "what": {"type": "string"}, "expires": {"type": "string"}, "text": {"type": "string"},
         "reason": {"type": "string"}, "mode": {"type": "string"}, "ref": {"type": "string"}, "by": {"type": "string"},
         "name": {"type": "string"}, "price": {"type": "number"}, "unit": {"type": "string"},
         "includes": {"type": "array", "items": {"type": "string"}}, "edits": {"type": "integer"}, "serial": {"type": "string"},
         "uin": {"type": "string"}, "weight_g": {"type": "integer"}, "insured_until": {"type": "string"},
         "studio": {"type": "string"}, "gstin": {"type": "string"}, "upi_id": {"type": "string"}, "address": {"type": "string"},
         "buffer_minutes": {"type": "integer"}, "hold_hours": {"type": "integer"}, "delivery_days": {"type": "integer"},
         "retention_days": {"type": "integer"}, "copyright": {"type": "string"}, "stages": {"type": "array", "items": {"type": "object"}},
         "cancel": {"type": "array", "items": {"type": "object"}}, "terms": {"type": "string"}, "rpc_number": {"type": "string"},
         "rpc_until": {"type": "string"}, "morning_time": {"type": "string"}, "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "photo_assist_dekho", "description": (
        "Read photo studio work (nothing changes). what=day (today / tomorrow's shoots, prep, holds ending, instalments, deliveries, "
        "cards waiting) | free (day, start, end, shooter, end_day) | calendar (month YYYY-MM) | shoots (status) | shoot (shoot: shot "
        "list, gear, checks, releases, culling, edits, payments, cards) | quote (shoot) | packages | gear | cards | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "free", "calendar", "shoots", "shoot", "quote", "packages", "gear", "cards", "settings"]},
         "shoot": {"type": "string"}, "day": {"type": "string"}, "end_day": {"type": "string"}, "start": {"type": "string"},
         "end": {"type": "string"}, "shooter": {"type": "string"}, "month": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
PHOTO_ASSIST_LABELS = {"photo_assist": "Photo studio ka kaam kar raha hoon", "photo_assist_dekho": "Shoot ki booking dekh raha hoon"}

_SET_KEYS = ("studio", "gstin", "address", "phone", "email", "upi_id", "buffer_minutes", "hold_hours", "delivery_days",
             "retention_days", "copyright", "stages", "cancel", "terms", "rpc_number", "rpc_until", "morning_time", "rules")
_SH_KEYS = ("kind", "client", "phone", "email", "client_kind", "client_gstin", "day", "end_day", "start", "end", "location", "place",
            "drone", "minors", "commercial", "shooters", "lines", "notes", "portfolio_ok", "deliverables")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..photoassist import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    sh = _s(a.get("shoot"))
    try:
        if action == "settings":
            return S.save_settings(t, actor, **{k: a[k] for k in _SET_KEYS if k in a})
        if action == "package":
            return S.package_save(t, _s(a.get("name")), a.get("price"), _s(a.get("unit")), a.get("includes"), a.get("edits"), actor=actor)
        if action == "gear":
            return S.gear_save(t, _s(a.get("name")), _s(a.get("kind")), _s(a.get("serial")), _s(a.get("uin")), a.get("weight_g"),
                               _s(a.get("insured_until")), _s(a.get("notes")), actor=actor)
        if action == "shoot":
            return S.shoot_save(t, sh, actor, conv, **{k: a[k] for k in _SH_KEYS if k in a})
        if action == "hold":
            return S.hold(t, sh, a.get("hours"), actor)
        if action == "release_hold":
            return S.release_hold(t, sh, actor)
        if action == "shots":
            return S.shots(t, sh, a.get("add"), a.get("tick"), None, bool(a.get("must")), actor)
        if action == "gear_check":
            return S.gear_check(t, sh, a.get("tick"), False, actor)
        if action == "check":
            return S.checks_tick(t, sh, _s(a.get("key")), True, actor)
        if action == "release":
            return S.release_new(t, sh, _s(a.get("kind")) or "model", _s(a.get("person")), _s(a.get("guardian")), _s(a.get("place")),
                                 a.get("uses"), _s(a.get("lang")) or "en", actor)
        if action == "release_withdraw":
            return S.release_withdraw(t, _s(a.get("release")), actor)
        if action == "cull":
            return S.cull(t, sh, None, [str(f) for f in (a.get("file_ids") or [])], True, actor)
        if action == "pick":
            return S.pick(t, a.get("ids") or [], _s(a.get("choice")), actor)
        if action == "edit":
            return S.edit(t, sh, _s(a.get("photo")), _s(a.get("ask")), _s(a.get("status")), a.get("index"), actor)
        if action == "quote_send":
            return S.quote_request(t, sh, actor, conv)
        if action == "contract_send":
            return S.contract_request(t, sh, actor, conv)
        if action == "confirm":
            return S.confirm_request(t, sh, actor, conv)
        if action == "pay_request":
            return S.pay_request(t, sh, _s(a.get("stage")), a.get("amount"), actor, conv)
        if action == "deliver":
            return S.delivery_request(t, sh, _s(a.get("link")), _s(a.get("what")), _s(a.get("expires")), actor, conv)
        if action == "invoice":
            return S.invoice_request(t, sh, actor, conv)
        if action == "message":
            return S.message_request(t, sh, _s(a.get("text")), actor, conv)
        if action == "discount":
            return S.discount_request(t, sh, a.get("amount"), a.get("pct"), _s(a.get("reason")), actor, conv)
        if action == "paid":
            return S.paid(t, sh, a.get("amount"), _s(a.get("mode")) or "upi", _s(a.get("ref")), "", actor)
        if action == "shot":
            return S.mark_shot(t, sh, actor)
        if action == "done":
            return S.done(t, sh, actor)
        if action == "cancel":
            return S.cancel(t, sh, _s(a.get("reason")), _s(a.get("by")) or "client", actor, conv)
        if action == "refund_sent":
            return S.refund_sent(t, sh, _s(a.get("ref")), actor)
        if action == "forget":
            return S.forget(t, sh, actor)
    except S.PhotoError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _dekho(ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    from ..photoassist import service as S
    t, w = ctx.tenant_id, _s(a.get("what")) or "day"
    try:
        if w == "day":
            return S.day(t)
        if w == "free":
            return S.free(t, _s(a.get("day")), _s(a.get("start")), _s(a.get("end")), _s(a.get("shooter")) or "main", _s(a.get("end_day")))
        if w == "calendar":
            return S.calendar(t, _s(a.get("month")))
        if w == "shoots":
            return {"shoots": S.shoots(t, _s(a.get("status")))}
        if w == "shoot":
            return S.shoot_view(t, _s(a.get("shoot")))
        if w == "quote":
            return S.quote(t, _s(a.get("shoot")))
        if w == "packages":
            return {"packages": S.packages(t)}
        if w == "gear":
            return {"gear": S.gear(t)}
        if w == "cards":
            return {"cards": S.cards(t)}
        if w == "settings":
            return S.settings(t)
    except S.PhotoError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{w}' nahi pehchana.")


async def _photo_assist(ctx: Ctx, **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, _s(a.get("action")), a)


async def _photo_assist_dekho(ctx: Ctx, **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_dekho, ctx, a)


PHOTO_ASSIST_HANDLERS = {"photo_assist": _photo_assist, "photo_assist_dekho": _photo_assist_dekho}

# module-name exports (MOD = photoassist), same objects
PHOTOASSIST_TOOLS = PHOTO_ASSIST_TOOLS
PHOTOASSIST_LABELS = PHOTO_ASSIST_LABELS
PHOTOASSIST_HANDLERS = PHOTO_ASSIST_HANDLERS
