#!/usr/bin/env python3
"""v0.672.0 version ritual - the LEADS ENGINE rebuild lands on their v0.671.0 tip.

Sweeps (source of truth: the merge brought OUR pins as 0.545.0/562 and THEIR pins as
0.671.0/608; the merged tree is ONE release 0.672.0/+678 with registry 614 = their 608
+ our six leads tools):

  1. tests: pubspec pins first ("0.671.0+677"/"0.545.0+568" -> "0.672.0+678"),
     then bare version pins ("0.671.0"/"0.545.0" -> "0.672.0")
  2. tests: registry count pins len(TOOLS) == 608 / == 562 -> == 614
  3. static console stamps: v2.html + webstudio.html "?v=0.671.0" -> "?v=0.672.0"
  4. leads provenance parser stamps: v0.543.0-gm1 / v0.544.0-vd1 (source + tests) ->
     v0.672.0-gm1 / v0.672.0-vd1 (the parsers ship in this release)

NOT touched (narrative history, said where a reader needs it): main.py's story chain
mentions of older releases, rules.py phase comments, HISTORY.md, CLAUDE.md body, test
docstrings that only NAME an old release.
"""
from __future__ import annotations

import glob
import re

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html"]

PUBSPEC_PAIRS = [("0.671.0+677", "0.672.0+678"), ("0.545.0+568", "0.672.0+678")]
VERSION_PAIRS = [("0.671.0", "0.672.0"), ("0.545.0", "0.672.0")]
REGISTRY_PAIRS = [("len(TOOLS) == 608", "len(TOOLS) == 614"), ("len(TOOLS) == 562", "len(TOOLS) == 614")]
STAMP_PAIRS = [("?v=0.671.0", "?v=0.672.0")]
PARSER_PAIRS = [("v0.543.0-gm1", "v0.672.0-gm1"), ("v0.544.0-vd1", "v0.672.0-vd1"),
                ("v0.540.0-hd1", "v0.672.0-hd1"), ("v0.541.0-im1", "v0.672.0-im1"),
                ("v0.541.0-pl1", "v0.672.0-pl1")]


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
    files_touched = set()
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, PUBSPEC_PAIRS)
        n += sweep(f, VERSION_PAIRS)
        if n:
            total["test_versions"] += n
            files_touched.add(f)
        r = sweep(f, REGISTRY_PAIRS)
        if r:
            total["registry"] += r
            files_touched.add(f)
        p = sweep(f, PARSER_PAIRS)
        if p:
            total["parsers"] += p
            files_touched.add(f)
    for f in STATICS:
        n = sweep(f, STAMP_PAIRS)
        if n:
            total["stamps"] += n
            files_touched.add(f)
    # leads SOURCE parser stamps (provenance stamps written into rows)
    for f in sorted(glob.glob(f"{ROOT}/app/leads/*.py")):
        p = sweep(f, PARSER_PAIRS)
        if p:
            total["parsers"] += p
            files_touched.add(f)
    print("ritual_0672:", total, "| files touched:", len(files_touched))


if __name__ == "__main__":
    main()
