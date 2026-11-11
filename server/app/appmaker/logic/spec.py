"""v0.382 DIMAAG: the app's logic spec - read, cleaned and CHECKED against the app's real lists before it can go live.

be["logic"] = {
  "relations":  [{name, from, field, to, label, on_delete: restrict|cascade|nullify, share: bool}]   customer -> orders -> lines
  "formulas":   [{coll, field, expr}]                                                    computed on every write
  "rules":      [{coll, check, message, on: always|create|update}]                       cross-field checks
  "unique":     [{coll, fields: [...], message}]                                         unique keys
  "workflows":  [{coll, field, states, initial, transitions: [{from, to, label, who, approval, require, when}],
                  sla: [{state, hours, notify, move_to, message}]}]                       state machine + approvals + SLA
  "triggers":   [{name, coll, on: create|update|delete|change:<field>|enter:<state>, when, do: [actions]}]
  "schedules":  [{name, every: hourly|daily HH:MM|weekly mon HH:MM|monthly D HH:MM, coll, where, do, once_per_row}]
  "functions":  [{name, params, body, tests: [{args, expect} | {args, fails}], callable}]  locked custom logic
  "labels":     {coll: field}                                                            what a row is called
  "gates":      [{coll, pass, via, pass_field, match: {field: value}}]   v0.581 read only with an active pass (a course)
  "subscription_list": coll                                             v0.581 her AutoPay plans -> one row per member
  "documents":  [{coll, title, lines: ["... {{expr}} ..."], signer, when}]  v0.581 a PDF from a row (a certificate)
}
Everything Opus (or the console) writes passes `check()`: every list / field / state / name must exist, every
formula and function must parse, formulas may not loop on each other, every function's own tests must pass. Only a
spec with zero errors can be applied - and only by her tap."""
from __future__ import annotations

import copy
import re
from typing import Any

from . import lang as L

WHO = ("member", "row_owner", "assigned", "staff", "admin", "owner")
ON_DELETE = ("restrict", "cascade", "nullify")
NOTIFY = ("owner", "staff", "admins", "row_owner", "assigned")
CAPS = {"relations": 24, "formulas": 60, "rules": 60, "unique": 20, "workflows": 12, "triggers": 60, "schedules": 20,
        "functions": 30, "transitions": 30, "actions": 8, "tests": 12, "gates": 12, "documents": 6}
EVERY = re.compile(r"^(hourly|daily (\d{1,2}):(\d{2})|weekly (mon|tue|wed|thu|fri|sat|sun) (\d{1,2}):(\d{2})|"
                   r"monthly (\d{1,2}) (\d{1,2}):(\d{2}))$")
TEMPLATE = re.compile(r"\{\{(.+?)\}\}")
CTX_NAMES = {"me", "id", "created", "owner_id"}


def slug(s: Any, n: int = 30) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(s or "").lower()).strip("_")[:n]


def _strs(v: Any) -> list[str]:
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return [str(x).strip() for x in (v or []) if str(x).strip()] if isinstance(v, list) else []


class Checker:
    def __init__(self, sch: dict[str, Any]):
        self.colls = {c["key"]: c for c in (sch or {}).get("collections") or []}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.rel: list[dict[str, Any]] = []
        self.fns: dict[str, tuple[list[str], Any]] = {}

    def err(self, where: str, msg: str):
        self.errors.append(f"{where}: {msg}")

    def fields(self, coll: str) -> dict[str, dict[str, Any]]:
        return {f["key"]: f for f in (self.colls.get(coll) or {}).get("fields") or []}

    def has_coll(self, where: str, coll: str) -> bool:
        if coll not in self.colls:
            self.err(where, f"list '{coll}' is not in the app")
            return False
        return True

    # what a piece of logic on `coll` may read: its fields, its parents (ref fields), its children (relations), me...
    def scope(self, coll: str, extra: set[str] | None = None) -> set[str]:
        s = set(self.fields(coll)) | CTX_NAMES | {r["name"] for r in self.rel if r["to"] == coll} | (extra or set())
        return s

    def keys_of(self, coll: str, name: str) -> set[str] | None:
        """The keys `name.<key>` may use: a ref field -> its target list's fields; a relation -> its child list's fields."""
        f = self.fields(coll).get(name)
        tgt = None
        for r in self.rel:
            if r["from"] == coll and r["field"] == name:
                tgt = r["to"]
            if r["to"] == coll and r["name"] == name:
                tgt = r["from"]
        if tgt is None and f is not None and f.get("type") == "ref":
            tgt = f.get("to")
        if tgt is None:
            return None
        return set(self.fields(tgt)) | {"id", "created"} | {r["name"] for r in self.rel if r["to"] == tgt}

    def expr(self, where: str, src: Any, coll: str, extra: set[str] | None = None, body: bool = False):
        if not str(src or "").strip():
            self.err(where, "is empty")
            return None
        try:
            ast = L.parse_body(str(src)) if body else L.parse_expr(str(src))
        except L.LogicError as e:
            self.err(where, str(e))
            return None
        allowed = self.scope(coll, extra)
        for n in sorted(L.names(ast)):
            if n not in allowed:
                self.err(where, f"no field / list named '{n}' in '{coll}'")
        for c in sorted(L.calls(ast)):
            if c not in L.BUILTINS and c not in L.LAZY and c not in self.fns:
                self.err(where, f"there is no function named '{c}()'")
        for name, key in sorted(L.field_paths(ast)):
            if name in (extra or set()) or name == "me":
                continue
            keys = self.keys_of(coll, name)
            if keys is not None and key not in keys:
                self.err(where, f"'{name}.{key}': '{key}' is not in that list")
        return ast


def check(raw: Any, sch: dict[str, Any], run_tests: bool = True) -> dict[str, Any]:
    """Whatever was written -> {spec (clean), errors, warnings, summary}. errors = [] means it can be applied."""
    ck = Checker(sch)
    raw = raw if isinstance(raw, dict) else {}
    out: dict[str, Any] = {k: [] for k in ("relations", "formulas", "rules", "unique", "workflows", "triggers", "schedules", "functions",
                                           "gates", "documents")}
    out["labels"] = {}
    for k, cap in CAPS.items():
        if k in raw and isinstance(raw[k], list) and len(raw[k]) > cap:
            ck.err(k, f"there are {len(raw[k])}, the limit is {cap}")

    # ---- functions first (formulas may call them); each is pure: it reads only its own params
    for i, f in enumerate((raw.get("functions") or [])[:CAPS["functions"]]):
        if not isinstance(f, dict):
            continue
        name, where = slug(f.get("name")), f"function {f.get('name') or i + 1}"
        if not name or name in L.RESERVED:
            ck.err(where, "a name is needed (and not the same as a built-in)")
            continue
        if name in ck.fns:
            ck.err(where, "this name is used twice")
            continue
        params = [slug(p) for p in _strs(f.get("params"))][:8]
        if any(not p or p in L.RESERVED for p in params) or len(set(params)) != len(params):
            ck.err(where, "param names are wrong / repeated")
            continue
        try:
            body = L.parse_body(str(f.get("body") or ""))
        except L.LogicError as e:
            ck.err(where, str(e))
            continue
        ck.fns[name] = (params, body)
        out["functions"].append({"name": name, "params": params, "body": str(f.get("body") or "")[:L.MAX_SOURCE],
                                 "callable": bool(f.get("callable")), "label": str(f.get("label") or name)[:60],
                                 "tests": [t for t in (f.get("tests") or [])[:CAPS["tests"]] if isinstance(t, dict)]})
    for f in out["functions"]:                  # names inside a body: params, its locals, builtins, other functions
        params, body = ck.fns[f["name"]]
        where = f"function {f['name']}"
        for n in sorted(L.names(body, bound=set(params))):
            ck.err(where, f"'{n}' comes from nowhere (a function reads only its own params)")
        for c in sorted(L.calls(body)):
            if c not in L.BUILTINS and c not in L.LAZY and c not in ck.fns:
                ck.err(where, f"there is no function named '{c}()'")
    if run_tests and not ck.errors:
        for f in out["functions"]:
            if not f["tests"]:
                ck.warnings.append(f"function {f['name']}: no tests (write 2-3 tests for every function)")
            for j, t in enumerate(f["tests"]):
                args = t.get("args") if isinstance(t.get("args"), list) else []
                where = f"function {f['name']} test {j + 1}"
                try:
                    got = L.call_function(ck.fns, f["name"], args)
                    if t.get("fails"):
                        ck.err(where, f"should have failed, got {got!r}")
                    elif "expect" in t and not _same(got, t.get("expect")):
                        ck.err(where, f"expected {t.get('expect')!r}, got {got!r}")
                except L.Fail as e:
                    if not t.get("fails"):
                        ck.err(where, f"failed: {e}")
                except L.LogicError as e:
                    ck.err(where, str(e))

    # ---- relations
    for i, r in enumerate((raw.get("relations") or [])[:CAPS["relations"]]):
        if not isinstance(r, dict):
            continue
        frm, to, field = slug(r.get("from")), slug(r.get("to")), slug(r.get("field"))
        where = f"relation {r.get('name') or i + 1}"
        if not (ck.has_coll(where, frm) and ck.has_coll(where, to)):
            continue
        f = ck.fields(frm).get(field)
        if f is None:
            ck.err(where, f"'{frm}' has no field '{field}' (add the field first)")
            continue
        if f.get("type") not in ("ref", "text"):
            ck.err(where, f"'{frm}.{field}' is a {f.get('type')} field; a link needs a ref field")
            continue
        name = slug(r.get("name")) or frm
        if name in ck.fields(to) or name in CTX_NAMES or name in L.RESERVED:
            ck.err(where, f"the name '{name}' clashes with a field of '{to}'")
            continue
        if any(x["to"] == to and x["name"] == name for x in ck.rel):
            ck.err(where, f"the name '{name}' is used twice on '{to}'")
            continue
        if any(x["from"] == frm and x["field"] == field for x in ck.rel):
            ck.err(where, f"'{frm}.{field}' is already a link")
            continue
        od = r.get("on_delete") if r.get("on_delete") in ON_DELETE else "restrict"
        rel = {"name": name, "from": frm, "field": field, "to": to, "on_delete": od,
               "label": str(r.get("label") or ck.colls[frm].get("label") or frm)[:60]}
        if r.get("share") is True:          # v0.414 a child row belongs to its parent row's person (a parent sees her child's marks)
            rel["share"] = True
        ck.rel.append(rel)
        out["relations"].append(rel)
    for c in ck.colls:                          # a ref field nobody linked is still a parent link for formulas
        for f in ck.colls[c]["fields"]:
            if f.get("type") == "ref" and f.get("to") in ck.colls and not any(x["from"] == c and x["field"] == f["key"] for x in ck.rel):
                ck.rel.append({"name": f"_{c}_{f['key']}", "from": c, "field": f["key"], "to": f["to"], "on_delete": "restrict",
                               "label": c, "_implicit": True})

    # ---- labels
    for c, fk in (raw.get("labels") or {}).items() if isinstance(raw.get("labels"), dict) else []:
        c, fk = slug(c), slug(fk)
        if ck.has_coll("labels", c) and fk in ck.fields(c):
            out["labels"][c] = fk
        elif c in ck.colls:
            ck.err("labels", f"'{c}.{fk}' is not a field")

    # ---- workflows (before formulas: a workflow field is never a formula)
    wf_fields: set[tuple[str, str]] = set()
    for i, w in enumerate((raw.get("workflows") or [])[:CAPS["workflows"]]):
        if not isinstance(w, dict):
            continue
        coll = slug(w.get("coll"))
        where = f"workflow {coll or i + 1}"
        if not ck.has_coll(where, coll):
            continue
        field = slug(w.get("field")) or "status"
        if field not in ck.fields(coll):
            ck.err(where, f"'{coll}' has no field '{field}'")
            continue
        if any(x["coll"] == coll for x in out["workflows"]):
            ck.err(where, "only one workflow per list")
            continue
        states = [str(s).strip()[:40] for s in _strs(w.get("states"))][:20]
        if len(states) < 2 or len(set(states)) != len(states):
            ck.err(where, "at least 2 different states are needed")
            continue
        initial = str(w.get("initial") or states[0]).strip()
        if initial not in states:
            ck.err(where, f"the initial state '{initial}' is not among the states")
            continue
        trs = []
        for j, t in enumerate((w.get("transitions") or [])[:CAPS["transitions"]]):
            if not isinstance(t, dict):
                continue
            tw = f"{where} step {j + 1}"
            frm = ["*"] if t.get("from") in ("*", ["*"]) else _strs(t.get("from"))
            to = str(t.get("to") or "").strip()
            bad = [s for s in frm if s != "*" and s not in states] + ([to] if to not in states else [])
            if bad or not frm:
                ck.err(tw, f"state {', '.join(map(repr, bad)) or '(from)'} is not in the workflow")
                continue
            who = [x for x in _strs(t.get("who")) if x in WHO] or ["staff"]
            req = [slug(x) for x in _strs(t.get("require"))]
            for rq in req:
                if rq not in ck.fields(coll):
                    ck.err(tw, f"required field '{rq}' does not exist")
            tr: dict[str, Any] = {"from": frm, "to": to, "label": str(t.get("label") or to)[:40], "who": who, "require": req}
            if str(t.get("when") or "").strip():
                if ck.expr(f"{tw} when", t.get("when"), coll, {"old"}) is not None:
                    tr["when"] = str(t["when"])
            ap = t.get("approval")
            if isinstance(ap, dict) and ap:
                steps = [s for s in (ap.get("steps") or [{"who": "admin"}]) if isinstance(s, dict)][:4] or [{"who": "admin"}]
                st2 = []
                for s in steps:
                    sw = s.get("who") if s.get("who") in ("staff", "admin", "owner") else "admin"
                    st2.append({"who": sw, "label": str(s.get("label") or sw.title())[:40]})
                tr["approval"] = {"steps": st2, "maker_checker": ap.get("maker_checker", True) is not False}
                if str(ap.get("when") or "").strip():            # approval only above an amount etc.
                    if ck.expr(f"{tw} approval when", ap.get("when"), coll) is not None:
                        tr["approval"]["when"] = str(ap["when"])
            trs.append(tr)
        if not trs:
            ck.err(where, "no step (transition)")
            continue
        reach = {initial}                       # every state should be reachable from the start (a warning, not an error)
        for _ in range(len(states)):
            for t in trs:
                if "*" in t["from"] or reach & set(t["from"]):
                    reach.add(t["to"])
        lost = [s for s in states if s not in reach]
        if lost:
            ck.warnings.append(f"{where}: no path leads to {', '.join(lost)}")
        slas = []
        for j, s in enumerate((w.get("sla") or [])[:10]):
            if not isinstance(s, dict):
                continue
            sw = f"{where} SLA {j + 1}"
            st = str(s.get("state") or "").strip()
            hrs = s.get("hours")
            if st not in states or not isinstance(hrs, (int, float)) or not 0 < hrs <= 24 * 90:
                ck.err(sw, "state + hours (1-2160) are needed")
                continue
            mv = str(s.get("move_to") or "").strip()
            if mv and mv not in states:
                ck.err(sw, f"move_to '{mv}' is not a state")
                continue
            nt = s.get("notify") if s.get("notify") in NOTIFY else "admins"
            slas.append({"state": st, "hours": float(hrs), "notify": nt, "move_to": mv,
                         "message": str(s.get("message") or f"In {st} for more than {hrs} hours")[:200]})
        wf_fields.add((coll, field))
        out["workflows"].append({"coll": coll, "field": field, "states": states, "initial": initial, "transitions": trs, "sla": slas})

    # ---- formulas (+ order inside each list; a loop between formulas is refused)
    by_coll: dict[str, dict[str, Any]] = {}
    for i, f in enumerate((raw.get("formulas") or [])[:CAPS["formulas"]]):
        if not isinstance(f, dict):
            continue
        coll, field = slug(f.get("coll")), slug(f.get("field"))
        where = f"formula {coll}.{field}"
        if not ck.has_coll(where, coll):
            continue
        fd = ck.fields(coll).get(field)
        if fd is None:
            ck.err(where, "the field does not exist (add it first)")
            continue
        if (coll, field) in wf_fields or fd.get("type") in ("ref", "photo", "file", "location", "scan"):
            ck.err(where, f"a {fd.get('type')} / workflow field cannot be a formula")
            continue
        if field in by_coll.get(coll, {}):
            ck.err(where, "is written twice")
            continue
        ast = ck.expr(where, f.get("expr"), coll)
        if ast is None:
            continue
        by_coll.setdefault(coll, {})[field] = {"coll": coll, "field": field, "expr": str(f["expr"])[:2000], "_ast": ast}
    for coll, fs in by_coll.items():
        order, seen, stack = [], set(), set()

        def visit(k, path):
            if k in seen:
                return True
            if k in stack:
                ck.err(f"formula {coll}.{k}", "the formulas depend on each other in a loop: " + " -> ".join(path + [k]))
                return False
            stack.add(k)
            for d in sorted(L.names(fs[k]["_ast"]) & set(fs)):
                if d != k and not visit(d, path + [k]):
                    return False
                if d == k:
                    ck.err(f"formula {coll}.{k}", "reads itself")
                    return False
            stack.discard(k)
            seen.add(k)
            order.append(k)
            return True
        for k in list(fs):
            visit(k, [])
        out["formulas"] += [{x: fs[k][x] for x in ("coll", "field", "expr")} for k in order]

    # ---- rules + unique
    for i, r in enumerate((raw.get("rules") or [])[:CAPS["rules"]]):
        if not isinstance(r, dict):
            continue
        coll = slug(r.get("coll"))
        where = f"rule {coll} {i + 1}"
        if not ck.has_coll(where, coll):
            continue
        on = r.get("on") if r.get("on") in ("always", "create", "update") else "always"
        if ck.expr(where, r.get("check"), coll, {"old"} if on != "create" else set()) is None:
            continue
        out["rules"].append({"coll": coll, "check": str(r["check"])[:2000], "on": on,
                             "message": str(r.get("message") or "This entry does not follow the rules.")[:200]})
    for i, u in enumerate((raw.get("unique") or [])[:CAPS["unique"]]):
        if not isinstance(u, dict):
            continue
        coll = slug(u.get("coll"))
        flds = [slug(x) for x in _strs(u.get("fields"))][:4]
        where = f"unique {coll} {i + 1}"
        if not ck.has_coll(where, coll):
            continue
        if not flds or any(x not in ck.fields(coll) for x in flds):
            ck.err(where, "fields must be real fields of the list")
            continue
        out["unique"].append({"coll": coll, "fields": flds,
                              "message": str(u.get("message") or f"This {', '.join(flds)} already exists.")[:200]})

    # ---- triggers + schedules (their actions)
    states_of = {w["coll"]: w for w in out["workflows"]}
    for i, t in enumerate((raw.get("triggers") or [])[:CAPS["triggers"]]):
        if not isinstance(t, dict):
            continue
        coll = slug(t.get("coll"))
        name = str(t.get("name") or f"trigger {i + 1}")[:60]
        where = f"trigger '{name}'"
        if not ck.has_coll(where, coll):
            continue
        on = str(t.get("on") or "create").strip()
        if on.startswith("change:"):
            if slug(on[7:]) not in ck.fields(coll):
                ck.err(where, f"'{on[7:]}' is not a field")
                continue
            on = "change:" + slug(on[7:])
        elif on.startswith("enter:"):
            st = on[6:].strip()
            if coll not in states_of or st not in states_of[coll]["states"]:
                ck.err(where, f"state '{st}' is not in the workflow of '{coll}'")
                continue
            on = "enter:" + st
        elif on not in ("create", "update", "delete"):
            ck.err(where, "on: create | update | delete | change:<field> | enter:<state>")
            continue
        tr = {"name": name, "coll": coll, "on": on}
        if str(t.get("when") or "").strip():
            if ck.expr(f"{where} when", t["when"], coll, {"old"}) is None:
                continue
            tr["when"] = str(t["when"])[:2000]
        acts = _actions(ck, where, coll, t.get("do"), states_of)
        if acts is None:
            continue
        tr["do"] = acts
        out["triggers"].append(tr)
    for i, s in enumerate((raw.get("schedules") or [])[:CAPS["schedules"]]):
        if not isinstance(s, dict):
            continue
        name = slug(s.get("name")) or f"job_{i + 1}"
        where = f"schedule '{name}'"
        every = re.sub(r"\s+", " ", str(s.get("every") or "").strip().lower())
        m = EVERY.match(every)
        if not m:
            ck.err(where, "every: hourly | daily 09:00 | weekly mon 09:00 | monthly 1 09:00")
            continue
        hh = next((int(g) for g in (m.group(2), m.group(5), m.group(8)) if g), 0)
        mm = next((int(g) for g in (m.group(3), m.group(6), m.group(9)) if g), 0)
        if hh > 23 or mm > 59 or (m.group(7) and not 1 <= int(m.group(7)) <= 28):
            ck.err(where, "wrong time (day 1-28, hour 0-23)")
            continue
        coll = slug(s.get("coll"))
        if any(x["name"] == name for x in out["schedules"]):
            ck.err(where, "name used twice")
            continue
        if not ck.has_coll(where, coll):
            continue
        sd = {"name": name, "every": every, "coll": coll, "once_per_row": s.get("once_per_row", True) is not False,
              "label": str(s.get("label") or name)[:60]}
        if str(s.get("where") or "").strip():
            if ck.expr(f"{where} where", s["where"], coll) is None:
                continue
            sd["where"] = str(s["where"])[:2000]
        acts = _actions(ck, where, coll, s.get("do"), states_of)
        if acts is None:
            continue
        sd["do"] = acts
        out["schedules"].append(sd)

    # ---- v0.581 gates: a list read only through a pass list (enrollment / membership) - courses, members-only content
    for i, g in enumerate((raw.get("gates") or [])[:CAPS["gates"]]):
        if not isinstance(g, dict):
            continue
        coll, pk = slug(g.get("coll")), slug(g.get("pass"))
        where = f"gate {coll or i + 1}"
        if not ck.has_coll(where, coll) or not ck.has_coll(where, pk):
            continue
        if coll == pk:
            ck.err(where, "a list cannot be its own pass")
            continue
        via, pf = slug(g.get("via")), slug(g.get("pass_field"))
        if via and (via not in ck.fields(coll) or not pf or pf not in ck.fields(pk)):
            ck.err(where, "via (a field of this list) and pass_field (a field of the pass list) must both be real")
            continue
        match = g.get("match") if isinstance(g.get("match"), dict) else {}
        bad = [k for k in match if slug(k) not in ck.fields(pk)]
        if bad or not match:
            ck.err(where, "match needs real fields of the pass list + values (for example {status: Active})")
            continue
        if any(x["coll"] == coll for x in out["gates"]):
            ck.err(where, "only one gate per list")
            continue
        out["gates"].append({"coll": coll, "pass": pk, "via": via, "pass_field": pf if via else "",
                             "match": {slug(k): str(v)[:60] for k, v in match.items()}})

    # ---- v0.581 subscription_list: her AutoPay plans keep one row per member here (plan + status Active / Ended)
    sl = raw.get("subscription_list")
    if sl:
        coll = slug(sl.get("coll") if isinstance(sl, dict) else sl)
        where = f"subscription_list {coll}"
        if ck.has_coll(where, coll):
            fl = ck.fields(coll)
            st = fl.get("status") or {}
            opts = set(st.get("options") or [])
            if "plan" not in fl or "status" not in fl:
                ck.err(where, "the list needs 'plan' and 'status' fields")
            elif st.get("type") == "choice" and not {"Active", "Ended"} <= opts:
                ck.err(where, "the status options need Active and Ended")
            else:
                out["subscription_list"] = coll

    # ---- v0.581 documents: a PDF made from a row (a certificate on completion), only for whoever may read that row
    for i, d in enumerate((raw.get("documents") or [])[:CAPS["documents"]]):
        if not isinstance(d, dict):
            continue
        coll = slug(d.get("coll"))
        where = f"document {coll or i + 1}"
        if not ck.has_coll(where, coll):
            continue
        lines = [str(x)[:300] for x in (d.get("lines") or []) if str(x).strip()][:12]
        if not lines:
            ck.err(where, "lines are needed (for example 'This certifies that {{student_name}} completed {{course}}')")
            continue
        ok = True
        for ln in lines + [str(d.get("title") or "")]:
            for m in TEMPLATE.finditer(ln):
                if ck.expr(where, m.group(1), coll) is None:
                    ok = False
        if not ok:
            continue
        dd = {"coll": coll, "title": str(d.get("title") or "Certificate")[:80], "lines": lines,
              "signer": str(d.get("signer") or "")[:80]}
        if str(d.get("when") or "").strip():
            if ck.expr(f"{where} when", d["when"], coll) is None:
                continue
            dd["when"] = str(d["when"])[:500]
        if any(x["coll"] == coll for x in out["documents"]):
            ck.err(where, "only one document per list")
            continue
        out["documents"].append(dd)

    for k in ("formulas", "rules", "triggers", "schedules"):     # nothing parsed is kept in the stored spec
        for x in out[k]:
            x.pop("_ast", None)
    n = {k: len(v) for k, v in out.items() if isinstance(v, list) and v}
    return {"spec": out, "errors": ck.errors[:80], "warnings": ck.warnings[:40], "counts": n, "summary": summary(out)}


def _same(a: Any, b: Any) -> bool:
    a, b = L.plain(a), L.plain(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) < 1e-6
    return a == b


def _actions(ck: Checker, where: str, coll: str, raw: Any, states_of: dict[str, Any]) -> list[dict[str, Any]] | None:
    acts: list[dict[str, Any]] = []
    raw = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
    if not raw:
        ck.err(where, "do: at least one action is needed")
        return None
    ok = True
    for j, a in enumerate(raw[:CAPS["actions"]]):
        aw = f"{where} action {j + 1}"
        if not isinstance(a, dict):
            ck.err(aw, "not understood")
            ok = False
            continue
        if "notify" in a:
            to = a.get("notify") if a.get("notify") in NOTIFY else None
            if to is None:
                ck.err(aw, f"notify: {' | '.join(NOTIFY)}")
                ok = False
                continue
            title, body = str(a.get("title") or "").strip()[:80], str(a.get("body") or "").strip()[:300]
            if not title:
                ck.err(aw, "notify needs a title")
                ok = False
                continue
            for part in TEMPLATE.findall(title + " " + body):
                if ck.expr(f"{aw} {{{{{part}}}}}", part, coll, {"old"}) is None:
                    ok = False
            acts.append({"notify": to, "title": title, "body": body})
        elif "set" in a:
            sets = a.get("set") if isinstance(a.get("set"), dict) else {}
            good = {}
            wf = states_of.get(coll)
            for fk, ex in list(sets.items())[:10]:
                fk = slug(fk)
                if fk not in ck.fields(coll):
                    ck.err(aw, f"'{fk}' is not a field")
                    ok = False
                    continue
                if wf and fk == wf["field"]:
                    ck.err(aw, f"'{fk}' is a workflow field - change it with 'move'")
                    ok = False
                    continue
                if ck.expr(f"{aw} {fk}", ex, coll, {"old"}) is None:
                    ok = False
                    continue
                good[fk] = str(ex)[:1000]
            if good:
                acts.append({"set": good})
        elif "move" in a:
            st = str(a.get("move") or "").strip()
            if coll not in states_of or st not in states_of[coll]["states"]:
                ck.err(aw, f"move: '{st}' is not a state of this list's workflow")
                ok = False
                continue
            acts.append({"move": st})
        elif "create" in a:
            tgt = slug(a.get("create"))
            if not ck.has_coll(aw, tgt):
                ok = False
                continue
            vals = a.get("values") if isinstance(a.get("values"), dict) else {}
            good = {}
            for fk, ex in list(vals.items())[:16]:
                fk = slug(fk)
                if fk not in ck.fields(tgt):
                    ck.err(aw, f"'{tgt}' has no field '{fk}'")
                    ok = False
                    continue
                if ck.expr(f"{aw} {fk}", ex, coll, {"old"}) is None:
                    ok = False
                    continue
                good[fk] = str(ex)[:1000]
            acts.append({"create": tgt, "values": good, "owner": "none" if a.get("owner") == "none" else "row_owner"})
        elif "assign" in a:
            acts.append({"assign": "row_owner" if a.get("assign") == "row_owner" else "least_busy"})
        elif "run" in a:
            fn = slug(a.get("run"))
            if fn not in ck.fns:
                ck.err(aw, f"there is no function '{fn}'")
                ok = False
                continue
            args = [str(x)[:500] for x in (a.get("args") or [])][:8] if isinstance(a.get("args"), list) else []
            for x in args:
                if ck.expr(f"{aw} arg", x, coll, {"old"}) is None:
                    ok = False
            acts.append({"run": fn, "args": args})
        else:
            ck.err(aw, "action must be: notify | set | move | create | assign | run")
            ok = False
    if not ok or not acts:
        if ok:
            ck.err(where, "do: no action is left")
        return None
    return acts


def summary(spec: dict[str, Any]) -> list[str]:
    """Plain lines for her card - what this logic will do (no code)."""
    out = []
    for r in spec.get("relations", []):
        out.append(f"Link: every {r['from']} belongs to one {r['to']} ({r['field']}); '{r['label']}' shows inside {r['to']}"
                   + {"cascade": ", deleted together with it", "nullify": ", link cleared on delete",
                      "restrict": ", cannot be deleted while linked"}[r["on_delete"]]
                   + (f"; whoever owns the {r['to']} entry can see it too" if r.get("share") else ""))
    for f in spec.get("formulas", []):
        out.append(f"Formula: {f['coll']}.{f['field']} = {f['expr']}")
    for r in spec.get("rules", []):
        out.append(f"Rule ({r['coll']}): {r['message']}")
    for u in spec.get("unique", []):
        out.append(f"No duplicates ({u['coll']}): {', '.join(u['fields'])}")
    for w in spec.get("workflows", []):
        out.append(f"Workflow ({w['coll']}): {' -> '.join(w['states'])}")
        for t in w["transitions"]:
            if t.get("approval"):
                steps = " then ".join(s["label"] for s in t["approval"]["steps"])
                out.append(f"  Approval for '{t['label']}': {steps}" + (" (the maker cannot approve it)"
                                                                           if t["approval"]["maker_checker"] else ""))
        for s in w["sla"]:
            out.append(f"  SLA: more than {s['hours']:g} hours in {s['state']} -> {s['notify']} are told"
                       + (f", then '{s['move_to']}'" if s["move_to"] else ""))
    for t in spec.get("triggers", []):
        out.append(f"Automatic ({t['coll']}, {t['on']}): {t['name']}")
    for s in spec.get("schedules", []):
        out.append(f"On schedule ({s['every']}): {s['label']}")
    for f in spec.get("functions", []):
        out.append(f"Custom function: {f['label']}({', '.join(f['params'])}) - runs in a sandbox, {len(f['tests'])} tests")
    for g in spec.get("gates", []):                     # v0.581
        m = ", ".join(f"{k} = {v}" for k, v in g["match"].items())
        out.append(f"Lock: '{g['coll']}' only for staff, or a member whose '{g['pass']}' entry has {m}"
                   + (f" and the same {g['via']}" if g["via"] else ""))
    if spec.get("subscription_list"):
        out.append(f"Subscription: when AutoPay starts, the member's entry in '{spec['subscription_list']}' becomes Active; when it stops, Ended")
    for d in spec.get("documents", []):
        out.append(f"PDF: '{d['title']}' for every '{d['coll']}' entry - only someone who can see that entry can download it")
    return out


def decorate_schema(sch: dict[str, Any], spec: dict[str, Any] | None) -> dict[str, Any]:
    """The lists as the apps / forms must see them with this logic: ref fields know their list, formula fields are
    computed (never in a form), a workflow field's options are its states, each parent list names its children."""
    if not spec:
        return sch
    sch = copy.deepcopy(sch)
    colls = {c["key"]: c for c in sch.get("collections") or []}
    for r in spec.get("relations", []):
        c = colls.get(r["from"])
        f = next((x for x in (c or {}).get("fields", []) if x["key"] == r["field"]), None)
        if f is not None:
            f["type"], f["to"] = "ref", r["to"]
        p = colls.get(r["to"])
        if p is not None:
            p.setdefault("relations", []).append({"name": r["name"], "coll": r["from"], "field": r["field"], "label": r["label"]})
    for fm in spec.get("formulas", []):
        f = next((x for x in (colls.get(fm["coll"]) or {}).get("fields", []) if x["key"] == fm["field"]), None)
        if f is not None:
            f["computed"], f["admin_only"], f["required"] = True, True, False
    for w in spec.get("workflows", []):
        f = next((x for x in (colls.get(w["coll"]) or {}).get("fields", []) if x["key"] == w["field"]), None)
        if f is not None:
            f.update({"type": "choice", "options": list(w["states"]), "default": w["initial"], "workflow": True,
                      "admin_only": True, "required": False})
            colls[w["coll"]]["workflow"] = w["field"]
    for c, fk in (spec.get("labels") or {}).items():
        if c in colls:
            colls[c]["label_field"] = fk
    for g in spec.get("gates", []):                     # v0.581 the list is read through its pass list
        c = colls.get(g["coll"])
        if c is not None:
            c["rules"] = {**c.get("rules", {}), "read": "gated"}
            c["gate"] = {k: g[k] for k in ("pass", "via", "pass_field", "match")}
    for d in spec.get("documents", []):
        if d["coll"] in colls:
            colls[d["coll"]]["document"] = d["title"]
    if spec.get("subscription_list"):
        sch["subscription_list"] = spec["subscription_list"]
    sch["approvals"] = any(t.get("approval") for w in spec.get("workflows", []) for t in w["transitions"])
    sch["functions"] = [{"name": f["name"], "label": f["label"], "params": f["params"]}
                        for f in spec.get("functions", []) if f.get("callable")]
    return sch
