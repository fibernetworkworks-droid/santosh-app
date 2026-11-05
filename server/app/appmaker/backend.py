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
# v0.364 the values the server adds to an order (stored as "_<key>" so a list's own field of that name is never overwritten)
SYS_KEYS = ("subtotal", "discount", "coupon", "coupon_note", "delivery", "delivery_note", "slot", "slot_label")
STATS = {"schemas": 0, "orders": 0, "dedup": 0, "notes": 0, "notes_capped": 0, "deleted_accounts": 0}
CID = re.compile(r"^[A-Za-z0-9_-]{8,48}$")
NOTE_CAP_PER_HOUR = 30
SCHEMA_V = 2                     # v0.319 photo / location / paid fields
MAX_DOC = 10 * 1024 * 1024        # v0.346 a PDF (prescription, ID proof, bill, resume) - kept as sent, checked, 10 MB
# a PDF that could run something when opened is refused (scripts, launch / open actions, embedded files, forms engine, media)
PDF_RISK = re.compile(rb"/(JavaScript|JS|Launch|EmbeddedFiles?|OpenAction|AA|RichMedia|XFA|SubmitForm|ImportData|GoToR)\b")
MAX_UPLOAD = 6 * 1024 * 1024     # what the phone may send (it shrinks to ~1600 px first); stored re-encoded, smaller
MAX_VIDEO = 50 * 1024 * 1024     # v0.425 RANG: a short video (MP4 / MOV), kept as sent after a container check
MAX_AUDIO = 10 * 1024 * 1024     # v0.425 a voice note (M4A / MP4 audio)
MAX_PHOTOS = 6                   # v0.425 photos in one multi-photo field
RICH_TAG = re.compile(r"<[^>]{0,200}>")
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
EXTRA_TYPES = ("photo", "location", "scan", "file", "signature", "photos", "video", "audio", "richtext")   # v0.425 RANG    # v0.346 file = a PDF document        # v0.340 scan = a barcode / QR read by the camera (or typed)
DOC_NAME = re.compile(r"(?i)(document|doc_|attachment|report|prescription|invoice|bill|resume|cv|proof|certificate|receipt|agreement|kyc)")
SCAN_NAME = re.compile(r"(?i)(barcode|^sku$|^tag$|serial|qr_?code|^imei$)")
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
        fields, extra = [], {"photo": 0, "location": 0, "scan": 0, "file": 0}
        for f in D.parse_fields(D.ENTITIES[e][2]):
            t = DM_TYPE.get(f["type"])
            if t == "text" and SCAN_NAME.search(f["name"]):      # v0.340 codes on labels are scanned, not typed
                t = "scan"
            if t == "photo" and DOC_NAME.search(f["name"]):      # v0.346 papers are PDFs (a photo still works there)
                t = "file"
            if t in extra:                      # at most 2 photos and 1 location per staff list
                extra[t] += 1
                if extra[t] > (2 if t in ("photo", "scan", "file") else 1):
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
    if (be.get("schema") or {}).get("kind") == "web" and be.get("schema", {}).get("collections") is not None:
        return _web_upgrade(r, be)     # v0.414 a website's lists are HERS (from the site / Architect), never re-made from a plan
    # v0.319 an older backend is upgraded in place: lists only GAIN fields (photo / location / paid), rows are untouched
    from . import locks as LK
    with LK.app(r.id), session() as s:           # v0.390 under the app's lock, from the row as it is NOW
        row = s.get(AppProject, r.id)
        be = _j(row.backend if row is not None else r.backend, {})
        if be.get("schema", {}).get("collections") is not None and int(be.get("v") or 1) >= SCHEMA_V:
            r.backend = row.backend
            return be
        old_changes = be.get("changes") or []
        keep = {k: v for k, v in be.items() if k not in ("schema", "v", "made", "rev", "changes", "upgraded")}
        be = {**keep, "schema": schema_for(r), "made": be.get("made") or now().isoformat(), "v": SCHEMA_V,
              "rev": int(be.get("rev") or 0), "changes": old_changes,   # v0.390 EVERY other setting survives (stock, coupons...)
              **({"upgraded": now().isoformat()} if be.get("made") else {})}
        for ch in old_changes:                 # v0.325 her own data changes survive an upgrade: replayed on the new lists
            _apply_ops(be["schema"], ch.get("ops") or {})
        txt = json.dumps(be, ensure_ascii=False)
        if row is not None:
            row.backend = txt
    r.backend = txt
    STATS["schemas"] += 1
    return be


def _web_upgrade(r: AppProject, be: dict[str, Any]) -> dict[str, Any]:
    """v0.414 a website app's backend only gets its version number raised: lists, fields and rows stay exactly as they are."""
    def up(b):
        b["v"] = SCHEMA_V
    out = patch_backend(r, fn=up)
    return out


def patch_backend(r: AppProject, set_: dict[str, Any] | None = None, drop: tuple[str, ...] = (), fn=None) -> dict[str, Any]:
    """v0.390 the ONLY safe way to change an app's backend JSON from slow code (logic apply, timed-job state, owner
    settings): under the app's cross-process lock, re-read the row as it is NOW, change only these keys, write it back -
    so a stock / coupon / slot change made in between is never overwritten by a stale copy."""
    from . import locks as LK
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = _j(row.backend, {})
        if fn is not None:
            fn(be)
        be.update(set_ or {})
        for k in drop:
            be.pop(k, None)
        txt = json.dumps(be, ensure_ascii=False)
        row.backend = txt
    r.backend = txt
    return be


def schema(r: AppProject) -> dict[str, Any]:
    from .logic import engine as LE                  # v0.382 DIMAAG: refs / formulas / workflow states on the lists
    return LE.decorated(r, ensure(r))


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
    from . import family as FA                       # v0.435 PARIVAAR: a rider / shop / staff app uses its main app's backend
    FA.note_key(app_key, r)
    return FA.home(r)


def who(r: AppProject, token: str) -> W.Who:
    m = W.member_of(bid(r), token) if token else None
    if m is not None:
        from ..site import security as SEC                 # v0.455 a login she / the member ENDED stops working at once
        if not SEC.token_ok(bid(r), token):
            return W.Who(None)
    return W.Who(m)


def public_schema(r: AppProject) -> dict[str, Any]:
    sch = schema(r)
    from . import coupon as CP
    out = {**W.public_schema(sch), "kind": sch.get("kind", ""), "order": sch.get("order", ""),
           "coupons": bool(sch.get("order")) and CP.active(r),            # v0.358 the cart shows the code box
           "approvals": bool(sch.get("approvals")), "functions": sch.get("functions") or []}   # v0.382 DIMAAG
    tr = _track_public(r)                                                 # v0.412 NAKSHA LIVE
    if tr:
        out["track"] = tr
    try:                                                                  # v0.540 JAANCH: feature switches (no login yet)
        from . import rollout as RO
        out["flags"] = RO.for_member(r, "")
    except Exception:                                                     # noqa: BLE001
        log.debug("flags public", exc_info=True)
    try:                                                                  # v0.455 SURAKSHIT LOGIN: the login box's ways
        from . import sign as SG
        out["sign"] = SG.public(r)
    except Exception:                                                     # noqa: BLE001
        log.debug("sign public", exc_info=True)
    return out


def signup(r: AppProject, email: str, password: str, name: str, ip: str) -> dict[str, Any]:
    return W.signup(bid(r), schema(r), email, password, name, ip)


def login(r: AppProject, email: str, password: str, ip: str) -> dict[str, Any]:
    schema(r)
    return W.login(bid(r), email, password, ip)


def _products(r: AppProject) -> dict[str, dict[str, Any]]:
    """Her products + one entry per size (v0.362 VARIANTS: "pid::vid", "Name (size)", its own price)."""
    from . import variants as VR
    return VR.expand(r, _base_products(r))


def _base_products(r: AppProject) -> dict[str, dict[str, Any]]:
    from .android import service as AN
    key = _j(r.android, {}).get("app_key") or ""
    try:
        lists = AN.content(key)["lists"] if key else {}
    except Exception:                                     # noqa: BLE001
        lists = {}
    return {str(p.get("id")): p for p in (lists.get("products") or []) if isinstance(p, dict) and p.get("id")}


def _cart_lines(r: AppProject, cart: Any) -> list[tuple[str, int, str]]:
    """v0.357 the cart as [(product id, qty, name)] - the same products / quantities _priced counts."""
    prods, out = _products(r), []
    for it in (cart if isinstance(cart, list) else [])[:80]:
        if not isinstance(it, dict):
            continue
        p = prods.get(str(it.get("id") or ""))
        try:
            q = max(0, min(999, int(it.get("qty") or 0)))
        except (TypeError, ValueError):
            q = 0
        if p is not None and q > 0:
            out.append((str(p.get("id")), q, str(p.get("name") or "")))
    return out


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
    """One write from the app. `cid` = the phone's own id for this write: the same cid again returns the first row.
    v0.390 the cid check and the insert hold one cross-process lock, so a phone's retry racing its first try in another
    worker process still makes exactly ONE row."""
    from . import backup as BK
    cid = str((body or {}).get("cid") or "") if isinstance(body, dict) else ""
    with BK.acting(w):                                   # v0.434 the journal records who made it
        if w.m is not None and (w.m.role or "") == "partner":      # v0.435 PARIVAAR: a partner shop's own menu rows
            from . import family as FA
            got_p = FA.create(r, coll, body, w, ip)
            if got_p is not None:
                return got_p
        if cid and CID.match(cid):
            from . import locks as LK
            with LK.hold(f"cid:{r.id}:{w.id}:{cid}"):
                return _create(r, coll, body, w, ip)
        return _create(r, coll, body, w, ip)


def _create(r: AppProject, coll: str, body: dict[str, Any], w: W.Who, ip: str = "") -> dict[str, Any]:
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
    taken: list = []
    if coll == sch.get("order") and "cart" in body:
        items, total = _priced(r, body.get("cart"))
        extra = {"items": items, "total": total}
    # v0.378 the discount code / delivery slot travel as "_coupon" / "_slot" (a list may have its OWN field named
    # coupon or slot - e.g. a scanned coupon code, a booking slot - and that field is never taken away)
    keys = {f["key"] for f in c["fields"]}
    code = str(body.get("_coupon") or (body.get("coupon") if "coupon" not in keys else "") or "").strip()
    slot_in = str(body.get("_slot") or (body.get("slot") if "slot" not in keys else "") or "")
    reserved = {"cid", "cart", "_coupon", "_slot"} | ({"coupon"} if "coupon" not in keys else set()) | ({"slot"} if "slot" not in keys else set())
    data = {k: v for k, v in body.items() if k not in reserved}
    _check_extra(r, c, data, w)
    from .logic import engine as LE                  # v0.382 DIMAAG: refs, first workflow state, formulas, rules (or refused)
    data = LE.before_create(r, coll, data, w)
    if extra:                                  # v0.357 STOCK: taken under one lock before the row exists (or refused)
        from . import stock as SK
        taken = SK.reserve(r, _cart_lines(r, body.get("cart")))
        if taken:
            extra["_stock"] = [[p, q] for p, q in taken]
    if extra and code:                         # v0.358 COUPON: applied by the server from its own subtotal (or noted, never lost)
        from . import coupon as CP
        d, cf = CP.apply(r, code, extra["total"], w)
        extra.update(cf)
        extra["total"] = round(extra["total"] - d, 2)
    slot_key = slot_in
    if extra:                                  # v0.360 DELIVERY: added after the coupon (a coupon discounts the goods only)
        from . import delivery as DL
        fee, df = DL.on_order(r, extra["total"], data)
        if slot_key:                           # v0.371 SLOT: booked under a lock, or a note (never a refusal)
            sf, why = DL.book(r, slot_key)
            df = {**df, **sf}
            if why:
                df["delivery_note"] = (df.get("delivery_note", "").rstrip(".") + "; " if df.get("delivery_note") else "") + why + "."
        if df:
            extra.update(df)
            extra["total"] = round(extra["total"] + fee, 2)
            if df.get("delivery_note"):
                try:
                    from .android.service import _note
                    _note(r, f"{r.name or 'Aapki app'} ({r.number}) naya order: {df['delivery_note']}")
                except Exception:
                    log.debug("delivery note", exc_info=True)
    from . import meter as MT                        # v0.390 her app's row limit (warns her at 80 / 95%, refuses at 100%)
    MT.check_write(r)
    try:
        out = W.create(site, sch, coll, data, w, ip, cap=10**9)
    except Exception:
        if taken:
            from . import stock as SK
            SK.put_back(r, taken)
        if extra.get("discount"):
            from . import coupon as CP
            CP.give_back(r, extra["coupon"], w.id)
        raise
    if extra or cid:
        stored = {("_" + k if k in SYS_KEYS else k): v for k, v in extra.items()}   # v0.364 system values never overwrite her fields
        _merge(out["id"], {**stored, **({"_cid": cid} if cid else {})})
        if extra.get("slot"):                          # v0.371 two orders raced for the last place: the later one gets the note
            from . import delivery as DL
            DL.confirm(r, out["id"])
    LE.after_create(r, coll, out["id"], w)          # v0.382 formulas stored, triggers, parents' totals
    try:                                            # v0.435 PARIVAAR: the partner shop this order is for hears it at once
        from . import family as FA
        FA.on_create(r, coll, out["id"], out)
    except Exception:
        log.debug("family create", exc_info=True)
    try:                                            # v0.424 JODO: her approved connectors listening for a new row (queued)
        from . import connect as CN
        CN.fire(r, coll, out["id"], "create")
    except Exception:
        log.debug("connect create", exc_info=True)
    out = W.row_view(c, _row(site, out["id"]), w)
    LE.decorate(r, coll, [out], w)
    if extra:
        STATS["orders"] += 1
    if coll in NEWS:
        _news(r, coll, out)
        try:                                            # v0.367 TURANT: staff phones hear about a new order / booking at once
            from . import turant as TU
            who_ = str(out.get("name") or out.get("customer") or "").strip()[:40]
            TU.later(r, [m for m in TU.staff_ids(r) if m != w.id], f"New {NEWS[coll]}", who_ or r.name or "", out.get("id", ""))
        except Exception:
            log.debug("turant new", exc_info=True)
    return out


def rows(r: AppProject, coll: str, w: W.Who, limit: int = 200, q: str = "", status: str = "", offset: int = 0,
         mine: bool = False) -> list[dict[str, Any]]:
    """v0.319 + search (q, any field) and a status filter, newest first; offset pages through them.
    v0.352 every row says who it is with (staff) / the first name on it (her own row); mine = only the rows given to me."""
    if w.m is not None and (w.m.role or "") == "partner":          # v0.435 PARIVAAR: a partner sees only its own work
        from . import family as FA
        got_p = FA.rows(r, coll, w, limit, q, status, offset, mine)
        if got_p is not None:
            return got_p
    got = with_assign(r, W.rows(bid(r), schema(r), coll, w, 1000 if (q or status or offset or mine) else limit), w)
    if mine:
        got = [x for x in got if w.id and x.get("assigned_to") == w.id]
    if status:
        got = [x for x in got if str(x.get("status") or "") == status]
    if q:
        t = q.strip().lower()[:80]
        got = [x for x in got if t in json.dumps(x, ensure_ascii=False).lower()]
    offset = max(0, int(offset or 0))
    from .logic import engine as LE                  # v0.382 ref names, workflow buttons, approvals waiting
    return LE.decorate(r, coll, got[offset:offset + max(1, min(int(limit or 200), 1000))], w)


def update(r: AppProject, coll: str, row_id: str, body: dict[str, Any], w: W.Who) -> dict[str, Any]:
    from . import backup as BK
    with BK.acting(w):                               # v0.434 the journal records who made it
        if w.m is not None and (w.m.role or "") == "partner":      # v0.435 PARIVAAR: checked steps only, then as the system
            from . import family as FA
            return FA.update(r, coll, row_id, body, w)
        return _update_inner(r, coll, row_id, body, w)


def _update_inner(r: AppProject, coll: str, row_id: str, body: dict[str, Any], w: W.Who) -> dict[str, Any]:
    body = {k: v for k, v in (body if isinstance(body, dict) else {}).items() if k not in ("cid", "cart")}
    if body.get("_credit"):                  # v0.359 KHATA: staff's "on credit" through the outbox (works offline)
        from . import khata as KH
        KH.credit(r, coll, row_id, w)
        body.pop("_credit", None)
        if not body:
            return with_assign(r, W.row_view(W.coll(schema(r), coll), _row(bid(r), row_id), w), w)
    body.pop("_credit", None)
    if RATE_KEY in body:                     # v0.353 the app's outbox sends a rating as an update {"_rate": {stars, note}}
        v = body.pop(RATE_KEY)
        v = v if isinstance(v, dict) else {"stars": v}
        return rate(r, coll, row_id, v.get("stars"), str(v.get("note") or ""), w)
    if ASSIGN_KEY in body:                   # v0.352 the app's outbox sends an assignment as an update {"_assign": id|"me"|""}
        to = body.pop(ASSIGN_KEY)
        out = assign(r, coll, row_id, str(to or ""), w)
        if not body:
            return out
    sch = schema(r)
    _guard_assigned(r, coll, row_id, w)
    _check_extra(r, W.coll(sch, coll), body, w)
    from .logic import engine as LE                  # v0.382 workflow steps / approvals, formulas, rules
    old = LE.load(r, row_id, coll)
    body, info = LE.before_update(r, coll, row_id, body, w)
    appr, move = (info or {}).get("approval"), (info or {}).get("move")
    if body or not (appr or move):
        out = W.update(bid(r), sch, coll, row_id, body, w)
    if move:                                         # an allowed workflow step (a customer's own Cancel too): the engine moves it
        LE.store(r, row_id, {move[0]: move[1]})
    LE.after_update(r, coll, row_id, old, w)
    if LE.compiled(r):
        out = W.row_view(W.coll(sch, coll), _row(bid(r), row_id), w)
        LE.decorate(r, coll, [out], w)
        if appr is not None:
            out["approval"] = appr
    moved = bool(move) or any(k in body for k in ("status", "paid"))
    if moved:
        _merge(row_id, {"_ev": now().isoformat()})     # v0.319 the moment her row moved: the app's update check reads it
        try:                                            # v0.367 TURANT: ... and her phone hears it at once (when on)
            from . import turant as TU
            owner = _row(bid(r), row_id).owner
            if owner and owner != w.id:
                c_ = W.coll(sch, coll)
                head = next((str(out.get(f["key"]) or "") for f in c_["fields"] if f.get("type") in ("text", "long_text")
                             and out.get(f["key"]) and f["key"] not in ("items", "utr")), c_["label"])
                TU.later(r, [owner], f"{c_['label']}: {out.get('status') or out.get('paid') or ''}".strip(": "), head[:80], row_id)
        except Exception:
            log.debug("turant status", exc_info=True)
    if "status" in body or (move and move[0] == "status"):
        status_moved(r, row_id, str(out.get("status") or ""))
    return with_assign(r, out, w)


def status_moved(r: AppProject, row_id: str, status: str) -> None:
    """A row reached a new status (her app, Hoola, an approval, a trigger, an SLA): a cancelled order gives back what it took."""
    try:                                            # v0.424 JODO: connectors waiting for this status (queued, never blocks)
        from . import connect as CN
        with session() as s_:
            x_ = s_.get(W.SiteAppRow, row_id)
            coll_ = x_.coll if x_ is not None else ""
        if coll_:
            CN.fire(r, coll_, row_id, "status", status)
    except Exception:
        log.debug("connect status", exc_info=True)
    try:                                            # v0.435 PARIVAAR: ready for pickup -> approved riders hear of the job
        from . import family as FA
        FA.on_status(r, row_id, status)
    except Exception:
        log.debug("family status", exc_info=True)
    if status.strip().lower() != "cancelled":
        return
    _stock_back(r, row_id)                          # v0.357 a cancelled order puts its stock back (once)
    _coupon_back(r, row_id)                         # v0.358 ... and its coupon use (once)
    from . import khata as KH                       # v0.359 ... and a credited order's udhaar is reversed (once)
    KH.reverse_order(r, row_id)
    from . import gst as G                          # v0.356 an invoiced row cancelled -> its credit note (given once)
    got = G.credit_for(r, row_id, "Order cancelled")
    if got:
        try:
            from .android.service import _note
            _note(r, f"{r.name or 'Aapki app'} ({r.number}): cancelled order ka credit note {got[0]} ban gaya "
                     "(invoice ke saamne). Paise lautane hon to woh aap khud karein; credit note sirf likhit record hai.")
        except Exception:
            log.debug("credit note note", exc_info=True)


def delete(r: AppProject, coll: str, row_id: str, w: W.Who) -> dict[str, Any]:
    from . import backup as BK
    with BK.acting(w):                               # v0.434 the journal records who made it
        if w.m is not None and (w.m.role or "") == "partner":      # v0.435 PARIVAAR
            from . import family as FA
            return FA.delete(r, coll, row_id, w)
        return _delete_inner(r, coll, row_id, w)


def _delete_inner(r: AppProject, coll: str, row_id: str, w: W.Who) -> dict[str, Any]:
    _guard_assigned(r, coll, row_id, w)
    from .logic import engine as LE                  # v0.382 children first: restrict / cascade / nullify
    sch = schema(r)
    W.coll(sch, coll)
    with session() as s:                             # her permission is checked BEFORE any child is touched
        row = s.get(W.SiteAppRow, row_id)
        if row is not None and row.site_id == bid(r) and row.coll == coll and not W._can_write(W.coll(sch, coll), w, row, "delete"):
            W._deny()
    d = LE.before_delete(r, coll, row_id, w)
    out = W.delete(bid(r), sch, coll, row_id, w)
    LE.after_delete(r, coll, row_id, d, w)
    return out


def delete_me(r: AppProject, w: W.Who) -> dict[str, Any]:
    from . import backup as BK
    with BK.acting(w):                               # v0.434 the journal records who made it
        return _delete_me_inner(r, w)


def _delete_me_inner(r: AppProject, w: W.Who) -> dict[str, Any]:
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


def data_app(tenant: str, ref: str) -> AppProject:
    """v0.435 PARIVAAR: the app whose DATA she means - a rider / shop / staff app's data is its main app's."""
    from . import family as FA
    return FA.home(by_key_or_ref(tenant, ref))


def owner_view(r: AppProject) -> dict[str, Any]:
    from . import family as FA
    r = FA.home(r)
    be = ensure(r)
    sch = be["schema"]
    from ..config import get_settings
    base = (get_settings().public_base_url or "").rstrip("/")
    key = _j(r.android, {}).get("app_key") or ""
    return {"app": r.id, "number": r.number, "name": r.name, "kind": sch.get("kind"), "order": sch.get("order"),
            "collections": sch["collections"], "counts": W.counts(bid(r)), "made": be.get("made"),
            "api": f"{base}/api/app-api/{key}" if key else "", "live": bool(key)}


def owner_rows(r: AppProject, coll: str, limit: int = 300) -> list[dict[str, Any]]:
    from . import family as FA
    r = FA.home(r)
    return rows(r, coll, W.Who(owner=True), limit)


def owner_update(r: AppProject, coll: str, row_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from . import backup as BK
    with BK.acting(W.Who(None, owner=True)):                               # v0.434 the journal records who made it
        return _owner_update_inner(r, coll, row_id, body)


def _owner_update_inner(r: AppProject, coll: str, row_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Her change from Hoola; {"assign": member id | ""} gives the row to a staff member (v0.352)."""
    from . import family as FA
    r = FA.home(r)
    body = dict(body or {})
    if "assign" in body:
        body[ASSIGN_KEY] = body.pop("assign")
    return update(r, coll, row_id, body, W.Who(owner=True))


def members(r: AppProject) -> list[dict[str, Any]]:
    from . import family as FA
    r = FA.home(r)
    ensure(r)
    return W.members(bid(r))


def set_role(r: AppProject, member_id: str, role: str) -> dict[str, Any]:
    from . import family as FA
    r = FA.home(r)
    ensure(r)
    return W.set_role(bid(r), member_id, role)


def seed_hint(r: AppProject) -> dict[str, Any]:
    """What the build puts into the app (assets/seed.json 'backend'): the lists, their fields and rules - no data."""
    from . import family as FA                             # v0.435 PARIVAAR: a face app carries its MAIN app's lists
    face = FA.face_info(r)
    r = FA.home(r)
    sch = schema(r)
    out = {"kind": sch.get("kind"), "order": sch.get("order"), "signup": sch.get("signup", True),
           "collections": sch["collections"]}
    if sch.get("approvals"):                               # v0.382 DIMAAG: the Approvals button for staff
        out["approvals"] = True
    try:                                                   # v0.455 SURAKSHIT LOGIN: which ways the app's login box offers
        from . import sign as SG
        out["sign"] = SG.public(r)
    except Exception:                                      # noqa: BLE001
        log.debug("sign hint", exc_info=True)
    if sch.get("order"):                                   # v0.358 COUPON: the cart shows the code box while a code is live
        from . import coupon as CP
        out["coupons"] = CP.active(r)
        from . import delivery as DL                       # v0.360 the cart shows the delivery rule + open / closed
        dl = DL.public(r)
        if dl:
            out["delivery"] = dl
    tr = _track_public(r)                                  # v0.412 NAKSHA LIVE: shift button, maps, Track live
    if tr:
        out["track"] = tr
    try:                                                   # v0.424 JODO: the staff buttons for her approved connectors
        from . import connect as CN
        btn = CN.staff_buttons(r)
        if btn:
            out["connect"] = btn
    except Exception:                                      # noqa: BLE001
        log.debug("connect hint", exc_info=True)
    try:                                                   # v0.419 PAISA: the Pay online button + AutoPay plans
        from . import pay as PY
        if PY.on(r):
            out["pay"] = {"on": True, "plans": bool(PY.plans(r)["plans"])}
    except Exception:                                      # noqa: BLE001
        log.debug("pay hint", exc_info=True)
    if face:
        out["face"] = face["kind"]
        if face["kind"] in FA.PARTNER_KINDS:
            out["partner"] = face["kind"]
    return out


def _track_public(r: AppProject) -> dict[str, Any] | None:
    try:
        from . import track as TR
        st = TR.settings(r)
    except Exception:                                       # noqa: BLE001
        return None
    return {"on": True, "coll": st["coll"], "statuses": st["statuses"], "loc": st["loc"]} if st["on"] else None


# ---------------------------------------------------------------- v0.319 photos, location, updates, "I paid"
def _check_extra(r: AppProject, c: dict[str, Any], data: dict[str, Any], w: W.Who) -> None:
    """Photo fields carry a file this app holds and this person may use; location fields are a real "lat,lng"."""
    for f in c["fields"]:
        k, t = f["key"], f.get("type")
        if t not in EXTRA_TYPES or k not in data or data[k] in (None, ""):
            continue
        v = str(data[k]).strip()
        if t == "scan":                         # v0.340 whatever the label holds, as plain text (no control characters)
            v = re.sub(r"[\x00-\x1f\x7f]", "", v)[:200]
            if not v:
                raise W.AppError(f"{f['label']}: code khaali hai.")
            data[k] = v
            continue
        if t == "richtext":                     # v0.425 formatted text = markdown words only (no HTML ever reaches a screen)
            data[k] = RICH_TAG.sub("", re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", v))[:4000]
            continue
        if t == "photos":                       # v0.425 up to MAX_PHOTOS picture ids, each checked like one photo
            ids = [x.strip() for x in v.split(",") if x.strip()]
            if len(ids) > MAX_PHOTOS:
                raise W.AppError(f"{f['label']}: {MAX_PHOTOS} photos tak.")
            for x in ids:
                meta = _file_meta(r, x)
                if meta is None or meta.get("kind") not in (None, "image") or \
                        not (w.staff or (w.id and meta.get("owner") == w.id) or (not meta.get("owner") and not w.id)):
                    raise W.AppError(f"{f['label']}: ek photo is account ki nahi.", 403)
            data[k] = ",".join(ids)
            continue
        if t == "location":
            m = LOC.match(v)
            if not m or abs(float(m.group(1))) > 90 or abs(float(m.group(2))) > 180:
                raise W.AppError(f"{f['label']}: location sahi nahi (lat,lng).")
            data[k] = f"{float(m.group(1)):.6f},{float(m.group(2)):.6f}"
        else:
            meta = _file_meta(r, v)
            if meta is None or not (w.staff or (w.id and meta.get("owner") == w.id) or (not meta.get("owner") and not w.id)):
                raise W.AppError(f"{f['label']}: yeh photo is account ki nahi.", 403)
            if t == "photo" and meta.get("kind") == "pdf":         # v0.346
                raise W.AppError(f"{f['label']}: yahan photo chahiye, PDF nahi.")
            want = {"signature": (None, "image"), "video": ("video",), "audio": ("audio",)}.get(t)   # v0.425
            if want is not None and meta.get("kind") not in want:
                raise W.AppError(f"{f['label']}: yeh file is field ke liye nahi.")
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


MEDIA_EXT = {"video": ".mp4", "video_mov": ".mov", "audio": ".m4a"}
MEDIA_MIME = {".mp4": "video/mp4", ".mov": "video/quicktime", ".m4a": "audio/mp4", ".pdf": "application/pdf", ".jpg": "image/jpeg"}


def _upload_media(r: AppProject, w: W.Who, raw: bytes, want: str) -> dict[str, Any]:
    """v0.425 RANG: a video / voice note, kept as sent. Only an ISO-BMFF container (MP4 / MOV / M4A) whose first box is
    `ftyp` with a known brand gets in - not whatever the phone calls it; the app never shows it inside a web page."""
    import secrets as _sec
    cap = MAX_AUDIO if want == "audio" else MAX_VIDEO
    if not raw or len(raw) > cap:
        STATS["upload_refused"] += 1
        raise W.AppError(("Voice note" if want == "audio" else "Video") + f" bahut bada hai ({cap // (1024 * 1024)} MB tak).", 413)
    brand = raw[8:12] if raw[4:8] == b"ftyp" else b""
    video_brands = (b"isom", b"iso2", b"iso4", b"iso5", b"iso6", b"mp41", b"mp42", b"avc1", b"qt  ", b"3gp4", b"3gp5", b"dash", b"MSNV", b"M4V ")
    audio_brands = (b"M4A ", b"M4B ", b"isom", b"mp42", b"mp41", b"iso2", b"3gp4", b"3gp5")
    if (want == "audio" and brand not in audio_brands) or (want == "video" and brand not in video_brands):
        STATS["upload_refused"] += 1
        raise W.AppError("Yeh file nahi khuli (MP4 / MOV video ya M4A voice note bhejiye).", 415)
    ext = ".m4a" if want == "audio" else (".mov" if brand == b"qt  " else ".mp4")
    fid = "f_" + _sec.token_hex(8)
    d = _files(r)
    (d / (fid + ext)).write_bytes(raw)
    (d / (fid + ".json")).write_text(json.dumps({"owner": w.id, "at": now().isoformat(), "size": len(raw), "kind": want,
                                                 "ext": ext, "public": False}))
    STATS["uploads"] += 1
    return {"id": fid, "kind": want, "size": len(raw)}


def upload(r: AppProject, w: W.Who, raw: bytes, ip: str = "", ctype: str = "") -> dict[str, Any]:
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
    if raw[:5] == b"%PDF-":                    # v0.346 a document
        return _upload_pdf(r, w, raw)
    if raw[4:8] == b"ftyp":                     # v0.425 a video / voice note (the app says which; the bytes must agree)
        return _upload_media(r, w, raw, "audio" if (ctype or "").lower().startswith("audio/") else "video")
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


def _upload_pdf(r: AppProject, w: W.Who, raw: bytes) -> dict[str, Any]:
    """v0.346 a PDF: at most 10 MB, really a PDF (pypdf opens it, not encrypted, 1-200 pages), nothing in it that could run
    (scripts, launch / open actions, embedded files, XFA forms, media). Kept byte for byte (re-writing would break signed
    PDFs); only ever served as a download."""
    import io
    import secrets as _sec
    if len(raw) > MAX_DOC:
        STATS["upload_refused"] += 1
        raise W.AppError("PDF bahut bada hai (10 MB tak).", 413)
    if PDF_RISK.search(raw):
        STATS["upload_refused"] += 1
        raise W.AppError("Is PDF mein script ya attachment hai; saada PDF bhejiye (print -> Save as PDF).", 415)
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(raw))
        if rd.is_encrypted:
            raise ValueError("encrypted")
        pages = len(rd.pages)
        if not 1 <= pages <= 200:
            raise ValueError(pages)
        risky = _pdf_risky(rd)
    except Exception:                                   # noqa: BLE001
        STATS["upload_refused"] += 1
        raise W.AppError("Yeh PDF nahi khula (password wala ya toota hua?).", 415)
    if risky:                                           # inside compressed parts too (the byte scan above can miss them)
        STATS["upload_refused"] += 1
        raise W.AppError("Is PDF mein script ya attachment hai; saada PDF bhejiye (print -> Save as PDF).", 415)
    fid = "f_" + _sec.token_hex(8)
    d = _files(r)
    (d / (fid + ".pdf")).write_bytes(raw)
    (d / (fid + ".json")).write_text(json.dumps({"owner": w.id, "at": now().isoformat(), "size": len(raw), "kind": "pdf",
                                                 "pages": pages, "public": False}))
    STATS["uploads"] += 1
    return {"id": fid, "kind": "pdf", "pages": pages, "size": len(raw)}


def _pdf_risky(rd) -> bool:
    """The PDF's own structure: open / page actions, named scripts, attached files, XFA forms, link actions that run or
    fetch something, file-attachment notes."""
    bad_actions = {"/JavaScript", "/Launch", "/ImportData", "/SubmitForm", "/GoToR", "/GoToE", "/RichMediaExecute"}
    root = rd.trailer["/Root"].get_object()
    if "/OpenAction" in root or "/AA" in root:
        return True
    names = root.get("/Names")
    names = names.get_object() if names is not None else {}
    if "/JavaScript" in names or "/EmbeddedFiles" in names:
        return True
    acro = root.get("/AcroForm")
    if acro is not None and "/XFA" in acro.get_object():
        return True
    for page in rd.pages:
        if "/AA" in page:
            return True
        for a in (page.get("/Annots") or []):
            a = a.get_object()
            if a.get("/Subtype") in ("/FileAttachment", "/RichMedia", "/Movie", "/Sound", "/Screen"):
                return True
            act = a.get("/A")
            if act is not None and act.get_object().get("/S") in bad_actions:
                return True
            if "/AA" in a:
                return True
    return False


def file_for(r: AppProject, fid: str, w: W.Who):
    """The stored photo / PDF, for the person who sent it, staff, her, or anyone when it sits in a public list.
    Returns the path; its suffix (.jpg / .pdf) says what it is."""
    meta = _file_meta(r, fid)
    f = (_files(r) / (fid + (meta.get("ext") or (".pdf" if meta.get("kind") == "pdf" else ".jpg")))) if meta is not None else None
    if f is None or not f.exists():
        raise W.AppError("not found", 404)
    if not (meta.get("public") or w.staff or (w.id and meta.get("owner") == w.id) or _readable_via_row(r, fid, w)):
        raise W.AppError("not found", 404)
    return f


def _readable_via_row(r: AppProject, fid: str, w: W.Who) -> bool:
    """v0.581 a file the teacher uploaded into a lesson is hers to watch exactly while she may read that lesson (a gated
    course: only with an active pass) - the row's own read rule decides, never the file alone."""
    if not w.id or not re.fullmatch(r"[\w-]{6,64}", fid or ""):
        return False
    from sqlalchemy import select as _sel
    sch = schema(r)
    with session() as s:
        hits = s.scalars(_sel(W.SiteAppRow).where(W.SiteAppRow.site_id == bid(r), W.SiteAppRow.data.like(f'%"{fid}"%')).limit(20)).all()
        for x in hits:
            s.expunge(x)
    for x in hits:
        try:
            c = W.coll(sch, x.coll)
        except W.AppError:
            continue
        files = {f["key"] for f in c["fields"] if f["type"] in EXTRA_TYPES}
        if any(_j(x.data, {}).get(k) == fid for k in files) and W._can_read(c, w, x):
            return True
    return False


def media_link(r: AppProject, fid: str, w: W.Who) -> dict[str, Any]:
    """v0.425 a 15-minute signed address for a video / voice note / PDF, so the phone's own player can open it without
    the sign-in token (players cannot add headers). Only for someone who may see the file now."""
    import hashlib as _h
    import hmac as _hm
    file_for(r, fid, w)
    exp = int(time.time()) + 900
    sig = _hm.new(W._secret(), f"media|{r.id}|{fid}|{exp}".encode(), _h.sha256).hexdigest()[:32]
    return {"path": f"/api/app-api/{_j(r.android, {}).get('app_key', '')}/media/{fid}.{exp}.{sig}", "expires": exp}


def media_file(r: AppProject, tok: str):
    import hashlib as _h
    import hmac as _hm
    try:
        fid, exp, sig = tok.split(".")
        exp_i = int(exp)
    except ValueError:
        raise W.AppError("not found", 404)
    want = _hm.new(W._secret(), f"media|{r.id}|{fid}|{exp_i}".encode(), _h.sha256).hexdigest()[:32]
    if not _hm.compare_digest(sig, want) or exp_i < time.time():
        raise W.AppError("not found", 404)
    meta = _file_meta(r, fid)
    f = (_files(r) / (fid + (meta.get("ext") or (".pdf" if meta.get("kind") == "pdf" else ".jpg")))) if meta else None
    if f is None or not f.exists():
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
            try:
                at = datetime.fromisoformat(str(d.get("_to_at") or "")) if d.get("_to_at") else None
            except ValueError:
                at = None
            if w.staff and d.get("_to") == w.m.id and at is not None and at > t0:      # v0.352 a row given to me
                items.append({"kind": "assigned", "coll": row.coll, "id": row.id, "title": f"Assigned to you: {head[:60]}",
                              "status": d.get("status", "")})
            elif w.staff and fresh and row.coll in NEWS and row.owner != w.m.id:
                items.append({"kind": "new", "coll": row.coll, "id": row.id, "title": f"New {NEWS[row.coll]}: {head[:60]}",
                              "status": d.get("status", "")})
            elif row.owner == w.m.id and moved:
                items.append({"kind": "status", "coll": row.coll, "id": row.id, "title": head[:60],
                              "status": d.get("status", ""), "paid": d.get("paid", "")})
    try:                                               # v0.378 BAAT: new chat messages for this account
        from . import baat as BT
        items += BT.new_for(r, w, t0n)
    except Exception:
        log.debug("chat updates", exc_info=True)
    STATS["updates"] += 1
    return {"now": now().isoformat(), "items": items}


def stats(r: AppProject, w: W.Who, days: int = 14) -> dict[str, Any]:
    """v0.340 the staff dashboard: per list the row count, the status mix, rows per day for `days` days and the money
    total (orders' server-priced totals). Staff only (customers never see the business's numbers)."""
    from datetime import timedelta
    if w.m is None:
        raise W.AppError("Pehle login kijiye.", 401)
    if not w.staff:
        raise W.AppError("Yeh sirf staff ke liye hai.", 403)
    days = max(7, min(int(days or 14), 60))
    sch, site = schema(r), bid(r)
    today = now().date()
    labels = [(today - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]
    out = []
    with session() as s:
        for c in sch["collections"]:
            keys = {f["key"] for f in c["fields"]}
            rows = s.query(W.SiteAppRow.data, W.SiteAppRow.created_at).filter(W.SiteAppRow.site_id == site,
                                                                              W.SiteAppRow.coll == c["key"]).all()
            st: dict[str, int] = {}
            daily = dict.fromkeys(labels, 0)
            money = 0.0
            for data, created in rows:
                d = _j(data, {})
                if "status" in keys:
                    k = str(d.get("status") or "-")[:40]
                    st[k] = st.get(k, 0) + 1
                day = created.date().isoformat() if created else ""
                if day in daily:
                    daily[day] += 1
                if "total" in keys:
                    try:
                        money += float(d.get("total") or 0)
                    except (TypeError, ValueError):
                        pass
            out.append({"key": c["key"], "label": c["label"], "count": len(rows),
                        "status": dict(sorted(st.items(), key=lambda kv: -kv[1])[:8]),
                        "daily": [daily[x] for x in labels], "total": round(money, 2) if "total" in keys else None})
    STATS["stats"] = STATS.get("stats", 0) + 1
    load = _load(r)                                     # v0.352 open rows per staff member (who has how much work)
    rated = _ratings(r)                                 # v0.353 RAAY: average stars per list and per person
    for l in out:
        got = rated["lists"].get(l["key"])
        l["rating"] = {"avg": round(sum(got) / len(got), 1), "count": len(got)} if got else None
    people = [{"name": _first(m.name, m.email), "open": load.get(m.id, 0),
               "rating": round(sum(rated["people"][m.id]) / len(rated["people"][m.id]), 1) if rated["people"].get(m.id) else None,
               "rated": len(rated["people"].get(m.id, []))} for m in _staff_of(site).values()]
    return {"now": now().isoformat(), "days": labels, "lists": out,
            "team": sorted(people, key=lambda p: -p["open"])[:20], "unassigned": _unassigned(r)}


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


# ---------------------------------------------------------------- v0.325 HOOLA QA: crashes on real users' phones
CRASH_KEEP = 200


def _crash_file(r: AppProject):
    return _files(r).parent / "crashes.json"


def _crash_sig(trace: str) -> tuple[str, str, list[str]]:
    """Same crash = same exception class + the same first app frames (line numbers ignored: they move between builds)."""
    import hashlib
    lines = [ln.strip() for ln in (trace or "").splitlines() if ln.strip()]
    exc = next((ln for ln in lines if re.match(r"(Caused by: )?[\w.$]+(Exception|Error)\b", ln)), lines[0] if lines else "")
    frames = [ln for ln in lines if ln.startswith("at hoola.")][:6]
    key = re.sub(r":\d+\)", ")", exc.split(":")[0] + "|" + "|".join(frames[:3]))
    return "c_" + hashlib.sha1(key.encode()).hexdigest()[:12], exc[:300], frames


def crash(r: AppProject, body: dict[str, Any], ip: str = "") -> dict[str, Any]:
    """A crash the installed app kept and sends on its next start (no login needed; nothing personal in it)."""
    if not isinstance(body, dict):
        raise W.AppError("bad crash")
    W.rate(f"cr|{bid(r)}|{ip}", 20, 3600)
    trace = str(body.get("trace") or "")[:6000]
    if not trace.strip():
        raise W.AppError("empty crash")
    sig, exc, frames = _crash_sig(trace)
    # v0.540 JAANCH: an ANR is NOT a crash - the app did not die, it stopped answering, and Play counts it
    # separately against the app. Two defects that look alike in a list are two defects nobody fixes.
    kind = str(body.get("kind") or "crash").strip().lower()
    kind = kind if kind in ("crash", "anr", "native") else "crash"
    sig = (kind[:3] + sig)[:40] if kind != "crash" else sig
    screen = re.sub(r"[^a-z0-9_]", "", str(body.get("screen") or "").lower())[:49]
    ver = re.sub(r"[^0-9A-Za-z.\-]", "", str(body.get("ver") or ""))[:20]
    f = _crash_file(r)
    from . import locks as LK
    with LK.hold(f"crash:{r.id}"):                  # v0.390 the crash file is shared by every worker process
        data = _j(f.read_text(), {}) if f.exists() else {}
        x = data.get(sig)
        first = x is None
        if first:
            if len(data) >= CRASH_KEEP:
                for k, _v in sorted(data.items(), key=lambda kv: kv[1].get("last", ""))[:len(data) - CRASH_KEEP + 1]:
                    data.pop(k, None)
            x = data[sig] = {"id": sig, "exception": exc, "frames": frames, "sample": trace, "count": 0, "first": now().isoformat(),
                             "screens": [], "versions": [], "devices": [], "status": "new", "kind": kind}
        x["count"] += 1
        x["last"] = now().isoformat()
        x.setdefault("kind", kind)
        for k, v, n in (("screens", screen, 10), ("versions", ver, 10),
                        ("devices", f"{str(body.get('model') or '')[:40]} / "            # v0.332 iPhones report too
                        + (f"iOS {(re.search(r'\d+(?:\.\d+)*', str(body.get('ios'))) or [''])[0][:8]}" if body.get("ios")
                           else f"Android {str(body.get('android') or '')[:3]}"), 8)):
            if v and v not in x[k]:
                x[k] = (x[k] + [v])[-n:]
        came_back = x.get("status") == "fixing" and ver and x.get("fix_version") and ver == x.get("fix_version")
        if came_back:
            x["status"] = "back"            # it happened again in the build that was meant to fix it: say so honestly
        f.write_text(json.dumps(data, ensure_ascii=False))
    STATS["crashes"] = STATS.get("crashes", 0) + 1
    if first or came_back:
        where = f" ({screen} screen)" if screen else ""
        try:
            from .android.service import _note
            _note(r, f"{r.name or 'Aapki app'} ({r.number}) ek user ke phone pe "
                     + ("JAM ho gayi (ANR - screen hil hi nahi rahi thi)" if kind == "anr" else "band ho gayi")
                     + f"{where}: {exc.split(':')[0][:80]}"
                     + (" - fix wali build mein bhi" if came_back else "") + ". Kahiye 'crash theek karo' - Hoola us screen ko asli "
                     "crash dekh kar dobara likhegi aur nayi build banayegi.")
        except Exception:                               # noqa: BLE001
            log.debug("crash note", exc_info=True)
    return {"ok": True, "id": sig, "new": first}


def crashes(r: AppProject) -> list[dict[str, Any]]:
    f = _crash_file(r)
    data = _j(f.read_text(), {}) if f.exists() else {}
    return sorted(data.values(), key=lambda x: (x.get("status") == "fixing", -int(x.get("count") or 0)))


def crash_screens(r: AppProject, sig: str) -> tuple[dict[str, Any], list[str]]:
    """The crash and the app's own screens in its stack (ScreenCart -> cart), else the screen it happened on."""
    from .android import gen as G
    x = next((c for c in crashes(r) if c["id"] == sig), None)
    if x is None:
        raise W.AppError("Yeh crash nahi mila.", 404)
    ids = list(_j(r.plan, {}).get("screens") or [])
    by_cls = {G.kotlin_name(s): s for s in ids}
    sids: list[str] = []
    for fr in x.get("frames") or []:
        m = re.search(r"hoola\.app\.screens\.(Screen\w+?)(Kt)?\.", fr)
        if m and m.group(1) in by_cls and by_cls[m.group(1)] not in sids:
            sids.append(by_cls[m.group(1)])
    if not sids:
        sids = [s for s in x.get("screens") or [] if s in ids][:2]
    return x, sids


def crash_mark(r: AppProject, sig: str, status: str, build: int = 0, version: str = "") -> None:
    f = _crash_file(r)
    from . import locks as LK
    with LK.hold(f"crash:{r.id}"):                  # v0.390 the crash file is shared by every worker process
        data = _j(f.read_text(), {}) if f.exists() else {}
        if sig in data:
            data[sig]["status"] = status
            if build:
                data[sig]["fix_build"] = build
            if version:
                data[sig]["fix_version"] = version
            f.write_text(json.dumps(data, ensure_ascii=False))



# ---------------------------------------------------------------- v0.325 UPDATES: her data changes, safe for old app versions
def _apply_ops(sch: dict[str, Any], ops: dict[str, Any]) -> list[str]:
    """add / hide / label fields. Only changes an app version already on people's phones survives: a new field is never
    required (an old app could not send it; a choice fills its default); a hidden field keeps its data and is
    only left out of the forms; nothing is ever deleted or renamed underneath existing rows."""
    done: list[str] = []
    colls = {c["key"]: c for c in sch.get("collections") or []}
    for nl in (ops.get("add_list") or [])[:8]:   # v0.382 DIMAAG: a new list (customers, order lines, classes...)
        k = W._slug(nl.get("key") or nl.get("label"))
        if not k or k.startswith("_") or k in colls:
            if k in colls:
                continue                         # replayed on an upgrade / already there: nothing to do
            raise W.AppError("Nayi list ka naam chahiye.")
        if len(colls) >= W.MAX_COLLECTIONS + 8:
            raise W.AppError("Is app mein aur list nahi aa sakti.")
        ru = nl.get("rules") if isinstance(nl.get("rules"), dict) else {}
        c = {"key": k, "label": str(nl.get("label") or k.replace("_", " ").title())[:60], "fields": [],
             "rules": {"create": ru.get("create") if ru.get("create") in W.CREATE else "admin",
                       "read": ru.get("read") if ru.get("read") in W.READ else "admin",
                       "update": ru.get("update") if ru.get("update") in W.WRITE else "admin",
                       "delete": ru.get("delete") if ru.get("delete") in W.WRITE else "admin"}}
        for f in (nl.get("fields") or [])[:W.MAX_FIELDS]:
            fd = _new_field(f, colls | {k: c}, fresh=True)
            if fd and not any(x["key"] == fd["key"] for x in c["fields"]):
                c["fields"].append(fd)
        if not c["fields"]:
            raise W.AppError(f"List '{k}' mein koi field nahi.")
        sch.setdefault("collections", []).append(c)
        colls[k] = c
        done.append(f"nayi list {k} ({len(c['fields'])} field)")
    for a in (ops.get("add") or [])[:12]:
        c = colls.get(str(a.get("coll") or ""))
        if c is None:
            raise W.AppError(f"List '{a.get('coll')}' is app mein nahi hai.")
        k = W._slug(a.get("key") or a.get("label"))
        if not k or k in ("id", "owner", "created", "updated", "cid", "cart"):
            raise W.AppError("Naye field ka naam chahiye.")
        if any(f["key"] == k for f in c["fields"]):
            old = next(f for f in c["fields"] if f["key"] == k)
            if old.get("hidden"):              # bringing a hidden field back
                old.pop("hidden", None)
                done.append(f"{c['key']}.{k} wapas dikhega")
                continue
            raise W.AppError(f"'{k}' pehle se hai.")
        if len(c["fields"]) >= W.MAX_FIELDS:
            raise W.AppError("Is list mein aur field nahi aa sakte.")
        fd = _new_field({**a, "key": k}, colls, fresh=False)
        c["fields"].append(fd)
        done.append(f"{c['key']}.{k} joda")
    for h in (ops.get("hide") or [])[:12]:
        c = colls.get(str(h.get("coll") or ""))
        f = next((x for x in (c or {}).get("fields", []) if x["key"] == h.get("key")), None)
        if f is None:
            raise W.AppError(f"Field '{h.get('key')}' nahi mila.")
        if f["key"] in ("status", "name", "phone", "items", "total") and c and c["key"] == sch.get("order"):
            raise W.AppError(f"'{f['key']}' order ke liye zaroori hai; chhupa nahi sakte.")
        f["hidden"], f["required"] = True, False
        done.append(f"{c['key']}.{f['key']} chhupa (data rakha hai)")
    for lb in (ops.get("label") or [])[:12]:
        c = colls.get(str(lb.get("coll") or ""))
        f = next((x for x in (c or {}).get("fields", []) if x["key"] == lb.get("key")), None)
        if f is None or not str(lb.get("label") or "").strip():
            raise W.AppError("Kaunsa field, naya naam kya?")
        f["label"] = str(lb["label"])[:60]
        done.append(f"{c['key']}.{f['key']} ka naam '{f['label']}'")
    return done


def _new_field(a: dict[str, Any], colls: dict[str, Any], fresh: bool) -> dict[str, Any] | None:
    """One field from an add / add_list op. On an EXISTING list a new field is never required (old apps cannot send it);
    on a brand-new list it may be. v0.382 type "ref" + "to" = a link to a row of another list."""
    k = W._slug(a.get("key") or a.get("label"))
    if not k or k in ("id", "owner", "created", "updated", "cid", "cart") or k.startswith("_"):
        if fresh:
            return None
        raise W.AppError("Naye field ka naam chahiye.")
    typ = a.get("type") if a.get("type") in (*W.TYPES, *EXTRA_TYPES, "ref") else "text"
    fd: dict[str, Any] = {"key": k, "label": str(a.get("label") or k.replace("_", " ").title())[:60], "type": typ,
                          "required": bool(a.get("required")) and fresh and typ != "choice", "admin_only": bool(a.get("admin_only"))}
    if a.get("private") is True:            # v0.434 per-field rule: only staff / her see it (row_view hides it from others)
        fd["private"], fd["admin_only"] = True, True
    if typ == "choice":
        opts = [str(o)[:40] for o in (a.get("options") or []) if str(o).strip()][:20]
        if not opts:
            raise W.AppError("Choice field ke options chahiye.")
        fd["options"], fd["default"] = opts, opts[0]          # an old app's row (it never sends it) gets the default
    if typ == "ref":
        to = W._slug(a.get("to"))
        if to not in colls:
            raise W.AppError(f"'{k}' kis list se juda hai? ('{a.get('to')}' nahi mili)")
        fd["to"] = to
    return fd


def change_schema(r: AppProject, ops: dict[str, Any], words: str = "") -> dict[str, Any]:
    """Her data change (tool / app data view): applied to a copy, checked, then saved with a new revision. The installed
    app reads the new lists from /api/app-content at once (rows show the new field); forms collect it from the next build."""
    import copy
    ensure(r)
    out: dict[str, Any] = {}

    def change(be):                                  # v0.390 applied to the backend as it is NOW, under the app's lock
        sch = copy.deepcopy(be["schema"])
        done = _apply_ops(sch, ops if isinstance(ops, dict) else {})
        if not done:
            raise W.AppError("Kya badalna hai? (add / hide / label / add_list)")
        be["schema"], be["rev"] = sch, int(be.get("rev") or 0) + 1
        be["changes"] = (be.get("changes") or []) + [{"at": now().isoformat(), "ops": ops, "words": str(words)[:300], "done": done}]
        out["done"] = done
    try:                                                  # v0.390 a schema change is a moment worth a backup
        from . import backup as BK
        BK.snapshot(r, "before a data change" + (f": {str(words)[:60]}" if words else ""))
    except Exception:                                    # noqa: BLE001
        log.debug("snapshot", exc_info=True)
    be = patch_backend(r, fn=change)
    done = out["done"]
    try:
        from .android import service as AN
        AN._CACHE.clear() if hasattr(AN, "_CACHE") else None
    except Exception:                                    # noqa: BLE001
        pass
    return {"rev": be["rev"], "done": done, "say": "; ".join(done) + ". Rows mein abhi dikhega; form mein agli build se."}


# ---------------------------------------------------------------- v0.352 KAAM BAANTO (App Sahayak Phase 16)
# A row (job / order / booking / request) is given to ONE staff member. The assignment lives inside the row's own data
# (`_to` member id, `_to_name`, `_to_at` when) - never a schema field, so a customer can never set it and old rows just
# read "not assigned". Who may do what (checked here on every call, the phone only shows the buttons):
#   * the owner (her Hoola) and an admin account: give any row to any staff / admin account, take it back, move it;
#   * a staff account: TAKE an unassigned row for itself ("I'll take it") or give back its own - never someone else's;
#   * a staff account cannot change a row that is with someone else (status, fields) - an admin / the owner still can;
#   * the customer who made the row sees only the first name of the person on it ("Ravi is on it"), never ids / e-mails.
ASSIGN_KEY = "_assign"
STATS.update({"assigned": 0, "assign_refused": 0})


def _staff_of(site: str) -> dict[str, W.SiteAppMember]:
    with session() as s:
        got = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == site,
                                                      W.SiteAppMember.role.in_(("staff", "admin")))).all()
        for m in got:
            s.expunge(m)
    return {m.id: m for m in got}


def _first(name: str, email: str = "") -> str:
    n = (name or "").strip() or (email or "").split("@")[0]
    return (n.split() or ["Staff"])[0][:30]


def _is_admin(w: W.Who) -> bool:
    return w.owner or bool(w.m and w.m.role == "admin")


def team(r: AppProject, w: W.Who) -> dict[str, Any]:
    """The staff list the app shows on its assign buttons: names only (no e-mails), staff accounts only, + each one's open
    rows count. `admin` = this account may give rows to others."""
    if w.m is None and not w.owner:
        raise W.AppError("Pehle login kijiye.", 401)
    if not w.staff:
        raise W.AppError("Yeh sirf staff ke liye hai.", 403)
    site = bid(r)
    load = _load(r)
    people = [{"id": m.id, "name": _first(m.name, m.email), "role": m.role, "open": load.get(m.id, 0)}
              for m in _staff_of(site).values()]
    people.sort(key=lambda p: (p["name"].lower(), p["id"]))
    return {"team": people, "admin": _is_admin(w), "me": w.id}


def _closed(st: str) -> bool:
    return st.strip().lower() in ("done", "delivered", "cancelled", "closed", "completed", "expired", "replied")


def _load(r: AppProject) -> dict[str, int]:
    """Open (not done / cancelled) rows per staff member."""
    out: dict[str, int] = {}
    with session() as s:
        for (data,) in s.query(W.SiteAppRow.data).filter(W.SiteAppRow.site_id == bid(r),
                                                          W.SiteAppRow.data.like('%"_to": "%')).all():
            d = _j(data, {})
            if d.get("_to") and not _closed(str(d.get("status") or "")):
                out[d["_to"]] = out.get(d["_to"], 0) + 1
    return out


def _assign_info(site: str, ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    with session() as s:
        got = s.query(W.SiteAppRow.id, W.SiteAppRow.data).filter(W.SiteAppRow.site_id == site, W.SiteAppRow.id.in_(ids)).all()
    return {i: _j(d, {}) for i, d in got}


def with_assign(r: AppProject, out: list[dict[str, Any]] | dict[str, Any], w: W.Who):
    """Adds who a row is with: staff see `assigned_to` (id) + `assigned_name`; the row's own customer only the first name."""
    one = isinstance(out, dict)
    rows_ = [out] if one else list(out)
    info = _assign_info(bid(r), [x.get("id") for x in rows_ if x.get("id")])
    own_keys = {f["key"] for c in schema(r)["collections"] for f in c["fields"]}
    kind = ""
    if any(receipt_ready(info.get(x.get("id"), {})) for x in rows_):
        from . import gst as G
        kind = "invoice" if G.on(r) else "receipt"          # v0.355 the app's button says Invoice for a GST business
    for x in rows_:
        d = info.get(x.get("id"), {})
        to = str(d.get("_to") or "")
        if w.staff:
            x["assigned_to"], x["assigned_name"] = to, (str(d.get("_to_name") or "") if to else "")
        elif x.get("mine") and to:
            x["assigned_name"] = str(d.get("_to_name") or "")
        if (w.staff or x.get("mine")) and d.get("_khata"):     # v0.359 KHATA: this order was given on credit
            x["on_credit"] = not d.get("_khata_back")
        if w.staff or x.get("mine"):                  # v0.358 COUPON: what the server took off (or why a code did not apply)
            own = own_keys
            for k in SYS_KEYS:                          # stored as "_k"; shown as "k" unless her list has its own field "k"
                v = d.get("_" + k)
                if v not in (None, ""):
                    x["_" + k] = v
                    if k not in own:
                        x[k] = v
        if w.staff or x.get("mine"):                  # v0.353 RAAY: the customer's rating, for her and the business
            if d.get("_rate"):
                x["rating"], x["rating_note"] = int(d["_rate"]), str(d.get("_rate_note") or "")
            x["receipt"] = receipt_ready(d)            # v0.354 RASEED: a receipt PDF can be had for this row
            if x["receipt"]:
                x["receipt_kind"] = "credit_note" if d.get("_cn_no") else kind      # v0.356
            x["can_rate"] = bool(x.get("mine") and not w.staff and not d.get("_rate") and _rateable(str(d.get("status") or "")))
    return rows_[0] if one else rows_


def _guard_assigned(r: AppProject, coll: str, row_id: str, w: W.Who) -> dict[str, Any]:
    """A staff account may not change a row that is with someone else (admin / owner may)."""
    d = _assign_info(bid(r), [row_id]).get(row_id, {})
    to = str(d.get("_to") or "")
    if to and w.staff and not _is_admin(w) and to != w.id:
        STATS["assign_refused"] += 1
        raise W.AppError(f"Yeh kaam {d.get('_to_name') or 'kisi aur'} ke paas hai.", 403)
    return d


def assign(r: AppProject, coll: str, row_id: str, to: str, w: W.Who) -> dict[str, Any]:
    """Give a row to a staff member (`to` = member id), take it ("me"), or give it back (""). Rules above."""
    sch, site = schema(r), bid(r)
    c = W.coll(sch, coll)
    if w.m is None and not w.owner:
        raise W.AppError("Pehle login kijiye.", 401)
    if not w.staff:
        raise W.AppError("Iski ijaazat nahi.", 403)
    to = str(to or "").strip()
    if to == "me":
        if w.m is None:
            raise W.AppError("Aap staff account nahi hain; kisi staff ko chuniye.")
        to = w.m.id
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != site or row.coll != coll:
            raise W.AppError("Yeh entry nahi mili.", 404)
        d = _j(row.data, {})
        cur = str(d.get("_to") or "")
        if not _is_admin(w):
            ok = (to == w.id and cur in ("", w.id)) or (to == "" and cur == w.id)
            if not ok:
                STATS["assign_refused"] += 1
                raise W.AppError(f"Yeh kaam {d.get('_to_name') or 'kisi aur'} ke paas hai; admin hi badal sakta hai." if cur
                                 else "Staff sirf khud ke liye kaam le sakta hai.", 403)
        if to:
            team_ = _staff_of(site)
            m = team_.get(to)
            if m is None and _is_admin(w):           # her words name a person ("Ravi ko do"): one staff member by name
                hit = [x for x in team_.values() if to.lower() in ((x.name or "").lower(), _first(x.name, x.email).lower(),
                                                                   (x.email or "").lower())]
                m = hit[0] if len(hit) == 1 else None
            if m is None:
                raise W.AppError("Yeh staff account nahi mila (pehle use staff banaiye).", 404)
            d.update({"_to": m.id, "_to_name": _first(m.name, m.email), "_to_at": now().isoformat(), "_ev": now().isoformat()})
        else:
            for k in ("_to", "_to_name", "_to_at"):
                d.pop(k, None)
        row.data, row.updated_at = json.dumps(d, ensure_ascii=False), now()
        s.flush()
        s.expunge(row)
    STATS["assigned"] += 1
    if to and to != w.id:                              # v0.367 TURANT: the person it was given to hears it at once
        try:
            from . import turant as TU
            TU.later(r, [to], "Given to you", c["label"] + " " + row_id[-6:].upper(), row_id)
        except Exception:
            log.debug("turant assign", exc_info=True)
    return with_assign(r, W.row_view(c, row, w), w)


def _unassigned(r: AppProject) -> int:
    """Open rows nobody has yet, in the lists that have a status (the work still to hand out)."""
    sch = schema(r)
    keys = [c["key"] for c in sch["collections"] if any(f["key"] == "status" for f in c["fields"])]
    if not keys:
        return 0
    n = 0
    with session() as s:
        for (data,) in s.query(W.SiteAppRow.data).filter(W.SiteAppRow.site_id == bid(r), W.SiteAppRow.coll.in_(keys)).all():
            d = _j(data, {})
            n += int(not d.get("_to") and not _closed(str(d.get("status") or "")))
    return n


def owner_assign(r: AppProject, coll: str, row_id: str, to: str) -> dict[str, Any]:
    return assign(r, coll, row_id, to, W.Who(owner=True))


# ---------------------------------------------------------------- v0.353 RAAY (App Sahayak Phase 17): the customer's rating
# Once her row is finished (Done / Delivered / Completed - never a cancelled one) the customer who made it rates it ONCE:
# 1-5 stars + a short note (300 chars, control characters stripped). Kept inside the row (`_rate`, `_rate_note`, `_rate_at`,
# and `_rate_to` = who had the job then), so the dashboard can show the average per list and per staff member. Nobody else
# can rate (not staff, not another customer, not the owner), a rating is never changed, and a low one (1-2 stars) reaches
# her chat at once so she can call the customer. Never shown to other customers (no public reviews here).
RATE_KEY = "_rate"
RATE_LOW = 2
STATS.update({"ratings": 0, "rating_refused": 0, "rating_low": 0})


def receipt_ready(d: dict[str, Any]) -> bool:
    """v0.354 a receipt is made for a finished row or a Verified UPI payment, never for a cancelled one
    (v0.356 except its credit note, when the cancelled row had a tax invoice)."""
    if d.get("_cn_no"):
        return True
    st = str(d.get("status") or "")
    return st.strip().lower() != "cancelled" and (_rateable(st) or str(d.get("paid") or "") == "Verified")


def _rateable(st: str) -> bool:
    return st.strip().lower() in ("done", "delivered", "completed", "closed", "replied", "confirmed", "active", "enrolled")


def rate(r: AppProject, coll: str, row_id: str, stars: Any, note: str, w: W.Who) -> dict[str, Any]:
    sch, site = schema(r), bid(r)
    c = W.coll(sch, coll)
    if w.m is None:
        raise W.AppError("Pehle login kijiye.", 401)
    try:
        f = float(str(stars).strip())
    except (TypeError, ValueError):
        f = 0.0
    n = int(f)
    if isinstance(stars, bool) or f != n or not 1 <= n <= 5:
        raise W.AppError("Stars 1 se 5 tak.")
    note = re.sub(r"[\x00-\x1f\x7f]+", " ", str(note or "")).strip()[:300]
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != site or row.coll != coll:
            raise W.AppError("Yeh entry nahi mili.", 404)
        d = _j(row.data, {})
        if row.owner != w.m.id:
            STATS["rating_refused"] += 1
            raise W.AppError("Sirf jisne yeh entry bheji, wahi rating de sakta hai.", 403)
        if d.get("_rate"):
            STATS["rating_refused"] += 1
            raise W.AppError("Rating pehle hi di ja chuki hai.", 409)
        if not _rateable(str(d.get("status") or "")):
            STATS["rating_refused"] += 1
            raise W.AppError("Kaam poora hone ke baad rating dijiye.", 409)
        d.update({"_rate": n, "_rate_note": note, "_rate_at": now().isoformat(), "_rate_to": d.get("_to", "")})
        row.data, row.updated_at = json.dumps(d, ensure_ascii=False), now()
        s.flush()
        s.expunge(row)
    STATS["ratings"] += 1
    if n <= RATE_LOW:
        STATS["rating_low"] += 1
        what = NEWS.get(coll, c["label"].lower())
        who_ = str(d.get("name") or d.get("customer") or w.m.name or "").strip()[:40]
        text = (f"{r.name or 'Aapki app'} ({r.number}): {who_ or 'ek customer'} ne apni {what} ko {n}/5 diya"
                + (f" - \"{note[:120]}\"" if note else "") + (f" (kaam {d.get('_to_name')} ke paas tha)" if d.get("_to_name") else "")
                + ". Unse baat kar lijiye.")
        try:
            from .android.service import _note
            _note(r, text)
        except Exception:
            log.debug("low rating note", exc_info=True)
    return with_assign(r, W.row_view(c, row, w), w)


def _ratings(r: AppProject) -> dict[str, dict[str, list[int]]]:
    lists: dict[str, list[int]] = {}
    people: dict[str, list[int]] = {}
    with session() as s:
        for coll, data in s.query(W.SiteAppRow.coll, W.SiteAppRow.data).filter(
                W.SiteAppRow.site_id == bid(r), W.SiteAppRow.data.like('%"_rate": %')).all():
            d = _j(data, {})
            try:
                n = int(d.get("_rate") or 0)
            except (TypeError, ValueError):
                continue
            if 1 <= n <= 5:
                lists.setdefault(coll, []).append(n)
                if d.get("_rate_to"):
                    people.setdefault(d["_rate_to"], []).append(n)
    return {"lists": lists, "people": people}



def _stock_back(r: AppProject, row_id: str) -> None:
    """v0.357 the quantities a cancelled order took go back to stock, once (`_stock_back` marks it)."""
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        d = _j(row.data, {}) if row is not None else {}
        if not d.get("_stock") or d.get("_stock_back"):
            return
        taken = d["_stock"]
        d["_stock_back"] = True
        row.data = json.dumps(d, ensure_ascii=False)
    from . import stock as SK
    SK.put_back(r, [(str(p), int(q)) for p, q in taken])



def _coupon_back(r: AppProject, row_id: str) -> None:
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        d = _j(row.data, {}) if row is not None else {}
        if not d.get("_discount") or not d.get("_coupon") or d.get("_coupon_back"):
            return
        d["_coupon_back"] = True
        row.data = json.dumps(d, ensure_ascii=False)
        code, who = d["_coupon"], row.owner
    from . import coupon as CP
    CP.give_back(r, code, who)
