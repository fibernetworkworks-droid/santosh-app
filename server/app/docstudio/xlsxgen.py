"""v0.189.0 docstudio.xlsxgen - Excel line, ported from the Claude Code xlsx skill
(templates/base.py + engines/design.md + engines/chart.md):

  - one colour family per workbook (PRIMARY header + white text, warm zebra, totals row)
  - setup_sheet: gridlines off, margin column A, title at B2, spacer, header on row 4
  - values are TYPED: "1,234" -> 1234, "Rs 1,200.50"/"Rs 1,200.50" -> currency number, "12%" -> 0.12
    with percent format, "2024-05-01" -> real date (a spreadsheet of text-numbers is not a spreadsheet)
  - live-formula guarantee + zero error tolerance: divisions must carry IFERROR; dynamic-array
    functions (XLOOKUP/FILTER/UNIQUE/...) are REFUSED with the cell named (they break old Excel)
  - chart factories: gapWidth 80 / overlap 100 baked, titles built through rich text with the font
    baked into every run (Office + WPS render identically - a bare string title is WRONG)
  - auto-fit widths from data (wide scripts counted 1.8x), headers wrap instead of stretching
"""
from __future__ import annotations

import datetime as _dt
import io
import re
from copy import deepcopy
from typing import Any

from . import tokens

MAX_ROWS, MAX_COLS, MAX_SHEETS = 5000, 120, 20
_DYNAMIC = re.compile(r"\b(XLOOKUP|FILTER|UNIQUE|SORT|SORTBY|XMATCH|SEQUENCE|LET|LAMBDA|RANDARRAY)\s*\(",
                      re.IGNORECASE)
_NUM_CLEAN = re.compile(r"[,\s]")
_CURRENCY = ("\u20b9", "Rs", "rs", "Rs.", "$")
_PCT = re.compile(r"^-?\d+(?:\.\d+)?\s*%$")
_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DMY = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$")

# The designed sheet places headers on row 4 and data from column B (title band + margin column),
# but the model writes formulas / chart ranges on its own simple grid (header row 1, data from A2).
# One convention, one translation: every A1-style reference shifts +3 rows and +1 column.
ROW_SHIFT, COL_SHIFT = 3, 1
_A1REF = re.compile(r"(?<![A-Za-z0-9_!$])(\$?)([A-Z]{1,3})(\$?)(\d{1,7})(?![\d(])")
_A1COLS = re.compile(r"(?<![A-Za-z0-9_:!$])(\$?)([A-Z]{1,3})(\$?):(\$?)([A-Z]{1,3})(?![A-Za-z0-9_(])")


def _col_shift(col: str, d: int) -> str:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    n += d
    out = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out or "A"


def rebase_a1(text: str, drow: int = ROW_SHIFT, dcol: int = COL_SHIFT) -> str:
    """Shift a model-grid A1 reference / formula / range onto the designed sheet grid."""
    s = str(text or "")

    def col_sub(m):
        return f"{m.group(1)}{_col_shift(m.group(2), dcol)}{m.group(3)}:{m.group(4)}{_col_shift(m.group(5), dcol)}"

    def ref_sub(m):
        dc, col, dr, row = m.groups()
        return f"{dc}{_col_shift(col, dcol)}{dr}{max(1, int(row) + drow)}"
    s = _A1COLS.sub(col_sub, s)
    s = _A1REF.sub(ref_sub, s)
    return s


def _typed(value: Any) -> tuple[Any, str | None]:
    """Return (cell_value, number_format_or_None). Strings that fully parse become real values."""
    if value is None or isinstance(value, (int, float, bool)):
        return value, None
    s = str(value).strip()
    if not s or s.startswith("="):
        return s, None
    raw = s
    cur = next((c for c in _CURRENCY if raw.startswith(c)), None)
    body = raw[len(cur):].strip() if cur else raw
    neg = body.startswith("-")
    body_n = body.lstrip("-+").strip()
    if _PCT.match(raw):
        try:
            return float(raw.rstrip("% ").strip()) / 100.0, "0.0%"
        except ValueError:
            return raw, None
    if cur:
        cleaned = _NUM_CLEAN.sub("", body_n)
        if re.fullmatch(r"\d+(\.\d+)?", cleaned):
            return (-1 if neg else 1) * float(cleaned), ("\u20b9#,##0.00" if cur in ("\u20b9", "Rs", "rs", "Rs.") else "$#,##0.00")
    m = _DATE.match(raw) or _DMY.match(raw)
    if m:
        try:
            g = [int(x) for x in m.groups()]
            d = _dt.date(g[0], g[1], g[2]) if _DATE.match(raw) else _dt.date(g[2], g[1], g[0])
            return d, "YYYY-MM-DD"
        except ValueError:
            return raw, None
    cleaned = _NUM_CLEAN.sub("", raw)
    if re.fullmatch(r"-?\d+", cleaned):
        return int(cleaned), "#,##0"
    if re.fullmatch(r"-?\d*\.\d+", cleaned):
        return float(cleaned), "#,##0.00"
    return raw, None


def _guard_formulas(rows: list[list[Any]], sheet: str) -> tuple[int, list[str]]:
    """Zero error tolerance: name every dynamic-array formula; divisions need IFERROR."""
    used, warnings = 0, []
    for r_i, row in enumerate(rows, start=1):
        for c_i, cell in enumerate(row, start=1):
            if isinstance(cell, str) and cell.startswith("="):
                used += 1
                bad = _DYNAMIC.search(cell)
                if bad:
                    raise ValueError(
                        f"'{sheet}'!{r_i},{c_i}: {bad.group(1).upper()} purane Excel mein nahi chalta "
                        f"(dynamic array). SUMPRODUCT / INDEX+MATCH / COUNTIFS use kijiye.")
                if "/" in cell and "IFERROR" not in cell.upper():
                    warnings.append(f"'{sheet}'!{r_i},{c_i}: bina IFERROR ke division - zero se bachein")
    return used, warnings


# ---------------------------------------------------------------- chart title (font baked in)

def _chart_title(text: str, size_pt: float = 12, bold: bool = True, axis: bool = False,
                 font_name: str = "Calibri"):
    from openpyxl.chart.text import RichText, Text
    from openpyxl.chart.title import Title
    from openpyxl.drawing.text import (CharacterProperties, Font as DrawingFont, Paragraph,
                                       ParagraphProperties, RichTextProperties, RegularTextRun)
    rpr = CharacterProperties(latin=DrawingFont(typeface=font_name), ea=DrawingFont(typeface=font_name),
                              sz=int(size_pt * 100), b=bold)
    para = Paragraph(pPr=ParagraphProperties(defRPr=deepcopy(rpr)),
                     r=[RegularTextRun(rPr=deepcopy(rpr), t=str(text))])
    rich = RichText(bodyPr=RichTextProperties(rot=-5400000) if axis else RichTextProperties(), p=[para])
    if axis:  # outer txPr carries the rotation for Office; single run - WPS never stacks boxes
        return Title(tx=Text(rich=rich),
                     txPr=RichText(bodyPr=RichTextProperties(rot=-5400000),
                                   p=[Paragraph(pPr=ParagraphProperties(defRPr=deepcopy(rpr)))]))
    return Title(tx=Text(rich=rich))


def _apply_chart_colors(chart, colors_list: list[str]) -> None:
    for i, series in enumerate(chart.series):
        series.graphicalProperties.solidFill = colors_list[i % len(colors_list)]
        line = getattr(series.graphicalProperties, "line", None)
        if line is not None:
            line.solidFill = colors_list[i % len(colors_list)]


def _apply_pie_colors(chart, count: int, colors_list: list[str]) -> None:
    from openpyxl.chart.series import DataPoint
    for idx in range(count):
        pt = DataPoint(idx=idx)
        pt.graphicalProperties.solidFill = colors_list[idx % len(colors_list)]
        chart.series[0].data_points.append(pt)


def _add_chart(wb, ws, spec: dict, pal: dict, sheet_name: str, max_row: int) -> int:
    from openpyxl.chart import BarChart, LineChart, PieChart, Reference
    kind = str(spec.get("type", "bar")).lower()
    cats = rebase_a1(str(spec.get("categories", "")))            # model grid -> designed grid
    vals = rebase_a1(str(spec.get("values", "")))
    if not cats or not vals:
        raise ValueError(f"chart on '{sheet_name}': categories aur values dono chahiye (jaise B2:B4)")
    title = str(spec.get("title") or f"{kind.title()} chart")
    chart = BarChart() if kind in ("bar", "column") else LineChart() if kind == "line" else PieChart()
    if isinstance(chart, BarChart):
        chart.type = "col" if kind in ("bar", "column") else "bar"
        chart.grouping, chart.gapWidth, chart.overlap = "clustered", 80, 100   # thin-bar fix baked
    chart.style, chart.width, chart.height = 10, 18, 10
    data = Reference(ws, range_string=f"'{ws.title}'!{vals}")
    chart.add_data(data, titles_from_data=bool(spec.get("titles_from_data", False)))
    chart.set_categories(Reference(ws, range_string=f"'{ws.title}'!{cats}"))
    font = "Calibri"
    if kind == "pie":
        _apply_pie_colors(chart, max(1, len(str(vals).split(","))), pal["CHART_COLORS"])
    else:
        _apply_chart_colors(chart, pal["CHART_COLORS"])
    chart.title = _chart_title(title, 12, True, False, font)
    if spec.get("y_title"):
        chart.y_axis.title = _chart_title(str(spec["y_title"]), 10, False, True, font)
    if spec.get("x_title"):
        chart.x_axis.title = _chart_title(str(spec["x_title"]), 10, False, False, font)
    anchor = str(spec.get("anchor") or f"B{max_row + 3}")
    ws.add_chart(chart, anchor)
    return 1


# ---------------------------------------------------------------- build

def make_xlsx(title: str, sheets: dict[str, Any], *, charts: list[dict] | None = None,
              style: str | None = None) -> dict[str, Any]:
    """Build a designed workbook. Returns {data, sheets:[{name,rows,cols,headers}], formulas, charts, qa}."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    if not isinstance(sheets, dict) or not sheets:
        raise ValueError("sheets chahiye: {'Sheet1': [[header...], [row...], ...]}")
    pal = tokens.xlsx_palette(style)
    FONT = "Calibri"
    BOLD_HEADER = True
    wb = Workbook()
    wb.remove(wb.active)
    wb.properties.title = tokens.sanitize_text(title)[:200]
    wb.properties.creator = "Hoola Document Studio v0.189.0"

    def fill(hexs: str) -> PatternFill:
        return PatternFill("solid", fgColor=hexs)

    info, formulas, chart_count, warnings = [], 0, 0, []
    charts = [c for c in (charts or []) if isinstance(c, dict)][:12]
    for name, rows in list(sheets.items())[:MAX_SHEETS]:
        sname = re.sub(r"[\[\]:*?/\\]", " ", str(name))[:31].strip() or "Sheet"
        f_rows, f_charts = rows, [c for c in charts if str(c.get("sheet", "")) == str(name)]
        if isinstance(rows, dict) and "rows" in rows:
            f_rows, f_charts = rows["rows"], [c for c in charts if str(c.get("sheet", "")) == str(name)] + \
                ([rows["chart"]] if rows.get("chart") else [])
        f_rows = [r if isinstance(r, list) else [r] for r in (f_rows or [])][:MAX_ROWS]
        formulas_used, warns = _guard_formulas(f_rows, sname)
        formulas += formulas_used
        warnings += warns
        ws = wb.create_sheet(sname)
        ws.sheet_view.showGridLines = False
        ws.column_dimensions["A"].width = 3                     # margin column
        ws.row_dimensions[1].height = 15
        ws.row_dimensions[2].height = 32
        ws.row_dimensions[3].height = 8
        if title:
            ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=min(12, max(4, len(f_rows[0]) if f_rows else 4)))
            tcell = ws.cell(row=2, column=2, value=tokens.sanitize_text(str(title))[:120])
            tcell.font = Font(name=FONT, size=16, bold=BOLD_HEADER, color=pal["PRIMARY"])
            tcell.alignment = Alignment(horizontal="left", vertical="center")
        data_start = 4
        header_row = f_rows[0] if f_rows else []
        body = f_rows[1:] if f_rows else []
        for c_i, h in enumerate(header_row[:MAX_COLS], start=2):
            cell = ws.cell(row=data_start, column=c_i, value=tokens.sanitize_text(str(h)) if not isinstance(h, (int, float)) else h)
            cell.fill = fill(str(pal["PRIMARY"]))
            cell.font = Font(name=FONT, size=11, bold=BOLD_HEADER, color=pal["HEADER_TEXT"])
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(bottom=Side(style="thin", color=pal["NEUTRAL_200"]))
        ws.row_dimensions[data_start].height = 28
        widths = [tokens.display_width(h) for h in header_row[:MAX_COLS]]
        totals_at = None
        for r_i, row in enumerate(body):
            excel_row = data_start + 1 + r_i
            first = str(row[0]).strip().lower() if row and isinstance(row[0], str) else ""
            is_total = first in ("total", "total", "grand total", "subtotal", "sum", "kul", "yog")
            if is_total:
                totals_at = excel_row
            zebra = fill(pal["NEUTRAL_0"] if r_i % 2 == 0 else pal["NEUTRAL_100"])
            for c_i in range(len(header_row[:MAX_COLS])):
                raw = row[c_i] if c_i < len(row) else None
                val, fmt = _typed(raw)
                if isinstance(raw, str) and raw.startswith("="):
                    val = rebase_a1(raw)      # model grid -> designed grid
                cell = ws.cell(row=excel_row, column=c_i + 2, value=val)
                cell.fill = fill(str(pal["PRIMARY_LIGHT"])) if is_total else zebra
                cell.font = Font(name=FONT, size=11, bold=is_total,
                                 color=pal["PRIMARY"] if is_total else pal["NEUTRAL_900"])
                if is_total:
                    cell.border = Border(top=Side(style="medium", color=pal["NEUTRAL_200"]))
                if fmt:
                    cell.number_format = fmt
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif isinstance(val, (int, float)) and not isinstance(val, bool):
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif isinstance(val, _dt.date):
                    cell.number_format = "YYYY-MM-DD"
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                if cell.value is not None:
                    widths[c_i] = max(widths[c_i] if c_i < len(widths) else 0,
                                      tokens.display_width(str(val) if not isinstance(val, _dt.date) else val.isoformat()))
            ws.row_dimensions[excel_row].height = 22
        end_row = data_start + len(body)
        last_col_letter = get_column_letter(max(2, len(header_row) + 1))
        if body:
            ws.auto_filter.ref = f"B{data_start}:{last_col_letter}{end_row}"
            ws.freeze_panes = f"B{data_start + 1}"
        for i, w in enumerate(widths):
            letter = get_column_letter(i + 2)
            ws.column_dimensions[letter].width = min(46, max(9, w + 3))
            if header_row and i < len(header_row):
                if tokens.display_width(header_row[i]) > ws.column_dimensions[letter].width:
                    pass  # header already wraps (wrap_text on)
        for spec in f_charts[:3]:
            try:
                chart_count += _add_chart(wb, ws, spec, pal, sname, end_row)
            except Exception as e:
                warnings.append(f"chart on '{sname}' skipped: {e}")
        info.append({"name": sname, "rows": len(body), "cols": len(header_row),
                     "headers": [str(h) for h in header_row[:12]], "totals_row": totals_at})
    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()
    qa = _qa(data, info)
    qa["issues"] = (qa["issues"] or []) + warnings
    qa["status"] = "pass" if not qa["issues"] else "warn"
    return {"data": data, "sheets": info, "formulas": formulas, "charts": chart_count,
            "style": pal["STYLE"], "qa": qa}


def _qa(data: bytes, info: list[dict]) -> dict[str, Any]:
    issues: list[str] = []
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data))
        if len(wb.sheetnames) != len(info):
            issues.append("sheet count mismatch after re-open")
        empty = [s for s in wb.sheetnames if wb[s].max_row < 2]
        if empty:
            issues.append(f"empty sheets: {empty}")
    except Exception as e:
        issues.append(f"read-back failed: {type(e).__name__}")
    if len(data) > 25 * 1024 * 1024:
        issues.append("file over 25 MB")
    return {"status": "pass" if not issues else "warn", "issues": issues,
            "size_kb": round(len(data) / 1024, 1), "checked": ["re-open", "empty-sheets", "size"]}
