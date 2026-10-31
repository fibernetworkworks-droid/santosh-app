"""v0.314 ASLI APP, Phase 1: every Hoola-made native app gets its OWN backend - accounts, real saved data, roles.

The engine is the v0.305 web-app engine (`site/webapp.py`: typed lists, a fixed rule vocabulary checked by the server on
EVERY call, PBKDF2 passwords, signed tokens, rate limits), kept separate per app under the id ``app:<project id>``. The
installed app talks to ``/api/app-api/<app_key>/...``; the owner sees and runs the same data from her Hoola.

  * Lists come from the app itself: a simple app from its goal (shop -> orders, booking -> bookings, service_request ->
    requests ...), a complex staff app from its blueprint's data model (staff-only lists, a new account waits until she
    makes it staff), a product app gets saved items + feedback. Made once, stored on the project (`AppProject.backend`).
  * An order is priced by the SERVER from her own product list (the phone sends ids + quantities, never a price), and
    every create carries the phone's own id (`cid`): a retried / replayed write never makes a second row (offline queue).
  * New orders / bookings / requests reach her chat at once (capped per hour), and she changes their status from Hoola.
  * Account deletion inside the app removes the account and its rows (both stores require it).
Never: payments (UPI happens in the customer's own UPI app), card / PIN / OTP fields, other people's rows."""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import Any

from sqlalchemy import select

from ..db import now, session
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger("santosh.appmaker.backend")
STATS = {"schemas": 0, "orders": 0, "dedup": 0, "notes": 0, "notes_capped": 0, "deleted_accounts": 0}
CID = re.compile(r"^[A-Za-z0-9_-]{8,48}$")
NOTE_CAP_PER_HOUR = 30
_KEYS: dict[str, tuple[float, str]] = {}           # app_key -> (when, project id)
_NOTES: dict[str, list[float]] = {}
_LOCK = threading.Lock()

STATUS = {
    "orders": ["New", "Accepted", "Packed", "Out for delivery", "Delivered", "Cancelled"],
    "bookings": ["Requested", "Confirmed", "Done", "Cancelled"],
    "requests": ["New", "Assigned", "In progress", "Done", "Cancelled"],
    "enrolments": ["Enquiry", "Enrolled", "Cancelled"],
    "memberships": ["Requested", "Active", "Expired", "Cancelled"],
    "registrations": ["Registered", "Confirmed", "Cancelled"],
    "enquiries": ["New", "Replied", "Closed"],
}
# the lists whose new rows are news for her (a chat note) and what the note calls them
NEWS = {"orders": "order", "bookings": "booking", "requests": "service request", "enrolments": "enrolment",
        "memberships": "membership request", "registrations": "registration", "enquiries": "enquiry"}


def _f(key: str, label: str, typ: str = "text", required: bool = False, admin_only: bool = False, options=None,
       default: str = "") -> dict[str, Any]:
    d: dict[str, Any] = {"key": key, "label": label, "type": typ, "required": required, "admin_only": admin_only}
    if options:
        d["options"] = list(options)
        if default:
            d["default"] = default
    return d


def _status(coll: str) -> dict[str, Any]:
    return _f("status", "Status", "choice", admin_only=True, options=STATUS[coll], default=STATUS[coll][0])


def _who_fields() -> list[dict[str, Any]]:
    return [_f("name", "Name", required=True), _f("phone", "Mobile number", "phone", required=True)]


CUSTOMER = {"create": "member", "read": "own", "update": "admin", "delete": "admin"}


def _orders() -> dict[str, Any]:
    return {"key": "orders", "label": "Orders", "rules": dict(CUSTOMER), "fields": [
        _f("items", "Items", "long_text", admin_only=True), _f("total", "Total (Rs)", "number", admin_only=True),
        *_who_fields(), _f("address", "Delivery address", "long_text"), _f("note", "Note", "long_text"),
        _f("pay", "Payment", "choice", options=["Cash on delivery", "UPI"], default="Cash on delivery"), _status("orders")]}


GOAL_LISTS: dict[str, list[dict[str, Any]]] = {
    "shop": [_orders()],
    "food_order": [_orders()],
    "khata": [_orders()],
    "booking": [{"key": "bookings", "label": "Bookings", "rules": dict(CUSTOMER), "fields": [
        _f("service", "Service", required=True), _f("date", "Date", "date", required=True), _f("time", "Time"),
        *_who_fields(), _f("note", "Note", "long_text"), _status("bookings")]}],
    "service_request": [{"key": "requests", "label": "Service requests", "rules": dict(CUSTOMER), "fields": [
        _f("service", "Service", required=True), _f("problem", "What is the problem", "long_text", required=True),
        _f("address", "Address", "long_text"), _f("date", "Preferred date", "date"), *_who_fields(), _status("requests")]}],
    "learning": [{"key": "enrolments", "label": "Enrolments", "rules": dict(CUSTOMER), "fields": [
        _f("course", "Course / batch", required=True), _f("student", "Student name", required=True),
        _f("phone", "Mobile number", "phone", required=True), _f("note", "Note", "long_text"), _status("enrolments")]}],
    "membership": [{"key": "memberships", "label": "Memberships", "rules": dict(CUSTOMER), "fields": [
        _f("plan", "Plan", required=True), _f("start", "Start date", "date"), *_who_fields(), _status("memberships")]}],
    "events": [{"key": "registrations", "label": "Registrations", "rules": dict(CUSTOMER), "fields": [
        _f("event", "Event", required=True), _f("people", "People", "number"), *_who_fields(), _status("registrations")]}],
    "catalogue": [{"key": "enquiries", "label": "Enquiries", "rules": {**CUSTOMER, "create": "public"}, "fields": [
        _f("item", "Item"), _f("message", "Message", "long_text", required=True), *_who_fields(), _status("enquiries")]}],
    "community": [
        {"key": "posts", "label": "Posts", "rules": {"create": "admin", "read": "public", "update": "admin", "delete": "admin"},
         "fields": [_f("title", "Title", required=True), _f("body", "Text", "long_text", required=True)]},
        {"key": "messages", "label": "Messages", "rules": dict(CUSTOMER), "fields": [
            _f("message", "Message", "long_text", required=True), _f("name", "Name")]}],
}
PRODUCT_LISTS = [
    {"key": "saved", "label": "Saved", "rules": {"create": "member", "read": "own", "update": "own", "delete": "own"},
     "fields": [_f("item", "Item", required=True), _f("note", "Note", "long_text")]},
    {"key": "feedback", "label": "Feedback", "rules": {"create": "member", "read": "own", "update": "admin", "delete": "admin"},
     "fields": [_f("message", "Message", "long_text", required=True),
                _f("rating", "Rating", "choice", options=["1", "2", "3", "4", "5"], default="5")]},
]
STAFF_RULES = {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"}   # 'admin' = staff + admin roles
# blueprint plumbing that never becomes an in-app list (the org chart and permissions live in Hoola; join / line tables
# ride inside their parent; jobs and report definitions are server work)
SKIP_ENT = re.compile(r"(_line|_item|_step|_answer|_dependency|_schedule|_rule|_def|_template)$|^(export_job|delegation|"
                      r"audit_log|telemetry|location_ping|sync_state|attachment)$")
INFRA_MODULES = ("core", "approvals", "reports")
DM_TYPE = {"text": "text", "long": "long_text", "int": "number", "decimal": "number", "money": "number", "bool": "yes_no",
           "date": "date", "datetime": "text", "time": "text", "phone": "phone", "email": "email", "url": "text",
           "enum": "choice", "ref": "text", "uuid": "text"}


def _complex_lists(plan: dict[str, Any], goal: str = "") -> list[dict[str, Any]]:
    from . import archetypes as A
    from . import datamodel as D
    bp = plan.get("blueprint") or {}
    # the archetype's OWN modules in its order (bp["modules"] is sorted and carries the closure: a hospital app must
    # start with its health / pharmacy / roster tables, not the CRM ones every money app pulls in)
    first = [m for m in (A.ARCHETYPES.get(goal) or {}).get("modules", []) if m not in INFRA_MODULES]
    mods = first + [m for m in (bp.get("modules") or []) if m not in INFRA_MODULES and m not in first]
    order = {m: i for i, m in enumerate(mods)}
    sens = set((bp.get("data") or {}).get("sensitive") or [])
    ents = [e for e in D.entities_for(bp.get("modules") or []) if e in D.ENTITIES and D.ENTITIES[e][0] not in INFRA_MODULES
            and e not in sens and not SKIP_ENT.search(e) and "s" not in D.ENTITIES[e][3]]
    ents.sort(key=lambda e: order.get(D.ENTITIES[e][0], 99))
    out = []
    for e in ents:
        fields = []
        for f in D.parse_fields(D.ENTITIES[e][2]):
            t = DM_TYPE.get(f["type"])
            if not t or W._slug(f["name"]) in ("id", "owner", "created", "updated") or \
                    re.search(r"(?i)(password|pin|otp|cvv|card|aadhaar|pan_no|account_no|ifsc|token|secret)", f["name"]):
                continue
            label = f["name"].replace("_", " ").capitalize() + (" (id / name)" if f["type"] == "ref" else "")
            fd = _f(f["name"], label, t, required=f["required"] and t != "choice")
            if t == "choice":
                if not f.get("values"):
                    continue
                fd["options"], fd["default"] = f["values"][:20], f["values"][0]
            fields.append(fd)
        if fields:
            out.append({"key": e, "label": D.ENTITIES[e][1], "rules": dict(STAFF_RULES), "fields": fields[:W.MAX_FIELDS]})
        if len(out) >= W.MAX_COLLECTIONS:
            break
    return out


def schema_for(r: AppProject) -> dict[str, Any]:
    """The lists this app keeps, in the web-app engine's vocabulary (cleaned by it, so only that vocabulary survives)."""
    from . import taxonomy as T
    plan = json.loads(r.plan or "{}")
    bp = plan.get("blueprint") or {}
    if bp.get("complex"):
        lists, kind = _complex_lists(plan, r.goal), "staff"
    elif (T.GOALS.get(r.goal) or {}).get("product"):
        lists, kind = [dict(x) for x in PRODUCT_LISTS], "product"
    else:
        lists, kind = [dict(x) for x in GOAL_LISTS.get(r.goal) or GOAL_LISTS["catalogue"]], "customer"
    sch = W.clean_schema({"collections": lists, "signup": True})
    sch["kind"] = kind
    sch["order"] = "orders" if any(c["key"] == "orders" for c in sch["collections"]) else ""
    return sch


def bid(r: AppProject | str) -> str:
    return "app:" + (r if isinstance(r, str) else r.id)


def _j(s: str | None, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def ensure(r: AppProject) -> dict[str, Any]:
    """The app's backend, made on first need (the Android build makes it before writing a single screen)."""
    W.ensure_tables()
    be = _j(r.backend, {})
    if be.get("schema", {}).get("collections") is not None:
        return be
    be = {"schema": schema_for(r), "made": now().isoformat(), "v": 1}
    with session() as s:
        row = s.get(AppProject, r.id)
        row.backend = json.dumps(be, ensure_ascii=False)
    r.backend = json.dumps(be, ensure_ascii=False)
    STATS["schemas"] += 1
    return be


def schema(r: AppProject) -> dict[str, Any]:
    return ensure(r)["schema"]


# ---------------------------------------------------------------- the installed app's side (public, by app_key)
class NotFound(W.AppError):
    def __init__(self):
        super().__init__("not found", 404)


def by_key(app_key: str) -> AppProject:
    if not app_key or not re.fullmatch(r"ak[0-9a-f]{8,38}", app_key):
        raise NotFound()
    hit = _KEYS.get(app_key)
    with session() as s:
        r = s.get(AppProject, hit[1]) if hit and time.time() - hit[0] < 600 else None
        if r is None:
            r = s.query(AppProject).filter(AppProject.android.like(f'%"app_key": "{app_key}"%')).first()
        if r is None or _j(r.android, {}).get("app_key") != app_key:
            raise NotFound()
        s.expunge(r)
    _KEYS[app_key] = (time.time(), r.id)
    return r


def who(r: AppProject, token: str) -> W.Who:
    return W.Who(W.member_of(bid(r), token) if token else None)


def public_schema(r: AppProject) -> dict[str, Any]:
    sch = schema(r)
    return {**W.public_schema(sch), "kind": sch.get("kind", ""), "order": sch.get("order", "")}


def signup(r: AppProject, email: str, password: str, name: str, ip: str) -> dict[str, Any]:
    return W.signup(bid(r), schema(r), email, password, name, ip)


def login(r: AppProject, email: str, password: str, ip: str) -> dict[str, Any]:
    schema(r)
    return W.login(bid(r), email, password, ip)


def _products(r: AppProject) -> dict[str, dict[str, Any]]:
    from .android import service as AN
    key = _j(r.android, {}).get("app_key") or ""
    try:
        lists = AN.content(key)["lists"] if key else {}
    except Exception:                                     # noqa: BLE001
        lists = {}
    return {str(p.get("id")): p for p in (lists.get("products") or []) if isinstance(p, dict) and p.get("id")}


def _priced(r: AppProject, cart: Any) -> tuple[str, float]:
    """The cart the phone sent ([{id, qty}]) -> the items line and the total, both from HER product list."""
    prods = _products(r)
    lines, total = [], 0.0
    for it in (cart if isinstance(cart, list) else [])[:80]:
        if not isinstance(it, dict):
            continue
        p = prods.get(str(it.get("id") or ""))
        try:
            q = max(0, min(999, int(it.get("qty") or 0)))
        except (TypeError, ValueError):
            q = 0
        if p is None or q <= 0:
            continue
        price = float(p.get("price") or 0)
        total += price * q
        lines.append(f"{q} x {p.get('name')}" + (f" @ Rs {price:g}" if price else ""))
    if not lines:
        raise W.AppError("Cart khaali hai ya items ab list mein nahi hain.")
    return "\n".join(lines), round(total, 2)


def _find_cid(site: str, coll: str, owner: str, cid: str) -> str:
    with session() as s:
        row = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site, W.SiteAppRow.coll == coll,
                                                   W.SiteAppRow.owner == owner,
                                                   W.SiteAppRow.data.like(f'%"_cid": "{cid}"%'))).first()
        return row.id if row is not None else ""


def _merge(row_id: str, extra: dict[str, Any]) -> None:
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        d = _j(row.data, {})
        d.update(extra)
        row.data = json.dumps(d, ensure_ascii=False)


def _row(site: str, row_id: str) -> W.SiteAppRow:
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        s.expunge(row)
    return row


def create(r: AppProject, coll: str, body: dict[str, Any], w: W.Who, ip: str = "") -> dict[str, Any]:
    """One write from the app. `cid` = the phone's own id for this write: the same cid again returns the first row."""
    sch, site = schema(r), bid(r)
    c = W.coll(sch, coll)
    body = body if isinstance(body, dict) else {}
    cid = str(body.get("cid") or "")
    if cid and not CID.match(cid):
        raise W.AppError("cid galat hai.")
    if cid:
        old = _find_cid(site, coll, w.id, cid)
        if old:
            STATS["dedup"] += 1
            return {**W.row_view(c, _row(site, old), w), "dedup": True}
    extra: dict[str, Any] = {}
    if coll == sch.get("order") and "cart" in body:
        items, total = _priced(r, body.get("cart"))
        extra = {"items": items, "total": total}
    data = {k: v for k, v in body.items() if k not in ("cid", "cart")}
    out = W.create(site, sch, coll, data, w, ip)
    if extra or cid:
        _merge(out["id"], {**extra, **({"_cid": cid} if cid else {})})
        out = W.row_view(c, _row(site, out["id"]), w)
    if extra:
        STATS["orders"] += 1
    if coll in NEWS:
        _news(r, coll, out)
    return out


def rows(r: AppProject, coll: str, w: W.Who, limit: int = 200) -> list[dict[str, Any]]:
    return W.rows(bid(r), schema(r), coll, w, limit)


def update(r: AppProject, coll: str, row_id: str, body: dict[str, Any], w: W.Who) -> dict[str, Any]:
    body = {k: v for k, v in (body if isinstance(body, dict) else {}).items() if k not in ("cid", "cart")}
    return W.update(bid(r), schema(r), coll, row_id, body, w)


def delete(r: AppProject, coll: str, row_id: str, w: W.Who) -> dict[str, Any]:
    return W.delete(bid(r), schema(r), coll, row_id, w)


def delete_me(r: AppProject, w: W.Who) -> dict[str, Any]:
    """In-app account deletion: the account and every row it owns are gone (Play + App Store rule, DPDP right to erase)."""
    if w.m is None:
        raise W.AppError("Pehle login kijiye.", 401)
    site = bid(r)
    with session() as s:
        for row in s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site, W.SiteAppRow.owner == w.m.id)).all():
            s.delete(row)
        m = s.get(W.SiteAppMember, w.m.id)
        if m is not None and m.site_id == site:
            s.delete(m)
    STATS["deleted_accounts"] += 1
    return {"ok": True}


def _news(r: AppProject, coll: str, row: dict[str, Any]) -> None:
    """A new order / booking / request reaches her chat at once (at most NOTE_CAP_PER_HOUR an hour per app)."""
    t = time.time()
    with _LOCK:
        hits = [x for x in _NOTES.get(r.id, []) if t - x < 3600]
        if len(hits) >= NOTE_CAP_PER_HOUR:
            STATS["notes_capped"] += 1
            _NOTES[r.id] = hits
            return
        _NOTES[r.id] = hits + [t]
    what = NEWS[coll]
    who_ = str(row.get("name") or row.get("student") or "").strip()
    bits = [f"Nayi {what} aayi: {r.name or 'aapki app'} ({r.number})"]
    if row.get("items"):
        n = len(str(row["items"]).splitlines())
        bits.append(f"{n} item" + ("s" if n != 1 else "") + (f", Rs {row['total']:g}" if isinstance(row.get("total"), (int, float)) else ""))
    for k in ("service", "course", "plan", "event", "item", "date", "time"):
        if row.get(k):
            bits.append(str(row[k])[:60])
    if who_:
        bits.append(who_[:40])
    text = " · ".join(bits) + ". Status badalna ho to kahiye (jaise 'order accept karo')."
    STATS["notes"] += 1
    try:
        from .android.service import _note
        _note(r, text)
        from .service import _publish
        _publish(r.tenant_id, "app_data", {"app": r.id, "coll": coll, "row": row.get("id")}, r.conv)
    except Exception:
        log.debug("app news", exc_info=True)


# ---------------------------------------------------------------- her side (Hoola login)
def by_key_or_ref(tenant: str, ref: str) -> AppProject:
    """Her app by its number / id / name (the tools' 'app'); the newest app when she named none."""
    from . import service as S
    with session() as s:
        if ref:
            r = S._find(s, tenant, ref)
        else:
            r = s.query(AppProject).filter(AppProject.tenant_id == tenant).order_by(AppProject.updated_at.desc()).first()
            if r is None:
                raise W.AppError("Abhi koi app nahi hai.", 404)
        s.expunge(r)
    return r


def owner_view(r: AppProject) -> dict[str, Any]:
    be = ensure(r)
    sch = be["schema"]
    from ..config import get_settings
    base = (get_settings().public_base_url or "").rstrip("/")
    key = _j(r.android, {}).get("app_key") or ""
    return {"app": r.id, "number": r.number, "name": r.name, "kind": sch.get("kind"), "order": sch.get("order"),
            "collections": sch["collections"], "counts": W.counts(bid(r)), "made": be.get("made"),
            "api": f"{base}/api/app-api/{key}" if key else "", "live": bool(key)}


def owner_rows(r: AppProject, coll: str, limit: int = 300) -> list[dict[str, Any]]:
    return rows(r, coll, W.Who(owner=True), limit)


def owner_update(r: AppProject, coll: str, row_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return update(r, coll, row_id, body, W.Who(owner=True))


def members(r: AppProject) -> list[dict[str, Any]]:
    ensure(r)
    return W.members(bid(r))


def set_role(r: AppProject, member_id: str, role: str) -> dict[str, Any]:
    ensure(r)
    return W.set_role(bid(r), member_id, role)


def seed_hint(r: AppProject) -> dict[str, Any]:
    """What the build puts into the app (assets/seed.json 'backend'): the lists, their fields and rules - no data."""
    sch = schema(r)
    return {"kind": sch.get("kind"), "order": sch.get("order"), "signup": sch.get("signup", True),
            "collections": sch["collections"]}
