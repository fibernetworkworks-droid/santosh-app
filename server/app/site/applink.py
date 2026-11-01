"""v0.407 EK DIMAAG (web Step 2, W1 of docs/WEB_PLATFORM_PLAN.md): a website's web app runs on the SAME backend as her
native apps - App Sahayak's backend + the DIMAAG logic engine (relations, formulas, rules, unique keys, workflows with
maker-checker approvals and SLAs, triggers, schedules, locked functions).

- `link(tenant, site)`: the site gets ONE App Sahayak project behind it (status 'web', its own app_key so a phone app can
  be built on the very same data later). The site's lists become that project's lists, and every member and row the
  site already has moves to it unchanged (same ids, same passwords; logins made before the move keep working).
- `call(site_id, op, ...)`: the site's own `/api/site-app/<site>/...` addresses stay the same for its pages; an unlinked
  site is served by the v0.305 engine exactly as before, a linked one by the app backend (logic runs on every write,
  rows come back with their workflow buttons, approvals waiting and linked-record names).
- Logic is drafted / applied with App Sahayak's own author + checker (`appmaker.logic.service`) - only her tap applies."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any

from sqlalchemy import update

from ..db import now, session
from . import webapp as W

log = logging.getLogger("santosh.site")


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


# ---------------------------------------------------------------- the link
def linked_id(r) -> str:
    """The App Sahayak project behind this site ('' = the v0.305 engine)."""
    return str((_j(r.app, {}) or {}).get("link") or "")


def project(r):
    from ..appmaker.models import AppProject
    pid = linked_id(r)
    if not pid:
        return None
    with session() as s:
        p = s.get(AppProject, pid)
        if p is not None:
            s.expunge(p)
        return p


def link(tenant: str, ref: str) -> dict[str, Any]:
    """Give the site its App Sahayak backend (idempotent). The site's lists + members + rows move over unchanged."""
    from ..appmaker import backend as BE
    from ..appmaker import service as AS
    from ..appmaker.models import AppProject
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    p = project(r)
    if p is not None:
        return {"app": p.id, "number": p.number, "linked": True, "say": f"Website pehle se app {p.number} ke dimaag par hai."}
    W.ensure_tables()
    sch = _j(r.app, {}) if isinstance(_j(r.app, {}), dict) else {}
    cols = [c for c in (sch.get("collections") or [])]
    schema = {"collections": cols, "signup": bool(sch.get("signup", True)), "kind": "web", "order": ""}
    be = {"schema": schema, "made": now().isoformat(), "v": BE.SCHEMA_V, "rev": 1, "changes": [], "site": r.id}
    facts = _j(r.facts, {})
    with session() as s:
        p = AppProject(tenant_id=tenant, number=AS._number(s, tenant), name=r.name or facts.get("name") or "Website app",
                       brief=f"Website {r.number}: {r.brief or ''}"[:2000], field=r.field or "", goal="web",
                       status="web", stage="web", facts=json.dumps(facts, ensure_ascii=False),
                       backend=json.dumps(be, ensure_ascii=False))
        s.add(p)
        s.flush()
        pid, number = p.id, p.number
    _join(r.id, pid)
    return {"app": pid, "number": number, "linked": True,
            "say": f"Website ab app {number} ke dimaag par chalegi: wahi lists, wahi log, ab rishte / workflow / approvals ke saath."}


def attach(tenant: str, site_id: str, pid: str) -> dict[str, Any]:
    """v0.407 ARCHITECT: a NEW site joins the app project her spec card drafted (its data + logic live there)."""
    from ..appmaker.models import AppProject
    from .models import Site
    W.ensure_tables()
    with session() as s:
        r = s.get(Site, site_id)
        p = s.get(AppProject, pid)
        if r is None or p is None or r.tenant_id != tenant or p.tenant_id != tenant:
            raise W.AppError("not found", 404)
        if linked_id(r):
            raise W.AppError("Website pehle se ek app se judi hai.", 409)
        be = _j(p.backend, {}) or {}
        be["site"] = r.id
        p.backend = json.dumps(be, ensure_ascii=False)
        p.status, p.stage = "web", "web"
        if not p.name and r.name:
            p.name = r.name
    _join(site_id, pid)
    return {"app": pid, "linked": True}


def _join(site_id: str, pid: str) -> None:
    """Move the site's members + rows to the app's backend id and point the site at the app (one transaction)."""
    from ..appmaker import backend as BE
    from ..appmaker.models import AppProject
    from .models import Site
    with session() as s:
        p = s.get(AppProject, pid)
        if hasattr(p, "android"):
            a = _j(p.android, {}) or {}
            a.setdefault("app_key", "ak" + secrets.token_hex(12))
            a["site"] = site_id
            p.android = json.dumps(a)
        s.execute(update(W.SiteAppRow).where(W.SiteAppRow.site_id == site_id).values(site_id=BE.bid(pid))
                  .execution_options(synchronize_session=False))
        s.execute(update(W.SiteAppMember).where(W.SiteAppMember.site_id == site_id).values(site_id=BE.bid(pid))
                  .execution_options(synchronize_session=False))
        row = s.get(Site, site_id)
        app = _j(row.app, {}) or {}
        app = {**(app if isinstance(app, dict) else {}), "link": pid}
        row.app = json.dumps(app, ensure_ascii=False)


def schema(r) -> dict[str, Any]:
    """The lists the site's pages show (the linked app's, decorated with its logic) - or the v0.305 schema."""
    p = project(r)
    if p is None:
        sch = _j(r.app, {})
        return {k: v for k, v in (sch or {}).items() if k != "link"} if isinstance(sch, dict) else {}
    from ..appmaker import backend as BE
    return BE.schema(p)


# ---------------------------------------------------------------- who is asking (old site logins keep working)
def _who(site_id: str, p, token: str) -> W.Who:
    from ..appmaker import backend as BE
    if p is None:
        return W.Who(W.member_of(site_id, token) if token else None)
    w = BE.who(p, token)
    if w.m is not None or not token:
        return w
    try:                                    # a login made before the link: signed for the site id, same member id
        sid, mid, gen, exp, sig = token.split(".")
    except ValueError:
        return w
    body = f"{sid}.{mid}.{gen}.{exp}"
    if sid != site_id or int(exp) < time.time() or not hmac.compare_digest(
            sig, hmac.new(W._secret(), body.encode(), hashlib.sha256).hexdigest()[:40]):
        return w
    with session() as s:
        m = s.get(W.SiteAppMember, mid)
        if m is None or m.site_id != BE.bid(p) or str(m.gen) != gen:
            return w
        s.expunge(m)
    return W.Who(m)


# ---------------------------------------------------------------- one entry for every public call
def call(site_id: str, op: str, token: str = "", body: dict[str, Any] | None = None, ip: str = "", **kw) -> dict[str, Any]:
    from . import service as S
    body = body or {}
    r, v305 = S.public_app(site_id)
    p = project(r)
    w = _who(site_id, p, token)
    if p is None:                                       # the v0.305 engine, exactly as before
        sch = v305
        if op == "schema":
            return W.public_schema(sch)
        if op == "signup":
            return W.signup(site_id, sch, str(body.get("email") or ""), str(body.get("password") or ""), str(body.get("name") or ""), ip)
        if op == "login":
            return W.login(site_id, str(body.get("email") or ""), str(body.get("password") or ""), ip)
        if op == "me":
            return {"me": W.view_member(w.m) if w.m else None}
        if op == "logout":
            if w.m:
                W.logout_all(site_id, w.m)
            return {"ok": True}
        if op == "rows":
            return {"rows": W.rows(site_id, sch, kw["key"], w)}
        if op == "create":
            return W.create(site_id, sch, kw["key"], body, w, ip)
        if op == "update":
            return W.update(site_id, sch, kw["key"], kw["row_id"], body, w)
        if op == "delete":
            return W.delete(site_id, sch, kw["key"], kw["row_id"], w)
        if op == "members":
            if not w.staff:
                raise W.AppError("Iski ijaazat nahi.", 403)
            return {"members": W.members(site_id), "admin": bool(w.m and w.m.role == "admin")}
        if op == "role":
            return _role(w, kw["member_id"], body, lambda mid, role: W.set_role(site_id, mid, role))
        if op == "stats":
            return W.stats(site_id, sch, w, int(kw.get("days") or 30))
        if op in ("approvals", "decide", "related", "fn"):
            raise W.AppError("Is website mein yeh abhi nahi; pehle website ko app ke dimaag se jodiye.", 404)
        raise W.AppError("not found", 404)
    from ..appmaker import backend as BE
    from ..appmaker.logic import engine as LE
    if op == "schema":
        return BE.public_schema(p)
    if op == "signup":
        return BE.signup(p, str(body.get("email") or ""), str(body.get("password") or ""), str(body.get("name") or ""), ip)
    if op == "login":
        return BE.login(p, str(body.get("email") or ""), str(body.get("password") or ""), ip)
    if op == "me":
        return {"me": W.view_member(w.m) if w.m else None}
    if op == "logout":
        if w.m:
            W.logout_all(BE.bid(p), w.m)
        return {"ok": True}
    if op == "rows":
        return {"rows": BE.rows(p, kw["key"], w)}
    if op == "create":
        return BE.create(p, kw["key"], body, w, ip)
    if op == "update":
        return BE.update(p, kw["key"], kw["row_id"], body, w)
    if op == "delete":
        return BE.delete(p, kw["key"], kw["row_id"], w)
    if op == "members":
        if not w.staff:
            raise W.AppError("Iski ijaazat nahi.", 403)
        return {"members": BE.members(p), "admin": bool(w.m and w.m.role == "admin")}
    if op == "role":
        return _role(w, kw["member_id"], body, lambda mid, role: BE.set_role(p, mid, role))
    if op == "stats":
        return W.stats(BE.bid(p), BE.schema(p), w, int(kw.get("days") or 30))
    if op == "approvals":
        if not w.m:
            raise W.AppError("Pehle login kijiye.", 401)
        return {"approvals": LE.approvals(p, w)}
    if op == "decide":
        return LE.decide(p, kw["appr_id"], str(body.get("decision") or ""), str(body.get("note") or "")[:300], w)
    if op == "related":
        return LE.related(p, kw["key"], kw["row_id"], kw["rel"], w)
    if op == "fn":
        args = body.get("args") if isinstance(body.get("args"), list) else []
        return LE.call_public(p, kw["name"], args, w)
    raise W.AppError("not found", 404)


def _role(w: W.Who, member_id: str, body: dict[str, Any], setter) -> dict[str, Any]:
    if not (w.m and w.m.role == "admin"):
        raise W.AppError("Role sirf admin badal sakta hai.", 403)
    if member_id == w.m.id:
        raise W.AppError("Apna role khud nahi badal sakte.", 400)
    return setter(member_id, str(body.get("role") or ""))


# ---------------------------------------------------------------- her side: logic (drafted by App Sahayak's author)
def logic_view(tenant: str, ref: str) -> dict[str, Any]:
    from ..appmaker.logic import service as LS
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    p = project(r)
    if p is None:
        return {"linked": False, "say": "Website abhi seedhi lists par hai; niyam / workflow chahiye to 'logic' kahiye - pehle jod denge."}
    return {"linked": True, "app": p.id, "number": p.number, **LS.view(p)}


def logic_draft(tenant: str, ref: str, words: str) -> dict[str, Any]:
    from ..appmaker.logic import service as LS
    from . import service as S
    link(tenant, ref)
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    return LS.draft(project(r), words)


def logic_apply(tenant: str, ref: str, h: str) -> dict[str, Any]:
    """ONLY her tap (the console button / the API with the draft's hash she saw)."""
    from ..appmaker.logic import service as LS
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    p = project(r)
    if p is None:
        raise W.AppError("Pehle logic ka draft banaiye.", 409)
    out = LS.apply(p, h)
    try:                                    # new lists / fields reach the account + staff pages
        S._after_edit(S._load(r.id), "logic: nayi lists / niyam")
    except Exception:
        log.info("site rebuild after logic skipped", exc_info=True)
    return out
