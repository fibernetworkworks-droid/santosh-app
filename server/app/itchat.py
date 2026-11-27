"""IT ADMIN DESK - the IT Admin employee gets its own section, like the finance desks (owner: "IT Admin same as finance desks").

- The IT Admin chat = a Conversation with kind 'itadmin', kept out of every Hoola chat list (callconv.not_call); facts she tells it still
  reach her one memory. A turn in it (or a voice call started from it) gets the desk's state as a block and the IT admin tools
  (`it_admin` / `it_admin_dekho`, family itadmin) in view.
- The desk runs the IT Admin engine (app/itadmin): licences and subscriptions (seats bought vs used, renewals, what free seats cost her,
  IT spend), the people and access register (never a password), joiner / mover / leaver checklists, access reviews, Google Workspace /
  Microsoft 365 read with her consent, change cards (disable a user, licences, admin rights) decided only by her tap, staff how-to
  guides, staff IT questions answered from the guides or turned into an IT Helpdesk ticket.
- GLOBAL: her country decides the extra good-practice rows (India's CERT-In / DPDP rows checked; other countries' rows say 'check this'),
  her own money unit is used for every price she types; Hoola converts or guesses no price.
- Hoola never asks for, writes or keeps a password / PIN / OTP, never creates a user or resets a password by API, and changes access
  or settings only on her tap.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.itchat")

KIND = "itadmin"
KEY = "it_admin"                 # the Hub employee
FAMILIES = ["itadmin", "helpdesk"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FOOT = ("Hoola keeps your licences, renewals, people and access, runs joiner / leaver checklists and access reviews, writes staff "
        "guides and answers staff IT questions. It never asks for a password, and changes access or settings only on your tap.")
_SECRET = re.compile(r"\b(otp|cvv|cvc|upi ?pin|atm ?pin|card ?number|card no|net ?banking|m-?pin)\b|\b(password|passwd|pwd|pin)\b\s*(is|:|=)\s*\S+", re.I)
_DATA_FIELDS = {"text", "words"}            # a staff question / guide words may mention 'password' (e.g. "reset my password")


class ItDeskError(ValueError):
    pass


def is_itadmin(conv: str) -> bool:
    if not conv:
        return False
    if conv in _OF:
        return _OF[conv]
    hit = False
    try:
        with session() as s:
            c = s.get(Conversation, conv)
            if c is not None:
                if (c.kind or "") == KIND:
                    hit = True
                elif (c.kind or "") == "call" and c.origin_conv:
                    o = s.get(Conversation, c.origin_conv)
                    hit = bool(o is not None and (o.kind or "") == KIND)
    except Exception:   # noqa: BLE001
        log.exception("it admin chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _hire():
    from .employee import hire
    return hire


def _S():
    from .itadmin import service
    return service


def _K():
    from .itadmin import connectors
    return connectors


# ---------------------------------------------------------------- the desk
def spend(tenant: str, lic: list[dict]) -> dict[str, Any]:
    """IT spend from HER numbers: per year, by kind, by vendor, per active person, the next 90 days of renewals."""
    S = _S()
    rows = [x for x in lic if x.get("yearly") is not None]
    total = round(sum(x["yearly"] for x in rows), 2)
    by_kind: dict[str, float] = {}
    by_vendor: dict[str, float] = {}
    for x in rows:
        by_kind[x["kind_label"]] = by_kind.get(x["kind_label"], 0) + x["yearly"]
        v = x["vendor"] or x["name"]
        by_vendor[v] = by_vendor.get(v, 0) + x["yearly"]
    active = len([p for p in S.people(tenant) if p["status"] in ("active", "joining", "")])
    soon = [x for x in lic if x["days_left"] is not None and 0 <= x["days_left"] <= 90]
    out90 = round(sum((x["yearly"] if x["cost_per"] == "year" else (x["cost"] or 0) * (3 if x["cost_per"] == "month" else 1)) or 0
                      for x in soon if x.get("cost") is not None), 2)
    waste = round(sum((x["waste"] or {}).get("rupees_year") or 0 for x in lic), 2)
    return {"year": total, "month": round(total / 12, 2), "per_person": round(total / active, 2) if active else None, "people": active,
            "by_kind": sorted(by_kind.items(), key=lambda t: -t[1]), "by_vendor": sorted(by_vendor.items(), key=lambda t: -t[1])[:10],
            "next_90": out90, "waste": waste, "unpriced": len(lic) - len(rows),
            "auto_off": len([x for x in lic if x["auto_renew"] is False]), "auto_unknown": len([x for x in lic if x["auto_renew"] is None and x["renews_on"]])}


def access_stats(tenant: str) -> dict[str, Any]:
    S = _S()
    acc = S.access_list(tenant, status="active")
    ppl = {p["id"]: p for p in S.people(tenant)}
    left = [a for a in acc if (ppl.get(a["person_id"]) or {}).get("status") in ("left", "leaving")]
    return {"active": len(acc), "admins": len([a for a in acc if a["level"] in ("admin", "owner")]),
            "admins_no_mfa": len([a for a in acc if a["level"] in ("admin", "owner") and a["mfa"] == "no"]),
            "no_mfa": len([a for a in acc if a["mfa"] == "no"]), "shared": len([a for a in acc if a["shared"]]),
            "never_reviewed": len([a for a in acc if not a["reviewed_at"]]), "leavers_active": len(left),
            "leaver_rows": left[:20], "by_system": sorted(_count(acc, "system").items(), key=lambda t: -t[1])[:12]}


def _count(rows: list[dict], k: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r[k] or "-"] = out.get(r[k] or "-", 0) + 1
    return out


def today_view(tenant: str) -> dict[str, Any]:
    S = _S()
    o = S.overview(tenant)
    d = o["day"]
    st = o["settings"]
    sp = spend(tenant, o["licences"])
    ac = access_stats(tenant)
    needs: list[dict[str, Any]] = []

    def n_(x: int, w1: str, wm: str = "") -> str:
        return f"{x:,} {w1 if x == 1 else (wm or w1 + 's')}"
    if d["waiting"]:
        needs.append({"say": f"{n_(len(d['waiting']), 'change card')} waiting for your tap", "go": "changes", "bad": True})
    if d["approved"]:
        needs.append({"say": f"{n_(len(d['approved']), 'approved change')} still to do in the console", "go": "changes"})
    if ac["leavers_active"]:
        needs.append({"say": f"{n_(ac['leavers_active'], 'access', 'accesses')} still open for people who left", "go": "people", "bad": True})
    if ac["admins_no_mfa"]:
        needs.append({"say": f"{n_(ac['admins_no_mfa'], 'admin account')} without 2-step sign-in", "go": "people", "bad": True})
    for l in d["renewals"]["licences"][:3]:
        needs.append({"say": f"{l['name']} renews {l['renews_on']} ({l['days_left']} days)" + (", auto-renew OFF" if l["auto_renew"] is False else ""),
                      "go": "licences", "bad": l["days_left"] <= 7})
    for c in d["due_checklists"][:3]:
        needs.append({"say": f"{c.get('person') or 'Someone'}: {c['kind']} checklist {c['done']}/{c['total']} due {c['due']}", "go": "people", "bad": True})
    if d["review_due"]:
        needs.append({"say": f"Access review is due (every {st['review_months']} months)", "go": "people"})
    if sp["waste"]:
        needs.append({"say": f"Unused seats cost about {S.money(tenant, sp['waste'])} a year", "go": "licences"})
    if d["gaps"] and d["gaps"][0]["count"] >= 3:
        needs.append({"say": f"Staff keep asking '{d['gaps'][0]['topic'][:60]}' - write a guide", "go": "guides"})
    if not st.get("country"):
        needs.append({"say": "Set your country and money unit", "go": "settings"})
    if not o["licences"]:
        needs.append({"say": "Add your licences and subscriptions (or connect Google Workspace / Microsoft 365)", "go": "licences"})
    from .itadmin import rules as R
    return {**o, "needs": needs, "spend": spend(tenant, o["licences"]), "access_stats": ac, "access": S.access_list(tenant, status=""),
            "checklists": S.checklists(tenant, ""), "gaps": S.gaps(tenant, 30), "lic_kinds": R.LIC_KINDS, "change_kinds": R.CHANGE_KINDS,
            "money_unit": (st.get("currency") or "INR")}


def summary(tenant: str) -> dict[str, Any]:
    h = _hire()
    st = h.status(tenant, KEY)
    if st not in ("hired", "paused"):
        return {"hired": False, "status": st, "say": "IT Admin is not hired. Hire it from AI Employees."}
    with session() as s:
        trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    out: dict[str, Any] = {"hired": True, "status": st, "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
                           "foot": FOOT}
    try:
        out["desk"] = today_view(tenant)
    except Exception as e:   # noqa: BLE001
        log.exception("it admin desk read failed")
        out["desk_error"] = str(e)[:200]
    return out


# ---------------------------------------------------------------- actions
def _act(tenant: str, part: str, a: dict[str, Any]) -> Any:
    S, K = _S(), _K()
    g = lambda k: str(a.get(k) or "").strip()   # noqa: E731
    pick = lambda *ks: {k: a[k] for k in ks if k in a}   # noqa: E731
    f = {
        "licence_save": lambda: S.save_licence(tenant, g("id"), **pick("name", "kind", "vendor", "plan", "owner", "login_with", "seats_bought",
                                                                         "seats_used", "cost", "cost_per", "per_seat", "renews_on", "auto_renew", "notes")),
        "licence_remove": lambda: S.remove_licence(tenant, g("id")),
        "renewed": lambda: S.renewed(tenant, g("id"), g("renews_on"), float(a["cost"]) if str(a.get("cost") or "").strip() else None),
        "person_save": lambda: S.save_person(tenant, g("id"), **pick("name", "email", "phone", "role", "department", "manager", "notes",
                                                                    "status", "join_date", "leave_date")),
        "person_get": lambda: S.person_view(tenant, g("id")),
        "forget_person": lambda: S.forget_person(tenant, g("id")),
        "access_save": lambda: S.save_access(tenant, g("id"), **pick("person", "system", "account", "level", "shared", "mfa", "status", "notes")),
        "checklist": lambda: S.start_checklist(tenant, g("person"), g("kind"), g("when"), g("new_role")),
        "check_item": lambda: S.check_item(tenant, g("checklist"), g("item"), bool(a.get("done", True))),
        "change": lambda: S.request_change(tenant, g("kind"), g("person"), g("access"), g("system"), g("target"), g("what"), g("licence")),
        "decide": lambda: S.decide_change(tenant, g("change"), bool(a.get("yes")), g("hash"), g("reason"), by_tap=True),
        "change_done": lambda: S.change_done(tenant, g("change"), bool(a.get("ok", True)), g("note")),
        "review_start": lambda: S.start_review(tenant),
        "review_item": lambda: S.review_item(tenant, g("review"), g("access"), g("decision")),
        "review_close": lambda: S.close_review(tenant, g("review")),
        "guide_write": lambda: S.write_guide(tenant, g("topic"), str(a.get("words") or ""), None, g("audience"), guide=g("id")),
        "guide_get": lambda: S.guide_view(tenant, g("id")),
        "guide_step": lambda: S.edit_step(tenant, g("id"), int(a.get("n") or 0), g("text"), bool(a.get("remove"))),
        "guide_publish": lambda: S.publish_guide(tenant, g("id"), archive=bool(a.get("archive"))),
        "guide_restore": lambda: S.restore_version(tenant, g("id"), int(a.get("version") or 0)),
        "guide_file": lambda: S.guide_file(tenant, g("id")),
        "ask": lambda: S.ask(tenant, str(a.get("text") or ""), g("person")),
        "sync": lambda: S.sync(tenant, g("provider")),
        "google_start": lambda: {"url": K.google_start(tenant, g("mode") or "read")},
        "ms_save": lambda: K.ms_save(tenant, g("directory_id"), g("client_id"), str(a.get("client_secret") or "").strip(), g("mode") or "read"),
        "conn_forget": lambda: K.forget(tenant, g("provider")),
        "register_file": lambda: S.register_file(tenant),
        "settings": lambda: S.save_settings(tenant, **pick("org_name", "domain", "admin_name", "standard_systems", "windows", "review_months",
                                                           "morning_time", "rules", "practices", "country", "currency")),
    }.get(part)
    if f is None:
        raise ItDeskError("Not an IT Admin desk action.")
    return f()


READS = {"person_get", "guide_get"}


def do(tenant: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    st = _hire().status(tenant, KEY)
    if st not in ("hired", "paused"):
        raise PermissionError("Hire IT Admin from AI Employees first.")
    if st == "paused" and part not in READS:
        raise PermissionError("IT Admin is paused: resume it to make changes.")
    blob = json.dumps({k: v for k, v in a.items() if k not in _DATA_FIELDS and k != "client_secret"}, ensure_ascii=False)
    if _SECRET.search(blob):
        raise PermissionError("Hoola never takes a password, OTP, PIN or card number - record only THAT an access exists.")
    if part != "ms_save" and a.get("client_secret"):
        raise PermissionError("An app secret goes only into the Microsoft 365 connection in Settings, sealed.")
    try:
        out = _act(tenant, part, a)
    except (_S().ItadminError,) as e:
        raise ItDeskError(str(e))
    if part not in READS:
        forget(tenant)
    return out


# ---------------------------------------------------------------- the chat
GREET_NO = ("I keep your licences and renewals, who has which access, joiner and leaver checklists, access reviews and staff "
            "guides. Hire me from AI Employees to start.")
GREET_EMPTY = ("Hello. Tell me your licences and subscriptions, add the people and the systems they use, or connect Google Workspace "
               "or Microsoft 365 in Settings so I can read them.")
GREET_TAIL = "Ask me about a renewal, someone joining or leaving, or a staff IT question. Any change of access is your tap."
CHAT_TITLE = "IT Admin chat"

RULES = ("You are her IT administrator, talking in the desk's own chat (or a voice call started from it). Use it_admin_dekho to read "
         "and it_admin to act. Licences, prices and dates are HER numbers - never guess one. Access records say THAT an access exists - "
         "never ask for, write or repeat a password, PIN or OTP. Any change of access or settings (disable a user, licence, admin rights, "
         "shared password) is only a CARD: she taps it on the desk - never say it is done. Users are never created and passwords never "
         "reset by API. Staff IT questions: answer from her guides, else open an IT Helpdesk ticket. Country rules: India's CERT-In / DPDP "
         "rows are checked; for any other country say 'check this'. Plain English, short. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<itadmin_desk>{RULES}IT Admin is not hired yet: tell her to hire it from AI Employees.</itadmin_desk>"
        else:
            k = d.get("desk") or {}
            st = k.get("settings") or {}
            sp = k.get("spend") or {}
            ac = k.get("access_stats") or {}
            S = _S()
            lic = "; ".join(f"{l['number']} {l['name']}" + (f" renews {l['renews_on']}" if l["renews_on"] else "")
                            + (f", {l['seats_used']}/{l['seats_bought']} seats" if l["seats_bought"] else "") for l in (k.get("licences") or [])[:15])[:1200] or "none"
            ch = "; ".join(f"{c['number']} {c['kind_label']} {c['target'] or c['system']}: {c['status']}" for c in (k.get("changes") or [])[:8])[:700] or "none"
            ppl = ", ".join(f"{p['name']} ({p['status'] or 'active'})" for p in (k.get("people") or [])[:20])[:600] or "none"
            txt = (f"\n\n<itadmin_desk>{RULES}\nLicences: {lic}.\nIT spend a year: {S.money(tenant, sp.get('year')) or 'not priced'}; unused seats "
                   f"{S.money(tenant, sp.get('waste')) or 'none'}.\nPeople: {ppl}.\nAccess: {ac.get('active', 0)} active, {ac.get('admins', 0)} admin, "
                   f"{ac.get('admins_no_mfa', 0)} admin without 2-step, {ac.get('leavers_active', 0)} open for leavers.\nChange cards: {ch}."
                   f"\nCountry {st.get('country') or 'IN (not set)'}, money {st.get('currency') or 'INR'}.\nHer rules: {(st.get('rules') or '')[:400]}"
                   "\nNeeds: " + "; ".join(x["say"] for x in (k.get("needs") or [])[:10]) + "</itadmin_desk>")
    except Exception:   # noqa: BLE001
        log.exception("it admin desk block failed")
        txt = f"\n\n<itadmin_desk>{RULES}The desk could not be read just now.</itadmin_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


def greeting(tenant: str) -> str:
    try:
        d = summary(tenant)
    except Exception:   # noqa: BLE001
        return GREET_EMPTY
    if not d.get("hired"):
        return GREET_NO
    k = d.get("desk") or {}
    if not k.get("licences") and not k.get("people"):
        return GREET_EMPTY
    return (f"Hello. {len(k.get('licences') or [])} licence(s) and {len(k.get('people') or [])} people on the register. " + GREET_TAIL)


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title=CHAT_TITLE)
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/itdesk/chat", dependencies=dep)
    def it_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/itdesk/chat/new", dependencies=dep)
    def it_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/itdesk/chat/{conv}/ok", dependencies=dep)
    def it_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your IT Admin chat")
        return {"ok": True}

    @router.get("/api/itdesk/desk", dependencies=dep)
    def it_desk(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant)

    @router.post("/api/itdesk/do/{part}", dependencies=dep)
    def it_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        try:
            return do(tenant, part, body or {})
        except PermissionError as e:
            raise HTTPException(403, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
