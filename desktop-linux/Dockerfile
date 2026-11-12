# Hoola PC: the Linux cloud computer that belongs to Hoola (per-user coworker VM).
# Runs on the same VPS as the Hoola server (Phase 1), pairs over the normal PC bridge.
FROM python:3.12-slim

RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        xvfb scrot xdotool wmctrl openbox dbus-x11 x11-utils chromium fonts-indic fonts-noto-core \
        procps curl ca-certificates gnupg at-spi2-core libatk-adaptor \
    && rm -rf /var/lib/apt/lists/*

# v1.2.0 Google Chrome stable (the real thing: H.264/AAC/MP3 codecs + Widevine, the exact
# build every website is tested against). Debian's chromium stays installed as the fallback
# (and for non-amd64 arches - Google ships Chrome for amd64 only). The agent prefers
# google-chrome and falls back to chromium automatically, so this layer failing to matter
# is impossible to miss: check `which google-chrome` in the deploy log.
RUN ARCH=$(dpkg --print-architecture) \
    && if [ "$ARCH" = "amd64" ]; then \
         curl -fsSL -o /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
         && DEBIAN_FRONTEND=noninteractive apt-get update -qq \
         && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends /tmp/chrome.deb \
         && rm -rf /var/lib/apt/lists/* /tmp/chrome.deb \
         && which google-chrome; \
       else echo "arch $ARCH: google-chrome not available, agent will use chromium"; fi

# v0.842 EXACT MODE on Hoola's own PC: vercel-labs/agent-desktop v1.2.0 (Apache-2.0) reads Linux apps through
# AT-SPI the way it reads Windows apps through UIA, so the SAME ax_* tools work here. Official release archive,
# checksum-verified at build time (a mismatch fails the build), plus its clipboard helper.
ARG AGENT_DESKTOP=1.2.0
RUN ARCH=$(dpkg --print-architecture) \
    && case "$ARCH" in amd64) T=x86_64-unknown-linux-gnu ;; arm64) T=aarch64-unknown-linux-gnu ;; *) T="" ;; esac \
    && if [ -n "$T" ]; then \
         A=agent-desktop-v${AGENT_DESKTOP}-$T.tar.gz \
         && curl -fsSL -o /tmp/$A https://github.com/vercel-labs/agent-desktop/releases/download/v${AGENT_DESKTOP}/$A \
         && curl -fsSL -o /tmp/sums https://github.com/vercel-labs/agent-desktop/releases/download/v${AGENT_DESKTOP}/checksums.txt \
         && cd /tmp && grep " $A\$" sums | sha256sum -c - \
         && tar xzf /tmp/$A -C /usr/local/bin && rm -f /tmp/$A /tmp/sums \
         && /usr/local/bin/agent-desktop version; \
       else echo "arch $ARCH: no agent-desktop build, exact mode off (pixel mode still works)"; fi
ENV HOOLA_AGENT_DESKTOP=/usr/local/bin/agent-desktop

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py axtree.py ./
COPY start.sh /start.sh
RUN chmod +x /start.sh

ENV DISPLAY=:1
# /data holds: identity.json (pairing), chrome/ (profile - logged-in sessions survive),
# Downloads/, installed.log. A volume keeps all of it across restarts.
VOLUME ["/data"]

# ~150 MB idle (Xvfb + openbox + agent), ~0.7-1.0 GB with Chromium on a heavy page.
STOPSIGNAL SIGTERM
CMD ["/start.sh"]
