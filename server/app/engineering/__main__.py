"""`python -m app.engineering <check|libs>` - is the CAD engineer alive on THIS server? No model, no cost."""
from __future__ import annotations

import argparse
import json
import sys

from . import selfcheck, service


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.engineering")
    ap.add_argument("what", nargs="?", default="check", choices=["check", "libs", "health"])
    ap.add_argument("--quick", action="store_true", help="skip the slowest study (past yield)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.what == "libs":
        rows = selfcheck.libs()
        if a.json:
            print(json.dumps(rows, indent=2))
        else:
            for r in rows:
                print(f"[{'there' if r['ok'] else 'MISSING'}] {r['lib']}"
                      + ("" if r["ok"] else f" - without it: {r['why']}"))
        return 0 if all(r["ok"] or r["soft"] for r in rows) else 1
    if a.what == "health":
        print(json.dumps(service.health(), indent=2))
        return 0
    if a.json:
        rows = selfcheck.check(quick=a.quick)
        print(json.dumps({"rows": rows, "verdict": selfcheck.verdict(rows)}, indent=2)[:40000])
        return 0 if selfcheck.verdict(rows)["ok"] else 1
    lines = selfcheck.report_lines(quick=a.quick)
    for line in lines:
        print(line)
    return 0 if not any(line.startswith("GADBAD") for line in lines) else 1


if __name__ == "__main__":
    sys.exit(main())
