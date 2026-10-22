"""v0.131 The app blueprint: everything under the screens of a complex app, decided by code from the archetype (or the simple
goal), the screens in the plan and her words, and changed in her words later:

  archetype + modules -> data model (tables, keys, relations, RLS, sync columns; Postgres + phone SQLite + Room + ER page)
  org levels + roles + permission matrix + approval chain by amount (orgmodel)
  login plan (auth) and the phone capabilities with Play / App Store status (capabilities; restricted ones replaced by their
  allowed alternative, never promised)

It is part of the design contract: the design hash covers it, so 'Design pakka' freezes screens AND blueprint together."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from . import auth as AU
from . import capabilities as CP
from . import datamodel as DM
from . import orgmodel as OM
from . import taxonomy as T

# simple (customer) goals -> modules / roles / levels
SIMPLE: dict[str, dict[str, Any]] = {
    "shop": {"modules": ["sales", "inventory", "crm"], "roles": ["super_admin", "admin", "staff", "customer"], "levels": "retail"},
    "food_order": {"modules": ["sales", "inventory", "crm"], "roles": ["super_admin", "admin", "kitchen", "customer"], "levels": "retail"},
    "booking": {"modules": ["crm", "sales", "hr", "tasks"], "roles": ["super_admin", "admin", "staff", "customer"], "levels": "clinic"},
    "learning": {"modules": ["education", "sales", "comms"], "roles": ["super_admin", "admin", "teacher", "student"], "levels": "school"},
    "membership": {"modules": ["crm", "sales", "hr"], "roles": ["super_admin", "admin", "trainer", "member"], "levels": "retail"},
    "service_request": {"modules": ["service", "sales", "field"], "roles": ["super_admin", "admin", "field", "customer"], "levels": "service"},
    "khata": {"modules": ["sales", "crm", "finance"], "roles": ["super_admin", "admin", "staff", "customer"], "levels": "retail"},
    "catalogue": {"modules": ["sales", "crm"], "roles": ["super_admin", "admin", "staff", "customer"], "levels": "retail"},
    "events": {"modules": ["events", "sales", "comms"], "roles": ["super_admin", "admin", "volunteer", "customer"], "levels": "project"},
    "community": {"modules": ["comms", "events", "sales"], "roles": ["super_admin", "admin", "member"], "levels": "society"},
}
SIMPLE_AUTH = ["phone_otp", "google", "apple", "biometric_unlock"]
SENSITIVE_MODULES = {"health", "hr", "finance", "education"}


def is_complex(goal: str) -> bool:
    return bool((T.GOALS.get(goal) or {}).get("complex"))


def make(goal: str, screens: list[str], words: str = "", extra: dict[str, Any] | None = None) -> dict[str, Any]:
    g = T.GOALS.get(goal) or T.GOALS["shop"]
    cx = bool(g.get("complex"))
    base = g if cx else SIMPLE.get(goal, SIMPLE["shop"])
    modules = list(dict.fromkeys(base["modules"] + (["approvals"] if g.get("money") and cx else [])))
    data_extra = (extra or {}).get("data") or {}
    model = DM.build(modules, data_extra)
    sensitive = bool(SENSITIVE_MODULES & set(modules))
    org = OM.build(base["levels"], base["roles"], model["modules"], bool(g.get("money")))
    asked = CP.from_words(words)
    wanted = CP.resolve(list(g.get("caps") or []) + CP.from_screens(screens) + asked)
    if sensitive:
        wanted = CP.resolve(wanted + ["screen_secure", "keystore"])
    wanted = CP.resolve(wanted + ["keystore", "offline_db", "push_fcm"] if cx else wanted + ["push_fcm"])
    capcheck = CP.check(wanted)
    login = AU.plan(list(g.get("auth") or SIMPLE_AUTH), bool(g.get("money")), cx, sensitive)
    bp = {"v": 1, "goal": goal, "complex": cx, "archetype": g["label"] if cx else "", "modules": model["modules"],
          "module_labels": {m: DM.MODULES.get(m, m) for m in model["modules"]},
          "org": org, "login": login, "caps": capcheck, "caps_asked": asked, "caps_usable": CP.usable(wanted),
          "data_extra": data_extra, "data": DM.summary(model), "sensitive": sensitive,
          "offline": "offline_db" in wanted}
    bp["problems"] = list(org.get("problems") or []) + list(model.get("problems") or [])
    bp["hash"] = hash_of(bp)
    return bp


def model_of(bp: dict[str, Any]) -> dict[str, Any]:
    mods = [m for m in bp.get("modules", []) if m in DM.MODULES]
    return DM.build(mods, bp.get("data_extra") or {})


def hash_of(bp: dict[str, Any]) -> str:
    keep = {k: bp.get(k) for k in ("goal", "modules", "data_extra")}
    keep["org"] = {k: (bp.get("org") or {}).get(k) for k in ("levels", "roles", "matrix", "approvals", "custom_roles")}
    keep["login"] = (bp.get("login") or {}).get("ids")
    keep["caps"] = [c["id"] for c in (bp.get("caps") or {}).get("caps", [])]
    return hashlib.sha256(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()[:20]


def change(bp: dict[str, Any], ops: dict[str, Any], words: str = "") -> tuple[dict[str, Any], list[str]]:
    """ops from the CHANGE prompt's "blueprint" key: levels, add_roles, remove_roles, matrix, login {add, remove},
    caps {add, remove}, add_entities, add_fields, modules {add, remove}. Never touches the screens."""
    done: list[str] = []
    b = json.loads(json.dumps(bp))
    mods = list(b.get("modules") or [])
    for m in (ops.get("modules") or {}).get("add") or []:
        if m in DM.MODULES and m not in mods:
            mods.append(m)
            done.append(f"module + {m}")
    for m in (ops.get("modules") or {}).get("remove") or []:
        if m in mods and m != "core":
            mods.remove(m)
            done.append(f"module - {m}")
    data_extra, d2 = DM.change(b.get("data_extra") or {}, ops)
    done += d2
    model = DM.build([m for m in mods if m != "core"], data_extra)
    org, d3 = OM.change({**b["org"], "modules": model["modules"]}, ops)
    if set(model["modules"]) != set(b["org"].get("modules", [])):
        cu = org.get("custom_roles")
        org["matrix"] = {r: OM.role_perms(r, model["modules"], cu) for r in org["roles"]}
        org["modules"] = model["modules"]
        org["problems"] = OM.validate(org)
    done += d3
    login_ids = list((b.get("login") or {}).get("ids") or [])
    for m in (ops.get("login") or {}).get("add") or []:
        if m in AU.METHODS and m not in login_ids:
            login_ids.append(m)
            done.append(f"login + {AU.METHODS[m]['label']}")
    for m in (ops.get("login") or {}).get("remove") or []:
        if m in login_ids:
            login_ids.remove(m)
            done.append(f"login - {m}")
    g = T.GOALS.get(b["goal"]) or {}
    sensitive = bool(SENSITIVE_MODULES & set(model["modules"]))
    login = AU.plan(login_ids, bool(g.get("money")), bool(g.get("complex")), sensitive)
    caps = [c["id"] for c in (b.get("caps") or {}).get("caps", [])]
    add = CP.resolve(list((ops.get("caps") or {}).get("add") or []) + CP.from_words(words))
    for c in add:
        if c not in caps:
            caps.append(c)
            done.append(f"cap + {CP.CAPS[c]['label']}")
    for c in (ops.get("caps") or {}).get("remove") or []:
        if c in caps:
            caps.remove(c)
            done.append(f"cap - {c}")
    capcheck = CP.check(caps)
    b.update({"modules": model["modules"], "module_labels": {m: DM.MODULES.get(m, m) for m in model["modules"]}, "org": org,
              "login": login, "caps": capcheck, "caps_usable": CP.usable(caps), "caps_asked": list(dict.fromkeys(
                  (b.get("caps_asked") or []) + CP.from_words(words))), "data_extra": data_extra, "data": DM.summary(model),
              "sensitive": sensitive})
    b["problems"] = list(org.get("problems") or []) + list(model.get("problems") or [])
    b["hash"] = hash_of(b)
    return b, done


def view(bp: dict[str, Any]) -> dict[str, Any]:
    """Compact for the plan card / app."""
    if not bp:
        return {}
    org = bp.get("org") or {}
    caps = bp.get("caps") or {}
    return {"archetype": bp.get("archetype"), "complex": bp.get("complex"), "modules": bp.get("module_labels"),
            "levels": org.get("levels"), "roles": [{"id": r, "label": (org.get("role_labels") or {}).get(r, r)} for r in org.get("roles", [])],
            "matrix": org.get("matrix"), "approvals": org.get("approvals"), "org_rules": org.get("rules", [])[:5],
            "login": [{"id": m["id"], "label": m["label"], "kind": m["kind"]} for m in (bp.get("login") or {}).get("methods", [])],
            "login_rules": (bp.get("login") or {}).get("rules", []), "login_warnings": (bp.get("login") or {}).get("warnings", []),
            "caps": [{"id": c["id"], "label": c["label"], "play": c["play"], "play_label": c["play_label"], "ios": c["ios"],
                      "ios_label": c["ios_label"]} for c in caps.get("caps", [])],
            "cap_problems": caps.get("problems", []), "cap_notes": caps.get("notes", [])[:6],
            "permissions": caps.get("permissions", []), "data": {k: (bp.get("data") or {}).get(k) for k in
                                                               ("tables", "columns", "relations", "sensitive", "geo")},
            "tables": {m: ts for m, ts in ((bp.get("data") or {}).get("modules") or {}).items()},
            "sensitive": bp.get("sensitive"), "offline": bp.get("offline"), "problems": bp.get("problems", []),
            "hash": bp.get("hash")}


def say(bp: dict[str, Any]) -> str:
    return say_view(view(bp)) if bp else ""


def say_view(v: dict[str, Any]) -> str:
    if not v or not v.get("data"):
        return ""
    bits = [f"{v['data']['tables']} tables", f"{len(v['roles'])} roles", f"{len(v['levels'] or [])} levels ({' > '.join(v['levels'] or [])})",
            "login: " + ", ".join(m["label"] for m in v["login"][:4])]
    s = "Andar ka dhaancha: " + "; ".join(bits) + "."
    if v["cap_problems"]:
        s += " Store nahi dete: " + "; ".join(p["text"].split(":")[0] for p in v["cap_problems"]) + " (iski jagah doosra tareeka joda)."
    return s


def write_files(bp: dict[str, Any], out_dir, title: str = "") -> dict[str, str]:
    """schema.sql (Postgres + PostGIS), schema-plain.sql (no PostGIS), app.sqlite.sql, room/Entities.kt, er.mmd, er.html,
    blueprint.json into the app folder (the native build reads them)."""
    from pathlib import Path
    d = Path(out_dir) / "blueprint"
    d.mkdir(parents=True, exist_ok=True)
    model = model_of(bp)
    files = {"schema.sql": DM.ddl_postgres(model, "postgis"), "schema-plain.sql": DM.ddl_postgres(model, "plain"),
             "app.sqlite.sql": DM.ddl_sqlite(model), "Entities.kt": DM.room_kotlin(model), "er.mmd": DM.mermaid(model),
             "er.html": DM.er_html(model, title), "blueprint.json": json.dumps(bp, ensure_ascii=False, indent=1, default=str)}
    for name, text in files.items():
        (d / name).write_text(text)
    return {k: f"blueprint/{k}" for k in files}


def check() -> list[str]:
    """Every archetype refers to real screens, modules, roles, level presets, capabilities, login methods and fallback field."""
    from ..site import library as SL
    p: list[str] = []
    F = SL.fields()
    for gid, g in T.GOALS.items():
        if not g.get("complex"):
            if gid not in SIMPLE:
                p.append(f"goal {gid}: no simple blueprint")
            continue
        for m in g["modules"]:
            if m not in DM.MODULES:
                p.append(f"{gid}: module {m}")
        for r in g["roles"]:
            if r not in OM.ROLES:
                p.append(f"{gid}: role {r}")
        if g["levels"] not in OM.LEVELS:
            p.append(f"{gid}: levels {g['levels']}")
        for c in g["caps"]:
            if c not in CP.CAPS:
                p.append(f"{gid}: cap {c}")
        for a in g["auth"]:
            if a not in AU.METHODS:
                p.append(f"{gid}: auth {a}")
        if g["fallback"] not in F:
            p.append(f"{gid}: fallback field {g['fallback']}")
        for st in g["styles"]:
            if st not in T.STYLES:
                p.append(f"{gid}: style {st}")
        from ..site import taxonomy as ST
        for ind in g["industries"]:
            if ind not in ST.INDUSTRIES:
                p.append(f"{gid}: industry {ind}")
        bp = make(gid, g["screens"])
        if bp["problems"]:
            p.append(f"{gid}: {bp['problems'][:3]}")
    for c in CP.CAPS.values():
        if c["alt"] and c["alt"] not in CP.CAPS:
            p.append(f"cap alt {c['alt']}")
    return p
