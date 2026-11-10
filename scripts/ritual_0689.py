#!/usr/bin/env python3
"""v0.689.0 version ritual - LEADS DESK SEAM re-head after the v0.688.0 COLLISION.

COLLISION: the release was built as v0.688.0 while the dev chain shipped its own v0.688.0 KAAM MANCH
(7efbfb1bc, the OWL port) mid-push. REBASE PROTOCOL onto their tip: their code kept whole (kaam_laws.py,
kaam tools, their tests - all ride untouched); their story layers (main.py head / CLAUDE.md line /
HISTORY.md section) are pulled VERBATIM from their commit and ride the Previous chain. One composition
note: their main.py chain SKIPS the v0.687.0 LEADS EMPLOYEE clause (theirs: v0.688 -> v0.686), so the
chain is SPLICED, not replaced: this release's story -> their KAAM MANCH clause -> the v0.687 LEADS
EMPLOYEE clause -> their v0.686 tail - nothing is lost. Their CLAUDE.md line chains correctly
(v0.688 -> v0.687 -> ...) and is composed normally. Sweeps:

  1. main.py: APP_VERSION 0.688.0 -> 0.689.0 (LEADS DESK SEAM head) + their KAAM MANCH clause spliced
     as the Previous head (their body verbatim, cut at their own Previous tail) + the v0.687 clause and
     deeper chain kept from this release's own line
  2. pubspec.yaml: 0.688.0+687 -> 0.689.0+688
  3. CLAUDE.md: current-version line re-headed v0.689.0; their v0.688 KAAM MANCH line (with its correct
     v0.687 chain) as previous head
  4. docs/HISTORY.md: this release's section re-headed v0.689.0 (collision noted) + THEIR v0.688 KAAM
     MANCH section restored verbatim above the v0.687 section
  5. tests: pins 0.688.0+687 -> 0.689.0+688; bare 0.688.0 -> 0.689.0 (incl. their test_v0688_kaam_manch
     conscious-bump guard); parser prefix startswith("v0.688") -> startswith("v0.689")
  6. static console stamps -> "?v=0.689.0" (v2.html + webstudio.html)
  7. leads parser stamps v0.688.0-* -> v0.689.0-* (source)
  8. the newest-story pin (test_v0475) re-headed to the v0.689.0 marker (their KAAM MANCH line noted)
  9. this release's test renamed test_v0688_leads_desk_seam.py -> test_v0689_leads_desk_seam.py (born
     in the collision round, ships as v0.689; the docstring re-heads through the bare sweep)

NOT touched: their scripts/ritual_v0688.py and this release's scripts/ritual_0688.py (both are the
historical record of the collision round), the registry pins (615 stands), WORKLOG.
"""
from __future__ import annotations

import glob
import subprocess

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html"]
THEIR_COMMIT = "7efbfb1bc"          # their v0.688.0 KAAM MANCH

MAIN_PREFIX = 'APP_VERSION = "0.688.0"   # '
SPLIT_MARK = " Previous head v0.687.0"
MY_ONE_LINER = ("the Leads Desk answers again - the desk called GET /api/leads/overview, the server serves "
                "GET /api/leads, the 404 killed the first-load Promise.all into a red \"Not Found\"; the call "
                "is the canonical route now + the seam test fires the first-load trio")
CLAUDE_MARK = "Current version: v0.688.0"
HIST_SPLIT = "## v0.687.0 LEADS EMPLOYEE"
FRAMES_PAIR = ("their LEADS EMPLOYEE line rides the Previous chain)",
               "their KAAM MANCH line rides the Previous chain)")


def their_file(path: str) -> str:
    out = subprocess.run(["git", "show", f"{THEIR_COMMIT}:{path}"], capture_output=True, text=True, check=True)
    return out.stdout


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

    # ---------- their layers, verbatim from their commit
    their_main_line = next(l for l in their_file(f"{ROOT}/app/main.py").splitlines()
                           if l.startswith("APP_VERSION = "))
    assert "KAAM MANCH" in their_main_line and their_main_line.startswith(MAIN_PREFIX), "their main head moved"
    their_body = their_main_line[len(MAIN_PREFIX):]
    cut = their_body.find(" Previous head")
    assert cut > 0, "their chain tail not found"
    their_clause = their_body[:cut]                      # their story body only, no chain

    their_claude_line = next(l for l in their_file("CLAUDE.md").splitlines() if l.startswith(CLAUDE_MARK))
    assert "KAAM MANCH" in their_claude_line and "previous head v0.687.0" in their_claude_line, \
        "their claude line moved"
    their_claude_tail = their_claude_line[len("Current version: "):]

    their_hist = their_file("docs/HISTORY.md")
    assert their_hist.startswith("## v0.688.0 KAAM MANCH"), "their history head moved"
    their_hist_section = their_hist[:their_hist.find(HIST_SPLIT)].rstrip() + "\n"

    # ---------- 1. main.py: splice my story -> their clause -> my chain (v0.687 -> deeper)
    src = open(f"{ROOT}/app/main.py", encoding="utf-8").read()
    my_line = next(l for l in src.splitlines() if l.startswith("APP_VERSION = "))
    assert "LEADS DESK SEAM" in my_line, "my main head moved"
    head_story, rest = my_line.split(SPLIT_MARK, 1)      # rest = ' LEADS EMPLOYEE (owner: ...' chain tail
    new_line = head_story.replace("0.688.0", "0.689.0") + " Previous head " + their_clause \
        + SPLIT_MARK + rest
    assert new_line.count("Previous head") == my_line.count("Previous head") + 1
    for marker in ("KAAM MANCH", "LEADS EMPLOYEE", "LEADS DESK SEAM", "webstudio"):
        assert marker in new_line, marker
    open(f"{ROOT}/app/main.py", "w", encoding="utf-8").write(src.replace(my_line, new_line))
    add("main", 1)

    # ---------- 2. pubspec
    n = sweep("pubspec.yaml", [("version: 0.688.0+687", "version: 0.689.0+688")])
    add("pubspec", n)

    # ---------- 3. CLAUDE.md: my head clause + their correct chain
    src = open("CLAUDE.md", encoding="utf-8").read()
    my_claude = next(l for l in src.splitlines() if l.startswith(CLAUDE_MARK))
    new_claude = (f"Current version: v0.689.0 (pubspec 0.689.0+688; LEADS DESK SEAM v0.689.0 = {MY_ONE_LINER}"
                  f"); previous head " + their_claude_tail)
    open("CLAUDE.md", "w", encoding="utf-8").write(src.replace(my_claude, new_claude))
    add("claude", 1)

    # ---------- 4. HISTORY.md: my re-headed section + their section restored + the v0.687 tail
    src = open("docs/HISTORY.md", encoding="utf-8").read()
    assert src.startswith("## v0.688.0 LEADS DESK SEAM"), "my history head moved"
    rest_hist = src[src.find(HIST_SPLIT):]               # the v0.687 section onward, untouched
    my_section = (
        "## v0.689.0 LEADS DESK SEAM — the desk's first load answers (8 Nov 2026; owner: \"NOW A PERFECT "
        "LEAD DESK FOR IT\" + a screenshot of the Leads Desk showing a red \"Not Found\"; built as v0.688.0, "
        "their KAAM MANCH took v0.688.0 mid-push — REBASE PROTOCOL onto their tip, their story restored "
        "verbatim as the Previous chain)\n\n"
        "The v0.687 desk was wired to a route that did not exist: its first load was "
        "`Promise.all([GET /api/leads/overview, GET /api/leads/runs?limit=12, GET /api/leads/outreach?limit=100])`, "
        "the server's overview route is `GET /api/leads` (the router itself is the overview since v0.544) — one 404 "
        "killed the whole `Promise.all`, the `catch` painted the message red, and a desk with six of seven routes "
        "working looked dead on open.\n\n"
        "- **THE FIX** — one line in `employees.js`: the desk calls the canonical `GET /api/leads`. No new route, "
        "no alias, no second name for the same thing.\n"
        "- **THE GUARD** — NEW `test_v0689_leads_desk_seam.py` (4 tests, zero network): extracts EVERY "
        "`api('METHOD', '/api/leads…')` call from the console sources and asserts each `(method, path)` against the "
        "REAL FastAPI route table; the ghost route is asserted gone; the desk's exact first-load trio is FIRED over "
        "the TestClient (200/200/200 with the key, 401 without; the overview carries the nine keys the desk renders "
        "on first paint). The v0.687 test had checked each side separately — the seam is now checked whole. Proven "
        "the honest way: with the old call restored, the seam file fails 3/4.\n"
        "- `test_v0687`'s surface pin healed to the canonical path (it had pinned the bug).\n"
        "- Version ritual: `scripts/ritual_0689.py` (first cut `scripts/ritual_0688.py` rode the pre-collision "
        "round) — the COLLISION release: main.py APP_VERSION + story head with their KAAM MANCH clause spliced as "
        "the Previous head (their main chain had skipped v0.687 — spliced, not replaced: this story → KAAM MANCH → "
        "LEADS EMPLOYEE → the deeper chain, nothing lost), pubspec 0.689.0+688, CLAUDE.md current-version line "
        "(their v0.688 line as previous head), HISTORY: their v0.688 section restored verbatim, test pins → "
        "0.689.0/+688, console stamps `?v=0.689.0`, the leads parser stamps v0.688.0-* → v0.689.0-*, the "
        "newest-story pin moved to the v0.689.0 marker (test_v0475), the release's test renamed "
        "test_v0689_leads_desk_seam.py.\n\n\n")
    open("docs/HISTORY.md", "w", encoding="utf-8").write(my_section + their_hist_section + "\n" + rest_hist)
    add("history", 1)

    # ---------- 9. rename this release's test to its shipping version
    import os
    old_t = f"{ROOT}/tests/test_v0688_leads_desk_seam.py"
    new_t = f"{ROOT}/tests/test_v0689_leads_desk_seam.py"
    if os.path.exists(old_t):
        os.rename(old_t, new_t)
        add("rename", 1)

    # ---------- 5-8. the sweeps
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [("0.688.0+687", "0.689.0+688"), ("0.688.0", "0.689.0"),
                      ('startswith("v0.688")', 'startswith("v0.689")'), FRAMES_PAIR])
        if n:
            add("tests", n)
    for f in STATICS:
        n = sweep(f, [("?v=0.688.0", "?v=0.689.0")])
        if n:
            add("stamps", n)
    for f in sorted(glob.glob(f"{ROOT}/app/leads/*.py")):
        n = sweep(f, [("v0.688.0-", "v0.689.0-")])
        if n:
            add("parsers", n)
    print("ritual_0689:", total)


if __name__ == "__main__":
    main()
