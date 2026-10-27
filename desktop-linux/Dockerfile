# Hoola PC: the Linux cloud computer that belongs to Hoola (per-user coworker VM).
# Runs on the same VPS as the Hoola server (Phase 1), pairs over the normal PC bridge.
FROM python:3.12-slim

RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        xvfb scrot xdotool wmctrl openbox dbus-x11 x11-utils chromium fonts-indic fonts-noto-core \
        procps curl ca-certificates gnupg \
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

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py .
COPY start.sh /start.sh
RUN chmod +x /start.sh

ENV DISPLAY=:1
# /data holds: identity.json (pairing), chrome/ (profile - logged-in sessions survive),
# Downloads/, installed.log. A volume keeps all of it across restarts.
VOLUME ["/data"]

# ~150 MB idle (Xvfb + openbox + agent), ~0.7-1.0 GB with Chromium on a heavy page.
STOPSIGNAL SIGTERM
CMD ["/start.sh"]
