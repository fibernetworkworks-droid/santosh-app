"""v0.943 THE CODE MAP (owner, on the Cursor comparison: "No index of the code. On big repos it reads more and takes
longer. Hoola's code map tool exists but isn't connected to Hoola Code").

Worked out in CODE from the working copy, never from a model's guess:
  * every source file's top-level names (functions, classes, types) with their line numbers, read by small regexes
    per language,
  * which modules lean on which, from the import lines (the Master Architect's `archdesk/repomap.py`),
  * a short MAP for the session's first message: the files that match her words first, then the most-depended-on
    ones, fitted to a character budget,
  * the `code_map` tool: `find` a name -> where it is defined; `refs` a name -> the lines that use it; `file` a path ->
    its names with lines. One call instead of a dozen greps on a big repo.

Secrets are never read into it (the engine's SECRET_FILES), links are never followed (the working copy's own walk),
and a huge repo is read only up to a ceiling - the map says when it stopped early.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger("hoola.devsahayak.repoindex")

SOURCE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".java", ".kt", ".kts", ".cs", ".php",
              ".rs", ".dart", ".swift", ".rb", ".c", ".h", ".cc", ".cpp", ".hpp", ".vue", ".svelte")
MAX_FILES = 4000            # files read for names
MAX_BYTES = 400_000         # a file bigger than this is listed, not read (generated / bundled code)
MAX_TOTAL = 40_000_000      # all bytes read for one map
MAP_CHARS = 5000            # the map in the first message

_DEFS: list[tuple[tuple[str, ...], re.Pattern[str]]] = [
    ((".py",), re.compile(r"^(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)", re.M)),
    ((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte"), re.compile(
        r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\*?\s+([A-Za-z_$][\w$]*)"
        r"|class\s+([A-Za-z_$][\w$]*)|(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)"
        r"|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>)", re.M)),
    ((".go",), re.compile(r"^(?:func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)|type\s+([A-Za-z_]\w*))", re.M)),
    ((".java", ".kt", ".kts", ".cs", ".swift"), re.compile(
        r"^\s{0,4}(?:(?:public|private|protected|internal|open|abstract|final|static|sealed|data|override|suspend|partial)\s+)*"
        r"(?:class|interface|object|enum|struct|record|protocol|extension|fun|func)\s+([A-Za-z_]\w*)", re.M)),
    ((".rs",), re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:fn|struct|enum|trait|type|mod)\s+([A-Za-z_]\w*)", re.M)),
    ((".dart",), re.compile(r"^(?:abstract\s+|sealed\s+|final\s+|base\s+)*(?:class|mixin|enum|extension|typedef)\s+([A-Za-z_]\w*)"
                            r"|^(?:Future<[^>]*>|void|String|int|double|bool|Widget|dynamic|[A-Z]\w*)\s+([a-z_]\w*)\s*\(", re.M)),
    ((".rb",), re.compile(r"^\s*(?:def|class|module)\s+(?:self\.)?([A-Za-z_]\w*[?!]?)", re.M)),
    ((".php",), re.compile(r"^\s*(?:(?:abstract|final|public|private|protected|static)\s+)*(?:function|class|interface|trait)\s+([A-Za-z_]\w*)", re.M)),
    ((".c", ".h", ".cc", ".cpp", ".hpp"), re.compile(r"^(?:[A-Za-z_][\w:<>,\s\*&]*\s+)?\**([A-Za-z_]\w*)\s*\([^;]*\)\s*\{|^(?:class|struct)\s+([A-Za-z_]\w*)", re.M)),
]
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_STOP = {"the", "and", "for", "with", "this", "that", "from", "into", "make", "add", "fix", "please", "karo", "kar", "ko",
         "hai", "mein", "aur", "nahi", "should", "when", "what", "where", "file", "code", "page", "app", "all"}


def names_in(path: str, text: str) -> list[tuple[str, int]]:
    """Top-level names a file defines, with 1-based line numbers. Pure."""
    low = path.lower()
    for exts, rx in _DEFS:
        if low.endswith(exts):
            out: list[tuple[str, int]] = []
            seen: set[str] = set()
            for m in rx.finditer(text):
                name = next((g for g in m.groups() if g), "")
                if not name or name in seen or name in ("if", "for", "while", "switch", "return", "main") and low.endswith((".c", ".cc", ".cpp")):
                    continue
                seen.add(name)
                out.append((name, text.count("\n", 0, m.start()) + 1))
                if len(out) >= 200:
                    break
            return out
    return []


def _readable(repo: Path, rel: str) -> str | None:
    try:
        from . import engine as EN
        if EN.R.SECRET_FILES.search(rel):
            return None
    except Exception:
        pass
    p = repo / rel
    try:
        if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_BYTES:
            return None
        return p.read_text("utf-8", errors="ignore")
    except OSError:
        return None


def _words(request: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(request or "") if w.lower() not in _STOP}


def build(repo: Path, paths: list[str], request: str = "") -> dict[str, Any]:
    """Read the working copy once: {files: {path: [(name, line)]}, graph: repomap graph, read, skipped, stopped}.
    On a repo too big to read whole, the files whose path matches her words are read first."""
    words = _words(request)
    src = [p for p in paths if p.lower().endswith(SOURCE_EXT)]
    if words:
        src.sort(key=lambda p: -sum(1 for w in words if w in p.lower()))
    files: dict[str, list[tuple[str, int]]] = {}
    texts: dict[str, str] = {}
    total, stopped = 0, False
    for rel in src[:MAX_FILES]:
        text = _readable(repo, rel)
        if text is None:
            continue
        total += len(text)
        if total > MAX_TOTAL:
            stopped = True
            break
        texts[rel] = text
        files[rel] = names_in(rel, text)
    stopped = stopped or len(src) > MAX_FILES
    graph: dict[str, Any] = {}
    try:
        from ..archdesk import repomap as RM
        graph = RM.build(texts, all_paths=paths)
    except Exception as e:                       # the map without module arrows is still a map
        log.debug("repomap build failed: %s", e)
    return {"files": files, "graph": graph, "read": len(texts), "source": len(src), "stopped": stopped}


def _fan_in(graph: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in graph.get("edges") or []:
        if isinstance(e, dict):
            to = str(e.get("to") or e.get("target") or "")
            out[to] = out.get(to, 0) + int(e.get("count") or e.get("imports") or 1)
        elif isinstance(e, (list, tuple)) and len(e) >= 2:
            out[str(e[1])] = out.get(str(e[1]), 0) + (int(e[2]) if len(e) > 2 and str(e[2]).isdigit() else 1)
    return out


def map_text(idx: dict[str, Any], request: str = "", budget: int = MAP_CHARS) -> str:
    """The <repo_map> block: matching files first, then the most-depended-on, each with its names. '' when empty."""
    files: dict[str, list[tuple[str, int]]] = idx.get("files") or {}
    if not files:
        return ""
    words = _words(request)
    fan = _fan_in(idx.get("graph") or {})
    try:
        from ..archdesk import repomap as RM
        mod_of = RM.module_of
    except Exception:
        def mod_of(p: str, depth: int = 2) -> str:
            return "/".join(p.split("/")[:depth])

    def score(path: str) -> float:
        low = path.lower()
        names = " ".join(n.lower() for n, _ in files[path][:60])
        hit = sum(2 for w in words if w in low) + sum(1 for w in words if w in names)
        return hit * 100 + fan.get(mod_of(path), 0) + min(len(files[path]), 20) * 0.1

    ranked = sorted(files, key=lambda p: (-score(p), p))
    head = (f"<repo_map files=\"{idx.get('source', len(files))}\" read=\"{idx.get('read', len(files))}\">\n"
            "Source files with the names each defines (file: Name:line). Use code_map find / refs / file for more; "
            "read a file only when you need its body.\n")
    lines: list[str] = []
    used = len(head) + 40
    for p in ranked:
        ns = files[p]
        line = f"{p}: " + (", ".join(f"{n}:{ln}" for n, ln in ns[:14]) + (f" +{len(ns) - 14}" if len(ns) > 14 else "") if ns else "-")
        if used + len(line) + 1 > budget:
            lines.append(f"... {len(ranked) - len(lines)} more files (code_map file / find to see them)")
            break
        lines.append(line)
        used += len(line) + 1
    hot = sorted(fan.items(), key=lambda kv: -kv[1])[:6]
    tail = ""
    if hot:
        tail = "Most depended-on modules: " + ", ".join(f"{m} ({n} imports in)" for m, n in hot) + "\n"
    if idx.get("stopped"):
        tail += "(The repo is big: the map read the first part only.)\n"
    return head + "\n".join(lines) + "\n" + tail + "</repo_map>"


# ---------------------------------------------------------------- the code_map tool
CODE_MAP_TOOL = {
    "name": "code_map",
    "description": ("The repo's code map, worked out from the working copy (no guess). "
                    "action find + name: where a function / class / type is defined (file:line). "
                    "action refs + name: the lines that use a name, across the repo (up to 60). "
                    "action file + path: the names a file defines, with lines. "
                    "Faster than many greps on a big repo; read the file itself only when you need its body."),
    "input_schema": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["find", "refs", "file"]},
        "name": {"type": "string", "description": "For find / refs: the exact name"},
        "path": {"type": "string", "description": "For file: the path from the repo root"}},
        "required": ["action"]},
}


_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_S = 120


def cached(key: str, repo: Path, paths: list[str]) -> dict[str, Any]:
    """The map of one session, kept CACHE_S seconds so a run of lookups costs one read (edited files are re-read)."""
    import time
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_S:
        return hit[1]
    idx = build(repo, paths)
    _CACHE[key] = (time.time(), idx)
    if len(_CACHE) > 16:
        _CACHE.pop(min(_CACHE, key=lambda k: _CACHE[k][0]), None)
    return idx


def forget(key: str) -> None:
    _CACHE.pop(key, None)


def on() -> bool:
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "dev_code_map", True))
    except Exception:
        return True


def run_tool(repo: Path, paths: list[str], inp: dict[str, Any], idx: dict[str, Any] | None = None) -> str:
    act = str(inp.get("action") or "")
    name = str(inp.get("name") or "").strip()
    if act in ("find", "refs") and not re.fullmatch(r"[A-Za-z_$][\w$]*[?!]?", name):
        return "Give the exact name (letters, digits, _): for example name=\"create_order\"."
    idx = idx if idx is not None else build(repo, paths)
    files: dict[str, list[tuple[str, int]]] = idx.get("files") or {}
    if act == "find":
        hits = [f"{p}:{ln}" for p, ns in files.items() for n, ln in ns if n == name]
        if not hits:
            near = sorted({n for ns in files.values() for n, _ in ns if name.lower() in n.lower()})[:12]
            return f"No definition of {name}." + (f" Close names: {', '.join(near)}" if near else "")
        return f"{name} is defined at:\n" + "\n".join(hits[:40])
    if act == "refs":
        rx = re.compile(r"(?<![\w$])" + re.escape(name) + r"(?![\w$])")
        out: list[str] = []
        for p in files:
            text = _readable(repo, p)
            if not text or name not in text:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    out.append(f"{p}:{i}: {line.strip()[:160]}")
                    if len(out) >= 60:
                        return f"Uses of {name} (first 60):\n" + "\n".join(out)
        return (f"Uses of {name}:\n" + "\n".join(out)) if out else f"No line uses {name}."
    if act == "file":
        from ..devlab import service as LS
        rel = LS.safe_rel(str(inp.get("path") or ""))
        if not rel:
            return "Give the file's path from the repo root."
        text = _readable(repo, rel)                 # always the file as it is now, after any edit
        if text is None:
            return f"{rel} is not a readable source file (or it holds secrets)."
        ns = names_in(rel, text)
        return (f"{rel} defines:\n" + "\n".join(f"{n}:{ln}" for n, ln in ns)) if ns else f"{rel} defines no top-level names."
    return "action must be find, refs or file."
