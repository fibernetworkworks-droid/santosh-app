#!/usr/bin/env bash
# HOOLA FRAMES (v0.471): installs HeyGen's open-source HyperFrames engine (github.com/heygen-com/hyperframes,
# Apache 2.0) PINNED to hyperframes 0.9.6, and pre-warms its headless Chromium. The model writes the HTML
# composition; this engine turns it into a deterministic MP4 (frame-clock seek -> Chrome capture -> FFmpeg).
# Renders run nice -n 19, one at a time, killed on timeout - the worker (server/app/studio/frames.py) enforces it.
# Needs: node >= 22 + npm (a STANDALONE Node 22 in ~/apps/node22 is fine and never touches pm2's runtime),
# ffmpeg with libass + x264 (already installed by setup_video.sh). Disk: ~1 GB browser cache, 10 GB project cap.
set -euo pipefail
DIR="${FRAMES_DIR:-$HOME/apps/hoola-frames-cli}"
mkdir -p "$DIR" && cd "$DIR"
[ -f package.json ] || npm init -y >/dev/null
for i in 1 2 3; do
  npm install --ignore-scripts --save-exact hyperframes@0.9.6 && break
  [ "$i" = 3 ] && { echo "npm install failed 3x - check the registry from this box"; exit 1; }
  echo "retry $i..."; sleep 10
done
HF="$DIR/node_modules/.bin/hyperframes"
[ -x "$HF" ] || { echo "hyperframes launcher missing after install"; exit 1; }
"$HF" --version
echo "== pre-warming headless Chromium (one-time ~150 MB download)"
"$HF" browser ensure || echo "WARN: browser ensure failed; the first render will download it instead"
echo "== ffmpeg check (libass + x264 needed for captions/encode)"
command -v ffmpeg >/dev/null || { echo "ffmpeg missing: sudo apt install -y ffmpeg"; exit 1; }
ffmpeg -hide_banner -filters 2>/dev/null | grep -qE ' (ass|subtitles) ' && echo "ffmpeg ok (libass present)"
echo
echo "Add to ~/apps/santosh-core/.env (idempotent block is written by the hf_setup job):"
echo "FRAMES_BIN=$HF"
echo "FRAMES_ROOT=\$HOME/apps/hoola-frames"
echo "FRAMES_TIMEOUT_S=900"
echo "FRAMES_DISK_CAP_GB=10"
