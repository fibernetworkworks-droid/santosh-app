"""v0.455 fix: the iPhone simulator check calls a screen crashed only when the app really is gone.

The old probe compared the pid `simctl launch` printed with the pid column of `launchctl list`. On the FIRST
simulator of a job that matched; on the second and third (Pro Max for the App Store shots, then the 13-inch iPad)
it failed for EVERY screen - the run said "opened 0, 17 crashed" while the very same step saved 18 correctly
sized, non-blank screenshots of those screens. A crashed app cannot be photographed, so the report was wrong and
the iPhone workflow had been red on that for weeks.

These tests drive the real awk + case logic out of the shipped script, so the shape of a live and of an exited
service is pinned here and not in a comment.
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
