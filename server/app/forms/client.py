"""Google Forms API v1 (+ Drive v3 for finding forms by name and sharing), over plain HTTPS with a bearer token."""
from __future__ import annotations

import re
import time
from typing import Any, Callable

import httpx

FORMS = "https://forms.googleapis.com/v1/forms"
DRIVE = "https://www.googleapis.com/drive/v3"
GFORM = "application/vnd.google-apps.form"


class FormError(Exception):
    pass


class NotConnected(FormError):
    pass


ID_RE = re.compile(r"/forms/d/(?:e/)?([a-zA-Z0-9_-]{20,})")


def id_from(text: str) -> str | None:
    """Form id from an edit link (docs.google.com/forms/d/<id>/edit) or a bare id. Responder links (/d/e/...) carry a
    different public id that the API can't open, so those are refused with a clear message by the caller."""
    t = (text or "").strip()
    if "/forms/d/e/" in t:
        return None
    m = ID_RE.search(t)
    if m:
        return m.group(1)
    return t if re.fullmatch(r"[a-zA-Z0-9_-]{30,}", t) else None


def edit_link(form_id: str) -> str:
    return f"https://docs.google.com/forms/d/{form_id}/edit"


class FormsClient:
    def __init__(self, key: str, address: str, token: Callable[[bool], str], client: httpx.Client | None = None,
                 can_search: bool = True) -> None:
        self.key = key
        self.address = (address or "").lower()
        self.kind = "google"
        self._token = token
        self._client = client
        self.can_search = can_search

    RETRIES = 5
    RETRY_WAIT = 1.0
    RATE = ("rateLimitExceeded", "userRateLimitExceeded", "RATE_LIMIT_EXCEEDED", "backendError", "Quota exceeded")

    def _req(self, method: str, url: str, **kw) -> Any:
        """v0.999.187: Google's speed limit (429, 5xx, a 403 that says rate limit) is waited out (Retry-After, else
        1-2-4-8-16 s, 5 tries) instead of told as "No permission"; other 403s say what is really missing."""
        c = self._client or httpx.Client(timeout=40)
        try:
            tries = 0
            while True:
                tries += 1
                for attempt in (0, 1):
                    r = c.request(method, url, headers={"Authorization": f"Bearer {self._token(attempt == 1)}"}, **kw)
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
            raise FormError(f"Could not reach Google Forms ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code in (429,) or (r.status_code >= 500) or (
                r.status_code == 403 and any(w in r.text for w in self.RATE)):
            raise FormError("Google Forms is busy (its speed limit for this account). Hoola waited and tried 5 times; "
                            "try again in a minute.")
        if r.status_code == 403:
            if "has not been used" in r.text or "SERVICE_DISABLED" in r.text:
                raise FormError("The Google Forms API is not enabled in the Google Cloud project.")
            if "insufficient" in r.text.lower() and "scope" in r.text.lower():
                raise FormError("Google Forms was connected without the permission this needs. Connect Forms again "
                                "(Connectors > Google) and tick every box on Google's page.")
            raise FormError("No permission for this form (it may be someone else's form). Or connect again from "
                            "Connectors > Google > Forms.")
        if r.status_code == 404:
            raise FormError("This form was not found. Is the edit link or name correct?")
        if r.status_code >= 400:
            msg = r.text[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise FormError(f"Google Forms: {msg}")
        return r.json() if r.content else {}

    # ---------------- forms ----------------
    def create(self, title: str) -> dict:
        return self._req("POST", FORMS, json={"info": {"title": title, "documentTitle": title}})

    def get(self, form_id: str) -> dict:
        return self._req("GET", f"{FORMS}/{form_id}")

    def batch(self, form_id: str, requests: list[dict], revision: str = "") -> dict:
        """revision = the form's revisionId the change was planned on: Google refuses the batch (400) if the form
        changed since (WriteControl.requiredRevisionId), so a card never edits a different form than she saw."""
        body: dict[str, Any] = {"requests": requests, "includeFormInResponse": True}
        if revision:
            body["writeControl"] = {"requiredRevisionId": revision}
        return self._req("POST", f"{FORMS}/{form_id}:batchUpdate", json=body)

    def publish(self, form_id: str, accepting: bool) -> dict:
        return self._req("POST", f"{FORMS}/{form_id}:setPublishSettings", json={
            "publishSettings": {"publishState": {"isPublished": True, "isAcceptingResponses": bool(accepting)}},
            "updateMask": "publishState"})

    def set_published(self, form_id: str, published: bool) -> dict:
        """v0.213: full publishState control — unpublish (isPublished=false) hides the form entirely; the old
        publish() above always keeps isPublished=true and only flips accepting."""
        return self._req("POST", f"{FORMS}/{form_id}:setPublishSettings", json={
            "publishSettings": {"publishState": {"isPublished": bool(published), "isAcceptingResponses": bool(published)}},
            "updateMask": "publishState"})

    def response_get(self, form_id: str, response_id: str) -> dict:
        """v0.213: forms.responses.get — one response by id."""
        return self._req("GET", f"{FORMS}/{form_id}/responses/{response_id}")

    def responses(self, form_id: str, since: str | None = None, limit: int = 100000, at_or_after: bool = False) -> list[dict]:
        out: list[dict] = []
        token = None
        while True:
            params: dict[str, Any] = {"pageSize": 5000}
            if token:
                params["pageToken"] = token
            if since:
                params["filter"] = f"timestamp {'>=' if at_or_after else '>'} {since}"
            res = self._req("GET", f"{FORMS}/{form_id}/responses", params=params)
            out += res.get("responses", [])
            token = res.get("nextPageToken")
            if not token or len(out) >= limit:
                return out[:limit]

    # ---------------- Drive ----------------
    def search(self, query: str = "", limit: int = 15) -> list[dict[str, Any]]:
        """v0.999.187: follows Drive's pages (was one page of up to 50)."""
        if not self.can_search:
            raise FormError("Search by name does not work on this connection; give the form's edit link.")
        q = [f"mimeType = '{GFORM}'", "trashed = false"]
        if query:
            q.append("name contains '" + query.replace("\\", " ").replace("'", " ") + "'")
        limit = max(1, min(int(limit or 15), 1000))
        out: list[dict[str, Any]] = []
        token = None
        while True:
            params: dict[str, Any] = {"q": " and ".join(q), "orderBy": "modifiedTime desc",
                                      "pageSize": min(limit - len(out), 100),
                                      "fields": "nextPageToken,files(id,name,modifiedTime,webViewLink)",
                                      "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
            if token:
                params["pageToken"] = token
            res = self._req("GET", DRIVE + "/files", params=params)
            out += [{"id": f["id"], "title": f["name"], "modified": f.get("modifiedTime", "")[:10],
                     "edit_link": f.get("webViewLink") or edit_link(f["id"])} for f in res.get("files", [])]
            token = res.get("nextPageToken")
            if not token or len(out) >= limit:
                return out[:limit]

    def permissions(self, form_id: str) -> list[dict]:
        """v0.999.187: who can edit / view the form itself (Drive permissions)."""
        res = self._req("GET", f"{DRIVE}/files/{form_id}/permissions", params={
            "supportsAllDrives": "true", "fields": "permissions(id,type,role,emailAddress,displayName,domain)"})
        return res.get("permissions", [])

    def unshare(self, form_id: str, permission_id: str) -> None:
        self._req("DELETE", f"{DRIVE}/files/{form_id}/permissions/{permission_id}", params={"supportsAllDrives": "true"})

    def share(self, form_id: str, email: str, role: str = "writer") -> dict:
        return self._req("POST", f"{DRIVE}/files/{form_id}/permissions",
                         params={"sendNotificationEmail": "true", "supportsAllDrives": "true"},
                         json={"type": "user", "role": role, "emailAddress": email})

    def trash(self, form_id: str) -> dict:
        """v0.213: Drive trash for a form (recoverable from Drive's Trash / Version history)."""
        return self._req("PATCH", f"{DRIVE}/files/{form_id}", params={"supportsAllDrives": "true"},
                         json={"trashed": True})

    def copy(self, form_id: str, new_title: str | None = None) -> dict:
        """v0.213: Drive files.copy — duplicate a form with its questions and settings."""
        body: dict[str, Any] = {"mimeType": GFORM}
        if new_title:
            body["name"] = new_title[:300]
        return self._req("POST", f"{DRIVE}/files/{form_id}/copy", params={"supportsAllDrives": "true"}, json=body)
