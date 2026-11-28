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
          "comment": "Add comment?", "reply": "Add reply?", "comment_delete": "Delete comment?",
          # v0.999.186 DRIVE COMPLETE
          "replace": "Replace this file's contents?", "rev_restore": "Put the old version back?",
          "rev_delete": "Remove this version?", "team_delete": "Remove this shared drive?",
          "member_add": "Add to the shared drive?", "member_remove": "Remove from the shared drive?",
          "member_role": "Change their role?", "request_accept": "Give access?", "request_deny": "Decline the request?",
          # v0.999.192 GOOGLE DOCS COMPLETE
          "doc_delete": "Delete this part of the document?", "doc_rewrite": "Rewrite this part of the document?",
          "doc_tab_del": "Delete this tab?", "doc_comment": "Add this comment?", "doc_reply": "Add this reply?",
          "doc_cmt_del": "Delete this comment?", "doc_reply_del": "Delete this reply?", "doc_sugg_all": "Change all these suggestions?"}
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
        if act.startswith("doc_"):
            items = [{"name": str(x)[:200]} for x in sm.get("lines") or [sm.get("name", "")]]
        elif act == "share":
            items = [{"name": f"{sm['type']}: {sm['name']}"},
                     {"name": "To: " + ", ".join(sm["people"])[:200]},
                     {"name": f"They {ROLE.get(sm['role'], sm['role'])}; " +
                              ("Google will not email them." if sm.get("quiet") else "Google will email them.")}]
            if sm.get("expires"):
                items.append({"name": f"Their access ends on {sm['expires']}."})
        elif act == "public":
            what = {"reader": "view", "commenter": "comment on", "writer": "EDIT"}.get(sm.get("role") or "reader", "view")
            items = [{"name": f"{sm['type']}: {sm['name']}"},
                     {"name": f"Anyone with the link can {what} it (no sign-in needed)."}]
            if sm.get("discoverable"):
                items.append({"name": "People can also find it by searching the web / Google."})
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
                     {"name": "You will stay an editor; getting ownership back needs a separate step."},
                     {"name": "For a personal Google account, Google first asks them to accept."}]
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
        elif act == "replace":
            items = [{"name": f"File: {sm['name']}"}, {"name": f"New contents: {sm['new']} ({sm.get('size', '')})"},
                     {"name": "Link, sharing and comments stay; the old contents stay in its version history."}]
        elif act == "rev_restore":
            items = [{"name": f"File: {sm['name']}"}, {"name": f"Version of {sm['when']} becomes the current one."},
                     {"name": "The newer versions stay in its history."}]
        elif act == "rev_delete":
            items = [{"name": f"File: {sm['name']}"}, {"name": f"Version of {sm['when']}"},
                     {"name": "This version will be removed forever."}]
        elif act == "team_delete":
            items = [{"name": f"Shared drive: {sm['name']}"}, {"name": "It is empty; it will be removed for every member."}]
        elif act in ("member_add", "member_remove", "member_role"):
            items = [{"name": f"Shared drive: {sm['name']}"}, {"name": "Who: " + ", ".join(sm["people"])[:200]}]
            if act == "member_add":
                items.append({"name": f"As {sm['role']}; they will see every file in it."})
            elif act == "member_role":
                items.append({"name": f"New role: {sm['role']}."})
            else:
                items.append({"name": "They lose access to every file in it."})
        elif act in ("request_accept", "request_deny"):
            items = [{"name": f"File: {sm['name']}"}, {"name": "From: " + ", ".join(sm["people"])[:200]}]
            items.append({"name": f"They {ROLE.get(sm.get('role', ''), sm.get('role', ''))}; Google emails them."
                          if act == "request_accept" else "Google tells them it was declined."})
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
