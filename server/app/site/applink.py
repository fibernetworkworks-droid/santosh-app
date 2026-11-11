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
        return {"app": p.id, "number": p.number, "linked": True, "say": f"The website already runs on the brain of app {p.number}."}
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
            "say": f"The website now runs on the brain of app {number}: the same lists, the same people, now with links / workflow / approvals."}


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
            raise W.AppError("The website is already linked to an app.", 409)
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
    from . import security as SEC
    if token and not SEC.token_ok(BE.bid(p), token):     # v0.434 a login she / the member ended
        return W.Who(None)
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
                raise W.AppError("This is not allowed.", 403)
            return {"members": W.members(site_id), "admin": bool(w.m and w.m.role == "admin")}
        if op == "role":
            return _role(w, kw["member_id"], body, lambda mid, role: W.set_role(site_id, mid, role))
        if op == "stats":
            return W.stats(site_id, sch, w, int(kw.get("days") or 30))
        if op in ("approvals", "decide", "related", "fn", "otp_start", "otp_verify", "2fa_login", "sessions", "session_end",
                  "logout_all", "2fa_start", "2fa_confirm", "2fa_off", "export", "delete_me", "audit", "matrix", "upload",
                  "pay_plans", "pay_subscribe", "pay_subs", "pay_cancel") or op in LIVE_OPS:
            raise W.AppError("This website does not have this yet; link the website to the app's brain first.", 404)
        raise W.AppError("not found", 404)
    from ..appmaker import backend as BE
    from ..appmaker.logic import engine as LE
    from . import security as SEC
    site, ua = BE.bid(p), str(kw.get("ua") or "")
    if op == "schema":
        out = BE.public_schema(p)
        out["security"] = {"otp": bool(SEC.provider()), "consent": True}       # v0.434 what the login box may offer
        from . import livesite as LS
        out["live"] = {"queue": bool(LS.cfg(p).get("on")), "push": True}       # v0.459 live channel / chat / queue / push
        return out
    if op == "signup":                                   # v0.434 DPDP: the website's sign-up needs her tick
        # the new page script always sends the tick (true / false); a page built before v0.434 sends nothing - it still
        # works (until its next rebuild ships the new script) but no consent is recorded for it
        if "consent" in body and body.get("consent") is not True:
            raise W.AppError("To create an account, a yes (tick) on the privacy notice is required.", 400)
        out = BE.signup(p, str(body.get("email") or ""), str(body.get("password") or ""), str(body.get("name") or ""), ip)
        mem = W.member_of(site, out.get("token") or "")
        if mem is not None:
            if body.get("consent") is True:
                SEC.save_consent(site, mem.id, "signup")
            SEC.record(site, mem, out["token"], ua, ip, "signup")
        return out
    if op == "login":
        out = BE.login(p, str(body.get("email") or ""), str(body.get("password") or ""), ip)
        mem = W.member_of(site, out.get("token") or "")
        if mem is not None and SEC.needs_2fa(site, mem.email):   # password right; the authenticator code is step two
            return {"need_2fa": True, "ticket": SEC._ticket(site, mem)}
        if mem is not None:
            SEC.record(site, mem, out["token"], ua, ip, "password")
        return out
    if op == "otp_start":
        return SEC.otp_start(site, str(body.get("phone") or ""), ip)
    if op == "otp_verify":
        return SEC.otp_verify(site, BE.schema(p), str(body.get("phone") or ""), str(body.get("code") or ""),
                              str(body.get("name") or ""), body.get("consent") is True, ua, ip)
    if op == "2fa_login":
        return SEC.two_fa_login(site, str(body.get("ticket") or ""), str(body.get("code") or ""), ua, ip)
    if op == "me":
        return {"me": W.view_member(w.m) if w.m else None}
    if op == "logout":
        if w.m:
            SEC.end_all(site, w.m)
        return {"ok": True}
    if op in ("sessions", "session_end", "logout_all", "2fa_start", "2fa_confirm", "2fa_off", "export", "delete_me"):
        if not w.m:
            raise W.AppError("Sign in first.", 401)
        if op == "sessions":
            return {"sessions": SEC.sessions(site, w.m, token)}
        if op == "session_end":
            return SEC.end(site, w.m, str(kw.get("sid") or ""))
        if op == "logout_all":
            return SEC.end_all(site, w.m)
        if op == "2fa_start":
            return SEC.two_fa_start(site, w.m, (r.name or "Hoola") if r is not None else "Hoola")
        if op == "2fa_confirm":
            return SEC.two_fa_confirm(site, w.m, str(body.get("code") or ""))
        if op == "2fa_off":
            return SEC.two_fa_off(site, w.m, str(body.get("code") or ""))
        if op == "export":
            return SEC.export(site, BE.schema(p), w.m)
        out = BE.delete_me(p, w)
        try:                                            # v0.459 her browsers' notification addresses go with her account
            from . import webpush as WP
            WP.forget_member(site, w.m.id)
        except Exception:                               # noqa: BLE001
            pass
        return out
    if op == "audit":                                    # admin only (her own view is the console)
        if not (w.m and w.m.role == "admin"):
            raise W.AppError("Only admins can see the audit log.", 403)
        return {"audit": SEC.audit(site, int(kw.get("limit") or 200), str(kw.get("coll") or ""))}
    if op == "matrix":
        if not w.staff:
            raise W.AppError("This is not allowed.", 403)
        return {"matrix": SEC.matrix(BE.schema(p))}
    if op == "upload":
        return BE.upload(p, w, kw.get("raw") or b"", ip)
    if op in ("pay_plans", "pay_subscribe", "pay_subs", "pay_cancel"):   # v0.452 AutoPay plans on the website (her plans)
        from ..appmaker import pay as PY
        if op == "pay_plans":
            return PY.plans(p)
        if not w.m:
            raise W.AppError("Sign in first.", 401)
        if op == "pay_subscribe":
            return PY.subscribe(p, w, str(kw.get("key") or ""))
        if op == "pay_subs":
            return PY.my_subs(p, w)
        return PY.cancel_sub(p, w, str(kw.get("sid") or ""))
    if op in LIVE_OPS:                                   # v0.459 live chat / presence / queue / browser notifications / hooks
        return _live_op(site_id, p, w, op, body, ua, **{k: v for k, v in kw.items() if k != "ua"})
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
            raise W.AppError("This is not allowed.", 403)
        return {"members": BE.members(p), "admin": bool(w.m and w.m.role == "admin")}
    if op == "role":
        return _role(w, kw["member_id"], body, lambda mid, role: BE.set_role(p, mid, role))
    if op == "stats":
        return W.stats(BE.bid(p), BE.schema(p), w, int(kw.get("days") or 30))
    if op == "approvals":
        if not w.m:
            raise W.AppError("Sign in first.", 401)
        return {"approvals": LE.approvals(p, w)}
    if op == "decide":
        return LE.decide(p, kw["appr_id"], str(body.get("decision") or ""), str(body.get("note") or "")[:300], w)
    if op == "related":
        return LE.related(p, kw["key"], kw["row_id"], kw["rel"], w)
    if op == "fn":
        args = body.get("args") if isinstance(body.get("args"), list) else []
        return LE.call_public(p, kw["name"], args, w)
    raise W.AppError("not found", 404)


LIVE_OPS = ("chat_mine", "chat_write", "chat_threads", "chat_thread", "chat_reply", "typing", "presence", "push_key", "push_sub",
            "push_unsub", "queue_board", "queue_mine", "queue_take", "queue_staff", "queue_add", "queue_call", "queue_mark", "hook")


def _live_op(site_id: str, p, w: W.Who, op: str, body: dict[str, Any], ua: str, **kw) -> dict[str, Any]:
    """v0.459 ABHI ABHI WEBSITE: the website's live features on its linked app (site/livesite.py, appmaker/baat.py)."""
    from ..appmaker import backend as BE
    from ..appmaker import baat as BT
    from ..appmaker import live as LV
    from . import livesite as LS
    from . import webpush as WP
    if op == "chat_mine":
        return BT.mine(p, w)
    if op == "chat_write":
        return BT.write(p, w, str(body.get("text") or ""), str(body.get("order") or ""))
    if op == "chat_threads":
        return BT.threads(p, w)
    if op == "chat_thread":
        return BT.thread(p, w, str(kw.get("member") or ""))
    if op == "chat_reply":                               # website staff (her own replies go through the console, her tap)
        return BT.reply(p, w, str(kw.get("member") or ""), str(body.get("text") or ""), her_tap=False)
    if op == "typing":
        return LV.typing(p, w, str(body.get("thread") or ""))
    if op == "presence":
        return LV.online(p, w)
    if op == "push_key":
        return {"key": WP.public_key()}
    if op == "push_sub":
        return WP.subscribe(BE.bid(p), w, body, ua)
    if op == "push_unsub":
        return WP.unsubscribe(BE.bid(p), w, body)
    if op == "queue_board":
        return LS.board_cached(p)
    if op == "queue_mine":
        return LS.mine(p, w)
    if op == "queue_take":
        return LS.take(p, w, body)
    if op == "queue_staff":
        return LS.staff_view(p, w)
    if op == "queue_add":
        return LS.add(p, w, body)
    if op == "queue_call":
        n = body.get("token")
        return LS.call_next(p, w, int(n) if str(n or "").isdigit() else None)
    if op == "queue_mark":
        try:
            n = int(body.get("token"))
        except (TypeError, ValueError):
            raise W.AppError("Token number?", 400)
        return LS.mark(p, w, n, str(body.get("status") or ""))
    if op == "hook":                                     # her outside service calls the website's app (signed)
        from ..appmaker import connect as CN
        return CN.hook(p, str(kw.get("key") or ""), kw.get("headers") or {}, kw.get("raw") or b"")
    raise W.AppError("not found", 404)


def live_open(site_id: str, token: str):
    """The live stream's door: (project, who) for a signed-in member of a linked website, or AppError."""
    from . import service as S
    r, _ = S.public_app(site_id)
    p = project(r)
    if p is None:
        raise W.AppError("This website does not have live yet; link the website to the app's brain first.", 404)
    return p, _who(site_id, p, token)


def queue_project(site_id: str):
    from . import service as S
    r, _ = S.public_app(site_id)
    p = project(r)
    if p is None:
        raise W.AppError("not found", 404)
    return p


def _role(w: W.Who, member_id: str, body: dict[str, Any], setter) -> dict[str, Any]:
    if not (w.m and w.m.role == "admin"):
        raise W.AppError("Only an admin can change a role.", 403)
    if member_id == w.m.id:
        raise W.AppError("You cannot change your own role.", 400)
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
        return {"linked": False, "say": "The website is on plain lists right now; if you want rules / workflow say 'logic' - it gets linked first."}
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
        raise W.AppError("Make the logic draft first.", 409)
    out = LS.apply(p, h)
    try:                                    # new lists / fields reach the account + staff pages
        S._after_edit(S._load(r.id), "logic: new lists / rules")
    except Exception:
        log.info("site rebuild after logic skipped", exc_info=True)
    return out


# ---------------------------------------------------------------- v0.414 every old v0.305 site moves by itself
_MIGRATE = {"done": 0, "failed": 0, "last": ""}


def migrate_all(limit: int = 25) -> dict[str, Any]:
    """The worker's sweep: every website that still has a v0.305 app (lists, no link) is joined to App Sahayak's backend -
    same members, same rows, same passwords, same addresses. Idempotent; a site that fails is retried next sweep."""
    from ..config import get_settings
    from .models import Site
    if not getattr(get_settings(), "site_app_link", True):
        return {"moved": 0, "off": True}
    W.ensure_tables()
    with session() as s:
        rows = s.query(Site.id, Site.tenant_id, Site.app).filter(Site.app.like('%"collections"%')).limit(400).all()
    todo = []
    for sid, tenant, app in rows:
        a = _j(app, {})
        if isinstance(a, dict) and not a.get("link") and a.get("collections"):
            todo.append((sid, tenant))
    moved = []
    for sid, tenant in todo[:limit]:
        try:
            out = link(tenant, sid)
            moved.append({"site": sid, "app": out["app"]})
            _MIGRATE["done"] += 1
        except Exception as e:                   # noqa: BLE001 - one bad site never stops the others
            _MIGRATE["failed"] += 1
            _MIGRATE["last"] = f"{sid}: {e}"[:300]
            log.warning("site app migrate failed for %s: %s", sid, e)
    return {"moved": len(moved), "left": max(0, len(todo) - len(moved)), "sites": moved}


# ---------------------------------------------------------------- v0.414 the phone app on the SAME data
def phone_app(tenant: str, ref: str, conv: str = "") -> dict[str, Any]:
    """Her website's app becomes an Android / iPhone app design WITHOUT a second copy of anything: App Sahayak plans the
    screens for the site's business (its normal plan card -> 3 looks -> design -> build), on the SAME project - same id,
    same app_key, same lists, logic, members and rows. A row added on the website shows in the phone app and back."""
    from ..appmaker import service as AS
    from ..appmaker.models import AppProject
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    link(tenant, ref)
    p = project(S._load(r.id))
    if p.status not in ("web",):
        return {"app": p.id, "number": p.number, "status": p.status,
                "say": f"This website's phone app is already being made in app {p.number} ({p.status})."}
    facts = _j(r.facts, {})
    try:
        tmp = AS.new(tenant, (r.brief or r.name or "")[:1800], conv, name=r.name or facts.get("name") or "",
                     field=r.field or "", quiet=True, answers={"sure": True, **{k: facts[k] for k in ("phone", "address", "city") if facts.get(k)}})
    except AS.AppError as e:
        raise W.AppError(str(e), 400) from e
    keep = ("name", "brief", "field", "goal", "style", "styles", "language", "facts", "answers", "plan", "status", "stage",
            "board", "preview_token")
    with session() as s:
        t = s.get(AppProject, tmp["id"])
        row = s.get(AppProject, p.id)
        old_plan = _j(row.plan, {})
        for k in keep:
            setattr(row, k, getattr(t, k))
        plan = _j(row.plan, {})
        for k in ("architect",):                 # the Architect's card stays with the project
            if k in old_plan:
                plan[k] = old_plan[k]
        plan["web_site"] = r.id
        row.plan = json.dumps(plan, ensure_ascii=False)
        row.conv = conv or row.conv
        row.updated_at = now()
        s.delete(t)                              # the planning shell only; nothing else ever pointed at it
        s.flush()
        s.expunge(row)
    AS._emit(row, push=True)
    v = AS.view(row)
    return {"app": row.id, "number": row.number, "status": row.status, "app_key": (_j(row.android, {}) or {}).get("app_key", ""),
            "say": f"The phone app plan is ready (app {row.number}) - the same data as the website. Approve on the plan card, "
                   "then 3 looks; after the build the Android / iPhone app and the website see the same data.", "view": v}


# ---------------------------------------------------------------- v0.434 her view: who changed what, who may do what
def owner_audit(tenant: str, ref: str, limit: int = 100) -> dict[str, Any]:
    from ..appmaker import backend as BE
    from . import security as SEC
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    p = project(r)
    if p is None:
        return {"audit": [], "matrix": [], "linked": False}
    return {"linked": True, "audit": SEC.audit(BE.bid(p), limit), "matrix": SEC.matrix(BE.schema(p)),
            "otp": bool(SEC.provider())}
