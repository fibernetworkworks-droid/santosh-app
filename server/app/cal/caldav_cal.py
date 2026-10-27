"""The server owner's Google Calendar over CalDAV with the .env Gmail app password (the older route).
Shapes events like the Calendar API so the rest of Santosh doesn't care which route is used. Google Meet links,
editing and RSVP need the proper Google sign-in (Profile > Calendar)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .google import CalError

NEEDS_SIGNIN = ("Yeh kaam purane calendar connection (app password) par nahi hota. App mein Profile > Calendar se "
                "Google Calendar jodiye.")


def _when(v) -> dict:
    if isinstance(v, datetime):
        return {"dateTime": v.isoformat()}
    if isinstance(v, date):
        return {"date": v.isoformat()}
    return {}


class CaldavCal:
    kind = "caldav"

    def __init__(self, address: str) -> None:
        self.key = "env"
        self.address = address.lower()
        self.name = ""

    def _cal(self):
        from .. import gcal
        try:
            return gcal._primary(gcal._client())
        except gcal.CalError as e:
            raise CalError(str(e))

    @staticmethod
    def _shape(ev) -> dict[str, Any]:
        comp = ev.icalendar_component
        start = comp.get("dtstart").dt if comp.get("dtstart") else None
        end = comp.get("dtend").dt if comp.get("dtend") else None
        att = comp.get("attendee") or []
        if not isinstance(att, list):
            att = [att]
        return {"id": str(comp.get("uid") or ""), "summary": str(comp.get("summary") or "(no title)"),
                "start": _when(start), "end": _when(end or start), "location": str(comp.get("location") or ""),
                "description": str(comp.get("description") or ""),
                "attendees": [{"email": str(a).replace("mailto:", "")} for a in att], "status": "confirmed"}

    def calendars(self) -> list[dict[str, Any]]:
        return [{"id": "primary", "name": self.address, "primary": True, "role": "owner", "color": "", "selected": True,
                 "timezone": ""}]

    def events(self, cal_id, start, end, q=None, limit=100):
        from zoneinfo import ZoneInfo
        cal = self._cal()
        try:
            found = cal.search(start=start.astimezone(ZoneInfo("UTC")), end=end.astimezone(ZoneInfo("UTC")),
                               event=True, expand=True)
        except TypeError:
            found = cal.date_search(start, end)
        except Exception as e:
            raise CalError(f"Calendar padhne mein dikkat: {e}")
        out = []
        for ev in found:
            try:
                e = self._shape(ev)
            except Exception:
                continue
            if q and q.lower() not in (e["summary"] + " " + e["location"] + " " + e["description"]).lower():
                continue
            out.append(e)
        out.sort(key=lambda e: e["start"].get("dateTime") or e["start"].get("date") or "")
        return out[:limit]

    def get(self, cal_id, event_id):
        try:
            return self._shape(self._cal().event_by_uid(event_id))
        except CalError:
            raise
        except Exception:
            raise CalError("Yeh event nahi mila (shayad hata diya gaya).")

    def create(self, cal_id, body, send_updates="none", meet=False):
        from .. import gcal
        if meet or body.get("recurrence"):
            raise CalError(NEEDS_SIGNIN)
        s, e = body["start"], body["end"]
        if "date" in s:
            raise CalError(NEEDS_SIGNIN)
        start = datetime.fromisoformat(s["dateTime"])
        end = datetime.fromisoformat(e["dateTime"])
        try:
            v = gcal._create(body.get("summary", ""), start, end, body.get("location", ""), body.get("description", ""),
                             [a["email"] for a in body.get("attendees") or []])
        except gcal.CalError as ex:
            raise CalError(str(ex))
        return {"id": v["id"], "summary": v["title"], "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": end.isoformat()}, "location": v["location"], "attendees": body.get("attendees") or [],
                "status": "confirmed"}

    def patch(self, *a, **kw):
        raise CalError(NEEDS_SIGNIN)

    def delete(self, cal_id, event_id, send_updates="none"):
        from .. import gcal
        try:
            gcal._cancel(event_id)
        except gcal.CalError as e:
            raise CalError(str(e))

    def busy(self, cal_ids, start, end):
        spans = []
        for e in self.events("primary", start, end):
            s, en = e["start"].get("dateTime"), e["end"].get("dateTime")
            if s and en:     # all-day items (birthdays, holidays) don't block time
                spans.append((datetime.fromisoformat(s), datetime.fromisoformat(en)))
        return spans
