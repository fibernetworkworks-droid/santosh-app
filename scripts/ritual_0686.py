#!/usr/bin/env python3
"""v0.686.0 version ritual - the LEADS EMPLOYEE joins the Hub (owner: "PUT THE LEAD GENEARTION AI EMPLOYEE IN
THAT SECTION" - the AI Employees hub's Business department) + its Leads Desk in the web console.

v0.685.0 TEESRI JAANCH swept the tests to 0.685.0/+684; the leads parser stamps stood at v0.684.0-* (their
audit release did not touch them). This release re-heads them to v0.686.0-*. Sweeps:

  1. main.py: APP_VERSION 0.685.0 -> 0.686.0 + the v0.686.0 LEADS EMPLOYEE story head (their TEESRI JAANCH
     chain stays VERBATIM as the Previous chain - all story tokens keep their window)
  2. pubspec.yaml: 0.685.0+684 -> 0.686.0+685
  3. CLAUDE.md: the current-version line re-headed (v0.686.0 head, their line becomes the previous head)
  4. tests: pubspec pins -> "0.686.0+685"; bare version pins -> "0.686.0"
  5. static console stamps -> "?v=0.686.0"
  6. leads provenance parser stamps v0.684.0-* -> v0.686.0-* (source + tests, both exact and prefix forms)

NOT touched: the registry pins (615 stands - no new tool), HISTORY.md / WORKLOG.md prose (composed by hand).
"""
from __future__ import annotations

import glob

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html"]

MAIN_OLD = 'APP_VERSION = "0.685.0"   # v0.685.0 TEESRI JAANCH (owner:'
STORY_HEAD = ('APP_VERSION = "0.686.0"   # v0.686.0 LEADS EMPLOYEE (owner: "PERFECT NOW CHECK IN AI EMPLOYE :: '
              'BUSINESS SECTION IN WEB CONSOLVE ---- AND PUT THE LEAD GENEARTION AI EMPLOYEE IN THAT SECTION" - '
              'the AI Employees hub\'s Business department): the P0-P5 leads engine (docs/LEADS_PLAN.md) joins the '
              'Hub as the Lead Generation employee (key leads, live, default group Business) with its own Leads '
              'Desk in the web console - the desk reads the REAL /api/leads/* surface (the overview\'s lanes and '
              'caps, the runs, the rows store with search + per-row opt-out, the outreach ledger) and carries the '
              'TWO-TAP hand-off (the confirm card names rows / rows_without_phone / opt_out_excluded and creates '
              'nothing until the second tap builds the list) + the DPO forget; the six leads tools stay open to '
              'every user (no is_hired gate - the EDU_OPEN law, tested); registry stays 615 (no new tool). '
              'Previous head v0.685.0 TEESRI JAANCH (owner:')
PUBSPEC_OLD = "0.685.0+684"
PUBSPEC_NEW = "0.686.0+685"
VERSION_OLD = "0.685.0"
VERSION_NEW = "0.686.0"
CLAUDE_OLD = ("- Current version: v0.685.0 (pubspec 0.685.0+684; TEESRI JAANCH v0.685.0 (built as 0.681)")
CLAUDE_NEW = ("- Current version: v0.686.0 (pubspec 0.686.0+685; LEADS EMPLOYEE v0.686.0 = the Lead Generation "
              "employee joins the Hub's Business department (key leads, live) + its Leads Desk in the web console "
              "- the real /api/leads surface, the two-tap campaign-list confirm card, the outreach ledger, the "
              "per-row opt-out and the DPO forget; the six leads tools stay open to every user, registry 615 "
              "stands; previous head v0.685.0 (pubspec 0.685.0+684; TEESRI JAANCH v0.685.0 (built as 0.681)")
PARSER_OLD = ["v0.684.0-gm1", "v0.684.0-im1", "v0.684.0-pl1", "v0.684.0-vd1",
              "v0.684.0-en1", "v0.684.0-her1"]
PARSER_PREFIX_OLD = 'startswith("v0.684")'
PARSER_PREFIX_NEW = 'startswith("v0.686")'


def sweep(path: str, pairs: list[tuple[str, str]]) -> int:
    try:
        src = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, FileNotFoundError):
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
    total = {"main": 0, "pubspec": 0, "claude": 0, "tests": 0, "stamps": 0, "parsers": 0, "prefix": 0}
    files = 0
    n = sweep(f"{ROOT}/app/main.py", [(MAIN_OLD, STORY_HEAD)])
    total["main"] += n
    files += 1 if n else 0
    n = sweep("pubspec.yaml", [(f'version: {PUBSPEC_OLD}', f'version: {PUBSPEC_NEW}')])
    total["pubspec"] += n
    files += 1 if n else 0
    n = sweep("CLAUDE.md", [(CLAUDE_OLD, CLAUDE_NEW)])
    total["claude"] += n
    files += 1 if n else 0
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [(PUBSPEC_OLD, PUBSPEC_NEW), (VERSION_OLD, VERSION_NEW),
                      (PARSER_PREFIX_OLD, PARSER_PREFIX_NEW)]
                  + [(o, "v0.686.0" + o[7:]) for o in PARSER_OLD])
        if n:
            total["tests"] += n
            files += 1
    for f in STATICS:
        n = sweep(f, [("?v=0.685.0", "?v=0.686.0")])
        if n:
            total["stamps"] += n
            files += 1
    for f in sorted(glob.glob(f"{ROOT}/app/leads/*.py")):
        n = sweep(f, [(o, "v0.686.0" + o[7:]) for o in PARSER_OLD])
        if n:
            total["parsers"] += n
            files += 1
    print("ritual_0686:", total, "| files touched:", files)


if __name__ == "__main__":
    main()
