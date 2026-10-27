"""Archassist Sahayak tools (architect's assistant). `archassist_dekho` only reads; `archassist` does the work. Issuing drawings
(transmittal), 'submit karo' for a building permission / NOC, and invoices only become CARDS here: her tap in the app decides.
Hoola never logs in to BPMS / AutoDCR, never pays, never sends anything to a client or authority by itself."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

ARCHASSIST_TOOLS = [
    {"name": "archassist", "description": (
        "Architect's assistant, end to end. Her numbers only (plot area, road width, fee, % done): never invent; FSI / setback / "
        "parking checks are 'rule book se pakka kijiye', never final. action=settings*: firm, architect, coa_no, coa_valid_to, gstin, "
        "address, phone, email, upi_id, ruleset udcpr|udcpr_congested|dcpr_suburbs|dcpr_island|custom, terms, inv_prefix, morning_time. "
        "action=project: name (new) or project (number / name to update), client, client_phone, client_email, client_gstin, site, pin, "
        "city, authority maha_bpms|mcgm_autodcr|pmrda|midc_bpams|custom, ruleset, use, survey_no, cts_no, area (+ area_unit sqm|sqft|"
        "guntha|acre), road_width_m, road_widening_sqm, reservation_sqm, trees, near_airport, heritage, coastal, railway, highway, "
        "promoter, units, rera_no, status. action=doc: project, key (7/12, property card, title...), state have|missing|na, file_id. "
        "action=area: project, proposal {floors [{area_sqm}], bua_sqm, height_m, front_m, side_m, rear_m, units, parking, footprint_sqm, "
        "use}, overrides (HER rule numbers: basic, premium, tdr, front, side, rear, max_height, ground_coverage_pct, parking_per_unit). "
        "action=approval: project, key (building_permission|cc|plinth|oc|noc_fire|noc_tree|noc_airport|noc_env|...), status, ref_no, "
        "on, valid_to. action=submit: project, stage -> a card SHE taps (never say submitted). action=sub_update*: submission_id, "
        "status submitted|query|granted|refused, ref_no, valid_to. action=drawing: project, sheet, title, discipline A|S|E|P|M|F|L|I|C, "
        "scale, status, rev, file_id, note, revise (new revision). action=transmittal: project, to_kind client|authority|consultant|"
        "contractor, to_name, to_contact, sheets [..], purpose for_approval|for_construction|for_information|for_comments|"
        "for_submission|for_tender -> a card SHE taps. action=rera: project, building, pct_done (her site visit %), as_on. "
        "action=consultant: name, kind structural|mep|electrical|plumbing|hvac|fire|landscape|..., phone, email, firm. action=rfi: "
        "project, subject, question, party, sheets, due, direction out|in. action=rfi_answer: rfi_id, answer, close. action=meeting: "
        "project, points [{point, by, due}], attendees, on, place (minutes Word file + draft). action=fee*: project, basis percent|lump, "
        "percent, project_cost, lump, stages [{key,label,pct}]. action=invoice: project, stage (fee stage key) or amount + label -> a "
        "card SHE taps. action=paid*: invoice_id, amount, tds, on. action=register (Excel). action=forget* (DPDP, after done). "
        "* = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "project", "doc", "area", "approval", "submit", "sub_update", "drawing",
                                               "transmittal", "rera", "consultant", "rfi", "rfi_answer", "meeting", "fee", "invoice",
                                               "paid", "register", "forget"]},
         "project": {"type": "string"}, "name": {"type": "string"}, "client": {"type": "string"}, "client_phone": {"type": "string"},
         "client_email": {"type": "string"}, "client_gstin": {"type": "string"}, "site": {"type": "string"}, "pin": {"type": "string"},
         "city": {"type": "string"}, "authority": {"type": "string"}, "ruleset": {"type": "string"}, "use": {"type": "string"},
         "survey_no": {"type": "string"}, "cts_no": {"type": "string"}, "area": {"type": "string"}, "area_unit": {"type": "string"},
         "road_width_m": {"type": "number"}, "road_widening_sqm": {"type": "number"}, "reservation_sqm": {"type": "number"},
         "trees": {"type": "boolean"}, "near_airport": {"type": "boolean"}, "heritage": {"type": "boolean"}, "coastal": {"type": "boolean"},
         "railway": {"type": "boolean"}, "highway": {"type": "boolean"}, "promoter": {"type": "boolean"}, "units": {"type": "integer"},
         "rera_no": {"type": "string"}, "status": {"type": "string"}, "key": {"type": "string"}, "state": {"type": "string"},
         "file_id": {"type": "string"}, "proposal": {"type": "object"}, "overrides": {"type": "object"}, "ref_no": {"type": "string"},
         "on": {"type": "string"}, "valid_to": {"type": "string"}, "stage": {"type": "string"}, "submission_id": {"type": "string"},
         "sheet": {"type": "string"}, "title": {"type": "string"}, "discipline": {"type": "string"}, "scale": {"type": "string"},
         "rev": {"type": "string"}, "note": {"type": "string"}, "revise": {"type": "boolean"}, "to_kind": {"type": "string"},
         "to_name": {"type": "string"}, "to_contact": {"type": "string"}, "sheets": {"type": "array", "items": {"type": "string"}},
         "purpose": {"type": "string"}, "copies": {"type": "integer"}, "building": {"type": "string"}, "pct_done": {"type": "number"},
         "as_on": {"type": "string"}, "kind": {"type": "string"}, "phone": {"type": "string"}, "email": {"type": "string"},
         "firm": {"type": "string"}, "licence": {"type": "string"}, "subject": {"type": "string"}, "question": {"type": "string"},
         "party": {"type": "string"}, "due": {"type": "string"}, "direction": {"type": "string"}, "rfi_id": {"type": "string"},
         "answer": {"type": "string"}, "close": {"type": "boolean"}, "points": {"type": "array", "items": {"type": "object"}},
         "attendees": {"type": "array", "items": {"type": "string"}}, "place": {"type": "string"}, "basis": {"type": "string"},
         "percent": {"type": "number"}, "project_cost": {"type": "number"}, "lump": {"type": "number"},
         "stages": {"type": "array", "items": {"type": "object"}}, "amount": {"type": "number"}, "label": {"type": "string"},
         "invoice_id": {"type": "string"}, "tds": {"type": "number"}, "architect": {"type": "string"}, "coa_no": {"type": "string"},
         "coa_valid_to": {"type": "string"}, "gstin": {"type": "string"}, "address": {"type": "string"}, "upi_id": {"type": "string"},
         "terms": {"type": "string"}, "inv_prefix": {"type": "string"}, "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "archassist_dekho", "description": (
        "Read architect work (nothing changes). what=day (her taps waiting, late RFIs, approvals expiring, unpaid invoices, CoA date) | "
        "projects | project (project: plot, papers, area statement, drawings, approvals, RFIs, invoices) | area (last area statement) | "
        "drawings (register) | approvals (checklist + portal steps) | rfis | invoices | consultants | settings | rules (starter tables)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "projects", "project", "area", "drawings", "approvals", "rfis", "invoices",
                                             "consultants", "settings", "rules"]},
         "project": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
ARCHASSIST_LABELS = {"archassist": "Architect office ka kaam kar raha hoon", "archassist_dekho": "Project file dekh raha hoon"}

_OWNER_ONLY = ("settings", "sub_update", "fee", "paid", "forget")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


_PROJECT_KEYS = ("client", "client_phone", "client_email", "client_gstin", "site", "pin", "city", "authority", "ruleset", "use",
                 "survey_no", "cts_no", "area", "area_unit", "road_width_m", "road_widening_sqm", "reservation_sqm", "trees",
                 "near_airport", "heritage", "coastal", "railway", "highway", "promoter", "units", "rera_no", "status", "notes")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..archassist import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh architect office ka andar ka kaam hai.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    pr = _s(a.get("project"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "project":
            if a.get("status") in ("done", "dropped") and not _owner(ctx):
                raise ToolError("Project band karna sirf owner.")
            return S.save_project(t, _s(a.get("name")), pr, **{k: a[k] for k in _PROJECT_KEYS if k in a})
        if action == "doc":
            return S.doc(t, pr, _s(a.get("key")), _s(a.get("state") or "have"), _s(a.get("file_id")), _s(a.get("note")))
        if action == "area":
            return S.area_check(t, pr, a.get("proposal") or {}, a.get("overrides") or {}, conv)
        if action == "approval":
            if _s(a.get("status")) in ("granted", "not_needed") and not _owner(ctx):
                raise ToolError("Approval 'granted / not_needed' sirf owner bataye.")
            return S.approval_set(t, pr, _s(a.get("key")), _s(a.get("status")), _s(a.get("ref_no")), _s(a.get("on")), _s(a.get("valid_to")),
                                  _s(a.get("file_id")), _s(a.get("note")))
        if action == "submit":
            return S.submission_request(t, pr, _s(a.get("stage") or "building_permission"), conv, _s(a.get("note")))
        if action == "sub_update":
            return S.submission_update(t, _s(a.get("submission_id")), _s(a.get("status")), _s(a.get("ref_no")), _s(a.get("on")),
                                       _s(a.get("valid_to")), _s(a.get("note")))
        if action == "drawing":
            by = "Owner" if _owner(ctx) else _actor(ctx)[:40]
            return S.drawing(t, pr, _s(a.get("sheet")), _s(a.get("title")), _s(a.get("discipline")), _s(a.get("scale")), _s(a.get("status")),
                             _s(a.get("rev")), _s(a.get("file_id")), _s(a.get("note")), by, bool(a.get("revise")))
        if action == "transmittal":
            return S.transmittal_request(t, pr, _s(a.get("to_kind") or "client"), _s(a.get("to_name")), a.get("sheets") or [],
                                         _s(a.get("purpose") or "for_approval"), _s(a.get("to_contact")), _s(a.get("note")),
                                         int(a.get("copies") or 1), conv)
        if action == "rera":
            return S.rera_certificate(t, pr, _s(a.get("building")), a.get("pct_done"), _s(a.get("as_on")), None, conv)
        if action == "consultant":
            return S.consultant(t, _s(a.get("name")), _s(a.get("kind") or "structural"), _s(a.get("phone")), _s(a.get("email")),
                                _s(a.get("firm")), _s(a.get("licence")))
        if action == "rfi":
            return S.rfi(t, pr, _s(a.get("subject")), _s(a.get("question")), _s(a.get("party")), a.get("sheets") or [], _s(a.get("due")),
                         _s(a.get("direction") or "out"))
        if action == "rfi_answer":
            return S.rfi_answer(t, _s(a.get("rfi_id")), _s(a.get("answer")), bool(a.get("close")))
        if action == "meeting":
            return S.meeting(t, pr, a.get("points") or [], a.get("attendees") or [], _s(a.get("on")), _s(a.get("place")), conv)
        if action == "fee":
            return S.fee_set(t, pr, _s(a.get("basis")), a.get("percent"), a.get("project_cost"), a.get("lump"), a.get("stages"))
        if action == "invoice":
            return S.invoice_request(t, pr, _s(a.get("stage")), a.get("amount"), _s(a.get("label")), conv)
        if action == "paid":
            return S.invoice_paid(t, _s(a.get("invoice_id")), a.get("amount"), a.get("tds"), _s(a.get("on")), _s(a.get("ref_no")))
        if action == "register":
            return S.register_file(t, pr, conv)
        if action == "forget":
            return S.forget(t, pr)
    except (S.ArchError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..archassist import rules as R
    from ..archassist import service as S
    t, pr = ctx.tenant_id, _s(a.get("project"))
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh architect office ka andar ka kaam hai.")
    try:
        if what == "day":
            return S.day(t)
        if what == "projects":
            return {"projects": S.projects(t, _s(a.get("status")))}
        if what == "project":
            return S.project_view(t, pr)
        if what == "area":
            v = S.project_view(t, pr)
            return v.get("area") or {"say": "Area statement abhi nahi bana."}
        if what == "drawings":
            return {"drawings": S.drawings(t, pr)}
        if what == "approvals":
            return S.approvals(t, pr)
        if what == "rfis":
            return {"rfis": S.rfis(t, pr, _s(a.get("status")))}
        if what == "invoices":
            return {"invoices": S.invoices(t, pr, _s(a.get("status")))}
        if what == "consultants":
            return {"consultants": S.consultants(t)}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": R.NEVER, "check": R.CHECK_LINE, "rulesets": {k: v["label"] for k, v in R.RULESETS.items()},
                    "authorities": {k: v["label"] for k, v in R.AUTHORITIES.items()}, "gst": f"SAC {R.SAC} @ {R.GST_RATE:g}%",
                    "tds": "Client deducts 10% u/s 393(1) Income-tax Act 2025 above Rs 50,000 a year"}
    except (S.ArchError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def archassist(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def archassist_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


ARCHASSIST_HANDLERS = {"archassist": archassist, "archassist_dekho": archassist_dekho}
