"""v0.94 Payroll Officer tools. `payroll_dekho` only reads; `payroll` changes things. Paying salaries waits for HER
Haan; Hoola makes the bank file and she uploads / pays it herself. PAN and bank account numbers are kept sealed and
shown masked; the model never sees them in full."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

PAYROLL_TOOLS = [
    {"name": "payroll", "description": (
        "Payroll officer: runs the business's monthly salary end to end. "
        "action=employee: name, employee (to update: name / code / alias), phone, gender M|F, dob, doj (joining), designation, "
        "pay {basic, da, hra, conveyance, special, other} monthly OR gross (Hoola splits it 50% basic / 20% HRA / rest "
        "special), uan, esic_ip, pan, account, ifsc, regime new|old, declared (old regime deductions for the year), "
        "prev_income, prev_tds, pf_member, eps_member, pf_on_full, fixed_term, alias (the name she uses, e.g. 'Ramu'). "
        "action=attendance: period (YYYY-MM), entries [{employee, lop_days, ot_hours, extra, deduct, note}] from what she "
        "said ('Ramesh 2 din chhutti, Suresh 6 ghante OT'). action=import_attendance: period, file_id (Excel / CSV). "
        "action=advance: employee, amount, emi, given_on. "
        "action=run: period -> the whole payroll with every check; show the summary and checks and ask for her haan. "
        "action=decide: run (id or period), approve, note: ONLY when she herself says haan / mana. action=files: run (after "
        "her haan: payslips PDF, salary register, bank bulk file, ECR, ESIC sheet). action=paid: run, paid_on (after SHE "
        "paid). action=payslip_drafts: run. action=leaving: employee, last_day, leave_days, notice_recovery, other, "
        "death_or_disability (full & final + gratuity). action=bonus: period (any month of the year), rate. "
        "action=settings: company, state, pf_on, pf_code, esi_on, esi_code, tan, min_wage (monthly, her state's "
        "notification), days_basis calendar|26|30, pay_account, pay_ifsc, morning_time. Hoola NEVER pays or logs in to a bank."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["employee", "attendance", "import_attendance", "advance", "run", "decide", "files", "paid",
                                               "payslip_drafts", "leaving", "bonus", "settings"]},
         "name": {"type": "string"}, "employee": {"type": "string"}, "phone": {"type": "string"}, "gender": {"type": "string"},
         "dob": {"type": "string"}, "doj": {"type": "string"}, "designation": {"type": "string"}, "pay": {"type": "object"},
         "gross": {"type": "number"}, "uan": {"type": "string"}, "esic_ip": {"type": "string"}, "pan": {"type": "string"},
         "account": {"type": "string"}, "ifsc": {"type": "string"}, "regime": {"type": "string"}, "declared": {"type": "number"},
         "prev_income": {"type": "number"}, "prev_tds": {"type": "number"}, "pf_member": {"type": "boolean"},
         "eps_member": {"type": "boolean"}, "pf_on_full": {"type": "boolean"}, "fixed_term": {"type": "boolean"},
         "alias": {"type": "string"}, "period": {"type": "string"}, "entries": {"type": "array", "items": {"type": "object"}},
         "file_id": {"type": "string"}, "amount": {"type": "number"}, "emi": {"type": "number"}, "given_on": {"type": "string"},
         "run": {"type": "string"}, "approve": {"type": "boolean"}, "note": {"type": "string"}, "paid_on": {"type": "string"},
         "last_day": {"type": "string"}, "leave_days": {"type": "number"}, "notice_recovery": {"type": "number"},
         "other": {"type": "number"}, "death_or_disability": {"type": "boolean"}, "rate": {"type": "number"},
         "company": {"type": "string"}, "state": {"type": "string"}, "pf_on": {"type": "boolean"}, "pf_code": {"type": "string"},
         "esi_on": {"type": "boolean"}, "esi_code": {"type": "string"}, "tan": {"type": "string"}, "min_wage": {"type": "number"},
         "days_basis": {"type": "string"}, "pay_account": {"type": "string"}, "pay_ifsc": {"type": "string"},
         "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "payroll_dekho", "description": (
        "Read payroll (nothing changes). what=today (salary / PF / ESIC / TDS / Form 138 / ESIC return / bonus due, late) | "
        "employees | runs | run (run: id or period) | employee (employee) | settings | tax (gross_year, regime, declared: "
        "income tax on a yearly salary) | pf (period, wages) | pt (state, gross, month, gender)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["today", "employees", "runs", "run", "employee", "settings", "tax", "pf", "pt"]},
         "run": {"type": "string"}, "employee": {"type": "string"}, "gross_year": {"type": "number"}, "regime": {"type": "string"},
         "declared": {"type": "number"}, "period": {"type": "string"}, "wages": {"type": "number"}, "state": {"type": "string"},
         "gross": {"type": "number"}, "month": {"type": "integer"}, "gender": {"type": "string"}},
         "required": ["what"]}},
]
PAYROLL_LABELS = {"payroll": "Salary ka kaam kar raha hoon", "payroll_dekho": "Payroll register dekh raha hoon"}

_EMP = ("phone", "gender", "dob", "doj", "designation", "pay", "gross", "uan", "esic_ip", "pan", "account", "ifsc", "regime",
        "declared", "prev_income", "prev_tds", "pf_member", "eps_member", "pf_on_full", "fixed_term", "alias")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..payroll import service as P
    t, conv = ctx.tenant_id, ctx.conversation_id
    by = "owner" if _owner(ctx) else (getattr(ctx, "actor", "") or "staff")
    try:
        if action == "employee":
            return P.save_employee(t, _s(a.get("name")), _s(a.get("employee")), **{k: a[k] for k in _EMP if k in a})
        if action == "attendance":
            return P.set_attendance(t, _s(a.get("period")), a.get("entries") or [], by)
        if action == "import_attendance":
            from ..mailbox import service as ms
            name, _m, data = ms.load_files(t, [{"type": "file", "file_id": _s(a.get("file_id"))}])[0]
            return P.import_attendance(t, _s(a.get("period")), data, name)
        if action == "advance":
            return P.add_advance(t, _s(a.get("employee")), a.get("amount"), a.get("emi"), _s(a.get("given_on")), _s(a.get("note")))
        if action == "run":
            return P.prepare_run(t, _s(a.get("period")), conv)
        if action == "decide":
            if not _owner(ctx):
                raise ToolError("Salary par haan sirf owner de sakti hain.")
            return P.decide(t, _s(a.get("run") or a.get("period")), bool(a.get("approve")), _s(a.get("note")), conv)
        if action == "files":
            return P.files(t, _s(a.get("run") or a.get("period")), conv)
        if action == "paid":
            if not _owner(ctx):
                raise ToolError("Payment ho gaya, yeh sirf owner bata sakti hain.")
            return P.mark_paid(t, _s(a.get("run") or a.get("period")), _s(a.get("paid_on")), by, conv)
        if action == "payslip_drafts":
            return P.payslip_drafts(t, _s(a.get("run") or a.get("period")))
        if action == "leaving":
            return P.full_and_final(t, _s(a.get("employee")), _s(a.get("last_day")), a.get("leave_days") or 0, a.get("notice_recovery") or 0,
                                    a.get("other") or 0, bool(a.get("death_or_disability")), conv)
        if action == "bonus":
            return P.bonus_report(t, _s(a.get("period")), float(a.get("rate") or 8.33))
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Settings sirf owner.")
            keys = ("company", "state", "pf_on", "pf_code", "esi_on", "esi_code", "tan", "min_wage", "days_basis", "pay_account",
                    "pay_ifsc", "morning_time")
            return {"settings": P.save_settings(t, **{k: a[k] for k in keys if k in a}), "say": "Save."}
    except (P.PayError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..payroll import rules as R
    from ..payroll import service as P
    t = ctx.tenant_id
    try:
        if what == "today":
            return P.calendar(t)
        if what == "employees":
            return {"employees": P.employees(t)}
        if what == "runs":
            return {"runs": P.runs(t)}
        if what == "run":
            return P.get_run(t, _s(a.get("run") or a.get("period")))
        if what == "employee":
            return next((e for e in P.employees(t, False) if _s(a.get("employee")).lower() in (e["name"].lower(), e["code"].lower(), e["id"])),
                        {"error": "nahi mila"})
        if what == "settings":
            return P.settings(t)
        if what == "tax":
            reg = _s(a.get("regime")) or "new"
            ti = float(a.get("gross_year") or 0) - R.STD_DED.get(reg, 75000) - (float(a.get("declared") or 0) if reg == "old" else 0)
            return R.annual_tax(ti, reg)
        if what == "pf":
            return R.pf(_s(a.get("period")), float(a.get("wages") or 0))
        if what == "pt":
            return {"pt": R.pt(_s(a.get("state")), float(a.get("gross") or 0), int(a.get("month") or 1), _s(a.get("gender")))}
    except (P.PayError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("what galat")


async def payroll(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def payroll_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


PAYROLL_HANDLERS = {"payroll": payroll, "payroll_dekho": payroll_dekho}
