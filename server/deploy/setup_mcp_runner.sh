#!/usr/bin/env bash
# Hoola MCP Runner (v0.154): run on a SEPARATE Ubuntu 22.04 / 24.04 machine (never the Hoola VPS).
#   sudo bash setup_mcp_runner.sh mcp-run.example.com           (a DNS A record for that name must point here)
# Prints MCP_RUNNER_URL / MCP_RUNNER_SECRET to put into the Hoola VPS .env.
set -euo pipefail
DOMAIN="${1:?usage: setup_mcp_runner.sh <domain>}"
HOME_DIR=/srv/hoola-mcp
NET=hoola-mcp
HERE="$(cd "$(dirname "$0")/.." && pwd)"

apt-get update -y
apt-get install -y ca-certificates curl nginx certbot python3-certbot-nginx iptables-persistent python3
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

id hoola-mcp >/dev/null 2>&1 || useradd --system --home "$HOME_DIR" --shell /usr/sbin/nologin hoola-mcp
usermod -aG docker hoola-mcp
mkdir -p "$HOME_DIR"
install -m 0644 "$HERE/mcp_runner/runner.py" "$HOME_DIR/runner.py"
chown -R hoola-mcp:hoola-mcp "$HOME_DIR"

# 1. a bridge network for the servers; it may reach only the PUBLIC internet (no LAN, no cloud metadata, not this host)
docker network inspect "$NET" >/dev/null 2>&1 || \
  docker network create --driver bridge --opt com.docker.network.bridge.name=br-hoolamcp \
    --opt com.docker.network.bridge.enable_icc=false "$NET"
for cidr in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 100.64.0.0/10 169.254.0.0/16 127.0.0.0/8 0.0.0.0/8 \
            198.18.0.0/15 224.0.0.0/4 240.0.0.0/4; do
  iptables -C DOCKER-USER -i br-hoolamcp -d "$cidr" -j DROP 2>/dev/null || \
    iptables -I DOCKER-USER -i br-hoolamcp -d "$cidr" -j DROP
done
# DNS goes to Docker's resolver, which forwards upstream; allow replies for established connections first
iptables -C DOCKER-USER -i br-hoolamcp -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || \
  iptables -I DOCKER-USER -i br-hoolamcp -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
# the containers can't open connections to this machine itself (the runner, sshd, nginx)
iptables -C INPUT -i br-hoolamcp -m conntrack --ctstate NEW -j DROP 2>/dev/null || \
  iptables -I INPUT -i br-hoolamcp -m conntrack --ctstate NEW -j DROP
iptables -C INPUT -i br-hoolamcp -p udp --dport 53 -j ACCEPT 2>/dev/null || \
  iptables -I INPUT -i br-hoolamcp -p udp --dport 53 -j ACCEPT
netfilter-persistent save || true

# 2. the images servers run in (pulled once; the runner never builds images)
docker pull node:22-bookworm-slim
docker pull ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 3. secret + service
ENVF=/etc/hoola-mcp-runner.env
if [ ! -f "$ENVF" ]; then
  echo "HOOLA_RUNNER_SECRET=$(python3 -c 'import secrets;print(secrets.token_urlsafe(40))')" > "$ENVF"
  echo "HOOLA_RUNNER_NETWORK=$NET" >> "$ENVF"
  chmod 0600 "$ENVF"
fi
cat > /etc/systemd/system/hoola-mcp-runner.service <<EOF
[Unit]
Description=Hoola MCP runner
After=docker.service network-online.target
Requires=docker.service

[Service]
User=hoola-mcp
EnvironmentFile=$ENVF
ExecStart=/usr/bin/python3 $HOME_DIR/runner.py --port 8091 --host 127.0.0.1
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$HOME_DIR
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now hoola-mcp-runner
# containers left over from an earlier run (the runner keeps nothing on disk)
docker ps -aq --filter label=hoola-mcp=1 | xargs -r docker rm -f

# 4. nginx + TLS
cat > /etc/nginx/sites-available/hoola-mcp <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    client_max_body_size 5m;
    location / {
        proxy_pass http://127.0.0.1:8091;
        proxy_set_header Host \$host;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }
}
EOF
ln -sf /etc/nginx/sites-available/hoola-mcp /etc/nginx/sites-enabled/hoola-mcp
nginx -t && systemctl reload nginx
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect || \
  echo "certbot failed: check the DNS record for $DOMAIN, then run: certbot --nginx -d $DOMAIN"

echo
echo "Done. On the Hoola VPS add to ~/apps/santosh-core/.env and restart (pm2 restart santosh --update-env):"
echo "MCP_RUNNER_URL=https://$DOMAIN"
grep HOOLA_RUNNER_SECRET "$ENVF" | sed 's/HOOLA_RUNNER_SECRET/MCP_RUNNER_SECRET/'
echo "Check: curl -s https://$DOMAIN/v1/health"
