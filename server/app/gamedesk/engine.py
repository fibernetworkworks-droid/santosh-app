"""Godot 4 in a box: a headless smoke run (the game plays ~10 s with no screen, so script errors surface) and the Web
export (single-threaded: runs on any host, no special headers). Same safety as the 3D Studio box:

- No network: `unshare -rn` when the kernel allows it (GAME_NO_NET=false turns it off for odd hosts).
- No secrets: a tiny environment (PATH, HOME = the job folder, XDG dirs inside it); nothing from Hoola's .env.
- Its own folder, own process group, memory / file-size / core limits, nice 10, a wall-clock kill.
- Export templates are reached through a link inside the job folder, so Godot never writes to the real data folder.

Godot: GODOT_BIN, else ~/apps/godot/godot, else /opt/godot/godot, else `godot` on PATH (deploy/setup_godot.py installs it
+ the Web templates into ~/apps/godot and ~/.local/share/godot/export_templates)."""
from __future__ import annotations

import gzip
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

_NET_OK: bool | None = None
_VERSION: str | None = None
ERROR_LINE = re.compile(r"(SCRIPT ERROR|Parse Error|Invalid call|Invalid access|Invalid get|Invalid set|"
                        r"Identifier .* not declared|Cannot call|Nonexistent function|Attempt to call|"
                        r"ERROR: .*res://(?!hoola_probe))", re.I)


class EngineError(Exception):
    pass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def find() -> str:
    for cand in (os.environ.get("GODOT_BIN", "").strip(), str(Path.home() / "apps" / "godot" / "godot"), "/opt/godot/godot",
                 shutil.which("godot") or ""):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return ""


def version() -> str:
    """'4.7.2' (from `godot --version`), '' when not installed."""
    global _VERSION
    if _VERSION is None:
        b = find()
        if not b:
            return ""
        try:
            out = subprocess.run([b, "--headless", "--version"], capture_output=True, text=True, timeout=60).stdout
            m = re.search(r"(\d+\.\d+(?:\.\d+)?)\.stable", out or "")
            _VERSION = m.group(1) if m else ""
        except Exception:
            _VERSION = ""
    return _VERSION


def templates_dir() -> Path | None:
    v = version()
    if not v:
        return None
    base = Path(os.environ.get("GODOT_TEMPLATES", "") or (Path.home() / ".local/share/godot/export_templates")) / f"{v}.stable"
    return base if (base / "web_nothreads_release.zip").is_file() else None


def net_isolation() -> bool:
    global _NET_OK
    if os.environ.get("GAME_NO_NET", "true").lower() in ("0", "false", "off"):
        return False
    if _NET_OK is None:
        u = shutil.which("unshare")
        try:
            _NET_OK = bool(u) and subprocess.run([u, "-rn", "true"], capture_output=True, timeout=5).returncode == 0
        except Exception:
            _NET_OK = False
    return _NET_OK


def health() -> dict[str, Any]:
    b = find()
    return {"installed": bool(b), "version": version() if b else "", "web_templates": bool(templates_dir()),
            "debug_template": debug_template(), "no_network": net_isolation() if b else False}


def _limits():
    import resource
    mem = _env_int("GAME_MEM_MB", 6144) * 1024 * 1024
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


def _run(job: Path, args: list[str], log_name: str, timeout: int, holder: dict | None = None) -> tuple[int, str, bool]:
    b = find()
    if not b:
        raise EngineError("Godot server par install nahi hai (deploy/setup_godot.py chalaiye)")
    tpl = templates_dir()
    xdg = job / ".xdg"
    (xdg / "data" / "godot" / "export_templates").mkdir(parents=True, exist_ok=True)
    (xdg / "config").mkdir(exist_ok=True)
    (xdg / "cache").mkdir(exist_ok=True)
    (job / "tmp").mkdir(exist_ok=True)
    if tpl is not None:
        link = xdg / "data" / "godot" / "export_templates" / tpl.name
        if not link.exists():
            link.symlink_to(tpl, target_is_directory=True)
    cmd = [b, "--headless"] + args
    if net_isolation():
        cmd = [shutil.which("unshare") or "unshare", "-rn"] + cmd
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(job), "TMPDIR": str(job / "tmp"), "LANG": "C.UTF-8",
           "XDG_DATA_HOME": str(xdg / "data"), "XDG_CONFIG_HOME": str(xdg / "config"), "XDG_CACHE_HOME": str(xdg / "cache")}
    logp = job / log_name
    with open(logp, "wb") as logf:
        p = subprocess.Popen(cmd, cwd=str(job), env=env, stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             preexec_fn=_limits)
        if holder is not None:
            holder["proc"] = p
        timed_out = False
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                p.kill()
            p.wait()
    text = logp.read_text(errors="replace")
    return p.returncode, re.sub(r"\x1b\[[0-9;]*m", "", text), timed_out


def errors_in(log: str) -> list[str]:
    out: list[str] = []
    lines = log.splitlines()
    for i, ln in enumerate(lines):
        if ERROR_LINE.search(ln) and "hoola_probe" not in ln:
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            item = (ln.strip() + (" | " + nxt if nxt.startswith("at:") or "res://" in nxt else ""))[:300]
            if item not in out:
                out.append(item)
    return out[:12]


def smoke(job: Path, frames: int = 600, holder: dict | None = None) -> dict[str, Any]:
    """Play the game headless for `frames` frames (~10 s at 60 fps): parse + runtime script errors come out here."""
    t0 = time.time()
    # v0.406: import first - it builds the global class cache, so `class_name Helper` + Helper.new() works headless
    # (a bare --quit-after run has no cache and every class_name is "not declared"; found by a real run, and named in
    # Claude-Code-Game-Studios' godot-parse-check notes). Its own errors are left to the play run that follows.
    _ic, _ilog, ito = _run(job, ["--path", "proj", "--import"], "import.log", _env_int("GAME_IMPORT_TIMEOUT_S", 120), holder)
    if ito:
        return {"ok": False, "errors": ["the project import did not finish in time"], "seconds": round(time.time() - t0, 1),
                "exit": _ic}
    code, log, to = _run(job, ["--path", "proj", "--quit-after", str(frames)], "smoke.log",
                         _env_int("GAME_SMOKE_TIMEOUT_S", 120), holder)
    errs = errors_in(log)
    if to:
        errs.append("the game did not finish 10 seconds of play in time (an endless loop in _ready / _process?)")
    return {"ok": not errs, "errors": errs, "seconds": round(time.time() - t0, 1), "exit": code}


def debug_template() -> bool:
    """v0.415 the debug web template (QA farm: release web builds print no script errors in the browser)."""
    t = templates_dir()
    return bool(t and (t / "web_nothreads_debug.zip").is_file())


def export_web(job: Path, holder: dict | None = None, debug: bool = False) -> dict[str, Any]:
    """Web export into job/build: index.html / .js / .wasm / .pck (+ .wasm.gz and .pck.gz for small downloads).
    debug=True (QA farm) -> job/build_debug with Godot's debug template, so script errors reach the browser console."""
    if templates_dir() is None:
        raise EngineError("Godot ke Web export templates nahi mile (deploy/setup_godot.py chalaiye)")
    if debug and not debug_template():
        raise EngineError("Godot ka debug Web template nahi mila (deploy/setup_godot.py dobara chalaiye)")
    out = job / ("build_debug" if debug else "build")
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    t0 = time.time()
    code, log, to = _run(job, ["--path", "proj", "--export-debug" if debug else "--export-release", "Web",
                               f"../{out.name}/index.html"], "export_debug.log" if debug else "export.log",
                         _env_int("GAME_EXPORT_TIMEOUT_S", 300), holder)
    ok = (out / "index.html").is_file() and (out / "index.wasm").is_file() and (out / "index.pck").is_file()
    if not ok:
        tail = " | ".join(errors_in(log) or [log.strip()[-300:]])
        return {"ok": False, "errors": [("export timed out" if to else f"export failed (exit {code})") + f": {tail}"],
                "seconds": round(time.time() - t0, 1)}
    for name in ("index.wasm", "index.pck", "index.js"):
        src = out / name
        with open(src, "rb") as f, gzip.open(str(src) + ".gz", "wb", compresslevel=6) as g:
            shutil.copyfileobj(f, g)
    size = {p.name: p.stat().st_size for p in out.iterdir() if p.is_file()}
    return {"ok": True, "errors": [], "seconds": round(time.time() - t0, 1), "bytes": sum(v for k, v in size.items()
            if not k.endswith(".gz")), "download_bytes": sum(v for k, v in size.items() if k.endswith(".gz") or
            k in ("index.html",)), "files": sorted(size)}


def kill(holder: dict) -> None:
    holder["cancelled"] = True
    p = holder.get("proc")
    if p is not None and p.poll() is None:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
