#!/usr/bin/env bash
# Hoola 3D Studio (v0.141): the OFFICIAL Blender for the server, from download.blender.org (checksum checked) into
# /opt/blender. Runs headless (Cycles on CPU); every job runs in its own folder with no network and no secrets.
# Usage: bash ~/santosh_app/server/deploy/setup_blender.sh [version, default 5.2.3]
# Fallback when the download is blocked: the official `bpy` module from PyPI in its own venv (needs Python 3.13).
set -euo pipefail
VER="${1:-5.2.3}"
SERIES="${VER%.*}"
CORE="${CORE:-$HOME/apps/santosh-core}"
URL="https://download.blender.org/release/Blender${SERIES}"
TAR="blender-${VER}-linux-x64.tar.xz"

echo "== system libraries Blender needs headless + ffmpeg (turntable videos) + unshare (no-network jobs)"
sudo apt-get update -y
sudo apt-get install -y xz-utils libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libxkbcommon0 libsm6 libice6 \
  libegl1 ffmpeg util-linux || true

ok=0
tmp="$(mktemp -d)"
if curl -fsSL "$URL/$TAR" -o "$tmp/$TAR" && curl -fsSL "$URL/blender-${VER}.sha256" -o "$tmp/sums"; then
  want="$(grep " $TAR\$" "$tmp/sums" | awk '{print $1}')"
  got="$(sha256sum "$tmp/$TAR" | awk '{print $1}')"
  if [ -n "$want" ] && [ "$want" = "$got" ]; then
    echo "== checksum ok, installing to /opt/blender"
    sudo rm -rf "/opt/blender-${VER}"
    sudo tar -xJf "$tmp/$TAR" -C /opt
    sudo mv "/opt/blender-${VER}-linux-x64" "/opt/blender-${VER}"
    sudo ln -sfn "/opt/blender-${VER}" /opt/blender
    ok=1
  else
    echo "!! checksum did not match ($got vs $want) - not installed"
  fi
fi
rm -rf "$tmp"

if [ "$ok" = 0 ]; then
  echo "== download not possible: official bpy module from PyPI instead"
  PY313="$(command -v python3.13 || true)"
  if [ -z "$PY313" ]; then
    echo "!! needs python3.13 (sudo apt-get install python3.13 python3.13-venv) - stopping"; exit 1
  fi
  "$PY313" -m venv "$CORE/.blender-venv"
  "$CORE/.blender-venv/bin/pip" install --quiet "bpy==${VER}"
  echo "BLENDER_PY=$CORE/.blender-venv/bin/python" | tee -a "$CORE/.env" >/dev/null
fi

echo "== quick check"
cd "$CORE"
"$CORE/.venv/bin/python" - <<'PYEOF' || true
import sys
sys.path.insert(0, "")
from app.blender3d import sandbox
print("Blender:", sandbox.find() or "NOT FOUND", "| jobs without network:", sandbox.net_isolation())
PYEOF
if ! unshare -rn true 2>/dev/null; then
  echo "note: this kernel does not allow 'unshare -rn' for this user; jobs still run with the code check + import gate."
  echo "      (Ubuntu 24.04: sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0 to allow it)"
fi
echo "Done. Now: pm2 restart santosh --update-env"
