"""Google Calendar: connecting by Google sign-in, agenda across calendars, adding (Meet, reminders, repeat), invites /
reschedules / cancels / declines behind confirm cards, RSVP, free slots, meeting alerts, briefing, and the older
CalDAV route for the server owner."""
import asyncio
import json
from datetime import datetime, timedelta
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_bazar import _events, _notices, bz  # noqa: F401
from tests.test_life import conv_ctx

IST = ZoneInfo("Asia/Kolkata")
ME = "meghana@fnw.in"


def _iso(dt):
    return dt.isoformat()


class FakeGoogle:
    """Google Calendar API v3 (+ token / userinfo), in memory."""

    def __init__(self):
        self.cals = {"primary": {"id": ME, "summary": ME, "primary": True, "accessRole": "owner", "selected": True},
                     "hol": {"id": "en.indian#holiday@group.v.calendar.google.com", "summary": "Holidays in India",
                             "accessRole": "reader", "selected": True},
                     "other": {"id": "family@group.calendar.google.com", "summary": "Family", "accessRole": "owner",
                               "selected": False}}
        self.events = {}     # calendar id -> {event id: event}
        self.calls = []
        self.n = 0

    def add(self, cal, ev):
        self.n += 1
        ev = {"id": ev.get("id") or f"ev{self.n}", "status": "confirmed", "htmlLink": f"https://calendar.google.com/e/{self.n}",
              "organizer": ev.pop("organizer", {"email": ME, "self": True}), **ev}
        self.events.setdefault(cal, {})[ev["id"]] = ev
        return ev

    @staticmethod
    def _start(e):
        s = e["start"]
        return datetime.fromisoformat(s["dateTime"]) if "dateTime" in s else datetime.fromisoformat(s["date"]).replace(tzinfo=IST)

    def __call__(self, req: httpx.Request):
        path, params = req.url.path, req.url.params
        try:
            body = json.loads(req.content) if req.content else None
        except ValueError:
            body = None                      # form-encoded token requests
        self.calls.append((req.method, path, dict(params), body))
        if req.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at", "refresh_token": "rt", "expires_in": 3600,
                                             "scope": "openid email https://www.googleapis.com/auth/calendar"})
        if req.url.host == "openidconnect.googleapis.com":
            return httpx.Response(200, json={"email": ME, "name": "Meghana"})
        assert req.headers["authorization"] == "Bearer at"
        p = path.removeprefix("/calendar/v3")
        if p == "/users/me/calendarList":
            return httpx.Response(200, json={"items": list(self.cals.values())})
        if p == "/freeBusy":
            body = json.loads(req.content)
            t0, t1 = datetime.fromisoformat(body["timeMin"]), datetime.fromisoformat(body["timeMax"])
            out = {}
            for it in body["items"]:
                busy = [{"start": e["start"]["dateTime"], "end": e["end"]["dateTime"]}
                        for e in self.events.get(it["id"], {}).values() if "dateTime" in e["start"] and t0 <= self._start(e) < t1]
                out[it["id"]] = {"busy": busy}
            return httpx.Response(200, json={"calendars": out})
        parts = p.split("/")       # /calendars/<cal>/events[/<id>]
        cal = unquote(parts[2])
        evs = self.events.setdefault(cal, {})
        if len(parts) == 4 and req.method == "GET":
            t0, t1 = datetime.fromisoformat(params["timeMin"]), datetime.fromisoformat(params["timeMax"])
            items = [e for e in evs.values() if t0 <= self._start(e) < t1]
            if params.get("q"):
                items = [e for e in items if params["q"].lower() in e.get("summary", "").lower()]
            return httpx.Response(200, json={"items": sorted(items, key=self._start)})
        if len(parts) == 4 and req.method == "POST":
            body = json.loads(req.content)
            if body.pop("conferenceData", None):
                assert params["conferenceDataVersion"] == "1"
                body["hangoutLink"] = "https://meet.google.com/abc-defg-hij"
            return httpx.Response(200, json=self.add(cal, body))
        eid = unquote(parts[4])
        if eid not in evs:
            return httpx.Response(404, json={"error": "notFound"})
        if req.method == "GET":
            return httpx.Response(200, json=evs[eid])
        if req.method == "PATCH":
            body = json.loads(req.content)
            if body.pop("conferenceData", None):
                body["hangoutLink"] = "https://meet.google.com/new-link"
            evs[eid].update(body)
            return httpx.Response(200, json=evs[eid])
        if req.method == "DELETE":
            del evs[eid]
            return httpx.Response(204)
        return httpx.Response(400)


@pytest.fixture
def g(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.cal import service as cs
    from app.mailbox import accounts as ma
    cs._cal_cache.clear()
    fake = FakeGoogle()
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    yield fake
    ma.set_http(None)


def _connect():
    from app import main
    with TestClient(main.app) as c:
        url = c.get("/api/calendar/link").json()["url"]
        assert "auth%2Fcalendar" in url and "state=cal_" in url
        state = httpx.URL(url).params["state"]
        page = c.get("/auth/google/callback", params={"code": "c", "state": state})
        assert page.status_code == 200 and ME in page.text
        return c.get("/api/calendar/accounts").json()


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


def _today(h, m=0, days=0):
    d = datetime.now(IST).date() + timedelta(days=days)
    return datetime(d.year, d.month, d.day, h, m, tzinfo=IST)


def _dt(dt):
    return {"dateTime": _iso(dt), "timeZone": "Asia/Kolkata"}


def test_connect_and_agenda_across_calendars(g):
    tom = _today(10, days=1)
    g.add(ME, {"summary": "Team standup", "start": _dt(tom), "end": _dt(tom + timedelta(minutes=30))})
    g.add(ME, {"summary": "ITPC training", "start": _dt(tom.replace(hour=15)), "end": _dt(tom.replace(hour=17)),
               "location": "BSNL Pune", "hangoutLink": "https://meet.google.com/x",
               "attendees": [{"email": ME, "self": True, "responseStatus": "accepted"},
                             {"email": "officer@bsnl.in", "responseStatus": "needsAction"}]})
    g.add("en.indian#holiday@group.v.calendar.google.com", {"summary": "Diwali", "start": {"date": tom.date().isoformat()},
                                                             "end": {"date": (tom.date() + timedelta(days=1)).isoformat()}})
    g.add("family@group.calendar.google.com", {"summary": "Not read", "start": _dt(tom), "end": _dt(tom)})
    st = _connect()
    assert st["accounts"][0]["address"] == ME and st["accounts"][0]["full"]
    assert {c["name"]: c["reading"] for c in st["calendars"]} == {ME: True, "Holidays in India": True, "Family": False}
    out = run("calendar_agenda", {"from_date": tom.date().isoformat()}, conv_ctx())
    assert [e["title"] for e in out["events"]] == ["Diwali", "Team standup", "ITPC training"]   # all-day first
    itpc = out["events"][2]
    assert itpc["meet_link"] and itpc["my_response"] == "accepted" and itpc["attendees"][0]["email"] == "officer@bsnl.in"
    assert out["events"][0]["calendar"] == "Holidays in India" and out["events"][0]["all_day"]


def test_private_event_added_at_once_with_meet_reminders_repeat(g):
    _connect()
    ctx = conv_ctx()
    start = _today(16, days=2).strftime("%Y-%m-%dT%H:%M")
    out = run("calendar_add_event", {"title": "Gym", "start": start, "meet": True, "reminders": [10, 60],
                                     "repeat": {"freq": "weekly", "days": ["MO", "TH"], "count": 8}}, ctx)
    assert out["added"] and out["event"]["meet_link"] == "https://meet.google.com/abc-defg-hij"
    post = [c for c in g.calls if c[0] == "POST" and c[1].endswith("/events")][-1]
    assert post[2]["sendUpdates"] == "none"
    body = post[3]
    assert body["recurrence"] == ["RRULE:FREQ=WEEKLY;BYDAY=MO,TH;COUNT=8"]
    assert body["reminders"]["overrides"] == [{"method": "popup", "minutes": 10}, {"method": "popup", "minutes": 60}]
    assert body["start"]["timeZone"] == "Asia/Kolkata"
    card = _events(ctx.conversation_id, "calendar_event")[-1]
    assert card["title"] == "Gym" and card["status"] == "added" and card["link"].startswith("https://calendar.google.com")
    allday = run("calendar_add_event", {"title": "Leave", "start": _today(0, days=5).date().isoformat(), "all_day": True}, ctx)
    assert allday["event"]["all_day"]


def test_invite_waits_for_approval(bz, g):  # noqa: F811
    _connect()
    from app.mailbox import contacts
    contacts.learn("default", [("Swati Sirsath", "swati@fnw.in")], 1.0, sent=True)
    ctx = Ctx("default", bz["conv"])
    out = run("calendar_add_event", {"title": "Sales review", "start": _today(11, days=1).strftime("%Y-%m-%dT%H:%M"),
                                     "attendees": ["Swati"], "meet": True}, ctx)
    assert out["needs_approval"] and not g.events.get(ME)            # nothing created yet
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Invite bhejein?" and "swati@fnw.in" in json.dumps(card)
    bz["svc"].decide("default", card["id"], "approve")
    ev = list(g.events[ME].values())[0]
    assert ev["attendees"] == [{"email": "swati@fnw.in"}] and ev["hangoutLink"]
    post = [c for c in g.calls if c[0] == "POST" and c[1].endswith("/events")][-1]
    assert post[2]["sendUpdates"] == "all"


def test_reschedule_cancel_and_decline(bz, g):  # noqa: F811
    _connect()
    ctx = Ctx("default", bz["conv"])
    t = _today(10, days=1)
    priv = g.add(ME, {"summary": "Dentist", "start": _dt(t), "end": _dt(t + timedelta(minutes=30))})
    shared = g.add(ME, {"summary": "Vendor call", "start": _dt(t.replace(hour=12)), "end": _dt(t.replace(hour=13)),
                        "attendees": [{"email": ME, "self": True}, {"email": "ramesh@vendor.in"}]})
    guest = g.add(ME, {"summary": "BSNL meeting", "start": _dt(t.replace(hour=15)), "end": _dt(t.replace(hour=16)),
                       "organizer": {"email": "gm@bsnl.in"},
                       "attendees": [{"email": ME, "self": True, "responseStatus": "needsAction"}, {"email": "gm@bsnl.in"}]})
    found = run("calendar_find_event", {"query": "Dentist"}, ctx)["events"][0]["id"]
    # private: moved at once
    out = run("calendar_update_event", {"event_id": found, "start": t.replace(hour=11).strftime("%Y-%m-%dT%H:%M")}, ctx)
    assert out["updated"] and g.events[ME][priv["id"]]["start"]["dateTime"].startswith(t.replace(hour=11).isoformat()[:16])
    assert g.events[ME][priv["id"]]["end"]["dateTime"].startswith(t.replace(hour=11, minute=30).isoformat()[:16])
    # shared: card first, then everyone is told
    sid = run("calendar_find_event", {"query": "Vendor"}, ctx)["events"][0]["id"]
    out = run("calendar_update_event", {"event_id": sid, "start": t.replace(hour=14).strftime("%Y-%m-%dT%H:%M")}, ctx)
    assert out["needs_approval"] and g.events[ME][shared["id"]]["start"]["dateTime"].startswith(t.replace(hour=12).isoformat()[:13])
    card = _events(bz["conv"], "bazar_approval")[-1]
    bz["svc"].decide("default", card["id"], "approve")
    assert g.events[ME][shared["id"]]["start"]["dateTime"].startswith(t.replace(hour=14).isoformat()[:13])
    assert [c for c in g.calls if c[0] == "PATCH"][-1][2]["sendUpdates"] == "all"
    # cancel the shared one: card, then cancellation mails
    run("calendar_cancel_event", {"event_id": sid}, ctx)
    assert shared["id"] in g.events[ME]
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert shared["id"] not in g.events[ME]
    assert [c for c in g.calls if c[0] == "DELETE"][-1][2]["sendUpdates"] == "all"
    # a guest can't change the meeting, and "cancel" means decline
    gid = run("calendar_find_event", {"query": "BSNL"}, ctx)["events"][0]["id"]
    with pytest.raises(ToolError, match="organizer"):
        run("calendar_update_event", {"event_id": gid, "title": "x"}, ctx)
    run("calendar_cancel_event", {"event_id": gid}, ctx)
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Meeting ke liye mana karein?"
    bz["svc"].decide("default", card["id"], "approve")
    me = [a for a in g.events[ME][guest["id"]]["attendees"] if a.get("self")][0]
    assert me["responseStatus"] == "declined" and guest["id"] in g.events[ME]


def test_accept_invite_at_once(g):
    _connect()
    t = _today(15, days=1)
    ev = g.add(ME, {"summary": "Board meet", "start": _dt(t), "end": _dt(t + timedelta(hours=1)),
                    "organizer": {"email": "ceo@x.in"}, "attendees": [{"email": ME, "self": True}, {"email": "ceo@x.in"}]})
    ctx = conv_ctx()
    eid = run("calendar_find_event", {"query": "Board"}, ctx)["events"][0]["id"]
    out = run("calendar_respond", {"event_id": eid, "response": "accepted"}, ctx)
    assert out["responded"] == "accepted"
    assert [a for a in g.events[ME][ev["id"]]["attendees"] if a.get("self")][0]["responseStatus"] == "accepted"


def test_free_slots(g):
    _connect()
    day = _today(0, days=1)
    for h0, h1 in ((10, 11), (15, 17)):
        g.add(ME, {"summary": "busy", "start": _dt(day.replace(hour=h0)), "end": _dt(day.replace(hour=h1))})
    out = run("calendar_free_slots", {"from_date": day.date().isoformat(), "minutes": 60}, conv_ctx())
    got = [(datetime.fromisoformat(s["start_iso"]).hour, s["minutes_free"]) for s in out["free"]]
    assert got == [(9, 60), (11, 240), (17, 120)]


def test_meeting_alert_once_and_briefing(g):
    _connect()
    from app.cal import service as cs
    from app.life import compose_briefing
    soon = datetime.now(IST) + timedelta(minutes=8)
    g.add(ME, {"summary": "Client call", "start": _dt(soon), "end": _dt(soon + timedelta(minutes=30)),
               "hangoutLink": "https://meet.google.com/zzz"})
    ctx = conv_ctx()
    run("calendar_agenda", {}, ctx)                       # remembers which chat to nudge
    assert cs.alerts_tick() == 1
    assert cs.alerts_tick() == 0                          # only once
    assert any("minute mein: Client call" in (n or "") and "meet.google.com/zzz" in n for n in _notices(ctx.conversation_id))
    text = asyncio.run(compose_briefing("default"))
    if soon.date() == datetime.now(IST).date():
        assert "Aaj calendar mein:" in text and "Client call" in text
    run("calendar_settings", {"meeting_alerts": 0}, ctx)
    assert cs.prefs("default")["alert_minutes"] == 0


def test_settings_choose_calendars(g):
    _connect()
    ctx = conv_ctx()
    out = run("calendar_settings", {"read_calendars": [ME, "Family"], "default_calendar": "Family"}, ctx)
    reading = {c["name"]: c["reading"] for c in out["calendars"]}
    assert reading == {ME: True, "Holidays in India": False, "Family": True}
    run("calendar_add_event", {"title": "Bday dinner", "start": _today(20, days=3).strftime("%Y-%m-%dT%H:%M")}, ctx)
    assert any(e["summary"] == "Bday dinner" for e in g.events["family@group.calendar.google.com"].values())


def test_not_connected_points_to_profile(env):
    with pytest.raises(ToolError, match="Profile > Calendar"):
        run("calendar_agenda", {}, Ctx("someone", "c"))


# ---------------- the server owner's older CalDAV route ----------------
class FakeEvent:
    def __init__(self, comp):
        self.icalendar_component = comp
        self.deleted = False

    def delete(self):
        self.deleted = True


def comp(summary, start, end, uid, location=""):
    return {"summary": summary, "dtstart": type("X", (), {"dt": start})(), "dtend": type("X", (), {"dt": end})(),
            "uid": uid, "location": location, "description": ""}


class FakeDav:
    def __init__(self, events):
        self.events = events
        self.saved = []

    def search(self, start=None, end=None, event=True, expand=True):
        return [e for e in self.events if start <= e.icalendar_component["dtstart"].dt.astimezone(ZoneInfo("UTC")) <= end]

    def save_event(self, ical):
        self.saved.append(ical)

    def event_by_uid(self, uid):
        for e in self.events:
            if e.icalendar_component["uid"] == uid:
                return e
        raise Exception("nf")


def test_owner_caldav_route(bz, monkeypatch):  # noqa: F811
    from app import gcal
    t = _today(10, days=1)
    dav = FakeDav([FakeEvent(comp("Team standup", t, t + timedelta(minutes=30), "u1@g")),
                   FakeEvent(comp("Dentist", t.replace(hour=12), t.replace(hour=13), "u2@g"))])
    monkeypatch.setattr(gcal, "configured", lambda: True)
    monkeypatch.setattr(gcal, "_client", lambda: object())
    monkeypatch.setattr(gcal, "_primary", lambda client: dav)
    monkeypatch.setattr(gcal, "_tz", lambda: IST)
    monkeypatch.setenv("EMAIL_ADDRESS", "owner@gmail.com")
    from app.config import get_settings
    get_settings.cache_clear()
    ctx = Ctx("default", bz["conv"])
    out = run("calendar_agenda", {"from_date": t.date().isoformat()}, ctx)
    assert [e["title"] for e in out["events"]] == ["Team standup", "Dentist"] and out["events"][0]["id"] == "env~primary~u1@g"
    run("calendar_add_event", {"title": "Client call", "start": t.replace(hour=16).strftime("%Y-%m-%dT%H:%M")}, ctx)
    assert "Client call" in dav.saved[0]
    with pytest.raises(ToolError, match="Profile > Calendar"):
        run("calendar_add_event", {"title": "x", "start": t.replace(hour=17).strftime("%Y-%m-%dT%H:%M"), "meet": True}, ctx)
    run("calendar_cancel_event", {"event_id": "env~primary~u2@g"}, ctx)
    assert not dav.events[1].deleted
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert dav.events[1].deleted
    with pytest.raises(ToolError, match="juda nahi"):                   # not for other users
        run("calendar_agenda", {}, Ctx("usr_other", "c"))
