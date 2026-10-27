"""Mera PC: the user's own computer running Santosh Desktop, reached through the PC bridge hub.

Reads (search, list, read, send to phone, Tally reports) run straight away. Printing and Tally entries are Tier 2:
the exact job is frozen in a confirm card and sent to the PC only after the user taps Approve.
"""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec

TALLY_REPORTS = ["companies", "ledgers", "receivables", "payables", "sales", "purchases", "receipts", "payments",
                 "daybook", "stock", "ledger"]

SCHEMAS: dict[str, tuple[str, dict[str, Any]]] = {
    "status": ("Is the PC online; its shared folders, Tally status and what is indexed.", {"type": "object", "properties": {}}),
    "search": ("Find files on the PC by name or content words (party name, invoice no, month, 'GST', 'bank statement'). "
               "Returns path, name, size, modified, category and a text snippet.",
               {"type": "object", "properties": {
                   "query": {"type": "string"},
                   "kind": {"type": "string", "enum": ["any", "pdf", "excel", "word", "image", "text", "tally"]},
                   "limit": {"type": "integer"}}, "required": ["query"]}),
    "list": ("List a folder on the PC (empty path = the shared folders).",
             {"type": "object", "properties": {"path": {"type": "string"}}}),
    "read": ("Read the text of a PC file (PDF, Word, Excel/CSV, text) to answer questions about it.",
             {"type": "object", "properties": {"path": {"type": "string"}, "max_chars": {"type": "integer"}}, "required": ["path"]}),
    "send_file": ("Send a PC file to the user's phone (a download card appears in the chat). Full quality, no compression.",
                  {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}),
    "save_file": ("Save a file the user sent from the phone into the PC's Santosh Inbox folder.",
                  {"type": "object", "properties": {"file_id": {"type": "string"}, "name": {"type": "string"}}, "required": ["file_id"]}),
    "print": ("Print a PC file on the PC's default printer (needs the user's tap).",
              {"type": "object", "properties": {"path": {"type": "string"}, "copies": {"type": "integer"}}, "required": ["path"]}),
    "tally_report": ("Read TallyPrime on the PC (read-only): companies, ledgers (with closing balance), receivables "
                     "(who owes, Sundry Debtors), payables (whom we owe), sales / purchases / receipts / payments vouchers "
                     "for a period, daybook (a date), stock (stock summary), ledger (one party's vouchers). Dates YYYY-MM-DD.",
                     {"type": "object", "properties": {
                         "report": {"type": "string", "enum": TALLY_REPORTS},
                         "from_date": {"type": "string"}, "to_date": {"type": "string"},
                         "party": {"type": "string"}, "company": {"type": "string"}}, "required": ["report"]}),
    "tally_voucher": ("Create a simple voucher in TallyPrime (needs the user's tap): Sales, Purchase, Receipt or Payment "
                      "between a party ledger and an account ledger (Sales/Purchase/Cash/Bank).",
                      {"type": "object", "properties": {
                          "voucher_type": {"type": "string", "enum": ["Sales", "Purchase", "Receipt", "Payment"]},
                          "party": {"type": "string"}, "amount": {"type": "number"},
                          "ledger": {"type": "string", "description": "Sales / Purchase / Cash / Bank ledger name"},
                          "date": {"type": "string", "description": "YYYY-MM-DD, default today"},
                          "narration": {"type": "string"}, "company": {"type": "string"}},
                      "required": ["voucher_type", "party", "amount", "ledger"]}),
}


def _call(ctx: Ctx, action: str, args: dict[str, Any]) -> dict[str, Any]:
    from ...pc.hub import PcError, PcOffline, hub
    try:
        return hub.call_sync(ctx.user.id, action, args)
    except PcOffline:
        raise ToolError("PC_OFFLINE: The PC is offline. Ask the user to switch it on and open Santosh Desktop "
                        "(or pair one: Santosh app > Main > Mera PC).")
    except PcError as e:
        raise ToolError(f"PC: {e}")


class PcExecutor:
    name = "pc"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec(t.name, SCHEMAS[t.name][0], SCHEMAS[t.name][1], t.tier) for t in pack.tools]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        if tool not in SCHEMAS:
            raise ToolError(f"Mera PC has no tool '{tool}'")
        if tool == "print":
            if not str(args.get("path") or "").strip():
                raise ToolError("Which file? Give its path from search.")
            copies = max(1, min(int(args.get("copies") or 1), 20))
            name = str(args["path"]).replace("\\", "/").split("/")[-1]
            return NeedsApproval(tier=2, title=f"PC par print: {name}", payee="Mera PC", amount_paise=0,
                                 items=[{"name": f"{name} × {copies}", "price_paise": None}], pay_method="PC ka printer",
                                 action={"executor": "pc", "pack_id": pack.id, "name": "print",
                                         "args": {"path": args["path"], "copies": copies}})
        if tool == "tally_voucher":
            try:
                amount = round(float(args.get("amount")), 2)
            except (TypeError, ValueError):
                raise ToolError("Amount must be a number")
            if amount <= 0:
                raise ToolError("Amount must be more than 0")
            vt = str(args.get("voucher_type") or "")
            if vt not in ("Sales", "Purchase", "Receipt", "Payment"):
                raise ToolError("voucher_type must be Sales, Purchase, Receipt or Payment")
            party, ledger = str(args.get("party") or "").strip(), str(args.get("ledger") or "").strip()
            if not party or not ledger:
                raise ToolError("Party and ledger names are needed (use tally_report ledgers to see exact names).")
            frozen = {"voucher_type": vt, "party": party, "amount": amount, "ledger": ledger,
                      "date": str(args.get("date") or ""), "narration": str(args.get("narration") or "")[:300],
                      "company": str(args.get("company") or "")}
            # amount is shown, but amount_paise stays 0 so spending limits never auto-approve a Tally entry
            return NeedsApproval(tier=2, title=f"Tally entry: {vt} ₹{amount:,.2f}", payee=party, amount_paise=0,
                                 items=[{"name": f"{vt}: {party} ↔ {ledger}  ₹{amount:,.2f}", "price_paise": None}]
                                 + ([{"name": frozen["narration"], "price_paise": None}] if frozen["narration"] else []),
                                 pay_method="TallyPrime on your PC (no money moves)",
                                 action={"executor": "pc", "pack_id": pack.id, "name": "tally_voucher", "args": frozen})
        out = _call(ctx, tool, args)
        if tool == "send_file" and out.get("file_id"):
            from ...pc import service as pcs
            f = pcs.get_file(out["file_id"])
            if f is None or f.tenant_id != ctx.user.id:
                raise ToolError("PC: the file did not arrive")
            return {"pc_file": pcs.public_file(f), "message": f"{f.name} phone par bhej diya."}
        return out

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        out = _call(ctx, action, args)
        msg = {"print": "PC par print bhej diya.", "tally_voucher": "Tally mein entry ho gayi."}.get(action, "Ho gaya.")
        return {"status": "done", "message": out.get("message") or msg, **{k: v for k, v in out.items() if k != "message"}}
