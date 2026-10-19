#!/usr/bin/env bash
# pm2 entry: loads .env and starts the worker on 127.0.0.1:8079 (never exposed to the internet)
cd "$(dirname "$0")"
set -a; . ./.env; set +a
exec .venv/bin/python -m uvicorn worker:app --host 127.0.0.1 --port "${PORT:-8079}" --workers 1
