"""v0.820: a tap that opens ANOTHER app (contacts picker, calendar, Play / browser) must not hide every later screen.

v0.815's first CI run: the Android device check tapped 'Pick from contacts' on the fixture dashboard, the contacts picker
stayed on top, and the next 7 screens were reported as not opened (support, seller_info, privacy, ... ) - behind the
picker. `clean_front` closes whatever non-launcher app is in front before each screen and after each tap. Driven here
with a fake adb on PATH."""
import os
import stat
import subprocess
from pathlib import Path

AND = Path(__file__).resolve().parents[1] / "app" / "appmaker" / "android"


def _run(tmp_path, top_line):
    log = tmp_path / "adb.log"
    fake = tmp_path / "adb"
    fake.write_text("#!/usr/bin/env bash\n"
                    f'echo "$@" >> "{log}"\n'
                    'if [ "$1 $2 $3" = "shell dumpsys activity" ]; then\n'
                    f"  printf '  {top_line}\\n'\n"
                    "fi\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    src = (AND / "device_check.sh").read_text()
    fn = src[src.index("clean_front() {"):src.index("\n}\n", src.index("clean_front() {")) + 3]
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "PKG": "in.hoola.preview.fixture"}
    subprocess.run(["bash", "-c", fn + "\nclean_front"], env=env, check=True, timeout=20)
    return log.read_text()


def test_a_foreign_app_on_top_is_closed_then_home(tmp_path):
    out = _run(tmp_path, "topResumedActivity=ActivityRecord{1 u0 com.google.android.contacts/.activities.PickerActivity t9}")
    assert "shell am force-stop com.google.android.contacts" in out
    assert out.strip().splitlines()[-1] == "shell input keyevent KEYCODE_HOME"


def test_our_app_and_the_launcher_are_never_force_stopped_here(tmp_path):
    ours = _run(tmp_path, "topResumedActivity=ActivityRecord{1 u0 in.hoola.preview.fixture/hoola.app.MainActivity t9}")
    assert "force-stop" not in ours
    (tmp_path / "adb.log").unlink()
    home = _run(tmp_path, "mResumedActivity: ActivityRecord{2 u0 com.google.android.apps.nexuslauncher/.NexusLauncherActivity t1}")
    assert "force-stop" not in home and "KEYCODE_HOME" in home


def test_called_before_every_screen_and_around_every_tap():
    s = (AND / "device_check.sh").read_text()
    loop = s[s.index('for id in "$@"; do'):]
    assert loop.index("clean_front") < loop.index('adb shell am force-stop "$PKG"')
    tap = s[s.index("n=$((n + 1))"):s.index("done 3<")]
    assert tap.count("clean_front") == 2                     # before the fresh start and after the tap is judged
    t = (AND / "tablet_check.sh").read_text()
    assert "clean_front() {" in t and t.index("clean_front\n") < t.index('adb shell am force-stop "$PKG" < /dev/null')
