"""Google Photos Picker API + Library API (app-created data only), over HTTPS with a bearer token.

Since 31 March 2025 Google lets apps read only (a) the photos the user picks in the Google Photos Picker, and
(b) the photos and albums the app itself uploaded. Santosh never browses or deletes the user's library.
"""
from __future__ import annotations

from typing import Any, Callable

import httpx

PICKER = "https://photospicker.googleapis.com/v1"
LIBRARY = "https://photoslibrary.googleapis.com/v1"


class PhotosError(Exception):
    pass


class NotConnected(PhotosError):
    pass


class PhotosClient:
    def __init__(self, key: str, address: str, token: Callable[[bool], str], client: httpx.Client | None = None,
                 can_library: bool = True) -> None:
        self.key = key
        self.address = (address or "").lower()
        self._token = token
        self._client = client
        self.can_library = can_library

    def _req(self, method: str, url: str, raw: bool = False, text: bool = False, headers: dict | None = None, **kw) -> Any:
        c = self._client or httpx.Client(timeout=90)
        try:
            for attempt in (0, 1):
                h = {"Authorization": f"Bearer {self._token(attempt == 1)}", **(headers or {})}
                r = c.request(method, url, headers=h, **kw)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise PhotosError(f"Google Photos se baat nahi ho payi ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 403:
            if "has not been used" in r.text or "SERVICE_DISABLED" in r.text:
                raise PhotosError("Google Cloud project mein Photos Picker / Photos Library API enable nahi hai.")
            raise PhotosError("Google Photos ki permission nahi mili. Profile > Google Photos se dobara jodiye.")
        if r.status_code == 404:
            raise PhotosError("Yeh photo / album / chunne ka session nahi mila (shayad expire ho gaya).")
        if r.status_code == 429:
            raise PhotosError("Google Photos ne abhi bahut requests ki wajah se roka hai; thodi der baad try kijiye.")
        if r.status_code >= 400:
            msg = r.text[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise PhotosError(f"Google Photos: {msg}")
        if raw:
            return r.content
        if text:
            return r.text
        return r.json() if r.content else {}

    # ---------------- Picker ----------------
    def new_session(self, max_items: int = 0) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if max_items:
            body["pickingConfig"] = {"maxItemCount": str(max(1, min(int(max_items), 2000)))}
        return self._req("POST", f"{PICKER}/sessions", json=body)

    def get_session(self, sid: str) -> dict[str, Any]:
        return self._req("GET", f"{PICKER}/sessions/{sid}")

    def delete_session(self, sid: str) -> None:
        self._req("DELETE", f"{PICKER}/sessions/{sid}")

    def picked(self, sid: str, limit: int = 2000) -> list[dict[str, Any]]:
        out, token = [], None
        while len(out) < limit:
            params: dict[str, Any] = {"sessionId": sid, "pageSize": 100}
            if token:
                params["pageToken"] = token
            res = self._req("GET", f"{PICKER}/mediaItems", params=params)
            out += res.get("mediaItems", [])
            token = res.get("nextPageToken")
            if not token:
                break
        return out[:limit]

    def download(self, base_url: str, kind: str = "PHOTO", preview: bool = False) -> bytes:
        suffix = "=w1024-h1024" if preview else ("=dv" if kind == "VIDEO" else "=d")
        return self._req("GET", base_url + suffix, raw=True)

    # ---------------- Library (app-created only) ----------------
    def upload_bytes(self, data: bytes, mime: str) -> str:
        return self._req("POST", f"{LIBRARY}/uploads", text=True, content=data,
                         headers={"Content-type": "application/octet-stream", "X-Goog-Upload-Content-Type": mime,
                                  "X-Goog-Upload-Protocol": "raw"}).strip()

    def batch_create(self, items: list[dict], album_id: str | None = None) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"newMediaItems": items}
        if album_id:
            body["albumId"] = album_id
        return self._req("POST", f"{LIBRARY}/mediaItems:batchCreate", json=body).get("newMediaItemResults", [])

    def albums(self) -> list[dict[str, Any]]:
        out, token = [], None
        for _ in range(10):
            params: dict[str, Any] = {"pageSize": 50, "excludeNonAppCreatedData": "true"}
            if token:
                params["pageToken"] = token
            res = self._req("GET", f"{LIBRARY}/albums", params=params)
            out += res.get("albums", [])
            token = res.get("nextPageToken")
            if not token:
                break
        return out

    def create_album(self, title: str) -> dict[str, Any]:
        return self._req("POST", f"{LIBRARY}/albums", json={"album": {"title": title[:500]}})

    def album_items(self, album_id: str, limit: int = 100) -> list[dict[str, Any]]:
        res = self._req("POST", f"{LIBRARY}/mediaItems:search", json={"albumId": album_id, "pageSize": max(1, min(limit, 100))})
        return res.get("mediaItems", [])
