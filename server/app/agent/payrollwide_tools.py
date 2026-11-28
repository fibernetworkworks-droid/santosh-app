"""Payroll worldwide (F5 of docs/FINANCE_GLOBAL_PLAN.md) tool: `payroll_worldwide`. Payroll on HER rules for any country: people,
a period's run with every line shown, payslips, the list for her bank, her filings tracker and contractor information returns.
It never pays and never files. India's statutory payroll (PF / ESI / TDS) also lives in the payroll tool."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "employee", "people", "run", "close", "payslip", "payments", "filings", "done", "contractors",
            "desk", "inputs", "input_rows", "missing", "changes", "prepare", "rules", "starting_list", "apply_starting_list",
            "sources", "people_text", "import_view", "history", "parts", "part_save", "policy_save", "propose_parts", "match_test",
            "preview", "report", "history_report", "group_view"]
_CHANGES = {"settings", "employee", "run", "close", "done", "input_rows", "prepare", "apply_starting_list", "people_text", "part_save",
            "policy_save", "match_test", "preview"}
# v0.999.171 using an import (her tick on each line read by AI), accepting a test difference, checking and approving stay HER taps
# v0.999.169 approving a run, the payment file, payslip emails and checking a country rule are HER taps on the Payroll desk

PAYROLLWIDE_TOOLS = [
    {"name": "payroll_worldwide", "description": (
        "Payroll for any country on HER rules (workspace = her finance workspace); never pays, never files; not payroll advice. "
        "settings: country, frequency monthly|fortnightly|weekly, source (where her rates come from - required with rates), "
        "contributions [{name, employee_pct, employer_pct, from, upto (per period), base gross|taxable, cap_employee, cap_employer, "
        "slabs [{upto, employee, employer}]}], income_tax {method annualised|period|flat|none, bands [{upto, pct}], allowance (a year), "
        "flat_pct}, filings [{name, every monthly|quarterly|yearly|per_run, due_day, due_offset_days, month}], pay_day. A country rate "
        "nobody checked is never used: with no rules she is asked for hers. employee: name + annual | per_period | hourly (+ hours), "
        "pre_tax_pct, allowance, tax_id (kept masked), start; leave=true + left_on. people: list. run: period YYYY-MM (monthly) or the "
        "first day YYYY-MM-DD, extras {name: {overtime, bonus, commission, unpaid_days, working_days, hours}} -> per person gross, tax, "
        "contributions, net, employer cost, the arithmetic; a draft. close: period (locks). payslip: period, employee. payments: period "
        "-> net to each person + to each authority (she pays). filings: year -> due dates from her rules, done / overdue. done: filing, "
        "for, on, reference (she filed). contractors: year, rows [{payee, amount, date, tax_id}] or contractors [names] from her bills, "
        "threshold, tax_ids -> totals, who to report, missing tax ids, CSV. "
        "v0.999.169 Payroll desk: desk (this period, inputs, what needs her); inputs (period, status checked|waiting); input_rows "
        "rows [{name, date, hours, overtime_hours, overtime, bonus, commission, unpaid_days, leave_days}] from a timesheet she gave - "
        "each row is checked (her people, the period, her hours limit, never twice); missing (who has no hours); prepare (period) = "
        "the run from her people + checked inputs, with changes from the last run; changes (period); rules (her country rules and "
        "which still need a check); starting_list (country) / apply_starting_list (country): the country's starting list, every rule "
        "marked 'check this' and not used until a person checks it on the desk. Approving a run, the payment file, payslip emails "
        "and checking a rule are HER taps on the Payroll desk - never say they are done. "
        "v0.999.171 every size: sources (where her people can come from and which programs are connected); people_text (text = pasted "
        "lines -> proposed people she ticks on the People page); import_view (import); history (past pay); parts (her pay parts, habits "
        "and the words a formula may use); part_save {name, kind earning|untaxed|pre_tax|deduction|employer, formula, applies_to all | "
        "department:X | location:X | company:X | people:id1,id2, new_words} - a formula uses numbers, + - * / ( ), min, max, round, "
        "`a ? b : c` and known words only; policy_save {days calendar|working|thirty, week_days, round_net, shift_start HH:MM, "
        "grace_min, day_hours, jump_pct, minimum_pay, overtime_from_punches}; propose_parts (text = her payslip / policy -> proposals, "
        "nothing saved); match_test (period YYYY-MM she already paid -> every person must match to the cent); preview (period) = "
        "'run the payroll preview': prepares, checks and reports (flags, changes, cash needed, by department) and tells her in this "
        "chat - say its line; report (period); history_report; group_view (every business). Checking and approving are her taps."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "workspace": {"type": "string"}, "country": {"type": "string"},
         "frequency": {"type": "string"}, "source": {"type": "string"},
         "contributions": {"type": "array", "items": {"type": "object"}}, "income_tax": {"type": "object"},
         "pre_tax": {"type": "array", "items": {"type": "string"}}, "filings": {"type": "array", "items": {"type": "object"}},
         "pay_day": {"type": "integer"}, "name": {"type": "string"}, "annual": {"type": "number"}, "per_period": {"type": "number"},
         "hourly": {"type": "number"}, "hours": {"type": "number"}, "pre_tax_pct": {"type": "number"}, "allowance": {"type": "number"},
         "tax_id": {"type": "string"}, "start": {"type": "string"}, "leave": {"type": "boolean"}, "left_on": {"type": "string"},
         "period": {"type": "string"}, "extras": {"type": "object"}, "employee": {"type": "string"}, "year": {"type": "integer"},
         "filing": {"type": "string"}, "for": {"type": "string"}, "on": {"type": "string"}, "reference": {"type": "string"},
         "rows": {"type": "array", "items": {"type": "object"}}, "contractors": {"type": "array", "items": {"type": "string"}},
         "threshold": {"type": "number"}, "tax_ids": {"type": "object"}, "basis": {"type": "string"},
         "status": {"type": "string"}, "source_name": {"type": "string"}, "file": {"type": "string"},
         "text": {"type": "string"}, "import": {"type": "string"}, "kind": {"type": "string"}, "formula": {"type": "string"},
         "applies_to": {"type": "string"}, "new_words": {"type": "array", "items": {"type": "string"}}, "days": {"type": "string"},
         "week_days": {"type": "integer"}, "round_net": {"type": "integer"}, "shift_start": {"type": "string"},
         "grace_min": {"type": "number"}, "day_hours": {"type": "number"}, "jump_pct": {"type": "number"},
         "minimum_pay": {"type": "number"}, "overtime_from_punches": {"type": "boolean"}, "months": {"type": "integer"},
         "tell": {"type": "boolean"}},
         "required": ["action"]}},
]
PAYROLLWIDE_LABELS = {"payroll_worldwide": "Working out the payroll"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import payroll as PY
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "payroll_worldwide", action, a, lambda: PY.run(tenant, action, a, actor))


async def _payroll_worldwide(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if action in _CHANGES and actor != "owner" and not actor.startswith("approved:"):
        raise ToolError("Changing the payroll is for the owner or someone she approved.")
    try:
        return await asyncio.to_thread(_work, ctx, action, a)
    except PermissionError as e:
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


PAYROLLWIDE_HANDLERS = {"payroll_worldwide": _payroll_worldwide}
