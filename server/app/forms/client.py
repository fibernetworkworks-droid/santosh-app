"""Google Forms API v1 (+ Drive v3 for finding forms by name and sharing), over plain HTTPS with a bearer token."""
from __future__ import annotations

import re
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

    def _req(self, method: str, url: str, **kw) -> Any:
        c = self._client or httpx.Client(timeout=40)
        try:
            for attempt in (0, 1):
                r = c.request(method, url, headers={"Authorization": f"Bearer {self._token(attempt == 1)}"}, **kw)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise FormError(f"Google Forms se baat nahi ho payi ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 403:
            if "has not been used" in r.text or "SERVICE_DISABLED" in r.text:
                raise FormError("Google Cloud project mein Google Forms API enable nahi hai.")
            raise FormError("Is form ki permission nahi hai (shayad kisi aur ka form hai). Ya Profile > Google Forms se "
                            "dobara jodiye.")
        if r.status_code == 404:
            raise FormError("Yeh form nahi mila. Edit link ya naam sahi hai?")
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

    def batch(self, form_id: str, requests: list[dict]) -> dict:
        return self._req("POST", f"{FORMS}/{form_id}:batchUpdate",
                         json={"requests": requests, "includeFormInResponse": True})

    def publish(self, form_id: str, accepting: bool) -> dict:
        return self._req("POST", f"{FORMS}/{form_id}:setPublishSettings", json={
            "publishSettings": {"publishState": {"isPublished": True, "isAcceptingResponses": bool(accepting)}},
            "updateMask": "publishState"})

    def responses(self, form_id: str, since: str | None = None, limit: int = 5000) -> list[dict]:
        out: list[dict] = []
        token = None
        while True:
            params: dict[str, Any] = {"pageSize": 5000}
            if token:
                params["pageToken"] = token
            if since:
                params["filter"] = f"timestamp > {since}"
            res = self._req("GET", f"{FORMS}/{form_id}/responses", params=params)
            out += res.get("responses", [])
            token = res.get("nextPageToken")
            if not token or len(out) >= limit:
                return out[:limit]

    # ---------------- Drive ----------------
    def search(self, query: str = "", limit: int = 15) -> list[dict[str, Any]]:
        if not self.can_search:
            raise FormError("Naam se dhoondhna is connection par nahi hota; form ka edit link dijiye.")
        q = [f"mimeType = '{GFORM}'", "trashed = false"]
        if query:
            q.append("name contains '" + query.replace("\\", " ").replace("'", " ") + "'")
        res = self._req("GET", DRIVE + "/files", params={
            "q": " and ".join(q), "orderBy": "modifiedTime desc", "pageSize": max(1, min(limit, 50)),
            "fields": "files(id,name,modifiedTime,webViewLink)", "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true"})
        return [{"id": f["id"], "title": f["name"], "modified": f.get("modifiedTime", "")[:10],
                 "edit_link": f.get("webViewLink") or edit_link(f["id"])} for f in res.get("files", [])]

    def share(self, form_id: str, email: str, role: str = "writer") -> dict:
        return self._req("POST", f"{DRIVE}/files/{form_id}/permissions",
                         params={"sendNotificationEmail": "true", "supportsAllDrives": "true"},
                         json={"type": "user", "role": role, "emailAddress": email})
