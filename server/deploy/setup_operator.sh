#!/usr/bin/env bash
# Hoola Computer Operator: Playwright inside santosh-core's own venv (one browser per owner while a job runs, ~300 MB
# each; OPERATOR_MAX_JOBS caps them). Her logins are kept in ~/apps/santosh-core/data/operator/<owner>/profiles.
# v0.74: Google Chrome + a virtual screen (Xvfb), so the operator is a real browser window and not "HeadlessChrome"
# (many Indian portals and banks refuse headless browsers outright).
set -euo pipefail
VENV=~/apps/santosh-core/.venv
$VENV/bin/pip install -q "playwright>=1.48"
sudo apt-get update -qq && sudo apt-get install -y -qq xvfb fonts-noto fonts-noto-color-emoji >/dev/null
sudo $VENV/bin/python -m playwright install-deps chromium
$VENV/bin/python -m playwright install chromium
# Google Chrome stable (amd64 only); if it can't be installed the operator uses Chromium in a real window.
if [ "$(dpkg --print-architecture)" = "amd64" ]; then
  sudo $VENV/bin/python -m playwright install chrome || echo "Google Chrome not installed: Chromium will be used."
fi
chmod 700 ~/apps/santosh-core/data 2>/dev/null || true
echo "OK: Computer Operator ready. Restart: pm2 restart santosh --update-env"
echo "Check: cd ~/apps/santosh-core && .venv/bin/python -m app.operator.check https://www.incometax.gov.in/"
