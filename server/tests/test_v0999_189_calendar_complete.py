"""v0.999.189 CALENDAR COMPLETE: her calendars, sharing, out of office / focus time / working location, repeating
series, a time for several people, .ics in and out, alerts on new invites, more event options, Google's speed limit.
The stand-in checks every request against Google's own Calendar API v3 shapes (its discovery document, revision
20261118)."""
import json
from datetime import datetime, timedelta
from urllib.parse import unquote

import httpx
import pytest

from app.agent.tools import Ctx, ToolError
from tests.test_bazar import _events, _notices, bz  # noqa: F401
from tests.test_gcal import ME, FakeGoogle, _connect, _dt, _today, run
from tests.test_life import conv_ctx

SEND = {"all", "externalOnly", "none"}
ROLES = {"none", "freeBusyReader", "reader", "writerWithoutPrivateAccess", "writer", "owner"}
TYPES = {"default", "outOfOffice", "focusTime", "workingLocation", "birthday"}
DECLINE = {"declineNone", "declineAllConflictingInvitations", "declineOnlyNewConflictingInvitations"}


class Full(FakeGoogle):
    def __init__(self):
        super().__init__()
        self.acl = {ME: [{"id": f"user:{ME}", "role": "owner", "scope": {"type": "user", "value": ME}},
                         {"id": "user:ravi@fnw.in", "role": "reader", "scope": {"type": "user", "value": "ravi@fnw.in"}}]}
        self.cal_meta = {ME: {"id": ME, "summary": ME, "timeZone": "Asia/Kolkata"}}
        self.busy = 0
        self.token_n = 0
        self.private = {"zara@other.com"}
        self.people_busy = {}

    def _check_event(self, body, params):
        assert body.get("eventType", "default") in TYPES
        if "sendUpdates" in params:
            assert params["sendUpdates"] in SEND
        if body.get("attachments"):
            assert params.get("supportsAttachments") == "true"
            assert all(a["fileUrl"].startswith("https://drive.google.com/") for a in body["attachments"])
        if "eventLabelId" in body:
            assert params.get("eventLabelVersion") == "1"
        for r in (body.get("reminders") or {}).get("overrides", []):
            assert r["method"] in ("popup", "email") and 0 <= r["minutes"] <= 40320
        assert len((body.get("reminders") or {}).get("overrides", [])) <= 5
        for r in body.get("recurrence") or []:
            assert r.startswith(("RRULE:", "EXDATE", "RDATE")), r
        if body.get("transparency"):
            assert body["transparency"] in ("opaque", "transparent")
        if body.get("visibility"):
            assert body["visibility"] in ("default", "public", "private", "confidential")
        for k in ("outOfOfficeProperties", "focusTimeProperties"):
            if k in body:
                assert body["autoDecline" if False else k]["autoDeclineMode"] in DECLINE
        if body.get("eventType") == "focusTime" and "chatStatus" in body["focusTimeProperties"]:
            assert body["focusTimeProperties"]["chatStatus"] in ("available", "doNotDisturb")
        if body.get("eventType") == "workingLocation":
            wl = body["workingLocationProperties"]
            assert wl["type"] in ("homeOffice", "officeLocation", "customLocation") and wl["type"] in wl

    def __call__(self, req: httpx.Request):
        if req.url.host in ("oauth2.googleapis.com", "openidconnect.googleapis.com"):
            return super().__call__(req)
        if self.busy:
            self.busy -= 1
            return httpx.Response(403, json={"error": {"errors": [{"reason": "rateLimitExceeded"}],
                                                       "message": "Rate Limit Exceeded"}})
        path, params = req.url.path, dict(req.url.params)
        p = path.removeprefix("/calendar/v3")
        body = json.loads(req.content) if req.content else {}
        m = req.method
        if p == "/users/me/calendarList" and m == "POST":
            cid = body["id"]
            if "#holiday@" in cid or cid.endswith("@group.calendar.google.com"):
                self.cals[cid] = {"id": cid, "summary": "Holidays" if "#holiday" in cid else cid,
                                  "accessRole": "reader", "selected": True}
                return httpx.Response(200, json=self.cals[cid])
            return httpx.Response(404, json={"error": {"message": "Not Found"}})
        if p.startswith("/users/me/calendarList/"):
            cid = unquote(p.rsplit("/", 1)[1])
            key = next(k for k, v in self.cals.items() if v["id"] == cid)
            if m == "PATCH":
                if "backgroundColor" in body:
                    assert params.get("colorRgbFormat") == "true"
                self.cals[key].update(body)
                return httpx.Response(200, json=self.cals[key])
            if m == "DELETE":
                del self.cals[key]
                return httpx.Response(204)
        if p == "/calendars" and m == "POST":
            cid = f"new{self.n}@group.calendar.google.com"
            self.n += 1
            self.cals[cid] = {"id": cid, "summary": body["summary"], "accessRole": "owner", "selected": True}
            self.cal_meta[cid] = {"id": cid, **body}
            return httpx.Response(200, json=self.cal_meta[cid])
        parts = p.split("/")
        if len(parts) >= 3 and parts[1] == "calendars":
            cal = unquote(parts[2])
            if len(parts) == 3:
                meta = self.cal_meta.setdefault(cal, {"id": cal})
                if m == "GET":
                    return httpx.Response(200, json=meta)
                if m == "PATCH":
                    if "labelProperties" in body:
                        for lab in body["labelProperties"]["eventLabels"]:
                            assert lab["backgroundColor"].startswith("#") and len(lab.get("name", "")) <= 50
                    meta.update(body)
                    return httpx.Response(200, json=meta)
                if m == "DELETE":
                    self.cals = {k: v for k, v in self.cals.items() if v["id"] != cal}
                    return httpx.Response(204)
            if len(parts) == 4 and parts[3] == "clear":
                self.events[cal] = {}
                return httpx.Response(204)
            if len(parts) >= 4 and parts[3] == "acl":
                rules = self.acl.setdefault(cal, [])
                if len(parts) == 4 and m == "GET":
                    return httpx.Response(200, json={"items": rules})
                if len(parts) == 4 and m == "POST":
                    assert body["role"] in ROLES and body["scope"]["type"] in ("default", "user", "group", "domain")
                    assert body["scope"]["type"] == "default" or body["scope"].get("value")
                    r = {"id": f"{body['scope']['type']}:{body['scope'].get('value', '')}", **body}
                    rules.append(r)
                    return httpx.Response(200, json=r)
                rid = unquote(parts[4])
                r = next(x for x in rules if x["id"] == rid)
                if m == "PATCH":
                    assert body["role"] in ROLES
                    r.update(body)
                    return httpx.Response(200, json=r)
                if m == "DELETE":
                    rules.remove(r)
                    return httpx.Response(204)
            if len(parts) == 4 and parts[3] == "events" and m == "GET" and ("syncToken" in params or "timeMin" not in params):
                assert "timeMin" not in params and "q" not in params and "orderBy" not in params
                self.token_n += 1
                items = list(self.events.get(cal, {}).values()) if "syncToken" in params else []
                if "syncToken" in params:
                    items = [e for e in items if e.get("_new")]
                    for e in items:
                        e.pop("_new", None)
                return httpx.Response(200, json={"items": items, "nextSyncToken": f"tok{self.token_n}"})
            if len(parts) == 5 and parts[3] == "events" and parts[4] == "import":
                assert body.get("iCalUID") and body["start"] and body["end"]
                e = self.add(cal, {k: v for k, v in body.items()})
                return httpx.Response(200, json=e)
            if len(parts) == 4 and parts[3] == "events" and m == "POST":
                self._check_event(body, params)
            if len(parts) == 5 and m == "PATCH":
                self._check_event(body, params)
            if len(parts) == 6 and parts[5] == "move":
                eid = unquote(parts[4])
                ev = self.events[cal].pop(eid)
                assert params["destination"] and params["sendUpdates"] in SEND
                self.events.setdefault(params["destination"], {})[eid] = ev
                return httpx.Response(200, json=ev)
            if len(parts) == 6 and parts[5] == "instances":
                master = self.events[cal][unquote(parts[4])]
                st = self._start(master)
                out = []
                for i in range(4):
                    s = st + timedelta(days=7 * i)
                    out.append({**{k: v for k, v in master.items() if k != "recurrence"},
                                "id": f"{master['id']}_{i}", "recurringEventId": master["id"],
                                "start": _dt(s), "end": _dt(s + timedelta(hours=1)), "originalStartTime": _dt(s)})
                return httpx.Response(200, json={"items": out})
        if p == "/freeBusy":
            out = {}
            for it in body["items"]:
                if it["id"] in self.private:
                    out[it["id"]] = {"errors": [{"domain": "global", "reason": "notFound"}], "busy": []}
                elif it["id"] in self.people_busy:          # like Google: only busy times inside the asked window
                    t0 = datetime.fromisoformat(body["timeMin"].replace("Z", "+00:00"))
                    t1 = datetime.fromisoformat(body["timeMax"].replace("Z", "+00:00"))
                    out[it["id"]] = {"busy": [b for b in self.people_busy[it["id"]]
                                              if datetime.fromisoformat(b["start"]) < t1
                                              and datetime.fromisoformat(b["end"]) > t0]}
                else:
                    busy = [{"start": e["start"]["dateTime"], "end": e["end"]["dateTime"]}
                            for e in self.events.get(it["id"], {}).values() if "dateTime" in e["start"]]
                    out[it["id"]] = {"busy": busy}
            return httpx.Response(200, json={"calendars": out})
        if p == "/users/me/settings":
            return httpx.Response(200, json={"items": [{"id": "timezone", "value": "Asia/Kolkata"},
                                                       {"id": "weekStart", "value": "1"}]})
        return super().__call__(req)


@pytest.fixture
def gc(env, monkeypatch):
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


def _ev(fake, title):
    for cal, evs in fake.events.items():
        for e in evs.values():
            if e.get("summary") == title:
                return cal, e
    raise KeyError(title)


def test_more_event_options_in_googles_shapes(gc):
    ctx = conv_ctx()
    s = _today(15, days=1)
    out = run("calendar_add_event", {
        "title": "Budget review", "start": s.strftime("%Y-%m-%dT%H:%M"), "color": "tomato", "visibility": "private",
        "show_as": "free", "reminders": [10], "email_reminders": [1440],
        "attachments": ["https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/view"],
        "repeat": {"freq": "monthly", "nth": 1, "days": ["monday"]}}, ctx)
    ev = out["event"]
    assert ev["color"] == "tomato" and ev["visibility"] == "private" and ev["show_as"] == "free"
    assert ev["repeat_rule"] == "FREQ=MONTHLY;BYDAY=1MO" and "1440 min email" in ev["reminders"]
    assert ev["attachments"][0]["link"] == "https://drive.google.com/open?id=1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
    with pytest.raises(ToolError, match="Google Calendar's event colours"):
        run("calendar_add_event", {"title": "x", "start": s.strftime("%Y-%m-%dT%H:%M"), "color": "rainbow"}, ctx)
    with pytest.raises(ToolError, match="nth"):
        run("calendar_add_event", {"title": "x", "start": s.strftime("%Y-%m-%dT%H:%M"),
                                   "repeat": {"freq": "weekly", "nth": 1, "days": ["MO"]}}, ctx)
    with pytest.raises(ToolError, match="Drive file"):
        run("calendar_add_event", {"title": "x", "start": s.strftime("%Y-%m-%dT%H:%M"), "attachments": ["report.pdf"]}, ctx)
    # move to another of her calendars (private event: at once)
    moved = run("calendar_update_event", {"event_id": ev["id"], "move_to": "Family"}, ctx)
    assert _ev(gc, "Budget review")[0] == "family@group.calendar.google.com" and moved["updated"]


def test_calendars_create_rename_holidays_labels_and_cards(bz, gc):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    made = run("calendar_calendars", {"action": "create", "name": "Clients", "color": "#0b8043"}, ctx)
    assert made["created"] == "Clients" and gc.cal_meta[made["id"]]["timeZone"]
    run("calendar_calendars", {"action": "describe", "calendar": "Clients", "description": "Client visits"}, ctx)
    assert gc.cal_meta[made["id"]]["description"] == "Client visits"
    hol = run("calendar_calendars", {"action": "holidays", "country": "UAE"}, ctx)
    assert hol["id"] == "en.ae#holiday@group.v.calendar.google.com"
    with pytest.raises(ToolError, match="Which country"):
        run("calendar_calendars", {"action": "holidays", "country": "Atlantis"}, ctx)
    lab = run("calendar_calendars", {"action": "add_label", "calendar": "Clients", "label": "Site visit",
                                     "label_color": "#ff8800"}, ctx)
    assert lab["labels"][0]["name"] == "Site visit"
    s = _today(11, days=2).strftime("%Y-%m-%dT%H:%M")
    ev = run("calendar_add_event", {"title": "Akola site", "start": s, "calendar": "Clients", "label": "Site visit"},
             ctx)["event"]
    assert ev["label_id"] == lab["labels"][0]["id"]
    with pytest.raises(ToolError, match="Google does not delete a main calendar"):
        run("calendar_calendars", {"action": "delete", "calendar": ME}, ctx)
    out = run("calendar_calendars", {"action": "delete", "calendar": "Clients"}, ctx)
    assert out["status"] == "needs_approval" and made["id"] in [c["id"] for c in gc.cals.values()]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Delete the whole calendar?"
    bz["svc"].decide("default", card["id"], "approve")
    assert made["id"] not in [c["id"] for c in gc.cals.values()]


def test_share_list_add_change_remove_public(bz, gc):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    lst = run("calendar_share", {"action": "list"}, ctx)
    assert {p["who"] for p in lst["people"]} == {ME, "ravi@fnw.in"}
    from app.mailbox import contacts
    contacts.learn("default", [("Swati Sirsath", "swati@fnw.in")], 1.0, sent=True)
    run("calendar_share", {"action": "add", "people": ["Swati"], "role": "free_busy"}, ctx)
    assert len(gc.acl[ME]) == 2
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert gc.acl[ME][-1] == {"id": "user:swati@fnw.in", "role": "freeBusyReader",
                              "scope": {"type": "user", "value": "swati@fnw.in"}}
    run("calendar_share", {"action": "change", "people": ["ravi"], "role": "edit"}, ctx)
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert next(r for r in gc.acl[ME] if r["id"] == "user:ravi@fnw.in")["role"] == "writer"
    with pytest.raises(ToolError, match="never edit"):
        run("calendar_share", {"action": "public", "role": "edit"}, ctx)
    run("calendar_share", {"action": "public", "role": "free_busy"}, ctx)
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Make the calendar public?"
    bz["svc"].decide("default", card["id"], "approve")
    assert gc.acl[ME][-1]["scope"] == {"type": "default"}
    run("calendar_share", {"action": "remove", "people": ["public"]}, ctx)
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert all(r["scope"]["type"] != "default" for r in gc.acl[ME])
    with pytest.raises(ToolError, match="Nobody like that"):
        run("calendar_share", {"action": "remove", "people": [ME]}, ctx)       # she is never removed from her own


def test_out_of_office_focus_and_working_location(gc):
    ctx = conv_ctx()
    d = _today(0, days=3)
    ooo = run("calendar_status", {"kind": "out_of_office", "start": d.strftime("%Y-%m-%d"),
                                  "end": (d + timedelta(days=1)).strftime("%Y-%m-%d"),
                                  "message": "On leave, back Monday", "decline": "all"}, ctx)
    _cal, e = _ev(gc, "Out of office")
    assert e["eventType"] == "outOfOffice" and e["outOfOfficeProperties"] == {
        "autoDeclineMode": "declineAllConflictingInvitations", "declineMessage": "On leave, back Monday"}
    assert "every one" in ooo["note"]
    run("calendar_status", {"kind": "focus_time", "start": _today(14, days=4).strftime("%Y-%m-%dT%H:%M"),
                            "end": _today(16, days=4).strftime("%Y-%m-%dT%H:%M"), "chat": "dnd"}, ctx)
    _cal, f = _ev(gc, "Focus time")
    assert f["focusTimeProperties"]["chatStatus"] == "doNotDisturb"
    run("calendar_status", {"kind": "working_location", "start": d.strftime("%Y-%m-%d"),
                            "end": d.strftime("%Y-%m-%d"), "where": "home"}, ctx)
    _cal, w = _ev(gc, "Working location")
    assert w["workingLocationProperties"] == {"type": "homeOffice", "homeOffice": {}} and "date" in w["start"]


def test_series_list_skip_end_and_change_following(bz, gc):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    s = _today(9, days=1)
    ev = run("calendar_add_event", {"title": "Weekly sync", "start": s.strftime("%Y-%m-%dT%H:%M"),
                                    "repeat": {"freq": "weekly", "days": ["MO"]}}, ctx)["event"]
    lst = run("calendar_series", {"event_id": ev["id"], "action": "list"}, ctx)
    assert lst["repeat_rule"] == "FREQ=WEEKLY;BYDAY=MO" and len(lst["next"]) == 4
    third = lst["next"][2]["id"]
    cal, master = _ev(gc, "Weekly sync")
    gc.events[cal][third.split("~")[-1]] = {**{k: v for k, v in master.items() if k != "recurrence"},
                                            "id": third.split("~")[-1], "recurringEventId": master["id"],
                                            "start": _dt(s + timedelta(days=14)), "end": _dt(s + timedelta(days=14, hours=1)),
                                            "originalStartTime": _dt(s + timedelta(days=14))}
    out = run("calendar_series", {"event_id": third, "action": "change_following", "title": "Weekly sync (new room)"}, ctx)
    assert "split" in out["done"]
    assert "UNTIL=" in master["recurrence"][0]
    _c2, new = _ev(gc, "Weekly sync (new room)")
    assert new["recurrence"] == ["RRULE:FREQ=WEEKLY;BYDAY=MO"]
    end = run("calendar_series", {"event_id": ev["id"], "action": "end", "until": s.date().isoformat()}, ctx)
    assert "changed" in end["done"]
    with pytest.raises(ToolError, match="does not repeat"):
        one = run("calendar_add_event", {"title": "Once", "start": s.strftime("%Y-%m-%dT%H:%M")}, ctx)["event"]
        run("calendar_series", {"event_id": one["id"], "action": "list"}, ctx)


def test_meeting_time_for_several_people(gc):
    ctx = conv_ctx()
    from app.mailbox import contacts
    contacts.learn("default", [("Ravi", "ravi@fnw.in"), ("Zara", "zara@other.com")], 1.0, sent=True)
    d = _today(9, days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    gc.people_busy["ravi@fnw.in"] = [{"start": d.isoformat(), "end": (d + timedelta(hours=4)).isoformat()}]
    out = run("calendar_meeting_time", {"people": ["Ravi", "Zara"], "from_date": d.date().isoformat(),
                                        "to_date": d.date().isoformat(), "minutes": 60}, ctx)
    assert out["could_not_see"] == ["zara@other.com"] and "private" in out["note"]
    assert out["free_for_everyone"][0]["start_iso"].startswith(d.date().isoformat() + "T13:00")


def test_ics_import_and_export(gc):
    ctx = conv_ctx()
    from app.mailbox import service as ms
    ics = (b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//x//EN\r\nBEGIN:VEVENT\r\nUID:conf-123@x\r\n"
           b"DTSTART:20261210T040000Z\r\nDTEND:20261210T050000Z\r\nSUMMARY:Tech conference\r\n"
           b"LOCATION:Pune\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    fid = ms.store_bytes("default", "conference.ics", ics, "to_phone").id
    out = run("calendar_ics", {"action": "import", "file_id": fid}, ctx)
    assert out["added"] == 1 and out["titles"] == ["Tech conference"]
    _cal, e = _ev(gc, "Tech conference")
    assert e["iCalUID"] == "conf-123@x" and e["location"] == "Pune"
    bad = ms.store_bytes("default", "notes.ics", b"hello", "to_phone").id
    with pytest.raises(ToolError, match="not a calendar"):
        run("calendar_ics", {"action": "import", "file_id": bad}, ctx)
    from app.cal import service as cs
    ref = cs.make_ref(cs.get_box("default"), ME, e["id"])
    exp = run("calendar_ics", {"action": "export", "event_id": ref}, ctx)
    assert exp["file"] == "Tech conference.ics" and exp["events"] == 1
    from app.mailbox.service import _file_row
    from pathlib import Path
    data = Path(_file_row("default", exp["file_id"]).stored_path).read_bytes()
    assert b"BEGIN:VEVENT" in data and b"UID:conf-123@x" in data


def test_watch_tells_about_new_invites_once(gc):
    ctx = conv_ctx()
    on = run("calendar_watch", {"action": "on", "kinds": "invites"}, ctx)
    assert on["watching"] == "invites"
    from app.cal import more
    assert more.watch_tick() == 0
    s = _today(17, days=2)
    gc.add(ME, {"summary": "Vendor demo", "start": _dt(s), "end": _dt(s + timedelta(hours=1)), "_new": True,
                "organizer": {"email": "vendor@acme.com"},
                "attendees": [{"email": ME, "self": True, "responseStatus": "needsAction"}]})
    assert more.watch_tick() == 1
    assert "New invite from vendor@acme.com: Vendor demo" in _notices(ctx.conversation_id)[-1]
    assert more.watch_tick() == 0
    assert run("calendar_watch", {"action": "list"}, ctx)["watching"][0]["kinds"] == "invites"
    run("calendar_watch", {"action": "off"}, ctx)
    assert run("calendar_watch", {"action": "list"}, ctx)["watching"][0]["on"] is False


def test_speed_limit_respond_comment_and_settings(gc):
    ctx = conv_ctx()
    gc.busy = 2
    assert run("calendar_agenda", {}, ctx)["count"] == 0 and gc.busy == 0
    gc.busy = 9
    with pytest.raises(ToolError, match="busy"):
        run("calendar_agenda", {}, ctx)
    gc.busy = 0
    s = _today(12, days=1)
    gc.add(ME, {"summary": "Board call", "start": _dt(s), "end": _dt(s + timedelta(hours=1)),
                "organizer": {"email": "chair@fnw.in"},
                "attendees": [{"email": ME, "self": True, "responseStatus": "needsAction"}, {"email": "chair@fnw.in"}]})
    ev = run("calendar_find_event", {"query": "Board call"}, ctx)["events"][0]
    run("calendar_respond", {"event_id": ev["id"], "response": "tentative", "comment": "May join late"}, ctx)
    me = next(a for a in _ev(gc, "Board call")[1]["attendees"] if a.get("self"))
    assert me["responseStatus"] == "tentative" and me["comment"] == "May join late"
    st = run("calendar_settings", {}, ctx)
    assert st["google_settings"][ME]["timezone"] == "Asia/Kolkata"


def test_tool_count():
    from app.agent.gcal_tools import GCAL_HANDLERS, GCAL_LABELS, GCAL_TOOLS
    assert len(GCAL_TOOLS) == 18 and set(GCAL_HANDLERS) == set(GCAL_LABELS) == {t["name"] for t in GCAL_TOOLS}
