"""v0.88 Mobile Dukaan Sahayak tools (mobile recharge + repair shop). `mobile_shop_dekho` only reads; `mobile_shop`
changes things. The bill to the customer is a card that waits for HER Haan; 'ready' messages and recharge reminders are
drafts she sends; Hoola never recharges, never takes money, never keeps a phone's passcode, never changes an IMEI."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

MSHOP_TOOLS = [
    {"name": "mobile_shop", "description": (
        "Mobile recharge + repair shop coworker. "
        "action=new_job: name, phone, brand, model, imei (15 digits, *#06#), problem (her words), faults (display, battery, "
        "charging_port, speaker, mic, camera, back_panel, buttons, network, water, software, motherboard, unlock, other), "
        "accessories [sim, memory_card, cover, charger, cable, earphone, box, back_cover], condition (scratches / cracks), "
        "promised_on (kal / 2 din / 28/10), estimate, advance, proof (ownership proof for lock / FRP jobs), photos "
        "(file_ids of the phone's photos she sent), technician. Rules and earlier work are checked first: saved=false with "
        "problems -> tell her; force=true only after she agrees. NEVER ask for or note the customer's phone password / "
        "pattern. IMEI change / write / repair is illegal: refuse. "
        "action=photo: job, file_ids, kind in|out|part. action=status: job (M-0012 / 12 / IMEI), status received | "
        "diagnosing | waiting_customer | waiting_part | repairing | ready | delivered | returned | cancelled, note. "
        "ready -> Hoola prepares the bill as a card for HER Haan; the customer is told only after that, by her. "
        "action=part: job, name, price (customer pays), cost (she paid), warranty_days, labour. "
        "action=bill: job (prepare again). action=decide_bill: job, approve, total: ONLY when she herself says haan / "
        "mana / the amount. action=customer_ok: job, estimate (the customer agreed). action=pay: job, amount, how. "
        "action=deliver: job, paid_now. action=update: job + promised_on / notes / technician / imei / proof / estimate. "
        "action=slip: PDF job card / bill. action=ready_message: the draft again (after her Haan). "
        "action=recharge: number, amount, operator (jio / airtel / vi / bsnl), validity_days, name, plan, via (Jio POS "
        "Plus / Airtel Mitra / Vi...): a recharge SHE did (Hoola never recharges). action=reminded: recharge_id. "
        "action=void_recharge: recharge_id. "
        "action=rules: shop_name, gstin, gst_on, prices {fault: rupees}, warranty {fault: days}, fix_days {fault: days}, "
        "jobs_per_day, unclaimed_days, commission {operator: %}, remind_days, terms, ready_template, rules [her sentences], "
        "morning_time. Owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new_job", "photo", "status", "part", "bill", "decide_bill", "customer_ok", "pay",
                                               "deliver", "update", "slip", "ready_message", "recharge", "reminded",
                                               "void_recharge", "rules"]},
         "job": {"type": "string"}, "name": {"type": "string"}, "phone": {"type": "string"}, "brand": {"type": "string"},
         "model": {"type": "string"}, "imei": {"type": "string"}, "problem": {"type": "string"},
         "faults": {"type": "array", "items": {"type": "string"}}, "accessories": {"type": "array", "items": {"type": "string"}},
         "condition": {"type": "string"}, "promised_on": {"type": "string"}, "estimate": {"type": "number"},
         "advance": {"type": "number"}, "proof": {"type": "string"}, "photos": {"type": "array", "items": {"type": "string"}},
         "file_ids": {"type": "array", "items": {"type": "string"}}, "kind": {"type": "string"}, "technician": {"type": "string"},
         "force": {"type": "boolean"}, "status": {"type": "string"}, "note": {"type": "string"}, "notes": {"type": "string"},
         "price": {"type": "number"}, "cost": {"type": "number"}, "warranty_days": {"type": "integer"}, "labour": {"type": "number"},
         "approve": {"type": "boolean"}, "total": {"type": "number"}, "amount": {"type": "number"}, "how": {"type": "string"},
         "paid_now": {"type": "number"}, "number": {"type": "string"}, "operator": {"type": "string"},
         "validity_days": {"type": "integer"}, "plan": {"type": "string"}, "via": {"type": "string"},
         "recharge_id": {"type": "string"}, "shop_name": {"type": "string"}, "gstin": {"type": "string"},
         "gst_on": {"type": "boolean"}, "prices": {"type": "object"}, "warranty": {"type": "object"}, "fix_days": {"type": "object"},
         "jobs_per_day": {"type": "integer"}, "unclaimed_days": {"type": "integer"}, "commission": {"type": "object"},
         "remind_days": {"type": "integer"}, "terms": {"type": "string"}, "ready_template": {"type": "string"},
         "rules": {"type": "array", "items": {"type": "string"}}, "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "mobile_shop_dekho", "description": (
        "Read the mobile shop (nothing changes). what=today (due today, late, waiting for parts, bills waiting for her, "
        "ready but not collected, recharges ending soon, yesterday's recharges + commission) | jobs (status open|ready|"
        "delivered..., q = name / phone / model / IMEI) | job (job) | warranty (q = IMEI / phone / job number) | check "
        "(problem, faults, brand, model, imei, phone, promised_on: rules + earlier work BEFORE promising) | recharges (date) "
        "| recharge_due (within days) | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["today", "jobs", "job", "warranty", "check", "recharges", "recharge_due", "rules"]},
         "job": {"type": "string"}, "status": {"type": "string"}, "q": {"type": "string"}, "date": {"type": "string"},
         "within": {"type": "integer"}, "problem": {"type": "string"}, "faults": {"type": "array", "items": {"type": "string"}},
         "brand": {"type": "string"}, "model": {"type": "string"}, "imei": {"type": "string"}, "phone": {"type": "string"},
         "promised_on": {"type": "string"}, "proof": {"type": "string"}},
         "required": ["what"]}},
]
MSHOP_LABELS = {"mobile_shop": "Mobile dukaan ka kaam kar raha hoon", "mobile_shop_dekho": "Mobile dukaan ka register dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..mshop import service as M
    t, conv = ctx.tenant_id, ctx.conversation_id
    by = "hoola" if _owner(ctx) else (getattr(ctx, "actor", "") or "staff")
    try:
        if action == "new_job":
            return M.new_job(t, _s(a.get("name")), _s(a.get("phone")), _s(a.get("brand")), _s(a.get("model")), _s(a.get("imei")),
                             _s(a.get("problem")), a.get("faults"), a.get("accessories"), _s(a.get("condition")),
                             _s(a.get("promised_on")), a.get("estimate"), a.get("advance"), _s(a.get("proof")),
                             a.get("photos") or a.get("file_ids"), _s(a.get("technician")), bool(a.get("force")), by, conv)
        if action == "photo":
            got = [M.attach_chat_photo(t, _s(a.get("job")), _s(f), _s(a.get("kind")) or "in") for f in (a.get("file_ids") or a.get("photos") or [])]
            if not got:
                raise ToolError("file_ids chahiye (jo photo usne bheji).")
            return {"photos": got, "say": f"{len(got)} photo job mein lag gayi."}
        if action == "status":
            return M.set_status(t, _s(a.get("job")), _s(a.get("status")), _s(a.get("note")), by, conv)
        if action == "part":
            return M.add_part(t, _s(a.get("job")), _s(a.get("name")), a.get("price"), a.get("cost"), a.get("warranty_days"),
                              a.get("labour"), by)
        if action == "bill":
            return M.prepare_bill(t, _s(a.get("job")), conv)
        if action == "decide_bill":
            if not _owner(ctx):
                raise ToolError("Bill par haan sirf owner de sakti hain.")
            return M.decide_bill(t, _s(a.get("job")), bool(a.get("approve")), a.get("total"), conv)
        if action == "customer_ok":
            return M.customer_agreed(t, _s(a.get("job")), a.get("estimate"), by)
        if action == "pay":
            return M.pay(t, _s(a.get("job")), a.get("amount"), _s(a.get("how")), by)
        if action == "deliver":
            return M.deliver(t, _s(a.get("job")), a.get("paid_now"), _s(a.get("note")), by, conv)
        if action == "update":
            return M.update_job(t, _s(a.get("job")), _s(a.get("promised_on")), _s(a.get("notes") or a.get("note")),
                                _s(a.get("technician")), _s(a.get("imei")), _s(a.get("proof")), a.get("estimate"),
                                bool(a.get("force")), by)
        if action == "slip":
            return M.slip_file(t, _s(a.get("job")), conv)
        if action == "ready_message":
            return {"card": M.ready_card(t, _s(a.get("job")), conv), "say": "Draft card par hai: aap bhejengi."}
        if action == "recharge":
            return M.add_recharge(t, _s(a.get("number") or a.get("phone")), a.get("amount"), _s(a.get("operator")),
                                  a.get("validity_days"), _s(a.get("name")), _s(a.get("plan")), _s(a.get("via")), _s(a.get("date")))
        if action == "reminded":
            return M.mark_reminded(t, _s(a.get("recharge_id")))
        if action == "void_recharge":
            return M.void_recharge(t, _s(a.get("recharge_id")))
        if action == "rules":
            if not _owner(ctx):
                raise ToolError("Daam, warranty aur niyam sirf owner badal sakti hain.")
            keys = ("shop_name", "gstin", "gst_on", "prices", "warranty", "fix_days", "jobs_per_day", "unclaimed_days",
                    "commission", "remind_days", "terms", "ready_template", "rules", "morning_time")
            return {"rules": M.save_settings(t, **{k: a[k] for k in keys if k in a}), "say": "Niyam save."}
    except M.MShopError as e:
        raise ToolError(str(e))
    raise ToolError("action = new_job | photo | status | part | bill | decide_bill | customer_ok | pay | deliver | update | "
                    "slip | ready_message | recharge | reminded | void_recharge | rules")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..mshop import service as M
    t = ctx.tenant_id
    try:
        if what == "today":
            return M.day(t)
        if what == "jobs":
            return {"jobs": M.jobs(t, _s(a.get("status")) or "open", _s(a.get("q")), 40)}
        if what == "job":
            return M.get_job(t, _s(a.get("job")))
        if what == "warranty":
            return M.warranty(t, _s(a.get("q") or a.get("imei") or a.get("phone") or a.get("job")))
        if what == "check":
            return M.check_job(t, _s(a.get("problem")), a.get("faults"), _s(a.get("brand")), _s(a.get("model")),
                               _s(a.get("imei")), _s(a.get("phone")), _s(a.get("promised_on")), _s(a.get("proof")))
        if what == "recharges":
            return M.recharges_day(t, _s(a.get("date")))
        if what == "recharge_due":
            return {"due": M.due_recharges(t, a.get("within"))}
        if what == "rules":
            return M.settings(t)
    except M.MShopError as e:
        raise ToolError(str(e))
    raise ToolError("what = today | jobs | job | warranty | check | recharges | recharge_due | rules")


async def mobile_shop(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def mobile_shop_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


MSHOP_HANDLERS = {"mobile_shop": mobile_shop, "mobile_shop_dekho": mobile_shop_dekho}
