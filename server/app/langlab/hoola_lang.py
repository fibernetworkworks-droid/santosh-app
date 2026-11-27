"""Hoola Grammar - a small parser generator in plain Python (no other files needed).

It ships three ways: inside Hoola (the Compiler Construction Engineer's engine), inside the locked sandbox that runs her
interpreter, and in the zip she downloads (her language then runs anywhere Python 3.9+ runs).

THE GRAMMAR (a .hg file):

    # a comment
    %ignore /\\s+/                 skipped between tokens (spaces, comments ...)
    %ignore /#[^\\n]*/
    %allow_keywords                (optional) a NAME-like token may also match a fixed word of the grammar
    program   : statement* ;
    statement : "let" NAME "=" expr ";"
              | "print" expr ";" ;
    ?expr     : term (("+" | "-") term)* ;     ? = left out of the tree when it has only one child
    !call     : NAME "(" args? ")" ;            ! = keep every fixed word / mark in the tree
    NAME      : /[A-Za-z_][A-Za-z_0-9]*/ ;     UPPER CASE = a token (a regex /.../ or a fixed "text")
    NUMBER    : /\\d+(\\.\\d+)?/ ;

    lower-case names are rules; "text" is a fixed word or mark; ( ) groups; | is ordered choice (the first that fits wins);
    * many, + one or more, ? optional. Fixed words and marks are left out of the tree, except inside a choice of them
    (like "+" | "-") so the tree still says which operator it was. A fixed word made of letters only matches as a whole
    word ("let" does not match the start of "letter"), and a NAME-like token never matches a fixed word of the grammar
    unless %allow_keywords is written.

THE TREE: Node(rule, children, line, col) and Tok(kind, text, line, col). sexp(tree) prints it as (rule child ...).
Errors are ParseError with line, col, what was expected and a pointer under the line.
"""
from __future__ import annotations

import random
import re
from typing import Any

try:                                   # the regex parser of the standard library (moved in 3.11)
    import re._parser as _sre          # type: ignore[import-not-found]
    import re._constants as _src       # type: ignore[import-not-found]
except Exception:                      # noqa: BLE001
    import sre_parse as _sre           # type: ignore[no-redef]
    import sre_constants as _src       # type: ignore[no-redef]

VERSION = "1.0"
MAX_STEPS = 2_000_000
MAX_SOURCE = 2_000_000


class GrammarError(Exception):
    def __init__(self, msg: str, line: int = 0):
        super().__init__(f"Line {line}: {msg}" if line else msg)
        self.msg, self.line = msg, line


class ParseError(Exception):
    def __init__(self, msg: str, line: int, col: int, expected: list[str], found: str, pointer: str):
        super().__init__(f"Line {line}, column {col}: {msg}")
        self.msg, self.line, self.col, self.expected, self.found, self.pointer = msg, line, col, expected, found, pointer

    def as_dict(self) -> dict[str, Any]:
        return {"message": str(self), "line": self.line, "col": self.col, "expected": self.expected, "found": self.found,
                "pointer": self.pointer}


class LangError(Exception):
    """Raised by HER interpreter for an error in the program it runs (a clean error, not a crash)."""
    def __init__(self, msg: str, node: Any = None):
        super().__init__(msg)
        self.line = getattr(node, "line", 0) or 0


# ---------------------------------------------------------------- the tree
class Tok:
    __slots__ = ("kind", "text", "line", "col")

    def __init__(self, kind: str, text: str, line: int, col: int):
        self.kind, self.text, self.line, self.col = kind, text, line, col

    def __repr__(self) -> str:
        return f"Tok({self.kind}, {self.text!r})"

    def __str__(self) -> str:
        return self.text

    def __eq__(self, other: object) -> bool:
        return self.text == (other.text if isinstance(other, Tok) else other)

    def __hash__(self) -> int:
        return hash(self.text)


class Node:
    __slots__ = ("rule", "children", "line", "col")

    def __init__(self, rule: str, children: list, line: int, col: int):
        self.rule, self.children, self.line, self.col = rule, children, line, col

    def __repr__(self) -> str:
        return sexp(self)

    def __iter__(self):
        return iter(self.children)

    def __len__(self) -> int:
        return len(self.children)

    def __getitem__(self, i):
        return self.children[i]

    def nodes(self, rule: str) -> list["Node"]:
        """Every child node (one level) with this rule name."""
        return [c for c in self.children if isinstance(c, Node) and c.rule == rule]

    def toks(self, kind: str = "") -> list[Tok]:
        return [c for c in self.children if isinstance(c, Tok) and (not kind or c.kind == kind)]


def _atom(t: str) -> str:
    return t if t and not re.search(r'[\s()"\\]', t) else '"' + t.replace("\\", "\\\\").replace('"', '\\"') + '"'


def sexp(t: Any) -> str:
    if isinstance(t, Tok):
        return _atom(t.text)
    if isinstance(t, Node):
        return "(" + " ".join([t.rule] + [sexp(c) for c in t.children]) + ")"
    return str(t)


def norm_sexp(s: str) -> str:
    """Compare two printed trees without caring about spaces / new lines."""
    out, i, n = [], 0, len(s or "")
    s = s or ""
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in "()":
            out.append(c)
            i += 1
        elif c == '"':
            j, buf = i + 1, []
            while j < n and s[j] != '"':
                if s[j] == "\\" and j + 1 < n:
                    j += 1
                buf.append(s[j])
                j += 1
            out.append(_atom("".join(buf)))
            i = j + 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in '()"':
                j += 1
            out.append(_atom(s[i:j]))
            i = j
    txt = ""
    for p in out:
        if txt and not txt.endswith("(") and p != ")":
            txt += " "
        txt += p
    return txt


def to_json(t: Any) -> Any:
    if isinstance(t, Tok):
        return {"tok": t.kind, "text": t.text, "line": t.line, "col": t.col}
    return {"rule": t.rule, "line": t.line, "col": t.col, "children": [to_json(c) for c in t.children]}


# ---------------------------------------------------------------- grammar expressions
class E:                    # base
    kind = ""


class Lit(E):
    kind = "lit"

    def __init__(self, s: str):
        self.s, self.word, self.keep = s, bool(re.fullmatch(r"\w+", s)), False


class Ref(E):
    kind = "ref"

    def __init__(self, name: str, line: int):
        self.name, self.line = name, line


class Seq(E):
    kind = "seq"

    def __init__(self, items: list[E]):
        self.items = items


class Alt(E):
    kind = "alt"

    def __init__(self, alts: list[E]):
        self.alts = alts


class Rep(E):
    kind = "rep"

    def __init__(self, item: E, lo: int, hi: int | None):
        self.item, self.lo, self.hi = item, lo, hi


class Rule:
    def __init__(self, name: str, expr: E, line: int, inline: bool = False, keep: bool = False):
        self.name, self.expr, self.line, self.inline, self.keep = name, expr, line, inline, keep


# Python's \w leaves out the vowel signs and other combining marks of many scripts (the "ा" of दाम, Arabic harakat,
# Thai vowels), so a name written in those languages would break in the middle. In a token pattern \w also takes them.
MARKS = ("\u0300-\u036f\u0483-\u0489\u0591-\u05c7\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0711\u0730-\u074a"
         "\u07a6-\u07b0\u0900-\u0903\u093a-\u094f\u0951-\u0957\u0962\u0963\u0981-\u0983\u09bc-\u09d7\u0a01-\u0a03"
         "\u0a3c-\u0a51\u0a70\u0a71\u0a75\u0a81-\u0a83\u0abc-\u0acd\u0b01-\u0b03\u0b3c-\u0b57\u0b82\u0bbe-\u0bcd"
         "\u0bd7\u0c00-\u0c04\u0c3c-\u0c56\u0c81-\u0c83\u0cbc-\u0cd6\u0d00-\u0d03\u0d3b-\u0d57\u0d81-\u0d83"
         "\u0dca-\u0df3\u0e31\u0e34-\u0e3a\u0e47-\u0e4e\u0eb1\u0eb4-\u0ebc\u0ec8-\u0ecd\u0f18\u0f19\u0f35\u0f37"
         "\u0f39\u0f3e\u0f3f\u0f71-\u0f84\u102b-\u103e\u1056-\u1059\u17b4-\u17d3\u1ab0-\u1aff\u1dc0-\u1dff"
         "\u200c\u200d\u20d0-\u20ff\u302a-\u302f\u3099\u309a\ufe00-\ufe0f\ufe20-\ufe2f")
WORDCH = re.compile("[\\w" + MARKS + "]")


def widen(pattern: str) -> str:
    r"""\w -> \w plus combining marks (outside and inside [...]); everything else unchanged."""
    out, i, cls = [], 0, False
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            nxt = pattern[i + 1]
            if nxt == "w":
                out.append(("\\w" + MARKS) if cls else ("[\\w" + MARKS + "]"))
            else:
                out.append(c + nxt)
            i += 2
            continue
        if c == "[" and not cls:
            cls = True
        elif c == "]" and cls and out and out[-1] not in ("[", "[^"):
            cls = False
        out.append(c)
        i += 1
    return "".join(out)


class TokenDef:
    def __init__(self, name: str, pattern: str, regex: bool, line: int):
        self.name, self.pattern, self.regex, self.line = name, pattern, regex, line
        try:
            self.rx = re.compile(widen(pattern) if regex else re.escape(pattern))
        except re.error as e:
            raise GrammarError(f"token {name}: the pattern /{pattern}/ is not a valid regular expression ({e})", line)


# ---------------------------------------------------------------- reading the grammar text
_TOK = re.compile(r"""
    (?P<ws>[ \t\r]+) | (?P<nl>\n) | (?P<com>(?:\#|//)[^\n]*)
  | (?P<dir>%[a-z_]+) | (?P<str>"(?:[^"\\\n]|\\.)*") | (?P<rx>/(?:[^/\\\n]|\\.)+/[imsx]*)
  | (?P<name>[!?]?[A-Za-z_][A-Za-z0-9_]*) | (?P<op>[:|()*+?;=])
""", re.X)


def _unq(s: str) -> str:
    body = s[1:-1]
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t", "r": "\r"}.get(m.group(1), m.group(1)), body)


def _lex_grammar(text: str) -> list[tuple[str, str, int]]:
    out, i, line = [], 0, 1
    while i < len(text):
        m = _TOK.match(text, i)
        if not m:
            raise GrammarError(f"cannot read the grammar here: {text[i:i + 20]!r}", line)
        k = m.lastgroup
        v = m.group()
        if k == "nl":
            line += 1
        elif k not in ("ws", "com"):
            out.append((k, v, line))
        i = m.end()
    out.append(("eof", "", line))
    return out


class Grammar:
    def __init__(self, text: str, start: str = ""):
        if len(text or "") > 200_000:
            raise GrammarError("the grammar is longer than 200,000 characters")
        self.text = text or ""
        self.rules: dict[str, Rule] = {}
        self.tokens: dict[str, TokenDef] = {}
        self.ignore: list[re.Pattern] = []
        self.ignore_src: list[str] = []
        self.allow_keywords = False
        self.order: list[str] = []
        self._read()
        if not self.rules:
            raise GrammarError("the grammar has no rules (a rule looks like: program : statement* ;)")
        self.start = start or self.order[0]
        if self.start not in self.rules:
            raise GrammarError(f"the start rule '{self.start}' is not defined")
        self.literals = sorted({lit.s for lit in self._lits()}, key=len, reverse=True)
        self.keywords = {s for s in self.literals if re.fullmatch(r"[^\W\d]\w*", s)}
        self._mark_kept()

    # -- reading
    def _read(self) -> None:
        t = _lex_grammar(self.text)
        self._t, self._i = t, 0
        while self._peek()[0] != "eof":
            k, v, line = self._peek()
            if k == "dir":
                self._next()
                if v == "%ignore":
                    k2, v2, l2 = self._next()
                    if k2 == "rx":
                        pat, fl = self._rx(v2)
                    elif k2 == "str":
                        pat, fl = re.escape(_unq(v2)), ""
                    else:
                        raise GrammarError("%ignore needs a /regex/ or a \"text\"", l2)
                    try:
                        rx = re.compile(pat, self._flags(fl))
                    except re.error as e:
                        raise GrammarError(f"%ignore /{pat}/ is not a valid regular expression ({e})", l2)
                    if rx.match(""):
                        raise GrammarError(f"%ignore /{pat}/ also matches nothing at all - use + instead of *", l2)
                    self.ignore.append(rx)
                    self.ignore_src.append(pat)
                elif v == "%allow_keywords":
                    self.allow_keywords = True
                else:
                    raise GrammarError(f"unknown directive {v} (known: %ignore, %allow_keywords)", line)
                self._opt(";")
                continue
            if k != "name":
                raise GrammarError(f"a rule name is expected here, not {v!r}", line)
            self._next()
            raw = v
            inline, keep = raw.startswith("?"), raw.startswith("!")
            name = raw.lstrip("?!")
            k2, v2, l2 = self._next()
            if v2 not in (":", "="):
                raise GrammarError(f"after '{name}' a ':' is expected", l2)
            if name in self.rules or name in self.tokens:
                raise GrammarError(f"'{name}' is defined twice", line)
            if name.isupper() or (name[0].isupper() and name.upper() == name):
                k3, v3, l3 = self._next()
                if k3 == "rx":
                    pat, fl = self._rx(v3)
                    if fl:
                        pat = f"(?{fl}){pat}"
                    td = TokenDef(name, pat, True, line)
                elif k3 == "str":
                    td = TokenDef(name, _unq(v3), False, line)
                else:
                    raise GrammarError(f"token {name} needs a /regex/ or a \"text\"", l3)
                if td.rx.match(""):
                    raise GrammarError(f"token {name} also matches nothing at all - it must take at least one character", line)
                self.tokens[name] = td
                self._end(name)
            else:
                if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
                    raise GrammarError(f"rule names are lower case (tokens are UPPER CASE): '{name}'", line)
                expr = self._alt()
                self.rules[name] = Rule(name, expr, line, inline, keep)
                self.order.append(name)
                self._end(name)

    def _rx(self, v: str) -> tuple[str, str]:
        j = v.rindex("/")
        return v[1:j], v[j + 1:]

    @staticmethod
    def _flags(fl: str) -> int:
        f = 0
        for c in fl:
            f |= {"i": re.I, "m": re.M, "s": re.S, "x": re.X}[c]
        return f

    def _peek(self):
        return self._t[self._i]

    def _next(self):
        x = self._t[self._i]
        self._i += 1
        return x

    def _opt(self, op: str) -> bool:
        if self._peek()[1] == op and self._peek()[0] == "op":
            self._i += 1
            return True
        return False

    def _end(self, name: str) -> None:
        k, v, line = self._peek()
        if v == ";":
            self._i += 1
            return
        if k == "eof":
            return
        # no ';': allowed when the next thing starts a new definition (name followed by ':')
        if k in ("name", "dir") and (k == "dir" or self._t[self._i + 1][1] in (":", "=")):
            return
        raise GrammarError(f"'{name}' should end with ';' (found {v!r})", line)

    def _alt(self) -> E:
        alts = [self._seq()]
        while self._opt("|"):
            alts.append(self._seq())
        return alts[0] if len(alts) == 1 else Alt(alts)

    def _seq(self) -> E:
        items: list[E] = []
        while True:
            k, v, line = self._peek()
            if k == "op" and v in ("|", ")", ";"):
                break
            if k == "eof":
                break
            if k == "name" and self._t[self._i + 1][1] in (":", "=") and not v.startswith(("?", "!")) and items:
                break          # the next definition starts (a missing ';')
            if k == "name" and v.startswith(("?", "!")):
                break
            if k == "dir":
                break
            items.append(self._postfix())
        if not items:
            k, v, line = self._peek()
            raise GrammarError("an empty choice: something must come between | and | (use ? for optional parts)", line)
        return items[0] if len(items) == 1 else Seq(items)

    def _postfix(self) -> E:
        e = self._atom()
        while True:
            k, v, _ = self._peek()
            if k == "op" and v in "*+?":
                self._i += 1
                e = Rep(e, 0 if v != "+" else 1, None if v != "?" else 1)
            else:
                return e

    def _atom(self) -> E:
        k, v, line = self._next()
        if k == "str":
            s = _unq(v)
            if not s:
                raise GrammarError('an empty "" fixed text', line)
            return Lit(s)
        if k == "name":
            return Ref(v, line)
        if k == "op" and v == "(":
            e = self._alt()
            if not self._opt(")"):
                raise GrammarError("a '(' is not closed", line)
            return e
        if k == "rx":
            raise GrammarError(f"a /regex/ inside a rule: give it a token name, like NAME : {v} ;", line)
        raise GrammarError(f"unexpected {v!r}", line)

    # -- walking
    def _walk(self, e: E):
        yield e
        for c in (e.items if isinstance(e, Seq) else e.alts if isinstance(e, Alt) else [e.item] if isinstance(e, Rep) else []):
            yield from self._walk(c)

    def _lits(self):
        for r in self.rules.values():
            for e in self._walk(r.expr):
                if isinstance(e, Lit):
                    yield e

    def _mark_kept(self) -> None:
        for r in self.rules.values():
            for e in self._walk(r.expr):
                if isinstance(e, Alt) and all(isinstance(a, Lit) for a in e.alts):
                    for a in e.alts:
                        a.keep = True
            if r.keep:
                for e in self._walk(r.expr):
                    if isinstance(e, Lit):
                        e.keep = True

    # ---------------------------------------------------------------- checks
    def check(self) -> dict[str, list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        warns: list[dict[str, Any]] = []
        for r in self.rules.values():
            for e in self._walk(r.expr):
                if isinstance(e, Ref) and e.name not in self.rules and e.name not in self.tokens:
                    errors.append({"line": e.line, "rule": r.name, "say": f"'{e.name}' is used in {r.name} but never defined"})
        if errors:
            return {"errors": errors, "warnings": warns}
        null = self.nullable()
        for r in self.rules.values():
            for e in self._walk(r.expr):
                if isinstance(e, Rep) and e.hi is None and self._null(e.item, null):
                    errors.append({"line": r.line, "rule": r.name,
                                   "say": f"in {r.name} a repeated part (* or +) can match nothing, so it would loop for ever"})
        for name, path in self.left_recursion(null).items():
            r = self.rules[name]
            errors.append({"line": r.line, "rule": name,
                           "say": f"{name} is left-recursive ({' -> '.join(path)}): it calls itself before reading anything. "
                                  f"Write it as a loop, e.g. {name} : item (op item)* ;"})
        reach = self.reachable()
        for n in self.order:
            if n not in reach:
                warns.append({"line": self.rules[n].line, "rule": n, "say": f"rule {n} is never used from {self.start}"})
        for n, td in self.tokens.items():
            if n not in reach:
                warns.append({"line": td.line, "rule": n, "say": f"token {n} is never used"})
        for r in self.rules.values():
            for e in self._walk(r.expr):
                if isinstance(e, Alt):
                    for i, a in enumerate(e.alts):
                        for b in e.alts[i + 1:]:
                            sa, sb = self._first_lit(a), self._first_lit(b)
                            if sa and sb and sb.startswith(sa) and sa != sb and not re.fullmatch(r"\w+", sa) and \
                                    isinstance(a, Lit):
                                warns.append({"line": r.line, "rule": r.name,
                                              "say": f'in {r.name} "{sb}" can never match: "{sa}" comes first and wins. '
                                                     f'Put "{sb}" first.'})
                    firsts = [self._first_lit(a) if isinstance(a, Lit) else "" for a in e.alts]
                    seen = set()
                    for f_ in firsts:
                        if f_ and f_ in seen:
                            warns.append({"line": r.line, "rule": r.name, "say": f'in {r.name} "{f_}" is a choice twice'})
                        seen.add(f_)
        for n, td in self.tokens.items():
            if td.regex and re.search(r"\((?:[^()\\]|\\.)*[+*]\)[+*{]", td.pattern):
                warns.append({"line": td.line, "rule": n,
                              "say": f"token {n} repeats something that repeats - on long input it can be very slow. "
                                     "Simplify the pattern."})
        return {"errors": errors, "warnings": warns}

    def _first_lit(self, e: E) -> str:
        if isinstance(e, Lit):
            return e.s
        if isinstance(e, Seq) and e.items and isinstance(e.items[0], Lit):
            return e.items[0].s
        return ""

    def nullable(self) -> set[str]:
        null: set[str] = set()
        changed = True
        while changed:
            changed = False
            for r in self.rules.values():
                if r.name not in null and self._null(r.expr, null):
                    null.add(r.name)
                    changed = True
        return null

    def _null(self, e: E, null: set[str]) -> bool:
        if isinstance(e, Lit):
            return False
        if isinstance(e, Ref):
            return e.name in null
        if isinstance(e, Seq):
            return all(self._null(i, null) for i in e.items)
        if isinstance(e, Alt):
            return any(self._null(a, null) for a in e.alts)
        if isinstance(e, Rep):
            return e.lo == 0 or self._null(e.item, null)
        return False

    def _left(self, e: E, null: set[str]) -> set[str]:
        """Rules that can come first (before any character is read) in e."""
        if isinstance(e, Ref):
            return {e.name} if e.name in self.rules else set()
        if isinstance(e, Seq):
            out: set[str] = set()
            for i in e.items:
                out |= self._left(i, null)
                if not self._null(i, null):
                    break
            return out
        if isinstance(e, Alt):
            out = set()
            for a in e.alts:
                out |= self._left(a, null)
            return out
        if isinstance(e, Rep):
            return self._left(e.item, null)
        return set()

    def left_recursion(self, null: set[str] | None = None) -> dict[str, list[str]]:
        null = self.nullable() if null is None else null
        edges = {n: self._left(r.expr, null) for n, r in self.rules.items()}
        found: dict[str, list[str]] = {}
        for n in self.order:
            stack, seen = [(n, [n])], {n}
            while stack:
                cur, path = stack.pop()
                for m in edges.get(cur, ()):
                    if m == n:
                        found[n] = path + [n]
                        stack = []
                        break
                    if m not in seen:
                        seen.add(m)
                        stack.append((m, path + [m]))
        return found

    def reachable(self) -> set[str]:
        out, todo = set(), [self.start]
        while todo:
            n = todo.pop()
            if n in out:
                continue
            out.add(n)
            if n in self.rules:
                for e in self._walk(self.rules[n].expr):
                    if isinstance(e, Ref):
                        todo.append(e.name)
        return out

    # ---------------------------------------------------------------- the grammar as EBNF text + a picture model
    def ebnf(self, e: E | None = None) -> str:
        if e is None:
            return "\n".join(f"{('?' if r.inline else '!' if r.keep else '')}{n} : {self.ebnf(r.expr)} ;"
                             for n, r in self.rules.items())
        if isinstance(e, Lit):
            return '"' + e.s.replace('"', '\\"') + '"'
        if isinstance(e, Ref):
            return e.name
        if isinstance(e, Seq):
            return " ".join(self._par(i) for i in e.items)
        if isinstance(e, Alt):
            return " | ".join(self.ebnf(a) for a in e.alts)
        if isinstance(e, Rep):
            return self._par(e.item, True) + ("?" if e.hi == 1 else "+" if e.lo == 1 else "*")
        return ""

    def _par(self, e: E, tight: bool = False) -> str:
        s = self.ebnf(e)
        return f"({s})" if isinstance(e, Alt) or (tight and isinstance(e, Seq)) else s

    def shape(self, e: E) -> dict[str, Any]:
        """A JSON form of a rule for drawing (railroad diagrams)."""
        if isinstance(e, Lit):
            return {"k": "lit", "s": e.s}
        if isinstance(e, Ref):
            return {"k": "tok" if e.name in self.tokens else "ref", "s": e.name}
        if isinstance(e, Seq):
            return {"k": "seq", "c": [self.shape(i) for i in e.items]}
        if isinstance(e, Alt):
            return {"k": "alt", "c": [self.shape(a) for a in e.alts]}
        if isinstance(e, Rep):
            return {"k": "opt" if e.hi == 1 else "many1" if e.lo == 1 else "many", "c": [self.shape(e.item)]}
        return {"k": "lit", "s": "?"}

    # ---------------------------------------------------------------- parsing
    def parse(self, src: str, start: str = "") -> Node:
        return _Parser(self, src).run(start or self.start)

    # ---------------------------------------------------------------- making example programs (fuzzing)
    def sample(self, rnd: random.Random | None = None, depth: int = 8, rule: str = "") -> str:
        rnd = rnd or random.Random(1)
        sep = " " if any(rx.match(" ") for rx in self.ignore) else ""
        parts: list[str] = []
        mind = self._min_depth()
        self._gen(Ref(rule or self.start, 0), rnd, depth, parts, mind)
        out = ""
        for p in parts:
            if out and sep and (re.match(r"\w", p[:1] or " ") and re.search(r"\w$", out) or True):
                out += sep
            out += p
        return out

    def _min_depth(self) -> dict[str, int]:
        INF = 10 ** 6
        d = {n: INF for n in self.rules}

        def md(e: E) -> int:
            if isinstance(e, (Lit,)):
                return 0
            if isinstance(e, Ref):
                return 0 if e.name in self.tokens else d.get(e.name, INF) + 1
            if isinstance(e, Seq):
                return max((md(i) for i in e.items), default=0)
            if isinstance(e, Alt):
                return min(md(a) for a in e.alts)
            if isinstance(e, Rep):
                return 0 if e.lo == 0 else md(e.item)
            return 0
        for _ in range(len(self.rules) + 2):
            for n, r in self.rules.items():
                d[n] = min(d[n], md(r.expr))
        self._md = md
        return d

    def _gen(self, e: E, rnd: random.Random, depth: int, out: list[str], mind: dict[str, int]) -> None:
        if len(out) > 400:
            return
        if isinstance(e, Lit):
            out.append(e.s)
        elif isinstance(e, Ref):
            if e.name in self.tokens:
                out.append(self.sample_token(e.name, rnd))
            else:
                self._gen(self.rules[e.name].expr, rnd, depth - 1, out, mind)
        elif isinstance(e, Seq):
            for i in e.items:
                self._gen(i, rnd, depth, out, mind)
        elif isinstance(e, Alt):
            if depth <= 0:
                best = min(e.alts, key=self._md)
                self._gen(best, rnd, depth, out, mind)
            else:
                self._gen(rnd.choice(e.alts), rnd, depth, out, mind)
        elif isinstance(e, Rep):
            n = e.lo if depth <= 0 else rnd.randint(e.lo, e.hi if e.hi is not None else e.lo + 2)
            for _ in range(n):
                self._gen(e.item, rnd, depth, out, mind)

    def sample_token(self, name: str, rnd: random.Random | None = None) -> str:
        rnd = rnd or random.Random(1)
        td = self.tokens[name]
        if not td.regex:
            return td.pattern
        for _ in range(30):
            try:
                s = _sample_rx(td.pattern, rnd)
            except Exception:   # noqa: BLE001
                s = ""
            if s and td.rx.fullmatch(s) and (self.allow_keywords or s not in self.keywords) and \
                    not any(rx.match(s) for rx in self.ignore):
                return s
        return "x"


# ---------------------------------------------------------------- the packrat parser
class _Fail(Exception):
    pass


class _Parser:
    def __init__(self, g: Grammar, src: str):
        if len(src) > MAX_SOURCE:
            raise ParseError("the program is longer than 2,000,000 characters", 1, 1, [], "", "")
        self.g, self.s, self.n = g, src, len(src)
        self.memo: dict[tuple[str, int], Any] = {}
        self.far, self.exp = 0, set()
        self.steps = 0
        self._lines = [0] + [m.end() for m in re.finditer(r"\n", src)]

    def pos(self, i: int) -> tuple[int, int]:
        lo, hi = 0, len(self._lines) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._lines[mid] <= i:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1, i - self._lines[lo] + 1

    def skip(self, i: int) -> int:
        if not self.g.ignore:
            return i
        while True:
            j = i
            for rx in self.g.ignore:
                m = rx.match(self.s, j)
                if m and m.end() > j:
                    j = m.end()
            if j == i:
                return i
            i = j

    def fail(self, i: int, what: str):
        if i > self.far:
            self.far, self.exp = i, {what}
        elif i == self.far:
            self.exp.add(what)
        raise _Fail()

    def run(self, start: str) -> Node:
        i = self.skip(0)
        try:
            kids, j = self.rule(start, i)
            j = self.skip(j)
            if j < self.n:
                self.fail(j, "end of the program")
        except _Fail:
            raise self.error()
        except RecursionError:
            l_, c_ = self.pos(self.far)
            raise ParseError("the program nests too deep for this parser", l_, c_, [], "", "")
        if isinstance(kids, Node):
            return kids
        line, col = self.pos(i)
        return Node(start, [k for k in kids] if isinstance(kids, list) else [kids], line, col)

    def error(self) -> ParseError:
        line, col = self.pos(self.far)
        start = self._lines[line - 1]
        end = self.s.find("\n", start)
        end = self.n if end < 0 else end
        text = self.s[start:end]
        pointer = text.replace("\t", " ") + "\n" + " " * (col - 1) + "^"
        if self.far >= self.n:
            found = "the end of the program"
        else:
            m = re.match(r"\w+|\S", self.s[self.far:])
            found = repr(m.group()) if m else "a space"
        exp = sorted(self.exp, key=lambda x: (not x.startswith('"'), x))[:8]
        msg = f"expected {' or '.join(exp)} but found {found}" if exp else f"cannot read {found}"
        return ParseError(msg, line, col, exp, found, pointer)

    def rule(self, name: str, i: int):
        key = (name, i)
        if key in self.memo:
            r = self.memo[key]
            if r is None:
                raise _Fail()
            return r
        self.memo[key] = None                # a guard: a rule that re-enters itself at the same place fails
        r = self.g.rules[name]
        line, col = self.pos(self.skip(i))
        try:
            kids, j = self.expr(r.expr, i)
        except _Fail:
            raise
        kids = [k for k in kids if k is not None]
        if r.inline and len(kids) == 1:
            res = (kids[0], j)
        else:
            res = (Node(name, kids, line, col), j)
        self.memo[key] = res
        return res

    def expr(self, e: E, i: int) -> tuple[list, int]:
        self.steps += 1
        if self.steps > MAX_STEPS:
            line, col = self.pos(i)
            raise ParseError("the program is too complex for this grammar (the parser stopped after 2,000,000 steps)",
                             line, col, [], "", "")
        if isinstance(e, Lit):
            i = self.skip(i)
            if self.s.startswith(e.s, i):
                end = i + len(e.s)
                if e.word and end < self.n and WORDCH.match(self.s[end]):
                    self.fail(i, f'"{e.s}"')
                if e.keep:
                    line, col = self.pos(i)
                    return [Tok(f'"{e.s}"', e.s, line, col)], end
                return [], end
            self.fail(i, f'"{e.s}"')
        if isinstance(e, Ref):
            if e.name in self.g.tokens:
                i = self.skip(i)
                td = self.g.tokens[e.name]
                m = td.rx.match(self.s, i)
                if not m or m.end() == i:
                    self.fail(i, e.name)
                txt = m.group()
                if not self.g.allow_keywords and txt in self.g.keywords and td.regex:
                    self.fail(i, e.name)
                line, col = self.pos(i)
                return [Tok(e.name, txt, line, col)], m.end()
            node, j = self.rule(e.name, i)
            return [node], j
        if isinstance(e, Seq):
            out: list = []
            for it in e.items:
                k, i = self.expr(it, i)
                out.extend(k)
            return out, i
        if isinstance(e, Alt):
            for a in e.alts:
                try:
                    return self.expr(a, i)
                except _Fail:
                    continue
            raise _Fail()
        if isinstance(e, Rep):
            out = []
            n = 0
            while e.hi is None or n < e.hi:
                try:
                    k, j = self.expr(e.item, i)
                except _Fail:
                    break
                if j == i and n >= e.lo:
                    break
                out.extend(k)
                i, n = j, n + 1
            if n < e.lo:
                raise _Fail()
            return out, i
        raise _Fail()


# ---------------------------------------------------------------- a small regex sampler (for example programs)
def _sample_rx(pattern: str, rnd: random.Random) -> str:
    tree = _sre.parse(pattern)
    return _emit(tree, rnd, 0)


def _emit(items, rnd: random.Random, depth: int) -> str:
    out = []
    C = _src
    for op, av in items:
        if op is C.LITERAL:
            out.append(chr(av))
        elif op is C.NOT_LITERAL:
            out.append("a" if chr(av) != "a" else "b")
        elif op is C.ANY:
            out.append(rnd.choice("abcxyz"))
        elif op is C.IN:
            out.append(_pick_in(av, rnd))
        elif op in (C.MAX_REPEAT, C.MIN_REPEAT, getattr(C, "POSSESSIVE_REPEAT", None)):
            lo, hi, sub = av
            hi = min(hi if hi != C.MAXREPEAT else lo + 3, lo + 3)
            n = rnd.randint(lo, max(lo, hi))
            for _ in range(n):
                out.append(_emit(sub, rnd, depth + 1))
        elif op is C.SUBPATTERN:
            out.append(_emit(av[-1], rnd, depth + 1))
        elif op is C.BRANCH:
            out.append(_emit(rnd.choice(av[1]), rnd, depth + 1))
        elif op is C.CATEGORY:
            out.append(_cat(av, rnd))
        elif op is C.AT:
            pass
        else:
            pass
    return "".join(out)


def _cat(av, rnd: random.Random) -> str:
    C = _src
    if av is C.CATEGORY_DIGIT:
        return rnd.choice("0123456789")
    if av is C.CATEGORY_SPACE:
        return " "
    if av is C.CATEGORY_WORD:
        return rnd.choice("abcxyz")
    if av is C.CATEGORY_NOT_DIGIT:
        return "a"
    return "a"


def _pick_in(av, rnd: random.Random) -> str:
    C = _src
    neg = any(op is C.NEGATE for op, _ in av)
    pool: list[str] = []
    for op, v in av:
        if op is C.LITERAL:
            pool.append(chr(v))
        elif op is C.RANGE:
            lo, hi = v
            pool.extend(chr(c) for c in range(lo, min(hi, lo + 25) + 1))
        elif op is C.CATEGORY:
            pool.append(_cat(v, rnd))
    if neg:
        for c in "abcxyz019 ":
            if c not in pool:
                return c
        return "q"
    return rnd.choice(pool) if pool else "a"


def load(text: str, start: str = "") -> Grammar:
    return Grammar(text, start)
