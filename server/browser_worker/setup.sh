#!/usr/bin/env bash
# One-time setup of Santosh Browser on the VPS. Run from anywhere:  bash ~/santosh_app/server/browser_worker/setup.sh
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/apps/santosh-browser"
mkdir -p "$DEST"
cp "$SRC"/worker.py "$SRC"/guard.py "$SRC"/netguard.py "$SRC"/display.py "$SRC"/requirements.txt "$SRC"/run.sh "$DEST"/
cd "$DEST"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m playwright install chromium
if [ ! -f .env ]; then
  KEY=$(.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))")
  printf "WORKER_KEY=%s\nMAX_SESSIONS=2\nIDLE_SECONDS=600\n" "$KEY" > .env
  chmod 600 .env
fi
echo "OK. Worker key (put it in ~/apps/santosh-core/.env as BROWSER_WORKER_KEY):"
grep WORKER_KEY .env | cut -d= -f2
