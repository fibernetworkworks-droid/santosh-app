# v0.456 PRAYOGSHALA (the coding lab) - the base image every check runs in.
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
LABEL hoola.devlab.rev="4"

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

# v0.999 (rev 4) code intelligence, Hoola Code's LSP tool (Claude Code's): language servers for Python and JS / TS live
# in the image, so every repo gets go-to-definition, references and diagnostics with nothing installed. They run in the
# box like every command (a server reads and can run the repo's own config), never on the server.
# A failed download must never cost the box itself (every command needs it): the image builds without them, and
# the lsp tool then says plainly that no language server is installed.
RUN (npm install -g --no-fund --no-audit pyright@1 typescript@5 typescript-language-server@4 && npm cache clean --force) \
 || echo "hoola: language servers not installed (npm failed) - the box works without them"

RUN useradd -m -u 1000 -s /bin/bash lab \
 && mkdir -p /work /home/lab/.local/bin \
 && chown -R lab:lab /work /home/lab
USER lab
WORKDIR /work
CMD ["bash", "-lc", "echo hoola-devlab ready; python3 -V; node -v"]
