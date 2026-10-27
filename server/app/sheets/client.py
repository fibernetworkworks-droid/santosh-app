"""Google Sheets API v4 (+ Drive v3 for finding sheets by name), over plain HTTPS with a bearer token."""
from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import quote

import httpx

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
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

    def _req(self, method: str, url: str, **kw) -> Any:
        c = self._client or httpx.Client(timeout=40)
        try:
            for attempt in (0, 1):
                r = c.request(method, url, headers={"Authorization": f"Bearer {self._token(attempt == 1)}"}, **kw)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise SheetError(f"Google Sheets se baat nahi ho payi ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 403:
            if "has not been used" in r.text or "SERVICE_DISABLED" in r.text:
                raise SheetError("Google Cloud project mein Sheets / Drive API enable nahi hai.")
            if self.kind == "service":
                raise SheetError("Santosh ke paas is sheet ki permission nahi hai. Sheet ko service account ki email "
                                 "ke saath 'Editor' share kijiye, ya Profile > Google Sheets se apna Google account jodiye.")
            raise SheetError("Is sheet ki permission nahi hai (shayad kisi aur ki sheet hai jo aapke saath share nahi). "
                             "Ya Profile > Google Sheets se dobara jodiye.")
        if r.status_code == 404:
            raise SheetError("Yeh sheet nahi mili. Link / naam sahi hai?")
        if r.status_code >= 400:
            msg = r.text[:300]
            try:
                msg = r.json().get("error", {}).get("message", msg)
            except Exception:
                pass
            raise SheetError(f"Google Sheets: {msg}")
        return r.json() if r.content else {}

    # ---------------- finding ----------------
    def search(self, query: str = "", limit: int = 15) -> list[dict[str, Any]]:
        if not self.can_search:
            raise SheetError("Naam se dhoondhna is connection par nahi hota; sheet ka link dijiye.")
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
                      "sheets(properties(sheetId,title,index,gridProperties(rowCount,columnCount,frozenRowCount)))"})
        return {"id": res["spreadsheetId"], "title": res["properties"]["title"], "link": res.get("spreadsheetUrl", ""),
                "tabs": [{"id": s["properties"]["sheetId"], "title": s["properties"]["title"],
                          "rows": s["properties"].get("gridProperties", {}).get("rowCount", 0),
                          "cols": s["properties"].get("gridProperties", {}).get("columnCount", 0)}
                         for s in sorted(res.get("sheets", []), key=lambda s: s["properties"].get("index", 0))]}

    def values(self, sid: str, rng: str) -> list[list[Any]]:
        res = self._req("GET", f"{SHEETS}/{sid}/values/{quote(rng, safe='')}", params={
            "valueRenderOption": "UNFORMATTED_VALUE", "dateTimeRenderOption": "FORMATTED_STRING",
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
