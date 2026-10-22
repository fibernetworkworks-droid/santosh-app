#!/usr/bin/env bash
# Hoola Website Sahayak: what the VPS needs to build, check and preview websites.
#   Chromium (Playwright) for the checks + screenshots, ffmpeg for the scroll video, Lighthouse (optional, real scores)
#   and axe-core (optional, accessibility rules). Without the optional ones Hoola uses its own lab checks.
# Usage: bash ~/santosh_app/server/deploy/setup_sites.sh [core dir, default ~/apps/santosh-core]
set -euo pipefail
CORE="${1:-$HOME/apps/santosh-core}"
PY="$CORE/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
TOOLS="$CORE/data/site_tools"
mkdir -p "$TOOLS"

echo "== system packages (ffmpeg, fonts)"
sudo apt-get update -y
sudo apt-get install -y ffmpeg fonts-noto-core fonts-noto-color-emoji

echo "== Python packages"
"$PY" -m pip install --quiet "playwright>=1.47" "beautifulsoup4>=4.12" "pillow>=11.2"

echo "== Chromium"
sudo "$PY" -m playwright install-deps chromium || true
"$PY" -m playwright install chromium

echo "== Node + Lighthouse (optional: real Lighthouse scores)"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs || echo "node not installed (Hoola lab scores will be used)"
fi
if command -v npm >/dev/null 2>&1; then
  sudo npm install -g lighthouse@12 || echo "lighthouse not installed (Hoola lab scores will be used)"
  ( cd "$TOOLS" && npm pack axe-core@4 --silent >/dev/null && tar -xzf axe-core-*.tgz package/axe.min.js && mv package/axe.min.js . && rm -rf package axe-core-*.tgz ) \
    || echo "axe-core not fetched (Hoola's own accessibility checks will be used)"
fi

echo "== quick check"
cd "$CORE"
"$PY" - <<'PYEOF'
import shutil, sys
sys.path.insert(0, "")
from app.site import checks, library
print("library:", library.counts())
print("chromium:", checks.available() or "ok")
print("lighthouse:", shutil.which("lighthouse") or "not installed (Hoola lab scores)")
print("axe:", checks._vendor("axe.min.js") or "not installed (Hoola checks)")
print("ffmpeg:", shutil.which("ffmpeg") or "missing (no scroll video)")
PYEOF
echo "Done. Set PUBLIC_BASE_URL in .env (preview links + site forms), then: pm2 restart santosh --update-env"
