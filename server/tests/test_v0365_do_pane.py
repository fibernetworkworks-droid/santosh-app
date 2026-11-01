"""v0.365 DO PANE (App Sahayak Phase 29): on a wide Android screen a record opened from a tab shows beside that tab's list
(42 / 58), a record opened from the list replaces the one on the right, Back closes it, the rail stays with the list's tab lit;
phones unchanged. The CI tablet pass opens every non-tab screen from the start tab = the two-pane view."""
from pathlib import Path

NAV = Path(__file__).resolve().parents[1] / "app/appmaker/android/template/app/src/main/java/hoola/kit/Nav.kt"


def test_shell_two_panes():
    s = NAV.read_text()
    assert "var split by mutableStateOf(false)" in s
    assert "if (split) while (stack.size > 1) stack.removeAt(stack.lastIndex)" in s
    assert "val split = wide && nav.stack.size >= 2 && nav.tabs.any { it.id == base }" in s
    assert "Box(Modifier.weight(0.42f).fillMaxSize()) { key(base, AppData.version.value) { screen(base) } }" in s
    assert "if (railNow && (nav.onTab || split)) Rail(nav)" in s and "selected = nav.stack.firstOrNull() == t.id" in s
