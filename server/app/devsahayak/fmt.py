"""v0.999 FORMAT AFTER EDITS, OpenCode's formatter step (owner: "GO 1 TO 5").

OpenCode runs the project's formatter on a file the agent just wrote, so what lands is what the project's own tools would
have produced, and the model is shown the formatted result. Hoola Code does the same, carefully:

- ONLY a formatter the repo itself declares: prettier / biome in package.json or their config files, ruff format or black
  configured in pyproject.toml / ruff.toml, gofmt for Go, rustfmt for a Cargo project, clang-format with a .clang-format.
  A repo that declares none is never reformatted.
- In the session's LOCKED BOX (no network), once per reply for every file the reply changed - never on the server.
  prettier / biome run only from the repo's own node_modules (`--no-install`), so nothing is downloaded.
- A formatter that would rewrite most of a file that was not formatted before (over `dev_format_max_lines` changed lines) is
  put back: her pull request must not fill with unrelated layout changes. Hidden (secret) files and paths the coder may not
  write are never touched.
- The coder is told which files changed and a short diff, so its next edit copies the formatted text.
"""
from __future__ import annotations

import difflib
import json
import re
import uuid
from pathlib import Path
from typing import Any

STATS = {"runs": 0, "formatted": 0, "put_back": 0}

JS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".json", ".jsonc", ".css", ".scss", ".less", ".html",
      ".vue", ".svelte", ".md", ".mdx", ".yml", ".yaml", ".graphql")
PRETTIER_CFG = (".prettierrc", ".prettierrc.json", ".prettierrc.yaml", ".prettierrc.yml", ".prettierrc.js", ".prettierrc.cjs",
                ".prettierrc.mjs", ".prettierrc.toml", "prettier.config.js", "prettier.config.cjs", "prettier.config.mjs")


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def on() -> bool:
    return bool(_set("dev_auto_format", True))


def _read(p: Path, limit: int = 400_000) -> str:
    try:
        return p.read_text("utf-8", errors="replace")[:limit] if p.is_file() and not p.is_symlink() else ""
    except OSError:
        return ""


def declared(repo: Path) -> dict[str, dict[str, Any]]:
    """The formatters this repo declares, by name: {name: {exts, shell}} (shell gets the files at the end)."""
    out: dict[str, dict[str, Any]] = {}
    pkg = _read(repo / "package.json")
    try:
        pj = json.loads(pkg) if pkg else {}
    except ValueError:
        pj = {}
    deps = {**(pj.get("dependencies") or {}), **(pj.get("devDependencies") or {})} if isinstance(pj, dict) else {}
    if (repo / "biome.json").is_file() or (repo / "biome.jsonc").is_file() or "@biomejs/biome" in deps:
        out["biome"] = {"exts": JS, "shell": "[ -x node_modules/.bin/biome ] && node_modules/.bin/biome format --write"}
    elif "prettier" in deps or any((repo / c).is_file() for c in PRETTIER_CFG) or (isinstance(pj, dict) and "prettier" in pj):
        out["prettier"] = {"exts": JS, "shell": "[ -x node_modules/.bin/prettier ] && node_modules/.bin/prettier --write --log-level warn"}
    py = _read(repo / "pyproject.toml")
    if (repo / "ruff.toml").is_file() or (repo / ".ruff.toml").is_file() or re.search(r"(?m)^\[tool\.ruff(\.format)?\]", py):
        out["ruff"] = {"exts": (".py", ".pyi"), "shell": "command -v ruff >/dev/null && ruff format -q"}
    elif re.search(r"(?m)^\[tool\.black\]", py):
        out["black"] = {"exts": (".py", ".pyi"), "shell": "command -v black >/dev/null && black -q"}
    if (repo / "go.mod").is_file():
        out["gofmt"] = {"exts": (".go",), "shell": "command -v gofmt >/dev/null && gofmt -w"}
    cargo = _read(repo / "Cargo.toml")
    if cargo:
        m = re.search(r'(?m)^\s*edition\s*=\s*"(\d{4})"', cargo)
        out["rustfmt"] = {"exts": (".rs",), "shell": "command -v rustfmt >/dev/null && rustfmt --edition " + (m.group(1) if m else "2021")}
    if (repo / ".clang-format").is_file():
        out["clang-format"] = {"exts": (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh"), "shell": "command -v clang-format >/dev/null && clang-format -i"}
    return out


def _q(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def _exec(tools: Any, shell: str, timeout: int) -> dict[str, Any]:
    """One box run (the tests run it straight on this machine)."""
    img, note = tools._image()
    if not img:
        return {"rc": 127, "out": note}
    from ..devlab import box
    tools.bash_runs = getattr(tools, "bash_runs", 0) + 1
    return box.run_in(img, str(tools.s.repo), f"cd {box.WORK}; {shell}", timeout=timeout, network=False, env=tools.env or None)


def after_edits(tools: Any, paths: list[str]) -> tuple[str, list[str]]:
    """Format what this reply changed. Returns (the note for the coder, the files that changed)."""
    if not on() or not paths:
        return "", []
    repo = tools.s.repo
    fmts = declared(repo)
    if not fmts:
        return "", []
    from . import rules as R
    hidden = set(getattr(tools, "hidden", set()) or set())
    groups: dict[str, list[str]] = {}
    for p in dict.fromkeys(paths):
        f = tools.s.real(p) if p else None
        if not p or f is None or not f.is_file() or p in hidden or R.path_problem(p, getattr(tools, "allow_workflows", False)):
            continue
        for name, spec in fmts.items():
            if p.lower().endswith(spec["exts"]):
                groups.setdefault(name, []).append(p)
                break
    if not groups:
        return "", []
    before = {p: _read(repo / p) for fs in groups.values() for p in fs}
    mark = "HOOLA_FMT_" + uuid.uuid4().hex[:8]
    shell = "; ".join(f"({fmts[n]['shell']} {' '.join(_q('./' + x) for x in fs)}) >/dev/null 2>&1 || echo {mark} {n}"
                      for n, fs in groups.items())
    STATS["runs"] += 1
    try:
        r = _exec(tools, shell, int(_set("dev_format_s", 90) or 90))
    except Exception:  # noqa: BLE001 - formatting never stops the work
        return "", []
    missing = sorted(set(re.findall(rf"{mark} (\S+)", str(r.get("out") or ""))))
    cap = int(_set("dev_format_max_lines", 120) or 120)
    changed, put_back, diffs = [], [], []
    for p, old in before.items():
        new = _read(repo / p)
        if new == old or not new:
            continue
        d = [x for x in difflib.unified_diff(old.splitlines(), new.splitlines(), f"a/{p}", f"b/{p}", n=0, lineterm="")]
        n = sum(1 for x in d if x[:1] in "+-" and not x.startswith(("+++", "---")))
        if n > cap:                                        # it was not formatted before: do not reformat the whole file
            (repo / p).write_text(old, "utf-8")
            put_back.append(p)
            STATS["put_back"] += 1
            continue
        changed.append(p)
        diffs.append("\n".join(d[:40]) + ("\n..." if len(d) > 40 else ""))
    STATS["formatted"] += len(changed)
    if not changed and not put_back:
        return "", []
    parts = []
    if changed:
        parts.append(f"The repo's formatter ({', '.join(n for n, fs in groups.items() if set(fs) & set(changed))}) changed "
                     f"{', '.join(changed)} after your edit - copy from the formatted text next time:\n" + "\n".join(diffs)[:6000])
    if put_back:
        parts.append(f"Not formatted (the formatter would rewrite most of it, so the file was left as you wrote it): {', '.join(put_back)}.")
    if missing:
        parts.append(f"(Formatter not installed in the box, skipped: {', '.join(missing)}.)")
    return "<formatted>\n" + "\n".join(parts) + "\n</formatted>", changed
