"""v0.999.322 THE SYNTAX CHECK ON SAVE (from the bolt.diy read): every JS / TS file Hoola writes into an App Engine app
is parsed the moment it is written, so a broken file is refused with its exact line and column instead of failing the
next build in the box (slower, a whole build round lost).

The parser is tree-sitter's TypeScript grammar (tree-sitter-typescript, MIT; .ts uses the TypeScript grammar, .tsx /
.jsx / .js / .mjs the TSX one). The parser only finds where a file stops making sense: it never runs the code and never
rewrites it. When the parser is not installed on the server the check is skipped and says so; the build still checks.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

EXTS = {".ts", ".mts", ".cts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
MAX_PROBLEMS = 4


@lru_cache(maxsize=2)
def _parser(kind: str):
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_typescript as tst
    except Exception:                                    # noqa: BLE001 - no parser here: the check is skipped, the build checks
        return None
    lang = Language(tst.language_typescript() if kind == "ts" else tst.language_tsx())
    try:
        return Parser(lang)
    except TypeError:                                    # an older tree-sitter: Parser() then .language
        p = Parser()
        p.language = lang
        return p


def available() -> bool:
    return _parser("tsx") is not None


def _ext(path: str) -> str:
    m = re.search(r"\.[A-Za-z0-9]+$", path or "")
    return m.group(0).lower() if m else ""


def _walk_problems(node, out: list) -> None:
    """The first error nodes, deepest useful first: a MISSING token (a } or ) the parser had to invent) or an ERROR."""
    if len(out) >= MAX_PROBLEMS:
        return
    if node.is_missing:
        out.append(("missing", node))
        return
    if node.type == "ERROR":
        out.append(("error", node))
        return
    if not node.has_error:
        return
    for ch in node.children:
        _walk_problems(ch, out)
        if len(out) >= MAX_PROBLEMS:
            return


def _hint(kind: str, node, code: str, line_text: str) -> str:
    if "\n" not in code.strip() and len(code) > 200:
        return "the whole file came as ONE line; send it with real line breaks"
    if kind == "missing":
        t = node.type
        return {"}": "a closing } is missing", ")": "a closing ) is missing", "]": "a closing ] is missing",
                ";": "the statement before it is not finished", ">": "a JSX tag is not closed",
                "identifier": "a name is missing here"}.get(t, f"'{t}' is missing here")
    s = line_text.strip()
    if re.search(r"<[A-Za-z][^>]*$", s):
        return "a JSX tag is not closed on this line"
    if s.count("{") != s.count("}") or s.count("(") != s.count(")"):
        return "the brackets on this line do not match"
    if re.search(r"\)\s*\.map\(", s) or ".map(" in s:
        return "keep the whole .map(...) inside one JSX {expression}"
    return "the code stops making sense here"


def check(path: str, code: str) -> list[dict[str, Any]] | None:
    """Problems as [{file, line, col, rule: 'syntax', found, fix}] ([] = it parses). None = not a JS/TS file or no parser."""
    ext = _ext(path)
    if ext not in EXTS:
        return None
    p = _parser("ts" if ext in (".ts", ".mts", ".cts") else "tsx")
    if p is None:
        return None
    data = code.encode("utf-8")
    tree = p.parse(data)
    if not tree.root_node.has_error:
        return []
    found: list = []
    _walk_problems(tree.root_node, found)
    lines = code.split("\n")
    out = []
    for kind, node in found:
        row, col_b = node.start_point
        row = min(row, max(0, len(lines) - 1))
        text = lines[row] if lines else ""
        col = len(text.encode("utf-8")[:col_b].decode("utf-8", "replace")) + 1
        out.append({"file": path, "line": row + 1, "col": col, "rule": "syntax", "found": text.strip()[:160],
                    "fix": _hint(kind, node, code, text)})
    return out


def say(probs: list[dict[str, Any]]) -> str:
    return "; ".join(f"line {p['line']} col {p['col']}: {p['fix']} (`{p['found']}`)" for p in probs[:MAX_PROBLEMS])
