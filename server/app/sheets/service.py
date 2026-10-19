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
from .client import SheetError, SheetsClient, a1_col, col_index, id_from, q_tab

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
