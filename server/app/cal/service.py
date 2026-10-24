"""Santosh's Google Calendar work: agenda across calendars, search, adding events (Meet link, reminders, repeats),
rescheduling, cancelling, RSVP, free-slot finding and meeting alerts. Blocking; tools run it in a thread.

Event ids handed to the model are "<account key>~<calendar id>~<event id>".
Anything that emails other people (invites, reschedules of shared meetings, cancellations, declines) waits for
the user's tap on a confirm card. Private changes to the user's own calendar happen at once.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from ..db import (CalendarAccount, CalendarAlert, CalendarPending, CalendarPrefs, Conversation, OAuthConnection,
                  Profile, now, session)
from ..events import bus, notify
from .accounts import boxes, get_box
from .google import CalError

log = logging.getLogger("santosh.cal")

_cal_cache: dict[str, tuple[float, list]] = {}
REPEATS = {"daily": "DAILY", "weekly": "WEEKLY", "monthly": "MONTHLY", "yearly": "YEARLY", "weekdays": "WEEKLY"}
DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")


def _tz(tenant: str) -> ZoneInfo:
    from ..life import tz_of
    return tz_of(tenant)


def _fmt(dt: datetime, tz: ZoneInfo) -> str:
    from ..life import fmt_local
    return fmt_local(dt, tz)


# ---------------- prefs ----------------
def prefs(tenant: str) -> dict[str, Any]:
    with session() as s:
        p = s.get(CalendarPrefs, tenant)
        if p is None:
            return {"read_calendars": None, "default_calendar": None, "alert_minutes": 10, "alert_conversation_id": None}
        return {"read_calendars": p.read_calendars, "default_calendar": p.default_calendar,
                "alert_minutes": p.alert_minutes, "alert_conversation_id": p.alert_conversation_id}


def set_prefs(tenant: str, **kw) -> dict[str, Any]:
    with session() as s:
        p = s.get(CalendarPrefs, tenant)
        if p is None:
            p = CalendarPrefs(tenant_id=tenant)
            s.add(p)
        for k, v in kw.items():
            if v is not None or k == "read_calendars":
                setattr(p, k, v)
    return prefs(tenant)


def remember_conversation(tenant: str, conv: str) -> None:
    if conv and prefs(tenant).get("alert_conversation_id") != conv:
        set_prefs(tenant, alert_conversation_id=conv)


# ---------------- calendars ----------------
def _calendars(box) -> list[dict]:
    hit = _cal_cache.get(box.key + box.address)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    cals = box.calendars()
    _cal_cache[box.key + box.address] = (time.time(), cals)
    return cals


def all_calendars(tenant: str) -> list[dict[str, Any]]:
    p = prefs(tenant)
    chosen = set(p["read_calendars"] or [])
    default = p["default_calendar"]
    out = []
    for b in boxes(tenant):
        for c in _calendars(b):
            ref = f"{b.key}~{c['id']}"
            out.append({**c, "ref": ref, "account": b.address,
                        "reading": (ref in chosen) if p["read_calendars"] is not None else (c["primary"] or c["selected"]),
                        "default": ref == default})
    if not any(c["default"] for c in out):
        for c in out:
            if c["primary"] and c.get("role") in ("owner", "writer", ""):
                c["default"] = True
                break
    return out


def _reading(tenant: str) -> list[tuple[Any, str, str]]:
    """(box, calendar id, calendar name) Santosh reads for the agenda."""
    bs = {b.key: b for b in boxes(tenant)}
    if not bs:
        get_box(tenant)          # raises the "connect your calendar" message
    out = []
    for c in all_calendars(tenant):
        key = c["ref"].split("~", 1)[0]
        if c["reading"] and key in bs:
            out.append((bs[key], c["id"], c["name"]))
    return out


def _default_target(tenant: str, calendar: str | None = None) -> tuple[Any, str]:
    cals = all_calendars(tenant)
    if calendar:
        w = calendar.strip().lower()
        for c in cals:
            if w in (c["ref"].lower(), c["id"].lower(), c["name"].lower()):
                return get_box(tenant, c["ref"].split("~", 1)[0]), c["id"]
        raise CalError(f"'{calendar}' calendar nahi mila. Calendars: {', '.join(c['name'] for c in cals)}")
    for c in cals:
        if c["default"]:
            return get_box(tenant, c["ref"].split("~", 1)[0]), c["id"]
    b = get_box(tenant)
    return b, "primary"


# ---------------- ids and views ----------------
def make_ref(box, cal_id: str, event_id: str) -> str:
    return f"{box.key}~{cal_id}~{event_id}"


def split_ref(tenant: str, ref: str):
    parts = str(ref or "").split("~")
    if len(parts) >= 3:
        return get_box(tenant, parts[0]), parts[1], "~".join(parts[2:])
    return get_box(tenant), "primary", str(ref)


def _parse_when(w: dict, tz: ZoneInfo) -> tuple[datetime | None, bool]:
    if not w:
        return None, False
    if w.get("dateTime"):
        dt = datetime.fromisoformat(w["dateTime"].replace("Z", "+00:00"))
        return (dt if dt.tzinfo else dt.replace(tzinfo=tz)), False
    if w.get("date"):
        d = date.fromisoformat(w["date"])
        return datetime(d.year, d.month, d.day, tzinfo=tz), True
    return None, False


def view(box, cal_id: str, cal_name: str, e: dict, tz: ZoneInfo) -> dict[str, Any]:
    start, all_day = _parse_when(e.get("start") or {}, tz)
    end, _ = _parse_when(e.get("end") or {}, tz)
    me = box.address
    attendees = []
    my_response = ""
    for a in e.get("attendees") or []:
        em = (a.get("email") or "").lower()
        if a.get("self") or em == me:
            my_response = a.get("responseStatus", "")
            continue
        if a.get("resource"):
            continue
        attendees.append({"email": em, "name": a.get("displayName", ""), "response": a.get("responseStatus", "needsAction")})
    organizer = ((e.get("organizer") or {}).get("email") or "").lower()
    meet = e.get("hangoutLink") or ""
    if not meet:
        for ep in ((e.get("conferenceData") or {}).get("entryPoints") or []):
            if ep.get("entryPointType") == "video":
                meet = ep.get("uri", "")
                break
    if all_day:
        when = start.strftime("%d %b %Y") + " (poora din)" if start else ""
        end_label = ((end - timedelta(days=1)).strftime("%d %b %Y") if end and (end - start).days > 1 else "")
    else:
        when = _fmt(start, tz) if start else ""
        end_label = _fmt(end, tz) if end else ""
    return {"id": make_ref(box, cal_id, e.get("id", "")), "title": e.get("summary") or "(no title)",
            "start": when, "end": end_label, "start_iso": start.isoformat() if start else "",
            "end_iso": end.isoformat() if end else "", "all_day": all_day,
            "location": e.get("location") or "", "description": (e.get("description") or "")[:600],
            "attendees": attendees, "organizer": organizer,
            "i_am_organizer": (not organizer) or organizer == me or bool((e.get("organizer") or {}).get("self")),
            "my_response": my_response, "meet_link": meet, "link": e.get("htmlLink", ""), "calendar": cal_name,
            "recurring": bool(e.get("recurringEventId") or e.get("recurrence")), "account": me}


# ---------------- reading ----------------
def agenda(tenant: str, start: datetime, end: datetime, query: str | None = None, limit: int = 100) -> dict[str, Any]:
    tz = _tz(tenant)
    out, errors = [], []
    for box, cal_id, cal_name in _reading(tenant):
        try:
            for e in box.events(cal_id, start, end, query, limit):
                out.append(view(box, cal_id, cal_name, e, tz))
        except CalError as ex:
            errors.append(f"{cal_name}: {ex}")
    out.sort(key=lambda v: (v["start_iso"][:10], not v["all_day"], v["start_iso"]))   # all-day items first each day
    res: dict[str, Any] = {"count": len(out), "events": out[:limit]}
    if errors and not out:
        raise CalError("; ".join(errors))
    if errors:
        res["warnings"] = errors
    return res


def get_event(tenant: str, ref: str) -> tuple[Any, str, dict, dict]:
    box, cal_id, eid = split_ref(tenant, ref)
    raw = box.get(cal_id, eid)
    return box, cal_id, raw, view(box, cal_id, cal_id, raw, _tz(tenant))


# ---------------- building events ----------------
def _when_body(dt: datetime, all_day: bool, tz: ZoneInfo) -> dict:
    local = dt.astimezone(tz)
    if all_day:
        return {"date": local.date().isoformat()}
    return {"dateTime": local.isoformat(), "timeZone": str(tz)}


def rrule(repeat: dict | str | None) -> list[str] | None:
    if not repeat:
        return None
    if isinstance(repeat, str):
        repeat = {"freq": repeat}
    freq = str(repeat.get("freq", "")).lower()
    if freq in ("", "none", "no"):
        return None
    if freq not in REPEATS:
        raise CalError("repeat.freq: daily, weekly, weekdays, monthly ya yearly")
    parts = [f"FREQ={REPEATS[freq]}"]
    days = [str(d).upper()[:2] for d in (repeat.get("days") or [])]
    if freq == "weekdays":
        days = ["MO", "TU", "WE", "TH", "FR"]
    if days:
        bad = [d for d in days if d not in DAYS]
        if bad:
            raise CalError(f"repeat.days: {', '.join(DAYS)}")
        parts.append("BYDAY=" + ",".join(days))
    if repeat.get("interval"):
        parts.append(f"INTERVAL={max(1, int(repeat['interval']))}")
    if repeat.get("count"):
        parts.append(f"COUNT={max(1, min(int(repeat['count']), 730))}")
    elif repeat.get("until"):
        d = date.fromisoformat(str(repeat["until"])[:10])
        parts.append(f"UNTIL={d.strftime('%Y%m%d')}T235959Z")
    return ["RRULE:" + ";".join(parts)]


def build_body(tenant: str, *, title: str, start: datetime, end: datetime, all_day: bool, location: str = "",
               description: str = "", attendees: list[str] | None = None, reminders: list[int] | None = None,
               repeat=None, color: str | None = None) -> dict[str, Any]:
    tz = _tz(tenant)
    body: dict[str, Any] = {"summary": title.strip()[:300] or "(no title)",
                            "start": _when_body(start, all_day, tz), "end": _when_body(end, all_day, tz)}
    if location:
        body["location"] = location[:500]
    if description:
        body["description"] = description[:8000]
    if attendees:
        body["attendees"] = [{"email": a} for a in attendees]
    if reminders is not None:
        mins = sorted({max(0, min(int(m), 40320)) for m in reminders})[:5]
        body["reminders"] = {"useDefault": False, "overrides": [{"method": "popup", "minutes": m} for m in mins]}
    r = rrule(repeat)
    if r:
        body["recurrence"] = r
    if color:
        body["colorId"] = str(color)
    return body


def _publish_event(conv: str, v: dict, status: str = "added") -> None:
    if conv:
        bus.publish(conv, "calendar_event", {**v, "status": status})


def create_now(tenant: str, conv: str, box, cal_id: str, body: dict, meet: bool, send_updates: str = "none") -> dict:
    e = box.create(cal_id, body, send_updates, meet)
    v = view(box, cal_id, cal_id, e, _tz(tenant))
    _publish_event(conv, v, "added")
    return v


# ---------------- changes that inform other people: confirm card first ----------------
def pend(tenant: str, conv: str, action: str, payload: dict, summary: dict) -> str:
    with session() as s:
        p = CalendarPending(tenant_id=tenant, conversation_id=conv, action=action, payload=payload, summary=summary)
        s.add(p)
        s.flush()
        return p.id


def pending(tenant: str, pid: str) -> dict | None:
    with session() as s:
        p = s.get(CalendarPending, pid)
        if p is None or p.tenant_id != tenant:
            return None
        return {"id": p.id, "action": p.action, "payload": p.payload, "summary": p.summary, "status": p.status,
                "conversation_id": p.conversation_id}


def run_pending(tenant: str, pid: str) -> dict[str, Any]:
    p = pending(tenant, pid)
    if p is None or p["status"] != "pending":
        raise CalError("Yeh calendar badlav ab baaki nahi hai.")
    pl, conv = p["payload"], p["conversation_id"]
    box = get_box(tenant, pl["box"])
    tz = _tz(tenant)
    try:
        if p["action"] == "create":
            v = create_now(tenant, conv, box, pl["cal"], pl["body"], pl.get("meet", False), "all")
            msg = f"Invite bhej diya: \"{v['title']}\" {v['start']}" + (f" · Meet: {v['meet_link']}" if v["meet_link"] else "")
        elif p["action"] == "update":
            e = box.patch(pl["cal"], pl["event"], pl["body"], "all", pl.get("meet", False))
            v = view(box, pl["cal"], pl["cal"], e, tz)
            _publish_event(conv, v, "updated")
            msg = f"Meeting badal di aur sabko bata diya: \"{v['title']}\" ab {v['start']}."
        elif p["action"] == "cancel":
            box.delete(pl["cal"], pl["event"], "all" if pl.get("notify") else "none")
            _publish_event(conv, {**p["summary"], "id": pl["ref"]}, "cancelled")
            msg = f"\"{p['summary'].get('title', '')}\" cancel kar diya" + (" aur sabko bata diya." if pl.get("notify") else ".")
        elif p["action"] == "decline":
            respond_now(tenant, pl["ref"], "declined")
            _publish_event(conv, {**p["summary"], "id": pl["ref"]}, "declined")
            msg = f"\"{p['summary'].get('title', '')}\" ke liye mana kar diya (organizer ko bata diya)."
        else:
            raise CalError("unknown calendar action")
    except CalError as e:
        with session() as s:
            s.get(CalendarPending, pid).status = "failed"
        raise
    with session() as s:
        s.get(CalendarPending, pid).status = "done"
    return {"message": msg}


# ---------------- RSVP ----------------
def respond_now(tenant: str, ref: str, response: str) -> dict[str, Any]:
    if response not in ("accepted", "declined", "tentative"):
        raise CalError("response: accepted, declined ya tentative")
    box, cal_id, raw, v = get_event(tenant, ref)
    if box.kind != "google":
        from .caldav_cal import NEEDS_SIGNIN
        raise CalError(NEEDS_SIGNIN)
    atts = raw.get("attendees") or []
    mine = [a for a in atts if a.get("self") or (a.get("email") or "").lower() == box.address]
    if not mine:
        raise CalError("Aap is event mein invited nahi hain (ya aap hi organizer hain).")
    for a in mine:
        a["responseStatus"] = response
    e = box.patch(cal_id, raw["id"], {"attendees": atts}, "all")
    return view(box, cal_id, cal_id, e, _tz(tenant))


# ---------------- free time ----------------
def free_slots(tenant: str, day_from: date, day_to: date, minutes: int = 60, work_start: str = "09:00",
               work_end: str = "19:00", limit: int = 10) -> list[dict[str, Any]]:
    tz = _tz(tenant)
    minutes = max(10, min(int(minutes or 60), 600))
    ws_h, ws_m = [int(x) for x in work_start.split(":")[:2]]
    we_h, we_m = [int(x) for x in work_end.split(":")[:2]]
    start = datetime(day_from.year, day_from.month, day_from.day, tzinfo=tz)
    end = datetime(day_to.year, day_to.month, day_to.day, tzinfo=tz) + timedelta(days=1)
    spans: list[tuple[datetime, datetime]] = []
    by_box: dict[str, tuple[Any, list[str]]] = {}
    for box, cal_id, _ in _reading(tenant):
        by_box.setdefault(box.key, (box, []))[1].append(cal_id)
    for box, cal_ids in by_box.values():
        spans += box.busy(cal_ids, start, end)
    spans = sorted((a.astimezone(tz), b.astimezone(tz)) for a, b in spans)
    out = []
    nowl = datetime.now(tz)
    d = day_from
    while d <= day_to and len(out) < limit:
        w0 = datetime(d.year, d.month, d.day, ws_h, ws_m, tzinfo=tz)
        w1 = datetime(d.year, d.month, d.day, we_h, we_m, tzinfo=tz)
        cur = max(w0, nowl.replace(second=0, microsecond=0) + timedelta(minutes=(15 - nowl.minute % 15) % 15)) \
            if d == nowl.date() else w0
        for a, b in spans + [(w1, w1)]:
            if b <= cur:
                continue
            if a > cur:
                gap_end = min(a, w1)
                if (gap_end - cur) >= timedelta(minutes=minutes):
                    out.append({"start": _fmt(cur, tz), "end": _fmt(gap_end, tz), "start_iso": cur.isoformat(),
                                "minutes_free": int((gap_end - cur).total_seconds() // 60)})
                    if len(out) >= limit:
                        break
            cur = max(cur, b)
            if cur >= w1:
                break
        d += timedelta(days=1)
    return out


# ---------------- meeting alerts ----------------
def _tenants_with_calendar() -> set[str]:
    from .. import accounts as acc
    from .. import gcal
    from ..config import get_settings
    from .accounts import CAL_SCOPE
    out: set[str] = set()
    with session() as s:
        out |= set(s.scalars(select(CalendarAccount.tenant_id)).all())
        for c in s.scalars(select(OAuthConnection).where(OAuthConnection.provider == "google")).all():
            if CAL_SCOPE in (c.scopes or "").split():
                try:
                    out.add(acc.tenant_of_user(c.user_id))
                except Exception:
                    pass
    if gcal.configured():
        out.add(get_settings().tenant_id)
    return out


def _conversation_for(tenant: str) -> str | None:
    from .. import convs
    cur = convs.current(tenant)     # v0.158 the chat she is in first (a saved alert chat may be one she left)
    if cur:
        return cur
    p = prefs(tenant)
    with session() as s:
        for cid in (p.get("alert_conversation_id"), getattr(s.get(Profile, tenant), "briefing_conversation_id", None)):
            if cid and s.get(Conversation, cid):
                return cid
        c = s.scalars(select(Conversation).where(Conversation.tenant_id == tenant)
                      .order_by(Conversation.created_at.desc())).first()
        return c.id if c else None


def alerts_tick() -> int:
    sent = 0
    for tenant in _tenants_with_calendar():
        mins = prefs(tenant)["alert_minutes"]
        if not mins:
            continue
        nowu = now()
        try:
            evs = agenda(tenant, nowu, nowu + timedelta(minutes=mins + 1), limit=20)["events"]
        except Exception as e:
            log.info("calendar alerts skipped for %s: %s", tenant, e)
            continue
        for v in evs:
            if v["all_day"] or v["my_response"] == "declined" or not v["start_iso"]:
                continue
            st = datetime.fromisoformat(v["start_iso"])
            if st < nowu - timedelta(minutes=1):
                continue
            key = f"{v['id']}|{v['start_iso']}"[:600]
            with session() as s:
                if s.scalar(select(CalendarAlert.id).where(CalendarAlert.tenant_id == tenant, CalendarAlert.event_key == key)):
                    continue
                s.add(CalendarAlert(tenant_id=tenant, event_key=key))
            conv = _conversation_for(tenant)
            if not conv:
                continue
            left = max(0, int((st - nowu).total_seconds() // 60))
            text = f"⏰ {left} minute mein: {v['title']}" + (f" · {v['location']}" if v["location"] else "")
            if v["meet_link"]:
                text += f"\nGoogle Meet: {v['meet_link']}"
            notify(conv, text)
            _publish_event(conv, v, "soon")
            sent += 1
    with session() as s:   # keep the table small
        for old in s.scalars(select(CalendarAlert).where(CalendarAlert.created_at < now() - timedelta(days=3))).all():
            s.delete(old)
    return sent


def today_lines(tenant: str) -> list[str]:
    """For the morning briefing."""
    tz = _tz(tenant)
    d = datetime.now(tz).date()
    start = datetime(d.year, d.month, d.day, tzinfo=tz)
    evs = agenda(tenant, start, start + timedelta(days=1), limit=15)["events"]
    lines = []
    for v in evs:
        if v["all_day"]:
            lines.append(f"{v['title']} (poora din)")
        else:
            t = datetime.fromisoformat(v["start_iso"]).astimezone(tz).strftime("%I:%M %p").lstrip("0")
            lines.append(f"{t} {v['title']}")
    return lines
