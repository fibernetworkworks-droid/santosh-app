"""A GitHub Actions workflow that guards a machine-learning model: on every pull request it runs her evaluation command (which writes a metrics
JSON such as {"auc": 0.912, "f1": 0.81, "rmse": 4.2, "latency_ms": 18.4}), compares each number with the baseline file kept in her repository,
and fails when a score drops more than she allows or a time rises more than she allows - the comparison written to the run's
summary. The file is text she adds herself; nothing is pushed."""
from __future__ import annotations

import re
from typing import Any


class CiError(ValueError):
    pass


def _cmd(v: str, what: str, need: bool) -> str:
    v = str(v or "").strip()
    if not v:
        if need:
            raise CiError(f"{what}: the command that evaluates the model and writes the metrics file (e.g. python eval.py --out eval/metrics.json).")
        return ""
    if "\n" in v or "\r" in v or len(v) > 400:
        raise CiError(f"{what}: one line, up to 400 characters.")
    if "${{" in v:
        raise CiError(f"{what}: no ${{{{ }}}} expressions - they would run inside the workflow.")
    return v


def _path(v: str, what: str) -> str:
    v = str(v or "").strip()
    if not re.fullmatch(r"[\w./\-]{1,160}", v) or ".." in v or v.startswith("/"):
        raise CiError(f"{what}: a path inside the repository, such as eval/metrics.json.")
    return v


COMPARE = r'''import json, os, sys
DROP, RISE = @DROP@, @RISE@
LOWER = ("latency", "time", "_ms", "loss", "error", "fpr", "fnr", "ece", "mae", "rmse", "mse", "mape", "wape", "logloss", "brier", "perplexity", "wer", "cer")
head, base = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
def flat(d, p=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, p + k + "."))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[p + k] = float(v)
    return out
h, b = flat(head), flat(base)
rows, fail = [], []
for k in sorted(set(h) | set(b)):
    if k not in h:
        fail.append(f"{k} is in the baseline but the run did not report it")
        rows.append(f"| {k} | {b[k]:.4g} | missing | |")
        continue
    if k not in b:
        rows.append(f"| {k} | new | {h[k]:.4g} | |")
        continue
    lower = any(x in k.lower() for x in LOWER)
    d = h[k] - b[k]
    if lower:
        bad = b[k] > 0 and d / b[k] * 100 > RISE
        lim = f"rise over {RISE:g}%"
    else:
        scale = 100 if max(abs(h[k]), abs(b[k])) <= 1 else 1
        bad = -d * scale > DROP
        lim = f"drop over {DROP:g} points"
    if bad:
        fail.append(f"{k}: {b[k]:.4g} -> {h[k]:.4g} ({lim})")
    rows.append(f"| {k} | {b[k]:.4g} | {h[k]:.4g} | {'FAIL' if bad else ('better' if (d < 0 if lower else d > 0) else ('same' if d == 0 else 'within limit'))} |")
with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as s:
    s.write("## Model check\n\n| metric | baseline | this pull request | |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
print("\n".join(rows))
for f in fail:
    print("::error::" + f)
sys.exit(1 if fail else 0)
'''


def workflow(eval_cmd: str = "", metrics: str = "eval/metrics.json", baseline: str = "eval/baseline.json", max_drop: Any = 1.0, max_rise: Any = 10.0,
             setup_cmd: str = "", python: str = "3.12", runner: str = "ubuntu-24.04", lfs: bool = False) -> dict[str, Any]:
    ev = _cmd(eval_cmd, "Evaluation command", True)
    st = _cmd(setup_cmd, "Setup command", False)
    mp, bp = _path(metrics, "Metrics file"), _path(baseline, "Baseline file")
    if mp == bp:
        raise CiError("The metrics file and the baseline must be different files.")
    try:
        dr, ri = float(max_drop), float(max_rise)
    except (TypeError, ValueError):
        raise CiError("Allowed drop and rise: numbers.")
    if not 0 <= dr <= 100 or not 0 <= ri <= 1000:
        raise CiError("Allowed drop: 0 to 100 points; allowed rise: 0 to 1000%.")
    if not re.fullmatch(r"3\.\d{1,2}", str(python)):
        raise CiError("Python: a version such as 3.12.")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04 (a GPU runner's label if the evaluation needs one).")
    py = COMPARE.replace("@DROP@", repr(dr)).replace("@RISE@", repr(ri))
    py = "\n".join(("          " + ln) if ln else "" for ln in py.splitlines())
    setup = f"      - name: Setup\n        run: {st}\n" if st else ""
    yaml = f"""name: Model check
# Made by Hoola's ML desk. Runs the evaluation on every pull request and fails when a score drops more than
# {dr:g} points or a time rises more than {ri:g}% against {bp}.
on:
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  evaluate:
    runs-on: {runner}
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: {'true' if lfs else 'false'}
      - uses: actions/setup-python@v5
        with:
          python-version: "{python}"
          cache: pip
{setup}      - name: Evaluate
        run: {ev}
      - name: Compare with the baseline
        run: |
          test -f "{mp}" || {{ echo "::error::the evaluation did not write {mp}"; exit 1; }}
          test -f "{bp}" || {{ echo "::error::no baseline at {bp} - commit one from main first"; exit 1; }}
          python3 - "{mp}" "{bp}" <<'PY'
{py}
          PY
      - name: Keep the metrics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: metrics
          path: {mp}
          retention-days: 30
"""
    return {"file": ".github/workflows/model-check.yml", "yaml": yaml, "compare": py,
            "note": ("Put it at .github/workflows/model-check.yml. Commit the baseline (the metrics from main) at " + bp + " and update it in the "
                     "same pull request when a change is meant to move the numbers. Scores between 0 and 1 are compared in points (0.412 -> 41.2); "
                     "names with latency, time, loss, error, MAE, RMSE or perplexity count lower as better. Evaluate on a fixed, versioned test set - the check means "
                     "nothing if the images change between runs. Times measured on a shared CI runner are noisy; set a generous rise.")}
