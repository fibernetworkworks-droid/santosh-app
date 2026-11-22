"""Paisa Sahayak (consumer finance protection) tool: `paisa_sahayak`. Everything is a CALCULATION or a CHECK on what she types or pastes:
nothing is stored, nothing is sent, no money moves, and no PIN / OTP / CVV / card number / password is ever asked for or kept.
It is education and tracking, not financial, tax or legal advice, and it never recommends a lender or a product.

Register: docs/research/banking_finance_industry/00_INDEX.md  (#1 money manager, #2 fee auditor, #3 loan reader, #5 debt planner,
#6 scam shield, #7 UPI coach, #8 complaint drafter).
"""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["loan", "compare", "flat", "prepay", "debts", "charges", "spend", "scam", "url", "upi", "complaint", "facts",
            "check_pay", "refund_claim", "card_dispute", "credit_dispute", "id_theft", "deposit_check", "case_prep", "cases"]
_GLOBAL = {"check_pay", "refund_claim", "card_dispute", "credit_dispute", "id_theft", "deposit_check", "case_prep", "cases"}
_STATEMENT = {"charges", "spend"}

FINGUARD_TOOLS = [
    {"name": "paisa_sahayak", "description": (
        "Consumer money-safety helper (calculations and checks; nothing is stored or sent; never moves money; not financial / tax / legal advice; "
        "never asks for or keeps a PIN, OTP, CVV, card number or password). action=loan: amount, rate (annual %), months, fee_pct, fee_fixed, "
        "fee_gst_pct (default 18, shown as ASSUMED), insurance, other_upfront, fees_deducted, balloon -> EMI, total cost, money actually received, "
        "APR on that money, flags. compare: offers [{name, amount, rate, months, fee_pct, ...}] -> total cost + APR side by side. flat: rate "
        "(a 'flat rate' quote), months -> the true reducing-balance rate. prepay: amount, rate, months, lump_amount, at_month, mode "
        "reduce_tenure|reduce_emi, charge_pct -> interest saved vs the charge. debts: debts [{name, balance, rate, min_payment}], extra_monthly, "
        "income_drop_pct -> snowball vs avalanche vs minimums. charges: text (CSV statement) or rows [{date, narration, debit, credit}] or file_id "
        "-> fee-like lines by kind, GST check, duplicates, yearly projection. spend: same input + overrides {word: category}, budget {category: amount} "
        "-> monthly in / out by category, recurring payments. scam: text (a message or what the caller said), sender -> scam family, the words that "
        "triggered it, links analysed (never opened), what to do. url: url. upi: scenario collect_request|qr_to_receive|refund|wrong_transfer|"
        "screen_share|autopay_mandate|limit. complaint: issue_type unauthorised_txn|failed_txn|charges|harassment|kyc_block|other, bank, branch, name, "
        "account (last 4 is enough), amount, txn_date, txn_ref, narrative, prior_complaint_no, prior_date, outcome, country, complained_on, final_answer_on -> a letter with [blanks], an "
        "evidence checklist and the escalation ladder (she sends it); with a country (ISO code) it uses that country's firm and ombudsman route instead. "
        "facts: the helplines / rules this uses, each marked verify. Helplines and scheme rules are from memory (verify: true): re-check the primary site. "
        "EVERY COUNTRY (country = two-letter code, e.g. GB US IN AE SG AU CA IE DE SA; any other code gets the steps that hold everywhere): "
        "check_pay: country, text (the message), sender, payee_new, pressure -> scam signs + who to call there if she already paid. "
        "refund_claim: country, txn_date, noticed_on, amount, bank, account (last 4), txn_ref, kind scam|unauthorised, narrative, name -> the "
        "refund letter under that country's scheme, time limits, evidence, route. card_dispute: country, txn_date or statement_date, amount, merchant, "
        "reason not_received|not_as_described|charged_twice|cancelled|unauthorised, contacted_on, bank, account -> dispute letter + time limit. "
        "credit_dispute: country, bureau, item, narrative, name, sent_on -> bureau dispute letter + answer time. id_theft: country, lost [phone, "
        "id, card...] -> recovery steps. deposit_check: country, balances [{bank, amount}] -> protected vs above the limit. case_prep (a bank / "
        "institution's staff): country, case_kind scam|dispute|complaint, opened_on, txn_date, evidence [..], workspace -> the case file, clocks, "
        "missing evidence; the decision is left to a named person. cases: her saved letters and cases. Country rules carry a level: a time limit is "
        "stated as a deadline only when a person confirmed it; otherwise Hoola shows the rule it has as not confirmed and says to check it. "
        "Letters are drafts she sends; nothing is filed, decided or paid."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "amount": {"type": "number"}, "rate": {"type": "number"}, "months": {"type": "integer"},
         "fee_pct": {"type": "number"}, "fee_fixed": {"type": "number"}, "fee_gst_pct": {"type": "number"}, "insurance": {"type": "number"},
         "other_upfront": {"type": "number"}, "fees_deducted": {"type": "boolean"}, "balloon": {"type": "number"},
         "offers": {"type": "array", "items": {"type": "object"}}, "lump_amount": {"type": "number"}, "at_month": {"type": "integer"},
         "mode": {"type": "string"}, "charge_pct": {"type": "number"}, "debts": {"type": "array", "items": {"type": "object"}},
         "extra_monthly": {"type": "number"}, "income_drop_pct": {"type": "number"}, "text": {"type": "string"},
         "rows": {"type": "array", "items": {"type": "object"}}, "file_id": {"type": "string"}, "overrides": {"type": "object"},
         "budget": {"type": "object"}, "sender": {"type": "string"}, "url": {"type": "string"}, "scenario": {"type": "string"},
         "issue_type": {"type": "string"}, "bank": {"type": "string"}, "branch": {"type": "string"}, "name": {"type": "string"},
         "account": {"type": "string"}, "txn_date": {"type": "string"}, "txn_ref": {"type": "string"}, "narrative": {"type": "string"},
         "prior_complaint_no": {"type": "string"}, "prior_date": {"type": "string"}, "outcome": {"type": "string"},
         "country": {"type": "string"}, "kind": {"type": "string"}, "noticed_on": {"type": "string"},
         "statement_date": {"type": "string"}, "merchant": {"type": "string"}, "reason": {"type": "string"},
         "contacted_on": {"type": "string"}, "complained_on": {"type": "string"}, "final_answer_on": {"type": "string"},
         "bureau": {"type": "string"}, "item": {"type": "string"}, "sent_on": {"type": "string"},
         "lost": {"type": "array", "items": {"type": "string"}}, "balances": {"type": "array", "items": {"type": "object"}},
         "case_kind": {"type": "string"}, "opened_on": {"type": "string"}, "evidence": {"type": "array", "items": {"type": "string"}},
         "workspace": {"type": "string"}, "payee_new": {"type": "boolean"}, "pressure": {"type": "boolean"}},
         "required": ["action"]}},
]
FINGUARD_LABELS = {"paisa_sahayak": "Checking accounts with Paisa Sahayak"}


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _rows_of(ctx: Ctx, a: dict[str, Any]) -> list[dict[str, Any]]:
    from ..finguard import statement as ST
    if a.get("rows"):
        return list(a["rows"])[:5000]
    if a.get("text"):
        return ST.parse_csv(str(a["text"]))
    if a.get("file_id"):
        from ..analyst import service as AN
        name, data = AN._load_file(ctx.tenant_id, str(a["file_id"]))
        if name.lower().endswith((".csv", ".txt")):
            return ST.parse_csv(data.decode("utf-8", "ignore"))
        grid = AN._rows(name, data)
        import csv
        import io
        buf = io.StringIO()
        csv.writer(buf).writerows(grid)
        return ST.parse_csv(buf.getvalue())
    raise ValueError("Give the statement: text (CSV), rows, or file_id.")


def _sync(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..finguard import complaint as CP
    from ..finguard import loans as LN
    from ..finguard import scam as SC
    from ..finguard import statement as ST
    if action in _GLOBAL or (action == "complaint" and a.get("country")):
        from ..fin.desks import safety as SF
        return SF.run(getattr(ctx, "tenant_id", "") or "default", "complaint_global" if action == "complaint" else action, a)
    if action == "loan":
        return LN.true_cost(a.get("amount"), a.get("rate"), a.get("months"), fee_pct=a.get("fee_pct", 0), fee_fixed=a.get("fee_fixed", 0),
                            fee_gst_pct=a.get("fee_gst_pct"), insurance=a.get("insurance", 0), other_upfront=a.get("other_upfront", 0),
                            fees_deducted=a.get("fees_deducted", True) is not False, balloon=a.get("balloon", 0))
    if action == "compare":
        return LN.compare(a.get("offers"))
    if action == "flat":
        return LN.flat_to_reducing(a.get("rate"), a.get("months"))
    if action == "prepay":
        return LN.prepay(a.get("amount"), a.get("rate"), a.get("months"), a.get("lump_amount"), a.get("at_month"), a.get("mode") or "reduce_tenure",
                         a.get("charge_pct", 0))
    if action == "debts":
        return LN.debt_plan(a.get("debts"), a.get("extra_monthly", 0), a.get("income_drop_pct", 0))
    if action == "charges":
        return ST.charges(_rows_of(ctx, a))
    if action == "spend":
        return ST.spend(_rows_of(ctx, a), a.get("overrides"), a.get("budget"))
    if action == "scam":
        return SC.check(a.get("text"), a.get("sender", ""))
    if action == "url":
        return SC.analyse_url(str(a.get("url") or ""))
    if action == "upi":
        return SC.upi_coach(a.get("scenario", ""))
    if action == "complaint":
        keys = ("issue_type", "bank", "branch", "name", "account", "amount", "txn_date", "txn_ref", "narrative", "prior_complaint_no", "prior_date", "outcome")
        return CP.draft({k: a.get(k) for k in keys})
    if action == "facts":
        return {"facts": SC.FACTS, "ladder": CP.LADDER, "always": SC.HEADLINE_RULES,
                "note": "Items marked verify: true are from memory; check them again on the primary site."}
    raise ToolError(f"Unknown action '{action}'.")



def _core(ctx: Ctx, tool: str, action: str, a: dict[str, Any], work):
    """F0 of FINANCE_GLOBAL_PLAN: the laws gate + one audit row around the same work (results unchanged)."""
    from ..fin import core
    return core.run_tool(getattr(ctx, "tenant_id", "") or "default", getattr(ctx, "actor", "owner") or "owner", tool, action, a, work)

async def _paisa_sahayak(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action in _STATEMENT and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Statements are for the owner only.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    try:
        return await asyncio.to_thread(_core, ctx, "paisa_sahayak", action, a, lambda: _sync(ctx, action, a))
    except PermissionError as e:   # fin.laws.Refused: a tier C act or a secret
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


FINGUARD_HANDLERS = {"paisa_sahayak": _paisa_sahayak}
