"""A GitHub Actions security gate: on every pull request it diffs the branch against its base and runs the desk's own risky-code
patterns on the lines the pull request adds (the same rules as the Code page), failing the check at her chosen level (high, or
medium too) and writing each hit - masked - to the run's summary. It needs no keys and no network beyond the checkout; nothing is
pushed or changed. It is a first pass, not a replacement for a full scanner."""
from __future__ import annotations

import re
from typing import Any

from .code import EXT, PLACEHOLDER, RULES
from .common import SecInputError


class CiError(SecInputError):
    pass


GUARD = r'''import os, re, subprocess, sys
RULES = @RULES@
EXT = @EXT@
PLACEHOLDER = re.compile(@PH@, re.I)
FAIL = @FAIL@
CI_FLAGS = ("weak-hash", "hardcoded-secret", "weak-random", "debug-on", "sql-concat")
base = os.environ.get("BASE_SHA") or "origin/" + os.environ.get("GITHUB_BASE_REF", "main")
diff = subprocess.run(["git", "diff", "-U0", "--no-color", base + "...HEAD"], capture_output=True, text=True).stdout if len(sys.argv) < 2 else open(sys.argv[1]).read()
rows, f, n = [], "", 0
for ln in diff.split("\n"):
    if ln.startswith("+++ "):
        f = re.sub(r"^b/", "", ln[4:].strip()); continue
    if ln.startswith(("--- ", "diff --git", "index ")):
        continue
    m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", ln)
    if m:
        n = int(m.group(1)); continue
    if ln.startswith("+"):
        rows.append((f, n, ln[1:])); n += 1
    elif not ln.startswith("-"):
        n += 1
hits = []
for f, n, code in rows:
    if not code.strip() or re.match(r"^\s*(#|//|\*|/\*)", code):
        continue
    lg = EXT.get(f.rsplit(".", 1)[-1].lower() if "." in f else "", "")
    for rid, langs, sev, cwe, pat, what, fix in RULES:
        if langs is not None and lg and lg not in {EXT.get(x, x) for x in langs}:
            continue
        m = re.search(pat, code, re.I if rid in CI_FLAGS else 0)
        if not m:
            continue
        if rid == "hardcoded-secret" and (PLACEHOLDER.match(m.group(2)) or re.search(r"os\.environ|getenv|process\.env|config\[", code)):
            continue
        if rid == "eval" and lg == "py" and re.search(r"\.eval\s*\(|literal_eval", code):
            continue
        hits.append((sev, rid, cwe, what, f, n))
order = {"high": 0, "medium": 1, "low": 2}
bad = [h for h in hits if order[h[0]] <= order[FAIL]]
with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as s:
    s.write(f"## Security gate\n\n{len(rows)} added line(s), {len(hits)} risky place(s), {len(bad)} at {FAIL} or above.\n\n")
    if hits:
        s.write("| severity | rule | CWE | file | line |\n|---|---|---|---|---|\n" + "\n".join(f"| {a} | {b} | {c} | {e} | {g} |" for a, b, c, d, e, g in hits) + "\n")
for sev, rid, cwe, what, f, n in bad:
    print(f"::error file={f},line={n}::{what} ({rid}, {cwe})")
print(f"{len(rows)} added line(s), {len(hits)} hit(s), {len(bad)} failing")
sys.exit(1 if bad else 0)
'''


def workflow(fail_level: str = "high", runner: str = "ubuntu-24.04", branches: str = "") -> dict[str, Any]:
    if fail_level not in ("high", "medium", "low"):
        raise CiError("Fail level: high, medium or low.")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    br = [b.strip() for b in str(branches or "").split(",") if b.strip()]
    for b in br:
        if not re.fullmatch(r"[\w./\-*]{1,80}", b):
            raise CiError(f"Branch '{b}': letters, digits, / . - and * only.")
    guard = (GUARD.replace("@RULES@", repr(RULES)).replace("@EXT@", repr(EXT)).replace("@PH@", repr(PLACEHOLDER.pattern)).replace("@FAIL@", repr(fail_level)))
    body = "\n".join("          " + ln if ln else "" for ln in guard.splitlines())
    on = "  pull_request:\n" + (("    branches:\n" + "".join(f'      - "{b}"\n' for b in br)) if br else "")
    yml = f"""name: Security gate
# Added by you from the Security Engineer desk. It reads the lines this pull request adds and fails on risky code
# at {fail_level} or above. It needs no keys and changes nothing.
on:
{on}permissions:
  contents: read
jobs:
  gate:
    runs-on: {runner}
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Check the added lines
        env:
          BASE_SHA: ${{{{ github.event.pull_request.base.sha }}}}
        shell: python3 {{0}}
        run: |
{body}
"""
    return {"file": ".github/workflows/security-gate.yml", "yaml": yml, "fail_level": fail_level, "runner": runner,
            "steps": ["Add the file to your repository's .github/workflows folder in a pull request.",
                      "Make 'Security gate' a required check in the branch protection rules.",
                      "Keep a full scanner (CodeQL, Semgrep, Trivy) too - this gate is a fast first pass on the new lines."],
            "note": "It reads only the pull request's own lines; it needs no keys and no cloud access."}
