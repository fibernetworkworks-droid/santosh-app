"""Google Calendar tools against a fake CalDAV calendar."""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app import gcal
from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_life import conv_ctx

IST = ZoneInfo("Asia/Kolkata")


class FakeComp(dict):
    def __init__(self, d):
        super().__init__(d)


class FakeEvent:
    def __init__(self, comp):
        self.icalendar_component = comp
        self.deleted = False

    def delete(self):
        self.deleted = True


def comp(summary, start, end, uid, location="", attendees=None):
    d = {"summary": summary, "dtstart": type("X", (), {"dt": start})(), "dtend": type("X", (), {"dt": end})(),
         "uid": uid, "location": location, "description": ""}
    if attendees:
        d["attendee"] = [f"mailto:{a}" for a in attendees]
    return FakeComp(d)


class FakeCalendar:
    def __init__(self, events):
        self.events = events
        self.saved = []

    def search(self, start=None, end=None, event=True, expand=True):
        out = []
        for e in self.events:
            s = e.icalendar_component["dtstart"].dt
            sdt = s if isinstance(s, datetime) else datetime(s.year, s.month, s.day, tzinfo=IST)
            if start <= sdt.astimezone(ZoneInfo("UTC")) <= end:
                out.append(e)
        return out

    def save_event(self, ical):
        self.saved.append(ical)

    def event_by_uid(self, uid):
        for e in self.events:
            if str(e.icalendar_component["uid"]) == uid:
                return e
        raise Exception("not found")


@pytest.fixture
def cal(monkeypatch):
    events = [
        FakeEvent(comp("Team standup", datetime(2026, 10, 20, 10, 0, tzinfo=IST), datetime(2026, 10, 20, 10, 30, tzinfo=IST), "u1@g")),
        FakeEvent(comp("ITPC training Pune", datetime(2026, 10, 20, 15, 0, tzinfo=IST), datetime(2026, 10, 20, 17, 0, tzinfo=IST),
                       "u2@g", location="BSNL Pune", attendees=["officer@bsnl.in"])),
        FakeEvent(comp("Dentist", datetime(2026, 10, 25, 11, 0, tzinfo=IST), datetime(2026, 10, 25, 11, 30, tzinfo=IST), "u3@g")),
    ]
    fake = FakeCalendar(events)
    monkeypatch.setattr(gcal, "configured", lambda: True)
    monkeypatch.setattr(gcal, "_client", lambda: object())
    monkeypatch.setattr(gcal, "_primary", lambda client: fake)
    monkeypatch.setattr(gcal, "_tz", lambda: IST)
    return fake


def test_agenda_one_day_sorted(cal):
    ctx = conv_ctx()
    out = asyncio.run(dispatch("calendar_agenda", {"from_date": "2026-10-20"}, ctx))
    assert out["count"] == 2
    assert [e["title"] for e in out["events"]] == ["Team standup", "ITPC training Pune"]
    assert out["events"][1]["location"] == "BSNL Pune" and out["events"][1]["attendees"] == ["officer@bsnl.in"]


def test_agenda_range(cal):
    ctx = conv_ctx()
    out = asyncio.run(dispatch("calendar_agenda", {"from_date": "2026-10-20", "to_date": "2026-10-26"}, ctx))
    assert out["count"] == 3


def test_add_event_writes_ical(cal):
    ctx = conv_ctx()
    out = asyncio.run(dispatch("calendar_add_event", {"title": "Client call", "start": "2026-10-21T16:00", "location": "Zoom"}, ctx))
    assert out["title"] == "Client call"
    assert len(cal.saved) == 1
    ics = cal.saved[0]
    assert "Client call" in ics and "SUMMARY" in ics and "DTSTART" in ics


def test_find_and_cancel(cal):
    ctx = conv_ctx()
    import app.gcal as g
    import datetime as dt
    # make "now" land near the events so find()'s window covers them
    real = g.datetime

    class FixedDT(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2026, 10, 20, 9, 0, tzinfo=tz or IST)

    g.datetime = FixedDT
    try:
        found = asyncio.run(dispatch("calendar_find_event", {"query": "ITPC", "days": 10}, ctx))
        assert found["count"] == 1 and found["events"][0]["id"] == "u2@g"
        out = asyncio.run(dispatch("calendar_cancel_event", {"event_id": "u2@g"}, ctx))
        assert out["cancelled"] == "u2@g" and out["title"] == "ITPC training Pune"
        assert cal.events[1].deleted is True
    finally:
        g.datetime = real


def test_not_configured_is_clear_error(monkeypatch):
    monkeypatch.setattr(gcal, "configured", lambda: False)
    with pytest.raises(ToolError, match="connect nahi"):
        asyncio.run(dispatch("calendar_agenda", {}, Ctx("default", "c")))


def test_configured_requires_gmail(monkeypatch):
    import os
    from app.config import get_settings
    for a, want in [("x@gmail.com", True), ("x@outlook.com", False), ("", False)]:
        os.environ["EMAIL_ADDRESS"] = a
        os.environ["EMAIL_PASSWORD"] = "p" if a else ""
        get_settings.cache_clear()
        assert gcal.configured() is want
    os.environ.pop("EMAIL_ADDRESS", None); os.environ.pop("EMAIL_PASSWORD", None)
    get_settings.cache_clear()
