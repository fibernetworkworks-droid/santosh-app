#!/usr/bin/env bash
# v0.65 Hoola Video Editor: ffmpeg (with libass + x264) for rendering. faster-whisper is optional (exact word timings
# for captions; without it Gemini's timed transcript is used).
set -euo pipefail
sudo apt-get update -y
sudo apt-get install -y ffmpeg fonts-noto-core
ffmpeg -hide_banner -filters | grep -qE ' (ass|subtitles) ' && echo "ffmpeg ok (libass present)"
if [ "${WITH_WHISPER:-0}" = "1" ]; then
  ~/apps/santosh-core/.venv/bin/pip install faster-whisper
  echo "set VIDEO_WHISPER=true in ~/apps/santosh-core/.env"
fi
