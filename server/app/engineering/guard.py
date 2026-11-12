"""Code check for the CadQuery scripts Hoola writes for a CAD part (same idea as blender3d/guard.py).

Before a script reaches the runner it is parsed and walked: only `cadquery` and `math` may be imported, and anything that
could read / write files, reach the network, start programs or poke Python's internals is refused with a plain reason the
model can fix. The runner runs it again with cut-down builtins and an import gate, in a process with no network and no
secrets (sandbox.py). Saving / exporting is the runner's job, never the script's: the script only builds `result`."""
from __future__ import annotations

import ast

MAX_CHARS = 40_000
ALLOWED_IMPORTS = {"cadquery", "math"}

BAD_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "breakpoint", "input", "help",
             "exit", "quit", "memoryview", "delattr", "setattr", "getattr", "__builtins__", "__loader__", "__spec__",
             "classmethod", "staticmethod", "super", "object", "type", "show_object", "debug"}

BAD_ATTRS = {
    # files: the runner exports STEP / STL itself
    "exporters", "importers", "export", "exportStep", "exportStl", "exportBrep", "exportSvg", "exportDXF",
    "importStep", "importBrep", "importStl", "importDXF", "importSvg", "save", "load", "write", "toSvg",
    "fromBrep", "importBin", "exportBin", "occ_impl", "vis", "cq_directive",
    # v0.361 never by name, whatever object it hangs off (the box may have no network namespace on some servers)
    "os", "sys", "subprocess", "socket", "shutil", "importlib", "ctypes", "builtins", "tempfile", "pathlib", "io",
    "system", "popen", "Popen", "environ", "getenv", "putenv", "spawn", "fork", "modules", "urllib", "http", "requests",
    # python internals
    "f_globals", "f_locals", "f_back", "gi_frame", "gi_code", "co_code", "func_globals", "tb_frame", "mro",
}


class GuardError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def problems(code: str) -> list[str]:
    """Plain-word problems; [] = the script may run."""
    code = code or ""
    if not code.strip():
        return ["the script is empty"]
    if len(code) > MAX_CHARS:
        return [f"the script is too long ({len(code)} > {MAX_CHARS} characters)"]
    try:
        tree = ast.parse(code, filename="hoola_part.py")
    except SyntaxError as e:
        return [f"SyntaxError line {e.lineno}: {e.msg}"]
    out: list[str] = []

    def bad(node: ast.AST, why: str) -> None:
        msg = f"line {getattr(node, 'lineno', 0)}: {why}"
        if msg not in out:
            out.append(msg)

    sets_result = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name not in ALLOWED_IMPORTS:
                    bad(node, f"import {a.name} is not allowed (only cadquery and math)")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level or mod not in ALLOWED_IMPORTS:
                bad(node, f"from {mod or '.'} import is not allowed (only cadquery and math)")
            for a in node.names:
                if a.name == "*" or a.name.startswith("_") or a.name in BAD_ATTRS:
                    bad(node, f"from {mod} import {a.name} is not allowed")
        elif isinstance(node, ast.Name):
            if node.id in BAD_NAMES or node.id.startswith("__"):
                bad(node, f"'{node.id}' is not allowed")
            if node.id == "result" and isinstance(node.ctx, ast.Store):
                sets_result = True
            if node.id in ("cq", "math", "H") and isinstance(node.ctx, ast.Store):
                bad(node, f"changing '{node.id}' is not allowed")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                bad(node, f"attribute '.{node.attr}' starting with '_' is not allowed")
            elif node.attr in BAD_ATTRS:
                bad(node, f"'.{node.attr}' is not allowed (Hoola's runner does export / import itself)")
        elif isinstance(node, ast.keyword) and node.arg and node.arg.startswith("_"):
            bad(node, f"'{node.arg}=' is not allowed")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bad(node, "global / nonlocal is not allowed")    # runaway loops: the sandbox's time limit
    if not sets_result and not out:
        out.append("set `result = ...` (cadquery Workplane / Shape) at the end of the script")
    return out


def check(code: str) -> None:
    p = problems(code)
    if p:
        raise GuardError(p)
