#!/usr/bin/env bash
# Hoola Code server helper — installer (v0.941). She runs ONE line on her server:
#   curl -fsSL <base>/vps/install | sudo bash -s <6-digit-code>
# It makes an unprivileged `hoola` user, installs the helper + the `hoola-agent` command, enrolls with her code, and
# starts a service. No inbound port is opened, no firewall rule changes, and the helper keeps no SSH key.
set -euo pipefail

BASE="__BASE__"
CODE="${1:-}"

if [ "$(id -u)" != "0" ]; then echo "Please run with sudo."; exit 1; fi
if ! printf '%s' "$CODE" | grep -Eq '^[0-9]{6}$'; then echo "Usage: sudo bash -s <6-digit code from the app>"; exit 1; fi
command -v python3 >/dev/null 2>&1 || { echo "python3 is needed (it is on nearly every server)."; exit 1; }

echo "Hoola helper: setting up…"

# 1) an unprivileged user with no login shell and no password
if ! id hoola >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin hoola
fi

# 2) the helper + the control command
install -d -m 755 /opt/hoola-agent
curl -fsSL "$BASE/vps/agent.py" -o /opt/hoola-agent/agent.py
chmod 755 /opt/hoola-agent/agent.py
install -d -m 700 -o hoola -g hoola /etc/hoola-agent

cat > /usr/local/bin/hoola-agent <<'CTL'
#!/usr/bin/env bash
# hoola-agent allow "<cmd>" | remove | status  — the only way to grant root to a command, or to remove the helper.
set -euo pipefail
case "${1:-}" in
  allow)
    [ -n "${2:-}" ] || { echo 'hoola-agent allow "<command>"'; exit 1; }
    install -d -m 750 /etc/sudoers.d
    LINE="hoola ALL=(root) NOPASSWD: $2"
    echo "$LINE" | EDITOR="tee -a" visudo -f /etc/sudoers.d/hoola-agent >/dev/null
    echo "Granted root for: $2"
    ;;
  remove)
    systemctl disable --now hoola-agent 2>/dev/null || true
    rm -f /etc/systemd/system/hoola-agent.service /usr/local/bin/hoola-agent
    rm -f /etc/sudoers.d/hoola-agent
    rm -rf /opt/hoola-agent /etc/hoola-agent
    systemctl daemon-reload 2>/dev/null || true
    userdel -r hoola 2>/dev/null || true
    [ "${2:-}" = "--quiet" ] || echo "Removed the Hoola helper and the hoola user."
    ;;
  status) systemctl status hoola-agent --no-pager || true ;;
  *) echo "hoola-agent allow \"<cmd>\" | remove | status" ;;
esac
CTL
chmod 755 /usr/local/bin/hoola-agent

# 3) enroll once with her code
if ! sudo -u hoola python3 /opt/hoola-agent/agent.py --enroll "$BASE" "$CODE"; then
  echo "Could not connect to Hoola. Make a fresh code in the app and try again."; exit 1
fi

# 4) a service that starts with the server, running as hoola
cat > /etc/systemd/system/hoola-agent.service <<UNIT
[Unit]
Description=Hoola Code server helper
After=network-online.target
Wants=network-online.target

[Service]
User=hoola
ExecStart=/usr/bin/python3 /opt/hoola-agent/agent.py
Restart=always
RestartSec=10
NoNewPrivileges=false
ProtectSystem=full
ProtectHome=read-only
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT
touch /var/log/hoola-agent.log && chown hoola:hoola /var/log/hoola-agent.log
systemctl daemon-reload
systemctl enable --now hoola-agent

echo "Done. Open the app — '$(hostname)' is connected."
