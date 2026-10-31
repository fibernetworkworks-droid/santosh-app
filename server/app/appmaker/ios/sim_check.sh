#!/usr/bin/env bash
# v0.332 IPHONE: HOOLA QA on an iPhone simulator (macOS runner). Installs the debug .app, opens EVERY screen directly
# (-hoola_screen <id>), photographs it, and calls a screen crashed when the app process is gone after it opened
# or a crash report for the app appeared. Writes <out>/report.json + <out>/<screen>.png.
# usage: sim_check.sh <App.app> <bundle id> <out dir> <screen ids...>
set -u
APP="$1"; BID="$2"; OUT="$3"; shift 3
mkdir -p "$OUT"
DEV=$(xcrun simctl list devices available -j | python3 -c '
import json, sys
d = json.load(sys.stdin)["devices"]
best = []
for rt, devs in d.items():
    if "iOS" not in rt:
        continue
    for x in devs:
        if x.get("isAvailable") and x["name"].startswith("iPhone"):
            best.append((rt, x["name"], x["udid"]))
best.sort()
print(best[-1][2] if best else "")')
[ -n "$DEV" ] || { echo "::error::no iPhone simulator on this Mac"; exit 1; }
echo "simulator $DEV"
xcrun simctl boot "$DEV" 2>/dev/null || true
xcrun simctl bootstatus "$DEV" -b > /dev/null
xcrun simctl status_bar "$DEV" override --time "9:41" --batteryState charged --batteryLevel 100 2>/dev/null || true
xcrun simctl install "$DEV" "$APP"
NAME=$(/usr/libexec/PlistBuddy -c "Print :CFBundleExecutable" "$APP/Info.plist" 2>/dev/null || echo App)
REPORTS="$HOME/Library/Logs/DiagnosticReports"
mkdir -p "$REPORTS"
before=$(ls "$REPORTS" 2>/dev/null | grep -c "$NAME" || true)
SIZE_KB=$(du -sk "$APP" | cut -f1)
python3 - "$OUT" <<'PY'
import json, sys
json.dump({"screens": {}}, open(sys.argv[1] + "/state.json", "w"))
PY
cold=""
for s in "$@"; do
  xcrun simctl terminate "$DEV" "$BID" > /dev/null 2>&1 || true
  t0=$(python3 -c 'import time; print(time.time())')
  pid=$(xcrun simctl launch "$DEV" "$BID" -hoola_screen "$s" 2>&1 | awk -F': ' '{print $NF}' | tr -dc '0-9')
  t1=$(python3 -c 'import time; print(time.time())')
  [ -z "$cold" ] && cold=$(python3 -c "print(int(($t1-$t0)*1000))")
  sleep 3
  alive=0
  if [ -n "$pid" ] && xcrun simctl spawn "$DEV" launchctl list 2>/dev/null | grep "$BID" | awk '{print $1}' | grep -qx "$pid"; then alive=1; fi
  now=$(ls "$REPORTS" 2>/dev/null | grep -c "$NAME" || true)
  crashed=0
  if [ "$alive" = 0 ] || [ "$now" -gt "$before" ]; then crashed=1; before=$now; fi
  xcrun simctl io "$DEV" screenshot "$OUT/$s.png" > /dev/null 2>&1 || true
  python3 - "$OUT" "$s" "$crashed" <<'PY'
import json, os, sys
out, sid, crashed = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
st = json.load(open(out + "/state.json"))
png = out + f"/{sid}.png"
st["screens"][sid] = {"crashed": crashed, "shot": os.path.exists(png), "bytes": os.path.getsize(png) if os.path.exists(png) else 0}
json.dump(st, open(out + "/state.json", "w"))
PY
  echo "$s crashed=$crashed"
done
# the crash text (first one) for the fix step
CR=$(ls -t "$REPORTS" 2>/dev/null | grep "$NAME" | head -1)
[ -n "$CR" ] && head -c 6000 "$REPORTS/$CR" > "$OUT/crash.txt" || true
python3 - "$OUT" "${cold:-}" "$SIZE_KB" <<'PY'
import json, sys
out, cold, kb = sys.argv[1], sys.argv[2], sys.argv[3]
st = json.load(open(out + "/state.json"))
sc = st["screens"]
crashed = [k for k, v in sc.items() if v["crashed"]]
blank = [k for k, v in sc.items() if not v["crashed"] and v["bytes"] < 8000]
rep = {"platform": "ios", "opened": len(sc) - len(crashed), "total": len(sc), "crashed": crashed, "blank": blank,
       "perf": {"launch_ms": int(cold) if cold.isdigit() else None, "app_mb": round(int(kb) / 1024, 2) if kb.isdigit() else None},
       "screens": sc, "passed": not crashed and len(sc) > 0}
json.dump(rep, open(out + "/report.json", "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("opened", "total", "crashed", "blank", "perf", "passed")}))
PY
