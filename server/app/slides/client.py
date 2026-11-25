"""Google Slides API v1 (+ Drive v3 to find, copy, export, import and share decks; Sheets v4 to list charts), over HTTPS
with a bearer token."""
from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

import httpx

SLIDES = "https://slides.googleapis.com/v1/presentations"
DRIVE = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
GSLIDES = "application/vnd.google-apps.presentation"
GSHEET = "application/vnd.google-apps.spreadsheet"
EXPORT = {"pdf": ("application/pdf", ".pdf"),
          "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
          "odp": ("application/vnd.oasis.opendocument.presentation", ".odp"),
          "txt": ("text/plain", ".txt")}
# what Google Drive turns into Google Slides on upload
IMPORTS = {".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
           ".ppt": "application/vnd.ms-powerpoint",
           ".odp": "application/vnd.oasis.opendocument.presentation",
           ".pptm": "application/vnd.ms-powerpoint.presentation.macroEnabled.12"}


class SlidesError(Exception):
    pass


class NotConnected(SlidesError):
    pass


ID_RE = re.compile(r"/presentation/d/([a-zA-Z0-9_-]{20,})")
SHEET_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]{20,})")


def id_from(text: str) -> str | None:
    m = ID_RE.search(text or "")
    if m:
        return m.group(1)
    t = (text or "").strip()
    return t if re.fullmatch(r"[a-zA-Z0-9_-]{30,}", t) else None


class SlidesClient:
    RETRIES = 5
    RETRY_WAIT = 1.0
    RATE = ("rateLimitExceeded", "userRateLimitExceeded", "RATE_LIMIT_EXCEEDED", "backendError", "Quota exceeded")

    def __init__(self, key: str, address: str, token: Callable[[bool], str], client: httpx.Client | None = None,
                 can_search: bool = True) -> None:
        self.key = key
        self.address = (address or "").lower()
        self._token = token
        self._client = client
        self.can_search = can_search

    def _req(self, method: str, url: str, raw: bool = False, **kw) -> Any:
        """v0.999.188: Google's speed limit (429, 5xx, a 403 that says rate limit) is waited out (Retry-After, else
        1-2-4-8-16 s, 5 tries) instead of told as "No permission"; other 403s say what is really missing."""
        c = self._client or httpx.Client(timeout=60)
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
            raise SlidesError(f"Could not reach Google Slides ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 429 or r.status_code >= 500 or (
                r.status_code == 403 and any(w in r.text for w in self.RATE)):
            raise SlidesError("Google Slides is busy (its speed limit for this account). Hoola waited and tried 5 times; "
                              "try again in a minute.")
        if r.status_code == 403:
            t = r.text
            if "has not been used" in t or "SERVICE_DISABLED" in t:
                raise SlidesError("The Slides / Drive / Sheets API is not enabled in the Google Cloud project.")
            if "exportSizeLimitExceeded" in t:
                raise SlidesError("This deck is too big for Google to export in one file (Google's limit is 10 MB). "
                                  "Export it from Google Slides itself (File > Download).")
            if "insufficient" in t.lower() and "scope" in t.lower():
                raise SlidesError("Google Slides was connected without the permission this needs. Connect Slides again "
                                  "(Connectors > Google > Slides) and tick every box on Google's page.")
            raise SlidesError("You do not have permission for this presentation (it may belong to someone else). Or "
                              "connect again from Connectors > Google > Slides.")
        if r.status_code == 404:
            raise SlidesError("This presentation was not found. Is the link / name right?")
        if r.status_code >= 400:
            msg = r.text[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise SlidesError(f"Google Slides: {msg}")
        if raw:
            return r.content
        return r.json() if r.content else {}

    # ---------------- finding ----------------
    def _files(self, q: list[str], limit: int, fields: str = "id,name,modifiedTime,webViewLink") -> list[dict]:
        out: list[dict] = []
        token = ""
        while len(out) < limit:
            params = {"q": " and ".join(q), "orderBy": "modifiedTime desc", "pageSize": min(100, limit - len(out)),
                      "fields": f"nextPageToken,files({fields})", "supportsAllDrives": "true",
                      "includeItemsFromAllDrives": "true"}
            if token:
                params["pageToken"] = token
            res = self._req("GET", DRIVE + "/files", params=params)
            out += res.get("files", [])
            token = res.get("nextPageToken", "")
            if not token:
                break
        return out[:limit]

    def search(self, query: str = "", limit: int = 15, mime: str = GSLIDES) -> list[dict[str, Any]]:
        if not self.can_search:
            raise SlidesError("Searching by name is not available on this connection. Please give the presentation link.")
        q = [f"mimeType = '{mime}'", "trashed = false"]
        if query:
            q.append("name contains '" + query.replace("\\", " ").replace("'", " ") + "'")
        files = self._files(q, max(1, min(int(limit or 15), 1000)))
        return [{"id": f["id"], "title": f["name"], "modified": f.get("modifiedTime", "")[:10], "link": f.get("webViewLink", "")}
                for f in files]

    # ---------------- the deck ----------------
    def get(self, pid: str, comments: bool = False) -> dict[str, Any]:
        params = {"commentsViewMode": "COMMENTS_VIEW_MODE_INCLUDED"} if comments else None
        return self._req("GET", f"{SLIDES}/{pid}", params=params)

    def create(self, title: str) -> dict[str, Any]:
        return self._req("POST", SLIDES, json={"title": title})

    def batch(self, pid: str, requests: list[dict], revision: str = "") -> dict[str, Any]:
        """revision = the deck's revisionId the change was planned on: Google refuses the batch if the deck changed
        since (WriteControl.requiredRevisionId), so a card never changes a different deck than she saw."""
        if not requests:
            return {}
        body: dict[str, Any] = {"requests": requests}
        if revision:
            body["writeControl"] = {"requiredRevisionId": revision}
        return self._req("POST", f"{SLIDES}/{pid}:batchUpdate", json=body)

    def thumbnail(self, pid: str, page_id: str, size: str = "MEDIUM") -> str:
        res = self._req("GET", f"{SLIDES}/{pid}/pages/{page_id}/thumbnail",
                        params={"thumbnailProperties.thumbnailSize": size, "thumbnailProperties.mimeType": "PNG"})
        return res.get("contentUrl", "")

    def fetch(self, url: str) -> bytes:
        """A thumbnail's contentUrl is a short-lived public link; it is read without her sign-in."""
        c = self._client or httpx.Client(timeout=60)
        try:
            r = c.get(url, follow_redirects=True)
        except httpx.HTTPError as e:
            raise SlidesError(f"Could not download the slide picture ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code >= 400:
            raise SlidesError("Google did not give the slide picture; try again.")
        return r.content

    # ---------------- Drive side ----------------
    def export(self, pid: str, fmt: str) -> bytes:
        mime = EXPORT[fmt][0]
        return self._req("GET", f"{DRIVE}/files/{pid}/export", raw=True, params={"mimeType": mime})

    def file(self, pid: str) -> dict:
        return self._req("GET", f"{DRIVE}/files/{pid}", params={"fields": "id,name,mimeType,owners(emailAddress),"
                                                                     "webViewLink,trashed", "supportsAllDrives": "true"})

    def copy(self, pid: str, name: str) -> dict:
        return self._req("POST", f"{DRIVE}/files/{pid}/copy", params={"supportsAllDrives": "true", "fields": "id,name"},
                         json={"name": name})

    def rename(self, pid: str, name: str) -> dict:
        return self._req("PATCH", f"{DRIVE}/files/{pid}", params={"supportsAllDrives": "true", "fields": "id,name"},
                         json={"name": name})

    def trash(self, pid: str) -> dict:
        return self._req("PATCH", f"{DRIVE}/files/{pid}", params={"supportsAllDrives": "true", "fields": "id,trashed"},
                         json={"trashed": True})

    def upload_convert(self, name: str, mime: str, data: bytes) -> dict:
        """Her PowerPoint / OpenDocument file uploaded and turned into Google Slides by Drive."""
        boundary = "hoola_slides_upload_boundary"
        meta = json.dumps({"name": name, "mimeType": GSLIDES})
        body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
                f"--{boundary}\r\nContent-Type: {mime}\r\n\r\n").encode() + data + f"\r\n--{boundary}--".encode()
        return self._upload(body, boundary)

    def _upload(self, body: bytes, boundary: str) -> dict:
        c = self._client or httpx.Client(timeout=300)
        try:
            for attempt in (0, 1):
                r = c.post(UPLOAD, params={"uploadType": "multipart", "supportsAllDrives": "true", "fields": "id,name"},
                           headers={"Authorization": f"Bearer {self._token(attempt == 1)}",
                                    "Content-Type": f"multipart/related; boundary={boundary}"}, content=body)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise SlidesError(f"Could not reach Google Drive ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code >= 400:
            msg = r.text[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise SlidesError(f"Google Drive could not turn the file into Google Slides: {msg}")
        return r.json()

    def permissions(self, pid: str) -> list[dict]:
        res = self._req("GET", f"{DRIVE}/files/{pid}/permissions", params={
            "supportsAllDrives": "true", "fields": "permissions(id,type,role,emailAddress,domain,displayName)"})
        return res.get("permissions", [])

    def share(self, pid: str, email: str, role: str, message: str = "") -> dict:
        params = {"sendNotificationEmail": "true", "supportsAllDrives": "true"}
        if message:
            params["emailMessage"] = message[:1000]
        return self._req("POST", f"{DRIVE}/files/{pid}/permissions", params=params,
                         json={"type": "user", "role": role, "emailAddress": email})

    def share_anyone(self, pid: str, role: str = "reader") -> dict:
        return self._req("POST", f"{DRIVE}/files/{pid}/permissions", params={"supportsAllDrives": "true"},
                         json={"type": "anyone", "role": role})

    def unshare(self, pid: str, perm_id: str) -> None:
        self._req("DELETE", f"{DRIVE}/files/{pid}/permissions/{perm_id}", params={"supportsAllDrives": "true"})

    # ---------------- Sheets side (charts) ----------------
    def charts(self, sheet_id: str) -> tuple[str, list[dict]]:
        res = self._req("GET", f"{SHEETS}/{sheet_id}", params={
            "fields": "properties(title),sheets(properties(title),charts(chartId,spec(title)))"})
        out = []
        for sh in res.get("sheets", []):
            for ch in sh.get("charts", []) or []:
                out.append({"chart_id": ch.get("chartId"), "title": ((ch.get("spec") or {}).get("title") or ""),
                            "tab": (sh.get("properties") or {}).get("title", "")})
        return (res.get("properties") or {}).get("title", ""), out
