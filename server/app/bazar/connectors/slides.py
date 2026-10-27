"""Confirm cards for Google Slides changes that are hard to undo or reach other people (deleting slides, sharing).
The card and the action come from the stored change, never from model text."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec

TITLES = {"delete": "Slides hatayein?", "share": "Presentation share karein?"}


class SlidesExecutor:
    name = "slides"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_change", "Ask the user to approve a prepared Google Slides change.",
                         {"type": "object", "properties": {"pending_id": {"type": "string"}}, "required": ["pending_id"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...slides import service as sv
        if tool != "confirm_change":
            raise ToolError(f"Unknown tool {tool}")
        p = sv.pending(ctx.user.id, str(args.get("pending_id", "")))
        if p is None or p["status"] != "pending":
            raise ToolError("Yeh badlav taiyaar nahi hai; dobara boliye.")
        sm = p["summary"]
        items = [{"name": sm.get("title", "")}] + [{"name": str(x)[:160]} for x in sm.get("lines", [])[:8]]
        if sm.get("note"):
            items.append({"name": sm["note"]})
        return NeedsApproval(tier=2, title=TITLES.get(p["action"], "Slides badlein?"), payee="Google Slides", amount_paise=0,
                             items=[i for i in items if i["name"]], pay_method="Santosh Slides",
                             preview={"message": f"Approve to {p['action']} in '{sm.get('title', '')}'."},
                             action={"executor": "slides", "pack_id": pack.id, "name": "run", "args": {"pending_id": p["id"]}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...slides import service as sv
        from ...slides.client import SlidesError
        if action != "run":
            raise ToolError(f"Unknown action {action}")
        try:
            return sv.run_pending(ctx.user.id, args["pending_id"])
        except SlidesError as e:
            raise ToolError(str(e))
