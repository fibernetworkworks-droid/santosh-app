"""v0.84 Chai Sahayak tools. `chai_dekho` only reads (today's galla, best hours, tomorrow's plan, recent payments,
settings); `chai` changes things (cash she tells, forwarded alerts / statements, stock, plan, menu / suppliers, her Haan on
a stock order only when she says so herself, the day's feedback)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

CHAI_TOOLS = [
    {"name": "chai", "description": (
        "Chai stall coworker (her tea stall / tapri / nashta stall). "
        "action=cash: amount (rupees), date (aaj / kal / 2026-10-20), hour (0-23, if she said when): cash sales she tells. "
        "action=alerts: alerts [{title, text}] = payment-received messages she forwarded or pasted (only credits are "
        "counted; never OTP). action=statement: file_id of a CSV / Excel statement from her payment app or bank. "
        "action=void: entry_id (a wrong entry). "
        "action=plan: tomorrow's cups, milk / sugar / patti and the stock order cards (for_date optional). Order cards "
        "wait for HER tap; never say milk was ordered. If it returns needs=typical_cups, ask her and save it with "
        "action=setup typical_cups. "
        "action=stock: milk_l, sugar_kg, tea_kg she has now. "
        "action=feedback: for_date, milk_left_l, ran_out_at (HH:MM), sugar_left_kg, tea_left_kg, cash, bought_milk_l: "
        "how the day really went (teaches milk per cup and the cash share). "
        "action=decide: order_id, approve: ONLY when she herself clearly says haan / mana for that stock order. "
        "action=setup: stall_name, menu [{name, price, milk_ml, sugar_g, tea_g, share %}], other_pct (sales that are "
        "not chai), cash_pct, safety_pct, milk_packet_ml, typical_cups, suppliers [{name, phone, items [milk|sugar|tea], "
        "site (blinkit / jiomart / bigbasket... for sugar / patti)}], rules [her sentences], plan_time (HH:MM), "
        "apps [payment app package names to read], open_hour, close_hour. Owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["cash", "alerts", "statement", "void", "plan", "stock", "feedback", "decide", "setup"]},
         "amount": {"type": "number"}, "date": {"type": "string"}, "hour": {"type": "integer"}, "note": {"type": "string"},
         "alerts": {"type": "array", "items": {"type": "object", "properties": {"title": {"type": "string"}, "text": {"type": "string"}}}},
         "file_id": {"type": "string"}, "entry_id": {"type": "string"}, "for_date": {"type": "string"},
         "milk_l": {"type": "number"}, "sugar_kg": {"type": "number"}, "tea_kg": {"type": "number"},
         "milk_left_l": {"type": "number"}, "ran_out_at": {"type": "string"}, "sugar_left_kg": {"type": "number"},
         "tea_left_kg": {"type": "number"}, "cash": {"type": "number"}, "bought_milk_l": {"type": "number"},
         "order_id": {"type": "string"}, "approve": {"type": "boolean"},
         "stall_name": {"type": "string"}, "menu": {"type": "array", "items": {"type": "object"}}, "other_pct": {"type": "number"},
         "cash_pct": {"type": "number"}, "safety_pct": {"type": "number"}, "milk_packet_ml": {"type": "number"},
         "typical_cups": {"type": "integer"}, "suppliers": {"type": "array", "items": {"type": "object"}},
         "rules": {"type": "array", "items": {"type": "string"}}, "plan_time": {"type": "string"},
         "apps": {"type": "array", "items": {"type": "string"}}, "open_hour": {"type": "integer"}, "close_hour": {"type": "integer"}},
         "required": ["action"]}},
    {"name": "chai_dekho", "description": (
        "Read the chai stall's numbers (nothing changes). what=today (the day's sales: UPI + cash, by hour, best hour, vs "
        "the same weekday before; date optional) | hours (best-selling hours over the last weeks, per weekday) | plan "
        "(tomorrow's plan if made) | recent (latest payments) | settings (menu, suppliers, rules, learned milk per cup, "
        "cash share, which payment apps are read)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["today", "hours", "plan", "recent", "settings"]},
         "date": {"type": "string"}, "days": {"type": "integer"}},
         "required": ["what"]}},
]
CHAI_LABELS = {"chai": "Chai stall ka kaam kar raha hoon", "chai_dekho": "Galla dekh raha hoon"}


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any], weather: dict | None) -> dict[str, Any]:
    from ..chai import service as C
    from ..galla import service as G
    t = ctx.tenant_id
    try:
        if action == "cash":
            return G.add_cash(t, a.get("amount"), str(a.get("date") or ""), a.get("hour"), str(a.get("note") or ""))
        if action == "alerts":
            r = G.ingest_alerts(t, [x for x in (a.get("alerts") or []) if isinstance(x, dict)])
            r["say"] = f"{r['added']} payment jode" + (f", {r['skipped']} chhode (credit nahi / dobara)" if r["skipped"] else "") + "."
            return r
        if action == "statement":
            from ..mailbox import service as ms
            try:
                name, _mime, data = ms.load_files(t, [{"type": "file", "file_id": str(a.get("file_id") or "")}])[0]
            except Exception as e:
                raise ToolError(f"Statement file nahi mili: {e}")
            return G.import_statement(t, name, data)
        if action == "void":
            return G.void(t, str(a.get("entry_id") or ""))
        if action == "plan":
            return C.plan_tomorrow(t, str(a.get("for_date") or ""), weather, ctx.conversation_id)
        if action == "stock":
            return C.set_stock(t, a.get("milk_l"), a.get("sugar_kg"), a.get("tea_kg"))
        if action == "feedback":
            return C.feedback(t, str(a.get("for_date") or ""), a.get("milk_left_l"), str(a.get("ran_out_at") or ""),
                              a.get("sugar_left_kg"), a.get("tea_left_kg"), a.get("cash"), a.get("bought_milk_l"))
        if action == "decide":
            if not _owner(ctx):
                raise ToolError("Stock order par haan sirf owner de sakti hain.")
            return C.decide_order(t, str(a.get("order_id") or ""), bool(a.get("approve")), ctx.conversation_id)
        if action == "setup":
            if not _owner(ctx):
                raise ToolError("Menu, supplier aur niyam sirf owner badal sakti hain.")
            keys = ("stall_name", "menu", "other_pct", "cash_pct", "safety_pct", "milk_packet_ml", "typical_cups",
                    "suppliers", "rules", "plan_time")
            out = C.save_settings(t, **{k: a[k] for k in keys if k in a})
            if any(k in a for k in ("apps", "open_hour", "close_hour")):
                out["galla"] = G.save_settings(t, a.get("apps"), a.get("open_hour"), a.get("close_hour"))
            out["say"] = "Chai stall ki setting save."
            return out
    except (C.ChaiError, G.GallaError) as e:
        raise ToolError(str(e))
    raise ToolError("action = cash | alerts | statement | void | plan | stock | feedback | decide | setup")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..chai import service as C
    from ..galla import service as G
    t = ctx.tenant_id
    try:
        if what == "today":
            return G.day_summary(t, str(a.get("date") or ""))
        if what == "hours":
            return G.best_hours(t, int(a.get("days") or 28))
        if what == "plan":
            return C.get_plan(t, str(a.get("date") or "")) or {"say": "Abhi koi plan nahi bana (chai action=plan)."}
        if what == "recent":
            return {"payments": G.recent(t, 30)}
        if what == "settings":
            return C.settings(t) | {"galla": G.settings(t)}
    except (C.ChaiError, G.GallaError) as e:
        raise ToolError(str(e))
    raise ToolError("what = today | hours | plan | recent | settings")


async def chai(ctx: Ctx, action, **a: Any):
    weather = None
    if str(action) == "plan":
        try:
            from ..life import weather_for
            weather = await weather_for(ctx.tenant_id)
        except Exception:
            weather = None
    return await asyncio.to_thread(_act, ctx, str(action), a, weather)


async def chai_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


CHAI_HANDLERS = {"chai": chai, "chai_dekho": chai_dekho}
