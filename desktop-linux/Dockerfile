# Hoola PC: the Linux cloud computer that belongs to Hoola (per-user coworker VM).
# Runs on the same VPS as the Hoola server (Phase 1), pairs over the normal PC bridge.
FROM python:3.12-slim

RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        xvfb scrot xdotool wmctrl openbox dbus-x11 x11-utils chromium fonts-indic fonts-noto-core \
        procps curl ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*

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
