"""UPI intent links (NPCI deep-link spec). Santosh fills payee, amount and note; the user enters the PIN in their UPI app.

Santosh never sees, stores or types a UPI PIN.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urlencode

from sqlalchemy import select

from ..db import Contact, Transaction
from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec, rupees, to_paise

VPA_RE = re.compile(r"^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z][a-zA-Z0-9.\-]{1,64}$")


def valid_vpa(vpa: str) -> bool:
    return bool(VPA_RE.match(vpa or ""))


def build_upi_intent(pa: str, pn: str, amount_paise: int, note: str = "", tr: str = "",
                     scheme: str = "upi", max_paise: int = 10_000_000) -> str:
    if not valid_vpa(pa):
        raise ToolError(f"'{pa}' is not a valid UPI ID")
    if amount_paise <= 0:
        raise ToolError("Amount must be more than ₹0")
    if amount_paise > max_paise:
        raise ToolError(f"Amount is above the UPI limit of {rupees(max_paise)}")
    params = {"pa": pa, "pn": pn[:50] or pa, "am": f"{amount_paise / 100:.2f}", "cu": "INR"}
    if note:
        params["tn"] = note[:80]
    if tr:
        params["tr"] = tr[:35]
    base = {"upi": "upi://pay", "tez": "tez://upi/pay", "phonepe": "phonepe://pay", "paytmmp": "paytmmp://pay"}.get(scheme, "upi://pay")
    return base + "?" + urlencode(params, quote_via=quote)


class UpiExecutor:
    name = "upi"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [
            ToolSpec("send_money", f"Prepare a UPI payment in {pack.name}. Give either a saved contact name or a UPI ID, the amount in rupees and an optional note. "
                     "The user approves and enters their PIN in the UPI app.",
                     {"type": "object", "properties": {
                         "to": {"type": "string", "description": "Contact name or UPI ID"},
                         "amount_rupees": {"type": "number"},
                         "note": {"type": "string"}}, "required": ["to", "amount_rupees"]}, 3),
            ToolSpec("request_money", "Create a UPI payment link the user can share to collect money from someone.",
                     {"type": "object", "properties": {
                         "amount_rupees": {"type": "number"}, "note": {"type": "string"},
                         "payee_vpa": {"type": "string", "description": "User's own UPI ID to receive the money"}},
                      "required": ["amount_rupees", "payee_vpa"]}, 1),
        ]

    def _resolve(self, ctx: Ctx, to: str) -> tuple[str, str]:
        to = to.strip()
        if valid_vpa(to):
            return to, to.split("@")[0]
        c = ctx.session.scalars(select(Contact).where(Contact.user_id == ctx.user.id)).all()
        hits = [x for x in c if to.lower() in x.name.lower() or x.name.lower() in to.lower()]
        if not hits:
            raise ToolError(f"I couldn't find '{to}' in your saved contacts. Share their UPI ID once and I'll remember it.")
        if len(hits) > 1:
            raise ToolError("More than one contact matches: " + ", ".join(h.name for h in hits) + ". Which one?")
        if not hits[0].upi_id:
            raise ToolError(f"I have {hits[0].name} saved but not their UPI ID.")
        return hits[0].upi_id, hits[0].name

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        cap = ctx.settings.upi_max_amount_paise
        if tool == "send_money":
            vpa, name = self._resolve(ctx, str(args.get("to", "")))
            paise = to_paise(args.get("amount_rupees"))
            build_upi_intent(vpa, name, paise, max_paise=cap)  # validate now
            return NeedsApproval(
                tier=3, title=f"Send {rupees(paise)} to {name}", payee=f"{name} ({vpa})", amount_paise=paise,
                items=[{"name": args.get("note") or "UPI transfer", "price_paise": paise}],
                pay_method=f"UPI PIN in {pack.name}",
                action={"executor": "upi", "pack_id": pack.id, "name": "open_upi_app",
                        "args": {"vpa": vpa, "name": name, "amount_paise": paise, "note": str(args.get("note", ""))}})
        if tool == "request_money":
            paise = to_paise(args.get("amount_rupees"))
            vpa = str(args.get("payee_vpa", ""))
            link = build_upi_intent(vpa, ctx.user.name or vpa, paise, str(args.get("note", "")), max_paise=cap)
            return {"payment_link": link, "amount": rupees(paise), "share_text": f"Please pay {rupees(paise)} here: {link}"}
        raise ToolError(f"Unknown tool {tool}")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        if action != "open_upi_app":
            raise ToolError(f"Unknown action {action}")
        txn = Transaction(user_id=ctx.user.id, task_id=ctx.task.id if ctx.task else "", kind="upi", provider=pack.id,
                          amount_paise=args["amount_paise"], status="awaiting_payment",
                          meta={"vpa": args["vpa"], "name": args["name"], "app": pack.name,
                                "package": pack.config.get("android_package") or ""})
        ctx.session.add(txn)
        ctx.session.flush()
        pkg = pack.config.get("android_package") or ""
        from ..upiresult import link_blocked
        if link_blocked(ctx.user, pkg):
            # v0.120 this app refuses payment links to a person ("security reasons"): open the app itself, the phone
            # copies the UPI ID, she pastes it and types the amount there. Same record, same Ho gaya / Nahi hua card.
            txn.meta = {**(txn.meta or {}), "mode": "copy"}
            amt = rupees(args["amount_paise"])
            return {"status": "copy_pay", "android_package": pkg, "txn_ref": txn.txn_ref, "vpa": args["vpa"],
                    "payee_name": args["name"], "amount": amt, "app": pack.name,
                    "message": (f"{pack.name} kisi vyakti ko link se payment rok deta hai, isliye {pack.name} seedha khul "
                                f"raha hai. {args['name']} ka UPI ID ({args['vpa']}) copy ho gaya hai: 'To UPI ID' mein paste "
                                f"karke {amt} bhejiye, PIN wahin daaliye. Ho jaane par yahan 'Ho gaya' dabaiye.")}
        link = build_upi_intent(args["vpa"], args["name"], args["amount_paise"], args.get("note", ""), tr=txn.txn_ref,
                                scheme=pack.config.get("scheme", "upi"), max_paise=ctx.settings.upi_max_amount_paise)
        return {"status": "open_app", "intent_url": link, "android_package": pack.config.get("android_package"),
                "txn_ref": txn.txn_ref, "vpa": args["vpa"], "payee_name": args["name"], "amount": rupees(args["amount_paise"]),
                "message": f"{pack.name} khul raha hai: {args['name']} aur {rupees(args['amount_paise'])} bhare hue honge. "
                           f"UPI PIN wahin daaliye; ho jaane par Hoola yahan bata dega."}
