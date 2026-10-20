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
    actor: str = "owner"        # owner | routine | staff:<id> | customer:<x> | approved:<ask id> (Hoola Employee, v0.58)


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
    # Hoola Employee: pause, trust per duty and team permissions are enforced here, for chat, calls and jobs alike
    from ..employee import service as employee
    try:
        held = employee.gate(ctx, name, args or {})
    except employee.Blocked as e:
        raise ToolError(str(e))
    if held is not None:
        return held
    try:
        out = await h(ctx, **(args or {}))
    except Exception as e:
        employee.after(ctx, name, args or {}, False, str(e)[:200])
        raise
    employee.after(ctx, name, args or {}, not (isinstance(out, dict) and out.get("error")))
    return out


# daily-life tools live in their own module; merged here so the agent sees one tool list
from .life_tools import LIFE_HANDLERS, LIFE_LABELS, LIFE_TOOLS  # noqa: E402

TOOLS.extend(LIFE_TOOLS)
TOOL_LABELS.update(LIFE_LABELS)
HANDLERS.update(LIFE_HANDLERS)

from .web_tools import WEB_HANDLERS, WEB_LABELS, WEB_TOOLS  # noqa: E402

TOOLS.extend(WEB_TOOLS)
TOOL_LABELS.update(WEB_LABELS)
HANDLERS.update(WEB_HANDLERS)

from .army_tools import ARMY_HANDLERS, ARMY_LABELS, ARMY_TOOLS  # noqa: E402

TOOLS.extend(ARMY_TOOLS)
TOOL_LABELS.update(ARMY_LABELS)
HANDLERS.update(ARMY_HANDLERS)

from .artifact_tools import ARTIFACT_HANDLERS, ARTIFACT_LABELS, ARTIFACT_TOOLS  # noqa: E402

TOOLS.extend(ARTIFACT_TOOLS)
TOOL_LABELS.update(ARTIFACT_LABELS)
HANDLERS.update(ARTIFACT_HANDLERS)

from .email_tools import EMAIL_HANDLERS, EMAIL_LABELS, EMAIL_TOOLS  # noqa: E402

TOOLS.extend(EMAIL_TOOLS)
TOOL_LABELS.update(EMAIL_LABELS)
HANDLERS.update(EMAIL_HANDLERS)

from .gcal_tools import GCAL_HANDLERS, GCAL_LABELS, GCAL_TOOLS  # noqa: E402

TOOLS.extend(GCAL_TOOLS)
TOOL_LABELS.update(GCAL_LABELS)
HANDLERS.update(GCAL_HANDLERS)

from .gdrive_tools import GDRIVE_HANDLERS, GDRIVE_LABELS, GDRIVE_TOOLS  # noqa: E402
from .sheets_tools import SHEETS_HANDLERS, SHEETS_LABELS, SHEETS_TOOLS  # noqa: E402

# Google Sheets has its own full toolset now (per-user sign-in); the old service-account sheet tools step aside
from .drive_tools import DRIVE_HANDLERS, DRIVE_LABELS, DRIVE_TOOLS  # noqa: E402
from .forms_tools import FORMS_HANDLERS, FORMS_LABELS, FORMS_TOOLS  # noqa: E402
from .slides_tools import SLIDES_HANDLERS, SLIDES_LABELS, SLIDES_TOOLS  # noqa: E402
from .photos_tools import PHOTOS_HANDLERS, PHOTOS_LABELS, PHOTOS_TOOLS  # noqa: E402
from .notebook_tools import NOTEBOOK_HANDLERS, NOTEBOOK_LABELS, NOTEBOOK_TOOLS  # noqa: E402
from .youtube_tools import YOUTUBE_HANDLERS, YOUTUBE_LABELS, YOUTUBE_TOOLS  # noqa: E402
from .appcheck_tools import APPCHECK_HANDLERS, APPCHECK_LABELS, APPCHECK_TOOLS  # noqa: E402
from .hoola_tools import HOOLA_HANDLERS, HOOLA_LABELS, HOOLA_TOOLS  # noqa: E402

# Google Sheets and Google Drive have their own full toolsets now (per-user sign-in, service account as fallback);
# the old service-account tools with the same names step aside
_new = set(SHEETS_HANDLERS) | set(DRIVE_HANDLERS)
TOOLS.extend([t for t in GDRIVE_TOOLS if t["name"] not in _new])
TOOL_LABELS.update({k: v for k, v in GDRIVE_LABELS.items() if k not in _new})
HANDLERS.update({k: v for k, v in GDRIVE_HANDLERS.items() if k not in _new})
for _t, _l, _h in ((SHEETS_TOOLS, SHEETS_LABELS, SHEETS_HANDLERS), (DRIVE_TOOLS, DRIVE_LABELS, DRIVE_HANDLERS),
                   (FORMS_TOOLS, FORMS_LABELS, FORMS_HANDLERS), (SLIDES_TOOLS, SLIDES_LABELS, SLIDES_HANDLERS),
                   (PHOTOS_TOOLS, PHOTOS_LABELS, PHOTOS_HANDLERS), (NOTEBOOK_TOOLS, NOTEBOOK_LABELS, NOTEBOOK_HANDLERS),
                   (YOUTUBE_TOOLS, YOUTUBE_LABELS, YOUTUBE_HANDLERS), (APPCHECK_TOOLS, APPCHECK_LABELS, APPCHECK_HANDLERS),
                   (HOOLA_TOOLS, HOOLA_LABELS, HOOLA_HANDLERS)):
    TOOLS.extend(_t)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)

from .bazar_tools import BAZAR_HANDLERS, BAZAR_LABELS, BAZAR_TOOLS  # noqa: E402

TOOLS.extend(BAZAR_TOOLS)
TOOL_LABELS.update(BAZAR_LABELS)
HANDLERS.update(BAZAR_HANDLERS)

from .maps_tools import MAPS_HANDLERS, MAPS_LABELS, MAPS_TOOLS  # noqa: E402

TOOLS.extend(MAPS_TOOLS)
TOOL_LABELS.update(MAPS_LABELS)
HANDLERS.update(MAPS_HANDLERS)

from .pc_tools import PC_HANDLERS, PC_LABELS, PC_TOOLS  # noqa: E402

TOOLS.extend(PC_TOOLS)
TOOL_LABELS.update(PC_LABELS)
HANDLERS.update(PC_HANDLERS)

from .bt_tools import BT_HANDLERS, BT_LABELS, BT_TOOLS  # noqa: E402

TOOLS.extend(BT_TOOLS)
TOOL_LABELS.update(BT_LABELS)
HANDLERS.update(BT_HANDLERS)

from .file_tools import FILE_HANDLERS, FILE_LABELS, FILE_TOOLS  # noqa: E402

TOOLS.extend(FILE_TOOLS)
TOOL_LABELS.update(FILE_LABELS)
HANDLERS.update(FILE_HANDLERS)

from .publicapi_tools import PUBLICAPI_HANDLERS, PUBLICAPI_LABELS, PUBLICAPI_TOOLS  # noqa: E402

TOOLS.extend(PUBLICAPI_TOOLS)
TOOL_LABELS.update(PUBLICAPI_LABELS)
HANDLERS.update(PUBLICAPI_HANDLERS)

from .tv_tools import TV_HANDLERS, TV_LABELS, TV_TOOLS  # noqa: E402

TOOLS.extend(TV_TOOLS)
TOOL_LABELS.update(TV_LABELS)
HANDLERS.update(TV_HANDLERS)

from .make_tools import MAKE_HANDLERS, MAKE_LABELS, MAKE_TOOLS  # noqa: E402

TOOLS.extend(MAKE_TOOLS)
TOOL_LABELS.update(MAKE_LABELS)
HANDLERS.update(MAKE_HANDLERS)

from .reel_tools import REEL_HANDLERS, REEL_LABELS, REEL_TOOLS  # noqa: E402

TOOLS.extend(REEL_TOOLS)
TOOL_LABELS.update(REEL_LABELS)
HANDLERS.update(REEL_HANDLERS)

# v0.56 phone background health (why a reminder did not come)
from .device_tools import DEVICE_HANDLERS, DEVICE_LABELS, DEVICE_TOOLS  # noqa: E402

TOOLS.extend(DEVICE_TOOLS)
TOOL_LABELS.update(DEVICE_LABELS)
HANDLERS.update(DEVICE_HANDLERS)

from .employee_tools import EMPLOYEE_HANDLERS, EMPLOYEE_LABELS, EMPLOYEE_TOOLS  # noqa: E402

TOOLS.extend(EMPLOYEE_TOOLS)
TOOL_LABELS.update(EMPLOYEE_LABELS)
HANDLERS.update(EMPLOYEE_HANDLERS)

# v0.59 PDF kaam + India calendar / bank / money facts
from .india_tools import INDIA_HANDLERS, INDIA_LABELS, INDIA_TOOLS  # noqa: E402

TOOLS.extend(INDIA_TOOLS)
TOOL_LABELS.update(INDIA_LABELS)
HANDLERS.update(INDIA_HANDLERS)
