"""v0.999.114 ULTIMATE PC PLAN P3 - data without clicking, on Hoola PC (docs/HOOLA_ULTIMATE_PC_PLAN.md).

A spreadsheet, a Word file or a PDF is read and written as DATA, not by clicking through LibreOffice: one exact step
instead of dozens of screenshots, and nothing mis-typed into the wrong cell.
    read(path)                     -> text + tables (xlsx / xls via openpyxl, docx, pdf, csv, txt)
    sheet_write(path, rows|cells)  -> writes rows (a table) or single cells, keeps the rest of the workbook
    doc_fill(template, values)     -> a copy of a .docx with {{Name}} / [Name] blanks filled (format kept per run)
Paths are her folder only (agent._guard). Ideas from Goose's computer-controller (xlsx / docx tools) and Agent-S's code
agent; the code is Hoola's own."""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any

MAX_ROWS = 2000
MAX_COLS = 60


class DataError(Exception):
    pass


def _cell(v: Any) -> Any:
    if v is None:
        return ""
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def read(path: Path, max_chars: int = 20000, sheet: str = "") -> dict[str, Any]:
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        sheets = []
        for ws in wb.worksheets:
            if sheet and ws.title != sheet:
                continue
            rows = []
            for r in ws.iter_rows(values_only=True):
                if len(rows) >= MAX_ROWS:
                    break
                vals = [_cell(v) for v in r[:MAX_COLS]]
                while vals and vals[-1] == "":
                    vals.pop()
                rows.append(vals)
            while rows and not any(str(x) for x in rows[-1]):
                rows.pop()
            sheets.append({"name": ws.title, "rows": rows, "n_rows": len(rows)})
        wb.close()
        return {"kind": "sheet", "sheets": sheets}
    if ext == ".csv":
        text = path.read_text(errors="ignore")
        rows = [r[:MAX_COLS] for r in csv.reader(io.StringIO(text))][:MAX_ROWS]
        return {"kind": "sheet", "sheets": [{"name": path.stem, "rows": rows, "n_rows": len(rows)}]}
    if ext == ".docx":
        import docx
        d = docx.Document(str(path))
        text = "\n".join(p.text for p in d.paragraphs)
        tables = [[[c.text for c in row.cells][:MAX_COLS] for row in t.rows][:MAX_ROWS] for t in d.tables]
        return {"kind": "document", "text": text[:max_chars], "tables": tables}
    if ext == ".pdf":
        tables, pages = [], []
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                for pg in pdf.pages[:60]:
                    pages.append(pg.extract_text() or "")
                    for t in pg.extract_tables() or []:
                        tables.append([[_cell(c) for c in row][:MAX_COLS] for row in t][:MAX_ROWS])
        except ImportError:
            import pypdf
            for pg in pypdf.PdfReader(str(path)).pages[:60]:
                pages.append(pg.extract_text() or "")
        text = "\n\n".join(pages)
        return {"kind": "pdf", "text": text[:max_chars], "tables": tables[:20], "pages": len(pages),
                "scanned": not text.strip()}
    if ext in (".txt", ".md", ".json", ".xml", ".html", ".log"):
        return {"kind": "text", "text": path.read_text(errors="ignore")[:max_chars]}
    raise DataError(f"{ext or 'this file'} is not a file I read as data (xlsx, csv, docx, pdf, txt) - open it on screen")


_ADDR = re.compile(r"^([A-Za-z]{1,3})([1-9]\d{0,6})$")


def sheet_write(path: Path, rows: list | None = None, cells: dict | None = None, sheet: str = "",
                start: str = "A1", new: bool = False) -> dict[str, Any]:
    """rows = a table written from `start` down; cells = {"B4": 120, ...}. The rest of the workbook stays."""
    import openpyxl
    if path.suffix.lower() not in (".xlsx", ".xlsm"):
        raise DataError("sheet_write writes .xlsx files")
    if path.exists() and not new:
        wb = openpyxl.load_workbook(path)
    else:
        wb = openpyxl.Workbook()
        if sheet:
            wb.active.title = sheet[:31]
    ws = wb[sheet] if sheet and sheet in wb.sheetnames else (wb.create_sheet(sheet[:31]) if sheet else wb.active)
    n = 0
    if cells:
        for addr, v in list(cells.items())[:5000]:
            if not _ADDR.match(str(addr).strip()):
                raise DataError(f"'{addr}' is not a cell address like B4")
            ws[str(addr).strip().upper()] = v
            n += 1
    if rows:
        m = _ADDR.match(start or "A1")
        if not m:
            raise DataError(f"'{start}' is not a cell address like A1")
        from openpyxl.utils import column_index_from_string
        c0, r0 = column_index_from_string(m.group(1).upper()), int(m.group(2))
        for i, row in enumerate(rows[:MAX_ROWS]):
            for j, v in enumerate((row if isinstance(row, list) else [row])[:MAX_COLS]):
                ws.cell(row=r0 + i, column=c0 + j, value=v)
                n += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return {"written": n, "path": str(path), "sheet": ws.title}


_BLANK = re.compile(r"\{\{\s*([^{}]{1,60}?)\s*\}\}|\[([A-Za-z][A-Za-z0-9 _-]{0,40})\]")


def doc_fill(template: Path, out: Path, values: dict) -> dict[str, Any]:
    """Fill {{Name}} or [Name] blanks in a .docx (paragraphs + tables), keeping each run's format."""
    import docx
    if template.suffix.lower() != ".docx":
        raise DataError("doc_fill fills .docx templates")
    vals = {str(k).strip().lower(): str(v) for k, v in (values or {}).items()}
    d = docx.Document(str(template))
    filled, missing = set(), set()

    def sub(m):
        key = (m.group(1) or m.group(2) or "").strip()
        if key.lower() in vals:
            filled.add(key)
            return vals[key.lower()]
        missing.add(key)
        return m.group(0)

    def paras():
        yield from d.paragraphs
        for t in d.tables:
            for row in t.rows:
                for c in row.cells:
                    yield from c.paragraphs
    for p in paras():
        whole = "".join(r.text for r in p.runs)
        if not _BLANK.search(whole):
            continue
        new = _BLANK.sub(sub, whole)
        if p.runs:                       # the text goes into the first run (its format), the rest are emptied
            p.runs[0].text = new
            for r in p.runs[1:]:
                r.text = ""
    out.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(out))
    return {"path": str(out), "filled": sorted(filled), "left_blank": sorted(missing - filled)}
