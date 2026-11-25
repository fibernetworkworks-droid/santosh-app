"""Google Calendar through the official Calendar API v3 (OAuth scope: calendar)."""
from __future__ import annotations

import secrets
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote

import httpx

API = "https://www.googleapis.com/calendar/v3"


class CalError(Exception):
    pass


class NotConnected(CalError):
    pass


class GoneSync(CalError):
    """Google's sync token expired (410 fullSyncRequired): start the change list again."""


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

    RETRIES = 5
    RETRY_WAIT = 1.0
    RATE = ("rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded", "backendError", "Quota exceeded")

    def _req(self, method: str, path: str, **kw) -> Any:
        """v0.999.189: Google's speed limit (429, 5xx, a 403 that says rate limit) is waited out (Retry-After, else
        1-2-4-8-16 s, 5 tries); other refusals say what is really wrong."""
        c = self._client or httpx.Client(timeout=30)
        try:
            tries = 0
            while True:
                tries += 1
                for attempt in (0, 1):
                    r = c.request(method, API + path, headers={"Authorization": f"Bearer {self._token(attempt == 1)}"}, **kw)
                    if r.status_code == 401 and attempt == 0:
                        continue
                    break
                rate = r.status_code in (429, 500, 502, 503, 504) or (
                    r.status_code == 403 and any(w in r.text for w in self.RATE))
                if not rate or tries >= self.RETRIES:
                    break
                try:
                    wait = float(r.headers.get("retry-after") or 0)
                except ValueError:
                    wait = 0.0
                time.sleep(min(wait or self.RETRY_WAIT * 2 ** (tries - 1), 30))
        except httpx.HTTPError as e:
            raise CalError(f"Could not reach Google Calendar ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        t = r.text
        if r.status_code == 429 or r.status_code >= 500 or (r.status_code == 403 and any(w in t for w in self.RATE)):
            raise CalError("Google Calendar is busy (its speed limit for this account). Hoola waited and tried 5 times; "
                           "try again in a minute.")
        if r.status_code == 403:
            if "has not been used" in t or "SERVICE_DISABLED" in t:
                raise CalError("The Google Calendar API is not enabled in the Google Cloud project.")
            if "insufficient" in t.lower() and "scope" in t.lower():
                raise CalError("No calendar permission. Connect Google Calendar again (Connectors > Google > Calendar) "
                               "and tick every box on Google's page.")
            if "forbiddenForNonOrganizer" in t:
                raise CalError("Only the organizer can change this; you can reply to it (calendar_respond).")
            raise CalError("You can only look at this calendar, not change it (it belongs to someone else or is a "
                           "subscribed calendar).")
        if r.status_code == 409:
            raise CalError("That already exists in the calendar (same event id).")
        if r.status_code == 410 and "fullSyncRequired" in t:
            raise GoneSync("Google asks for a fresh start of the change list.")
        if r.status_code in (404, 410):
            raise CalError("This event or calendar was not found (it may have been deleted).")
        if r.status_code >= 400:
            msg = t[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            low = msg.lower()
            if any(w in low for w in ("outofoffice", "focustime", "workinglocation", "event type")):
                raise CalError(f"Google refused this kind of event here: {msg} (Out of office, focus time and working "
                               "location work only on the main calendar of a Google Workspace account.)")
            raise CalError(f"Google Calendar: {msg}")
        return r.json() if r.content else {}

    def _pages(self, path: str, params: dict, limit: int, key: str = "items") -> tuple[list[dict], dict]:
        out: list[dict] = []
        token, last = "", {}
        while len(out) < limit:
            p = {**params, "maxResults": min(250, limit - len(out))}
            if token:
                p["pageToken"] = token
            last = self._req("GET", path, params=p)
            out += last.get(key, [])
            token = last.get("nextPageToken", "")
            if not token:
                break
        return out[:limit], last

    # ---------------- calendars ----------------
    def calendars(self, hidden: bool = False) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"showHidden": "true"} if hidden else {}
        items, _ = self._pages("/users/me/calendarList", params, 1000)
        return [{"id": c["id"], "name": c.get("summaryOverride") or c.get("summary") or c["id"],
                 "primary": bool(c.get("primary")), "role": c.get("accessRole", ""), "color": c.get("backgroundColor", ""),
                 "selected": bool(c.get("selected", c.get("primary", False))), "timezone": c.get("timeZone", ""),
                 "hidden": bool(c.get("hidden")), "description": (c.get("description") or "")[:300]}
                for c in items]

    def calendar(self, cal_id: str) -> dict:
        return self._req("GET", f"/calendars/{_q(cal_id)}")

    def calendar_new(self, body: dict) -> dict:
        return self._req("POST", "/calendars", json=body)

    def calendar_patch(self, cal_id: str, body: dict) -> dict:
        return self._req("PATCH", f"/calendars/{_q(cal_id)}", json=body)

    def calendar_delete(self, cal_id: str) -> None:
        self._req("DELETE", f"/calendars/{_q(cal_id)}")

    def calendar_clear(self, cal_id: str) -> None:
        self._req("POST", f"/calendars/{_q(cal_id)}/clear")

    def list_add(self, cal_id: str, body: dict | None = None) -> dict:
        return self._req("POST", "/users/me/calendarList", params={"colorRgbFormat": "true"},
                         json={"id": cal_id, **(body or {})})

    def list_patch(self, cal_id: str, body: dict) -> dict:
        return self._req("PATCH", f"/users/me/calendarList/{_q(cal_id)}", params={"colorRgbFormat": "true"}, json=body)

    def list_remove(self, cal_id: str) -> None:
        self._req("DELETE", f"/users/me/calendarList/{_q(cal_id)}")

    def acl(self, cal_id: str) -> list[dict]:
        items, _ = self._pages(f"/calendars/{_q(cal_id)}/acl", {}, 500)
        return items

    def acl_add(self, cal_id: str, scope: dict, role: str, notify: bool = True) -> dict:
        return self._req("POST", f"/calendars/{_q(cal_id)}/acl", params={"sendNotifications": str(notify).lower()},
                         json={"scope": scope, "role": role})

    def acl_patch(self, cal_id: str, rule_id: str, role: str) -> dict:
        return self._req("PATCH", f"/calendars/{_q(cal_id)}/acl/{_q(rule_id)}", json={"role": role})

    def acl_delete(self, cal_id: str, rule_id: str) -> None:
        self._req("DELETE", f"/calendars/{_q(cal_id)}/acl/{_q(rule_id)}")

    def settings(self) -> dict[str, str]:
        items, _ = self._pages("/users/me/settings", {}, 250)
        return {i.get("id", ""): i.get("value", "") for i in items}

    # ---------------- events ----------------
    def events(self, cal_id: str, start: datetime, end: datetime, q: str | None = None, limit: int = 100,
               types: list[str] | None = None) -> list[dict]:
        params: dict[str, Any] = {"timeMin": rfc3339(start), "timeMax": rfc3339(end), "singleEvents": "true",
                                  "orderBy": "startTime"}
        if q:
            params["q"] = q
        if types:
            params["eventTypes"] = list(types)
        items, _ = self._pages(f"/calendars/{_q(cal_id)}/events", params, max(1, min(int(limit or 100), 2500)))
        return [e for e in items if e.get("status") != "cancelled"]

    def changes(self, cal_id: str, sync_token: str = "") -> tuple[list[dict], str]:
        """Everything that changed since the sync token (cancelled ones too). With no token: Google's first full read,
        only to collect a token (Google gives it on the last page), so nothing old is told as new."""
        params: dict[str, Any] = {"showDeleted": "true", "maxResults": 2500}
        if sync_token:
            params["syncToken"] = sync_token
        else:
            params["fields"] = "nextPageToken,nextSyncToken,items(id)"
        items: list[dict] = []
        for _ in range(40):
            res = self._req("GET", f"/calendars/{_q(cal_id)}/events", params=params)
            items += res.get("items", [])
            if res.get("nextSyncToken"):
                return ([] if not sync_token else items), res["nextSyncToken"]
            if not res.get("nextPageToken"):
                break
            params = {**params, "pageToken": res["nextPageToken"]}
        raise CalError("Google did not give a change token for this calendar (too many events to read).")

    def instances(self, cal_id: str, event_id: str, start: datetime | None = None, end: datetime | None = None,
                  limit: int = 100) -> list[dict]:
        params: dict[str, Any] = {}
        if start:
            params["timeMin"] = rfc3339(start)
        if end:
            params["timeMax"] = rfc3339(end)
        items, _ = self._pages(f"/calendars/{_q(cal_id)}/events/{_q(event_id)}/instances", params, limit)
        return [e for e in items if e.get("status") != "cancelled"]

    def get(self, cal_id: str, event_id: str) -> dict:
        return self._req("GET", f"/calendars/{_q(cal_id)}/events/{_q(event_id)}")

    @staticmethod
    def _write_params(body: dict, send_updates: str, meet: bool, label: bool = False) -> tuple[dict, dict]:
        params: dict[str, Any] = {"sendUpdates": send_updates}
        if meet:
            body = {**body, "conferenceData": {"createRequest": {"requestId": secrets.token_hex(8),
                                                                  "conferenceSolutionKey": {"type": "hangoutsMeet"}}}}
            params["conferenceDataVersion"] = 1
        if "attachments" in body:
            params["supportsAttachments"] = "true"
        if label or "eventLabelId" in body:
            params["eventLabelVersion"] = 1
        return body, params

    def create(self, cal_id: str, body: dict, send_updates: str = "none", meet: bool = False) -> dict:
        body, params = self._write_params(body, send_updates, meet)
        return self._req("POST", f"/calendars/{_q(cal_id)}/events", params=params, json=body)

    def patch(self, cal_id: str, event_id: str, body: dict, send_updates: str = "none", meet: bool = False) -> dict:
        body, params = self._write_params(body, send_updates, meet)
        return self._req("PATCH", f"/calendars/{_q(cal_id)}/events/{_q(event_id)}", params=params, json=body)

    def delete(self, cal_id: str, event_id: str, send_updates: str = "none") -> None:
        self._req("DELETE", f"/calendars/{_q(cal_id)}/events/{_q(event_id)}", params={"sendUpdates": send_updates})

    def move(self, cal_id: str, event_id: str, dest: str, send_updates: str = "none") -> dict:
        return self._req("POST", f"/calendars/{_q(cal_id)}/events/{_q(event_id)}/move",
                         params={"destination": dest, "sendUpdates": send_updates})

    def import_event(self, cal_id: str, body: dict) -> dict:
        return self._req("POST", f"/calendars/{_q(cal_id)}/events/import", json=body)

    def colors(self) -> dict:
        return self._req("GET", "/colors")

    def free_busy(self, ids: list[str], start: datetime, end: datetime) -> dict[str, dict]:
        out = self._req("POST", "/freeBusy", json={"timeMin": rfc3339(start), "timeMax": rfc3339(end),
                                                   "items": [{"id": c} for c in ids[:50]]})
        return out.get("calendars") or {}

    def busy(self, cal_ids: list[str], start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        """v0.999.189: a calendar Google could not read is no longer silently counted as free; its name is kept in
        busy_errors for the caller to say."""
        spans = []
        self.busy_errors = []
        for cid, cal in self.free_busy(cal_ids, start, end).items():
            if cal.get("errors"):
                self.busy_errors.append(cid)
            for b in cal.get("busy", []):
                spans.append((datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
                              datetime.fromisoformat(b["end"].replace("Z", "+00:00"))))
        return spans
