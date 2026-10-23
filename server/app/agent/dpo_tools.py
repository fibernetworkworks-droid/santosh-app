"""DPO Sahayak tools (data protection officer under the DPDP Act 2023 + Rules 2025). `dpo_dekho` only reads; `dpo` does the
work. Publishing a notice, replying to a person, erasing data and breach notices are only CARDS here: her tap in the app decides
them. Hoola is not a lawyer and files nothing on any portal."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_FACTS = {k: {"type": "string"} for k in ("nature", "extent", "when", "location", "impact", "consequences", "measures", "safety",
                                          "cause", "findings", "remedial", "details", "systems", "people_report")}

DPO_TOOLS = [
    {"name": "dpo", "description": (
        "Data protection officer (DPDP Act 2023 + DPDP Rules 2025; notice / consent / rights / breach duties apply from 13-05-2027). "
        "Jaankari only, not legal advice. action=settings (owner): org, contact_name, contact_email, contact_phone (the person who "
        "answers people), link (https page / form to withdraw consent and ask), identifiers (how she identifies a person, e.g. "
        "'registered mobile'), reply_days (her target, max 90), languages, sdf, third_schedule ecommerce|gaming|social, morning_time, "
        "rules. action=scan: pre-fill records of processing from the Hoola modules she uses (counts only). action=activity (owner): "
        "activity (PA-01 to edit, empty = new), name, people, items [..], purpose, basis consent|voluntary|employment|law|emergency, "
        "retention, retention_days, processors [..], children, abroad, law_hold, status active|stopped, confirmed (she checked it), "
        "notes. action=dpia (owner): activity, answers {purpose, children, health_fin, scale, new_tech, abroad, sharing, security, "
        "consent_ok, erase_ok: true/false}. action=notice: lang hi|mr|en, activities [PA-..] -> draft (Rule 3). action=notice_edit "
        "(owner): notice, text. action=notice_publish: notice -> card for her tap. action=consent: name, phone, activities, how, proof "
        "(reference only), child, parent_name, parent_check (HOW the parent was verified + reference, never an ID number). "
        "action=withdraw: phone or consent (their right: recorded at once). action=request: text (THEIR words = data), name, phone, "
        "email, via, kind access|correction|erasure|withdraw|grievance|nominee, received (date) -> R-0001 with the due date. "
        "action=verify: request, ok, how (method + reference only). action=reply: request, body (optional; access replies are built "
        "from her records) -> card. action=erase: request, modules [..] -> card (needs verified identity). action=sent (owner): request, "
        "how. action=close (owner): request, status closed|rejected, note. action=breach: title, aware ('YYYY-MM-DD HH:MM' or 'abhi'), "
        "nature, extent, when, location, impact, consequences, measures, safety, cause, findings, remedial, details, systems, "
        "activities, affected [{name, phone, email}], cert_in (default true: opens the IT Helpdesk incident with the CERT-In 6-hour "
        "clock). action=breach_update: breach + any fact / affected. action=breach_send: breach, which initial|report|people -> card. "
        "action=breach_sent (owner): breach, which, ref. action=breach_close (owner): breach. action=vendor (owner): vendor (name / id "
        "to edit), name, service, items, country, dpa_signed, dpa_on, review_on, clauses {instructions, security, breach, subprocessor, "
        "staff, erase, help_rights, location, audit, logs, liability: true/false}, notes. action=register: Excel of everything."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "scan", "activity", "dpia", "notice", "notice_edit", "notice_publish", "consent",
                                               "withdraw", "request", "verify", "reply", "erase", "sent", "close", "breach",
                                               "breach_update", "breach_send", "breach_sent", "breach_close", "vendor", "register"]},
         "org": {"type": "string"}, "contact_name": {"type": "string"}, "contact_email": {"type": "string"},
         "contact_phone": {"type": "string"}, "link": {"type": "string"}, "identifiers": {"type": "string"},
         "reply_days": {"type": "integer"}, "languages": {"type": "string"}, "sdf": {"type": "boolean"},
         "third_schedule": {"type": "string"}, "morning_time": {"type": "string"}, "rules": {"type": "string"},
         "activity": {"type": "string"}, "name": {"type": "string"}, "people": {"type": "string"},
         "items": {"type": "array", "items": {"type": "string"}}, "purpose": {"type": "string"}, "basis": {"type": "string"},
         "retention": {"type": "string"}, "retention_days": {"type": "integer"},
         "processors": {"type": "array", "items": {"type": "string"}}, "children": {"type": "boolean"}, "abroad": {"type": "boolean"},
         "law_hold": {"type": "boolean"}, "status": {"type": "string"}, "confirmed": {"type": "boolean"}, "notes": {"type": "string"},
         "answers": {"type": "object"}, "lang": {"type": "string"}, "activities": {"type": "array", "items": {"type": "string"}},
         "notice": {"type": "string"}, "text": {"type": "string"}, "phone": {"type": "string"}, "how": {"type": "string"},
         "proof": {"type": "string"}, "child": {"type": "boolean"}, "parent_name": {"type": "string"}, "parent_check": {"type": "string"},
         "consent": {"type": "string"}, "email": {"type": "string"}, "via": {"type": "string"}, "kind": {"type": "string"},
         "received": {"type": "string"}, "request": {"type": "string"}, "ok": {"type": "boolean"}, "body": {"type": "string"},
         "modules": {"type": "array", "items": {"type": "string"}}, "note": {"type": "string"}, "title": {"type": "string"},
         "aware": {"type": "string"}, **_FACTS, "affected": {"type": "array", "items": {"type": "object"}}, "cert_in": {"type": "boolean"},
         "breach": {"type": "string"}, "which": {"type": "string"}, "ref": {"type": "string"}, "vendor": {"type": "string"},
         "service": {"type": "string"}, "country": {"type": "string"}, "dpa_signed": {"type": "boolean"}, "dpa_on": {"type": "string"},
         "review_on": {"type": "string"}, "clauses": {"type": "object"}},
         "required": ["action"]}},
    {"name": "dpo_dekho", "description": (
        "Read the data protection register (nothing changes). what=day (breach clocks, requests due, cards waiting, records to check) | "
        "activities (records of processing with checks) | notices | consents (q) | requests (status open|...) | request (request) | "
        "find (phone: where this person's data is in her Hoola modules) | breaches | breach (breach: drafts for Board / people) | vendors "
        "(DPA clause gaps) | retention | cards | settings | law (phases, penalties, DPIA / DPA checklists, sources)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "activities", "notices", "consents", "requests", "request", "find", "breaches",
                                             "breach", "vendors", "retention", "cards", "settings", "law"]},
         "q": {"type": "string"}, "status": {"type": "string"}, "request": {"type": "string"}, "phone": {"type": "string"},
         "breach": {"type": "string"}},
         "required": ["what"]}},
]
DPO_LABELS = {"dpo": "Data suraksha ka kaam kar raha hoon", "dpo_dekho": "Data suraksha register dekh raha hoon"}

OWNER_ONLY = ("settings", "activity", "dpia", "notice_edit", "sent", "close", "breach_sent", "breach_close", "vendor")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..dpo import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Data suraksha ka kaam graahak ke liye nahi.")
    if action in OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    try:
        if action == "settings":
            return S.save_settings(t, actor, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "scan":
            return S.scan(t, actor)
        if action == "activity":
            return S.activity_save(t, _s(a.get("activity")), actor, **{k: a[k] for k in S._ACT_KEYS if k in a})
        if action == "dpia":
            return S.dpia(t, _s(a.get("activity")), a.get("answers") or {}, actor)
        if action == "notice":
            return S.notice_draft(t, _s(a.get("lang") or "hi"), a.get("activities"), actor)
        if action == "notice_edit":
            return S.notice_edit(t, _s(a.get("notice")), _s(a.get("text")), actor)
        if action == "notice_publish":
            return S.notice_request(t, _s(a.get("notice")), actor, conv)
        if action == "consent":
            return S.consent_add(t, _s(a.get("name")), _s(a.get("phone")), a.get("activities"), _s(a.get("how")), _s(a.get("proof")),
                                 bool(a.get("child")), _s(a.get("parent_name")), _s(a.get("parent_check")), a.get("notice_version"), actor)
        if action == "withdraw":
            return S.consent_withdraw(t, _s(a.get("consent")), _s(a.get("phone")), _s(a.get("how")), conv)
        if action == "request":
            return S.request_new(t, _s(a.get("text")), _s(a.get("name")), _s(a.get("phone")), _s(a.get("email")), _s(a.get("via")),
                                 _s(a.get("kind")), _s(a.get("received")), actor, conv)
        if action == "verify":
            return S.request_verify(t, _s(a.get("request")), bool(a.get("ok", True)), _s(a.get("how")), actor)
        if action == "reply":
            return S.request_reply(t, _s(a.get("request")), _s(a.get("body")), actor, conv)
        if action == "erase":
            return S.erase_request(t, _s(a.get("request")), a.get("modules"), actor, conv)
        if action == "sent":
            return S.request_sent(t, _s(a.get("request")), _s(a.get("how")), actor)
        if action == "close":
            return S.request_close(t, _s(a.get("request")), _s(a.get("status") or "closed"), _s(a.get("note")), actor)
        if action == "breach":
            facts = {k: a[k] for k in S.R.BREACH_FIELDS if k in a}
            return S.breach_new(t, _s(a.get("title")), _s(a.get("aware")), bool(a.get("cert_in", True)), a.get("activities"),
                                a.get("affected"), actor, conv, **facts)
        if action == "breach_update":
            facts = {k: a[k] for k in S.R.BREACH_FIELDS if k in a}
            return S.breach_update(t, _s(a.get("breach")), a.get("affected"), actor, **facts)
        if action == "breach_send":
            return S.breach_send(t, _s(a.get("breach")), _s(a.get("which") or "initial"), actor, conv)
        if action == "breach_sent":
            return S.breach_sent(t, _s(a.get("breach")), _s(a.get("which") or "initial"), _s(a.get("ref")), actor)
        if action == "breach_close":
            return S.breach_close(t, _s(a.get("breach")), actor)
        if action == "vendor":
            kw = {k: a[k] for k in ("name", "service", "items", "country", "dpa_signed", "dpa_on", "review_on", "clauses", "notes")
                  if k in a}
            return S.vendor_save(t, _s(a.get("vendor")), actor, **kw)
        if action == "register":
            return S.register_file(t, conv)
    except (S.DpoError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..dpo import service as S
    t = ctx.tenant_id
    if (getattr(ctx, "actor", "owner") or "").startswith("customer:"):
        raise ToolError("Data suraksha ka register graahak ke liye nahi.")
    try:
        if what == "day":
            return S.day(t)
        if what == "activities":
            return {"activities": S.activities(t)}
        if what == "notices":
            return {"notices": S.notices(t)}
        if what == "consents":
            return {"consents": S.consents(t, _s(a.get("q")))}
        if what == "requests":
            return {"requests": S.requests(t, _s(a.get("status")))}
        if what == "request":
            return S.request_view(t, _s(a.get("request")))
        if what == "find":
            return {"found": S.find(t, _s(a.get("phone")))}
        if what == "breaches":
            return {"breaches": S.breaches(t, _s(a.get("status")))}
        if what == "breach":
            return S.breach_view(t, _s(a.get("breach")))
        if what == "vendors":
            return {"vendors": S.vendors(t)}
        if what == "retention":
            return {"retention": S.retention(t)}
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status") or "waiting"))}
        if what == "settings":
            return S.settings(t)
        if what == "law":
            return S.law()
    except (S.DpoError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def dpo(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def dpo_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


DPO_HANDLERS = {"dpo": dpo, "dpo_dekho": dpo_dekho}
