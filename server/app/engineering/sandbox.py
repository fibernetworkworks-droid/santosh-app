"""Start the engineering runner for one job in a box (same safety as blender3d/sandbox.py).

- Python: `ENG_PY` (a Python that has cadquery) else the server's own Python.
- No network: `unshare -rn` when the kernel allows it; the runner's import gate and guard.py keep sockets out either way.
- No secrets: the child gets a tiny environment (PATH, HOME = the job folder, TMPDIR, LANG); nothing from Hoola's .env.
- Its own folder, own process group, memory / file-size / core limits, nice 10, a wall-clock timeout that kills the group.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

RUNNER = Path(__file__).with_name("runner.py")
_NET_OK: bool | None = None


class SandboxError(Exception):
    pass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def python() -> str:
    p = os.environ.get("ENG_PY", "").strip()
    return p if p and os.path.isfile(p) else sys.executable


def installed() -> bool:
    try:
        r = subprocess.run([python(), "-I", "-c", "import cadquery"], capture_output=True, timeout=60,
                           env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"})
        return r.returncode == 0
    except Exception:
        return False


def net_isolation() -> bool:
    global _NET_OK
    if os.environ.get("ENG_NO_NET", "true").lower() in ("0", "false", "off"):
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
    mem = _env_int("ENG_MEM_MB", 6144) * 1024 * 1024
    for res, val in ((resource.RLIMIT_AS, mem), (resource.RLIMIT_FSIZE, 512 * 1024 * 1024), (resource.RLIMIT_CORE, 0)):
        try:
            resource.setrlimit(res, (val, val))
        except (ValueError, OSError):
            pass
    os.setsid()
    try:
        os.nice(10)
    except OSError:
        pass


def run(job_dir: Path, code: str, timeout: int | None = None) -> dict[str, Any]:
    """Run one script; returns result.json (+ wall_s / isolated). A script error is in result['errors'];
    SandboxError when the runner itself could not start."""
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "tmp").mkdir(exist_ok=True)
    jp = job_dir / "job.json"
    jp.write_text(json.dumps({"code": code, "out_dir": str(job_dir)}), encoding="utf-8")
    res_p = job_dir / "result.json"
    res_p.unlink(missing_ok=True)
    cmd = [python(), "-I", str(RUNNER), str(jp)]            # -I: the runner adds its own folder for parts.py
    if net_isolation():
        cmd = [shutil.which("unshare") or "unshare", "-rn"] + cmd
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(job_dir), "TMPDIR": str(job_dir / "tmp"),
           "LANG": "C.UTF-8", "OMP_NUM_THREADS": str(_env_int("ENG_THREADS", 2)), "PYTHONNOUSERSITE": "1"}
    timeout = timeout or _env_int("ENG_TIMEOUT_S", 600)
    t0 = time.time()
    with open(job_dir / "run.log", "wb") as logf:
        p = subprocess.Popen(cmd, cwd=str(job_dir), env=env, stdout=logf, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, preexec_fn=_limits)
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                p.kill()
            p.wait()
            return {"ok": False, "errors": [f"{timeout} second mein poora nahi hua: part halka karo / loop chhota karo"],
                    "timeout": True, "wall_s": round(time.time() - t0, 1)}
    if not res_p.exists():
        tail = (job_dir / "run.log").read_text(errors="replace")[-400:]
        raise SandboxError(f"Engineering runner ne jawab nahi diya (exit {p.returncode}): {tail}")
    out = json.loads(res_p.read_text(encoding="utf-8"))
    out["wall_s"] = round(time.time() - t0, 1)
    out["isolated"] = net_isolation()
    return out
