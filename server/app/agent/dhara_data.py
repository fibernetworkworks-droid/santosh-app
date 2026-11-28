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

# ---------------------------------------------------------------- v0.999.254 MAKE PARITY: Make's own functions
# The function list of Make's help centre (general, math, text and binary, date and time, array), each under its
# snake_case name AND Make's own camelCase name, so a formula from Make works as written once its ';' are ','.
# `if` is a Python word, so if(c, a, b) is read as iff(c, a, b) (rewritten before parsing).
_MOMENT = re.compile(r"\[[^\]]*\]|YYYY|YY|Y|Qo|Q|MMMM|MMM|MM|Mo|M|DDDD|DDDo|DDD|DD|Do|D|dddd|ddd|dd|do|d|E|"
                     r"wo|ww|w|Wo|WW|W|gggg|gg|GGGG|GG|HH|H|hh|h|kk|k|A|a|mm|m|ss|s|S{1,9}|ZZ|Z|X|x")
_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"]
_WDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def _ord(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def moment_format(d: datetime, fmt: str) -> str:
    """Make's (Moment.js) date tokens: YYYY-MM-DD HH:mm, Do MMMM, dddd, X ... Text in [brackets] stays as it is."""
    iso = d.isocalendar()
    wd = (d.weekday() + 1) % 7                       # 0 = Sunday, Make's d
    h12 = d.hour % 12 or 12
    off = d.utcoffset()

    def z(sep: str) -> str:
        if off is None:
            return f"+00{sep}00"
        m = int(off.total_seconds() // 60)
        sg = "-" if m < 0 else "+"
        m = abs(m)
        return f"{sg}{m // 60:02d}{sep}{m % 60:02d}"
    week = int(d.strftime("%U")) + 1
    tok = {"YYYY": f"{d.year:04d}", "YY": f"{d.year % 100:02d}", "Y": str(d.year), "Q": str((d.month - 1) // 3 + 1),
           "Qo": _ord((d.month - 1) // 3 + 1), "MMMM": _MONTHS[d.month - 1], "MMM": _MONTHS[d.month - 1][:3],
           "MM": f"{d.month:02d}", "Mo": _ord(d.month), "M": str(d.month), "DDDD": f"{d.timetuple().tm_yday:03d}",
           "DDDo": _ord(d.timetuple().tm_yday), "DDD": str(d.timetuple().tm_yday), "DD": f"{d.day:02d}", "Do": _ord(d.day),
           "D": str(d.day), "dddd": _WDAYS[wd], "ddd": _WDAYS[wd][:3], "dd": _WDAYS[wd][:2], "do": _ord(wd), "d": str(wd),
           "E": str(iso[2]), "w": str(week), "wo": _ord(week), "ww": f"{week:02d}", "W": str(iso[1]), "Wo": _ord(iso[1]),
           "WW": f"{iso[1]:02d}", "gggg": f"{d.year:04d}", "gg": f"{d.year % 100:02d}", "GGGG": f"{iso[0]:04d}",
           "GG": f"{iso[0] % 100:02d}", "HH": f"{d.hour:02d}", "H": str(d.hour), "hh": f"{h12:02d}", "h": str(h12),
           "kk": f"{d.hour or 24:02d}", "k": str(d.hour or 24), "A": "AM" if d.hour < 12 else "PM",
           "a": "am" if d.hour < 12 else "pm", "mm": f"{d.minute:02d}", "m": str(d.minute), "ss": f"{d.second:02d}",
           "s": str(d.second), "ZZ": z(""), "Z": z(":"),
           "X": str(int(d.timestamp())), "x": str(int(d.timestamp() * 1000))}

    def one(mm):
        t = mm.group(0)
        if t.startswith("["):
            return t[1:-1]
        if t.startswith("S"):
            return f"{d.microsecond:06d}{'0' * 3}"[:len(t)]
        return tok.get(t, t)
    return _MOMENT.sub(one, fmt)


_STRP = {"YYYY": "%Y", "YY": "%y", "MMMM": "%B", "MMM": "%b", "MM": "%m", "M": "%m", "DD": "%d", "D": "%d", "Do": "%d",
         "dddd": "%A", "ddd": "%a", "HH": "%H", "H": "%H", "hh": "%I", "h": "%I", "kk": "%H", "k": "%H", "mm": "%M",
         "m": "%M", "ss": "%S", "s": "%S", "A": "%p", "a": "%p", "ZZ": "%z", "Z": "%z", "SSS": "%f", "SS": "%f", "S": "%f",
         "DDDD": "%j", "DDD": "%j"}


def parse_date(text: Any, fmt: Any = "", tz: Any = "") -> str:
    """Make's parseDate(text; format; [timezone]). Without a format, any common date is read."""
    t, f, tz = str(text or "").strip(), str(fmt or ""), str(tz or "")
    if not f:
        return _iso(_dt(t, tz))
    if f.strip() in ("X", "x"):
        n = float(_num(t)) / (1000 if f.strip() == "x" else 1)
        d = datetime.fromtimestamp(n, tz=timezone.utc)
        return _iso(d.astimezone(ZoneInfo(tz)) if tz else d)
    if "%" in f:
        py = f
    else:
        def one(mm):
            tk = mm.group(0)
            if tk.startswith("["):
                return tk[1:-1].replace("%", "%%")
            if tk in _STRP:
                return _STRP[tk]
            raise ExprError(f"parse_date cannot read the token '{tk}'")
        py = _MOMENT.sub(one, f)
        t = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", t) if "Do" in f else t
    try:
        d = datetime.strptime(t, py)
    except ValueError:
        raise ExprError(f"'{t[:40]}' does not match the format '{f[:40]}'")
    if tz and d.tzinfo is None:
        d = d.replace(tzinfo=ZoneInfo(tz))
    return _iso(d)


def format_date(v: Any, fmt: Any = "YYYY-MM-DD", tz: Any = "") -> str:
    """Make's formatDate(date; format; [timezone]): Make tokens (YYYY-MM-DD), or %-codes."""
    f = str(fmt or "YYYY-MM-DD")
    if len(f) > 80:
        raise ExprError("The date format is too long")
    d = _dt(v, str(tz or ""))
    return d.strftime(f) if "%" in f else moment_format(d, f)


def _date_set(v: Any, what: str, n: Any) -> str:
    d = _dt(v)
    if what == "day":                               # Make's setDay: 1 = Sunday .. 7 = Saturday, or a day name
        if isinstance(n, str) and not n.strip().isdigit():
            names = [w.lower() for w in _WDAYS]
            key = n.strip().lower()
            hit = [i for i, w in enumerate(names) if w.startswith(key[:3])]
            if not hit:
                raise ExprError(f"'{n}' is not a day name")
            want = hit[0]
        else:
            want = int(_num(n)) - 1
        cur = (d.weekday() + 1) % 7
        return _iso(d + timedelta(days=want - cur))
    if what == "month" and isinstance(n, str) and not n.strip().isdigit():
        hit = [i for i, m in enumerate(_MONTHS) if m.lower().startswith(n.strip().lower()[:3])]
        if not hit:
            raise ExprError(f"'{n}' is not a month name")
        n = hit[0] + 1
    k = int(_num(n))
    from dateutil.relativedelta import relativedelta
    if what == "second":
        return _iso(d.replace(second=0) + timedelta(seconds=k))
    if what == "minute":
        return _iso(d.replace(minute=0) + timedelta(minutes=k))
    if what == "hour":
        return _iso(d.replace(hour=0) + timedelta(hours=k))
    if what == "date":
        return _iso(d.replace(day=1) + timedelta(days=k - 1))
    if what == "month":
        return _iso(d.replace(month=1) + relativedelta(months=k - 1))
    if what == "year":
        return _iso(d.replace(year=max(1, min(k, 9999))))
    raise ExprError("Unknown date part")


def _iff(cond: Any, a: Any = None, b: Any = None) -> Any:
    return a if cond else b


def _ifempty(a: Any, b: Any) -> Any:
    return b if a in (None, "", [], {}) else a


def _switch(v: Any, *pairs: Any) -> Any:
    rest = list(pairs)
    while len(rest) >= 2:
        k, r = rest.pop(0), rest.pop(0)
        if v == k or (not isinstance(v, (dict, list)) and str(v) == str(k)):
            return r
    return rest[0] if rest else None


def _omit(obj: Any, *keys: Any) -> Any:
    ks = {str(k) for k in keys}
    return {k: v for k, v in obj.items() if k not in ks} if isinstance(obj, dict) else obj


def _pick(obj: Any, *keys: Any) -> Any:
    ks = [str(k) for k in keys]
    return {k: obj[k] for k in ks if k in obj} if isinstance(obj, dict) else obj


def _set_path(obj: Any, path: Any, value: Any) -> Any:
    out = json.loads(json.dumps(obj if isinstance(obj, (dict, list)) else {}, default=str))
    cur = out
    parts = [p for p in str(path).split(".") if p]
    if not parts:
        return value
    for i, p in enumerate(parts):
        last = i == len(parts) - 1
        if isinstance(cur, list) and p.isdigit():
            j = int(p)
            while len(cur) <= j:
                cur.append(None)
            if last:
                cur[j] = value
            else:
                cur[j] = cur[j] if isinstance(cur[j], (dict, list)) else {}
                cur = cur[j]
        elif isinstance(cur, dict):
            if last:
                cur[p] = value
            else:
                cur[p] = cur.get(p) if isinstance(cur.get(p), (dict, list)) else {}
                cur = cur[p]
        else:
            break
    return out


def _flatten(v: Any, depth: int = 0) -> list:
    out: list = []
    for x in _list(v):
        if isinstance(x, list) and depth < 20:
            out.extend(_flatten(x, depth + 1))
        else:
            out.append(x)
        if len(out) > LIST_MAX:
            raise ExprError("The list is too long")
    return out


def _map(v: Any, key: Any, fkey: Any = None, fvals: Any = None) -> list:
    items = _list(v)
    if fkey not in (None, ""):
        want = {s.strip() for s in str(fvals or "").split(",")}
        items = [x for x in items if str(_get(x, str(fkey))) in want]
    return [_get(x, str(key)) for x in items]


def _sort_make(v: Any, order: Any = "asc", key: Any = "") -> list:
    o = str(order or "asc").lower()
    items = list(_list(v))
    ci = o.endswith(" ci")

    def k(x):
        y = _get(x, str(key or ""))
        return (y is None, str(y).lower() if ci else y)
    try:
        return sorted(items, key=k, reverse=o.startswith("desc"))
    except TypeError:
        return sorted(items, key=lambda x: str(_get(x, str(key or ""))), reverse=o.startswith("desc"))


def _distinct(v: Any, key: Any = "") -> list:
    return _unique(v, str(key or ""))


def _to_collection(v: Any, key: Any, value: Any) -> dict:
    return {str(_get(x, str(key))): _get(x, str(value)) for x in _list(v)}


def _to_array(v: Any) -> list:
    return [{"key": k, "value": x} for k, x in v.items()] if isinstance(v, dict) else _list(v)


def _array_diff(a: Any, b: Any) -> list:
    bb = [json.dumps(x, sort_keys=True, default=str) for x in _list(b)]
    return [x for x in _list(a) if json.dumps(x, sort_keys=True, default=str) not in bb]


def _array_intersect(a: Any, b: Any) -> list:
    bb = [json.dumps(x, sort_keys=True, default=str) for x in _list(b)]
    return [x for x in _list(a) if json.dumps(x, sort_keys=True, default=str) in bb]


def _merge_arrays(*arrs: Any) -> list:
    out: list = []
    for a in arrs:
        out.extend(_list(a))
        if len(out) > LIST_MAX:
            raise ExprError("The list is too long")
    return out


def _shuffle(v: Any) -> list:
    out = list(_list(v))
    secrets.SystemRandom().shuffle(out)
    return out


def _nums(a: tuple) -> list:
    return [_num(x) for x in (_list(a[0]) if len(a) == 1 and isinstance(a[0], list) else a) if x not in (None, "")]


def _median(*a: Any) -> float | int:
    xs = sorted(_nums(a))
    if not xs:
        return 0
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _stdev(a: tuple, sample: bool) -> float:
    xs = _nums(a)
    n = len(xs)
    if n < (2 if sample else 1):
        return 0
    m = sum(xs) / n
    return round(math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1 if sample else n)), 10)


def _format_number(v: Any, decimals: Any = 0, dec_sep: Any = ",", thou_sep: Any = ".") -> str:
    """Make's formatNumber(number; decimals; [decimal separator]; [thousands separator]) - Make's own defaults."""
    n = int(_num(decimals))
    s = f"{float(_num(v)):,.{max(0, min(n, 20))}f}"
    return s.replace(",", "\x00").replace(".", str(dec_sep)).replace("\x00", str(thou_sep))


def _parse_number(v: Any, dec_sep: Any = ".") -> float | int:
    s = str(v).strip()
    ds = str(dec_sep or ".")
    other = "," if ds == "." else "."
    s = s.replace(" ", "").replace(" ", "").replace(other, "").replace(ds, ".")
    s = re.sub(r"[^0-9.\-+eE]", "", s)
    return _num(s)


def _trunc(v: Any, digits: Any = 0) -> float | int:
    k = int(_num(digits))
    f = 10 ** k
    r = math.trunc(_num(v) * f) / f
    return int(r) if k <= 0 else r


def _regex(pat: str) -> tuple[re.Pattern, bool]:
    m = re.fullmatch(r"/(.*)/([gimsuy]*)", pat, re.S)
    if not m:
        return re.compile(re.escape(pat)), True
    if len(m.group(1)) > 500:
        raise ExprError("The pattern is too long")
    fl = 0
    for c in m.group(2):
        fl |= {"i": re.I, "m": re.M, "s": re.S}.get(c, 0)
    try:
        return re.compile(m.group(1), fl), "g" in m.group(2)
    except re.error as e:
        raise ExprError(f"The pattern is not valid ({e})")


def _replace_make(s: Any, search: Any, rep: Any) -> str:
    """Make's replace: plain text, or /regex/flags with $& and $1 in the replacement."""
    text, pat = str(s if s is not None else ""), str(search if search is not None else "")
    rp = str(rep if rep is not None else "")
    if not re.fullmatch(r"/.*/[gimsuy]*", pat, re.S):
        return _cap_text(_safe_replace(text, pat, rp))
    rx, glob = _regex(pat)
    py = re.sub(r"\$(\d+)", r"\\g<\1>", rp.replace("\\", "\\\\")).replace("$&", r"\g<0>")
    return _cap_text(rx.sub(py, text, count=0 if glob else 1))


def _match(s: Any, pat: Any) -> Any:
    """The first match of /pattern/ (with its groups), or every match with g."""
    rx, glob = _regex(str(pat))
    text = str(s if s is not None else "")[:TEXT_MAX]
    if glob:
        return [m.group(0) for m in rx.finditer(text)][:LIST_MAX]
    m = rx.search(text)
    return None if m is None else ([m.group(0)] + list(m.groups()))


def _ascii(s: Any, strip_marks: Any = False) -> str:
    t = str(s if s is not None else "")
    if strip_marks:
        import unicodedata
        t = unicodedata.normalize("NFKD", t)
    return t.encode("ascii", "ignore").decode()


def _strip_html(s: Any) -> str:
    import html as _h
    return _h.unescape(re.sub(r"<[^>]+>", "", str(s if s is not None else "")))


def _escape_md(s: Any) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|>~])", r"\\\1", str(s if s is not None else ""))


def _hash(algo: str, s: Any, enc: Any = "hex", key: Any = None) -> str:
    b = (s if isinstance(s, str) else json.dumps(s, ensure_ascii=False)).encode("utf-8")
    if key not in (None, ""):
        dig = hmac.new(str(key).encode("utf-8"), b, getattr(hashlib, algo)).digest()
    else:
        dig = hashlib.new(algo, b).digest()
    e = str(enc or "hex").lower()
    return base64.b64encode(dig).decode() if e == "base64" else dig.decode("latin1") if e == "latin1" else dig.hex()


def _remove_emoji(s: Any) -> str:
    return re.sub("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\uFE0F\u200d]", "",
                  str(s if s is not None else ""))


def _to_binary(v: Any, enc: Any = "") -> str:
    e = str(enc or "").lower()
    b = str(v if v is not None else "").encode("utf-8")
    if e == "base64":
        return base64.b64decode(str(v)).hex()
    if e == "hex":
        return bytes.fromhex(str(v)).hex()
    return b.hex()


def _index_of(s: Any, x: Any, start: Any = 0) -> int:
    if isinstance(s, list):
        try:
            return s.index(x, int(_num(start)))
        except ValueError:
            return -1
    return str(s if s is not None else "").find(str(x), int(_num(start)))


def _length(v: Any) -> int:
    if isinstance(v, (str, list, dict)):
        return len(v)
    return 0 if v is None else len(str(v))


MAKE_FUNCS: dict[str, Any] = {
    # general
    "iff": _iff, "ifempty": _ifempty, "switch": _switch, "omit": _omit, "pick": _pick, "equal": lambda a, b: a == b,
    "set": _set_path, "get": lambda v, path, d=None: (lambda r: d if r is None else r)(_get(v, str(path))),
    # math
    "average": lambda *a: (round(sum(_nums(a)) / len(_nums(a)), 10) if _nums(a) else 0), "median": _median,
    "stdev_p": lambda *a: _stdev(a, False), "stdev_s": lambda *a: _stdev(a, True), "format_number": _format_number,
    "parse_number": _parse_number, "trunc": _trunc, "sum": lambda *a: sum(_nums(a)),
    "max": lambda *a: (max(_nums(a)) if _nums(a) else None), "min": lambda *a: (min(_nums(a)) if _nums(a) else None),
    # text and binary
    "ascii": _ascii, "base64": lambda s: base64.b64encode(str(s).encode("utf-8")).decode(),
    "unbase64": lambda s: base64.b64decode(str(s)).decode("utf-8", "replace"),
    "capitalize": lambda s: (lambda t: t[:1].upper() + t[1:])(str(s if s is not None else "")),
    "startcase": lambda s: " ".join(w[:1].upper() + w[1:] for w in str(s if s is not None else "").split(" ")),
    "decode_url": lambda s: unquote(str(s)), "encode_url": lambda s: quote(str(s), safe=""),
    "escape_html": lambda s: __import__("html").escape(str(s if s is not None else "")),
    "escape_json": lambda s: json.dumps(str(s if s is not None else ""), ensure_ascii=False)[1:-1],
    "escape_markdown": _escape_md, "index_of": _index_of, "length": _length,
    "md5": lambda s: _hash("md5", s), "sha1": lambda s, e="hex", k=None: _hash("sha1", s, e, k),
    "sha256": lambda s, e="hex", k=None, ke=None: _hash("sha256", s, e, k),
    "sha512": lambda s, e="hex", k=None, ke=None: _hash("sha512", s, e, k),
    "replace": _replace_make, "match": _match, "replace_emoji": _remove_emoji, "strip_html": _strip_html,
    "substring": lambda s, a=0, b=None: str(s if s is not None else "")[int(_num(a)):(None if b is None else int(_num(b)))],
    "to_binary": _to_binary, "to_string": lambda v: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    if isinstance(v, (dict, list)) else ("" if v is None else str(v)),
    "split": lambda s, sep=",": [x for x in str(s if s is not None else "").split(str(sep))][:LIST_MAX],
    # date and time
    "format_date": format_date, "parse_date": parse_date,
    "add_seconds": lambda d, n: date_add(d, n, "seconds"), "add_minutes": lambda d, n: date_add(d, n, "minutes"),
    "add_hours": lambda d, n: date_add(d, n, "hours"), "add_days": lambda d, n: date_add(d, n, "days"),
    "add_months": lambda d, n: date_add(d, n, "months"), "add_years": lambda d, n: date_add(d, n, "years"),
    "set_second": lambda d, n: _date_set(d, "second", n), "set_minute": lambda d, n: _date_set(d, "minute", n),
    "set_hour": lambda d, n: _date_set(d, "hour", n), "set_day": lambda d, n: _date_set(d, "day", n),
    "set_date": lambda d, n: _date_set(d, "date", n), "set_month": lambda d, n: _date_set(d, "month", n),
    "set_year": lambda d, n: _date_set(d, "year", n), "timestamp": lambda d=None: int((_dt(d) if d not in (None, "")
    else datetime.now(timezone.utc)).timestamp()),
    # array
    "add": lambda arr, *xs: _merge_arrays(arr, list(xs)), "remove": lambda arr, *xs: [x for x in _list(arr) if x not in xs],
    "array_diff": _array_diff, "array_intersect": _array_intersect, "deduplicate": lambda v: _unique(v),
    "distinct": _distinct, "flatten": _flatten, "map": _map, "merge": _merge_arrays,
    "reverse": lambda v: list(reversed(_list(v))) if not isinstance(v, str) else v[::-1], "shuffle": _shuffle,
    "sort": lambda v, a="", b=None: (_sort_make(v, a, b or "") if str(a).lower() in ("asc", "desc", "asc ci", "desc ci")
                                     else _sort(v, str(a or ""), b)), "to_array": _to_array, "to_collection": _to_collection,
    "range": lambda a, b=None, st=1: (lambda r: r if len(r) <= LIST_MAX else (_ for _ in ()).throw(ExprError("The range is too long")))(
        list(range(int(_num(a)), int(_num(b)), int(_num(st)) or 1)) if b is not None else list(range(int(_num(a))))),
}
# Make's own camelCase names (and a few of its spellings) point to the same functions
for _mk, _ours in {"formatDate": "format_date", "parseDate": "parse_date", "addSeconds": "add_seconds",
                   "addMinutes": "add_minutes", "addHours": "add_hours", "addDays": "add_days", "addMonths": "add_months",
                   "addYears": "add_years", "setSecond": "set_second", "setMinute": "set_minute", "setHour": "set_hour",
                   "setDay": "set_day", "setDate": "set_date", "setMonth": "set_month", "setYear": "set_year",
                   "formatNumber": "format_number", "parseNumber": "parse_number", "stdevP": "stdev_p",
                   "stdevS": "stdev_s", "decodeURL": "decode_url", "encodeURL": "encode_url", "escapeHTML": "escape_html",
                   "escapeJSON": "escape_json", "escapeMarkdown": "escape_markdown", "indexOf": "index_of",
                   "replaceEmojiCharacters": "replace_emoji", "stripHTML": "strip_html", "toBinary": "to_binary",
                   "toString": "to_string", "arrayDiff": "array_diff", "arrayIntersect": "array_intersect",
                   "toArray": "to_array", "toCollection": "to_collection", "dateDifference": "date_diff"}.items():
    MAKE_FUNCS[_mk] = MAKE_FUNCS.get(_ours) or _ours

_NAMES = {"true": True, "false": False, "null": None, "none": None}
for _k, _f in MAKE_FUNCS.items():
    if isinstance(_f, str):
        _f = FUNCS.get(_f) or MAKE_FUNCS.get(_f)
    if _k in ("split", "get") and _k in FUNCS:
        continue                                     # ours already work the same way, with the older argument order
    FUNCS[_k] = _f
FUNCS["date_format"] = format_date                   # %-codes as before, and Make's tokens (YYYY-MM-DD)
FUNCS["if_"] = _iff


def _kw_random() -> float:
    return secrets.SystemRandom().random()


# Make's built-in keywords, read without ( ): now, timestamp, uuid, random, pi, newline, space, tab ...
KEYWORDS: dict[str, Any] = {"now": lambda: now(), "today": lambda: today(), "timestamp": lambda: int(datetime.now(timezone.utc).timestamp()),
                            "uuid": lambda: str(uuid.uuid4()), "random": _kw_random, "pi": lambda: math.pi,
                            "newline": lambda: "\n", "space": lambda: " ", "tab": lambda: "\t",
                            "carriage_return": lambda: "\r", "empty_string": lambda: "", "emptystring": lambda: "",
                            "empty_array": lambda: [], "emptyarray": lambda: [], "erase": lambda: None}

_ROOTS = ("vars", "steps", "item", "env", "run", "error")   # v0.999.246: env = her route variables
_BIN = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b, ast.Mod: lambda a, b: a % b, ast.Pow: lambda a, b: a ** b}
_CMP = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
        ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b, ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}


_IF_CALL = re.compile(r"(?<![A-Za-z0-9_.])if\s*\(")


def _prep(src: str) -> str:
    """Make's if(c; a; b) - `if` is a Python word, so it is read as iff( ); everything else stays as written."""
    out, i, q = [], 0, None
    s = str(src)
    while i < len(s):                                # leave text inside quotes alone
        c = s[i]
        if q:
            out.append(c)
            if c == "\\" and i + 1 < len(s):
                out.append(s[i + 1])
                i += 1
            elif c == q:
                q = None
        elif c in "'\"":
            q = c
            out.append(c)
        else:
            m = _IF_CALL.match(s, i)
            if m and (i == 0 or not (s[i - 1].isalnum() or s[i - 1] in "_.")):
                out.append("iff(")
                i = m.end()
                continue
            out.append(c)
        i += 1
    return "".join(out)


def parse(src: str) -> ast.AST:
    import warnings
    try:
        with warnings.catch_warnings():              # a pattern like "/\d+/" is her text, not a Python warning
            warnings.simplefilter("ignore")
            return ast.parse(_prep(str(src).strip()), mode="eval").body
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
        if k in KEYWORDS:                            # v0.999.254: Make's keywords (now, uuid, newline ...)
            return KEYWORDS[k]()
        if k in FUNCS:
            raise ExprError(f"{k} is a function - write {k}( )")
        raise ExprError(f"Unknown name '{k}' - start with vars, steps, item, env or run")
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
        if isinstance(n, ast.Name) and n.id not in _ROOTS and n.id.lower() not in _NAMES and n.id not in FUNCS \
                and n.id not in KEYWORDS:
            return f"Unknown name '{n.id}' - start with vars, steps, item, env or run"
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
                "base64_encode", "base64_decode", "url_encode", "url_decode",
                # v0.999.254 MAKE PARITY: Text parser, XML, table aggregator, Markdown
                "regex_match", "regex_replace", "data_to_xml", "rows_to_table", "markdown_to_html", "html_to_markdown")
FILE_ACTIONS = ("make_csv", "make_xlsx", "make_pdf", "read", "zip", "unzip")   # v0.999.254: Make's Archive
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
    if op == "text" and act in ("regex_match", "regex_replace") and not str(step.get("pattern") or "").strip():
        raise ToolError(f"Step '{sid}': give the pattern to look for")
    if op == "file" and act == "zip" and step.get("items") in (None, "", []):
        raise ToolError(f"Step '{sid}': give the files to zip (their file ids)")
    if op == "file" and act == "unzip" and not str(step.get("file_id") or "").strip():
        raise ToolError(f"Step '{sid}': give the ZIP file to open (its file id)")
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
    if act in ("zip", "unzip"):                       # v0.999.254 Make's Archive: create / extract a ZIP
        import zipfile
        from ..mailbox import service as ms
        if act == "zip":
            ids = R(step.get("items"))
            ids = ids if isinstance(ids, list) else [x.strip() for x in str(ids or "").split(",") if x.strip()]
            if not ids:
                raise ExprError("Give the files to put in the ZIP (their file ids)")
            buf = io.BytesIO()
            total = 0
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                used: set[str] = set()
                for x in ids[:200]:
                    fid = x.get("file_id") if isinstance(x, dict) else x
                    try:
                        f = ms._file_row(tenant, str(fid))
                        data = open(f.stored_path, "rb").read()
                    except Exception as e:   # noqa: BLE001
                        raise ExprError(f"The file {fid} is not there any more ({str(e)[:60]})")
                    total += len(data)
                    if total > 25 * 1024 * 1024:
                        raise ExprError("The files come to more than 25 MB")
                    nm, k = f.name or "file", 1
                    while nm in used:
                        k += 1
                        nm = re.sub(r"(\.[^.]*)?$", lambda m: f" ({k}){m.group(1) or ''}", f.name or "file", count=1)
                    used.add(nm)
                    z.writestr(nm, data)
            return _store(tenant, (name or "files") + ("" if (name or "").lower().endswith(".zip") else ".zip"), buf.getvalue())
        fid = str(R(step.get("file_id")) or "").strip()
        if not fid:
            raise ExprError("Give the ZIP file to open (its file id)")
        try:
            f = ms._file_row(tenant, fid)
            zf = zipfile.ZipFile(f.stored_path)
        except zipfile.BadZipFile:
            raise ExprError("That file is not a ZIP")
        except Exception as e:   # noqa: BLE001
            raise ExprError(str(e)[:200])
        out, total = [], 0
        with zf:
            for info in zf.infolist()[:200]:
                if info.is_dir():
                    continue
                total += info.file_size
                if total > 50 * 1024 * 1024 or (info.compress_size and info.file_size / max(info.compress_size, 1) > 200):
                    raise ExprError("The ZIP opens to too much data (over 50 MB, or packed suspiciously tight)")
                base_nm = info.filename.replace("\\", "/").rsplit("/", 1)[-1] or "file"
                out.append(_store(tenant, base_nm, zf.read(info)))
        return out
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


def _flag(v: Any) -> bool:
    return v is True or str(v).strip().lower() in ("true", "yes", "1", "on")


def _xml(tag: str, v: Any, depth: int = 0) -> str:
    from xml.sax.saxutils import escape, quoteattr
    t = re.sub(r"[^A-Za-z0-9_.-]", "_", str(tag)) or "item"
    if t[0].isdigit() or t[0] in "-.":
        t = "_" + t
    if depth > 30:
        raise ExprError("The data is nested too deep for XML")
    if isinstance(v, list):
        return "".join(_xml(t, x, depth + 1) for x in v)
    if isinstance(v, dict):
        attrs = "".join(f" {re.sub(r'[^A-Za-z0-9_.-]', '_', k[1:])}={quoteattr(str(x))}" for k, x in v.items() if str(k).startswith("@"))
        inner = escape(str(v.get("#text"))) if "#text" in v else ""
        inner += "".join(_xml(k, x, depth + 1) for k, x in v.items() if not str(k).startswith("@") and k != "#text")
        return f"<{t}{attrs}>{inner}</{t}>"
    return f"<{t}>{escape('' if v is None else (str(v).lower() if isinstance(v, bool) else str(v)))}</{t}>"


def _md_html(src: str) -> str:
    """Markdown to HTML (Make's Markdown app): headings, bold, italic, code, links, lists, quotes, paragraphs."""
    import html as _h
    out, para, lst = [], [], None

    def inline(t: str) -> str:
        t = _h.escape(t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<em>\1</em>", t)
        t = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", t)
        t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|mailto:[^)\s]+|/[^)\s]*)\)", r'<a href="\2">\1</a>', t)
        return t

    def flush():
        nonlocal para, lst
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            lst = None
    code = None
    for line in src.splitlines():
        if line.strip().startswith("```"):
            if code is None:
                flush()
                code = []
            else:
                out.append("<pre><code>" + _h.escape("\n".join(code)) + "</code></pre>")
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        ul = re.match(r"^\s*[-*+]\s+(.*)$", line)
        ol = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if m:
            flush()
            out.append(f"<h{len(m.group(1))}>{inline(m.group(2).strip())}</h{len(m.group(1))}>")
        elif ul or ol:
            if para:
                out.append("<p>" + inline(" ".join(para)) + "</p>")
                para = []
            tag = "ul" if ul else "ol"
            if not lst or lst[0] != tag:
                flush()
                lst = (tag, [])
            lst[1].append((ul or ol).group(1))
        elif line.startswith(">"):
            flush()
            out.append("<blockquote>" + inline(line.lstrip("> ")) + "</blockquote>")
        elif not line.strip():
            flush()
        else:
            if lst:
                flush()
            para.append(line.strip())
    if code is not None:
        out.append("<pre><code>" + _h.escape("\n".join(code)) + "</code></pre>")
    flush()
    return "\n".join(out)


def _html_md(src: str) -> str:
    try:
        from markdownify import markdownify
        return re.sub(r"\n{3,}", "\n\n", markdownify(src, heading_style="ATX")).strip()
    except ImportError:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(src, "lxml")
        for tag, mark in (("strong", "**"), ("b", "**"), ("em", "*"), ("i", "*")):
            for el in soup.find_all(tag):
                el.replace_with(f"{mark}{el.get_text()}{mark}")
        for a in soup.find_all("a"):
            a.replace_with(f"[{a.get_text()}]({a.get('href', '')})")
        for n in range(1, 7):
            for h in soup.find_all(f"h{n}"):
                h.replace_with(f"\n{'#' * n} {h.get_text()}\n")
        for li in soup.find_all("li"):
            li.replace_with(f"\n- {li.get_text()}")
        return re.sub(r"\n{3,}", "\n\n", soup.get_text()).strip()


def _text(step: dict, R) -> Any:
    act = step.get("action")
    v = R(step.get("value"))
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else ("" if v is None else str(v))
    _cap_text(s)
    if act in ("regex_match", "regex_replace"):     # v0.999.254 Make's Text parser: Match pattern / Replace
        pat = str(R(step.get("pattern")) or "")
        if not pat:
            raise ExprError("Give the pattern to look for")
        if len(pat) > 500:
            raise ExprError("The pattern is too long")
        fl = (0 if _flag(step.get("case_sensitive", True)) else re.I) | (re.M if _flag(step.get("multiline")) else 0) | \
            (re.S if _flag(step.get("singleline")) else 0)
        try:
            rx = re.compile(pat, fl)
        except re.error as e:
            raise ExprError(f"The pattern is not valid ({e})")
        glob = _flag(step.get("global", True))
        if act == "regex_replace":
            rep_ = str(R(step.get("replace")) or "")
            py = re.sub(r"\$(\d+)", r"\\g<\1>", rep_.replace("\\", "\\\\")).replace("$&", r"\g<0>")
            return _cap_text(rx.sub(py, s, count=0 if glob else 1))
        found = []
        for m in (rx.finditer(s) if glob else [x for x in [rx.search(s)] if x]):
            b: dict[str, Any] = {"$0": m.group(0), "$index": m.start()}
            for i, g in enumerate(m.groups(), start=1):
                b[f"${i}"] = g
            b.update({k: x for k, x in m.groupdict().items()})
            found.append(b)
            if len(found) >= LIST_MAX:
                break
        if not found and not _flag(step.get("continue_if_none", True)):
            raise ExprError("The pattern was not found")
        return found
    if act == "data_to_xml":                          # Make's XML > Create XML (and aggregate to XML)
        root = str(R(step.get("root")) or "root")
        return '<?xml version="1.0" encoding="UTF-8"?>' + _xml(root, v)
    if act == "rows_to_table":                        # Make's Table aggregator
        cols, rows = _rows(_list(v, "The rows"))
        csep = str(R(step.get("column_sep")) if step.get("column_sep") not in (None, "") else "\t").replace("\\t", "\t")
        rsep = str(R(step.get("row_sep")) if step.get("row_sep") not in (None, "") else "\n").replace("\\n", "\n")
        lines = ([csep.join(cols)] if _flag(step.get("header", True)) else []) + \
            [csep.join("" if c is None else str(c) for c in r) for r in rows]
        return _cap_text(rsep.join(lines))
    if act == "markdown_to_html":
        return _md_html(s)
    if act == "html_to_markdown":
        return _html_md(s)
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
