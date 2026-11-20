"""python -m app.appengine status | setup [--rebuild] [--prebuilt <node_modules>] | proof [--no-browser] |
kit [--no-browser] [--shots DIR]   (v0.999.51 D1: every kit block built + rendered in 3 genomes)"""
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
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
