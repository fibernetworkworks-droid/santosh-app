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
FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 NODE_OPTIONS=--max-old-space-size=1536 HOME=/home/lab

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git make gcc g++ pkg-config \
      python3 python3-venv python3-pip python3-dev \
      nodejs npm \
      openjdk-17-jdk-headless \
      sqlite3 ripgrep jq unzip \
 && rm -rf /var/lib/apt/lists/*

# pytest / ruff for Python repos that declare no dev dependencies of their own
RUN python3 -m pip install --break-system-packages --no-cache-dir pytest pytest-timeout ruff

RUN useradd -m -u 1000 -s /bin/bash lab && mkdir -p /work && chown lab:lab /work
USER lab
WORKDIR /work
CMD ["bash", "-lc", "echo hoola-devlab ready; python3 -V; node -v"]
"""
DOCKERFILE = Path(__file__).resolve().parents[3] / "deploy" / "devlab" / "Dockerfile"

CHECK_TIMEOUT = 600          # seconds a check may run (her setting may lower it)
SETUP_TIMEOUT = 1200         # ... and a one-time dependency install
MEM = "2g"
CPUS = "2"
PIDS = "512"
WORK = "/work"


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
    return {"ok": True, "docker": ver, "base_image": BASE_IMAGE, "base_built": bool(imgs.strip()),
            "why": "" if imgs.strip() else f"base image abhi bani nahi - `python -m app.devlab setup` chalaiye."}


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


def _limits(network: bool) -> list[str]:
    """The walls. Nothing here is negotiable by the repo's own code."""
    args = ["--rm", "--user", "1000:1000", "--workdir", WORK,
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--memory", MEM, "--memory-swap", MEM, "--cpus", CPUS, "--pids-limit", PIDS,
            "--read-only", "--tmpfs", "/tmp:rw,exec,size=1g", "--tmpfs", "/home/lab:rw,exec,size=512m",
            "--env", "HOME=/home/lab", "--env", "LANG=C.UTF-8", "--env", "CI=1",
            "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "HOOLA_LAB=1"]
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
    args = [d, "run", "--name", name] + [a for a in _limits(network) if not (keep and a == "--rm")]
    args += ["-v", f"{os.path.abspath(files_dir)}:{WORK}:rw", image, "bash", "-lc", command]
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
