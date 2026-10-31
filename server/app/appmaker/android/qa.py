"""v0.324 HOOLA QA: the device check's report (standard library only: it runs on the build machine and in CI too).

    python3 qa.py report <out_dir>     # reads what device_check.sh collected, writes <out_dir>/report.json

Per screen: opened (no crash), the crash (exception line + the app's own frames), the accessibility findings from the
UI tree (a tappable thing with no words for TalkBack, a tap target under 48 x 48 dp), the screenshot. For the app: cold
start (median of 3, release build), janky frames while scrolling, APK size, each against the budget. `passed` = every
screen opened; budget and accessibility findings are reported, the crash is what blocks a build."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import median
from typing import Any

BUDGET = {"cold_ms": 1500, "apk_mb": 15.0, "jank_pct": 25.0}
TARGET_DP = 48
BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def a11y(xml_text: str, density: int = 420) -> list[dict[str, Any]]:
    """Findings in one screen's UI tree (uiautomator dump)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    px_per_dp = max(1.0, density / 160.0)
    out: list[dict[str, Any]] = []

    def words(n: ET.Element) -> str:
        own = (n.get("text") or "") + (n.get("content-desc") or "")
        return own + "".join(words(c) for c in n)

    for n in root.iter("node"):
        if n.get("clickable") != "true" or n.get("enabled") == "false":
            continue
        m = BOUNDS.match(n.get("bounds") or "")
        w_dp = h_dp = 0.0
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            w_dp, h_dp = (x2 - x1) / px_per_dp, (y2 - y1) / px_per_dp
            if w_dp <= 0 or h_dp <= 0:
                continue
        label = words(n).strip()
        if not label:
            out.append({"kind": "unlabelled", "text": f"a tappable {n.get('class', '').split('.')[-1] or 'item'} has no label "
                                                      f"for TalkBack", "bounds": n.get("bounds") or ""})
        if m and (w_dp < TARGET_DP - 4 or h_dp < TARGET_DP - 4):
            out.append({"kind": "small_target", "text": f"tap target {w_dp:.0f}x{h_dp:.0f} dp (under 48 dp): "
                                                        f"{label[:40] or 'no label'}", "bounds": n.get("bounds") or ""})
    return out[:20]


def crash_of(text: str) -> dict[str, Any] | None:
    """The first FATAL EXCEPTION in a logcat: its exception line and the app's own frames (hoola.*)."""
    i = text.find("FATAL EXCEPTION")
    if i < 0:
        return None
    lines = [ln.split(": ", 1)[-1] if ": " in ln[:80] else ln for ln in text[i:].splitlines()[1:80]]
    exc = next((ln.strip() for ln in lines if re.match(r"\s*[\w.$]+(Exception|Error)\b", ln.strip())), "")
    frames = [ln.strip() for ln in lines if ln.strip().startswith("at hoola.")][:8]
    screen = next((m.group(1) for f in frames for m in [re.search(r"hoola\.app\.screens\.(Screen\w+?)(Kt)?\.", f)] if m), "")
    return {"exception": exc[:300], "frames": frames, "screen_class": screen,
            "excerpt": "\n".join(ln.rstrip() for ln in lines[:40])[:4000]}


def jank_of(text: str) -> tuple[int, float] | None:
    m = re.search(r"Total frames rendered:\s*(\d+).*?Janky frames:\s*(\d+)\s*\(([\d.]+)%\)", text, re.S)
    return (int(m.group(1)), float(m.group(3))) if m else None


def report(out: Path) -> dict[str, Any]:
    out = Path(out)
    try:
        density = int((out / "density.txt").read_text().strip() or 420)
    except (OSError, ValueError):
        density = 420
    screens: dict[str, Any] = {}
    for ln in (out / "opened.txt").read_text().splitlines() if (out / "opened.txt").exists() else []:
        parts = ln.split()
        if len(parts) != 2:
            continue
        sid, alive = parts[0], parts[1] == "1"
        d = out / "screens"
        xml = d / f"{sid}.xml"
        crash = crash_of((d / f"{sid}.crash.txt").read_text(errors="replace")) if (d / f"{sid}.crash.txt").exists() else None
        screens[sid] = {"opened": alive and crash is None, "crash": crash,
                        "a11y": a11y(xml.read_text(errors="replace"), density) if xml.exists() else [],
                        "shot": f"screens/{sid}.png" if (d / f"{sid}.png").exists() and (d / f"{sid}.png").stat().st_size > 1000 else ""}
    cold = [int(x) for x in ((out / "cold.txt").read_text().split() if (out / "cold.txt").exists() else []) if x.isdigit()]
    jank = jank_of((out / "gfxinfo.txt").read_text(errors="replace")) if (out / "gfxinfo.txt").exists() else None
    try:
        apk = int((out / "apk_bytes.txt").read_text().strip())
    except (OSError, ValueError):
        apk = 0
    perf = {"cold_ms": int(median(cold)) if cold else None, "cold_all": cold,
            "jank_pct": jank[1] if jank else None, "frames": jank[0] if jank else None,
            "apk_mb": round(apk / 1048576, 2) if apk else None}
    budget = {k: (None if perf.get(k) is None else ("ok" if perf[k] <= v else "over")) for k, v in BUDGET.items()}
    crashed = [s for s, x in screens.items() if not x["opened"]]
    rep = {"v": 1, "screens": screens, "perf": perf, "budget": budget, "limits": BUDGET,
           "opened": len(screens) - len(crashed), "total": len(screens), "crashed": crashed,
           "a11y_count": sum(len(x["a11y"]) for x in screens.values()),
           "passed": bool(screens) and not crashed}
    (out / "report.json").write_text(json.dumps(rep, indent=1))
    return rep


def summary(rep: dict[str, Any]) -> str:
    p, b = rep.get("perf") or {}, rep.get("budget") or {}
    bits = [f"{rep.get('opened', 0)}/{rep.get('total', 0)} screens opened"]
    if rep.get("crashed"):
        bits.append("CRASHED: " + ", ".join(rep["crashed"]))
    if p.get("cold_ms") is not None:
        bits.append(f"cold start {p['cold_ms']} ms ({b.get('cold_ms')})")
    if p.get("jank_pct") is not None:
        bits.append(f"janky frames {p['jank_pct']}% ({b.get('jank_pct')})")
    if p.get("apk_mb") is not None:
        bits.append(f"APK {p['apk_mb']} MB ({b.get('apk_mb')})")
    bits.append(f"{rep.get('a11y_count', 0)} accessibility findings")
    return "HOOLA QA " + ("PASS" if rep.get("passed") else "FAIL") + ": " + " · ".join(bits)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "report":
        r = report(Path(sys.argv[2]))
        print(summary(r))
        sys.exit(0 if r["passed"] else 1)
    print(__doc__)
    sys.exit(2)
