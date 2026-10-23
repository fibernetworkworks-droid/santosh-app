"""Start Blender for one job in a box.

- Blender: `BLENDER_BIN` (the official binary from download.blender.org, `deploy/setup_blender.sh` puts it in
  /opt/blender) or `BLENDER_PY` (a Python that has the official `bpy` module from PyPI). Found by itself when unset.
- No network: `unshare -rn` (a new user + network namespace with only loopback) when the kernel allows it; the import
  gate in runner.py and guard.py's check keep sockets out either way.
- No secrets: the child gets a tiny environment (PATH, HOME = the job folder, TMPDIR, LANG); nothing from Hoola's .env.
- Its own folder, own process group, memory / file-size / core limits, nice 10, a wall-clock timeout that kills the group.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.blender3d")
RUNNER = Path(__file__).with_name("runner.py")
_NET_OK: bool | None = None


class SandboxError(Exception):
    pass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def find() -> dict[str, str]:
    """{'kind': 'bin'|'py', 'path': ...} or {} when no Blender is installed."""
    b = os.environ.get("BLENDER_BIN", "").strip()
    if b and os.path.isfile(b) and os.access(b, os.X_OK):
        return {"kind": "bin", "path": b}
    p = os.environ.get("BLENDER_PY", "").strip()
    if p and os.path.isfile(p):
        return {"kind": "py", "path": p}
    for cand in ("/opt/blender/blender", shutil.which("blender") or ""):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return {"kind": "bin", "path": cand}
    home = Path(os.environ.get("BLENDER_HOME", "") or Path.home() / "apps" / "santosh-core" / ".blender-venv")
    py = home / "bin" / "python"
    if py.is_file():
        return {"kind": "py", "path": str(py)}
    return {}


def net_isolation() -> bool:
    global _NET_OK
    if os.environ.get("BLENDER_NO_NET", "true").lower() in ("0", "false", "off"):
        return False
    if _NET_OK is None:
        u = shutil.which("unshare")
        try:
            _NET_OK = bool(u) and subprocess.run([u, "-rn", "true"], capture_output=True, timeout=5).returncode == 0
        except Exception:
            _NET_OK = False
    return _NET_OK


def _limits():
    import resource
    mem = _env_int("BLENDER_MEM_MB", 8192) * 1024 * 1024
    for res, val in ((resource.RLIMIT_AS, mem), (resource.RLIMIT_FSIZE, 1024 * 1024 * 1024), (resource.RLIMIT_CORE, 0)):
        try:
            resource.setrlimit(res, (val, val))
        except (ValueError, OSError):
            pass
    os.setsid()
    try:
        os.nice(10)
    except OSError:
        pass


def run(job_dir: Path, job: dict[str, Any], timeout: int | None = None, holder: dict | None = None) -> dict[str, Any]:
    """Write job.json, run Blender, return result.json (+ log tail). Never raises for a script error (that is in
    result['errors']); raises SandboxError when Blender itself can't run."""
    who = find()
    if not who:
        raise SandboxError("Blender is server par install nahi hai (deploy/setup_blender.sh chalaiye)")
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "tmp").mkdir(exist_ok=True)
    job = {**job, "out_dir": str(job_dir)}
    jp = job_dir / "job.json"
    jp.write_text(json.dumps(job), encoding="utf-8")
    res_p = job_dir / "result.json"
    res_p.unlink(missing_ok=True)
    if who["kind"] == "bin":
        cmd = [who["path"], "-b", "--factory-startup", "--disable-autoexec", "-noaudio", "--python", str(RUNNER), "--", str(jp)]
    else:
        cmd = [who["path"], "-I", str(RUNNER), str(jp)]
    if net_isolation():
        cmd = [shutil.which("unshare") or "unshare", "-rn"] + cmd
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(job_dir), "TMPDIR": str(job_dir / "tmp"),
           "LANG": "C.UTF-8", "OMP_NUM_THREADS": str(_env_int("BLENDER_THREADS", 2)), "PYTHONNOUSERSITE": "1"}
    timeout = timeout or _env_int("BLENDER_TIMEOUT_S", 600)
    t0 = time.time()
    with open(job_dir / "blender.log", "wb") as logf:
        p = subprocess.Popen(cmd, cwd=str(job_dir), env=env, stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             preexec_fn=_limits)
        if holder is not None:
            holder["proc"] = p
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                p.kill()
            p.wait()
            return {"ok": False, "errors": [f"{timeout} second mein poora nahi hua: model halka karo / loop chhota karo"],
                    "timeout": True, "seconds": round(time.time() - t0, 1)}
    if holder is not None and holder.get("cancelled"):
        return {"ok": False, "errors": ["rok diya gaya"], "cancelled": True}
    if not res_p.exists():
        tail = (job_dir / "blender.log").read_text(errors="replace")[-1500:]
        raise SandboxError(f"Blender ne jawab nahi diya (exit {p.returncode}): {tail[-400:]}")
    out = json.loads(res_p.read_text(encoding="utf-8"))
    out["wall_s"] = round(time.time() - t0, 1)
    out["isolated"] = net_isolation()
    return out


def health() -> dict[str, Any]:
    who = find()
    return {"installed": bool(who), "kind": who.get("kind", ""), "no_network": net_isolation() if who else False}


def kill(holder: dict) -> None:
    holder["cancelled"] = True
    p = holder.get("proc")
    if p is not None and p.poll() is None:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            p.kill()
