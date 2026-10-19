"""Confirm cards for calendar changes that email other people: invites, rescheduling a shared meeting, cancelling
or declining. The card text and what runs after the tap come from the stored change, never from model text."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec

TITLES = {"create": "Invite bhejein?", "update": "Meeting badlein aur sabko batayein?",
          "cancel": "Event cancel karein?", "decline": "Meeting ke liye mana karein?"}


class CalendarExecutor:
    name = "cal"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_change", "Ask the user to approve a prepared calendar change.",
                         {"type": "object", "properties": {"pending_id": {"type": "string"}}, "required": ["pending_id"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...cal import service as cs
        if tool != "confirm_change":
            raise ToolError(f"Unknown tool {tool}")
        p = cs.pending(ctx.user.id, str(args.get("pending_id", "")))
        if p is None or p["status"] != "pending":
            raise ToolError("Yeh calendar badlav taiyaar nahi hai; dobara boliye.")
        sm = p["summary"]
        items = [{"name": sm.get("title", "")}, {"name": sm.get("when", "")}]
        if sm.get("location"):
            items.append({"name": f"Jagah: {sm['location']}"})
        if sm.get("people"):
            items.append({"name": "Logon ko email jayega: " + ", ".join(sm["people"])[:200]})
        if sm.get("meet"):
            items.append({"name": "Google Meet link banega"})
        if sm.get("note"):
            items.append({"name": sm["note"][:200]})
        return NeedsApproval(tier=2, title=TITLES.get(p["action"], "Calendar badlav?"), payee="Google Calendar",
                             amount_paise=0, items=[i for i in items if i["name"]], pay_method="Santosh Calendar",
                             preview={"message": f"Approve to {p['action']} '{sm.get('title', '')}' on Google Calendar."},
                             action={"executor": "cal", "pack_id": pack.id, "name": "run", "args": {"pending_id": p["id"]}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...cal import service as cs
        from ...cal.google import CalError
        if action != "run":
            raise ToolError(f"Unknown action {action}")
        try:
            return cs.run_pending(ctx.user.id, args["pending_id"])
        except CalError as e:
            raise ToolError(str(e))
