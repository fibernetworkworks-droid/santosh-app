"""Compliance Sahayak tools (compliance officer). `compliance_dekho` only reads; `compliance` does the work. 'Portal par file karo'
and the monthly certificate sign-off only become CARDS here: her app tap decides. Marking a duty done needs an evidence file or the
owner's own word. Hoola never logs in to a portal, never pays a challan, never submits a return. Jaankari only, not legal advice."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

COMPLIANCE_TOOLS = [
    {"name": "compliance", "description": (
        "Compliance officer for HER business: statutory calendar (GST, TDS / TCS, PF / ESIC, PT, LWF, labour-code returns, Shop Act, "
        "FSSAI, fire NOC, pollution consent, trade / factory licence, MSME-1, ROC basics) with due dates, owners, evidence and status. "
        "Never invent a date, fee, section or penalty: the catalogue has dated starters with sources, her own date wins; say 'CA / CS se "
        "pakka'. GST / payroll / Daftar renewals / Company Secretary items are READ from those Sahayaks, not copied. "
        "action=facts*: entity proprietor|partnership|llp|pvt_ltd|public_ltd|opc|trust|society|huf, state (name or GST code), employees, "
        "contract_workers, contractor (bool), turnover (Rs, last FY), gstin, gst_scheme monthly|qrmp|composition, tan, salary_tds, tcs, "
        "pt_yearly, sectors [shop, office, restaurant, factory, manufacturing, food, it, trading, construction...], food_kind none|"
        "manufacturer|importer|packer|relabeller|trader|restaurant|milk|storage|transport, food_licence registration|state|central, "
        "pollution none|white|green|orange|red, factory, fire_noc, msme_dues, agm_date, licences {fssai|consent|fire|shop|trade|factory|"
        "contract: valid-till date} -> calendar rebuilt. action=settings*: firm, signatory, designation, owners {area: name}, team "
        "[{name, phone}], windows (reminder days e.g. '7,3,1,0'), morning_time. action=build (refresh calendar). action=add*: label, due, "
        "area, owner (her own duty). action=update: item (C-0003), due* (her date), owner, note. action=evidence: item, file_id (challan / "
        "ack / certificate from chat). action=done: item, file_id (or her_word=true, owner only), ack (ARN / SRN / challan no.), on. "
        "action=na*: item, reason. action=reopen*: item. action=filing: item -> a card SHE taps (never say filed; she logs in, pays and "
        "submits herself). action=certificate: month YYYY-MM -> sign-off card SHE taps. action=nudge: item (WhatsApp draft to the owner of "
        "the task; she sends). action=register (Excel). action=forget*: name (DPDP, person who left). * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["facts", "settings", "build", "add", "update", "evidence", "done", "na", "reopen", "filing",
                                               "certificate", "nudge", "register", "forget"]},
         "item": {"type": "string"}, "entity": {"type": "string"}, "state": {"type": "string"}, "employees": {"type": "integer"},
         "contract_workers": {"type": "integer"}, "contractor": {"type": "boolean"}, "turnover": {"type": "number"},
         "gstin": {"type": "string"}, "gst_scheme": {"type": "string"}, "tan": {"type": "boolean"}, "salary_tds": {"type": "boolean"},
         "tcs": {"type": "boolean"}, "pt_yearly": {"type": "number"}, "sectors": {"type": "array", "items": {"type": "string"}},
         "food_kind": {"type": "string"}, "food_licence": {"type": "string"}, "pollution": {"type": "string"}, "factory": {"type": "boolean"},
         "fire_noc": {"type": "boolean"}, "msme_dues": {"type": "boolean"}, "agm_date": {"type": "string"},
         "licences": {"type": "object"}, "firm": {"type": "string"}, "signatory": {"type": "string"}, "designation": {"type": "string"},
         "owners": {"type": "object"}, "team": {"type": "array", "items": {"type": "object"}}, "windows": {"type": "string"},
         "morning_time": {"type": "string"}, "label": {"type": "string"}, "due": {"type": "string"}, "area": {"type": "string"},
         "owner": {"type": "string"}, "note": {"type": "string"}, "file_id": {"type": "string"}, "her_word": {"type": "boolean"},
         "ack": {"type": "string"}, "on": {"type": "string"}, "reason": {"type": "string"}, "month": {"type": "string"},
         "name": {"type": "string"}},
         "required": ["action"]}},
    {"name": "compliance_dekho", "description": (
        "Read compliance (nothing changes). what=day (late with penalty andaaza, this week, her taps waiting, questions) | applicability "
        "(what applies and why, with sources; questions she must answer) | calendar (area, state late|due|upcoming|no_date|done, ahead days; "
        "incl. linked GST / payroll / Daftar / CS rows) | item (item) | certificate (month: draft content) | rules (catalogue + sources) | "
        "settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "applicability", "calendar", "item", "certificate", "rules", "settings"]},
         "item": {"type": "string"}, "area": {"type": "string"}, "state": {"type": "string"}, "ahead": {"type": "integer"},
         "month": {"type": "string"}},
         "required": ["what"]}},
]
COMPLIANCE_LABELS = {"compliance": "Compliance ka kaam kar raha hoon", "compliance_dekho": "Compliance calendar dekh raha hoon"}

_OWNER_ONLY = ("facts", "settings", "add", "na", "reopen", "forget")
_FACT_ARGS = ("entity", "state", "employees", "contract_workers", "contractor", "turnover", "gstin", "gst_scheme", "tan", "salary_tds",
              "tcs", "pt_yearly", "sectors", "food_kind", "food_licence", "pollution", "factory", "fire_noc", "msme_dues", "agm_date",
              "licences")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..compliance import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh business ka andar ka compliance kaam hai.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    it = _s(a.get("item"))
    try:
        if action == "facts":
            facts = {k: a[k] for k in _FACT_ARGS if k in a}
            if not facts:
                raise ToolError("Koi fact nahi diya.")
            v = S.save_settings(t, facts)
            ap = S.applicability(t)
            return {"facts": v["facts"], "applies": [x["label"] for x in ap["items"] if x["applies"]], "questions": ap["questions"],
                    "say": ap["say"]}
        if action == "settings":
            return S.save_settings(t, None, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "build":
            return S.build(t)
        if action == "add":
            return S.add_custom(t, _s(a.get("label")), _s(a.get("due")), _s(a.get("area") or "custom"), _s(a.get("owner")),
                                _s(a.get("note")), actor)
        if action == "update":
            return S.item_update(t, it, _s(a.get("due")), a.get("owner"), _s(a.get("note")), actor)
        if action == "evidence":
            return S.add_evidence(t, it, _s(a.get("file_id")), _s(a.get("note")), actor)
        if action == "done":
            if a.get("her_word") and not _owner(ctx):
                raise ToolError("Bina saboot 'ho gaya' sirf owner keh sakti hain; file bhejiye.")
            return S.mark_done(t, it, _s(a.get("file_id")), _s(a.get("note")), bool(a.get("her_word")), _s(a.get("ack")),
                               _s(a.get("on")), actor)
        if action == "na":
            return S.mark_na(t, it, _s(a.get("reason")), actor)
        if action == "reopen":
            return S.reopen(t, it, actor)
        if action == "filing":
            return S.filing_request(t, it, conv)
        if action == "certificate":
            return S.cert_request(t, _s(a.get("month")), conv)
        if action == "nudge":
            return S.nudge(t, it)
        if action == "register":
            return S.register_file(t, conv)
        if action == "forget":
            return S.forget_person(t, _s(a.get("name")))
    except (S.CompError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..compliance import rules as R
    from ..compliance import service as S
    t = ctx.tenant_id
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh business ka andar ka compliance kaam hai.")
    try:
        if what == "day":
            return S.day(t)
        if what == "applicability":
            return S.applicability(t)
        if what == "calendar":
            return S.calendar(t, int(a.get("ahead") or 60), _s(a.get("area")), _s(a.get("state")))
        if what == "item":
            return S.item(t, _s(a.get("item")))
        if what == "certificate":
            return S.certificate(t, _s(a.get("month")))
        if what == "rules":
            return {"catalogue": [{"key": c["key"], "label": c["label"], "area": c["area"], "source": R.source(c)} for c in R.CATALOGUE],
                    "never": R.NEVER, "check": R.CHECK_LINE}
        if what == "settings":
            return S.settings(t)
    except (S.CompError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def compliance(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def compliance_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


COMPLIANCE_HANDLERS = {"compliance": compliance, "compliance_dekho": compliance_dekho}
