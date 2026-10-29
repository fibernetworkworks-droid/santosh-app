"""The tools Santosh can use. Each has a JSON schema for Claude and a handler."""
from __future__ import annotations

import re
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
    place: str = ""             # v0.93 where she said a website job runs: pc | hoola | phone | "" (agent/where.py)


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
    {"name": "haan_karo", "description": (
        "v0.199 BOL-KAR-HAAN: a PC/browser step of THIS conversation's running job is waiting on a 'Haan, karo' "
        "approval card and the user's words in this turn approve it in context ('haan karo', 'kar do', 'theek hai', "
        "any clear yes). Call this to approve THAT step: the job moves at once. ONLY when such a step card is really "
        "pending; if the tool says none, don't insist. NEVER for money / UPI / bank-OTP / password cards: those "
        "approve only by tapping the card in the app; voice can never approve them - say so plainly."),
     "input_schema": {"type": "object", "properties": {
         "heard": {"type": "string", "description": "Her words that approved it (short quote)"}}}},
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
    "haan_karo": "Manzoori laga raha hoon",
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


async def haan_karo_tool(ctx: Ctx, heard: str = "", **_):
    """v0.199 BLOCK 2: the model judged her words as a yes for THIS conversation's pending step approval — resolve
    it without a tap. Money approvals can never reach here: voice_pending only carries non-money PC/browser steps
    (amount / tier>=3 / UPI-bank-OTP / money words are filtered before), and money words in her own sentence are
    refused again inside."""
    from ..bazar import service
    return service.voice_tool_approve(ctx.tenant_id, ctx.conversation_id, heard)


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
    "haan_karo": haan_karo_tool,
}


_reconnect_told: dict[str, float] = {}


def _google_refused(ctx: Ctx, e: BaseException) -> str:
    """Her Google sign-in was refused (expired / revoked): one clear line for the model + a card to connect again."""
    from ..google_auth import GoogleReconnect, reconnect_message
    try:
        from google.auth.exceptions import RefreshError
    except Exception:          # pragma: no cover
        RefreshError = ()      # type: ignore
    if isinstance(e, GoogleReconnect):
        msg = str(e)
    elif RefreshError and isinstance(e, RefreshError):
        from ..google_auth import mark_error
        mark_error(ctx.tenant_id, str(e))
        msg = reconnect_message("", str(e))
    else:
        return ""
    import time as _t
    if _t.time() - _reconnect_told.get(ctx.tenant_id, 0) > 1800 and ctx.conversation_id:
        _reconnect_told[ctx.tenant_id] = _t.time()
        try:
            from ..events import bus
            bus.publish(ctx.conversation_id, "google_reconnect", {"text": msg})
        except Exception:
            pass
    return msg


async def dispatch(name: str, args: dict, ctx: Ctx):
    h = HANDLERS.get(name)
    if not h:
        raise ToolError(f"Unknown tool {name}")
    moved = ""
    from . import pick, where
    pick.check(name, args or {}, ctx)   # v0.245 a plainly wrong pick (a PC not in view, data sent to a PC) never runs
    # v0.93 her words decide: her PC vs Hoola's own browser (never mixed up); v0.104 else the place where this chat's
    # website work is already running, so a job never jumps to another browser half way
    place_now = getattr(ctx, "place", "") or where.working(getattr(ctx, "conversation_id", "") or "")
    if place_now:
        asked = name
        name, args, moved = where.steer(name, args or {}, place_now)
        h = HANDLERS[name]
        if name == "pc_do" and asked != "pc_do":
            # a moved call must never start a NEW PC job over the one still running there (start() cancels it)
            from ..pc import operator as _pcop
            live = _pcop.running(ctx.tenant_id)
            if live is not None:
                return {"status": "pc_busy", "session_id": live.id, "where": "Aapka PC (HER computer)",
                        "say": ("This website work is already running on HER PC (session " + live.id + "). Don't start "
                                "another one and don't open your own browser: its result comes as a note, or check it with "
                                "pc_task_result. If she wants something else now, ask her first.")}
    where.worked(getattr(ctx, "conversation_id", "") or "", name, args or {})
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
        msg = _google_refused(ctx, e)
        if msg:        # v0.70: an expired Google sign-in used to surface as a raw "invalid_grant" crash
            raise ToolError(msg + " (Tell her this plainly in one or two lines and don't retry this tool now.)") from None
        if place_now == "pc" and name in ("pc_do", "pc_task_result") and isinstance(e, ToolError):
            raise ToolError(f"{e} (This website work runs on HER PC. Do NOT switch to your own browser by yourself: tell her "
                            "plainly and ask whether to wait for the PC or do it in your own browser.)") from None
        raise
    if isinstance(out, dict) and out.get("moved_to") == "pc":
        where.worked(getattr(ctx, "conversation_id", "") or "", name, args or {}, out)
    employee.after(ctx, name, args or {}, not (isinstance(out, dict) and out.get("error")))
    if moved and isinstance(out, dict):
        out = {**out, "ran_as": name, "place_note": moved}
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
from .photo_tools import PHOTO_HANDLERS, PHOTO_LABELS, PHOTO_TOOLS  # noqa: E402
from .appcheck_tools import APPCHECK_HANDLERS, APPCHECK_LABELS, APPCHECK_TOOLS  # noqa: E402
from .rea_tools import REA_HANDLERS, REA_LABELS, REA_TOOLS  # noqa: E402
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
                   (YOUTUBE_TOOLS, YOUTUBE_LABELS, YOUTUBE_HANDLERS), (PHOTO_TOOLS, PHOTO_LABELS, PHOTO_HANDLERS), (APPCHECK_TOOLS, APPCHECK_LABELS, APPCHECK_HANDLERS),
                   (REA_TOOLS, REA_LABELS, REA_HANDLERS), (HOOLA_TOOLS, HOOLA_LABELS, HOOLA_HANDLERS)):
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

# v0.189.0 Document Studio: Claude-grade PDF / Word / Excel / PowerPoint (design system + QA)
from .docstudio_tools import (DOCSTUDIO_HANDLERS, DOCSTUDIO_LABELS,  # noqa: E402
                              DOCSTUDIO_TOOLS)
from .data_tools import DATA_HANDLERS, DATA_LABELS, DATA_TOOLS  # noqa: E402  v0.238 data desk
TOOLS.extend(DATA_TOOLS)
TOOL_LABELS.update(DATA_LABELS)
HANDLERS.update(DATA_HANDLERS)

TOOLS.extend(DOCSTUDIO_TOOLS)
TOOL_LABELS.update(DOCSTUDIO_LABELS)
HANDLERS.update(DOCSTUDIO_HANDLERS)

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

# v0.63 seekhe hue kaam (procedures Hoola learned)
from .procedure_tools import PROCEDURE_HANDLERS, PROCEDURE_LABELS, PROCEDURE_TOOLS  # noqa: E402

TOOLS.extend(PROCEDURE_TOOLS)
TOOL_LABELS.update(PROCEDURE_LABELS)
HANDLERS.update(PROCEDURE_HANDLERS)

# v0.59 the WhatsApp customer's tools: callable (customer turns, owner-approved asks) but never offered to the owner's model
from ..employee.inbox import BIZ_HANDLERS, BIZ_LABELS  # noqa: E402

TOOL_LABELS.update(BIZ_LABELS)
HANDLERS.update(BIZ_HANDLERS)

# v0.65 Hoola Video Editor
from .video_tools import VIDEO_HANDLERS, VIDEO_LABELS, VIDEO_TOOLS  # noqa: E402

TOOLS.extend(VIDEO_TOOLS)
TOOL_LABELS.update(VIDEO_LABELS)
HANDLERS.update(VIDEO_HANDLERS)

# v0.66 Hoola Motion
from .motion_tools import MOTION_HANDLERS, MOTION_LABELS, MOTION_TOOLS  # noqa: E402

TOOLS.extend(MOTION_TOOLS)
TOOL_LABELS.update(MOTION_LABELS)
HANDLERS.update(MOTION_HANDLERS)

# v0.67 Hoola Computer Operator
from .operator_tools import OPERATOR_HANDLERS, OPERATOR_LABELS, OPERATOR_TOOLS  # noqa: E402
from .jaanch_tools import JAANCH_HANDLERS, JAANCH_LABELS, JAANCH_TOOLS  # noqa: E402

TOOLS.extend(OPERATOR_TOOLS)
TOOL_LABELS.update(OPERATOR_LABELS)
HANDLERS.update(OPERATOR_HANDLERS)
TOOLS.extend(JAANCH_TOOLS)
TOOL_LABELS.update(JAANCH_LABELS)
HANDLERS.update(JAANCH_HANDLERS)

# v0.68 Hoola Video Studio (AI-generated shots)
from .studio_tools import STUDIO_HANDLERS, STUDIO_LABELS, STUDIO_TOOLS  # noqa: E402

TOOLS.extend(STUDIO_TOOLS)
TOOL_LABELS.update(STUDIO_LABELS)
HANDLERS.update(STUDIO_HANDLERS)

# v0.70 Google connection check
from .google_tools import GOOGLE_HANDLERS, GOOGLE_LABELS, GOOGLE_TOOLS  # noqa: E402

TOOLS.extend(GOOGLE_TOOLS)
TOOL_LABELS.update(GOOGLE_LABELS)
HANDLERS.update(GOOGLE_HANDLERS)

# v0.75 Pehchaan Locker
from .id_tools import ID_HANDLERS, ID_LABELS, ID_TOOLS  # noqa: E402

TOOLS.extend(ID_TOOLS)
TOOL_LABELS.update(ID_LABELS)
HANDLERS.update(ID_HANDLERS)

# v0.80 Order karo (shopping / food / travel up to payment; she pays)
from .shop_tools import SHOP_HANDLERS, SHOP_LABELS, SHOP_TOOLS  # noqa: E402

TOOLS.extend(SHOP_TOOLS)
TOOL_LABELS.update(SHOP_LABELS)
HANDLERS.update(SHOP_HANDLERS)

# v0.82 Darzi Sahayak (tailor / boutique coworker)
from .darzi_tools import DARZI_HANDLERS, DARZI_LABELS, DARZI_TOOLS  # noqa: E402

TOOLS.extend(DARZI_TOOLS)
TOOL_LABELS.update(DARZI_LABELS)
HANDLERS.update(DARZI_HANDLERS)

# v0.84 Chai Sahayak (chai stall coworker: galla from UPI alerts, best hours, tomorrow's milk / sugar)
from .chai_tools import CHAI_HANDLERS, CHAI_LABELS, CHAI_TOOLS  # noqa: E402

TOOLS.extend(CHAI_TOOLS)
TOOL_LABELS.update(CHAI_LABELS)
HANDLERS.update(CHAI_HANDLERS)
# v0.85 Daftar Sahayak (office manager coworker)
from .office_tools import OFFICE_HANDLERS, OFFICE_LABELS, OFFICE_TOOLS  # noqa: E402

TOOLS.extend(OFFICE_TOOLS)
TOOL_LABELS.update(OFFICE_LABELS)
HANDLERS.update(OFFICE_HANDLERS)

# v0.87 Lekhak Sahayak (typist + translator coworker)
from .lekhak_tools import LEKHAK_HANDLERS, LEKHAK_LABELS, LEKHAK_TOOLS  # noqa: E402

TOOLS.extend(LEKHAK_TOOLS)
TOOL_LABELS.update(LEKHAK_LABELS)
HANDLERS.update(LEKHAK_HANDLERS)

# v0.88 Mobile Dukaan Sahayak (mobile recharge + repair shop coworker)
from .mshop_tools import MSHOP_HANDLERS, MSHOP_LABELS, MSHOP_TOOLS  # noqa: E402

TOOLS.extend(MSHOP_TOOLS)
TOOL_LABELS.update(MSHOP_LABELS)
HANDLERS.update(MSHOP_HANDLERS)

# v0.90 Phone Doctor (her phone's problem, end to end: phone self-check, one fix at a time, then shop / operator / CEIR / 1930)
from .phonedoc_tools import PHONEDOC_HANDLERS, PHONEDOC_LABELS, PHONEDOC_TOOLS  # noqa: E402

TOOLS.extend(PHONEDOC_TOOLS)
TOOL_LABELS.update(PHONEDOC_LABELS)
HANDLERS.update(PHONEDOC_HANDLERS)

# v0.93 GST Sahayak (GST practitioner coworker: bills, GSTR-1 JSON, 2B + IMS, 3B, notices; filing on her haan, she pays)
from .gst_tools import GST_HANDLERS, GST_LABELS, GST_TOOLS  # noqa: E402

TOOLS.extend(GST_TOOLS)
TOOL_LABELS.update(GST_LABELS)
HANDLERS.update(GST_HANDLERS)

# v0.94 Payroll Officer (salary run: attendance, PF / ESIC / PT / TDS, payslips, bank file, ECR; she approves and pays)
from .payroll_tools import PAYROLL_HANDLERS, PAYROLL_LABELS, PAYROLL_TOOLS  # noqa: E402

TOOLS.extend(PAYROLL_TOOLS)
TOOL_LABELS.update(PAYROLL_LABELS)
HANDLERS.update(PAYROLL_HANDLERS)

# v0.95 Financial Analyst (books + bank -> P&L, ratios, cash runway, aging, MSME risk, loan check, advance tax, MIS)
from .analyst_tools import ANALYST_HANDLERS, ANALYST_LABELS, ANALYST_TOOLS  # noqa: E402

TOOLS.extend(ANALYST_TOOLS)
TOOL_LABELS.update(ANALYST_LABELS)
HANDLERS.update(ANALYST_HANDLERS)

# v0.96 Auditor's Assistant (materiality, analytics, JE tests, cash / TDS rules, Benford, sampling, confirmations, WPs)
from .audit_tools import AUDIT_HANDLERS, AUDIT_LABELS, AUDIT_TOOLS  # noqa: E402

TOOLS.extend(AUDIT_TOOLS)
TOOL_LABELS.update(AUDIT_LABELS)
HANDLERS.update(AUDIT_HANDLERS)

from .askform_tools import ASKFORM_HANDLERS, ASKFORM_LABELS, ASKFORM_TOOLS  # noqa: E402

TOOLS.extend(ASKFORM_TOOLS)
TOOL_LABELS.update(ASKFORM_LABELS)
HANDLERS.update(ASKFORM_HANDLERS)

# v0.98 Bima Sahayak (insurance agent: clients, policies, renewals, needs, claims)
from .insure_tools import INSURE_HANDLERS, INSURE_LABELS, INSURE_TOOLS  # noqa: E402

TOOLS.extend(INSURE_TOOLS)
TOOL_LABELS.update(INSURE_LABELS)
HANDLERS.update(INSURE_HANDLERS)
# v0.99 Telecaller Sahayak (Hoola prepares calls, a person makes them)
from .telecall_tools import TELECALL_HANDLERS, TELECALL_LABELS, TELECALL_TOOLS  # noqa: E402

TOOLS.extend(TELECALL_TOOLS)
TOOL_LABELS.update(TELECALL_LABELS)
HANDLERS.update(TELECALL_HANDLERS)
# v0.101 Kalam Sahayak (content writer: blogs, product pages, emails; publishing on her tap)
from .kalam_tools import KALAM_HANDLERS, KALAM_LABELS, KALAM_TOOLS  # noqa: E402

TOOLS.extend(KALAM_TOOLS)
TOOL_LABELS.update(KALAM_LABELS)
HANDLERS.update(KALAM_HANDLERS)


from .usage_tools import USAGE_HANDLERS, USAGE_LABELS, USAGE_TOOLS  # noqa: E402

TOOLS.extend(USAGE_TOOLS)
TOOL_LABELS.update(USAGE_LABELS)
HANDLERS.update(USAGE_HANDLERS)

# v0.103 SEO Sahayak (site audit, Core Web Vitals, Search Console, schema, content briefs, Business Profile drafts)
from .seo_tools import SEO_HANDLERS, SEO_LABELS, SEO_TOOLS  # noqa: E402

TOOLS.extend(SEO_TOOLS)
TOOL_LABELS.update(SEO_LABELS)
HANDLERS.update(SEO_HANDLERS)

# v0.107 Thok Sahayak (wholesale: orders -> GST bills, credit, collections, cheques, purchases, reorder, margins)
from .thok_tools import THOK_HANDLERS, THOK_LABELS, THOK_TOOLS  # noqa: E402

TOOLS.extend(THOK_TOOLS)
TOOL_LABELS.update(THOK_LABELS)
HANDLERS.update(THOK_HANDLERS)

# v0.108 Document desk + Sheet Milaan (her PC files, edits on her tap) + yaad_khojo (search all memory)
from .desk_tools import DESK_HANDLERS, DESK_LABELS, DESK_TOOLS  # noqa: E402

TOOLS.extend(DESK_TOOLS)
TOOL_LABELS.update(DESK_LABELS)
HANDLERS.update(DESK_HANDLERS)

# v0.250 FULL CLAUDE MODE 3B: haal_ki_chats - her other recent chats by time (Claude's "recent chats")
from .recall_tools import RECALL_HANDLERS, RECALL_LABELS, RECALL_TOOLS  # noqa: E402

TOOLS.extend(RECALL_TOOLS)
TOOL_LABELS.update(RECALL_LABELS)
HANDLERS.update(RECALL_HANDLERS)

# v0.110 Niryat Sahayak (exporter: buyers, PI -> invoice + packing list, shipping bill, RBI realisation, RoDTEP, FTA / CBAM checks)
from .niryat_tools import NIRYAT_HANDLERS, NIRYAT_LABELS, NIRYAT_TOOLS  # noqa: E402

TOOLS.extend(NIRYAT_TOOLS)
TOOL_LABELS.update(NIRYAT_LABELS)
HANDLERS.update(NIRYAT_HANDLERS)

# v0.111 Ads Sahayak (performance marketer: reports -> leaks -> budget changes on her tap -> copies to test)
from .ads_tools import ADS_HANDLERS, ADS_LABELS, ADS_TOOLS  # noqa: E402

TOOLS.extend(ADS_TOOLS)
TOOL_LABELS.update(ADS_LABELS)
HANDLERS.update(ADS_HANDLERS)

# v0.115 Franchise Sahayak (outlets, sales, royalty statements with GST / RCM / TDS, P&L, licences, SOP audits)
from .franchise_tools import FRANCHISE_HANDLERS, FRANCHISE_LABELS, FRANCHISE_TOOLS  # noqa: E402

TOOLS.extend(FRANCHISE_TOOLS)
TOOL_LABELS.update(FRANCHISE_LABELS)
HANDLERS.update(FRANCHISE_HANDLERS)

# v0.116 outside A2A agents, AA / ABDM consent hand-offs, DigiLocker requester, optional ONDC listing
from .handoff_tools import HANDOFF_HANDLERS, HANDOFF_LABELS, HANDOFF_TOOLS  # noqa: E402

TOOLS.extend(HANDOFF_TOOLS)
TOOL_LABELS.update(HANDOFF_LABELS)
HANDLERS.update(HANDOFF_HANDLERS)

# v0.117 Theka Sahayak (contractor: tenders, BOQ, measurement book, RA bills + deductions, subcontractors, site diary, EOT)
from .theka_tools import THEKA_HANDLERS, THEKA_LABELS, THEKA_TOOLS  # noqa: E402

TOOLS.extend(THEKA_TOOLS)
TOOL_LABELS.update(THEKA_LABELS)
HANDLERS.update(THEKA_HANDLERS)

# v0.118 Brand Sahayak (brand designer: kit from her logo, posters in every size, final artwork only on her tap)
from .brand_tools import BRAND_HANDLERS, BRAND_LABELS, BRAND_TOOLS  # noqa: E402

TOOLS.extend(BRAND_TOOLS)
TOOL_LABELS.update(BRAND_LABELS)
HANDLERS.update(BRAND_HANDLERS)
# v0.119 what Hoola learned about how she speaks (pace, pauses, tone, her words, mis-hearings)
from .voicestyle_tools import SEEKHA_HANDLERS, SEEKHA_LABELS, SEEKHA_TOOLS  # noqa: E402

TOOLS.extend(SEEKHA_TOOLS)
TOOL_LABELS.update(SEEKHA_LABELS)
HANDLERS.update(SEEKHA_HANDLERS)

# v0.121 Website Sahayak (website developer / designer: 1 lakh brief library, live build board, checks, preview)
from .site_tools import SITE_HANDLERS, SITE_LABELS, SITE_TOOLS  # noqa: E402

TOOLS.extend(SITE_TOOLS)
TOOL_LABELS.update(SITE_LABELS)
HANDLERS.update(SITE_HANDLERS)

# v0.128 App Sahayak (native app designer: 1 lakh app briefs, every screen designed + tap-through prototype before the build)
from .app_tools import APP_HANDLERS, APP_LABELS, APP_TOOLS  # noqa: E402

TOOLS.extend(APP_TOOLS)
TOOL_LABELS.update(APP_LABELS)
HANDLERS.update(APP_HANDLERS)

# v0.133 Seva suite: 7 customer-support Sahayaks (support agent, IT helpdesk, complaints, after-sales, feedback, returns,
# community). Customer-safe biz_* tools go into the business WhatsApp inbox list only (never offered to her model).
from .seva_tools import BIZ_SEVA_TOOLS, SEVA_HANDLERS, SEVA_LABELS, SEVA_TOOLS  # noqa: E402
from .helpdesk_tools import HELPDESK_HANDLERS, HELPDESK_LABELS, HELPDESK_TOOLS  # noqa: E402
from .shikayat_tools import (SHIKAYAT_BIZ_HANDLERS, SHIKAYAT_BIZ_LABELS, SHIKAYAT_BIZ_TOOLS, SHIKAYAT_HANDLERS,  # noqa: E402
                             SHIKAYAT_LABELS, SHIKAYAT_TOOLS)
from .aftersales_tools import AFTERSALES_HANDLERS, AFTERSALES_LABELS, AFTERSALES_TOOLS  # noqa: E402
from .feedback_tools import FEEDBACK_HANDLERS, FEEDBACK_LABELS, FEEDBACK_TOOLS  # noqa: E402
from .wapsi_tools import (WAPSI_BIZ_HANDLERS, WAPSI_BIZ_LABELS, WAPSI_BIZ_TOOLS, WAPSI_HANDLERS, WAPSI_LABELS,  # noqa: E402
                          WAPSI_TOOLS)
from .samudaay_tools import SAMUDAAY_HANDLERS, SAMUDAAY_LABELS, SAMUDAAY_TOOLS  # noqa: E402
from .callcentre_tools import CALLCENTRE_HANDLERS, CALLCENTRE_LABELS, CALLCENTRE_TOOLS  # noqa: E402

for _t, _l, _h in ((SEVA_TOOLS, SEVA_LABELS, SEVA_HANDLERS), (HELPDESK_TOOLS, HELPDESK_LABELS, HELPDESK_HANDLERS),
                   (SHIKAYAT_TOOLS, SHIKAYAT_LABELS, SHIKAYAT_HANDLERS), (AFTERSALES_TOOLS, AFTERSALES_LABELS, AFTERSALES_HANDLERS),
                   (FEEDBACK_TOOLS, FEEDBACK_LABELS, FEEDBACK_HANDLERS), (WAPSI_TOOLS, WAPSI_LABELS, WAPSI_HANDLERS),
                   (SAMUDAAY_TOOLS, SAMUDAAY_LABELS, SAMUDAAY_HANDLERS),
                   (CALLCENTRE_TOOLS, CALLCENTRE_LABELS, CALLCENTRE_HANDLERS)):
    TOOLS.extend(_t)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)
TOOL_LABELS.update(SHIKAYAT_BIZ_LABELS)
TOOL_LABELS.update(WAPSI_BIZ_LABELS)
HANDLERS.update(SHIKAYAT_BIZ_HANDLERS)
HANDLERS.update(WAPSI_BIZ_HANDLERS)

from ..employee import inbox as _biz_inbox  # noqa: E402

_have = {t["name"] for t in _biz_inbox.BIZ_TOOLS}
_biz_inbox.BIZ_TOOLS[:0] = [t for t in BIZ_SEVA_TOOLS if t["name"] not in _have]   # biz_seva_answer first
_biz_inbox.BIZ_TOOLS.extend(t for t in SHIKAYAT_BIZ_TOOLS + WAPSI_BIZ_TOOLS if t["name"] not in _have)
_biz_inbox.BIZ_HANDLERS.update({k: v for k, v in SEVA_HANDLERS.items() if k.startswith("biz_")})
_biz_inbox.BIZ_HANDLERS.update(SHIKAYAT_BIZ_HANDLERS)
_biz_inbox.BIZ_HANDLERS.update(WAPSI_BIZ_HANDLERS)
_biz_inbox.BIZ_LABELS.update({k: v for k, v in SEVA_LABELS.items() if k.startswith("biz_")})
_biz_inbox.BIZ_LABELS.update(SHIKAYAT_BIZ_LABELS)
_biz_inbox.BIZ_LABELS.update(WAPSI_BIZ_LABELS)

# v0.134 Gyaan: knowledge base search (gyaan_khojo, read only) + management (gyaan)
from .gyaan_tools import GYAAN_HANDLERS, GYAAN_LABELS, GYAAN_TOOLS  # noqa: E402

TOOLS.extend(GYAAN_TOOLS)
TOOL_LABELS.update(GYAAN_LABELS)
HANDLERS.update(GYAAN_HANDLERS)

# v0.141 3D Studio: Blender in a locked box (blender_3d)
from .blender_tools import BLENDER_HANDLERS, BLENDER_LABELS, BLENDER_TOOLS  # noqa: E402
from .pgdb_tools import PGDB_HANDLERS, PGDB_LABELS, PGDB_TOOLS  # noqa: E402

TOOLS.extend(BLENDER_TOOLS)
TOOL_LABELS.update(BLENDER_LABELS)
HANDLERS.update(BLENDER_HANDLERS)
TOOLS.extend(PGDB_TOOLS)
TOOL_LABELS.update(PGDB_LABELS)
HANDLERS.update(PGDB_HANDLERS)

# v0.136 live state of her long jobs (kaam_status, read only)
from .kaam_tools import KAAM_HANDLERS, KAAM_LABELS, KAAM_TOOLS  # noqa: E402

TOOLS.extend(KAAM_TOOLS)
TOOL_LABELS.update(KAAM_LABELS)
HANDLERS.update(KAAM_HANDLERS)

# v0.137 Tech suite: 9 Technology & software Sahayaks (developer, QA, IT admin, ISP NOC, cyber suraksha, DevOps,
# technical writer, app reviewer, product manager). Each tool object is registered once (some modules also export
# alias names for the same objects).
from .devsahayak_tools import DEV_HANDLERS, DEV_LABELS, DEV_TOOLS  # noqa: E402
from .qa_tools import QA_HANDLERS, QA_LABELS, QA_TOOLS  # noqa: E402
from .itadmin_tools import ITADMIN_HANDLERS, ITADMIN_LABELS, ITADMIN_TOOLS  # noqa: E402
from .ispnoc_tools import NOC_HANDLERS, NOC_LABELS, NOC_TOOLS  # noqa: E402
from .cyber_tools import CYBER_HANDLERS, CYBER_LABELS, CYBER_TOOLS  # noqa: E402
from .devops_tools import DEVOPS_HANDLERS, DEVOPS_LABELS, DEVOPS_TOOLS  # noqa: E402
from .docwriter_tools import DOCWRITER_HANDLERS, DOCWRITER_LABELS, DOCWRITER_TOOLS  # noqa: E402
from .appreview_tools import APPREVIEW_HANDLERS, APPREVIEW_LABELS, APPREVIEW_TOOLS  # noqa: E402
from .product_tools import PRODUCT_HANDLERS, PRODUCT_LABELS, PRODUCT_TOOLS  # noqa: E402

for _t, _l, _h in ((DEV_TOOLS, DEV_LABELS, DEV_HANDLERS), (QA_TOOLS, QA_LABELS, QA_HANDLERS),
                   (ITADMIN_TOOLS, ITADMIN_LABELS, ITADMIN_HANDLERS), (NOC_TOOLS, NOC_LABELS, NOC_HANDLERS),
                   (CYBER_TOOLS, CYBER_LABELS, CYBER_HANDLERS), (DEVOPS_TOOLS, DEVOPS_LABELS, DEVOPS_HANDLERS),
                   (DOCWRITER_TOOLS, DOCWRITER_LABELS, DOCWRITER_HANDLERS),
                   (APPREVIEW_TOOLS, APPREVIEW_LABELS, APPREVIEW_HANDLERS),
                   (PRODUCT_TOOLS, PRODUCT_LABELS, PRODUCT_HANDLERS)):
    _seen = {t["name"] for t in TOOLS}
    TOOLS.extend(t for t in _t if t["name"] not in _seen)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)

# v0.139 Safar suite: 7 Logistics, transport & travel Sahayaks (logistics coordinator, fleet manager, warehouse manager, courier
# desk, travel agent, driver coordinator, import & customs desk). Courier's customer-safe biz_parcel_* tools go into the business
# WhatsApp inbox only (never offered to her model), like the Seva suite's biz_* tools.
from .customs_tools import CUSTOMS_HANDLERS, CUSTOMS_LABELS, CUSTOMS_TOOLS  # noqa: E402
from .travel_tools import TRAVEL_HANDLERS, TRAVEL_LABELS, TRAVEL_TOOLS  # noqa: E402
from .warehouse_tools import WAREHOUSE_HANDLERS, WAREHOUSE_LABELS, WAREHOUSE_TOOLS  # noqa: E402
from .fleet_tools import FLEET_HANDLERS, FLEET_LABELS, FLEET_TOOLS  # noqa: E402
from .courier_tools import (COURIER_BIZ_HANDLERS, COURIER_BIZ_LABELS, COURIER_BIZ_TOOLS, COURIER_HANDLERS,  # noqa: E402
                            COURIER_LABELS, COURIER_TOOLS)
from .drivers_tools import DRIVERS_HANDLERS, DRIVERS_LABELS, DRIVERS_TOOLS  # noqa: E402
from .logistics_tools import LOGISTICS_HANDLERS, LOGISTICS_LABELS, LOGISTICS_TOOLS  # noqa: E402

for _t, _l, _h in ((CUSTOMS_TOOLS, CUSTOMS_LABELS, CUSTOMS_HANDLERS), (TRAVEL_TOOLS, TRAVEL_LABELS, TRAVEL_HANDLERS),
                   (WAREHOUSE_TOOLS, WAREHOUSE_LABELS, WAREHOUSE_HANDLERS), (FLEET_TOOLS, FLEET_LABELS, FLEET_HANDLERS),
                   (COURIER_TOOLS, COURIER_LABELS, COURIER_HANDLERS), (DRIVERS_TOOLS, DRIVERS_LABELS, DRIVERS_HANDLERS),
                   (LOGISTICS_TOOLS, LOGISTICS_LABELS, LOGISTICS_HANDLERS)):
    _seen = {t["name"] for t in TOOLS}
    TOOLS.extend(t for t in _t if t["name"] not in _seen)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)
TOOL_LABELS.update(COURIER_BIZ_LABELS)
HANDLERS.update(COURIER_BIZ_HANDLERS)
_have = {t["name"] for t in _biz_inbox.BIZ_TOOLS}
_biz_inbox.BIZ_TOOLS.extend(t for t in COURIER_BIZ_TOOLS if t["name"] not in _have)
_biz_inbox.BIZ_HANDLERS.update(COURIER_BIZ_HANDLERS)
_biz_inbox.BIZ_LABELS.update(COURIER_BIZ_LABELS)

# v0.144 Makaan suite: 6 Real estate & construction Sahayaks (real estate agent, property manager, site supervisor, interior
# designer, architect's assistant, housing society manager). Rentdesk's customer-safe biz_rent_* tools go into the business
# WhatsApp inbox only (never offered to her model), like the courier desk's biz_parcel_* tools.
from .propagent_tools import PROPAGENT_HANDLERS, PROPAGENT_LABELS, PROPAGENT_TOOLS  # noqa: E402
from .rentdesk_tools import (RENTDESK_BIZ_HANDLERS, RENTDESK_BIZ_LABELS, RENTDESK_BIZ_TOOLS, RENTDESK_HANDLERS,  # noqa: E402
                             RENTDESK_LABELS, RENTDESK_TOOLS)
from .sitesup_tools import SITESUP_HANDLERS, SITESUP_LABELS, SITESUP_TOOLS  # noqa: E402
from .interior_tools import INTERIOR_HANDLERS, INTERIOR_LABELS, INTERIOR_TOOLS  # noqa: E402
from .archassist_tools import ARCHASSIST_HANDLERS, ARCHASSIST_LABELS, ARCHASSIST_TOOLS  # noqa: E402
from .society_tools import SOCIETY_HANDLERS, SOCIETY_LABELS, SOCIETY_TOOLS  # noqa: E402

for _t, _l, _h in ((PROPAGENT_TOOLS, PROPAGENT_LABELS, PROPAGENT_HANDLERS), (RENTDESK_TOOLS, RENTDESK_LABELS, RENTDESK_HANDLERS),
                   (SITESUP_TOOLS, SITESUP_LABELS, SITESUP_HANDLERS), (INTERIOR_TOOLS, INTERIOR_LABELS, INTERIOR_HANDLERS),
                   (ARCHASSIST_TOOLS, ARCHASSIST_LABELS, ARCHASSIST_HANDLERS), (SOCIETY_TOOLS, SOCIETY_LABELS, SOCIETY_HANDLERS)):
    _seen = {t["name"] for t in TOOLS}
    TOOLS.extend(t for t in _t if t["name"] not in _seen)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)
TOOL_LABELS.update(RENTDESK_BIZ_LABELS)
HANDLERS.update(RENTDESK_BIZ_HANDLERS)
_have = {t["name"] for t in _biz_inbox.BIZ_TOOLS}
_biz_inbox.BIZ_TOOLS.extend(t for t in RENTDESK_BIZ_TOOLS if t["name"] not in _have)
_biz_inbox.BIZ_HANDLERS.update(RENTDESK_BIZ_HANDLERS)
_biz_inbox.BIZ_LABELS.update(RENTDESK_BIZ_LABELS)

# v0.150 Kanoon suite: 8 Law, compliance & safety Sahayaks (lawyer's junior, legal researcher, compliance officer, contract
# manager, company secretary, notary desk, PI desk, data protection officer). Every card is decided only by her app tap.
from .vakil_tools import VAKIL_HANDLERS, VAKIL_LABELS, VAKIL_TOOLS  # noqa: E402
from .legalres_tools import LEGALRES_HANDLERS, LEGALRES_LABELS, LEGALRES_TOOLS  # noqa: E402
from .compliance_tools import COMPLIANCE_HANDLERS, COMPLIANCE_LABELS, COMPLIANCE_TOOLS  # noqa: E402
from .contracts_tools import CONTRACTS_HANDLERS, CONTRACTS_LABELS, CONTRACTS_TOOLS  # noqa: E402
from .cosec_tools import COSEC_HANDLERS, COSEC_LABELS, COSEC_TOOLS  # noqa: E402
from .notary_tools import NOTARY_HANDLERS, NOTARY_LABELS, NOTARY_TOOLS  # noqa: E402
from .pidesk_tools import PIDESK_HANDLERS, PIDESK_LABELS, PIDESK_TOOLS  # noqa: E402
from .dpo_tools import DPO_HANDLERS, DPO_LABELS, DPO_TOOLS  # noqa: E402

for _t, _l, _h in ((VAKIL_TOOLS, VAKIL_LABELS, VAKIL_HANDLERS), (LEGALRES_TOOLS, LEGALRES_LABELS, LEGALRES_HANDLERS), (COMPLIANCE_TOOLS, COMPLIANCE_LABELS, COMPLIANCE_HANDLERS), (CONTRACTS_TOOLS, CONTRACTS_LABELS, CONTRACTS_HANDLERS), (COSEC_TOOLS, COSEC_LABELS, COSEC_HANDLERS), (NOTARY_TOOLS, NOTARY_LABELS, NOTARY_HANDLERS), (PIDESK_TOOLS, PIDESK_LABELS, PIDESK_HANDLERS), (DPO_TOOLS, DPO_LABELS, DPO_HANDLERS)):
    _seen = {t["name"] for t in TOOLS}
    TOOLS.extend(t for t in _t if t["name"] not in _seen)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)

# v0.152 Mehmaan suite: 6 Hospitality, events & tourism Sahayaks (hotel front office, event planner, wedding planner, tour
# guide, homestay host, banquet sales). Every card / message is decided or sent only by her app tap.
from .frontoffice_tools import FRONTOFFICE_HANDLERS, FRONTOFFICE_LABELS, FRONTOFFICE_TOOLS  # noqa: E402
from .eventplan_tools import EVENTPLAN_HANDLERS, EVENTPLAN_LABELS, EVENTPLAN_TOOLS  # noqa: E402
from .shaadi_tools import SHAADI_HANDLERS, SHAADI_LABELS, SHAADI_TOOLS  # noqa: E402
from .tourguide_tools import TOURGUIDE_HANDLERS, TOURGUIDE_LABELS, TOURGUIDE_TOOLS  # noqa: E402
from .homestay_tools import HOMESTAY_HANDLERS, HOMESTAY_LABELS, HOMESTAY_TOOLS  # noqa: E402
from .banquet_tools import BANQUET_HANDLERS, BANQUET_LABELS, BANQUET_TOOLS  # noqa: E402

for _t, _l, _h in ((FRONTOFFICE_TOOLS, FRONTOFFICE_LABELS, FRONTOFFICE_HANDLERS), (EVENTPLAN_TOOLS, EVENTPLAN_LABELS, EVENTPLAN_HANDLERS), (SHAADI_TOOLS, SHAADI_LABELS, SHAADI_HANDLERS), (TOURGUIDE_TOOLS, TOURGUIDE_LABELS, TOURGUIDE_HANDLERS), (HOMESTAY_TOOLS, HOMESTAY_LABELS, HOMESTAY_HANDLERS), (BANQUET_TOOLS, BANQUET_LABELS, BANQUET_HANDLERS)):
    _seen = {t["name"] for t in TOOLS}
    TOOLS.extend(t for t in _t if t["name"] not in _seen)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)

# v0.156 Kala suite: 10 Media, design & creative Sahayaks (video editor desk, motion designer, AI film producer, journalist,
# photographer's assistant, graphic designer, artist manager, author & editor, podcast producer, influencer manager).
# Every card / message is decided or sent only by her app tap.
from .editdesk_tools import EDITDESK_HANDLERS, EDITDESK_LABELS, EDITDESK_TOOLS  # noqa: E402
from .motiondesk_tools import MOTIONDESK_HANDLERS, MOTIONDESK_LABELS, MOTIONDESK_TOOLS  # noqa: E402
from .filmdesk_tools import FILMDESK_HANDLERS, FILMDESK_LABELS, FILMDESK_TOOLS  # noqa: E402
from .patrakar_tools import PATRAKAR_HANDLERS, PATRAKAR_LABELS, PATRAKAR_TOOLS  # noqa: E402
from .photoassist_tools import PHOTOASSIST_HANDLERS, PHOTOASSIST_LABELS, PHOTOASSIST_TOOLS  # noqa: E402
from .graphic_tools import GRAPHIC_HANDLERS, GRAPHIC_LABELS, GRAPHIC_TOOLS  # noqa: E402
from .artistmgr_tools import ARTISTMGR_HANDLERS, ARTISTMGR_LABELS, ARTISTMGR_TOOLS  # noqa: E402
from .kitab_tools import KITAB_HANDLERS, KITAB_LABELS, KITAB_TOOLS  # noqa: E402
from .podcast_tools import PODCAST_HANDLERS, PODCAST_LABELS, PODCAST_TOOLS  # noqa: E402
from .influencer_tools import INFLUENCER_HANDLERS, INFLUENCER_LABELS, INFLUENCER_TOOLS  # noqa: E402

for _t, _l, _h in ((EDITDESK_TOOLS, EDITDESK_LABELS, EDITDESK_HANDLERS), (MOTIONDESK_TOOLS, MOTIONDESK_LABELS, MOTIONDESK_HANDLERS), (FILMDESK_TOOLS, FILMDESK_LABELS, FILMDESK_HANDLERS), (PATRAKAR_TOOLS, PATRAKAR_LABELS, PATRAKAR_HANDLERS), (PHOTOASSIST_TOOLS, PHOTOASSIST_LABELS, PHOTOASSIST_HANDLERS), (GRAPHIC_TOOLS, GRAPHIC_LABELS, GRAPHIC_HANDLERS), (ARTISTMGR_TOOLS, ARTISTMGR_LABELS, ARTISTMGR_HANDLERS), (KITAB_TOOLS, KITAB_LABELS, KITAB_HANDLERS), (PODCAST_TOOLS, PODCAST_LABELS, PODCAST_HANDLERS), (INFLUENCER_TOOLS, INFLUENCER_LABELS, INFLUENCER_HANDLERS)):
    _seen = {t["name"] for t in TOOLS}
    TOOLS.extend(t for t in _t if t["name"] not in _seen)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)

# v0.186 Lamba kaam pakka: the brain's own plan tool (goal mode lives in agent/goal.py)
from .goal_tools import GOAL_HANDLERS, GOAL_LABELS, GOAL_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in GOAL_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(GOAL_LABELS)
HANDLERS.update(GOAL_HANDLERS)

# v0.193 HARNESS-3: the agent team (deploy_agents / agent_status) + the session_log reader - the brain can now
# deploy SEVERAL agents that work in parallel and hand it their deliverables (agent/team.py; depth 1 enforced
# there by never handing these tools to a sub-agent)
from .team import TEAM_HANDLERS, TEAM_LABELS, TEAM_TOOLS  # noqa: E402

_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in TEAM_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(TEAM_LABELS)
HANDLERS.update(TEAM_HANDLERS)


# ---------------------------------------------------------------- v0.187 schema diet
# 384 tool specs measured ~568 KB (~142 K tokens) and EVERY one of the up-to-24 model calls of a turn re-sent
# all of it: on the production brain (no prompt cache) that alone put 15-60 s of dead air before the first word.
# The diet keeps every tool NAME, every type, every enum, every required field and every nested structure -
# only the prose shrinks, with graduated caps: a tool description keeps its first sentence(s); tools whose
# prose IS the safety rule (confirm cards, approvals, consent, money, OTP) get a much higher cap so their
# safety sentences survive; a property description becomes one short line. Names are untouched, so dispatch(),
# TOOL_LABELS and every handler keep working exactly as before.
DIET_DESC_MAX = 140      # tool description cap (chars) for ordinary tools
DIET_SAFETY_MAX = 700    # tool description cap for safety-word tools (their rules must survive)
DIET_PROP_MAX = 72       # property / nested description cap
_DIET_KEEP_RE = re.compile(r"confirm|approval|consent|otp|password|tier-2|bhejo|manzoori|payment|money", re.I)

_RAW_SPECS: list[dict] = [dict(t) for t in TOOLS]     # kept for tests / size stats only (never sent anywhere)
DIET_STATS: dict[str, int] = {"raw_chars": 0, "diet_chars": 0, "kept_full": 0}


def _first_sentences(text: str, cap: int) -> str:
    t = " ".join(str(text or "").split())
    if len(t) <= cap:
        return t
    cut = t[:cap]
    dot = max(cut.rfind(". "), cut.rfind("। "))
    if dot >= cap // 2:
        return cut[:dot + 1]
    sp = cut.rfind(" ")
    return ((cut[:sp] if sp >= cap // 2 else cut).rstrip(" ,;:")) + "…"


def _diet_schema(node: object, depth: int = 0) -> object:
    """Trim only `description` strings inside a JSON schema; types / enums / required / structure untouched."""
    if depth > 10:
        return node
    if isinstance(node, list):
        return [_diet_schema(x, depth + 1) for x in node]
    if isinstance(node, dict):
        out: dict = {}
        for k, v in node.items():
            if k == "description" and isinstance(v, str):
                out[k] = _first_sentences(v, DIET_PROP_MAX)
            else:
                out[k] = _diet_schema(v, depth + 1)
        return out
    return node


def diet_tool_specs(specs: list[dict]) -> list[dict]:
    out: list[dict] = []
    for t in specs:
        if not isinstance(t, dict) or not t.get("name"):
            out.append(t)
            continue
        desc = " ".join(str(t.get("description") or "").split())
        cap = DIET_SAFETY_MAX if _DIET_KEEP_RE.search(desc) else DIET_DESC_MAX
        if len(desc) <= cap:
            if len(desc) > DIET_DESC_MAX:
                DIET_STATS["kept_full"] += 1
            out.append(t)
            continue
        d = dict(t)
        d["description"] = _first_sentences(desc, cap)
        if isinstance(t.get("input_schema"), dict):
            d["input_schema"] = _diet_schema(t["input_schema"])
        out.append(d)
    return out


def _diet_size(specs: list[dict]) -> int:
    import json as _json
    return sum(len(_json.dumps(t, ensure_ascii=False)) for t in specs)


DIET_STATS["raw_chars"] = _diet_size(_RAW_SPECS)
TOOLS[:] = diet_tool_specs(TOOLS)
DIET_STATS["diet_chars"] = _diet_size(TOOLS)


# ---------------------------------------------------------------- v0.191 tool families (step-admitted subsets)
# Every family list merged above (LIFE_TOOLS, WEB_TOOLS, EMAIL_TOOLS, ...) is still in this module's namespace, so
# the name -> family map is built here in one pass. Tools that arrived outside a named family (the campaign/base
# specs at the top, the goal tools) are unmapped and are treated as CORE by agent/admit.py - the small always-on set.
FAMILY_OF: dict[str, str] = {}

for _n, _v in list(globals().items()):
    if _n.endswith("_TOOLS") and isinstance(_v, list):
        _fam = _n[:-6].lower()                    # LIFE_TOOLS -> "life"
        for _t in _v:
            if isinstance(_t, dict) and _t.get("name"):
                FAMILY_OF.setdefault(_t["name"], _fam)


