"""Confirm cards for YouTube changes the public will see: replying to a comment, editing a video, uploading.
The card and the action come from the stored change, never from model text."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec

TITLES = {"reply": "Comment ka jawab post karein?", "update": "Video badlein?", "upload": "YouTube par upload karein?"}


class YouTubeExecutor:
    name = "youtube"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_change", "Ask the user to approve a prepared YouTube change.",
                         {"type": "object", "properties": {"pending_id": {"type": "string"}}, "required": ["pending_id"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...youtube import service as ys
        if tool != "confirm_change":
            raise ToolError(f"Unknown tool {tool}")
        p = ys.pending(ctx.user.id, str(args.get("pending_id", "")))
        if p is None or p["status"] != "pending":
            raise ToolError("Yeh badlav taiyaar nahi hai; dobara boliye.")
        sm = p["summary"]
        items = [{"name": sm.get("title", "")}] + [{"name": str(x)[:220]} for x in sm.get("lines", [])[:6]]
        items.append({"name": "Yeh YouTube par sabko dikhega."})
        return NeedsApproval(tier=2, title=TITLES.get(p["action"], "YouTube badlav?"), payee="YouTube", amount_paise=0,
                             items=[i for i in items if i["name"]], pay_method="Santosh YouTube",
                             preview={"message": f"Approve to {p['action']} on YouTube."},
                             action={"executor": "youtube", "pack_id": pack.id, "name": "run", "args": {"pending_id": p["id"]}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...youtube import service as ys
        from ...youtube.client import YTError
        if action != "run":
            raise ToolError(f"Unknown action {action}")
        try:
            return ys.run_pending(ctx.user.id, args["pending_id"])
        except YTError as e:
            raise ToolError(str(e))
