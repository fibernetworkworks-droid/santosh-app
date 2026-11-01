"""v0.362 VARIANTS (App Sahayak Phase 26, owner: "CONTINUE"): sizes / weights / colours of a product in her app
(Atta 1 kg / 5 kg, Shirt S / M / L), each with its own price.

A variant is addressed as "<product id>::<variant id>" and behaves like a product of its own everywhere the app already
works with products: the cart line ("Atta (5 kg)", its price), the server's pricing (`backend._products` lists every variant;
the phone never sends a price), stock (counted per variant), coupons, delivery and GST (the variant keeps its product's HSN /
rate). The app content gives each product its `variants` list, so the kit's Add button becomes size chips in every generated
screen without rewriting it. Kept in AppProject.backend["variants"] = {product id: [{id, name, price}]}."""
from __future__ import annotations

import json
import re
from typing import Any

from ..db import session
from ..site import webapp as W
from .models import AppProject

SEP = "::"
MAX_PER = 12
STATS = {"saved": 0}


class VariantError(W.AppError):
    pass


def table(r: AppProject) -> dict[str, list[dict[str, Any]]]:
    from . import backend as BE
    with session() as s:
        row = s.get(AppProject, r.id)
        return dict(BE._j(row.backend if row else r.backend, {}).get("variants") or {})


def _slug(name: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "v")[:24]


def view(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    t = table(r)
    base = BE._base_products(r)
    return {"products": [{"id": k, "name": p.get("name"), "price": p.get("price"), "variants": t.get(k, [])}
                         for k, p in list(base.items())[:500]],
            "note": "Each size has its own price (and its own stock). Leave a product without sizes to sell it as before."}


def save(r: AppProject, pid: str, variants: Any) -> dict[str, Any]:
    """One product's sizes: [{name, price}] (an empty list removes them)."""
    from . import backend as BE
    from . import stock as SK
    base = BE._base_products(r)
    pid = str(pid or "")
    if pid not in base:
        by_name = {str(p.get("name") or "").strip().lower(): k for k, p in base.items()}
        pid = by_name.get(pid.strip().lower(), "")
    if not pid:
        raise VariantError("Yeh product nahi mila.", 404)
    if not isinstance(variants, list):
        raise VariantError("variants = [{name, price}]")
    out, seen = [], set()
    for v in variants[:MAX_PER]:
        if not isinstance(v, dict):
            continue
        name = re.sub(r"[\x00-\x1f]+", " ", str(v.get("name") or "")).strip()[:40]
        if not name:
            continue
        try:
            price = round(float(str(v.get("price")).replace(",", "").replace("₹", "").strip()), 2)
        except (TypeError, ValueError):
            raise VariantError(f"{name}: price number mein.")
        if not 0 < price <= 10_000_000:
            raise VariantError(f"{name}: price 1 se 1 crore tak.")
        vid = _slug(name)
        while vid in seen:
            vid = vid[:20] + str(len(seen))
        seen.add(vid)
        out.append({"id": vid, "name": name, "price": int(price) if price == int(price) else price})
    with session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        t = dict(be.get("variants") or {})
        if out:
            t[pid] = out
        else:
            t.pop(pid, None)
        be["variants"] = t
        row.backend = json.dumps(be, ensure_ascii=False)
        r.backend = row.backend
    SK._flush(r)
    STATS["saved"] += 1
    return view(r)


def expand(r: AppProject, base: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Base products + one entry per variant ("pid::vid", "Name (size)", its price) for the server's pricing."""
    t = table(r)
    out = dict(base)
    for pid, vs in t.items():
        p = base.get(pid)
        if not p or not vs:
            continue
        out.pop(pid, None)                     # a product with sizes is bought by its size (no size = no price)
        for v in vs:
            out[f"{pid}{SEP}{v['id']}"] = {**p, "id": f"{pid}{SEP}{v['id']}", "name": f"{p.get('name')} ({v['name']})",
                                         "price": v["price"], "variant_of": pid}
    return out


def decorate(r: AppProject, products: list[dict[str, Any]], stock: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    """The app's product list: each product with sizes gets `variants` [{id, name, price, stock?, sold_out?}]."""
    t = table(r)
    if not t:
        return products
    out = []
    for p in products:
        vs = t.get(str(p.get("id"))) if isinstance(p, dict) else None
        if not vs:
            out.append(p)
            continue
        lst = []
        for v in vs:
            q = (stock.get(f"{p['id']}{SEP}{v['id']}") or {}).get("qty")
            lst.append({**v, **({"stock": q, "sold_out": q == 0} if q is not None else {})})
        out.append({**p, "variants": lst, "price": min(v["price"] for v in vs),
                    **({"sold_out": True} if all(x.get("sold_out") for x in lst) else {})})
    return out
