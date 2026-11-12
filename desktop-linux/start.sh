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
# v0.842 a real session bus for the whole container + the accessibility bus, so apps (Chromium included) show
# their buttons / fields to agent-desktop (exact mode). Any failure here only turns exact mode off.
eval "$(dbus-launch --sh-syntax 2>/dev/null)" || true
export DBUS_SESSION_BUS_ADDRESS NO_AT_BRIDGE=0
openbox &
/usr/libexec/at-spi-bus-launcher --launch-immediately >/dev/null 2>&1 &
sleep 0.5
/usr/libexec/at-spi2-registryd >/dev/null 2>&1 &
mkdir -p /data/Downloads /data/chrome
exec python /app/agent.py
