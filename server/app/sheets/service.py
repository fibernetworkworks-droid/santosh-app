"""Santosh's Google Sheets work. Blocking; tools run it in a thread.

A sheet can be named the way the user says it ("meri sales sheet"), by link, or by id. Columns are used by their
header names. Adding rows, editing a few rows and creating sheets happen at once; deleting rows, editing many rows
and sharing with other people wait for the user's tap on a confirm card.
"""
from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select

from ..db import SheetsPending, SheetsRecent, now, session
from ..events import bus
from .accounts import clients, get_client
from .client import SHEETS, SheetError, SheetsClient, a1_col, col_index, id_from, q_tab

BIG_UPDATE = 20          # editing more rows than this needs a tap
MAX_ROWS = 5000
OPS = ("=", "!=", ">", ">=", "<", "<=", "contains", "not_contains", "startswith", "empty", "not_empty")


# ---------------- finding the sheet ----------------
def _remember(tenant: str, client: SheetsClient, sid: str, title: str) -> None:
    with session() as s:
        r = s.scalar(select(SheetsRecent).where(SheetsRecent.tenant_id == tenant, SheetsRecent.spreadsheet_id == sid))
        if r is None:
            r = SheetsRecent(tenant_id=tenant, spreadsheet_id=sid)
            s.add(r)
        r.title, r.account, r.used_at = title[:300], client.key, now()


def recent(tenant: str, limit: int = 15) -> list[dict[str, Any]]:
    with session() as s:
        return [{"id": r.spreadsheet_id, "title": r.title, "used": r.used_at.isoformat()[:10]}
                for r in s.scalars(select(SheetsRecent).where(SheetsRecent.tenant_id == tenant)
                                   .order_by(SheetsRecent.used_at.desc()).limit(limit)).all()]


def find(tenant: str, query: str = "", limit: int = 15) -> dict[str, Any]:
    out, notes, seen = [], [], set()
    for c in clients(tenant) or [get_client(tenant)]:
        try:
            for f in c.search(query, limit):
                if f["id"] not in seen:
                    seen.add(f["id"])
                    out.append({**f, "account": c.address})
        except SheetError as e:
            notes.append(f"{c.address}: {e}")
    q = (query or "").lower()
    for r in recent(tenant, 30):
        if r["id"] not in seen and (not q or q in r["title"].lower()):
            seen.add(r["id"])
            out.append({"id": r["id"], "title": r["title"], "modified": r["used"], "link": "", "account": "", "recent": True})
    res: dict[str, Any] = {"count": len(out), "sheets": out[:limit]}
    if notes:
        res["notes"] = notes
    return res


def resolve(tenant: str, spreadsheet: str, account: str | None = None) -> tuple[SheetsClient, dict[str, Any]]:
    text = str(spreadsheet or "").strip()
    if not text:
        raise SheetError("Kaunsi sheet? Naam, link ya id dijiye.")
    cs = [get_client(tenant, account)] if account else (clients(tenant) or [get_client(tenant)])
    sid = id_from(text)
    if not sid:     # by name: recent first, then Drive search
        with session() as s:
            rows = s.scalars(select(SheetsRecent).where(SheetsRecent.tenant_id == tenant)
                             .order_by(SheetsRecent.used_at.desc())).all()
            hits = [r for r in rows if r.title.lower() == text.lower()] or [r for r in rows if text.lower() in r.title.lower()]
            if len(hits) == 1:
                sid = hits[0].spreadsheet_id
        if not sid:
            found = []
            for c in cs:
                try:
                    found += [(c, f) for f in c.search(text, 10)]
                except SheetError:
                    continue
            exact = [x for x in found if x[1]["title"].lower() == text.lower()]
            pick = exact or found
            if not pick:
                raise SheetError(f"'{text}' naam ki sheet nahi mili. sheets_find se list dekhiye, ya sheet ka link dijiye.")
            if len({f["id"] for _, f in pick}) > 1:
                opts = "; ".join(f"{f['title']} (id {f['id']}, {f['modified']})" for _, f in pick[:6])
                raise SheetError(f"Is naam ki kai sheets hain: {opts}. User se poochiye kaunsi, phir id se boliye.")
            cs = [pick[0][0]] + [c for c in cs if c is not pick[0][0]]
            sid = pick[0][1]["id"]
    last: Exception | None = None
    for c in cs:
        try:
            meta = c.meta(sid)
            _remember(tenant, c, sid, meta["title"])
            return c, meta
        except SheetError as e:
            last = e
    raise last or SheetError("Sheet nahi khuli")


def tab_of(meta: dict, tab: str | None) -> dict:
    tabs = meta["tabs"]
    if not tabs:
        raise SheetError("Is sheet mein koi tab nahi hai.")
    if not tab:
        return tabs[0]
    t = tab.strip().lower()
    for x in tabs:
        if x["title"].lower() == t:
            return x
    for x in tabs:
        if t in x["title"].lower():
            return x
    raise SheetError(f"'{tab}' tab nahi mila. Tabs: {', '.join(x['title'] for x in tabs)}")


# ---------------- tables ----------------
def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


class Table:
    def __init__(self, header: list[str], rows: list[list[Any]], first_row: int, tab: str):
        self.header = header
        self.rows = rows
        self.first_row = first_row      # sheet row number of rows[0]
        self.tab = tab

    def col(self, name: Any) -> int:
        n = _norm(name)
        for i, h in enumerate(self.header):
            if _norm(h) == n:
                return i
        if re.fullmatch(r"[a-z]{1,2}", n):
            return col_index(n) - 1
        for i, h in enumerate(self.header):
            if n and n in _norm(h):
                return i
        raise SheetError(f"'{name}' column nahi mila. Columns: {', '.join(str(h) for h in self.header if str(h).strip())}")

    def cell(self, row: list, i: int) -> Any:
        return row[i] if i < len(row) else ""

    def as_dict(self, idx: int) -> dict[str, Any]:
        row = self.rows[idx]
        d: dict[str, Any] = {"_row": self.first_row + idx}
        for i, h in enumerate(self.header):
            key = str(h).strip() or a1_col(i + 1)
            d[key] = self.cell(row, i)
        return d


def load(client: SheetsClient, meta: dict, tab: str | None, header_row: int = 1, max_rows: int = MAX_ROWS) -> Table:
    t = tab_of(meta, tab)
    header_row = max(1, int(header_row or 1))
    vals = client.values(meta["id"], f"{q_tab(t['title'])}!A{header_row}:ZZ{header_row + max_rows}")
    header = [str(h).strip() for h in (vals[0] if vals else [])]
    rows = vals[1:]
    width = max([len(header)] + [len(r) for r in rows[:200]] or [0])
    header += [""] * (width - len(header))
    while rows and not any(str(c).strip() for c in rows[-1]):
        rows.pop()
    return Table(header, rows, header_row + 1, t["title"])


def _num(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[₹,\s]|rs\.?|inr", "", str(v or "").lower())
    if s.endswith("%"):
        s = s[:-1]
    try:
        return float(s)
    except ValueError:
        return None


DATE_FMTS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d-%b-%Y", "%d %B %Y", "%m/%d/%Y", "%d/%m/%y")


def _date(v: Any) -> datetime | None:
    s = str(v or "").strip()
    for f in DATE_FMTS:
        try:
            return datetime.strptime(s[:len(datetime.now().strftime(f)) + 4].strip(), f)
        except ValueError:
            continue
    return None


def _match(cell: Any, op: str, value: Any) -> bool:
    if op == "empty":
        return not str(cell).strip()
    if op == "not_empty":
        return bool(str(cell).strip())
    a, b = _num(cell), _num(value)
    if op in (">", ">=", "<", "<=") or (op in ("=", "!=") and a is not None and b is not None):
        if a is None or b is None:
            da, db = _date(cell), _date(value)
            if da is None or db is None:
                return False
            a, b = da.timestamp(), db.timestamp()
        return {"=": a == b, "!=": a != b, ">": a > b, ">=": a >= b, "<": a < b, "<=": a <= b}[op]
    sa, sb = _norm(cell), _norm(value)
    if op == "=":
        return sa == sb
    if op == "!=":
        return sa != sb
    if op == "contains":
        return sb in sa
    if op == "not_contains":
        return sb not in sa
    if op == "startswith":
        return sa.startswith(sb)
    raise SheetError(f"op: {', '.join(OPS)}")


def select_rows(t: Table, where: list[dict] | None = None, rows: list[int] | None = None) -> list[int]:
    """Indexes into t.rows matching every condition (or the given sheet row numbers)."""
    if rows:
        idx = [r - t.first_row for r in rows]
        bad = [r for r, i in zip(rows, idx) if i < 0 or i >= len(t.rows)]
        if bad:
            raise SheetError(f"Row {bad} data mein nahi hai (data rows {t.first_row}-{t.first_row + len(t.rows) - 1}).")
        return idx
    conds = [(t.col(w["column"]), str(w.get("op") or "="), w.get("value", "")) for w in (where or [])]
    for _, op, _v in conds:
        if op not in OPS:
            raise SheetError(f"op: {', '.join(OPS)}")
    return [i for i, r in enumerate(t.rows)
            if any(str(c).strip() for c in r) and all(_match(t.cell(r, c), op, v) for c, op, v in conds)]


# ---------------- reading / asking ----------------
def info(tenant: str, spreadsheet: str) -> dict[str, Any]:
    c, meta = resolve(tenant, spreadsheet)
    heads = c.batch_values(meta["id"], [f"{q_tab(t['title'])}!A1:ZZ1" for t in meta["tabs"][:20]]) if meta["tabs"] else []
    tabs = []
    for t, h in zip(meta["tabs"], heads + [[]] * len(meta["tabs"])):
        tabs.append({"tab": t["title"], "columns": [x for x in (h[0] if h else []) if str(x).strip()],
                     "grid_rows": t["rows"]})
    return {"id": meta["id"], "title": meta["title"], "link": meta["link"], "account": c.address, "tabs": tabs}


def read(tenant: str, spreadsheet: str, tab: str | None = None, cell_range: str | None = None, limit: int = 100,
         offset: int = 0, header_row: int = 1) -> dict[str, Any]:
    c, meta = resolve(tenant, spreadsheet)
    if cell_range:
        rng = cell_range if "!" in cell_range else f"{q_tab(tab_of(meta, tab)['title'])}!{cell_range}"
        vals = c.values(meta["id"], rng)
        return {"title": meta["title"], "link": meta["link"], "range": rng, "values": vals[:500],
                "truncated": len(vals) > 500}
    t = load(c, meta, tab, header_row)
    limit = max(1, min(int(limit or 100), 300))
    offset = max(0, int(offset or 0))
    return {"title": meta["title"], "link": meta["link"], "tab": t.tab, "columns": [h for h in t.header if h],
            "total_rows": len(t.rows), "showing": f"{offset + 1}-{min(len(t.rows), offset + limit)}",
            "rows": [t.as_dict(i) for i in range(offset, min(len(t.rows), offset + limit))],
            "note": "_row is the sheet row number (use it to edit or delete)."}


def query(tenant: str, spreadsheet: str, tab: str | None = None, where: list[dict] | None = None,
          sort_by: str | None = None, descending: bool = False, totals: list[str] | None = None,
          group_by: str | None = None, limit: int = 50, header_row: int = 1) -> dict[str, Any]:
    c, meta = resolve(tenant, spreadsheet)
    t = load(c, meta, tab, header_row)
    idx = select_rows(t, where)
    if sort_by:
        si = t.col(sort_by)

        def key(i):
            v = t.cell(t.rows[i], si)
            n = _num(v)
            d = _date(v) if n is None else None
            return (0, n) if n is not None else (1, d.timestamp()) if d else (2, _norm(v))
        idx.sort(key=key, reverse=bool(descending))
    out: dict[str, Any] = {"title": meta["title"], "tab": t.tab, "link": meta["link"], "matched": len(idx),
                           "of_rows": len(t.rows)}
    tcols = [(name, t.col(name)) for name in (totals or [])]
    if tcols:
        agg = {}
        for name, ci in tcols:
            nums = [n for n in (_num(t.cell(t.rows[i], ci)) for i in idx) if n is not None]
            agg[t.header[ci] or name] = {"sum": round(sum(nums), 2), "avg": round(sum(nums) / len(nums), 2) if nums else None,
                                         "min": min(nums) if nums else None, "max": max(nums) if nums else None,
                                         "count_numbers": len(nums)}
        out["totals"] = agg
    if group_by:
        gi = t.col(group_by)
        groups: dict[str, dict[str, Any]] = {}
        for i in idx:
            g = str(t.cell(t.rows[i], gi)).strip() or "(khaali)"
            e = groups.setdefault(g, {"count": 0})
            e["count"] += 1
            for name, ci in tcols:
                n = _num(t.cell(t.rows[i], ci))
                if n is not None:
                    e[t.header[ci] or name] = round(e.get(t.header[ci] or name, 0) + n, 2)
        out["groups"] = dict(sorted(groups.items(), key=lambda kv: -kv[1]["count"])[:100])
    limit = max(0, min(int(limit or 50), 200))
    out["rows"] = [t.as_dict(i) for i in idx[:limit]]
    if len(idx) > limit:
        out["more"] = len(idx) - limit
    return out


# ---------------- writing ----------------
def _row_values(t: Table, row: Any, add_columns: bool) -> tuple[list[Any], list[str]]:
    if isinstance(row, list):
        return list(row), []
    if not isinstance(row, dict):
        raise SheetError("Har row ek object {column: value} ya list honi chahiye.")
    vals = [""] * len(t.header)
    new_cols = []
    for k, v in row.items():
        try:
            i = t.col(k)
            if i >= len(vals):
                vals += [""] * (i + 1 - len(vals))
        except SheetError:
            if not add_columns:
                raise
            t.header.append(str(k))
            new_cols.append(str(k))
            vals.append("")
            i = len(t.header) - 1
        vals[i] = v
    return vals, new_cols


def append(tenant: str, spreadsheet: str, rows: list, tab: str | None = None, add_columns: bool = False,
           header_row: int = 1) -> dict[str, Any]:
    if not rows:
        raise SheetError("Kya daalna hai? rows do.")
    if len(rows) > 2000:
        raise SheetError("Ek baar mein 2000 rows tak.")
    c, meta = resolve(tenant, spreadsheet)
    t = load(c, meta, tab, header_row)
    out_rows, added = [], []
    for r in rows:
        v, new = _row_values(t, r, add_columns)
        out_rows.append(v)
        added += new
    if added:
        c.update(meta["id"], [{"range": f"{q_tab(t.tab)}!A{header_row}", "values": [t.header]}])
    if not any(str(h).strip() for h in t.header) and rows and isinstance(rows[0], dict):   # empty tab: write header first
        c.update(meta["id"], [{"range": f"{q_tab(t.tab)}!A{header_row}", "values": [list(rows[0].keys())]}])
    res = c.append(meta["id"], f"{q_tab(t.tab)}!A{header_row}", [[("" if x is None else x) for x in r] for r in out_rows])
    up = res.get("updates", {})
    return {"title": meta["title"], "tab": t.tab, "added_rows": up.get("updatedRows", len(out_rows)),
            "range": up.get("updatedRange", ""), "new_columns": added, "link": meta["link"]}


def plan_update(tenant: str, spreadsheet: str, set_values: dict, where: list[dict] | None = None,
                rows: list[int] | None = None, tab: str | None = None, header_row: int = 1) -> dict[str, Any]:
    if not set_values:
        raise SheetError("Kya badalna hai? set do, jaise {Status: Paid}.")
    if not where and not rows:
        raise SheetError("Kaunsi rows? where (condition) ya rows (row numbers) do.")
    c, meta = resolve(tenant, spreadsheet)
    t = load(c, meta, tab, header_row)
    idx = select_rows(t, where, rows)
    if not idx:
        raise SheetError("Koi row match nahi hui. Pehle sheet_query se dekhiye.")
    cols = [(t.col(k), v) for k, v in set_values.items()]
    data, before = [], []
    for i in idx:
        rn = t.first_row + i
        before.append(t.as_dict(i))
        for ci, v in cols:
            data.append({"range": f"{q_tab(t.tab)}!{a1_col(ci + 1)}{rn}", "values": [["" if v is None else v]]})
    return {"client": c, "meta": meta, "tab": t.tab, "data": data, "rows": [t.first_row + i for i in idx],
            "before": before, "set": {t.header[ci] or a1_col(ci + 1): v for ci, v in cols}}


def do_update(c: SheetsClient, sid: str, data: list[dict]) -> int:
    res = c.update(sid, data)
    return int(res.get("totalUpdatedCells", len(data)))


def write_range(tenant: str, spreadsheet: str, cell_range: str, values: list[list[Any]], tab: str | None = None) -> dict:
    cells = sum(len(r) for r in values or [])
    if not cells:
        raise SheetError("values khaali hai")
    if cells > 2000:
        raise SheetError("Ek baar mein 2000 cells tak.")
    c, meta = resolve(tenant, spreadsheet)
    rng = cell_range if "!" in cell_range else f"{q_tab(tab_of(meta, tab)['title'])}!{cell_range}"
    n = do_update(c, meta["id"], [{"range": rng, "values": values}])
    return {"title": meta["title"], "range": rng, "updated_cells": n, "link": meta["link"]}


def plan_delete(tenant: str, spreadsheet: str, where: list[dict] | None = None, rows: list[int] | None = None,
                tab: str | None = None, header_row: int = 1) -> dict[str, Any]:
    if not where and not rows:
        raise SheetError("Kaunsi rows hatani hain? where ya rows do.")
    c, meta = resolve(tenant, spreadsheet)
    t = load(c, meta, tab, header_row)
    idx = select_rows(t, where, rows)
    if not idx:
        raise SheetError("Koi row match nahi hui.")
    if len(idx) > 500:
        raise SheetError("Ek baar mein 500 rows tak hata sakte hain.")
    tab_id = tab_of(meta, t.tab)["id"]
    return {"client": c, "meta": meta, "tab": t.tab, "tab_id": tab_id, "rows": sorted(t.first_row + i for i in idx),
            "before": [t.as_dict(i) for i in idx]}


def do_delete(c: SheetsClient, sid: str, tab_id: int, rows: list[int]) -> int:
    reqs = [{"deleteDimension": {"range": {"sheetId": tab_id, "dimension": "ROWS", "startIndex": r - 1, "endIndex": r}}}
            for r in sorted(set(rows), reverse=True)]      # bottom first, so row numbers don't shift
    c.batch(sid, reqs)
    return len(reqs)


def create(tenant: str, title: str, tabs: list[dict] | None = None, account: str | None = None) -> dict[str, Any]:
    """tabs: [{name, header: [...], rows: [[...]] or [{...}]}]"""
    c = get_client(tenant, account)
    if c.kind == "service":
        raise SheetError("Service account se nayi sheet aapke Drive mein nahi banti. Profile > Google Sheets se apna "
                         "Google account jodiye.")
    tabs = tabs or [{"name": "Sheet1"}]
    names = [str(t.get("name") or f"Sheet{i + 1}")[:90] for i, t in enumerate(tabs)]
    meta = c.create(str(title)[:200] or "Santosh sheet", names)
    data, fmt = [], []
    for t, tm in zip(tabs, meta["tabs"]):
        header = [str(h) for h in (t.get("header") or [])]
        rows = t.get("rows") or []
        if rows and isinstance(rows[0], dict):
            if not header:
                header = list(rows[0].keys())
            rows = [[r.get(h, "") for h in header] for r in rows]
        grid = ([header] if header else []) + [list(r) for r in rows[:5000]]
        if grid:
            data.append({"range": f"{q_tab(tm['title'])}!A1", "values": grid})
        if header:
            fmt.append({"repeatCell": {"range": {"sheetId": tm["id"], "startRowIndex": 0, "endRowIndex": 1},
                                       "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                                                                      "backgroundColor": {"red": 0.93, "green": 0.9, "blue": 1}}},
                                       "fields": "userEnteredFormat(textFormat,backgroundColor)"}})
            fmt.append({"autoResizeDimensions": {"dimensions": {"sheetId": tm["id"], "dimension": "COLUMNS",
                                                                "startIndex": 0, "endIndex": max(1, len(header))}}})
    if data:
        c.update(meta["id"], data)
    if fmt:
        try:
            c.batch(meta["id"], fmt)
        except SheetError:
            pass
    _remember(tenant, c, meta["id"], meta["title"])
    return {"id": meta["id"], "title": meta["title"], "link": meta["link"], "tabs": names, "account": c.address}


def add_tab(tenant: str, spreadsheet: str, name: str, header: list[str] | None = None) -> dict[str, Any]:
    c, meta = resolve(tenant, spreadsheet)
    if any(t["title"].lower() == name.strip().lower() for t in meta["tabs"]):
        raise SheetError(f"'{name}' tab pehle se hai.")
    c.batch(meta["id"], [{"addSheet": {"properties": {"title": name.strip()[:90], "gridProperties": {"frozenRowCount": 1}}}}])
    if header:
        c.update(meta["id"], [{"range": f"{q_tab(name.strip()[:90])}!A1", "values": [header]}])
    return {"title": meta["title"], "tab": name.strip()[:90], "link": meta["link"]}


# ---------- helpers (color + A1 grid range) ----------

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
NAMED_COLORS: dict[str, tuple[float, float, float]] = {
    "red": (1, 0, 0), "green": (0, 1, 0), "blue": (0, 0, 1),
    "yellow": (1, 1, 0), "black": (0, 0, 0), "white": (1, 1, 1),
    "orange": (1, 0.65, 0), "purple": (0.5, 0, 0.5), "pink": (1, 0.75, 0.75),
    "cyan": (0, 1, 1), "magenta": (1, 0, 1), "grey": (0.5, 0.5, 0.5), "gray": (0.5, 0.5, 0.5),
    "lightblue": (0.68, 0.85, 0.9), "lightgreen": (0.56, 0.93, 0.56), "lightyellow": (1, 1, 0.71),
    "lightgrey": (0.83, 0.83, 0.83), "lightgray": (0.83, 0.83, 0.83),
}


def _rgb(color: Any) -> dict[str, float] | None:
    """Resolve a color spec (#hex, named, or {r,g,b}) into Sheets API RGB channels (0..1 floats, long keys)."""
    if color is None:
        return None
    if isinstance(color, dict) and ({"r", "g", "b"} & set(color) or {"red", "green", "blue"} & set(color)):
        # accept both short {r,g,b} and long {red,green,blue} input; output is long-form
        return {"red": float(color.get("red", color.get("r", 0))),
                "green": float(color.get("green", color.get("g", 0))),
                "blue": float(color.get("blue", color.get("b", 0)))}
    s = str(color).strip().lower()
    if s in NAMED_COLORS:
        r, g, b = NAMED_COLORS[s]
        return {"red": r, "green": g, "blue": b}
    m = HEX_RE.match(s)
    if m:
        h = m.group(1)
        return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}
    raise SheetError(f"Color nahi samajh aaya: {color}")


def _text_format(spec: dict) -> dict:
    tf: dict[str, Any] = {}
    for k in ("bold", "italic", "underline", "strikethrough"):
        if k in spec:
            tf[k] = bool(spec[k])
    if "font_size" in spec:
        tf["fontSize"] = int(spec["font_size"])
    if "font_family" in spec:
        tf["fontFamily"] = str(spec["font_family"])[:64]
    if "font_color" in spec:
        fc = _rgb(spec["font_color"])
        if fc is not None:
            tf["foregroundColor"] = fc
    return tf


def _user_format(spec: dict) -> dict:
    fmt: dict[str, Any] = {}
    tf = _text_format(spec)
    if tf:
        fmt["textFormat"] = tf
    if "bg_color" in spec:
        bc = _rgb(spec["bg_color"])
        if bc is not None:
            fmt["backgroundColor"] = bc
    if "number_format" in spec:
        nf = str(spec["number_format"]).strip()
        # Named types accepted by Sheets API: TEXT, NUMBER, PERCENT, CURRENCY, DATE, TIME, DATE_TIME, SCIENTIFIC
        named = {"text", "number", "percent", "currency", "date", "time", "datetime", "scientific"}
        if nf.lower() in named:
            t = "DATE_TIME" if nf.lower() == "datetime" else nf.upper()
            fmt["numberFormat"] = {"type": t}
        else:
            fmt["numberFormat"] = {"type": "NUMBER", "pattern": nf}  # pattern like "#,##0.00" or "yyyy-mm-dd"
    if "horizontal_alignment" in spec:
        fmt["horizontalAlignment"] = str(spec["horizontal_alignment"]).upper()
    if "vertical_alignment" in spec:
        fmt["verticalAlignment"] = str(spec["vertical_alignment"]).upper()
    if "wrap_strategy" in spec:
        fmt["wrapStrategy"] = str(spec["wrap_strategy"]).upper()
    return fmt


def _a1_to_grid_range(rng_str: str, sheet_id: int) -> dict:
    """A1 (e.g. 'A1:C10' or 'B2' or 'A:A') -> Sheets GridRange dict (0-indexed)."""
    rng_str = rng_str.strip()
    m = re.fullmatch(r"([A-Z]*)(\d*)(?::([A-Z]*)(\d*))?", rng_str)
    if not m:
        raise SheetError(f"A1 range samajh nahi aaya: {rng_str}")
    sc, sr, ec, er = m.group(1), m.group(2), m.group(3), m.group(4)
    start_col = col_index(sc) - 1 if sc else 0
    start_row = int(sr) - 1 if sr else 0
    end_col = col_index(ec) if ec else 16383
    end_row = int(er) if er else 1048575
    if end_col <= start_col:
        end_col = start_col + 1
    if end_row <= start_row:
        end_row = start_row + 1
    return {"sheetId": sheet_id, "startRowIndex": start_row, "endRowIndex": end_row,
            "startColumnIndex": start_col, "endColumnIndex": end_col}


def _split_tab_range(meta: dict, rng: str, tab: str | None) -> tuple[dict, str]:
    """Return (tab_dict, a1_only) for a range string that may or may not have a tab prefix."""
    if "!" in rng:
        tab_name, a1 = rng.split("!", 1)
        tab_name = tab_name.strip("'").replace("''", "'")
    else:
        t = tab_of(meta, tab)
        tab_name, a1 = t["title"], rng
    return tab_of(meta, tab_name), a1


# ---------- clear ----------

def plan_clear(tenant: str, spreadsheet: str, ranges: list[str], tab: str | None = None) -> dict[str, Any]:
    """Clear one or more A1 ranges of their VALUES (formatting stays). Always behind a confirm card."""
    if not ranges:
        raise SheetError("Kya saaf karna hai? ranges do (jaise ['A1:C10', 'Summary!B1:F5']).")
    if len(ranges) > 50:
        raise SheetError("Ek baar mein 50 ranges tak.")
    c, meta = resolve(tenant, spreadsheet)
    norm = []
    for r in ranges:
        t, a1 = _split_tab_range(meta, str(r), tab)
        norm.append(f"{q_tab(t['title'])}!{a1}")
    return {"client": c, "meta": meta, "ranges": norm,
            "summary": {"title": meta["title"], "lines": [f"{len(norm)} range ki values clear hongi"] + norm[:6],
                        "more": max(0, len(norm) - 6),
                        "note": "Format bold/rang nahi utrte; sirf values. Undo: Google Sheets version history."}}


def do_clear(c: SheetsClient, sid: str, ranges: list[str]) -> int:
    c.clear(sid, ranges)
    return len(ranges)


# ---------- copy / duplicate / delete tabs ----------

def copy_tab(tenant: str, spreadsheet: str, tab: str, dest_spreadsheet: str, new_title: str | None = None) -> dict[str, Any]:
    """Copy a tab to another spreadsheet (or the same one). Not destructive — runs at once."""
    if not dest_spreadsheet:
        raise SheetError("Kis sheet mein copy karna hai? dest_spreadsheet do (naam/link/id).")
    c, meta = resolve(tenant, spreadsheet)
    src_tab = tab_of(meta, tab)
    dest_sid = id_from(str(dest_spreadsheet))
    if not dest_sid:
        try:
            dc, dmeta = resolve(tenant, str(dest_spreadsheet))
            dest_sid = dmeta["id"]
        except SheetError:
            raise SheetError(f"Destination sheet '{dest_spreadsheet}' nahi mili.")
    out = c.copy_tab(meta["id"], src_tab["id"], dest_sid, new_title)
    return {"src_tab": src_tab["title"], "new_tab": out.get("title") or new_title or src_tab["title"],
            "dest_spreadsheet_id": dest_sid, "new_sheet_id": out.get("sheet_id"), "link": meta["link"]}


def duplicate_tab(tenant: str, spreadsheet: str, tab: str, new_title: str | None = None,
                  new_index: int | None = None) -> dict[str, Any]:
    """Duplicate a tab inside the same spreadsheet. Not destructive — runs at once."""
    c, meta = resolve(tenant, spreadsheet)
    t = tab_of(meta, tab)
    name = (new_title or f"{t['title']} copy")[:100]
    # find a sheet id that doesn't collide
    used = {x["id"] for x in meta["tabs"]}
    new_id = max(used) + 1 if used else 1
    c.batch(meta["id"], [{"duplicateSheet": {
        "sourceSheetId": t["id"], "insertSheetIndex": int(new_index) if new_index is not None else len(meta["tabs"]),
        "newSheetId": new_id, "newSheetName": name}}])
    return {"title": meta["title"], "src_tab": t["title"], "new_tab": name, "link": meta["link"]}


def plan_delete_tab(tenant: str, spreadsheet: str, tab: str) -> dict[str, Any]:
    """Delete a whole tab. Destructive — confirm card first; refuses on the last tab."""
    c, meta = resolve(tenant, spreadsheet)
    t = tab_of(meta, tab)
    if len(meta["tabs"]) == 1:
        raise SheetError("Yeh akhaari tab hai; sheet khali nahi ho sakti. Pehle naya tab banaiye.")
    return {"client": c, "meta": meta, "tab_id": t["id"], "tab": t["title"],
            "summary": {"title": meta["title"], "lines": [f"Tab '{t['title']}' hata di jayegi"],
                        "note": "Undo: Google Sheets version history se wapas la sakte hain."}}


def do_delete_tab(c: SheetsClient, sid: str, tab_id: int) -> int:
    c.batch(sid, [{"deleteSheet": {"sheetId": int(tab_id)}}])
    return 1


# ---------- format ----------

def format_cells(tenant: str, spreadsheet: str, rng: str, format: dict, tab: str | None = None) -> dict[str, Any]:
    """Apply a cell/text format to an A1 range. Bold / italic / color / number format / align / wrap / freeze."""
    if not format or not isinstance(format, dict):
        raise SheetError("Kya format lagana hai? format do (bold, italic, font_size, font_color, bg_color, "
                         "number_format, horizontal_alignment, vertical_alignment, wrap_strategy, freeze_rows, freeze_cols).")
    c, meta = resolve(tenant, spreadsheet)
    t, a1 = _split_tab_range(meta, str(rng), tab)
    user_fmt = _user_format(format)
    if not user_fmt and "freeze_rows" not in format and "freeze_cols" not in format:
        raise SheetError("format khaali hai. Kam se kam ek property do.")
    requests: list[dict] = []
    if user_fmt:
        fmt_fields = list(user_fmt.keys())
        fields_str = "userEnteredFormat(" + ",".join(fmt_fields) + ")"
        requests.append({"repeatCell": {"range": _a1_to_grid_range(a1, t["id"]),
                                        "cell": {"userEnteredFormat": user_fmt}, "fields": fields_str}})
    fr_rows = int(format.get("freeze_rows", 0)) if "freeze_rows" in format else None
    fr_cols = int(format.get("freeze_cols", 0)) if "freeze_cols" in format else None
    if fr_rows is not None or fr_cols is not None:
        gp: dict[str, int] = {}
        if fr_rows is not None:
            gp["frozenRowCount"] = max(0, fr_rows)
        if fr_cols is not None:
            gp["frozenColumnCount"] = max(0, fr_cols)
        requests.append({"updateSheetProperties": {
            "properties": {"sheetId": t["id"], "gridProperties": gp},
            "fields": "gridProperties(frozenRowCount,frozenColumnCount)"}})
    c.batch(meta["id"], requests)
    return {"title": meta["title"], "tab": t["title"], "range": a1, "applied": list(format.keys())[:20],
            "link": meta["link"]}


# ---------- protect (confirm card) ----------

def plan_protect(tenant: str, spreadsheet: str, rng: str, tab: str | None = None,
                 description: str = "", editors: list[str] | None = None) -> dict[str, Any]:
    """Lock a range so only listed editors can change it. Destructive (blocks editing) — confirm card first."""
    c, meta = resolve(tenant, spreadsheet)
    t, a1 = _split_tab_range(meta, str(rng), tab)
    desc = (description or "")[:200]
    ed = [str(e).strip()[:320] for e in (editors or []) if str(e).strip()]
    return {"client": c, "meta": meta, "tab_id": t["id"], "tab": t["title"], "range": a1,
            "description": desc, "editors": ed,
            "summary": {"title": meta["title"], "tab": t["title"],
                        "lines": [f"Lock kar dein: {a1}" + (f" - {desc[:60]}" if desc else "")]
                                 + ([f"Editors: {', '.join(ed[:6])}"] if ed else []),
                        "note": "Locked cell sirf editors edit kar sakte hain."}}


def do_protect(c: SheetsClient, sid: str, tab_id: int, rng: str, description: str, editors: list[str]) -> int:
    body: dict[str, Any] = {"protectedRange": {"range": _a1_to_grid_range(rng, int(tab_id)),
                                               "description": description or ""}}
    if editors:
        body["protectedRange"]["editors"] = {"users": editors}
    c.batch(sid, [{"addProtectedRange": body}])
    return 1


# ---------- named ranges ----------

def named_range(tenant: str, spreadsheet: str, action: str, name: str | None = None,
                rng: str | None = None, named_id: int | None = None, tab: str | None = None) -> dict[str, Any]:
    """Add / update / delete / list named ranges."""
    action = (action or "list").lower()
    if action not in ("add", "update", "delete", "list"):
        raise SheetError("action: add / update / delete / list")
    c, meta = resolve(tenant, spreadsheet)
    if action == "list":
        res = c._req("GET", f"{SHEETS}/{meta['id']}", params={"fields": "namedRanges"})
        return {"title": meta["title"], "named_ranges": res.get("namedRanges", [])}
    if action == "add" and not name:
        raise SheetError("Naam do (named range ka naam).")
    if action == "add":
        if not rng:
            raise SheetError("Range do (jaise 'A1:C10' ya 'Summary!B2:F20').")
        t, a1 = _split_tab_range(meta, str(rng), tab)
        c.batch(meta["id"], [{"addNamedRange": {"namedRange": {"name": str(name)[:250],
                                                               "range": _a1_to_grid_range(a1, t["id"])}}}])
        return {"title": meta["title"], "name": name, "range": f"{t['title']}!{a1}", "action": "added"}
    if action == "delete":
        if named_id is None:
            raise SheetError("named_id do (delete karne ke liye).")
        c.batch(meta["id"], [{"deleteNamedRange": {"namedRangeId": str(int(named_id))}}])
        return {"title": meta["title"], "named_id": int(named_id), "action": "deleted"}
    if action == "update":
        if named_id is None:
            raise SheetError("named_id do (update karne ke liye).")
        props: dict[str, Any] = {"namedRangeId": str(int(named_id))}
        if name:
            props["name"] = str(name)[:250]
        if rng:
            t, a1 = _split_tab_range(meta, str(rng), tab)
            props["range"] = _a1_to_grid_range(a1, t["id"])
        c.batch(meta["id"], [{"updateNamedRange": {"namedRange": props, "fields": "*"}}])
        return {"title": meta["title"], "named_id": int(named_id), "action": "updated"}
    raise SheetError("unreachable")


# ---------- conditional formatting ----------

def _cf_rule(spec: dict, sheet_id: int) -> dict:
    """Build a conditional-format rule from a compact spec.

    spec.type = color_scale | data_bar | cell_is | expression
    color_scale: min/mid/max = {color, type ('min'|'number'|'percent'|'max'), value (number/percent)}
    data_bar: min/max (same shape), color (a single named/hex color)
    cell_is: operator (GREATER_THAN / LESS_THAN / BETWEEN / ...), values (list), format (cell format dict)
    expression: formula (str starting with '='), format (cell format dict)
    """
    t = str(spec.get("type") or "").lower()
    if t == "color_scale":
        pts = []
        for k in ("min", "mid", "max"):
            if k in spec:
                p = spec[k]
                rgb = _rgb(p.get("color"))
                pts.append({"color": rgb or {}, "type": str(p.get("type", "min")).lower(),
                            "value": p.get("value") if p.get("value") is not None else 0})
        if len(pts) < 2:
            raise SheetError("color_scale needs min and max.")
        rule: dict[str, Any] = {"gradientRule": {"minpoint": pts[0],
                                                 "maxpoint": pts[-1]}}
        if len(pts) >= 3:
            rule["gradientRule"]["midpoint"] = pts[1]
        return rule
    if t == "data_bar":
        rgb = _rgb(spec.get("color", "blue"))
        rule = {"booleanRule": {"condition": {"type": "NUMBER_GREATER_THAN", "values": [{"userEnteredValue": "0"}]},
                                "format": {"backgroundColor": rgb or {}}}}
        return rule
    if t == "cell_is":
        op = str(spec.get("operator", "GREATER_THAN")).upper()
        vals = [str(v) for v in (spec.get("values") or [])]
        cond = {"type": op, "values": [{"userEnteredValue": v} for v in vals]}
        fmt = _user_format(spec.get("format") or {"bg_color": "lightgreen"})
        return {"booleanRule": {"condition": cond, "format": fmt}}
    if t == "expression":
        formula = str(spec.get("formula") or "")
        if not formula:
            raise SheetError("expression formula do (jaise '=B1>1000').")
        fmt = _user_format(spec.get("format") or {"bg_color": "lightyellow"})
        return {"booleanRule": {"condition": {"type": "CUSTOM_FORMULA",
                                             "values": [{"userEnteredValue": formula.lstrip("=")}]},
                                "format": fmt}}
    raise SheetError(f"conditional_format type: color_scale / data_bar / cell_is / expression")


def conditional_format(tenant: str, spreadsheet: str, rng: str, rule: dict,
                       tab: str | None = None, action: str = "add", rule_index: int | None = None) -> dict[str, Any]:
    """Add / update / delete a conditional formatting rule on a range."""
    action = (action or "add").lower()
    c, meta = resolve(tenant, spreadsheet)
    t, a1 = _split_tab_range(meta, str(rng), tab)
    grid = _a1_to_grid_range(a1, t["id"])
    if action == "add":
        if not rule:
            raise SheetError("rule do (type: color_scale / data_bar / cell_is / expression).")
        c.batch(meta["id"], [{"addConditionalFormatRule": {"rule": _cf_rule(rule, t["id"]), "range": grid,
                                                            "index": 0}}])
        return {"title": meta["title"], "tab": t["title"], "range": a1, "action": "added", "rule_type": rule.get("type")}
    if action == "delete":
        if rule_index is None:
            raise SheetError("rule_index do (delete karne ke liye).")
        c.batch(meta["id"], [{"deleteConditionalFormatRule": {"sheetId": t["id"], "index": int(rule_index)}}])
        return {"title": meta["title"], "tab": t["title"], "action": "deleted", "rule_index": int(rule_index)}
    if action == "update":
        if rule_index is None or not rule:
            raise SheetError("rule_index aur rule dono do (update ke liye).")
        c.batch(meta["id"], [{"updateConditionalFormatRule": {
            "rule": _cf_rule(rule, t["id"]), "rule_index": int(rule_index), "sheetId": t["id"]}}])
        return {"title": meta["title"], "tab": t["title"], "action": "updated", "rule_index": int(rule_index)}
    raise SheetError("action: add / update / delete")


# ---------- data validation ----------

def _dv_condition(spec: dict) -> dict:
    """Build a Sheets DataValidationCondition from a compact spec.

    spec.type = list | number | whole | date | text_length | boolean | custom_formula
    spec.operator = BETWEEN / NOT_BETWEEN / GREATER_THAN / LESS_THAN / EQUAL / NOT_EQUAL / GREATER_THAN_OR_EQUAL_TO / ...
    spec.values = list (for list type, a list of allowed values; for number/date/etc., [low, high])
    spec.formula = single formula (only for custom_formula or list-from-range)
    """
    t = str(spec.get("type") or "list").lower()
    if t == "list":
        vals = spec.get("values") or []
        if not vals:
            raise SheetError("list ke liye values do (jaise ['Paid', 'Pending', 'Cancelled']).")
        # Sheets API uses ONE_CONDITION_VALUE for lists, joined by comma
        joined = ",".join(str(v) for v in vals[:200])
        return {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": joined}]}
    if t == "custom_formula":
        f = str(spec.get("formula") or "")
        if not f:
            raise SheetError("custom_formula ke liye formula do.")
        return {"type": "CUSTOM_IS_VALID", "values": [{"userEnteredValue": f.lstrip("=")}]}
    op_map = {
        "between": "NUMBER_BETWEEN", "not_between": "NUMBER_NOT_BETWEEN",
        "greater_than": "NUMBER_GREATER_THAN", "less_than": "NUMBER_LESS_THAN",
        "equal": "NUMBER_EQ", "not_equal": "NUMBER_NOT_EQ",
        "greater_than_or_equal_to": "NUMBER_GREATER_THAN_OR_EQUAL_TO",
        "less_than_or_equal_to": "NUMBER_LESS_THAN_OR_EQUAL_TO",
    }
    base = "DATE_" if t == "date" else "TEXT_LENGTH_" if t == "text_length" else "NUMBER_"
    op = str(spec.get("operator", "between")).lower()
    ctype = op_map.get(op)
    if not ctype:
        raise SheetError(f"operator: between / not_between / greater_than / less_than / equal / not_equal")
    if t == "date":
        ctype = ctype.replace("NUMBER_", "DATE_")
    elif t == "text_length":
        ctype = ctype.replace("NUMBER_", "TEXT_LENGTH_")
    elif t == "whole":
        ctype = ctype.replace("NUMBER_", "NUMBER_")  # whole numbers are NUMBER_*
    vals = [str(v) for v in (spec.get("values") or []) if v is not None and str(v).strip() != ""]
    return {"type": ctype, "values": [{"userEnteredValue": v} for v in vals]}


def data_validation(tenant: str, spreadsheet: str, rng: str, rule: dict,
                     tab: str | None = None, action: str = "set") -> dict[str, Any]:
    """Set or clear data validation on a range."""
    action = (action or "set").lower()
    c, meta = resolve(tenant, spreadsheet)
    t, a1 = _split_tab_range(meta, str(rng), tab)
    grid = _a1_to_grid_range(a1, t["id"])
    if action == "clear":
        c.batch(meta["id"], [{"setDataValidation": {"range": grid, "rule": None}}])
        return {"title": meta["title"], "tab": t["title"], "range": a1, "action": "cleared"}
    if action != "set":
        raise SheetError("action: set / clear")
    cond = _dv_condition(rule)
    body = {"range": grid, "rule": {"condition": cond,
                                    "showCustomUi": bool(rule.get("show_dropdown", True)),
                                    "strict": bool(rule.get("strict", False))}}
    if rule.get("input_message"):
        body["rule"]["inputMessage"] = str(rule["input_message"])[:500]
    if rule.get("error_message"):
        body["rule"]["errorMessage"] = str(rule["error_message"])[:500]
    c.batch(meta["id"], [{"setDataValidation": body}])
    return {"title": meta["title"], "tab": t["title"], "range": a1, "action": "set",
            "validation_type": rule.get("type")}


# ---------- merge cells ----------

def merge_cells(tenant: str, spreadsheet: str, rng: str, merge_type: str = "MERGE_ALL",
                tab: str | None = None, action: str = "merge") -> dict[str, Any]:
    """Merge or unmerge a range. merge_type: MERGE_ALL / MERGE_COLUMNS / MERGE_ROWS."""
    action = (action or "merge").lower()
    c, meta = resolve(tenant, spreadsheet)
    t, a1 = _split_tab_range(meta, str(rng), tab)
    grid = _a1_to_grid_range(a1, t["id"])
    if action == "merge":
        mt = str(merge_type or "MERGE_ALL").upper()
        if mt not in ("MERGE_ALL", "MERGE_COLUMNS", "MERGE_ROWS"):
            raise SheetError("merge_type: MERGE_ALL / MERGE_COLUMNS / MERGE_ROWS")
        c.batch(meta["id"], [{"mergeCells": {"range": grid, "mergeType": mt}}])
        return {"title": meta["title"], "tab": t["title"], "range": a1, "action": "merged", "merge_type": mt}
    if action == "unmerge":
        c.batch(meta["id"], [{"unmergeCells": {"range": grid}}])
        return {"title": meta["title"], "tab": t["title"], "range": a1, "action": "unmerged"}
    raise SheetError("action: merge / unmerge")


# ---------- cell notes (PII-guarded) ----------

def cell_notes(tenant: str, spreadsheet: str, notes: list[dict] | None = None,
               tab: str | None = None, read_only: bool = False) -> dict[str, Any]:
    """Read cell notes (read_only=True) or set cell notes from a list of {row, col, note} dicts.

    Note text passes the same PII guard as drive_comments / uploads (no Aadhaar / OTP / password / CVV).
    """
    c, meta = resolve(tenant, spreadsheet)
    t = tab_of(meta, tab)
    if read_only or not notes:
        # read existing notes via the values API with notes renderOption? Actually notes are in cells metaData.
        res = c._req("GET", f"{SHEETS}/{meta['id']}", params={
            "fields": "sheets(data(rowData(values(note,userEnteredValue))),properties"}
        )
        sheets = res.get("sheets", [])
        out: list[dict[str, Any]] = []
        for s in sheets:
            sheet_id = s.get("properties", {}).get("sheetId")
            if sheet_id != t["id"]:
                continue
            for ri, row in enumerate(s.get("data", [])):
                for ci, cell in enumerate(row.get("rowData", [])):
                    note = cell.get("values", [{}])[0].get("note")
                    if note:
                        out.append({"row": ri + 1, "col": ci + 1, "note": note})
        return {"title": meta["title"], "tab": t["title"], "notes": out}
    # set notes: build updateCells request
    if len(notes) > 100:
        raise SheetError("Ek baar mein 100 notes tak.")
    from .. import pii
    for n in notes:
        text = str(n.get("note") or "")
        if pii.find(text):
            raise SheetError("Note mein personal / OTP / password jaankari nahi likhi ja sakti.")
    # group by row, sort
    by_row: dict[int, list[dict]] = {}
    for n in notes:
        r = int(n.get("row", 0))
        if r < 1:
            raise SheetError(f"row number 1 ya usse bada chahiye (mile: {r}).")
        by_row.setdefault(r, []).append(n)
    requests: list[dict] = []
    for r, items in sorted(by_row.items()):
        max_col = max(int(n.get("col", 0)) for n in items)
        row_vals = [{}] * (max_col + 1)
        for n in items:
            col = int(n.get("col", 0))
            if col < 1:
                raise SheetError(f"col number 1 ya usse bada chahiye (mile: {col}).")
            row_vals[col - 1] = {"note": str(n["note"])[:500]}
        requests.append({"updateCells": {
            "start": {"sheetId": t["id"], "rowIndex": r - 1, "columnIndex": 0},
            "rows": [{"values": row_vals}],
            "fields": "note"}})
    c.batch(meta["id"], requests)
    return {"title": meta["title"], "tab": t["title"], "notes_set": len(notes), "link": meta["link"]}


# ---------- find / replace (PII-guarded) ----------

def find_replace(tenant: str, spreadsheet: str, find: str, replace: str, tab: str | None = None,
                 match_case: bool = False, match_entire_cell: bool = False,
                 search_by_formulas: bool = False, include_formulas: bool = True) -> dict[str, Any]:
    """Find and replace within a sheet (or one tab). Replacement text is PII-guarded."""
    if not find:
        raise SheetError("Kya dhoondhna hai? find do.")
    from .. import pii
    if pii.find(str(replace)):
        raise SheetError("Replace mein personal / OTP / password jaankari nahi daal sakte.")
    c, meta = resolve(tenant, spreadsheet)
    body: dict[str, Any] = {"find": str(find), "replacement": str(replace),
                            "matchCase": bool(match_case), "matchEntireCell": bool(match_entire_cell),
                            "searchByFormulas": bool(search_by_formulas),
                            "includeFormulas": bool(include_formulas)}
    if tab:
        body["sheetId"] = tab_of(meta, tab)["id"]
    else:
        body["allSheets"] = True
    res = c.batch(meta["id"], [{"findReplace": body}])
    rep = (res.get("replies", [{}])[0].get("findReplace", {}))
    return {"title": meta["title"], "tab": tab or "(all)",
            "values_changed": rep.get("valuesChanged", 0),
            "formulas_changed": rep.get("formulasChanged", 0),
            "rows_changed": rep.get("rowsChanged", 0),
            "sheets_changed": rep.get("sheetsChanged", 0), "link": meta["link"]}

# ---------------- files: import / export ----------------
def import_rows(tenant: str, source: dict[str, Any]) -> tuple[list[list[Any]], str]:
    from ..mailbox import mime
    from ..mailbox import service as ms
    if source.get("email_id"):
        name, _mt, data = ms.attachment(tenant, source["email_id"], str(source.get("attachment_id") or "0"))
    elif source.get("file_id"):
        from pathlib import Path
        f = ms._file_row(tenant, source["file_id"])
        name, data = f.name, Path(f.stored_path).read_bytes()
    else:
        raise SheetError("source: {email_id, attachment_id} ya {file_id} (Excel / CSV)")
    rows = mime.table_rows(name, data)
    if not rows:
        raise SheetError(f"{name} mein koi data nahi mila.")
    return rows, name


def export(tenant: str, spreadsheet: str, tab: str | None = None, fmt: str = "xlsx") -> tuple[str, bytes, dict]:
    c, meta = resolve(tenant, spreadsheet)
    tabs = [tab_of(meta, tab)] if tab else meta["tabs"][:20]
    grids = c.batch_values(meta["id"], [q_tab(t["title"]) for t in tabs])
    safe = re.sub(r"[^\w\- ]+", "", meta["title"]).strip() or "sheet"
    if fmt == "csv":
        import csv
        buf = io.StringIO()
        csv.writer(buf).writerows(grids[0] if grids else [])
        return f"{safe}.csv", buf.getvalue().encode("utf-8-sig"), meta
    import openpyxl
    from openpyxl.styles import Font
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for t, grid in zip(tabs, grids):
        ws = wb.create_sheet(re.sub(r"[\[\]:*?/\\]", " ", t["title"])[:31] or "Sheet")
        for r in grid:
            ws.append([_num(v) if _num(v) is not None and not str(v).startswith("0") else v for v in r])
        if grid:
            for cell in ws[1]:
                cell.font = Font(bold=True)
            ws.freeze_panes = "A2"
    out = io.BytesIO()
    wb.save(out)
    return f"{safe}.xlsx", out.getvalue(), meta


# ---------------- confirm cards ----------------
def pend(tenant: str, conv: str, action: str, payload: dict, summary: dict) -> str:
    with session() as s:
        p = SheetsPending(tenant_id=tenant, conversation_id=conv, action=action, payload=payload, summary=summary)
        s.add(p)
        s.flush()
        return p.id


def pending(tenant: str, pid: str) -> dict | None:
    with session() as s:
        p = s.get(SheetsPending, pid)
        if p is None or p.tenant_id != tenant:
            return None
        return {"id": p.id, "action": p.action, "payload": p.payload, "summary": p.summary, "status": p.status,
                "conversation_id": p.conversation_id}


def run_pending(tenant: str, pid: str) -> dict[str, Any]:
    p = pending(tenant, pid)
    if p is None or p["status"] != "pending":
        raise SheetError("Yeh sheet badlav ab baaki nahi hai.")
    pl = p["payload"]
    c = get_client(tenant, pl["account"])
    try:
        if p["action"] == "update":
            n = do_update(c, pl["sid"], pl["data"])
            msg = f"{p['summary']['title']}: {len(pl['rows'])} rows badal di ({n} cells)."
        elif p["action"] == "delete":
            meta = c.meta(pl["sid"])
            # the sheet may have changed since the card was made: check the rows still hold what the user saw
            t = load(c, meta, pl["tab"], pl.get("header_row", 1))
            for b in pl["before"]:
                i = b["_row"] - t.first_row
                if i < 0 or i >= len(t.rows) or t.as_dict(i) != b:
                    raise SheetError("Card banne ke baad sheet badal gayi; rows dobara chun kar boliye.")
            n = do_delete(c, pl["sid"], pl["tab_id"], pl["rows"])
            msg = f"{p['summary']['title']}: {n} rows hata di. (Google Sheets mein File > Version history se wapas la sakte hain.)"
        elif p["action"] == "share":
            for e in pl["emails"]:
                c.share(pl["sid"], e, pl["role"])
            msg = f"{p['summary']['title']} share kar di: {', '.join(pl['emails'])} ({'edit' if pl['role'] == 'writer' else 'dekh'} sakte hain)."
        elif p["action"] == "clear":
            c.clear(pl["sid"], pl["ranges"])
            msg = f"{p['summary']['title']}: {len(pl['ranges'])} range clear kar di. (Undo: version history.)"
        elif p["action"] == "delete_tab":
            do_delete_tab(c, pl["sid"], pl["tab_id"])
            msg = f"{p['summary']['title']}: tab '{pl.get('tab', '')}' hata di. (Undo: version history.)"
        elif p["action"] == "protect":
            do_protect(c, pl["sid"], pl["tab_id"], pl["range"], pl.get("description", ""), pl.get("editors", []))
            msg = f"{p['summary']['title']}: range '{pl['range']}' lock kar di."
        else:
            raise SheetError("unknown sheet action")
    except SheetError:
        with session() as s:
            s.get(SheetsPending, pid).status = "failed"
        raise
    with session() as s:
        s.get(SheetsPending, pid).status = "done"
    if p["conversation_id"]:
        bus.publish(p["conversation_id"], "sheet", {"id": pl["sid"], "title": p["summary"]["title"],
                                                    "link": pl.get("link", ""), "status": p["action"] + "d"})
    return {"message": msg}
