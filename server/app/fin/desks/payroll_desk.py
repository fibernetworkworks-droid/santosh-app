"""v0.999.169 PAYROLL DESK - what the Payroll employee's own desk adds to the F5 engine (fin/desks/payroll.py) (owner: "WE WILL
WORK ON NEXT AI EMPLOYEE SAME WAY A PAYROLL" -> the design claude.ai/artifact/M5ukAtPfTjN89y7NzqT8pt -> "GO").

  Step 2 - pay inputs that arrive by themselves: hours, overtime, bonus, unpaid days and leave from her sheet, her payroll email,
           her time / HR software (read tools only), an upload or her own system (a payroll key). Every row is checked in code
           before a run: the name is one of her people, the date sits in the period, hours stay under her limit, nothing is counted
           twice, money is not negative. A row that fails waits with its reason; she matches or drops it.
  Step 3 - country rules with help: a country's starting list comes from its pack (payroll.starting_list, status verify). Each rule
           lands marked "check this" and the engine refuses to run until a person checked it against its official page (source +
           date + who). India's PF / ESI / PT / TDS are data rows in the India pack now; people from the older India payroll move
           over by her tap, their old runs stay where they were.
  Step 4 - joined to the books: a run is approved by her tap on the hash of the run she saw; approval locks it and posts the wage
           journal to Books & Accounts; the payment file (her bank's CSV, or ISO 20022 with accounts she types for that one file -
           never kept); the run shows Paid only when bank lines in Bank & matching cover it; payslips as PDFs in each person's
           language, put in her mailbox's Drafts - she sends them.
  Step 5 - team: the Books & Accounts team roles on the same business (accountant = preparer, approver, auditor / viewer read);
           above her limit a run is approved by someone other than the person who ran it.

Hoola never pays anyone and never files. Bank account numbers are never kept. Not payroll advice."""
from __future__ import annotations

import csv
import difflib
import hashlib
import io
import json
import logging
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any

from . import payroll as PY

log = logging.getLogger("santosh.payrolldesk")

PayrollError = PY.PayrollError
ACTIONS = ("desk", "inputs", "input_rows", "input_match", "input_drop", "missing", "changes", "prepare", "approve", "unapprove",
           "post_journal", "pay_file", "paid_check", "payslip_pdf", "payslip_drafts", "starting_list", "apply_starting_list",
           "check_rule", "rules", "import_old", "desk_settings", "api_key", "api_stop", "mail_attach", "mail_detach", "sheet_read",
           "software_read", "mailboxes")
FIELDS = ("hours", "overtime_hours", "overtime", "bonus", "commission", "other_pay", "unpaid_days", "leave_days")
MONEY = ("overtime", "bonus", "commission", "other_pay")
DEFAULT_DESK = {"max_hours": {"monthly": 260, "fortnightly": 130, "weekly": 65}, "overtime_x": 1.5, "standard_hours": 160,
                "approve_limit": 0, "mail": [], "sheet": {}, "software": [], "hook_hash": ""}
SOFTWARE = {"deputy": "Deputy", "bamboohr": "BambooHR", "factorial": "Factorial", "keka": "Keka", "personio": "Personio",
            "hibob": "HiBob", "when_i_work": "When I Work", "homebase": "Homebase", "clockify": "Clockify", "harvest": "Harvest",
            "toggl": "Toggl Track", "zoho_people": "Zoho People"}
FILE_EXT = (".csv", ".xlsx", ".xls", ".tsv")
NEVER_KEPT = "Account numbers you type here are used for this one file and never kept."
# what the role on these books may do here (the Books & Accounts team, books_ent)
READ = {"desk", "mailboxes", "inputs", "missing", "changes", "rules", "starting_list", "payslip_pdf", "people", "payslip", "payments", "filings"}
PREP = READ | {"upload", "input_rows", "input_match", "input_drop", "prepare", "employee", "sheet_read", "software_read", "paid_check",
               "pay_file", "payslip_drafts", "contractors"}
CAN = {"owner": None, "admin": None, "accountant": PREP, "approver": READ | {"approve", "unapprove", "pay_file", "paid_check", "done"},
       "auditor": READ, "viewer": READ - {"payslip_pdf", "payslip"}}
ROLE_SAY = {"accountant": "Preparer", "approver": "Approver", "auditor": "Auditor", "viewer": "Viewer", "admin": "Admin", "owner": "Owner"}


def allowed(role: str, action: str) -> bool:
    c = CAN.get(role, set())
    return c is None or action in c


# ---------------------------------------------------------------- plumbing
def _w(tenant: str, ws: str) -> dict[str, Any]:
    return PY._ws(tenant, ws)                                     # noqa: SLF001


def _c(tenant: str, ws: str) -> dict[str, Any]:
    return PY._cfg(_w(tenant, ws))                                # noqa: SLF001


def desk_cfg(c: dict[str, Any]) -> dict[str, Any]:
    d = {**DEFAULT_DESK, **(c.get("desk") or {})}
    d["max_hours"] = {**DEFAULT_DESK["max_hours"], **(d.get("max_hours") or {})}
    return d


def _save(tenant: str, ws: str, fn):
    return PY._save(tenant, ws, fn)                               # noqa: SLF001


def freq(c: dict[str, Any]) -> str:
    return c.get("frequency") or "monthly"


def period_of(c: dict[str, Any], day: date | None = None) -> dict[str, str]:
    """The pay period a day sits in: YYYY-MM for monthly; for weekly / fortnightly the period starting on the anchor (her first run's
    start, else the Monday of this week) stepped by 7 / 14 days."""
    d = day or date.today()
    f = freq(c)
    if f == "monthly":
        key, start, end = PY._period(d.strftime("%Y-%m"))         # noqa: SLF001
        return {"key": key, "start": start, "end": end}
    step = 7 if f == "weekly" else 14
    runs = sorted((c.get("runs") or {}).keys())
    try:
        anchor = date.fromisoformat(runs[0]) if runs else d - timedelta(days=d.weekday())
    except ValueError:
        anchor = d - timedelta(days=d.weekday())
    n = (d - anchor).days // step
    s = anchor + timedelta(days=n * step)
    return {"key": s.isoformat(), "start": s.isoformat(), "end": (s + timedelta(days=step - 1)).isoformat()}


def bounds(c: dict[str, Any], key: str) -> tuple[str, str]:
    k, s, e = PY._period(key)                                     # noqa: SLF001
    if not e:
        e = (date.fromisoformat(s) + timedelta(days=(7 if freq(c) == "weekly" else 14) - 1)).isoformat()
    return s, e


def _norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _num(v: Any) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


# ---------------------------------------------------------------- Step 2: pay inputs
ALIASES = {"name": ("name", "employee", "employee name", "staff", "person", "worker", "full name", "user", "member"),
           "date": ("date", "day", "week", "period", "start", "work date"),
           "hours": ("hours", "hours worked", "regular hours", "total hours", "time", "worked"),
           "overtime_hours": ("overtime hours", "ot hours", "ot", "extra hours"),
           "overtime": ("overtime pay", "overtime amount"), "bonus": ("bonus", "incentive"), "commission": ("commission",),
           "other_pay": ("other pay", "allowance", "arrears"),
           "unpaid_days": ("unpaid days", "lop", "loss of pay", "unpaid leave", "absent days", "absent"),
           "leave_days": ("leave days", "paid leave", "holiday", "leave", "vacation")}


def _col(header: list[str]) -> dict[str, int]:
    h = [_norm(x) for x in header]
    out: dict[str, int] = {}
    for f, names in ALIASES.items():
        for i, x in enumerate(h):
            if i in out.values():
                continue
            if x in names or (f not in ("date", "name") and any(x == n for n in names)):
                out[f] = i
                break
    return out


def rows_of_table(table: list[list[Any]]) -> list[dict[str, Any]]:
    """A sheet / CSV table (first row = headings) -> input rows {name, date?, hours, ...}."""
    table = [r for r in table if any(str(x or "").strip() for x in r)]
    if len(table) < 2:
        return []
    cols = _col([str(x or "") for x in table[0]])
    if "name" not in cols:
        raise PayrollError("The file needs a column with each person's name (Name / Employee).")
    out = []
    for r in table[1:]:
        g = lambda f: r[cols[f]] if f in cols and cols[f] < len(r) else None   # noqa: E731
        row = {"name": str(g("name") or "").strip()}
        if g("date") not in (None, ""):
            row["date"] = g("date")
        for f in FIELDS:
            if f in cols and g(f) not in (None, ""):
                row[f] = g(f)
        out.append(row)
    return out


def rows_of_file(name: str, data: bytes) -> list[dict[str, Any]]:
    n = str(name or "").lower()
    if n.endswith((".xlsx", ".xls")):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            ws = wb.worksheets[0]
            return rows_of_table([list(r) for r in ws.iter_rows(values_only=True)])
        except PayrollError:
            raise
        except Exception as e:   # noqa: BLE001
            raise PayrollError(f"The spreadsheet could not be read: {str(e)[:120]}")
    text = data.decode("utf-8-sig", errors="replace")
    dialect = "excel-tab" if n.endswith(".tsv") or text.count("\t") > text.count(",") else "excel"
    return rows_of_table(list(csv.reader(io.StringIO(text), dialect=dialect)))


def _day(v: Any) -> str:
    if isinstance(v, (date, datetime)):
        return (v.date() if isinstance(v, datetime) else v).isoformat()
    s = str(v or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _match(people: dict[str, Any], name: str) -> tuple[str, str]:
    """(pid, '') on an exact match by name or id, else ('', the closest name to suggest or '')."""
    n = _norm(name)
    for pid, p in people.items():
        if n and (n == _norm(p.get("name")) or n == _norm(pid)):
            return pid, ""
    names = {_norm(p.get("name")): pid for pid, p in people.items()}
    close = difflib.get_close_matches(n, list(names), n=1, cutoff=0.75)
    return "", (people[names[close[0]]]["name"] if close else "")


def _check(c: dict[str, Any], key: str, row: dict[str, Any], taken: dict[tuple[str, str], str]) -> tuple[dict[str, Any], list[str]]:
    """One input row against her people, the period and her limits."""
    people = c.get("employees") or {}
    why: list[str] = []
    pid, near = _match(people, row.get("name", ""))
    vals: dict[str, float] = {}
    for f in FIELDS:
        if f in row and row[f] not in (None, ""):
            v = _num(row[f])
            if v is None:
                why.append(f"{f.replace('_', ' ')} is not a number ({str(row[f])[:20]})")
            elif v < 0:
                why.append(f"{f.replace('_', ' ')} is below zero")
            else:
                vals[f] = v
    if not vals:
        why.append("the row has no hours, days or pay in it")
    if not pid:
        why.append(f"no one called {row.get('name') or '(no name)'} in your people" + (f" - did you mean {near}?" if near else ""))
    s, e = bounds(c, key)
    d = _day(row.get("date")) if row.get("date") not in (None, "") else ""
    if row.get("date") not in (None, "") and not d:
        why.append(f"the date {str(row['date'])[:20]} could not be read")
    elif d and not s <= d <= e:
        why.append(f"the date {d} is outside {key} ({s} to {e})")
    lim = desk_cfg(c)["max_hours"].get(freq(c), 260)
    hrs = vals.get("hours", 0) + vals.get("overtime_hours", 0)
    if hrs > lim:
        why.append(f"{hrs:g} hours is over your limit of {lim:g} for one {freq(c).replace('ly', '')} period")
    if pid and not d:
        for f in vals:
            if (pid, f) in taken:
                why.append(f"{people[pid]['name']} already has {f.replace('_', ' ')} for {key} from {taken[(pid, f)]}")
                break
    return {"pid": pid, "near": near, "date": d, "values": vals}, why


def _rowsha(source: str, ref: str, row: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps([source, ref, row], sort_keys=True, default=str).encode()).hexdigest()[:24]


def take_rows(tenant: str, ws: str, rows: list[dict[str, Any]], source: str, period: str = "", ref: str = "",
              file: str = "", actor: str = "") -> dict[str, Any]:
    """Pay inputs in: each row checked, kept as checked or waiting with its reasons. The same row from the same place never twice."""
    c = _c(tenant, ws)
    key = str(period or period_of(c)["key"])
    if (((c.get("runs") or {}).get(key)) or {}).get("closed"):
        raise PayrollError(f"{key} is approved and locked; put these in the next period.")
    if len(rows) > 2000:
        raise PayrollError("Up to 2,000 rows at a time.")
    got = {"checked": 0, "waiting": 0, "already": 0}

    def ch(cfg):
        items = cfg.setdefault("inputs", [])
        seen = {i.get("sha") for i in items}
        taken = {}
        for i in items:
            if i["period"] == key and i["status"] == "checked" and not i.get("date"):
                for f in i.get("values") or {}:
                    taken[(i["pid"], f)] = i.get("file") or i["source"]
        live = {**cfg}
        for r in rows:
            r = {k: v for k, v in (r or {}).items() if k in ("name", "date") + FIELDS}
            sha = _rowsha(source, ref, r)
            if sha in seen:
                got["already"] += 1
                continue
            seen.add(sha)
            out, why = _check(live, key, r, taken)
            it = {"id": "pi_" + secrets.token_hex(5), "period": key, "source": source, "ref": str(ref)[:200], "file": str(file)[:120],
                  "name": str(r.get("name") or "")[:120], "pid": out["pid"], "near": out["near"], "date": out["date"],
                  "values": out["values"], "status": "waiting" if why else "checked", "why": why, "sha": sha,
                  "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "by": str(actor)[:120]}
            if not why and not out["date"]:
                for f in out["values"]:
                    taken[(out["pid"], f)] = it["file"] or source
            items.append(it)
            got["checked" if not why else "waiting"] += 1
        cfg["inputs"] = items[-5000:]
        return got
    _save(tenant, ws, ch)
    return {"period": key, **got, "says": f"{got['checked']} checked, {got['waiting']} waiting for you"
                                          + (f", {got['already']} already here" if got["already"] else "") + "."}


def inputs(tenant: str, ws: str, period: str = "", status: str = "") -> dict[str, Any]:
    c = _c(tenant, ws)
    key = str(period or period_of(c)["key"])
    items = [i for i in (c.get("inputs") or []) if i["period"] == key and (not status or i["status"] == status)]
    people = c.get("employees") or {}
    for i in items:
        i["person"] = (people.get(i["pid"]) or {}).get("name", "")
        i.pop("sha", None)
    cnt: dict[str, int] = {}
    for i in (c.get("inputs") or []):
        if i["period"] == key:
            cnt[i["status"]] = cnt.get(i["status"], 0) + 1
    return {"period": key, "items": sorted(items, key=lambda x: x["at"], reverse=True)[:500], "counts": cnt}


def match(tenant: str, ws: str, item: str, pid: str) -> dict[str, Any]:
    def ch(cfg):
        it = next((i for i in cfg.get("inputs") or [] if i["id"] == item), None)
        if not it:
            raise PayrollError("No such input.")
        if pid not in (cfg.get("employees") or {}):
            raise PayrollError("No such person.")
        it["pid"], it["near"] = pid, ""
        live = dict(cfg)
        taken = {(i["pid"], f): i.get("file") or i["source"] for i in cfg.get("inputs") or []
                 if i is not it and i["period"] == it["period"] and i["status"] == "checked" and not i.get("date") for f in i.get("values") or {}}
        out, why = _check(live, it["period"], {"name": cfg["employees"][pid]["name"], "date": it.get("date") or None,
                                               **it["values"]}, taken)
        it["why"], it["status"] = why, "waiting" if why else "checked"
        return dict(it)
    return {"input": _save(tenant, ws, ch)}


def drop(tenant: str, ws: str, item: str) -> dict[str, Any]:
    def ch(cfg):
        it = next((i for i in cfg.get("inputs") or [] if i["id"] == item), None)
        if not it:
            raise PayrollError("No such input.")
        it["status"] = "dropped"
        return {"dropped": item}
    return _save(tenant, ws, ch)


def extras_for(c: dict[str, Any], key: str, cur: str = "USD") -> dict[str, dict[str, Any]]:
    """The checked inputs of a period, summed per person, as the run's extras (overtime hours turned into pay by her multiplier)."""
    people = c.get("employees") or {}
    dc = desk_cfg(c)
    ppy = PY.PPY[freq(c)]
    out: dict[str, dict[str, float]] = {}
    for i in c.get("inputs") or []:
        if i["period"] != key or i["status"] != "checked" or i["pid"] not in people:
            continue
        x = out.setdefault(i["pid"], {})
        for f, v in (i.get("values") or {}).items():
            x[f] = round(x.get(f, 0) + float(v), 4)
    for pid, x in out.items():
        p = people[pid]
        oh = x.pop("overtime_hours", 0)
        x.pop("leave_days", None)                               # paid leave is paid: nothing changes in the pay
        if oh:
            pay = PY._u(int(p.get("pay_minor") or 0), cur)       # noqa: SLF001
            rate = pay if p.get("pay_kind") == "hourly" else (pay / ppy / float(dc["standard_hours"]) if p.get("pay_kind") == "annual"
                                                               else pay / float(dc["standard_hours"]))
            x["overtime"] = round(x.get("overtime", 0) + oh * rate * float(dc["overtime_x"]), 2)
            x["_oh"] = oh
    return out


def missing(tenant: str, ws: str, period: str = "") -> dict[str, Any]:
    """Who has no inputs yet: hourly people with no hours in the period."""
    c = _c(tenant, ws)
    key = str(period or period_of(c)["key"])
    s, e = bounds(c, key)
    have = {i["pid"] for i in c.get("inputs") or [] if i["period"] == key and i["status"] == "checked" and "hours" in (i.get("values") or {})}
    out = []
    for pid, p in sorted((c.get("employees") or {}).items()):
        if p.get("left") and p["left"] < s or p.get("start") and p["start"] > e:
            continue
        if p.get("pay_kind") == "hourly" and pid not in have:
            out.append({"id": pid, "name": p["name"], "email": p.get("email", ""), "what": "hours"})
    return {"period": key, "missing": out}


# ---------------------------------------------------------------- the run, its changes and its approval
def _hash(run: dict[str, Any]) -> str:
    core = [run["period"], run["totals"], [(p["id"], p["gross"], p["net"], p["tax"], p["ee"], p["er"]) for p in run["people"]]]
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()[:16]


def _flow(c: dict[str, Any], key: str) -> dict[str, Any]:
    return dict((c.get("flow") or {}).get(key) or {})


def prepare(tenant: str, ws: str, a: dict[str, Any], actor: str) -> dict[str, Any]:
    """Run a period from her people + the checked inputs (+ any extras she adds). Its approval resets if it changed."""
    c = _c(tenant, ws)
    key = str(a.get("period") or period_of(c)["key"])
    if _flow(c, key).get("status") in ("approved", "paid"):
        raise PayrollError(f"{key} is approved; it is never recalculated. Put a correction in the next period.")
    ex = extras_for(c, key, PY._cur(_w(tenant, ws)))              # noqa: SLF001
    for k, v in (a.get("extras") or {}).items():
        ex.setdefault(k, {}).update(v or {})
    oh = {k: v.pop("_oh") for k, v in ex.items() if "_oh" in v}
    run = PY.run_payroll(tenant, ws, {"period": key, "extras": ex})
    h = _hash(run)
    waiting = sum(1 for i in c.get("inputs") or [] if i["period"] == key and i["status"] == "waiting")
    miss = missing(tenant, ws, key)["missing"]

    def ch(cfg):
        fl = cfg.setdefault("flow", {})
        fl[key] = {"status": "draft", "hash": h, "prepared_by": str(actor)[:120], "prepared_at": date.today().isoformat(),
                   "overtime_hours": oh}
        return fl[key]
    _save(tenant, ws, ch)
    return {**run, "hash": h, "status": "draft", "changes": changes(tenant, ws, key)["people"], "waiting_inputs": waiting,
            "missing": miss}


def changes(tenant: str, ws: str, period: str) -> dict[str, Any]:
    """Each person's pay against the run before, with the reason taken from what really changed."""
    c = _c(tenant, ws)
    runs = c.get("runs") or {}
    r = runs.get(period)
    if not r:
        raise PayrollError(f"No payroll for {period}: run it first.")
    before = [k for k in sorted(runs) if k < period]
    prev = runs[before[-1]] if before else None
    pmap = {p["id"]: p for p in (prev or {}).get("people", [])}
    people = c.get("employees") or {}
    s, e = r["start"], r["end"]
    ex = extras_for(c, period, r["currency"])
    oh = _flow(c, period).get("overtime_hours") or {}
    out = []
    for p in r["people"]:
        why: list[str] = []
        q = people.get(p["id"]) or {}
        if q.get("start") and s <= q["start"] <= e:
            why.append(f"joined {q['start']}")
        if q.get("left") and s <= q["left"] <= e:
            why.append(f"leaves {q['left']}")
        for hst in q.get("pay_history") or []:
            if prev and prev["end"] < hst["on"] <= e or not prev and hst["on"] <= e and hst["on"] >= s:
                why.append(f"pay changed from {PY._u(hst['was'], r['currency'])} to {PY._u(hst['now'], r['currency'])}")   # noqa: SLF001
        x = ex.get(p["id"]) or {}
        if oh.get(p["id"]):
            why.append(f"{oh[p['id']]:g} h overtime")
        for f in ("bonus", "commission", "other_pay"):
            if x.get(f):
                why.append(f"{f.replace('_', ' ')} {x[f]:g}")
        if x.get("unpaid_days"):
            why.append(f"{x['unpaid_days']:g} unpaid days")
        old = pmap.get(p["id"])
        diff = round(p["gross"] - old["gross"], 2) if old else None
        if old is None and prev:
            why.insert(0, "new this period")
        if diff and not why:
            why.append("pay differs from last time")
        out.append({"id": p["id"], "name": p["name"], "gross": p["gross"], "net": p["net"], "before": old["gross"] if old else None,
                    "diff": diff, "why": why})
    gone = [{"id": k, "name": v["name"], "before": v["gross"], "why": ["not paid this period"]} for k, v in pmap.items()
            if k not in {p["id"] for p in r["people"]}]
    return {"period": period, "before": before[-1] if before else "", "people": out, "gone": gone,
            "changed": [x for x in out if x["why"]] + gone}


def _post_journal(tenant: str, ws: str, run: dict[str, Any], actor: str) -> dict[str, Any]:
    """The wage journal into Books & Accounts: wages + employer contributions, against what is owed to the people and the authorities."""
    from . import books as BK
    BK.ensure_coa(tenant, ws)
    have = {a["code"] for a in BK.coa(tenant, ws)}
    for code, name, typ in (("6310", "Employer payroll costs", "expense"), ("2210", "Wages payable", "liability"),
                            ("2220", "Payroll taxes and contributions payable", "liability"),
                            ("2230", "Pay deductions payable", "liability")):
        if code not in have:
            BK.add_account(tenant, ws, code, name, typ)
    w = BK._ws(tenant, ws)                                         # noqa: SLF001
    book = BK._book_cur(w)                                         # noqa: SLF001
    if run["currency"] != book:
        return {"posted": False, "why": f"The payroll is in {run['currency']} and the books in {book}; post it by hand with your rate."}
    m = lambda v: BK._m(v, book)                                   # noqa: E731,SLF001
    t = run["totals"]
    lines = [{"code": "6300", "debit_minor": m(t["gross"])}]
    if t["er"]:
        lines.append({"code": "6310", "debit_minor": m(t["er"])})
    lines.append({"code": "2210", "credit_minor": m(t["net"])})
    owed = m(t["tax"]) + m(t["ee"]) + m(t["er"])
    if owed:
        lines.append({"code": "2220", "credit_minor": owed})
    if t["pre_tax"]:
        lines.append({"code": "2230", "credit_minor": m(t["pre_tax"])})
    dr = sum(l.get("debit_minor", 0) for l in lines)
    cr = sum(l.get("credit_minor", 0) for l in lines)
    if dr != cr:                                                   # a rounding cent between the totals goes to the wages line
        lines[0]["debit_minor"] += cr - dr
    try:
        jid = BK.post(tenant, ws, run["end"], lines, memo=f"Payroll {run['period']}", source="payroll",
                      source_ref=f"payroll:{run['period']}", actor=actor)
    except BK.BooksError as e:
        return {"posted": False, "why": str(e)}
    return {"posted": True, "journal": jid}


def approve(tenant: str, ws: str, a: dict[str, Any], actor: str) -> dict[str, Any]:
    c = _c(tenant, ws)
    key = str(a.get("period") or "")
    r = (c.get("runs") or {}).get(key)
    fl = _flow(c, key)
    if not r or not fl:
        raise PayrollError(f"No payroll for {key} to approve: prepare it first.")
    if fl.get("status") in ("approved", "paid"):
        return {"period": key, "status": fl["status"], "says": "Already approved."}
    if str(a.get("hash") or "") != _hash(r) or fl.get("hash") != _hash(r):
        raise PayrollError("The payroll changed after you looked at it. Look at it again, then approve.")
    lim = float(desk_cfg(c).get("approve_limit") or 0)
    if lim and r["totals"]["net"] > lim and _who(fl.get("prepared_by")) == _who(actor):
        raise PayrollError(f"Net pay is over your limit of {lim:,.2f}: someone other than the person who prepared it approves it.")
    PY.close(tenant, ws, {"period": key})
    j = _post_journal(tenant, ws, r, actor)

    def ch(cfg):
        f = cfg.setdefault("flow", {}).setdefault(key, {})
        f.update({"status": "approved", "approved_by": str(actor)[:120], "approved_at": date.today().isoformat(),
                  "journal": j.get("journal", ""), "journal_why": j.get("why", "")})
        return dict(f)
    out = _save(tenant, ws, ch)
    return {"period": key, **out, "journal_posted": j.get("posted"),
            "says": f"{key} approved and locked." + (" The wage journal is in your books." if j.get("posted")
                                                     else f" The wage journal is not posted: {j.get('why')}") + " " + PY.NEVER_PAYS}


def _who(s: Any) -> str:
    m = re.search(r"<([^>]+)>", str(s or ""))
    return (m.group(1) if m else str(s or "")).strip().lower()


def unapprove(tenant: str, ws: str, a: dict[str, Any], actor: str) -> dict[str, Any]:
    raise PayrollError("An approved payroll is never reopened: put a correction in the next period.")


def post_journal(tenant: str, ws: str, a: dict[str, Any], actor: str) -> dict[str, Any]:
    c = _c(tenant, ws)
    key = str(a.get("period") or "")
    fl = _flow(c, key)
    if fl.get("status") not in ("approved", "paid"):
        raise PayrollError("Approve the payroll first.")
    if fl.get("journal"):
        return {"posted": True, "journal": fl["journal"]}
    j = _post_journal(tenant, ws, (c.get("runs") or {})[key], actor)

    def ch(cfg):
        cfg["flow"][key].update({"journal": j.get("journal", ""), "journal_why": j.get("why", "")})
        return j
    return _save(tenant, ws, ch)


# ---------------------------------------------------------------- paying (she pays) and Paid from the bank
def _xml(s: Any) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def pay_file(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    """The file for her bank: CSV (names, her payee references, amounts) or ISO 20022 pain.001 when she types each account for this
    one file. Only for an approved payroll."""
    w = _w(tenant, ws)
    c = PY._cfg(w)                                                 # noqa: SLF001
    key = str(a.get("period") or "")
    if _flow(c, key).get("status") not in ("approved", "paid"):
        raise PayrollError("The payment file is made from an approved payroll: approve it first.")
    r = c["runs"][key]
    people = c.get("employees") or {}
    pay = [(p, people.get(p["id"]) or {}) for p in r["people"] if p["net"] > 0]
    fmt = str(a.get("format") or "csv")
    ref = f"Pay {key}"
    if fmt == "csv":
        buf = io.StringIO()
        wr = csv.writer(buf)
        wr.writerow(["name", "payee_reference", "amount", "currency", "reference"])
        for p, q in pay:
            wr.writerow([p["name"], q.get("payee_ref", ""), f"{p['net']:.2f}", r["currency"], ref])
        return {"name": f"payroll-{key}.csv", "mime": "text/csv", "text": buf.getvalue(), "count": len(pay),
                "total": round(sum(p["net"] for p, _ in pay), 2), "says": PY.NEVER_PAYS}
    if fmt != "pain001":
        raise PayrollError("format: csv | pain001.")
    acc = a.get("accounts") or {}
    debtor = a.get("from") or {}
    iban = lambda v: re.sub(r"\s", "", str(v or "")).upper()        # noqa: E731
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", iban(debtor.get("iban"))):
        raise PayrollError("from.iban: the account you pay from (IBAN), for this file only.")
    bad = [p["name"] for p, _ in pay if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", iban((acc.get(p["id"]) or {}).get("iban")))]
    if bad:
        raise PayrollError("accounts: an IBAN for " + ", ".join(bad[:6]) + ". " + NEVER_KEPT)
    now = datetime.now(timezone.utc)
    mid = f"HOOLA-{key}-{now.strftime('%H%M%S')}"
    tot = sum(p["net"] for p, _ in pay)
    tx = "".join(
        f"<CdtTrfTxInf><PmtId><EndToEndId>{_xml((q.get('payee_ref') or p['id'])[:35])}</EndToEndId></PmtId>"
        f"<Amt><InstdAmt Ccy=\"{r['currency']}\">{p['net']:.2f}</InstdAmt></Amt>"
        + (f"<CdtrAgt><FinInstnId><BICFI>{_xml((acc.get(p['id']) or {}).get('bic'))}</BICFI></FinInstnId></CdtrAgt>" if (acc.get(p['id']) or {}).get("bic") else "")
        + f"<Cdtr><Nm>{_xml(p['name'][:70])}</Nm></Cdtr><CdtrAcct><Id><IBAN>{iban(acc[p['id']]['iban'])}</IBAN></Id></CdtrAcct>"
        f"<Purp><Cd>SALA</Cd></Purp><RmtInf><Ustrd>{_xml(ref)}</Ustrd></RmtInf></CdtTrfTxInf>" for p, q in pay)
    xml = ('<?xml version="1.0" encoding="UTF-8"?><Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"><CstmrCdtTrfInitn>'
           f"<GrpHdr><MsgId>{mid}</MsgId><CreDtTm>{now.isoformat(timespec='seconds')}</CreDtTm><NbOfTxs>{len(pay)}</NbOfTxs>"
           f"<CtrlSum>{tot:.2f}</CtrlSum><InitgPty><Nm>{_xml(w.get('name') or 'Employer')}</Nm></InitgPty></GrpHdr>"
           f"<PmtInf><PmtInfId>{mid}</PmtInfId><PmtMtd>TRF</PmtMtd><NbOfTxs>{len(pay)}</NbOfTxs><CtrlSum>{tot:.2f}</CtrlSum>"
           "<PmtTpInf><CtgyPurp><Cd>SALA</Cd></CtgyPurp></PmtTpInf>"
           f"<ReqdExctnDt><Dt>{_xml(a.get('pay_on') or date.today().isoformat())}</Dt></ReqdExctnDt>"
           f"<Dbtr><Nm>{_xml(w.get('name') or 'Employer')}</Nm></Dbtr><DbtrAcct><Id><IBAN>{iban(debtor['iban'])}</IBAN></Id></DbtrAcct>"
           + (f"<DbtrAgt><FinInstnId><BICFI>{_xml(debtor['bic'])}</BICFI></FinInstnId></DbtrAgt>" if debtor.get("bic")
              else "<DbtrAgt><FinInstnId><Othr><Id>NOTPROVIDED</Id></Othr></FinInstnId></DbtrAgt>")
           + tx + "</PmtInf></CstmrCdtTrfInitn></Document>")
    return {"name": f"payroll-{key}.xml", "mime": "application/xml", "text": xml, "count": len(pay), "total": round(tot, 2),
            "says": PY.NEVER_PAYS + " " + NEVER_KEPT}


def paid_check(tenant: str, ws: str, period: str = "") -> dict[str, Any]:
    """Paid = bank lines in Bank & matching cover the net pay: one line for the whole run, or a line per person (amount, and the name
    in the line's words). Lines from 5 days before approval onwards."""
    from . import books as BK
    c = _c(tenant, ws)
    out = []
    for key, fl in sorted((c.get("flow") or {}).items()):
        if period and key != period or fl.get("status") != "approved":
            continue
        r = (c.get("runs") or {}).get(key)
        if not r:
            continue
        cur = r["currency"]
        since = (date.fromisoformat(fl.get("approved_at") or r["end"]) - timedelta(days=5)).isoformat()
        try:
            lines = [l for l in BK._bank_lines(tenant, ws, since=since) if l["amount_minor"] < 0]   # noqa: SLF001
        except Exception:   # noqa: BLE001
            lines = []
        total = PY._m(r["totals"]["net"], cur, "net")               # noqa: SLF001
        hit = next((l for l in lines if -l["amount_minor"] == total), None)
        found, used = [], set()
        if hit:
            found = [hit["id"]]
        else:
            for p in r["people"]:
                want = PY._m(p["net"], cur, "net")                  # noqa: SLF001
                first = _norm(p["name"]).split(" ")[0] if p["name"] else ""
                l = next((l for l in lines if l["id"] not in used and -l["amount_minor"] == want and first and first in _norm(l["narration"])), None)
                if l:
                    used.add(l["id"])
                    found.append(l["id"])
            if len(found) < len([p for p in r["people"] if p["net"] > 0]):
                out.append({"period": key, "paid": False, "found": len(found), "of": len(r["people"])})
                continue

        def ch(cfg, key=key, found=found):
            cfg["flow"][key].update({"status": "paid", "paid_on": date.today().isoformat(), "paid_lines": found})
            return True
        _save(tenant, ws, ch)
        out.append({"period": key, "paid": True, "lines": found})
    return {"runs": out}


# ---------------------------------------------------------------- payslips in each person's language
LABELS = {
    "en": {"t": "Payslip", "g": "Gross pay", "pre": "Before-tax deduction", "tax": "Income tax", "net": "Net pay",
           "er": "Paid by your employer on top (not taken from your pay)", "rules": "Rules", "p": "Period", "final": "Final", "draft": "Draft"},
    "hi": {"t": "वेतन पर्ची", "g": "कुल वेतन", "pre": "कर से पहले कटौती", "tax": "आयकर", "net": "शुद्ध वेतन",
           "er": "नियोक्ता द्वारा अलग से दिया गया (आपके वेतन से नहीं कटा)", "rules": "नियम", "p": "अवधि", "final": "अंतिम", "draft": "मसौदा"},
    "es": {"t": "Nómina", "g": "Salario bruto", "pre": "Deducción antes de impuestos", "tax": "Impuesto sobre la renta", "net": "Salario neto",
           "er": "Pagado además por su empleador (no se descuenta de su salario)", "rules": "Reglas", "p": "Periodo", "final": "Final", "draft": "Borrador"},
    "fr": {"t": "Bulletin de paie", "g": "Salaire brut", "pre": "Déduction avant impôt", "tax": "Impôt sur le revenu", "net": "Salaire net",
           "er": "Payé en plus par votre employeur (non retenu sur votre salaire)", "rules": "Règles", "p": "Période", "final": "Définitif", "draft": "Brouillon"},
    "de": {"t": "Gehaltsabrechnung", "g": "Bruttolohn", "pre": "Abzug vor Steuern", "tax": "Lohnsteuer", "net": "Nettolohn",
           "er": "Zusätzlich vom Arbeitgeber gezahlt (nicht von Ihrem Lohn abgezogen)", "rules": "Regeln", "p": "Zeitraum", "final": "Endgültig", "draft": "Entwurf"},
    "pt": {"t": "Recibo de vencimento", "g": "Salário bruto", "pre": "Dedução antes do imposto", "tax": "Imposto sobre o rendimento", "net": "Salário líquido",
           "er": "Pago a mais pelo seu empregador (não descontado do seu salário)", "rules": "Regras", "p": "Período", "final": "Final", "draft": "Rascunho"},
    "mr": {"t": "पगार पावती", "g": "एकूण पगार", "pre": "करापूर्वी कपात", "tax": "आयकर", "net": "निव्वळ पगार",
           "er": "मालकाने वेगळे भरलेले (तुमच्या पगारातून नाही)", "rules": "नियम", "p": "कालावधी", "final": "अंतिम", "draft": "मसुदा"},
}


def _font(lang: str) -> str:
    from pathlib import Path
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if lang in ("hi", "mr"):
        f = Path(__file__).resolve().parents[2] / "fonts" / "NotoSansDevanagari-Regular.ttf"
        if f.exists():
            try:
                pdfmetrics.registerFont(TTFont("HoolaDeva", str(f)))
                return "HoolaDeva"
            except Exception:   # noqa: BLE001
                pass
    return "Helvetica"


def payslip_pdf(tenant: str, ws: str, period: str, who: str) -> tuple[str, bytes, str]:
    """One person's payslip as a PDF in their language (en, hi, es, fr, de, pt, mr; any other language = English, said on the slip)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    w = _w(tenant, ws)
    c = PY._cfg(w)                                                 # noqa: SLF001
    r = (c.get("runs") or {}).get(period)
    if not r:
        raise PayrollError(f"No payroll for {period}.")
    p = next((x for x in r["people"] if x["id"] == who or x["name"].lower() == str(who).lower()), None)
    if not p:
        raise PayrollError("No such person in this payroll.")
    q = (c.get("employees") or {}).get(p["id"]) or {}
    lang = str(q.get("lang") or "en").lower()[:2]
    L = LABELS.get(lang) or LABELS["en"]
    font = _font(lang if lang in LABELS else "en")
    if font == "Helvetica" and lang in ("hi", "mr"):
        L = LABELS["en"]
    bio = io.BytesIO()
    cv = canvas.Canvas(bio, pagesize=A4)
    W, H = A4
    y = H - 22 * mm
    cv.setFont(font, 15)
    cv.drawString(20 * mm, y, f"{w.get('name') or ''} - {L['t']}")
    y -= 9 * mm
    cv.setFont(font, 10)
    cv.drawString(20 * mm, y, f"{p['name']}{(' · ' + q['role']) if q.get('role') else ''}")
    cv.drawRightString(W - 20 * mm, y, f"{L['p']}: {r['start']} - {r['end']}  ({r['currency']})")
    y -= 12 * mm
    rows = [(L["g"], p["gross"])]
    if p.get("pre_tax"):
        rows.append((L["pre"], -p["pre_tax"]))
    rows.append((L["tax"], -p["tax"]))
    rows += [(x["name"], -x["employee"]) for x in p.get("contributions") or [] if x["employee"]]
    for k, v in rows:
        cv.drawString(20 * mm, y, str(k)[:70])
        cv.drawRightString(W - 20 * mm, y, f"{v:,.2f}")
        y -= 6.5 * mm
    y -= 3 * mm
    cv.setFont(font, 12)
    cv.drawString(20 * mm, y, L["net"])
    cv.drawRightString(W - 20 * mm, y, f"{p['net']:,.2f} {r['currency']}")
    y -= 11 * mm
    er = [x for x in p.get("contributions") or [] if x["employer"]]
    if er:
        cv.setFont(font, 9)
        cv.drawString(20 * mm, y, L["er"])
        y -= 6 * mm
        for x in er:
            cv.drawString(24 * mm, y, x["name"][:70])
            cv.drawRightString(W - 20 * mm, y, f"{x['employer']:,.2f}")
            y -= 5.5 * mm
    y -= 6 * mm
    cv.setFont("Helvetica", 8)
    note = f"{L['rules'] if font != 'Helvetica' or lang not in ('hi', 'mr') else 'Rules'}: {r.get('source') or '-'}."
    cv.drawString(20 * mm, y, note[:150])
    y -= 5 * mm
    cv.drawString(20 * mm, y, ("Final" if r.get("closed") else "DRAFT - not approved yet") +
                  ("" if lang in LABELS else f" · Printed in English: Hoola has no payslip words for '{lang}' yet."))
    cv.showPage()
    cv.save()
    safe = re.sub(r"[^A-Za-z0-9]+", "-", p["name"]).strip("-") or "person"
    return f"payslip-{period}-{safe}.pdf", bio.getvalue(), q.get("email", "")


def payslip_drafts(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    """Her tap: each approved payslip as an email with the PDF, put in her mailbox's Drafts folder. She sends them; Hoola sends nothing."""
    c = _c(tenant, ws)
    key = str(a.get("period") or "")
    if _flow(c, key).get("status") not in ("approved", "paid"):
        raise PayrollError("Payslips go out from an approved payroll: approve it first.")
    from ...mailbox import mime
    from ...mailbox.accounts import get_box
    try:
        box = get_box(tenant, str(a.get("account") or "") or None)
    except Exception as e:   # noqa: BLE001
        raise PayrollError(f"Connect the email you send payslips from first ({str(e)[:100]}).")
    made, skipped = 0, []
    w = _w(tenant, ws)
    for p in c["runs"][key]["people"]:
        name, data, to = payslip_pdf(tenant, ws, key, p["id"])
        if not to:
            skipped.append(p["name"])
            continue
        msg = mime.build(from_addr=box.address, from_name=w.get("name") or "", to=to, subject=f"Your payslip for {key}",
                         body=f"Hello {p['name'].split(' ')[0]},\n\nYour payslip for {key} is attached.\n\n{w.get('name') or ''}",
                         files=[(name, "application/pdf", data)])
        try:
            box.save_draft(msg)
            made += 1
        except Exception as e:   # noqa: BLE001
            raise PayrollError(f"Your mailbox did not take the drafts: {str(e)[:120]}")
    return {"drafts": made, "no_email": skipped, "account": box.address,
            "says": f"{made} payslip email{'s' if made != 1 else ''} in the Drafts of {box.address}. Open your mailbox and send them."
                    + (f" No email for: {', '.join(skipped[:6])}." if skipped else "")}


# ---------------------------------------------------------------- Step 3: country rules with help
def starting_list(cc: str) -> dict[str, Any]:
    from .. import pack as P
    cc = str(cc or "").upper()[:2]
    try:
        v = P.peek(cc, "payroll.starting_list")
    except Exception:   # noqa: BLE001
        v = None
    try:
        system = P.peek(cc, "payroll.system")
    except Exception:   # noqa: BLE001
        system = None
    where = ""
    try:
        leaf = ((P.load(cc) or {}).get("sections", {}).get("payroll", {}) or {}).get("starting_list") or {}
        where = leaf.get("where_to_check", "")
    except Exception:   # noqa: BLE001
        pass
    return {"country": cc, "system": system, "list": v, "where": where,
            "says": ("A starting list from memory: every rule in it is marked 'check this' and is not used until a person checks it."
                     if v else "Hoola has no starting list for this country: put your own rules in, each with where it comes from.")}


def apply_starting_list(tenant: str, ws: str, a: dict[str, Any], actor: str) -> dict[str, Any]:
    w = _w(tenant, ws)
    cc = str(a.get("country") or (PY._cfg(w).get("country")) or (w.get("countries") or [""])[0]).upper()   # noqa: SLF001
    st = starting_list(cc)
    t = st["list"]
    if not t:
        raise PayrollError(st["says"])
    clean = lambda x: {k: v for k, v in x.items() if k != "note"}   # noqa: E731
    PY.save_settings(tenant, ws, {"country": cc, "frequency": a.get("frequency") or t.get("frequency") or "monthly",
                                  "source": f"Hoola's starting list for {cc} - check each rule at {st['where'] or 'the official page'}",
                                  "contributions": [clean(x) for x in t.get("contributions") or []],
                                  "income_tax": clean(t.get("income_tax") or {"method": "none"}) | {"bands": (t.get("income_tax") or {}).get("bands") or []},
                                  "filings": t.get("filings") or [], "_keep_meta": True})
    notes = {x["name"]: x.get("note", "") for x in t.get("contributions") or []}

    def ch(cfg):
        meta = {f"contribution:{x['name']}": {"status": "check", "note": notes.get(x["name"], ""), "from": f"starting list {cc}"}
                for x in t.get("contributions") or []}
        meta["income_tax"] = {"status": "check", "note": (t.get("income_tax") or {}).get("note", ""), "from": f"starting list {cc}"}
        cfg["rules_meta"] = meta
        return meta
    meta = _save(tenant, ws, ch)
    return {"country": cc, "rules": len(meta), "where": st["where"],
            "says": f"{len(meta)} rules put in, each marked 'check this'. Check each against its official page; the payroll runs once all are checked."}


def rules(tenant: str, ws: str) -> dict[str, Any]:
    c = _c(tenant, ws)
    meta = c.get("rules_meta") or {}
    out = []
    for x in c.get("contributions") or []:
        m = meta.get(f"contribution:{x['name']}") or {"status": "checked", "by": "you", "source": c.get("source", "")}
        out.append({"key": f"contribution:{x['name']}", "name": x["name"], "rule": x, **m})
    it = c.get("income_tax")
    if it:
        m = meta.get("income_tax") or {"status": "checked", "by": "you", "source": c.get("source", "")}
        out.append({"key": "income_tax", "name": "Income tax", "rule": it, **m})
    cc = str(c.get("country") or "")
    return {"country": cc, "frequency": freq(c), "source": c.get("source", ""), "rules": out,
            "to_check": [r["name"] for r in out if r["status"] != "checked"], "filings": c.get("filings") or [],
            "pay_day": c.get("pay_day"), "where": starting_list(cc)["where"] if cc else ""}


def check_rule(tenant: str, ws: str, a: dict[str, Any], actor: str) -> dict[str, Any]:
    """A person checked one rule against its official page: the page, the date, who. A changed value replaces the starting one."""
    key = str(a.get("key") or "")
    src = str(a.get("source") or "").strip()
    if not re.match(r"https?://", src) and len(src) < 8:
        raise PayrollError("source: the official page you checked it on (its address), or who gave you the rate.")
    c = _c(tenant, ws)
    if a.get("rule") is not None:          # she corrected the value while checking
        if key == "income_tax":
            PY.save_settings(tenant, ws, {"income_tax": a["rule"], "source": c.get("source") or src, "_keep_meta": True})
        elif key.startswith("contribution:"):
            name = key.split(":", 1)[1]
            cons = [dict(a["rule"], name=name) if x["name"] == name else x for x in c.get("contributions") or []]
            PY.save_settings(tenant, ws, {"contributions": cons, "source": c.get("source") or src, "_keep_meta": True})

    def ch(cfg):
        meta = cfg.setdefault("rules_meta", {})
        if key not in meta:
            raise PayrollError("No such rule waiting for a check.")
        meta[key].update({"status": "checked", "source": src[:300], "checked_on": date.today().isoformat(), "by": str(actor)[:120]})
        return {"key": key, **meta[key], "left": sum(1 for m in meta.values() if m.get("status") != "checked")}
    return _save(tenant, ws, ch)


def import_old(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    """People from the older India payroll into this business (name, monthly pay, start, PAN masked). Their old runs stay there."""
    from ...db import session
    from ...payroll import service as OLD
    OLD.ensure() if hasattr(OLD, "ensure") else None
    made, kept = 0, 0
    with session() as s:
        try:
            rows = s.query(OLD.PayEmployee).filter(OLD.PayEmployee.tenant_id == tenant).all()
        except Exception:   # noqa: BLE001
            rows = []
        old = [(e.name, e.pay, e.doj, e.dol, e.pan, e.designation) for e in rows if e.name]
    have = {_norm(p["name"]) for p in (_c(tenant, ws).get("employees") or {}).values()}
    for name, pay, doj, dol, pan, desig in old:
        if _norm(name) in have:
            kept += 1
            continue
        try:
            monthly = sum(float(v or 0) for v in json.loads(pay or "{}").values())
        except (ValueError, AttributeError):
            monthly = 0
        if monthly <= 0:
            continue
        try:
            pan_txt = OLD._open(pan) if pan else ""                # noqa: SLF001
        except Exception:   # noqa: BLE001
            pan_txt = ""
        PY.employee(tenant, ws, {"name": name, "per_period": monthly, "start": doj or None, "tax_id": pan_txt or None,
                                 "role": desig or None})
        if dol:
            PY.employee(tenant, ws, {"name": name, "leave": True, "left_on": dol})
        made += 1
    return {"moved": made, "already_here": kept, "says": f"{made} people moved over from the older payroll"
            + (f", {kept} already here" if kept else "") + ". Their past payrolls stay readable in the older payroll."}


# ---------------------------------------------------------------- desk settings and where inputs come from
def desk_settings(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    upd: dict[str, Any] = {}
    for k in ("approve_limit", "overtime_x", "standard_hours"):
        if a.get(k) not in (None, ""):
            v = _num(a[k])
            if v is None or v < 0:
                raise PayrollError(f"{k}: a number, not below 0.")
            upd[k] = v
    if a.get("max_hours") not in (None, ""):
        v = _num(a["max_hours"])
        if not v or v <= 0:
            raise PayrollError("max_hours: a number above 0.")
        upd["max_hours_now"] = v
    if "sheet" in a:
        sh = a.get("sheet") or {}
        upd["sheet"] = {"spreadsheet": str(sh.get("spreadsheet") or "").strip()[:200], "tab": str(sh.get("tab") or "").strip()[:80]} if sh.get("spreadsheet") else {}
    if "software" in a:
        upd["software"] = [k for k in (a.get("software") or []) if k in SOFTWARE]
    if a.get("pay_day") not in (None, ""):
        PY.save_settings(tenant, ws, {"pay_day": int(a["pay_day"]), "_keep_meta": True})

    def ch(cfg):
        d = desk_cfg(cfg)
        if "max_hours_now" in upd:
            d["max_hours"][freq(cfg)] = upd.pop("max_hours_now")
        d.update(upd)
        cfg["desk"] = d
        return {k: v for k, v in d.items() if k != "hook_hash"}
    return {"desk": _save(tenant, ws, ch)}


def api_key(tenant: str, ws: str) -> dict[str, Any]:
    tok = "py_" + secrets.token_urlsafe(24)
    h = hashlib.sha256(tok.encode()).hexdigest()

    def ch(cfg):
        d = desk_cfg(cfg)
        d["hook_hash"] = h
        cfg["desk"] = d
        return True
    _save(tenant, ws, ch)
    return {"key": tok, "url": "/api/payroll/in", "header": "Authorization: Bearer <key>",
            "body": '{"period": "2026-11", "rows": [{"name": "Anil Kumar", "hours": 152, "overtime_hours": 6}]}',
            "says": "Copy it now - Hoola keeps only a fingerprint of it. Making a new one stops the old one."}


def api_stop(tenant: str, ws: str) -> dict[str, Any]:
    def ch(cfg):
        d = desk_cfg(cfg)
        d["hook_hash"] = ""
        cfg["desk"] = d
        return True
    _save(tenant, ws, ch)
    return {"stopped": True}


def _all_ws():
    from ... import db
    from ..models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        for w in s.query(FinWorkspace).filter(FinWorkspace.status == "active").all():
            st = json.loads(w.settings or "{}")
            if st.get("payroll"):
                yield w.tenant_id, w.id, st["payroll"]


def ws_of_key(tok: str) -> tuple[str, str] | None:
    if not str(tok or "").startswith("py_"):
        return None
    h = hashlib.sha256(str(tok).encode()).hexdigest()
    for t, w, c in _all_ws():
        if (c.get("desk") or {}).get("hook_hash") == h:
            return t, w
    return None


def mail_attach(tenant: str, ws: str, address: str) -> dict[str, Any]:
    from . import books_feed as BF
    a = str(address or "").strip().lower()
    if a not in {str(b.get("address") or "").lower() for b in BF._boxes(tenant)}:          # noqa: SLF001
        raise PayrollError("That email is not connected to Hoola yet - connect it first (Gmail, Outlook or another email).")

    def ch(cfg):
        d = desk_cfg(cfg)
        d["mail"] = [x for x in d.get("mail") or [] if x != a] + [a]
        d["mail_since"] = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        cfg["desk"] = d
        return d["mail"]
    return {"mail": _save(tenant, ws, ch), "says": f"Timesheets, hours and leave mailed to {a} now come into the payroll."}


def mail_detach(tenant: str, ws: str, address: str) -> dict[str, Any]:
    a = str(address or "").strip().lower()

    def ch(cfg):
        d = desk_cfg(cfg)
        d["mail"] = [x for x in d.get("mail") or [] if x != a]
        cfg["desk"] = d
        return d["mail"]
    return {"mail": _save(tenant, ws, ch)}


def sheet_read(tenant: str, ws: str, actor: str = "hoola") -> dict[str, Any]:
    c = _c(tenant, ws)
    sh = desk_cfg(c).get("sheet") or {}
    if not sh.get("spreadsheet"):
        raise PayrollError("No sheet set: put your timesheet sheet's link in Payroll > Inputs.")
    from ...sheets import service as SS
    recs: list[dict[str, Any]] = []
    try:
        while len(recs) < 2000:
            got = SS.read(tenant, sh["spreadsheet"], sh.get("tab") or None, None, 300, len(recs))
            page = got.get("rows") or []
            recs += page
            if len(page) < 300 or len(recs) >= int(got.get("total_rows") or 0):
                break
    except Exception as e:   # noqa: BLE001
        raise PayrollError(f"The sheet could not be read: {str(e)[:160]}")
    hdr = [h for h in (recs[0].keys() if recs else []) if h != "_row"]
    table = [hdr] + [[r.get(h) for h in hdr] for r in recs] if recs else []
    rows = rows_of_table(table)
    return take_rows(tenant, ws, rows, "sheet", ref=sh["spreadsheet"] + "#" + (sh.get("tab") or ""), file="Timesheet sheet", actor=actor)


def _records(data: Any) -> list[dict[str, Any]]:
    from .books_feed import _records as R
    return R(data)


def _rec_row(rec: dict[str, Any]) -> dict[str, Any]:
    flat = {}
    for k, v in rec.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                flat[f"{k}_{k2}".lower()] = v2
        else:
            flat[str(k).lower()] = v
    name = next((flat[k] for k in flat if re.search(r"(employee|user|staff|member|person)_?(full_?)?name|^name$|display_?name", k) and flat[k]), "")
    secs = next((flat[k] for k in flat if re.search(r"seconds|duration", k) and isinstance(flat[k], (int, float))), None)
    hrs = next((flat[k] for k in flat if re.search(r"^(total_)?hours|hours_worked|hours$", k) and _num(flat[k]) is not None), None)
    day = next((flat[k] for k in flat if re.search(r"^date$|start(_time|_date)?$|^day$", k) and flat[k]), "")
    row = {"name": str(name)}
    if hrs is not None:
        row["hours"] = _num(hrs)
    elif secs is not None:
        row["hours"] = round(float(secs) / 3600, 2)
    if day:
        row["date"] = str(day)[:10]
    return row


async def software_read(tenant: str, ws: str) -> dict[str, Any]:
    """Her connected time / HR programs: their own READ tools that list timesheets, hours or shifts; each record becomes an input row."""
    import asyncio
    c = _c(tenant, ws)
    kits = desk_cfg(c).get("software") or []
    if not kits:
        return {"read": 0, "says": "No program ticked."}
    try:
        from ...bazar import composio as C
        from ...db import session
    except Exception:   # noqa: BLE001
        return {"read": 0}
    if not C.configured():
        return {"read": 0, "says": "Connectors are not set up on this server."}
    got = {"checked": 0, "waiting": 0, "already": 0}
    for kit in kits:
        try:
            with session() as s:
                _c0, ca = C.account(s, tenant, kit)
                s.commit()
            if not ca:
                continue
            tools = []
            for w in ("timesheet", "time", "shift"):
                tools += await asyncio.to_thread(C.tool_list, kit, w, False, 40)
        except Exception as e:   # noqa: BLE001
            log.info("payroll software %s %s: %s", tenant, kit, e)
            continue
        seen: set[str] = set()
        for t in tools:
            slug = str(t.get("slug") or "").upper()
            if slug in seen or not re.search(r"(LIST|QUERY|SEARCH|GET_ALL|FETCH)", slug) or not re.search(r"(TIMESHEET|TIME_ENTR|SHIFT|HOURS|ATTENDANCE)", slug):
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
                log.info("payroll software %s %s: %s", kit, slug, e)
                continue
            if not res.get("successful", True):
                continue
            rows = [r for r in (_rec_row(x) for x in _records(res.get("data"))) if r.get("name") and r.get("hours") is not None]
            if rows:
                r = take_rows(tenant, ws, rows, "software", ref=f"{kit}:{slug}", file=SOFTWARE.get(kit, kit))
                for k in got:
                    got[k] += r.get(k, 0)
    return {**got, "says": f"{got['checked']} checked, {got['waiting']} waiting from your programs."}


def take_file(tenant: str, ws: str, name: str, data: bytes, ref: str, source: str = "upload", actor: str = "") -> dict[str, Any]:
    if len(data) > 10 * 1024 * 1024:
        raise PayrollError("The file is over 10 MB.")
    return take_rows(tenant, ws, rows_of_file(name, data), source, ref=ref or hashlib.sha256(data).hexdigest()[:16], file=name, actor=actor)


WORDS = re.compile(r"timesheet|time sheet|hours|attendance|overtime|rota|leave|payroll|shift", re.I)


async def mail_tick(tenant: str, ws: str) -> int:
    """Her attached payroll email: new mails with a CSV / Excel timesheet become input rows."""
    import asyncio
    from ...mailbox import service as MS
    c = _c(tenant, ws)
    d = desk_cfg(c)
    boxes = set(d.get("mail") or [])
    if not boxes:
        return 0
    try:
        since = datetime.fromisoformat(d.get("mail_since") or "")
    except ValueError:
        since = datetime.now(timezone.utc) - timedelta(days=3)
    started = datetime.now(timezone.utc)
    try:
        got = await asyncio.to_thread(MS.check, tenant, "inbox", False, None, 60, "all", since, True)
    except Exception as e:   # noqa: BLE001
        log.info("payroll mail %s: %s", tenant, e)
        return 0
    made = 0
    seen = {i.get("ref", "").split("#")[0] for i in c.get("inputs") or [] if i.get("source") == "email"}
    for m in got.get("emails") or []:
        if str(m.get("account") or "").lower() not in boxes or not m.get("has_attachments") or str(m.get("id")) in seen:
            continue
        if not WORDS.search(" ".join(str(m.get(k) or "") for k in ("subject", "snippet"))):
            continue
        try:
            full = await asyncio.to_thread(MS.read, tenant, m["id"], False, False)
        except Exception:   # noqa: BLE001
            continue
        for a in (full.get("attachments") or [])[:5]:
            nm = str(a.get("name") or a.get("filename") or "")
            if not nm.lower().endswith(FILE_EXT):
                continue
            try:
                nm2, _t, data = await asyncio.to_thread(MS.attachment, tenant, m["id"], str(a.get("id")))
                take_file(tenant, ws, nm2 or nm, data, f"{m['id']}#{a.get('id')}", "email", str(full.get("from_email") or "")[:120])
                made += 1
            except PayrollError as e:
                log.info("payroll mail file %s: %s", m["id"], e)
            except Exception:   # noqa: BLE001
                continue

    def ch(cfg):
        dd = desk_cfg(cfg)
        dd["mail_since"] = started.isoformat()
        cfg["desk"] = dd
        return True
    _save(tenant, ws, ch)
    return made


async def tick() -> int:
    """Every half hour: payroll emails, the sheet, the programs, and the Paid check of approved payrolls."""
    import asyncio
    n = 0
    for t, w, c in list(_all_ws()):
        d = desk_cfg(c)
        try:
            if d.get("mail"):
                n += await mail_tick(t, w)
            if (d.get("sheet") or {}).get("spreadsheet"):
                n += (await asyncio.to_thread(sheet_read, t, w)).get("checked", 0)
            if d.get("software"):
                n += (await software_read(t, w)).get("checked", 0)
            if any(f.get("status") == "approved" for f in (c.get("flow") or {}).values()):
                await asyncio.to_thread(paid_check, t, w)
        except Exception as e:   # noqa: BLE001
            log.info("payroll tick %s %s: %s", t, w, e)
    return n


# ---------------------------------------------------------------- the desk's summary
def desk(tenant: str, ws: str) -> dict[str, Any]:
    w = _w(tenant, ws)
    c = PY._cfg(w)                                                 # noqa: SLF001
    per = period_of(c)
    key = per["key"]
    people = c.get("employees") or {}
    active = [p for p in people.values() if not p.get("left")]
    flow = (c.get("flow") or {})
    runs = c.get("runs") or {}
    last = sorted(runs)[-1] if runs else ""
    cnt = inputs(tenant, ws, key)["counts"]
    meta = c.get("rules_meta") or {}
    pay_day = c.get("pay_day")
    if freq(c) == "monthly":
        e = date.fromisoformat(per["end"])
        pd_ = e.replace(day=min(int(pay_day), e.day)) if pay_day else e
    else:
        pd_ = date.fromisoformat(per["end"])
    try:
        fil = PY.filings(tenant, ws, {"year": date.today().year})["items"] if c.get("filings") else []
    except Exception:   # noqa: BLE001
        fil = []
    soon = [f for f in fil if f["status"] != "done" and f["due"] <= (date.today() + timedelta(days=10)).isoformat()]
    f = flow.get(key) or {}
    return {"period": key, "start": per["start"], "end": per["end"], "frequency": freq(c), "country": c.get("country") or "",
            "pay_day": pd_.isoformat(), "people": len(active), "currency": PY._cur(w),            # noqa: SLF001
            "run": {"status": f.get("status") or ("none" if key not in runs else "draft"), "hash": f.get("hash", ""),
                    "totals": (runs.get(key) or {}).get("totals"), "prepared_by": f.get("prepared_by", ""),
                    "approved_by": f.get("approved_by", ""), "journal": bool(f.get("journal")), "journal_why": f.get("journal_why", "")},
            "last_run": {"period": last, "totals": (runs.get(last) or {}).get("totals"), "status": (flow.get(last) or {}).get("status", "draft")} if last else None,
            "inputs": cnt, "missing": missing(tenant, ws, key)["missing"],
            "rules_set": bool(c.get("contributions") or c.get("income_tax")),
            "rules_to_check": [k.split(":", 1)[-1] if k != "income_tax" else "Income tax" for k, m in meta.items() if m.get("status") != "checked"],
            "no_tax_id": [p["name"] for p in active if not p.get("tax_id")],
            "filings_soon": soon[:6], "overdue_filings": [x for x in fil if x["status"] == "overdue"][:6],
            "awaiting_paid": [k for k, v in flow.items() if v.get("status") == "approved"],
            "sources": {"mail": desk_cfg(c).get("mail") or [], "sheet": desk_cfg(c).get("sheet") or {},
                        "software": desk_cfg(c).get("software") or [], "api_on": bool(desk_cfg(c).get("hook_hash"))},
            "approve_limit": desk_cfg(c).get("approve_limit") or 0}


# ---------------------------------------------------------------- door
def run(tenant: str, action: str, ws: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    if action == "desk":
        return desk(tenant, ws)
    if action == "inputs":
        return inputs(tenant, ws, str(a.get("period") or ""), str(a.get("status") or ""))
    if action == "input_rows":
        return take_rows(tenant, ws, a.get("rows") or [], str(a.get("source_name") or "chat"), str(a.get("period") or ""),
                         str(a.get("ref") or ""), str(a.get("file") or ""), actor)
    if action == "input_match":
        return match(tenant, ws, str(a.get("item") or ""), str(a.get("person") or ""))
    if action == "input_drop":
        return drop(tenant, ws, str(a.get("item") or ""))
    if action == "missing":
        return missing(tenant, ws, str(a.get("period") or ""))
    if action == "changes":
        return changes(tenant, ws, str(a.get("period") or period_of(_c(tenant, ws))["key"]))
    if action == "prepare":
        return prepare(tenant, ws, a, actor)
    if action == "approve":
        return approve(tenant, ws, a, actor)
    if action == "unapprove":
        return unapprove(tenant, ws, a, actor)
    if action == "post_journal":
        return post_journal(tenant, ws, a, actor)
    if action == "pay_file":
        return pay_file(tenant, ws, a)
    if action == "paid_check":
        return paid_check(tenant, ws, str(a.get("period") or ""))
    if action == "payslip_pdf":
        name, data, _ = payslip_pdf(tenant, ws, str(a.get("period") or ""), str(a.get("employee") or ""))
        import base64
        return {"name": name, "pdf_b64": base64.b64encode(data).decode()}
    if action == "payslip_drafts":
        return payslip_drafts(tenant, ws, a)
    if action == "starting_list":
        return starting_list(str(a.get("country") or ""))
    if action == "apply_starting_list":
        return apply_starting_list(tenant, ws, a, actor)
    if action == "check_rule":
        return check_rule(tenant, ws, a, actor)
    if action == "rules":
        return rules(tenant, ws)
    if action == "import_old":
        return import_old(tenant, ws, a)
    if action == "desk_settings":
        return desk_settings(tenant, ws, a)
    if action == "api_key":
        return api_key(tenant, ws)
    if action == "api_stop":
        return api_stop(tenant, ws)
    if action == "mail_attach":
        return mail_attach(tenant, ws, str(a.get("address") or ""))
    if action == "mail_detach":
        return mail_detach(tenant, ws, str(a.get("address") or ""))
    if action == "sheet_read":
        return sheet_read(tenant, ws, actor)
    if action == "mailboxes":
        from . import books_feed as BF
        d = desk_cfg(_c(tenant, ws))
        return {"boxes": [str(b.get("address") or "").lower() for b in BF._boxes(tenant) if b.get("address")],   # noqa: SLF001
                "attached": d.get("mail") or [], "software": SOFTWARE, "ticked": d.get("software") or [],
                "sheet": d.get("sheet") or {}, "api_on": bool(d.get("hook_hash"))}
    if action == "software_read":
        import asyncio
        return asyncio.run(software_read(tenant, ws))
    raise PayrollError("action: " + ", ".join(ACTIONS))
