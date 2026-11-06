"""v0.531.0 const_contracts tools (C10: #44 register + obligations + #45 variations + #46 claims
working papers + #51 insurance/bonds row). Variation approval records the CLIENT's name; the claim
paper carries her entitlement matrix + the notice-compliance arithmetic - entitlement itself is
counsel's conclusion (tier C refusals ride gates.py)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

CONTRACTS_TOOLS = [
    {"name": "const_contracts", "description": (
        "Contracts desk: register, obligations with the chase, variation papers (DRAFT), claims working papers. "
        "action=contract: name, party, role employer|contractor|sub-contractor, value, signed_on, start_on, end_on, "
        "notice_days, ref. action=oblig: contract, obligation, due_on, owner_side (true=hamara). action=oblig_done: "
        "oblig (id), on. action=oblig_due: days (late pehle). action=variation: contract, desc, basis (SOR/quoted/"
        "daywork), qty, rate -> DRAFT (approve CLIENT karega; unke naam se record hota hai). action=variation_mark: "
        "variation (id), status draft|submitted|approved|rejected, approved_by (client ka naam). action=claim: contract, "
        "cause, event_on, noticed_on, matrix [{event, clause, effect, evidence}] -> notice-compliance ka hisaab; "
        "entitlement ka faisla advocate ka. action=insured: contract, note (bonds/insurance yahin record). "
        "Wave 4 #48: action=ld_calc: project, contract_ref, delay_days, ld_pct_per_week, contract_value, "
        "cap_pct, sources (clause no) -> arithmetic + cap check; LD kaatna tier C. #50: action=arb_bundle_add: "
        "project, claim, rows [date, evidence, exhibit], by -> bundle index (case counsel ka); "
        "action=arb_bundle: project, claim -> index padho."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["contract", "oblig", "oblig_done", "oblig_due", "variation",
                                               "variation_mark", "claim", "insured", "ld_calc",
                                               "arb_bundle_add", "arb_bundle"]},
         "name": {"type": "string"}, "party": {"type": "string"}, "role": {"type": "string"},
         "value": {"type": "number"}, "signed_on": {"type": "string"}, "start_on": {"type": "string"},
         "end_on": {"type": "string"}, "notice_days": {"type": "number"}, "ref": {"type": "string"},
         "contract": {"type": "string"}, "obligation": {"type": "string"}, "due_on": {"type": "string"},
         "owner_side": {"type": "boolean"}, "note": {"type": "string"}, "oblig": {"type": "string"},
         "on": {"type": "string"}, "days": {"type": "number"}, "desc": {"type": "string"}, "basis": {"type": "string"},
         "qty": {"type": "number"}, "rate": {"type": "number"}, "variation": {"type": "string"},
         "status": {"type": "string"}, "approved_by": {"type": "string"}, "cause": {"type": "string"},
         "delay_days": {"type": "number"}, "cap_pct": {"type": "number"}, "claim": {"type": "string"},
         "pct": {"type": "number"},
         "rows": {"type": "array", "items": {}}, "by": {"type": "string"},
         "event_on": {"type": "string"}, "noticed_on": {"type": "string"},
         "matrix": {"type": "array", "items": {"type": "object"}}},
         "required": ["action"]}},
    {"name": "const_contracts_dekho", "description": (
        "Read contracts desk (nothing changes). what=day | contracts | obligs (contract optional) | variations | "
        "claims (contract optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "contracts", "obligs", "variations", "claims"]},
         "contract": {"type": "string"}}, "required": ["what"]}},
]
CONTRACTS_LABELS = {"const_contracts": "Contract ka record dekh raha hoon", "const_contracts_dekho": "Contracts dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import contracts as K
    from ..construction.common import guard
    guard(f"{action} contracts")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "contract":
            return K.contract_new(t, _s(a.get("name")), _s(a.get("party")), _s(a.get("role")) or "contractor",
                                  a.get("value"), _s(a.get("signed_on")), _s(a.get("start_on")),
                                  _s(a.get("end_on")), a.get("notice_days"), _s(a.get("ref")), conv)
        if action == "oblig":
            return K.oblig_add(t, _s(a.get("contract")), _s(a.get("obligation")), _s(a.get("due_on")),
                               bool(a.get("owner_side", True)), _s(a.get("note")))
        if action == "oblig_done":
            return K.oblig_done(t, _s(a.get("oblig")), _s(a.get("on")))
        if action == "oblig_due":
            return K.oblig_due(t, int(a.get("days") or 7))
        if action == "variation":
            return K.variation_draft(t, _s(a.get("contract")), _s(a.get("desc")), _s(a.get("basis")),
                                     a.get("qty"), a.get("rate"), _s(a.get("ref")), conv)
        if action == "variation_mark":
            return K.variation_mark(t, _s(a.get("variation")), _s(a.get("status")), _s(a.get("approved_by")))
        if action == "claim":
            return K.claim_paper(t, _s(a.get("contract")), _s(a.get("cause")), _s(a.get("event_on")),
                                 _s(a.get("noticed_on")), a.get("notice_days"), a.get("matrix"), conv)
        if action == "insured":
            # #51 Insurance & Bonds Coordinator row: the policy / bond rides the contract's obligations
            what = f"insurance/bond: {_s(a.get('note'))[:160]}" if a.get("note") else "insurance/bond"
            return K.oblig_add(t, _s(a.get("contract")), what,
                               _s(a.get("due_on")) or _s(a.get("end_on")), True, "insurance & bonds row")

        if action == "ld_calc":
            return K.ld_calc(t, _s(a.get("project")), _s(a.get("ref")), int(a.get("delay_days") or 0),
                             float(a.get("pct") or 0), float(a.get("value") or 0),
                             float(a.get("cap_pct") or 0) if a.get("cap_pct") is not None else 0.0,
                             _s(a.get("basis")))
        if action == "arb_bundle_add":
            return K.arb_bundle_add(t, _s(a.get("project")), _s(a.get("claim")), a.get("rows") or [],
                                    _s(a.get("approved_by")), conv)
        if action == "arb_bundle":
            return K.arb_bundle(t, _s(a.get("project")), _s(a.get("claim")))
    except (K.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import contracts as K
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CContract, CContrClaim, CContrOblig, CContrVariation
    t = ctx.tenant_id
    guard(f"read contracts {what}")
    try:
        if what == "day":
            return K.day(t)
        if what == "contracts":
            with session() as s:
                rows = s.scalars(select(CContract).where(CContract.tenant_id == t)).all()
            return {"contracts": [{"id": r.id, "name": r.name, "party": r.party, "role": r.role, "value": r.value,
                                   "end_on": r.end_on, "notice_days": r.notice_days, "status": r.status}
                                  for r in rows]}
        if what == "obligs":
            with session() as s:
                rows = s.scalars(select(CContrOblig).where(CContrOblig.tenant_id == t)).all()
            c = _s(a.get("contract"))
            if c:
                rows = [r for r in rows if r.contract_id == c]
            return {"obligs": [{"id": r.id, "obligation": r.obligation[:100], "due_on": r.due_on,
                                "side": "hamara" if r.owner_side else "unka", "status": r.status} for r in rows]}
        if what == "variations":
            with session() as s:
                rows = s.scalars(select(CContrVariation).where(CContrVariation.tenant_id == t)).all()
            return {"variations": [{"id": r.id, "desc": r.desc[:100], "amount": r.amount, "basis": r.basis[:60],
                                    "status": r.status, "approved_by": r.approved_by} for r in rows]}
        if what == "claims":
            with session() as s:
                rows = s.scalars(select(CContrClaim).where(CContrClaim.tenant_id == t)).all()
            c = _s(a.get("contract"))
            if c:
                rows = [r for r in rows if r.contract_id == c]
            return {"claims": [{"id": r.id, "cause": r.cause[:100], "event_on": r.event_on,
                                "noticed_on": r.noticed_on, "status": r.status} for r in rows]}
    except (K.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def const_contracts(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_contracts_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


CONTRACTS_HANDLERS = {"const_contracts": const_contracts, "const_contracts_dekho": const_contracts_dekho}
