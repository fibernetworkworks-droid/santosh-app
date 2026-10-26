"""v0.191.0 docstudio.xlsxgen - Excel line, ported from the Claude Code xlsx skill
(templates/base.py + engines/design.md + engines/chart.md), scaled to the owner's
"complex Excel, lakh columns, 100% coverage" directive:

  - one colour family per workbook (PRIMARY header + white text, warm zebra, totals row)
  - setup_sheet: gridlines off, margin column A, title at B2, spacer, header on row 4
  - values are TYPED: "1,234" -> 1234, "Rs 1,200.50" -> currency number, "12%" -> 0.12
    with percent format, "2024-05-01" -> real date (a spreadsheet of text-numbers is not a spreadsheet)
  - live-formula guarantee + zero error tolerance: divisions must carry IFERROR; dynamic-array
    functions (XLOOKUP/FILTER/UNIQUE/...) are REFUSED with the cell named (they break old Excel);
    the classic set is WELCOME: VLOOKUP/HLOOKUP/INDEX+MATCH, SUMIF(S)/COUNTIF(S)/AVERAGEIF(S),
    SUMPRODUCT, TEXT/DATE functions, SUBTOTAL, ROUND family, IF/AND/OR/IFS/SWITCH
  - AT SCALE (v0.191): MAX_COLS = 16,384 = Excel's own hard limit (XFD); a sheet asking for MORE
    is AUTO-SPLIT into 'Name-P1'..'Name-PN' parts (first column repeated as the row key on every
    part) plus an 'Index' sheet listing every part's column range - lakh-column datasets land in
    ONE workbook honestly, because the XLSX format itself cannot hold >16,384 cols in one sheet.
    MAX_ROWS = 100,000; anything clipped is a QA ISSUE, never silent (the v0.189 lie is dead).
  - BIG SHEETS switch strategies: >100K cells, >256 cols or >10K rows -> zebra becomes ONE
    conditional-formatting rule (MOD(ROW(),2)=0) instead of per-cell fills, row heights default,
    body fonts default - the build finishes in seconds, the look survives. Small sheets keep the
    exact v0.189 per-cell styling.
  - FULL COVERAGE extras per sheet (dict form): conditional_formatting (color_scale | data_bar |
    cell_is | expression), validation (list | number | date dropdowns/ranges), merges,
    defined_names - ranges rebased onto the designed grid like formulas.
  - chart factories: bar/column/line/pie PLUS scatter, area, doughnut, radar and combo
    (bar + line on a secondary axis); gapWidth 80 / overlap 100 baked, titles built through rich
    text with the font baked into every run (Office + WPS render identically)
  - auto-fit widths measured on the first 64 columns (16K measured widths = slow + pointless);
    wider sheets get sheet_format.defaultColWidth
  - pivot tables: honestly IMPOSSIBLE from Python (no library creates real pivots, openpyxl only
    preserves existing ones) - the studio's answer is a SUMIFS-matrix summary sheet, taught in prompts
"""
from __future__ import annotations

import datetime as _dt
import io
import re
from copy import deepcopy
from typing import Any

from . import tokens

MAX_ROWS, MAX_SHEETS = 100_000, 25
EXCEL_MAX_COLS = 16_384          # XLSX format's own limit (XFD) - nothing can exceed it
MAX_COLS = EXCEL_MAX_COLS
BIG_CELLS = 100_000              # above this: CF zebra + default heights/fonts (big mode)
WIDTH_MEASURE_COLS = 64          # auto-fit measured on the first N columns only
CHARTS_PER_SHEET, CHARTS_PER_BOOK = 6, 30
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
    """Zero error tolerance: name every dynamic-array formula; divisions need IFERROR.
    The classic set (VLOOKUP, INDEX+MATCH, SUMIFS, COUNTIFS, TEXT, DATE, SUBTOTAL, ...) is welcome."""
    used, warnings = 0, []
    for r_i, row in enumerate(rows, start=1):
        for c_i, cell in enumerate(row, start=1):
            if isinstance(cell, str) and cell.startswith("="):
                used += 1
                bad = _DYNAMIC.search(cell)
                if bad:
                    raise ValueError(
                        f"'{sheet}'!{r_i},{c_i}: {bad.group(1).upper()} purane Excel mein nahi chalta "
                        f"(dynamic array). VLOOKUP / INDEX+MATCH / SUMIFS / COUNTIFS use kijiye.")
                if "/" in cell and "IFERROR" not in cell.upper():
                    warnings.append(f"'{sheet}'!{r_i},{c_i}: bina IFERROR ke division - zero se bachein")
                if len(cell) > 8192:
                    warnings.append(f"'{sheet}'!{r_i},{c_i}: formula 8192 se lamba hai (Excel ki limit)")
    return used, warnings


def _cf_fill(hexs: str):
    from openpyxl.styles import PatternFill
    hexs = str(hexs).lstrip("#").upper()
    return PatternFill(start_color=hexs, end_color=hexs, fill_type="solid")


def _split_plan(name: str, n_cols: int) -> tuple[list[tuple[str, int, int]], bool]:
    """Wide-data plan: [(part_name, col_start, col_end_exclusive), ...], split_needed.
    Column 0 (the row key) repeats on every part; each part carries EXCEL_MAX_COLS-1 data cols."""
    if n_cols <= MAX_COLS:
        return [(str(name), 0, n_cols)], False
    span = MAX_COLS - 1
    n_parts = (n_cols - 1 + span - 1) // span
    base = re.sub(r"[\[\]:*?/\\]", " ", str(name))[:26].strip() or "Sheet"
    return [(f"{base}-P{p + 1}", 1 + p * span, min(n_cols, 1 + (p + 1) * span)) for p in range(n_parts)], True


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
    from openpyxl.chart import (AreaChart, BarChart, DoughnutChart, LineChart, PieChart,
                                RadarChart, Reference, ScatterChart, Series)
    kind = str(spec.get("type", "bar")).lower()
    cats = rebase_a1(str(spec.get("categories", "")))            # model grid -> designed grid
    vals = rebase_a1(str(spec.get("values", "")))
    if not cats or not vals:
        raise ValueError(f"chart on '{sheet_name}': categories aur values dono chahiye (jaise B2:B4)")
    title = str(spec.get("title") or f"{kind.title()} chart")
    if kind == "combo":
        return _add_combo_chart(ws, spec, pal, cats, vals, title, max_row)
    chart = (BarChart() if kind in ("bar", "column") else LineChart() if kind == "line"
             else PieChart() if kind == "pie" else AreaChart() if kind == "area"
             else DoughnutChart() if kind == "doughnut" else RadarChart() if kind == "radar"
             else ScatterChart())
    if isinstance(chart, BarChart):
        chart.type = "col" if kind in ("bar", "column") else "bar"
        chart.grouping, chart.gapWidth, chart.overlap = "clustered", 80, 100   # thin-bar fix baked
    if isinstance(chart, DoughnutChart):
        chart.holeSize = 58
    if isinstance(chart, RadarChart):
        chart.type = "marker"
    if isinstance(chart, ScatterChart):
        chart.scatterStyle = "marker"
        xref = Reference(ws, range_string=f"'{ws.title}'!{cats}")
        yref = Reference(ws, range_string=f"'{ws.title}'!{vals}")
        s = Series(yref, xref, title_from_data=bool(spec.get("titles_from_data", False)))
        s.marker.symbol = "circle"
        s.marker.size = 6
        s.graphicalProperties.line.noFill = True               # markers only, no connecting line
        chart.series.append(s)
        chart.style, chart.width, chart.height = 10, 18, 10
        chart.title = _chart_title(title, 12, True, False, "Calibri")
        if spec.get("y_title"):
            chart.y_axis.title = _chart_title(str(spec["y_title"]), 10, False, True, "Calibri")
        if spec.get("x_title"):
            chart.x_axis.title = _chart_title(str(spec["x_title"]), 10, False, False, "Calibri")
        ws.add_chart(chart, str(spec.get("anchor") or f"B{max_row + 3}"))
        return 1
    chart.style, chart.width, chart.height = 10, 18, 10
    data = Reference(ws, range_string=f"'{ws.title}'!{vals}")
    chart.add_data(data, titles_from_data=bool(spec.get("titles_from_data", False)))
    chart.set_categories(Reference(ws, range_string=f"'{ws.title}'!{cats}"))
    font = "Calibri"
    if kind in ("pie", "doughnut"):
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


def _add_combo_chart(ws, spec: dict, pal: dict, cats: str, vals: str, title: str, max_row: int) -> int:
    """Bar + line on a secondary axis: values = bar series, line_values = line series."""
    from openpyxl.chart import BarChart, LineChart, Reference
    line_vals = rebase_a1(str(spec.get("line_values", "")))
    if not line_vals:
        raise ValueError(f"combo chart on '{ws.title}': line_values chahiye (jaise E2:E5)")
    bar = BarChart()
    bar.type = str(spec.get("bar_type", "col"))
    bar.grouping, bar.gapWidth, bar.overlap = "clustered", 80, 100
    bar.add_data(Reference(ws, range_string=f"'{ws.title}'!{vals}"),
                 titles_from_data=bool(spec.get("titles_from_data", False)))
    bar.set_categories(Reference(ws, range_string=f"'{ws.title}'!{cats}"))
    _apply_chart_colors(bar, pal["CHART_COLORS"][:1] or pal["CHART_COLORS"])
    line = LineChart()
    line.add_data(Reference(ws, range_string=f"'{ws.title}'!{line_vals}"),
                  titles_from_data=bool(spec.get("titles_from_data", False)))
    line.y_axis.axId = 200
    line.y_axis.title = _chart_title(str(spec.get("line_title") or spec.get("y_title") or ""), 10, False, True, "Calibri") \
        if (spec.get("line_title") or spec.get("y_title")) else None
    line.y_axis.crosses = "max"                                 # secondary axis on the right
    _apply_chart_colors(line, (pal["CHART_COLORS"][1:] or pal["CHART_COLORS"])[:1])
    bar += line
    bar.style, bar.width, bar.height = 10, 18, 10
    bar.title = _chart_title(title, 12, True, False, "Calibri")
    if spec.get("y_title"):
        bar.y_axis.title = _chart_title(str(spec["y_title"]), 10, False, True, "Calibri")
    if spec.get("x_title"):
        bar.x_axis.title = _chart_title(str(spec["x_title"]), 10, False, False, "Calibri")
    ws.add_chart(bar, str(spec.get("anchor") or f"B{max_row + 3}"))
    return 1


# ---------------------------------------------------------------- build

def make_xlsx(title: str, sheets: dict[str, Any], *, charts: list[dict] | None = None,
              style: str | None = None) -> dict[str, Any]:
    """Build a designed workbook. Returns {data, sheets:[{name,rows,cols,headers}], formulas, charts,
    splits, conditional_formats, validations, defined_names, style, qa}.
    A sheet's value may be a plain row list or a dict: {rows, conditional_formatting, validation,
    merges, defined_names}. Sheets wider than Excel's own 16,384-col limit are auto-split into
    '-P1..-PN' parts (row key column repeated) plus an 'Index' sheet - never silently clipped."""
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
    wb.properties.creator = "Hoola Document Studio v0.191.0"

    def fill(hexs: str) -> PatternFill:
        return PatternFill("solid", fgColor=hexs)

    info, formulas, chart_count, warnings = [], 0, 0, []
    issues: list[str] = []                       # HARD facts (clipping) - never silent
    splits: list[dict] = []
    cf_count = dv_count = dn_count = 0
    charts = [c for c in (charts or []) if isinstance(c, dict)][:CHARTS_PER_BOOK]
    requested_sheets = list(sheets.items())
    if len(requested_sheets) > MAX_SHEETS:
        issues.append(f"{len(requested_sheets)} sheets maangi thi, {MAX_SHEETS} banayi (MAX_SHEETS) - baaki ka naam qa mein")
        warnings.append("baaki sheets: " + ", ".join(str(n) for n, _ in requested_sheets[MAX_SHEETS:])[:300])
    for name, rows in requested_sheets[:MAX_SHEETS]:
        extra: dict[str, Any] = {}
        if isinstance(rows, dict) and "rows" in rows:
            extra = {k: v for k, v in rows.items() if k != "rows"}
            rows = rows["rows"]
        f_rows = [r if isinstance(r, list) else [r] for r in (rows or [])]
        n_input_cols = max((len(r) for r in f_rows), default=0)
        plan, split_needed = _split_plan(str(name), n_input_cols)
        if len(f_rows) > MAX_ROWS:
            issues.append(f"'{name}': {len(f_rows):,} rows maangi thi, {MAX_ROWS:,} likhe (Excel ki safety limit) - "
                          f"baaki data ko agle sheet mein bhejiye")
            f_rows = f_rows[:MAX_ROWS]
        if split_needed:
            splits.append({"sheet": str(name), "cols": n_input_cols,
                           "parts": [p[0] for p in plan],
                           "note": f"{n_input_cols:,} cols ek sheet mein nahi aate - Excel ki own limit 16,384 hai; "
                                   f"{len(plan)} parts + Index bana, pehla column har part par row key hai"})
        for part_i, (sname, c0, c1) in enumerate(plan):
            part_rows = f_rows
            if split_needed:
                part_rows = []
                for r in f_rows:
                    key = r[0] if r else None
                    part_rows.append(([key] if c0 > 0 else []) + list(r[c0:c1]))
            formulas_used, warns = _guard_formulas(part_rows, sname)
            formulas += formulas_used
            warnings += warns
            ws = wb.create_sheet(sname)
            ws.sheet_view.showGridLines = False
            ws.column_dimensions["A"].width = 3                     # margin column
            ws.row_dimensions[1].height = 15
            ws.row_dimensions[2].height = 32
            ws.row_dimensions[3].height = 8
            if title:
                ws.merge_cells(start_row=2, start_column=2, end_row=2,
                               end_column=min(12, max(4, len(part_rows[0]) if part_rows else 4)))
                tcell = ws.cell(row=2, column=2, value=tokens.sanitize_text(str(title))[:120])
                tcell.font = Font(name=FONT, size=16, bold=BOLD_HEADER, color=pal["PRIMARY"])
                tcell.alignment = Alignment(horizontal="left", vertical="center")
            data_start = 4
            header_row = part_rows[0] if part_rows else []
            body = part_rows[1:] if part_rows else []
            n_cols = len(header_row)
            big = n_cols * max(1, len(body)) > BIG_CELLS or n_cols > 256 or len(body) > 10_000
            for c_i, h in enumerate(header_row[:MAX_COLS], start=2):
                cell = ws.cell(row=data_start, column=c_i,
                               value=tokens.sanitize_text(str(h)) if not isinstance(h, (int, float)) else h)
                cell.fill = fill(str(pal["PRIMARY"]))
                cell.font = Font(name=FONT, size=11, bold=BOLD_HEADER, color=pal["HEADER_TEXT"])
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = Border(bottom=Side(style="thin", color=pal["NEUTRAL_200"]))
            ws.row_dimensions[data_start].height = 28
            measure = min(n_cols, WIDTH_MEASURE_COLS)
            widths = [tokens.display_width(h) for h in header_row[:measure]]
            totals_at = None
            for r_i, row in enumerate(body):
                excel_row = data_start + 1 + r_i
                first = str(row[0]).strip().lower() if row and isinstance(row[0], str) else ""
                is_total = first in ("total", "total", "grand total", "subtotal", "sum", "kul", "yog")
                if is_total:
                    totals_at = excel_row
                zebra = fill(pal["NEUTRAL_0"] if r_i % 2 == 0 else pal["NEUTRAL_100"])
                for c_i in range(n_cols):
                    raw = row[c_i] if c_i < len(row) else None
                    val, fmt = _typed(raw)
                    if isinstance(raw, str) and raw.startswith("="):
                        val = rebase_a1(raw)      # model grid -> designed grid
                    cell = ws.cell(row=excel_row, column=c_i + 2, value=val)
                    if is_total or not big:
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
                    if cell.value is not None and c_i < measure:
                        widths[c_i] = max(widths[c_i] if c_i < len(widths) else 0,
                                          tokens.display_width(str(val) if not isinstance(val, _dt.date) else val.isoformat()))
                if not big:
                    ws.row_dimensions[excel_row].height = 22
            end_row = data_start + len(body)
            last_col_letter = get_column_letter(max(2, n_cols + 1))
            if body:
                ws.auto_filter.ref = f"B{data_start}:{last_col_letter}{end_row}"
                ws.freeze_panes = f"B{data_start + 1}"
            if big:                              # one CF rule instead of lakh per-cell fills
                from openpyxl.formatting.rule import FormulaRule
                ws.conditional_formatting.add(
                    f"B{data_start + 1}:{last_col_letter}{end_row}",
                    FormulaRule(formula=["MOD(ROW(),2)=0"], fill=_cf_fill(str(pal["NEUTRAL_100"]))))
                cf_count += 1
            if n_cols > WIDTH_MEASURE_COLS:
                ws.sheet_format.defaultColWidth = 11
            for i, w in enumerate(widths):
                letter = get_column_letter(i + 2)
                ws.column_dimensions[letter].width = min(46, max(9, w + 3))
            # ---- full-coverage extras (ranges rebased like formulas) ----
            for cf in (extra.get("conditional_formatting") or [])[:20]:
                if not isinstance(cf, dict):
                    continue
                rng = rebase_a1(str(cf.get("range", "")))
                if not rng:
                    continue
                ctype = str(cf.get("type", "")).lower()
                try:
                    from openpyxl.formatting.rule import (CellIsRule, ColorScaleRule,
                                                          DataBarRule, FormulaRule)
                    if ctype == "color_scale":
                        ws.conditional_formatting.add(rng, ColorScaleRule(
                            start_type=cf.get("start_type", "min"),
                            start_color=str(cf.get("start_color", pal["CHART_COLORS"][0])).lstrip("#"),
                            mid_type=cf.get("mid_type"), mid_color=str(cf["mid_color"]).lstrip("#") if cf.get("mid_color") else None,
                            end_type=cf.get("end_type", "max"),
                            end_color=str(cf.get("end_color", pal["CHART_COLORS"][-1])).lstrip("#")))
                    elif ctype == "data_bar":
                        ws.conditional_formatting.add(rng, DataBarRule(
                            start_type=cf.get("start_type", "num"), start_value=cf.get("start_value", 0),
                            end_type=cf.get("end_type", "max"), end_value=cf.get("end_value"),
                            color=str(cf.get("color", pal["CHART_COLORS"][0])).lstrip("#")))
                    elif ctype == "cell_is":
                        ws.conditional_formatting.add(rng, CellIsRule(
                            operator=str(cf.get("operator", "greaterThan")),
                            formula=[rebase_a1(str(f)) for f in (cf.get("formula") or [cf.get("formula", "0")])]
                            if isinstance(cf.get("formula"), list) else [rebase_a1(str(cf.get("formula", "0")))],
                            fill=_cf_fill(cf["fill"]) if cf.get("fill") else None,
                            font=Font(color=str(cf["font_color"]).lstrip("#")) if cf.get("font_color") else None))
                    elif ctype == "expression":
                        ws.conditional_formatting.add(rng, FormulaRule(
                            formula=[rebase_a1(str(f)) for f in (cf.get("formula") or ["0"])],
                            fill=_cf_fill(cf["fill"]) if cf.get("fill") else None))
                    else:
                        warnings.append(f"'{sname}': conditional_formatting type '{ctype}' nahi bani "
                                        f"(color_scale | data_bar | cell_is | expression)")
                        continue
                    cf_count += 1
                except Exception as e:
                    warnings.append(f"'{sname}' conditional_formatting skipped: {type(e).__name__}")
            for v in (extra.get("validation") or [])[:20]:
                if not isinstance(v, dict):
                    continue
                rng = rebase_a1(str(v.get("range", "")))
                vtype = str(v.get("type", "")).lower()
                if not rng or vtype not in ("list", "number", "whole", "date", "decimal", "textlength"):
                    warnings.append(f"'{sname}': validation needs range + type (list|number|whole|date|decimal|textlength)")
                    continue
                try:
                    from openpyxl.worksheet.datavalidation import DataValidation
                    f1 = str(v.get("formula1", ""))
                    if vtype == "date" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", f1):
                        y, m, d = (int(x) for x in f1.split("-"))
                        f1 = f"DATE({y},{m},{d})"
                    dv = DataValidation(type={"number": "decimal"}.get(vtype, vtype),
                                        formula1=f1, formula2=str(v["formula2"]) if v.get("formula2") else None,
                                        operator=v.get("operator"), allow_blank=True)
                    ws.add_data_validation(dv)
                    dv.add(rng)
                    dv_count += 1
                except Exception as e:
                    warnings.append(f"'{sname}' validation skipped: {type(e).__name__}")
            for m in (extra.get("merges") or [])[:20]:
                try:
                    ws.merge_cells(rebase_a1(str(m)))
                except Exception as e:
                    warnings.append(f"'{sname}' merge '{m}' skipped: {type(e).__name__}")
            for dn in (extra.get("defined_names") or [])[:20]:
                if not isinstance(dn, dict) or not dn.get("name") or not dn.get("ref"):
                    continue
                try:
                    from openpyxl.workbook.defined_name import DefinedName
                    dn_name = re.sub(r"[^A-Za-z0-9_.]", "_", str(dn["name"]))[:64]
                    if re.fullmatch(r"[A-Za-z]{1,3}\d+", dn_name):
                        dn_name = "N_" + dn_name        # a name that looks like a cell ref is illegal
                    wb.defined_names.add(DefinedName(dn_name, attr_text=f"'{sname}'!{rebase_a1(str(dn['ref']))}"))
                    dn_count += 1
                except Exception as e:
                    warnings.append(f"'{sname}' defined_name skipped: {type(e).__name__}")
            # ---- charts ----
            f_charts = [c for c in charts if str(c.get("sheet", "")) == str(name)]
            if isinstance(extra, dict) and extra.get("chart"):
                f_charts = f_charts + [extra["chart"]]
            for spec in f_charts[:CHARTS_PER_SHEET]:
                if split_needed and part_i > 0 and not spec.get("anchor"):
                    continue                            # unanchored charts land once, on -P1
                try:
                    chart_count += _add_chart(wb, ws, spec, pal, sname, end_row)
                except Exception as e:
                    warnings.append(f"chart on '{sname}' skipped: {e}")
            info.append({"name": sname, "rows": len(body), "cols": n_cols,
                         "headers": [str(h) for h in header_row[:12]], "totals_row": totals_at,
                         "big": big})
        if split_needed:                          # the Index sheet, right after the parts
            try:
                ws = wb.create_sheet("Index")
                ws.sheet_view.showGridLines = False
                ws.column_dimensions["A"].width = 3
                ws.row_dimensions[2].height = 32
                ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=6)
                tcell = ws.cell(row=2, column=2, value=tokens.sanitize_text(f"{title} - wide index")[:120])
                tcell.font = Font(name=FONT, size=16, bold=True, color=pal["PRIMARY"])
                idx_rows = [["Part sheet", "Columns", "From", "To", "Rows"]]
                for (pname, c0, c1) in plan:
                    idx_rows.append([pname, (c1 - c0) + (1 if c0 > 0 else 0),
                                     str(f_rows[0][c0]) if c0 < len(f_rows[0] or []) else c0,
                                     str(f_rows[0][c1 - 1]) if c1 - 1 < len(f_rows[0] or []) else c1,
                                     len(f_rows) - 1])
                for r_i, row in enumerate(idx_rows):
                    for c_i, v in enumerate(row):
                        cell = ws.cell(row=4 + r_i, column=2 + c_i, value=v)
                        if r_i == 0:
                            cell.fill = fill(str(pal["PRIMARY"]))
                            cell.font = Font(name=FONT, size=11, bold=True, color=pal["HEADER_TEXT"])
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                        else:
                            cell.fill = fill(pal["NEUTRAL_0"] if r_i % 2 == 0 else pal["NEUTRAL_100"])
                ws.column_dimensions["B"].width = 24
                for L in ("C", "D", "E", "F"):
                    ws.column_dimensions[L].width = 16
                info.append({"name": "Index", "rows": len(idx_rows) - 1, "cols": 5,
                             "headers": idx_rows[0], "totals_row": None, "big": False})
            except Exception as e:
                warnings.append(f"Index sheet skipped: {type(e).__name__}")
    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()
    qa = _qa(data, info)
    qa["issues"] = (qa["issues"] or []) + issues + warnings
    qa["status"] = "pass" if not qa["issues"] else "warn"
    return {"data": data, "sheets": info, "formulas": formulas, "charts": chart_count,
            "splits": splits, "conditional_formats": cf_count, "validations": dv_count,
            "defined_names": dn_count, "style": pal["STYLE"], "qa": qa}


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
