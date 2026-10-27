"""v0.110 Niryat Sahayak tools (exporter). `niryat_dekho` only reads; `niryat` does the work. The PI reaches the buyer and the
commercial invoice is made only on HER Haan. Shipping bill, certificate of origin, e-BRC and forward contracts are hers /
her CHA's / her AD bank's; Hoola never touches money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

NIRYAT_TOOLS = [
    {"name": "niryat", "description": (
        "Exporter's coworker, end to end. action=settings: firm, address, iec, gstin, phone, email, ad_bank, lut_no (this FY), "
        "rcmc, rcmc_valid_to, prefix. action=buyer: name or buyer (to update), country (name or ISO code), address, email, phone, "
        "currency USD|EUR|GBP|AED|..., pay_terms advance|lc|dp|da|open|part, credit_days. action=pi: buyer, lines [{item, hs "
        "(8-digit ITC-HS), qty, unit, rate (foreign currency), net_kg, gross_kg, packages, rodtep_pct, rodtep_cap}] or text "
        "('Haldi powder 2000 kg @ 2.10 HS 09103030'), incoterm FOB|CIF|CFR|EXW|FCA|DAP|DDP..., place, fx (rupees per unit), "
        "freight, insurance, gst_mode lut|igst, port_loading, port_discharge, mode sea|air -> PI PDF + checks. action=send_pi: "
        "shipment (ONLY when she says it may go: message draft she sends). action=confirm: shipment, inv_date, fx (ONLY on her "
        "haan: commercial invoice + packing list). action=shipped: shipment, sb_no, sb_date, bl_no, ship_date, fx (customs rate). "
        "action=receive: shipment, amount (foreign currency), inr, on, ref (IRM / e-BRC). action=cancel: shipment, reason. "
        "action=register (Excel)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "buyer", "pi", "send_pi", "confirm", "shipped", "receive", "cancel", "register"]},
         "firm": {"type": "string"}, "address": {"type": "string"}, "iec": {"type": "string"}, "gstin": {"type": "string"},
         "phone": {"type": "string"}, "email": {"type": "string"}, "ad_bank": {"type": "string"}, "lut_no": {"type": "string"},
         "rcmc": {"type": "string"}, "rcmc_valid_to": {"type": "string"}, "prefix": {"type": "string"}, "name": {"type": "string"},
         "buyer": {"type": "string"}, "country": {"type": "string"}, "currency": {"type": "string"}, "pay_terms": {"type": "string"},
         "credit_days": {"type": "integer"}, "lines": {"type": "array", "items": {"type": "object"}}, "text": {"type": "string"},
         "incoterm": {"type": "string"}, "place": {"type": "string"}, "fx": {"type": "number"}, "freight": {"type": "number"},
         "insurance": {"type": "number"}, "gst_mode": {"type": "string"}, "port_loading": {"type": "string"},
         "port_discharge": {"type": "string"}, "mode": {"type": "string"}, "shipment": {"type": "string"}, "inv_date": {"type": "string"},
         "sb_no": {"type": "string"}, "sb_date": {"type": "string"}, "bl_no": {"type": "string"}, "ship_date": {"type": "string"},
         "amount": {"type": "number"}, "inr": {"type": "number"}, "on": {"type": "string"}, "ref": {"type": "string"},
         "reason": {"type": "string"}, "notes": {"type": "string"}},
         "required": ["action"]}},
    {"name": "niryat_dekho", "description": (
        "Read export work (nothing changes). what=day (LUT, RCMC, realisation dues, PIs waiting) | shipments (status pi|confirmed|"
        "shipped|realised, buyer) | shipment (shipment) | realisation (RBI 9-month dates + reminder drafts) | buyers | settings | "
        "incoterms | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "shipments", "shipment", "realisation", "buyers", "settings", "incoterms", "rules"]},
         "status": {"type": "string"}, "buyer": {"type": "string"}, "shipment": {"type": "string"}},
         "required": ["what"]}},
]
NIRYAT_LABELS = {"niryat": "Export ka kaam kar raha hoon", "niryat_dekho": "Export file dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..niryat import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    sh = _s(a.get("shipment"))
    try:
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            keys = ("firm", "address", "iec", "gstin", "phone", "email", "ad_bank", "lut_no", "rcmc", "rcmc_valid_to", "prefix")
            return S.save_settings(t, **{k: a[k] for k in keys if k in a})
        if action == "buyer":
            return S.save_buyer(t, _s(a.get("name")), _s(a.get("buyer")), _s(a.get("country")), _s(a.get("address")), _s(a.get("email")),
                                _s(a.get("phone")), _s(a.get("currency")), _s(a.get("pay_terms")), a.get("credit_days"), _s(a.get("notes")))
        if action == "pi":
            return S.proforma(t, _s(a.get("buyer")), a.get("lines"), _s(a.get("text")), _s(a.get("incoterm")) or "FOB", _s(a.get("place")),
                              a.get("fx"), a.get("freight"), a.get("insurance"), _s(a.get("gst_mode")) or "lut", _s(a.get("port_loading")),
                              _s(a.get("port_discharge")), _s(a.get("mode")) or "sea", _s(a.get("currency")), conv)
        if action == "send_pi":
            if not _owner(ctx):
                raise ToolError("Buyer ko PI bhejne ki haan sirf owner.")
            return S.pi_draft(t, sh)
        if action == "confirm":
            if not _owner(ctx):
                raise ToolError("Invoice banane ki haan sirf owner.")
            return S.confirm(t, sh, _s(a.get("inv_date")), a.get("fx"), conv)
        if action == "shipped":
            return S.shipped(t, sh, _s(a.get("sb_no")), _s(a.get("sb_date")), _s(a.get("bl_no")), _s(a.get("ship_date")), a.get("fx"))
        if action == "receive":
            return S.receive(t, sh, a.get("amount"), a.get("inr"), _s(a.get("on")), _s(a.get("ref")))
        if action == "cancel":
            return S.cancel(t, sh, _s(a.get("reason")))
        if action == "register":
            return S.register_file(t, conv)
    except (S.NiryatError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..niryat import rules as R
    from ..niryat import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "shipments":
            return {"shipments": S.shipments(t, _s(a.get("status")), _s(a.get("buyer")))}
        if what == "shipment":
            return S.get_shipment(t, _s(a.get("shipment")))
        if what == "realisation":
            return S.realisation(t)
        if what == "buyers":
            return {"buyers": S.buyers(t)}
        if what == "settings":
            return S.settings(t)
        if what == "incoterms":
            return {"incoterms": R.INCOTERMS, "pay_terms": R.PAY_TERMS}
        if what == "rules":
            return {"never": list(R.NEVER), "realise_months": R.REALISE_MONTHS, "realise_months_inr": R.REALISE_MONTHS_INR,
                    "rodtep_until": R.RODTEP_UNTIL.isoformat(), "fta": R.FTA}
    except (S.NiryatError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def niryat(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def niryat_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


NIRYAT_HANDLERS = {"niryat": niryat, "niryat_dekho": niryat_dekho}
