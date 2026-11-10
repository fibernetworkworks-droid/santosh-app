#!/usr/bin/env python3
"""v0.684.0 version ritual, round 3 - the LEADS ENGINE re-landed on their v0.681.0 KALA MANCH tip.

Round 2 swept to 0.681.0/+680; the dev chain then shipped v0.681.0 KALA MANCH (registry
608 -> 609, one tool), so the engine lands as v0.684.0/+681 with registry 615 = their 609
+ our six leads tools. Sweeps:

  1. tests: pubspec pins -> "0.684.0+681"; bare version pins -> "0.684.0"
  2. tests: registry pins == 609 -> == 615 (len(TOOLS) and len(tools.TOOLS) forms)
  3. static console stamps -> "?v=0.684.0"
  4. leads provenance parser stamps v0.681.0-* / v0.672.0-* -> v0.684.0-* (source + tests)

NOT touched: main.py story narrative, rules.py phase comments, HISTORY.md, CLAUDE.md body.
"""
from __future__ import annotations

import glob

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html"]

PUBSPEC_OLD = ["0.683.0+682", "0.682.0+681", "0.681.0+680", "0.680.0+679", "0.672.0+678", "0.671.0+677", "0.545.0+568"]
VERSION_OLD = ["0.683.0", "0.682.0", "0.681.0", "0.680.0", "0.672.0", "0.671.0", "0.545.0"]
REGISTRY_OLD = [("len(TOOLS) == 609", "len(TOOLS) == 615"),
                ("len(tools.TOOLS) == 609", "len(tools.TOOLS) == 615"),
                ("len(TOOLS) == 608", "len(TOOLS) == 615"),
                ("len(tools.TOOLS) == 608", "len(tools.TOOLS) == 615")]
PARSER_OLD = ["v0.681.0-gm1", "v0.681.0-im1", "v0.681.0-pl1", "v0.681.0-vd1",
              "v0.681.0-en1", "v0.681.0-her1",
              "v0.672.0-gm1", "v0.672.0-im1", "v0.672.0-pl1", "v0.672.0-vd1",
              "v0.672.0-en1", "v0.672.0-her1"]
PREFIX_OLD = ['startswith("v0.681")', 'startswith("v0.672")']


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
    total = {"tests": 0, "stamps": 0, "parsers": 0, "prefix": 0}
    files = 0
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [(o, "0.684.0+681") for o in PUBSPEC_OLD])
        n += sweep(f, [(o, "0.684.0") for o in VERSION_OLD])
        n += sweep(f, REGISTRY_OLD)
        n += sweep(f, [(o, "v0.684.0" + o[7:]) for o in PARSER_OLD])
        n += sweep(f, [(o, 'startswith("v0.682")') for o in PREFIX_OLD])
        if n:
            total["tests"] += n
            files += 1
    for f in STATICS:
        n = sweep(f, [("?v=0.681.0", "?v=0.684.0"), ("?v=0.680.0", "?v=0.684.0"),
                      ("?v=0.672.0", "?v=0.684.0")])
        if n:
            total["stamps"] += n
            files += 1
    for f in sorted(glob.glob(f"{ROOT}/app/leads/*.py")):
        n = sweep(f, [(o, "v0.684.0" + o[7:]) for o in PARSER_OLD])
        if n:
            total["parsers"] += n
            files += 1
    print("ritual_0684:", total, "| files touched:", files)


if __name__ == "__main__":
    main()
