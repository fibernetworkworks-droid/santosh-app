"""IT Admin Sahayak tools. `it_admin_dekho` only reads; `it_admin` keeps the licence / people / access registers, starts joiner /
mover / leaver checklists, writes staff guides, answers staff IT questions and syncs her admin consoles READ-ONLY. Any change of
access or settings only becomes a CARD here: her tap in the app decides (there is no approve action). Hoola never asks for or
keeps a password / OTP / PIN."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_CHANGE_KINDS = ["user_create", "user_disable", "user_enable", "user_signout", "licence_assign", "licence_remove", "admin_grant",
                 "admin_remove", "password_reset", "password_rotate", "access_add", "access_remove", "setting", "other"]

ITADMIN_TOOLS = [
    {"name": "it_admin", "description": (
        "Office IT administrator (devices live in the IT Helpdesk register). action=licence: licence (to update) or name, kind "
        "m365|workspace|tally|antivirus|domain|ssl|cloud|backup|software|saas|isp|other, vendor, plan, seats_bought, seats_used, cost "
        "(her number in rupees; never guess), cost_per month|year|once, per_seat, renews_on (YYYY-MM-DD), auto_renew, owner, "
        "login_with (which account manages it: never a password), notes. action=renewed (owner): licence, renews_on, cost (she renewed "
        "it herself). action=licence_remove (owner). action=person: person (to update) or name, email, phone, role, department, manager, "
        "join_date, leave_date, notes. action=access: person, system, account, level user|admin|owner, shared, mfa yes|no|unknown, notes "
        "(records only THAT access exists; never a password). action=joiner|mover|leaver: person, when, new_role -> checklist + change "
        "cards. action=item: checklist, item, done. action=change: kind (" + "|".join(_CHANGE_KINDS) + "), person, access, licence, system, "
        "target, what -> ONLY a card for her tap (never say it is approved, never do it yourself, not even with pc_do). "
        "action=change_done (owner): change, ok, note (she did an approved change in the console). action=review: start the access "
        "review; action=review_item (owner): review, access, decision keep|remove; action=review_close (owner). action=guide: topic, "
        "words (HER setup words: the only facts), steps (optional list), audience, tags, guide (to make a new version). "
        "action=guide_step: guide, n, text / remove. action=guide_publish (owner): guide, archive. action=guide_file: guide (Word). "
        "action=ask: text (a staff IT question; the staff member's words), person -> answer from her published guides, else the IT "
        "helpdesk (ticket); access requests become her card. action=sync (owner): provider google|microsoft (read-only pull of users, "
        "licences, devices). action=forget_person (owner): person (left staff, DPDP). action=settings (owner): org_name, domain, "
        "admin_name, standard_systems, windows, review_months, morning_time, rules, practices. action=register (Excel)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["licence", "renewed", "licence_remove", "person", "access", "joiner", "mover", "leaver",
                                               "item", "change", "change_done", "review", "review_item", "review_close", "guide",
                                               "guide_step", "guide_publish", "guide_file", "ask", "sync", "forget_person", "settings",
                                               "register"]},
         "licence": {"type": "string"}, "name": {"type": "string"}, "kind": {"type": "string"}, "vendor": {"type": "string"},
         "plan": {"type": "string"}, "seats_bought": {"type": "integer"}, "seats_used": {"type": "integer"}, "cost": {"type": "number"},
         "cost_per": {"type": "string"}, "per_seat": {"type": "boolean"}, "renews_on": {"type": "string"}, "auto_renew": {"type": "boolean"},
         "owner": {"type": "string"}, "login_with": {"type": "string"}, "notes": {"type": "string"}, "person": {"type": "string"},
         "email": {"type": "string"}, "phone": {"type": "string"}, "role": {"type": "string"}, "department": {"type": "string"},
         "manager": {"type": "string"}, "join_date": {"type": "string"}, "leave_date": {"type": "string"}, "system": {"type": "string"},
         "account": {"type": "string"}, "level": {"type": "string"}, "shared": {"type": "boolean"}, "mfa": {"type": "string"},
         "when": {"type": "string"}, "new_role": {"type": "string"}, "checklist": {"type": "string"}, "item": {"type": "string"},
         "done": {"type": "boolean"}, "access": {"type": "string"}, "target": {"type": "string"}, "what": {"type": "string"},
         "change": {"type": "string"}, "ok": {"type": "boolean"}, "note": {"type": "string"}, "review": {"type": "string"},
         "decision": {"type": "string"}, "topic": {"type": "string"}, "words": {"type": "string"},
         "steps": {"type": "array", "items": {"type": "string"}}, "audience": {"type": "string"},
         "tags": {"type": "array", "items": {"type": "string"}}, "guide": {"type": "string"}, "n": {"type": "integer"},
         "text": {"type": "string"}, "remove": {"type": "boolean"}, "archive": {"type": "boolean"}, "provider": {"type": "string"},
         "org_name": {"type": "string"}, "domain": {"type": "string"}, "admin_name": {"type": "string"},
         "standard_systems": {"type": "array", "items": {"type": "string"}}, "windows": {"type": "array", "items": {"type": "integer"}},
         "review_months": {"type": "integer"}, "morning_time": {"type": "string"}, "rules": {"type": "string"},
         "practices": {"type": "object"}},
         "required": ["action"]}},
    {"name": "it_admin_dekho", "description": (
        "Read the office IT admin registers (nothing changes). what=day (renewals in 30 days, free seats in rupees, changes waiting for "
        "her haan, approved changes still to do, checklists due, review due, questions staff keep asking) | licences (kind) | renewals "
        "(days) | devices (IT Helpdesk register) | people (status) | person (person: access, devices, checklists) | access (person, "
        "system) | checklists | changes (status) | reviews | guides | guide (guide: steps, versions) | gaps (questions no guide answered) "
        "| connections (Google Workspace / Microsoft 365 status, permissions needed) | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "licences", "renewals", "devices", "people", "person", "access", "checklists", "changes",
                                             "reviews", "guides", "guide", "gaps", "connections", "settings", "rules"]},
         "kind": {"type": "string"}, "days": {"type": "integer"}, "status": {"type": "string"}, "person": {"type": "string"},
         "system": {"type": "string"}, "guide": {"type": "string"}},
         "required": ["what"]}},
]
ITADMIN_LABELS = {"it_admin": "IT admin ka kaam kar raha hoon", "it_admin_dekho": "Licence, log aur access dekh raha hoon"}

_OWNER_ONLY = {"renewed", "licence_remove", "change_done", "review_item", "review_close", "guide_publish", "sync", "forget_person", "settings"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _pick(a: dict, keys) -> dict:
    return {k: a[k] for k in keys if k in a and a[k] is not None}


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..itadmin import connectors as K
    from ..itadmin import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Office IT admin graahakon ke liye nahi hai.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    try:
        if action == "licence":
            return S.save_licence(t, _s(a.get("licence")), **_pick(a, ("name", "kind", "vendor", "plan", "seats_bought", "seats_used", "cost",
                                                                        "cost_per", "per_seat", "renews_on", "auto_renew", "owner",
                                                                        "login_with", "notes")))
        if action == "renewed":
            return S.renewed(t, _s(a.get("licence")), _s(a.get("renews_on")), a.get("cost"), actor=actor)
        if action == "licence_remove":
            return S.remove_licence(t, _s(a.get("licence")))
        if action == "person":
            return S.save_person(t, _s(a.get("person")), **_pick(a, ("name", "email", "phone", "role", "department", "manager",
                                                                      "join_date", "leave_date", "notes")))
        if action == "access":
            return S.save_access(t, "", **_pick(a, ("person", "system", "account", "level", "shared", "mfa", "notes")))
        if action in ("joiner", "mover", "leaver"):
            return S.start_checklist(t, _s(a.get("person") or a.get("name")), action, _s(a.get("when")), _s(a.get("new_role")),
                                     actor=actor, conv=conv)
        if action == "item":
            return S.check_item(t, _s(a.get("checklist")), _s(a.get("item")), bool(a.get("done", True)), actor=actor)
        if action == "change":
            return S.request_change(t, _s(a.get("kind")), _s(a.get("person")), _s(a.get("access")), _s(a.get("system")),
                                    _s(a.get("target")), _s(a.get("what")), _s(a.get("licence")), actor=actor, conv=conv)
        if action == "change_done":
            return S.change_done(t, _s(a.get("change")), bool(a.get("ok", True)), _s(a.get("note")), actor=actor)
        if action == "review":
            return S.start_review(t, conv)
        if action == "review_item":
            return S.review_item(t, _s(a.get("review")), _s(a.get("access")), _s(a.get("decision")), actor=actor, conv=conv)
        if action == "review_close":
            return S.close_review(t, _s(a.get("review")), actor=actor)
        if action == "guide":
            return S.write_guide(t, _s(a.get("topic")), _s(a.get("words")), a.get("steps"), _s(a.get("audience")), a.get("tags"),
                                 _s(a.get("guide")), actor=actor, conv=conv)
        if action == "guide_step":
            return S.edit_step(t, _s(a.get("guide")), int(a.get("n") or 0), _s(a.get("text")), bool(a.get("remove")))
        if action == "guide_publish":
            return S.publish_guide(t, _s(a.get("guide")), actor=actor, archive=bool(a.get("archive")))
        if action == "guide_file":
            return S.guide_file(t, _s(a.get("guide")), conv)
        if action == "ask":
            return S.ask(t, _s(a.get("text")), _s(a.get("person")), actor=actor, conv=conv)
        if action == "sync":
            return S.sync(t, _s(a.get("provider")), conv)
        if action == "forget_person":
            return S.forget_person(t, _s(a.get("person")), actor=actor)
        if action == "settings":
            return S.save_settings(t, **_pick(a, ("org_name", "domain", "admin_name", "standard_systems", "windows", "review_months",
                                                  "morning_time", "rules", "practices")))
        if action == "register":
            return S.register_file(t, conv)
    except (S.ItadminError, K.ConnError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..itadmin import connectors as K
    from ..itadmin import rules as R
    from ..itadmin import service as S
    t = ctx.tenant_id
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Office IT admin graahakon ke liye nahi hai.")
    try:
        if what == "day":
            return S.day(t)
        if what == "licences":
            return {"licences": S.licences(t, _s(a.get("kind")))}
        if what == "renewals":
            return S.renewals(t, int(a.get("days") or 90))
        if what == "devices":
            return S.devices(t)
        if what == "people":
            return {"people": S.people(t, _s(a.get("status")))}
        if what == "person":
            return S.person_view(t, _s(a.get("person")))
        if what == "access":
            return {"access": S.access_list(t, _s(a.get("person")), _s(a.get("system")))}
        if what == "checklists":
            return {"checklists": S.checklists(t, _s(a.get("status") or "open"))}
        if what == "changes":
            return {"changes": S.changes(t, _s(a.get("status")))}
        if what == "reviews":
            return {"reviews": S.reviews(t)}
        if what == "guides":
            return {"guides": S.guides(t, _s(a.get("status")))}
        if what == "guide":
            return S.guide_view(t, _s(a.get("guide")))
        if what == "gaps":
            return {"gaps": S.gaps(t, int(a.get("days") or 30))}
        if what == "connections":
            return K.status(t)
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"change_kinds": R.CHANGE_KINDS, "never_by_api": sorted(R.NEVER_API), "practices": R.practices_list(),
                    "licence_kinds": R.LIC_KINDS,
                    "never": ["password / OTP / PIN maangna, rakhna ya batana", "access / setting khud badalna (sirf uske tap se card)",
                              "user banana ya password reset API se (password lagta hai: woh console mein khud)",
                              "staff ka data naukri ke kaam ke alawa"]}
    except (S.ItadminError, K.ConnError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def it_admin(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def it_admin_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


ITADMIN_HANDLERS = {"it_admin": it_admin, "it_admin_dekho": it_admin_dekho}
