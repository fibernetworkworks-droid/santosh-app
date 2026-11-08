#!/usr/bin/env python3
"""v0.691.0 version ritual - LEADS DESK EMPTY re-head after the SECOND v0.690.0 COLLISION.

COLLISION: the release was built as v0.690.0 while the dev chain shipped its own v0.690.0 MANN KI BAAT
(bb12ca32d, audit wave 13, built as 0.686) mid-push - the second collision in a row. REBASE PROTOCOL onto
their tip: their code kept whole; their story layers ride the Previous chain. One splice again: their
main.py chain SKIPS this release's v0.689.0 LEADS DESK SEAM clause (theirs: v0.690 -> v0.688), so the chain
is SPLICED - this release's story -> their MANN KI BAAT clause -> the v0.689 LEADS DESK SEAM clause ->
their v0.688 tail - chronological, nothing lost. Their CLAUDE.md line chains correctly (v0.690 -> v0.689
-> ...) and composes normally. Their HISTORY section exists at their own anchor (verbatim, untouched).
Sweeps:

  1. main.py: APP_VERSION 0.690.0 -> 0.691.0 (LEADS DESK EMPTY head) + their MANN KI BAAT clause spliced
     as the Previous head + this release's own v0.689 clause and deeper chain kept from the release line
  2. pubspec.yaml: 0.690.0+689 -> 0.691.0+690
  3. CLAUDE.md: current-version line re-headed v0.691.0; their v0.690 MANN KI BAAT line (with its correct
     v0.689 chain) as previous head
  4. docs/HISTORY.md: this release's section re-headed v0.691.0 (collision noted) PREPENDED; their v0.690
     MANN KI BAAT section stays at their anchor verbatim
  5. tests: pins 0.690.0+689 -> 0.691.0+690; bare 0.690.0 -> 0.691.0 (incl. their suites);
     parser prefix startswith("v0.690") -> startswith("v0.691")
  6. static console stamps -> "?v=0.691.0" (v2.html + webstudio.html)
  7. leads parser stamps v0.690.0-* -> v0.691.0-* (source)
  8. the newest-story pin (test_v0475) re-headed to the v0.691.0 marker (their MANN KI BAAT line noted)
  9. this release's test renamed test_v0690_leads_desk_scope.py -> test_v0691_leads_desk_scope.py (born in
     the collision round, ships as v0.691; the docstring re-heads through the bare sweep)

NOT touched: their scripts (this release's scripts/ritual_0690.py stays as the pre-collision record), the
registry pins (615 stands), WORKLOG.
"""
from __future__ import annotations

import glob
import os
import subprocess

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html"]
MY_COMMIT = "9f3938042"             # this release, pre-rebase (its main.py line carries my story + my chain)

MAIN_PREFIX = 'APP_VERSION = "0.690.0"   # '
SPLIT_MARK = " Previous head "
MY_ONE_LINER = ("the desk's \"Loading…\" forever healed - it called the Education desk's local `empty` helper, "
                "ReferenceError at first render, the fetches all 200; the desk carries its own now + the "
                "reachability guard")
CLAUDE_MARK = "Current version: v0.690.0"
FRAMES_OLD = ("""    assert 'MANN KI BAAT' in main and 'webstudio' in main  # the newest-story precedent (v0.690.0 """
              """carries the marker; LEADS DESK SEAM rides the Previous chain)""")
FRAMES_NEW = ("""    assert 'LEADS DESK EMPTY' in main and 'webstudio' in main  # the newest-story precedent (v0.691.0 """
              """carries the marker; their MANN KI BAAT line rides the Previous chain)""")


def commit_file(sha: str, path: str) -> str:
    out = subprocess.run(["git", "show", f"{sha}:{path}"], capture_output=True, text=True, check=True)
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

    # ---------- the two main.py lines: mine (release) and theirs (their tip, now the working file)
    my_line = next(l for l in commit_file(MY_COMMIT, f"{ROOT}/app/main.py").splitlines()
                   if l.startswith("APP_VERSION = "))
    assert "LEADS DESK EMPTY" in my_line, "my release line moved"
    my_story, my_chain = my_line.split(SPLIT_MARK, 1)          # my_chain: 'Previous head v0.689.0 ...'
    my_story_bumped = my_story.replace("0.690.0", "0.691.0")

    src = open(f"{ROOT}/app/main.py", encoding="utf-8").read()
    their_line = next(l for l in src.splitlines() if l.startswith("APP_VERSION = "))
    assert "MANN KI BAAT" in their_line and their_line.startswith(MAIN_PREFIX), "their main head moved"
    their_tail = their_line[len(MAIN_PREFIX):]
    cut = their_tail.find(SPLIT_MARK)
    assert cut > 0, "their chain tail not found"
    their_clause = their_tail[:cut]

    new_line = my_story_bumped + SPLIT_MARK + their_clause + SPLIT_MARK + my_chain
    for marker in ("MANN KI BAAT", "LEADS DESK SEAM", "LEADS DESK EMPTY", "KAAM MANCH", "LEADS EMPLOYEE",
                   "webstudio"):
        assert marker in new_line, marker
    assert new_line.count("Previous head") == my_line.count("Previous head") + 1
    order = [new_line.find(m) for m in ("v0.691.0 LEADS DESK EMPTY", "v0.690.0 MANN KI BAAT",
                                        "Previous head v0.689.0 LEADS DESK SEAM", "Previous head v0.688.0",
                                        "Previous head v0.687.0")]
    assert all(p != -1 for p in order) and order == sorted(order), order
    open(f"{ROOT}/app/main.py", "w", encoding="utf-8").write(src.replace(their_line, new_line))
    add("main", 1)

    # ---------- 2. pubspec
    n = sweep("pubspec.yaml", [("version: 0.690.0+689", "version: 0.691.0+690")])
    add("pubspec", n)

    # ---------- 3. CLAUDE.md: my head clause + their correct chain
    src = open("CLAUDE.md", encoding="utf-8").read()
    their_claude = next(l for l in src.splitlines() if l.startswith(CLAUDE_MARK))
    assert "MANN KI BAAT" in their_claude and "previous head v0.689.0" in their_claude, "their claude moved"
    new_claude = (f"Current version: v0.691.0 (pubspec 0.691.0+690; LEADS DESK EMPTY v0.691.0 = {MY_ONE_LINER}"
                  f"); previous head " + their_claude[len("Current version: "):])
    open("CLAUDE.md", "w", encoding="utf-8").write(src.replace(their_claude, new_claude))
    add("claude", 1)

    # ---------- 4. HISTORY.md: re-head this release's section to v0.691.0, collision noted, prepended
    src = open("docs/HISTORY.md", encoding="utf-8").read()
    assert src.startswith("## v0.690.0 LEADS DESK EMPTY"), "my history head moved"
    assert "## v0.690.0 MANN KI BAAT" in src, "their MANN section must stay in the record"
    old_my_head = ("## v0.690.0 LEADS DESK EMPTY — the desk renders (8 Nov 2026; owner: \"it stuck on loading\" "
                   "+ a screenshot of the desk stuck at \"Loading…\")")
    assert old_my_head in src
    my_section = (
        "## v0.691.0 LEADS DESK EMPTY — the desk renders (8 Nov 2026; owner: \"it stuck on loading\" + a "
        "screenshot of the desk stuck at \"Loading…\"; built as v0.690.0, their MANN KI BAAT took v0.690.0 "
        "mid-push — the SECOND collision in a row — REBASE PROTOCOL onto their tip, their story restored as "
        "the Previous chain, their main chain spliced to keep the v0.689 clause)\n\n"
        "The v0.689 fix removed the 404 — and the desk STILL hung at \"Loading…\", now with all three "
        "first-load fetches green (200/200/200). Reproduced end-to-end in a real browser against the real app "
        "(login → hub → Business → Open desk), the rejection caught live: `ReferenceError: empty is not "
        "defined at Object.leads` — the desk called `empty(...)`, which is the EDUCATION desk's LOCAL helper "
        "(a `const` inside `async function edu(el)`), invisible from the leads desk. The Loading div went up, "
        "the render threw before the first `innerHTML =`, the promise rejected unhandled: a dead desk with a "
        "green network tab.\n\n"
        "- **THE FIX** — the desk carries its own `empty` (the same helper, the same pattern each desk uses "
        "for its own).\n"
        "- **THE GUARD** — NEW `test_v0691_leads_desk_scope.py` (3 tests, zero network): the desk's own "
        "`empty` pinned; every function the desk body calls must be REACHABLE (a destructured param of the "
        "HoolaEmployees wrapper, a definition at the wrapper's own scope, or a definition inside the desk body "
        "itself) — a helper living only inside another desk's closure fails the test; the v0.689 route-seam "
        "law re-asserted through it. The v0.687-era string-presence tests never ran the JS, which is why both "
        "this and the route bug sailed through.\n"
        "- **THE PROOF** — the browser walk re-run after the fix: the desk renders fully (the pitch, the "
        "Seekh trust tag, the five KPIs with the 20,000/day cap named, all five lanes Built, the store line, "
        "Recent runs, the Outreach ledger), zero unhandled rejections.\n"
        "- Version ritual: `scripts/ritual_0691.py` (first cut `scripts/ritual_0690.py` rode the pre-collision "
        "round) — the COLLISION release: main.py APP_VERSION + story head with their MANN KI BAAT clause "
        "spliced as the Previous head (their main chain had skipped v0.689 — spliced, not replaced), pubspec "
        "0.691.0+690, CLAUDE.md current-version line (their v0.690 line as previous head), their v0.690 HISTORY "
        "section stays at their anchor verbatim, test pins → 0.691.0/+690, console stamps `?v=0.691.0`, the "
        "leads parser stamps v0.690.0-* → v0.691.0-*, the newest-story pin moved to the v0.691.0 marker "
        "(test_v0475), the release's test renamed test_v0691_leads_desk_scope.py.\n\n\n")
    # drop the old v0.690 section (up to the next section head) and prepend the v0.691 one
    start = src.index(old_my_head)
    nxt = src.find("\n## v0.", start + 10)
    src = my_section + src[nxt + 2:]
    open("docs/HISTORY.md", "w", encoding="utf-8").write(src)
    add("history", 1)

    # ---------- 9. rename this release's test to its shipping version
    old_t = f"{ROOT}/tests/test_v0690_leads_desk_scope.py"
    new_t = f"{ROOT}/tests/test_v0691_leads_desk_scope.py"
    if os.path.exists(old_t):
        os.rename(old_t, new_t)
        add("rename", 1)

    # ---------- 5-8. the sweeps
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [("0.690.0+689", "0.691.0+690"), ("0.690.0", "0.691.0"),
                      ('startswith("v0.690")', 'startswith("v0.691")'), (FRAMES_OLD, FRAMES_NEW)])
        if n:
            add("tests", n)
    for f in STATICS:
        n = sweep(f, [("?v=0.690.0", "?v=0.691.0")])
        if n:
            add("stamps", n)
    for f in sorted(glob.glob(f"{ROOT}/app/leads/*.py")):
        n = sweep(f, [("v0.690.0-", "v0.691.0-")])
        if n:
            add("parsers", n)
    print("ritual_0691:", total)


if __name__ == "__main__":
    main()
