"""Google Forms tools: the user's own Google Forms through the official Forms API (Profile > Google Forms).

Making forms, editing questions, opening / closing and reading answers happen at once. Sharing edit access and
deleting questions that already have answers show a confirm card first. To send a form to people, give the
responder link to email_draft (or WhatsApp tools); Santosh never sends it on its own.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..bazar.connectors.base import ToolError as BazarError
from ..forms import service as fs
from ..forms.client import FormError, NotConnected
from .tools import Ctx, ToolError

QUESTION = {"type": "object", "properties": {
    "title": {"type": "string"},
    "type": {"type": "string", "enum": list(fs.TYPES),
             "description": "short, paragraph, choice (one answer), checkbox (many), dropdown, scale, rating, date, "
                            "datetime, time, section (a heading)"},
    "options": {"type": "array", "items": {"type": "string"}, "description": "For choice / checkbox / dropdown"},
    "required": {"type": "boolean"}, "description": {"type": "string"},
    "allow_other": {"type": "boolean", "description": "Add an 'Other' option"},
    "low": {"type": "integer"}, "high": {"type": "integer"}, "low_label": {"type": "string"}, "high_label": {"type": "string"},
    "correct": {"description": "Quiz: the right answer (or list of answers)"},
    "points": {"type": "integer", "description": "Quiz points"}},
    "required": ["title"]}
FORM = {"type": "string", "description": "The form: its name, edit link or id"}

FORMS_TOOLS = [
    {"name": "form_create", "description": (
        "Make a Google Form (or quiz) in the user's Google account from what they describe: write all the questions "
        "yourself with sensible types and options (registration, feedback, order, survey, attendance, quiz). It is "
        "published and accepting answers; returns the link to share (responder_link) and the edit link. To send it, "
        "use email_draft with the responder_link."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "description": {"type": "string"},
         "questions": {"type": "array", "items": QUESTION},
         "quiz": {"type": "boolean"}, "collect_emails": {"type": "boolean"},
         "account": {"type": "string"}}, "required": ["title", "questions"]}},
    {"name": "form_edit", "description": (
        "Change a form: new title or description, add questions, remove questions (by number or title), or update a "
        "question (title, required, options). Removing questions that already have answers shows a confirm card."),
     "input_schema": {"type": "object", "properties": {
         "form": FORM, "title": {"type": "string"}, "description": {"type": "string"},
         "add": {"type": "array", "items": QUESTION},
         "remove": {"type": "array", "items": {"type": "string"}, "description": "Question numbers or titles"},
         "update": {"type": "array", "items": {"type": "object", "properties": {
             "question": {"type": "string", "description": "Number or title"}, "title": {"type": "string"},
             "required": {"type": "boolean"}, "options": {"type": "array", "items": {"type": "string"}},
             "description": {"type": "string"}}, "required": ["question"]}}},
         "required": ["form"]}},
    {"name": "form_find", "description": "Find the user's Google Forms by name (or list recent ones), with ids and links.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}}},
    {"name": "form_responses", "description": (
        "The answers people gave on a form, newest first, as rows keyed by question. Also shows the form's questions "
        "when there are no answers yet."),
     "input_schema": {"type": "object", "properties": {"form": FORM, "limit": {"type": "integer"}}, "required": ["form"]}},
    {"name": "form_summary", "description": (
        "Summary of a form's answers: how many answered, counts per option, averages for ratings and scales, latest "
        "written answers, quiz scores. Use for 'kitne logon ne bhara', 'feedback kaisa aaya'."),
     "input_schema": {"type": "object", "properties": {"form": FORM}, "required": ["form"]}},
    {"name": "form_export", "description": (
        "Export a form's answers: to='sheet' makes a new Google Sheet (when Sheets is connected), to='phone' sends an "
        "Excel file to the phone (its file_id can be attached to an email). Default: Sheet if connected, else phone."),
     "input_schema": {"type": "object", "properties": {"form": FORM, "to": {"type": "string", "enum": ["auto", "sheet", "phone"]}},
                      "required": ["form"]}},
    {"name": "form_settings", "description": "Open or close a form for answers (accepting), or turn quiz mode on / off.",
     "input_schema": {"type": "object", "properties": {"form": FORM, "accepting": {"type": "boolean"}, "quiz": {"type": "boolean"}},
                      "required": ["form"]}},
    {"name": "form_share", "description": (
        "Let other people edit (or view) the form itself, by email or name. Google emails them, so the user confirms "
        "on a card first. (To get people to FILL the form, send the responder link instead.)"),
     "input_schema": {"type": "object", "properties": {
         "form": FORM, "people": {"type": "array", "items": {"type": "string"}},
         "role": {"type": "string", "enum": ["writer", "reader"]}}, "required": ["form", "people"]}},
    {"name": "form_alerts", "description": (
        "Tell the user in the chat when new answers arrive on a form (checked every ~10 minutes). on=false stops it. "
        "With no form, lists the forms being watched."),
     "input_schema": {"type": "object", "properties": {"form": FORM, "on": {"type": "boolean"}}}},
]

FORMS_LABELS = {"form_create": "Google Form bana raha hoon", "form_edit": "Form badal raha hoon",
                "form_find": "Form dhoondh raha hoon", "form_responses": "Form ke jawab dekh raha hoon",
                "form_summary": "Jawab ka saar nikaal raha hoon", "form_export": "Jawab export kar raha hoon",
                "form_settings": "Form settings badal raha hoon", "form_share": "Share ki manzoori le raha hoon",
                "form_alerts": "Naye jawab ka alert laga raha hoon"}


async def _t(fn, *a, **kw):
    try:
        return await asyncio.to_thread(fn, *a, **kw)
    except NotConnected as e:
        raise ToolError(str(e))
    except FormError as e:
        raise ToolError(str(e))


def _card(ctx: Ctx, pid: str) -> dict[str, Any]:
    from ..bazar import service
    try:
        out = service.run(ctx.tenant_id, ctx.conversation_id, "santosh-forms", "confirm_change", {"pending_id": pid})
    except BazarError as e:
        raise ToolError(str(e))
    return {k: v for k, v in out.items() if k in ("needs_approval", "approval_id", "card", "say")}


def _brief(v: dict) -> dict:
    return {k: v.get(k) for k in ("id", "title", "responder_link", "edit_link", "accepting", "is_quiz")} | {
        "questions": [f"{q['n']}. {q['title']} ({q['type']}{', required' if q.get('required') else ''})" for q in v["questions"]]}


async def form_create(ctx: Ctx, title, questions, description="", quiz=False, collect_emails=False, account=None, **_):
    v = await _t(fs.create, ctx.tenant_id, ctx.conversation_id, str(title), list(questions or []), str(description or ""),
                 bool(quiz), bool(collect_emails), account)
    return {"created": True, **_brief(v),
            "note": "Form card is in the chat. Share responder_link (email_draft can send it); edit_link is for the user."}


async def form_edit(ctx: Ctx, form, title=None, description=None, add=None, remove=None, update=None, **_):
    out = await _t(fs.edit, ctx.tenant_id, ctx.conversation_id, str(form), title, description, add, remove, update)
    res: dict[str, Any] = {"form": _brief(out["form"])}
    if out.get("pending_id"):
        res.update(await asyncio.to_thread(_card, ctx, out["pending_id"]))
        res["note"] = "Questions with answers are removed only after the user approves the card."
    return res


async def form_find(ctx: Ctx, query="", **_):
    return await _t(fs.find, ctx.tenant_id, str(query or ""))


async def form_responses(ctx: Ctx, form, limit=50, **_):
    return await _t(fs.responses, ctx.tenant_id, str(form), int(limit or 50))


async def form_summary(ctx: Ctx, form, **_):
    return await _t(fs.summary, ctx.tenant_id, str(form))


async def form_export(ctx: Ctx, form, to="auto", **_):
    return await _t(fs.export, ctx.tenant_id, ctx.conversation_id, str(form), str(to or "auto"))


async def form_settings(ctx: Ctx, form, accepting=None, quiz=None, **_):
    if accepting is None and quiz is None:
        raise ToolError("Kya badalna hai? accepting (khula / band) ya quiz.")
    return _brief(await _t(fs.settings, ctx.tenant_id, ctx.conversation_id, str(form), accepting, quiz))


async def form_share(ctx: Ctx, form, people, role="writer", **_):
    pid = await _t(fs.plan_share, ctx.tenant_id, ctx.conversation_id, str(form), list(people or []), str(role or "writer"))
    card = await asyncio.to_thread(_card, ctx, pid)
    return {**card, "status": "needs_approval", "note": "Confirm card is in the chat; nobody gets access until the user approves."}


async def form_alerts(ctx: Ctx, form=None, on=True, **_):
    if not form:
        return {"watching": await _t(fs.watches, ctx.tenant_id)}
    return await _t(fs.set_alerts, ctx.tenant_id, ctx.conversation_id, str(form), on is not False)


FORMS_HANDLERS = {"form_create": form_create, "form_edit": form_edit, "form_find": form_find,
                  "form_responses": form_responses, "form_summary": form_summary, "form_export": form_export,
                  "form_settings": form_settings, "form_share": form_share, "form_alerts": form_alerts}
