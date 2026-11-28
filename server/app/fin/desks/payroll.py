"""F5 of docs/FINANCE_GLOBAL_PLAN.md - Payroll worldwide (employee `payroll`, tool `payroll_worldwide`), for a sole trader with one
helper up to a firm, in any country. Her payroll rules are HERS: she (or her payroll adviser) types the rates, thresholds and bands with
where they came from, and Hoola uses them exactly. A country pack rate is used only when a person has checked it; nothing in the packs is
checked yet, so today every rule comes from her settings and every output says so (D3: no payroll deduction from an unchecked rule).

  settings     country, frequency (monthly | fortnightly | weekly), source (where her rules come from), contributions
               [{name, employee_pct, employer_pct, from, upto, base gross|taxable, cap_employee, slabs}], income_tax {method annualised |
               period | flat, bands [{upto, pct}], allowance, flat_pct}, pre_tax (pension etc. taken before tax), filings [{name, every
               monthly | quarterly | yearly, due_day, due_offset_days, month}], pay_day.
  employee     add or change a person: name, pay (annual salary | per period | hourly rate), hours, pre_tax_pct, allowance (her own figure),
               tax_id (kept masked), start, leave. Removing marks them as left; their past payslips stay.
  run          a payroll for one period: per person gross, pre-tax deductions, taxable pay, income tax, each contribution (employee and
               employer side), net pay and employer cost, with the arithmetic shown; extras per person (overtime, bonus, unpaid days).
               It is a draft until she closes it; a closed period is never recalculated.
  close        she closes the period: it locks.
  payslip      one person's payslip from a run (text, every line traced to her rules).
  payments     the list her bank needs: who gets how much net, and what goes to each authority. Hoola never pays.
  filings      her filings tracker: what is due for each period from HER rules, due dates, done (with her reference) or overdue.
  done         she records a filing she made: the date and her reference. Hoola never files.
  contractors  payments to contractors in a year (her bills or rows given), per payee total against the threshold she gives, missing tax
               ids named, the rows for the information return (US 1099-NEC shape and a general layout) as CSV. She files it.

Not payroll advice, not a payroll provider. Amounts in her workspace currency, rounded half-up to the cent per line."""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L
from .. import pack as P
from ..calc import from_minor, to_minor


class PayrollError(ValueError):
    pass


NEVER_PAYS = "Hoola never pays anyone: this is the list for your bank or payroll payment, which you make."
NEVER_FILES = "Hoola does not file: you (or your payroll adviser) file on the official service; Hoola keeps the figures and the dates."
NOT_CONFIRMED = " (not confirmed - check this)"
PPY = {"monthly": 12, "fortnightly": 26, "weekly": 52}
MAX_PEOPLE = 10000                 # v0.999.171 every size: up to 10,000 people in one business (more = one business per company)


# ---- plumbing --------------------------------------------------------------------------------------------------------------

def _ws(tenant: str, ws: str) -> dict[str, Any]:
    from ..profile import ProfileError, get
    try:
        return get(tenant, ws)
    except ProfileError as e:
        raise PayrollError(str(e))


def _cfg(w: dict[str, Any]) -> dict[str, Any]:
    return dict((w.get("settings") or {}).get("payroll") or {})


def _save(tenant: str, ws: str, change) -> dict[str, Any]:
    from ... import db
    from ..models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != tenant:
            raise PayrollError("No such workspace.")
        st = json.loads(row.settings or "{}")
        cfg = st.setdefault("payroll", {})
        out = change(cfg)
        row.settings = json.dumps(st)
        s.commit()
    return out


def _cur(w: dict[str, Any]) -> str:
    return str(w.get("currency") or "USD").upper()


def _m(x: Any, cur: str, what: str) -> int:
    try:
        return to_minor(x, cur)
    except Exception:
        raise PayrollError(f"{what}: a number.")


def _u(minor: int, cur: str) -> float:
    return float(from_minor(int(minor), cur))


def _pct(minor: int, rate: Any) -> int:
    return int((Decimal(int(minor)) * Decimal(str(rate)) / 100).quantize(Decimal(1), ROUND_HALF_UP))


def _num(v: Any, what: str, lo: float = 0) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise PayrollError(f"{what}: a number.")
    if f < lo:
        raise PayrollError(f"{what}: not below {lo}.")
    return f


def _period(p: Any) -> tuple[str, str, str]:
    """YYYY-MM (monthly) or YYYY-MM-DD (the first day of a weekly / fortnightly period) -> key, start, end (end set by caller)."""
    s = str(p or "")
    if re.fullmatch(r"\d{4}-\d{2}", s):
        y, mo = int(s[:4]), int(s[5:])
        if not 1 <= mo <= 12:
            raise PayrollError("period: YYYY-MM.")
        end = date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1)
        return s, f"{s}-01", end.isoformat()
    try:
        d = date.fromisoformat(s)
    except ValueError:
        raise PayrollError("period: YYYY-MM (monthly) or the first day YYYY-MM-DD (weekly / fortnightly).")
    return s, d.isoformat(), ""


def _mask(tax_id: Any) -> str:
    t = re.sub(r"\s", "", str(tax_id or ""))
    return ("*" * max(0, len(t) - 4) + t[-4:]) if t else ""


# ---- settings ----------------------------------------------------------------------------------------------------------------

def _contrib(c: Any, i: int) -> dict[str, Any]:
    if not isinstance(c, dict) or not str(c.get("name") or "").strip():
        raise PayrollError(f"contributions[{i}]: name, employee_pct and / or employer_pct, from, upto, base gross|taxable.")
    out: dict[str, Any] = {"name": str(c["name"])[:60], "base": c.get("base") or "gross"}
    if out["base"] not in ("gross", "taxable"):
        raise PayrollError(f"contributions[{i}].base: gross | taxable.")
    for k in ("employee_pct", "employer_pct"):
        if c.get(k) is not None:
            out[k] = _num(c[k], f"contributions[{i}].{k}")
    for k in ("from", "upto", "cap_employee", "cap_employer", "only_upto"):
        if c.get(k) is not None:
            out[k] = _num(c[k], f"contributions[{i}].{k}")
    if c.get("slabs"):   # a fixed amount by pay band, e.g. a professional tax: [{upto, employee, employer}]
        sl = []
        for j, s in enumerate(c["slabs"]):
            sl.append({"upto": None if s.get("upto") is None else _num(s["upto"], f"slabs[{j}].upto"),
                       "employee": _num(s.get("employee", 0), f"slabs[{j}].employee"),
                       "employer": _num(s.get("employer", 0), f"slabs[{j}].employer")})
        out["slabs"] = sl
    if not any(k in out for k in ("employee_pct", "employer_pct", "slabs")):
        raise PayrollError(f"contributions[{i}]: give employee_pct, employer_pct or slabs.")
    return out


def _bands(b: Any, what: str) -> list[dict[str, Any]]:
    out, last = [], -1.0
    for j, x in enumerate(b or []):
        up = None if x.get("upto") in (None, "") else _num(x["upto"], f"{what}[{j}].upto")
        if up is not None and up <= last:
            raise PayrollError(f"{what}: each band's upto must be higher than the one before.")
        last = up if up is not None else last
        out.append({"upto": up, "pct": _num(x.get("pct"), f"{what}[{j}].pct")})
    return out


def save_settings(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    new: dict[str, Any] = {}
    if a.get("country"):
        new["country"] = str(a["country"]).upper()[:2]
    if a.get("frequency"):
        if a["frequency"] not in PPY:
            raise PayrollError("frequency: monthly | fortnightly | weekly.")
        new["frequency"] = a["frequency"]
    if a.get("source"):
        new["source"] = str(a["source"])[:200]
    if a.get("contributions") is not None:
        new["contributions"] = [_contrib(c, i) for i, c in enumerate(a["contributions"])][:20]
    if isinstance(a.get("income_tax"), dict):
        t = a["income_tax"]
        meth = t.get("method") or "annualised"
        if meth not in ("annualised", "period", "flat", "none"):
            raise PayrollError("income_tax.method: annualised | period | flat | none.")
        new["income_tax"] = {"method": meth, "bands": _bands(t.get("bands"), "income_tax.bands"),
                             "allowance": _num(t.get("allowance", 0), "income_tax.allowance"),
                             "flat_pct": _num(t.get("flat_pct", 0), "income_tax.flat_pct")}
        if meth in ("annualised", "period") and not new["income_tax"]["bands"]:
            raise PayrollError("income_tax.bands: the bands [{upto, pct}] (the last one with upto empty).")
    if a.get("pre_tax") is not None:
        new["pre_tax"] = [str(x)[:40] for x in a["pre_tax"]][:6]
    if a.get("filings") is not None:
        fl = []
        for i, f in enumerate(a["filings"]):
            every = f.get("every") or "monthly"
            if every not in ("monthly", "quarterly", "yearly", "per_run"):
                raise PayrollError(f"filings[{i}].every: monthly | quarterly | yearly | per_run.")
            fl.append({"name": str(f.get("name") or "filing")[:80], "every": every,
                       "due_day": int(f["due_day"]) if f.get("due_day") else None,
                       "due_offset_days": int(f["due_offset_days"]) if f.get("due_offset_days") is not None else None,
                       "month": int(f["month"]) if f.get("month") else None})
        new["filings"] = fl[:20]
    if a.get("pay_day") is not None:
        new["pay_day"] = max(1, min(31, int(a["pay_day"])))
    if not new:
        raise PayrollError("settings: country, frequency, source, contributions, income_tax, pre_tax, filings, pay_day.")
    if (new.get("contributions") or new.get("income_tax")) and not (a.get("source") or _cfg(_ws(tenant, ws)).get("source")):
        raise PayrollError("source: where these rates come from (e.g. 'my accountant, 2026-27 rates' or the official page) - "
                           "Hoola keeps it beside every payslip.")

    def ch(cfg):
        cfg.update(new)
        meta = cfg.get("rules_meta") or {}       # v0.999.169 a rule she gives herself replaces the starting-list one
        for k in list(meta):
            if ("contributions" in new and k.startswith("contribution:")) or ("income_tax" in new and k == "income_tax"):
                meta.pop(k)
        if not a.get("_keep_meta"):
            cfg["rules_meta"] = meta
        return {k: v for k, v in cfg.items() if k not in ("employees", "runs", "done", "inputs", "flow", "desk")}
    out = _save(tenant, ws, ch)
    return {"workspace": ws, "payroll": out, "says": "Your rules are used exactly as you gave them; Hoola does not check them against the law."}


def _rules(w: dict[str, Any]) -> dict[str, Any]:
    c = _cfg(w)
    open_ = [k for k, m in (c.get("rules_meta") or {}).items() if m.get("status") != "checked"]
    if open_:       # v0.999.169 a rule that came from a country starting list is used only once a person checked it
        raise PayrollError("These rules came from Hoola's starting list and nobody has checked them yet: " + ", ".join(k.split(":", 1)[-1] if k != "income_tax" else "Income tax" for k in open_[:8]) +
                           ". Check each one against its official page (Payroll > Settings > Country rules), then run.")
    if not c.get("contributions") and not c.get("income_tax"):
        cc = str(c.get("country") or (w.get("countries") or [""])[0] or "").upper()
        hint = P.peek(cc, "payroll.system") if cc else None
        raise PayrollError("Hoola has no checked payroll rates for " + (cc or "this country") + "." +
                           (f" The pack says: {hint}{NOT_CONFIRMED}." if hint else "") +
                           " Put your own rules in settings (contributions, income_tax, source) to go on.")
    return c


# ---- people ------------------------------------------------------------------------------------------------------------------

def employee(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    name = str(a.get("name") or "").strip()
    if not name:
        raise PayrollError("name: the person's name.")
    pid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "person"

    def ch(cfg):
        people = cfg.setdefault("employees", {})
        p = dict(people.get(pid) or {"name": name[:80]})
        if a.get("leave"):
            if pid not in people:
                raise PayrollError(f"No one called {name}.")
            p["left"] = str(a.get("left_on") or date.today().isoformat())[:10]
        else:
            kinds = [k for k in ("annual", "per_period", "hourly") if a.get(k) is not None]
            if len(kinds) > 1:
                raise PayrollError("pay: give one of annual, per_period, hourly.")
            if kinds:
                new = _m(a[kinds[0]], cur, kinds[0])
                if p.get("pay_minor") is not None and (p.get("pay_kind"), p.get("pay_minor")) != (kinds[0], new):
                    p.setdefault("pay_history", []).append({"on": str(a.get("from") or date.today().isoformat())[:10],
                                                            "kind": p.get("pay_kind"), "was": p.get("pay_minor"), "now": new})
                    p["pay_history"] = p["pay_history"][-24:]
                p["pay_kind"] = kinds[0]
                p["pay_minor"] = new
            if not p.get("pay_kind"):
                raise PayrollError("pay: annual (salary a year), per_period (pay each period) or hourly (rate an hour).")
            for k in ("hours", "pre_tax_pct"):
                if a.get(k) is not None:
                    p[k] = _num(a[k], k)
            if a.get("allowance") is not None:
                p["allowance"] = _num(a["allowance"], "allowance")
            if a.get("tax_id"):
                p["tax_id"] = _mask(a["tax_id"])
            for k, n in (("lang", 8), ("email", 120), ("payee_ref", 60), ("role", 80), ("code", 40), ("department", 80),
                         ("location", 80), ("company", 80), ("cost_centre", 60), ("phone", 30), ("group", 60)):   # v0.999.169 / v0.999.171
                if a.get(k) is not None:
                    v = str(a[k]).strip()[:n]
                    if k == "payee_ref" and p.get("payee_ref") and v != p["payee_ref"]:
                        p["payee_changed_on"] = date.today().isoformat()      # v0.999.171 a changed bank payee is flagged in the preview
                    p[k] = v
            if a.get("parts") is not None:                                     # v0.999.171 this person's own pay parts
                from . import payroll_flow as PF
                p["parts"] = PF.clean_parts(a["parts"], person=True)
            if a.get("numbers") is not None:
                p["numbers"] = {PF_snake(k): float(v) for k, v in dict(a["numbers"]).items() if _isnum(v)}
            if a.get("start"):
                p["start"] = str(a["start"])[:10]
            p.pop("left", None)
            if pid not in people and len(people) >= MAX_PEOPLE:
                raise PayrollError(f"Up to {MAX_PEOPLE} people in one workspace.")
        people[pid] = p
        return {"id": pid, **p}
    out = _save(tenant, ws, ch)
    return {"employee": _show(out, cur), "says": "Her tax id is kept masked. Bank details are never kept here."}


def PF_snake(k: Any) -> str:
    from .payroll_formula import snake
    return snake(k)[:40]


def _isnum(v: Any) -> bool:
    try:
        float(v)
        return not isinstance(v, bool)
    except (TypeError, ValueError):
        return False


def _show(p: dict[str, Any], cur: str) -> dict[str, Any]:
    q = dict(p)
    if "pay_minor" in q:
        q["pay"] = _u(q.pop("pay_minor"), cur)
    return q


def people(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    return {"employees": [_show({"id": k, **v}, cur) for k, v in sorted((_cfg(w).get("employees") or {}).items())]}


# ---- the run ------------------------------------------------------------------------------------------------------------------

def bands_tax(amount: int, bands: list[dict[str, Any]], cur: str) -> tuple[int, list[dict[str, Any]]]:
    """Tax on an amount (minor units) over bands whose upto is in units; each slice rounded half-up."""
    tax, lo, rows = 0, 0, []
    for b in bands:
        hi = None if b["upto"] is None else to_minor(b["upto"], cur)
        top = amount if hi is None else min(amount, hi)
        if top > lo:
            t = _pct(top - lo, b["pct"])
            rows.append({"from": _u(lo, cur), "to": _u(top, cur), "pct": b["pct"], "tax": _u(t, cur)})
            tax += t
        if hi is None or amount <= hi:
            break
        lo = hi
    return tax, rows


def _gross(p: dict[str, Any], ppy: int, x: dict[str, Any], cur: str) -> tuple[int, list[str]]:
    kind, pay = p.get("pay_kind"), int(p.get("pay_minor") or 0)
    if kind == "annual":
        base = int((Decimal(pay) / ppy).quantize(Decimal(1), ROUND_HALF_UP))
        how = [f"salary {_u(pay, cur)} / {ppy} = {_u(base, cur)}"]
    elif kind == "per_period":
        base, how = pay, [f"pay for the period {_u(pay, cur)}"]
    else:
        hrs = Decimal(str(x.get("hours", p.get("hours", 0))))
        base = int((Decimal(pay) * hrs).quantize(Decimal(1), ROUND_HALF_UP))
        how = [f"{hrs} hours x {_u(pay, cur)} = {_u(base, cur)}"]
    x["_period_pay"] = base                                        # v0.999.171 the full period's pay, for pay parts
    if x.get("_prorate") and kind != "hourly":     # v0.999.169 joined or left inside the period: calendar days worked
        w_, n_ = x["_prorate"]
        cut = base - int((Decimal(base) * w_ / n_).quantize(Decimal(1), ROUND_HALF_UP))
        base -= cut
        how.append(f"{w_} of {n_} days in the period: -{_u(cut, cur)}")
    if x.get("unpaid_days"):
        days = Decimal(str(_num(x["unpaid_days"], "unpaid_days")))
        per = Decimal(str(_num(x.get("working_days", 21 if ppy == 12 else 5 * 52 // ppy), "working_days", 1)))
        cut = int((Decimal(base) * days / per).quantize(Decimal(1), ROUND_HALF_UP))
        base -= cut
        how.append(f"less {days} unpaid of {per} working days: -{_u(cut, cur)}")
    x["_basic"] = base                                             # v0.999.171 after days not worked
    extra = 0
    for k in ("overtime", "bonus", "commission", "other_pay"):
        if x.get(k) and k not in (x.get("_used") or ()):          # v0.999.171 a pay part that names it decides it instead
            v = _m(x[k], cur, k)
            extra += v
            how.append(f"{k} {_u(v, cur)}")
    return base + extra, how


def _contribution(c: dict[str, Any], gross: int, taxable: int, cur: str) -> tuple[int, int, str]:
    if c.get("only_upto") is not None and gross > to_minor(c["only_upto"], cur):   # v0.999.169 applies only up to a pay level
        return 0, 0, f"not due: pay is above {c['only_upto']}"
    if c.get("slabs"):
        g = _u(gross, cur)
        for s in c["slabs"]:
            if s["upto"] is None or g <= s["upto"]:
                return to_minor(s["employee"], cur), to_minor(s["employer"], cur), f"fixed for pay up to {s['upto'] or 'any'}"
        return 0, 0, "no slab"
    base = gross if c.get("base", "gross") == "gross" else taxable
    lo = to_minor(c.get("from", 0), cur)
    hi = to_minor(c["upto"], cur) if c.get("upto") is not None else None
    part = max(0, (min(base, hi) if hi is not None else base) - lo)
    ee, er = _pct(part, c.get("employee_pct", 0)), _pct(part, c.get("employer_pct", 0))
    if c.get("cap_employee") is not None:
        ee = min(ee, to_minor(c["cap_employee"], cur))
    if c.get("cap_employer") is not None:
        er = min(er, to_minor(c["cap_employer"], cur))
    return ee, er, f"on {_u(part, cur)} ({c.get('base', 'gross')} between {c.get('from', 0)} and {c.get('upto', 'no limit')})"


def pay_one(rules: dict[str, Any], p: dict[str, Any], x: dict[str, Any], cur: str) -> dict[str, Any]:
    ppy = PPY[rules.get("frequency") or "monthly"]
    x = dict(x)
    x["_used"] = _used_names(rules, p)
    gross, how = _gross(p, ppy, x, cur)
    from . import payroll_flow as PF                                 # v0.999.171 pay as building blocks
    parts, add_gross, add_untaxed, add_pre, deduct, employer = PF.work_parts(rules, p, x, gross, ppy, cur)
    gross += add_gross + add_untaxed
    pre = (_pct(gross, p.get("pre_tax_pct", 0)) if p.get("pre_tax_pct") else 0) + add_pre
    taxable = gross - pre - add_untaxed
    t = rules.get("income_tax") or {"method": "none"}
    allow = to_minor(p["allowance"] if p.get("allowance") is not None else t.get("allowance", 0), cur)
    if t["method"] == "annualised":
        yearly = max(0, taxable * ppy - allow)
        ty, slices = bands_tax(yearly, t["bands"], cur)
        tax = int((Decimal(ty) / ppy).quantize(Decimal(1), ROUND_HALF_UP))
        tax_how = f"({_u(taxable, cur)} x {ppy} - allowance {_u(allow, cur)}) on your bands = {_u(ty, cur)} a year / {ppy}"
    elif t["method"] == "period":
        per = max(0, taxable - int((Decimal(allow) / ppy).quantize(Decimal(1), ROUND_HALF_UP)))
        tax, slices = bands_tax(per, t["bands"], cur)
        tax_how = f"{_u(per, cur)} on your bands for one period"
    elif t["method"] == "flat":
        tax, slices = _pct(taxable, t["flat_pct"]), []
        tax_how = f"{t['flat_pct']}% of {_u(taxable, cur)}"
    else:
        tax, slices, tax_how = 0, [], "no income tax taken here"
    cons, ee_all, er_all = [], 0, 0
    for c in rules.get("contributions") or []:
        ee, er, chow = _contribution(c, gross, taxable, cur)
        ee_all += ee
        er_all += er
        cons.append({"name": c["name"], "employee": _u(ee, cur), "employer": _u(er, cur), "how": chow,
                     "_ee": ee, "_er": er})
    net = gross - pre - tax - ee_all - deduct
    rnd = PF.round_net(rules, net, cur)
    return {"gross": gross, "pre_tax": pre, "taxable": taxable, "tax": tax, "ee": ee_all, "er": er_all + employer,
            "deductions": deduct, "rounding": rnd, "net": net + rnd,
            "cost": gross + er_all + employer, "how": how, "tax_how": tax_how, "tax_slices": slices, "contributions": cons,
            "parts": parts}


def _used_names(rules: dict[str, Any], p: dict[str, Any]) -> set[str]:
    from . import payroll_flow as PF
    return PF.used_names(rules, p)


def run_payroll(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    rules = _rules(w)
    key, start, end = _period(a.get("period"))
    freq = rules.get("frequency") or "monthly"
    if freq == "monthly" and not end:
        raise PayrollError("period: YYYY-MM for a monthly payroll.")
    if freq != "monthly":
        if end:
            raise PayrollError(f"period: the first day YYYY-MM-DD of the {freq} period.")
        end = (date.fromisoformat(start) + timedelta(days=(7 if freq == "weekly" else 14) - 1)).isoformat()
    runs = rules.get("runs") or {}
    if (runs.get(key) or {}).get("closed") and not a.get("_dry"):
        raise PayrollError(f"{key} is closed: a closed payroll is never recalculated. Run the next period, or put a correction in it.")
    rec = compute(rules, key, start, end, a.get("extras") or {}, cur, only=a.get("_only"))
    if a.get("_dry"):
        return rec

    def ch(cfg):
        rs = cfg.setdefault("runs", {})
        rs[key] = rec
        keep = 60 if len(rec["people"]) <= 1000 else 24
        for old in sorted(rs)[:-keep]:
            rs.pop(old)
        return rec
    _save(tenant, ws, ch)
    return {**rec, "says": f"Draft payroll for {key} on your rules (source: {rec['source'] or 'not given'}). Close it when it is right. "
                           + NEVER_PAYS}


def compute(rules: dict[str, Any], key: str, start: str, end: str, extras: dict[str, Any], cur: str,
            only: Any = None) -> dict[str, Any]:
    """One period worked out from her people, rules and inputs - nothing saved (a run saves it, the same-as-before test does not)."""
    from . import payroll_flow as PF
    rows, T = [], {"gross": 0, "pre_tax": 0, "tax": 0, "ee": 0, "er": 0, "deductions": 0, "net": 0, "cost": 0}
    by_con: dict[str, list[int]] = {}
    for pid, p in sorted((rules.get("employees") or {}).items()):
        if only is not None and pid not in only:
            continue
        if p.get("left") and p["left"] < start or p.get("start") and p["start"] > end:
            continue
        x = dict(extras.get(pid) or extras.get(p.get("name")) or {})
        d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
        a0 = max(d0, date.fromisoformat(p["start"])) if p.get("start") else d0
        a1 = min(d1, date.fromisoformat(p["left"])) if p.get("left") else d1
        if (a0, a1) != (d0, d1):
            x["_prorate"] = PF.days_worked(rules, d0, d1, a0, a1)
        x.setdefault("working_days", PF.period_days(rules, d0, d1))
        r = pay_one(rules, p, x, cur)
        for k in T:
            T[k] += r[k]
        for c in r["contributions"]:
            v = by_con.setdefault(c["name"], [0, 0])
            v[0] += c.pop("_ee")
            v[1] += c.pop("_er")
        rows.append({"id": pid, "name": p["name"], **{k: _u(r[k], cur) for k in T}, "pay_how": r["how"], "tax_how": r["tax_how"],
                     "tax_slices": r["tax_slices"], "contributions": r["contributions"],
                     "parts": [{**q, "amount": _u(q["amount"], cur)} for q in r["parts"]],
                     **({"rounding": _u(r["rounding"], cur)} if r["rounding"] else {}),
                     **{k: p[k] for k in ("department", "location", "company", "cost_centre", "code") if p.get(k)}})
    if not rows:
        raise PayrollError("No one to pay in this period: add people with employee first.")
    rec = {"period": key, "start": start, "end": end, "currency": cur, "people": rows, "closed": False,
           "totals": {k: _u(v, cur) for k, v in T.items()},
           "to_authorities": {"income tax": _u(T["tax"], cur), **{n: _u(v[0] + v[1], cur) for n, v in by_con.items()}},
           "source": rules.get("source", ""), "made": date.today().isoformat()}
    return rec


def _run_of(w: dict[str, Any], period: Any) -> dict[str, Any]:
    key = str(period or "")
    r = (_cfg(w).get("runs") or {}).get(key)
    if not r:
        raise PayrollError(f"No payroll for {key or '(period)'}: run it first.")
    return r


def close(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    key = str(a.get("period") or "")

    def ch(cfg):
        r = (cfg.get("runs") or {}).get(key)
        if not r:
            raise PayrollError(f"No payroll for {key}: run it first.")
        r["closed"] = True
        r["closed_on"] = date.today().isoformat()
        return {"period": key, "closed": True}
    return {**_save(tenant, ws, ch), "says": "Closed: this payroll is now fixed. " + NEVER_PAYS}


def payslip(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    r = _run_of(w, a.get("period"))
    who = str(a.get("employee") or a.get("name") or "")
    p = next((x for x in r["people"] if who and (x["id"] == who or x["name"].lower() == who.lower())), None)
    if not p:
        raise PayrollError("employee: whose payslip (their name).")
    cur = r["currency"]
    lines = [f"PAYSLIP - {p['name']} - {r['period']} ({r['start']} to {r['end']})", f"Currency: {cur}", "",
             f"Gross pay            {p['gross']:>12.2f}   " + "; ".join(p["pay_how"])]
    if p["pre_tax"]:
        lines.append(f"Before-tax deduction {-p['pre_tax']:>12.2f}")
    lines.append(f"Income tax           {-p['tax']:>12.2f}   {p['tax_how']}")
    for c in p["contributions"]:
        if c["employee"]:
            lines.append(f"{c['name'][:20]:<20} {-c['employee']:>12.2f}   {c['how']}")
    lines += [f"NET PAY              {p['net']:>12.2f}", "", "Paid by your employer on top (not taken from your pay):"]
    lines += [f"  {c['name'][:20]:<20} {c['employer']:>10.2f}" for c in p["contributions"] if c["employer"]]
    lines += ["", f"Rules: {r.get('source') or 'not given'}. " + ("Final." if r.get("closed") else "DRAFT - not yet closed.")]
    return {"payslip": "\n".join(lines), "net": p["net"], "closed": bool(r.get("closed"))}


def payments(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    r = _run_of(w, a.get("period"))
    return {"period": r["period"], "currency": r["currency"], "closed": bool(r.get("closed")),
            "to_people": [{"name": p["name"], "net": p["net"]} for p in r["people"]], "to_authorities": r["to_authorities"],
            "total_out": round(r["totals"]["net"] + sum(r["to_authorities"].values()), 2), "says": NEVER_PAYS}


# ---- filings ------------------------------------------------------------------------------------------------------------------

def _due(f: dict[str, Any], period_end: date) -> date:
    if f.get("due_offset_days") is not None:
        return period_end + timedelta(days=f["due_offset_days"])
    nxt = date(period_end.year + (period_end.month == 12), period_end.month % 12 + 1, 1)
    day = f.get("due_day") or 1
    last = (date(nxt.year + (nxt.month == 12), nxt.month % 12 + 1, 1) - timedelta(days=1)).day
    return nxt.replace(day=min(day, last))


def filings(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    c = _cfg(w)
    if not c.get("filings"):
        raise PayrollError("filings: put your filings in settings (name, every monthly | quarterly | yearly | per_run, due_day or "
                           "due_offset_days, month). Hoola does not use country deadlines nobody has checked.")
    year = int(a.get("year") or date.today().year)
    today = date.fromisoformat(str(a.get("today") or date.today().isoformat()))
    done = c.get("done") or {}
    items = []
    for f in c["filings"]:
        if f["every"] == "per_run":
            ends = [(k, date.fromisoformat(r["end"])) for k, r in sorted((c.get("runs") or {}).items()) if r["end"].startswith(str(year))]
        elif f["every"] == "monthly":
            ends = [(f"{year}-{m:02d}", date(year + (m == 12), m % 12 + 1, 1) - timedelta(days=1)) for m in range(1, 13)]
        elif f["every"] == "quarterly":
            ends = [(f"{year}-Q{q}", date(year + (q == 4), (3 * q) % 12 + 1, 1) - timedelta(days=1)) for q in range(1, 5)]
        else:
            m = f.get("month") or 12
            ends = [(str(year), date(year + (m == 12), m % 12 + 1, 1) - timedelta(days=1))]
        for k, e in ends:
            due = _due(f, e)
            d = done.get(f"{f['name']}|{k}")
            items.append({"filing": f["name"], "for": k, "due": due.isoformat(),
                          "status": "done" if d else ("overdue" if due < today else "upcoming"), **({"done": d} if d else {})})
    items.sort(key=lambda x: x["due"])
    return {"year": year, "items": items, "overdue": [x for x in items if x["status"] == "overdue"],
            "says": "Due dates from YOUR rules. " + NEVER_FILES}


def mark_done(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    name, for_ = str(a.get("filing") or ""), str(a.get("for") or "")
    if not name or not for_:
        raise PayrollError("filing and for: which filing and which period you filed.")

    def ch(cfg):
        if name not in [f["name"] for f in cfg.get("filings") or []]:
            raise PayrollError(f"No filing called {name} in your settings.")
        rec = {"on": str(a.get("on") or date.today().isoformat())[:10], "reference": str(a.get("reference") or "")[:80]}
        cfg.setdefault("done", {})[f"{name}|{for_}"] = rec
        return {"filing": name, "for": for_, **rec}
    return {**_save(tenant, ws, ch), "says": "Recorded as you filed it. " + NEVER_FILES}


# ---- contractors ---------------------------------------------------------------------------------------------------------------

def contractors(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    year = str(a.get("year") or date.today().year)
    names = {str(x).lower() for x in a.get("contractors") or []}
    rows = []
    for r in a.get("rows") or []:
        rows.append({"payee": str(r.get("payee") or "")[:120], "minor": _m(r.get("amount"), cur, "amount"),
                     "day": str(r.get("date") or "")[:10], "tax_id": _mask(r.get("tax_id")) if r.get("tax_id") else ""})
    if not rows and names:
        from .books import _db
        db, M = _db()
        with db.session() as s:
            q = s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws,
                                              M.FinInvoice.kind == "purchase", M.FinInvoice.status.in_(("open", "paid")))
            for d in q.all():
                if d.party.lower() in names and d.issue.startswith(year):
                    paid = d.paid_minor if a.get("basis", "paid") == "paid" else d.total_minor
                    rows.append({"payee": d.party, "minor": int(round(paid * (d.rate if d.currency != cur else 1))), "day": d.issue,
                                 "tax_id": ""})
    if not rows:
        raise PayrollError("rows [{payee, amount, date, tax_id}] or contractors [names of her suppliers who are contractors].")
    ids = {str(k).lower(): _mask(v) for k, v in (a.get("tax_ids") or {}).items()}
    thr = a.get("threshold")
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        if not r["day"].startswith(year):
            continue
        b = by.setdefault(r["payee"], {"payee": r["payee"], "minor": 0, "payments": 0, "tax_id": ""})
        b["minor"] += r["minor"]
        b["payments"] += 1
        b["tax_id"] = r["tax_id"] or b["tax_id"] or ids.get(r["payee"].lower(), "")
    out = []
    for b in sorted(by.values(), key=lambda x: -x["minor"]):
        over = None if thr is None else b["minor"] >= to_minor(thr, cur)
        out.append({"payee": b["payee"], "total": _u(b["minor"], cur), "payments": b["payments"], "tax_id": b["tax_id"],
                    "report": over, "missing_tax_id": not b["tax_id"]})
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(["payee", "tax_id_masked", "year", "total_paid", "currency", "payments"])
    for o in out:
        if o["report"] is not False:
            wr.writerow([o["payee"], o["tax_id"], year, f"{o['total']:.2f}", cur, o["payments"]])
    cc = str(_cfg(w).get("country") or (w.get("countries") or [""])[0]).upper()
    form = {"US": "Form 1099-NEC (nonemployee compensation)"}.get(cc, "the contractor information return in your country")
    return {"year": year, "currency": cur, "payees": out, "csv": buf.getvalue(),
            "missing_tax_ids": [o["payee"] for o in out if o["missing_tax_id"] and o["report"] is not False],
            "form": form + NOT_CONFIRMED,
            "threshold": (f"{thr} (yours)" if thr is not None else "none given: every payee is listed; give the threshold for "
                          "your form" + NOT_CONFIRMED),
            "says": NEVER_FILES}


# ---- door --------------------------------------------------------------------------------------------------------------------

ACTIONS = ("settings", "employee", "people", "run", "close", "payslip", "payments", "filings", "done", "contractors")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    if action in ("file", "submit"):
        raise L.Refused("file_as_institution", NEVER_FILES)
    ws = str(a.get("workspace") or "")
    if not ws:
        raise PayrollError("workspace: the finance workspace this payroll belongs to.")
    from . import payroll_desk as PD
    if action in PD.ACTIONS or action in PD.PF.ACTIONS:
        out = PD.run(tenant, action, ws, a, actor)
        out.setdefault("not_advice", L.NOT_ADVICE)
        return out
    f = {"settings": save_settings, "employee": employee, "people": people, "run": run_payroll, "close": close,
         "payslip": payslip, "payments": payments, "filings": filings, "done": mark_done, "contractors": contractors}
    if action not in f:
        raise PayrollError("action: " + ", ".join(ACTIONS + PD.ACTIONS))
    out = f[action](tenant, ws, a)
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
