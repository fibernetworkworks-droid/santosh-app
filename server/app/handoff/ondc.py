"""v0.116 Optional ONDC listing: get her shop ready for the ONDC network through the seller app SHE chooses.

Official route only: on ONDC a shop is listed by a registered seller network participant (a "seller app"), which holds
the network keys, signs the protocol calls and settles the money. Hoola is not one and never calls the ONDC gateway. What
Hoola does (off until she switches it on):
  setup      her listing details: domain (retail category), seller app name she picked, store name, FSSAI (food),
             consumer-care contact (CCPA e-commerce rules), pincodes / radius she serves, time to ship, returns,
             cancellation, cash on delivery, fulfilment.
  items      her Hoola stock list (the same one Hoola Deals quotes from) + the extra things ONDC catalogues ask for per item
             (category, MRP, brand, net quantity, maker / packer and address, generic name, month-year of packing, country
             of origin, veg / non-veg, HSN, image file).
  readiness  blockers / warnings in plain words (GSTIN check digit, FSSAI for food, consumer care, price <= MRP, Legal
             Metrology fields for packaged goods, stock counted, images).
  export     one Excel (catalogue rows with ONDC retail attribute names + seller sheet + how-to) as her file; she uploads it
             in her seller app. Stock that changed after the last export is pointed out so she re-uploads.
ONDC retail domain codes used: RET10 grocery, RET11 food & beverage, RET12 fashion, RET13 beauty & personal care,
RET14 electronics, RET15 appliances, RET16 home & kitchen, RET18 health & wellness (others: ask her seller app).
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session
from ..net import policy
from .aa import HandoffError, _utc

DOMAINS = {"RET10": "Grocery (kirana)", "RET11": "Food & beverage (khana / restaurant)", "RET12": "Fashion (kapde, joote)",
           "RET13": "Beauty & personal care", "RET14": "Electronics", "RET15": "Appliances", "RET16": "Home & kitchen",
           "RET18": "Health & wellness"}
PACKAGED = {"RET10", "RET13", "RET14", "RET15", "RET16", "RET18"}     # Legal Metrology (Packaged Commodities) fields
FOOD = {"RET10", "RET11"}
ITEM_KEYS = ("category", "mrp", "brand", "net_quantity", "maker", "maker_address", "generic_name", "packed_on",
             "country", "veg", "hsn", "image_file_id", "description")
STATS = {"exports": 0}
GSTIN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
FSSAI = re.compile(r"^\d{14}$")


class OndcListing(Base):
    __tablename__ = "handoff_ondc_listing"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    on: Mapped[bool] = mapped_column(Boolean, default=False)
    domain: Mapped[str] = mapped_column(String(6), default="RET10")
    seller_app: Mapped[str] = mapped_column(String(80), default="")
    store_name: Mapped[str] = mapped_column(String(120), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    fssai: Mapped[str] = mapped_column(String(14), default="")
    care: Mapped[dict] = mapped_column(JSON, default=dict)                  # {name, email, phone}
    pincodes: Mapped[list] = mapped_column(JSON, default=list)
    radius_km: Mapped[int] = mapped_column(Integer, default=0)
    ship_minutes: Mapped[int] = mapped_column(Integer, default=60)
    returnable: Mapped[bool] = mapped_column(Boolean, default=False)
    return_days: Mapped[int] = mapped_column(Integer, default=0)
    cancellable: Mapped[bool] = mapped_column(Boolean, default=True)
    cod: Mapped[bool] = mapped_column(Boolean, default=False)
    fulfilment: Mapped[str] = mapped_column(String(10), default="delivery")  # delivery | pickup | both
    items: Mapped[dict] = mapped_column(JSON, default=dict)                 # stock key -> extra ONDC fields
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _row(tenant: str, s) -> OndcListing:
    r = s.get(OndcListing, tenant)
    if r is None:
        r = OndcListing(tenant_id=tenant, updated_at=now())
        from ..net.business import Business
        b = s.get(Business, tenant)
        if b is not None:
            r.store_name, r.gstin = b.name or "", (getattr(b, "gstin", "") or "")[:15]
        s.add(r)
        s.flush()
    return r


def view(r: OndcListing) -> dict[str, Any]:
    return {"on": r.on, "domain": r.domain, "domain_say": DOMAINS.get(r.domain, r.domain), "seller_app": r.seller_app,
            "store_name": r.store_name, "gstin": r.gstin, "fssai": r.fssai, "care": r.care or {}, "pincodes": r.pincodes or [],
            "radius_km": r.radius_km, "ship_minutes": r.ship_minutes, "returnable": r.returnable, "return_days": r.return_days,
            "cancellable": r.cancellable, "cod": r.cod, "fulfilment": r.fulfilment,
            "exported_at": _utc(r.exported_at).isoformat() if r.exported_at else ""}


def setup(tenant: str, **kw) -> dict[str, Any]:
    with session() as s:
        r = _row(tenant, s)
        if "on" in kw and kw["on"] is not None:
            r.on = bool(kw["on"])
        if kw.get("domain"):
            d = str(kw["domain"]).upper()
            if d not in DOMAINS:
                raise HandoffError("domain: " + ", ".join(f"{k} ({v})" for k, v in DOMAINS.items()))
            r.domain = d
        for k, lim in (("seller_app", 80), ("store_name", 120)):
            if kw.get(k) is not None:
                setattr(r, k, policy.clean_name(kw[k], lim))
        if kw.get("gstin") is not None:
            g = str(kw["gstin"]).strip().upper()
            if g and not GSTIN.match(g):
                raise HandoffError("GSTIN 15 akshar ka hota hai (jaise 27ABCDE1234F1Z5).")
            r.gstin = g
        if kw.get("fssai") is not None:
            f = re.sub(r"\D", "", str(kw["fssai"]))
            if f and not FSSAI.match(f):
                raise HandoffError("FSSAI number 14 ankon ka hota hai.")
            r.fssai = f
        if isinstance(kw.get("care"), dict):
            c = kw["care"]
            r.care = {"name": policy.clean_name(c.get("name"), 80), "email": str(c.get("email") or "")[:120].strip(),
                      "phone": re.sub(r"[^\d+]", "", str(c.get("phone") or ""))[:15]}
        if kw.get("pincodes") is not None:
            pins = kw["pincodes"] if isinstance(kw["pincodes"], list) else re.split(r"[,\s]+", str(kw["pincodes"]))
            r.pincodes = sorted({p for p in (re.sub(r"\D", "", str(x)) for x in pins) if re.fullmatch(r"[1-9]\d{5}", p)})[:200]
        for k, lo, hi in (("radius_km", 0, 100), ("ship_minutes", 10, 7 * 24 * 60), ("return_days", 0, 30)):
            if kw.get(k) is not None:
                try:
                    setattr(r, k, max(lo, min(hi, int(kw[k]))))
                except (TypeError, ValueError):
                    raise HandoffError(f"{k} ek number ho")
        for k in ("returnable", "cancellable", "cod"):
            if kw.get(k) is not None:
                setattr(r, k, bool(kw[k]))
        if kw.get("fulfilment") in ("delivery", "pickup", "both"):
            r.fulfilment = kw["fulfilment"]
        r.updated_at = now()
        s.flush()
        return view(r)


def set_item(tenant: str, item: str, **fields) -> dict[str, Any]:
    from ..net import deal
    items = deal._catalog_items(tenant)
    m = deal.match(items, item)
    if m is None or not m.get("id"):
        raise HandoffError(f"'{item}' aapke stock list mein nahi; pehle stock mein daaliye.")
    clean: dict[str, Any] = {}
    for k in ITEM_KEYS:
        v = fields.get(k)
        if v is None:
            continue
        if k == "mrp":
            try:
                clean[k] = round(float(v), 2)
            except (TypeError, ValueError):
                raise HandoffError("MRP ek number ho")
        elif k == "veg":
            clean[k] = bool(v)
        elif k == "hsn":
            h = re.sub(r"\D", "", str(v))
            if h and len(h) not in (4, 6, 8):
                raise HandoffError("HSN 4, 6 ya 8 ankon ka hota hai")
            clean[k] = h
        else:
            clean[k] = policy.quote(v, 300 if k in ("maker_address", "description") else 80)
    with session() as s:
        r = _row(tenant, s)
        cur = dict(r.items or {})
        cur[m["key"]] = {**(cur.get(m["key"]) or {}), **clean}
        r.items, r.updated_at = cur, now()
    return {"item": m["name"], "fields": cur[m["key"]]}


def _items(tenant: str, r: OndcListing) -> list[dict[str, Any]]:
    from ..net import deal
    out = []
    for it in deal._catalog_items(tenant):
        if not it.get("public", True) or it.get("kind") == "service":
            continue
        extra = (r.items or {}).get(it["key"]) or {}
        out.append({"name": it["name"], "key": it["key"], "unit": it["unit"], "price": it["price"], "gst_pct": it["gst_pct"],
                    "free": it["free"], "id": it["id"], **extra})
    return out


def readiness(tenant: str) -> dict[str, Any]:
    with session() as s:
        r = _row(tenant, s)
        v = view(r)
        items = _items(tenant, r)
        exported = _utc(r.exported_at)
    block, warn = [], []
    if not v["gstin"]:
        block.append("GSTIN: zyadatar seller apps aur ONDC par bechne ke liye GSTIN chahiye (kuch categories mein PAN se bhi).")
    if v["domain"] in FOOD and not v["fssai"]:
        block.append("FSSAI licence / registration number (14 ank) khane ki cheezon ke liye zaroori hai.")
    care = v["care"]
    if not (care.get("name") and (care.get("email") or care.get("phone"))):
        block.append("Customer care (naam + phone / email): e-commerce rules mein graahak ko dikhana zaroori hai.")
    if not v["store_name"]:
        block.append("Dukaan ka naam.")
    if not v["pincodes"] and not v["radius_km"]:
        warn.append("Kahan tak deliver karengi (pincode ya km): seller app mein bhi bharna hoga.")
    if not items:
        block.append("Stock list khaali hai: Hoola Deals > Stock mein cheezein daaliye (ya sheet se).")
    bad_items = []
    for it in items:
        miss = []
        if not it.get("price"):
            miss.append("daam")
        if it.get("mrp") is not None and it["price"] and it["price"] * (1 + it["gst_pct"] / 100) > it["mrp"] + 0.01:
            miss.append("daam MRP se zyada")
        if v["domain"] in PACKAGED:
            for k, say in (("mrp", "MRP"), ("net_quantity", "net quantity"), ("maker", "maker / packer"),
                           ("maker_address", "maker ka pata"), ("generic_name", "aam naam"), ("packed_on", "mahina-saal")):
                if not it.get(k):
                    miss.append(say)
        if not it.get("image_file_id"):
            miss.append("photo")
        if it.get("free") is None:
            miss.append("stock ginti")
        if v["domain"] in FOOD and it.get("veg") is None:
            miss.append("veg / non-veg")
        if miss:
            bad_items.append({"item": it["name"], "missing": miss})
    if bad_items:
        warn.append(f"{len(bad_items)} cheezon mein jaankari adhoori (seller app maangega).")
    changed = 0
    if exported:
        from ..net import deal
        with session() as s:
            changed = len(s.scalars(select(deal.StockItem.id).where(deal.StockItem.tenant_id == tenant,
                                                                    deal.StockItem.updated_at > exported)).all())
        if changed:
            warn.append(f"Pichhle export ke baad {changed} cheezon ka stock / daam badla: nayi sheet seller app mein daaliye.")
    return {"listing": v, "ready": not block, "blockers": block, "warnings": warn, "items": len(items), "item_gaps": bad_items[:60],
            "changed_since_export": changed,
            "how": ["ondc.org par 'seller apps' ki list se ek seller app chuniye (unki fees / commission dekh kar).",
                    "Seller app mein register kijiye: GSTIN / PAN, bank account (paise wahi bhejte hain), FSSAI (khana).",
                    "Hoola ki export sheet seller app ke 'bulk upload / catalogue' mein daaliye (unke template mein copy).",
                    "Order seller app mein aayenge; stock badle to Hoola se nayi sheet nikaaliye."],
            "say": "Taiyaar hai: sheet nikaal kar seller app mein daaliye." if not block else
                   "Pehle yeh bharna hoga: " + "; ".join(block)}


def export(tenant: str) -> dict[str, Any]:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    rd = readiness(tenant)
    with session() as s:
        r = _row(tenant, s)
        v = view(r)
        items = _items(tenant, r)
    if not items:
        raise HandoffError("Stock list khaali hai; pehle cheezein daaliye.")
    wb = Workbook()
    ws = wb.active
    ws.title = "ONDC catalogue"
    cols = ["descriptor.name", "descriptor.short_desc", "category_id", "price.value (incl. GST)", "price.maximum_value (MRP)",
            "quantity.unitized.measure", "quantity.available.count", "quantity.maximum.count", "gst_percent", "hsn",
            "brand", "@ondc/org/returnable", "@ondc/org/return_window", "@ondc/org/cancellable", "@ondc/org/time_to_ship",
            "@ondc/org/available_on_cod", "veg", "manufacturer_or_packer_name", "manufacturer_or_packer_address",
            "common_or_generic_name_of_commodity", "net_quantity_or_measure_of_commodity_in_pkg",
            "month_year_of_manufacture_packing_import", "imported_product_country_of_origin", "image (Hoola file)"]
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True)
    for it in items:
        price = round(it["price"] * (1 + it["gst_pct"] / 100), 2)
        ws.append([it["name"], it.get("description", ""), it.get("category", ""), price, it.get("mrp", ""), it["unit"],
                   "" if it["free"] is None else int(it["free"]), "", it["gst_pct"], it.get("hsn", ""), it.get("brand", ""),
                   v["returnable"], f"P{v['return_days']}D" if v["returnable"] else "", v["cancellable"],
                   f"PT{v['ship_minutes']}M" if v["ship_minutes"] < 1440 else f"P{v['ship_minutes'] // 1440}D", v["cod"],
                   "" if it.get("veg") is None else ("veg" if it["veg"] else "non-veg"), it.get("maker", ""),
                   it.get("maker_address", ""), it.get("generic_name", ""), it.get("net_quantity", ""), it.get("packed_on", ""),
                   it.get("country", "") or "India", it.get("image_file_id", "")])
    s2 = wb.create_sheet("Seller")
    for k, val in (("Store name", v["store_name"]), ("Domain", f"ONDC:{v['domain']} {v['domain_say']}"),
                   ("GSTIN", v["gstin"]), ("FSSAI", v["fssai"]), ("Consumer care name", v["care"].get("name", "")),
                   ("Consumer care email", v["care"].get("email", "")), ("Consumer care phone", v["care"].get("phone", "")),
                   ("Serviceable pincodes", ", ".join(v["pincodes"])), ("Radius km", v["radius_km"]),
                   ("Fulfilment", v["fulfilment"]), ("Seller app", v["seller_app"])):
        s2.append([k, val])
    s3 = wb.create_sheet("Kaise")
    for line in rd["how"] + ["", "Yeh sheet Hoola ne aapke stock se banayi. Seller app ka apna template ho to columns wahan copy kijiye.",
                             "Hoola ONDC network se khud nahi judta; listing aur orders aapke seller app mein."]:
        s3.append([line])
    buf = io.BytesIO()
    wb.save(buf)
    from .. import chatfiles
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    f = chatfiles.store(tenant, f"ONDC catalogue {re.sub(r'[^\w ]', '', v['store_name'])[:40] or 'shop'} {stamp}.xlsx",
                        buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with session() as s:
        r = _row(tenant, s)
        r.exported_at = now()
    STATS["exports"] += 1
    return {"file": {k: f.get(k) for k in ("file_id", "name", "size", "url")}, "items": len(items), "ready": rd["ready"],
            "blockers": rd["blockers"], "say": f"{len(items)} cheezon ki ONDC sheet taiyaar. Apne seller app mein upload kijiye." +
            ("" if rd["ready"] else " Pehle yeh bhi bharna: " + "; ".join(rd["blockers"]))}
