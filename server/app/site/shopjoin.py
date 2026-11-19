"""v0.999.14 ONE SHOP step 1 (gap 9 of docs/research/lovable/03_backend_vs_hoola.md, owner: "Full merge, in steps"):
one product list and one stock count for her website shop and her app.

Before: the website shop kept its products and stock in `site_shop_products`, the app kept its products in her business
facts and its stock in the project's stock table (`appmaker/stock.py`). The same piece could be sold twice - once on the
website, once in the phone app - because each side counted its own stock.

Now, for a site joined to its App Sahayak project (every site is, since B4 joins one on its first public call):
- the website's products are part of the app's products (`products_for` -> `backend._base_products` and the phone app's
  content), with the website product's own id, so a phone app on the same project shows and sells them;
- their stock lives in ONE place - the project's stock table. The column on `site_shop_products` is moved there once
  (`move_stock`, under the app's lock) and is not read again; every website checkout and every app order takes from the
  same count under the same lock, a cancel puts it back there;
- the website stays where she edits these products (step 2 moves the orders, step 3 the old orders).

A site with no project keeps the old path, unchanged."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select

from ..db import now, session

log = logging.getLogger("santosh.site")


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def project_of(site_id: str):
    """The site's live App Sahayak project, or None."""
    from . import shoppay as SP
    try:
        return SP.project_of(site_id)
    except Exception:                                   # noqa: BLE001 - a shop never breaks because the link could not be read
        log.debug("shop project", exc_info=True)
        return None


def joined(site_id: str):
    """The project whose stock table this site's shop uses (its stock moved there first), or None (the old path)."""
    p = project_of(site_id)
    if p is None:
        return None
    move_stock(site_id, p)
    return p


def moved(p, site_id: str) -> bool:
    from ..appmaker import backend as BE
    with session() as s:
        from ..appmaker.models import AppProject
        row = s.get(AppProject, p.id)
        be = BE._j(row.backend if row else p.backend, {})
    return site_id in (be.get("shop_stock") or {})


def move_stock(site_id: str, p) -> int:
    """Once per site: the website products' stock column becomes rows of the project's stock table (by product id).
    A product the app already counts keeps the app's number. Returns how many were moved."""
    from ..appmaker import backend as BE
    from ..appmaker import locks as LK
    from ..appmaker import stock as SK
    from ..appmaker.models import AppProject
    from . import shop as SH
    if moved(p, site_id):
        return 0
    SH.ensure_tables()
    with session() as s:
        stocks = {x.id: int(x.stock) for x in s.scalars(select(SH.SiteShopProduct).where(
            SH.SiteShopProduct.site_id == site_id, SH.SiteShopProduct.stock.is_not(None))).all()}
    n = 0
    with LK.app(p.id), session() as s:
        row = s.get(AppProject, p.id)
        be = BE._j(row.backend, {})
        done = dict(be.get("shop_stock") or {})
        if site_id in done:                             # another worker moved it meanwhile
            return 0
        st = dict(be.get("stock") or {})
        for pid, q in stocks.items():
            if "qty" not in (st.get(pid) or {}):
                st[pid] = {"qty": max(0, min(SK.MAX_QTY, q)), "low": SK.LOW_DEFAULT}
                n += 1
        done[site_id] = {"at": now().isoformat(), "moved": n}
        be["stock"], be["shop_stock"] = st, done
        row.backend = json.dumps(be, ensure_ascii=False)
    SK._flush(p)
    log.info("shop stock moved site=%s app=%s n=%d", site_id, p.id, n)
    return n


def sites_of(p) -> list[str]:
    """The websites whose backend is this project."""
    from . import applink as AL
    from .models import Site
    with session() as s:
        rows = s.scalars(select(Site).where(Site.tenant_id == p.tenant_id, Site.app.like(f"%{p.id}%"))).all()
        return [r.id for r in rows if AL.linked_id(r) == p.id]


def products_for(p) -> dict[str, dict[str, Any]]:
    """The joined websites' active shop products, as app products (id = the website product's id, price in rupees)."""
    from . import shop as SH
    sites = sites_of(p)
    if not sites:
        return {}
    SH.ensure_tables()
    out: dict[str, dict[str, Any]] = {}
    with session() as s:
        for x in s.scalars(select(SH.SiteShopProduct).where(SH.SiteShopProduct.site_id.in_(sites),
                                                            SH.SiteShopProduct.active == 1)
                           .order_by(SH.SiteShopProduct.title)).all():
            if getattr(x, "vendor", None) and getattr(x, "mod", None) != "ok":   # a seller's product she has not approved
                continue
            out[x.id] = {"id": x.id, "name": x.title, "price": round(x.price / 100, 2), "unit": x.unit or "",
                         "category": "", "photo": x.photo or "", "from": "website", "slug": x.slug}
    return out


def stock_of(p, ids: list[str]) -> dict[str, int | None]:
    """The one stock count for these products (None = not counted)."""
    from ..appmaker import stock as SK
    st = SK.table(p)
    return {i: (st.get(i) or {}).get("qty") for i in ids}


def set_stock(p, values: dict[str, Any]) -> None:
    """Her (or a seller's) stock numbers for website products, into the one table, by product id. None / '' /
    'unlimited' = not counted. Written directly under the app's lock: a product not on sale yet (a seller's, waiting for
    her OK) keeps its number too."""
    from ..appmaker import backend as BE
    from ..appmaker import locks as LK
    from ..appmaker import stock as SK
    from ..appmaker.models import AppProject
    if not values:
        return
    with LK.app(p.id), session() as s:
        row = s.get(AppProject, p.id)
        be = BE._j(row.backend, {})
        st = dict(be.get("stock") or {})
        for k, v in values.items():
            if v in (None, "", "unlimited"):
                st.pop(str(k), None)
                continue
            cur = dict(st.get(str(k)) or {"low": SK.LOW_DEFAULT})
            cur["qty"] = max(0, min(SK.MAX_QTY, int(v)))
            if cur["qty"] > int(cur.get("low", SK.LOW_DEFAULT)):
                cur.pop("warned", None)
            st[str(k)] = cur
        be["stock"] = st
        row.backend = json.dumps(be, ensure_ascii=False)
    SK._flush(p)
