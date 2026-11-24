"""Google Sheets API v4 (+ Drive v3 for finding sheets by name), over plain HTTPS with a bearer token."""
from __future__ import annotations

import re
import time
from typing import Any, Callable
from urllib.parse import quote

import httpx

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
SCRIPT = "https://script.googleapis.com/v1"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
RETRIES = 5          # v0.999.185 tries when Google says "too many requests"
RETRY_WAIT = 1.0     # first wait in seconds, doubled each try (tests set it to 0)
DRIVE = "https://www.googleapis.com/drive/v3"
GSHEET = "application/vnd.google-apps.spreadsheet"


class SheetError(Exception):
    pass


class NotConnected(SheetError):
    pass


def a1_col(n: int) -> str:
    """1 -> A, 27 -> AA"""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - 64)
    return n


def q_tab(tab: str) -> str:
    """Quote a tab name for A1 notation: 'Sales 2026'!A1"""
    return "'" + tab.replace("'", "''") + "'"


ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]{20,})")


def id_from(text: str) -> str | None:
    m = ID_RE.search(text or "")
    if m:
        return m.group(1)
    t = (text or "").strip()
    return t if re.fullmatch(r"[a-zA-Z0-9_-]{30,}", t) else None


class SheetsClient:
    def __init__(self, key: str, address: str, token: Callable[[bool], str], kind: str = "google",
                 client: httpx.Client | None = None, can_search: bool = True) -> None:
        self.key = key
        self.address = (address or "").lower()
        self.kind = kind
        self._token = token
        self._client = client
        self.can_search = can_search

    def _req(self, method: str, url: str, raw: bool = False, extra_headers: dict | None = None, **kw) -> Any:
        c = self._client or httpx.Client(timeout=60)
        try:
            fresh, busy = False, 0
            while True:
                hd = {"Authorization": f"Bearer {self._token(fresh)}", **(extra_headers or {})}
                r = c.request(method, url, headers=hd, **kw)
                if r.status_code == 401 and not fresh:
                    fresh = True
                    continue
                # v0.999.185 Google's speed limit (about 60 changes a minute a person): wait and ask again, up to 5 times
                if r.status_code in (429, 500, 502, 503) and busy < RETRIES:
                    busy += 1
                    try:
                        wait = float(r.headers.get("retry-after") or 0)
                    except ValueError:
                        wait = 0.0
                    time.sleep(min(max(wait, RETRY_WAIT * (2 ** (busy - 1))), 32.0))
                    continue
                break
        except httpx.HTTPError as e:
            raise SheetError(f"Could not reach Google Sheets ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 429:
            raise SheetError("Google is limiting how fast Hoola can change this sheet (about 60 changes a minute). "
                             "Hoola waited and tried 5 times; try again in a minute.")
        if r.status_code == 403:
            low = r.text.lower()
            if "has not enabled the apps script api" in low or "apps script api has not been" in low:
                raise SheetError("Turn on 'Google Apps Script API' once at script.google.com/home/usersettings (signed in as "
                                 "this Google account), then ask again.")
            if "insufficient" in low and "scope" in low:
                need = ("Apps Script" if "script.googleapis.com" in url else "BigQuery" if "bigquery" in low
                        else "Drive" if "/drive/" in url else "Sheets")
                raise SheetError(f"Hoola needs Google {need} access for this. Open Connectors > Google, choose {need} and "
                                 "press Connect, then ask again.")
            if "has not been used" in r.text or "SERVICE_DISABLED" in r.text:
                raise SheetError("The Sheets / Drive API is not enabled in the Google Cloud project.")
            if self.kind == "service":
                raise SheetError("Hoola does not have permission for this sheet. Share the sheet with the service account's email "
                                 "as 'Editor', or link your Google account in Profile > Google Sheets.")
            raise SheetError("No permission for this sheet (it may be someone else's sheet that is not shared with you). "
                             "Or link again in Profile > Google Sheets.")
        if r.status_code == 404:
            raise SheetError("This sheet was not found. Are the link / name right?")
        if r.status_code >= 400:
            msg = r.text[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise SheetError(f"Google Sheets: {msg}")
        if raw:
            return r
        return r.json() if r.content else {}

    # ---------------- finding ----------------
    def search(self, query: str = "", limit: int = 15) -> list[dict[str, Any]]:
        if not self.can_search:
            raise SheetError("Finding by name does not work on this connection; give the sheet's link.")
        q = [f"mimeType = '{GSHEET}'", "trashed = false"]
        if query:
            q.append("name contains '" + query.replace("\\", " ").replace("'", " ") + "'")
        res = self._req("GET", DRIVE + "/files", params={
            "q": " and ".join(q), "orderBy": "modifiedTime desc", "pageSize": max(1, min(limit, 50)),
            "fields": "files(id,name,modifiedTime,webViewLink,owners(displayName,emailAddress))",
            "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"})
        return [{"id": f["id"], "title": f["name"], "modified": f.get("modifiedTime", "")[:10],
                 "link": f.get("webViewLink", ""),
                 "owner": ((f.get("owners") or [{}])[0].get("displayName") or "")} for f in res.get("files", [])]

    # ---------------- reading ----------------
    def meta(self, sid: str) -> dict[str, Any]:
        res = self._req("GET", f"{SHEETS}/{sid}", params={
            "fields": "spreadsheetId,properties(title,locale,timeZone),spreadsheetUrl,"
                      "sheets(properties(sheetId,title,index,hidden,tabColorStyle,"
                      "gridProperties(rowCount,columnCount,frozenRowCount)))"})
        return {"id": res["spreadsheetId"], "title": res["properties"]["title"], "link": res.get("spreadsheetUrl", ""),
                "locale": res["properties"].get("locale", ""), "time_zone": res["properties"].get("timeZone", ""),
                "tabs": [{"id": s["properties"]["sheetId"], "title": s["properties"]["title"],
                          "rows": s["properties"].get("gridProperties", {}).get("rowCount", 0),
                          "cols": s["properties"].get("gridProperties", {}).get("columnCount", 0),
                          "hidden": bool(s["properties"].get("hidden"))}
                         for s in sorted(res.get("sheets", []), key=lambda s: s["properties"].get("index", 0))]}

    def values(self, sid: str, rng: str, render: str = "UNFORMATTED_VALUE") -> list[list[Any]]:
        """render: UNFORMATTED_VALUE (numbers as numbers), FORMULA (what was typed, e.g. =SUM(B2:B9)) or
        FORMATTED_VALUE (as shown on screen, e.g. 'Rs 1,500.00')."""
        res = self._req("GET", f"{SHEETS}/{sid}/values/{quote(rng, safe='')}", params={
            "valueRenderOption": render, "dateTimeRenderOption": "FORMATTED_STRING",
            "majorDimension": "ROWS"})
        return res.get("values", [])

    def batch_values(self, sid: str, ranges: list[str]) -> list[list[list[Any]]]:
        res = self._req("GET", f"{SHEETS}/{sid}/values:batchGet",
                        params=[("ranges", r) for r in ranges] + [("valueRenderOption", "FORMATTED_VALUE")])
        return [vr.get("values", []) for vr in res.get("valueRanges", [])]

    # ---------------- writing ----------------
    def append(self, sid: str, rng: str, rows: list[list[Any]]) -> dict:
        return self._req("POST", f"{SHEETS}/{sid}/values/{quote(rng, safe='')}:append",
                         params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
                         json={"values": rows})

    def update(self, sid: str, data: list[dict]) -> dict:
        return self._req("POST", f"{SHEETS}/{sid}/values:batchUpdate",
                         json={"valueInputOption": "USER_ENTERED", "data": data})

    def batch(self, sid: str, requests: list[dict]) -> dict:
        return self._req("POST", f"{SHEETS}/{sid}:batchUpdate", json={"requests": requests})

    def clear(self, sid: str, ranges: list[str]) -> dict:
        """values.batchClear — wipes the values out of one or more A1 ranges (formatting stays)."""
        return self._req("POST", f"{SHEETS}/{sid}/values:batchClear", json={"ranges": ranges})

    def copy_tab(self, sid: str, sheet_id: int, dest_sid: str, new_title: str | None = None) -> dict:
        """sheets.copyTo — copies a tab to another (or the same) spreadsheet. Returns the new sheetId."""
        body: dict[str, Any] = {"destination_spreadsheet_id": dest_sid}
        if new_title:
            body["newTitle"] = new_title[:100]
        res = self._req("POST", f"{SHEETS}/{sid}/sheets/{sheet_id}:copyTo", json=body)
        return {"sheet_id": res.get("sheetId"), "title": res.get("title", ""),
                "spreadsheet_id": res.get("spreadsheetId", dest_sid)}

    def create(self, title: str, tabs: list[str]) -> dict:
        body = {"properties": {"title": title},
                "sheets": [{"properties": {"title": t, "gridProperties": {"frozenRowCount": 1}}} for t in tabs or ["Sheet1"]]}
        res = self._req("POST", SHEETS, json=body)
        return {"id": res["spreadsheetId"], "title": res["properties"]["title"], "link": res.get("spreadsheetUrl", ""),
                "tabs": [{"id": s["properties"]["sheetId"], "title": s["properties"]["title"]} for s in res.get("sheets", [])]}

    def share(self, sid: str, email: str, role: str) -> dict:
        return self._req("POST", f"{DRIVE}/files/{sid}/permissions",
                         params={"sendNotificationEmail": "true", "supportsAllDrives": "true"},
                         json={"type": "user", "role": role, "emailAddress": email})

    # ---------------- v0.999.184 SHEETS 100%: the rest of Sheets + the Drive side of a sheet ----------------
    def raw_meta(self, sid: str, fields: str) -> dict[str, Any]:
        """The spreadsheet with only the fields asked (charts, protected ranges, banding, filter views ...)."""
        return self._req("GET", f"{SHEETS}/{sid}", params={"fields": fields})

    def drive_patch(self, sid: str, body: dict) -> dict:
        return self._req("PATCH", f"{DRIVE}/files/{sid}", params={"supportsAllDrives": "true", "fields": "id,name,trashed"},
                         json=body)

    def permissions(self, sid: str) -> list[dict[str, Any]]:
        res = self._req("GET", f"{DRIVE}/files/{sid}/permissions", params={
            "supportsAllDrives": "true", "fields": "permissions(id,type,role,emailAddress,displayName,domain,deleted)"})
        return res.get("permissions", [])

    def permission_delete(self, sid: str, pid: str) -> dict:
        return self._req("DELETE", f"{DRIVE}/files/{sid}/permissions/{quote(pid, safe='')}",
                         params={"supportsAllDrives": "true"})

    def permission_update(self, sid: str, pid: str, role: str) -> dict:
        return self._req("PATCH", f"{DRIVE}/files/{sid}/permissions/{quote(pid, safe='')}",
                         params={"supportsAllDrives": "true"}, json={"role": role})

    def comments(self, sid: str) -> list[dict[str, Any]]:
        res = self._req("GET", f"{DRIVE}/files/{sid}/comments", params={
            "pageSize": "100", "includeDeleted": "false",
            "fields": "comments(id,content,createdTime,resolved,author(displayName,emailAddress),"
                      "quotedFileContent(value),replies(id,content,createdTime,action,author(displayName)))"})
        return res.get("comments", [])

    def comment_add(self, sid: str, text: str, quoted: str = "") -> dict:
        body: dict[str, Any] = {"content": text}
        if quoted:
            body["quotedFileContent"] = {"mimeType": "text/plain", "value": quoted}
        return self._req("POST", f"{DRIVE}/files/{sid}/comments", params={"fields": "id,content"}, json=body)

    def comment_reply(self, sid: str, cid: str, text: str, resolve: bool = False) -> dict:
        body: dict[str, Any] = {"content": text}
        if resolve:
            body["action"] = "resolve"
        return self._req("POST", f"{DRIVE}/files/{sid}/comments/{quote(cid, safe='')}/replies",
                         params={"fields": "id,content,action"}, json=body)

    # ---------------- v0.999.185 SHEETS COMPLETE: cells with their look, copies, versions, Apps Script ----------------
    def grid(self, sid: str, ranges: list[str], fields: str) -> dict[str, Any]:
        """spreadsheets.get with the cells of these ranges (only the fields asked)."""
        return self._req("GET", f"{SHEETS}/{sid}", params=[("ranges", r) for r in ranges]
                         + [("includeGridData", "true"), ("fields", fields)])

    def file_copy(self, sid: str, name: str) -> dict:
        return self._req("POST", f"{DRIVE}/files/{sid}/copy", params={"supportsAllDrives": "true",
                                                                      "fields": "id,name,webViewLink"}, json={"name": name})

    def revisions(self, sid: str) -> list[dict[str, Any]]:
        res = self._req("GET", f"{DRIVE}/files/{sid}/revisions", params={
            "pageSize": "200", "fields": "revisions(id,modifiedTime,lastModifyingUser(displayName,emailAddress),exportLinks)"})
        return res.get("revisions", [])

    def download(self, url: str) -> bytes:
        return self._req("GET", url, raw=True, follow_redirects=True).content

    def upload_as_sheet(self, name: str, data: bytes, mime: str) -> dict:
        """A file (an .xlsx) uploaded to her Drive as a new Google Sheet."""
        import json as _json
        import uuid
        b = "hoola" + uuid.uuid4().hex
        head = _json.dumps({"name": name, "mimeType": "application/vnd.google-apps.spreadsheet"}).encode()
        body = (f"--{b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode() + head
                + f"\r\n--{b}\r\nContent-Type: {mime}\r\n\r\n".encode() + data + f"\r\n--{b}--".encode())
        return self._req("POST", UPLOAD, params={"uploadType": "multipart", "fields": "id,name,webViewLink"}, content=body,
                         extra_headers={"Content-Type": f"multipart/related; boundary={b}"})

    def script_create(self, title: str, parent: str) -> dict:
        return self._req("POST", f"{SCRIPT}/projects", json={"title": title, "parentId": parent})

    def script_content(self, script_id: str) -> list[dict[str, Any]]:
        return self._req("GET", f"{SCRIPT}/projects/{quote(script_id, safe='')}/content").get("files", [])

    def script_save(self, script_id: str, files: list[dict]) -> dict:
        return self._req("PUT", f"{SCRIPT}/projects/{quote(script_id, safe='')}/content",
                         json={"scriptId": script_id, "files": files})
