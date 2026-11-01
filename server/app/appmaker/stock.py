"""v0.357 STOCK (App Sahayak Phase 21, owner: "START PHASE 21"): stock per product for her shop app.

She sets how many of a product she has (and when to warn her). Every order takes its quantities out of stock under one lock
BEFORE the row is written, so two customers can never buy the last piece; an order asking for more than is left is refused
with the product named; a retried write (same cid) never takes stock twice; a cancelled order puts its quantities back once.
When a product falls to its warning level her chat hears it once. The app shows "Sold out" and will not add it to a cart.
A product without a stock number stays unlimited, exactly as before. Kept in AppProject.backend["stock"]:
{product id: {"qty": int, "low": int}} - no new table."""
from __future__ import annotations

import json
import threading
from typing import Any

from ..db import session
from ..site import webapp as W
from .models import AppProject
from . import locks as LK                     # v0.390 one cross-process lock per app

_LOCK = threading.Lock()
LOW_DEFAULT = 3
MAX_QTY = 1_000_000
STATS = {"reserved": 0, "refused": 0, "returned": 0, "low_notes": 0}


class StockError(W.AppError):
    pass


def table(r: AppProject) -> dict[str, dict[str, int]]:
    from . import backend as BE
    with session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend if row else r.backend, {})
    return dict(be.get("stock") or {})


def view(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    st = table(r)
    prods = [{"id": k, "name": p.get("name"), "price": p.get("price"),
              "qty": (st.get(k) or {}).get("qty"), "low": (st.get(k) or {}).get("low", LOW_DEFAULT),
              "sold_out": (st.get(k) or {}).get("qty") == 0} for k, p in list(BE._products(r).items())[:500]]
    return {"products": prods, "tracked": sum(1 for p in prods if p["qty"] is not None),
            "sold_out": sum(1 for p in prods if p["sold_out"]),
            "note": "Blank = unlimited (not counted). Orders take stock the moment they are placed; a cancelled order puts it back."}


def _int(v: Any, what: str) -> int:
    try:
        f = float(str(v).strip())
    except (TypeError, ValueError):
        raise StockError(f"{what}: poora number chahiye.")
    if f != int(f) or f < 0 or f > MAX_QTY:
        raise StockError(f"{what}: 0 se {MAX_QTY:,} tak poora number.")
    return int(f)


def set_items(r: AppProject, items: dict[str, Any]) -> dict[str, Any]:
    """{product id: {qty: n | None (unlimited), low: n}}. Unknown products are ignored."""
    from . import backend as BE
    prods = BE._products(r)
    if not isinstance(items, dict):
        raise StockError("items = {product id: {qty, low}}")
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        st = dict(be.get("stock") or {})
        for k, v in list(items.items())[:1000]:
            k = str(k)
            if k not in prods or not isinstance(v, dict):
                continue
            cur = dict(st.get(k) or {})
            if "qty" in v:
                if v["qty"] in (None, ""):
                    cur.pop("qty", None)
                else:
                    cur["qty"] = _int(v["qty"], str(prods[k].get("name") or k))
                    cur.pop("warned", None) if cur["qty"] > int(cur.get("low", LOW_DEFAULT)) else None
            if "low" in v and v["low"] not in (None, ""):
                cur["low"] = _int(v["low"], "Warning level")
            if "qty" in cur:
                st[k] = cur
            else:
                st.pop(k, None)
        be["stock"] = st
        row.backend = json.dumps(be, ensure_ascii=False)
        r.backend = row.backend
    _flush(r)
    return view(r)


def _flush(r: AppProject) -> None:
    """The app's content cache (60 s) is dropped so 'Sold out' shows at once."""
    try:
        from . import backend as BE
        from .android import service as AN
        AN._CACHE.pop(BE._j(r.android, {}).get("app_key") or "", None)
    except Exception:                                    # noqa: BLE001
        pass


def reserve(r: AppProject, want: list[tuple[str, int, str]]) -> list[tuple[str, int]]:
    """Takes [(product id, qty, name)] out of stock (only tracked products) or refuses the whole order. Returns what was
    taken (to put back if the row could not be written, or when the order is cancelled)."""
    from . import backend as BE
    need: dict[str, int] = {}
    names: dict[str, str] = {}
    for pid, q, name in want:
        need[pid] = need.get(pid, 0) + q
        names[pid] = name
    lows: list[str] = []
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        st = dict(be.get("stock") or {})
        taken = [(pid, q) for pid, q in need.items() if "qty" in (st.get(pid) or {})]
        if not taken:
            return []
        short = [(pid, int(st[pid]["qty"])) for pid, q in taken if int(st[pid]["qty"]) < q]
        if short:
            STATS["refused"] += 1
            raise StockError("; ".join(f"{names[p]}: {'khatam ho gaya (sold out)' if left == 0 else f'sirf {left} bache hain'}"
                                       for p, left in short) + ". Cart badal kar dobara bhejiye.", 409)
        for pid, q in taken:
            cur = dict(st[pid])
            before, cur["qty"] = int(cur["qty"]), int(cur["qty"]) - q
            low = int(cur.get("low", LOW_DEFAULT))
            if cur["qty"] <= low < before or (cur["qty"] == 0 and before > 0 and not cur.get("warned")):
                if not cur.get("warned"):
                    lows.append(f"{names[pid]}: {cur['qty']} bache" if cur["qty"] else f"{names[pid]}: khatam")
                    cur["warned"] = True
            st[pid] = cur
        be["stock"] = st
        row.backend = json.dumps(be, ensure_ascii=False)
    STATS["reserved"] += 1
    _flush(r)
    if lows:
        STATS["low_notes"] += 1
        try:
            from .android.service import _note
            _note(r, f"{r.name or 'Aapki app'} ({r.number}) stock kam: " + ", ".join(lows)
                  + ". Naya maal aaye to stock badha dijiye (app ka data > Stock).")
        except Exception:                                # noqa: BLE001
            pass
    return taken


def put_back(r: AppProject, taken: list[tuple[str, int]] | list[list[Any]]) -> None:
    from . import backend as BE
    if not taken:
        return
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        st = dict(be.get("stock") or {})
        for pid, q in taken:
            if "qty" in (st.get(pid) or {}):
                cur = dict(st[pid])
                cur["qty"] = min(MAX_QTY, int(cur["qty"]) + int(q))
                if cur["qty"] > int(cur.get("low", LOW_DEFAULT)):
                    cur.pop("warned", None)
                st[pid] = cur
        be["stock"] = st
        row.backend = json.dumps(be, ensure_ascii=False)
    STATS["returned"] += 1
    _flush(r)


def decorate(r: AppProject, products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The app's product list with `stock` (tracked ones) and `sold_out` - read fresh, not from the content cache.
    v0.362 products with sizes carry `variants` (each with its own stock)."""
    st = table(r)
    from . import variants as VR
    products = VR.decorate(r, products, st)
    out = []
    for p in products:
        q = (st.get(str(p.get("id"))) or {}).get("qty") if isinstance(p, dict) else None
        out.append({**p, "stock": q, "sold_out": q == 0} if q is not None else p)
    return out
