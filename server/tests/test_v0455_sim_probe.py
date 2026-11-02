"""v0.455 fix: the iPhone simulator check checks the APP, and calls a screen crashed only when it really is gone.

Two faults, found in this order:

1. The probe compared the pid `simctl launch` printed with the pid column of `launchctl list`. The printed pid is
   parsed out of simctl's own text, so anything extra in that text welds the digits together. It now reads the pid
   column for our bundle id and asks only whether it is numeric ("-" means the service has exited).

2. The REAL cause of fifteen red runs: `find ... -name "*.app" | head -1` picked `AppUITests-Runner.app` once the
   flow walk had built it beside the app. The Pro Max and iPad steps installed the TEST RUNNER, launched a bundle
   id that was not on that device, and `simctl io screenshot` photographed the simulator's HOME SCREEN - which is
   a valid, correctly sized, non-blank PNG, so the App Store size check passed on pictures of an iPad springboard.
   The same selection is in her real app builds, whose screenshots go to App Store Connect.

These tests run the shipped awk, `case` and bundle-id guard out of the script itself, so the behaviour is pinned
here and not in a comment.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

SIM = Path(__file__).resolve().parents[1] / "app/appmaker/ios/sim_check.sh"
LIVE = "1234\t0\tUIKitApplication:in.hoola.preview.fixture[0x3f1c][5678]\n"
OTHER = "-\t0\tUIKitApplication:in.other.app[0x11][22]\n"
GONE = "-\t0\tUIKitApplication:in.hoola.preview.fixture[0x3f1c][5678]\n"


def _probe() -> str:
    """The awk program the script actually ships (so this test cannot drift from it)."""
    t = SIM.read_text()
    m = re.search(r"lpid=\$\(xcrun simctl spawn \"\$DEV\" launchctl list 2>/dev/null \| (awk .*)\)", t)
    assert m, "the liveness probe line changed shape"
    return m.group(1)


def _alive(listing: str, bid: str = "in.hoola.preview.fixture") -> bool:
    """Run the shipped probe + the shipped `case` on a launchctl listing and say whether the app is alive."""
    script = (
        'lpid=$(printf "%s" "$LISTING" | ' + _probe().replace('"$BID"', '"$BID"') + ")\n"
        'case "$lpid" in\n'
        "  ''|*[!0-9]*) echo no ;;\n"
        "  *) echo yes ;;\n"
        "esac\n"
    )
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                         env={"LISTING": listing, "BID": bid, "PATH": "/usr/bin:/bin"})
    assert out.returncode == 0, out.stderr
    return out.stdout.strip() == "yes"


def test_a_running_app_is_not_a_crash_even_among_other_services():
    assert _alive(OTHER + LIVE) is True
    assert _alive(LIVE + OTHER) is True


def test_an_exited_app_is_a_crash():
    assert _alive(GONE + OTHER) is False          # launchctl writes "-" in the pid column once it has gone
    assert _alive(OTHER) is False                 # our bundle id is not listed at all


def test_the_probe_does_not_depend_on_the_pid_simctl_printed():
    t = SIM.read_text()
    probe = t[t.index("  alive=0"):t.index("  now=$(ls")]
    assert "$pid" not in probe, "back to comparing simctl's pid: that is the bug this test exists for"
    assert "grep -qx" not in probe


def test_only_our_own_simulator_is_booted():
    """Two booted simulators is what made `simctl spawn ... launchctl list` answer for the wrong device."""
    t = SIM.read_text()
    assert "simctl shutdown all" in t
    assert t.index("simctl shutdown all") < t.index('simctl boot "$DEV"')


def test_the_e2e_check_step_waits_for_the_server_step():
    """The 'No module named sqlalchemy' error that hid the real failure: if: always() with its deps skipped."""
    wf = (Path(__file__).resolve().parents[2] / ".github/workflows/ios-check.yml").read_text()
    assert "steps.e2e_server.outcome == 'success'" in wf
    assert wf.count("if: always()\n") >= 1          # the other always() steps are untouched


# ---------------------------------------------------------------- the app under test is the APP, not the runner
def _fake_app(root: Path, bundle_id: str) -> Path:
    import plistlib
    app = root / "App.app"
    app.mkdir(parents=True, exist_ok=True)
    (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": bundle_id, "CFBundleExecutable": "App"}))
    return app


def _run(app: str, bid: str, out: Path):
    return subprocess.run(["bash", str(SIM), app, bid, str(out), "home"], capture_output=True, text=True)


def test_a_bundle_that_is_not_the_app_under_test_is_refused(tmp_path):
    """The flow walk builds AppUITests-Runner.app beside the app; find ... | head -1 then picked the RUNNER, and
    the check installed it, launched a bundle id that was not on the device and photographed the home screen."""
    runner = _fake_app(tmp_path / "r", "in.hoola.preview.fixture.xctrunner")
    r = _run(str(runner), "in.hoola.preview.fixture", tmp_path / "out")
    assert r.returncode == 1
    assert "wrong app bundle" in r.stdout + r.stderr
    assert "xctrunner" in r.stdout + r.stderr          # it says WHICH bundle it was handed


def test_a_missing_bundle_is_refused_loudly(tmp_path):
    r = _run(str(tmp_path / "nope.app"), "in.hoola.preview.fixture", tmp_path / "out")
    assert r.returncode == 1 and "no app bundle" in r.stdout + r.stderr


def test_the_real_app_gets_past_the_guard(tmp_path):
    """Same id = the check proceeds (and then stops at the simulator, which this machine has not got)."""
    app = _fake_app(tmp_path / "a", "in.hoola.preview.fixture")
    r = _run(str(app), "in.hoola.preview.fixture", tmp_path / "out")
    said = r.stdout + r.stderr
    assert "wrong app bundle" not in said and "no app bundle" not in said


def test_no_caller_can_pick_the_test_runner():
    """Both workflows - the fixture check AND her real app builds, whose App Store screenshots go to Apple."""
    for rel in (".github/workflows/ios-check.yml", "server/app_builder/hoola-ios.yml"):
        y = (Path(__file__).resolve().parents[2] / rel).read_text()
        assert '-name "*.app" | head -1' not in y and "-name '*.app' | head -1" not in y, rel
        assert y.count("! -name") >= 3 or rel.endswith("hoola-ios.yml"), rel
        assert "Runner.app" in y, rel
