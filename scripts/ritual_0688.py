#!/usr/bin/env python3
"""v0.688.0 version ritual - LEADS DESK SEAM release (clean bump, no collision).

The release: the Leads Desk's first load called GET /api/leads/overview, the server serves GET /api/leads -
one 404 killed the Promise.all into the owner's red "Not Found". The call is the canonical route now, and
NEW test_v0688_leads_desk_seam.py checks the seam WHOLE (every desk call vs the real route table + the
first-load trio fired for real). Sweeps:

  1. main.py: APP_VERSION 0.687.0 -> 0.688.0 (LEADS DESK SEAM head); the v0.687 LEADS EMPLOYEE clause
     rides the Previous chain verbatim (only the head up to "(owner:" is replaced - the old body continues)
  2. pubspec.yaml: 0.687.0+686 -> 0.688.0+687
  3. CLAUDE.md: current-version line re-headed v0.688.0; the v0.687 line as previous head
  4. docs/HISTORY.md: the NEW v0.688.0 section PREPENDED (the v0.687 section stays untouched)
  5. tests: pins 0.687.0+686 -> 0.688.0+687, bare 0.687.0 -> 0.688.0, parser prefix startswith("v0.687")
     -> startswith("v0.688")
  6. static console stamps -> "?v=0.688.0" (v2.html + webstudio.html)
  7. leads parser stamps v0.687.0-* -> v0.688.0-* (source: app/leads/*.py; tests carry no 00-anomaly
     this round - the clean v0.687 stamps heal through the bare sweep)
  8. the newest-story pin (test_v0475) moves to the v0.688.0 marker

NOT touched: the registry pins (615 stands), the export-line pins (..., edu, leads} - no new keys).
"""
from __future__ import annotations

import glob

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html"]

NEW_STORY = ('the desk\'s first load was Promise.all([GET /api/leads/overview, GET /api/leads/runs?limit=12, '
             'GET /api/leads/outreach?limit=100]) but the server\'s overview route is GET /api/leads (the router '
             'itself is the overview since v0.544) - one 404 killed the Promise.all, the catch painted the '
             'message red, six of seven routes worked and the desk still looked dead on open; THE FIX: the desk '
             'calls the canonical GET /api/leads now (one line in employees.js; no new route, no alias, no second '
             'name for the same thing); THE GUARD: NEW test_v0688_leads_desk_seam.py (4, zero network) - it '
             'extracts EVERY api(\'METHOD\', \'/api/leads...\') call from the console sources and asserts each '
             '(method, path) against the REAL FastAPI route table, asserts the ghost route gone from the sources, '
             'and FIRES the desk\'s exact first-load trio over the TestClient (200/200/200 with the key, 401 '
             'without; the overview carrying the store/usage/caps/lanes/lanes_built/store_backend/never/'
             'one_question/store_boundary keys the desk renders) - the v0.687 test had checked each side '
             'SEPARATELY so the broken seam passed both; the seam is checked WHOLE now, proven the honest way '
             '(with the old call restored the seam file fails 3/4); test_v0687\'s surface pin healed to the '
             'canonical path (it had pinned the bug). NOT VERIFIED unchanged: the desk answers real APIs on the '
             'deployed server, no lane has answered the real world yet.')

MAIN_OLD_HEAD = 'APP_VERSION = "0.687.0"   # v0.687.0 LEADS EMPLOYEE (owner:'
MAIN_NEW_HEAD = ('APP_VERSION = "0.688.0"   # v0.688.0 LEADS DESK SEAM (owner: "NOW A PERFECT LEAD DESK FOR IT" '
                 '+ their screenshot of the desk showing a red "Not Found"): ' + NEW_STORY +
                 ' Previous head v0.687.0 LEADS EMPLOYEE (owner:')
PUBSPEC_OLD = "version: 0.687.0+686"
PUBSPEC_NEW = "version: 0.688.0+687"
CLAUDE_OLD_HEAD = "Current version: v0.687.0 (pubspec 0.687.0+686; LEADS EMPLOYEE v0.687.0 ="
CLAUDE_NEW_HEAD = ("Current version: v0.688.0 (pubspec 0.688.0+687; LEADS DESK SEAM v0.688.0 = the Leads Desk "
                   "answers again - the desk called GET /api/leads/overview, the server serves GET /api/leads, "
                   "the 404 killed the first-load Promise.all into a red \"Not Found\"; the call is the canonical "
                   "route now + the seam test fires the first-load trio); previous head v0.687.0 "
                   "(pubspec 0.687.0+686; LEADS EMPLOYEE v0.687.0 =")

HISTORY_NEW_SECTION = (
    "## v0.688.0 LEADS DESK SEAM — the desk's first load answers (8 Nov 2026; owner: \"NOW A PERFECT LEAD DESK "
    "FOR IT\" + a screenshot of the Leads Desk showing a red \"Not Found\")\n\n"
    "The v0.687 desk was wired to a route that did not exist: its first load was "
    "`Promise.all([GET /api/leads/overview, GET /api/leads/runs?limit=12, GET /api/leads/outreach?limit=100])`, "
    "the server's overview route is `GET /api/leads` (the router itself is the overview since v0.544) — one 404 "
    "killed the whole `Promise.all`, the `catch` painted the message red, and a desk with six of seven routes "
    "working looked dead on open.\n\n"
    "- **THE FIX** — one line in `employees.js`: the desk calls the canonical `GET /api/leads`. No new route, "
    "no alias, no second name for the same thing.\n"
    "- **THE GUARD** — NEW `test_v0688_leads_desk_seam.py` (4 tests, zero network): extracts EVERY "
    "`api('METHOD', '/api/leads…')` call from the console sources and asserts each `(method, path)` against the "
    "REAL FastAPI route table; the ghost route is asserted gone; the desk's exact first-load trio is FIRED over "
    "the TestClient (200/200/200 with the key, 401 without; the overview carries the nine keys the desk renders "
    "on first paint). The v0.687 test had checked each side separately — the seam is now checked whole. Proven "
    "the honest way: with the old call restored, the seam file fails 3/4.\n"
    "- `test_v0687`'s surface pin healed to the canonical path (it had pinned the bug).\n"
    "- Version ritual: `scripts/ritual_0688.py` — APP_VERSION + story head (the v0.687 LEADS EMPLOYEE clause "
    "verbatim as Previous), pubspec 0.688.0+687, CLAUDE.md current-version line, HISTORY section, test pins → "
    "0.688.0/+687, console stamps `?v=0.688.0`, the leads parser stamps v0.687.0-* → v0.688.0-* (source + "
    "tests), the newest-story pin moved to the v0.688.0 marker (test_v0475).\n\n\n")

HISTORY_OLD_HEAD = "## v0.687.0 LEADS EMPLOYEE — the Lead Generation employee joins the AI Employees hub"
FRAMES_OLD = ("assert 'LEADS EMPLOYEE' in main and 'webstudio' in main  # the newest-story precedent (v0.687.0 "
              "carries the marker; their EK LAKH ALAG WEBSITE line rides the Previous chain)")
FRAMES_NEW = ("assert 'LEADS DESK SEAM' in main and 'webstudio' in main  # the newest-story precedent (v0.688.0 "
              "carries the marker; their LEADS EMPLOYEE line rides the Previous chain)")


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
    files = 0
    n = sweep(f"{ROOT}/app/main.py", [(MAIN_OLD_HEAD, MAIN_NEW_HEAD)])
    total["main"] = n
    files += 1 if n else 0
    n = sweep("pubspec.yaml", [(PUBSPEC_OLD, PUBSPEC_NEW)])
    add("pubspec", n)
    files += 1 if n else 0
    n = sweep("CLAUDE.md", [(CLAUDE_OLD_HEAD, CLAUDE_NEW_HEAD)])
    add("claude", n)
    files += 1 if n else 0
    # HISTORY: prepend the new section above the current first section head
    p = "docs/HISTORY.md"
    src = open(p, encoding="utf-8").read()
    assert HISTORY_OLD_HEAD in src, "HISTORY first head moved - inspect before prepending"
    open(p, "w", encoding="utf-8").write(HISTORY_NEW_SECTION + src)
    total["history"] = 1
    files += 1
    n = sweep(f"{ROOT}/tests/test_v0475_console_frames.py", [(FRAMES_OLD, FRAMES_NEW)])
    add("frames", n)
    files += 1 if n else 0
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [("0.687.0+686", "0.688.0+687"), ("0.687.0", "0.688.0"),
                      ('startswith("v0.687")', 'startswith("v0.688")')])
        if n:
            add("tests", n)
            files += 1
    for f in STATICS:
        n = sweep(f, [("?v=0.687.0", "?v=0.688.0")])
        if n:
            add("stamps", n)
            files += 1
    for f in sorted(glob.glob(f"{ROOT}/app/leads/*.py")):
        n = sweep(f, [("v0.687.0-", "v0.688.0-")])
        if n:
            add("parsers", n)
            files += 1
    print("ritual_0688:", total, "| files touched:", files)


if __name__ == "__main__":
    main()
