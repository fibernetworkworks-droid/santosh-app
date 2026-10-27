"""Confirm cards for Google Forms changes that reach other people or lose answers: sharing edit access, deleting
questions that already have answers. Card text and the action come from the stored change, never from model text."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec

TITLES = {"share": "Form share karein?", "delete_questions": "Jawab wale sawaal hatayein?"}


class FormsExecutor:
    name = "forms"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_change", "Ask the user to approve a prepared Google Forms change.",
                         {"type": "object", "properties": {"pending_id": {"type": "string"}}, "required": ["pending_id"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...forms import service as fs
        if tool != "confirm_change":
            raise ToolError(f"Unknown tool {tool}")
        p = fs.pending(ctx.user.id, str(args.get("pending_id", "")))
        if p is None or p["status"] != "pending":
            raise ToolError("Yeh form badlav taiyaar nahi hai; dobara boliye.")
        sm = p["summary"]
        items = [{"name": f"Form: {sm.get('title', '')}"}, {"name": sm.get("what", "")}, {"name": sm.get("note", "")}]
        return NeedsApproval(tier=2, title=TITLES.get(p["action"], "Form badlav?"), payee="Google Forms", amount_paise=0,
                             items=[i for i in items if i["name"]], pay_method="Santosh Forms",
                             preview={"message": f"Approve to {p['action'].replace('_', ' ')} on '{sm.get('title', '')}'."},
                             action={"executor": "forms", "pack_id": pack.id, "name": "run", "args": {"pending_id": p["id"]}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...forms import service as fs
        from ...forms.client import FormError
        if action != "run":
            raise ToolError(f"Unknown action {action}")
        try:
            return fs.run_pending(ctx.user.id, args["pending_id"])
        except FormError as e:
            raise ToolError(str(e))
