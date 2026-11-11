"""Generate the BYOX catalogue from codecrafters-io/build-your-own-x's README.

The repo is ONE README: a curated index of tutorials hosted elsewhere (CC0 for the list; each
tutorial belongs to its own author). We take only the INDEX - category, language, title, url -
and never the tutorial text. Deterministic, no network, no model: run it again on the same
README and the JSON is byte-identical.

    python scripts/gen_byox_catalogue.py <path-to-README.md> <commit-sha>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HEAD_RE = re.compile(r"^####\s+(?:Build your own\s+)?`?([^`\n]+?)`?\s*$")
# * [**Lang**: _Title_](url)   /   * [**Lang**: Title](url)
LINK_RE = re.compile(
    r"^\*\s+\[\s*\*\*(?P<lang>[^*]+?)\*\*\s*:\s*_?(?P<title>.*?)_?\s*\]\(\s*(?P<url>[^)\s]+)\s*\)"
    r"(?P<tail>.*)$"
)


def parse(readme: str) -> list[dict]:
    rows: list[dict] = []
    category = ""
    for raw in readme.splitlines():
        line = raw.rstrip()
        h = HEAD_RE.match(line)
        if h:
            category = h.group(1).strip()
            continue
        if not category:
            continue
        m = LINK_RE.match(line)
        if not m:
            continue
        title = m.group("title").strip().rstrip("_").strip()
        tail = m.group("tail") or ""
        rows.append({
            "category": category,
            "lang": m.group("lang").strip(),
            "title": title,
            "url": m.group("url").strip(),
            "video": "[video]" in tail or "[video]" in line,
            "pdf": "[pdf]" in tail,
        })
    return rows


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    readme = Path(sys.argv[1]).read_text(encoding="utf-8")
    commit = sys.argv[2]
    rows = parse(readme)
    cats: dict[str, int] = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    out = {
        "source": "github.com/codecrafters-io/build-your-own-x",
        "commit": commit,
        "licence": "CC0-1.0 (the INDEX only; each tutorial is its author's own work)",
        "counts": {"tutorials": len(rows), "categories": len(cats),
                   "videos": sum(1 for r in rows if r["video"])},
        "categories": [{"name": k, "tutorials": v} for k, v in sorted(cats.items())],
        "tutorials": rows,
    }
    dest = Path(__file__).resolve().parent.parent / "app" / "coder" / "byox_catalogue.json"
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=False) + "\n",
                    encoding="utf-8")
    print(f"{len(rows)} tutorials, {len(cats)} categories -> {dest}")
    for k, v in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {v:3d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
