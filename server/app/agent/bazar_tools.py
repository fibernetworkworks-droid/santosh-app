"""Santosh Bazar: 159 Indian app/biller/shop packs behind three tools, so the model's tool list stays small."""
from __future__ import annotations

import asyncio

from ..bazar import service
from ..bazar.connectors.base import ToolError as BazarError
from .tools import Ctx, ToolError

BAZAR_TOOLS = [
    {"name": "bazar_find", "description": (
        "Find Santosh Bazar packs for a task: bill payments (98 electricity/gas/LPG/mobile/broadband/DTH billers), local shops "
        "(kirana, dairy, tiffin, medical, clinic, salon, plumber, local ISP...), UPI apps (PhonePe, GPay, Paytm, BHIM...), "
        "ride apps (Uber, Ola, Rapido...), food/grocery apps (Swiggy, Instamart, Zomato, Zepto, Dineout, District) and "
        "helpers (bill reminders, birthdays, medicine, spend report from bank SMS, expense split, family, festival greetings). "
        "Query in any language, e.g. 'bijli bill msedcl', 'kirana atta', 'phonepe', 'uber', 'swiggy biryani'. "
        "Returns matching packs with status and their tools (name, description, input_schema). Empty query = catalogue."),
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string"}, "category": {"type": "string", "description": "Optional category filter"}}}},
    {"name": "bazar_run", "description": (
        "Run one tool of a Bazar pack found with bazar_find. Give pack_id, tool and args matching that tool's input_schema. "
        "Read tools return data. Tools that spend money or message people return needs_approval: a confirm card is shown "
        "to the user; tell them the total and to tap Approve. Never claim an order/payment is done until the user approved "
        "and the result says so. Results with an app/UPI link show an Open button in the chat."),
     "input_schema": {"type": "object", "properties": {
         "pack_id": {"type": "string"}, "tool": {"type": "string"},
         "args": {"type": "object", "description": "Arguments for the tool"}}, "required": ["pack_id", "tool"]}},
    {"name": "bazar_contact", "description": (
        "Save or list the user's payment contacts (name + UPI ID and/or phone) used by UPI packs, greetings and splits. "
        "Only save a UPI ID the user gave you."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["save", "list"]}, "name": {"type": "string"}, "upi_id": {"type": "string"},
         "phone": {"type": "string"}, "relation": {"type": "string"}}, "required": ["action"]}},
    {"name": "bazar_activity", "description": "The user's recent Bazar orders and payments with their status.",
     "input_schema": {"type": "object", "properties": {}}},
]

BAZAR_LABELS = {"bazar_find": "Sahi app/dukaan dhoondh raha hoon", "bazar_run": "Kaam kar raha hoon",
                "bazar_contact": "Contact dekh raha hoon", "bazar_activity": "Orders aur payments dekh raha hoon"}


async def _call(fn, *a):
    try:
        return await asyncio.to_thread(fn, *a)
    except BazarError as e:
        raise ToolError(str(e))


async def bazar_find(ctx: Ctx, query="", category="", **_):
    return await _call(service.find, ctx.tenant_id, str(query or ""), str(category or ""))


async def bazar_run(ctx: Ctx, pack_id, tool, args=None, **_):
    return await _call(service.run, ctx.tenant_id, ctx.conversation_id, str(pack_id), str(tool), args or {})


async def bazar_contact(ctx: Ctx, action, name="", upi_id="", phone="", relation="", **_):
    if action == "list":
        return {"contacts": await _call(service.list_contacts, ctx.tenant_id)}
    return await _call(service.add_contact, ctx.tenant_id, str(name or ""), str(upi_id or ""), str(phone or ""), str(relation or ""))


async def bazar_activity(ctx: Ctx, **_):
    return await _call(service.activity, ctx.tenant_id)


BAZAR_HANDLERS = {"bazar_find": bazar_find, "bazar_run": bazar_run, "bazar_contact": bazar_contact,
                  "bazar_activity": bazar_activity}
