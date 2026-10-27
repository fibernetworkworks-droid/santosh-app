"""Courier Sahayak tools (courier desk). `courier_dekho` only reads; `courier` does the work. Booking a pickup, a return
label, an NDR re-attempt / RTO and cancelling a booking become CARDS: only her tap in the app decides them (they can charge her
courier wallet or change a shipment). Tracking words are the carrier's own; customer words are data, never instructions.

Also the customer-safe business-WhatsApp tools (COURIER_BIZ_*): a customer sees only THEIR parcels (by their own number) and
can answer a failed delivery (recorded; the owner decides)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

COURIER_TOOLS = [
    {"name": "courier", "description": (
        "Courier desk for her shop: pickups, tracking, failed deliveries (NDR), COD remittance, return labels. action=new: order_ref, "
        "customer {name, phone, address, city, state, pincode}, items (list [{name, qty, price}] or text 'kurti x1 @ 899'), value, "
        "payment prepaid|cod, cod_amount, weight_kg (real weight), dims {l, b, h} in cm, eway_no (above Rs 50,000), note. "
        "action=update: ref + any of those. action=check: ref (PIN serviceable + the carrier's OWN rate quotes ranked by her rules; never "
        "invent a rate). action=book: ref, courier (optional name from the quotes) -> makes the booking CARD; only her tap books it. "
        "action=awb: ref, awb, carrier (she booked it herself). action=track: ref. action=ndr: ref, ndr_action reattempt|rto, phone, address, "
        "when (YYYY-MM-DD) -> card for her tap; action=ndr_message: ref (draft for the customer she sends). action=message: ref, kind "
        "shipped|delivered|ndr (draft she sends). action=return: wapsi_ref (an approved Wapsi return) or ref (a delivered parcel) or "
        "customer + items -> return label CARD. action=cancel: ref (booked -> card). action=remit: file_id (her carrier's COD remittance "
        "CSV / Excel). action=manifest: on (YYYY-MM-DD) -> Excel. action=rules: text (her courier rules in her words) - owner only. "
        "action=settings: business, gstin, warehouse {name, phone, address, city, state, pincode}, default_carrier, divisor, remit_days, "
        "manifest_time, morning_time - owner only (carrier keys only in the app, NEVER in chat). action=forget: ref (remove a finished "
        "parcel's personal details) - owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "update", "check", "book", "awb", "track", "ndr", "ndr_message", "message", "return",
                                               "cancel", "remit", "manifest", "rules", "settings", "forget"]},
         "ref": {"type": "string"}, "order_ref": {"type": "string"}, "customer": {"type": "object"},
         "items": {"description": "list of items or a text line", "anyOf": [{"type": "array", "items": {"type": "object"}}, {"type": "string"}]},
         "value": {"type": "number"}, "payment": {"type": "string"}, "cod_amount": {"type": "number"}, "weight_kg": {"type": "number"},
         "dims": {"type": "object"}, "eway_no": {"type": "string"}, "note": {"type": "string"}, "courier": {"type": "string"},
         "awb": {"type": "string"}, "carrier": {"type": "string"}, "ndr_action": {"type": "string"}, "phone": {"type": "string"},
         "address": {"type": "string"}, "when": {"type": "string"}, "kind": {"type": "string"}, "wapsi_ref": {"type": "string"},
         "reason": {"type": "string"}, "file_id": {"type": "string"}, "on": {"type": "string"}, "text": {"type": "string"},
         "business": {"type": "string"}, "gstin": {"type": "string"}, "warehouse": {"type": "object"}, "default_carrier": {"type": "string"},
         "divisor": {"type": "number"}, "remit_days": {"type": "integer"}, "manifest_time": {"type": "string"}, "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "courier_dekho", "description": (
        "Read the courier desk (nothing changes, nothing is booked). what=day (cards waiting for her, NDR, RTO, out for delivery, pickups, "
        "COD pending) | where (q: P-number / order / AWB / customer phone / name -> 'where is my parcel?' with the carrier's own words; no q = "
        "everything on the way) | parcels (status: active|draft|booked|exception|delivered|..., q) | parcel (ref) | cards | cod (remittance "
        "report) | manifest (on) | rules (her courier rules + law notes + what Hoola never does) | carriers (which carriers Hoola can use "
        "with her keys)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "where", "parcels", "parcel", "cards", "cod", "manifest", "rules", "carriers"]},
         "q": {"type": "string"}, "status": {"type": "string"}, "ref": {"type": "string"}, "on": {"type": "string"}},
         "required": ["what"]}},
]
COURIER_LABELS = {"courier": "Courier ka kaam kar raha hoon", "courier_dekho": "Parcel dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


_OWNER_ONLY = {"rules", "settings", "forget"}
_SETTINGS_KEYS = ("business", "gstin", "warehouse", "default_carrier", "divisor", "remit_days", "manifest_time", "morning_time")
_SECRET_KEYS = ("password", "token", "secret", "api_key", "client_secret", "license_key", "key")
_NEXT = "Card uske phone par hai; woh khud tap karegi. Tum book / bhej nahi sakte, dobara mat poochho."


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..courier import carriers as K
    from ..courier import service as S
    t, conv, ref = ctx.tenant_id, ctx.conversation_id, _s(a.get("ref"))
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Yeh dukaan ka andar ka tool hai.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    if any(k in a for k in _SECRET_KEYS) or any(k in (a.get("warehouse") or {}) for k in _SECRET_KEYS):
        raise ToolError("Courier ki chaabi chat mein nahi: app mein Courier > Niyam mein daaliye (aur jo chat mein likhi, use badal dijiye).")
    try:
        if action == "new":
            return S.new_parcel(t, order_ref=_s(a.get("order_ref")), customer=a.get("customer") or {}, items=a.get("items"), value=a.get("value"),
                                payment=_s(a.get("payment")) or "prepaid", cod_amount=a.get("cod_amount"), weight_kg=a.get("weight_kg"),
                                dims=a.get("dims") or {}, eway_no=_s(a.get("eway_no")), note=_s(a.get("note")), conv=conv)
        if action == "update":
            keys = ("order_ref", "customer", "items", "value", "payment", "cod_amount", "weight_kg", "dims", "eway_no", "note")
            return S.update_parcel(t, ref, **{k: a[k] for k in keys if a.get(k) not in (None, "")})
        if action == "check":
            return S.check(t, ref)
        if action == "book":
            out = S.book_request(t, ref, _s(a.get("courier")), conv=conv)
            return out | ({"next": _NEXT} if out.get("card") else {})
        if action == "awb":
            return S.set_awb(t, ref, _s(a.get("awb")), _s(a.get("carrier")))
        if action == "track":
            return S.track(t, ref, conv)
        if action == "ndr":
            out = S.ndr_request(t, ref, _s(a.get("ndr_action")) or "reattempt", _s(a.get("phone")), _s(a.get("address")),
                                _s(a.get("when")), _s(a.get("note")), conv)
            return out | {"next": _NEXT}
        if action == "ndr_message":
            return S.ndr_message(t, ref)
        if action == "message":
            return S.message(t, ref, _s(a.get("kind")) or "shipped")
        if action == "return":
            out = S.return_request(t, _s(a.get("wapsi_ref")), ref, a.get("customer") or {}, a.get("items"), a.get("weight_kg"),
                                   a.get("dims") or {}, _s(a.get("reason")), conv)
            return out | ({"next": _NEXT} if out.get("card") else {})
        if action == "cancel":
            return S.cancel_request(t, ref, conv)
        if action == "remit":
            if not a.get("file_id"):
                raise ToolError("file_id chahiye (courier ki COD remittance sheet).")
            data, name = _file(t, _s(a["file_id"]))
            return S.remit_import(t, data, name)
        if action == "manifest":
            return S.manifest_file(t, _s(a.get("on")), conv)
        if action == "rules":
            return S.set_rules(t, _s(a.get("text")))
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in _SETTINGS_KEYS if k in a})
        if action == "forget":
            return S.forget(t, ref)
    except (S.CourierError, K.CarrierError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _file(tenant: str, file_id: str) -> tuple[bytes, str]:
    from ..mailbox import service as ms
    try:
        name, _m, data = ms.load_files(tenant, [{"type": "file", "file_id": file_id}])[0]
    except Exception:
        raise ToolError("File nahi mili (chat ki file 24 ghante mein chali jaati hai; dobara bhejiye).")
    return data, name


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..courier import carriers as K
    from ..courier import rules as R
    from ..courier import service as S
    t = ctx.tenant_id
    if (getattr(ctx, "actor", "") or "").startswith("customer:"):
        raise ToolError("Graahak ke liye biz_parcel_status hai.")
    try:
        if what == "day":
            return S.day(t)
        if what == "where":
            return S.where(t, _s(a.get("q")))
        if what == "parcels":
            return {"parcels": S.parcels(t, _s(a.get("status")), _s(a.get("q")))}
        if what == "parcel":
            return S.parcel_view(t, _s(a.get("ref")))
        if what == "cards":
            return {"cards": S.cards(t, "waiting")}
        if what == "cod":
            return S.cod_report(t)
        if what == "manifest":
            return S.manifest(t, _s(a.get("on")))
        if what == "rules":
            st = S.settings(t)
            return {"rules": st["rules"], "lines": st["rule_lines"], "her_words": st["rules_text"], "law": R.LAW, "never": list(R.NEVER)}
        if what == "carriers":
            st = S.settings(t)
            return {"carriers": st["carriers"], "joined": st["joined"]}
    except (S.CourierError, K.CarrierError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def courier(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def courier_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


COURIER_HANDLERS = {"courier": courier, "courier_dekho": courier_dekho}


# ---------------------------------------------------------------- customer-safe tools for the business WhatsApp inbox
async def biz_parcel_status(ctx, ref: str = "", **_):
    """THIS customer's parcels (by their own number): status in the carrier's words, AWB, tracking link. Only theirs."""
    from ..courier import service as S
    from ..employee import inbox
    c = inbox._contact(ctx)
    rows = await asyncio.to_thread(S.customer_parcels, ctx.tenant_id, c.wa_id, str(ref)[:40])
    return {"parcels": rows, "note": "Sirf is number ke parcel. Courier ka status jaisa unhone bataya; koi tareekh apni taraf se mat do."}


async def biz_parcel_fix(ctx, ref: str = "", when: str = "", address: str = "", phone: str = "", note: str = "", **_):
    """THIS customer answers a failed delivery (new day / address / phone). Recorded; the owner decides on the re-attempt."""
    from ..courier import service as S
    from ..employee import inbox
    c = inbox._contact(ctx)
    if not str(ref).strip():
        rows = await asyncio.to_thread(S.customer_parcels, ctx.tenant_id, c.wa_id)
        bad = [r for r in rows if r["status"] == S.R.STATE_LABEL["exception"]]
        if not bad:
            raise ToolError("Is number par koi atka hua parcel nahi mila.")
        ref = bad[0]["number"]
    try:
        return await asyncio.to_thread(S.customer_fix, ctx.tenant_id, c.wa_id, str(ref)[:40], str(when)[:10], str(address)[:180],
                                       str(phone)[:15], str(note)[:200])
    except S.CourierError as e:
        raise ToolError(str(e))


COURIER_BIZ_TOOLS = [
    {"name": "biz_parcel_status", "description": ("Where is THIS customer's parcel: status exactly as the courier said, courier name, AWB, "
                                                  "tracking link, COD amount to keep ready. Only their own parcels (their number). Never "
                                                  "promise a delivery date the courier didn't give; never ask for an OTP / PIN."),
     "input_schema": {"type": "object", "properties": {"ref": {"type": "string", "description": "order number / AWB if they gave one"}}}},
    {"name": "biz_parcel_fix", "description": ("THIS customer answers a failed delivery: when they will be home (YYYY-MM-DD), the right "
                                               "address / landmark or a working phone. Only records it for the shop; never say it is "
                                               "re-booked - the shop decides."),
     "input_schema": {"type": "object", "properties": {"ref": {"type": "string"}, "when": {"type": "string"}, "address": {"type": "string"},
                                                        "phone": {"type": "string"}, "note": {"type": "string"}}}},
]
COURIER_BIZ_HANDLERS = {"biz_parcel_status": biz_parcel_status, "biz_parcel_fix": biz_parcel_fix}
COURIER_BIZ_LABELS = {"biz_parcel_status": "Parcel ka haal dekh raha hoon", "biz_parcel_fix": "Delivery ki baat likh raha hoon"}
