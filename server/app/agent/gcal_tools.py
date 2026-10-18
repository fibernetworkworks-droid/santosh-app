"""Google Calendar tools (read your agenda, add and cancel events). Reuses the Gmail app password."""
from __future__ import annotations

from datetime import timedelta

from .. import gcal, life
from .tools import Ctx, ToolError

GCAL_TOOLS = [
    {"name": "calendar_agenda", "description": (
        "The user's Google Calendar schedule for a day or range. Use for 'aaj/kal kya hai', 'is hafte ki meetings'. "
        "Returns events with time, title, location and attendees."),
     "input_schema": {"type": "object", "properties": {
         "from_date": {"type": "string", "description": "Local date YYYY-MM-DD (default today)"},
         "to_date": {"type": "string", "description": "Local date YYYY-MM-DD (default = from_date, i.e. one day)"}}}},
    {"name": "calendar_add_event", "description": (
        "Add an event to the user's Google Calendar (syncs to all their devices). Work out the exact local date-time "
        "from what they say. Add attendees (emails) only if the user names people to invite; inviting sends them a "
        "calendar invite."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "start": {"type": "string", "description": "Local ISO date-time, e.g. 2026-10-20T16:00"},
         "end": {"type": "string", "description": "Local ISO date-time; default 1 hour after start"},
         "location": {"type": "string"}, "description": {"type": "string"},
         "attendees": {"type": "array", "items": {"type": "string"}, "description": "Email addresses to invite (optional)"}},
         "required": ["title", "start"]}},
    {"name": "calendar_find_event", "description": "Find events matching text (title/location) in the next few weeks, to get an event id for cancelling.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"},
                                                       "days": {"type": "integer", "description": "How many days ahead to look (default 30)"}},
                      "required": ["query"]}},
    {"name": "calendar_cancel_event", "description": "Cancel/delete a calendar event by id (get the id from calendar_find_event or calendar_agenda).",
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}}, "required": ["event_id"]}},
]

GCAL_LABELS = {"calendar_agenda": "Calendar dekh raha hoon", "calendar_add_event": "Calendar mein event daal raha hoon",
               "calendar_find_event": "Event dhoondh raha hoon", "calendar_cancel_event": "Event hata raha hoon"}


def _require():
    if not gcal.configured():
        raise ToolError("Google Calendar abhi connect nahi hai. (Gmail app password wale account par CalDAV se chalta hai.)")


async def calendar_agenda(ctx: Ctx, from_date=None, to_date=None, **_):
    _require()
    tz = life.tz_of(ctx.tenant_id)
    from datetime import datetime
    today = datetime.now(tz).date()
    try:
        d0 = datetime.fromisoformat(from_date).date() if from_date else today
        d1 = datetime.fromisoformat(to_date).date() if to_date else d0
    except ValueError:
        raise ToolError("Date YYYY-MM-DD format mein do, e.g. 2026-10-20.")
    start = datetime(d0.year, d0.month, d0.day, 0, 0, tzinfo=tz)
    end = datetime(d1.year, d1.month, d1.day, 23, 59, tzinfo=tz)
    try:
        events = await gcal.agenda(start, end)
    except gcal.CalError as e:
        raise ToolError(str(e))
    return {"from": d0.isoformat(), "to": d1.isoformat(), "count": len(events), "events": events}


async def calendar_add_event(ctx: Ctx, title, start, end=None, location="", description="", attendees=None, **_):
    _require()
    tz = life.tz_of(ctx.tenant_id)
    try:
        s = life.parse_local(start, tz)
    except ValueError as e:
        raise ToolError(f"Start time samajh nahi aaya: {e}")
    if end:
        try:
            e_dt = life.parse_local(end, tz)
        except ValueError:
            e_dt = s + timedelta(hours=1)
    else:
        e_dt = s + timedelta(hours=1)
    try:
        return await gcal.create(title, s, e_dt, location=location or "", description=description or "", attendees=attendees or [])
    except gcal.CalError as e:
        raise ToolError(str(e))


async def calendar_find_event(ctx: Ctx, query, days=30, **_):
    _require()
    try:
        events = await gcal.find(str(query), days=int(days or 30))
    except gcal.CalError as e:
        raise ToolError(str(e))
    return {"count": len(events), "events": events}


async def calendar_cancel_event(ctx: Ctx, event_id, **_):
    _require()
    try:
        return await gcal.cancel(str(event_id))
    except gcal.CalError as e:
        raise ToolError(str(e))


GCAL_HANDLERS = {"calendar_agenda": calendar_agenda, "calendar_add_event": calendar_add_event,
                 "calendar_find_event": calendar_find_event, "calendar_cancel_event": calendar_cancel_event}
