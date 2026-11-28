"""A GitHub Actions workflow that guards her data pipeline: on every pull request it runs her data test command (dbt build, pytest,
Great Expectations - whatever she uses), then compares the schema her command writes (a JSON of column -> type, or a list of
{name, type}) with the contract committed in her repository, and fails on a column removed or a type changed - the summary of
the comparison written to the run. The file is text she adds herself; nothing is pushed."""
from __future__ import annotations

import re
from typing import Any

from .common import DeInputError


class CiError(DeInputError):
    pass


def _cmd(v: str, what: str, need: bool) -> str:
    v = str(v or "").strip()
    if not v:
        if need:
            raise CiError(f"{what}: the command that runs your data tests (e.g. dbt build --select state:modified+).")
        return ""
    if "\n" in v or "\r" in v or len(v) > 400:
        raise CiError(f"{what}: one line, up to 400 characters.")
    if "${{" in v:
        raise CiError(f"{what}: no ${{{{ }}}} expressions - they would run inside the workflow.")
    return v


def _path(v: str, what: str, need: bool = True) -> str:
    v = str(v or "").strip()
    if not v and not need:
        return ""
    if not re.fullmatch(r"[\w./\-]{1,160}", v) or ".." in v or v.startswith("/"):
        raise CiError(f"{what}: a path inside the repository, such as contracts/orders.json.")
    return v


COMPARE = r'''import json, os, sys
def load(p):
    d = json.load(open(p))
    if isinstance(d, dict) and "columns" in d:
        d = d["columns"]
    if isinstance(d, list):
        d = {c["name"]: str(c.get("type") or c.get("data_type") or "") for c in d}
    return {str(k).lower(): str(v).lower().replace(" ", "") for k, v in d.items()}
new, con = load(sys.argv[1]), load(sys.argv[2])
rows, fail = [], []
for k in sorted(set(new) | set(con)):
    if k not in new:
        fail.append(f"{k} is in the contract but the build no longer has it")
        rows.append(f"| {k} | {con[k]} | missing | FAIL |")
    elif k not in con:
        rows.append(f"| {k} | new | {new[k]} | added |")
    elif new[k] != con[k]:
        fail.append(f"{k}: {con[k]} -> {new[k]}")
        rows.append(f"| {k} | {con[k]} | {new[k]} | FAIL |")
    else:
        rows.append(f"| {k} | {con[k]} | {new[k]} | same |")
with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as s:
    s.write("## Schema contract\n\n| column | contract | this pull request | |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
print("\n".join(rows))
for f in fail:
    print("::error::" + f)
sys.exit(1 if fail else 0)
'''


def workflow(test_cmd: str = "", schema: str = "", contract: str = "", setup_cmd: str = "", python: str = "3.12", runner: str = "ubuntu-24.04") -> dict[str, Any]:
    tc = _cmd(test_cmd, "Data test command", True)
    st = _cmd(setup_cmd, "Setup command", False)
    sp, cp = _path(schema, "Schema file", False), _path(contract, "Contract file", False)
    if bool(sp) != bool(cp):
        raise CiError("Give both the schema file your command writes and the contract file - or neither.")
    if sp and sp == cp:
        raise CiError("The schema file and the contract must be different files.")
    if not re.fullmatch(r"3\.\d{1,2}", str(python)):
        raise CiError("Python: a version such as 3.12.")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    py = "\n".join(("          " + ln) if ln else "" for ln in COMPARE.splitlines())
    setup = f"      - name: Setup\n        run: {st}\n" if st else ""
    check = f"""      - name: Compare with the contract
        run: |
          test -f "{sp}" || {{ echo "::error::the tests did not write {sp}"; exit 1; }}
          test -f "{cp}" || {{ echo "::error::no contract at {cp} - commit one from main first"; exit 1; }}
          python3 - "{sp}" "{cp}" <<'PY'
{py}
          PY
""" if sp else ""
    yaml = f"""name: Data checks
# Made by Hoola's Data Engineer desk. Runs the data tests on every pull request{' and fails when a column is removed or its type changes against ' + cp if cp else ''}.
on:
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  data:
    runs-on: {runner}
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "{python}"
          cache: pip
{setup}      - name: Data tests
        run: {tc}
{check}"""
    return {"file": ".github/workflows/data-checks.yml", "yaml": yaml, "compare": py if sp else "",
            "note": ("Put it at .github/workflows/data-checks.yml. Connection details for a warehouse go in the repository's GitHub secrets "
                     "and are read by your own command - never in this file. " + (f"Commit the contract (the schema from main) at {cp} and update it in the same pull "
                     "request when a change is meant to alter the table. " if cp else "Add a schema file and a contract in Settings to fail pull requests that break a table's shape. ")
                     + "Run the tests on a small fixed sample, so a pull request is checked in minutes.")}
