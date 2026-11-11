#!/usr/bin/env bash
# v0.363 BADI SCREEN: the same emulator turned into a tablet (1600x2560 px at 320 dpi = 800 dp wide) - every screen opened
# again (debug build, extra hoola_screen): it must stay alive, and a screenshot is kept so the wide layout (side rail,
# centred column, 3-column grids) can be seen. The screen size is put back afterwards.
# Usage: tablet_check.sh <debug.apk> <out_dir> <package> <screen ids...>
set -u
DBG="$1"; OUT="$2"; PKG="$3"; shift 3
mkdir -p "$OUT/tablet"
: > "$OUT/tablet.txt"
adb install -r "$DBG" < /dev/null > "$OUT/tablet_install.txt" 2>&1
adb shell wm size 1600x2560 < /dev/null; adb shell wm density 320 < /dev/null
sleep 3
# v0.820 a tap may open ANOTHER app (contacts picker, calendar, Play / browser for "Rate this app", a share sheet).
# Our force-stop does not close it, and it stays in front of every later screen (v0.815's first run: 7 screens "not
# opened" behind the contacts picker). Before each screen / tap: close whatever non-launcher app is on top, go home.
clean_front() {
  local top
  top=$(adb shell dumpsys activity activities < /dev/null 2>/dev/null | tr -d '\r' \
        | grep -m1 -E 'topResumedActivity|mResumedActivity' | grep -oE '[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+' | head -1 | cut -d/ -f1)
  if [ -n "$top" ] && [ "$top" != "$PKG" ] && ! printf '%s' "$top" | grep -qiE 'launcher|systemui'; then
    adb shell am force-stop "$top" < /dev/null
  fi
  adb shell input keyevent KEYCODE_HOME < /dev/null
}
for id in "$@"; do
  clean_front
  adb shell am force-stop "$PKG" < /dev/null
  adb shell am start -W -n "$PKG/hoola.app.MainActivity" --es hoola_screen "$id" < /dev/null > /dev/null 2>&1
  sleep 2
  adb exec-out screencap -p < /dev/null > "$OUT/tablet/$id.png" 2>/dev/null
  alive=1; adb shell pidof "$PKG" < /dev/null > /dev/null || alive=0
  echo "$id $alive" >> "$OUT/tablet.txt"
  [ "$alive" = 1 ] || { echo "::error::tablet: $id crashed"; adb logcat -d -t 200 < /dev/null | grep -E "AndroidRuntime|FATAL" | head -20; }
done
adb shell wm size reset < /dev/null; adb shell wm density reset < /dev/null
dead=$(awk '$2==0' "$OUT/tablet.txt" | wc -l | tr -d ' ')
echo "tablet: $(wc -l < "$OUT/tablet.txt" | tr -d ' ') screens, $dead crashed"
[ "$dead" = 0 ]
