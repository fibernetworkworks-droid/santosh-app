"""v0.939 HOOLA CODE MAKES THINGS (owner, on the design canvas claude.ai/artifact/BjGPb7Tkqfx6QqpgkDznxH -> "GO BUILD"):
Hoola Code makes the things Claude makes beside the code - a PRD or any document, a web page, a clickable prototype,
an artboard of screens, a sheet - each one a card in her session that opens full screen, with versions she can go back to.

The model makes one in parts so she watches it grow (Claude's artifact card says what it is writing now):
  make start  (kind, title, parts)   -> a new thing, or a new version of one (id given)
  make write  (id, part, content)    -> one section / screen / tab, checked for its kind
  make finish (id)                   -> the file is built (Markdown, a self-contained HTML page, an .xlsx with real
                                        formulas), the version is ready, and what was checked is said
Her phone reads the list (`listing`) inside the session view and one thing (`detail`) when she opens it. The built file is
served on a signed link (`link`) only: HTML always with a sandbox CSP (its own opaque origin - it can never read the
console's sign-in) and no network but Google Fonts; a sheet's preview values come from a small formula reader here, and a
formula it cannot work out is shown as the formula and named, never as a made-up number."""
from __future__ import annotations

import hashlib
import hmac
import html as _html
import json
import re
import threading
import time
from pathlib import Path
from typing import Any

KINDS: dict[str, tuple[str, str, str]] = {        # kind: (label, file extension, what one part is)
    "doc": ("Document", "md", "section"),
    "page": ("Web page", "html", "section"),
    "prototype": ("Prototype", "html", "screen"),
    "artboard": ("Artboard", "html", "screen"),
    "sheet": ("Sheet", "xlsx", "tab"),
}
ALIASES = {"prd": "doc", "document": "doc", "spec": "doc", "markdown": "doc", "md": "doc", "report": "doc",
           "web": "page", "html": "page", "website": "page", "landing": "page", "webpage": "page",
           "proto": "prototype", "clickable": "prototype", "board": "artboard", "screens": "artboard", "mockup": "artboard",
           "spreadsheet": "sheet", "excel": "sheet", "xlsx": "sheet", "table": "sheet", "csv": "sheet"}
MAX_THINGS, MAX_PARTS, MAX_VERSIONS = 20, 12, 30
MAX_PART = {"doc": 40000, "page": 120000, "prototype": 80000, "artboard": 80000, "sheet": 200000}
MAX_ROWS, MAX_COLS = 2000, 40
LINK_HOURS = 24
_LOCK = threading.RLock()

TOOL: dict[str, Any] = {
    "name": "make",
    "description": (
        "Make a THING for her beside the code, shown as a card in her session that she opens full screen (the way Claude "
        "makes artifacts): kind doc (a PRD, spec, plan, report - Markdown), page (one web page / landing page - HTML), "
        "prototype (a clickable flow of phone screens - HTML, one part per screen), artboard (several screens side by "
        "side to compare - HTML, one part per screen), sheet (a spreadsheet - one part per tab). "
        "action=start with kind, title and parts (the section / screen / tab names, in order) -> it returns the id. Then "
        "action=write once per part with id, part and content, then action=finish with id. To CHANGE a thing: start again "
        "with its id (a new version keeps every part), write only the parts that change, finish. action=list shows what "
        "exists. Content rules: doc = Markdown for that one section, starting with its own '## heading'. page / "
        "prototype / artboard = an HTML fragment (no <html>/<head>/<body>), inline <style> allowed and kept to this part's "
        "own class names, no outside scripts, images only as data: or https URLs; design for a 390 px wide phone unless "
        "she asked otherwise. In a prototype, move between screens with <a href=\"#Screen name\"> or data-go=\"Screen "
        "name\" on any button. sheet = JSON {\"columns\": [...], \"rows\": [[...], ...]}: numbers as numbers, a formula "
        "as a string starting with = (A1 style, the header is row 1, so data starts at row 2), e.g. \"=SUM(C2:C8)\". "
        "Use her real facts; a fact you do not know becomes a [BLANK TO FILL], never a made-up number. Make a thing only "
        "when she asks for one (a PRD, prototype, mockup, screens, sheet, page); code changes stay in the repo."),
    "input_schema": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["start", "write", "finish", "list"]},
        "id": {"type": "string", "description": "the thing's id (from start); with start = a new version of it"},
        "kind": {"type": "string", "enum": list(KINDS)},
        "title": {"type": "string", "description": "a short name she will recognise, e.g. 'Salon booking · PRD'"},
        "parts": {"type": "array", "items": {"type": "string"}, "description": "section / screen / tab names, in order"},
        "part": {"type": "string", "description": "for write: which part"},
        "content": {"type": "string", "description": "for write: that part's content (see the rules above)"},
        "note": {"type": "string", "description": "for start of a new version: what changes, in a few words"}},
        "required": ["action"]}}

HOWTO = ("MAKING THINGS (the make tool): when she asks for a PRD / spec / plan document, a web page, a clickable prototype, "
         "screens or a mockup to compare, or a spreadsheet, make it with make (start -> write each part -> finish), not as "
         "a file in the repo unless she asks for it in the repo. Read the code first when it is about her app, so the "
         "thing matches what is really there. After finish, tell her in one or two sentences what it holds; she opens "
         "the card herself. To change one, start with its id and write only the parts that change.")


def _settings():
    from ..config import get_settings
    return get_settings()


def on() -> bool:
    return bool(getattr(_settings(), "dev_make", True))


def root() -> Path:
    return Path("data") / "devsahayak" / "made"


def _tdir(tid: str) -> Path:
    return root() / (re.sub(r"[^A-Za-z0-9_-]", "", tid or "") or "x")


def _mdir(tid: str, mid: str) -> Path:
    return _tdir(tid) / (re.sub(r"[^a-z0-9-]", "", mid or "") or "x")


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(s: str, n: int = 40) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")[:n] or "thing"


def _kind(k: Any) -> str:
    k = str(k or "").strip().lower()
    return k if k in KINDS else ALIASES.get(k, "")


def _meta(tid: str, mid: str) -> dict[str, Any] | None:
    f = _mdir(tid, mid) / "meta.json"
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text())
    except ValueError:
        return None


def _save(tid: str, m: dict[str, Any]) -> None:
    d = _mdir(tid, m["id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(m, ensure_ascii=False))
    tmp.replace(d / "meta.json")


def _ids(tid: str) -> list[str]:
    d = _tdir(tid)
    if not d.is_dir():
        return []
    return sorted((p.name for p in d.iterdir() if (p / "meta.json").is_file()),
                  key=lambda x: (_mdir(tid, x) / "meta.json").stat().st_mtime)


def _part_file(tid: str, mid: str, v: int, i: int) -> Path:
    return _mdir(tid, mid) / f"v{v}" / f"part{i}.txt"


def _part_text(tid: str, mid: str, ver: dict[str, Any], i: int) -> str:
    src = (ver.get("src") or {}).get(str(i))           # a part carried over from an earlier version is read from there
    v = int(src) if src else int(ver["v"])
    f = _part_file(tid, mid, v, i)
    return f.read_text() if f.is_file() else ""


def _latest(m: dict[str, Any]) -> dict[str, Any]:
    return m["versions"][-1]


def _ready(m: dict[str, Any]) -> dict[str, Any] | None:
    for ver in reversed(m["versions"]):
        if ver.get("state") == "ready":
            return ver
    return None


# ---------------------------------------------------------------- checking one part
def _check_html(content: str) -> str:
    low = content.lower()
    if re.search(r"<script[^>]*\bsrc\s*=", low):
        return "outside scripts are not allowed - put the script inline"
    if re.search(r"<\s*(html|head|body)\b", low):
        return "send a fragment only: no <html>, <head> or <body>"
    if re.search(r"<(iframe|object|embed)\b", low):
        return "no <iframe>, <object> or <embed>"
    return ""


def _check_sheet(content: str) -> tuple[dict[str, Any] | None, str]:
    try:
        d = json.loads(content)
    except ValueError as e:
        return None, f"not valid JSON ({e})"
    if not isinstance(d, dict) or not isinstance(d.get("columns"), list) or not isinstance(d.get("rows"), list):
        return None, 'it must be {"columns": [...], "rows": [[...], ...]}'
    cols = [str(c)[:80] for c in d["columns"]][:MAX_COLS]
    if not cols:
        return None, "a tab needs at least one column"
    rows = []
    for r in d["rows"][:MAX_ROWS]:
        if not isinstance(r, list):
            return None, "every row must be a list of cells"
        rows.append([c if isinstance(c, (int, float)) and not isinstance(c, bool) else ("" if c is None else str(c)[:500])
                     for c in r[:len(cols)]])
    return {"columns": cols, "rows": rows}, ""


# ---------------------------------------------------------------- a small formula reader (sheet previews)
_REF = re.compile(r"\$?([A-Z]{1,3})\$?(\d{1,5})")


def _col_n(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def col_name(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


class _FormulaError(Exception):
    pass


class _Reader:
    """=SUM(C2:C8), =B2*C2, =ROUND(AVERAGE(D2:D9),1), =IF(B2>0,B2,0) - enough for a preview; anything else is said."""
    FUNCS = ("SUM", "AVERAGE", "MIN", "MAX", "COUNT", "ROUND", "ABS", "IF")

    def __init__(self, grid: list[list[Any]], depth: int = 0):
        self.grid, self.depth = grid, depth

    def cell(self, r: int, c: int) -> Any:
        if r < 0 or r >= len(self.grid) or c < 0 or c >= len(self.grid[r]):
            return 0
        v = self.grid[r][c]
        if isinstance(v, str) and v.startswith("="):
            if self.depth > 30:
                raise _FormulaError("a formula refers to itself")
            return _Reader(self.grid, self.depth + 1).value(v)
        return v

    def value(self, formula: str) -> Any:
        self.toks = re.findall(r"\$?[A-Z]{1,3}\$?\d{1,5}(?::\$?[A-Z]{1,3}\$?\d{1,5})?|[A-Z]+(?=\()|\d+(?:\.\d+)?|"
                               r"\"[^\"]*\"|<=|>=|<>|[-+*/(),<>=&^%]", formula[1:].upper().replace(" ", ""))
        joined = "".join(self.toks)
        if joined != formula[1:].upper().replace(" ", "").replace("'", ""):
            raise _FormulaError("this formula has parts the preview cannot read")
        self.i = 0
        v = self.cmp()
        if self.i != len(self.toks):
            raise _FormulaError("this formula has parts the preview cannot read")
        return v

    def peek(self) -> str:
        return self.toks[self.i] if self.i < len(self.toks) else ""

    def take(self) -> str:
        t = self.peek()
        self.i += 1
        return t

    def cmp(self) -> Any:
        a = self.add()
        while self.peek() in ("<", ">", "=", "<=", ">=", "<>"):
            op, b = self.take(), self.add()
            a = {"<": a < b, ">": a > b, "=": a == b, "<=": a <= b, ">=": a >= b, "<>": a != b}[op]
        return a

    def add(self) -> Any:
        a = self.mul()
        while self.peek() in ("+", "-"):
            op, b = self.take(), self.mul()
            a = _num(a) + _num(b) if op == "+" else _num(a) - _num(b)
        return a

    def mul(self) -> Any:
        a = self.unary()
        while self.peek() in ("*", "/"):
            op, b = self.take(), self.unary()
            if op == "/" and _num(b) == 0:
                raise _FormulaError("divides by zero")
            a = _num(a) * _num(b) if op == "*" else _num(a) / _num(b)
        return a

    def unary(self) -> Any:
        if self.peek() == "-":
            self.take()
            return -_num(self.unary())
        if self.peek() == "+":
            self.take()
            return _num(self.unary())
        v = self.atom()
        if self.peek() == "%":
            self.take()
            v = _num(v) / 100
        return v

    def args(self) -> list[Any]:
        if self.take() != "(":
            raise _FormulaError("this formula has parts the preview cannot read")
        out: list[Any] = []
        if self.peek() == ")":
            self.take()
            return out
        while True:
            t = self.peek()
            if ":" in t:
                self.take()
                out.append(self.range(t))
            else:
                out.append(self.cmp())
            sep = self.take()
            if sep == ")":
                return out
            if sep != ",":
                raise _FormulaError("this formula has parts the preview cannot read")

    def range(self, t: str) -> list[Any]:
        a, b = t.split(":")
        (c1, r1), (c2, r2) = (_REF.fullmatch(a).groups(), _REF.fullmatch(b).groups())   # type: ignore[union-attr]
        cs, ce = sorted((_col_n(c1), _col_n(c2)))
        rs, re_ = sorted((int(r1) - 1, int(r2) - 1))
        return [self.cell(r, c) for r in range(rs, re_ + 1) for c in range(cs, ce + 1)]

    def atom(self) -> Any:
        t = self.take()
        if not t:
            raise _FormulaError("this formula ends too early")
        if t == "(":
            v = self.cmp()
            if self.take() != ")":
                raise _FormulaError("a bracket is not closed")
            return v
        if t in self.FUNCS:
            a = self.args()
            flat = [x for v in a for x in (v if isinstance(v, list) else [v])]
            nums = [_num(x) for x in flat if isinstance(x, (int, float)) and not isinstance(x, bool)]
            if t == "SUM":
                return sum(nums)
            if t == "AVERAGE":
                return sum(nums) / len(nums) if nums else 0
            if t == "MIN":
                return min(nums) if nums else 0
            if t == "MAX":
                return max(nums) if nums else 0
            if t == "COUNT":
                return len(nums)
            if t == "ABS":
                return abs(_num(a[0])) if a else 0
            if t == "ROUND":
                return round(_num(a[0]), int(_num(a[1])) if len(a) > 1 else 0) if a else 0
            if t == "IF":
                return (a[1] if len(a) > 1 else True) if a and a[0] else (a[2] if len(a) > 2 else False)
        if re.fullmatch(r"[A-Z]+", t):
            raise _FormulaError(f"the preview cannot work out {t}()")
        if t.startswith('"'):
            return t[1:-1]
        m = _REF.fullmatch(t)
        if m:
            return self.cell(int(m.group(2)) - 1, _col_n(m.group(1)))
        try:
            return float(t) if "." in t else int(t)
        except ValueError:
            raise _FormulaError("this formula has parts the preview cannot read")


def _num(v: Any) -> float:
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return v
    try:
        return float(str(v).replace(",", "").replace("₹", "").strip() or 0)
    except ValueError:
        raise _FormulaError("adds up a cell that holds words")


def sheet_preview(tab: dict[str, Any]) -> dict[str, Any]:
    """The tab as she sees it: every formula worked out (or named when it cannot be), plus the formula behind each cell."""
    grid = [list(tab["columns"])] + [list(r) + [""] * (len(tab["columns"]) - len(r)) for r in tab["rows"]]
    rd = _Reader(grid)
    shown, formulas, problems = [], {}, []
    for ri, row in enumerate(grid[1:], start=2):
        out = []
        for ci_, v in enumerate(row):
            if isinstance(v, str) and v.startswith("="):
                ref = f"{col_name(ci_)}{ri}"
                formulas[ref] = v
                try:
                    val = rd.value(v)
                    out.append(_fmt(val))
                except (_FormulaError, RecursionError, TypeError, ValueError, AttributeError, IndexError) as e:
                    out.append(v)
                    problems.append(f"{ref}: {e if isinstance(e, _FormulaError) else 'the preview could not work it out'}")
            else:
                out.append(_fmt(v))
        shown.append(out)
    return {"columns": grid[0], "rows": shown, "formulas": formulas, "problems": problems[:20]}


def _fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        if v.is_integer():
            v = int(v)
        else:
            return f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


# ---------------------------------------------------------------- building the file
_BASE_CSS = ("*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;"
             "color:#1B1A17;background:#FFFFFF;line-height:1.5}img{max-width:100%}")


def _screen_id(name: str) -> str:
    return "s-" + _slug(name, 60)


def _page(title: str, body: str, extra_css: str = "", script: str = "") -> str:
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            "content=\"width=device-width,initial-scale=1\"><title>" + _html.escape(title) + "</title><style>" + _BASE_CSS
            + extra_css + "</style></head><body>" + body + (("<script>" + script + "</script>") if script else "")
            + "</body></html>")


_PROTO_JS = ("(function(){var s=[].slice.call(document.querySelectorAll('.hs-screen'));function sl(t){return 's-'+String(t||'')"
             ".toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,60)}function go(id){var hit=null;s.forEach("
             "function(e){if(e.id===id)hit=e});if(!hit)return false;s.forEach(function(e){e.hidden=e!==hit});window.scrollTo(0,0);"
             "return true}document.addEventListener('click',function(ev){var el=ev.target.closest('[data-go],a[href^=\"#\"]');"
             "if(!el)return;var t=el.getAttribute('data-go')||decodeURIComponent((el.getAttribute('href')||'').slice(1));"
             "if(go(t.indexOf('s-')===0?t:sl(t)))ev.preventDefault()});var h=decodeURIComponent(location.hash.slice(1));"
             "if(!(h&&go(h.indexOf('s-')===0?h:sl(h)))&&s[0])go(s[0].id)})();")

_BOARD_CSS = ("body{background:#ECEBE6}.hs-grid{display:flex;flex-wrap:wrap;gap:28px;padding:24px;justify-content:center}"
              ".hs-cell{display:flex;flex-direction:column;gap:8px;align-items:flex-start}"
              ".hs-frame{width:195px;height:422px;overflow:hidden;border-radius:16px;background:#fff;"
              "box-shadow:0 1px 3px rgba(0,0,0,.12)}.hs-frame iframe{width:390px;height:844px;border:0;"
              "transform:scale(.5);transform-origin:0 0}.hs-name{font:600 13px system-ui,sans-serif;color:#1B1A17}")


def build(tid: str, m: dict[str, Any], ver: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Writes v<n>/out.<ext> and returns (its file name, facts) - facts = what the card says and what was checked."""
    kind, names = m["kind"], ver["parts"]
    texts = [_part_text(tid, m["id"], ver, i) for i in range(len(names))]
    d = _mdir(tid, m["id"]) / f"v{ver['v']}"
    d.mkdir(parents=True, exist_ok=True)
    facts: dict[str, Any] = {"parts": len(names)}
    if kind == "doc":
        body = "\n\n".join(x.strip() for x in texts if x.strip())
        if not body.lstrip().startswith("# "):
            body = f"# {m['title']}\n\n" + body
        (d / "out.md").write_text(body + "\n")
        facts["words"] = len(re.findall(r"\w+", body))
        facts["line"] = f"{len(names)} section{'s' if len(names) != 1 else ''} · {facts['words']:,} words"
        return "out.md", facts
    if kind == "sheet":
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        wb = Workbook()
        wb.remove(wb.active)
        problems, rows = [], 0
        for name, raw in zip(names, texts):
            tab, why = _check_sheet(raw or '{"columns":["A"],"rows":[]}')
            if tab is None:
                tab = {"columns": ["A"], "rows": []}
            ws = wb.create_sheet(re.sub(r"[\[\]:*?/\\]", " ", name)[:31] or "Sheet")
            ws.append(tab["columns"])
            for c in ws[1]:
                c.font = Font(bold=True)
                c.fill = PatternFill("solid", fgColor="F1F0EC")
            for r in tab["rows"]:
                ws.append(r)
            ws.freeze_panes = "A2"
            for i, col in enumerate(tab["columns"]):
                ws.column_dimensions[col_name(i)].width = max(10, min(40, len(str(col)) + 4))
            rows += len(tab["rows"])
            problems += [f"{name} {p}" for p in sheet_preview(tab)["problems"]]
        wb.save(d / "out.xlsx")
        facts.update(rows=rows, problems=problems[:20])
        facts["line"] = (f"{len(names)} tab{'s' if len(names) != 1 else ''} · {rows:,} rows · "
                         + ("every formula worked out" if not problems else f"{len(problems)} formula{'s' if len(problems) != 1 else ''} to check"))
        return "out.xlsx", facts
    if kind == "prototype":
        body = "".join(f'<section class="hs-screen" id="{_screen_id(n)}" data-name="{_html.escape(n)}" hidden>{x}</section>'
                       for n, x in zip(names, texts))
        (d / "out.html").write_text(_page(m["title"], body, script=_PROTO_JS))
        facts["line"] = f"{len(names)} screen{'s' if len(names) != 1 else ''} · tap to play"
        return "out.html", facts
    if kind == "artboard":
        cells = []
        for n, x in zip(names, texts):
            doc = _page(n, x)
            cells.append(f'<div class="hs-cell"><div class="hs-frame"><iframe title="{_html.escape(n)}" sandbox="allow-scripts" '
                         f'srcdoc="{_html.escape(doc, quote=True)}"></iframe></div><div class="hs-name">{_html.escape(n)}</div></div>')
        (d / "out.html").write_text(_page(m["title"], '<div class="hs-grid">' + "".join(cells) + "</div>", _BOARD_CSS))
        facts["line"] = f"{len(names)} screen{'s' if len(names) != 1 else ''}"
        return "out.html", facts
    (d / "out.html").write_text(_page(m["title"], "".join(texts)))
    facts["line"] = "works on phone and computer" if len(names) <= 1 else f"{len(names)} sections"
    return "out.html", facts


# ---------------------------------------------------------------- the tool
def tool(tid: str, inp: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """(what the model reads back, the page event or None). Never raises: a bad call is answered in words."""
    act = str(inp.get("action") or "").strip().lower()
    try:
        with _LOCK:
            if act == "start":
                return _start(tid, inp)
            if act == "write":
                return _write(tid, inp), None
            if act == "finish":
                return _finish(tid, inp)
            if act == "list":
                rows = listing(tid)
                return ("Nothing made yet." if not rows else "\n".join(
                    f"{r['id']}: {r['kind_label']} '{r['title']}' v{r['version']} ({r['state']}) parts: "
                    + ", ".join(p["name"] for p in r["parts"]) for r in rows)), None
            return "action must be start, write, finish or list.", None
    except OSError as e:
        return f"make could not save that ({e.__class__.__name__}). Try again.", None


def _start(tid: str, inp: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    mid = _slug(str(inp.get("id") or ""), 48) if inp.get("id") else ""
    names = [re.sub(r"\s+", " ", str(p)).strip()[:80] for p in (inp.get("parts") or []) if str(p).strip()][:MAX_PARTS]
    m = _meta(tid, mid) if mid else None
    if mid and m is None:
        return f"There is no thing called {mid}. Use make list, or start without an id for a new one.", None
    if m is None:
        kind = _kind(inp.get("kind"))
        title = re.sub(r"\s+", " ", str(inp.get("title") or "")).strip()[:90]
        if not kind:
            return "Say which kind: doc, page, prototype, artboard or sheet.", None
        if not title:
            return "Give it a short title she will recognise.", None
        if len(_ids(tid)) >= MAX_THINGS:
            return f"This session already has {MAX_THINGS} things. Change one of them instead.", None
        if not names:
            names = [KINDS[kind][2].capitalize()] if kind != "doc" else ["Overview"]
        base, mid, n = _slug(title), _slug(title), 2
        while _meta(tid, mid) is not None:
            mid, n = f"{base}-{n}", n + 1
        ver = {"v": 1, "state": "making", "parts": _uniq(names), "done": [], "src": {}, "changed": [], "note": "",
               "at": _now()}
        m = {"id": mid, "kind": kind, "title": title, "versions": [ver], "created": _now()}
        _save(tid, m)
        n_ = len(ver["parts"])
        return (f"Started {mid} ({KINDS[kind][0].lower()}, version 1) with {n_} {KINDS[kind][2]}{'s' if n_ != 1 else ''}: "
                + ", ".join(ver["parts"]) + ". Now make write each one, then make finish."), {"k": "made", "id": mid, "v": 1}
    last = _latest(m)
    if last.get("state") == "making":                 # still being made: start again only renames / adds parts
        if names:
            last["parts"] = _uniq(last["parts"] + [n for n in names if n not in last["parts"]])[:MAX_PARTS]
            _save(tid, m)
        return f"{mid} version {last['v']} is still being made. Write its parts, then finish.", None
    if len(m["versions"]) >= MAX_VERSIONS:
        return f"{mid} already has {MAX_VERSIONS} versions. Make a new thing instead.", None
    base = _ready(m) or last
    parts = list(base["parts"])
    src = {str(i): str((base.get("src") or {}).get(str(i)) or base["v"]) for i in range(len(parts))}
    for n in names:
        if n not in parts and len(parts) < MAX_PARTS:
            parts.append(n)
    if inp.get("title"):
        m["title"] = re.sub(r"\s+", " ", str(inp["title"])).strip()[:90] or m["title"]
    ver = {"v": int(last["v"]) + 1, "state": "making", "parts": parts, "done": list(src), "src": src, "changed": [],
           "note": str(inp.get("note") or "").strip()[:200], "at": _now(), "from": base["v"]}
    m["versions"].append(ver)
    _save(tid, m)
    return (f"Started version {ver['v']} of {mid}, from version {base['v']}: every part is kept. Write only the parts "
            "that change (or new ones), then make finish."), {"k": "made", "id": mid, "v": ver["v"]}


def _uniq(names: list[str]) -> list[str]:
    out: list[str] = []
    for n in names:
        k, i = n, 2
        while k in out:
            k, i = f"{n} {i}", i + 1
        out.append(k)
    return out


def _write(tid: str, inp: dict[str, Any]) -> str:
    mid = _slug(str(inp.get("id") or ""), 48)
    m = _meta(tid, mid) if mid else None
    if m is None:
        return "Give the id that make start returned."
    ver = _latest(m)
    if ver.get("state") != "making":
        return f"{mid} is finished. make start with its id to begin a new version, then write."
    part = re.sub(r"\s+", " ", str(inp.get("part") or "")).strip()[:80]
    names = ver["parts"]
    if part not in names:
        low = {n.lower(): n for n in names}
        if part.lower() in low:
            part = low[part.lower()]
        elif part and len(names) < MAX_PARTS:
            names.append(part)
        else:
            return "Which part? One of: " + ", ".join(names)
    content = str(inp.get("content") or "")
    kind = m["kind"]
    if not content.strip():
        return "The content is empty."
    if len(content) > MAX_PART[kind]:
        return f"That part is too long ({len(content):,} characters, at most {MAX_PART[kind]:,}). Split it into more parts."
    if kind in ("page", "prototype", "artboard"):
        why = _check_html(content)
        if why:
            return f"Not saved: {why}."
    if kind == "sheet":
        tab, why = _check_sheet(content)
        if tab is None:
            return f"Not saved: {why}."
        content = json.dumps(tab, ensure_ascii=False)
    i = names.index(part)
    f = _part_file(tid, mid, int(ver["v"]), i)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content)
    ver.setdefault("src", {}).pop(str(i), None)
    if str(i) not in ver["done"]:
        ver["done"].append(str(i))
    if part not in ver["changed"]:
        ver["changed"].append(part)
    ver["now"] = part
    _save(tid, m)
    left = [n for j, n in enumerate(names) if str(j) not in ver["done"]]
    extra = ""
    if kind == "sheet":
        pv = sheet_preview(json.loads(content))
        if pv["problems"]:
            extra = " Formulas to check: " + "; ".join(pv["problems"][:5]) + "."
    return (f"Saved {part}." + extra + (" Still to write: " + ", ".join(left) + "." if left else " Every part is written: make finish."))


def _finish(tid: str, inp: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    mid = _slug(str(inp.get("id") or ""), 48)
    m = _meta(tid, mid) if mid else None
    if m is None:
        return "Give the id that make start returned.", None
    ver = _latest(m)
    if ver.get("state") != "making":
        return f"{mid} version {ver['v']} is already finished.", None
    left = [n for j, n in enumerate(ver["parts"]) if str(j) not in ver["done"]]
    if left:
        return "Not finished: still to write " + ", ".join(left) + ".", None
    if int(ver["v"]) > 1 and not ver["changed"]:
        m["versions"].pop()                              # nothing changed: no empty version in her list
        _save(tid, m)
        return f"Nothing changed, so {mid} stays at version {_latest(m)['v']}.", None
    name, facts = build(tid, m, ver)
    ver.update(state="ready", file=name, facts=facts, done_at=_now())
    ver.pop("now", None)
    _save(tid, m)
    said = f"{m['title']} version {ver['v']} is ready: {facts.get('line', '')}."
    if facts.get("problems"):
        said += " The preview could not work out: " + "; ".join(facts["problems"][:5]) + ". Fix them or say so to her."
    return said, None


# ---------------------------------------------------------------- what the phone reads
def _row(tid: str, m: dict[str, Any]) -> dict[str, Any]:
    ver = _latest(m)
    show = ver if ver.get("state") == "ready" else (_ready(m) or ver)
    names = ver["parts"]
    return {"id": m["id"], "kind": m["kind"], "kind_label": KINDS[m["kind"]][0], "title": m["title"],
            "version": int(ver["v"]), "ready_version": int(show["v"]) if show.get("state") == "ready" else 0,
            "state": ver.get("state", "making"),
            "parts": [{"name": n, "done": str(i) in ver.get("done", [])} for i, n in enumerate(names)],
            "now": ver.get("now", "") if ver.get("state") == "making" else "",
            "changed": ver.get("changed", []) if int(ver["v"]) > 1 else [],
            "note": ver.get("note", ""), "line": (show.get("facts") or {}).get("line", ""),
            "at": ver.get("at", ""), "done_at": ver.get("done_at", "")}


def listing(tid: str) -> list[dict[str, Any]]:
    out = []
    for mid in _ids(tid):
        m = _meta(tid, mid)
        if m and m.get("versions"):
            out.append(_row(tid, m))
    return out


def detail(tid: str, mid: str, v: int = 0, base_url: str = "") -> dict[str, Any]:
    m = _meta(tid, _slug(mid, 48))
    if m is None:
        raise ValueError("That thing was not found.")
    vers = m["versions"]
    ver = next((x for x in vers if int(x["v"]) == v), None) if v else (_ready(m) or _latest(m))
    if ver is None:
        raise ValueError("That version was not found.")
    out = {**_row(tid, m), "shown": int(ver["v"]), "shown_state": ver.get("state"),
           "versions": [{"v": int(x["v"]), "state": x.get("state"), "at": x.get("at", ""), "note": x.get("note", ""),
                         "changed": x.get("changed", []), "from": x.get("from", 0),
                         "line": (x.get("facts") or {}).get("line", "")} for x in reversed(vers)]}
    kind = m["kind"]
    texts = [_part_text(tid, m["id"], ver, i) for i in range(len(ver["parts"]))]
    if kind == "doc":
        body = "\n\n".join(x.strip() for x in texts if x.strip())
        out["doc"] = body if body.lstrip().startswith("# ") else f"# {m['title']}\n\n{body}"
    elif kind == "sheet":
        tabs = []
        for n, raw in zip(ver["parts"], texts):
            tab, _ = _check_sheet(raw) if raw else (None, "")
            tabs.append({"name": n, **(sheet_preview(tab) if tab else {"columns": [], "rows": [], "formulas": {}, "problems": []})})
        out["sheet"] = tabs
    if ver.get("state") == "ready" and ver.get("file"):
        out["url"] = base_url + link(tid, m["id"], int(ver["v"]), ver["file"])
        out["file_name"] = f"{_slug(m['title'])}.{KINDS[kind][1]}"
    elif kind in ("page", "prototype", "artboard") and texts:
        name, _ = build(tid, m, ver)                     # Peek: the draft so far, built now (parts not written yet are empty)
        out["url"] = base_url + link(tid, m["id"], int(ver["v"]), name)
    return out


def restore(tid: str, mid: str, v: int) -> dict[str, Any]:
    """Undo = her tap: a NEW version with version v's parts (nothing is ever deleted)."""
    with _LOCK:
        m = _meta(tid, _slug(mid, 48))
        if m is None:
            raise ValueError("That thing was not found.")
        old = next((x for x in m["versions"] if int(x["v"]) == int(v) and x.get("state") == "ready"), None)
        if old is None:
            raise ValueError("That version cannot be brought back.")
        if _latest(m).get("state") == "making":
            raise ValueError("Hoola is still making a version of this. Try again when it is done.")
        if len(m["versions"]) >= MAX_VERSIONS:
            raise ValueError("This thing already has the most versions it can keep.")
        src = {str(i): str((old.get("src") or {}).get(str(i)) or old["v"]) for i in range(len(old["parts"]))}
        ver = {"v": int(_latest(m)["v"]) + 1, "state": "making", "parts": list(old["parts"]), "done": list(src), "src": src,
               "changed": [], "note": f"Back to version {old['v']}", "at": _now(), "from": int(old["v"])}
        name, facts = build(tid, m, ver)
        ver.update(state="ready", file=name, facts=facts, done_at=_now())
        m["versions"].append(ver)
        _save(tid, m)
        return _row(tid, m)


# ---------------------------------------------------------------- signed links (the file itself, no sign-in)
def _sig(tid: str, mid: str, v: int, name: str, exp: int) -> str:
    st = _settings()
    key = (getattr(st, "secret_key", "") or getattr(st, "api_key", "") or "hoola-made").encode()
    return hmac.new(key, f"made|{tid}|{mid}|{v}|{name}|{exp}".encode(), hashlib.sha256).hexdigest()[:40]


def link(tid: str, mid: str, v: int, name: str, hours: int = LINK_HOURS) -> str:
    exp = int(time.time()) + hours * 3600
    return f"/api/devsahayak/made/{tid}/{mid}/{v}/{name}?exp={exp}&sig={_sig(tid, mid, v, name, exp)}"


def open_file(tid: str, mid: str, v: int, name: str, exp: int, sig: str) -> tuple[bytes, str, dict[str, str]] | None:
    if name not in ("out.md", "out.html", "out.xlsx") or exp < time.time():
        return None
    if not hmac.compare_digest(sig or "", _sig(tid, mid, v, name, exp)):
        return None
    f = _mdir(tid, mid) / f"v{int(v)}" / name
    if not f.is_file():
        return None
    m = _meta(tid, mid) or {}
    fname = f"{_slug(m.get('title', mid))}.{name.rsplit('.', 1)[1]}"
    head = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Cache-Control": "private, max-age=300"}
    if name.endswith(".html"):
        head["Content-Security-Policy"] = (
            "sandbox allow-scripts allow-popups; default-src 'none'; script-src 'unsafe-inline'; "
            "style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com data:; "
            "img-src data: https: blob:; media-src data: https:; frame-src 'self' data: blob:")
        return f.read_bytes(), "text/html; charset=utf-8", head
    head["Content-Disposition"] = f'attachment; filename="{fname}"'
    if name.endswith(".md"):
        return f.read_bytes(), "text/markdown; charset=utf-8", head
    return f.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", head
