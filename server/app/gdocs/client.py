"""Google Docs API v1 (revision 20261118) over HTTPS, on her Google Drive connection (Google's Docs API accepts the
full Drive permission, so no new sign-in is needed)."""
from __future__ import annotations

import random
import re
import time
from typing import Any

import httpx

from ..drive.client import DriveClient, DriveError

DOCS = "https://docs.googleapis.com/v1/documents"
GDOC = "application/vnd.google-apps.document"
RETRIES = 5
RETRY_WAIT = 1.0
RATE = ("rateLimitExceeded", "userRateLimitExceeded", "RATE_LIMIT_EXCEEDED", "RESOURCE_EXHAUSTED", "Quota exceeded")
ID_RE = re.compile(r"/document/(?:u/\d+/)?d/([a-zA-Z0-9_-]{20,})")


class DocsError(DriveError):
    pass


class StaleDoc(DocsError):
    """The document changed between Hoola's read and its write (Google's requiredRevisionId check)."""


def id_from(text: str) -> str | None:
    m = ID_RE.search(text or "")
    if m:
        return m.group(1)
    t = (text or "").strip()
    return t if re.fullmatch(r"[a-zA-Z0-9_-]{30,}", t) else None


class DocsClient:
    def __init__(self, drive: DriveClient) -> None:
        self.drive = drive
        self.key = drive.key
        self.address = drive.address

    def _req(self, method: str, url: str, **kw) -> Any:
        """Google's limits (60 writes a minute per user) are waited out with backoff + a little randomness, as Google
        asks; its other refusals are said in plain words."""
        d = self.drive
        c = d._client or httpx.Client(timeout=120)
        try:
            fresh, tries = False, 0
            while True:
                r = c.request(method, url, headers={"Authorization": f"Bearer {d._token(fresh)}"}, **kw)
                if r.status_code == 401 and not fresh:
                    fresh = True
                    continue
                busy = r.status_code in (429, 500, 502, 503, 504) or (
                    r.status_code == 403 and any(w in r.text for w in RATE))
                if busy and tries < RETRIES:
                    tries += 1
                    try:
                        wait = float(r.headers.get("retry-after") or 0)
                    except ValueError:
                        wait = 0.0
                    if RETRY_WAIT:
                        time.sleep(min(max(wait, RETRY_WAIT * 2 ** (tries - 1)) + random.random() * 0.5, 32.0))
                    continue
                break
        except httpx.HTTPError as e:
            raise DocsError(f"Could not reach Google Docs ({type(e).__name__})")
        finally:
            if d._client is None:
                c.close()
        if r.status_code < 400:
            return r.json() if r.content else {}
        msg = r.text[:400]
        try:
            msg = r.json().get("error", {}).get("message", msg)
        except Exception:
            pass
        low = msg.lower()
        if r.status_code == 429 or any(w in r.text for w in RATE):
            raise DocsError("Google Docs is limiting how fast Hoola can work (60 changes a minute per person). Hoola "
                            "waited and tried 5 times; try again in a minute.")
        if r.status_code == 403:
            if "has not been used" in r.text or "SERVICE_DISABLED" in r.text:
                raise DocsError("The Google Docs API is not enabled in the Google Cloud project.")
            if "insufficient" in low and "scope" in low:
                raise DocsError("Google Docs was connected without the permission this needs. Open Connectors > Google "
                                "(console) or Settings > Google (phone) and press Reconnect for Drive / Docs.")
            if "suggestion" in low:
                raise DocsError(f"Google refused this suggestion change: {msg[:200]}")
            raise DocsError("She can only view or comment on this document, or it belongs to someone who has not shared "
                            "it with her for editing.")
        if r.status_code == 404:
            raise DocsError("This document was not found. Is the link / name right?")
        if r.status_code == 400 and "revision" in low and ("required" in low or "match" in low or "latest" in low):
            raise StaleDoc("The document changed while Hoola was working on it.")
        raise DocsError(f"Google Docs refused this: {msg[:300]}")

    def get(self, doc_id: str, suggestions: str = "SUGGESTIONS_INLINE", comments: bool = False) -> dict[str, Any]:
        """Google's rules: indexes for a later change come only from SUGGESTIONS_INLINE; comments need it + tabs."""
        params: dict[str, Any] = {"includeTabsContent": "true", "suggestionsViewMode": suggestions}
        if comments:
            params["commentsViewMode"] = "COMMENTS_VIEW_MODE_INCLUDED"
            params["suggestionsViewMode"] = "SUGGESTIONS_INLINE"
        return self._req("GET", f"{DOCS}/{doc_id}", params=params)

    def create(self, title: str) -> dict[str, Any]:
        return self._req("POST", DOCS, json={"title": (title or "Untitled document")[:300]})

    def batch(self, doc_id: str, requests: list[dict], revision: str = "", suggest: bool = False) -> list[dict]:
        if not requests:
            return []
        body: dict[str, Any] = {"requests": requests}
        wc: dict[str, Any] = {}
        if revision:
            wc["requiredRevisionId"] = revision
        if suggest:
            wc["writeMode"] = "SUGGEST"
        if wc:
            body["writeControl"] = wc
        return self._req("POST", f"{DOCS}/{doc_id}:batchUpdate", json=body).get("replies", [])
