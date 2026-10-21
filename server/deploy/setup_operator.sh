#!/usr/bin/env bash
# v0.67 Hoola Computer Operator: Playwright + Chromium inside santosh-core's own venv (one browser per owner while a job
# runs, ~300 MB each; OPERATOR_MAX_JOBS caps them). Her logins are kept in ~/apps/santosh-core/data/operator/<owner>/profiles.
set -euo pipefail
VENV=~/apps/santosh-core/.venv
$VENV/bin/pip install -q "playwright>=1.48"
sudo $VENV/bin/python -m playwright install-deps chromium
$VENV/bin/python -m playwright install chromium
chmod 700 ~/apps/santosh-core/data 2>/dev/null || true
echo "OK: Computer Operator ready. Restart: pm2 restart santosh --update-env  (/healthz lists computer_operator)"
