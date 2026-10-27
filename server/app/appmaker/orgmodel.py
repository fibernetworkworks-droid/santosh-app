"""v0.131 Organisation hierarchy and who-can-do-what for complex apps.

Levels: up to 8 named levels (Company > Region > Zone > Branch > Team ...), presets per kind of business. Every record belongs
to one org unit; a person sees records by SCOPE: own (made by / assigned to me) < unit (my unit and below) < parent (my
unit's parent and below) < all. Roles = a base template (super_admin, admin, manager, supervisor, staff, field, customer,
auditor, viewer) + a name in the business's words (Doctor, Captain, Guard ...). Permissions per module x action
(read, create, update, delete, approve, export) -> scope or none. Money approvals climb a chain by amount. The server
enforces all of it (row-level security in the database + checks in the API); the app only hides what isn't allowed."""
from __future__ import annotations

import copy
import re
from typing import Any

MAX_LEVELS = 8
ACTIONS = ["read", "create", "update", "delete", "approve", "export"]
SCOPES = ["none", "own", "unit", "parent", "all"]
SCOPE_LABEL = {"none": "-", "own": "Apna", "unit": "Apni unit + neeche", "parent": "Upar wali unit + neeche", "all": "Sab"}

LEVELS: dict[str, list[str]] = {
    "company": ["Company", "Region", "Branch", "Department", "Team"],
    "sales": ["Company", "Zone", "Region", "Area", "Territory"],
    "service": ["Company", "Region", "Service centre", "Team"],
    "warehouse": ["Company", "Warehouse", "Zone", "Rack"],
    "retail": ["Company", "City", "Outlet", "Counter"],
    "plant": ["Company", "Plant", "Department", "Line", "Shift"],
    "logistics": ["Company", "Region", "Hub", "Route"],
    "isp": ["Company", "Circle", "Zone", "POP", "Cluster"],
    "project": ["Organisation", "Programme", "Project", "Site"],
    "hospital": ["Group", "Hospital", "Department", "Ward / Unit"],
    "clinic": ["Clinic", "Branch", "Room"],
    "school": ["Trust", "School / Campus", "Grade", "Section"],
    "hotel": ["Group", "Property", "Department"],
    "society": ["Society", "Wing / Tower", "Floor"],
    "agri": ["FPO / Society", "Block", "Village", "Collection centre"],
}

# base templates: module -> action -> scope (applied to every module the app has, with the exceptions below)
BASE: dict[str, dict[str, str]] = {
    "super_admin": {a: "all" for a in ACTIONS},
    "admin": {"read": "all", "create": "all", "update": "all", "delete": "all", "approve": "all", "export": "all"},
    "manager": {"read": "unit", "create": "unit", "update": "unit", "delete": "none", "approve": "unit", "export": "unit"},
    "supervisor": {"read": "unit", "create": "unit", "update": "unit", "delete": "none", "approve": "unit", "export": "none"},
    "staff": {"read": "unit", "create": "own", "update": "own", "delete": "none", "approve": "none", "export": "none"},
    "field": {"read": "own", "create": "own", "update": "own", "delete": "none", "approve": "none", "export": "none"},
    "customer": {"read": "own", "create": "own", "update": "own", "delete": "none", "approve": "none", "export": "none"},
    "auditor": {"read": "all", "create": "none", "update": "none", "delete": "none", "approve": "none", "export": "all"},
    "viewer": {"read": "unit", "create": "none", "update": "none", "delete": "none", "approve": "none", "export": "none"},
}

# named roles in the business's words -> base template (+ modules they may not touch / may only read)
ROLES: dict[str, dict[str, Any]] = {
    "super_admin": {"label": "Owner / Super admin", "hi": "malik", "base": "super_admin"},
    "admin": {"label": "Admin", "hi": "admin", "base": "admin", "no": []},
    "manager": {"label": "Manager", "hi": "manager", "base": "manager"},
    "regional_head": {"label": "Regional head", "hi": "regional head", "base": "manager", "scope_up": True},
    "supervisor": {"label": "Supervisor", "hi": "supervisor", "base": "supervisor"},
    "staff": {"label": "Staff", "hi": "staff", "base": "staff"},
    "field": {"label": "Field staff", "hi": "field staff", "base": "field"},
    "customer": {"label": "Customer", "hi": "graahak", "base": "customer", "only": ["sales", "service", "crm", "comms", "core"]},
    "auditor": {"label": "Auditor", "hi": "auditor", "base": "auditor"},
    "viewer": {"label": "Viewer", "hi": "dekhne wala", "base": "viewer"},
    "hr": {"label": "HR", "hi": "HR", "base": "manager", "focus": ["hr"], "scope_all": ["hr"]},
    "accounts": {"label": "Accounts", "hi": "accounts", "base": "manager", "focus": ["finance", "sales", "purchase"], "scope_all": ["finance", "sales", "purchase"]},
    "cashier": {"label": "Cashier", "hi": "cashier", "base": "staff", "focus": ["sales"]},
    "dispatcher": {"label": "Dispatcher", "hi": "dispatcher", "base": "supervisor", "focus": ["logistics"]},
    "driver": {"label": "Driver / rider", "hi": "driver", "base": "field", "focus": ["logistics"]},
    "noc": {"label": "NOC engineer", "hi": "NOC", "base": "supervisor", "focus": ["isp", "iot", "service"], "scope_all": ["isp", "iot"]},
    "operator": {"label": "Operator", "hi": "operator", "base": "staff"},
    "doctor": {"label": "Doctor", "hi": "doctor", "base": "staff", "focus": ["health"], "write": ["health"]},
    "nurse": {"label": "Nurse", "hi": "nurse", "base": "staff", "focus": ["health"]},
    "front_desk": {"label": "Front desk", "hi": "reception", "base": "staff", "focus": ["sales", "crm", "health", "hospitality"],
                   "read_only": ["health"]},
    "lab": {"label": "Lab staff", "hi": "lab", "base": "staff", "focus": ["health"]},
    "phlebotomist": {"label": "Sample collector", "hi": "sample collector", "base": "field", "focus": ["health", "logistics"]},
    "pharmacy": {"label": "Pharmacist", "hi": "pharmacist", "base": "staff", "focus": ["inventory", "health"], "read_only": ["health"]},
    "principal": {"label": "Principal", "hi": "principal", "base": "manager"},
    "teacher": {"label": "Teacher", "hi": "teacher", "base": "staff", "focus": ["education", "comms"]},
    "parent": {"label": "Parent", "hi": "abhibhavak", "base": "customer", "only": ["education", "comms", "sales", "core"]},
    "student": {"label": "Student", "hi": "student", "base": "customer", "only": ["education", "comms", "sales", "core"]},
    "counsellor": {"label": "Counsellor", "hi": "counsellor", "base": "staff", "focus": ["crm"]},
    "housekeeping": {"label": "Housekeeping", "hi": "housekeeping", "base": "field", "focus": ["hospitality", "tasks", "service"]},
    "captain": {"label": "Captain / waiter", "hi": "captain", "base": "staff", "focus": ["sales"]},
    "kitchen": {"label": "Kitchen", "hi": "kitchen", "base": "staff", "focus": ["sales", "inventory", "tasks"]},
    "channel_partner": {"label": "Channel partner", "hi": "channel partner", "base": "customer", "only": ["crm", "sales", "core"]},
    "committee": {"label": "Committee member", "hi": "committee", "base": "manager"},
    "guard": {"label": "Guard", "hi": "guard", "base": "field"},
    "resident": {"label": "Resident", "hi": "nivasi", "base": "customer", "only": ["society", "service", "comms", "sales", "core"]},
    "client": {"label": "Client", "hi": "client", "base": "viewer"},
    "inspector": {"label": "Inspector", "hi": "inspector", "base": "field"},
    "farmer": {"label": "Farmer member", "hi": "kisan", "base": "customer", "only": ["agri", "sales", "comms", "core"]},
    "member": {"label": "Member", "hi": "sadasya", "base": "customer"},
    "donor": {"label": "Donor", "hi": "daata", "base": "viewer", "only": ["reports", "core"]},
    "volunteer": {"label": "Volunteer", "hi": "volunteer", "base": "field"},
    "vendor": {"label": "Vendor", "hi": "vendor", "base": "customer"},
    "trainer": {"label": "Trainer", "hi": "trainer", "base": "staff"},
}

# who owns money / sensitive actions regardless of role (house rules, enforced by the server)
RULES = [
    "Maker-checker: nobody approves their own request (create and approve by the same person is refused).",
    "Delete is soft (deleted_at); only admins can restore or purge, and purging is logged.",
    "Auditors only read and export; every export above the role's limit needs an approval and is logged.",
    "Customers / parents / residents see only their own records.",
    "Health, payslip and ID data: only the roles that need it, screenshots blocked, every view logged.",
    "A person leaving: switched off at once, their open work moves to their manager.",
    "Changes to roles, approval limits and payout details need the second login step and land in the audit log.",
]


def levels_for(preset: str, names: list[str] | None = None) -> list[str]:
    lv = [re.sub(r"\s+", " ", str(x)).strip()[:30] for x in (names or LEVELS.get(preset) or LEVELS["company"])]
    lv = [x for x in lv if x][:MAX_LEVELS]
    return lv or list(LEVELS["company"])


def _scope_max(a: str, b: str) -> str:
    return a if SCOPES.index(a) >= SCOPES.index(b) else b


def _role(role: str, custom: dict[str, Any] | None = None) -> dict[str, Any]:
    return (custom or {}).get(role) or ROLES.get(role) or {"base": "staff", "label": role}


def role_perms(role: str, modules: list[str], custom: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    r = _role(role, custom)
    base = BASE[r["base"]]
    out: dict[str, dict[str, str]] = {}
    for m in ["core", *modules]:
        p = dict(base)
        if r.get("only") is not None and m not in r["only"]:
            p = {a: "none" for a in ACTIONS}
        if m in r.get("read_only", []):
            p = {a: ("unit" if a == "read" else "none") for a in ACTIONS}
        if m in r.get("scope_all", []):
            p = {a: (_scope_max(v, "all") if v != "none" else "none") for a, v in p.items()}
            p["read"] = "all"
        if m in r.get("write", []):
            p["update"] = _scope_max(p["update"], "unit")
            p["create"] = _scope_max(p["create"], "unit")
        if r.get("focus") and m not in r["focus"] and m not in ("core", "comms", "reports") and r["base"] not in ("customer",):
            p = {a: ("own" if a == "read" and v != "none" else "none") for a, v in p.items()}
        if r.get("scope_up"):
            p = {a: ("parent" if v == "unit" else v) for a, v in p.items()}
        if m == "core" and r["base"] not in ("super_admin", "admin"):
            p = {"read": "own" if r["base"] in ("customer", "field") else "unit", "create": "none", "update": "own",
                 "delete": "none", "approve": "none", "export": "none"}
        if m == "reports" and r["base"] in ("staff", "field", "customer"):
            p = {a: ("own" if a == "read" else "none") for a in ACTIONS}
        out[m] = p
    return out


def matrix(roles: list[str], modules: list[str]) -> dict[str, dict[str, dict[str, str]]]:
    return {r: role_perms(r, modules) for r in roles}


def approval_chain(roles: list[str], money: bool) -> list[dict[str, Any]]:
    """Money approvals by amount (rupees), using the approver roles this app has."""
    if not money:
        return [{"upto": None, "role": next((r for r in ("manager", "supervisor", "admin") if r in roles), "admin"),
                 "what": "leave, tasks, changes"}]
    order = [r for r in ("supervisor", "manager", "regional_head", "accounts", "admin", "super_admin") if r in roles]
    if not order:
        order = ["admin"]
    caps = [10000, 50000, 200000, 1000000]
    chain = []
    for i, r in enumerate(order[:4]):
        chain.append({"upto": caps[i] if i < len(order) - 1 else None, "role": r})
    return chain


def org_chart(levels: list[str], roles: list[str]) -> dict[str, Any]:
    """A small example tree for the preview / ER screen (not her real data)."""
    def node(depth: int, idx: int) -> dict[str, Any]:
        n = {"level": levels[depth], "name": f"{levels[depth]} {idx + 1}", "children": []}
        if depth + 1 < len(levels):
            n["children"] = [node(depth + 1, j) for j in range(2 if depth < 2 else 1)]
        return n
    return node(0, 0)


def validate(org: dict[str, Any]) -> list[str]:
    p: list[str] = []
    lv = org.get("levels") or []
    if not 1 <= len(lv) <= MAX_LEVELS:
        p.append(f"levels: {len(lv)} (1-{MAX_LEVELS})")
    if len(set(x.lower() for x in lv)) != len(lv):
        p.append("levels: duplicate names")
    roles = org.get("roles") or []
    cu = org.get("custom_roles") or {}
    if not any(_role(r, cu).get("base") in ("super_admin", "admin") for r in roles):
        p.append("roles: no admin")
    mx = org.get("matrix") or {}
    for r, mods in mx.items():
        for m, acts in mods.items():
            for a, s in acts.items():
                if a not in ACTIONS or s not in SCOPES:
                    p.append(f"{r}.{m}.{a}: bad scope {s}")
            if acts.get("approve", "none") != "none" and acts.get("read", "none") == "none":
                p.append(f"{r}.{m}: approve without read")
            if acts.get("update", "none") != "none" and acts.get("read", "none") == "none":
                p.append(f"{r}.{m}: update without read")
        if _role(r, cu).get("base") == "auditor" and any(acts.get(a) not in ("none", None) for m, acts in mods.items() if m != "core"
                                                             for a in ("create", "update", "delete", "approve")):
            p.append(f"{r}: auditor can write")
        if _role(r, cu).get("base") == "customer" and any(s in ("unit", "parent", "all") for acts in mods.values()
                                                              for s in acts.values()):
            p.append(f"{r}: customer sees others")
    return p


def build(preset: str, roles: list[str], modules: list[str], money: bool, levels: list[str] | None = None) -> dict[str, Any]:
    roles = [r for r in dict.fromkeys(roles) if r in ROLES] or ["super_admin", "admin", "staff"]
    if "super_admin" not in roles:
        roles.insert(0, "super_admin")
    lv = levels_for(preset, levels)
    org = {"preset": preset, "levels": lv, "roles": roles, "modules": list(modules),
           "role_labels": {r: ROLES[r]["label"] for r in roles}, "matrix": matrix(roles, modules),
           "approvals": approval_chain(roles, money), "rules": list(RULES), "scopes": dict(SCOPE_LABEL)}
    org["problems"] = validate(org)
    return org


def change(org: dict[str, Any], ops: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Her changes in structured form (from the CHANGE prompt): levels, add / remove roles, matrix cells."""
    o = copy.deepcopy(org)
    done: list[str] = []
    if isinstance(ops.get("levels"), list) and ops["levels"]:
        o["levels"] = levels_for(o.get("preset", "company"), ops["levels"])
        done.append("levels: " + " > ".join(o["levels"]))
    for x in ops.get("add_roles") or []:
        rid = re.sub(r"[^a-z0-9_]", "_", str(x.get("id") or x.get("name") or "").lower()).strip("_")[:30]
        like = x.get("like") if x.get("like") in BASE else (ROLES.get(x.get("like") or "", {}).get("base") or "staff")
        if not rid or rid in o["roles"]:
            continue
        cu = o.setdefault("custom_roles", {})
        if rid not in ROLES:
            cu[rid] = {"label": str(x.get("name") or rid)[:40], "hi": str(x.get("name") or rid)[:40], "base": like, "custom": True}
        o["roles"].append(rid)
        o["role_labels"][rid] = _role(rid, cu)["label"]
        o["matrix"][rid] = role_perms(rid, o["modules"], cu)
        done.append(f"role + {o['role_labels'][rid]}")
    for rid in ops.get("remove_roles") or []:
        if rid in o["roles"] and _role(rid, o.get("custom_roles")).get("base") != "super_admin":
            o["roles"].remove(rid)
            o["matrix"].pop(rid, None)
            o["role_labels"].pop(rid, None)
            done.append(f"role - {rid}")
    for c in ops.get("matrix") or []:
        r, m, a, s = c.get("role"), c.get("module"), c.get("action"), c.get("scope")
        if r in o["matrix"] and m in o["matrix"][r] and a in ACTIONS and s in SCOPES:
            o["matrix"][r][m][a] = s
            done.append(f"{r}.{m}.{a}={s}")
    o["approvals"] = approval_chain(o["roles"], any(c.get("upto") for c in o.get("approvals", [])) or bool(ops.get("money")))
    o["problems"] = validate(o)
    return o, done


def counts() -> dict[str, int]:
    return {"role_templates": len(BASE), "named_roles": len(ROLES), "level_presets": len(LEVELS), "max_levels": MAX_LEVELS}
