"""python -m app.dockit check   (D0: every document engine on this server, each with one real timed run)"""
from __future__ import annotations

import json
import sys

from . import health


def main(argv: list[str]) -> int:
    if not argv or argv[0] != "check":
        print(__doc__)
        return 2
    rep = health.check()
    print("\n".join(health.lines(rep)))
    if "--json" in argv:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0 if rep["core_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
