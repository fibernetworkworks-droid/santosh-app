"""Film Desk tools (AI film producer on Hoola Video Studio). `film_desk_dekho` only reads; `film_desk` does the work.

Paid AI shots: `spend` only asks the STUDIO, which makes its own price card; only her tap there spends. A real person's face /
voice goes to the studio only with a recorded consent in the register. Messages to outside people and marking a film released
are CARDS for her tap. Hoola never posts, uploads, files with CBFC or pays."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "new", "update", "script", "script_set", "script_restore", "cast", "shots", "shot", "storyboard",
            "preview", "spend", "assemble", "person", "consent", "withdraw", "forget", "right", "rating", "cbfc", "tick",
            "message", "release", "schedule", "callsheet", "budget_plan", "festival", "window", "waterfall", "deliverable", "localise", "royalty"]
_OWNER_ONLY = {"settings", "consent", "withdraw", "forget", "rating", "cbfc", "budget_plan", "window", "waterfall", "royalty"}

FILMDESK_TOOLS = [
    {"name": "film_desk", "description": (
        "AI film producer desk on Video Studio. Never invent facts, prices or consent. action=new: title, logline, format "
        "short|reel|ad|music_video|web_episode|feature|documentary|explainer, language, targets [youtube, instagram, ott, festival, "
        "theatrical, whatsapp, tv], budget_inr*. script: notes (Claude writes from her words). script_set: text (her script). "
        "script_restore: n. cast: character, person (P-001 = real, needs recorded consent) or description (AI character). shots: "
        "scene (optional). shot: shot, prompt/camera/duration/dialogue or delete. storyboard: push to studio. preview: free "
        "animatic. spend: quality draft|final, shot_ids -> STUDIO price card, only her tap spends. assemble. person: name, role, "
        "phone, real, public_figure, minor, photo_files. consent*: person, how signed_form|video|audio|email|written, file_id "
        "(proof), uses [ai_likeness, ai_voice, real_footage, real_voice, name, promo], until, guardian. withdraw* / forget*: "
        "person. right: kind music|song|voice|stock|font|script|lyrics|footage|artwork|ai_model, title, owner, licence "
        "own|commissioned|licensed|royalty_free|ai_generated|public_domain, sync, platforms, until, file_id. rating*: rating "
        "U|UA7|UA13|UA16|A. cbfc*: category, number, date. tick: key, done. message: msg_kind consent_request|rights_request|"
        "festival|distributor|custom, person / phone, text, uses, item -> CARD. release: force, reason -> CARD. Every action "
        "takes project (F-0001). * = owner only. PRODUCTION layer (all in code, nothing sent or paid): schedule: "
        "start_date YYYY-MM-DD, day_hours, setup_hours, hours_per_screen_minute (her real numbers; defaults are ASSUMPTIONS), days_off "
        "[sun], blocked_dates, unavailable {character: [dates]} -> shooting days grouped by place, day before night + "
        "day-out-of-days. callsheet: day (shoot day number), call_time HH:MM, cast_calls {name: HH:MM}, location_address {place: "
        "address}, contacts {role: phone}, notes -> text + PDF; unknown details stay [blanks]; sending to cast is action=message "
        "(card). budget_plan*: rates {crew, cast, location, equipment, night_allowance, transport, food, post_per_screen_minute, "
        "'extra:name'} in rupees per unit, ONLY her numbers; contingency_pct -> at-least total, heads without a rate listed as missing. SALES layer "
        "(her facts only, nothing submitted or signed): festival: op add|update|remove|tick, entry (fs1), name, country, category, "
        "deadline/event_date/submitted_on/screened_on YYYY-MM-DD, fee_inr, requires regional|national|international|world|none, status "
        "planned|submitted|accepted|rejected|withdrawn|screened; tick: key logline|screener|poster|stills|trailer|bios|subtitles|... -> "
        "days left, premiere-conflict warnings, packet checklist. window*: op add|remove|holdbacks, medium theatrical|festival|svod|"
        "avod|tvod|tv|home_video|airline|educational|other, territory 'india, uae' or world, start, end, exclusive, licensee, fee_inr, "
        "holdbacks [{after, before, days}] -> exclusivity overlaps + holdback violations. waterfall*: gross_inr, deductions [{name, kind "
        "fixed_inr|percent_of_gross|percent_of_remaining, value, cap_inr}], investors [{name, invested_inr, premium_pct}], shares "
        "[{name, pct}] (sum 100) -> tiers that add back to the gross. DELIVERY layer (hers to edit, nothing is sent or accepted): "
        "deliverable: op add|update|remove|starter, entry (d1), label, buyer, due YYYY-MM-DD, status todo|in_progress|delivered|qc_failed|"
        "accepted|waived, notes; starter: kind festival|ott|theatrical|tv adds a STARTING list of item names (the buyer's own spec is final). "
        "localise: op add|update|remove, entry (l1), language, kind subtitles|dub|both, dub_mode human|ai_voice, voice_person (P-001, an AI voice "
        "is flagged unless that person's recorded consent covers ai_voice), vendor, due, status todo|translating|recording|qc|delivered|"
        "accepted|blocked, qa_rounds, notes. SCRIPT COVERAGE + PREVIS are read-only (film_desk_dekho what=coverage|previs: counts and heuristic "
        "flags, never a reader's verdict). ROYALTY*: op add|update|remove|receipt|unreceipt, entry (gt1 / rc1), party, role writer|director|actor|composer|"
        "lyricist|singer|musician|editor|cinematographer|other, guild, basis flat_inr|percent_of_gross|percent_of_net|per_unit, rate, threshold_inr, cap_inr, "
        "floor_inr, applies_to [medium], start, end, SOURCE (the contract clause: REQUIRED, there is no built-in guild rate table); receipt: medium, "
        "amount_inr, net_inr, units, period, payer -> what each party is due under HER terms (a calculation to check against the contract)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "project": {"type": "string"}, "title": {"type": "string"},
         "logline": {"type": "string"}, "format": {"type": "string"}, "language": {"type": "string"},
         "targets": {"type": "array", "items": {"type": "string"}}, "budget_inr": {"type": "number"},
         "genre": {"type": "string"}, "aspect": {"type": "string"}, "runtime_s": {"type": "integer"},
         "notes": {"type": "string"}, "text": {"type": "string"}, "n": {"type": "integer"}, "character": {"type": "string"},
         "description": {"type": "string"}, "scene": {"type": "string"}, "shot": {"type": "string"},
         "prompt": {"type": "string"}, "camera": {"type": "string"}, "duration": {"type": "integer"},
         "dialogue": {"type": "string"}, "delete": {"type": "boolean"}, "quality": {"type": "string"},
         "shot_ids": {"type": "array", "items": {"type": "string"}}, "variants": {"type": "integer"},
         "person": {"type": "string"}, "name": {"type": "string"}, "role": {"type": "string"}, "phone": {"type": "string"},
         "email": {"type": "string"}, "real": {"type": "boolean"}, "public_figure": {"type": "boolean"},
         "minor": {"type": "boolean"}, "photo_files": {"type": "array", "items": {"type": "string"}},
         "how": {"type": "string"}, "file_id": {"type": "string"}, "uses": {"type": "array", "items": {"type": "string"}},
         "until": {"type": "string"}, "guardian": {"type": "string"}, "kind": {"type": "string"}, "owner": {"type": "string"},
         "licence": {"type": "string"}, "sync": {"type": "boolean"}, "platforms": {"type": "array", "items": {"type": "string"}},
         "fee_inr": {"type": "number"}, "isrc": {"type": "string"}, "rating": {"type": "string"},
         "descriptors": {"type": "string"}, "category": {"type": "string"}, "number": {"type": "string"},
         "date": {"type": "string"}, "key": {"type": "string"}, "done": {"type": "boolean"}, "msg_kind": {"type": "string"},
         "item": {"type": "string"}, "terms": {"type": "string"}, "force": {"type": "array", "items": {"type": "string"}},
         "reason": {"type": "string"}, "banner": {"type": "string"}, "producer": {"type": "string"},
         "month_budget_inr": {"type": "number"}, "morning_time": {"type": "string"}, "rules": {"type": "string"},
         "start_date": {"type": "string"}, "day_hours": {"type": "number"}, "setup_hours": {"type": "number"},
         "hours_per_screen_minute": {"type": "number"}, "days_off": {"type": "array", "items": {"type": "string"}},
         "blocked_dates": {"type": "array", "items": {"type": "string"}}, "unavailable": {"type": "object"},
         "call_time": {"type": "string"}, "cast_calls": {"type": "object"}, "location_address": {"type": "object"},
         "contacts": {"type": "object"}, "day": {"type": "integer"}, "rates": {"type": "object"},
         "contingency_pct": {"type": "number"}, "op": {"type": "string"}, "entry": {"type": "string"},
         "requires": {"type": "string"}, "status": {"type": "string"}, "deadline": {"type": "string"},
         "event_date": {"type": "string"}, "submitted_on": {"type": "string"}, "screened_on": {"type": "string"},
         "country": {"type": "string"}, "medium": {"type": "string"}, "territory": {"type": "string"}, "start": {"type": "string"},
         "end": {"type": "string"}, "exclusive": {"type": "boolean"}, "licensee": {"type": "string"},
         "holdbacks": {"type": "array", "items": {"type": "object"}}, "gross_inr": {"type": "number"},
         "deductions": {"type": "array", "items": {"type": "object"}}, "investors": {"type": "array", "items": {"type": "object"}},
         "shares": {"type": "array", "items": {"type": "object"}}, "label": {"type": "string"}, "buyer": {"type": "string"},
         "due": {"type": "string"}, "dub_mode": {"type": "string"}, "voice_person": {"type": "string"}, "vendor": {"type": "string"},
         "qa_rounds": {"type": "integer"}, "party": {"type": "string"}, "basis": {"type": "string"},
         "rate": {"type": "number"}, "threshold_inr": {"type": "number"}, "cap_inr": {"type": "number"}, "floor_inr": {"type": "number"},
         "applies_to": {"type": "array", "items": {"type": "string"}}, "source": {"type": "string"}, "guild": {"type": "string"},
         "amount_inr": {"type": "number"}, "net_inr": {"type": "number"}, "units": {"type": "number"}, "payer": {"type": "string"}},
         "required": ["action"]}},
    {"name": "film_desk_dekho", "description": (
        "Read the film desk (nothing changes). what=day | projects | project (project) | script | shots | budget (studio "
        "estimate per shot in rupees) | release (checklist + blockers + AI disclosure line) | people | person (person) | "
        "rights | cards | settings | cbfc_note | schedule | dood (day-out-of-days) | plan_budget | callsheet (day) | festivals | windows | waterfall | deliverables | localisation | coverage | previs | royalties."),
     "input_schema": {"type": "object", "properties": {"what": {"type": "string"}, "project": {"type": "string"},
                                                       "person": {"type": "string"}, "status": {"type": "string"}},
                      "required": ["what"]}},
]
FILMDESK_LABELS = {"film_desk": "Working on the film", "film_desk_dekho": "Checking the film desk"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _sync(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..filmdesk import service as S
    t, conv, actor, pr = ctx.tenant_id, ctx.conversation_id, _actor(ctx), _s(a.get("project"))
    if action == "settings":
        return S.save_settings(t, actor, **{k: a[k] for k in S._SET_KEYS if k in a})
    if action == "new":
        return S.project_new(t, _s(a.get("title")), _s(a.get("logline")), _s(a.get("format")), _s(a.get("language")),
                             a.get("targets"), _s(a.get("aspect")), a.get("runtime_s"), a.get("budget_inr"), _s(a.get("genre")),
                             "", actor, conv)
    if action == "update":
        keys = ("title", "logline", "genre", "format", "language", "aspect", "targets", "runtime_s", "budget_inr")
        return S.project_update(t, pr, actor, **{k: a[k] for k in keys if k in a})
    if action == "script":
        return S.script_write(t, pr, _s(a.get("notes")), actor)
    if action == "script_set":
        return S.script_set(t, pr, _s(a.get("text")), actor)
    if action == "script_restore":
        return S.script_restore(t, pr, int(a.get("n") or 0), actor)
    if action == "cast":
        return S.cast_set(t, pr, _s(a.get("character")), _s(a.get("person")), _s(a.get("description")), actor)
    if action == "shots":
        return S.shots_make(t, pr, _s(a.get("scene")), True, actor)
    if action == "shot":
        keys = ("prompt", "camera", "duration", "characters", "dialogue", "speaker", "caption", "delete")
        return S.shot_update(t, pr, _s(a.get("shot")), actor, **{k: a[k] for k in keys if k in a})
    if action == "person":
        return S.person_add(t, _s(a.get("name")), _s(a.get("role")) or "actor", _s(a.get("phone")), _s(a.get("email")),
                            a.get("real", True) is not False, bool(a.get("public_figure")), bool(a.get("minor")),
                            a.get("photo_files") or [], _s(a.get("notes")), actor)
    if action == "consent":
        return S.consent_record(t, _s(a.get("person")), _s(a.get("how")), _s(a.get("file_id")), a.get("uses"),
                                _s(a.get("until")), [pr] if pr else None, _s(a.get("guardian")), actor)
    if action == "withdraw":
        return S.consent_withdraw(t, _s(a.get("person")), _s(a.get("notes") or a.get("reason")), actor)
    if action == "forget":
        return S.forget_person(t, _s(a.get("person")), actor)
    if action == "right":
        return S.right_add(t, pr, _s(a.get("kind")), _s(a.get("title")), _s(a.get("owner")), _s(a.get("licence")),
                           bool(a.get("sync")), a.get("platforms"), "", _s(a.get("until")), a.get("fee_inr"), _s(a.get("isrc")),
                           _s(a.get("file_id")), _s(a.get("notes")), actor)
    if action == "rating":
        return S.set_rating(t, pr, _s(a.get("rating")), _s(a.get("descriptors")), actor)
    if action == "cbfc":
        return S.set_cbfc(t, pr, _s(a.get("category")), _s(a.get("number")), _s(a.get("date")), None, actor)
    if action == "tick":
        return S.tick_item(t, pr, _s(a.get("key")), a.get("done", True) is not False, actor)
    if action == "message":
        return S.message_request(t, pr, _s(a.get("msg_kind")) or "custom", _s(a.get("person")), _s(a.get("text")),
                                 _s(a.get("phone")), _s(a.get("email")), a.get("uses"), _s(a.get("terms")), _s(a.get("item")),
                                 "", actor, conv)
    if action == "release":
        return S.release_request(t, pr, a.get("force") or None, _s(a.get("reason")), actor, conv)
    if action == "schedule":
        keys = ("start_date", "day_hours", "setup_hours", "hours_per_screen_minute", "days_off", "blocked_dates", "unavailable",
                "call_time")
        return S.plan_schedule(t, pr, actor, **{k: a[k] for k in keys if k in a})
    if action == "budget_plan":
        return S.plan_budget(t, pr, a.get("rates"), a.get("contingency_pct"), actor)
    if action == "festival":
        keys = ("entry", "name", "country", "category", "deadline", "event_date", "fee_inr", "requires", "status", "submitted_on",
                "screened_on", "notes", "key", "done")
        return S.festival_op(t, pr, _s(a.get("op")) or "add", actor, **{k: a[k] for k in keys if k in a})
    if action == "window":
        keys = ("entry", "medium", "territory", "start", "end", "exclusive", "licensee", "fee_inr", "notes", "holdbacks")
        return S.window_op(t, pr, _s(a.get("op")) or "add", actor, **{k: a[k] for k in keys if k in a})
    if action == "deliverable":
        keys = ("entry", "label", "buyer", "due", "status", "notes", "kind")
        return S.deliverable_op(t, pr, _s(a.get("op")) or "add", actor, **{k: a[k] for k in keys if k in a})
    if action == "localise":
        keys = ("entry", "language", "kind", "dub_mode", "voice_person", "vendor", "due", "status", "qa_rounds", "notes")
        return S.localise_op(t, pr, _s(a.get("op")) or "add", actor, **{k: a[k] for k in keys if k in a})
    if action == "royalty":
        keys = ("entry", "party", "role", "guild", "basis", "rate", "threshold_inr", "cap_inr", "floor_inr", "applies_to", "start", "end",
                "source", "notes", "medium", "amount_inr", "net_inr", "units", "period", "payer")
        return S.royalty_op(t, pr, _s(a.get("op")) or "add", actor, **{k: a[k] for k in keys if k in a})
    if action == "waterfall":
        return S.waterfall_run(t, pr, a.get("gross_inr"), a.get("deductions"), a.get("investors"), a.get("shares"), actor)
    raise ToolError(f"Unknown action '{action}'.")


async def _film_desk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    from ..filmdesk import service as S
    actor = _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Only the owner can do this.")
    t, conv, pr = ctx.tenant_id, ctx.conversation_id, _s(a.get("project"))
    try:
        if action == "storyboard":
            return await S.storyboard_push(t, pr, actor, conv)
        if action == "preview":
            return await S.preview(t, pr, actor, conv)
        if action == "spend":
            return await S.spend(t, pr, _s(a.get("quality")) or "draft", a.get("shot_ids") or None, int(a.get("variants") or 1),
                                 actor, conv)
        if action == "assemble":
            return await S.assemble(t, pr, True, actor)
        if action == "callsheet":
            keys = ("call_time", "cast_calls", "location_address", "contacts", "notes")
            return await asyncio.to_thread(lambda: S.plan_callsheet(t, pr, a.get("day"), actor, conv,
                                                                    **{k: a[k] for k in keys if k in a}))
        return await asyncio.to_thread(_sync, ctx, action, a)
    except S.FilmError as e:
        raise ToolError(str(e))


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..filmdesk import rules as R
    from ..filmdesk import service as S
    t, pr = ctx.tenant_id, _s(a.get("project"))
    if what == "day":
        return S.day(t)
    if what == "projects":
        return {"projects": S.projects(t, _s(a.get("status")))}
    if what in ("project", "script", "shots"):
        v = S.project_view(t, pr)
        if what == "script":
            return {k: v[k] for k in ("number", "title", "script", "script_versions", "breakdown", "cast")}
        if what == "shots":
            return {k: v[k] for k in ("number", "title", "shots", "cast", "studio_project")}
        v.pop("script", None)
        return v
    if what == "budget":
        return S.budget(t, pr)
    if what == "release":
        return S.release_view(t, pr)
    if what == "people":
        return {"people": S.people(t)}
    if what == "person":
        return S.person_view(t, _s(a.get("person")))
    if what == "rights":
        return {"rights": S.rights(t, pr)}
    if what == "cards":
        return {"cards": S.cards(t, _s(a.get("status")) or "waiting")}
    if what == "settings":
        return S.settings(t)
    if what == "cbfc_note":
        return {"note": R.CBFC_NOTE}
    if what in ("schedule", "dood", "plan_budget", "callsheet"):
        return S.plan_view(t, pr, what, a.get("day"))
    if what == "festivals":
        return S.festival_view(t, pr)
    if what == "windows":
        return S.windows_view(t, pr)
    if what == "waterfall":
        return S.waterfall_view(t, pr)
    if what == "deliverables":
        return S.deliverables_view(t, pr)
    if what == "localisation":
        return S.localisation_view(t, pr)
    if what == "coverage":
        return S.coverage_view(t, pr)
    if what == "previs":
        return S.previs_view(t, pr)
    if what == "royalties":
        if not _owner(ctx):
            raise ToolError("Only the owner can do this.")
        return S.royalties_view(t, pr)
    raise ToolError(f"Unknown what '{what}'.")


async def _film_desk_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    from ..filmdesk import service as S
    try:
        return await asyncio.to_thread(_see, ctx, what, a)
    except S.FilmError as e:
        raise ToolError(str(e))


FILMDESK_HANDLERS = {"film_desk": _film_desk, "film_desk_dekho": _film_desk_dekho}
