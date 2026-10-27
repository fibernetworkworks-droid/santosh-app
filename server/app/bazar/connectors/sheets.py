"""Confirm cards for Google Sheets changes that are hard to undo or reach other people: deleting rows, editing many
rows at once, sharing a sheet. The card and the action come from the stored change, never from model text."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec

TITLES = {"update": "Itni rows badlein?", "delete": "Rows hatayein?", "share": "Sheet share karein?"}


class SheetsExecutor:
    name = "sheets"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_change", "Ask the user to approve a prepared Google Sheets change.",
                         {"type": "object", "properties": {"pending_id": {"type": "string"}}, "required": ["pending_id"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...sheets import service as ss
        if tool != "confirm_change":
            raise ToolError(f"Unknown tool {tool}")
        p = ss.pending(ctx.user.id, str(args.get("pending_id", "")))
        if p is None or p["status"] != "pending":
            raise ToolError("Yeh sheet badlav taiyaar nahi hai; dobara boliye.")
        sm = p["summary"]
        items = [{"name": f"{sm.get('title', '')} · {sm.get('tab', '')}".strip(" ·")}]
        for line in sm.get("lines", [])[:6]:
            items.append({"name": str(line)[:160]})
        if sm.get("more"):
            items.append({"name": f"+ {sm['more']} aur"})
        if sm.get("note"):
            items.append({"name": sm["note"][:200]})
        return NeedsApproval(tier=2, title=TITLES.get(p["action"], "Sheet badlein?"), payee="Google Sheets", amount_paise=0,
                             items=items, pay_method="Santosh Sheets",
                             preview={"message": f"Approve to {p['action']} in '{sm.get('title', '')}'."},
                             action={"executor": "sheets", "pack_id": pack.id, "name": "run", "args": {"pending_id": p["id"]}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...sheets import service as ss
        from ...sheets.client import SheetError
        if action != "run":
            raise ToolError(f"Unknown action {action}")
        try:
            return ss.run_pending(ctx.user.id, args["pending_id"])
        except SheetError as e:
            raise ToolError(str(e))
