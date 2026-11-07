"""MASTER ARCHITECT: her repo's real module map, worked out in CODE from the import lines - never from a model's guess.

`build(files)` takes {path: source text} and returns the module graph (a module = the first two folders of a path, so
`app/orders/api.py` is `app/orders`), the edges with how many imports carry each one, dependency CYCLES (Tarjan),
fan-in / fan-out hot-spots and the biggest modules. `mermaid()` draws it as a diagram that is true by construction.
`check_rules()` runs the design's fitness rules ("orders must not depend on riders") over a graph, so a design rule
becomes a check code can run on every PR, not an opinion.

Imports understood: Python (import / from), JavaScript / TypeScript (import ... from, require, dynamic import), Go
(import "..."), Java / Kotlin (import a.b.C), C# (using), PHP (use), Rust (use crate::). Unresolved imports (packages
from outside the repo) are counted as external, never guessed onto a module.
"""
from __future__ import annotations

import posixpath
import re
from typing import Any

SOURCE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".java", ".kt", ".cs", ".php", ".rs")
MAX_EDGES_DRAWN = 40

_PY = re.compile(r"^\s*(?:from\s+(\.*[\w.]*)\s+import\s+([\w*, ()]+)|import\s+([\w., ]+))", re.M)
_JS = re.compile(r"""(?:import\s+(?:[\w*{}\s,]+\s+from\s+)?|require\(\s*|import\(\s*|export\s+[\w*{}\s,]+\s+from\s+)['"]([^'"]+)['"]""")
_GO = re.compile(r'"([\w./-]+)"')
_GO_BLOCK = re.compile(r"^\s*import\s*(?:\(([^)]*)\)|([\w.]*\s*\"[^\"]+\"))", re.M | re.S)
_JAVA = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)", re.M)
_CS = re.compile(r"^\s*using\s+(?:static\s+)?([\w.]+)\s*;", re.M)
_PHP = re.compile(r"^\s*use\s+([\w\\]+)", re.M)
_RS = re.compile(r"^\s*(?:pub\s+)?use\s+crate::([\w:]+)", re.M)
_MOD = re.compile(r"[^\w./-]")


def module_of(path: str, depth: int = 2) -> str:
    """'app/orders/api.py' -> 'app/orders'; a top-level file -> its own name without the extension."""
    parts = [p for p in path.split("/") if p]
    if len(parts) <= 1:
        return posixpath.splitext(parts[0])[0] if parts else ""
    dirs = parts[:-1]
    return "/".join(dirs[:depth])


def _py_targets(path: str, text: str, paths: set[str]) -> list[str]:
    out = []
    here = posixpath.dirname(path)
    for m in _PY.finditer(text):
        frm, names, plain = m.group(1), m.group(2), m.group(3)
        mods: list[str] = []
        if plain:
            mods = [x.strip().split(" as ")[0] for x in plain.split(",") if x.strip()]
        elif frm is not None:
            dots = len(frm) - len(frm.lstrip("."))
            rest = frm.lstrip(".")
            if dots:
                base = here
                for _ in range(dots - 1):
                    base = posixpath.dirname(base)
                root = posixpath.join(base, rest.replace(".", "/")) if rest else base
                cands = [root] + [posixpath.join(root, n.strip(" ()")) for n in (names or "").split(",") if n.strip(" ()*")]
                out += [c for c in cands if _resolve_py(c, paths)]
                continue
            mods = [rest] + [f"{rest}.{n.strip(' ()')}" for n in (names or "").split(",") if n.strip(" ()*")]
        for mod in mods:
            c = mod.replace(".", "/")
            if _resolve_py(c, paths):
                out.append(c)
    return out


def _resolve_py(cand: str, paths: set[str]) -> str:
    for p in (cand + ".py", cand + "/__init__.py"):
        if p in paths:
            return p
    for root in ("src/", "app/", "lib/"):             # common source roots imported without the prefix
        for p in (root + cand + ".py", root + cand + "/__init__.py"):
            if p in paths:
                return p
    return ""


def _js_resolve(path: str, spec: str, paths: set[str]) -> str:
    if not spec.startswith((".", "/", "@/", "~/", "src/")):
        return ""
    if spec.startswith(("@/", "~/")):
        spec = "src/" + spec[2:]
        base = spec
    elif spec.startswith("/"):
        base = spec.lstrip("/")
    elif spec.startswith("src/"):
        base = spec
    else:
        base = posixpath.normpath(posixpath.join(posixpath.dirname(path), spec))
    for ext in ("", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", "/index.ts", "/index.tsx", "/index.js", "/index.jsx"):
        if base + ext in paths:
            return base + ext
    return ""


def _dotted_resolve(name: str, paths: set[str], sep: str = ".") -> str:
    """Java / Kotlin / C# / PHP: the longest repo path whose directory matches the dotted name."""
    segs = [s for s in re.split(r"[.\\:]+", name) if s]
    for cut in range(len(segs), 0, -1):
        frag = "/".join(segs[:cut])
        for p in paths:
            if f"/{frag}." in "/" + p or f"/{frag}/" in "/" + p:
                return p
    return ""


def _targets(path: str, text: str, paths: set[str], go_mod: str) -> tuple[list[str], int]:
    """(repo files this file imports, count of imports that point outside the repo)."""
    low = path.lower()
    found: list[str] = []
    external = 0
    if low.endswith(".py"):
        found = [_resolve_py(c, paths) for c in _py_targets(path, text, paths)]
        external = max(0, len(_PY.findall(text)) - len(found))
    elif low.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
        for spec in _JS.findall(text):
            r = _js_resolve(path, spec, paths)
            if r:
                found.append(r)
            else:
                external += 1
    elif low.endswith(".go"):
        for block, single in _GO_BLOCK.findall(text):
            for spec in _GO.findall(block or single):
                if go_mod and spec.startswith(go_mod + "/"):
                    rel = spec[len(go_mod) + 1:]
                    hit = next((p for p in paths if p.startswith(rel + "/") and p.endswith(".go")), "")
                    if hit:
                        found.append(hit)
                        continue
                external += 1
    else:
        rx = _JAVA if low.endswith((".java", ".kt")) else _CS if low.endswith(".cs") else _PHP if low.endswith(".php") \
            else _RS if low.endswith(".rs") else None
        if rx is not None:
            for name in rx.findall(text):
                r = _dotted_resolve(name, paths)
                if r:
                    found.append(r)
                else:
                    external += 1
    return [f for f in found if f and f != path], external


def _tarjan(nodes: list[str], edges: dict[str, set[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on: set[str] = set()
    out: list[list[str]] = []
    counter = [0]

    def visit(v: str) -> None:            # iterative enough for repo-sized graphs (a few hundred modules)
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in sorted(edges.get(v, ())):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))

    import sys
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, 10000))
    try:
        for v in nodes:
            if v not in index:
                visit(v)
    finally:
        sys.setrecursionlimit(old)
    return sorted(out, key=lambda c: (-len(c), c))


def build(files: dict[str, str], all_paths: list[str] | None = None, depth: int = 2) -> dict[str, Any]:
    """The module graph of the files given (path -> text). all_paths = every path in the repo (for resolving imports
    to files that were not read)."""
    paths = set(all_paths or []) | set(files)
    go_mod = ""
    gm = files.get("go.mod", "")
    m = re.search(r"^module\s+(\S+)", gm, re.M)
    if m:
        go_mod = m.group(1)
    file_edges: dict[str, set[str]] = {}
    external = 0
    for path, text in files.items():
        if not path.lower().endswith(SOURCE_EXT):
            continue
        tg, ext = _targets(path, text or "", paths, go_mod)
        external += ext
        file_edges[path] = set(tg)
    weight: dict[tuple[str, str], int] = {}
    size: dict[str, int] = {}
    for path in file_edges:
        size[module_of(path, depth)] = size.get(module_of(path, depth), 0) + len((files.get(path) or "").splitlines())
    for src, tgs in file_edges.items():
        a = module_of(src, depth)
        for t in tgs:
            b = module_of(t, depth)
            if a and b and a != b:
                weight[(a, b)] = weight.get((a, b), 0) + 1
    edges: dict[str, set[str]] = {}
    for (a, b) in weight:
        edges.setdefault(a, set()).add(b)
    nodes = sorted(set(size) | {a for a, _ in weight} | {b for _, b in weight})
    fan_out = {n: len(edges.get(n, ())) for n in nodes}
    fan_in = {n: sum(1 for a in edges if n in edges[a]) for n in nodes}
    cycles = _tarjan(nodes, edges)
    hot = sorted(nodes, key=lambda n: -(fan_in[n] + fan_out[n]))[:8]
    return {"modules": nodes, "edges": [{"from": a, "to": b, "imports": w} for (a, b), w in
                                        sorted(weight.items(), key=lambda kv: (-kv[1], kv[0]))],
            "cycles": cycles, "files_scanned": len(file_edges), "external_imports": external,
            "hotspots": [{"module": n, "fan_in": fan_in[n], "fan_out": fan_out[n], "lines": size.get(n, 0)}
                         for n in hot if fan_in[n] + fan_out[n] > 0],
            "biggest": [{"module": n, "lines": size[n]} for n in sorted(size, key=lambda n: -size[n])[:8]]}


def _nid(name: str) -> str:
    return "m_" + re.sub(r"\W", "_", name)[:60]


def mermaid(graph: dict[str, Any]) -> str:
    """The as-is module graph as a Mermaid flowchart (heaviest edges first, capped); cycle edges drawn thick."""
    edges = graph.get("edges") or []
    if not edges:
        return ""
    in_cycle = {m for c in graph.get("cycles") or [] for m in c}
    shown = edges[:MAX_EDGES_DRAWN]
    names = sorted({e["from"] for e in shown} | {e["to"] for e in shown})
    lines = ["flowchart LR"]
    for n in names:
        label = _MOD.sub("", n)[:50] or n[:50]
        lines.append(f'  {_nid(n)}["{label}"]')
    for e in shown:
        arrow = "==>" if e["from"] in in_cycle and e["to"] in in_cycle else "-->"
        lines.append(f'  {_nid(e["from"])} {arrow}|{e["imports"]}| {_nid(e["to"])}')
    return "\n".join(lines)


def _match(module: str, pattern: str) -> bool:
    p = (pattern or "").strip().strip("/")
    return bool(p) and (module == p or module.startswith(p + "/") or p.endswith("*") and module.startswith(p[:-1]))


def clean_rules(rules: Any) -> list[dict[str, str]]:
    """The design's fitness rules, shaped: [{name, from, must_not_depend_on, why}] (max 20)."""
    out = []
    for r in rules if isinstance(rules, list) else []:
        if not isinstance(r, dict):
            continue
        a = str(r.get("from") or "").strip().strip("/")[:120]
        b = str(r.get("must_not_depend_on") or "").strip().strip("/")[:120]
        if a and b and a != b:
            out.append({"name": str(r.get("name") or f"{a} must not depend on {b}")[:160], "from": a,
                        "must_not_depend_on": b, "why": str(r.get("why") or "")[:300]})
    return out[:20]


def check_rules(rules: list[dict[str, str]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every rule against every edge: [{rule, from, to, imports}] for each break (empty = the code follows the design)."""
    out = []
    for r in rules:
        for e in edges:
            if _match(e["from"], r["from"]) and _match(e["to"], r["must_not_depend_on"]):
                out.append({"rule": r["name"], "from": e["from"], "to": e["to"], "imports": e.get("imports", 1)})
    return out


def pr_edges(files: list[dict[str, Any]], all_paths: list[str], depth: int = 2) -> list[dict[str, Any]]:
    """Module edges ADDED by a pull request: only the '+' lines of each patch are read, so an old import is never
    blamed on the PR."""
    paths = set(all_paths)
    weight: dict[tuple[str, str], int] = {}
    for f in files:
        path = str(f.get("filename") or "")
        if not path.lower().endswith(SOURCE_EXT):
            continue
        added = "\n".join(ln[1:] for ln in str(f.get("patch") or "").splitlines()
                          if ln.startswith("+") and not ln.startswith("+++"))
        tg, _ = _targets(path, added, paths | {path}, "")
        a = module_of(path, depth)
        for t in tg:
            b = module_of(t, depth)
            if a and b and a != b:
                weight[(a, b)] = weight.get((a, b), 0) + 1
    return [{"from": a, "to": b, "imports": w} for (a, b), w in sorted(weight.items())]
