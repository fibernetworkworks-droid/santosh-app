"""Google Drive / Sheets / Docs via a service account.

Santosh sees only what is shared with the service account's email (ideally one folder), so the user
controls its reach and can revoke by unsharing. All blocking Google API calls run in a thread.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os

from .config import get_settings

log = logging.getLogger("santosh.gdrive")

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
]
GDOC = "application/vnd.google-apps.document"
GSHEET = "application/vnd.google-apps.spreadsheet"
GFOLDER = "application/vnd.google-apps.folder"


class DriveError(Exception):
    pass


def configured(tenant_id: str | None = None) -> bool:
    st = get_settings()
    if tenant_id:
        try:
            from . import google_auth
            if google_auth.has_google(tenant_id):
                return True
        except Exception:
            pass
    if tenant_id and tenant_id != st.tenant_id:
        return False  # the service account / shared folder belongs to the server owner only
    return bool(st.google_sa_file and os.path.exists(st.google_sa_file)) or bool(st.google_sa_json.strip())


def _creds():
    from google.oauth2 import service_account
    st = get_settings()
    try:
        if st.google_sa_json.strip():
            import json
            return service_account.Credentials.from_service_account_info(json.loads(st.google_sa_json), scopes=SCOPES)
        return service_account.Credentials.from_service_account_file(st.google_sa_file, scopes=SCOPES)
    except Exception as e:
        raise DriveError(f"Service account key padhne mein dikkat: {e}")


def _svc(name, version, tenant_id: str | None = None):
    from googleapiclient.discovery import build
    creds = None
    if tenant_id:
        try:
            from . import google_auth
            if google_auth.has_google(tenant_id):
                creds = google_auth.credentials_for(tenant_id)
        except Exception as e:
            log.warning("per-user google creds failed (%s); falling back to service account: %s", tenant_id, e)
    if creds is None and tenant_id and tenant_id != get_settings().tenant_id:
        raise DriveError("Aapka Google Drive abhi connect nahi hai. App mein 'Sign in with Google' se jodiye.")
    return build(name, version, credentials=creds or _creds(), cache_discovery=False)


def _folder(tenant_id: str | None = None) -> str:
    st = get_settings()
    if tenant_id and tenant_id != st.tenant_id:
        return ""  # a signed-in user's own Drive: search all of it
    return st.google_drive_folder_id.strip()


# ---------------- Drive ----------------
def _find(query: str, limit: int, tenant_id=None):
    svc = _svc("drive", "v3", tenant_id)
    q_parts = ["trashed = false"]
    folder = _folder(tenant_id)
    if folder:
        q_parts.append(f"'{folder}' in parents")
    if query:
        safe = query.replace("'", " ").replace("\\", " ")
        q_parts.append(f"name contains '{safe}'")
    try:
        res = svc.files().list(q=" and ".join(q_parts), orderBy="modifiedTime desc", pageSize=max(1, min(limit, 30)),
                               fields="files(id,name,mimeType,modifiedTime,webViewLink,owners(displayName))",
                               supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    except Exception as e:
        raise DriveError(_explain(e))
    kinds = {GDOC: "Google Doc", GSHEET: "Google Sheet", GFOLDER: "Folder"}
    out = []
    for f in res.get("files", []):
        out.append({"id": f["id"], "name": f["name"], "type": kinds.get(f["mimeType"], f["mimeType"].split(".")[-1]),
                    "modified": f.get("modifiedTime", "")[:10], "link": f.get("webViewLink", "")})
    return out


def _read_file(file_id: str, tenant_id=None):
    from googleapiclient.http import MediaIoBaseDownload
    svc = _svc("drive", "v3", tenant_id)
    try:
        meta = svc.files().get(fileId=file_id, fields="id,name,mimeType,webViewLink", supportsAllDrives=True).execute()
    except Exception as e:
        raise DriveError(_explain(e))
    mime = meta["mimeType"]
    if mime == GSHEET:
        return {"name": meta["name"], "type": "sheet", "note": "Yeh ek Google Sheet hai; sheet_read se iske cells padhiye.",
                "id": file_id, "link": meta.get("webViewLink", "")}
    buf = io.BytesIO()
    try:
        if mime == GDOC:
            req = svc.files().export_media(fileId=file_id, mimeType="text/plain")
        elif mime.startswith("text/") or mime in ("application/json", "text/csv"):
            req = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
        else:
            return {"name": meta["name"], "type": mime, "link": meta.get("webViewLink", ""),
                    "note": "Yeh file text nahi hai (PDF/image/other); link se kholiye ya phone par bhejne ko kahiye."}
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
    except Exception as e:
        raise DriveError(_explain(e))
    text = buf.getvalue().decode("utf-8", errors="replace")
    return {"name": meta["name"], "type": "text", "link": meta.get("webViewLink", ""),
            "text": text[:14000], "truncated": len(text) > 14000}


# ---------------- Sheets ----------------
def _sheet_read(sid: str, cell_range: str | None, tenant_id=None):
    svc = _svc("sheets", "v4", tenant_id)
    rng = cell_range or "A1:Z200"
    try:
        res = svc.spreadsheets().values().get(spreadsheetId=sid, range=rng,
                                              valueRenderOption="UNFORMATTED_VALUE").execute()
    except Exception as e:
        raise DriveError(_explain(e))
    rows = res.get("values", [])
    header = rows[0] if rows else []
    return {"range": res.get("range", rng), "row_count": len(rows), "header": header,
            "rows": rows[:200]}


def _sheet_append(sid: str, values: list, sheet_name: str | None, tenant_id=None):
    svc = _svc("sheets", "v4", tenant_id)
    rng = (sheet_name or "Sheet1")
    body = {"values": values if values and isinstance(values[0], list) else [values]}
    try:
        res = svc.spreadsheets().values().append(spreadsheetId=sid, range=rng, valueInputOption="USER_ENTERED",
                                                 insertDataOption="INSERT_ROWS", body=body).execute()
    except Exception as e:
        raise DriveError(_explain(e))
    up = res.get("updates", {})
    return {"added_rows": up.get("updatedRows", len(body["values"])), "range": up.get("updatedRange", rng)}


# ---------------- Docs ----------------
def _doc_create(title: str, content: str, tenant_id=None):
    docs = _svc("docs", "v1", tenant_id)
    drive = _svc("drive", "v3", tenant_id)
    try:
        doc = docs.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        if content:
            docs.documents().batchUpdate(documentId=doc_id, body={
                "requests": [{"insertText": {"location": {"index": 1}, "text": content}}]}).execute()
        folder = _folder(tenant_id)
        if folder:
            # move it into the shared folder so the user sees it
            cur = drive.files().get(fileId=doc_id, fields="parents", supportsAllDrives=True).execute()
            drive.files().update(fileId=doc_id, addParents=folder,
                                 removeParents=",".join(cur.get("parents", [])), supportsAllDrives=True).execute()
        link = drive.files().get(fileId=doc_id, fields="webViewLink", supportsAllDrives=True).execute().get("webViewLink", "")
    except Exception as e:
        raise DriveError(_explain(e))
    return {"id": doc_id, "title": title, "link": link,
            "note": "" if (_folder(tenant_id) or (tenant_id and tenant_id != get_settings().tenant_id)) else "Tip: naya doc service account ke Drive mein bana; use dekhne ke liye folder share rakhiye (GOOGLE_DRIVE_FOLDER_ID)."}


def _explain(e) -> str:
    msg = str(e)
    from .google_auth import GoogleReconnect, reconnect_message
    if isinstance(e, GoogleReconnect):
        return msg
    if "invalid_grant" in msg or type(e).__name__ == "RefreshError":
        return reconnect_message("", msg)
    if "403" in msg or "permission" in msg.lower() or "insufficient" in msg.lower():
        return ("Santosh ke paas is file/folder ki permission nahi hai. Drive mein woh folder ya file service account ki "
                "email ko 'Editor' banakar share kijiye.")
    if "404" in msg or "notFound" in msg.lower():
        return "Yeh file nahi mili. id sahi hai? Aur kya woh Santosh ke saath share hai?"
    if "has not been used" in msg or "disabled" in msg.lower() or "SERVICE_DISABLED" in msg:
        return "Google Cloud project mein Drive/Sheets/Docs API enable nahi hai. Console mein teenon API enable kijiye."
    return f"Google Drive error: {msg[:200]}"


# ---------------- async wrappers ----------------
async def find(query="", limit=15, tenant_id=None):
    return await asyncio.to_thread(_find, query, limit, tenant_id)


async def read_file(file_id, tenant_id=None):
    return await asyncio.to_thread(_read_file, file_id, tenant_id)


async def sheet_read(sid, cell_range=None, tenant_id=None):
    return await asyncio.to_thread(_sheet_read, sid, cell_range, tenant_id)


async def sheet_append(sid, values, sheet_name=None, tenant_id=None):
    return await asyncio.to_thread(_sheet_append, sid, values, sheet_name, tenant_id)


async def doc_create(title, content="", tenant_id=None):
    return await asyncio.to_thread(_doc_create, title, content, tenant_id)
