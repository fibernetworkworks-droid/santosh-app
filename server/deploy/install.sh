#!/usr/bin/env bash
# Santosh Core: one-command install for an Ubuntu VPS (run as your normal user, e.g. `fnw`, NOT root).
#
#   unzip santosh-v0.2.zip && cd santosh-core && bash deploy/install.sh
#
# Does: copies the app to ~/apps/santosh-core, creates a Python venv, writes .env with a fresh API key,
# starts Santosh on 127.0.0.1:8077 under PM2 (or nohup), and prints the Caddy block for https.
# It never touches other apps, Docker containers or your Caddyfile.
set -euo pipefail

APP_DIR="${SANTOSH_DIR:-$HOME/apps/santosh-core}"
PORT="${SANTOSH_PORT:-8077}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
say() { printf "\n\033[1;35m▸ %s\033[0m\n" "$*"; }
die() { printf "\n\033[1;31m✗ %s\033[0m\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] && die "Run this as your normal user (e.g. fnw), not root."
command -v python3 >/dev/null || die "python3 is missing: sudo apt install -y python3 python3-venv"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || die "Python 3.10+ needed"
python3 -c 'import venv, ensurepip' 2>/dev/null || die "python3-venv is missing: sudo apt install -y python3-venv"

if command -v ss >/dev/null && ss -ltn "( sport = :$PORT )" | grep -q LISTEN; then
  if ! curl -fsS "http://127.0.0.1:$PORT/healthz" 2>/dev/null | grep -q dry_run; then
    die "Port $PORT is used by another app. Run again with SANTOSH_PORT=8078 bash deploy/install.sh"
  fi
fi

say "Copying Santosh to $APP_DIR"
mkdir -p "$APP_DIR"
if [ "$SRC" != "$APP_DIR" ]; then
  # keep an existing .env and database on upgrades
  tar -C "$SRC" --exclude='.env' --exclude='*.db*' --exclude='.venv' --exclude='__pycache__' -cf - . | tar -C "$APP_DIR" -xf -
fi
cd "$APP_DIR"

say "Installing Python packages (first time takes a minute)"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

if [ ! -f .env ]; then
  say "Creating .env"
  KEY="${ANTHROPIC_API_KEY:-}"
  if [ -z "$KEY" ] && [ -t 0 ]; then
    read -r -s -p "Paste your Claude API key (sk-ant-…), or press Enter to add it later: " KEY; echo
  fi
  API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  VERIFY="$(python3 -c 'import secrets; print(secrets.token_hex(12))')"
  sed -e "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=${KEY}|" \
      -e "s|^API_KEY=.*|API_KEY=${API_KEY}|" \
      -e "s|^WA_VERIFY_TOKEN=.*|WA_VERIFY_TOKEN=${VERIFY}|" \
      -e "s|^DATABASE_URL=.*|DATABASE_URL=sqlite:///${APP_DIR}/santosh.db|" \
      .env.example > .env
  chmod 600 .env
else
  say "Keeping your existing .env"
fi

say "Running the tests"
.venv/bin/python -m pytest -q 2>&1 | tail -1

say "Starting Santosh on 127.0.0.1:$PORT"
CMD="$APP_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $PORT --proxy-headers"
if command -v pm2 >/dev/null; then
  pm2 delete santosh >/dev/null 2>&1 || true
  pm2 start "$APP_DIR/.venv/bin/python" --name santosh --cwd "$APP_DIR" --interpreter none \
    -- -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --proxy-headers >/dev/null
  pm2 save >/dev/null
  echo "Running under PM2 as 'santosh' (logs: pm2 logs santosh)."
else
  pkill -f "uvicorn app.main:app --host 127.0.0.1 --port $PORT" 2>/dev/null || true
  nohup $CMD > "$APP_DIR/santosh.log" 2>&1 &
  echo "PM2 not found; started with nohup (logs: $APP_DIR/santosh.log). For restarts after reboot, install PM2 or use deploy/santosh.service."
fi

for i in $(seq 1 20); do
  if curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then break; fi
  sleep 1
done
HEALTH="$(curl -fsS "http://127.0.0.1:$PORT/healthz" 2>/dev/null)" || die "Santosh did not start. Check the logs above."
echo "Health: $HEALTH"

IP="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"
HOST="santosh.${IP//./-}.sslip.io"
API_KEY_NOW="$(grep '^API_KEY=' .env | cut -d= -f2-)"

cat <<EOF

────────────────────────────────────────────────────────────────
 Santosh is running on this server (127.0.0.1:$PORT).

 1) Give it an https address. Add this block to your Caddyfile
    (it does not change your existing sites), then reload Caddy:

      $HOST {
          reverse_proxy 127.0.0.1:$PORT
      }

    Using your own domain instead? Point an A record (e.g. santosh.ainewtika.com)
    to $IP and use that name in place of $HOST.
    Reload:  sudo caddy reload --config /etc/caddy/Caddyfile
    (If Caddy runs in Docker, add the block to that Caddyfile and reload the container,
     using host.docker.internal:$PORT or the host IP instead of 127.0.0.1.)

 2) Open  https://$HOST/?key=$API_KEY_NOW
    to chat with Santosh in the browser.

 3) In the Android app use:
      Server:  https://$HOST
      API key: $API_KEY_NOW

 Settings live in $APP_DIR/.env (Claude key, WhatsApp, limits).
 After editing it:  pm2 restart santosh
────────────────────────────────────────────────────────────────
EOF
