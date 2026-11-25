"""Google Photos Picker API + Library API (app-created data only), over HTTPS with a bearer token.

Since 31 March 2025 Google lets apps read only (a) the photos the user picks in the Google Photos Picker, and
(b) the photos and albums the app itself uploaded. Santosh never browses or deletes the user's library.
"""
from __future__ import annotations

import time
from typing import Any, Callable

import httpx

PICKER = "https://photospicker.googleapis.com/v1"
LIBRARY = "https://photoslibrary.googleapis.com/v1"


class PhotosError(Exception):
    pass


class NotConnected(PhotosError):
    pass


SIMPLE_MAX = 20 * 1024 * 1024   # bigger files go through the resumable upload
CHUNK = 8 * 1024 * 1024
RETRIES = 5          # v0.999.191 Google asks for retries with backoff on 429 / 5xx
RETRY_WAIT = 1.0


class PhotosClient:
    def __init__(self, key: str, address: str, token: Callable[[bool], str], client: httpx.Client | None = None,
                 can_library: bool = True) -> None:
        self.key = key
        self.address = (address or "").lower()
        self._token = token
        self._client = client
        self.can_library = can_library

    def _req(self, method: str, url: str, raw: bool = False, text: bool = False, headers: dict | None = None,
             whole: bool = False, **kw) -> Any:
        c = self._client or httpx.Client(timeout=300)
        try:
            refreshed, tries = False, 0
            while True:
                h = {"Authorization": f"Bearer {self._token(refreshed)}", **(headers or {})}
                try:
                    r = c.request(method, url, headers=h, **kw)
                except httpx.TransportError as e:
                    if tries < RETRIES and method == "GET":
                        tries += 1
                        time.sleep(RETRY_WAIT * (2 ** (tries - 1)))
                        continue
                    raise PhotosError(f"Could not reach Google Photos ({type(e).__name__})")
                if r.status_code == 401 and not refreshed:
                    refreshed = True
                    continue
                if (r.status_code == 429 or r.status_code >= 500) and tries < RETRIES:
                    tries += 1
                    wait = RETRY_WAIT * (2 ** (tries - 1))
                    try:
                        wait = max(wait, min(30.0, float(r.headers.get("retry-after", 0)))) if RETRY_WAIT else 0
                    except ValueError:
                        pass
                    time.sleep(wait)
                    continue
                break
        except httpx.HTTPError as e:
            raise PhotosError(f"Could not reach Google Photos ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 403:
            if "has not been used" in r.text or "SERVICE_DISABLED" in r.text:
                raise PhotosError("The Photos Picker / Photos Library API is not enabled in the Google Cloud project.")
            if "insufficient" in r.text.lower() or "scope" in r.text.lower():
                raise PhotosError("Google Photos permission is missing. On the web console open Connectors > Google, or in "
                                  "the phone app open Settings > Google, and press Reconnect for Google Photos.")
            msg = ""
            try:
                msg = r.json().get("error", {}).get("message", "")
            except Exception:
                pass
            raise PhotosError("Google Photos refused this" + (f": {msg[:200]}" if msg else ".")
                              + " Google lets Hoola change only photos and albums Hoola itself added.")
        if r.status_code == 404:
            raise PhotosError("This photo / album / picker session was not found (it may have expired).")
        if r.status_code == 429:
            raise PhotosError("Google Photos is limiting requests right now (its speed limit); try again in a little while.")
        if r.status_code >= 400:
            msg = r.text[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise PhotosError(f"Google Photos: {msg}")
        if whole:
            return r
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
        if len(data) > SIMPLE_MAX:
            return self.upload_resumable(data, mime)
        return self._req("POST", f"{LIBRARY}/uploads", text=True, content=data,
                         headers={"Content-type": "application/octet-stream", "X-Goog-Upload-Content-Type": mime,
                                  "X-Goog-Upload-Protocol": "raw"}).strip()

    def upload_resumable(self, data: bytes, mime: str) -> str:
        """v0.999.191 Google's resumable upload for big files: start, then chunks in its granularity, then finalize."""
        r = self._req("POST", f"{LIBRARY}/uploads", whole=True, content=b"",
                      headers={"Content-Length": "0", "X-Goog-Upload-Command": "start",
                               "X-Goog-Upload-Content-Type": mime, "X-Goog-Upload-Protocol": "resumable",
                               "X-Goog-Upload-Raw-Size": str(len(data))})
        url = r.headers.get("x-goog-upload-url")
        if not url:
            raise PhotosError("Google Photos did not start the upload; please try again.")
        gran = int(r.headers.get("x-goog-upload-chunk-granularity") or 262144)
        size = max(gran, (CHUNK // gran) * gran)
        off, tok = 0, ""
        while off < len(data):
            part = data[off:off + size]
            last = off + len(part) >= len(data)
            tok = self._req("POST", url, text=True, content=part,
                            headers={"X-Goog-Upload-Command": "upload, finalize" if last else "upload",
                                     "X-Goog-Upload-Offset": str(off)})
            off += len(part)
        return tok.strip()

    def batch_create(self, items: list[dict], album_id: str | None = None, position: dict | None = None) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"newMediaItems": items}
        if album_id:
            body["albumId"] = album_id
            if position:
                body["albumPosition"] = position
        return self._req("POST", f"{LIBRARY}/mediaItems:batchCreate", json=body).get("newMediaItemResults", [])

    def albums(self, limit: int = 1000) -> list[dict[str, Any]]:
        out, token = [], None
        while len(out) < limit:
            params: dict[str, Any] = {"pageSize": 50, "excludeNonAppCreatedData": "true"}
            if token:
                params["pageToken"] = token
            res = self._req("GET", f"{LIBRARY}/albums", params=params)
            out += res.get("albums", [])
            token = res.get("nextPageToken")
            if not token:
                break
        return out[:limit]

    def album(self, album_id: str) -> dict[str, Any]:
        return self._req("GET", f"{LIBRARY}/albums/{album_id}")

    def create_album(self, title: str) -> dict[str, Any]:
        return self._req("POST", f"{LIBRARY}/albums", json={"album": {"title": title[:500]}})

    def patch_album(self, album_id: str, title: str | None = None, cover: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"id": album_id}
        mask: list[str] = []
        if title is not None:
            body["title"] = title[:500]
            mask.append("title")
        if cover is not None:
            body["coverPhotoMediaItemId"] = cover
            mask.append("coverPhotoMediaItemId")
        return self._req("PATCH", f"{LIBRARY}/albums/{album_id}", params={"updateMask": ",".join(mask)}, json=body)

    def album_add(self, album_id: str, ids: list[str]) -> None:
        for i in range(0, len(ids), 50):
            self._req("POST", f"{LIBRARY}/albums/{album_id}:batchAddMediaItems", json={"mediaItemIds": ids[i:i + 50]})

    def album_remove(self, album_id: str, ids: list[str]) -> None:
        for i in range(0, len(ids), 50):
            self._req("POST", f"{LIBRARY}/albums/{album_id}:batchRemoveMediaItems", json={"mediaItemIds": ids[i:i + 50]})

    def add_enrichment(self, album_id: str, item: dict, position: dict) -> dict[str, Any]:
        return self._req("POST", f"{LIBRARY}/albums/{album_id}:addEnrichment",
                         json={"newEnrichmentItem": item, "albumPosition": position})

    def search(self, album_id: str | None = None, filters: dict | None = None, limit: int = 100,
               order: str = "") -> list[dict[str, Any]]:
        out, token = [], None
        while len(out) < limit:
            body: dict[str, Any] = {"pageSize": 100}
            if album_id:
                body["albumId"] = album_id
            elif filters:
                body["filters"] = filters
                if order:
                    body["orderBy"] = order
            if token:
                body["pageToken"] = token
            res = self._req("POST", f"{LIBRARY}/mediaItems:search", json=body)
            out += res.get("mediaItems", [])
            token = res.get("nextPageToken")
            if not token:
                break
        return out[:limit]

    def album_items(self, album_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.search(album_id, limit=max(1, min(limit, 20000)))

    def items(self, limit: int = 100) -> list[dict[str, Any]]:
        out, token = [], None
        while len(out) < limit:
            params: dict[str, Any] = {"pageSize": 100}
            if token:
                params["pageToken"] = token
            res = self._req("GET", f"{LIBRARY}/mediaItems", params=params)
            out += res.get("mediaItems", [])
            token = res.get("nextPageToken")
            if not token:
                break
        return out[:limit]

    def item(self, mid: str) -> dict[str, Any]:
        return self._req("GET", f"{LIBRARY}/mediaItems/{mid}")

    def items_get(self, ids: list[str]) -> list[dict[str, Any]]:
        out: list[dict] = []
        for i in range(0, len(ids), 50):
            res = self._req("GET", f"{LIBRARY}/mediaItems:batchGet", params=[("mediaItemIds", x) for x in ids[i:i + 50]])
            for r in res.get("mediaItemResults", []):
                if r.get("mediaItem"):
                    out.append(r["mediaItem"])
        return out

    def patch_item(self, mid: str, description: str) -> dict[str, Any]:
        return self._req("PATCH", f"{LIBRARY}/mediaItems/{mid}", params={"updateMask": "description"},
                         json={"id": mid, "description": description[:1000]})
