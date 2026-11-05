"""v0.382 DIMAAG: the app's brain at run time - every write from her app passes through here.

  create:  refs checked (the parent exists in THIS app and the person may see it) -> workflow starts at its first state ->
           formulas -> rules + unique keys -> saved -> triggers (create, enter:<state>) -> parents' totals recomputed
  update:  a workflow field may only move along an allowed step, by the allowed people, with its required fields and
           condition; a step that needs approval becomes an APPROVAL REQUEST (maker != checker), the row does not move
           until the last approver says yes -> formulas -> rules -> saved -> triggers (update, change:<f>, enter:<s>)
  delete:  children first: restrict (refused while any child exists), cascade (children go too), nullify (links cleared)
  timed:   schedules (hourly / daily / weekly / monthly, IST) and workflow SLAs (a row waiting too long -> notify / move)

Every automatic action is written to the app's audit list. Loops are cut: triggers may cause writes that cause triggers
only 3 levels deep and at most 100 automatic actions per request. A formula that cannot run leaves its field blank (and
is audited) - an order is never lost because of a formula; a rule that says no (or fail("...")) refuses with its message."""
from __future__ import annotations

import contextvars
import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ...db import new_id, now, session
from ...site import webapp as W
from ..models import AppProject
from . import lang as L
from . import spec as SP

log = logging.getLogger(__name__)
STATS = {"writes": 0, "refused": 0, "formula_errors": 0, "triggers": 0, "actions": 0, "approvals": 0, "decided": 0,
         "cascaded": 0, "scheduled": 0, "sla": 0, "rule_errors": 0}
APPROVAL, AUDIT = "_approval", "_audit"
MAX_DEPTH, MAX_ACTIONS, MAX_CASCADE, MAX_CHILDREN = 3, 100, 500, 2000
AUDIT_KEEP = 3000
_depth = contextvars.ContextVar("logic_depth", default=0)
_budget = contextvars.ContextVar("logic_budget", default=None)
_CACHE: dict[str, tuple[str, dict[str, Any]]] = {}
_LOCK = threading.RLock()


# ---------------------------------------------------------------- the compiled logic of one app
def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def spec_of(r: AppProject) -> dict[str, Any] | None:
    be = _j(r.backend, {})
    lg = be.get("logic")
    if not isinstance(lg, dict) or lg.get("on") is False:
        return None
    return lg.get("spec") if isinstance(lg.get("spec"), dict) else None


def compiled(r: AppProject) -> dict[str, Any] | None:
    sp = spec_of(r)
    if not sp:
        return None
    lg = _j(r.backend, {}).get("logic") or {}
    key = f"rev{lg['rev']}" if lg.get("rev") else json.dumps(sp, sort_keys=True, ensure_ascii=False)
    hit = _CACHE.get(r.id)
    if hit and hit[0] == key:
        return hit[1]
    c: dict[str, Any] = {"spec": sp, "fns": {}, "formulas": {}, "rules": {}, "unique": {}, "wf": {}, "trig": {},
                         "rel_from": {}, "rel_to": {}, "labels": sp.get("labels") or {}}
    for f in sp.get("functions", []):
        try:
            c["fns"][f["name"]] = (f["params"], L.parse_body(f["body"]))
        except L.LogicError:
            log.warning("logic function %s does not parse", f.get("name"))
    for f in sp.get("formulas", []):
        try:
            c["formulas"].setdefault(f["coll"], []).append((f["field"], L.parse_expr(f["expr"])))
        except L.LogicError:
            pass
    for r_ in sp.get("rules", []):
        try:
            c["rules"].setdefault(r_["coll"], []).append({**r_, "_ast": L.parse_expr(r_["check"])})
        except L.LogicError:
            pass
    for u in sp.get("unique", []):
        c["unique"].setdefault(u["coll"], []).append(u)
    for w in sp.get("workflows", []):
        w2 = dict(w)
        w2["transitions"] = [dict(t, _when=_safe_parse(t.get("when")), _awhen=_safe_parse((t.get("approval") or {}).get("when")))
                             for t in w["transitions"]]
        c["wf"][w["coll"]] = w2
    for t in sp.get("triggers", []):
        c["trig"].setdefault(t["coll"], []).append(dict(t, _when=_safe_parse(t.get("when"))))
    for rel in sp.get("relations", []):
        c["rel_from"].setdefault(rel["from"], []).append(rel)
        c["rel_to"].setdefault(rel["to"], []).append(rel)
    _CACHE[r.id] = (key, c)
    return c


def _safe_parse(src: Any):
    if not str(src or "").strip():
        return None
    try:
        return L.parse_expr(str(src))
    except L.LogicError:
        return None


def site(r: AppProject) -> str:
    return "app:" + r.id


def _schema(r: AppProject) -> dict[str, Any]:
    from .. import backend as BE
    return BE.schema(r)


_SCH: dict[str, tuple[Any, dict[str, Any]]] = {}


def decorated(r: AppProject, be: dict[str, Any]) -> dict[str, Any]:
    """The app's lists as everyone sees them with its logic on (cached per schema + logic revision)."""
    lg = be.get("logic") if isinstance(be.get("logic"), dict) else {}
    sp = lg.get("spec") if lg.get("on") is not False else None
    if not sp:
        return be["schema"]
    key = (be.get("rev"), be.get("v"), lg.get("rev"), len(json.dumps(be["schema"])))
    hit = _SCH.get(r.id)
    if hit and hit[0] == key:
        return hit[1]
    out = SP.decorate_schema(be["schema"], sp)
    _SCH[r.id] = (key, out)
    return out


# ---------------------------------------------------------------- rows (system access - permission checks are the caller's)
def _row_dict(row: W.SiteAppRow) -> dict[str, Any]:
    d = _j(row.data, {})
    return {**d, "id": row.id, "created": row.created_at.isoformat() if row.created_at else "", "owner_id": row.owner or ""}


def load(r: AppProject, row_id: str, coll: str = "") -> dict[str, Any] | None:
    if not row_id or not isinstance(row_id, str) or len(row_id) > 40:
        return None
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != site(r) or (coll and row.coll != coll) or row.coll.startswith("_"):
            return None
        s.expunge(row)
    return _row_dict(row)


def _raw(r: AppProject, row_id: str) -> W.SiteAppRow | None:
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != site(r):
            return None
        s.expunge(row)
    return row


def children(r: AppProject, rel: dict[str, Any], parent_id: str, cap: int = MAX_CHILDREN) -> list[dict[str, Any]]:
    """v0.390 one indexed lookup (app_refs), never a scan of the whole child list."""
    if not parent_id:
        return []
    from .. import refs as RF
    got = RF.child_rows(site(r), rel["from"], rel["field"], parent_id, cap)
    return [d for d in (_row_dict(x) for x in got) if str(d.get(rel["field"]) or "") == parent_id]


def store(r: AppProject, row_id: str, changes: dict[str, Any]) -> None:
    """A system write into one row's data (no permission check: callers are the engine / an approved step)."""
    if not changes:
        return
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != site(r):
            return
        d = _j(row.data, {})
        d.update(changes)
        row.data, row.updated_at = json.dumps(d, ensure_ascii=False), now()


# ---------------------------------------------------------------- evaluation env
def _who_env(w: W.Who | None) -> dict[str, Any]:
    if w is None:
        return {"id": "", "role": "system", "name": "", "staff": True}
    if w.owner:
        return {"id": "", "role": "owner", "name": "Owner", "staff": True}
    m = w.m
    return {"id": m.id if m else "", "role": m.role if m else "visitor", "name": (m.name if m else "") or "",
            "staff": bool(w.staff)}


def env(r: AppProject, c: dict[str, Any], coll: str, data: dict[str, Any], w: W.Who | None = None,
        old: dict[str, Any] | None = None) -> dict[str, Any]:
    sch = _schema(r)
    fields = {f["key"]: f for f in W.coll(sch, coll)["fields"]} if any(x["key"] == coll for x in sch["collections"]) else {}
    e: dict[str, Any] = {}
    for k, f in fields.items():
        v = data.get(k, "")
        if f.get("type") == "ref" and f.get("to"):
            tgt = f["to"]
            e[k] = L.LazyRow(str(v or ""), lambda rid, tgt=tgt: _with_kids(r, c, tgt, load(r, rid, tgt)))
        else:
            e[k] = v
    for k in ("id", "created", "owner_id"):
        e[k] = data.get(k, "")
    e["me"] = _who_env(w)
    for rel in c["rel_to"].get(coll, []):
        rid = str(data.get("id") or "")
        e[rel["name"]] = _memo(lambda rel=rel, rid=rid: [_with_kids(r, c, rel["from"], x) for x in children(r, rel, rid)])
    if old is not None:
        e["old"] = {k: v for k, v in old.items()}
    return e


def _with_kids(r, c, coll: str, d: dict[str, Any] | None) -> dict[str, Any] | None:
    """A parent / child row as a map, whose own relations (its children) load on first use."""
    if d is None:
        return None
    out = _LazyMap(d)
    for rel in c["rel_to"].get(coll, []):
        out.lazy[rel["name"]] = lambda rel=rel, rid=d.get("id", ""): [_with_kids(r, c, rel["from"], x) for x in children(r, rel, rid)]
    return out


class _LazyMap(dict):
    """A row map whose relation keys are filled on first read (dict lookups only - never Python attributes)."""

    def __init__(self, d):
        super().__init__(d)
        self.lazy = {}

    def get(self, key, default=None):
        if key in self.lazy and not dict.__contains__(self, key):
            self[key] = self.lazy.pop(key)()
        return dict.get(self, key, default)


def _memo(fn):
    box: list = []

    def get():
        if not box:
            box.append(fn())
        return box[0]
    return get


def _fail(msg: str, code: int = 422):
    STATS["refused"] += 1
    raise W.AppError(msg, code)


# ---------------------------------------------------------------- formulas, rules, unique, refs
def compute(r: AppProject, c: dict[str, Any], coll: str, data: dict[str, Any], w: W.Who | None = None) -> dict[str, Any]:
    """Formula fields of one row, in order (a later formula may read an earlier one). Returns only changed values."""
    out: dict[str, Any] = {}
    cur = dict(data)
    for field, ast in c["formulas"].get(coll, []):
        try:
            v = L.evaluate(ast, env(r, c, coll, cur, w), c["fns"])
            if isinstance(v, float):
                v = round(v, 4)
            if isinstance(v, (list, dict)):
                v = L.text(v)[:4000]
        except (L.LogicError, L.Fail) as e:
            STATS["formula_errors"] += 1
            audit(r, "formula_error", coll=coll, row=str(data.get("id") or ""), what=f"{field}: {e}")
            v = ""
        cur[field] = v
        if data.get(field) != v:
            out[field] = v
    return out


def check_rules(r: AppProject, c: dict[str, Any], coll: str, data: dict[str, Any], w: W.Who | None,
                old: dict[str, Any] | None) -> None:
    op = "update" if old is not None else "create"
    for rule in c["rules"].get(coll, []):
        if rule["on"] not in ("always", op):
            continue
        try:
            ok = L.truthy(L.evaluate(rule["_ast"], env(r, c, coll, data, w, old), c["fns"]))
        except L.Fail as e:
            _fail(str(e))
        except L.LogicError as e:                 # a rule that cannot run never bricks her app: audited, let through
            STATS["rule_errors"] += 1
            audit(r, "rule_error", coll=coll, row=str(data.get("id") or ""), what=f"{rule['message']}: {e}")
            continue
        if not ok:
            _fail(rule["message"])
    for u in c["unique"].get(coll, []):
        vals = {f: L.text(data.get(f)).strip().lower() for f in u["fields"]}
        if not all(vals.values()):
            continue
        first = u["fields"][0]
        needle = json.dumps({first: data.get(first)}, ensure_ascii=False)[1:-1]
        with session() as s:
            got = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.coll == coll,
                                                       W.SiteAppRow.data.like(f"%{needle[:200]}%")).limit(500)).all()
            for x in got:
                if x.id == data.get("id"):
                    continue
                d = _j(x.data, {})
                if all(L.text(d.get(f)).strip().lower() == vals[f] for f in u["fields"]):
                    _fail(u["message"], 409)


def check_refs(r: AppProject, coll: str, data: dict[str, Any], w: W.Who, only: set[str] | None = None) -> None:
    sch = _schema(r)
    for f in W.coll(sch, coll)["fields"]:
        if f.get("type") != "ref" or not f.get("to") or (only is not None and f["key"] not in only):
            continue
        v = str(data.get(f["key"]) or "").strip()
        if not v:
            continue
        row = _raw(r, v)
        if row is None or row.coll != f["to"]:
            _fail(f"{f['label']}: yeh entry nahi mili.")
        try:
            tc = W.coll(sch, f["to"])
        except W.AppError:
            _fail(f"{f['label']}: yeh list nahi hai.")
        if not w.owner and not W._can_read(tc, w, row):
            _fail(f"{f['label']}: is entry ko aap nahi chun sakte.", 403)


# ---------------------------------------------------------------- workflow
def _allowed(t: dict[str, Any], w: W.Who, row: dict[str, Any]) -> bool:
    if w is None or w.owner:
        return True
    who = set(t.get("who") or ["staff"])
    role = w.m.role if w.m else ""
    if "admin" in who and role == "admin":
        return True
    if "staff" in who and w.staff:
        return True
    if "member" in who and w.m is not None:
        return True
    if "row_owner" in who and w.id and row.get("owner_id") == w.id:
        return True
    if "assigned" in who and w.id and row.get("_to") == w.id:
        return True
    return False


def actions_for(r: AppProject, c: dict[str, Any], coll: str, row: dict[str, Any], w: W.Who) -> list[dict[str, Any]]:
    wf = c["wf"].get(coll)
    if not wf:
        return []
    cur = str(row.get(wf["field"]) or wf["initial"])
    out, seen = [], set()
    for t in wf["transitions"]:
        if t["to"] == cur or t["to"] in seen or not ("*" in t["from"] or cur in t["from"]) or not _allowed(t, w, row):
            continue
        if t.get("_when") is not None:
            try:
                if not L.truthy(L.evaluate(t["_when"], env(r, c, coll, row, w), c["fns"])):
                    continue
            except (L.LogicError, L.Fail):
                continue
        seen.add(t["to"])
        out.append({"to": t["to"], "label": t["label"], "approval": _needs_approval(r, c, coll, t, row, w)})
    return out


def _needs_approval(r, c, coll: str, t: dict[str, Any], row: dict[str, Any], w) -> bool:
    ap = t.get("approval")
    if not ap:
        return False
    if t.get("_awhen") is not None:
        try:
            return L.truthy(L.evaluate(t["_awhen"], env(r, c, coll, row, w), c["fns"]))
        except (L.LogicError, L.Fail):
            return True                          # cannot tell -> ask (the safe side)
    return True


def _transition(r: AppProject, c: dict[str, Any], coll: str, row: dict[str, Any], to: str, w: W.Who,
                prospective: dict[str, Any]) -> dict[str, Any]:
    wf = c["wf"][coll]
    cur = str(row.get(wf["field"]) or wf["initial"])
    if to not in wf["states"]:
        _fail(f"'{to}' is kaam ki state nahi hai.")
    cands = [t for t in wf["transitions"] if t["to"] == to and ("*" in t["from"] or cur in t["from"])]
    if not cands:
        _fail(f"'{cur}' se seedha '{to}' nahi ja sakte.")
    mine = [t for t in cands if _allowed(t, w, row)]
    if not mine:
        _fail(f"'{to}' karne ki ijaazat aapko nahi hai.", 403)
    for t in mine:
        missing = [k for k in t.get("require") or [] if L.plain(prospective.get(k)) in (None, "")]
        if missing:
            continue
        if t.get("_when") is not None:
            try:
                if not L.truthy(L.evaluate(t["_when"], env(r, c, coll, prospective, w, row), c["fns"])):
                    continue
            except L.Fail as e:
                _fail(str(e))
            except L.LogicError:
                continue
        return t
    t = mine[0]
    missing = [k for k in t.get("require") or [] if L.plain(prospective.get(k)) in (None, "")]
    if missing:
        sch = _schema(r)
        labels = {f["key"]: f["label"] for f in W.coll(sch, coll)["fields"]}
        _fail(f"'{t['label']}' se pehle bhariye: {', '.join(labels.get(k, k) for k in missing)}.")
    _fail(f"Abhi '{t['label']}' ki sharat poori nahi hai.")


# ---------------------------------------------------------------- the hooks backend.py calls
def _strip_computed(c: dict[str, Any], coll: str, body: dict[str, Any]) -> dict[str, Any]:
    comp = {f for f, _ in c["formulas"].get(coll, [])}
    return {k: v for k, v in body.items() if k not in comp}


def before_create(r: AppProject, coll: str, data: dict[str, Any], w: W.Who) -> dict[str, Any]:
    c = compiled(r)
    if not c:
        return data
    data = _strip_computed(c, coll, dict(data))
    wf = c["wf"].get(coll)
    if wf:
        data[wf["field"]] = wf["initial"]           # every new row starts at the first state, whoever sends what
    sch = _schema(r)
    cc = W.coll(sch, coll)
    try:
        clean = W._clean(cc, data, w)
    except W.AppError:
        return data                                  # W.create gives the field message itself
    if wf:
        clean[wf["field"]] = wf["initial"]
    check_refs(r, coll, clean, w)
    pros = {**clean, "id": "", "created": now().isoformat(), "owner_id": w.id}
    pros.update(compute(r, c, coll, pros, w))
    check_rules(r, c, coll, pros, w, None)
    return data


def _share_owner(r: AppProject, c: dict[str, Any], coll: str, row_id: str) -> None:
    """v0.414 relation `share`: a row made under a parent row (attendance / marks under a student) belongs to that parent
    row's person, so a parent reads her own child's rows ('own') while staff still see all. Set once, at create."""
    rels = [x for x in (c.get("spec") or {}).get("relations", []) if x.get("share") and x["from"] == coll]
    if not rels:
        return
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != site(r):
            return
        d = _j(row.data, {})
        for rel in rels:
            pid = str(d.get(rel["field"]) or "")
            par = s.get(W.SiteAppRow, pid) if pid else None
            if par is not None and par.site_id == row.site_id and par.coll == rel["to"] and par.owner:
                row.owner = par.owner
                break


def after_create(r: AppProject, coll: str, row_id: str, w: W.Who) -> None:
    c = compiled(r)
    if not c:
        return
    STATS["writes"] += 1
    _share_owner(r, c, coll, row_id)
    with _guard() as ok:
        d = load(r, row_id, coll) or {}
        ch = compute(r, c, coll, d, w)
        wf = c["wf"].get(coll)
        if wf:
            ch["_wf_at"] = now().isoformat()
            ch[wf["field"]] = wf["initial"]
        store(r, row_id, ch)
        if not ok:
            return
        d.update(ch)
        _fire(r, c, coll, "create", d, None, w)
        if wf:
            _fire(r, c, coll, f"enter:{wf['initial']}", d, None, w)
        _rollup(r, c, coll, d, None)


def before_update(r: AppProject, coll: str, row_id: str, body: dict[str, Any], w: W.Who) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """-> (body for the normal write, info). A workflow step is taken OUT of the body: allowed -> info["move"] (the engine
    writes it, so a customer's own allowed step - Cancel - works although customers never write staff fields); needs
    approval -> info["approval"] (the row does not move until the last approver says yes)."""
    c = compiled(r)
    if not c:
        return body, None
    body = _strip_computed(c, coll, dict(body))
    old = load(r, row_id, coll)
    if old is None:
        return body, None
    sch = _schema(r)
    cc = W.coll(sch, coll)
    wf = c["wf"].get(coll)
    want = str(body.pop(wf["field"])).strip() if wf and wf["field"] in body else None
    if want is not None or body:
        raw = _raw(r, row_id)
        if raw is not None and not w.owner and not W._can_read(cc, w, raw):
            _fail("Yeh entry nahi mili.", 404)
    try:
        part = W._clean(cc, body, w, partial=True)
    except W.AppError:
        return body, None                              # the normal write gives the field's own message
    pros = {**old, **part}
    info: dict[str, Any] = {}
    if want is not None and want != str(old.get(wf["field"]) or wf["initial"]):
        t = _transition(r, c, coll, old, want, w, pros)
        if _needs_approval(r, c, coll, t, pros, w):
            info["approval"] = request_approval(r, c, coll, old, t, w)
        else:
            info["move"] = (wf["field"], want)
            pros[wf["field"]] = want
    check_refs(r, coll, part, w, only=set(part))
    pros.update(compute(r, c, coll, pros, w))
    check_rules(r, c, coll, pros, w, old)
    return body, info or None


def after_update(r: AppProject, coll: str, row_id: str, old: dict[str, Any] | None, w: W.Who | None) -> None:
    c = compiled(r)
    if not c or old is None:
        return
    STATS["writes"] += 1
    with _guard() as ok:
        d = load(r, row_id, coll) or {}
        ch = compute(r, c, coll, d, w)
        wf = c["wf"].get(coll)
        moved = bool(wf and str(d.get(wf["field"]) or "") != str(old.get(wf["field"]) or ""))
        if moved:
            ch["_wf_at"] = now().isoformat()
        store(r, row_id, ch)
        d.update(ch)
        if not ok:
            return
        _fire(r, c, coll, "update", d, old, w)
        for k in sorted(set(d) | set(old)):
            if not k.startswith("_") and k not in ("id", "created", "owner_id") and d.get(k) != old.get(k):
                _fire(r, c, coll, f"change:{k}", d, old, w)
        if moved:
            _fire(r, c, coll, f"enter:{d.get(wf['field'])}", d, old, w)
        _rollup(r, c, coll, d, old)


def before_delete(r: AppProject, coll: str, row_id: str, w: W.Who) -> dict[str, Any] | None:
    c = compiled(r)
    if not c:
        return None
    d = load(r, row_id, coll)
    if d is None:
        return None
    for rel in c["rel_to"].get(coll, []):
        kids = children(r, rel, row_id, cap=MAX_CASCADE + 1)
        if not kids:
            continue
        if rel["on_delete"] == "restrict":
            _fail(f"Iske saath {len(kids)} {rel['label']} jude hain; pehle unhe hataiye.", 409)
        if len(kids) > MAX_CASCADE:
            _fail(f"Iske saath {len(kids)}+ {rel['label']} jude hain - ek baar mein itne nahi hata sakte.", 409)
    return d


def after_delete(r: AppProject, coll: str, row_id: str, d: dict[str, Any] | None, w: W.Who) -> None:
    c = compiled(r)
    if not c or d is None:
        return
    with _guard() as ok:
        for rel in c["rel_to"].get(coll, []):
            for k in children(r, rel, row_id, cap=MAX_CASCADE):
                if rel["on_delete"] == "cascade":
                    kd = before_delete(r, rel["from"], k["id"], None) if _depth.get() < MAX_DEPTH else None
                    _delete_row(r, k["id"])
                    STATS["cascaded"] += 1
                    after_delete(r, rel["from"], k["id"], kd or k, None)
                elif rel["on_delete"] == "nullify":
                    store(r, k["id"], {rel["field"]: ""})
        audit(r, "deleted", coll=coll, row=row_id, by=_by(w))
        if ok:
            _fire(r, c, coll, "delete", d, None, w)
            _rollup(r, c, coll, None, d)


def _delete_row(r: AppProject, row_id: str) -> None:
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is not None and row.site_id == site(r):
            s.delete(row)


def _rollup(r: AppProject, c: dict[str, Any], coll: str, d: dict[str, Any] | None, old: dict[str, Any] | None) -> None:
    """A child changed -> each parent's formulas again (old parent too when the link moved), one level up at a time."""
    if _depth.get() >= MAX_DEPTH + 2:
        return
    for rel in c["rel_from"].get(coll, []):
        ids = {str((d or {}).get(rel["field"]) or ""), str((old or {}).get(rel["field"]) or "")} - {""}
        for pid in ids:
            p = load(r, pid, rel["to"])
            if p is None:
                continue
            ch = compute(r, c, rel["to"], p, None)
            if ch:
                store(r, pid, ch)
                p2 = {**p, **ch}
                tok = _depth.set(_depth.get() + 1)
                try:
                    _fire(r, c, rel["to"], "update", p2, p, None)
                    for k in ch:
                        _fire(r, c, rel["to"], f"change:{k}", p2, p, None)
                    _rollup(r, c, rel["to"], p2, p)
                finally:
                    _depth.reset(tok)


def recompute_all(r: AppProject, cap: int = 5000) -> dict[str, int]:
    """After new logic is applied: every existing row gets its formulas (children first, then parents)."""
    c = compiled(r)
    if not c:
        return {}
    done: dict[str, int] = {}
    order = _coll_order(c)
    for coll in order:
        if coll not in c["formulas"]:
            continue
        with session() as s:
            got = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.coll == coll).limit(cap)).all()
            for x in got:
                s.expunge(x)
        n = 0
        for x in got:
            d = _row_dict(x)
            ch = compute(r, c, coll, d, None)
            if ch:
                store(r, x.id, ch)
                n += 1
        done[coll] = n
    wfs = c["wf"]
    for coll, wf in wfs.items():                     # rows older than the workflow: an unknown state -> the first one
        with session() as s:
            got = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.coll == coll).limit(cap)).all()
            for x in got:
                d = _j(x.data, {})
                if str(d.get(wf["field"]) or "") not in wf["states"] or "_wf_at" not in d:
                    if str(d.get(wf["field"]) or "") not in wf["states"]:
                        d[wf["field"]] = wf["initial"]
                    d.setdefault("_wf_at", (x.updated_at or x.created_at or now()).isoformat())
                    x.data = json.dumps(d, ensure_ascii=False)
    audit(r, "recomputed", what=json.dumps(done))
    return done


def _coll_order(c: dict[str, Any]) -> list[str]:
    """Children before parents (a parent's total reads its children's computed amounts)."""
    colls = set(c["formulas"]) | set(c["rel_from"]) | set(c["rel_to"])
    order, seen = [], set()

    def visit(x, stack=()):
        if x in seen or x in stack:
            return
        for rel in c["rel_to"].get(x, []):
            visit(rel["from"], stack + (x,))
        seen.add(x)
        order.append(x)
    for x in sorted(colls):
        visit(x)
    return order


# ---------------------------------------------------------------- triggers + actions
class _guard:
    """Depth + action budget for one request (a trigger's write may cause triggers, 3 levels at most)."""

    def __enter__(self):
        self.tok = _depth.set(_depth.get() + 1)
        self.btok = _budget.set([MAX_ACTIONS]) if _budget.get() is None else None
        return _depth.get() <= MAX_DEPTH

    def __exit__(self, *a):
        _depth.reset(self.tok)
        if self.btok is not None:
            _budget.reset(self.btok)
        return False


def _spend() -> bool:
    b = _budget.get()
    if b is None:
        return True
    if b[0] <= 0:
        return False
    b[0] -= 1
    return True


def _fire(r: AppProject, c: dict[str, Any], coll: str, on: str, d: dict[str, Any], old: dict[str, Any] | None,
          w: W.Who | None) -> None:
    if _depth.get() > MAX_DEPTH:
        return
    for t in c["trig"].get(coll, []):
        if t["on"] != on:
            continue
        if t.get("_when") is not None:
            try:
                if not L.truthy(L.evaluate(t["_when"], env(r, c, coll, d, w, old), c["fns"])):
                    continue
            except (L.LogicError, L.Fail) as e:
                audit(r, "trigger_error", coll=coll, row=d.get("id", ""), what=f"{t['name']}: {e}")
                continue
        STATS["triggers"] += 1
        run_actions(r, c, coll, d, old, w, t["do"], t["name"])


def run_actions(r: AppProject, c: dict[str, Any], coll: str, d: dict[str, Any], old: dict[str, Any] | None,
                w: W.Who | None, acts: list[dict[str, Any]], why: str) -> list[str]:
    done: list[str] = []
    for a in acts:
        if not _spend():
            audit(r, "budget", coll=coll, row=d.get("id", ""), what=f"{why}: automatic kaam ki seema poori")
            break
        STATS["actions"] += 1
        try:
            done.append(_act(r, c, coll, d, old, w, a, why))
        except (L.LogicError, L.Fail, W.AppError) as e:
            audit(r, "action_error", coll=coll, row=d.get("id", ""), what=f"{why}: {e}")
        except Exception as e:                       # noqa: BLE001 - one broken action never breaks her app's write
            log.exception("logic action failed")
            audit(r, "action_error", coll=coll, row=d.get("id", ""), what=f"{why}: {type(e).__name__}")
    return done


def _tmpl(r, c, coll, d, old, w, s: str) -> str:
    def one(m):
        try:
            return L.text(L.evaluate(m.group(1), env(r, c, coll, d, w, old), c["fns"]))[:200]
        except (L.LogicError, L.Fail):
            return ""
    return SP.TEMPLATE.sub(one, s or "")


def _act(r, c, coll: str, d: dict[str, Any], old, w, a: dict[str, Any], why: str) -> str:
    rid = str(d.get("id") or "")
    if "notify" in a:
        title, body = _tmpl(r, c, coll, d, old, w, a["title"]), _tmpl(r, c, coll, d, old, w, a.get("body", ""))
        notify(r, a["notify"], title, body, d)
        audit(r, "notify", coll=coll, row=rid, what=f"{why}: {a['notify']} <- {title}")
        return f"notify {a['notify']}"
    if "set" in a:
        ch = {}
        for fk, ex in a["set"].items():
            ch[fk] = L.evaluate(ex, env(r, c, coll, d, w, old), c["fns"])
        system_update(r, coll, rid, ch, why)
        return "set " + ", ".join(ch)
    if "move" in a:
        system_move(r, coll, rid, a["move"], why)
        return f"move {a['move']}"
    if "create" in a:
        vals = {fk: L.evaluate(ex, env(r, c, coll, d, w, old), c["fns"]) for fk, ex in a["values"].items()}
        owner = d.get("owner_id", "") if a.get("owner") != "none" else ""
        new = system_create(r, a["create"], vals, owner, why)
        return f"create {a['create']} {new}"
    if "assign" in a:
        from .. import backend as BE
        if a["assign"] == "least_busy":
            staff = BE._staff_of(site(r))
            if not staff:
                return "assign: koi staff nahi"
            load_ = BE._load(r)
            pick = min(staff, key=lambda mid: (load_.get(mid, 0), mid))
            BE.owner_assign(r, coll, rid, pick)
            audit(r, "assign", coll=coll, row=rid, what=f"{why}: {staff[pick].name or 'staff'}")
            return "assign"
        return "assign: skip"
    if "run" in a:
        args = [L.evaluate(x, env(r, c, coll, d, w, old), c["fns"]) for x in a.get("args") or []]
        got = L.call_function(c["fns"], a["run"], args)
        if isinstance(got, dict):
            sch = _schema(r)
            keys = {f["key"] for f in W.coll(sch, coll)["fields"]}
            comp = {f for f, _ in c["formulas"].get(coll, [])}
            wf = c["wf"].get(coll)
            ch = {k: v for k, v in got.items() if k in keys and k not in comp and not (wf and k == wf["field"])}
            if ch:
                system_update(r, coll, rid, ch, why)
        audit(r, "run", coll=coll, row=rid, what=f"{why}: {a['run']}() -> {L.text(got)[:120]}")
        return f"run {a['run']}"
    return "?"


def system_update(r: AppProject, coll: str, row_id: str, changes: dict[str, Any], why: str) -> None:
    """A trigger / approval / schedule changes a row: values cleaned like a staff write, then formulas + triggers."""
    old = load(r, row_id, coll)
    if old is None:
        return
    sch = _schema(r)
    cc = W.coll(sch, coll)
    clean = W._clean(cc, {k: L.text(v) if isinstance(v, (list, dict)) else v for k, v in changes.items()},
                     W.Who(None, owner=True), partial=True)
    if not clean:
        return
    store(r, row_id, clean)
    audit(r, "set", coll=coll, row=row_id, what=f"{why}: " + ", ".join(f"{k}={L.text(v)[:40]}" for k, v in clean.items()))
    after_update(r, coll, row_id, old, None)


def system_move(r: AppProject, coll: str, row_id: str, to: str, why: str, by: str = "") -> None:
    c = compiled(r)
    old = load(r, row_id, coll)
    if c is None or old is None or coll not in c["wf"]:
        return
    wf = c["wf"][coll]
    if to not in wf["states"] or str(old.get(wf["field"]) or "") == to:
        return
    store(r, row_id, {wf["field"]: to, "_ev": now().isoformat()})
    audit(r, "move", coll=coll, row=row_id, by=by, what=f"{why}: {old.get(wf['field'])} -> {to}")
    after_update(r, coll, row_id, old, None)
    _tell_owner_of_row(r, coll, row_id, old, to)
    if wf["field"] == "status":
        from .. import backend as BE
        BE.status_moved(r, row_id, to)                 # a cancelled order gives back its stock / coupon / udhaar


def system_create(r: AppProject, coll: str, vals: dict[str, Any], owner: str, why: str) -> str:
    sch = _schema(r)
    cc = W.coll(sch, coll)
    c = compiled(r)
    data = {k: L.text(v) if isinstance(v, (list, dict)) else v for k, v in vals.items()}
    wf = c["wf"].get(coll) if c else None
    if wf:
        data[wf["field"]] = wf["initial"]
    clean = W._clean(cc, data, W.Who(None, owner=True))
    with session() as s:
        row = W.SiteAppRow(site_id=site(r), coll=coll, owner=owner or "", data=json.dumps(clean, ensure_ascii=False))
        s.add(row)
        s.flush()
        rid = row.id
    audit(r, "create", coll=coll, row=rid, what=why)
    after_create(r, coll, rid, W.Who(None, owner=True))
    return rid


def _tell_owner_of_row(r: AppProject, coll: str, row_id: str, old: dict[str, Any], to: str) -> None:
    owner = old.get("owner_id")
    if not owner:
        return
    try:
        from .. import turant as TU
        sch = _schema(r)
        TU.later(r, [owner], f"{W.coll(sch, coll)['label']}: {to}", label_of(r, coll, old)[:80], row_id)
    except Exception:                               # noqa: BLE001
        log.debug("tell owner", exc_info=True)


def notify(r: AppProject, to: str, title: str, body: str, d: dict[str, Any]) -> None:
    from .. import backend as BE
    ids: list[str] = []
    if to == "owner":
        try:
            from ..android.service import _note
            _note(r, f"{r.name or 'Aapki app'} ({r.number}): {title}" + (f" - {body}" if body else ""))
        except Exception:                           # noqa: BLE001
            log.debug("owner note", exc_info=True)
        return
    if to in ("staff", "admins"):
        staff = BE._staff_of(site(r))
        ids = [m for m, x in staff.items() if to == "staff" or x.role == "admin"]
    elif to == "row_owner" and d.get("owner_id"):
        ids = [d["owner_id"]]
    elif to == "assigned" and d.get("_to"):
        ids = [d["_to"]]
    if ids:
        try:
            from .. import turant as TU
            TU.later(r, ids, title[:80], body[:200], str(d.get("id") or ""))
        except Exception:                           # noqa: BLE001
            log.debug("notify push", exc_info=True)


# ---------------------------------------------------------------- approvals (maker -> checker chain)
def _appr_rows(r: AppProject, status: str = "pending", limit: int = 300) -> list[W.SiteAppRow]:
    with session() as s:
        q = select(W.SiteAppRow).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.coll == APPROVAL)
        if status:
            q = q.where(W.SiteAppRow.data.like(f'%"status": "{status}"%'))
        got = s.scalars(q.order_by(W.SiteAppRow.created_at.desc()).limit(limit)).all()
        for x in got:
            s.expunge(x)
    return got


def pending_for_row(r: AppProject, row_id: str) -> dict[str, Any] | None:
    for x in _appr_rows(r):
        d = _j(x.data, {})
        if d.get("row") == row_id and d.get("status") == "pending":
            return {**d, "id": x.id}
    return None


def request_approval(r: AppProject, c: dict[str, Any], coll: str, row: dict[str, Any], t: dict[str, Any], w: W.Who) -> dict[str, Any]:
    if pending_for_row(r, row["id"]):
        _fail("Is entry ki ek manzoori pehle se ruki hai; uska faisla hone dijiye.", 409)
    wf = c["wf"][coll]
    data = {"coll": coll, "row": row["id"], "field": wf["field"], "from": str(row.get(wf["field"]) or wf["initial"]),
            "to": t["to"], "label": t["label"], "steps": t["approval"]["steps"], "maker_checker": t["approval"]["maker_checker"],
            "at_step": 0, "decisions": [], "status": "pending", "maker": w.id if w else "", "maker_name": _by(w),
            "title": label_of(r, coll, row)[:120], "asked": now().isoformat()}
    with session() as s:
        x = W.SiteAppRow(site_id=site(r), coll=APPROVAL, owner=w.id if w else "", data=json.dumps(data, ensure_ascii=False))
        s.add(x)
        s.flush()
        aid = x.id
    STATS["approvals"] += 1
    audit(r, "approval_asked", coll=coll, row=row["id"], by=_by(w), what=f"{data['from']} -> {t['to']} ({t['label']})")
    _ask_next(r, {**data, "id": aid})
    return {"id": aid, "to": t["to"], "label": t["label"], "step": 1, "of": len(data["steps"]),
            "say": f"'{t['label']}' ke liye manzoori maangi gayi ({data['steps'][0]['label']})."}


def _ask_next(r: AppProject, a: dict[str, Any]) -> None:
    step = a["steps"][a["at_step"]]
    title = f"Manzoori chahiye: {a['label']}"
    body = f"{a['title']} ({a['from']} -> {a['to']})"
    if step["who"] == "owner":
        notify(r, "owner", title, body + " - Hoola mein manzoor / mana kijiye.", {})
    else:
        notify(r, "admins" if step["who"] == "admin" else "staff", title, body, {"id": a["row"]})


def can_decide(a: dict[str, Any], w: W.Who) -> bool:
    if a.get("status") != "pending":
        return False
    if w.owner:
        return True
    step = a["steps"][a["at_step"]]
    if a.get("maker_checker") and w.id and w.id == a.get("maker"):
        return False
    if any(x.get("by_id") == w.id for x in a.get("decisions") or [] if w.id):
        return False                                  # one person = one step
    role = w.m.role if w.m else ""
    return (step["who"] == "staff" and w.staff) or (step["who"] == "admin" and role == "admin")


def approvals(r: AppProject, w: W.Who, everything: bool = False) -> list[dict[str, Any]]:
    out = []
    for x in _appr_rows(r, "" if everything else "pending", 300):
        d = _j(x.data, {})
        mine = bool(w.id) and d.get("maker") == w.id
        dec = can_decide(d, w)
        if not (w.owner or dec or mine or (everything and w.staff)):
            continue
        out.append({"id": x.id, "coll": d["coll"], "row": d["row"], "title": d.get("title", ""), "label": d["label"],
                    "from": d["from"], "to": d["to"], "status": d["status"], "step": d["at_step"] + 1, "of": len(d["steps"]),
                    "waiting_for": d["steps"][d["at_step"]]["label"] if d["status"] == "pending" else "",
                    "maker": d.get("maker_name", ""), "asked": d.get("asked", ""), "can_decide": dec, "mine": mine,
                    "decisions": [{k: v for k, v in z.items() if k != "by_id"} for z in d.get("decisions") or []]})
    return out


def decide(r: AppProject, appr_id: str, decision: str, note: str, w: W.Who) -> dict[str, Any]:
    if decision not in ("approve", "reject"):
        _fail("Faisla: approve ya reject.", 400)
    from .. import locks as LK
    with LK.hold(f"appr:{appr_id}"):                 # v0.390 two approvers in two worker processes: one decides first
        x = _raw(r, appr_id)
        if x is None or x.coll != APPROVAL:
            _fail("Yeh manzoori nahi mili.", 404)
        a = _j(x.data, {})
        if a.get("status") != "pending":
            _fail("Is par faisla ho chuka hai.", 409)
        if not can_decide(a, w):
            if a.get("maker_checker") and w.id and w.id == a.get("maker"):
                _fail("Jisne maanga, woh khud manzoor nahi kar sakta (maker-checker).", 403)
            _fail("Is step ka faisla aapke haath mein nahi.", 403)
        a["decisions"].append({"step": a["at_step"] + 1, "decision": decision, "by": _by(w), "by_id": w.id,
                               "note": str(note or "")[:300], "at": now().isoformat()})
        row = load(r, a["row"], a["coll"])
        if decision == "reject":
            a["status"] = "rejected"
        elif row is None:
            a["status"] = "cancelled"
        elif str(row.get(a["field"]) or "") != a["from"]:
            a["status"] = "cancelled"                  # the row moved meanwhile: this request no longer fits
        elif a["at_step"] + 1 < len(a["steps"]):
            a["at_step"] += 1
        else:
            a["status"] = "approved"
        store(r, appr_id, a)
    STATS["decided"] += 1
    audit(r, f"approval_{decision}", coll=a["coll"], row=a["row"], by=_by(w),
          what=f"{a['label']} step {len(a['decisions'])}: {decision}" + (f" ({note[:80]})" if note else ""))
    if a["status"] == "approved":
        system_move(r, a["coll"], a["row"], a["to"], f"manzoor: {a['label']}", _by(w))
    elif a["status"] == "pending":
        _ask_next(r, a)
    if a["status"] in ("approved", "rejected") and a.get("maker"):
        try:
            from .. import turant as TU
            TU.later(r, [a["maker"]], f"{a['label']}: {'manzoor' if a['status'] == 'approved' else 'mana'}",
                     a.get("title", "")[:80], a["row"])
        except Exception:                           # noqa: BLE001
            log.debug("tell maker", exc_info=True)
    return {"id": appr_id, "status": a["status"], "step": a["at_step"] + 1, "of": len(a["steps"]),
            "say": {"approved": "Manzoor - entry aage badh gayi.", "rejected": "Mana kar diya.",
                    "pending": f"Step manzoor; ab {a['steps'][a['at_step']]['label']} ki baari.",
                    "cancelled": "Entry beech mein badal gayi; yeh manzoori band."}[a["status"]]}


# ---------------------------------------------------------------- what the app sees on each row
def label_of(r: AppProject, coll: str, d: dict[str, Any]) -> str:
    c = compiled(r)
    sch = _schema(r)
    try:
        cc = W.coll(sch, coll)
    except W.AppError:
        return str(d.get("id") or "")
    lf = (c or {}).get("labels", {}).get(coll) or cc.get("label_field")
    if lf and str(d.get(lf) or "").strip():
        return str(d.get(lf))
    for f in cc["fields"]:
        if f["type"] in ("text", "long_text", "phone", "email") and str(d.get(f["key"]) or "").strip() and not f.get("hidden"):
            return str(d.get(f["key"]))[:120]
    return f"{cc['label']} {str(d.get('id') or '')[-5:]}"


def decorate(r: AppProject, coll: str, rows: list[dict[str, Any]], w: W.Who) -> list[dict[str, Any]]:
    """_labels (a ref's name), _actions (the workflow buttons this person may press), _pending (an approval waiting)."""
    c = compiled(r)
    if not c or not rows:
        return rows
    sch = _schema(r)
    try:
        cc = W.coll(sch, coll)
    except W.AppError:
        return rows
    refs = [f for f in cc["fields"] if f.get("type") == "ref" and f.get("to")]
    ids = {str(x.get(f["key"]) or "") for x in rows for f in refs} - {""}
    names: dict[str, str] = {}
    if ids:
        with session() as s:
            got = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.id.in_(list(ids)[:500]))).all()
            for x in got:
                names[x.id] = label_of(r, x.coll, _row_dict(x))
    wf = c["wf"].get(coll)
    pend = {}
    if wf:
        for x in _appr_rows(r):
            d = _j(x.data, {})
            if d.get("coll") == coll:
                pend[d["row"]] = {"id": x.id, **d}
    full: dict[str, dict[str, Any]] = {}
    if wf and rows:
        with session() as s:
            got = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.id.in_([x.get("id") for x in rows if x.get("id")][:1000]))).all()
            full = {x.id: _row_dict(x) for x in got if x.site_id == site(r)}
    for x in rows:
        if refs:
            x["_labels"] = {f["key"]: names.get(str(x.get(f["key"]) or ""), "") for f in refs if x.get(f["key"])}
        if wf:
            d = full.get(x.get("id")) or x
            p = pend.get(x.get("id"))
            x["_actions"] = [] if p else actions_for(r, c, coll, d, w)
            if p:
                x["_pending"] = {"id": p["id"], "to": p["to"], "label": p["label"], "step": p["at_step"] + 1, "of": len(p["steps"]),
                                 "waiting_for": p["steps"][p["at_step"]]["label"], "can_decide": can_decide(p, w)}
    return rows


def related(r: AppProject, coll: str, row_id: str, rel_name: str, w: W.Who) -> dict[str, Any]:
    """The children of one row (lines of an order, students of a class) that this person may read."""
    c = compiled(r)
    rel = next((x for x in (c or {}).get("rel_to", {}).get(coll, []) if x["name"] == rel_name), None)
    if rel is None:
        _fail("Yeh judi list nahi hai.", 404)
    parent = _raw(r, row_id)
    sch = _schema(r)
    pc, kc = W.coll(sch, coll), W.coll(sch, rel["from"])
    if parent is None or parent.coll != coll or not W._can_read(pc, w, parent):
        _fail("Yeh entry nahi mili.", 404)
    from .. import refs as RF                         # v0.390 indexed, not a scan
    got = RF.child_rows(site(r), rel["from"], rel["field"], row_id, MAX_CHILDREN)
    rows = [W.row_view(kc, x, w) for x in got if str(_j(x.data, {}).get(rel["field"]) or "") == row_id and W._can_read(kc, w, x)]
    return {"rel": {"name": rel["name"], "coll": rel["from"], "field": rel["field"], "label": rel["label"]},
            "rows": decorate(r, rel["from"], rows, w)}


def call_public(r: AppProject, name: str, args: list[Any], w: W.Who) -> dict[str, Any]:
    """A function she marked callable (a price calculator, an EMI) from inside her app - pure, no data access."""
    c = compiled(r)
    f = next((x for x in (c or {}).get("spec", {}).get("functions", []) if x["name"] == name and x.get("callable")), None)
    if f is None:
        _fail("Yeh kaam app mein nahi hai.", 404)
    W.rate(f"fn|{site(r)}|{w.id or 'anon'}", 60, 60)
    try:
        return {"result": L.call_function(c["fns"], name, [a for a in (args or [])][:8], steps=20_000)}
    except L.Fail as e:
        _fail(str(e))
    except L.LogicError as e:
        _fail(f"Hisaab nahi ho saka: {e}")


# ---------------------------------------------------------------- audit
def _by(w: W.Who | None) -> str:
    if w is None:
        return "Hoola (apne aap)"
    if w.owner:
        return "Owner"
    return (w.m.name or w.m.email.split("@")[0]) if w.m else "visitor"


def audit(r: AppProject, kind: str, coll: str = "", row: str = "", by: str = "", what: str = "") -> None:
    try:
        d = {"kind": kind, "coll": coll, "row": row, "by": by or "Hoola (apne aap)", "what": str(what)[:400], "at": now().isoformat()}
        with session() as s:
            s.add(W.SiteAppRow(id=new_id("aud"), site_id=site(r), coll=AUDIT, owner="", data=json.dumps(d, ensure_ascii=False)))
    except Exception:                               # noqa: BLE001
        log.debug("audit", exc_info=True)


def audit_list(r: AppProject, limit: int = 100, row: str = "") -> list[dict[str, Any]]:
    with session() as s:
        q = select(W.SiteAppRow).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.coll == AUDIT)
        if row:
            q = q.where(W.SiteAppRow.data.like(f'%"row": "{row}"%'))
        got = s.scalars(q.order_by(W.SiteAppRow.created_at.desc()).limit(max(1, min(limit, 500)))).all()
        return [_j(x.data, {}) for x in got]


def prune_audit(r: AppProject, keep: int = AUDIT_KEEP) -> int:
    with session() as s:
        ids = s.scalars(select(W.SiteAppRow.id).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.coll == AUDIT)
                        .order_by(W.SiteAppRow.created_at.desc()).offset(keep).limit(5000)).all()
        for i in ids:
            x = s.get(W.SiteAppRow, i)
            if x is not None:
                s.delete(x)
    return len(ids)


# ---------------------------------------------------------------- timed: schedules + SLA (the worker calls tick())
DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
_last_tick = 0.0
_pruned: dict[str, float] = {}


def due(every: str, last: str, at: datetime) -> bool:
    """Has the slot for `every` (IST) come since `last` ran?"""
    m = SP.EVERY.match(every)
    if not m:
        return False
    loc = at.astimezone(L.IST)
    if every == "hourly":
        slot = loc.replace(minute=0, second=0, microsecond=0)
    elif m.group(2):
        slot = loc.replace(hour=int(m.group(2)), minute=int(m.group(3)), second=0, microsecond=0)
        if slot > loc:
            slot -= timedelta(days=1)
    elif m.group(4):
        slot = loc.replace(hour=int(m.group(5)), minute=int(m.group(6)), second=0, microsecond=0)
        slot -= timedelta(days=(loc.weekday() - DAYS[m.group(4)]) % 7)
        if slot > loc:
            slot -= timedelta(days=7)
    else:
        slot = loc.replace(day=int(m.group(7)), hour=int(m.group(8)), minute=int(m.group(9)), second=0, microsecond=0)
        if slot > loc:
            mo = slot.month - 1 or 12
            slot = slot.replace(year=slot.year - (1 if slot.month == 1 else 0), month=mo)
    if not last:
        return loc - slot < timedelta(minutes=90)     # a brand-new job waits for its first real slot (no catch-up storm)
    try:
        prev = datetime.fromisoformat(last)
    except ValueError:
        return True
    return prev.astimezone(L.IST) < slot


def run_schedule(r: AppProject, name: str, force: bool = False) -> dict[str, Any]:
    c = compiled(r)
    sd = next((x for x in (c or {}).get("spec", {}).get("schedules", []) if x["name"] == name), None)
    if sd is None:
        _fail("Yeh samay wala kaam nahi mila.", 404)
    where = _safe_parse(sd.get("where"))
    with session() as s:
        got = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.coll == sd["coll"])
                        .order_by(W.SiteAppRow.created_at).limit(5000)).all()
        for x in got:
            s.expunge(x)
    hit, acted = 0, 0
    mark = f"_s_{name}"
    for x in got:
        d = _row_dict(x)
        if sd.get("once_per_row") and d.get(mark):
            continue
        if where is not None:
            try:
                if not L.truthy(L.evaluate(where, env(r, c, sd["coll"], d, None), c["fns"])):
                    continue
            except (L.LogicError, L.Fail):
                continue
        hit += 1
        if acted >= 200:                               # one run does 200 rows; the next slot / tick takes the rest
            break
        acted += 1
        with _guard():
            run_actions(r, c, sd["coll"], d, None, None, sd["do"], f"samay: {sd['label']}")
        if sd.get("once_per_row"):
            store(r, x.id, {mark: now().isoformat()})
    STATS["scheduled"] += 1
    audit(r, "schedule", coll=sd["coll"], what=f"{sd['label']}: {acted} entries" + (" (haath se)" if force else ""))
    return {"name": name, "matched": hit, "acted": acted}


def sla_check(r: AppProject) -> int:
    c = compiled(r)
    if not c:
        return 0
    n = 0
    t_now = datetime.now(timezone.utc)
    for coll, wf in c["wf"].items():
        if not wf.get("sla"):
            continue
        with session() as s:
            got = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.coll == coll).limit(5000)).all()
            for x in got:
                s.expunge(x)
        for x in got:
            d = _row_dict(x)
            st = str(d.get(wf["field"]) or "")
            at = d.get("_wf_at") or d.get("created")
            for sla in wf["sla"]:
                if sla["state"] != st or not at:
                    continue
                key = f"{st}|{at}|{sla['hours']}"
                if key in (d.get("_sla") or []):
                    continue
                try:
                    since = datetime.fromisoformat(str(at))
                except ValueError:
                    continue
                since = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
                if t_now - since < timedelta(hours=sla["hours"]):
                    continue
                store(r, x.id, {"_sla": ((d.get("_sla") or []) + [key])[-10:]})
                notify(r, sla["notify"], f"Der ho rahi hai: {label_of(r, coll, d)[:60]}", sla["message"], d)
                audit(r, "sla", coll=coll, row=x.id, what=sla["message"])
                STATS["sla"] += 1
                n += 1
                if sla.get("move_to"):
                    system_move(r, coll, x.id, sla["move_to"], f"SLA: {sla['message']}")
    return n


def tick(force: bool = False) -> int:
    """Every minute from the worker: due schedules + SLA checks for every app that has them."""
    global _last_tick
    if not force and time.time() - _last_tick < 55:
        return 0
    _last_tick = time.time()
    with session() as s:
        apps = s.scalars(select(AppProject).where(AppProject.backend.like('%"logic"%'))).all()
        for a in apps:
            s.expunge(a)
    ran = 0
    at = datetime.now(timezone.utc)
    for r in apps:
        try:
            c = compiled(r)
            if not c:
                continue
            be = _j(r.backend, {})
            last = ((be.get("logic") or {}).get("ran") or {})
            new_last = dict(last)
            for sd in c["spec"].get("schedules", []):
                if due(sd["every"], str(last.get(sd["name"]) or ""), at):
                    new_last[sd["name"]] = at.isoformat()
                    _save_ran(r, new_last)            # marked BEFORE running: a crash never re-runs the slot twice
                    run_schedule(r, sd["name"])
                    ran += 1
                elif sd["name"] not in last:
                    new_last[sd["name"]] = at.isoformat()
                    _save_ran(r, new_last)
            ran += sla_check(r)
            if time.time() - _pruned.get(r.id, 0) > 3600:
                _pruned[r.id] = time.time()
                prune_audit(r)
        except Exception:                           # noqa: BLE001 - one app's logic never stops the others
            log.exception("logic tick failed for %s", r.id)
    return ran


def _save_ran(r: AppProject, ran: dict[str, str]) -> None:
    from .. import backend as BE

    def put(be):                                     # v0.390 only this key, on the backend as it is NOW
        if isinstance(be.get("logic"), dict):
            be["logic"]["ran"] = ran
    BE.patch_backend(r, fn=put)


# ---------------------------------------------------------------- v0.570 subscriptions -> a pass row the gates can read
SUB_ACTIVE = ("authenticated", "activated", "charged", "resumed")
SUB_ENDED = ("halted", "cancelled", "completed", "paused")


def subscription_event(r: AppProject, member: str, plan_name: str, status: str) -> str:
    """Her AutoPay plan's state, kept as ONE row per member + plan in the declared subscription_list (status Active /
    Ended), owned by the member - so a gate ('lessons only with an Active membership') reads it like any other row.
    Only the gateway's own events reach here (pay._sub_event after the signed webhook); a phone can never write it,
    because the list is created by admin only in a sensible spec and this path is the system's."""
    sp = spec_of(r)
    coll = (sp or {}).get("subscription_list") or ""
    if not coll or not member:
        return ""
    want = "Active" if status in SUB_ACTIVE else ("Ended" if status in SUB_ENDED else "")
    if not want:
        return ""
    from sqlalchemy import select as _sel
    with session() as s:
        rows = s.scalars(_sel(W.SiteAppRow).where(W.SiteAppRow.site_id == site(r), W.SiteAppRow.coll == coll,
                                                  W.SiteAppRow.owner == member)).all()
        hit = next((x.id for x in rows if str(_j(x.data, {}).get("plan") or "") == plan_name), "")
    if hit:
        cur = load(r, hit, coll) or {}
        if str(cur.get("status") or "") != want:
            system_update(r, coll, hit, {"status": want}, f"subscription {status}")
        return hit
    if want != "Active":
        return ""
    return system_create(r, coll, {"plan": plan_name, "status": "Active"}, member, f"subscription {status}")


# ---------------------------------------------------------------- v0.570 a document (certificate) made from a row
def document_pdf(r: AppProject, coll: str, row_id: str, w: W.Who) -> tuple[bytes, str]:
    """The row's PDF, only for someone who may read that row now, and only when its `when` holds (a certificate only
    for a passed attempt). Every value comes from the row through the checked template - nothing typed by a model."""
    sp = spec_of(r)
    d = next((x for x in (sp or {}).get("documents", []) if x["coll"] == coll), None)
    if d is None:
        raise W.AppError("Is list ka koi document nahi.", 404)
    raw = _raw(r, row_id)
    sch = _schema(r)
    cc = W.coll(sch, coll)
    if raw is None or raw.coll != coll or not (w.owner or W._can_read(cc, w, raw)):
        raise W.AppError("not found", 404)
    c = compiled(r)
    row = load(r, row_id, coll) or {}
    if d.get("when"):
        try:
            ok = L.evaluate(d["when"], env(r, c, coll, row, w, None), c["fns"])
        except (L.LogicError, L.Fail):
            ok = False
        if not ok:
            raise W.AppError("Yeh document abhi nahi ban sakta (shart poori nahi).", 409)
    title = _tmpl(r, c, coll, row, None, w, d["title"])
    lines = [_tmpl(r, c, coll, row, None, w, x) for x in d["lines"]]
    return _pdf(r, title, lines, d.get("signer") or "", row_id), title


def _pdf(r: AppProject, title: str, lines: list[str], signer: str, row_id: str) -> bytes:
    import io
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    w, h = landscape(A4)
    cv = canvas.Canvas(buf, pagesize=(w, h))
    cv.setTitle(title[:120])
    cv.setLineWidth(3)
    cv.rect(12 * mm, 12 * mm, w - 24 * mm, h - 24 * mm)
    cv.setLineWidth(0.8)
    cv.rect(16 * mm, 16 * mm, w - 32 * mm, h - 32 * mm)
    cv.setFont("Helvetica-Bold", 30)
    cv.drawCentredString(w / 2, h - 48 * mm, title[:60])
    cv.setFont("Helvetica", 15)
    y = h - 72 * mm
    for ln in lines:
        for part in _wrap(ln, 90):
            cv.drawCentredString(w / 2, y, part)
            y -= 9 * mm
    cv.setFont("Helvetica", 11)
    cv.drawString(26 * mm, 30 * mm, f"{(r.name or '')[:60]}")
    if signer:
        cv.line(w - 96 * mm, 36 * mm, w - 26 * mm, 36 * mm)
        cv.drawCentredString(w - 61 * mm, 30 * mm, signer[:40])
    cv.setFont("Helvetica", 8)
    cv.drawString(26 * mm, 20 * mm, f"No. {row_id}")
    cv.showPage()
    cv.save()
    return buf.getvalue()


def _wrap(s: str, n: int) -> list[str]:
    out, cur = [], ""
    for word in str(s).split():
        if len(cur) + len(word) + 1 > n and cur:
            out.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    return out + ([cur] if cur else [])
