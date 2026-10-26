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
                raise ToolError("Kaunsi emails delete karni hain? ids do.")
            if len(ids) > MAX_DELETE:
                raise ToolError(f"Ek baar mein {MAX_DELETE} se zyada emails delete nahi.")
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
                items.append({"name": f"+ {len(ids) - 5} aur emails"})
            if forever:
                items.append({"name": "HAMESHA KE LIYE delete hongi — Trash mein bhi nahi milengi, wapas NAHI aayengi."})
                items.append({"name": "Pakka? Agar shak ho to forever ke bina wahi delete Trash mein jaati (30 din tak wapas la sakte hain)."})
            else:
                items.append({"name": "Trash mein jayengi (30 din tak wapas la sakte hain)."})
            title = (f"{len(ids)} email HAMESHA KE LIYE delete karein?" if forever
                     else f"{len(ids)} email delete karein?")
            return NeedsApproval(tier=2, title=title, payee="Email", amount_paise=0,
                                 items=items, pay_method="Santosh Email",
                                 preview={"message": (f"Approve to permanently delete {len(ids)} email(s) — no Trash."
                                                      if forever else f"Approve to move {len(ids)} email(s) to Trash.")},
                                 action={"executor": "mail", "pack_id": pack.id,
                                         "name": ("delete_forever" if forever else "delete"), "args": {"ids": ids}})
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
        if tool == "confirm_draft_send":
            did = str(args.get("id") or "").strip()
            if not did:
                raise ToolError("Kaunsa draft? id do (email_drafts list se).")
            try:
                v = ms.gmail_draft_view(tenant, did, str(args.get("account") or "") or None)
            except MailError as e:
                raise ToolError(str(e))
            items = [{"name": f"Kiske liye: {v['to'][:90]}"}]
            if v.get("cc"):
                items.append({"name": f"Cc: {v['cc'][:90]}"})
            items.append({"name": f"Vishay: {v['subject'][:90]}"})
            items.append({"name": (v.get("body") or "")[:240] + ("…" if len(v.get("body") or "") > 240 else "")})
            if v.get("attachments"):
                items.append({"name": "Attachments: " + ", ".join(v["attachments"])[:120]})
            items.append({"name": "Yeh Gmail ke Drafts folder wala draft seedha BHEJEGI — baad mein undo nahi hoga."})
            return NeedsApproval(tier=2, title="Yeh Gmail draft bhejein?", payee=v.get("account") or "Gmail",
                                 amount_paise=0, items=items, pay_method="Santosh Email",
                                 preview={"message": f"Approve to send the Gmail draft '{v['subject'][:60]}'."},
                                 action={"executor": "mail", "pack_id": pack.id, "name": "draft_send",
                                         "args": {"id": did, "account": str(args.get("account") or "")}})
        if tool == "confirm_alias_delete":
            em = str(args.get("email") or "").strip().lower()
            if not em:
                raise ToolError("Kaunsa alias? email do (email_alias list se).")
            me = ms.alias_find(tenant, em, str(args.get("account") or "") or None)
            if me is None:
                raise ToolError(f"'{em}' naam ka alias is Gmail mein nahi hai.")
            if me.get("isPrimary"):
                raise ToolError("Primary address kabhi hat nahi sakta — woh khud Gmail ka login hai.")
            return NeedsApproval(tier=2, title=f"Alias '{em}' hatayein?", payee="Gmail", amount_paise=0,
                                 items=[{"name": f"Gmail ka send-as alias '{em}' hata degi."},
                                        {"name": "Is address se ab mail nahi bhej paayengi (purane mails waise hi hain)."},
                                        {"name": "Dobara jodna ho to email_alias action='add' se hoga."}],
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
                raise ToolError("Vacation reply sirf Gmail mailbox ki setting hai.")
            if enable and not message:
                raise ToolError("Vacation reply ON karne ke liye message do (wahi sabko auto-jawab jayega).")
            items = [{"name": ("Vacation auto-reply ON hoga" if enable else "Vacation auto-reply BAND hoga")
                           + f" — {box.address}"}]
            if enable:
                items.append({"name": "Auto-jawab: " + (message[:220] + ("…" if len(message) > 220 else ""))})
                if str(args.get("subject") or "").strip():
                    items.append({"name": f"Vishay: {str(args['subject']).strip()[:80]}"})
                window = "Abhi se" if not str(args.get("start") or "").strip() else f"{args['start']} se"
                if str(args.get("end") or "").strip():
                    window += f" {args['end']} tak"
                else:
                    window += ", band karne tak"
                items.append({"name": window})
                if args.get("contacts_only"):
                    items.append({"name": "Sirf saved contacts ko jawab jayega."})
                items.append({"name": "Gmail aane wali HAR mail ko yeh jawab bhejega (ek baar hi, har sender ko)."})
            else:
                items.append({"name": "Aane wali mails par ab koi auto-jawab nahi jayega."})
            if not settings_scope_ok(tenant, box):
                items.append({"name": "(Pehle is Gmail ko ek baar dobara jodna hoga — Profile > Email; mail pehle jaisa "
                                      "chalega.)"})
            return NeedsApproval(tier=2, title="Vacation reply " + ("chalu karein?" if enable else "band karein?"),
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
                raise ToolError("Is mailbox ka signature khaali hai — pehle email_accounts signature='...' se set kijiye.")
            return NeedsApproval(tier=2, title="Signature Gmail mein daalein?", payee="Gmail", amount_paise=0,
                                 items=[{"name": f"{box.address} ka Gmail signature badlega:"},
                                        {"name": sig[:220] + ("…" if len(sig) > 220 else "")},
                                        {"name": "(Gmail web + Gmail app, sab jagah yahi dikhega.)"}],
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
                raise ToolError("Auto-forward sirf Gmail mailbox ki setting hai.")
            if enable:
                from ...mailbox import contacts
                if not to or not contacts.valid(to):
                    raise ToolError("Forward kis address par? Sahi email do.")
            items = ([{"name": f"{box.address} ki har nayi mail {to} par bhi jayegi (Gmail ka apna auto-forward)."},
                      {"name": "Gmail inbox mein mail rakhta hai (copy ke saath)."},
                      {"name": "Yeh Gmail ki apni setting hai — Gmail web ke Forwarding mein bhi dikhegi."}]
                     if enable else
                     [{"name": f"{box.address} ka auto-forward band hoga."},
                      {"name": "Aane wali mails sirf is mailbox mein aayengi."}])
            return NeedsApproval(tier=2, title="Auto-forward " + ("chalu karein?" if enable else "band karein?"),
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
                return {"message": f"{n} email Trash mein daal di."}
            if action == "delete_forever":
                n = ms.delete_forever(tenant, list(args["ids"]))
                return {"message": f"{n} email hamesha ke liye delete kar di (Trash mein bhi nahi)."}
            if action == "draft_send":
                out = ms.send_gmail_draft(tenant, str(args.get("id") or ""), str(args.get("account") or "") or None)
                return {"message": out["note"]}
            if action == "alias_delete":
                out = ms.alias_op(tenant, "remove", str(args.get("email") or ""), account=str(args.get("account") or "") or None)
                return {"message": out["note"]}
            if action == "bulk_send":
                out = ms.start_bulk(tenant, args["bulk_id"])
                return {"message": f"{out.get('total', '')} logon ko email bhejna shuru kar diya.".strip()}
            if action == "label_delete":
                ms.label_op(tenant, "delete", str(args.get("name") or ""))
                return {"message": "Label hata di (mails waisi hi padi hain)."}
            if action == "draft_delete":
                ms.delete_gmail_draft(tenant, str(args.get("id") or ""))
                return {"message": "Gmail ka draft hata diya."}
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
