"""Google Slides API v1 (+ Drive v3 to find, export and share decks), over HTTPS with a bearer token."""
from __future__ import annotations

import re
from typing import Any, Callable

import httpx

SLIDES = "https://slides.googleapis.com/v1/presentations"
DRIVE = "https://www.googleapis.com/drive/v3"
GSLIDES = "application/vnd.google-apps.presentation"
EXPORT = {"pdf": ("application/pdf", ".pdf"),
          "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx")}


class SlidesError(Exception):
    pass


class NotConnected(SlidesError):
    pass


ID_RE = re.compile(r"/presentation/d/([a-zA-Z0-9_-]{20,})")


def id_from(text: str) -> str | None:
    m = ID_RE.search(text or "")
    if m:
        return m.group(1)
    t = (text or "").strip()
    return t if re.fullmatch(r"[a-zA-Z0-9_-]{30,}", t) else None


class SlidesClient:
    def __init__(self, key: str, address: str, token: Callable[[bool], str], client: httpx.Client | None = None,
                 can_search: bool = True) -> None:
        self.key = key
        self.address = (address or "").lower()
        self._token = token
        self._client = client
        self.can_search = can_search

    def _req(self, method: str, url: str, raw: bool = False, **kw) -> Any:
        c = self._client or httpx.Client(timeout=60)
        try:
            for attempt in (0, 1):
                r = c.request(method, url, headers={"Authorization": f"Bearer {self._token(attempt == 1)}"}, **kw)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise SlidesError(f"Google Slides se baat nahi ho payi ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 403:
            if "has not been used" in r.text or "SERVICE_DISABLED" in r.text:
                raise SlidesError("Google Cloud project mein Slides / Drive API enable nahi hai.")
            raise SlidesError("Is presentation ki permission nahi hai (kisi aur ki ho sakti hai). Ya Profile > Google "
                              "Slides se dobara jodiye.")
        if r.status_code == 404:
            raise SlidesError("Yeh presentation nahi mili. Link / naam sahi hai?")
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

    def search(self, query: str = "", limit: int = 15) -> list[dict[str, Any]]:
        if not self.can_search:
            raise SlidesError("Naam se dhoondhna is connection par nahi hota; presentation ka link dijiye.")
        q = [f"mimeType = '{GSLIDES}'", "trashed = false"]
        if query:
            q.append("name contains '" + query.replace("\\", " ").replace("'", " ") + "'")
        res = self._req("GET", DRIVE + "/files", params={
            "q": " and ".join(q), "orderBy": "modifiedTime desc", "pageSize": max(1, min(limit, 50)),
            "fields": "files(id,name,modifiedTime,webViewLink)", "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true"})
        return [{"id": f["id"], "title": f["name"], "modified": f.get("modifiedTime", "")[:10], "link": f.get("webViewLink", "")}
                for f in res.get("files", [])]

    def get(self, pid: str) -> dict[str, Any]:
        return self._req("GET", f"{SLIDES}/{pid}")

    def create(self, title: str) -> dict[str, Any]:
        return self._req("POST", SLIDES, json={"title": title})

    def batch(self, pid: str, requests: list[dict]) -> dict[str, Any]:
        if not requests:
            return {}
        return self._req("POST", f"{SLIDES}/{pid}:batchUpdate", json={"requests": requests})

    def export(self, pid: str, fmt: str) -> bytes:
        mime = EXPORT[fmt][0]
        return self._req("GET", f"{DRIVE}/files/{pid}/export", raw=True, params={"mimeType": mime})

    def share(self, pid: str, email: str, role: str) -> dict:
        return self._req("POST", f"{DRIVE}/files/{pid}/permissions",
                         params={"sendNotificationEmail": "true", "supportsAllDrives": "true"},
                         json={"type": "user", "role": role, "emailAddress": email})

    def thumbnail(self, pid: str, page_id: str) -> str:
        res = self._req("GET", f"{SLIDES}/{pid}/pages/{page_id}/thumbnail",
                        params={"thumbnailProperties.thumbnailSize": "MEDIUM"})
        return res.get("contentUrl", "")
