"""Notary Sahayak tools (notary public / documentation desk). `notary_dekho` only reads; `notary` does the work.
Final print only becomes a CARD here (her tap in the app decides). Notarising / signing / sealing / e-stamping are her acts;
the register line + receipt are written only when SHE (the owner) says it is done. Hoola never takes or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_PARTY = {"type": "object", "description": "name, relation so|do|wo|ho, relative, age, occupation, address, gender m|f, phone; "
                                            "identity ONLY as id_ref ({id:...} from her Pehchaan Locker) or id_number + id_kind "
                                            "(it goes straight into the locker, never stored here)"}

NOTARY_TOOLS = [
    {"name": "notary", "description": (
        "Notary & documentation desk. Documents are drafted by CODE from the party's facts (never invent a fact: missing = [blank]); "
        "this is a draft, not legal advice. action=draft: kind aff_name_change|aff_address|aff_gap_year|aff_income|aff_lost_document|"
        "aff_general|declaration|self_declaration|rent_summary|poa_general|poa_special|indemnity|noc (or words: her exact words, kind is "
        "guessed), lang en|hi|mr, party, facts {field: value} (see notary_dekho what=kinds), others [party] (e.g. second executant), state. "
        "action=update: doc, party / facts / lang / state. action=text: doc, text (her own wording). action=copy: doc, lang. "
        "action=translate: doc, to (any language; other than en/hi/mr = Lekhak 'not certified' draft). action=rentdesk: tenancy "
        "(Rentdesk T-0001) -> rent summary. action=stamp: doc, ref (e-stamp UIN / e-SBTR / franking no.), mode, state. action=print: doc "
        "-> a final-print CARD she taps (never say printed). action=notarise*: doc (or executants + contents for a document not made "
        "here), act, fee, pages, payer, mode cash|upi, charges {typing, print, xerox}, remarks -> Form XV register line + fee receipt, ONLY "
        "after she says she notarised it. action=correct*: serial, remarks. action=executed: doc, notary (desk mode: a notary did it). "
        "action=receipt*: payer, charges, mode. action=register_file*: year. action=apostille: doc_title or doc, doc_type personal|"
        "educational|commercial|affidavit|poa|other, country, hague yes|no, party, phone. action=apostille_step: apostille, step, done, "
        "hague. action=settings*: mode notary|desk, office, notary_name, reg_no, area, appointed_by, cop_valid_to, address, phone, state, "
        "default_lang, morning_time. action=stamp_rate*: state, key (affidavit|declaration|...), amount (from HER state's schedule), mode. "
        "action=fee*: act, amount (her fee; Rule 10 cap checked). action=forget*: doc (DPDP). * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["draft", "update", "text", "copy", "translate", "rentdesk", "stamp", "print", "notarise",
                                               "correct", "executed", "receipt", "register_file", "apostille", "apostille_step", "settings",
                                               "stamp_rate", "fee", "forget"]},
         "doc": {"type": "string"}, "kind": {"type": "string"}, "lang": {"type": "string"}, "words": {"type": "string"},
         "party": _PARTY, "others": {"type": "array", "items": _PARTY}, "facts": {"type": "object"}, "state": {"type": "string"},
         "text": {"type": "string"}, "to": {"type": "string"}, "tenancy": {"type": "string"}, "ref": {"type": "string"},
         "mode": {"type": "string"}, "act": {"type": "string"}, "fee": {"type": "number"}, "pages": {"type": "integer"},
         "payer": {"type": "string"}, "charges": {"type": "object"}, "remarks": {"type": "string"}, "contents": {"type": "string"},
         "executants": {"type": "array", "items": _PARTY}, "stamp_text": {"type": "string"}, "serial": {"type": "string"},
         "notary": {"type": "string"}, "on": {"type": "string"}, "year": {"type": "integer"}, "doc_title": {"type": "string"},
         "doc_type": {"type": "string"}, "country": {"type": "string"}, "hague": {"type": "string"}, "phone": {"type": "string"},
         "apostille": {"type": "string"}, "step": {"type": "string"}, "done": {"type": "boolean"}, "key": {"type": "string"},
         "amount": {"type": "number"}, "office": {"type": "string"}, "notary_name": {"type": "string"}, "reg_no": {"type": "string"},
         "area": {"type": "string"}, "appointed_by": {"type": "string"}, "cop_valid_to": {"type": "string"},
         "address": {"type": "string"}, "default_lang": {"type": "string"}, "morning_time": {"type": "string"},
         "note": {"type": "string"}},
         "required": ["action"]}},
    {"name": "notary_dekho", "description": (
        "Read the notary desk (nothing changes). what=day | docs (status, q) | doc (doc: text, blanks, checks, stamp + e-stamp steps) | "
        "kinds (document kinds + their fields) | register (year: Form XV lines, IDs masked, counts for the Form XIV annual return) | "
        "apostilles | settings (her stamp table, fees, Rule 10 caps) | rules (what Hoola never does + sources)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "docs", "doc", "kinds", "register", "apostilles", "settings", "rules"]},
         "doc": {"type": "string"}, "status": {"type": "string"}, "q": {"type": "string"}, "year": {"type": "integer"}},
         "required": ["what"]}},
]
NOTARY_LABELS = {"notary": "Notary ka kaagaz taiyaar kar raha hoon", "notary_dekho": "Notary register / documents dekh raha hoon"}

_OWNER_ONLY = ("notarise", "correct", "receipt", "register_file", "settings", "stamp_rate", "fee", "forget")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..notary import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh notary office ka andar ka kaam hai.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner (notary) yeh kar sakti hain.")
    d = _s(a.get("doc"))
    try:
        if action == "draft":
            return S.draft(t, _s(a.get("kind")), _s(a.get("lang")), a.get("party") or {}, a.get("facts") or {}, _s(a.get("words")),
                           _s(a.get("state")), conv, "", a.get("others") or [])
        if action == "update":
            return S.update(t, d, a.get("party") or None, a.get("facts") or None, _s(a.get("lang")), _s(a.get("state")), conv,
                            a.get("others"))
        if action == "text":
            return S.edit_text(t, d, _s(a.get("text")), conv)
        if action == "copy":
            return S.copy(t, d, _s(a.get("lang")), conv)
        if action == "translate":
            return S.translate(t, d, _s(a.get("to")), conv)
        if action == "rentdesk":
            return S.from_rentdesk(t, _s(a.get("tenancy")), _s(a.get("lang")), conv)
        if action == "stamp":
            return S.stamp_ref(t, d, _s(a.get("ref")), _s(a.get("mode")), _s(a.get("state")))
        if action == "print":
            return S.print_request(t, d, conv)
        if action == "notarise":
            return S.notarise(t, d, _s(a.get("act")), a.get("fee"), a.get("executants") or [], _s(a.get("contents")),
                              _s(a.get("stamp_text")), _s(a.get("payer")), _s(a.get("mode") or "cash"), _s(a.get("ref")),
                              a.get("charges") or {}, _s(a.get("remarks")), int(a.get("pages") or 1), conv)
        if action == "correct":
            return S.correct_entry(t, _s(a.get("serial")), _s(a.get("remarks")), conv)
        if action == "executed":
            return S.executed(t, d, _s(a.get("notary")), _s(a.get("on")))
        if action == "receipt":
            return S.receipt(t, _s(a.get("payer")), a.get("charges") or {}, _s(a.get("mode") or "cash"), _s(a.get("ref")), d, conv)
        if action == "register_file":
            return S.register_file(t, a.get("year"), conv)
        if action == "apostille":
            return S.apostille(t, _s(a.get("doc_title")), _s(a.get("doc_type") or "personal"), _s(a.get("country")), a.get("hague"),
                               _s(a.get("party")), _s(a.get("phone")), d, conv)
        if action == "apostille_step":
            return S.apostille_update(t, _s(a.get("apostille")), _s(a.get("step")), bool(a.get("done", True)), a.get("hague"),
                                      _s(a.get("note")))
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "stamp_rate":
            return S.set_stamp(t, _s(a.get("state")), _s(a.get("key")), a.get("amount"), _s(a.get("mode")))
        if action == "fee":
            return S.set_fee(t, _s(a.get("act")), a.get("amount"))
        if action == "forget":
            return S.forget(t, d)
    except (S.NotaryError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..notary import rules as R
    from ..notary import service as S
    t = ctx.tenant_id
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh notary office ka andar ka kaam hai.")
    try:
        if what == "day":
            return S.day(t)
        if what == "docs":
            return {"docs": S.docs(t, _s(a.get("status")), _s(a.get("q")))}
        if what == "doc":
            return S.get_doc(t, _s(a.get("doc")))
        if what == "kinds":
            return {"kinds": {k: {"label": v["label"], "fields": [f"{x}{'*' if req else ''} ({lab})" for x, lab, req in v["fields"]]}
                              for k, v in R.KINDS.items()},
                    "party": [f"{x}{'*' if req else ''} ({lab})" for x, lab, req in R.PARTY_FIELDS], "langs": R.LANGS}
        if what == "register":
            if not _owner(ctx):
                raise ToolError("Register sirf owner dekh sakti hain.")
            return S.register(t, a.get("year"))
        if what == "apostilles":
            return {"apostilles": S.apostilles(t, _s(a.get("status")))}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": R.NEVER, "not_advice": R.NOT_ADVICE, "sources": R.SOURCES, "acts": {k: v["label"] for k, v in R.ACTS.items()}}
    except (S.NotaryError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def notary(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def notary_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


NOTARY_HANDLERS = {"notary": notary, "notary_dekho": notary_dekho}
