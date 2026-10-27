#!/bin/sh
# Hoola PC container boot: virtual screen -> window manager -> dbus -> the agent.
set -e
export DISPLAY=:1
Xvfb :1 -screen 0 1280x800x24 -nolisten tcp &
i=0
until xdpyinfo -display :1 >/dev/null 2>&1; do
  i=$((i+1)); [ "$i" -gt 50 ] && { echo "Xvfb did not start" >&2; exit 1; }
  sleep 0.2
done
openbox &
dbus-launch --exit-with-session true 2>/dev/null || true
mkdir -p /data/Downloads /data/chrome
exec python /app/agent.py
