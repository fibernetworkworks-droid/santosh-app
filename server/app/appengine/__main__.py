"""python -m app.appengine status | setup [--rebuild] [--prebuilt <node_modules>] | proof [--no-browser]"""
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
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
