"""The sums for the jobs whose work IS arithmetic.

`tpm.py` proved the shape: when a question has exactly one right answer, the answer belongs in code and not in a
prompt, because a wrong number looks exactly as confident as a right one. Four more jobs are like that.

    supply_opt   when to reorder, how much, what is dead, what runs out when
    plm          what a part is used in, what an assembly costs, what a change hits
    bank_int     which statement lines matched the ledger and which did not
    regtech      what is due, what is late, what it could cost

Each one refuses rather than guesses when the data cannot answer the question - a reorder point computed from
three days of history is not a reorder point, and saying so is the useful answer.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

MAX_ROWS = 20000


class CalcError(Exception):
    pass


def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _n(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _day(v: Any) -> date | None:
    s = _s(v)[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date() if s else None
    except ValueError:
        return None


def _rows(rows: Any, what: str) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise CalcError(f"Rows are needed for {what}.")
    if len(rows) > MAX_ROWS:
        raise CalcError(f"No more than {MAX_ROWS} rows.")
    out = [r for r in rows if isinstance(r, dict)]
    if not out:
        raise CalcError("Every row must be an object.")
    return out


def _rupee(paise: float) -> float:
    return round(paise / 100, 2)


# ================================================================ supply_opt
#: a reorder point from too little history is a guess wearing a number's clothes
MIN_HISTORY_DAYS = 14
Z = {80: 0.84, 85: 1.04, 90: 1.28, 95: 1.65, 97: 1.88, 99: 2.33}


def reorder(rows: list[dict[str, Any]], service_level: int = 95, days_of_history: int = 0) -> dict[str, Any]:
    """rows: sku, sold (in the window), on_hand, lead_days, unit_cost, [sold_daily [..]] for variation.

    Safety stock = Z x sigma x sqrt(lead). Without daily numbers there is no sigma, so the answer says it used a
    flat fraction instead of inventing a distribution.
    """
    items = _rows(rows, "reorder")
    hist = int(days_of_history or 0)
    if hist and hist < MIN_HISTORY_DAYS:
        raise CalcError(f"{hist} days of history is not enough ({MIN_HISTORY_DAYS} days needed) - "
                        "a reorder point from this would not be reliable.")
    z = Z.get(int(service_level), 1.65)
    out, warn = [], []
    for r in items:
        sku = _s(r.get("sku") or r.get("id"))
        if not sku:
            raise CalcError("Every row needs an sku.")
        window = max(1.0, _n(r.get("days") or hist, 30))
        sold = max(0.0, _n(r.get("sold")))
        per_day = sold / window
        lead = max(0.0, _n(r.get("lead_days"), 7))
        daily = [_n(x) for x in (r.get("sold_daily") or []) if x not in (None, "")]
        if len(daily) >= MIN_HISTORY_DAYS:
            mean = sum(daily) / len(daily)
            var = sum((d - mean) ** 2 for d in daily) / (len(daily) - 1)
            sigma = math.sqrt(var)
            safety = z * sigma * math.sqrt(lead)
            how = "from daily numbers"
        else:
            safety = 0.5 * per_day * lead          # a flat half-lead cushion, stated as such
            how = "no daily numbers - half the lead time used"
            warn.append(sku)
        rop = per_day * lead + safety
        on_hand = _n(r.get("on_hand"))
        days_left = (on_hand / per_day) if per_day > 0 else None
        out.append({"sku": sku, "roz_bikta": round(per_day, 3), "lead_din": lead,
                    "safety": round(safety, 2), "reorder_point": round(rop, 2),
                    "abhi_hai": on_hand, "mangwana_hai": on_hand <= rop,
                    "kitne_din_chalega": round(days_left, 1) if days_left is not None else None,
                    "khatm_hone_ki_tareekh": (date.today() + timedelta(days=int(days_left))).isoformat()
                    if days_left is not None and days_left < 400 else None,
                    "safety_kaise": how})
    need = [x for x in out if x["mangwana_hai"]]
    return {"saman": sorted(out, key=lambda x: (x["kitne_din_chalega"] is None, x["kitne_din_chalega"])),
            "abhi_mangwaiye": need, "service_level": service_level,
            "note": (f"{len(need)} items are at or below the reorder point."
                     + (f" {len(warn)} had no daily numbers." if warn else ""))}


def dead_stock(rows: list[dict[str, Any]], days: int = 90) -> dict[str, Any]:
    """What the money is sitting in. rows: sku, on_hand, unit_cost, last_sold, sold."""
    items = _rows(rows, "dead stock")
    t = date.today()
    dead, slow, total = [], [], 0.0
    for r in items:
        sku = _s(r.get("sku") or r.get("id"))
        val = _n(r.get("on_hand")) * _n(r.get("unit_cost"))
        total += val
        last = _day(r.get("last_sold"))
        quiet = (t - last).days if last else None
        row = {"sku": sku, "abhi_hai": _n(r.get("on_hand")), "paisa_phansa": round(val, 2),
               "aakhri_bikri": _s(r.get("last_sold"))[:10], "chup_din": quiet}
        if (quiet is not None and quiet >= days) or (last is None and _n(r.get("sold")) == 0):
            dead.append(row)
        elif quiet is not None and quiet >= days // 2:
            slow.append(row)
    dead.sort(key=lambda x: -x["paisa_phansa"])
    return {"mara_hua": dead, "dheema": slow,
            "mare_hue_mein_paisa": round(sum(x["paisa_phansa"] for x in dead), 2),
            "kul_stock_ka_paisa": round(total, 2),
            "note": (f"{len(dead)} items have not sold in {days} days." if dead else "Everything is moving.")}


# ================================================================ plm
def bom_explode(rows: list[dict[str, Any]], top: str, qty: float = 1.0, max_depth: int = 20) -> dict[str, Any]:
    """rows: parent, child, qty [, unit_cost]. Flattens the tree and rolls the cost up from the leaves.

    A loop in a BOM (a part inside itself) is refused, like a dependency cycle: there is no right number for it.
    """
    items = _rows(rows, "BOM")
    kids: dict[str, list[tuple[str, float]]] = {}
    cost: dict[str, float] = {}
    for r in items:
        p, c = _s(r.get("parent")), _s(r.get("child"))
        if not p or not c:
            raise CalcError("Every row needs a parent and a child.")
        kids.setdefault(p, []).append((c, _n(r.get("qty"), 1)))
        if r.get("unit_cost") not in (None, ""):
            cost[c] = _n(r.get("unit_cost"))
        if r.get("parent_cost") not in (None, ""):
            cost[p] = _n(r.get("parent_cost"))
    top = _s(top)
    if top not in kids and top not in cost:
        raise CalcError(f"'{top}' not found in the BOM.")
    flat: dict[str, float] = {}
    lines: list[dict[str, Any]] = []

    def walk(node: str, mult: float, depth: int, stack: tuple[str, ...]) -> float:
        if node in stack:
            raise CalcError("The BOM has a loop (" + " -> ".join(stack[stack.index(node):] + (node,)) +
                            ") - no cost will be true until this is fixed.")
        if depth > max_depth:
            raise CalcError(f"The BOM is deeper than {max_depth} levels - something looks wrong.")
        own = 0.0
        for child, q in kids.get(node, []):
            total_q = q * mult
            flat[child] = flat.get(child, 0.0) + total_q
            lines.append({"level": depth + 1, "part": child, "qty": round(total_q, 4)})
            own += walk(child, total_q, depth + 1, stack + (node,))
        if not kids.get(node):
            return cost.get(node, 0.0) * mult
        return own + cost.get(node, 0.0) * mult if node in cost and depth > 0 else own

    total_cost = walk(top, _n(qty, 1), 0, ())
    missing = sorted({p for p in flat if p not in cost and p not in kids})
    return {"top": top, "qty": _n(qty, 1), "lines": lines,
            "kul_parts": [{"part": k, "qty": round(v, 4)} for k, v in
                          sorted(flat.items(), key=lambda kv: -kv[1])],
            "laagat": round(total_cost, 2),
            "daam_nahi_mila": missing,
            "note": ("Parts with no price were taken as 0 - the cost shows that much lower."
                     if missing else "Every part had a price.")}


def where_used(rows: list[dict[str, Any]], part: str) -> dict[str, Any]:
    """Which assemblies a part ends up in - the question a change order really asks."""
    items = _rows(rows, "where used")
    parents: dict[str, list[str]] = {}
    for r in items:
        p, c = _s(r.get("parent")), _s(r.get("child"))
        parents.setdefault(c, []).append(p)
    part = _s(part)
    seen, order, stack = set(), [], [part]
    while stack:
        cur = stack.pop()
        for p in parents.get(cur, []):
            if p not in seen:
                seen.add(p)
                order.append({"assembly": p, "through": cur})
                stack.append(p)
    tops = [x["assembly"] for x in order if x["assembly"] not in parents]
    return {"part": part, "kahan_lagta_hai": order, "sabse_upar": sorted(set(tops)),
            "kitne": len(order),
            "note": (f"Used in {len(order)} places - a change affects all of them." if order
                     else "This part was not found in any assembly.")}


# ================================================================ bank_int
def reconcile(statement: list[dict[str, Any]], ledger: list[dict[str, Any]],
              days: int = 3, paise: bool = False) -> dict[str, Any]:
    """Match a bank statement against the books. Amount must match exactly; the date may differ by `days`.

    Matching on amount alone is how reconciliations go wrong, so a match needs amount AND a date within the
    window, and each line is used once. What did not match is the output that matters.
    """
    st = _rows(statement, "statement")
    lg = _rows(ledger, "ledger")

    def norm(rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
        out = []
        for i, r in enumerate(rows):
            amt = _n(r.get("amount"))
            if paise:
                amt = round(amt)
            out.append({"i": i, "kind": kind, "amount": round(amt, 2),
                        "date": _day(r.get("date")), "ref": _s(r.get("ref") or r.get("id"))[:60],
                        "desc": _s(r.get("desc") or r.get("narration"))[:160], "used": False})
        return out

    S, L = norm(st, "statement"), norm(lg, "ledger")
    pairs = []
    # pass 1: same reference and amount - the strongest evidence
    for s in S:
        if s["used"] or not s["ref"]:
            continue
        for l in L:
            if not l["used"] and l["ref"] and l["ref"] == s["ref"] and l["amount"] == s["amount"]:
                s["used"] = l["used"] = True
                pairs.append({"statement": s["i"], "ledger": l["i"], "amount": s["amount"], "kaise": "ref"})
                break
    # pass 2: amount plus a date inside the window
    for s in S:
        if s["used"]:
            continue
        for l in L:
            if l["used"] or l["amount"] != s["amount"]:
                continue
            if s["date"] and l["date"] and abs((s["date"] - l["date"]).days) > days:
                continue
            s["used"] = l["used"] = True
            pairs.append({"statement": s["i"], "ledger": l["i"], "amount": s["amount"], "kaise": "amount+date"})
            break
    only_bank = [{"i": s["i"], "amount": s["amount"], "date": s["date"].isoformat() if s["date"] else "",
                  "desc": s["desc"]} for s in S if not s["used"]]
    only_books = [{"i": l["i"], "amount": l["amount"], "date": l["date"].isoformat() if l["date"] else "",
                   "desc": l["desc"]} for l in L if not l["used"]]
    return {"mile": len(pairs), "jode": pairs,
            "sirf_bank_mein": only_bank, "sirf_kitaab_mein": only_books,
            "bank_ka_jod": round(sum(s["amount"] for s in S), 2),
            "kitaab_ka_jod": round(sum(l["amount"] for l in L), 2),
            "antar": round(sum(s["amount"] for s in S) - sum(l["amount"] for l in L), 2),
            "note": ("Everything matched." if not only_bank and not only_books else
                     f"{len(only_bank)} bank lines and {len(only_books)} book lines did not match - "
                     "these are what to look at.")}


# ================================================================ regtech
def due_calendar(rows: list[dict[str, Any]], today: str = "", ahead: int = 30) -> dict[str, Any]:
    """rows: name, due (YYYY-MM-DD), owner, status, penalty_per_day, penalty_flat, rule.

    Exposure is only ever computed from numbers she gave. No penalty number is invented - a filing with no
    penalty figure is listed as late with the figure left blank, because a made-up fine is worse than none.
    """
    items = _rows(rows, "calendar")
    t = _day(today) or date.today()
    late, soon, done, no_date = [], [], [], []
    exposure = 0.0
    for r in items:
        name = _s(r.get("name"))[:160]
        st = _s(r.get("status")).lower()
        d = _day(r.get("due"))
        row = {"name": name, "due": _s(r.get("due"))[:10], "owner": _s(r.get("owner")),
               "rule": _s(r.get("rule"))[:200]}
        if st in ("done", "filed", "jama", "closed"):
            done.append(row)
            continue
        if d is None:
            no_date.append(row)
            continue
        if d < t:
            od = (t - d).days
            per = _n(r.get("penalty_per_day"))
            flat = _n(r.get("penalty_flat"))
            amt = per * od + flat if (per or flat) else None
            if amt:
                exposure += amt
            late.append({**row, "kitne_din_late": od,
                         "jurmana": round(amt, 2) if amt is not None else None})
        elif (d - t).days <= ahead:
            soon.append({**row, "kitne_din_mein": (d - t).days})
    late.sort(key=lambda x: -x["kitne_din_late"])
    soon.sort(key=lambda x: x["kitne_din_mein"])
    no_fig = [x["name"] for x in late if x["jurmana"] is None]
    return {"late": late, "aane_wale": soon, "ho_gaye": done, "tareekh_nahi": no_date,
            "jurmana_jod": round(exposure, 2),
            "jurmana_pata_nahi": no_fig,
            "note": (f"{len(late)} items are late." if late else "Nothing is late.")
            + (f" {len(no_fig)} had no penalty figure given - not included in the total."
               if no_fig else "")}
