"""Confirm cards for Santosh PC Operator (Santosh using the user's PC): the step comes from the operator session
itself (never from model text) and runs only after the user taps Approve."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec


class PcOpExecutor:
    name = "pcop"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_step", "Ask the user to approve the step Santosh paused on while using their PC.",
                         {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...pc import operator
        if tool != "confirm_step":
            raise ToolError(f"Unknown tool {tool}")
        op = operator.get(ctx.user.id, str(args.get("session_id", "")))
        if op is None or not op.pending:
            raise ToolError("Santosh isn't waiting for an approval on the PC any more.")
        what = op.pending["what"]
        return NeedsApproval(
            tier=2, title=f"Mera PC: {what[:70]}", payee="Mera PC", amount_paise=0,
            items=[{"name": what}, {"name": f"Abhi PC par: {op.window or '-'}"},
                   {"name": "Santosh password, OTP aur payment kabhi nahi bharta."}],
            pay_method="Santosh on your PC", preview={"message": f"Approve to let Santosh do this on your PC: {what}"},
            action={"executor": "pcop", "pack_id": pack.id, "name": "approve_step",
                    "args": {"session_id": op.id, "pending_id": op.pending["id"]}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...pc import operator
        if action != "approve_step":
            raise ToolError(f"Unknown action {action}")
        if not operator.decide(ctx.user.id, args["session_id"], args["pending_id"], True):
            raise ToolError("That step expired; ask Santosh again.")
        return {"message": "Theek hai, PC par aage badh raha hoon."}
