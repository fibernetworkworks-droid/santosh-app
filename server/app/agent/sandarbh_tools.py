"""v0.589.0 SANDARBH MANCH - the T1 reference family, house-sized, backend-only (the hoola AI's own lanes; built as 0.586.0, re-versioned onto their v0.588.0 base - COLLISION #8, REBASE PROTOCOL, both kept).

Owner: "T1 Reference -- deploye it for hoola --- only in backend for hoola ai" - the T1 item of
download/HOOLA_MCP_FEED.json: modelcontextprotocol/servers (MIT), the reference MCP family, whose
catalog rows are the filesystem role ("Direct local file system access") and the knowledge-graph
memory role ("Knowledge graph-based persistent memory for maintaining context"). ZERO reference
code exists here (the house port law keeps even MIT code out; the reference servers are TypeScript
MCP processes HOOLA does not run) - what is ported is the IDEA, rebuilt as TWO ONE-tool+actions
lanes the hoola AI runs from the backend registry. Backend only: no console page, no phone screen,
no route - the agent tool surface is the whole product.

TWO tools:

1. `workspace` - the reference FILESYSTEM role. One confined directory per tenant
   (data/workspace/<tenant>/) the agent may list, read, write, edit, walk, search and inspect.
   The reference's discipline survives the port:
   - THE ROOT IS THE LAW: every path is resolved and must land inside the tenant root - the
     envelope's meta.root names the one allowed directory on EVERY answer (the reference's
     list_allowed_directories idea made ambient). Absolute paths, `..`, and symlink escapes are
     refused before anything is touched.
   - EDIT IS EXACT: old_string must appear EXACTLY once unless replace_all is asked (the reference
     edit_file law) - a fuzzy or ambiguous edit is refused, never guessed.
   - READS ARE HONEST: a byte cap (the envelope stays small), and a binary file is refused with a
     note, not dumped as mojibake.
   - Writes create parents; the tree walk is depth- and node-capped; search matches NAMES
     (reference search_files behaviour, not a content index).

2. `kgmemory` - the reference KNOWLEDGE-GRAPH MEMORY role. Entities, typed relations and text
   observations in per-tenant SQLite (data/kgmemory/<tenant>/kg.db), the reference tool family
   (create_entities / create_relations / add_observations / delete_* / read_graph / search_nodes /
   open_nodes) collapsed into actions create | relate | observe | forget | read | search | open.
   The house law the reference taught elsewhere applies here too:
   - NO GHOST REFS: a relation or observation is refused when its entity does not exist (the
     speckit traceability law at memory scale) - the hint names action=create.
   - FORGET IS EXACT AND CASCADE-HONEST: deleting an entity takes its observations and its
     touching relations with it, and says so in the counts.
   - THE ENVELOPE STAYS SMALL: read truncates past a graph cap with a hint to search/open instead;
     search/open return matched neighbourhoods, never the whole store.

Envelope (the v0.559 discipline shape, same as reach/speckit): {schema_version, ok, tool, action,
..., meta{elapsed_ms, ...}, error{code, message, hint}} - the model branches on ok / error.code,
never on prose. Kill switches `workspace_enabled` / `kgmemory_enabled` stop the WRITES; the
read-only introspections stay answerable (the reach honest-off pattern). All offline: no network,
no model calls, no keys, stdlib only.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..config import get_settings
from .tools import Ctx

SCHEMA_VERSION = 1

_IST = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------------- error codes (the discipline)
NEED_SETUP = "NEED_SETUP"      # the lane is turned off on this server
BAD_INPUT = "BAD_INPUT"        # the arguments were rejected (the message names what and why)
NOT_FOUND = "NOT_FOUND"        # path / entity unknown for this tenant
CONFLICT = "CONFLICT"          # the write would break an exactness / capacity law
TOO_BIG = "TOO_BIG"            # the payload would blow the envelope cap

# ---------------------------------------------------------------- caps (generous, but the envelope stays small)
_ROOT_DIR = "workspace"        # data/workspace/<tenant>/
_KG_DIR = "kgmemory"           # data/kgmemory/<tenant>/kg.db
_MAX_READ_BYTES = 200_000
_MAX_WRITE_BYTES = 200_000
_MAX_LIST = 500
_MAX_TREE_DEPTH = 6
_MAX_TREE_NODES = 400
_MAX_SEARCH = 200
_MAX_ENTITIES_CALL = 50
_MAX_RELATIONS_CALL = 50
_MAX_OBS_CALL = 200
_MAX_ENTITIES_TOTAL = 5_000
_MAX_RELATIONS_TOTAL = 10_000
_MAX_OBS_TEXT = 500
_MAX_READ_NODES = 300
_MAX_MATCH_NODES = 50
_NAME_CHARS = 120
_TYPE_CHARS = 60
_KIND_CHARS = 60
_OBS_CHARS = _MAX_OBS_TEXT
_PATH_MAX = 400

_WS_ACTIONS = ("list", "read", "write", "edit", "tree", "search", "info")
_KG_ACTIONS = ("create", "relate", "observe", "forget", "read", "search", "open")


def _clean(value: Any, cap: int) -> str:
    return " ".join(str(value or "").split())[:cap]


# ================================================================ workspace - the filesystem role

def _ws_root(tenant_id: str) -> Path:
    root = (Path("data") / _ROOT_DIR / tenant_id).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _ws_resolve(root: Path, rel: str | None) -> Path:
    """Resolve `rel` under the root; raise ValueError when it leaves the sandbox."""
    raw = (rel or "").strip()
    if raw and (raw.startswith(("/", "\\")) or Path(raw).is_absolute()):
        raise ValueError("absolute paths are refused - use a path relative to meta.root")
    rel = raw.strip("/")
    if len(rel) > _PATH_MAX:
        raise ValueError("path too long")
    candidate = (root / rel).resolve() if rel else root
    if candidate != root and not str(candidate).startswith(str(root) + "/"):
        raise ValueError("path escapes the workspace root")
    return candidate


def _ws_envelope(action: str, path: str | None = None, error: tuple[str, str, str] | None = None,
                 elapsed_ms: int = 0, **fields) -> dict:
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "ok": error is None, "tool": "workspace",
                           "action": action, "path": path,
                           "error": (None if error is None else
                                     {"code": error[0], "message": error[1], "hint": error[2]})}
    out.update(fields)
    meta = dict(out.pop("meta", {}) or {})
    out["meta"] = {"elapsed_ms": max(0, int(elapsed_ms)), **meta}
    return out


def _ws_bad(action: str, msg: str, hint: str = "", path: str | None = None) -> dict:
    return _ws_envelope(action, path=path, error=(BAD_INPUT, msg, hint))


def _rel_of(root: Path, p: Path) -> str:
    return str(p.relative_to(root)) if p != root else ""


def _ws_rides_link(root: Path, rel: str) -> bool:
    """True when the UNRESOLVED path (or a parent of it) is a symlink - writes never ride links."""
    cur = root
    for part in Path(rel).parts:
        cur = cur / part
        if cur.is_symlink():
            return True
    return False


def _ws_is_binary(p: Path) -> bool:
    try:
        with open(p, "rb") as fh:
            return b"\x00" in fh.read(8192)
    except OSError:
        return True


def _ws_write_locked() -> bool:
    return not bool(getattr(get_settings(), "workspace_enabled", True))


def _do_ws_list(root: Path, rel: str | None) -> dict:
    try:
        target = _ws_resolve(root, rel)
    except ValueError as e:
        return _ws_bad("list", str(e), "paths stay inside meta.root - use a relative path.", rel)
    if not target.exists():
        return _ws_envelope("list", path=rel, error=(NOT_FOUND, f"no such directory: {rel or '(root)'}",
                                                     "action=tree shows what exists."))
    if not target.is_dir():
        return _ws_bad("list", f"not a directory: {rel}", "action=info describes a file.", rel)
    entries = []
    try:
        for child in sorted(target.iterdir(), key=lambda c: (c.is_file(), c.name.lower())):
            if len(entries) >= _MAX_LIST:
                break
            if child.is_symlink():
                entries.append({"name": child.name, "type": "symlink", "size": 0})
                continue
            entries.append({"name": child.name, "type": "dir" if child.is_dir() else "file",
                            "size": child.stat().st_size if child.is_file() else 0})
    except OSError as e:
        return _ws_bad("list", f"directory not readable: {e}")
    return _ws_envelope("list", path=rel, entries=entries,
                        meta={"count": len(entries), "truncated": len(entries) >= _MAX_LIST})


def _do_ws_read(root: Path, rel: str) -> dict:
    if not rel:
        return _ws_bad("read", "read needs a path", "action=list shows what exists.")
    try:
        target = _ws_resolve(root, rel)
    except ValueError as e:
        return _ws_bad("read", str(e), "paths stay inside meta.root - use a relative path.", rel)
    if not target.exists():
        return _ws_envelope("read", path=rel, error=(NOT_FOUND, f"no such file: {rel}",
                                                     "action=search finds files by name."))
    if target.is_dir():
        return _ws_bad("read", f"that is a directory: {rel}", "action=list reads a directory.", rel)
    if target.is_symlink() or _ws_is_binary(target):
        return _ws_bad("read", f"not a text file: {rel}",
                       "this lane reads text only; binary content is refused, not garbled.", rel)
    try:
        size = target.stat().st_size
        with open(target, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read(_MAX_READ_BYTES + 1)
    except OSError as e:
        return _ws_bad("read", f"file not readable: {e}", "", rel)
    truncated = len(content) > _MAX_READ_BYTES
    if truncated:
        content = content[:_MAX_READ_BYTES]
    return _ws_envelope("read", path=rel, content=content,
                        meta={"bytes": size, "truncated": truncated, "cap": _MAX_READ_BYTES})


def _do_ws_write(root: Path, rel: str, content: Any) -> dict:
    if not rel:
        return _ws_bad("write", "write needs a path", "a relative path inside meta.root.")
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    if len(text.encode("utf-8")) > _MAX_WRITE_BYTES:
        return _ws_envelope("write", path=rel, error=(TOO_BIG, f"content over the {_MAX_WRITE_BYTES}-byte cap",
                                                      "split the write or shrink the content."))
    try:
        target = _ws_resolve(root, rel)
    except ValueError as e:
        return _ws_bad("write", str(e), "paths stay inside meta.root - use a relative path.", rel)
    if _ws_rides_link(root, rel):
        return _ws_envelope("write", path=rel, error=(CONFLICT, "that path is a symlink",
                                                      "write the real file, not through a link."))
    if _ws_write_locked():
        return _ws_envelope("write", path=rel, error=(NEED_SETUP, "workspace writes are turned off on this server",
                                                      "Tell her plainly; nothing to fix from the chat."))
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError as e:
        return _ws_bad("write", f"write failed: {e}", "", rel)
    return _ws_envelope("write", path=rel, meta={"bytes": len(text.encode("utf-8")),
                                                 "created": True},
                        say=f"Written to {rel}")


def _do_ws_edit(root: Path, rel: str, old_string: str, new_string: str, replace_all: bool) -> dict:
    if not rel or not old_string:
        return _ws_bad("edit", "edit needs path + old_string",
                       "the exact string to replace; replace_all=true for every occurrence.")
    if _ws_write_locked():
        return _ws_envelope("edit", path=rel, error=(NEED_SETUP, "workspace writes are turned off on this server",
                                                     "Tell her plainly; nothing to fix from the chat."))
    try:
        target = _ws_resolve(root, rel)
    except ValueError as e:
        return _ws_bad("edit", str(e), "paths stay inside meta.root - use a relative path.", rel)
    if _ws_rides_link(root, rel):
        return _ws_envelope("edit", path=rel, error=(CONFLICT, "that path is a symlink",
                                                     "edit the real file, not through a link."))
    if not target.exists() or target.is_dir():
        return _ws_envelope("edit", path=rel, error=(NOT_FOUND, f"no such file: {rel}",
                                                     "action=read first shows the exact text."))
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return _ws_bad("edit", f"file not readable: {e}", "", rel)
    count = text.count(old_string)
    if count == 0:
        return _ws_envelope("edit", path=rel, error=(NOT_FOUND, "old_string not found in this file",
                                                     "action=read gives the exact text - edit is exact, never fuzzy."))
    if count > 1 and not replace_all:
        return _ws_envelope("edit", path=rel, error=(CONFLICT, f"old_string appears {count} times",
                                                     "make it unique or pass replace_all=true."))
    if len(text) + (len(new_string) - len(old_string)) * count > _MAX_WRITE_BYTES:
        return _ws_envelope("edit", path=rel, error=(TOO_BIG, "the edited file would cross the size cap",
                                                     "split the file or shrink the edit."))
    updated = text.replace(old_string, new_string) if replace_all else text.replace(old_string, new_string, 1)
    try:
        target.write_text(updated, encoding="utf-8")
    except OSError as e:
        return _ws_bad("edit", f"write failed: {e}", "", rel)
    return _ws_envelope("edit", path=rel, meta={"replacements": count if replace_all else 1,
                                                "bytes": len(updated.encode("utf-8"))},
                        say=f"Edited {rel}")


def _do_ws_tree(root: Path, rel: str | None) -> dict:
    try:
        start = _ws_resolve(root, rel)
    except ValueError as e:
        return _ws_bad("tree", str(e), "paths stay inside meta.root - use a relative path.", rel)
    if not start.exists() or not start.is_dir():
        return _ws_envelope("tree", path=rel, error=(NOT_FOUND, f"no such directory: {rel or '(root)'}",
                                                     "action=list reads one directory."))
    nodes: list[dict] = []

    def walk(dirp: Path, prefix: str, depth: int) -> None:
        if depth > _MAX_TREE_DEPTH or len(nodes) >= _MAX_TREE_NODES:
            return
        try:
            children = sorted(dirp.iterdir(), key=lambda c: (c.is_file(), c.name.lower()))
        except OSError:
            return
        for child in children:
            if len(nodes) >= _MAX_TREE_NODES:
                return
            if child.is_symlink():
                continue
            r = f"{prefix}{child.name}" if prefix else child.name
            if child.is_dir():
                nodes.append({"path": r, "type": "dir"})
                walk(child, f"{r}/", depth + 1)
            else:
                nodes.append({"path": r, "type": "file", "size": child.stat().st_size})

    walk(start, "", 1)
    return _ws_envelope("tree", path=rel, nodes=nodes,
                        meta={"count": len(nodes), "truncated": len(nodes) >= _MAX_TREE_NODES,
                              "max_depth": _MAX_TREE_DEPTH})


def _do_ws_search(root: Path, pattern: str) -> dict:
    needle = (pattern or "").strip().lower()
    if not needle:
        return _ws_bad("search", "search needs a pattern", "a name fragment, matched case-insensitively.")
    hits: list[dict] = []
    for p in sorted(root.rglob("*")):
        if len(hits) >= _MAX_SEARCH:
            break
        if p.is_symlink():
            continue
        r = _rel_of(root, p)
        if needle in r.lower():
            hits.append({"path": r, "type": "dir" if p.is_dir() else "file",
                         "size": p.stat().st_size if p.is_file() else 0})
    return _ws_envelope("search", pattern=needle, matches=hits,
                        meta={"count": len(hits), "truncated": len(hits) >= _MAX_SEARCH})


def _do_ws_info(root: Path, rel: str) -> dict:
    if not rel:
        return _ws_envelope("info", path="", info={"type": "dir", "path": "(root)",
                                                   "note": "the tenant workspace root"},
                            meta={"root": True})
    try:
        target = _ws_resolve(root, rel)
    except ValueError as e:
        return _ws_bad("info", str(e), "paths stay inside meta.root - use a relative path.", rel)
    if not target.exists():
        return _ws_envelope("info", path=rel, error=(NOT_FOUND, f"no such path: {rel}",
                                                     "action=search finds files by name."))
    st = target.stat()
    info = {"type": "dir" if target.is_dir() else ("symlink" if target.is_symlink() else "file"),
            "size": st.st_size if target.is_file() else 0,
            "modified_at": datetime.fromtimestamp(st.st_mtime, _IST).strftime("%Y-%m-%d %H:%M:%S")}
    return _ws_envelope("info", path=rel, info=info)


async def workspace(ctx: Ctx, action: str = "list", path: str | None = None, *,
                    content: Any = None, old_string: str | None = None, new_string: str | None = None,
                    replace_all: bool = False, pattern: str | None = None, **_) -> dict:
    """The tenant workspace: one confined directory, every answer one envelope. Never raises."""
    started = time.monotonic()
    action = str(action or "").strip().lower()
    if action not in _WS_ACTIONS:
        return _ws_bad(action or "", f"unknown action '{action}'; valid: {', '.join(_WS_ACTIONS)}")
    root = _ws_root(ctx.tenant_id)
    if action == "list":
        out = _do_ws_list(root, path)
    elif action == "read":
        out = _do_ws_read(root, path or "")
    elif action == "write":
        out = _do_ws_write(root, path or "", content)
    elif action == "edit":
        out = _do_ws_edit(root, path or "", old_string or "", new_string or "", bool(replace_all))
    elif action == "tree":
        out = _do_ws_tree(root, path)
    elif action == "search":
        out = _do_ws_search(root, pattern or "")
    else:
        out = _do_ws_info(root, path or "")
    # the reference's list_allowed_directories idea, made ambient: every answer names the one root
    out["meta"]["root"] = f"data/{_ROOT_DIR}/{ctx.tenant_id}"
    out["meta"]["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return out


# ================================================================ kgmemory - the knowledge-graph memory role

def _kg_path(tenant_id: str) -> Path:
    return Path("data") / _KG_DIR / tenant_id / "kg.db"


def _kg_con(tenant_id: str) -> sqlite3.Connection:
    _kg_path(tenant_id).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_kg_path(tenant_id)), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS entities (name TEXT PRIMARY KEY, type TEXT DEFAULT '', "
                "created_at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "entity TEXT, text TEXT, created_at REAL, UNIQUE(entity, text))")
    con.execute("CREATE TABLE IF NOT EXISTS relations (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "src TEXT, dst TEXT, kind TEXT, created_at REAL, UNIQUE(src, dst, kind))")
    return con


def _kg_envelope(action: str, error: tuple[str, str, str] | None = None, elapsed_ms: int = 0,
                 **fields) -> dict:
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "ok": error is None, "tool": "kgmemory",
                           "action": action,
                           "error": (None if error is None else
                                     {"code": error[0], "message": error[1], "hint": error[2]})}
    out.update(fields)
    meta = dict(out.pop("meta", {}) or {})
    out["meta"] = {"elapsed_ms": max(0, int(elapsed_ms)), **meta}
    return out


def _kg_bad(action: str, msg: str, hint: str = "") -> dict:
    return _kg_envelope(action, error=(BAD_INPUT, msg, hint))


def _kg_counts(con: sqlite3.Connection) -> tuple[int, int, int]:
    e = con.execute("SELECT COUNT(*) c FROM entities").fetchone()["c"]
    o = con.execute("SELECT COUNT(*) c FROM observations").fetchone()["c"]
    r = con.execute("SELECT COUNT(*) c FROM relations").fetchone()["c"]
    return e, o, r


def _entity_exists(con: sqlite3.Connection, name: str) -> bool:
    return con.execute("SELECT 1 FROM entities WHERE name = ?", (name,)).fetchone() is not None


def _entity_payload(con: sqlite3.Connection, names: list[str]) -> list[dict]:
    out = []
    for n in names:
        row = con.execute("SELECT name, type FROM entities WHERE name = ?", (n,)).fetchone()
        if row is None:
            continue
        obs = [r["text"] for r in con.execute(
            "SELECT text FROM observations WHERE entity = ? ORDER BY id", (n,)).fetchall()]
        out.append({"name": row["name"], "type": row["type"], "observations": obs})
    return out


def _relations_touching(con: sqlite3.Connection, names: list[str]) -> list[dict]:
    if not names:
        return []
    marks, vals = [], []
    for n in names:
        marks.append("src = ? OR dst = ?")
        vals.extend([n, n])
    where = " OR ".join(marks)
    rows = con.execute(f"SELECT src, dst, kind FROM relations WHERE {where} "
                       "ORDER BY id LIMIT ?", (*vals, _MAX_READ_NODES * 2)).fetchall()
    return [{"from": r["src"], "to": r["dst"], "kind": r["kind"]} for r in rows]


def _kg_write_locked(action: str) -> dict | None:
    if bool(getattr(get_settings(), "kgmemory_enabled", True)):
        return None
    return _kg_envelope(action, error=(NEED_SETUP, "kgmemory writes are turned off on this server",
                                       "Tell her plainly; nothing to fix from the chat."))


def _do_kg_create(con: sqlite3.Connection, entities: Any) -> dict:
    if not isinstance(entities, list) or not entities:
        return _kg_bad("create", "create needs entities: [{name, type}]",
                       "names are the graph's primary keys - one line per entity.")
    if len(entities) > _MAX_ENTITIES_CALL:
        return _kg_bad("create", f"at most {_MAX_ENTITIES_CALL} entities per call")
    e_total, _, _ = _kg_counts(con)
    created, kept, clean = [], [], []
    for ent in entities:
        if not isinstance(ent, dict) or not str(ent.get("name") or "").strip():
            return _kg_bad("create", "every entity needs a name")
        name = _clean(ent.get("name"), _NAME_CHARS)
        etype = _clean(ent.get("type"), _TYPE_CHARS)
        clean.append((name, etype))
    if e_total + len({n for n, _ in clean}) > _MAX_ENTITIES_TOTAL:
        return _kg_envelope("create", error=(CONFLICT, "the graph is at its entity cap",
                                             "forget stale entities or keep the graph curated."))
    for name, etype in clean:
        if _entity_exists(con, name):
            kept.append(name)
            continue
        con.execute("INSERT INTO entities (name, type, created_at) VALUES (?, ?, ?)",
                    (name, etype, time.time()))
        created.append(name)
    con.commit()
    return _kg_envelope("create", entities=_entity_payload(con, [n for n, _ in clean]),
                        meta={"created": len(created), "kept": len(kept),
                              **({"created_names": created} if created else {})})


def _do_kg_relate(con: sqlite3.Connection, relations: Any) -> dict:
    if not isinstance(relations, list) or not relations:
        return _kg_bad("relate", "relate needs relations: [{from, to, kind}]",
                       "kind is the relation verb, e.g. works_at, part_of, uses.")
    if len(relations) > _MAX_RELATIONS_CALL:
        return _kg_bad("relate", f"at most {_MAX_RELATIONS_CALL} relations per call")
    clean = []
    for rel in relations:
        if not isinstance(rel, dict):
            return _kg_bad("relate", "every relation needs from, to, kind")
        src = _clean(rel.get("from") or rel.get("src"), _NAME_CHARS)
        dst = _clean(rel.get("to") or rel.get("dst"), _NAME_CHARS)
        kind = _clean(rel.get("kind") or rel.get("relation"), _KIND_CHARS)
        if not src or not dst or not kind:
            return _kg_bad("relate", "every relation needs from, to, kind")
        missing = [n for n in (src, dst) if not _entity_exists(con, n)]
        if missing:
            return _kg_envelope("relate", error=(NOT_FOUND, f"entity not in the graph: {', '.join(missing)}",
                                                 "action=create makes the entities first - no ghost refs."))
        clean.append((src, dst, kind))
    r_total, _, _ = _kg_counts(con)
    if r_total + len(set(clean)) > _MAX_RELATIONS_TOTAL:
        return _kg_envelope("relate", error=(CONFLICT, "the graph is at its relation cap",
                                             "forget stale relations or keep the graph curated."))
    added, kept = [], []
    for src, dst, kind in clean:
        cur = con.execute("SELECT 1 FROM relations WHERE src = ? AND dst = ? AND kind = ?",
                          (src, dst, kind)).fetchone()
        if cur:
            kept.append(f"{src}-[{kind}]->{dst}")
            continue
        con.execute("INSERT INTO relations (src, dst, kind, created_at) VALUES (?, ?, ?, ?)",
                    (src, dst, kind, time.time()))
        added.append({"from": src, "to": dst, "kind": kind})
    con.commit()
    return _kg_envelope("relate", added=added,
                        meta={"added": len(added), "kept": len(kept),
                              **({"note": "duplicate relations are kept once, reported as kept"} if kept else {})})


def _do_kg_observe(con: sqlite3.Connection, observations: Any) -> dict:
    if not isinstance(observations, list) or not observations:
        return _kg_bad("observe", "observe needs observations: [{entity, contents: [text...]}]",
                       "facts ride on entities - create the entity first if it is new.")
    clean: list[tuple[str, str]] = []
    for ob in observations:
        if not isinstance(ob, dict) or not str(ob.get("entity") or "").strip():
            return _kg_bad("observe", "every observation needs entity + contents")
        name = _clean(ob.get("entity"), _NAME_CHARS)
        contents = ob.get("contents") if isinstance(ob.get("contents"), list) else [ob.get("text")]
        for c in contents:
            text = str(c or "").strip()
            if not text:
                continue
            if len(text) > _OBS_CHARS:
                return _kg_bad("observe", f"one observation is over the {_OBS_CHARS}-char cap",
                               "observations are facts, not documents - split or shorten.")
            clean.append((name, _clean(text, _OBS_CHARS)))
        if len(clean) > _MAX_OBS_CALL:
            return _kg_bad("observe", f"at most {_MAX_OBS_CALL} observations per call")
    if not clean:
        return _kg_bad("observe", "no non-empty observation text found")
    unknown = sorted({n for n, _ in clean if not _entity_exists(con, n)})
    if unknown:
        return _kg_envelope("observe", error=(NOT_FOUND, f"entity not in the graph: {', '.join(unknown)}",
                                              "action=create makes the entity first - no ghost refs."))
    added, kept = 0, 0
    for name, text in clean:
        cur = con.execute("SELECT 1 FROM observations WHERE entity = ? AND text = ?", (name, text)).fetchone()
        if cur:
            kept += 1
            continue
        con.execute("INSERT INTO observations (entity, text, created_at) VALUES (?, ?, ?)",
                    (name, text, time.time()))
        added += 1
    con.commit()
    return _kg_envelope("observe", meta={"added": added, "kept": kept},
                        say=f"{added} observation(s) added")


def _do_kg_forget(con: sqlite3.Connection, entities: Any, relations: Any, observations: Any) -> dict:
    deleted = {"entities": [], "observations": 0, "relations": 0}
    if isinstance(entities, list) and entities:
        names = [_clean(n, _NAME_CHARS) for n in entities if str(n or "").strip()]
        for n in names:
            cur = con.execute("SELECT 1 FROM entities WHERE name = ?", (n,)).fetchone()
            if not cur:
                continue
            con.execute("DELETE FROM observations WHERE entity = ?", (n,))
            con.execute("DELETE FROM relations WHERE src = ? OR dst = ?", (n, n))
            con.execute("DELETE FROM entities WHERE name = ?", (n,))
            deleted["entities"].append(n)
    if isinstance(observations, list) and observations:
        for ob in observations:
            if not isinstance(ob, dict):
                continue
            name = _clean(ob.get("entity"), _NAME_CHARS)
            for c in (ob.get("contents") if isinstance(ob.get("contents"), list) else [ob.get("text")]):
                text = _clean(c, _OBS_CHARS)
                if name and text:
                    cur = con.execute("DELETE FROM observations WHERE entity = ? AND text = ?",
                                      (name, text))
                    deleted["observations"] += cur.rowcount if cur.rowcount > 0 else 0
    if isinstance(relations, list) and relations:
        for rel in relations:
            if not isinstance(rel, dict):
                continue
            src = _clean(rel.get("from") or rel.get("src"), _NAME_CHARS)
            dst = _clean(rel.get("to") or rel.get("dst"), _NAME_CHARS)
            kind = _clean(rel.get("kind") or rel.get("relation"), _KIND_CHARS)
            if src and dst and kind:
                cur = con.execute("DELETE FROM relations WHERE src = ? AND dst = ? AND kind = ?",
                                  (src, dst, kind))
                deleted["relations"] += cur.rowcount if cur.rowcount > 0 else 0
    con.commit()
    cascade = len(deleted["entities"]) > 0
    return _kg_envelope("forget", deleted=deleted,
                        meta={"cascade": "entity deletes take their observations and touching relations"
                                         " with them" if cascade else None},
                        say=("Forgot " + ", ".join(deleted["entities"])) if cascade else "Nothing matched")


def _do_kg_read(con: sqlite3.Connection) -> dict:
    names = [r["name"] for r in con.execute("SELECT name FROM entities ORDER BY name").fetchall()]
    truncated = len(names) > _MAX_READ_NODES
    if truncated:
        names = names[:_MAX_READ_NODES]
    ents = _entity_payload(con, names)
    rels = _relations_touching(con, names) if not truncated else []
    e_total, o_total, r_total = _kg_counts(con)
    return _kg_envelope("read", entities=ents, relations=rels,
                        meta={"entities": e_total, "observations": o_total, "relations": r_total,
                              **({"truncated": True,
                                  "hint": "graph past the read cap - action=search or action=open for neighbourhoods"}
                                 if truncated else {})})


def _do_kg_search(con: sqlite3.Connection, query: str) -> dict:
    needle = (query or "").strip().lower()
    if not needle:
        return _kg_bad("search", "search needs a query", "matched against names, types and observations.")
    like = f"%{needle}%"
    rows = con.execute(
        "SELECT DISTINCT name FROM entities WHERE LOWER(name) LIKE ? OR LOWER(type) LIKE ? "
        "UNION SELECT DISTINCT entity FROM observations WHERE LOWER(text) LIKE ? LIMIT ?",
        (like, like, like, _MAX_MATCH_NODES)).fetchall()
    names = [r["name"] for r in rows]
    ents = _entity_payload(con, names)
    return _kg_envelope("search", query=needle, entities=ents, relations=_relations_touching(con, names),
                        meta={"matches": len(ents)})


def _do_kg_open(con: sqlite3.Connection, names: Any) -> dict:
    if not isinstance(names, list) or not names:
        return _kg_bad("open", "open needs names: [entity names]", "exact names - search finds them.")
    wanted = [_clean(n, _NAME_CHARS) for n in names if str(n or "").strip()][: _MAX_MATCH_NODES]
    missing = [n for n in wanted if not _entity_exists(con, n)]
    ents = _entity_payload(con, [n for n in wanted if n not in missing])
    return _kg_envelope("open", names=wanted, entities=ents, relations=_relations_touching(con, wanted),
                        meta={"found": len(ents), **({"missing": missing} if missing else {})})


def kg_forget_carrying(tenant_id: str, fact: str, carries) -> int:
    """v0.603 BHOOL JAO HAR JAGAH: the graph's observations that carry a forgotten fact go. A tenant
    with no graph has nothing to forget (the file is never created for this)."""
    if not _kg_path(tenant_id).exists():
        return 0
    con = _kg_con(tenant_id)
    try:
        rows = con.execute("SELECT id, entity, text FROM observations").fetchall()
        ids = [r["id"] for r in rows if carries(fact, f"{r['entity']} {r['text']}")]
        for i in ids:
            con.execute("DELETE FROM observations WHERE id=?", (i,))
        con.commit()
        return len(ids)
    finally:
        con.close()


async def kgmemory(ctx: Ctx, action: str = "read", *, entities: list | None = None,
                   relations: list | None = None, observations: list | None = None,
                   names: list | None = None, query: str | None = None, **_) -> dict:
    """The tenant knowledge graph. Never raises; every answer is one envelope."""
    started = time.monotonic()
    action = str(action or "").strip().lower()
    if action not in _KG_ACTIONS:
        return _kg_bad(action or "", f"unknown action '{action}'; valid: {', '.join(_KG_ACTIONS)}")
    if action in ("create", "relate", "observe", "forget"):
        locked = _kg_write_locked(action)
        if locked:
            return locked
    if action in ("create", "relate", "observe"):
        # v0.603 INCOGNITO SACH: an incognito chat may READ her graph but never adds to it
        # ("yahan ki baatein yaad mein nahi jayengi"); forget stays allowed - removing is always hers
        from ..fence import is_incognito
        if is_incognito(getattr(ctx, "conversation_id", "") or ""):
            return _kg_envelope(action, error=(NEED_SETUP, "this is an incognito chat: nothing from it is "
                                               "remembered, so the knowledge graph is read-only here",
                                               "Tell her plainly; if she wants it kept, say it in a normal chat."))
    con = _kg_con(ctx.tenant_id)
    try:
        if action == "create":
            out = _do_kg_create(con, entities)
        elif action == "relate":
            out = _do_kg_relate(con, relations)
        elif action == "observe":
            out = _do_kg_observe(con, observations)
        elif action == "forget":
            out = _do_kg_forget(con, entities, relations, observations)
        elif action == "read":
            out = _do_kg_read(con)
        elif action == "search":
            out = _do_kg_search(con, query or "")
        else:
            out = _do_kg_open(con, names)
    finally:
        con.close()
    out["meta"]["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return out


# ---------------------------------------------------------------- the tool specs the model sees
WORKSPACE_TOOLS = [
    {"name": "workspace", "description": (
        "SANDARBH MANCH (v0.586): the agent's OWN file desk - one confined directory per tenant, the "
        "reference MCP filesystem idea. Actions: list (one directory) | read (text file) | write "
        "(create/overwrite, parents auto-made) | edit (EXACT string replace; old_string must appear once "
        "or pass replace_all=true) | tree (recursive walk, depth-capped) | search (files/folders by name "
        "fragment) | info (size/type/modified). Every path is relative and stays inside meta.root - the "
        "envelope names the allowed root on every answer; escapes, symlinks and binary reads are refused. "
        "One envelope {ok, action, path, error:{code, message, hint}}."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": list(_WS_ACTIONS),
                    "description": "list | read | write | edit | tree | search | info"},
         "path": {"type": "string", "description": "relative path inside the workspace root (list/tree default to the root)"},
         "content": {"type": "string", "description": "write: the full text to write"},
         "old_string": {"type": "string", "description": "edit: the exact text to replace"},
         "new_string": {"type": "string", "description": "edit: the replacement text"},
         "replace_all": {"type": "boolean", "description": "edit: replace every occurrence (default false = once)"},
         "pattern": {"type": "string", "description": "search: name fragment, case-insensitive"}}}},
]

KGMEMORY_TOOLS = [
    {"name": "kgmemory", "description": (
        "SANDARBH MANCH (v0.586): the agent's OWN knowledge-graph memory - entities, typed relations and "
        "text observations per tenant, the reference MCP memory idea. Actions: create (entities "
        "[{name, type}]) | relate (relations [{from, to, kind}] - BOTH entities must already exist, no "
        "ghost refs) | observe (facts [{entity, contents: [text...]}], deduped) | forget (deletes: "
        "entities and/or relations and/or observations; an entity delete takes its observations and "
        "touching relations with it, and says so) | read (the graph, capped - use search/open past the "
        "cap) | search (substring over names, types, observations) | open (exact entities + their "
        "neighbourhood). One envelope {ok, action, error:{code, message, hint}}."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": list(_KG_ACTIONS),
                    "description": "create | relate | observe | forget | read | search | open"},
         "entities": {"type": "array", "description": "create: [{name, type}]; forget: [name,...]"},
         "relations": {"type": "array", "description": "relate: [{from, to, kind}]; forget: the exact triples to drop"},
         "observations": {"type": "array", "description": "observe: [{entity, contents: [text,...]}]; forget: [{entity, contents/text}]"},
         "names": {"type": "array", "description": "open: exact entity names"},
         "query": {"type": "string", "description": "search: substring over names, types and observations"}}}},
]

WORKSPACE_LABELS = {"workspace": "Sandarbh: the agent's own file desk"}
KGMEMORY_LABELS = {"kgmemory": "Sandarbh: the knowledge-graph memory"}

WORKSPACE_HANDLERS = {"workspace": workspace}
KGMEMORY_HANDLERS = {"kgmemory": kgmemory}
