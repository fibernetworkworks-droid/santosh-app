#!/usr/bin/env python3
"""ritual_0711 finisher: the 4 registry-pin files the main sweep's ', \"' pattern could not reach
(the paren form `== 616, (\"...\")` and the in-src string check `\"len(TOOLS) == 616\" in src`),
then the full zero-residual proof and a mirror check. STEP 3 (added after the first run): the repair
regex - the main ritual inserted its clause with a closing quote, breaking 29 string literals;
plan). "(?=non-space) -> plan).  rebuilt every file and proved zero breakage with py_compile."""
from __future__ import annotations

import glob
import subprocess

ROOT = "/home/z/my-project/seekh-wt"
MY_CLAUSE = ('616 + 1 seekh_video (v0.711 SEEKH MANCH: the learn-from-video bridge tool, owner \'GO\' on '
             "the SEEKH MANCH plan). ")


def sweep(path: str, pairs: list[tuple[str, str]]) -> int:
    src = open(path, encoding="utf-8").read()
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
    # the paren-form pins (duniya / jharokha / kala / aep1's own pin) + the in-src needle
    for f in sorted(glob.glob(f"{ROOT}/server/tests/*.py")):
        n = sweep(f, [('== 616, ("', f'== 617, ("{MY_CLAUSE}"'),
                    ('"len(TOOLS) == 616" in src', '"len(TOOLS) == 617" in src'),
                    ('"len(tools.TOOLS) == 616" in src', '"len(tools.TOOLS) == 617" in src')])
        if n:
            print("fixed", f.split("/")[-1], n)

    # zero-residual proof (version + registry)
    for pat in ("0.710.0", "== 616"):
        out = subprocess.run(["grep", "-rn", pat, f"{ROOT}/server/tests", "--include=*.py"],
                             capture_output=True, text=True).stdout.strip()
        assert not out, f"residual {pat}:\n{out[:2000]}"
    print("zero residual in tests: OK")

    # mirror check
    main_src = open(f"{ROOT}/server/app/main.py", encoding="utf-8").read()
    line = next(l for l in main_src.splitlines() if l.startswith("APP_VERSION = "))
    assert line.startswith('APP_VERSION = "0.711.0"   # SEEKH MANCH v0.711.0 = '), line[:120]
    assert "Previous: ARCHITECT OPUS v0.710.0" in line
    pub = open(f"{ROOT}/pubspec.yaml", encoding="utf-8").read()
    assert "version: 0.711.0+710" in pub
    claude = open(f"{ROOT}/CLAUDE.md", encoding="utf-8").read()
    assert claude.count("Current version: v0.711.0") == 1 and "previous head v0.710.0" in claude
    hist = open(f"{ROOT}/docs/HISTORY.md", encoding="utf-8").read()
    assert hist.startswith("## v0.711.0 SEEKH MANCH") and "## v0.694.0 WEB CLONE" in hist
    wl = open(f"{ROOT}/docs/WORKLOG.md", encoding="utf-8").read()
    assert wl.count("Task ID: v0.711.0 SEEKH MANCH") == 1
    v475 = open(f"{ROOT}/server/tests/test_v0475_console_frames.py", encoding="utf-8").read()
    assert "'SEEKH MANCH' in main and '0.711.0' in main" in v475, v475[:0]
    stamps = sum(open(f, encoding="utf-8").read().count("?v=0.711.0")
                 for f in ("v2.html", "webstudio.html", "appstudio.html")
                 for f in [f"{ROOT}/server/app/static/console/{f}"])
    assert stamps == 32, stamps
    print("mirrors: OK (main, pubspec, CLAUDE, HISTORY, WORKLOG, v0475, 32 stamps)")


if __name__ == "__main__":
    main()
