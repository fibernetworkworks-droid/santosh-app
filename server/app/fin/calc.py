"""One calculation API for every finance employee (plan 4.4). Arithmetic is done here, in code, never by the model.

`run(name, **inputs)` -> {"result", "trace"}: the trace names the function, its version and the inputs it used, so a figure in a reply
can be traced. The registry wraps the tested engines already in Hoola (finguard, finops, riskdesk) - the same functions, so their
tools' results do not change - plus the money helpers every new part needs."""
from __future__ import annotations

import importlib
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable

from . import pack as P

VERSION = "f0.1"

# name -> "module:function" (lazy, so importing calc never loads every engine)
REGISTRY: dict[str, str] = {
    "loan.emi": "app.finguard.loans:emi", "loan.schedule": "app.finguard.loans:schedule",
    "loan.true_cost": "app.finguard.loans:true_cost", "loan.flat_to_reducing": "app.finguard.loans:flat_to_reducing",
    "loan.compare": "app.finguard.loans:compare", "loan.prepay": "app.finguard.loans:prepay", "debt.plan": "app.finguard.loans:debt_plan",
    "statement.charges": "app.finguard.statement:charges", "statement.spend": "app.finguard.statement:spend",
    "goal.plan": "app.finops.goals:goal", "tax.advance_india": "app.finops.goals:advance_tax",
    "tax.tds_reconcile": "app.finops.tax:tds_reconcile", "ledger.ageing": "app.finops.ledger:ageing",
    "ledger.three_way": "app.finops.ledger:three_way", "aml.triage": "app.finops.aml:triage", "aml.screen": "app.finops.aml:screen",
    "credit.ratios": "app.finops.credit:ratios", "credit.memo": "app.finops.credit:memo",
    "credit.underwrite": "app.riskdesk.credit:underwrite", "credit.kfs": "app.riskdesk.credit:kfs", "credit.dpd": "app.riskdesk.credit:dpd",
    "credit.ecl": "app.riskdesk.credit:ecl", "order.ticket": "app.riskdesk.orders:ticket", "portfolio.drift": "app.riskdesk.orders:drift",
    "valuation.dcf": "app.riskdesk.valuation:dcf", "watch.velocity": "app.riskdesk.watch:velocity", "watch.round_trips": "app.riskdesk.watch:wash",
    "money.to_minor": "app.fin.calc:to_minor", "money.from_minor": "app.fin.calc:from_minor", "money.fx": "app.fin.calc:fx",
    "money.split": "app.fin.calc:split",
}


class CalcError(ValueError):
    pass


def fn(name: str) -> Callable[..., Any]:
    ref = REGISTRY.get(name)
    if not ref:
        raise CalcError(f"No calculation '{name}'.")
    mod, attr = ref.split(":")
    return getattr(importlib.import_module(mod), attr)


def call(name: str, *args: Any, **kw: Any) -> Any:
    """The plain result - what the old tools return, byte for byte."""
    return fn(name)(*args, **kw)


def run(name: str, **kw: Any) -> dict[str, Any]:
    result = call(name, **kw)
    return {"result": result, "trace": {"calc": name, "fn": REGISTRY[name], "version": VERSION,
                                        "inputs": sorted(k for k, v in kw.items() if v is not None)}}


# ---- money (integer minor units, never a float in storage) --------------------------------------------------------------------

def _dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v).replace(",", "").strip())
    except Exception:
        raise CalcError(f"Not a number: {v!r}")


def to_minor(amount: Any, currency: str) -> int:
    units = P.minor_unit(currency)
    q = _dec(amount).scaleb(units).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(q)


def from_minor(minor: int, currency: str) -> Decimal:
    return Decimal(int(minor)).scaleb(-P.minor_unit(currency))


def fx(amount_minor: int, from_cur: str, to_cur: str, rate: Any, rate_date: str = "", source: str = "") -> dict[str, Any]:
    """Convert at a rate she or a source gave (no rate is ever invented). Rounded half-up in the target currency."""
    if not source or not rate_date:
        raise CalcError("A conversion needs the rate's date and source.")
    r = _dec(rate)
    if r <= 0:
        raise CalcError("Rate must be above zero.")
    out = to_minor(from_minor(amount_minor, from_cur) * r, to_cur)
    return {"amount_minor": out, "currency": to_cur.upper(), "rate": str(r), "rate_date": rate_date, "source": source,
            "from_minor": int(amount_minor), "from_currency": from_cur.upper()}


def split(amount_minor: int, parts: list[Any]) -> list[int]:
    """Split by weights so the pieces add up exactly (largest remainder)."""
    ws = [_dec(p) for p in parts]
    tot = sum(ws)
    if not ws or tot <= 0:
        raise CalcError("Weights must add up to more than zero.")
    raw = [Decimal(int(amount_minor)) * w / tot for w in ws]
    base = [int(x) for x in raw]
    left = int(amount_minor) - sum(base)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - base[i], reverse=True)
    for i in order[:left]:
        base[i] += 1
    return base
