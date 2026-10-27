"""v0.82 Darzi Sahayak tools. `darzi_dekho` only reads (orders, today, a customer's measurements, prices, a check);
`darzi` changes things (new order, measurements, status, money noted, delivery, her rules). Sending the 'ready' message
and settling a new price are never done here: they become cards and wait for her tap."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ITEM = {"type": "object", "properties": {
    "garment": {"type": "string", "description": "blouse, kurti, salwar_suit, salwar, palazzo, lehenga, gown, petticoat, "
                                                 "saree_work (fall-pico), frock, shirt, pant, kurta_pajama, sherwani, safari, "
                                                 "alteration, or her own words"},
    "qty": {"type": "integer"}, "person": {"type": "string", "description": "who wears it if not the customer (beti, Riya)"},
    "fabric": {"type": "string"}, "style": {"type": "string", "description": "design / neck / sleeves / lining in her words"},
    "price": {"type": "number", "description": "rupees per piece, only if she said a price"}}}

DARZI_TOOLS = [
    {"name": "darzi", "description": (
        "Tailor / boutique coworker (her stitching business). Use for every stitching job, measurement, trial, "
        "delivery and tailoring price. "
        "action=new_order: customer (name and phone), items [{garment, qty, person, fabric, style, price}], deliver_on "
        "(28/10, 2026-10-28, '5 din', kal), trial_on, advance (rupees received), notes, photos (file_ids of fabric / "
        "design / the order-book photo). The system checks it against HER rules and earlier work first: if it returns "
        "saved=false with problems, tell her the problems and the earliest date, and only call again with force=true "
        "after she agrees. Prices not in her list become a price card for her Haan (never promise those prices to the "
        "customer before she approves). "
        "action=measure: customer / name / phone, garment, values ({chest: 34, waist: 30} or her words 'L 15 chest 34 "
        "kamar 30 bahi 11 1/2'), person, note (fitting / style), unit. Old measurements are kept; big changes come back "
        "to point out. Photo of the measurement book: file_read first, then measure. "
        "action=status: order (D-0012 / 12 / id), status new|cutting|stitching|trial|ready|delivered|cancelled, note. "
        "ready = a 'taiyaar hai' message draft card for HER to send (never say it was sent). "
        "action=update: order + deliver_on / trial_on / notes / items. action=pay: order, amount, how (cash / UPI): "
        "money she received. action=deliver: order, paid_now: closes it with a log. action=cancel: order, reason. "
        "action=slip: PDF job slip for an order. action=ready_message: the draft card again. "
        "action=rules: her rules: shop_name, unit (inch|cm), pieces_per_day, closed_days ([Ravi]), rush_percent, "
        "min_days {garment: days}, prices {garment: rupees}, rules [her own sentences], ready_template, morning_time. "
        "Only the owner sets prices and rules."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new_order", "measure", "status", "update", "pay", "deliver", "cancel",
                                               "slip", "ready_message", "rules"]},
         "customer": {"type": "string", "description": "customer id, name or phone"},
         "name": {"type": "string"}, "phone": {"type": "string"},
         "items": {"type": "array", "items": _ITEM}, "deliver_on": {"type": "string"}, "trial_on": {"type": "string"},
         "advance": {"type": "number"}, "notes": {"type": "string"}, "photos": {"type": "array", "items": {"type": "string"}},
         "force": {"type": "boolean"},
         "garment": {"type": "string"}, "values": {"description": "measurements: object {field: number} or her words"},
         "person": {"type": "string"}, "note": {"type": "string"}, "unit": {"type": "string"},
         "order": {"type": "string"}, "status": {"type": "string"}, "amount": {"type": "number"}, "how": {"type": "string"},
         "paid_now": {"type": "number"}, "reason": {"type": "string"},
         "shop_name": {"type": "string"}, "pieces_per_day": {"type": "integer"},
         "closed_days": {"type": "array", "items": {"type": "string"}}, "rush_percent": {"type": "integer"},
         "min_days": {"type": "object"}, "prices": {"type": "object"}, "rules": {"type": "array", "items": {"type": "string"}},
         "ready_template": {"type": "string"}, "morning_time": {"type": "string"}, "remeasure_months": {"type": "integer"}},
         "required": ["action"]}},
    {"name": "darzi_dekho", "description": (
        "Read the tailoring work (nothing changes). what=today (trials, deliveries, late, waiting for pickup, the "
        "week's load; date optional) | orders (status open|ready|delivered..., customer) | order (order) | customer "
        "(customer / name / phone: details + latest measurements; history=true for all versions) | customers (q) | "
        "check (items, deliver_on, trial_on, customer: what her rules and earlier work say BEFORE promising a date or "
        "price) | prices (her list + pending price cards) | rules | garments (what each garment needs measured)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["today", "orders", "order", "customer", "customers", "check", "prices", "rules",
                                             "garments"]},
         "date": {"type": "string"}, "status": {"type": "string"}, "customer": {"type": "string"}, "name": {"type": "string"},
         "phone": {"type": "string"}, "order": {"type": "string"}, "q": {"type": "string"}, "garment": {"type": "string"},
         "history": {"type": "boolean"}, "items": {"type": "array", "items": _ITEM}, "deliver_on": {"type": "string"},
         "trial_on": {"type": "string"}},
         "required": ["what"]}},
]
DARZI_LABELS = {"darzi": "Darzi ka kaam kar raha hoon", "darzi_dekho": "Darzi ka register dekh raha hoon"}
_OWNER_ONLY = {"rules"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..darzi import service as D
    actor = getattr(ctx, "actor", "owner") or "owner"
    by = "hoola" if actor in ("owner",) else actor
    conv = ctx.conversation_id
    try:
        if action in _OWNER_ONLY and actor not in ("owner",) and not actor.startswith("approved:"):
            raise ToolError("Daam aur niyam sirf owner badal sakti hain.")
        if action == "new_order":
            return D.new_order(ctx.tenant_id, a.get("items") or ([{"garment": a["garment"]}] if a.get("garment") else []),
                               _s(a.get("customer")), _s(a.get("name")), _s(a.get("phone")), _s(a.get("deliver_on")),
                               _s(a.get("trial_on")), a.get("advance"), _s(a.get("notes")), a.get("photos") or [],
                               bool(a.get("force")), by=by, conv=conv)
        if action == "measure":
            return D.save_measure(ctx.tenant_id, _s(a.get("customer")), _s(a.get("garment")), a.get("values"),
                                  _s(a.get("person")), _s(a.get("note")), _s(a.get("unit")), "chat",
                                  _s(a.get("name")), _s(a.get("phone")))
        if action == "status":
            return D.set_status(ctx.tenant_id, _s(a.get("order")), _s(a.get("status")), _s(a.get("note")), by=by, conv=conv)
        if action == "update":
            return D.update_order(ctx.tenant_id, _s(a.get("order")), _s(a.get("deliver_on")), _s(a.get("trial_on")),
                                  _s(a.get("notes")), a.get("items"), bool(a.get("force")), by=by)
        if action == "pay":
            return D.pay(ctx.tenant_id, _s(a.get("order")), a.get("amount"), _s(a.get("how")), by=by)
        if action == "deliver":
            return D.deliver(ctx.tenant_id, _s(a.get("order")), a.get("paid_now"), _s(a.get("note")), by=by, conv=conv)
        if action == "cancel":
            return D.cancel(ctx.tenant_id, _s(a.get("order")), _s(a.get("reason")), by=by)
        if action == "slip":
            return D.slip_file(ctx.tenant_id, _s(a.get("order")), conv)
        if action == "ready_message":
            card = D.ready_card(ctx.tenant_id, _s(a.get("order")), conv)
            return {"card": card, "say": "Message draft card par hai: aap tap karengi tabhi jayega."}
        if action == "rules":
            keys = ("shop_name", "unit", "pieces_per_day", "closed_days", "rush_percent", "min_days", "prices", "rules",
                    "ready_template", "morning_time", "remeasure_months")
            return {"rules": D.save_settings(ctx.tenant_id, **{k: a[k] for k in keys if k in a}), "say": "Niyam save."}
    except D.DarziError as e:
        raise ToolError(str(e))
    raise ToolError("action = new_order | measure | status | update | pay | deliver | cancel | slip | ready_message | rules")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..darzi import garments as G
    from ..darzi import service as D
    t = ctx.tenant_id
    try:
        if what == "today":
            return D.day(t, _s(a.get("date")))
        if what == "orders":
            return {"orders": D.orders(t, _s(a.get("status")) or "open", _s(a.get("customer") or a.get("name") or a.get("phone")), 40)}
        if what == "order":
            return D.get_order(t, _s(a.get("order")))
        if what == "customer":
            return D.measures(t, _s(a.get("customer")), _s(a.get("name")), _s(a.get("phone")), _s(a.get("garment")),
                              bool(a.get("history"))) | {"orders": D.orders(t, "", _s(a.get("customer") or a.get("name") or a.get("phone")), 10)}
        if what == "customers":
            return {"customers": D.customers(t, _s(a.get("q")), 50)}
        if what == "check":
            return D.check(t, a.get("items") or ([{"garment": a["garment"]}] if a.get("garment") else []),
                           _s(a.get("deliver_on")), _s(a.get("trial_on")), _s(a.get("customer")), _s(a.get("name")),
                           _s(a.get("phone")))
        if what == "prices":
            st = D.settings(t)
            return {"prices": st["prices"], "usual_days": st["usual_days"], "rush_percent": st["rush_percent"],
                    "pending_cards": D.quotes(t)}
        if what == "rules":
            return D.settings(t)
        if what == "garments":
            return {"garments": G.listing()}
    except D.DarziError as e:
        raise ToolError(str(e))
    raise ToolError("what = today | orders | order | customer | customers | check | prices | rules | garments")


async def darzi(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def darzi_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


DARZI_HANDLERS = {"darzi": darzi, "darzi_dekho": darzi_dekho}
