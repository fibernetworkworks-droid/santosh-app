"""v0.999.334 Add one DESIGN.md from another MIT repository to the Web Studio design catalog.

    python tools/designmd_add.py <DESIGN.md> --id ant-design --name "Enterprise console" --src ant.design \
        --brand "Ant Design" --cat saas --line "..." --repo github.com/ant-design/ant-design --commit "c046700 2026-11-28" \
        --licence <LICENSE file>

The look keeps where it came from (`from`: repo, licence, commit) and a re-run replaces it in place. tools/designmd_build.py
keeps every look that carries `from` when it rebuilds the awesome-design-md part, and LICENSE.txt gets the repo's licence.
Nothing is fetched from the network here.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "app" / "site" / "designmd_lib"


def add(md: str, lid: str, name: str, src: str, brand: str, cat: str, line: str, repo: str, commit: str,
        licence: str = "", upper: bool = False) -> int:
    p = OUT / "looks.json.gz"
    data = json.loads(gzip.decompress(p.read_bytes()))
    text = Path(md).read_text(encoding="utf-8")
    if not text.lstrip().startswith("---"):
        raise SystemExit("that file has no DESIGN.md front matter")
    entry = {"id": lid, "name": name, "src": src, "brand": brand, "cat": cat, "line": line[:140], "upper": upper,
             "text": text, "new": True, "from": {"repo": repo, "licence": "MIT", "commit": commit}}
    looks = [x for x in data["looks"] if x["id"] != lid]
    if any(x["name"] == name for x in looks):
        raise SystemExit(f"another look is already named {name}")
    looks.append(entry)
    data["looks"] = looks
    p.write_bytes(gzip.compress(json.dumps(data, ensure_ascii=False).encode(), 9, mtime=0))
    if licence:
        lic = OUT / "LICENSE.txt"
        head = f"\n\n---------------------------------------------------------------- {repo}\n"
        body = lic.read_text(encoding="utf-8")
        if repo not in body:
            lic.write_text(body.rstrip() + head + f"The {name} look ({src}) comes from {repo} ({commit}).\n\n"
                           + Path(licence).read_text(encoding="utf-8"), encoding="utf-8")
    return len(looks)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("md")
    for k in ("id", "name", "src", "brand", "cat", "line", "repo", "commit", "licence"):
        a.add_argument("--" + k, default="")
    a.add_argument("--upper", action="store_true")
    o = a.parse_args()
    n = add(o.md, o.id, o.name, o.src, o.brand, o.cat, o.line, o.repo, o.commit, o.licence, o.upper)
    print(f"{n} looks in the catalog")
