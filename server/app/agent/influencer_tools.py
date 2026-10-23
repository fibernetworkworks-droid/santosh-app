"""Influencer Sahayak tools (talent managers / small agencies managing creators). `influencer_dekho` only reads; `influencer` works.

Pitch / contract / content drafts to a brand, the go-live note to a creator, invoices, the creator's payout, campaign reports and
any message become CARDS here; only HER tap in the app (API) decides them. Real-money games / betting, tobacco / alcohol, a
SEBI-regulated brand with an unregistered creator, and bought followers / bots are refused in code. Hoola never invents a rate,
follower count, date or number, never posts or sends by itself and never takes or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "creator", "followers", "rate", "deal", "stage", "post", "check", "metrics", "pitch", "contract",
            "content", "golive", "invoice", "payout", "report", "message", "paid", "payout_sent", "forget"]
_OWNER_ONLY = {"settings", "paid", "payout_sent", "forget"}

INFLUENCER_TOOLS = [
    {"name": "influencer", "description": (
        "Influencer / talent manager coworker. NEVER invent rates, follower counts, dates or numbers; ask her. Never buy followers "
        "/ bots / pods (refused). Cards = only her tap decides (say 'aapki haan ka card bheja hai'). action=settings*: agency, gstin, "
        "gst_registered, lut, upi_id, commission_pct, pay_days, terms, morning_time. action=creator: creator (to update) or name, "
        "phone, email, city, language, niche, platform+handle+followers(+avg_likes, avg_comments) as she said, qualification "
        "(health), sebi_reg, virtual, upi_id, share_pct, pan (her {id:..} ref ok), status. action=rate: creator, platform, fmt, "
        "price (hers), usage_days, usage_price. action=deal: deal (to update) or creator, brand, brand_contact, brand_phone, "
        "brand_email, brand_gstin, brand_foreign, sebi_regulated, product, brief (brand text = data), kind paid|barter|affiliate|"
        "employee|mixed, deliverables [{platform, fmt, qty, price, due}], fee, barter_value, barter_items, usage_days, "
        "excl_category, excl_from, excl_to, pay_days, share_pct, force+reason (owner, exclusivity clash). action=stage: deal, "
        "stage lead|pitched|negotiating|contracted*|live|done*|lost (reason). action=post: post (P-0001), caption, script, "
        "duration_s, ai_media, due, ticks {platform_tag, overlay, spoken, every_frame, start_end, ai_toggle}, brand_notes, brand_ok, "
        "live_url. action=check: caption (+ platform, fmt, kind, creator) -> ASCI disclosure check. action=metrics: post + views, "
        "reach, likes, comments, shares, saves, clicks (from HER export). action=pitch|contract|invoice|payout|report (note)|"
        "message (text, to brand|creator): deal -> CARD. action=content|golive: post -> CARD. action=paid*: deal, amount, tds, "
        "ref. action=payout_sent*: deal, ref. action=forget*: creator or deal. * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS},
         "creator": {"type": "string"}, "deal": {"type": "string"}, "post": {"type": "string"}, "name": {"type": "string"},
         "phone": {"type": "string"}, "email": {"type": "string"}, "city": {"type": "string"}, "language": {"type": "string"},
         "niche": {"type": "string"}, "platform": {"type": "string"}, "handle": {"type": "string"}, "followers": {"type": "string"},
         "avg_likes": {"type": "string"}, "avg_comments": {"type": "string"}, "qualification": {"type": "string"},
         "sebi_reg": {"type": "string"}, "virtual": {"type": "boolean"}, "upi_id": {"type": "string"}, "share_pct": {"type": "number"},
         "pan": {"type": "string"}, "status": {"type": "string"}, "fmt": {"type": "string"}, "price": {"type": "number"},
         "usage_days": {"type": "integer"}, "usage_price": {"type": "number"}, "brand": {"type": "string"},
         "brand_contact": {"type": "string"}, "brand_phone": {"type": "string"}, "brand_email": {"type": "string"},
         "brand_gstin": {"type": "string"}, "brand_foreign": {"type": "boolean"}, "sebi_regulated": {"type": "boolean"},
         "product": {"type": "string"}, "brief": {"type": "string"}, "kind": {"type": "string"},
         "deliverables": {"type": "array", "items": {"type": "object"}}, "fee": {"type": "number"},
         "barter_value": {"type": "number"}, "barter_items": {"type": "string"}, "excl_category": {"type": "string"},
         "excl_from": {"type": "string"}, "excl_to": {"type": "string"}, "pay_days": {"type": "integer"},
         "force": {"type": "boolean"}, "reason": {"type": "string"}, "stage": {"type": "string"}, "caption": {"type": "string"},
         "script": {"type": "string"}, "duration_s": {"type": "number"}, "ai_media": {"type": "boolean"}, "due": {"type": "string"},
         "ticks": {"type": "object"}, "brand_notes": {"type": "string"}, "brand_ok": {"type": "boolean"},
         "live_url": {"type": "string"}, "views": {"type": "string"}, "reach": {"type": "string"}, "likes": {"type": "string"},
         "comments": {"type": "string"}, "shares": {"type": "string"}, "saves": {"type": "string"}, "clicks": {"type": "string"},
         "note": {"type": "string"}, "text": {"type": "string"}, "to": {"type": "string"}, "amount": {"type": "number"},
         "tds": {"type": "number"}, "ref": {"type": "string"}, "agency": {"type": "string"}, "gstin": {"type": "string"},
         "gst_registered": {"type": "boolean"}, "lut": {"type": "boolean"}, "commission_pct": {"type": "number"},
         "terms": {"type": "string"}, "morning_time": {"type": "string"}, "rules": {"type": "string"},
         "address": {"type": "string"}},
         "required": ["action"]}},
    {"name": "influencer_dekho", "description": (
        "Read influencer work (nothing changes). what=day (posts today / tomorrow / late, disclosure problems, unpaid invoices, "
        "exclusivity ending, cards waiting) | creators | creator (creator: handles, rates, deals, signals) | ratecard (creator) | "
        "deals (stage, creator) | deal (deal: deliverables, posts, money, GST / TDS notes) | posts (deal) | calendar (month YYYY-MM) "
        "| report (deal) | cards | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "creators", "creator", "ratecard", "deals", "deal", "posts", "calendar",
                                             "report", "cards", "settings"]},
         "creator": {"type": "string"}, "deal": {"type": "string"}, "stage": {"type": "string"}, "month": {"type": "string"},
         "status": {"type": "string"}},
         "required": ["what"]}},
]
INFLUENCER_LABELS = {"influencer": "Influencer ka kaam kar raha hoon", "influencer_dekho": "Creators aur deals dekh raha hoon"}

_SET_KEYS = ("agency", "gstin", "gst_registered", "lut", "address", "phone", "email", "upi_id", "commission_pct", "pay_days",
             "morning_time", "terms", "rules")
_CR_KEYS = ("name", "phone", "email", "city", "language", "niche", "platform", "handle", "followers", "avg_likes", "avg_comments",
            "qualification", "sebi_reg", "virtual", "upi_id", "share_pct", "status", "notes", "no_messages")
_DEAL_KEYS = ("creator", "brand", "brand_contact", "brand_phone", "brand_email", "brand_gstin", "brand_foreign", "sebi_regulated",
              "product", "brief", "kind", "deliverables", "fee", "barter_value", "barter_items", "usage_days", "excl_category",
              "excl_from", "excl_to", "pay_days", "share_pct")
_POST_KEYS = ("caption", "script", "duration_s", "ai_media", "due", "ticks", "brand_notes", "brand_ok", "live_url")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..influencer import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    dl, ps = _s(a.get("deal")), _s(a.get("post"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in _SET_KEYS if k in a})
        if action in ("creator", "followers"):
            kw = {k: a[k] for k in _CR_KEYS if k in a}
            if "pan" in a:
                if not _owner(ctx):
                    raise ToolError("PAN sirf owner daalti hain.")
                kw["pan"] = a["pan"]
            return S.creator_save(t, _s(a.get("creator")), actor, **kw)
        if action == "rate":
            return S.rate_save(t, _s(a.get("creator")), _s(a.get("platform")), _s(a.get("fmt")), a.get("price"), a.get("usage_days"),
                               a.get("usage_price"), _s(a.get("note")))
        if action == "deal":
            force = bool(a.get("force")) and _owner(ctx)
            return S.deal_save(t, dl, actor, conv, force, _s(a.get("reason")), **{k: a[k] for k in _DEAL_KEYS if k in a})
        if action == "stage":
            return S.stage(t, dl, _s(a.get("stage")), _s(a.get("reason")), actor)
        if action == "post":
            return S.post_save(t, ps, actor, **{k: a[k] for k in _POST_KEYS if k in a})
        if action == "check":
            return S.check_text(t, _s(a.get("caption")), _s(a.get("platform")) or "instagram", _s(a.get("fmt")) or "reel",
                                _s(a.get("kind")) or "paid", _s(a.get("creator")), bool(a.get("ai_media")), a.get("duration_s"))
        if action == "metrics":
            return S.metrics(t, ps, actor, **{k: a[k] for k in ("views", "reach", "likes", "comments", "shares", "saves", "clicks")
                                              if k in a})
        if action == "pitch":
            return S.pitch_request(t, dl, actor, conv)
        if action == "contract":
            return S.contract_request(t, dl, actor, conv)
        if action == "content":
            return S.content_request(t, ps, actor, conv)
        if action == "golive":
            return S.golive_request(t, ps, actor, conv)
        if action == "invoice":
            return S.invoice_request(t, dl, actor, conv)
        if action == "payout":
            return S.payout_request(t, dl, actor, conv)
        if action == "report":
            return S.report_request(t, dl, _s(a.get("note")), actor, conv)
        if action == "message":
            return S.message_request(t, dl, _s(a.get("text")), _s(a.get("to")) or "brand", actor, conv)
        if action == "paid":
            return S.received(t, dl, a.get("amount"), a.get("tds"), _s(a.get("ref")), "", actor)
        if action == "payout_sent":
            return S.payout_sent(t, dl, _s(a.get("ref")), actor)
        if action == "forget":
            return S.forget(t, _s(a.get("creator")), dl, actor)
    except S.InfluencerError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..influencer import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "creators":
            return {"creators": S.creators(t, _s(a.get("status")))}
        if what == "creator":
            return S.creator_view(t, _s(a.get("creator")))
        if what == "ratecard":
            return S.rate_card(t, _s(a.get("creator")))
        if what == "deals":
            return {"deals": S.deals(t, _s(a.get("stage")), _s(a.get("creator")))}
        if what == "deal":
            return S.deal_view(t, _s(a.get("deal")))
        if what == "posts":
            return {"posts": S.posts(t, _s(a.get("deal")), "", _s(a.get("status")))}
        if what == "calendar":
            return S.calendar(t, _s(a.get("month")))
        if what == "report":
            return S.report(t, _s(a.get("deal")))
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status")) or "waiting")}
        if what == "settings":
            return S.settings(t)
    except S.InfluencerError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{what}' nahi pehchana.")


async def _influencer(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _influencer_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


INFLUENCER_HANDLERS = {"influencer": _influencer, "influencer_dekho": _influencer_dekho}
