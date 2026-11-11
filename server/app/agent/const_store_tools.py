"""v0.512.0 const_store tools (#61 Material Planner & Store Manager). `const_store_dekho` only reads;
`const_store` does the work. Tier A: GRN / issue / reconciliation with the reorder alerts - the store
in-charge signs the sheet; Hoola never invents a rate, a quantity or a vendor."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

STORE_TOOLS = [
    {"name": "const_store", "description": (
        "Material store accounts (construction store in-charge's desk). action=lot: item, unit, min_qty "
        "(reorder level), max_qty (storage cap). action=grn: item, qty, rate, vendor, invoice_no (challan), vehicle, "
        "site, day, ok (quantity / quality checked), note - stock goes up. action=issue: item, qty, site, gang, "
        "purpose, day, waste (true = written-off), note - stock goes down (never takes more than the stock). action=reconcile: "
        "item (optional) - received vs issued vs left, wastage %, REORDER alerts. Hoola does not pay; the order goes only on your "
        "approval (indent card in sitesup)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["lot", "grn", "issue", "reconcile"]},
         "item": {"type": "string"}, "unit": {"type": "string"}, "min_qty": {"type": "number"}, "max_qty": {"type": "number"},
         "qty": {"type": "number"}, "rate": {"type": "number"}, "vendor": {"type": "string"}, "invoice_no": {"type": "string"},
         "vehicle": {"type": "string"}, "site": {"type": "string"}, "day": {"type": "string"}, "ok": {"type": "boolean"},
         "gang": {"type": "string"}, "purpose": {"type": "string"}, "waste": {"type": "boolean"}, "note": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_store_dekho", "description": (
        "Read the material store (nothing changes). what=stock (every lot with balance + reorder flag) | "
        "reconcile (item optional: received vs issued vs on-hand vs wastage %)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["stock", "reconcile"]}, "item": {"type": "string"}},
         "required": ["what"]}},
]
STORE_LABELS = {"const_store": "Writing the store accounts", "const_store_dekho": "Checking the store"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import store as S
    from ..construction.common import guard
    from .tools import ToolError as _TE
    guard(f"{action} store")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "lot":
            return S.upsert_lot(t, _s(a.get("item")), _s(a.get("unit")), a.get("min_qty"), a.get("max_qty"), _s(a.get("note")))
        if action == "grn":
            return S.grn(t, _s(a.get("item")), a.get("qty"), a.get("rate"), _s(a.get("vendor")), _s(a.get("invoice_no")),
                         _s(a.get("vehicle")), _s(a.get("site")), _s(a.get("day")), bool(a.get("ok", True)),
                         _s(a.get("note")), _s(a.get("by")), conv)
        if action == "issue":
            return S.issue(t, _s(a.get("item")), a.get("qty"), _s(a.get("site")), _s(a.get("gang")), _s(a.get("purpose")),
                           _s(a.get("day")), bool(a.get("waste")), _s(a.get("by")), _s(a.get("note")), conv)
        if action == "reconcile":
            return S.reconcile(t, _s(a.get("item")))
    except (S.CstError, ValueError) as ex:
        raise _TE(str(ex))
    raise _TE("unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import store as S
    from .tools import ToolError as _TE
    t = ctx.tenant_id
    try:
        if what == "stock":
            return {"lots": S.lots(t)}
        if what == "reconcile":
            return S.reconcile(t, _s(a.get("item")))
    except (S.CstError, ValueError) as ex:
        raise _TE(str(ex))
    raise _TE("unknown what")


async def const_store(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_store_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


STORE_HANDLERS = {"const_store": const_store, "const_store_dekho": const_store_dekho}
