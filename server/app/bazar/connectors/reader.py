"""L4 Reader packs: banks, cards and investment apps. Santosh reads only what the user shares (SMS, statement text),
keeps a summary, reminds dues and SIPs, and opens the app when the user wants to act. It never moves money here."""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

from sqlalchemy import select

from ..db import InstalledPack, Reminder, SpendEntry
from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec, rupees, to_paise
from .sms_parser import parse_sms
from .timeparse import IST, ist_now, to_utc_naive

BAL = re.compile(r"(?:avl\.?\s*bal(?:ance)?|available balance|a/c bal(?:ance)?|bal)\s*(?:is|:)?\s*(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)", re.I)
CARD_DUE = re.compile(r"(?:total|minimum)?\s*amount due\s*(?:of|:)?\s*(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?).*?due (?:date|by|on)\s*:?\s*(\d{1,2}[-/ ][A-Za-z0-9]{2,3}[-/ ]\d{2,4})", re.I | re.S)


def _next_monthly(day: int, today: dt.date, lead_days: int = 0) -> dt.date:
    y, m = today.year, today.month
    for _ in range(14):
        try:
            d = dt.date(y, m, day)
        except ValueError:
            d = dt.date(y, m, 28)
        if d - dt.timedelta(days=lead_days) >= today:
            return d
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    raise ToolError("Could not work out the date")


class ReaderExecutor:
    name = "reader"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        src = pack.config["source_name"]
        specs = {
            "import_messages": ToolSpec("import_messages", f"Import {src} SMS or statement lines the user shared. Picks up spends, credits, balance and card dues. OTPs are ignored.",
                                        {"type": "object", "properties": {"messages": {"type": "array", "items": {"type": "string"}}}, "required": ["messages"]}, 1),
            "add_due": ToolSpec("add_due", f"Monthly reminder for a {src} EMI or card due on a day of the month (3 days before).",
                                {"type": "object", "properties": {"name": {"type": "string"}, "day_of_month": {"type": "number"},
                                                                  "amount_rupees": {"type": "number"}}, "required": ["name", "day_of_month"]}, 1),
            "add_sip": ToolSpec("add_sip", f"Track a SIP in {src}: fund, amount and debit day; reminds 2 days before so the account has money.",
                                {"type": "object", "properties": {"fund": {"type": "string"}, "amount_rupees": {"type": "number"},
                                                                  "day_of_month": {"type": "number"}}, "required": ["fund", "amount_rupees", "day_of_month"]}, 1),
            "summary": ToolSpec("summary", f"This month at {src}: money out, money in, last balance seen, upcoming dues or SIPs.",
                                {"type": "object", "properties": {"month": {"type": "string"}}}, 0),
            "open_app": ToolSpec("open_app", f"Open {src} for the user to act (pay, invest, check). Santosh does not log in for them.",
                                 {"type": "object", "properties": {"purpose": {"type": "string"}}}, 1),
        }
        return [specs[t.name] for t in pack.tools]

    def _inst(self, ctx: Ctx, pack: Pack) -> InstalledPack:
        inst = ctx.session.scalars(select(InstalledPack).where(InstalledPack.user_id == ctx.user.id, InstalledPack.pack_id == pack.id)).first()
        if inst is None:
            inst = InstalledPack(user_id=ctx.user.id, pack_id=pack.id, settings={})
            ctx.session.add(inst)
        return inst

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        src = pack.config["source_name"]
        if tool == "import_messages":
            msgs = args.get("messages") or []
            if isinstance(msgs, str):
                msgs = [m for m in msgs.splitlines() if m.strip()]
            inst = self._inst(ctx, pack)
            settings = dict(inst.settings or {})
            added = skipped = 0
            dues = []
            for m in msgs:
                m = str(m)
                if re.search(r"\botp\b|one time password", m, re.I):
                    skipped += 1
                    continue
                b = BAL.search(m)
                if b:
                    settings["last_balance_paise"] = to_paise(b.group(1))
                    settings["balance_seen_on"] = dt.date.today().isoformat()
                d = CARD_DUE.search(m)
                if d:
                    from .sms_parser import parse_date
                    due_on = parse_date(d.group(2), dt.date.today())
                    amt = to_paise(d.group(1))
                    ctx.session.add(Reminder(user_id=ctx.user.id, kind="bill", text=f"{src} card due {rupees(amt)} on {due_on.strftime('%d %b')}",
                                             due_at=to_utc_naive(dt.datetime.combine(due_on - dt.timedelta(days=3), dt.time(9, 0), tzinfo=IST)),
                                             meta={"name": f"{src} card", "amount_paise": amt, "due_date": due_on.isoformat(), "pack_id": pack.id}))
                    dues.append({"amount": rupees(amt), "due": due_on.isoformat()})
                    continue
                p = parse_sms(m)
                if not p:
                    skipped += 1
                    continue
                p["bank"] = src
                ctx.session.add(SpendEntry(user_id=ctx.user.id, raw=m[:500], **p))
                added += 1
            inst.settings = settings
            out: dict[str, Any] = {"source": src, "transactions": added, "skipped": skipped}
            if "last_balance_paise" in settings:
                out["last_balance"] = rupees(settings["last_balance_paise"])
            if dues:
                out["card_dues"] = dues
            return out
        if tool in ("add_due", "add_sip"):
            day = int(args["day_of_month"])
            if not 1 <= day <= 31:
                raise ToolError("Day of month must be 1–31")
            lead = 3 if tool == "add_due" else 2
            due = _next_monthly(day, ist_now().date(), lead)
            amt = to_paise(args["amount_rupees"]) if args.get("amount_rupees") else 0
            label = args.get("name") or f"SIP: {args.get('fund')}"
            ctx.session.add(Reminder(user_id=ctx.user.id, kind="bill" if tool == "add_due" else "reminder",
                                     text=f"{src} · {label}" + (f" ({rupees(amt)})" if amt else "") + f" on {due.strftime('%d %b')}",
                                     due_at=to_utc_naive(dt.datetime.combine(due - dt.timedelta(days=lead), dt.time(9, 0), tzinfo=IST)),
                                     repeat="monthly", meta={"name": f"{src} {label}", "amount_paise": amt, "due_date": due.isoformat(), "pack_id": pack.id}))
            return {"tracking": label, "source": src, "next": due.isoformat(), "reminds": f"{lead} days before, every month"}
        if tool == "summary":
            month = str(args.get("month") or ist_now().strftime("%Y-%m"))
            y, mo = map(int, month.split("-"))
            start, end = dt.date(y, mo, 1), dt.date(y + (mo == 12), mo % 12 + 1, 1)
            es = ctx.session.scalars(select(SpendEntry).where(SpendEntry.user_id == ctx.user.id, SpendEntry.bank == src,
                                                              SpendEntry.occurred_on >= start, SpendEntry.occurred_on < end)).all()
            out_p = sum(e.amount_paise for e in es if e.direction == "debit")
            in_p = sum(e.amount_paise for e in es if e.direction == "credit")
            inst = self._inst(ctx, pack)
            rs = ctx.session.scalars(select(Reminder).where(Reminder.user_id == ctx.user.id, Reminder.done.is_(False))).all()
            upcoming = [r.text for r in rs if (r.meta or {}).get("pack_id") == pack.id]
            res: dict[str, Any] = {"source": src, "month": month, "money_out": rupees(out_p), "money_in": rupees(in_p),
                                   "transactions": len(es), "upcoming": upcoming}
            if (inst.settings or {}).get("last_balance_paise") is not None:
                res["last_balance"] = rupees(inst.settings["last_balance_paise"])
                res["balance_seen_on"] = inst.settings.get("balance_seen_on")
            if not es and not upcoming:
                res["hint"] = f"Share your {src} SMS or statement and I'll keep this updated."
            return res
        if tool == "open_app":
            return {"app": src, "open": {"web": pack.config.get("web", ""), "app_store": pack.config.get("play_search", "")},
                    "message": f"Opening {src}. Log in there yourself; Santosh never asks for your password, PIN or OTP."}
        raise ToolError(f"Unknown tool {tool}")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        raise ToolError("Reader packs never move money")
