"""Logistics Sahayak tools. `logistics_dekho` only reads; `logistics` does the work. Customer messages are drafts SHE sends (or her
tap on business WhatsApp in the app); an e-way bill filing (generate / Part B / extend / consolidated) is only a card here: it goes
to the portal by her tap in the app. Tracking statuses come only from her / transporter / driver / courier, never made up."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_SHIP_PROPS = {
    "shipment": {"type": "string", "description": "S-0001 / LR / invoice no / vehicle no / AWB / EWB no"},
    "consignee": {"type": "string"}, "consignee_gstin": {"type": "string"}, "consignee_address": {"type": "string"},
    "consignee_place": {"type": "string"}, "consignee_pincode": {"type": "string"}, "consignee_phone": {"type": "string"},
    "consignee_state": {"type": "string"}, "consignor": {"type": "string"}, "consignor_gstin": {"type": "string"},
    "consignor_place": {"type": "string"},
    "goods": {"type": "array", "items": {"type": "object"}, "description": "[{name, hsn, qty, unit, value (taxable), gst %}]"},
    "goods_text": {"type": "string", "description": "e.g. 'cement 120 bag @ 380, sariya 2 ton'"},
    "value": {"type": "number"}, "tax": {"type": "number"}, "thok_order": {"type": "string", "description": "Thok bill number / id"},
    "direction": {"type": "string", "enum": ["out", "in", "carry"]},
    "doc_type": {"type": "string", "enum": ["invoice", "bill_of_supply", "challan", "bill_of_entry", "other"]},
    "doc_no": {"type": "string"}, "doc_date": {"type": "string"},
    "reason": {"type": "string", "description": "supply | job_work | own_use | job_work_return | sales_return | line_sales | exhibition | others"},
    "weight_kg": {"type": "number"}, "packages": {"type": "integer"}, "package_kind": {"type": "string"},
    "mode": {"type": "string", "enum": ["road", "rail", "air", "ship", "courier"]}, "fleet": {"type": "string", "enum": ["own", "hired", "courier"]},
    "transporter_name": {"type": "string"}, "transporter_gstin": {"type": "string"}, "transporter_phone": {"type": "string"},
    "vehicle_no": {"type": "string"}, "odc": {"type": "boolean"}, "driver_name": {"type": "string"}, "driver_phone": {"type": "string"},
    "courier": {"type": "string"}, "awb": {"type": "string"}, "lr_no": {"type": "string"}, "freight": {"type": "number"},
    "freight_by": {"type": "string", "enum": ["paid", "to_pay", "tbb"]}, "from_place": {"type": "string"}, "to_place": {"type": "string"},
    "distance_km": {"type": "number"}, "dispatch": {"type": "string"}, "eta": {"type": "string", "description": "her words: 'kal shaam', '25-10 6 pm', '2 din'"},
    "note": {"type": "string"},
}

LOGISTICS_TOOLS = [
    {"name": "logistics", "description": (
        "Logistics coordinator (trader / manufacturer / transporter): shipments, dispatch papers, e-way bill readiness, tracking, "
        "customer updates. action=settings (owner): firm, role trader|manufacturer|transporter, gstin, address, place, pincode, phone, "
        "carrier_reg (Carriage by Road Act registration), gta_rate 5|18, lr_prefix, dc_prefix, grace_h, silent_h, morning_time, terms. "
        "action=party: name or party, gstin, address, place, pincode, phone, kind customer|supplier|transporter, trans_id, no_messages. "
        "action=new: consignee + shipment fields (or thok_order = a billed Thok invoice). action=edit: shipment + fields. "
        "action=update: shipment, status (booked|loaded|dispatched|in_transit|reached_hub|out_for_delivery|delivered|held|breakdown|"
        "delayed|returned) or text = HER / the driver's / transporter's real words, where, eta, at, source her|driver|transporter, "
        "reason (for a delay). NEVER invent a status or place. action=location: shipment, text (the location link she forwarded). "
        "action=track: shipment (courier AWB via the courier desk). action=draft: shipment, kind dispatch|in_transit|delay|"
        "out_for_delivery|delivered|custom, text (custom), reason, where -> a customer message draft SHE sends. action=sent: message_id "
        "(she sent it herself). action=docs: shipment, which [lr, challan, packing, invoice, ewb_json]. action=ewb_ready: shipment. "
        "action=ewb: shipment, kind generate|part_b|extend|consolidated, vehicle_no, reason, from_place, from_state, from_pincode, "
        "remaining_km, shipments (more refs for consolidated) -> ONLY a card for her tap (say so; never say it is filed). "
        "action=ewb_number (owner): shipment, ewb_no (12 digits she made on the portal), valid_upto, generated. action=pod: shipment, "
        "file_id (photo she sent), receiver, remarks, short, damaged. action=cancel: shipment, reason. action=register (Excel)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "party", "new", "edit", "update", "location", "track", "draft", "sent", "docs",
                                               "ewb_ready", "ewb", "ewb_number", "pod", "cancel", "register"]},
         **_SHIP_PROPS,
         "firm": {"type": "string"}, "role": {"type": "string"}, "gstin": {"type": "string"}, "address": {"type": "string"},
         "place": {"type": "string"}, "pincode": {"type": "string"}, "phone": {"type": "string"}, "carrier_reg": {"type": "string"},
         "gta_rate": {"type": "number"}, "lr_prefix": {"type": "string"}, "dc_prefix": {"type": "string"}, "grace_h": {"type": "number"},
         "silent_h": {"type": "number"}, "morning_time": {"type": "string"}, "terms": {"type": "string"},
         "name": {"type": "string"}, "party": {"type": "string"}, "kind": {"type": "string"}, "trans_id": {"type": "string"},
         "no_messages": {"type": "boolean"}, "status": {"type": "string"}, "text": {"type": "string"}, "where": {"type": "string"},
         "at": {"type": "string"}, "source": {"type": "string", "enum": ["her", "driver", "transporter"]}, "message_id": {"type": "string"},
         "which": {"type": "array", "items": {"type": "string"}}, "from_state": {"type": "string"}, "from_pincode": {"type": "string"},
         "remaining_km": {"type": "number"}, "shipments": {"type": "array", "items": {"type": "string"}}, "ewb_no": {"type": "string"},
         "valid_upto": {"type": "string"}, "generated": {"type": "string"}, "file_id": {"type": "string"}, "receiver": {"type": "string"},
         "remarks": {"type": "string"}, "short": {"type": "number"}, "damaged": {"type": "boolean"}},
         "required": ["action"]}},
    {"name": "logistics_dekho", "description": (
        "Read logistics (nothing changes). what=board (today's dispatches, moving, late vs ETA, e-way bill expiry, delivered without "
        "POD, cards / drafts waiting) | shipments (status open|delivered|..., q) | shipment (shipment: timeline, papers, EWB, drafts) | "
        "ewb_ready (shipment) | parties (kind, q) | ontime (per transporter, from real trips) | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["board", "shipments", "shipment", "ewb_ready", "parties", "ontime", "settings", "rules"]},
         "status": {"type": "string"}, "q": {"type": "string"}, "shipment": {"type": "string"}, "kind": {"type": "string"}},
         "required": ["what"]}},
]
LOGISTICS_LABELS = {"logistics": "Maal ki dispatch / tracking sambhal raha hoon", "logistics_dekho": "Shipments dekh raha hoon"}

_SHIP_KEYS = tuple(k for k in _SHIP_PROPS if k not in ("shipment", "consignee", "goods", "goods_text", "thok_order"))


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..logistics import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    ref = _s(a.get("shipment"))
    try:
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return S.save_settings(t, **{k: a[k] for k in S.SETTING_KEYS if k in a})
        if action == "party":
            keys = ("gstin", "address", "place", "pincode", "phone", "kind", "trans_id", "no_messages", "state")
            return S.save_party(t, _s(a.get("name")), _s(a.get("party")), **{k: a[k] for k in keys if k in a})
        if action == "new":
            return S.new_shipment(t, _s(a.get("consignee")), a.get("goods"), _s(a.get("goods_text")), _s(a.get("thok_order")), conv,
                                  **{k: a[k] for k in _SHIP_KEYS if k in a})
        if action == "edit":
            kw = {k: a[k] for k in _SHIP_KEYS if k in a}
            for k in ("goods", "goods_text"):
                if k in a:
                    kw[k] = a[k]
            return S.update_shipment(t, ref, conv, **kw)
        if action == "update":
            return S.update(t, ref, _s(a.get("status")), _s(a.get("text")), _s(a.get("where")), _s(a.get("eta")), _s(a.get("at")),
                            by=_actor(ctx), source=_s(a.get("source")) or "her", conv=conv, reason=_s(a.get("reason")))
        if action == "location":
            return S.location(t, ref, _s(a.get("text")), _s(a.get("source")) or "driver", conv)
        if action == "track":
            return S.track(t, ref, conv)
        if action == "draft":
            return S.draft(t, ref, _s(a.get("kind")) or "in_transit", conv, _s(a.get("reason")), _s(a.get("where")), _s(a.get("text")))
        if action == "sent":
            return S.message_sent(t, _s(a.get("message_id")))
        if action == "docs":
            return S.documents(t, ref, a.get("which") or None, conv)
        if action == "ewb_ready":
            return S.ewb_ready(t, ref)
        if action == "ewb":
            r = S.ewb_request(t, ref, _s(a.get("kind")) or "generate", _s(a.get("vehicle_no")), _s(a.get("reason")), _s(a.get("from_place")),
                              _s(a.get("from_state")), _s(a.get("from_pincode")), a.get("remaining_km"), a.get("shipments"), conv)
            return {"status": "needs_tap", "say": r["say"], "ask_id": r["ask"]["id"]}
        if action == "ewb_number":
            if not _owner(ctx):
                raise ToolError("E-way bill number sirf owner daalti hai.")
            return S.ewb_set(t, ref, _s(a.get("ewb_no")), _s(a.get("valid_upto")), _s(a.get("generated")), conv)
        if action == "pod":
            if not _s(a.get("file_id")):
                raise ToolError("POD ki photo chat mein bhejiye (file_id).")
            return S.add_photo_file(t, ref, _s(a.get("file_id")), stage="pod", receiver=_s(a.get("receiver")), remarks=_s(a.get("remarks")),
                                    short=a.get("short"), damaged=bool(a.get("damaged")), conv=conv)
        if action == "cancel":
            if not _owner(ctx):
                raise ToolError("Cancel sirf owner.")
            return S.cancel(t, ref, _s(a.get("reason")), conv)
        if action == "register":
            return S.register_file(t, conv=conv)
    except (S.LogiError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..logistics import rules as R
    from ..logistics import service as S
    t = ctx.tenant_id
    try:
        if what == "board":
            return S.board(t)
        if what == "shipments":
            return {"shipments": S.shipments(t, _s(a.get("status")), _s(a.get("q")))}
        if what == "shipment":
            return S.get(t, _s(a.get("shipment")))
        if what == "ewb_ready":
            return S.ewb_ready(t, _s(a.get("shipment")))
        if what == "parties":
            return {"parties": S.parties(t, _s(a.get("kind")), _s(a.get("q")))}
        if what == "ontime":
            return {"ontime": S._ontime(t)}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "ewb_inter": R.EWB_INTER, "ewb_intra": R.EWB_INTRA, "km_per_day": R.KM_PER_DAY,
                    "odc_km_per_day": R.ODC_KM_PER_DAY, "extend_window_h": R.EXTEND_WINDOW_H, "max_doc_age_days": R.MAX_DOC_AGE_DAYS,
                    "max_extend_days": R.MAX_EXTEND_DAYS, "part_b_free_km": R.PART_B_FREE_KM, "claim_notice_days": R.CLAIM_NOTICE_DAYS,
                    "liability_x_freight": R.LIABILITY_X_FREIGHT, "gta_rates": R.GTA_RATES}
    except (S.LogiError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def logistics(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def logistics_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


LOGISTICS_HANDLERS = {"logistics": logistics, "logistics_dekho": logistics_dekho}
