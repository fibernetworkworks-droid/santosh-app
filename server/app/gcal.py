"""Google Calendar over CalDAV, reusing the Gmail app password already in .env.

Reading is reliable on Google's legacy CalDAV endpoint; creating/cancelling is attempted there too.
If Google retires the legacy endpoint, we'll switch this module to the OAuth Calendar API without
changing the agent tools. All blocking caldav calls run in a thread.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import get_settings

log = logging.getLogger("santosh.gcal")

LEGACY_URL = "https://www.google.com/calendar/dav/{email}/user"


class CalError(Exception):
    pass


def configured() -> bool:
    """CalDAV reuses the email app password; only Gmail/Workspace addresses have this endpoint."""
    st = get_settings()
    if not (st.email_address and st.email_password):
        return False
    domain = st.email_address.split("@")[-1].lower()
    return domain in ("gmail.com", "googlemail.com") or bool(st.gcal_caldav_url)


def _tz() -> ZoneInfo:
    from . import life
    return life.tz_of(get_settings().tenant_id)


def _client():
    import caldav
    st = get_settings()
    url = st.gcal_caldav_url or LEGACY_URL.format(email=st.email_address)
    return caldav.DAVClient(url=url, username=st.email_address, password=st.email_password, timeout=25)


def _primary(client):
    """The user's main calendar (named after their address), else the first writable one."""
    import caldav
    try:
        principal = client.principal()
        cals = principal.calendars()
    except Exception as e:
        raise CalError(f"Calendar se connect nahi hua: {e}. App password aur 2-step verification check kijiye.")
    if not cals:
        raise CalError("Koi calendar nahi mila is account mein.")
    addr = get_settings().email_address.lower()
    for c in cals:
        try:
            if addr in str(c.url).lower():
                return c
        except Exception:
            pass
    return cals[0]


def _fmt(dt, tz) -> str:
    from . import life
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return life.fmt_local(dt, tz)
    return str(dt)   # all-day (date only)


def _event_view(ev, tz) -> dict:
    comp = ev.icalendar_component
    start = comp.get("dtstart").dt if comp.get("dtstart") else None
    end = comp.get("dtend").dt if comp.get("dtend") else None
    all_day = start is not None and not isinstance(start, datetime)
    attendees = []
    for a in comp.get("attendee", []) if comp.get("attendee") else []:
        attendees.append(str(a).replace("mailto:", ""))
    uid = str(comp.get("uid") or "")
    return {
        "id": uid,
        "title": str(comp.get("summary") or "(no title)"),
        "start": _fmt(start, tz) if start else "",
        "end": _fmt(end, tz) if end else "",
        "all_day": all_day,
        "location": str(comp.get("location") or ""),
        "description": str(comp.get("description") or "")[:500],
        "attendees": attendees,
        "_start_raw": start.isoformat() if start else "",
    }


# ---------------- reading ----------------
def _agenda(start_local: datetime, end_local: datetime):
    tz = _tz()
    client = _client()
    cal = _primary(client)
    start = start_local.replace(tzinfo=tz) if start_local.tzinfo is None else start_local
    end = end_local.replace(tzinfo=tz) if end_local.tzinfo is None else end_local
    try:
        found = cal.search(start=start.astimezone(ZoneInfo("UTC")), end=end.astimezone(ZoneInfo("UTC")),
                           event=True, expand=True)
    except TypeError:   # older caldav signature
        found = cal.date_search(start, end)
    except Exception as e:
        raise CalError(f"Calendar padhne mein dikkat: {e}")
    views = []
    for ev in found:
        try:
            views.append(_event_view(ev, tz))
        except Exception:
            continue
    views.sort(key=lambda v: v["_start_raw"])
    for v in views:
        v.pop("_start_raw", None)
    return views


def _find(query: str, days: int):
    tz = _tz()
    now = datetime.now(tz)
    events = _agenda(now - timedelta(days=1), now + timedelta(days=days))
    q = query.lower().strip()
    return [e for e in events if q in e["title"].lower() or q in e["location"].lower() or q in e["description"].lower()]


# ---------------- writing ----------------
def _create(title, start_local, end_local, location, description, attendees):
    from icalendar import Calendar as ICal, Event as IEvent
    tz = _tz()
    client = _client()
    cal = _primary(client)
    uid = f"{uuid.uuid4()}@santosh"
    ic = ICal()
    ic.add("prodid", "-//Santosh//EN")
    ic.add("version", "2.0")
    ev = IEvent()
    ev.add("uid", uid)
    ev.add("summary", title)
    ev.add("dtstart", start_local if start_local.tzinfo else start_local.replace(tzinfo=tz))
    ev.add("dtend", end_local if end_local.tzinfo else end_local.replace(tzinfo=tz))
    ev.add("dtstamp", datetime.now(tz))
    if location:
        ev.add("location", location)
    if description:
        ev.add("description", description)
    for a in attendees or []:
        if "@" in a:
            ev.add("attendee", f"mailto:{a}")
    ic.add_component(ev)
    try:
        cal.save_event(ic.to_ical().decode())
    except Exception as e:
        raise CalError(f"Event banane mein dikkat (CalDAV): {e}")
    return {"id": uid, "title": title, "start": _fmt(start_local, tz), "end": _fmt(end_local, tz),
            "location": location or "", "attendees": attendees or []}


def _cancel(uid: str):
    client = _client()
    cal = _primary(client)
    try:
        ev = cal.event_by_uid(uid)
    except Exception:
        raise CalError("Yeh event nahi mila (shayad pehle hi hata diya).")
    title = ""
    try:
        title = str(ev.icalendar_component.get("summary") or "")
    except Exception:
        pass
    try:
        ev.delete()
    except Exception as e:
        raise CalError(f"Event hatane mein dikkat: {e}")
    return {"cancelled": uid, "title": title}


# ---------------- async wrappers ----------------
async def agenda(start_local, end_local):
    return await asyncio.to_thread(_agenda, start_local, end_local)


async def find(query, days=30):
    return await asyncio.to_thread(_find, query, days)


async def create(title, start_local, end_local, location="", description="", attendees=None):
    return await asyncio.to_thread(_create, title, start_local, end_local, location, description, attendees)


async def cancel(uid):
    return await asyncio.to_thread(_cancel, uid)
