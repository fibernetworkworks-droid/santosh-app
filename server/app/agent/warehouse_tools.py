"""Godown Sahayak tools (warehouse manager). `warehouse_dekho` only reads; `warehouse` does the work. A stock adjustment after a
count or a write-off is only a CARD here: it is decided ONLY by her tap in the app (POST /api/warehouse/adjustments/{id}/decide).
Hoola never moves money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

WAREHOUSE_TOOLS = [
    {"name": "warehouse", "description": (
        "Warehouse / godown manager: stock by bin, inward, picking, cycle counts. Item names are matched to HER stock list (Hoola "
        "Deals); prices are read from there, never typed here. action=bin: code (A-12 / B-03-2-4) or zone+aisle+rack+bin, kind "
        "pick|bulk|receiving|dispatch|quarantine|damage, capacity (units). action=bins_many: zone, aisles, racks, bins, kind, capacity. "
        "action=sku: name or sku, code, barcode (her pack barcode), unit, track none|batch|serial, abc (fix a class), home_bin. "
        "action=opening: lines [{item, qty, bin, batch, expiry}] (stock already lying in bins). action=grn (goods received): lines "
        "[{item, qty, batch, expiry, mfg, serials, damaged}] or text, or file_id (CSV / Excel sheet; for a challan PHOTO read it with "
        "file_read first and send lines), supplier, doc (challan / PO / bill no), expected [{item, qty}] (PO, to find short "
        "receipt), purchase (Thok purchase id). action=putaway: grn (accept Hoola's suggestion) or lines [{item, to_bin, qty, "
        "from_bin, batch}], force. action=move: item, from_bin, to_bin, qty, batch. action=pick: source list|deal|thok, refs (deal / "
        "Thok bill numbers; empty = all open), lines or text (her list), party -> pick list with a walking path (FEFO, waves). "
        "action=pick_done: pick, picked [{n, qty, serials}] or all=true, finish, picker. action=pick_cancel: pick. action=pick_sheet: "
        "pick (PDF). action=classify (ABC). action=count: bins [codes] or sku, or nothing = today's due bins -> BLIND count. "
        "action=count_enter: count, entries [{bin, item, batch, qty}]. action=count_close: count, zero_missing. action=recount: count. "
        "action=count_sheet: count (PDF). action=writeoff: item, bin, qty, batch, reason damaged|expired|lost|theft|sample|other, note "
        "(ONLY a card for her tap). action=labels: what bins|skus, codes. action=export: what stock|ledger|abc|expiry|slow|variance, "
        "count. action=settings: name, count_days {A,B,C}, abc_split [A,B], tolerance {A:{units,pct}}, near_expiry_days, slow_days, "
        "dead_days, count_bins_per_day, food, morning_time, rules."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["bin", "bins_many", "sku", "opening", "grn", "putaway", "move", "pick", "pick_done",
                                               "pick_cancel", "pick_sheet", "classify", "count", "count_enter", "count_close", "recount",
                                               "count_sheet", "writeoff", "labels", "export", "settings"]},
         "code": {"type": "string"}, "zone": {"type": "string"}, "aisle": {"type": "string"}, "rack": {"type": "string"},
         "bin": {"type": "string"}, "kind": {"type": "string"}, "capacity": {"type": "number"}, "aisles": {"type": "integer"},
         "racks": {"type": "integer"}, "bins": {"type": "array", "items": {"type": "string"}}, "bins_per_rack": {"type": "integer"},
         "name": {"type": "string"}, "sku": {"type": "string"}, "barcode": {"type": "string"}, "unit": {"type": "string"},
         "track": {"type": "string"}, "abc": {"type": "string"}, "home_bin": {"type": "string"},
         "lines": {"type": "array", "items": {"type": "object"}}, "text": {"type": "string"}, "file_id": {"type": "string"},
         "supplier": {"type": "string"}, "doc": {"type": "string"}, "expected": {"type": "array", "items": {"type": "object"}},
         "purchase": {"type": "string"}, "grn": {"type": "string"}, "force": {"type": "boolean"}, "item": {"type": "string"},
         "from_bin": {"type": "string"}, "to_bin": {"type": "string"}, "qty": {"type": "number"}, "batch": {"type": "string"},
         "source": {"type": "string"}, "refs": {"type": "array", "items": {"type": "string"}}, "party": {"type": "string"},
         "pick": {"type": "string"}, "picked": {"type": "array", "items": {"type": "object"}}, "all": {"type": "boolean"},
         "finish": {"type": "boolean"}, "picker": {"type": "string"}, "count": {"type": "string"},
         "entries": {"type": "array", "items": {"type": "object"}}, "zero_missing": {"type": "boolean"}, "reason": {"type": "string"},
         "note": {"type": "string"}, "what": {"type": "string"}, "codes": {"type": "array", "items": {"type": "string"}},
         "count_days": {"type": "object"}, "abc_split": {"type": "array", "items": {"type": "number"}}, "tolerance": {"type": "object"},
         "near_expiry_days": {"type": "integer"}, "slow_days": {"type": "integer"}, "dead_days": {"type": "integer"},
         "count_bins_per_day": {"type": "integer"}, "food": {"type": "boolean"}, "morning_time": {"type": "string"},
         "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "warehouse_dekho", "description": (
        "Read the godown (nothing changes). what=day (counts due, open picks, receiving to put away, expiry, cards waiting, stock "
        "list differences) | bins (zone, kind) | bin (bin: what is in it + moves) | stock (bin / sku) | skus (q) | sku (sku) | "
        "ledger (sku, bin, days) | grns | grn (grn) | picks (status) | pick (pick) | counts (status) | count (count; blind) | due "
        "(what to count) | adjustments (status) | expiry (days) | slow (slow / dead stock) | recon (bins vs stock list) | settings | "
        "rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "bins", "bin", "stock", "skus", "sku", "ledger", "grns", "grn", "picks", "pick", "counts",
                                             "count", "due", "adjustments", "expiry", "slow", "recon", "settings", "rules"]},
         "bin": {"type": "string"}, "sku": {"type": "string"}, "zone": {"type": "string"}, "kind": {"type": "string"},
         "q": {"type": "string"}, "days": {"type": "integer"}, "grn": {"type": "string"}, "pick": {"type": "string"},
         "count": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
WAREHOUSE_LABELS = {"warehouse": "Godown ka kaam kar raha hoon", "warehouse_dekho": "Godown dekh raha hoon"}

_OWNER_ONLY = ("settings", "opening", "bins_many")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _by(ctx: Ctx) -> str:
    try:
        from ..employee.service import actor_label
        return actor_label(ctx.tenant_id, _actor(ctx))
    except Exception:
        return "Owner" if _owner(ctx) else _actor(ctx)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..warehouse import service as S
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Godown ka kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner badal sakti hain.")
    t, conv, by = ctx.tenant_id, ctx.conversation_id, _by(ctx)
    try:
        if action == "bin":
            kw = {k: _s(a[k]) for k in ("code", "zone", "aisle", "rack", "bin", "kind", "note") if k in a and not isinstance(a[k], list)}
            if "capacity" in a:
                kw["capacity"] = a["capacity"]
            return S.save_bin(t, **kw)
        if action == "bins_many":
            return S.make_bins(t, _s(a.get("zone")), a.get("aisles") or 1, a.get("racks") or 1, a.get("bins_per_rack") or 0,
                               _s(a.get("kind")) or "pick", a.get("capacity"))
        if action == "sku":
            if a.get("abc") and not _owner(ctx):
                raise ToolError("ABC class sirf owner badal sakti hain.")
            return S.save_sku(t, **{k: _s(a[k]) for k in ("name", "sku", "code", "barcode", "unit", "track", "abc", "home_bin", "note") if k in a})
        if action == "opening":
            return S.opening(t, a.get("lines"), _s(a.get("text")), _s(a.get("bin")), by)
        if action == "grn":
            return S.grn(t, a.get("lines"), _s(a.get("text")), _s(a.get("file_id")), _s(a.get("supplier")), _s(a.get("doc")),
                         _s(a.get("source")), _s(a.get("purchase")), a.get("expected"), by, conv)
        if action == "putaway":
            return S.putaway(t, _s(a.get("grn")), a.get("lines"), bool(a.get("force")), by, conv)
        if action == "move":
            return S.move(t, _s(a.get("item")), _s(a.get("from_bin")), _s(a.get("to_bin")), a.get("qty"), _s(a.get("batch")), bool(a.get("force")), by)
        if action == "pick":
            return S.pick_list(t, _s(a.get("source")) or "list", a.get("refs"), a.get("lines"), _s(a.get("text")), _s(a.get("party")), by, conv)
        if action == "pick_done":
            return S.pick_confirm(t, _s(a.get("pick")), a.get("picked"), bool(a.get("all")), bool(a.get("finish")), _s(a.get("picker")), by, conv)
        if action == "pick_cancel":
            return S.pick_cancel(t, _s(a.get("pick")), _s(a.get("reason")))
        if action == "pick_sheet":
            return S.pick_sheet(t, _s(a.get("pick")), conv)
        if action == "classify":
            return S.classify(t)
        if action == "count":
            return S.count_plan(t, a.get("bins"), _s(a.get("sku")), _s(a.get("kind")) or "cycle", _s(a.get("reason")), conv)
        if action == "count_enter":
            return S.count_enter(t, _s(a.get("count")), a.get("entries") or [], by)
        if action == "count_close":
            return S.count_close(t, _s(a.get("count")), bool(a.get("zero_missing")), by, conv)
        if action == "recount":
            return S.recount(t, _s(a.get("count")), conv)
        if action == "count_sheet":
            return S.count_sheet(t, _s(a.get("count")), conv)
        if action == "writeoff":
            r = S.writeoff_request(t, _s(a.get("item")), _s(a.get("bin")), a.get("qty"), _s(a.get("batch")), _s(a.get("reason")),
                                   _s(a.get("note")), by, conv)
            return {**r, "status": "needs_tap", "say": r["say"] + " Card aapke app mein hai: haan / mana wahin se."}
        if action == "labels":
            return S.labels(t, _s(a.get("what")) or "bins", a.get("codes"), conv)
        if action == "export":
            return S.export(t, _s(a.get("what")) or "stock", _s(a.get("count")), conv)
        if action == "settings":
            keys = ("name", "count_days", "abc_split", "tolerance", "near_expiry_days", "slow_days", "dead_days", "count_bins_per_day", "food",
                    "rules", "morning_time")
            return S.save_settings(t, **{k: a[k] for k in keys if k in a})
    except (S.WarehouseError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..warehouse import rules as R
    from ..warehouse import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "bins":
            return {"bins": S.bins(t, _s(a.get("zone")), _s(a.get("kind")))}
        if what == "bin":
            return S.bin_view(t, _s(a.get("bin")))
        if what == "stock":
            return {"lots": S.stock_by_bin(t, _s(a.get("bin")), _s(a.get("sku")))}
        if what == "skus":
            return {"skus": S.skus(t, _s(a.get("q")))}
        if what == "sku":
            return S.sku_view(t, _s(a.get("sku")))
        if what == "ledger":
            return S.ledger(t, _s(a.get("sku")), _s(a.get("bin")), int(a.get("days") or 30))
        if what == "grns":
            return {"grns": S.grns(t)}
        if what == "grn":
            return S.grn_view(t, _s(a.get("grn")))
        if what == "picks":
            return {"picks": S.picks(t, _s(a.get("status")))}
        if what == "pick":
            return S.pick_view(t, _s(a.get("pick")))
        if what == "counts":
            return {"counts": S.counts(t, _s(a.get("status")))}
        if what == "count":
            return S.count_view(t, _s(a.get("count")))
        if what == "due":
            return {"due": S.due(t)}
        if what == "adjustments":
            return {"adjustments": S.adjusts(t, _s(a.get("status")))}
        if what == "expiry":
            return S.near_expiry(t, a.get("days"))
        if what == "slow":
            return S.slow_dead(t)
        if what == "recon":
            return S.recon(t)
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "count_days": R.COUNT_DAYS, "abc_split": R.ABC_SPLIT, "tolerance": R.TOLERANCE,
                    "itc": R.ITC_NOTE, "records": R.RECORDS_NOTE, "food": R.FOOD_NOTE, "bin_kinds": R.BIN_KINDS, "reasons": R.REASONS}
    except (S.WarehouseError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def warehouse(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def warehouse_dekho(ctx: Ctx, what, **a: Any):
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Godown ki jaankari graahak ke liye nahi.")
    return await asyncio.to_thread(_read, ctx, str(what), a)


WAREHOUSE_HANDLERS = {"warehouse": warehouse, "warehouse_dekho": warehouse_dekho}
