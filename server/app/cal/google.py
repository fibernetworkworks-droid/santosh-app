"""Google Calendar through the official Calendar API v3 (OAuth scope: calendar)."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote

import httpx

API = "https://www.googleapis.com/calendar/v3"


class CalError(Exception):
    pass


class NotConnected(CalError):
    pass


def _q(s: str) -> str:
    return quote(s, safe="")


def rfc3339(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class GoogleCal:
    kind = "google"

    def __init__(self, key: str, address: str, token: Callable[[bool], str], name: str = "",
                 client: httpx.Client | None = None) -> None:
        self.key = key
        self.address = (address or "").lower()
        self.name = name
        self._token = token
        self._client = client

    def _req(self, method: str, path: str, **kw) -> Any:
        c = self._client or httpx.Client(timeout=30)
        try:
            for attempt in (0, 1):
                r = c.request(method, API + path, headers={"Authorization": f"Bearer {self._token(attempt == 1)}"}, **kw)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise CalError(f"Google Calendar se baat nahi ho payi ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 403 and ("insufficient" in r.text.lower() or "scope" in r.text.lower()):
            raise CalError("Calendar ki permission nahi mili. App mein Profile > Calendar se Google Calendar dobara jodiye.")
        if r.status_code in (404, 410):
            raise CalError("Yeh event ya calendar nahi mila (shayad hata diya gaya).")
        if r.status_code >= 400:
            raise CalError(f"Google Calendar error {r.status_code}: {r.text[:200]}")
        return r.json() if r.content else {}

    # ---------------- calendars ----------------
    def calendars(self) -> list[dict[str, Any]]:
        items = self._req("GET", "/users/me/calendarList", params={"maxResults": 250}).get("items", [])
        return [{"id": c["id"], "name": c.get("summaryOverride") or c.get("summary") or c["id"],
                 "primary": bool(c.get("primary")), "role": c.get("accessRole", ""), "color": c.get("backgroundColor", ""),
                 "selected": bool(c.get("selected", c.get("primary", False))), "timezone": c.get("timeZone", "")}
                for c in items]

    # ---------------- events ----------------
    def events(self, cal_id: str, start: datetime, end: datetime, q: str | None = None, limit: int = 100) -> list[dict]:
        params: dict[str, Any] = {"timeMin": rfc3339(start), "timeMax": rfc3339(end), "singleEvents": "true",
                                  "orderBy": "startTime", "maxResults": max(1, min(limit, 250))}
        if q:
            params["q"] = q
        return [e for e in self._req("GET", f"/calendars/{_q(cal_id)}/events", params=params).get("items", [])
                if e.get("status") != "cancelled"]

    def get(self, cal_id: str, event_id: str) -> dict:
        return self._req("GET", f"/calendars/{_q(cal_id)}/events/{_q(event_id)}")

    def create(self, cal_id: str, body: dict, send_updates: str = "none", meet: bool = False) -> dict:
        params: dict[str, Any] = {"sendUpdates": send_updates}
        if meet:
            body = {**body, "conferenceData": {"createRequest": {"requestId": secrets.token_hex(8),
                                                                  "conferenceSolutionKey": {"type": "hangoutsMeet"}}}}
            params["conferenceDataVersion"] = 1
        return self._req("POST", f"/calendars/{_q(cal_id)}/events", params=params, json=body)

    def patch(self, cal_id: str, event_id: str, body: dict, send_updates: str = "none", meet: bool = False) -> dict:
        params: dict[str, Any] = {"sendUpdates": send_updates}
        if meet:
            body = {**body, "conferenceData": {"createRequest": {"requestId": secrets.token_hex(8),
                                                                  "conferenceSolutionKey": {"type": "hangoutsMeet"}}}}
            params["conferenceDataVersion"] = 1
        return self._req("PATCH", f"/calendars/{_q(cal_id)}/events/{_q(event_id)}", params=params, json=body)

    def delete(self, cal_id: str, event_id: str, send_updates: str = "none") -> None:
        self._req("DELETE", f"/calendars/{_q(cal_id)}/events/{_q(event_id)}", params={"sendUpdates": send_updates})

    def busy(self, cal_ids: list[str], start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        out = self._req("POST", "/freeBusy", json={"timeMin": rfc3339(start), "timeMax": rfc3339(end),
                                                   "items": [{"id": c} for c in cal_ids]})
        spans = []
        for cal in (out.get("calendars") or {}).values():
            for b in cal.get("busy", []):
                spans.append((datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
                              datetime.fromisoformat(b["end"].replace("Z", "+00:00"))))
        return spans
