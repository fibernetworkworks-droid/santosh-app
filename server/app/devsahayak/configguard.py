"""v0.999 CONFIG PROTECTION, from ECC's config-protection hook (affaan-m/ECC, MIT; idea only, Hoola's own code).

A coding model that cannot make the linter, the type checker or the tests pass is tempted to loosen their settings
instead: turn a rule off, add an ignore, drop strict mode, lower a coverage bar, skip a folder. ECC blocks edits to those
files and steers the agent to fix the code. Hoola Code does the same:
- files that ARE such settings (eslint, prettier, biome, stylelint, ruff, flake8, mypy, pylint, pytest, jest, vitest,
  coverage, rubocop, golangci, phpstan, psalm, swiftlint, detekt, clang-tidy, checkstyle, tsconfig, their ignore files);
- the settings parts of shared files (pyproject.toml [tool.ruff / mypy / pytest / black / isort / pylint / coverage /
  pyright], setup.cfg / tox.ini [flake8 / mypy / tool:pytest / coverage / pylint], package.json eslintConfig /
  prettier / jest / stylelint, Cargo.toml [lints]).
A change there is refused, unless her own words this session ask about those settings (then it is her change). Creating
a new settings file is allowed (nothing is loosened). Switch: `dev_config_protect` (default on).
"""
from __future__ import annotations

import json
import re
from typing import Any

WHOLE = re.compile(r"(?i)(^|/)(\.eslintrc(\.[\w]+)?|eslint\.config\.[cm]?[jt]s|\.eslintignore|\.prettierrc(\.[\w]+)?|"
                   r"prettier\.config\.[cm]?[jt]s|\.prettierignore|biome\.jsonc?|\.stylelintrc(\.[\w]+)?|"
                   r"stylelint\.config\.[cm]?[jt]s|\.stylelintignore|ruff\.toml|\.ruff\.toml|\.flake8|mypy\.ini|\.mypy\.ini|"
                   r"pytest\.ini|\.pylintrc|pylintrc|\.coveragerc|codecov\.ya?ml|jest\.config\.[cm]?[jt]s|"
                   r"vitest\.config\.[cm]?[jt]s|\.rubocop\.ya?ml|\.golangci\.ya?ml|phpstan\.neon(\.dist)?|psalm\.xml|"
                   r"\.swiftlint\.ya?ml|detekt\.ya?ml|\.clang-tidy|checkstyle[\w-]*\.xml|tsconfig(\.[\w-]+)?\.json|"
                   r"tslint\.json|clippy\.toml|\.markdownlint(\.[\w]+)?|analysis_options\.yaml)$")
INI_SECTIONS = {
    "pyproject.toml": re.compile(r"^\[tool\.(ruff|mypy|pytest|black|isort|pylint|coverage|pyright|flake8)\b"),
    "setup.cfg": re.compile(r"^\[(flake8|mypy[^\]]*|tool:pytest|coverage:[^\]]*|pylint[^\]]*|isort|pycodestyle)\]"),
    "tox.ini": re.compile(r"^\[(flake8|pytest|coverage:[^\]]*|isort|pycodestyle)\]"),
    "Cargo.toml": re.compile(r"^\[(workspace\.)?lints\b"),
}
PKG_KEYS = ("eslintConfig", "prettier", "jest", "stylelint", "eslintIgnore")
ASKED = re.compile(r"(?i)\b(lint\w*|eslint|prettier|biome|stylelint|ruff|flake8|mypy|pylint|pyright|pytest\.ini|jest|"
                   r"vitest|coverage|rubocop|golangci|phpstan|psalm|swiftlint|detekt|clang-tidy|checkstyle|tsconfig|"
                   r"strict(ness| mode)?|formatter|formatting rules?|config(uration)? (file|settings)|tooling|"
                   r"type.?check\w*|analysis_options|clippy)\b")


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def on() -> bool:
    return bool(_set("dev_config_protect", True))


def _sections(text: str, head: re.Pattern) -> str:
    """Only the lines inside the protected [sections] of an ini / toml file."""
    out, keep = [], False
    for ln in (text or "").splitlines():
        s = ln.strip()
        if s.startswith("["):
            keep = bool(head.match(s))
        if keep:
            out.append(ln.rstrip())
    return "\n".join(out)


def _pkg(text: str) -> str:
    try:
        j = json.loads(text or "{}")
    except ValueError:
        return ""
    return json.dumps({k: j.get(k) for k in PKG_KEYS if isinstance(j, dict) and k in j}, sort_keys=True)


def touched(rel: str, old: str, new: str) -> str:
    """What kind of settings this change touches ('' = none)."""
    base = rel.rsplit("/", 1)[-1]
    if WHOLE.search(rel):
        return "" if old == new else base
    if base in INI_SECTIONS:
        head = INI_SECTIONS[base]
        return "" if _sections(old, head) == _sections(new, head) else f"the {base} settings sections"
    if base == "package.json" and _pkg(old) != _pkg(new):
        return "the lint / format / test settings in package.json"
    return ""


def check(rel: str, old: str, new: str, her_words: str) -> str:
    if not on():
        return ""
    what = touched(rel, old, new)
    if not what or ASKED.search(her_words or ""):
        return ""
    return (f"Refused: {rel} - {what} - holds this repo's lint / format / type-check / test settings (adapted from "
            "ECC's config protection). Loosening them to make a check pass hides the problem: fix the code instead. If "
            "the settings really must change for her request, do not change them yourself - say what and why, and ask her "
            "ONE question in done.")
