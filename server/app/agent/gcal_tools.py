"""Google Calendar tools: the user's own Google Calendar (official Calendar API through Google sign-in; the server
owner's .env Gmail over CalDAV still works for the basics).

Private changes to the user's own calendar happen at once. Anything that emails other people (invites, rescheduling
or cancelling a shared meeting, declining) shows a confirm card first.
"""
from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timedelta
from typing import Any

from .. import life
from ..bazar.connectors.base import ToolError as BazarError
from ..cal import more as cm
from ..cal import service as cs
from ..cal.google import CalError, NotConnected
from .tools import Ctx, ToolError

REPEAT_SCHEMA = {"type": "object", "description": (
    "Optional repeat, e.g. {freq: weekly, days: [MO, TH], count: 10}; the first Monday of each month = "
    "{freq: monthly, nth: 1, days: [MO]}, the last Friday = nth -1."),
                 "properties": {"freq": {"type": "string", "enum": ["daily", "weekly", "weekdays", "monthly", "yearly"]},
                                "days": {"type": "array", "items": {"type": "string"}, "description": "MO TU WE TH FR SA SU"},
                                "nth": {"type": "integer"},
                                "interval": {"type": "integer"}, "count": {"type": "integer"},
                                "until": {"type": "string", "description": "YYYY-MM-DD"}}}

OPTIONS = {
    "color": {"type": "string", "description": "Event colour: lavender, sage, grape, flamingo, banana, tangerine, "
                                                "peacock, graphite, blueberry, basil, tomato"},
    "label": {"type": "string", "description": "One of the calendar's own event labels by name (calendar_calendars "
                                                "action labels)"},
    "visibility": {"type": "string", "enum": ["default", "private", "public"]},
    "show_as": {"type": "string", "enum": ["busy", "free"]},
    "guests": {"type": "object", "description": "What guests may do: can_modify, can_invite, can_see_guests (true/false)",
               "properties": {"can_modify": {"type": "boolean"}, "can_invite": {"type": "boolean"},
                              "can_see_guests": {"type": "boolean"}}},
    "optional_attendees": {"type": "array", "items": {"type": "string"}},
    "email_reminders": {"type": "array", "items": {"type": "integer"}, "description": "Minutes before, by email"},
    "attachments": {"type": "array", "items": {"type": "string"}, "description": "Google Drive file links or ids"},
}
GCAL_TOOLS = [
    {"name": "calendar_agenda", "description": (
        "The user's Google Calendar for a day or range (all the calendars they read: work, family, holidays). Use for "
        "'what is on today/tomorrow', 'this week's meetings', 'when am I free next month'. Returns time, title, location, people, "
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
        "minutes before for phone pop-ups, e.g. [10, 60]; email_reminders by email. repeat for recurring events. "
        "attendees = emails or names of people to invite (only when the user names people), optional_attendees too: "
        "inviting emails them, so the user confirms on a card first. color, label, visibility (private hides the "
        "details), show_as (free = does not block her time), guests (what guests may do), attachments (Drive files). "
        "Out of office / focus time / working location: calendar_status."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "start": {"type": "string", "description": "Local ISO date-time 2026-10-20T16:00, or a date 2026-10-20 when all_day"},
         "end": {"type": "string", "description": "Local ISO; default 1 hour after start (all-day: same day)"},
         "all_day": {"type": "boolean"}, "location": {"type": "string"}, "description": {"type": "string"},
         "attendees": {"type": "array", "items": {"type": "string"}},
         "meet": {"type": "boolean"}, "reminders": {"type": "array", "items": {"type": "integer"}},
         "repeat": REPEAT_SCHEMA,
         "calendar": {"type": "string", "description": "Which calendar (name), when not the default"}, **OPTIONS},
         "required": ["title", "start"]}},
    {"name": "calendar_update_event", "description": (
        "Change an event: move it (new start/end), rename, change place or notes, add/remove people, add a Meet link, "
        "colour, label, visibility, show_as, guest rules, reminders, attachments; move_to = another of her calendars. "
        "event_id from calendar_agenda / calendar_find_event. A repeating event: this changes only that one "
        "occurrence - for all of them or this-and-following use calendar_series. If other people are invited they get "
        "an update email, so the user confirms on a card first; changes to private events happen at once."),
     "input_schema": {"type": "object", "properties": {
         "event_id": {"type": "string"}, "title": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
         "location": {"type": "string"}, "description": {"type": "string"},
         "add_attendees": {"type": "array", "items": {"type": "string"}},
         "remove_attendees": {"type": "array", "items": {"type": "string"}},
         "meet": {"type": "boolean"}, "reminders": {"type": "array", "items": {"type": "integer"}},
         "move_to": {"type": "string", "description": "Another of her calendars (name)"}, **OPTIONS},
         "required": ["event_id"]}},
    {"name": "calendar_cancel_event", "description": (
        "Cancel / delete an event (event_id). whole_series=true for every occurrence of a repeating event. If the user "
        "is only a guest, this declines the invite instead. Always shows the user a confirm card first."),
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}, "whole_series": {"type": "boolean"}},
                      "required": ["event_id"]}},
    {"name": "calendar_respond", "description": (
        "Reply to a meeting invite the user received: accepted, tentative (maybe), or declined. comment = a note to "
        "the organizer; whole_series = every occurrence of a repeating invite. Declining shows a confirm card; "
        "accepting happens at once."),
     "input_schema": {"type": "object", "properties": {
         "event_id": {"type": "string"}, "response": {"type": "string", "enum": ["accepted", "tentative", "declined"]},
         "comment": {"type": "string"}, "whole_series": {"type": "boolean"}},
         "required": ["event_id", "response"]}},
    {"name": "calendar_free_slots", "description": (
        "When is the user free? Finds open time of at least `minutes` between work_start and work_end on the given "
        "days, from their Google Calendar. Use for 'when am I free tomorrow', 'find a 1-hour slot this week'."),
     "input_schema": {"type": "object", "properties": {
         "from_date": {"type": "string", "description": "YYYY-MM-DD (default today)"},
         "to_date": {"type": "string", "description": "YYYY-MM-DD (default = from_date)"},
         "minutes": {"type": "integer", "description": "Length needed (default 60)"},
         "work_start": {"type": "string", "description": "HH:MM (default 09:00)"},
         "work_end": {"type": "string", "description": "HH:MM (default 19:00)"},
         "weekdays_only": {"type": "boolean"}}}},
    {"name": "calendar_meeting_time", "description": (
        "A time when several people are free, from Google's free / busy for each of them (people = emails or names) "
        "plus the user's own calendars, between work_start and work_end. Says whose calendars Google would not show "
        "(private or another organisation). Then offer 2-3 slots and invite with calendar_add_event."),
     "input_schema": {"type": "object", "properties": {
         "people": {"type": "array", "items": {"type": "string"}},
         "from_date": {"type": "string"}, "to_date": {"type": "string"}, "minutes": {"type": "integer"},
         "work_start": {"type": "string"}, "work_end": {"type": "string"}, "weekdays_only": {"type": "boolean"}},
         "required": ["people"]}},
    {"name": "calendar_calendars", "description": (
        "Her calendars themselves. action list (all, hidden too), create (name, description, time_zone, color), "
        "rename / describe / time_zone (calendar, name / description / time_zone), color (hex), hide, show, "
        "subscribe (calendar_id of a shared or public calendar), holidays (country = public holidays of that country), "
        "unsubscribe (off her list; card), delete (a calendar she owns and all its events; card), clear (every event "
        "on her main calendar; card), labels / add_label (label, label_color: the calendar's own event labels)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "create", "rename", "describe", "time_zone", "color", "hide",
                                               "show", "subscribe", "holidays", "unsubscribe", "delete", "clear",
                                               "labels", "add_label"]},
         "calendar": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"},
         "time_zone": {"type": "string"}, "color": {"type": "string"}, "country": {"type": "string"},
         "calendar_id": {"type": "string"}, "label": {"type": "string"}, "label_color": {"type": "string"}}}},
    {"name": "calendar_share", "description": (
        "Who can see one of her calendars. action list; add (people, role: free_busy = only busy / free, view = all "
        "details, edit = can change, manage = can change and share; Google emails them); change (people, role); "
        "remove (people); public (anyone on the internet, role free_busy or view); domain (everyone at a domain). "
        "Everything but list shows a confirm card."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "add", "change", "remove", "public", "domain"]},
         "calendar": {"type": "string"}, "people": {"type": "array", "items": {"type": "string"}},
         "role": {"type": "string", "enum": ["free_busy", "view", "edit", "manage"]}, "domain": {"type": "string"}}}},
    {"name": "calendar_status", "description": (
        "Mark her time on her main calendar. kind out_of_office (leave / travel; decline = new (default) / all / none "
        "clashing invites, message = what the decline says), focus_time (decline, message, chat = dnd / available), "
        "working_location (where = home / office / a place; office = the office's name). Google allows these only on "
        "a Google Workspace account's main calendar - on personal Gmail use calendar_add_event instead."),
     "input_schema": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": ["out_of_office", "focus_time", "working_location"]},
         "start": {"type": "string"}, "end": {"type": "string"}, "title": {"type": "string"},
         "message": {"type": "string"}, "decline": {"type": "string", "enum": ["new", "all", "none"]},
         "chat": {"type": "string", "enum": ["dnd", "available"]}, "where": {"type": "string"},
         "office": {"type": "string"}}, "required": ["kind", "start", "end"]}},
    {"name": "calendar_series", "description": (
        "A repeating event (event_id = any occurrence). action list (its rule + next occurrences with their ids), "
        "skip (take out this one occurrence), end (stop it after until = YYYY-MM-DD, default today), change_all "
        "(title / start time / end / location / description for every occurrence), change_following (from this "
        "occurrence on: the series is split, earlier ones stay). Guests get an update email, so a card first."),
     "input_schema": {"type": "object", "properties": {
         "event_id": {"type": "string"}, "action": {"type": "string", "enum": ["list", "skip", "end", "change_all",
                                                                               "change_following"]},
         "start": {"type": "string"}, "end": {"type": "string"}, "title": {"type": "string"},
         "location": {"type": "string"}, "description": {"type": "string"}, "until": {"type": "string"}},
         "required": ["event_id"]}},
    {"name": "calendar_ics", "description": (
        "Calendar files (.ics). action import: an .ics file she sent in the chat (file_id) into a calendar (nobody is "
        "emailed; the same file again updates the same events). action export: an event (event_id) or a range "
        "(from_date / to_date, query) as an .ics file in the chat, to send to anyone using any calendar app."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["import", "export"]}, "file_id": {"type": "string"},
         "calendar": {"type": "string"}, "event_id": {"type": "string"}, "from_date": {"type": "string"},
         "to_date": {"type": "string"}, "query": {"type": "string"}}, "required": ["action"]}},
    {"name": "calendar_watch", "description": (
        "Tell her in the chat when a calendar gets something new. action on (kinds: invites = new invites to her, "
        "changes = anything added, moved or cancelled, all; job = a task Hoola does each time, e.g. 'accept invites "
        "from my team, ask me about the rest'), off, list. Checked every few minutes."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["on", "off", "list"]}, "calendar": {"type": "string"},
         "kinds": {"type": "string", "enum": ["invites", "changes", "all"]}, "job": {"type": "string"}}}},
    {"name": "calendar_settings", "description": (
        "The user's connected calendars and Santosh's calendar settings. read_calendars = names of calendars to "
        "include in the agenda; default_calendar = where new events go; meeting_alerts = minutes before a meeting "
        "Hoola nudges (0 = off). Call with no arguments to list (also her Google Calendar settings: time zone, week "
        "start, default event length). If nothing is connected tell the user: Connect Google Calendar in "
        "Connectors > Google."),
     "input_schema": {"type": "object", "properties": {
         "read_calendars": {"type": "array", "items": {"type": "string"}}, "default_calendar": {"type": "string"},
         "meeting_alerts": {"type": "integer"}}}},
]

GCAL_LABELS = {"calendar_agenda": "Checking the calendar", "calendar_add_event": "Adding an event to the calendar",
               "calendar_find_event": "Finding the event", "calendar_cancel_event": "Getting approval to cancel",
               "calendar_update_event": "Changing the event", "calendar_respond": "Replying to the invite",
               "calendar_free_slots": "Finding free time slots", "calendar_settings": "Checking calendar settings",
               "calendar_meeting_time": "Finding a time for everyone", "calendar_calendars": "Working on the calendars",
               "calendar_share": "Sharing the calendar", "calendar_status": "Marking your time",
               "calendar_series": "Working on the repeating event", "calendar_ics": "Working on the calendar file",
               "calendar_watch": "Setting calendar alerts"}


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
        raise ToolError("Give the date in YYYY-MM-DD format, e.g. 2026-10-20.")


def _today(ctx: Ctx) -> date:
    return datetime.now(life.tz_of(ctx.tenant_id)).date()


def _parse(ctx: Ctx, s: str, what: str) -> datetime:
    try:
        return life.parse_local(str(s), life.tz_of(ctx.tenant_id))
    except ValueError as e:
        raise ToolError(f"{what} was not understood ({e}). Give local ISO time, like 2026-10-20T16:00.")


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
        raise ToolError("Calendar for up to 3 months at a time.")
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


def _attach(items) -> list[dict] | None:
    out = []
    for x in items or []:
        v = str(x).strip()
        m = re.search(r"/d/([A-Za-z0-9_-]{20,})|[?&]id=([A-Za-z0-9_-]{20,})", v)
        fid = (m.group(1) or m.group(2)) if m else (v if re.fullmatch(r"[A-Za-z0-9_-]{20,}", v) else "")
        if not fid:
            raise ToolError(f"'{v}' is not a Google Drive file link or id (Google attaches only Drive files).")
        out.append({"fileUrl": f"https://drive.google.com/open?id={fid}"})
    return out or None


async def calendar_add_event(ctx: Ctx, title, start, end=None, all_day=False, location="", description="",
                             attendees=None, meet=False, reminders=None, repeat=None, calendar=None, color=None,
                             label=None, visibility=None, show_as=None, guests=None, optional_attendees=None,
                             email_reminders=None, attachments=None, **_):
    s = _parse(ctx, start, "Start time")
    all_day = bool(all_day) or (len(str(start).strip()) <= 10)
    if end:
        e = _parse(ctx, end, "End time")
        if all_day:
            e = e + timedelta(days=1)
    else:
        e = s + (timedelta(days=1) if all_day else timedelta(hours=1))
    if e <= s:
        raise ToolError("End time must be after the start.")
    people = _people(ctx, attendees)
    maybe = _people(ctx, optional_attendees)
    files = _attach(attachments)

    def work():
        box, cal_id = cs._default_target(ctx.tenant_id, calendar)
        cs.remember_conversation(ctx.tenant_id, ctx.conversation_id)
        body = cs.build_body(ctx.tenant_id, title=str(title), start=s, end=e, all_day=all_day, location=location or "",
                             description=description or "", attendees=people, reminders=reminders, repeat=repeat,
                             color=color, optional=maybe, email_reminders=email_reminders, visibility=visibility,
                             show_as=show_as, guests=guests, attachments=files)
        if label:
            body["eventLabelId"] = cm.label_id(box, cal_id, str(label))
        people_all = people + [m for m in maybe if m not in people]
        tz = life.tz_of(ctx.tenant_id)
        when = (s.strftime("%d %b %Y") + " (all day)") if all_day else life.fmt_local(s, tz)
        if people_all:
            pid = cs.pend(ctx.tenant_id, ctx.conversation_id, "create",
                          {"box": box.key, "cal": cal_id, "body": body, "meet": bool(meet)},
                          {"title": body["summary"], "when": when, "location": location or "", "people": people_all,
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
                                add_attendees=None, remove_attendees=None, meet=False, reminders=None, move_to=None,
                                color=None, label=None, visibility=None, show_as=None, guests=None,
                                optional_attendees=None, email_reminders=None, attachments=None, **_):
    adds = _people(ctx, add_attendees)
    maybe = _people(ctx, optional_attendees)
    files = _attach(attachments)
    removes = {a.lower() for a in _people(ctx, remove_attendees)}

    def work():
        box, cal_id, raw, v = cs.get_event(ctx.tenant_id, str(event_id))
        if box.kind != "google":
            from ..cal.caldav_cal import NEEDS_SIGNIN
            raise CalError(NEEDS_SIGNIN)
        if move_to:
            dbox, dcal = cs._default_target(ctx.tenant_id, str(move_to))
            if dbox.key != box.key:
                raise CalError("Google moves events only between calendars of the same Google account.")
            if not v["i_am_organizer"]:
                raise CalError("Only the organizer can move a meeting to another calendar.")
            if v["attendees"]:
                return {"pending_id": cs.pend(ctx.tenant_id, ctx.conversation_id, "move",
                                              {"box": box.key, "cal": cal_id, "event": raw["id"], "dest": dcal},
                                              {"title": v["title"], "when": v["start"], "to": str(move_to),
                                               "people": [a["email"] for a in v["attendees"]],
                                               "note": "Guests get an update email."})}
            e = box.move(cal_id, raw["id"], dcal, "none")
            nv = cs.view(box, dcal, str(move_to), e, life.tz_of(ctx.tenant_id))
            cs._publish_event(ctx.conversation_id, nv, "moved")
            return {"event": nv}
        if not v["i_am_organizer"] and (title or start or end or location is not None or adds or removes or maybe):
            raise CalError(f"The organizer of this meeting is {v['organizer']}; you can only reply (calendar_respond).")
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
                raise CalError("End time must be after the start.")
            body["start"] = cs._when_body(ns, v["all_day"], tz)
            body["end"] = cs._when_body(ne, v["all_day"], tz)
        if adds or removes or maybe:
            atts = [a for a in (raw.get("attendees") or []) if (a.get("email") or "").lower() not in removes]
            have = {(a.get("email") or "").lower() for a in atts}
            atts += [{"email": a} for a in adds if a.lower() not in have]
            atts += [{"email": a, "optional": True} for a in maybe if a.lower() not in have and a not in adds]
            body["attendees"] = atts
        rb = cs.reminders_body(reminders, email_reminders)
        if rb:
            body["reminders"] = rb
        body.update(cs.options_body(visibility, show_as, guests, color))
        if label:
            body["eventLabelId"] = cm.label_id(box, cal_id, str(label))
        if files:
            body["attachments"] = (raw.get("attachments") or []) + files
        if not body and not meet:
            raise CalError("What should change? (title, start, end, location, attendees, meet)")
        others = [a["email"] for a in v["attendees"]] + adds + maybe
        if others and (set(body) - {"reminders", "colorId", "eventLabelId"} or meet):
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
        summary = {"title": v["title"], "when": v["start"] + (" (every occurrence)" if whole_series and v["recurring"] else ""),
                   "location": v["location"]}
        if not v["i_am_organizer"] and v["organizer"]:
            summary["note"] = f"A 'cannot attend' reply will go to organizer {v['organizer']}."
            return cs.pend(ctx.tenant_id, ctx.conversation_id, "decline", {"box": box.key, "ref": cs.make_ref(box, cal_id, raw["id"])},
                           summary)
        people = [a["email"] for a in v["attendees"]]
        if people:
            summary["people"] = people
            summary["note"] = "Everyone will get a cancellation email."
        return cs.pend(ctx.tenant_id, ctx.conversation_id, "cancel",
                       {"box": box.key, "cal": cal_id, "event": eid, "ref": ref, "notify": bool(people)}, summary)
    pid = await _t(work)
    card = await asyncio.to_thread(_card, ctx, pid)
    return {**card, "status": "needs_approval", "note": "Confirm card is in the chat; nothing changes until the user approves."}


async def calendar_respond(ctx: Ctx, event_id, response, comment="", whole_series=False, **_):
    if response == "declined":
        def work():
            box, cal_id, raw, v = cs.get_event(ctx.tenant_id, str(event_id))
            return cs.pend(ctx.tenant_id, ctx.conversation_id, "decline",
                           {"box": box.key, "ref": str(event_id), "comment": str(comment or "")[:500],
                            "all": bool(whole_series)},
                           {"title": v["title"], "when": v["start"] + (" (every occurrence)" if whole_series else ""),
                            "note": f"Organizer {v['organizer']} will be told." + (f" Note: {comment}" if comment else "")})
        pid = await _t(work)
        card = await asyncio.to_thread(_card, ctx, pid)
        return {**card, "status": "needs_approval"}
    v = await _t(cs.respond_now, ctx.tenant_id, str(event_id), str(response), str(comment or ""), bool(whole_series))
    await asyncio.to_thread(cs._publish_event, ctx.conversation_id, v, response)
    return {"responded": response, "event": {k: v[k] for k in ("title", "start", "organizer")}}


async def calendar_free_slots(ctx: Ctx, from_date=None, to_date=None, minutes=60, work_start="09:00", work_end="19:00",
                              weekdays_only=False, **_):
    d0 = _day(from_date, _today(ctx))
    d1 = _day(to_date, d0)
    if (d1 - d0).days > 31:
        raise ToolError("Up to one month at a time.")
    warn: list[str] = []
    try:
        slots = await _t(cs.free_slots, ctx.tenant_id, d0, d1, int(minutes or 60), work_start or "09:00",
                         work_end or "19:00", 10, warn, None, bool(weekdays_only))
    except ValueError:
        raise ToolError("Give work_start / work_end in HH:MM format.")
    out = {"from": d0.isoformat(), "to": d1.isoformat(), "minutes": int(minutes or 60), "free": slots,
           "note": "Offer 2-3 of these; book with calendar_add_event once the user picks one."}
    if warn:
        out["warnings"] = warn
    return out


async def _maybe_card(ctx: Ctx, out: dict) -> dict:
    if "pending_id" in out:
        card = await asyncio.to_thread(_card, ctx, out["pending_id"])
        return {**out, **card, "status": "needs_approval", "note": "A confirm card is in the chat; nothing done yet."}
    return out


async def calendar_meeting_time(ctx: Ctx, people, from_date=None, to_date=None, minutes=60, work_start="09:00",
                                work_end="18:00", weekdays_only=True, **_):
    d0 = _day(from_date, _today(ctx))
    d1 = _day(to_date, d0 + timedelta(days=6))
    if (d1 - d0).days > 31:
        raise ToolError("Up to one month at a time.")
    try:
        return await _t(cm.meeting_time, ctx.tenant_id, list(people or []), d0, d1, int(minutes or 60),
                        work_start or "09:00", work_end or "18:00", bool(True if weekdays_only is None else weekdays_only))
    except ValueError:
        raise ToolError("Give work_start / work_end in HH:MM format.")


async def calendar_calendars(ctx: Ctx, action="list", calendar="", name="", description=None, time_zone="", color="",
                             country="", calendar_id="", label="", label_color="", **_):
    out = await _t(cm.calendars, ctx.tenant_id, ctx.conversation_id, str(action or "list"), str(calendar or ""),
                   str(name or ""), description, str(time_zone or ""), str(color or ""), str(country or ""),
                   str(calendar_id or ""), str(label or ""), str(label_color or ""))
    return await _maybe_card(ctx, out)


async def calendar_share(ctx: Ctx, action="list", calendar="", people=None, role="view", domain="", **_):
    out = await _t(cm.share, ctx.tenant_id, ctx.conversation_id, str(action or "list"), str(calendar or ""),
                   list(people or []), str(role or "view"), str(domain or ""))
    return await _maybe_card(ctx, out)


async def calendar_status(ctx: Ctx, kind, start, end, title="", message="", decline="new", chat="", where="", office="",
                          **_):
    s = _parse(ctx, start, "Start")
    e = _parse(ctx, end, "End")
    if len(str(end).strip()) <= 10:
        e = e + timedelta(days=1)
    return await _t(cm.status, ctx.tenant_id, ctx.conversation_id, str(kind), s, e, str(message or ""),
                    str(decline or "new"), str(chat or ""), str(where or ""), str(office or ""), str(title or ""))


async def calendar_series(ctx: Ctx, event_id, action="list", start=None, end=None, title=None, location=None,
                          description=None, until="", **_):
    s = _parse(ctx, start, "Start") if start else None
    e = _parse(ctx, end, "End") if end else None
    out = await _t(cm.series, ctx.tenant_id, ctx.conversation_id, str(event_id), str(action or "list"), s, e, title,
                   location, description, str(until or ""))
    return await _maybe_card(ctx, out)


async def calendar_ics(ctx: Ctx, action, file_id="", calendar="", event_id="", from_date=None, to_date=None, query="",
                       **_):
    if str(action) == "import":
        if not file_id:
            raise ToolError("Which file? Give the file_id of the .ics file sent in the chat.")
        return await _t(cm.import_ics, ctx.tenant_id, ctx.conversation_id, str(file_id), str(calendar or ""))
    d0 = _day(from_date, _today(ctx)) if from_date else None
    d1 = _day(to_date, d0) if (to_date and d0) else d0
    return await _t(cm.export_ics, ctx.tenant_id, ctx.conversation_id, str(event_id or ""), d0, d1, str(query or ""))


async def calendar_watch(ctx: Ctx, action="on", calendar="", kinds="invites", job="", **_):
    return await _t(cm.watch, ctx.tenant_id, ctx.conversation_id, str(action or "on"), str(calendar or ""),
                    str(kinds or "invites"), str(job or ""))


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
            raise CalError(f"'{name}' calendar not found. Calendars: {', '.join(c['name'] for c in cals)}")
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
        google_settings = {}
        for b in cs.boxes(ctx.tenant_id):
            if b.kind == "google":
                try:
                    st = b.settings()
                    google_settings[b.address] = {k: st[k] for k in ("timezone", "weekStart", "defaultEventLength",
                                                                     "format24HourTime", "locale", "hideWeekends")
                                                  if k in st}
                except CalError:
                    pass
        out = {"accounts": views(ctx.tenant_id),
               "calendars": [{k: c[k] for k in ("name", "account", "primary", "reading", "default", "role")}
                             for c in cs.all_calendars(ctx.tenant_id)],
               "meeting_alerts_minutes": cs.prefs(ctx.tenant_id)["alert_minutes"]}
        if google_settings:
            out["google_settings"] = google_settings
        if changed:
            out["changed"] = changed
        return out
    return await _t(work)


GCAL_HANDLERS = {"calendar_agenda": calendar_agenda, "calendar_add_event": calendar_add_event,
                 "calendar_find_event": calendar_find_event, "calendar_update_event": calendar_update_event,
                 "calendar_cancel_event": calendar_cancel_event, "calendar_respond": calendar_respond,
                 "calendar_free_slots": calendar_free_slots, "calendar_settings": calendar_settings,
                 "calendar_meeting_time": calendar_meeting_time, "calendar_calendars": calendar_calendars,
                 "calendar_share": calendar_share, "calendar_status": calendar_status, "calendar_series": calendar_series,
                 "calendar_ics": calendar_ics, "calendar_watch": calendar_watch}
