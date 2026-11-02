"""python -m app.quality [--live] [--judge] [--label "..."] | compare <before.json> <after.json>
   | tools [--live] [--fresh] [--limit N] [--brain claude|glm] [--label "..."]   (v0.245 tool-choice card)
   | longjobs [--hours 24]   (v0.347 how her real long jobs went)
   | longcard [--check | --status | --k 3 --only id,id --limit N --parallel 3 --max-min 75 --label x]
     (v0.436 LONG CARD: 25 long jobs x k through the real loop, judged on the end state)
   | code [--set 1|2|3] [--only id,id] [--limit N] [--kind fix] [--spec] [--label "..."]
   | review [--modes old,new] [--k 1] [--only id,id] [--label x]   (v0.402 PR review card: ECC specialists vs old)
   | sdk [--setup]   (v0.378 the Dart / Kotlin toolchains the mobile coding card runs with)   (v0.360 coding card: 12 practice jobs through the real loop)"""
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


def _code(argv: list[str]) -> int:
    from . import codecard as K
    val = lambda k: argv[argv.index(k) + 1] if k in argv and len(argv) > argv.index(k) + 1 else ""  # noqa: E731
    only = [x for x in val("--only").split(",") if x]
    kw = {"spec": True} if "--spec" in argv else {}          # v0.402 fix jobs with the ECC fixer specialist
    if val("--kind"):
        kw["kind"] = val("--kind")
    cd = K.save(K.card(only=only or None, limit=int(val("--limit") or 0), set_=int(val("--set") or 1), **kw), val("--label"))
    print("\n".join(K.lines(cd)))
    print(f"\n  saved: {cd['file']}")
    return 0


def _hardcard(argv: list[str]) -> int:
    from . import hard_card as H

    def arg(name, default=""):
        return argv[argv.index(name) + 1] if name in argv and len(argv) > argv.index(name) + 1 else default
    items = H.pick(only=arg("--only"), limit=int(arg("--limit", "0") or 0), quick="--quick" in argv)
    card = asyncio.run(H.live_card(items, judge="--judge" in argv)) if "--live" in argv else H.free_card(items)
    card = H.save(card, arg("--label"))
    print("\n".join(H.lines(card)))
    print(f"\n  saved: {card['file']}")
    return 0


def _longcard(argv: list[str]) -> int:
    from . import longcard as LC
    from .long_asks import ASKS
    val = lambda k: argv[argv.index(k) + 1] if k in argv and len(argv) > argv.index(k) + 1 else ""  # noqa: E731
    if "--check" in argv:                     # free: the set is valid, nothing runs
        bad = LC.check_set()
        k = int(val("--k") or 3)
        lo, hi = LC.estimate(len(ASKS) * k)
        print(f"Long card set {LC.SET_V}: {len(ASKS)} asks, {len(ASKS) * k} runs at k={k} "
              f"(rough cost Rs {lo:,}-{hi:,}).")
        print("\n".join(f"  PROBLEM {b}" for b in bad) or "  set OK")
        return 1 if bad else 0
    if "--status" in argv:
        cards = LC.saved()
        print("\n".join(LC.lines(cards[-1])) if cards else "No long card saved yet.")
        return 0
    only = [x for x in val("--only").split(",") if x]
    asks = [a for a in ASKS if not only or a["id"] in only]
    if val("--limit"):
        asks = asks[:int(val("--limit"))]
    cd = asyncio.run(LC.card(asks, k=int(val("--k") or 3), parallel=int(val("--parallel") or 3),
                             max_min=float(val("--max-min") or 75), label=val("--label")))
    print("\n".join(LC.lines(cd)))
    print(f"\n  saved: {cd['file']}")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "longcard":      # v0.436 LONG CARD (real long jobs: costs model calls unless --check)
        return _longcard(argv[1:])
    if argv and argv[0] == "review":        # v0.401 PR review card (old vs ECC specialists)
        from . import reviewcard as RC
        rest = argv[1:]
        val = lambda k: rest[rest.index(k) + 1] if k in rest and len(rest) > rest.index(k) + 1 else ""  # noqa: E731
        cd = RC.save(RC.card(modes=[x for x in (val("--modes") or "old,new").split(",") if x],
                             k=int(val("--k") or 1), only=[x for x in val("--only").split(",") if x] or None), val("--label"))
        print("\n".join(RC.lines(cd)))
        print(f"\n  saved: {cd['file']}")
        return 0
    if argv and argv[0] == "sdk":           # v0.378 Dart / Kotlin toolchains for the mobile coding card
        from . import sdk
        if "--setup" in argv:
            print("\n".join(sdk.setup()))
        print("\n".join(sdk.status()))
        return 0
    if argv and argv[0] == "code":          # v0.360 coding card (model calls: ~12 Opus jobs)
        return _code(argv[1:])
    if argv and argv[0] == "tools":
        return _tools(argv[1:])
    if argv and argv[0] == "longjobs":      # v0.347 how her real long jobs went (free, reads the records only)
        from . import longjobs as LJ
        hours = int(argv[argv.index("--hours") + 1]) if "--hours" in argv and len(argv) > argv.index("--hours") + 1 else 24
        print("\n".join(LJ.lines(LJ.report(hours))))
        return 0
    if argv and argv[0] == "hardcard":      # v0.438 the hard card: known answers, scored (free, or --live)
        return _hardcard(argv[1:])
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
