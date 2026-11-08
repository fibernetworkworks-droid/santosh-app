#!/usr/bin/env python3
"""v0.687.0 version ritual - REBASE PROTOCOL round for the LEADS EMPLOYEE release.

COLLISION: the release was built as v0.686.0 while the dev chain shipped its own v0.686.0 EK LAKH ALAG
WEBSITE (e755c680b) mid-push. Rebased onto their tip; their version layer (main.py story / CLAUDE.md line)
was restored from their commit and now rides the Previous chain; this release re-heads everything as
v0.687.0/+686. Sweeps:

  1. main.py: APP_VERSION 0.686.0 -> 0.687.0 (LEADS EMPLOYEE head) + their EK LAKH ALAG WEBSITE clause
     restored as the Previous head (their chain verbatim below it)
  2. pubspec.yaml: 0.686.0+685 -> 0.687.0+686
  3. CLAUDE.md: current-version line re-headed v0.687.0 + their v0.686 line as previous head
  4. docs/HISTORY.md: the LEADS EMPLOYEE section re-headed v0.687.0 (their release added no HISTORY section)
  5. tests: pubspec pins -> "0.687.0+686"; bare version pins -> "0.687.0"; parser prefix pins -> v0.687
  6. static console stamps -> "?v=0.687.0"
  7. leads provenance parser stamps v0.686.0-* -> v0.687.0-* (source + tests)
  8. the newest-story pin (test_v0475) moves to the v0.687.0 marker

NOT touched: the registry pins (615 stands), WORKLOG (already carries both Task ID lines).
"""
from __future__ import annotations

import glob

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html"]

THEIR_LAKH = ("owner, after v0.683 showed 100 'Sweet shop' cards in a row: \"world wide website template "
              "across every field ... not just a small business ... 1 lakh unique templates, 1 lakh website, "
              "not same name everywhere\"): the Web Studio Templates (webstudio.js) = 1,00,000 UNIQUE websites "
              "- 1,000 subjects in 50 world sectors (site/world.py: SaaS, AI, developer tools, security, "
              "enterprise, finance, fintech, health, schools, universities, media, gaming, climate, non-profits, "
              "civic, crafts ...) x 10 positionings x 10 world cities (Mumbai, Bengaluru, Dubai, London, "
              "New York, Singapore, Sydney, Toronto, Nairobi, Berlin), each its own business with its own "
              "working name (330 roots, 1,00,000 different names), a website type that suits its sector "
              "(6 of 10 types per sector) and a design style (all 10 used); neighbours always differ in sector, "
              "name and style; site/templates.py composes card + deep prompt on demand (who visits, goal, pages, "
              "home sections, must-work features, positioning, design, content, SEO, build quality, sector rules, "
              "never-invent), each <= 2,000 chars and guard-clean (all 1,00,000 checked); search by name / "
              "subject / positioning / city / sector / type / style + sector, website-type, style filters; "
              "Use sends the sector's library field + the type's goal + the style; 7 tests incl. a browser walk.")

MAIN_OLD_HEAD = 'APP_VERSION = "0.686.0"   # v0.686.0 LEADS EMPLOYEE'
MAIN_NEW_HEAD = 'APP_VERSION = "0.687.0"   # v0.687.0 LEADS EMPLOYEE'
MAIN_OLD_PREV = "Previous head v0.685.0 TEESRI JAANCH (owner:"
MAIN_NEW_PREV = ("Previous head v0.686.0 EK LAKH ALAG WEBSITE (" + THEIR_LAKH +
                 " Previous head v0.685.0 TEESRI JAANCH (owner:")
PUBSPEC_OLD = "version: 0.686.0+685"
PUBSPEC_NEW = "version: 0.687.0+686"
CLAUDE_OLD_HEAD = "- Current version: v0.686.0 (pubspec 0.686.0+685; LEADS EMPLOYEE v0.686.0 ="
CLAUDE_NEW_HEAD = "- Current version: v0.687.0 (pubspec 0.687.0+686; LEADS EMPLOYEE v0.687.0 ="
CLAUDE_OLD_PREV = "previous head v0.685.0 (pubspec 0.685.0+684; TEESRI JAANCH"
CLAUDE_NEW_PREV = ("previous head v0.686.0 (pubspec 0.686.0+685; EK LAKH ALAG WEBSITE v0.686.0 = the Web Studio "
                   "Templates as 1,00,000 unique websites worldwide); previous head v0.685.0 (pubspec "
                   "0.685.0+684; TEESRI JAANCH")
HIST_OLD_HEAD = "## v0.686.0 LEADS EMPLOYEE"
HIST_NEW_HEAD = "## v0.687.0 LEADS EMPLOYEE"
HIST_OLD_RITUAL = ("Version ritual: `scripts/ritual_0686.py` — APP_VERSION + story head (their TEESRI JAANCH "
                   "chain verbatim as Previous), pubspec 0.686.0+685, CLAUDE.md current-version line, 345 test "
                   "pins to 0.686.0/+685 (zero residual), 27 console stamps `?v=0.686.0`, the leads parser "
                   "stamps re-headed v0.684.0-* → v0.686.0-* (source + tests, exact and prefix forms).")
HIST_NEW_RITUAL = ("Version ritual: `scripts/ritual_0687.py` — the COLLISION release: built as v0.686.0 while "
                   "the dev chain shipped its own v0.686.0 EK LAKH ALAG WEBSITE mid-push; REBASE PROTOCOL onto "
                   "their tip, their story restored from their commit as the Previous head; APP_VERSION + story "
                   "head, pubspec 0.687.0+686, CLAUDE.md current-version line, the test pins to 0.687.0/+686 "
                   "(zero residual), console stamps `?v=0.687.0`, the leads parser stamps re-headed "
                   "v0.686.0-* → v0.687.0-* (source + tests, exact and prefix forms).")
HIST_OLD_TEST = "NEW `test_v0686_leads_employee.py`"
HIST_NEW_TEST = "NEW `test_v0687_leads_employee.py`"
FRAMES_OLD = ("assert 'TEESRI JAANCH' in main and 'webstudio' in main  # the newest-story precedent (v0.686.0 "
              "carries the marker; older stories live in git history)")
FRAMES_NEW = ("assert 'LEADS EMPLOYEE' in main and 'webstudio' in main  # the newest-story precedent (v0.687.0 "
              "carries the marker; their EK LAKH ALAG WEBSITE line rides the Previous chain)")
VERSION_OLD = "0.686.0"
VERSION_NEW = "0.687.0"
PARSER_PREFIX_OLD = 'startswith("v0.686")'
PARSER_PREFIX_NEW = 'startswith("v0.687")'


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
    total = {"main": 0, "pubspec": 0, "claude": 0, "history": 0, "frames": 0,
             "tests": 0, "stamps": 0, "parsers": 0}
    files = 0
    n = sweep(f"{ROOT}/app/main.py", [(MAIN_OLD_HEAD, MAIN_NEW_HEAD), (MAIN_OLD_PREV, MAIN_NEW_PREV)])
    total["main"] += n
    files += 1 if n else 0
    n = sweep("pubspec.yaml", [(PUBSPEC_OLD, PUBSPEC_NEW)])
    total["pubspec"] += n
    files += 1 if n else 0
    n = sweep("CLAUDE.md", [(CLAUDE_OLD_HEAD, CLAUDE_NEW_HEAD), (CLAUDE_OLD_PREV, CLAUDE_NEW_PREV)])
    total["claude"] += n
    files += 1 if n else 0
    n = sweep("docs/HISTORY.md", [(HIST_OLD_HEAD, HIST_NEW_HEAD), (HIST_OLD_RITUAL, HIST_NEW_RITUAL),
                                  (HIST_OLD_TEST, HIST_NEW_TEST)])
    total["history"] += n
    files += 1 if n else 0
    n = sweep(f"{ROOT}/tests/test_v0475_console_frames.py", [(FRAMES_OLD, FRAMES_NEW)])
    total["frames"] += n
    files += 1 if n else 0
    # the v0.686 sweep's own off-by-one healed: 'v0.684.0-gm1'[7:] is '0-gm1' (the same v0.682.00- typo class
    # their round-3 suite caught), so the stamps became v0.686.00-*; the plain 0.686.0 -> 0.687.0 sweep then
    # made the TEST pins v0.687.00-*; both forms heal to the clean v0.687.0-*
    DOUBLE_ZERO = [("v0.686.00-" + s, "v0.687.0-" + s) for s in ("gm1", "im1", "pl1", "vd1", "en1", "her1")] \
        + [("v0.687.00-" + s, "v0.687.0-" + s) for s in ("gm1", "im1", "pl1", "vd1", "en1", "her1")]
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [("0.686.0+685", "0.687.0+686"), (VERSION_OLD, VERSION_NEW),
                      (PARSER_PREFIX_OLD, PARSER_PREFIX_NEW)]
                  + DOUBLE_ZERO
                  + [(o, "v0.687.0" + o[7:]) for o in
                     ("v0.686.0-gm1", "v0.686.0-im1", "v0.686.0-pl1", "v0.686.0-vd1",
                      "v0.686.0-en1", "v0.686.0-her1")])
        if n:
            total["tests"] += n
            files += 1
    for f in STATICS:
        n = sweep(f, [("?v=0.686.0", "?v=0.687.0")])
        if n:
            total["stamps"] += n
            files += 1
    for f in sorted(glob.glob(f"{ROOT}/app/leads/*.py")):
        n = sweep(f, DOUBLE_ZERO
                  + [(o, "v0.687.0" + o[7:]) for o in
                     ("v0.686.0-gm1", "v0.686.0-im1", "v0.686.0-pl1", "v0.686.0-vd1",
                      "v0.686.0-en1", "v0.686.0-her1")])
        if n:
            total["parsers"] += n
            files += 1
    print("ritual_0687:", total, "| files touched:", files)


if __name__ == "__main__":
    main()
