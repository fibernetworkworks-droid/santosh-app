#!/usr/bin/env python3
"""v0.681.0 version ritual, round 2 - the LEADS ENGINE re-merged onto their v0.680.0 tip.

Round 1 (ritual_0672.py) swept the tree to 0.672.0/+678; then the dev chain pushed
v0.672.0-v0.680.0 and this merge re-lands the engine as v0.681.0/+680 (registry stays
614 = their 608 + our six leads tools). Sweeps:

  1. tests: pubspec pins ("0.680.0+679"/"0.672.0+678"/"0.671.0+677"/"0.545.0+568" -> "0.681.0+680"),
     then bare version pins ("0.680.0"/"0.672.0"/"0.671.0"/"0.545.0" -> "0.681.0")
  2. tests: registry count pins == 608 -> == 614 (len(TOOLS) and len(tools.TOOLS) forms)
  3. static console stamps: v2.html + webstudio.html -> "?v=0.681.0"
  4. leads provenance parser stamps: v0.672.0-* -> v0.681.0-* (source + tests)

NOT touched: main.py's story narrative, rules.py phase comments, HISTORY.md, CLAUDE.md body.
"""
from __future__ import annotations

import glob

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html"]

PUBSPEC_OLD = ["0.680.0+679", "0.672.0+678", "0.671.0+677", "0.545.0+568"]
VERSION_OLD = ["0.680.0", "0.672.0", "0.671.0", "0.545.0"]
REGISTRY_OLD = [("len(TOOLS) == 608", "len(TOOLS) == 614"),
                ("len(tools.TOOLS) == 608", "len(tools.TOOLS) == 614")]
PARSER_OLD = ["v0.672.0-gm1", "v0.672.0-im1", "v0.672.0-pl1", "v0.672.0-vd1",
              "v0.672.0-en1", "v0.672.0-her1"]


def sweep(path: str, pairs: list[tuple[str, str]]) -> int:
    try:
        src = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, FileNotFoundError):
        return 0
    n = 0
    for old, new in pairs:
        c = src.count(old)
        if c:
            src = src.replace(old, new)
            n += c
    if n:
        open(path, "w", encoding="utf-8").write(src)
    return n


def main() -> None:
    total = {"test_versions": 0, "registry": 0, "stamps": 0, "parsers": 0}
    files = 0
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [(o, "0.681.0+680") for o in PUBSPEC_OLD])
        n += sweep(f, [(o, "0.681.0") for o in VERSION_OLD])
        n += sweep(f, REGISTRY_OLD)
        n += sweep(f, [(o, o.replace("v0.672.0-", "v0.681.0-")) for o in PARSER_OLD])
        if n:
            total["test_versions"] += n
            files += 1
    for f in STATICS:
        n = sweep(f, [("?v=0.680.0", "?v=0.681.0"), ("?v=0.672.0", "?v=0.681.0")])
        if n:
            total["stamps"] += n
            files += 1
    for f in sorted(glob.glob(f"{ROOT}/app/leads/*.py")):
        n = sweep(f, [(o, o.replace("v0.672.0-", "v0.681.0-")) for o in PARSER_OLD])
        if n:
            total["parsers"] += n
            files += 1
    print("ritual_0681:", total, "| files touched:", files)


if __name__ == "__main__":
    main()
