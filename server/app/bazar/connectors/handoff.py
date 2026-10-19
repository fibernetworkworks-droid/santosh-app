"""L3 Handoff packs: apps and portals without agent access (yet). Santosh does the thinking, prepares every detail and
opens the right app or official portal at the start; the user finishes there. Travel and logistics packs run this way
until a partner API is signed (config.partner_pending)."""
from __future__ import annotations

import datetime as dt
from typing import Any

from ..db import Reminder
from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec
from .timeparse import parse_when, to_utc_naive


class HandoffExecutor:
    name = "handoff"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [
            ToolSpec("prepare", f"Prepare the user's task for {pack.name}: restate the goal, gather details, and return the link to open "
                     f"plus the steps the user finishes there. {pack.description}",
                     {"type": "object", "properties": {"goal": {"type": "string"},
                                                       "details": {"type": "object", "description": "Anything already known: dates, names, items, budget"}},
                      "required": ["goal"]}, 1),
            ToolSpec("remind", f"Set a reminder tied to {pack.name} (exam date, appointment, delivery, renewal).",
                     {"type": "object", "properties": {"text": {"type": "string"}, "when": {"type": "string"}}, "required": ["text", "when"]}, 1),
        ]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        cfg = pack.config
        if tool == "prepare":
            goal = str(args.get("goal") or (ctx.task.text if ctx.task else "")).strip()
            if not goal:
                raise ToolError(f"What do you want to do on {pack.name}?")
            details = {k: v for k, v in (args.get("details") or {}).items() if v not in (None, "")}
            prof = ctx.user.profile or {}
            prefill = {"name": ctx.user.name, "mobile": ctx.user.phone, "city": ctx.user.city, "pincode": ctx.user.pincode,
                       "address": prof.get("address", "")}
            out = {
                "app": pack.name, "goal": goal, "details": details,
                "open": {"web": cfg.get("web", ""), "web_verified": bool(cfg.get("web_verified")), "app_store": cfg.get("play_search", "")},
                "you_finish": cfg.get("steps", []),
                "prefill_from_profile": {k: v for k, v in prefill.items() if v},
                "message": f"Ready for {pack.name}. " + ("Opening the official site. " if cfg.get("web") else "Opening the app. ")
                           + "Finish the last step there; tell me the reference number and I'll track it.",
            }
            if cfg.get("partner_pending"):
                out["note"] = "Direct booking through Santosh starts once our partner API is live."
            if ctx.task is not None:
                ctx.task.result = {**(ctx.task.result or {}), "handoff": {"pack": pack.id, "goal": goal}}
            return out
        if tool == "remind":
            when = parse_when(str(args.get("when", "")))
            if when is None:
                raise ToolError("When should I remind you?")
            r = Reminder(user_id=ctx.user.id, kind="reminder", text=f"{pack.name}: {args['text']}", due_at=to_utc_naive(when),
                         meta={"pack_id": pack.id, "created": dt.date.today().isoformat()})
            ctx.session.add(r)
            return {"reminder": r.text, "when": when.strftime("%a %d %b, %I:%M %p")}
        raise ToolError(f"Unknown tool {tool}")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        raise ToolError("Handoff packs have no approval actions")
