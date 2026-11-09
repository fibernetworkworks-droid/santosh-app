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
        "approve only by tapping the card in the app; voice can never approve them - say so plainly. A bare 'yes' / 'haan' that answers the question or offer in "
        "YOUR OWN last reply ('Want me to make a PDF report?') is NOT this tool's job: do what you offered."),
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


_SEND_YES = re.compile(r"\b(haan|han|ha|haa|yes|yep|ok|okay|theek|thik|bhej\s*d[oeiy]|bhejo|bhejiye|send|go\s+ahead|kar\s*do"
                       r"|chalu\s*kar|start\s+(?:it|the)|sabko\s+bhej|bhej\s*den?a)\b", re.I)
_SEND_NO = re.compile(r"\b(nahi|nahin|mat|ruko|wait|no|don'?t|cancel|baad\s*mein)\b", re.I)


def _she_said_send(ctx: Ctx) -> bool:
    """Wave 9: a bulk WhatsApp send starts only when HER words in THIS turn say send - never a routine, a wake report or
    the model reading an older 'haan'. Otherwise the campaign waits as a card ("Haan, bhej do" on her phone)."""
    actor = getattr(ctx, "actor", "owner") or "owner"
    if not (actor == "owner" or actor.startswith("approved:")):
        return False
    try:
        from .santosh import ASK_NOW
        words = ASK_NOW.get() or ""
    except Exception:   # noqa: BLE001
        return False
    return bool(_SEND_YES.search(words)) and not _SEND_NO.search(words)


WAIT_FOR_HER = ("The campaign is READY but NOT sent: her own words in this turn did not say send. Show her the message "
                "text and how many people it goes to, and ask 'Bhej doon?'. It sends only when she says haan / bhej do "
                "herself, or taps 'Haan, bhej do' on the campaign card. Never say it was sent.")


async def create_campaign(ctx: Ctx, title, lead_list_id, template_id, param_mapping, consent_confirmed, auto_send, **_):
    if auto_send and not _she_said_send(ctx):
        auto_send = False
    try:
        v = camp.create_campaign(tenant_id=ctx.tenant_id, conversation_id=ctx.conversation_id, title=title,
                                 lead_list_id=lead_list_id, template_id=template_id, param_mapping=param_mapping,
                                 consent_confirmed=bool(consent_confirmed), auto_send=bool(auto_send),
                                 live_mode=not get_settings().wa_dry_run)
    except camp.CampaignError as e:
        raise ToolError(str(e))
    v["daily_limit"] = get_settings().max_daily_sends
    if not auto_send:
        v["not_sent"] = WAIT_FOR_HER
    return v


async def confirm_send(ctx: Ctx, campaign_id, **_):
    if not _she_said_send(ctx):
        v = camp.campaign_view(campaign_id)
        v["not_sent"] = WAIT_FOR_HER
        return v
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

from .reach_tools import REACH_HANDLERS, REACH_LABELS, REACH_TOOLS  # noqa: E402  v0.559 REACH MANCH - the Agent-Reach discipline layer (envelope, ordered backends, health, status)

TOOLS.extend(REACH_TOOLS)
TOOL_LABELS.update(REACH_LABELS)
HANDLERS.update(REACH_HANDLERS)

from .speckit_tools import SPECKIT_HANDLERS, SPECKIT_LABELS, SPECKIT_TOOLS  # noqa: E402  v0.560 SPEC SUTRA - the spec-driven ladder (constitution/specify/clarify/plan/tasks/analyze/converge, the spec-kit idea)

TOOLS.extend(SPECKIT_TOOLS)
TOOL_LABELS.update(SPECKIT_LABELS)
HANDLERS.update(SPECKIT_HANDLERS)

from .sandarbh_tools import (  # noqa: E402  v0.586 SANDARBH MANCH - the T1 reference family (modelcontextprotocol/servers, MIT, IDEA-ONLY): the confined tenant workspace (the filesystem role) + the knowledge-graph memory (the memory role), backend-only
    KGMEMORY_HANDLERS, KGMEMORY_LABELS, KGMEMORY_TOOLS,
    WORKSPACE_HANDLERS, WORKSPACE_LABELS, WORKSPACE_TOOLS,
)

TOOLS.extend(WORKSPACE_TOOLS)
TOOL_LABELS.update(WORKSPACE_LABELS)
HANDLERS.update(WORKSPACE_HANDLERS)
TOOLS.extend(KGMEMORY_TOOLS)
TOOL_LABELS.update(KGMEMORY_LABELS)
HANDLERS.update(KGMEMORY_HANDLERS)

from .bhandar_tools import (  # noqa: E402  v0.618 BHANDAR MANCH - the T2 local-core family (the no-credential local beds of download/HOOLA_MCP_FEED.json, IDEA-ONLY): read-only SQL over the tenant's own SQLite, markdown/json/AST workbenches + IANA time, backend-only
    BHANDAR_HANDLERS, BHANDAR_LABELS, BHANDAR_TOOLS,
)

TOOLS.extend(BHANDAR_TOOLS)
TOOL_LABELS.update(BHANDAR_LABELS)
HANDLERS.update(BHANDAR_HANDLERS)

from .jharokha_tools import (  # noqa: E402  v0.665 JHAROKHA MANCH - the T3 local-browser family (the no-credential browser rows of download/HOOLA_MCP_FEED.json, IDEA-ONLY): the agent's OWN headless Chromium driven one deterministic action at a time - open/snapshot/click/type/press/console/tabs/screenshot/close through accessibility-style refs, backend-only
    JHAROKHA_HANDLERS, JHAROKHA_LABELS, JHAROKHA_TOOLS,
)

TOOLS.extend(JHAROKHA_TOOLS)
TOOL_LABELS.update(JHAROKHA_LABELS)
HANDLERS.update(JHAROKHA_HANDLERS)

from .duniya_tools import (  # noqa: E402  v0.667 DUNIYA MANCH - the T4 keyless-public-web family (the no-login / no-key public-web rows of download/HOOLA_MCP_FEED.json, IDEA-ONLY): ONE GET-only lane over the famous no-key services - fetch (the mcp/servers fetch reference idea) + wikipedia / weather / hn / currency / dictionary / arxiv / status, every free url SSRF-guarded, backend-only
    DUNIYA_HANDLERS, DUNIYA_LABELS, DUNIYA_TOOLS,
)

TOOLS.extend(DUNIYA_TOOLS)
TOOL_LABELS.update(DUNIYA_LABELS)
HANDLERS.update(DUNIYA_HANDLERS)

from .kala_tools import (  # noqa: E402  v0.681 KALA MANCH - the T5 knowledge-skill catalog family (github.com/google/skills, Apache-2.0, fork-and-remix sanctioned, IDEA-ONLY): ONE GET-only door over Google's public skill catalog - catalog (index.json byte-exact behind a TTL cache, regex-narrowed) + read / references (SKILL.md documents fetched fresh on demand, NEVER executed) + list / status, every url behind the house SSRF guard AND a one-host allowlist, backend-only
    KALA_HANDLERS, KALA_LABELS, KALA_TOOLS,
)

TOOLS.extend(KALA_TOOLS)
TOOL_LABELS.update(KALA_LABELS)
HANDLERS.update(KALA_HANDLERS)

from .shilp_tools import (  # noqa: E402  v0.730 SHILP MANCH - the ArtCraft generation lane (their Omni API, api.storyteller.ai, BYOK): ONE door over their documented surface - video / image generation (job tokens, credits spent on her explicit ask) + job / jobs status polling + status / models (zero network), the key in the VPS .env only, reference urls behind the lane's own wall (http(s), no credentials, no private hosts), idempotency minted here, 402 PAYMENT final
    SHILP_HANDLERS, SHILP_LABELS, SHILP_TOOLS,
)

TOOLS.extend(SHILP_TOOLS)
TOOL_LABELS.update(SHILP_LABELS)
HANDLERS.update(SHILP_HANDLERS)

from .scrape_tools import SCRAPE_HANDLERS, SCRAPE_LABELS, SCRAPE_TOOLS  # noqa: E402  v0.474 Scrapling

TOOLS.extend(SCRAPE_TOOLS)
TOOL_LABELS.update(SCRAPE_LABELS)
HANDLERS.update(SCRAPE_HANDLERS)

from .crawl_jobs import CRAWL_HANDLERS, CRAWL_LABELS, CRAWL_TOOLS  # noqa: E402  v0.486 background crawl lane

TOOLS.extend(CRAWL_TOOLS)
TOOL_LABELS.update(CRAWL_LABELS)
HANDLERS.update(CRAWL_HANDLERS)

from .dhara_tools import DHARA_HANDLERS, DHARA_LABELS, DHARA_TOOLS  # noqa: E402  v0.502 DHARA - her workflows (the n8n lane)

TOOLS.extend(DHARA_TOOLS)
TOOL_LABELS.update(DHARA_LABELS)
HANDLERS.update(DHARA_HANDLERS)

from .finguard_tools import FINGUARD_HANDLERS, FINGUARD_LABELS, FINGUARD_TOOLS  # noqa: E402  v0.585 Paisa Sahayak (consumer finance protection)

TOOLS.extend(FINGUARD_TOOLS)
TOOL_LABELS.update(FINGUARD_LABELS)
HANDLERS.update(FINGUARD_HANDLERS)

from .finops_tools import FINOPS_HANDLERS, FINOPS_LABELS, FINOPS_TOOLS  # noqa: E402  v0.602 Vitt Sahayak (finance desk assists, Wave 2)

TOOLS.extend(FINOPS_TOOLS)
TOOL_LABELS.update(FINOPS_LABELS)
HANDLERS.update(FINOPS_HANDLERS)

from .riskdesk_tools import RISKDESK_HANDLERS, RISKDESK_LABELS, RISKDESK_TOOLS  # noqa: E402  v0.603 Risk Desk (markets and credit papers, Wave 3)

TOOLS.extend(RISKDESK_TOOLS)
TOOL_LABELS.update(RISKDESK_LABELS)
HANDLERS.update(RISKDESK_HANDLERS)

from .retaildesk_tools import RETAILDESK_HANDLERS, RETAILDESK_LABELS, RETAILDESK_TOOLS  # noqa: E402  v0.604 Dukaan Desk (retail Wave 1)

TOOLS.extend(RETAILDESK_TOOLS)
TOOL_LABELS.update(RETAILDESK_LABELS)
HANDLERS.update(RETAILDESK_HANDLERS)

from .retailgrowth_tools import RETAILGROWTH_HANDLERS, RETAILGROWTH_LABELS, RETAILGROWTH_TOOLS  # noqa: E402  v0.607 Retail Growth (retail Wave 2)

TOOLS.extend(RETAILGROWTH_TOOLS)
TOOL_LABELS.update(RETAILGROWTH_LABELS)
HANDLERS.update(RETAILGROWTH_HANDLERS)

from .retailtrust_tools import RETAILTRUST_HANDLERS, RETAILTRUST_LABELS, RETAILTRUST_TOOLS  # noqa: E402  v0.607 Retail Trust (retail Wave 3)

TOOLS.extend(RETAILTRUST_TOOLS)
TOOL_LABELS.update(RETAILTRUST_LABELS)
HANDLERS.update(RETAILTRUST_HANDLERS)

from .bimadesk_tools import BIMADESK_HANDLERS, BIMADESK_LABELS, BIMADESK_TOOLS  # noqa: E402  v0.609 Bima Desk (health-insurance Wave 1)

TOOLS.extend(BIMADESK_TOOLS)
TOOL_LABELS.update(BIMADESK_LABELS)
HANDLERS.update(BIMADESK_HANDLERS)

from .bimaassist_tools import BIMAASSIST_HANDLERS, BIMAASSIST_LABELS, BIMAASSIST_TOOLS  # noqa: E402  v0.610 Bima Assist (health-insurance Wave 2)

TOOLS.extend(BIMAASSIST_TOOLS)
TOOL_LABELS.update(BIMAASSIST_LABELS)
HANDLERS.update(BIMAASSIST_HANDLERS)

from .bimarisk_tools import BIMARISK_HANDLERS, BIMARISK_LABELS, BIMARISK_TOOLS  # noqa: E402  v0.611 Bima Risk (health-insurance Wave 3)

TOOLS.extend(BIMARISK_TOOLS)
TOOL_LABELS.update(BIMARISK_LABELS)
HANDLERS.update(BIMARISK_HANDLERS)

from .kaan_tools import KAAN_HANDLERS, KAAN_LABELS, KAAN_TOOLS  # noqa: E402  v0.589 KAAN PACK - WhisperAI Wave W0 (transcription core)

TOOLS.extend(KAAN_TOOLS)
TOOL_LABELS.update(KAAN_LABELS)
HANDLERS.update(KAAN_HANDLERS)

from .officehours_tools import OFFICEHOURS_HANDLERS, OFFICEHOURS_LABELS, OFFICEHOURS_TOOLS  # noqa: E402  v0.495 office hours (the gstack THINK/PLAN lane)

TOOLS.extend(OFFICEHOURS_TOOLS)
TOOL_LABELS.update(OFFICEHOURS_LABELS)
HANDLERS.update(OFFICEHOURS_HANDLERS)

from .graph_tools import GRAPH_HANDLERS, GRAPH_LABELS, GRAPH_TOOLS  # noqa: E402  v0.496 Graphify code graph

TOOLS.extend(GRAPH_TOOLS)
TOOL_LABELS.update(GRAPH_LABELS)
HANDLERS.update(GRAPH_HANDLERS)

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
from .create_tools import CREATE_HANDLERS, CREATE_LABELS, CREATE_TOOLS  # noqa: E402
from .appcheck_tools import APPCHECK_HANDLERS, APPCHECK_LABELS, APPCHECK_TOOLS  # noqa: E402
from .rea_tools import REA_HANDLERS, REA_LABELS, REA_TOOLS  # noqa: E402
from .frames_tools import FRAMES_HANDLERS, FRAMES_LABELS, FRAMES_TOOLS  # noqa: E402
from .hoola_tools import HOOLA_HANDLERS, HOOLA_LABELS, HOOLA_TOOLS  # noqa: E402
from .webclone_tools import WEBCLONE_HANDLERS, WEBCLONE_LABELS, WEBCLONE_TOOLS  # noqa: E402

# Google Sheets and Google Drive have their own full toolsets now (per-user sign-in, service account as fallback);
# the old service-account tools with the same names step aside
_new = set(SHEETS_HANDLERS) | set(DRIVE_HANDLERS)
TOOLS.extend([t for t in GDRIVE_TOOLS if t["name"] not in _new])
TOOL_LABELS.update({k: v for k, v in GDRIVE_LABELS.items() if k not in _new})
HANDLERS.update({k: v for k, v in GDRIVE_HANDLERS.items() if k not in _new})
for _t, _l, _h in ((SHEETS_TOOLS, SHEETS_LABELS, SHEETS_HANDLERS), (DRIVE_TOOLS, DRIVE_LABELS, DRIVE_HANDLERS),
                   (FORMS_TOOLS, FORMS_LABELS, FORMS_HANDLERS), (SLIDES_TOOLS, SLIDES_LABELS, SLIDES_HANDLERS),
                   (PHOTOS_TOOLS, PHOTOS_LABELS, PHOTOS_HANDLERS), (NOTEBOOK_TOOLS, NOTEBOOK_LABELS, NOTEBOOK_HANDLERS),
                   (YOUTUBE_TOOLS, YOUTUBE_LABELS, YOUTUBE_HANDLERS), (PHOTO_TOOLS, PHOTO_LABELS, PHOTO_HANDLERS), (CREATE_TOOLS, CREATE_LABELS, CREATE_HANDLERS), (APPCHECK_TOOLS, APPCHECK_LABELS, APPCHECK_HANDLERS),
                   (REA_TOOLS, REA_LABELS, REA_HANDLERS), (FRAMES_TOOLS, FRAMES_LABELS, FRAMES_HANDLERS), (HOOLA_TOOLS, HOOLA_LABELS, HOOLA_HANDLERS), (WEBCLONE_TOOLS, WEBCLONE_LABELS, WEBCLONE_HANDLERS)):
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

# v0.277 INDIAMART: live B2B products / prices / suppliers from IndiaMART's own MCP server (read-only)
from .indiamart_tools import INDIAMART_HANDLERS, INDIAMART_LABELS, INDIAMART_TOOLS  # noqa: E402

TOOLS.extend(INDIAMART_TOOLS)
TOOL_LABELS.update(INDIAMART_LABELS)
HANDLERS.update(INDIAMART_HANDLERS)

# v0.348 MOSPI BUILT IN: official Government of India statistics (MoSPI eSankhyiki MCP, no login, read-only)
from .mospi_tools import MOSPI_HANDLERS, MOSPI_LABELS, MOSPI_TOOLS  # noqa: E402

TOOLS.extend(MOSPI_TOOLS)
TOOL_LABELS.update(MOSPI_LABELS)
HANDLERS.update(MOSPI_HANDLERS)

# v0.473 R2 APNA ENGINE: Hoola's own research engine (plan -> parallel workers that READ pages -> re-plan or stop -> a dossier)
from .research_tools import RESEARCH_HANDLERS, RESEARCH_LABELS, RESEARCH_TOOLS  # noqa: E402

TOOLS.extend(RESEARCH_TOOLS)
TOOL_LABELS.update(RESEARCH_LABELS)
HANDLERS.update(RESEARCH_HANDLERS)

# v0.381 GAME DESK: the Game Developer employee (Godot 4 games, built + test-played in a locked box)
from .gamedesk_tools import GAMEDESK_HANDLERS, GAMEDESK_LABELS, GAMEDESK_TOOLS  # noqa: E402

TOOLS.extend(GAMEDESK_TOOLS)
TOOL_LABELS.update(GAMEDESK_LABELS)
HANDLERS.update(GAMEDESK_HANDLERS)

# v0.410 ARCHITECTURE DESK: the Principal Software Architect employee (designs, ADRs, diagrams, PRs vs the design)
from .arch_tools import ARCH_HANDLERS, ARCH_LABELS, ARCH_TOOLS  # noqa: E402

TOOLS.extend(ARCH_TOOLS)
TOOL_LABELS.update(ARCH_LABELS)
HANDLERS.update(ARCH_HANDLERS)

# v0.63 seekhe hue kaam (procedures Hoola learned)
from .procedure_tools import PROCEDURE_HANDLERS, PROCEDURE_LABELS, PROCEDURE_TOOLS  # noqa: E402

TOOLS.extend(PROCEDURE_TOOLS)
TOOL_LABELS.update(PROCEDURE_LABELS)
HANDLERS.update(PROCEDURE_HANDLERS)

# v0.713 SEEKH MANCH: learn a way of working from a video (the bridge tool; the eyes and memories ship already)
from .seekh_tools import SEEKH_HANDLERS, SEEKH_LABELS, SEEKH_TOOLS  # noqa: E402

TOOLS.extend(SEEKH_TOOLS)
TOOL_LABELS.update(SEEKH_LABELS)
HANDLERS.update(SEEKH_HANDLERS)

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

# v0.512 Construction & Real Estate Wave 1 (register docs/research/building_industry/07 - the tier gate in
# construction/gates.py rides every tool: PREPARE, never CERTIFY; tier C refusals carry the human's name).
# Store (#61), Labour+wages+cess (#85/#87/#90), Customer money+handover+DLP (#92/#97/#98), Quality ITP/NCR/
# test lots + punch (#75/#76/#78), Meeting secretary (#67). Sitesup voice_log (#64/#70) and theka
# sub rate-basis + advances + wage calc (#62/#71) ride the existing tools; RA bills (#88) already lived.
from .const_store_tools import STORE_HANDLERS, STORE_LABELS, STORE_TOOLS  # noqa: E402
from .const_labour_tools import LABOUR_HANDLERS, LABOUR_LABELS, LABOUR_TOOLS  # noqa: E402
from .const_customer_tools import CUSTOMER_HANDLERS, CUSTOMER_LABELS, CUSTOMER_TOOLS  # noqa: E402
from .const_quality_tools import QUALITY_HANDLERS, QUALITY_LABELS, QUALITY_TOOLS  # noqa: E402
from .const_meet_tools import MEET_HANDLERS, MEET_LABELS, MEET_TOOLS  # noqa: E402

# v0.531 Construction Wave 2 (file-builders & checkers; plan docs/CONSTRUCTION_EMPLOYEE_PLAN.md C7-C10):
# Approvals office (#28-32,34,36), QS desk (#37-39,41,49), RERA & escrow (#35,93), Contracts (#44-46,51),
# Tendering (#52-56,58), Drawing QA + bye-law (#9,16,73). Every tool rides construction/gates.py:
# PREPARE, never CERTIFY - a named licensee on every output, the pack cites, the pack refuses when stale.
from .const_approvals_tools import APPROVALS_HANDLERS, APPROVALS_LABELS, APPROVALS_TOOLS  # noqa: E402
from .const_qs_tools import QS_HANDLERS, QS_LABELS, QS_TOOLS  # noqa: E402
from .const_rera_tools import RERA_HANDLERS, RERA_LABELS, RERA_TOOLS  # noqa: E402
from .const_contracts_tools import CONTRACTS_HANDLERS, CONTRACTS_LABELS, CONTRACTS_TOOLS  # noqa: E402
from .const_tender_tools import TENDER_HANDLERS, TENDER_LABELS, TENDER_TOOLS  # noqa: E402
from .const_drawqa_tools import DRAWQA_HANDLERS, DRAWQA_LABELS, DRAWQA_TOOLS  # noqa: E402

# v0.550 Construction Wave 3 (model-level & certificate-adjacent; plan §7 C11-C15): BIM/Information
# desk (#18-21 - IFC read / BCF write / IDS subset / CDE / clash / 4D-5D), Pre-design (#10-12 -
# load take-down, preliminary sizing, MEP estimates, fire rule checks), Survey & measurement
# (#22-24,26 - traverse, shoelace, volumes, deviations, RERA carpet), Delay working papers (#47),
# Green & performance (#104,110-118 - meters/ECBC/daylight/carbon/water/credits/Cx/T&C/M&V).
# #82 incident investigation rides const_quality. Same law: open formats said on the tin, a named
# licensee on every output, every rule row with clause + source, every number with its trail.
from .const_bim_tools import BIM_HANDLERS, BIM_LABELS, BIM_TOOLS  # noqa: E402
from .const_predesign_tools import PREDESIGN_HANDLERS, PREDESIGN_LABELS, PREDESIGN_TOOLS  # noqa: E402
from .const_survey_tools import SURVEY_HANDLERS, SURVEY_LABELS, SURVEY_TOOLS  # noqa: E402
from .const_delay_tools import DELAY_HANDLERS, DELAY_LABELS, DELAY_TOOLS  # noqa: E402
from .const_green_tools import GREEN_HANDLERS, GREEN_LABELS, GREEN_TOOLS  # noqa: E402
from .const_land_tools import LAND_HANDLERS, LAND_LABELS, LAND_TOOLS  # noqa: E402
from .const_plan_tools import PLAN_HANDLERS, PLAN_LABELS, PLAN_TOOLS  # noqa: E402
from .const_ehs_tools import EHS_HANDLERS, EHS_LABELS, EHS_TOOLS  # noqa: E402
# FINAL CHECK: imported under its OWN names - as STUDIO_* it overwrote the AI video studio's names, so video_studio
# lost its family (rode every turn) and "ai video" opened the construction shot-brief desk instead (the v0.559 trap again)
from .const_studio_tools import STUDIO_HANDLERS as CSTUDIO_HANDLERS, STUDIO_LABELS as CSTUDIO_LABELS  # noqa: E402
from .const_studio_tools import STUDIO_TOOLS as CSTUDIO_TOOLS  # noqa: E402
from .const_studio_tools import LEARN_HANDLERS, LEARN_LABELS, LEARN_TOOLS  # noqa: E402
from .const_fm_tools import FM_HANDLERS, FM_LABELS, FM_TOOLS  # noqa: E402

for _t, _l, _h in ((STORE_TOOLS, STORE_LABELS, STORE_HANDLERS), (LABOUR_TOOLS, LABOUR_LABELS, LABOUR_HANDLERS),
                   (CUSTOMER_TOOLS, CUSTOMER_LABELS, CUSTOMER_HANDLERS), (QUALITY_TOOLS, QUALITY_LABELS, QUALITY_HANDLERS),
                   (MEET_TOOLS, MEET_LABELS, MEET_HANDLERS),
                   (APPROVALS_TOOLS, APPROVALS_LABELS, APPROVALS_HANDLERS), (QS_TOOLS, QS_LABELS, QS_HANDLERS),
                   (RERA_TOOLS, RERA_LABELS, RERA_HANDLERS), (CONTRACTS_TOOLS, CONTRACTS_LABELS, CONTRACTS_HANDLERS),
                   (TENDER_TOOLS, TENDER_LABELS, TENDER_HANDLERS), (DRAWQA_TOOLS, DRAWQA_LABELS, DRAWQA_HANDLERS),
                   (BIM_TOOLS, BIM_LABELS, BIM_HANDLERS), (PREDESIGN_TOOLS, PREDESIGN_LABELS, PREDESIGN_HANDLERS),
                   (SURVEY_TOOLS, SURVEY_LABELS, SURVEY_HANDLERS), (DELAY_TOOLS, DELAY_LABELS, DELAY_HANDLERS),
                   (GREEN_TOOLS, GREEN_LABELS, GREEN_HANDLERS)):
    _seen = {t["name"] for t in TOOLS}
    TOOLS.extend(t for t in _t if t["name"] not in _seen)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)

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
# v0.357 Engineering Desk: the hired CAD Engineer (cad_part)
from .eng_tools import ENG_HANDLERS, ENG_LABELS, ENG_TOOLS  # noqa: E402

TOOLS.extend(ENG_TOOLS)
TOOL_LABELS.update(ENG_LABELS)
HANDLERS.update(ENG_HANDLERS)
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
from .enterprise_tools import ENTERPRISE_HANDLERS, ENTERPRISE_LABELS, ENTERPRISE_TOOLS  # noqa: E402

for _t, _l, _h in ((DEV_TOOLS, DEV_LABELS, DEV_HANDLERS), (QA_TOOLS, QA_LABELS, QA_HANDLERS),
                   (ITADMIN_TOOLS, ITADMIN_LABELS, ITADMIN_HANDLERS), (NOC_TOOLS, NOC_LABELS, NOC_HANDLERS),
                   (CYBER_TOOLS, CYBER_LABELS, CYBER_HANDLERS), (DEVOPS_TOOLS, DEVOPS_LABELS, DEVOPS_HANDLERS),
                   (DOCWRITER_TOOLS, DOCWRITER_LABELS, DOCWRITER_HANDLERS),
                   (APPREVIEW_TOOLS, APPREVIEW_LABELS, APPREVIEW_HANDLERS),
                   (PRODUCT_TOOLS, PRODUCT_LABELS, PRODUCT_HANDLERS),
                   # v0.358 Enterprise Systems & ERP: ten jobs, generated from enterprise/rules.ROLES
                   (ENTERPRISE_TOOLS, ENTERPRISE_LABELS, ENTERPRISE_HANDLERS)):
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
for _t, _l, _h in ((LAND_TOOLS, LAND_LABELS, LAND_HANDLERS), (PLAN_TOOLS, PLAN_LABELS, PLAN_HANDLERS),
                   (EHS_TOOLS, EHS_LABELS, EHS_HANDLERS), (CSTUDIO_TOOLS, CSTUDIO_LABELS, CSTUDIO_HANDLERS),
                   (LEARN_TOOLS, LEARN_LABELS, LEARN_HANDLERS), (FM_TOOLS, FM_LABELS, FM_HANDLERS)):
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
# v0.311 SAHI AUZAAR 2: the 140-char cut was the main reason Hoola picked the WRONG tool. It hit 291 of 430 tools and
# kept only "what it is" - the "use it when / not when / prefer this over X" sentences that tell neighbours apart were
# exactly what got cut (data_fetch lost "Prefer this over api_call / open_website / the cloud PC"; 150 descriptions
# ended mid-sentence). Anthropic's tool guidance: the description IS where tool choice is won. Full prose costs ~7.5 KB
# on an ordinary turn (35 -> 42.5 KB of specs); the cap below only stops a runaway description.
DIET_DESC_MAX = 1200     # tool description cap (chars) - v0.311: 140 -> 1200 (whole descriptions, sentence edge)
DIET_SAFETY_MAX = 1200   # tool description cap for safety-word tools (v0.311: the same - every rule survives)
DIET_PROP_MAX = 240      # property / nested description cap (v0.311: 72 -> 240, the format hints stay)
_DIET_KEEP_RE = re.compile(r"confirm|approval|consent|otp|password|tier-2|bhejo|manzoori|payment|money", re.I)

# v0.381 Shiksha suite Phase 0 + 1: the education foundation (classes, learners + guardian consent, the shared question
# bank, gradebook), the Pathyakram Sahayak (curriculum & exam designer) and the locked Python sandbox (pylab).
from .shiksha_tools import SHIKSHA_HANDLERS, SHIKSHA_LABELS, SHIKSHA_TOOLS  # noqa: E402
from .guru_tools import GURU_HANDLERS, GURU_LABELS, GURU_TOOLS  # noqa: E402  (Phase 2: personal tutor)
from .daftar_tools import DAFTAR_HANDLERS, DAFTAR_LABELS, DAFTAR_TOOLS  # noqa: E402  (Phase 3: school office)
from .shodh_tools import SHODH_HANDLERS, SHODH_LABELS, SHODH_TOOLS  # noqa: E402  (Phase 4: research assistant)
from .prayog_tools import PRAYOG_HANDLERS, PRAYOG_LABELS, PRAYOG_TOOLS  # noqa: E402  (v0.409 Prayogshala 3D labs)

for _t, _l, _h in ((SHIKSHA_TOOLS, SHIKSHA_LABELS, SHIKSHA_HANDLERS), (GURU_TOOLS, GURU_LABELS, GURU_HANDLERS),
                   (DAFTAR_TOOLS, DAFTAR_LABELS, DAFTAR_HANDLERS), (SHODH_TOOLS, SHODH_LABELS, SHODH_HANDLERS),
                   (PRAYOG_TOOLS, PRAYOG_LABELS, PRAYOG_HANDLERS)):
    _seen = {t["name"] for t in TOOLS}
    TOOLS.extend(t for t in _t if t["name"] not in _seen)
    TOOL_LABELS.update(_l)
    HANDLERS.update(_h)

# v0.463 ZOO: the BYOK model zoo (one Muapi gateway, 211 models, registry-driven, app/zoo.py + zoo_catalog.json).
# Purely ADDITIVE - the curated studios (video_studio / photo_banao / create_studio) keep their exact specs;
# the zoo only ADDS one tool for the models/styles they don't cover. Same refusals, same usage counting.
from .zoo_tools import ZOO_HANDLERS, ZOO_LABELS, ZOO_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in ZOO_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(ZOO_LABELS)
HANDLERS.update(ZOO_HANDLERS)
del _seen

# v0.477 HOOLA SELF-TEACH: ONE skill_manage tool (the coder/skills_tool surface) - Santosh can
# author and improve reusable skills mid-conversation; the coder nudge resets its counter on use.
from ..coder.skills_tool import SKILL_HANDLERS, SKILL_LABELS, SKILL_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in SKILL_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(SKILL_LABELS)
HANDLERS.update(SKILL_HANDLERS)
del _seen

# v0.486 HOOLA UIUX PRO MAX: ONE uiux_design tool (the coder/uiux_tool surface over the
# vendored MIT engine coder/uiux/) - the design database (79 styles, 192 palettes, 74 font
# pairings, 119 UX guidelines, 22 stacks) behind one local search; the seed skill
# uiux-pro-max.md teaches when, the tool is how. Zero network, zero brain calls.
from ..coder.uiux_tool import UIUX_HANDLERS, UIUX_LABELS, UIUX_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in UIUX_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(UIUX_LABELS)
HANDLERS.update(UIUX_HANDLERS)
del _seen

# v0.478 HOOLA SWARM: ONE delegate_task tool (the coder/delegate surface) - parallel bounded
# child agents; every child tool call rides _run_tool so capture sees the whole picture; the
# voice allowlist never admits it (a call routes it to a kaam job instead).
from ..coder.delegate import DELEGATE_HANDLERS, DELEGATE_LABELS, DELEGATE_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in DELEGATE_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(DELEGATE_LABELS)
HANDLERS.update(DELEGATE_HANDLERS)
del _seen

# v0.479 HOOLA SMART HOME: ghar ke devices Home Assistant ke official REST se - home_link /
# home_devices / home_on / home_off / home_state. Reads gate-free (link ke bina kabhi nahi
# chalte), controls `home_control` gate ke peeche (PC se alag). Locks confirm-only, routine
# turns se kabhi nahi; fridge/washer/geyser read-only; AC 20-28 °C; volume <= 90 %.
from .home_tools import HOME_HANDLERS, HOME_LABELS, HOME_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in HOME_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(HOME_LABELS)
HANDLERS.update(HOME_HANDLERS)
del _seen

# v0.486.0 BYOX SKILL PACK: Build-Your-Own-X — 31 categories, seed default on.
# byox_list / byox_guide / byox_plan admitted under the "byox" family.
from .byox_tools import BYOX_HANDLERS, BYOX_LABELS, BYOX_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in BYOX_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(BYOX_LABELS)
HANDLERS.update(BYOX_HANDLERS)
del _seen


# v0.501 HOOLA CONTEXT7: ONE docs7 tool (the coder/docs7 surface) - the upstash/context7 port:
# resolve a library NAME to its Context7 ID (/org/project), then pull up-to-date, version-
# specific docs into the turn. Every successful fetch lands in the vault as a docs7 observation
# (FTS5 -> search/primer/dedup/curator all see it); the vault answers repeats within the TTL
# with zero network; queries pass strip_private + redact_secrets BEFORE they leave the box;
# one attempt, drop-don't-wait (20 s ceiling); voice never sees it (the VOICE_TOOL_NAMES
# allowlist - a 20 s network stall has no place in a live call), coder_docs7 gates the handler.
from ..coder.docs7 import DOCS7_HANDLERS, DOCS7_LABELS, DOCS7_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in DOCS7_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(DOCS7_LABELS)
HANDLERS.update(DOCS7_HANDLERS)
del _seen

# v0.512 HOOLA 21ST: ONE magic21 tool (the coder/magic21 surface) - the 21st-dev/magic-mcp
# port: search the 21st.dev UI catalog, fetch a component's full code, generate new UI only
# when the account's entitlement says so (get_usage.aiGenerationEnabled; a result carrying
# ai_subscription_required STOPS - no retries through legacy aliases or the CLI). Five ops
# (list/usage/search/get/call) over the MCP wire (initialize -> initialized -> tools/call,
# the session echo honoured per turn, stateless between turns); the endpoint's NOT_AUTHED
# sentence rides verbatim; 401 latches for the process life (upstream saw ~100k doomed
# initialize retries an hour - src/index.ts:146-152); no key or latched auth answers locally
# with ZERO network; arguments pass strip_private + redact_secrets before egress; one attempt
# drop-don't-wait (20 s); per-tenant rolling-hour window; voice never sees it (the
# VOICE_TOOL_NAMES allowlist); coder_magic21 gates the handler (default OFF - bake, then flip).
from ..coder.magic21 import MAGIC21_HANDLERS, MAGIC21_LABELS, MAGIC21_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in MAGIC21_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(MAGIC21_LABELS)
HANDLERS.update(MAGIC21_HANDLERS)
del _seen

# v0.514 HOOLA CREW: ONE crew_run tool (the coder/crew_run surface) - the crewAIInc/crewAI
# port: a named team of role agents (role/goal/backstory) working a task list inside one
# turn - sequential with context threading or hierarchical (a manager with NO tools
# delegating via DELEGATE/ASK/FINISH lines), guardrails with bounded retries, async tasks
# joining before the next sync task. The library (app.crew: core/agent/task/crew/engine)
# is inert and provider-free - the RUNNER here is the house child worker (delegate.py's
# _call_brain + _run_tool funnel) framed by the identity, so capture/scrub/timeout see
# every crew worker like every other child. The deny set is structural: a crew member can
# NEVER delegate, send, approve or start PC jobs (delegate.CHILD_DENIED, money never moves
# inside a crew). Caps: 6 agents / 12 tasks / 180 s per task / 600 s whole-crew. Voice
# never sees it (out of the VOICE_TOOL_NAMES allowlist); coder_crew gates the handler
# (default OFF - bake, then flip). Stateless: the crew IS the tool call (v0.514).
from ..coder.crew_run import CREW_HANDLERS, CREW_LABELS, CREW_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in CREW_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(CREW_LABELS)
HANDLERS.update(CREW_HANDLERS)
del _seen

# v0.540.0 LEADS NEEV: the lead generation engine - five tools (leads_run / leads_status / leads_list /
# leads_export / leads_forget) over the run store, plan-time caps and the provenance gate. P0 runs L0 (her
# data) only; the engine gathers and NEVER contacts anyone - outreach stays behind her tap on the desks.
from .leads_tools import LEADS_HANDLERS, LEADS_LABELS, LEADS_TOOLS  # noqa: E402
_seen = {t["name"] for t in TOOLS}
TOOLS.extend(t for t in LEADS_TOOLS if t["name"] not in _seen)
TOOL_LABELS.update(LEADS_LABELS)
HANDLERS.update(LEADS_HANDLERS)
del _seen

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


def _diet_schema(node: object, depth: int = 0, prop_max: int | None = None) -> object:
    """Trim only `description` strings inside a JSON schema; types / enums / required / structure untouched."""
    pm = DIET_PROP_MAX if prop_max is None else prop_max
    if depth > 10:
        return node
    if isinstance(node, list):
        return [_diet_schema(x, depth + 1, pm) for x in node]
    if isinstance(node, dict):
        out: dict = {}
        for k, v in node.items():
            if k == "description" and isinstance(v, str):
                out[k] = _first_sentences(v, pm)
            else:
                out[k] = _diet_schema(v, depth + 1, pm)
        return out
    return node


def diet_tool_specs(specs: list[dict], desc_max: int | None = None, safety_max: int | None = None,
                    prop_max: int | None = None) -> list[dict]:
    dm = DIET_DESC_MAX if desc_max is None else desc_max
    sm = DIET_SAFETY_MAX if safety_max is None else safety_max
    out: list[dict] = []
    for t in specs:
        if not isinstance(t, dict) or not t.get("name"):
            out.append(t)
            continue
        desc = " ".join(str(t.get("description") or "").split())
        cap = sm if _DIET_KEEP_RE.search(desc) else dm
        if len(desc) <= cap:
            if len(desc) > dm:
                DIET_STATS["kept_full"] += 1
            out.append(t)
            continue
        d = dict(t)
        d["description"] = _first_sentences(desc, cap)
        if isinstance(t.get("input_schema"), dict):
            d["input_schema"] = _diet_schema(t["input_schema"], prop_max=prop_max)
        out.append(d)
    return out


def _diet_size(specs: list[dict]) -> int:
    import json as _json
    return sum(len(_json.dumps(t, ensure_ascii=False)) for t in specs)


DIET_STATS["raw_chars"] = _diet_size(_RAW_SPECS)
# v0.331 EK KAAM EK AUZAAR: where several tools can do the same job, each one's description now STARTS with its lane
# (use for / not for -> the neighbour). Anthropic: "If a human engineer can't definitively say which tool should be
# used, an AI agent can't be expected to do better." Renaming / merging the tools would touch every prompt, voice list
# and saved procedure, so the lanes are drawn in the descriptions instead - first, so no cap can ever cut them.
TOOL_LANES: dict[str, str] = {
    # wave 12: overlapping tools with no rule between them - the model picked at random
    "add_calendar_event": "LANE: an event on HER PHONE's own calendar (no Google sign-in needed). Her GOOGLE Calendar (shared, "
                          "invites, Meet link, seen on every device) -> calendar_add_event. Only a reminder to ring -> "
                          "create_reminder.",
    "calendar_add_event": "LANE: an event on her GOOGLE Calendar (invites, Meet link, every device). Google not connected or "
                          "she means the phone's own calendar -> add_calendar_event.",
    "scrape": "LANE: the DEFAULT way to read a public web page (it escalates past blocks by itself). One known link and a "
              "plain page -> open_website is fine; clicks / forms / login -> browse_web; many links of a site -> scrape_map; "
              "a search -> google_search.",
    "scrape_page": "LANE: one page's text when scrape is not needed (no block expected). The default reader is scrape.",
    "reach": "LANE: a page or a search with its sources and backend shown (the disciplined envelope) when you need to SAY "
             "where it came from. Plain reading -> scrape; a plain search -> google_search.",
    "kgmemory": "LANE: the knowledge GRAPH of people / companies and how they relate (who is whose supplier). A plain fact "
                "to keep -> remember; finding anything she told you -> yaad_khojo.",
    # v0.449 maps: a KIND of place -> maps_nearby; a NAMED place -> maps_search; one place's details -> maps_place
    "maps_search": "LANE: a place you can NAME ('Haldiram Nagpur', 'Akola station', a particular shop). A CATEGORY "
                   "near somewhere ('chemist', 'petrol pump', 'hardware shop') -> maps_nearby, which ranks by real "
                   "distance. Time / distance between two places -> maps_directions.",
    "maps_nearby": "LANE: what is AROUND a point, by category (pharmacy, bank, gas_station...). A place you can name "
                   "-> maps_search. Phone / website / rating / timings of one result -> maps_place. Circle only, "
                   "50 km max, 20 results, no next page.",
    "maps_nearest": "LANE: which of a LIST she already has is nearest by real road time (godowns, branches, workers vs "
                    "a customer). Finding places of a kind -> maps_nearby. One trip's route -> maps_directions.",
    "maps_address_check": "LANE: is THIS delivery address good (PIN, completeness, how far Google matched it). One address "
                          "per call. Finding places -> maps_nearby / maps_search. A point's address -> maps_pata.",
    "maps_pata": "LANE: lat/lng -> the address there (reverse geocode). Address -> check it with maps_address_check.",
    "maps_route_plan": "LANE: the ORDER to visit many stops in a day (time windows, capacity). Which ONE is nearest -> "
                       "maps_nearest. One trip's route -> maps_directions. Proposes only, assigns nothing.",
    "maps_links": "LANE: a Google Maps LINK (view / directions / Street View) to put in a PDF, WhatsApp message or bill. "
                  "Never a map picture. Route steps -> maps_directions; open navigation on her phone -> maps_navigate.",
    "gbp_locations": "LANE: HER OWN Google Business Profile listing(s) (her shop on Google Maps). Other places -> maps_search / "
                     "maps_nearby. How people found her -> gbp_numbers.",
    "gbp_numbers": "LANE: how many people saw / called / asked directions to HER business on Google. Not a competitor "
                   "or any other place.",
    "ownmap_import": "LANE: bring HER OWN My Maps export (KML/KMZ) or Takeout 'Saved' file into Hoola once. Not for finding "
                     "new places (maps_nearby / maps_search).",
    "ownmap_near": "LANE: which of HER OWN imported pins / areas are near somewhere. Other businesses -> maps_nearby. Her "
                   "Google listing -> gbp_locations.",
    "solar_check": "LANE: is rooftop SOLAR workable at one building (roof area, panels, sunshine, kWh). Not electricity "
                   "prices or payback maths (pylab).",
    "maps_snap": "LANE: clean a recorded GPS trail onto roads. Finding places / routes -> maps_nearby / maps_directions.",
    "maps_place": "LANE: phone, website, rating and opening hours of ONE place you already have a place_id for. "
                  "Finding places -> maps_nearby / maps_search. One at a time: these are the costly fields.",
    # web: answer -> quotes -> one page -> clicks -> forms
    "google_search": "LANE: quick facts that change (prices, news, timings) as a short answer. Need the sources' own "
                     "words -> web_sources; one known page -> open_website; clicking / logging in -> browse_web.",
    "web_sources": "LANE: the web's own QUOTED words with links (checking a claim, comparing sites, a rule you will "
                   "quote). A quick fact -> google_search; one known page -> open_website.",
    "open_website": "LANE: read ONE page whose link you have. No link -> google_search; the page needs clicks, a "
                    "search box or login -> browse_web; a data API -> data_fetch.",
    "browse_web": "LANE: a real browser for pages that need clicking, searching inside a site or several pages. "
                  "Reading one link -> open_website; filling a form / download / application for her -> "
                  "computer_operator.",
    "computer_operator": "LANE: do a JOB on a website for her (forms, applications, downloads, bookings, portal "
                         "updates). Only looking something up -> browse_web / open_website.",
    "api_call": "LANE: one small read from a public API. A list / many records to keep, sort or turn into a file -> "
                "data_fetch.",
    "data_fetch": "LANE: many records from an API (lists, top N, repos, prices) saved as a dataset for data_read / "
                  "doc_studio data=. One small read -> api_call. Never a PC for data.",
    # documents: which file maker
    "doc_studio": "LANE: every designed file for her - PDF / Word / Excel / PowerPoint reports, quotations, invoices, "
                  "proposals, decks. A plain quick file -> make_document; an interactive page -> artifact_make. "
                  "She gave the items / prices / names = make it now; a missing GST rate, address or number stays "
                  "blank (say so after) - never ask before the first draft.",
    "make_document": "LANE: a plain quick Office file (letter, simple list). Anything formal or designed (report, "
                     "quotation, invoice, proposal, deck) -> doc_studio.",
    "docs_writer": "LANE: technical docs for HER product (manuals, API reference, release notes). Any other "
                   "document -> doc_studio.",
    "hoola_make": "LANE: a file made FOR a connected person and sent on the Hoola Network. A file for her own chat -> "
                  "doc_studio.",
    "artifact_make": "LANE: the POLISH builder for a studio-quality page she asked to be polished. A page you can write "
                     "yourself -> artifact. A document to read or print -> doc_studio.",
    "artifact": "LANE: a page / dashboard / chart / tracker / diagram you write yourself, edited in place with "
                "update old_str -> new_str. A polished / studio-quality page she asked for -> artifact_make; a "
                "document to read or print -> doc_studio.",
    "notebook_make": "LANE: a quick item made FROM her notebook's sources (summary, FAQ, timeline). A designed file -> "
                     "doc_studio.",
    # memory: what to search
    "remember": "LANE: SAVE one fact she asked you to keep. Finding a fact -> memory_search.",
    "memory_search": "LANE: find a FACT she asked you to remember. What was said in her chats / calls / jobs -> "
                     "yaad_khojo; her own files and documents -> gyaan_khojo; chats by date ('kal', 'is hafte') -> "
                     "haal_ki_chats.",
    "yaad_khojo": "LANE: the ONE memory door - facts, past chats / calls / jobs, work notes, her graph and page in one "
                  "search. Her documents' contents -> gyaan_khojo; by date -> haal_ki_chats.",
    "gyaan_khojo": "LANE: search inside HER files and documents (Gyaan, Drive folders). A file she attached in this "
                   "chat -> file_read; her chats -> yaad_khojo.",
    "haal_ki_chats": "LANE: her other chats by DATE ('aaj', 'kal', 'is hafte'). By topic -> yaad_khojo.",
    "file_read": "LANE: read a file she attached (file_id). The layout / pages of a document -> doc_preview; her "
                 "stored files by topic -> gyaan_khojo.",
}
for _t in TOOLS:
    _lane = TOOL_LANES.get(_t.get("name", ""))
    if _lane and not str(_t.get("description") or "").startswith("LANE:"):
        _t["description"] = _lane + " " + str(_t.get("description") or "")

TOOLS[:] = diet_tool_specs(TOOLS)
DIET_STATS["diet_chars"] = _diet_size(TOOLS)
# v0.313 the VOICE CALL keeps the short v0.187 form: Gemini Live re-reads every declared tool on each call and its
# VOICE_TOOL_BUDGET was sized on it (a call picks among few everyday tools; big work goes to santosh_kaam anyway)
VOICE_DESC_MAX, VOICE_SAFETY_MAX, VOICE_PROP_MAX = 140, 700, 72
VOICE_SPECS: list[dict] = diet_tool_specs(_RAW_SPECS, VOICE_DESC_MAX, VOICE_SAFETY_MAX, VOICE_PROP_MAX)


# ---------------------------------------------------------------- v0.191 tool families (step-admitted subsets)
# Every family list merged above (LIFE_TOOLS, WEB_TOOLS, EMAIL_TOOLS, ...) is still in this module's namespace, so
# the name -> family map is built here in one pass. Tools that arrived outside a named family (the campaign/base
# specs at the top, the goal tools) are unmapped and are treated as CORE by agent/admit.py - the small always-on set.
FAMILY_OF: dict[str, str] = {}

# v0.311 SAHI AUZAAR 2: the 9 WhatsApp-campaign specs at the top had no family, so they rode on EVERY turn ("hello"
# included) - noise next to the tool she really needed. They are the "campaign" family now: her campaign words, or a
# chat that already has a campaign / lead list (admit.sticky_families), bring them in.
CAMPAIGN_NAMES = ("list_lead_lists", "get_lead_list", "check_template", "submit_template", "check_template_status",
                  "create_campaign", "confirm_send", "get_campaign_status", "control_campaign")
for _n in CAMPAIGN_NAMES:
    FAMILY_OF[_n] = "campaign"

for _n, _v in list(globals().items()):
    if _n.endswith("_TOOLS") and isinstance(_v, list):
        _fam = _n[:-6].lower()                    # LIFE_TOOLS -> "life"
        for _t in _v:
            if isinstance(_t, dict) and _t.get("name"):
                FAMILY_OF.setdefault(_t["name"], _fam)

# v0.559 SAHI GINTI: two modules both export CONTRACTS_TOOLS, so the construction pair (const_contracts /
# const_contracts_dekho) lost its family to the later import and rode on EVERY turn, "namaste" included.
from . import const_contracts_tools as _cct   # noqa: E402
for _t in _cct.CONTRACTS_TOOLS:
    FAMILY_OF.setdefault(_t["name"], "contracts")


