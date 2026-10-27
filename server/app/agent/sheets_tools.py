"""Google Sheets tools: the user's own sheets (official Sheets API through Google sign-in; the server owner's
service account still works for sheets shared with it).

A sheet can be given by name ("sales sheet"), link or id; columns by their header names. Reading, asking, adding
rows, editing a few rows and creating sheets happen at once. Deleting rows, editing more than 20 rows and sharing
with people show a confirm card first.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..bazar.connectors.base import ToolError as BazarError
from ..events import bus
from ..sheets import service as ss
from ..sheets.client import NotConnected, SheetError
from .tools import Ctx, ToolError

SHEET = {"type": "string", "description": "The sheet: its name as the user says it, a Google Sheets link, or its id"}
TAB = {"type": "string", "description": "Tab name (default: the first tab)"}
WHERE = {"type": "array", "description": "Row conditions, all must match, e.g. [{column: 'City', op: '=', value: 'Pune'}, "
                                         "{column: 'Due', op: '>', value: 1000}]",
         "items": {"type": "object", "properties": {"column": {"type": "string"},
                                                    "op": {"type": "string", "enum": list(ss.OPS)},
                                                    "value": {}}, "required": ["column"]}}
ROWS_N = {"type": "array", "items": {"type": "integer"}, "description": "Sheet row numbers (the _row values)"}

SHEETS_TOOLS = [
    {"name": "sheets_find", "description": (
        "Find the user's Google Sheets by name (or list recent ones when query is empty). Returns id, title, link, "
        "last modified."),
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "sheet_info", "description": "A sheet's tabs and each tab's column names. Use first when unsure of the layout.",
     "input_schema": {"type": "object", "properties": {"spreadsheet": SHEET}, "required": ["spreadsheet"]}},
    {"name": "sheet_read", "description": (
        "Read rows of a sheet as {column: value} with _row numbers (100 at a time; offset to page). Or give an A1 range "
        "like 'B2:F20' for raw cells. For questions over the data (filters, totals, top 10) use sheet_query instead."),
     "input_schema": {"type": "object", "properties": {
         "spreadsheet": SHEET, "tab": TAB, "range": {"type": "string"}, "limit": {"type": "integer"},
         "offset": {"type": "integer"}, "header_row": {"type": "integer", "description": "Row with the column names (default 1)"},
         "spreadsheet_id": {"type": "string", "description": "(old name of spreadsheet)"}}}},
    {"name": "sheet_query", "description": (
        "Ask a question of a sheet, computed exactly by Santosh (not guessed): filter rows (where), sort (sort_by + "
        "descending), totals (sum / average / min / max of number columns), group_by a column (counts and sums per "
        "group). E.g. 'Pune ke customers jinka due 1000 se zyada hai', 'har salesman ki total sale'."),
     "input_schema": {"type": "object", "properties": {
         "spreadsheet": SHEET, "tab": TAB, "where": WHERE, "sort_by": {"type": "string"}, "descending": {"type": "boolean"},
         "totals": {"type": "array", "items": {"type": "string"}, "description": "Number columns to total"},
         "group_by": {"type": "string"}, "limit": {"type": "integer", "description": "Rows to return (default 50)"},
         "header_row": {"type": "integer"}}, "required": ["spreadsheet"]}},
    {"name": "sheet_append", "description": (
        "Add rows at the bottom of a sheet. Give each row as {column name: value} (matched to the header) or as a list "
        "in column order. Formulas like =SUM(B2:B9) and dates work. add_columns=true adds new header columns when needed."),
     "input_schema": {"type": "object", "properties": {
         "spreadsheet": SHEET, "tab": TAB,
         "rows": {"type": "array", "items": {}, "description": "Rows: objects {column: value} or lists"},
         "values": {"type": "array", "items": {}, "description": "(one row as a list; old style)"},
         "add_columns": {"type": "boolean"}, "spreadsheet_id": {"type": "string"}, "sheet_name": {"type": "string"}}}},
    {"name": "sheet_update", "description": (
        "Change cells in matching rows: set = {column: new value}, rows chosen by where (conditions) or rows (row "
        "numbers). E.g. mark Sharma Traders as Paid. Up to 20 rows change at once; more need the user's tap on a card."),
     "input_schema": {"type": "object", "properties": {
         "spreadsheet": SHEET, "tab": TAB, "set": {"type": "object"}, "where": WHERE, "rows": ROWS_N,
         "header_row": {"type": "integer"}}, "required": ["spreadsheet", "set"]}},
    {"name": "sheet_write_range", "description": (
        "Write a block of cells at an A1 range (e.g. 'E1' or 'Summary!A1'), values as rows of cells. For formulas, "
        "headers, small tables. Max 2000 cells."),
     "input_schema": {"type": "object", "properties": {
         "spreadsheet": SHEET, "tab": TAB, "range": {"type": "string"},
         "values": {"type": "array", "items": {"type": "array", "items": {}}}}, "required": ["spreadsheet", "range", "values"]}},
    {"name": "sheet_delete_rows", "description": (
        "Delete rows (by where conditions or row numbers). Always shows the user a confirm card with the rows first."),
     "input_schema": {"type": "object", "properties": {
         "spreadsheet": SHEET, "tab": TAB, "where": WHERE, "rows": ROWS_N, "header_row": {"type": "integer"}},
         "required": ["spreadsheet"]}},
    {"name": "sheet_create", "description": (
        "Create a new Google Sheet in the user's Drive, with tabs, a header row and optional rows (objects or lists). "
        "Or import an Excel / CSV: source = {email_id, attachment_id} (from an email) or {file_id} (PC / phone file). "
        "Returns the link and shows a card in the chat."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "tabs": {"type": "array", "items": {"type": "object", "properties": {
             "name": {"type": "string"}, "header": {"type": "array", "items": {"type": "string"}},
             "rows": {"type": "array", "items": {}}}}},
         "source": {"type": "object", "properties": {"email_id": {"type": "string"}, "attachment_id": {"type": "string"},
                                                     "file_id": {"type": "string"}}}},
         "required": ["title"]}},
    {"name": "sheet_add_tab", "description": "Add a new tab to a sheet, optionally with a header row.",
     "input_schema": {"type": "object", "properties": {"spreadsheet": SHEET, "name": {"type": "string"},
                                                       "header": {"type": "array", "items": {"type": "string"}}},
                      "required": ["spreadsheet", "name"]}},
    {"name": "sheet_export", "description": (
        "Turn a sheet into an Excel (.xlsx, all tabs) or CSV (one tab) file and send it to the user's phone. The result "
        "has a file_id you can attach to an email (email_draft attachments [{file_id}])."),
     "input_schema": {"type": "object", "properties": {"spreadsheet": SHEET, "tab": TAB,
                                                       "format": {"type": "string", "enum": ["xlsx", "csv"]}},
                      "required": ["spreadsheet"]}},
    {"name": "sheet_share", "description": (
        "Share a sheet with people (emails or names). role: reader (view) or writer (edit). They get a Google email, so "
        "the user confirms on a card first."),
     "input_schema": {"type": "object", "properties": {"spreadsheet": SHEET, "people": {"type": "array", "items": {"type": "string"}},
                                                       "role": {"type": "string", "enum": ["reader", "writer"]}},
                      "required": ["spreadsheet", "people"]}},
]

SHEETS_LABELS = {"sheets_find": "Sheet dhoondh raha hoon", "sheet_info": "Sheet dekh raha hoon",
                 "sheet_read": "Sheet padh raha hoon", "sheet_query": "Sheet mein hisaab laga raha hoon",
                 "sheet_append": "Sheet mein row daal raha hoon", "sheet_update": "Sheet badal raha hoon",
                 "sheet_write_range": "Cells likh raha hoon", "sheet_delete_rows": "Delete ki manzoori le raha hoon",
                 "sheet_create": "Nayi sheet bana raha hoon", "sheet_add_tab": "Naya tab bana raha hoon",
                 "sheet_export": "Sheet ki file bana raha hoon", "sheet_share": "Share ki manzoori le raha hoon"}


async def _t(fn, *a, **kw):
    try:
        return await asyncio.to_thread(fn, *a, **kw)
    except NotConnected as e:
        raise ToolError(str(e))
    except SheetError as e:
        raise ToolError(str(e))


def _card(ctx: Ctx, pid: str) -> dict[str, Any]:
    from ..bazar import service
    try:
        out = service.run(ctx.tenant_id, ctx.conversation_id, "santosh-sheets", "confirm_change", {"pending_id": pid})
    except BazarError as e:
        raise ToolError(str(e))
    return {k: v for k, v in out.items() if k in ("needs_approval", "approval_id", "card", "say")}


def _sheet_arg(spreadsheet, spreadsheet_id):
    s = spreadsheet or spreadsheet_id
    if not s:
        raise ToolError("Kaunsi sheet? spreadsheet (naam, link ya id) do.")
    return str(s)


def _card_event(ctx: Ctx, title: str, link: str, sid: str, status: str, extra: dict | None = None) -> None:
    bus.publish(ctx.conversation_id, "sheet", {"id": sid, "title": title, "link": link, "status": status, **(extra or {})})


async def sheets_find(ctx: Ctx, query="", limit=15, **_):
    return await _t(ss.find, ctx.tenant_id, str(query or ""), int(limit or 15))


async def sheet_info(ctx: Ctx, spreadsheet, **_):
    return await _t(ss.info, ctx.tenant_id, str(spreadsheet))


async def sheet_read(ctx: Ctx, spreadsheet=None, tab=None, range=None, limit=100, offset=0, header_row=1,
                     spreadsheet_id=None, **_):
    return await _t(ss.read, ctx.tenant_id, _sheet_arg(spreadsheet, spreadsheet_id), tab, range, int(limit or 100),
                    int(offset or 0), int(header_row or 1))


async def sheet_query(ctx: Ctx, spreadsheet, tab=None, where=None, sort_by=None, descending=False, totals=None,
                      group_by=None, limit=50, header_row=1, **_):
    return await _t(ss.query, ctx.tenant_id, str(spreadsheet), tab, where or [], sort_by, bool(descending), totals or [],
                    group_by, int(limit if limit is not None else 50), int(header_row or 1))


async def sheet_append(ctx: Ctx, spreadsheet=None, tab=None, rows=None, values=None, add_columns=False,
                       spreadsheet_id=None, sheet_name=None, **_):
    if not rows and values:
        rows = [values] if not isinstance(values[0], list) else values
    out = await _t(ss.append, ctx.tenant_id, _sheet_arg(spreadsheet, spreadsheet_id), rows or [], tab or sheet_name,
                   bool(add_columns))
    return out


async def sheet_update(ctx: Ctx, spreadsheet, set, where=None, rows=None, tab=None, header_row=1, **_):
    def work():
        plan = ss.plan_update(ctx.tenant_id, str(spreadsheet), dict(set or {}), where or [], rows or [], tab, int(header_row or 1))
        c, meta = plan["client"], plan["meta"]
        if len(plan["rows"]) > ss.BIG_UPDATE:
            lines = [f"Row {b['_row']}: " + ", ".join(f"{k}={v}" for k, v in list(b.items())[1:4]) for b in plan["before"][:5]]
            pid = ss.pend(ctx.tenant_id, ctx.conversation_id, "update",
                          {"account": c.key, "sid": meta["id"], "data": plan["data"], "rows": plan["rows"], "link": meta["link"]},
                          {"title": meta["title"], "tab": plan["tab"],
                           "lines": [f"{len(plan['rows'])} rows mein: " + ", ".join(f"{k} → {v}" for k, v in plan["set"].items())] + lines,
                           "more": max(0, len(plan["rows"]) - 5)})
            return {"pending_id": pid}
        n = ss.do_update(c, meta["id"], plan["data"])
        return {"title": meta["title"], "tab": plan["tab"], "rows": plan["rows"], "set": plan["set"], "updated_cells": n,
                "link": meta["link"]}
    res = await _t(work)
    if "pending_id" in res:
        card = await asyncio.to_thread(_card, ctx, res["pending_id"])
        return {**card, "status": "needs_approval",
                "note": f"More than {ss.BIG_UPDATE} rows: a confirm card is in the chat; nothing changed yet."}
    return res


async def sheet_write_range(ctx: Ctx, spreadsheet, range, values, tab=None, **_):
    return await _t(ss.write_range, ctx.tenant_id, str(spreadsheet), str(range), values or [], tab)


async def sheet_delete_rows(ctx: Ctx, spreadsheet, tab=None, where=None, rows=None, header_row=1, **_):
    def work():
        plan = ss.plan_delete(ctx.tenant_id, str(spreadsheet), where or [], rows or [], tab, int(header_row or 1))
        c, meta = plan["client"], plan["meta"]
        lines = [f"Row {b['_row']}: " + ", ".join(f"{k}={v}" for k, v in list(b.items())[1:4]) for b in plan["before"][:6]]
        return ss.pend(ctx.tenant_id, ctx.conversation_id, "delete",
                       {"account": c.key, "sid": meta["id"], "tab": plan["tab"], "tab_id": plan["tab_id"],
                        "rows": plan["rows"], "before": plan["before"], "header_row": int(header_row or 1),
                        "link": meta["link"]},
                       {"title": meta["title"], "tab": plan["tab"], "lines": [f"{len(plan['rows'])} rows hatengi"] + lines,
                        "more": max(0, len(plan["rows"]) - 6),
                        "note": "Google Sheets ki Version history se wapas la sakte hain."})
    pid = await _t(work)
    card = await asyncio.to_thread(_card, ctx, pid)
    return {**card, "status": "needs_approval", "note": "Confirm card with the rows is in the chat; nothing deleted yet."}


async def sheet_create(ctx: Ctx, title, tabs=None, source=None, **_):
    def work():
        t = tabs
        src = ""
        if source:
            rows, src = ss.import_rows(ctx.tenant_id, dict(source))
            t = [{"name": "Sheet1", "header": [str(h) for h in rows[0]], "rows": rows[1:]}]
        return ss.create(ctx.tenant_id, str(title), t), src
    out, src = await _t(work)
    _card_event(ctx, out["title"], out["link"], out["id"], "created", {"tabs": out["tabs"]})
    return {**out, **({"imported_from": src} if src else {}), "note": "A card with the link is in the chat."}


async def sheet_add_tab(ctx: Ctx, spreadsheet, name, header=None, **_):
    return await _t(ss.add_tab, ctx.tenant_id, str(spreadsheet), str(name), [str(h) for h in header or []])


async def sheet_export(ctx: Ctx, spreadsheet, tab=None, format="xlsx", **_):
    def work():
        from ..mailbox import service as ms
        from ..pc import service as pcs
        name, data, meta = ss.export(ctx.tenant_id, str(spreadsheet), tab, "csv" if format == "csv" else "xlsx")
        row = ms.store_bytes(ctx.tenant_id, name, data, "to_phone")
        return name, len(data), pcs.public_file(row), meta
    name, size, view, meta = await _t(work)
    bus.publish(ctx.conversation_id, "pc_file", {**view, "source": "sheets"})
    return {"file": name, "size": size, "file_id": view["file_id"], "title": meta["title"],
            "note": "Download card is in the chat. To email it: email_draft with attachments [{file_id}]."}


async def sheet_share(ctx: Ctx, spreadsheet, people, role="reader", **_):
    def work():
        from ..mailbox import contacts
        addrs, problems = contacts.resolve(ctx.tenant_id, ", ".join(str(p) for p in people or []))
        if problems:
            raise SheetError(" ".join(problems))
        emails = [a.strip() for a in addrs.split(",") if a.strip()]
        if not emails:
            raise SheetError("Kisko share karna hai?")
        c, meta = ss.resolve(ctx.tenant_id, str(spreadsheet))
        r = "writer" if role == "writer" else "reader"
        return ss.pend(ctx.tenant_id, ctx.conversation_id, "share",
                       {"account": c.key, "sid": meta["id"], "emails": emails, "role": r, "link": meta["link"]},
                       {"title": meta["title"], "lines": [("Edit" if r == "writer" else "Sirf dekh") + " sakenge: " + ", ".join(emails)],
                        "note": "Unhe Google se email jayega."})
    pid = await _t(work)
    card = await asyncio.to_thread(_card, ctx, pid)
    return {**card, "status": "needs_approval"}


SHEETS_HANDLERS = {"sheets_find": sheets_find, "sheet_info": sheet_info, "sheet_read": sheet_read,
                   "sheet_query": sheet_query, "sheet_append": sheet_append, "sheet_update": sheet_update,
                   "sheet_write_range": sheet_write_range, "sheet_delete_rows": sheet_delete_rows,
                   "sheet_create": sheet_create, "sheet_add_tab": sheet_add_tab, "sheet_export": sheet_export,
                   "sheet_share": sheet_share}
