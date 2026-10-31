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
SCHEMA_V = 2                     # v0.319 photo / location / paid fields
MAX_UPLOAD = 6 * 1024 * 1024     # what the phone may send (it shrinks to ~1600 px first); stored re-encoded, smaller
STATS.update({"uploads": 0, "upload_refused": 0, "paid_claims": 0, "updates": 0})
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


PAID = ["No", "Customer says paid", "Verified"]


def _orders() -> dict[str, Any]:
    return {"key": "orders", "label": "Orders", "rules": dict(CUSTOMER), "fields": [
        _f("items", "Items", "long_text", admin_only=True), _f("total", "Total (Rs)", "number", admin_only=True),
        *_who_fields(), _f("address", "Delivery address", "long_text"), _f("pin", "Delivery location", "location"),
        _f("note", "Note", "long_text"),
        _f("pay", "Payment", "choice", options=["Cash on delivery", "UPI"], default="Cash on delivery"), _status("orders"),
        # v0.319 the customer's word that she paid by UPI + the UPI reference she typed; only the owner marks it Verified
        _f("paid", "Paid?", "choice", admin_only=True, options=PAID, default="No"), _f("utr", "UPI reference", admin_only=True)]}


GOAL_LISTS: dict[str, list[dict[str, Any]]] = {
    "shop": [_orders()],
    "food_order": [_orders()],
    "khata": [_orders()],
    "booking": [{"key": "bookings", "label": "Bookings", "rules": dict(CUSTOMER), "fields": [
        _f("service", "Service", required=True), _f("date", "Date", "date", required=True), _f("time", "Time"),
        *_who_fields(), _f("note", "Note", "long_text"), _status("bookings")]}],
    "service_request": [{"key": "requests", "label": "Service requests", "rules": dict(CUSTOMER), "fields": [
        _f("service", "Service", required=True), _f("problem", "What is the problem", "long_text", required=True),
        _f("photo", "Photo of the problem", "photo"), _f("address", "Address", "long_text"), _f("pin", "Location", "location"),
        _f("date", "Preferred date", "date"), *_who_fields(), _status("requests")]}],
    "learning": [{"key": "enrolments", "label": "Enrolments", "rules": dict(CUSTOMER), "fields": [
        _f("course", "Course / batch", required=True), _f("student", "Student name", required=True),
        _f("phone", "Mobile number", "phone", required=True), _f("note", "Note", "long_text"), _status("enrolments")]}],
    "membership": [{"key": "memberships", "label": "Memberships", "rules": dict(CUSTOMER), "fields": [
        _f("plan", "Plan", required=True), _f("start", "Start date", "date"), *_who_fields(), _status("memberships")]}],
    "events": [{"key": "registrations", "label": "Registrations", "rules": dict(CUSTOMER), "fields": [
        _f("event", "Event", required=True), _f("people", "People", "number"), *_who_fields(), _status("registrations")]}],
    "catalogue": [{"key": "enquiries", "label": "Enquiries", "rules": {**CUSTOMER, "create": "public"}, "fields": [
        _f("item", "Item"), _f("message", "Message", "long_text", required=True), _f("photo", "Photo", "photo"),
        *_who_fields(), _status("enquiries")]}],
    "community": [
        {"key": "posts", "label": "Posts", "rules": {"create": "admin", "read": "public", "update": "admin", "delete": "admin"},
         "fields": [_f("title", "Title", required=True), _f("body", "Text", "long_text", required=True), _f("photo", "Photo", "photo")]},
        {"key": "messages", "label": "Messages", "rules": dict(CUSTOMER), "fields": [
            _f("message", "Message", "long_text", required=True), _f("name", "Name")]}],
}
PRODUCT_LISTS = [
    {"key": "saved", "label": "Saved", "rules": {"create": "member", "read": "own", "update": "own", "delete": "own"},
     "fields": [_f("item", "Item", required=True), _f("note", "Note", "long_text")]},
    {"key": "feedback", "label": "Feedback", "rules": {"create": "member", "read": "own", "update": "admin", "delete": "admin"},
     "fields": [_f("message", "Message", "long_text", required=True),
                _f("rating", "Rating", "choice", options=["1", "2", "3", "4", "5"], default="5"), _f("photo", "Screenshot", "photo")]},
]
STAFF_RULES = {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"}   # 'admin' = staff + admin roles
# blueprint plumbing that never becomes an in-app list (the org chart and permissions live in Hoola; join / line tables
# ride inside their parent; jobs and report definitions are server work)
SKIP_ENT = re.compile(r"(_line|_item|_step|_answer|_dependency|_schedule|_rule|_def|_template)$|^(export_job|delegation|"
                      r"audit_log|telemetry|location_ping|sync_state|attachment)$")
INFRA_MODULES = ("core", "approvals", "reports")
DM_TYPE = {"text": "text", "long": "long_text", "int": "number", "decimal": "number", "money": "number", "bool": "yes_no",
           "date": "date", "datetime": "text", "time": "text", "phone": "phone", "email": "email", "url": "text",
           "enum": "choice", "ref": "text", "uuid": "text", "file": "photo", "point": "location"}
# v0.319 kinds the app backend adds on top of the web-app engine's vocabulary (kept through clean_schema, checked here)
EXTRA_TYPES = ("photo", "location")
LOC = re.compile(r"^\s*(-?\d{1,2}(?:\.\d{1,7})?)\s*,\s*(-?\d{1,3}(?:\.\d{1,7})?)\s*$")
FILE_ID = re.compile(r"^f_[0-9a-f]{16}$")


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
        fields, extra = [], {"photo": 0, "location": 0}
        for f in D.parse_fields(D.ENTITIES[e][2]):
            t = DM_TYPE.get(f["type"])
            if t in extra:                      # at most 2 photos and 1 location per staff list
                extra[t] += 1
                if extra[t] > (2 if t == "photo" else 1):
                    continue
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
    want = {(c["key"], f["key"]): f["type"] for c in lists for f in c["fields"] if f.get("type") in EXTRA_TYPES}
    for c in sch["collections"]:                # clean_schema turned photo / location into text: give them back
        for f in c["fields"]:
            if (c["key"], f["key"]) in want:
                f["type"] = want[(c["key"], f["key"])]
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
    if be.get("schema", {}).get("collections") is not None and int(be.get("v") or 1) >= SCHEMA_V:
        return be
    # v0.319 an older backend is upgraded in place: lists only GAIN fields (photo / location / paid), rows are untouched
    be = {"schema": schema_for(r), "made": be.get("made") or now().isoformat(), "v": SCHEMA_V,
          **({"upgraded": now().isoformat()} if be.get("made") else {})}
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
    _check_extra(r, c, data, w)
    out = W.create(site, sch, coll, data, w, ip)
    if extra or cid:
        _merge(out["id"], {**extra, **({"_cid": cid} if cid else {})})
        out = W.row_view(c, _row(site, out["id"]), w)
    if extra:
        STATS["orders"] += 1
    if coll in NEWS:
        _news(r, coll, out)
    return out


def rows(r: AppProject, coll: str, w: W.Who, limit: int = 200, q: str = "", status: str = "", offset: int = 0) -> list[dict[str, Any]]:
    """v0.319 + search (q, any field) and a status filter, newest first; offset pages through them."""
    got = W.rows(bid(r), schema(r), coll, w, 1000 if (q or status or offset) else limit)
    if status:
        got = [x for x in got if str(x.get("status") or "") == status]
    if q:
        t = q.strip().lower()[:80]
        got = [x for x in got if t in json.dumps(x, ensure_ascii=False).lower()]
    offset = max(0, int(offset or 0))
    return got[offset:offset + max(1, min(int(limit or 200), 1000))]


def update(r: AppProject, coll: str, row_id: str, body: dict[str, Any], w: W.Who) -> dict[str, Any]:
    body = {k: v for k, v in (body if isinstance(body, dict) else {}).items() if k not in ("cid", "cart")}
    sch = schema(r)
    _check_extra(r, W.coll(sch, coll), body, w)
    out = W.update(bid(r), sch, coll, row_id, body, w)
    if any(k in body for k in ("status", "paid")):
        _merge(row_id, {"_ev": now().isoformat()})     # v0.319 the moment her row moved: the app's update check reads it
    return out


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


# ---------------------------------------------------------------- v0.319 photos, location, updates, "I paid"
def _check_extra(r: AppProject, c: dict[str, Any], data: dict[str, Any], w: W.Who) -> None:
    """Photo fields carry a file this app holds and this person may use; location fields are a real "lat,lng"."""
    for f in c["fields"]:
        k, t = f["key"], f.get("type")
        if t not in EXTRA_TYPES or k not in data or data[k] in (None, ""):
            continue
        v = str(data[k]).strip()
        if t == "location":
            m = LOC.match(v)
            if not m or abs(float(m.group(1))) > 90 or abs(float(m.group(2))) > 180:
                raise W.AppError(f"{f['label']}: location sahi nahi (lat,lng).")
            data[k] = f"{float(m.group(1)):.6f},{float(m.group(2)):.6f}"
        else:
            meta = _file_meta(r, v)
            if meta is None or not (w.staff or (w.id and meta.get("owner") == w.id) or (not meta.get("owner") and not w.id)):
                raise W.AppError(f"{f['label']}: yeh photo is account ki nahi.", 403)
            if (c.get("rules") or {}).get("read") == "public" and not meta.get("public"):
                meta["public"] = True
                _files(r).joinpath(v + ".json").write_text(json.dumps(meta))
            data[k] = v


def _files(r: AppProject):
    from . import kit as K
    d = K.app_dir(r.tenant_id, r.id) / "backend" / "files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _file_meta(r: AppProject, fid: str) -> dict[str, Any] | None:
    if not FILE_ID.match(fid or ""):
        return None
    f = _files(r) / (fid + ".json")
    return _j(f.read_text(), None) if f.exists() else None


def upload(r: AppProject, w: W.Who, raw: bytes, ip: str = "") -> dict[str, Any]:
    """A photo from the app: any common image the phone sends, stored as a fresh JPEG (EXIF / GPS dropped by the
    re-encode), at most 1600 px. Needs an account unless the app has a list anybody may write to."""
    import io
    import secrets as _sec
    from PIL import Image, ImageOps
    sch = schema(r)
    if w.m is None and not w.owner and not any((c.get("rules") or {}).get("create") == "public" for c in sch["collections"]):
        raise W.AppError("Pehle login kijiye.", 401)
    if not w.owner:
        W.rate(f"up|{bid(r)}|{w.id or ip}", 30, 600)
    if not raw or len(raw) > MAX_UPLOAD:
        STATS["upload_refused"] += 1
        raise W.AppError("Photo bahut badi hai (6 MB tak).", 413)
    try:
        Image.MAX_IMAGE_PIXELS = 40_000_000
        im = Image.open(io.BytesIO(raw))
        if (im.format or "").upper() not in ("JPEG", "PNG", "WEBP", "HEIF", "HEIC", "GIF"):
            raise ValueError(im.format)
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        im.thumbnail((1600, 1600))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=82, optimize=True)
    except Exception:                                   # noqa: BLE001
        STATS["upload_refused"] += 1
        raise W.AppError("Yeh photo nahi khuli (JPEG / PNG / WebP bhejiye).", 415)
    fid = "f_" + _sec.token_hex(8)
    d = _files(r)
    (d / (fid + ".jpg")).write_bytes(out.getvalue())
    (d / (fid + ".json")).write_text(json.dumps({"owner": w.id, "at": now().isoformat(), "size": out.tell(),
                                                 "w": im.width, "h": im.height, "public": False}))
    STATS["uploads"] += 1
    return {"id": fid, "w": im.width, "h": im.height, "size": out.tell()}


def file_for(r: AppProject, fid: str, w: W.Who):
    """The stored photo, for the person who sent it, staff, her, or anyone when it sits in a public list."""
    meta = _file_meta(r, fid)
    f = _files(r) / (fid + ".jpg") if meta is not None else None
    if f is None or not f.exists():
        raise W.AppError("not found", 404)
    if not (meta.get("public") or w.staff or (w.id and meta.get("owner") == w.id)):
        raise W.AppError("not found", 404)
    return f


def updates(r: AppProject, w: W.Who, since: str = "") -> dict[str, Any]:
    """What changed for this person since `since` (the app's background check, every 15+ minutes): a customer hears that
    HER rows moved (status / paid), a staff account hears about NEW rows in the order-like lists."""
    from datetime import datetime, timedelta
    if w.m is None:
        raise W.AppError("Pehle login kijiye.", 401)
    sch, site = schema(r), bid(r)
    try:
        t0 = datetime.fromisoformat(since[:32]) if since else now() - timedelta(hours=6)
    except ValueError:
        t0 = now() - timedelta(hours=6)
    from datetime import timezone
    t0 = t0 if t0.tzinfo else t0.replace(tzinfo=timezone.utc)
    t0n = t0.astimezone(timezone.utc).replace(tzinfo=None)      # SQLite hands rows back without a zone (UTC)
    items = []
    colls = {c["key"]: c for c in sch["collections"]}
    with session() as s:
        q = s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id == site, W.SiteAppRow.updated_at > t0)
        if not w.staff:
            q = q.filter(W.SiteAppRow.owner == w.m.id)
        for row in q.order_by(W.SiteAppRow.updated_at.asc()).limit(50).all():
            c = colls.get(row.coll)
            if c is None:
                continue
            d = _j(row.data, {})
            created = row.created_at.replace(tzinfo=None) if row.created_at else None
            changed = row.updated_at.replace(tzinfo=None) if row.updated_at else None
            fresh = created is not None and created > t0n
            try:
                ev = datetime.fromisoformat(str(d.get("_ev") or "")) if d.get("_ev") else None
            except ValueError:
                ev = None
            moved = ev is not None and ev > t0 and changed is not None
            head = next((str(d.get(f["key"]) or "") for f in c["fields"] if f.get("type") in ("text", "long_text")
                         and d.get(f["key"]) and f["key"] not in ("items", "utr")), c["label"])
            if w.staff and fresh and row.coll in NEWS and row.owner != w.m.id:
                items.append({"kind": "new", "coll": row.coll, "id": row.id, "title": f"New {NEWS[row.coll]}: {head[:60]}",
                              "status": d.get("status", "")})
            elif row.owner == w.m.id and moved:
                items.append({"kind": "status", "coll": row.coll, "id": row.id, "title": head[:60],
                              "status": d.get("status", ""), "paid": d.get("paid", "")})
    STATS["updates"] += 1
    return {"now": now().isoformat(), "items": items}


def mark_paid(r: AppProject, coll: str, row_id: str, utr: str, w: W.Who) -> dict[str, Any]:
    """The customer says she paid by UPI and types the UPI reference. Nothing is verified here (Hoola never sees money):
    the row reads "Customer says paid" and the owner gets a note to check her own bank app; only she marks Verified."""
    sch = schema(r)
    if coll != sch.get("order"):
        raise W.AppError("Yeh list payment ki nahi.", 400)
    if w.m is None:
        raise W.AppError("Pehle login kijiye.", 401)
    ref = re.sub(r"\s", "", str(utr or ""))
    if not re.fullmatch(r"[A-Za-z0-9]{6,24}", ref):
        raise W.AppError("UPI reference / UTR sahi nahi (6-24 akshar / ank).")
    c = W.coll(sch, coll)
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != bid(r) or row.coll != coll or row.owner != w.m.id:
            raise W.AppError("Yeh order nahi mila.", 404)
        d = _j(row.data, {})
        if d.get("paid") == "Verified":
            raise W.AppError("Is order ka payment pehle hi pakka hai.", 409)
        d.update({"paid": "Customer says paid", "utr": ref[:24]})
        row.data, row.updated_at = json.dumps(d, ensure_ascii=False), now()
        s.flush()
        s.expunge(row)
    STATS["paid_claims"] += 1
    out = W.row_view(c, row, w)
    total = out.get("total")
    try:
        from .android.service import _note
        _note(r, f"{out.get('name') or 'Customer'} ne {r.name or 'aapki app'} ke order ka payment UPI se bheja bataya"
                 + (f" (Rs {total:g})" if isinstance(total, (int, float)) else "") + f", UTR {ref[-12:]}. Apne bank / UPI app "
                 "mein check karke kahiye 'payment verified' - tab tak order 'Customer says paid' hai.")
    except Exception:                                   # noqa: BLE001
        log.debug("paid note", exc_info=True)
    return out
