"""v0.128 App Sahayak tools. `app_banao` designs her native app (every screen, tap-through prototype) before any app is
built; `app_dekho` only reads. Plan, look and 'Design pakka' are HER choices on the cards (the tool can do them only when
the owner herself clearly says so)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

APP_TOOLS = [
    {"name": "app_banao", "description": (
        "Design HER business a premium NATIVE mobile app (Android + iPhone look) and show her EVERY screen as a tap-through "
        "prototype BEFORE anything is built. A few words are enough: the 1 lakh app brief library knows 1,000 kinds of "
        "business x 10 app goals x 10 premium styles. action=new: brief (her words, e.g. 'kirana dukaan ki app, ghar pe "
        "delivery'), name, goal (shop|food_order|booking|learning|membership|service_request|khata|catalogue|events|"
        "community; guessed), style (optional), answers {name, phone, whatsapp, address, hours, upi_id}. Returns the PLAN "
        "card (screens, tabs, main flow, legal screens made by code) + up to 3 questions: ask them in ONE message (or "
        "ask_form). action=answer: app + answers. action=plan_ok: ONLY when she clearly said haan to the plan (+ drop: "
        "screens she doesn't want) -> Home screen in 3 looks (a few minutes; cards update by themselves, don't poll). "
        "action=look: app + index (0-2) she chose (+ colors_from) -> every screen is designed while she watches the board. "
        "action=change: app + instruction (her words: 'cart mein coupon hatao', 'rang halka', 'booking screen add karo', "
        "'tabs mein offers') -> only those screens redesign. action=approve: ONLY when she herself says 'design pakka' "
        "(+ hash from the card) - freezes the design for the real app build. action=stop / resume / delete*. "
        "Never invent prices, phone numbers or reviews ([blank] instead); never card / CVV / UPI PIN / password fields; payments = "
        "UPI to her own UPI ID. The real Android / iPhone app build and store publishing come in later versions. (* owner only)"),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "answer", "plan_ok", "look", "change", "approve", "stop", "resume", "delete"]},
         "app": {"type": "string", "description": "app number (A-0001) or name; empty = the latest"},
         "brief": {"type": "string"}, "name": {"type": "string"}, "goal": {"type": "string"}, "style": {"type": "string"},
         "answers": {"type": "object"}, "index": {"type": "integer"}, "colors_from": {"type": "integer"},
         "instruction": {"type": "string"}, "drop": {"type": "array", "items": {"type": "string"}}, "hash": {"type": "string"}},
         "required": ["action"]}},
    {"name": "app_dekho", "description": (
        "Read her app designs (nothing changes). what=apps | app (app: board, screens, checks, preview link, versions) | "
        "checks (app) | spec (app: the frozen design contract: tokens, tabs, every screen's purpose / data / actions) | "
        "library (q or industry: business types with their app goal) | brief (field, goal, style: the full ready app brief) | "
        "understand (q: what a short ask means: business type, app goal, 3 looks)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["apps", "app", "checks", "spec", "library", "brief", "understand"]},
         "app": {"type": "string"}, "q": {"type": "string"}, "industry": {"type": "string"}, "field": {"type": "string"},
         "goal": {"type": "string"}, "style": {"type": "string"}},
         "required": ["what"]}},
]
APP_LABELS = {"app_banao": "App design bana raha hoon", "app_dekho": "App design dekh raha hoon"}
_OWNER_ONLY = {"delete"}
_TAP_LIKE = {"plan_ok", "look", "approve"}


def _owner(ctx: Ctx) -> bool:
    return ctx.actor == "owner" or str(ctx.actor).startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..appmaker import service as S
    t, ref, conv = ctx.tenant_id, str(a.get("app") or ""), ctx.conversation_id or ""
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf maalkin yeh kar sakti hain.")
    if action in _TAP_LIKE and not _owner(ctx):
        raise ToolError("Plan / look / design pakka sirf maalkin chunti hain (app ke card par).")
    if action == "new":
        v = S.new(t, str(a.get("brief") or ""), conv, str(a.get("name") or ""), "", str(a.get("goal") or ""),
                  str(a.get("style") or ""), a.get("answers") if isinstance(a.get("answers"), dict) else None)
        return {k: v.get(k) for k in ("id", "number", "name", "status", "field_label", "goal_label", "plan", "questions",
                                      "understood", "say")}
    if action == "answer":
        return S.answer(t, ref, a.get("answers") if isinstance(a.get("answers"), dict) else {})
    if action == "plan_ok":
        v = S.approve_plan(t, ref, conv, a.get("drop") if isinstance(a.get("drop"), list) else None)
        return {"status": v["status"], "say": "Home screen ke 3 looks ban rahe hain; card par aa jayenge (poll mat kariye)."}
    if action == "look":
        cf = a.get("colors_from")
        v = S.choose_look(t, ref, int(a.get("index") or 0), int(cf) if cf is not None else None, conv)
        return {"status": v["status"], "preview": v["preview"],
                "say": "Screens banana shuru. Har screen ban-te hi board aur prototype mein dikhegi."}
    if action == "change":
        return S.change(t, ref, str(a.get("instruction") or ""), conv)
    if action == "approve":
        h = str(a.get("hash") or "") or S.get(t, ref).get("hash", "")
        v = S.approve(t, ref, h)
        return {"status": v["status"], "version": v["version"], "say": v["say"]}
    if action == "stop":
        return S.stop(t, ref)
    if action == "resume":
        return S.resume(t, ref)
    if action == "delete":
        return S.delete(t, ref)
    raise ToolError(f"Unknown action {action}")


async def app_banao(ctx: Ctx, action: str, **a) -> Any:
    from ..appmaker import service as S
    try:
        return await asyncio.to_thread(_act, ctx, action, a)
    except (S.AppError, KeyError) as e:
        raise ToolError(str(e) or "Nahi mila")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> Any:
    from ..appmaker import library as L
    from ..appmaker import service as S
    t, ref = ctx.tenant_id, str(a.get("app") or "")
    if what == "apps":
        return {"apps": S.apps(t)}
    if what == "app":
        v = S.get(t, ref)
        v.pop("facts", None)
        return v
    if what == "checks":
        return S.get(t, ref).get("checks")
    if what == "spec":
        return S.spec(t, ref)
    if what == "library":
        return L.browse(str(a.get("industry") or ""), str(a.get("q") or ""), 30)
    if what == "brief":
        b = L.brief(str(a.get("field") or ""), str(a.get("goal") or ""), str(a.get("style") or ""))
        return {k: b[k] for k in ("id", "field_label", "goal_label", "style_label", "screens", "tabs", "flow", "code_screens",
                                  "questions", "text")}
    if what == "understand":
        return L.understand(str(a.get("q") or ""))
    raise ToolError(f"Unknown what {what}")


async def app_dekho(ctx: Ctx, what: str, **a) -> Any:
    from ..appmaker import service as S
    try:
        return await asyncio.to_thread(_read, ctx, what, a)
    except (S.AppError, KeyError) as e:
        raise ToolError(str(e) or "Nahi mila")


APP_HANDLERS = {"app_banao": app_banao, "app_dekho": app_dekho}
