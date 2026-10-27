"""Confirm card for deleting a Santosh Notebook (its sources, notes and audio go with it)."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec


class NotebookExecutor:
    name = "notebook"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_delete", "Ask the user to approve deleting a notebook.",
                         {"type": "object", "properties": {"notebook": {"type": "string"}}, "required": ["notebook"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...notebook import service as ns
        if tool != "confirm_delete":
            raise ToolError(f"Unknown tool {tool}")
        try:
            d = ns.detail(ctx.user.id, str(args.get("notebook", "")))
        except ns.NotebookError as e:
            raise ToolError(str(e))
        return NeedsApproval(tier=2, title="Notebook delete karein?", payee="Santosh Notebook", amount_paise=0,
                             items=[{"name": f"{d['emoji']} {d['title']}"},
                                    {"name": f"{len(d['sources'])} sources, {len(d['notes'])} notes, {len(d['audio'])} audio"},
                                    {"name": "Yeh wapas nahi aayega (aapki asli files par koi asar nahi)."}],
                             pay_method="Santosh Notebook", preview={"message": f"Approve to delete notebook '{d['title']}'."},
                             action={"executor": "notebook", "pack_id": pack.id, "name": "delete", "args": {"notebook": d["id"]}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...notebook import service as ns
        if action != "delete":
            raise ToolError(f"Unknown action {action}")
        try:
            return {"message": f"Notebook '{ns.delete(ctx.user.id, args['notebook'])}' delete kar di."}
        except ns.NotebookError as e:
            raise ToolError(str(e))
