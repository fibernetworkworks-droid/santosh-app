"""python -m app.quality [--live] [--judge] [--label "..."] | compare <before.json> <after.json>
   | tools [--live] [--fresh] [--limit N] [--brain claude|glm] [--label "..."]   (v0.245 tool-choice card)
   | longjobs [--hours 24]   (v0.347 how her real long jobs went)
   | longcard [--check | --status | --k 3 --only id,id --limit N --parallel 3 --max-min 75 --label x]
     (v0.443 LONG CARD: 25 long jobs x k through the real loop, judged on the end state)
   | code [--set 1|2|3] [--only id,id] [--limit N] [--kind fix] [--spec] [--label "..."]
   | review [--modes old,new] [--k 1] [--only id,id] [--label x]   (v0.402 PR review card: ECC specialists vs old)
   | maps [--live] [--only id,id] [--limit N] [--kind geo|tool|rule] [--label x]   (v0.470 MAPS card: proof + rupees)
   | skills [--live] [--only id,id] [--limit N] [--kind pos|neg] [--label x]   (v0.494 SKILLS card: do imported skills reach the model)
   | research [--live] [--judge] [--only id,id] [--limit N] [--kind topic|trap] [--label x]
       | research verdict <id> right|wrong ["why"] [--engine X]   (v0.471 R0 RESEARCH card: report quality scored from its own evidence)
       | research runoff --check | --status | --decide | --apply | --reset | --budget-inr N [--engines hoola,parallel,exa] [--only ids] [--limit N] [--k 1] [--judge]
         (v0.478 R7: the card across the engines, scored the same way; --apply writes the winner as the default, only when she says so)
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


def _mapscard(argv: list[str]) -> int:
    from . import mapscard as MC
    val = lambda k: argv[argv.index(k) + 1] if k in argv and len(argv) > argv.index(k) + 1 else ""  # noqa: E731
    items = MC.pick(only=val("--only"), limit=int(val("--limit") or 0), kind=val("--kind"))
    card = asyncio.run(MC.live_card(items)) if "--live" in argv else MC.free_card(items)
    card = MC.save(card, val("--label"))
    print("\n".join(MC.lines(card)))
    print(f"\n  saved: {card['file']}")
    return 0


def _skillscard(argv: list[str]) -> int:
    from . import skillscard as SC
    val = lambda k: argv[argv.index(k) + 1] if k in argv and len(argv) > argv.index(k) + 1 else ""  # noqa: E731
    items = SC.pick(only=val("--only"), limit=int(val("--limit") or 0), kind=val("--kind"))
    card = asyncio.run(SC.live_card(items)) if "--live" in argv else SC.free_card(items)
    card = SC.save(card, val("--label"))
    print("\n".join(SC.lines(card)))
    print(f"\n  saved: {card['file']}")
    return 0


def _runoff(argv: list[str]) -> int:
    from . import researchcard as RC
    from . import runoffcard as RO
    val = lambda k: argv[argv.index(k) + 1] if k in argv and len(argv) > argv.index(k) + 1 else ""  # noqa: E731
    engines = [x for x in (val("--engines") or "hoola").split(",") if x]
    if "--check" in argv:
        print("\n".join(RO.check_lines(RO.check_free(engines, k=int(val("--k") or 1)))))
        return 0
    if "--reset" in argv:
        print("default cleared - 'auto' now means Hoola's own engine" if RO.reset_default() else "no default was applied")
        return 0
    if "--status" in argv or "--decide" in argv or "--apply" in argv:
        card = RO.latest()
        if not card:
            print("No run-off has been run yet.")
            return 0
        card["table"], card["decision"] = RO.rebuild(card)          # with her CURRENT verdicts
        print("\n".join(RO.lines(card)))
        if "--apply" in argv:
            try:
                d = RO.apply_default(card["decision"], card["file"])
            except ValueError as e:
                print("\nNOT APPLIED: " + str(e))
                return 1
            print(f"\nAPPLIED: the default research engine is now '{d['engine']}' (research_engine=auto). Undo with --reset.")
        return 0
    try:
        budget = float(val("--budget-inr") or 0)
    except ValueError:
        budget = 0.0
    items = RC.pick(only=val("--only"), limit=int(val("--limit") or 0), kind=val("--kind"))
    try:
        card = asyncio.run(RO.run_card(engines, items, budget, int(val("--k") or 1), progress=lambda s: print("  ..", s, flush=True)))
    except ValueError as e:
        print(str(e))
        return 2
    card = RO.save(card, val("--label"))
    print("\n".join(RO.lines(card)))
    print(f"\n  saved: {card['file']}")
    return 0


def _researchcard(argv: list[str]) -> int:
    from . import researchcard as RC
    if argv and argv[0] == "runoff":                  # v0.478 R7
        return _runoff(argv[1:])
    val = lambda k: argv[argv.index(k) + 1] if k in argv and len(argv) > argv.index(k) + 1 else ""  # noqa: E731
    if argv and argv[0] == "verdict":       # HER verdict outranks every number on the card
        if len(argv) < 3:
            print('usage: python -m app.quality research verdict <ask id> right|wrong ["why"]')
            return 2
        try:
            rest = argv[3:]
            eng = ""
            if "--engine" in rest:                      # v0.478 R7: her verdict on ONE engine's report
                i = rest.index("--engine")
                eng = rest[i + 1] if len(rest) > i + 1 else ""
                rest = rest[:i] + rest[i + 2:]
            print(RC.set_verdict(argv[1], argv[2], " ".join(rest), eng))
        except ValueError as e:
            print(str(e))
            return 2
        return 0
    items = RC.pick(only=val("--only"), limit=int(val("--limit") or 0), kind=val("--kind"))
    card = asyncio.run(RC.live_card(items, judge="--judge" in argv)) if "--live" in argv else RC.free_card(items)
    card = RC.save(card, val("--label"))
    print("\n".join(RC.lines(card)))
    print(f"\n  saved: {card['file']}")
    return 1 if card["kind"] == "free" and card["calibration_ok"] < len(card["calibration"]) else 0


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
    if "--ping" in argv:                   # v0.443 one tiny real call per model + shape: which part does the API refuse?
        print("\n".join(asyncio.run(H.ping())))
        return 0
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
    if argv and argv[0] == "longcard":      # v0.443 LONG CARD (real long jobs: costs model calls unless --check)
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
    if argv and argv[0] == "maps":          # v0.470 MAPS card (free; --live costs model calls + real Maps rupees)
        return _mapscard(argv[1:])
    if argv and argv[0] == "skills":        # v0.494 SKILLS card (free = reachability; --live = a real model's turns)
        return _skillscard(argv[1:])
    if argv and argv[0] == "research":      # v0.471 R0 RESEARCH card (free; --live costs model calls + web)
        return _researchcard(argv[1:])
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
