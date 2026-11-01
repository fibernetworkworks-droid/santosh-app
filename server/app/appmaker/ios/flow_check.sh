#!/usr/bin/env bash
# v0.345 HAR RAASTA on the iPhone: runs the generated XCUITest (UITests/FlowTests.swift) on the booted iPhone simulator -
# every button / link on every screen tapped from a fresh start - and folds the result into <out>/report.json (flows.py).
# Run from the project folder after sim_check.sh (which leaves the simulator booted). usage: flow_check.sh <out dir>
set -u
OUT="$1"
P=$(ls -d *.xcodeproj | head -1)
DEV=$(xcrun simctl list devices booted -j | python3 -c '
import json, sys
d = [x for v in json.load(sys.stdin)["devices"].values() for x in v]
d.sort(key=lambda x: "Max" in x["name"])            # the plain iPhone first (the Pro Max is for store pictures)
print(d[0]["udid"] if d else "")')
[ -n "$DEV" ] || { echo "::error::no booted simulator for the flow walk"; exit 1; }
NAME=$(grep -m1 '^name:' project.yml | awk '{print $2}')
REPORTS="$HOME/Library/Logs/DiagnosticReports"
before=$(ls "$REPORTS" 2>/dev/null | grep -c "$NAME" || true)
xcodebuild test -project "$P" -scheme App -destination "id=$DEV" -derivedDataPath dd CODE_SIGNING_ALLOWED=NO \
  -only-testing:AppUITests > "$OUT/flows.log" 2>&1 || true
grep -E "error:|Test Case .* (passed|failed)|\*\* TEST" "$OUT/flows.log" | tail -8
now=$(ls "$REPORTS" 2>/dev/null | grep -c "$NAME" || true)
if [ "$now" -gt "$before" ]; then
  CR=$(ls -t "$REPORTS" | grep "$NAME" | head -1)
  head -c 3500 "$REPORTS/$CR" > "$OUT/flows-crash.txt"
fi
python3 hoola_qa/flows.py "$OUT" "$OUT/flows.log"
