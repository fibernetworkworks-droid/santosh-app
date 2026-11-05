"""v0.456 the lab's one public surface: give it a repo + a ref + a declared command, get back a pass/fail with evidence.

The order of a run, and why each step is where it is:
1. MATERIALIZE - clone her branch OUTSIDE the box with her token, then `rm -rf .git` before anything goes in. The
   token never enters the container and the repo's own code can never push anywhere (Anthropic: "avoid mounting host
   secrets"; "treat every command as untrusted input").
2. SNAPSHOT - the dependency install runs ONCE per lock-file hash, with the network ON, and the result is committed as
   an image (Codex's cached `universal` container; Jules's "Run and Snapshot"; Devin's blueprint snapshot). Her repo's
   install scripts run here, so this step is the one with teeth - it is time-capped, non-root and has no secrets.
3. CHECK - her declared command, on the snapshot, with NO network at all. Failure-first output + a log she can grep.
Third-party repos are allowed (her decision, 2 Nov 2026) and get exactly the same walls; nothing in the box is hers."""
from __future__ import annotations

import logging
import os
import re
import shutil
import sys
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from . import box, out, spec

log = logging.getLogger("santosh.devlab")

MAX_CHECKOUT_MB = 600
KEEP_LOGS = 60
LOG_DIR = Path(os.environ.get("HOOLA_DATA", "data")) / "devlab"


def _slug(repo: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (repo or "repo").lower()).strip("-")[:40] or "repo"


def image_for(repo: str, key: str) -> str:
    """v0.542: the BASE revision rides in the tag. A snapshot is built ON the base image, so a base that changes
    (a new Python, a new tool) must not be served stale dependencies built against the old one - which is exactly
    what would have happened after the 3.11 -> 3.13 move: a cached snapshot, a fresh base, and the same failure."""
    return f"hoola-devlab:{_slug(repo)}-r{box.BASE_REV}-{key}"


def _git(argv: list[str], cwd: str, token: str, timeout: int) -> tuple[int, str]:
    """git, with the token handed over through an askpass file that is deleted straight after - never in argv, never in
    the clone's config, never inside the box."""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": cwd, "LANG": "C.UTF-8",
           "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
           "GIT_LFS_SKIP_SMUDGE": "1"}
    ask = ""
    try:
        if token:
            fd, ask = tempfile.mkstemp(prefix="hoola-ask-", suffix=".sh", dir=cwd)
            with os.fdopen(fd, "w") as f:
                f.write('#!/bin/sh\ncase "$1" in Username*) echo x-access-token ;; *) printf %s "$HOOLA_T" ;; esac\n')
            os.chmod(ask, 0o700)
            env["GIT_ASKPASS"] = ask
            env["HOOLA_T"] = token
        r = subprocess.run(["git", *argv], cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).replace(token or "\0x\0", "***")[-4000:]
    except subprocess.TimeoutExpired:
        return 124, f"git {argv[0]} timed out after {timeout}s"
    except OSError as e:
        return 127, f"git: {e}"
    finally:
        if ask:
            try:
                os.remove(ask)
            except OSError:
                pass


def _du_mb(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
        if total > MAX_CHECKOUT_MB * 1024 * 1024:
            break
    return total // (1024 * 1024)


def materialize(repo: str, ref: str = "", token: str = "", host: str = "github.com") -> dict[str, Any]:
    """Her branch (or any repo's, by her decision) as plain files in a throwaway folder, with no .git and no token."""
    work = tempfile.mkdtemp(prefix="hoola-lab-")
    url = f"https://{host}/{repo}.git"
    sha = bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
    if sha:
        rc, txt = _git(["init", "-q", "."], work, "", 60)
        if rc == 0:
            rc, txt = _git(["remote", "add", "origin", url], work, "", 60)
        if rc == 0:
            rc, txt = _git(["fetch", "--depth", "1", "-q", "origin", ref], work, token, 600)
        if rc == 0:
            rc, txt = _git(["checkout", "-q", "FETCH_HEAD"], work, "", 120)
    else:
        argv = ["clone", "--depth", "1", "--single-branch", "-q"] + (["--branch", ref] if ref else []) + [url, "."]
        rc, txt = _git(argv, work, token, 900)
    if rc != 0:
        shutil.rmtree(work, ignore_errors=True)
        return {"ok": False, "why": f"repo laaya nahi ja saka: {txt.strip()[-400:]}"}
    shutil.rmtree(os.path.join(work, ".git"), ignore_errors=True)       # no history, no remote, no credentials inside
    mb = _du_mb(work)
    if mb > MAX_CHECKOUT_MB:
        shutil.rmtree(work, ignore_errors=True)
        return {"ok": False, "why": f"repo bahut bada hai ({mb} MB, seema {MAX_CHECKOUT_MB} MB)"}
    paths = []
    for root, dirs, files in os.walk(work):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".venv", "venv", "__pycache__", ".git")]
        for f in files:
            p = os.path.relpath(os.path.join(root, f), work)
            paths.append(p)
            if len(paths) > 20000:
                break
    os.chmod(work, 0o777)                                               # the box runs as uid 1000, not as us
    return {"ok": True, "dir": work, "paths": sorted(paths), "mb": mb}


def read_some(work: str, names: list[str]) -> dict[str, str]:
    """The few files the command discovery needs (rules, CI, .hoola/lab.json, lock files) - nothing else is read."""
    got: dict[str, str] = {}
    for n in names:
        p = Path(work) / n
        try:
            if p.is_file() and p.stat().st_size <= 256 * 1024:
                got[n] = p.read_text("utf-8", errors="replace")
        except OSError:
            continue
    return got


def spec_for(work: str, paths: list[str], hers: dict[str, str] | None = None) -> dict[str, Any]:
    wf = [p for p in paths if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml"))][:4]
    files = read_some(work, ["AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "README.md", ".hoola/lab.json",
                             *spec.LOCKS, *wf])
    sp = spec.discover(paths, files, hers)
    sp["deps_key"] = spec.deps_key(files)
    return sp


def snapshot(repo: str, work: str, setup_cmd: str, deps_key: str, timeout: int = box.SETUP_TIMEOUT) -> dict[str, Any]:
    """The per-repo dependency image, built once per lock-file hash. Reused for every later check on this repo."""
    tag = image_for(repo, deps_key)
    if box.has_image(tag):
        return {"ok": True, "image": tag, "cached": True, "seconds": 0.0}
    if not box.has_image(box.BASE_IMAGE):
        b = box.build_base()
        if not b["ok"]:
            return {"ok": False, "why": b["why"], "out": b.get("out", "")[-2000:]}
    cmd = setup_cmd.strip() or "true"
    r = box.run_in(box.BASE_IMAGE, work, f"set -o pipefail; cd {box.WORK}; {cmd}", timeout=timeout, network=True,
                   commit_to=tag)
    if r["rc"] != 0 or not box.has_image(tag):
        return {"ok": False, "why": "setup command poori nahi hui", "image": "", "cached": False,
                "seconds": round(r["secs"], 1), "out": r["out"][-6000:]}
    return {"ok": True, "image": tag, "cached": False, "seconds": round(r["secs"], 1), "out": r["out"][-2000:]}


def _log_folder() -> str:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    runs = sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    for old in runs[:-KEEP_LOGS]:
        try:
            old.unlink()
        except OSError:
            pass
    return str(LOG_DIR)


def check(repo: str, ref: str = "", token: str = "", cmd: str = "", hers: dict[str, str] | None = None,
          timeout: int = 0, setup: str = "", keep: bool = False) -> dict[str, Any]:
    """Run her declared check on this repo at this ref. Everything about the run is in the answer, including WHY not."""
    t0 = time.time()
    av = box.available()
    if not av["ok"]:
        return {"ok": False, "stage": "box", "why": av["why"]}
    m = materialize(repo, ref, token)
    if not m["ok"]:
        return {"ok": False, "stage": "clone", "why": m["why"]}
    work, paths = m["dir"], m["paths"]
    try:
        sp = spec_for(work, paths, hers)
        run_cmd = spec._clean(cmd) or sp["test"]
        if not run_cmd:
            return {"ok": False, "stage": "command", "why": sp["why"], "spec": sp}
        bad = spec.refuse_reason(run_cmd)
        if bad:
            return {"ok": False, "stage": "command", "why": bad, "spec": sp}
        if not cmd and sp.get("confirm") and not (hers or {}).get("ok"):
            return {"ok": False, "stage": "confirm", "spec": sp,
                    "why": f"Yeh command {sp['source']} se padhi hai: `{sp['test']}`. Ek baar haan kahiye, phir "
                           "yaad rakhunga."}
        snap = snapshot(repo, work, setup or sp["setup"], sp["deps_key"])
        if not snap["ok"]:
            return {"ok": False, "stage": "setup", "why": snap["why"], "out": snap.get("out", ""), "spec": sp}
        lim = timeout or sp.get("timeout") or box.CHECK_TIMEOUT
        r = box.run_in(snap["image"], work, f"set -o pipefail; cd {box.WORK}; {run_cmd}", timeout=int(lim),
                       network=False)
        logp = out.write_log(_log_folder(), f"{_slug(repo)}-{int(time.time())}", r["out"])
        res = out.shape(r["out"], r["rc"], logp, r["secs"], r["timed_out"])
        res.update({"stage": "check", "cmd": run_cmd, "source": "aap" if cmd else sp["source"], "repo": repo,
                    "ref": ref or "default branch", "image": snap["image"], "snapshot_cached": snap["cached"],
                    "setup_seconds": snap["seconds"], "total_seconds": round(time.time() - t0, 1),
                    "say": out.say(res, run_cmd), "spec": {k: sp[k] for k in ("lang", "setup", "test", "source")}})
        return res
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------- v0.531 step 2: one workspace per task, reused
def safe_rel(path: str) -> str:
    """A repo-relative path we are willing to write. Anything else is refused by name, never silently dropped."""
    raw = (path or "").strip().replace("\\", "/")
    if not raw or raw.startswith("/") or ".." in raw.split("/") or len(raw) > 400:
        return ""
    p = raw.removeprefix("./")
    if not p or p.startswith(".git/") or p == ".git":
        return ""
    return p


def write_overlay(work: str, overlay: dict[str, str]) -> dict[str, Any]:
    """Put the task's EDITED files on top of the checkout, so a check runs on the code as it is NOW - not on the base
    commit. Without this the lab would only ever test code that is already pushed, which is the whole problem."""
    wrote, bad = [], []
    for path, text in (overlay or {}).items():
        rel = safe_rel(path)
        if not rel:
            bad.append(path)
            continue
        f = Path(work) / rel
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text if isinstance(text, str) else str(text), "utf-8")
            os.chmod(f, 0o666)
            wrote.append(rel)
        except OSError as e:
            bad.append(f"{rel} ({e})")
    return {"wrote": sorted(wrote), "refused": bad[:5]}


def open_workspace(repo: str, ref: str = "", token: str = "", hers: dict[str, str] | None = None,
                   cmd: str = "") -> dict[str, Any]:
    """Clone ONCE for a whole task and keep the folder: a persistent workspace is what every product that runs code
    has and a GitHub-API-only agent does not (docs/CODING_HARNESS_PLAN.md 4). The dependency snapshot is built on the
    FIRST check, not here, so opening a workspace for a task that never runs one costs a clone and nothing more."""
    av = box.available()
    if not av["ok"]:
        return {"ok": False, "stage": "box", "why": av["why"]}
    m = materialize(repo, ref, token)
    if not m["ok"]:
        return {"ok": False, "stage": "clone", "why": m["why"]}
    sp = spec_for(m["dir"], m["paths"], hers)
    want = spec._clean(cmd) or sp["test"]
    bad = spec.refuse_reason(want) if want else ""
    return {"ok": True, "dir": m["dir"], "paths": m["paths"], "spec": sp, "repo": repo, "ref": ref,
            "cmd": "" if bad else want, "source": "aap" if cmd else sp["source"],
            "confirm": bool(want) and not cmd and sp.get("confirm") and not (hers or {}).get("ok"),
            "why": bad or sp["why"], "image": "", "runs": 0}


def run_on(ws: dict[str, Any], cmd: str = "", overlay: dict[str, str] | None = None, timeout: int = 0,
           label: str = "") -> dict[str, Any]:
    """One check on an open workspace, with the task's edits written in first. The snapshot is built (or reused) here."""
    if not ws.get("ok"):
        return {"ok": False, "stage": "box", "why": ws.get("why") or "lab khula nahi"}
    run_cmd = spec._clean(cmd) or ws.get("cmd") or ""
    if not run_cmd:
        return {"ok": False, "stage": "command", "why": ws.get("why") or "koi command declare nahi hui"}
    bad = spec.refuse_reason(run_cmd)
    if bad:
        return {"ok": False, "stage": "command", "why": bad}
    ov = write_overlay(ws["dir"], overlay or {})
    if not ws.get("image"):
        snap = snapshot(ws["repo"], ws["dir"], ws["spec"]["setup"], ws["spec"]["deps_key"])
        if not snap["ok"]:
            return {"ok": False, "stage": "setup", "why": snap["why"], "out": snap.get("out", "")[-4000:]}
        ws["image"], ws["setup_seconds"], ws["snapshot_cached"] = snap["image"], snap["seconds"], snap["cached"]
    lim = int(timeout or ws["spec"].get("timeout") or box.CHECK_TIMEOUT)
    r = box.run_in(ws["image"], ws["dir"], f"set -o pipefail; cd {box.WORK}; {run_cmd}", timeout=lim, network=False)
    ws["runs"] = int(ws.get("runs") or 0) + 1
    logp = out.write_log(_log_folder(), f"{_slug(ws['repo'])}-{label or 'check'}-{int(time.time())}", r["out"])
    res = out.shape(r["out"], r["rc"], logp, r["secs"], r["timed_out"])
    res.update({"stage": "check", "cmd": run_cmd, "files_written": len(ov["wrote"]), "refused_paths": ov["refused"],
                "say": out.say(res, run_cmd), "run": ws["runs"]})
    ws["last_log"] = logp
    return res


def close_workspace(ws: dict[str, Any]) -> None:
    d = (ws or {}).get("dir") or ""
    if d:
        shutil.rmtree(d, ignore_errors=True)
        ws["dir"] = ""


def selftest() -> list[str]:
    """`python -m app.devlab check` - does the box work on THIS machine, end to end, with no repo of hers involved?"""
    lines = []
    av = box.available()
    lines.append(f"docker: {'ok ' + str(av.get('docker')) if av['ok'] else 'NAHI - ' + av['why']}")
    if not av["ok"]:
        return lines
    lines.append(f"base image {box.BASE_IMAGE}: {'bani hai' if av.get('base_built') else 'NAHI bani'}"
                 + (f" (rev {av.get('base_rev') or '1'}, chahiye {box.BASE_REV})" if av.get("base_built") else ""))
    if av.get("base_stale"):
        lines.append("  PURANI image hai - naye niyamon se dobara bana raha hoon")
    if not av.get("base_built") or av.get("base_stale"):
        b = box.build_base(nocache=bool(av.get("base_stale")))
        lines.append(f"  build: {'ok' if b['ok'] else 'FAIL - ' + b['why']} ({b.get('seconds')}s)")
        if not b["ok"]:
            lines += ["  " + x for x in b.get("out", "").splitlines()[-12:]]
            return lines
    work = tempfile.mkdtemp(prefix="hoola-lab-self-")
    try:
        Path(work, "app.py").write_text("def total(items):\n    return sum(i['price'] for i in items)\n")
        Path(work, "test_app.py").write_text("from app import total\n\n\ndef test_empty():\n    assert total([]) == 0\n")
        os.chmod(work, 0o777)
        good = box.run_in(box.BASE_IMAGE, work, "cd /work; python3 -m pytest -q", timeout=120)
        lines.append(f"ek pass hone wala test: exit {good['rc']} ({good['secs']:.1f}s) - "
                     + ("ok" if good["rc"] == 0 else "FAIL: " + good["out"].strip()[-300:]))
        Path(work, "test_app.py").write_text("from app import total\n\n\ndef test_bad():\n    assert total([]) == 1\n")
        bad = box.run_in(box.BASE_IMAGE, work, "cd /work; python3 -m pytest -q", timeout=120)
        shaped = out.shape(bad["out"], bad["rc"], "", bad["secs"], bad["timed_out"])
        lines.append(f"ek fail hone wala test: exit {bad['rc']} - " + ("ok, aur fail ka ant dikh raha hai"
                     if bad["rc"] != 0 and "assert" in shaped["shown"] else "GADBAD: fail pakda nahi gaya"))
        # v0.542: the box must speak the SAME Python as her server, or a check fails on code that runs fine in
        # production - which is exactly what her first working lab_try did (a 3.12+ f-string, SyntaxError on 3.11).
        ver = box.run_in(box.BASE_IMAGE, work, "python3 -c \"import sys;print('%d.%d' % sys.version_info[:2])\"",
                         timeout=60)
        box_py = (ver["out"] or "").strip().splitlines()[-1].strip() if (ver["out"] or "").strip() else "?"
        mine = "%d.%d" % sys.version_info[:2]
        lines.append(f"box ka python {box_py}, server ka {mine}: "
                     + ("ok (ek hi hai)" if box_py == mine else
                        f"GADBAD - farak hai, uska code is box mein toot sakta hai (image rev {box.BASE_REV})"))
        net = box.run_in(box.BASE_IMAGE, work, "cd /work; python3 -c \"import socket;"
                         "socket.create_connection(('1.1.1.1',53),timeout=4)\"", timeout=60)
        lines.append("network band hai: " + ("ok (box bahar nahi pahunch saka)" if net["rc"] != 0
                     else "KHATRA - box ko internet mila, --network none kaam nahi kiya"))
        w = box.run_in(box.BASE_IMAGE, work, "touch /etc/hoola-should-fail 2>&1; echo rc=$?", timeout=60)
        lines.append("root filesystem read-only hai: " + ("ok" if "rc=0" not in w["out"] else "GADBAD - likh paya"))
        # v0.537: her first live lab_try died here, not on any wall - Debian's PEP 668 marker refused the repo's own
        # pip command. This proves a plain `pip install` works AND that what it installs survives the commit.
        Path(work, "needs.txt").write_text("tabulate==0.9.0\n")
        tag = box.BASE_IMAGE + "-selftest"
        ins = box.run_in(box.BASE_IMAGE, work, "cd /work; python3 -m pip install -q -r needs.txt",
                         timeout=300, network=True, commit_to=tag)
        lines.append("repo ka apna `pip install` chalta hai: " + ("ok" if ins["rc"] == 0 else
                     "GADBAD - " + ins["out"].strip()[-300:]))
        if ins["rc"] == 0 and box.has_image(tag):
            kept = box.run_in(tag, work, "cd /work; python3 -c \"import tabulate; print('mila', tabulate.__name__)\"",
                              timeout=90)
            lines.append("install snapshot mein bacha rehta hai: " + ("ok" if "mila" in kept["out"]
                         else "GADBAD - commit ke baad gayab: " + kept["out"].strip()[-300:]))
            box.forget(tag)
        else:
            lines.append("install snapshot mein bacha rehta hai: GADBAD - snapshot hi nahi bani")
        who = box.run_in(box.BASE_IMAGE, work, "id -u", timeout=60)
        lines.append(f"box ka user: {who['out'].strip()[:20]} " + ("(ok, root nahi)" if who["out"].strip() != "0"
                                                                  else "(GADBAD - root hai)"))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    imgs = box.images()
    lines.append(f"lab images: {len(imgs)} ({', '.join(i['image'] + ' ' + i['size'] for i in imgs[:6])})")
    return lines
