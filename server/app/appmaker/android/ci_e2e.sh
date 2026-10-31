#!/usr/bin/env bash
# v0.314: runs inside the CI emulator after ci_smoke.sh. The debug build of the fixture app talks to a REAL Hoola server
# on the runner (http://10.0.2.2:8077, debug builds only): the kit's E2e signs up, places an order through the outbox,
# checks the server-priced copy, sends the same write twice (one row), signs out and in. Pass = logcat "HOOLA_E2E OK".
# Usage: ci_e2e.sh out_dir [debug.apk]   (v0.324: the device check leaves the RELEASE build installed; the debug one goes back)
set -u
OUT="$1"
[ -n "${2:-}" ] && adb install -r "$2" > /dev/null
PKG="in.hoola.preview.fixture"
mkdir -p "$OUT"
adb shell pm clear "$PKG" > /dev/null
adb logcat -c
adb shell am start -W -n "$PKG/hoola.app.MainActivity" --ez hoola_e2e true --es hoola_test_server "http://10.0.2.2:8077" > /dev/null
for i in $(seq 1 90); do
  if adb logcat -d -s HOOLA_E2E:I | grep -qE "HOOLA_E2E (OK|FAIL)"; then break; fi
  sleep 1
done
adb exec-out screencap -p > "$OUT/_e2e.png"
adb logcat -d -s HOOLA_E2E:I | tee "$OUT/e2e.txt"
adb logcat -d > "$OUT/logcat_e2e.txt"
if grep -q "HOOLA_E2E OK" "$OUT/e2e.txt"; then exit 0; fi
grep -E "HOOLA_E2E FAIL" "$OUT/e2e.txt" | while IFS= read -r l; do echo "::error::$l"; done
grep -A 25 "FATAL EXCEPTION" "$OUT/logcat_e2e.txt" | head -40 | while IFS= read -r l; do echo "::error::$l"; done
[ -s "$OUT/e2e.txt" ] || echo "::error::no HOOLA_E2E line in 90 s"
exit 1
