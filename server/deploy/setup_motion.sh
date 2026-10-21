#!/usr/bin/env bash
# Hoola Motion: what the VPS needs to render animated reels to MP4.
#   headless Chromium (Playwright), ffmpeg, colour emoji + Indian-script fonts.
# Usage: bash ~/santosh_app/server/deploy/setup_motion.sh [core dir, default ~/apps/santosh-core]
set -euo pipefail
CORE="${1:-$HOME/apps/santosh-core}"
PY="$CORE/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

echo "== system packages (ffmpeg, emoji + Noto fonts)"
sudo apt-get update -y
sudo apt-get install -y ffmpeg fonts-noto-color-emoji fonts-noto-core

echo "== Playwright + Chromium"
"$PY" -m pip install --quiet "playwright>=1.47"
sudo "$PY" -m playwright install-deps chromium || true
"$PY" -m playwright install chromium

echo "== quick check"
cd "$CORE"
"$PY" - <<'PYEOF'
import sys
sys.path.insert(0, "")
try:
    from app.motion import render
    print("missing:", render.available() or "nothing - Hoola Motion is ready")
except Exception as e:
    print("check skipped:", e)
PYEOF
echo "Done. Now: pm2 restart santosh --update-env"
