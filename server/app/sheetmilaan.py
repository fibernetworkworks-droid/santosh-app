"""v0.108 Sheet Milaan: compare two spreadsheets by a key column and update the old one - all in code, nothing guessed.

    load(name, data, sheet)      -> Table (header row found by itself, typed values, row numbers)
    compare(old, new, key, update) -> added / changed (old -> new per cell) / missing rows, duplicates, column map
    apply(old_name, old_bytes, result, opts) -> the updated copy (openpyxl writes VALUES only, so fonts, fills, borders,
                                    number formats, widths, merged cells, formulas elsewhere and other sheets stay)

Keys are compared normalised: a MAC "aa-bb-cc-dd-ee-ff" = "AA:BB:CC:DD:EE:FF" = "aabb.ccdd.eeff"; "123.0" = "123";
case and extra spaces never make a difference. The original file is never changed: the caller saves a NEW copy.
"""
from __future__ import annotations

import csv
import difflib
import io
import re
import zipfile
from copy import copy
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

MAC_RE = re.compile(r"^\s*([0-9a-f]{2})[:\-\. ]?([0-9a-f]{2})[:\-\. ]?([0-9a-f]{2})[:\-\. ]?([0-9a-f]{2})[:\-\. ]?"
                    r"([0-9a-f]{2})[:\-\. ]?([0-9a-f]{2})\s*$", re.I)
MAC_DOT = re.compile(r"^\s*([0-9a-f]{4})\.([0-9a-f]{4})\.([0-9a-f]{4})\s*$", re.I)
ROWNO_WORDS = {"sno", "srno", "slno", "sn0", "serialnumber_row", "no", "number", "kramank", "क्रमांक", "क्र"}
KEY_ORDER = [  # header words that make a column a key, strongest first
    ("mac", ("macaddress", "macid", "mac", "macno", "onumac", "ontmac", "routermac", "devicemac")),
    ("serial", ("serialnumber", "serialno", "serial", "ponsn", "gponsn", "onusn", "ontsn", "sn", "deviceserial")),
    ("imei", ("imei", "imeino", "imeinumber")),
    ("id", ("customerid", "custid", "consumerno", "consumerid", "accountid", "accountno", "subscriberid", "userid",
            "username", "loginid", "employeeid", "empid", "studentid", "rollno", "itemcode", "productcode", "sku",
            "partno", "code", "id", "uid", "ticketid", "orderid", "invoiceno", "billno", "policyno", "vehicleno")),
    ("phone", ("mobile", "mobileno", "phone", "phoneno", "contact", "contactno", "whatsapp")),
    ("name", ("customername", "name", "customer", "party", "partyname", "subscriber", "subscribername", "client")),
]


class SheetError(ValueError):
    pass


@dataclass
class Table:
    name: str
    sheet: str
    sheets: list[str]
    header_row: int                     # 1-based row in the sheet
    headers: list[str]                  # as written
    rows: list[tuple[int, list[Any]]]   # (sheet row number, values)
    kind: str = "xlsx"                  # xlsx | csv
    notes: list[str] = field(default_factory=list)


def hnorm(h: Any) -> str:
    return re.sub(r"[^a-z0-9ऀ-ॿ]+", "", str(h or "").lower())


def mac(v: Any) -> str | None:
    s = str(v or "").strip()
    m = MAC_RE.match(s) or MAC_DOT.match(s)
    if not m:
        return None
    hexs = "".join(m.groups()).upper()
    return ":".join(hexs[i:i + 2] for i in range(0, 12, 2))


def vnorm(v: Any) -> str:
    """Value as compared: MACs canonical, 12.0 = 12, dates as yyyy-mm-dd, case / spaces ignored."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        f = float(v)
        return str(int(f)) if f.is_integer() else repr(round(f, 6))
    if isinstance(v, datetime):
        return v.date().isoformat() if (v.hour, v.minute, v.second) == (0, 0, 0) else v.isoformat(timespec="minutes")
    if isinstance(v, date):
        return v.isoformat()
    s = str(v).strip().lstrip("'")
    m = mac(s)
    if m:
        return m
    if re.fullmatch(r"-?\d+\.0+", s):
        s = s.split(".")[0]
    return re.sub(r"\s+", " ", s).casefold()


def shown(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d-%m-%Y") if (v.hour, v.minute) == (0, 0) else v.strftime("%d-%m-%Y %H:%M")
    if isinstance(v, date):
        return v.strftime("%d-%m-%Y")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


# ---------------------------------------------------------------- reading
def risky_parts(name: str, data: bytes) -> list[str]:
    """Things openpyxl cannot carry into the new copy (said on the card before her Haan)."""
    out = []
    if not name.lower().endswith((".xlsx", ".xlsm")):
        return out
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
    except Exception:
        return out
    if any(n.startswith("xl/charts/") for n in names):
        out.append("is file mein chart hai: naye copy mein chart nahi rahega (data aur formatting rahegi)")
    if any(n.startswith("xl/media/") for n in names) or any(n.startswith("xl/drawings/") for n in names):
        out.append("photo / logo / shapes naye copy mein nahi rahenge")
    if any("vbaProject" in n for n in names):
        out.append("macro wali file (.xlsm): macros rakhe jayenge, par Excel 'Enable content' poochh sakta hai")
    if any(n.startswith("xl/pivotTables/") for n in names):
        out.append("pivot table hai: Excel mein khol kar 'Refresh' kijiye")
    if any(n.startswith("xl/externalLinks/") for n in names):
        out.append("doosri files se jude formulas (external links) hain: unki value Excel kholne par update hogi")
    if any(n.startswith("xl/slicers/") or n.startswith("xl/timelines/") for n in names):
        out.append("slicer / timeline naye copy mein nahi rahenge")
    return out


def _csv_rows(data: bytes) -> list[list[str]]:
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except Exception:
            continue
    else:
        raise SheetError("CSV padhi nahi ja saki")
    try:
        dialect = csv.Sniffer().sniff(text[:5000], delimiters=",;\t|")
    except Exception:
        dialect = csv.excel
    return [r for r in csv.reader(io.StringIO(text), dialect)]


def _is_texty(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != "" and not re.fullmatch(r"[\d.,\-/: ]+", v.strip())


def _header_at(grid: list[list[Any]]) -> int:
    """0-based index of the header row: the first row with 2+ filled cells, mostly words, and data below it."""
    for i, row in enumerate(grid[:15]):
        filled = [c for c in row if c not in (None, "")]
        if len(filled) < 2:
            continue
        texty = sum(1 for c in filled if _is_texty(c))
        below = any(any(c not in (None, "") for c in r) for r in grid[i + 1:i + 4])
        if texty / len(filled) >= 0.6 and below:
            return i
    for i, row in enumerate(grid[:15]):
        if sum(1 for c in row if c not in (None, "")) >= 2:
            return i
    raise SheetError("Sheet mein koi table nahi mili (heading wali line nahi dikhi)")


def _table(name: str, sheet: str, sheets: list[str], grid: list[list[Any]], kind: str) -> Table:
    hi = _header_at(grid)
    raw = list(grid[hi])
    while raw and raw[-1] in (None, ""):
        raw.pop()
    headers = [str(h).strip() if h not in (None, "") else f"Column {i + 1}" for i, h in enumerate(raw)]
    rows = []
    empty_run = 0
    for j, r in enumerate(grid[hi + 1:], start=hi + 2):
        vals = list(r[:len(headers)]) + [None] * max(0, len(headers) - len(r))
        if all(v in (None, "") for v in vals):
            empty_run += 1
            if empty_run > 50:
                break
            continue
        empty_run = 0
        rows.append((j, vals))
    return Table(name=name, sheet=sheet, sheets=sheets, header_row=hi + 1, headers=headers, rows=rows, kind=kind)


def load(name: str, data: bytes, sheet: str | None = None, want: list[str] | None = None) -> Table:
    low = (name or "").lower()
    if low.endswith((".csv", ".tsv", ".txt")):
        return _table(name, "", [], _csv_rows(data), "csv")
    if low.endswith(".xls"):
        raise SheetError("Yeh purani .xls file hai: Excel mein kholkar 'Save As' > .xlsx kar dijiye, phir main milaan kar dunga")
    if not low.endswith((".xlsx", ".xlsm")):
        raise SheetError(f"{name}: sirf Excel (.xlsx) ya CSV ka milaan hota hai")
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    except Exception as e:
        raise SheetError(f"{name} Excel file khul nahi payi ({type(e).__name__}); file kharab ya password wali to nahi?")
    try:
        names = wb.sheetnames
        if sheet:
            pick = next((n for n in names if n == sheet), None) or next((n for n in names if hnorm(n) == hnorm(sheet)), None)
            if not pick:
                raise SheetError(f"'{sheet}' naam ki sheet nahi mili; sheets: {', '.join(names)}")
            cands = [pick]
        else:
            cands = names
        best: Table | None = None
        best_score = -1.0
        for n in cands:
            ws = wb[n]
            grid = [list(r) for r in ws.iter_rows(values_only=True, max_row=20000)]
            if not grid:
                continue
            try:
                t = _table(name, n, names, grid, "xlsx")
            except SheetError:
                continue
            hs = {hnorm(h) for h in t.headers}
            score = len(t.rows) + (500 if want and any(hnorm(w) in hs for w in want) else 0) + \
                (200 if any(k in hs for _, ks in KEY_ORDER[:3] for k in ks) else 0)
            if score > best_score:
                best, best_score = t, score
        if best is None:
            raise SheetError(f"{name} mein koi table nahi mili")
        if len(cands) > 1 and len([n for n in cands if n]) > 1:
            best.notes.append(f"{len(names)} sheets mein se '{best.sheet}' li (sabse badi table)")
        return best
    finally:
        wb.close()


# ---------------------------------------------------------------- comparing
def _col(t: Table, want: str | None) -> int | None:
    if not want:
        return None
    w = hnorm(want)
    for i, h in enumerate(t.headers):
        if hnorm(h) == w:
            return i
    for i, h in enumerate(t.headers):
        if w and (w in hnorm(h) or hnorm(h) in w) and len(hnorm(h)) >= 2:
            return i
    if len(want) <= 3 and want.isalpha():          # a column letter: "B"
        from openpyxl.utils import column_index_from_string
        try:
            i = column_index_from_string(want.upper()) - 1
            return i if 0 <= i < len(t.headers) else None
        except Exception:
            return None
    return None


def _unique(t: Table, i: int) -> float:
    vals = [vnorm(v[i]) for _, v in t.rows if i < len(v) and vnorm(v[i])]
    return len(set(vals)) / len(vals) if vals else 0.0


def _filled(t: Table, i: int) -> float:
    return sum(1 for _, v in t.rows if i < len(v) and vnorm(v[i])) / max(1, len(t.rows))


def _macish(t: Table, i: int) -> float:
    vals = [v[i] for _, v in t.rows[:300] if i < len(v) and v[i] not in (None, "")]
    return sum(1 for x in vals if mac(x)) / len(vals) if vals else 0.0


def column_map(old: Table, new: Table) -> dict[int, int]:
    """old column index -> new column index (same heading, or nearly the same)."""
    out: dict[int, int] = {}
    used: set[int] = set()
    for i, h in enumerate(old.headers):
        n = hnorm(h)
        j = next((j for j, g in enumerate(new.headers) if j not in used and hnorm(g) == n), None)
        if j is not None:
            out[i] = j
            used.add(j)
    def family(n: str) -> str | None:
        for label, words in KEY_ORDER:
            if n in words:
                return label
        return None
    for i, h in enumerate(old.headers):     # "MAC" = "MAC Address", "Serial" = "Serial No", "Customer" = "Customer Name"
        if i in out:
            continue
        n = hnorm(h)
        fam = family(n)
        cands = [j for j, g in enumerate(new.headers) if j not in used and
                 ((fam and family(hnorm(g)) == fam) or
                  (min(len(n), len(hnorm(g))) >= 3 and (hnorm(g).startswith(n) or n.startswith(hnorm(g)))))]
        if len(cands) == 1:
            out[i] = cands[0]
            used.add(cands[0])
    for i, h in enumerate(old.headers):
        if i in out:
            continue
        n = hnorm(h)
        best, bs = None, 0.0
        for j, g in enumerate(new.headers):
            if j in used:
                continue
            r = difflib.SequenceMatcher(None, n, hnorm(g)).ratio()
            if r > bs:
                best, bs = j, r
        if best is not None and bs >= 0.84:
            out[i] = best
            used.add(best)
    return out


def pick_key(old: Table, new: Table, cmap: dict[int, int], skip: set[int]) -> tuple[int, int, str]:
    """(old index, new index, why). Strongest named key that is filled and unique in both; else MAC-looking values."""
    for label, words in KEY_ORDER:
        for i, h in enumerate(old.headers):
            if i in skip or i not in cmap or hnorm(h) in ROWNO_WORDS:
                continue
            hn = hnorm(h)
            if not any(hn == w or (len(w) >= 4 and hn.startswith(w)) for w in words):
                continue
            j = cmap[i]
            if _filled(old, i) >= 0.6 and _unique(old, i) >= 0.9 and _unique(new, j) >= 0.9:
                return i, j, f"'{h}' ({label}) dono files mein hai aur har line mein alag"
    for i in range(len(old.headers)):
        if i in skip or i not in cmap:
            continue
        if _macish(old, i) >= 0.8 and _macish(new, cmap[i]) >= 0.8:
            return i, cmap[i], f"'{old.headers[i]}' mein MAC address hain"
    best = None
    for i in range(len(old.headers)):
        if i in skip or i not in cmap or hnorm(old.headers[i]) in ROWNO_WORDS:
            continue
        u = min(_unique(old, i), _unique(new, cmap[i]))
        if u >= 0.97 and _filled(old, i) >= 0.8 and (best is None or u > best[2]):
            best = (i, cmap[i], u)
    if best:
        return best[0], best[1], f"'{old.headers[best[0]]}' har line mein alag hai"
    raise SheetError("Dono files mein milaan ke liye koi pakka column (MAC / serial / ID) nahi mila; "
                     "batayein kis column se milaun (key=...)")


def compare(old: Table, new: Table, key: str | None = None, update: list[str] | None = None,
            key_new: str | None = None) -> dict[str, Any]:
    cmap = column_map(old, new)
    upd_old: set[int] = set()
    for u in update or []:
        i = _col(old, u)
        if i is None:
            raise SheetError(f"Purani file mein '{u}' column nahi mila; columns: {', '.join(old.headers[:20])}")
        upd_old.add(i)
        if i not in cmap:
            j = _col(new, u)
            if j is None:
                raise SheetError(f"Nayi file mein '{u}' column nahi mila; columns: {', '.join(new.headers[:20])}")
            cmap[i] = j
    if key:
        ki = _col(old, key)
        if ki is None:
            raise SheetError(f"Purani file mein '{key}' column nahi mila; columns: {', '.join(old.headers[:20])}")
        kj = _col(new, key_new or key) if (key_new or ki not in cmap) else cmap[ki]
        if kj is None:
            raise SheetError(f"Nayi file mein '{key_new or key}' column nahi mila; columns: {', '.join(new.headers[:20])}")
        why = f"'{old.headers[ki]}' se milaya (aapne kaha)"
        cmap[ki] = kj
    else:
        ki, kj, why = pick_key(old, new, cmap, upd_old)
    if ki in upd_old:
        raise SheetError("Jis column se milaan ho raha hai wahi update nahi ho sakta; doosra key column batayein")
    compare_cols = sorted(upd_old) if upd_old else [i for i in cmap if i != ki]

    def index(t: Table, col: int) -> tuple[dict[str, tuple[int, list[Any]]], list[str], int]:
        out: dict[str, tuple[int, list[Any]]] = {}
        dupes: list[str] = []
        blank = 0
        for rn, vals in t.rows:
            k = vnorm(vals[col]) if col < len(vals) else ""
            if not k:
                blank += 1
                continue
            if k in out:
                dupes.append(shown(vals[col]))
                continue
            out[k] = (rn, vals)
        return out, dupes, blank

    oi, od, ob = index(old, ki)
    ni, nd, nb = index(new, kj)
    added, changed, missing = [], [], []
    for k, (rn, vals) in ni.items():
        if k not in oi:
            added.append({"key": shown(vals[kj]), "row_new": rn,
                          "values": {new.headers[j]: shown(vals[j]) for j in range(len(new.headers)) if vals[j] not in (None, "")}})
    for k, (rn, vals) in oi.items():
        if k not in ni:
            missing.append({"key": shown(vals[ki]), "row_old": rn,
                            "values": {old.headers[i]: shown(vals[i]) for i in range(len(old.headers)) if vals[i] not in (None, "")}})
            continue
        nrn, nvals = ni[k]
        cells = []
        for i in compare_cols:
            j = cmap.get(i)
            if j is None or j >= len(nvals):
                continue
            a, b = vals[i] if i < len(vals) else None, nvals[j]
            if vnorm(a) != vnorm(b):
                if vnorm(b) == "" and not upd_old:
                    continue          # an empty cell in the new file never wipes her data unless she asked for that column
                cells.append({"col": old.headers[i], "old": shown(a), "new": shown(b)})
        if cells:
            changed.append({"key": shown(vals[ki]), "row_old": rn, "row_new": nrn, "cells": cells})
    new_cols = [new.headers[j] for j in range(len(new.headers)) if j not in cmap.values()]
    return {"key": {"old": old.headers[ki], "new": new.headers[kj], "why": why},
            "sheets": {"old": old.sheet, "new": new.sheet},
            "columns": [{"old": old.headers[i], "new": new.headers[j]} for i, j in sorted(cmap.items())],
            "compare": [old.headers[i] for i in compare_cols],
            "new_columns": new_cols,
            "added": added, "changed": changed, "missing": missing,
            "dupes": {"old": od[:20], "new": nd[:20]}, "blank_keys": {"old": ob, "new": nb},
            "counts": {"old_rows": len(old.rows), "new_rows": len(new.rows), "added": len(added), "changed": len(changed),
                       "missing": len(missing), "same": len(oi) - len(changed) - len(missing)},
            "notes": old.notes + new.notes, "_cols": {"key_old": ki, "map": {str(i): j for i, j in cmap.items()}}}


def say(res: dict[str, Any]) -> str:
    c = res["counts"]
    parts = [f"Milaan '{res['key']['old']}' se: {c['changed']} badle", f"{c['added']} naye", f"{c['missing']} naye mein nahi",
             f"{c['same']} same"]
    if res["dupes"]["old"] or res["dupes"]["new"]:
        parts.append(f"dohraye gaye key: purani {len(res['dupes']['old'])}, nayi {len(res['dupes']['new'])}")
    return ", ".join(parts) + "."


# ---------------------------------------------------------------- applying (new copy)
def _typed(v: str, like: Any) -> Any:
    """The new value as a number / date when the old cell was one (keeps her number formats meaningful)."""
    if v in (None, ""):
        return None
    if isinstance(like, (int, float)) and not isinstance(like, bool):
        s = str(v).replace(",", "").strip()
        try:
            f = float(s)
            return int(f) if f.is_integer() and not isinstance(like, float) else f
        except ValueError:
            return v
    if isinstance(like, (datetime, date)):
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y %H:%M"):
            try:
                return datetime.strptime(str(v), fmt)
            except ValueError:
                continue
    return v


def _typed_from_new(cell_new: Any, like: Any) -> Any:
    if cell_new is None or isinstance(cell_new, (int, float, datetime, date)):
        return cell_new
    return _typed(str(cell_new), like)


def apply(old_name: str, old_data: bytes, new_name: str, new_data: bytes, res: dict[str, Any],
          add: bool = True, update: bool = True, missing: str = "keep", highlight: bool = False) -> tuple[bytes, dict[str, Any]]:
    """Returns (bytes of the updated copy, what was done). Raises SheetError."""
    old_t = load(old_name, old_data, res["sheets"]["old"] or None)
    new_t = load(new_name, new_data, res["sheets"]["new"] or None)
    ki = int(res["_cols"]["key_old"])
    cmap = {int(i): j for i, j in res["_cols"]["map"].items()}
    kj = cmap[ki]
    new_by = {vnorm(v[kj]): (rn, v) for rn, v in new_t.rows if kj < len(v) and vnorm(v[kj])}
    done = {"updated_cells": 0, "added_rows": 0, "missing_marked": 0, "missing_deleted": 0, "skipped_formula": [],
            "warnings": risky_parts(old_name, old_data)}
    changed_rows = {c["row_old"]: c for c in res["changed"]}
    upd_cols = {old_t.headers.index(c) for c in res["compare"] if c in old_t.headers}
    if old_t.kind == "csv":
        grid = _csv_rows(old_data)
        hdr = old_t.header_row - 1
        if update:
            for rn, ch in changed_rows.items():
                r = grid[rn - 1]
                key = vnorm(r[ki]) if ki < len(r) else ""
                if key not in new_by:
                    continue
                nv = new_by[key][1]
                want = {c["col"] for c in ch["cells"]}
                for i in upd_cols:
                    j = cmap.get(i)
                    if j is None or old_t.headers[i] not in want:
                        continue
                    while len(r) <= i:
                        r.append("")
                    r[i] = shown(nv[j])
                    done["updated_cells"] += 1
        if add:
            for a in res["added"]:
                nv = new_by.get(vnorm(a["key"]))
                if not nv:
                    continue
                row = ["" for _ in old_t.headers]
                for i, j in cmap.items():
                    row[i] = shown(nv[1][j])
                grid.append(row)
                done["added_rows"] += 1
        miss_rows = {m["row_old"] for m in res["missing"]}
        if missing == "delete" and miss_rows:
            grid = [r for n, r in enumerate(grid, start=1) if n not in miss_rows]
            done["missing_deleted"] = len(miss_rows)
        elif missing == "mark" and miss_rows:
            grid[hdr].append("Hoola milaan")
            for n in miss_rows:
                grid[n - 1].append("naye mein nahi")
            done["missing_marked"] = len(miss_rows)
        buf = io.StringIO()
        csv.writer(buf).writerows(grid)
        return buf.getvalue().encode("utf-8-sig"), done

    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill
    keep_vba = old_name.lower().endswith(".xlsm")
    wb = load_workbook(io.BytesIO(old_data), keep_vba=keep_vba)
    wb_vals = load_workbook(io.BytesIO(old_data), data_only=True, read_only=True)
    ws = wb[old_t.sheet]
    wsv = wb_vals[old_t.sheet]
    yellow = PatternFill("solid", fgColor="FFF59D")
    if update:
        for rn, ch in changed_rows.items():
            kv = wsv.cell(row=rn, column=ki + 1).value
            nv = new_by.get(vnorm(kv))
            if not nv:
                continue
            want = {c["col"] for c in ch["cells"]}
            for i in upd_cols:
                if old_t.headers[i] not in want:
                    continue
                j = cmap.get(i)
                if j is None:
                    continue
                cell = ws.cell(row=rn, column=i + 1)
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    done["skipped_formula"].append(f"{cell.coordinate}")
                    continue
                cell.value = _typed_from_new(nv[1][j], wsv.cell(row=rn, column=i + 1).value)
                if highlight:
                    cell.fill = yellow
                done["updated_cells"] += 1
    last = max((rn for rn, _ in old_t.rows), default=old_t.header_row)
    miss_rows = sorted({m["row_old"] for m in res["missing"]})
    if missing == "mark" and miss_rows:
        mc = len(old_t.headers) + 1
        hc = ws.cell(row=old_t.header_row, column=mc, value="Hoola milaan")
        src = ws.cell(row=old_t.header_row, column=len(old_t.headers))
        if src.has_style:
            hc._style = copy(src._style)
        for rn in miss_rows:
            ws.cell(row=rn, column=mc, value="naye mein nahi")
        done["missing_marked"] = len(miss_rows)
    if add and res["added"]:
        # a running serial number column (1, 2, 3...) keeps counting
        rowno = None
        for i, h in enumerate(old_t.headers):
            if hnorm(h) in ROWNO_WORDS:
                vals = [v[i] for _, v in old_t.rows if isinstance(v[i], (int, float))]
                if vals and len(vals) >= len(old_t.rows) * 0.8:
                    rowno = (i, int(max(vals)))
                break
        r = last
        if ws.max_row > last and any(ws.cell(row=x, column=c).value not in (None, "")
                                     for x in range(last + 1, min(ws.max_row, last + 30) + 1)
                                     for c in range(1, len(old_t.headers) + 1)):
            done["warnings"].append("table ke neeche kuch likha hai (jaise Total): naye rows uske upar daale; "
                                    "Total ka formula naye rows tak badhaiye")
        for a in res["added"]:
            nv = new_by.get(vnorm(a["key"]))
            if not nv:
                continue
            r += 1
            ws.insert_rows(r) if r <= ws.max_row else None
            for i in range(len(old_t.headers)):
                tgt = ws.cell(row=r, column=i + 1)
                srcc = ws.cell(row=last, column=i + 1)
                if srcc.has_style:
                    tgt._style = copy(srcc._style)
                j = cmap.get(i)
                if j is not None and j < len(nv[1]):
                    tgt.value = _typed_from_new(nv[1][j], wsv.cell(row=last, column=i + 1).value)
                elif rowno and i == rowno[0]:
                    rowno = (i, rowno[1] + 1)
                    tgt.value = rowno[1]
                if highlight and j is not None:
                    tgt.fill = yellow
            done["added_rows"] += 1
    if missing == "delete" and miss_rows:
        for rn in reversed(miss_rows):
            ws.delete_rows(rn)
        done["missing_deleted"] = len(miss_rows)
    wb_vals.close()
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue(), done
