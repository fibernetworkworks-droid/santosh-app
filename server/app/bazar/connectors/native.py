"""Santosh's 13 built-in MVP skills. They run entirely on Newtika's stack."""
from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from typing import Any

from sqlalchemy import select

from ..db import Contact, ListItem, Memory, Reminder, SpendEntry, Transaction
from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec, rupees, to_paise
from .sms_parser import parse_sms
from .timeparse import IST, ist_now, parse_when, to_ist, to_utc_naive
from .upi import build_upi_intent, valid_vpa
from .whatsapp import WhatsApp

S = lambda **p: {"type": "object", "properties": p}  # noqa: E731
STR, NUM = {"type": "string"}, {"type": "number"}
ARR = {"type": "array", "items": {"type": "string"}}

GREETINGS = {
    "hi": "{name} ji, aapko aur aapke parivar ko {festival} ki hardik shubhkamnayein! — {sender}",
    "mr": "{name}, तुम्हाला आणि तुमच्या कुटुंबाला {festival} च्या हार्दिक शुभेच्छा! — {sender}",
    "en": "Dear {name}, wishing you and your family a very happy {festival}! — {sender}",
}


def _when(args: dict[str, Any], key: str = "when") -> dt.datetime:
    raw = str(args.get(key) or "")
    d = parse_when(raw)
    if d is None:
        raise ToolError("When should I remind you? For example 'kal subah 7 baje' or 'at 6:30 pm'.")
    return d


def _mmdd(s: str) -> str:
    s = s.strip()
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})", s)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        return f"{mo:02d}-{d:02d}"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return f"{m.group(2)}-{m.group(3)}"
    m = re.match(r"^(\d{2})-(\d{2})$", s)
    if m:
        return s
    raise ToolError("Give the date as DD/MM, e.g. 14/03")


def _next_yearly(mmdd: str, today: dt.date) -> dt.date:
    mo, d = map(int, mmdd.split("-"))
    for y in (today.year, today.year + 1):
        try:
            cand = dt.date(y, mo, d)
        except ValueError:  # 29 Feb
            cand = dt.date(y, 2, 28)
        if cand >= today:
            return cand
    return cand


class NativeExecutor:
    name = "native"

    SPECS: dict[str, list[ToolSpec]] = {
        "reminders": [
            ToolSpec("set_reminder", "Set a reminder or alarm. 'when' accepts ISO time or phrases like 'kal subah 7 baje'.",
                     {**S(text=STR, when=STR, repeat={"type": "string", "enum": ["", "daily", "weekly", "monthly", "yearly"]},
                          kind={"type": "string", "enum": ["reminder", "alarm"]}), "required": ["text", "when"]}, 1),
            ToolSpec("list_reminders", "List upcoming reminders.", S(days=NUM), 0),
            ToolSpec("cancel_reminder", "Cancel a reminder by id or by matching text.", S(reminder_id=STR, text=STR), 1),
        ],
        "calendar": [
            ToolSpec("add_event", "Add a calendar event with a reminder 30 minutes before.",
                     {**S(title=STR, when=STR, duration_min=NUM, place=STR), "required": ["title", "when"]}, 1),
            ToolSpec("agenda", "Events and reminders for a day (default today).", S(date=STR), 0),
        ],
        "notes": [
            ToolSpec("save_note", "Remember something the user says.", {**S(text=STR, tags=ARR), "required": ["text"]}, 1),
            ToolSpec("search_notes", "Find saved notes.", S(query=STR), 0),
        ],
        "lists": [
            ToolSpec("add_to_list", "Add items to a list (default 'shopping').", {**S(items=ARR, list=STR), "required": ["items"]}, 1),
            ToolSpec("show_list", "Show a list.", S(list=STR), 0),
            ToolSpec("clear_list", "Remove done or all items from a list.", S(list=STR, only_done={"type": "boolean"}), 1),
        ],
        "briefing": [ToolSpec("morning_brief", "Today's agenda, bills due this week, birthdays and the shopping list.", S(), 0)],
        "spend": [
            ToolSpec("import_sms", "Import bank/UPI SMS the user shared (one message per item). OTP messages are ignored.",
                     {**S(messages=ARR), "required": ["messages"]}, 1),
            ToolSpec("spend_report", "Spending by category for a month (YYYY-MM, default this month).", S(month=STR), 0),
        ],
        "bill_reminders": [
            ToolSpec("add_bill_reminder", "Monthly reminder for a bill/EMI/rent on a day of the month, 3 days before.",
                     {**S(name=STR, day_of_month=NUM, amount_rupees=NUM), "required": ["name", "day_of_month"]}, 1),
            ToolSpec("upcoming_bills", "Bills and EMIs due in the next N days (default 10).", S(days=NUM), 0),
        ],
        "splitter": [
            ToolSpec("split_expense", "Split an amount between people. Optional payee_vpa makes UPI request links.",
                     {**S(total_rupees=NUM, people=ARR, shares={"type": "object"}, payee_vpa=STR, note=STR),
                      "required": ["total_rupees", "people"]}, 1),
        ],
        "family": [
            ToolSpec("save_family_member", "Save a family member's details (relation, diet, sizes, address, phone).",
                     {**S(name=STR, relation=STR, details={"type": "object"}), "required": ["name"]}, 1),
            ToolSpec("get_family", "Family profiles.", S(), 0),
        ],
        "medicine": [
            ToolSpec("add_medicine", "Daily medicine reminders at given times (HH:MM, 24h) for N days (0 = ongoing).",
                     {**S(name=STR, times=ARR, days=NUM, for_person=STR), "required": ["name", "times"]}, 1),
        ],
        "birthdays": [
            ToolSpec("add_birthday", "Save a birthday or anniversary (DD/MM) with a yearly reminder.",
                     {**S(name=STR, date=STR, kind={"type": "string", "enum": ["birthday", "anniversary"]}, phone=STR),
                      "required": ["name", "date"]}, 1),
            ToolSpec("upcoming_birthdays", "Birthdays and anniversaries in the next N days (default 30).", S(days=NUM), 0),
        ],
        "greetings": [
            ToolSpec("draft_greetings", "Draft personalised festival greetings for saved contacts.",
                     {**S(festival=STR, names=ARR, language=STR), "required": ["festival"]}, 0),
            ToolSpec("send_greetings", "Ask approval to send the drafted greetings on WhatsApp.",
                     {**S(festival=STR, names=ARR, language=STR), "required": ["festival"]}, 2),
        ],
        "wa_marketing": [
            ToolSpec("create_template", "Submit a WhatsApp message template to Meta for approval. Use {{1}}, {{2}} for variables.",
                     {**S(name=STR, body=STR, language=STR, category={"type": "string", "enum": ["MARKETING", "UTILITY"]},
                          example=ARR), "required": ["name", "body"]}, 1),
            ToolSpec("template_status", "Check a template's approval status.", {**S(name=STR), "required": ["name"]}, 0),
            ToolSpec("send_campaign", "Ask approval to send an approved template to a list of phone numbers.",
                     {**S(template=STR, language=STR, recipients=ARR, params=ARR), "required": ["template", "recipients"]}, 2),
        ],
    }

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return self.SPECS[pack.config["skill"]]

    # ------------------------------------------------------------------
    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        fn = getattr(self, f"_{tool}", None)
        if fn is None:
            raise ToolError(f"Unknown tool {tool}")
        return fn(pack, args, ctx)

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        wa = WhatsApp(ctx.settings)
        if action == "send_messages":
            # Personal greetings go from the user's own WhatsApp: one tap per contact on a prefilled chat.
            # (The Business API can't send free text to people who haven't messaged first.)
            from urllib.parse import quote
            links = [{"name": m["name"], "url": f"https://wa.me/{re.sub(r'[^0-9]', '', m['phone'])}?text={quote(m['text'])}"}
                     for m in args["messages"]]
            return {"share_links": links, "count": len(links),
                    "message": f"{len(links)} greetings ready. Tap each name to open WhatsApp with the message filled in, then press send."}
        if action == "send_campaign":
            results = [wa.send_template(p, args["template"], args["language"], args.get("params", [])) for p in args["recipients"]]
            return {"sent": sum(r["ok"] for r in results), "failed": sum(not r["ok"] for r in results)}
        raise ToolError(f"Unknown action {action}")

    # ---------------- reminders / calendar ----------------
    def _set_reminder(self, pack, a, ctx):
        when = _when(a)
        r = Reminder(user_id=ctx.user.id, kind=a.get("kind") or "reminder", text=str(a["text"]), due_at=to_utc_naive(when),
                     repeat=str(a.get("repeat") or ""))
        ctx.session.add(r)
        ctx.session.flush()
        return {"reminder_id": r.id, "text": r.text, "when": when.strftime("%a %d %b, %I:%M %p"), "repeat": r.repeat}

    def _list_reminders(self, pack, a, ctx):
        until = to_utc_naive(ist_now() + dt.timedelta(days=float(a.get("days") or 7)))
        rs = ctx.session.scalars(select(Reminder).where(Reminder.user_id == ctx.user.id, Reminder.done.is_(False),
                                                        Reminder.due_at <= until).order_by(Reminder.due_at)).all()
        return {"reminders": [{"id": r.id, "text": r.text, "kind": r.kind, "when": to_ist(r.due_at).strftime("%a %d %b, %I:%M %p")}
                              for r in rs]}

    def _cancel_reminder(self, pack, a, ctx):
        q = select(Reminder).where(Reminder.user_id == ctx.user.id, Reminder.done.is_(False))
        rs = ctx.session.scalars(q).all()
        if a.get("reminder_id"):
            rs = [r for r in rs if r.id == a["reminder_id"]]
        elif a.get("text"):
            rs = [r for r in rs if str(a["text"]).lower() in r.text.lower()]
        else:
            raise ToolError("Which reminder?")
        if len(rs) != 1:
            raise ToolError("I found " + (f"{len(rs)} matching reminders" if rs else "no matching reminder") + ". Which one?")
        rs[0].done = True
        return {"cancelled": rs[0].text}

    def _add_event(self, pack, a, ctx):
        when = _when(a)
        r = Reminder(user_id=ctx.user.id, kind="event", text=str(a["title"]), due_at=to_utc_naive(when - dt.timedelta(minutes=30)),
                     meta={"start": when.isoformat(), "duration_min": int(a.get("duration_min") or 60), "place": a.get("place", "")})
        ctx.session.add(r)
        ctx.session.flush()
        return {"event_id": r.id, "title": r.text, "starts": when.strftime("%a %d %b, %I:%M %p"), "reminder": "30 minutes before"}

    def _agenda(self, pack, a, ctx):
        day = dt.date.fromisoformat(a["date"]) if a.get("date") else ist_now().date()
        start = to_utc_naive(dt.datetime.combine(day, dt.time(0, 0), tzinfo=IST))
        end = start + dt.timedelta(days=1)
        rs = ctx.session.scalars(select(Reminder).where(Reminder.user_id == ctx.user.id, Reminder.done.is_(False),
                                                        Reminder.due_at >= start, Reminder.due_at < end).order_by(Reminder.due_at)).all()
        return {"date": day.isoformat(), "items": [{"time": to_ist(r.due_at).strftime("%I:%M %p"), "text": r.text, "kind": r.kind} for r in rs]}

    # ---------------- notes / lists / family ----------------
    def _save_note(self, pack, a, ctx):
        m = Memory(user_id=ctx.user.id, kind="note", text=str(a["text"]), tags=list(a.get("tags") or []))
        ctx.session.add(m)
        ctx.session.flush()
        return {"saved": m.text, "note_id": m.id}

    def _search_notes(self, pack, a, ctx):
        q = str(a.get("query") or "").lower()
        ms = ctx.session.scalars(select(Memory).where(Memory.user_id == ctx.user.id).order_by(Memory.created_at.desc())).all()
        words = [w for w in re.split(r"\W+", q) if len(w) > 2]
        hits = [m for m in ms if not words or any(w in m.text.lower() or w in " ".join(m.tags).lower() for w in words)]
        return {"notes": [{"text": m.text, "saved_on": m.created_at.date().isoformat()} for m in hits[:20]]}

    def _add_to_list(self, pack, a, ctx):
        name = str(a.get("list") or "shopping").lower()
        items = a["items"] if isinstance(a["items"], list) else re.split(r",|\baur\b|\band\b", str(a["items"]))
        added = []
        for it in items:
            it = str(it).strip()
            if it:
                ctx.session.add(ListItem(user_id=ctx.user.id, list_name=name, text=it))
                added.append(it)
        return {"list": name, "added": added}

    def _show_list(self, pack, a, ctx):
        name = str(a.get("list") or "shopping").lower()
        its = ctx.session.scalars(select(ListItem).where(ListItem.user_id == ctx.user.id, ListItem.list_name == name)).all()
        return {"list": name, "items": [{"text": i.text, "done": i.done} for i in its]}

    def _clear_list(self, pack, a, ctx):
        name = str(a.get("list") or "shopping").lower()
        its = ctx.session.scalars(select(ListItem).where(ListItem.user_id == ctx.user.id, ListItem.list_name == name)).all()
        n = 0
        for i in its:
            if not a.get("only_done") or i.done:
                ctx.session.delete(i)
                n += 1
        return {"list": name, "removed": n}

    def _save_family_member(self, pack, a, ctx):
        prof = dict(ctx.user.profile or {})
        fam = list(prof.get("family", []))
        name = str(a["name"])
        entry = next((f for f in fam if f["name"].lower() == name.lower()), None)
        if entry is None:
            entry = {"name": name}
            fam.append(entry)
        if a.get("relation"):
            entry["relation"] = a["relation"]
        entry.update({k: v for k, v in (a.get("details") or {}).items()})
        prof["family"] = fam
        ctx.user.profile = prof
        return {"saved": entry}

    def _get_family(self, pack, a, ctx):
        return {"family": (ctx.user.profile or {}).get("family", [])}

    # ---------------- briefing ----------------
    def _morning_brief(self, pack, a, ctx):
        now = ist_now()
        today = self._agenda(pack, {"date": now.date().isoformat()}, ctx)["items"]
        bills = self._upcoming_bills(pack, {"days": 7}, ctx)["bills"]
        bdays = self._upcoming_birthdays(pack, {"days": 1}, ctx)["upcoming"]
        shopping = [i["text"] for i in self._show_list(pack, {"list": "shopping"}, ctx)["items"] if not i["done"]]
        lines = [f"Good morning{', ' + ctx.user.name if ctx.user.name else ''}! {now.strftime('%A, %d %B')}."]
        lines.append(("Today: " + "; ".join(f"{i['time']} {i['text']}" for i in today)) if today else "Nothing scheduled today.")
        if bills:
            lines.append("Bills this week: " + "; ".join(f"{b['name']} ({b['due']})" for b in bills))
        if bdays:
            lines.append("Today: " + ", ".join(f"{b['name']}'s {b['kind']}" for b in bdays) + ". Want me to send wishes?")
        if shopping:
            lines.append(f"Shopping list has {len(shopping)} item(s): " + ", ".join(shopping[:6]))
        return {"brief": "\n".join(lines), "agenda": today, "bills": bills, "occasions": bdays, "shopping_list": shopping}

    # ---------------- money insight ----------------
    def _import_sms(self, pack, a, ctx):
        msgs = a["messages"] if isinstance(a["messages"], list) else [a["messages"]]
        added, skipped = 0, 0
        for m in msgs:
            p = parse_sms(str(m))
            if not p:
                skipped += 1
                continue
            ctx.session.add(SpendEntry(user_id=ctx.user.id, raw=str(m)[:500], **p))
            added += 1
        return {"imported": added, "skipped": skipped}

    def _spend_report(self, pack, a, ctx):
        month = str(a.get("month") or ist_now().strftime("%Y-%m"))
        y, mo = map(int, month.split("-"))
        start = dt.date(y, mo, 1)
        end = dt.date(y + (mo == 12), mo % 12 + 1, 1)
        es = ctx.session.scalars(select(SpendEntry).where(SpendEntry.user_id == ctx.user.id, SpendEntry.occurred_on >= start,
                                                          SpendEntry.occurred_on < end)).all()
        # Santosh's own completed payments count too
        txns = ctx.session.scalars(select(Transaction).where(Transaction.user_id == ctx.user.id,
                                                             Transaction.status.in_(["completed", "paid"]))).all()
        by: dict[str, int] = defaultdict(int)
        spent = income = 0
        for e in es:
            if e.direction == "debit":
                by[e.category] += e.amount_paise
                spent += e.amount_paise
            else:
                income += e.amount_paise
        top = sorted(by.items(), key=lambda kv: -kv[1])
        return {"month": month, "spent": rupees(spent), "received": rupees(income),
                "by_category": [{"category": k, "amount": rupees(v), "share": f"{v * 100 // spent}%" if spent else "0%"} for k, v in top],
                "entries": len(es), "santosh_payments": len(txns)}

    def _add_bill_reminder(self, pack, a, ctx):
        day = int(a["day_of_month"])
        if not 1 <= day <= 31:
            raise ToolError("Day of month must be 1–31")
        now = ist_now()
        y, m = now.year, now.month
        due = None
        for _ in range(3):
            try:
                cand = dt.date(y, m, day)
            except ValueError:
                cand = dt.date(y, m, 28)
            if cand - dt.timedelta(days=3) >= now.date():
                due = cand
                break
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        assert due is not None
        amt = to_paise(a["amount_rupees"]) if a.get("amount_rupees") else 0
        r = Reminder(user_id=ctx.user.id, kind="bill", text=f"{a['name']} due on {due.strftime('%d %b')}" + (f" ({rupees(amt)})" if amt else ""),
                     due_at=to_utc_naive(dt.datetime.combine(due - dt.timedelta(days=3), dt.time(9, 0), tzinfo=IST)),
                     repeat="monthly", meta={"name": a["name"], "day": day, "amount_paise": amt, "due_date": due.isoformat()})
        ctx.session.add(r)
        return {"bill": a["name"], "first_due": due.isoformat(), "reminds": "3 days before, every month"}

    def _upcoming_bills(self, pack, a, ctx):
        until = to_utc_naive(ist_now() + dt.timedelta(days=float(a.get("days") or 10)))
        rs = ctx.session.scalars(select(Reminder).where(Reminder.user_id == ctx.user.id, Reminder.kind == "bill",
                                                        Reminder.done.is_(False), Reminder.due_at <= until).order_by(Reminder.due_at)).all()
        out = [{"name": r.meta.get("name") or r.text, "due": r.meta.get("due_date") or to_ist(r.due_at).date().isoformat(),
                "amount": rupees(r.meta["amount_paise"]) if r.meta.get("amount_paise") else ""} for r in rs]
        unpaid = ctx.session.scalars(select(Transaction).where(Transaction.user_id == ctx.user.id, Transaction.kind == "bill",
                                                               Transaction.status == "fetched")).all()
        for t in unpaid:
            b = t.meta.get("bill", {})
            out.append({"name": b.get("biller", t.provider), "due": b.get("due_date", ""), "amount": rupees(t.amount_paise), "fetched": True})
        return {"bills": out}

    def _split_expense(self, pack, a, ctx):
        total = to_paise(a["total_rupees"])
        people = [str(p) for p in a["people"]]
        if not people:
            raise ToolError("Split between whom?")
        shares = a.get("shares") or {}
        if shares:
            wsum = sum(float(v) for v in shares.values())
            parts = {p: int(total * float(shares.get(p, 0)) / wsum) for p in people}
        else:
            base = total // len(people)
            parts = {p: base for p in people}
        diff = total - sum(parts.values())
        parts[people[0]] += diff
        vpa = str(a.get("payee_vpa") or "")
        out = []
        for p, amt in parts.items():
            row: dict[str, Any] = {"name": p, "owes": rupees(amt)}
            if vpa and valid_vpa(vpa) and amt > 0:
                row["pay_link"] = build_upi_intent(vpa, ctx.user.name or vpa, amt, str(a.get("note") or "Split"))
            out.append(row)
        return {"total": rupees(total), "split": out}

    def _add_medicine(self, pack, a, ctx):
        times = [str(t) for t in a["times"]]
        now = ist_now()
        made = []
        for t in times:
            m = re.match(r"^(\d{1,2}):(\d{2})$", t.strip())
            if not m:
                raise ToolError("Times must look like 08:00 or 21:30")
            first = dt.datetime.combine(now.date(), dt.time(int(m.group(1)), int(m.group(2))), tzinfo=IST)
            if first <= now:
                first += dt.timedelta(days=1)
            who = f" for {a['for_person']}" if a.get("for_person") else ""
            r = Reminder(user_id=ctx.user.id, kind="medicine", text=f"Take {a['name']}{who}", due_at=to_utc_naive(first), repeat="daily",
                         meta={"days": int(a.get("days") or 0), "started": now.date().isoformat()})
            ctx.session.add(r)
            made.append(first.strftime("%I:%M %p"))
        return {"medicine": a["name"], "daily_at": made, "days": int(a.get("days") or 0) or "ongoing"}

    def _add_birthday(self, pack, a, ctx):
        mmdd = _mmdd(str(a["date"]))
        kind = a.get("kind") or "birthday"
        name = str(a["name"])
        c = ctx.session.scalars(select(Contact).where(Contact.user_id == ctx.user.id, Contact.name == name)).first()
        if c is None:
            c = Contact(user_id=ctx.user.id, name=name, phone=str(a.get("phone") or ""))
            ctx.session.add(c)
        if kind == "anniversary":
            c.anniversary = mmdd
        else:
            c.birthday = mmdd
        nxt = _next_yearly(mmdd, ist_now().date())
        ctx.session.add(Reminder(user_id=ctx.user.id, kind="birthday", text=f"{name}'s {kind} today",
                                 due_at=to_utc_naive(dt.datetime.combine(nxt, dt.time(8, 0), tzinfo=IST)), repeat="yearly",
                                 meta={"name": name, "kind": kind}))
        return {"saved": name, kind: mmdd, "next": nxt.isoformat()}

    def _upcoming_birthdays(self, pack, a, ctx):
        today = ist_now().date()
        days = int(a.get("days") or 30)
        out = []
        for c in ctx.session.scalars(select(Contact).where(Contact.user_id == ctx.user.id)).all():
            for kind, mmdd in (("birthday", c.birthday), ("anniversary", c.anniversary)):
                if mmdd:
                    d = _next_yearly(mmdd, today)
                    if (d - today).days < days:
                        out.append({"name": c.name, "kind": kind, "date": d.isoformat(), "in_days": (d - today).days})
        return {"upcoming": sorted(out, key=lambda x: x["in_days"])}

    # ---------------- greetings / WhatsApp ----------------
    def _messages(self, a, ctx) -> list[dict[str, str]]:
        lang = str(a.get("language") or ctx.user.language or "hi")
        tpl = GREETINGS.get(lang, GREETINGS["hi"])
        cs = ctx.session.scalars(select(Contact).where(Contact.user_id == ctx.user.id)).all()
        names = [n.lower() for n in (a.get("names") or [])]
        if names:
            cs = [c for c in cs if c.name.lower() in names]
        cs = [c for c in cs if c.phone]
        if not cs:
            raise ToolError("I need contacts with phone numbers to send greetings to.")
        return [{"name": c.name, "phone": c.phone,
                 "text": tpl.format(name=c.name, festival=a["festival"], sender=ctx.user.name or "")} for c in cs]

    def _draft_greetings(self, pack, a, ctx):
        msgs = self._messages(a, ctx)
        return {"count": len(msgs), "drafts": msgs[:10]}

    def _send_greetings(self, pack, a, ctx):
        msgs = self._messages(a, ctx)
        return NeedsApproval(tier=2, title=f"Send {a['festival']} wishes to {len(msgs)} people", payee="WhatsApp", amount_paise=0,
                             items=[{"name": f"{m['name']}: {m['text'][:60]}…", "price_paise": None} for m in msgs[:20]],
                             pay_method="You send each from your WhatsApp",
                             action={"executor": "native", "pack_id": pack.id, "name": "send_messages", "args": {"messages": msgs}})

    def _create_template(self, pack, a, ctx):
        name = re.sub(r"[^a-z0-9_]", "_", str(a["name"]).lower())[:60]
        res = WhatsApp(ctx.settings).create_template(name, str(a.get("language") or "en"), str(a.get("category") or "MARKETING"),
                                                     str(a["body"]), [str(x) for x in a.get("example") or []] or None)
        return {"template": name, "status": res.get("status", "PENDING"), "id": res.get("id"),
                "message": "Submitted to Meta. Approval usually takes minutes to a few hours; I'll check the status."}

    def _template_status(self, pack, a, ctx):
        return WhatsApp(ctx.settings).template_status(str(a["name"]))

    def _send_campaign(self, pack, a, ctx):
        wa = WhatsApp(ctx.settings)
        st = wa.template_status(str(a["template"]))
        if st.get("status") != "APPROVED":
            raise ToolError(f"Template '{a['template']}' is {st.get('status', 'unknown')}. It must be APPROVED before sending.")
        rec = [re.sub(r"\D", "", str(p)) for p in a["recipients"]]
        rec = [("91" + p if len(p) == 10 else p) for p in rec if len(p) >= 10]
        if not rec:
            raise ToolError("No valid phone numbers in the list.")
        return NeedsApproval(tier=2, title=f"Send '{a['template']}' to {len(rec)} contacts", payee="WhatsApp (Meta charges per message)",
                             amount_paise=0, items=[{"name": p, "price_paise": None} for p in rec[:20]], pay_method="Billed by Meta",
                             action={"executor": "native", "pack_id": pack.id, "name": "send_campaign",
                                     "args": {"template": a["template"], "language": a.get("language") or st.get("language", "en"),
                                              "recipients": rec, "params": a.get("params") or []}})
