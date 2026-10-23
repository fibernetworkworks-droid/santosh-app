#!/usr/bin/env bash
# v0.132: runs inside an Android emulator (CI). Installs the debug build of the fixture app, opens EVERY screen (debug-only
# extra hoola_screen), takes its picture, and fails when the app crashes anywhere. Usage: ci_smoke.sh app-debug.apk out_dir ids...
set -u
APK="$1"; OUT="$2"; shift 2
PKG="in.hoola.preview.fixture"
mkdir -p "$OUT"
adb install -r "$APK" || exit 1
adb logcat -c
fail=0
for id in "$@"; do
  adb shell am force-stop "$PKG"
  adb shell am start -W -n "$PKG/hoola.app.MainActivity" --es hoola_screen "$id" > /dev/null
  sleep 4
  adb exec-out screencap -p > "$OUT/$id.png"
  if ! adb shell pidof "$PKG" > /dev/null; then echo "::error::screen $id: app not running (crash?)"; fail=1; fi
done
# the first-run flow too: splash -> consent
adb shell pm clear "$PKG" > /dev/null
adb shell am start -W -n "$PKG/hoola.app.MainActivity" > /dev/null
sleep 3
adb exec-out screencap -p > "$OUT/_first_run.png"
adb logcat -d > "$OUT/logcat.txt"
if grep -E "FATAL EXCEPTION|AndroidRuntime: Process: $PKG" "$OUT/logcat.txt"; then
  grep -A 25 "FATAL EXCEPTION" "$OUT/logcat.txt" | head -60 | while IFS= read -r l; do echo "::error::$l"; done
  fail=1
fi
exit $fail
