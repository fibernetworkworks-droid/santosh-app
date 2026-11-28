"""A GitHub Actions alert-rules check: on every pull request that changes her Prometheus rules files it reads each alerting rule and
fails the check when a rule cannot work at 3 am - no severity label, a counter compared without rate(), two alerts with one name - and
(at her level) when it will be noisy or hard to act on: no `for`, no summary, no runbook link. With a promtool version named in
Settings it also runs promtool's own syntax check from the official Prometheus release. It needs no keys and changes nothing."""
from __future__ import annotations

import re
from typing import Any


class CiError(ValueError):
    pass


CHECK = r'''import glob, os, re, sys
FAIL = @FAIL@
PATTERN = @PATTERN@
NEED_RUNBOOK = @RUNBOOK@
files = sorted(f for f in glob.glob(PATTERN, recursive=True) if f.endswith((".yml", ".yaml"))) if len(sys.argv) < 2 else sys.argv[1:]
hits, seen, alerts = [], {}, 0
for f in files:
    lines = open(f, encoding="utf-8").read().split("\n")
    blocks, cur = [], None
    for n, ln in enumerate(lines, 1):
        m = re.match(r"^(\s*)-\s*(alert|record)\s*:\s*['\"]?([\w:.-]+)", ln)
        if m:
            cur = {"kind": m.group(2), "name": m.group(3), "line": n, "ind": len(m.group(1)), "body": []}
            blocks.append(cur)
            continue
        if cur is not None:
            if ln.strip() and (len(ln) - len(ln.lstrip())) <= cur["ind"] and not ln.lstrip().startswith("#"):
                cur = None
                continue
            cur["body"].append(ln)
    for b in blocks:
        if b["kind"] != "alert":
            continue
        alerts += 1
        body = "\n".join(b["body"])
        expr = re.search(r"(?m)^\s*expr\s*:\s*(.*)$", body)
        e = expr.group(1).strip() if expr else ""
        if e in ("|", ">", "|-", ">-"):
            e = " ".join(x.strip() for x in body.split("expr", 1)[1].split("\n")[1:6])
        def hit(sev, rid, what):
            hits.append((sev, rid, f"{b['name']}: {what}", f, b["line"]))
        if not e:
            hit("bad", "no-expr", "no expr")
        if not re.search(r"(?m)^\s*severity\s*:", body):
            hit("bad", "no-severity", "no severity label - nobody knows whether to wake up")
        if e and re.search(r"\b\w+_total\b(?!\s*\[)", e) and not re.search(r"\b(rate|irate|increase|delta|resets|changes)\s*\(", e):
            hit("bad", "raw-counter", "a counter (_total) compared without rate() or increase()")
        if not re.search(r"(?m)^\s*for\s*:", body):
            hit("warn", "no-for", "no `for` - one bad scrape pages someone")
        if not re.search(r"(?m)^\s*(summary|description)\s*:", body):
            hit("warn", "no-summary", "no summary or description annotation")
        if NEED_RUNBOOK and not re.search(r"(?m)^\s*(runbook_url|runbook)\s*:", body):
            hit("warn", "no-runbook", "no runbook_url annotation")
        sv = re.search(r"(?m)^\s*severity\s*:\s*['\"]?([\w-]+)", body)
        key = (b["name"], sv.group(1).lower() if sv else "")
        if key in seen:
            hit("bad", "duplicate", f"the same alert name and severity are also at {seen[key]}")
        else:
            seen[key] = f"{f}:{b['line']}"
order = {"bad": 0, "warn": 1}
bad = [h for h in hits if order[h[0]] <= order[FAIL]]
with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as s:
    s.write(f"## Alert rules check\n\n{len(files)} file(s), {alerts} alert(s), {len(hits)} finding(s), {len(bad)} failing.\n\n")
    if hits:
        s.write("| level | rule | finding | file | line |\n|---|---|---|---|---|\n" + "\n".join(f"| {a} | {r} | {w} | {f} | {n} |" for a, r, w, f, n in hits) + "\n")
for sev, rid, what, f, n in bad:
    print(f"::error file={f},line={n}::{what} ({rid})")
for sev, rid, what, f, n in hits:
    if (sev, rid, what, f, n) not in bad:
        print(f"::warning file={f},line={n}::{what} ({rid})")
print(f"{len(files)} file(s), {alerts} alert(s), {len(hits)} finding(s), {len(bad)} failing")
sys.exit(1 if bad else 0)
'''

_GLOB = re.compile(r"[\w./*\-{},]{1,120}")
_VER = re.compile(r"\d+\.\d+\.\d+")


def workflow(rules_glob: str = "**/*rules*.y*ml", fail_level: str = "bad", runbook: bool = True, promtool_version: str = "",
             runner: str = "ubuntu-24.04") -> dict[str, Any]:
    rules_glob = str(rules_glob or "").strip() or "**/*rules*.y*ml"
    if not _GLOB.fullmatch(rules_glob) or ".." in rules_glob:
        raise CiError("Rules files: a path pattern inside the repository, like monitoring/**/*.yml")
    if fail_level not in ("bad", "warn"):
        raise CiError("Fail on: serious only (bad) or anything to fix (warn).")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    pv = str(promtool_version or "").strip().lstrip("v")
    if pv and not _VER.fullmatch(pv):
        raise CiError("promtool version: like 2.53.0 (a Prometheus release), or leave it empty.")
    pattern = rules_glob
    check = (CHECK.replace("@FAIL@", repr(fail_level)).replace("@PATTERN@", repr(pattern)).replace("@RUNBOOK@", repr(bool(runbook))))
    body = "\n".join("          " + ln if ln else "" for ln in check.splitlines())
    prom = ""
    if pv:
        prom = f"""      - name: promtool check rules (Prometheus {pv})
        run: |
          curl -fsSLo prom.tgz https://github.com/prometheus/prometheus/releases/download/v{pv}/prometheus-{pv}.linux-amd64.tar.gz
          tar -xzf prom.tgz --strip-components=1 prometheus-{pv}.linux-amd64/promtool
          shopt -s globstar nullglob
          files=( {rules_glob} )
          if [ ${{#files[@]}} -gt 0 ]; then ./promtool check rules "${{files[@]}}"; else echo "No rules files match {rules_glob}"; fi
"""
    yml = f"""name: Alert rules check
# Added by you from the Site Reliability Engineer desk. It reads the Prometheus rules files in this pull request and fails on
# alerts that cannot work or will wake people for nothing. It needs no keys and changes nothing.
on:
  pull_request:
    paths:
      - "{rules_glob}"
      - ".github/workflows/alert-rules-check.yml"
permissions:
  contents: read
jobs:
  rules:
    runs-on: {runner}
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - name: Check the alert rules
        shell: python3 {{0}}
        run: |
{body}
{prom}"""
    return {"file": ".github/workflows/alert-rules-check.yml", "yaml": yml.rstrip() + "\n", "fail_level": fail_level, "rules_glob": rules_glob,
            "promtool": pv or None, "runner": runner,
            "steps": ["Add the file to .github/workflows in a pull request.",
                      "Make 'Alert rules check' a required check on the default branch.",
                      "Fix what it names - or change the level in Settings."],
            "note": ("It reads only the rules files in the repository; it needs no keys. "
                     + (f"promtool comes from the official Prometheus {pv} release." if pv else
                        "Name a Prometheus version in Settings to add promtool's own syntax check."))}
