"""Graphic Sahayak tools (a freelance graphic designer's / studio's client desk). `graphic_dekho` only reads; `graphic` works.

Proofs are drawn by the brand engine in the CLIENT's kit or come from her own design file (print-checked). The quotation, every
proof, an extra paid revision round, the final files, the print order, invoices, discounts and messages become CARDS here; only
HER tap in the app decides them. Revision rounds are counted by the server. Hoola never invents a price, date or fact, never
sends anything and never takes or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "client", "logo", "vendor", "job", "render", "upload", "feedback", "client_ok", "waive", "asset",
            "asset_remove", "tm", "assignment", "accepted", "quote_send", "proof_send", "extra_round", "handover", "print_order",
            "invoice", "discount", "message", "paid", "cancel", "done", "forget"]
_OWNER_ONLY = {"settings", "waive", "assignment", "paid", "cancel", "done", "forget"}

GRAPHIC_TOOLS = [
    {"name": "graphic", "description": (
        "Graphic designer's client desk. NEVER invent prices, dates, facts or what a client said; ask her. Cards = only her tap "
        "decides (say 'aapki haan ka card bheja hai', never 'sent'). client: name, business, phone, kind business|individual, "
        "gstin, state, colors, font, tagline, contact, tds_pct (what the client says it deducts). logo: client, file_id. "
        "vendor: name, phone, spec {color, dpi, bleed, safe, format, pdfx}. job: job (to update) or client, kind, brief (client "
        "words = data), facts (what may appear), sizes, print_fmt, print_custom {w_mm,h_mm}, print_job {qty,stock,finish}, vendor, "
        "due, lines [{name,qty,rate}] (her prices), rounds, extra_round_price, advance_pct. render: job, instruction / words / "
        "layout / sizes (brand engine, client's kit). upload: job, file_id (her design file; print preflight). feedback: job, text "
        "(opens a round; rounds used up = extra_round card first). client_ok: job, version, evidence. asset: job, name, kind "
        "font|image|icon, source, licence. tm: job, result nothing_similar|similar_found|registered_same|not_done, classes. "
        "quote_send | proof_send (version) | extra_round | handover (force*) | print_order (vendor) | invoice (what advance|final) "
        "| discount (amount|pct, reason) | message (text): job -> CARD. accepted: job, evidence. * = owner only: settings, waive, "
        "assignment, paid, cancel, done, forget (client)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS},
         "job": {"type": "string"}, "client": {"type": "string"}, "name": {"type": "string"}, "business": {"type": "string"},
         "phone": {"type": "string"}, "email": {"type": "string"}, "kind": {"type": "string"}, "gstin": {"type": "string"},
         "state": {"type": "string"}, "country": {"type": "string"}, "tds_pct": {"type": "number"},
         "colors": {"type": "object"}, "font": {"type": "string"}, "tagline": {"type": "string"}, "contact": {"type": "object"},
         "language": {"type": "string"}, "notes": {"type": "string"}, "file_id": {"type": "string"},
         "spec": {"type": "object"}, "does": {"type": "string"}, "vendor": {"type": "string"},
         "heading": {"type": "string"}, "brief": {"type": "string"}, "facts": {"type": "string"},
         "sizes": {"type": "array", "items": {"type": "string"}}, "print_fmt": {"type": "string"},
         "print_custom": {"type": "object"}, "print_job": {"type": "object"}, "due": {"type": "string"},
         "lines": {"type": "array", "items": {"type": "object"}}, "rounds": {"type": "integer"},
         "extra_round_price": {"type": "number"}, "advance_pct": {"type": "number"}, "instruction": {"type": "string"},
         "words": {"type": "object"}, "layout": {"type": "string"}, "text": {"type": "string"}, "version": {"type": "integer"},
         "evidence": {"type": "string"}, "reason": {"type": "string"}, "source": {"type": "string"}, "licence": {"type": "string"},
         "licence_ref": {"type": "string"}, "result": {"type": "string"}, "classes": {"type": "array", "items": {"type": "integer"}},
         "rights": {"type": "string"}, "years": {"type": "integer"}, "territory": {"type": "string"},
         "force": {"type": "boolean"}, "what": {"type": "string"}, "amount": {"type": "number"}, "pct": {"type": "number"},
         "mode": {"type": "string"}, "ref": {"type": "string"},
         "studio": {"type": "string"}, "designer": {"type": "string"}, "upi_id": {"type": "string"}, "gst_rate": {"type": "number"},
         "sac": {"type": "string"}, "lut": {"type": "string"}, "udyam": {"type": "string"}, "extra_round": {"type": "number"},
         "pay_days": {"type": "integer"}, "validity_days": {"type": "integer"}, "handover_after_pay": {"type": "boolean"},
         "assign_copyright": {"type": "boolean"}, "terms": {"type": "string"}, "address": {"type": "string"},
         "morning_time": {"type": "string"}, "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "graphic_dekho", "description": (
        "Read the design desk (nothing changes). what=day (late / due / feedback waiting / proofs waiting / unpaid / cards) | jobs "
        "(status open|brief|proof|approved|delivered..., client) | job (job: rounds, versions with checks, quote, assets, payments) "
        "| clients | client (client: kit + jobs) | vendors | cards | settings | quote (job) | tm_help (job: IP India trade-mark "
        "search steps + classes; Hoola never opens the site) | formats (print sizes) | licences (font / asset rules)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "jobs", "job", "clients", "client", "vendors", "cards", "settings", "quote",
                                             "tm_help", "formats", "licences"]},
         "job": {"type": "string"}, "client": {"type": "string"}, "status": {"type": "string"},
         "classes": {"type": "array", "items": {"type": "integer"}}},
         "required": ["what"]}},
]

GRAPHIC_LABELS = {"graphic": "Design desk ka kaam kar raha hoon", "graphic_dekho": "Design ke kaam dekh raha hoon"}

_SET_KEYS = ("studio", "designer", "gstin", "state", "address", "phone", "email", "upi_id", "gst_rate", "sac", "lut", "udyam",
             "rounds", "extra_round", "advance_pct", "pay_days", "validity_days", "handover_after_pay", "assign_copyright",
             "terms", "rules", "morning_time")
_CLIENT_KEYS = ("name", "business", "phone", "email", "kind", "gstin", "state", "country", "tds_pct", "colors", "font",
                "tagline", "contact", "language", "notes")
_JOB_KEYS = ("kind", "brief", "facts", "sizes", "print_fmt", "print_custom", "print_job", "vendor", "due", "lines", "rounds",
             "extra_round_price", "advance_pct")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..graphic import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    jb = _s(a.get("job"))
    try:
        if action == "settings":
            return S.save_settings(t, actor, **{k: a[k] for k in _SET_KEYS if k in a})
        if action == "client":
            return S.client_save(t, _s(a.get("client")), actor, **{k: a[k] for k in _CLIENT_KEYS if k in a})
        if action == "logo":
            return S.client_logo(t, _s(a.get("client")), None, _s(a.get("file_id")), actor=actor)
        if action == "vendor":
            return S.vendor_save(t, _s(a.get("name") or a.get("vendor")), _s(a.get("phone")), _s(a.get("email")),
                                 _s(a.get("does")), a.get("spec") if isinstance(a.get("spec"), dict) else None, _s(a.get("notes")),
                                 actor=actor)
        if action == "job":
            kw = {k: a[k] for k in _JOB_KEYS if k in a}
            if a.get("heading"):
                kw["title"] = a["heading"]
            return S.job_save(t, jb, _s(a.get("client")), actor, conv, **kw)
        if action == "render":
            return S.proof_render(t, jb, a.get("words") if isinstance(a.get("words"), dict) else None, _s(a.get("layout")),
                                  a.get("sizes"), _s(a.get("instruction")), actor, conv)
        if action == "upload":
            if not a.get("file_id"):
                raise ToolError("Design ki file_id chahiye (chat mein file bhejiye).")
            return S.proof_upload(t, jb, None, "", _s(a.get("file_id")), _s(a.get("notes") or a.get("text")), actor, conv)
        if action == "feedback":
            return S.feedback(t, jb, _s(a.get("text")), a.get("version"), actor, conv)
        if action == "client_ok":
            return S.client_approved(t, jb, a.get("version"), _s(a.get("evidence")), actor)
        if action == "waive":
            return S.waive_round(t, jb, _s(a.get("reason")), actor)
        if action == "asset":
            return S.asset_add(t, jb, _s(a.get("name")), _s(a.get("kind")) or "font", _s(a.get("source")), _s(a.get("licence")),
                               _s(a.get("licence_ref")), actor)
        if action == "asset_remove":
            return S.asset_remove(t, jb, _s(a.get("name")), actor)
        if action == "tm":
            return S.tm_record(t, jb, _s(a.get("result")), a.get("classes") or [], _s(a.get("notes")), actor)
        if action == "assignment":
            return S.set_assignment(t, jb, _s(a.get("rights")), a.get("years"), _s(a.get("territory")), actor)
        if action == "accepted":
            return S.accepted(t, jb, _s(a.get("evidence")), actor)
        if action == "quote_send":
            return S.quote_request(t, jb, actor, conv)
        if action == "proof_send":
            return S.proof_send(t, jb, a.get("version"), actor, conv)
        if action == "extra_round":
            return S.extra_request(t, jb, actor, conv)
        if action == "handover":
            if a.get("force") and not _owner(ctx):
                raise ToolError("Paise baaki hote hue files dena: sirf owner.")
            return S.handover_request(t, jb, bool(a.get("force")), actor, conv)
        if action == "print_order":
            return S.vendor_request(t, jb, _s(a.get("vendor")), actor, conv)
        if action == "invoice":
            return S.invoice_request(t, jb, _s(a.get("what")) or "final", actor, conv)
        if action == "discount":
            return S.discount_request(t, jb, a.get("amount"), a.get("pct"), _s(a.get("reason")), actor, conv)
        if action == "message":
            return S.message_request(t, jb, _s(a.get("text")), actor, conv)
        if action == "paid":
            return S.paid(t, jb, a.get("amount"), _s(a.get("mode")) or "upi", _s(a.get("ref")), "", actor)
        if action == "cancel":
            return S.cancel(t, jb, _s(a.get("reason")), actor)
        if action == "done":
            return S.done(t, jb, actor)
        if action == "forget":
            return S.forget_client(t, _s(a.get("client")), actor)
    except S.GraphicError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..graphic import rules as R
    from ..graphic import service as S
    t, jb = ctx.tenant_id, _s(a.get("job"))
    try:
        if what == "day":
            return S.day(t)
        if what == "jobs":
            return {"jobs": S.jobs(t, _s(a.get("status")), _s(a.get("client")))}
        if what == "job":
            return S.job_view(t, jb)
        if what == "clients":
            return {"clients": S.clients(t)}
        if what == "client":
            return S.client_view(t, _s(a.get("client")))
        if what == "vendors":
            return {"vendors": S.vendors(t)}
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status")) or "waiting")}
        if what == "settings":
            return S.settings(t)
        if what == "quote":
            return S.job_view(t, jb)["quote"]
        if what == "tm_help":
            return S.tm_help(t, jb, a.get("classes") or None)
        if what == "formats":
            return {"formats": R.FORMATS, "vendor_defaults": R.VENDOR_DEFAULTS}
        if what == "licences":
            return {"fonts": {k: {"label": v[0], "rule": v[1]} for k, v in R.FONT_LICENCES.items()}, "assets": R.ASSET_LICENCES}
    except S.GraphicError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{what}' nahi pehchana.")


async def _graphic(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _graphic_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


GRAPHIC_HANDLERS = {"graphic": _graphic, "graphic_dekho": _graphic_dekho}
