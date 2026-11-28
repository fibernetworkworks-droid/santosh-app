"""A GitHub Actions pipeline guard: on every pull request that changes .github/workflows it reads each workflow file with the desk's
own line rules (third-party actions not pinned to a commit SHA, event text put into a shell, permissions: write-all, curl | bash)
plus two file rules (no top-level permissions; pull_request_target that checks out the pull request's code) and fails the check
on any of them, listing each with its line in the run's summary. Her trusted owners are not asked to pin. It needs no keys and
changes nothing."""
from __future__ import annotations

import re
from typing import Any

from .common import DsoInputError
from .workflows import LINE_RULES, TRUSTED


class CiError(DsoInputError):
    pass


GUARD = r'''import glob, os, re, sys
RULES = @RULES@
OWNERS = @OWNERS@
FAIL = @FAIL@
hits = []
files = sorted(glob.glob(".github/workflows/*.yml") + glob.glob(".github/workflows/*.yaml")) if len(sys.argv) < 2 else sys.argv[1:]
for f in files:
    src = open(f, encoding="utf-8").read()
    lines = src.split("\n")
    for n, ln in enumerate(lines, 1):
        for rid, sev, pat, what, fix in RULES:
            m = re.search(pat, ln, re.I if rid == "curl-sh" else 0)
            if not m:
                continue
            if rid == "unpinned-action" and m.group(1).lower().startswith(OWNERS):
                continue
            hits.append((sev, rid, what, f, n))
    if not re.search(r"(?m)^permissions:", src):
        hits.append(("warn", "no-permissions", "No top-level permissions", f, 1))
    if re.search(r"(?m)^\s*pull_request_target\s*:|^on:\s*\[?[^\n]*pull_request_target", src) and re.search(r"ref:\s*\$\{\{\s*(github\.event\.pull_request\.head\.(sha|ref)|github\.head_ref)", src):
        hits.append(("bad", "prt-checkout", "pull_request_target checks out the pull request's code", f, 1))
order = {"bad": 0, "warn": 1, "info": 2}
bad = [h for h in hits if order[h[0]] <= order[FAIL]]
with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as s:
    s.write(f"## Pipeline guard\n\n{len(files)} workflow file(s), {len(hits)} finding(s), {len(bad)} failing.\n\n")
    if hits:
        s.write("| level | rule | file | line |\n|---|---|---|---|\n" + "\n".join(f"| {a} | {b} | {d} | {e} |" for a, b, c, d, e in hits) + "\n")
for sev, rid, what, f, n in bad:
    print(f"::error file={f},line={n}::{what} ({rid})")
print(f"{len(files)} file(s), {len(hits)} finding(s), {len(bad)} failing")
sys.exit(1 if bad else 0)
'''


def workflow(fail_level: str = "warn", trusted_owners: str = "", runner: str = "ubuntu-24.04") -> dict[str, Any]:
    if fail_level not in ("bad", "warn"):
        raise CiError("Fail on: serious only (bad) or anything to fix (warn).")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    own = [o.strip().rstrip("/") for o in str(trusted_owners or "").split(",") if o.strip()]
    for o in own:
        if not re.fullmatch(r"[\w.\-]{1,60}", o):
            raise CiError(f"Trusted owner '{o}': a GitHub user or organisation name.")
    owners = tuple(TRUSTED) + tuple(o.lower() + "/" for o in own)
    guard = GUARD.replace("@RULES@", repr(LINE_RULES)).replace("@OWNERS@", repr(owners)).replace("@FAIL@", repr(fail_level))
    body = "\n".join("          " + ln if ln else "" for ln in guard.splitlines())
    yml = f"""name: Pipeline guard
# Added by you from the DevSecOps Engineer desk. It reads the workflow files in this pull request and fails on the ways
# pipelines are attacked. It needs no keys and changes nothing.
on:
  pull_request:
    paths:
      - ".github/workflows/**"
permissions:
  contents: read
jobs:
  guard:
    runs-on: {runner}
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - name: Check the workflows
        shell: python3 {{0}}
        run: |
{body}
"""
    return {"file": ".github/workflows/pipeline-guard.yml", "yaml": yml, "fail_level": fail_level, "owners": list(owners), "runner": runner,
            "steps": ["Add the file to .github/workflows in a pull request - the guard checks itself too.",
                      "Make 'Pipeline guard' a required check on the default branch.",
                      "Pin the actions it names to commit SHAs (Dependabot can keep pinned SHAs up to date)."],
            "note": "It reads only the workflow files in the pull request; it needs no keys and no cloud access."}
