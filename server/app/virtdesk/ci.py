"""A GitHub Actions workflow she adds to her own repository: it builds her image and runs it the hardened way (non-root user,
read-only root, every capability dropped, no-new-privileges, her seccomp profile, memory / CPU / process limits), then checks it
is still running and answers its health check. A second job can run it once with the profile in log mode so the kernel log names
every syscall the profile would refuse. Text only: Hoola does not push it."""
from __future__ import annotations

import re
from typing import Any


class CiError(ValueError):
    pass


_IMG = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,200}(:[\w.-]{1,128})?(@sha256:[a-f0-9]{64})?$")
_PATH = re.compile(r"^(?!/)(?!.*\.\.)[\w./-]{1,200}$")
_CMD = re.compile(r"^[\w ./:=@%+,-]{1,200}$")
_MEM = re.compile(r"^\d{1,6}[kmg]$", re.I)


def workflow(image: str = "", dockerfile: str = "Dockerfile", context: str = ".", seccomp_file: str = "", uid: int = 10001, port: int = 0,
             health: str = "", memory: str = "512m", pids: int = 256, cpus: str = "1", net_bind: bool = False, log_job: bool = True) -> dict[str, Any]:
    image, dockerfile, context, seccomp_file, health = (str(x or "").strip() for x in (image, dockerfile, context, seccomp_file, health))
    if image and not _IMG.match(image):
        raise CiError("Image: a name like ghcr.io/me/app:1.4 (lower case).")
    for v, what in ((dockerfile, "Dockerfile path"), (context or ".", "Build folder")):
        if not _PATH.match(v):
            raise CiError(f"{what}: a path inside the repository, like Dockerfile or docker/app.Dockerfile.")
    if seccomp_file and not _PATH.match(seccomp_file):
        raise CiError("Seccomp profile path: a file inside the repository, like security/seccomp.json.")
    try:
        uid, port, pids = int(uid), int(port or 0), int(pids)
    except (TypeError, ValueError):
        raise CiError("User id, port and process limit are whole numbers.")
    if not 1 <= uid <= 2 ** 31:
        raise CiError("User id: 1 or more (not 0, that is root).")
    if not 0 <= port <= 65535:
        raise CiError("Port: 1 to 65535, or 0 for none.")
    if not 16 <= pids <= 100000:
        raise CiError("Process limit: 16 to 100,000.")
    if not _MEM.match(str(memory)):
        raise CiError("Memory: like 512m or 2g.")
    if not re.match(r"^\d+(\.\d+)?$", str(cpus)):
        raise CiError("CPUs: a number like 1 or 0.5.")
    hurl = hcmd = ""
    if health:
        if re.match(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?/[\w./?=&%-]*$", health):
            hurl = health
            if not port:
                raise CiError("A health URL needs the port the container listens on.")
        elif _CMD.match(health):
            hcmd = health
        else:
            raise CiError("Health check: a URL on 127.0.0.1 (like http://127.0.0.1:8080/health) or a command run inside the container.")
    tag = "hoola-check:${{ github.sha }}"
    src = image or tag
    flags = [f"--user {uid}:{uid}", "--read-only", "--tmpfs /tmp:rw,noexec,nosuid,size=64m", "--cap-drop ALL"]
    if net_bind:
        flags.append("--cap-add NET_BIND_SERVICE")
    flags += ["--security-opt no-new-privileges"]
    if seccomp_file:
        flags.append(f"--security-opt seccomp={seccomp_file}")
    flags += [f"--pids-limit {pids}", f"--memory {memory}", f"--cpus {cpus}"]
    if port:
        flags.append(f"-p 127.0.0.1:{port}:{port}")
    run_lines = " \\\n            ".join(["docker run -d --name app"] + flags + [src])
    build = (f"""      - name: Pull the image
        run: docker pull {image}
""" if image else f"""      - name: Build the image
        run: docker build -t {tag} -f {dockerfile} {context or '.'}
""")
    probe = (f'curl -fsS --max-time 3 {hurl} >/dev/null && echo "Healthy" && exit 0' if hurl else
             f'docker exec app {hcmd} && echo "Healthy" && exit 0' if hcmd else
             '[ "$i" -ge 10 ] && echo "Still running after 20 s" && exit 0')
    check = f"""      - name: Check it keeps running
        run: |
          for i in $(seq 1 30); do
            if [ "$(docker inspect -f '{{{{.State.Running}}}}' app)" != "true" ]; then
              echo "The container stopped (exit code $(docker inspect -f '{{{{.State.ExitCode}}}}' app))"; docker logs app; exit 1
            fi
            {probe} || true
            sleep 2
          done
          echo "No healthy answer in 60 s"; docker logs app; exit 1
      - name: Logs
        if: always()
        run: docker logs app 2>&1 | tail -200 || true
"""
    y = f"""# Made on the Hoola Virtualization desk. Runs the container the hardened way on every pull request.
name: Hardened container check
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  hardened-run:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
{build}      - name: Run it hardened
        run: |
          {run_lines}
{check}"""
    if seccomp_file and log_job:
        y += f"""
  seccomp-log:
    # the same run with the profile in log mode: nothing is refused, the kernel log names what would be
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
{build}      - name: The profile in log mode
        run: jq '.defaultAction = "SCMP_ACT_LOG"' {seccomp_file} > /tmp/seccomp-log.json
      - name: Run it
        run: |
          {run_lines.replace(f"seccomp={seccomp_file}", "seccomp=/tmp/seccomp-log.json")}
{check}      - name: Syscalls the profile would refuse
        if: always()
        run: sudo dmesg | grep -E 'type=1326|SECCOMP' | grep -o 'syscall=[0-9]*' | sort | uniq -c | sort -rn | head -50 || echo "None logged"
"""
    return {"yaml": y, "file": ".github/workflows/hardened-container.yml", "flags": flags,
            "note": ("Add it to your repository yourself; Hoola does not push it. It needs a Linux runner with Docker (GitHub's ubuntu runners have it). "
                     "The log job lists syscall numbers: paste them into the Seccomp tab (audit lines) to see their names. If the runner's kernel log "
                     "shows nothing, run the same thing on a machine of yours.")}
