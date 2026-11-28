"""The Labour & Wages desk's core: settings, sites, employers (her company and the subcontractors), workers, papers and the
renewal radar, pay rates and floor rows, the worker import and the old labour rows brought in once.

Ids and account numbers are never kept whole: only the last 4 (the full number lives in her Pehchaan Locker). A minimum
(floor) rate row without a source is kept but says "no source written"; Hoola never supplies a minimum rate."""
from __future__ import annotations

import csv
import difflib
import io
import logging
import math
import re
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import packs as P
from .models import ALL, LdEmployer, LdPaper, LdRate, LdSettings, LdSite, LdWorker  # noqa: F401

log = logging.getLogger("santosh.labourdesk")
LOCK = threading.RLock()

FIELDS = ("company", "project", "country", "region", "currency", "pay_cycle", "week_start", "day_hours", "week_hours", "max_day_hours",
          "ot_x", "cutoff", "advance_cap", "second_limit", "gate_tol", "burst", "deductions", "required", "language", "packs_off")
CURRENCIES = re.compile(r"^[A-Z]{3}$")
BASIS = ("day", "hour", "piece")
WHOSE = ("company", "employer", "worker", "site")


class LabourError(ValueError):
    pass


_READY: set[int] = set()


def tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    for m in ALL:
        m.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def tz(tenant: str):
    try:
        from ..life import tz_of
        return tz_of(tenant)
    except Exception:   # noqa: BLE001
        return timezone.utc


def today(tenant: str) -> date:
    return datetime.now(tz(tenant)).date()


def stamp(tenant: str) -> str:
    return datetime.now(tz(tenant)).strftime("%Y-%m-%dT%H:%M:%S")


def S(v: Any, n: int = 200) -> str:
    return ("" if v is None else str(v)).strip()[:n]


def day_of(v: Any, tenant: str, name: str = "Date") -> str:
    if not v:
        return today(tenant).isoformat()
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        raise LabourError(f"{name} '{v}': write it as YYYY-MM-DD.")


def num(v: Any, name: str = "Amount", allow_zero: bool = True) -> float:
    if v is None or v == "":
        raise LabourError(f"{name}: give a number.")
    try:
        x = float(v) if isinstance(v, (int, float)) else float(str(v).replace(",", "").strip())
    except ValueError:
        raise LabourError(f"{name}: '{v}' is not a number.")
    if math.isnan(x) or math.isinf(x) or x < 0:
        raise LabourError(f"{name}: a number of zero or more.")
    if not allow_zero and x == 0:
        raise LabourError(f"{name}: must be more than zero.")
    return x


def last4(v: Any) -> str:
    """Only the last 4 characters of an id / account number are ever kept."""
    t = re.sub(r"[^0-9A-Za-z]", "", S(v, 80))
    return t[-4:].upper() if t else ""


def need_who(v: Any, what: str = "this") -> str:
    w = S(v, 80)
    if not w:
        raise LabourError(f"Who is doing {what}? A person's name is needed.")
    return w


# ---------------------------------------------------------------- settings
DEFAULTS = {"company": "", "project": "", "country": "", "region": "", "currency": "USD", "pay_cycle": "weekly", "week_start": 0, "day_hours": 8.0,
            "week_hours": 48.0, "max_day_hours": 12.0, "ot_x": 0.0, "cutoff": "11:00", "advance_cap": 50.0, "second_limit": 0.0, "gate_tol": 0,
            "burst": 5, "deductions": [], "required": [], "language": "en", "packs_off": []}


def settings(tenant: str) -> dict[str, Any]:
    tables()
    with session() as s:
        r = s.get(LdSettings, tenant)
        d = {k: (getattr(r, k) if r else None) for k in FIELDS}
    d["set"] = r is not None and bool(d.get("country"))
    for k, v in DEFAULTS.items():
        if d.get(k) is None or (d.get(k) in ("", [], {}) and k not in ("company", "project", "country", "region", "deductions", "required", "packs_off")):
            d[k] = v
    d["pack"] = P.pack(d["country"], d["region"])
    o = d["pack"]["ot"]
    d["ot"] = {"basis": o["basis"], "after": o.get("after") or 0, "x": o.get("x") or 0, "source": o["source"], "check": o["check"], "id": o["id"]}
    if not d["required"]:
        d["required"] = [p["kind"] for p in P.papers(d["country"], "worker", d["packs_off"]) if p["required"] and not p["check"]]
    return d


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    tables()
    clean: dict[str, Any] = {}
    for k, v in f.items():
        if k not in FIELDS or v is None:
            continue
        if k in ("company", "project"):
            clean[k] = S(v, 120)
        elif k == "region":
            clean[k] = S(v, 40)
        elif k == "country":
            c = S(v, 4).upper()
            if c and not re.fullmatch(r"[A-Z]{2}", c):
                raise LabourError("Country: the two-letter code, like IN, GB, US, AE, SA, SG, AU, DE.")
            clean[k] = c
        elif k == "currency":
            c = S(v, 10).upper()
            if not CURRENCIES.match(c):
                raise LabourError("Currency: the three-letter code, like INR, GBP, USD, AED.")
            clean[k] = c
        elif k == "pay_cycle":
            if v not in ("weekly", "fortnightly", "monthly"):
                raise LabourError("Pay period: weekly, fortnightly or monthly.")
            clean[k] = v
        elif k == "week_start":
            x = int(num(v, "Week start"))
            if x > 6:
                raise LabourError("Week start: 0 (Monday) to 6 (Sunday).")
            clean[k] = x
        elif k in ("day_hours", "max_day_hours"):
            x = num(v, k, allow_zero=False)
            if x > 24:
                raise LabourError(f"{k}: at most 24 hours.")
            clean[k] = x
        elif k == "week_hours":
            x = num(v, "Hours a week", allow_zero=False)
            if x > 168:
                raise LabourError("Hours a week: at most 168.")
            clean[k] = x
        elif k == "ot_x":
            x = num(v, "Your overtime multiplier")
            if x and (x < 1 or x > 5):
                raise LabourError("Your overtime multiplier: between 1 and 5 (or 0 to follow the country rule).")
            clean[k] = x
        elif k == "cutoff":
            t = S(v, 5)
            if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t):
                raise LabourError("Muster cut-off: HH:MM, like 11:00.")
            clean[k] = t
        elif k == "advance_cap":
            x = num(v, "Advance recovery cap")
            if x > 100:
                raise LabourError("Advance recovery cap: at most 100% of one period's pay.")
            clean[k] = x
        elif k == "second_limit":
            clean[k] = num(v, "Second approver above")
        elif k in ("gate_tol", "burst"):
            clean[k] = int(num(v, k))
        elif k == "language":
            clean[k] = S(v, 10) or "en"
        elif k == "deductions":
            clean[k] = _deductions(v)
        elif k == "required":
            clean[k] = [S(x, 40) for x in (v or []) if S(x, 40)][:20]
        elif k == "packs_off":
            clean[k] = [S(x, 40) for x in (v or [])][:60]
    if "country" in clean and "currency" not in clean and clean["country"] in P.CURRENCY:
        cur = settings(tenant)
        if not cur["set"] or cur["currency"] == "USD":
            clean["currency"] = P.CURRENCY[clean["country"]]
    with LOCK, session() as s:
        r = s.get(LdSettings, tenant)
        if r is None:
            r = LdSettings(tenant_id=tenant, deductions=[], required=[], packs_off=[], legacy_done={})
            s.add(r)
        for k, v in clean.items():
            setattr(r, k, v)
        r.updated_at = now()
    out = settings(tenant)
    out["say"] = "Settings saved."
    return out


def _deductions(v: Any) -> list[dict[str, Any]]:
    if not isinstance(v, list):
        raise LabourError("Deductions: a list of rows {name, pct, base basic|gross, cap, employer_pct, source}.")
    out = []
    for d in v[:12]:
        if not isinstance(d, dict):
            continue
        name = S(d.get("name"), 60)
        if not name:
            raise LabourError("Each deduction needs a name.")
        src = S(d.get("source"), 240)
        if not src:
            raise LabourError(f"{name}: write where the rate comes from (the scheme, the notification, your payroll adviser).")
        base = S(d.get("base"), 6) or "basic"
        if base not in ("basic", "gross"):
            raise LabourError(f"{name}: base is basic or gross.")
        pct = num(d.get("pct"), f"{name} %")
        if pct > 50:
            raise LabourError(f"{name}: at most 50%.")
        out.append({"name": name, "pct": pct, "base": base, "cap": num(d.get("cap") or 0, f"{name} wage ceiling"),
                    "employer_pct": num(d.get("employer_pct") or 0, f"{name} employer %"), "source": src})
    return out


# ---------------------------------------------------------------- sites and employers
def sites(tenant: str, all_: bool = False) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        rows = s.scalars(select(LdSite).where(LdSite.tenant_id == tenant).order_by(LdSite.created_at)).all()
        return [{"id": r.id, "name": r.name, "project": r.project, "region": r.region, "planned": r.planned, "active": r.active}
                for r in rows if all_ or r.active]


def save_site(tenant: str, name: str, project: str = "", region: str = "", planned: Any = None, id: str = "", active: Any = None) -> dict[str, Any]:
    tables()
    name = S(name, 80)
    with LOCK, session() as s:
        r = s.get(LdSite, id) if id else None
        if r is None or r.tenant_id != tenant:
            if not name:
                raise LabourError("Give the site a name.")
            dup = s.scalars(select(LdSite).where(LdSite.tenant_id == tenant, LdSite.name == name)).first()
            r = dup or LdSite(tenant_id=tenant)
            if dup is None:
                s.add(r)
        if name:
            r.name = name
        if project:
            r.project = S(project, 120)
        if region:
            r.region = S(region, 40)
        if planned not in (None, ""):
            r.planned = int(num(planned, "Planned headcount"))
        if active is not None:
            r.active = bool(active)
        s.flush()
        return {"id": r.id, "name": r.name, "say": f"Site {r.name} saved."}


def site_id(s, tenant: str, v: str) -> str:
    v = S(v, 80)
    if not v:
        rows = s.scalars(select(LdSite).where(LdSite.tenant_id == tenant, LdSite.active.is_(True)).order_by(LdSite.created_at)).all()
        if len(rows) == 1:
            return rows[0].id
        if not rows:
            raise LabourError("Add a site first (Settings).")
        raise LabourError("Which site? " + ", ".join(r.name for r in rows[:8]))
    r = s.get(LdSite, v)
    if r is not None and r.tenant_id == tenant:
        return r.id
    for r in s.scalars(select(LdSite).where(LdSite.tenant_id == tenant)).all():
        if r.name.lower() == v.lower():
            return r.id
    raise LabourError(f"No site called '{v}'.")


def site_names(s, tenant: str) -> dict[str, str]:
    return {r.id: r.name for r in s.scalars(select(LdSite).where(LdSite.tenant_id == tenant)).all()}


def own_employer(s, tenant: str) -> LdEmployer:
    r = s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant, LdEmployer.kind == "own")).first()
    if r is None:
        st = s.get(LdSettings, tenant)
        r = LdEmployer(tenant_id=tenant, name=(st.company if st and st.company else "Own gangs"), kind="own")
        s.add(r)
        s.flush()
    return r


def employer_view(r: LdEmployer) -> dict[str, Any]:
    return {"id": r.id, "name": r.name, "kind": r.kind, "status": r.status, "tax_id_last4": r.tax_id_last4, "tax_id_ok": r.tax_id_ok,
            "checked_on": r.checked_on, "checked_by": r.checked_by, "contact": r.contact, "active": r.active}


def employers(tenant: str) -> list[dict[str, Any]]:
    tables()
    with LOCK, session() as s:
        own_employer(s, tenant)
    with session() as s:
        rows = s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant).order_by(LdEmployer.created_at)).all()
        return [employer_view(r) for r in rows if r.active]


def save_employer(tenant: str, name: str, kind: str = "sub", status: str = "", tax_id: str = "", tax_id_ok: Any = None, checked_on: str = "",
                  checked_by: str = "", contact: str = "", id: str = "") -> dict[str, Any]:
    tables()
    name = S(name, 120)
    if kind not in ("own", "sub"):
        raise LabourError("Kind: own (your company) or sub (a subcontractor / labour contractor).")
    if status and status not in P.STATUSES:
        raise LabourError("Tax status: " + ", ".join(P.STATUSES) + ".")
    with LOCK, session() as s:
        r = s.get(LdEmployer, id) if id else None
        if r is None or r.tenant_id != tenant:
            if kind == "own":
                r = own_employer(s, tenant)
            else:
                if not name:
                    raise LabourError("Give the subcontractor's name.")
                r = s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant, LdEmployer.name == name)).first()
                if r is None:
                    r = LdEmployer(tenant_id=tenant, kind="sub")
                    s.add(r)
        if name:
            r.name = name
        if status:
            r.status = status
        if tax_id:
            r.tax_id_last4 = last4(tax_id)
        if tax_id_ok is not None:
            r.tax_id_ok = bool(tax_id_ok)
            if r.tax_id_ok:
                r.checked_on = day_of(checked_on, tenant, "Checked on")
                r.checked_by = need_who(checked_by, "the tax id check")
        if contact:
            r.contact = S(contact, 120)
        s.flush()
        return {**employer_view(r), "say": f"{r.name} saved."}


def employer_id(s, tenant: str, v: str) -> str:
    v = S(v, 120)
    if not v:
        return own_employer(s, tenant).id
    r = s.get(LdEmployer, v)
    if r is not None and r.tenant_id == tenant:
        return r.id
    if v.lower() in ("own", "own gangs", "ours", "company"):
        return own_employer(s, tenant).id
    rows = s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant)).all()
    for r in rows:
        if r.name.lower() == v.lower():
            return r.id
    hit = [r for r in rows if v.lower() in r.name.lower()]
    if len(hit) == 1:
        return hit[0].id
    raise LabourError(f"No employer called '{v}'. Add the subcontractor first.")


# ---------------------------------------------------------------- workers
def worker_view(r: LdWorker, emp: dict[str, str] | None = None, sites_: dict[str, str] | None = None) -> dict[str, Any]:
    return {"id": r.id, "code": r.code, "name": r.name, "employer_id": r.employer_id, "employer": (emp or {}).get(r.employer_id, ""), "trade": r.trade,
            "skill": r.skill, "gang": r.gang, "site_id": r.site_id, "site": (sites_ or {}).get(r.site_id, ""), "id_last4": r.id_last4,
            "bank_last4": r.bank_last4, "phone_last4": r.phone_last4, "language": r.language, "joined": r.joined, "left": r.left, "active": r.active}


def save_worker(tenant: str, **f: Any) -> dict[str, Any]:
    tables()
    for k in ("id_number", "bank_account", "account", "aadhaar", "pan"):
        if f.get(k) and len(re.sub(r"\D", "", S(f[k], 40))) > 4:
            f.setdefault({"id_number": "id_last4", "aadhaar": "id_last4", "pan": "id_last4"}.get(k, "bank_last4"), f[k])
    with LOCK, session() as s:
        r = s.get(LdWorker, S(f.get("id"), 40)) if f.get("id") else None
        if r is None or r.tenant_id != tenant:
            name = S(f.get("name"), 120)
            if not name:
                raise LabourError("Give the worker's name.")
            r = LdWorker(tenant_id=tenant, name=name)
            s.add(r)
        if f.get("name"):
            r.name = S(f["name"], 120)
        if "employer" in f or "employer_id" in f or not r.employer_id:
            r.employer_id = employer_id(s, tenant, S(f.get("employer_id") or f.get("employer"), 120))
        if f.get("site") or f.get("site_id"):
            r.site_id = site_id(s, tenant, S(f.get("site_id") or f.get("site"), 80))
        for k, n in (("code", 30), ("trade", 60), ("skill", 30), ("gang", 60), ("language", 10)):
            if f.get(k) is not None and f.get(k) != "":
                setattr(r, k, S(f[k], n))
        for k in ("id_last4", "bank_last4", "phone_last4"):
            if f.get(k):
                setattr(r, k, last4(f[k]))
        for k in ("joined", "left"):
            if f.get(k):
                setattr(r, k, day_of(f[k], tenant, k))
        if f.get("active") is not None:
            r.active = bool(f["active"])
        if r.left and r.left <= today(tenant).isoformat():
            r.active = False
        s.flush()
        return {**worker_view(r), "say": f"{r.name} saved."}


def workers(tenant: str, q: str = "", employer: str = "", site: str = "", all_: bool = False) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        emp = {r.id: r.name for r in s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant)).all()}
        sn = site_names(s, tenant)
        eid = employer_id(s, tenant, employer) if employer else ""
        sid = site_id(s, tenant, site) if site else ""
        rows = s.scalars(select(LdWorker).where(LdWorker.tenant_id == tenant).order_by(LdWorker.name)).all()
        ql = S(q, 60).lower()
        out = []
        for r in rows:
            if not all_ and not r.active:
                continue
            if eid and r.employer_id != eid or sid and r.site_id != sid:
                continue
            if ql and ql not in r.name.lower() and ql not in (r.code or "").lower() and ql not in (r.trade or "").lower():
                continue
            out.append(worker_view(r, emp, sn))
        return out


def match(s, tenant: str, name: str, site: str = "") -> tuple[LdWorker | None, list[str]]:
    """Her spelling to one worker: exact, the code, then a close match only if it is the clear one. Never a guess between two."""
    n = re.sub(r"\s+", " ", S(name, 120)).lower()
    if not n:
        return None, []
    rows = [r for r in s.scalars(select(LdWorker).where(LdWorker.tenant_id == tenant)).all() if r.active]
    for r in rows:
        if r.name.lower() == n or (r.code and r.code.lower() == n):
            return r, []
    first = [r for r in rows if r.name.lower().split(" ")[0] == n] if " " not in n else []
    if len(first) == 1:
        return first[0], []
    pool = {r.name.lower(): r for r in rows}
    close = difflib.get_close_matches(n, list(pool), n=3, cutoff=0.82)
    if len(close) == 1:
        return pool[close[0]], []
    if len(close) > 1 and difflib.SequenceMatcher(None, n, close[0]).ratio() - difflib.SequenceMatcher(None, n, close[1]).ratio() > 0.08:
        return pool[close[0]], []
    guesses = close or difflib.get_close_matches(n, list(pool), n=3, cutoff=0.6)
    return None, [pool[g].name for g in guesses]


def import_workers(tenant: str, text: str, employer: str = "", site: str = "") -> dict[str, Any]:
    """Her sheet as CSV: name, trade, skill, gang, employer, site, code, joined, language, id_last4, bank_last4 (the last 4 only)."""
    rows = list(csv.DictReader(io.StringIO(str(text or "")[:2_000_000])))
    if not rows:
        raise LabourError("Paste a CSV with at least: name, trade.")
    ok, bad, same = 0, [], 0
    have = {w["name"].lower(): w["id"] for w in workers(tenant, all_=True)}
    for i, r in enumerate(rows[:5000], 2):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        try:
            name = r.get("name") or r.get("worker")
            f = {k: r.get(k) for k in ("trade", "skill", "gang", "code", "joined", "language", "id_last4", "bank_last4") if r.get(k)}
            f["employer"] = r.get("employer") or r.get("contractor") or employer
            if r.get("site") or site:
                f["site"] = r.get("site") or site
            if name and name.lower() in have:
                f["id"] = have[name.lower()]
                same += 1
            else:
                f["name"] = name
            save_worker(tenant, **f)
            ok += 1
        except LabourError as e:
            bad.append(f"line {i}: {e}")
    return {"saved": ok, "already": same, "errors": bad[:30],
            "say": f"{ok} worker(s) saved" + (f" ({same} were already on the register)" if same else "") + (f", {len(bad)} refused" if bad else "") + "."}


# ---------------------------------------------------------------- papers and the renewal radar
def paper_view(r: LdPaper, owners: dict[str, str], t0: date) -> dict[str, Any]:
    left = None
    if r.valid_to:
        try:
            left = (date.fromisoformat(r.valid_to) - t0).days
        except ValueError:
            left = None
    return {"id": r.id, "whose": r.whose, "owner_id": r.owner_id, "owner": owners.get(r.owner_id, "your company" if r.whose == "company" else ""),
            "kind": r.kind, "name": r.name or r.kind.replace("_", " "), "number_last4": r.number_last4, "issuer": r.issuer, "valid_from": r.valid_from,
            "valid_to": r.valid_to, "days_left": left, "lapsed": left is not None and left < 0, "file_id": r.file_id, "note": r.note}


def save_paper(tenant: str, whose: str, kind: str, owner: str = "", name: str = "", number: str = "", issuer: str = "", valid_from: str = "",
               valid_to: str = "", file_id: str = "", note: str = "", id: str = "") -> dict[str, Any]:
    tables()
    if whose not in WHOSE:
        raise LabourError("Whose paper: company, employer (a subcontractor), worker or site.")
    kind = S(kind, 40).lower().replace(" ", "_")
    if not kind:
        raise LabourError("Which kind of paper (licence, registration, insurance, work_permit, induction, medical, skills ...)?")
    with LOCK, session() as s:
        oid = ""
        if whose == "worker":
            w = s.get(LdWorker, owner) if owner else None
            if w is None or w.tenant_id != tenant:
                w, guesses = match(s, tenant, owner)
                if w is None:
                    raise LabourError(f"No worker called '{owner}'." + (f" Did you mean {', '.join(guesses)}?" if guesses else ""))
            oid = w.id
        elif whose == "employer":
            oid = employer_id(s, tenant, owner)
        elif whose == "site":
            oid = site_id(s, tenant, owner)
        r = s.get(LdPaper, id) if id else None
        if r is None or r.tenant_id != tenant:
            r = LdPaper(tenant_id=tenant)
            s.add(r)
        r.whose, r.owner_id, r.kind = whose, oid, kind
        r.name = S(name, 120) or r.name
        if number:
            r.number_last4 = last4(number)
        r.issuer = S(issuer, 120) or r.issuer
        if valid_from:
            r.valid_from = day_of(valid_from, tenant, "Valid from")
        if valid_to:
            r.valid_to = day_of(valid_to, tenant, "Valid to")
        r.file_id = S(file_id, 60) or r.file_id
        r.note = S(note, 300) or r.note
        s.flush()
        return {"id": r.id, "say": f"Paper saved ({r.name or kind}" + (f", valid to {r.valid_to}" if r.valid_to else ", no end date") + ")."}


def owners(s, tenant: str) -> dict[str, str]:
    d = {r.id: r.name for r in s.scalars(select(LdWorker).where(LdWorker.tenant_id == tenant)).all()}
    d.update({r.id: r.name for r in s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant)).all()})
    d.update(site_names(s, tenant))
    return d


def papers(tenant: str, whose: str = "", owner: str = "") -> list[dict[str, Any]]:
    tables()
    t0 = today(tenant)
    with session() as s:
        ow = owners(s, tenant)
        q = select(LdPaper).where(LdPaper.tenant_id == tenant)
        if whose:
            q = q.where(LdPaper.whose == whose)
        if owner:
            q = q.where(LdPaper.owner_id == owner)
        return [paper_view(r, ow, t0) for r in s.scalars(q).all()]


def radar(tenant: str) -> dict[str, Any]:
    """Company / employer papers expiring in 90 / 60 / 30 days; person papers in 30 / 14; lapsed ones first."""
    t0 = today(tenant)
    rows = []
    for p in papers(tenant):
        if p["days_left"] is None:
            continue
        horizon = 30 if p["whose"] == "worker" else 90
        if p["days_left"] <= horizon:
            band = "lapsed" if p["lapsed"] else (("14" if p["days_left"] <= 14 else "30") if p["whose"] == "worker"
                                                  else ("30" if p["days_left"] <= 30 else "60" if p["days_left"] <= 60 else "90"))
            rows.append({**p, "band": band})
    rows.sort(key=lambda r: r["days_left"])
    return {"rows": rows, "lapsed": sum(1 for r in rows if r["lapsed"]), "soon": sum(1 for r in rows if not r["lapsed"]), "today": t0.isoformat()}


def paper_state(s, tenant: str, worker_ids: list[str], on: str, required: list[str]) -> dict[str, list[str]]:
    """For each worker: the required papers lapsed or missing on that day."""
    if not worker_ids or not required:
        return {}
    by: dict[str, dict[str, str]] = {}
    for r in s.scalars(select(LdPaper).where(LdPaper.tenant_id == tenant, LdPaper.whose == "worker", LdPaper.owner_id.in_(worker_ids))).all():
        best = by.setdefault(r.owner_id, {})
        best[r.kind] = max(best.get(r.kind, ""), r.valid_to or "9999-12-31")
    out = {}
    for w in worker_ids:
        miss = []
        for k in required:
            v = (by.get(w) or {}).get(k)
            if v is None:
                miss.append(f"no {k.replace('_', ' ')} on file")
            elif v < on:
                miss.append(f"{k.replace('_', ' ')} lapsed {v}")
        if miss:
            out[w] = miss
    return out


# ---------------------------------------------------------------- rates and floors
def save_rate(tenant: str, rate: Any, kind: str = "pay", trade: str = "", skill: str = "", site: str = "", region: str = "", worker: str = "",
              basis: str = "day", unit: str = "", wef: str = "", source: str = "") -> dict[str, Any]:
    tables()
    if kind not in ("pay", "floor"):
        raise LabourError("Kind: pay (what you pay) or floor (the minimum / prevailing rate for the trade).")
    if basis not in BASIS:
        raise LabourError("Basis: day, hour or piece.")
    x = num(rate, "Rate", allow_zero=False)
    with LOCK, session() as s:
        wid = ""
        if worker:
            w, g = match(s, tenant, worker)
            if w is None:
                raise LabourError(f"No worker called '{worker}'." + (f" Did you mean {', '.join(g)}?" if g else ""))
            wid = w.id
        sid = site_id(s, tenant, site) if site else ""
        if not (S(trade) or S(skill) or wid):
            raise LabourError("A rate is for a trade, a skill grade or one worker.")
        r = LdRate(tenant_id=tenant, kind=kind, trade=S(trade, 60), skill=S(skill, 30), site_id=sid, region=S(region, 40), worker_id=wid,
                   basis=basis, rate=x, unit=S(unit, 20), wef=day_of(wef, tenant, "Effective from"), source=S(source, 240))
        s.add(r)
        s.flush()
        warn = "" if r.source else (" No source written - write the notification, wage determination or award clause it comes from."
                                    if kind == "floor" else "")
        return {"id": r.id, "say": f"{'Minimum' if kind == 'floor' else 'Pay'} rate saved: {x:g} a {basis}" + (f" for {r.trade}" if r.trade else "") + "." + warn}


def rates(tenant: str, kind: str = "") -> list[dict[str, Any]]:
    tables()
    with session() as s:
        sn = site_names(s, tenant)
        wn = {r.id: r.name for r in s.scalars(select(LdWorker).where(LdWorker.tenant_id == tenant)).all()}
        q = select(LdRate).where(LdRate.tenant_id == tenant)
        if kind:
            q = q.where(LdRate.kind == kind)
        return [{"id": r.id, "kind": r.kind, "trade": r.trade, "skill": r.skill, "site": sn.get(r.site_id, ""), "site_id": r.site_id, "region": r.region,
                 "worker": wn.get(r.worker_id, ""), "basis": r.basis, "rate": r.rate, "unit": r.unit, "wef": r.wef, "source": r.source}
                for r in sorted(s.scalars(q).all(), key=lambda r: (r.kind, r.trade, r.wef))]


def find_rate(all_rates: list[LdRate], kind: str, w: LdWorker, site: str, region: str, on: str) -> LdRate | None:
    """The newest row in force on `on`: the worker's own, then trade + skill + site, trade + site, trade + skill, trade, skill."""
    cands = [r for r in all_rates if r.kind == kind and (r.wef or "") <= on]
    if kind == "pay":
        own = [r for r in cands if r.worker_id == w.id]
        if own:
            return sorted(own, key=lambda r: r.wef)[-1]
    cands = [r for r in cands if not r.worker_id]
    best, score = None, -1
    for r in cands:
        if r.trade and r.trade.lower() != (w.trade or "").lower():
            continue
        if r.skill and r.skill.lower() != (w.skill or "").lower():
            continue
        if r.site_id and r.site_id != site:
            continue
        if r.region and region and r.region.lower() != region.lower():
            continue
        if not r.trade and not r.skill:
            continue
        sc = (4 if r.trade else 0) + (2 if r.skill else 0) + (1 if r.site_id or r.region else 0)
        if sc > score or (sc == score and best is not None and r.wef >= best.wef):
            best, score = r, sc
    return best


# ---------------------------------------------------------------- the old labour rows, brought in once
def bring_legacy(tenant: str) -> dict[str, Any]:
    tables()
    try:
        from ..construction.models import CLabourLicence, CLabourMuster, CLabourWage
    except Exception:   # noqa: BLE001
        return {}
    with LOCK, session() as s:
        st = s.get(LdSettings, tenant)
        if st is None:
            st = LdSettings(tenant_id=tenant, deductions=[], required=[], packs_off=[], legacy_done={})
            s.add(st)
            s.flush()
        done = dict(st.legacy_done or {})
        if done.get("v1"):
            return {}
        try:
            lic = s.scalars(select(CLabourLicence).where(CLabourLicence.tenant_id == tenant)).all()
            wag = s.scalars(select(CLabourWage).where(CLabourWage.tenant_id == tenant)).all()
            mus = s.scalars(select(CLabourMuster).where(CLabourMuster.tenant_id == tenant)).all()
        except Exception:   # noqa: BLE001   (old tables were never made on this server)
            lic, wag, mus = [], [], []
        n = 0
        sids: dict[str, str] = {}

        def _site(name: str) -> str:
            name = S(name, 80) or "Site"
            if name not in sids:
                r = s.scalars(select(LdSite).where(LdSite.tenant_id == tenant, LdSite.name == name)).first()
                if r is None:
                    r = LdSite(tenant_id=tenant, name=name)
                    s.add(r)
                    s.flush()
                sids[name] = r.id
            return sids[name]

        def _emp(name: str) -> str:
            name = S(name, 120)
            if not name:
                return own_employer(s, tenant).id
            r = s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant, LdEmployer.name == name)).first()
            if r is None:
                r = LdEmployer(tenant_id=tenant, name=name, kind="sub")
                s.add(r)
                s.flush()
            return r.id

        for r in lic:
            whose = "employer" if r.holder else "company"
            s.add(LdPaper(tenant_id=tenant, whose=whose, owner_id=_emp(r.holder) if r.holder else "", kind={"contract_labour": "licence", "bocw": "registration"}.get(r.kind, r.kind or "other"),
                          name=r.kind.replace("_", " "), number_last4=last4(r.number), issuer=S(r.authority, 120), valid_from=r.valid_from, valid_to=r.valid_to,
                          note="brought in from the old labour desk"))
            n += 1
        for r in wag:
            s.add(LdRate(tenant_id=tenant, kind="pay", trade=S(r.trade, 60), site_id=_site(r.site) if r.site else "", basis=r.basis if r.basis in BASIS else "day",
                         rate=r.rate, wef=r.wef or "2000-01-01", source=S(r.source, 240) or "the old labour desk"))
            n += 1
        from .models import LdMark
        for r in mus:
            if not r.present:
                continue
            s.add(LdMark(tenant_id=tenant, day=r.day, site_id=_site(r.site), employer_id=_emp(r.contractor), gang=S(r.trade, 60) or "gang",
                         count=int(r.present), value=1.0, ot_hours=float(r.ot_hours or 0), source="legacy", who="the old labour desk", at=r.day + "T00:00:00"))
            n += 1
        done["v1"] = n
        st.legacy_done = done
    return {"brought": n}


def resolve(s, tenant: str, worker: str) -> LdWorker:
    w = s.get(LdWorker, worker) if worker else None
    if w is not None and w.tenant_id == tenant:
        return w
    w, g = match(s, tenant, worker)
    if w is None:
        raise LabourError(f"No worker called '{worker}'." + (f" Did you mean {', '.join(g)}?" if g else ""))
    return w


def span(start: str, end: str) -> list[str]:
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if b < a:
        raise LabourError("The period ends before it starts.")
    if (b - a).days > 62:
        raise LabourError("A period of at most 62 days.")
    return [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]
