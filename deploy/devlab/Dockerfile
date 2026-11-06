# v0.456 PRAYOGSHALA (the coding lab) - the base image every check runs in.
# Built ONCE on the VPS by `python -m app.devlab setup`; per-repo dependency snapshots are committed on top of it.
# Rules this image obeys (docs/CODING_HARNESS_PLAN.md 1.4): no secret ever enters it, it runs as a non-root user,
# and a CHECK runs with --network none (only the one-time SETUP step gets the network, the way Codex does it).
FROM debian:12-slim

# v0.537: the walls and this image are one thing - bump BASE_REV whenever the image must be rebuilt, and
# `lab_check` can then tell her that the image on her VPS is older than the code reading it.
LABEL hoola.devlab.rev="2"

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 NODE_OPTIONS=--max-old-space-size=1536 HOME=/home/lab

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git make gcc g++ pkg-config \
      python3 python3-venv python3-pip python3-dev \
      nodejs npm \
      openjdk-17-jdk-headless \
      sqlite3 ripgrep jq unzip \
 && rm -rf /var/lib/apt/lists/*

# v0.537: Debian marks its Python "externally managed" (PEP 668), so a repo's own declared
# `pip install -r requirements.txt` dies with error: externally-managed-environment - which is exactly what
# her first live lab_try hit. A container IS the virtual environment, so the marker comes off here, once, and
# every repo's real command works without Hoola rewriting it.
RUN rm -f /usr/lib/python3*/EXTERNALLY-MANAGED

# pytest / ruff for Python repos that declare no dev dependencies of their own
RUN python3 -m pip install --no-cache-dir pytest pytest-timeout ruff

RUN useradd -m -u 1000 -s /bin/bash lab \
 && mkdir -p /work /home/lab/.local/bin \
 && chown -R lab:lab /work /home/lab
USER lab
WORKDIR /work
CMD ["bash", "-lc", "echo hoola-devlab ready; python3 -V; node -v"]
