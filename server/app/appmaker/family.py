"""v0.435 PARIVAAR (App Sahayak Pillar H, Phases 58-59): one business, several apps, one backend + a web admin.

A real product is a SET of apps on the same data - the customer app, a delivery partner app, a partner shop (restaurant /
seller / branch) app, a staff app - and an admin website for the business. Here:

  * A FACE is its own App Sahayak project (its own plan card, looks, design she approves, Android / iPhone builds, store
    listing, package name), marked `plan.face = {of: <the main app>, kind}`. Every backend call made with a face's app_key
    lands on the MAIN app's backend (backend.by_key -> home()): one set of accounts, lists, rows, logic, payments,
    connectors, live stream. Nothing is copied, so nothing can drift.
  * PARTNERS are a role of their own, checked in CODE on every call (never by the app's screens):
      - rider (delivery partner): sees open jobs that are READY for pickup (offers) without the customer's phone, takes
        one (first tap wins, under a lock), then sees that job in full and may move it only through her rider steps
        (Picked up -> Out for delivery -> Delivered); the shift + live location of Pillar D work for riders too.
      - vendor (partner shop): is linked to ONE row of her partner list (a restaurant, a seller); sees only the orders
        that point at that row - never the customer's phone / e-mail / location - moves them only through her vendor
        steps (Accepted -> Preparing -> Ready), and keeps its own menu rows (lists that point at its row) itself.
    A partner is approved by her (or an app admin), never by the app: a sign-up in the rider app is only an application.
  * The WEB ADMIN (`/app-admin/<app_key>`): a website for her staff / admins on the same backend - every list with
    search, filters, edit, status, assign, CSV export, dashboard numbers, partner approvals and member roles. Staff-only
    rules are the server's, so the page can never show what the account may not see.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import threading
import time
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"faces": 0, "requests": 0, "approved": 0, "refused": 0, "taken": 0, "take_lost": 0, "steps": 0,
         "denied": 0, "exports": 0}

KINDS: dict[str, dict[str, Any]] = {
    "rider": {"label": "Delivery partner app", "short": "Partner", "role": "partner",
              "brief": "A delivery partner (rider) app: the rider signs in, starts a shift, sees new deliveries ready for "
                       "pickup, takes one, goes to the shop, then to the customer, and marks it delivered; earnings and "
                       "past deliveries"},
    "vendor": {"label": "Partner shop app", "short": "Partner Shop", "role": "partner",
               "brief": "A partner shop app (restaurant / seller / branch on the platform): the shop signs in, sees new "
                        "orders for its own shop, accepts, prepares and marks them ready for pickup, and keeps its own "
                        "menu / items and opening status"},
    "staff": {"label": "Staff app", "short": "Staff", "role": "staff",
              "brief": "A staff / operations app for the business team: every order and request, assign work, change "
                       "status, customers, dashboard"},
    "customer": {"label": "Customer app", "short": "", "role": "member",
                 "brief": "The customer app: browse, order / book, pay, track, rate"},
}
PARTNER_KINDS = ("rider", "vendor")
RIDER_OFFER = ("ready", "ready for pickup", "packed", "accepted", "confirmed", "prepared")
RIDER_STEPS = ("picked", "picked up", "out for delivery", "on the way", "shipped", "delivered", "completed")
VENDOR_STEPS = ("accepted", "confirmed", "preparing", "in kitchen", "packed", "ready", "ready for pickup", "rejected",
                "cancelled")
LIMITED_TYPES = ("phone", "email", "location")          # never shown to a partner shop; to a rider only on HIS job
PROOF_TYPES = ("signature", "photo", "photos")          # a rider may attach proof of delivery
RIDER_MAX = 3                                           # open jobs one rider may hold at a time (her setting)
SCAN = 3000


class FamilyError(W.AppError):
    pass


class AppPartner(Base):
    """One application / approval per account and kind. active: 0 waiting, 1 approved, -1 refused, -2 removed."""
    __tablename__ = "app_partner"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ptr"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    member: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="rider")
    name: Mapped[str] = mapped_column(String(120), default="")
    link_coll: Mapped[str] = mapped_column(String(40), default="")
    link_row: Mapped[str] = mapped_column(String(40), default="")
    active: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_OK = False


def ensure_table() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        AppPartner.__table__.create(_db._engine, checkfirst=True)
        _OK = True


def _j(s: Any, d: Any) -> Any:
    if isinstance(s, (dict, list)):
        return s
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def _site(r: AppProject) -> str:
    return "app:" + r.id


def _first(name: str) -> str:
    return (str(name or "").strip().split(" ") or [""])[0][:30]


# ---------------------------------------------------------------- faces: which app is which, and whose backend it uses
def face_info(r: AppProject) -> dict[str, Any] | None:
    if '"face"' not in (r.plan or ""):                    # every app_key request passes here: no JSON parse for most apps
        return None
    f = _j(r.plan, {}).get("face")
    return f if isinstance(f, dict) and f.get("of") and f.get("kind") in KINDS else None


def home(r: AppProject) -> AppProject:
    """The app whose backend this app uses: the main app for a face, itself otherwise."""
    f = face_info(r)
    if not f:
        return r
    with session() as s:
        p = s.get(AppProject, f["of"])
        if p is None or p.tenant_id != r.tenant_id:
            return r
        s.expunge(p)
    return p


_KEYFACE: dict[str, tuple[float, str]] = {}
_LOCK = threading.Lock()


def note_key(app_key: str, r: AppProject) -> None:
    """backend.by_key tells us which face an app_key belongs to (the rider app's key -> 'rider')."""
    f = face_info(r)
    with _LOCK:
        _KEYFACE[app_key] = (time.time(), f["kind"] if f else "")


def kind_for_key(app_key: str) -> str:
    with _LOCK:
        hit = _KEYFACE.get(app_key)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    from . import backend as BE
    try:
        BE.by_key(app_key)
    except W.AppError:
        return ""
    with _LOCK:
        hit = _KEYFACE.get(app_key)
    return hit[1] if hit else ""


def faces(r: AppProject) -> list[dict[str, Any]]:
    """The apps on this backend (the main one first)."""
    r = home(r)
    out = [{"kind": "main", "app": r.id, "number": r.number, "name": r.name, "status": r.status,
            "android": _j(r.android, {}).get("status", ""), "app_key": _j(r.android, {}).get("app_key", "")}]
    with session() as s:
        rows = s.query(AppProject).filter(AppProject.tenant_id == r.tenant_id,
                                          AppProject.plan.like(f'%"of": "{r.id}"%')).all()
        for x in rows:
            s.expunge(x)
    for x in sorted(rows, key=lambda y: y.number):
        f = face_info(x)
        if f and f["of"] == r.id:
            out.append({"kind": f["kind"], "label": KINDS[f["kind"]]["label"], "app": x.id, "number": x.number,
                        "name": x.name, "status": x.status, "android": _j(x.android, {}).get("status", ""),
                        "app_key": _j(x.android, {}).get("app_key", "")})
    return out


def add_face(tenant: str, ref: str, kind: str, words: str = "", conv: str = "") -> dict[str, Any]:
    """Her tap / words 'rider app bhi banao': a new app project on the SAME backend. It gets the normal plan card ->
    3 looks -> design she approves -> build; only its data is the main app's."""
    from . import backend as BE
    from . import service as AS
    kind = str(kind or "").strip().lower()
    if kind not in KINDS:
        raise FamilyError("Kaunsi app? rider (delivery partner), vendor (partner shop), staff ya customer.")
    p = home(BE.by_key_or_ref(tenant, ref))
    if face_info(p):
        raise FamilyError("Yeh app khud kisi aur app ka hissa hai; main app chuniye.")
    for f in faces(p)[1:]:
        if f["kind"] == kind:
            return {**f, "existing": True, "say": f"{KINDS[kind]['label']} pehle se hai: app {f['number']} ({f['status']})."}
    if kind in PARTNER_KINDS:
        problem = _partner_problem(p, kind)
        if problem:
            raise FamilyError(problem)
    brief = (f"{KINDS[kind]['brief']}, for the business '{p.name or 'the main app'}' (app {p.number}). It uses the SAME "
             f"accounts and data as app {p.number}. {str(words or '').strip()}")[:1900]
    name = (f"{p.name} {KINDS[kind]['short']}".strip() if KINDS[kind]["short"] else p.name)[:60] or KINDS[kind]["label"]
    try:
        made = AS.new(tenant, brief, conv, name=name, field=p.field, goal=p.goal, answers={"sure": True}, quiet=True)
    except AS.AppError as e:
        raise FamilyError(str(e)) from e
    with session() as s:
        x = s.get(AppProject, made["id"])
        plan = _j(x.plan, {})
        plan["face"] = {"of": p.id, "kind": kind, "at": now().isoformat()}
        x.plan = json.dumps(plan, ensure_ascii=False)
        facts = {**_j(p.facts, {}), "name": name}                 # the same business: phone, address, UPI...
        x.facts = json.dumps(facts, ensure_ascii=False)
        x.name = name
        x.language = p.language or x.language
        x.conv = conv or p.conv or x.conv
        s.flush()
        s.expunge(x)
    STATS["faces"] += 1
    AS._emit(x, push=True)
    v = AS.view(x)
    v["face"] = {"of": p.id, "of_number": p.number, "kind": kind, "label": KINDS[kind]["label"]}
    v["say"] = (f"{KINDS[kind]['label']} ka plan taiyaar: app {x.number} ({name}). Data, accounts aur orders app {p.number} "
                "wale hi rahenge - kuch copy nahi hota. Plan dekh kar Haan kahiye, phir looks aur design.")
    return v


# ---------------------------------------------------------------- her settings (in the main app's backend JSON)
def _status_field(c: dict[str, Any]) -> dict[str, Any] | None:
    return next((f for f in c.get("fields") or [] if f.get("key") == "status"), None)


def _options(c: dict[str, Any]) -> list[str]:
    f = _status_field(c) or {}
    return [str(o) for o in (f.get("options") or []) if str(o).strip()]


def _jobs_coll(sch: dict[str, Any]) -> str:
    order = str(sch.get("order") or "")
    colls = sch.get("collections") or []
    if order and any(c["key"] == order for c in colls):
        return order
    return next((c["key"] for c in colls if _options(c)), "")


def _refs(c: dict[str, Any], to: str = "") -> list[str]:
    return [f["key"] for f in c.get("fields") or [] if f.get("type") == "ref" and (not to or f.get("to") == to)]


def _pick(opts: list[str], want: tuple[str, ...]) -> list[str]:
    return [o for o in opts if o.strip().lower() in want]


def settings(r: AppProject) -> dict[str, Any]:
    """Her rules for each partner kind, with honest defaults from the app's own lists and status words."""
    from . import backend as BE
    r = home(r)
    sch = BE.schema(r)
    saved = _j(r.backend, {}).get("family") or {}
    colls = {c["key"]: c for c in sch.get("collections") or []}
    jobs = saved.get("jobs") if saved.get("jobs") in colls else _jobs_coll(sch)
    opts = _options(colls[jobs]) if jobs else []
    rider = dict(saved.get("rider") or {})
    vendor = dict(saved.get("vendor") or {})
    link = vendor.get("link") if vendor.get("link") in colls else ""
    if not link and jobs:
        tos = [f.get("to") for f in colls[jobs].get("fields") or [] if f.get("type") == "ref" and f.get("to") in colls]
        link = tos[0] if tos else ""
    out = {
        "jobs": jobs, "statuses": opts,
        "rider": {"offer": [o for o in rider.get("offer", _pick(opts, RIDER_OFFER)) if o in opts],
                  "steps": [o for o in rider.get("steps", _pick(opts, RIDER_STEPS)) if o in opts],
                  "max": max(1, min(int(rider.get("max") or RIDER_MAX), 20))},
        "vendor": {"link": link, "ref": (_refs(colls[jobs], link)[:1] or [""])[0] if jobs and link else "",
                   "steps": [o for o in vendor.get("steps", _pick(opts, VENDOR_STEPS)) if o in opts],
                   "lists": [k for k, c in colls.items() if link and k not in (jobs, link) and _refs(c, link)]},
    }
    return out


def save_settings(r: AppProject, body: dict[str, Any]) -> dict[str, Any]:
    from . import backend as BE
    r = home(r)
    cur = settings(r)
    body = body if isinstance(body, dict) else {}
    sch = BE.schema(r)
    colls = {c["key"]: c for c in sch.get("collections") or []}
    fam: dict[str, Any] = {}
    jobs = str(body.get("jobs") or cur["jobs"])
    if jobs and jobs not in colls:
        raise FamilyError("Yeh list app mein nahi hai.")
    fam["jobs"] = jobs
    opts = _options(colls[jobs]) if jobs else []
    moved = jobs != cur["jobs"]                                # another list: its own status words, not the old list's
    fresh = {("rider", "offer"): _pick(opts, RIDER_OFFER), ("rider", "steps"): _pick(opts, RIDER_STEPS),
             ("vendor", "steps"): _pick(opts, VENDOR_STEPS)}
    for kind, keys in (("rider", ("offer", "steps")), ("vendor", ("steps",))):
        src = body.get(kind) if isinstance(body.get(kind), dict) else {}
        part: dict[str, Any] = {}
        for k in keys:
            vals = src.get(k, fresh[(kind, k)] if moved else cur[kind][k])
            if not isinstance(vals, list):
                raise FamilyError(f"{kind}.{k}: status ki list chahiye.")
            bad = [v for v in vals if v not in opts]
            if bad:
                raise FamilyError(f"Yeh status list mein nahi: {', '.join(map(str, bad[:3]))}. Status: {', '.join(opts)}.")
            part[k] = [str(v) for v in vals][:12]
        if kind == "rider":
            part["max"] = max(1, min(int(src.get("max") or cur["rider"]["max"]), 20))
            if set(part["offer"]) & set(part["steps"]):
                raise FamilyError("Ek status 'naye kaam' aur 'rider ke kadam' dono mein nahi ho sakta.")
        if kind == "vendor":
            link = str(src.get("link") or ("" if moved else cur["vendor"]["link"]) or "")
            if not link and jobs:
                tos = [f.get("to") for f in colls[jobs].get("fields") or [] if f.get("type") == "ref" and f.get("to") in colls]
                link = tos[0] if tos else ""
            if link and (link not in colls or not _refs(colls.get(jobs) or {}, link)):
                raise FamilyError(f"'{jobs}' list mein '{link}' ka link (ref) field nahi hai; pehle woh field jodiye.")
            part["link"] = link
        fam[kind] = part
    BE.patch_backend(r, set_={"family": fam})
    return settings(r)


def _partner_problem(r: AppProject, kind: str) -> str:
    st = settings(r)
    if not st["jobs"]:
        return "Is app mein order / kaam ki koi list nahi jisme status ho; partner app ke liye pehle woh chahiye."
    if not st["statuses"]:
        return f"'{st['jobs']}' list mein status nahi hai."
    if kind == "vendor" and not (st["vendor"]["link"] and st["vendor"]["ref"]):
        return (f"Partner shop app ke liye '{st['jobs']}' list mein dukaan / restaurant ka link (ref) field chahiye "
                "(jaise orders -> restaurants). App ke data mein 'restaurants' list aur order mein uska link jodiye, phir.")
    return ""


# ---------------------------------------------------------------- partners: application, her approval, who is who
def partner(r: AppProject, w: W.Who) -> AppPartner | None:
    """The approved partner record of this account, or None (customers, staff, the owner)."""
    if w.owner or w.m is None or (w.m.role or "") != "partner":
        return None
    ensure_table()
    r = home(r)
    with session() as s:
        p = s.scalars(select(AppPartner).where(AppPartner.site_id == _site(r), AppPartner.member == w.m.id,
                                               AppPartner.active == 1)).first()
        if p is not None:
            s.expunge(p)
    return p


def is_partner(w: W.Who) -> bool:
    return bool(w.m is not None and not w.owner and (w.m.role or "") == "partner")


def is_rider(r: AppProject, w: W.Who) -> bool:
    p = partner(r, w) if is_partner(w) else None
    return bool(p and p.kind == "rider")


def _pview(p: AppPartner, link_name: str = "", email: str = "") -> dict[str, Any]:
    return {"id": p.id, "member": p.member, "kind": p.kind, "label": KINDS.get(p.kind, {}).get("label", p.kind),
            "name": p.name, "email": email, "link_coll": p.link_coll, "link_row": p.link_row, "link_name": link_name,
            "state": {1: "approved", 0: "waiting", -1: "refused", -2: "removed"}.get(p.active, "waiting"),
            "since": p.created_at.isoformat() if p.created_at else ""}


def _row_name(site: str, row_id: str) -> str:
    if not row_id:
        return ""
    with session() as s:
        x = s.get(W.SiteAppRow, row_id)
        if x is None or x.site_id != site:
            return ""
        d = _j(x.data, {})
    return str(d.get("name") or d.get("title") or d.get("shop") or row_id[-6:].upper())[:80]


def request(r: AppProject, w: W.Who, kind: str) -> dict[str, Any]:
    """'Partner banna hai': an application from the rider / shop app. Only she (or an app admin) can approve it."""
    r = home(r)
    if w.m is None:
        raise FamilyError("Pehle login kijiye.", 401)
    if kind not in PARTNER_KINDS:
        raise FamilyError("Yeh app partner app nahi hai.", 400)
    if (w.m.role or "") in ("staff", "admin"):
        raise FamilyError("Staff account partner nahi ban sakta; alag account banaiye.", 409)
    ensure_table()
    W.rate(f"ptr-req:{_site(r)}:{w.m.id}", 5, 3600)
    with session() as s:
        p = s.scalars(select(AppPartner).where(AppPartner.site_id == _site(r), AppPartner.member == w.m.id,
                                               AppPartner.kind == kind)).first()
        if p is None:
            p = AppPartner(site_id=_site(r), member=w.m.id, kind=kind, name=(w.m.name or w.m.email.split("@")[0])[:120])
            s.add(p)
            fresh = True
        else:
            fresh = p.active in (-1, -2)
            if fresh:
                p.active, p.decided_at = 0, None
        s.flush()
        s.expunge(p)
    if fresh:
        STATS["requests"] += 1
        try:
            from .android.service import _note
            _note(r, f"{r.name or 'Aapki app'} ({r.number}): {p.name} ne {KINDS[kind]['label']} ke liye arzi di. "
                     "App ke Parivaar box ya web admin mein Haan / Na kijiye.")
        except Exception:
            log.debug("partner note", exc_info=True)
    return me(r, w, kind)


def me(r: AppProject, w: W.Who, kind: str = "") -> dict[str, Any]:
    r = home(r)
    if w.m is None:
        return {"state": "login", "kind": kind}
    ensure_table()
    with session() as s:
        q = select(AppPartner).where(AppPartner.site_id == _site(r), AppPartner.member == w.m.id)
        if kind:
            q = q.where(AppPartner.kind == kind)
        p = s.scalars(q.order_by(AppPartner.created_at.desc())).first()
        if p is not None:
            s.expunge(p)
    if p is None:
        return {"state": "none", "kind": kind, "label": KINDS.get(kind, {}).get("label", "")}
    v = _pview(p, _row_name(_site(r), p.link_row))
    if p.active == 1 and (w.m.role or "") != "partner":
        v["state"] = "removed"
    return v


def partners(r: AppProject, state: str = "") -> list[dict[str, Any]]:
    r = home(r)
    ensure_table()
    with session() as s:
        got = s.scalars(select(AppPartner).where(AppPartner.site_id == _site(r)).order_by(AppPartner.created_at.desc())
                        .limit(2000)).all()
        mem = {m.id: m.email for m in s.scalars(select(W.SiteAppMember).where(
            W.SiteAppMember.site_id == _site(r), W.SiteAppMember.id.in_([p.member for p in got] or ["-"]))).all()}
        for p in got:
            s.expunge(p)
    out = [_pview(p, _row_name(_site(r), p.link_row), mem.get(p.member, "")) for p in got]
    return [x for x in out if not state or x["state"] == state]


def _set_role(site: str, member: str, role: str, logout: bool) -> None:
    with session() as s:
        m = s.get(W.SiteAppMember, member)
        if m is None or m.site_id != site:
            raise FamilyError("Yeh account nahi mila.", 404)
        if m.role in ("staff", "admin") and role == "partner":
            raise FamilyError("Staff / admin account partner nahi ban sakta.", 409)
        m.role = role
        if logout:
            m.gen = (m.gen or 0) + 1                  # removed partner: every token of that account stops at once


def decide(r: AppProject, pid: str, ok: bool, link_row: str = "") -> dict[str, Any]:
    """Her (or an app admin's) Haan / Na on an application. A partner shop is tied to ONE row of her partner list."""
    r = home(r)
    ensure_table()
    st = settings(r)
    with session() as s:
        p = s.get(AppPartner, pid)
        if p is None or p.site_id != _site(r):
            raise FamilyError("Yeh arzi nahi mili.", 404)
        kind, member = p.kind, p.member
    if ok and kind == "vendor":
        link = st["vendor"]["link"]
        if not link:
            raise FamilyError(_partner_problem(r, "vendor"))
        with session() as s:
            x = s.get(W.SiteAppRow, str(link_row or ""))
            if x is None or x.site_id != _site(r) or x.coll != link:
                raise FamilyError(f"Kaunsi dukaan? '{link}' list ki ek entry chuniye.", 400)
            taken = s.scalars(select(AppPartner).where(AppPartner.site_id == _site(r), AppPartner.kind == "vendor",
                                                       AppPartner.link_row == link_row, AppPartner.active == 1,
                                                       AppPartner.id != pid)).first()
        if taken is not None:
            log.info("shop %s gets a second partner account", link_row)   # allowed: a shop may have two phones
    if ok:
        _set_role(_site(r), member, "partner", False)
    with session() as s:
        p = s.get(AppPartner, pid)
        p.active = 1 if ok else -1
        p.decided_at = now()
        if ok and kind == "vendor":
            p.link_coll, p.link_row = st["vendor"]["link"], str(link_row)
        s.flush()
        s.expunge(p)
    STATS["approved" if ok else "refused"] += 1
    return _pview(p, _row_name(_site(r), p.link_row))


def remove(r: AppProject, pid: str) -> dict[str, Any]:
    r = home(r)
    ensure_table()
    with session() as s:
        p = s.get(AppPartner, pid)
        if p is None or p.site_id != _site(r):
            raise FamilyError("Yeh partner nahi mila.", 404)
        p.active, p.decided_at = -2, now()
        member = p.member
        others = s.scalars(select(AppPartner).where(AppPartner.site_id == _site(r), AppPartner.member == member,
                                                    AppPartner.active == 1, AppPartner.id != pid)).first()
        s.flush()
        s.expunge(p)
    if others is None:
        with session() as s:
            m = s.get(W.SiteAppMember, member)
            if m is not None and m.role == "partner":
                m.role, m.gen = "member", (m.gen or 0) + 1
    _release(r, member)
    return _pview(p)


def _release(r: AppProject, member: str) -> None:
    """A removed rider's open jobs go back to the pool (never left with nobody able to move them)."""
    from . import backend as BE
    st = settings(r)
    if not st["jobs"]:
        return
    with session() as s:
        for x in s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.coll == st["jobs"],
                                                      W.SiteAppRow.data.like(f'%"_to": "{member}"%'))).all():
            d = _j(x.data, {})
            if d.get("_to") == member and not BE._closed(str(d.get("status") or "")):
                for k in ("_to", "_to_name", "_to_at"):
                    d.pop(k, None)
                d["_ev"] = now().isoformat()
                x.data, x.updated_at = json.dumps(d, ensure_ascii=False), now()


# ---------------------------------------------------------------- what a partner sees
def _scope(r: AppProject, p: AppPartner, st: dict[str, Any], coll: str, d: dict[str, Any], me_id: str) -> str:
    """'' = not this partner's business; 'full' / 'limited' / 'offer' = how much of the row it sees."""
    if p.kind == "rider":
        if coll != st["jobs"]:
            return ""
        to = str(d.get("_to") or "")
        if to == me_id:
            return "full"
        if not to and str(d.get("status") or "") in st["rider"]["offer"]:
            return "offer"
        return ""
    if p.kind == "vendor" and p.link_row:
        ven = st["vendor"]
        if coll == st["jobs"] and ven["ref"] and str(d.get(ven["ref"]) or "") == p.link_row:
            return "limited"
        if coll in ven["lists"]:
            colls = {c["key"]: c for c in _schema(r).get("collections") or []}
            if any(str(d.get(k) or "") == p.link_row for k in _refs(colls.get(coll) or {}, ven["link"])):
                return "full"
    return ""


def _schema(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    return BE.schema(r)


def _view(r: AppProject, c: dict[str, Any], x: W.SiteAppRow, w: W.Who, how: str, p: AppPartner,
          st: dict[str, Any]) -> dict[str, Any]:
    v = W.row_view(c, x, w)
    d = _j(x.data, {})
    if how in ("limited", "offer"):
        for f in c["fields"]:
            if f.get("type") in LIMITED_TYPES:
                v.pop(f["key"], None)
            if f["key"] in ("name", "customer") and v.get(f["key"]):
                v[f["key"]] = _first(v[f["key"]])
    for k in ("total", "items", "discount", "delivery_fee"):
        if k not in v and d.get("_" + k) not in (None, ""):
            v[k] = d["_" + k]
        elif k not in v and d.get(k) not in (None, "") and k in ("total", "items"):
            v[k] = d[k]
    status = str(d.get("status") or "")
    v["partner"] = how
    if p.kind == "rider":
        v["can_take"] = how == "offer"
        v["steps"] = [s for s in st["rider"]["steps"] if s != status] if how == "full" and not _done(status) else []
    elif coll_is(c, st["jobs"]):
        v["steps"] = [s for s in st["vendor"]["steps"] if s != status] if not _done(status) and not d.get("_to") else []
    return v


def coll_is(c: dict[str, Any], key: str) -> bool:
    return c.get("key") == key


def _done(status: str) -> bool:
    from . import backend as BE
    return BE._closed(status)


def _scan(r: AppProject, coll: str, like: str = "") -> list[W.SiteAppRow]:
    with session() as s:
        q = select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.coll == coll)
        if like:
            q = q.where(W.SiteAppRow.data.like(like))
        got = s.scalars(q.order_by(W.SiteAppRow.created_at.desc()).limit(SCAN)).all()
        for x in got:
            s.expunge(x)
    return got


def rows(r: AppProject, coll: str, w: W.Who, limit: int = 200, q: str = "", status: str = "", offset: int = 0,
         mine: bool = False) -> list[dict[str, Any]] | None:
    """A partner's view of a list (None = not a partner: the normal rules apply)."""
    if not is_partner(w):
        return None
    p = partner(r, w)
    sch = _schema(r)
    c = W.coll(sch, coll)
    try:                                                       # what any signed-in account may see by the list's own rules
        base = W.rows(_site(r), sch, coll, w, 1000)
    except W.AppError:
        base = []
    out = {x["id"]: x for x in base}
    if p is not None:
        st = settings(r)
        like = f'%"{p.link_row}"%' if p.kind == "vendor" and p.link_row else ""
        for x in _scan(r, coll, like):
            how = _scope(r, p, st, coll, _j(x.data, {}), w.m.id)
            if how:
                out[x.id] = _view(r, c, x, w, how, p, st)
    got = list(out.values())
    if mine:
        got = [x for x in got if x.get("partner") == "full" or x.get("mine")]
    if status:
        got = [x for x in got if str(x.get("status") or "") == status]
    if q:
        t = q.strip().lower()[:80]
        got = [x for x in got if t in json.dumps(x, ensure_ascii=False).lower()]
    got.sort(key=lambda x: str(x.get("created") or ""), reverse=True)
    offset = max(0, int(offset or 0))
    return got[offset:offset + max(1, min(int(limit or 200), 1000))]


def sees(r: AppProject, w: W.Who, coll: str, row_id: str, d: dict[str, Any] | None = None) -> str:
    """For the live stream: how much of this row a partner may see ('' = nothing)."""
    p = partner(r, w) if is_partner(w) else None
    if p is None:
        return ""
    if d is None:
        with session() as s:
            x = s.get(W.SiteAppRow, row_id)
            d = _j(x.data, {}) if x is not None else {}
    return _scope(r, p, settings(r), coll, d, w.m.id)


def limit_live(r: AppProject, c: dict[str, Any], view: dict[str, Any], how: str) -> dict[str, Any]:
    if how in ("limited", "offer"):
        for f in c["fields"]:
            if f.get("type") in LIMITED_TYPES:
                view.pop(f["key"], None)
            if f["key"] in ("name", "customer") and view.get(f["key"]):
                view[f["key"]] = _first(view[f["key"]])
    view["partner"] = how
    return view


# ---------------------------------------------------------------- what a partner may change (checked here, done as the system)
def _load_row(r: AppProject, coll: str, row_id: str) -> W.SiteAppRow:
    with session() as s:
        x = s.get(W.SiteAppRow, row_id)
        if x is None or x.site_id != _site(r) or x.coll != coll:
            raise FamilyError("Yeh entry nahi mili.", 404)
        s.expunge(x)
    return x


def _deny(msg: str = "Yeh aapke kaam ka hissa nahi.") -> None:
    STATS["denied"] += 1
    raise FamilyError(msg, 403)


def update(r: AppProject, coll: str, row_id: str, body: dict[str, Any], w: W.Who) -> dict[str, Any] | None:
    """A partner's change (None = not a partner). Rider: take / steps / proof on HIS job. Shop: steps on its orders,
    its own rows in its lists. Checked here, then written through the normal path as the system (logic, connectors,
    push, stock / coupon give-back all run), and the row remembers who did it (_by)."""
    from . import backend as BE
    if not is_partner(w):
        return None
    p = partner(r, w)
    if p is None:
        _deny("Aapka partner account abhi approve nahi hua.")
    body = {k: v for k, v in (body if isinstance(body, dict) else {}).items() if k not in ("cid", "cart")}
    st = settings(r)
    x = _load_row(r, coll, row_id)
    d = _j(x.data, {})
    how = _scope(r, p, st, coll, d, w.m.id)
    if not how:
        _deny()
    if BE.ASSIGN_KEY in body:                                  # the rider app's outbox: {"_assign": "me"}
        if p.kind != "rider" or str(body.pop(BE.ASSIGN_KEY) or "") != "me":
            _deny()
        take(r, w, row_id)
        if not body:
            return _one(r, coll, row_id, w)
        x = _load_row(r, coll, row_id)
        d = _j(x.data, {})
        how = _scope(r, p, st, coll, d, w.m.id)
    c = W.coll(_schema(r), coll)
    types = {f["key"]: f for f in c["fields"]}
    allowed: set[str] = set()
    steps: list[str] = []
    if p.kind == "rider" and how == "full":
        steps = st["rider"]["steps"]
        allowed = {"status"} | {k for k, f in types.items() if f.get("type") in PROOF_TYPES and not f.get("admin_only")}
    elif p.kind == "vendor" and coll == st["jobs"]:
        if d.get("_to"):                                       # with a rider now: the shop's part is over
            _deny("Yeh order ab rider ke paas hai; badlaav business se karwaiye.")
        steps = st["vendor"]["steps"]
        allowed = {"status"}
    elif p.kind == "vendor" and how == "full":
        refs = set(_refs(c, st["vendor"]["link"]))
        allowed = {k for k, f in types.items() if not f.get("admin_only") and k not in refs and k != "status"}
    bad = [k for k in body if k not in allowed]
    if bad:
        _deny(f"Yeh badal nahi sakte: {', '.join(bad[:3])}.")
    if "status" in body:
        to = str(body["status"] or "")
        if to not in steps or _done(str(d.get("status") or "")):
            _deny(f"Status '{to}' aapke kadmon mein nahi" + (f" ({', '.join(steps)})." if steps else "."))
        STATS["steps"] += 1
    if not body:
        return _one(r, coll, row_id, w)
    upd = getattr(BE, "_update_inner", BE.update)              # inside the caller's journal 'acting' = the partner
    upd(r, coll, row_id, body, W.Who(owner=True))
    BE._merge(row_id, {"_by": w.m.id, "_by_kind": p.kind, "_by_at": now().isoformat()})
    return _one(r, coll, row_id, w)


def _one(r: AppProject, coll: str, row_id: str, w: W.Who) -> dict[str, Any]:
    p = partner(r, w)
    st = settings(r)
    x = _load_row(r, coll, row_id)
    how = _scope(r, p, st, coll, _j(x.data, {}), w.m.id) if p else ""
    if not how:
        return {"id": row_id, "partner": "", "gone": True}
    return _view(r, W.coll(_schema(r), coll), x, w, how, p, st)


def take(r: AppProject, w: W.Who, row_id: str) -> dict[str, Any]:
    """A rider takes an open job: the first tap wins (one lock across processes); at most `max` open jobs at a time."""
    from . import backend as BE
    from . import locks as LK
    p = partner(r, w)
    if p is None or p.kind != "rider":
        _deny("Sirf approved delivery partner kaam le sakta hai.")
    st = settings(r)
    with LK.hold(f"take:{_site(r)}:{row_id}"):
        x = _load_row(r, st["jobs"], row_id)
        d = _j(x.data, {})
        if str(d.get("_to") or "") == w.m.id:
            return _one(r, st["jobs"], row_id, w)
        if d.get("_to") or str(d.get("status") or "") not in st["rider"]["offer"]:
            STATS["take_lost"] += 1
            raise FamilyError("Yeh kaam ab khula nahi (kisi aur ne le liya ya status badal gaya).", 409)
        held = sum(1 for y in _scan(r, st["jobs"], f'%"_to": "{w.m.id}"%')
                   if _j(y.data, {}).get("_to") == w.m.id and not _done(str(_j(y.data, {}).get("status") or "")))
        if held >= st["rider"]["max"]:
            raise FamilyError(f"Aapke paas pehle se {held} kaam hain (seema {st['rider']['max']}); ek poora kijiye.", 409)
        name = _first(w.m.name or w.m.email.split("@")[0])
        BE._merge(row_id, {"_to": w.m.id, "_to_name": name, "_to_at": now().isoformat(), "_ev": now().isoformat(),
                           "_by": w.m.id, "_by_kind": "rider"})
    STATS["taken"] += 1
    try:                                                       # the customer hears that a rider is on it
        from . import turant as TU
        if x.owner:
            TU.later(r, [x.owner], "Rider assigned", f"{name} is picking up your order", row_id)
    except Exception:
        log.debug("take push", exc_info=True)
    return _one(r, st["jobs"], row_id, w)


def create(r: AppProject, coll: str, body: dict[str, Any], w: W.Who, ip: str = "") -> dict[str, Any] | None:
    """A partner shop adds a row to ITS list (a menu item): the link to its own shop is set by the server, never by it."""
    from . import backend as BE
    if not is_partner(w):
        return None
    p = partner(r, w)
    st = settings(r)
    if p is None or p.kind != "vendor" or coll not in st["vendor"]["lists"]:
        return None                                            # every other list: the list's own rules for this account
    c = W.coll(_schema(r), coll)
    refs = _refs(c, st["vendor"]["link"])
    data = {k: v for k, v in (body if isinstance(body, dict) else {}).items()
            if k == "cid" or (k in {f["key"] for f in c["fields"] if not f.get("admin_only")} and k not in refs and k != "status")}
    for k in refs:
        data[k] = p.link_row
    W.rate(f"ptr-cr:{_site(r)}:{w.m.id}", 60, 600)
    from . import locks as LK
    cid = str(data.get("cid") or "")
    if cid and BE.CID.match(cid):                              # the phone's retry makes ONE row (its own cid lock)
        with LK.hold(f"cid:{r.id}:{w.m.id}:{cid}"):
            out = BE._create(r, coll, data, W.Who(owner=True), ip)
    else:
        out = BE._create(r, coll, data, W.Who(owner=True), ip)
    BE._merge(out["id"], {"_by": w.m.id, "_by_kind": "vendor"})
    return _one(r, coll, out["id"], w)


def delete(r: AppProject, coll: str, row_id: str, w: W.Who) -> dict[str, Any] | None:
    from . import backend as BE
    if not is_partner(w):
        return None
    p = partner(r, w)
    st = settings(r)
    if p is None or p.kind != "vendor" or coll not in st["vendor"]["lists"]:
        _deny()
    if _scope(r, p, st, coll, _j(_load_row(r, coll, row_id).data, {}), w.m.id) != "full":
        _deny()
    dele = getattr(BE, "_delete_inner", BE.delete)
    return dele(r, coll, row_id, W.Who(owner=True))


# ---------------------------------------------------------------- the partner app's own screen (kit "hoola_jobs")
def _card(r: AppProject, c: dict[str, Any], v: dict[str, Any], st: dict[str, Any], kind: str) -> dict[str, Any]:
    fields = {f["key"]: f for f in c["fields"]}
    head = c["label"] + " " + str(v.get("id") or "")[-6:].upper()
    total = v.get("total")
    lines: list[str] = []
    items = str(v.get("items") or "").strip()
    if items:
        it = items.splitlines()
        lines.append(" · ".join(it[:3]) + (f" +{len(it) - 3}" if len(it) > 3 else ""))
    ven = st["vendor"]
    if kind == "rider" and ven["ref"] and v.get(ven["ref"]):
        lines.append("Pickup: " + _row_name(_site(r), str(v[ven["ref"]])))
    addr = next((str(v[k]) for k in fields if "address" in k and v.get(k)), "")
    if addr:
        lines.append(("Drop: " if kind == "rider" else "") + addr[:140])
    who_ = str(v.get("name") or v.get("customer") or "")
    if who_:
        lines.append(who_[:40])
    for k in ("note", "notes", "instructions"):
        if v.get(k):
            lines.append(str(v[k])[:140])
    phone = next((str(v[k]) for k, f in fields.items() if f.get("type") == "phone" and v.get(k)), "")
    loc = next((str(v[k]) for k, f in fields.items() if f.get("type") == "location" and v.get(k)), "")
    lat = lng = None
    m = re.match(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$", loc)
    if m:
        lat, lng = float(m.group(1)), float(m.group(2))
    return {"id": v.get("id"), "coll": c["key"], "title": head + (f" · Rs {total:g}" if isinstance(total, (int, float)) else ""),
            "lines": lines[:6], "status": str(v.get("status") or ""), "steps": v.get("steps") or [],
            "take": bool(v.get("can_take")), "phone": phone if v.get("partner") == "full" else "",
            "address": addr if v.get("partner") == "full" or kind == "rider" else "", "lat": lat, "lng": lng,
            "created": v.get("created", "")}


def jobs(r: AppProject, w: W.Who, app_key: str = "") -> dict[str, Any]:
    """GET /partner/jobs: everything the partner app's jobs screen shows, already decided by the server."""
    kind = kind_for_key(app_key) if app_key else ""
    kind = kind if kind in PARTNER_KINDS else ""
    if w.m is None:
        return {"state": "login", "kind": kind, "label": KINDS.get(kind, {}).get("label", "")}
    p = partner(r, w)
    if p is None or (kind and p.kind != kind):
        info = me(r, w, kind)
        return {**info, "state": info.get("state") if info.get("state") != "approved" else "none",
                "kind": kind, "can_request": bool(kind) and info.get("state") in ("none", "refused", "removed")}
    st = settings(r)
    c = W.coll(_schema(r), st["jobs"])
    got = rows(r, st["jobs"], w, 300) or []
    out: dict[str, Any] = {"state": "active", "kind": p.kind, "label": KINDS[p.kind]["label"], "offers": [], "mine": [],
                           "done": [], "shop": _row_name(_site(r), p.link_row) if p.kind == "vendor" else ""}
    for v in got:
        card = _card(r, c, v, st, p.kind)
        if v.get("partner") == "offer":
            out["offers"].append(card)
        elif v.get("partner") in ("full", "limited"):
            (out["done"] if _done(card["status"]) else out["mine"]).append(card)
    out["done"] = out["done"][:20]
    if p.kind == "rider":
        out["max"] = st["rider"]["max"]
    return out


def step(r: AppProject, w: W.Who, row_id: str, status: str) -> dict[str, Any]:
    st = settings(r)
    if not st["jobs"]:
        raise FamilyError("Is app mein kaam ki list nahi.", 404)
    return update(r, st["jobs"], row_id, {"status": status}, w) or {}


# ---------------------------------------------------------------- news to partners (push; never blocks the write)
def on_create(r: AppProject, coll: str, row_id: str, d: dict[str, Any]) -> None:
    """A new order for a partner shop: its phones hear it at once."""
    try:
        st = settings(r)
        ven = st["vendor"]
        if coll != st["jobs"] or not ven["ref"] or not d.get(ven["ref"]):
            return
        ensure_table()
        with session() as s:
            ids = [p.member for p in s.scalars(select(AppPartner).where(
                AppPartner.site_id == _site(home(r)), AppPartner.kind == "vendor", AppPartner.active == 1,
                AppPartner.link_row == str(d[ven["ref"]]))).all()]
        if ids:
            from . import turant as TU
            TU.later(r, ids, "New order", str(d.get("items") or "")[:80], row_id)
    except Exception:
        log.debug("family on_create", exc_info=True)


def on_status(r: AppProject, row_id: str, status: str) -> None:
    """An order became ready for pickup: approved riders hear there is a new job."""
    try:
        st = settings(r)
        if status not in st["rider"]["offer"]:
            return
        with session() as s:
            x = s.get(W.SiteAppRow, row_id)
            if x is None or x.coll != st["jobs"] or _j(x.data, {}).get("_to"):
                return
        ensure_table()
        with session() as s:
            ids = [p.member for p in s.scalars(select(AppPartner).where(
                AppPartner.site_id == _site(home(r)), AppPartner.kind == "rider", AppPartner.active == 1)).all()]
        if ids:
            from . import turant as TU
            TU.later(r, ids[:200], "New delivery", "A new delivery is ready for pickup", row_id)
    except Exception:
        log.debug("family on_status", exc_info=True)


# ---------------------------------------------------------------- the web admin (staff / admins of the app)
def _staff(w: W.Who, admin: bool = False) -> None:
    if w.m is None and not w.owner:
        raise FamilyError("Pehle login kijiye.", 401)
    if not w.staff:
        raise FamilyError("Yeh sirf staff ke liye hai.", 403)
    if admin and not (w.owner or (w.m and w.m.role == "admin")):
        raise FamilyError("Yeh sirf admin kar sakta hai.", 403)


def admin_overview(r: AppProject, w: W.Who) -> dict[str, Any]:
    from . import backend as BE
    _staff(w)
    r = home(r)
    sch = BE.schema(r)
    return {"name": r.name, "number": r.number, "admin": bool(w.owner or (w.m and w.m.role == "admin")),
            "me": W.view_member(w.m) if w.m else None,
            "lists": [{"key": c["key"], "label": c["label"], "fields": c["fields"], "statuses": _options(c),
                       "rules": c.get("rules") or {}} for c in sch.get("collections") or []],
            "counts": W.counts(_site(r)), "order": sch.get("order", ""),
            "faces": [{k: f.get(k) for k in ("kind", "label", "number", "name", "status")} for f in faces(r)],
            "waiting": len(partners(r, "waiting")), "family": settings(r)}


def admin_members(r: AppProject, w: W.Who) -> list[dict[str, Any]]:
    _staff(w)
    return W.members(_site(home(r)))


def admin_role(r: AppProject, w: W.Who, member: str, role: str) -> dict[str, Any]:
    """An app admin makes an account member / staff (only she makes an admin, from Hoola)."""
    _staff(w, admin=True)
    if role not in ("member", "staff") and not w.owner:
        raise FamilyError("Admin sirf member / staff bana sakta hai; naya admin maalkin Hoola se banati hain.", 403)
    if w.m is not None and member == w.m.id:
        raise FamilyError("Apna role khud nahi badal sakte.", 409)
    r = home(r)
    with session() as s:
        m = s.get(W.SiteAppMember, member)
        if m is None or m.site_id != _site(r):
            raise FamilyError("Yeh account nahi mila.", 404)
        if m.role == "admin" and not w.owner:
            raise FamilyError("Admin ka role sirf maalkin badal sakti hain.", 403)
        if m.role == "partner":
            raise FamilyError("Partner ko pehle Partners se hataiye.", 409)
    return W.set_role(_site(r), member, role)


def admin_partners(r: AppProject, w: W.Who) -> dict[str, Any]:
    _staff(w)
    st = settings(r)
    link = st["vendor"]["link"]
    shops = []
    if link:
        shops = [{"id": x.id, "name": _row_name(_site(home(r)), x.id)} for x in _scan(home(r), link)[:500]]
    return {"partners": partners(r), "shops": shops, "link": link, "admin": bool(w.owner or (w.m and w.m.role == "admin"))}


def admin_decide(r: AppProject, w: W.Who, pid: str, body: dict[str, Any]) -> dict[str, Any]:
    _staff(w, admin=True)
    act = str((body or {}).get("action") or "")
    if act == "remove":
        return remove(r, pid)
    if act not in ("approve", "refuse"):
        raise FamilyError("action: approve / refuse / remove.")
    return decide(r, pid, act == "approve", str((body or {}).get("link_row") or ""))


def _cell(v: Any) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
    s = s.replace("\r", " ")
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t") else s     # a cell can never run as a formula in Excel


def export_csv(r: AppProject, coll: str, w: W.Who) -> tuple[str, str]:
    """CSV of one list as THIS account may see it (staff: every row; the rules are the server's)."""
    from . import backend as BE
    _staff(w)
    W.rate(f"export:{_site(home(r))}:{w.id or 'owner'}", 20, 3600)
    sch = BE.schema(r)
    c = W.coll(sch, coll)
    got = BE.rows(r, coll, w, 1000)
    keys = [f["key"] for f in c["fields"]]
    extra = [k for k in ("total", "assigned_name", "created") if any(k in x for x in got) and k not in keys]
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(["id"] + keys + extra)
    for x in got:
        wr.writerow([_cell(x.get("id", ""))] + [_cell(x.get(k, "")) for k in keys + extra])
    STATS["exports"] += 1
    return "﻿" + buf.getvalue(), f"{coll}.csv"


# ---------------------------------------------------------------- her side (console / phone / chat)
def view(r: AppProject) -> dict[str, Any]:
    from ..config import get_settings
    r = home(r)
    base = (get_settings().public_base_url or "").rstrip("/")
    key = _j(r.android, {}).get("app_key") or ""
    st = settings(r)
    return {"app": r.id, "number": r.number, "faces": faces(r), "kinds": {k: v["label"] for k, v in KINDS.items()},
            "settings": st, "partners": partners(r)[:300],
            "problems": {k: _partner_problem(r, k) for k in PARTNER_KINDS},
            "admin_url": f"{base}/app-admin/{key}" if key else "",
            "admin_note": "" if key else "Web admin pehli Android build ke baad khulta hai (app ki chaabi wahin banti hai)."}


def prompt_line(seed_backend: dict[str, Any]) -> str:
    kind = str((seed_backend or {}).get("partner") or "")
    if kind not in PARTNER_KINDS:
        return ""
    who = "delivery partner (rider)" if kind == "rider" else "partner shop"
    return (f"THIS IS THE {who.upper()} APP of the business: the FIRST tab screen must start with PartnerJobsBlock() (the "
            "kit's jobs block: sign-in / apply / waiting / new jobs / my jobs with the allowed steps - the server decides "
            "all of it). Never draw your own order list for partners and never show customer phone numbers yourself.")
