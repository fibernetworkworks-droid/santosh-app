"""v0.999.237 DATA STEPS + EXPRESSIONS (R3 of the Hoola Route plan; owner: "GO R3").

Two things the route engine (dhara_tools.py) gains, kept here so the engine stays small:

1. EXPRESSIONS with maths and functions inside {{ }}: `{{ steps.order.output.total * 1.18 }}`,
   `{{ upper(vars.name) }}`, `{{ date_add(today(), 7) }}`, `{{ 'big' if vars.amount > 5000 else 'small' }}`.
   Parsed with Python's own parser and evaluated by a small walker that allows only reading her data (vars, steps, item),
   numbers / text / lists / objects, arithmetic, comparisons, `x if c else y` and the functions listed in FUNCS. No
   attribute of a Python object, no import, no call of anything else - nothing of Python ever runs. Capped in size and steps.
   A plain {{a.b.c}} keeps working exactly as before.

2. The DATA step (type "data", field "op"): sort, limit, dedupe, aggregate, split, compare, keep_fields, rename,
   fields (several values at once), date, text (HTML / XML / CSV / JSON / Base64 / URL), file (make CSV / Excel / PDF,
   read CSV / Excel / PDF / text) and crypto (hashes, HMAC, ids). Every value in the step is an expression first.
"""
from __future__ import annotations

import ast
import base64
import csv
import hashlib
import hmac
import io
import json
import math
import re
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, unquote
from zoneinfo import ZoneInfo

LIST_MAX = 10_000
TEXT_MAX = 2_000_000
NODES_MAX = 4_000


class ExprError(ValueError):
    pass


# ---------------------------------------------------------------- helpers
def _num(v: Any) -> float | int:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return v
    try:
        s = str(v).strip().replace(",", "")
        f = float(s)
        return int(f) if f.is_integer() and "." not in s and "e" not in s.lower() else f
    except (TypeError, ValueError):
        raise ExprError(f"'{str(v)[:40]}' is not a number")


def _list(v: Any, what: str = "This") -> list:
    if v is None:
        return []
    if isinstance(v, list):
        if len(v) > LIST_MAX:
            raise ExprError(f"{what} has more than {LIST_MAX} items")
        return v
    if isinstance(v, dict):
        return [v]
    raise ExprError(f"{what} is not a list")


def _get(obj: Any, path: str) -> Any:
    if path in ("", None):
        return obj
    cur = obj
    for part in str(path).strip().split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            i = int(part)
            cur = cur[i] if 0 <= i < len(cur) else None
        else:
            return None
    return cur


def _safe_replace(s: str, a: str, b: str) -> str:
    """v0.999.253: the size is worked out BEFORE the text is built (a huge result used to be built first)."""
    n = (len(s) + 1) if a == "" else s.count(a)
    if len(s) + n * (len(b) - len(a)) > TEXT_MAX:
        raise ExprError("The text is too long")
    return s.replace(a, b)


def _safe_join(items: list, sep: str) -> str:
    parts, size = [], 0
    for x in items:
        t = "" if x is None else str(x)
        size += len(t) + (len(sep) if parts else 0)
        if size > TEXT_MAX:
            raise ExprError("The text is too long")
        parts.append(t)
    return sep.join(parts)


def _cap_text(s: str) -> str:
    if len(s) > TEXT_MAX:
        raise ExprError("The text is too long")
    return s


def _dt(v: Any, tz: str = "") -> datetime:
    if isinstance(v, datetime):
        d = v
    elif isinstance(v, date):
        d = datetime(v.year, v.month, v.day)
    elif isinstance(v, (int, float)) and not isinstance(v, bool):
        d = datetime.fromtimestamp(float(v), tz=timezone.utc)
    else:
        from dateutil import parser as dp
        try:
            d = dp.parse(str(v))
        except (ValueError, OverflowError, TypeError):
            raise ExprError(f"'{str(v)[:40]}' is not a date")
    if tz:
        try:
            z = ZoneInfo(tz)
        except Exception:   # noqa: BLE001
            raise ExprError(f"Unknown time zone '{tz}'")
        d = d.replace(tzinfo=z) if d.tzinfo is None else d.astimezone(z)
    return d


_UNITS = {"second": "seconds", "seconds": "seconds", "minute": "minutes", "minutes": "minutes", "hour": "hours",
          "hours": "hours", "day": "days", "days": "days", "week": "weeks", "weeks": "weeks"}


def _iso(d: datetime) -> str:
    return d.isoformat(timespec="seconds") if (d.hour or d.minute or d.second or d.tzinfo) else d.date().isoformat()


def date_add(v: Any, n: Any = 1, unit: str = "days") -> str:
    d, n = _dt(v), _num(n)
    u = str(unit).lower()
    if u in ("month", "months", "year", "years"):
        from dateutil.relativedelta import relativedelta
        d = d + (relativedelta(months=int(n)) if u.startswith("month") else relativedelta(years=int(n)))
    elif u in _UNITS:
        d = d + timedelta(**{_UNITS[u]: n})
    else:
        raise ExprError(f"Unknown unit '{unit}' - use days, weeks, months, years, hours, minutes or seconds")
    return _iso(d)


def date_diff(a: Any, b: Any, unit: str = "days") -> float | int:
    da, db = _dt(a), _dt(b)
    if (da.tzinfo is None) != (db.tzinfo is None):
        da, db = da.replace(tzinfo=None), db.replace(tzinfo=None)
    secs = (db - da).total_seconds()
    div = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400, "weeks": 604800}.get(_UNITS.get(str(unit).lower(), ""), None)
    if div is None:
        raise ExprError(f"Unknown unit '{unit}'")
    r = secs / div
    return int(r) if float(r).is_integer() else round(r, 4)


def date_format(v: Any, fmt: str = "%d %b %Y", tz: str = "") -> str:
    fmt = str(fmt or "%d %b %Y")
    if len(fmt) > 60:
        raise ExprError("The date format is too long")
    return _dt(v, tz).strftime(fmt)


def now(tz: str = "") -> str:
    d = datetime.now(timezone.utc)
    return (d.astimezone(ZoneInfo(tz)) if tz else d).isoformat(timespec="seconds")


def today(tz: str = "") -> str:
    d = datetime.now(timezone.utc)
    return (d.astimezone(ZoneInfo(tz)) if tz else d).date().isoformat()


def _round(v: Any, n: Any = 0) -> float | int:
    r = round(_num(v), int(_num(n)))
    return int(r) if int(_num(n)) <= 0 else r


def _sort(v: Any, key: str = "", desc: Any = False) -> list:
    items = list(_list(v))
    try:
        return sorted(items, key=lambda x: (_get(x, key) is None, _get(x, key)), reverse=bool(desc))
    except TypeError:
        return sorted(items, key=lambda x: str(_get(x, key)), reverse=bool(desc))


def _unique(v: Any, key: str = "") -> list:
    seen, out = set(), []
    for x in _list(v):
        k = json.dumps(_get(x, key), sort_keys=True, default=str)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _avg(v: Any) -> float:
    xs = [_num(x) for x in _list(v)]
    return round(sum(xs) / len(xs), 6) if xs else 0


FUNCS: dict[str, Any] = {
    "upper": lambda s: str(s).upper(), "lower": lambda s: str(s).lower(), "title": lambda s: str(s).title(),
    "trim": lambda s: str(s).strip(), "len": lambda v: len(v) if isinstance(v, (str, list, dict)) else len(str(v)),
    "count": lambda v: len(_list(v)), "replace": lambda s, a, b: _cap_text(_safe_replace(str(s), str(a), str(b))),
    "split": lambda s, sep=",": [x.strip() for x in str(s).split(str(sep))][:LIST_MAX],
    "join": lambda v, sep=", ": _cap_text(_safe_join(_list(v), str(sep))),
    "slice": lambda v, a=0, b=None: v[int(_num(a)):(None if b is None else int(_num(b)))],
    "contains": lambda v, x: (x in v) if isinstance(v, (list, dict)) else (str(x) in str(v)),
    "starts_with": lambda s, x: str(s).startswith(str(x)), "ends_with": lambda s, x: str(s).endswith(str(x)),
    "text": lambda v: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else ("" if v is None else str(v)),
    "num": _num, "int": lambda v: int(_num(v)), "round": _round, "abs": lambda v: abs(_num(v)),
    "floor": lambda v: math.floor(_num(v)), "ceil": lambda v: math.ceil(_num(v)),
    "min": lambda *a: min(_num(x) for x in (_list(a[0]) if len(a) == 1 else a)),
    "max": lambda *a: max(_num(x) for x in (_list(a[0]) if len(a) == 1 else a)),
    "sum": lambda v: sum(_num(x) for x in _list(v)), "avg": _avg,
    "default": lambda v, d: d if v in (None, "", [], {}) else v,
    "json": lambda v: json.dumps(v, ensure_ascii=False), "parse_json": lambda s: json.loads(str(s)),
    "keys": lambda v: list(v.keys()) if isinstance(v, dict) else [], "values": lambda v: list(v.values()) if isinstance(v, dict) else [],
    "first": lambda v: (_list(v) or [None])[0], "last": lambda v: (_list(v) or [None])[-1],
    "sort": _sort, "unique": _unique, "pluck": lambda v, key: [_get(x, key) for x in _list(v)],
    "get": lambda v, path, d=None: (lambda r: d if r is None else r)(_get(v, path)),
    "now": now, "today": today, "date_add": date_add, "date_diff": date_diff, "date_format": date_format,
    "to_date": lambda v: _iso(_dt(v)),
}
_NAMES = {"true": True, "false": False, "null": None, "none": None}
_ROOTS = ("vars", "steps", "item", "env")   # v0.999.246: env = her route variables
_BIN = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b, ast.Mod: lambda a, b: a % b, ast.Pow: lambda a, b: a ** b}
_CMP = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
        ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b, ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}


def parse(src: str) -> ast.AST:
    try:
        return ast.parse(str(src).strip(), mode="eval").body
    except SyntaxError as e:
        raise ExprError(f"This is not a valid expression ({e.msg})")


def _ev(n: ast.AST, ctx: dict, budget: list) -> Any:
    budget[0] += 1
    if budget[0] > NODES_MAX:
        raise ExprError("The expression is too long")
    if isinstance(n, ast.Constant):
        if isinstance(n.value, (str, int, float, bool)) or n.value is None:
            return n.value
        raise ExprError("That kind of value is not allowed")
    if isinstance(n, ast.Name):
        k = n.id
        if k in _ROOTS:
            return ctx.get(k)
        if k.lower() in _NAMES:
            return _NAMES[k.lower()]
        if k in FUNCS:
            raise ExprError(f"{k} is a function - write {k}( )")
        raise ExprError(f"Unknown name '{k}' - start with vars, steps, item or env")
    if isinstance(n, ast.Attribute):
        return _get(_ev(n.value, ctx, budget), n.attr)
    if isinstance(n, ast.Subscript):
        obj = _ev(n.value, ctx, budget)
        if isinstance(n.slice, ast.Slice):
            lo = None if n.slice.lower is None else int(_num(_ev(n.slice.lower, ctx, budget)))
            hi = None if n.slice.upper is None else int(_num(_ev(n.slice.upper, ctx, budget)))
            return obj[lo:hi] if isinstance(obj, (list, str)) else None
        k = _ev(n.slice, ctx, budget)
        if isinstance(obj, dict):
            return obj.get(k if isinstance(k, str) else str(k))
        if isinstance(obj, (list, str)) and isinstance(k, (int, float)) and not isinstance(k, bool):
            i = int(k)
            return obj[i] if -len(obj) <= i < len(obj) else None
        return None
    if isinstance(n, ast.BinOp):
        op = _BIN.get(type(n.op))
        if op is None:
            raise ExprError("That operator is not allowed")
        a, b = _ev(n.left, ctx, budget), _ev(n.right, ctx, budget)
        if isinstance(n.op, ast.Add) and (isinstance(a, str) or isinstance(b, str)):
            return _cap_text(("" if a is None else str(a)) + ("" if b is None else str(b)))
        if isinstance(n.op, ast.Add) and isinstance(a, list) and isinstance(b, list):
            r = a + b
            if len(r) > LIST_MAX:
                raise ExprError("The list is too long")
            return r
        x, y = _num(a), _num(b)
        if isinstance(n.op, ast.Pow) and (abs(y) > 64 or abs(x) > 1e9):
            raise ExprError("That power is too big")
        if isinstance(n.op, (ast.Div, ast.FloorDiv, ast.Mod)) and y == 0:
            raise ExprError("Division by zero")
        r = op(x, y)
        return int(r) if isinstance(r, float) and r.is_integer() and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult)) and isinstance(x, int) and isinstance(y, int) else r
    if isinstance(n, ast.UnaryOp):
        v = _ev(n.operand, ctx, budget)
        if isinstance(n.op, ast.Not):
            return not v
        if isinstance(n.op, ast.USub):
            return -_num(v)
        if isinstance(n.op, ast.UAdd):
            return _num(v)
        raise ExprError("That operator is not allowed")
    if isinstance(n, ast.BoolOp):
        if isinstance(n.op, ast.And):
            v = True
            for x in n.values:
                v = _ev(x, ctx, budget)
                if not v:
                    return v
            return v
        v = False
        for x in n.values:
            v = _ev(x, ctx, budget)
            if v:
                return v
        return v
    if isinstance(n, ast.Compare):
        left = _ev(n.left, ctx, budget)
        for op, rn in zip(n.ops, n.comparators):
            right = _ev(rn, ctx, budget)
            f = _CMP.get(type(op))
            if f is None:
                raise ExprError("That comparison is not allowed")
            try:
                ok = f(left, right)
            except TypeError:
                try:
                    ok = f(_num(left), _num(right))
                except ExprError:
                    ok = f(str(left), str(right))
            if not ok:
                return False
            left = right
        return True
    if isinstance(n, ast.IfExp):
        return _ev(n.body, ctx, budget) if _ev(n.test, ctx, budget) else _ev(n.orelse, ctx, budget)
    if isinstance(n, ast.Call):
        if not isinstance(n.func, ast.Name) or n.func.id not in FUNCS or n.keywords:
            name = n.func.id if isinstance(n.func, ast.Name) else "that"
            raise ExprError(f"Unknown function '{name}'")
        args = [_ev(a, ctx, budget) for a in n.args]
        try:
            return FUNCS[n.func.id](*args)
        except ExprError:
            raise
        except TypeError:
            raise ExprError(f"{n.func.id}( ) got the wrong number of values")
        except (ValueError, KeyError, IndexError, ZeroDivisionError, OverflowError) as e:
            raise ExprError(f"{n.func.id}( ): {str(e)[:120] or type(e).__name__}")
    if isinstance(n, (ast.List, ast.Tuple)):
        if len(n.elts) > 200:
            raise ExprError("The list is too long")
        return [_ev(x, ctx, budget) for x in n.elts]
    if isinstance(n, ast.Dict):
        if len(n.keys) > 200 or any(k is None for k in n.keys):
            raise ExprError("That object is not allowed")
        return {str(_ev(k, ctx, budget)): _ev(v, ctx, budget) for k, v in zip(n.keys, n.values)}
    raise ExprError("That is not allowed in an expression")


def evaluate(src: str, ctx: dict) -> Any:
    if len(str(src)) > 2000:
        raise ExprError("The expression is too long")
    try:
        return _ev(parse(src), ctx, [0])
    except ExprError:
        raise
    except RecursionError:
        raise ExprError("The expression is nested too deep")
    except (TypeError, ValueError, OverflowError) as e:
        raise ExprError(str(e)[:160])


def check(src: str) -> str:
    """'' when the expression is well formed (names / functions allowed), else why not - no data needed."""
    try:
        tree = parse(src)
    except ExprError as e:
        return str(e)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and not (isinstance(n.func, ast.Name) and n.func.id in FUNCS):
            return f"Unknown function '{n.func.id if isinstance(n.func, ast.Name) else 'that'}'"
        if isinstance(n, ast.Name) and n.id not in _ROOTS and n.id.lower() not in _NAMES and n.id not in FUNCS:
            return f"Unknown name '{n.id}' - start with vars, steps, item or env"
        if isinstance(n, (ast.Lambda, ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp, ast.Starred,
                          ast.NamedExpr, ast.JoinedStr, ast.Await, ast.Yield, ast.YieldFrom, ast.Set)):
            return "That is not allowed in an expression"
    return ""


# ---------------------------------------------------------------- the data step
OPS = ("sort", "limit", "dedupe", "aggregate", "split", "compare", "keep_fields", "rename", "fields", "date", "text", "file", "crypto",
       "merge")
MERGE_MODES = ("append", "by_key", "by_position", "keep_matches", "keep_non_matches")   # v0.999.239 ROUTE R4
MERGE_JOINS = ("inner", "left", "outer")
TEXT_ACTIONS = ("html_text", "html_select", "xml_to_data", "csv_to_rows", "rows_to_csv", "json_parse", "json_text",
                "base64_encode", "base64_decode", "url_encode", "url_decode")
FILE_ACTIONS = ("make_csv", "make_xlsx", "make_pdf", "read")
CRYPTO_ACTIONS = ("sha256", "sha1", "md5", "hmac_sha256", "uuid", "random")
DATE_ACTIONS = ("format", "add", "subtract", "diff", "parse", "now")
HOW = ("count", "sum", "avg", "min", "max", "list", "join", "unique")


def validate(step: dict, sid: str) -> None:
    from .tools import ToolError
    op = str(step.get("op") or "")
    if op not in OPS:
        raise ToolError(f"Step '{sid}': a data step needs op = one of: {', '.join(OPS)}")
    need = {"sort": ("items",), "limit": ("items",), "dedupe": ("items",), "aggregate": ("items",), "split": ("items", "field"),
            "compare": ("a", "b"), "keep_fields": ("items", "fields"), "rename": ("items", "map"), "fields": ("values",),
            "date": ("action",), "text": ("action", "value"), "file": ("action",), "crypto": ("action",),
            "merge": ("a", "b")}[op]
    for k in need:
        if step.get(k) in (None, "", [], {}):
            raise ToolError(f"Step '{sid}': {op} needs {k}")
    act = str(step.get("action") or "")
    for o, allowed in (("text", TEXT_ACTIONS), ("file", FILE_ACTIONS), ("crypto", CRYPTO_ACTIONS), ("date", DATE_ACTIONS)):
        if op == o and act not in allowed:
            raise ToolError(f"Step '{sid}': {op} action must be one of: {', '.join(allowed)}")
    if op == "merge":
        mode = str(step.get("mode") or "append")
        if mode not in MERGE_MODES:
            raise ToolError(f"Step '{sid}': merge mode must be one of: {', '.join(MERGE_MODES)}")
        if mode in ("by_key", "keep_matches", "keep_non_matches") and not str(step.get("key") or "").strip():
            raise ToolError(f"Step '{sid}': merging {mode.replace('_', ' ')} needs the key field")
        if str(step.get("join") or "inner") not in MERGE_JOINS:
            raise ToolError(f"Step '{sid}': join must be one of: {', '.join(MERGE_JOINS)}")
    if op == "aggregate" and str(step.get("how") or "count") not in HOW:
        raise ToolError(f"Step '{sid}': how must be one of: {', '.join(HOW)}")
    if op in ("fields", "rename") and not isinstance(step.get("values" if op == "fields" else "map"), (dict, str)):
        raise ToolError(f"Step '{sid}': {op} needs an object of name: value")


def _fields_list(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def _obj(v: Any, what: str) -> dict:
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            raise ExprError(f"{what} must be an object like {{\"old\": \"new\"}}")
    if not isinstance(v, dict):
        raise ExprError(f"{what} must be an object")
    return v


def _store(tenant: str, name: str, data: bytes) -> dict:
    from ..mailbox import service as ms
    from ..pc.service import public_file
    if len(data) > 25 * 1024 * 1024:
        raise ExprError("The file would be over 25 MB")
    row = ms.store_bytes(tenant, name, data, "mail")
    return {k: v for k, v in public_file(row).items() if k != "pc_path"}


def _rows(items: list) -> tuple[list[str], list[list]]:
    cols: list[str] = []
    for it in items:
        if isinstance(it, dict):
            for k in it:
                if k not in cols:
                    cols.append(str(k))
    if not cols:
        return ["value"], [[x] for x in items]
    return cols, [[(it.get(c) if isinstance(it, dict) else None) for c in cols] for it in items]


def _cell(v: Any) -> Any:
    return v if isinstance(v, (int, float, str, bool)) or v is None else json.dumps(v, ensure_ascii=False)


def _file(tenant: str, step: dict, R) -> Any:
    act = step.get("action")
    name = str(R(step.get("name")) or "").strip()
    if act == "read":
        from ..mailbox import service as ms
        fid = str(R(step.get("file_id")) or "").strip()
        if not fid:
            raise ExprError("Give the file to read (its file id)")
        try:
            f = ms._file_row(tenant, fid)
        except Exception as e:   # noqa: BLE001
            raise ExprError(str(e)[:200])
        data = open(f.stored_path, "rb").read()
        low = (f.name or "").lower()
        if low.endswith(".csv"):
            return {"name": f.name, "rows": list(csv.DictReader(io.StringIO(data.decode("utf-8-sig", "replace"))))[:LIST_MAX]}
        if low.endswith((".xlsx", ".xlsm")):
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            ws = wb.worksheets[0]
            vals = list(ws.iter_rows(values_only=True))[: LIST_MAX + 1]
            head = [str(h if h is not None else f"col{i + 1}") for i, h in enumerate(vals[0])] if vals else []
            return {"name": f.name, "sheet": ws.title, "rows": [dict(zip(head, [(_cell(c)) for c in r])) for r in vals[1:]]}
        if low.endswith(".pdf"):
            from pypdf import PdfReader
            rd = PdfReader(io.BytesIO(data))
            return {"name": f.name, "pages": len(rd.pages), "text": _cap_text("\n".join((p.extract_text() or "") for p in rd.pages[:200]))}
        return {"name": f.name, "text": _cap_text(data.decode("utf-8", "replace"))}
    items = _list(R(step.get("items")), "The rows") if act in ("make_csv", "make_xlsx") else []
    if act == "make_csv":
        cols, rows = _rows(items)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        for r in rows:
            w.writerow([_cell(c) for c in r])
        return _store(tenant, (name or "rows") + ("" if name.lower().endswith(".csv") else ".csv"), buf.getvalue().encode("utf-8-sig"))
    if act == "make_xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = str(R(step.get("sheet")) or "Sheet1")[:31]
        cols, rows = _rows(items)
        ws.append(cols)
        for r in rows:
            ws.append([_cell(c) for c in r])
        buf = io.BytesIO()
        wb.save(buf)
        return _store(tenant, (name or "rows") + ("" if name.lower().endswith(".xlsx") else ".xlsx"), buf.getvalue())
    if act == "make_pdf":
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from xml.sax.saxutils import escape
        text = str(R(step.get("value")) or "")
        title = str(R(step.get("title")) or "")
        buf = io.BytesIO()
        st = getSampleStyleSheet()
        story = ([Paragraph(escape(title), st["Title"]), Spacer(1, 8)] if title else [])
        for para in _cap_text(text).split("\n\n")[:2000]:
            story.append(Paragraph(escape(para).replace("\n", "<br/>"), st["BodyText"]))
            story.append(Spacer(1, 6))
        SimpleDocTemplate(buf, pagesize=A4, title=title or name or "Document").build(story or [Paragraph("", st["BodyText"])])
        return _store(tenant, (name or "document") + ("" if name.lower().endswith(".pdf") else ".pdf"), buf.getvalue())
    raise ExprError("Unknown file action")


def _text(step: dict, R) -> Any:
    act = step.get("action")
    v = R(step.get("value"))
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else ("" if v is None else str(v))
    _cap_text(s)
    if act in ("html_text", "html_select"):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(s, "lxml")
        for t in soup(["script", "style"]):
            t.decompose()
        if act == "html_text":
            return re.sub(r"\n\s*\n+", "\n\n", soup.get_text("\n")).strip()
        sel = str(R(step.get("selector")) or "").strip()
        if not sel:
            raise ExprError("Give the part of the page to pick (a CSS selector, like h2 or .price)")
        attr = str(R(step.get("attr")) or "").strip()
        try:
            found = soup.select(sel)[:LIST_MAX]
        except Exception as e:   # noqa: BLE001
            raise ExprError(f"That selector is not valid ({str(e)[:80]})")
        return [(el.get(attr) if attr else el.get_text(" ", strip=True)) for el in found]
    if act == "xml_to_data":
        import xml.etree.ElementTree as ET
        if "<!DOCTYPE" in s.upper() or "<!ENTITY" in s.upper():
            raise ExprError("XML with a DOCTYPE or entities is not read (for safety)")
        try:
            root = ET.fromstring(s)
        except ET.ParseError as e:
            raise ExprError(f"This is not valid XML ({str(e)[:80]})")

        def conv(el):
            kids = list(el)
            d: dict[str, Any] = {f"@{k}": v for k, v in el.attrib.items()}
            if not kids:
                t = (el.text or "").strip()
                return t if not d else {**d, "#text": t}
            for k in kids:
                tag = re.sub(r"^\{.*\}", "", k.tag)
                val = conv(k)
                if tag in d:
                    d[tag] = d[tag] if isinstance(d[tag], list) else [d[tag]]
                    d[tag].append(val)
                else:
                    d[tag] = val
            return d
        return {re.sub(r"^\{.*\}", "", root.tag): conv(root)}
    if act == "csv_to_rows":
        delim = str(R(step.get("separator")) or ",")[:1] or ","
        return list(csv.DictReader(io.StringIO(s), delimiter=delim))[:LIST_MAX]
    if act == "rows_to_csv":
        cols, rows = _rows(_list(v, "The rows"))
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        for r in rows:
            w.writerow([_cell(c) for c in r])
        return buf.getvalue()
    if act == "json_parse":
        try:
            return json.loads(s)
        except ValueError as e:
            raise ExprError(f"This is not valid JSON ({str(e)[:80]})")
    if act == "json_text":
        return json.dumps(v, ensure_ascii=False, indent=2)
    if act == "base64_encode":
        return base64.b64encode(s.encode("utf-8")).decode("ascii")
    if act == "base64_decode":
        try:
            return base64.b64decode(s.encode("ascii"), validate=False).decode("utf-8", "replace")
        except Exception:   # noqa: BLE001
            raise ExprError("This is not valid Base64")
    if act == "url_encode":
        return quote(s, safe="")
    if act == "url_decode":
        return unquote(s)
    raise ExprError("Unknown text action")


def _merge(step: dict, R) -> list:
    """v0.999.239 ROUTE R4: two lists into one - one after the other, matched by a field (like a join),
    side by side by position, or keep only the rows of the first list that do (not) have a match."""
    a, b = _list(R(step.get("a")), "The first list"), _list(R(step.get("b")), "The second list")
    mode = str(step.get("mode") or "append")
    mix = lambda x, y: ({**x, **y} if isinstance(x, dict) and isinstance(y, dict)
                        else {"first": x, "second": y})
    if mode == "append":
        out = a + b
    elif mode == "by_position":
        n = max(len(a), len(b)) if str(step.get("keep") or "") == "all" else min(len(a), len(b))
        out = [mix(a[i] if i < len(a) else {}, b[i] if i < len(b) else {}) for i in range(n)]
    else:
        ka = str(R(step.get("key")) or "")
        kb = str(R(step.get("key_b")) or "") or ka
        jk = lambda v: json.dumps(v, sort_keys=True, default=str)
        index: dict[str, list] = {}
        for y in b:
            v = _get(y, kb)
            if v not in (None, ""):
                index.setdefault(jk(v), []).append(y)
        has = lambda x: _get(x, ka) not in (None, "") and jk(_get(x, ka)) in index
        if mode == "keep_matches":
            out = [x for x in a if has(x)]
        elif mode == "keep_non_matches":
            out = [x for x in a if not has(x)]
        else:
            join, out, used = str(step.get("join") or "inner"), [], set()
            for x in a:
                v = _get(x, ka)
                key = jk(v) if v not in (None, "") else None
                if key is not None and key in index:
                    used.add(key)
                    out.extend(mix(x, y) for y in index[key])
                elif join in ("left", "outer"):
                    out.append(x)
                if len(out) > LIST_MAX:
                    break
            if join == "outer":
                for key, ys in index.items():
                    if key not in used:
                        out.extend(ys)
    if len(out) > LIST_MAX:
        raise ExprError(f"More than {LIST_MAX} items")
    return out


def run(tenant: str, step: dict, ctx: dict, resolve) -> Any:
    """One data step. `resolve` is the engine's own resolve (expressions included)."""
    R = (lambda v: resolve(v, ctx))
    op = step.get("op")
    try:
        if op == "sort":
            return _sort(R(step.get("items")), str(R(step.get("by")) or ""), str(step.get("order") or "asc") == "desc")
        if op == "limit":
            items, n = _list(R(step.get("items"))), int(_num(R(step.get("count")) or 10))
            return items[-n:] if str(step.get("keep") or "first") == "last" and n else items[:max(0, n)]
        if op == "dedupe":
            return _unique(R(step.get("items")), str(R(step.get("by")) or ""))
        if op == "aggregate":
            items, field, how = _list(R(step.get("items"))), str(R(step.get("field")) or ""), str(step.get("how") or "count")
            vals = [_get(x, field) for x in items]
            if how == "count":
                return len([x for x in vals if x not in (None, "")]) if field else len(items)
            if how == "sum":
                return sum(_num(x) for x in vals if x not in (None, ""))
            if how == "avg":
                return _avg([x for x in vals if x not in (None, "")])
            if how in ("min", "max"):
                xs = [_num(x) for x in vals if x not in (None, "")]
                return (min(xs) if how == "min" else max(xs)) if xs else None
            if how == "list":
                return vals
            if how == "unique":
                return _unique(vals)
            return _cap_text(str(R(step.get("sep")) or ", ").join("" if x is None else str(x) for x in vals))
        if op == "split":
            out = []
            for it in _list(R(step.get("items"))):
                v = _get(it, str(R(step.get("field")) or ""))
                out.extend(v if isinstance(v, list) else ([] if v is None else [v]))
                if len(out) > LIST_MAX:
                    raise ExprError(f"More than {LIST_MAX} items")
            return out
        if op == "compare":
            a, b, key = _list(R(step.get("a")), "The first list"), _list(R(step.get("b")), "The second list"), str(R(step.get("key")) or "")
            ka = {json.dumps(_get(x, key), sort_keys=True, default=str): x for x in a}
            kb = {json.dumps(_get(x, key), sort_keys=True, default=str): x for x in b}
            added = [kb[k] for k in kb if k not in ka]
            removed = [ka[k] for k in ka if k not in kb]
            changed = [{"before": ka[k], "after": kb[k]} for k in kb if k in ka and ka[k] != kb[k]]
            same = [kb[k] for k in kb if k in ka and ka[k] == kb[k]]
            return {"added": added, "removed": removed, "changed": changed, "same": same,
                    "counts": {"added": len(added), "removed": len(removed), "changed": len(changed), "same": len(same)}}
        if op == "merge":
            return _merge(step, R)
        if op == "keep_fields":
            fs = _fields_list(R(step.get("fields")))
            drop = str(step.get("mode") or "keep") == "drop"
            res = [({k: v for k, v in it.items() if (k in fs) != drop} if isinstance(it, dict) else it) for it in _list(R(step.get("items")))]
            return res
        if op == "rename":
            mp = _obj(R(step.get("map")), "The names")
            raw = R(step.get("items"))
            one = isinstance(raw, dict)
            res = [({mp.get(k, k): v for k, v in it.items()} if isinstance(it, dict) else it) for it in _list(raw)]
            return res[0] if one else res
        if op == "fields":
            vals = step.get("values")
            if isinstance(vals, str):
                vals = _obj(vals, "The values")
            return {str(k): R(v) for k, v in vals.items()}
        if op == "date":
            act = step.get("action")
            tz = str(R(step.get("tz")) or "")
            if act == "now":
                return now(tz)
            v = R(step.get("value"))
            if act == "format":
                return date_format(v, str(R(step.get("format")) or "%d %b %Y"), tz)
            if act in ("add", "subtract"):
                n = _num(R(step.get("amount")) or 0)
                return date_add(v, -n if act == "subtract" else n, str(step.get("unit") or "days"))
            if act == "diff":
                return date_diff(v, R(step.get("other")), str(step.get("unit") or "days"))
            return _iso(_dt(v, tz))
        if op == "text":
            return _text(step, R)
        if op == "file":
            return _file(tenant, step, R)
        if op == "crypto":
            act = step.get("action")
            if act == "uuid":
                return str(uuid.uuid4())
            if act == "random":
                n = max(4, min(int(_num(R(step.get("length")) or 16)), 128))
                return secrets.token_urlsafe(n)[:n]
            s = R(step.get("value"))
            b = (s if isinstance(s, str) else json.dumps(s, ensure_ascii=False, sort_keys=True)).encode("utf-8")
            if act == "hmac_sha256":
                key = str(R(step.get("secret")) or "")
                if not key:
                    raise ExprError("HMAC needs a secret")
                return hmac.new(key.encode("utf-8"), b, hashlib.sha256).hexdigest()
            return getattr(hashlib, act)(b).hexdigest()
    except ExprError:
        raise
    except (TypeError, ValueError, KeyError, OSError) as e:
        raise ExprError(str(e)[:200] or type(e).__name__)
    raise ExprError("Unknown data step")
