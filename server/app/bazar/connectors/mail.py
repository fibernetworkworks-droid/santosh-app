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
            ToolSpec("confirm_delete", "Ask the user to approve moving these emails to Trash (or, with forever=true, "
                     "deleting them PERMANENTLY — no Trash).",
                     {"type": "object", "properties": {"ids": {"type": "array", "items": {"type": "string"}},
                                                       "forever": {"type": "boolean"}},
                      "required": ["ids"]}, 2),
            ToolSpec("confirm_bulk", "Ask the user to approve sending a prepared bulk email.",
                     {"type": "object", "properties": {"bulk_id": {"type": "string"}}, "required": ["bulk_id"]}, 2),
            ToolSpec("confirm_label_delete", "Ask the user to approve deleting a Gmail label (mails stay).",
                     {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, 2),
            ToolSpec("confirm_draft_delete", "Ask the user to approve deleting a draft saved in Gmail.",
                     {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}, 2),
            ToolSpec("confirm_vacation", "Ask the user to approve switching the Gmail vacation auto-reply on or off.",
                     {"type": "object", "properties": {"enable": {"type": "boolean"}, "message": {"type": "string"},
                                                        "subject": {"type": "string"}, "start": {"type": "string"},
                                                        "end": {"type": "string"},
                                                        "contacts_only": {"type": "boolean"},
                                                        "account": {"type": "string"}}, "required": ["enable"]}, 2),
            ToolSpec("confirm_signature_push", "Ask the user to approve pushing the mailbox signature into Gmail.",
                     {"type": "object", "properties": {"account": {"type": "string"}, "signature": {"type": "string"}},
                      "required": ["account"]}, 2),
            ToolSpec("confirm_auto_forward", "Ask the user to approve changing Gmail's own auto-forwarding.",
                     {"type": "object", "properties": {"enable": {"type": "boolean"}, "to": {"type": "string"},
                                                        "account": {"type": "string"}}, "required": ["enable"]}, 2),
            ToolSpec("confirm_draft_send", "Ask the user to approve SENDING the draft that already sits in Gmail.",
                     {"type": "object", "properties": {"id": {"type": "string"}, "account": {"type": "string"}},
                      "required": ["id"]}, 2),
            ToolSpec("confirm_alias_delete", "Ask the user to approve removing a Gmail send-as alias (the primary never).",
                     {"type": "object", "properties": {"email": {"type": "string"}, "account": {"type": "string"}},
                      "required": ["email"]}, 2),
        ]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...mailbox import service as ms
        from ...mailbox.base import MailError
        tenant = ctx.user.id
        if tool == "confirm_delete":
            ids = [str(i) for i in (args.get("ids") or []) if str(i).strip()]
            forever = bool(args.get("forever"))
            if not ids:
                raise ToolError("Which emails should be deleted? Give the ids.")
            if len(ids) > MAX_DELETE:
                raise ToolError(f"No more than {MAX_DELETE} emails can be deleted at once.")
            items = []
            try:
                for ref in ids[:5]:
                    # learn_contacts=False: this runs INSIDE the bazar transaction - a nested write on SQLite
                    # locked the whole DB ("database is locked") whenever the mail was from a real person.
                    m = ms.read(tenant, ref, mark_seen=False, learn_contacts=False)
                    items.append({"name": f"{m['from'][:40]}: {m['subject'][:70]}"})
            except MailError as e:
                raise ToolError(str(e))
            if len(ids) > 5:
                items.append({"name": f"+ {len(ids) - 5} more emails"})
            if forever:
                items.append({"name": "They will be deleted FOREVER — not even in Trash, and they will NOT come back."})
                items.append({"name": "Sure? If in doubt, the same delete without 'forever' moves them to Trash (you can bring them back for 30 days)."})
            else:
                items.append({"name": "They will go to Trash (you can bring them back for 30 days)."})
            title = (f"Delete {len(ids)} email(s) FOREVER?" if forever
                     else f"Delete {len(ids)} email(s)?")
            return NeedsApproval(tier=2, title=title, payee="Email", amount_paise=0,
                                 items=items, pay_method="Santosh Email",
                                 preview={"message": (f"Approve to permanently delete {len(ids)} email(s) — no Trash."
                                                      if forever else f"Approve to move {len(ids)} email(s) to Trash.")},
                                 action={"executor": "mail", "pack_id": pack.id,
                                         "name": ("delete_forever" if forever else "delete"), "args": {"ids": ids}})
        if tool == "confirm_bulk":
            v = ms.bulk_view(tenant, str(args.get("bulk_id", "")))
            if v is None or v["status"] != "pending":
                raise ToolError("This bulk email is not ready (or has already run). Create it again with email_bulk.")
            first = v["first"][0] if v["first"] else {"email": "", "fields": {}}
            items = [{"name": f"Subject: {ms.render(v['subject'], first['fields'])[:90]}"},
                     {"name": f"First: {first['email']}"},
                     {"name": ms.render(v["body"], first["fields"])[:300]}]
            if v["attachments"]:
                items.append({"name": "Attachment: " + ", ".join(v["attachments"])[:120]})
            from ...config import get_settings
            items.append({"name": f"Each person gets a separate email (nobody sees anyone else's address), "
                                  f"~{get_settings().mail_bulk_per_minute} per minute."})
            return NeedsApproval(tier=2, title=f"Send email to {v['total']} people?", payee=v["source"] or "Email list",
                                 amount_paise=0, items=items, pay_method="Santosh Email",
                                 preview={"message": f"Approve to send '{v['subject'][:80]}' to {v['total']} people."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "bulk_send",
                                         "args": {"bulk_id": v["id"]}})
        if tool == "confirm_label_delete":
            name = str(args.get("name") or "").strip()
            if not name:
                raise ToolError("Which label? Give the name.")
            return NeedsApproval(tier=2, title=f"Delete label '{name}'?", payee="Email", amount_paise=0,
                                 items=[{"name": f"The Gmail label '{name}' will be deleted."},
                                        {"name": "No emails will be deleted; only this label will be removed from them."}],
                                 pay_method="Santosh Email",
                                 preview={"message": f"Approve to delete the label '{name}'."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "label_delete",
                                         "args": {"name": name}})
        if tool == "confirm_draft_delete":
            did = str(args.get("id") or "").strip()
            if not did:
                raise ToolError("Which draft? Give the id (from the email_drafts list).")
            return NeedsApproval(tier=2, title="Delete Gmail draft?", payee="Email", amount_paise=0,
                                 items=[{"name": "This will be removed from the Gmail Drafts folder forever."},
                                        {"name": "(Gmail drafts do not go to Trash.)"}],
                                 pay_method="Santosh Email",
                                 preview={"message": "Approve to delete this draft from the Gmail Drafts folder."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "draft_delete",
                                         "args": {"id": did}})
        if tool == "confirm_draft_send":
            did = str(args.get("id") or "").strip()
            if not did:
                raise ToolError("Which draft? Give the id (from the email_drafts list).")
            try:
                v = ms.gmail_draft_view(tenant, did, str(args.get("account") or "") or None)
            except MailError as e:
                raise ToolError(str(e))
            items = [{"name": f"To: {v['to'][:90]}"}]
            if v.get("cc"):
                items.append({"name": f"Cc: {v['cc'][:90]}"})
            items.append({"name": f"Subject: {v['subject'][:90]}"})
            items.append({"name": (v.get("body") or "")[:240] + ("…" if len(v.get("body") or "") > 240 else "")})
            if v.get("attachments"):
                items.append({"name": "Attachments: " + ", ".join(v["attachments"])[:120]})
            items.append({"name": "This will SEND the draft from the Gmail Drafts folder right away — it cannot be undone."})
            return NeedsApproval(tier=2, title="Send this Gmail draft?", payee=v.get("account") or "Gmail",
                                 amount_paise=0, items=items, pay_method="Santosh Email",
                                 preview={"message": f"Approve to send the Gmail draft '{v['subject'][:60]}'."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "draft_send",
                                         "args": {"id": did, "account": str(args.get("account") or "")}})
        if tool == "confirm_alias_delete":
            em = str(args.get("email") or "").strip().lower()
            if not em:
                raise ToolError("Which alias? Give the email (from the email_alias list).")
            me = ms.alias_find(tenant, em, str(args.get("account") or "") or None)
            if me is None:
                raise ToolError(f"There is no alias '{em}' in this Gmail.")
            if me.get("isPrimary"):
                raise ToolError("The primary address can never be removed — it is the Gmail login itself.")
            return NeedsApproval(tier=2, title=f"Remove alias '{em}'?", payee="Gmail", amount_paise=0,
                                 items=[{"name": f"The Gmail send-as alias '{em}' will be removed."},
                                        {"name": "You will no longer be able to send mail from this address (old mails stay as they are)."},
                                        {"name": "To add it back, use email_alias action='add'."}],
                                 pay_method="Santosh Email",
                                 preview={"message": f"Approve to remove the send-as alias '{em}'."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "alias_delete",
                                         "args": {"email": em, "account": str(args.get("account") or "")}})
        if tool == "confirm_vacation":
            from ...mailbox.accounts import get_box, settings_scope_ok
            enable = bool(args.get("enable"))
            message = str(args.get("message") or "").strip()
            account = str(args.get("account") or "").strip() or None
            try:
                box = get_box(tenant, account)
            except MailError as e:
                raise ToolError(str(e))
            if box.kind != "gmail":
                raise ToolError("Vacation reply is a setting for Gmail mailboxes only.")
            if enable and not message:
                raise ToolError("To turn the vacation reply ON, give a message (that is the auto-reply everyone will get).")
            items = [{"name": ("Vacation auto-reply will be turned ON" if enable else "Vacation auto-reply will be turned OFF")
                           + f" — {box.address}"}]
            if enable:
                items.append({"name": "Auto-reply: " + (message[:220] + ("…" if len(message) > 220 else ""))})
                if str(args.get("subject") or "").strip():
                    items.append({"name": f"Subject: {str(args['subject']).strip()[:80]}"})
                window = "From now" if not str(args.get("start") or "").strip() else f"From {args['start']}"
                if str(args.get("end") or "").strip():
                    window += f" until {args['end']}"
                else:
                    window += ", until turned off"
                items.append({"name": window})
                if args.get("contacts_only"):
                    items.append({"name": "Only saved contacts will get a reply."})
                items.append({"name": "Gmail will send this reply to EVERY incoming mail (only once per sender)."})
            else:
                items.append({"name": "Incoming mails will no longer get an auto-reply."})
            if not settings_scope_ok(tenant, box):
                items.append({"name": "(You will first need to reconnect this Gmail once — Profile > Email; mail keeps working as before.)"})
            return NeedsApproval(tier=2, title="Turn vacation reply " + ("on?" if enable else "off?"),
                                 payee="Gmail", amount_paise=0, items=items, pay_method="Santosh Email",
                                 preview={"message": ("Approve to switch the vacation auto-reply "
                                                      + ("ON." if enable else "OFF."))},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "vacation_set",
                                         "args": {"enable": enable, "message": message,
                                                  "subject": str(args.get("subject") or ""),
                                                  "start": str(args.get("start") or ""),
                                                  "end": str(args.get("end") or ""),
                                                  "contacts_only": bool(args.get("contacts_only")),
                                                  "account": box.key}})
        if tool == "confirm_signature_push":
            from ...mailbox.accounts import get_box
            try:
                box = get_box(tenant, str(args.get("account") or "") or None)
            except MailError as e:
                raise ToolError(str(e))
            sig = (str(args.get("signature") or "").strip() or (box.signature or "").strip())
            if not sig:
                raise ToolError("This mailbox has no signature — set one first with email_accounts signature='...'.")
            return NeedsApproval(tier=2, title="Put signature into Gmail?", payee="Gmail", amount_paise=0,
                                 items=[{"name": f"The Gmail signature for {box.address} will change to:"},
                                        {"name": sig[:220] + ("…" if len(sig) > 220 else "")},
                                        {"name": "(It will show everywhere: Gmail web and the Gmail app.)"}],
                                 pay_method="Santosh Email",
                                 preview={"message": "Approve to push this signature into Gmail itself."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "signature_push",
                                         "args": {"account": box.key}})
        if tool == "confirm_auto_forward":
            from ...mailbox.accounts import get_box
            enable = bool(args.get("enable"))
            to = str(args.get("to") or "").strip().lower()
            try:
                box = get_box(tenant, str(args.get("account") or "") or None)
            except MailError as e:
                raise ToolError(str(e))
            if box.kind != "gmail":
                raise ToolError("Auto-forward is a setting for Gmail mailboxes only.")
            if enable:
                from ...mailbox import contacts
                if not to or not contacts.valid(to):
                    raise ToolError("Forward to which address? Give a valid email.")
            items = ([{"name": f"Every new mail to {box.address} will also go to {to} (Gmail's own auto-forward)."},
                      {"name": "Gmail keeps the mail in the inbox (a copy is forwarded)."},
                      {"name": "This is Gmail's own setting — it will also show in Gmail web under Forwarding."}]
                     if enable else
                     [{"name": f"Auto-forward for {box.address} will be turned off."},
                      {"name": "Incoming mails will arrive only in this mailbox."}])
            return NeedsApproval(tier=2, title="Turn auto-forward " + ("on?" if enable else "off?"),
                                 payee="Gmail", amount_paise=0, items=items, pay_method="Santosh Email",
                                 preview={"message": ("Approve to switch auto-forwarding "
                                                      + (f"ON to {to}." if enable else "OFF."))},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "auto_forward_set",
                                         "args": {"enable": enable, "to": to, "account": box.key}})
        raise ToolError(f"Unknown tool {tool}")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...mailbox import service as ms
        from ...mailbox.base import MailError
        tenant = ctx.user.id
        try:
            if action == "delete":
                n = ms.trash(tenant, list(args["ids"]))
                return {"message": f"Moved {n} email(s) to Trash."}
            if action == "delete_forever":
                n = ms.delete_forever(tenant, list(args["ids"]))
                return {"message": f"Deleted {n} email(s) forever (not even in Trash)."}
            if action == "draft_send":
                out = ms.send_gmail_draft(tenant, str(args.get("id") or ""), str(args.get("account") or "") or None)
                return {"message": out["note"]}
            if action == "alias_delete":
                out = ms.alias_op(tenant, "remove", str(args.get("email") or ""), account=str(args.get("account") or "") or None)
                return {"message": out["note"]}
            if action == "bulk_send":
                out = ms.start_bulk(tenant, args["bulk_id"])
                return {"message": f"Started sending email to {out.get('total', '')} people.".strip()}
            if action == "label_delete":
                ms.label_op(tenant, "delete", str(args.get("name") or ""))
                return {"message": "Label removed (the mails are untouched)."}
            if action == "draft_delete":
                ms.delete_gmail_draft(tenant, str(args.get("id") or ""))
                return {"message": "Gmail draft deleted."}
            if action == "vacation_set":
                out = ms.vacation_set(tenant, str(args.get("account") or "") or None, bool(args.get("enable")),
                                      str(args.get("message") or ""), str(args.get("subject") or ""),
                                      str(args.get("start") or "") or None, str(args.get("end") or "") or None,
                                      bool(args.get("contacts_only")))
                return {"message": out["note"]}
            if action == "signature_push":
                out = ms.signature_push(tenant, str(args.get("account") or "") or None, "")
                return {"message": out["note"]}
            if action == "auto_forward_set":
                out = ms.auto_forwarding_set(tenant, str(args.get("account") or "") or None, bool(args.get("enable")),
                                             str(args.get("to") or ""))
                return {"message": out["note"]}
        except MailError as e:
            raise ToolError(str(e))
        raise ToolError(f"Unknown action {action}")
