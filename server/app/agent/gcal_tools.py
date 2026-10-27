"""Google Calendar tools: the user's own Google Calendar (official Calendar API through Google sign-in; the server
owner's .env Gmail over CalDAV still works for the basics).

Private changes to the user's own calendar happen at once. Anything that emails other people (invites, rescheduling
or cancelling a shared meeting, declining) shows a confirm card first.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any

from .. import life
from ..bazar.connectors.base import ToolError as BazarError
from ..cal import service as cs
from ..cal.google import CalError, NotConnected
from .tools import Ctx, ToolError

REPEAT_SCHEMA = {"type": "object", "description": "Optional repeat, e.g. {freq: weekly, days: [MO, TH], count: 10}",
                 "properties": {"freq": {"type": "string", "enum": ["daily", "weekly", "weekdays", "monthly", "yearly"]},
                                "days": {"type": "array", "items": {"type": "string"}, "description": "MO TU WE TH FR SA SU"},
                                "interval": {"type": "integer"}, "count": {"type": "integer"},
                                "until": {"type": "string", "description": "YYYY-MM-DD"}}}

GCAL_TOOLS = [
    {"name": "calendar_agenda", "description": (
        "The user's Google Calendar for a day or range (all the calendars they read: work, family, holidays). Use for "
        "'aaj/kal kya hai', 'is hafte ki meetings', 'agle mahine kab free hoon'. Returns time, title, location, people, "
        "Meet link, and whether the user has replied to an invite. query filters by words."),
     "input_schema": {"type": "object", "properties": {
         "from_date": {"type": "string", "description": "Local date YYYY-MM-DD (default today)"},
         "to_date": {"type": "string", "description": "Local date YYYY-MM-DD (default = from_date)"},
         "query": {"type": "string"}}}},
    {"name": "calendar_find_event", "description": (
        "Find events by words (title, place, people, notes) from a week ago to `days` ahead. Use to get an event id "
        "before changing, cancelling or replying to it."),
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"},
                                                       "days": {"type": "integer", "description": "Days ahead (default 60)"}},
                      "required": ["query"]}},
    {"name": "calendar_add_event", "description": (
        "Add an event to the user's Google Calendar (syncs to all their devices). Work out the exact local time. "
        "all_day for birthdays, leave, holidays (start/end as dates). meet=true adds a Google Meet link. reminders = "
        "minutes before for phone pop-ups, e.g. [10, 60]. repeat for recurring events. attendees = emails or names of "
        "people to invite (only when the user names people): inviting emails them, so the user confirms on a card first."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "start": {"type": "string", "description": "Local ISO date-time 2026-10-20T16:00, or a date 2026-10-20 when all_day"},
         "end": {"type": "string", "description": "Local ISO; default 1 hour after start (all-day: same day)"},
         "all_day": {"type": "boolean"}, "location": {"type": "string"}, "description": {"type": "string"},
         "attendees": {"type": "array", "items": {"type": "string"}},
         "meet": {"type": "boolean"}, "reminders": {"type": "array", "items": {"type": "integer"}},
         "repeat": REPEAT_SCHEMA,
         "calendar": {"type": "string", "description": "Which calendar (name), when not the default"}},
         "required": ["title", "start"]}},
    {"name": "calendar_update_event", "description": (
        "Change an event: move it (new start/end), rename, change place or notes, add/remove people, add a Meet link. "
        "event_id from calendar_agenda / calendar_find_event. If other people are invited they get an update email, so "
        "the user confirms on a card first; changes to private events happen at once."),
     "input_schema": {"type": "object", "properties": {
         "event_id": {"type": "string"}, "title": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
         "location": {"type": "string"}, "description": {"type": "string"},
         "add_attendees": {"type": "array", "items": {"type": "string"}},
         "remove_attendees": {"type": "array", "items": {"type": "string"}},
         "meet": {"type": "boolean"}, "reminders": {"type": "array", "items": {"type": "integer"}}},
         "required": ["event_id"]}},
    {"name": "calendar_cancel_event", "description": (
        "Cancel / delete an event (event_id). whole_series=true for every occurrence of a repeating event. If the user "
        "is only a guest, this declines the invite instead. Always shows the user a confirm card first."),
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}, "whole_series": {"type": "boolean"}},
                      "required": ["event_id"]}},
    {"name": "calendar_respond", "description": (
        "Reply to a meeting invite the user received: accepted, tentative (maybe), or declined. Declining shows a "
        "confirm card; accepting happens at once."),
     "input_schema": {"type": "object", "properties": {
         "event_id": {"type": "string"}, "response": {"type": "string", "enum": ["accepted", "tentative", "declined"]}},
         "required": ["event_id", "response"]}},
    {"name": "calendar_free_slots", "description": (
        "When is the user free? Finds open time of at least `minutes` between work_start and work_end on the given "
        "days, from their Google Calendar. Use for 'kal kab free hoon', 'is hafte 1 ghante ka slot dhoondho'."),
     "input_schema": {"type": "object", "properties": {
         "from_date": {"type": "string", "description": "YYYY-MM-DD (default today)"},
         "to_date": {"type": "string", "description": "YYYY-MM-DD (default = from_date)"},
         "minutes": {"type": "integer", "description": "Length needed (default 60)"},
         "work_start": {"type": "string", "description": "HH:MM (default 09:00)"},
         "work_end": {"type": "string", "description": "HH:MM (default 19:00)"}}}},
    {"name": "calendar_settings", "description": (
        "The user's connected calendars and Santosh's calendar settings. read_calendars = names of calendars to "
        "include in the agenda; default_calendar = where new events go; meeting_alerts = minutes before a meeting "
        "Santosh nudges (0 = off). Call with no arguments to list. If nothing is connected tell the user: "
        "Profile > Calendar > Google Calendar jodiye."),
     "input_schema": {"type": "object", "properties": {
         "read_calendars": {"type": "array", "items": {"type": "string"}}, "default_calendar": {"type": "string"},
         "meeting_alerts": {"type": "integer"}}}},
]

GCAL_LABELS = {"calendar_agenda": "Calendar dekh raha hoon", "calendar_add_event": "Calendar mein event daal raha hoon",
               "calendar_find_event": "Event dhoondh raha hoon", "calendar_cancel_event": "Cancel ki manzoori le raha hoon",
               "calendar_update_event": "Event badal raha hoon", "calendar_respond": "Invite ka jawab de raha hoon",
               "calendar_free_slots": "Khaali samay dhoondh raha hoon", "calendar_settings": "Calendar settings dekh raha hoon"}


async def _t(fn, *a, **kw):
    try:
        return await asyncio.to_thread(fn, *a, **kw)
    except NotConnected as e:
        raise ToolError(str(e))
    except CalError as e:
        raise ToolError(str(e))


def _day(s: str | None, default: date) -> date:
    if not s:
        return default
    try:
        return datetime.fromisoformat(str(s)[:10]).date()
    except ValueError:
        raise ToolError("Date YYYY-MM-DD format mein do, e.g. 2026-10-20.")


def _today(ctx: Ctx) -> date:
    return datetime.now(life.tz_of(ctx.tenant_id)).date()


def _parse(ctx: Ctx, s: str, what: str) -> datetime:
    try:
        return life.parse_local(str(s), life.tz_of(ctx.tenant_id))
    except ValueError as e:
        raise ToolError(f"{what} samajh nahi aaya ({e}). Local ISO do, jaise 2026-10-20T16:00.")


def _people(ctx: Ctx, people: list[str] | None) -> list[str]:
    if not people:
        return []
    from ..mailbox import contacts
    addrs, problems = contacts.resolve(ctx.tenant_id, ", ".join(str(p) for p in people))
    if problems:
        raise ToolError("attendees: " + " ".join(problems))
    return [a.strip() for a in addrs.split(",") if a.strip()]


def _card(ctx: Ctx, pid: str) -> dict[str, Any]:
    from ..bazar import service
    try:
        out = service.run(ctx.tenant_id, ctx.conversation_id, "santosh-calendar", "confirm_change", {"pending_id": pid})
    except BazarError as e:
        raise ToolError(str(e))
    return {k: v for k, v in out.items() if k in ("needs_approval", "approval_id", "card", "say")}


async def calendar_agenda(ctx: Ctx, from_date=None, to_date=None, query=None, **_):
    tz = life.tz_of(ctx.tenant_id)
    d0 = _day(from_date, _today(ctx))
    d1 = _day(to_date, d0)
    if d1 < d0:
        d0, d1 = d1, d0
    if (d1 - d0).days > 92:
        raise ToolError("Ek baar mein 3 mahine tak ka calendar.")
    start = datetime(d0.year, d0.month, d0.day, tzinfo=tz)
    end = datetime(d1.year, d1.month, d1.day, tzinfo=tz) + timedelta(days=1)
    await asyncio.to_thread(cs.remember_conversation, ctx.tenant_id, ctx.conversation_id)
    out = await _t(cs.agenda, ctx.tenant_id, start, end, query or None, 150)
    return {"from": d0.isoformat(), "to": d1.isoformat(), **out}


async def calendar_find_event(ctx: Ctx, query, days=60, **_):
    tz = life.tz_of(ctx.tenant_id)
    nowl = datetime.now(tz)
    out = await _t(cs.agenda, ctx.tenant_id, nowl - timedelta(days=7), nowl + timedelta(days=max(1, min(int(days or 60), 366))),
                   str(query), 50)
    if not out["events"]:   # Google's search matches whole words; try a looser match over the next weeks
        wide = await _t(cs.agenda, ctx.tenant_id, nowl - timedelta(days=7), nowl + timedelta(days=60), None, 250)
        q = str(query).lower()
        out = {"count": 0, "events": [e for e in wide["events"] if q in (e["title"] + " " + e["location"] + " " +
                                                                        e["description"]).lower()]}
        out["count"] = len(out["events"])
    return out


async def calendar_add_event(ctx: Ctx, title, start, end=None, all_day=False, location="", description="",
                             attendees=None, meet=False, reminders=None, repeat=None, calendar=None, **_):
    s = _parse(ctx, start, "Start time")
    all_day = bool(all_day) or (len(str(start).strip()) <= 10)
    if end:
        e = _parse(ctx, end, "End time")
        if all_day:
            e = e + timedelta(days=1)
    else:
        e = s + (timedelta(days=1) if all_day else timedelta(hours=1))
    if e <= s:
        raise ToolError("End time start ke baad hona chahiye.")
    people = _people(ctx, attendees)

    def work():
        box, cal_id = cs._default_target(ctx.tenant_id, calendar)
        cs.remember_conversation(ctx.tenant_id, ctx.conversation_id)
        body = cs.build_body(ctx.tenant_id, title=str(title), start=s, end=e, all_day=all_day, location=location or "",
                             description=description or "", attendees=people, reminders=reminders, repeat=repeat)
        tz = life.tz_of(ctx.tenant_id)
        when = (s.strftime("%d %b %Y") + " (poora din)") if all_day else life.fmt_local(s, tz)
        if people:
            pid = cs.pend(ctx.tenant_id, ctx.conversation_id, "create",
                          {"box": box.key, "cal": cal_id, "body": body, "meet": bool(meet)},
                          {"title": body["summary"], "when": when, "location": location or "", "people": people,
                           "meet": bool(meet)})
            return {"pending_id": pid}
        return {"event": cs.create_now(ctx.tenant_id, ctx.conversation_id, box, cal_id, body, bool(meet))}
    res = await _t(work)
    if "pending_id" in res:
        card = await asyncio.to_thread(_card, ctx, res["pending_id"])
        return {**card, "status": "needs_approval",
                "note": "Invite card is in the chat; the event is created and invites go out only after the user approves."}
    v = res["event"]
    return {"added": True, "event": v, "note": "Event added (a card with the link is in the chat)."}


async def calendar_update_event(ctx: Ctx, event_id, title=None, start=None, end=None, location=None, description=None,
                                add_attendees=None, remove_attendees=None, meet=False, reminders=None, **_):
    adds = _people(ctx, add_attendees)
    removes = {a.lower() for a in _people(ctx, remove_attendees)}

    def work():
        box, cal_id, raw, v = cs.get_event(ctx.tenant_id, str(event_id))
        if box.kind != "google":
            from ..cal.caldav_cal import NEEDS_SIGNIN
            raise CalError(NEEDS_SIGNIN)
        if not v["i_am_organizer"] and (title or start or end or location is not None or adds or removes):
            raise CalError(f"Is meeting ke organizer {v['organizer']} hain; aap sirf jawab (calendar_respond) de sakte hain.")
        tz = life.tz_of(ctx.tenant_id)
        body: dict[str, Any] = {}
        if title:
            body["summary"] = str(title)[:300]
        if location is not None:
            body["location"] = str(location)[:500]
        if description is not None:
            body["description"] = str(description)[:8000]
        if start or end:
            old_s = datetime.fromisoformat(v["start_iso"]) if v["start_iso"] else None
            old_e = datetime.fromisoformat(v["end_iso"]) if v["end_iso"] else None
            ns = _parse(ctx, start, "Start time") if start else old_s
            ne = _parse(ctx, end, "End time") if end else (ns + (old_e - old_s) if old_s and old_e else ns + timedelta(hours=1))
            if ne <= ns:
                raise CalError("End time start ke baad hona chahiye.")
            body["start"] = cs._when_body(ns, v["all_day"], tz)
            body["end"] = cs._when_body(ne, v["all_day"], tz)
        if adds or removes:
            atts = [a for a in (raw.get("attendees") or []) if (a.get("email") or "").lower() not in removes]
            have = {(a.get("email") or "").lower() for a in atts}
            atts += [{"email": a} for a in adds if a.lower() not in have]
            body["attendees"] = atts
        if reminders is not None:
            mins = sorted({max(0, min(int(m), 40320)) for m in reminders})[:5]
            body["reminders"] = {"useDefault": False, "overrides": [{"method": "popup", "minutes": m} for m in mins]}
        if not body and not meet:
            raise CalError("Kya badalna hai? (title, start, end, location, attendees, meet)")
        others = [a["email"] for a in v["attendees"]] + adds
        if others and (set(body) - {"reminders"} or meet):
            ns_label = life.fmt_local(_parse(ctx, start, "Start") if start else datetime.fromisoformat(v["start_iso"]), tz) \
                if v["start_iso"] else v["start"]
            pid = cs.pend(ctx.tenant_id, ctx.conversation_id, "update",
                          {"box": box.key, "cal": cal_id, "event": raw["id"], "body": body, "meet": bool(meet)},
                          {"title": body.get("summary") or v["title"], "when": f"{v['start']} → {ns_label}" if start else v["start"],
                           "location": body.get("location", v["location"]), "people": sorted(set(others)), "meet": bool(meet)})
            return {"pending_id": pid}
        e = box.patch(cal_id, raw["id"], body, "none", bool(meet))
        nv = cs.view(box, cal_id, cal_id, e, tz)
        cs._publish_event(ctx.conversation_id, nv, "updated")
        return {"event": nv}
    res = await _t(work)
    if "pending_id" in res:
        card = await asyncio.to_thread(_card, ctx, res["pending_id"])
        return {**card, "status": "needs_approval", "note": "Guests will get an update email; confirm card is in the chat."}
    return {"updated": True, "event": res["event"]}


async def calendar_cancel_event(ctx: Ctx, event_id, whole_series=False, **_):
    def work():
        box, cal_id, raw, v = cs.get_event(ctx.tenant_id, str(event_id))
        eid = raw["id"]
        if whole_series and raw.get("recurringEventId"):
            eid = raw["recurringEventId"]
        ref = cs.make_ref(box, cal_id, eid)
        summary = {"title": v["title"], "when": v["start"] + (" (har baar)" if whole_series and v["recurring"] else ""),
                   "location": v["location"]}
        if not v["i_am_organizer"] and v["organizer"]:
            summary["note"] = f"Organizer {v['organizer']} ko 'nahi aa paunga' jayega."
            return cs.pend(ctx.tenant_id, ctx.conversation_id, "decline", {"box": box.key, "ref": cs.make_ref(box, cal_id, raw["id"])},
                           summary)
        people = [a["email"] for a in v["attendees"]]
        if people:
            summary["people"] = people
            summary["note"] = "Sabko cancellation email jayega."
        return cs.pend(ctx.tenant_id, ctx.conversation_id, "cancel",
                       {"box": box.key, "cal": cal_id, "event": eid, "ref": ref, "notify": bool(people)}, summary)
    pid = await _t(work)
    card = await asyncio.to_thread(_card, ctx, pid)
    return {**card, "status": "needs_approval", "note": "Confirm card is in the chat; nothing changes until the user approves."}


async def calendar_respond(ctx: Ctx, event_id, response, **_):
    if response == "declined":
        def work():
            box, cal_id, raw, v = cs.get_event(ctx.tenant_id, str(event_id))
            return cs.pend(ctx.tenant_id, ctx.conversation_id, "decline", {"box": box.key, "ref": str(event_id)},
                           {"title": v["title"], "when": v["start"], "note": f"Organizer {v['organizer']} ko bataya jayega."})
        pid = await _t(work)
        card = await asyncio.to_thread(_card, ctx, pid)
        return {**card, "status": "needs_approval"}
    v = await _t(cs.respond_now, ctx.tenant_id, str(event_id), str(response))
    await asyncio.to_thread(cs._publish_event, ctx.conversation_id, v, response)
    return {"responded": response, "event": {k: v[k] for k in ("title", "start", "organizer")}}


async def calendar_free_slots(ctx: Ctx, from_date=None, to_date=None, minutes=60, work_start="09:00", work_end="19:00", **_):
    d0 = _day(from_date, _today(ctx))
    d1 = _day(to_date, d0)
    if (d1 - d0).days > 31:
        raise ToolError("Ek baar mein ek mahine tak.")
    try:
        slots = await _t(cs.free_slots, ctx.tenant_id, d0, d1, int(minutes or 60), work_start or "09:00", work_end or "19:00")
    except ValueError:
        raise ToolError("work_start / work_end HH:MM format mein do.")
    return {"from": d0.isoformat(), "to": d1.isoformat(), "minutes": int(minutes or 60), "free": slots,
            "note": "Offer 2-3 of these; book with calendar_add_event once the user picks one."}


async def calendar_settings(ctx: Ctx, read_calendars=None, default_calendar=None, meeting_alerts=None, **_):
    def work():
        from ..cal.accounts import views
        changed = []
        cals = cs.all_calendars(ctx.tenant_id)

        def find(name: str) -> dict:
            w = name.strip().lower()
            for c in cals:
                if w in (c["name"].lower(), c["id"].lower(), c["ref"].lower()):
                    return c
            raise CalError(f"'{name}' calendar nahi mila. Calendars: {', '.join(c['name'] for c in cals)}")
        if read_calendars is not None:
            refs = [find(n)["ref"] for n in read_calendars]
            cs.set_prefs(ctx.tenant_id, read_calendars=refs or None)
            changed.append("reading: " + ", ".join(read_calendars))
        if default_calendar:
            c = find(default_calendar)
            cs.set_prefs(ctx.tenant_id, default_calendar=c["ref"])
            changed.append(f"new events go to {c['name']}")
        if meeting_alerts is not None:
            m = max(0, min(int(meeting_alerts), 120))
            cs.set_prefs(ctx.tenant_id, alert_minutes=m, alert_conversation_id=ctx.conversation_id)
            changed.append(f"meeting alerts {m} min before" if m else "meeting alerts off")
        out = {"accounts": views(ctx.tenant_id),
               "calendars": [{k: c[k] for k in ("name", "account", "primary", "reading", "default", "role")}
                             for c in cs.all_calendars(ctx.tenant_id)],
               "meeting_alerts_minutes": cs.prefs(ctx.tenant_id)["alert_minutes"]}
        if changed:
            out["changed"] = changed
        return out
    return await _t(work)


GCAL_HANDLERS = {"calendar_agenda": calendar_agenda, "calendar_add_event": calendar_add_event,
                 "calendar_find_event": calendar_find_event, "calendar_update_event": calendar_update_event,
                 "calendar_cancel_event": calendar_cancel_event, "calendar_respond": calendar_respond,
                 "calendar_free_slots": calendar_free_slots, "calendar_settings": calendar_settings}
