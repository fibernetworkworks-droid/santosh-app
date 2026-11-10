"""Confirm cards for Google Drive changes that reach other people or are hard to undo: sharing a file, making a
public link, moving files to Trash, taking access away (unshare / role change / ownership transfer), deleting files
forever, emptying the Trash, and writing or removing comments. Card text and what runs after the tap come from the
stored change, never from model text."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec

TITLES = {"share": "Share this file?", "public": "Create a public link?", "trash": "Move to Trash?",
          "unshare": "Remove sharing?", "role": "Change role?", "transfer": "Transfer ownership?",
          "delete": "Delete forever?", "empty_trash": "Empty the whole Trash?",
          "comment": "Add comment?", "reply": "Add reply?", "comment_delete": "Delete comment?"}
ROLE = {"reader": "can only view", "commenter": "can comment", "writer": "can edit"}


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
            raise ToolError("This Drive change is not ready; please ask again.")
        sm, act = p["summary"], p["action"]
        if act == "share":
            items = [{"name": f"{sm['type']}: {sm['name']}"},
                     {"name": "To: " + ", ".join(sm["people"])[:200]},
                     {"name": f"They {ROLE.get(sm['role'], sm['role'])}; Google will email them."}]
        elif act == "public":
            items = [{"name": f"{sm['type']}: {sm['name']}"},
                     {"name": "Anyone with the link can view it (no sign-in needed)."}]
        elif act == "unshare":
            items = [{"name": f"File: {sm['name']}"},
                     {"name": "Who to remove: " + ", ".join(sm["people"])[:200]},
                     {"name": "Nobody without permission will be able to open it by link." if sm.get("stop") == "sab"
                      else "After this they will not be able to open the file."}]
        elif act == "role":
            items = [{"name": f"File: {sm['name']}"},
                     {"name": "Who: " + ", ".join(sm["people"])[:200]},
                     {"name": f"New role: {ROLE.get(sm.get('role', ''), sm.get('role', ''))}."}]
        elif act == "transfer":
            items = [{"name": f"File: {sm['name']}"},
                     {"name": "New owner: " + ", ".join(sm["people"])[:200]},
                     {"name": "You will stay an editor; getting ownership back needs a separate step."}]
        elif act == "delete":
            names = sm.get("names") or []
            items = [{"name": n} for n in names[:6]]
            if len(names) > 6:
                items.append({"name": f"+ {len(names) - 6} more"})
            if sm.get("folders"):
                items.append({"name": "All files inside the folder will go too."})
            items.append({"name": "FOREVER — it will not come back from Trash either."})
        elif act == "empty_trash":
            items = [{"name": f"All of the Trash in {sm['name']}"},
                     {"name": "Every file in the Trash will be deleted forever."}]
        elif act == "comment":
            items = [{"name": f"{sm.get('type', 'File')}: {sm['name']}"},
                     {"name": "What it says: " + sm.get("content", "")[:200]},
                     {"name": "Google will email the people on the file."}]
        elif act == "reply":
            items = [{"name": "Replying to: " + sm.get("quoted", "")[:120]},
                     {"name": "What it says: " + sm.get("content", "")[:200]}]
        elif act == "comment_delete":
            items = [{"name": f"File: {sm['name']}"},
                     {"name": "Which comment: " + sm.get("quoted", "")[:150]},
                     {"name": "The comment will be removed forever."}]
        else:
            names = sm.get("names") or []
            items = [{"name": n} for n in names[:6]]
            if len(names) > 6:
                items.append({"name": f"+ {len(names) - 6} more"})
            if sm.get("folders"):
                items.append({"name": "All files inside the folder will go to Trash too."})
            items.append({"name": "You can bring them back from Drive Trash for 30 days."})
        return NeedsApproval(tier=2, title=TITLES.get(act, "Drive change?"), payee="Google Drive", amount_paise=0,
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
