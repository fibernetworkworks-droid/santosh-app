"""The Material Store desk: the Today view, stock, one item, and the one door every action goes through (`run`).

Actions that decide something - confirming a receipt or a slip, a quality decision, an approval, a scrap, a reversal, a recovery
decision - are a person's tap on the desk (`TAP`): the chat and the tool can draft them, never post them."""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from ..db import session
from . import counts as CT, demand as DM, issue as IS, packs as P, receive as RC, recon as RE
from .core import FIELDS as CFIELDS
from .core import (S, SdDoc, SdItem, SdLot, SdMove, StoreError, abc, balances, bring_legacy, doc_view, docs, find_item, item_view,
                   items, ledger, reorder, reverse, save_item, save_settings, save_store, settings, store_id, store_names, stores, tables,
                   today, valuation)

TAP = {"confirm_receipt", "reject_receipt", "quality", "return_vendor", "confirm_slip", "receive_transfer", "decide_indent", "approve_adjust",
       "scrap", "reverse", "decide_recovery", "invoiced"}
READS = {"today", "stock", "item", "ledger", "docs", "doc", "reorder", "shortfall", "budgets", "reconcile", "month_end", "close_out",
         "quality_queue", "transit", "holders", "held", "plan", "accuracy", "valuation", "pack", "settings", "stores", "items"}


def stock(tenant: str, store: str = "", q: str = "", only: str = "") -> dict[str, Any]:
    tables()
    st = settings(tenant)
    with session() as s:
        sid = store_id(s, tenant, store) if store else None
        its = [r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all() if r.active]
        cls = abc(s, tenant)
        bal = balances(s, tenant)
        agg: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for (i, l, stx, p, h), qty in bal.items():
            if p == "holder" or sid is None or stx == sid:
                agg[i][p] += qty
        last = {}
        for m in s.scalars(select(SdMove).where(SdMove.tenant_id == tenant).order_by(SdMove.seq.desc()).limit(20000)).all():
            last.setdefault(m.item_id, m.day)
        lots = s.scalars(select(SdLot).where(SdLot.tenant_id == tenant)).all()
        soon: dict[str, int] = {}
        for l in lots:
            if l.expires:
                try:
                    dd = (date.fromisoformat(l.expires) - today(tenant)).days
                except ValueError:
                    continue
                if any(k[1] == l.id and v > 1e-9 for k, v in bal.items()):
                    soon[l.item_id] = min(soon.get(l.item_id, 10 ** 6), dd)
        val = {r["item_id"]: r for r in valuation(s, tenant)["items"]}
        out = []
        ql = S(q, 80).lower()
        lot_refs = defaultdict(list)
        for l in lots:
            lot_refs[l.item_id].append(l.ref.lower())
        for it in its:
            if ql and ql not in it.name.lower() and ql not in (it.code or "").lower() and not any(ql in r for r in lot_refs[it.id]):
                continue
            a = agg.get(it.id, {})
            r = reorder(s, tenant, it, st)
            stale = None
            if last.get(it.id):
                stale = (today(tenant) - date.fromisoformat(last[it.id])).days
            row = {"id": it.id, "item": it.name, "code": it.code, "unit": it.unit, "class": cls.get(it.id, "C"), "category": it.category,
                   "available": round(a.get("available", 0), 3), "hold": round(a.get("hold", 0), 3), "blocked": round(a.get("blocked", 0), 3),
                   "holder": round(a.get("holder", 0), 3), "transit": round(a.get("transit", 0), 3), "rop": r["rop"],
                   "cover": round(a.get("available", 0) / r["rop"], 2) if r["rop"] else None, "value": (val.get(it.id) or {}).get("value", 0),
                   "expires_in": soon.get(it.id), "stale": stale, "below": bool(r["rop"]) and a.get("available", 0) <= r["rop"] + 1e-9}
            flags = []
            if row["below"]:
                flags.append("below reorder")
            if row["hold"]:
                flags.append("on hold")
            if row["expires_in"] is not None and row["expires_in"] <= 30:
                flags.append(f"expires in {row['expires_in']} days")
            if stale is not None and stale >= int(st["stale_days"]) and (row["available"] > 0):
                flags.append(f"no movement {stale} days")
            row["flags"] = flags
            if only == "below" and not row["below"] or only == "hold" and not row["hold"] or \
               only == "ageing" and not (row["expires_in"] is not None and row["expires_in"] <= 30) or \
               only == "stale" and not any(f.startswith("no movement") for f in flags):
                continue
            out.append(row)
        out.sort(key=lambda r: ({"A": 0, "B": 1, "C": 2}.get(r["class"], 3), -r["value"], r["item"]))
        return {"items": out, "store": store_names(s, tenant).get(sid, "All stores") if sid else "All stores", "currency": st["currency"],
                "total": round(sum(r["value"] for r in out), 2)}


def item_detail(tenant: str, item: str) -> dict[str, Any]:
    tables()
    st = settings(tenant)
    with session() as s:
        it = find_item(s, tenant, item)
        names = store_names(s, tenant)
        bal = balances(s, tenant, [it.id])
        lots = {r.id: r for r in s.scalars(select(SdLot).where(SdLot.tenant_id == tenant, SdLot.item_id == it.id)).all()}
        places, by_lot = [], defaultdict(float)
        for (i, l, stx, p, h), q in bal.items():
            places.append({"store": names.get(stx, "") if p != "holder" else "", "where": p, "holder": h, "lot": lots[l].ref if l in lots else "", "qty": q})
            by_lot[l] += q
        r = reorder(s, tenant, it, st)
        cls = abc(s, tenant).get(it.id, "C")
        d = item_view(it)
    d.update({"class": cls, "reorder": r, "places": sorted(places, key=lambda x: (x["where"], x["store"])),
              "lots": [{"id": lid, "ref": l.ref, "made": l.made, "expires": l.expires, "cert": l.cert, "received": l.received, "cost": l.cost,
                        "qty": round(by_lot.get(lid, 0), 3)} for lid, l in sorted(lots.items(), key=lambda kv: kv[1].received) if by_lot.get(lid, 0) > 1e-9],
              "ledger": ledger(tenant, it.id, limit=200), "docs_needed": P.docs_for(st["country"], it.category, it.trace, st["packs_off"]),
              "storage": P.storage_for(st["country"], it.name, st["packs_off"]), "currency": st["currency"]})
    return d


def _history(s, tenant: str, it: SdItem, days: int = 30) -> list[dict[str, Any]]:
    end = today(tenant)
    start = end - timedelta(days=days - 1)
    moves = s.scalars(select(SdMove).where(SdMove.tenant_id == tenant, SdMove.item_id == it.id).order_by(SdMove.seq)).all()
    q, out, i = 0.0, [], 0
    days_list = [(start + timedelta(days=k)).isoformat() for k in range(days)]
    pre = [m for m in moves if (m.day or "") < days_list[0]]
    for m in pre:
        q += (m.qty if m.to_pos == "available" else 0) - (m.qty if m.from_pos == "available" else 0)
    rest = [m for m in moves if (m.day or "") >= days_list[0]]
    for d in days_list:
        while i < len(rest) and (rest[i].day or "") <= d:
            m = rest[i]
            q += (m.qty if m.to_pos == "available" else 0) - (m.qty if m.from_pos == "available" else 0)
            i += 1
        out.append({"day": d, "qty": round(q, 3)})
    return out


def chart(tenant: str, item: str = "", days: int = 30, ahead: int = 14) -> dict[str, Any]:
    """On hand (available) for the last 30 days and the forecast for the next 14 from orders due and the look-ahead demand."""
    tables()
    with session() as s:
        if item:
            it = find_item(s, tenant, item)
        else:
            sf = DM.shortfall(tenant)
            pick = next((r for r in sf if r["short"]), None) or (sf[0] if sf else None)
            it = s.get(SdItem, pick["item_id"]) if pick else None
            if it is None:
                cls = abc(s, tenant)
                its = [r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all() if r.active]
                its.sort(key=lambda r: ({"A": 0, "B": 1, "C": 2}.get(cls.get(r.id, "C")), r.name))
                it = its[0] if its else None
        if it is None:
            return {}
        hist = _history(s, tenant, it, days)
        r = reorder(s, tenant, it)
        now_q = hist[-1]["qty"] if hist else 0.0
        pos = s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.kind == "po", SdDoc.status.in_(("open", "part")))).all()
        from .models import SdBudget
        dem = [b for b in s.scalars(select(SdBudget).where(SdBudget.tenant_id == tenant, SdBudget.item_id == it.id)).all() if b.need_qty > 0 and b.need_by]
        fc, q, marks = [], now_q, []
        t0 = today(tenant)
        for k in range(1, ahead + 1):
            d = (t0 + timedelta(days=k)).isoformat()
            for p in pos:
                if (p.data or {}).get("due") == d or (k == 1 and (p.data or {}).get("due", "9999") < d):
                    for y in p.lines or []:
                        if y["item_id"] == it.id and y["qty"] - y.get("received", 0) > 1e-9:
                            add = y["qty"] - y.get("received", 0)
                            q += add
                            marks.append({"day": d, "kind": "in", "qty": round(add, 3), "label": f"{p.number} +{add:g}"})
            for b in dem:
                if b.need_by == d or (k == 1 and b.need_by < d):
                    q -= b.need_qty
                    marks.append({"day": d, "kind": "need", "qty": round(b.need_qty, 3), "label": f"{b.work} -{b.need_qty:g}"})
            fc.append({"day": d, "qty": round(q, 3)})
        low = min(fc, key=lambda x: x["qty"]) if fc else None
        return {"item_id": it.id, "item": it.name, "unit": it.unit, "history": hist, "forecast": fc, "rop": r["rop"], "marks": marks,
                "lowest": low, "short": low is not None and low["qty"] < -1e-9}


def today_view(tenant: str) -> dict[str, Any]:
    tables()
    st = settings(tenant)
    t0 = today(tenant)
    needs: list[dict[str, Any]] = []
    with session() as s:
        names = store_names(s, tenant)
        val = valuation(s, tenant)
        alldocs = s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.status.in_(
            ("draft", "waiting", "transit", "short", "counting", "recount", "open", "part")))).all()
        views = [doc_view(s, d) for d in alldocs]
        n_items = len([1 for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all() if r.active])
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
    for d in views:
        k, x = d["kind"], d["data"]
        if k == "grn" and d["status"] == "draft":
            bad = x.get("bad") or 0
            short = [ln for ln in d["lines"] if ln.get("short")]
            needs.append({"say": f"Delivery {d['number']} from {d['party']}" + (f": {short[0]['item']} short of the paper" if short else "") +
                          (f" - {bad} serious check(s)" if bad else "") + " - confirm the receipt", "go": "receive/" + d["id"], "bad": bool(bad)})
        elif k == "slip" and d["status"] == "draft":
            needs.append({"say": f"{d['number']}: {x.get('item')} {x.get('qty_in')} {x.get('unit_in')} waiting to be confirmed", "go": "issue/" + d["id"]})
        elif k == "slip" and d["status"] in ("transit", "short"):
            sent = x.get("sent") or d["day"]
            days = (t0 - date.fromisoformat(sent)).days if sent else 0
            if d["status"] == "short" or days >= int(st["transit_days"]):
                needs.append({"say": f"Transfer {d['number']} to {names.get(x.get('to_store'), '')} " +
                              ("arrived short - settle the difference" if d["status"] == "short" else f"in transit for {days} days"),
                              "go": "transfers", "bad": d["status"] == "short"})
        elif k == "indent" and d["status"] == "waiting":
            b = x.get("budget") or {}
            needs.append({"say": f"Indent {d['number']} from {d['party'] or 'site'}: {x.get('item')} {x.get('qty_in')} {x.get('unit_in')}" +
                          (f" - takes {b['work']} to {b['share']:.0%} of its budget" if b.get("over") else ""), "go": "indents/" + d["id"], "bad": bool(b.get("over"))})
        elif k == "count" and d["status"] == "recount":
            needs.append({"say": f"Count {d['number']}: a recount by a third person is due", "go": "counts/" + d["id"], "bad": True})
        elif k == "adjust" and d["status"] == "waiting":
            needs.append({"say": f"{d['number']}: {x.get('item')} {x.get('qty'):+g} {x.get('unit')} from count {x.get('count')} - the {(x.get('tier') or {}).get('who', 'approver')} approves",
                          "go": "counts", "bad": abs(x.get("value") or 0) > 0})
        elif k == "po" and d["status"] in ("open", "part"):
            due = x.get("due")
            if due and due < t0.isoformat() and (t0 - date.fromisoformat(due)).days >= int(st["overdue_days"]):
                needs.append({"say": f"Order {d['number']} from {d['party']} was due {due} and is not fully here", "go": "indents", "bad": True})
    hold = RC.quality_queue(tenant)
    for h in hold:
        if h["pos"] == "hold" and (h["days"] or 0) >= int(st["hold_days"]):
            needs.append({"say": f"{h['item']} lot {h['lot'] or '-'} on quality hold for {h['days']} days", "go": "receive", "bad": False})
    sf = DM.shortfall(tenant)
    short = [r for r in sf if r["short"] and r["short"]["date"] <= (t0 + timedelta(days=14)).isoformat()]
    for r in short[:6]:
        needs.append({"say": f"{r['item']} runs {r['short']['short']:g} {r['unit']} short by {r['short']['date']} ({r['short']['work']})", "go": "indents", "bad": True})
    rl = DM.reorder_list(tenant)
    for r in [x for x in rl if x["below"]][:6]:
        needs.append({"say": f"{r['item']} is below its reorder point ({r['available']:g} of {r['rop']:g} {r['unit']})", "go": "stock/" + r["item_id"]})
    rec = RE.reconcile(tenant)
    for h in [x for x in rec["holders"] if x["excess"] > 1e-9][:4]:
        needs.append({"say": f"{h['holder']} is over the allowance on {h['item']} ({h['pct']:+.1f}% against {h['allowance']:g}%)", "go": "reconcile"})
    if not views and not n_items:
        needs.append({"say": "Set up your company, your stores and your item list to start", "go": "settings"})
    elif not st["set"]:
        needs.append({"say": "Set your country, currency and approval limits", "go": "settings"})
    coming = []
    for d in views:
        if d["kind"] == "po" and d["status"] in ("open", "part"):
            for y in d["lines"]:
                left = y["qty"] - y.get("received", 0)
                if left > 1e-9:
                    coming.append({"due": d["data"].get("due") or "", "po": d["number"], "supplier": d["party"], "item": y["item"], "qty": round(left, 3),
                                   "unit": y["unit"], "late": bool(d["data"].get("due")) and d["data"]["due"] < t0.isoformat()})
    coming.sort(key=lambda c: c["due"] or "9999")
    need14 = 0.0
    from .demand import budgets as _bud
    for b in _bud(tenant):
        if b["need_qty"] and b["need_by"] and b["need_by"] <= (t0 + timedelta(days=14)).isoformat():
            need14 += b["need_qty"] * ((its.get(b["item_id"]).price if its.get(b["item_id"]) else 0) or 0)
    me = RE.month_end(tenant)
    acc = CT.accuracy(tenant)
    due_today = [c for c in coming if c["due"] == t0.isoformat()]
    rec_today = [d for d in docs(tenant, "grn") if d["day"] == t0.isoformat()]
    return {"settings": st, "stores": stores(tenant), "items": n_items, "value": val["total"], "currency": st["currency"], "method": val["method"],
            "unpriced": val["unpriced"], "need14": round(need14, 2), "short": [{"item": r["item"], "short": r["short"], "unit": r["unit"]} for r in short],
            "needs": needs[:20], "coming": coming[:12], "chart": chart(tenant),
            "tiles": {"due_today": len(due_today), "received_today": len(rec_today), "on_hold": len([h for h in hold if h["pos"] == "hold"]),
                      "hold_lots": [f"{h['item']} {h['lot']}".strip() for h in hold if h["pos"] == "hold"][:3], "wastage": me["wastage_pct"],
                      "allowance": st["wastage"], "accuracy": acc["accuracy"], "count_lines": acc["lines"]},
            "counts": {"receive": sum(1 for d in views if d["kind"] == "grn" and d["status"] == "draft"),
                       "transfers": sum(1 for d in views if d["kind"] == "slip" and d["status"] in ("transit", "short")),
                       "indents": sum(1 for d in views if d["kind"] == "indent" and d["status"] == "waiting"),
                       "counts": sum(1 for d in views if (d["kind"] == "count" and d["status"] in ("counting", "recount")) or (d["kind"] == "adjust" and d["status"] == "waiting")),
                       "issue": sum(1 for d in views if d["kind"] == "slip" and d["status"] == "draft")},
            "serious": sum(1 for n in needs if n.get("bad"))}


def import_items(tenant: str, text: str) -> dict[str, Any]:
    """Her item list as CSV: name, unit, code, category, min, max, lead_days, price, trace, inspect, conv (like 'bag=50')."""
    rows = list(csv.DictReader(io.StringIO(str(text or "")[:2_000_000])))
    if not rows:
        raise StoreError("Paste a CSV with at least: name, unit.")
    ok, bad = 0, []
    have = {r["name"].lower(): r["id"] for r in items(tenant, True)}
    for i, r in enumerate(rows[:5000], 2):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        try:
            conv = {}
            for part in (r.get("conv") or "").split(";"):
                if "=" in part:
                    a, b = part.split("=", 1)
                    conv[a.strip()] = b.strip()
            f = {"name": r.get("name") or r.get("item"), "unit": r.get("unit") or None, "code": r.get("code") or None,
                 "category": r.get("category") or None, "min_qty": r.get("min") or r.get("min_qty") or None, "max_qty": r.get("max") or r.get("max_qty") or None,
                 "lead_days": r.get("lead_days") or None, "price": r.get("price") or r.get("rate") or None, "trace": r.get("trace") or None,
                 "inspect": (r.get("inspect", "").lower() in ("yes", "y", "true", "1")) if r.get("inspect") else None, "conv": conv or None}
            nm = S(f["name"], 120).lower()
            if nm in have:
                f["id"] = have[nm]
                f.pop("name")
            elif not f.get("unit"):
                raise StoreError("give its unit")
            save_item(tenant, **{k: v for k, v in f.items() if v is not None})
            ok += 1
        except StoreError as e:
            bad.append(f"line {i}: {e}")
    return {"saved": ok, "errors": bad[:30], "say": f"{ok} item(s) saved" + (f", {len(bad)} refused" if bad else "") + "."}


def run(tenant: str, part: str, a: dict[str, Any], actor: str = "desk") -> Any:
    """The one door. `actor` 'tool' (the chat) cannot take a TAP action: it drafts, a person posts."""
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    if actor != "desk" and part in TAP:
        raise PermissionError(f"'{part}' is a person's decision on the desk (with their name). Hoola drafts it; it does not post it.")
    g = lambda k: a.get(k)   # noqa: E731
    gs = lambda k: S(a.get(k), 300)   # noqa: E731
    if part in ("today",):
        bring_legacy(tenant)
    f = {
        "today": lambda: today_view(tenant),
        "settings": lambda: settings(tenant),
        "save_settings": lambda: save_settings(tenant, **{k: v for k, v in a.items() if k in CFIELDS}),
        "stores": lambda: {"stores": stores(tenant, True)},
        "save_store": lambda: save_store(tenant, gs("name"), gs("project"), gs("kind") or "main", gs("id"), g("active")),
        "items": lambda: {"items": items(tenant, bool(g("all")))},
        "save_item": lambda: save_item(tenant, **{k: v for k, v in a.items()}),
        "import_items": lambda: import_items(tenant, g("text") or ""),
        "stock": lambda: stock(tenant, gs("store"), gs("q"), gs("only")),
        "item": lambda: item_detail(tenant, gs("item") or gs("id")),
        "ledger": lambda: {"rows": ledger(tenant, gs("item"), gs("store"), int(g("limit") or 200))},
        "valuation": lambda: _val(tenant, gs("method")),
        "reorder": lambda: {"rows": DM.reorder_list(tenant)},
        "shortfall": lambda: {"rows": DM.shortfall(tenant)},
        "chart": lambda: chart(tenant, gs("item")),
        "pack": lambda: P.pack(settings(tenant)["country"]),
        # receiving
        "save_po": lambda: RC.save_po(tenant, gs("number"), gs("supplier"), g("lines") or [], gs("due"), gs("store"), gs("note"), gs("id")),
        "draft_receipt": lambda: RC.draft_receipt(tenant, gs("supplier"), g("lines") or (RC.parse_lines(g("text")) if g("text") else []), gs("store"),
                                                  gs("doc_no"), gs("doc_date"), gs("vehicle"), gs("po"), gs("who"), gs("driver"), gs("note"),
                                                  g("photos") or [], gs("id"), gs("read_from")),
        "confirm_receipt": lambda: RC.confirm_receipt(tenant, gs("id"), gs("who")),
        "reject_receipt": lambda: RC.reject_receipt(tenant, gs("id"), gs("who"), gs("reason")),
        "invoiced": lambda: RC.mark_invoiced(tenant, gs("id"), gs("invoice")),
        "quality_queue": lambda: {"rows": RC.quality_queue(tenant)},
        "quality": lambda: RC.quality(tenant, gs("decision"), gs("lot"), gs("who"), gs("store"), g("qty"), gs("note"), gs("cert")),
        "return_vendor": lambda: RC.return_vendor(tenant, gs("lot"), gs("who"), g("qty"), gs("store"), gs("reason")),
        # issue, returns, transfers, holders
        "draft_slip": lambda: IS.draft_slip(tenant, gs("type") or "issue", gs("item"), g("qty"), gs("unit"), gs("store"), gs("to_store"), gs("work"),
                                            gs("holder"), gs("person"), gs("who"), gs("note"), gs("from_holder"), gs("id")),
        "confirm_slip": lambda: IS.confirm_slip(tenant, gs("id"), gs("who")),
        "cancel_slip": lambda: IS.cancel_slip(tenant, gs("id"), gs("who")),
        "receive_transfer": lambda: IS.receive_transfer(tenant, gs("id"), gs("who"), g("qty")),
        "transit": lambda: {"rows": IS.transit(tenant)},
        "holders": lambda: {"rows": IS.holders(tenant)},
        "save_holder": lambda: IS.save_holder(tenant, gs("name"), g("allowance"), g("rates"), g("uplift"), gs("clause"), gs("id")),
        "held": lambda: {"rows": IS.held_by(tenant)},
        # demand
        "budgets": lambda: {"rows": DM.budgets(tenant, gs("work"))},
        "save_budget": lambda: DM.save_budget(tenant, gs("work"), gs("item"), g("qty"), gs("unit"), gs("name"), g("allowance"), g("done"), g("unused"),
                                              gs("need_by"), g("need_qty"), gs("source")),
        "import_budgets": lambda: DM.import_budgets(tenant, g("text") or "", gs("source")),
        "progress": lambda: DM.progress(tenant, gs("work"), g("done"), g("unused")),
        "delete_budget": lambda: DM.delete_budget(tenant, gs("id")),
        "draft_indent": lambda: DM.draft_indent(tenant, gs("item"), g("qty"), gs("unit"), gs("work"), gs("need_by"), gs("store"), gs("by"), gs("note")),
        "decide_indent": lambda: DM.decide_indent(tenant, gs("id"), gs("decision"), gs("who"), gs("note")),
        # counts
        "plan": lambda: {"rows": CT.plan(tenant)},
        "open_count": lambda: CT.open_count(tenant, gs("store"), g("items"), g("counters")),
        "enter_count": lambda: CT.enter(tenant, gs("id"), gs("who"), g("counts") or {}),
        "recounter": lambda: CT.recounter(tenant, gs("id"), gs("who")),
        "approve_adjust": lambda: CT.approve_adjust(tenant, gs("id"), gs("who"), gs("role"), gs("reason"), gs("decision") or "approve"),
        "accuracy": lambda: CT.accuracy(tenant),
        # reconcile and month-end
        "reconcile": lambda: RE.reconcile(tenant, gs("item")),
        "draft_recovery": lambda: RE.draft_recovery(tenant, gs("holder"), gs("item"), gs("who")),
        "decide_recovery": lambda: RE.decide_recovery(tenant, gs("id"), gs("decision"), gs("who"), gs("note")),
        "scrap": lambda: RE.scrap(tenant, gs("item"), g("qty"), gs("who"), gs("role"), gs("reason"), gs("store"), gs("unit"), g("sale_value"), gs("buyer"),
                                  bool(g("from_blocked"))),
        "month_end": lambda: RE.month_end(tenant, gs("month")),
        "close_out": lambda: RE.close_out(tenant, gs("store")),
        "reverse": lambda: reverse(tenant, gs("id"), gs("who"), gs("reason")),
        "docs": lambda: {"rows": docs(tenant, gs("kind"), gs("status"))},
        "doc": lambda: _doc(tenant, gs("id")),
    }.get(part)
    if f is None:
        raise StoreError(f"'{part}' is not a store action.")
    return f()


def _val(tenant: str, method: str) -> dict[str, Any]:
    with session() as s:
        return valuation(s, tenant, method or None)


def _doc(tenant: str, id: str) -> dict[str, Any]:
    from .core import get_doc
    from .counts import _view
    with session() as s:
        d = get_doc(s, tenant, id)
        return _view(s, d) if d.kind == "count" else doc_view(s, d)
