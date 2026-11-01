"""Run model- or user-written Python in a locked child process (Shiksha suite, Phase 0).

The child gets:
- its own empty work folder (inputs copied in, outputs collected from it), nothing else of ours;
- a clean environment: no API keys, no tokens, no PYTHON* variables (`-I` isolated mode);
- hard limits: CPU seconds, memory, file size, open files, wall-clock timeout (the whole process group is killed);
- no network: its own empty network namespace (`unshare -rn`) when the kernel allows it, and in every case an audit hook
  that refuses sockets, new processes, ctypes / native loading and any write outside the work folder.

The audit hook is installed before the user's code is compiled and cannot be removed from Python, so the hook alone
already blocks the usual escapes; the namespace makes "no network" true even for C code.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

MAX_CODE = 60_000
MAX_INPUT_BYTES = 40 * 1024 * 1024
OUT_TEXT = 20_000
OUT_FILE_BYTES = 8 * 1024 * 1024
OUT_FILES = 12
LIBS = ("pandas", "numpy", "scipy", "statsmodels", "matplotlib", "openpyxl")

PRELUDE = r'''
import sys, os
_WORK = os.path.realpath(os.getcwd())
_BLOCK = ("socket.", "subprocess.", "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "os.forkpty",
          "os.kill", "os.killpg", "pty.", "ctypes.", "winreg.", "sys.setrecursionlimit_unbounded", "webbrowser.",
          "urllib.Request", "http.client.connect", "ftplib.", "smtplib.", "poplib.", "imaplib.", "telnetlib.", "nntplib.")
_WRITE_EVENTS = ("os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.link", "os.symlink",
                 "os.truncate", "os.utime", "shutil.rmtree", "shutil.move", "shutil.copyfile", "shutil.copytree")

def _inside(p):
    try:
        p = os.fsdecode(p)
    except Exception:
        return False
    full = os.path.realpath(os.path.join(_WORK, p))
    return full == _WORK or full.startswith(_WORK + os.sep)

# reading is allowed only inside the work folder and the Python / library install (imports, fonts, time zones):
# never the server's own folders (code, .env, database, other users' data)
_READ_OK = sorted({os.path.realpath(p) for p in sys.path if p and os.path.isdir(p) and os.path.realpath(p) != _WORK} |
                  {os.path.realpath(p) for p in (sys.prefix, sys.base_prefix, sys.exec_prefix)} |
                  {"/usr/share", "/usr/lib", "/usr/lib64", "/usr/local/lib", "/usr/local/share", "/etc/localtime",
                   "/etc/ld.so.cache", "/etc/mime.types", "/dev/null", "/dev/urandom", "/proc/self", "/proc/cpuinfo",
                   "/proc/meminfo", "/sys/devices/system/cpu", "/sys/fs/cgroup"})
_READ_OK = [p for p in _READ_OK if p not in ("/", os.path.realpath(os.path.expanduser("~")))]

def _readable(p):
    if isinstance(p, int):
        return True
    try:
        full = os.path.realpath(os.path.join(_WORK, os.fsdecode(p)))
    except Exception:
        return False
    if full == _WORK or full.startswith(_WORK + os.sep):
        return True
    return any(full == r or full.startswith(r + os.sep) for r in _READ_OK)

def _hook(event, args):
    if event.startswith(_BLOCK) and event not in ("socket.gethostname",):
        raise PermissionError(f"Sandbox: '{event}' allowed nahi (no network, no new programs).")
    if event == "open" and args:
        path, mode = args[0], (args[1] if len(args) > 1 else "r")
        if isinstance(mode, int):
            writing = bool(mode & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC))
        else:
            writing = any(c in str(mode or "r") for c in "wax+")
        if writing and not isinstance(path, int) and not _inside(path):
            raise PermissionError("Sandbox: sirf apne work folder mein likh sakte hain.")
        if not writing and not _readable(path):
            raise PermissionError("Sandbox: yeh file padhna allowed nahi (sirf di gayi files).")
    if event in ("os.listdir", "os.scandir") and args and args[0] is not None and not _readable(args[0]):
        raise PermissionError("Sandbox: is folder ko dekhna allowed nahi.")
    if event in _WRITE_EVENTS:
        for a in args[:2]:
            if isinstance(a, (str, bytes, os.PathLike)) and not _inside(a):
                raise PermissionError(f"Sandbox: '{event}' work folder ke bahar allowed nahi.")

import matplotlib as _m  # noqa: E402  (headless charts; loaded before the hook so its font cache can be read)
''' + "\n" + r'''
sys.addaudithook(_hook)
del _hook
_src = open("main.py", encoding="utf-8").read()
_g = {"__name__": "__main__", "__file__": "main.py", "__builtins__": __builtins__}
exec(compile(_src, "main.py", "exec"), _g)
try:
    import matplotlib.pyplot as _plt
    for _i, _n in enumerate(_plt.get_fignums(), 1):
        if not os.path.exists(f"figure_{_i}.png"):
            _plt.figure(_n).savefig(f"figure_{_i}.png", dpi=130, bbox_inches="tight")
except Exception:
    pass
'''

PRELUDE_NO_MPL = PRELUDE.replace("import matplotlib as _m  # noqa: E402  (headless charts; loaded before the hook so its font cache can be read)", "")


class PylabError(Exception):
    pass


@lru_cache
def libs() -> dict[str, str]:
    """Which analysis libraries the sandbox can import (name -> version, '' when missing)."""
    code = ("import importlib, json\nout = {}\nfor n in %r:\n    try:\n        m = importlib.import_module(n)\n"
            "        out[n] = getattr(m, '__version__', 'yes')\n    except Exception:\n        out[n] = ''\nprint(json.dumps(out))") % (LIBS,)
    try:
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60, env=_env("/tmp"))
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {n: "" for n in LIBS}


@lru_cache
def net_isolation() -> bool:
    """Can we give the child its own empty network namespace (unshare -rn)?"""
    if os.environ.get("PYLAB_NO_UNSHARE") == "1" or not shutil.which("unshare"):
        return False
    try:
        return subprocess.run(["unshare", "-rn", "--", sys.executable, "-I", "-c", "pass"], capture_output=True,
                              timeout=10).returncode == 0
    except Exception:
        return False


def _env(work: str) -> dict[str, str]:
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": work, "TMPDIR": work, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "MPLBACKEND": "Agg", "MPLCONFIGDIR": work, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}


def _limits(cpu_s: int, mem_mb: int):
    def go():
        import resource
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 1))
        mem = mem_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024, 64 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    return go


def _safe_name(name: str) -> str:
    n = os.path.basename(str(name or "").replace("\\", "/")).strip() or "input"
    n = "".join(ch for ch in n if ch.isalnum() or ch in "._- ")[:120].strip(". ") or "input"
    return "data_" + n if n in ("main.py", "_prelude.py") else n


def run(code: str, files: dict[str, bytes] | None = None, timeout_s: int = 30, mem_mb: int = 1024,
        stdin: str = "") -> dict[str, Any]:
    """Run `code` (the file main.py) with `files` copied into its work folder.

    Returns {ok, exit, stdout, stderr, error, seconds, timed_out, net_isolated, outputs: [{name, size, data}]}.
    `outputs` are the files the code created (charts, CSVs, Excel) - at most OUT_FILES, each at most OUT_FILE_BYTES."""
    code = str(code or "")
    if not code.strip():
        raise PylabError("Chalaane ke liye code chahiye.")
    if len(code) > MAX_CODE:
        raise PylabError(f"Code {MAX_CODE // 1000}k characters se lamba hai.")
    files = files or {}
    if sum(len(b) for b in files.values()) > MAX_INPUT_BYTES:
        raise PylabError("Input files 40 MB se zyada hain.")
    timeout_s = max(1, min(int(timeout_s or 30), 300))
    mem_mb = max(128, min(int(mem_mb or 1024), 4096))
    work = tempfile.mkdtemp(prefix="pylab_")
    try:
        os.chmod(work, 0o700)
        given = set()
        for name, data in files.items():
            n = _safe_name(name)
            Path(work, n).write_bytes(data)
            given.add(n)
        Path(work, "main.py").write_text(code, encoding="utf-8")
        have_mpl = bool(libs().get("matplotlib"))
        Path(work, "_prelude.py").write_text(PRELUDE if have_mpl else PRELUDE_NO_MPL, encoding="utf-8")
        cmd = [sys.executable, "-I", "-X", "utf8", "_prelude.py"]
        iso = net_isolation()
        if iso:
            cmd = ["unshare", "-rn", "--"] + cmd
        t0 = time.monotonic()
        p = subprocess.Popen(cmd, cwd=work, env=_env(work), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, preexec_fn=_limits(timeout_s, mem_mb))
        timed_out = False
        try:
            out, err = p.communicate(stdin.encode() if stdin else None, timeout=timeout_s + 2)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except Exception:
                p.kill()
            out, err = p.communicate()
        secs = round(time.monotonic() - t0, 2)
        outputs = []
        for f in sorted(Path(work).iterdir()):
            if f.name in ("main.py", "_prelude.py") or f.name in given or not f.is_file() or f.name.startswith("."):
                continue
            if f.suffix in (".pyc",) or f.name.endswith(".cache") or f.name.startswith("fontlist"):
                continue
            if len(outputs) >= OUT_FILES:
                break
            size = f.stat().st_size
            outputs.append({"name": f.name, "size": size, "data": f.read_bytes() if size <= OUT_FILE_BYTES else b""})
        so, se = out.decode("utf-8", "replace"), err.decode("utf-8", "replace")
        rc = p.returncode
        error = ""
        if timed_out or rc in (-signal.SIGXCPU, -signal.SIGKILL) and secs >= timeout_s:
            error, timed_out = f"Time limit ({timeout_s} s) poora ho gaya; code ruk gaya.", True
        elif rc != 0:
            last = [ln for ln in se.strip().splitlines() if ln.strip()][-1:] or [f"exit {rc}"]
            error = "MemoryError: memory limit" if "MemoryError" in se else last[0][:400]
        return {"ok": rc == 0 and not timed_out, "exit": rc, "stdout": _trim(so), "stderr": _trim(_clean_tb(se)),
                "error": error, "seconds": secs, "timed_out": timed_out, "net_isolated": iso, "outputs": outputs}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _trim(s: str, n: int = OUT_TEXT) -> str:
    return s if len(s) <= n else s[: n // 2] + f"\n... [{len(s) - n} characters cut] ...\n" + s[-n // 2:]


def _clean_tb(se: str) -> str:
    """Hide the sandbox's own frames from tracebacks (the code author only needs main.py lines)."""
    keep, skip = [], False
    for ln in se.splitlines():
        if '"_prelude.py"' in ln:
            skip = True
            continue
        if skip and ln.startswith("    "):
            skip = False
            continue
        skip = False
        keep.append(ln)
    return "\n".join(keep)
