"""The tools Santosh can use. Each has a JSON schema for Claude and a handler."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from .. import campaigns as camp
from ..config import get_settings
from ..db import Lead, LeadList, Template, now, session
from ..whatsapp import WhatsAppError, check_template, get_whatsapp, render_body


class ToolError(Exception):
    pass


@dataclass
class Ctx:
    tenant_id: str
    conversation_id: str


TEMPLATE_PROPS = {
    "name": {"type": "string", "description": "lowercase_with_underscores, unique, e.g. diwali_offer_2026"},
    "language": {"type": "string", "description": "Template language code: hi (Hindi/Hinglish in Devanagari or Roman), en, mr, gu, ta, te, kn, ml, bn, pa"},
    "category": {"type": "string", "enum": ["MARKETING", "UTILITY"], "description": "Offers/promotions = MARKETING. Order or account updates = UTILITY."},
    "body": {"type": "string", "description": "Message text, max 1024 chars. Variables as {{1}}, {{2}}. *bold* allowed."},
    "example_values": {"type": "array", "items": {"type": "string"}, "description": "One realistic example per variable, in order"},
    "footer": {"type": "string", "description": "Optional, max 60 chars, no variables. Good place for 'STOP likhkar band karein'."},
}

TOOLS = [
    {"name": "list_lead_lists", "description": "List the contact lists the user has uploaded, newest first.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_lead_list", "description": "Details of one contact list: counts, columns, whether it has an opt-in column, a few sample first names.",
     "input_schema": {"type": "object", "properties": {"list_id": {"type": "string"}}, "required": ["list_id"]}},
    {"name": "check_template", "description": "Check a WhatsApp template draft against WhatsApp's rules without sending it to Meta. Fix every error before submitting.",
     "input_schema": {"type": "object", "properties": TEMPLATE_PROPS, "required": ["name", "language", "category", "body", "example_values"]}},
    {"name": "submit_template", "description": "Submit a checked template to Meta for approval. Approval usually takes a few minutes, sometimes up to a day.",
     "input_schema": {"type": "object", "properties": TEMPLATE_PROPS, "required": ["name", "language", "category", "body", "example_values"]}},
    {"name": "check_template_status", "description": "Get the latest Meta approval status of a submitted template.",
     "input_schema": {"type": "object", "properties": {"template_id": {"type": "string"}}, "required": ["template_id"]}},
    {"name": "create_campaign", "description": (
        "Create a WhatsApp campaign that sends an approved (or pending) template to a contact list. "
        "The background worker waits for Meta approval, then sends. Each template variable is filled from param_mapping, in order."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string", "description": "Short title the user will recognise, e.g. 'Diwali WhatsApp Campaign'"},
         "lead_list_id": {"type": "string"},
         "template_id": {"type": "string"},
         "param_mapping": {"type": "array", "description": "One entry per variable {{1}}, {{2}}… in order", "items": {
             "type": "object", "properties": {
                 "source": {"type": "string", "enum": ["lead_name", "lead_column", "static"],
                            "description": "lead_name = contact's first name; lead_column = another column from their file; static = same text for everyone"},
                 "value": {"type": "string", "description": "Column name for lead_column, or the fixed text for static"},
                 "fallback": {"type": "string", "description": "Used when the contact has no value, e.g. 'ji' for a missing name"}},
             "required": ["source"]}},
         "consent_confirmed": {"type": "boolean", "description": "True only if the user has told you these contacts agreed to get WhatsApp messages from the business."},
         "auto_send": {"type": "boolean", "description": "True if the user already asked to send right away once approved. False to wait for their yes."}},
         "required": ["title", "lead_list_id", "template_id", "param_mapping", "consent_confirmed", "auto_send"]}},
    {"name": "confirm_send", "description": "The user said yes: start (or allow) sending this campaign as soon as the template is approved.",
     "input_schema": {"type": "object", "properties": {"campaign_id": {"type": "string"}}, "required": ["campaign_id"]}},
    {"name": "get_campaign_status", "description": "Progress and results of a campaign: sent, delivered, read, replied, failed.",
     "input_schema": {"type": "object", "properties": {"campaign_id": {"type": "string"}}, "required": ["campaign_id"]}},
    {"name": "control_campaign", "description": "Pause, resume or cancel a campaign.",
     "input_schema": {"type": "object", "properties": {"campaign_id": {"type": "string"},
                                                        "action": {"type": "string", "enum": ["pause", "resume", "cancel"]}},
                      "required": ["campaign_id", "action"]}},
]

TOOL_LABELS = {
    "list_lead_lists": "Contact lists dekh raha hoon",
    "get_lead_list": "Leads padh raha hoon",
    "check_template": "Template ke rules check kar raha hoon",
    "submit_template": "Meta ko template approval ke liye bhej raha hoon",
    "check_template_status": "Meta approval status dekh raha hoon",
    "create_campaign": "Campaign taiyaar kar raha hoon",
    "confirm_send": "Bhejne ki permission set kar raha hoon",
    "get_campaign_status": "Campaign ki report nikaal raha hoon",
    "control_campaign": "Campaign update kar raha hoon",
}


def _list_summary(ll: LeadList, sample_names: list[str] | None = None) -> dict:
    d = {"list_id": ll.id, "name": ll.name, "file": ll.source_filename, "total_rows": ll.total_rows,
         "valid_numbers": ll.valid, "invalid_numbers": ll.invalid, "duplicates_removed": ll.duplicates,
         "has_opt_in_column": ll.has_consent_column, "uploaded_at": ll.created_at.isoformat(),
         "columns": ll.columns}
    if ll.has_consent_column:
        d["opted_in"] = ll.opted_in
    if sample_names is not None:
        d["sample_first_names"] = sample_names
    return d


async def list_lead_lists(ctx: Ctx, **_):
    with session() as s:
        rows = s.scalars(select(LeadList).where(LeadList.tenant_id == ctx.tenant_id)
                         .order_by(LeadList.created_at.desc()).limit(10)).all()
        return {"lists": [_list_summary(r) for r in rows]}


async def get_lead_list(ctx: Ctx, list_id: str, **_):
    with session() as s:
        ll = s.get(LeadList, list_id)
        if not ll or ll.tenant_id != ctx.tenant_id:
            raise ToolError(f"No list with id {list_id}. Call list_lead_lists to see what exists.")
        names = s.scalars(select(Lead.name).where(Lead.list_id == list_id, Lead.name.is_not(None)).limit(3)).all()
        return _list_summary(ll, [n.split(" ")[0] for n in names])


async def check_template_tool(ctx: Ctx, name, language, category, body, example_values, footer=None, **_):
    res = check_template(name, language, category, body, example_values, footer)
    res["preview"] = render_body(body, example_values)
    return res


async def submit_template(ctx: Ctx, name, language, category, body, example_values, footer=None, **_):
    res = check_template(name, language, category, body, example_values, footer)
    if not res["ok"]:
        raise ToolError("Template has problems, fix them first: " + " | ".join(res["errors"]))
    with session() as s:
        taken = set(s.scalars(select(Template.name).where(Template.tenant_id == ctx.tenant_id)).all())
    final = name
    i = 2
    while final in taken:
        final = f"{name}_v{i}"; i += 1
    wa = get_whatsapp()
    try:
        out = await wa.create_template(final, language, category, body, example_values, footer)
    except WhatsAppError as e:
        raise ToolError(f"Meta did not accept the template: {e}")
    with session() as s:
        t = Template(tenant_id=ctx.tenant_id, name=final, language=language, category=category.upper(), body=body,
                     footer=footer, example_values=list(example_values), meta_id=out["meta_id"],
                     status=(out.get("status") or "PENDING").upper())
        s.add(t)
        s.flush()
        return {"template_id": t.id, "name": t.name, "status": t.status, "warnings": res["warnings"],
                "note": "Meta usually approves in a few minutes. The worker keeps checking; you do not need to poll."}


async def check_template_status(ctx: Ctx, template_id: str, **_):
    with session() as s:
        t = s.get(Template, template_id)
        if not t or t.tenant_id != ctx.tenant_id:
            raise ToolError(f"No template with id {template_id}")
        meta_id, created = t.meta_id, t.created_at
    try:
        st = await get_whatsapp().get_template_status(meta_id, created)
    except WhatsAppError as e:
        raise ToolError(f"Could not read status from Meta: {e}")
    with session() as s:
        t = s.get(Template, template_id)
        t.status = st["status"].upper()
        t.rejection_reason = st.get("reason")
        t.updated_at = now()
        return {"template_id": t.id, "name": t.name, "status": t.status, "rejection_reason": t.rejection_reason}


async def create_campaign(ctx: Ctx, title, lead_list_id, template_id, param_mapping, consent_confirmed, auto_send, **_):
    try:
        v = camp.create_campaign(tenant_id=ctx.tenant_id, conversation_id=ctx.conversation_id, title=title,
                                 lead_list_id=lead_list_id, template_id=template_id, param_mapping=param_mapping,
                                 consent_confirmed=bool(consent_confirmed), auto_send=bool(auto_send),
                                 live_mode=not get_settings().wa_dry_run)
    except camp.CampaignError as e:
        raise ToolError(str(e))
    v["daily_limit"] = get_settings().max_daily_sends
    return v


async def confirm_send(ctx: Ctx, campaign_id, **_):
    try:
        return camp.confirm_send(campaign_id)
    except camp.CampaignError as e:
        raise ToolError(str(e))


async def get_campaign_status(ctx: Ctx, campaign_id, **_):
    try:
        return camp.campaign_view(campaign_id)
    except camp.CampaignError as e:
        raise ToolError(str(e))


async def control_campaign(ctx: Ctx, campaign_id, action, **_):
    try:
        v = camp.campaign_view(campaign_id)
        if action == "pause" and v["status"] in ("sending", "ready", "awaiting_approval", "waiting_limit"):
            return camp.set_campaign_status(campaign_id, "paused", "Paused by the user")
        if action == "resume" and v["status"] == "paused":
            nxt = "sending" if v["template"]["status"] == "APPROVED" else "awaiting_approval"
            return camp.set_campaign_status(campaign_id, nxt)
        if action == "cancel" and v["status"] not in ("completed", "cancelled"):
            return camp.set_campaign_status(campaign_id, "cancelled", "Cancelled by the user")
        return {"unchanged": True, **v}
    except camp.CampaignError as e:
        raise ToolError(str(e))


HANDLERS = {
    "list_lead_lists": list_lead_lists,
    "get_lead_list": get_lead_list,
    "check_template": check_template_tool,
    "submit_template": submit_template,
    "check_template_status": check_template_status,
    "create_campaign": create_campaign,
    "confirm_send": confirm_send,
    "get_campaign_status": get_campaign_status,
    "control_campaign": control_campaign,
}


async def dispatch(name: str, args: dict, ctx: Ctx):
    h = HANDLERS.get(name)
    if not h:
        raise ToolError(f"Unknown tool {name}")
    return await h(ctx, **(args or {}))


# daily-life tools live in their own module; merged here so the agent sees one tool list
from .life_tools import LIFE_HANDLERS, LIFE_LABELS, LIFE_TOOLS  # noqa: E402

TOOLS.extend(LIFE_TOOLS)
TOOL_LABELS.update(LIFE_LABELS)
HANDLERS.update(LIFE_HANDLERS)
