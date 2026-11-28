"""v0.999.190 CALENDAR: the last 8 pieces - default reminders + notification emails, an event in another time zone,
meeting rooms, working hours, birthdays, giving a calendar to another owner, files from the chat on an event, and
Google Tasks. The stand-in checks Google's shapes (Calendar v3 revision 20261118, Tasks v1 revision 20261117)."""
import json
from datetime import datetime, timedelta
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.agent.tools import Ctx, ToolError
from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_gcal import ME, _connect, _dt, _today, run
from tests.test_life import conv_ctx
from tests.test_v0999_189_calendar_complete import Full as Full189, _ev

NOTIFY = {"eventCreation", "eventChange", "eventCancellation", "eventResponse", "agenda"}
WEEK = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
ROOM = "c_room-akola@resource.calendar.google.com"


class Full(Full189):
    def __init__(self):
        super().__init__()
        self.lists = {"L1": {"id": "L1", "title": "My Tasks"}}
        self.tasks = {"L1": {}}
        self.transfers = []
        self.admin = False

    def _check_event(self, body, params):
        super()._check_event(body, params)
        if body.get("eventType") == "birthday":
            assert set(body["start"]) == {"date"} and body["recurrence"] == ["RRULE:FREQ=YEARLY"]
            assert body["visibility"] == "private" and body["transparency"] == "transparent"
            assert body["birthdayProperties"] == {"type": "birthday"}
        for k in ("start", "end"):
            if "dateTime" in body.get(k, {}):
                ZoneInfo(body[k]["timeZone"])
                assert datetime.fromisoformat(body[k]["dateTime"]).utcoffset() == \
                    datetime.fromisoformat(body[k]["dateTime"]).replace(tzinfo=None).replace(
                        tzinfo=ZoneInfo(body[k]["timeZone"])).utcoffset()
        for a in body.get("attendees") or []:
            if a.get("resource"):
                assert a["email"].endswith("@resource.calendar.google.com") or "@" in a["email"]

    def __call__(self, req: httpx.Request):
        url, m = req.url, req.method
        try:
            body = json.loads(req.content) if req.content else {}
        except ValueError:
            body = {}                       # the form-encoded sign-in request
        if url.host == "tasks.googleapis.com":
            assert req.headers["authorization"] == "Bearer at"
            p = url.path.removeprefix("/tasks/v1")
            if p == "/users/@me/lists":
                if m == "GET":
                    return httpx.Response(200, json={"items": list(self.lists.values())})
                lid = f"L{len(self.lists) + 1}"
                self.lists[lid] = {"id": lid, "title": body["title"]}
                self.tasks[lid] = {}
                return httpx.Response(200, json=self.lists[lid])
            if p.startswith("/users/@me/lists/"):
                lid = unquote(p.rsplit("/", 1)[1])
                if m == "PATCH":
                    self.lists[lid].update(body)
                    return httpx.Response(200, json=self.lists[lid])
                if m == "DELETE":
                    del self.lists[lid]
                    return httpx.Response(204)
            parts = p.split("/")             # /lists/<id>/tasks[/<task>[/move]] or /lists/<id>/clear
            lid = unquote(parts[2])
            ts = self.tasks.setdefault(lid, {})
            if parts[3] == "clear":
                for t in ts.values():
                    if t["status"] == "completed":
                        t["hidden"] = True
                return httpx.Response(204)
            if len(parts) == 4 and m == "GET":
                items = [t for t in ts.values() if url.params.get("showCompleted") == "true" or t["status"] != "completed"]
                items = [t for t in items if url.params.get("showHidden") == "true" or not t.get("hidden")]
                return httpx.Response(200, json={"items": items})
            if len(parts) == 4 and m == "POST":
                assert len(body["title"]) <= 1024
                if "due" in body:
                    assert body["due"].endswith("T00:00:00.000Z"), body["due"]
                tid = f"t{len(ts) + 1}"
                ts[tid] = {"id": tid, "status": "needsAction", **body, "position": f"{len(ts):020d}"}
                if url.params.get("parent"):
                    ts[tid]["parent"] = url.params["parent"]
                return httpx.Response(200, json=ts[tid])
            tid = unquote(parts[4])
            if len(parts) == 6 and parts[5] == "move":
                t = ts.pop(tid)
                dest = url.params.get("destinationTasklist", lid)
                if url.params.get("parent"):
                    t["parent"] = url.params["parent"]
                self.tasks.setdefault(dest, {})[tid] = t
                return httpx.Response(200, json=t)
            if m == "PATCH":
                assert body.get("status", "needsAction") in ("needsAction", "completed")
                ts[tid].update({k: v for k, v in body.items() if v is not None})
                if body.get("status") == "completed":
                    ts[tid]["completed"] = "2026-11-25T10:00:00.000Z"
                if body.get("completed", 1) is None:
                    ts[tid].pop("completed", None)
                return httpx.Response(200, json=ts[tid])
            if m == "DELETE":
                del ts[tid]
                return httpx.Response(204)
        p = url.path.removeprefix("/calendar/v3")
        if p.endswith("/transferOwnership"):
            assert url.params["useAdminAccess"] == "true" and url.params["newDataOwner"]
            if not self.admin:
                return httpx.Response(403, json={"error": {"message": "Not authorized to access this resource/api"}})
            self.transfers.append((unquote(p.split("/")[2]), url.params["newDataOwner"]))
            return httpx.Response(200, json={})
        if p.startswith("/users/me/calendarList/") and m == "PATCH":
            for r in body.get("defaultReminders", []):
                assert r["method"] in ("popup", "email") and 0 <= r["minutes"] <= 40320
            for n in (body.get("notificationSettings") or {}).get("notifications", []):
                assert n == {"type": n["type"], "method": "email"} and n["type"] in NOTIFY
        if p.startswith("/calendars/") and p.count("/") == 2 and m == "PATCH" and "workingHours" in body:
            wh = body["workingHours"]
            if wh.get("workingHoursEnabled"):
                assert wh["availableTimes"]
            for t in wh.get("availableTimes", []):
                assert t["dayOfWeek"] in WEEK and 0 <= t["periodStart"] < t["periodEnd"] <= 1440
        return super().__call__(req)


@pytest.fixture
def gm(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.cal import service as cs
    from app.cal.google import GoogleCal
    from app.mailbox import accounts as ma
    monkeypatch.setattr(GoogleCal, "RETRY_WAIT", 0.0)
    cs._cal_cache.clear()
    fake = Full()
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    _connect()
    yield fake
    ma.set_http(None)


def test_scopes_ask_for_google_tasks():
    from app.cal.accounts import SCOPES
    assert "https://www.googleapis.com/auth/tasks" in SCOPES


def test_default_reminders_notifications_and_working_hours(gm):
    ctx = conv_ctx()
    out = run("calendar_calendars", {"action": "default_reminders", "reminders": [10], "email_reminders": [60]}, ctx)
    assert out["default_reminders"] == ["10 min popup", "60 min email"]
    assert gm.cals["primary"]["defaultReminders"] == [{"method": "popup", "minutes": 10},
                                                      {"method": "email", "minutes": 60}]
    run("calendar_calendars", {"action": "notifications", "notify": ["new", "cancelled", "daily agenda"]}, ctx)
    assert [n["type"] for n in gm.cals["primary"]["notificationSettings"]["notifications"]] == \
        ["eventCreation", "eventCancellation", "agenda"]
    with pytest.raises(ToolError, match="notify"):
        run("calendar_calendars", {"action": "notifications", "notify": ["sms"]}, ctx)
    run("calendar_calendars", {"action": "working_hours", "hours": [
        {"days": ["mon", "tue", "wed", "thu", "fri"], "from": "09:30", "to": "18:00"},
        {"days": ["saturday"], "from": "10:00", "to": "13:00"}]}, ctx)
    wh = gm.cal_meta[ME]["workingHours"]
    assert len(wh["availableTimes"]) == 6 and wh["availableTimes"][0] == {"dayOfWeek": "monday", "periodStart": 570,
                                                                          "periodEnd": 1080}
    read = run("calendar_calendars", {"action": "working_hours"}, ctx)
    assert read["working_hours"][5] == {"day": "saturday", "from": "10:00", "to": "13:00"} and read["on"]
    run("calendar_calendars", {"action": "working_hours", "off": True}, ctx)
    assert gm.cal_meta[ME]["workingHours"] == {"workingHoursEnabled": False, "availableTimes": []}


def test_event_in_another_time_zone(gm):
    ctx = conv_ctx()
    d = (datetime.now(ZoneInfo("Europe/London")) + timedelta(days=3)).date()
    out = run("calendar_add_event", {"title": "Call with London office", "start": f"{d.isoformat()}T15:00",
                                     "time_zone": "London"}, ctx)
    _cal, e = _ev(gm, "Call with London office")
    assert e["start"]["timeZone"] == "Europe/London" and e["start"]["dateTime"].startswith(f"{d.isoformat()}T15:00")
    v = out["event"]
    assert v["time_zone"] == "Europe/London" and v["start_there"].endswith("03:00 PM")
    with pytest.raises(ToolError, match="not a time zone"):
        run("calendar_add_event", {"title": "x", "start": f"{d.isoformat()}T15:00", "time_zone": "Atlantis"}, ctx)


def test_meeting_rooms_seen_free_and_booked(gm):
    ctx = conv_ctx()
    past = _today(10, days=-5)
    gm.add(ME, {"summary": "Old review", "start": _dt(past), "end": _dt(past + timedelta(hours=1)),
                "attendees": [{"email": ME, "self": True}, {"email": ROOM, "displayName": "Akola - Board room",
                                                              "resource": True}]})
    rooms = run("calendar_rooms", {"action": "list"}, ctx)["rooms"]
    assert rooms == [{"email": ROOM, "name": "Akola - Board room"}]
    s = _today(11, days=2)
    gm.people_busy[ROOM] = [{"start": s.isoformat(), "end": (s + timedelta(hours=1)).isoformat()}]
    free = run("calendar_rooms", {"action": "free", "rooms": ["board"], "start": s.strftime("%Y-%m-%dT%H:%M")}, ctx)
    assert free["busy"] == ["Akola - Board room"]
    with pytest.raises(ToolError, match="Booked already"):
        run("calendar_add_event", {"title": "Planning", "start": s.strftime("%Y-%m-%dT%H:%M"), "rooms": ["board"]}, ctx)
    later = s + timedelta(hours=3)
    out = run("calendar_add_event", {"title": "Planning", "start": later.strftime("%Y-%m-%dT%H:%M"),
                                     "rooms": ["board"]}, ctx)
    assert out["added"] and out["event"]["rooms"] == [{"name": ROOM, "response": ""}]
    _cal, e = _ev(gm, "Planning")
    assert {"email": ROOM, "resource": True} in e["attendees"]
    with pytest.raises(ToolError, match="Which room"):
        run("calendar_add_event", {"title": "x", "start": later.strftime("%Y-%m-%dT%H:%M"), "rooms": ["moon base"]}, ctx)


def test_birthdays_and_anniversaries(gm):
    ctx = conv_ctx()
    b = run("calendar_birthday", {"name": "Swati", "date": "1994-08-15", "reminders": [1440]}, ctx)
    assert b["added"] == "Swati's birthday" and "Google's own birthday" in b["note"]
    _cal, e = _ev(gm, "Swati's birthday")
    assert e["eventType"] == "birthday" and e["recurrence"] == ["RRULE:FREQ=YEARLY"]
    a = run("calendar_birthday", {"name": "Wedding", "date": "2018-02-10", "kind": "anniversary"}, ctx)
    _cal, w = _ev(gm, "Wedding - anniversary")
    assert "eventType" not in w and w["recurrence"] == ["RRULE:FREQ=YEARLY"] and "only birthdays" in a["note"]


def test_transfer_needs_a_workspace_admin(bz, gm):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    run("calendar_calendars", {"action": "transfer", "calendar": "Family", "new_owner": "ravi@fnw.in"}, ctx)
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Give the calendar to another owner?" and "Workspace administrator" in json.dumps(card)
    bz["svc"].decide("default", card["id"], "approve")
    assert gm.transfers == []                           # Google refused: not an administrator - said, nothing changed
    with pytest.raises(ToolError, match="main calendar cannot be given away"):
        run("calendar_calendars", {"action": "transfer", "calendar": ME, "new_owner": "ravi@fnw.in"}, ctx)
    gm.admin = True
    run("calendar_calendars", {"action": "transfer", "calendar": "Family", "new_owner": "ravi@fnw.in"}, ctx)
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert gm.transfers == [("family@group.calendar.google.com", "ravi@fnw.in")]


def test_chat_file_goes_to_drive_then_on_the_event(gm, monkeypatch):
    ctx = conv_ctx()
    from app.mailbox import service as ms
    fid = ms.store_bytes("default", "Agenda.pdf", b"%PDF-1.4 agenda", "to_phone").id

    class Drive:
        address = ME
        uploaded = []

        def upload(self, name, mime, data):
            self.uploaded.append((name, mime, data))
            return {"id": "1DriveFileId0000000000000000000000"}
    drv = Drive()
    import app.drive.accounts as da
    monkeypatch.setattr(da, "clients", lambda tenant: [drv])
    out = run("calendar_add_event", {"title": "Board meeting", "start": _today(10, days=4).strftime("%Y-%m-%dT%H:%M"),
                                     "chat_files": [fid]}, ctx)
    assert drv.uploaded == [("Agenda.pdf", "application/pdf", b"%PDF-1.4 agenda")]
    assert out["event"]["attachments"] == [{"title": "Agenda.pdf",
                                            "link": "https://drive.google.com/open?id=1DriveFileId0000000000000000000000"}]
    monkeypatch.setattr(da, "clients", lambda tenant: [])
    with pytest.raises(ToolError, match="Google Drive must be connected"):
        run("calendar_add_event", {"title": "x", "start": _today(10, days=4).strftime("%Y-%m-%dT%H:%M"),
                                   "chat_files": [fid]}, ctx)


def test_google_tasks(bz, gm):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    run("google_tasks", {"action": "add", "title": "File GST return", "due": "2026-12-20T15:00", "notes": "GSTR-3B"}, ctx)
    out = run("google_tasks", {"action": "add", "title": "Collect invoices", "under": "File GST return"}, ctx)
    assert out["added"]["under"] == "t1"
    lst = run("google_tasks", {"action": "list"}, ctx)
    assert lst["list"] == "My Tasks" and [t["title"] for t in lst["tasks"]] == ["File GST return", "Collect invoices"]
    assert lst["tasks"][0]["due"] == "2026-12-20"
    run("google_tasks", {"action": "done", "task": "collect"}, ctx)
    assert run("google_tasks", {"action": "list"}, ctx)["count"] == 1
    assert run("google_tasks", {"action": "list", "show_completed": True}, ctx)["count"] == 2
    run("google_tasks", {"action": "reopen", "task": "Collect invoices"}, ctx)
    assert "completed" not in gm.tasks["L1"]["t2"]
    run("google_tasks", {"action": "new_list", "name": "Office"}, ctx)
    run("google_tasks", {"action": "move", "task": "File GST return", "to_list": "Office"}, ctx)
    assert "t1" in gm.tasks["L2"]
    run("google_tasks", {"action": "delete", "task": "Collect invoices"}, ctx)
    assert "t2" in gm.tasks["L1"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Delete the task?"
    bz["svc"].decide("default", card["id"], "approve")
    assert "t2" not in gm.tasks["L1"]
    run("google_tasks", {"action": "delete_list", "task_list": "Office"}, ctx)
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert "L2" not in gm.lists
    with pytest.raises(ToolError, match="No task list 'Home'"):
        run("google_tasks", {"action": "list", "task_list": "Home"}, ctx)


def test_tool_count():
    from app.agent.gcal_tools import GCAL_TOOLS
    assert len(GCAL_TOOLS) == 18
