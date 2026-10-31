#!/usr/bin/env bash
# v0.324 HOOLA QA: the device check every Hoola-made app gets after it compiles, on a real Android emulator (CI, the
# GitHub builds repo, or a build machine with an emulator). Like a human team's QA pass:
#   * every screen opened (debug build, extra hoola_screen): no crash, a screenshot, the UI tree for the accessibility
#     check (unlabelled buttons, tap targets under 48 dp), the crash's logcat when there is one;
#   * the release build: cold start 3 times (am start -W TotalTime), a few swipes then dumpsys gfxinfo (janky frames);
#   * then qa.py writes report.json (budget: cold start, APK size; crashes block the build).
# Usage: device_check.sh <debug.apk> <release.apk> <out_dir> <package> <screen ids...>
set -u
DBG="$1"; REL="$2"; OUT="$3"; PKG="$4"; shift 4
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT/screens"
: > "$OUT/opened.txt"; : > "$OUT/cold.txt"
adb wait-for-device
adb shell wm density | tr -dc '0-9\n' | tail -1 > "$OUT/density.txt"
adb install -r "$DBG" > "$OUT/install_debug.txt" 2>&1 || { echo "::error::debug install failed"; cat "$OUT/install_debug.txt"; }
for id in "$@"; do
  adb shell am force-stop "$PKG"
  adb logcat -c
  adb shell am start -W -n "$PKG/hoola.app.MainActivity" --es hoola_screen "$id" > /dev/null 2>&1
  sleep 3
  adb exec-out screencap -p > "$OUT/screens/$id.png" 2>/dev/null
  adb shell uiautomator dump /sdcard/hoola_ui.xml > /dev/null 2>&1 && adb pull /sdcard/hoola_ui.xml "$OUT/screens/$id.xml" > /dev/null 2>&1
  alive=1; adb shell pidof "$PKG" > /dev/null || alive=0
  adb logcat -d -b crash > "$OUT/screens/$id.crash.txt" 2>/dev/null || true
  grep -q "FATAL EXCEPTION" "$OUT/screens/$id.crash.txt" 2>/dev/null && alive=0
  echo "$id $alive" >> "$OUT/opened.txt"
done
# release build: cold start + scrolling (same signing key: installs over the debug build)
adb shell am force-stop "$PKG"
if [ -f "$REL" ]; then
  adb install -r "$REL" > "$OUT/install_release.txt" 2>&1 || true
  adb shell pm clear "$PKG" > /dev/null 2>&1
  for i in 1 2 3; do
    adb shell am force-stop "$PKG"
    sleep 1
    adb shell am start -W -n "$PKG/hoola.app.MainActivity" 2>/dev/null | tr -d '\r' | awk -F': ' '/TotalTime/ {print $2}' >> "$OUT/cold.txt"
    sleep 2
  done
  adb shell dumpsys gfxinfo "$PKG" reset > /dev/null 2>&1
  for i in 1 2 3 4; do adb shell input swipe 540 1600 540 500 300; sleep 0.6; adb shell input swipe 540 600 540 1500 300; sleep 0.6; done
  adb shell dumpsys gfxinfo "$PKG" > "$OUT/gfxinfo.txt" 2>/dev/null
  stat -c %s "$REL" > "$OUT/apk_bytes.txt" 2>/dev/null || wc -c < "$REL" > "$OUT/apk_bytes.txt"
fi
python3 "$HERE/qa.py" report "$OUT" > "$OUT/summary.txt"
cat "$OUT/summary.txt"
