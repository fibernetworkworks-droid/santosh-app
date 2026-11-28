"""Levies on construction (a base, a rate row with its source, a due date, a receipt) and tax withheld from contractor payments
(the rate by the subcontractor's status at that date, the limits counted across the year), and the filing calendar.

A rule is HER row: taken from the country pack (a checked row in one tap; a 'check this' row only when a person writes the
source, the rate and their name) or written by her. A rule past its review date refuses to work until it is checked again.
Hoola pays no levy and files no return: it works the numbers out and records her receipt."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from ..db import session
from . import packs as P
from .core import LOCK, LabourError, S, day_of, employer_id, last4, need_who, num, settings, site_id, site_names, tables, today
from .models import LdEmployer, LdFiling, LdLevy, LdPayment, LdRule

BASES = ("cost_of_work", "gross_wages", "per_head", "per_permit")


def _view(r: LdRule, t0: str) -> dict[str, Any]:
    return {"id": r.id, "kind": r.kind, "name": r.name, "region": r.region, "base": r.base, "rate_pct": r.rate_pct, "per_unit": r.per_unit, "rates": r.rates,
            "limits": r.limits, "due": r.due, "source": r.source, "checked_by": r.checked_by, "checked_on": r.checked_on, "review_by": r.review_by,
            "stale": bool(r.review_by) and r.review_by < t0, "pack_id": r.pack_id, "active": r.active}


def rules(tenant: str, kind: str = "") -> list[dict[str, Any]]:
    tables()
    t0 = today(tenant).isoformat()
    with session() as s:
        q = select(LdRule).where(LdRule.tenant_id == tenant, LdRule.active.is_(True))
        if kind:
            q = q.where(LdRule.kind == kind)
        return [_view(r, t0) for r in s.scalars(q).all()]


def use_pack(tenant: str, pack_id: str, who: str, source: str = "", rate_pct: Any = None, per_unit: Any = None, rates: Any = None) -> dict[str, Any]:
    """Make a pack row hers. A row marked 'check this' needs the source she checked, the rate if the pack gives none, and her name."""
    tables()
    who = need_who(who, "checking the rule")
    row = P.row(S(pack_id, 40))
    if row is None or row not in (P.LEVIES + P.WITHHOLD):
        raise LabourError("No levy or withholding row with that id in the country pack.")
    src = S(source, 300)
    if row["check"] and not src:
        raise LabourError(f"'{row['name']}' is marked check this: write the source you checked it against (the notification, the act, the board's page).")
    t0 = today(tenant)
    kind = "levy" if row in P.LEVIES else "withholding"
    r = LdRule(tenant_id=tenant, kind=kind, name=row["name"], region=S(row.get("region"), 40), source=src or row["source"], checked_by=who,
               checked_on=t0.isoformat(), review_by=(t0 + timedelta(days=365)).isoformat(), pack_id=row["id"], due=dict(row.get("due") or {}))
    if kind == "levy":
        r.base = row["base"]
        x = row.get("rate_pct")
        if rate_pct not in (None, ""):
            x = num(rate_pct, "Rate %")
        if row["base"] in ("per_head", "per_permit"):
            u = row.get("per_unit") if per_unit in (None, "") else num(per_unit, "Amount per head / permit")
            if not u:
                raise LabourError(f"'{row['name']}': the pack gives no amount - write the amount per {row['base'][4:]} from your source.")
            r.per_unit = float(u)
        elif x in (None, 0):
            raise LabourError(f"'{row['name']}': the pack gives no rate - write the rate % from your source.")
        else:
            if float(x) > 10:
                raise LabourError("A levy rate above 10% - check the figure.")
            r.rate_pct = float(x)
    else:
        rr = dict(row["rates"])
        if isinstance(rates, dict):
            rr.update({S(k, 14): num(v, f"Rate for {k}") for k, v in rates.items()})
        r.rates, r.limits = rr, dict(row.get("limits") or {})
    with LOCK, session() as s:
        for old in s.scalars(select(LdRule).where(LdRule.tenant_id == tenant, LdRule.pack_id == row["id"], LdRule.active.is_(True))).all():
            old.active = False
        s.add(r)
        s.flush()
        return {**_view(r, t0.isoformat()), "say": f"'{r.name}' is now your rule, checked by {who} (review by {r.review_by})."}


def save_rule(tenant: str, kind: str, name: str, who: str, source: str, base: str = "cost_of_work", rate_pct: Any = None, per_unit: Any = None,
              rates: Any = None, limits: Any = None, due: Any = None, region: str = "") -> dict[str, Any]:
    """Her own rule for a levy or withholding the pack does not have."""
    tables()
    who = need_who(who, "the rule")
    src = S(source, 300)
    if not src:
        raise LabourError("Write the source of the rule (the act, notification or board page).")
    if kind not in ("levy", "withholding"):
        raise LabourError("Kind: levy or withholding.")
    t0 = today(tenant)
    r = LdRule(tenant_id=tenant, kind=kind, name=S(name, 120) or kind, region=S(region, 40), source=src, checked_by=who, checked_on=t0.isoformat(),
               review_by=(t0 + timedelta(days=365)).isoformat(), due=due if isinstance(due, dict) else {"type": "days_after", "days": 30})
    if kind == "levy":
        if base not in BASES:
            raise LabourError("Base: cost_of_work, gross_wages, per_head or per_permit.")
        r.base = base
        if base in ("per_head", "per_permit"):
            r.per_unit = num(per_unit, "Amount per head / permit", allow_zero=False)
        else:
            r.rate_pct = num(rate_pct, "Rate %", allow_zero=False)
    else:
        if not isinstance(rates, dict) or not rates:
            raise LabourError("Withholding rates by status, like {'individual': 1, 'firm': 2, 'no_id': 20}.")
        r.rates = {S(k, 14): num(v, f"Rate for {k}") for k, v in rates.items()}
        r.limits = limits if isinstance(limits, dict) else {}
    with LOCK, session() as s:
        s.add(r)
        s.flush()
        return {**_view(r, t0.isoformat()), "say": f"Rule '{r.name}' saved."}


def _rule(s, tenant: str, rid: str, kind: str) -> LdRule:
    r = s.get(LdRule, rid) if rid else None
    if r is None:
        rows = s.scalars(select(LdRule).where(LdRule.tenant_id == tenant, LdRule.kind == kind, LdRule.active.is_(True))).all()
        if len(rows) == 1:
            r = rows[0]
        elif not rows:
            raise LabourError(f"No {kind} rule yet: take the row from your country pack (Levies & tax) or write your own with its source.")
        else:
            hit = [x for x in rows if x.name.lower() == S(rid, 120).lower() or x.pack_id == rid]
            if len(hit) != 1:
                raise LabourError(f"Which {kind} rule? " + ", ".join(x.name for x in rows))
            r = hit[0]
    if r.tenant_id != tenant or not r.active:
        raise LabourError("No such rule.")
    if r.review_by and r.review_by < today(tenant).isoformat():
        raise LabourError(f"'{r.name}' passed its review date ({r.review_by}): check it against the source and take it again before using it.")
    return r


def _due(r: LdRule, d: str) -> str:
    x = date.fromisoformat(d)
    rule = r.due or {}
    if rule.get("type") == "monthly":
        nm = (x.replace(day=1) + timedelta(days=32)).replace(day=1)
        if x.month == 3 and rule.get("march"):
            mm, dd = rule["march"].split("-")
            return date(x.year, int(mm), int(dd)).isoformat()
        return nm.replace(day=min(int(rule.get("day") or 7), 28)).isoformat()
    return (x + timedelta(days=int(rule.get("days") or 0))).isoformat()


def draft_levy(tenant: str, base_amount: Any, ref: str, rule: str = "", base_source: str = "", day: str = "", site: str = "", count: Any = None,
               due: str = "") -> dict[str, Any]:
    tables()
    d = day_of(day, tenant, "Bill date")
    with LOCK, session() as s:
        r = _rule(s, tenant, S(rule, 120), "levy")
        if r.base in ("per_head", "per_permit"):
            n = num(count if count not in (None, "") else base_amount, "Head / permit count", allow_zero=False)
            base, amt = n, round(n * r.per_unit, 2)
            how = f"{n:g} x {r.per_unit:,.2f} ({r.name})"
        else:
            base = num(base_amount, "Base amount", allow_zero=False)
            amt = round(base * r.rate_pct / 100, 2)
            how = f"{r.rate_pct:g}% of {base:,.2f} ({r.name})"
        due_d = day_of(due, tenant, "Due") if due else _due(r, d)
        lv = LdLevy(tenant_id=tenant, rule_id=r.id, ref=S(ref, 80) or "bill", site_id=site_id(s, tenant, site) if site else "", base_amount=base,
                    base_source=S(base_source, 200), amount=amt, day=d, due=due_d, status="due", say=f"{how}; source: {r.source}")
        s.add(lv)
        s.flush()
        return {"id": lv.id, "amount": amt, "due": due_d, "how": how, "source": r.source,
                "say": f"{r.name} on {lv.ref}: {amt:,.2f} = {how}. Due by {due_d}. Paying it is yours; record the receipt here."}


def mark_levy_paid(tenant: str, id: str, who: str, receipt: str, on: str = "") -> dict[str, Any]:
    who = need_who(who, "recording the payment")
    if not S(receipt):
        raise LabourError("The challan / receipt number (only its last 4 are kept).")
    with LOCK, session() as s:
        lv = s.get(LdLevy, id)
        if lv is None or lv.tenant_id != tenant:
            raise LabourError("No such levy row.")
        if lv.status == "paid":
            raise LabourError("Already recorded as paid.")
        lv.status, lv.receipt_last4, lv.paid_on, lv.paid_by = "paid", last4(receipt), day_of(on, tenant, "Paid on"), who
        return {"say": f"Recorded as paid on {lv.paid_on} (receipt ending {lv.receipt_last4})."}


def levies(tenant: str) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        rn = {r.id: r.name for r in s.scalars(select(LdRule).where(LdRule.tenant_id == tenant)).all()}
        sn = site_names(s, tenant)
        t0 = today(tenant).isoformat()
        return [{"id": x.id, "rule": rn.get(x.rule_id, ""), "ref": x.ref, "site": sn.get(x.site_id, ""), "base": x.base_amount, "base_source": x.base_source,
                 "amount": x.amount, "day": x.day, "due": x.due, "status": x.status, "late": x.status == "due" and x.due < t0, "receipt_last4": x.receipt_last4,
                 "paid_on": x.paid_on, "how": x.say}
                for x in sorted(s.scalars(select(LdLevy).where(LdLevy.tenant_id == tenant)).all(), key=lambda x: x.day, reverse=True)]


# ---------------------------------------------------------------- withholding
def _year_start(d: str, mmdd: str) -> str:
    x = date.fromisoformat(d)
    m, dd = (int(p) for p in (mmdd or "01-01").split("-"))
    y = x.year if (x.month, x.day) >= (m, dd) else x.year - 1
    return date(y, m, dd).isoformat()


def add_payment(tenant: str, employer: str, amount: Any, day: str = "", ref: str = "", materials: Any = None, rule: str = "") -> dict[str, Any]:
    """A payment to a subcontractor (made or about to be made): the deduction for its status at that date, the limits counted
    across the year so far. Hoola does not pay it."""
    tables()
    d = day_of(day, tenant)
    with LOCK, session() as s:
        eid = employer_id(s, tenant, employer)
        e = s.get(LdEmployer, eid)
        if e.kind == "own":
            raise LabourError("That is your own company: withholding is on payments to subcontractors.")
        r = _rule(s, tenant, S(rule, 120), "withholding")
        amt = num(amount, "Amount", allow_zero=False)
        mat = num(materials or 0, "Materials")
        lim = r.limits or {}
        base = amt - mat if lim.get("ex_materials") else amt
        why = []
        status = e.status or ""
        if not e.tax_id_ok or not e.checked_on:
            st_key = "no_id" if "no_id" in r.rates else status
            why.append("the tax id / verification is not checked on the desk" + (f" - the {r.rates.get('no_id', 0):g}% row applies until it is" if "no_id" in r.rates else ""))
        else:
            st_key = status
            why.append(f"{status} (checked {e.checked_on} by {e.checked_by})")
        if st_key not in r.rates:
            raise LabourError(f"{e.name}: set its tax status ({', '.join(k for k in r.rates if k != 'no_id')}) on Subcontractors first.")
        rate = float(r.rates[st_key])
        ys = _year_start(d, lim.get("year_start", "01-01"))
        prior = s.scalars(select(LdPayment).where(LdPayment.tenant_id == tenant, LdPayment.employer_id == eid, LdPayment.day >= ys, LdPayment.day <= d)).all()
        before = sum(p.base for p in prior)
        single, year = float(lim.get("single") or 0), float(lim.get("year") or 0)
        applies, catch = True, 0.0
        if single or year:
            over_single = single and base > single
            over_year = year and before + base > year
            applies = bool(over_single or over_year)
            if not applies:
                why.append(f"under the limits ({base:,.0f} in one payment, {before + base:,.0f} this year)")
            if over_year and year and before <= year:
                catch = sum(p.base for p in prior if p.withheld == 0)
                if catch:
                    why.append(f"the year's total crossed {year:,.0f}: includes {catch:,.2f} paid earlier this year with nothing withheld")
        held = round((base + catch) * rate / 100, 2) if applies else 0.0
        if applies:
            why.insert(0, f"{rate:g}% of {base + catch:,.2f}")
        if lim.get("ex_materials") and mat:
            why.append(f"materials {mat:,.2f} left out of the base")
        p = LdPayment(tenant_id=tenant, employer_id=eid, rule_id=r.id, ref=S(ref, 80), day=d, amount=amt, materials=mat, base=base, status=st_key,
                      rate_pct=rate if applies else 0.0, withheld=held, why="; ".join(why) + f". Rule: {r.name} ({r.source})")
        s.add(p)
        s.flush()
        return {"id": p.id, "withheld": held, "rate_pct": p.rate_pct, "base": base, "pay": round(amt - held, 2), "due": _due(r, d) if held else "",
                "why": p.why, "say": f"{e.name}: withhold {held:,.2f} ({p.why}). Pay {amt - held:,.2f}; deposit the tax by {_due(r, d) if held else '-'}."}


def payments(tenant: str, month: str = "") -> list[dict[str, Any]]:
    tables()
    with session() as s:
        en = {r.id: r.name for r in s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant)).all()}
        q = select(LdPayment).where(LdPayment.tenant_id == tenant)
        if month:
            q = q.where(LdPayment.day >= month + "-01", LdPayment.day <= month + "-31")
        return [{"id": p.id, "employer": en.get(p.employer_id, ""), "employer_id": p.employer_id, "ref": p.ref, "day": p.day, "amount": p.amount,
                 "materials": p.materials, "base": p.base, "status": p.status, "rate_pct": p.rate_pct, "withheld": p.withheld, "why": p.why,
                 "deposited": p.deposited, "receipt_last4": p.receipt_last4}
                for p in sorted(s.scalars(q).all(), key=lambda p: p.day, reverse=True)]


def mark_deposited(tenant: str, month: str, who: str, receipt: str, on: str = "") -> dict[str, Any]:
    """She deposited the month's tax withheld: record the challan for every row of that month."""
    who = need_who(who, "recording the deposit")
    if not S(receipt):
        raise LabourError("The challan / receipt number (only its last 4 are kept).")
    with LOCK, session() as s:
        rows = [p for p in s.scalars(select(LdPayment).where(LdPayment.tenant_id == tenant, LdPayment.day >= month + "-01", LdPayment.day <= month + "-31")).all()
                if p.withheld > 0 and not p.deposited]
        if not rows:
            raise LabourError(f"Nothing withheld in {month} is waiting to be deposited.")
        for p in rows:
            p.deposited, p.receipt_last4 = day_of(on, tenant, "Deposited on"), last4(receipt)
        return {"say": f"{len(rows)} row(s) of {month} recorded as deposited ({sum(p.withheld for p in rows):,.2f}, receipt ending {last4(receipt)})."}


# ---------------------------------------------------------------- the filing calendar
def calendar(tenant: str, days: int = 120) -> dict[str, Any]:
    tables()
    st = settings(tenant)
    t0 = today(tenant)
    end = t0 + timedelta(days=days)
    items = []
    for x in levies(tenant):
        if x["status"] == "due":
            items.append({"key": "levy:" + x["id"], "what": f"{x['rule']} on {x['ref']}", "due": x["due"], "amount": x["amount"], "ready": True, "kind": "pay"})
    by_m: dict[str, float] = defaultdict(float)
    for p in payments(tenant):
        if p["withheld"] and not p["deposited"]:
            by_m[p["day"][:7]] += p["withheld"]
    with session() as s:
        wr = s.scalars(select(LdRule).where(LdRule.tenant_id == tenant, LdRule.kind == "withholding", LdRule.active.is_(True))).first()
        filed = {f.key: f for f in s.scalars(select(LdFiling).where(LdFiling.tenant_id == tenant)).all()}
    for m, amt in sorted(by_m.items()):
        due = _due(wr, m + "-15") if wr else ""
        items.append({"key": "deposit:" + m, "what": f"Deposit the tax withheld in {m}", "due": due, "amount": round(amt, 2), "ready": True, "kind": "pay"})
    for r in P.pack(st["country"])["returns"]:
        if r.get("needs") == "federal":            # only on federal work: shown with the pack, not on every calendar
            continue
        since = ""
        if r.get("needs") == "withholding":        # a return of tax withheld only once she withholds, and only from then on
            if wr is None:
                continue
            since = wr.checked_on or ""
        for due, period in _dues(r, t0, end):
            if since and due < since:
                continue
            k = f"{r['id']}:{period}"
            f = filed.get(k)
            items.append({"key": k, "what": f"{r['what']} - {period}", "due": due, "kind": "file", "check": r["check"], "source": r["source"],
                          "filed": ({"by": f.filed_by, "on": f.filed_on, "ref": f.ref} if f else None), "ready": True})
    items.sort(key=lambda i: i["due"] or "9999")
    for i in items:
        i["late"] = bool(i["due"]) and i["due"] < t0.isoformat() and not i.get("filed")
        i["in_days"] = (date.fromisoformat(i["due"]) - t0).days if i["due"] else None
    return {"items": [i for i in items if not i.get("filed") or (i["due"] or "") >= t0.isoformat()], "country": st["country"]}


def _dues(r: dict[str, Any], t0: date, end: date) -> list[tuple[str, str]]:
    out = []
    if r["every"] == "month":
        m = (t0.replace(day=1) - timedelta(days=1)).replace(day=1)
        while m <= end:
            nm = (m + timedelta(days=32)).replace(day=1)
            due = nm.replace(day=min(int(r.get("day") or 1), 28))
            if t0 - timedelta(days=31) <= due <= end:
                out.append((due.isoformat(), m.strftime("%Y-%m")))
            m = nm
    elif r["every"] == "quarter":
        start_m = int(r.get("quarters_from") or "01")
        for y in (t0.year - 1, t0.year, t0.year + 1):
            for q in range(4):
                mm = (start_m - 1 + 3 * q) % 12 + 1
                yy = y + ((start_m - 1 + 3 * q) // 12)
                mmdd = r["dues"][str(q + 1)]
                due_m, due_d = (int(p) for p in mmdd.split("-"))
                end_m = (mm + 2 - 1) % 12 + 1
                end_y = yy + ((mm + 2 - 1) // 12)
                due_y = end_y if due_m > end_m else end_y + 1
                due = date(due_y, due_m, due_d)
                if t0 - timedelta(days=31) <= due <= end:
                    out.append((due.isoformat(), f"{date(yy, mm, 1).strftime('%b %Y')} to {date(end_y, end_m, 1).strftime('%b %Y')}"))
    elif r["every"] == "week":
        d = t0 - timedelta(days=t0.weekday())
        for i in range(0, 3):
            dd = d + timedelta(days=7 * i + 6)
            out.append((dd.isoformat(), f"week of {(d + timedelta(days=7 * i)).isoformat()}"))
    return out


def mark_filed(tenant: str, key: str, who: str, ref: str = "", on: str = "") -> dict[str, Any]:
    who = need_who(who, "recording the filing")
    key = S(key, 80)
    if not key:
        raise LabourError("Which filing?")
    with LOCK, session() as s:
        f = s.scalars(select(LdFiling).where(LdFiling.tenant_id == tenant, LdFiling.key == key)).first()
        if f is None:
            f = LdFiling(tenant_id=tenant, key=key)
            s.add(f)
        f.filed_by, f.filed_on, f.ref = who, day_of(on, tenant, "Filed on"), S(ref, 80)
        return {"say": f"Recorded as filed by {who} on {f.filed_on}."}
