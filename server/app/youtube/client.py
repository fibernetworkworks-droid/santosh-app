"""YouTube Data API v3 + YouTube Analytics API v2 over HTTPS. Public lookups use the server's API key (or the
user's sign-in); the user's own channel uses their OAuth token."""
from __future__ import annotations

import re
from typing import Any, Callable

import httpx

API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"


class YTError(Exception):
    pass


class NotConnected(YTError):
    pass


ID_PATTERNS = (re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/|v/))([\w-]{11})"),)


def video_id(text: str) -> str | None:
    t = (text or "").strip()
    for p in ID_PATTERNS:
        m = p.search(t)
        if m:
            return m.group(1)
    return t if re.fullmatch(r"[\w-]{11}", t) else None


def watch_url(vid: str) -> str:
    return f"https://www.youtube.com/watch?v={vid}"


def iso_duration(s: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


class YouTubeClient:
    def __init__(self, key: str, address: str, token: Callable[[bool], str] | None = None, api_key: str = "",
                 client: httpx.Client | None = None) -> None:
        self.key = key
        self.address = (address or "").lower()
        self._token = token
        self.api_key = api_key
        self._client = client

    @property
    def signed_in(self) -> bool:
        return self._token is not None

    def _req(self, method: str, url: str, auth: bool = False, **kw) -> Any:
        if auth and not self._token:
            raise NotConnected("Iske liye apna YouTube channel jodiye: Profile > YouTube > 'YouTube jodiye'.")
        c = self._client or httpx.Client(timeout=60)
        params = dict(kw.pop("params", None) or {})
        headers = dict(kw.pop("headers", None) or {})
        use_token = auth or (not self.api_key and self._token is not None)
        if not use_token:
            if not self.api_key:
                raise NotConnected("YouTube ke liye server par YOUTUBE_API_KEY chahiye, ya Profile > YouTube se Google account jodiye.")
            params["key"] = self.api_key
        try:
            for attempt in (0, 1):
                h = dict(headers)
                if use_token:
                    h["Authorization"] = f"Bearer {self._token(attempt == 1)}"
                r = c.request(method, url, params=params, headers=h, **kw)
                if r.status_code == 401 and use_token and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise YTError(f"YouTube se baat nahi ho payi ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code >= 400:
            msg, reason = r.text[:300], ""
            try:
                err = r.json().get("error", {})
                msg = err.get("message", msg)
                reason = ((err.get("errors") or [{}])[0]).get("reason", "")
            except Exception:
                pass
            if reason in ("quotaExceeded", "dailyLimitExceeded"):
                raise YTError("Aaj ka YouTube API quota khatam ho gaya; kal phir koshish kijiye.")
            if "has not been used" in msg or reason == "accessNotConfigured":
                raise YTError("Google Cloud project mein YouTube Data API (ya Analytics API) enable nahi hai.")
            if reason in ("commentsDisabled",):
                raise YTError("Is video par comments band hain.")
            if r.status_code == 404 or reason in ("videoNotFound", "channelNotFound"):
                raise YTError("Yeh video / channel nahi mila.")
            if r.status_code == 403:
                raise YTError(f"YouTube ne mana kiya: {msg}")
            raise YTError(f"YouTube: {msg}")
        return r.json() if r.content else {}

    def get(self, path: str, auth: bool = False, **params) -> dict:
        return self._req("GET", API + path, auth=auth, params={k: v for k, v in params.items() if v not in (None, "")})

    def post(self, path: str, body: dict, part: str) -> dict:
        return self._req("POST", API + path, auth=True, params={"part": part}, json=body)

    def put(self, path: str, body: dict, part: str) -> dict:
        return self._req("PUT", API + path, auth=True, params={"part": part}, json=body)

    def analytics(self, **params) -> dict:
        return self._req("GET", ANALYTICS, auth=True, params=params)

    def upload(self, data: bytes, mime: str, snippet: dict, status: dict) -> dict:
        """Resumable upload in one go: start the session, then send the bytes."""
        start = self._req_raw("POST", UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"},
                              json={"snippet": snippet, "status": status},
                              headers={"X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(len(data))})
        loc = start.headers.get("location")
        if not loc:
            raise YTError("YouTube ne upload shuru nahi kiya.")
        r = self._req_raw("PUT", loc, content=data, headers={"Content-Type": mime})
        return r.json()

    def _req_raw(self, method: str, url: str, **kw) -> httpx.Response:
        if not self._token:
            raise NotConnected("Upload ke liye apna YouTube channel jodiye.")
        c = self._client or httpx.Client(timeout=600)
        headers = dict(kw.pop("headers", None) or {})
        try:
            for attempt in (0, 1):
                r = c.request(method, url, headers={**headers, "Authorization": f"Bearer {self._token(attempt == 1)}"}, **kw)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise YTError(f"Upload mein dikkat ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code >= 400:
            raise YTError(f"YouTube upload: {r.text[:200]}")
        return r
