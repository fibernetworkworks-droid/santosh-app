"""v0.195: Advanced copy/paste/cut engine.
- extract_tables: pull tables from a URL, HTML, or raw text.
- save_table: convert tables to xlsx / csv / markdown / html files.
- pc_clipboard: control PC clipboard via keyboard shortcuts (copy, paste, cut, select_all, read, write).
"""
from __future__ import annotations
import asyncio
import csv
import io
import logging
import uuid
from pathlib import Path

log = logging.getLogger("santosh.clipboard")
OUT_DIR = Path("static/generated")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------- conversion helpers ----------
def _html_to_tables(html: str) -> list[dict]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    tables = []
    for table in soup.find_all("table"):
        headers = []
        rows = []
        thead = table.find("thead")
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all("th")]
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            row = [c.get_text(strip=True) for c in cells]
            if not headers and tr.find("th"):
                headers = row
            else:
                rows.append(row)
        if rows:
            tables.append({"headers": headers, "rows": rows})
    return tables


def _text_to_table(text: str) -> dict:
    lines = [ln for ln in text.strip().split("\n") if ln.strip()]
    if not lines:
        return {"headers": [], "rows": []}
    delim = "\t"
    if "\t" not in lines[0]:
        if "," in lines[0]: delim = ","
        elif "|" in lines[0]: delim = "|"
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = [r for r in reader if r]
    if not rows:
        return {"headers": [], "rows": []}
    if len(rows) > 1 and all(c.strip().startswith("-") for c in rows[1]):
        return {"headers": [c.strip() for c in rows[0]], "rows": [[c.strip() for c in r] for r in rows[2:]]}
    return {"headers": [c.strip() for c in rows[0]], "rows": [[c.strip() for c in r] for r in rows[1:]]}


def _table_to_csv(headers, rows) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    if headers: w.writerow(headers)
    w.writerows(rows)
    return out.getvalue()


def _table_to_markdown(headers, rows) -> str:
    lines = []
    if headers:
        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _table_to_html(headers, rows) -> str:
    out = ['<table border="1" cellpadding="6" style="border-collapse:collapse;font-family:sans-serif;">']
    if headers:
        out.append("<tr>" + "".join(f"<th style='background:#1E3A5F;color:white;padding:8px'>{h}</th>" for h in headers) + "</tr>")
    for row in rows:
        out.append("<tr>" + "".join(f"<td style='padding:6px'>{c}</td>" for c in row) + "</tr>")
    out.append("</table>")
    return "".join(out)


def _table_to_xlsx(headers, rows, name="clipboard.xlsx") -> str:
    import xlsxwriter
    doc_id = str(uuid.uuid4())[:8]
    path = OUT_DIR / f"clip_{doc_id}_{name}"
    wb = xlsxwriter.Workbook(str(path))
    ws = wb.add_worksheet("Data")
    fmt = wb.add_format({"bold": True, "bg_color": "#1E3A5F", "font_color": "white", "border": 1})
    for i, h in enumerate(headers or []):
        ws.write(0, i, h, fmt)
    for r, row in enumerate(rows or [], start=1):
        for c, val in enumerate(row):
            ws.write(r, c, val)
    for i in range(len(headers or [])):
        ws.set_column(i, i, 15)
    ws.freeze_panes(1, 0)
    wb.close()
    return f"/static/generated/clip_{doc_id}_{name}"


# ---------- tool handlers ----------
async def extract_tables(ctx, url: str = "", text: str = "", **_):
    try:
        if url:
            import requests
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            tables = _html_to_tables(r.text)
            return {"ok": True, "source": url, "count": len(tables), "tables": tables}
        if text:
            tables = _html_to_tables(text) if "<table" in text.lower() else [_text_to_table(text)]
            return {"ok": True, "source": "text", "count": len(tables), "tables": tables}
        return {"ok": False, "error": "Provide url or text"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def save_table(ctx, headers: list | None = None, rows: list | None = None, format: str = "xlsx", name: str = "clipboard", **_):
    try:
        headers = headers or []
        rows = rows or []
        if format == "xlsx":
            return {"ok": True, "url": _table_to_xlsx(headers, rows, f"{name}.xlsx")}
        if format == "csv":
            doc_id = str(uuid.uuid4())[:8]
            path = OUT_DIR / f"clip_{doc_id}_{name}.csv"
            path.write_text(_table_to_csv(headers, rows), encoding="utf-8")
            return {"ok": True, "url": f"/static/generated/{path.name}"}
        if format == "markdown":
            return {"ok": True, "text": _table_to_markdown(headers, rows)}
        if format == "html":
            return {"ok": True, "text": _table_to_html(headers, rows)}
        return {"ok": False, "error": "format must be xlsx/csv/markdown/html"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def pc_clipboard(ctx, action: str, text: str = "", **_):
    try:
        from .pc_tools import PC_HANDLERS
        task_map = {
            "copy": "Press Ctrl+C to copy the currently selected text",
            "paste": "Press Ctrl+V to paste the clipboard content",
            "cut": "Press Ctrl+X to cut the currently selected text",
            "select_all": "Press Ctrl+A to select all",
            "read": "Read the current clipboard content and return it as plain text",
        }
        if action in task_map:
            return await PC_HANDLERS["pc_do"](ctx, task=task_map[action])
        if action == "write":
            if not text:
                return {"ok": False, "error": "text required for write"}
            return await PC_HANDLERS["pc_do"](ctx, task=f"Put this exact text into the clipboard and confirm: {text[:800]}")
        return {"ok": False, "error": "action must be copy/paste/cut/select_all/read/write"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


CLIPBOARD_TOOLS = [
    {"name": "extract_tables", "description": "Extract all tables from a URL, HTML string, or raw text (CSV/TSV/Markdown). Returns headers+rows for each table. Use this whenever the user says 'copy this table', 'get data from this page', or 'scrape the table at this URL'.", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "text": {"type": "string"}}}},
    {"name": "save_table", "description": "Save a table (headers + rows) as an Excel, CSV, Markdown, or HTML file. Use after extract_tables to hand the user a downloadable file.", "input_schema": {"type": "object", "properties": {"headers": {"type": "array", "items": {"type": "string"}}, "rows": {"type": "array", "items": {"type": "array"}}, "format": {"type": "string", "enum": ["xlsx", "csv", "markdown", "html"]}, "name": {"type": "string"}}, "required": ["format"]}},
    {"name": "pc_clipboard", "description": "Control the PC clipboard via keyboard shortcuts. Actions: copy (Ctrl+C), paste (Ctrl+V), cut (Ctrl+X), select_all (Ctrl+A), read (get clipboard text), write (put text into clipboard). Use this when the user says 'copy this', 'paste that', 'cut that row', or 'read my clipboard'.", "input_schema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["copy", "paste", "cut", "select_all", "read", "write"]}, "text": {"type": "string"}}, "required": ["action"]}},
]

CLIPBOARD_HANDLERS = {
    "extract_tables": extract_tables,
    "save_table": save_table,
    "pc_clipboard": pc_clipboard,
}

CLIPBOARD_LABELS = {
    "extract_tables": "Tables nikaal raha hoon",
    "save_table": "Table file bana raha hoon",
    "pc_clipboard": "Clipboard sambhal raha hoon",
}
