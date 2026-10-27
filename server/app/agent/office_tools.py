"""v0.85 Daftar Sahayak tools. `office_dekho` only reads; `office` changes the office books (stock, repairs, renewals,
deadlines, petty cash, bills, vendors). Spending money is never done here: it becomes a spend card that waits for her
tap in the app, and team reminders are message drafts she sends herself."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

OFFICE_TOOLS = [
    {"name": "office", "description": (
        "Office manager coworker (her office / shop / clinic admin). Use for supplies, repairs, AMCs, renewals and "
        "licences, team deadlines, petty cash, vendor bills and the weekly office note. A forwarded bill, photo or "
        "message: file_read it first, then call this with what it says. "
        "SUPPLIES: action=item_add (name, qty = what is there now, unit, min_qty, lead_days, vendor, price per unit, "
        "location; also used to correct a count) | use (item, qty, note) | restock (item, qty, price, vendor: stock that "
        "ARRIVED) | reorder (names optional: low items -> spend cards per vendor; daily use is learned from 'use'). "
        "REPAIRS: ticket_new (title in her words, asset e.g. 'AC cabin 2', category, priority urgent|high|normal|low "
        "(leave empty and it is judged; fire / spark / leak / lift stuck = urgent), vendor, assigned_to, photos) -> "
        "R-0001 with a due time; the result says if the same thing broke before | ticket_update (ticket, status "
        "open|assigned|waiting|done|cancelled, note, vendor, assigned_to, cost = rupees quoted: makes a spend card). "
        "RENEWALS: renewal_add (name, due_on, kind licence|amc|insurance|rent|subscription|domain|vehicle|tax|bill|"
        "certificate|other, every_months (0 = once), amount, vendor, notice_by = last day to say 'don't renew', notes, "
        "files) | renewal_done (renewal, paid, next_due) | renewal_pay (renewal, amount: spend card for her Haan). "
        "TEAM: deadline_add (title, due_on, owner = team member's name, note) | deadline_done (deadline, dropped) | "
        "nudge (deadline or owner: a reminder message DRAFT she sends; never say it was sent) | team (team "
        "[{name, phone, role}], owner only). "
        "MONEY: spend_request (title, amount, kind purchase|repair|renewal|other, vendor, why): any spending -> card; "
        "petty (amount, what, kind out|in, by, on, bill = file_id): cash already spent / put in | bill_add (vendor, "
        "amount, number, bill_date, due_on, gst, what, file_id): a vendor bill (duplicates refused; MSME 45-day and "
        "GST 180-day warnings) | bill_paid (bill, on) | vendor_add (name, phone, email, category, gstin, udyam = "
        "micro/small supplier, notes). "
        "NOTE: weekly_note (file=true for a Word file). "
        "SETUP: rules (owner only: office_name, morning_time, note_day, note_time, windows [30,15,7,1,0], lead_days, "
        "safety_days, month_budget, rules [her sentences], enabled). "
        "Never say money was paid or a message was sent: she does both herself."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["item_add", "use", "restock", "reorder", "ticket_new", "ticket_update",
                                               "renewal_add", "renewal_done", "renewal_pay", "deadline_add", "deadline_done",
                                               "nudge", "team", "spend_request", "petty", "bill_add", "bill_paid",
                                               "vendor_add", "weekly_note", "rules"]},
         "name": {"type": "string"}, "item": {"type": "string"}, "names": {"type": "array", "items": {"type": "string"}},
         "qty": {"type": "number"}, "unit": {"type": "string"}, "min_qty": {"type": "number"}, "lead_days": {"type": "integer"},
         "vendor": {"type": "string"}, "price": {"type": "number"}, "location": {"type": "string"}, "note": {"type": "string"},
         "title": {"type": "string"}, "asset": {"type": "string"}, "category": {"type": "string"},
         "priority": {"type": "string"}, "assigned_to": {"type": "string"}, "photos": {"type": "array", "items": {"type": "string"}},
         "ticket": {"type": "string"}, "status": {"type": "string"}, "cost": {"type": "number"},
         "renewal": {"type": "string"}, "due_on": {"type": "string"}, "kind": {"type": "string"},
         "every_months": {"type": "integer"}, "amount": {"type": "number"}, "notice_by": {"type": "string"},
         "notes": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}, "paid": {"type": "number"},
         "next_due": {"type": "string"}, "deadline": {"type": "string"}, "owner": {"type": "string"},
         "dropped": {"type": "boolean"}, "team": {"type": "array", "items": {"type": "object"}}, "why": {"type": "string"},
         "what": {"type": "string"}, "by": {"type": "string"}, "on": {"type": "string"}, "bill": {"type": "string"},
         "number": {"type": "string"}, "bill_date": {"type": "string"}, "gst": {"type": "number"}, "file_id": {"type": "string"},
         "phone": {"type": "string"}, "email": {"type": "string"}, "gstin": {"type": "string"}, "udyam": {"type": "boolean"},
         "file": {"type": "boolean"}, "office_name": {"type": "string"}, "morning_time": {"type": "string"},
         "note_day": {"type": "string"}, "note_time": {"type": "string"}, "windows": {"type": "array", "items": {"type": "integer"}},
         "safety_days": {"type": "integer"}, "month_budget": {"type": "number"},
         "rules": {"type": "array", "items": {"type": "string"}}, "enabled": {"type": "boolean"}},
         "required": ["action"]}},
    {"name": "office_dekho", "description": (
        "Read the office books (nothing changes). what=today (morning list: renewals, low stock, late repairs, "
        "deadlines, bills, cards waiting for her Haan) | stock (q; low=true for only low items with the reorder "
        "reasoning) | tickets (status open|done|all) | renewals (within_days) | starters (India checklist of common "
        "office renewals to offer her) | deadlines (status, owner) | vendors (q) | petty | bills (unpaid=false for all) "
        "| spends (status pending|approved|rejected|all) | note (this week's office note text) | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["today", "stock", "tickets", "renewals", "starters", "deadlines", "vendors",
                                             "petty", "bills", "spends", "note", "rules"]},
         "q": {"type": "string"}, "low": {"type": "boolean"}, "status": {"type": "string"},
         "within_days": {"type": "integer"}, "owner": {"type": "string"}, "unpaid": {"type": "boolean"}},
         "required": ["what"]}},
]
OFFICE_LABELS = {"office": "Office ka kaam kar raha hoon", "office_dekho": "Office ka register dekh raha hoon"}
_OWNER_ONLY = {"rules", "team"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..office import service as O
    actor = getattr(ctx, "actor", "owner") or "owner"
    by = "hoola" if actor == "owner" else actor
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action in _OWNER_ONLY and actor != "owner" and not actor.startswith("approved:"):
            raise ToolError("Office ke niyam aur team sirf owner badal sakti hain.")
        if action == "item_add":
            return {"item": O.item_upsert(t, _s(a.get("name") or a.get("item")), a.get("qty"), _s(a.get("unit")), a.get("min_qty"),
                                          a.get("lead_days"), _s(a.get("vendor")), a.get("price"), _s(a.get("location")), by)}
        if action == "use":
            return O.use(t, _s(a.get("item") or a.get("name")), a.get("qty"), _s(a.get("note")), by)
        if action == "restock":
            return O.restock(t, _s(a.get("item") or a.get("name")), a.get("qty"), a.get("price"), _s(a.get("vendor")), by)
        if action == "reorder":
            names = a.get("names") or ([a["item"]] if a.get("item") else None)
            return O.reorder(t, names, conv)
        if action == "ticket_new":
            return O.ticket_new(t, _s(a.get("title") or a.get("name")), _s(a.get("asset")), _s(a.get("category")),
                                _s(a.get("priority")), _s(a.get("vendor")), _s(a.get("assigned_to")), a.get("photos") or [], by, conv)
        if action == "ticket_update":
            return O.ticket_update(t, _s(a.get("ticket")), _s(a.get("status")), _s(a.get("note")), _s(a.get("vendor")),
                                   _s(a.get("assigned_to")), a.get("cost"), by, conv)
        if action == "renewal_add":
            return O.renewal_add(t, _s(a.get("name") or a.get("title")), _s(a.get("due_on")), _s(a.get("kind")),
                                 a.get("every_months"), a.get("amount"), _s(a.get("vendor")), _s(a.get("notes") or a.get("note")),
                                 a.get("files") or [], _s(a.get("notice_by")))
        if action == "renewal_done":
            return O.renewal_done(t, _s(a.get("renewal") or a.get("name")), a.get("paid"), _s(a.get("next_due")), _s(a.get("note")))
        if action == "renewal_pay":
            return O.renewal_pay(t, _s(a.get("renewal") or a.get("name")), a.get("amount"), conv)
        if action == "deadline_add":
            return O.deadline_add(t, _s(a.get("title") or a.get("name")), _s(a.get("due_on")), _s(a.get("owner")), _s(a.get("note")))
        if action == "deadline_done":
            return O.deadline_done(t, _s(a.get("deadline") or a.get("title")), bool(a.get("dropped")))
        if action == "nudge":
            return O.nudge(t, _s(a.get("deadline")), _s(a.get("owner")), conv)
        if action == "team":
            return {"settings": O.save_settings(t, team=a.get("team") or []), "say": "Team save."}
        if action == "spend_request":
            return O.spend_request(t, _s(a.get("title") or a.get("name")), a.get("amount"), _s(a.get("kind")) or "other",
                                   _s(a.get("vendor")), _s(a.get("why")), conv)
        if action == "petty":
            return O.petty_add(t, a.get("amount"), _s(a.get("what") or a.get("title")), _s(a.get("kind")) or "out",
                               _s(a.get("by")), _s(a.get("on")), _s(a.get("bill") or a.get("file_id")))
        if action == "bill_add":
            return O.bill_add(t, _s(a.get("vendor")), a.get("amount"), _s(a.get("number")), _s(a.get("bill_date")),
                              _s(a.get("due_on")), a.get("gst"), _s(a.get("what") or a.get("title")), _s(a.get("file_id")))
        if action == "bill_paid":
            return O.bill_paid(t, _s(a.get("bill") or a.get("number")), _s(a.get("on")))
        if action == "vendor_add":
            return {"vendor": O.vendor_upsert(t, _s(a.get("name") or a.get("vendor")), _s(a.get("phone")), _s(a.get("email")),
                                              _s(a.get("category")), _s(a.get("gstin")), _s(a.get("notes") or a.get("note")),
                                              udyam=a.get("udyam"))}
        if action == "weekly_note":
            return O.weekly_note(t, make_file=bool(a.get("file", True)), conv=conv)
        if action == "rules":
            keys = ("office_name", "morning_time", "note_day", "note_time", "windows", "lead_days", "safety_days",
                    "month_budget", "rules", "enabled")
            return {"rules": O.save_settings(t, **{k: a[k] for k in keys if k in a}), "say": "Office ke niyam save."}
    except O.OfficeError as e:
        raise ToolError(str(e))
    raise ToolError("action = item_add | use | restock | reorder | ticket_new | ticket_update | renewal_add | renewal_done | "
                    "renewal_pay | deadline_add | deadline_done | nudge | team | spend_request | petty | bill_add | bill_paid | "
                    "vendor_add | weekly_note | rules")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..office import service as O
    t = ctx.tenant_id
    try:
        if what == "today":
            return O.overview(t)
        if what == "stock":
            return {"items": O.items(t, _s(a.get("q")), bool(a.get("low")))}
        if what == "tickets":
            return {"tickets": O.tickets(t, _s(a.get("status")) or "open")}
        if what == "renewals":
            wd = a.get("within_days")
            return {"renewals": O.renewals(t, int(wd) if wd not in (None, "") else None)}
        if what == "starters":
            return {"starters": O.starters(t), "say": "Common Indian office items; tareekh unke kagaz se lijiye."}
        if what == "deadlines":
            return {"deadlines": O.deadlines(t, _s(a.get("status")) or "open", _s(a.get("owner")))}
        if what == "vendors":
            return {"vendors": O.vendors(t, _s(a.get("q")))}
        if what == "petty":
            return O.petty(t)
        if what == "bills":
            return {"bills": O.bills(t, a.get("unpaid") is not False)}
        if what == "spends":
            return {"spends": O.spends(t, _s(a.get("status")) or "pending")}
        if what == "note":
            return O.weekly_note(t, make_file=False)
        if what == "rules":
            return O.settings(t)
    except O.OfficeError as e:
        raise ToolError(str(e))
    raise ToolError("what = today | stock | tickets | renewals | starters | deadlines | vendors | petty | bills | spends | note | rules")


async def office(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def office_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


OFFICE_HANDLERS = {"office": office, "office_dekho": office_dekho}
