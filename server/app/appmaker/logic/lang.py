"""v0.382 DIMAAG (App Phase 43-46): the app's own small language - formulas, checks and locked custom functions.

Two layers, ONE interpreter written here (never Python eval / exec, never an import, never a file or the network):

  * an EXPRESSION - formulas, validations, trigger conditions:  qty * rate,  sum(lines.amount),
    if(total > 5000, "High", "Normal"),  days_between(due, today()) > 0,  customer.city == "Akola";
  * a FUNCTION BODY - custom logic Opus writes for her when a formula is not enough:
        let d = 0
        if tier == "gold" { d = total * 0.1 } else if total > 2000 { d = 100 }
        for l in lines { if l.qty > 10 { d = d + 5 } }
        return round(d, 2)

Values are only JSON shapes (number / text / true-false / null / list / map) plus a lazy row (a ref's parent row, loaded
on first use). `.name` on a map / row reads that key, on a list reads it from every item (lines.amount = the amounts).
There is no way to reach a Python object: attribute access is a dict lookup, calls are only to the fixed BUILTINS below
or to her own functions. Every run has a budget (steps, list / text size, call depth, wall time) - a runaway loop stops
with a plain error, it never hangs the server."""
from __future__ import annotations

import math
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

IST = timezone(timedelta(hours=5, minutes=30))
MAX_STEPS = 50_000
MAX_LIST = 2_000
MAX_TEXT = 20_000
MAX_DEPTH = 8
MAX_SECONDS = 0.5
MAX_NUM = 1e15
MAX_SOURCE = 6_000


class LogicError(Exception):
    """A formula / function that cannot run (bad words, a wrong type, out of budget)."""


class Fail(Exception):
    """fail("...") inside her logic: a rule said no - the message goes to the app user as is."""


# ---------------------------------------------------------------- tokens
KEYWORDS = {"and", "or", "not", "in", "if", "else", "for", "let", "return", "true", "false", "null", "break", "continue"}
TOKEN = re.compile(r"""
    (?P<ws>[ \t\r]+|\#[^\n]*)
  | (?P<nl>\n)
  | (?P<num>\d+(?:\.\d+)?)
  | (?P<str>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>==|!=|<=|>=|&&|\|\||[-+*/%<>()\[\]{},.:;=!])
""", re.X)
ESC = {"n": "\n", "t": "\t", '"': '"', "'": "'", "\\": "\\"}


def tokens(src: str) -> list[tuple[str, Any, int]]:
    if len(src) > MAX_SOURCE:
        raise LogicError(f"Logic bahut lambi hai ({len(src)} akshar, seema {MAX_SOURCE}).")
    out, i, line = [], 0, 1
    while i < len(src):
        m = TOKEN.match(src, i)
        if not m:
            raise LogicError(f"Line {line}: '{src[i]}' samajh nahi aaya.")
        k = m.lastgroup
        v = m.group(k)
        if k == "nl":
            out.append(("nl", "\n", line))
            line += 1
        elif k == "num":
            out.append(("num", float(v) if "." in v else int(v), line))
        elif k == "str":
            body = v[1:-1]
            out.append(("str", re.sub(r"\\(.)", lambda x: ESC.get(x.group(1), x.group(1)), body), line))
        elif k == "name":
            out.append(("kw" if v in KEYWORDS else "name", v, line))
        elif k == "op":
            out.append(("op", {"&&": "and", "||": "or"}.get(v, v), line))
        i = m.end()
    out.append(("eof", None, line))
    return out


# ---------------------------------------------------------------- parser -> tuples (op, ...)
class Parser:
    def __init__(self, src: str):
        self.t = tokens(src)
        self.i = 0

    def peek(self, skip_nl: bool = True):
        j = self.i
        while skip_nl and self.t[j][0] == "nl":
            j += 1
        return self.t[j]

    def next(self, skip_nl: bool = True):
        while skip_nl and self.t[self.i][0] == "nl":
            self.i += 1
        tok = self.t[self.i]
        self.i += 1
        return tok

    def at(self, kind: str, val: Any = None, skip_nl: bool = True) -> bool:
        k, v, _ = self.peek(skip_nl)
        return k == kind and (val is None or v == val)

    def want(self, kind: str, val: Any = None):
        k, v, ln = self.next()
        if k != kind or (val is not None and v != val):
            got = "end" if k == "eof" else repr(v)
            raise LogicError(f"Line {ln}: {val or kind} chahiye tha, {got} mila.")
        return v

    # expressions (newlines inside are allowed: an expression never ends at a newline inside brackets)
    def expr(self):
        return self.or_()

    def or_(self):
        a = self.and_()
        while self.at("kw", "or"):
            self.next()
            a = ("or", a, self.and_())
        return a

    def and_(self):
        a = self.not_()
        while self.at("kw", "and"):
            self.next()
            a = ("and", a, self.not_())
        return a

    def not_(self):
        if self.at("kw", "not") or self.at("op", "!"):
            self.next()
            return ("not", self.not_())
        return self.cmp()

    def cmp(self):
        a = self.add()
        while True:
            if self.at("op") and self.peek()[1] in ("==", "!=", "<", "<=", ">", ">="):
                op = self.next()[1]
                a = ("cmp", op, a, self.add())
            elif self.at("kw", "in"):
                self.next()
                a = ("in", a, self.add())
            elif self.at("kw", "not") and self.t[self._ahead()][0:2] == ("kw", "in"):
                self.next()
                self.next()
                a = ("not", ("in", a, self.add()))
            else:
                return a

    def _ahead(self) -> int:
        j = self.i
        while self.t[j][0] == "nl":
            j += 1
        j += 1
        while self.t[j][0] == "nl":
            j += 1
        return j

    def add(self):
        a = self.mul()
        while self.at("op") and self.peek()[1] in ("+", "-"):
            op = self.next()[1]
            a = ("bin", op, a, self.mul())
        return a

    def mul(self):
        a = self.unary()
        while self.at("op") and self.peek()[1] in ("*", "/", "%"):
            op = self.next()[1]
            a = ("bin", op, a, self.unary())
        return a

    def unary(self):
        if self.at("op", "-"):
            self.next()
            return ("neg", self.unary())
        if self.at("op", "+"):
            self.next()
            return self.unary()
        return self.post()

    def post(self):
        a = self.primary()
        while True:
            if self.at("op", ".", skip_nl=False):
                self.next()
                k, v, ln = self.next()
                if k not in ("name", "kw"):
                    raise LogicError(f"Line {ln}: '.' ke baad naam chahiye.")
                a = ("get", a, ("lit", v))
            elif self.at("op", "[", skip_nl=False):
                self.next()
                idx = self.expr()
                self.want("op", "]")
                a = ("get", a, idx)
            elif self.at("op", "(", skip_nl=False) and a[0] == "name":
                self.next()
                args = []
                if not self.at("op", ")"):
                    args.append(self.expr())
                    while self.at("op", ","):
                        self.next()
                        if self.at("op", ")"):
                            break
                        args.append(self.expr())
                self.want("op", ")")
                a = ("call", a[1], args)
            else:
                return a

    def primary(self):
        k, v, ln = self.next()
        if k == "num" or k == "str":
            return ("lit", v)
        if k == "kw" and v in ("true", "false", "null"):
            return ("lit", {"true": True, "false": False, "null": None}[v])
        if k == "kw" and v == "if":                # if(c, a, b) written with the keyword
            if self.at("op", "(", skip_nl=False):
                self.next()
                args = [self.expr()]
                while self.at("op", ","):
                    self.next()
                    args.append(self.expr())
                self.want("op", ")")
                return ("call", "if", args)
        if k == "name":
            return ("name", v)
        if k == "op" and v == "(":
            e = self.expr()
            self.want("op", ")")
            return e
        if k == "op" and v == "[":
            items = []
            if not self.at("op", "]"):
                items.append(self.expr())
                while self.at("op", ","):
                    self.next()
                    if self.at("op", "]"):
                        break
                    items.append(self.expr())
            self.want("op", "]")
            return ("list", items)
        if k == "op" and v == "{":
            pairs = []
            if not self.at("op", "}"):
                while True:
                    kk, kv, kl = self.next()
                    if kk not in ("name", "str", "kw"):
                        raise LogicError(f"Line {kl}: map ki chaabi naam / text honi chahiye.")
                    self.want("op", ":")
                    pairs.append((str(kv), self.expr()))
                    if self.at("op", ","):
                        self.next()
                        if self.at("op", "}"):
                            break
                        continue
                    break
            self.want("op", "}")
            return ("map", pairs)
        got = "end" if k == "eof" else repr(v)
        raise LogicError(f"Line {ln}: yahan {got} nahi aa sakta.")

    # statements (function bodies)
    def block(self, top: bool = False):
        body = []
        if not top:
            self.want("op", "{")
        while True:
            while self.at("nl", skip_nl=False) or self.at("op", ";", skip_nl=False):
                self.next(skip_nl=False)
            if top and self.at("eof"):
                break
            if not top and self.at("op", "}"):
                self.next()
                break
            if self.at("eof"):
                raise LogicError("'}' band karna reh gaya.")
            body.append(self.stmt())
        return ("block", body)

    def stmt(self):
        k, v, ln = self.peek()
        if k == "kw" and v == "let":
            self.next()
            name = self.want("name")
            self.want("op", "=")
            return ("let", name, self.expr(), ln)
        if k == "kw" and v == "if" and not self._if_call():
            self.next()
            cond = self.expr()
            then = self.block()
            other = None
            if self.at("kw", "else"):
                self.next()
                other = ("block", [self.stmt()]) if self.at("kw", "if") else self.block()
            return ("if", cond, then, other, ln)
        if k == "kw" and v == "for":
            self.next()
            name = self.want("name")
            self.want("kw", "in")
            seq = self.expr()
            return ("for", name, seq, self.block(), ln)
        if k == "kw" and v == "return":
            self.next()
            if self.at("nl", skip_nl=False) or self.at("op", "}") or self.at("eof") or self.at("op", ";", skip_nl=False):
                return ("return", ("lit", None), ln)
            return ("return", self.expr(), ln)
        if k == "kw" and v in ("break", "continue"):
            self.next()
            return (v, ln)
        if k == "name" and self.t[self._ahead()][0:2] == ("op", "="):
            self.next()
            self.next()
            return ("set", v, self.expr(), ln)
        return ("expr", self.expr(), ln)

    def _if_call(self) -> bool:
        """`if(a, b, c)` as an expression statement vs an if-block."""
        j = self._ahead()
        if self.t[j][0:2] != ("op", "("):
            return False
        depth, k = 0, j
        while self.t[k][0] != "eof":
            tk = self.t[k]
            if tk[0] == "op" and tk[1] in ("(", "[", "{"):
                depth += 1
            elif tk[0] == "op" and tk[1] in (")", "]", "}"):
                depth -= 1
                if depth == 0:              # a call only when the statement ends right after it
                    nxt = self.t[k + 1]
                    return nxt[0] in ("nl", "eof") or nxt[0:2] in (("op", ";"), ("op", "}"))
            k += 1
        return False


def parse_expr(src: str):
    p = Parser(str(src or ""))
    if p.at("eof"):
        raise LogicError("Formula khaali hai.")
    e = p.expr()
    if not p.at("eof"):
        _k, v, ln = p.peek()
        raise LogicError(f"Line {ln}: formula ke baad {v!r} bacha hai.")
    return e


def parse_body(src: str):
    return Parser(str(src or "")).block(top=True)


# ---------------------------------------------------------------- names used (the checker's static pass)
def names(node, out: set[str] | None = None, bound: set[str] | None = None) -> set[str]:
    """Free names a piece of logic reads (fields, relations, `me`, ...) - locals made by let / for / params excluded."""
    out = set() if out is None else out
    bound = set() if bound is None else bound
    if not isinstance(node, tuple):
        return out
    op = node[0]
    if op == "name":
        if node[1] not in bound:
            out.add(node[1])
    elif op == "lit":
        pass
    elif op == "call":
        for a in node[2]:
            names(a, out, bound)
    elif op == "map":
        for _k, v in node[1]:
            names(v, out, bound)
    elif op == "list":
        for v in node[1]:
            names(v, out, bound)
    elif op == "block":
        local = set(bound)
        for s in node[1]:
            names(s, out, local)
    elif op == "let":
        names(node[2], out, bound)
        bound.add(node[1])
    elif op == "set":
        names(node[2], out, bound)
        if node[1] not in bound:
            out.add(node[1])
    elif op == "for":
        names(node[2], out, bound)
        names(node[3], out, bound | {node[1]})
    elif op == "if":
        names(node[1], out, bound)
        names(node[2], out, set(bound))
        if node[3]:
            names(node[3], out, set(bound))
    elif op in ("return", "expr"):
        names(node[1], out, bound)
    elif op in ("break", "continue"):
        pass
    else:
        for x in node[1:]:
            if isinstance(x, tuple):
                names(x, out, bound)
    return out


def calls(node, out: set[str] | None = None) -> set[str]:
    out = set() if out is None else out
    if isinstance(node, tuple):
        if node and node[0] == "call":
            out.add(node[1])
        for x in node[1:]:
            if isinstance(x, tuple):
                calls(x, out)
            elif isinstance(x, list):
                for y in x:
                    if isinstance(y, tuple):
                        calls(y, out)
    elif isinstance(node, list):
        for y in node:
            calls(y, out)
    return out


def field_paths(node, out: set[tuple[str, str]] | None = None) -> set[tuple[str, str]]:
    """name.key pairs (customer.city, lines.amount) - the checker confirms each key exists on that relation's list."""
    out = set() if out is None else out
    if isinstance(node, tuple):
        if node and node[0] == "get" and isinstance(node[1], tuple) and node[1][0] == "name" and node[2][0] == "lit":
            out.add((node[1][1], str(node[2][1])))
        for x in node[1:]:
            if isinstance(x, (tuple, list)):
                field_paths(x, out)
    elif isinstance(node, list):
        for y in node:
            field_paths(y, out)
    return out


# ---------------------------------------------------------------- runtime values
class LazyRow:
    """A ref's parent row: loaded on the first `.field` (never before), shown as its id everywhere else."""
    __slots__ = ("id", "_load", "_data")

    def __init__(self, row_id: str, load: Callable[[str], dict[str, Any] | None]):
        self.id, self._load, self._data = str(row_id or ""), load, None

    def data(self) -> dict[str, Any]:
        if self._data is None:
            self._data = (self._load(self.id) if self.id else None) or {}
        return self._data

    def get(self, key: str) -> Any:
        if key == "id":
            return self.id
        return self.data().get(key)

    def __eq__(self, other):                       # compares like its id
        return plain(self) == plain(other)

    def __hash__(self):
        return hash(self.id)


def plain(v: Any) -> Any:
    """A runtime value -> JSON (a lazy row = its id)."""
    if isinstance(v, LazyRow):
        return v.id
    if isinstance(v, list):
        return [plain(x) for x in v]
    if isinstance(v, dict):
        return {str(k): plain(x) for k, x in v.items()}
    if isinstance(v, float) and v.is_integer() and abs(v) < MAX_NUM:
        return int(v)
    return v


def num(v: Any, what: str = "number") -> float:
    v = plain(v)
    if v is None or v == "":
        return 0
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return v
    try:
        return float(str(v).replace(",", "").replace("₹", "").strip())
    except ValueError:
        raise LogicError(f"'{str(v)[:30]}' {what} nahi hai.")


def text(v: Any) -> str:
    v = plain(v)
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else f"{v:.10g}"
    if isinstance(v, (list, dict)):
        import json
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def truthy(v: Any) -> bool:
    v = plain(v)
    if isinstance(v, str):
        return v.strip().lower() not in ("", "false", "no", "0", "nahi")
    return bool(v)


def _date(v: Any) -> date | None:
    v = plain(v)
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    try:
        if len(s) >= 19:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return (d.astimezone(IST) if d.tzinfo else d).date()
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        raise LogicError(f"'{s[:30]}' tareekh nahi hai (YYYY-MM-DD).")


def _dt(v: Any) -> datetime | None:
    v = plain(v)
    if v in (None, ""):
        return None
    s = str(v).strip()
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00")) if len(s) > 10 else datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        raise LogicError(f"'{s[:30]}' samay nahi hai.")
    return d if d.tzinfo else d.replace(tzinfo=IST)


def _cmp(op: str, a: Any, b: Any) -> bool:
    a, b = plain(a), plain(b)
    if op in ("==", "!="):
        if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, str):
            try:
                b = float(b)
            except ValueError:
                pass
        elif isinstance(b, (int, float)) and not isinstance(b, bool) and isinstance(a, str):
            try:
                a = float(a)
            except ValueError:
                pass
        eq = (a == b) or (a in (None, "") and b in (None, ""))
        return eq if op == "==" else not eq
    if isinstance(a, str) and isinstance(b, str):
        try:
            a, b = float(a), float(b)
        except ValueError:
            pass
    if isinstance(a, str) or isinstance(b, str):
        a, b = text(a), text(b)
    else:
        a, b = num(a), num(b)
    return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]


def _check_num(v: Any) -> Any:
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            raise LogicError("Hisaab galat (0 se bhaag ya bahut bada number).")
    if isinstance(v, (int, float)) and abs(v) > MAX_NUM:
        raise LogicError("Number bahut bada ho gaya.")
    return v


# ---------------------------------------------------------------- builtins (pure; no I/O)
def _list(v: Any) -> list:
    v = v if not isinstance(v, LazyRow) else [v]
    if v is None or v == "":
        return []
    if not isinstance(v, list):
        return [v]
    return v


def _vals(args: list) -> list:
    if len(args) == 1 and isinstance(args[0], list):
        return [x for x in args[0] if plain(x) not in (None, "")]
    return [x for x in args if plain(x) not in (None, "")]


def _round(x, n=0):
    n = int(num(n))
    q = round(num(x) + (1e-9 if num(x) >= 0 else -1e-9), max(0, min(n, 6)))
    return int(q) if n <= 0 else q


def _where(items, field, op="==", value=None, *more):
    if value is None and op not in ("==", "!=", "<", "<=", ">", ">=", "in", "contains"):
        op, value = "==", op
    out = []
    for it in _list(items):
        got = it.get(text(field)) if isinstance(it, (dict, LazyRow)) else None
        if op == "in":
            ok = plain(got) in plain(_list(value))
        elif op == "contains":
            ok = text(value).lower() in text(got).lower()
        else:
            ok = _cmp(op, got, value)
        if ok:
            out.append(it)
    return out


def _sort(items, field="", desc=False):
    lst = list(_list(items))
    key = (lambda it: plain(it.get(text(field)) if isinstance(it, (dict, LazyRow)) else it)) if field else plain

    def k(it):
        v = key(it)
        return (0, v) if isinstance(v, (int, float)) and not isinstance(v, bool) else (1, text(v))
    return sorted(lst, key=k, reverse=truthy(desc))


def _days_between(a, b):
    da, db = _date(a), _date(b)
    if da is None or db is None:
        return None
    return (db - da).days


def _add_days(d, n):
    dd = _date(d)
    return (dd + timedelta(days=int(num(n)))).isoformat() if dd else None


def _add_months(d, n):
    dd = _date(d)
    if not dd:
        return None
    m = dd.month - 1 + int(num(n))
    y, m = dd.year + m // 12, m % 12 + 1
    import calendar
    return date(y, m, min(dd.day, calendar.monthrange(y, m)[1])).isoformat()


def _hours_since(t):
    d = _dt(t)
    if d is None:
        return None
    return round((datetime.now(timezone.utc) - d).total_seconds() / 3600, 2)


def _age(d):
    dd = _date(d)
    if not dd:
        return None
    t = datetime.now(IST).date()
    return t.year - dd.year - ((t.month, t.day) < (dd.month, dd.day))


def _fmt_money(x):
    n = num(x)
    neg, n = n < 0, abs(round(n, 2))
    whole, frac = int(n), round((n - int(n)) * 100)
    s = str(whole)
    if len(s) > 3:                                 # Indian grouping 12,34,567
        head, tail = s[:-3], s[-3:]
        head = ",".join(re.findall(r"\d{1,2}(?=(?:\d{2})*$)", head))
        s = head + "," + tail
    return ("-" if neg else "") + "₹" + s + (f".{frac:02d}" if frac else "")


def _pad(x, n, ch="0"):
    return text(x).rjust(max(0, min(int(num(n)), 40)), (text(ch) or "0")[0])


def _split(s, sep=","):
    return [p.strip() for p in text(s).split(text(sep) or ",")][:MAX_LIST]


def _get(m, k, default=None):
    if isinstance(m, (dict, LazyRow)):
        v = m.get(text(k))
        return default if v is None else v
    if isinstance(m, list):
        i = int(num(k))
        return m[i] if -len(m) <= i < len(m) else default
    return default


def _unique(items, field=""):
    seen, out = set(), []
    for it in _list(items):
        v = plain(it.get(text(field)) if field and isinstance(it, (dict, LazyRow)) else it)
        key = text(v)
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def _count(items, field=None, value=None):
    lst = _list(items)
    if field is not None:
        lst = _where(lst, field, "==", value) if value is not None else [x for x in lst if truthy(_get(x, field))]
    return len(lst)


def _matches(s, pattern):
    pat = text(pattern)
    if len(pat) > 120 or re.search(r"\(\?|\\\d|(\+|\*|\})\s*(\+|\*|\{)", pat):   # no backrefs / nested quantifiers
        raise LogicError("Yeh pattern bahut ulajh hai.")
    try:
        return re.fullmatch(pat, text(s)[:500]) is not None
    except re.error:
        raise LogicError("Pattern galat hai.")


def _first(items, field=None, value=None):
    lst = _where(items, field, "==", value) if field is not None and value is not None else _list(items)
    return lst[0] if lst else None


BUILTINS: dict[str, Callable[..., Any]] = {
    # numbers
    "round": _round, "abs": lambda x: abs(num(x)), "floor": lambda x: math.floor(num(x)), "ceil": lambda x: math.ceil(num(x)),
    "number": lambda x, d=0: (num(x) if plain(x) not in (None, "") else num(d)),
    "min": lambda *a: min((num(x) for x in _vals(list(a))), default=0),
    "max": lambda *a: max((num(x) for x in _vals(list(a))), default=0),
    "sum": lambda *a: sum(num(x) for x in _vals(list(a))),
    "avg": lambda *a: (sum(num(x) for x in _vals(list(a))) / len(_vals(list(a)))) if _vals(list(a)) else 0,
    "percent": lambda part, whole: (num(part) * 100 / num(whole)) if num(whole) else 0,
    "money": _fmt_money,
    # text
    "text": text, "upper": lambda s: text(s).upper(), "lower": lambda s: text(s).lower(), "trim": lambda s: text(s).strip(),
    "len": lambda x: len(x) if isinstance(x, (list, dict)) else len(text(x)),
    "concat": lambda *a: "".join(text(x) for x in a), "contains": lambda s, p: text(p).lower() in text(s).lower(),
    "starts": lambda s, p: text(s).lower().startswith(text(p).lower()), "ends": lambda s, p: text(s).lower().endswith(text(p).lower()),
    "replace": lambda s, a, b: text(s).replace(text(a), text(b)), "split": _split,
    "join": lambda items, sep=", ": text(sep).join(text(x) for x in _list(items)), "pad": _pad,
    "left": lambda s, n: text(s)[:max(0, int(num(n)))], "right": lambda s, n: text(s)[-max(0, int(num(n))):] if int(num(n)) else "",
    "matches": _matches,
    # logic
    "coalesce": lambda *a: next((x for x in a if plain(x) not in (None, "")), None),
    "empty": lambda x: plain(x) in (None, "", [], {}), "bool": truthy,
    # dates (IST)
    "today": lambda: datetime.now(IST).date().isoformat(), "now": lambda: datetime.now(IST).isoformat(timespec="seconds"),
    "days_between": _days_between, "add_days": _add_days, "add_months": _add_months, "hours_since": _hours_since,
    "year": lambda d: (_date(d).year if _date(d) else None), "month": lambda d: (_date(d).month if _date(d) else None),
    "day": lambda d: (_date(d).day if _date(d) else None),
    "weekday": lambda d: (_date(d).strftime("%a") if _date(d) else None), "age": _age, "date": lambda d: (_date(d).isoformat() if _date(d) else None),
    # lists
    "count": _count, "where": _where, "sort": _sort, "first": _first, "last": lambda items: (_list(items)[-1] if _list(items) else None),
    "unique": _unique, "get": _get, "keys": lambda m: list(m.keys()) if isinstance(m, dict) else [],
    "range": lambda a, b=None: list(range(int(num(a)))) if b is None else list(range(int(num(a)), int(num(b)))),
    "append": lambda items, x: _list(items) + [x], "any": lambda items: any(truthy(x) for x in _list(items)),
    "all": lambda items: all(truthy(x) for x in _list(items)),
}
LAZY = {"if", "fail"}                       # args evaluated by the interpreter itself
RESERVED = set(BUILTINS) | LAZY | KEYWORDS | {"me", "row", "old", "id", "created"}


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _Return(Exception):
    def __init__(self, v):
        self.v = v


# ---------------------------------------------------------------- interpreter
class Run:
    """One evaluation: a budget + the names it may read + her own functions (each a parsed body + params)."""

    def __init__(self, env: dict[str, Any] | None = None, functions: dict[str, tuple[list[str], Any]] | None = None,
                 steps: int = MAX_STEPS, seconds: float = MAX_SECONDS):
        self.env = env or {}
        self.functions = functions or {}
        self.steps, self.deadline, self.depth = steps, time.monotonic() + seconds, 0

    def tick(self):
        self.steps -= 1
        if self.steps <= 0:
            raise LogicError("Logic ne bahut kadam liye (loop band kiya).")
        if self.steps % 256 == 0 and time.monotonic() > self.deadline:
            raise LogicError("Logic ka samay khatam (loop band kiya).")

    def value(self, node, scope: dict[str, Any]):
        self.tick()
        op = node[0]
        if op == "lit":
            return node[1]
        if op == "name":
            k = node[1]
            if k in scope:
                return scope[k]
            if k in self.env:
                v = self.env[k]
                return v() if callable(v) and not isinstance(v, LazyRow) else v
            raise LogicError(f"'{k}' naam ka field / cheez nahi mili.")
        if op == "get":
            base = self.value(node[1], scope)
            key = self.value(node[2], scope)
            return self._get(base, key)
        if op == "bin":
            a, b = self.value(node[2], scope), self.value(node[3], scope)
            o = node[1]
            if o == "+":
                pa, pb = plain(a), plain(b)
                if isinstance(pa, list) or isinstance(pb, list):
                    out = _list(a) + _list(b)
                    if len(out) > MAX_LIST:
                        raise LogicError("List bahut lambi ho gayi.")
                    return out
                if isinstance(pa, str) and not _numeric(pa) or isinstance(pb, str) and not _numeric(pb):
                    s = text(a) + text(b)
                    if len(s) > MAX_TEXT:
                        raise LogicError("Text bahut lamba ho gaya.")
                    return s
                return _check_num(num(a) + num(b))
            if o == "-":
                return _check_num(num(a) - num(b))
            if o == "*":
                return _check_num(num(a) * num(b))
            if o == "/":
                d = num(b)
                if d == 0:
                    raise LogicError("0 se bhaag nahi ho sakta.")
                return _check_num(num(a) / d)
            if o == "%":
                d = num(b)
                if d == 0:
                    raise LogicError("0 se bhaag nahi ho sakta.")
                return _check_num(num(a) % d)
        if op == "neg":
            return -num(self.value(node[1], scope))
        if op == "not":
            return not truthy(self.value(node[1], scope))
        if op == "and":
            a = self.value(node[1], scope)
            return self.value(node[2], scope) if truthy(a) else a
        if op == "or":
            a = self.value(node[1], scope)
            return a if truthy(a) else self.value(node[2], scope)
        if op == "cmp":
            return _cmp(node[1], self.value(node[2], scope), self.value(node[3], scope))
        if op == "in":
            a, b = plain(self.value(node[1], scope)), self.value(node[2], scope)
            if isinstance(b, str):
                return text(a).lower() in b.lower()
            return a in [plain(x) for x in _list(b)]
        if op == "list":
            if len(node[1]) > MAX_LIST:
                raise LogicError("List bahut lambi hai.")
            return [self.value(x, scope) for x in node[1]]
        if op == "map":
            return {k: self.value(v, scope) for k, v in node[1]}
        if op == "call":
            return self.call(node[1], node[2], scope)
        raise LogicError("Yeh logic samajh nahi aaya.")

    def _get(self, base, key):
        if isinstance(base, list):
            if isinstance(key, (int, float)) and not isinstance(key, bool):
                i = int(key)
                return base[i] if -len(base) <= i < len(base) else None
            k = text(key)
            return [it.get(k) if isinstance(it, (dict, LazyRow)) else None for it in base]
        if isinstance(base, (dict, LazyRow)):
            return base.get(text(key))
        if base is None or base == "":
            return None
        raise LogicError(f"'{text(base)[:30]}' ke andar '{text(key)}' nahi hota.")

    def call(self, name: str, arg_nodes: list, scope: dict[str, Any]):
        if name == "if":
            if len(arg_nodes) not in (2, 3):
                raise LogicError("if(sharat, haan, nahi) - 2 ya 3 cheezein.")
            if truthy(self.value(arg_nodes[0], scope)):
                return self.value(arg_nodes[1], scope)
            return self.value(arg_nodes[2], scope) if len(arg_nodes) == 3 else None
        if name == "fail":
            msg = text(self.value(arg_nodes[0], scope)) if arg_nodes else "Yeh sahi nahi hai."
            raise Fail(msg[:300])
        args = [self.value(a, scope) for a in arg_nodes]
        if name in self.functions:
            params, body = self.functions[name]
            if len(args) > len(params):
                raise LogicError(f"{name}() mein {len(params)} cheezein jaati hain.")
            if self.depth >= MAX_DEPTH:
                raise LogicError("Functions ek doosre ko bahut gehre bula rahe hain.")
            self.depth += 1
            try:
                return self.run_body(body, {p: (args[i] if i < len(args) else None) for i, p in enumerate(params)})
            finally:
                self.depth -= 1
        fn = BUILTINS.get(name)
        if fn is None:
            raise LogicError(f"'{name}()' naam ka kaam nahi hai.")
        try:
            out = fn(*args)
        except (LogicError, Fail):
            raise
        except TypeError:
            raise LogicError(f"{name}() mein cheezein galat ginti mein hain.")
        except (ValueError, OverflowError, ArithmeticError) as e:
            raise LogicError(f"{name}(): {str(e)[:80]}")
        if isinstance(out, list) and len(out) > MAX_LIST:
            raise LogicError("List bahut lambi ho gayi.")
        if isinstance(out, str) and len(out) > MAX_TEXT:
            raise LogicError("Text bahut lamba ho gaya.")
        return _check_num(out) if isinstance(out, (int, float)) else out

    # statements
    def run_body(self, body, scope: dict[str, Any]):
        try:
            self.exec(body, scope)
        except _Return as r:
            return r.v
        except (_Break, _Continue):
            raise LogicError("break / continue sirf for ke andar.")
        return None

    def exec(self, node, scope: dict[str, Any]):
        self.tick()
        op = node[0]
        if op == "block":
            for s in node[1]:
                self.exec(s, scope)
        elif op == "let" or op == "set":
            if op == "set" and node[1] not in scope:
                raise LogicError(f"Line {node[3]}: '{node[1]}' pehle 'let {node[1]} = ...' se banaiye.")
            if node[1] in RESERVED and op == "let":
                raise LogicError(f"Line {node[3]}: '{node[1]}' naam pehle se kaam mein hai.")
            v = self.value(node[2], scope)
            if isinstance(v, str) and len(v) > MAX_TEXT:
                raise LogicError("Text bahut lamba ho gaya.")
            scope[node[1]] = v
        elif op == "if":
            if truthy(self.value(node[1], scope)):
                self.exec(node[2], scope)
            elif node[3] is not None:
                self.exec(node[3], scope)
        elif op == "for":
            seq = self.value(node[2], scope)
            items = list(seq.keys()) if isinstance(seq, dict) else _list(seq)
            if len(items) > MAX_LIST:
                raise LogicError("Itni lambi list par loop nahi chalega.")
            for it in items:
                scope[node[1]] = it
                try:
                    self.exec(node[3], scope)
                except _Break:
                    break
                except _Continue:
                    continue
        elif op == "return":
            raise _Return(self.value(node[1], scope))
        elif op == "break":
            raise _Break()
        elif op == "continue":
            raise _Continue()
        elif op == "expr":
            self.value(node[1], scope)
        else:
            raise LogicError("Yeh statement samajh nahi aaya.")


def _numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def evaluate(src_or_ast, env: dict[str, Any] | None = None, functions: dict[str, tuple[list[str], Any]] | None = None,
             steps: int = MAX_STEPS) -> Any:
    """One expression -> a JSON value."""
    ast = parse_expr(src_or_ast) if isinstance(src_or_ast, str) else src_or_ast
    return plain(Run(env, functions, steps).value(ast, {}))


def call_function(functions: dict[str, tuple[list[str], Any]], name: str, args: list[Any],
                  env: dict[str, Any] | None = None, steps: int = MAX_STEPS) -> Any:
    if name not in functions:
        raise LogicError(f"Function '{name}' nahi mila.")
    params, body = functions[name]
    run = Run(env, functions, steps)
    run.depth = 1
    return plain(run.run_body(body, {p: (args[i] if i < len(args) else None) for i, p in enumerate(params)}))
