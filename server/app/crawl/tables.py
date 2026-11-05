"""Item 5: tables as DATA, not flattened text. Hand-built, zero upstream code (the port law).

The gap: Hoola's web lane has no table-structure extraction at all. `html_to_text` and the scrape lane
flatten a <table> into a run of words, so "Cement 50kg 380 410" arrives with no idea which number is the
old price and which the new. Her Data Desk (v0.238) can hold a real table; nothing could produce one from
a page.

Two problems to solve, and the second is the one that makes this worth building:

1. colspan / rowspan. A merged cell means the visual grid and the HTML rows disagree. Expanded here into a
   dense grid so column N is the same field on every row.
2. Most <table> elements on the web are LAYOUT, not data - a table used to position a logo and a menu. A
   scorer decides, because handing a layout table to the Data Desk as if it were a price list is worse
   than returning nothing.

Pure computation: lxml in, dict out. No network, no model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_WS = re.compile(r"\s+")
_NUMISH = re.compile(r"^[\s₹$€£]*-?[\d,]+(?:\.\d+)?\s*(?:%|kg|km|g|ml|l|rs|inr|usd|pcs?|units?)?\s*$", re.I)
_LAYOUT_HINT = re.compile(r"layout|wrapper|container|header|footer|nav|menu|banner|grid|spacer", re.I)
_DATA_HINT = re.compile(r"data|table|price|rate|spec|stat|result|score|compar|list|report|fee|chart", re.I)


@dataclass
class Table:
    """One extracted table. `rows` are aligned to `headers` when there are headers."""
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    caption: str = ""
    score: int = 0
    n_rows: int = 0
    n_cols: int = 0
    numeric_share: float = 0.0

    def as_dicts(self) -> list[dict]:
        """Rows keyed by header - what the Data Desk and a CSV want."""
        if not self.headers:
            return [{f"col{i + 1}": v for i, v in enumerate(r)} for r in self.rows]
        out = []
        for r in self.rows:
            out.append({(self.headers[i] if i < len(self.headers) and self.headers[i] else f"col{i + 1}"): v
                        for i, v in enumerate(r)})
        return out

    def as_csv(self) -> str:
        import csv
        import io
        buf = io.StringIO()
        w = csv.writer(buf)
        if self.headers:
            w.writerow(self.headers)
        w.writerows(self.rows)
        return buf.getvalue()


def _txt(el) -> str:
    return _WS.sub(" ", (el.text_content() or "")).strip()


def _grid(table) -> list[list[str]]:
    """Expand colspan / rowspan into a dense grid.

    The carry map holds cells still spanning DOWN from an earlier row: {column -> (text, rows_left)}. Without
    it, a rowspan silently shifts every later row one column left and the whole table is misaligned - which
    is the single most common way a scraped table is quietly wrong.
    """
    grid: list[list[str]] = []
    carry: dict[int, tuple[str, int]] = {}
    for tr in table.iter("tr"):
        cells = [c for c in tr if str(getattr(c, "tag", "")).lower() in ("td", "th")]
        if not cells:
            continue
        row: list[str] = []
        col = 0
        ci = 0
        while ci < len(cells) or col in carry:
            if col in carry:                      # a cell from an earlier row still occupies this column
                text, left = carry[col]
                row.append(text)
                if left - 1 <= 0:
                    del carry[col]
                else:
                    carry[col] = (text, left - 1)
                col += 1
                continue
            c = cells[ci]
            ci += 1
            text = _txt(c)
            try:
                cs = max(1, min(32, int(c.get("colspan") or 1)))
            except ValueError:
                cs = 1
            try:
                rs = max(1, min(256, int(c.get("rowspan") or 1)))
            except ValueError:
                rs = 1
            for k in range(cs):
                row.append(text)
                if rs > 1:
                    carry[col + k] = (text, rs - 1)
            col += cs
        grid.append(row)
    if not grid:
        return []
    width = max(len(r) for r in grid)
    return [r + [""] * (width - len(r)) for r in grid]


def _numeric_share(rows: list[list[str]]) -> float:
    cells = [c for r in rows for c in r if c]
    if not cells:
        return 0.0
    return sum(1 for c in cells if _NUMISH.match(c)) / float(len(cells))


def score_table(table, grid: list[list[str]]) -> int:
    """Is this a DATA table or a LAYOUT table? Higher is more data-like; the gate is >= 7.

    Signals, each worth what it is worth in practice rather than in theory: real <th> cells and a <thead>
    are the strongest evidence anyone intended a data table; nested tables and a layout-ish class are the
    strongest evidence against.
    """
    s = 0
    if table.find(".//th") is not None:
        s += 3
    if table.find(".//thead") is not None:
        s += 2
    if table.find(".//tbody") is not None:
        s += 1
    if table.find(".//caption") is not None:
        s += 2
    if table.get("summary"):
        s += 1
    rows, cols = len(grid), (max((len(r) for r in grid), default=0))
    if rows >= 3:
        s += 2
    if rows >= 6:
        s += 1
    if cols >= 2:
        s += 2
    if cols == 1:
        s -= 3                                     # a one-column table is a list, usually layout
    if rows <= 1:
        s -= 3
    share = _numeric_share(grid)
    if share >= 0.25:
        s += 2                                     # prices, rates, counts
    if share >= 0.55:
        s += 1
    # consistent row width is what a data table looks like
    if grid and len({len(r) for r in grid}) == 1 and cols >= 2:
        s += 1
    if table.find(".//table") is not None:
        s -= 4                                     # nested tables are a layout tell
    blob = f"{table.get('class') or ''} {table.get('id') or ''} {table.get('role') or ''}"
    if _LAYOUT_HINT.search(blob):
        s -= 3
    if _DATA_HINT.search(blob):
        s += 2
    if (table.get("role") or "").lower() == "presentation":
        s -= 6                                     # the author SAID it is not data
    if table.get("border") in ("0", None) and not blob.strip() and rows < 3:
        s -= 1
    return s


def _headers(grid: list[list[str]], table) -> tuple[list[str], list[list[str]]]:
    """Take the first row as headers only when it looks like one."""
    if not grid:
        return [], []
    first = grid[0]
    has_th = False
    for tr in table.iter("tr"):
        if any(str(getattr(c, "tag", "")).lower() == "th" for c in tr):
            has_th = True
        break
    looks = has_th or (_numeric_share([first]) < 0.2 and _numeric_share(grid[1:]) > 0.2
                       and all(c for c in first))
    if looks and len(grid) >= 2:
        return [c.strip() for c in first], grid[1:]
    return [], grid


def extract(html: str, min_score: int = 7, max_tables: int = 20, min_rows: int = 1) -> list[Table]:
    """Every data table on the page, best-scoring first. Layout tables are dropped, not returned weakly."""
    from lxml import html as LH
    try:
        root = LH.fromstring(html or "")
    except Exception:
        return []
    out: list[Table] = []
    for t in root.iter("table"):
        grid = _grid(t)
        if not grid:
            continue
        sc = score_table(t, grid)
        if sc < min_score:
            continue
        headers, rows = _headers(grid, t)
        rows = [r for r in rows if any(c.strip() for c in r)]
        if len(rows) < max(1, min_rows):
            continue
        cap = t.find(".//caption")
        out.append(Table(headers=headers, rows=rows, caption=(_txt(cap) if cap is not None else ""),
                         score=sc, n_rows=len(rows), n_cols=(max(len(r) for r in rows) if rows else 0),
                         numeric_share=round(_numeric_share(rows), 3)))
        if len(out) >= max_tables:
            break
    out.sort(key=lambda x: -x.score)
    return out
