"""python -m app.quality [--live] [--judge] [--label "..."] | compare <before.json> <after.json>
   | tools [--live] [--fresh] [--limit N] [--brain claude|glm] [--label "..."]   (v0.245 tool-choice card)"""
from __future__ import annotations

import asyncio
import json
import sys

from . import run as R


def _tools(argv: list[str]) -> int:
    from . import toolchoice as T
    label = argv[argv.index("--label") + 1] if "--label" in argv and len(argv) > argv.index("--label") + 1 else ""
    brain = argv[argv.index("--brain") + 1] if "--brain" in argv and len(argv) > argv.index("--brain") + 1 else ""
    # v0.331 --fresh = the held-out FRESH asks; --limit N = only the first N (a live run costs one model call per ask)
    asks = T.fresh_asks() if "--fresh" in argv else None
    if "--limit" in argv and len(argv) > argv.index("--limit") + 1:
        from .tool_asks import ASKS
        asks = (asks or list(ASKS))[:int(argv[argv.index("--limit") + 1])]
    card = asyncio.run(T.live_card(asks, brain=brain)) if "--live" in argv else T.router_card(asks)
    card = T.save(card, label)
    print("\n".join(T.lines(card)))
    print(f"\n  saved: {card['file']}")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "tools":
        return _tools(argv[1:])
    if argv and argv[0] == "hard":          # v0.272 the hard-reasoning detector card (free, no model)
        from . import hard_asks as HA
        print("\n".join(HA.lines(HA.card())))
        return 0
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
