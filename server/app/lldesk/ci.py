"""A GitHub Actions workflow that guards latency on every pull request: it builds and runs her benchmark on the pull request's base
and on its head, on the same runner and interleaved (base, head, base, head ...), so the machine's noise falls on both sides, and fails
when the head's chosen percentile is more than her tolerance slower. Her benchmark writes one latency per line to a file. The file
is text she adds to her repository herself; nothing is pushed."""
from __future__ import annotations

import re
from typing import Any


class CiError(ValueError):
    pass


_UNIT = {"ns": 0.001, "us": 1, "ms": 1000, "s": 1000000}


def _cmd(v: str, what: str, need: bool) -> str:
    v = str(v or "").strip()
    if not v:
        if need:
            raise CiError(f"{what}: the command that runs your benchmark (it writes one latency per line).")
        return ""
    if "\n" in v or "\r" in v or len(v) > 400:
        raise CiError(f"{what}: one line, up to 400 characters.")
    if "${{" in v:
        raise CiError(f"{what}: no ${{{{ }}}} expressions - they would run inside the workflow.")
    return v


COMPARE = r'''import glob, math, os, sys
Q, TOL, MULT = @Q@, @TOL@, @MULT@
def read(p):
    v = []
    for ln in open(p):
        ln = ln.strip().split()
        if ln:
            try:
                v.append(float(ln[0]) * MULT)
            except ValueError:
                pass
    return sorted(v)
def q(v, p):
    return v[max(0, min(len(v) - 1, math.ceil(p / 100 * len(v)) - 1))]
rows = {"base": [], "head": []}
for f in sorted(glob.glob("results/*.txt")):
    side = os.path.basename(f).split("-")[0]
    v = read(f)
    if len(v) < 100:
        print(f"::warning::{f} has only {len(v)} samples")
    if v:
        rows[side].append((q(v, 50), q(v, Q), len(v)))
if not rows["base"] or not rows["head"]:
    print("::error::no samples on one side")
    sys.exit(1)
med = lambda xs: sorted(xs)[len(xs) // 2]
b, h = med([r[1] for r in rows["base"]]), med([r[1] for r in rows["head"]])
change = (h / b - 1) * 100 if b else 0.0
lines = ["| side | run | p50 (us) | p@QS@ (us) | samples |", "|---|---|---|---|---|"]
for side in ("base", "head"):
    for i, (a, c, n) in enumerate(rows[side], 1):
        lines.append(f"| {side} | {i} | {a:.1f} | {c:.1f} | {n} |")
verdict = f"p@QS@: base {b:.1f} us, head {h:.1f} us ({change:+.1f}%) - tolerance {TOL:g}%"
with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as s:
    s.write("## Latency check\n\n" + verdict + "\n\n" + "\n".join(lines) + "\n")
print(verdict)
if change > TOL:
    print(f"::error::p@QS@ is {change:.1f}% slower than the base (tolerance {TOL:g}%)")
    sys.exit(1)
'''


def workflow(bench_cmd: str = "", build_cmd: str = "", out_file: str = "bench.txt", unit: str = "us", quantile: float = 99.0,
             tolerance: float = 10.0, runs: int = 3, runner: str = "ubuntu-24.04", pin_cpu: bool = True) -> dict[str, Any]:
    bench = _cmd(bench_cmd, "Benchmark", True)
    build = _cmd(build_cmd, "Build", False)
    out_file = str(out_file or "bench.txt").strip()
    if not re.fullmatch(r"[\w./\-]{1,120}", out_file) or ".." in out_file or out_file.startswith("/"):
        raise CiError("Results file: a path inside the repository - letters, numbers and . / - _ only.")
    if unit not in _UNIT:
        raise CiError("Unit: ns, us, ms or s.")
    try:
        quantile, tolerance, runs = float(quantile), float(tolerance), int(runs)
    except (TypeError, ValueError):
        raise CiError("Percentile, tolerance and runs must be numbers.")
    if not 50 <= quantile < 100:
        raise CiError("Percentile to guard: 50 to 99.99.")
    if not 1 <= tolerance <= 200:
        raise CiError("Tolerance: 1 to 200 %.")
    if not 1 <= runs <= 9:
        raise CiError("Runs on each side: 1 to 9.")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    pin = "taskset -c 1 " if pin_cpu else ""
    qs = f"{quantile:g}"
    py = COMPARE.replace("@Q@", repr(quantile)).replace("@TOL@", repr(tolerance)).replace("@MULT@", repr(_UNIT[unit])).replace("@QS@", qs)
    py = "\n".join(("          " + ln) if ln else "" for ln in py.splitlines())
    if build:
        build_lines = f"          (cd base && {build})\n          (cd head && {build})"
    else:
        build_lines = '          echo "No build step."'
    yaml = f"""name: Latency check
# Made by Hoola's Low Latency desk. Runs your benchmark on the pull request's base and head on the same runner, interleaved,
# and fails when p{qs} of the head is more than {tolerance:g}% slower than the base.
on:
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: latency-${{{{ github.ref }}}}
  cancel-in-progress: true
jobs:
  latency:
    runs-on: {runner}
    timeout-minutes: 60
    steps:
      - name: Head
        uses: actions/checkout@v4
        with:
          path: head
      - name: Base
        uses: actions/checkout@v4
        with:
          path: base
          ref: ${{{{ github.event.pull_request.base.sha || github.sha }}}}
      - name: Build both
        run: |
          set -euo pipefail
{build_lines}
      - name: Run both, interleaved
        run: |
          set -euo pipefail
          mkdir -p results
          for i in $(seq 1 {runs}); do
            for side in base head; do
              : > "./$side/{out_file}"
              (cd "./$side" && {pin}{bench})
              test -s "./$side/{out_file}" || {{ echo "::error::the benchmark did not write $side/{out_file}"; exit 1; }}
              cp "./$side/{out_file}" "results/$side-$i.txt"
            done
          done
      - name: Compare
        run: |
          python3 - <<'PY'
{py}
          PY
      - name: Keep the samples
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: latency-samples
          path: results/
          retention-days: 14
"""
    return {"file": ".github/workflows/latency.yml", "yaml": yaml, "compare": py,
            "note": ("Put it at .github/workflows/latency.yml. Your benchmark must write one latency per line (in " + unit + ") to " + out_file +
                     " - the file is emptied before each run, so write it fresh or append to it. Shared GitHub runners are noisy: running base and "
                     "head on the same machine, interleaved, cancels most of it, but keep the tolerance above the noise you see between two runs of "
                     "the same code (try it on a pull request that changes nothing). For small differences use a self-hosted runner with isolated cores.")}
