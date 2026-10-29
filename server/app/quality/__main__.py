"""python -m app.quality [--live] [--judge] [--label "..."] | compare <before.json> <after.json>"""
from __future__ import annotations

import asyncio
import json
import sys

from . import run as R


def main(argv: list[str]) -> int:
    if argv and argv[0] == "compare":
        if len(argv) != 3:
            print("usage: python -m app.quality compare <before.json> <after.json>")
            return 2
        v = R.compare(R.load(argv[1]), R.load(argv[2]))
        for row in v["rows"]:
            print(f"  {row['metric']:>18}: {row['before']} -> {row['after']}  ({row['delta']:+}) {row['verdict']}")
        for f in v["flags"]:
            print(f"  {f['flag']:>18}: {f['before']} -> {f['after']}  {f['verdict']}")
        print("\n" + v["say"])
        return 0
    live = "--live" in argv
    judge = "--judge" in argv
    label = ""
    if "--label" in argv:
        i = argv.index("--label")
        label = argv[i + 1] if len(argv) > i + 1 else ""
    snap = asyncio.run(R.snapshot(live=live, judge=judge, label=label))
    print("\n".join(R.lines(snap)))
    print(f"\n  saved: {snap['file']}")
    if "--json" in argv:
        print(json.dumps(snap, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
