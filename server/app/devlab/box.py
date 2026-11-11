"""v0.456 the box: Docker, with the walls the research says are the only honest ones.

Every claim this file acts on comes from docs/CODING_HARNESS_PLAN.md 1.4:
- OpenHands uses Docker because "executing untrusted code can pose significant risks to the host system";
- Codex "blocks internet access during the agent phase" and lets only the SETUP script reach the network, with the
  secrets removed before the agent starts;
- Anthropic: "treat every command as untrusted input... run the session in an isolated environment, such as a
  container or a virtual machine, as the least-privileged user that can do the work", and command-text allowlists are
  "fragile", so we do not pretend to filter commands - we take away what a command could reach.

So: a CHECK gets no network, no capabilities, no secrets, a non-root user, a read-only root filesystem, and caps on
memory / CPU / pids / time. A SETUP gets the network and nothing else. The owner's token NEVER enters the box: the
clone happens outside it and `.git` is stripped before the files go in."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.devlab")

BASE_IMAGE = "hoola-devlab:base"
# v0.532 the Dockerfile text lives HERE, not only on disk: the VPS deploy copies `server/app` alone, so
# deploy/devlab/Dockerfile does not exist next to the running code (lab_check would have failed with "Dockerfile nahi
# mili" - that is how a feature ships broken). A build writes this text to a temp folder, so it works wherever the code
# runs from. deploy/devlab/Dockerfile stays as the readable copy and a test asserts the two are identical.
DOCKERFILE_TEXT = r"""# v0.456 PRAYOGSHALA (the coding lab) - the base image every check runs in.
# Built ONCE on the VPS by `python -m app.devlab setup`; per-repo dependency snapshots are committed on top of it.
# Rules this image obeys (docs/CODING_HARNESS_PLAN.md 1.4): no secret ever enters it, it runs as a non-root user,
# and a CHECK runs with --network none (only the one-time SETUP step gets the network, the way Codex does it).
FROM python:3.13-slim-bookworm

# v0.542: the box MUST speak the same Python as her server. Debian 12's own python3 is 3.11, and her code is
# valid 3.12+ (PEP 701 allows a backslash inside an f-string expression - app/notebook/render.py:517 uses one),
# so on the old image EVERY check died at import with a SyntaxError in code that runs perfectly in production.
# A lab on a different language version than production does not test her code; it invents failures.
# python:3.13-slim-bookworm keeps bookworm's apt packages (node, jdk 17) and puts 3.13 on /usr/local/bin.
#
# v0.537: the walls and this image are one thing - bump BASE_REV whenever the image must be rebuilt, and
# `lab_check` can then tell her that the image on her VPS is older than the code reading it.
LABEL hoola.devlab.rev="3"

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 NODE_OPTIONS=--max-old-space-size=1536 HOME=/home/lab

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git make gcc g++ pkg-config \
      nodejs npm \
      openjdk-17-jdk-headless \
      sqlite3 ripgrep jq unzip \
 && rm -rf /var/lib/apt/lists/*

# v0.537: Debian marks its Python "externally managed" (PEP 668), so a repo's own declared
# `pip install -r requirements.txt` dies with error: externally-managed-environment - which is exactly what
# her first live lab_try hit. A container IS the virtual environment, so the marker comes off here, once, and
# every repo's real command works without Hoola rewriting it. The python:3.13 image carries no marker of its
# own, but a `python3` apt package could still drop one in, so this stays - it costs nothing and cannot lie.
RUN rm -f /usr/lib/python3*/EXTERNALLY-MANAGED /usr/local/lib/python3*/EXTERNALLY-MANAGED

# pytest / ruff for Python repos that declare no dev dependencies of their own
RUN python3 -m pip install --no-cache-dir pytest pytest-timeout ruff

RUN useradd -m -u 1000 -s /bin/bash lab \
 && mkdir -p /work /home/lab/.local/bin \
 && chown -R lab:lab /work /home/lab
USER lab
WORKDIR /work
CMD ["bash", "-lc", "echo hoola-devlab ready; python3 -V; node -v"]
"""
DOCKERFILE = Path(__file__).resolve().parents[3] / "deploy" / "devlab" / "Dockerfile"

BASE_REV = "3"                # bump with any image change; lab_check compares it with what is built
CHECK_TIMEOUT = 600          # seconds a check may run (her setting may lower it)
SETUP_TIMEOUT = 1200         # ... and a one-time dependency install
MEM = "2g"
CPUS = "2"
PIDS = "512"
WORK = "/work"
SETUP_HOME = "/home/lab"     # the setup step writes here and docker commit keeps it
CHECK_HOME = "/tmp/home"     # a check writes here (inside the one tmpfs) so /home/lab stays visible, not masked
USER_BASE = "/home/lab/.local"   # `pip install --user` at setup time; found at check time through PYTHONUSERBASE


def _run(argv: list[str], timeout: int, cwd: str = "") -> tuple[int, str, float]:
    t0 = time.time()
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd or None,
                           env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp"),
                                "LANG": "C.UTF-8", "DOCKER_HOST": os.environ.get("DOCKER_HOST", "")})
        return r.returncode, (r.stdout or "") + (r.stderr or ""), time.time() - t0
    except subprocess.TimeoutExpired as e:
        got = (e.stdout or b"") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = (e.stderr or b"") if isinstance(e.stderr, bytes) else (e.stderr or "")
        txt = (got.decode("utf-8", "replace") if isinstance(got, bytes) else got) + \
              (err.decode("utf-8", "replace") if isinstance(err, bytes) else err)
        return 124, txt + f"\n[timed out after {timeout}s]", time.time() - t0
    except OSError as e:
        return 127, f"{argv[0]}: {e}", time.time() - t0


def docker() -> str:
    return shutil.which("docker") or ""


def available() -> dict[str, Any]:
    """Is the lab usable on this machine? Never raises: the answer is data, with the reason in her words."""
    d = docker()
    if not d:
        return {"ok": False, "why": "is machine par docker nahi hai (VPS par `docker --version` dekhiye)."}
    rc, txt, _ = _run([d, "version", "--format", "{{.Server.Version}}"], 25)
    if rc != 0:
        return {"ok": False, "why": "docker daemon jawab nahi de raha: " + txt.strip()[:300]}
    ver = txt.strip().splitlines()[-1][:40] if txt.strip() else "?"
    rc2, imgs, _ = _run([d, "images", "-q", BASE_IMAGE], 25)
    built = bool(imgs.strip())
    rev = base_rev() if built else ""
    stale = built and rev != BASE_REV
    why = ""
    if not built:
        why = "base image abhi bani nahi - `python -m app.devlab setup` chalaiye."
    elif stale:
        why = (f"base image purani hai (rev {rev or '1'}, chahiye {BASE_REV}) - `python -m app.devlab setup "
               "--rebuild` chalaiye, warna purane niyam chalte rahenge.")
    return {"ok": True, "docker": ver, "base_image": BASE_IMAGE, "base_built": built,
            "base_rev": rev, "base_rev_wanted": BASE_REV, "base_stale": stale, "why": why}


def base_rev() -> str:
    """Which revision of the image is actually built here? Read from the image's own label - no container needed."""
    d = docker()
    if not d:
        return ""
    rc, out_, _ = _run([d, "image", "inspect", BASE_IMAGE, "--format",
                        "{{index .Config.Labels \"hoola.devlab.rev\"}}"], 25)
    txt = (out_ or "").strip().splitlines()[-1].strip() if (out_ or "").strip() else ""
    return "" if rc != 0 or txt in ("<no value>", "<nil>") else txt[:12]


def build_base(nocache: bool = False) -> dict[str, Any]:
    """Build the one base image (python + node + jdk + git + ripgrep). Once per VPS, ~2-4 minutes. The Dockerfile is
    written from DOCKERFILE_TEXT into a temp folder, so a build works wherever the code runs from - the VPS has only
    `server/app`, not deploy/."""
    d = docker()
    if not d:
        return {"ok": False, "why": "docker nahi hai"}
    import tempfile
    with tempfile.TemporaryDirectory(prefix="hoola-devlab-build-") as tmp:
        f = Path(tmp) / "Dockerfile"
        f.write_text(DOCKERFILE_TEXT, "utf-8")
        argv = [d, "build", "-t", BASE_IMAGE, "-f", str(f)] + (["--no-cache"] if nocache else []) + [tmp]
        rc, txt, secs = _run(argv, 2400)
    return {"ok": rc == 0, "seconds": round(secs, 1), "out": txt[-4000:], "image": BASE_IMAGE,
            "why": "" if rc == 0 else "base image nahi bani (log dekhiye)"}


def _limits(network: bool, writable: bool = False) -> list[str]:
    """The walls. Nothing here is negotiable by the repo's own code.

    `writable` is true for the SETUP step alone, and only because a sealed step cannot leave anything behind: the
    dependency install has to land in the container's own filesystem for `docker commit` to keep it. v0.537 found
    that the hard way - the old walls gave setup a read-only root AND a tmpfs over /home/lab, and docker commit
    keeps neither, so an install that succeeded was thrown away and every later check failed on missing imports
    with the snapshot tag already cached. A CHECK keeps every wall: read-only root, no network, and a writable
    HOME inside /tmp instead of a tmpfs that would MASK the installed dependencies."""
    home = SETUP_HOME if writable else CHECK_HOME
    args = ["--rm", "--user", "1000:1000", "--workdir", WORK,
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--memory", MEM, "--memory-swap", MEM, "--cpus", CPUS, "--pids-limit", PIDS,
            "--tmpfs", "/tmp:rw,exec,size=1g",
            "--env", f"HOME={home}", "--env", f"PYTHONUSERBASE={USER_BASE}",
            "--env", f"PATH={USER_BASE}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "--env", "LANG=C.UTF-8", "--env", "CI=1",
            "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "HOOLA_LAB=1"]
    if not writable:
        args.insert(1, "--read-only")
    args += ["--network", "bridge"] if network else ["--network", "none"]
    return args


def run_in(image: str, files_dir: str, command: str, timeout: int = CHECK_TIMEOUT, network: bool = False,
           commit_to: str = "") -> dict[str, Any]:
    """Run ONE shell command on a copy of her files inside `image`.

    network=False (a check) means there is no route out at all. commit_to != "" keeps the container and commits it as
    an image afterwards (that is how a dependency snapshot is made) - only ever used by the setup step."""
    d = docker()
    if not d:
        return {"rc": 127, "out": "docker nahi hai", "secs": 0.0, "timed_out": False}
    name = f"hoola-lab-{os.getpid()}-{int(time.time() * 1000) % 1_000_000}"
    keep = bool(commit_to)
    # Writability is DERIVED from commit_to and cannot be asked for: the only reason to let a container keep what it
    # writes is that we are about to commit it. No caller can unseal a check by passing a flag.
    args = [d, "run", "--name", name] + [a for a in _limits(network, writable=keep) if not (keep and a == "--rm")]
    shell = f'mkdir -p "$HOME" 2>/dev/null || true; {command}'
    args += ["-v", f"{os.path.abspath(files_dir)}:{WORK}:rw", image, "bash", "-lc", shell]
    rc, txt, secs = _run(args, timeout + 30)
    timed_out = rc == 124 or f"[timed out after {timeout + 30}s]" in txt
    if timed_out:
        _run([d, "kill", name], 30)
    if keep:
        if rc == 0 and not timed_out:
            crc, cout, _ = _run([d, "commit", name, commit_to], 300)
            if crc != 0:
                txt += f"\n[snapshot nahi bani: {cout.strip()[:300]}]"
        _run([d, "rm", "-f", name], 60)
    return {"rc": 124 if timed_out else rc, "out": txt, "secs": secs, "timed_out": timed_out}


def has_image(tag: str) -> bool:
    d = docker()
    if not d:
        return False
    rc, out, _ = _run([d, "images", "-q", tag], 25)
    return rc == 0 and bool(out.strip())


def images(prefix: str = "hoola-devlab") -> list[dict[str, Any]]:
    d = docker()
    if not d:
        return []
    rc, out, _ = _run([d, "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"], 30)
    rows = []
    for line in (out or "").splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].startswith(prefix):
            rows.append({"image": parts[0], "size": parts[1], "at": parts[2][:19]})
    return rows


def forget(tag: str) -> bool:
    d = docker()
    return bool(d) and _run([d, "rmi", "-f", tag], 120)[0] == 0


def prune(keep: int = 12) -> list[str]:
    """Drop the oldest repo snapshots, newest `keep` kept (the base image is never dropped)."""
    rows = [r for r in images() if r["image"] != BASE_IMAGE]
    rows.sort(key=lambda r: r["at"], reverse=True)
    gone = []
    for r in rows[keep:]:
        if forget(r["image"]):
            gone.append(r["image"])
    return gone


# ---------------------------------------------------------------- Hoola Code Phase 4: a LIVE box for one session
# A check (above) is one container per command, thrown away. A coding session needs the opposite: ONE box that stays
# for the life of the session, so files, a build's output and a background command are still there on the next
# message. The walls are the same ones - no network, no capabilities, non-root, read-only root, memory / CPU / pids
# caps - and they come from the same `_limits()`, so a live box can never be given more than a check gets. The
# session's time limit is per COMMAND (`timeout` inside the box, so the process itself is killed, not only our
# docker client). How many live boxes may exist at once is the caller's rule (devsahayak/wsp.py), not this file's.
LIVE_PREFIX = "hoola-ws-"
BG_DIR = "/tmp/hoola-bg"


def live_name(key: str) -> str:
    import re as _re
    return LIVE_PREFIX + (_re.sub(r"[^a-z0-9_-]", "", str(key or "").lower())[:40] or "x")


def _env_flags(env: dict[str, str] | None) -> list[str]:
    flags: list[str] = []
    for k, v in (env or {}).items():
        flags += ["--env", f"{k}={v}"]
    return flags


def start_live(name: str, image: str, files_dir: str, mem: str = "") -> dict[str, Any]:
    """Start the session's box: the checkout mounted at /work, nothing running in it but `sleep`. A box that already
    has this name is replaced (it is the same session coming back)."""
    d = docker()
    if not d:
        return {"ok": False, "why": "docker is not installed on this machine"}
    _run([d, "rm", "-f", name], 60)
    lim = _limits(False)
    if mem:
        for flag in ("--memory", "--memory-swap"):
            lim[lim.index(flag) + 1] = mem
    args = [d, "run", "-d", "--name", name, "--init", "--label", "hoola.ws=1"] + lim
    args += ["-v", f"{os.path.abspath(files_dir)}:{WORK}:rw", image, "sleep", "infinity"]
    rc, txt, secs = _run(args, 120)
    return {"ok": rc == 0, "name": name, "seconds": round(secs, 1),
            "why": "" if rc == 0 else "the box did not start: " + txt.strip()[-300:]}


def live_alive(name: str) -> bool:
    d = docker()
    if not d:
        return False
    rc, out_, _ = _run([d, "inspect", "-f", "{{.State.Running}}", name], 20)
    return rc == 0 and out_.strip().endswith("true")


def exec_live(name: str, command: str, timeout: int = 300, env: dict[str, str] | None = None) -> dict[str, Any]:
    """One command in the session's box, from the repo root. `timeout` runs INSIDE the box, so the command and its
    children are killed there when the time is up."""
    d = docker()
    if not d:
        return {"rc": 127, "out": "docker is not installed", "secs": 0.0, "timed_out": False}
    # umask 0: what a command creates stays writable for the server too, whatever user the server runs as
    shell = f'mkdir -p "$HOME" 2>/dev/null || true; umask 0000; cd {WORK}; {command}'
    args = [d, "exec", "--user", "1000:1000", "--workdir", WORK] + _env_flags(env)
    args += [name, "timeout", "-k", "5", str(int(timeout)), "bash", "-lc", shell]
    rc, txt, secs = _run(args, int(timeout) + 30)
    timed_out = rc in (124, 137) and secs >= timeout - 1
    return {"rc": 124 if timed_out else rc, "out": txt, "secs": secs, "timed_out": timed_out}


def bg_start(name: str, slot: str, command: str, limit: int = 900, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Start a command that keeps running after this call (a dev server, a watcher). It has its own time limit; its
    output goes to a file inside the box that `bg_read` shows."""
    import shlex
    d = docker()
    if not d:
        return {"ok": False, "why": "docker is not installed"}
    inner = (f"mkdir -p {BG_DIR}; umask 0000; cd {WORK}; rm -f {BG_DIR}/{slot}.rc; "
             f"(timeout -k 5 {int(limit)} bash -lc {shlex.quote(command)} > {BG_DIR}/{slot}.log 2>&1 & "
             f"echo $! > {BG_DIR}/{slot}.pid; wait $!; echo $? > {BG_DIR}/{slot}.rc)")
    args = [d, "exec", "-d", "--user", "1000:1000", "--workdir", WORK] + _env_flags(env) + [name, "bash", "-lc", inner]
    rc, txt, _ = _run(args, 60)
    return {"ok": rc == 0, "why": "" if rc == 0 else txt.strip()[-300:]}


def bg_read(name: str, slot: str, tail: int = 6000) -> dict[str, Any]:
    d = docker()
    if not d:
        return {"running": False, "rc": None, "out": ""}
    cmd = (f"if [ -f {BG_DIR}/{slot}.rc ]; then echo \"RC=$(cat {BG_DIR}/{slot}.rc)\"; else echo RC=; fi; "
           f"tail -c {int(tail)} {BG_DIR}/{slot}.log 2>/dev/null")
    rc, txt, _ = _run([d, "exec", "--user", "1000:1000", name, "bash", "-lc", cmd], 30)
    head, _, body = (txt or "").partition("\n")
    code = head.removeprefix("RC=").strip()
    done = bool(code) or rc != 0
    return {"running": not done, "rc": int(code) if code.lstrip("-").isdigit() else None, "out": body}


def bg_stop(name: str, slot: str) -> bool:
    d = docker()
    if not d:
        return False
    cmd = f"kill -TERM $(cat {BG_DIR}/{slot}.pid 2>/dev/null) 2>/dev/null; true"
    return _run([d, "exec", "--user", "1000:1000", name, "bash", "-lc", cmd], 30)[0] == 0


def stop_live(name: str, files_dir: str = "") -> bool:
    """End the session's box. The files it made are opened up first (they belong to uid 1000), so the server can
    remove the folder whatever user it runs as."""
    d = docker()
    if not d:
        return False
    if live_alive(name):
        _run([d, "exec", "--user", "1000:1000", name, "bash", "-lc", f"chmod -R a+rwX {WORK} 2>/dev/null; true"], 60)
    return _run([d, "rm", "-f", name], 60)[0] == 0


def live_boxes() -> list[str]:
    d = docker()
    if not d:
        return []
    rc, out_, _ = _run([d, "ps", "--filter", "label=hoola.ws=1", "--format", "{{.Names}}"], 30)
    return [x.strip() for x in (out_ or "").splitlines() if x.strip()] if rc == 0 else []
