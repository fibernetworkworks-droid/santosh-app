"""Google Drive / Sheets / Docs tools (scoped to what's shared with Santosh's service account)."""
from __future__ import annotations

from .. import gdrive
from .tools import Ctx, ToolError

GDRIVE_TOOLS = [
    {"name": "drive_find", "description": (
        "Find files in the user's shared Google Drive folder by name (or list recent when query is empty). "
        "Returns each file's id, name, type and link. Use the id with drive_read_file or sheet_read."),
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "drive_read_file", "description": "Read a file's text (Google Doc or text/csv). For a Google Sheet use sheet_read instead. id comes from drive_find.",
     "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}}, "required": ["file_id"]}},
    {"name": "sheet_read", "description": (
        "Read cells from a Google Sheet. Give the sheet id (from drive_find, or the long id in its URL). "
        "Default range is the first sheet's A1:Z200. First row is usually the header."),
     "input_schema": {"type": "object", "properties": {
         "spreadsheet_id": {"type": "string"},
         "range": {"type": "string", "description": "A1 notation, e.g. 'Sheet1!A1:D50' or 'Leads!A:F'. Optional."}},
         "required": ["spreadsheet_id"]}},
    {"name": "sheet_append", "description": (
        "Add a row (or rows) to the bottom of a Google Sheet. Give the values in column order matching the sheet. "
        "Confirm to the user what you added."),
     "input_schema": {"type": "object", "properties": {
         "spreadsheet_id": {"type": "string"},
         "values": {"type": "array", "items": {"type": "string"}, "description": "One row's cells, left to right"},
         "sheet_name": {"type": "string", "description": "Tab name (default Sheet1)"}},
         "required": ["spreadsheet_id", "values"]}},
    {"name": "doc_create", "description": "Create a new Google Doc with the given title and text, in the shared folder. Returns its link.",
     "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
                      "required": ["title"]}},
]

GDRIVE_LABELS = {"drive_find": "Drive mein dhoondh raha hoon", "drive_read_file": "File padh raha hoon",
                 "sheet_read": "Sheet padh raha hoon", "sheet_append": "Sheet mein row daal raha hoon",
                 "doc_create": "Doc bana raha hoon"}


def _require():
    if not gdrive.configured():
        raise ToolError("Google Drive abhi connect nahi hai. Server par service account key (GOOGLE_SA_FILE) set karke "
                        "ek folder Santosh ki service-account email ko share kijiye.")


async def drive_find(ctx: Ctx, query="", limit=15, **_):
    _require()
    try:
        files = await gdrive.find(query=str(query or ""), limit=int(limit or 15))
    except gdrive.DriveError as e:
        raise ToolError(str(e))
    return {"count": len(files), "files": files}


async def drive_read_file(ctx: Ctx, file_id, **_):
    _require()
    try:
        return await gdrive.read_file(str(file_id))
    except gdrive.DriveError as e:
        raise ToolError(str(e))


async def sheet_read(ctx: Ctx, spreadsheet_id, range=None, **_):
    _require()
    try:
        return await gdrive.sheet_read(str(spreadsheet_id), range)
    except gdrive.DriveError as e:
        raise ToolError(str(e))


async def sheet_append(ctx: Ctx, spreadsheet_id, values, sheet_name=None, **_):
    _require()
    if not isinstance(values, list) or not values:
        raise ToolError("values ek list honi chahiye (row ke cells).")
    try:
        return await gdrive.sheet_append(str(spreadsheet_id), [str(v) for v in values], sheet_name)
    except gdrive.DriveError as e:
        raise ToolError(str(e))


async def doc_create(ctx: Ctx, title, content="", **_):
    _require()
    try:
        return await gdrive.doc_create(str(title), str(content or ""))
    except gdrive.DriveError as e:
        raise ToolError(str(e))


GDRIVE_HANDLERS = {"drive_find": drive_find, "drive_read_file": drive_read_file, "sheet_read": sheet_read,
                   "sheet_append": sheet_append, "doc_create": doc_create}
