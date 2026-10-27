"""v0.97 Tool `ask_form`: one card with several questions instead of asking one by one (chat + calls)."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

ASKFORM_TOOLS = [
    {"name": "ask_form", "description": (
        "Send her ONE form card when a job needs several details from her (e.g. a booking: name, date, time, people; a "
        "letter: to whom, subject, dates; a new customer: name, phone, address). Up to 12 fields. Kinds: text, number, date, "
        "choice / multi (give options), phone, email, id (Aadhaar / PAN / voter / DL / passport number: it goes into her "
        "Pehchaan Locker and you get a {id:...} reference). Pre-fill `value` with what you already know so she only "
        "checks it. Never for OTP, passwords, PIN, CVV or card numbers (refused). Her answers arrive as her next message "
        "(\"[Form bhara: ...]\"); until then don't ask the same things in chat. Use it only when 3+ details are missing; "
        "for one or two, just ask in a line."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string", "description": "Short, e.g. 'Train ticket ki jaankari'"},
         "why": {"type": "string", "description": "One line: what you will do with it"},
         "fields": {"type": "array", "items": {"type": "object", "properties": {
             "name": {"type": "string"}, "label": {"type": "string"},
             "kind": {"type": "string", "enum": ["text", "number", "date", "choice", "multi", "phone", "email", "id"]},
             "options": {"type": "array", "items": {"type": "string"}},
             "required": {"type": "boolean"}, "hint": {"type": "string"}, "value": {"type": "string"}},
             "required": ["label"]}}},
         "required": ["title", "fields"]}},
]
ASKFORM_LABELS = {"ask_form": "Aapke liye form bana raha hoon"}


async def ask_form(ctx: Ctx, title, fields, why: str = "", **_):
    from .. import askform
    try:
        v = await asyncio.to_thread(askform.create, ctx.tenant_id, ctx.conversation_id, str(title), fields, str(why or ""))
    except askform.FormError as e:
        raise ToolError(str(e))
    return {"form_id": v["id"], "status": "sent", "fields": [f["label"] for f in v["fields"]],
            "say": "Ek form bheja hai, bhar dijiye; jaise hi bharengi, main aage badhunga.",
            "note_for_you": "Wait for her answers (they arrive as her next message). Don't ask these in chat meanwhile."}


ASKFORM_HANDLERS = {"ask_form": ask_form}
