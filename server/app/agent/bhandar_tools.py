"""v0.620.0 BHANDAR MANCH - the T2 local-core family, house-sized, backend-only (the hoola AI's own
local-data workbench; built as 0.618.0 - their HAMESHA JUDA took 0.618.0 and their KAAN W2 took 0.619.0
while BHANDAR sat built, REBASE PROTOCOL #11, re-versioned onto their e522b90b0 tip, both kept; owner:
"T2 Local Core -- START" - the T2 tier of download/HOOLA_MCP_FEED.json,
the zero-network / zero-login / zero-key local beds).

The T2 catalog rows this lane ports (all catalog-description-verified, all IDEA-ONLY, zero upstream
code, zero new pip, zero new keys - every capability below is Python stdlib):

- Aderali06/sqlite-mcp-server: "Safe, read-only SQLite MCP server with auto schema discovery, row
  limits, and structured AI error handling." -> the `sql` + `beds` actions.
- hannesrudolph/sqlite-explorer-fastmcp-mcp-server: "Safe, read-only access to explore and query
  SQLite databases, with query validation." -> the sql gate (validate BEFORE the wall).
- scoretracker4321/json-mcp-lite: "Serve any JSON file (catalogue, FAQ, price list) as read-only
  list, keyword search and get-by-id tools" -> the `json` action (read-only get/keys/validate).
- micl2e2/code-to-tree: "Convert source code into an AST, regardless of language." (house-sized to
  Python via the stdlib ast module) -> the `ast` action.
- rafim-dev/mcp-context-condenser: "AST-based code outliner, log compressor and context budget
  analyzer to reduce LLM token usage." -> the ast outline returns the skeleton, never the file.
- EdelmarSchneider/permark: "Markdown reader and editor that tells coding agents what you are
  reading" -> the `md` action (outline / links / stats: the structure first).
- davidan90/time-node-mcp: "Timezone-aware date and time operations: IANA timezones, timezone
  conversion and daylight saving time handling." and the mcp/servers `time` reference
  (get_current_time / convert_time over IANA zones, the local zone named so the model can default
  to it) -> the `time` action.

THE LANES (all read-only - bhandar never writes anywhere):

- `beds` - discovery: this tenant's own SQLite beds (data/scraping/<tenant>/*.db, the kgmemory
  graph, any workspace .db) with size / mtime / table counts, plus meta.root (the workspace root
  the md/json/ast lanes read from). Nothing is created by a discovery - an empty tenant is an
  honest empty list.
- `sql` - read-only SQL against ONE named bed (a name `beds` returned, e.g. "scraping/elements.db").
  The gate is THREE belts: (1) exactly one statement, its first word must be select / with /
  explain / pragma; (2) the write verbs and write pragmas are refused by name before anything
  runs; (3) the database is opened `mode=ro` - SQLite itself is the wall. Row caps and cell caps
  keep the envelope small; a truncated answer says so.
- `md` - markdown structure over workspace files: outline (the heading tree with line numbers),
  links (inline + reference, deduped), stats (words / fences / headings). The root is the law -
  same discipline as the sandarbh workspace.
- `json` - read-only JSON over workspace files: validate (with the parse position on failure),
  get (a dotted path a.b.0.c), keys (a typed outline of the structure, depth-capped).
- `ast` - the Python skeleton of a workspace .py file: classes (bases, methods, line spans),
  functions (arity, line spans), imports, top-level assigns - the outliner's law: the shape, not
  the source.
- `time` - IANA timezone now / convert with honest UTC offsets and DST flags; the house zone
  (Asia/Kolkata) is the default. zoneinfo is a local database - zero network.

Envelope (the v0.559 discipline shape, same as reach/speckit/sandarbh): {schema_version, ok, tool,
action, ..., meta{elapsed_ms, ...}, error{code, message, hint}} - the model branches on ok /
error.code, never on prose. Kill switch `bhandar_enabled` stops the whole lane with the honest
NEED_SETUP (everything here is a read, so off means off). All offline: no network, no model calls,
no keys, stdlib only (sqlite3, json, ast, zoneinfo, pathlib, re).
"""
from __future__ import annotations

import ast as pyast
import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..config import get_settings
from .tools import Ctx

SCHEMA_VERSION = 1

# ---------------------------------------------------------------- error codes (the discipline)
NEED_SETUP = "NEED_SETUP"      # the lane is turned off on this server
BAD_INPUT = "BAD_INPUT"        # the arguments were rejected (the message names what and why)
NOT_FOUND = "NOT_FOUND"        # bed / path / zone unknown for this tenant
TOO_BIG = "TOO_BIG"            # the payload would blow the envelope cap
SQL_ERROR = "SQL_ERROR"        # sqlite refused or failed the query (its own message, honestly)
PARSE_ERROR = "PARSE_ERROR"    # the file does not parse (markdown/json/python), position named

# ---------------------------------------------------------------- caps (generous, but the envelope stays small)
_MAX_ROWS = 200
_MAX_CELL = 400
_MAX_TABLES = 100
_MAX_BEDS = 100
_MAX_READ_BYTES = 200_000
_MAX_OUTLINE = 300
_MAX_LINKS = 200
_MAX_AST_NODES = 400
_MAX_JSON_DEPTH = 12
_MAX_JSON_OUT = 20_000
_TZ_CHARS = 60
_PATH_MAX = 400
_HOME_TZ = "Asia/Kolkata"      # the house zone - named in the tool description (the time reference law)

_BH_ACTIONS = ("beds", "sql", "md", "json", "ast", "time")

# the tenant's own bed dirs (relative to the server cwd, the same law as sandarbh's data/workspace)
_BED_DIRS = ("scraping", "kgmemory", "workspace")

# ---------------------------------------------------------------- the sql gate (three belts)
_SQL_HEADS = ("select", "with", "explain", "pragma")
_SQL_WRITE_VERBS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|vacuum|reindex|"
    r"rollback|commit|savepoint|release|begin)\b", re.I)
# note: `replace` is deliberately NOT scanned - SELECT replace(col, 'a', 'b') is a legal read;
# REPLACE INTO is a statement head the first-belt head check already refuses.
_PRAGMA_READ = {
    "table_list", "table_info", "table_xinfo", "index_list", "index_xinfo",
    "page_count", "page_size", "freelist_count", "user_version", "application_id",
    "integrity_check", "quick_check", "encoding", "database_list", "function_list",
    "module_list", "compile_options", "data_version", "foreign_key_check",
}
_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
_MD_REF = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s+(\S+)", re.M)


def _clean(value: Any, cap: int) -> str:
    return " ".join(str(value or "").split())[:cap]


def _ws_root(tenant_id: str) -> Path:
    """The workspace root (the md/json/ast lanes' allowed root). Never created by bhandar -
    a read-only lane does not make directories; an absent root is an honest empty."""
    return (Path("data") / "workspace" / tenant_id).resolve()


def _bh_envelope(action: str, error: tuple[str, str, str] | None = None, elapsed_ms: int = 0,
                 **fields) -> dict:
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "ok": error is None, "tool": "bhandar",
                           "action": action,
                           "error": (None if error is None else
                                     {"code": error[0], "message": error[1], "hint": error[2]})}
    out.update(fields)
    meta = dict(out.pop("meta", {}) or {})
    out["meta"] = {"elapsed_ms": max(0, int(elapsed_ms)), **meta}
    return out


def _bh_bad(action: str, msg: str, hint: str = "", code: str = BAD_INPUT) -> dict:
    return _bh_envelope(action, error=(code, msg, hint))


def _locked(action: str) -> dict | None:
    if not bool(getattr(get_settings(), "bhandar_enabled", True)):
        return _bh_envelope(action, error=(
            NEED_SETUP, "the bhandar local-data workbench is turned off on this server",
            "Ask the owner to set bhandar_enabled=true."))
    return None


# ================================================================ beds - discovery over the tenant's own stores

def _resolve_bed(tenant_id: str, bed: str) -> Path:
    """A bed name is exactly what `beds` returned: '<dir>/<file>.db' under the tenant's own
    data dirs. Anything else - absolute, dot-dot, a name beds never gave - is refused."""
    raw = str(bed or "").strip()
    if not raw or raw.startswith(("/", "\\")) or Path(raw).is_absolute() or len(raw) > _PATH_MAX:
        raise ValueError("name the bed exactly as the beds action returned it "
                         "(e.g. 'scraping/elements.db')")
    parts = [p for p in raw.split("/") if p not in ("", ".")]
    if len(parts) < 2 or parts[0] not in _BED_DIRS or ".." in parts or not parts[-1].endswith(".db"):
        raise ValueError("unknown bed name - call action=beds first and use one of its names")
    base = (Path("data") / parts[0] / tenant_id).resolve()
    p = (base / "/".join(parts[1:])).resolve()
    if not str(p).startswith(str(base) + "/"):
        raise ValueError("bed path escapes this tenant's own directories")
    return p


def _bed_scan(tenant_id: str) -> list[dict]:
    found: list[dict] = []
    for d in _BED_DIRS:
        base = (Path("data") / d / tenant_id).resolve()
        if not base.is_dir():
            continue
        it = base.rglob("*.db") if d == "workspace" else base.glob("*.db")
        for p in it:
            try:
                st = p.stat()
                rel = f"{d}/{p.relative_to(base).as_posix()}"
                tables = None
                if d != "workspace":  # house beds are always sqlite; workspace files may not be
                    tables = _quick_tables(p)
                found.append({"name": rel, "bytes": st.st_size,
                              "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                              **({"tables": tables} if tables is not None else {})})
            except OSError:
                continue
    found.sort(key=lambda b: b["modified"], reverse=True)
    return found[:_MAX_BEDS]


def _quick_tables(p: Path) -> int | None:
    try:
        con = sqlite3.connect(f"{p.as_uri()}?mode=ro", uri=True)
        try:
            n = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        finally:
            con.close()
        return int(n)
    except (sqlite3.Error, OSError):
        return None


def _do_beds(tenant_id: str) -> dict:
    beds = _bed_scan(tenant_id)
    return _bh_envelope("beds", beds=beds, count=len(beds),
                        meta={"root": str(_ws_root(tenant_id)),
                              "note": "workspace/*.db beds are listed without being opened; "
                                      "sql opens ANY named bed read-only (including those)"})


# ================================================================ sql - the read-only query door

def _one_statement(sql_text: str) -> str:
    text = str(sql_text or "").strip()
    if not text:
        raise ValueError("give a sql statement")
    if len(text) > 8_000:
        raise ValueError("sql too long (8k cap)")
    text = text.rstrip(";").strip()
    if ";" in text:
        raise ValueError("exactly ONE statement per call - remove the extra ';'")
    if not text:
        raise ValueError("give a sql statement")
    return text


def _sql_gate(text: str) -> str:
    """Belt 1 + 2: the head word and the write verbs. Belt 3 (mode=ro) is the real wall."""
    head = text.split(None, 1)[0].lower() if text.split() else ""
    if head == "explain":
        rest = text[len("explain"):].strip().lower()
        if rest.startswith("query plan"):
            rest = rest[len("query plan"):].strip()
        head = rest.split(None, 1)[0] if rest.split() else ""
        if head not in ("select", "with"):
            raise ValueError("EXPLAIN is allowed only on a SELECT / WITH statement")
        return text
    if head not in _SQL_HEADS:
        raise ValueError(f"read-only lane: the statement must start with "
                         f"SELECT / WITH / EXPLAIN / PRAGMA (got '{head}')")
    if head == "pragma":
        body = text[len("pragma"):].strip()
        name = re.split(r"[\s(=]", body, 1)[0].lower()
        if name not in _PRAGMA_READ:
            raise ValueError(f"PRAGMA '{name}' is not on the read list "
                             f"(allowed: schema/page/integrity reads)")
        if "=" in body:
            raise ValueError("PRAGMA assignment is a write - refused")
        return text
    m = _SQL_WRITE_VERBS.search(text)
    if m:
        raise ValueError(f"read-only lane: '{m.group(0).upper()}' is a write verb - refused")
    return text


def _do_sql(tenant_id: str, bed: str, sql_text: str) -> dict:
    try:
        p = _resolve_bed(tenant_id, bed)
    except ValueError as e:
        return _bh_bad("sql", str(e), "action=beds lists this tenant's own beds")
    if not p.is_file():
        return _bh_bad("sql", f"bed '{bed}' does not exist (yet)", "action=beds lists what exists",
                       code=NOT_FOUND)
    try:
        text = _one_statement(sql_text)
        _sql_gate(text)
    except ValueError as e:
        return _bh_bad("sql", str(e), "one read statement per call; beds lists the house stores")
    uri = f"{p.as_uri()}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True)
        try:
            cur = con.execute(text)
            rows = cur.fetchmany(_MAX_ROWS + 1)
            truncated = len(rows) > _MAX_ROWS
            cols = [d[0] for d in (cur.description or [])]
            rows = rows[:_MAX_ROWS]
        finally:
            con.close()
    except sqlite3.Error as e:
        return _bh_bad("sql", f"sqlite says: {e}", "check the table names with "
                       "sql='PRAGMA table_list'", code=SQL_ERROR)
    except OSError as e:
        return _bh_bad("sql", f"could not open the bed: {e}", "action=beds lists what exists",
                       code=SQL_ERROR)
    out_rows = [[(_clean(c, _MAX_CELL) if isinstance(c, str) else c) for c in r] for r in rows]
    return _bh_envelope("sql", bed=bed, columns=cols[:40], rows=out_rows,
                        count=len(out_rows),
                        meta={"read_only": True, "row_cap": _MAX_ROWS,
                              **({"truncated": True,
                                  "hint": f"more rows exist - add LIMIT / WHERE (cap {_MAX_ROWS}/call)"}
                                 if truncated else {})})


# ================================================================ md / json / ast - the workspace text beds

def _resolve_ws(tenant_id: str, rel: str) -> Path:
    """The sandarbh root law: relative, resolved, inside the tenant workspace."""
    raw = str(rel or "").strip()
    if not raw:
        raise ValueError("give a path relative to meta.root")
    if raw.startswith(("/", "\\")) or Path(raw).is_absolute() or len(raw) > _PATH_MAX:
        raise ValueError("absolute paths are refused - use a path relative to meta.root")
    root = _ws_root(tenant_id)
    candidate = (root / raw.strip("/")).resolve()
    if candidate != root and not str(candidate).startswith(str(root) + "/"):
        raise ValueError("path escapes the workspace root")
    return candidate


def _read_text(p: Path) -> str:
    if not p.is_file():
        raise FileNotFoundError(p.name)
    if p.stat().st_size > _MAX_READ_BYTES:
        raise OverflowError(f"file is larger than the {_MAX_READ_BYTES} byte cap")
    data = p.read_bytes()
    if b"\x00" in data[:8192]:
        raise UnicodeDecodeError("utf-8", data[:8], 0, 1, "binary file - refused, not garbled")
    return data.decode("utf-8", errors="replace")


def _do_md(tenant_id: str, rel: str, op: str) -> dict:
    try:
        p = _resolve_ws(tenant_id, rel)
        text = _read_text(p)
    except FileNotFoundError:
        return _bh_bad("md", f"'{rel}' does not exist in the workspace",
                       "the workspace tool's action=list shows what exists", code=NOT_FOUND)
    except OverflowError as e:
        return _bh_bad("md", str(e), "read the file in pieces with the workspace tool", code=TOO_BIG)
    except (ValueError, UnicodeDecodeError) as e:
        return _bh_bad("md", str(e), "the md lane reads text files inside the workspace")
    op = (op or "outline").strip().lower()
    if op == "outline":
        items = [{"level": len(m.group(1)), "text": m.group(2)[:200], "line": i + 1}
                 for i, line in enumerate(text.splitlines())
                 for m in [_MD_HEADING.match(line)] if m]
        return _bh_envelope("md", op=op, path=rel, outline=items[:_MAX_OUTLINE],
                            count=min(len(items), _MAX_OUTLINE),
                            meta={"root": str(_ws_root(tenant_id))})
    if op == "links":
        seen, links = set(), []
        for label, url in _MD_LINK.findall(text):
            if url in seen:
                continue
            seen.add(url)
            links.append({"label": label.strip()[:120], "url": url[:300]})
        for label, url in _MD_REF.findall(text):
            if url in seen:
                continue
            seen.add(url)
            links.append({"label": label.strip()[:120], "url": url[:300], "reference": True})
        return _bh_envelope("md", op=op, path=rel, links=links[:_MAX_LINKS],
                            count=min(len(links), _MAX_LINKS),
                            meta={"root": str(_ws_root(tenant_id))})
    if op == "stats":
        lines = text.splitlines()
        fences = sum(1 for l in lines if l.strip().startswith("```"))
        headings = sum(1 for l in lines if _MD_HEADING.match(l))
        return _bh_envelope("md", op=op, path=rel,
                            stats={"chars": len(text), "words": len(text.split()),
                                   "lines": len(lines), "headings": headings,
                                   "code_fences": fences // 2,
                                   "links": len(_MD_LINK.findall(text))},
                            meta={"root": str(_ws_root(tenant_id))})
    return _bh_bad("md", f"unknown op '{op}'; valid: outline | links | stats")


def _json_walk(node: Any, depth: int) -> list[dict]:
    out: list[dict] = []
    if depth > _MAX_JSON_DEPTH:
        return out
    if isinstance(node, dict):
        for k, v in list(node.items())[:50]:
            kind = type(v).__name__
            size = len(v) if isinstance(v, (list, dict, str)) else None
            out.append({"path": k, "type": kind, **({"size": size} if size is not None else {})})
            out.extend(_json_walk(v, depth + 1) if isinstance(v, (list, dict)) else [])
    elif isinstance(node, list) and node:
        out.append({"path": "[0]", "type": type(node[0]).__name__, "note": f"list of {len(node)}"})
        out.extend(_json_walk(node[0], depth + 1))
    return out


def _do_json(tenant_id: str, rel: str, op: str, dotted: str) -> dict:
    try:
        p = _resolve_ws(tenant_id, rel)
        text = _read_text(p)
    except FileNotFoundError:
        return _bh_bad("json", f"'{rel}' does not exist in the workspace",
                       "the workspace tool's action=list shows what exists", code=NOT_FOUND)
    except OverflowError as e:
        return _bh_bad("json", str(e), "keep bed files under the cap", code=TOO_BIG)
    except (ValueError, UnicodeDecodeError) as e:
        return _bh_bad("json", str(e), "the json lane reads text files inside the workspace")
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        return _bh_bad("json", f"JSON does not parse: line {e.lineno}, column {e.colno} ({e.msg})",
                       "fix the file with the workspace tool's action=edit", code=PARSE_ERROR)
    op = (op or "keys").strip().lower()
    if op == "validate":
        return _bh_envelope("json", op=op, path=rel, valid=True,
                            top_type=type(doc).__name__,
                            **({"top_size": len(doc)} if isinstance(doc, (list, dict)) else {}),
                            meta={"root": str(_ws_root(tenant_id))})
    if op == "keys":
        items = _json_walk(doc, 0)[:_MAX_AST_NODES]
        return _bh_envelope("json", op=op, path=rel, structure=items, count=len(items),
                            meta={"root": str(_ws_root(tenant_id)),
                                  "depth_cap": _MAX_JSON_DEPTH})
    if op == "get":
        cur = doc
        hops = [h for h in str(dotted or "").split(".") if h != ""]
        if not hops:
            return _bh_bad("json", "give the dotted path to fetch (e.g. 'items.0.name')")
        for i, h in enumerate(hops):
            if isinstance(cur, dict) and h in cur:
                cur = cur[h]
            elif isinstance(cur, list) and h.isdigit() and int(h) < len(cur):
                cur = cur[int(h)]
            else:
                return _bh_bad("json", f"path stops at '{h}' in '{dotted}' (hop {i + 1} of {len(hops)})",
                               "action=keys shows the structure", code=NOT_FOUND)
        try:
            out = json.dumps(cur, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            return _bh_bad("json", f"result is not serializable: {e}")
        if len(out) > _MAX_JSON_OUT:
            return _bh_bad("json", f"result is {len(out)} bytes, over the {_MAX_JSON_OUT} cap",
                           "drill deeper into the structure with action=keys", code=TOO_BIG)
        return _bh_envelope("json", op=op, path=rel, value=cur, bytes=len(out),
                            meta={"root": str(_ws_root(tenant_id))})
    return _bh_bad("json", f"unknown op '{op}'; valid: validate | keys | get")


def _py_outline(source: str) -> dict:
    tree = pyast.parse(source)
    classes, functions, imports, assigns = [], [], [], 0
    for node in pyast.walk(tree):
        if len(classes) >= _MAX_AST_NODES:
            break
        if isinstance(node, pyast.ClassDef):
            classes.append({"name": node.name, "line": node.lineno, "end_line": node.end_lineno,
                            "bases": [pyast.unparse(b)[:80] for b in node.bases][:6],
                            "methods": [n.name for n in node.body
                                        if isinstance(n, (pyast.FunctionDef, pyast.AsyncFunctionDef))][:40]})
    # the skeleton's law: functions/imports/assigns are TOP-LEVEL only - a class's methods ride
    # the class (the outliner returns the shape, not a flat soup of names)
    for node in tree.body:
        if isinstance(node, (pyast.FunctionDef, pyast.AsyncFunctionDef)):
            functions.append({"name": node.name, "line": node.lineno, "end_line": node.end_lineno,
                              "args": len(node.args.args) + len(node.args.kwonlyargs)
                                      + (1 if node.args.vararg else 0)
                                      + (1 if node.args.kwarg else 0),
                              "async": isinstance(node, pyast.AsyncFunctionDef)})
        elif isinstance(node, (pyast.Import, pyast.ImportFrom)):
            names = [a.name for a in node.names][:8]
            imports.append({"module": getattr(node, "module", None) or names[0].split(".")[0],
                            "names": names, "line": node.lineno})
        elif isinstance(node, pyast.Assign):
            assigns += 1
    return {"classes": classes, "functions": functions, "imports": imports,
            "top_level_assigns": assigns}


def _do_ast(tenant_id: str, rel: str) -> dict:
    raw = str(rel or "").strip()
    if not raw.endswith(".py"):
        return _bh_bad("ast", "the ast lane reads Python files only (a *.py path)",
                       "name a .py file inside the workspace")
    try:
        p = _resolve_ws(tenant_id, raw)
        text = _read_text(p)
    except FileNotFoundError:
        return _bh_bad("ast", f"'{raw}' does not exist in the workspace",
                       "the workspace tool's action=list shows what exists", code=NOT_FOUND)
    except OverflowError as e:
        return _bh_bad("ast", str(e), "outline smaller files", code=TOO_BIG)
    except (ValueError, UnicodeDecodeError) as e:
        return _bh_bad("ast", str(e), "the ast lane reads .py files inside the workspace")
    try:
        shape = _py_outline(text)
    except SyntaxError as e:
        return _bh_bad("ast", f"Python does not parse: line {e.lineno} ({e.msg})",
                       "fix the file with the workspace tool's action=edit", code=PARSE_ERROR)
    return _bh_envelope("ast", path=raw, **shape,
                        meta={"root": str(_ws_root(tenant_id)),
                              "node_cap": _MAX_AST_NODES})


# ================================================================ time - the IANA now / convert door

def _zone(name: str | None) -> ZoneInfo:
    tz = _clean(name or _HOME_TZ, _TZ_CHARS)
    if not tz or "/" not in tz and tz not in ("UTC",):
        raise ZoneInfoNotFoundError(f"'{tz}' is not an IANA zone name")
    return ZoneInfo(tz)


def _stamp(dt: datetime) -> dict:
    off = dt.utcoffset()
    total = int(off.total_seconds()) if off is not None else 0
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return {"iso": dt.isoformat(timespec="seconds"), "tz": str(dt.tzinfo),
            "utc_offset": f"{sign}{total // 3600:02d}:{total % 3600 // 60:02d}",
            "is_dst": bool(dt.dst())}


def _do_time(op: str, tz: str | None, to_tz: str | None, at: str | None) -> dict:
    op = (op or "now").strip().lower()
    try:
        if op == "now":
            zone = _zone(tz)
            return _bh_envelope("time", op=op, **_stamp(datetime.now(zone)),
                                meta={"database": "zoneinfo (local IANA database - zero network)",
                                      "home_tz": _HOME_TZ})
        if op == "convert":
            zone = _zone(tz)
            target = _zone(to_tz)
            if at:
                try:
                    moment = datetime.fromisoformat(str(at).strip())
                except ValueError:
                    return _bh_bad("time", f"could not read the moment '{at}'",
                                   "give an ISO moment, e.g. 2026-11-06T14:00:00")
                moment = moment.replace(tzinfo=zone) if moment.tzinfo is None else moment.astimezone(zone)
            else:
                moment = datetime.now(zone)
            other = moment.astimezone(target)
            return _bh_envelope("time", op=op, from_zone=_stamp(moment), to_zone=_stamp(other),
                                meta={"database": "zoneinfo (local IANA database - zero network)",
                                      "home_tz": _HOME_TZ})
    except ZoneInfoNotFoundError as e:
        return _bh_bad("time", str(e), "use IANA names: Asia/Kolkata, America/New_York, UTC, ...",
                       code=NOT_FOUND)
    return _bh_bad("time", f"unknown op '{op}'; valid: now | convert")


# ================================================================ the ONE tool

async def bhandar(ctx: Ctx, action: str = "beds", *, bed: str | None = None, sql: str | None = None,
                  path: str | None = None, op: str | None = None, dotted: str | None = None,
                  tz: str | None = None, to_tz: str | None = None, at: str | None = None, **_) -> dict:
    """The tenant's local-data workbench. Never raises; every answer is one envelope."""
    started = time.monotonic()
    action = str(action or "").strip().lower()
    if action not in _BH_ACTIONS:
        return _bh_bad(action or "", f"unknown action '{action}'; valid: {', '.join(_BH_ACTIONS)}")
    if (lock := _locked(action)) is not None:
        return lock
    if action == "beds":
        out = _do_beds(ctx.tenant_id)
    elif action == "sql":
        out = _do_sql(ctx.tenant_id, bed or "", sql or "")
    elif action == "md":
        out = _do_md(ctx.tenant_id, path or "", op or "outline")
    elif action == "json":
        out = _do_json(ctx.tenant_id, path or "", op or "keys", dotted or "")
    elif action == "ast":
        out = _do_ast(ctx.tenant_id, path or "")
    else:
        out = _do_time(op or "now", tz, to_tz, at)
    out["meta"]["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return out


# ---------------------------------------------------------------- the tool spec the model sees
BHANDAR_TOOLS = [
    {"name": "bhandar", "description": (
        "BHANDAR MANCH (v0.618): the agent's own local-data workbench over THIS tenant's beds - "
        "read-only, zero network, the T2 local-core idea. Actions: beds (list the tenant's own "
        "SQLite stores: scraping / kgmemory / workspace, with sizes and table counts) | sql (ONE "
        "read statement - SELECT / WITH / EXPLAIN / read PRAGMA - against a named bed; writes and "
        "write-pragmas refused, the database opens mode=ro, rows capped) | md (markdown structure "
        "of a workspace file: outline | links | stats) | json (validate | keys | get with a dotted "
        "path) | ast (the Python skeleton of a workspace .py: classes, functions, imports - shape, "
        "not source) | time (IANA now / convert with honest UTC offsets and DST flags; home zone "
        "Asia/Kolkata). md/json/ast paths are relative to meta.root (the tenant workspace) and "
        "never leave it. One envelope {ok, action, error:{code, message, hint}}."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": list(_BH_ACTIONS),
                    "description": "beds | sql | md | json | ast | time"},
         "bed": {"type": "string", "description": "sql: the bed name exactly as beds returned it (e.g. 'scraping/elements.db')"},
         "sql": {"type": "string", "description": "sql: ONE read statement (SELECT / WITH / EXPLAIN / read PRAGMA)"},
         "path": {"type": "string", "description": "md/json/ast: path relative to meta.root (the tenant workspace)"},
         "op": {"type": "string", "description": "md: outline | links | stats; json: validate | keys | get; time: now | convert"},
         "dotted": {"type": "string", "description": "json get: the dotted path (e.g. 'items.0.name')"},
         "tz": {"type": "string", "description": "time: IANA zone (default Asia/Kolkata)"},
         "to_tz": {"type": "string", "description": "time convert: the target IANA zone"},
         "at": {"type": "string", "description": "time convert: an ISO moment (default = now)"}}}},
]

BHANDAR_LABELS = {"bhandar": "Bhandar: the agent's local-data workbench"}
BHANDAR_HANDLERS = {"bhandar": bhandar}
