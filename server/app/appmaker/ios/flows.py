"""v0.345 HAR RAASTA on the iPhone: folds the XCUITest flow walk (HOOLA_TAP lines in the xcodebuild test log) into the
simulator check's report.json - the same shape the Android device check writes (screens[sid].taps, tap_crash, flows).
Standard library only (runs on the Mac).

    python3 flows.py <out_dir> <xcodebuild-test.log>"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LINE = re.compile(r"HOOLA_TAP\t([a-z][a-z0-9_]{0,48})\t([^\t]*)\t([01])\t([01])\t(\d+)")


def merge(out: Path, log: str) -> dict:
    rep_f = out / "report.json"
    rep = json.loads(rep_f.read_text()) if rep_f.exists() else {"screens": {}, "passed": False}
    screens = rep.setdefault("screens", {})
    crash_text = (out / "flows-crash.txt").read_text(errors="replace")[:3500] if (out / "flows-crash.txt").exists() else ""
    tapped = moved = 0
    dead, crashed = [], []
    for m in LINE.finditer(log or ""):
        sid, label, alive, changed = m.group(1), m.group(2).strip(), m.group(3) == "1", m.group(4) == "1"
        if label == "(open)" or sid not in screens:
            continue
        tapped += 1
        screens[sid].setdefault("taps", []).append({"label": label, "ok": alive, "changed": changed})
        if not alive:
            crashed.append({"screen": sid, "label": label})
            if "tap_crash" not in screens[sid]:
                screens[sid]["tap_crash"] = {"label": label, "exception": "the app closed after this tap",
                                             "excerpt": crash_text if len(crashed) == 1 else ""}
        elif changed:
            moved += 1
        else:
            dead.append({"screen": sid, "label": label})
    rep["flows"] = {"tapped": tapped, "moved": moved, "dead": dead[:30], "crashed": crashed, "ran": tapped > 0}
    rep["passed"] = bool(rep.get("passed")) and not crashed
    rep_f.write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    r = merge(Path(sys.argv[1]), Path(sys.argv[2]).read_text(errors="replace") if Path(sys.argv[2]).exists() else "")
    f = r["flows"]
    print(f"HOOLA FLOWS: {f['tapped']} buttons tapped, {len(f['crashed'])} crashed, {len(f['dead'])} did nothing")
    sys.exit(0 if not f["crashed"] else 1)
