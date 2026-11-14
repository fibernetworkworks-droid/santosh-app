"""v0.905 NAV GAP: the room under a page is the tab bar's measured height + a small gap, never a fixed 96 dp."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
SHOTS = (ROOT / "test/goldens/screens_test.dart").read_text()


def test_room_is_measured_not_fixed():
    assert ": 96.0;" not in SHELL, "the fixed 96 dp reservation is gone"
    assert "const double navGap = 4;" in SHELL
    assert "MediaQuery.paddingOf(context).bottom + navGap" in SHELL
    assert "extendBody: true" in SHELL, "the Scaffold hands the tab bar's height down as bottom padding"


def test_gap_is_measured_on_the_real_shell():
    assert "61_gap_home_" in SHOTS and "61_gap_chat_" in SHOTS
    assert "moreOrLessEquals(12" in SHOTS and "FakeViewPadding(bottom:" in SHOTS


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.906.0"
    assert "version: 0.906.0+905" in (ROOT / "pubspec.yaml").read_text()
