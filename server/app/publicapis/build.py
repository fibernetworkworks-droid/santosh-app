"""Turn the public-apis README (github.com/public-apis/public-apis, MIT) into Hoola's catalog.

  python -m app.publicapis.build /path/to/public-apis/README.md      (or no argument: fetch from GitHub)

Writes app/publicapis/catalog.json.gz: [{id, name, desc, cat, auth, https, cors, link, host}].
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

OUT = Path(__file__).with_name("catalog.json.gz")
SRC = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
_ROW = re.compile(r"^\|\s*\[(.+?)\]\((.+?)\)\s*\|(.*)$")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def parse(md: str) -> list[dict]:
    start = md.find("### Animals")
    md = md[start:] if start >= 0 else md
    cat, out, seen = None, [], set()
    for line in md.splitlines():
        if line.startswith("### "):
            cat = line[4:].strip()
            continue
        m = _ROW.match(line)
        if not (m and cat):
            continue
        cells = [c.strip().strip("`") for c in m.group(3).split("|")]
        if len(cells) < 4:
            continue
        name, link = m.group(1).strip(), m.group(2).strip()
        base = slug(f"{cat}-{name}")
        aid, n = base, 2
        while aid in seen:
            aid, n = f"{base}-{n}", n + 1
        seen.add(aid)
        auth = cells[1] if cells[1] not in ("", "No") else "none"
        out.append({"id": aid, "name": name, "desc": cells[0][:300], "cat": cat, "auth": auth,
                    "https": cells[2].lower() == "yes", "cors": cells[3].lower(), "link": link,
                    "host": (urlparse(link).hostname or "").lower()})
    return out


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        md = Path(argv[1]).read_text(encoding="utf-8")
    else:
        import httpx
        md = httpx.get(SRC, timeout=60).text
    rows = parse(md)
    if len(rows) < 500:
        print("too few rows, not writing", len(rows))
        return 1
    OUT.write_bytes(gzip.compress(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()))
    print(f"{len(rows)} APIs -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
