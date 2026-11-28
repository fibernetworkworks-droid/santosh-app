"""A GitHub Actions workflow that keeps a translation proved: on every pull request it builds the new code, runs it on the saved
inputs, and compares its output with the old program's output saved in the repository (the golden file) - field by field through the
copybook layout when there is one, line by line otherwise - and fails on any difference. The file is text she adds to her repository
herself; nothing is pushed."""
from __future__ import annotations

import json
import re
from typing import Any


class CiError(ValueError):
    pass


def _cmd(v: str, what: str, need: bool) -> str:
    v = str(v or "").strip()
    if not v:
        if need:
            raise CiError(f"{what}: the command that runs the new program on the saved input and writes its output.")
        return ""
    if "\n" in v or "\r" in v or len(v) > 400:
        raise CiError(f"{what}: one line, up to 400 characters.")
    if "${{" in v:
        raise CiError(f"{what}: no ${{{{ }}}} expressions - they would run inside the workflow.")
    return v


def _path(v: str, what: str) -> str:
    v = str(v or "").strip()
    if not re.fullmatch(r"[\w./\-]{1,160}", v) or ".." in v or v.startswith("/"):
        raise CiError(f"{what}: a path inside the repository - letters, numbers and . / - _ only.")
    return v


COMPARE = r'''import json, os, sys
from decimal import Decimal, InvalidOperation
LAYOUT = json.loads(@LAYOUT@)
KEYS, IGNORE, TOL = @KEYS@, @IGNORE@, Decimal(@TOL@)
POS, NEG = dict(zip("{ABCDEFGHI", "0123456789")), dict(zip("}JKLMNOPQR", "0123456789"))
def num(s, f):
    v, neg = s.strip(), False
    if f.get("signed") and v[-1:] in POS: v = v[:-1] + POS[v[-1]]
    elif f.get("signed") and v[-1:] in NEG: v, neg = v[:-1] + NEG[v[-1]], True
    if v.endswith("-"): v, neg = v[:-1], True
    try: d = Decimal(v.replace(",", ""))
    except InvalidOperation: return None
    if f.get("scale") and v.lstrip("+-").isdigit(): d = d.scaleb(-f["scale"])
    return -d if neg else d
def recs(p):
    lines = [l.rstrip("\n").rstrip("\r") for l in open(p, encoding="latin-1")]
    while lines and not lines[-1].strip(): lines.pop()
    if not LAYOUT: return [{"line": l} for l in lines]
    return [{f["name"]: l[f["offset"]:f["offset"] + f["length"]] for f in LAYOUT} for l in lines]
old, new = recs(sys.argv[1]), recs(sys.argv[2])
meta = {f["name"]: f for f in LAYOUT}
fields = [f["name"] for f in LAYOUT] or ["line"]
cmp = [h for h in fields if h not in IGNORE and h not in KEYS]
def key(r, i): return tuple(r[k].strip() for k in KEYS) if KEYS else i
A = {key(r, i): r for i, r in enumerate(old)}
B = {key(r, i): r for i, r in enumerate(new)}
diffs = []
for k in A:
    if k not in B: diffs.append((k, "(record)", "present", "missing")); continue
    for h in cmp:
        x, y = A[k][h], B[k][h]
        if x == y: continue
        f = meta.get(h, {})
        if f.get("kind") in ("zoned", "packed", "binary", "edited"):
            a, b = num(x, f), num(y, f)
            if a is not None and b is not None and abs(a - b) <= TOL: continue
        diffs.append((k, h, x, y))
for k in B:
    if k not in A: diffs.append((k, "(record)", "missing", "present"))
summary = f"{len(old)} old record(s), {len(new)} new; {len(diffs)} difference(s)"
with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as s:
    s.write("## Output check\n\n" + summary + "\n\n")
    if diffs:
        s.write("| record | field | old | new |\n|---|---|---|---|\n")
        for k, h, x, y in diffs[:50]:
            s.write(f"| {k} | {h} | `{x}` | `{y}` |\n")
print(summary)
for k, h, x, y in diffs[:20]:
    print(f"::error::record {k} field {h}: old {x!r} new {y!r}")
sys.exit(1 if diffs else 0)
'''


def workflow(run_cmd: str = "", build_cmd: str = "", golden: str = "tests/golden/output.txt", out_file: str = "output.txt",
             layout: list[dict[str, Any]] | None = None, keys: str = "", ignore: str = "", tolerance: Any = 0, runner: str = "ubuntu-24.04",
             setup: str = "") -> dict[str, Any]:
    run = _cmd(run_cmd, "Run", True)
    build = _cmd(build_cmd, "Build", False)
    golden = _path(golden, "Saved old output")
    out_file = _path(out_file, "New output file")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    try:
        tol = float(tolerance or 0)
    except (TypeError, ValueError):
        raise CiError("Tolerance: a number.")
    if tol < 0:
        raise CiError("Tolerance cannot be below 0.")
    lay = [{k: f.get(k) for k in ("name", "offset", "length", "kind", "scale", "signed")} for f in (layout or []) if not f.get("group") and f.get("length") and not f.get("redefines")]
    names = {f["name"] for f in lay}
    kk = [k.strip().upper() for k in re.split(r"[,\s]+", keys or "") if k.strip()]
    ig = [k.strip().upper() for k in re.split(r"[,\s]+", ignore or "") if k.strip()]
    if lay:
        for k in kk + ig:
            if k not in names:
                raise CiError(f"{k} is not a field of the copybook.")
    elif kk:
        raise CiError("Key fields need a copybook layout; without one the output is compared line by line.")
    setup_step = {"java": "      - uses: actions/setup-java@v4\n        with:\n          distribution: temurin\n          java-version: '21'\n",
                  "python": "      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'\n",
                  "dotnet": "      - uses: actions/setup-dotnet@v4\n        with:\n          dotnet-version: '8.0.x'\n",
                  "gnucobol": "      - name: GnuCOBOL\n        run: sudo apt-get update && sudo apt-get install -y gnucobol\n"}.get(setup, "")
    py = (COMPARE.replace("@LAYOUT@", repr(json.dumps(lay))).replace("@KEYS@", repr(kk)).replace("@IGNORE@", repr(ig)).replace("@TOL@", repr(str(tol))))
    py = "\n".join(("          " + ln) if ln else "" for ln in py.splitlines())
    yaml = f"""name: Output check
# Made by Hoola's Mainframe Modernization desk. Builds the new code, runs it on the saved input and fails when its output
# differs from the old program's output saved in {golden}.
on:
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  output:
    runs-on: {runner}
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
{setup_step}      - name: Build
        run: {build or 'echo "No build step."'}
      - name: Run on the saved input
        run: |
          set -euo pipefail
          {run}
          test -s "{out_file}" || {{ echo "::error::the run did not write {out_file}"; exit 1; }}
      - name: Compare with the old output
        run: |
          python3 - "{golden}" "{out_file}" <<'PY'
{py}
          PY
      - name: Keep the output
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: new-output
          path: {out_file}
          retention-days: 14
"""
    return {"file": ".github/workflows/output-check.yml", "yaml": yaml, "compare": py, "fields": len(lay),
            "note": (f"Put it at .github/workflows/output-check.yml. Save the old program's output for a fixed input at {golden} (download it from "
                     "the mainframe in text mode - or convert it with the Data layouts page - so both sides are in the same character set), and "
                     f"make the run command write the new program's output to {out_file}. "
                     + (f"It compares the {len(lay)} fields of the copybook" + (f" by key {', '.join(kk)}" if kk else " in record order") + "." if lay else "It compares line by line - pick a copybook in Settings to compare field by field.")
                     + " Add an input with edge cases (zeros, negatives, largest values, blanks, month and year ends) - a check only proves the inputs it runs.")}
