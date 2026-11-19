"""v0.827 HOOLA CLOUD (L10 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L10") - the backend of an App Engine app.

Built on what exists: the website-app core (`site/webapp.py`) - members with PBKDF2 passwords, roles member / staff /
admin kept in ITS member table (never a field a user can edit), signed tokens, rows, and a fixed rule vocabulary
checked on EVERY call (create public | member | admin, read public | members | own | admin, update / delete own |
admin). Nothing the model writes is a rule that runs: rules are words from that list.

- TWO DATASETS from day one: `preview` (the Studio preview; sample rows seeded and marked) and `live` (her visitors).
  They are different keys in the core (`ae:<app>:p` / `ae:<app>:l`), so publish never copies a preview row or a
  preview account to live - the wall Lovable removed in March 2026; we keep it.
- THE SCHEMA is data on the server (`<app>/cloud/schema.json`), not app code: restoring old code never touches data.
- MIGRATIONS are additive (add a list / field / choice, hide / show, label, rules, sign-up on / off) and a set of
  changes is ONE run (all or nothing, numbered, logged). Dropping, renaming, changing a type or removing a choice is
  refused and explained as add-copy-hide; only HER tap on an "I accept data loss" card in the Studio can run it.
- THE RULE AUDIT: every list's rules in plain words, with flags; a change that lets anyone on the internet read a list
  holding personal fields (email, phone, name, address...) is refused unless the change says confirm_public - and
  since v0.999.12 (B7) only HER tap can say it (the Studio route / the 'Let anyone read this' card), never the model.
- The app reaches all this ONLY through src/lib/hoola.ts -> its Hoola shell page (which keeps the sign-in) ->
  /api/cloud/<key>/... ; the app's own code never holds a token (it runs in a sealed frame).
Not built yet (said on the page): files, server functions, live updates, payments, AI from the app, phone OTP login."""
from __future__ import annotations

import json
import re
import threading
from datetime import date
from pathlib import Path
from typing import Any

from ..db import now, session
from ..site import webapp as W

DATASETS = ("preview", "live")
TYPES = W.TYPES                      # text long_text number phone email date choice yes_no url
CREATE, READ, WRITE = ("public", "member", "admin"), ("public", "members", "own", "admin"), ("own", "admin")
MAX_LISTS, MAX_FIELDS = W.MAX_COLLECTIONS, W.MAX_FIELDS
PERSONAL = re.compile(r"(name|email|phone|mobile|address|dob|birth|age|gender|aadhaar|pan|city|pincode|pin_code|whatsapp)", re.I)
RESERVED = {"id", "owner", "created", "updated", "mine", "sample"}
SAMPLE_OWNER = "sample"
_LOCK = threading.Lock()
ADDITIVE = ("add_list", "add_field", "add_option", "hide_field", "show_field", "hide_list", "show_list", "label",
            "rules", "signup")
DESTRUCTIVE = {
    "drop_list": "keep it and hide it instead (hide_list): the rows stay, visitors stop seeing the list",
    "drop_field": "hide the field instead (hide_field): the values stay, nobody sees or fills it",
    "rename_list": "add a new list, copy what is needed, hide the old one (add-copy-hide)",
    "rename_field": "add a new field, copy the values, hide the old one (add-copy-hide) - or only change its label",
    "change_type": "add a new field of the new type, copy what converts, hide the old one",
    "remove_option": "keep the choice (old rows use it); add the new choices you need",
}
ERR_EN = [  # the core speaks Hinglish to her website visitors; App Engine apps answer in English
    (r"Pehle login kijiye", "Please sign in first."), (r"Iski ijaazat nahi", "You are not allowed to do that."),
    (r"Email sahi nahi lagta", "That email does not look right."), (r"Password kam se kam 8", "The password needs at least 8 characters."),
    (r"pehle se hai; login", "An account with this email already exists; please sign in."),
    (r"Email ya password galat", "Wrong email or password."), (r"Bahut zyada koshish", "Too many tries; please wait a little."),
    (r"naye account band", "New accounts are closed for this app."), (r"Yeh entry nahi mili", "That entry was not found."),
    (r"Yeh list is website mein nahi", "This app has no such list."), (r"(.+) bharna zaroori hai", r"\1 is required."),
    (r"(.+): number chahiye", r"\1 must be a number."), (r"(.+): 10 ank ka mobile number", r"\1 must be a 10-digit mobile number."),
    (r"(.+): email sahi nahi", r"\1 must be an email address."), (r"(.+): tareekh YYYY-MM-DD", r"\1 must be a date (YYYY-MM-DD)."),
    (r"(.+): https:// se shuru", r"\1 must be a full https:// link."), (r"(.+): in mein se chuniye: (.+)\.", r"\1: choose one of \2."),
    (r"Bahut lamba", "That is too long."), (r"data seema poori", "This app's data limit is reached."),
    (r"2-step login staff", "Two-step sign-in is for staff and admin accounts."),             # v0.999.7 B4
    (r"mobile OTP login abhi chalu nahi", "Phone sign-in is not switched on for this app; sign in with email."),
]


class CloudError(Exception):
    def __init__(self, msg: str, code: int = 400, data: Any = None):
        super().__init__(msg)
        self.code = code
        self.data = data


def english(msg: str) -> str:
    for rx, rep in ERR_EN:
        if re.search(rx, msg):
            return re.sub(rf"^.*?{rx}.*$", rep, msg) if "\\1" in rep else rep
    return msg


# ------------------------------------------------------------------ where things live
def _dir(r) -> Path:
    from . import service as S
    d = S.pdir(r.tenant_id, r.id) / "cloud"
    d.mkdir(parents=True, exist_ok=True)
    return d


def site_key(r, ds: str) -> str:
    """v0.999.7 B4: the dataset's id in the ONE backend - live = the app's App Sahayak project (`app:<id>`), preview = that
    project's preview twin. Before B4 these were `ae:<app>:l` / `ae:<app>:p` (`old_key`); `link` moves them over once."""
    if ds not in DATASETS:
        raise CloudError("dataset is preview or live")
    from ..appmaker import backend as BE
    return BE.bid(data_project(r, ds))


def old_key(r, ds: str) -> str:
    """The pre-B4 id of a dataset (rows still there are moved by `link`; a login made then still works)."""
    return f"ae:{r.id}:{ds[0]}"


# ------------------------------------------------------------------ v0.999.7 B4 ONE BACKEND (docs/research/lovable/03)
# An App Engine app's data used to live in its own corner of the website-app core: no journal, no backups, no logic, no
# phone OTP, no 2FA, no sessions. Now every app has ONE App Sahayak project behind it (status 'engine', hidden from the
# app lists) - the same engine a website's data runs on - and the Studio preview has that project's preview twin. The
# Cloud schema here stays the record of every change (numbered migrations, refusals, her data-loss tap); each run is
# written into the project's lists, so the rules are checked by the same code for websites, phone apps and React apps.
def _link_file(r) -> Path:
    return _dir(r) / "backend.json"


def _pid(r) -> str:
    try:
        return str(json.loads(_link_file(r).read_text()).get("project") or "")
    except (OSError, ValueError):
        return ""


def _load_p(pid: str):
    from ..appmaker.models import AppProject as AP
    if not pid:
        return None
    with session() as s:
        p = s.get(AP, pid)
        if p is not None:
            s.expunge(p)
    return p


def _be_schema(sch: dict[str, Any]) -> dict[str, Any]:
    core = core_schema(sch)
    return {"collections": core["collections"], "signup": core["signup"], "kind": "web", "order": ""}


def link(r):
    """The App Sahayak project holding this app's data - made on first need, idempotent, one at a time per app. Rows and
    members still under the old `ae:` keys move over in the same transaction (same ids, same passwords)."""
    p = _load_p(_pid(r))
    if p is not None:
        return p
    from ..appmaker import backend as BE
    from ..appmaker import locks as LK
    from ..appmaker.models import AppProject as AP
    from ..site import twin as TW
    W.ensure_tables()
    with LK.hold(f"ae-link:{r.id}"):
        p = _load_p(_pid(r))
        if p is not None:
            return p
        sch = schema(r)
        be = {"schema": _be_schema(sch), "made": now().isoformat(), "v": BE.SCHEMA_V, "rev": 1, "changes": [],
              "engine": r.id, "engine_v": int(sch.get("version") or 0)}
        with session() as s:
            p = AP(tenant_id=r.tenant_id, number="", name=r.name or "App", brief=f"App Engine app {r.number}: {r.brief or ''}"[:2000],
                   field="", goal="engine", status="engine", stage="engine", backend=json.dumps(be, ensure_ascii=False))
            s.add(p)
            s.flush()
            s.expunge(p)
        t = TW.make(p, "preview", staff=False)        # the preview keeps its OWN accounts, as it always did

        def keep(b):
            b.setdefault("twins", {})["preview"] = t.id
        BE.patch_backend(p, fn=keep)
        from sqlalchemy import update
        with session() as s:
            for ds, to in (("live", BE.bid(p)), ("preview", BE.bid(t))):
                for model in (W.SiteAppRow, W.SiteAppMember):
                    s.execute(update(model).where(model.site_id == old_key(r, ds)).values(site_id=to)
                              .execution_options(synchronize_session=False))
        _link_file(r).write_text(json.dumps({"project": p.id, "at": now().isoformat()}))
    return _load_p(p.id)


def _synced(r, p):
    """The project's lists = this app's Cloud schema (a run made elsewhere - a branch merge, an older server - is caught
    up here). Returns the project as it is now."""
    from ..appmaker import backend as BE
    sch = schema(r)
    v = int(sch.get("version") or 0)
    be = json.loads(p.backend or "{}") if p is not None else {}
    if int(be.get("engine_v", -1)) == v:
        return p

    def up(b):
        b["schema"] = {**(b.get("schema") or {}), **_be_schema(sch)}
        b["engine_v"] = v
    BE.patch_backend(p, fn=up)
    return _load_p(p.id) or p


def data_project(r, ds: str = "live"):
    """The project a dataset's rows live in: live = the app's project, preview = its preview twin."""
    from ..site import twin as TW
    p = _synced(r, link(r))
    return p if ds == "live" else TW.preview_of(p)


def forget(r) -> None:
    """The app is deleted: its data project, its preview twin and every row / member go with it (old keys too)."""
    from ..appmaker import backend as BE
    from ..appmaker.models import AppProject as AP
    from ..site import twin as TW
    W.ensure_tables()
    p = _load_p(_pid(r))
    ids = [old_key(r, ds) for ds in DATASETS]
    tid = ""
    if p is not None:
        ids.append(BE.bid(p))
        tid = str((json.loads(p.backend or "{}").get("twins") or {}).get("preview") or "")
    with session() as s:
        for k in ids:
            s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id == k).delete(synchronize_session=False)
            s.query(W.SiteAppMember).filter(W.SiteAppMember.site_id == k).delete(synchronize_session=False)
        if p is not None:
            row = s.get(AP, p.id)
            if row is not None:
                s.delete(row)
    if tid:
        TW.drop(tid)


def schema(r) -> dict[str, Any]:
    try:
        return json.loads((_dir(r) / "schema.json").read_text())
    except (OSError, ValueError):
        return {"version": 0, "signup": True, "lists": []}


def _save_schema(r, sch: dict[str, Any]) -> None:
    f = _dir(r) / "schema.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(sch, indent=2, ensure_ascii=False))
    tmp.replace(f)


def migrations(r) -> list[dict[str, Any]]:
    try:
        return json.loads((_dir(r) / "migrations.json").read_text())
    except (OSError, ValueError):
        return []


def core_schema(sch: dict[str, Any]) -> dict[str, Any]:
    """Our schema -> the core's (hidden lists / fields left out: their data stays, nobody reaches it)."""
    cols = []
    for lst in sch.get("lists") or []:
        if lst.get("hidden"):
            continue
        fields = [{k: v for k, v in f.items() if k != "hidden"} for f in lst["fields"] if not f.get("hidden")]
        if fields:
            cols.append({"key": lst["key"], "label": lst["label"], "fields": fields, "rules": dict(lst["rules"])})
    return {"collections": cols, "signup": bool(sch.get("signup", True))}


# ------------------------------------------------------------------ changes (migrations)
def _slug(s: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(s or "").lower()).strip("_")[:30]


def _field(raw: dict[str, Any], where: str) -> dict[str, Any]:
    key = _slug(raw.get("key") or raw.get("label"))
    if not key or key in RESERVED:
        raise CloudError(f"{where}: a field needs a key (not {', '.join(sorted(RESERVED))}).")
    typ = str(raw.get("type") or "text")
    if typ not in TYPES:
        raise CloudError(f"{where}.{key}: type must be one of {', '.join(TYPES)}.")
    f = {"key": key, "label": str(raw.get("label") or key.replace("_", " ").title())[:60], "type": typ,
         "required": bool(raw.get("required")), "admin_only": bool(raw.get("admin_only"))}
    if raw.get("private"):
        f["private"] = True
    if typ == "choice":
        opts = [str(o).strip()[:40] for o in (raw.get("options") or []) if str(o).strip()][:20]
        if not opts:
            raise CloudError(f"{where}.{key}: a choice field needs options.")
        f["options"] = list(dict.fromkeys(opts))
        if raw.get("default") in f["options"]:
            f["default"] = raw["default"]
    return f


def _rules(raw: dict[str, Any] | None, base: dict[str, str] | None = None) -> dict[str, str]:
    r = dict(base or {"create": "member", "read": "own", "update": "admin", "delete": "admin"})
    for k, allowed in (("create", CREATE), ("read", READ), ("update", WRITE), ("delete", WRITE)):
        v = (raw or {}).get(k)
        if v is None:
            continue
        if v not in allowed:
            raise CloudError(f"rules.{k} must be one of {', '.join(allowed)} (got '{v}').")
        r[k] = v
    return r


def _find(sch, key, what="list"):
    lst = next((x for x in sch["lists"] if x["key"] == key), None)
    if lst is None:
        raise CloudError(f"There is no {what} '{key}'.", 404)
    return lst


def _personal(lst: dict[str, Any]) -> list[str]:
    return [f["key"] for f in lst["fields"] if not f.get("hidden") and (f["type"] in ("email", "phone") or PERSONAL.search(f["key"]))]


def apply_changes(r, changes: list[dict[str, Any]], by: str = "hoola", accept_data_loss: bool = False,
                  from_model: bool = False) -> dict[str, Any]:
    """ONE run: every change is checked against a copy; any refusal = nothing changes. Returns the new schema + audit.
    v0.999.12 B7 GATES IN CODE: `from_model` (the chat tool always passes True) = confirm_public is never honoured - a list
    holding personal data opens to the internet only from HER tap on the card in the Studio's Cloud tab (public_run)."""
    if isinstance(changes, dict):
        changes = [changes]
    changes = [c for c in (changes or []) if isinstance(c, dict)][:40]
    if not changes:
        raise CloudError("No changes given.")
    destructive = [c for c in changes if c.get("op") in DESTRUCTIVE]
    if destructive and not accept_data_loss:
        raise CloudError("Not changed - these would lose data and are never done by Hoola alone: " + "; ".join(
            f"{c['op']} ({c.get('list', '')}{'.' + c['field'] if c.get('field') else ''}): {DESTRUCTIVE[c['op']]}" for c in destructive)
            + ". If she really wants it, it waits for her tap on an 'I accept data loss' card in the Studio (Cloud tab).",
            409, {"destructive": destructive})
    with _LOCK:
        old = schema(r)
        sch = json.loads(json.dumps(old))
        notes, seeds = [], []
        for i, c in enumerate(changes, 1):
            op = str(c.get("op") or "")
            where = f"change {i} ({op})"
            if op not in ADDITIVE and op not in DESTRUCTIVE:
                raise CloudError(f"{where}: unknown change. Changes: {', '.join(ADDITIVE)}.")
            if op == "add_list":
                key = _slug(c.get("key") or c.get("label"))
                if not key or key in RESERVED:
                    raise CloudError(f"{where}: the list needs a key.")
                if any(x["key"] == key for x in sch["lists"]):
                    raise CloudError(f"{where}: there is already a list '{key}' (add fields to it instead).")
                if len([x for x in sch["lists"] if not x.get("hidden")]) >= MAX_LISTS:
                    raise CloudError(f"{where}: an app has at most {MAX_LISTS} lists.")
                fields, seen = [], set()
                for fr in (c.get("fields") or [])[:MAX_FIELDS]:
                    f = _field(fr if isinstance(fr, dict) else {}, f"{where} {key}")
                    if f["key"] in seen:
                        raise CloudError(f"{where}: field '{f['key']}' twice.")
                    seen.add(f["key"])
                    fields.append(f)
                if not fields:
                    raise CloudError(f"{where}: a list needs at least one field.")
                lst = {"key": key, "label": str(c.get("label") or key.replace("_", " ").title())[:60], "fields": fields,
                       "rules": _rules(c.get("rules"))}
                sch["lists"].append(lst)
                seeds.append((key, c.get("samples")))
            elif op == "add_field":
                lst = _find(sch, str(c.get("list") or ""))
                f = _field(c, f"{where} {lst['key']}")
                if any(x["key"] == f["key"] for x in lst["fields"]):
                    raise CloudError(f"{where}: '{lst['key']}' already has a field '{f['key']}'.")
                if len([x for x in lst["fields"] if not x.get("hidden")]) >= MAX_FIELDS:
                    raise CloudError(f"{where}: a list has at most {MAX_FIELDS} fields.")
                lst["fields"].append(f)
                if f["required"]:
                    notes.append(f"{lst['key']}.{f['key']} is required for NEW entries; rows made before have it empty.")
            elif op == "add_option":
                lst = _find(sch, str(c.get("list") or ""))
                f = _find({"lists": lst["fields"]}, str(c.get("field") or ""), "field")
                if f["type"] != "choice":
                    raise CloudError(f"{where}: {f['key']} is not a choice field.")
                o = str(c.get("option") or "").strip()[:40]
                if not o:
                    raise CloudError(f"{where}: the option is empty.")
                if o not in f["options"]:
                    f["options"].append(o)
            elif op in ("hide_field", "show_field"):
                lst = _find(sch, str(c.get("list") or ""))
                f = _find({"lists": lst["fields"]}, str(c.get("field") or ""), "field")
                f["hidden"] = op == "hide_field"
                if f["hidden"]:
                    notes.append(f"{lst['key']}.{f['key']} is hidden: its values stay in the rows; show_field brings it back.")
            elif op in ("hide_list", "show_list"):
                lst = _find(sch, str(c.get("list") or ""))
                lst["hidden"] = op == "hide_list"
            elif op == "label":
                lst = _find(sch, str(c.get("list") or ""))
                target = _find({"lists": lst["fields"]}, str(c["field"]), "field") if c.get("field") else lst
                lab = str(c.get("label") or "").strip()[:60]
                if not lab:
                    raise CloudError(f"{where}: the label is empty.")
                target["label"] = lab
            elif op == "rules":
                lst = _find(sch, str(c.get("list") or ""))
                lst["rules"] = _rules(c, lst["rules"])
            elif op == "signup":
                sch["signup"] = bool(c.get("on", True))
            elif op in DESTRUCTIVE:                       # only reached with her accept_data_loss tap
                _destructive(sch, c, where, notes)
        # the plan-time flag: anyone on the internet reading personal fields
        for lst in sch["lists"]:
            if lst["rules"]["read"] != "public":
                lst.pop("public_ack", None)                # no longer public: her earlier yes no longer applies
            if lst.get("hidden") or lst["rules"]["read"] != "public":
                continue
            was = next((x for x in old["lists"] if x["key"] == lst["key"]), None)
            pers = _personal(lst)
            if pers and not (was and was["rules"]["read"] == "public" and set(_personal(was)) >= set(pers)):
                if from_model or not any(c.get("confirm_public") for c in changes):
                    raise CloudError(f"Not changed - '{lst['key']}' would let ANYONE on the internet read {', '.join(pers)} of every "
                                     "entry. Use read: own (each member sees their own) or admin; making it public is only "
                                     "her tap on the card in the Studio's Cloud tab.", 409,
                                     {"flag": "public_personal", "list": lst["key"], "fields": pers})
                lst["public_ack"] = True                    # v0.832 her yes is kept; the publish scan looks for it
        sch["version"] = int(old.get("version") or 0) + 1
        sch["changed_at"] = now().isoformat()
        _save_schema(r, sch)
        log = migrations(r)
        log.append({"n": sch["version"], "at": sch["changed_at"], "by": by, "changes": changes,
                    "destructive": bool(destructive)})
        (_dir(r) / "migrations.json").write_text(json.dumps(log[-200:], ensure_ascii=False))
    write_types(r, sch)
    data_project(r, "live")                            # v0.999.7 B4 the run reaches the one backend's lists at once
    for key, samples in seeds:
        seed(r, key, samples)
    return {"version": sch["version"], "schema": public_view(sch), "audit": audit(sch), "notes": notes,
            "say": f"Hoola Cloud schema version {sch['version']}: {len(changes)} change(s) applied as one run." +
                   (" " + " ".join(notes) if notes else "")}


def _destructive(sch: dict[str, Any], c: dict[str, Any], where: str, notes: list[str]) -> None:
    op = c["op"]
    lst = _find(sch, str(c.get("list") or ""))
    if op == "drop_list":
        sch["lists"] = [x for x in sch["lists"] if x is not lst]
        notes.append(f"list {lst['key']} dropped (rows deleted in both datasets).")
        c["_purge"] = ("list", lst["key"], "")
    elif op == "drop_field":
        f = _find({"lists": lst["fields"]}, str(c.get("field") or ""), "field")
        lst["fields"] = [x for x in lst["fields"] if x is not f]
        c["_purge"] = ("field", lst["key"], f["key"])
        notes.append(f"field {lst['key']}.{f['key']} dropped (its values deleted).")
    elif op == "rename_field":
        f = _find({"lists": lst["fields"]}, str(c.get("field") or ""), "field")
        new = _slug(c.get("to"))
        if not new or new in RESERVED or any(x["key"] == new for x in lst["fields"]):
            raise CloudError(f"{where}: the new key is empty or taken.")
        c["_purge"] = ("rename", lst["key"], f["key"] + ">" + new)
        f["key"] = new
    elif op == "change_type":
        f = _find({"lists": lst["fields"]}, str(c.get("field") or ""), "field")
        t = str(c.get("type") or "")
        if t not in TYPES or t == "choice":
            raise CloudError(f"{where}: a field can change to one of {', '.join(x for x in TYPES if x != 'choice')}.")
        f["type"] = t
        f.pop("options", None)
        notes.append(f"{lst['key']}.{f['key']} is now {t}; old values that do not fit are refused when the row is next saved.")
    elif op == "remove_option":
        f = _find({"lists": lst["fields"]}, str(c.get("field") or ""), "field")
        f["options"] = [o for o in f.get("options") or [] if o != str(c.get("option"))]
        if not f["options"]:
            raise CloudError(f"{where}: a choice needs at least one option.")
    elif op == "rename_list":
        raise CloudError(f"{where}: a list is never renamed in place; add a new list and hide this one.")


def purge(r, changes: list[dict[str, Any]]) -> None:
    """The data side of a destructive run (her tap only): both datasets."""
    from sqlalchemy import select
    for c in changes:
        p = c.get("_purge")
        if not p:
            continue
        kind, lkey, extra = p
        with session() as s:
            for ds in DATASETS:
                q = select(W.SiteAppRow).where(W.SiteAppRow.site_id == site_key(r, ds), W.SiteAppRow.coll == lkey)
                for row in s.scalars(q).all():
                    if kind == "list":
                        s.delete(row)
                        continue
                    d = json.loads(row.data or "{}")
                    if kind == "field":
                        d.pop(extra, None)
                    elif kind == "rename":
                        a, b = extra.split(">")
                        if a in d:
                            d[b] = d.pop(a)
                    row.data = json.dumps(d, ensure_ascii=False)


def destructive_run(r, changes: list[dict[str, Any]], confirm: bool, accept: bool) -> dict[str, Any]:
    """HER tap on the 'I accept data loss' card (the route needs both; the tool never reaches this)."""
    if not (confirm and accept):
        raise CloudError("A change that loses data needs her tap on 'I accept data loss'.", 403)
    out = apply_changes(r, changes, by="her (accepted data loss)", accept_data_loss=True)
    purge(r, changes)
    _clear_pending(r)
    return out


def queue_public(r, changes: list[dict[str, Any]], lkey: str, fields: list[str]) -> dict[str, Any]:
    """v0.999.12 B7 the model asked to open a list with personal data to the internet: the whole change set waits as ONE
    card in the Studio's Cloud tab ('Let anyone read this') - nothing changed until her tap (public_run)."""
    clean = [{k: v for k, v in c.items() if k != "confirm_public"} for c in changes if isinstance(c, dict)][:40]
    card = {"list": str(lkey), "fields": [str(f) for f in fields][:20], "changes": clean, "at": now().isoformat()}
    (_dir(r) / "public.json").write_text(json.dumps(card, ensure_ascii=False))
    return card


def pending_public(r) -> dict[str, Any] | None:
    try:
        d = json.loads((_dir(r) / "public.json").read_text())
        return d if isinstance(d, dict) and d.get("changes") else None
    except (OSError, ValueError):
        return None


def clear_public(r) -> None:
    (_dir(r) / "public.json").unlink(missing_ok=True)


def public_run(r, confirm: bool) -> dict[str, Any]:
    """HER tap on 'Let anyone read this' (the route only; the tool never reaches this): the waiting change set runs with
    her yes, and the list's public_ack records it for the publish scan."""
    if not confirm:
        raise CloudError("Opening a list with personal data to the internet needs her tap on the card.", 403)
    card = pending_public(r)
    if not card:
        raise CloudError("Nothing is waiting for that tap any more.", 409)
    changes = [dict(c) for c in card["changes"]]
    changes[-1]["confirm_public"] = True
    out = apply_changes(r, changes, by="her (let anyone read)")
    clear_public(r)
    return out


def queue_pending(r, changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    f = _dir(r) / "pending.json"
    pend = [c for c in changes if isinstance(c, dict) and c.get("op") in DESTRUCTIVE][:20]
    f.write_text(json.dumps(pend))
    return pend


def pending(r) -> list[dict[str, Any]]:
    try:
        return json.loads((_dir(r) / "pending.json").read_text())
    except (OSError, ValueError):
        return []


def _clear_pending(r) -> None:
    (_dir(r) / "pending.json").unlink(missing_ok=True)


# ------------------------------------------------------------------ the audit
def audit(sch: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    who_read = {"public": "anyone on the internet", "members": "every signed-in member", "own": "each member - only their own",
                "admin": "only you and your staff"}
    who_add = {"public": "anyone, without signing in", "member": "signed-in members", "admin": "only you and your staff"}
    who_chg = {"own": "the member who made it (and you / staff)", "admin": "only you and your staff"}
    for lst in sch.get("lists") or []:
        if lst.get("hidden"):
            continue
        r = lst["rules"]
        pers = _personal(lst)
        flags = []
        if r["read"] == "public" and pers:
            flags.append({"level": "high", "say": f"Anyone on the internet can read {', '.join(pers)} of every entry."})
        elif r["read"] == "public":
            flags.append({"level": "info", "say": "Public on purpose: anyone can read every entry (fine for a menu or notices)."})
        if r["create"] == "public":
            flags.append({"level": "info", "say": "Anyone can add entries without signing in (limited to 30 per 10 minutes per visitor)."})
        if r["read"] == "members" and pers:
            flags.append({"level": "medium", "say": f"Every signed-in member can read everyone's {', '.join(pers)}."})
        out.append({"list": lst["key"], "label": lst["label"],
                    "read": who_read[r["read"]], "add": who_add[r["create"]], "change": who_chg[r["update"]],
                    "delete": who_chg[r["delete"]], "flags": flags})
    return out


def public_view(sch: dict[str, Any]) -> dict[str, Any]:
    return {"version": sch.get("version", 0), "signup": sch.get("signup", True),
            "lists": [{"key": x["key"], "label": x["label"], "hidden": bool(x.get("hidden")), "rules": x["rules"],
                       "fields": [{k: v for k, v in f.items()} for f in x["fields"]]} for x in sch.get("lists") or []]}


# ------------------------------------------------------------------ the typed client file
_TS = {"number": "number", "yes_no": "boolean"}


def types_ts(sch: dict[str, Any]) -> str:
    out = ["// Hoola App Engine - written by Hoola from this app's Hoola Cloud lists (do not edit; it changes with the lists).",
           "export type Lists = {"]
    for lst in sch.get("lists") or []:
        if lst.get("hidden"):
            continue
        out.append(f"  {lst['key']}: {{")
        for f in lst["fields"]:
            if f.get("hidden"):
                continue
            t = " | ".join(json.dumps(o) for o in f["options"]) if f["type"] == "choice" else _TS.get(f["type"], "string")
            out.append(f"    {f['key']}{'' if f['required'] else '?'}: {t};")
        out.append("  };")
    out.append("};")
    return "\n".join(out) + "\n"


def write_types(r, sch: dict[str, Any] | None = None, quiet: bool = False) -> None:
    """src/lib/cloud.types.ts from the lists (locked; a schema change makes the app build again, quiet = inside a build)."""
    from . import service as S
    f = S.src_dir(r) / "src" / "lib" / "cloud.types.ts"
    f.parent.mkdir(parents=True, exist_ok=True)
    txt = types_ts(sch or schema(r))
    if not f.exists() or f.read_text() != txt:
        f.write_text(txt, "utf-8")
        if not quiet:
            S._save(r.id, dirty=True)
            S.schedule_build(r.tenant_id, r.id)


# ------------------------------------------------------------------ sample rows (preview only)
def _sample_value(f: dict[str, Any], i: int) -> Any:
    t = f["type"]
    if t == "number":
        return i * 10
    if t == "yes_no":
        return i % 2 == 0
    if t == "email":
        return f"sample{i}@example.com"
    if t == "phone":
        return f"900000000{i}"
    if t == "date":
        return date.today().isoformat()
    if t == "url":
        return "https://example.com"
    if t == "choice":
        return f["options"][(i - 1) % len(f["options"])]
    if t == "long_text":
        return f"Sample {f['label'].lower()} {i}."
    return f"Sample {f['label'].lower()} {i}"


def seed(r, key: str, samples: Any = None, n: int = 3) -> int:
    """Marked sample rows in the PREVIEW dataset only (owner 'sample'); never live, never copied."""
    sch = core_schema(schema(r))
    try:
        c = W.coll(sch, key)
    except W.AppError:
        return 0
    rows = [s for s in (samples or []) if isinstance(s, dict)][:10] or \
        [{f["key"]: _sample_value(f, i) for f in c["fields"]} for i in range(1, n + 1)]
    made = 0
    for data in rows:
        try:
            clean = W._clean(c, data, W.Who(owner=True))
        except W.AppError:
            continue
        with session() as s:
            s.add(W.SiteAppRow(site_id=site_key(r, "preview"), coll=key, owner=SAMPLE_OWNER, data=json.dumps(clean, ensure_ascii=False)))
        made += 1
    return made


def clear_preview(r) -> int:
    from sqlalchemy import delete as sqldel
    with session() as s:
        res = s.execute(sqldel(W.SiteAppRow).where(W.SiteAppRow.site_id == site_key(r, "preview")))
        s.execute(sqldel(W.SiteAppMember).where(W.SiteAppMember.site_id == site_key(r, "preview")))
    return int(res.rowcount or 0)


# ------------------------------------------------------------------ the app's calls (through its shell)
def key_of(r, ds: str) -> str:
    return ("p-" + r.preview_token) if ds == "preview" else ("l-" + r.slug)


def resolve(key: str):
    """'/api/cloud/<key>/...' -> (app row, dataset). A live key works only while the app is live."""
    from sqlalchemy import select
    from . import models as M
    M.ensure_table()
    W.ensure_tables()
    k = str(key or "")
    with session() as s:
        if k.startswith("p-") and len(k) > 18:
            r = s.scalars(select(M.AppProject).where(M.AppProject.preview_token == k[2:])).first()
            ds = "preview"
        elif k.startswith("l-"):
            r = s.scalars(select(M.AppProject).where(M.AppProject.slug == k[2:])).first()
            ds = "live"
            if r is not None and not r.live_version:
                r = None
        else:
            r = None
        if r is None:
            raise CloudError("not found", 404)
        s.expunge(r)
    return r, ds


def _who(r, ds: str, pp, token: str) -> W.Who:
    """Who is asking, on the one backend. A login she / the member ENDED stops at once; a login made before B4 (signed
    for the old `ae:` key, same member id - moved by `link`) keeps working until it runs out."""
    import hashlib
    import hmac
    import time as _t
    from ..appmaker import backend as BE
    from ..site import security as SEC
    sk = BE.bid(pp)
    if token and not SEC.token_ok(sk, token):
        return W.Who(None)
    w = BE.who(pp, token)
    if w.m is not None or not token:
        return w
    try:
        sid, mid, gen, exp, sig = token.split(".")
    except ValueError:
        return w
    body = f"{sid}.{mid}.{gen}.{exp}"
    if sid != old_key(r, ds) or int(exp) < _t.time() or not hmac.compare_digest(
            sig, hmac.new(W._secret(), body.encode(), hashlib.sha256).hexdigest()[:40]):
        return w
    with session() as s:
        m = s.get(W.SiteAppMember, mid)
        if m is None or m.site_id != sk or str(m.gen) != gen:
            return w
        s.expunge(m)
    return W.Who(m)


def _wrap(fn, *a):
    try:
        return fn(*a)
    except W.AppError as e:
        raise CloudError(english(str(e)), e.code)


AUTH_OPS = ("sessions", "session_end", "signout_all", "2fa_start", "2fa_confirm", "2fa_off", "export", "delete_me")
OPS = ("schema", "signup", "signin", "signout", "me", "otp_start", "otp_verify", "2fa_login", "list", "create", "update",
       "remove", "approvals", "decide", "fn") + AUTH_OPS


def call(key: str, op: str, args: dict[str, Any], token: str = "", ip: str = "", ua: str = "") -> dict[str, Any]:
    """Every op the app may ask for; the rules are checked by the one backend on each one (never trusted from the app)."""
    try:
        return _call(key, op, args, token, ip, ua)
    except W.AppError as e:
        raise CloudError(english(str(e)), e.code)


def _call(key: str, op: str, args: dict[str, Any], token: str, ip: str, ua: str) -> dict[str, Any]:
    from ..appmaker import backend as BE
    from ..appmaker.logic import engine as LE
    from ..site import security as SEC
    r, ds = resolve(key)
    if op not in OPS:
        raise CloudError(f"Unknown request '{op}'.", 400)
    pp = data_project(r, ds)
    sk = BE.bid(pp)
    args = args if isinstance(args, dict) else {}
    ua = str(ua or "")[:300]
    if op == "schema":
        return {"dataset": ds, **W.public_schema(BE.schema(pp)), "security": {"otp": bool(SEC.provider()), "two_factor": True}}
    if op == "signup":
        out = BE.signup(pp, str(args.get("email") or ""), str(args.get("password") or ""), str(args.get("name") or ""), ip)
        mem = W.member_of(sk, out.get("token") or "")
        if mem is not None:
            if args.get("consent") is True:
                SEC.save_consent(sk, mem.id, "signup")
            SEC.record(sk, mem, out["token"], ua, ip, "signup")
        return out
    if op == "signin":
        out = BE.login(pp, str(args.get("email") or ""), str(args.get("password") or ""), ip)
        mem = W.member_of(sk, out.get("token") or "")
        if mem is not None and SEC.needs_2fa(sk, mem.email):        # password right; the authenticator code is step two
            return {"need_2fa": True, "ticket": SEC._ticket(sk, mem)}
        if mem is not None:
            SEC.record(sk, mem, out["token"], ua, ip, "password")
        return out
    if op == "2fa_login":
        return SEC.two_fa_login(sk, str(args.get("ticket") or ""), str(args.get("code") or ""), ua, ip)
    if op == "otp_start":
        return SEC.otp_start(sk, str(args.get("phone") or ""), ip)
    if op == "otp_verify":
        return SEC.otp_verify(sk, BE.schema(pp), str(args.get("phone") or ""), str(args.get("code") or ""),
                              str(args.get("name") or ""), args.get("consent") is True, ua, ip)
    w = _who(r, ds, pp, token)
    if op == "me":
        return {"me": W.view_member(w.m) if w.m else None}
    if op == "signout":
        if w.m:
            SEC.end_all(sk, w.m)
        return {"ok": True}
    if op in AUTH_OPS:
        if not w.m:
            raise CloudError("Please sign in first.", 401)
        if op == "sessions":
            return {"sessions": SEC.sessions(sk, w.m, token)}
        if op == "session_end":
            return SEC.end(sk, w.m, str(args.get("id") or ""))
        if op == "signout_all":
            return SEC.end_all(sk, w.m)
        if op == "2fa_start":
            return SEC.two_fa_start(sk, w.m, r.name or "Hoola")
        if op == "2fa_confirm":
            return SEC.two_fa_confirm(sk, w.m, str(args.get("code") or ""))
        if op == "2fa_off":
            return SEC.two_fa_off(sk, w.m, str(args.get("code") or ""))
        if op == "export":
            return SEC.export(sk, BE.schema(pp), w.m)
        return BE.delete_me(pp, w)
    if op == "approvals":
        if not w.m:
            raise CloudError("Please sign in first.", 401)
        return {"approvals": LE.approvals(pp, w)}
    if op == "decide":
        return LE.decide(pp, str(args.get("id") or ""), str(args.get("decision") or ""), str(args.get("note") or "")[:300], w)
    if op == "fn":
        fa = args.get("args") if isinstance(args.get("args"), list) else []
        return LE.call_public(pp, str(args.get("name") or ""), fa, w)
    lkey = _slug(args.get("list"))
    if op == "list":
        rows = BE.rows(pp, lkey, w, int(args.get("limit") or 200))
        if ds == "preview" and rows:
            from sqlalchemy import select
            with session() as s:
                sample = set(s.scalars(select(W.SiteAppRow.id).where(W.SiteAppRow.site_id == sk, W.SiteAppRow.owner == SAMPLE_OWNER)).all())
            for x in rows:
                if x["id"] in sample:
                    x["sample"] = True
        return {"rows": rows}
    if op == "create":
        return {"row": BE.create(pp, lkey, args.get("data") or {}, w, ip)}
    if op == "update":
        return {"row": BE.update(pp, lkey, str(args.get("id") or ""), args.get("data") or {}, w)}
    return BE.delete(pp, lkey, str(args.get("id") or ""), w)


# ------------------------------------------------------------------ her view (the Studio's Cloud tab)
def overview(r) -> dict[str, Any]:
    sch = schema(r)
    out = {"schema": public_view(sch), "audit": audit(sch), "migrations": migrations(r)[-20:][::-1], "pending": pending(r),
           "pending_public": pending_public(r), "datasets": {}, "not_built": ["files", "server functions", "live updates", "payments", "AI from the app"],
           "backend": _backend_view(r)}
    for ds in DATASETS:
        out["datasets"][ds] = W.counts(site_key(r, ds)) if sch.get("lists") else {"members": 0}
    return out


def _backend_view(r) -> dict[str, Any]:
    """v0.999.7 B4 what the one backend gives this app (said in the Cloud tab)."""
    pid = _pid(r)
    return {"project": pid, "linked": bool(pid),
            "has": ["a journal of every write", "daily backups + restore to a moment", "phone OTP sign-in (needs the SMS "
                    "service)", "authenticator 2FA", "sign-in sessions + sign out everywhere", "approvals + workflows",
                    "the same rule checks as websites and phone apps"]}


def owner_rows(r, ds: str, lkey: str, limit: int = 300) -> list[dict[str, Any]]:
    sch = core_schema(schema(r))
    rows = _wrap(W.rows, site_key(r, ds), sch, _slug(lkey), W.Who(owner=True), limit)
    if ds == "preview":
        from sqlalchemy import select
        with session() as s:
            sample = set(s.scalars(select(W.SiteAppRow.id).where(W.SiteAppRow.site_id == site_key(r, ds), W.SiteAppRow.owner == SAMPLE_OWNER)).all())
        for x in rows:
            x["sample"] = x["id"] in sample
    return rows


def members(r, ds: str) -> list[dict[str, Any]]:
    return W.members(site_key(r, ds))


def set_role(r, ds: str, member_id: str, role: str) -> dict[str, Any]:
    return _wrap(W.set_role, site_key(r, ds), member_id, role)


def prompt_block(r) -> str:
    sch = schema(r)
    if not sch.get("lists"):
        return ("\nHoola Cloud: no lists yet. To save data (sign-in, entries that every visitor shares), first add lists with "
                "app_engine action=cloud_change, then use hoola.db / hoola.auth from src/lib/hoola.ts.")
    lines = []
    for x in audit(sch):
        lst = _find(sch, x["list"])
        flds = ", ".join(f"{f['key']}:{f['type']}{'*' if f['required'] else ''}" for f in lst["fields"] if not f.get("hidden"))
        lines.append(f"- {x['list']} ({flds}) - read: {x['read']}; add: {x['add']}; change: {x['change']}" +
                     "".join(f" [FLAG {fl['level']}: {fl['say']}]" for fl in x["flags"] if fl["level"] != "info"))
    return ("\nHoola Cloud (schema v" + str(sch.get("version")) + ", sign-up " + ("on" if sch.get("signup", True) else "off") +
            "): use `import { hoola } from \"@/lib/hoola\"` - hoola.db.collection(\"<list>\").list() / create(data) / "
            "update(id, data) / remove(id), hoola.auth.signUp / signIn / signOut / me / onChange. The server checks every "
            "rule; never check roles only in the page. Preview data is SAMPLE data, separate from live.\n" + "\n".join(lines))
