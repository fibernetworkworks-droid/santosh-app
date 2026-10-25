"""Confirm cards for email actions that can't be taken back: deleting mail and bulk mail. What the card shows and what
runs after the tap is computed here from the mailbox and the stored bulk job, never from model text."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec

MAX_DELETE = 100


class MailExecutor:
    name = "mail"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [
            ToolSpec("confirm_delete", "Ask the user to approve moving these emails to Trash.",
                     {"type": "object", "properties": {"ids": {"type": "array", "items": {"type": "string"}}},
                      "required": ["ids"]}, 2),
            ToolSpec("confirm_bulk", "Ask the user to approve sending a prepared bulk email.",
                     {"type": "object", "properties": {"bulk_id": {"type": "string"}}, "required": ["bulk_id"]}, 2),
            ToolSpec("confirm_label_delete", "Ask the user to approve deleting a Gmail label (mails stay).",
                     {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, 2),
            ToolSpec("confirm_draft_delete", "Ask the user to approve deleting a draft saved in Gmail.",
                     {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}, 2),
        ]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...mailbox import service as ms
        from ...mailbox.base import MailError
        tenant = ctx.user.id
        if tool == "confirm_delete":
            ids = [str(i) for i in (args.get("ids") or []) if str(i).strip()]
            if not ids:
                raise ToolError("Kaunsi emails delete karni hain? ids do.")
            if len(ids) > MAX_DELETE:
                raise ToolError(f"Ek baar mein {MAX_DELETE} se zyada emails delete nahi.")
            items = []
            try:
                for ref in ids[:5]:
                    m = ms.read(tenant, ref, mark_seen=False)
                    items.append({"name": f"{m['from'][:40]}: {m['subject'][:70]}"})
            except MailError as e:
                raise ToolError(str(e))
            if len(ids) > 5:
                items.append({"name": f"+ {len(ids) - 5} aur emails"})
            items.append({"name": "Trash mein jayengi (30 din tak wapas la sakte hain)."})
            return NeedsApproval(tier=2, title=f"{len(ids)} email delete karein?", payee="Email", amount_paise=0,
                                 items=items, pay_method="Santosh Email",
                                 preview={"message": f"Approve to move {len(ids)} email(s) to Trash."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "delete", "args": {"ids": ids}})
        if tool == "confirm_bulk":
            v = ms.bulk_view(tenant, str(args.get("bulk_id", "")))
            if v is None or v["status"] != "pending":
                raise ToolError("Yeh bulk email taiyaar nahi hai (ya pehle hi chal chuka hai). email_bulk se dobara banaiye.")
            first = v["first"][0] if v["first"] else {"email": "", "fields": {}}
            items = [{"name": f"Vishay: {ms.render(v['subject'], first['fields'])[:90]}"},
                     {"name": f"Pehla: {first['email']}"},
                     {"name": ms.render(v["body"], first["fields"])[:300]}]
            if v["attachments"]:
                items.append({"name": "Attachment: " + ", ".join(v["attachments"])[:120]})
            from ...config import get_settings
            items.append({"name": f"Har vyakti ko alag email (kisi ko doosron ka address nahi dikhega), "
                                  f"~{get_settings().mail_bulk_per_minute} per minute."})
            return NeedsApproval(tier=2, title=f"{v['total']} logon ko email bhejein?", payee=v["source"] or "Email list",
                                 amount_paise=0, items=items, pay_method="Santosh Email",
                                 preview={"message": f"Approve to send '{v['subject'][:80]}' to {v['total']} people."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "bulk_send",
                                         "args": {"bulk_id": v["id"]}})
        if tool == "confirm_label_delete":
            name = str(args.get("name") or "").strip()
            if not name:
                raise ToolError("Kaunsa label? naam do.")
            return NeedsApproval(tier=2, title=f"Label '{name}' hatayein?", payee="Email", amount_paise=0,
                                 items=[{"name": f"Gmail label '{name}' delete hogi."},
                                        {"name": "Mails delete nahi hongi; sirf yeh label un par se hat jayegi."}],
                                 pay_method="Santosh Email",
                                 preview={"message": f"Approve to delete the label '{name}'."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "label_delete",
                                         "args": {"name": name}})
        if tool == "confirm_draft_delete":
            did = str(args.get("id") or "").strip()
            if not did:
                raise ToolError("Kaunsa draft? id do (email_drafts list se).")
            return NeedsApproval(tier=2, title="Gmail draft delete karein?", payee="Email", amount_paise=0,
                                 items=[{"name": "Yeh Gmail ke Drafts folder se hamesha ke liye hat jayega."},
                                        {"name": "(Gmail ke drafts Trash mein nahi jaate.)"}],
                                 pay_method="Santosh Email",
                                 preview={"message": "Approve to delete this draft from the Gmail Drafts folder."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "draft_delete",
                                         "args": {"id": did}})
        raise ToolError(f"Unknown tool {tool}")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...mailbox import service as ms
        from ...mailbox.base import MailError
        tenant = ctx.user.id
        try:
            if action == "delete":
                n = ms.trash(tenant, list(args["ids"]))
                return {"message": f"{n} email Trash mein daal di."}
            if action == "bulk_send":
                out = ms.start_bulk(tenant, args["bulk_id"])
                return {"message": f"{out.get('total', '')} logon ko email bhejna shuru kar diya.".strip()}
            if action == "label_delete":
                ms.label_op(tenant, "delete", str(args.get("name") or ""))
                return {"message": "Label hata di (mails waisi hi padi hain)."}
            if action == "draft_delete":
                ms.delete_gmail_draft(tenant, str(args.get("id") or ""))
                return {"message": "Gmail ka draft hata diya."}
        except MailError as e:
            raise ToolError(str(e))
        raise ToolError(f"Unknown action {action}")
