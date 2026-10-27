"""v0.118 Brand Sahayak tools (brand designer). `brand` makes / changes designs and the brand kit; `brand_dekho` only reads.
Final artwork is approved ONLY by her tap on the card in the app; the tool can only send that card."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

BRAND_TOOLS = [
    {"name": "brand", "description": (
        "Brand designer for HER business: posters in her brand colours, every platform size, a brand kit. "
        "action=make: brief (her words: what, offer, price, dates), kind (poster|festival|offer|event|hiring|product|quote|"
        "announcement; guessed), sizes (list or set: social|whatsapp|all_social|print|festival or insta_post, insta_square, "
        "insta_grid, story, fb_post, fb_cover, linkedin, x_post, yt_thumb, gbp, pinterest, a4, a3, a5, flex_6x3), festival "
        "(name, for greetings), photo (file_id of her product / shop photo), layout (hero|photo|split|minimal|offer|"
        "festival), ai_background (true only if she asks for an AI picture), template (a saved design number to reuse) -> "
        "proofs with a PROOF mark + checks. action=revise: design + instruction (her words). action=resize: design + sizes "
        "(add=false replaces). action=photo: design + file_id. action=approve: design -> sends her the FINAL approval card "
        "(she taps it in the app; never say it is final before that). action=copy / template (design, on true|false) / "
        "delete*. action=kit*: name, tagline, colors {primary|secondary|accent|dark|light: '#hex' or colour name}, contact "
        "{phone, whatsapp, website, instagram, address}, font (poppins|mukta), tone, rule (one lasting rule), state (for "
        "festival dates), language, nudge (festival reminders on/off), nudge_days. action=logo*: file_id of her logo "
        "(colours are read from it), clean_bg. (* owner only). Never use the National Flag, Ashoka Chakra, government "
        "emblems, Gandhi / PM pictures or other brands' logos; never invent prices / dates / phone numbers."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["make", "revise", "resize", "photo", "approve", "copy", "template", "delete",
                                               "kit", "logo"]},
         "brief": {"type": "string"}, "kind": {"type": "string"}, "sizes": {"type": "array", "items": {"type": "string"}},
         "festival": {"type": "string"}, "photo": {"type": "string"}, "layout": {"type": "string"},
         "ai_background": {"type": "boolean"}, "template": {"type": "string"}, "design": {"type": "string"},
         "instruction": {"type": "string"}, "add": {"type": "boolean"}, "file_id": {"type": "string"},
         "on": {"type": "boolean"}, "force": {"type": "boolean"}, "name": {"type": "string"}, "tagline": {"type": "string"},
         "colors": {"type": "object"}, "contact": {"type": "object"}, "font": {"type": "string"}, "tone": {"type": "string"},
         "rule": {"type": "string"}, "state": {"type": "string"}, "language": {"type": "string"},
         "nudge": {"type": "boolean"}, "nudge_days": {"type": "integer"}, "clean_bg": {"type": "boolean"}},
         "required": ["action"]}},
    {"name": "brand_dekho", "description": (
        "Read her brand work (nothing changes). what=kit | designs (status draft|waiting|approved|rejected|template, q) | "
        "design (design) | festivals (days: coming festivals with themes and whether a poster exists) | sizes."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["kit", "designs", "design", "festivals", "sizes"]},
         "design": {"type": "string"}, "status": {"type": "string"}, "q": {"type": "string"}, "days": {"type": "integer"}},
         "required": ["what"]}},
]
BRAND_LABELS = {"brand": "Poster bana raha hoon", "brand_dekho": "Brand kit dekh raha hoon"}
_OWNER_ONLY = {"kit", "logo", "delete"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _short(v: dict) -> dict:
    keep = ("id", "number", "kind_label", "title", "status", "version", "layout", "sizes", "checks", "blocks", "note",
            "festival", "content")
    return {k: v.get(k) for k in keep if k in v}


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..brand import service as B
    actor = getattr(ctx, "actor", "owner") or "owner"
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action in _OWNER_ONLY and actor != "owner" and not actor.startswith("approved:"):
            raise ToolError("Yeh sirf owner kar sakti hain.")
        if action == "make":
            r = B.make(t, _s(a.get("brief")), _s(a.get("kind")), a.get("sizes"), _s(a.get("festival")), _s(a.get("photo")),
                       _s(a.get("layout")), ai_background=bool(a.get("ai_background")), template=_s(a.get("template")),
                       conv=conv)
        elif action == "revise":
            r = B.revise(t, _s(a.get("design")), _s(a.get("instruction") or a.get("brief")), conv)
        elif action == "resize":
            r = B.resize(t, _s(a.get("design")), a.get("sizes"), a.get("add", True) is not False, conv)
        elif action == "photo":
            r = B.set_photo(t, _s(a.get("design")), _s(a.get("file_id") or a.get("photo")), conv=conv)
        elif action == "approve":
            r = B.request_approval(t, _s(a.get("design")), bool(a.get("force")), conv)
            r["note"] = "Card sent. Only her tap on 'Haan, final' makes the final files; do not say it is approved."
        elif action == "copy":
            r = B.copy_design(t, _s(a.get("design")))
        elif action == "template":
            r = B.copy_design(t, _s(a.get("design")), template=a.get("on", True) is not False)
        elif action == "delete":
            r = B.delete(t, _s(a.get("design")))
        elif action == "kit":
            keys = ("name", "tagline", "colors", "contact", "font", "tone", "rule", "state", "language", "nudge", "nudge_days")
            return {"kit": B.save_kit(t, **{k: a[k] for k in keys if k in a}), "say": "Brand kit save."}
        elif action == "logo":
            r = B.set_logo(t, file_id=_s(a.get("file_id")), clean_bg=bool(a.get("clean_bg")))
            return {"palette": r["palette"], "kit_colors": r["kit"]["colors"], "say": r["say"]}
        else:
            raise ToolError("action = make | revise | resize | photo | approve | copy | template | delete | kit | logo")
    except B.BrandError as e:
        raise ToolError(str(e))
    if isinstance(r.get("design"), dict):
        r = {**r, "design": _short(r["design"])}
    return r


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..brand import rules as R
    from ..brand import service as B
    t = ctx.tenant_id
    try:
        if what == "kit":
            return B.kit(t)
        if what == "designs":
            return {"designs": B.designs(t, _s(a.get("status")), _s(a.get("q")))}
        if what == "design":
            return _short(B.get(t, _s(a.get("design"))))
        if what == "festivals":
            return {"festivals": B.upcoming(t, int(a.get("days") or 45))}
        if what == "sizes":
            return {"sizes": {k: v["label"] for k, v in R.SIZES.items()}, "sets": R.SETS}
    except B.BrandError as e:
        raise ToolError(str(e))
    raise ToolError("what = kit | designs | design | festivals | sizes")


async def brand(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def brand_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


BRAND_HANDLERS = {"brand": brand, "brand_dekho": brand_dekho}
