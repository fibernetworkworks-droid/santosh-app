#!/usr/bin/env bash
# v0.332 IPHONE: runs on the CI Mac after sim_check.sh. The DEBUG build of the fixture app talks to a REAL Hoola server on the
# runner (http://localhost:8077, debug builds only): E2e.swift signs up, orders through the outbox (server-priced), sends the
# same write twice (one row), a photo up and back, the UPI paid claim, the updates check, a crash report, sign out / in.
# Pass = "HOOLA_E2E OK" in the app's Documents/hoola_e2e.txt. Server side is checked by `python -m app.appmaker.android.ci_e2e check`.
# usage: ci_e2e.sh <bundle id> <out dir>
set -u
BID="$1"; OUT="$2"
mkdir -p "$OUT"
DEV=$(xcrun simctl list devices booted -j | python3 -c 'import json,sys; d=json.load(sys.stdin)["devices"]; print(next((x["udid"] for v in d.values() for x in v), ""))')
[ -n "$DEV" ] || { echo "::error::no booted simulator"; exit 1; }
xcrun simctl terminate "$DEV" "$BID" > /dev/null 2>&1 || true
DATA=$(xcrun simctl get_app_container "$DEV" "$BID" data)
rm -f "$DATA/Documents/hoola_e2e.txt"
xcrun simctl launch "$DEV" "$BID" -hoola_e2e -hoola_base "http://localhost:8077" > /dev/null
for i in $(seq 1 120); do
  if grep -qE "HOOLA_E2E (OK|FAIL)" "$DATA/Documents/hoola_e2e.txt" 2>/dev/null; then break; fi
  sleep 1
done
xcrun simctl io "$DEV" screenshot "$OUT/_e2e.png" > /dev/null 2>&1 || true
cp "$DATA/Documents/hoola_e2e.txt" "$OUT/e2e.txt" 2>/dev/null || echo "no result file" > "$OUT/e2e.txt"
cat "$OUT/e2e.txt"
if grep -q "HOOLA_E2E OK" "$OUT/e2e.txt"; then exit 0; fi
grep -E "HOOLA_E2E FAIL" "$OUT/e2e.txt" | while IFS= read -r l; do echo "::error::$l"; done
exit 1
