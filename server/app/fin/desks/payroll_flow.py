"""v0.999.171 PAYROLL FOR EVERY SIZE (owner: "WHEN USER HIRE A PAYROLL AI EMPLOYEE :: 1ST PAGE IS PEOPLE ( VERY SMALL , SMALL , MEDIUM ,
LARGE , BIG ) ... THEN LANDS ON DASHBOARD ... ATTACH THE EMPLOYEE ... A CONNECTOR TO SAP OR A PDF OR A RAZORPAY PAYROLL ... ALSO ATTACH
A ATTENDANCE SOFTWARE ... RUN THE PAYROL PREVIEW FOR THIS MONTH AND AI WILL SEND IT TO USER WITH PERFECT REPORT FOR APPROVAL ... WE
WANT A PERFECT GENERALIZE AI PAYROLL SYTEM" -> the design claude.ai/artifact/R6gYtFbfoHf1FHDs5AzEG4 -> "GO").

  Part 1  the size (very small 1-10 .. big 5,000+) + countries + how often; the size sets which ways to link people come first, the
          approval chain and how deep the report goes. The dashboard's steps come from the real state.
  Part 2  people, attendance and past pay linked the way they live today: Excel / CSV, PDF and photos (read by one AI call, every line
          shown back and confirmed before it is used), her Google Sheet, payroll / HR programs through Connectors (read tools only),
          her own system (the payroll key), typing them in. Attendance machine exports (punches) become days present, hours, late
          days and overtime per period. Past registers become the history.
  Part 3  pay as building blocks: each person's pay = their base pay + parts (earning / not taxed / before tax / deduction / employer
          cost), each part a short formula worked out by plain code (payroll_formula); company habits (how days are counted, rounding,
          a pay rise rule) are settings. The AI only PROPOSES parts from her papers; she saves them. The "same as before" test works out
          a month she already paid and must match every person to the cent before her first approval (or she accepts each difference).
  Part 4  "Run the preview": the month prepared, checked and reported - totals, cash needed by pay day, what changed, what to look at
          first (a bank payee that just changed, a big jump, paid with no days present, below her minimum, a negative pay, two people
          with one payee), by department / location / company for bigger sizes - in the desk, the Payroll chat and her phone.
  Part 5  the approval chain by size (prepare -> check -> approve, a different person at each step when there is a team), then the
          lock, the books, the bank files, payslips, dues, the monthly report and the history.
  Part 6  big companies: every business's payroll in one group view, totals per currency (never converted by Hoola).

Hoola never pays anyone and never files. Bank account numbers are never kept. Not payroll advice."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from . import payroll as PY
from . import payroll_formula as FX

log = logging.getLogger("santosh.payrollflow")
PayrollError = PY.PayrollError

ACTIONS = ("setup_size", "sources", "people_file", "people_text", "people_sheet", "people_sheet_read", "people_software_read",
           "import_view", "import_apply", "import_drop", "attendance_file", "history_file", "history",
           "parts", "part_save", "part_delete", "policy_save", "propose_parts", "match_test", "match_accept",
           "preview", "check_run", "report", "report_pdf", "history_report", "group_view")
READ = {"sources", "import_view", "history", "parts", "report", "report_pdf", "history_report", "group_view"}
PREP = READ | {"people_file", "people_text", "people_sheet", "people_sheet_read", "people_software_read", "import_apply", "import_drop",
               "attendance_file", "history_file", "part_save", "part_delete", "policy_save", "propose_parts", "match_test", "preview"}
OWNER_ONLY = {"setup_size", "match_accept"}

# ------------------------------------------------------------------------------------------------ Part 1: the size
SIZES = {
    "very_small": {"name": "Very small", "range": "1 – 10 people", "lo": 1, "hi": 10, "chain": ["approve"], "split": False,
                   "depth": ["people"], "sources": ["type", "photo", "excel", "pdf", "sheet"],
                   "says": "Shop, clinic, office. Usually a notebook or a sheet today."},
    "small": {"name": "Small", "range": "11 – 50 people", "lo": 11, "hi": 50, "chain": ["approve"], "split": False,
              "depth": ["people", "changes"], "sources": ["excel", "sheet", "payroll_app", "pdf", "type"],
              "says": "Often an accountant or simple payroll software."},
    "medium": {"name": "Medium", "range": "51 – 500 people", "lo": 51, "hi": 500, "chain": ["approve"], "split": True,
               "depth": ["people", "changes", "department", "location"], "sources": ["payroll_app", "excel", "sheet", "hr_system", "pdf"],
               "says": "HR person, attendance machine, payroll software."},
    "large": {"name": "Large", "range": "501 – 5,000 people", "lo": 501, "hi": 5000, "chain": ["check", "approve"], "split": True,
              "depth": ["people", "changes", "department", "location", "cost_centre"], "sources": ["hr_system", "payroll_app", "excel", "api"],
              "says": "Payroll team, SAP / Oracle / Darwinbox, several approvers."},
    "big": {"name": "Big", "range": "5,000+ people", "lo": 5001, "hi": None, "chain": ["check", "approve"], "split": True,
            "depth": ["people", "changes", "department", "location", "cost_centre", "company"],
            "sources": ["hr_system", "partner", "api", "excel"], "says": "Many countries, many companies, global payroll partners."},
}

# Where her people live today. A program listed under Connectors is read with its own READ tools only; one that is not there is
# brought in as an export file or through her own system (the payroll key) - said plainly, never pretended.
SOURCES = {
    "type": {"name": "Type them in", "kind": "type", "line": "For a few people, the quickest way."},
    "excel": {"name": "Excel or CSV", "kind": "file", "line": "Drop the file. Hoola matches the columns and shows what it understood."},
    "pdf": {"name": "PDF", "kind": "ai_file", "line": "Salary register, old payslips, offer letters. Every line read is shown back for you to confirm."},
    "photo": {"name": "Photo of the register", "kind": "ai_file", "line": "Read and shown back line by line, like a PDF."},
    "sheet": {"name": "Google Sheet", "kind": "sheet", "line": "Link once. New joiners added to the sheet come in by themselves."},
    "payroll_app": {"name": "Payroll software", "kind": "software", "line": "Read only, through Connectors.",
                    "kits": {"gusto": "Gusto", "rippling": "Rippling", "deel": "Deel", "remote": "Remote", "quickbooks": "QuickBooks Payroll",
                             "xero": "Xero Payroll", "zoho_payroll": "Zoho Payroll", "razorpay_payroll": "RazorpayX Payroll",
                             "keka": "Keka", "greythr": "greytHR", "adp": "ADP", "paychex": "Paychex"}},
    "hr_system": {"name": "HR system", "kind": "software", "line": "Your IT gives a read-only login once, in Connectors.",
                  "kits": {"workday": "Workday", "sap_successfactors": "SAP SuccessFactors", "oracle_hcm": "Oracle HCM",
                           "darwinbox": "Darwinbox", "bamboohr": "BambooHR", "personio": "Personio", "hibob": "HiBob",
                           "zoho_people": "Zoho People", "factorial": "Factorial"}},
    "partner": {"name": "Payroll partners", "kind": "file", "line": "Employer-of-record and country partners (Deel, Remote, local bureaus): their monthly export file."},
    "api": {"name": "Your own system", "kind": "api", "line": "Your system sends people and changes with a Hoola payroll key."},
}
ATTENDANCE = {
    "machine": {"name": "Attendance machine", "line": "The export file from eSSL, ZKTeco, Matrix or any machine: punches become days, hours, late days and overtime."},
    "app": {"name": "Attendance app", "line": "Keka, Zoho People, greytHR, Deputy, Jibble, Clockify - read only, through Connectors."},
    "sheet": {"name": "A sheet or a photo", "line": "Your Google Sheet of hours, or a photo of the register."},
    "none": {"name": "No attendance", "line": "Everyone is paid a fixed amount each period."},
}


def _c(tenant: str, ws: str) -> dict[str, Any]:
    return PY._cfg(PY._ws(tenant, ws))                         # noqa: SLF001


def size_of(c: dict[str, Any]) -> str:
    return str(((c.get("desk") or {}).get("size")) or "")


def size_info(c: dict[str, Any]) -> dict[str, Any]:
    return SIZES.get(size_of(c)) or SIZES["small"]


def setup_size(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    size = str(a.get("size") or "")
    if size not in SIZES:
        raise PayrollError("size: " + " | ".join(SIZES))
    countries = [str(x).upper()[:2] for x in (a.get("countries") or []) if re.fullmatch(r"[A-Za-z]{2}", str(x))][:60]
    fq = str(a.get("frequency") or "")
    if fq and fq not in PY.PPY and fq != "mixed":
        raise PayrollError("frequency: monthly | fortnightly | weekly | mixed.")
    att = str(a.get("attendance") or "")
    if att and att not in ATTENDANCE:
        raise PayrollError("attendance: " + " | ".join(ATTENDANCE))
    if countries or (fq and fq != "mixed"):
        st: dict[str, Any] = {}
        if countries:
            st["country"] = countries[0]
        if fq and fq != "mixed":
            st["frequency"] = fq
        PY.save_settings(tenant, ws, {**st, "_keep_meta": True})

    def ch(cfg):
        d = cfg.setdefault("desk", {})
        d["size"] = size
        if countries:
            d["countries"] = countries
        if fq:
            d["mixed_frequency"] = fq == "mixed"
        if att:
            d["attendance"] = att
        d.setdefault("sized_at", date.today().isoformat())
        if size in ("large", "big") and not d.get("approve_limit"):
            d["approve_limit"] = 0
        return dict(d)
    d = PY._save(tenant, ws, ch)                                # noqa: SLF001
    info = SIZES[size]
    return {"size": size, "info": info, "countries": d.get("countries") or countries, "attendance": d.get("attendance", ""),
            "says": f"Set for {info['name'].lower()} ({info['range']}). " + (
                "You approve alone." if info["chain"] == ["approve"] and not info["split"] else
                "The person who prepares a payroll does not approve it when you have a team." if info["chain"] == ["approve"] else
                "A payroll is prepared, then checked, then approved - by different people when you have a team.")}


def next_steps(tenant: str, ws: str) -> list[dict[str, Any]]:
    """The dashboard's steps, each from the real state: size, people, attendance, past pay, rules, the same-as-before test, preview."""
    from . import payroll_desk as PD
    c = _c(tenant, ws)
    d = c.get("desk") or {}
    people = [p for p in (c.get("employees") or {}).values() if not p.get("left")]
    att = d.get("attendance") or ""
    key = PD.period_of(c)["key"]
    got_att = any(i.get("source") == "attendance" or "days_present" in (i.get("values") or {})
                  for i in c.get("inputs") or [] if i.get("period") == key)
    hist = c.get("history") or {}
    meta = c.get("rules_meta") or {}
    open_rules = [k for k, m in meta.items() if m.get("status") != "checked"]
    rules_set = bool(c.get("contributions") or c.get("income_tax"))
    m = gate(c)
    fl = PD._flow(c, key)                                         # noqa: SLF001
    out = [
        {"key": "size", "name": "Size", "done": bool(size_of(c)), "say": size_info(c)["range"] if size_of(c) else "Not set"},
        {"key": "people", "name": "People linked", "done": bool(people), "say": (f"{len(people)} " + ("person" if len(people) == 1 else "people")) if people else "No one yet"},
        {"key": "attendance", "name": "Attendance", "done": att == "none" or got_att or bool(d.get("software") or (d.get("sheet") or {}).get("spreadsheet") or d.get("mail")),
         "say": "Fixed pay" if att == "none" else ("In for " + key if got_att else "Not linked yet")},
        {"key": "history", "name": "Past pay", "done": bool(hist), "say": f"{len(hist)} months read" if hist else "Optional"},
        {"key": "rules", "name": "Rules checked", "done": rules_set and not open_rules,
         "say": (f"{len(open_rules)} left" if open_rules else "All checked") if rules_set else "Not set"},
        {"key": "match", "name": "Same as before", "done": m["ok"], "say": m["say"]},
        {"key": "preview", "name": "Preview", "done": fl.get("status") in ("draft", "checked", "approved", "paid") and bool(fl.get("report")),
         "say": {"draft": "Waiting for you", "checked": "Checked", "approved": "Approved", "paid": "Paid"}.get(fl.get("status", ""), "Not yet")},
    ]
    nxt = next((s["key"] for s in out if not s["done"] and s["key"] != "history"), "")
    for s in out:
        s["now"] = s["key"] == nxt
    return out


# ------------------------------------------------------------------------------------------------ Part 3: pay as building blocks
KINDS = {"earning": "Pay (taxed)", "untaxed": "Pay (not taxed)", "pre_tax": "Taken before tax", "deduction": "Taken from pay",
         "employer": "Employer cost"}
BASE_VARS = ("basic", "period_pay", "annual_pay", "day_pay", "hour_pay", "paid_ratio", "standard_hours", "working_days",
             "hours", "overtime_hours", "days_present", "unpaid_days", "leave_days", "late_days", "night_hours", "pieces", "sales",
             "overtime", "bonus", "commission", "other_pay", "gross_so_far")
INPUT_VARS = ("hours", "overtime_hours", "days_present", "unpaid_days", "leave_days", "late_days", "night_hours", "pieces", "sales",
              "overtime", "bonus", "commission", "other_pay")
MONEY_IN = ("overtime", "bonus", "commission", "other_pay")
POLICY = {"days": ("calendar", "working", "thirty"), "week_days": (5, 6, 7), "round_net": (0, 1, 10, 100)}


def clean_parts(parts: Any, person: bool = False) -> list[dict[str, Any]]:
    out, seen = [], set()
    for i, q in enumerate(list(parts or [])[:40]):
        if not isinstance(q, dict):
            raise PayrollError(f"parts[{i}]: {{name, kind, formula}}.")
        name = str(q.get("name") or "").strip()[:60]
        key = FX.snake(name)
        if not key:
            raise PayrollError(f"parts[{i}].name: the part's name, e.g. House rent allowance.")
        if key in BASE_VARS:
            raise PayrollError(f"parts[{i}].name: '{name}' is a word Hoola already uses; call it something else.")
        if key in seen:
            raise PayrollError(f"parts[{i}].name: '{name}' is there twice.")
        seen.add(key)
        kind = str(q.get("kind") or "earning")
        if kind not in KINDS:
            raise PayrollError(f"parts[{i}].kind: " + " | ".join(KINDS))
        f = str(q.get("formula") if q.get("formula") is not None else "").strip()
        try:
            FX.parse(f)
        except FX.FormulaError as e:
            raise PayrollError(f"{name}: {e}")
        to = str(q.get("applies_to") or "all").strip()[:120]
        if not (to == "all" or re.fullmatch(r"(department|location|company|cost_centre|group|people):.+", to)):
            raise PayrollError(f"parts[{i}].applies_to: all, or department:Sales, location:Pune, company:X, group:Y, people:id1,id2.")
        pr = q.get("prorate")
        out.append({"name": name, "key": key, "kind": kind, "formula": f, "applies_to": "all" if person else to,
                    "prorate": bool(pr) if pr is not None else _is_number(f) and kind in ("earning", "untaxed"),
                    "note": str(q.get("note") or "")[:200]})
    return out


def _is_number(f: str) -> bool:
    try:
        float(f)
        return True
    except ValueError:
        return False


def _applies(q: dict[str, Any], pid: str, p: dict[str, Any]) -> bool:
    to = q.get("applies_to") or "all"
    if to == "all":
        return True
    field, _, val = to.partition(":")
    if field == "people":
        return pid in [x.strip() for x in val.split(",")]
    return str(p.get(field) or "").strip().lower() == val.strip().lower()


def parts_for(rules: dict[str, Any], p: dict[str, Any]) -> list[dict[str, Any]]:
    """The company's parts that apply to this person, with the person's own parts replacing a company part of the same name."""
    pid = str(p.get("id") or p.get("_id") or "")
    own = {q["key"]: q for q in p.get("parts") or []}
    out = [own.pop(q["key"], q) for q in rules.get("parts") or [] if _applies(q, pid, p) or q["key"] in own]
    return out + list(own.values())


def used_names(rules: dict[str, Any], p: dict[str, Any]) -> set[str]:
    used: set[str] = set()
    for q in parts_for(rules, p):
        try:
            used |= set(FX.check(q["formula"], set()))
        except FX.FormulaError:
            continue
    return used & set(MONEY_IN + ("overtime_hours",))


def known_vars(c: dict[str, Any]) -> set[str]:
    k = set(BASE_VARS)
    for q in c.get("parts") or []:
        k.add(q["key"])
    for p in (c.get("employees") or {}).values():
        k |= set((p.get("numbers") or {}).keys())
        k |= {q["key"] for q in p.get("parts") or []}
    k |= set((c.get("desk") or {}).get("input_words") or [])
    return k


def _m(v: Any, cur: str) -> Decimal:
    return PY.from_minor(int(v), cur) if not isinstance(v, Decimal) else v


def work_parts(rules: dict[str, Any], p: dict[str, Any], x: dict[str, Any], gross: int, ppy: int, cur: str):
    """Every pay part of one person for one period: (rows, taxed pay, untaxed pay, before-tax, deductions, employer cost) in minor."""
    plist = parts_for(rules, p)
    if not plist:
        return [], 0, 0, 0, 0, 0
    pol = rules.get("policy") or {}
    d = rules.get("desk") or {}
    std = Decimal(str(pol.get("standard_hours") or d.get("standard_hours") or 160))
    period_pay = _m(x.get("_period_pay", 0), cur)
    basic = _m(x.get("_basic", 0), cur)
    wd = Decimal(str(x.get("working_days") or 21))
    env: dict[str, Any] = {k: Decimal(0) for k in BASE_VARS}
    env.update({"basic": basic, "period_pay": period_pay, "annual_pay": period_pay * ppy, "standard_hours": std,
                "working_days": wd, "day_pay": period_pay / wd if wd else Decimal(0),
                "hour_pay": (_m(p.get("pay_minor", 0), cur) if p.get("pay_kind") == "hourly" else (period_pay / std if std else Decimal(0))),
                "paid_ratio": (basic / period_pay) if period_pay else Decimal(1), "gross_so_far": _m(gross, cur)})
    for k, v in x.items():
        if not str(k).startswith("_") and PY._isnum(v):                  # noqa: SLF001
            env[FX.snake(k)] = Decimal(str(v))
    for k, v in (p.get("numbers") or {}).items():
        env[FX.snake(k)] = Decimal(str(v))
    rows, tot = [], {k: 0 for k in KINDS}
    for q in plist:
        notes: list[str] = []
        try:
            val = FX.evaluate(q["formula"], env, notes)
        except FX.FormulaError as e:
            raise PayrollError(f"{p.get('name', '')}: pay part '{q['name']}': {e}")
        if q.get("prorate"):
            val = val * env["paid_ratio"]
            notes.append(f"for {(env['paid_ratio'] * 100).quantize(Decimal('0.1'))}% of the period")
        minor = PY.to_minor(val, cur)
        if minor < 0 and q["kind"] in ("earning", "untaxed"):
            notes.append("came out below zero, counted as 0")
            minor = 0
        env[q["key"]] = PY.from_minor(minor, cur)
        if q["kind"] in ("earning", "untaxed"):
            env["gross_so_far"] += env[q["key"]]
        tot[q["kind"]] += minor
        rows.append({"name": q["name"], "kind": q["kind"], "amount": minor, "formula": q["formula"], "notes": notes})
    return rows, tot["earning"], tot["untaxed"], tot["pre_tax"], tot["deduction"], tot["employer"]


def round_net(rules: dict[str, Any], net: int, cur: str) -> int:
    step = int((rules.get("policy") or {}).get("round_net") or 0)
    if not step:
        return 0
    s = PY.to_minor(step, cur)
    return int((Decimal(net) / s).quantize(Decimal(1), ROUND_HALF_UP)) * s - net if s else 0


def _work_days(d0: date, d1: date, per_week: int) -> int:
    n, d = 0, d0
    while d <= d1:
        if d.weekday() < per_week:
            n += 1
        d += timedelta(days=1)
    return n


def period_days(rules: dict[str, Any], d0: date, d1: date) -> float:
    pol = rules.get("policy") or {}
    how = pol.get("days")
    if not how:
        ppy = PY.PPY[rules.get("frequency") or "monthly"]
        return 21 if ppy == 12 else 5 * 52 // ppy                    # the engine's own default before v0.999.171
    if how == "thirty":
        return 30
    if how == "working":
        return _work_days(d0, d1, int(pol.get("week_days") or 5))
    return (d1 - d0).days + 1


def days_worked(rules: dict[str, Any], d0: date, d1: date, a0: date, a1: date) -> tuple[int, int]:
    how = (rules.get("policy") or {}).get("days")
    if how == "working":
        wk = int((rules.get("policy") or {}).get("week_days") or 5)
        return _work_days(a0, a1, wk), max(1, _work_days(d0, d1, wk))
    if how == "thirty":
        return min(30, (a1 - a0).days + 1), 30
    return (a1 - a0).days + 1, (d1 - d0).days + 1


def parts_view(tenant: str, ws: str) -> dict[str, Any]:
    c = _c(tenant, ws)
    return {"parts": c.get("parts") or [], "policy": c.get("policy") or {}, "kinds": KINDS, "words": sorted(known_vars(c)),
            "inputs": list(INPUT_VARS), "people_with_own": [{"id": k, "name": v["name"], "parts": v.get("parts")}
                                                           for k, v in (c.get("employees") or {}).items() if v.get("parts")][:200]}


def part_save(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    q = clean_parts([a])[0]
    c = _c(tenant, ws)
    unknown = FX.check(q["formula"], known_vars(c) | {q["key"]} | set(str(w) for w in (a.get("new_words") or [])))
    if unknown:
        raise PayrollError(f"{q['name']}: Hoola does not know " + ", ".join(f"`{u}`" for u in unknown) +
                           ". Use a word from the list, the name of an earlier part, or add it as an input word (a column in your sheet).")
    words = [FX.snake(w) for w in (a.get("new_words") or []) if FX.snake(w)][:20]

    def ch(cfg):
        ps = [x for x in cfg.get("parts") or [] if x["key"] != q["key"]]
        at = next((i for i, x in enumerate(cfg.get("parts") or []) if x["key"] == q["key"]), None)
        ps.insert(at if at is not None else len(ps), q)
        cfg["parts"] = ps[:60]
        if words:
            d = cfg.setdefault("desk", {})
            d["input_words"] = sorted(set(d.get("input_words") or []) | set(words))[:60]
        return q
    return {"part": PY._save(tenant, ws, ch), "says": f"{q['name']} saved. Run the same-as-before test again before you approve."}   # noqa: SLF001


def part_delete(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    key = FX.snake(a.get("name") or a.get("key"))

    def ch(cfg):
        before = len(cfg.get("parts") or [])
        cfg["parts"] = [x for x in cfg.get("parts") or [] if x["key"] != key]
        if len(cfg["parts"]) == before:
            raise PayrollError("No such part.")
        return True
    PY._save(tenant, ws, ch)                                      # noqa: SLF001
    return {"deleted": key}


def policy_save(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    new: dict[str, Any] = {}
    if a.get("days") is not None:
        if a["days"] not in POLICY["days"]:
            raise PayrollError("days: calendar | working | thirty (how days are counted when someone joins, leaves or is unpaid).")
        new["days"] = a["days"]
    if a.get("week_days") is not None:
        if int(a["week_days"]) not in POLICY["week_days"]:
            raise PayrollError("week_days: 5, 6 or 7.")
        new["week_days"] = int(a["week_days"])
    if a.get("round_net") is not None:
        if int(a["round_net"]) not in POLICY["round_net"]:
            raise PayrollError("round_net: 0 (none), 1, 10 or 100.")
        new["round_net"] = int(a["round_net"])
    for k, lo, hi in (("standard_hours", 1, 400), ("jump_pct", 1, 500), ("minimum_pay", 0, 1e9), ("shift_start_min", 0, 1439),
                      ("grace_min", 0, 240), ("day_hours", 1, 24)):
        if a.get(k) not in (None, ""):
            v = float(a[k])
            if not lo <= v <= hi:
                raise PayrollError(f"{k}: between {lo:g} and {hi:g}.")
            new[k] = v
    if a.get("shift_start"):
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", str(a["shift_start"]).strip())
        if not m:
            raise PayrollError("shift_start: HH:MM, e.g. 09:30.")
        new["shift_start_min"] = int(m.group(1)) * 60 + int(m.group(2))
    if "overtime_from_punches" in a:
        new["overtime_from_punches"] = bool(a["overtime_from_punches"])
    if not new:
        raise PayrollError("policy: days, week_days, round_net, standard_hours, jump_pct, minimum_pay, shift_start, grace_min, "
                           "day_hours, overtime_from_punches.")

    def ch(cfg):
        cfg.setdefault("policy", {}).update(new)
        return dict(cfg["policy"])
    return {"policy": PY._save(tenant, ws, ch)}                   # noqa: SLF001


# ------------------------------------------------------------------------------------------------ Part 2: linking
PALIAS = {"name": ("name", "employee name", "full name", "staff name", "employee", "emp name", "worker", "person"),
          "code": ("emp id", "employee id", "emp code", "employee code", "staff id", "id", "code", "emp no", "employee no", "worker id"),
          "annual": ("annual", "annual salary", "ctc", "yearly salary", "salary a year", "annual ctc", "ctc per annum"),
          "per_period": ("monthly salary", "salary", "monthly", "basic", "basic salary", "basic pay", "pay", "fixed pay", "wage"),
          "hourly": ("hourly", "hourly rate", "rate per hour", "rate an hour", "hour rate"),
          "department": ("department", "dept", "team", "division"), "location": ("location", "branch", "site", "office", "city"),
          "company": ("company", "entity", "legal entity", "employer"), "cost_centre": ("cost centre", "cost center", "cost code"),
          "role": ("designation", "role", "job", "title", "job title", "position"),
          "start": ("date of joining", "doj", "joining date", "start date", "start", "joined", "hire date"),
          "left": ("date of leaving", "dol", "exit date", "last day", "left", "leaving date", "termination date"),
          "email": ("email", "email id", "e-mail", "mail"), "phone": ("phone", "mobile", "mobile no", "contact"),
          "lang": ("language", "payslip language", "lang"),
          "tax_id": ("pan", "tax id", "tin", "ssn", "nin", "ni number", "tax number", "tfn", "uan"),
          "payee_ref": ("payee", "payee reference", "beneficiary", "beneficiary name", "bank payee")}
TOTALS = re.compile(r"^(total|gross|net|ctc|take home|net pay|gross pay|total earnings|total deductions|net salary|in hand|s ?no|sr ?no|serial)", re.I)
DEDUCT = re.compile(r"loan|advance|canteen|deduction|recovery|fine|penalty|uniform|emi", re.I)
STATUTORY = re.compile(r"^(pf|epf|esi|esic|pt|professional tax|tds|income tax|tax|ni|national insurance|cpf|social security|fica|"
                       r"medicare|super|superannuation|lwf)$", re.I)
LANGS = {"english": "en", "hindi": "hi", "marathi": "mr", "spanish": "es", "french": "fr", "german": "de", "portuguese": "pt"}


def _norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _num(v: Any) -> float | None:
    from .payroll_desk import _num as n
    return n(v)


def _day(v: Any) -> str:
    from .payroll_desk import _day as d
    return d(v)


def _cols(header: list[Any]) -> tuple[dict[str, int], dict[int, str]]:
    h = [_norm(x) for x in header]
    cols: dict[str, int] = {}
    for f, names in PALIAS.items():
        for i, x in enumerate(h):
            if i not in cols.values() and x in names:
                cols[f] = i
                break
    if "per_period" in cols and h[cols["per_period"]].startswith("basic"):
        cols["_basic"] = cols["per_period"]
    extra = {i: str(header[i]).strip() for i, x in enumerate(h) if x and i not in cols.values() and not TOTALS.match(x)}
    return cols, extra


def people_rows(table: list[list[Any]]) -> list[dict[str, Any]]:
    """A people table (first row = headings) -> one proposed person per row, with salary-breakup columns as their own pay parts."""
    table = [r for r in table if any(str(x or "").strip() for x in r)]
    if len(table) < 2:
        return []
    cols, extra = _cols(list(table[0]))
    if "name" not in cols:
        raise PayrollError("The file needs a column with each person's name (Name / Employee name).")
    out = []
    for n, r in enumerate(table[1:], start=2):
        g = lambda f: r[cols[f]] if f in cols and cols[f] < len(r) else None    # noqa: E731
        row: dict[str, Any] = {"line": n, "name": str(g("name") or "").strip()}
        for f in ("code", "department", "location", "company", "cost_centre", "role", "email", "phone", "tax_id", "payee_ref"):
            if g(f) not in (None, ""):
                row[f] = str(g(f)).strip()
        if g("lang"):
            lv = _norm(g("lang"))
            row["lang"] = LANGS.get(lv, lv[:2])
        for f in ("start", "left"):
            if g(f) not in (None, ""):
                row[f] = _day(g(f)) or ("?" + str(g(f))[:20])
        for f in ("annual", "per_period", "hourly"):
            if g(f) not in (None, ""):
                row["pay_kind"], row["pay"] = f, _num(g(f)) if _num(g(f)) is not None else ("?" + str(g(f))[:20])
                break
        parts = []
        for i, title in extra.items():
            v = _num(r[i]) if i < len(r) else None
            if v is None or v == 0 or STATUTORY.match(_norm(title)):
                continue
            parts.append({"name": title[:60], "kind": "deduction" if DEDUCT.search(title) else "earning", "formula": f"{v:g}"})
        if parts:
            row["parts"] = parts[:20]
        out.append(row)
    return out


def _problems(row: dict[str, Any], people: dict[str, Any], seen: dict[str, int]) -> tuple[list[str], str]:
    why: list[str] = []
    name = row.get("name") or ""
    if not name:
        why.append("no name")
    if isinstance(row.get("pay"), str):
        why.append(f"pay is not a number ({row['pay'][1:]})")
    for f in ("start", "left"):
        if str(row.get(f) or "").startswith("?"):
            why.append(f"the {f} date {row[f][1:]} could not be read")
    match = ""
    for pid, p in people.items():
        if (row.get("code") and row["code"] == p.get("code")) or (name and _norm(name) == _norm(p.get("name"))) \
                or (row.get("email") and row["email"].lower() == str(p.get("email") or "").lower()):
            match = pid
            break
    if not match and row.get("pay") in (None, "") and not row.get("parts"):
        why.append("no pay given")
    for k in ("code", "email", "payee_ref"):
        v = str(row.get(k) or "").lower()
        if v:
            if (k, v) in seen:
                why.append(f"the same {k.replace('_', ' ')} as line {seen[(k, v)]}")
            seen[(k, v)] = row.get("line", 0)
    if name and ("name", _norm(name)) in seen and not row.get("code"):
        why.append(f"the same name as line {seen[('name', _norm(name))]}")
    seen[("name", _norm(name))] = row.get("line", 0)
    for f in ("pay",):
        if isinstance(row.get(f), (int, float)) and row[f] < 0:
            why.append("pay is below zero")
    return why, match


def _import(tenant: str, ws: str, kind: str, rows: list[dict[str, Any]], source: str, file: str, ai: bool,
            period: str = "") -> dict[str, Any]:
    if not rows:
        raise PayrollError("Nothing could be read from it.")
    if len(rows) > PY.MAX_PEOPLE:
        raise PayrollError(f"Up to {PY.MAX_PEOPLE:,} rows at a time.")
    c = _c(tenant, ws)
    people = c.get("employees") or {}
    seen: dict[tuple[str, str], int] = {}
    for r in rows:
        if kind == "people":
            r["problems"], r["matches"] = _problems(r, people, seen)
            r["does"] = ("update " + people[r["matches"]]["name"]) if r["matches"] else "add"
        else:
            pid = _find(people, r)
            r["matches"] = pid
            r["problems"] = [] if pid else [f"no one called {r.get('name') or r.get('code') or '(no name)'} in your people"]
            if not r.get("period"):
                r["problems"].append("no month given")
            if r.get("gross") is None and r.get("net") is None:
                r["problems"].append("no gross or net pay")
        r["confirmed"] = not ai
    iid = "pim_" + secrets.token_hex(5)
    body = {"id": iid, "kind": kind, "source": source, "file": str(file)[:120], "ai": ai, "rows": rows, "period": period,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    body["hash"] = hashlib.sha256(json.dumps([kind, rows], sort_keys=True, default=str).encode()).hexdigest()[:16]

    def ch(cfg):
        ims = [x for x in cfg.get("imports") or [] if x["id"] != iid][-7:]
        ims.append(body)
        cfg["imports"] = ims
        return True
    PY._save(tenant, ws, ch)                                      # noqa: SLF001
    return _iview(body)


def _iview(im: dict[str, Any]) -> dict[str, Any]:
    rows = im["rows"]
    ok = [r for r in rows if not r["problems"]]
    return {"import": im["id"], "kind": im["kind"], "source": im["source"], "file": im["file"], "ai": im["ai"], "hash": im["hash"],
            "rows": rows[:2000], "count": len(rows), "ready": len(ok), "waiting": len(rows) - len(ok),
            "says": (f"Read {len(rows)} line{'s' if len(rows) != 1 else ''}: {len(ok)} ready, {len(rows) - len(ok)} need you."
                     + (" This was read by AI - confirm each line you checked before it is used." if im["ai"] else ""))}


def _find(people: dict[str, Any], r: dict[str, Any]) -> str:
    for pid, p in people.items():
        if r.get("code") and str(r["code"]) == str(p.get("code") or ""):
            return pid
    from .payroll_desk import _match
    return _match(people, str(r.get("name") or ""))[0]


def _ai_read(name: str, data: bytes, what: str) -> list[dict[str, Any]]:
    """A PDF or photo -> rows, by ONE AI call on its text. The rows are proposals; she confirms each one before it is used."""
    from .books_feed import text_of
    text, how = text_of(name, data)
    if not str(text or "").strip():
        raise PayrollError(f"No words could be read from {name} ({how}). Try a clearer scan or the Excel file.")
    got = _ask_ai(what, text)
    rows = got.get("rows") if isinstance(got, dict) else None
    if not isinstance(rows, list):
        raise PayrollError("The AI did not return the lines. Try again, or use the Excel file.")
    return [r for r in rows if isinstance(r, dict)][:PY.MAX_PEOPLE]


AI_PEOPLE = ("You read a payroll document (salary register, payslips or offer letters). Return ONLY JSON: {\"rows\": [{\"name\", \"code\", "
             "\"pay_kind\" (annual|per_period|hourly), \"pay\" (number), \"start\" (YYYY-MM-DD or \"\"), \"department\", \"location\", "
             "\"role\", \"email\", \"parts\": [{\"name\", \"kind\" (earning|deduction), \"amount\"}]}]}. One row per person. Copy only "
             "what is printed - never guess a number, use \"\" or leave it out. Leave out tax and statutory lines (PF, ESI, PT, TDS, "
             "income tax, social security) - those come from the country rules.")
AI_HISTORY = ("You read a past payroll document (register or payslips). Return ONLY JSON: {\"rows\": [{\"name\", \"code\", \"period\" "
              "(YYYY-MM), \"gross\", \"net\", \"days_present\", \"unpaid_days\", \"overtime_hours\", \"parts\": {\"part name\": amount}}]}. "
              "One row per person per month. Copy only what is printed; never guess a number.")


def _ask_ai(what: str, text: str) -> dict[str, Any]:
    import asyncio
    from .books_feed import _loose
    system = AI_PEOPLE if what == "people" else AI_HISTORY

    async def go():
        from ...agent import llm
        from ...config import get_settings
        prompt = "Document:\n<<<\n" + text[:30000] + "\n>>>\nReturn the JSON object now."
        brain = llm.cheap_brain()
        if brain:
            blocks, _, _ = await llm.openai_create(brain, system, [], [{"role": "user", "content": prompt}], 8000)
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if get_settings().anthropic_api_key:
            from ...agent import door
            from ...agent.santosh import get_client
            st = get_settings()
            msg = await door.acreate(get_client(), door.shape("write", st.anthropic_model, 8000, system, [{"role": "user", "content": prompt}]))
            return "".join(getattr(b, "text", "") for b in msg.content)
        raise PayrollError("No AI model is set up on this server, so a PDF or photo cannot be read. Use the Excel file.")
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(1) as ex:
            out = ex.submit(asyncio.run, go()).result()
    except RuntimeError:
        out = asyncio.run(go())
    return _loose(out)


def _ai_people(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for n, r in enumerate(rows, start=1):
        row: dict[str, Any] = {"line": n, "name": str(r.get("name") or "").strip()[:80]}
        for f in ("code", "department", "location", "role", "email"):
            if r.get(f):
                row[f] = str(r[f]).strip()[:80]
        if r.get("start"):
            row["start"] = _day(r["start"]) or ("?" + str(r["start"])[:20])
        if r.get("pay") not in (None, ""):
            v = _num(r["pay"])
            row["pay"] = v if v is not None else "?" + str(r["pay"])[:20]
            row["pay_kind"] = r.get("pay_kind") if r.get("pay_kind") in ("annual", "per_period", "hourly") else "per_period"
        ps = [{"name": str(q.get("name"))[:60], "kind": "deduction" if q.get("kind") == "deduction" else "earning",
               "formula": f"{_num(q.get('amount')):g}"} for q in r.get("parts") or []
              if isinstance(q, dict) and q.get("name") and _num(q.get("amount")) and not STATUTORY.match(_norm(q.get("name")))]
        if ps:
            row["parts"] = ps[:20]
        out.append(row)
    return out


def _table_of(name: str, data: bytes) -> list[list[Any]]:
    n = str(name or "").lower()
    if n.endswith((".xlsx", ".xlsm")):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        except Exception as e:   # noqa: BLE001
            raise PayrollError(f"The spreadsheet could not be read: {str(e)[:120]}")
    import csv
    text = data.decode("utf-8-sig", errors="replace")
    dialect = "excel-tab" if n.endswith(".tsv") or text.count("\t") > text.count(",") else "excel"
    return list(csv.reader(io.StringIO(text), dialect=dialect))


def _is_table(name: str) -> bool:
    return str(name or "").lower().endswith((".csv", ".xlsx", ".xlsm", ".tsv", ".txt"))


def people_file(tenant: str, ws: str, name: str, data: bytes, source: str = "excel") -> dict[str, Any]:
    if len(data) > 20 * 1024 * 1024:
        raise PayrollError("The file is over 20 MB.")
    if _is_table(name):
        return _import(tenant, ws, "people", people_rows(_table_of(name, data)), source if source in SOURCES else "excel", name, False)
    return _import(tenant, ws, "people", _ai_people(_ai_read(name, data, "people")),
                   "photo" if re.search(r"\.(png|jpe?g|webp|heic)$", name, re.I) else "pdf", name, True)


def people_text(tenant: str, ws: str, text: str) -> dict[str, Any]:
    """Pasted lines (from an email or a chat) -> proposed people, read by AI and confirmed line by line."""
    if not str(text or "").strip():
        raise PayrollError("text: the lines to read.")
    got = _ask_ai("people", str(text)[:30000]).get("rows") or []
    return _import(tenant, ws, "people", _ai_people([r for r in got if isinstance(r, dict)]), "text", "Pasted text", True)


def import_view(tenant: str, ws: str, iid: str = "") -> dict[str, Any]:
    ims = _c(tenant, ws).get("imports") or []
    if not iid:
        return {"imports": [{k: v for k, v in _iview(x).items() if k != "rows"} | {"at": x["at"]} for x in reversed(ims)]}
    im = next((x for x in ims if x["id"] == iid), None)
    if not im:
        raise PayrollError("No such import.")
    return _iview(im)


def import_drop(tenant: str, ws: str, iid: str) -> dict[str, Any]:
    def ch(cfg):
        cfg["imports"] = [x for x in cfg.get("imports") or [] if x["id"] != iid]
        return True
    PY._save(tenant, ws, ch)                                      # noqa: SLF001
    return {"dropped": iid}


def _pid_for(people: dict[str, Any], row: dict[str, Any]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", str(row["name"]).lower()).strip("-")[:40] or "person"
    if base not in people:
        return base
    if row.get("code"):
        return (base + "-" + re.sub(r"[^a-z0-9]+", "-", str(row["code"]).lower()).strip("-"))[:50]
    n = 2
    while f"{base}-{n}" in people:
        n += 1
    return f"{base}-{n}"


def _put_person(people: dict[str, Any], row: dict[str, Any], cur: str) -> str:
    pid = row.get("matches") or ""
    if pid and pid in people:
        p = people[pid]
    else:
        pid = _pid_for(people, row)
        p = {"name": str(row["name"])[:80]}
    if isinstance(row.get("pay"), (int, float)) and row.get("pay_kind"):
        new = PY._m(row["pay"], cur, "pay")                       # noqa: SLF001
        if p.get("pay_minor") is not None and (p.get("pay_kind"), p.get("pay_minor")) != (row["pay_kind"], new):
            p.setdefault("pay_history", []).append({"on": date.today().isoformat(), "kind": p.get("pay_kind"), "was": p.get("pay_minor"),
                                                    "now": new})
            p["pay_history"] = p["pay_history"][-24:]
        p["pay_kind"], p["pay_minor"] = row["pay_kind"], new
    elif not p.get("pay_kind") and row.get("parts"):
        p["pay_kind"], p["pay_minor"] = "per_period", 0
    for k, n in (("code", 40), ("department", 80), ("location", 80), ("company", 80), ("cost_centre", 60), ("role", 80),
                 ("email", 120), ("phone", 30), ("lang", 8), ("payee_ref", 60)):
        if row.get(k):
            v = str(row[k]).strip()[:n]
            if k == "payee_ref" and p.get("payee_ref") and v != p["payee_ref"]:
                p["payee_changed_on"] = date.today().isoformat()
            p[k] = v
    if row.get("tax_id"):
        p["tax_id"] = PY._mask(row["tax_id"])                     # noqa: SLF001
    if row.get("start"):
        p["start"] = row["start"]
    if row.get("left"):
        p["left"] = row["left"]
    if row.get("parts"):
        p["parts"] = clean_parts(row["parts"], person=True)
    people[pid] = p
    return pid


def import_apply(tenant: str, ws: str, a: dict[str, Any], actor: str = "") -> dict[str, Any]:
    """Her tap on the import she saw (its hash): the ready lines go in; read-by-AI lines only those she confirmed."""
    iid, h = str(a.get("import") or ""), str(a.get("hash") or "")
    lines = {int(x) for x in (a.get("lines") or []) if str(x).isdigit()}
    w = PY._ws(tenant, ws)                                        # noqa: SLF001
    cur = PY._cur(w)                                              # noqa: SLF001
    done = {"added": 0, "updated": 0, "months": 0, "skipped": 0}

    def ch(cfg):
        im = next((x for x in cfg.get("imports") or [] if x["id"] == iid), None)
        if not im:
            raise PayrollError("No such import.")
        if h != im["hash"]:
            raise PayrollError("This import changed after you looked at it. Look again, then use it.")
        if im["ai"] and not lines:
            raise PayrollError("Tick each line you checked against the document first.")
        people = cfg.setdefault("employees", {})
        for r in im["rows"]:
            if r["problems"] or (im["ai"] and r.get("line") not in lines):
                done["skipped"] += 1
                continue
            if im["kind"] == "people":
                if len(people) >= PY.MAX_PEOPLE and not r.get("matches"):
                    raise PayrollError(f"Up to {PY.MAX_PEOPLE:,} people in one business.")
                done["updated" if r.get("matches") else "added"] += 1
                _put_person(people, r, cur)
            else:
                pid = r.get("matches") or _find(people, r)
                if not pid:
                    done["skipped"] += 1
                    continue
                h_ = cfg.setdefault("history", {}).setdefault(r["period"], {})
                h_[pid] = {k: r[k] for k in ("gross", "net", "days_present", "unpaid_days", "overtime_hours", "hours", "parts")
                           if r.get(k) not in (None, "", {})}
                h_[pid]["from"] = im["file"] or im["source"]
                done["months"] += 1
        cfg["imports"] = [x for x in cfg.get("imports") or [] if x["id"] != iid]
        if im["kind"] == "history":
            hs = cfg.get("history") or {}
            for old in sorted(hs)[:-36]:
                hs.pop(old)
        return dict(done)
    out = PY._save(tenant, ws, ch)                                # noqa: SLF001
    if out.get("months"):
        return {**out, "says": f"{out['months']} person-months of past pay read. Run the same-as-before test on one of those months."}
    return {**out, "says": f"{out['added']} added, {out['updated']} updated" + (f", {out['skipped']} left out" if out["skipped"] else "") + "."}


# ---- her people sheet and her programs
def people_sheet(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    url = str(a.get("spreadsheet") or "").strip()

    def ch(cfg):
        d = cfg.setdefault("desk", {})
        d["people_sheet"] = {"spreadsheet": url[:300], "tab": str(a.get("tab") or "")[:80]} if url else {}
        return dict(d.get("people_sheet") or {})
    return {"people_sheet": PY._save(tenant, ws, ch)}             # noqa: SLF001


def _auto(tenant: str, ws: str, view: dict[str, Any]) -> dict[str, Any]:
    """Her linked sheet / program is where her people live: its ready lines go in by themselves; lines with a problem wait for her."""
    if view["ready"]:
        im = next(x for x in _c(tenant, ws).get("imports") or [] if x["id"] == view["import"])
        if not view["waiting"]:
            return import_apply(tenant, ws, {"import": im["id"], "hash": im["hash"]})
        ready = [r for r in im["rows"] if not r["problems"]]
        wait = [r for r in im["rows"] if r["problems"]]
        im2 = _import(tenant, ws, "people", ready, im["source"], im["file"], False)
        import_drop(tenant, ws, im["id"])
        cfg_im = next(x for x in _c(tenant, ws).get("imports") or [] if x["id"] == im2["import"])
        got = import_apply(tenant, ws, {"import": cfg_im["id"], "hash": cfg_im["hash"]})
        if wait:
            _import(tenant, ws, "people", wait, im["source"], im["file"], False)
        return {**got, "waiting": len(wait)}
    return view


def people_sheet_read(tenant: str, ws: str) -> dict[str, Any]:
    sh = ((_c(tenant, ws).get("desk") or {}).get("people_sheet") or {})
    if not sh.get("spreadsheet"):
        raise PayrollError("No people sheet linked: put its link in People.")
    from ...sheets import service as SS
    recs: list[dict[str, Any]] = []
    try:
        while len(recs) < PY.MAX_PEOPLE:
            got = SS.read(tenant, sh["spreadsheet"], sh.get("tab") or None, None, 300, len(recs))
            page = got.get("rows") or []
            recs += page
            if len(page) < 300 or len(recs) >= int(got.get("total_rows") or 0):
                break
    except Exception as e:   # noqa: BLE001
        raise PayrollError(f"The sheet could not be read: {str(e)[:160]}")
    hdr = [h for h in (recs[0].keys() if recs else []) if h != "_row"]
    rows = people_rows([hdr] + [[r.get(h) for h in hdr] for r in recs]) if recs else []
    if not rows:
        return {"says": "The sheet is empty."}
    return _auto(tenant, ws, _import(tenant, ws, "people", rows, "sheet", "People sheet", False))


def connector_state(tenant: str) -> dict[str, str]:
    """For each program in the lists: connected | can_connect | not_offered (not in Connectors on this server) | off."""
    out: dict[str, str] = {}
    kits = {k for s in SOURCES.values() for k in (s.get("kits") or {})}
    from .payroll_desk import SOFTWARE
    kits |= set(SOFTWARE)
    try:
        from ...bazar import composio as C
        from ...db import session
        if not C.configured():
            return {k: "off" for k in kits}
        cat = C.catalog() or {}
        with session() as s:
            for k in kits:
                if k not in cat:
                    out[k] = "not_offered"
                    continue
                try:
                    _a, ca = C.account(s, tenant, k)
                except Exception:   # noqa: BLE001
                    ca = None
                out[k] = "connected" if ca else "can_connect"
    except Exception:   # noqa: BLE001
        return {k: "off" for k in kits}
    return out


def sources(tenant: str, ws: str) -> dict[str, Any]:
    c = _c(tenant, ws)
    st = connector_state(tenant)
    order = size_info(c)["sources"]
    lst = []
    for key in order + [k for k in SOURCES if k not in order]:
        s = dict(SOURCES[key])
        s["key"] = key
        s["first"] = key in order
        if s.get("kits"):
            s["programs"] = [{"key": k, "name": v, "state": st.get(k, "off")} for k, v in s["kits"].items()]
            s.pop("kits")
        lst.append(s)
    d = c.get("desk") or {}
    return {"size": size_of(c), "people": lst, "attendance": ATTENDANCE, "attendance_set": d.get("attendance", ""),
            "people_sheet": d.get("people_sheet") or {}, "people_programs": d.get("people_programs") or [],
            "imports": import_view(tenant, ws)["imports"], "history_months": sorted(c.get("history") or {}),
            "says": "A program marked 'not offered' is not in Connectors on this server: bring it in as its export file or through your own system."}


async def people_software_read(tenant: str, ws: str, kits: list[str] | None = None) -> dict[str, Any]:
    """Her payroll / HR programs: their READ tools that list employees; each record becomes a proposed person."""
    import asyncio
    c = _c(tenant, ws)
    kits = kits or (c.get("desk") or {}).get("people_programs") or []
    if not kits:
        return {"read": 0, "says": "No program ticked."}
    try:
        from ...bazar import composio as C
        from ...db import session
    except Exception:   # noqa: BLE001
        return {"read": 0}
    if not C.configured():
        return {"read": 0, "says": "Connectors are not set up on this server."}
    from .payroll_desk import _records
    rows: list[dict[str, Any]] = []
    for kit in kits:
        try:
            with session() as s:
                _c0, ca = C.account(s, tenant, kit)
                s.commit()
            if not ca:
                continue
            tools = []
            for wd in ("employee", "people", "worker", "staff"):
                tools += await asyncio.to_thread(C.tool_list, kit, wd, False, 40)
        except Exception as e:   # noqa: BLE001
            log.info("payroll people %s %s: %s", tenant, kit, e)
            continue
        seen: set[str] = set()
        for t in tools:
            slug = str(t.get("slug") or "").upper()
            if slug in seen or not re.search(r"(LIST|QUERY|SEARCH|GET_ALL|FETCH)", slug) or not re.search(r"(EMPLOYEE|PEOPLE|WORKER|STAFF)", slug):
                continue
            seen.add(slug)
            if not C.is_read(slug, kit):
                continue
            try:
                with session() as s:
                    C.take_call(s, tenant)
                    s.commit()
                res = await asyncio.to_thread(C.client().execute, slug, C.composio_user(tenant), ca, {})
            except Exception as e:   # noqa: BLE001
                log.info("payroll people %s %s: %s", kit, slug, e)
                continue
            if res.get("successful", True):
                rows += [r for r in (_person_rec(x) for x in _records(res.get("data"))) if r.get("name")]
            break
    if not rows:
        return {"read": 0, "says": "No people came back from your programs."}
    for n, r in enumerate(rows, start=1):
        r["line"] = n
    return _auto(tenant, ws, _import(tenant, ws, "people", rows[:PY.MAX_PEOPLE], "payroll_app", ", ".join(kits)[:120], False))


def _person_rec(rec: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for k, v in rec.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                flat[f"{k}_{k2}".lower()] = v2
        else:
            flat[str(k).lower()] = v
    pick = lambda pat: next((flat[k] for k in flat if re.search(pat, k) and flat[k] not in (None, "", [], {})), None)   # noqa: E731
    first, last = pick(r"first_?name"), pick(r"last_?name")
    name = pick(r"^(full_?|display_?|preferred_?)?name$|employee_name") or " ".join(str(x) for x in (first, last) if x)
    row: dict[str, Any] = {"name": str(name or "").strip()[:80]}
    for f, pat in (("code", r"employee_?(id|number|code)$|^emp_?(id|code)$"), ("email", r"(work_)?email"),
                   ("department", r"department"), ("location", r"location|office|site"), ("role", r"job_?title|title|designation"),
                   ("start", r"(start|hire|join)(_date)?$|date_of_joining")):
        v = pick(pat)
        if v not in (None, ""):
            row[f] = (_day(v) or str(v)[:10]) if f == "start" else str(v)[:80]
    return row


# ---- attendance machine exports and past pay
def _mins(v: Any) -> int | None:
    if isinstance(v, datetime):
        return v.hour * 60 + v.minute
    s = str(v or "").strip()
    m = re.search(r"(\d{1,2}):(\d{2})(?::\d{2})?\s*([ap]\.?m\.?)?", s, re.I)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if m.group(3):
        h = h % 12 + (12 if m.group(3).lower().startswith("p") else 0)
    return h * 60 + mi


def attendance_rows(table: list[list[Any]], pol: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Punch exports -> (person, day) -> first in, last out. Columns: code and/or name, date, and in / out (or one punch time a row)."""
    table = [r for r in table if any(str(x or "").strip() for x in r)]
    if len(table) < 2:
        return {}
    h = [_norm(x) for x in table[0]]
    idx = lambda *names: next((i for i, x in enumerate(h) if x in names), None)    # noqa: E731
    ci = idx("emp id", "employee id", "emp code", "employee code", "user id", "id", "code", "ac no", "badge", "enroll no", "enrollment no")
    ni = idx("name", "employee name", "employee", "emp name", "staff name")
    di = idx("date", "day", "punch date", "att date", "attendance date")
    ii = idx("in", "in time", "check in", "first in", "time in", "punch in", "intime")
    oi = idx("out", "out time", "check out", "last out", "time out", "punch out", "outtime")
    ti = idx("time", "punch time", "datetime", "date time", "log time", "timestamp", "punch")
    if ci is None and ni is None:
        raise PayrollError("The attendance file needs an employee code or name column.")
    if di is None and ti is None:
        raise PayrollError("The attendance file needs a date column (or a date-and-time column).")
    days: dict[tuple[str, str], dict[str, Any]] = {}
    for r in table[1:]:
        g = lambda i: r[i] if i is not None and i < len(r) else None    # noqa: E731
        who = str(g(ci) or "").strip() or str(g(ni) or "").strip()
        if not who:
            continue
        day = _day(g(di)) if di is not None else _day(str(g(ti))[:10])
        if not day:
            continue
        rec = days.setdefault((who, day), {"code": str(g(ci) or "").strip(), "name": str(g(ni) or "").strip(), "first": None, "last": None})
        for v in ([g(ii), g(oi)] if ii is not None or oi is not None else [g(ti)]):
            m = _mins(v)
            if m is None:
                continue
            rec["first"] = m if rec["first"] is None else min(rec["first"], m)
            rec["last"] = m if rec["last"] is None else max(rec["last"], m)
    return days


def attendance_file(tenant: str, ws: str, name: str, data: bytes, actor: str = "") -> dict[str, Any]:
    from . import payroll_desk as PD
    if not _is_table(name):
        raise PayrollError("Attendance comes in as the machine's export file (CSV or Excel). For a photo of a register, drop it in the chat.")
    c = _c(tenant, ws)
    pol = c.get("policy") or {}
    table = _table_of(name, data)
    hdr = [_norm(x) for x in (table[0] if table else [])]
    if any(x in ("hours", "hours worked", "total hours", "days present", "present days") for x in hdr) and not any(
            x in ("in", "in time", "check in", "punch time", "time") for x in hdr):
        rows = _summary_rows(table)
        return PD.take_rows(tenant, ws, rows, "attendance", ref=hashlib.sha256(data).hexdigest()[:16], file=name, actor=actor)
    days = attendance_rows(table, pol)
    if not days:
        raise PayrollError("No punches could be read from the file.")
    people = c.get("employees") or {}
    by_code = {str(p.get("code")): p["name"] for p in people.values() if p.get("code")}
    start_m = int(pol.get("shift_start_min") or 0)
    grace = int(pol.get("grace_min") or 10)
    day_h = float(pol.get("day_hours") or 8)
    per: dict[tuple[str, str], dict[str, float]] = {}
    for (who, day), r in days.items():
        nm = by_code.get(r["code"]) or r["name"] or who
        key = PD.period_of(c, date.fromisoformat(day))["key"]
        x = per.setdefault((nm, key), {"days_present": 0, "hours": 0.0, "late_days": 0, "overtime_hours": 0.0})
        x["days_present"] += 1
        if r["first"] is not None and r["last"] is not None and r["last"] > r["first"]:
            hrs = round((r["last"] - r["first"]) / 60, 2)
            x["hours"] = round(x["hours"] + hrs, 2)
            if pol.get("overtime_from_punches") and hrs > day_h:
                x["overtime_hours"] = round(x["overtime_hours"] + hrs - day_h, 2)
        if start_m and r["first"] is not None and r["first"] > start_m + grace:
            x["late_days"] += 1
    got = {"checked": 0, "waiting": 0, "already": 0, "periods": []}
    sha = hashlib.sha256(data).hexdigest()[:16]
    for key in sorted({k for _, k in per}):
        rows = []
        for (nm, k), x in sorted(per.items()):
            if k != key:
                continue
            row = {"name": nm, **{f: v for f, v in x.items() if v or f == "days_present"}}
            if not pol.get("overtime_from_punches"):
                row.pop("overtime_hours", None)
            rows.append(row)
        try:
            r = PD.take_rows(tenant, ws, rows, "attendance", period=key, ref=sha, file=name, actor=actor)
        except PayrollError as e:
            got["periods"].append(f"{key}: {e}")
            continue
        for k in ("checked", "waiting", "already"):
            got[k] += r.get(k, 0)
        got["periods"].append(key)
    return {**got, "days": len(days), "says": f"{len(days)} days of punches read: {got['checked']} checked, {got['waiting']} waiting for you."}


def _summary_rows(table: list[list[Any]]) -> list[dict[str, Any]]:
    from .payroll_desk import rows_of_table
    h = [_norm(x) for x in table[0]]
    out = rows_of_table(table)
    di = next((i for i, x in enumerate(h) if x in ("days present", "present days", "present", "days worked")), None)
    li = next((i for i, x in enumerate(h) if x in ("late days", "late", "late marks")), None)
    for r, raw in zip(out, table[1:]):
        if di is not None and di < len(raw) and _num(raw[di]) is not None:
            r["days_present"] = _num(raw[di])
        if li is not None and li < len(raw) and _num(raw[li]) is not None:
            r["late_days"] = _num(raw[li])
    return out


def _month(v: Any) -> str:
    s = str(v or "").strip()
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m")
    m = re.fullmatch(r"(\d{4})-(\d{1,2})(-\d{1,2})?", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.fullmatch(r"(\d{1,2})[/-](\d{4})", s)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    for fmt in ("%b %Y", "%B %Y", "%b-%Y", "%B-%Y", "%b-%y", "%b %y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    d = _day(s)
    return d[:7] if d else ""


def history_rows(table: list[list[Any]], period: str = "") -> list[dict[str, Any]]:
    table = [r for r in table if any(str(x or "").strip() for x in r)]
    if len(table) < 2:
        return []
    raw = list(table[0])
    h = [_norm(x) for x in raw]
    find = lambda *n: next((i for i, x in enumerate(h) if x in n), None)    # noqa: E731
    ni, ci = find(*PALIAS["name"]), find(*PALIAS["code"])
    pi = find("month", "period", "pay period", "salary month", "payroll month")
    gi = find("gross", "gross pay", "gross salary", "total earnings", "earnings")
    neti = find("net", "net pay", "net salary", "take home", "in hand", "net payable")
    if ni is None and ci is None:
        raise PayrollError("The file needs each person's name or employee code.")
    if gi is None and neti is None:
        raise PayrollError("The file needs a Gross or Net pay column.")
    inputs = {find("days present", "present days", "paid days", "days worked"): "days_present",
              find("unpaid days", "lop", "loss of pay", "lop days"): "unpaid_days",
              find("overtime hours", "ot hours"): "overtime_hours", find("hours", "hours worked"): "hours"}
    inputs.pop(None, None)
    used = {ni, ci, pi, gi, neti} | set(inputs)
    part_cols = {i: str(raw[i]).strip() for i, x in enumerate(h) if i not in used and x and not TOTALS.match(x)}
    out = []
    for n, r in enumerate(table[1:], start=2):
        g = lambda i: r[i] if i is not None and i < len(r) else None    # noqa: E731
        row: dict[str, Any] = {"line": n, "name": str(g(ni) or "").strip(), "code": str(g(ci) or "").strip(),
                               "period": _month(g(pi)) if pi is not None else period}
        for i, f in ((gi, "gross"), (neti, "net")):
            if i is not None and _num(g(i)) is not None:
                row[f] = _num(g(i))
        for i, f in inputs.items():
            if _num(g(i)) is not None:
                row[f] = _num(g(i))
        parts = {FX.snake(t): _num(g(i)) for i, t in part_cols.items() if _num(g(i)) not in (None, 0)}
        if parts:
            row["parts"] = parts
        out.append(row)
    return out


def history_file(tenant: str, ws: str, name: str, data: bytes, period: str = "") -> dict[str, Any]:
    if period and not re.fullmatch(r"\d{4}-\d{2}", period):
        raise PayrollError("period: YYYY-MM (the month of this register).")
    if _is_table(name):
        return _import(tenant, ws, "history", history_rows(_table_of(name, data), period), "history", name, False, period)
    rows = []
    for n, r in enumerate(_ai_read(name, data, "history"), start=1):
        row = {"line": n, "name": str(r.get("name") or "")[:80], "code": str(r.get("code") or "")[:40],
               "period": _month(r.get("period")) or period}
        for f in ("gross", "net", "days_present", "unpaid_days", "overtime_hours"):
            if _num(r.get(f)) is not None:
                row[f] = _num(r.get(f))
        if isinstance(r.get("parts"), dict):
            row["parts"] = {FX.snake(k): _num(v) for k, v in r["parts"].items() if _num(v)}
        rows.append(row)
    return _import(tenant, ws, "history", rows, "history", name, True, period)


def history(tenant: str, ws: str) -> dict[str, Any]:
    c = _c(tenant, ws)
    hs = c.get("history") or {}
    people = c.get("employees") or {}
    return {"months": [{"period": k, "people": len(v), "gross": round(sum(float(x.get("gross") or 0) for x in v.values()), 2),
                        "net": round(sum(float(x.get("net") or 0) for x in v.values()), 2),
                        "rows": [{"id": pid, "name": (people.get(pid) or {}).get("name", pid), **x} for pid, x in sorted(v.items())][:500]}
                       for k, v in sorted(hs.items(), reverse=True)]}


# ------------------------------------------------------------------------------------------------ Part 3: the same-as-before test
def gate(c: dict[str, Any]) -> dict[str, Any]:
    if not c.get("history"):
        return {"ok": True, "say": "No past month to test against", "none": True}
    ms = c.get("match") or {}
    good = [k for k, m in ms.items() if m.get("status") in ("matched", "accepted")]
    if good:
        last = ms[sorted(good)[-1]]
        stale = last.get("rules_sig") != rules_sig(c)
        if not stale:
            return {"ok": True, "say": ("Matched " if last["status"] == "matched" else "Accepted ") + sorted(good)[-1]}
        return {"ok": False, "say": "Rules changed since the test - run it again"}
    if ms:
        return {"ok": False, "say": "Differences to look at"}
    return {"ok": False, "say": "Not run yet"}


def rules_sig(c: dict[str, Any]) -> str:
    core = [c.get("parts") or [], c.get("policy") or {}, c.get("contributions") or [], c.get("income_tax") or {},
            {k: [v.get("pay_kind"), v.get("pay_minor"), v.get("parts"), v.get("numbers")] for k, v in (c.get("employees") or {}).items()}]
    return hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode()).hexdigest()[:16]


def match_test(tenant: str, ws: str, period: str, actor: str = "") -> dict[str, Any]:
    """Work out a month she already paid from today's blocks; every person must match to the cent."""
    w = PY._ws(tenant, ws)                                        # noqa: SLF001
    c = PY._cfg(w)                                                # noqa: SLF001
    cur = PY._cur(w)                                              # noqa: SLF001
    hs = (c.get("history") or {}).get(period)
    if not hs:
        raise PayrollError(f"No past pay for {period}. Bring that month's register in first (People > Past pay).")
    extras = {}
    for pid, x in hs.items():
        e = {k: x[k] for k in ("days_present", "unpaid_days", "overtime_hours", "hours") if x.get(k) is not None}
        if e:
            extras[pid] = e
    from . import payroll_desk as PD
    rec = PY.run_payroll(tenant, ws, {"period": period if PD.freq(c) == "monthly" else period + "-01", "extras": extras,
                                      "_dry": True, "_only": set(hs)})
    ours = {p["id"]: p for p in rec["people"]}
    unit = Decimal(1).scaleb(-PY.P.minor_unit(cur))
    rows, same = [], 0
    for pid, x in sorted(hs.items()):
        o = ours.get(pid)
        name = ((c.get("employees") or {}).get(pid) or {}).get("name", pid)
        if not o:
            rows.append({"id": pid, "name": name, "status": "not_paid_now", "diffs": [{"what": "person", "ours": "not paid", "theirs": "paid"}]})
            continue
        diffs = []
        for f in ("gross", "net"):
            if x.get(f) is not None and abs(Decimal(str(o[f])) - Decimal(str(x[f]))) >= unit:
                diffs.append({"what": f, "ours": o[f], "theirs": x[f], "by": round(o[f] - float(x[f]), 2)})
        op = {FX.snake(q["name"]): q["amount"] for q in o.get("parts") or []}
        op.update({FX.snake(cc["name"]): cc["employee"] for cc in o.get("contributions") or []})
        for k, v in (x.get("parts") or {}).items():
            if k in op and abs(Decimal(str(op[k])) - Decimal(str(v))) >= unit:
                diffs.append({"what": k, "ours": op[k], "theirs": v, "by": round(op[k] - float(v), 2)})
        rows.append({"id": pid, "name": name, "status": "differs" if diffs else "matched", "diffs": diffs, "ours_net": o["net"],
                     "theirs_net": x.get("net")})
        same += 0 if diffs else 1
    status = "matched" if same == len(rows) else "differs"
    res = {"period": period, "status": status, "people": len(rows), "same": same, "rows": rows,
           "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "by": str(actor)[:120], "rules_sig": rules_sig(c)}

    def ch(cfg):
        cfg.setdefault("match", {})[period] = res
        return True
    PY._save(tenant, ws, ch)                                      # noqa: SLF001
    return {**res, "says": (f"All {len(rows)} people match {period} to the cent." if status == "matched" else
                            f"{same} of {len(rows)} match. Look at each difference: fix the part or the rule, or accept it with a reason.")}


def match_accept(tenant: str, ws: str, a: dict[str, Any], actor: str = "") -> dict[str, Any]:
    period, why = str(a.get("period") or ""), str(a.get("reason") or "").strip()
    if len(why) < 8:
        raise PayrollError("reason: why these differences are right (e.g. 'last year we paid a one-off arrear').")

    def ch(cfg):
        m = (cfg.get("match") or {}).get(period)
        if not m:
            raise PayrollError("Run the same-as-before test on that month first.")
        if m.get("rules_sig") != rules_sig(cfg):
            raise PayrollError("Your rules changed since that test: run it again, then accept.")
        m.update({"status": "accepted", "accepted_by": str(actor)[:120], "reason": why[:400],
                  "accepted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        return dict(m)
    m = PY._save(tenant, ws, ch)                                  # noqa: SLF001
    return {"period": period, "status": m["status"], "says": "Accepted with your reason. It is kept beside the payroll."}


async def propose_parts(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    """Proposed pay parts from her papers (a payslip or a policy, as text) - one AI call; nothing is saved until she saves each part."""
    text = str(a.get("text") or "").strip()
    if not text:
        raise PayrollError("text: a payslip, a salary breakup or her pay policy, as text.")
    c = _c(tenant, ws)
    words = sorted(known_vars(c))
    system = ("You turn a company's pay papers into pay parts. Return ONLY JSON {\"parts\": [{\"name\", \"kind\" (earning|untaxed|pre_tax|"
              "deduction|employer), \"formula\", \"applies_to\" (all or department:X etc.), \"why\" (the line of the paper it comes "
              "from)}]}. A formula uses only numbers, + - * / ( ), min, max, round, `a ? b : c` and these words: " + ", ".join(words) +
              ". Leave out statutory deductions (PF, ESI, income tax, social security) - they come from the country rules. Never invent "
              "a number that is not on the paper.")
    import asyncio
    from .books_feed import _loose
    from ...agent import llm
    prompt = "Papers:\n<<<\n" + text[:20000] + "\n>>>\nReturn the JSON object now."
    brain = llm.cheap_brain()
    if brain:
        blocks, _, _ = await llm.openai_create(brain, system, [], [{"role": "user", "content": prompt}], 3000)
        out = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    else:
        from ...config import get_settings
        if not get_settings().anthropic_api_key:
            raise PayrollError("No AI model is set up on this server.")
        from ...agent import door
        from ...agent.santosh import get_client
        msg = await door.acreate(get_client(), door.shape("write", get_settings().anthropic_model, 3000, system,
                                                          [{"role": "user", "content": prompt}]))
        out = "".join(getattr(b, "text", "") for b in msg.content)
    got = (_loose(out) or {}).get("parts") or []
    props = []
    for q in got[:20]:
        if not isinstance(q, dict):
            continue
        item = {"name": str(q.get("name") or "")[:60], "kind": q.get("kind") if q.get("kind") in KINDS else "earning",
                "formula": str(q.get("formula") or ""), "applies_to": str(q.get("applies_to") or "all"), "why": str(q.get("why") or "")[:200]}
        try:
            clean_parts([item])
            unknown = FX.check(item["formula"], set(words) | {FX.snake(x.get("name")) for x in got if isinstance(x, dict)})
            item["problem"] = ("Unknown words: " + ", ".join(unknown)) if unknown else ""
        except PayrollError as e:
            item["problem"] = str(e)
        props.append(item)
    await asyncio.sleep(0)
    return {"proposals": props, "says": f"{len(props)} parts proposed from your papers. Save the ones that are right; nothing is used until you do."}


# ------------------------------------------------------------------------------------------------ Part 4: the preview and its report
def _team_others(tenant: str, ws: str) -> int:
    try:
        from . import books_ent as E
        return sum(1 for m in E.team(tenant, ws) if m.get("active"))
    except Exception:   # noqa: BLE001
        return 0


def flags(c: dict[str, Any], run: dict[str, Any], prev: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    people = c.get("employees") or {}
    pol = c.get("policy") or {}
    jump = float(pol.get("jump_pct") or 25)
    pmap = {p["id"]: p for p in (prev or {}).get("people", [])}
    ins: dict[str, dict[str, float]] = {}
    att_linked = False
    for i in c.get("inputs") or []:
        if i.get("period") == key and i.get("status") == "checked":
            x = ins.setdefault(i["pid"], {})
            for f, v in (i.get("values") or {}).items():
                x[f] = x.get(f, 0) + float(v)
                att_linked = att_linked or f == "days_present"
    out: list[dict[str, Any]] = []
    soon = (date.today() - timedelta(days=30)).isoformat()
    for p in run["people"]:
        q = people.get(p["id"]) or {}
        if q.get("payee_changed_on") and q["payee_changed_on"] >= soon:
            out.append({"level": "bad", "who": p["name"], "id": p["id"], "what": "payee",
                        "say": f"{p['name']}: bank payee changed on {q['payee_changed_on']}. Confirm it with them before paying."})
        old = pmap.get(p["id"])
        if old and old.get("gross") and abs(p["gross"] - old["gross"]) / old["gross"] * 100 >= jump:
            ch = round((p["gross"] - old["gross"]) / old["gross"] * 100)
            out.append({"level": "warn", "who": p["name"], "id": p["id"], "what": "jump",
                        "say": f"{p['name']}: pay is {abs(ch)}% {'higher' if ch > 0 else 'lower'} than last time ({old['gross']:,.2f} -> {p['gross']:,.2f})."})
        x = ins.get(p["id"]) or {}
        if att_linked and "days_present" in x and x["days_present"] == 0 and not x.get("leave_days") and p["gross"] > 0:
            out.append({"level": "warn", "who": p["name"], "id": p["id"], "what": "absent",
                        "say": f"{p['name']}: 0 days present but paid {p['gross']:,.2f}. Leave or unpaid days missing?"})
        if pol.get("minimum_pay") and p["gross"] < float(pol["minimum_pay"]) and not (q.get("start") and q["start"] > run["start"]) \
                and not (q.get("left") and q["left"] < run["end"]):
            out.append({"level": "bad", "who": p["name"], "id": p["id"], "what": "minimum",
                        "say": f"{p['name']}: gross {p['gross']:,.2f} is below your minimum pay {float(pol['minimum_pay']):,.2f} (your figure - check this)."})
        if p["net"] <= 0:
            out.append({"level": "bad", "who": p["name"], "id": p["id"], "what": "net",
                        "say": f"{p['name']}: net pay is {p['net']:,.2f}. Deductions are more than the pay."})
    seen: dict[tuple[str, str], str] = {}
    for p in run["people"]:
        q = people.get(p["id"]) or {}
        for f in ("payee_ref", "email"):
            v = str(q.get(f) or "").lower()
            if not v:
                continue
            if (f, v) in seen:
                out.append({"level": "bad", "who": p["name"], "id": p["id"], "what": "twice",
                            "say": f"{p['name']} and {seen[(f, v)]} have the same {f.replace('_', ' ')}. One person paid twice?"})
            seen[(f, v)] = p["name"]
    return out


def _by(run: dict[str, Any], field: str) -> list[dict[str, Any]]:
    g: dict[str, dict[str, Any]] = {}
    for p in run["people"]:
        k = str(p.get(field) or "Not set")
        x = g.setdefault(k, {"name": k, "people": 0, "gross": 0.0, "net": 0.0, "cost": 0.0})
        x["people"] += 1
        for f in ("gross", "net", "cost"):
            x[f] = round(x[f] + p[f], 2)
    return sorted(g.values(), key=lambda x: -x["cost"])


def preview(tenant: str, ws: str, a: dict[str, Any], actor: str = "") -> dict[str, Any]:
    """'Run the preview': the period prepared, checked and reported; sent to the desk, the Payroll chat and her phone."""
    from . import payroll_desk as PD
    c = _c(tenant, ws)
    key = str(a.get("period") or PD.period_of(c)["key"])
    g = gate(c)
    if not g["ok"]:
        raise PayrollError("First the same-as-before test: work out a month you already paid and make it match (Pay rules). " + g["say"] + ".")
    run = PD.prepare(tenant, ws, {"period": key, "extras": a.get("extras") or {}}, actor)
    c = _c(tenant, ws)
    runs = c.get("runs") or {}
    before = [k for k in sorted(runs) if k < key]
    prev = runs[before[-1]] if before else None
    info = size_info(c)
    fl = flags(c, run, prev, key)
    t = run["totals"]
    to_auth = sum(run["to_authorities"].values())
    d = PD.desk(tenant, ws)
    ch = run.get("changes") or []
    moved = [x for x in ch if x.get("why")]
    joined = sum(1 for x in moved if any(str(w).startswith("joined") for w in x["why"]))
    left = sum(1 for x in moved if any(str(w).startswith("leaves") for w in x["why"]))
    prev_net = (prev or {}).get("totals", {}).get("net")
    report = {
        "period": key, "start": run["start"], "end": run["end"], "currency": run["currency"], "hash": run["hash"],
        "people": len(run["people"]), "totals": t, "to_authorities": run["to_authorities"],
        "cash_needed": round(t["net"] + to_auth, 2), "pay_day": d.get("pay_day"), "net_before": prev_net,
        "net_change_pct": round((t["net"] - prev_net) / prev_net * 100, 1) if prev_net else None,
        "joined": joined, "left": left, "changes": moved[:200], "gone": [], "flags": fl,
        "waiting_inputs": run.get("waiting_inputs", 0), "missing": run.get("missing") or [],
        "by": {f: _by(run, f) for f in ("department", "location", "cost_centre", "company") if f in info["depth"]
               and any(p.get(f) for p in run["people"])},
        "dues": d.get("filings_soon") or [], "size": size_of(c) or "small", "chain": info["chain"],
        "match": g["say"], "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "made_by": str(actor)[:120],
    }
    try:
        report["gone"] = PD.changes(tenant, ws, key).get("gone") or []
    except PayrollError:
        pass
    line = _say(report)
    report["line"] = line

    def ch_(cfg):
        f = cfg.setdefault("flow", {}).setdefault(key, {})
        f["report"] = report
        f.pop("checked_by", None)
        return True
    PY._save(tenant, ws, ch_)                                      # noqa: SLF001
    if a.get("tell", True):
        _tell(tenant, line)
    return {**report, "says": line}


def _say(r: dict[str, Any]) -> str:
    cur = r["currency"]
    m = lambda v: f"{cur} {v:,.2f}"                                  # noqa: E731
    bits = [f"Payroll preview for {r['period']} is ready: {r['people']} people, net pay {m(r['totals']['net'])}"]
    if r.get("net_change_pct") is not None:
        bits.append(f"({'+' if r['net_change_pct'] >= 0 else ''}{r['net_change_pct']}% on last time)")
    s = " ".join(bits) + f". Cash needed by {r.get('pay_day') or 'pay day'}: {m(r['cash_needed'])}."
    bad = [f for f in r["flags"] if f["level"] == "bad"]
    warn = [f for f in r["flags"] if f["level"] == "warn"]
    if bad or warn:
        s += f" {len(bad) + len(warn)} thing{'s' if len(bad) + len(warn) != 1 else ''} to look at first"
        s += ": " + "; ".join(f["say"] for f in (bad + warn)[:2]) + "."
    else:
        s += " Nothing unusual found."
    if r.get("waiting_inputs"):
        s += f" {r['waiting_inputs']} input{'s' if r['waiting_inputs'] != 1 else ''} still waiting."
    s += " Open Payroll > Run payroll to " + ("check and approve it." if "check" in r["chain"] else "approve it.")
    return s


def _tell(tenant: str, line: str) -> None:
    """The report's line in her Payroll chat - the same message reaches her phone."""
    try:
        from ...agent.santosh import _save as save
        from ...events import bus
        from ...payrollchat import current
        conv = current(tenant)["id"]
        save(conv, "assistant", [{"type": "text", "text": line}], display=line)
        bus.publish(conv, "message", {"role": "assistant", "text": line, "source": "payroll_preview"})
    except Exception:   # noqa: BLE001
        log.exception("payroll preview note")


def report(tenant: str, ws: str, period: str) -> dict[str, Any]:
    from . import payroll_desk as PD
    c = _c(tenant, ws)
    key = period or PD.period_of(c)["key"]
    f = PD._flow(c, key)                                          # noqa: SLF001
    r = f.get("report")
    if not r:
        raise PayrollError(f"No preview for {key} yet: run the preview.")
    run = (c.get("runs") or {}).get(key) or {}
    stale = PD._hash(run) != r["hash"] if run else True           # noqa: SLF001
    return {**r, "status": f.get("status", "draft"), "checked_by": f.get("checked_by", ""), "approved_by": f.get("approved_by", ""),
            "prepared_by": f.get("prepared_by", ""), "stale": stale, "team": _team_others(tenant, ws)}


def check_run(tenant: str, ws: str, a: dict[str, Any], actor: str) -> dict[str, Any]:
    """The checker's tap (large and big sizes): on the hash of the run she saw, by someone other than the preparer when there is a team."""
    from . import payroll_desk as PD
    c = _c(tenant, ws)
    key = str(a.get("period") or "")
    r = (c.get("runs") or {}).get(key)
    fl = PD._flow(c, key)                                         # noqa: SLF001
    if not r or not fl:
        raise PayrollError(f"No payroll for {key}: run the preview first.")
    if fl.get("status") not in ("draft",):
        return {"period": key, "status": fl.get("status"), "says": "Already past checking."}
    if str(a.get("hash") or "") != PD._hash(r) or fl.get("hash") != PD._hash(r):   # noqa: SLF001
        raise PayrollError("The payroll changed after you looked at it. Look at it again, then check it.")
    if _team_others(tenant, ws) and PD._who(fl.get("prepared_by")) == PD._who(actor):   # noqa: SLF001
        raise PayrollError("The person who prepared it does not check it: someone else on the team checks it.")

    def ch(cfg):
        f = cfg["flow"][key]
        f.update({"status": "checked", "checked_by": str(actor)[:120], "checked_at": date.today().isoformat()})
        return dict(f)
    PY._save(tenant, ws, ch)                                      # noqa: SLF001
    return {"period": key, "status": "checked", "says": f"{key} checked. Now it waits for approval."}


def chain_ok(tenant: str, ws: str, c: dict[str, Any], key: str, actor: str) -> None:
    """Before approval: the size's chain is followed (called from payroll_desk.approve)."""
    from . import payroll_desk as PD
    info = size_info(c)
    fl = PD._flow(c, key)                                         # noqa: SLF001
    team = _team_others(tenant, ws)
    if "check" in info["chain"] and fl.get("status") != "checked":
        raise PayrollError("For your size a payroll is checked before it is approved: the checker taps Check first.")
    if team and info["split"]:
        if PD._who(fl.get("prepared_by")) == PD._who(actor):     # noqa: SLF001
            raise PayrollError("The person who prepared it does not approve it: someone else on the team approves it.")
        if fl.get("checked_by") and PD._who(fl.get("checked_by")) == PD._who(actor):   # noqa: SLF001
            raise PayrollError("The person who checked it does not also approve it.")


def report_pdf(tenant: str, ws: str, period: str) -> tuple[str, bytes]:
    r = report(tenant, ws, period)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    w = PY._ws(tenant, ws)                                        # noqa: SLF001
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    y = H - 20 * mm
    cur = r["currency"]
    m = lambda v: f"{cur} {float(v):,.2f}"                           # noqa: E731

    def line(txt: str, size: int = 10, bold: bool = False, gap: float = 5.5) -> None:
        nonlocal y
        if y < 20 * mm:
            pdf.showPage()
            y = H - 20 * mm
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(18 * mm, y, txt[:110])
        y -= gap * mm

    line(f"{w.get('name') or 'Payroll'} - payroll report {r['period']}", 15, True, 8)
    line(f"{r['start']} to {r['end']} · {r['people']} people · prepared by {r.get('prepared_by') or '-'} · status {r['status']}", 9)
    line("")
    for k, label in (("gross", "Gross pay"), ("tax", "Income tax"), ("ee", "Contributions from pay"), ("er", "Employer costs"),
                     ("net", "Net pay"), ("cost", "Total cost")):
        line(f"{label}: {m(r['totals'].get(k, 0))}")
    line(f"Cash needed by {r.get('pay_day') or 'pay day'}: {m(r['cash_needed'])}", 10, True)
    for n, v in r["to_authorities"].items():
        line(f"   to {n}: {m(v)}", 9)
    line("")
    line("Look at these first", 12, True, 7)
    for f in r["flags"] or [{"say": "Nothing unusual found."}]:
        line("- " + f["say"], 9)
    line("")
    line("What changed", 12, True, 7)
    for x in r["changes"][:60] or [{"name": "-", "why": ["same as before"]}]:
        line(f"- {x['name']}: {', '.join(x.get('why') or [])}", 9)
    for f, rows in (r.get("by") or {}).items():
        line("")
        line("By " + f.replace("_", " "), 12, True, 7)
        for g in rows[:40]:
            line(f"- {g['name']}: {g['people']} people, net {m(g['net'])}, cost {m(g['cost'])}", 9)
    line("")
    line("Hoola never pays anyone and never files. Not payroll advice.", 8)
    pdf.save()
    return f"payroll-report-{r['period']}.pdf", buf.getvalue()


# ------------------------------------------------------------------------------------------------ Part 5 + 6: history and the group
def history_report(tenant: str, ws: str, n: int = 12) -> dict[str, Any]:
    c = _c(tenant, ws)
    runs = c.get("runs") or {}
    flow = c.get("flow") or {}
    hs = c.get("history") or {}
    months: dict[str, dict[str, Any]] = {}
    for k, v in hs.items():
        months[k] = {"period": k, "from": "past pay", "people": len(v), "gross": round(sum(float(x.get("gross") or 0) for x in v.values()), 2),
                     "net": round(sum(float(x.get("net") or 0) for x in v.values()), 2), "cost": None, "overtime_hours": None}
    for k, r in runs.items():
        st = (flow.get(k) or {}).get("status") or ("approved" if r.get("closed") else "draft")
        months[k] = {"period": k, "from": st, "people": len(r["people"]), "gross": r["totals"]["gross"], "net": r["totals"]["net"],
                     "cost": r["totals"]["cost"], "overtime_hours": round(sum((flow.get(k) or {}).get("overtime_hours", {}).values()), 2)}
    rows = [months[k] for k in sorted(months)][-max(1, min(int(n or 12), 36)):]
    for i, x in enumerate(rows):
        x["per_person"] = round((x["cost"] or x["gross"]) / x["people"], 2) if x["people"] else 0
        if i:
            p = rows[i - 1]
            x["net_change_pct"] = round((x["net"] - p["net"]) / p["net"] * 100, 1) if p["net"] else None
    first, last = (rows[0], rows[-1]) if rows else ({}, {})
    say = ""
    if len(rows) >= 2 and first.get("net"):
        say = (f"Net pay moved {round((last['net'] - first['net']) / first['net'] * 100, 1)}% from {first['period']} to {last['period']}; "
               f"people {first['people']} -> {last['people']}.")
        ot = [x for x in rows if x.get("overtime_hours")]
        if ot:
            top = max(ot, key=lambda x: x["overtime_hours"])
            say += f" Most overtime: {top['period']} ({top['overtime_hours']:g} hours)."
    return {"months": rows, "currency": PY._cur(PY._ws(tenant, ws)), "says": say or "Not enough months yet."}   # noqa: SLF001


def group_view(tenant: str) -> dict[str, Any]:
    """Every business's payroll in one view; totals per currency, never converted."""
    from ... import db
    from ..models import FinWorkspace, ensure
    from . import payroll_desk as PD
    ensure()
    rows = []
    with db.session() as s:
        wss = s.query(FinWorkspace).filter(FinWorkspace.tenant_id == tenant, FinWorkspace.status == "active").all()
        items = [(w.id, w.name, w.currency, json.loads(w.settings or "{}").get("payroll") or {}) for w in wss]
    for wid, name, cur, c in items:
        if not c.get("employees"):
            continue
        try:
            key = PD.period_of(c)["key"]
        except Exception:   # noqa: BLE001
            continue
        if key not in (c.get("runs") or {}) and c.get("runs"):
            key = sorted(c["runs"])[-1]                              # where this business last got to
        f = (c.get("flow") or {}).get(key) or {}
        r = (c.get("runs") or {}).get(key) or {}
        rows.append({"workspace": wid, "name": name, "currency": c.get("currency") or cur, "period": key,
                     "people": sum(1 for p in c["employees"].values() if not p.get("left")),
                     "status": f.get("status") or ("draft" if r else "none"), "net": (r.get("totals") or {}).get("net"),
                     "cost": (r.get("totals") or {}).get("cost"), "flags": len(((f.get("report") or {}).get("flags")) or [])})
    tot: dict[str, dict[str, float]] = {}
    for r in rows:
        if r["net"] is None:
            continue
        x = tot.setdefault(r["currency"], {"net": 0.0, "cost": 0.0, "people": 0})
        x["net"] = round(x["net"] + r["net"], 2)
        x["cost"] = round(x["cost"] + (r["cost"] or 0), 2)
        x["people"] += r["people"]
    ready = all(r["status"] in ("approved", "paid") for r in rows) if rows else False
    return {"companies": rows, "totals": tot, "all_approved": ready,
            "says": f"{len(rows)} businesses. Totals are kept per currency; Hoola never converts them for you."}


# ------------------------------------------------------------------------------------------------ door
def run(tenant: str, action: str, ws: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    import asyncio
    import base64
    if action == "setup_size":
        return setup_size(tenant, ws, a)
    if action == "sources":
        return sources(tenant, ws)
    if action in ("people_file", "attendance_file", "history_file"):
        try:
            data = base64.b64decode(str(a.get("data_b64") or ""), validate=True)
        except Exception:   # noqa: BLE001
            raise PayrollError("The file did not arrive.")
        nm = str(a.get("name") or "file.csv")
        if action == "people_file":
            return people_file(tenant, ws, nm, data, str(a.get("source") or "excel"))
        if action == "attendance_file":
            return attendance_file(tenant, ws, nm, data, actor)
        return history_file(tenant, ws, nm, data, str(a.get("period") or ""))
    if action == "people_text":
        return people_text(tenant, ws, str(a.get("text") or ""))
    if action == "people_sheet":
        return people_sheet(tenant, ws, a)
    if action == "people_sheet_read":
        return people_sheet_read(tenant, ws)
    if action == "people_software_read":
        if a.get("programs") is not None:
            ks = [str(k) for k in a["programs"]][:20]

            def ch(cfg):
                cfg.setdefault("desk", {})["people_programs"] = ks
                return ks
            PY._save(tenant, ws, ch)                              # noqa: SLF001
        return asyncio.run(people_software_read(tenant, ws))
    if action == "import_view":
        return import_view(tenant, ws, str(a.get("import") or ""))
    if action == "import_apply":
        return import_apply(tenant, ws, a, actor)
    if action == "import_drop":
        return import_drop(tenant, ws, str(a.get("import") or ""))
    if action == "history":
        return history(tenant, ws)
    if action == "parts":
        return parts_view(tenant, ws)
    if action == "part_save":
        return part_save(tenant, ws, a)
    if action == "part_delete":
        return part_delete(tenant, ws, a)
    if action == "policy_save":
        return policy_save(tenant, ws, a)
    if action == "propose_parts":
        return asyncio.run(propose_parts(tenant, ws, a))
    if action == "match_test":
        return match_test(tenant, ws, str(a.get("period") or ""), actor)
    if action == "match_accept":
        return match_accept(tenant, ws, a, actor)
    if action == "preview":
        return preview(tenant, ws, a, actor)
    if action == "check_run":
        return check_run(tenant, ws, a, actor)
    if action == "report":
        return report(tenant, ws, str(a.get("period") or ""))
    if action == "report_pdf":
        name, data = report_pdf(tenant, ws, str(a.get("period") or ""))
        return {"name": name, "pdf_b64": base64.b64encode(data).decode()}
    if action == "history_report":
        return history_report(tenant, ws, int(a.get("months") or 12))
    if action == "group_view":
        return group_view(tenant)
    raise PayrollError("action: " + ", ".join(ACTIONS))
