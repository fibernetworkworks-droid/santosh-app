"""Google Drive API v3 over plain HTTPS with a bearer token (refreshed once on 401)."""
from __future__ import annotations

import json
import re
import secrets
import time
from typing import Any, Callable

import httpx

API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"
GDOC = "application/vnd.google-apps.document"
GSHEET = "application/vnd.google-apps.spreadsheet"
GSLIDES = "application/vnd.google-apps.presentation"
GDRAWING = "application/vnd.google-apps.drawing"
SHORTCUT = "application/vnd.google-apps.shortcut"
GFORM = "application/vnd.google-apps.form"
FIELDS = ("id,name,mimeType,modifiedTime,size,webViewLink,parents,starred,shared,trashed,description,createdTime,"
          "lastModifyingUser(displayName),copyRequiresWriterPermission,writersCanShare,quotaBytesUsed,"
          "shortcutDetails(targetId,targetMimeType),owners(displayName,emailAddress),md5Checksum,driveId,"
          "folderColorRgb,contentRestrictions(readOnly,reason),viewedByMeTime,ownedByMe")
RETRIES = 5            # v0.999.186 Google's speed limit / a busy Google: wait and ask again
RETRY_WAIT = 1.0
SMALL_UPLOAD = 5 * 1024 * 1024      # Google: multipart for 5 MB or less, resumable above
RATE_REASONS = ("userratelimitexceeded", "ratelimitexceeded", "backenderror")


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

    @staticmethod
    def _reason(r: httpx.Response) -> str:
        try:
            err = r.json().get("error", {})
            errs = err.get("errors") or []
            return str((errs[0].get("reason") if errs else "") or err.get("status") or "").lower()
        except Exception:
            return ""

    def _req(self, method: str, url: str, raw: bool = False, resp: bool = False, **kw) -> Any:
        c = self._client or httpx.Client(timeout=120)
        extra = kw.pop("headers", {})
        try:
            fresh, busy = False, 0
            while True:
                r = c.request(method, url, headers={"Authorization": f"Bearer {self._token(fresh)}", **extra}, **kw)
                if r.status_code == 401 and not fresh:
                    fresh = True
                    continue
                busy_now = r.status_code in (429, 500, 502, 503, 504) or (
                    r.status_code == 403 and self._reason(r) in RATE_REASONS)
                if busy_now and busy < RETRIES:
                    busy += 1
                    try:
                        wait = float(r.headers.get("retry-after") or 0)
                    except ValueError:
                        wait = 0.0
                    time.sleep(min(max(wait, RETRY_WAIT * (2 ** (busy - 1))), 32.0))
                    continue
                break
        except httpx.HTTPError as e:
            raise DriveError(f"Could not talk to Google Drive ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        reason = self._reason(r) if r.status_code >= 400 else ""
        if r.status_code == 429 or reason in RATE_REASONS:
            raise DriveError("Google is limiting how fast Hoola can work in Drive right now. Hoola waited and tried 5 "
                             "times; try again in a minute.")
        if r.status_code == 403:
            text = r.text
            low = text.lower()
            if "has not been used" in text or "SERVICE_DISABLED" in text:
                need = "Drive Activity" if "driveactivity" in url else "Drive Labels" if "drivelabels" in url else "Drive"
                raise DriveError(f"The {need} API is not enabled in the Google Cloud project.")
            if "insufficient" in low and ("scope" in low or "permission" in reason):
                need = ("Drive Activity" if "driveactivity" in url else "Drive Labels" if "drivelabels" in url
                        else "Drive")
                raise DriveError(f"Hoola needs Google {need} access for this. Open Connectors > Google, choose {need} and "
                                 "press Connect, then ask again.")
            if "exportsizelimitexceeded" in low:
                raise DriveError("This file is too big for Google to convert; open it from the link.")
            if "storagequotaexceeded" in low or "quotaexceeded" in reason:
                raise DriveError("Google Drive is full (no storage left). Free up some space.")
            if "sharingratelimitexceeded" in reason:
                raise DriveError("Google allows only so many sharing changes in a short time; try again later.")
            if "domainpolicy" in reason or "domain policy" in low:
                raise DriveError("Her organisation's Google settings do not allow this (domain policy). Her Google admin "
                                 "decides it.")
            if reason == "teamdrivemembershiprequired" or "shared drive" in low and "member" in low:
                raise DriveError("She is not a member of this shared drive (or not with a role that can do this).")
            if reason in ("cannotsharewithowner", "cannotsharetodomain", "publishoutnotpermitted",
                          "cannotshareteamdrivetopfolderwithanyoneordomains", "cannotshareteamdrivewithnondomainusers"):
                raise DriveError(f"Google does not allow this sharing here ({reason}).")
            if reason == "consentrequiredforownershiptransfer":
                raise DriveError("Google needs the new owner to accept ownership (consentRequiredForOwnershipTransfer).")
            if self.kind == "service":
                raise DriveError("Hoola does not have permission for this file. Share the file / folder with the service account's email, "
                                 "or connect your own Google account in Profile > Google Drive.")
            raise DriveError("No permission for this file (it may be someone else's file that is not shared with you, or "
                             "her role on it does not allow this).")
        if r.status_code == 404:
            raise DriveError("This file or folder was not found. Are the link / name right?")
        if r.status_code >= 400:
            msg = r.text[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise DriveError(f"Google Drive: {msg}")
        if resp:
            return r
        if raw:
            return r.content
        return r.json() if r.content else {}

    def _pages(self, url: str, params: dict, key: str, limit: int, page_max: int = 100) -> tuple[list[dict], bool]:
        """Every page of a Drive list up to `limit` items; second value = Google has more."""
        out: list[dict] = []
        token = ""
        while True:
            pp = dict(params, pageSize=max(1, min(page_max, limit - len(out))))
            if token:
                pp["pageToken"] = token
            if "fields" in pp and "nextPageToken" not in pp["fields"]:
                pp["fields"] = "nextPageToken," + pp["fields"]
            data = self._req("GET", url, params=pp)
            out += data.get(key, []) or []
            token = data.get("nextPageToken") or ""
            if not token or len(out) >= limit:
                return out[:limit], bool(token)

    # ---------------- reading ----------------
    def search(self, q: str, limit: int = 20, order: str = "modifiedTime desc", corpora_all: bool = True,
               drive_id: str = "") -> list[dict]:
        return self.search_more(q, limit, order, corpora_all, drive_id)[0]

    def search_more(self, q: str, limit: int = 20, order: str = "modifiedTime desc", corpora_all: bool = True,
                    drive_id: str = "") -> tuple[list[dict], bool]:
        """v0.999.186 files.list across pages (Google gives at most 100 a page): up to `limit`, plus whether more exist."""
        params = {"q": q, "fields": f"files({FIELDS})", "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
        if order:
            params["orderBy"] = order
        if drive_id:
            params["corpora"], params["driveId"] = "drive", drive_id
        elif corpora_all:
            params["corpora"] = "allDrives" if self.kind != "service" else "user"
        return self._pages(API + "/files", params, "files", max(1, min(int(limit), 5000)))

    def get(self, fid: str) -> dict:
        return self._req("GET", f"{API}/files/{fid}", params={"fields": FIELDS, "supportsAllDrives": "true"})

    def download(self, fid: str) -> bytes:
        return self._req("GET", f"{API}/files/{fid}", raw=True, params={"alt": "media", "supportsAllDrives": "true"})

    def export(self, fid: str, mime: str) -> bytes:
        return self._req("GET", f"{API}/files/{fid}/export", raw=True, params={"mimeType": mime})

    def about(self) -> dict:
        return self._req("GET", API + "/about", params={"fields": "user(emailAddress,displayName),storageQuota"})

    def permissions(self, fid: str) -> list[dict]:
        return self._pages(f"{API}/files/{fid}/permissions", {
            "fields": "permissions(id,type,role,emailAddress,displayName,domain,expirationTime,pendingOwner,"
                      "allowFileDiscovery,permissionDetails(inherited,role))", "supportsAllDrives": "true"},
            "permissions", 1000)[0]

    # ---------------- writing ----------------
    def upload(self, name: str, mime: str, data: bytes, parent: str | None = None, convert_to: str | None = None,
               extra_meta: dict | None = None, params: dict | None = None) -> dict:
        meta: dict[str, Any] = {"name": name, **(extra_meta or {})}
        if parent:
            meta["parents"] = [parent]
        if convert_to:
            meta["mimeType"] = convert_to
        return self._send_media("POST", UPLOAD, meta, mime, data, params)

    def update_media(self, fid: str, mime: str, data: bytes, meta: dict | None = None) -> dict:
        """v0.999.186 new contents for the same file: the link, sharing and comments stay; Drive keeps the old version."""
        return self._send_media("PATCH", f"{UPLOAD}/{fid}", meta or {}, mime, data, None)

    def _send_media(self, method: str, url: str, meta: dict, mime: str, data: bytes, params: dict | None) -> dict:
        p = {"fields": FIELDS, "supportsAllDrives": "true", **(params or {})}
        mime = mime or "application/octet-stream"
        if len(data) > SMALL_UPLOAD:   # Google's resumable upload: start a session, then PUT the bytes
            r = self._req(method, url, resp=True, params={**p, "uploadType": "resumable"}, json=meta,
                          headers={"X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(len(data))})
            loc = r.headers.get("location") or r.headers.get("Location")
            if not loc:
                raise DriveError("Google did not open an upload session; try again.")
            return self._req("PUT", loc, content=data, headers={"Content-Type": mime})
        boundary = "santosh" + secrets.token_hex(12)
        body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
                f"--{boundary}\r\nContent-Type: {mime}\r\n\r\n").encode() + data + \
            f"\r\n--{boundary}--\r\n".encode()
        return self._req(method, url, params={**p, "uploadType": "multipart"},
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

    def permission_update(self, fid: str, pid: str, role: str, transfer: bool = False) -> dict:
        params: dict[str, str] = {"supportsAllDrives": "true"}
        if transfer:
            params["transferOwnership"] = "true"
            params["moveToNewOwnersRoot"] = "true"
        return self._req("PATCH", f"{API}/files/{fid}/permissions/{pid}", params=params, json={"role": role})

    def permission_delete(self, fid: str, pid: str) -> None:
        self._req("DELETE", f"{API}/files/{fid}/permissions/{pid}", params={"supportsAllDrives": "true"})

    # ---------------- comments ----------------
    def comments(self, fid: str, limit: int = 500) -> list[dict]:
        return self._pages(f"{API}/files/{fid}/comments", {
            "includeDeleted": "false", "supportsAllDrives": "true",
            "fields": "comments(id,author(displayName,emailAddress),content,createdTime,modifiedTime,resolved,"
                      "quotedFileContent(value),replies(id,author(displayName),content,createdTime,resolved))"},
            "comments", max(1, int(limit)))[0]

    def comment_add(self, fid: str, content: str) -> dict:
        return self._req("POST", f"{API}/files/{fid}/comments", params={"supportsAllDrives": "true"},
                         json={"content": str(content)[:4000]})

    def reply_add(self, fid: str, cid: str, content: str) -> dict:
        return self._req("POST", f"{API}/files/{fid}/comments/{cid}/replies", params={"supportsAllDrives": "true"},
                         json={"content": str(content)[:4000]})

    def comment_update(self, fid: str, cid: str, content: str | None = None, resolved: bool | None = None) -> dict:
        body: dict[str, Any] = {}
        if content is not None:
            body["content"] = str(content)[:4000]
        if resolved is not None:
            body["resolved"] = bool(resolved)
        return self._req("PATCH", f"{API}/files/{fid}/comments/{cid}", params={"supportsAllDrives": "true"}, json=body)

    def comment_delete(self, fid: str, cid: str) -> None:
        self._req("DELETE", f"{API}/files/{fid}/comments/{cid}", params={"supportsAllDrives": "true"})

    # ---------------- revisions ----------------
    def revisions(self, fid: str, limit: int = 1000) -> list[dict]:
        return self._pages(f"{API}/files/{fid}/revisions", {
            "supportsAllDrives": "true",
            "fields": "revisions(id,modifiedTime,lastModifyingUser(displayName),keepForever,size,mimeType,"
                      "originalFilename,exportLinks)"}, "revisions", max(1, int(limit)), 200)[0]

    def revision_update(self, fid: str, rid: str, keep: bool) -> dict:
        return self._req("PATCH", f"{API}/files/{fid}/revisions/{rid}", params={"supportsAllDrives": "true"},
                         json={"keepForever": bool(keep)})

    # ---------------- hard delete / shared drives / shortcuts ----------------
    def delete(self, fid: str) -> None:
        self._req("DELETE", f"{API}/files/{fid}", params={"supportsAllDrives": "true"})

    def empty_trash(self) -> None:
        self._req("DELETE", f"{API}/files/emptyTrash", params={"supportsAllDrives": "true"})

    def drives(self, limit: int = 50) -> list[dict]:
        return self._req("GET", API + "/drives", params={"pageSize": max(1, min(int(limit), 100))}).get("drives", [])

    def create_shortcut(self, name: str, target_id: str, parent: str | None = None) -> dict:
        body: dict[str, Any] = {"name": (name or "Shortcut")[:200], "mimeType": SHORTCUT,
                                "shortcutDetails": {"targetId": target_id}}
        if parent:
            body["parents"] = [parent]
        return self._req("POST", API + "/files", params={"fields": FIELDS, "supportsAllDrives": "true"}, json=body)

    # ---------------- v0.999.186 DRIVE COMPLETE ----------------
    def raw_get(self, url: str, **params) -> Any:
        return self._req("GET", url, params=params or None)

    def call(self, method: str, url: str, **kw) -> Any:
        return self._req(method, url, **kw)

    def share_as(self, fid: str, body: dict, notify: bool | None = None, message: str = "",
                 transfer: bool = False) -> dict:
        """Any permission (user / group / domain / anyone, expiry, discovery, pendingOwner)."""
        params: dict[str, str] = {"supportsAllDrives": "true"}
        if body.get("type") in ("user", "group"):
            params["sendNotificationEmail"] = "false" if notify is False else "true"
            if message and notify is not False:
                params["emailMessage"] = message[:1000]
        if transfer:
            params["transferOwnership"] = "true"
        return self._req("POST", f"{API}/files/{fid}/permissions", params=params, json=body)

    def permission_patch(self, fid: str, pid: str, body: dict) -> dict:
        return self._req("PATCH", f"{API}/files/{fid}/permissions/{pid}", params={"supportsAllDrives": "true"},
                         json=body)

    def revision_media(self, fid: str, rid: str) -> bytes:
        return self._req("GET", f"{API}/files/{fid}/revisions/{rid}", raw=True,
                         params={"alt": "media", "supportsAllDrives": "true"})

    def revision_delete(self, fid: str, rid: str) -> None:
        self._req("DELETE", f"{API}/files/{fid}/revisions/{rid}", params={"supportsAllDrives": "true"})

    def download_op(self, fid: str, mime: str, revision: str = "", wait_s: float = 90.0) -> bytes:
        """files.download (a long-running operation): a Google file, or an older version of one, as bytes."""
        params = {"mimeType": mime}
        if revision:
            params["revisionId"] = revision
        op = self._req("POST", f"{API}/files/{fid}/download", params=params)
        waited = 0.0
        while not op.get("done"):
            if waited >= wait_s:
                raise DriveError("Google is still preparing this file; try again in a minute.")
            time.sleep(2.0)
            waited += 2.0
            op = self._req("GET", f"{API}/operations/{op.get('name', '')}")
        if op.get("error"):
            raise DriveError(f"Google could not prepare this file: {op['error'].get('message', '')}")
        uri = (op.get("response") or {}).get("downloadUri") or ""
        if not uri:
            raise DriveError("Google prepared the file but gave no download link.")
        return self._req("GET", uri, raw=True)

    def copy_as(self, fid: str, body: dict, ocr_language: str = "") -> dict:
        params = {"fields": FIELDS, "supportsAllDrives": "true"}
        if ocr_language:
            params["ocrLanguage"] = ocr_language
        return self._req("POST", f"{API}/files/{fid}/copy", params=params, json=body)

    def new_file(self, name: str, mime: str, parent: str | None = None) -> dict:
        body: dict[str, Any] = {"name": name, "mimeType": mime}
        if parent:
            body["parents"] = [parent]
        return self._req("POST", API + "/files", params={"fields": FIELDS, "supportsAllDrives": "true"}, json=body)

    # changes
    def start_token(self, drive_id: str = "") -> str:
        params = {"supportsAllDrives": "true"}
        if drive_id:
            params["driveId"] = drive_id
        return self._req("GET", API + "/changes/startPageToken", params=params).get("startPageToken", "")

    def changes_since(self, token: str, limit: int = 1000) -> tuple[list[dict], str]:
        """Changes after `token`; returns them and the token to use next time."""
        out: list[dict] = []
        tok = token
        while True:
            data = self._req("GET", API + "/changes", params={
                "pageToken": tok, "pageSize": 1000, "includeRemoved": "true", "includeItemsFromAllDrives": "true",
                "supportsAllDrives": "true", "spaces": "drive",
                "fields": f"nextPageToken,newStartPageToken,changes(changeType,removed,fileId,time,file({FIELDS}))"})
            out += data.get("changes", []) or []
            if data.get("newStartPageToken"):
                return out[:limit], data["newStartPageToken"]
            tok = data.get("nextPageToken") or ""
            if not tok or len(out) >= limit:
                return out[:limit], tok or token

    # shared drives
    def drive_create(self, name: str, request_id: str) -> dict:
        return self._req("POST", API + "/drives", params={"requestId": request_id}, json={"name": name})

    def drive_get(self, did: str) -> dict:
        return self._req("GET", f"{API}/drives/{did}")

    def drive_update(self, did: str, body: dict) -> dict:
        return self._req("PATCH", f"{API}/drives/{did}", json=body)

    def drive_delete(self, did: str) -> None:
        self._req("DELETE", f"{API}/drives/{did}")

    def drive_hide(self, did: str, hide: bool = True) -> dict:
        return self._req("POST", f"{API}/drives/{did}/{'hide' if hide else 'unhide'}")

    # access requests
    def proposals(self, fid: str) -> list[dict]:
        return self._pages(f"{API}/files/{fid}/accessproposals", {}, "accessProposals", 200)[0]

    def proposal_resolve(self, fid: str, pid: str, action: str, roles: list[str] | None = None,
                         notify: bool = True) -> dict:
        body: dict[str, Any] = {"action": action, "sendNotification": bool(notify)}
        if roles:
            body["role"] = roles
        return self._req("POST", f"{API}/files/{fid}/accessproposals/{pid}:resolve", json=body)

    # labels (Workspace)
    def labels(self, fid: str) -> list[dict]:
        return self._req("GET", f"{API}/files/{fid}/listLabels", params={"maxResults": 100}).get("labels", [])

    def labels_modify(self, fid: str, mods: list[dict]) -> dict:
        return self._req("POST", f"{API}/files/{fid}/modifyLabels",
                         json={"kind": "drive#modifyLabelsRequest", "labelModifications": mods})
