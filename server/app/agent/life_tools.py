"""Daily-life tools: reminders, phone alarms/timers/calendar, memory, lists, profile, weather."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from .. import life
from ..db import DeviceAction, ListItem, MemoryFact, Profile, Reminder, Routine, as_utc, now, session
from ..events import bus
from .tools import Ctx, ToolError

LIFE_TOOLS = [
    {"name": "create_reminder", "description": (
        "Remind the user at a time. Santosh messages them in the chat and their phone shows a notification. "
        "Use for 'yaad dilana', medicines, bills, calls to make. Time is the user's LOCAL time."),
     "input_schema": {"type": "object", "properties": {
         "text": {"type": "string", "description": "What to remind, short, in the user's language, e.g. 'Dawai lena (BP)'"},
         "when": {"type": "string", "description": "Local date-time ISO, e.g. 2026-10-18T09:00"},
         "repeat": {"type": "string", "enum": list(life.REPEATS), "description": "none, daily, weekdays, weekly or monthly"}},
         "required": ["text", "when"]}},
    {"name": "list_reminders", "description": "The user's upcoming reminders.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "cancel_reminder", "description": "Cancel a reminder by id (get ids from list_reminders).",
     "input_schema": {"type": "object", "properties": {"reminder_id": {"type": "string"}}, "required": ["reminder_id"]}},
    {"name": "set_phone_alarm", "description": (
        "Set a real alarm in the phone's clock app (rings even if the app is closed). Use for waking up or anything "
        "that must ring loudly. For a gentle nudge use create_reminder instead."),
     "input_schema": {"type": "object", "properties": {
         "time": {"type": "string", "description": "24h local time HH:MM, e.g. 06:00"},
         "label": {"type": "string"},
         "days": {"type": "array", "items": {"type": "string", "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]},
                  "description": "Repeat days; leave empty for one time"}},
         "required": ["time"]}},
    {"name": "set_phone_timer", "description": "Start a countdown timer on the phone, e.g. 10 minutes for cooking.",
     "input_schema": {"type": "object", "properties": {"minutes": {"type": "number"}, "label": {"type": "string"}},
                      "required": ["minutes"]}},
    {"name": "add_calendar_event", "description": "Add an event to the phone's calendar (the calendar app opens with everything filled in; the user taps Save).",
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "start": {"type": "string", "description": "Local ISO date-time"},
         "end": {"type": "string", "description": "Local ISO date-time; default 1 hour after start"},
         "location": {"type": "string"}, "notes": {"type": "string"},
         "remind_minutes_before": {"type": "integer", "description": "Also create a Santosh reminder this many minutes before (optional)"}},
         "required": ["title", "start"]}},
    {"name": "remember", "description": "Save a fact the user wants you to remember (dates, preferences, people, numbers like policy expiry). Do NOT save passwords, OTPs, card or bank numbers.",
     "input_schema": {"type": "object", "properties": {"fact": {"type": "string"}}, "required": ["fact"]}},
    {"name": "forget", "description": "Delete a remembered fact by its id (ids are shown in your context).",
     "input_schema": {"type": "object", "properties": {"fact_id": {"type": "integer"}}, "required": ["fact_id"]}},
    {"name": "list_add", "description": "Add items to a named list (shopping, todo, packing...). Creates the list if needed.",
     "input_schema": {"type": "object", "properties": {"list_name": {"type": "string"},
                                                        "items": {"type": "array", "items": {"type": "string"}}},
                      "required": ["list_name", "items"]}},
    {"name": "list_show", "description": "Show a list, or all lists when list_name is empty.",
     "input_schema": {"type": "object", "properties": {"list_name": {"type": "string"}}}},
    {"name": "list_done", "description": "Tick off items (matched by text) or clear the whole list with clear_all.",
     "input_schema": {"type": "object", "properties": {"list_name": {"type": "string"},
                                                        "items": {"type": "array", "items": {"type": "string"}},
                                                        "clear_all": {"type": "boolean"}},
                      "required": ["list_name"]}},
    {"name": "set_profile", "description": "Save the user's name, city, language, time zone, or daily briefing time (HH:MM, or 'off').",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "city": {"type": "string"},
                                                        "language": {"type": "string"}, "timezone": {"type": "string"},
                                                        "briefing_time": {"type": "string"}}}},
    {"name": "create_routine", "description": (
        "Give yourself a job that you will do AUTOMATICALLY at a set time, again and again, even when the user's app is closed "
        "(you run it on the server and the phone gets a notification with your result). Use for: daily news/weather/market "
        "summaries, checking something every hour, a weekly list review, 'har roz raat 9 baje kal ka plan bhejna'. "
        "The instruction is what you will be told to do each time, so write it as a complete task for yourself. "
        "For a simple fixed-text nudge use create_reminder instead."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string", "description": "Short name the user sees, e.g. 'Subah ka mausam'"},
         "instruction": {"type": "string", "description": "Full task for yourself, e.g. 'Check Pune weather for today and tell the user in 2 lines whether to carry an umbrella.'"},
         "first_run": {"type": "string", "description": "Local date-time ISO of the first run, e.g. 2026-10-19T07:00"},
         "repeat": {"type": "string", "enum": ["none", "hourly", "daily", "weekdays", "weekly", "monthly"]}},
         "required": ["title", "instruction", "first_run"]}},
    {"name": "list_routines", "description": "The jobs you run automatically for the user.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "cancel_routine", "description": "Stop an automatic job by id (ids from list_routines).",
     "input_schema": {"type": "object", "properties": {"routine_id": {"type": "string"}}, "required": ["routine_id"]}},
    {"name": "get_weather", "description": "Current weather and today/tomorrow forecast for the user's city or a named city.",
     "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}}},
]

LIFE_LABELS = {
    "create_reminder": "Reminder laga raha hoon", "list_reminders": "Reminders dekh raha hoon",
    "cancel_reminder": "Reminder hata raha hoon", "set_phone_alarm": "Phone par alarm laga raha hoon",
    "set_phone_timer": "Timer shuru kar raha hoon", "add_calendar_event": "Calendar mein daal raha hoon",
    "remember": "Yaad rakh raha hoon", "forget": "Bhool raha hoon", "list_add": "List mein daal raha hoon",
    "list_show": "List dekh raha hoon", "list_done": "List update kar raha hoon",
    "set_profile": "Aapki jaankari save kar raha hoon",
    "create_routine": "Apna roz ka kaam set kar raha hoon", "list_routines": "Apne kaam dekh raha hoon",
    "cancel_routine": "Kaam band kar raha hoon", "get_weather": "Mausam dekh raha hoon",
}

SENSITIVE = ("password", "passcode", "otp", "pin ", "cvv", "card number", "account number", "aadhaar", "pan number")


def _publish_reminders(ctx: Ctx) -> None:
    bus.publish(ctx.conversation_id, "reminders", {"reminders": life.upcoming_reminders(ctx.tenant_id)})


def _device_action(ctx: Ctx, type_: str, payload: dict, say: str) -> dict:
    with session() as s:
        a = DeviceAction(tenant_id=ctx.tenant_id, conversation_id=ctx.conversation_id, type=type_, payload=payload)
        s.add(a)
        s.flush()
        aid = a.id
    bus.publish(ctx.conversation_id, "device_action", {"id": aid, "type": type_, **payload})
    return {"action_id": aid, "sent_to_phone": True, "note": say}


async def create_reminder(ctx: Ctx, text, when, repeat="none", **_):
    tz = life.tz_of(ctx.tenant_id)
    try:
        due = life.parse_local(when, tz)
    except ValueError as e:
        raise ToolError(f"Could not read the time '{when}': {e}. Use local ISO like 2026-10-18T09:00.")
    if due < now() - timedelta(minutes=1):
        raise ToolError(f"{life.fmt_local(due, tz)} is already in the past. Ask the user for a future time.")
    repeat = repeat if repeat in life.REPEATS else "none"
    with session() as s:
        r = Reminder(tenant_id=ctx.tenant_id, conversation_id=ctx.conversation_id, text=text[:500], due_at=due, repeat=repeat)
        s.add(r)
        s.flush()
        view = life.reminder_view(r, tz)
    _publish_reminders(ctx)
    return view


async def list_reminders(ctx: Ctx, **_):
    return {"reminders": life.upcoming_reminders(ctx.tenant_id)}


async def cancel_reminder(ctx: Ctx, reminder_id, **_):
    with session() as s:
        r = s.get(Reminder, reminder_id)
        if not r or r.tenant_id != ctx.tenant_id:
            raise ToolError(f"No reminder with id {reminder_id}")
        r.status = "cancelled"
        text = r.text
    _publish_reminders(ctx)
    return {"cancelled": reminder_id, "text": text}


async def set_phone_alarm(ctx: Ctx, time, label="Santosh alarm", days=None, **_):
    try:
        hh, mm = [int(x) for x in str(time).split(":")[:2]]
        assert 0 <= hh < 24 and 0 <= mm < 60
    except Exception:
        raise ToolError("Time must be HH:MM in 24-hour format, e.g. 06:30")
    return _device_action(ctx, "set_alarm", {"hour": hh, "minute": mm, "label": label or "Santosh alarm",
                                            "days": [d for d in (days or []) if d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")]},
                          "The phone app sets this in the clock app; tell the user it is done once the app confirms, or that it was sent to the phone.")


async def set_phone_timer(ctx: Ctx, minutes, label="Santosh timer", **_):
    secs = int(round(float(minutes) * 60))
    if not 1 <= secs <= 24 * 3600:
        raise ToolError("Timer must be between a few seconds and 24 hours")
    return _device_action(ctx, "set_timer", {"seconds": secs, "label": label or "Santosh timer"}, "Timer sent to the phone.")


async def add_calendar_event(ctx: Ctx, title, start, end=None, location=None, notes=None, remind_minutes_before=None, **_):
    tz = life.tz_of(ctx.tenant_id)
    try:
        s_utc = life.parse_local(start, tz)
        e_utc = life.parse_local(end, tz) if end else s_utc + timedelta(hours=1)
    except ValueError as e:
        raise ToolError(f"Could not read the time: {e}")
    if e_utc <= s_utc:
        e_utc = s_utc + timedelta(hours=1)
    out = _device_action(ctx, "add_calendar_event", {
        "title": title, "start_ms": int(s_utc.timestamp() * 1000), "end_ms": int(e_utc.timestamp() * 1000),
        "location": location or "", "notes": notes or "", "when": life.fmt_local(s_utc, tz)},
        "The calendar app opens on the phone with this filled in; the user taps Save.")
    if remind_minutes_before:
        r_at = s_utc - timedelta(minutes=int(remind_minutes_before))
        if r_at > now():
            with session() as s:
                s.add(Reminder(tenant_id=ctx.tenant_id, conversation_id=ctx.conversation_id,
                               text=f"{title} ({int(remind_minutes_before)} min mein)", due_at=r_at))
            _publish_reminders(ctx)
            out["reminder_at"] = life.fmt_local(r_at, tz)
    return out


async def remember(ctx: Ctx, fact, **_):
    low = f" {fact.lower()} "
    from ..pii import describe, find
    found = find(str(fact))
    if found:
        raise ToolError(f"Isme {describe(found)} hai. Hoola yeh yaad nahi rakhta; password manager / DigiLocker mein rakhiye.")
    if any(k in low for k in SENSITIVE):
        raise ToolError("This looks like a password, OTP, PIN or account/card number. Do not store it; tell the user to keep it in a password manager.")
    with session() as s:
        m = MemoryFact(tenant_id=ctx.tenant_id, text=fact[:500])
        s.add(m)
        s.flush()
        return {"saved": True, "fact_id": m.id}


async def forget(ctx: Ctx, fact_id, **_):
    with session() as s:
        m = s.get(MemoryFact, int(fact_id))
        if not m or m.tenant_id != ctx.tenant_id:
            raise ToolError(f"No remembered fact with id {fact_id}")
        text = m.text
        s.delete(m)
    return {"forgotten": text}


def _norm_list(name: str) -> str:
    return (name or "todo").strip().lower()[:80] or "todo"


def _list_view(tenant: str, name: str | None = None) -> dict:
    with session() as s:
        q = select(ListItem).where(ListItem.tenant_id == tenant, ListItem.done.is_(False))
        if name:
            q = q.where(ListItem.list_name == _norm_list(name))
        rows = s.scalars(q.order_by(ListItem.list_name, ListItem.id)).all()
        out: dict[str, list[str]] = {}
        for r in rows:
            out.setdefault(r.list_name, []).append(r.text)
        return out


async def list_add(ctx: Ctx, list_name, items, **_):
    name = _norm_list(list_name)
    existing = {t.lower() for t in _list_view(ctx.tenant_id, name).get(name, [])}
    added = []
    with session() as s:
        for it in items or []:
            it = str(it).strip()[:200]
            if it and it.lower() not in existing:
                s.add(ListItem(tenant_id=ctx.tenant_id, list_name=name, text=it))
                existing.add(it.lower())
                added.append(it)
    lists = _list_view(ctx.tenant_id)
    bus.publish(ctx.conversation_id, "lists", {"lists": lists})
    return {"list": name, "added": added, "items": lists.get(name, [])}


async def list_show(ctx: Ctx, list_name=None, **_):
    return {"lists": _list_view(ctx.tenant_id, list_name or None)}


async def list_done(ctx: Ctx, list_name, items=None, clear_all=False, **_):
    name = _norm_list(list_name)
    ticked = []
    with session() as s:
        rows = s.scalars(select(ListItem).where(ListItem.tenant_id == ctx.tenant_id, ListItem.list_name == name,
                                                ListItem.done.is_(False))).all()
        wanted = [str(i).strip().lower() for i in (items or [])]
        for r in rows:
            t = r.text.lower()
            if clear_all or any(w and (w in t or t in w) for w in wanted):
                r.done = True
                ticked.append(r.text)
    lists = _list_view(ctx.tenant_id)
    bus.publish(ctx.conversation_id, "lists", {"lists": lists})
    return {"list": name, "ticked": ticked, "remaining": lists.get(name, [])}


async def set_profile(ctx: Ctx, name=None, city=None, language=None, timezone=None, briefing_time=None, **_):
    life.get_profile(ctx.tenant_id)   # make sure the row exists
    with session() as s:
        p = s.get(Profile, ctx.tenant_id)
        if name:
            p.name = name.strip()[:120]
        if city and city.strip() != (p.city or ""):
            p.city, p.lat, p.lon = city.strip()[:120], None, None
        if language:
            p.language = language[:32]
        if timezone:
            from zoneinfo import ZoneInfo
            try:
                ZoneInfo(timezone)
            except Exception:
                raise ToolError(f"Unknown time zone {timezone}; use names like Asia/Kolkata or Asia/Dubai")
            p.timezone = timezone
        if briefing_time:
            if briefing_time.lower() in ("off", "none", "band", "stop"):
                p.briefing_time = None
            else:
                try:
                    hh, mm = [int(x) for x in briefing_time.split(":")[:2]]
                    assert 0 <= hh < 24 and 0 <= mm < 60
                except Exception:
                    raise ToolError("briefing_time must be HH:MM, e.g. 07:30, or 'off'")
                p.briefing_time = f"{hh:02d}:{mm:02d}"
                p.briefing_conversation_id = ctx.conversation_id
                p.last_briefing_date = None
        return {"name": p.name, "city": p.city, "language": p.language, "timezone": p.timezone,
                "briefing_time": p.briefing_time}


MAX_ROUTINES = 20


def _publish_routines(ctx: Ctx) -> None:
    bus.publish(ctx.conversation_id, "routines", {"routines": life.active_routines(ctx.tenant_id)})


async def create_routine(ctx: Ctx, title, instruction, first_run, repeat="daily", **_):
    tz = life.tz_of(ctx.tenant_id)
    try:
        due = life.parse_local(first_run, tz)
    except ValueError as e:
        raise ToolError(f"Could not read the time '{first_run}': {e}. Use local ISO like 2026-10-19T07:00.")
    if due < now() - timedelta(minutes=1):
        raise ToolError(f"{life.fmt_local(due, tz)} is already in the past. Pick the next future time.")
    repeat = repeat if repeat in life.ROUTINE_REPEATS else "daily"
    with session() as s:
        n = s.scalar(select(func.count()).select_from(Routine).where(Routine.tenant_id == ctx.tenant_id,
                                                                     Routine.status == "active")) or 0
        if n >= MAX_ROUTINES:
            raise ToolError(f"The user already has {n} automatic jobs (limit {MAX_ROUTINES}). Ask which one to stop first.")
        r = Routine(tenant_id=ctx.tenant_id, conversation_id=ctx.conversation_id, title=title[:200],
                    instruction=instruction[:2000], next_run=due, repeat=repeat)
        s.add(r)
        s.flush()
        view = life.routine_view(r, tz)
    _publish_routines(ctx)
    return view


async def list_routines(ctx: Ctx, **_):
    return {"routines": life.active_routines(ctx.tenant_id)}


async def cancel_routine(ctx: Ctx, routine_id, **_):
    with session() as s:
        r = s.get(Routine, routine_id)
        if not r or r.tenant_id != ctx.tenant_id:
            raise ToolError(f"No automatic job with id {routine_id}")
        r.status = "cancelled"
        title = r.title
    _publish_routines(ctx)
    return {"cancelled": routine_id, "title": title}


async def get_weather(ctx: Ctx, city=None, **_):
    try:
        return await life.weather_for(ctx.tenant_id, city)
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        raise ToolError(f"Weather service did not answer: {e}")


LIFE_HANDLERS = {
    "create_reminder": create_reminder, "list_reminders": list_reminders, "cancel_reminder": cancel_reminder,
    "set_phone_alarm": set_phone_alarm, "set_phone_timer": set_phone_timer, "add_calendar_event": add_calendar_event,
    "remember": remember, "forget": forget, "list_add": list_add, "list_show": list_show, "list_done": list_done,
    "set_profile": set_profile, "get_weather": get_weather,
    "create_routine": create_routine, "list_routines": list_routines, "cancel_routine": cancel_routine,
}
