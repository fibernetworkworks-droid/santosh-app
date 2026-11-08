#!/usr/bin/env python3
"""v0.690.0 version ritual - LEADS DESK EMPTY release (clean bump).

The release: the desk rendered 'Loading…' forever with all three fetches 200 - `ReferenceError: empty is
not defined at Object.leads` (the EDUCATION desk's local helper, invisible from the leads desk). Reproduced
end-to-end in a real browser (agent-browser walk: login -> hub -> Business -> Open desk -> the rejection
caught), then fixed (the desk carries its own `empty`) and re-walked: the desk renders fully, zero
rejections. NEW test_v0690_leads_desk_scope.py guards the class: every function the desk body calls must be
reachable (wrapper param / wrapper scope / the desk's own body). Sweeps:

  1. main.py: APP_VERSION 0.689.0 -> 0.690.0 (LEADS DESK EMPTY head); the v0.689 clause rides the Previous
     chain verbatim (only the head up to "(owner:" is replaced)
  2. pubspec.yaml: 0.689.0+688 -> 0.690.0+689
  3. CLAUDE.md: current-version line re-headed v0.690.0; the v0.689 line as previous head
  4. docs/HISTORY.md: the NEW v0.690.0 section PREPENDED
  5. tests: pins 0.689.0+688 -> 0.690.0+689; bare 0.689.0 -> 0.690.0; parser prefix startswith("v0.689")
     -> startswith("v0.690")
  6. static console stamps -> "?v=0.690.0" (v2.html + webstudio.html)
  7. leads parser stamps v0.689.0-* -> v0.690.0-* (source)
  8. the newest-story pin (test_v0475) moves to the v0.690.0 marker

NOT touched: the registry pins (615 stands), the export-line pins, WORKLOG.
"""
from __future__ import annotations

import glob

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html"]

NEW_STORY = ('the desk rendered "Loading…" FOREVER with all three first-load fetches 200 (their second '
             'screenshot; reproduced end-to-end in a real browser against the real app - login, hub, Business, '
             'Open desk, the rejection caught): ROOT CAUSE `ReferenceError: empty is not defined at '
             'Object.leads` - the desk called `empty(...)`, the EDUCATION desk\'s LOCAL helper (a const inside '
             'async function edu(el)), invisible from the leads desk; the first paint put the Loading div up, '
             'the render threw before the first innerHTML assignment, the promise rejected unhandled, and a '
             'desk with a green network tab looked dead; THE FIX: the desk carries its own `empty` (the same '
             'helper, the same pattern every desk uses for its own); THE GUARD: NEW test_v0690_leads_desk_'
             'scope.py (3, zero network) - the desk\'s own empty pinned, and every function the desk body '
             'calls must be REACHABLE (a destructured param of the HoolaEmployees wrapper, a definition at the '
             'wrapper\'s own scope, or a definition inside the desk body itself - a helper living only inside '
             'another desk\'s closure fails the test), plus the v0.689 route-seam law re-asserted through it; '
             'THE PROOF: the browser walk re-run after the fix - the desk renders fully (the pitch, the Seekh '
             'trust tag, the five KPIs with the 20,000/day cap named, all five lanes Built, the store line, '
             'Recent runs, the Outreach ledger), zero unhandled rejections. NOT VERIFIED unchanged: the desk '
             'answers real APIs on the deployed server, no lane has answered the real world yet.')

MAIN_OLD_HEAD = 'APP_VERSION = "0.689.0"   # v0.689.0 LEADS DESK SEAM (owner:'
MAIN_NEW_HEAD = ('APP_VERSION = "0.690.0"   # v0.690.0 LEADS DESK EMPTY (owner: "it stuck on loading" + their '
                 'screenshot of the desk stuck at "Loading…"): ' + NEW_STORY +
                 ' Previous head v0.689.0 LEADS DESK SEAM (owner:')
PUBSPEC_OLD = "version: 0.689.0+688"
PUBSPEC_NEW = "version: 0.690.0+689"
CLAUDE_OLD_HEAD = "Current version: v0.689.0 (pubspec 0.689.0+688; LEADS DESK SEAM v0.689.0 ="
CLAUDE_NEW_HEAD = ("Current version: v0.690.0 (pubspec 0.690.0+689; LEADS DESK EMPTY v0.690.0 = the desk's "
                   "\"Loading…\" forever healed - it called the Education desk's local `empty` helper, "
                   "ReferenceError at first render, the fetches all 200; the desk carries its own now + the "
                   "reachability guard); previous head v0.689.0 (pubspec 0.689.0+688; LEADS DESK SEAM v0.689.0 =")
HIST_OLD_HEAD = "## v0.689.0 LEADS DESK SEAM"

FRAMES_OLD = ("assert 'LEADS DESK SEAM' in main and 'webstudio' in main  # the newest-story precedent (v0.689.0 "
              "carries the marker; their KAAM MANCH line rides the Previous chain)")
FRAMES_NEW = ("assert 'LEADS DESK EMPTY' in main and 'webstudio' in main  # the newest-story precedent (v0.690.0 "
              "carries the marker; their LEADS DESK SEAM line rides the Previous chain)")


def sweep(path: str, pairs: list[tuple[str, str]]) -> int:
    try:
        src = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        print("  MISSING (skipped):", path)
        return 0
    n = 0
    for old, new in pairs:
        c = src.count(old)
        if c:
            src = src.replace(old, new)
            n += c
    if n:
        open(path, "w", encoding="utf-8").write(src)
    return n


def main() -> None:
    total: dict[str, int] = {}

    def add(key: str, n: int) -> None:
        total[key] = total.get(key, 0) + n

    n = sweep(f"{ROOT}/app/main.py", [(MAIN_OLD_HEAD, MAIN_NEW_HEAD)])
    add("main", n)
    n = sweep("pubspec.yaml", [(PUBSPEC_OLD, PUBSPEC_NEW)])
    add("pubspec", n)
    n = sweep("CLAUDE.md", [(CLAUDE_OLD_HEAD, CLAUDE_NEW_HEAD)])
    add("claude", n)
    p = "docs/HISTORY.md"
    src = open(p, encoding="utf-8").read()
    assert src.startswith(HIST_OLD_HEAD), "HISTORY first head moved - inspect before prepending"
    section = (
        "## v0.690.0 LEADS DESK EMPTY — the desk renders (8 Nov 2026; owner: \"it stuck on loading\" + a "
        "screenshot of the desk stuck at \"Loading…\")\n\n"
        "The v0.689 fix removed the 404 — and the desk STILL hung at \"Loading…\", now with all three "
        "first-load fetches green (200/200/200). Reproduced end-to-end in a real browser against the real app "
        "(login → hub → Business → Open desk), the rejection caught live: `ReferenceError: empty is not "
        "defined at Object.leads` — the desk called `empty(...)`, which is the EDUCATION desk's LOCAL helper "
        "(a `const` inside `async function edu(el)`), invisible from the leads desk. The Loading div went up, "
        "the render threw before the first `innerHTML =`, the promise rejected unhandled: a dead desk with a "
        "green network tab.\n\n"
        "- **THE FIX** — the desk carries its own `empty` (the same helper, the same pattern each desk uses "
        "for its own).\n"
        "- **THE GUARD** — NEW `test_v0690_leads_desk_scope.py` (3 tests, zero network): the desk's own "
        "`empty` pinned; every function the desk body calls must be REACHABLE (a destructured param of the "
        "HoolaEmployees wrapper, a definition at the wrapper's own scope, or a definition inside the desk body "
        "itself) — a helper living only inside another desk's closure fails the test; the v0.689 route-seam "
        "law re-asserted through it. The v0.687-era string-presence tests never ran the JS, which is why both "
        "this and the route bug sailed through.\n"
        "- **THE PROOF** — the browser walk re-run after the fix: the desk renders fully (the pitch, the "
        "Seekh trust tag, the five KPIs with the 20,000/day cap named, all five lanes Built, the store line, "
        "Recent runs, the Outreach ledger), zero unhandled rejections.\n"
        "- Version ritual: `scripts/ritual_0690.py` — APP_VERSION + story head (the v0.689 clause verbatim as "
        "Previous), pubspec 0.690.0+689, CLAUDE.md current-version line, HISTORY section, test pins → "
        "0.690.0/+689, console stamps `?v=0.690.0`, the leads parser stamps v0.689.0-* → v0.690.0-*, the "
        "newest-story pin moved to the v0.690.0 marker (test_v0475).\n\n\n")
    open(p, "w", encoding="utf-8").write(section + src)
    add("history", 1)
    n = sweep(f"{ROOT}/tests/test_v0475_console_frames.py", [(FRAMES_OLD, FRAMES_NEW)])
    add("frames", n)
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [("0.689.0+688", "0.690.0+689"), ("0.689.0", "0.690.0"),
                      ('startswith("v0.689")', 'startswith("v0.690")')])
        if n:
            add("tests", n)
    for f in STATICS:
        n = sweep(f, [("?v=0.689.0", "?v=0.690.0")])
        if n:
            add("stamps", n)
    for f in sorted(glob.glob(f"{ROOT}/app/leads/*.py")):
        n = sweep(f, [("v0.689.0-", "v0.690.0-")])
        if n:
            add("parsers", n)
    print("ritual_0690:", total)


if __name__ == "__main__":
    main()
