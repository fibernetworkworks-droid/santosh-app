"""v0.999 /test-coverage, from ECC's test-coverage command (affaan-m/ECC, MIT; the idea is theirs, the code is Hoola's).

ECC's command finds the files under 80% coverage and writes tests for them. Hoola Code points it at what matters in a
session: the lines THIS session changed. In code, before the round starts, Hoola reads the working copy's diff and lists
every changed line by file (so the coder cannot guess); the round then runs the repo's own coverage tool in the box,
says which of those lines no test runs, writes the missing tests (happy path, errors, edges, each branch) until the
changed lines reach 80% - or the most it can - runs them, and reports before / after. `/test-coverage report` only reports
and writes nothing. Switch: `dev_test_coverage` (default on).
"""
from __future__ import annotations

import re
from typing import Any

CREDIT = "(adapted from ECC's /test-coverage)"
CODE = re.compile(r"(?i)\.(py|pyi|js|jsx|mjs|cjs|ts|tsx|go|rs|java|kt|kts|scala|rb|php|cs|fs|swift|dart|c|cc|cpp|cxx|h|hpp|"
                  r"m|mm|ex|exs|erl|clj|lua|r|jl|vue|svelte|gd)$")
TESTY = re.compile(r"(?i)(^|/)(tests?|spec|__tests__)(/|$)|(^|/)test_[^/]*$|_test\.\w+$|\.(test|spec)\.\w+$")


def on() -> bool:
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "dev_test_coverage", True))
    except Exception:  # noqa: BLE001
        return True


def parse_cmd(words: str) -> tuple[bool, bool]:
    """(is it /test-coverage, report only)."""
    m = re.match(r"^\s*/test-coverage\b\s*(\S*)", words or "", re.I)
    if not m:
        return False, False
    return True, m.group(1).lower() in ("report", "only", "check", "--report")


def changed_lines(diff: str) -> dict[str, list[int]]:
    """{file: [new line numbers the diff adds]} for code files that are not tests."""
    out: dict[str, list[int]] = {}
    cur, n = "", 0
    for ln in (diff or "").splitlines():
        if ln.startswith("+++ "):
            p = ln[4:].strip()
            cur = p[2:] if p.startswith("b/") else ("" if p == "/dev/null" else p)
            continue
        if ln.startswith("--- "):
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", ln)
        if m:
            n = int(m.group(1))
            continue
        if not cur:
            continue
        if ln.startswith("+"):
            if CODE.search(cur) and not TESTY.search(cur) and ln[1:].strip():
                out.setdefault(cur, []).append(n)
            n += 1
        elif ln.startswith("-"):
            continue
        else:
            n += 1
    return out


def ranges(nums: list[int]) -> str:
    nums = sorted(set(nums))
    parts, start, prev = [], None, None
    for x in nums:
        if start is None:
            start = prev = x
        elif x == prev + 1:
            prev = x
        else:
            parts.append(f"{start}" if start == prev else f"{start}-{prev}")
            start = prev = x
    if start is not None:
        parts.append(f"{start}" if start == prev else f"{start}-{prev}")
    return ", ".join(parts)


def command_text(diff: str, report_only: bool) -> str:
    lines = changed_lines(diff)
    if lines:
        listing = "\n".join(f"- {f}: lines {ranges(v)} ({len(v)} lines)" for f, v in sorted(lines.items())[:60])
        scope = ("The code lines this session changed (worked out by Hoola from the working copy's diff - this is the "
                 "list to measure):\n" + listing)
    else:
        scope = ("This session has not changed any code lines yet, so measure the whole repo instead and list the "
                 "files under 80%, worst first.")
    work = ("Report only: change NO file." if report_only else
            "Then write the missing tests for the uncovered changed lines - the normal case, error cases, edge cases "
            "(empty, null, limits) and each branch - in the repo's own test style and folders, until the changed lines "
            "reach 80% (or the most you can). Run them; every new test must pass. Never change the code under test to "
            "make a test pass, and never lower a coverage setting.")
    return ("<her_command>/test-coverage</her_command>\nShe wants to know which changed lines no test runs " + CREDIT
            + ".\n" + scope + "\n\nSteps:\n1. Find the repo's test framework and its coverage tool from its files "
            "(pytest + coverage / pytest-cov, jest --coverage, vitest --coverage, go test -coverprofile, cargo llvm-cov / "
            "tarpaulin, jacoco, dart/flutter test --coverage, simplecov...). Use the repo's own test command if it has "
            "one. The box has no network: if the coverage tool is not installed, say exactly that and which line "
            "would install it - never guess numbers.\n2. Run the tests with coverage and read the per-line result for "
            "the files above. List, per file, the changed lines that NO test runs.\n3. " + work
            + "\n4. In done: a short table - file | changed lines | covered before | covered after - then the lines "
            "still not covered and why (e.g. a branch that needs a real network). Put the exact commands in test_plan.")
