"""Confirm cards for Google Drive changes that reach other people or are hard to undo: sharing a file, making a
public link, moving files to Trash. Card text and what runs after the tap come from the stored change, never from
model text."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec

TITLES = {"share": "File share karein?", "public": "Public link banayein?", "trash": "Trash mein daalein?"}
ROLE = {"reader": "sirf dekh sakenge", "commenter": "comment kar sakenge", "writer": "badal (edit) bhi sakenge"}


class DriveExecutor:
    name = "drive"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_change", "Ask the user to approve a prepared Google Drive change.",
                         {"type": "object", "properties": {"pending_id": {"type": "string"}}, "required": ["pending_id"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...drive import service as ds
        if tool != "confirm_change":
            raise ToolError(f"Unknown tool {tool}")
        p = ds.pending(ctx.user.id, str(args.get("pending_id", "")))
        if p is None or p["status"] != "pending":
            raise ToolError("Yeh Drive badlav taiyaar nahi hai; dobara boliye.")
        sm, act = p["summary"], p["action"]
        if act == "share":
            items = [{"name": f"{sm['type']}: {sm['name']}"},
                     {"name": "Kisko: " + ", ".join(sm["people"])[:200]},
                     {"name": f"Woh {ROLE.get(sm['role'], sm['role'])}; unhe Google se email jayega."}]
        elif act == "public":
            items = [{"name": f"{sm['type']}: {sm['name']}"},
                     {"name": "Link wala koi bhi ise dekh sakega (bina login)."}]
        else:
            names = sm.get("names") or []
            items = [{"name": n} for n in names[:6]]
            if len(names) > 6:
                items.append({"name": f"+ {len(names) - 6} aur"})
            if sm.get("folders"):
                items.append({"name": "Folder ke andar ki sab files bhi Trash mein jayengi."})
            items.append({"name": "30 din tak Drive ke Trash se wapas la sakte hain."})
        return NeedsApproval(tier=2, title=TITLES.get(act, "Drive badlav?"), payee="Google Drive", amount_paise=0,
                             items=items, pay_method="Santosh Drive",
                             preview={"message": f"Approve to {act} on Google Drive."},
                             action={"executor": "drive", "pack_id": pack.id, "name": "run", "args": {"pending_id": p["id"]}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...drive import service as ds
        from ...drive.client import DriveError
        if action != "run":
            raise ToolError(f"Unknown action {action}")
        try:
            return ds.run_pending(ctx.user.id, args["pending_id"])
        except DriveError as e:
            raise ToolError(str(e))
