"""v0.98 Bima Sahayak tools. `bima_dekho` only reads; `bima` changes things. A recommendation reaches the client only
after HER Haan. Hoola never collects or pays a premium, never signs a proposal, never fills a health declaration for
the client and never promises a return the brochure doesn't guarantee."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

INSURE_TOOLS = [
    {"name": "bima", "description": (
        "Insurance agent's coworker (LIC / private life, health, motor): client book, policies, renewals, needs, claims. "
        "action=client: name or client (to update), phone, dob, gender, city, income (yearly), family [{name, relation, dob}], "
        "liabilities, goals, savings, whatsapp_ok, notes. action=policy: client, insurer, plan, type term|endowment|ulip|pension|"
        "health|topup|pa|critical|motor|home|travel, number, start, mode monthly|quarterly|half_yearly|yearly|single, premium, "
        "cover, next_due, nominee, commission_pct, group, members, pay_link (insurer's own https page), policy (id/number to "
        "update), status. action=import: file_id (renewal / policy list Excel or CSV from the insurer's agent portal), insurer. "
        "action=paid: policy, paid_on (client paid the insurer; Hoola never takes money). action=reminders: days (WhatsApp "
        "drafts she sends). action=reminded: policy. action=recommend: client, options [{insurer, plan, type, premium, cover, "
        "csr, features, guaranteed}] she got from insurers, note -> comparison + IRDAI need-analysis record. action=approve: "
        "advice_id, approve: ONLY when she says it may go to the client. action=claim: policy, kind death|health_cashless|"
        "health_reimbursement|motor|other, event_on, amount. action=claim_update: claim_id, have [documents received], "
        "status open|filed|query|settled|rejected, insurer_ref, filed_on, settled_amount, note. action=book_file (Excel). "
        "action=settings: agent_name, agent_code, remind_days, morning_time."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["client", "policy", "import", "paid", "reminders", "reminded", "recommend", "approve",
                                               "claim", "claim_update", "book_file", "settings"]},
         "name": {"type": "string"}, "client": {"type": "string"}, "phone": {"type": "string"}, "dob": {"type": "string"},
         "gender": {"type": "string"}, "city": {"type": "string"}, "income": {"type": "number"},
         "family": {"type": "array", "items": {"type": "object"}}, "liabilities": {"type": "number"}, "goals": {"type": "number"},
         "savings": {"type": "number"}, "whatsapp_ok": {"type": "boolean"}, "notes": {"type": "string"}, "insurer": {"type": "string"},
         "plan": {"type": "string"}, "type": {"type": "string"}, "number": {"type": "string"}, "start": {"type": "string"},
         "mode": {"type": "string"}, "premium": {"type": "number"}, "cover": {"type": "number"}, "next_due": {"type": "string"},
         "nominee": {"type": "string"}, "commission_pct": {"type": "number"}, "group": {"type": "boolean"},
         "members": {"type": "array", "items": {"type": "string"}}, "pay_link": {"type": "string"}, "policy": {"type": "string"},
         "status": {"type": "string"}, "file_id": {"type": "string"}, "paid_on": {"type": "string"}, "days": {"type": "integer"},
         "options": {"type": "array", "items": {"type": "object"}}, "note": {"type": "string"}, "advice_id": {"type": "string"},
         "approve": {"type": "boolean"}, "kind": {"type": "string"}, "event_on": {"type": "string"}, "amount": {"type": "number"},
         "claim_id": {"type": "string"}, "have": {"type": "array", "items": {"type": "string"}}, "insurer_ref": {"type": "string"},
         "filed_on": {"type": "string"}, "settled_amount": {"type": "number"}, "agent_name": {"type": "string"},
         "agent_code": {"type": "string"}, "remind_days": {"type": "integer"}, "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "bima_dekho", "description": (
        "Read insurance work (nothing changes). what=clients | policies (client, state due|grace|lapsed) | renewals (days) | "
        "needs (client: life + health cover gap) | claims (all for closed too) | birthdays (days) | book (persistency, "
        "premium, commission) | checklist (type, age: proposal documents) | claim_docs (kind) | tax (self_premium, "
        "parents_premium, self_senior, parents_senior: Sec 126 old regime) | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["clients", "policies", "renewals", "needs", "claims", "birthdays", "book", "checklist",
                                             "claim_docs", "tax", "settings"]},
         "client": {"type": "string"}, "state": {"type": "string"}, "days": {"type": "integer"}, "all": {"type": "boolean"},
         "type": {"type": "string"}, "age": {"type": "integer"}, "kind": {"type": "string"}, "self_premium": {"type": "number"},
         "parents_premium": {"type": "number"}, "self_senior": {"type": "boolean"}, "parents_senior": {"type": "boolean"}},
         "required": ["what"]}},
]
INSURE_LABELS = {"bima": "Bima ka kaam kar raha hoon", "bima_dekho": "Policy book dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..insure import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    by = "owner" if _owner(ctx) else (getattr(ctx, "actor", "") or "staff")
    try:
        if action == "client":
            return S.save_client(t, _s(a.get("name")), _s(a.get("client")), _s(a.get("phone")), _s(a.get("dob")), _s(a.get("gender")),
                                 _s(a.get("city")), a.get("metro"), a.get("income"), a.get("family"), a.get("liabilities"),
                                 a.get("goals"), a.get("savings"), a.get("whatsapp_ok"), _s(a.get("notes")))
        if action == "policy":
            return S.save_policy(t, _s(a.get("client")), _s(a.get("insurer")), _s(a.get("plan")), _s(a.get("type")), _s(a.get("number")),
                                 _s(a.get("start")), _s(a.get("mode")), a.get("premium"), a.get("cover"), _s(a.get("next_due")),
                                 nominee=_s(a.get("nominee")), commission_pct=a.get("commission_pct"), group=a.get("group"),
                                 members=a.get("members"), pay_link=_s(a.get("pay_link")), policy=_s(a.get("policy")),
                                 status=_s(a.get("status")), by=by)
        if action == "import":
            return S.import_policies(t, _s(a.get("file_id")), insurer=_s(a.get("insurer")))
        if action == "paid":
            return S.premium_paid(t, _s(a.get("policy")), _s(a.get("paid_on")), by)
        if action == "reminders":
            return S.reminder_drafts(t, a.get("days"))
        if action == "reminded":
            return S.mark_reminded(t, _s(a.get("policy")))
        if action == "recommend":
            return S.recommend(t, _s(a.get("client")), a.get("options") or [], _s(a.get("note")), conv)
        if action == "approve":
            if not _owner(ctx):
                raise ToolError("Graahak ko salah bhejne ki haan sirf owner.")
            return S.approve_advice(t, _s(a.get("advice_id")), bool(a.get("approve", True)))
        if action == "claim":
            return S.start_claim(t, _s(a.get("policy")), _s(a.get("kind")) or "other", _s(a.get("event_on")), a.get("amount"), by)
        if action == "claim_update":
            return S.update_claim(t, _s(a.get("claim_id")), a.get("have"), _s(a.get("status")), _s(a.get("insurer_ref")),
                                  _s(a.get("filed_on")), a.get("settled_amount"), _s(a.get("note")))
        if action == "book_file":
            return S.book_file(t, conv)
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            keys = ("agent_name", "agent_code", "remind_days", "morning_time")
            return S.save_settings(t, **{k: a[k] for k in keys if k in a})
    except (S.InsError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..insure import rules as R
    from ..insure import service as S
    t = ctx.tenant_id
    try:
        if what == "clients":
            return {"clients": S.clients(t)}
        if what == "policies":
            return {"policies": S.policies(t, _s(a.get("client")), _s(a.get("state")))}
        if what == "renewals":
            return S.renewals(t, a.get("days"))
        if what == "needs":
            return S.needs(t, _s(a.get("client")))
        if what == "claims":
            return {"claims": S.claims(t, not a.get("all"))}
        if what == "birthdays":
            return S.birthdays(t, int(a.get("days") or 7))
        if what == "book":
            return S.book(t)
        if what == "checklist":
            return S.proposal_checklist(_s(a.get("type")), a.get("age"))
        if what == "claim_docs":
            k = _s(a.get("kind"))
            return {"kind": k, "documents": R.CLAIM_DOCS.get(k, R.CLAIM_DOCS["other"])}
        if what == "tax":
            return R.health_deduction(float(a.get("self_premium") or 0), float(a.get("parents_premium") or 0),
                                      bool(a.get("self_senior")), bool(a.get("parents_senior")))
        if what == "settings":
            return S.settings(t)
    except (S.InsError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def bima(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def bima_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


INSURE_HANDLERS = {"bima": bima, "bima_dekho": bima_dekho}
