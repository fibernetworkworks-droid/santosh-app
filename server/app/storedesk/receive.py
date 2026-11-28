"""Receiving: purchase orders she records, the receipt (GRN) drafted and checked line by line, confirmed only by a named person, then
quality hold -> accepted / rejected -> returned to the supplier.

A receipt is matched three ways - the order, the supplier's paper and what was counted or weighed - and every shortage, excess or
damage is written on the receipt itself. Checks are arithmetic on her numbers: the tolerance, a bar's mass per metre, a shelf life,
the ready-mix time limit all come from her item settings, never from Hoola. A heat number with no certificate goes on hold."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import packs as P
from .core import (LOCK, S, SdDoc, SdItem, SdLot, StoreError, balance, balances, doc_view, find_item, get_doc, lots_fifo, num, number, post,
                   settings, show_qty, store_id, tables, to_base, today)

LINE_KEYS = ("item", "doc_qty", "qty", "unit", "lot", "made", "expires", "cert", "gross", "tare", "bars", "length_m", "batch_time",
             "arrival", "rate", "damaged", "docs", "note")


def _f(v: Any) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise StoreError(f"'{v}' is not a number.")


def _mins(a: Any, b: Any) -> float | None:
    def t(x: Any) -> datetime | None:
        x = S(x, 25)
        if not x:
            return None
        for f in ("%H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(x, f)
            except ValueError:
                continue
        raise StoreError(f"Time '{x}': write it as HH:MM.")
    x, y = t(a), t(b)
    if x is None or y is None:
        return None
    m = (y - x).total_seconds() / 60
    return m + 1440 if m < 0 else m


# ---------------------------------------------------------------- purchase orders (hers; Hoola never places one)
def save_po(tenant: str, number_: str, supplier: str, lines: list[dict[str, Any]], due: str = "", store: str = "", note: str = "",
            id: str = "") -> dict[str, Any]:
    tables()
    number_ = S(number_, 20).upper()
    if not number_:
        raise StoreError("Give the order's number (your purchase order number).")
    if not S(supplier):
        raise StoreError("Give the supplier's name.")
    if not lines:
        raise StoreError("Add at least one line: item, quantity, rate.")
    with LOCK, session() as s:
        out = []
        for ln in lines[:200]:
            it = find_item(s, tenant, ln.get("item"))
            base, qin, uin = to_base(it, ln.get("qty"), S(ln.get("unit"), 12))
            rate = _f(ln.get("rate"))
            per_base = (rate * qin / base) if rate is not None and base else None
            out.append({"item_id": it.id, "item": it.name, "qty": round(base, 6), "qty_in": qin, "unit_in": uin, "unit": it.unit,
                        "rate": per_base, "rate_in": rate, "received": 0.0})
        sid = store_id(s, tenant, store)
        d = None
        if id:
            d = get_doc(s, tenant, id, "po")
        else:
            if s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.kind == "po", SdDoc.number == number_)).first():
                raise StoreError(f"Order {number_} is already recorded.")
            d = SdDoc(tenant_id=tenant, kind="po", number=number_, status="open")
            s.add(d)
        if d.lines:
            got = {x["item_id"]: x.get("received", 0) for x in d.lines}
            for x in out:
                x["received"] = got.get(x["item_id"], 0.0)
        d.party, d.lines, d.store_id = S(supplier, 160), out, sid
        d.data = {"due": S(due, 10), "note": S(note, 300)}
        d.day = today(tenant).isoformat()
        d.updated_at = now()
        s.flush()
        v = doc_view(s, d)
    v["say"] = f"Order {number_} from {supplier} recorded: {len(out)} line(s)."
    return v


def _po_status(lines: list[dict[str, Any]]) -> str:
    if all(x.get("received", 0) + 1e-9 >= x["qty"] for x in lines):
        return "received"
    return "part" if any(x.get("received", 0) > 0 for x in lines) else "open"


# ---------------------------------------------------------------- the receipt
def _check_line(s, tenant: str, st: dict[str, Any], it: SdItem, ln: dict[str, Any], po: SdDoc | None, supplier: str) -> dict[str, Any]:
    unit = S(ln.get("unit"), 12)
    checks: list[dict[str, str]] = []
    doc_q = _f(ln.get("doc_qty"))
    gross, tare = _f(ln.get("gross")), _f(ln.get("tare"))
    counted = _f(ln.get("qty"))
    if counted is None and gross is not None and tare is not None:
        counted = gross - tare
        checks.append({"sev": "ok", "text": f"Weighbridge: {gross:g} - {tare:g} = {counted:g} {unit or it.unit} net"})
    conv = lambda q: to_base(it, q, unit)[0] if q is not None else None   # noqa: E731
    doc_b, cnt_b = conv(doc_q) if doc_q else None, conv(counted) if counted is not None and counted > 0 else None
    dmg = _f(ln.get("damaged")) or 0.0
    dmg_b = conv(dmg) if dmg else 0.0
    tol = it.tol_pct if it.tol_pct >= 0 else float(st["receive_tol"])
    hold_why: list[str] = []
    if cnt_b is None:
        checks.append({"sev": "warn", "text": "Not counted or weighed yet"})
    if doc_b and cnt_b is not None:
        d = (cnt_b - doc_b) / doc_b * 100
        if abs(d) > tol + 1e-9:
            checks.append({"sev": "bad", "text": f"Counted {show_qty(it, cnt_b)} vs the paper's {show_qty(it, doc_b)}: {d:+.1f}%, your tolerance ±{tol:g}%"})
        else:
            checks.append({"sev": "ok", "text": f"Counted vs the paper: {d:+.1f}% (within ±{tol:g}%)"})
    bars, length = _f(ln.get("bars")), _f(ln.get("length_m"))
    if bars and length:
        if not it.mass_per_m:
            checks.append({"sev": "warn", "text": f"Bar weight not checked: set {it.name}'s mass per metre (kg/m) from your standard"})
        elif cnt_b is not None:
            kg = bars * length * it.mass_per_m
            nominal = kg / 1000 if it.unit in ("t", "tonne") else kg if it.unit == "kg" else None
            if nominal is None:
                checks.append({"sev": "warn", "text": f"Bar weight not checked: {it.name} is kept in {it.unit}, not kg or t"})
            else:
                d = (cnt_b - nominal) / nominal * 100
                src = f" ({it.mass_src})" if it.mass_src else ""
                checks.append({"sev": "bad" if abs(d) > tol + 1e-9 else "ok",
                               "text": f"{bars:g} bars x {length:g} m x {it.mass_per_m:g} kg/m{src} = {show_qty(it, nominal)} nominal; weighed {d:+.1f}% (±{tol:g}%)"})
    if po is not None:
        line = next((x for x in po.lines or [] if x["item_id"] == it.id), None)
        if supplier and po.party and supplier.lower() not in po.party.lower() and po.party.lower() not in supplier.lower():
            checks.append({"sev": "warn", "text": f"Supplier '{supplier}' is not the order's '{po.party}'"})
        if line is None:
            checks.append({"sev": "bad", "text": f"{it.name} is not on order {po.number}"})
        else:
            open_q = line["qty"] - line.get("received", 0)
            if cnt_b is not None and cnt_b > open_q + 1e-9:
                checks.append({"sev": "warn", "text": f"More than the order's open {show_qty(it, max(open_q, 0))} by {show_qty(it, cnt_b - max(open_q, 0))}: the buyer accepts the excess or it goes back"})
            elif cnt_b is not None:
                checks.append({"sev": "ok", "text": f"Within the order's open {show_qty(it, open_q)}"})
            r = _f(ln.get("rate"))
            if r is not None and line.get("rate_in") is not None and abs(r - float(line["rate_in"])) > 1e-6:
                checks.append({"sev": "warn", "text": f"Rate {r:g} is not the order's {float(line['rate_in']):g}"})
    else:
        checks.append({"sev": "warn", "text": "No purchase order to match"})
    if it.trace in ("heat", "batch", "serial") and not S(ln.get("lot")):
        checks.append({"sev": "bad", "text": f"No {it.trace} number given - {it.name} has to be traced"})
        hold_why.append(f"no {it.trace} number")
    if it.trace == "heat" and not S(ln.get("cert")):
        checks.append({"sev": "bad", "text": "No mill test certificate for this heat - it goes on quality hold"})
        hold_why.append("no certificate")
    made = S(ln.get("made"), 10)
    if made and it.shelf_days:
        try:
            age = (today(tenant) - date.fromisoformat(made)).days
        except ValueError:
            raise StoreError(f"Made on '{made}': write it as YYYY-MM-DD.")
        if age > it.shelf_days:
            checks.append({"sev": "bad", "text": f"Made {age} days ago - past your {it.shelf_days}-day limit"})
            hold_why.append("too old")
        elif age > 0.8 * it.shelf_days:
            checks.append({"sev": "warn", "text": f"Made {age} days ago - close to your {it.shelf_days}-day limit; issue it first"})
        else:
            checks.append({"sev": "ok", "text": f"Made {age} days ago (your limit {it.shelf_days} days)"})
    mins = _mins(ln.get("batch_time"), ln.get("arrival"))
    if mins is not None:
        if it.max_minutes and mins > it.max_minutes:
            checks.append({"sev": "bad", "text": f"Batched {mins:.0f} min before arrival - over the {it.max_minutes} min in your specification"})
            hold_why.append("over the time limit")
        elif it.max_minutes:
            checks.append({"sev": "ok", "text": f"Batched {mins:.0f} min before arrival (limit {it.max_minutes})"})
        else:
            checks.append({"sev": "warn", "text": f"Batched {mins:.0f} min before arrival - set the limit from your specification to check it"})
    have = set(ln.get("docs") or [])
    for row in P.docs_for(st["country"], it.category, it.trace, st.get("packs_off")):
        if row["id"] in ("gen-delivery", "gen-heat"):
            continue
        if row["check"]:
            checks.append({"sev": "info", "text": f"Check this: {row['need']} (not read from the rule itself)"})
        elif row["id"] not in have:
            checks.append({"sev": "bad", "text": f"Missing: {row['need']} - {row['source']}"})
            hold_why.append("missing " + row["id"])
    if dmg_b:
        checks.append({"sev": "warn", "text": f"Damaged: {show_qty(it, dmg_b)} - not taken into stock, noted for the supplier"})
    accept = max((cnt_b or 0) - dmg_b, 0)
    to = "hold" if (it.inspect or hold_why) else "available"
    return {"item_id": it.id, "item": it.name, "unit": it.unit, "unit_in": unit or it.unit, "doc_qty": doc_b, "counted": cnt_b,
            "damaged": dmg_b, "accept": round(accept, 6), "short": round(max((doc_b or 0) - (cnt_b or 0), 0), 6) if doc_b and cnt_b is not None else 0,
            "excess": round(max((cnt_b or 0) - (doc_b or 0), 0), 6) if doc_b and cnt_b is not None else 0,
            "to": to, "hold_why": hold_why, "checks": checks,
            "src": {k: ln.get(k) for k in LINE_KEYS if ln.get(k) not in (None, "", [])}}


def draft_receipt(tenant: str, supplier: str, lines: list[dict[str, Any]], store: str = "", doc_no: str = "", doc_date: str = "",
                  vehicle: str = "", po: str = "", who: str = "", driver: str = "", note: str = "", photos: list[str] | None = None,
                  id: str = "", read_from: str = "") -> dict[str, Any]:
    """Draft (or redraft) a receipt and check every line. Nothing enters stock until a named person confirms it."""
    tables()
    st = settings(tenant)
    if not S(supplier):
        raise StoreError("Who delivered it? Give the supplier's name.")
    if not lines:
        raise StoreError("Add the lines that arrived: item and quantity.")
    with LOCK, session() as s:
        pod = get_doc(s, tenant, po, "po") if S(po) else None
        out = []
        for ln in lines[:200]:
            if not isinstance(ln, dict):
                raise StoreError("Each line: {item, doc_qty, qty, unit, lot, cert ...}.")
            out.append(_check_line(s, tenant, st, find_item(s, tenant, ln.get("item")), ln, pod, S(supplier)))
        sid = store_id(s, tenant, store)
        if id:
            d = get_doc(s, tenant, id, "grn")
            if d.status != "draft":
                raise StoreError(f"{d.number} is already {d.status}: it cannot change. Reverse a movement instead.")
        else:
            d = SdDoc(tenant_id=tenant, kind="grn", number=number(s, tenant, "grn"), status="draft")
            s.add(d)
        bad = sum(1 for x in out for c in x["checks"] if c["sev"] == "bad")
        d.store_id, d.party, d.lines, d.who = sid, S(supplier, 160), out, S(who, 80)
        d.data = {"doc_no": S(doc_no, 60), "doc_date": S(doc_date, 10), "vehicle": S(vehicle, 30), "po": pod.number if pod else "",
                  "po_id": pod.id if pod else "", "driver": S(driver, 80), "note": S(note, 300), "photos": [S(p, 80) for p in (photos or [])][:20],
                  "bad": bad, "read_from": S(read_from, 80),
                  "word": P.pack(st["country"])["delivery_word"]}
        if not S(doc_no):
            d.data["checks"] = [{"sev": "warn", "text": f"No {d.data['word']} number - write it on the receipt"}]
        d.day = today(tenant).isoformat()
        d.updated_at = now()
        s.flush()
        v = doc_view(s, d)
    short = [x for x in out if x["short"] > 0]
    v["say"] = (f"{v['number']} drafted from {supplier}: {len(out)} line(s), {bad} serious finding(s)"
                + (f"; short on {', '.join(x['item'] for x in short)}" if short else "")
                + ". A named person confirms it before anything enters stock.")
    return v


def confirm_receipt(tenant: str, id: str, who: str) -> dict[str, Any]:
    """Her storekeeper's tap: accepted quantities go into stock (on quality hold where a check or the item asks), each line its own lot."""
    tables()
    who = S(who, 80)
    if not who:
        raise StoreError("Who is confirming the receipt? Give the person's name.")
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "grn")
        if d.status != "draft":
            raise StoreError(f"{d.number} is already {d.status}.")
        if any(x["counted"] is None for x in d.lines or []):
            raise StoreError("Count or weigh every line before confirming.")
        pod = s.get(SdDoc, d.data.get("po_id")) if (d.data or {}).get("po_id") else None
        held, took = 0, 0
        new_lines = []
        for x in d.lines:
            it = s.get(SdItem, x["item_id"])
            src = x.get("src") or {}
            rate = _f(src.get("rate"))
            per_base = None
            if rate is not None:
                b, qi, _u = to_base(it, 1, x.get("unit_in") or it.unit)
                per_base = rate / b if b else None
            elif pod is not None:
                pl = next((y for y in pod.lines if y["item_id"] == it.id), None)
                per_base = pl.get("rate") if pl else None
            lot = SdLot(tenant_id=tenant, item_id=it.id, ref=S(src.get("lot"), 60), made=S(src.get("made"), 10), expires=S(src.get("expires"), 10),
                        cert=S(src.get("cert"), 80), receipt_id=d.id, cost=per_base or it.price or 0.0, received=d.day or today(tenant).isoformat())
            s.add(lot)
            s.flush()
            if per_base:
                it.price = per_base
            if x["accept"] > 1e-9:
                post(s, tenant, "receive", it, x["accept"], ("", "outside"), (d.store_id, x["to"]), lot=lot.id, cost=lot.cost,
                     doc={"grn": d.number, "grn_id": d.id, "po": (d.data or {}).get("po", ""), "doc_no": (d.data or {}).get("doc_no", ""),
                          "supplier": d.party}, who=who, note="; ".join(x.get("hold_why") or []), day=d.day)
                took += 1
                held += x["to"] == "hold"
            if pod is not None:
                for y in pod.lines:
                    if y["item_id"] == it.id:
                        y["received"] = round(y.get("received", 0) + x["accept"], 6)
            new_lines.append({**x, "lot_id": lot.id})
        if pod is not None:
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(pod, "lines")
            pod.status = _po_status(pod.lines)
            pod.updated_at = now()
        d.lines, d.status, d.approver = new_lines, "confirmed", who
        d.data = {**(d.data or {}), "confirmed_at": now().isoformat(), "invoiced": ""}
        d.updated_at = now()
        v = doc_view(s, d)
    v["say"] = f"{v['number']} confirmed by {who}: {took} line(s) into stock" + (f", {held} on quality hold for the QC engineer" if held else "") + "."
    return v


def reject_receipt(tenant: str, id: str, who: str, reason: str) -> dict[str, Any]:
    tables()
    if not S(who) or not S(reason):
        raise StoreError("Rejecting a delivery needs the person's name and the reason.")
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "grn")
        if d.status != "draft":
            raise StoreError(f"{d.number} is already {d.status}.")
        d.status, d.approver = "rejected", S(who, 80)
        d.data = {**(d.data or {}), "reject": S(reason, 300)}
        d.updated_at = now()
        v = doc_view(s, d)
    v["say"] = f"{v['number']} rejected by {who}: nothing entered stock."
    return v


def mark_invoiced(tenant: str, id: str, invoice: str) -> dict[str, Any]:
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "grn")
        if d.status != "confirmed":
            raise StoreError("Only a confirmed receipt is matched to an invoice.")
        d.data = {**(d.data or {}), "invoiced": S(invoice, 60) or "yes"}
        d.updated_at = now()
        v = doc_view(s, d)
    v["say"] = f"{v['number']} matched to invoice {invoice or ''}."
    return v


# ---------------------------------------------------------------- quality hold
def quality_queue(tenant: str) -> list[dict[str, Any]]:
    tables()
    from .core import store_names
    with session() as s:
        names = store_names(s, tenant)
        out = []
        bal = balances(s, tenant)
        lots = {r.id: r for r in s.scalars(select(SdLot).where(SdLot.tenant_id == tenant)).all()}
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        for (iid, lot, st, pos, _h), q in bal.items():
            if pos not in ("hold", "blocked") or q <= 1e-9:
                continue
            l, it = lots.get(lot), its.get(iid)
            days = (today(tenant) - date.fromisoformat(l.received)).days if l and l.received else None
            out.append({"item_id": iid, "item": it.name if it else "?", "unit": it.unit if it else "", "lot_id": lot, "lot": l.ref if l else "",
                        "cert": l.cert if l else "", "store_id": st, "store": names.get(st, ""), "pos": pos, "qty": q, "days": days})
        return sorted(out, key=lambda x: (x["pos"], -(x["days"] or 0)))


def quality(tenant: str, decision: str, lot: str, who: str, store: str = "", qty: Any = None, note: str = "", cert: str = "") -> dict[str, Any]:
    """The QC engineer's decision on a held lot: accept -> available, reject -> blocked. Hoola never decides quality."""
    tables()
    who = S(who, 80)
    if not who:
        raise StoreError("Quality is decided by a named person (the QC engineer): give the name.")
    if decision not in ("accept", "reject"):
        raise StoreError("Decision: accept or reject.")
    with LOCK, session() as s:
        l = s.get(SdLot, lot)
        if l is None or l.tenant_id != tenant:
            raise StoreError("That lot is not yours.")
        it = s.get(SdItem, l.item_id)
        sid = store_id(s, tenant, store) if store else None
        held = [(st, q) for (i, lo, st, p, h), q in balances(s, tenant, [it.id]).items()
                if lo == l.id and p == "hold" and q > 1e-9 and (sid is None or st == sid)]
        if not held:
            raise StoreError(f"Nothing of lot {l.ref or l.id} is on hold.")
        if cert:
            l.cert = S(cert, 80)
        if decision == "accept" and it.trace == "heat" and not l.cert:
            raise StoreError("This heat has no mill test certificate on file. Add the certificate's number first, or reject the lot.")
        moved = 0.0
        for st, q in held:
            take = min(q, num(qty) - moved) if qty not in (None, "") else q
            if take <= 1e-9:
                break
            post(s, tenant, decision, it, take, (st, "hold"), (st, "available" if decision == "accept" else "blocked"), lot=l.id,
                 cost=l.cost, doc={"lot": l.ref}, who=who, approver=who, note=note, day=today(tenant).isoformat())
            moved += take
        say = f"{it.name} lot {l.ref or '-'}: {show_qty(it, moved)} {'accepted - now available' if decision == 'accept' else 'rejected - blocked, waiting to go back'} ({who})."
        return {"lot": l.id, "qty": moved, "say": say}


def return_vendor(tenant: str, lot: str, who: str, qty: Any = None, store: str = "", reason: str = "") -> dict[str, Any]:
    tables()
    who = S(who, 80)
    if not who:
        raise StoreError("Give the name of the person sending it back.")
    with LOCK, session() as s:
        l = s.get(SdLot, lot)
        if l is None or l.tenant_id != tenant:
            raise StoreError("That lot is not yours.")
        it = s.get(SdItem, l.item_id)
        g = s.get(SdDoc, l.receipt_id) if l.receipt_id else None
        sid = store_id(s, tenant, store) if store else None
        places = [((st, p), q) for (i, lo, st, p, h), q in balances(s, tenant, [it.id]).items()
                  if lo == l.id and p in ("blocked", "available") and q > 1e-9 and (sid is None or st == sid)]
        places.sort(key=lambda x: x[0][1] != "blocked")
        want = num(qty) if qty not in (None, "") else sum(q for _p, q in places)
        if want <= 1e-9:
            raise StoreError("Nothing of that lot is left to send back.")
        left = want
        for (st, p), q in places:
            take = min(q, left)
            post(s, tenant, "return_vendor", it, take, (st, p), ("", "vendor"), lot=l.id, cost=l.cost,
                 doc={"grn": g.number if g else "", "supplier": g.party if g else ""}, who=who, note=S(reason, 300), day=today(tenant).isoformat())
            left -= take
            if left <= 1e-9:
                break
        if left > 1e-6:
            raise StoreError(f"Only {show_qty(it, want - left)} of that lot can be sent back.")
        sup = g.party if g else "the supplier"
        note = (f"To {sup}: we are returning {show_qty(it, want)} of {it.name}" + (f" (lot {l.ref})" if l.ref else "") +
                (f", received on {g.number} ({(g.data or {}).get('doc_no') or 'no paper number'})" if g else "") +
                (f". Reason: {reason}." if reason else ".") + " Please send a credit note or a replacement.")
        return {"qty": want, "debit_note": note, "say": f"{show_qty(it, want)} of {it.name} sent back to {sup}. The note for them is ready."}


def receipts_open(tenant: str) -> list[dict[str, Any]]:
    from .core import docs
    return docs(tenant, "grn", "draft")


_NUM = re.compile(r"^\s*([^,;]+?)\s*[,;]\s*([\d.,]+)\s*(?:[,;]\s*([A-Za-z0-9 ]{1,12}))?\s*(?:[,;]\s*([^,;]*))?(?:[,;]\s*([^,;]*))?\s*$")


def parse_lines(text: str) -> list[dict[str, Any]]:
    """'item, quantity, unit, lot, certificate' lines (a pasted list) -> receipt lines. Text is data, never instructions."""
    out = []
    for raw in str(text or "")[:20000].splitlines():
        if not raw.strip() or raw.lower().startswith(("item", "#")):
            continue
        m = _NUM.match(raw)
        if not m:
            raise StoreError(f"Line '{raw[:60]}': write item, quantity, unit, lot, certificate.")
        out.append({"item": m.group(1), "doc_qty": m.group(2).replace(",", ""), "qty": m.group(2).replace(",", ""), "unit": (m.group(3) or "").strip(),
                    "lot": (m.group(4) or "").strip(), "cert": (m.group(5) or "").strip()})
    if not out:
        raise StoreError("No lines found.")
    return out


__all__ = ["save_po", "draft_receipt", "confirm_receipt", "reject_receipt", "mark_invoiced", "quality_queue", "quality", "return_vendor",
           "receipts_open", "parse_lines", "balance", "lots_fifo"]
