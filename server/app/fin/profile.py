"""The workspace profile (plan section 1): one employee, five sizes. Size changes configuration, never code - every part reads
`approval_for`, `autonomy`, `store`, `audit_level` and `tiers` from here.

Setup = 8 questions -> clean() -> derive() -> preview() (what turns on, and a hash) -> apply(hash) on her tap."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SIZES: dict[str, dict[str, Any]] = {
    "personal": {"label": "Me or my household", "users": "her + family she invites", "books": "household",
                 "approvals": "her_tap", "autonomy": "partner", "store": "sqlite", "audit": "simple", "tiers": ["A"],
                 "max_users": 6, "clients": False, "maker_checker": False},
    "solo": {"label": "My own work (sole trader, freelancer, landlord)", "users": "her + her accountant (read only)",
             "books": "business+household", "approvals": "her_tap", "autonomy": "partner", "store": "sqlite", "audit": "simple",
             "tiers": ["A"], "max_users": 3, "clients": False, "maker_checker": False},
    "business": {"label": "My business with a team", "users": "team with roles", "books": "entities",
                 "approvals": "roles_and_limits", "autonomy": "learning", "store": "sqlite_or_postgres", "audit": "append_only",
                 "tiers": ["A", "B"], "max_users": 500, "clients": False, "maker_checker": False},
    "firm": {"label": "Clients of my firm (accountant, adviser, broker, bookkeeper)", "users": "staff + each client sees only their own",
             "books": "one_per_client", "approvals": "partner_review", "autonomy": "drafts_only", "store": "postgres",
             "audit": "per_client", "tiers": ["A", "B"], "max_users": 2000, "clients": True, "maker_checker": False},
    "institution": {"label": "My regulated institution (bank, lender, payment firm, broker, fund, public body)",
                    "users": "teams, roles, departments", "books": "entities_cost_centres", "approvals": "maker_checker",
                    "autonomy": "drafts_only", "store": "postgres_own_region", "audit": "full", "tiers": ["A", "B"],
                    "max_users": 100000, "clients": False, "maker_checker": True},
}
SIZE_ORDER = ["personal", "solo", "business", "firm", "institution"]

ENTITY_TYPES = {
    "individual": "A person", "household": "A household", "sole_trader": "Sole trader / freelancer", "partnership": "Partnership",
    "company": "Company", "trust": "Trust", "non_profit": "Non-profit / NGO", "cooperative": "Co-operative / credit union",
    "bank": "Bank", "lender": "Lender / finance company", "payment_firm": "Payment firm / money service", "broker": "Broker / dealer",
    "fund": "Fund / asset manager", "adviser_firm": "Advisory firm", "accounting_firm": "Accounting / tax firm",
    "insurer_adjacent": "Insurance intermediary", "vasp": "Digital-asset firm", "public_body": "Public body / regulator",
}
DEFAULT_ENTITY = {"personal": "individual", "solo": "sole_trader", "business": "company", "firm": "accounting_firm",
                  "institution": "bank"}

EMPLOYEES = {
    "safety": "Money Safety", "household": "Household Money", "books": "Books & Accounts", "tax": "Tax",
    "payroll": "Payroll & People Costs", "cash": "Cash & Treasury", "credit": "Credit & Lending", "payments": "Payments",
    "wealth": "Investments & Wealth", "markets": "Markets & Post-Trade", "fincrime": "Financial Crime", "compliance": "Compliance",
    "risk": "Risk", "audit": "Audit & Controls", "governance": "Governance & Company Secretary", "cfo": "CFO Office",
    "community": "Community & Inclusive Finance", "digital": "Digital Assets",
}
# which sizes each employee serves (plan section 2)
SERVES = {
    "safety": "personal solo business firm institution", "household": "personal solo",
    "books": "solo business firm institution", "tax": "personal solo business firm institution",
    "payroll": "solo business firm institution", "cash": "solo business firm institution",
    "credit": "personal solo business firm institution", "payments": "personal solo business firm institution",
    "wealth": "personal solo firm institution", "markets": "firm institution", "fincrime": "business firm institution",
    "compliance": "solo business firm institution", "risk": "business firm institution", "audit": "business firm institution",
    "governance": "business firm institution", "cfo": "solo business firm", "community": "personal solo business institution",
    "digital": "personal solo firm institution",
}
RECOMMEND = {
    "personal": ["safety", "household", "tax", "wealth"], "solo": ["safety", "books", "tax", "cash"],
    "business": ["books", "tax", "payroll", "cash", "cfo"], "firm": ["books", "tax", "payroll", "wealth", "compliance"],
    "institution": ["compliance", "fincrime", "risk", "audit", "safety"],
}
AUTONOMY = ("learning", "partner", "trusted", "drafts_only")
ROLES = ("owner", "admin", "preparer", "reviewer", "approver", "viewer", "client")


class ProfileError(ValueError):
    pass


def questions() -> list[dict[str, Any]]:
    return [
        {"key": "size", "q": "Who is this for?", "kind": "one", "options": {k: SIZES[k]["label"] for k in SIZE_ORDER}},
        {"key": "countries", "q": "Which countries? (where she lives, earns, holds money or pays tax)", "kind": "many",
         "hint": "ISO codes, e.g. GB, US, IN"},
        {"key": "currency", "q": "Main currency", "kind": "text", "hint": "ISO 4217, e.g. GBP"},
        {"key": "entity_type", "q": "What kind of entity?", "kind": "one", "options": ENTITY_TYPES},
        {"key": "year_end", "q": "Year end / tax year end (MM-DD)", "kind": "text", "hint": "from the country pack if left blank"},
        {"key": "wants", "q": "What do you want help with?", "kind": "many", "options": EMPLOYEES},
        {"key": "sources", "q": "Where is your data?", "kind": "many",
         "options": {"statements": "Bank statements (upload)", "open_banking": "Bank connection", "accounting": "Accounting system",
                     "payroll": "Payroll system", "broker": "Broker / investments", "files": "Documents and files"}},
        {"key": "people", "q": "Who else works on it?", "kind": "list", "hint": "[{name, role}] - roles: " + ", ".join(ROLES)},
    ]


def _cc(v: Any) -> str:
    s = str(v or "").strip().upper()
    return s if re.fullmatch(r"[A-Z]{2}", s) else ""


def clean(answers: dict | None) -> dict[str, Any]:
    a = dict(answers or {})
    size = a.get("size") if a.get("size") in SIZES else ""
    if not size:
        raise ProfileError("size: one of " + ", ".join(SIZE_ORDER))
    cs = [c for c in (_cc(x) for x in (a.get("countries") or [])) if c]
    cs = list(dict.fromkeys(cs))[:20]
    if not cs:
        raise ProfileError("countries: at least one ISO country code")
    cur = str(a.get("currency") or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", cur):
        from . import pack as P
        cur = P.currency_of(cs[0]) or ""
        if not cur:
            raise ProfileError("currency: an ISO 4217 code (no pack knows the currency of " + cs[0] + ")")
    ent = a.get("entity_type") if a.get("entity_type") in ENTITY_TYPES else DEFAULT_ENTITY[size]
    ye = str(a.get("year_end") or "").strip()
    if ye and not re.fullmatch(r"(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", ye):
        raise ProfileError("year_end: MM-DD")
    wants = [w for w in (a.get("wants") or []) if w in EMPLOYEES]
    srcs = [s for s in (a.get("sources") or []) if s in questions()[6]["options"]]
    people = []
    for p in (a.get("people") or [])[:200]:
        if isinstance(p, dict) and str(p.get("name") or "").strip():
            role = p.get("role") if p.get("role") in ROLES else "viewer"
            people.append({"name": str(p["name"]).strip()[:80], "role": role})
    if len(people) + 1 > SIZES[size]["max_users"]:
        raise ProfileError(f"{SIZES[size]['label']}: at most {SIZES[size]['max_users']} people")
    return {"size": size, "countries": cs, "currency": cur, "entity_type": ent, "year_end": ye, "wants": wants,
            "sources": srcs, "people": people, "name": str(a.get("name") or "").strip()[:160]}


def derive(a: dict[str, Any]) -> dict[str, Any]:
    from . import pack as P
    sz = SIZES[a["size"]]
    serves = [k for k in EMPLOYEES if a["size"] in SERVES[k].split()]
    wants = [w for w in a["wants"] if w in serves] or [w for w in RECOMMEND[a["size"]] if w in serves]
    not_for = [w for w in a["wants"] if w not in serves]
    packs = []
    for cc in a["countries"]:
        f = P.freshness(cc)
        packs.append({"cc": cc, "pack": "floor" if f["floor"] else "country", "checked": f["checked"],
                      "source_read": f["source_read"], "verify": f["verify"], "expired": f["expired"]})
    ye = a["year_end"]
    if not ye:
        v = P.peek(a["countries"][0], "tax.year_end")
        ye = v if isinstance(v, str) and re.fullmatch(r"\d\d-\d\d", v) else "12-31"
    return {
        "size": a["size"], "label": sz["label"], "users": sz["users"], "books": sz["books"], "approvals": sz["approvals"],
        "autonomy": {w: sz["autonomy"] for w in wants}, "store": sz["store"], "audit": sz["audit"], "tiers": sz["tiers"],
        "maker_checker": sz["maker_checker"], "clients": sz["clients"], "employees": wants,
        "not_for_this_size": not_for, "packs": packs, "year_end": ye,
        "deciders": [p for p in a["people"] if p["role"] in ("approver", "reviewer", "owner")],
    }


def _hash(a: dict, settings: dict) -> str:
    return hashlib.sha256(json.dumps({"a": a, "s": settings}, sort_keys=True).encode()).hexdigest()


def preview(answers: dict | None) -> dict[str, Any]:
    a = clean(answers)
    s = derive(a)
    lines = [f"Size: {s['label']}", f"Countries: {', '.join(a['countries'])} ({a['currency']})",
             "Employees: " + ", ".join(EMPLOYEES[w] for w in s["employees"]),
             f"Approvals: {s['approvals'].replace('_', ' ')}", f"Year end: {s['year_end']}"]
    for p in s["packs"]:
        if p["pack"] == "floor":
            lines.append(f"{p['cc']}: no country pack yet - explanations, budgets, documents and maths on her own numbers only")
        elif p["checked"] == 0:
            lines.append(f"{p['cc']}: country rules not checked yet - Hoola will say 'check this' before using any")
    if s["not_for_this_size"]:
        lines.append("Not for this size: " + ", ".join(EMPLOYEES[w] for w in s["not_for_this_size"]))
    return {"answers": a, "settings": s, "lines": lines, "hash": _hash(a, s)}


# ---- stored workspaces ---------------------------------------------------------------------------------------------------------

def _view(w) -> dict[str, Any]:
    return {"id": w.id, "name": w.name, "size": w.size, "entity_type": w.entity_type, "countries": json.loads(w.countries or "[]"),
            "currency": w.currency, "parent_id": w.parent_id, "settings": json.loads(w.settings or "{}"), "status": w.status,
            "hash": w.hash}


def apply(tenant: str, answers: dict | None, hash: str, workspace_id: str = "", parent_id: str = "", actor: str = "owner") -> dict[str, Any]:
    from ..db import now, session
    from . import evidence as EV
    from .models import FinWorkspace, ensure
    pv = preview(answers)
    if not hash or hash != pv["hash"]:
        raise ProfileError("The setup changed since it was shown; look at it again and tap once more.")
    ensure()
    a, s = pv["answers"], pv["settings"]
    with session() as db:
        if parent_id:
            par = db.get(FinWorkspace, parent_id)
            if not par or par.tenant_id != tenant or par.size != "firm":
                raise ProfileError("A client book can only sit inside a firm workspace of this account.")
        w = db.get(FinWorkspace, workspace_id) if workspace_id else None
        if w is not None and w.tenant_id != tenant:
            raise ProfileError("No such workspace.")
        if w is None:
            w = FinWorkspace(tenant_id=tenant, parent_id=parent_id)
            db.add(w)
        w.name = a["name"] or SIZES[a["size"]]["label"]
        w.size, w.entity_type, w.currency = a["size"], a["entity_type"], a["currency"]
        w.countries, w.answers, w.settings = json.dumps(a["countries"]), json.dumps(a), json.dumps(s)
        w.hash, w.updated_at = pv["hash"], now()
        db.flush()
        out = _view(w)
    EV.record(tenant, out["id"], actor, "profile", f"setup applied: {a['size']}", {"hash": pv["hash"]})
    return out


def workspaces(tenant: str) -> list[dict[str, Any]]:
    from ..db import session
    from .models import FinWorkspace, ensure
    ensure()
    with session() as db:
        rows = db.query(FinWorkspace).filter(FinWorkspace.tenant_id == tenant, FinWorkspace.status == "active") \
            .order_by(FinWorkspace.created_at).all()
        return [_view(w) for w in rows]


def get(tenant: str, workspace_id: str) -> dict[str, Any]:
    from ..db import session
    from .models import FinWorkspace, ensure
    ensure()
    with session() as db:
        w = db.get(FinWorkspace, workspace_id)
        if not w or w.tenant_id != tenant:
            raise ProfileError("No such workspace.")
        return _view(w)


# ---- what every part reads (configuration, never a code branch on size) ----------------------------------------------------------

def approval_for(ws: dict[str, Any], action: str) -> str:
    """How an action of this kind is approved in this workspace: her_tap | roles_and_limits | partner_review | maker_checker."""
    s = ws.get("settings") or {}
    if action in ("read", "explain", "calculate"):
        return "none"
    return s.get("approvals") or "her_tap"


def autonomy(ws: dict[str, Any], employee: str) -> str:
    return (ws.get("settings") or {}).get("autonomy", {}).get(employee, "learning")


def store(ws: dict[str, Any]) -> str:
    return (ws.get("settings") or {}).get("store", "sqlite")


def audit_level(ws: dict[str, Any]) -> str:
    return (ws.get("settings") or {}).get("audit", "simple")


def tier_allowed(ws: dict[str, Any], tier: str) -> bool:
    return tier in ((ws.get("settings") or {}).get("tiers") or ["A"])
