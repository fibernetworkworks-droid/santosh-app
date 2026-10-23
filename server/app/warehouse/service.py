"""Godown Sahayak: Hoola as a warehouse manager, end to end.

  1. Gets the job: "50 bori atta aaya, challan photo", "Gupta ka order nikalo", "A-12 mein kya hai", "aaj kaun se bin gine",
     "ye 3 carton toot gaye", a supplier's challan photo / PO / Excel, Hoola Deals accepted orders, Thok bills.
  2. Does the work: bins (zone / aisle / rack / bin, capacity), SKUs linked to HER stock list (Hoola Deals `hoola_stock`;
     prices and Thok cost read from there, never copied), batches with expiry (FEFO) and serials; GRN into a receiving bin with
     putaway suggestions (same SKU bin, fast movers near dispatch, capacity); pick lists from orders with a walking path sorted
     by location, waves for many orders, short picks; movement ledger per bin; ABC classes, cycle-count schedule, BLIND count
     sheets, variance report.
  3. Checked against rules and earlier work: expiry passed / near, shelf life left at receipt, duplicate serials, bin
     capacity, short receipt vs PO, tolerance per class, what moved since the count, bins vs the shared stock count.
  4. Ready as a card / file: GRN + putaway card, pick list card + walking-order PDF, count sheet PDF (no system quantity),
     variance report, bin / SKU QR + barcode labels PDF, Excel exports, morning note.
  5. Waits for her Haan: every stock adjustment after a count and every write-off is a card with a hash; ONLY
     `decide_adjust(by_tap=True)` from her app changes the stock. Hoola never moves money (no payments, no debit-note payment,
     GST ITC reversal is her CA's job).
  6. Delivers and learns: ledger keeps every movement; picks teach velocity -> ABC; short picks open a spot count.

Shared stock count (hoola_stock.qty): GRN from a challan / PO / photo / list adds to it, a pick from her own list takes from
it, an approved adjustment changes it. Thok billing / purchases and Hoola Deals handover already change it themselves, so a
GRN against a Thok purchase and a pick for a Thok bill / Hoola Deal leave it alone (`sync` false).
"""
from __future__ import annotations

import io
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ..db import now as _now, session
from . import rules as R
from .models import WhAdjust, WhBin, WhCount, WhGrn, WhLot, WhMove, WhPick, WhSettings, WhSku

log = logging.getLogger("santosh.warehouse")
_LOCK = threading.RLock()
RCV_CODE = "RCV"
DMG_CODE = "DMG"
QTN_CODE = "QTN"


class WarehouseError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def clock() -> datetime:
    return datetime.now(timezone.utc)


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return clock().astimezone(_tz(tenant)).date()


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("warehouse publish failed")


def _st(s, tenant: str) -> WhSettings:
    r = s.get(WhSettings, tenant)
    if r is None:
        r = WhSettings(tenant_id=tenant, count_days=dict(R.COUNT_DAYS), abc_split=list(R.ABC_SPLIT),
                       tolerance={k: dict(v) for k, v in R.TOLERANCE.items()}, seq={})
        s.add(r)
        s.flush()
    return r


def _next(st: WhSettings, kind: str, prefix: str) -> str:
    seq = dict(st.seq or {})
    seq[kind] = int(seq.get(kind) or 0) + 1
    st.seq = seq
    return f"{prefix}-{seq[kind]:04d}"


def _rs(v: float | None) -> str:
    if v is None:
        return "daam pata nahi"
    from ..thok.service import _rs as rs
    return rs(v)


def _days(st: WhSettings) -> dict[str, int]:
    d = dict(R.COUNT_DAYS)
    d.update({k: int(v) for k, v in (st.count_days or {}).items() if k in d})
    return d


def _tol(st: WhSettings) -> dict[str, dict]:
    t = {k: dict(v) for k, v in R.TOLERANCE.items()}
    for k, v in (st.tolerance or {}).items():
        if k in t and isinstance(v, dict):
            t[k].update({x: float(v[x]) for x in ("units", "pct") if x in v})
    return t


# ---------------------------------------------------------------- settings
def settings(tenant: str) -> dict:
    with session() as s:
        st = _st(s, tenant)
        return {"name": st.name, "count_days": _days(st), "abc_split": list(st.abc_split or R.ABC_SPLIT), "tolerance": _tol(st),
                "near_expiry_days": st.near_expiry_days, "slow_days": st.slow_days, "dead_days": st.dead_days,
                "count_bins_per_day": st.count_bins_per_day, "food": st.food, "rules": st.rules, "morning_time": st.morning_time,
                "never": list(R.NEVER), "notes": [R.RECORDS_NOTE] + ([R.FOOD_NOTE] if st.food else [])}


def save_settings(tenant: str, **kw: Any) -> dict:
    with session() as s:
        st = _st(s, tenant)
        if "name" in kw:
            st.name = str(kw["name"] or "Godown").strip()[:120]
        if isinstance(kw.get("count_days"), dict):
            cd = _days(st)
            for k, v in kw["count_days"].items():
                n = R.num(v, 1, 730)
                if k in cd and n:
                    cd[k] = int(n)
            st.count_days = cd
        if isinstance(kw.get("abc_split"), (list, tuple)) and len(kw["abc_split"]) == 2:
            a, b = R.num(kw["abc_split"][0], 1, 99), R.num(kw["abc_split"][1], 1, 99.9)
            if not a or not b or a >= b:
                raise WarehouseError("ABC: A ka hissa B se kam hona chahiye, jaise [80, 95].")
            st.abc_split = [a, b]
        if isinstance(kw.get("tolerance"), dict):
            t = _tol(st)
            for k, v in kw["tolerance"].items():
                if k in t and isinstance(v, dict):
                    for x in ("units", "pct"):
                        n = R.num(v.get(x), 0, 1000)
                        if n is not None:
                            t[k][x] = n
            st.tolerance = t
        for k, lo, hi in (("near_expiry_days", 1, 365), ("slow_days", 7, 720), ("dead_days", 14, 1460), ("count_bins_per_day", 1, 200)):
            if k in kw:
                n = R.num(kw[k], lo, hi)
                if n is None:
                    raise WarehouseError(f"{k}: {lo}-{hi}")
                setattr(st, k, int(n))
        if "food" in kw:
            st.food = bool(kw["food"])
        if "rules" in kw:
            st.rules = str(kw["rules"] or "")[:2000]
        if "morning_time" in kw:
            mt = str(kw["morning_time"] or "")
            if not (len(mt) == 5 and mt[2] == ":" and mt[:2].isdigit() and mt[3:].isdigit()):
                raise WarehouseError("Subah ka samay HH:MM jaise 09:00")
            st.morning_time = mt
    return {**settings(tenant), "say": "Godown ke niyam save."}


# ---------------------------------------------------------------- bins
def _bin(s, tenant: str, ref: str) -> WhBin | None:
    ref = str(ref or "").strip()
    if not ref:
        return None
    b = s.get(WhBin, ref)
    if b and b.tenant_id == tenant:
        return b
    scan = R.parse_scan(ref)
    code = scan["code"] if scan["type"] == "bin" else ref.upper().replace(" ", "-")
    return s.scalars(select(WhBin).where(WhBin.tenant_id == tenant, WhBin.code == code)).first()


def _need_bin(s, tenant: str, ref: str) -> WhBin:
    b = _bin(s, tenant, ref)
    if b is None:
        raise WarehouseError(f"Bin '{ref}' nahi mila. Pehle bin banaiye (jaise A-12).")
    return b


def _special_bin(s, tenant: str, code: str, kind: str) -> WhBin:
    b = s.scalars(select(WhBin).where(WhBin.tenant_id == tenant, WhBin.kind == kind, WhBin.active.is_(True))).first()
    if b is None:
        b = s.scalars(select(WhBin).where(WhBin.tenant_id == tenant, WhBin.code == code)).first()
    if b is None:
        b = WhBin(tenant_id=tenant, code=code, zone=code, kind=kind, note="Hoola ne banaya")
        s.add(b)
        s.flush()
    return b


def save_bin(tenant: str, code: str = "", zone: str = "", aisle: str = "", rack: str = "", bin: str = "", kind: str = "",
             capacity: Any = "unset", active: Any = None, note: str = "") -> dict:
    code = str(code or "").strip().upper().replace(" ", "-") or R.make_code(zone, aisle, rack, bin)
    if not R.valid_code(code):
        raise WarehouseError("Bin code aisa ho: A-12 ya B-03-2-4 (zone-aisle-rack-bin; akshar / ank).")
    if kind and kind not in R.BIN_KINDS:
        raise WarehouseError("Bin kind: " + ", ".join(R.BIN_KINDS))
    with session() as s:
        b = _bin(s, tenant, code)
        new = b is None
        if new:
            parts = R.split_code(code)
            b = WhBin(tenant_id=tenant, code=code, **{k: v for k, v in (("zone", zone or parts["zone"]), ("aisle", aisle or parts["aisle"]),
                                                                        ("rack", rack or parts["rack"]), ("bin", bin or parts["bin"]))})
            s.add(b)
        if kind:
            b.kind = kind
        if capacity != "unset":
            b.capacity = None if capacity in (None, "") else R.num(capacity, 0, 1e7)
        if active is not None:
            if not active and _bin_qty(s, b.id) > 0:
                raise WarehouseError(f"{b.code} mein maal hai; pehle khaali kijiye.")
            b.active = bool(active)
        if note:
            b.note = str(note)[:200]
        s.flush()
        v = _bin_view(s, b)
    return {"bin": v, "say": f"Bin {v['code']} {'bana' if new else 'badla'}" + (f", jagah {R.qtxt(v['capacity'])}" if v["capacity"] is not None else "") + "."}


def make_bins(tenant: str, zone: str, aisles: int = 1, racks: int = 1, bins: int = 0, kind: str = "pick", capacity: Any = None) -> dict:
    """Many bins at once: zone A, aisles 1..n, racks 1..m (and bins 1..k) -> A-1-1, A-1-2 ... (max 400)."""
    z = R.make_code(zone)
    a_n, r_n, b_n = int(R.num(aisles, 1, 50) or 1), int(R.num(racks, 1, 50) or 1), int(R.num(bins, 0, 20) or 0)
    if not z:
        raise WarehouseError("Zone ka naam chahiye (jaise A).")
    if a_n * r_n * max(1, b_n) > 400:
        raise WarehouseError("Ek baar mein 400 bin tak.")
    made = 0
    for a in range(1, a_n + 1):
        for r in range(1, r_n + 1):
            for b in range(1, (b_n or 1) + 1):
                code = R.make_code(z, str(a), str(r), str(b) if b_n else "")
                with session() as s:
                    if _bin(s, tenant, code):
                        continue
                save_bin(tenant, code=code, kind=kind, capacity=capacity)
                made += 1
    return {"made": made, "say": f"Zone {z}: {made} naye bin bane."}


def _bin_qty(s, bin_id: str) -> float:
    return R.r3(sum(l.qty for l in s.scalars(select(WhLot).where(WhLot.bin_id == bin_id)).all()))


def _bin_view(s, b: WhBin, lots: bool = False) -> dict:
    rows = s.scalars(select(WhLot).where(WhLot.bin_id == b.id, WhLot.qty > 0)).all()
    used = R.r3(sum(l.qty for l in rows))
    v = {"id": b.id, "code": b.code, "zone": b.zone, "aisle": b.aisle, "rack": b.rack, "bin": b.bin, "kind": b.kind,
         "kind_label": R.BIN_KINDS.get(b.kind, b.kind), "capacity": b.capacity, "used": used,
         "free": None if b.capacity is None else R.r3(max(0.0, b.capacity - used)),
         "full_pct": None if not b.capacity else round(used * 100 / b.capacity), "skus": len({l.sku_id for l in rows}),
         "active": b.active, "note": b.note}
    if lots:
        v["lots"] = [_lot_view(s, l) for l in rows]
    return v


def bins(tenant: str, zone: str = "", kind: str = "") -> list[dict]:
    with session() as s:
        q = select(WhBin).where(WhBin.tenant_id == tenant)
        rows = [b for b in s.scalars(q).all() if (not zone or b.zone == zone.upper()) and (not kind or b.kind == kind)]
        rows.sort(key=lambda b: R.path_key({"zone": b.zone, "aisle": b.aisle, "rack": b.rack, "bin": b.bin}))
        return [_bin_view(s, b) for b in rows]


def bin_view(tenant: str, ref: str) -> dict:
    with session() as s:
        b = _need_bin(s, tenant, ref)
        v = _bin_view(s, b, lots=True)
        mv = s.scalars(select(WhMove).where(WhMove.tenant_id == tenant, WhMove.bin_id == b.id).order_by(WhMove.at.desc()).limit(30)).all()
        v["moves"] = [_move_view(s, m) for m in mv]
    v["say"] = f"{v['code']}: " + (", ".join(f"{l['name']} {R.qtxt(l['qty'])}{(' (' + l['batch'] + ')') if l['batch'] else ''}"
                                             for l in v["lots"]) or "khaali") + "."
    return v


# ---------------------------------------------------------------- SKUs (linked to her stock list)
def _catalog(tenant: str) -> list[dict]:
    """Her stock list (Hoola Deals `hoola_stock`, goods only) in deal.match's shape + the counted quantity."""
    from ..net.deal import StockItem, norm
    try:
        with session() as s:
            rows = s.scalars(select(StockItem).where(StockItem.tenant_id == tenant)).all()
            return [{"id": r.id, "name": r.name, "key": r.key, "aliases": [norm(a) for a in r.aliases or []], "unit": r.unit,
                     "price": r.price, "gst_pct": r.gst_pct, "qty": None if r.qty is None else R.r3(r.qty)}
                    for r in rows if (r.kind or "goods") != "service"]
    except Exception:
        log.exception("stock list read failed")
        return []


def _costs(tenant: str) -> dict[str, float]:
    try:
        from ..thok.service import ThokItem
        with session() as s:
            return {m.key: m.cost for m in s.scalars(select(ThokItem).where(ThokItem.tenant_id == tenant)).all() if m.cost}
    except Exception:
        return {}


def _unit_value(key: str, cat: dict[str, dict], costs: dict[str, float]) -> tuple[float | None, str]:
    if costs.get(key):
        return costs[key], "cost"
    c = cat.get(key)
    if c and c.get("price"):
        return float(c["price"]), "price"
    return None, ""


def _sku(s, tenant: str, ref: str, cat: list[dict] | None = None, create: bool = False, unit: str = "") -> WhSku | None:
    from ..net import deal
    ref = str(ref or "").strip()
    if not ref:
        return None
    k = s.get(WhSku, ref)
    if k and k.tenant_id == tenant:
        return k
    scan = R.parse_scan(ref)
    if scan["type"] == "sku":
        k = s.scalars(select(WhSku).where(WhSku.tenant_id == tenant, WhSku.code == scan["code"])).first()
        if k:
            return k
    k = s.scalars(select(WhSku).where(WhSku.tenant_id == tenant, (WhSku.code == ref.upper()) | (WhSku.barcode == ref))).first()
    if k:
        return k
    key = deal.norm(ref)
    k = s.scalars(select(WhSku).where(WhSku.tenant_id == tenant, WhSku.key == key)).first()
    if k:
        return k
    m = deal.match(cat or [], ref) if cat else None
    if m:
        k = s.scalars(select(WhSku).where(WhSku.tenant_id == tenant, WhSku.key == m["key"])).first()
        if k:
            return k
    mine = s.scalars(select(WhSku).where(WhSku.tenant_id == tenant)).all()
    hit = deal.match([{"key": x.key, "aliases": [deal.norm(x.code)], "id": x.id} for x in mine], ref) if mine else None
    if hit:
        return s.get(WhSku, hit["id"])
    if not create:
        return None
    st = _st(s, tenant)
    name, key_ = (m["name"], m["key"]) if m else (ref[:140], key)
    k = WhSku(tenant_id=tenant, key=key_, name=name, code=_next(st, "sku", "SKU"), unit=(m or {}).get("unit") or unit or "")
    s.add(k)
    s.flush()
    return k


def _need_sku(s, tenant: str, ref: str, cat: list[dict] | None = None) -> WhSku:
    k = _sku(s, tenant, ref, cat)
    if k is None:
        raise WarehouseError(f"'{ref}' ka SKU nahi mila.")
    return k


def save_sku(tenant: str, name: str = "", sku: str = "", code: str = "", barcode: str = "", unit: str = "", track: str = "",
             abc: str = "", home_bin: str = "", note: str = "") -> dict:
    cat = _catalog(tenant)
    with session() as s:
        k = _sku(s, tenant, sku or name, cat, create=bool(name or sku), unit=unit)
        if k is None:
            raise WarehouseError("SKU ka naam chahiye.")
        if code:
            c = str(code).strip().upper()[:30]
            other = s.scalars(select(WhSku).where(WhSku.tenant_id == tenant, WhSku.code == c, WhSku.id != k.id)).first()
            if other:
                raise WarehouseError(f"Code {c} pehle se {other.name} ka hai.")
            k.code = c
        if barcode:
            k.barcode = str(barcode).strip()[:40]
        if unit:
            k.unit = str(unit)[:20]
        if track:
            if track not in R.TRACK:
                raise WarehouseError("track: none | batch | serial")
            k.track = track
        if abc:
            if abc.upper() not in "ABC" or len(abc) != 1:
                raise WarehouseError("ABC: A, B ya C")
            k.abc, k.abc_manual = abc.upper(), True
        if home_bin:
            k.home_bin = _need_bin(s, tenant, home_bin).code
        if note:
            k.note = str(note)[:200]
        sid = k.id
    return {"sku": sku_view(tenant, sid), "say": "SKU save."}


def _sku_row(s, k: WhSku, cat: dict, costs: dict, on: date) -> dict:
    lots = s.scalars(select(WhLot).where(WhLot.sku_id == k.id, WhLot.qty > 0)).all()
    inbins = R.r3(sum(l.qty for l in lots))
    c = cat.get(k.key)
    uv, basis = _unit_value(k.key, cat, costs)
    return {"id": k.id, "code": k.code, "name": k.name, "unit": k.unit or (c or {}).get("unit", ""), "barcode": k.barcode, "track": k.track,
            "abc": k.abc, "abc_manual": k.abc_manual, "last_counted": k.last_counted, "home_bin": k.home_bin, "linked": c is not None,
            "in_bins": inbins, "shared_qty": None if c is None else c.get("qty"),
            "unit_value": uv, "value_basis": basis, "value": None if uv is None else round(uv * inbins, 2),
            "bins": sorted({l.bin_id for l in lots}).__len__()}


def skus(tenant: str, q: str = "") -> list[dict]:
    cat = {c["key"]: c for c in _catalog(tenant)}
    costs = _costs(tenant)
    on = today(tenant)
    w = R.norm(q)
    with session() as s:
        rows = s.scalars(select(WhSku).where(WhSku.tenant_id == tenant).order_by(WhSku.name)).all()
        return [_sku_row(s, k, cat, costs, on) for k in rows if not w or w in k.key or w in k.code.lower()][:500]


def sku_view(tenant: str, ref: str) -> dict:
    cat_l = _catalog(tenant)
    cat = {c["key"]: c for c in cat_l}
    costs = _costs(tenant)
    on = today(tenant)
    with session() as s:
        k = _need_sku(s, tenant, ref, cat_l)
        v = _sku_row(s, k, cat, costs, on)
        v["lots"] = [_lot_view(s, l, on) for l in sorted(s.scalars(select(WhLot).where(WhLot.sku_id == k.id, WhLot.qty > 0)).all(),
                                                          key=lambda l: R.fefo_key({"expiry": l.expiry, "received_on": l.received_on}))]
    return v


# ---------------------------------------------------------------- lots / ledger
def _lot_view(s, l: WhLot, on: date | None = None) -> dict:
    k = s.get(WhSku, l.sku_id)
    b = s.get(WhBin, l.bin_id)
    v = {"id": l.id, "sku_id": l.sku_id, "sku": k.code if k else "", "name": k.name if k else "", "unit": k.unit if k else "",
         "bin": b.code if b else "", "bin_kind": b.kind if b else "", "batch": l.batch, "expiry": l.expiry, "mfg": l.mfg,
         "qty": R.r3(l.qty), "serials": list(l.serials or [])[:200], "status": l.status, "received_on": l.received_on}
    if on:
        v["expiry_state"] = R.expiry_state(l.expiry, on)
    return v


def _find_lot(s, tenant: str, sku_id: str, bin_id: str, batch: str = "", expiry: str = "") -> WhLot | None:
    q = select(WhLot).where(WhLot.tenant_id == tenant, WhLot.sku_id == sku_id, WhLot.bin_id == bin_id, WhLot.batch == (batch or ""))
    rows = s.scalars(q).all()
    if expiry:
        rows = [r for r in rows if r.expiry in ("", expiry)]
    return rows[0] if rows else None


def _add(s, tenant: str, sku: WhSku, b: WhBin, qty: float, kind: str, ref: str, by: str, on: date, batch: str = "", expiry: str = "",
         mfg: str = "", serials: list | None = None, grn_id: str = "", reason: str = "", note: str = "", synced: bool = False,
         received_on: str = "") -> WhLot:
    lot = _find_lot(s, tenant, sku.id, b.id, batch, expiry)
    if lot is None:
        lot = WhLot(tenant_id=tenant, sku_id=sku.id, bin_id=b.id, batch=batch or "", expiry=expiry or "", mfg=mfg or "", qty=0.0,
                    serials=[], received_on=received_on or on.isoformat(), grn_id=grn_id,
                    status="hold" if b.kind in ("quarantine", "damage") else "ok")
        s.add(lot)
        s.flush()
    elif expiry and not lot.expiry:
        lot.expiry = expiry
    lot.qty = R.r3(lot.qty + qty)
    if serials:
        lot.serials = sorted(set(lot.serials or []) | set(serials))
    lot.updated_at = _now()
    s.add(WhMove(tenant_id=tenant, day=on.isoformat(), kind=kind, sku_id=sku.id, bin_id=b.id, lot_id=lot.id, batch=lot.batch,
                 qty=R.r3(qty), ref=ref, by=by, reason=reason, note=note[:240], synced=synced))
    return lot


def _take(s, tenant: str, lot: WhLot, qty: float, kind: str, ref: str, by: str, on: date, serials: list | None = None, reason: str = "",
          note: str = "", synced: bool = False) -> None:
    lot.qty = R.r3(max(0.0, lot.qty - qty))
    if serials:
        lot.serials = [x for x in (lot.serials or []) if x not in set(serials)]
    lot.updated_at = _now()
    s.add(WhMove(tenant_id=tenant, day=on.isoformat(), kind=kind, sku_id=lot.sku_id, bin_id=lot.bin_id, lot_id=lot.id, batch=lot.batch,
                 qty=-R.r3(qty), ref=ref, by=by, reason=reason, note=note[:240], synced=synced))


def _move_view(s, m: WhMove) -> dict:
    k = s.get(WhSku, m.sku_id)
    b = s.get(WhBin, m.bin_id)
    return {"at": m.at.isoformat() if m.at else "", "day": m.day, "kind": m.kind, "sku": k.code if k else "", "name": k.name if k else "",
            "bin": b.code if b else "", "batch": m.batch, "qty": m.qty, "ref": m.ref, "by": m.by, "reason": m.reason, "note": m.note,
            "synced": m.synced}


def ledger(tenant: str, sku: str = "", bin: str = "", days: int = 30, limit: int = 300) -> dict:
    on = today(tenant)
    since = (on - timedelta(days=max(1, min(int(days or 30), 3650)))).isoformat()
    cat = _catalog(tenant)
    with session() as s:
        q = select(WhMove).where(WhMove.tenant_id == tenant, WhMove.day >= since)
        if sku:
            q = q.where(WhMove.sku_id == _need_sku(s, tenant, sku, cat).id)
        if bin:
            q = q.where(WhMove.bin_id == _need_bin(s, tenant, bin).id)
        rows = s.scalars(q.order_by(WhMove.at.desc()).limit(max(1, min(limit, 2000)))).all()
        out = [_move_view(s, m) for m in rows]
    sums: dict[str, float] = {}
    for m in out:
        sums[m["kind"]] = R.r3(sums.get(m["kind"], 0.0) + m["qty"])
    return {"moves": out, "totals": sums, "since": since, "note": R.RECORDS_NOTE}


def _sync(tenant: str, changes: dict[str, float]) -> list[str]:
    """Change the shared stock count (hoola_stock) for linked SKUs. Returns names that are not on her stock list."""
    from ..net import deal
    if not changes:
        return []
    cat = {c["key"]: c for c in _catalog(tenant)}
    items, missing = [], []
    for key, d in changes.items():
        if not d:
            continue
        c = cat.get(key)
        if c is None:
            missing.append(key)
        else:
            items.append({"name": c["name"], "add": R.r3(d)})
    if items:
        try:
            deal.set_stock(tenant, items)
        except Exception:
            log.exception("shared stock sync failed")
    return missing


def opening(tenant: str, lines: list | None = None, text: str = "", bin: str = "", by: str = "Owner") -> dict:
    """Stock already lying in bins (first day): goes into the bins; the shared count is NOT touched (it already has it)."""
    rows = list(lines or []) or R.parse_lines(text)
    if not rows:
        raise WarehouseError("Lines chahiye: [{item, qty, bin, batch, expiry}] ya 'atta 10 bori' A-12 ke saath.")
    cat = _catalog(tenant)
    on = today(tenant)
    n = 0
    with _LOCK, session() as s:
        for x in rows:
            q = R.num(x.get("qty"), 0.001, 1e7)
            if q is None:
                raise WarehouseError(f"{x.get('item')}: maatra galat")
            k = _sku(s, tenant, str(x.get("item") or x.get("sku") or ""), cat, create=True, unit=str(x.get("unit") or ""))
            if k is None:
                raise WarehouseError("Item ka naam chahiye.")
            b = _need_bin(s, tenant, str(x.get("bin") or bin))
            exp = R.iso(R.parse_date(x.get("expiry")))
            _add(s, tenant, k, b, q, "opening", "OPENING", by, on, str(x.get("batch") or "")[:40], exp, serials=_serials(x))
            n += 1
    return {"lines": n, "say": f"{n} line opening stock binon mein daali (stock list ki ginti nahi badli)."}


def _serials(x: dict) -> list[str]:
    raw = x.get("serials") or []
    if isinstance(raw, str):
        raw = [p for p in raw.replace(";", ",").split(",")]
    return [str(v).strip()[:40] for v in raw if str(v).strip()][:2000]


# ---------------------------------------------------------------- GRN (inward) + putaway
def _bins_for_plan(s, tenant: str) -> list[dict]:
    rows = s.scalars(select(WhBin).where(WhBin.tenant_id == tenant, WhBin.active.is_(True))).all()
    rows.sort(key=lambda b: R.path_key({"zone": b.zone, "aisle": b.aisle, "rack": b.rack, "bin": b.bin}))
    out = []
    for i, b in enumerate(rows):
        skus: dict[str, list] = {}
        used = 0.0
        for l in s.scalars(select(WhLot).where(WhLot.bin_id == b.id, WhLot.qty > 0)).all():
            skus.setdefault(l.sku_id, []).append(l.batch)
            used += l.qty
        out.append({"code": b.code, "kind": b.kind, "capacity": b.capacity, "used": used, "skus": skus, "rank": i, "active": b.active})
    return out


def _fast(s, tenant: str, sku: WhSku, on: date) -> bool:
    if sku.abc == "A":
        return True
    since = (on - timedelta(days=30)).isoformat()
    n = len(s.scalars(select(WhMove.id).where(WhMove.tenant_id == tenant, WhMove.sku_id == sku.id, WhMove.kind == "pick",
                                              WhMove.day >= since)).all())
    return n >= 8


def _grn_rows(tenant: str, file_id: str) -> list[dict]:
    """A GRN / challan / PO sheet (CSV / Excel): item, qty, batch, expiry, mfg, serial columns found by name."""
    from ..analyst.service import _load_file, _rows
    name, data = _load_file(tenant, file_id)
    if not name.lower().endswith((".csv", ".xlsx", ".xls", ".txt")):
        raise WarehouseError("Photo / PDF ho to pehle file_read se padhiye aur lines bhejiye; sheet (CSV / Excel) yahan seedha chalegi.")
    rows = _rows(name, data)
    cols: dict[str, int] = {}
    words = {"item": ("item", "name", "product", "description", "maal", "particulars", "sku"), "qty": ("qty", "quantity", "maatra", "nos", "received"),
             "batch": ("batch", "lot"), "expiry": ("expiry", "exp", "best before", "use by"), "mfg": ("mfg", "manufactur"),
             "serial": ("serial", "imei", "sr no")}
    head = 0
    for i, r in enumerate(rows[:15]):
        h = [str(c or "").strip().lower() for c in r]
        found = {}
        for k, ws in words.items():
            for j, c in enumerate(h):
                if c and any(c.startswith(w) or w in c for w in ws) and j not in found.values():
                    found[k] = j
                    break
        if "item" in found and "qty" in found:
            cols, head = found, i
            break
    if not cols:
        raise WarehouseError("Sheet mein 'item' aur 'qty' wale column nahi mile.")
    out = []
    for r in rows[head + 1:]:
        def g(k):
            j = cols.get(k)
            return r[j] if j is not None and j < len(r) else None
        if not g("item") or R.num(g("qty"), 0.001, 1e7) is None:
            continue
        out.append({"item": str(g("item")).strip(), "qty": R.num(g("qty")), "batch": str(g("batch") or "").strip(),
                    "expiry": str(g("expiry") or "").strip()[:10], "mfg": str(g("mfg") or "").strip()[:10],
                    "serials": [str(g("serial")).strip()] if g("serial") else []})
    return out


def grn(tenant: str, lines: list | None = None, text: str = "", file_id: str = "", supplier: str = "", doc: str = "",
        source: str = "", purchase: str = "", expected: list | None = None, by: str = "Owner", conv: str = "") -> dict:
    """Goods received: into the receiving bin (damaged -> damage bin, expired -> quarantine), checks, putaway suggestions."""
    rows: list[dict] = []
    sync = True
    if purchase:
        from ..thok.service import ThokParty, ThokPurchase
        with session() as s:
            p = s.get(ThokPurchase, purchase)
            if p is None or p.tenant_id != tenant:
                raise WarehouseError("Thok purchase nahi mili.")
            import json as _json
            rows = [{"item": x["item"], "qty": x["qty"]} for x in _json.loads(p.lines or "[]")]
            sp = s.get(ThokParty, p.supplier_id)
            supplier = supplier or (sp.name if sp else "")
            doc = doc or p.bill_no
        source, sync = "thok_purchase", False          # Thok already added it to the shared stock count
    elif file_id and not lines and not text:
        rows, source = _grn_rows(tenant, file_id), source or "file"
    else:
        rows = list(lines or []) or R.parse_lines(text)
    if not rows:
        raise WarehouseError("Kya aaya? Lines bhejiye: [{item, qty, batch, expiry}] ya 'atta 50 bori'. Challan photo ho to pehle file_read.")
    source = source or ("photo" if file_id else "challan")
    exp_map: dict[str, float] = {}
    for e in expected or []:
        if isinstance(e, dict) and e.get("item"):
            exp_map[R.norm(e["item"])] = float(R.num(e.get("qty"), 0, 1e7) or 0)
    cat = _catalog(tenant)
    on = today(tenant)
    notes: list[str] = []
    out_lines: list[dict] = []
    sync_add: dict[str, float] = {}
    with _LOCK, session() as s:
        st = _st(s, tenant)
        number = _next(st, "grn", "GRN")
        g = WhGrn(tenant_id=tenant, number=number, supplier=str(supplier)[:140], doc=str(doc)[:60], source=source[:16],
                  source_ref=purchase, sync=sync, file_id=file_id, by=by)
        s.add(g)
        s.flush()
        rcv = _special_bin(s, tenant, RCV_CODE, "receiving")
        all_serials = {x for l in s.scalars(select(WhLot).where(WhLot.tenant_id == tenant)).all() for x in (l.serials or [])}
        for x in rows:
            name = str(x.get("item") or x.get("name") or x.get("sku") or "").strip()
            q = R.num(x.get("qty"), 0.001, 1e7)
            if not name or q is None:
                raise WarehouseError(f"'{name or x}': naam aur maatra chahiye.")
            k = _sku(s, tenant, name, cat, create=True, unit=str(x.get("unit") or ""))
            linked = any(c["key"] == k.key for c in cat)
            batch = str(x.get("batch") or "").strip()[:40]
            exp_d = R.parse_date(x.get("expiry"))
            exp = R.iso(exp_d)
            mfg = R.iso(R.parse_date(x.get("mfg")))
            serials = _serials(x)
            dmg = R.num(x.get("damaged"), 0, q) or 0.0
            ln: dict[str, Any] = {"sku_id": k.id, "sku": k.code, "name": k.name, "unit": k.unit, "qty": q, "damaged": dmg, "batch": batch,
                                  "expiry": exp, "mfg": mfg, "serials": len(serials), "linked": linked, "notes": []}
            if x.get("expiry") and not exp_d:
                ln["notes"].append(f"expiry '{x.get('expiry')}' samajh nahi aayi: label dekh kar likhiye")
            if k.track == "batch" and not batch:
                ln["notes"].append("batch number nahi likha")
            if k.track == "serial":
                if len(serials) != int(q):
                    ln["notes"].append(f"serial {len(serials)} mile, maatra {R.qtxt(q)}")
                dup = sorted(set(serials) & all_serials)
                if dup:
                    raise WarehouseError(f"{k.name}: serial {', '.join(dup[:5])} pehle se godown mein hai. Dobara mat chadhaiye; jaanch kijiye.")
                all_serials |= set(serials)
            state = R.expiry_state(exp, on, st.near_expiry_days)
            left = R.shelf_left_pct(mfg, exp, on)
            good = R.r3(q - dmg)
            if state == "expired":
                target = _special_bin(s, tenant, QTN_CODE, "quarantine")
                ln["notes"].append(f"EXPIRED ({exp}) aaya: quarantine bin {target.code} mein; supplier ko lautaiye")
                ln["to_bin"] = target.code
            else:
                target = rcv
                if state == "near":
                    ln["notes"].append(f"expiry paas hai ({exp})")
                if left is not None and left < 30:
                    ln["notes"].append(f"sirf {left:g}% shelf life bachi hai")
            if good > 0:
                _add(s, tenant, k, target, good, "grn", number, by, on, batch, exp, mfg, serials, g.id, synced=sync and linked)
            if dmg > 0:
                db = _special_bin(s, tenant, DMG_CODE, "damage")
                _add(s, tenant, k, db, dmg, "grn", number, by, on, batch, exp, mfg, None, g.id, reason="damaged",
                     note="toota aaya", synced=sync and linked)
                ln["notes"].append(f"{R.qtxt(dmg)} toota: {db.code} bin mein (write-off sirf aapke card se)")
            want = exp_map.pop(R.norm(name), None) if exp_map else None
            if want is not None and abs(want - q) > 1e-9:
                ln["expected"] = want
                ln["notes"].append(f"PO / challan mein {R.qtxt(want)} tha, aaya {R.qtxt(q)}")
            if not linked:
                ln["notes"].append("stock list (Hoola Deals) mein nahi: daam wahan jodiye")
            if sync and linked:
                sync_add[k.key] = sync_add.get(k.key, 0.0) + q
            if target.kind == "receiving" and good > 0:
                ln["putaway"] = R.putaway_plan(good, _bins_for_plan(s, tenant), k.id, batch, _fast(s, tenant, k, on))
            out_lines.append(ln)
        for item, want in exp_map.items():
            notes.append(f"{item}: {R.qtxt(want)} aana tha, aaya hi nahi")
        short = [l for l in out_lines if l.get("expected") is not None and l["qty"] < l["expected"]] or exp_map
        g.lines, g.notes = out_lines, notes
        g.status = "received" if any(l.get("putaway") for l in out_lines) else "putaway"
        gid = g.id
    missing = _sync(tenant, sync_add)
    v = grn_view(tenant, gid)
    if short:
        sh = [f"{l['name']} {R.qtxt(l['expected'] - l['qty'])} kam" for l in out_lines if l.get("expected") is not None and l["qty"] < l["expected"]]
        sh += [f"{k} {R.qtxt(q)} nahi aaya" for k, q in exp_map.items()]
        v["draft"] = {"to": supplier, "text": f"Namaste, {doc or 'aapke challan'} ka maal {on.strftime('%d-%m-%Y')} ko mila. Kam aaya: "
                      + "; ".join(sh) + ". Kripya bhejiye ya credit / debit note dijiye. - " + (settings(tenant)["name"] or "")}
    say = f"{v['number']}: {len(out_lines)} item aaye" + (f" ({supplier})" if supplier else "") + "."
    if any(l.get("putaway") for l in out_lines):
        say += " Kahan rakhna hai, sujhaav card par: 'Haan, aise rakho' ya bin badliye."
    if not sync:
        say += " (Thok purchase se: stock list ki ginti pehle hi badh chuki.)"
    if missing:
        say += f" {len(missing)} item stock list par nahi."
    v["say"] = say
    _publish(tenant, "warehouse_grn", {"grn": v, "say": say}, conv)
    return v


def grn_view(tenant: str, ref: str) -> dict:
    with session() as s:
        g = s.get(WhGrn, ref)
        if g is None or g.tenant_id != tenant:
            g = s.scalars(select(WhGrn).where(WhGrn.tenant_id == tenant, WhGrn.number == str(ref).upper())).first()
        if g is None:
            raise WarehouseError("GRN nahi mila.")
        return {"id": g.id, "number": g.number, "supplier": g.supplier, "doc": g.doc, "source": g.source, "sync": g.sync, "status": g.status,
                "lines": list(g.lines or []), "notes": list(g.notes or []), "day": g.created_at.date().isoformat() if g.created_at else "",
                "by": g.by}


def grns(tenant: str, limit: int = 40) -> list[dict]:
    with session() as s:
        ids = s.scalars(select(WhGrn.id).where(WhGrn.tenant_id == tenant).order_by(WhGrn.created_at.desc()).limit(limit)).all()
    return [grn_view(tenant, i) for i in ids]


def _move_qty(s, tenant: str, k: WhSku, src: WhBin, dst: WhBin, qty: float, batch: str, ref: str, kind: str, by: str, on: date,
              force: bool = False, serials: list | None = None) -> float:
    if src.id == dst.id:
        raise WarehouseError("Same bin.")
    if dst.kind == "dispatch" and kind == "putaway":
        raise WarehouseError("Dispatch bin mein putaway nahi.")
    if dst.capacity is not None and not force:
        free = dst.capacity - _bin_qty(s, dst.id)
        if qty > free + 1e-9:
            raise WarehouseError(f"{dst.code} mein jagah {R.qtxt(max(0, free))} hai, {R.qtxt(qty)} nahi aayega. Doosra bin ya force.")
    lots = [l for l in s.scalars(select(WhLot).where(WhLot.tenant_id == tenant, WhLot.sku_id == k.id, WhLot.bin_id == src.id, WhLot.qty > 0)).all()
            if not batch or l.batch == batch]
    lots.sort(key=lambda l: R.fefo_key({"expiry": l.expiry, "received_on": l.received_on}))
    have = sum(l.qty for l in lots)
    if have + 1e-9 < qty:
        raise WarehouseError(f"{src.code} mein {k.name} {R.qtxt(have)} hi hai.")
    left = qty
    for l in lots:
        if left <= 0:
            break
        take = min(l.qty, left)
        ser = list(serials or [])[: int(take)] if serials else (list(l.serials or [])[: int(take)] if l.serials else None)
        _take(s, tenant, l, take, kind, ref, by, on, ser)
        _add(s, tenant, k, dst, take, kind, ref, by, on, l.batch, l.expiry, l.mfg, ser, l.grn_id, received_on=l.received_on)
        left = R.r3(left - take)
    return qty


def putaway(tenant: str, grn: str = "", lines: list | None = None, force: bool = False, by: str = "Owner", conv: str = "") -> dict:
    """Move received stock from the receiving bin into bins: her own lines, or (no lines) Hoola's suggestion on the GRN card."""
    cat = _catalog(tenant)
    on = today(tenant)
    moved = []
    with _LOCK, session() as s:
        g = None
        if grn:
            g = s.get(WhGrn, grn) or s.scalars(select(WhGrn).where(WhGrn.tenant_id == tenant, WhGrn.number == str(grn).upper())).first()
            if g is None or g.tenant_id != tenant:
                raise WarehouseError("GRN nahi mila.")
        todo = []
        if lines:
            for x in lines:
                todo.append((str(x.get("item") or x.get("sku") or ""), str(x.get("from_bin") or ""), str(x.get("to_bin") or x.get("bin") or ""),
                             R.num(x.get("qty"), 0.001, 1e7), str(x.get("batch") or "")))
        elif g is not None:
            for ln in g.lines or []:
                for p in ln.get("putaway") or []:
                    if p.get("bin"):
                        todo.append((ln["sku_id"], "", p["bin"], p["qty"], ln.get("batch") or ""))
        if not todo:
            raise WarehouseError("Kya kahan rakhna hai? lines: [{item, to_bin, qty}] ya GRN.")
        rcv = _special_bin(s, tenant, RCV_CODE, "receiving")
        ref = g.number if g else "PUTAWAY"
        for item, frm, to, q, batch in todo:
            k = _need_sku(s, tenant, item, cat)
            src = _need_bin(s, tenant, frm) if frm else rcv
            dst = _need_bin(s, tenant, to)
            if q is None:
                q = sum(l.qty for l in s.scalars(select(WhLot).where(WhLot.sku_id == k.id, WhLot.bin_id == src.id)).all() if not batch or l.batch == batch)
            if q <= 0:
                continue
            _move_qty(s, tenant, k, src, dst, q, batch, ref, "putaway", by, on, force)
            moved.append({"name": k.name, "qty": R.r3(q), "bin": dst.code})
        if g is not None:
            left = sum(l.qty for l in s.scalars(select(WhLot).where(WhLot.grn_id == g.id, WhLot.bin_id == rcv.id)).all())
            g.status = "putaway" if left <= 0 else "received"
            gid = g.id
    say = "Rakh diya: " + "; ".join(f"{m['name']} {R.qtxt(m['qty'])} -> {m['bin']}" for m in moved) + "."
    if grn:
        v = grn_view(tenant, gid)
        _publish(tenant, "warehouse_grn", {"grn": v, "say": say}, conv)
    return {"moved": moved, "say": say}


def move(tenant: str, item: str, from_bin: str, to_bin: str, qty: Any, batch: str = "", force: bool = False, by: str = "Owner") -> dict:
    cat = _catalog(tenant)
    on = today(tenant)
    q = R.num(qty, 0.001, 1e7)
    if q is None:
        raise WarehouseError("Maatra chahiye.")
    with _LOCK, session() as s:
        k = _need_sku(s, tenant, item, cat)
        src, dst = _need_bin(s, tenant, from_bin), _need_bin(s, tenant, to_bin)
        _move_qty(s, tenant, k, src, dst, q, batch, "MOVE", "move", by, on, force)
        name, a, b = k.name, src.code, dst.code
    return {"say": f"{name} {R.qtxt(q)}: {a} -> {b}."}


# ---------------------------------------------------------------- pick lists
def _order_lines(tenant: str, source: str, refs: list[str]) -> tuple[list[dict], list[dict], list[str]]:
    """-> (lines [{item, qty, order}], refs [{kind, id, number, party}], notes)."""
    lines, out_refs, notes = [], [], []
    if source == "deal":
        from ..net.deal import Deal
        with session() as s:
            q = select(Deal).where(Deal.tenant_id == tenant, Deal.role == "seller", Deal.state.in_(("accepted", "packing")))
            rows = s.scalars(q).all()
            if refs:
                want = {str(r).upper() for r in refs}
                rows = [d for d in rows if d.id in refs or (d.number or "").upper() in want]
            for d in rows:
                if (d.ask or {}).get("service"):
                    continue
                num = d.number or d.id
                out_refs.append({"kind": "deal", "id": d.id, "number": num, "party": d.title or d.peer})
                for ln in (d.quote or {}).get("lines") or []:
                    if float(ln.get("qty") or 0) > 0 and ln.get("status") not in ("not_found", "out"):
                        lines.append({"item": ln["item"], "qty": float(ln["qty"]), "order": num})
        if not out_refs:
            notes.append("Koi pakka (accepted) Hoola Deals order nahi mila.")
    elif source == "thok":
        from ..thok.service import ThokOrder, ThokParty
        import json as _json
        with session() as s:
            rows = s.scalars(select(ThokOrder).where(ThokOrder.tenant_id == tenant, ThokOrder.status == "billed")).all()
            if refs:
                want = {str(r).upper() for r in refs}
                rows = [o for o in rows if o.id in refs or (o.number or "").upper() in want]
            else:
                rows = rows[-20:]
            for o in rows:
                p = s.get(ThokParty, o.party_id)
                out_refs.append({"kind": "thok", "id": o.id, "number": o.number, "party": p.name if p else ""})
                for ln in _json.loads(o.lines or "[]"):
                    lines.append({"item": ln["item"], "qty": float(ln.get("qty") or 0), "order": o.number})
        if not out_refs:
            notes.append("Koi Thok bill nahi mila.")
    return lines, out_refs, notes


def _held(s, tenant: str, exclude: str = "") -> dict[str, float]:
    """Quantity already promised to open pick lists, per lot."""
    held: dict[str, float] = {}
    for p in s.scalars(select(WhPick).where(WhPick.tenant_id == tenant, WhPick.status == "open")).all():
        if p.id == exclude:
            continue
        for t in p.tasks or []:
            if not t.get("done"):
                held[t["lot_id"]] = held.get(t["lot_id"], 0.0) + float(t["qty"])
    return held


def pick_list(tenant: str, source: str = "list", refs: list | None = None, lines: list | None = None, text: str = "", party: str = "",
              by: str = "Owner", conv: str = "") -> dict:
    """Pick list with a walking path. source list (her words / lines) | deal (Hoola Deals accepted orders) | thok (billed
    Thok bills). Many orders = one wave: lines merged per SKU, each order's share kept for sorting at dispatch."""
    refs = [str(r) for r in (refs or []) if str(r).strip()]
    notes: list[str] = []
    if source in ("deal", "thok"):
        raw, out_refs, notes = _order_lines(tenant, source, refs)
        sync = False                   # Thok billing / Deals handover change the shared count themselves
    elif source == "list":
        raw = [{"item": x.get("item") or x.get("name") or x.get("sku"), "qty": x.get("qty"), "order": party or "list"}
               for x in (lines or [])] or [{**x, "order": party or "list"} for x in R.parse_lines(text)]
        out_refs = [{"kind": "list", "id": "", "number": "", "party": party}] if party else []
        sync = True
    else:
        raise WarehouseError("source: list | deal | thok")
    if not raw:
        raise WarehouseError("Pick ke liye koi line nahi. " + " ".join(notes))
    cat = _catalog(tenant)
    on = today(tenant)
    with _LOCK, session() as s:
        if out_refs and source != "list":
            open_refs = {(r.get("kind"), r.get("id")) for p in s.scalars(select(WhPick).where(WhPick.tenant_id == tenant, WhPick.status == "open")).all()
                         for r in p.refs or []}
            dup = [r["number"] for r in out_refs if (r["kind"], r["id"]) in open_refs]
            if dup:
                raise WarehouseError(f"In orders ki pick list pehle se khuli hai: {', '.join(dup)}. Wo poori / cancel kijiye.")
        merged: dict[str, dict] = {}
        for x in raw:
            q = R.num(x.get("qty"), 0.001, 1e7)
            if q is None:
                continue
            k = _sku(s, tenant, str(x.get("item") or ""), cat)
            if k is None:
                notes.append(f"'{x.get('item')}' godown mein nahi (SKU nahi): chhoota")
                merged.setdefault("?" + str(x.get("item")), {"sku_id": "", "name": str(x.get("item")), "unit": "", "qty": q, "orders": {},
                                                             "short": q, "note": "SKU nahi"})
                continue
            m = merged.setdefault(k.id, {"sku_id": k.id, "name": k.name, "unit": k.unit, "qty": 0.0, "orders": {}, "short": 0.0, "note": "",
                                         "track": k.track})
            m["qty"] = R.r3(m["qty"] + q)
            o = str(x.get("order") or "")
            m["orders"][o] = R.r3(m["orders"].get(o, 0.0) + q)
        held = _held(s, tenant)
        tasks = []
        for m in merged.values():
            if not m["sku_id"]:
                continue
            lots = []
            for l in s.scalars(select(WhLot).where(WhLot.tenant_id == tenant, WhLot.sku_id == m["sku_id"], WhLot.qty > 0)).all():
                b = s.get(WhBin, l.bin_id)
                if b is None or not b.active or b.kind not in R.PICKABLE or l.status != "ok":
                    continue
                free = R.r3(l.qty - held.get(l.id, 0.0))
                if free <= 0:
                    continue
                if R.expiry_state(l.expiry, on) == "expired":
                    notes.append(f"{m['name']} batch {l.batch or '-'} ({b.code}) EXPIRED: pick mein nahi liya; quarantine mein daaliye")
                    continue
                loc = {"zone": b.zone, "aisle": b.aisle, "rack": b.rack, "bin": b.bin}
                kind_rank = {"pick": 0, "bulk": 1, "receiving": 2}.get(b.kind, 3)
                lots.append((R.fefo_key({"expiry": l.expiry, "received_on": l.received_on}), kind_rank, R.path_key(loc), l, b, free))
            lots.sort(key=lambda x: (x[0][0], x[0][1], x[1], x[2]))
            left = m["qty"]
            for _, _, pk, l, b, free in lots:
                if left <= 0:
                    break
                take = R.r3(min(free, left))
                tasks.append({"bin": b.code, "bin_id": b.id, "path": list(map(str, pk)), "lot_id": l.id, "sku_id": m["sku_id"], "name": m["name"],
                              "unit": m["unit"], "batch": l.batch, "expiry": l.expiry, "qty": take, "picked": None, "done": False,
                              "serial": m.get("track") == "serial", "_pk": pk})
                left = R.r3(left - take)
            if left > 0:
                m["short"] = left
                m["note"] = f"{R.qtxt(left)} kam hai (godown mein utna free maal nahi)"
        tasks.sort(key=lambda t: t.pop("_pk"))
        for i, t in enumerate(tasks, 1):
            t["n"] = i
            t.pop("path", None)
        st = _st(s, tenant)
        number = _next(st, "pick", "PL")
        wave = len({o for m in merged.values() for o in m["orders"]}) > 1
        p = WhPick(tenant_id=tenant, number=number, source="wave" if wave and source != "list" else source, refs=out_refs, sync=sync,
                   lines=[{k: v for k, v in m.items() if k != "track"} for m in merged.values()], tasks=tasks, notes=notes, picker="")
        s.add(p)
        s.flush()
        pid = p.id
    v = pick_view(tenant, pid)
    short = [l for l in v["lines"] if l["short"] > 0]
    say = f"{v['number']}: {len(v['tasks'])} jagah se uthana, {len(v['lines'])} item" + (" (wave: kai order ek saath)" if v["wave"] else "")
    say += f". Raasta: {' -> '.join(dict.fromkeys(t['bin'] for t in v['tasks']))}." if v["tasks"] else "."
    if short:
        say += " Kam: " + ", ".join(f"{l['name']} {R.qtxt(l['short'])}" for l in short) + "."
    v["say"] = say
    _publish(tenant, "warehouse_pick", {"pick": v, "say": say}, conv)
    return v


def _pick(s, tenant: str, ref: str) -> WhPick:
    p = s.get(WhPick, ref)
    if p is None or p.tenant_id != tenant:
        p = s.scalars(select(WhPick).where(WhPick.tenant_id == tenant, WhPick.number == str(ref).upper())).first()
    if p is None:
        raise WarehouseError("Pick list nahi mili.")
    return p


def pick_view(tenant: str, ref: str) -> dict:
    with session() as s:
        p = _pick(s, tenant, ref)
        orders = sorted({o for l in p.lines or [] for o in (l.get("orders") or {})})
        return {"id": p.id, "number": p.number, "source": p.source, "wave": len(orders) > 1, "orders": orders, "refs": list(p.refs or []),
                "sync": p.sync, "lines": list(p.lines or []), "tasks": list(p.tasks or []), "status": p.status, "picker": p.picker,
                "notes": list(p.notes or []), "day": p.created_at.date().isoformat() if p.created_at else ""}


def picks(tenant: str, status: str = "", limit: int = 40) -> list[dict]:
    with session() as s:
        q = select(WhPick.id).where(WhPick.tenant_id == tenant)
        if status:
            q = q.where(WhPick.status == status)
        ids = s.scalars(q.order_by(WhPick.created_at.desc()).limit(limit)).all()
    return [pick_view(tenant, i) for i in ids]


def pick_confirm(tenant: str, pick: str, picked: list | None = None, all_done: bool = False, finish: bool = False, picker: str = "",
                 by: str = "Owner", conv: str = "") -> dict:
    """The picker reports: picked [{n, qty, serials}] (task numbers) or all_done. Less than planned = short pick: that bin gets a
    spot count (blind). finish = close the list; tasks not reported count as not picked (short)."""
    on = today(tenant)
    sync_take: dict[str, float] = {}
    spot: list[tuple[str, str]] = []
    with _LOCK, session() as s:
        p = _pick(s, tenant, pick)
        if p.status != "open":
            raise WarehouseError(f"{p.number} pehle se {p.status}.")
        tasks = [dict(t) for t in p.tasks or []]
        by_n = {int(x.get("n")): x for x in (picked or []) if isinstance(x, dict) and R.num(x.get("n"), 1, 10000)}
        for t in tasks:
            if t.get("done"):
                continue
            rep = by_n.get(int(t["n"]))
            if rep is None and not all_done:
                continue
            want = float(t["qty"])
            got = want if rep is None or rep.get("qty") in (None, "") else float(R.num(rep.get("qty"), 0, 1e7) or 0.0)
            lot = s.get(WhLot, t["lot_id"])
            have = lot.qty if lot else 0.0
            if got > have + 1e-9:
                got = have
            serials = _serials(rep or {}) if t.get("serial") else None
            if t.get("serial") and serials:
                bad = [x for x in serials if lot is None or x not in (lot.serials or [])]
                if bad:
                    raise WarehouseError(f"Task {t['n']}: serial {', '.join(bad[:5])} is bin ke record mein nahi.")
                got = float(len(serials))
            k = s.get(WhSku, t["sku_id"])
            if got > 0 and lot is not None:
                _take(s, tenant, lot, got, "pick", p.number, by, on, serials, synced=p.sync)
                if p.sync and k:
                    sync_take[k.key] = sync_take.get(k.key, 0.0) - got
            t["picked"], t["done"] = R.r3(got), True
            if got + 1e-9 < want:
                t["short"] = R.r3(want - got)
                spot.append((t["bin_id"], t["sku_id"]))
        if finish:
            for t in tasks:
                if not t.get("done"):
                    t["picked"], t["done"], t["short"] = 0.0, True, t["qty"]
        p.tasks = tasks
        lines = [dict(l) for l in p.lines or []]
        for l in lines:
            if l.get("sku_id"):
                ts = [t for t in tasks if t["sku_id"] == l["sku_id"]]
                miss = sum(t.get("short", 0.0) for t in ts if t.get("done"))
                planned_short = float(l.get("short") or 0.0)
                l["picked"] = R.r3(sum(float(t.get("picked") or 0) for t in ts if t.get("done")))
                l["short_total"] = R.r3(planned_short + miss)
        p.lines = lines
        if picker:
            p.picker = str(picker)[:80]
        if all(t.get("done") for t in tasks):
            p.status, p.done_at = "done", _now()
        pid = p.id
    if sync_take:
        _sync(tenant, sync_take)
    spots = []
    for bin_id, sku_id in dict.fromkeys(spot):
        try:
            spots.append(count_plan(tenant, bins=[bin_id], kind="spot", reason="pick mein kam mila", conv=conv)["number"])
        except WarehouseError:
            pass
    v = pick_view(tenant, pid)
    short = [l for l in v["lines"] if (l.get("short_total") or 0) > 0]
    say = f"{v['number']}: " + ("poori uth gayi." if v["status"] == "done" else "kuch kaam baaki.")
    if short:
        say += " Kam mila: " + ", ".join(f"{l['name']} {R.qtxt(l['short_total'])}" for l in short) + "."
    if spots:
        say += f" Bin dobara ginne ka kaam bana: {', '.join(spots)}."
    v["say"] = say
    _publish(tenant, "warehouse_pick", {"pick": v, "say": say}, conv)
    return v


def pick_cancel(tenant: str, pick: str, reason: str = "") -> dict:
    with session() as s:
        p = _pick(s, tenant, pick)
        if p.status != "open":
            raise WarehouseError(f"{p.number} {p.status} hai.")
        if any(t.get("done") for t in p.tasks or []):
            raise WarehouseError("Kuch maal uth chuka; 'finish' se band kijiye.")
        p.status = "cancelled"
        p.notes = list(p.notes or []) + [f"cancel: {reason}"[:200]]
        n = p.number
    return {"say": f"{n} cancel."}


# ---------------------------------------------------------------- PDFs (pick sheet, count sheet, labels)
def _pdf_table(title: str, sub: str, head: list[str], rows: list[list[str]], widths: list[float]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    y = H - 40

    def header():
        nonlocal y
        c.setFont("Helvetica-Bold", 14)
        c.drawString(36, y, title[:80])
        y -= 16
        c.setFont("Helvetica", 9)
        c.drawString(36, y, sub[:120])
        y -= 18
        c.setFont("Helvetica-Bold", 9)
        x = 36
        for h, w in zip(head, widths):
            c.drawString(x, y, h)
            x += w
        y -= 4
        c.line(36, y, W - 36, y)
        y -= 12
        c.setFont("Helvetica", 9)

    header()
    for r in rows:
        if y < 50:
            c.showPage()
            y = H - 40
            header()
        x = 36
        for v, w in zip(r, widths):
            c.drawString(x, y, str(v)[: max(4, int(w / 5))])
            x += w
        y -= 15
    c.showPage()
    c.save()
    return buf.getvalue()


def _file(tenant: str, name: str, data: bytes, mime: str, title: str, conv: str = "") -> dict:
    from .. import chatfiles
    f = chatfiles.store(tenant, name, data, mime)
    _publish(tenant, "pc_file", {**f, "source": "warehouse", "title": title}, conv)
    return f


def pick_sheet(tenant: str, pick: str, conv: str = "") -> dict:
    v = pick_view(tenant, pick)
    rows = [[str(t["n"]), t["bin"], t["name"], t["batch"] or "-", t["expiry"] or "-", f"{R.qtxt(t['qty'])} {t['unit']}", "[  ]"] for t in v["tasks"]]
    for l in v["lines"]:
        if l.get("short"):
            rows.append(["", "KAM", l["name"], "", "", R.qtxt(l["short"]), ""])
    sub = f"{settings(tenant)['name']} · {v['day']} · orders: {', '.join(v['orders']) or '-'} · raasta bin ke kram mein"
    data = _pdf_table(f"Pick list {v['number']}", sub, ["#", "Bin", "Item", "Batch", "Expiry", "Qty", "Uthaya"], rows, [24, 70, 170, 70, 70, 70, 50])
    f = _file(tenant, f"{v['number']}.pdf", data, "application/pdf", f"Pick list {v['number']}", conv)
    return {"file": f, "say": f"{v['number']} ki sheet taiyaar."}


def labels(tenant: str, what: str = "bins", codes: list | None = None, conv: str = "") -> dict:
    """QR + Code128 labels (A4, 3 x 7). Bins: 'HOOLA-BIN:<code>'; SKUs: 'HOOLA-SKU:<code>' (+ her own pack barcode if set).
    Our codes are internal: never printed as a GS1 GTIN."""
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode import code128
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    want = {str(c).strip().upper() for c in (codes or []) if str(c).strip()}
    if what == "bins":
        items = [(b["code"], b["kind_label"], f"HOOLA-BIN:{b['code']}", "") for b in bins(tenant) if not want or b["code"] in want]
    elif what == "skus":
        items = [(k["code"], k["name"], f"HOOLA-SKU:{k['code']}", k["barcode"]) for k in skus(tenant)
                 if not want or k["code"] in want or k["name"].upper() in want]
    else:
        raise WarehouseError("what: bins | skus")
    if not items:
        raise WarehouseError("Label ke liye kuch nahi mila.")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    cols, rows_n = 3, 7
    lw, lh = (W - 40) / cols, (H - 40) / rows_n
    for i, (code, sub, qrtext, bar) in enumerate(items[:600]):
        pos = i % (cols * rows_n)
        if i and pos == 0:
            c.showPage()
        x = 20 + (pos % cols) * lw
        y = H - 20 - (pos // cols + 1) * lh
        c.rect(x + 2, y + 2, lw - 4, lh - 4)
        q = QrCodeWidget(qrtext)
        b0, b1, b2, b3 = q.getBounds()
        size = lh - 30
        d = Drawing(size, size, transform=[size / (b2 - b0), 0, 0, size / (b3 - b1), 0, 0])
        d.add(q)
        renderPDF.draw(d, c, x + 6, y + 18)
        c.setFont("Helvetica-Bold", 16 if what == "bins" else 11)
        c.drawString(x + size + 12, y + lh - 30, code[:16])
        c.setFont("Helvetica", 8)
        c.drawString(x + size + 12, y + lh - 44, sub[:26])
        bc = code128.Code128(bar or code, barHeight=18, barWidth=0.8)
        bc.drawOn(c, x + size + 6, y + 14)
    c.showPage()
    c.save()
    f = _file(tenant, f"labels_{what}.pdf", buf.getvalue(), "application/pdf", f"{len(items)} {what} labels", conv)
    return {"file": f, "count": len(items), "say": f"{len(items)} label taiyaar (QR + barcode). Print karke bin / maal par lagaiye."}


# ---------------------------------------------------------------- ABC + cycle counts
def classify(tenant: str, days: int = 90) -> dict:
    """ABC by yearly usage value (picked qty x her cost, else stock-list price) over the last `days`; picks when no value."""
    on = today(tenant)
    since = (on - timedelta(days=days)).isoformat()
    cat = {c["key"]: c for c in _catalog(tenant)}
    costs = _costs(tenant)
    with session() as s:
        st = _st(s, tenant)
        split = tuple(st.abc_split or R.ABC_SPLIT)
        rows = s.scalars(select(WhSku).where(WhSku.tenant_id == tenant)).all()
        moves = s.scalars(select(WhMove).where(WhMove.tenant_id == tenant, WhMove.kind == "pick", WhMove.day >= since)).all()
        used: dict[str, float] = {}
        cnt: dict[str, int] = {}
        for m in moves:
            used[m.sku_id] = used.get(m.sku_id, 0.0) - m.qty
            cnt[m.sku_id] = cnt.get(m.sku_id, 0) + 1
        data = []
        for k in rows:
            uv, _ = _unit_value(k.key, cat, costs)
            data.append({"id": k.id, "value": (used.get(k.id, 0.0) * (uv or 0.0)) * 365.0 / days, "picks": cnt.get(k.id, 0)})
        res = R.abc(data, split)
        changed = 0
        for k in rows:
            if k.abc_manual:
                continue
            new = res.get(k.id, "C")
            if new != k.abc:
                k.abc, changed = new, changed + 1
        counts = {c: sum(1 for k in rows if k.abc == c) for c in "ABC"}
        basis = "value" if any(d["value"] > 0 for d in data) else "picks"
    return {"classes": counts, "changed": changed, "basis": basis,
            "say": f"ABC: A {counts['A']}, B {counts['B']}, C {counts['C']} ({'saal ki khapat ka rupaya' if basis == 'value' else 'kitni baar nikla'} se)."}


def due(tenant: str) -> list[dict]:
    on = today(tenant)
    with session() as s:
        st = _st(s, tenant)
        days = _days(st)
        out = []
        for k in s.scalars(select(WhSku).where(WhSku.tenant_id == tenant)).all():
            has = s.scalars(select(WhLot.id).where(WhLot.sku_id == k.id, WhLot.qty > 0).limit(1)).first()
            if not has:
                continue
            is_due, gap = R.count_due(k.abc, k.last_counted, on, days)
            if is_due:
                out.append({"sku_id": k.id, "code": k.code, "name": k.name, "abc": k.abc, "last_counted": k.last_counted, "overdue_days": gap})
    out.sort(key=lambda x: ("ABC".index(x["abc"] or "C"), -x["overdue_days"]))
    return out


def count_plan(tenant: str, bins: list | None = None, sku: str = "", kind: str = "cycle", reason: str = "", conv: str = "") -> dict:
    """A blind count: bins she names, a SKU's bins, or (none) today's due bins (A first, most overdue). The sheet never shows the
    system quantity."""
    cat = _catalog(tenant)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        open_bins = {b for c in s.scalars(select(WhCount).where(WhCount.tenant_id == tenant, WhCount.status == "open")).all() for b in c.bins or []}
        if bins:
            ids = [_need_bin(s, tenant, str(b)).id for b in bins]
        elif sku:
            k = _need_sku(s, tenant, sku, cat)
            ids = sorted({l.bin_id for l in s.scalars(select(WhLot).where(WhLot.sku_id == k.id, WhLot.qty > 0)).all()})
        else:
            ids = []
            for d in due(tenant):
                for l in s.scalars(select(WhLot).where(WhLot.sku_id == d["sku_id"], WhLot.qty > 0)).all():
                    if l.bin_id not in ids:
                        ids.append(l.bin_id)
                if len(ids) >= st.count_bins_per_day:
                    break
            ids = ids[: st.count_bins_per_day]
        ids = [i for i in ids if i not in open_bins or kind in ("spot", "recount")]
        if not ids:
            raise WarehouseError("Aaj ginne ko koi bin nahi (sab gine ja chuke ya ginti khuli hai).")
        lines = []
        for bid in ids:
            for l in s.scalars(select(WhLot).where(WhLot.bin_id == bid, WhLot.qty > 0)).all():
                lines.append({"bin_id": bid, "sku_id": l.sku_id, "batch": l.batch, "lot_id": l.id, "system": None, "counted": None})
        c = WhCount(tenant_id=tenant, number=_next(st, "count", "CC"), kind=kind if kind in ("cycle", "spot", "full", "recount") else "cycle",
                    bins=ids, lines=lines, reason=str(reason)[:200])
        s.add(c)
        s.flush()
        cid = c.id
    v = count_view(tenant, cid)
    v["say"] = f"{v['number']}: {len(v['bins'])} bin ginne hain ({', '.join(v['bins'][:8])}). Sheet par system ki maatra nahi hai: jo dikhe wahi likhiye."
    _publish(tenant, "warehouse_count", {"count": v, "say": v["say"]}, conv)
    return v


def _count(s, tenant: str, ref: str) -> WhCount:
    c = s.get(WhCount, ref)
    if c is None or c.tenant_id != tenant:
        c = s.scalars(select(WhCount).where(WhCount.tenant_id == tenant, WhCount.number == str(ref).upper())).first()
    if c is None:
        raise WarehouseError("Count nahi mila.")
    return c


def count_view(tenant: str, ref: str, reveal: bool = False) -> dict:
    """Blind by default: `system` is never in the view while the count is open (and only with reveal=True after closing)."""
    with session() as s:
        c = _count(s, tenant, ref)
        bmap = {b.id: b.code for b in s.scalars(select(WhBin).where(WhBin.id.in_(c.bins or []))).all()}
        lines = []
        for ln in c.lines or []:
            k = s.get(WhSku, ln["sku_id"])
            row = {"bin": bmap.get(ln["bin_id"]) or (s.get(WhBin, ln["bin_id"]).code if s.get(WhBin, ln["bin_id"]) else ""), "sku": k.code if k else "",
                   "name": k.name if k else "", "unit": k.unit if k else "", "batch": ln.get("batch", ""), "counted": ln.get("counted"),
                   "by": ln.get("by", ""), "found_new": bool(ln.get("found_new"))}
            if reveal and c.status == "closed":
                row["system"] = ln.get("system")
            lines.append(row)
        return {"id": c.id, "number": c.number, "kind": c.kind, "status": c.status, "bins": [bmap.get(b, "") for b in c.bins or []],
                "lines": lines, "counted": sum(1 for l in lines if l["counted"] is not None), "total": len(lines), "reason": c.reason,
                "adjust_id": c.adjust_id, "blind": True}


def counts(tenant: str, status: str = "", limit: int = 40) -> list[dict]:
    with session() as s:
        q = select(WhCount.id).where(WhCount.tenant_id == tenant)
        if status:
            q = q.where(WhCount.status == status)
        ids = s.scalars(q.order_by(WhCount.created_at.desc()).limit(limit)).all()
    return [count_view(tenant, i) for i in ids]


def count_sheet(tenant: str, count: str, conv: str = "") -> dict:
    v = count_view(tenant, count)
    rows = [[l["bin"], l["name"], l["sku"], l["batch"] or "-", "__________"] for l in v["lines"]]
    for b in v["bins"]:
        rows.append([b, "(bin mein aur kuch mila?)", "", "", "__________"])
    data = _pdf_table(f"Count sheet {v['number']} (blind)", f"{settings(tenant)['name']} · system ki maatra jaan-boojh kar nahi chhapi · gin kar likhiye",
                      ["Bin", "Item", "SKU", "Batch", "Gina"], rows, [70, 200, 70, 80, 90])
    f = _file(tenant, f"{v['number']}.pdf", data, "application/pdf", f"Count sheet {v['number']}", conv)
    return {"file": f, "say": f"{v['number']} ki count sheet taiyaar."}


def count_enter(tenant: str, count: str, entries: list, by: str = "Owner") -> dict:
    """What the counter saw: [{bin, item, batch, qty}]. The system quantity is noted (hidden) at this moment."""
    if not entries:
        raise WarehouseError("entries: [{bin, item, batch, qty}]")
    cat = _catalog(tenant)
    n = 0
    with _LOCK, session() as s:
        c = _count(s, tenant, count)
        if c.status != "open":
            raise WarehouseError(f"{c.number} band ho chuka.")
        lines = [dict(l) for l in c.lines or []]
        for e in entries:
            b = _need_bin(s, tenant, str(e.get("bin") or ""))
            if b.id not in (c.bins or []):
                raise WarehouseError(f"{b.code} is ginti mein nahi hai.")
            k = _sku(s, tenant, str(e.get("item") or e.get("sku") or ""), cat, create=True)
            q = R.num(e.get("qty"), 0, 1e7)
            if k is None or q is None:
                raise WarehouseError("Har entry mein item aur qty chahiye.")
            batch = str(e.get("batch") or "")[:40]
            match = [l for l in lines if l["bin_id"] == b.id and l["sku_id"] == k.id and (l.get("batch", "") == batch or not batch)]
            sysq = R.r3(sum(l.qty for l in s.scalars(select(WhLot).where(WhLot.bin_id == b.id, WhLot.sku_id == k.id)).all()
                            if (l.batch == (match[0]["batch"] if match else batch))))
            if match:
                ln = match[0]
            else:
                ln = {"bin_id": b.id, "sku_id": k.id, "batch": batch, "lot_id": "", "found_new": True}
                lines.append(ln)
            ln.update(counted=R.r3(q), system=sysq, by=by[:80], at=clock().isoformat())
            n += 1
        c.lines = lines
        num = c.number
        left = sum(1 for l in lines if l.get("counted") is None)
    return {"entered": n, "left": left, "say": f"{num}: {n} entry likhi" + (f", {left} line abhi gin-ni baaki." if left else ". Sab gin liya: 'band karo' kahiye.")}


def _variance_lines(s, tenant: str, c: WhCount, cat: dict, costs: dict, tol: dict) -> list[dict]:
    out = []
    for ln in c.lines or []:
        if ln.get("counted") is None:
            continue
        k = s.get(WhSku, ln["sku_id"])
        b = s.get(WhBin, ln["bin_id"])
        sysq, cnt = float(ln.get("system") or 0.0), float(ln["counted"])
        diff = R.r3(cnt - sysq)
        uv, basis = _unit_value(k.key if k else "", cat, costs)
        out.append({"bin": b.code if b else "", "bin_id": ln["bin_id"], "sku_id": ln["sku_id"], "sku": k.code if k else "", "name": k.name if k else "",
                    "unit": k.unit if k else "", "abc": k.abc if k else "C", "batch": ln.get("batch", ""), "system": R.r3(sysq), "counted": cnt,
                    "diff": diff, "value": None if uv is None else round(diff * uv, 2), "value_basis": basis,
                    "within": R.within(diff, sysq, k.abc if k else "C", tol)})
    return out


def count_close(tenant: str, count: str, zero_missing: bool = False, by: str = "Owner", conv: str = "") -> dict:
    """Close the count -> variance report. Lines not counted stay 'not counted' (never assumed zero unless she says so). Any
    difference -> ONE adjustment card that only her tap decides."""
    cat_l = _catalog(tenant)
    cat = {x["key"]: x for x in cat_l}
    costs = _costs(tenant)
    on = today(tenant)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        c = _count(s, tenant, count)
        if c.status != "open":
            raise WarehouseError(f"{c.number} pehle se band.")
        lines = [dict(l) for l in c.lines or []]
        missing = [l for l in lines if l.get("counted") is None]
        if missing and zero_missing:
            for l in missing:
                sysq = R.r3(sum(x.qty for x in s.scalars(select(WhLot).where(WhLot.bin_id == l["bin_id"], WhLot.sku_id == l["sku_id"])).all()
                                if x.batch == l.get("batch", "")))
                l.update(counted=0.0, system=sysq, by=by, at=clock().isoformat(), zeroed=True)
            missing = []
        c.lines = lines
        c.status, c.closed_at = "closed", _now()
        counted_skus = {l["sku_id"] for l in lines if l.get("counted") is not None}
        for k in s.scalars(select(WhSku).where(WhSku.id.in_(counted_skus))).all():
            k.last_counted = on.isoformat()
        var = _variance_lines(s, tenant, c, cat, costs, _tol(st))
        cid, num = c.id, c.number
    diffs = [v for v in var if abs(v["diff"]) > 1e-9]
    acc = round(100.0 * (len(var) - len(diffs)) / len(var), 1) if var else None
    res: dict[str, Any] = {"count": count_view(tenant, cid, reveal=True), "variance": var, "accuracy_pct": acc,
                           "not_counted": len(missing), "adjust": None}
    say = f"{num} band: {len(var)} line gini" + (f", sahi {acc:g}%" if acc is not None else "") + "."
    if missing:
        say += f" {len(missing)} line gini hi nahi gayi (inhe zero nahi maana)."
    if diffs:
        adj = _make_adjust(tenant, "count", cid, diffs, by, conv)
        with session() as s:
            c = s.get(WhCount, cid)
            c.adjust_id = adj["id"]
        res["adjust"] = adj
        out_t = [d for d in diffs if not d["within"]]
        say += f" {len(diffs)} line mein farak; badalne ka card aapki haan ke liye bheja." + (f" {len(out_t)} line had se zyada: pehle dobara ginwana theek rahega." if out_t else "")
    else:
        say += " Koi farak nahi."
    res["say"] = say
    return res


def recount(tenant: str, count: str, conv: str = "") -> dict:
    """Count the lines with a difference again; the waiting adjustment card of that count goes stale."""
    with _LOCK, session() as s:
        c = _count(s, tenant, count)
        bins_ = sorted({l["bin_id"] for l in c.lines or [] if l.get("counted") is not None and abs(float(l["counted"]) - float(l.get("system") or 0)) > 1e-9})
        if c.adjust_id:
            a = s.get(WhAdjust, c.adjust_id)
            if a and a.status == "waiting":
                a.status, a.reason = "stale", "dobara ginti"
        num = c.number
    if not bins_:
        raise WarehouseError("Is ginti mein farak wali koi line nahi.")
    return count_plan(tenant, bins=bins_, kind="recount", reason=f"{num} ka dobara", conv=conv)


# ---------------------------------------------------------------- adjustments / write-offs: HER tap only
def _adj_hash(kind: str, lines: list[dict]) -> str:
    return R.hash_of(kind, [{k: l.get(k) for k in ("bin_id", "sku_id", "batch", "system", "counted", "reason")} for l in lines])


def _make_adjust(tenant: str, kind: str, count_id: str, lines: list[dict], by: str, conv: str = "") -> dict:
    total = None
    if all(l.get("value") is not None for l in lines):
        total = round(sum(l["value"] for l in lines), 2)
    for l in lines:
        l.setdefault("reason", R.reason_of(l.get("note", ""), l["diff"]))
    h = _adj_hash(kind, lines)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        dup = s.scalars(select(WhAdjust).where(WhAdjust.tenant_id == tenant, WhAdjust.status == "waiting", WhAdjust.hash == h)).first()
        if dup:
            aid = dup.id
        else:
            a = WhAdjust(tenant_id=tenant, number=_next(st, "adj", "ADJ"), kind=kind, count_id=count_id, lines=lines, value=total, hash=h,
                         asked_by=by)
            s.add(a)
            s.flush()
            aid = a.id
    v = adjust_view(tenant, aid)
    _publish(tenant, "warehouse_adjust", {"adjust": v, "say": v["say"]}, conv)
    return v


def adjust_view(tenant: str, ref: str) -> dict:
    with session() as s:
        a = s.get(WhAdjust, ref)
        if a is None or a.tenant_id != tenant:
            a = s.scalars(select(WhAdjust).where(WhAdjust.tenant_id == tenant, WhAdjust.number == str(ref).upper())).first()
        if a is None:
            raise WarehouseError("Adjustment card nahi mila.")
        c = s.get(WhCount, a.count_id) if a.count_id else None
        lines = list(a.lines or [])
    minus = [l for l in lines if l["diff"] < 0]
    plus = [l for l in lines if l["diff"] > 0]
    say = (f"{a.number}: {'ginti ke baad' if a.kind == 'count' else 'write-off'} stock badlav - "
           + "; ".join(f"{l['bin']} {l['name']} {'+' if l['diff'] > 0 else ''}{R.qtxt(l['diff'])}" for l in lines[:6])
           + (f" (kul {_rs(a.value)})" if a.value is not None else " (daam pata nahi)") + ". Sirf aapke tap se badlega.")
    return {"id": a.id, "number": a.number, "kind": a.kind, "count": c.number if c else "", "lines": lines, "value": a.value,
            "hash": a.hash, "status": a.status, "asked_by": a.asked_by, "reason": a.reason,
            "minus": len(minus), "plus": len(plus), "itc_note": R.ITC_NOTE if minus else "",
            "recount_first": [l["name"] for l in lines if l.get("within") is False],
            "decided_at": a.decided_at.isoformat() if a.decided_at else "", "say": say}


def adjusts(tenant: str, status: str = "", limit: int = 40) -> list[dict]:
    with session() as s:
        q = select(WhAdjust.id).where(WhAdjust.tenant_id == tenant)
        if status:
            q = q.where(WhAdjust.status == status)
        ids = s.scalars(q.order_by(WhAdjust.created_at.desc()).limit(limit)).all()
    return [adjust_view(tenant, i) for i in ids]


def writeoff_request(tenant: str, item: str, bin: str, qty: Any, batch: str = "", reason: str = "", note: str = "", by: str = "Owner",
                     conv: str = "") -> dict:
    """Damaged / expired / lost stock: only a CARD. Nothing leaves the books until her tap."""
    q = R.num(qty, 0.001, 1e7)
    if q is None:
        raise WarehouseError("Kitna? qty chahiye.")
    if reason and reason not in R.REASONS:
        raise WarehouseError("reason: " + ", ".join(R.REASONS))
    cat_l = _catalog(tenant)
    cat = {c["key"]: c for c in cat_l}
    costs = _costs(tenant)
    with session() as s:
        k = _need_sku(s, tenant, item, cat_l)
        b = _need_bin(s, tenant, bin)
        lots = [l for l in s.scalars(select(WhLot).where(WhLot.sku_id == k.id, WhLot.bin_id == b.id)).all() if not batch or l.batch == batch]
        if batch == "" and len({l.batch for l in lots if l.qty > 0}) > 1:
            raise WarehouseError(f"{b.code} mein {k.name} ke kai batch hain; batch bataiye.")
        bt = batch or (lots[0].batch if lots else "")
        have = R.r3(sum(l.qty for l in lots if l.batch == bt))
        if q > have + 1e-9:
            raise WarehouseError(f"{b.code} mein {k.name} {R.qtxt(have)} hi hai.")
        uv, basis = _unit_value(k.key, cat, costs)
        line = {"bin": b.code, "bin_id": b.id, "sku_id": k.id, "sku": k.code, "name": k.name, "unit": k.unit, "abc": k.abc, "batch": bt,
                "system": have, "counted": R.r3(have - q), "diff": -R.r3(q), "value": None if uv is None else round(-q * uv, 2),
                "value_basis": basis, "reason": reason or R.reason_of(note, -q), "note": str(note)[:200]}
    return _make_adjust(tenant, "writeoff", "", [line], by, conv)


def decide_adjust(tenant: str, adjust: str, yes: bool, hash: str = "", reason: str = "", by_tap: bool = False, conv: str = "") -> dict:
    """ONLY her app tap (by_tap=True from POST /api/warehouse/adjustments/{id}/decide). The card's hash must match, and the bins
    must still hold what the card was made from (anything picked / moved since = stale: count again)."""
    if not by_tap:
        raise WarehouseError("Stock badalne ki haan sirf aapke app ke card par tap se hoti hai.")
    on = today(tenant)
    sync: dict[str, float] = {}
    linked_keys = {c["key"] for c in _catalog(tenant)}
    with _LOCK, session() as s:
        a = s.get(WhAdjust, adjust)
        if a is None or a.tenant_id != tenant:
            a = s.scalars(select(WhAdjust).where(WhAdjust.tenant_id == tenant, WhAdjust.number == str(adjust).upper())).first()
        if a is None:
            raise WarehouseError("Card nahi mila.")
        if a.status != "waiting":
            raise WarehouseError(f"{a.number} pehle se {a.status}.")
        if not hash or hash != a.hash or _adj_hash(a.kind, list(a.lines or [])) != a.hash:
            raise WarehouseError("Card badal gaya hai; naya card dekhiye.")
        a.decided_at = _now()
        if not yes:
            a.status, a.reason = "rejected", str(reason or "")[:500]
            num = a.number
            aid = a.id
        else:
            stale = []
            for l in a.lines or []:
                cur = R.r3(sum(x.qty for x in s.scalars(select(WhLot).where(WhLot.bin_id == l["bin_id"], WhLot.sku_id == l["sku_id"])).all()
                               if x.batch == (l.get("batch") or "")))
                if abs(cur - float(l["system"])) > 1e-9:
                    stale.append(f"{l['bin']} {l['name']} (ab {R.qtxt(cur)})")
            if stale:
                a.status, a.reason = "stale", "card ke baad maal hila: " + ", ".join(stale)
                num, aid = a.number, a.id
                s.flush()
                raise_msg = f"{num}: card ke baad maal hila ({', '.join(stale[:3])}). Kuch nahi badla; dobara giniye."
            else:
                raise_msg = ""
                ref = a.number
                for l in a.lines or []:
                    k = s.get(WhSku, l["sku_id"])
                    b = s.get(WhBin, l["bin_id"])
                    d = float(l["diff"])
                    kind = "writeoff" if a.kind == "writeoff" or (d < 0 and l.get("reason") in ("damaged", "expired", "theft", "sample", "lost")) else "adjust"
                    linked = k.key in linked_keys
                    if d > 0:
                        _add(s, tenant, k, b, d, kind, ref, "Owner ki haan", on, l.get("batch", ""), reason=l.get("reason", ""), note=l.get("note", ""),
                             synced=linked)
                    elif d < 0:
                        left = -d
                        for lot in s.scalars(select(WhLot).where(WhLot.bin_id == b.id, WhLot.sku_id == k.id)).all():
                            if lot.batch != (l.get("batch") or "") or left <= 0:
                                continue
                            take = min(lot.qty, left)
                            _take(s, tenant, lot, take, kind, ref, "Owner ki haan", on, reason=l.get("reason", ""), note=l.get("note", ""),
                                  synced=linked)
                            left = R.r3(left - take)
                    sync[k.key] = sync.get(k.key, 0.0) + d
                a.status, a.reason = "approved", str(reason or "")[:500]
                num, aid = a.number, a.id
        status = a.status
    if status == "stale":
        _publish(tenant, "warehouse_adjust", {"adjust": adjust_view(tenant, aid), "say": raise_msg}, conv)
        raise WarehouseError(raise_msg)
    missing = _sync(tenant, sync) if status == "approved" else []
    v = adjust_view(tenant, aid)
    if status == "approved":
        say = f"{num}: aapki haan se stock badla, ledger mein wajah ke saath likha."
        if v["itc_note"]:
            say += " " + R.ITC_NOTE
        if missing:
            say += f" ({len(missing)} item stock list par nahi, wahan ki ginti nahi badli.)"
    else:
        say = f"{num}: mana kiya, stock waisa hi hai."
    v["say"] = say
    _publish(tenant, "warehouse_adjust", {"adjust": v, "say": say}, conv)
    return v


# ---------------------------------------------------------------- reports
def stock_by_bin(tenant: str, bin: str = "", sku: str = "") -> list[dict]:
    on = today(tenant)
    cat = _catalog(tenant)
    with session() as s:
        q = select(WhLot).where(WhLot.tenant_id == tenant, WhLot.qty > 0)
        if bin:
            q = q.where(WhLot.bin_id == _need_bin(s, tenant, bin).id)
        if sku:
            q = q.where(WhLot.sku_id == _need_sku(s, tenant, sku, cat).id)
        out = [_lot_view(s, l, on) for l in s.scalars(q).all()]
    out.sort(key=lambda x: (x["bin"], x["name"], x["expiry"] or "9"))
    return out


def near_expiry(tenant: str, days: int | None = None) -> dict:
    on = today(tenant)
    with session() as s:
        nd = int(days or _st(s, tenant).near_expiry_days)
    rows = [l for l in stock_by_bin(tenant) if l["expiry"]]
    expired = [l for l in rows if R.expiry_state(l["expiry"], on) == "expired"]
    near = [l for l in rows if R.expiry_state(l["expiry"], on, nd) == "near"]
    for l in near + expired:
        l["days_left"] = (R.parse_date(l["expiry"]) - on).days
    near.sort(key=lambda x: x["days_left"])
    say = f"{len(near)} batch {nd} din mein expire" + (f", {len(expired)} expire ho chuke (quarantine mein daaliye, write-off sirf aapke card se)" if expired else "") + "."
    return {"near": near, "expired": expired, "days": nd, "say": say}


def slow_dead(tenant: str) -> dict:
    on = today(tenant)
    cat = {c["key"]: c for c in _catalog(tenant)}
    costs = _costs(tenant)
    with session() as s:
        st = _st(s, tenant)
        slow, dead = [], []
        for k in s.scalars(select(WhSku).where(WhSku.tenant_id == tenant)).all():
            qty = R.r3(sum(l.qty for l in s.scalars(select(WhLot).where(WhLot.sku_id == k.id, WhLot.qty > 0)).all()))
            if qty <= 0:
                continue
            last = s.scalars(select(WhMove.day).where(WhMove.sku_id == k.id, WhMove.kind == "pick").order_by(WhMove.day.desc()).limit(1)).first()
            first_in = s.scalars(select(WhMove.day).where(WhMove.sku_id == k.id, WhMove.qty > 0).order_by(WhMove.day).limit(1)).first()
            ref = R.parse_date(last or first_in)
            if not ref:
                continue
            idle = (on - ref).days
            uv, _ = _unit_value(k.key, cat, costs)
            row = {"sku": k.code, "name": k.name, "qty": qty, "idle_days": idle, "last_pick": last or "", "value": None if uv is None else round(uv * qty, 2)}
            if idle >= st.dead_days:
                dead.append(row)
            elif idle >= st.slow_days:
                slow.append(row)
    for lst in (slow, dead):
        lst.sort(key=lambda x: -(x["value"] or 0))
    tv = sum(x["value"] or 0 for x in dead)
    return {"slow": slow, "dead": dead, "say": f"{len(slow)} item dheere, {len(dead)} item pade hue (dead)" + (f", lagbhag {_rs(tv)} ka maal" if tv else "") + "."}


def recon(tenant: str) -> dict:
    """Bins vs the shared stock count (hoola_stock) for linked SKUs. Differences are shown, never fixed by themselves."""
    cat = {c["key"]: c for c in _catalog(tenant)}
    out = []
    with session() as s:
        for k in s.scalars(select(WhSku).where(WhSku.tenant_id == tenant)).all():
            c = cat.get(k.key)
            if c is None:
                continue
            shared = c.get("qty")
            inbins = R.r3(sum(l.qty for l in s.scalars(select(WhLot).where(WhLot.sku_id == k.id)).all()))
            if shared is None or abs(shared - inbins) > 1e-9:
                out.append({"sku": k.code, "name": k.name, "in_bins": inbins, "stock_list": shared,
                            "diff": None if shared is None else R.r3(inbins - shared)})
    say = (f"{len(out)} item mein binon ki ginti aur stock list alag hai. Count karwa kar card se theek kijiye." if out
           else "Binon ki ginti aur stock list barabar hai.")
    return {"items": out, "say": say}


def overview(tenant: str) -> dict:
    return {**day(tenant), "settings": settings(tenant), "bins": bins(tenant), "picks": picks(tenant, "open"), "counts": counts(tenant, "open"),
            "adjusts": adjusts(tenant, "waiting"), "grns": grns(tenant, 10)}


def day(tenant: str) -> dict:
    d = due(tenant)
    ne = near_expiry(tenant)
    op = picks(tenant, "open")
    wa = adjusts(tenant, "waiting")
    rc = recon(tenant)
    with session() as s:
        rcv = s.scalars(select(WhBin).where(WhBin.tenant_id == tenant, WhBin.kind == "receiving")).first()
        rcv_qty = _bin_qty(s, rcv.id) if rcv else 0.0
        bins_n = len(s.scalars(select(WhBin.id).where(WhBin.tenant_id == tenant)).all())
    parts = []
    if wa:
        parts.append(f"{len(wa)} stock badlav card aapki haan ka intezaar")
    if op:
        parts.append(f"{len(op)} pick list khuli")
    if rcv_qty:
        parts.append(f"receiving mein {R.qtxt(rcv_qty)} maal rakhna baaki")
    if d:
        parts.append(f"{len(d)} item ginne ka samay (A pehle)")
    if ne["expired"]:
        parts.append(f"{len(ne['expired'])} batch expire")
    if ne["near"]:
        parts.append(f"{len(ne['near'])} batch jaldi expire")
    if rc["items"]:
        parts.append(f"{len(rc['items'])} item ginti alag")
    say = ("Godown: " + "; ".join(parts) + ".") if parts else ("Godown mein aaj sab theek." if bins_n else "Pehle bin banaiye (jaise zone A, 3 aisle, 4 rack).")
    return {"say": say, "due": d[:20], "near_expiry": ne, "open_picks": len(op), "waiting": len(wa), "receiving_qty": rcv_qty,
            "recon": rc["items"][:20], "has_something": bool(parts)}


def export(tenant: str, what: str = "stock", count: str = "", conv: str = "") -> dict:
    """Excel: stock (by bin) | ledger | abc | expiry | slow | variance (count)."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    if what == "stock":
        ws.title = "Stock by bin"
        ws.append(["Bin", "SKU", "Item", "Unit", "Batch", "Expiry", "Qty", "Serials", "Status"])
        for l in stock_by_bin(tenant):
            ws.append([l["bin"], l["sku"], l["name"], l["unit"], l["batch"], l["expiry"], l["qty"], ", ".join(l["serials"][:50]), l["status"]])
    elif what == "ledger":
        ws.title = "Ledger"
        ws.append(["Date", "Kind", "Bin", "SKU", "Item", "Batch", "Qty (+in / -out)", "Ref", "By", "Reason", "Note"])
        for m in reversed(ledger(tenant, days=3650, limit=2000)["moves"]):
            ws.append([m["day"], m["kind"], m["bin"], m["sku"], m["name"], m["batch"], m["qty"], m["ref"], m["by"], m["reason"], m["note"]])
    elif what == "abc":
        ws.title = "ABC"
        ws.append(["SKU", "Item", "Class", "Last counted", "In bins", "Value"])
        for k in skus(tenant):
            ws.append([k["code"], k["name"], k["abc"], k["last_counted"], k["in_bins"], k["value"]])
    elif what == "expiry":
        ws.title = "Expiry"
        ne = near_expiry(tenant)
        ws.append(["State", "Bin", "Item", "Batch", "Expiry", "Days left", "Qty"])
        for st_, rows in (("expired", ne["expired"]), ("near", ne["near"])):
            for l in rows:
                ws.append([st_, l["bin"], l["name"], l["batch"], l["expiry"], l["days_left"], l["qty"]])
    elif what == "slow":
        ws.title = "Slow-dead"
        sd = slow_dead(tenant)
        ws.append(["Type", "SKU", "Item", "Qty", "Idle days", "Last pick", "Value"])
        for t_, rows in (("dead", sd["dead"]), ("slow", sd["slow"])):
            for r in rows:
                ws.append([t_, r["sku"], r["name"], r["qty"], r["idle_days"], r["last_pick"], r["value"]])
    elif what == "variance":
        if not count:
            raise WarehouseError("Kaunsi ginti? count chahiye.")
        cat = {c["key"]: c for c in _catalog(tenant)}
        costs = _costs(tenant)
        with session() as s:
            c = _count(s, tenant, count)
            if c.status != "closed":
                raise WarehouseError("Ginti band hone ke baad hi variance.")
            var = _variance_lines(s, tenant, c, cat, costs, _tol(_st(s, tenant)))
            num = c.number
        ws.title = f"Variance {num}"
        ws.append(["Bin", "SKU", "Item", "Class", "Batch", "System", "Counted", "Diff", "Value", "Within tolerance"])
        for v in var:
            ws.append([v["bin"], v["sku"], v["name"], v["abc"], v["batch"], v["system"], v["counted"], v["diff"], v["value"], "yes" if v["within"] else "NO"])
    else:
        raise WarehouseError("what: stock | ledger | abc | expiry | slow | variance")
    bio = io.BytesIO()
    wb.save(bio)
    f = _file(tenant, f"Godown_{what}.xlsx", bio.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"Godown {what}", conv)
    return {"file": f, "say": f"Excel ({what}) taiyaar."}


# ---------------------------------------------------------------- worker
def tick(now: datetime | None = None) -> int:
    """Once a day at her morning time (within 3 h): the morning note, only when there is something."""
    n = 0
    t0 = (now or clock())
    with session() as s:
        tenants = []
        for r in s.scalars(select(WhSettings)).all():
            local = t0.astimezone(_tz(r.tenant_id))
            try:
                hh, mm = [int(x) for x in (r.morning_time or "09:00").split(":")]
            except ValueError:
                hh, mm = 9, 0
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            d = local.date().isoformat()
            if r.last_morning != d and 0 <= late <= 180:
                r.last_morning = d
                tenants.append(r.tenant_id)
    for t in tenants:
        try:
            dv = day(t)
            if dv["has_something"]:
                _publish(t, "warehouse_day", dv)
                n += 1
        except Exception:
            log.exception("warehouse morning failed")
    return n
