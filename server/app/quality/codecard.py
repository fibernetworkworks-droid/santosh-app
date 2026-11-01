"""v0.360 CODE CARD - how well does Developer Sahayak really code? (owner: "GO 6")

`python -m app.quality code [--only id,id] [--limit N] [--label x]`; vps-ops job `code_card`.
Each fixed practice job (code_tasks.TASKS) goes through the SAME 8-tool loop her real tasks use (devsahayak/loop.run, same
model, same rules), against an in-memory copy of the tiny repo - no GitHub, no branch, no PR. Then it is marked:
  works    the hidden check passes on the changed repo
  scope    only the files the job needed were changed
  rules    the project's rules hold in the changed files (no print(), no f-string SQL, folder docstrings ...)
  test     a fix / feature came with a test that passes - and for a fix, that FAILS on the old code (it proves the bug);
           a tests job's tests pass AND catch a broken version (mutant)
A job is RIGHT only when every mark it needs is green. Costs model calls (~12 Opus jobs, roughly Rs 150-400).

Running the code: the checks and Hoola's own tests run in a child Python in a temp folder with NO secrets in its
environment (PATH + the folder only), CPU / memory / file-size limits and a timeout; code that reaches for the network,
processes or eval is not run at all (marked unsafe). Only our fixed jobs' answers are ever run - never a user's repo."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any

from . import code_tasks as C

UNSAFE = re.compile(r"\bimport\s+(socket|subprocess|requests|httpx|urllib|ctypes|multiprocessing|shutil)\b|"
                    r"\bfrom\s+(socket|subprocess|requests|httpx|urllib|ctypes|multiprocessing|shutil)\b|"
                    r"\bos\.(system|popen|exec|spawn|remove|unlink|rmdir|fork|kill)|\b__import__\(|\beval\(|\bexec\(|"
                    r"\bopen\([^)]*['\"][wax]")
STEPS, MINUTES, PARALLEL = 30, 6.0, 4


class MemGh:
    """The few GitHub reads loop.run makes, served from the task's files."""

    def __init__(self, files: dict[str, str]):
        self.files = files

    def branch_sha(self, repo, base):
        return "base0000"

    def tree(self, repo, sha):
        return [{"path": p} for p in sorted(self.files)]

    def file(self, repo, path, sha):
        return (self.files[path], f"sha-{path}") if path in self.files else ("", "")

    def search_code(self, repo, words):
        low = [w.lower() for w in words if w]
        return [p for p, t in sorted(self.files.items()) if low and all(w in t.lower() for w in low)]


# ---------------------------------------------------------------- running code safely
def _limits():  # pragma: no cover - runs in the child
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))


def _write(root: str, files: dict[str, str]) -> None:
    for p, text in files.items():
        full = os.path.join(root, p)
        if not os.path.realpath(full).startswith(os.path.realpath(root) + os.sep):
            continue                                   # never outside the temp folder
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)


def _py(files: dict[str, str], args: list[str], timeout: int = 60) -> tuple[int, str]:
    """Run python in a fresh temp copy of `files`; no secrets in the child's environment."""
    root = tempfile.mkdtemp(prefix="hoola-codecard-")
    try:
        _write(root, files)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": root, "PYTHONPATH": root,
               "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"}
        try:
            r = subprocess.run([sys.executable, *args], cwd=root, env=env, capture_output=True, text=True,
                               timeout=timeout, preexec_fn=_limits if os.name == "posix" else None)
            return r.returncode, (r.stdout + r.stderr)[-1500:]
        except subprocess.TimeoutExpired:
            return 124, "timed out"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _pytest(files: dict[str, str], tests: list[str]) -> tuple[int, str]:
    return _py(files, ["-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", *tests])


# ---------------------------------------------------------------- marking
def score(task: dict, changed: dict[str, str], out: dict[str, Any] | None = None) -> dict[str, Any]:
    """Mark one job from what it changed ({path: final text}) and its done answer. Pure + reusable by the tests."""
    out = out or {}
    start = C.repo(task)
    final = {**start, **changed}
    row: dict[str, Any] = {"id": task["id"], "kind": task["kind"], "changed": sorted(changed), "why": []}
    real = {p: t for p, t in changed.items() if start.get(p) != t}
    row["scope"] = all(re.match(task["allow"], p) for p in real)
    if not row["scope"]:
        row["why"].append("changed " + ", ".join(p for p in real if not re.match(task["allow"], p)))
    bad = []
    for path_re, rx in task.get("forbid", []):
        bad += [f"{p}: {rx[:30]}" for p, t in real.items() if re.match(path_re, p) and re.search(rx, t)]
    for path_re, rx in task.get("want", []):
        hits = [p for p in final if re.match(path_re, p)]
        if not any(re.search(rx, final[p]) for p in hits):
            bad.append(f"missing {rx[:30]}")
    row["rules"] = not bad
    if bad:
        row["why"].append("rule: " + "; ".join(bad))
    if task["kind"] == "explain":
        said = f"{out.get('explain', '')} {out.get('cause', '')}"
        row["works"] = not real and bool(re.search(task["explain_re"], said, re.I))
        if not row["works"]:
            row["why"].append("changed files" if real else "explanation misses the cause")
        row["test"] = None
        row["right"] = row["works"] and row["scope"]
        return row
    unsafe = [p for p, t in real.items() if p.endswith(".py") and UNSAFE.search(t)]
    if unsafe:
        row.update(works=False, test=False if (task.get("must_test") or task.get("mutant")) else None, right=False,
                   unsafe=unsafe)
        row["why"].append("unsafe code not run: " + ", ".join(unsafe))
        return row
    if not real and task["kind"] != "explain":
        row["why"].append("nothing changed")
    if task.get("check"):
        rc, log = _py({**final, "_hoola_check.py": task["check"]}, ["_hoola_check.py"])
        row["works"] = rc == 0
        if rc:
            row["why"].append("check failed: " + (log.strip().splitlines() or ["?"])[-1][:160])
    else:
        row["works"] = bool(real)
    tests = [p for p, t in real.items() if re.match(r"^tests/.+\.py$", p) and "def test_" in t]
    row["test"] = None
    if task.get("must_test") or task.get("mutant"):
        if not tests:
            row["test"] = False
            row["why"].append("no test written")
        else:
            rc, log = _pytest(final, tests)
            ok = rc == 0
            if not ok:
                row["why"].append("its own test fails: " + (log.strip().splitlines() or ["?"])[-1][:160])
            n = sum(final[p].count("def test_") for p in tests)
            if ok and task.get("min_tests") and n < task["min_tests"]:
                ok = False
                row["why"].append(f"only {n} tests (want {task['min_tests']})")
            if ok and task["kind"] == "fix":            # the test must PROVE the bug: red on the old code
                rc_old, _ = _pytest({**start, **{p: final[p] for p in tests}}, tests)
                row["proves"] = rc_old != 0
                if not row["proves"]:
                    ok = False
                    row["why"].append("its test also passes on the old (broken) code")
            if ok and task.get("mutant"):              # a tests job: they must catch a broken version
                rc_m, _ = _pytest({**final, **task["mutant"]}, tests)
                if rc_m == 0:
                    ok = False
                    row["why"].append("tests do not catch the broken version")
            row["test"] = ok
    row["right"] = bool(row["works"] and row["scope"] and row["rules"] and row["test"] is not False)
    return row


# ---------------------------------------------------------------- one job through the real loop
def run_task(task: dict) -> dict[str, Any]:
    from ..devsahayak import loop as L
    t0 = time.time()
    t = SimpleNamespace(repo="hoola/codecard", base="main", kind=task["kind"], text=task["request"], issue=0)
    try:
        _, _, ctx, out = L.run(MemGh(C.repo(task)), t, "", [], False, "", max_steps=STEPS, minutes=MINUTES)
    except Exception as e:  # noqa: BLE001 - one broken job never stops the card
        return {"id": task["id"], "kind": task["kind"], "right": False, "works": False, "scope": True, "rules": True,
                "test": None, "why": [f"loop error: {str(e)[:160]}"], "seconds": round(time.time() - t0), "steps": 0}
    changed = {f["path"]: f["content"] for f in out.get("files") or []}
    row = score(task, changed, out)
    loop = (ctx.get("found") or {}).get("loop") or {}
    row.update(seconds=round(time.time() - t0), steps=loop.get("steps", 0), finished=loop.get("finished", False),
               rules_read=(ctx.get("found") or {}).get("rules", []))
    return row


def card(only: list[str] | None = None, limit: int = 0, parallel: int = PARALLEL) -> dict[str, Any]:
    tasks = [x for x in C.TASKS if not only or x["id"] in only]
    if limit:
        tasks = tasks[:limit]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max(1, parallel)) as ex:
        rows = list(ex.map(run_task, tasks))
    from ..config import get_settings
    st = get_settings()
    model = getattr(st, "dev_loop_model", "") or getattr(st, "site_model", "") or getattr(st, "anthropic_model", "")
    need_test = [r for r in rows if r.get("test") is not None]
    fixes = [r for r in rows if "proves" in r]
    return {"kind": "code", "set": C.SET, "model": model, "jobs": len(rows),
            "right": sum(1 for r in rows if r.get("right")), "works": sum(1 for r in rows if r.get("works")),
            "scope": sum(1 for r in rows if r.get("scope")), "rules": sum(1 for r in rows if r.get("rules")),
            "tests": sum(1 for r in need_test if r.get("test")), "tests_of": len(need_test),
            "proves": sum(1 for r in fixes if r.get("proves")), "proves_of": len(fixes),
            "steps_avg": round(sum(r.get("steps", 0) for r in rows) / max(1, len(rows)), 1),
            "minutes": round((time.time() - t0) / 60, 1), "rows": rows}


def save(cd: dict, label: str = "") -> dict:
    from .toolchoice import _dir
    cd = {**cd, "label": label, "at": int(time.time())}
    name = f"code-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(cd, ensure_ascii=False, indent=1))
    cd["file"] = name
    return cd


def lines(cd: dict) -> list[str]:
    n = cd["jobs"] or 1
    out = [f"Coding card (set v{cd['set']}, {cd.get('model') or 'model'}): {cd['right']}/{cd['jobs']} jobs fully right "
           f"({round(100 * cd['right'] / n)}%).",
           f"  works {cd['works']}/{cd['jobs']} · stayed in scope {cd['scope']}/{cd['jobs']} · project rules "
           f"{cd['rules']}/{cd['jobs']} · good tests {cd['tests']}/{cd['tests_of']} (fix tests that prove the bug "
           f"{cd['proves']}/{cd['proves_of']}) · {cd['steps_avg']} steps a job · {cd['minutes']} min"]
    for r in cd["rows"]:
        mark = "OK  " if r.get("right") else "MISS"
        tail = "" if r.get("right") else " - " + "; ".join(r.get("why") or ["?"])
        out.append(f"  {mark} {r['id']} ({r['kind']}, {r.get('steps', 0)} steps, {r.get('seconds', 0)}s){tail}")
    return out
