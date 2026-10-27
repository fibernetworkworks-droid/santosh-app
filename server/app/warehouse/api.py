"""HTTP routes of the Godown Sahayak (/api/warehouse/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY way a stock adjustment / write-off is approved: POST /api/warehouse/adjustments/{id}/decide from her app (her tap)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/warehouse", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.WarehouseError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    def _s(v: Any) -> str:
        return "" if v is None else str(v)

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("name", "count_days", "abc_split", "tolerance", "near_expiry_days", "slow_days", "dead_days", "count_bins_per_day", "food",
                "rules", "morning_time")
        return await run(S.save_settings, tenant, **{k: b[k] for k in keys if k in b})

    # ---- bins
    @r.get("/bins")
    async def list_bins(zone: str = "", kind: str = "", tenant: str = Depends(current_tenant)):
        return {"bins": await run(S.bins, tenant, zone, kind)}

    @r.post("/bins")
    async def save_bin(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if b.get("many"):
            return await run(S.make_bins, tenant, _s(b.get("zone")), b.get("aisles") or 1, b.get("racks") or 1, b.get("bins") or 0,
                             _s(b.get("kind")) or "pick", b.get("capacity"))
        kw = {k: _s(b[k]) for k in ("code", "zone", "aisle", "rack", "bin", "kind", "note") if k in b}
        if "capacity" in b:
            kw["capacity"] = b["capacity"]
        if "active" in b:
            kw["active"] = bool(b["active"])
        return await run(S.save_bin, tenant, **kw)

    @r.get("/bins/{ref}")
    async def get_bin(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.bin_view, tenant, ref)

    # ---- SKUs + stock
    @r.get("/skus")
    async def list_skus(q: str = "", tenant: str = Depends(current_tenant)):
        return {"skus": await run(S.skus, tenant, q)}

    @r.post("/skus")
    async def save_sku(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_sku, tenant, **{k: _s(b[k]) for k in ("name", "sku", "code", "barcode", "unit", "track", "abc", "home_bin", "note") if k in b})

    @r.get("/skus/{ref}")
    async def get_sku(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.sku_view, tenant, ref)

    @r.get("/stock")
    async def stock(bin: str = "", sku: str = "", tenant: str = Depends(current_tenant)):
        return {"lots": await run(S.stock_by_bin, tenant, bin, sku)}

    @r.post("/opening")
    async def opening(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.opening, tenant, b.get("lines"), _s(b.get("text")), _s(b.get("bin")))

    @r.post("/move")
    async def move(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.move, tenant, _s(b.get("item")), _s(b.get("from_bin")), _s(b.get("to_bin")), b.get("qty"), _s(b.get("batch")),
                         bool(b.get("force")))

    @r.get("/ledger")
    async def ledger(sku: str = "", bin: str = "", days: int = 30, tenant: str = Depends(current_tenant)):
        return await run(S.ledger, tenant, sku, bin, days)

    # ---- inward
    @r.get("/grns")
    async def list_grns(tenant: str = Depends(current_tenant)):
        return {"grns": await run(S.grns, tenant)}

    @r.post("/grns")
    async def new_grn(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.grn, tenant, b.get("lines"), _s(b.get("text")), _s(b.get("file_id")), _s(b.get("supplier")), _s(b.get("doc")),
                         _s(b.get("source")), _s(b.get("purchase")), b.get("expected"))

    @r.get("/grns/{ref}")
    async def get_grn(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.grn_view, tenant, ref)

    @r.post("/grns/{ref}/putaway")
    async def putaway(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.putaway, tenant, ref, b.get("lines"), bool(b.get("force")))

    # ---- picks
    @r.get("/picks")
    async def list_picks(status: str = "", tenant: str = Depends(current_tenant)):
        return {"picks": await run(S.picks, tenant, status)}

    @r.post("/picks")
    async def new_pick(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.pick_list, tenant, _s(b.get("source")) or "list", b.get("refs"), b.get("lines"), _s(b.get("text")), _s(b.get("party")))

    @r.get("/picks/{ref}")
    async def get_pick(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.pick_view, tenant, ref)

    @r.post("/picks/{ref}/confirm")
    async def pick_confirm(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.pick_confirm, tenant, ref, b.get("picked"), bool(b.get("all")), bool(b.get("finish")), _s(b.get("picker")))

    @r.post("/picks/{ref}/cancel")
    async def pick_cancel(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.pick_cancel, tenant, ref, _s(_b(body).get("reason")))

    @r.post("/picks/{ref}/sheet")
    async def pick_sheet(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.pick_sheet, tenant, ref)

    # ---- counts
    @r.post("/classify")
    async def classify(tenant: str = Depends(current_tenant)):
        return await run(S.classify, tenant)

    @r.get("/due")
    async def due(tenant: str = Depends(current_tenant)):
        return {"due": await run(S.due, tenant)}

    @r.get("/counts")
    async def list_counts(status: str = "", tenant: str = Depends(current_tenant)):
        return {"counts": await run(S.counts, tenant, status)}

    @r.post("/counts")
    async def new_count(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.count_plan, tenant, b.get("bins"), _s(b.get("sku")), _s(b.get("kind")) or "cycle", _s(b.get("reason")))

    @r.get("/counts/{ref}")
    async def get_count(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.count_view, tenant, ref)            # blind: never the system quantity while open

    @r.post("/counts/{ref}/enter")
    async def count_enter(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.count_enter, tenant, ref, _b(body).get("entries") or [])

    @r.post("/counts/{ref}/close")
    async def count_close(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.count_close, tenant, ref, bool(_b(body).get("zero_missing")))

    @r.post("/counts/{ref}/recount")
    async def recount(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.recount, tenant, ref)

    @r.post("/counts/{ref}/sheet")
    async def count_sheet(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.count_sheet, tenant, ref)

    # ---- adjustments / write-offs: HER tap
    @r.get("/adjustments")
    async def list_adjusts(status: str = "", tenant: str = Depends(current_tenant)):
        return {"adjustments": await run(S.adjusts, tenant, status)}

    @r.post("/writeoff")
    async def writeoff(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.writeoff_request, tenant, _s(b.get("item")), _s(b.get("bin")), b.get("qty"), _s(b.get("batch")), _s(b.get("reason")),
                         _s(b.get("note")))

    @r.post("/adjustments/{ref}/decide")
    async def decide(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        return await run(S.decide_adjust, tenant, ref, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), by_tap=True)

    # ---- reports / files
    @r.get("/expiry")
    async def expiry(days: int = 0, tenant: str = Depends(current_tenant)):
        return await run(S.near_expiry, tenant, days or None)

    @r.get("/slow")
    async def slow(tenant: str = Depends(current_tenant)):
        return await run(S.slow_dead, tenant)

    @r.get("/recon")
    async def recon(tenant: str = Depends(current_tenant)):
        return await run(S.recon, tenant)

    @r.post("/labels")
    async def labels(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.labels, tenant, _s(b.get("what")) or "bins", b.get("codes"))

    @r.post("/export")
    async def export(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.export, tenant, _s(b.get("what")) or "stock", _s(b.get("count")))

    return r
