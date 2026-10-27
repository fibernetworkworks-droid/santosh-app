"""Code check for the Blender scripts Hoola writes (or the chat model passes with action=run_code).

The official Blender Lab MCP server says plainly that it runs model code "without any guards". Hoola does not: before a
script ever reaches Blender it is parsed and walked here, and anything that could touch files, the network, other
programs, Blender's own settings / add-ons / startup scripts or Python's internals is refused with a plain reason the
model can fix. The runner then executes it again with a cut-down set of builtins and an import gate (defence in depth),
and the process itself has no network and no secrets (sandbox.py).

Allowed: building and changing the scene - bpy.data meshes / objects / materials / node trees / modifiers / curves /
text, bmesh, mathutils, math, random, colorsys, itertools, functools, collections, statistics - plus Hoola's `H`
helpers (materials, primitives, her photos as textures, fonts, bevel / smooth / apply). Rendering, saving and exporting
are done by the runner after the script, never by the script.
"""
from __future__ import annotations

import ast
from typing import Any

MAX_CHARS = 60_000

ALLOWED_IMPORTS = {"bpy", "bmesh", "mathutils", "math", "random", "colorsys", "itertools", "functools", "collections",
                   "statistics", "mathutils.noise", "mathutils.geometry", "mathutils.bvhtree", "mathutils.kdtree",
                   "bmesh.ops", "bmesh.types", "bmesh.utils", "bmesh.geometry"}

BAD_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "breakpoint", "input", "help",
             "exit", "quit", "memoryview", "delattr", "__builtins__", "__loader__", "__spec__", "classmethod",
             "staticmethod", "super", "object", "type"}

# attribute names that read / write files, run code, change Blender itself or reach its internals
BAD_ATTRS = {
    # files
    "filepath", "filepath_raw", "filepath_from_user", "directory", "filename", "load", "save", "save_render",
    "save_as", "pack", "unpack", "reload", "write", "libraries", "abspath", "cache_file", "cache_files",
    "sound", "sounds", "movieclips", "fonts",
    # code that runs by itself
    "texts", "expression", "driver_namespace", "handlers", "timers", "msgbus", "use_scripts_auto_execute",
    "register_class", "unregister_class", "register_module", "execfile", "script_paths", "script_path_user",
    "user_resource", "modules", "app_template",
    # Blender itself
    "preferences", "addons", "addon_utils", "window_manager", "keyconfigs", "utils", "extensions",
    # python internals
    "f_globals", "f_locals", "f_back", "gi_frame", "gi_code", "co_code", "func_globals", "tb_frame",
}

# bpy.ops namespaces the script may use (scene building only). render / export / import / wm / script / file / image
# / text / preferences ... are not here: the runner does those itself.
OPS_OK = {"mesh", "object", "curve", "curves", "material", "transform", "uv", "node", "surface", "armature", "pose",
          "rigidbody", "geometry", "collection", "font", "anim", "constraint", "texture", "world", "lattice", "mball",
          "particle", "poselib", "cloth"}

MAX_LOOP_HINT = 2_000_000


class GuardError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def _dotted(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def problems(code: str) -> list[str]:
    """Plain-word problems; [] = the script may run."""
    code = code or ""
    out: list[str] = []
    if not code.strip():
        return ["script khaali hai"]
    if len(code) > MAX_CHARS:
        return [f"script bahut lambi hai ({len(code)} > {MAX_CHARS} characters): chhoti likho, loops use karo"]
    try:
        tree = ast.parse(code, filename="hoola_scene.py")
    except SyntaxError as e:
        return [f"SyntaxError line {e.lineno}: {e.msg}"]

    def bad(node: ast.AST, why: str) -> None:
        line = getattr(node, "lineno", 0)
        msg = f"line {line}: {why}"
        if msg not in out:
            out.append(msg)

    # nodes that are the left part of a longer attribute chain (bpy in bpy.data, bpy.ops in bpy.ops.mesh.x ...)
    inner = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for node in ast.walk(tree):
        # bpy / bpy.ops / bpy.ops.<ns> never kept in a variable or passed around: otherwise `o = bpy.ops; o.wm...`
        # would hide what runs
        if isinstance(node, ast.Name) and node.id == "bpy" and id(node) not in inner \
                and not isinstance(getattr(node, "ctx", None), ast.Store):
            bad(node, "'bpy' akela variable / argument mein mat do; bpy.data... / bpy.ops.mesh... seedha likho")
        if isinstance(node, ast.Attribute):
            d = _dotted(node)
            if (d == "bpy.ops" or (d.startswith("bpy.ops.") and d.count(".") == 2)) and id(node) not in inner:
                bad(node, f"'{d}' ko variable mein mat rakho; poora op seedha likho (bpy.ops.mesh.primitive_cube_add())")
        if isinstance(node, ast.keyword) and node.arg and (node.arg in BAD_ATTRS or node.arg.startswith("_")):
            bad(node, f"'{node.arg}=' allowed nahi (files Hoola ka runner khud padhta / likhta hai)")
        if isinstance(node, ast.alias) and node.name == "bpy" and node.asname:
            bad(node, "import bpy as ... mat karo")
        if isinstance(node, (ast.Name)) and isinstance(node.ctx, ast.Store) and node.id in ("bpy", "H", "bmesh"):
            bad(node, f"'{node.id}' ko badalna allowed nahi")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name not in ALLOWED_IMPORTS:
                    bad(node, f"import {a.name} allowed nahi (sirf bpy, bmesh, mathutils, math, random, colorsys, "
                              "itertools, functools, collections, statistics)")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level or mod not in ALLOWED_IMPORTS:
                bad(node, f"from {mod or '.'} import allowed nahi")
            for a in node.names:
                if a.name == "*" or a.name.startswith("_") or a.name in BAD_ATTRS:
                    bad(node, f"from {mod} import {a.name} allowed nahi")
                if mod == "bpy" and a.name in ("ops", "utils", "app", "path"):
                    bad(node, f"from bpy import {a.name} mat karo; bpy.{a.name} seedha likho")
        elif isinstance(node, ast.Name):
            if node.id in BAD_NAMES:
                bad(node, f"'{node.id}' allowed nahi")
            elif node.id.startswith("__"):
                bad(node, f"'{node.id}' allowed nahi")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                bad(node, f"'_' se shuru hone wala attribute '.{node.attr}' allowed nahi")
            elif node.attr in BAD_ATTRS:
                bad(node, f"'.{node.attr}' allowed nahi (files / settings / code chalana Hoola ka runner khud karta hai)")
            d = _dotted(node)
            if d.startswith("bpy.ops."):
                ns = d.split(".")[2] if d.count(".") >= 2 else ""
                if ns and ns not in OPS_OK:
                    bad(node, f"bpy.ops.{ns} allowed nahi (render / save / export / import runner karta hai; "
                              f"scene banane wale ops hi: {', '.join(sorted(OPS_OK))})")
            elif d.startswith("bpy.app.") and d.split(".")[2] not in ("version", "version_string"):
                bad(node, f"{d} allowed nahi")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "__" in node.value:
                bad(node, "text mein '__' allowed nahi")
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else ""
            if name in ("getattr", "setattr", "hasattr"):
                if len(node.args) < 2 or not (isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)):
                    bad(node, f"{name}() ka doosra hissa seedha naam (string) hona chahiye")
                else:
                    a = node.args[1].value
                    if a.startswith("_") or a in BAD_ATTRS:
                        bad(node, f"{name}(..., '{a}') allowed nahi")
            if isinstance(fn, ast.Attribute) and fn.attr == "format" and isinstance(fn.value, ast.Constant) \
                    and "{" in str(fn.value.value) and "." in str(fn.value.value).split("{", 1)[1].split("}", 1)[0]:
                bad(node, "format() mein attribute padhna allowed nahi; f-string likho")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            pass
        elif isinstance(node, ast.While):
            if isinstance(node.test, ast.Constant) and node.test.value is True and \
                    not any(isinstance(n, ast.Break) for n in ast.walk(node)):
                bad(node, "while True bina break ke: kabhi khatam nahi hoga")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)):
            bad(node, "async allowed nahi")
    return out


def check(code: str) -> None:
    p = problems(code)
    if p:
        raise GuardError(p)


def summary(code: str) -> dict[str, Any]:
    """Small facts about a script for the card (lines, ops used)."""
    try:
        tree = ast.parse(code or "")
    except SyntaxError:
        return {"lines": len((code or "").splitlines())}
    ops = sorted({_dotted(n).split(".")[2] for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                  and _dotted(n).startswith("bpy.ops.") and _dotted(n).count(".") >= 2})
    return {"lines": len(code.splitlines()), "ops": ops[:12]}
