"""v0.93 GST Sahayak tools: a GST practitioner's work for every client. `gst_dekho` only reads; `gst` changes things.
Filing waits for HER Haan and stops before the final EVC / DSC submit; the tax challan is always the taxpayer's own
payment. Hoola never stores a portal password and never pays."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

GST_TOOLS = [
    {"name": "gst", "description": (
        "GST practitioner coworker: does all GST work for her clients (or her own business) end to end. "
        "action=client: name, gstin, scheme monthly|qrmp|composition, aato (last FY turnover, rupees), portal_user (username "
        "only, NEVER a password), login_as taxpayer|practitioner, contact_name, contact_phone, fee, notes (e.g. 'restaurant'), "
        "client (to update). "
        "action=bill: client, direction out (sale) | in (purchase), number, date, party_gstin, party_name, pos (state code or "
        "name), kind inv|cn|dn|exp|sez, rcm, irn, category (purchases: what for, e.g. 'car repair' -> 17(5) check), paid_on, "
        "value, items [{desc, hsn, qty, uqc, rate, txval, igst, cgst, sgst, cess}] (or txval + rate + hsn + desc for one line). "
        "Read a forwarded bill photo / PDF with file_read first, then save it here. Every bill is checked (GSTIN, POS vs "
        "IGST / CGST+SGST, rate slab, tax maths, HSN digits, IRN, duplicate). replace=true to overwrite. "
        "action=import: client, direction, file_id (Tally / Vyapar / Excel / CSV sales or purchase register), period. "
        "action=import_2b: client, period, file_id (GSTR-2B JSON or Excel from the portal). action=fetch_2b: client, period "
        "(Computer Operator downloads it). action=ims: client, period, decisions {2b_row_id: accept|reject|pending}: ONLY "
        "what she decided. action=ims_apply: client, period (puts her decisions on the portal). "
        "action=gstr1: client, period (YYYY-MM; QRMP quarter = its last month; IFF for months 1-2). action=gstr3b: client, "
        "period, other_reversal {igst, cgst, sgst}. action=cmp08: client, period, turnover. "
        "action=decide: return_id, approve, note: ONLY when she herself says haan / mana. action=file: return_id (after her "
        "haan; Computer Operator fills the portal and stops before submit; EVC OTP + challan are the taxpayer's). "
        "action=filed: return_id, arn, filed_on. action=json: return_id (GSTR-1 JSON + review Excel as files). "
        "action=supplier_drafts: client, period (messages to suppliers whose bills are missing in 2B). "
        "action=ask_bills: client, period (draft to the client). action=tax_message: return_id (draft: tax to pay). "
        "action=paid: client, number, paid_on, supplier (Rule 37). action=delete_bill: bill_id. "
        "action=notice: client, form (ASMT-10, DRC-01, DRC-01A, DRC-01B, DRC-01C, GSTR-3A, REG-03, REG-17, REG-31, CMP-05, "
        "ADT-01, RFD-08), issued_on, ref, text, amount, due_on. action=notice_draft: notice_id. action=notice_status: "
        "notice_id, status open|replied|closed. action=settings: practitioner, enrolment, morning_time, remind_days."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["client", "bill", "import", "import_2b", "fetch_2b", "ims", "ims_apply", "gstr1",
                                               "gstr3b", "cmp08", "decide", "file", "filed", "json", "supplier_drafts", "ask_bills",
                                               "tax_message", "paid", "delete_bill", "notice", "notice_draft", "notice_status",
                                               "settings"]},
         "client": {"type": "string"}, "name": {"type": "string"}, "gstin": {"type": "string"}, "scheme": {"type": "string"},
         "aato": {"type": "number"}, "portal_user": {"type": "string"}, "login_as": {"type": "string"},
         "contact_name": {"type": "string"}, "contact_phone": {"type": "string"}, "fee": {"type": "number"}, "notes": {"type": "string"},
         "direction": {"type": "string"}, "number": {"type": "string"}, "date": {"type": "string"}, "party_gstin": {"type": "string"},
         "party_name": {"type": "string"}, "pos": {"type": "string"}, "kind": {"type": "string"}, "rcm": {"type": "boolean"},
         "irn": {"type": "string"}, "category": {"type": "string"}, "paid_on": {"type": "string"}, "value": {"type": "number"},
         "items": {"type": "array", "items": {"type": "object"}}, "txval": {"type": "number"}, "rate": {"type": "number"},
         "hsn": {"type": "string"}, "desc": {"type": "string"}, "qty": {"type": "number"}, "uqc": {"type": "string"},
         "igst": {"type": "number"}, "cgst": {"type": "number"}, "sgst": {"type": "number"}, "cess": {"type": "number"},
         "replace": {"type": "boolean"}, "file_id": {"type": "string"}, "period": {"type": "string"}, "decisions": {"type": "object"},
         "other_reversal": {"type": "object"}, "turnover": {"type": "number"}, "return_id": {"type": "string"},
         "approve": {"type": "boolean"}, "note": {"type": "string"}, "arn": {"type": "string"}, "filed_on": {"type": "string"},
         "supplier": {"type": "string"}, "bill_id": {"type": "string"}, "form": {"type": "string"}, "issued_on": {"type": "string"},
         "ref": {"type": "string"}, "text": {"type": "string"}, "amount": {"type": "number"}, "due_on": {"type": "string"},
         "notice_id": {"type": "string"}, "status": {"type": "string"}, "practitioner": {"type": "string"},
         "enrolment": {"type": "string"}, "morning_time": {"type": "string"}, "remind_days": {"type": "integer"},
         "einvoice": {"type": "boolean"}},
         "required": ["action"]}},
    {"name": "gst_dekho", "description": (
        "Read GST work (nothing changes). what=today (due in the next days, late with late fee, notices, ITC 30-Nov "
        "deadline, GSTR-9) | clients | client (client) | bills (client, period, direction) | returns (client, period, status) | "
        "return (return_id, or client + period + kind gstr1|gstr3b|cmp08) | reconcile (client, period: books vs GSTR-2B with "
        "IMS suggestions) | notices (status) | gstin (gstin: valid? state, entity) | due (kind, period, scheme, state) | "
        "late_fee (kind, days, nil, aato) | setoff (liability {igst,cgst,sgst,cess}, credit {...}) | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["today", "clients", "client", "bills", "returns", "return", "reconcile", "notices",
                                             "gstin", "due", "late_fee", "setoff", "settings"]},
         "client": {"type": "string"}, "period": {"type": "string"}, "direction": {"type": "string"}, "status": {"type": "string"},
         "return_id": {"type": "string"}, "kind": {"type": "string"}, "gstin": {"type": "string"}, "scheme": {"type": "string"},
         "state": {"type": "string"}, "days": {"type": "integer"}, "nil": {"type": "boolean"}, "aato": {"type": "number"},
         "liability": {"type": "object"}, "credit": {"type": "object"}},
         "required": ["what"]}},
]
GST_LABELS = {"gst": "GST ka kaam kar raha hoon", "gst_dekho": "GST register dekh raha hoon"}

_LINE = ("txval", "rate", "hsn", "desc", "qty", "uqc", "igst", "cgst", "sgst", "cess")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..gstp import service as G
    t, conv = ctx.tenant_id, ctx.conversation_id
    by = "owner" if _owner(ctx) else (getattr(ctx, "actor", "") or "staff")
    try:
        if action == "client":
            return G.add_client(t, _s(a.get("name")), _s(a.get("gstin")), _s(a.get("scheme")), a.get("aato"), _s(a.get("portal_user")),
                                _s(a.get("login_as")), _s(a.get("contact_name")), _s(a.get("contact_phone")), a.get("fee"),
                                _s(a.get("notes")), a.get("einvoice"), _s(a.get("client")))
        if action == "bill":
            return G.add_doc(t, _s(a.get("client")), _s(a.get("direction")) or "out", _s(a.get("number")), a.get("date"),
                             _s(a.get("party_gstin")), _s(a.get("party_name")), _s(a.get("pos")), a.get("items"),
                             _s(a.get("kind")) or "inv", bool(a.get("rcm")), _s(a.get("irn")), _s(a.get("category")),
                             _s(a.get("paid_on")), a.get("value"), "chat", bool(a.get("replace")), **{k: a.get(k) for k in _LINE})
        if action == "import":
            return G.import_register(t, _s(a.get("client")), _s(a.get("direction")) or "out", _s(a.get("file_id")), period=_s(a.get("period")))
        if action == "import_2b":
            return G.import_2b(t, _s(a.get("client")), _s(a.get("period")), _s(a.get("file_id")))
        if action == "fetch_2b":
            return G.fetch_2b(t, _s(a.get("client")), _s(a.get("period")), conv, by)
        if action == "ims":
            if not _owner(ctx):
                raise ToolError("IMS ka faisla sirf owner.")
            return G.ims_decide(t, _s(a.get("client")), _s(a.get("period")), a.get("decisions") or {}, by)
        if action == "ims_apply":
            if not _owner(ctx):
                raise ToolError("Portal par IMS sirf owner ki haan se.")
            return G.ims_apply(t, _s(a.get("client")), _s(a.get("period")), conv, by)
        if action == "gstr1":
            return G.prepare_gstr1(t, _s(a.get("client")), _s(a.get("period")), conv)
        if action == "gstr3b":
            return G.prepare_gstr3b(t, _s(a.get("client")), _s(a.get("period")), a.get("other_reversal"), conv)
        if action == "cmp08":
            return G.prepare_cmp08(t, _s(a.get("client")), _s(a.get("period")), a.get("turnover"), conv)
        if action == "decide":
            if not _owner(ctx):
                raise ToolError("Return par haan sirf owner de sakti hain.")
            return G.decide(t, _s(a.get("return_id")), bool(a.get("approve")), _s(a.get("note")), conv)
        if action == "file":
            if not _owner(ctx):
                raise ToolError("Filing sirf owner ki haan se.")
            return G.file_return(t, _s(a.get("return_id")), conv, by)
        if action == "filed":
            return G.mark_filed(t, _s(a.get("return_id")), _s(a.get("arn")), _s(a.get("filed_on")), by, conv)
        if action == "json":
            return G.return_file(t, _s(a.get("return_id")), conv)
        if action == "supplier_drafts":
            return G.supplier_drafts(t, _s(a.get("client")), _s(a.get("period")))
        if action == "ask_bills":
            return G.client_request_draft(t, _s(a.get("client")), _s(a.get("period")))
        if action == "tax_message":
            return G.tax_message_draft(t, _s(a.get("return_id")))
        if action == "paid":
            return G.mark_paid(t, _s(a.get("client")), _s(a.get("number")), _s(a.get("paid_on")), _s(a.get("supplier")))
        if action == "delete_bill":
            return G.delete_doc(t, _s(a.get("bill_id")))
        if action == "notice":
            return G.add_notice(t, _s(a.get("client")), _s(a.get("form")), _s(a.get("issued_on")), _s(a.get("ref")), _s(a.get("text")),
                                a.get("amount"), _s(a.get("due_on")))
        if action == "notice_draft":
            return G.notice_draft(t, _s(a.get("notice_id")))
        if action == "notice_status":
            return G.notice_status(t, _s(a.get("notice_id")), _s(a.get("status")))
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Settings sirf owner.")
            keys = ("practitioner", "enrolment", "morning_time", "remind_days")
            return {"settings": G.save_settings(t, **{k: a[k] for k in keys if k in a}), "say": "Save."}
    except (G.GstError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..gstp import rules as R
    from ..gstp import service as G
    from ..india.money import gstin_info
    t = ctx.tenant_id
    try:
        if what == "today":
            return G.calendar(t)
        if what == "clients":
            return {"clients": G.clients(t)}
        if what == "client":
            return G.get_client(t, _s(a.get("client")))
        if what == "bills":
            return {"bills": G.docs(t, _s(a.get("client")), _s(a.get("period")), _s(a.get("direction")), 200)}
        if what == "returns":
            return {"returns": G.returns(t, _s(a.get("client")), _s(a.get("period")), _s(a.get("status")))}
        if what == "return":
            if a.get("return_id"):
                return G.get_return(t, _s(a.get("return_id")))
            return G.find_return(t, _s(a.get("client")), _s(a.get("period")), _s(a.get("kind")) or "gstr3b")
        if what == "reconcile":
            return G.reconcile(t, _s(a.get("client")), _s(a.get("period")))
        if what == "notices":
            return {"notices": G.notices(t, _s(a.get("status")) or "open")}
        if what == "gstin":
            return gstin_info(_s(a.get("gstin")))
        if what == "due":
            d = R.due_date(_s(a.get("kind")) or "gstr3b", _s(a.get("period")), _s(a.get("scheme")) or "monthly", _s(a.get("state")) or "27")
            return {"due": d.isoformat()}
        if what == "late_fee":
            return {"late_fee": R.late_fee(_s(a.get("kind")) or "gstr3b", int(a.get("days") or 0), bool(a.get("nil")), float(a.get("aato") or 0))}
        if what == "setoff":
            return R.set_off(a.get("liability") or {}, a.get("credit") or {})
        if what == "settings":
            return G.settings(t)
    except (G.GstError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("what galat")


async def gst(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def gst_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


GST_HANDLERS = {"gst": gst, "gst_dekho": gst_dekho}
