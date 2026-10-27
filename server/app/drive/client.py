"""Google Drive API v3 over plain HTTPS with a bearer token (refreshed once on 401)."""
from __future__ import annotations

import json
import re
import secrets
from typing import Any, Callable

import httpx

API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"
GDOC = "application/vnd.google-apps.document"
GSHEET = "application/vnd.google-apps.spreadsheet"
GSLIDES = "application/vnd.google-apps.presentation"
GDRAWING = "application/vnd.google-apps.drawing"
FIELDS = "id,name,mimeType,modifiedTime,size,webViewLink,parents,starred,shared,trashed,owners(displayName,emailAddress)"


class DriveError(Exception):
    pass


class NotConnected(DriveError):
    pass


ID_PATTERNS = (re.compile(r"/d/([a-zA-Z0-9_-]{15,})"), re.compile(r"/folders/([a-zA-Z0-9_-]{15,})"),
               re.compile(r"[?&]id=([a-zA-Z0-9_-]{15,})"))


def id_from(text: str) -> str | None:
    t = (text or "").strip()
    for p in ID_PATTERNS:
        m = p.search(t)
        if m:
            return m.group(1)
    return t if re.fullmatch(r"[a-zA-Z0-9_-]{25,}", t) else None


def q_str(s: str) -> str:
    return "'" + str(s).replace("\\", "\\\\").replace("'", "\\'") + "'"


class DriveClient:
    def __init__(self, key: str, address: str, token: Callable[[bool], str], kind: str = "google",
                 client: httpx.Client | None = None, root: str = "root") -> None:
        self.key = key
        self.address = (address or "").lower()
        self.kind = kind
        self.root = root or "root"
        self._token = token
        self._client = client

    def _req(self, method: str, url: str, raw: bool = False, **kw) -> Any:
        c = self._client or httpx.Client(timeout=60)
        extra = kw.pop("headers", {})
        try:
            for attempt in (0, 1):
                r = c.request(method, url, headers={"Authorization": f"Bearer {self._token(attempt == 1)}", **extra}, **kw)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise DriveError(f"Google Drive se baat nahi ho payi ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 403:
            text = r.text
            if "has not been used" in text or "SERVICE_DISABLED" in text:
                raise DriveError("Google Cloud project mein Drive API enable nahi hai.")
            if "exportSizeLimitExceeded" in text:
                raise DriveError("Yeh file itni badi hai ki Google ise convert nahi karta; link se kholiye.")
            if "storageQuotaExceeded" in text:
                raise DriveError("Google Drive bhar gaya hai (storage poori). Kuch jagah khaali kijiye.")
            if self.kind == "service":
                raise DriveError("Santosh ke paas is file ki permission nahi hai. File/folder service account ki email ke "
                                 "saath share kijiye, ya Profile > Google Drive se apna Google account jodiye.")
            raise DriveError("Is file ki permission nahi hai (shayad kisi aur ki file hai jo aapke saath share nahi).")
        if r.status_code == 404:
            raise DriveError("Yeh file ya folder nahi mila. Link / naam sahi hai?")
        if r.status_code >= 400:
            msg = r.text[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise DriveError(f"Google Drive: {msg}")
        if raw:
            return r.content
        return r.json() if r.content else {}

    # ---------------- reading ----------------
    def search(self, q: str, limit: int = 20, order: str = "modifiedTime desc", corpora_all: bool = True) -> list[dict]:
        params = {"q": q, "pageSize": max(1, min(int(limit), 100)), "fields": f"files({FIELDS})",
                  "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
        if order:
            params["orderBy"] = order
        if corpora_all:
            params["corpora"] = "allDrives" if self.kind != "service" else "user"
        return self._req("GET", API + "/files", params=params).get("files", [])

    def get(self, fid: str) -> dict:
        return self._req("GET", f"{API}/files/{fid}", params={"fields": FIELDS, "supportsAllDrives": "true"})

    def download(self, fid: str) -> bytes:
        return self._req("GET", f"{API}/files/{fid}", raw=True, params={"alt": "media", "supportsAllDrives": "true"})

    def export(self, fid: str, mime: str) -> bytes:
        return self._req("GET", f"{API}/files/{fid}/export", raw=True, params={"mimeType": mime})

    def about(self) -> dict:
        return self._req("GET", API + "/about", params={"fields": "user(emailAddress,displayName),storageQuota"})

    def permissions(self, fid: str) -> list[dict]:
        return self._req("GET", f"{API}/files/{fid}/permissions", params={
            "fields": "permissions(id,type,role,emailAddress,displayName)", "supportsAllDrives": "true"}).get("permissions", [])

    # ---------------- writing ----------------
    def upload(self, name: str, mime: str, data: bytes, parent: str | None = None, convert_to: str | None = None) -> dict:
        meta: dict[str, Any] = {"name": name}
        if parent:
            meta["parents"] = [parent]
        if convert_to:
            meta["mimeType"] = convert_to
        boundary = "santosh" + secrets.token_hex(12)
        body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
                f"--{boundary}\r\nContent-Type: {mime or 'application/octet-stream'}\r\n\r\n").encode() + data + \
            f"\r\n--{boundary}--\r\n".encode()
        return self._req("POST", UPLOAD, params={"uploadType": "multipart", "fields": FIELDS, "supportsAllDrives": "true"},
                         content=body, headers={"Content-Type": f"multipart/related; boundary={boundary}"})

    def create_folder(self, name: str, parent: str | None = None) -> dict:
        body: dict[str, Any] = {"name": name, "mimeType": FOLDER}
        if parent:
            body["parents"] = [parent]
        return self._req("POST", API + "/files", params={"fields": FIELDS, "supportsAllDrives": "true"}, json=body)

    def update(self, fid: str, body: dict | None = None, add_parents: str = "", remove_parents: str = "") -> dict:
        params = {"fields": FIELDS, "supportsAllDrives": "true"}
        if add_parents:
            params["addParents"] = add_parents
        if remove_parents:
            params["removeParents"] = remove_parents
        return self._req("PATCH", f"{API}/files/{fid}", params=params, json=body or {})

    def copy(self, fid: str, name: str | None = None, parent: str | None = None) -> dict:
        body: dict[str, Any] = {}
        if name:
            body["name"] = name
        if parent:
            body["parents"] = [parent]
        return self._req("POST", f"{API}/files/{fid}/copy", params={"fields": FIELDS, "supportsAllDrives": "true"}, json=body)

    def share(self, fid: str, email: str, role: str, message: str = "") -> dict:
        params = {"sendNotificationEmail": "true", "supportsAllDrives": "true"}
        if message:
            params["emailMessage"] = message[:1000]
        return self._req("POST", f"{API}/files/{fid}/permissions", params=params,
                         json={"type": "user", "role": role, "emailAddress": email})

    def share_anyone(self, fid: str, role: str = "reader") -> dict:
        return self._req("POST", f"{API}/files/{fid}/permissions", params={"supportsAllDrives": "true"},
                         json={"type": "anyone", "role": role})
