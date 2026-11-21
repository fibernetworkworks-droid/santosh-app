"""python -m app.appengine status | setup [--rebuild] [--prebuilt <node_modules>] | proof [--no-browser] |
kit [--no-browser] [--shots DIR]   (v0.999.51 D1: every kit block built + rendered in 3 genomes) |
genomes [N] [--no-browser]   (v0.999.58 D2: N random design genomes pass contrast + render every block) |
speed [direction ...]   (v0.999.64 D3: the proof site pre-rendered + measured like a phone: Core Web Vitals in the lab) |
writer-card [--limit N] [--only b01,o03] [--out FILE] [--live --budget-inr N] [--critic [--d0 FILE]]   (v0.999.65 D4: the
40 briefs written in React from the kit + built; the done-line is 0 refused writes left. v0.999.67 D5 --critic: each site
through the critic loop - free = a scripted critic; live = the real critic, compared with the D0 design card)"""
from __future__ import annotations

import json
import sys


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        from . import service as AE
        print(json.dumps(AE.status(), indent=2))
        return 0
    if cmd == "setup":
        from . import image as IMG
        from . import runner as RN
        av = RN.available()
        if av["ok"] and "--rebuild" not in argv:
            print("The App Engine image is already built:", json.dumps(av))
            return 0
        pre = argv[argv.index("--prebuilt") + 1] if "--prebuilt" in argv else ""
        r = IMG.build(nocache="--rebuild" in argv and not pre, prebuilt=pre)
        print(r["out"][-3000:])
        print(json.dumps({k: v for k, v in r.items() if k != "out"}, indent=2))
        print(json.dumps(RN.available(), indent=2))
        return 0 if r["ok"] else 1
    if cmd == "proof":
        from . import proof
        r = proof.run(browser="--no-browser" not in argv)
        for row in r["rows"]:
            print(json.dumps(row))
        print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=2))
        return 0 if r["verdict"] == "PASS" else 1
    if cmd == "kit":
        from . import kit
        shots = argv[argv.index("--shots") + 1] if "--shots" in argv else ""
        r = kit.render_check(browser="--no-browser" not in argv, shots=shots)
        for g in r["genomes"]:
            print(json.dumps({k: g[k] for k in g if k != "problems"}), "problems:", len(g["problems"]))
            for p in g["problems"][:40]:
                print("  -", p)
        for p in r["rule_problems"][:40]:
            print(f"  rule {p['file']}:{p['line']} {p['rule']} - {p['found']}")
        print(json.dumps({k: v for k, v in r.items() if k not in ("genomes", "rule_problems")}, indent=2))
        return 0 if r["verdict"] == "PASS" else 1
    if cmd == "writer-card":
        from . import writercard as WC

        def opt(k: str, d: str = "") -> str:
            return argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d
        card = WC.run(limit=int(opt("--limit", "0") or 0), only=opt("--only"), live="--live" in argv,
                      budget_inr=float(opt("--budget-inr", "0") or 0), out=opt("--out"), critic_on="--critic" in argv,
                      d0=opt("--d0"))
        print(json.dumps(card.get("summary") or {"verdict": card.get("verdict"), "why": card.get("why")}, indent=2))
        if card.get("against_d0"):
            print(json.dumps({"against_d0": card["against_d0"]}, indent=2))
        return 0 if (card.get("summary") or {}).get("verdict") == "PASS" else 1
    if cmd == "speed":
        from . import speed
        dirs = [a for a in argv[1:] if not a.startswith("-")] or list(speed.DIRECTIONS)
        r = speed.lab_check(dirs)
        print(speed.say(r))
        print(json.dumps({"verdict": r["verdict"], "why": r.get("why", "")}))
        return 0 if r["verdict"] == "PASS" else 1
    if cmd == "genomes":
        from . import kit
        nums = [a for a in argv[1:] if a.isdigit()]
        r = kit.genome_check(int(nums[0]) if nums else 100, browser="--no-browser" not in argv)
        for row in r.get("rows", []):
            print(json.dumps(row)[:600])
        print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=2))
        return 0 if r["verdict"] == "PASS" else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
