"""Cosec Sahayak tools (company secretary's desk). `cosec_dekho` only reads; `cosec` does the work. Sending a meeting notice,
signing off minutes and "file karo" on an MCA form only become CARDS here: her tap in the app decides. Hoola never logs in to
MCA V3, never uses a DSC, never pays a fee. Everything is draft / jaankari (CS / vakil / CA se pakka)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

COSEC_TOOLS = [
    {"name": "cosec", "description": (
        "Company secretary's desk for her client companies / LLPs. Dates only from her words (incorporation, AGM, board meeting, "
        "appointment, allotment): never invent a date, fee or section; computed due dates are 'andaaza' when the AGM is not held yet. "
        "Directors: DIN only (Aadhaar / PAN never here; only a Pehchaan Locker {id:...} reference). "
        "action=settings*: firm, cs_name, membership_no (ACS/FCS), email, phone, windows ('30,15,7,1,0'), morning_time. "
        "action=entity: name (new) or entity (number / name / CIN to update), kind private|opc|public|listed|section8|llp, cin, llpin, "
        "roc, incorporated_on, paid_up, turnover (small company is worked out: <= Rs 10 crore / Rs 100 crore, private only), "
        "holding_or_sub, registered_office, email, auditor_name, auditor_frn, auditor_term_to_agm (FY like 2029-30), last_agm, "
        "deposits, msme_dues, dormant, startup, first_fy, status (closed / struck_off owner only). "
        "action=person: entity, name, role director|partner|kmp|member, person (id / DIN / folio to update), din, designation, "
        "appointed_on, ceased_on, din_on, kyc_on, email, phone, address, id_ref, folio, shares, share_class, nominal. "
        "action=calendar: entity, fy -> annual MCA forms with due dates (AOC-4, MGT-7/7A, ADT-1, DPT-3, MSME-1, DIR-3 KYC, LLP 8/11). "
        "action=event: entity, kind (director_appoint|director_resign|allotment|transfer|ro_change_local|ro_change_city|ro_change_state|"
        "charge_create|charge_satisfy|ben_declaration|auditor_appoint|auditor_resign|special_resolution|incorporation|partner_change|"
        "kyc_change) or words (her words, the kind is guessed), on (date), details {name, din, designation, allottees [{name, shares}], "
        "from, to, shares, address, holder, amount, property, charge_id, frn, term_to_agm} -> registers updated + filings with due dates. "
        "action=file: filing_id -> a filing CARD she taps (never say filed). action=filed*: filing_id, srn, filed_on, fee (after SHE "
        "filed on MCA). action=skip*: filing_id, reason. "
        "action=meeting: entity, kind board|agm|egm|committee, on, time, place, mode physical|vc|hybrid, agenda [..], fy (AGM), chair. "
        "action=meeting_update: meeting, on, time, place, agenda. action=notice: meeting, send_on, mode email|hand|post|courier, "
        "shorter_consent -> notice CARD she taps (SS-1 7 / s.101 21 clear days checked). action=attendance: meeting, present [names / "
        "DIN], interested [..], chair, members_count -> quorum. action=resolution: meeting (or entity for circular), kind board|ordinary|"
        "special|circular, text, votes_for, votes_against, mgt14. action=minutes_draft / minutes_edit (text) / minutes (sign-off CARD "
        "she taps): meeting. action=registers (Excel). action=forget* (DPDP, after closed). * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "entity", "person", "calendar", "event", "file", "filed", "skip", "meeting",
                                               "meeting_update", "notice", "attendance", "resolution", "minutes_draft", "minutes_edit",
                                               "minutes", "registers", "forget"]},
         "entity": {"type": "string"}, "name": {"type": "string"}, "kind": {"type": "string"}, "cin": {"type": "string"},
         "llpin": {"type": "string"}, "roc": {"type": "string"}, "incorporated_on": {"type": "string"}, "paid_up": {"type": "string"},
         "turnover": {"type": "string"}, "holding_or_sub": {"type": "boolean"}, "registered_office": {"type": "string"},
         "email": {"type": "string"}, "auditor_name": {"type": "string"}, "auditor_frn": {"type": "string"},
         "auditor_term_to_agm": {"type": "string"}, "last_agm": {"type": "string"}, "deposits": {"type": "boolean"},
         "msme_dues": {"type": "boolean"}, "dormant": {"type": "boolean"}, "startup": {"type": "boolean"}, "first_fy": {"type": "boolean"},
         "status": {"type": "string"}, "notes": {"type": "string"}, "role": {"type": "string"}, "person": {"type": "string"},
         "din": {"type": "string"}, "designation": {"type": "string"}, "appointed_on": {"type": "string"}, "ceased_on": {"type": "string"},
         "din_on": {"type": "string"}, "kyc_on": {"type": "string"}, "phone": {"type": "string"}, "address": {"type": "string"},
         "id_ref": {"type": "string"}, "folio": {"type": "string"}, "shares": {"type": "string"}, "share_class": {"type": "string"},
         "nominal": {"type": "string"}, "fy": {"type": "string"}, "on": {"type": "string"}, "words": {"type": "string"},
         "details": {"type": "object"}, "filing_id": {"type": "string"}, "srn": {"type": "string"}, "filed_on": {"type": "string"},
         "fee": {"type": "number"}, "reason": {"type": "string"}, "meeting": {"type": "string"}, "time": {"type": "string"},
         "place": {"type": "string"}, "mode": {"type": "string"}, "agenda": {"type": "array", "items": {"type": "string"}},
         "chair": {"type": "string"}, "send_on": {"type": "string"}, "shorter_consent": {"type": "boolean"},
         "present": {"type": "array", "items": {"type": "string"}}, "interested": {"type": "array", "items": {"type": "string"}},
         "members_count": {"type": "integer"}, "text": {"type": "string"}, "votes_for": {"type": "number"},
         "votes_against": {"type": "number"}, "mgt14": {"type": "boolean"}, "firm": {"type": "string"}, "cs_name": {"type": "string"},
         "membership_no": {"type": "string"}, "windows": {"type": "string"}, "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "cosec_dekho", "description": (
        "Read the company secretary's desk (nothing changes). what=day (overdue / due in 30 days / her cards waiting / notices to send / "
        "minutes to sign / next board meeting) | entities | entity (entity: master, directors, members, charges, meetings, filings, "
        "board-meeting gaps) | filings (entity, status, within_days) | meetings (entity, status) | meeting (meeting) | resolutions "
        "(entity) | settings | rules (forms with due-date rules, events, what Hoola never does)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "entities", "entity", "filings", "meetings", "meeting", "resolutions", "settings", "rules"]},
         "entity": {"type": "string"}, "meeting": {"type": "string"}, "status": {"type": "string"}, "within_days": {"type": "integer"}},
         "required": ["what"]}},
]
COSEC_LABELS = {"cosec": "Company secretary ka kaam kar raha hoon", "cosec_dekho": "Company ki file dekh raha hoon"}

_OWNER_ONLY = ("settings", "filed", "skip", "forget")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


_ENT_ARGS = ("kind", "cin", "llpin", "roc", "incorporated_on", "paid_up", "turnover", "holding_or_sub", "registered_office", "email",
             "auditor_name", "auditor_frn", "auditor_term_to_agm", "last_agm", "status", "notes", "deposits", "msme_dues", "dormant",
             "startup", "first_fy")
_PERSON_ARGS = ("din", "designation", "address", "share_class", "folio", "appointed_on", "ceased_on", "din_on", "kyc_on", "email",
                "phone", "id_ref", "shares", "nominal")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..cosec import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh company secretary office ka andar ka kaam hai.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    en = _s(a.get("entity"))
    mt = _s(a.get("meeting"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "entity":
            if _s(a.get("status")) in ("closed", "struck_off") and not _owner(ctx):
                raise ToolError("Entity band karna sirf owner.")
            return S.save_entity(t, _s(a.get("name")), en, **{k: a[k] for k in _ENT_ARGS if k in a})
        if action == "person":
            return S.person(t, en, _s(a.get("name")), _s(a.get("role") or "director"), _s(a.get("person")),
                            **{k: a[k] for k in _PERSON_ARGS if k in a})
        if action == "calendar":
            return S.calendar(t, en, _s(a.get("fy")))
        if action == "event":
            det = a.get("details") if isinstance(a.get("details"), dict) else {}
            return S.event(t, en, _s(a.get("kind")), _s(a.get("on")), _s(a.get("words")), det, conv)
        if action == "file":
            return S.filing_request(t, _s(a.get("filing_id")), conv)
        if action == "filed":
            return S.filing_done(t, _s(a.get("filing_id")), _s(a.get("srn")), _s(a.get("filed_on")), a.get("fee"))
        if action == "skip":
            return S.filing_skip(t, _s(a.get("filing_id")), _s(a.get("reason")))
        if action == "meeting":
            return S.meeting_new(t, en, _s(a.get("kind") or "board"), _s(a.get("on")), _s(a.get("time")), _s(a.get("place")),
                                 _s(a.get("mode") or "physical"), a.get("agenda") or [], _s(a.get("fy")), _s(a.get("chair")), conv)
        if action == "meeting_update":
            return S.meeting_update(t, mt, **{k: a[k] for k in ("on", "time", "place", "chair", "mode", "agenda") if k in a})
        if action == "notice":
            sc = a.get("shorter_consent")
            return S.notice_request(t, mt, _s(a.get("send_on")), _s(a.get("mode")), None if sc is None else bool(sc), conv)
        if action == "attendance":
            mc = a.get("members_count")
            return S.attendance(t, mt, a.get("present") or [], a.get("interested") or [], _s(a.get("chair")), int(mc) if mc else None)
        if action == "resolution":
            kind = _s(a.get("kind") or ("circular" if not mt else "board"))
            return S.resolution(t, mt, en, kind, _s(a.get("text")), _s(a.get("on")), a.get("votes_for"), a.get("votes_against"),
                                bool(a.get("mgt14")))
        if action == "minutes_draft":
            return S.minutes_draft(t, mt)
        if action == "minutes_edit":
            return S.minutes_edit(t, mt, _s(a.get("text")))
        if action == "minutes":
            return S.minutes_request(t, mt, conv)
        if action == "registers":
            return S.registers_file(t, en, conv)
        if action == "forget":
            return S.forget(t, en)
    except (S.CosecError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..cosec import rules as R
    from ..cosec import service as S
    t, en = ctx.tenant_id, _s(a.get("entity"))
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh company secretary office ka andar ka kaam hai.")
    try:
        if what == "day":
            S.ensure(t)
            return S.day(t)
        if what == "entities":
            return {"entities": S.entities(t, _s(a.get("status")))}
        if what == "entity":
            return S.entity_view(t, en)
        if what == "filings":
            wd = a.get("within_days")
            return {"filings": S.filings(t, en, _s(a.get("status")), int(wd) if wd not in (None, "") else None)}
        if what == "meetings":
            return {"meetings": S.meetings(t, en, _s(a.get("status")))}
        if what == "meeting":
            return next((m for m in S.meetings(t) if m["id"] == _s(a.get("meeting")) or m["number"] == _s(a.get("meeting")).upper()),
                        {"say": "Meeting nahi mili."})
        if what == "resolutions":
            return {"resolutions": S.resolutions(t, en)}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": R.NEVER, "draft_line": R.DRAFT_LINE, "forms": {k: f"{v['label']}: {v['what']} ({v['law']})" for k, v in R.FORMS.items()},
                    "events": {k: v["label"] for k, v in R.EVENTS.items()}}
    except (S.CosecError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def cosec(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def cosec_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


COSEC_HANDLERS = {"cosec": cosec, "cosec_dekho": cosec_dekho}
