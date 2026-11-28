"""Where the three vendored engines live, what each one can draw, and whether the copy is whole.

The type lists are READ from each engine's own SKILL.md (archify's "Type router", diagram-design's "Visual-type guide"),
so a newer upstream copy with a new type shows up without a code change here."""
from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor"
ARCHIFY = VENDOR / "archify"
ARCHIFY_PR = VENDOR / "archify-pr"
DD = VENDOR / "diagram-design"
DRAWIO_AI = VENDOR / "drawio-ai"

ENGINES = ("archify", "diagram-design", "drawio-ai")

# files each copy must have to count as whole (the entry points Hoola calls)
NEEDED: dict[str, tuple[str, ...]] = {
    "archify": ("SKILL.md", "LICENSE", "LICENSE-MIT", "NOTICE", "bin/archify.mjs", "bin/finalize.mjs",
                "schemas/architecture.schema.json", "examples/web-app.architecture.json", "package.json"),
    "diagram-design": ("SKILL.md", "LICENSE", "scripts/self_check.py", "scripts/verify_geometry.py",
                       "scripts/export_png.py", "references/style-guide.md", "assets/template.html"),
    "drawio-ai": ("LICENSE", "src/drawio-version.json", "src/xml-validation.ts", "drawio-files.txt", "package.json"),
}


def _files(engine: str) -> list[Path]:
    base = path_of(engine)
    roots = [base] + ([ARCHIFY_PR] if engine == "archify" else [])
    out = []
    for r in roots:
        for f in r.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts and not f.name.endswith(".pyc"):
                out.append(f)
    return sorted(out)


def tree_hash(engine: str) -> str:
    """One SHA-256 over every vendored file of this engine (path + bytes) - VENDOR.json keeps the value taken when it was
    copied, so a hand edit to a vendored file is caught by the tests."""
    import hashlib
    h = hashlib.sha256()
    for f in _files(engine):
        h.update(f.relative_to(VENDOR).as_posix().encode() + b"\0")
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def path_of(engine: str) -> Path:
    return {"archify": ARCHIFY, "diagram-design": DD, "drawio-ai": DRAWIO_AI}[engine]


@functools.lru_cache(maxsize=1)
def manifest() -> dict[str, Any]:
    return json.loads((ROOT / "VENDOR.json").read_text("utf-8"))


def missing(engine: str) -> list[str]:
    """The entry-point files this copy lacks ([] = whole)."""
    base = path_of(engine)
    return [f for f in NEEDED[engine] if not (base / f).is_file()]


def status() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for e in ENGINES:
        m = manifest().get(e, {})
        out[e] = {"commit": m.get("commit", ""), "version": m.get("version", ""), "license": m.get("license", ""),
                  "missing": missing(e), "whole": not missing(e)}
    return out


def _rows(text: str, heading: str) -> list[list[str]]:
    """The cells of the first markdown table after `heading`."""
    i = text.find(heading)
    if i < 0:
        return []
    rows: list[list[str]] = []
    started = False
    for line in text[i:].splitlines()[1:]:
        s = line.strip()
        if s.startswith("|"):
            started = True
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            rows.append(cells)
        elif started:
            break
    return rows[1:] if rows else []      # drop the header row


@functools.lru_cache(maxsize=1)
def archify_types() -> list[dict[str, str]]:
    """[{type, use, schema, example}] from archify's Type router."""
    out = []
    for cells in _rows((ARCHIFY / "SKILL.md").read_text("utf-8"), "## Type router"):
        if len(cells) < 3:
            continue
        m = re.search(r"`([a-z][a-z-]*)`", cells[0])
        if not m:
            continue
        schema = re.search(r"`(schemas/[^`]+)`", cells[2])
        example = re.search(r"`(examples/[^`]+)`", cells[3] if len(cells) > 3 else "")
        out.append({"type": m.group(1), "use": re.sub(r"\s+", " ", cells[1]).strip(),
                    "schema": schema.group(1) if schema else "", "example": example.group(1) if example else ""})
    return out


@functools.lru_cache(maxsize=1)
def dd_types() -> list[dict[str, str]]:
    """[{type, name, use, reference}] from diagram-design's Visual-type guide (52)."""
    out = []
    for cells in _rows((DD / "SKILL.md").read_text("utf-8"), "### Visual-type guide"):
        if len(cells) < 3:
            continue
        name = re.search(r"\*\*([^*]+)\*\*", cells[1])
        ref = re.search(r"\((references/type-([a-z0-9-]+)\.md)\)", cells[2])
        if not (name and ref):
            continue
        out.append({"type": ref.group(2), "name": name.group(1).strip(), "use": re.sub(r"\s+", " ", cells[0]).strip(),
                    "reference": ref.group(1)})
    return out


def dd_examples() -> list[Path]:
    return sorted((DD / "assets").glob("example-*.html"))


def archify_examples() -> list[tuple[str, Path]]:
    """(type, file) for every archify example whose type is a native diagram type."""
    kinds = {t["type"] for t in archify_types()}
    out = []
    for f in sorted((ARCHIFY / "examples").glob("*.json")):
        parts = f.name.split(".")
        if len(parts) >= 3 and parts[-2] in kinds:
            out.append((parts[-2], f))
    return out


def drawio_pin() -> dict[str, str]:
    """{version, sha256, downloadUrl} of the draw.io editor release next-ai-draw-io pins."""
    return json.loads((DRAWIO_AI / "src" / "drawio-version.json").read_text("utf-8"))
