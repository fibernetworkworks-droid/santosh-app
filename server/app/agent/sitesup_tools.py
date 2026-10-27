"""Site Sahayak tools (construction site supervisor). `sitesup_dekho` only reads; `sitesup` does the work. A material indent /
purchase, any DPR / message to the client and any stop-work order only become CARDS here: her tap in the app decides
(POST /api/sitesup/.../decide). Hoola never orders, pays, sends to the client or stops work by itself."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_OBJ = {"type": "object"}
SITESUP_TOOLS = [
    {"name": "sitesup", "description": (
        "Construction SITE SUPERVISOR's work (works on a Theka project when the site is linked; BOQ / measurement book / RA bills stay in "
        "theka). action=settings*: firm, supervisor, morning_time, dpr_time, day_hours, week_hours, lookahead_days, behind_pct, rates "
        "{trade: her daily rate}, cube_limits {individual_minus, mean_plus, sd} from her QA plan, rules. action=site: name or site, address, "
        "client, client_phone, client_email, engineer, start, finish, theka_project (link), status running|done|closed. action=plan: site, "
        "items [{code, name, location, unit, qty, start, finish, contractor, needs [{item, qty, unit}]}] or from_boq=true. action=progress: "
        "site, activity, qty (EXACTLY as reported), day, note, delay (reason if work stopped / slow), lost_hours, by_client. "
        "action=attendance: site, day, rows [{contractor, trade, count, hours} or {worker, trade, contractor, hours, gender}]. action=register "
        "(start, end) | register_file: wage-register NUMBERS (salary stays with payroll). action=material: site, item, qty, kind "
        "in|used|return|waste, unit, supplier, challan, vehicle, ok (quality), indent. action=indent: site, items [{item, qty, unit}], need_by, "
        "reason, supplier, supplier_phone, amount (ONLY from her / supplier's quote) -> a card for HER tap. action=indent_ordered: indent "
        "(after her tap). action=toolbox: site, topic, people. action=checklist: site, kind ppe|height|scaffold|excavation|pour|electrical|"
        "welfare, answers {item_id: true|false}, area (a critical 'no' prepares a stop-work card). action=incident: site, text (what / where), "
        "kind near_miss|first_aid|injury|death|dangerous|property, at, people, names, note (first aid / hospital / what was done), injury_off_since. action=reported*: incident, "
        "ref (her Form XI reference). action=stop: site, area, reason, contractor -> stop-work card for HER tap. action=pour: site, element, "
        "grade (M20...), volume (cum), cement (OPC 53 / PPC...), day, source, slump, checks, hot_dry, ages. action=cube: pour, age, results "
        "[N/mm2], sample, lab. action=snag: site, text, location, trade, contractor, due. action=snag_status: snag, status open|fixed|verified. "
        "action=photo: site, file_id, ref (snag / incident / pour id or number), stage. action=dpr: site, day, weather, tomorrow, remarks, "
        "to_phone -> DPR PDF + text, card for HER tap before it goes to the client. action=message: site, text, to_phone (card). "
        "action=forget*: site (DPDP, after the site is done). * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "site", "plan", "progress", "attendance", "register", "register_file", "material",
                                               "indent", "indent_ordered", "toolbox", "checklist", "incident", "reported", "stop", "pour", "cube",
                                               "snag", "snag_status", "photo", "dpr", "message", "forget"]},
         "site": {"type": "string"}, "name": {"type": "string"}, "address": {"type": "string"}, "client": {"type": "string"},
         "client_phone": {"type": "string"}, "client_email": {"type": "string"}, "engineer": {"type": "string"}, "start": {"type": "string"},
         "finish": {"type": "string"}, "end": {"type": "string"}, "theka_project": {"type": "string"}, "status": {"type": "string"},
         "firm": {"type": "string"}, "supervisor": {"type": "string"}, "morning_time": {"type": "string"}, "dpr_time": {"type": "string"},
         "day_hours": {"type": "number"}, "week_hours": {"type": "number"}, "lookahead_days": {"type": "integer"}, "behind_pct": {"type": "number"},
         "rates": _OBJ, "cube_limits": _OBJ, "rules": {"type": "array", "items": {"type": "string"}},
         "items": {"type": "array", "items": _OBJ}, "from_boq": {"type": "boolean"}, "activity": {"type": "string"}, "qty": {"type": "number"},
         "day": {"type": "string"}, "note": {"type": "string"}, "delay": {"type": "string"}, "lost_hours": {"type": "number"},
         "by_client": {"type": "boolean"}, "rows": {"type": "array", "items": _OBJ}, "item": {"type": "string"}, "kind": {"type": "string"},
         "unit": {"type": "string"}, "supplier": {"type": "string"}, "challan": {"type": "string"}, "vehicle": {"type": "string"},
         "ok": {"type": "boolean"}, "indent": {"type": "string"}, "need_by": {"type": "string"}, "reason": {"type": "string"},
         "supplier_phone": {"type": "string"}, "amount": {"type": "number"}, "topic": {"type": "string"}, "people": {"type": "integer"},
         "by": {"type": "string"}, "answers": _OBJ, "area": {"type": "string"}, "text": {"type": "string"}, "at": {"type": "string"},
         "names": {"type": "string"}, "injury_off_since": {"type": "string"}, "incident": {"type": "string"}, "ref": {"type": "string"},
         "contractor": {"type": "string"}, "element": {"type": "string"}, "grade": {"type": "string"}, "volume": {"type": "number"},
         "cement": {"type": "string"}, "source": {"type": "string"}, "slump": {"type": "string"}, "checks": _OBJ, "hot_dry": {"type": "boolean"},
         "ages": {"type": "array", "items": {"type": "integer"}}, "pour": {"type": "string"}, "age": {"type": "integer"},
         "results": {"type": "array", "items": {"type": "number"}}, "sample": {"type": "integer"}, "lab": {"type": "string"},
         "location": {"type": "string"}, "trade": {"type": "string"}, "due": {"type": "string"}, "snag": {"type": "string"},
         "file_id": {"type": "string"}, "stage": {"type": "string"}, "weather": {"type": "string"}, "tomorrow": {"type": "string"},
         "remarks": {"type": "string"}, "to_phone": {"type": "string"}},
         "required": ["action"]}},
    {"name": "sitesup_dekho", "description": (
        "Read the construction site (nothing changes). what=day (morning note: incidents to report, behind-plan work, material short, cube "
        "tests, curing, cards waiting) | sites | site | activities (plan vs done) | lookahead (days) | labour (day) | register (start, end) | "
        "material (balance) | indents (status) | safety (kind talk|check|incident) | stops | pours | cubes_due | snags (status) | reports | "
        "form_xi (incident) | checklists | rules | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "sites", "site", "activities", "lookahead", "labour", "register", "material", "indents",
                                             "safety", "stops", "pours", "cubes_due", "snags", "reports", "form_xi", "checklists", "rules", "settings"]},
         "site": {"type": "string"}, "day": {"type": "string"}, "days": {"type": "integer"}, "start": {"type": "string"}, "end": {"type": "string"},
         "status": {"type": "string"}, "kind": {"type": "string"}, "incident": {"type": "string"}},
         "required": ["what"]}},
]
SITESUP_LABELS = {"sitesup": "Site ka kaam likh raha hoon", "sitesup_dekho": "Site ka haal dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


_SITE_KEYS = ("address", "client", "client_phone", "client_email", "engineer", "start", "finish", "theka_project", "status")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..sitesup import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Site ka kaam graahak ke liye nahi.")
    site = _s(a.get("site"))
    try:
        if action in ("settings", "reported", "forget") and not _owner(ctx):
            raise ToolError("Sirf owner.")
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "site":
            if a.get("status") in ("done", "closed") and not _owner(ctx):
                raise ToolError("Site band karna sirf owner.")
            kw = {k: a[k] for k in _SITE_KEYS if k in a}
            if not kw.get("finish") and a.get("end"):
                kw["finish"] = a["end"]
            return S.save_site(t, _s(a.get("name")), site, **kw)
        if action == "plan":
            return S.plan(t, site, a.get("items"), bool(a.get("from_boq")))
        if action == "progress":
            return S.progress(t, site, _s(a.get("activity")), a.get("qty"), _s(a.get("day")), _s(a.get("note")), _s(a.get("delay")),
                              a.get("lost_hours"), a.get("by_client"), actor)
        if action == "attendance":
            one = {k: a[k] for k in ("contractor", "trade", "count", "hours", "worker", "gender") if k in a}
            if "count" not in one and "people" in a:
                one["count"] = a["people"]
            return S.attendance(t, site, a.get("rows"), _s(a.get("day")), actor, **one)
        if action == "register":
            return S.register(t, site, _s(a.get("start")), _s(a.get("end")))
        if action == "register_file":
            return S.register_file(t, site, _s(a.get("start")), _s(a.get("end")), conv)
        if action == "material":
            return S.material(t, site, _s(a.get("item")), a.get("qty"), _s(a.get("kind") or "in"), _s(a.get("unit")), _s(a.get("supplier")),
                              _s(a.get("challan")), _s(a.get("vehicle")), a.get("ok", True) is not False, _s(a.get("note")), _s(a.get("day")),
                              _s(a.get("indent")), actor)
        if action == "indent":
            items = a.get("items")
            if not items and a.get("item"):
                items = [{"item": a["item"], "qty": a.get("qty"), "unit": a.get("unit")}]
            return S.indent_request(t, site, items, _s(a.get("need_by")), _s(a.get("reason")), _s(a.get("supplier")), _s(a.get("supplier_phone")),
                                    a.get("amount"), actor, conv)
        if action == "indent_ordered":
            return S.indent_ordered(t, _s(a.get("indent")))
        if action == "toolbox":
            return S.toolbox(t, site, _s(a.get("topic")), a.get("people"), _s(a.get("by")), _s(a.get("note")), _s(a.get("day")), actor)
        if action == "checklist":
            return S.checklist(t, site, _s(a.get("kind")), a.get("answers") or {}, _s(a.get("area")), _s(a.get("day")), actor, conv)
        if action == "incident":
            return S.incident(t, site, _s(a.get("text")), _s(a.get("kind")), _s(a.get("at")), a.get("people"), _s(a.get("names")),
                              _s(a.get("action_taken") or a.get("note")), _s(a.get("injury_off_since")), actor, conv)
        if action == "reported":
            return S.incident_reported(t, _s(a.get("incident")), _s(a.get("ref")))
        if action == "stop":
            return S.stop_request(t, site, _s(a.get("area")), _s(a.get("reason")), "", _s(a.get("contractor")), actor, conv)
        if action == "pour":
            return S.pour(t, site, _s(a.get("element")), _s(a.get("grade")), a.get("volume"), _s(a.get("cement")), _s(a.get("day")),
                          _s(a.get("source")), _s(a.get("slump")), a.get("checks"), bool(a.get("hot_dry")), a.get("ages"), actor)
        if action == "cube":
            return S.cube_result(t, _s(a.get("pour")), a.get("age"), a.get("results"), int(a.get("sample") or 1), _s(a.get("lab")),
                                 _s(a.get("day")), conv)
        if action == "snag":
            return S.snag(t, site, _s(a.get("text")), _s(a.get("location")), _s(a.get("trade")), _s(a.get("contractor")), _s(a.get("due")), actor)
        if action == "snag_status":
            return S.snag_status(t, _s(a.get("snag")), _s(a.get("status")), actor)
        if action == "photo":
            if not a.get("file_id"):
                raise ToolError("Photo ka file_id chahiye (chat mein bheji photo).")
            return S.add_photo(t, b"", site, _s(a.get("ref")), _s(a.get("stage") or "site"), _s(a.get("note")), _s(a.get("file_id")))
        if action == "dpr":
            return S.dpr_request(t, site, _s(a.get("day")), _s(a.get("weather")), _s(a.get("tomorrow")), _s(a.get("remarks")),
                                 _s(a.get("to_phone")), actor, conv)
        if action == "message":
            return S.message_request(t, site, _s(a.get("text")), _s(a.get("to_phone")), conv)
        if action == "forget":
            return S.forget(t, site)
    except (S.SiteError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..sitesup import rules as R
    from ..sitesup import service as S
    t, site = ctx.tenant_id, _s(a.get("site"))
    if (getattr(ctx, "actor", "owner") or "").startswith("customer:"):
        raise ToolError("Site ka haal graahak ke liye nahi.")
    try:
        if what == "day":
            return S.day(t)
        if what == "sites":
            return {"sites": S.sites(t, _s(a.get("status")))}
        if what == "site":
            return S.site_view(t, site)
        if what == "activities":
            return {"activities": S.activities(t, site)}
        if what == "lookahead":
            return S.lookahead(t, site, a.get("days") or None)
        if what == "labour":
            return S.labour_day(t, site, _s(a.get("day")))
        if what == "register":
            return S.register(t, site, _s(a.get("start")), _s(a.get("end")))
        if what == "material":
            return {"material": S.material_balance(t, site)}
        if what == "indents":
            return {"indents": S.indents(t, _s(a.get("status")), site)}
        if what == "safety":
            return {"safety": S.safety_log(t, site, _s(a.get("kind")), int(a.get("days") or 30))}
        if what == "stops":
            return {"stops": S.stops(t, _s(a.get("status")))}
        if what == "pours":
            return {"pours": S.pours(t, site)}
        if what == "cubes_due":
            return {"cubes": S.cubes_due(t, int(a.get("days") or 3))}
        if what == "snags":
            return {"snags": S.snags(t, site, _s(a.get("status")))}
        if what == "reports":
            return {"reports": S.reports(t, site, _s(a.get("status")))}
        if what == "form_xi":
            return {"text": S.form_xi_text(t, _s(a.get("incident")))}
        if what == "checklists":
            return {k: {"label": v["label"], "items": [{"id": i, "q": q, "critical": c} for i, q, c in v["items"]]} for k, v in R.CHECKLISTS.items()}
        if what == "rules":
            return {"never": list(R.NEVER), "day_hours": R.DAY_HOURS, "week_hours": R.WEEK_HOURS, "ot_rate": R.OT_RATE,
                    "incidents": R.INCIDENT_KINDS, "topics": list(R.TOOLBOX_TOPICS)}
        if what == "settings":
            return S.settings(t)
    except (S.SiteError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def sitesup(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def sitesup_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


SITESUP_HANDLERS = {"sitesup": sitesup, "sitesup_dekho": sitesup_dekho}
