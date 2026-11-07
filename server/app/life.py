"""Daily-life helpers: user profile, time handling, reminders, weather and the morning briefing."""
from __future__ import annotations

import asyncio
import calendar
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select

from .db import ListItem, MemoryFact, Profile, Reminder, as_utc, now, session

log = logging.getLogger("santosh.life")
REPEATS = ("none", "daily", "weekdays", "weekly", "monthly")


def get_profile(tenant_id: str) -> Profile:
    with session() as s:
        p = s.get(Profile, tenant_id)
        if p is None:
            p = Profile(tenant_id=tenant_id, timezone="Asia/Kolkata")
            s.add(p)
            s.flush()
        s.expunge(p)
        return p


def tz_of(tenant_id: str) -> ZoneInfo:
    try:
        return ZoneInfo(get_profile(tenant_id).timezone or "Asia/Kolkata")
    except Exception:
        return ZoneInfo("Asia/Kolkata")


def parse_local(when: str, tz: ZoneInfo) -> datetime:
    """'2026-10-18T06:00' (user's local time) -> aware UTC datetime."""
    s = (when or "").strip().replace(" ", "T")
    if not s:
        raise ValueError("No time given")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


def fmt_local(dt: datetime, tz: ZoneInfo) -> str:
    d = as_utc(dt).astimezone(tz)
    today = datetime.now(tz).date()
    day = "aaj" if d.date() == today else "kal" if d.date() == today + timedelta(days=1) else d.strftime("%a %d %b")
    return f"{day} {d.strftime('%I:%M %p').lstrip('0')}"


def next_due(due: datetime, repeat: str, tz: ZoneInfo, anchor_day: int | None = None) -> datetime | None:
    """Next occurrence after `due`, keeping the same local clock time.
    v0.667 `anchor_day`: a monthly repeat's own day (the 31st stays the 31st where the month has one; it used to clamp
    from the PREVIOUS due date, so Jan 31 -> Feb 28 -> Mar 28 -> the 28th for ever)."""
    if repeat == "none":
        return None
    if repeat == "hourly":
        return as_utc(due) + timedelta(hours=1)
    local = as_utc(due).astimezone(tz)
    if repeat == "daily":
        nxt = local + timedelta(days=1)
    elif repeat == "weekly":
        nxt = local + timedelta(days=7)
    elif repeat == "weekdays":
        nxt = local + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
    elif repeat == "monthly":
        y, m = (local.year + (local.month // 12), local.month % 12 + 1)
        d = min(int(anchor_day or local.day), calendar.monthrange(y, m)[1])
        nxt = local.replace(year=y, month=m, day=d)
    else:
        return None
    # rebuild from wall-clock parts so DST-free zones and others stay on the same local time
    nxt = datetime(nxt.year, nxt.month, nxt.day, local.hour, local.minute, tzinfo=tz)
    return nxt.astimezone(timezone.utc)


def reminder_view(r: Reminder, tz: ZoneInfo) -> dict:
    return {"id": r.id, "text": r.text, "due_at": as_utc(r.due_at).isoformat(), "when": fmt_local(r.due_at, tz),
            "repeat": r.repeat, "status": r.status}


def upcoming_reminders(tenant_id: str, limit: int = 50, include_done: bool = False) -> list[dict]:
    tz = tz_of(tenant_id)
    with session() as s:
        q = select(Reminder).where(Reminder.tenant_id == tenant_id)
        if not include_done:
            q = q.where(Reminder.status == "active")
        rows = s.scalars(q.order_by(Reminder.due_at).limit(limit)).all()
        return [reminder_view(r, tz) for r in rows]


PINNED_CHARS = 1500     # "hamesha yaad": always in the prompt, kept short (idea from Hermes Agent)
RECENT_FACTS = 40       # v0.605: the default of the `memory_recent_facts` setting (see recent_facts()); kept for callers


def recent_facts() -> int:
    """v0.605 JUST IN TIME: how many of her newest (unpinned) facts ride the system prompt. 40 -> 15 by default:
    pinned facts all ride, the facts closest IN MEANING to her message ride the turn block (yaad.relevant_facts),
    and the rest are one yaad_khojo / memory_search away - the Claude shape (a short memory summary in, the rest
    looked up)."""
    try:
        from .config import get_settings
        return max(0, int(getattr(get_settings(), "memory_recent_facts", 15)))
    except Exception:
        return 15


def memory_facts(tenant_id: str, limit: int = 60, conversation_id: str = "") -> list[MemoryFact]:
    """Pinned facts first (all of them), then the newest others, oldest of those first.
    v0.246 FENCE: with a chat, facts Hoola picked up in ANOTHER Session (or in a general chat, for a Session chat) are
    left out; her own / pinned / older facts are global."""
    from .fence import chats_in
    allowed = chats_in(tenant_id, conversation_id) if conversation_id else None
    with session() as s:
        pinned = s.scalars(select(MemoryFact).where(MemoryFact.tenant_id == tenant_id, MemoryFact.pinned.is_(True))
                           .order_by(MemoryFact.id)).all()
        q = select(MemoryFact).where(MemoryFact.tenant_id == tenant_id,
                                     (MemoryFact.pinned.is_(None)) | (MemoryFact.pinned.is_(False)))
        if allowed is not None:
            from .fence import main_memory_ok   # v0.609 a Session with 'use main memory' off: only its own facts
            q = q.where(MemoryFact.conversation_id.is_(None) | MemoryFact.conversation_id.in_(allowed)) \
                if main_memory_ok(conversation_id) else q.where(MemoryFact.conversation_id.in_(allowed))
        rest = s.scalars(q.order_by(MemoryFact.id.desc()).limit(max(0, limit))).all()
        for r in list(pinned) + list(rest):
            s.expunge(r)
        return list(pinned) + list(reversed(rest))


def memory_count(tenant_id: str) -> int:
    from sqlalchemy import func
    with session() as s:
        return s.scalar(select(func.count()).select_from(MemoryFact).where(MemoryFact.tenant_id == tenant_id)) or 0


def pin_fact(tenant_id: str, fact_id: int, pinned: bool) -> MemoryFact:
    with session() as s:
        f = s.get(MemoryFact, int(fact_id))
        if f is None or f.tenant_id != tenant_id:
            raise ValueError("Yeh yaad nahi mili.")
        if pinned and not f.pinned:
            used = sum(len(x.text) for x in s.scalars(select(MemoryFact).where(
                MemoryFact.tenant_id == tenant_id, MemoryFact.pinned.is_(True))).all())
            if used + len(f.text) > PINNED_CHARS:
                raise ValueError(f"'Hamesha yaad' mein {PINNED_CHARS} akshar tak hi aate hain. Pehle koi purani pin hataiye.")
        f.pinned = bool(pinned)
        s.flush()
        s.expunge(f)
        return f


def context_block(tenant_id: str, conversation_id: str = "") -> str:
    """What Santosh should always know about this user; added to the system prompt.
    v0.246 `conversation_id`: the facts are fenced to that chat's Session (fence.py)."""
    p = get_profile(tenant_id)
    tz = tz_of(tenant_id)
    lines = []
    try:   # v0.250 "Mere baare mein": her memory page first (unless she turned recall off)
        from .aboutme import block as _about
        from .fence import main_memory_ok   # v0.609 a Session on its own memory never reads her main page
        ab = _about(tenant_id) if main_memory_ok(conversation_id) else ""
        if ab:
            lines.append(ab)
    except Exception:
        log.exception("about-me block failed")
    if p.name:
        lines.append(f"User's name: {p.name}")
    if p.city:
        lines.append(f"User's city: {p.city}")
    if p.language:
        lines.append(f"Preferred language: {p.language}")
    lines.append(f"User's time zone: {p.timezone or 'Asia/Kolkata'}; local time now {datetime.now(tz).strftime('%A %d %B %Y %H:%M')}")
    if p.briefing_time:
        lines.append(f"Morning briefing is set for {p.briefing_time} every day")
    jobs = active_routines(tenant_id)
    if jobs:
        lines.append("Your automatic jobs for this user (id: title, repeat, next run):")
        lines += [f"- {j['id']}: {j['title']}, {j['repeat']}, {j['next_run_local']}" for j in jobs]
    facts = memory_facts(tenant_id, recent_facts(), conversation_id)
    pins = [f for f in facts if f.pinned]
    if pins:
        lines.append("ALWAYS keep in mind (the user pinned these; id: fact):")
        lines += [f"- {f.id}: {f.text}" for f in pins]
    others = [f for f in facts if not f.pinned]
    # v0.665 SACH KA HISAAB: a fact Hoola picked up by itself (source auto) is NOT her instruction, and an old fact may be
    # out of date - both used to sit under "the user asked you to remember", undated, and were stated to her as truth
    hers = [f for f in others if (f.source or "") != "auto"]
    guessed = [f for f in others if (f.source or "") == "auto"]

    def _when(f) -> str:
        try:
            return f.created_at.strftime("%d %b %Y")
        except Exception:   # noqa: BLE001
            return "?"
    if hers:
        lines.append("Things the user asked you to remember (id: fact, saved on):")
        lines += [f"- {f.id}: {f.text} (saved {_when(f)})" for f in hers]
    if guessed:
        lines.append("Things YOU picked up from earlier chats - your own reading, not her words (id: fact, noted on). "
                     "They can be wrong or out of date: before you act on one or state it as a fact, check it with her "
                     "in a few words (e.g. 'aapka godown ab bhi Chakan mein hai na?'):")
        lines += [f"- {f.id}: {f.text} (noted {_when(f)})" for f in guessed]
    if memory_count(tenant_id) > len(facts):
        lines.append("Older things the user told you are not listed here: yaad_khojo (or memory_search for a saved "
                     "fact) finds them in one call - look them up before saying you do not know or asking her again.")
    return "\n".join(lines)


# ---------------- weather (Open-Meteo: free, no key) ----------------
WMO = {0: "saaf aasmaan", 1: "zyadatar saaf", 2: "halke baadal", 3: "baadal", 45: "kohra", 48: "kohra",
       51: "halki boondabaandi", 53: "boondabaandi", 55: "tez boondabaandi", 61: "halki baarish", 63: "baarish",
       65: "tez baarish", 71: "halki barf", 80: "baarish ki bauchhar", 81: "baarish ki bauchhar", 82: "tez bauchhar",
       95: "aandhi-toofan", 96: "toofan aur ole", 99: "toofan aur ole"}

_http: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=10)
    return _http


async def geocode(city: str) -> tuple[float, float, str] | None:
    r = await _client().get("https://geocoding-api.open-meteo.com/v1/search",
                            params={"name": city, "count": 1, "language": "en", "format": "json"})
    r.raise_for_status()
    res = (r.json().get("results") or [])
    if not res:
        return None
    g = res[0]
    return g["latitude"], g["longitude"], f"{g['name']}, {g.get('admin1') or g.get('country', '')}".strip(", ")


async def weather(lat: float, lon: float, tz: str = "Asia/Kolkata") -> dict:
    r = await _client().get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lon, "timezone": tz,
        "current": "temperature_2m,weather_code,relative_humidity_2m,is_day,apparent_temperature,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code,sunrise,sunset",
        "forecast_days": 2})
    r.raise_for_status()
    d = r.json()
    cur, day = d.get("current", {}), d.get("daily", {})
    pick = lambda k, i=0: (day.get(k) or [None])[i]
    return {"now_c": cur.get("temperature_2m"), "humidity": cur.get("relative_humidity_2m"),
            "feels_c": cur.get("apparent_temperature"), "wind_kmph": cur.get("wind_speed_10m"),
            "is_day": bool(cur.get("is_day", 1)),   # v0.166 Aaj ka Din card picks icon/colours from code + day/night
            "now_code": cur.get("weather_code"), "now": WMO.get(cur.get("weather_code"), "mausam"),
            "today_code": pick("weather_code"),
            "today_max_c": pick("temperature_2m_max"), "today_min_c": pick("temperature_2m_min"),
            "rain_chance_pct": pick("precipitation_probability_max"),
            "sunrise": pick("sunrise"), "sunset": pick("sunset"),
            "today": WMO.get(pick("weather_code"), "mausam"),
            "tomorrow_max_c": pick("temperature_2m_max", 1), "tomorrow_min_c": pick("temperature_2m_min", 1),
            "tomorrow_rain_chance_pct": pick("precipitation_probability_max", 1)}


async def weather_for(tenant_id: str, city: str | None = None) -> dict:
    p = get_profile(tenant_id)
    if city and (not p.city or city.strip().lower() != (p.city or "").lower()):
        g = await geocode(city)
        if not g:
            raise ValueError(f"Could not find a place called {city}")
        lat, lon, label = g
    else:
        if p.lat is None or p.lon is None:
            if not p.city:
                raise ValueError("No city known. Ask the user which city they are in, then save it with set_profile.")
            g = await geocode(p.city)
            if not g:
                raise ValueError(f"Could not find {p.city}")
            with session() as s:
                pr = s.get(Profile, tenant_id)
                pr.lat, pr.lon = g[0], g[1]
            lat, lon, label = g
        else:
            lat, lon, label = p.lat, p.lon, p.city
    w = await weather(lat, lon, p.timezone or "Asia/Kolkata")
    w["place"] = label
    return w


# ---------------- morning briefing ----------------
def _today_bounds(tz: ZoneInfo) -> tuple[datetime, datetime, date]:
    d = datetime.now(tz).date()
    start = datetime(d.year, d.month, d.day, tzinfo=tz)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc), d


async def compose_briefing(tenant_id: str) -> str:
    p = get_profile(tenant_id)
    tz = tz_of(tenant_id)
    start, end, d = _today_bounds(tz)
    hello = f"Suprabhat{(' ' + p.name.split(' ')[0]) if p.name else ''}! Aaj {d.strftime('%A, %d %B')} hai."
    parts = [hello]
    try:
        if p.city or p.lat is not None:
            w = await weather_for(tenant_id)
            line = f"{w['place']}: abhi {round(w['now_c'])}°C, {w['now']}. Aaj {round(w['today_min_c'])}-{round(w['today_max_c'])}°C"
            if (w.get("rain_chance_pct") or 0) >= 40:
                line += f", baarish ki {w['rain_chance_pct']}% sambhavna, chhata rakh lijiye"
            parts.append(line + ".")
    except Exception as e:
        log.info("briefing weather skipped: %s", e)
    with session() as s:
        rems = s.scalars(select(Reminder).where(Reminder.tenant_id == tenant_id, Reminder.status == "active",
                                                Reminder.due_at >= start, Reminder.due_at < end)
                         .order_by(Reminder.due_at)).all()
        rem_lines = [f"{as_utc(r.due_at).astimezone(tz).strftime('%I:%M %p').lstrip('0')} {r.text}" for r in rems]
        open_items = s.scalars(select(ListItem).where(ListItem.tenant_id == tenant_id, ListItem.done.is_(False))).all()
    try:
        from .cal import service as cal_service
        cal_lines = await asyncio.to_thread(cal_service.today_lines, tenant_id)
        if cal_lines:
            parts.append("Aaj calendar mein: " + "; ".join(cal_lines) + ".")
    except Exception as e:
        log.info("briefing calendar skipped: %s", e)
    if rem_lines:
        parts.append("Aaj ke reminders: " + "; ".join(rem_lines) + ".")
    else:
        parts.append("Aaj koi reminder nahi hai.")
    if open_items:
        lists: dict[str, int] = {}
        for it in open_items:
            lists[it.list_name] = lists.get(it.list_name, 0) + 1
        parts.append("Lists: " + ", ".join(f"{k} mein {v} cheezein" for k, v in lists.items()) + ".")
    parts.append("Kuch aur karna ho to bas boliye.")
    return "\n".join(parts)


ROUTINE_REPEATS = ("none", "hourly", "daily", "weekdays", "weekly", "monthly")


def routine_view(r, tz: ZoneInfo) -> dict:
    return {"id": r.id, "title": r.title, "instruction": r.instruction, "repeat": r.repeat, "status": r.status,
            "next_run": as_utc(r.next_run).isoformat(), "next_run_local": fmt_local(r.next_run, tz),
            "run_count": r.run_count, "last_run": as_utc(r.last_run).isoformat() if r.last_run else None,
            "last_result": (r.last_result or "")[:300] or None}


def active_routines(tenant_id: str) -> list[dict]:
    from .db import Routine
    tz = tz_of(tenant_id)
    with session() as s:
        rows = s.scalars(select(Routine).where(Routine.tenant_id == tenant_id, Routine.status == "active")
                         .order_by(Routine.next_run)).all()
        return [routine_view(r, tz) for r in rows]


def anchor_of(due: datetime, repeat: str, tz: ZoneInfo) -> int | None:
    """v0.667 the day of the month a monthly repeat keeps (None for any other repeat)."""
    if repeat != "monthly" or due is None:
        return None
    return as_utc(due).astimezone(tz).day
