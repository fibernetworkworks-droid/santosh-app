"""v0.814 the build of an App Engine app, in the box.

A build = TypeScript's own check (tsc --noEmit) + `vite build`, run in the `hoola-appengine:base` image with NO
network, a read-only root, no capabilities, a non-root user and caps on memory / CPU / processes / time. The app's
files go in read-only; only the folder the build writes out to is writable. Nothing is installed: the packages are the
image's own (image.py).

At most `app_engine_previews` builds run at once on this server (the plan's decision 1, default 2): a build that cannot
start within a short wait says "queued" plainly instead of starting a third.

`runner=local` (settings `app_engine_runner`) runs the same two commands on the host with the node_modules folder named
by HOOLA_APPENGINE_NODE_MODULES - for development and tests only; the server default is the box."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from . import image as IMG

TIMEOUT = 240
_GATE: threading.BoundedSemaphore | None = None
_GATE_N = 0
_GATE_LOCK = threading.Lock()
STATS = {"builds": 0, "queued": 0, "failed": 0}
SCRIPT = ("mkdir -p /tmp/w && cp -R /src/. /tmp/w/ && ln -s /opt/tpl/node_modules /tmp/w/node_modules && cd /tmp/w && "
          "{ node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json --pretty false > /out/tsc.txt 2>&1; echo $? > /out/tsc.rc; } ; "
          "node node_modules/vite/bin/vite.js build --configLoader runner --logLevel warn > /out/vite.txt 2>&1; rc=$?; "
          "if [ $rc = 0 ]; then cp -R dist /out/dist; fi; exit $rc")


def _settings():
    from ..config import get_settings
    return get_settings()


def gate() -> threading.BoundedSemaphore:
    global _GATE, _GATE_N
    n = max(1, int(getattr(_settings(), "app_engine_previews", 2) or 2))
    with _GATE_LOCK:
        if _GATE is None or n != _GATE_N:
            _GATE, _GATE_N = threading.BoundedSemaphore(n), n
        return _GATE


def mode() -> str:
    m = str(getattr(_settings(), "app_engine_runner", "box") or "box").lower()
    return m if m in ("box", "local") else "box"


def available() -> dict[str, Any]:
    """Can this server build an app right now? Never raises; the reason is in plain words."""
    if mode() == "local":
        nm = os.environ.get("HOOLA_APPENGINE_NODE_MODULES", "")
        ok = bool(nm) and (Path(nm) / "vite" / "package.json").exists() and bool(shutil.which("node"))
        return {"ok": ok, "runner": "local", "why": "" if ok else "local runner: HOOLA_APPENGINE_NODE_MODULES + node are needed"}
    from ..devlab import box
    if not box.docker():
        return {"ok": False, "runner": "box", "why": "docker is not on this server"}
    rc, out, _ = box._run([box.docker(), "version", "--format", "{{.Server.Version}}"], 25)
    if rc != 0:
        return {"ok": False, "runner": "box", "why": "the docker daemon is not answering"}
    if not box.has_image(IMG.IMAGE):
        return {"ok": False, "runner": "box", "why": "the App Engine image is not built yet: run `python -m app.appengine setup` "
                                                     "(vps-ops > appengine_setup)"}
    r = IMG.rev()
    if r != IMG.IMAGE_REV:
        return {"ok": False, "runner": "box", "why": f"the App Engine image is older (rev {r or '?'}, needs {IMG.IMAGE_REV}): "
                                                     "run `python -m app.appengine setup --rebuild`"}
    return {"ok": True, "runner": "box", "image": IMG.IMAGE, "rev": r, "why": ""}


_TSC = re.compile(r"^(?:/tmp/w/)?(src/[^\s(]+)\((\d+),(\d+)\): error (TS\d+): (.+)$", re.M)
_VITE = re.compile(r"(?:/tmp/w/|[A-Za-z]:?/[^\s:]*?/)?(src/[\w./-]+\.(?:tsx|ts|css))(?:[:(](\d+)[:,](\d+)\)?)?")


def parse_tsc(txt: str) -> list[dict[str, Any]]:
    return [{"file": m.group(1), "line": int(m.group(2)), "col": int(m.group(3)), "code": m.group(4),
             "message": m.group(5)[:300]} for m in _TSC.finditer(txt or "")][:40]


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def parse_vite(txt: str, root: str = "/tmp/w/") -> list[dict[str, Any]]:
    t = _ANSI.sub("", (txt or "")).replace(root, "")
    out = []
    for line in t.splitlines():
        if "error" not in line.lower() and "failed" not in line.lower() and "could not" not in line.lower():
            continue
        m = _VITE.search(line)
        out.append({"file": m.group(1) if m else "", "line": int(m.group(2)) if m and m.group(2) else 0,
                    "message": line.strip()[:400]})
        if len(out) >= 20:
            break
    return out


def _box_argv(src: str, out: str) -> list[str]:
    from ..devlab import box
    return [box.docker(), "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp:rw,exec,size=768m",
            "--user", "1000:1000", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--memory", "1536m", "--memory-swap", "1536m", "--cpus", "2", "--pids-limit", "256",
            "--env", "NODE_OPTIONS=--max-old-space-size=1024", "--env", "CI=1", "--env", "NO_COLOR=1", "--env", "FORCE_COLOR=0",
            "-v", f"{os.path.abspath(src)}:/src:ro", "-v", f"{os.path.abspath(out)}:/out:rw",
            IMG.IMAGE, "sh", "-c", SCRIPT]


def _local(src: str, out: str) -> tuple[int, str, float]:
    nm = os.environ.get("HOOLA_APPENGINE_NODE_MODULES", "")
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="hoola-ae-w-") as w:
        shutil.copytree(src, w, dirs_exist_ok=True)
        os.symlink(nm, os.path.join(w, "node_modules"))
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": w, "CI": "1", "LANG": "C.UTF-8", "NO_COLOR": "1", "FORCE_COLOR": "0"}
        r1 = subprocess.run(["node", "node_modules/typescript/bin/tsc", "--noEmit", "-p", "tsconfig.json", "--pretty", "false"],
                            cwd=w, capture_output=True, text=True, timeout=TIMEOUT, env=env)
        Path(out, "tsc.txt").write_text((r1.stdout or "") + (r1.stderr or ""))
        Path(out, "tsc.rc").write_text(str(r1.returncode))
        r2 = subprocess.run(["node", "node_modules/vite/bin/vite.js", "build", "--configLoader", "runner", "--logLevel", "warn"],
                            cwd=w, capture_output=True, text=True, timeout=TIMEOUT, env=env)
        Path(out, "vite.txt").write_text(((r2.stdout or "") + (r2.stderr or "")).replace(w + "/", ""))
        if r2.returncode == 0:
            shutil.copytree(os.path.join(w, "dist"), os.path.join(out, "dist"))
        return r2.returncode, "", time.time() - t0


def build(src: Path, wait: float = 20.0) -> dict[str, Any]:
    """Build `src` (a whole app folder). Returns ok, seconds, the built dist folder (a temp dir the caller moves),
    TypeScript's problems and the build's own problems. Never raises for a failed build; raises RuntimeError only when
    the box is not there."""
    av = available()
    if not av["ok"]:
        raise RuntimeError(av["why"])
    g = gate()
    if not g.acquire(timeout=wait):
        STATS["queued"] += 1
        return {"ok": False, "queued": True, "why": f"{_GATE_N} app builds are already running on this server; "
                                                     "this one starts when one finishes."}
    out = Path(tempfile.mkdtemp(prefix="hoola-ae-out-"))
    try:
        os.chmod(out, 0o777)                      # the box writes as uid 1000
        t0 = time.time()
        if mode() == "local":
            rc, txt, _ = _local(str(src), str(out))
        else:
            from ..devlab import box
            rc, txt, _ = box._run(_box_argv(str(src), str(out)), TIMEOUT + 30)
        secs = round(time.time() - t0, 2)
        STATS["builds"] += 1
        read = lambda n: (out / n).read_text("utf-8", "replace") if (out / n).exists() else ""   # noqa: E731
        vite_txt, tsc_txt = _ANSI.sub("", read("vite.txt")).replace("/tmp/w/", ""), read("tsc.txt")
        tsc_rc = read("tsc.rc").strip()
        dist = out / "dist"
        ok = rc == 0 and (dist / "index.html").exists()
        if not ok:
            STATS["failed"] += 1
        timed_out = rc == 124
        return {"ok": ok, "queued": False, "seconds": secs, "runner": mode(), "dist": str(dist) if ok else "",
                "out_dir": str(out), "types_ok": tsc_rc == "0", "types": parse_tsc(tsc_txt),
                "build_problems": [] if ok else parse_vite(vite_txt or txt),
                "log": ((vite_txt or txt)[-6000:] if not ok else vite_txt[-2000:]), "types_log": tsc_txt[-4000:],
                "timed_out": timed_out,
                "why": "" if ok else ("the build took too long" if timed_out else "the build failed - read build_problems")}
    finally:
        g.release()
