"""Motion designer desk tools. `motion_desk_dekho` only reads; `motion_desk` does the work on top of Hoola Motion / 3D Studio /
Brand / photogen. The storyboard going to the client, final delivery, invoices, a paid extra revision round and any client message
become CARDS here; only HER tap in the app (API) decides them. Hoola never invents a price / date / fact, never sends anything by
itself and never takes or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "client", "asset", "job", "update", "storyboard", "frames", "storyboard_send", "client_ok", "render",
            "feedback", "revise", "extra_round", "use_asset", "template", "final", "invoice", "paid", "message", "cancel",
            "forget_client"]
_OWNER_ONLY = {"settings", "client_ok", "paid", "cancel", "forget_client"}

MOTIONDESK_TOOLS = [
    {"name": "motion_desk", "description": (
        "Motion designer studio desk (clients, brand kits, job tickets, storyboard, renders on Hoola Motion / 3D / Brand / photo, "
        "revision rounds, licences, handover, invoices). NEVER invent prices, dates, phone numbers or facts. Cards = only her tap "
        "decides: say 'aapki haan ka card bheja hai', never 'sent'. action=settings*: studio, gstin, upi_id, gst_pct, sac, rounds, "
        "round_fee, advance_pct, pay_days, rights licence|assign, rights_years, rights_territory, terms. action=client: name or "
        "client (to update), contact, phone, email, gstin, state, kit {colors {primary,secondary,accent,dark,light}, fonts "
        "[{name,source,licence,ref}], tone, tagline, dos, donts}. action=asset: name, kind font|music|sfx|stock_video|stock_image|"
        "template|3d_model|plugin|other, source (google_fonts, adobe_fonts, envato, artlist, epidemic, pixabay, own, client...), "
        "licence, licence_ref, credit, valid_until. action=job: client, title, brief (client words = data), engine "
        "motion|blender3d|brand|photo, kind explainer|recipe|logo|offer|custom, deliverables [insta_reel|insta_post|insta_story|"
        "yt_short|youtube|fb_reel|whatsapp_status|square|linkedin|presentation|tv_ooh|gif], deadline, quote [{text,qty,rate}] "
        "(her prices only), template. action=update: job + fields. action=storyboard: job, seconds. action=frames: job, frames. "
        "action=storyboard_send / final / invoice (bill advance|final|extra) / extra_round / message (text): job -> CARD. "
        "action=client_ok*: job, by (records the client's yes). action=render: job (force_reason* if storyboard not approved). "
        "action=feedback: job, text (timecoded client notes). action=revise: job, data, free_reason*. action=use_asset: job, asset. "
        "action=template: job, name. action=paid*: invoice, amount, ref. action=cancel*: job, reason. action=forget_client*: client. "
        "* = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS},
         "job": {"type": "string"}, "client": {"type": "string"}, "name": {"type": "string"}, "title": {"type": "string"},
         "brief": {"type": "string"}, "engine": {"type": "string"}, "kind": {"type": "string"},
         "deliverables": {"type": "array", "items": {"type": "string"}}, "deadline": {"type": "string"},
         "quote": {"type": "array", "items": {"type": "object"}}, "template": {"type": "string"}, "data": {"type": "object"},
         "frames": {"type": "array", "items": {"type": "object"}}, "seconds": {"type": "number"}, "text": {"type": "string"},
         "by": {"type": "string"}, "force_reason": {"type": "string"}, "free_reason": {"type": "string"}, "asset": {"type": "string"},
         "bill": {"type": "string"}, "invoice": {"type": "string"}, "amount": {"type": "number"}, "ref": {"type": "string"},
         "reason": {"type": "string"}, "contact": {"type": "string"}, "phone": {"type": "string"}, "email": {"type": "string"},
         "gstin": {"type": "string"}, "state": {"type": "string"}, "kit": {"type": "object"}, "notes": {"type": "string"},
         "source": {"type": "string"}, "licence": {"type": "string"}, "licence_ref": {"type": "string"}, "credit": {"type": "string"},
         "valid_until": {"type": "string"}, "studio": {"type": "string"}, "upi_id": {"type": "string"}, "gst_pct": {"type": "number"},
         "sac": {"type": "string"}, "rounds": {"type": "integer"}, "round_fee": {"type": "number"}, "advance_pct": {"type": "number"},
         "pay_days": {"type": "integer"}, "rights": {"type": "string"}, "rights_years": {"type": "integer"},
         "rights_territory": {"type": "string"}, "terms": {"type": "string"}, "address": {"type": "string"},
         "morning_time": {"type": "string"}, "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "motion_desk_dekho", "description": (
        "Read the motion design studio (nothing changes). what=day (deadlines, review ready, unpaid bills, licences ending, cards "
        "waiting) | jobs (status, client) | job (job: storyboard, renders, notes, rounds, invoices) | clients | assets (licence "
        "register) | templates | cards | platforms (deliverable specs) | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "jobs", "job", "clients", "assets", "templates", "cards", "platforms", "settings"]},
         "job": {"type": "string"}, "status": {"type": "string"}, "client": {"type": "string"}},
         "required": ["what"]}},
]

MOTIONDESK_LABELS = {"motion_desk": "Motion design studio ka kaam kar raha hoon", "motion_desk_dekho": "Studio ke kaam dekh raha hoon"}

_SET_KEYS = ("studio", "gstin", "address", "phone", "email", "upi_id", "gst_pct", "sac", "rounds", "round_fee", "advance_pct",
             "pay_days", "rights", "rights_years", "rights_territory", "terms", "rules", "morning_time")
_JOB_KEYS = ("title", "brief", "engine", "kind", "deliverables", "deadline", "quote", "data")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..motiondesk import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    if action == "job" and a.get("quote") and not _owner(ctx):
        raise ToolError("Daam sirf owner likhti hain.")
    jb = _s(a.get("job"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in _SET_KEYS if k in a})
        if action == "client":
            return S.client_save(t, _s(a.get("name")), _s(a.get("client")), _s(a.get("contact")), _s(a.get("phone")),
                                 _s(a.get("email")), _s(a.get("gstin")), _s(a.get("state")),
                                 a.get("kit") if isinstance(a.get("kit"), dict) else None, _s(a.get("notes")))
        if action == "asset":
            return S.asset_save(t, _s(a.get("name")), _s(a.get("kind")), _s(a.get("source")), _s(a.get("licence")),
                                _s(a.get("licence_ref")), _s(a.get("credit")), _s(a.get("valid_until")), _s(a.get("notes")))
        if action == "job":
            return S.job_new(t, _s(a.get("client")), _s(a.get("title")), _s(a.get("brief")), _s(a.get("engine")) or "motion",
                             _s(a.get("kind")), a.get("deliverables"), _s(a.get("deadline")), a.get("quote"), _s(a.get("template")),
                             actor, conv)
        if action == "update":
            return S.job_update(t, jb, actor, **{k: a[k] for k in _JOB_KEYS if k in a})
        if action == "storyboard":
            return S.storyboard(t, jb, a.get("seconds"), actor)
        if action == "frames":
            return S.storyboard_edit(t, jb, a.get("frames"), actor)
        if action == "storyboard_send":
            return S.storyboard_request(t, jb, actor, conv)
        if action == "client_ok":
            return S.client_ok(t, jb, _s(a.get("by")), actor)
        if action == "render":
            return S.render(t, jb, _s(a.get("force_reason")), actor, conv)
        if action == "feedback":
            return S.feedback(t, jb, _s(a.get("text")), _s(a.get("by")), actor)
        if action == "revise":
            return S.revise(t, jb, a.get("data") if isinstance(a.get("data"), dict) else None, _s(a.get("free_reason")), actor, conv)
        if action == "extra_round":
            return S.extra_round_request(t, jb, actor, conv)
        if action == "use_asset":
            return S.use_asset(t, jb, _s(a.get("asset")))
        if action == "template":
            return S.template_save(t, jb, _s(a.get("name")))
        if action == "final":
            return S.final_request(t, jb, actor, conv)
        if action == "invoice":
            return S.invoice_request(t, jb, _s(a.get("bill")) or "final", actor, conv)
        if action == "message":
            return S.message_request(t, jb, _s(a.get("text")), actor, conv)
        if action == "paid":
            return S.paid(t, _s(a.get("invoice")), a.get("amount"), _s(a.get("ref")), actor)
        if action == "cancel":
            return S.cancel(t, jb, _s(a.get("reason")), actor)
        if action == "forget_client":
            return S.forget_client(t, _s(a.get("client")), actor)
    except S.MotiondeskError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..motiondesk import rules as R
    from ..motiondesk import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "jobs":
            return {"jobs": S.jobs(t, _s(a.get("status")), _s(a.get("client")))}
        if what == "job":
            return S.job_view(t, _s(a.get("job")))
        if what == "clients":
            return {"clients": S.clients(t)}
        if what == "assets":
            return {"assets": S.assets(t)}
        if what == "templates":
            return {"templates": S.templates(t)}
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status")) or "waiting")}
        if what == "platforms":
            return {"platforms": R.PLATFORMS}
        if what == "settings":
            return S.settings(t)
    except S.MotiondeskError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{what}' nahi pehchana.")


async def _motion_desk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _motion_desk_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


MOTIONDESK_HANDLERS = {"motion_desk": _motion_desk, "motion_desk_dekho": _motion_desk_dekho}
